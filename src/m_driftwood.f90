module m_driftwood
  ! ================= 流木プロセスモジュール(§50) =================
  ! 流木をセルごとの柱状材積 (m3/m2 = m) のオイラー的なラスタ場として
  ! 概算する加算的プロセス。個別流木のラグランジュ追跡・幾何的閉塞・
  ! 衝突力は対象外(§0 方針2。docs/driftwood_plan.md §1)。
  !   台帳:   立木ストック wst(私有。幾何面積基底 m3/m2)→ 流木化 →
  !           流動流木 s%hd(柱状量。貯留の意味論は h・hs と同一)→
  !           接地・乾燥 → 堆積流木 s%wd(柱状量。再流動あり)
  !   輸送:   浮遊砂と同じ保存輸送カーネル(advect_scalar)を swflow_enc が
  !           ステップ内で実行(s%dw_active)。本モジュールは発生・停止・
  !           再流動・台帳・診断を担う(セル局所のみ = エッジ・ハロ・
  !           collective 不要)
  !   有効化: fn_driftwood の指定(&list_driftwood。f_dw=0 で一時無効化)。
  !           ENC 格子のみ。無効時はメモリ・CPU ゼロ追加
  !   発生:   (a) 水理的流失 — wst>0 かつ h+hs>dw_hrec かつ vv>dw_vrec で
  !           wst→hd をレート dw_wrec(数値的閉包【独自】・閾値
  !           【要文献照合】)。(b) 侵食連行 — 累積侵食深 zref−z が根系深
  !           dw_droot を超えたセルの wst 全量→hd(zref は init 時 z の
  !           私有写し。z 低下の事実だけを見るため f_fluvial/f_debris/
  !           f_slide/f_release のどの侵食・崩壊とも自動連動)
  !   停止:   喫水 hf = 円柱の浮力平衡の厳密解(Braudrick & Grant 2000
  !           式(23)(6)。sg・D の線形近似でなく円形セグメント面積で解く)。
  !           h+hs < hf または vv < dw_vstop で hd→wd をレート dw_wstop
  !           (f_dbstop=1 と同型の数値的閉包)。乾燥セル(h≤dd)は全量。
  !           再流動は h+hs > dw_rfloat・hf かつ vv > dw_vfloat で wd→hd
  !           レート dw_wfloat(既定 0 = なし)。wd は z に足さない
  !   運動量: 流木の運動量・抵抗への算入はしない(第1段。§50)
  !   ダム:   捕捉帯セルは毎ステップ全量吸収されるため、流動流木 hd も
  !           同伴してダム別台帳へ移す(m_wq と同じ契約。放流流木 0 =
  !           既知の妥協。堆積 wd は接地済みのため残す)
  !   save:   s%hd, s%wd, wst, zref をモジュール私有ファイル driftwood.dat
  !           で保存(§7 の契約C。state.dat の形式は不変)
  !   診断:   result/driftwood.csv(発生・堆積・再流動・ダム捕捉の累積と
  !           現在貯留。系外流出は収支残差。rank0、dt_recrd 間隔。
  !           総和は par_sum_rows = 決定的)
  !   出力:   f_out_hd(流動 Hd0001…)、f_out_wd(堆積 Wd0001… +
  !           期間最大到達量 Wd9999 = max(hd+wd)。統計は save 対象外)
  ! ================================================================
  use iso_fortran_env, only : real64
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use m_boundary, only : t_boundary, e_struct_dam
  use list_driftwood, only : t_list_driftwood, list_driftwood_read
  use m_swflow_enc, only : have_width, wfrac
  use m_fileio, only : fileio_write_rle, fileio_read_rle, fileio_read_matrix
  use m_sysdep_util, only : sysdep_mkdir
  use m_parallel, only : dcp, is_root, par_info, par_stop, par_abort, par_sum_rows, &
                         par_gather_to, par_scatter_cell
  implicit none
  private
  public :: t_driftwood
  public :: m_driftwood_init
  public :: m_driftwood_calc
  public :: m_driftwood_record
  public :: m_driftwood_dispose

  ! ダム捕捉台帳(m_wq の t_wqdam と同型)
  type t_dwdam
    integer :: ist = 0                   ! b%struct のインデックス
    integer :: nc = 0                    ! 自帯内の捕捉帯セル数
    integer, allocatable :: cells(:,:)
  end type

  type t_driftwood
    ! init に早期 return 経路があるため全成分デフォルト初期化必須(§13)
    logical :: enabled = .false.
    logical :: initialized = .false.
    real :: hf = 0.0                     ! 喫水 (m)。円柱の浮力平衡の厳密解
                                         !   (B&G2000 式(23)(6)。init で二分法)
    logical :: have_hyd = .false.        ! 水理的流失の有効
    real :: wrec = 0.0                   ! 水理的流失レート (m/s)
    real :: hrec = 0.0                   ! 水理的流失の水深閾値 (m。h+hs)
    real :: vrec = 0.0                   ! 水理的流失の流速閾値 (m/s)
    logical :: have_ero = .false.        ! 侵食連行の有効
    real :: droot = 0.0                  ! 根系深 (m)
    real :: wstop = 0.0                  ! 接地堆積レート (m/s)
    real :: vstop = 0.0                  ! 低速堆積の流速閾値 (m/s。0=水深のみ)
    logical :: have_flt = .false.        ! 再流動の有効
    real :: wfloat = 0.0                 ! 再流動レート (m/s)
    real :: hfloat = 0.0                 ! 再流動の水深閾値 (m) = dw_rfloat・hf(導出)
    real :: vfloat = 0.0                 ! 再流動の流速閾値 (m/s)
    real, allocatable :: wst(:,:)        ! 立木ストック (m3/m2。幾何面積基底 =
                                         !   セル内材積 wst×A。帯 jsh:jeh で確保
                                         !   するが更新・参照は js:je のみ)
    real, allocatable :: zref(:,:)       ! 侵食連行の基準地形 (m。init 時 z の写し)
    integer :: ndam = 0
    type(t_dwdam), allocatable :: dam(:)
    ! 診断(行部分和 real64。材積 m3)
    real(real64), allocatable :: vrow(:,:)  ! (js:je, 1:5) 1=水理的流失 2=侵食連行
                                            !   3=堆積(hd→wd) 4=再流動(wd→hd)
                                            !   5=ダム捕捉
    integer :: un = 0                    ! CSV 装置番号(rank0)
  end type

