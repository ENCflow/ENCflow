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
  !   溶岩面 s = z + hl、面勾配 S = |∇s|、降伏最小厚 h0 = τ_y/(ρgS)。
  !   単位幅フラックスの大きさ(he = エッジ平均厚、hf = he−h0):
  !     |q| = (ρgS/6η)・hf²・(2he+h0)   (hf > 0。τ_y=0 で |q| = ρgS he³/3η)
  !   拡散形 q = D・Δs/dist、D = (ρg/6η) hf² (2he+h0) として glacier の
  !   SIA と同じ保存形2ループ+ドナー律速+適応サブサイクリングに乗せる。
  !   係数 D(降伏最小厚 h0)はエッジの勾配の大きさ S = √(Sn² + St²) で
  !   評価し、エッジの向きは線形項 Δs/dist(法線勾配 Sn)の射影にだけ使う
  !   (真の Mahaffy 化。developer.md §51.4)。接線勾配 St はエッジ両側の
  !   溶岩のあるセルの、エッジに沿う方向の溶岩面の差分の平均(edge_tslope)。
  !   法線勾配だけで判定すると斜め方向の勾配が 1/√2 に見えて降伏応力が
  !   実質 √2 倍になり、ドームや溶岩原が格子軸の方向に伸びたひし形になる
  !   (2026-11-03 修正)
  !
  ! 【毎 dt_lavaflow tick の処理(順序が契約)】
  !   (1) 噴火口ソース: 噴出率 Q(t)(時系列補間)をセル集合へ均等分配
  !       (柱状 m。owner-compute。運動量なし)
  !   (2) s%hl のハロ交換(注入の帯更新を配布)
  !   (3) Bingham 拡散流動: サブサイクルごとに D_max の allreduce_max から
  !       dt_sub を決定(全ランク同一 = collective 安全)。エッジ流量は
  !       ドナー律速(1エッジ ≤ ドナー溶岩体積の 1/4)で hl>=0 を構造的に
  !       保証。サブサイクルごとに hl のハロ交換
  !   (4) 固化(lv_wsol > 0 のとき): エッジ深さ平均流速 D・S/he(S は
  !       勾配の大きさ)の最大が lv_vsol 未満の「停止セル」の hl を
  !       レート lv_wsol で s%z へ転換(数えるのは溶岩が動けるエッジだけ =
  !       送り手〔溶岩面の高い側〕に溶岩のあるエッジ。§51.5)
  !       (sd は増やさない = 侵食されない岩盤)。固化したセルの土層は埋める:
  !       sd(と土層の内数 hb・sf・ht、定着度 fx)を 0 にし、地下水計算が
  !       有効なら容量を失った地下貯留を地表水へ移す(§51.6)。e 回復と
  !       s%z(・sd ほか)のハロ交換まで済ませる。速度閾値+レートは f_dbstop=1(db_vstop/db_wstop)
  !       と同じ閉じ方 — Bingham の停止は漸近的(q→0 だが有限時間で 0 に
  !       ならない)ため、厳密なフラックス 0 判定では固化が発火しない。
  !       再流動なし(固化は不可逆)。数値的閉包であり温度による固化は
  !       段階2(lava_plan.md §8)。判定はパス1が時刻 n の場から行い
  !       パス2が適用する(近傍参照とその場更新の競合対策。glacier の
  !       tick_erosion と同型)
  !
  ! 【温度(段階2。f_lvtemp=1 のときだけ。lava_plan.md §8・developer.md §51.7)】
  !   状態 s%tl = 深さ平均温度 (°C。溶岩のないセルは 0)。移流で保存する量は
  !   熱量 hl·Tl(× ρc_p × セル面積 = J。0 °C 基準の顕熱):
  !     ∂(hl Tl)/∂t + ∇·(q T*) = Σ (Q/A) T_v − (F_rad + F_conv)/(ρ c_p)
  !   T* = エッジの送り手(風上)の温度(f_lvtemp_scheme = 3 では送り手・受け手・
  !   さらに風上の 3 点の MUSCL の面値。§94)、T_v = 噴出温度。冷却は有効放射率 ε の
  !   放射 F_rad = ε σ (Tl_K⁴ − Ta_K⁴) と対流 F_conv = h_c (Tl − Ta)(Ta は
  !   fn_meteo のセルの気温か lv_tair)。表面の殻の断熱は ε を下げて表す。
  !   粘度と降伏応力は η(T) = η_r exp(−β_η (T − T_r))、τ_y(T) = τ_r exp(−β_τ (T − T_r))
  !   (lv_visc・lv_tauy を基準温度 lv_tref の値と読む)を、エッジの温度
  !   T_e = (hl_c Tl_c + hl_n Tl_n)/(hl_c + hl_n) で評価する(β = 0 なら係数は
  !   等温と同じ値 = ビット一致)。tick の順序: (1) 注入(熱量で混合)→ (2) hl・tl の
  !   ハロ交換 → (3) 流動(熱のエッジ流量 q·T* を同じ保存形で。サブサイクルごとに
  !   hl・tl のハロ交換)→ (3') 冷却(セルごとの後退 Euler。Ta を下回らない)→
  !   (4) 固化(Tl ≤ lv_tsol のセルの溶岩を柱ごと z へ。速度閾値の閉じ方
  !   lv_wsol・lv_vsol は使わない。土層の埋没は同じ)。
  !   入れないもの: 結晶化の潜熱(有効比熱 lv_cp に含めて与えてよい)、地面への
  !   熱伝導、粘性発熱、表面の殻と内部を分けた鉛直構造。リスタートは私有ファイル
  !   lavaflow_temp.dat(lavaflow.dat の形式は等温と同じに保つ)
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
  use m_state, only : t_state, gw_to_h, sect_cell, sect_add_vh
  use m_boundary, only : interp_series, read_cell_file2, read_val_file2
  use m_meteo, only : t_meteo, meteo_temp_set, meteo_temp_cell
  use list_lavaflow, only : t_list_lavaflow, list_lavaflow_read, &
                            lvmax, lvcmax, lvvmax, lv_cell, lv_val
  use m_restart, only : restart_write_cell, restart_read_cell
  use m_sysdep_util, only : sysdep_mkdir
  use m_parallel, only : par_info, par_stop, dcp, is_root, &
                         par_halo_cell, par_allreduce_max, par_allreduce_sumr, &
                         par_gather_to, par_scatter_cell
  use m_util, only : itoa, rtoa, str2sec, param_default
  use m_flow8, only : flow8_weights, flow8_open, flow8_diag_gs2
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

  ! 温度(段階2)の物理定数と数値の上限
  real, parameter :: sigma_sb = 5.670374419e-8  ! Stefan-Boltzmann 定数 (W/m2/K4。CODATA 2018)
  real, parameter :: tk0 = 273.15               ! 0 °C の絶対温度 (K)
  real, parameter :: xexp = 50.0                ! レオロジーの温度因子 exp(x) の |x| の上限(異常な
                                                !   入力での桁あふれ防止。通常の溶岩の範囲では効かない)
  integer, parameter :: nnewton = 50            ! 冷却の後退 Euler のニュートン反復の上限

  type t_vent                        ! 噴火口1個
    integer :: ncell = 0             ! セル数
    integer, allocatable :: cell(:,:)  ! セル座標 (1:2, 1:ncell)
    integer :: nval = 0              ! 噴出率時系列のデータ数
    real, allocatable :: val(:,:)    ! 時系列 (1:2, 1:nval) (s, m3/s)
    real :: temp = 0.0               ! 噴出温度 (°C。温度モードのみ)
  end type

  type t_lvwork
    real :: cw(1:4) = 0.0            ! エッジ伝導度重み(= 通過幅/距離。lv_diagratio = 0 では 4 近傍のみ)
    real :: cwd(1:4) = 0.0           ! 8 近傍の振り替えの伝導度の増分(§96)。軸 k = 2・4: 塞がれた斜め
                                     !   1 本分(ld·面長/距離。nb 倍して足す)、斜め k = 1・3: 斜め先 1 つ分
                                     !   ((自然幅 − 斜めの通過幅)/2/距離。塞がり率の和の 1/2 倍して足す)
    real :: dist(1:4) = 0.0          ! エッジ法線方向のセル中心間距離 (m)
    real :: diag = 0.0               ! 流動の斜めの配分 d(lv_diagratio。0 = 4 近傍。§96)
    real :: area = 0.0               ! セル面積 dx*dy (m2)
    real :: ainv = 0.0               ! 1 / (dx*dy)
    real :: rdx2 = 0.0               ! 1/dx^2 + 1/dy^2(安定条件用)
    real, allocatable :: q(:,:,:)    ! エッジ溶岩フラックス4成分 (m3/s)
    real, allocatable :: ge(:,:,:)   ! エッジの伝導度 G = D·cw·(振り替え) (m2/s)。8 近傍(diag > 0)のみ
                                     !   確保。q と同形(パスA が書き、dt の決定とパスB が読む。§96)
    real, allocatable :: sdz(:,:)    ! 固化深の作業領域 (m)(1:nx, js:je)。
                                     !   2パス構造用(判定は時刻 n の場、適用は
                                     !   パス2。lv_wsol>0 か温度モードのみ確保)
    real, allocatable :: qt(:,:,:)   ! エッジ熱フラックス4成分 (m3/s × °C。q × 送り手の温度。
                                     !   温度モードのみ確保。q と同形)
    real, allocatable :: tw(:,:)     ! 新しい温度の作業領域 (°C)(ish:ieh, js:je)。パスC で
                                     !   近傍の旧温度を読みながら書くため。温度モードのみ確保
    integer :: nvent = 0             ! 噴火口数
    type(t_vent), allocatable :: vent(:)
    real :: vin = 0.0                ! 噴出の累計(自帯セル分の柱状 m 和)
    real :: vsol = 0.0               ! 固化の累計(同上)
    real :: vbur = 0.0               ! 埋めた土層の累計(同上。§51.6)
    real :: vgwr = 0.0               ! 埋めた土層から地表へ移した地下水の累計(同上)
    real :: ein = 0.0                ! 噴出した熱量の累計(自帯セルの柱状 m × °C の和。
                                     !   × ρc_p × セル面積 = J。0 °C 基準。温度モード)
    real :: erad = 0.0               ! 放射で失った熱量の累計(同上)
    real :: ecnv = 0.0               ! 対流で失った熱量の累計(同上)
    real :: esol = 0.0               ! 固化した溶岩が持っていた熱量の累計(同上)
    real :: e0 = 0.0                 ! 計算開始時(リスタートの復元後)に溶けていた溶岩の熱量(同上)
    integer :: nsubtot = 0           ! サブサイクル総数(ランク共通。dispose で報告)
    integer :: ntick = 0             ! 更新回数
  end type

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
    ! 温度(段階2。f_lvtemp=1。lava_plan.md §8)
    logical :: thermal = .false.     ! 温度を計算する
    logical :: tmuscl = .false.      ! 熱の移流の面の温度を MUSCL で再構成する(f_lvtemp_scheme = 3。§94)
    logical :: usemet = .false.      ! 気温を meteo から読む(.false. = 定数 tair)
    real :: tref = 0.0               ! レオロジーの基準温度 T_r (°C)
    real :: bvisc = 0.0              ! 粘度の温度感度 β_η (1/K)
    real :: btau = 0.0               ! 降伏応力の温度感度 β_τ (1/K)
    real :: tsol = 0.0               ! 固化温度 T_sol (°C)
    real :: emis = 0.0               ! 有効放射率 ε
    real :: hconv = 0.0              ! 対流の熱伝達係数 h_c (W/m2/K)
    real :: rhocp = 0.0              ! ρ c_p (J/m3/K)
    real :: tair = 0.0               ! 気温 (°C。usemet = .false. のとき)
    logical :: initialized = .false.
    type(t_lvwork) :: lvw            ! 作業台帳(モジュール変数から成分へ。nesting_plan.md §3.2 A 群)
  end type


  ! モジュール私有の作業領域(単一インスタンス前提。developer.md §12)

contains


!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! 溶岩流モジュールを初期化する
!   fn_lavaflow 未指定 or f_lavaflow=0 なら何もしない(enabled = .false.)。
!   等温モードは他モジュールに依存しない。温度モード(f_lvtemp=1)は
!   fn_meteo があればセルの気温を使う(m_meteo_init の後に呼ぶこと)
!----------------------------------------------------------------------
subroutine m_lavaflow_init(lv, p, g, s, mt)
  type(t_lavaflow), intent(out) :: lv
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_meteo), intent(in) :: mt
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
  ! 粘度の既定(未指定 = 番兵 −9999 なら採用し表示。developer.md §66)。
  ! lv_tauy の 0 は「Newton 流体」、lv_wsol の 0 は「固化なし」の明示なので既定なし
  list%lv_visc = param_default("lavaflow", "lv_visc", list%lv_visc, 1.0e4, " Pa.s", unset=-9999.0)
  if (list%lv_visc <= 0.0) call par_stop("list_lavaflow: lv_visc must be > 0 (Pa s)")
  if (list%lv_tauy < 0.0) call par_stop("list_lavaflow: lv_tauy must be >= 0 (Pa)")
  lv%rhog = list%lv_rho * p%gg
  lv%coef = lv%rhog / (6.0 * list%lv_visc)
  lv%tauy = list%lv_tauy

  ! --- 固化(速度閾値+レート。f_dbstop=1 と同じ閉じ方) ---
  if (list%lv_wsol < 0.0) call par_stop("list_lavaflow: lv_wsol must be >= 0 (m/s)")
  lv%wsol = list%lv_wsol
  if (lv%wsol > 0.0) then
    ! 停止判定の速度閾値の既定(lv_wsol > 0 のときだけ読む。§66)
    list%lv_vsol = param_default("lavaflow", "lv_vsol", list%lv_vsol, 5.0e-4, " m/s", unset=-9999.0)
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
  if (list%lv_diagratio < 0.0 .or. list%lv_diagratio > 1.0) then
    call par_stop("list_lavaflow: lv_diagratio must be in [0, 1]")
  end if
  lv%lvw%diag = list%lv_diagratio

  ! --- 噴火口(セル集合+噴出率。番号は 1 から連続 = pump と同じ規約) ---
  do iv = 1, lvmax
    active(iv) = (lv_cell(1,1,iv) > -9999) &
                 .or. (lv_val(1,1,iv) > -9999.0) &
                 .or. (list%lv_q0(iv) > -9999.0) &
                 .or. (len_trim(list%fn_lv_cell(iv)) > 0) &
                 .or. (len_trim(list%fn_lv_val(iv)) > 0)
  end do
  lv%lvw%nvent = count(active)
  if (lv%lvw%nvent <= 0) call par_stop("list_lavaflow: no vents defined " &
                                    // "(give lv_cell and lv_q0/lv_val)")
  if (.not. all(active(1:lv%lvw%nvent))) then
    call par_stop("list_lavaflow: vent numbers must be consecutive from 1")
  end if

  allocate(lv%lvw%vent(1:lv%lvw%nvent))
  do iv = 1, lv%lvw%nvent

    !--- セル集合(ファイル指定が優先) ---
    if (len_trim(list%fn_lv_cell(iv)) > 0) then
      call read_cell_file2(trim(p%dir_data)//"/"//trim(list%fn_lv_cell(iv)), &
                           lv%lvw%vent(iv)%ncell, lv%lvw%vent(iv)%cell)
    else
      n = 0
      do k = 1, lvcmax
        if (lv_cell(1,k,iv) <= -9999) exit    ! 番兵で終端
        n = n + 1
      end do
      allocate(lv%lvw%vent(iv)%cell(1:2,1:max(n,1)))
      lv%lvw%vent(iv)%cell(1:2,1:n) = lv_cell(1:2,1:n,iv)
      lv%lvw%vent(iv)%ncell = n
    end if

    !--- 噴出率(ファイル > インライン時系列 > 一定値。時刻は分→秒換算) ---
    if (len_trim(list%fn_lv_val(iv)) > 0) then
      call read_val_file2(trim(p%dir_data)//"/"//trim(list%fn_lv_val(iv)), &
                          lv%lvw%vent(iv)%nval, lv%lvw%vent(iv)%val)
    else if (lv_val(1,1,iv) > -9999.0) then
      n = 0
      do k = 1, lvvmax
        if (lv_val(1,k,iv) <= -9999.0) exit   ! 番兵で終端
        n = n + 1
      end do
      allocate(lv%lvw%vent(iv)%val(1:2,1:max(n,1)))
      lv%lvw%vent(iv)%val(1,1:n) = lv_val(1,1:n,iv) * 60   ! 分を秒に換算
      lv%lvw%vent(iv)%val(2,1:n) = lv_val(2,1:n,iv)
      lv%lvw%vent(iv)%nval = n
    else if (list%lv_q0(iv) > -9999.0) then
      allocate(lv%lvw%vent(iv)%val(1:2,1:1))               ! 一定値は1点時系列に退化
      lv%lvw%vent(iv)%val(1,1) = 0.0
      lv%lvw%vent(iv)%val(2,1) = list%lv_q0(iv)
      lv%lvw%vent(iv)%nval = 1
    end if

    !--- 検証 ---
    if (lv%lvw%vent(iv)%ncell <= 0) then
      call par_stop("list_lavaflow: vent "//itoa(iv)//" has no cells")
    end if
    if (lv%lvw%vent(iv)%nval <= 0) then
      call par_stop("list_lavaflow: vent "//itoa(iv)//" has no effusion rate " &
                    // "(give lv_q0, lv_val or fn_lv_val)")
    end if
    if (any(lv%lvw%vent(iv)%val(2,1:lv%lvw%vent(iv)%nval) < 0.0)) then
      call par_stop("list_lavaflow: vent "//itoa(iv)//" has a negative effusion rate")
    end if
    do k = 1, lv%lvw%vent(iv)%ncell
      i = lv%lvw%vent(iv)%cell(1,k)
      j = lv%lvw%vent(iv)%cell(2,k)
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

  ! --- 温度(段階2。f_lvtemp=1。lava_plan.md §8・developer.md §51.7) ---
  if (list%f_lvtemp /= 0 .and. list%f_lvtemp /= 1) then
    call par_stop("list_lavaflow: f_lvtemp must be 0 or 1")
  end if
  lv%thermal = (list%f_lvtemp == 1)
  if (lv%thermal) call init_thermal(lv, list, mt)
  if (list%f_lvtemp_scheme /= 1 .and. list%f_lvtemp_scheme /= 3) then
    call par_stop("list_lavaflow: f_lvtemp_scheme must be 1(first-order upwind) or 3(MUSCL)")
  end if
  ! 温度モードでないときは読まない(既定 3。§94)
  lv%tmuscl = lv%thermal .and. (list%f_lvtemp_scheme == 3)

  ! --- 状態の確保 ---
  allocate(s%hl(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  if (lv%thermal) allocate(s%tl(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)

  ! --- 作業領域(lv_diagratio = 0 は calc_creep / m_glacier と同じ4近傍) ---
  lv%lvw%area = g%dx * g%dy
  lv%lvw%ainv = 1.0 / lv%lvw%area
  lv%lvw%rdx2 = 1.0 / g%dx**2 + 1.0 / g%dy**2
  if (lv%lvw%diag > 0.0) then
    ! 8 近傍の 9 点の伝導度と振り替えの増分(m_flow8。§96)
    call flow8_weights(g, lv%lvw%diag, lv%lvw%cw, lv%lvw%cwd, lv%lvw%dist)
  else
    lv%lvw%cw(1) = 0.0             ! 斜め(未使用)
    lv%lvw%cw(2) = g%dx / g%dy
    lv%lvw%cw(3) = 0.0
    lv%lvw%cw(4) = g%dy / g%dx
    lv%lvw%dist(1) = 0.0
    lv%lvw%dist(2) = g%dy
    lv%lvw%dist(3) = 0.0
    lv%lvw%dist(4) = g%dx
  end if
  ! j 範囲はセル j を挟むエッジが j-1 と j にあるため下限 jsh-1
  ! (m_glacier の glw%q と同形)。確保時 0: マスク起因で書かれない
  ! エッジは恒久 0(無フラックス)
  allocate(lv%lvw%q(1:4, dcp%ish-1:dcp%ieh, dcp%jsh-1:dcp%jeh), source = 0.0)
  if (lv%lvw%diag > 0.0) allocate(lv%lvw%ge(1:4, dcp%ish-1:dcp%ieh, dcp%jsh-1:dcp%jeh), source = 0.0)
  if (lv%thermal) then
    allocate(lv%lvw%qt(1:4, dcp%ish-1:dcp%ieh, dcp%jsh-1:dcp%jeh), source = 0.0)
    allocate(lv%lvw%tw(dcp%ish:dcp%ieh, dcp%js:dcp%je), source = 0.0)
  end if
  if (lv%wsol > 0.0 .or. lv%thermal) then
    allocate(lv%lvw%sdz(dcp%ish:dcp%ieh, dcp%js:dcp%je), source = 0.0)
  end if

  ! --- リスタート ---
  if (p%f_state_restore > 0) call restore_state(lv, p, g, s)
  ! 熱の台帳の初期値(復元した溶岩の熱量。新規の計算では 0)
  if (lv%thermal) then
    do j = dcp%js, dcp%je
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0) cycle
        if (s%hl(i,j) <= 0.0) cycle
        lv%lvw%e0 = lv%lvw%e0 + s%hl(i,j) * s%tl(i,j)
      end do
    end do
  end if

  lv%enabled = .true.
  lv%initialized = .true.
  write(msg,'(a,i0,a,i0,a)') "lavaflow enabled (dt_lavaflow = ", lv%idt, &
        " steps, ", lv%lvw%nvent, " vent(s)"
  if (lv%thermal) msg = trim(msg) // ", temperature f_lvtemp=1"
  if (lv%tmuscl) msg = trim(msg) // ", heat advection MUSCL (f_lvtemp_scheme=3)"
  call par_info(trim(msg) // ")")
  if (lv%lvw%diag > 0.0) then
    write(msg,'(a,f6.4,a)') "lavaflow: flow on the 8-neighbour 9-point stencil (lv_diagratio = ", &
                            lv%lvw%diag, ") with dynamic reassignment of blocked diagonal shares"
    call par_info(trim(msg))
  end if
end subroutine


!----------------------------------------------------------------------
! 溶岩流の更新(dt_lavaflow 間隔。geomorph・driftwood の後 = z 更新
! プロセスの末尾)。順序はヘッダの契約: 噴火口ソース → ハロ交換 →
! Bingham 拡散流動 →(温度モードは冷却)→ 固化(→ z 更新・e 回復・
! z ハロ交換)。
! 注意: 冒頭の return とハロ交換の判定はすべて全ランクで同一
!----------------------------------------------------------------------
subroutine m_lavaflow_calc(lv, p, g, s, mt, it)
  type(t_lavaflow), intent(inout) :: lv
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_meteo), intent(inout) :: mt
  integer, intent(in) :: it
  real :: dtw

  if (.not. lv%enabled) return
  if (mod(it, lv%idt) /= 0) return
  lv%lvw%ntick = lv%lvw%ntick + 1
  dtw = p%dt * lv%idt

  ! (1) 噴火口ソース(owner-compute。温度モードは熱量で混合)
  call tick_vent(lv, s, dtw)

  ! (2) 注入の帯更新を配布(流動のエッジ冗長計算の入力)
  call par_halo_cell(s%hl)
  if (lv%thermal) call par_halo_cell(s%tl)

  ! (3) Bingham 拡散流動(サブサイクルごとに hl〔温度モードは tl も〕のハロ交換を内包)
  call tick_flow(lv, g, s, dtw)

  ! (3') 冷却(温度モード。セル局所の後退 Euler。気温の set は collective)
  if (lv%thermal) call tick_cool(lv, p, g, s, mt, dtw)

  ! (4) 固化(等温は不動セル、温度モードは冷えたセルの hl → z。e 回復と z のハロ交換まで)
  if (lv%wsol > 0.0 .or. lv%thermal) call tick_solidify(lv, g, s, dtw)

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
  real :: vsum(1:5), hsum, esum(1:6), fac
  integer :: i, j
  character(len=256) :: msg

  if (.not. lv%enabled) return
  if (p%f_state_save > 0) call save_state(lv, p, g, s)

  ! 台帳の総括(診断のみ。柱状 m 和 × セル面積 = 体積 m3)
  hsum = 0.0
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      hsum = hsum + s%hl(i,j)
    end do
  end do
  vsum(1) = lv%lvw%vin * lv%lvw%area
  vsum(2) = lv%lvw%vsol * lv%lvw%area
  vsum(3) = hsum * lv%lvw%area
  vsum(4) = lv%lvw%vbur * lv%lvw%area
  vsum(5) = lv%lvw%vgwr * lv%lvw%area
  call par_allreduce_sumr(vsum)
  if (is_root) then
    write(msg,'(a,es12.4,a,es12.4,a,es12.4,a)') &
      " lavaflow: erupted ", vsum(1), " m3, solidified ", vsum(2), &
      " m3, molten ", vsum(3), " m3"
    call par_info(trim(msg))
    ! 土層があるとき(地形変化・地下水の計算で s%sd を確保)だけ埋没の台帳を出す
    if (allocated(s%sd)) then
      write(msg,'(a,es12.4,a,es12.4,a)') &
        " lavaflow: soil buried under solidified lava ", vsum(4), &
        " m3, groundwater moved to the surface ", vsum(5), " m3"
      call par_info(trim(msg))
    end if
  end if
  ! 熱の台帳(温度モード。柱状 m × °C の和 × ρc_p × セル面積 = J。0 °C 基準の顕熱。
  ! 開始時 + 噴出 = 放射 + 対流 + 固化 + 残存 が丸めの範囲で閉じる。開始時は
  ! リスタートで復元した溶岩の熱量(新規の計算では 0)。lava_plan.md §8.9)
  if (lv%thermal) then
    hsum = 0.0
    do j = dcp%js, dcp%je
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0) cycle
        if (s%hl(i,j) <= 0.0) cycle
        hsum = hsum + s%hl(i,j) * s%tl(i,j)
      end do
    end do
    fac = lv%rhocp * lv%lvw%area
    esum(1) = lv%lvw%ein * fac
    esum(2) = lv%lvw%erad * fac
    esum(3) = lv%lvw%ecnv * fac
    esum(4) = lv%lvw%esol * fac
    esum(5) = hsum * fac
    esum(6) = lv%lvw%e0 * fac
    call par_allreduce_sumr(esum)
    if (is_root) then
      write(msg,'(a,es12.4,a,es12.4,a,es12.4,a)') &
        " lavaflow: heat erupted ", esum(1), " J, radiated ", esum(2), &
        " J, convected ", esum(3), " J"
      call par_info(trim(msg))
      write(msg,'(a,es12.4,a,es12.4,a)') &
        " lavaflow: heat in solidified lava ", esum(4), " J, in molten lava ", &
        esum(5), " J (sensible heat above 0 deg C)"
      call par_info(trim(msg))
      if (esum(6) > 0.0) then
        write(msg,'(a,es12.4,a)') " lavaflow: heat in molten lava at the start (restart) ", &
          esum(6), " J"
        call par_info(trim(msg))
      end if
      ! 閉じ方の確認(開始時 + 噴出 − 放射 − 対流 − 固化 − 残存。丸めの範囲で 0)
      fac = (esum(6) + esum(1)) - (esum(2) + esum(3) + esum(4) + esum(5))
      write(msg,'(a,es12.4,a,es10.2,a)') &
        " lavaflow: heat balance residual ", fac, " J (", &
        fac / max(esum(6) + esum(1), tiny(1.0)), " of start + erupted)"
      call par_info(trim(msg))
    end if
  end if
  if (lv%lvw%ntick > 0) then
    call par_info(" lavaflow: subcycles total = " // itoa(lv%lvw%nsubtot) &
                  // " over " // itoa(lv%lvw%ntick) // " updates")
  end if

  if (allocated(lv%lvw%q)) deallocate(lv%lvw%q)
  if (allocated(lv%lvw%ge)) deallocate(lv%lvw%ge)
  if (allocated(lv%lvw%qt)) deallocate(lv%lvw%qt)
  if (allocated(lv%lvw%tw)) deallocate(lv%lvw%tw)
  if (allocated(lv%lvw%sdz)) deallocate(lv%lvw%sdz)
  if (allocated(lv%lvw%vent)) deallocate(lv%lvw%vent)
  lv%lvw%nvent = 0
  lv%lvw%vin = 0.0
  lv%lvw%vsol = 0.0
  lv%lvw%vbur = 0.0
  lv%lvw%vgwr = 0.0
  lv%lvw%ein = 0.0
  lv%lvw%erad = 0.0
  lv%lvw%ecnv = 0.0
  lv%lvw%esol = 0.0
  lv%lvw%e0 = 0.0
  lv%lvw%nsubtot = 0
  lv%lvw%ntick = 0
  lv%enabled = .false.
  lv%initialized = .false.
end subroutine


!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

!----------------------------------------------------------------------
! 温度モード(f_lvtemp=1)の設定の検証と導出(m_lavaflow_init から。噴火口の
! 組み立ての後に呼ぶ)。既定は置かない(lava_plan.md §8.8): 溶岩の種類で桁が
! 変わる値(噴出温度・基準温度・温度感度・固化温度)と、原典を確かめていない
! 値(放射率・対流係数・比熱)は明示指定を求める
!----------------------------------------------------------------------
subroutine init_thermal(lv, list, mt)
  type(t_lavaflow), intent(inout) :: lv
  type(t_list_lavaflow), intent(in) :: list
  type(t_meteo), intent(in) :: mt
  integer :: iv

  ! 固化は温度で判定する(速度閾値+レートの閉じ方は使わない。§8.6)
  if (lv%wsol > 0.0) then
    call par_stop("list_lavaflow: lv_wsol (velocity-threshold solidification) is not used " &
                  // "with f_lvtemp=1; lava solidifies by temperature (lv_tsol). Set lv_wsol = 0")
  end if

  call need_param(list%lv_tref, "lv_tref")
  call need_param(list%lv_bvisc, "lv_bvisc")
  call need_param(list%lv_btau, "lv_btau")
  call need_param(list%lv_tsol, "lv_tsol")
  call need_param(list%lv_emis, "lv_emis")
  call need_param(list%lv_hconv, "lv_hconv")
  call need_param(list%lv_cp, "lv_cp")
  if (list%lv_tref <= -tk0) call par_stop("list_lavaflow: lv_tref must be above absolute zero (deg C)")
  if (list%lv_tsol <= -tk0) call par_stop("list_lavaflow: lv_tsol must be above absolute zero (deg C)")
  if (list%lv_bvisc < 0.0) call par_stop("list_lavaflow: lv_bvisc must be >= 0 (1/K)")
  if (list%lv_btau < 0.0) call par_stop("list_lavaflow: lv_btau must be >= 0 (1/K)")
  if (list%lv_emis < 0.0 .or. list%lv_emis > 1.0) then
    call par_stop("list_lavaflow: lv_emis must be in [0, 1]")
  end if
  if (list%lv_hconv < 0.0) call par_stop("list_lavaflow: lv_hconv must be >= 0 (W/m2/K)")
  if (list%lv_cp <= 0.0) call par_stop("list_lavaflow: lv_cp must be > 0 (J/kg/K)")
  lv%tref = list%lv_tref
  lv%bvisc = list%lv_bvisc
  lv%btau = list%lv_btau
  lv%tsol = list%lv_tsol
  lv%emis = list%lv_emis
  lv%hconv = list%lv_hconv
  lv%rhocp = list%lv_rho * list%lv_cp

  ! 噴出温度(噴火口ごとに必須。固化温度より高いこと)
  do iv = 1, lvmax
    if (iv <= lv%lvw%nvent) then
      if (list%lv_temp0(iv) <= -9999.0) then
        call par_stop("list_lavaflow: lv_temp0("//itoa(iv)//") (eruption temperature, deg C) " &
                      // "is required with f_lvtemp=1")
      end if
      if (list%lv_temp0(iv) <= lv%tsol) then
        call par_stop("list_lavaflow: lv_temp0("//itoa(iv)//") must be above lv_tsol")
      end if
      lv%lvw%vent(iv)%temp = list%lv_temp0(iv)
    else if (list%lv_temp0(iv) > -9999.0) then
      call par_stop("list_lavaflow: lv_temp0("//itoa(iv)//") is given for an undefined vent")
    end if
  end do

  ! 気温(fn_meteo があればセルの気温。なければ定数 lv_tair)
  lv%usemet = mt%enabled
  if (lv%usemet) then
    if (list%lv_tair > -9999.0) then
      call par_stop("list_lavaflow: lv_tair is not used when fn_meteo is given " &
                    // "(the air temperature comes from meteo); remove lv_tair")
    end if
  else
    if (list%lv_tair <= -9999.0) then
      call par_stop("list_lavaflow: lv_tair (air temperature, deg C) is required with " &
                    // "f_lvtemp=1 when fn_meteo is not given")
    end if
    if (list%lv_tair <= -tk0) call par_stop("list_lavaflow: lv_tair must be above absolute zero (deg C)")
    if (list%lv_tair >= lv%tsol) then
      call par_stop("list_lavaflow: lv_tair must be below lv_tsol " &
                    // "(the lava would never cool to the solidification temperature)")
    end if
    lv%tair = list%lv_tair
  end if
end subroutine


!----------------------------------------------------------------------
! 温度モードの必須パラメータ(番兵 -9999 のままなら停止)
!----------------------------------------------------------------------
subroutine need_param(v, name)
  real, intent(in) :: v
  character(len=*), intent(in) :: name
  if (v <= -9999.0) then
    call par_stop("list_lavaflow: "//name//" is required with f_lvtemp=1 (no default; " &
                  // "see docs/users_guide/lavaflow.md and examples/List_samples/list_lavaflow.txt)")
  end if
end subroutine


!----------------------------------------------------------------------
! 噴火口ソース(1 tick ぶんの注入)
!   噴出率 Q(t) を時刻 s%t で補間し、セル集合へ均等分配(柱状 m)。
!   指向性(運動量)は持たない。owner-compute のみでハロ交換は呼び出し側。
!   温度モードは注入先の溶岩と熱量で混ぜる: Tl ← (hl Tl + dh T_v)/(hl + dh)
!----------------------------------------------------------------------
subroutine tick_vent(lv, s, dtw)
  type(t_lavaflow), intent(inout) :: lv
  type(t_state), intent(inout) :: s
  real, intent(in) :: dtw
  integer :: iv, k, i, j
  real :: q, dh, ho, tv

  do iv = 1, lv%lvw%nvent
    q = interp_series(lv%lvw%vent(iv)%val, lv%lvw%vent(iv)%nval, s%t)
    if (q <= 0.0) cycle
    ! セルあたりの注入(柱状 m。セル集合へ等分配)
    dh = q * dtw / (lv%lvw%vent(iv)%ncell * lv%lvw%area)
    do k = 1, lv%lvw%vent(iv)%ncell
      i = lv%lvw%vent(iv)%cell(1,k)
      j = lv%lvw%vent(iv)%cell(2,k)
      if (j < dcp%js .or. j > dcp%je) cycle     ! owner-compute
      if (lv%thermal) then
        tv = lv%lvw%vent(iv)%temp
        ho = s%hl(i,j)
        if (ho > 0.0) then
          s%tl(i,j) = (ho * s%tl(i,j) + dh * tv) / (ho + dh)
        else
          s%tl(i,j) = tv
        end if
        lv%lvw%ein = lv%lvw%ein + dh * tv
      end if
      s%hl(i,j) = s%hl(i,j) + dh
      lv%lvw%vin = lv%lvw%vin + dh
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
!   エッジ流量の反対称集計により溶岩体積は機械精度で厳密に保存される。
!   降伏最小厚 h0 はエッジの勾配の大きさ √(Sn² + St²) で評価する
!   (St = edge_tslope。τ_y = 0 では h0 = 0 で係数が勾配によらないため
!   求めない。§51.4)。St は東西のエッジ(パスA・B の k=4)で行 j±1 を
!   読むので、書き手の行 je+1 では je+2 まで読む(ハロ幅 2 の内側)。
!   温度モード(§8.7): 係数と降伏応力をエッジの温度で評価し(edge_rheology)、
!   パスB で熱のエッジ流量 q·T*(T* = 送り手の温度。風上)を、パスC で熱量
!   hl·Tl を同じ保存形で更新して Tl = 熱量/hl とする。ドナー律速で送り手の
!   持ち出しは自分の溶岩以下なので、新しい Tl は自セルと流れ込みの送り手の
!   温度の凸結合になる(丸めの分を含めてその範囲に収める)。f_lvtemp_scheme = 3
!   では T* を MUSCL の面値にし(tface_muscl)、範囲に流れ出しの面の反対側の
!   近傍を加える(§94)。hl・tl をサブサイクルごとにハロ交換する
!   lv_diagratio > 0 では 8 近傍の 9 点(パスA・B を flow8_coef・flow8_flux に替える。
!   斜めのエッジと塞がれた配分の動的な振り替え、dt はセルごとの伝導度の和、ドナー律速は
!   1 エッジ 1/8。パスC は共通。§96)
!----------------------------------------------------------------------
subroutine tick_flow(lv, g, s, dtw)
  type(t_lavaflow), intent(inout) :: lv
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: dtw
  integer :: i, j, k, in, jn, jt, nsub
  real :: trem, dtsub, dmax, dlim
  real :: sc, sn_, ds, ss, gt, h0, hf, he, dd, gq, qcap, dv
  real :: cf, ty, gqt, dvt, ho, hn, tlo, thi, tn, tf
  integer :: io, jo
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
    !   8 近傍(lv_diagratio > 0。§96)はエッジの伝導度 G を ge に置き、dmax にセルごとの
    !   伝導度の和 Σ_k G_k の最大を返す(dt はその正値性の条件で決める)
    if (lv%lvw%diag > 0.0) then
      call flow8_coef(lv, g, s, jt, dmax)
    else
      dmax = 0.0
      !$omp parallel do schedule(static) private(i, j, k, in, jn, okc, sc, sn_, ds, ss, gt, h0, hf, &
      !$omp                                      he, dd, cf, ty) &
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
            ss = abs(ds) / lv%lvw%dist(k)
            cf = lv%coef
            ty = lv%tauy
            if (lv%thermal) call edge_rheology(lv, s, i, j, in, jn, cf, ty)
            h0 = 0.0
            if (ty > 0.0) then
              gt = edge_tslope(g, s, i, j, in, jn)
              h0 = ty / (lv%rhog * sqrt(ss * ss + gt * gt))
            end if
            hf = he - h0
            if (hf <= 0.0) cycle
            dd = cf * hf * hf * (2.0 * he + h0)
            dmax = max(dmax, dd)
          end do
        end do
      end do
      !$omp end parallel do
      w1(1) = dmax
      call par_allreduce_max(w1)
      dmax = w1(1)
    end if

    last = .true.
    dtsub = trem
    if (dmax > 0.0) then
      if (lv%lvw%diag > 0.0) then
        dlim = lv%cfl * lv%lvw%area / dmax     ! 自セルの係数 1 − dt Σ_k G_k / A >= 0(§96)
      else
        dlim = lv%cfl * 0.5 / (dmax * lv%lvw%rdx2)
      end if
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
    !   8 近傍(§96)はパスA の伝導度 ge から(ドナー律速は 1 エッジ 1/8)
    if (lv%lvw%diag > 0.0) then
      call flow8_flux(lv, g, s, jt, dtsub)
    else
      !$omp parallel do schedule(static) private(i, j, k, in, jn, okc, sc, sn_, ds, ss, gt, h0, hf, &
      !$omp                                      he, dd, gq, qcap, cf, ty, gqt, tf)
      do j = dcp%js, jt
        do i = g%wx(1,j), g%wx(2,j)
          if (g%x(i,j) <= 0) cycle
          okc = (g%sw(i,j) <= 0)
          do k = 1, 4
            in = i + din(k)
            jn = j + djn(k)
            ! 状態は毎回変わるため、条件を満たさない場合も必ず 0 を代入する
            gq = 0.0
            if (lv%lvw%cw(k) > 0.0 .and. okc .and. g%x(in,jn) > 0) then
              if (g%sw(in,jn) <= 0) then
                he = 0.5 * (s%hl(i,j) + s%hl(in,jn))
                if (he > 0.0) then
                  sc = s%z(i,j) + s%hl(i,j)
                  sn_ = s%z(in,jn) + s%hl(in,jn)
                  ds = sc - sn_
                  if (ds /= 0.0) then
                    ss = abs(ds) / lv%lvw%dist(k)
                    cf = lv%coef
                    ty = lv%tauy
                    if (lv%thermal) call edge_rheology(lv, s, i, j, in, jn, cf, ty)
                    h0 = 0.0
                    if (ty > 0.0) then
                      gt = edge_tslope(g, s, i, j, in, jn)
                      h0 = ty / (lv%rhog * sqrt(ss * ss + gt * gt))
                    end if
                    hf = he - h0
                    if (hf > 0.0) then
                      dd = cf * hf * hf * (2.0 * he + h0)
                      ! エッジ流量(書き手 c から k 近傍 n に向かい正)(m3/s)
                      gq = dd * ds * lv%lvw%cw(k)
                      ! ドナー律速: 1エッジの持ち出し ≤ ドナー溶岩体積の 1/4
                      ! (4エッジ合計 ≤ 全量 → hl >= 0 が構造的に成立)
                      if (ds > 0.0) then
                        qcap = 0.25 * s%hl(i,j) * lv%lvw%area / dtsub
                        gq = min(gq, qcap)
                      else
                        qcap = 0.25 * s%hl(in,jn) * lv%lvw%area / dtsub
                        gq = max(gq, -qcap)
                      end if
                    end if
                  end if
                end if
              end if
            end if
            lv%lvw%q(k, i+die(k), j+dje(k)) = gq
            if (lv%thermal) then
              ! 熱のエッジ流量 = 溶岩のエッジ流量 × 面の温度。面の温度は送り手(風上)の
              ! 温度(1 次風上)か、f_lvtemp_scheme = 3 ではエッジの向きに沿った
              ! 送り手・受け手・送り手のさらに風上の 3 点の MUSCL(tface_muscl。§94)
              gqt = 0.0
              if (gq > 0.0) then
                tf = s%tl(i,j)
                if (lv%tmuscl) tf = tface_muscl(g, s, i, j, in, jn, i - din(k), j - djn(k))
                gqt = gq * tf
              else if (gq < 0.0) then
                tf = s%tl(in,jn)
                if (lv%tmuscl) tf = tface_muscl(g, s, in, jn, i, j, in + din(k), jn + djn(k))
                gqt = gq * tf
              end if
              lv%lvw%qt(k, i+die(k), j+dje(k)) = gqt
            end if
          end do
        end do
      end do
      !$omp end parallel do
    end if

    ! --- パスC: 発散を取り hl を更新 ---
    ! 温度モードは先に熱量 hl·Tl を同じ保存形で更新し、新しい温度を作業領域 tw へ
    ! 置く(近傍の旧温度を読むため。hl の更新は等温と同じループで、両モードで
    ! 同じコードを通す = β = 0・冷却なしで hl が等温とビット一致する条件)。
    ! 新しい Tl は自セル(溶岩があれば)と流れ込みの送り手の温度の範囲に収める
    ! (厳密な算術では凸結合。範囲外は丸め、または hl がほぼ 0 になったセルの
    ! 桁落ちによる)。MUSCL(tmuscl)では流れ出しの面の値が、その面の反対側の
    ! 近傍(さらに風上のセル)の温度を正の重みで含むので、溶岩のあるその近傍も
    ! 範囲に加える(凸結合になる十分条件は流れ出しの合計 ≤ 自セルの溶岩の 1/2。§94)
    if (lv%thermal) then
      !$omp parallel do schedule(static) private(i, j, k, dv, dvt, ho, hn, tlo, thi, tn, io, jo)
      do j = dcp%js, dcp%je
        do i = g%wx(1,j), g%wx(2,j)
          if (g%x(i,j) <= 0) cycle
          if (g%sw(i,j) > 0) cycle
          ho = s%hl(i,j)
          if (ho > 0.0) then
            tlo = s%tl(i,j)
            thi = s%tl(i,j)
          else
            tlo = huge(1.0)
            thi = -huge(1.0)
          end if
          dv = 0.0
          dvt = 0.0
          do k = 1, 8
            dv = dv + sign_e(k) * lv%lvw%q(ke(k), i+die(k), j+dje(k))
            dvt = dvt + sign_e(k) * lv%lvw%qt(ke(k), i+die(k), j+dje(k))
            if (sign_e(k) * lv%lvw%q(ke(k), i+die(k), j+dje(k)) < 0.0) then
              tlo = min(tlo, s%tl(i+din(k), j+djn(k)))       ! 流れ込み(送り手 = 近傍)
              thi = max(thi, s%tl(i+din(k), j+djn(k)))
            else if (lv%tmuscl .and. sign_e(k) * lv%lvw%q(ke(k), i+die(k), j+dje(k)) > 0.0) then
              io = i - din(k)                                ! 流れ出しの面の反対側の近傍
              jo = j - djn(k)
              if (g%x(io,jo) > 0) then                       ! 領域外は x = 0(sw・hl を読まない)
                if (g%sw(io,jo) <= 0) then
                  if (s%hl(io,jo) > 0.0) then
                    tlo = min(tlo, s%tl(io,jo))
                    thi = max(thi, s%tl(io,jo))
                  end if
                end if
              end if
            end if
          end do
          hn = ho - dv * dtsub * lv%lvw%ainv              ! 下の hl の更新と同じ式
          if (hn > 0.0 .and. tlo <= thi) then
            tn = (ho * s%tl(i,j) - dvt * dtsub * lv%lvw%ainv) / hn
            lv%lvw%tw(i,j) = min(max(tn, tlo), thi)
          else
            lv%lvw%tw(i,j) = 0.0                        ! 溶岩がなくなった
          end if
        end do
      end do
      !$omp end parallel do
    end if

    !$omp parallel do schedule(static) private(i, j, k, dv)
    do j = dcp%js, dcp%je
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0) cycle
        if (g%sw(i,j) > 0) cycle
        dv = 0.0
        do k = 1, 8
          dv = dv + sign_e(k) * lv%lvw%q(ke(k), i+die(k), j+dje(k))
        end do
        s%hl(i,j) = s%hl(i,j) - dv * dtsub * lv%lvw%ainv
      end do
    end do
    !$omp end parallel do

    if (lv%thermal) then
      !$omp parallel do schedule(static) private(i, j)
      do j = dcp%js, dcp%je
        do i = g%wx(1,j), g%wx(2,j)
          if (g%x(i,j) <= 0) cycle
          if (g%sw(i,j) > 0) cycle
          s%tl(i,j) = lv%lvw%tw(i,j)
        end do
      end do
      !$omp end parallel do
    end if

    call par_halo_cell(s%hl)
    if (lv%thermal) call par_halo_cell(s%tl)

    if (last) exit
    trem = trem - dtsub
  end do

  lv%lvw%nsubtot = lv%lvw%nsubtot + nsub
end subroutine


!----------------------------------------------------------------------
! 8 近傍のパスA(lv_diagratio > 0。tick_flow の部品。§96)
!   エッジの伝導度 G = D·(cw + 振り替え量·cwd) を ge に置き(書き手 js..jt。各スロットの
!   書き手は 1 つ)、自帯のセルごとの和 Σ_k G_k(8 方向。パスC の集計と同じ)の全域の
!   最大を smax に返す(allreduce。全ランク同一)。
!   D は 4 近傍と同じ Bingham の式 cf·hf²(2he + h0)、h0 = τ_y/(ρg|∇s|)。|∇s| は軸のエッジで
!   √(Sn² + St²)(St = edge_tslope)、斜めのエッジで角点の勾配(m_flow8 の flow8_diag_gs2)。
!   振り替え量(案 A。m_flow8 の flow8_open)は、水の f_opening_dynamic = 3 と同じ規則を溶岩面に
!   当てはめた塞がり率の和の 1/2(斜め先の地盤が始点の溶岩面よりどれだけ高いか。局所の平面
!   からの盛り上がりで頭打ち)。読むのは書き手と近傍のセル、その横 ±1(行 js−1..je+2・列は
!   行窓 ±1)= ハロ幅 2 の内側
!----------------------------------------------------------------------
subroutine flow8_coef(lv, g, s, jt, smax)
  type(t_lavaflow), intent(inout) :: lv
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer, intent(in) :: jt
  real, intent(out) :: smax
  integer :: i, j, k, in, jn
  real :: sc, sn_, ds, ss, gt, gs2, h0, hf, he, dd, cf, ty, gg, sb, sm
  real :: w1(1)
  logical :: okc

  !$omp parallel do schedule(static) private(i, j, k, in, jn, okc, sc, sn_, ds, ss, gt, gs2, h0, &
  !$omp                                      hf, he, dd, cf, ty, gg, sb)
  do j = dcp%js, jt
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      okc = (g%sw(i,j) <= 0)
      do k = 1, 4
        in = i + din(k)
        jn = j + djn(k)
        ! 状態は毎回変わるため、条件を満たさない場合も必ず 0 を代入する
        gg = 0.0
        if (okc .and. g%x(in,jn) > 0) then
          if (g%sw(in,jn) <= 0) then
            he = 0.5 * (s%hl(i,j) + s%hl(in,jn))
            if (he > 0.0) then
              sc = s%z(i,j) + s%hl(i,j)
              sn_ = s%z(in,jn) + s%hl(in,jn)
              ds = sc - sn_
              if (ds /= 0.0) then
                cf = lv%coef
                ty = lv%tauy
                if (lv%thermal) call edge_rheology(lv, s, i, j, in, jn, cf, ty)
                h0 = 0.0
                if (ty > 0.0) then
                  if (mod(k, 2) == 0) then
                    ss = abs(ds) / lv%lvw%dist(k)
                    gt = edge_tslope(g, s, i, j, in, jn)
                    gs2 = ss * ss + gt * gt
                  else
                    gs2 = flow8_diag_gs2(g, s%z, s%hl, k, i, j)
                  end if
                  h0 = ty / (lv%rhog * sqrt(gs2))
                end if
                hf = he - h0
                if (hf > 0.0) then
                  dd = cf * hf * hf * (2.0 * he + h0)
                  ! 振り替え(案 A。塞がり率の和の 1/2 を cwd に掛けて足す。m_flow8)
                  sb = flow8_open(g, s%z, s%hl, k, i, j)
                  gg = dd * (lv%lvw%cw(k) + sb * lv%lvw%cwd(k))
                end if
              end if
            end if
          end if
        end if
        lv%lvw%ge(k, i+die(k), j+dje(k)) = gg
      end do
    end do
  end do
  !$omp end parallel do

  ! セルごとの伝導度の和(8 方向。パスC と同じ集計)の最大
  smax = 0.0
  !$omp parallel do schedule(static) private(i, j, k, sm) reduction(max: smax)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      sm = 0.0
      do k = 1, 8
        sm = sm + lv%lvw%ge(ke(k), i+die(k), j+dje(k))
      end do
      smax = max(smax, sm)
    end do
  end do
  !$omp end parallel do
  w1(1) = smax
  call par_allreduce_max(w1)
  smax = w1(1)
end subroutine


!----------------------------------------------------------------------
! 8 近傍のパスB(lv_diagratio > 0。tick_flow の部品。§96)
!   エッジ流量 = G·(s_c − s_n)(G はパスA の ge)。ドナー律速は 1 エッジの持ち出し ≤ ドナーの
!   溶岩体積の 1/8(8 エッジの合計 ≤ 全量 → hl >= 0)。熱のエッジ流量は 4 近傍のパスB と同じ
!   (面の温度は送り手の温度か、f_lvtemp_scheme = 3 ではエッジの向きの 3 点の MUSCL)
!----------------------------------------------------------------------
subroutine flow8_flux(lv, g, s, jt, dtsub)
  type(t_lavaflow), intent(inout) :: lv
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer, intent(in) :: jt
  real, intent(in) :: dtsub
  integer :: i, j, k, in, jn
  real :: ds, gg, gq, qcap, gqt, tf

  !$omp parallel do schedule(static) private(i, j, k, in, jn, ds, gg, gq, qcap, gqt, tf)
  do j = dcp%js, jt
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      do k = 1, 4
        in = i + din(k)
        jn = j + djn(k)
        gq = 0.0
        gg = lv%lvw%ge(k, i+die(k), j+dje(k))
        if (gg > 0.0) then
          ds = (s%z(i,j) + s%hl(i,j)) - (s%z(in,jn) + s%hl(in,jn))
          ! エッジ流量(書き手 c から k 近傍 n に向かい正)(m3/s)
          gq = gg * ds
          ! ドナー律速: 1エッジの持ち出し ≤ ドナー溶岩体積の 1/8(8 エッジ)
          if (ds > 0.0) then
            qcap = 0.125 * s%hl(i,j) * lv%lvw%area / dtsub
            gq = min(gq, qcap)
          else
            qcap = 0.125 * s%hl(in,jn) * lv%lvw%area / dtsub
            gq = max(gq, -qcap)
          end if
        end if
        lv%lvw%q(k, i+die(k), j+dje(k)) = gq
        if (lv%thermal) then
          gqt = 0.0
          if (gq > 0.0) then
            tf = s%tl(i,j)
            if (lv%tmuscl) tf = tface_muscl(g, s, i, j, in, jn, i - din(k), j - djn(k))
            gqt = gq * tf
          else if (gq < 0.0) then
            tf = s%tl(in,jn)
            if (lv%tmuscl) tf = tface_muscl(g, s, in, jn, i, j, in + din(k), jn + djn(k))
            gqt = gq * tf
          end if
          lv%lvw%qt(k, i+die(k), j+dje(k)) = gqt
        end if
      end do
    end do
  end do
  !$omp end parallel do
end subroutine


!----------------------------------------------------------------------
! 冷却(温度モード。1 tick = dtw ぶん。lava_plan.md §8.7 (4))
!   セルごとに dTl/dt = −(F_rad + F_conv)/(ρ c_p hl) を後退 Euler で積分する
!   (cool_be)。陰解法なので刻みの制約はなく(薄い溶岩ほど速く冷える)、Tl は
!   Ta を下回らない。気温以下の溶岩は冷えも温まりもしない。失った熱量
!   hl (T_n − T) を、新しい温度での放射と対流の比で台帳に分ける(合計は
!   失った熱量そのもの)。気温は fn_meteo があればセルの気温
!   (meteo_temp_set は collective。全ランクが呼ぶ)、なければ定数 lv_tair。
!   自帯のみ更新する。tl のハロは次 tick 冒頭の交換が配る(固化の判定は
!   自セルの温度だけを読む)
!----------------------------------------------------------------------
subroutine tick_cool(lv, p, g, s, mt, dtw)
  type(t_lavaflow), intent(inout) :: lv
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_meteo), intent(inout) :: mt
  real, intent(in) :: dtw
  integer :: i, j
  real :: ta, t0, t1, dl, fr, fc, wr, srad, scnv

  if (lv%usemet) call meteo_temp_set(mt, p, g, s%t)

  srad = 0.0
  scnv = 0.0
  !$omp parallel do schedule(static) private(i, j, ta, t0, t1, dl, fr, fc, wr) &
  !$omp reduction(+: srad, scnv)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      if (s%hl(i,j) <= 0.0) cycle
      if (lv%usemet) then
        ta = meteo_temp_cell(mt, i, j, s%z(i,j) + s%hl(i,j))
      else
        ta = lv%tair
      end if
      t0 = s%tl(i,j)
      if (t0 <= ta) cycle
      t1 = cool_be(lv, s%hl(i,j), t0, ta, dtw)
      if (t1 >= t0) cycle                     ! 冷却なし(ε = h_c = 0)
      dl = s%hl(i,j) * (t0 - t1)              ! 失った熱量(柱状 m × °C)
      fr = lv%emis * sigma_sb * ((t1 + tk0)**4 - (ta + tk0)**4)
      fc = lv%hconv * (t1 - ta)
      if (fr + fc <= 0.0) then                ! 気温まで冷えた: 冷却前の温度の比で分ける
        fr = lv%emis * sigma_sb * ((t0 + tk0)**4 - (ta + tk0)**4)
        fc = lv%hconv * (t0 - ta)
      end if
      wr = dl * (fr / (fr + fc))
      srad = srad + wr
      scnv = scnv + (dl - wr)
      s%tl(i,j) = t1
    end do
  end do
  !$omp end parallel do
  lv%lvw%erad = lv%lvw%erad + srad
  lv%lvw%ecnv = lv%lvw%ecnv + scnv
end subroutine


!----------------------------------------------------------------------
! 冷却の後退 Euler の 1 段(tick_cool の部品。lava_plan.md §8.7 (4))
!   H(T) = h (T − T_n) + c [ε σ (T_K⁴ − Ta_K⁴) + h_c (T − Ta)] = 0、c = dtw/(ρ c_p)
!   の根を [Ta, T_n] で求める(後退 Euler の式に h を掛けた形。h → 0 でも
!   桁あふれしない)。H は T について単調増加かつ凸で H(Ta) < 0 ≤ H(T_n)
!   なので、T_n から始めたニュートン法は単調に根へ下がり、行き過ぎない
!   (Ta を下回らない)。反復は |ΔT| ≤ 4ε T_K で打ち切る(上限 nnewton)
!----------------------------------------------------------------------
pure function cool_be(lv, h, t0, ta, dtw) result(t)
  type(t_lavaflow), intent(in) :: lv
  real, intent(in) :: h, t0, ta, dtw
  real :: t
  real :: c, tak4, tk, hv, hd, dt
  integer :: it

  c = dtw / lv%rhocp
  tak4 = (ta + tk0)**4
  t = t0
  do it = 1, nnewton
    tk = t + tk0
    hv = h * (t - t0) + c * (lv%emis * sigma_sb * (tk**4 - tak4) + lv%hconv * (t - ta))
    hd = h + c * (4.0 * lv%emis * sigma_sb * tk**3 + lv%hconv)
    dt = hv / hd
    t = max(t - dt, ta)
    if (abs(dt) <= 4.0 * epsilon(t) * tk) exit
  end do
  t = min(t, t0)
end function


!----------------------------------------------------------------------
! 固化(停止セルの hl を s%z へ転換。数値的閉包 — lava_plan.md §5)
!   停止 = エッジ深さ平均流速 u = |q|/he = D・S/he の最大が lv_vsol
!   未満のセル(Bingham の停止は漸近的で厳密なフラックス 0 に達しない
!   ため速度閾値で閉じる。f_dbstop=1 の db_vstop/db_wstop と同じ構成)。
!   S は tick_flow と同じエッジの勾配の大きさ √(Sn² + St²)(流速の大きさ。
!   法線成分だけだと斜め方向の流れが 1/√2 に見えて早く止まる。§51.4)。
!   数えるのは溶岩が実際に動けるエッジだけ: 隣の溶岩面のほうが高い流れ込みの
!   エッジは、隣に溶岩がなければ数えない(送り手に溶岩がなく、パスB の
!   ドナー律速で流量は 0)。数えると、溶岩より高い乾いたセル(谷壁・先に
!   固まった溶岩の縁)に接するセルが、流れ込むはずのない上り勾配のエッジを
!   大きな流速とみなし、いつまでも固化しなかった(2026-11-03 修正。§51.5)。
!   転換量 w = min(hl, lv_wsol×dtw)。z のみ増加(sd は増やさない =
!   固化溶岩は侵食されない岩盤)。再流動なし(不可逆)。
!   土層の埋没(§51.6): 固化したセルに土層 sd があれば、それは溶岩の下に
!   埋まる。sd を 0 にし(埋まった土は岩盤 z − sd の内側へ。以後の侵食・
!   浸透の対象外)、土層の内数(動く底層 hb・細粒分 sf・崖錐 ht)と定着度 fx も
!   0 にする。地下水計算が有効なら、容量 sd × sy0 を失った地下貯留を地表水へ
!   移す(水の総量は保存。土石流の侵食 f_dbwet=2 と同じ扱い)。土層を確保して
!   いない計算(地形変化・地下水なし)では何もしない
!   2パス構造(glacier tick_erosion と同型の競合対策): パス1が時刻 n の
!   hl・z(近傍参照。ハロは tick_flow 末端の交換で最新)から固化深を
!   評価し、パス2が適用する。e 回復と s%z のハロ交換まで行う
!   (geomorph / glacier と同じ契約)。
!   温度モード(§8.6): 判定は温度だけ — 深さ平均温度 Tl ≤ lv_tsol のセルの
!   溶岩を柱ごと(w = hl)z へ移す(速度閾値の閉じ方は使わない)。固化した
!   溶岩の熱量を台帳へ移し、Tl を 0 にする。土層の埋没は同じ
!----------------------------------------------------------------------
subroutine tick_solidify(lv, g, s, dtw)
  type(t_lavaflow), intent(inout) :: lv
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: dtw
  integer :: i, j, k, in, jn
  real :: w, wcap, vsum, vmax, sc, sn_, ds, ss, gt, sm, h0, hf, he, dd, ue
  real :: bsum, gsum, cap, xg, esum
  logical :: soil

  wcap = lv%wsol * dtw

  ! --- パス1: 停止判定と固化深の評価(書き込みは sdz のみ) ---
  !$omp parallel do schedule(static) private(i, j, k, in, jn, vmax, sc, sn_, ds, ss, gt, sm, &
  !$omp                                      h0, hf, he, dd, ue)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      lv%lvw%sdz(i,j) = 0.0
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      if (s%hl(i,j) <= 0.0) cycle
      ! 温度モード: 冷えたセルの溶岩は柱ごと固まる(速度は見ない。§8.6)
      if (lv%thermal) then
        if (s%tl(i,j) <= lv%tsol) lv%lvw%sdz(i,j) = s%hl(i,j)
        cycle
      end if
      ! 4近傍エッジの深さ平均速度の最大(tick_flow パスB と同じ量)
      vmax = 0.0
      sc = s%z(i,j) + s%hl(i,j)
      do k = 1, 8
        if (lv%lvw%cw(ke(k)) <= 0.0) cycle        ! 斜めは未使用
        in = i + din(k)
        jn = j + djn(k)
        if (g%x(in,jn) <= 0) cycle
        if (g%sw(in,jn) > 0) cycle
        he = 0.5 * (s%hl(i,j) + s%hl(in,jn))
        if (he <= 0.0) cycle
        sn_ = s%z(in,jn) + s%hl(in,jn)
        ds = sc - sn_
        if (ds == 0.0) cycle
        ! 流れ込みのエッジ(隣の溶岩面のほうが高い)は、送り手である隣に溶岩が
        ! なければ数えない(流量は tick_flow パスB のドナー律速で 0。§51.5)
        if (ds < 0.0 .and. s%hl(in,jn) <= 0.0) cycle
        ss = abs(ds) / lv%lvw%dist(ke(k))
        gt = edge_tslope(g, s, i, j, in, jn)
        sm = sqrt(ss * ss + gt * gt)               ! エッジの勾配の大きさ
        h0 = 0.0
        if (lv%tauy > 0.0) h0 = lv%tauy / (lv%rhog * sm)
        hf = he - h0
        if (hf <= 0.0) cycle
        dd = lv%coef * hf * hf * (2.0 * he + h0)
        ue = dd * sm / he
        vmax = max(vmax, ue)
      end do
      if (vmax >= lv%vsol) cycle
      lv%lvw%sdz(i,j) = min(s%hl(i,j), wcap)
    end do
  end do
  !$omp end parallel do

  ! --- パス2: 適用(自帯のみ。sdz はパス1で全対象セルに 0 込みで設定済み) ---
  soil = allocated(s%sd)             ! 全ランク同一(確保は init で全ランク)
  vsum = 0.0
  bsum = 0.0
  gsum = 0.0
  esum = 0.0
  !$omp parallel do schedule(static) private(i, j, w, cap, xg) reduction(+: vsum, bsum, gsum, esum)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      w = lv%lvw%sdz(i,j)
      if (w <= 0.0) cycle
      if (lv%thermal) then
        esum = esum + w * s%tl(i,j)          ! 固化した溶岩の熱量(柱状 m × °C)
        s%tl(i,j) = 0.0                      ! 柱ごと固まった(hl = 0)
      end if
      s%hl(i,j) = s%hl(i,j) - w
      s%z(i,j) = s%z(i,j) + w
      ! 土層の埋没(§51.6。土層があるセルだけ)
      if (soil) then
        if (s%sd(i,j) > 0.0) then
          bsum = bsum + s%sd(i,j)
          s%sd(i,j) = 0.0
          if (allocated(s%hb)) s%hb(i,j) = 0.0
          if (allocated(s%sf)) s%sf(i,j) = 0.0
          if (allocated(s%ht)) s%ht(i,j) = 0.0
          if (allocated(s%fx)) s%fx(i,j) = 0.0
          ! 容量 sd × sy0 を超えた地下貯留(sd = 0 なので全量)を地表水へ。
          ! 地表は河道幅セルで河道の平面に載る(体積を保つ換算 gw_to_h。§26.1)。
          ! 集計 gsum は地下の側の水深(セルの平面)で数える
          if (s%gw_active) then
            cap = s%sd(i,j) * g%sy0
            if (s%hg(i,j) > cap) then
              xg = s%hg(i,j) - cap
              s%hg(i,j) = cap
              if (sect_cell(s, i, j)) then
                call sect_add_vh(s, i, j, xg * gw_to_h(s, i, j))   ! σ は体積で(§26.2)
              else
                s%h(i,j) = s%h(i,j) + xg * gw_to_h(s, i, j)
              end if
              gsum = gsum + xg
            end if
          end if
        end if
      end if
      s%e(i,j) = s%z(i,j) + s%h(i,j)
      vsum = vsum + w
    end do
  end do
  !$omp end parallel do
  lv%lvw%vsol = lv%lvw%vsol + vsum
  lv%lvw%vbur = lv%lvw%vbur + bsum
  lv%lvw%vgwr = lv%lvw%vgwr + gsum
  lv%lvw%esol = lv%lvw%esol + esum

  ! 固化の有無はランク・tick で異なるが、collective の実行判定は
  ! 「lv_wsol > 0 か温度モードの tick では常に交換」で全ランク同一(§5)。
  ! hl の帯更新は次 tick 冒頭の交換が配布する(この後 hl を読む者はいない)。
  ! 土層と内数は、近傍を読む次の過程(地下水の側方流・地形変化)のために交換する
  ! (確保の有無は全ランク同一)。h・hg は次ステップの頭で swflow・gwflow が交換する
  call par_halo_cell(s%z)
  if (soil) then
    call par_halo_cell(s%sd)
    if (allocated(s%hb)) call par_halo_cell(s%hb)
    if (allocated(s%sf)) call par_halo_cell(s%sf)
    if (allocated(s%ht)) call par_halo_cell(s%ht)
    if (allocated(s%fx)) call par_halo_cell(s%fx)
  end if
end subroutine


!----------------------------------------------------------------------
! エッジの温度に応じたレオロジー(温度モード。tick_flow のパスA・B の部品。
! lava_plan.md §8.5)
!   エッジの温度 T_e = (hl_c Tl_c + hl_n Tl_n)/(hl_c + hl_n)(熱量の加重平均。
!   hl ≤ 0 の側は重み 0)から、拡散の前置係数 ρg/(6η(T_e)) と降伏応力
!   τ_y(T_e) を返す:
!     η(T) = η_r exp(−β_η (T − T_r))  → cf = lv%coef × exp(β_η (T_e − T_r))
!     τ_y(T) = τ_r exp(−β_τ (T − T_r)) → ty = lv%tauy × exp(−β_τ (T_e − T_r))
!   指数の引数は ±xexp で打ち切る(異常な入力での桁あふれ防止)。β = 0 なら
!   exp(0) = 1 で等温と同じ値(ビット一致)。c と n を入れ替えても同じ値
!   (加算の交換だけ = IEEE で厳密)。呼び出し側が he > 0 を確かめていること
!----------------------------------------------------------------------
pure subroutine edge_rheology(lv, s, i, j, in, jn, cf, ty)
  type(t_lavaflow), intent(in) :: lv
  type(t_state), intent(in) :: s
  integer, intent(in) :: i, j, in, jn
  real, intent(out) :: cf, ty
  real :: wc, wn, te

  wc = max(s%hl(i,j), 0.0)
  wn = max(s%hl(in,jn), 0.0)
  te = (wc * s%tl(i,j) + wn * s%tl(in,jn)) / (wc + wn)
  cf = lv%coef * exp(min(max(lv%bvisc * (te - lv%tref), -xexp), xexp))
  ty = lv%tauy * exp(min(max(-lv%btau * (te - lv%tref), -xexp), xexp))
end subroutine


!----------------------------------------------------------------------
! 熱の移流の面の温度(f_lvtemp_scheme = 3。tick_flow のパスB の部品。§94)
!   送り手 d = (id,jd)・受け手 r = (ir,jr)・エッジの向きに沿って送り手の
!   さらに風上のセル u = (iu,ju) の 3 点から、地表のスカラーのリンクごとの
!   MUSCL(m_swflow_enc の muscl_face。§78)と同じ van Leer の面値
!     T_f = T_d + ψ(r)/2·(T_r − T_d)、r = (T_d − T_u)/(T_r − T_d)、
!     ψ = (r + |r|)/(1 + |r|)
!   を比 r を作らない形(a = T_d − T_u、δ = T_r − T_d が同符号なら
!   T_f = T_d + a·δ/(a + δ)、そうでなければ T_d)で返す。T_f は T_d と T_r の
!   間にある。受け手に溶岩がない(温度 0 は値でない)、u が領域外・確保範囲外・
!   無効・海・溶岩なしなら送り手の温度(1 次風上)のまま。u の列は送り手から
!   ±1(書き手の行窓 ±2)なので領域内なら dcp%ish..ieh に入り、行は
!   書き手の行 js..je+1 から ±2 で帯+ハロ 2 に入る(念のため確かめる)。
!   x は全域+1 周、sw は全域で確保されているので、領域の判定の後に読む
!----------------------------------------------------------------------
pure function tface_muscl(g, s, id, jd, ir, jr, iu, ju) result(tf)
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer, intent(in) :: id, jd, ir, jr, iu, ju
  real :: tf, a, d

  tf = s%tl(id,jd)
  if (s%hl(ir,jr) <= 0.0) return
  if (iu < 1 .or. iu > g%nx .or. ju < 1 .or. ju > g%ny) return
  if (ju < dcp%jsh .or. ju > dcp%jeh) return
  if (g%x(iu,ju) <= 0) return
  if (g%sw(iu,ju) > 0) return
  if (s%hl(iu,ju) <= 0.0) return
  a = tf - s%tl(iu,ju)
  d = s%tl(ir,jr) - tf
  if (a * d > 0.0) tf = tf + a * d / (a + d)
end function


!----------------------------------------------------------------------
! エッジの接線勾配 St(勾配の大きさ √(Sn² + St²) の接線成分。§51.4)
!   エッジを挟む 2 セル c = (i,j)・n = (in,jn) のうち溶岩のある(hl > 0)
!   セルについて、エッジに沿う方向の溶岩面の勾配(cell_tslope)を求めて
!   平均する(Mahaffy 1976 が角点で両成分から |∇s| を作るのと同じ考えの
!   4 近傍版)。両セルとも溶岩なしなら 0。4 近傍のエッジ専用で、東西の
!   エッジ(jn == j。法線が x)なら接線は y、南北のエッジなら x。
!   c と n を入れ替えても同じ値になる(加算の交換だけ = IEEE で厳密)。
!   エッジ反対称のフラックスと帯界面の冗長計算がビット一致する条件。
!   読むのは c・n の接線方向 ±1 のセル
!----------------------------------------------------------------------
pure function edge_tslope(g, s, i, j, in, jn) result(gt)
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer, intent(in) :: i, j, in, jn
  real :: gt
  integer :: ti, tj, nl
  real :: rd

  if (jn == j) then              ! 東西のエッジ: 接線は y
    ti = 0
    tj = 1
    rd = 1.0 / g%dy
  else                           ! 南北のエッジ: 接線は x
    ti = 1
    tj = 0
    rd = 1.0 / g%dx
  end if
  gt = 0.0
  nl = 0
  if (s%hl(i,j) > 0.0) then
    gt = gt + cell_tslope(g, s, i, j, ti, tj, rd)
    nl = nl + 1
  end if
  if (s%hl(in,jn) > 0.0) then
    gt = gt + cell_tslope(g, s, in, jn, ti, tj, rd)
    nl = nl + 1
  end if
  if (nl == 2) gt = 0.5 * gt
end function


!----------------------------------------------------------------------
! セル (i,j) の (ti,tj) 方向の溶岩面の勾配(edge_tslope の部品)
!   その方向の両隣のうち、溶岩のある有効セル(lava_cell)だけを使う:
!   両方なら中心差分、片方なら片側差分、なしなら 0。乾いたセルの地盤高は
!   溶岩面ではないので使わない(谷壁に接する溶岩で、壁の勾配が降伏と
!   停止判定に入らないように)。rd = 1/格子間隔
!----------------------------------------------------------------------
pure function cell_tslope(g, s, i, j, ti, tj, rd) result(gd)
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer, intent(in) :: i, j, ti, tj
  real, intent(in) :: rd
  real :: gd
  logical :: okp, okm

  okp = lava_cell(g, s, i + ti, j + tj)
  okm = lava_cell(g, s, i - ti, j - tj)
  if (okp .and. okm) then
    gd = 0.5 * rd * ((s%z(i+ti,j+tj) + s%hl(i+ti,j+tj)) - (s%z(i-ti,j-tj) + s%hl(i-ti,j-tj)))
  else if (okp) then
    gd = rd * ((s%z(i+ti,j+tj) + s%hl(i+ti,j+tj)) - (s%z(i,j) + s%hl(i,j)))
  else if (okm) then
    gd = rd * ((s%z(i,j) + s%hl(i,j)) - (s%z(i-ti,j-tj) + s%hl(i-ti,j-tj)))
  else
    gd = 0.0
  end if
end function


!----------------------------------------------------------------------
! 溶岩のある有効セルか(領域内・海でない・hl > 0)。x を先に見る
! (g%x は 0:nx+1 の縁付き。sw と状態は x > 0 のセルでだけ読む)
!----------------------------------------------------------------------
pure logical function lava_cell(g, s, i, j)
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer, intent(in) :: i, j

  lava_cell = .false.
  if (g%x(i,j) <= 0) return
  if (g%sw(i,j) > 0) return
  if (s%hl(i,j) <= 0.0) return
  lava_cell = .true.
end function


!----------------------------------------------------------------------
! 内部状態の保存・復元(モデル私有ファイル lavaflow.dat。契約5。§7)
!   温度モードの Tl は別の私有ファイル lavaflow_temp.dat に置く(lavaflow.dat の
!   形式は等温と同じに保ち、既存の保存と save_version を変えないため。
!   developer.md §51.7)。等温の保存では lavaflow_temp.dat を消す(古い温度を
!   後の温度モードの再開が読まないように)
!----------------------------------------------------------------------
subroutine save_state(lv, p, g, s)
  type(t_lavaflow), intent(in) :: lv
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  character(:), allocatable :: fnt
  logical :: found
  integer :: un
  if (g%initialized) continue  ! 引数未使用の警告を抑制
  if (is_root) then
    call sysdep_mkdir(p%dir_save)
    open(newunit=un, file=trim(p%dir_save)//'/lavaflow.dat', form='unformatted', &
         status='replace')
  end if
  call restart_write_cell(un, s%hl)       ! 帯を窓形に集約しながら RLE で書く(§83)
  if (is_root) close(un)

  fnt = trim(p%dir_save)//'/lavaflow_temp.dat'
  if (lv%thermal) then
    if (is_root) open(newunit=un, file=fnt, form='unformatted', status='replace')
    call restart_write_cell(un, s%tl)
    if (is_root) close(un)
  else if (is_root) then
    inquire(file=fnt, exist=found)
    if (found) then
      open(newunit=un, file=fnt, status='old')
      close(un, status='delete')
    end if
  end if
end subroutine


subroutine restore_state(lv, p, g, s)
  type(t_lavaflow), intent(in) :: lv
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  character(:), allocatable :: fname
  logical :: found
  integer :: un
  if (g%initialized) continue  ! 引数未使用の警告を抑制

  fname = trim(p%dir_save)//'/lavaflow.dat'
  inquire(file=fname, exist=found)
  if (.not. found) then
    call par_stop("lavaflow: state file not found (was fn_lavaflow enabled when saving): " &
                  //fname)
  end if
  if (is_root) open(newunit=un, file=fname, form='unformatted', status='old')
  call restart_read_cell(un, s%hl)
  if (is_root) close(un)

  if (lv%thermal) then
    fname = trim(p%dir_save)//'/lavaflow_temp.dat'
    inquire(file=fname, exist=found)
    if (.not. found) then
      call par_stop("lavaflow: temperature state file not found (was f_lvtemp=1 when saving): " &
                    //fname)
    end if
    if (is_root) open(newunit=un, file=fname, form='unformatted', status='old')
    call restart_read_cell(un, s%tl)
    if (is_root) close(un)
  end if
end subroutine

end module
