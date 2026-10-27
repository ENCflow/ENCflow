module m_wavefield
  ! ====== 沿岸の波浪場(代表周波数・方向分割の位相平均作用量平衡。fn_wavefield。§88) ======
  ! 短周期波を位相平均の方向ビン(N_θ 個)のエネルギー密度 E_m [J/m2/rad] として、
  ! 浅水流と同じ格子・同じ時間発展の中で解く(設計の正本 docs/wavefield_plan.md、
  ! 方針 5 の例外と決定の記録は developer.md §0-5・§88)。
  !
  ! 【基礎式】(段 W1: 固定床・流れの影響なし。σ = ω = 2π/T で一定)
  !   ∂E_m/∂t + ∇·(c_g ê_m E_m) + ∂(c_θ E_m)/∂θ = −(D_w + D_f) E_m/E
  !   作用量の保存(Bretherton & Garrett 1968)を SWAN(Booij ら 1999)の形から周波数
  !   1 個に縮約したもの(HISWA・XBeach 定常モード・SnapWave と同型)。σ が一定の
  !   W1 では作用量 N = E/σ とエネルギーの保存は同じなので、状態はエネルギーで持つ
  !   (代表周期が時系列で変わっても局所のエネルギーは読み替えない)。
  !   分散関係 σ² = g k tanh(kh)、c_g = (σ/2k)(1 + 2kh/sinh 2kh)、屈折速度
  !   c_θ = (σ/sinh 2kh)(sin θ ∂h/∂x − cos θ ∂h/∂y)(x 東・y 北。浅い側へ曲がる。
  !   SnapWave と同じく |c_θ| <= σ/4 に制限)。方向空間の移流は 1 次風上(陰的)に van Leer の
  !   制限つき反拡散流束を前の値から足す遅延補正(1 次風上だけでは方向空間の数値拡散で
  !   屈折が遅れる。中心差分は単一方向の入射で負のエネルギーを生むので採らない。§88)。
  !   砕波 D_w: Baldock ら(1998)(既定)または Janssen & Battjes(2007)。規則波(検定用)
  !   は H <= γh の飽和。不規則波は XBeach・SnapWave と同じく H_rms <= γmax h の上限も
  !   かける。底面摩擦 D_f = c ρ f_w u_orb³(c = 0.28 不規則・0.21 規則。Guza &
  !   Thornton 1985 の係数を XBeach が採用)。ビンへの配分は E_m/E に比例。
  !
  ! 【空間の輸送: 2 リンク分解の風上法】(wavefield_plan.md §6.1)
  !   伝播速度 v = c_g ê_m を、v の向きを挟む 2 本の格子方向(軸と対角)へ非負に
  !   分解する: 格子で正規化した p_x = v_x/Δx、p_y = v_y/Δy について、|p_x| >= |p_y|
  !   なら軸 x へ率 |p_x| − |p_y|、対角へ率 |p_y|(逆も同様)。流出率の和は
  !   max(|p_x|, |p_y|)。送り手のセル中心の値で評価するので流束は保存的で、
  !   格子方向(軸・対角)の伝播では横断の数値拡散がない(D∞ = Tarboton 1997 と
  !   同じ発想)。W1 は流れがないので分解はビンごとに一定(向きが固定)。
  !   対角リンクの両脇の 2 セルがともに非波浪セルなら、その対角は閉じる(1 セル厚の
  !   斜めの堤を波がすり抜けない。水の ENC とは意図的に違う)。
  !
  ! 【時間進行: 1 つの核と 2 つのモード】(§6.3)
  !   1 回の更新 = 空間の流入出(陽的・Jacobi: 前の値から新しい値)+ セル内の
  !   方向空間の屈折と源項(陰的。周期境界の三重対角。M 行列なので非負)。
  !   非定常(wf_mode = 1): 物理時間の dt で毎ステップ(流出率 × dt > 1 ならサブ
  !     ステップ)。輸送は陽的で保存的なので台帳は丸め誤差内で閉じる。
  !   準定常(wf_mode = 2): dt_wave ごとに、局所の擬似時間刻み Δτ = 1/(最大流出率)
  !     で反復(輸送について Jacobi 反復そのもの)して収束させる。分割しない更新
  !     なので定常解は Δτ に依らない。前回の解から始める。
  !   どちらもセルの更新順に依らない Jacobi 型 = 分割数・スレッド数によらずビット一致。
  !
  ! 【境界】外縁の辺(W, E, N, S)ごとに 0: 吸収 / 1: 入射 / 2: 側方 Neumann。
  !   格子の外の仮想の送り手が、入射なら沖の波(H・T・方向・方向分散)のビン別エネルギー、
  !   Neumann なら境界の内側のセルの値、吸収なら 0 を持つ(群速度は内側のセルの値)。
  !   各リンクの送り手は 1 つなので角で二重に注入しない。陸・乾燥・海域マスクの海セル・
  !   吸収セル(家屋空隙 gv < 1、サブグリッド河道の幅・断面形のセル)へ向かう分は
  !   吸収(反射なし)。波浪セル = 領域内(x > 0)・海セルでない・吸収セルでない・
  !   h > wf_hmin。
  !
  ! 【台帳】境界流入・境界流出・吸収・砕波・摩擦・上限(飽和)・乾燥化による除去・
  !   数値的な切り捨てを別々に数える(行部分和 → par_sum_rows)。準定常は収束時の率
  !   (W)を更新ごとに、非定常は累積量(J)を計測間隔ごとに result/wavefield.csv へ。
  !
  ! 【並列】帯分割のまま。セル量(N_θ 面)は帯±ハロで持ち、更新ごとにビンごとの
  !   ハロ交換(par_halo_cell)。準定常の反復回数は残差の max の allreduce で決まり
  !   全ランク同一。全域の端は 1..nx・1..ny を明示的に判定する(§84.15 の教訓)。
  !
  ! 【所有と結合】状態(E_m)は t_wavefield の私有。共有状態 s へは診断量(波高・平均
  !   波向・軌道流速・砕波散逸)だけを書く(W1 は流れ・地形に作用しない)。s%h は読む
  !   だけ(ハロは自前で交換)。保存・復元は私有ファイル wavefield_info.txt(全ランクが
  !   読む見出し)と wavefield.dat(ビンごとの RLE。m_restart。契約5)。
  !
  ! 【初版の併用制限】STG・ネストは init で停止(§88.1 D11)。
  ! ==================================================================================
  use, intrinsic :: iso_fortran_env, only : real64, int8
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use m_swflow_enc, only : chn, sct
  use list_wavefield, only : t_list_wavefield, list_wavefield_read, wf_nvalmax
  use m_restart, only : restart_write_cell, restart_read_cell
  use m_sysdep_util, only : sysdep_mkdir
  use m_util, only : param_default, itoa, rtoa
  use m_parallel, only : par_info, par_warn, par_stop, dcp, is_root, par_halo_cell, par_allreduce_max, &
                         par_allreduce_sumi, par_sum_rows
  implicit none
  private
  public :: t_wavefield
  public :: m_wavefield_init
  public :: m_wavefield_calc
  public :: m_wavefield_record
  public :: m_wavefield_dispose

  integer, parameter :: save_version = 20261027      ! 保存形式の版(形式変更日。§7)
  real, parameter :: pi = 3.14159265358979323846
  real, parameter :: rho = 1025.0                    ! 海水の密度 (kg/m3。XBeach の既定)
  real, parameter :: dir_missing = -9999.0           ! 無波セルの平均波向
  integer, parameter :: nl = 8                       ! 台帳の項目数
  ! 台帳の項目: 1 境界流入、2 境界流出、3 吸収、4 砕波、5 摩擦、6 上限(飽和)、
  !   7 乾燥化による除去(量 J)、8 数値的な切り捨て(負値の 0 化で足した分)
  integer, parameter :: l_in = 1, l_out = 2, l_abs = 3, l_brk = 4, l_fric = 5, l_lim = 6, &
                        l_dry = 7, l_neg = 8
  ! 格子方向 L = 0..7(E・NE・N・NW・W・SW・S・SE。反時計回り)の (di, dj)。j は南向き
  integer, parameter :: ldi(0:7) = [ 1,  1,  0, -1, -1, -1,  0,  1]
  integer, parameter :: ldj(0:7) = [ 0, -1, -1, -1,  0,  1,  1,  1]

  !-------------------------------------------
  ! 波浪場の状態の容器(t_encflow の成分。init に早期 return 経路があるため
  ! 全成分デフォルト初期化。§13)
  !-------------------------------------------
  type t_wavefield
    logical :: enabled = .false.
    logical :: initialized = .false.
    ! 方向ビン(中心 θ_m = (m−1)Δθ、x 軸から反時計回り)
    integer :: nth = 0
    real :: dth = 0.0                           ! ビン幅 (rad)
    real, allocatable :: cth(:), sth(:)         ! cos θ_m, sin θ_m (1:nth)
    ! ビンごとの 2 リンク分解(W1 は流れがないので向きが固定 = 群速度あたりの率)
    integer, allocatable :: la(:), lb(:)        ! 流出先の格子方向(la 軸・lb 対角)
    real, allocatable :: qa(:), qb(:)           ! 群速度あたりの流出率 (1/m)
    real :: qmax = 0.0                          ! max_m (qa + qb) (1/m)
    ! 解法
    integer :: mode = 2                         ! 1: 非定常 / 2: 準定常
    integer :: idt = 1                          ! 準定常の更新間隔(ステップ数)
    integer :: itmax = 0                        ! 準定常の反復の上限
    real :: tol = 0.0                           ! 準定常の収束判定(波高の相対変化)
    integer :: finit = 1                        ! 1: 開始時に準定常解 / 0: 静穏から
    ! 境界・波の種類・係数
    integer :: bcside(1:4) = 0                  ! W, E, N, S(0 吸収 / 1 入射 / 2 側方 Neumann)
    integer :: wtype = 1                        ! 1: 不規則波 / 2: 規則波
    integer :: brk = 1                          ! 1: Baldock / 2: Janssen & Battjes
    real :: gam = 0.0, alp = 0.0, gamx = 0.0, fw = 0.0, hmin = 0.0
    real :: cfric = 0.28                        ! 摩擦散逸の係数(不規則 0.28・規則 0.21)
    integer :: clock = 0                        ! 時系列の時計 0: 水理時間 / 1: 地形時間
    logical :: outdiag = .false.
    ! 沖の波(固定値または時系列)
    integer :: nval = 0
    real, allocatable :: val(:,:)               ! (1:5, 1:nval) 時刻 (s)・波高・周期・方向・方向分散
    real :: hfix = 0.0, tfix = 0.0, dfix = 0.0, sfix = 0.0
    ! 現在の沖の波(boundary_now が更新)
    real :: hbc = 0.0, tbc = 0.0, dbc = 0.0, sbc = 0.0
    real :: om = 0.0                            ! 代表角周波数 ω = 2π/T (rad/s。W1 は σ = ω)
    real, allocatable :: ebc(:)                 ! 入射のビン別エネルギー密度 (1:nth。J/m2/rad)
    ! 状態と作業配列
    real, allocatable :: ae(:,:,:)              ! E_m (ish:ieh, jsh:jeh, 1:nth)
    real, allocatable :: ae1(:,:,:)             ! 更新後の値 (ish:ieh, js:je, 1:nth)
    integer, allocatable :: wst(:,:)            ! 静的な波浪セル候補 (ish:ieh, jsh:jeh)
    integer, allocatable :: wcell(:,:)          ! 現在の波浪セル (ish:ieh, jsh:jeh)
    real, allocatable :: kw(:,:)                ! 波数 (ish:ieh, jsh:jeh)
    real, allocatable :: cg(:,:)                ! 群速度 (ish:ieh, jsh:jeh)
    real, allocatable :: dtl(:,:)               ! 1 回の更新の時間刻み (ish:ieh, js:je)
    ! 台帳(行部分和。1 回の反復の率と、非定常の累積量)
    real(real64), allocatable :: rrate(:,:)     ! (js:je, 1:nl)
    real(real64), allocatable :: rcum(:,:)      ! (js:je, 1:nl)
    real(real64) :: store0 = 0.0_real64         ! 非定常の開始時の貯留 (J)
    real(real64) :: cum0(1:nl) = 0.0_real64     ! 再開前までの累積(保存・復元で引き継ぐ)
    integer :: niter = 0                        ! 直近の準定常の反復回数
    real :: res = 0.0                           ! 直近の残差
    integer :: nsub = 1                         ! 直近の非定常のサブステップ数
    integer :: un = 0                           ! 台帳 CSV の装置番号(rank0)
    ! 波→流れ(段 W2。§88)
    integer :: flow = 0                         ! 0 作用なし / 1 外力 / 2 外力+GLM+波・流れの摩擦
    logical :: roller = .false.                 ! ローラーのエネルギー平衡
    real :: beta = 0.1                          ! ローラーの散逸係数 β
    real :: tramp = 0.0                         ! 外力の立ち上げ時間 (s。0 なら立ち上げなし)
    real, allocatable :: er(:,:)                ! ローラーのエネルギー E_r (ish:ieh, jsh:jeh。J/m2)
    real, allocatable :: er1(:,:)               ! 更新後の値 (ish:ieh, js:je)
    real, allocatable :: dbrk(:,:)              ! 砕波の散逸(上限の除去を含む。ish:ieh, js:je。W/m2)
    real, allocatable :: thm(:,:)               ! 平均波向 (rad。ish:ieh, jsh:jeh)
    real, allocatable :: cph(:,:)               ! 位相速度 c = σ/k (ish:ieh, jsh:jeh)
    integer, allocatable :: lar(:,:), lbr(:,:)  ! ローラーの 2 リンク分解の格子方向 (ish:ieh, jsh:jeh)
    real, allocatable :: qar(:,:), qbr(:,:)     ! 位相速度あたりの流出率 (1/m)
    integer :: nrit = 0                         ! 直近のローラーの反復回数
    ! 流れの波への作用(段 W3。f_wf_current = 1。§88)。ビンごとの量は有効時のみ確保
    logical :: current = .false.
    real, allocatable :: ux(:,:), uy(:,:)       ! 流れの流速 (m/s。x 東・y 北。ish:ieh, jsh:jeh)
    real, allocatable :: kb(:,:,:)              ! ビンごとの波数 k_m (ish:ieh, jsh:jeh, 1:nth)
    real, allocatable :: sgb(:,:,:)             ! ビンごとの固有角周波数 σ_m(0 = 阻止)
    real, allocatable :: qab(:,:,:), qbb(:,:,:) ! ビンごとの流出率 (1/s。軸 lab・対角 lbb へ)
    integer(int8), allocatable :: lab(:,:,:), lbb(:,:,:)   ! ビンごとの流出先の格子方向
    real, allocatable :: cthb(:,:,:)            ! ビンごとの屈折速度 c_θ (rad/s。ish:ieh, js:je, 1:nth)
    real, allocatable :: rmax(:,:)              ! セルの最大流出率 max_m (qab + qbb) (1/s)
    real(real64), allocatable :: rblk(:)        ! 阻止の率(行部分和。作用量 × ω。js:je)
    real(real64), allocatable :: rcblk(:)       ! 阻止の累積量(非定常。js:je)
    real(real64) :: cumblk0 = 0.0_real64        ! 再開前までの阻止の累積
  end type

contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! 初期化(fn_wavefield 指定時のみ有効。swflow の init より後 = chn・sct が確定)
!----------------------------------------------------------------------
subroutine m_wavefield_init(wf, p, g, s, multi)
  type(t_wavefield), intent(out) :: wf
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  logical, intent(in) :: multi
  type(t_list_wavefield) :: list
  logical :: have_diag, have_force

  if (len_trim(p%fn_wavefield) == 0) then
    if (p%f_state_restore > 0) call stop_if_orphan(p)
    return
  end if
  call list_wavefield_read(p, list)
  select case (list%f_wavefield)
    case (0)
      call par_info("list_wavefield: f_wavefield=0, the wave field is not enabled")
      if (p%f_state_restore > 0) call stop_if_orphan(p)
      return
    case (1)
    case default
      call par_stop("list_wavefield: f_wavefield must be 0 or 1: " // itoa(list%f_wavefield))
  end select

  if (p%f_gridsystem /= 0) call par_stop("list_wavefield: the wave field requires f_gridsystem=0 (ENC)")
  if (multi .or. len_trim(p%fn_nest) > 0) then
    call par_stop("list_wavefield: nesting is not supported by the wave field yet")
  end if

  call setup_params(wf, p, g, list)
  call setup_bins(wf, g)
  call setup_static_mask(wf, g)

  allocate(wf%ae(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh, 1:wf%nth), source = 0.0)
  allocate(wf%ae1(dcp%ish:dcp%ieh, dcp%js:dcp%je, 1:wf%nth), source = 0.0)
  allocate(wf%wcell(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0)
  allocate(wf%kw(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(wf%cg(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(wf%dtl(dcp%ish:dcp%ieh, dcp%js:dcp%je), source = 0.0)
  allocate(wf%ebc(1:wf%nth), source = 0.0)
  allocate(wf%rrate(dcp%js:dcp%je, 1:nl), source = 0.0_real64)
  allocate(wf%rcum(dcp%js:dcp%je, 1:nl), source = 0.0_real64)

  ! 共有状態の診断量(有効時のみ確保 = 無効時ゼロコスト)
  allocate(s%wvh(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(s%wvdir(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = dir_missing)
  allocate(s%wvub(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(s%wvdw(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  s%wv_active = .true.
  s%wv_outdiag = wf%outdiag

  ! 波→流れ(段 W2): 外力・Stokes 輸送(共有状態)とローラー・砕波の散逸(私有)
  if (wf%flow >= 1) then
    allocate(s%wvfx(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
    allocate(s%wvfy(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
    if (wf%flow >= 2) then
      allocate(s%wvus(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
      allocate(s%wvvs(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
      allocate(s%wvsp(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
    end if
    s%wv_rho = rho
    allocate(wf%dbrk(dcp%ish:dcp%ieh, dcp%js:dcp%je), source = 0.0)
    allocate(wf%thm(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
    allocate(wf%cph(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
    if (wf%roller) then
      allocate(wf%er(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
      allocate(wf%er1(dcp%ish:dcp%ieh, dcp%js:dcp%je), source = 0.0)
      allocate(wf%lar(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0)
      allocate(wf%lbr(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0)
      allocate(wf%qar(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
      allocate(wf%qbr(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
      allocate(s%wver(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
    end if
  end if

  ! 流れの波への作用(段 W3): ビンごとの分散関係・輸送の分解・屈折速度(有効時のみ確保)
  if (wf%current) then
    allocate(wf%ux(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
    allocate(wf%uy(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
    allocate(wf%kb(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh, 1:wf%nth), source = 0.0)
    allocate(wf%sgb(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh, 1:wf%nth), source = 0.0)
    allocate(wf%qab(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh, 1:wf%nth), source = 0.0)
    allocate(wf%qbb(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh, 1:wf%nth), source = 0.0)
    allocate(wf%lab(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh, 1:wf%nth), source = 0_int8)
    allocate(wf%lbb(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh, 1:wf%nth), source = 0_int8)
    allocate(wf%cthb(dcp%ish:dcp%ieh, dcp%js:dcp%je, 1:wf%nth), source = 0.0)
    allocate(wf%rmax(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
    allocate(wf%rblk(dcp%js:dcp%je), source = 0.0_real64)
    allocate(wf%rcblk(dcp%js:dcp%je), source = 0.0_real64)
  end if

  ! 開始時の波浪場: 復元、準定常解、または静穏
  call boundary_now(wf, p, s)
  call update_props(wf, p, g, s)
  if (wf%current) call update_current(wf, p, g, s)
  call check_incident_cells(wf, g)
  have_diag = .false.
  have_force = .false.
  if (p%f_state_restore > 0) then
    call restore_state(wf, p, s, have_diag, have_force)
  else if (wf%finit == 1) then
    call solve_steady(wf, p, g, s)
    if (wf%roller) call roller_steady(wf, p, g, s)
  end if
  ! 復元した診断量・外力があればそのまま使う(準定常の再開をビット一致にする。§88)
  if (.not. have_diag) then
    if (wf%current) then
      call diagnose_cur(wf, p, g, s)
    else
      call diagnose(wf, p, g, s)
    end if
  end if
  if (wf%flow >= 1 .and. .not. have_force) then
    if (wf%current) then
      call flow_coupling_cur(wf, p, g, s)
    else
      call flow_coupling(wf, p, g, s)
    end if
  end if
  s%wv_flow = wf%flow
  if (wf%flow >= 1) s%wv_ramp = ramp_factor(wf, p, s%it0)
  ! 非定常の台帳の起点: 再開(f_state_restore = 1)は保存時の起点と累積を引き継ぐ
  ! (restore_state が設定)。それ以外は現在の貯留から数え始める
  if (p%f_state_restore /= 1) then
    if (wf%current) then
      wf%store0 = storage_cur(wf, g)
    else
      wf%store0 = storage(wf, g)
    end if
  end if

  call open_csv(wf, p)
  if (wf%mode == 2 .and. p%f_state_restore /= 1) call write_steady(wf, g, s)
  wf%enabled = .true.
  wf%initialized = .true.
end subroutine


!----------------------------------------------------------------------
! 毎ステップ(tide の後・swflow の前): 非定常は毎ステップ、準定常は dt_wave ごと。
!   判定(enabled・mod(it, idt))は全ランク同一(collective 安全)
!----------------------------------------------------------------------
subroutine m_wavefield_calc(wf, p, g, s, it)
  type(t_wavefield), intent(inout) :: wf
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer, intent(in) :: it

  if (.not. wf%enabled) return
  ! 外力の立ち上げの係数(このステップの浅水流が使う。時間軸の it から決まるので
  ! 再開(f_state_restore = 1)でも続きの値になり、保存は要らない)
  if (wf%flow >= 1) s%wv_ramp = ramp_factor(wf, p, it)
  if (wf%mode == 2) then
    if (mod(it, wf%idt) /= 0) then
      if (wf%flow >= 2) call friction_speed(g, s)
      return
    end if
    call boundary_now(wf, p, s)
    call update_props(wf, p, g, s)
    if (wf%current) then
      call update_current(wf, p, g, s)
      call solve_steady(wf, p, g, s)
      if (wf%roller) call roller_steady(wf, p, g, s)
      call diagnose_cur(wf, p, g, s)
      if (wf%flow >= 1) call flow_coupling_cur(wf, p, g, s)
    else
      call solve_steady(wf, p, g, s)
      if (wf%roller) call roller_steady(wf, p, g, s)
      call diagnose(wf, p, g, s)
      if (wf%flow >= 1) call flow_coupling(wf, p, g, s)
    end if
    call write_steady(wf, g, s)
  else
    call boundary_now(wf, p, s)
    call update_props(wf, p, g, s)
    if (wf%current) then
      call update_current(wf, p, g, s)
      call step_unsteady_cur(wf, p, g, s)
      call diagnose_cur(wf, p, g, s)
      if (wf%flow >= 1) call flow_coupling_cur(wf, p, g, s)
    else
      call step_unsteady(wf, p, g, s)
      call diagnose(wf, p, g, s)
      if (wf%flow >= 1) call flow_coupling(wf, p, g, s)
    end if
  end if
  if (wf%flow >= 2) call friction_speed(g, s)
end subroutine


!----------------------------------------------------------------------
! 計測間隔ごと(非定常のみ。準定常は更新ごとに write_steady が書く)
!----------------------------------------------------------------------
subroutine m_wavefield_record(wf, p, g, s)
  type(t_wavefield), intent(inout) :: wf
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  if (.not. wf%enabled) return
  if (p%initialized) continue  ! 引数未使用の警告を抑制
  if (wf%mode == 1) call write_unsteady(wf, g, s)
end subroutine


!----------------------------------------------------------------------
! 破棄(save は dispose で。契約5。m_state の save より先に走る)
!----------------------------------------------------------------------
subroutine m_wavefield_dispose(wf, p, g, s)
  type(t_wavefield), intent(inout) :: wf
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  if (.not. wf%enabled) return
  if (p%f_state_save > 0) call save_state(wf, p, g, s)
  if (is_root .and. wf%un /= 0) close(wf%un)
  wf%un = 0
  if (allocated(wf%cth)) deallocate(wf%cth)
  if (allocated(wf%sth)) deallocate(wf%sth)
  if (allocated(wf%la)) deallocate(wf%la)
  if (allocated(wf%lb)) deallocate(wf%lb)
  if (allocated(wf%qa)) deallocate(wf%qa)
  if (allocated(wf%qb)) deallocate(wf%qb)
  if (allocated(wf%val)) deallocate(wf%val)
  if (allocated(wf%ebc)) deallocate(wf%ebc)
  if (allocated(wf%ae)) deallocate(wf%ae)
  if (allocated(wf%ae1)) deallocate(wf%ae1)
  if (allocated(wf%wst)) deallocate(wf%wst)
  if (allocated(wf%wcell)) deallocate(wf%wcell)
  if (allocated(wf%kw)) deallocate(wf%kw)
  if (allocated(wf%cg)) deallocate(wf%cg)
  if (allocated(wf%dtl)) deallocate(wf%dtl)
  if (allocated(wf%rrate)) deallocate(wf%rrate)
  if (allocated(wf%rcum)) deallocate(wf%rcum)
  if (allocated(wf%er)) deallocate(wf%er)
  if (allocated(wf%er1)) deallocate(wf%er1)
  if (allocated(wf%dbrk)) deallocate(wf%dbrk)
  if (allocated(wf%thm)) deallocate(wf%thm)
  if (allocated(wf%cph)) deallocate(wf%cph)
  if (allocated(wf%lar)) deallocate(wf%lar)
  if (allocated(wf%lbr)) deallocate(wf%lbr)
  if (allocated(wf%qar)) deallocate(wf%qar)
  if (allocated(wf%qbr)) deallocate(wf%qbr)
  wf%enabled = .false.
  wf%initialized = .false.
end subroutine


!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

!----------------------------------------------------------------------
! 波・流れの底面摩擦の速さ √(|u − u^S|² + (1.16 u_rms)²)(セル。Ruessink ら 2001。§88)
!   浅水流の辺は両セルの平均を摩擦の速さに使う。u・v は前ステップ確定の流速
!   (Lagrangian 平均)、u^S には立ち上げの係数を掛ける。担当帯で計算してハロを
!   交換する(この時点の s%u・s%v のハロ行は 1 ステップ前の値: 浅水流のステップ頭の
!   交換は wavefield_calc より後。ハロ行まで計算すると帯の境目の辺の摩擦が分割数で
!   変わった = W2 の MPI 検証で判明)
!----------------------------------------------------------------------
subroutine friction_speed(g, s)
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: i, j
  !$omp parallel do schedule(dynamic) private(i, j)
  do j = dcp%js, dcp%je
    do i = max(dcp%ish, 1), min(dcp%ieh, g%nx)
      s%wvsp(i,j) = sqrt((s%u(i,j) - s%wv_ramp * s%wvus(i,j))**2 + (s%v(i,j) - s%wv_ramp * s%wvvs(i,j))**2 &
                         + (1.16 * s%wvub(i,j))**2)
    end do
  end do
  !$omp end parallel do
  call par_halo_cell(s%wvsp)
end subroutine


!----------------------------------------------------------------------
! 外力の立ち上げの係数: ステップ it(t0 + it·dt → t0 + (it+1)·dt)の終わりの時刻で
! min(1, 経過時間 / wf_tramp)。wf_tramp = 0 なら常に 1
!----------------------------------------------------------------------
pure function ramp_factor(wf, p, it) result(r)
  type(t_wavefield), intent(in) :: wf
  type(t_sysparam), intent(in) :: p
  integer, intent(in) :: it
  real :: r
  if (wf%tramp > 0.0) then
    r = min(1.0, real(it + 1) * p%dt / wf%tramp)
  else
    r = 1.0
  end if
end function

!----------------------------------------------------------------------
! パラメータの検証と既定値(採用値は "(default)" 付きで表示。§62 方式)
!   既定値の出典: γ = 0.78・α = 1・γmax = 0.6・f_w = 0 は XBeach 定常モードの既定
!   (params.F90)、wf_hmin = 0.1 m と更新間隔 3600 s は SnapWave の既定。方向ビン
!   40 個(9°)は XBeach・SnapWave の既定 10° に近い 8 の倍数、方向分散 20° は本プロジェクトの
!   目安(独自。users guide)
!----------------------------------------------------------------------
subroutine setup_params(wf, p, g, list)
  type(t_wavefield), intent(inout) :: wf
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_list_wavefield), intent(in) :: list
  real :: v
  integer :: k, n

  ! --- 方向ビン ---
  wf%nth = list%wf_ntheta
  if (wf%nth == -9999) then
    wf%nth = 40
    call par_info("wavefield: wf_ntheta = 40 (default)")
  else
    call par_info("wavefield: wf_ntheta = " // itoa(wf%nth))
  end if
  if (wf%nth < 8 .or. mod(wf%nth, 8) /= 0 .or. wf%nth > 360) then
    call par_stop("list_wavefield: wf_ntheta must be a multiple of 8 between 8 and 360: " // itoa(wf%nth))
  end if

  ! --- 解法 ---
  wf%mode = list%wf_mode
  if (wf%mode == -9999) then
    wf%mode = 2
    call par_info("wavefield: wf_mode = 2 (quasi-steady) (default)")
  end if
  if (wf%mode /= 1 .and. wf%mode /= 2) then
    call par_stop("list_wavefield: wf_mode must be 1 (unsteady) or 2 (quasi-steady): " // itoa(wf%mode))
  end if
  if (wf%mode == 1) call par_info("wavefield: unsteady mode (the wave field advances in physical time every step)")
  if (wf%mode == 2) then
    v = param_default("wavefield", "dt_wave", list%dt_wave, 3600.0, " s", unset = -9999.0)
    if (v <= 0.0) call par_stop("list_wavefield: dt_wave must be > 0")
    wf%idt = max(1, nint(v / p%dt))
    call par_info("wavefield: the quasi-steady wave field is updated every " // itoa(wf%idt) // " steps")
  end if
  wf%itmax = list%wf_itmax
  if (wf%itmax == -9999) then
    wf%itmax = 4 * max(g%nx, g%ny)
    call par_info("wavefield: wf_itmax = " // itoa(wf%itmax) // " (default = 4 max(nx, ny))")
  else
    if (wf%itmax < 1) call par_stop("list_wavefield: wf_itmax must be >= 1")
    call par_info("wavefield: wf_itmax = " // itoa(wf%itmax))
  end if
  wf%tol = param_default("wavefield", "wf_tol", list%wf_tol, 1.0e-4, "", unset = -9999.0)
  if (wf%tol <= 0.0) call par_stop("list_wavefield: wf_tol must be > 0")
  wf%finit = list%f_wf_init
  if (wf%finit == -9999) wf%finit = 1
  if (wf%finit /= 0 .and. wf%finit /= 1) call par_stop("list_wavefield: f_wf_init must be 0 or 1")

  ! --- 境界の辺 ---
  do k = 1, 4
    wf%bcside(k) = list%wf_bc_side(k)
    if (wf%bcside(k) == -9999) wf%bcside(k) = 0
    if (wf%bcside(k) < 0 .or. wf%bcside(k) > 2) then
      call par_stop("list_wavefield: wf_bc_side must be 0 (absorbing), 1 (incident) or 2 (lateral Neumann)")
    end if
  end do
  if (all(wf%bcside /= 1)) call par_stop("list_wavefield: give at least one incident side (wf_bc_side = 1)")
  call par_info("wavefield: boundary sides (W, E, N, S) = " // itoa(wf%bcside(1)) // ", " &
                // itoa(wf%bcside(2)) // ", " // itoa(wf%bcside(3)) // ", " // itoa(wf%bcside(4)) &
                // " (0 absorbing, 1 incident, 2 lateral Neumann)")

  ! --- 波の種類・砕波・摩擦 ---
  wf%wtype = list%wf_wavetype
  if (wf%wtype == -9999) wf%wtype = 1
  if (wf%wtype /= 1 .and. wf%wtype /= 2) then
    call par_stop("list_wavefield: wf_wavetype must be 1 (random, H_m0) or 2 (regular, saturated breaking)")
  end if
  if (wf%wtype == 2) then
    call par_info("wavefield: regular waves (height H, saturated breaking H <= gamma h; for verification)")
    wf%cfric = 0.21
  else
    wf%cfric = 0.28
    wf%brk = list%wf_break
    if (wf%brk == -9999) then
      wf%brk = 1
      call par_info("wavefield: wf_break = 1 (Baldock et al. 1998) (default)")
    end if
    if (wf%brk /= 1 .and. wf%brk /= 2) then
      call par_stop("list_wavefield: wf_break must be 1 (Baldock et al. 1998) or 2 (Janssen & Battjes 2007)")
    end if
    if (wf%brk == 2) call par_info("wavefield: breaking by Janssen & Battjes (2007)")
    wf%alp = param_default("wavefield", "wf_alpha", list%wf_alpha, 1.0, "", unset = -9999.0)
    if (wf%alp <= 0.0) call par_stop("list_wavefield: wf_alpha must be > 0")
    wf%gamx = param_default("wavefield", "wf_gammax", list%wf_gammax, 0.6, "", unset = -9999.0)
    if (wf%gamx <= 0.0) call par_stop("list_wavefield: wf_gammax must be > 0")
  end if
  wf%gam = param_default("wavefield", "wf_gamma", list%wf_gamma, 0.78, "", unset = -9999.0)
  if (wf%gam <= 0.0 .or. wf%gam > 2.0) call par_stop("list_wavefield: wf_gamma must be in (0, 2]")
  wf%fw = param_default("wavefield", "wf_fw", list%wf_fw, 0.0, "", unset = -9999.0)
  if (wf%fw < 0.0) call par_stop("list_wavefield: wf_fw must be >= 0")
  wf%hmin = param_default("wavefield", "wf_hmin", list%wf_hmin, 0.1, " m", unset = -9999.0)
  if (wf%hmin <= 0.0) call par_stop("list_wavefield: wf_hmin must be > 0")
  wf%outdiag = (list%f_wf_outdiag == 1)
  if (list%f_wf_outdiag /= -9999 .and. list%f_wf_outdiag /= 0 .and. list%f_wf_outdiag /= 1) then
    call par_stop("list_wavefield: f_wf_outdiag must be 0 or 1")
  end if

  ! --- 流れへの作用(段 W2)---
  !   既定 0 = 段 W1 と同じ(波浪場は流れに作用しない)。ローラーの既定 1 と β = 0.1 は
  !   XBeach の既定(params.F90)
  wf%flow = list%wf_flow
  if (wf%flow == -9999) then
    wf%flow = 0
    call par_info("wavefield: wf_flow = 0 (default; the wave field does not act on the flow)")
  end if
  if (wf%flow < 0 .or. wf%flow > 2) then
    call par_stop("list_wavefield: wf_flow must be 0 (none), 1 (wave force) or 2 (wave force + GLM" &
                  // " Stokes drift + wave-current bed friction): " // itoa(wf%flow))
  end if
  if (wf%flow >= 1) then
    select case (list%f_wf_roller)
      case (-9999)
        wf%roller = .true.
        call par_info("wavefield: f_wf_roller = 1 (roller energy balance) (default)")
      case (0)
        wf%roller = .false.
      case (1)
        wf%roller = .true.
      case default
        call par_stop("list_wavefield: f_wf_roller must be 0 or 1")
    end select
    if (wf%roller) then
      wf%beta = param_default("wavefield", "wf_beta", list%wf_beta, 0.1, "", unset = -9999.0)
      if (wf%beta <= 0.0) call par_stop("list_wavefield: wf_beta must be > 0")
    end if
    ! 外力の立ち上げ(数値上の始動処理): 時間軸の起点 t0 から wf_tramp の間、外力と
    ! Stokes 輸送を 0 から 1 倍へ線形に増やす。準定常の波浪場は開始時に全域で満値に
    ! なるため、急な外力が浅水流の過渡(岸の副振動)を起こす。既定 100 s は XBeach の
    ! taper の既定(params.F90。定常の波浪場を全域で一度に与える同じ状況)
    wf%tramp = param_default("wavefield", "wf_tramp", list%wf_tramp, 100.0, "s", unset = -9999.0)
    if (wf%tramp < 0.0) call par_stop("list_wavefield: wf_tramp must be >= 0")
    if (wf%flow == 1) call par_info("wavefield: the wave force acts on the flow (wf_flow = 1)")
    if (wf%flow == 2) call par_info("wavefield: the wave force, the GLM Stokes drift and the wave-current" &
                                    // " bed friction act on the flow (wf_flow = 2)")
  else if (list%f_wf_roller /= -9999 .or. list%wf_beta > -9998.0 .or. list%wf_tramp > -9998.0) then
    call par_info("wavefield: f_wf_roller, wf_beta and wf_tramp are not used with wf_flow = 0")
  end if

  ! --- 流れの波への作用(段 W3)---
  select case (list%f_wf_current)
    case (-9999)
      wf%current = .false.
      call par_info("wavefield: f_wf_current = 0 (default; the current does not act on the waves)")
    case (0)
      wf%current = .false.
    case (1)
      wf%current = .true.
      call par_info("wavefield: the current acts on the waves (Doppler shift, refraction and transport" &
                    // " by the current, blocking; f_wf_current = 1)")
    case default
      call par_stop("list_wavefield: f_wf_current must be 0 or 1: " // itoa(list%f_wf_current))
  end select

  ! --- 沖の波(固定値または時系列)---
  wf%clock = list%wf_clock
  if (wf%clock == -9999) wf%clock = 0
  if (wf%clock /= 0 .and. wf%clock /= 1) call par_stop("list_wavefield: wf_clock must be 0 or 1")
  n = 0
  do k = 1, wf_nvalmax
    if (list%wf_val(1,k) <= -9998.0) exit       ! 時刻列の番兵で終端
    n = k
  end do
  if (n > 0) then
    wf%nval = n
    allocate(wf%val(1:5, 1:n))
    wf%val(1, 1:n) = list%wf_val(1, 1:n) * 60.0   ! 分 → 秒
    wf%val(2:5, 1:n) = list%wf_val(2:5, 1:n)
    do k = 1, n
      if (wf%val(2,k) < 0.0) call par_stop("list_wavefield: wf_val wave height must be >= 0")
      if (wf%val(2,k) > 0.0 .and. wf%val(3,k) <= 0.0) then
        call par_stop("list_wavefield: wf_val period must be > 0 when the wave height is > 0")
      end if
      if (wf%val(5,k) <= -9998.0) wf%val(5,k) = default_spread(wf%wtype)
      call check_spread(wf%val(5,k))
      if (k > 1) then
        if (wf%val(1,k) < wf%val(1,k-1)) call par_stop("list_wavefield: wf_val times must be non-decreasing")
      end if
    end do
    call par_info("wavefield: offshore wave series with " // itoa(n) // " entries (clock " &
                  // itoa(wf%clock) // ")")
  else
    if (list%wf_hm0 <= -9998.0 .or. list%wf_trep <= -9998.0 .or. list%wf_dir <= -9998.0) then
      call par_stop("list_wavefield: give wf_hm0, wf_trep and wf_dir (or a wf_val series)")
    end if
    if (list%wf_hm0 < 0.0) call par_stop("list_wavefield: wf_hm0 must be >= 0")
    if (list%wf_hm0 > 0.0 .and. list%wf_trep <= 0.0) call par_stop("list_wavefield: wf_trep must be > 0")
    wf%hfix = list%wf_hm0
    wf%tfix = list%wf_trep
    wf%dfix = list%wf_dir
    if (list%wf_spread <= -9998.0) then
      wf%sfix = default_spread(wf%wtype)
      call par_info("wavefield: wf_spread = " // rtoa(wf%sfix) // " deg (default)")
    else
      wf%sfix = list%wf_spread
    end if
    call check_spread(wf%sfix)
    call par_info("wavefield: offshore waves H = " // rtoa(wf%hfix) // " m, T = " // rtoa(wf%tfix) &
                  // " s, direction = " // rtoa(wf%dfix) // " deg, spreading = " // rtoa(wf%sfix) // " deg")
  end if
end subroutine


! 方向分散の既定: 不規則波 20°(目安)、規則波 0°(単一方向)
pure function default_spread(wtype) result(sp)
  integer, intent(in) :: wtype
  real :: sp
  if (wtype == 2) then
    sp = 0.0
  else
    sp = 20.0
  end if
end function


! 方向分散 σθ は 0(単一方向)〜cos⁰ 分布(半平面一様)の 48.8° まで
subroutine check_spread(sp)
  real, intent(in) :: sp
  if (sp < 0.0 .or. sp > 48.8) then
    call par_stop("list_wavefield: the directional spreading must be in [0, 48.8] deg " &
                  // "(0 = unidirectional, 48.8 = uniform over the half plane): " // rtoa(sp))
  end if
end subroutine


!----------------------------------------------------------------------
! 方向ビンとビンごとの 2 リンク分解(W1 は流れがないので向きで決まる)
!----------------------------------------------------------------------
subroutine setup_bins(wf, g)
  type(t_wavefield), intent(inout) :: wf
  type(t_geoinfo), intent(in) :: g
  integer :: m
  real :: th, qx, qy, ax, ay

  wf%dth = 2.0 * pi / real(wf%nth)
  allocate(wf%cth(1:wf%nth), wf%sth(1:wf%nth))
  allocate(wf%la(1:wf%nth), wf%lb(1:wf%nth), wf%qa(1:wf%nth), wf%qb(1:wf%nth))
  wf%qmax = 0.0
  do m = 1, wf%nth
    th = real(m - 1) * wf%dth
    wf%cth(m) = cos(th)
    wf%sth(m) = sin(th)
    if (abs(wf%cth(m)) < 1.0e-6) wf%cth(m) = 0.0      ! 軸の向きを厳密に格子へ揃える
    if (abs(wf%sth(m)) < 1.0e-6) wf%sth(m) = 0.0
    qx = wf%cth(m) / g%dx
    qy = wf%sth(m) / g%dy                              ! y は北向き
    ax = abs(qx)
    ay = abs(qy)
    if (abs(ax - ay) <= 1.0e-6 * max(ax, ay)) ay = ax  ! 対角の向きを厳密に揃える
    if (ax >= ay) then
      wf%la(m) = merge(0, 4, qx >= 0.0)                ! 軸 E / W
      wf%qa(m) = ax - ay
      wf%qb(m) = ay
    else
      wf%la(m) = merge(2, 6, qy >= 0.0)                ! 軸 N / S
      wf%qa(m) = ay - ax
      wf%qb(m) = ax
    end if
    wf%lb(m) = diag_code(qx, qy)
    wf%qmax = max(wf%qmax, wf%qa(m) + wf%qb(m))
  end do
end subroutine


! 物理成分の符号から対角の格子方向(NE 1・NW 3・SW 5・SE 7)
pure function diag_code(qx, qy) result(l)
  real, intent(in) :: qx, qy
  integer :: l
  if (qx >= 0.0) then
    l = merge(1, 7, qy >= 0.0)
  else
    l = merge(3, 5, qy >= 0.0)
  end if
end function


!----------------------------------------------------------------------
! 静的な波浪セル候補: 領域内・海セルでない・吸収セル(サブグリッド河道の幅・断面形の
! セル)でない。ゾーン2(マスクは全域)で帯±ハロの範囲を作る。家屋空隙(gv < 1)は
! 時間変化しうるので update_props が毎回判定する
!----------------------------------------------------------------------
subroutine setup_static_mask(wf, g)
  type(t_wavefield), intent(inout) :: wf
  type(t_geoinfo), intent(in) :: g
  integer :: i, j, nabs
  integer :: cnt(1)
  logical :: chan

  allocate(wf%wst(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0)
  chan = chn%have_width .or. sct%have_sect
  nabs = 0
  do j = max(1, dcp%jsh), min(g%ny, dcp%jeh)
    do i = max(1, dcp%ish), min(g%nx, dcp%ieh)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      if (chan) then
        if (g%rw(i,j) > 0) then
          if (j >= dcp%js .and. j <= dcp%je) nabs = nabs + 1
          cycle
        end if
      end if
      wf%wst(i,j) = 1
    end do
  end do
  if (chan) then
    cnt(1) = nabs
    call par_allreduce_sumi(cnt)
    if (cnt(1) > 0) call par_info("wavefield: " // itoa(cnt(1)) // " sub-grid channel cells absorb waves" &
                                  // " (channel width / cross-section cells are not wave cells in this version)")
  end if
end subroutine


!----------------------------------------------------------------------
! 入射の辺に接する波浪セルが開始時に 1 つもなければ警告する(沖の波が入れない。
! 典型は沖の辺が海域マスクの海セル(sw)の帯 = 解かない海。§88、wavefield_plan.md
! §7.5)。数は全ランクで集約(collective)し、表示は rank0
!----------------------------------------------------------------------
subroutine check_incident_cells(wf, g)
  type(t_wavefield), intent(in) :: wf
  type(t_geoinfo), intent(in) :: g
  integer :: i, j, cnt(1)

  cnt(1) = 0
  do j = dcp%js, dcp%je
    do i = max(1, dcp%ish), min(g%nx, dcp%ieh)
      if (wf%wcell(i,j) == 0) cycle
      if ((i == 1 .and. wf%bcside(1) == 1) .or. (i == g%nx .and. wf%bcside(2) == 1) .or. &
          (j == 1 .and. wf%bcside(3) == 1) .or. (j == g%ny .and. wf%bcside(4) == 1)) cnt(1) = cnt(1) + 1
    end do
  end do
  call par_allreduce_sumi(cnt)
  if (cnt(1) == 0 .and. is_root) then
    call par_warn("wavefield: no wave cell lies along the incident side(s) at the start, so the offshore" &
                  // " waves cannot enter (the edge cells are land, dry, sea-mask (sw) or absorbing cells)." &
                  // " Represent the offshore sea by ordinary cells with depth (e.g. f_htype = 2), not by" &
                  // " sea-mask cells")
  end if
end subroutine


!----------------------------------------------------------------------
! 現在の沖の波(固定値または時系列の線形補間。方向は短い向きの差で補間)と、
! 入射のビン別エネルギー密度
!   不規則波: E = ρ g H_m0²/16、規則波: E = ρ g H²/8。方向分布は cos^s(θ − θ0)
!   (|θ − θ0| < 90°。s は方向分散 σθ から Kuik ら(1988)の定義で逆算)をビンで
!   離散的に正規化(Σ D Δθ = 1。SnapWave と同じ)。σθ = 0 は θ0 を挟む 2 ビンへ
!   線形に配分
!----------------------------------------------------------------------
subroutine boundary_now(wf, p, s)
  type(t_wavefield), intent(inout) :: wf
  type(t_sysparam), intent(in) :: p
  type(t_state), intent(in) :: s
  real :: t, w, dd, e0, ms, dsum, x, fr
  integer :: k, m, m1, m2
  real, allocatable :: dist(:)

  if (wf%nval > 0) then
    t = s%t
    if (wf%clock == 1 .and. s%geo_morfac > 0.0) t = s%t * s%geo_morfac
    if (t <= wf%val(1,1)) then
      k = 1
      w = 0.0
    else if (t >= wf%val(1,wf%nval)) then
      k = max(1, wf%nval - 1)
      w = 1.0
      if (wf%nval == 1) w = 0.0
    else
      k = 1
      do while (wf%val(1,k+1) < t)
        k = k + 1
      end do
      if (wf%val(1,k+1) > wf%val(1,k)) then
        w = (t - wf%val(1,k)) / (wf%val(1,k+1) - wf%val(1,k))
      else
        w = 1.0
      end if
    end if
    m2 = min(k + 1, wf%nval)
    wf%hbc = (1.0 - w) * wf%val(2,k) + w * wf%val(2,m2)
    wf%tbc = (1.0 - w) * wf%val(3,k) + w * wf%val(3,m2)
    dd = modulo(wf%val(4,m2) - wf%val(4,k) + 540.0, 360.0) - 180.0
    wf%dbc = modulo(wf%val(4,k) + w * dd, 360.0)
    wf%sbc = (1.0 - w) * wf%val(5,k) + w * wf%val(5,m2)
    if (wf%hbc > 0.0 .and. wf%tbc <= 0.0) wf%hbc = 0.0     ! 周期 0 の行の補間端
  else
    wf%hbc = wf%hfix
    wf%tbc = wf%tfix
    wf%dbc = modulo(wf%dfix, 360.0)
    wf%sbc = wf%sfix
  end if
  if (wf%tbc > 0.0) then
    wf%om = 2.0 * pi / wf%tbc
  else
    wf%om = 0.0
  end if

  wf%ebc(:) = 0.0
  if (wf%hbc <= 0.0 .or. wf%om <= 0.0) return
  if (wf%wtype == 2) then
    e0 = rho * p%gg * wf%hbc**2 / 8.0
  else
    e0 = rho * p%gg * wf%hbc**2 / 16.0
  end if
  if (wf%sbc <= 0.0) then
    ! 単一方向: θ0 を挟む 2 ビンへ線形に配分(エネルギーと平均の向きをほぼ保つ)
    x = modulo(wf%dbc, 360.0) * pi / 180.0 / wf%dth
    m1 = int(x)
    fr = x - real(m1)
    m1 = modulo(m1, wf%nth) + 1
    m2 = modulo(m1, wf%nth) + 1
    wf%ebc(m1) = (1.0 - fr) * e0 / wf%dth
    wf%ebc(m2) = wf%ebc(m2) + fr * e0 / wf%dth
  else
    ms = cos_power(wf%sbc * pi / 180.0)
    allocate(dist(1:wf%nth))
    do m = 1, wf%nth
      x = cos(real(m - 1) * wf%dth - wf%dbc * pi / 180.0)
      if (x > 1.0e-6) then
        dist(m) = x**ms
      else
        dist(m) = 0.0
      end if
    end do
    dsum = sum(dist) * wf%dth
    if (dsum > 0.0) wf%ebc(:) = e0 * dist(:) / dsum
  end if
end subroutine


!----------------------------------------------------------------------
! 方向分散 σθ (rad) から cos^s 分布の指数 s を求める(Kuik ら 1988: σθ² = 2(1 − m1)、
! m1 = Γ((s+2)/2)² / (Γ((s+1)/2) Γ((s+3)/2)))。単調なので二分法
!----------------------------------------------------------------------
function cos_power(sig) result(ms)
  real, intent(in) :: sig
  real :: ms
  real(real64) :: target, lo, hi, mid, m1
  integer :: it
  target = 1.0_real64 - 0.5_real64 * real(sig, real64)**2
  lo = 0.0_real64
  hi = 1.0e5_real64
  if (first_moment(lo) >= target) then
    ms = 0.0
    return
  end if
  do it = 1, 200
    mid = 0.5_real64 * (lo + hi)
    m1 = first_moment(mid)
    if (m1 < target) then
      lo = mid
    else
      hi = mid
    end if
    if (hi - lo < 1.0e-10_real64 * max(1.0_real64, mid)) exit
  end do
  ms = real(0.5_real64 * (lo + hi))
contains
  pure function first_moment(sx) result(r)
    real(real64), intent(in) :: sx
    real(real64) :: r
    r = exp(2.0_real64 * log_gamma(0.5_real64 * (sx + 2.0_real64)) &
            - log_gamma(0.5_real64 * (sx + 1.0_real64)) - log_gamma(0.5_real64 * (sx + 3.0_real64)))
  end function
end function


!----------------------------------------------------------------------
! 波浪セルと分散関係(波数・群速度)を帯±1 行で更新する。s%h のハロは時間ループ中
! ±1 行しか現ステップの値でないので、先に交換する(collective)
!----------------------------------------------------------------------
subroutine update_props(wf, p, g, s)
  type(t_wavefield), intent(inout) :: wf
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: i, j
  real :: kh, n

  call par_halo_cell(s%h)
  !$omp parallel do schedule(dynamic) private(i, j, kh, n)
  do j = max(1, dcp%js - 1), min(g%ny, dcp%je + 1)
    do i = max(1, dcp%ish), min(g%nx, dcp%ieh)
      wf%wcell(i,j) = 0
      wf%kw(i,j) = 0.0
      wf%cg(i,j) = 0.0
      if (wf%wst(i,j) == 0) cycle
      if (s%h(i,j) <= wf%hmin) cycle
      if (s%gv(i,j) < 1.0) cycle                 ! 家屋空隙のセルは吸収(§88.1 D11)
      wf%wcell(i,j) = 1
      if (wf%om <= 0.0) cycle
      wf%kw(i,j) = disp_k(wf%om, s%h(i,j), p%gg)
      kh = wf%kw(i,j) * s%h(i,j)
      if (kh > 20.0) then
        n = 0.5
      else
        n = 0.5 * (1.0 + 2.0 * kh / sinh(2.0 * kh))
      end if
      wf%cg(i,j) = n * wf%om / wf%kw(i,j)
    end do
  end do
  !$omp end parallel do
end subroutine


!----------------------------------------------------------------------
! 分散関係 σ² = g k tanh(kh) を k について解く。初期値は Fenton & McKee (1990) の
! 陽な近似 kh ≈ y coth(y^{3/4})^{2/3}(y = σ²h/g)、続けて Newton 3 回
!----------------------------------------------------------------------
pure function disp_k(sig, h, gg) result(k)
  real, intent(in) :: sig, h, gg
  real :: k
  real :: y, kh, t, f, df
  integer :: it
  y = sig * sig * h / gg
  kh = y / tanh(y**0.75)**(2.0 / 3.0)
  do it = 1, 3
    t = tanh(kh)
    f = kh * t - y
    df = t + kh * (1.0 - t * t)
    kh = kh - f / df
  end do
  k = kh / h
end function


!----------------------------------------------------------------------
! 準定常: 局所の擬似時間刻みで収束まで反復する(前回の解から)。沖の波が 0 なら
! 定常解は 0 なので反復せずに場を消す
!----------------------------------------------------------------------
subroutine solve_steady(wf, p, g, s)
  type(t_wavefield), intent(inout) :: wf
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real :: res(1), href
  integer :: it

  if (wf%hbc <= 0.0 .or. wf%om <= 0.0) then
    wf%rrate(:,:) = 0.0_real64
    call drop_all(wf, g)
    wf%niter = 0
    wf%res = 0.0
    return
  end if
  href = wf%hbc
  if (wf%wtype == 1) href = wf%hbc / sqrt(2.0)     ! 比較は H_rms で
  wf%niter = 0
  do it = 1, wf%itmax
    if (wf%current) then
      call iterate_cur(wf, p, g, s, -1.0, href, res(1))
    else
      call iterate(wf, p, g, s, -1.0, href, res(1))
    end if
    call par_allreduce_max(res)
    wf%niter = it
    wf%res = res(1)
    if (res(1) < wf%tol) exit
  end do
  if (wf%res >= wf%tol) then
    call par_info("wavefield: the quasi-steady wave field did not converge in " // itoa(wf%itmax) &
                  // " iterations (residual " // rtoa(wf%res) // " >= wf_tol " // rtoa(wf%tol) // ")")
  end if
end subroutine


!----------------------------------------------------------------------
! 非定常: 物理時間の dt を、流出率 × Δt <= 1 になるサブステップで進める
!----------------------------------------------------------------------
subroutine step_unsteady(wf, p, g, s)
  type(t_wavefield), intent(inout) :: wf
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real :: cmax(1), dts, res, href
  integer :: i, j, k

  cmax(1) = 0.0
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (wf%wcell(i,j) == 1) cmax(1) = max(cmax(1), wf%cg(i,j))
      ! ローラーは位相速度 c = σ/k(> c_g)で運ぶ
      if (wf%roller .and. wf%wcell(i,j) == 1 .and. wf%kw(i,j) > 0.0) cmax(1) = max(cmax(1), wf%om / wf%kw(i,j))
    end do
  end do
  call par_allreduce_max(cmax)
  wf%nsub = max(1, ceiling(p%dt * cmax(1) * wf%qmax - 1.0e-6))
  dts = p%dt / real(wf%nsub)
  href = max(wf%hbc, 1.0e-6)
  do k = 1, wf%nsub
    call iterate(wf, p, g, s, dts, href, res)
    if (wf%roller) call roller_update(wf, p, g, dts)
    ! 累積(量 = 率 × Δt。乾燥化による除去は量そのもの)
    wf%rcum(:, 1:6) = wf%rcum(:, 1:6) + wf%rrate(:, 1:6) * real(dts, real64)
    wf%rcum(:, l_dry) = wf%rcum(:, l_dry) + wf%rrate(:, l_dry)
    wf%rcum(:, l_neg) = wf%rcum(:, l_neg) + wf%rrate(:, l_neg) * real(dts, real64)
  end do
end subroutine


!----------------------------------------------------------------------
! 1 回の更新(核)。dtg > 0 なら全セル同じ Δt(非定常)、dtg <= 0 なら局所の
! Δτ = 1/(最大流出率)(準定常 = 輸送について Jacobi 反復)。
!   (1) ビンごとに空間の流入出(陽的。前の値 ae から ae1 へ)
!   (2) セルごとに方向空間の屈折と源項を陰的に解き、上限で切る
!   (3) ae1 → ae、ビンごとのハロ交換(collective)
!   台帳は rrate(行部分和)へ率で書く(乾燥化による除去だけは量)。res は帯の
!   最大の波高変化 / href(全ランク集約は呼び出し側)
!----------------------------------------------------------------------
subroutine iterate(wf, p, g, s, dtg, href, res)
  type(t_wavefield), intent(inout) :: wf
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  real, intent(in) :: dtg, href
  real, intent(out) :: res
  integer :: i, j, m
  real :: resj

  ! 時間刻み
  !$omp parallel do schedule(dynamic) private(i, j)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      wf%dtl(i,j) = 0.0
      if (wf%wcell(i,j) == 0) cycle
      if (dtg > 0.0) then
        wf%dtl(i,j) = dtg
      else if (wf%cg(i,j) > 0.0) then
        wf%dtl(i,j) = 1.0 / (wf%cg(i,j) * wf%qmax)
      end if
    end do
  end do
  !$omp end parallel do

  wf%rrate(:,:) = 0.0_real64

  ! (1) 空間の流入出
  do m = 1, wf%nth
    call transport_bin(wf, g, m)
  end do

  ! (2) セル内の陰的な解き(屈折・源項・上限)
  res = 0.0
  !$omp parallel do schedule(dynamic) private(j, resj) reduction(max:res)
  do j = dcp%js, dcp%je
    call cell_row(wf, p, g, s, j, href, resj)
    res = max(res, resj)
  end do
  !$omp end parallel do

  ! (3) 確定とハロ交換
  !$omp parallel do schedule(dynamic) private(i, j, m)
  do j = dcp%js, dcp%je
    do m = 1, wf%nth
      do i = dcp%ish, dcp%ieh
        wf%ae(i,j,m) = wf%ae1(i,j,m)
      end do
    end do
  end do
  !$omp end parallel do
  do m = 1, wf%nth
    call par_halo_cell(wf%ae(:,:,m))
  end do
end subroutine


!----------------------------------------------------------------------
! ビン m の空間の流入出(受け手で集める = 書き手一意。決定的)
!   受け手 (i, j) の送り手は (i, j) − 方向 la・lb の 2 セル(W1 は流れがないので固定)。
!   送り手が格子の外なら仮想の送り手(辺の型で値が決まる)。台帳: 受け手側で境界
!   流入、自セルの流出先で境界流出・吸収を数える(すべて率)
!----------------------------------------------------------------------
subroutine transport_bin(wf, g, m)
  type(t_wavefield), intent(inout) :: wf
  type(t_geoinfo), intent(in) :: g
  integer, intent(in) :: m
  integer :: i, j, la, lb
  real :: qa, qb, fin, fbc, rout, ea
  real(real64) :: rin_bc, rout_bc, rout_abs

  la = wf%la(m)
  lb = wf%lb(m)
  qa = wf%qa(m)
  qb = wf%qb(m)
  !$omp parallel do schedule(dynamic) private(i, j, fin, fbc, rout, ea, rin_bc, rout_bc, rout_abs)
  do j = dcp%js, dcp%je
    rin_bc = 0.0_real64
    rout_bc = 0.0_real64
    rout_abs = 0.0_real64
    do i = g%wx(1,j), g%wx(2,j)
      if (wf%wcell(i,j) == 0) then
        wf%ae1(i,j,m) = 0.0
        cycle
      end if
      fin = 0.0
      fbc = 0.0
      if (qa > 0.0) call gather(i, j, la, qa, fin, fbc)
      if (qb > 0.0) call gather(i, j, lb, qb, fin, fbc)
      ea = wf%ae(i,j,m)
      rout = wf%cg(i,j) * (qa + qb)
      wf%ae1(i,j,m) = ea + wf%dtl(i,j) * (fin + fbc - rout * ea)
      rin_bc = rin_bc + real(fbc, real64)
      ! 自セルの流出先の分類(格子の外 = 境界流出、非波浪セル・閉じた対角 = 吸収)
      if (ea > 0.0) then
        if (qa > 0.0) call classify(i, j, la, wf%cg(i,j) * qa * ea, rout_bc, rout_abs)
        if (qb > 0.0) call classify(i, j, lb, wf%cg(i,j) * qb * ea, rout_bc, rout_abs)
      end if
    end do
    wf%rrate(j, l_in) = wf%rrate(j, l_in) + rin_bc * (g%dx * g%dy * wf%dth)
    wf%rrate(j, l_out) = wf%rrate(j, l_out) + rout_bc * (g%dx * g%dy * wf%dth)
    wf%rrate(j, l_abs) = wf%rrate(j, l_abs) + rout_abs * (g%dx * g%dy * wf%dth)
  end do
  !$omp end parallel do

contains

  ! 受け手 (i, j) へ格子方向 l で届く流入(送り手 = (i, j) − 方向 l)
  subroutine gather(i, j, l, q, fin, fbc)
    integer, intent(in) :: i, j, l
    real, intent(in) :: q
    real, intent(inout) :: fin, fbc
    integer :: id, jd, ic, jc
    id = i - ldi(l)
    jd = j - ldj(l)
    if (id < 1 .or. id > g%nx .or. jd < 1 .or. jd > g%ny) then
      ! 仮想の送り手(格子の外)。群速度・値は境界の内側のセル(座標を格子に寄せる)
      ic = min(max(id, 1), g%nx)
      jc = min(max(jd, 1), g%ny)
      if (wcell_in(wf, g, ic, jc) == 0) return
      select case (vside_type(wf, g, id, jd))
        case (1)
          fbc = fbc + wf%cg(ic,jc) * q * wf%ebc(m)
        case (2)
          fbc = fbc + wf%cg(ic,jc) * q * wf%ae(ic,jc,m)
        case default
          continue
      end select
      return
    end if
    if (wcell_in(wf, g, id, jd) == 0) return
    if (mod(l, 2) == 1) then
      if (diag_closed(wf, g, id, jd, i, j)) return
    end if
    fin = fin + wf%cg(id,jd) * q * wf%ae(id,jd,m)
  end subroutine

  ! 送り手 (i, j) から格子方向 l への流出 f(率)の行き先を台帳に分類する
  subroutine classify(i, j, l, f, rbc, rabs)
    integer, intent(in) :: i, j, l
    real, intent(in) :: f
    real(real64), intent(inout) :: rbc, rabs
    integer :: it, jt
    it = i + ldi(l)
    jt = j + ldj(l)
    if (it < 1 .or. it > g%nx .or. jt < 1 .or. jt > g%ny) then
      rbc = rbc + real(f, real64)
    else if (wcell_in(wf, g, it, jt) == 0) then
      rabs = rabs + real(f, real64)
    else if (mod(l, 2) == 1) then
      if (diag_closed(wf, g, i, j, it, jt)) rabs = rabs + real(f, real64)
    end if
  end subroutine

end subroutine

!----------------------------------------------------------------------
! 格子の外の仮想の送り手の辺の型(波とローラーの輸送が共有)。角(x・y とも外)は
! 入射 > 側方 Neumann > 吸収 の優先で決める(入射辺の角の外は沖の波の領域とみなす =
! 直線海岸で岸沿いに一様な解を崩さない。§88.2)
!----------------------------------------------------------------------
pure function vside_type(wf, g, id, jd) result(t)
  type(t_wavefield), intent(in) :: wf
  type(t_geoinfo), intent(in) :: g
  integer, intent(in) :: id, jd
  integer :: t
  integer :: tx, ty
  tx = -1
  ty = -1
  if (id < 1) tx = wf%bcside(1)
  if (id > g%nx) tx = wf%bcside(2)
  if (jd < 1) ty = wf%bcside(3)
  if (jd > g%ny) ty = wf%bcside(4)
  if (tx < 0) then
    t = ty
  else if (ty < 0) then
    t = tx
  else if (tx == 1 .or. ty == 1) then
    t = 1
  else if (tx == 2 .or. ty == 2) then
    t = 2
  else
    t = 0
  end if
end function


! 確保範囲・格子の外を 0 として波浪セルかを返す(帯±1 行)
pure function wcell_in(wf, g, ii, jj) result(w)
  type(t_wavefield), intent(in) :: wf
  type(t_geoinfo), intent(in) :: g
  integer, intent(in) :: ii, jj
  integer :: w
  w = 0
  if (ii < max(1, dcp%ish) .or. ii > min(g%nx, dcp%ieh)) return
  if (jj < max(1, dcp%js - 1) .or. jj > min(g%ny, dcp%je + 1)) return
  w = wf%wcell(ii, jj)
end function


! 対角リンク (id, jd) → (ir, jr) が閉じているか: 角を共有する 2 セル (ir, jd)・(id, jr)
! がともに格子内の非波浪セルなら閉じる(格子の外は開いた海とみなす)
pure function diag_closed(wf, g, id, jd, ir, jr) result(b)
  type(t_wavefield), intent(in) :: wf
  type(t_geoinfo), intent(in) :: g
  integer, intent(in) :: id, jd, ir, jr
  logical :: b
  b = .false.
  if (ir < 1 .or. ir > g%nx .or. jd < 1 .or. jd > g%ny) return
  if (id < 1 .or. id > g%nx .or. jr < 1 .or. jr > g%ny) return
  b = (wcell_in(wf, g, ir, jd) == 0) .and. (wcell_in(wf, g, id, jr) == 0)
end function



!----------------------------------------------------------------------
! 行 j のセルごとに、方向空間の屈折と源項を陰的に解き(周期境界の三重対角)、
! 上限(不規則波 H_rms <= γmax h、規則波 H <= γ h)で切る。台帳(率)と残差
!----------------------------------------------------------------------
subroutine cell_row(wf, p, g, s, j, href, resj)
  type(t_wavefield), intent(inout) :: wf
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer, intent(in) :: j
  real, intent(in) :: href
  real, intent(out) :: resj
  integer :: i, m, mp, mm
  real :: x(wf%nth), r(wf%nth), a(wf%nth), b(wf%nth), c(wf%nth), cth_(wf%nth), fc(wf%nth)
  real :: eold, enew, hold, hnew, sb, sf, dt, h, kh, fac, hx, hy, cfac, cl, cf_, q, emax, rhog
  real(real64) :: rbrk, rfric, rlim, rdry, rneg
  logical :: refr

  resj = 0.0
  rbrk = 0.0_real64
  rfric = 0.0_real64
  rlim = 0.0_real64
  rdry = 0.0_real64
  rneg = 0.0_real64
  rhog = rho * p%gg
  do i = g%wx(1,j), g%wx(2,j)
    if (wf%wcell(i,j) == 0) then
      ! 非波浪セル: 残っていたエネルギーは乾燥化による除去(量)
      eold = sum(wf%ae(i,j,:)) * wf%dth
      if (eold > 0.0) rdry = rdry + real(eold, real64)
      wf%ae1(i,j,:) = 0.0
      if (allocated(wf%dbrk)) wf%dbrk(i,j) = 0.0
      cycle
    end if
    dt = wf%dtl(i,j)
    h = s%h(i,j)
    eold = sum(wf%ae(i,j,:)) * wf%dth
    r(:) = wf%ae1(i,j,:)
    ! 源項の係数(Picard: 前の値で D/E を評価)
    sb = 0.0
    sf = 0.0
    if (eold > 0.0 .and. wf%kw(i,j) > 0.0) then
      if (wf%wtype == 1) sb = breaking(eold, wf%kw(i,j), h) / eold
      if (wf%fw > 0.0) sf = friction(eold, wf%kw(i,j), h) / eold
    end if
    ! 屈折速度(水深の勾配。非波浪の近傍は片側差分)
    refr = .false.
    kh = wf%kw(i,j) * h
    if (kh > 0.0 .and. kh <= 20.0) then
      call depth_grad(i, j, hx, hy)
      if (hx /= 0.0 .or. hy /= 0.0) then
        cfac = wf%om / sinh(2.0 * kh)
        cl = 0.25 * wf%om
        do m = 1, wf%nth
          cth_(m) = cfac * (wf%sth(m) * hx - wf%cth(m) * hy)
          cth_(m) = max(-cl, min(cl, cth_(m)))
        end do
        refr = .true.
      end if
    end if
    if (refr) then
      q = dt / wf%dth
      ! 制限つき 2 次の流束の反拡散部分(van Leer)を前の値から陽に右辺へ(遅延補正。
      ! 準定常の収束時は制限つき 2 次の流束の釣り合いを満たす。1 次風上だけでは
      ! 方向空間の数値拡散で屈折が遅れる = §88 の検証記録)
      do m = 1, wf%nth
        mp = modulo(m, wf%nth) + 1
        fc(m) = corr_flux(m, mp, 0.5 * (cth_(m) + cth_(mp)))
      end do
      do m = 1, wf%nth
        mm = modulo(m - 2, wf%nth) + 1
        r(m) = r(m) - q * (fc(m) - fc(mm))
      end do
      do m = 1, wf%nth
        mp = modulo(m, wf%nth) + 1
        mm = modulo(m - 2, wf%nth) + 1
        cf_ = 0.5 * (cth_(m) + cth_(mp))           ! 面 m+1/2
        cl = 0.5 * (cth_(mm) + cth_(m))            ! 面 m−1/2
        b(m) = 1.0 + dt * (sb + sf) + q * (max(cf_, 0.0) - min(cl, 0.0))
        c(m) = q * min(cf_, 0.0)
        a(m) = -q * max(cl, 0.0)
      end do
      call cyclic_tridiag(wf%nth, a, b, c, r, x)
    else
      fac = 1.0 / (1.0 + dt * (sb + sf))
      x(:) = r(:) * fac
    end if
    ! 負値(丸め規模)の切り捨て
    do m = 1, wf%nth
      if (x(m) < 0.0) then
        if (dt > 0.0) rneg = rneg + real(-x(m) * wf%dth / dt, real64)
        x(m) = 0.0
      end if
    end do
    enew = sum(x) * wf%dth
    rbrk = rbrk + real(sb * enew, real64)
    ! ローラーの源(段 W2): 砕波の散逸と上限で除いた分(収束時は定常の率)
    if (allocated(wf%dbrk)) wf%dbrk(i,j) = sb * enew
    rfric = rfric + real(sf * enew, real64)
    ! 上限(不規則波: H_rms <= γmax h、規則波: 飽和砕波 H <= γ h)
    if (wf%wtype == 1) then
      emax = rhog * (wf%gamx * h)**2 / 8.0
    else
      emax = rhog * (wf%gam * h)**2 / 8.0
    end if
    if (enew > emax) then
      fac = emax / enew
      x(:) = x(:) * fac
      if (dt > 0.0) rlim = rlim + real((enew - emax) / dt, real64)
      if (allocated(wf%dbrk) .and. dt > 0.0) wf%dbrk(i,j) = wf%dbrk(i,j) + (enew - emax) / dt
      enew = emax
    end if
    wf%ae1(i,j,:) = x(:)
    hold = sqrt(8.0 * eold / rhog)
    hnew = sqrt(8.0 * enew / rhog)
    resj = max(resj, abs(hnew - hold) / href)
  end do
  wf%rrate(j, l_brk) = rbrk * g%dx * g%dy
  wf%rrate(j, l_fric) = rfric * g%dx * g%dy
  wf%rrate(j, l_lim) = rlim * g%dx * g%dy
  wf%rrate(j, l_dry) = rdry * g%dx * g%dy
  wf%rrate(j, l_neg) = rneg * g%dx * g%dy

contains

  ! 面 m+1/2(m と mp の間)の制限つき反拡散流束(前の値 ae から。van Leer)。
  ! 風上が m なら c·ψ(r)/2·(E_mp − E_m)、r = (E_m − E_mm)/(E_mp − E_m)
  function corr_flux(m, mp, cf) result(f)
    integer, intent(in) :: m, mp
    real, intent(in) :: cf
    real :: f
    real :: eu, ed, euu, du, dn
    integer :: mu
    if (cf >= 0.0) then
      mu = modulo(m - 2, wf%nth) + 1
      eu = wf%ae(i,j,m)
      ed = wf%ae(i,j,mp)
      euu = wf%ae(i,j,mu)
    else
      mu = modulo(mp, wf%nth) + 1
      eu = wf%ae(i,j,mp)
      ed = wf%ae(i,j,m)
      euu = wf%ae(i,j,mu)
    end if
    du = eu - euu
    dn = ed - eu
    if (du * dn > 0.0) then
      f = cf * du * dn / (du + dn)        ! = c·ψ(r)/2·(ed − eu)、ψ = 2r/(1 + r)
    else
      f = 0.0
    end if
  end function

  ! 砕波の散逸 D_w (W/m2)
  pure function breaking(e, k, hh) result(dw)
    real, intent(in) :: e, k, hh
    real :: dw
    real :: hrms, hb, qb, rr, fr
    hrms = sqrt(8.0 * e / rhog)
    hb = 0.88 / k * tanh(wf%gam * k * hh / 0.88)
    fr = wf%om / (2.0 * pi)
    if (hb >= 30.0 * hrms) then
      ! 砕波の割合は倍精度で 0(exp(−900)。JB 型も 1 − erf(30) = 0)。比を作る前に判定して、
      ! 極小のエネルギーで (H_b/H_rms)² が overflow しないようにする
      dw = 0.0
    else if (wf%brk == 2) then
      ! Janssen & Battjes (2007)
      rr = hb / hrms
      qb = 1.0 + 4.0 / (3.0 * sqrt(pi)) * (rr**3 + 1.5 * rr) * exp(-rr * rr) - erf(rr)
      qb = max(qb, 0.0)
      dw = 3.0 * sqrt(pi) / 16.0 * wf%alp * rhog * fr * hrms**3 / hh * qb
    else
      ! Baldock ら (1998)
      qb = exp(-(hb / hrms)**2)
      dw = 0.25 * wf%alp * rhog * fr * qb * (hb**2 + hrms**2)
    end if
  end function

  ! 底面摩擦の散逸 D_f = c ρ f_w u_orb³ (W/m2)。u_orb = π H/(T sinh kh) = H σ/(2 sinh kh)
  pure function friction(e, k, hh) result(df)
    real, intent(in) :: e, k, hh
    real :: df
    real :: hrms, khh, uorb
    hrms = sqrt(8.0 * e / rhog)
    khh = k * hh
    if (khh > 20.0) then
      df = 0.0
      return
    end if
    uorb = hrms * wf%om / (2.0 * sinh(khh))
    df = wf%cfric * rho * wf%fw * uorb**3
  end function

  ! 水深の勾配(x 東、y 北)。両隣が波浪セルなら中央差分、片方なら片側差分
  subroutine depth_grad(ii, jj, gx, gy)
    integer, intent(in) :: ii, jj
    real, intent(out) :: gx, gy
    logical :: e_, w_, n_, s_
    e_ = wc(ii + 1, jj)
    w_ = wc(ii - 1, jj)
    n_ = wc(ii, jj - 1)
    s_ = wc(ii, jj + 1)
    gx = 0.0
    gy = 0.0
    if (e_ .and. w_) then
      gx = (s%h(ii+1,jj) - s%h(ii-1,jj)) / (2.0 * g%dx)
    else if (e_) then
      gx = (s%h(ii+1,jj) - s%h(ii,jj)) / g%dx
    else if (w_) then
      gx = (s%h(ii,jj) - s%h(ii-1,jj)) / g%dx
    end if
    if (n_ .and. s_) then
      gy = (s%h(ii,jj-1) - s%h(ii,jj+1)) / (2.0 * g%dy)
    else if (n_) then
      gy = (s%h(ii,jj-1) - s%h(ii,jj)) / g%dy
    else if (s_) then
      gy = (s%h(ii,jj) - s%h(ii,jj+1)) / g%dy
    end if
  end subroutine

  ! 確保範囲・格子の外を偽として波浪セルか
  pure function wc(ii, jj) result(w)
    integer, intent(in) :: ii, jj
    logical :: w
    w = .false.
    if (ii < max(1, dcp%ish) .or. ii > min(g%nx, dcp%ieh)) return
    if (jj < max(1, dcp%js - 1) .or. jj > min(g%ny, dcp%je + 1)) return
    w = (wf%wcell(ii, jj) == 1)
  end function

end subroutine


!----------------------------------------------------------------------
! 周期境界の三重対角 a(m) x(m−1) + b(m) x(m) + c(m) x(m+1) = r(m)(x(0) = x(n)、
! x(n+1) = x(1))を Sherman–Morrison で解く(対角優位の M 行列)
!----------------------------------------------------------------------
pure subroutine cyclic_tridiag(n, a, b, c, r, x)
  integer, intent(in) :: n
  real, intent(in) :: a(n), b(n), c(n), r(n)
  real, intent(out) :: x(n)
  real :: bb(n), u(n), z(n), gm, fact
  gm = -b(1)
  bb(:) = b(:)
  bb(1) = b(1) - gm
  bb(n) = b(n) - a(1) * c(n) / gm
  call tridiag(n, a, bb, c, r, x)
  u(:) = 0.0
  u(1) = gm
  u(n) = c(n)
  call tridiag(n, a, bb, c, u, z)
  fact = (x(1) + a(1) * x(n) / gm) / (1.0 + z(1) + a(1) * z(n) / gm)
  x(:) = x(:) - fact * z(:)
end subroutine


pure subroutine tridiag(n, a, b, c, r, x)
  integer, intent(in) :: n
  real, intent(in) :: a(n), b(n), c(n), r(n)
  real, intent(out) :: x(n)
  real :: cp(n), dp(n), den
  integer :: k
  cp(1) = c(1) / b(1)
  dp(1) = r(1) / b(1)
  do k = 2, n
    den = b(k) - a(k) * cp(k-1)
    cp(k) = c(k) / den
    dp(k) = (r(k) - a(k) * dp(k-1)) / den
  end do
  x(n) = dp(n)
  do k = n - 1, 1, -1
    x(k) = dp(k) - cp(k) * x(k+1)
  end do
end subroutine


!----------------------------------------------------------------------
! 場を 0 にする(準定常で沖の波が 0 のとき。残っていた分は乾燥化と同じ列に数えない
! = 定常解の置き換え)
!----------------------------------------------------------------------
subroutine drop_all(wf, g)
  type(t_wavefield), intent(inout) :: wf
  type(t_geoinfo), intent(in) :: g
  integer :: m
  if (g%initialized) continue  ! 引数未使用の警告を抑制
  do m = 1, wf%nth
    wf%ae(:,:,m) = 0.0
  end do
  if (allocated(wf%er)) wf%er(:,:) = 0.0
  if (allocated(wf%dbrk)) wf%dbrk(:,:) = 0.0
end subroutine


!----------------------------------------------------------------------
! 共有状態の診断量(波高・平均波向・軌道流速 u_rms・砕波散逸)を帯に書く
!   波高: 不規則波は H_m0 = √2 H_rms、規則波は H。u_rms = H_rms σ/(2√2 sinh kh)
!   (XBeach の定義)。無波セルの平均波向は dir_missing
!----------------------------------------------------------------------
subroutine diagnose(wf, p, g, s)
  type(t_wavefield), intent(in) :: wf
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: i, j, m
  real :: e, ex, ey, hrms, kh, rhog, hb, qb, fr, rr

  rhog = rho * p%gg
  !$omp parallel do schedule(dynamic) private(i, j, m, e, ex, ey, hrms, kh, hb, qb, fr, rr)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      s%wvh(i,j) = 0.0
      s%wvdir(i,j) = dir_missing
      s%wvub(i,j) = 0.0
      s%wvdw(i,j) = 0.0
      if (allocated(s%wver)) s%wver(i,j) = 0.0
      if (wf%wcell(i,j) == 0) cycle
      if (allocated(s%wver)) s%wver(i,j) = wf%er(i,j)
      e = 0.0
      ex = 0.0
      ey = 0.0
      do m = 1, wf%nth
        e = e + wf%ae(i,j,m)
        ex = ex + wf%ae(i,j,m) * wf%cth(m)
        ey = ey + wf%ae(i,j,m) * wf%sth(m)
      end do
      e = e * wf%dth
      if (e <= 0.0) cycle
      hrms = sqrt(8.0 * e / rhog)
      if (wf%wtype == 1) then
        s%wvh(i,j) = sqrt(2.0) * hrms
      else
        s%wvh(i,j) = hrms
      end if
      s%wvdir(i,j) = modulo(atan2(ey, ex) * 180.0 / pi, 360.0)
      kh = wf%kw(i,j) * s%h(i,j)
      if (kh > 0.0 .and. kh <= 20.0) s%wvub(i,j) = hrms * wf%om / (2.0 * sqrt(2.0) * sinh(kh))
      if (wf%wtype == 1 .and. wf%kw(i,j) > 0.0) then
        hb = 0.88 / wf%kw(i,j) * tanh(wf%gam * kh / 0.88)
        fr = wf%om / (2.0 * pi)
        if (hb >= 30.0 * hrms) then
          continue                       ! 散逸は 0 のまま(breaking の注)
        else if (wf%brk == 2) then
          rr = hb / hrms
          qb = max(1.0 + 4.0 / (3.0 * sqrt(pi)) * (rr**3 + 1.5 * rr) * exp(-rr * rr) - erf(rr), 0.0)
          s%wvdw(i,j) = 3.0 * sqrt(pi) / 16.0 * wf%alp * rhog * fr * hrms**3 / s%h(i,j) * qb
        else
          qb = exp(-(hb / hrms)**2)
          s%wvdw(i,j) = 0.25 * wf%alp * rhog * fr * qb * (hb**2 + hrms**2)
        end if
      end if
    end do
  end do
  !$omp end parallel do
end subroutine


!----------------------------------------------------------------------
! 貯留 Σ E A (J。行部分和の決定的総和。collective)
!----------------------------------------------------------------------
function storage(wf, g) result(st)
  type(t_wavefield), intent(in) :: wf
  type(t_geoinfo), intent(in) :: g
  real(real64) :: st
  real(real64) :: rows(dcp%js:dcp%je)
  integer :: i, j
  do j = dcp%js, dcp%je
    rows(j) = 0.0_real64
    do i = g%wx(1,j), g%wx(2,j)
      if (wf%wcell(i,j) == 0) cycle
      rows(j) = rows(j) + real(sum(wf%ae(i,j,:)) * wf%dth, real64)
    end do
    rows(j) = rows(j) * g%dx * g%dy
  end do
  call par_sum_rows(rows, st)
end function



!----------------------------------------------------------------------
! 平均波向 θ_m と位相速度 c = σ/k(帯±1 行。波浪セル以外は 0)。ローラーの輸送と
! 放射応力・Stokes 輸送が使う(段 W2)
!----------------------------------------------------------------------
subroutine mean_dir_speed(wf, g)
  type(t_wavefield), intent(inout) :: wf
  type(t_geoinfo), intent(in) :: g
  integer :: i, j, m
  real :: ex, ey

  !$omp parallel do schedule(dynamic) private(i, j, m, ex, ey)
  do j = max(1, dcp%js - 1), min(g%ny, dcp%je + 1)
    do i = max(1, dcp%ish), min(g%nx, dcp%ieh)
      wf%thm(i,j) = 0.0
      wf%cph(i,j) = 0.0
      if (wf%wcell(i,j) == 0 .or. wf%kw(i,j) <= 0.0) cycle
      ex = 0.0
      ey = 0.0
      do m = 1, wf%nth
        ex = ex + wf%ae(i,j,m) * wf%cth(m)
        ey = ey + wf%ae(i,j,m) * wf%sth(m)
      end do
      if (ex /= 0.0 .or. ey /= 0.0) wf%thm(i,j) = atan2(ey, ex)
      wf%cph(i,j) = wf%om / wf%kw(i,j)
    end do
  end do
  !$omp end parallel do
end subroutine


!----------------------------------------------------------------------
! ローラーの輸送の準備: 平均波向とセルごとの 2 リンク分解(帯±1 行。波と同じ規則で、
! 向きがセルごとに違う)
!----------------------------------------------------------------------
subroutine roller_prepare(wf, g)
  type(t_wavefield), intent(inout) :: wf
  type(t_geoinfo), intent(in) :: g
  integer :: i, j
  real :: c, sn, qx, qy, ax, ay

  call mean_dir_speed(wf, g)
  !$omp parallel do schedule(dynamic) private(i, j, c, sn, qx, qy, ax, ay)
  do j = max(1, dcp%js - 1), min(g%ny, dcp%je + 1)
    do i = max(1, dcp%ish), min(g%nx, dcp%ieh)
      wf%lar(i,j) = 0
      wf%lbr(i,j) = 0
      wf%qar(i,j) = 0.0
      wf%qbr(i,j) = 0.0
      if (wf%cph(i,j) <= 0.0) cycle
      c = cos(wf%thm(i,j))
      sn = sin(wf%thm(i,j))
      if (abs(c) < 1.0e-6) c = 0.0
      if (abs(sn) < 1.0e-6) sn = 0.0
      qx = c / g%dx
      qy = sn / g%dy
      ax = abs(qx)
      ay = abs(qy)
      if (abs(ax - ay) <= 1.0e-6 * max(ax, ay)) ay = ax
      if (ax >= ay) then
        wf%lar(i,j) = merge(0, 4, qx >= 0.0)
        wf%qar(i,j) = ax - ay
        wf%qbr(i,j) = ay
      else
        wf%lar(i,j) = merge(2, 6, qy >= 0.0)
        wf%qar(i,j) = ay - ax
        wf%qbr(i,j) = ax
      end if
      wf%lbr(i,j) = diag_code(qx, qy)
    end do
  end do
  !$omp end parallel do
end subroutine


!----------------------------------------------------------------------
! ローラーのエネルギー平衡の 1 回の更新(段 W2。Svendsen 1984・Nairn ら 1990・Reniers ら
! 2004、XBeach と同型):
!   ∂E_r/∂t + ∇·(c ê_r E_r) = D_b − D_r、D_r = 2βg E_r/c
!   (D_b = 砕波の散逸 + 上限で除いた分。ê_r は平均波向)。輸送は波と同じ 2 リンク分解の
!   風上(受け手で集める)、散逸は半陰的。dtg > 0 なら全セル同じ Δt、そうでなければ
!   局所の Δτ = 1/(c(q_a + q_b))。仮想の送り手は側方 Neumann なら内側のセルの値、
!   入射・吸収の辺からは入らない。res は帯の最大の変化 / eref
!----------------------------------------------------------------------
subroutine roller_iterate(wf, p, g, dtg, eref, res)
  type(t_wavefield), intent(inout) :: wf
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  real, intent(in) :: dtg, eref
  real, intent(out) :: res
  integer :: i, j, l, id, jd, ic, jc
  real :: fin, rout, dt, eo, en

  res = 0.0
  !$omp parallel do schedule(dynamic) private(i, j, l, id, jd, ic, jc, fin, rout, dt, eo, en) reduction(max:res)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      wf%er1(i,j) = 0.0
      if (wf%wcell(i,j) == 0 .or. wf%cph(i,j) <= 0.0) cycle
      fin = 0.0
      do l = 0, 7
        id = i - ldi(l)
        jd = j - ldj(l)
        if (id < 1 .or. id > g%nx .or. jd < 1 .or. jd > g%ny) then
          ic = min(max(id, 1), g%nx)
          jc = min(max(jd, 1), g%ny)
          if (wcell_in(wf, g, ic, jc) == 0) cycle
          if (vside_type(wf, g, id, jd) /= 2) cycle
          if (wf%lar(ic,jc) == l) fin = fin + wf%cph(ic,jc) * wf%qar(ic,jc) * wf%er(ic,jc)
          if (wf%lbr(ic,jc) == l) fin = fin + wf%cph(ic,jc) * wf%qbr(ic,jc) * wf%er(ic,jc)
          cycle
        end if
        if (wcell_in(wf, g, id, jd) == 0) cycle
        if (mod(l, 2) == 1) then
          if (diag_closed(wf, g, id, jd, i, j)) cycle
        end if
        if (wf%lar(id,jd) == l) fin = fin + wf%cph(id,jd) * wf%qar(id,jd) * wf%er(id,jd)
        if (wf%lbr(id,jd) == l) fin = fin + wf%cph(id,jd) * wf%qbr(id,jd) * wf%er(id,jd)
      end do
      rout = wf%cph(i,j) * (wf%qar(i,j) + wf%qbr(i,j))
      if (dtg > 0.0) then
        dt = dtg
      else
        dt = 1.0 / rout
      end if
      eo = wf%er(i,j)
      en = (eo + dt * (fin - rout * eo + wf%dbrk(i,j))) / (1.0 + dt * 2.0 * wf%beta * p%gg / wf%cph(i,j))
      en = max(en, 0.0)
      wf%er1(i,j) = en
      res = max(res, abs(en - eo) / eref)
    end do
  end do
  !$omp end parallel do
  !$omp parallel do schedule(dynamic) private(i, j)
  do j = dcp%js, dcp%je
    do i = dcp%ish, dcp%ieh
      wf%er(i,j) = wf%er1(i,j)
    end do
  end do
  !$omp end parallel do
  call par_halo_cell(wf%er)
end subroutine


! 非定常のサブステップごとのローラーの更新(向きは現在の波浪場から)
subroutine roller_update(wf, p, g, dtg)
  type(t_wavefield), intent(inout) :: wf
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  real, intent(in) :: dtg
  real :: res
  if (wf%current) then
    call roller_prepare_cur(wf, g)
  else
    call roller_prepare(wf, g)
  end if
  call roller_iterate(wf, p, g, dtg, 1.0, res)
end subroutine


!----------------------------------------------------------------------
! 準定常: 収束した波浪場の砕波の散逸を源に、ローラーを局所の擬似時間刻みで定常まで
! 反復する(前回の解から。判定は沖の波のエネルギーに対する変化で wf_tol)
!----------------------------------------------------------------------
subroutine roller_steady(wf, p, g, s)
  type(t_wavefield), intent(inout) :: wf
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  real :: eref, res(1)
  integer :: it

  if (s%initialized) continue  ! 引数未使用の警告を抑制
  wf%nrit = 0
  if (wf%hbc <= 0.0 .or. wf%om <= 0.0) then
    wf%er(:,:) = 0.0
    return
  end if
  if (wf%wtype == 2) then
    eref = rho * p%gg * wf%hbc**2 / 8.0
  else
    eref = rho * p%gg * wf%hbc**2 / 16.0
  end if
  if (wf%current) then
    call roller_prepare_cur(wf, g)
  else
    call roller_prepare(wf, g)
  end if
  do it = 1, wf%itmax
    call roller_iterate(wf, p, g, -1.0, eref, res(1))
    call par_allreduce_max(res)
    wf%nrit = it
    if (res(1) < wf%tol) exit
  end do
  if (res(1) >= wf%tol) then
    call par_info("wavefield: the roller did not converge in " // itoa(wf%itmax) // " iterations (residual " &
                  // rtoa(res(1)) // ")")
  end if
end subroutine


!----------------------------------------------------------------------
! 波→流れの受け渡し(段 W2。§88): 放射応力(波+ローラー)の発散から外力 F = −∇·S、
! Stokes 輸送 u^S(wf_flow = 2)を帯で求め、共有状態に流速と同じ向き(y = ラスタの行
! = 南)で書いてハロまで交換する(collective)。
!   S_xx = Σ E_m Δθ [n cos²θ_m + (n − 1/2)] + E_r cos²θ_r
!   S_xy = Σ E_m Δθ n cos θ_m sin θ_m + E_r cos θ_r sin θ_r
!   S_yy = Σ E_m Δθ [n sin²θ_m + (n − 1/2)] + E_r sin²θ_r、n = c_g/c
!   (Longuet-Higgins & Stewart 1964 を方向ビンで積分。ローラーは Nairn ら 1990 の近似 =
!   XBeach マニュアル)。発散は軸方向の中央差分(非波浪の近傍は片側差分)。
!   u^S = (Σ E_m Δθ ê_m + 2 E_r ê_r)/(ρ h c)(XBeach マニュアルの E ê/(ρhc) に、ローラーの
!   質量輸送 2E_r/(ρc)(Svendsen 1984)を加える)。u_rms(s%wvub)のハロも交換する
!----------------------------------------------------------------------
subroutine flow_coupling(wf, p, g, s)
  type(t_wavefield), intent(inout) :: wf
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, allocatable :: sxx(:,:), sxy(:,:), syy(:,:)
  integer :: i, j, m, j1, j2
  real :: n, e, exx, exy, eyy, mx, my, ct, st, er_, fyn, h

  if (p%initialized) continue  ! 引数未使用の警告を抑制
  call mean_dir_speed(wf, g)
  j1 = max(1, dcp%js - 1)
  j2 = min(g%ny, dcp%je + 1)
  allocate(sxx(dcp%ish:dcp%ieh, j1:j2), sxy(dcp%ish:dcp%ieh, j1:j2), syy(dcp%ish:dcp%ieh, j1:j2))
  !$omp parallel do schedule(dynamic) private(i, j, m, n, e, exx, exy, eyy, ct, st, er_)
  do j = j1, j2
    do i = dcp%ish, dcp%ieh
      sxx(i,j) = 0.0
      sxy(i,j) = 0.0
      syy(i,j) = 0.0
      if (i < 1 .or. i > g%nx) cycle
      if (wf%cph(i,j) <= 0.0) cycle
      n = wf%cg(i,j) / wf%cph(i,j)
      e = 0.0
      exx = 0.0
      exy = 0.0
      eyy = 0.0
      do m = 1, wf%nth
        e = e + wf%ae(i,j,m)
        exx = exx + wf%ae(i,j,m) * wf%cth(m)**2
        exy = exy + wf%ae(i,j,m) * wf%cth(m) * wf%sth(m)
        eyy = eyy + wf%ae(i,j,m) * wf%sth(m)**2
      end do
      e = e * wf%dth
      exx = exx * wf%dth
      exy = exy * wf%dth
      eyy = eyy * wf%dth
      sxx(i,j) = n * exx + (n - 0.5) * e
      sxy(i,j) = n * exy
      syy(i,j) = n * eyy + (n - 0.5) * e
      if (wf%roller) then
        er_ = wf%er(i,j)
        ct = cos(wf%thm(i,j))
        st = sin(wf%thm(i,j))
        sxx(i,j) = sxx(i,j) + er_ * ct * ct
        sxy(i,j) = sxy(i,j) + er_ * ct * st
        syy(i,j) = syy(i,j) + er_ * st * st
      end if
    end do
  end do
  !$omp end parallel do

  !$omp parallel do schedule(dynamic) private(i, j, m, fyn, mx, my, er_, h)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      s%wvfx(i,j) = 0.0
      s%wvfy(i,j) = 0.0
      if (wf%flow >= 2) then
        s%wvus(i,j) = 0.0
        s%wvvs(i,j) = 0.0
      end if
      if (wf%cph(i,j) <= 0.0) cycle
      ! F_x = −(∂S_xx/∂x + ∂S_xy/∂y)、F_y = −(∂S_xy/∂x + ∂S_yy/∂y)(y 北)
      s%wvfx(i,j) = -(ddx(sxx, i, j) + ddy(sxy, i, j))
      fyn = -(ddx(sxy, i, j) + ddy(syy, i, j))
      s%wvfy(i,j) = -fyn                           ! 流速と同じ向き(y = 南)へ
      if (wf%flow >= 2) then
        mx = 0.0
        my = 0.0
        do m = 1, wf%nth
          mx = mx + wf%ae(i,j,m) * wf%cth(m)
          my = my + wf%ae(i,j,m) * wf%sth(m)
        end do
        mx = mx * wf%dth
        my = my * wf%dth
        if (wf%roller) then
          er_ = wf%er(i,j)
          mx = mx + 2.0 * er_ * cos(wf%thm(i,j))
          my = my + 2.0 * er_ * sin(wf%thm(i,j))
        end if
        h = s%h(i,j)
        s%wvus(i,j) = mx / (rho * h * wf%cph(i,j))
        s%wvvs(i,j) = -my / (rho * h * wf%cph(i,j))  ! y = 南
      end if
    end do
  end do
  !$omp end parallel do
  deallocate(sxx, sxy, syy)

  call par_halo_cell(s%wvfx)
  call par_halo_cell(s%wvfy)
  if (wf%flow >= 2) then
    call par_halo_cell(s%wvus)
    call par_halo_cell(s%wvvs)
    call par_halo_cell(s%wvub)
  end if

contains

  ! ∂a/∂x(x 東)。両隣が波浪セルなら中央差分、片方なら片側差分、なければ 0
  function ddx(a, ii, jj) result(d)
    real, intent(in) :: a(dcp%ish:, j1:)
    integer, intent(in) :: ii, jj
    real :: d
    logical :: e_, w_
    e_ = wcell_in(wf, g, ii + 1, jj) == 1 .and. wf%cph(min(ii + 1, dcp%ieh), jj) > 0.0
    w_ = wcell_in(wf, g, ii - 1, jj) == 1 .and. wf%cph(max(ii - 1, dcp%ish), jj) > 0.0
    d = 0.0
    if (e_ .and. w_) then
      d = (a(ii+1,jj) - a(ii-1,jj)) / (2.0 * g%dx)
    else if (e_) then
      d = (a(ii+1,jj) - a(ii,jj)) / g%dx
    else if (w_) then
      d = (a(ii,jj) - a(ii-1,jj)) / g%dx
    end if
  end function

  ! ∂a/∂y(y 北 = j の負の向き)
  function ddy(a, ii, jj) result(d)
    real, intent(in) :: a(dcp%ish:, j1:)
    integer, intent(in) :: ii, jj
    real :: d
    logical :: n_, s_
    n_ = wcell_in(wf, g, ii, jj - 1) == 1 .and. wf%cph(ii, max(jj - 1, j1)) > 0.0
    s_ = wcell_in(wf, g, ii, jj + 1) == 1 .and. wf%cph(ii, min(jj + 1, j2)) > 0.0
    d = 0.0
    if (n_ .and. s_) then
      d = (a(ii,jj-1) - a(ii,jj+1)) / (2.0 * g%dy)
    else if (n_) then
      d = (a(ii,jj-1) - a(ii,jj)) / g%dy
    else if (s_) then
      d = (a(ii,jj) - a(ii,jj+1)) / g%dy
    end if
  end function

end subroutine

!======================================================================
! 流れの波への作用(段 W3。f_wf_current = 1。§88)
!   作用量の平衡 ∂N_m/∂t + ∇·[(c_g,m ê_m + U) N_m] + ∂(c_θ N_m)/∂θ = −D_m/σ_m
!   (Bretherton & Garrett 1968、SWAN = Booij ら 1999 の形を周波数 1 個に縮約。§5.2)を解く。
!   状態 ae はこの経路では作用量 N_m = E_m/σ_m(σ_m はセル・ビンごとの固有角周波数。
!   流れがなければ σ_m = ω で W1 のエネルギー平衡と同じ解)。作用量は時間変化する流れの
!   中の断熱不変量なので、流れが変わっても状態はそのまま(エネルギー E_m = σ_m N_m が
!   変わる)で、非定常の台帳(作用量 × ω)も閉じる。エネルギーが要る量(砕波・摩擦・上限・
!   診断量・放射応力)は σ_m N_m から求める。流れなしの経路の命令列を変えないよう、流れ
!   ありの手続きは別に置き、呼び出し元で振り分ける(段 W2 の -Ofast の教訓。§88.4)
!======================================================================

!----------------------------------------------------------------------
! 流れの場と、ビンごとの分散関係・輸送の分解・屈折速度(更新ごと。collective)
!   U は浅水流の流速(wf_flow = 2 では Lagrangian 平均 u^L。XBeach の wci と同じ)。
!   ビン m ごとに (ω − k U_m)² = g k tanh(kh)(U_m = ê_m·U)を U_m → 0 で連続な枝で
!   解き(doppler_k)、σ_m = ω − k U_m、固有の群速度 c_g,m = n σ_m/k を求め、伝播速度
!   v_m = c_g,m ê_m + U を W1 と同じ規則で 2 リンク分解する。根がない、または
!   c_g,m + U_m <= 0 のビンは阻止(sgb = 0。そこへ届く作用量は台帳「阻止」へ)。
!   屈折速度(x 東・y 北。SWAN・XBeach の形):
!     c_θ = σ/sinh 2kh (h_x sin θ − h_y cos θ) + cos θ (sin θ u_x − cos θ u_y)
!           + sin θ (sin θ v_x − cos θ v_y)、|c_θ| <= σ_m/4(W1 と同じ制限)
!   帯±1 行で求める(送り手はハロ行にもいる)。屈折速度は帯だけ
!----------------------------------------------------------------------
subroutine update_current(wf, p, g, s)
  type(t_wavefield), intent(inout) :: wf
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: i, j, m
  real :: h, um, k, sig, kh, n, cgm, px, py, ax, ay, rsum
  real :: hx, hy, uxx, uxy, uyx, uyy, cfac, cl
  logical :: ok

  ! 浅水流の流速のハロ(この時点のハロ行は 1 ステップ前の値。§88.4 の摩擦の速さの教訓)
  call par_halo_cell(s%u)
  call par_halo_cell(s%v)
  !$omp parallel do schedule(dynamic) private(i, j)
  do j = dcp%jsh, dcp%jeh
    do i = max(dcp%ish, 1), min(dcp%ieh, g%nx)
      wf%ux(i,j) = s%u(i,j)
      wf%uy(i,j) = -s%v(i,j)             ! y 北(浅水流の v は行の増える向き = 南が正)
    end do
  end do
  !$omp end parallel do

  !$omp parallel do schedule(dynamic) private(i, j, m, h, um, k, sig, kh, n, cgm, px, py, ax, ay, rsum, ok)
  do j = max(1, dcp%js - 1), min(g%ny, dcp%je + 1)
    do i = max(1, dcp%ish), min(g%nx, dcp%ieh)
      wf%rmax(i,j) = 0.0
      do m = 1, wf%nth
        wf%kb(i,j,m) = 0.0
        wf%sgb(i,j,m) = 0.0
        wf%qab(i,j,m) = 0.0
        wf%qbb(i,j,m) = 0.0
        wf%lab(i,j,m) = 0_int8
        wf%lbb(i,j,m) = 0_int8
      end do
      if (wf%wcell(i,j) == 0 .or. wf%kw(i,j) <= 0.0) cycle
      h = s%h(i,j)
      rsum = 0.0
      do m = 1, wf%nth
        um = wf%ux(i,j) * wf%cth(m) + wf%uy(i,j) * wf%sth(m)
        call doppler_k(wf%om, h, um, p%gg, wf%kw(i,j), k, sig, ok)
        if (.not. ok) cycle
        kh = k * h
        if (kh > 20.0) then
          n = 0.5
        else
          n = 0.5 * (1.0 + 2.0 * kh / sinh(2.0 * kh))
        end if
        cgm = n * sig / k
        if (cgm + um <= 0.0) cycle
        wf%kb(i,j,m) = k
        wf%sgb(i,j,m) = sig
        px = (cgm * wf%cth(m) + wf%ux(i,j)) / g%dx
        py = (cgm * wf%sth(m) + wf%uy(i,j)) / g%dy
        ax = abs(px)
        ay = abs(py)
        if (abs(ax - ay) <= 1.0e-6 * max(ax, ay)) ay = ax
        if (ax >= ay) then
          wf%lab(i,j,m) = int(merge(0, 4, px >= 0.0), int8)
          wf%qab(i,j,m) = ax - ay
          wf%qbb(i,j,m) = ay
        else
          wf%lab(i,j,m) = int(merge(2, 6, py >= 0.0), int8)
          wf%qab(i,j,m) = ay - ax
          wf%qbb(i,j,m) = ax
        end if
        wf%lbb(i,j,m) = int(diag_code(px, py), int8)
        rsum = max(rsum, wf%qab(i,j,m) + wf%qbb(i,j,m))
      end do
      wf%rmax(i,j) = rsum
    end do
  end do
  !$omp end parallel do

  !$omp parallel do schedule(dynamic) private(i, j, m, h, kh, hx, hy, uxx, uxy, uyx, uyy, cfac, cl)
  do j = dcp%js, dcp%je
    do i = max(1, dcp%ish), min(g%nx, dcp%ieh)
      do m = 1, wf%nth
        wf%cthb(i,j,m) = 0.0
      end do
      if (wf%wcell(i,j) == 0) cycle
      h = s%h(i,j)
      call grad_cell(wf, g, s%h, i, j, hx, hy)
      call grad_cell(wf, g, wf%ux, i, j, uxx, uxy)
      call grad_cell(wf, g, wf%uy, i, j, uyx, uyy)
      do m = 1, wf%nth
        if (wf%sgb(i,j,m) <= 0.0) cycle
        kh = wf%kb(i,j,m) * h
        cfac = 0.0
        if (kh <= 20.0) cfac = wf%sgb(i,j,m) / sinh(2.0 * kh)
        wf%cthb(i,j,m) = cfac * (wf%sth(m) * hx - wf%cth(m) * hy) &
                         + wf%cth(m) * (wf%sth(m) * uxx - wf%cth(m) * uxy) &
                         + wf%sth(m) * (wf%sth(m) * uyx - wf%cth(m) * uyy)
        cl = 0.25 * wf%sgb(i,j,m)
        wf%cthb(i,j,m) = max(-cl, min(cl, wf%cthb(i,j,m)))
      end do
    end do
  end do
  !$omp end parallel do
end subroutine


!----------------------------------------------------------------------
! 流れのある分散関係(段 W3): f(k) = σ_0(k) + k U_m − ω = 0、σ_0 = √(g k tanh kh) を、
! U_m → 0 で連続な枝(σ = ω − k U_m > 0)で解く。σ_0 は k に単調増加で上に凸
! (c_g = dσ_0/dk は k とともに減る)ので f も上に凸: f < 0 の側からの Newton 法は根を
! 越えずに単調に近づく。順流(U_m > 0)は f(k_0) > 0(k_0 は流れなしの根)なので 1 回目で
! 根の手前(f < 0 の側。正の k)へ移り、以後単調。逆流(U_m < 0)は f(k_0) < 0 から単調に
! 増え、f の最大(c_g + U_m = 0)に達する前に根がなければ解なし = 阻止(ok = .false.)
!----------------------------------------------------------------------
pure subroutine doppler_k(om, h, um, gg, k0, k, sig, ok)
  real, intent(in) :: om, h, um, gg, k0
  real, intent(out) :: k, sig
  logical, intent(out) :: ok
  real :: f, df, kh, s0, dk
  integer :: it

  ok = .true.
  k = k0
  sig = om
  if (um == 0.0) return
  do it = 1, 60
    kh = k * h
    if (kh > 20.0) then
      s0 = sqrt(gg * k)
      df = 0.5 * s0 / k + um
    else
      s0 = sqrt(gg * k * tanh(kh))
      df = 0.5 * s0 / k * (1.0 + 2.0 * kh / sinh(2.0 * kh)) + um
    end if
    f = s0 + k * um - om
    if (df <= 0.0) then
      ok = .false.                       ! f の最大を越えた: 逆流で根がない
      return
    end if
    dk = f / df
    k = k - dk
    if (abs(dk) <= 1.0e-10 * k) exit
  end do
  if (it > 60 .or. k <= 0.0) then
    ok = .false.                         ! 収束しない(阻止の点の重根の近く)
    return
  end if
  sig = om - k * um
  if (sig <= 0.0) ok = .false.
end subroutine


!----------------------------------------------------------------------
! セル (i, j) の勾配(x 東・y 北)。両隣が波浪セルなら中央差分、片方なら片側差分、
! なければ 0(cell_row の depth_grad と同じ規則。帯±1 行の範囲の波浪セルだけ読む)
!----------------------------------------------------------------------
pure subroutine grad_cell(wf, g, a, i, j, gx, gy)
  type(t_wavefield), intent(in) :: wf
  type(t_geoinfo), intent(in) :: g
  real, intent(in) :: a(dcp%ish:, dcp%jsh:)
  integer, intent(in) :: i, j
  real, intent(out) :: gx, gy
  logical :: e_, w_, n_, s_
  e_ = wcl(i + 1, j)
  w_ = wcl(i - 1, j)
  n_ = wcl(i, j - 1)
  s_ = wcl(i, j + 1)
  gx = 0.0
  gy = 0.0
  if (e_ .and. w_) then
    gx = (a(i+1,j) - a(i-1,j)) / (2.0 * g%dx)
  else if (e_) then
    gx = (a(i+1,j) - a(i,j)) / g%dx
  else if (w_) then
    gx = (a(i,j) - a(i-1,j)) / g%dx
  end if
  if (n_ .and. s_) then
    gy = (a(i,j-1) - a(i,j+1)) / (2.0 * g%dy)
  else if (n_) then
    gy = (a(i,j-1) - a(i,j)) / g%dy
  else if (s_) then
    gy = (a(i,j) - a(i,j+1)) / g%dy
  end if

contains

  pure function wcl(ii, jj) result(w)
    integer, intent(in) :: ii, jj
    logical :: w
    w = .false.
    if (ii < max(1, dcp%ish) .or. ii > min(g%nx, dcp%ieh)) return
    if (jj < max(1, dcp%js - 1) .or. jj > min(g%ny, dcp%je + 1)) return
    w = (wf%wcell(ii, jj) == 1)
  end function

end subroutine


!----------------------------------------------------------------------
! 1 回の更新(核。流れあり)。iterate と同じ手順で、局所の擬似時間刻みは
! Δτ = 1/(セルの最大流出率 rmax)、輸送と屈折は作用量で行う
!----------------------------------------------------------------------
subroutine iterate_cur(wf, p, g, s, dtg, href, res)
  type(t_wavefield), intent(inout) :: wf
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  real, intent(in) :: dtg, href
  real, intent(out) :: res
  integer :: i, j, m
  real :: resj

  !$omp parallel do schedule(dynamic) private(i, j)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      wf%dtl(i,j) = 0.0
      if (wf%wcell(i,j) == 0) cycle
      if (dtg > 0.0) then
        wf%dtl(i,j) = dtg
      else if (wf%rmax(i,j) > 0.0) then
        wf%dtl(i,j) = 1.0 / wf%rmax(i,j)
      end if
    end do
  end do
  !$omp end parallel do

  wf%rrate(:,:) = 0.0_real64
  wf%rblk(:) = 0.0_real64

  do m = 1, wf%nth
    call transport_bin_cur(wf, g, m)
  end do

  res = 0.0
  !$omp parallel do schedule(dynamic) private(j, resj) reduction(max:res)
  do j = dcp%js, dcp%je
    call cell_row_cur(wf, p, g, s, j, href, resj)
    res = max(res, resj)
  end do
  !$omp end parallel do

  !$omp parallel do schedule(dynamic) private(i, j, m)
  do j = dcp%js, dcp%je
    do m = 1, wf%nth
      do i = dcp%ish, dcp%ieh
        wf%ae(i,j,m) = wf%ae1(i,j,m)
      end do
    end do
  end do
  !$omp end parallel do
  do m = 1, wf%nth
    call par_halo_cell(wf%ae(:,:,m))
  end do
end subroutine


!----------------------------------------------------------------------
! ビン m の空間の流入出(流れあり。受け手で集める = 書き手一意。決定的)
!   送り手の分解はセルごとに違うので、受け手は 8 近傍すべてを調べ、送り手のビン m の
!   流出先がこの受け手なら率 × N_d を集める。N_i ← N_i + Δτ (Σ流入 − 流出率 × N_i)。
!   仮想の送り手(格子の外)は W1 と同じく境界の内側のセルの分解を使い、入射の辺は
!   沖のエネルギーを境界の内側のセルの σ で作用量にする。
!   阻止のビン(σ_i = 0)へ届く作用量は台帳「阻止」へ。台帳は作用量 × ω(率)
!----------------------------------------------------------------------
subroutine transport_bin_cur(wf, g, m)
  type(t_wavefield), intent(inout) :: wf
  type(t_geoinfo), intent(in) :: g
  integer, intent(in) :: m
  integer :: i, j, l
  real :: fin, fbc, rout, na, sg, fac
  real(real64) :: rin_bc, rout_bc, rout_abs, rb

  fac = g%dx * g%dy * wf%dth * wf%om
  !$omp parallel do schedule(dynamic) private(i, j, l, fin, fbc, rout, na, sg, rin_bc, rout_bc, rout_abs, rb)
  do j = dcp%js, dcp%je
    rin_bc = 0.0_real64
    rout_bc = 0.0_real64
    rout_abs = 0.0_real64
    rb = 0.0_real64
    do i = g%wx(1,j), g%wx(2,j)
      if (wf%wcell(i,j) == 0) then
        wf%ae1(i,j,m) = 0.0
        cycle
      end if
      fin = 0.0
      fbc = 0.0
      do l = 0, 7
        call gather_cur(i, j, l, fin, fbc)
      end do
      rin_bc = rin_bc + real(fbc, real64)
      sg = wf%sgb(i,j,m)
      if (sg <= 0.0) then
        ! 阻止のビン: 届いた作用量と残っていた分(流れが変わって阻止になった)を除く
        rb = rb + real(fin + fbc, real64)
        if (wf%dtl(i,j) > 0.0) rb = rb + real(wf%ae(i,j,m) / wf%dtl(i,j), real64)
        wf%ae1(i,j,m) = 0.0
        cycle
      end if
      na = wf%ae(i,j,m)
      rout = wf%qab(i,j,m) + wf%qbb(i,j,m)
      wf%ae1(i,j,m) = na + wf%dtl(i,j) * (fin + fbc - rout * na)
      if (na > 0.0) then
        if (wf%qab(i,j,m) > 0.0) call classify(i, j, int(wf%lab(i,j,m)), wf%qab(i,j,m) * na, rout_bc, rout_abs)
        if (wf%qbb(i,j,m) > 0.0) call classify(i, j, int(wf%lbb(i,j,m)), wf%qbb(i,j,m) * na, rout_bc, rout_abs)
      end if
    end do
    wf%rrate(j, l_in) = wf%rrate(j, l_in) + rin_bc * fac
    wf%rrate(j, l_out) = wf%rrate(j, l_out) + rout_bc * fac
    wf%rrate(j, l_abs) = wf%rrate(j, l_abs) + rout_abs * fac
    wf%rblk(j) = wf%rblk(j) + rb * fac
  end do
  !$omp end parallel do

contains

  ! 受け手 (i, j) へ格子方向 l で届く作用量の流入(送り手 = (i, j) − 方向 l)
  subroutine gather_cur(i, j, l, fin, fbc)
    integer, intent(in) :: i, j, l
    real, intent(inout) :: fin, fbc
    integer :: id, jd, ic, jc
    real :: q
    id = i - ldi(l)
    jd = j - ldj(l)
    if (id < 1 .or. id > g%nx .or. jd < 1 .or. jd > g%ny) then
      ic = min(max(id, 1), g%nx)
      jc = min(max(jd, 1), g%ny)
      if (wcell_in(wf, g, ic, jc) == 0) return
      if (wf%sgb(ic,jc,m) <= 0.0) return
      q = rate_to(ic, jc, l)
      if (q <= 0.0) return
      select case (vside_type(wf, g, id, jd))
        case (1)
          fbc = fbc + q * wf%ebc(m) / wf%sgb(ic,jc,m)
        case (2)
          fbc = fbc + q * wf%ae(ic,jc,m)
        case default
          continue
      end select
      return
    end if
    if (wcell_in(wf, g, id, jd) == 0) return
    if (wf%sgb(id,jd,m) <= 0.0) return
    q = rate_to(id, jd, l)
    if (q <= 0.0) return
    if (mod(l, 2) == 1) then
      if (diag_closed(wf, g, id, jd, i, j)) return
    end if
    fin = fin + q * wf%ae(id,jd,m)
  end subroutine

  ! 送り手 (ii, jj) からビン m で格子方向 l へ流れ出る率
  pure function rate_to(ii, jj, l) result(q)
    integer, intent(in) :: ii, jj, l
    real :: q
    q = 0.0
    if (int(wf%lab(ii,jj,m)) == l) q = q + wf%qab(ii,jj,m)
    if (int(wf%lbb(ii,jj,m)) == l) q = q + wf%qbb(ii,jj,m)
  end function

  ! 送り手 (i, j) から格子方向 l への流出 f(率)の行き先を台帳に分類する(transport_bin と同じ)
  subroutine classify(i, j, l, f, rbc, rabs)
    integer, intent(in) :: i, j, l
    real, intent(in) :: f
    real(real64), intent(inout) :: rbc, rabs
    integer :: it, jt
    it = i + ldi(l)
    jt = j + ldj(l)
    if (it < 1 .or. it > g%nx .or. jt < 1 .or. jt > g%ny) then
      rbc = rbc + real(f, real64)
    else if (wcell_in(wf, g, it, jt) == 0) then
      rabs = rabs + real(f, real64)
    else if (mod(l, 2) == 1) then
      if (diag_closed(wf, g, i, j, it, jt)) rabs = rabs + real(f, real64)
    end if
  end subroutine

end subroutine


!----------------------------------------------------------------------
! セル内の方向空間の屈折・源項・上限(流れあり。cell_row と同じ手順を作用量で)
!   源項の砕波・摩擦はエネルギー重みの平均の k̄・σ̄(代表周波数 σ̄/2π)で評価し、
!   率 D/E を作用量に掛ける(エネルギーは E = Σ σ_m N_m Δθ)。阻止のビンは 0(屈折で
!   流れ込んだ分は台帳「阻止」へ)。台帳は作用量 × ω(乾燥化による除去も)。ローラーへ
!   渡す砕波の散逸 dbrk と上限はエネルギーで
!----------------------------------------------------------------------
subroutine cell_row_cur(wf, p, g, s, j, href, resj)
  type(t_wavefield), intent(inout) :: wf
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer, intent(in) :: j
  real, intent(in) :: href
  real, intent(out) :: resj
  integer :: i, m, mp, mm
  real :: x(wf%nth), r(wf%nth), a(wf%nth), b(wf%nth), c(wf%nth), fc(wf%nth), sg(wf%nth), an(wf%nth)
  real :: eold, enew, nnew, hold, hnew, sb, sf, dt, h, fac, cf_, cl, q, emax, rhog, kbar, sbar, ew, em
  real(real64) :: rbrk, rfric, rlim, rdry, rneg, rb
  logical :: refr

  resj = 0.0
  rbrk = 0.0_real64
  rfric = 0.0_real64
  rlim = 0.0_real64
  rdry = 0.0_real64
  rneg = 0.0_real64
  rb = 0.0_real64
  rhog = rho * p%gg
  do i = g%wx(1,j), g%wx(2,j)
    if (wf%wcell(i,j) == 0) then
      eold = sum(wf%ae(i,j,:)) * wf%dth * wf%om       ! 残っていた作用量 × ω
      if (eold > 0.0) rdry = rdry + real(eold, real64)
      wf%ae1(i,j,:) = 0.0
      if (allocated(wf%dbrk)) wf%dbrk(i,j) = 0.0
      cycle
    end if
    dt = wf%dtl(i,j)
    h = s%h(i,j)
    ! 前の値のエネルギー E = Σ σ_m N_m Δθ と、エネルギー重みの平均の波数・固有角周波数
    ! (エネルギーがなければ流れなしの値)
    kbar = 0.0
    sbar = 0.0
    ew = 0.0
    do m = 1, wf%nth
      sg(m) = wf%sgb(i,j,m)
      if (sg(m) > 0.0) then
        em = sg(m) * wf%ae(i,j,m)
        kbar = kbar + em * wf%kb(i,j,m)
        sbar = sbar + em * sg(m)
        ew = ew + em
        an(m) = wf%ae(i,j,m)
        r(m) = wf%ae1(i,j,m)
      else
        an(m) = 0.0
        r(m) = 0.0
      end if
    end do
    eold = ew * wf%dth
    if (ew > 0.0) then
      kbar = kbar / ew
      sbar = sbar / ew
    else
      kbar = wf%kw(i,j)
      sbar = wf%om
    end if
    sb = 0.0
    sf = 0.0
    if (eold > 0.0 .and. kbar > 0.0) then
      if (wf%wtype == 1) sb = breaking_c(eold, kbar, h, sbar) / eold
      if (wf%fw > 0.0) sf = friction_c(eold, kbar, h, sbar) / eold
    end if
    refr = any(wf%cthb(i,j,:) /= 0.0)
    if (refr) then
      q = dt / wf%dth
      do m = 1, wf%nth
        mp = modulo(m, wf%nth) + 1
        fc(m) = corr_flux_n(m, mp, 0.5 * (wf%cthb(i,j,m) + wf%cthb(i,j,mp)))
      end do
      do m = 1, wf%nth
        mm = modulo(m - 2, wf%nth) + 1
        r(m) = r(m) - q * (fc(m) - fc(mm))
      end do
      do m = 1, wf%nth
        mp = modulo(m, wf%nth) + 1
        mm = modulo(m - 2, wf%nth) + 1
        cf_ = 0.5 * (wf%cthb(i,j,m) + wf%cthb(i,j,mp))
        cl = 0.5 * (wf%cthb(i,j,mm) + wf%cthb(i,j,m))
        b(m) = 1.0 + dt * (sb + sf) + q * (max(cf_, 0.0) - min(cl, 0.0))
        c(m) = q * min(cf_, 0.0)
        a(m) = -q * max(cl, 0.0)
      end do
      call cyclic_tridiag(wf%nth, a, b, c, r, x)
    else
      fac = 1.0 / (1.0 + dt * (sb + sf))
      x(:) = r(:) * fac
    end if
    ! 阻止のビン(屈折で流れ込んだ分を含む)と負値(丸め規模)の切り捨て
    do m = 1, wf%nth
      if (sg(m) <= 0.0) then
        if (x(m) > 0.0 .and. dt > 0.0) rb = rb + real(x(m) * wf%dth / dt, real64)
        x(m) = 0.0
      else if (x(m) < 0.0) then
        if (dt > 0.0) rneg = rneg + real(-x(m) * wf%dth * wf%om / dt, real64)
        x(m) = 0.0
      end if
    end do
    nnew = sum(x) * wf%dth
    rbrk = rbrk + real(sb * nnew * wf%om, real64)
    rfric = rfric + real(sf * nnew * wf%om, real64)
    enew = 0.0                           ! エネルギー(ローラーの源・上限・残差)
    do m = 1, wf%nth
      enew = enew + x(m) * sg(m)
    end do
    enew = enew * wf%dth
    if (allocated(wf%dbrk)) wf%dbrk(i,j) = sb * enew
    ! 上限(不規則波: H_rms <= γmax h、規則波: 飽和砕波 H <= γ h)
    if (wf%wtype == 1) then
      emax = rhog * (wf%gamx * h)**2 / 8.0
    else
      emax = rhog * (wf%gam * h)**2 / 8.0
    end if
    if (enew > emax) then
      fac = emax / enew
      x(:) = x(:) * fac
      if (dt > 0.0) rlim = rlim + real(nnew * (1.0 - fac) * wf%om / dt, real64)
      if (allocated(wf%dbrk) .and. dt > 0.0) wf%dbrk(i,j) = wf%dbrk(i,j) + (enew - emax) / dt
      enew = emax
    end if
    wf%ae1(i,j,:) = x(:)
    hold = sqrt(8.0 * eold / rhog)
    hnew = sqrt(8.0 * enew / rhog)
    resj = max(resj, abs(hnew - hold) / href)
  end do
  wf%rrate(j, l_brk) = rbrk * g%dx * g%dy
  wf%rrate(j, l_fric) = rfric * g%dx * g%dy
  wf%rrate(j, l_lim) = rlim * g%dx * g%dy
  wf%rrate(j, l_dry) = rdry * g%dx * g%dy
  wf%rrate(j, l_neg) = rneg * g%dx * g%dy
  wf%rblk(j) = wf%rblk(j) + rb * wf%om * g%dx * g%dy

contains

  ! 面 m+1/2 の制限つき反拡散流束(前の値の作用量 an から。cell_row の corr_flux と同じ形)
  function corr_flux_n(m, mp, cf) result(f)
    integer, intent(in) :: m, mp
    real, intent(in) :: cf
    real :: f
    real :: eu, ed, euu, du, dn
    integer :: mu
    if (cf >= 0.0) then
      mu = modulo(m - 2, wf%nth) + 1
      eu = an(m)
      ed = an(mp)
      euu = an(mu)
    else
      mu = modulo(mp, wf%nth) + 1
      eu = an(mp)
      ed = an(m)
      euu = an(mu)
    end if
    du = eu - euu
    dn = ed - eu
    if (du * dn > 0.0) then
      f = cf * du * dn / (du + dn)
    else
      f = 0.0
    end if
  end function

  ! 砕波の散逸 D_w (W/m2)。代表周波数は固有の σ̄/2π
  pure function breaking_c(e, k, hh, sig) result(dw)
    real, intent(in) :: e, k, hh, sig
    real :: dw
    real :: hrms, hb, qb, rr, fr
    hrms = sqrt(8.0 * e / rhog)
    hb = 0.88 / k * tanh(wf%gam * k * hh / 0.88)
    fr = sig / (2.0 * pi)
    if (hb >= 30.0 * hrms) then
      dw = 0.0                           ! breaking と同じ(極小のエネルギーの overflow を避ける)
    else if (wf%brk == 2) then
      rr = hb / hrms
      qb = 1.0 + 4.0 / (3.0 * sqrt(pi)) * (rr**3 + 1.5 * rr) * exp(-rr * rr) - erf(rr)
      qb = max(qb, 0.0)
      dw = 3.0 * sqrt(pi) / 16.0 * wf%alp * rhog * fr * hrms**3 / hh * qb
    else
      qb = exp(-(hb / hrms)**2)
      dw = 0.25 * wf%alp * rhog * fr * qb * (hb**2 + hrms**2)
    end if
  end function

  ! 底面摩擦の散逸 D_f = c ρ f_w u_orb³ (W/m2)。u_orb = H σ̄/(2 sinh k̄h)
  pure function friction_c(e, k, hh, sig) result(df)
    real, intent(in) :: e, k, hh, sig
    real :: df
    real :: hrms, khh, uorb
    hrms = sqrt(8.0 * e / rhog)
    khh = k * hh
    if (khh > 20.0) then
      df = 0.0
      return
    end if
    uorb = hrms * sig / (2.0 * sinh(khh))
    df = wf%cfric * rho * wf%fw * uorb**3
  end function

end subroutine


!----------------------------------------------------------------------
! 非定常(流れあり): 流出率 × Δt <= 1 になるサブステップで進める。率はセルの最大流出率
! rmax(流れを含む)、ローラーは (c + |U|)/min(Δx, Δy) で抑える
!----------------------------------------------------------------------
subroutine step_unsteady_cur(wf, p, g, s)
  type(t_wavefield), intent(inout) :: wf
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real :: cmax(1), dts, res, href, cr
  integer :: i, j, k, m

  cmax(1) = 0.0
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (wf%wcell(i,j) == 0) cycle
      cmax(1) = max(cmax(1), wf%rmax(i,j))
      if (wf%roller) then
        cr = 0.0
        do m = 1, wf%nth
          if (wf%sgb(i,j,m) > 0.0) cr = max(cr, wf%sgb(i,j,m) / wf%kb(i,j,m))
        end do
        cmax(1) = max(cmax(1), (cr + sqrt(wf%ux(i,j)**2 + wf%uy(i,j)**2)) / min(g%dx, g%dy))
      end if
    end do
  end do
  call par_allreduce_max(cmax)
  wf%nsub = max(1, ceiling(p%dt * cmax(1) - 1.0e-6))
  dts = p%dt / real(wf%nsub)
  href = max(wf%hbc, 1.0e-6)
  do k = 1, wf%nsub
    call iterate_cur(wf, p, g, s, dts, href, res)
    if (wf%roller) call roller_update(wf, p, g, dts)
    wf%rcum(:, 1:6) = wf%rcum(:, 1:6) + wf%rrate(:, 1:6) * real(dts, real64)
    wf%rcum(:, l_dry) = wf%rcum(:, l_dry) + wf%rrate(:, l_dry)
    wf%rcum(:, l_neg) = wf%rcum(:, l_neg) + wf%rrate(:, l_neg) * real(dts, real64)
    wf%rcblk(:) = wf%rcblk(:) + wf%rblk(:) * real(dts, real64)
  end do
end subroutine


!----------------------------------------------------------------------
! 共有状態の診断量(流れあり。diagnose と同じ量)。エネルギーは E_m = σ_m N_m、u_rms・
! 砕波散逸の k・σ はエネルギー重みの平均の k̄・σ̄(固有)
!----------------------------------------------------------------------
subroutine diagnose_cur(wf, p, g, s)
  type(t_wavefield), intent(in) :: wf
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: i, j, m
  real :: e, ex, ey, hrms, kh, rhog, hb, qb, fr, rr, kbar, sbar, em

  rhog = rho * p%gg
  !$omp parallel do schedule(dynamic) private(i, j, m, e, ex, ey, hrms, kh, hb, qb, fr, rr, kbar, sbar, em)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      s%wvh(i,j) = 0.0
      s%wvdir(i,j) = dir_missing
      s%wvub(i,j) = 0.0
      s%wvdw(i,j) = 0.0
      if (allocated(s%wver)) s%wver(i,j) = 0.0
      if (wf%wcell(i,j) == 0) cycle
      if (allocated(s%wver)) s%wver(i,j) = wf%er(i,j)
      e = 0.0
      ex = 0.0
      ey = 0.0
      kbar = 0.0
      sbar = 0.0
      do m = 1, wf%nth
        if (wf%sgb(i,j,m) <= 0.0) cycle
        em = wf%sgb(i,j,m) * wf%ae(i,j,m)
        e = e + em
        ex = ex + em * wf%cth(m)
        ey = ey + em * wf%sth(m)
        kbar = kbar + em * wf%kb(i,j,m)
        sbar = sbar + em * wf%sgb(i,j,m)
      end do
      if (e <= 0.0) cycle
      kbar = kbar / e
      sbar = sbar / e
      e = e * wf%dth
      hrms = sqrt(8.0 * e / rhog)
      if (wf%wtype == 1) then
        s%wvh(i,j) = sqrt(2.0) * hrms
      else
        s%wvh(i,j) = hrms
      end if
      s%wvdir(i,j) = modulo(atan2(ey, ex) * 180.0 / pi, 360.0)
      kh = kbar * s%h(i,j)
      if (kh > 0.0 .and. kh <= 20.0) s%wvub(i,j) = hrms * sbar / (2.0 * sqrt(2.0) * sinh(kh))
      if (wf%wtype == 1 .and. kbar > 0.0) then
        hb = 0.88 / kbar * tanh(wf%gam * kh / 0.88)
        fr = sbar / (2.0 * pi)
        if (hb >= 30.0 * hrms) then
          continue                       ! 散逸は 0 のまま(breaking の注)
        else if (wf%brk == 2) then
          rr = hb / hrms
          qb = max(1.0 + 4.0 / (3.0 * sqrt(pi)) * (rr**3 + 1.5 * rr) * exp(-rr * rr) - erf(rr), 0.0)
          s%wvdw(i,j) = 3.0 * sqrt(pi) / 16.0 * wf%alp * rhog * fr * hrms**3 / s%h(i,j) * qb
        else
          qb = exp(-(hb / hrms)**2)
          s%wvdw(i,j) = 0.25 * wf%alp * rhog * fr * qb * (hb**2 + hrms**2)
        end if
      end if
    end do
  end do
  !$omp end parallel do
end subroutine


!----------------------------------------------------------------------
! 平均波向 θ_m と位相速度 c = σ̄/k̄(流れあり。帯±1 行。σ̄・k̄ はエネルギー重みの平均、
! エネルギーがなければ流れなしの ω/k)
!----------------------------------------------------------------------
subroutine mean_dir_speed_cur(wf, g)
  type(t_wavefield), intent(inout) :: wf
  type(t_geoinfo), intent(in) :: g
  integer :: i, j, m
  real :: ex, ey, kbar, sbar, ew, em

  !$omp parallel do schedule(dynamic) private(i, j, m, ex, ey, kbar, sbar, ew, em)
  do j = max(1, dcp%js - 1), min(g%ny, dcp%je + 1)
    do i = max(1, dcp%ish), min(g%nx, dcp%ieh)
      wf%thm(i,j) = 0.0
      wf%cph(i,j) = 0.0
      if (wf%wcell(i,j) == 0 .or. wf%kw(i,j) <= 0.0) cycle
      ex = 0.0
      ey = 0.0
      kbar = 0.0
      sbar = 0.0
      ew = 0.0
      do m = 1, wf%nth
        if (wf%sgb(i,j,m) <= 0.0) cycle
        em = wf%sgb(i,j,m) * wf%ae(i,j,m)        ! E_m = σ_m N_m
        ex = ex + em * wf%cth(m)
        ey = ey + em * wf%sth(m)
        kbar = kbar + em * wf%kb(i,j,m)
        sbar = sbar + em * wf%sgb(i,j,m)
        ew = ew + em
      end do
      if (ex /= 0.0 .or. ey /= 0.0) wf%thm(i,j) = atan2(ey, ex)
      if (ew > 0.0) then
        wf%cph(i,j) = sbar / kbar
      else
        wf%cph(i,j) = wf%om / wf%kw(i,j)
      end if
    end do
  end do
  !$omp end parallel do
end subroutine


!----------------------------------------------------------------------
! ローラーの輸送の準備(流れあり): 伝播速度 c ê_θ̄ + U をセルごとに 2 リンク分解する。
! roller_iterate は率を c × q で使うので、q には率/c を入れる
!----------------------------------------------------------------------
subroutine roller_prepare_cur(wf, g)
  type(t_wavefield), intent(inout) :: wf
  type(t_geoinfo), intent(in) :: g
  integer :: i, j
  real :: c, qx, qy, ax, ay

  call mean_dir_speed_cur(wf, g)
  !$omp parallel do schedule(dynamic) private(i, j, c, qx, qy, ax, ay)
  do j = max(1, dcp%js - 1), min(g%ny, dcp%je + 1)
    do i = max(1, dcp%ish), min(g%nx, dcp%ieh)
      wf%lar(i,j) = 0
      wf%lbr(i,j) = 0
      wf%qar(i,j) = 0.0
      wf%qbr(i,j) = 0.0
      c = wf%cph(i,j)
      if (c <= 0.0) cycle
      qx = (c * cos(wf%thm(i,j)) + wf%ux(i,j)) / g%dx
      qy = (c * sin(wf%thm(i,j)) + wf%uy(i,j)) / g%dy
      ax = abs(qx)
      ay = abs(qy)
      if (abs(ax - ay) <= 1.0e-6 * max(ax, ay)) ay = ax
      if (ax >= ay) then
        wf%lar(i,j) = merge(0, 4, qx >= 0.0)
        wf%qar(i,j) = (ax - ay) / c
        wf%qbr(i,j) = ay / c
      else
        wf%lar(i,j) = merge(2, 6, qy >= 0.0)
        wf%qar(i,j) = (ay - ax) / c
        wf%qbr(i,j) = ax / c
      end if
      wf%lbr(i,j) = diag_code(qx, qy)
    end do
  end do
  !$omp end parallel do
end subroutine


!----------------------------------------------------------------------
! 波→流れの受け渡し(流れあり。flow_coupling と同じ量)。E_m = σ_m N_m、放射応力の n と
! Stokes 輸送の位相速度をビンごとの固有の値 n_m = c_g,m k_m/σ_m、c_m = σ_m/k_m にする
!   S_xx = Σ E_m Δθ [n_m cos²θ_m + (n_m − 1/2)] + E_r cos²θ_r 等、
!   u^S = Σ E_m Δθ ê_m/(ρ h c_m) + 2 E_r ê_r/(ρ h c̄)(E_m/c_m = k_m N_m = 波の運動量)
!----------------------------------------------------------------------
subroutine flow_coupling_cur(wf, p, g, s)
  type(t_wavefield), intent(inout) :: wf
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, allocatable :: sxx(:,:), sxy(:,:), syy(:,:)
  integer :: i, j, m, j1, j2
  real :: n, e, exx, exy, eyy, eh, mx, my, ct, st, er_, fyn, h, kh, em

  if (p%initialized) continue  ! 引数未使用の警告を抑制
  call mean_dir_speed_cur(wf, g)
  j1 = max(1, dcp%js - 1)
  j2 = min(g%ny, dcp%je + 1)
  allocate(sxx(dcp%ish:dcp%ieh, j1:j2), sxy(dcp%ish:dcp%ieh, j1:j2), syy(dcp%ish:dcp%ieh, j1:j2))
  !$omp parallel do schedule(dynamic) private(i, j, m, n, e, exx, exy, eyy, eh, ct, st, er_, kh, em)
  do j = j1, j2
    do i = dcp%ish, dcp%ieh
      sxx(i,j) = 0.0
      sxy(i,j) = 0.0
      syy(i,j) = 0.0
      if (i < 1 .or. i > g%nx) cycle
      if (wf%cph(i,j) <= 0.0) cycle
      e = 0.0
      exx = 0.0
      exy = 0.0
      eyy = 0.0
      eh = 0.0
      do m = 1, wf%nth
        if (wf%sgb(i,j,m) <= 0.0) cycle
        kh = wf%kb(i,j,m) * s%h(i,j)
        if (kh > 20.0) then
          n = 0.5
        else
          n = 0.5 * (1.0 + 2.0 * kh / sinh(2.0 * kh))
        end if
        em = wf%sgb(i,j,m) * wf%ae(i,j,m)
        e = e + em
        exx = exx + em * n * wf%cth(m)**2
        exy = exy + em * n * wf%cth(m) * wf%sth(m)
        eyy = eyy + em * n * wf%sth(m)**2
        eh = eh + em * (n - 0.5)
      end do
      sxx(i,j) = (exx + eh) * wf%dth
      sxy(i,j) = exy * wf%dth
      syy(i,j) = (eyy + eh) * wf%dth
      if (wf%roller) then
        er_ = wf%er(i,j)
        ct = cos(wf%thm(i,j))
        st = sin(wf%thm(i,j))
        sxx(i,j) = sxx(i,j) + er_ * ct * ct
        sxy(i,j) = sxy(i,j) + er_ * ct * st
        syy(i,j) = syy(i,j) + er_ * st * st
      end if
    end do
  end do
  !$omp end parallel do

  !$omp parallel do schedule(dynamic) private(i, j, m, fyn, mx, my, er_, h)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      s%wvfx(i,j) = 0.0
      s%wvfy(i,j) = 0.0
      if (wf%flow >= 2) then
        s%wvus(i,j) = 0.0
        s%wvvs(i,j) = 0.0
      end if
      if (wf%cph(i,j) <= 0.0) cycle
      s%wvfx(i,j) = -(ddx(sxx, i, j) + ddy(sxy, i, j))
      fyn = -(ddx(sxy, i, j) + ddy(syy, i, j))
      s%wvfy(i,j) = -fyn                           ! 流速と同じ向き(y = 南)へ
      if (wf%flow >= 2) then
        mx = 0.0
        my = 0.0
        do m = 1, wf%nth
          if (wf%sgb(i,j,m) <= 0.0) cycle
          mx = mx + wf%ae(i,j,m) * wf%cth(m) * wf%kb(i,j,m)
          my = my + wf%ae(i,j,m) * wf%sth(m) * wf%kb(i,j,m)
        end do
        mx = mx * wf%dth
        my = my * wf%dth
        if (wf%roller) then
          er_ = wf%er(i,j)
          mx = mx + 2.0 * er_ * cos(wf%thm(i,j)) / wf%cph(i,j)
          my = my + 2.0 * er_ * sin(wf%thm(i,j)) / wf%cph(i,j)
        end if
        h = s%h(i,j)
        s%wvus(i,j) = mx / (rho * h)
        s%wvvs(i,j) = -my / (rho * h)              ! y = 南
      end if
    end do
  end do
  !$omp end parallel do
  deallocate(sxx, sxy, syy)

  call par_halo_cell(s%wvfx)
  call par_halo_cell(s%wvfy)
  if (wf%flow >= 2) then
    call par_halo_cell(s%wvus)
    call par_halo_cell(s%wvvs)
    call par_halo_cell(s%wvub)
  end if

contains

  ! ∂a/∂x(x 東。flow_coupling の ddx と同じ)
  function ddx(a, ii, jj) result(d)
    real, intent(in) :: a(dcp%ish:, j1:)
    integer, intent(in) :: ii, jj
    real :: d
    logical :: e_, w_
    e_ = wcell_in(wf, g, ii + 1, jj) == 1 .and. wf%cph(min(ii + 1, dcp%ieh), jj) > 0.0
    w_ = wcell_in(wf, g, ii - 1, jj) == 1 .and. wf%cph(max(ii - 1, dcp%ish), jj) > 0.0
    d = 0.0
    if (e_ .and. w_) then
      d = (a(ii+1,jj) - a(ii-1,jj)) / (2.0 * g%dx)
    else if (e_) then
      d = (a(ii+1,jj) - a(ii,jj)) / g%dx
    else if (w_) then
      d = (a(ii,jj) - a(ii-1,jj)) / g%dx
    end if
  end function

  ! ∂a/∂y(y 北 = j の負の向き。flow_coupling の ddy と同じ)
  function ddy(a, ii, jj) result(d)
    real, intent(in) :: a(dcp%ish:, j1:)
    integer, intent(in) :: ii, jj
    real :: d
    logical :: n_, s_
    n_ = wcell_in(wf, g, ii, jj - 1) == 1 .and. wf%cph(ii, max(jj - 1, j1)) > 0.0
    s_ = wcell_in(wf, g, ii, jj + 1) == 1 .and. wf%cph(ii, min(jj + 1, j2)) > 0.0
    d = 0.0
    if (n_ .and. s_) then
      d = (a(ii,jj-1) - a(ii,jj+1)) / (2.0 * g%dy)
    else if (n_) then
      d = (a(ii,jj-1) - a(ii,jj)) / g%dy
    else if (s_) then
      d = (a(ii,jj) - a(ii,jj+1)) / g%dy
    end if
  end function

end subroutine


!----------------------------------------------------------------------
! 貯留(流れあり): Σ N_m ω Δθ A(作用量 × ω。台帳と同じ単位。collective)
!----------------------------------------------------------------------
function storage_cur(wf, g) result(st)
  type(t_wavefield), intent(in) :: wf
  type(t_geoinfo), intent(in) :: g
  real(real64) :: st
  real(real64) :: rows(dcp%js:dcp%je)
  integer :: i, j, m
  real :: sn
  do j = dcp%js, dcp%je
    rows(j) = 0.0_real64
    do i = g%wx(1,j), g%wx(2,j)
      if (wf%wcell(i,j) == 0) cycle
      sn = 0.0
      do m = 1, wf%nth
        sn = sn + wf%ae(i,j,m)
      end do
      rows(j) = rows(j) + real(sn * wf%dth * wf%om, real64)
    end do
    rows(j) = rows(j) * g%dx * g%dy
  end do
  call par_sum_rows(rows, st)
end function


!----------------------------------------------------------------------
! 台帳の CSV(rank0)
!----------------------------------------------------------------------
subroutine open_csv(wf, p)
  type(t_wavefield), intent(inout) :: wf
  type(t_sysparam), intent(in) :: p
  logical :: found
  if (.not. is_root) return
  ! 再開(f_state_restore = 1)は同じ結果ディレクトリの CSV があれば追記する
  ! (無ければ新しく見出しから書く。累積量は保存時から引き継ぐ)
  if (p%f_state_restore == 1) then
    inquire(file=trim(p%dir_result)//'/wavefield.csv', exist=found)
    if (found) then
      open(newunit=wf%un, file=trim(p%dir_result)//'/wavefield.csv', status='old', position='append')
      return
    end if
  end if
  open(newunit=wf%un, file=trim(p%dir_result)//'/wavefield.csv', status='replace')
  if (wf%mode == 2) then
    if (wf%current) then
      write(wf%un, '(a)') "t_s,it,iter,residual,H_bc,T_bc,dir_bc,in_W,out_W,absorbed_W,breaking_W," // &
                          "friction_W,limit_W,dry_J,trunc_W,imbalance_W,storage_J,blocked_W"
    else
      write(wf%un, '(a)') "t_s,it,iter,residual,H_bc,T_bc,dir_bc,in_W,out_W,absorbed_W,breaking_W," // &
                          "friction_W,limit_W,dry_J,trunc_W,imbalance_W,storage_J"
    end if
  else
    if (wf%current) then
      write(wf%un, '(a)') "t_s,it,nsub,H_bc,T_bc,dir_bc,in_J,out_J,absorbed_J,breaking_J,friction_J," // &
                          "limit_J,dry_J,trunc_J,storage_J,storage0_J,imbalance_J,blocked_J"
    else
      write(wf%un, '(a)') "t_s,it,nsub,H_bc,T_bc,dir_bc,in_J,out_J,absorbed_J,breaking_J,friction_J," // &
                          "limit_J,dry_J,trunc_J,storage_J,storage0_J,imbalance_J"
    end if
  end if
end subroutine


subroutine write_steady(wf, g, s)
  type(t_wavefield), intent(inout) :: wf
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  real(real64) :: v(nl), st, imb, vb
  integer :: k
  do k = 1, nl
    call par_sum_rows(wf%rrate(:, k), v(k))
  end do
  vb = 0.0_real64
  if (wf%current) then
    ! 流れがあるときの台帳は作用量 × ω(作用量の保存で閉じる。§88)
    call par_sum_rows(wf%rblk, vb)
    st = storage_cur(wf, g)
  else
    st = storage(wf, g)
  end if
  imb = v(l_in) - v(l_out) - v(l_abs) - v(l_brk) - v(l_fric) - v(l_lim) + v(l_neg)
  if (wf%current) imb = imb - vb
  if (is_root .and. wf%un /= 0) then
    if (wf%current) then
      write(wf%un, '(f0.2,",",i0,",",i0,",",es12.5,3(",",f0.4),11(",",es15.7))') s%t, s%it, wf%niter, &
        wf%res, wf%hbc, wf%tbc, wf%dbc, v(l_in), v(l_out), v(l_abs), v(l_brk), v(l_fric), v(l_lim), &
        v(l_dry), v(l_neg), imb, st, vb
    else
      write(wf%un, '(f0.2,",",i0,",",i0,",",es12.5,3(",",f0.4),10(",",es15.7))') s%t, s%it, wf%niter, &
        wf%res, wf%hbc, wf%tbc, wf%dbc, v(l_in), v(l_out), v(l_abs), v(l_brk), v(l_fric), v(l_lim), &
        v(l_dry), v(l_neg), imb, st
    end if
    flush(wf%un)
  end if
end subroutine


subroutine write_unsteady(wf, g, s)
  type(t_wavefield), intent(inout) :: wf
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  real(real64) :: v(nl), st, imb, vb
  integer :: k
  do k = 1, nl
    call par_sum_rows(wf%rcum(:, k), v(k))
    v(k) = v(k) + wf%cum0(k)
  end do
  vb = 0.0_real64
  if (wf%current) then
    call par_sum_rows(wf%rcblk, vb)
    vb = vb + wf%cumblk0
    st = storage_cur(wf, g)
  else
    st = storage(wf, g)
  end if
  imb = (st - wf%store0) - (v(l_in) - v(l_out) - v(l_abs) - v(l_brk) - v(l_fric) - v(l_lim) &
        - v(l_dry) + v(l_neg))
  if (wf%current) imb = imb + vb
  if (is_root .and. wf%un /= 0) then
    if (wf%current) then
      write(wf%un, '(f0.2,",",i0,",",i0,3(",",f0.4),12(",",es15.7))') s%t, s%it, wf%nsub, wf%hbc, &
        wf%tbc, wf%dbc, v(l_in), v(l_out), v(l_abs), v(l_brk), v(l_fric), v(l_lim), v(l_dry), v(l_neg), &
        st, wf%store0, imb, vb
    else
      write(wf%un, '(f0.2,",",i0,",",i0,3(",",f0.4),11(",",es15.7))') s%t, s%it, wf%nsub, wf%hbc, &
        wf%tbc, wf%dbc, v(l_in), v(l_out), v(l_abs), v(l_brk), v(l_fric), v(l_lim), v(l_dry), v(l_neg), &
        st, wf%store0, imb
    end if
    flush(wf%un)
  end if
end subroutine


!----------------------------------------------------------------------
! 保存・復元(私有ファイル。契約5)
!   wavefield_info.txt: 形式の版・ビン数・モード・非定常の累積台帳と起点の貯留、
!     段 W2 の拡張の有無(flow・roller・ndiag。旧ファイルは無く、既定 0 で読む)、
!     段 W3 の阻止の累積 cumblk と状態の量 state(0: エネルギー E_m、1: 流れありの作用量
!     N_m。同じく後方互換の拡張)(全ランクが読む)
!   wavefield.dat: ビンごとの状態(state。m_restart の RLE。collective)、続けて
!     ローラー E_r(roller = 1)、診断量 4 面(ndiag = 1: 波高・平均波向・u_rms・砕波散逸)、
!     外力 2 面(flow >= 1)、Stokes 輸送 2 面(flow = 2)。準定常は更新の間これらを
!     保持するので、復元して使うと再開がビット一致する(§88)
!----------------------------------------------------------------------
subroutine save_state(wf, p, g, s)
  type(t_wavefield), intent(in) :: wf
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer :: un, m, version, nth, mode, flow, roller, ndiag, state
  real(real64) :: cum(nl), store0, cumblk
  namelist /wavefield_info/ version, nth, mode, cum, store0, flow, roller, ndiag, cumblk, state

  do m = 1, nl
    call par_sum_rows(wf%rcum(:, m), cum(m))
    cum(m) = cum(m) + wf%cum0(m)
  end do
  cumblk = 0.0_real64
  if (wf%current) then
    call par_sum_rows(wf%rcblk, cumblk)
    cumblk = cumblk + wf%cumblk0
  end if
  if (g%initialized) continue  ! 引数未使用の警告を抑制
  version = save_version
  nth = wf%nth
  mode = wf%mode
  store0 = wf%store0
  flow = wf%flow
  roller = merge(1, 0, wf%roller)
  ndiag = 1
  state = merge(1, 0, wf%current)
  if (is_root) then
    call sysdep_mkdir(p%dir_save)
    open(newunit=un, file=trim(p%dir_save)//'/wavefield_info.txt', status='replace')
    write(un, nml=wavefield_info)
    close(un)
    open(newunit=un, file=trim(p%dir_save)//'/wavefield.dat', form='unformatted', status='replace')
  end if
  do m = 1, wf%nth
    call restart_write_cell(un, wf%ae(:,:,m))
  end do
  if (wf%roller) call restart_write_cell(un, wf%er)
  call restart_write_cell(un, s%wvh)
  call restart_write_cell(un, s%wvdir)
  call restart_write_cell(un, s%wvub)
  call restart_write_cell(un, s%wvdw)
  if (wf%flow >= 1) then
    call restart_write_cell(un, s%wvfx)
    call restart_write_cell(un, s%wvfy)
  end if
  if (wf%flow >= 2) then
    call restart_write_cell(un, s%wvus)
    call restart_write_cell(un, s%wvvs)
  end if
  if (is_root) close(un)
end subroutine


subroutine restore_state(wf, p, s, have_diag, have_force)
  type(t_wavefield), intent(inout) :: wf
  type(t_sysparam), intent(in) :: p
  type(t_state), intent(inout) :: s
  logical, intent(out) :: have_diag, have_force
  character(:), allocatable :: fname
  logical :: found
  integer :: un, ios, m, version, nth, mode, flow, roller, ndiag, state, i, j
  real(real64) :: cum(nl), store0, cumblk
  real, allocatable :: tmp(:,:)
  namelist /wavefield_info/ version, nth, mode, cum, store0, flow, roller, ndiag, cumblk, state

  fname = trim(p%dir_save)//'/wavefield_info.txt'
  inquire(file=fname, exist=found)
  if (.not. found) then
    call par_stop("wavefield: state file not found (was fn_wavefield enabled when saving): "//fname)
  end if
  version = -1
  nth = -1
  mode = -1
  cum(:) = 0.0_real64
  store0 = 0.0_real64
  flow = 0
  roller = 0
  ndiag = 0
  cumblk = 0.0_real64
  state = 0
  open(newunit=un, file=fname, status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("wavefield: cannot open "//fname)
  read(un, nml=wavefield_info, iostat=ios)
  close(un)
  if (ios /= 0) call par_stop("wavefield: cannot read "//fname)
  if (version /= save_version) then
    call par_stop("wavefield: state file format version "//itoa(version)//" does not match "//itoa(save_version))
  end if
  if (nth /= wf%nth) then
    call par_stop("wavefield: wf_ntheta ("//itoa(wf%nth)//") differs from the saved state ("//itoa(nth)//")")
  end if
  if (mode /= wf%mode) then
    call par_stop("wavefield: wf_mode ("//itoa(wf%mode)//") differs from the saved state ("//itoa(mode)//")")
  end if
  if (state == 1 .and. .not. wf%current) then
    call par_stop("wavefield: the saved wave field holds wave action (saved with f_wf_current = 1);" &
                  //" restore it with f_wf_current = 1")
  end if
  if (p%f_state_restore == 1) then
    wf%cum0(:) = cum(:)
    wf%store0 = store0
    wf%cumblk0 = cumblk
  end if
  fname = trim(p%dir_save)//'/wavefield.dat'
  inquire(file=fname, exist=found)                ! 全ランクが同じ判定をする(collective 安全)
  if (.not. found) call par_stop("wavefield: state file not found: "//fname)
  allocate(tmp(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  if (is_root) open(newunit=un, file=fname, form='unformatted', status='old', action='read')
  do m = 1, wf%nth
    call restart_read_cell(un, wf%ae(:,:,m))
  end do
  if (state == 0 .and. wf%current) then
    ! 流れなしで保存したエネルギーを作用量へ(init が求めた σ_m で。阻止のビンは 0)
    call par_info("wavefield: the saved wave energy is converted to wave action with the current at restart")
    do m = 1, wf%nth
      do j = dcp%js, dcp%je
        do i = max(1, dcp%ish), min(dcp%nx_g, dcp%ieh)
          if (wf%sgb(i,j,m) > 0.0) then
            wf%ae(i,j,m) = wf%ae(i,j,m) / wf%sgb(i,j,m)
          else
            wf%ae(i,j,m) = 0.0
          end if
        end do
      end do
      call par_halo_cell(wf%ae(:,:,m))
    end do
  end if
  ! 段 W2 の拡張(保存時に無かったものは既定: ローラー 0、診断量・外力は init が求め直す)
  if (roller == 1) then
    if (wf%roller) then
      call restart_read_cell(un, wf%er)
    else
      call restart_read_cell(un, tmp)
    end if
  end if
  if (wf%roller .and. roller /= 1) call par_info("wavefield: the saved state has no roller energy; it starts from 0")
  have_diag = (ndiag == 1)
  if (have_diag) then
    call restart_read_cell(un, s%wvh)
    call restart_read_cell(un, s%wvdir)
    call restart_read_cell(un, s%wvub)
    call restart_read_cell(un, s%wvdw)
  end if
  if (flow >= 1) then
    if (wf%flow >= 1) then
      call restart_read_cell(un, s%wvfx)
      call restart_read_cell(un, s%wvfy)
    else
      call restart_read_cell(un, tmp)
      call restart_read_cell(un, tmp)
    end if
  end if
  if (flow >= 2) then
    if (wf%flow >= 2) then
      call restart_read_cell(un, s%wvus)
      call restart_read_cell(un, s%wvvs)
    else
      call restart_read_cell(un, tmp)
      call restart_read_cell(un, tmp)
    end if
  end if
  if (is_root) close(un)
  deallocate(tmp)
  have_force = (wf%flow >= 1 .and. flow >= wf%flow)
  if (wf%flow >= 1 .and. .not. have_force) then
    call par_info("wavefield: the saved state has no wave force for wf_flow = "//itoa(wf%flow) &
                  //"; it is recomputed from the restored wave field")
  end if
  ! 流れが読む量はハロまで(帯は復元済み)
  if (wf%roller) call par_halo_cell(wf%er)
  if (have_force) then
    call par_halo_cell(s%wvfx)
    call par_halo_cell(s%wvfy)
    if (wf%flow >= 2) then
      call par_halo_cell(s%wvus)
      call par_halo_cell(s%wvvs)
      call par_halo_cell(s%wvub)
    end if
  end if
end subroutine


!----------------------------------------------------------------------
! 無効なのに私有ファイルが dir_save にあれば停止する(保存時の波浪場を黙って
! 捨てない。§16.2 の stop_if_orphan_state と同じ門番)
!----------------------------------------------------------------------
subroutine stop_if_orphan(p)
  type(t_sysparam), intent(in) :: p
  logical :: found
  inquire(file=trim(p%dir_save)//'/wavefield_info.txt', exist=found)
  if (found) then
    call par_stop("wavefield: wavefield_info.txt exists in "//trim(p%dir_save)//" but the wave field is" &
                  //" not enabled at restart (its stored state would be dropped); enable fn_wavefield or" &
                  //" remove the file if the drop is intended")
  end if
end subroutine

end module
