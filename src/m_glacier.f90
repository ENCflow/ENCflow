module m_glacier
  ! ================= 氷河プロセスモジュール(§45) =================
  ! 涵養(雪→氷)・消耗(氷面の度日融解)・氷体流動(SIA)・氷河侵食・
  ! 雪の重力再配分(雪崩)を担う。fn_glacier の指定で有効化(&list_glacier。
  ! f_glacier=0 で一時無効化)。無効時は s%hi を確保せず呼び出しもしない
  ! (ゼロコスト。§0)。設計・検証・既知の妥協の正本は docs/glacier_plan.md。
  !
  ! 【状態】 s%hi = 氷厚 (m 氷柱。幾何面積基底)。水当量は hi×(ρi/ρw)。
  !   リスタートはモデル私有ファイル glacier.dat(RLE。契約5)。
  !
  ! 【時間の二重台帳(MORFAC 方式。浮遊砂 E-D の台帳分離 §19.3 と同型)】
  !   氷河の流動・侵食・氷収支は「地形時間」dts = dt×idt×morfac で進み、
  !   水柱(s%h, s%swe)との交換は「水文時間」で行う:
  !     - 氷面融解: 水の生成は dt×1(融解水が水文・洪水を駆動)、
  !       氷の減少は ×morfac(1回の計算 = morfac 回の同一イベント)
  !     - 氷化(フィルン): swe の減少は水文時間の割合(季節雪の寿命を保つ)、
  !       氷の増加は ×morfac(地形時間の涵養量)
  !   morfac=1 では両台帳が厳密に一致し質量が機械精度で保存される。
  !   morfac>1 の氷⇄水の質量不一致は MORFAC の既知の近似(文書化済み)。
  !   morfac は geomorph と共通の1個(併用時は同値を検査。「地形の時間」を
  !   分裂させない)。
  !
  ! 【毎ステップの処理(run_main が snow_calc の後・swflow の前に呼ぶ)】
  !   氷面の度日融解: 雪(swe)が無いセルのみ(雪が先に融ける)。気温は
  !   氷面標高 z+hi で評価(m_meteo の減率)。融解水は s%h へ直接投入
  !   (gv・wfrac 換算+e 回復 = 融雪と同型)。
  !
  ! 【dt_glacier 間隔の処理(順序が契約)】
  !   (1) s%hi のハロ交換(毎ステップ融解の帯更新を配布)
  !   (2) 雪崩再配分(f_glava): 氷面 z+hi の最急勾配が tanθc を超えるセルの
  !       swe を最急降下の8近傍へ移送(2パス。決定的・保存的)
  !   (3) 氷化(フィルン): swe×(1−exp(−dtw/tfirn)) を氷へ(密度換算)
  !   (4) s%hi のハロ交換(氷化の帯更新を配布)
  !   (5) SIA 流動(f_glflow): 氷面 s = z+hi の非線形拡散
  !         ∂H/∂t = ∇・(D∇s), D = Γ H^5 |∇s|^2 + As(ρg)^3 H^4 |∇s|^2
  !       (Glen n=3、Weertman m=3 固定)。保存形2ループ(calc_creep と同型)、
  !       陽解法+適応サブサイクリング(D_max の allreduce_max から分割数を
  !       決定 = 全ランク同一の collective 安全)。エッジ流量はドナー律速
  !       (1エッジ ≤ ドナー氷体積の 1/4)で hi>=0 を構造的に保証。
  !       サブサイクルごとに hi のハロ交換。
  !   (6) 氷河侵食(f_glero。f_glslide 必須): 滑動速度 us = As τb^3
  !       (τb = ρi g H |∇s|、セル中心の中央差分勾配)のべき乗則
  !       edot = Kg・us^l(us は m/yr で評価)で s%z を削る。
  !       s%sd は同じ Δz で共動減少(sd=0 まで基岩固定、以後は基岩侵食 =
  !       fluvial の z/sd 共動 §19.2 と同じ構造)。侵食物は系外へ排出と
  !       みなす(氷内・融氷水による搬出の抽象化。体積は台帳 vero に記録し
  !       dispose で報告。glacier_plan.md §6)。z 更新後に e 回復+
  !       s%z(・s%sd)のハロ交換。
  !
  ! 【水との関係(抽象化)】
  !   地表水 s%h は氷の下・上を区別せず地盤 z の上を流れる(氷は水理に
  !   不可視。氷上・氷底流路の抽象化)。融解水・氷上の降雨は h に入り
  !   通常の swflow で流下する。海セルに氷は置かない(流入もしない =
  !   カービングは対象外)。
  !
  ! MPI 規約(developer.md §11):
  !   - s%hi / s%z / s%sd / s%swe の更新は自帯 js..je のみ(owner-compute)。
  !     エッジ・2パス計算の帯界面は冗長計算(ハロ入力からビット厳密に配布)
  !   - enabled / tick / サブサイクル数の判定は全ランク同一(collective 安全)
  !   - 総量診断は par_sum_rows(m_state の himean)。dispose の台帳報告は
  !     ランク局所(par_warn)
  ! ==============================================================
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use m_meteo, only : t_meteo, meteo_temp_set, meteo_temp_cell
  use m_swflow_enc, only : have_width, wfrac
  use list_glacier, only : t_list_glacier, list_glacier_read
  use m_fileio, only : fileio_write_rle, fileio_read_rle, fileio_read_matrix
  use m_sysdep_util, only : sysdep_mkdir
  use m_parallel, only : par_info, par_warn, par_stop, par_abort, dcp, is_root, &
                         par_halo_cell, par_allreduce_max, par_gather_to, &
                         par_scatter_cell
  use m_util, only : itoa, rtoa, str2sec
  implicit none
  private

  public :: t_glacier
  public :: m_glacier_init
  public :: m_glacier_calc
  public :: m_glacier_dispose

  real, parameter :: yr_s = 365.25 * 86400.0    ! 1 年 (s)(m_geomorph と同値)
  real, parameter :: mm2m = 1.0e-3
  real, parameter :: secday = 86400.0
  real, parameter :: rho_w = 1000.0             ! 水の密度 (kg/m3)
  real, parameter :: swe_eps = 1.0e-9           ! 「雪なし」判定の SWE 閾値 (m)

  ! 8近傍の規約(m_geomorph / m_swflow_enc と同一。k=1..4 が所有エッジ成分、
  ! k=5..8 は近傍の所有。9-k が反対向き)
  integer, parameter :: din(1:8) = [ -1,  0,  1, -1,  1, -1,  0,  1]
  integer, parameter :: djn(1:8) = [ -1, -1, -1,  0,  0,  1,  1,  1]
  integer, parameter :: die(1:8) = [ -1,  0,  0, -1,  0, -1,  0,  0]
  integer, parameter :: dje(1:8) = [ -1, -1, -1,  0,  0,  0,  0,  0]
  integer, parameter :: ke(1:8) = [ 1, 2, 3, 4, 4, 3, 2, 1]
  real, parameter :: sign_e(1:8) = [1., 1., 1., 1., -1., -1., -1., -1.]

  type t_glacier
    ! init に早期 return 経路があるため全成分デフォルト初期化必須(§13)
    logical :: enabled = .false.
    integer :: idt = 1               ! 更新間隔(ステップ数)
    real :: morfac = 1.0             ! 氷河=地形時間の加速係数
    real :: ri = 0.0                 ! ρw/ρi(水当量 → 氷厚)
    real :: ir = 0.0                 ! ρi/ρw(氷厚 → 水当量)
    real :: tfirn = 0.0              ! 氷化の e-folding 時間 (s)
    real :: ddfi = 0.0               ! 氷面度日係数 (m/℃/s に換算済み)
    real :: tmelt = 0.0              ! 氷面融解閾値 (℃)
    integer :: f_flow = 0            ! SIA 流動 (0:なし, 1:有効)
    real :: gamd = 0.0               ! 変形の係数 Γ = 2A(ρi g)^3/5 (1/(m^3 s))
    real :: cfl = 0.4                ! サブサイクルの安全係数
    integer :: nsubmax = 10000       ! サブサイクル数の上限
    integer :: f_slide = 0           ! Weertman 滑動 (0:なし, 1:有効)
    real :: gams = 0.0               ! 滑動の係数 As(ρi g)^3 (1/(m^2 s))
    real :: as_si = 0.0              ! 滑動係数 As (m s^-1 Pa^-3)
    real :: rhogi = 0.0              ! ρi g (Pa/m)
    integer :: f_ero = 0             ! 氷河侵食 (0:なし, 1:有効)
    real :: kg = 0.0                 ! 侵食係数 Kg(us は m/yr で評価)
    real :: lexp = 1.0               ! 侵食則のべき指数 l
    integer :: f_ava = 0             ! 雪崩再配分 (0:なし, 1:有効)
    real :: avatanc = 0.6            ! 雪崩の限界勾配 tanθc
    logical :: initialized = .false.
  end type

  ! モジュール私有の作業領域(単一インスタンス前提。developer.md §12)
  type t_glwork
    real :: cw(1:4) = 0.0            ! エッジ伝導度重み(= 通過幅/距離。4近傍のみ)
    real :: dist(1:4) = 0.0          ! エッジ法線方向のセル中心間距離 (m)
    real :: dist8(1:8) = 0.0         ! 8近傍セル中心までの距離 (m)(雪崩の勾配用)
    real :: area = 0.0               ! セル面積 dx*dy (m2)
    real :: ainv = 0.0               ! 1 / (dx*dy)
    real :: rdx2 = 0.0               ! 1/dx^2 + 1/dy^2(安定条件用)
    real, allocatable :: q(:,:,:)    ! エッジ氷フラックス4成分 (m3/s)
    real, allocatable :: edz(:,:)    ! 侵食深の作業領域 (m)(1:nx, js:je)。
                                     !   2パス構造用: パス1が時刻 n の z+hi
                                     !   (近傍参照)から侵食深を計算し、
                                     !   パス2が適用する。1パスのその場更新は
                                     !   勾配の近傍読みと競合する(§28.2 の
                                     !   OpenMP データ競合と同型。実検出)
    real, allocatable :: am(:,:)     ! 雪崩の移送量 (m 水当量)(1:nx, jsh:jeh)
    integer, allocatable :: ad(:,:)  ! 雪崩の移送方向 k=1..8(0=なし)(同上)
    real :: vero = 0.0               ! 侵食で系外へ排出した体積 (m3)(ランク局所累計)
    integer :: nsubtot = 0           ! サブサイクル総数(ランク共通。dispose で報告)
    integer :: ntick = 0             ! 更新回数
  end type
  type(t_glwork) :: glw