contains


!----------------------------------------------------------------------
! 流木モジュールを初期化する
!   fn_driftwood 未指定 or f_dw=0 なら何もしない(enabled = .false.)。
!   s%dw_active を立てるため swflow init より前・m_geomorph_init より後
!   (morfac の検査に s%geo_morfac を使う)に呼ぶこと。
!   セル検証はゾーン2(全域 x/sw が使える帯縮小前)で行う
!----------------------------------------------------------------------
subroutine m_driftwood_init(dw, p, g, b, s)
  type(t_driftwood), intent(out) :: dw
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(in) :: b      ! ダム捕捉台帳の構築
  type(t_state), intent(inout) :: s      ! hd/wd の確保と dw_active
  type(t_list_driftwood) :: list
  integer :: j

  if (len_trim(p%fn_driftwood) == 0) then
    ! 流木出力は本モジュールが前提(§28.9 の f_out_hs と同じ様式)
    if (p%f_out_hd > 0 .or. p%f_out_wd > 0) then
      call par_stop("list_sysparam: f_out_hd/f_out_wd require the driftwood module " &
                    //"(fn_driftwood)")
    end if
    return
  end if
  if (p%f_gridsystem /= 0) then
    call par_stop("list_driftwood: the driftwood module supports the ENC grid only " &
                  //"(same restriction as suspended sediment)")
  end if

  call list_driftwood_read(p, list)
  if (list%f_dw == 0) then      ! fn を書いたまま一時無効化する経路
    if (p%f_out_hd > 0 .or. p%f_out_wd > 0) then
      call par_stop("list_sysparam: f_out_hd/f_out_wd require the driftwood module " &
                    //"(f_dw=0 disables it)")
    end if
    return
  end if

  ! --- 代表諸元(喫水の実体。必須) ---
  if (list%dw_dlog <= -9998.0) call par_stop("list_driftwood: dw_dlog (m) is required")
  if (list%dw_dlog <= 0.0) call par_stop("list_driftwood: dw_dlog must be > 0")
  if (list%dw_sglog <= -9998.0) call par_stop("list_driftwood: dw_sglog is required")
  if (list%dw_sglog <= 0.0 .or. list%dw_sglog >= 1.0) then
    call par_stop("list_driftwood: dw_sglog must be in (0,1) — the module assumes " &
                  //"floatable wood (sinking logs are out of scope)")
  end if
  ! 喫水(浮遊限界水深)d_b: 円柱の浮力平衡 ρlog・πD²/4 = ρw・A_sub(d_b)
  ! (Braudrick & Grant 2000, WRR 36(2), 式(23)(6))。A_sub は円形断面の
  ! 水没セグメント面積で、面積率 f(x) = (θ − sinθ)/(2π)、θ = 2acos(1−2x)、
  ! x = d/D。f(x) = sg を二分法で解く(単調増加。全ランク同一演算 =
  ! 決定的。sg=0.5 は x=0.5 の厳密対称解)
  block
    real :: xlo, xhi, xm, th
    integer :: k2
    xlo = 0.0
    xhi = 1.0
    do k2 = 1, 60
      xm = 0.5 * (xlo + xhi)
      th = 2.0 * acos(1.0 - 2.0 * xm)
      if ((th - sin(th)) / (2.0 * acos(-1.0)) < list%dw_sglog) then
        xlo = xm
      else
        xhi = xm
      end if
    end do
    dw%hf = 0.5 * (xlo + xhi) * list%dw_dlog
  end block

  ! --- 発生(少なくとも一方が必須) ---
  if (list%dw_wrec > -9998.0) then
    if (list%dw_wrec <= 0.0) call par_stop("list_driftwood: dw_wrec must be > 0")
    if (list%dw_hrec <= -9998.0 .or. list%dw_vrec <= -9998.0) then
      call par_stop("list_driftwood: dw_wrec requires dw_hrec (m) and dw_vrec (m/s)")
    end if
    if (list%dw_hrec < 0.0) call par_stop("list_driftwood: dw_hrec must be >= 0")
    if (list%dw_vrec < 0.0) call par_stop("list_driftwood: dw_vrec must be >= 0")
    dw%wrec = list%dw_wrec
    dw%hrec = list%dw_hrec
    dw%vrec = list%dw_vrec
    dw%have_hyd = .true.
  end if
  if (list%dw_droot > -9998.0) then
    if (list%dw_droot <= 0.0) call par_stop("list_driftwood: dw_droot must be > 0")
    dw%droot = list%dw_droot
    dw%have_ero = .true.
  end if
  if (.not. (dw%have_hyd .or. dw%have_ero)) then
    call par_stop("list_driftwood: no recruitment process — specify dw_wrec " &
                  //"(hydraulic) and/or dw_droot (erosion entrainment)")
  end if

  ! --- 停止・堆積(必須)---
  if (list%dw_wstop <= -9998.0) call par_stop("list_driftwood: dw_wstop (m/s) is required")
  if (list%dw_wstop <= 0.0) call par_stop("list_driftwood: dw_wstop must be > 0")
  dw%wstop = list%dw_wstop
  if (list%dw_vstop < 0.0) call par_stop("list_driftwood: dw_vstop must be >= 0")
  dw%vstop = list%dw_vstop

  ! --- 再流動(既定 dw_wfloat=0 = なし。ヒステリシスの検証つき)---
  if (list%dw_wfloat < 0.0) call par_stop("list_driftwood: dw_wfloat must be >= 0")
  if (list%dw_wfloat > 0.0) then
    if (list%dw_rfloat <= 1.0) then
      call par_stop("list_driftwood: dw_rfloat must be > 1 (hysteresis against " &
                    //"per-step deposit/refloat oscillation)")
    end if
    if (list%dw_vfloat <= -9998.0) then
      call par_stop("list_driftwood: dw_wfloat requires dw_vfloat (m/s)")
    end if
    if (list%dw_vfloat < dw%vstop) then
      call par_stop("list_driftwood: dw_vfloat must be >= dw_vstop (hysteresis)")
    end if
    dw%wfloat = list%dw_wfloat
    dw%hfloat = list%dw_rfloat * dw%hf
    dw%vfloat = list%dw_vfloat
    dw%have_flt = .true.
  end if

  ! --- 流木はイベント量であり地形時間の加速と整合しない(f_debris と同じ) ---
  if (s%geo_morfac /= 0.0 .and. s%geo_morfac /= 1.0) then
    call par_stop("list_driftwood: the driftwood module requires morfac=1 " &
                  //"(event-scale computation)")
  end if

  ! --- 立木ストック(一様 dw_stock0 か分布 fn_dwstock の排他でどちらか
  !     必須。分布は rank0 読み+帯 scatter。方式2) ---
  if (len_trim(list%fn_dwstock) > 0 .and. list%dw_stock0 > -9998.0) then
    call par_stop("list_driftwood: specify the standing stock by either dw_stock0 " &
                  //"(uniform) or fn_dwstock (map), not both")
  end if
  if (len_trim(list%fn_dwstock) == 0 .and. list%dw_stock0 <= -9998.0) then
    call par_stop("list_driftwood: the standing stock is required — specify " &
                  //"dw_stock0 (uniform, m3/m2) or fn_dwstock (map)")
  end if
  allocate(dw%wst(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  if (len_trim(list%fn_dwstock) > 0) then
    call read_stock_scatter(p, g, list%fn_dwstock, dw%wst)
  else
    if (list%dw_stock0 < 0.0) call par_stop("list_driftwood: dw_stock0 must be >= 0")
    dw%wst(:,:) = list%dw_stock0
    ! 域外セルにはストックを置かない(台帳集計・出力と整合)
    block
      integer :: i3, j3
      do j3 = dcp%jsh, dcp%jeh
        do i3 = 1, g%nx
          if (g%x(i3,j3) <= 0) dw%wst(i3,j3) = 0.0
        end do
      end do
    end block
  end if
  ! 海セルには立木を置かない(発生の sw 除外と整合。ゾーン2 = sw は全域)
  block
    integer :: i2, j2
    do j2 = dcp%jsh, dcp%jeh
      do i2 = 1, g%nx
        if (g%sw(i2,j2) > 0) dw%wst(i2,j2) = 0.0
      end do
    end do
  end block

  ! --- 状態の確保 ---
  allocate(s%hd(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(s%wd(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  if (p%f_out_wd > 0) then
    allocate(s%wdmax(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  end if
  ! 侵食連行の基準地形(init 時 z の写し。海セルの潮位追随 z は
  ! 対象外セルのため影響しない)
  allocate(dw%zref(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  do j = dcp%jsh, dcp%jeh
    dw%zref(:,j) = s%z(:,j)
  end do

  ! --- ダム捕捉台帳(全ダム・湖沼が対象。m_wq と同型) ---
  call setup_dams(dw, b)

  ! --- リスタート ---
  if (p%f_state_restore > 0) call restore_state(dw, p, g, s)

  allocate(dw%vrow(dcp%js:dcp%je, 1:5), source = 0.0_real64)

  ! --- 診断 CSV(rank0。累積はラン先頭からの積算 = restore でリセット) ---
  if (is_root) then
    open(newunit=dw%un, file=trim(p%dir_result)//"/driftwood.csv", status='replace')
    write(dw%un, '(a)') "time_s,rec_hyd_m3,rec_ero_m3,deposit_m3,refloat_m3,to_dam_m3," &
                        //"vol_stock_m3,vol_float_m3,vol_deposit_m3"
  end if

  s%dw_active = .true.
  dw%enabled = .true.
  dw%initialized = .true.
  call par_info("driftwood module enabled")
end subroutine


!----------------------------------------------------------------------
! 立木ストック分布の読み込み(rank0 読み+帯 scatter。使用セルの負値は
! エラー。m_wq の read_map_scatter と同型)
!----------------------------------------------------------------------
subroutine read_stock_scatter(p, g, fn, a)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  character(len=*), intent(in) :: fn
  real, intent(inout) :: a(1:, dcp%jsh:)
  real, allocatable :: wk(:,:)
  real :: dum(1,1)
  character(:), allocatable :: fname
  character(len=1024) :: msg
  logical :: found
  integer :: i, j

  fname = trim(p%dir_data)//"/"//trim(fn)
  inquire(file=fname, exist=found)
  if (.not. found) call par_stop("list_driftwood: fn_dwstock not found: "//fname)

  if (is_root) then
    allocate(wk(1:g%nx, 1:g%ny))
    call par_info(" reading "//fname)
    call fileio_read_matrix(fname, g%nx, g%ny, wk, p%f_input_mode)
    do j = 1, g%ny
      do i = 1, g%nx
        if (g%x(i,j) <= 0) cycle
        if (wk(i,j) < 0.0) then
          write(msg,'(a,2i7,es12.4)') "list_driftwood: fn_dwstock has a negative " &
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
! ダム捕捉台帳の構築(全ダムの捕捉帯セル。自帯分のみ。m_wq と同型)
!----------------------------------------------------------------------
subroutine setup_dams(dw, b)
  type(t_driftwood), intent(inout) :: dw
  type(t_boundary), intent(in) :: b
  integer :: ist, nd, n, k, j

  nd = 0
  if (allocated(b%struct)) then
    do ist = 1, size(b%struct)
      if (b%struct(ist)%kind == e_struct_dam) nd = nd + 1
    end do
  end if
  dw%ndam = nd
  if (nd == 0) return

  allocate(dw%dam(1:nd))
  nd = 0
  do ist = 1, size(b%struct)
    if (b%struct(ist)%kind /= e_struct_dam) cycle
    nd = nd + 1
    dw%dam(nd)%ist = ist
    n = 0
    do k = 1, b%struct(ist)%ncin
      j = b%struct(ist)%cin(2,k)
      if (j >= dcp%js .and. j <= dcp%je) n = n + 1
    end do
    dw%dam(nd)%nc = n
    allocate(dw%dam(nd)%cells(1:2, 1:max(n,1)), source = 0)
    n = 0
    do k = 1, b%struct(ist)%ncin
      j = b%struct(ist)%cin(2,k)
      if (j < dcp%js .or. j > dcp%je) cycle
      n = n + 1
      dw%dam(nd)%cells(1,n) = b%struct(ist)%cin(1,k)
      dw%dam(nd)%cells(2,n) = j
    end do
  end do
end subroutine


!----------------------------------------------------------------------
! 流木過程を適用する(毎ステップ。run_main が geomorph calc の後に呼ぶ =
! 同一ステップの z 更新を見た侵食連行)。
!   順序: (1) 侵食連行 (2) 水理的流失 (3) 接地・乾燥堆積 (4) 再流動
!         (5) ダム捕捉 (6) 到達量統計
!   更新は自帯 js..je のセル内交換のみ(owner-compute。近傍を読まない
!   ため 2 パス不要 = §28.2 の適用外)。
!   無効時は no-op。冒頭の return 判定は全ランクで同一 = collective 安全
!----------------------------------------------------------------------
subroutine m_driftwood_calc(dw, p, g, s, it)
  type(t_driftwood), intent(inout) :: dw
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer, intent(in) :: it
  integer :: i, j, k, nd
  real :: hh, w

  if (it < 0) continue  ! 引数未使用の警告を抑制
  if (.not. dw%enabled) return

  !$omp parallel do schedule(dynamic) private(i, j, hh, w)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      hh = s%h(i,j) + max(s%hs(i,j), 0.0)     ! 混合流動深(判定は h+hs。§50)

      ! (1) 侵食連行: 累積侵食深が根系深を超えたら立木は根系ごと全量流失
      !     (どの侵食・崩壊プロセスの z 低下でも効く。発生後は wst=0 =
      !     再判定は自然に停止)
      if (dw%have_ero .and. dw%wst(i,j) > 0.0) then
        if (dw%zref(i,j) - s%z(i,j) > dw%droot) then
          w = dw%wst(i,j)
          dw%wst(i,j) = 0.0
          s%hd(i,j) = s%hd(i,j) + w / colfac(g, i, j)
          dw%vrow(j,2) = dw%vrow(j,2) + vol_geo(g, w)
        end if
      end if

      ! (2) 水理的流失: 浸水深・流速の閾値超過でレート流失
      !     (レート式は数値的閉包【独自】、閾値は【要文献照合】。§50)
      if (dw%have_hyd .and. dw%wst(i,j) > 0.0) then
        if (hh > dw%hrec .and. s%vv(i,j) > dw%vrec) then
          w = min(dw%wst(i,j), dw%wrec * p%dt)
          dw%wst(i,j) = dw%wst(i,j) - w
          s%hd(i,j) = s%hd(i,j) + w / colfac(g, i, j)
          dw%vrow(j,1) = dw%vrow(j,1) + vol_geo(g, w)
        end if
      end if

      ! (3) 接地・乾燥堆積: 喫水未満・低速でレート堆積、乾燥セルは全量
      !     (suspend の乾燥繰り入れと同型)
      if (s%hd(i,j) > 0.0) then
        if (s%h(i,j) <= p%dd) then
          w = s%hd(i,j)
        else if (hh < dw%hf .or. s%vv(i,j) < dw%vstop) then
          w = min(s%hd(i,j), dw%wstop * p%dt)
        else
          w = 0.0
        end if
        if (w > 0.0) then
          s%hd(i,j) = s%hd(i,j) - w
          s%wd(i,j) = s%wd(i,j) + w
          dw%vrow(j,3) = dw%vrow(j,3) + vol_col(g, i, j, w)
        end if
      end if

      ! (4) 再流動: 浮遊余裕率つきの閾値超過でレート再流動(既定なし。
      !     ヒステリシス rfloat>1・vfloat>=vstop は init が検証済み)
      if (dw%have_flt .and. s%wd(i,j) > 0.0) then
        if (hh > dw%hfloat .and. s%vv(i,j) > dw%vfloat) then
          w = min(s%wd(i,j), dw%wfloat * p%dt)
          s%wd(i,j) = s%wd(i,j) - w
          s%hd(i,j) = s%hd(i,j) + w
          dw%vrow(j,4) = dw%vrow(j,4) + vol_col(g, i, j, w)
        end if
      end if
    end do
  end do
  !$omp end parallel do

  ! (5) ダム捕捉帯の吸収(水は毎ステップ全量吸収されるため流動流木も
  !     同伴してダム台帳へ。堆積 wd は接地済みのため残す。§50)
  do nd = 1, dw%ndam
    do k = 1, dw%dam(nd)%nc
      i = dw%dam(nd)%cells(1,k)
      j = dw%dam(nd)%cells(2,k)
      if (s%hd(i,j) <= 0.0) cycle
      dw%vrow(j,5) = dw%vrow(j,5) + vol_col(g, i, j, s%hd(i,j))
      s%hd(i,j) = 0.0
    end do
  end do

  ! (6) 期間最大到達量 Wd9999 = max(hd+wd)(f_out_wd 指定時のみ確保。
  !     save 対象外 = hmax 系と同じ意図的仕様。§7)
  if (allocated(s%wdmax)) then
    !$omp parallel do schedule(static) private(i, j, w)
    do j = dcp%js, dcp%je
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0) cycle
        w = s%hd(i,j) + s%wd(i,j)
        if (w > s%wdmax(i,j)) s%wdmax(i,j) = w
      end do
    end do
    !$omp end parallel do
  end if
end subroutine


!----------------------------------------------------------------------
! セル (i,j) の柱状量→実材積の換算係数と換算(m3。real64)
!   柱状量の材積 = w × gv × wfrac × A(h・hs と同じ実効面積基底)、
!   幾何面積基底(wst)の材積 = w × A
!----------------------------------------------------------------------
function colfac(g, i, j) result(f)
  type(t_geoinfo), intent(in) :: g
  integer, intent(in) :: i, j
  real :: f, wf
  wf = 1.0
  if (have_width) wf = wfrac(i,j)
  f = g%gv(i,j) * wf
end function

function vol_col(g, i, j, w) result(vol)
  type(t_geoinfo), intent(in) :: g
  integer, intent(in) :: i, j
  real, intent(in) :: w
  real(real64) :: vol
  vol = real(w, real64) * real(colfac(g, i, j), real64) &
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
!   系外流出は収支残差として利用者が導出する(初期ストック総量 −
!   全項目の和)
!----------------------------------------------------------------------
subroutine m_driftwood_record(dw, p, g, s)
  type(t_driftwood), intent(inout) :: dw
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  real(real64) :: v(1:5), vstk, vflt, vdep
  real(real64) :: rows(dcp%js:dcp%je), rows2(dcp%js:dcp%je), rows3(dcp%js:dcp%je)
  integer :: i, j, k
  if (p%initialized) continue  ! 引数未使用の警告を抑制
  if (.not. dw%enabled) return

  do k = 1, 5
    call par_sum_rows(dw%vrow(:,k), v(k))
  end do
  rows(:) = 0.0_real64
  rows2(:) = 0.0_real64
  rows3(:) = 0.0_real64
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      rows(j) = rows(j) + vol_geo(g, dw%wst(i,j))
      rows2(j) = rows2(j) + vol_col(g, i, j, s%hd(i,j))
      rows3(j) = rows3(j) + vol_col(g, i, j, s%wd(i,j))
    end do
  end do
  call par_sum_rows(rows, vstk)
  call par_sum_rows(rows2, vflt)
  call par_sum_rows(rows3, vdep)

  if (is_root .and. dw%un /= 0) then
    write(dw%un, '(f0.2,8(",",es15.7))') s%t, v(1), v(2), v(3), v(4), v(5), &
                                          vstk, vflt, vdep
    flush(dw%un)
  end if
end subroutine


!----------------------------------------------------------------------
! 内部状態の保存・復元(モジュール私有ファイル driftwood.dat。契約C。§7)
!   保存対象: s%hd, s%wd, wst, zref(4成分固定)。wdmax は統計 = 対象外
!----------------------------------------------------------------------
subroutine save_state(dw, p, g, s)
  type(t_driftwood), intent(in) :: dw
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
    open(newunit=un, file=trim(p%dir_save)//'/driftwood.dat', form='unformatted', &
         status='replace')
  end if
  call par_gather_to(wk, s%hd)
  if (is_root) call fileio_write_rle(un, wk)
  call par_gather_to(wk, s%wd)
  if (is_root) call fileio_write_rle(un, wk)
  call par_gather_to(wk, dw%wst)
  if (is_root) call fileio_write_rle(un, wk)
  call par_gather_to(wk, dw%zref)
  if (is_root) then
    call fileio_write_rle(un, wk)
    close(un)
  end if
end subroutine


subroutine restore_state(dw, p, g, s)
  type(t_driftwood), intent(inout) :: dw
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
  fname = trim(p%dir_save)//'/driftwood.dat'
  inquire(file=fname, exist=found)
  if (.not. found) then
    call par_stop("driftwood: state file not found (was fn_driftwood enabled " &
                  //"when saving): "//fname)
  end if

  if (is_root) then
    allocate(wk(1:g%nx, 1:g%ny), source = 0.0)
    open(newunit=un, file=fname, form='unformatted', status='old')
    call fileio_read_rle(un, wk)
    call par_scatter_cell(wk, s%hd)
  else
    call par_scatter_cell(dum, s%hd)
  end if
  if (is_root) then
    call fileio_read_rle(un, wk)
    call par_scatter_cell(wk, s%wd)
  else
    call par_scatter_cell(dum, s%wd)
  end if
  if (is_root) then
    call fileio_read_rle(un, wk)
    call par_scatter_cell(wk, dw%wst)
  else
    call par_scatter_cell(dum, dw%wst)
  end if
  if (is_root) then
    call fileio_read_rle(un, wk)
    call par_scatter_cell(wk, dw%zref)
    close(un)
  else
    call par_scatter_cell(dum, dw%zref)
  end if
end subroutine


!----------------------------------------------------------------------
! 流木モジュールを破棄する(save は dispose で行う。契約C)
!----------------------------------------------------------------------
subroutine m_driftwood_dispose(dw, p, g, s)
  type(t_driftwood), intent(inout) :: dw
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  if (.not. dw%enabled) return
  if (p%f_state_save > 0) call save_state(dw, p, g, s)
  if (is_root .and. dw%un /= 0) close(dw%un)
  dw%un = 0
  if (allocated(dw%wst)) deallocate(dw%wst)
  if (allocated(dw%zref)) deallocate(dw%zref)
  if (allocated(dw%dam)) deallocate(dw%dam)
  if (allocated(dw%vrow)) deallocate(dw%vrow)
  dw%enabled = .false.
  dw%initialized = .false.
end subroutine

end module
