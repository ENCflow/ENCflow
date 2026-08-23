module m_lavaflow
  ! ================= 溶岩流プロセスモジュール =================
  ! 噴火口セル群からの湧き出し・深さ平均 Bingham 粘性重力流(潤滑近似の
  ! 非線形拡散)・不動セルの固化(→ s%z)を担う。fn_lavaflow の指定で
  ! 有効化(&list_lavaflow。f_lavaflow=0 で一時無効化)。無効時は s%hl を
  ! 確保せず呼び出しもしない(ゼロコスト。§0)。設計・検証・既知の妥協の
  ! 正本は docs/lava_plan.md。
  !
  ! 【状態】 s%hl = 溶岩厚 (m 溶岩柱。幾何面積基底)。
  !   リスタートはモデル私有ファイル lavaflow.dat(RLE。契約5)。
  !
  ! 【定式(等温 Bingham 潤滑流。lava_plan.md §3)】
  !   溶岩面 s = z + hl、面勾配 S = |Δs|/dist、降伏最小厚 h0 = τ_y/(ρgS)。
  !   エッジ単位幅フラックス(he = エッジ平均厚、hf = he−h0):
  !     q = (ρgS/6η)・hf²・(2he+h0)   (hf > 0。τ_y=0 で q = ρgS he³/3η)
  !   拡散形 q = D・Δs/dist、D = (ρg/6η) hf² (2he+h0) として glacier の
  !   SIA と同じ保存形2ループ+ドナー律速+適応サブサイクリングに乗せる。
  !
  ! 【毎 dt_lavaflow tick の処理(順序が契約)】
  !   (1) 噴火口ソース: 噴出率 Q(t)(時系列補間)をセル集合へ均等分配
  !       (柱状 m。owner-compute。運動量なし)
  !   (2) s%hl のハロ交換(注入の帯更新を配布)
  !   (3) Bingham 拡散流動: サブサイクルごとに D_max の allreduce_max から
  !       dt_sub を決定(全ランク同一 = collective 安全)。エッジ流量は
  !       ドナー律速(1エッジ ≤ ドナー溶岩体積の 1/4)で hl>=0 を構造的に
  !       保証。サブサイクルごとに hl のハロ交換
  !   (4) 固化(lv_wsol > 0 のとき): エッジ深さ平均速度の最大が lv_vsol
  !       未満の「停止セル」の hl をレート lv_wsol で s%z へ転換
  !       (sd は増やさない = 侵食されない岩盤)。e 回復と s%z のハロ交換
  !       まで済ませる。速度閾値+レートは f_dbstop=1(db_vstop/db_wstop)
  !       と同じ閉じ方 — Bingham の停止は漸近的(q→0 だが有限時間で 0 に
  !       ならない)ため、厳密なフラックス 0 判定では固化が発火しない。
  !       再流動なし(固化は不可逆)。数値的閉包であり温度による固化は
  !       段階2(lava_plan.md §8)。判定はパス1が時刻 n の場から行い
  !       パス2が適用する(近傍参照とその場更新の競合対策。glacier の
  !       tick_erosion と同型)
  !
  ! 【水との関係(抽象化)】
  !   地表水 s%h は流動中の溶岩に不可視で z の上を流れる(glacier §5 と
  !   同じ割り切り)。固化した分だけ z が上がるので、固化後の水理は
  !   自動的に新地形に従う。海セルとは無フラックス(海没は対象外)。
  !
  ! MPI 規約(developer.md §11):
  !   - s%hl / s%z の更新は自帯 js..je のみ(owner-compute)。エッジ計算の
  !     帯界面は冗長計算(ハロ入力からビット厳密に配布)
  !   - enabled / tick / サブサイクル数の判定は全ランク同一(collective 安全)
  !   - 台帳(噴出・固化・残存)は dispose で allreduce_sumr し root が報告
  ! ==============================================================
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use m_boundary, only : interp_series, read_cell_file2, read_val_file2
  use list_lavaflow, only : t_list_lavaflow, list_lavaflow_read, &
                            lvmax, lvcmax, lvvmax, lv_cell, lv_val
  use m_fileio, only : fileio_write_rle, fileio_read_rle
  use m_sysdep_util, only : sysdep_mkdir
  use m_parallel, only : par_info, par_stop, dcp, is_root, &
                         par_halo_cell, par_allreduce_max, par_allreduce_sumr, &
                         par_gather_to, par_scatter_cell
  use m_util, only : itoa, rtoa, str2sec
  implicit none
  private

  public :: t_lavaflow
  public :: m_lavaflow_init
  public :: m_lavaflow_calc
  public :: m_lavaflow_dispose

  ! 8近傍の規約(m_glacier / m_geomorph と同一。k=1..4 が所有エッジ成分、
  ! k=5..8 は近傍の所有。9-k が反対向き)
  integer, parameter :: din(1:8) = [ -1,  0,  1, -1,  1, -1,  0,  1]
  integer, parameter :: djn(1:8) = [ -1, -1, -1,  0,  0,  1,  1,  1]
  integer, parameter :: die(1:8) = [ -1,  0,  0, -1,  0, -1,  0,  0]
  integer, parameter :: dje(1:8) = [ -1, -1, -1,  0,  0,  0,  0,  0]
  integer, parameter :: ke(1:8) = [ 1, 2, 3, 4, 4, 3, 2, 1]
  real, parameter :: sign_e(1:8) = [1., 1., 1., 1., -1., -1., -1., -1.]

  type t_lavaflow
    ! init に早期 return 経路があるため全成分デフォルト初期化必須(§13)
    logical :: enabled = .false.
    integer :: idt = 1               ! 更新間隔(ステップ数)
    real :: rhog = 0.0               ! ρ g (Pa/m)
    real :: coef = 0.0               ! ρ g / 6η(拡散係数の前置係数 1/(m s))
    real :: tauy = 0.0               ! 降伏応力 τ_y (Pa。0 = Newton 流体)
    real :: wsol = 0.0               ! 停止セルの固化レート (m/s。0 = 固化なし)
    real :: vsol = 0.0               ! 停止判定の速度閾値 (m/s。wsol>0 で必須)
    real :: cfl = 0.4                ! サブサイクルの安全係数
    integer :: nsubmax = 10000       ! サブサイクル数の上限
    logical :: initialized = .false.
  end type

  type t_vent                        ! 噴火口1個
    integer :: ncell = 0             ! セル数
    integer, allocatable :: cell(:,:)  ! セル座標 (1:2, 1:ncell)
    integer :: nval = 0              ! 噴出率時系列のデータ数
    real, allocatable :: val(:,:)    ! 時系列 (1:2, 1:nval) (s, m3/s)
  end type

  ! モジュール私有の作業領域(単一インスタンス前提。developer.md §12)
  type t_lvwork
    real :: cw(1:4) = 0.0            ! エッジ伝導度重み(= 通過幅/距離。4近傍のみ)
    real :: dist(1:4) = 0.0          ! エッジ法線方向のセル中心間距離 (m)
    real :: area = 0.0               ! セル面積 dx*dy (m2)
    real :: ainv = 0.0               ! 1 / (dx*dy)
    real :: rdx2 = 0.0               ! 1/dx^2 + 1/dy^2(安定条件用)
    real, allocatable :: q(:,:,:)    ! エッジ溶岩フラックス4成分 (m3/s)
    real, allocatable :: sdz(:,:)    ! 固化深の作業領域 (m)(1:nx, js:je)。
                                     !   2パス構造用(判定は時刻 n の場、適用は
                                     !   パス2。lv_wsol>0 のみ確保)
    integer :: nvent = 0             ! 噴火口数
    type(t_vent), allocatable :: vent(:)
    real :: vin = 0.0                ! 噴出の累計(自帯セル分の柱状 m 和)
    real :: vsol = 0.0               ! 固化の累計(同上)
    integer :: nsubtot = 0           ! サブサイクル総数(ランク共通。dispose で報告)
    integer :: ntick = 0             ! 更新回数
  end type
  type(t_lvwork) :: lvw

