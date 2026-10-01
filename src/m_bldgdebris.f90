module m_bldgdebris
  ! ============ 家屋破壊・瓦礫プロセスモジュール(§63) ============
  ! 木造家屋群を「破壊可能なストック」のラスタ場として扱い、氾濫流による
  ! 破壊 → 瓦礫化 → 流動・堆積を、セルごとの柱状材積 (m3/m2 = m) の
  ! オイラー的なラスタ場として概算する加算的プロセス。個別家屋の構造
  ! 応答・個別瓦礫の軌跡・衝突力・幾何的閉塞は対象外(§0 方針2。
  ! docs/housedebris_plan.md §1)。実装様式は m_driftwood(§50)に倣う。
  !   台帳:   家屋ストック wbs(私有。幾何面積基底。入力)→ 破壊 →
  !           流動瓦礫 s%hbd(柱状量。貯留の意味論は h・hd と同一)→
  !           接地・低速 → 堆積瓦礫 s%wbd(柱状量。再流動あり)
  !   輸送:   advect_scalar を swflow_enc がステップ内で実行(s%bd_active)。
  !           本モジュールは破壊・停止・再流動・台帳・診断を担う(セル
  !           局所のみ = エッジ・ハロ・collective 不要)
  !   有効化: fn_bldgdebris の指定(&list_bldgdebris。f_bd=0 で一時無効化)。
  !           ENC 格子のみ。無効時はメモリ・CPU ゼロ追加
  !   破壊:   判定量 X が閾値を超えたセルで wbs→hbd(沈下率 bd_fsink の
  !           分は wbd へ直行)をレート bd_wdes(数値的閉包【独自】・閾値
  !           【要文献照合】)。X は f_bdcrit=1: 浸水深 h+hs、
  !           f_bdcrit=2: 荷重 (h + (1+s)hs + sg_log·hd + sg_bd·hbd)·V²
  !           (F9999 の清水規格化と同じ基底。浮遊物を混合密度に足す =
  !           単位面積あたりの運動量流束の加算。個別衝突の衝撃荷重では
  !           ない)。第2閾値を与えたときは線形ランプの破壊可能率を乗じる
  !   停止:   喫水 hf(円柱の浮力平衡。m_driftwood_draft を共用)。
  !           h+hs < hf または vv < bd_vstop で hbd→wbd をレート bd_wstop。
  !           乾燥セル(h≤dd)は全量。再流動は流木と同型(既定なし)
  !   流木:   s%hd・s%dw_sg を読むだけの一方向依存(dw_active で分岐)。
  !           m_driftwood は本モジュールを知らない
  !   帰還:   空隙率への帰還(f_bdgv。§63.4)は B2 で実装。本版は f_bdgv=0
  !           のみ受理(片方向結合 = 流れは変わらない)
  !   ダム:   捕捉帯セルの流動瓦礫はダム台帳へ(m_driftwood と同じ契約)
  !   save:   s%hbd, s%wbd, wbs, wbs0 を私有ファイル bldgdebris.dat で保存
  !           (§7 の契約C。state.dat の形式は不変)
  !   診断:   result/bldgdebris.csv(破壊(浮遊・沈下)・堆積・再流動・
  !           ダム捕捉の累積と現在貯留。rank0、dt_recrd 間隔。par_sum_rows)
  !   出力:   f_out_hbd(流動 Bf0001…)、f_out_wbd(堆積 Bd0001… + 期間
  !           最大到達量 Bd9999 = max(hbd+wbd))、f_out_bds(破壊率
  !           Bs0001… = 1 − wbs/wbs0)、f_out_fdmax(荷重込み最大流体力
  !           Fd9999。既存 F9999 の定義は不変)
  ! ================================================================
  use iso_fortran_env, only : real64
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use m_boundary, only : t_boundary, e_struct_dam
  use list_bldgdebris, only : t_list_bldgdebris, list_bldgdebris_read
  use m_driftwood, only : m_driftwood_draft
  use m_swflow_enc, only : have_width, wfrac
  use m_fileio, only : fileio_write_rle, fileio_read_rle, fileio_read_matrix
  use m_sysdep_util, only : sysdep_mkdir
  use m_parallel, only : dcp, is_root, par_info, par_stop, par_abort, par_sum_rows, &
                         par_gather_to, par_scatter_cell
  implicit none
  private
  public :: t_bldgdebris
  public :: m_bldgdebris_init
  public :: m_bldgdebris_calc
  public :: m_bldgdebris_record
  public :: m_bldgdebris_dispose

  ! ダム捕捉台帳(m_driftwood の t_dwdam と同型)
  type t_bddam
    integer :: ist = 0                   ! b%struct のインデックス
    integer :: nc = 0                    ! 自帯内の捕捉帯セル数
    integer, allocatable :: cells(:,:)
  end type

  type t_bldgdebris
    ! init に早期 return 経路があるため全成分デフォルト初期化必須(§13)
    logical :: enabled = .false.
    logical :: initialized = .false.
    real :: hf = 0.0                     ! 喫水 (m)。円柱の浮力平衡(m_driftwood_draft)
    real :: sg = 0.0                     ! 瓦礫の見かけ比重(荷重の付加質量係数)
    integer :: crit = 1                  ! 判定量 1:浸水深 2:荷重
    real :: hcrit = 0.0                  ! 浸水深閾値 (m)
    real :: hcrit2 = 0.0                 ! 浸水深の第2閾値 (m。ランプ上端)
    logical :: have_hramp = .false.
    real :: fcrit = 0.0                  ! 荷重閾値 (m3/s2)
    real :: fcrit2 = 0.0                 ! 荷重の第2閾値
    logical :: have_framp = .false.
    real :: wdes = 0.0                   ! 破壊レート (m/s)
    real :: fsink = 0.0                  ! 沈下率(破壊量のうち堆積に直行する比率)
    real :: wstop = 0.0                  ! 接地堆積レート (m/s)
    real :: vstop = 0.0                  ! 低速堆積の流速閾値 (m/s)
    logical :: have_flt = .false.        ! 再流動の有効
    real :: wfloat = 0.0                 ! 再流動レート (m/s)
    real :: hfloat = 0.0                 ! 再流動の水深閾値 (m) = bd_rfloat·hf
    real :: vfloat = 0.0                 ! 再流動の流速閾値 (m/s)
    logical :: need_load = .false.       ! 荷重 X を毎セル評価するか(crit=2 または fdmax)
    real, allocatable :: wbs(:,:)        ! 家屋ストック (m3/m2。幾何面積基底。帯 jsh:jeh で
                                         !   確保するが更新・参照は js:je のみ)
    real, allocatable :: wbs0(:,:)       ! 家屋ストックの初期値(破壊率の分母)
    real, allocatable :: fw(:,:)         ! 破壊可能割合 fw(fn_bdfrac 指定時のみ確保。
                                         !   空隙率帰還 B2 が使う)
    integer :: ndam = 0
    type(t_bddam), allocatable :: dam(:)
    ! 診断(行部分和 real64。材積 m3)
    real(real64), allocatable :: vrow(:,:)  ! (js:je, 1:5) 1=破壊(浮遊へ) 2=破壊(沈下→堆積)
                                            !   3=堆積(hbd→wbd) 4=再流動(wbd→hbd)
                                            !   5=ダム捕捉
    integer :: un = 0                    ! CSV 装置番号(rank0)
  end type