contains


!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! 氷河モジュールを初期化する
!   fn_glacier 未指定 or f_glacier=0 なら何もしない(enabled = .false.)。
!   気温(m_meteo)と積雪(m_snow = 涵養の供給源)が必須のため、
!   m_meteo_init・m_snow_init の後に呼ぶこと(積雪の有効は
!   allocated(s%swe) で判定する — プロセス層どうしの use を避ける)
!----------------------------------------------------------------------
subroutine m_glacier_init(gl, p, g, s, mt)
  type(t_glacier), intent(out) :: gl
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_meteo), intent(in) :: mt
  type(t_list_glacier) :: list
  real :: dtg
  character(len=256) :: msg

  if (len_trim(p%fn_glacier) == 0) return

  call list_glacier_read(p, list)
  if (list%f_glacier == 0) return    ! fn を書いたまま一時無効化する経路

  ! STG は非対応(z の時間発展に追従しない。geomorph と同じ制約)
  if (p%f_gridsystem /= 0) then
    call par_stop("list_glacier: glacier processes (fn_glacier) are not supported " &
                  // "with STG (f_gridsystem=1)")
  end if
  if (.not. mt%enabled) then
    call par_stop("list_glacier: glacier processes require air temperature " &
                  // "(specify fn_meteo)")
  end if
  if (.not. allocated(s%swe)) then
    call par_stop("list_glacier: glacier processes require the snow module " &
                  // "as the accumulation source (specify fn_snow with f_snow=1)")
  end if

  ! --- 更新間隔 ---
  dtg = str2sec(trim(list%dt_glacier_c), "list_glacier: dt_glacier_c is not a valid duration")
  if (dtg <= 0.0) call par_stop("list_glacier: dt_glacier_c must be a positive duration")
  gl%idt = max(nint(dtg / p%dt), 1)

  ! --- 加速係数(geomorph 併用時は同値必須 =「地形の時間」を分裂させない) ---
  if (list%gl_morfac <= 0.0) call par_stop("list_glacier: gl_morfac must be > 0")
  gl%morfac = list%gl_morfac
  if (s%geo_morfac > 0.0 .and. gl%morfac /= s%geo_morfac) then
    call par_stop("list_glacier: gl_morfac must equal morfac of list_geomorph " &
                  // "(a single shared geomorphic time; gl_morfac = " &
                  // rtoa(gl%morfac) // ", geomorph morfac = " // rtoa(s%geo_morfac) // ")")
  end if

  ! --- 質量収支(G1) ---
  if (list%gl_dens <= 0.0 .or. list%gl_dens > rho_w) then
    call par_stop("list_glacier: gl_dens must be in (0, 1000] kg/m3")
  end if
  gl%ri = rho_w / list%gl_dens
  gl%ir = list%gl_dens / rho_w
  s%gl_ir = gl%ir              ! m_state の himean(水当量換算)用
  if (list%gl_tfirn_yr <= 0.0) call par_stop("list_glacier: gl_tfirn_yr must be > 0")
  gl%tfirn = list%gl_tfirn_yr * yr_s
  if (list%gl_ddfi <= -9998.0) call par_stop("list_glacier: gl_ddfi is required (mm/deg-C/day)")
  if (list%gl_ddfi <= 0.0) call par_stop("list_glacier: gl_ddfi must be > 0")
  gl%ddfi = list%gl_ddfi * mm2m / secday          ! mm/℃/day -> m/℃/s(水当量)
  gl%tmelt = list%gl_tmelt

  ! --- SIA 流動(G2) ---
  gl%f_flow = list%f_glflow
  gl%rhogi = list%gl_dens * p%gg
  if (gl%f_flow > 0) then
    if (list%gl_afl <= 0.0) call par_stop("list_glacier: gl_afl must be > 0 (Pa^-3 yr^-1)")
    ! Γ = 2A(ρi g)^n/(n+2)、n=3 固定(A は Pa^-3 yr^-1 -> Pa^-3 s^-1)
    gl%gamd = 2.0 * (list%gl_afl / yr_s) * gl%rhogi**3 / 5.0
    if (list%gl_cfl <= 0.0 .or. list%gl_cfl > 1.0) then
      call par_stop("list_glacier: gl_cfl must be in (0, 1]")
    end if
    gl%cfl = list%gl_cfl
    if (list%gl_nsubmax < 1) call par_stop("list_glacier: gl_nsubmax must be >= 1")
    gl%nsubmax = list%gl_nsubmax
  end if

  ! --- Weertman 滑動(G3) ---
  gl%f_slide = list%f_glslide
  if (gl%f_slide > 0) then
    if (gl%f_flow <= 0) call par_stop("list_glacier: f_glslide requires f_glflow=1")
    if (list%gl_as <= -9998.0) call par_stop("list_glacier: f_glslide=1 requires gl_as " &
                                             // "(m yr^-1 Pa^-3)")
    if (list%gl_as <= 0.0) call par_stop("list_glacier: gl_as must be > 0")
    gl%as_si = list%gl_as / yr_s                  ! m yr^-1 Pa^-3 -> m s^-1 Pa^-3
    gl%gams = gl%as_si * gl%rhogi**3
  end if

  ! --- 氷河侵食(G3。滑動速度依存則のため f_glslide 必須) ---
  gl%f_ero = list%f_glero
  if (gl%f_ero > 0) then
    if (gl%f_slide <= 0) call par_stop("list_glacier: f_glero requires f_glslide=1 " &
                                       // "(erosion is driven by basal sliding)")
    if (list%gl_kg <= -9998.0) call par_stop("list_glacier: f_glero=1 requires gl_kg")
    if (list%gl_kg <= 0.0) call par_stop("list_glacier: gl_kg must be > 0")
    if (list%gl_lexp <= 0.0) call par_stop("list_glacier: gl_lexp must be > 0")
    gl%kg = list%gl_kg
    gl%lexp = list%gl_lexp
  end if

  ! --- 雪崩再配分(G4) ---
  gl%f_ava = list%f_glava
  if (gl%f_ava > 0) then
    if (list%gl_ava_tanc <= 0.0) call par_stop("list_glacier: gl_ava_tanc must be > 0")
    gl%avatanc = list%gl_ava_tanc
  end if

  ! --- 状態の確保と初期値(海セル・無効セルには置かない) ---
  allocate(s%hi(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  if (len_trim(list%fn_glacier_hi0) > 0) then
    call setup_hi0_map(p, g, s, list%fn_glacier_hi0)
  end if

  ! --- 作業領域 ---
  glw%area = g%dx * g%dy
  glw%ainv = 1.0 / glw%area
  glw%rdx2 = 1.0 / g%dx**2 + 1.0 / g%dy**2
  glw%cw(1) = 0.0             ! 斜め(未使用。calc_creep と同じ4近傍)
  glw%cw(2) = g%dx / g%dy
  glw%cw(3) = 0.0
  glw%cw(4) = g%dy / g%dx
  glw%dist(1) = 0.0
  glw%dist(2) = g%dy
  glw%dist(3) = 0.0
  glw%dist(4) = g%dx
  glw%dist8(1) = sqrt(g%dx**2 + g%dy**2)
  glw%dist8(2) = g%dy
  glw%dist8(3) = glw%dist8(1)
  glw%dist8(4) = g%dx
  glw%dist8(5) = g%dx
  glw%dist8(6) = glw%dist8(1)
  glw%dist8(7) = g%dy
  glw%dist8(8) = glw%dist8(1)
  if (gl%f_flow > 0) then
    ! j 範囲はセル j を挟むエッジが j-1 と j にあるため下限 jsh-1
    ! (m_geomorph の wrk%q と同形)。確保時 0: マスク起因で書かれない
    ! エッジは恒久 0(無フラックス)
    allocate(glw%q(1:4, 0:g%nx, dcp%jsh-1:dcp%jeh), source = 0.0)
  end if
  if (gl%f_ero > 0) then
    allocate(glw%edz(1:g%nx, dcp%js:dcp%je), source = 0.0)
  end if
  if (gl%f_ava > 0) then
    allocate(glw%am(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
    allocate(glw%ad(1:g%nx, dcp%jsh:dcp%jeh), source = 0)
  end if

  ! --- リスタート(復元値が hi0 に勝つ) ---
  if (p%f_state_restore > 0) call restore_state(p, g, s)

  gl%enabled = .true.
  gl%initialized = .true.
  write(msg,'(a,i0,a,es10.3,a)') "glacier enabled (dt_glacier = ", gl%idt, &
        " steps, morfac = ", gl%morfac, ")"
  call par_info(trim(msg))
end subroutine


!----------------------------------------------------------------------
! 氷河の毎ステップ更新(snow_calc の後・swflow の前)
!   毎ステップ: 氷面の度日融解(水文時間で h へ、氷は ×morfac)
!   dt_glacier 間隔: 雪崩 → 氷化 → SIA 流動 → 侵食(ヘッダの契約順)
!   注意: 冒頭の return とハロ交換の判定はすべて全ランクで同一
!----------------------------------------------------------------------
subroutine m_glacier_calc(gl, p, g, s, mt, it)
  type(t_glacier), intent(in) :: gl
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_meteo), intent(inout) :: mt
  integer, intent(in) :: it
  real :: dtw, dts
  integer :: i, j

  if (.not. gl%enabled) return

  ! 評価時刻の気温をセット(collective。snow_calc が同時刻で set 済みでも
  ! 冪等 — f_snow=0 の一時無効化時に自前で確保するため常に呼ぶ)
  call meteo_temp_set(mt, p, g, s%t)

  ! --- 毎ステップ: 氷面の度日融解 ---
  call calc_melt(gl, p, g, s, mt)

  ! --- dt_glacier 間隔の更新 ---
  if (mod(it, gl%idt) /= 0) return
  glw%ntick = glw%ntick + 1
  dtw = p%dt * gl%idt              ! 水文時間の窓
  dts = dtw * gl%morfac            ! 氷河=地形時間の窓

  ! (1) 毎ステップ融解の帯更新を配布(以降の近傍参照の正本)
  call par_halo_cell(s%hi)

  ! (2) 雪崩再配分(swe のハロ交換を内包)
  if (gl%f_ava > 0) call tick_avalanche(gl, g, s)

  ! (3) 氷化(フィルン): swe -> hi
  call tick_firn(gl, g, s, dtw)

  ! (4) 氷化の帯更新を配布(流動のエッジ冗長計算の入力)
  call par_halo_cell(s%hi)

  ! (5) SIA 流動(サブサイクルごとに hi のハロ交換を内包)
  if (gl%f_flow > 0) call tick_flow(gl, g, s, dts)

  ! (6) 氷河侵食(z・sd の更新と e 回復・ハロ交換)
  if (gl%f_ero > 0) then
    call tick_erosion(gl, g, s, dts)
    !$omp parallel do schedule(static) private(i, j)
    do j = dcp%js, dcp%je
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0) cycle
        s%e(i,j) = s%z(i,j) + s%h(i,j)
      end do
    end do
    !$omp end parallel do
    call par_halo_cell(s%z)
    if (allocated(s%sd)) call par_halo_cell(s%sd)
  end if

end subroutine


!----------------------------------------------------------------------
! 氷河モジュールを破棄する(save は dispose で行う。契約5)
!   台帳(侵食排出体積・サブサイクル数)を報告する
!----------------------------------------------------------------------
subroutine m_glacier_dispose(gl, p, g, s)
  type(t_glacier), intent(inout) :: gl
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  if (.not. gl%enabled) return
  if (p%f_state_save > 0) call save_state(p, g, s)
  if (gl%f_ero > 0) then
    ! ランク局所の診断(帯内の侵食排出体積)
    call par_warn("glacier: eroded volume exported from the system = " &
                  // rtoa(glw%vero) // " m3 (this rank)")
  end if
  if (gl%f_flow > 0 .and. glw%ntick > 0) then
    call par_warn("glacier: SIA subcycles total = " // itoa(glw%nsubtot) &
                  // " over " // itoa(glw%ntick) // " updates")
  end if
  if (allocated(glw%q)) deallocate(glw%q)
  if (allocated(glw%edz)) deallocate(glw%edz)
  if (allocated(glw%am)) deallocate(glw%am)
  if (allocated(glw%ad)) deallocate(glw%ad)
  glw%vero = 0.0
  glw%nsubtot = 0
  glw%ntick = 0
  gl%enabled = .false.
  gl%initialized = .false.
end subroutine


!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

!----------------------------------------------------------------------
! 氷面の度日融解(毎ステップ。水文時間)
!   雪に覆われたセル(swe > 雪なし閾値)は融けない(雪が先)。
!   気温は氷面標高 z+hi で評価(減率込み = 氷厚の負フィードバック)。
!   水の生成は dt×1、氷の減少は ×morfac(台帳分離。ヘッダ参照)。
!   融解水は融雪と同型で h へ(gv・wfrac 換算+e 回復)
!----------------------------------------------------------------------
subroutine calc_melt(gl, p, g, s, mt)
  type(t_glacier), intent(in) :: gl
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_meteo), intent(in) :: mt
  integer :: i, j
  real :: tc, wm, wf

  !$omp parallel do schedule(static) private(i, j, tc, wm, wf)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      if (s%hi(i,j) <= 0.0) cycle
      if (s%swe(i,j) > swe_eps) cycle
      tc = meteo_temp_cell(mt, i, j, s%z(i,j) + s%hi(i,j))
      if (tc <= gl%tmelt) cycle
      ! 融解ポテンシャル(m 水当量)と氷の在庫(地形時間側)の最小
      wm = min(gl%ddfi * (tc - gl%tmelt) * p%dt, s%hi(i,j) * gl%ir / gl%morfac)
      s%hi(i,j) = s%hi(i,j) - wm * gl%morfac * gl%ri
      wf = 1.0
      if (have_width) wf = wfrac(i,j)
      s%h(i,j) = s%h(i,j) + wm / g%gv(i,j) / wf
      s%e(i,j) = s%z(i,j) + s%h(i,j)
    end do
  end do
  !$omp end parallel do
end subroutine


!----------------------------------------------------------------------
! 氷化(フィルン): swe の一定割合を氷へ変換する
!   割合は水文時間の指数緩和 1−exp(−dtw/tfirn)(季節雪はほぼ変換されず、
!   越年した多年性 SWE が e-folding tfirn で氷化する)。氷の増加は
!   ×morfac(地形時間の涵養。ヘッダの台帳分離)
!----------------------------------------------------------------------
subroutine tick_firn(gl, g, s, dtw)
  type(t_glacier), intent(in) :: gl
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: dtw
  integer :: i, j
  real :: fr, w

  fr = 1.0 - exp(-dtw / gl%tfirn)
  !$omp parallel do schedule(static) private(i, j, w)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      if (s%swe(i,j) <= 0.0) cycle
      w = s%swe(i,j) * fr
      s%swe(i,j) = s%swe(i,j) - w
      s%hi(i,j) = s%hi(i,j) + w * gl%morfac * gl%ri
    end do
  end do
  !$omp end parallel do
end subroutine


!----------------------------------------------------------------------
! SIA 氷体流動(1回の呼び出しで地形時間 dts ぶん。適応サブサイクリング)
!   各サブサイクル:
!     パスA: 拡散係数の最大値(自帯エッジ)-> allreduce_max -> dt_sub 決定
!            (全ランク同一 = ループ回数・collective が同期)
!     パスB: エッジ流量(時刻 n の hi・z から。書き手はハロ行 je+1 まで =
!            帯界面の冗長計算。calc_creep と同型)。ドナー律速で hi>=0 保証
!     パスC: 発散を取り hi を更新(自帯 js..je のみ)-> hi のハロ交換
!   エッジ流量の反対称集計により氷体積は機械精度で厳密に保存される
!----------------------------------------------------------------------
subroutine tick_flow(gl, g, s, dts)
  type(t_glacier), intent(in) :: gl
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: dts
  integer :: i, j, k, in, jn, jt, nsub
  real :: trem, dtsub, dmax, dlim
  real :: sc, sn_, ds, gs2, he, dd, gq, qcap, dv
  real :: w1(1)
  logical :: okc, last

  trem = dts
  nsub = 0
  jt = min(dcp%je + 1, dcp%jeh)

  do while (trem > 0.0)
    nsub = nsub + 1
    if (nsub > gl%nsubmax) then
      call par_stop("glacier: SIA subcycle count exceeded gl_nsubmax = " &
                    // itoa(gl%nsubmax) // " (reduce dt_glacier_c/gl_morfac or " &
                    // "increase gl_nsubmax)")
    end if

    ! --- パスA: 拡散係数の最大値と dt_sub の決定 ---
    dmax = 0.0
    !$omp parallel do schedule(static) private(i, j, k, in, jn, okc, sc, sn_, ds, gs2, he, dd) &
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
          he = 0.5 * (s%hi(i,j) + s%hi(in,jn))
          if (he <= 0.0) cycle
          sc = s%z(i,j) + s%hi(i,j)
          sn_ = s%z(in,jn) + s%hi(in,jn)
          ds = sc - sn_
          gs2 = (ds / glw%dist(k))**2
          dd = gl%gamd * he**5 * gs2 + gl%gams * he**4 * gs2
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
      dlim = gl%cfl * 0.5 / (dmax * glw%rdx2)
      if (dlim < trem) then
        dtsub = dlim
        last = .false.
      end if
    else
      ! 動く氷がない: このサイクルで消化して終了(フラックスは全て 0)
      dtsub = trem
    end if

    ! --- パスB: エッジ流量(ドナー律速つき) ---
    !   帯界面のエッジ成分 k=1..3(行 je)はハロ行 je+1 の書き手が担う
    !   (冗長計算。全域端では行が存在せず対象外)
    !$omp parallel do schedule(static) private(i, j, k, in, jn, okc, sc, sn_, ds, gs2, he, &
    !$omp                                      dd, gq, qcap)
    do j = dcp%js, jt
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0) cycle
        okc = (g%sw(i,j) <= 0)
        do k = 1, 4
          in = i + din(k)
          jn = j + djn(k)
          ! 状態は毎回変わるため、条件を満たさない場合も必ず 0 を代入する
          gq = 0.0
          if (glw%cw(k) > 0.0 .and. okc .and. g%x(in,jn) > 0) then
            if (g%sw(in,jn) <= 0) then
              he = 0.5 * (s%hi(i,j) + s%hi(in,jn))
              if (he > 0.0) then
                sc = s%z(i,j) + s%hi(i,j)
                sn_ = s%z(in,jn) + s%hi(in,jn)
                ds = sc - sn_
                gs2 = (ds / glw%dist(k))**2
                dd = gl%gamd * he**5 * gs2 + gl%gams * he**4 * gs2
                ! エッジ流量(書き手 c から k 近傍 n に向かい正)(m3/s)
                gq = dd * ds * glw%cw(k)
                ! ドナー律速: 1エッジの持ち出し ≤ ドナー氷体積の 1/4
                ! (4エッジ合計 ≤ 全量 → hi >= 0 が構造的に成立)
                if (ds > 0.0) then
                  qcap = 0.25 * s%hi(i,j) * glw%area / dtsub
                  gq = min(gq, qcap)
                else
                  qcap = 0.25 * s%hi(in,jn) * glw%area / dtsub
                  gq = max(gq, -qcap)
                end if
              end if
            end if
          end if
          glw%q(k, i+die(k), j+dje(k)) = gq
        end do
      end do
    end do
    !$omp end parallel do

    ! --- パスC: 発散を取り hi を更新 ---
    !$omp parallel do schedule(static) private(i, j, k, dv)
    do j = dcp%js, dcp%je
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0) cycle
        if (g%sw(i,j) > 0) cycle
        dv = 0.0
        do k = 1, 8
          dv = dv + sign_e(k) * glw%q(ke(k), i+die(k), j+dje(k))
        end do
        s%hi(i,j) = s%hi(i,j) - dv * dtsub * glw%ainv
      end do
    end do
    !$omp end parallel do

    call par_halo_cell(s%hi)

    if (last) exit
    trem = trem - dtsub
  end do

  glw%nsubtot = glw%nsubtot + nsub
end subroutine


!----------------------------------------------------------------------
! 氷河侵食(滑動速度べき乗則。1回の呼び出しで地形時間 dts ぶん)
!   τb = ρi g H |∇s|(セル中心の中央差分勾配。無効近傍は片側/勾配 0 に退化)
!   us = As τb^3、edot = Kg・(us [m/yr])^l / yr_s [m/s]
!   2パス構造(§28.2 の実バグと同型の競合対策): パス1が時刻 n の z+hi
!   (近傍参照)から侵食深 edz を計算し、パス2が z・sd へ適用する。
!   1パスのその場更新は勾配の近傍読みとスレッド・帯界面で競合する
!   (np=2 の場不一致で実検出)。
!   z を削り sd を共動減少(sd=0 まで基岩 z−sd 固定、以後は基岩侵食)。
!   侵食物は系外排出(台帳 vero に記録)。z の書き手は自帯のみ、
!   読み(hi, z)はハロ最新(呼び出し順の契約)
!----------------------------------------------------------------------
subroutine tick_erosion(gl, g, s, dts)
  type(t_glacier), intent(in) :: gl
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: dts
  integer :: i, j
  real :: gx, gy, cnt, se, sw2, tb, us, dz
  real :: vsum

  ! --- パス1: 侵食深の評価(時刻 n の z+hi から。書き込みは edz のみ) ---
  !$omp parallel do schedule(static) private(i, j, gx, gy, cnt, se, sw2, tb, us, dz)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      glw%edz(i,j) = 0.0
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      if (s%hi(i,j) <= 0.0) cycle
      ! x 方向の氷面勾配(無効近傍は片側差分に退化。両側無効なら 0)。
      ! 近傍の g%sw は g%x の内側で検査する(g%x のみ 0 縁取り確保。
      ! .and. の短絡評価は言語仕様で保証されない — -fcheck 実検出)
      cnt = 0.0
      se = s%z(i,j) + s%hi(i,j)
      sw2 = se
      if (g%x(i+1,j) > 0) then
        if (g%sw(i+1,j) <= 0) then
          se = s%z(i+1,j) + s%hi(i+1,j)
          cnt = cnt + 1.0
        end if
      end if
      if (g%x(i-1,j) > 0) then
        if (g%sw(i-1,j) <= 0) then
          sw2 = s%z(i-1,j) + s%hi(i-1,j)
          cnt = cnt + 1.0
        end if
      end if
      gx = 0.0
      if (cnt > 0.0) gx = (se - sw2) / (cnt * g%dx)
      ! y 方向(行順は北→南: 符号は勾配の大きさにのみ使うため不問)
      cnt = 0.0
      se = s%z(i,j) + s%hi(i,j)
      sw2 = se
      if (g%x(i,j+1) > 0) then
        if (g%sw(i,j+1) <= 0) then
          se = s%z(i,j+1) + s%hi(i,j+1)
          cnt = cnt + 1.0
        end if
      end if
      if (g%x(i,j-1) > 0) then
        if (g%sw(i,j-1) <= 0) then
          sw2 = s%z(i,j-1) + s%hi(i,j-1)
          cnt = cnt + 1.0
        end if
      end if
      gy = 0.0
      if (cnt > 0.0) gy = (se - sw2) / (cnt * g%dy)

      tb = gl%rhogi * s%hi(i,j) * sqrt(gx**2 + gy**2)    ! 底面せん断応力 (Pa)
      us = gl%as_si * tb**3                              ! 滑動速度 (m/s)
      if (us <= 0.0) cycle
      dz = gl%kg * (us * yr_s)**gl%lexp / yr_s * dts     ! 侵食深 (m)
      glw%edz(i,j) = dz
    end do
  end do
  !$omp end parallel do

  ! --- パス2: 適用(自帯のみ。edz はパス1で全対象セルに 0 込みで設定済み) ---
  vsum = 0.0
  !$omp parallel do schedule(static) private(i, j, dz) reduction(+: vsum)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      dz = glw%edz(i,j)
      if (dz <= 0.0) cycle
      s%z(i,j) = s%z(i,j) - dz
      if (allocated(s%sd)) s%sd(i,j) = max(s%sd(i,j) - dz, 0.0)
      vsum = vsum + dz
    end do
  end do
  !$omp end parallel do
  glw%vero = glw%vero + vsum * glw%area
end subroutine


!----------------------------------------------------------------------
! 雪の重力再配分(雪崩。f_glava)
!   氷面 z+hi の8近傍最急降下勾配 tanθ が限界 tanθc を超えるセルの swe を
!   その近傍へ移送する。移送率 = min(1, (tanθ−tanθc)/tanθc)(超過に比例。
!   限界の2倍勾配で全量)。2パス構造:
!     パス1: 時刻 n の場から (量, 方向) を決定(ハロ行 js−1/je+1 も冗長
!            計算 = 帯界面の受け取りをランク数不変にする。§28.2 と同じ理由)
!     パス2: 自帯のみ、送り出しと8近傍からの受け取りを集計
!   単一受け手+送り量 ≤ swe なので保存的(領域外・海へは送らない)
!----------------------------------------------------------------------
subroutine tick_avalanche(gl, g, s)
  type(t_glacier), intent(in) :: gl
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: i, j, k, in, jn, jt0, jt1, kbest
  real :: sc, drop, tanmax, tanth, fr, w

  ! 決定はハロ入力に依存するため swe を最新化(hi は呼び出し側で交換済み)
  call par_halo_cell(s%swe)

  ! --- パス1: 送り量と方向の決定(ハロ行 ±1 を含む冗長計算) ---
  !   ±1 行の近傍参照は確保範囲(帯±2)に収まる(全域端の行は使用セルが
  !   ない=窓が空、という領域境界の規約で保護される。calc_creep と同じ)
  jt0 = max(dcp%js - 1, dcp%jsh)
  jt1 = min(dcp%je + 1, dcp%jeh)
  !$omp parallel do schedule(static) private(i, j, k, in, jn, sc, drop, tanmax, tanth, kbest, fr)
  do j = jt0, jt1
    do i = g%wx(1,j), g%wx(2,j)
      glw%am(i,j) = 0.0
      glw%ad(i,j) = 0
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      if (s%swe(i,j) <= 0.0) cycle
      sc = s%z(i,j) + s%hi(i,j)
      tanmax = 0.0
      kbest = 0
      do k = 1, 8
        in = i + din(k)
        jn = j + djn(k)
        if (g%x(in,jn) <= 0) cycle
        if (g%sw(in,jn) > 0) cycle
        drop = sc - (s%z(in,jn) + s%hi(in,jn))
        if (drop <= 0.0) cycle
        tanth = drop / glw%dist8(k)
        if (tanth > tanmax) then
          tanmax = tanth
          kbest = k
        end if
      end do
      if (kbest == 0) cycle
      if (tanmax <= gl%avatanc) cycle
      fr = min(1.0, (tanmax - gl%avatanc) / gl%avatanc)
      glw%am(i,j) = s%swe(i,j) * fr
      glw%ad(i,j) = kbest
    end do
  end do
  !$omp end parallel do

  ! --- パス2: 送り出しと受け取りの集計(自帯のみ) ---
  !   受け取り = 近傍 n の方向が自セルを指す(反対向き 9−k)場合
  !$omp parallel do schedule(static) private(i, j, k, in, jn, w)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      w = s%swe(i,j) - glw%am(i,j)
      do k = 1, 8
        in = i + din(k)
        jn = j + djn(k)
        if (jn < jt0 .or. jn > jt1) cycle       ! パス1の計算範囲外(全域端)
        if (g%x(in,jn) <= 0) cycle
        if (glw%ad(in,jn) == 9 - k) w = w + glw%am(in,jn)
      end do
      s%swe(i,j) = w
    end do
  end do
  !$omp end parallel do
end subroutine


!----------------------------------------------------------------------
! 初期氷厚分布の読み込み(m 氷厚。rank0 読み+帯 scatter。使用セルの負値は
! エラー。海セルはゼロ化。m_snow の setup_swe0_map と同型)
!----------------------------------------------------------------------
subroutine setup_hi0_map(p, g, s, fn)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  character(len=*), intent(in) :: fn
  real, allocatable :: wk(:,:)
  real :: dum(1,1)
  character(:), allocatable :: fname
  character(len=1024) :: msg
  logical :: found
  integer :: i, j

  fname = trim(p%dir_data)//"/"//trim(fn)
  inquire(file=fname, exist=found)
  if (.not. found) call par_stop("list_glacier: fn_glacier_hi0 not found: "//fname)
  if (is_root) then
    allocate(wk(1:g%nx, 1:g%ny))
    call par_info(" reading "//fname)
    call fileio_read_matrix(fname, g%nx, g%ny, wk, p%f_input_mode)
    do j = 1, g%ny
      do i = 1, g%nx
        if (g%x(i,j) <= 0) cycle
        if (wk(i,j) < 0.0) then
          write(msg,'(a,2i7,es12.4)') "list_glacier: fn_glacier_hi0 has a negative value " &
                                      //"at cell", i, j, wk(i,j)
          call par_abort(trim(msg))
        end if
      end do
    end do
    call par_scatter_cell(wk, s%hi)
  else
    call par_scatter_cell(dum, s%hi)
  end if
  do j = dcp%jsh, dcp%jeh
    do i = 1, g%nx
      if (g%sw(i,j) > 0) s%hi(i,j) = 0.0
    end do
  end do
end subroutine


!----------------------------------------------------------------------
! 内部状態の保存・復元(モデル私有ファイル glacier.dat。契約5。§7)
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
  call par_gather_to(wk, s%hi)
  if (is_root) then
    call sysdep_mkdir(p%dir_save)
    open(newunit=un, file=trim(p%dir_save)//'/glacier.dat', form='unformatted', &
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

  fname = trim(p%dir_save)//'/glacier.dat'
  inquire(file=fname, exist=found)
  if (.not. found) then
    call par_stop("glacier: state file not found (was fn_glacier enabled when saving): " &
                  //fname)
  end if
  if (is_root) then
    allocate(wk(1:g%nx, 1:g%ny), source = 0.0)
    open(newunit=un, file=fname, form='unformatted', status='old')
    call fileio_read_rle(un, wk)
    close(un)
    call par_scatter_cell(wk, s%hi)
  else
    call par_scatter_cell(dum, s%hi)
  end if
end subroutine

end module