contains


!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! 溶岩流モジュールを初期化する
!   fn_lavaflow 未指定 or f_lavaflow=0 なら何もしない(enabled = .false.)。
!   他モジュールへの依存はない(気象・積雪は不要。段階2の温度で meteo 連動)
!----------------------------------------------------------------------
subroutine m_lavaflow_init(lv, p, g, s)
  type(t_lavaflow), intent(out) :: lv
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_list_lavaflow) :: list
  real :: dtg
  integer :: iv, n, k, i, j
  logical :: active(1:lvmax)
  character(len=256) :: msg

  if (len_trim(p%fn_lavaflow) == 0) return

  call list_lavaflow_read(p, list)
  if (list%f_lavaflow == 0) return   ! fn を書いたまま一時無効化する経路

  ! STG は非対応(z の時間発展に追従しない。geomorph と同じ制約)
  if (p%f_gridsystem /= 0) then
    call par_stop("list_lavaflow: lava flow (fn_lavaflow) is not supported " &
                  // "with STG (f_gridsystem=1)")
  end if
  ! morfac 加速とは併用しない(溶岩はイベント時間。debris と同じ制約)
  if (s%geo_morfac > 1.0) then
    call par_stop("list_lavaflow: lava flow requires morfac = 1 " &
                  // "(event-scale process; found geomorph morfac = " &
                  // rtoa(s%geo_morfac) // ")")
  end if

  ! --- 更新間隔(空 = 毎ステップ) ---
  if (len_trim(list%dt_lavaflow_c) == 0) then
    lv%idt = 1
  else
    dtg = str2sec(trim(list%dt_lavaflow_c), &
                  "list_lavaflow: dt_lavaflow_c is not a valid duration")
    if (dtg <= 0.0) call par_stop("list_lavaflow: dt_lavaflow_c must be a positive duration")
    lv%idt = max(nint(dtg / p%dt), 1)
  end if

  ! --- レオロジー(ラン全体で1組。直接入力 — lava_plan.md §3) ---
  if (list%lv_rho <= 0.0) call par_stop("list_lavaflow: lv_rho must be > 0 (kg/m3)")
  if (list%lv_visc <= -9998.0) call par_stop("list_lavaflow: lv_visc is required (Pa s)")
  if (list%lv_visc <= 0.0) call par_stop("list_lavaflow: lv_visc must be > 0 (Pa s)")
  if (list%lv_tauy < 0.0) call par_stop("list_lavaflow: lv_tauy must be >= 0 (Pa)")
  lv%rhog = list%lv_rho * p%gg
  lv%coef = lv%rhog / (6.0 * list%lv_visc)
  lv%tauy = list%lv_tauy

  ! --- 固化(速度閾値+レート。f_dbstop=1 と同じ閉じ方) ---
  if (list%lv_wsol < 0.0) call par_stop("list_lavaflow: lv_wsol must be >= 0 (m/s)")
  lv%wsol = list%lv_wsol
  if (lv%wsol > 0.0) then
    if (list%lv_vsol <= -9998.0) then
      call par_stop("list_lavaflow: lv_wsol > 0 requires lv_vsol " &
                    // "(stop-detection velocity threshold, m/s)")
    end if
    if (list%lv_vsol <= 0.0) call par_stop("list_lavaflow: lv_vsol must be > 0 (m/s)")
    lv%vsol = list%lv_vsol
  end if

  ! --- サブサイクル ---
  if (list%lv_cfl <= 0.0 .or. list%lv_cfl > 1.0) then
    call par_stop("list_lavaflow: lv_cfl must be in (0, 1]")
  end if
  lv%cfl = list%lv_cfl
  if (list%lv_nsubmax < 1) call par_stop("list_lavaflow: lv_nsubmax must be >= 1")
  lv%nsubmax = list%lv_nsubmax

  ! --- 噴火口(セル集合+噴出率。番号は 1 から連続 = pump と同じ規約) ---
  do iv = 1, lvmax
    active(iv) = (lv_cell(1,1,iv) > -9999) &
                 .or. (lv_val(1,1,iv) > -9999.0) &
                 .or. (list%lv_q0(iv) > -9999.0) &
                 .or. (len_trim(list%fn_lv_cell(iv)) > 0) &
                 .or. (len_trim(list%fn_lv_val(iv)) > 0)
  end do
  lvw%nvent = count(active)
  if (lvw%nvent <= 0) call par_stop("list_lavaflow: no vents defined " &
                                    // "(give lv_cell and lv_q0/lv_val)")
  if (.not. all(active(1:lvw%nvent))) then
    call par_stop("list_lavaflow: vent numbers must be consecutive from 1")
  end if

  allocate(lvw%vent(1:lvw%nvent))
  do iv = 1, lvw%nvent

    !--- セル集合(ファイル指定が優先) ---
    if (len_trim(list%fn_lv_cell(iv)) > 0) then
      call read_cell_file2(trim(p%dir_data)//"/"//trim(list%fn_lv_cell(iv)), &
                           lvw%vent(iv)%ncell, lvw%vent(iv)%cell)
    else
      n = 0
      do k = 1, lvcmax
        if (lv_cell(1,k,iv) <= -9999) exit    ! 番兵で終端
        n = n + 1
      end do
      allocate(lvw%vent(iv)%cell(1:2,1:max(n,1)))
      lvw%vent(iv)%cell(1:2,1:n) = lv_cell(1:2,1:n,iv)
      lvw%vent(iv)%ncell = n
    end if

    !--- 噴出率(ファイル > インライン時系列 > 一定値。時刻は分→秒換算) ---
    if (len_trim(list%fn_lv_val(iv)) > 0) then
      call read_val_file2(trim(p%dir_data)//"/"//trim(list%fn_lv_val(iv)), &
                          lvw%vent(iv)%nval, lvw%vent(iv)%val)
    else if (lv_val(1,1,iv) > -9999.0) then
      n = 0
      do k = 1, lvvmax
        if (lv_val(1,k,iv) <= -9999.0) exit   ! 番兵で終端
        n = n + 1
      end do
      allocate(lvw%vent(iv)%val(1:2,1:max(n,1)))
      lvw%vent(iv)%val(1,1:n) = lv_val(1,1:n,iv) * 60   ! 分を秒に換算
      lvw%vent(iv)%val(2,1:n) = lv_val(2,1:n,iv)
      lvw%vent(iv)%nval = n
    else if (list%lv_q0(iv) > -9999.0) then
      allocate(lvw%vent(iv)%val(1:2,1:1))               ! 一定値は1点時系列に退化
      lvw%vent(iv)%val(1,1) = 0.0
      lvw%vent(iv)%val(2,1) = list%lv_q0(iv)
      lvw%vent(iv)%nval = 1
    end if

    !--- 検証 ---
    if (lvw%vent(iv)%ncell <= 0) then
      call par_stop("list_lavaflow: vent "//itoa(iv)//" has no cells")
    end if
    if (lvw%vent(iv)%nval <= 0) then
      call par_stop("list_lavaflow: vent "//itoa(iv)//" has no effusion rate " &
                    // "(give lv_q0, lv_val or fn_lv_val)")
    end if
    if (any(lvw%vent(iv)%val(2,1:lvw%vent(iv)%nval) < 0.0)) then
      call par_stop("list_lavaflow: vent "//itoa(iv)//" has a negative effusion rate")
    end if
    do k = 1, lvw%vent(iv)%ncell
      i = lvw%vent(iv)%cell(1,k)
      j = lvw%vent(iv)%cell(2,k)
      if (i < 1 .or. i > g%nx .or. j < 1 .or. j > g%ny) then
        call par_stop("list_lavaflow: vent "//itoa(iv)//" cell (" &
                      //itoa(i)//","//itoa(j)//") is outside the domain")
      end if
      if (g%x(i,j) <= 0) then
        call par_stop("list_lavaflow: vent "//itoa(iv)//" cell (" &
                      //itoa(i)//","//itoa(j)//") is not a valid cell")
      end if
      if (g%sw(i,j) > 0) then
        call par_stop("list_lavaflow: vent "//itoa(iv)//" cell (" &
                      //itoa(i)//","//itoa(j)//") is a sea cell")
      end if
    end do
  end do

  ! --- 状態の確保 ---
  allocate(s%hl(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)

  ! --- 作業領域(calc_creep / m_glacier と同じ4近傍) ---
  lvw%area = g%dx * g%dy
  lvw%ainv = 1.0 / lvw%area
  lvw%rdx2 = 1.0 / g%dx**2 + 1.0 / g%dy**2
  lvw%cw(1) = 0.0             ! 斜め(未使用)
  lvw%cw(2) = g%dx / g%dy
  lvw%cw(3) = 0.0
  lvw%cw(4) = g%dy / g%dx
  lvw%dist(1) = 0.0
  lvw%dist(2) = g%dy
  lvw%dist(3) = 0.0
  lvw%dist(4) = g%dx
  ! j 範囲はセル j を挟むエッジが j-1 と j にあるため下限 jsh-1
  ! (m_glacier の glw%q と同形)。確保時 0: マスク起因で書かれない
  ! エッジは恒久 0(無フラックス)
  allocate(lvw%q(1:4, 0:g%nx, dcp%jsh-1:dcp%jeh), source = 0.0)
  if (lv%wsol > 0.0) then
    allocate(lvw%sdz(1:g%nx, dcp%js:dcp%je), source = 0.0)
  end if

  ! --- リスタート ---
  if (p%f_state_restore > 0) call restore_state(p, g, s)

  lv%enabled = .true.
  lv%initialized = .true.
  write(msg,'(a,i0,a,i0,a)') "lavaflow enabled (dt_lavaflow = ", lv%idt, &
        " steps, ", lvw%nvent, " vent(s))"
  call par_info(trim(msg))
end subroutine


!----------------------------------------------------------------------
! 溶岩流の更新(dt_lavaflow 間隔。geomorph・driftwood の後 = z 更新
! プロセスの末尾)。順序はヘッダの契約: 噴火口ソース → ハロ交換 →
! Bingham 拡散流動 → 固化(→ z 更新・e 回復・z ハロ交換)。
! 注意: 冒頭の return とハロ交換の判定はすべて全ランクで同一
!----------------------------------------------------------------------
subroutine m_lavaflow_calc(lv, p, g, s, it)
  type(t_lavaflow), intent(in) :: lv
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer, intent(in) :: it
  real :: dtw

  if (.not. lv%enabled) return
  if (mod(it, lv%idt) /= 0) return
  lvw%ntick = lvw%ntick + 1
  dtw = p%dt * lv%idt

  ! (1) 噴火口ソース(owner-compute)
  call tick_vent(s, dtw)

  ! (2) 注入の帯更新を配布(流動のエッジ冗長計算の入力)
  call par_halo_cell(s%hl)

  ! (3) Bingham 拡散流動(サブサイクルごとに hl のハロ交換を内包)
  call tick_flow(lv, g, s, dtw)

  ! (4) 固化(不動セルの hl → z。e 回復と z のハロ交換まで)
  if (lv%wsol > 0.0) call tick_solidify(lv, g, s, dtw)

end subroutine


!----------------------------------------------------------------------
! 溶岩流モジュールを破棄する(save は dispose で行う。契約5)
!   台帳(噴出・固化・残存溶岩の体積)を全ランク総和して報告する。
!   par_allreduce_sumr は collective — 全ランクが dispose を呼ぶ前提
!----------------------------------------------------------------------
subroutine m_lavaflow_dispose(lv, p, g, s)
  type(t_lavaflow), intent(inout) :: lv
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  real :: vsum(1:3), hsum
  integer :: i, j
  character(len=256) :: msg

  if (.not. lv%enabled) return
  if (p%f_state_save > 0) call save_state(p, g, s)

  ! 台帳の総括(診断のみ。柱状 m 和 × セル面積 = 体積 m3)
  hsum = 0.0
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      hsum = hsum + s%hl(i,j)
    end do
  end do
  vsum(1) = lvw%vin * lvw%area
  vsum(2) = lvw%vsol * lvw%area
  vsum(3) = hsum * lvw%area
  call par_allreduce_sumr(vsum)
  if (is_root) then
    write(msg,'(a,es12.4,a,es12.4,a,es12.4,a)') &
      " lavaflow: erupted ", vsum(1), " m3, solidified ", vsum(2), &
      " m3, molten ", vsum(3), " m3"
    call par_info(trim(msg))
  end if
  if (lvw%ntick > 0) then
    call par_info(" lavaflow: subcycles total = " // itoa(lvw%nsubtot) &
                  // " over " // itoa(lvw%ntick) // " updates")
  end if

  if (allocated(lvw%q)) deallocate(lvw%q)
  if (allocated(lvw%sdz)) deallocate(lvw%sdz)
  if (allocated(lvw%vent)) deallocate(lvw%vent)
  lvw%nvent = 0
  lvw%vin = 0.0
  lvw%vsol = 0.0
  lvw%nsubtot = 0
  lvw%ntick = 0
  lv%enabled = .false.
  lv%initialized = .false.
end subroutine


!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

!----------------------------------------------------------------------
! 噴火口ソース(1 tick ぶんの注入)
!   噴出率 Q(t) を時刻 s%t で補間し、セル集合へ均等分配(柱状 m)。
!   指向性(運動量)は持たない。owner-compute のみでハロ交換は呼び出し側
!----------------------------------------------------------------------
subroutine tick_vent(s, dtw)
  type(t_state), intent(inout) :: s
  real, intent(in) :: dtw
  integer :: iv, k, i, j
  real :: q, dh

  do iv = 1, lvw%nvent
    q = interp_series(lvw%vent(iv)%val, lvw%vent(iv)%nval, s%t)
    if (q <= 0.0) cycle
    ! セルあたりの注入(柱状 m。セル集合へ等分配)
    dh = q * dtw / (lvw%vent(iv)%ncell * lvw%area)
    do k = 1, lvw%vent(iv)%ncell
      i = lvw%vent(iv)%cell(1,k)
      j = lvw%vent(iv)%cell(2,k)
      if (j < dcp%js .or. j > dcp%je) cycle     ! owner-compute
      s%hl(i,j) = s%hl(i,j) + dh
      lvw%vin = lvw%vin + dh
    end do
  end do
end subroutine


!----------------------------------------------------------------------
! Bingham 粘性重力流(1回の呼び出しで dtw ぶん。適応サブサイクリング)
!   各サブサイクル:
!     パスA: 拡散係数の最大値(自帯エッジ)-> allreduce_max -> dt_sub 決定
!            (全ランク同一 = ループ回数・collective が同期)
!     パスB: エッジ流量(時刻 n の hl・z から。書き手はハロ行 je+1 まで =
!            帯界面の冗長計算)。ドナー律速で hl>=0 保証
!     パスC: 発散を取り hl を更新(自帯 js..je のみ)。可動マスクを蓄積
!            -> hl のハロ交換
!   エッジ流量の反対称集計により溶岩体積は機械精度で厳密に保存される
!----------------------------------------------------------------------
subroutine tick_flow(lv, g, s, dtw)
  type(t_lavaflow), intent(in) :: lv
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: dtw
  integer :: i, j, k, in, jn, jt, nsub
  real :: trem, dtsub, dmax, dlim
  real :: sc, sn_, ds, ss, h0, hf, he, dd, gq, qcap, dv
  real :: w1(1)
  logical :: okc, last

  trem = dtw
  nsub = 0
  jt = min(dcp%je + 1, dcp%jeh)

  do while (trem > 0.0)
    nsub = nsub + 1
    if (nsub > lv%nsubmax) then
      call par_stop("lavaflow: subcycle count exceeded lv_nsubmax = " &
                    // itoa(lv%nsubmax) // " (reduce dt_lavaflow_c or " &
                    // "increase lv_nsubmax; very fluid lava is stiff — " &
                    // "see lava_plan.md sec.6)")
    end if

    ! --- パスA: 拡散係数の最大値と dt_sub の決定 ---
    dmax = 0.0
    !$omp parallel do schedule(static) private(i, j, k, in, jn, okc, sc, sn_, ds, ss, h0, hf, he, dd) &
    !$omp reduction(max: dmax)
    do j = dcp%js, jt
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0) cycle
        okc = (g%sw(i,j) <= 0)
        do k = 2, 4, 2
          in = i + din(k)
          jn = j + djn(k)
          if (.not. okc) cycle
          if (g%x(in,jn) <= 0) cycle
          if (g%sw(in,jn) > 0) cycle
          he = 0.5 * (s%hl(i,j) + s%hl(in,jn))
          if (he <= 0.0) cycle
          sc = s%z(i,j) + s%hl(i,j)
          sn_ = s%z(in,jn) + s%hl(in,jn)
          ds = sc - sn_
          if (ds == 0.0) cycle
          ss = abs(ds) / lvw%dist(k)
          h0 = 0.0
          if (lv%tauy > 0.0) h0 = lv%tauy / (lv%rhog * ss)
          hf = he - h0
          if (hf <= 0.0) cycle
          dd = lv%coef * hf * hf * (2.0 * he + h0)
          dmax = max(dmax, dd)
        end do
      end do
    end do
    !$omp end parallel do
    w1(1) = dmax
    call par_allreduce_max(w1)
    dmax = w1(1)

    last = .true.
    dtsub = trem
    if (dmax > 0.0) then
      dlim = lv%cfl * 0.5 / (dmax * lvw%rdx2)
      if (dlim < trem) then
        dtsub = dlim
        last = .false.
      end if
    else
      ! 動く溶岩がない: このサイクルで消化して終了(フラックスは全て 0)
      dtsub = trem
    end if

    ! --- パスB: エッジ流量(ドナー律速つき) ---
    !   帯界面のエッジ成分 k=1..3(行 je)はハロ行 je+1 の書き手が担う
    !   (冗長計算。全域端では行が存在せず対象外)
    !$omp parallel do schedule(static) private(i, j, k, in, jn, okc, sc, sn_, ds, ss, h0, hf, &
    !$omp                                      he, dd, gq, qcap)
    do j = dcp%js, jt
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0) cycle
        okc = (g%sw(i,j) <= 0)
        do k = 1, 4
          in = i + din(k)
          jn = j + djn(k)
          ! 状態は毎回変わるため、条件を満たさない場合も必ず 0 を代入する
          gq = 0.0
          if (lvw%cw(k) > 0.0 .and. okc .and. g%x(in,jn) > 0) then
            if (g%sw(in,jn) <= 0) then
              he = 0.5 * (s%hl(i,j) + s%hl(in,jn))
              if (he > 0.0) then
                sc = s%z(i,j) + s%hl(i,j)
                sn_ = s%z(in,jn) + s%hl(in,jn)
                ds = sc - sn_
                if (ds /= 0.0) then
                  ss = abs(ds) / lvw%dist(k)
                  h0 = 0.0
                  if (lv%tauy > 0.0) h0 = lv%tauy / (lv%rhog * ss)
                  hf = he - h0
                  if (hf > 0.0) then
                    dd = lv%coef * hf * hf * (2.0 * he + h0)
                    ! エッジ流量(書き手 c から k 近傍 n に向かい正)(m3/s)
                    gq = dd * ds * lvw%cw(k)
                    ! ドナー律速: 1エッジの持ち出し ≤ ドナー溶岩体積の 1/4
                    ! (4エッジ合計 ≤ 全量 → hl >= 0 が構造的に成立)
                    if (ds > 0.0) then
                      qcap = 0.25 * s%hl(i,j) * lvw%area / dtsub
                      gq = min(gq, qcap)
                    else
                      qcap = 0.25 * s%hl(in,jn) * lvw%area / dtsub
                      gq = max(gq, -qcap)
                    end if
                  end if
                end if
              end if
            end if
          end if
          lvw%q(k, i+die(k), j+dje(k)) = gq
        end do
      end do
    end do
    !$omp end parallel do

    ! --- パスC: 発散を取り hl を更新 ---
    !$omp parallel do schedule(static) private(i, j, k, dv)
    do j = dcp%js, dcp%je
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0) cycle
        if (g%sw(i,j) > 0) cycle
        dv = 0.0
        do k = 1, 8
          dv = dv + sign_e(k) * lvw%q(ke(k), i+die(k), j+dje(k))
        end do
        s%hl(i,j) = s%hl(i,j) - dv * dtsub * lvw%ainv
      end do
    end do
    !$omp end parallel do

    call par_halo_cell(s%hl)

    if (last) exit
    trem = trem - dtsub
  end do

  lvw%nsubtot = lvw%nsubtot + nsub
end subroutine


!----------------------------------------------------------------------
! 固化(停止セルの hl を s%z へ転換。数値的閉包 — lava_plan.md §5)
!   停止 = エッジ深さ平均速度 u = q_width/he = D・S/he の最大が lv_vsol
!   未満のセル(Bingham の停止は漸近的で厳密なフラックス 0 に達しない
!   ため速度閾値で閉じる。f_dbstop=1 の db_vstop/db_wstop と同じ構成)。
!   転換量 w = min(hl, lv_wsol×dtw)。z のみ増加(sd は増やさない =
!   固化溶岩は侵食されない岩盤)。再流動なし(不可逆)。
!   2パス構造(glacier tick_erosion と同型の競合対策): パス1が時刻 n の
!   hl・z(近傍参照。ハロは tick_flow 末端の交換で最新)から固化深を
!   評価し、パス2が適用する。e 回復と s%z のハロ交換まで行う
!   (geomorph / glacier と同じ契約)
!----------------------------------------------------------------------
subroutine tick_solidify(lv, g, s, dtw)
  type(t_lavaflow), intent(in) :: lv
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: dtw
  integer :: i, j, k, in, jn
  real :: w, wcap, vsum, vmax, sc, sn_, ds, ss, h0, hf, he, dd, ue

  wcap = lv%wsol * dtw

  ! --- パス1: 停止判定と固化深の評価(書き込みは sdz のみ) ---
  !$omp parallel do schedule(static) private(i, j, k, in, jn, vmax, sc, sn_, ds, ss, h0, hf, &
  !$omp                                      he, dd, ue)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      lvw%sdz(i,j) = 0.0
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      if (s%hl(i,j) <= 0.0) cycle
      ! 4近傍エッジの深さ平均速度の最大(tick_flow パスB と同じ量)
      vmax = 0.0
      sc = s%z(i,j) + s%hl(i,j)
      do k = 1, 8
        if (lvw%cw(ke(k)) <= 0.0) cycle        ! 斜めは未使用
        in = i + din(k)
        jn = j + djn(k)
        if (g%x(in,jn) <= 0) cycle
        if (g%sw(in,jn) > 0) cycle
        he = 0.5 * (s%hl(i,j) + s%hl(in,jn))
        if (he <= 0.0) cycle
        sn_ = s%z(in,jn) + s%hl(in,jn)
        ds = sc - sn_
        if (ds == 0.0) cycle
        ss = abs(ds) / lvw%dist(ke(k))
        h0 = 0.0
        if (lv%tauy > 0.0) h0 = lv%tauy / (lv%rhog * ss)
        hf = he - h0
        if (hf <= 0.0) cycle
        dd = lv%coef * hf * hf * (2.0 * he + h0)
        ue = dd * ss / he
        vmax = max(vmax, ue)
      end do
      if (vmax >= lv%vsol) cycle
      lvw%sdz(i,j) = min(s%hl(i,j), wcap)
    end do
  end do
  !$omp end parallel do

  ! --- パス2: 適用(自帯のみ。sdz はパス1で全対象セルに 0 込みで設定済み) ---
  vsum = 0.0
  !$omp parallel do schedule(static) private(i, j, w) reduction(+: vsum)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      w = lvw%sdz(i,j)
      if (w <= 0.0) cycle
      s%hl(i,j) = s%hl(i,j) - w
      s%z(i,j) = s%z(i,j) + w
      s%e(i,j) = s%z(i,j) + s%h(i,j)
      vsum = vsum + w
    end do
  end do
  !$omp end parallel do
  lvw%vsol = lvw%vsol + vsum

  ! 固化の有無はランク・tick で異なるが、collective の実行判定は
  ! 「lv_wsol > 0 の tick では常に交換」で全ランク同一(§5)。
  ! hl の帯更新は次 tick 冒頭の交換が配布する(この後 hl を読む者はいない)
  call par_halo_cell(s%z)
end subroutine


!----------------------------------------------------------------------
! 内部状態の保存・復元(モデル私有ファイル lavaflow.dat。契約5。§7)
!----------------------------------------------------------------------
subroutine save_state(p, g, s)
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
  call par_gather_to(wk, s%hl)
  if (is_root) then
    call sysdep_mkdir(p%dir_save)
    open(newunit=un, file=trim(p%dir_save)//'/lavaflow.dat', form='unformatted', &
         status='replace')
    call fileio_write_rle(un, wk)
    close(un)
  end if
end subroutine


subroutine restore_state(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, allocatable :: wk(:,:)
  real :: dum(1,1)
  character(:), allocatable :: fname
  logical :: found
  integer :: un

  fname = trim(p%dir_save)//'/lavaflow.dat'
  inquire(file=fname, exist=found)
  if (.not. found) then
    call par_stop("lavaflow: state file not found (was fn_lavaflow enabled when saving): " &
                  //fname)
  end if
  if (is_root) then
    allocate(wk(1:g%nx, 1:g%ny), source = 0.0)
    open(newunit=un, file=fname, form='unformatted', status='old')
    call fileio_read_rle(un, wk)
    close(un)
    call par_scatter_cell(wk, s%hl)
  else
    call par_scatter_cell(dum, s%hl)
  end if
end subroutine

end module