contains


!----------------------------------------------------------------------
! 家屋破壊・瓦礫モジュールを初期化する
!   fn_bldgdebris 未指定 or f_bd=0 なら何もしない(enabled = .false.)。
!   s%bd_active を立てるため swflow init より前、m_driftwood_init より後
!   (s%dw_active・s%dw_sg を荷重の評価に使う)に呼ぶこと。
!   セル検証はゾーン2(全域 x/sw が使える帯縮小前)で行う
!----------------------------------------------------------------------
subroutine m_bldgdebris_init(bd, p, g, b, s)
  type(t_bldgdebris), intent(out) :: bd
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(in) :: b      ! ダム捕捉台帳の構築
  type(t_state), intent(inout) :: s      ! hbd/wbd の確保と bd_active
  type(t_list_bldgdebris) :: list
  integer :: i, j

  if (len_trim(p%fn_bldgdebris) == 0) then
    ! 瓦礫出力は本モジュールが前提(f_out_hd と同じ様式)
    if (p%f_out_hbd > 0 .or. p%f_out_wbd > 0 .or. p%f_out_bds > 0 .or. p%f_out_fdmax > 0) then
      call par_stop("list_sysparam: f_out_hbd/f_out_wbd/f_out_bds/f_out_fdmax require " &
                    //"the building-debris module (fn_bldgdebris)")
    end if
    return
  end if
  if (p%f_gridsystem /= 0) then
    call par_stop("list_bldgdebris: the building-debris module supports the ENC grid only")
  end if

  call list_bldgdebris_read(p, list)
  if (list%f_bd == 0) then      ! fn を書いたまま一時無効化する経路
    if (p%f_out_hbd > 0 .or. p%f_out_wbd > 0 .or. p%f_out_bds > 0 .or. p%f_out_fdmax > 0) then
      call par_stop("list_sysparam: f_out_hbd/f_out_wbd/f_out_bds/f_out_fdmax require " &
                    //"the building-debris module (f_bd=0 disables it)")
    end if
    return
  end if

  ! --- 瓦礫の代表諸元(喫水の実体。必須) ---
  if (list%bd_dlog <= -9998.0) call par_stop("list_bldgdebris: bd_dlog (m) is required")
  if (list%bd_dlog <= 0.0) call par_stop("list_bldgdebris: bd_dlog must be > 0")
  if (list%bd_sg <= -9998.0) call par_stop("list_bldgdebris: bd_sg is required")
  if (list%bd_sg <= 0.0 .or. list%bd_sg >= 1.0) then
    call par_stop("list_bldgdebris: bd_sg must be in (0,1) — floatable debris; sinking " &
                  //"debris is represented by bd_fsink")
  end if
  bd%sg = list%bd_sg
  bd%hf = m_driftwood_draft(list%bd_sg, list%bd_dlog)

  ! --- 破壊判定 ---
  select case (list%f_bdcrit)
  case (1)
    if (list%bd_hcrit <= -9998.0) call par_stop("list_bldgdebris: bd_hcrit (m) is required " &
                                                //"for f_bdcrit=1")
    if (list%bd_hcrit < 0.0) call par_stop("list_bldgdebris: bd_hcrit must be >= 0")
    bd%hcrit = list%bd_hcrit
    if (list%bd_hcrit2 > -9998.0) then
      if (list%bd_hcrit2 <= list%bd_hcrit) then
        call par_stop("list_bldgdebris: bd_hcrit2 must be > bd_hcrit (ramp upper end)")
      end if
      bd%hcrit2 = list%bd_hcrit2
      bd%have_hramp = .true.
    end if
  case (2)
    if (list%bd_fcrit <= -9998.0) call par_stop("list_bldgdebris: bd_fcrit (m3/s2) is " &
                                                //"required for f_bdcrit=2")
    if (list%bd_fcrit < 0.0) call par_stop("list_bldgdebris: bd_fcrit must be >= 0")
    bd%fcrit = list%bd_fcrit
    if (list%bd_fcrit2 > -9998.0) then
      if (list%bd_fcrit2 <= list%bd_fcrit) then
        call par_stop("list_bldgdebris: bd_fcrit2 must be > bd_fcrit (ramp upper end)")
      end if
      bd%fcrit2 = list%bd_fcrit2
      bd%have_framp = .true.
    end if
  case default
    call par_stop("list_bldgdebris: f_bdcrit must be 1 (inundation depth) or 2 (load)")
  end select
  bd%crit = list%f_bdcrit
  if (list%bd_wdes <= -9998.0) call par_stop("list_bldgdebris: bd_wdes (m/s) is required")
  if (list%bd_wdes <= 0.0) call par_stop("list_bldgdebris: bd_wdes must be > 0")
  bd%wdes = list%bd_wdes
  if (list%bd_fsink < 0.0 .or. list%bd_fsink > 1.0) then
    call par_stop("list_bldgdebris: bd_fsink must be in [0,1]")
  end if
  bd%fsink = list%bd_fsink
  bd%need_load = (bd%crit == 2 .or. p%f_out_fdmax > 0)

  ! --- 停止・堆積(必須)---
  if (list%bd_wstop <= -9998.0) call par_stop("list_bldgdebris: bd_wstop (m/s) is required")
  if (list%bd_wstop <= 0.0) call par_stop("list_bldgdebris: bd_wstop must be > 0")
  bd%wstop = list%bd_wstop
  if (list%bd_vstop < 0.0) call par_stop("list_bldgdebris: bd_vstop must be >= 0")
  bd%vstop = list%bd_vstop

  ! --- 再流動(既定 bd_wfloat=0 = なし。ヒステリシスの検証つき)---
  if (list%bd_wfloat < 0.0) call par_stop("list_bldgdebris: bd_wfloat must be >= 0")
  if (list%bd_wfloat > 0.0) then
    if (list%bd_rfloat <= 1.0) then
      call par_stop("list_bldgdebris: bd_rfloat must be > 1 (hysteresis against " &
                    //"per-step deposit/refloat oscillation)")
    end if
    if (list%bd_vfloat <= -9998.0) then
      call par_stop("list_bldgdebris: bd_wfloat requires bd_vfloat (m/s)")
    end if
    if (list%bd_vfloat < bd%vstop) then
      call par_stop("list_bldgdebris: bd_vfloat must be >= bd_vstop (hysteresis)")
    end if
    bd%wfloat = list%bd_wfloat
    bd%hfloat = list%bd_rfloat * bd%hf
    bd%vfloat = list%bd_vfloat
    bd%have_flt = .true.
  end if

  ! --- 空隙率への帰還は B2 で実装(本版は片方向結合のみ) ---
  if (list%f_bdgv /= 0) then
    call par_stop("list_bldgdebris: f_bdgv=1 (feedback to the void ratio) is not " &
                  //"available in this version — set f_bdgv=0 (one-way coupling)")
  end if

  ! --- 瓦礫はイベント量であり地形時間の加速と整合しない(流木と同じ) ---
  if (s%geo_morfac /= 0.0 .and. s%geo_morfac /= 1.0) then
    call par_stop("list_bldgdebris: the building-debris module requires morfac=1 " &
                  //"(event-scale computation)")
  end if

  ! --- 家屋ストック(一様 bd_stock0 か分布 fn_bdstock の排他でどちらか
  !     必須。分布は rank0 読み+帯 scatter。方式2) ---
  if (len_trim(list%fn_bdstock) > 0 .and. list%bd_stock0 > -9998.0) then
    call par_stop("list_bldgdebris: specify the building stock by either bd_stock0 " &
                  //"(uniform) or fn_bdstock (map), not both")
  end if
  if (len_trim(list%fn_bdstock) == 0 .and. list%bd_stock0 <= -9998.0) then
    call par_stop("list_bldgdebris: the building stock is required — specify " &
                  //"bd_stock0 (uniform, m3/m2) or fn_bdstock (map)")
  end if
  allocate(bd%wbs(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  if (len_trim(list%fn_bdstock) > 0) then
    call read_map_scatter(p, g, list%fn_bdstock, "fn_bdstock", 0.0, -1.0, bd%wbs)
  else
    if (list%bd_stock0 < 0.0) call par_stop("list_bldgdebris: bd_stock0 must be >= 0")
    bd%wbs(:,:) = list%bd_stock0
  end if
  ! 域外セル・海セルには家屋を置かない(台帳集計・出力と整合。ゾーン2 =
  ! sw は全域)
  do j = dcp%jsh, dcp%jeh
    do i = 1, g%nx
      if (g%x(i,j) <= 0 .or. g%sw(i,j) > 0) bd%wbs(i,j) = 0.0
    end do
  end do
  allocate(bd%wbs0(1:g%nx, dcp%jsh:dcp%jeh), source = bd%wbs)

  ! --- 破壊可能割合 fw(任意。空隙率帰還の上限。B2 が使う) ---
  if (len_trim(list%fn_bdfrac) > 0) then
    allocate(bd%fw(1:g%nx, dcp%jsh:dcp%jeh), source = 1.0)
    call read_map_scatter(p, g, list%fn_bdfrac, "fn_bdfrac", 0.0, 1.0, bd%fw)
  end if

  ! --- 状態の確保 ---
  allocate(s%hbd(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(s%wbd(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  if (p%f_out_wbd > 0) allocate(s%wbdmax(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  if (p%f_out_bds > 0) allocate(s%bds(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  if (p%f_out_fdmax > 0) allocate(s%fdmax(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)

  ! --- ダム捕捉台帳(全ダム・湖沼が対象。m_driftwood と同型) ---
  call setup_dams(bd, b)

  ! --- リスタート ---
  if (p%f_state_restore > 0) call restore_state(bd, p, g, s)
  if (allocated(s%bds)) call update_damage(bd, g, s)

  allocate(bd%vrow(dcp%js:dcp%je, 1:5), source = 0.0_real64)

  ! --- 診断 CSV(rank0。累積はラン先頭からの積算 = restore でリセット) ---
  if (is_root) then
    open(newunit=bd%un, file=trim(p%dir_result)//"/bldgdebris.csv", status='replace')
    write(bd%un, '(a)') "time_s,destroy_float_m3,destroy_sink_m3,deposit_m3,refloat_m3," &
                        //"to_dam_m3,vol_stock_m3,vol_float_m3,vol_deposit_m3"
  end if

  s%bd_active = .true.
  bd%enabled = .true.
  bd%initialized = .true.
  call par_info("building-debris module enabled")
end subroutine


!----------------------------------------------------------------------
! 分布ラスタの読み込み(rank0 読み+帯 scatter。使用セルの値域を検証。
! m_driftwood の read_stock_scatter と同型。vmax < 0 なら上限なし)
!----------------------------------------------------------------------
subroutine read_map_scatter(p, g, fn, label, vmin, vmax, a)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  character(len=*), intent(in) :: fn, label
  real, intent(in) :: vmin, vmax
  real, intent(inout) :: a(1:, dcp%jsh:)
  real, allocatable :: wk(:,:)
  real :: dum(1,1)
  character(:), allocatable :: fname
  character(len=1024) :: msg
  logical :: found
  integer :: i, j

  fname = trim(p%dir_data)//"/"//trim(fn)
  inquire(file=fname, exist=found)
  if (.not. found) call par_stop("list_bldgdebris: "//label//" not found: "//fname)

  if (is_root) then
    allocate(wk(1:g%nx, 1:g%ny))
    call par_info(" reading "//fname)
    call fileio_read_matrix(fname, g%nx, g%ny, wk, p%f_input_mode)
    do j = 1, g%ny
      do i = 1, g%nx
        if (g%x(i,j) <= 0) cycle
        if (wk(i,j) < vmin .or. (vmax >= 0.0 .and. wk(i,j) > vmax)) then
          write(msg,'(a,2i7,es12.4)') "list_bldgdebris: "//label//" has an out-of-range " &
                                      //"value at cell", i, j, wk(i,j)
          call par_abort(trim(msg))
        end if
      end do
    end do
    call par_scatter_cell(wk, a)
  else
    call par_scatter_cell(dum, a)
  end if
end subroutine


!----------------------------------------------------------------------
! ダム捕捉台帳の構築(全ダムの捕捉帯セル。自帯分のみ。m_driftwood と同型)
!----------------------------------------------------------------------
subroutine setup_dams(bd, b)
  type(t_bldgdebris), intent(inout) :: bd
  type(t_boundary), intent(in) :: b
  integer :: ist, nd, n, k, j

  nd = 0
  if (allocated(b%struct)) then
    do ist = 1, size(b%struct)
      if (b%struct(ist)%kind == e_struct_dam) nd = nd + 1
    end do
  end if
  bd%ndam = nd
  if (nd == 0) return

  allocate(bd%dam(1:nd))
  nd = 0
  do ist = 1, size(b%struct)
    if (b%struct(ist)%kind /= e_struct_dam) cycle
    nd = nd + 1
    bd%dam(nd)%ist = ist
    n = 0
    do k = 1, b%struct(ist)%ncin
      j = b%struct(ist)%cin(2,k)
      if (j >= dcp%js .and. j <= dcp%je) n = n + 1
    end do
    bd%dam(nd)%nc = n
    allocate(bd%dam(nd)%cells(1:2, 1:max(n,1)), source = 0)
    n = 0
    do k = 1, b%struct(ist)%ncin
      j = b%struct(ist)%cin(2,k)
      if (j < dcp%js .or. j > dcp%je) cycle
      n = n + 1
      bd%dam(nd)%cells(1,n) = b%struct(ist)%cin(1,k)
      bd%dam(nd)%cells(2,n) = j
    end do
  end do
end subroutine


!----------------------------------------------------------------------
! 破壊率 s%bds = 1 − wbs/wbs0 を全帯で更新する(出力用。restore 後と
! 破壊のあったセル)
!----------------------------------------------------------------------
subroutine update_damage(bd, g, s)
  type(t_bldgdebris), intent(in) :: bd
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: i, j
  do j = dcp%jsh, dcp%jeh
    do i = 1, g%nx
      if (bd%wbs0(i,j) > 0.0) then
        s%bds(i,j) = 1.0 - bd%wbs(i,j) / bd%wbs0(i,j)
      else
        s%bds(i,j) = 0.0
      end if
    end do
  end do
end subroutine


!----------------------------------------------------------------------
! 家屋破壊・瓦礫過程を適用する(毎ステップ。run_main が m_driftwood_calc
! の後に呼ぶ = 同一ステップの hd を荷重に見る)。
!   順序: (0) 荷重の評価 (1) 破壊 (2) 接地・乾燥堆積 (3) 再流動
!         (4) ダム捕捉 (5) 到達量統計
!   更新は自帯 js..je のセル内交換のみ(owner-compute。近傍を読まない
!   ため 2 パス不要 = §28.2 の適用外)。
!   無効時は no-op。冒頭の return 判定は全ランクで同一 = collective 安全
!----------------------------------------------------------------------
subroutine m_bldgdebris_calc(bd, p, g, s, it)
  type(t_bldgdebris), intent(inout) :: bd
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer, intent(in) :: it
  integer :: i, j, k, nd
  real :: hh, xl, x, c1, c2, fac, w, ws, wf, cf
  logical :: ramp

  if (it < 0) continue  ! 引数未使用の警告を抑制
  if (.not. bd%enabled) return

  !$omp parallel do schedule(dynamic) private(i, j, hh, xl, x, c1, c2, fac, w, ws, wf, cf, ramp)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      hh = s%h(i,j) + max(s%hs(i,j), 0.0)     ! 混合流動深(判定は h+hs。§50 と同じ)

      ! (0) 荷重 X = (h + (1+s)hs + sg_log·hd + sg_bd·hbd)·V²(清水規格化。
      !     F9999 と同じ基底。浮遊物は水と同速で移流する前提の付加質量)
      xl = 0.0
      if (bd%need_load) then
        xl = s%h(i,j) + (1.0 + s%sed_sgrav) * max(s%hs(i,j), 0.0)
        if (s%dw_active) xl = xl + s%dw_sg * s%hd(i,j)
        xl = (xl + bd%sg * s%hbd(i,j)) * s%vv(i,j)**2
        if (allocated(s%fdmax)) then
          if (xl > s%fdmax(i,j)) s%fdmax(i,j) = xl
        end if
      end if

      ! (1) 破壊: 判定量の閾値超過でレート破壊(第2閾値があれば線形ランプ)
      if (bd%wbs(i,j) > 0.0) then
        if (bd%crit == 1) then
          x = hh; c1 = bd%hcrit; c2 = bd%hcrit2; ramp = bd%have_hramp
        else
          x = xl; c1 = bd%fcrit; c2 = bd%fcrit2; ramp = bd%have_framp
        end if
        if (x > c1) then
          fac = 1.0
          if (ramp) fac = min(1.0, (x - c1) / (c2 - c1))
          w = min(bd%wbs(i,j), bd%wdes * fac * p%dt)
          if (w > 0.0) then
            bd%wbs(i,j) = bd%wbs(i,j) - w
            ws = bd%fsink * w                       ! 沈下分(堆積へ直行)
            wf = w - ws                             ! 浮遊分
            cf = colfac(s, i, j)
            s%hbd(i,j) = s%hbd(i,j) + wf / cf
            s%wbd(i,j) = s%wbd(i,j) + ws / cf
            bd%vrow(j,1) = bd%vrow(j,1) + vol_geo(g, wf)
            bd%vrow(j,2) = bd%vrow(j,2) + vol_geo(g, ws)
            if (allocated(s%bds)) s%bds(i,j) = 1.0 - bd%wbs(i,j) / bd%wbs0(i,j)
          end if
        end if
      end if

      ! (2) 接地・乾燥堆積: 喫水未満・低速でレート堆積、乾燥セルは全量
      if (s%hbd(i,j) > 0.0) then
        if (s%h(i,j) <= p%dd) then
          w = s%hbd(i,j)
        else if (hh < bd%hf .or. s%vv(i,j) < bd%vstop) then
          w = min(s%hbd(i,j), bd%wstop * p%dt)
        else
          w = 0.0
        end if
        if (w > 0.0) then
          s%hbd(i,j) = s%hbd(i,j) - w
          s%wbd(i,j) = s%wbd(i,j) + w
          bd%vrow(j,3) = bd%vrow(j,3) + vol_col(g, s, i, j, w)
        end if
      end if

      ! (3) 再流動: 浮遊余裕率つきの閾値超過でレート再流動(既定なし)
      if (bd%have_flt .and. s%wbd(i,j) > 0.0) then
        if (hh > bd%hfloat .and. s%vv(i,j) > bd%vfloat) then
          w = min(s%wbd(i,j), bd%wfloat * p%dt)
          s%wbd(i,j) = s%wbd(i,j) - w
          s%hbd(i,j) = s%hbd(i,j) + w
          bd%vrow(j,4) = bd%vrow(j,4) + vol_col(g, s, i, j, w)
        end if
      end if
    end do
  end do
  !$omp end parallel do

  ! (4) ダム捕捉帯の吸収(流動瓦礫はダム台帳へ。堆積 wbd は接地済みのため残す)
  do nd = 1, bd%ndam
    do k = 1, bd%dam(nd)%nc
      i = bd%dam(nd)%cells(1,k)
      j = bd%dam(nd)%cells(2,k)
      if (s%hbd(i,j) <= 0.0) cycle
      bd%vrow(j,5) = bd%vrow(j,5) + vol_col(g, s, i, j, s%hbd(i,j))
      s%hbd(i,j) = 0.0
    end do
  end do

  ! (5) 期間最大到達量 Bd9999 = max(hbd+wbd)(f_out_wbd 指定時のみ確保。
  !     save 対象外 = hmax 系と同じ意図的仕様。§7)
  if (allocated(s%wbdmax)) then
    !$omp parallel do schedule(static) private(i, j, w)
    do j = dcp%js, dcp%je
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0) cycle
        w = s%hbd(i,j) + s%wbd(i,j)
        if (w > s%wbdmax(i,j)) s%wbdmax(i,j) = w
      end do
    end do
    !$omp end parallel do
  end if
end subroutine


!----------------------------------------------------------------------
! セル (i,j) の柱状量→実材積の換算係数と換算(m3。real64)
!   柱状量の材積 = w × gv × wfrac × A(h・hd と同じ実効面積基底)、
!   幾何面積基底(wbs)の材積 = w × A
!----------------------------------------------------------------------
function colfac(s, i, j) result(f)
  type(t_state), intent(in) :: s
  integer, intent(in) :: i, j
  real :: f, wf
  wf = 1.0
  if (have_width) wf = wfrac(i,j)
  f = s%gv(i,j) * wf
end function

function vol_col(g, s, i, j, w) result(vol)
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer, intent(in) :: i, j
  real, intent(in) :: w
  real(real64) :: vol
  vol = real(w, real64) * real(colfac(s, i, j), real64) &
        * real(g%dx, real64) * real(g%dy, real64)
end function

function vol_geo(g, w) result(vol)
  type(t_geoinfo), intent(in) :: g
  real, intent(in) :: w
  real(real64) :: vol
  vol = real(w, real64) * real(g%dx, real64) * real(g%dy, real64)
end function


!----------------------------------------------------------------------
! 診断 CSV の出力(record 間隔。collective: 全ランクで呼ぶ)
!   現在貯留(ストック・流動・堆積)も台帳化(par_sum_rows = 決定的)。
!   系外流出は収支残差として利用者が導出する
!----------------------------------------------------------------------
subroutine m_bldgdebris_record(bd, p, g, s)
  type(t_bldgdebris), intent(inout) :: bd
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  real(real64) :: v(1:5), vstk, vflt, vdep
  real(real64) :: rows(dcp%js:dcp%je), rows2(dcp%js:dcp%je), rows3(dcp%js:dcp%je)
  integer :: i, j, k
  if (p%initialized) continue  ! 引数未使用の警告を抑制
  if (.not. bd%enabled) return

  do k = 1, 5
    call par_sum_rows(bd%vrow(:,k), v(k))
  end do
  rows(:) = 0.0_real64
  rows2(:) = 0.0_real64
  rows3(:) = 0.0_real64
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      rows(j) = rows(j) + vol_geo(g, bd%wbs(i,j))
      rows2(j) = rows2(j) + vol_col(g, s, i, j, s%hbd(i,j))
      rows3(j) = rows3(j) + vol_col(g, s, i, j, s%wbd(i,j))
    end do
  end do
  call par_sum_rows(rows, vstk)
  call par_sum_rows(rows2, vflt)
  call par_sum_rows(rows3, vdep)

  if (is_root .and. bd%un /= 0) then
    write(bd%un, '(f0.2,8(",",es15.7))') s%t, v(1), v(2), v(3), v(4), v(5), &
                                          vstk, vflt, vdep
    flush(bd%un)
  end if
end subroutine


!----------------------------------------------------------------------
! 内部状態の保存・復元(モジュール私有ファイル bldgdebris.dat。契約C。§7)
!   保存対象: s%hbd, s%wbd, wbs, wbs0(4成分固定)。wbdmax・fdmax は統計、
!   bds は導出量 = 対象外(restore 後に update_damage で再構成)
!----------------------------------------------------------------------
subroutine save_state(bd, p, g, s)
  type(t_bldgdebris), intent(in) :: bd
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  real, allocatable :: wk(:,:)
  integer :: un
  if (is_root) then
    allocate(wk(1:g%nx, 1:g%ny), source = 0.0)
  else
    allocate(wk(1, 1), source = 0.0)
  end if
  if (is_root) then
    call sysdep_mkdir(p%dir_save)
    open(newunit=un, file=trim(p%dir_save)//'/bldgdebris.dat', form='unformatted', &
         status='replace')
  end if
  call par_gather_to(wk, s%hbd)
  if (is_root) call fileio_write_rle(un, wk)
  call par_gather_to(wk, s%wbd)
  if (is_root) call fileio_write_rle(un, wk)
  call par_gather_to(wk, bd%wbs)
  if (is_root) call fileio_write_rle(un, wk)
  call par_gather_to(wk, bd%wbs0)
  if (is_root) then
    call fileio_write_rle(un, wk)
    close(un)
  end if
end subroutine


subroutine restore_state(bd, p, g, s)
  type(t_bldgdebris), intent(inout) :: bd
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, allocatable :: wk(:,:)
  real :: dum(1,1)
  character(:), allocatable :: fname
  logical :: found
  integer :: un

  ! 版・格子・精度の検証は m_state(check_save_info)が済ませている。
  ! 自ファイルの有無のみ確認(無ければ停止 — 意図しない材積消失を防ぐ)
  fname = trim(p%dir_save)//'/bldgdebris.dat'
  inquire(file=fname, exist=found)
  if (.not. found) then
    call par_stop("bldgdebris: state file not found (was fn_bldgdebris enabled " &
                  //"when saving): "//fname)
  end if

  if (is_root) then
    allocate(wk(1:g%nx, 1:g%ny), source = 0.0)
    open(newunit=un, file=fname, form='unformatted', status='old')
    call fileio_read_rle(un, wk)
    call par_scatter_cell(wk, s%hbd)
  else
    call par_scatter_cell(dum, s%hbd)
  end if
  if (is_root) then
    call fileio_read_rle(un, wk)
    call par_scatter_cell(wk, s%wbd)
  else
    call par_scatter_cell(dum, s%wbd)
  end if
  if (is_root) then
    call fileio_read_rle(un, wk)
    call par_scatter_cell(wk, bd%wbs)
  else
    call par_scatter_cell(dum, bd%wbs)
  end if
  if (is_root) then
    call fileio_read_rle(un, wk)
    call par_scatter_cell(wk, bd%wbs0)
    close(un)
  else
    call par_scatter_cell(dum, bd%wbs0)
  end if
end subroutine


!----------------------------------------------------------------------
! 家屋破壊・瓦礫モジュールを破棄する(save は dispose で行う。契約C)
!----------------------------------------------------------------------
subroutine m_bldgdebris_dispose(bd, p, g, s)
  type(t_bldgdebris), intent(inout) :: bd
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  if (.not. bd%enabled) return
  if (p%f_state_save > 0) call save_state(bd, p, g, s)
  if (is_root .and. bd%un /= 0) close(bd%un)
  bd%un = 0
  if (allocated(bd%wbs)) deallocate(bd%wbs)
  if (allocated(bd%wbs0)) deallocate(bd%wbs0)
  if (allocated(bd%fw)) deallocate(bd%fw)
  if (allocated(bd%dam)) deallocate(bd%dam)
  if (allocated(bd%vrow)) deallocate(bd%vrow)
  bd%enabled = .false.
  bd%initialized = .false.
end subroutine

end module
