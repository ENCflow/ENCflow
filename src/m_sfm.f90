module m_sfm
  ! ============ 貯留関数法の区画流出(fn_sfm。developer.md §106) ============
  ! 木村(1961)の貯留関数法の基本形 S = K·q^P を、区画番号ラスタで指定した区画
  ! ごとのタンクとして格子に載せる。区画・雨の回収・出口・基底流の仕組みは
  ! VZ 流出(§87)と同じで、共通部は m_zonerunoff(入力群 = 区画)。
  !
  ! 【モデル】区画 g のタンク(単位面積あたりの量):
  !     dS/dt = r(t − T_L) − q,   S = K·q^P
  !   S [mm]・q [mm/h] の慣用の単位で K を与える(K の次元は mm^(1−P)·h^P)。
  !   r は区画に降った地上雨量(f_sfm_rain = 0: 区画内のセルで一致を要求、
  !   = 1: 区画内の面積平均 = 独自の近似)。区画のすべてのセルが同じ単位面積
  !   流出を持ち、セルごとのパラメータはない。区画の流出 q·A_g は出口
  !   (地表セル / 系外)へ瞬間的に移す(側方の遅れは解かない。VZ と同じ近似)。
  !   雨はすべてタンクに入り、損失はない。一次流出率 f1・飽和雨量 R_sa・2 価の
  !   貯留関数(Prasad 型・星・山岡型)は持たない(§106.1)。
  ! 【遅れ時間】(sfm_tl_h。§106.6)木村の q_l(t) = q(t + T_L)(タンクの流出が T_L 後に
  !   流域末端に現れる)を、雨を T_L 遅らせてタンクに入れる形で表す(初期状態が定常なら
  !   出口の流出の時系列は同じ)。T_L は時間刻み dt の整数倍 nlag に丸める。遅れの間の
  !   雨は区画ごとの「遅れ列」(区分一定の区間の並び = 連長圧縮。メモリは dt に依らない)
  !   に置き、移動中の水として台帳に数える。計算開始時の遅れ列は初期の流出強度 q0 の
  !   定常(移動中の水 = q0·T_L)。T_L = 0 は遅れ列を持たず、従来と同じ演算をする。
  !
  ! 【解法】(独自の選択)後退 Euler: S1 + h·q(S1) = S0 + h·r をスカラーの Newton 法
  !   (区間 [0, S0 + h·r] の二分法で保護。q は S の増加関数なので解は一意)で解く。
  !   時間誤差はステップ二分比較(粗い 1 歩と細かい 2 歩の貯留の差)で制御し、
  !   受理した歩は局所外挿 S = 2·S_fine − S_coarse(2 次精度。[0, S0 + h·r] を外れれば
  !   細かい枝)を採る。流出量は S0 + h·r − S1 で定義するので、タンクの水収支は
  !   構造的に閉じる(丸めを除く)。P は 0 < P ≤ 1(P = 1 は線形貯留で直接解く)。
  !
  ! 【蒸発散】(fn_evap と併用時。§106.7)m_evap が樹冠・地表水・ため池・地下水の順に引いた
  !   残りの要求を区画セルから s%sfe で受け取り、毎ステップ(m_evap_calc の直後)に区画ごとの
  !   面積平均の要求をその時刻のタンクの貯留から引く(遅れ列の中の雨は移動中なので引かない)。
  !   既定は供給制限のみ(貯留があるだけ引く)。sfm_elim_mm を与えた区画は、貯留 S がそれより
  !   少ないとき E·min(1, S/S_lim) に減らす(地下水の evap_hglim と同じ線形低減をステップ内で
  !   厳密に解く。§27.2)。引いた量は vevap(sfm_zone.csv)に数える。
  ! 【同期】dt_sfm(既定 0 = 毎ステップ)ごとに、区間の各ステップの雨を区分一定で
  !   与えてタンクを進め、区間の流出を区間末にまとめて出口へ渡す(VZ と同じ意味論)。
  ! 【並列】全ランクが全タンクを冗長に解く(スカラーなので計算は無視できる)。通信は
  !   同期ごとに区画の入力を揃える 1 回。出口への加算は所有ランク(共通基盤)。
  ! 【台帳】タンクの貯留 Σ S_g·A_g は s%sfstore(real64)、回収済み・未同期の雨は
  !   s%sfp。calcstat が S_grnd に算入する。保存・復元は私有ファイル sfm.dat(契約5)。
  ! 【併用】VZ(fn_vz)とは区画のセルが重ならず、出口が相手の区画セルにない限り
  !   併用できる(init で検査)。地下水・積雪・氷河・地形変化・水質・淡塩・ネスト・
  !   STG は VZ と同じく init で停止する。区画セルは河道・海・境界・ソース・
  !   構造物のセルに置けず、出口は区画セル・海セル・水位規定セルに置けない。
  ! ==========================================================================
  use, intrinsic :: iso_fortran_env, only : real64
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use m_boundary, only : t_boundary
  use list_sfm, only : t_list_sfm, list_sfm_read, sfm_nzonemax
  use m_zonerunoff, only : t_zonerunoff, zr_read_map, zr_set_groups, zr_setup_outlets, zr_setup_baseflow, &
                           zr_alloc_interval, zr_recover_rain, zr_collect_input, zr_deliver, &
                           zr_gather_carry, zr_report_outlets, zr_check_disjoint, zr_dispose
  use m_sysdep_util, only : sysdep_mkdir
  use m_util, only : param_default, itoa, es_out
  use m_parallel, only : par_info, par_stop, dcp, is_root, par_sum_rows
  implicit none
  private
  public :: t_sfm
  public :: m_sfm_init
  public :: m_sfm_calc
  public :: m_sfm_evap
  public :: m_sfm_record
  public :: m_sfm_dispose

  integer, parameter :: save_version = 2026111103 ! sfm.dat の形式の版(形式変更日 2026-11-11 の 3 回目
                                                   ! = §7 の "c"。遅れ列と蒸発散の累積を加えた)
  real(real64), parameter :: mmh = 3.6e6_real64    ! mm/h ↔ m/s の換算(1 m/s = 3.6e6 mm/h)
  real(real64), parameter :: s_abs = 1.0e-9_real64 ! 時間誤差の尺度の下限 (m)

  !-------------------------------------------
  ! 区画のタンク(単位面積あたりの量。SI: S [m]、q [m/s])
  !-------------------------------------------
  type t_sfmtank
    real(real64) :: k = 0.0_real64             ! 貯留係数 K(入力の単位: S [mm] = K·q[mm/h]^P)
    real(real64) :: p = 0.0_real64             ! 貯留指数 P
    real(real64) :: m = 1.0_real64             ! 1/P
    real(real64) :: c = 0.0_real64             ! q = c·S^m の係数(SI)
    real(real64) :: q0mmh = 0.0_real64         ! 初期の流出強度 (mm/h)
    real(real64) :: s = 0.0_real64             ! 貯留 (m)
    real(real64) :: hnext = 0.0_real64         ! 次の試行刻み (s)
    integer :: nacc = 0, nrej = 0              ! 受理・棄却した内部刻みの数(累積)
    ! 診断(累積 m3。全ランク同値)
    real(real64) :: vin = 0.0_real64           ! 雨の入力 A_g·Σ r·dt
    real(real64) :: vdrain = 0.0_real64        ! 流出 A_g·Σ q·dt
    real(real64) :: vstore0 = 0.0_real64       ! 計算開始時の貯留 (m3)
    real(real64) :: vstore = 0.0_real64        ! 現在の貯留 A_g·S (m3)
    real(real64) :: dvlast = 0.0_real64        ! 直近の同期区間の流出 (m3)
    ! 遅れ時間(§106.6)
    real(real64) :: tlh = 0.0_real64           ! 遅れ時間の入力値 (h)
    real(real64) :: tlah = 0.0_real64          ! 採用した遅れ時間 nlag·dt (h)
    integer :: nlag = 0                        ! 遅れのステップ数(T_L を dt の倍数に丸めた値。0 = 遅れなし)
    integer :: nq = 0                          ! 遅れ列の区間数
    real(real64), allocatable :: qr(:)         ! 遅れ列の区間の雨 (m/s。先頭が次にタンクへ入る)
    integer, allocatable :: qn(:)              ! 遅れ列の区間のステップ数(合計 = nlag)
    real(real64) :: vlag = 0.0_real64          ! 移動中の水 = 遅れ列の雨の体積 A_g·Σ r·n·dt (m3)
    ! 蒸発散(§106.7)
    real(real64) :: elim = 0.0_real64          ! 線形低減を始める貯留 S_lim (m。0 = 供給制限のみ)
    real(real64) :: vevap = 0.0_real64         ! タンクから引いた蒸発散の累積 (m3)
  end type

  !-------------------------------------------
  ! 貯留関数法の状態の容器(t_encflow の成分。init に早期 return 経路が
  ! あるため全成分デフォルト初期化。§13)
  !-------------------------------------------
  type t_sfm
    logical :: enabled = .false.
    type(t_zonerunoff) :: zr                   ! 区画・雨の回収・出口・基底流(入力群 = 区画)
    type(t_sfmtank), allocatable :: tanks(:)   ! 区画のタンク
    real(real64) :: tol = 0.0_real64           ! 時間誤差の相対許容(流出強度に対する比)
    real(real64) :: dtmin = 0.0_real64         ! 内部刻みの下限 (s)
    logical :: have_lag = .false.              ! 遅れ時間のある区画があるか(sfm_zone.csv の vlag 列)
    logical :: et = .false.                    ! 蒸発散をタンクから引くか(fn_evap と併用。vevap 列)
    real(real64), allocatable :: dvz(:)        ! (1:nzone) 直近の同期区間の区画の流出 (m3。作業)
    integer :: un_zone = 0                     ! CSV 装置番号(rank0)
    logical :: initialized = .false.
  end type

contains


!----------------------------------------------------------------------
! 初期化(fn_sfm 未指定・f_sfm = 0 なら何もしない)
!   multi: 複数インスタンス(ネスト等)で実行中か(初版は非対応)
!   vzr  : VZ 流出の共通部(VZ が有効なら区画の重なりと出口を検査する)
!   evap_on: 蒸発散(fn_evap)が有効か(有効ならタンクから引く。§106.7)
!----------------------------------------------------------------------
subroutine m_sfm_init(sf, p, g, b, s, multi, vzr, evap_on)
  type(t_sfm), intent(out) :: sf
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(in) :: b
  type(t_state), intent(inout) :: s
  logical, intent(in) :: multi
  type(t_zonerunoff), intent(in) :: vzr
  logical, intent(in) :: evap_on
  type(t_list_sfm) :: list
  integer :: z

  if (len_trim(p%fn_sfm) == 0) then
    if (p%f_state_restore > 0) call stop_if_orphan(p)
    return
  end if
  call list_sfm_read(p, list)
  select case (list%f_sfm)
    case (0)
      call par_info("list_sfm: f_sfm=0, the storage function runoff is not enabled")
      if (p%f_state_restore > 0) call stop_if_orphan(p)
      return
    case (1)
    case default
      call par_stop("list_sfm: f_sfm must be 0 or 1: " // itoa(list%f_sfm))
  end select

  sf%zr%tag = "sfm"
  sf%zr%label = "SFM"
  sf%zr%nml = "list_sfm_zone"
  sf%zr%grpword = "zone"
  call check_combinations(p, multi)
  call setup_control(sf, p, list)
  call setup_zones(sf, p, g, b, list)

  allocate(s%sfp(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  s%sf_active = .true.
  ! 蒸発散の受け渡し口(fn_evap と併用時だけ確保 = m_evap が残りの要求を書く)
  if (evap_on) then
    allocate(s%sfe(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
    sf%et = .true.
    call par_info("sfm: evapotranspiration (fn_evap) left after canopy, surface water, ponds and groundwater" &
                  //" is taken from the tanks")
  else if (any(sf%tanks(:)%elim > 0.0_real64)) then
    call par_info("sfm: sfm_elim_mm is not used because fn_evap is not enabled")
  end if
  call zr_alloc_interval(sf%zr)
  allocate(sf%dvz(1:sf%zr%nzone), source = 0.0_real64)

  if (p%f_state_restore > 0) call restore_state(sf, p)

  ! 貯留の初期値(restore 時は復元したタンクの状態と遅れ列から)。vstore0 は移動中の水を含む
  do z = 1, sf%zr%nzone
    sf%tanks(z)%vstore = sf%zr%zones(z)%area * sf%tanks(z)%s
    sf%tanks(z)%vlag = sf%zr%zones(z)%area * lag_volume(sf%tanks(z), real(p%dt, real64))
    if (p%f_state_restore <= 0) sf%tanks(z)%vstore0 = sf%tanks(z)%vstore + sf%tanks(z)%vlag
  end do
  s%sfstore = total_storage(sf)

  ! VZ との併用: 区画のセルが重ならず、出口が相手の区画セルにないこと(collective)
  if (allocated(vzr%zid)) call zr_check_disjoint(vzr, sf%zr, g)

  call report_zones(sf)
  call open_csv(sf, p)
  sf%enabled = .true.
  sf%initialized = .true.
end subroutine


!----------------------------------------------------------------------
! 毎ステップ(swflow の直後。VZ の後): 雨の回収と、同期時刻ならタンクの前進・出口
!   判定(sf%enabled・mod(it, idt))は全ランク同一(collective 安全)
!----------------------------------------------------------------------
subroutine m_sfm_calc(sf, p, g, s, it)
  type(t_sfm), intent(inout) :: sf
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer, intent(in) :: it

  if (.not. sf%enabled) return
  call zr_recover_rain(sf%zr, p, g, s, s%sfp)
  if (mod(it, sf%zr%idt) == 0) call sync_interval(sf, p, s)
end subroutine


!----------------------------------------------------------------------
! 毎ステップ(m_evap_calc の直後): m_evap が区画セルに残した蒸発散の要求 s%sfe を
! 区画ごとに集め(行部分和 → par_sum_rows で決定的。collective)、面積平均の要求を
! その時刻のタンクの貯留から引く(§106.7)。判定 sf%et は全ランク同一
!----------------------------------------------------------------------
subroutine m_sfm_evap(sf, g, s)
  type(t_sfm), intent(inout) :: sf
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: i, j, z
  real(real64) :: tot, d, w
  real(real64), allocatable :: rows(:,:), r1(:)

  if (.not. sf%enabled) return
  if (.not. sf%et) return
  allocate(rows(dcp%js:dcp%je, 1:sf%zr%nzone), source = 0.0_real64)
  allocate(r1(dcp%js:dcp%je))
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      z = sf%zr%zid(i,j)
      if (z > 0) rows(j,z) = rows(j,z) + real(s%sfe(i,j), real64)
    end do
  end do
  s%sfe(:,:) = 0.0
  do z = 1, sf%zr%nzone
    associate (tk => sf%tanks(z), area => sf%zr%zones(z)%area)
      r1(:) = rows(:,z)
      call par_sum_rows(r1, tot)
      d = tot * sf%zr%dxdy / area            ! 区画の面積平均の要求 (m)
      if (d > 0.0_real64) then
        w = tank_et_draw(tk%s, d, tk%elim)
        tk%s = tk%s - w
        tk%vevap = tk%vevap + area * w
        tk%vstore = area * tk%s
      end if
    end associate
  end do
  s%sfstore = total_storage(sf)
end subroutine


!----------------------------------------------------------------------
! 区画の時系列 CSV sfm_zone.csv(dt_record 間隔。値は全ランク同値で rank0 が書く。
! 直近の同期時刻の値)
!   rain: 直近ステップの雨 (mm/h。地上の雨。遅れ時間があるとタンクへはその T_L 後に入る)、
!   q: タンクの流出強度 (mm/h)、S: 貯留 (mm)、区画の累積水量 (m3) と収支残差
!   (貯留と移動中の水の変化 − (入力 − 流出))。遅れ時間のある区画があれば vlag
!   (移動中の水 m3)の列を residual の後に置く。蒸発散をタンクから引くときは vevap(累積 m3)を
!   その後に置き、残差に含める(基底流の vbase はその後 = 最後)
!----------------------------------------------------------------------
subroutine m_sfm_record(sf, s)
  type(t_sfm), intent(in) :: sf
  type(t_state), intent(in) :: s
  integer :: z
  real(real64) :: res

  if (.not. sf%enabled) return
  if (.not. is_root) return
  do z = 1, sf%zr%nzone
    associate (tk => sf%tanks(z), zc => sf%zr%zones(z))
      ! 遅れなしの区画は従来と同じ式(-Ofast の並べ替えで丸めが変わらないよう、移動中の水は
      ! 遅れのある区画だけ別に足す)
      res = tk%vstore - tk%vstore0 - tk%vin + tk%vdrain
      if (tk%nlag > 0) res = res + tk%vlag
      if (sf%et) res = res + tk%vevap
      write(sf%un_zone, '(f0.2,",",i0,10(",",es23.15))', advance='no') s%t, z, &
            es_out([zc%area, sf%zr%rlast(z) * mmh, qfun(tk, tk%s) * mmh, tk%s * 1.0e3_real64, &
                    tk%vin, tk%vstore, tk%vdrain, zc%vint, zc%vext, res])
      if (sf%have_lag) write(sf%un_zone, '(",",es23.15)', advance='no') es_out(tk%vlag)
      if (sf%et) write(sf%un_zone, '(",",es23.15)', advance='no') es_out(tk%vevap)
      if (sf%zr%have_base) write(sf%un_zone, '(",",es23.15)', advance='no') es_out(zc%vbase)
      write(sf%un_zone, '(a)') ""
    end associate
  end do
  flush(sf%un_zone)
end subroutine


!----------------------------------------------------------------------
! 破棄(save は dispose で。契約5)。区間の途中で保存する場合は残りを
! 同期してから保存する(回収済みの雨を捨てない。s%h への移送は m_state の
! save より先なので保存状態に入る)
!----------------------------------------------------------------------
subroutine m_sfm_dispose(sf, p, s)
  type(t_sfm), intent(inout) :: sf
  type(t_sysparam), intent(in) :: p
  type(t_state), intent(inout) :: s
  if (.not. sf%enabled) return
  if (p%f_state_save > 0) then
    if (sf%zr%kstep > 0) then
      call par_info("sfm: syncing the partial interval of "//itoa(sf%zr%kstep)//" steps before saving")
      call sync_interval(sf, p, s)
    end if
    call save_state(sf, p)
  end if
  if (is_root .and. sf%un_zone /= 0) close(sf%un_zone)
  sf%un_zone = 0
  if (allocated(sf%tanks)) deallocate(sf%tanks)
  call zr_dispose(sf%zr)
  sf%enabled = .false.
  sf%initialized = .false.
end subroutine


!======================================================================
!========================= PRIVATE ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! 初版で併用できない機能・実行形態を停止する(VZ と同じ一覧。§106.1)
!----------------------------------------------------------------------
subroutine check_combinations(p, multi)
  type(t_sysparam), intent(in) :: p
  logical, intent(in) :: multi
  call no_combo(p%fn_gwflow, "fn_gwflow", "both would take the rain of the same cells into the ground")
  call no_combo(p%fn_snow, "fn_snow", "snowmelt would bypass the storage tanks")
  call no_combo(p%fn_glacier, "fn_glacier", "ice melt would bypass the storage tanks")
  call no_combo(p%fn_geomorph, "fn_geomorph", "rain-driven erosion would act on cells whose rain is taken" &
                //" into the tanks")
  call no_combo(p%fn_wq, "fn_wq", "the storage tanks do not carry solutes")
  call no_combo(p%fn_salt, "fn_salt", "the storage tanks do not interact with the saltwater layers")
  call no_combo(p%fn_nest, "fn_nest", "nesting is not supported by sfm yet")
  if (multi) call par_stop("list_sfm: multiple instances (nesting) are not supported by sfm yet")
  if (p%f_gridsystem /= 0) call par_stop("list_sfm: sfm requires f_gridsystem=0 (ENC)")
contains
  subroutine no_combo(fn, name, why)
    character(len=*), intent(in) :: fn, name, why
    if (len_trim(fn) > 0) call par_stop("list_sfm: sfm cannot be combined with "//name//" ("//why//")")
  end subroutine
end subroutine


!----------------------------------------------------------------------
! 共通設定と数値制御(既定は採用値を "(default)" 付きで表示。§62)
!   dt_sfm の既定 0(毎ステップ)は、タンクがスカラーで計算が無視できるため
!   (VZ の 60 s は柱の計算の費用による。§87.2)。sfm_tol・sfm_dt_min の既定は
!   test/sfzone の解析解検定で確かめた出発値(§106.3)
!----------------------------------------------------------------------
subroutine setup_control(sf, p, list)
  type(t_sfm), intent(inout) :: sf
  type(t_sysparam), intent(in) :: p
  type(t_list_sfm), intent(in) :: list
  real :: dts, v

  dts = param_default("sfm", "dt_sfm", list%dt_sfm, 0.0, " s", unset = -9999.0)
  if (dts < 0.0) call par_stop("list_sfm: dt_sfm must be >= 0 (0 = every step)")
  if (dts == 0.0) then
    sf%zr%idt = 1
  else
    sf%zr%idt = max(1, nint(dts / p%dt))
  end if
  if (sf%zr%idt > 1) call par_info("sfm: tanks are synchronised every "//itoa(sf%zr%idt)//" steps")

  select case (list%f_sfm_rain)
    case (0, 1)
      sf%zr%rainmode = list%f_sfm_rain
    case default
      call par_stop("list_sfm: f_sfm_rain must be 0(identical within a zone) or 1(area average): " &
                    // itoa(list%f_sfm_rain))
  end select

  v = param_default("sfm", "sfm_tol", list%sfm_tol, 1.0e-4, "", unset = -9999.0)
  sf%tol = real(v, real64)
  v = param_default("sfm", "sfm_dt_min", list%sfm_dt_min, 1.0e-3, " s", unset = -9999.0)
  sf%dtmin = real(v, real64)
  if (.not. (sf%tol > 0.0_real64 .and. sf%dtmin > 0.0_real64)) then
    call par_stop("list_sfm: sfm_tol and sfm_dt_min must be > 0")
  end if
end subroutine


!----------------------------------------------------------------------
! 区画: 区画番号マップ(共通基盤)・タンクのパラメータと初期条件・出口と基底流
!   K は必須(流域ごとに桁で変わり、根拠を示せる一般の既定がない)。P の既定は
!   木村(1961)の標準値 0.6、初期の流出強度 q0 の既定は VZ と同じ 0.1 mm/h
!   (経験値。§87.7)、遅れ時間 T_L の既定は 0(遅れなし)。採用値は必ず表示する。
!   T_L は dt の整数倍 nlag に丸め(誤差 dt/2 以下)、丸めた値も表示する。遅れ列の
!   初期値は q0 の定常(区間 1 つ = 雨 q0 が nlag ステップ)
!----------------------------------------------------------------------
subroutine setup_zones(sf, p, g, b, list)
  type(t_sfm), intent(inout) :: sf
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(in) :: b
  type(t_list_sfm), intent(in) :: list
  real, parameter :: p_default = 0.6       ! 木村(1961)の標準値
  real, parameter :: q0_default_mmh = 0.1  ! 降雨前の流出率の目安(経験値。VZ と同じ)
  integer, allocatable :: zmap(:,:), grp(:)
  integer :: z, nzn
  real :: kk, pp, q0, tl, el
  real(real64) :: tla
  character(len=16) :: tag
  character(len=256) :: line

  ! --- 区画番号マップ(共通基盤: 読み込み・セルの検査・セル数と面積・帯の区画番号) ---
  call zr_read_map(sf%zr, p, g, b, list%fn_sfm_zone, "fn_sfm_zone", sfm_nzonemax, zmap)
  nzn = sf%zr%nzone
  do z = nzn + 1, sfm_nzonemax
    if (list%sfm_out_kind(z) > -9998 .or. list%sfm_k(z) > -9998.0 .or. list%sfm_p(z) > -9998.0 .or. &
        list%sfm_q0_mmh(z) > -9998.0 .or. list%sfm_tl_h(z) > -9998.0 .or. list%sfm_elim_mm(z) > -9998.0 .or. &
        list%sfm_base(1,1,z) > -9998.0 .or. &
        len_trim(list%fn_sfm_base(z)) > 0) then
      call par_stop("list_sfm_zone: zone "//itoa(z)//" is set but absent from fn_sfm_zone")
    end if
  end do
  allocate(grp(1:nzn))
  do z = 1, nzn
    grp(z) = z                       ! 入力群 = 区画(区画ごとに 1 つのタンク)
  end do
  call zr_set_groups(sf%zr, grp, nzn)

  ! --- タンクのパラメータと初期条件 ---
  allocate(sf%tanks(1:nzn))
  do z = 1, nzn
    write(tag, '("(",i0,")")') z
    if (list%sfm_k(z) <= -9998.0) then
      call par_stop("list_sfm_zone: sfm_k"//trim(tag)//" must be given (K depends on the basin and has no" &
                    //" general default)")
    end if
    kk = param_default("sfm", "sfm_k"//trim(tag), list%sfm_k(z), 0.0, "", unset = -9999.0)
    pp = param_default("sfm", "sfm_p"//trim(tag), list%sfm_p(z), p_default, "", unset = -9999.0)
    q0 = param_default("sfm", "sfm_q0_mmh"//trim(tag), list%sfm_q0_mmh(z), q0_default_mmh, " mm/h", &
                       unset = -9999.0)
    if (.not. (kk > 0.0)) call par_stop("list_sfm_zone: sfm_k"//trim(tag)//" must be > 0")
    if (.not. (pp > 0.0 .and. pp <= 1.0)) call par_stop("list_sfm_zone: sfm_p"//trim(tag)//" must satisfy 0 < P <= 1")
    tl = param_default("sfm", "sfm_tl_h"//trim(tag), list%sfm_tl_h(z), 0.0, " h", unset = -9999.0)
    if (.not. (q0 >= 0.0)) call par_stop("list_sfm_zone: sfm_q0_mmh"//trim(tag)//" must be >= 0")
    if (.not. (tl >= 0.0)) call par_stop("list_sfm_zone: sfm_tl_h"//trim(tag)//" must be >= 0 (h)")
    el = 0.0
    if (list%sfm_elim_mm(z) > -9998.0) then
      el = param_default("sfm", "sfm_elim_mm"//trim(tag), list%sfm_elim_mm(z), 0.0, " mm", unset = -9999.0)
      if (.not. (el > 0.0)) call par_stop("list_sfm_zone: sfm_elim_mm"//trim(tag)//" must be > 0 (mm)")
    end if
    associate (tk => sf%tanks(z))
      tk%k = real(kk, real64)
      tk%p = real(pp, real64)
      tk%m = 1.0_real64 / tk%p
      tk%c = (1.0e3_real64 / tk%k)**tk%m / mmh
      tk%q0mmh = real(q0, real64)
      tk%s = tk%k * tk%q0mmh**tk%p * 1.0e-3_real64     ! S0 [m] = K·q0^P [mm] / 1000
      tk%hnext = real(p%dt, real64)
      tk%elim = real(el, real64) * 1.0e-3_real64
      ! 遅れ時間: dt の整数倍に丸める。遅れ列の初期値は q0 の定常
      tk%tlh = real(tl, real64)
      tk%nlag = nint(tk%tlh * 3600.0_real64 / real(p%dt, real64))
      tla = real(tk%nlag, real64) * real(p%dt, real64) / 3600.0_real64
      tk%tlah = tla
      if (tl > 0.0) then
        write(line, '(a,i0,a,g0.8,a,i0,a)') "sfm: zone ", z, " lag time T_L adopted as ", tla, &
              " h (", tk%nlag, " steps of dt)"
        if (abs(tla - tk%tlh) > 1.0e-9_real64 * tk%tlh) then
          write(line, '(a,a,g0.8,a)') trim(line), "; rounded from ", tk%tlh, " h to a multiple of dt"
        end if
        call par_info(trim(line))
      end if
      if (tk%nlag > 0) then
        allocate(tk%qr(1:4), tk%qn(1:4))
        tk%nq = 1
        tk%qr(1) = tk%q0mmh / mmh
        tk%qn(1) = tk%nlag
        sf%have_lag = .true.
      end if
    end associate
  end do

  ! --- 出口と基底流(共通基盤) ---
  call zr_setup_outlets(sf%zr, g, b, list%sfm_out_kind, list%sfm_out_cell, list%sfm_out_w, zmap)
  call zr_setup_baseflow(sf%zr, p, list%sfm_base, list%fn_sfm_base)
end subroutine


!----------------------------------------------------------------------
! 同期: 区間の入力を確定し(共通基盤)、全タンクを進め、出口へ渡す(共通基盤)。
! collective(全ランクが同じ順で呼ぶ)
!----------------------------------------------------------------------
subroutine sync_interval(sf, p, s)
  type(t_sfm), intent(inout) :: sf
  type(t_sysparam), intent(in) :: p
  type(t_state), intent(inout) :: s
  integer :: z, k, ntseg
  real(real64) :: rin, vout, h
  real(real64), allocatable :: tsegl(:), tsegr(:)
  logical :: ok
  character(len=512) :: msg

  if (sf%zr%kstep == 0) return
  h = real(p%dt, real64)

  ! --- 区間の各ステップの雨(区画ごと)を確定し、区分一定の区間に圧縮する ---
  call zr_collect_input(sf%zr, p)

  ! --- タンクを進める(全ランクが同じ順で冗長に) ---
  do z = 1, sf%zr%nzone
    associate (tk => sf%tanks(z), area => sf%zr%zones(z)%area)
      rin = 0.0_real64
      do k = 1, sf%zr%nseg(z)
        if (sf%zr%segr(k,z) < 0.0_real64) then
          call par_stop("sfm: negative input (rainfall) to zone "//itoa(z)//"; the storage function" &
                        //" takes non-negative input only")
        end if
        rin = rin + sf%zr%segl(k,z) * sf%zr%segr(k,z)
      end do
      if (tk%nlag == 0) then
        call tank_advance(tk, sf%zr%nseg(z), sf%zr%segl(:,z), sf%zr%segr(:,z), sf%tol, sf%dtmin, vout, ok)
      else
        ! 遅れ時間: 区間の雨を遅れ列の末尾に足し、先頭から区間と同じステップ数を取り出して
        ! タンクの入力にする(遅れ列の長さは nlag ステップのまま)
        call lag_shift(tk, sf%zr%nseg(z), sf%zr%segl(:,z), sf%zr%segr(:,z), h, ntseg, tsegl, tsegr)
        call tank_advance(tk, ntseg, tsegl, tsegr, sf%tol, sf%dtmin, vout, ok)
        tk%vlag = area * lag_volume(tk, h)
      end if
      if (.not. ok) then
        write(msg, '(a,i0,a,f0.1,a,es10.3,a)') "sfm: zone ", z, " cannot advance at t=", s%t, &
              " s (internal time step fell below sfm_dt_min=", sf%dtmin, " s)"
        call par_stop(trim(msg))
      end if
      tk%vin = tk%vin + area * rin
      tk%dvlast = area * vout
      tk%vdrain = tk%vdrain + tk%dvlast
      sf%dvz(z) = tk%dvlast
      tk%vstore = area * tk%s
    end associate
  end do

  ! --- 基底流を加えて出口へ渡し、区間を閉じる(s%sfp も 0 に戻す) ---
  call zr_deliver(sf%zr, p, s, sf%dvz, s%sfp)

  ! --- 台帳 ---
  s%sfstore = total_storage(sf)
end subroutine


!----------------------------------------------------------------------
! 遅れ列の更新(§106.6): 区間の区分一定の雨(segl [s]・segr [m/s])をステップ数に
! 直して遅れ列の末尾に足し(直前の区間と同じ雨なら継ぎ足す)、先頭から区間と同じ
! ステップ数を取り出してタンクの入力の区間 tl [s]・tr [m/s] を返す。遅れ列の長さは
! nlag ステップに保たれる(区間の数は雨の変化の数で決まり、dt に依らない)
!----------------------------------------------------------------------
subroutine lag_shift(tk, nseg, segl, segr, h, nt, tl, tr)
  type(t_sfmtank), intent(inout) :: tk
  integer, intent(in) :: nseg
  real(real64), intent(in) :: segl(:), segr(:)
  real(real64), intent(in) :: h
  integer, intent(out) :: nt
  real(real64), allocatable, intent(out) :: tl(:), tr(:)
  integer :: k, n, nk, i, take, j

  ! --- 末尾に足す ---
  nk = 0
  do k = 1, nseg
    n = nint(segl(k) / h)
    nk = nk + n
    if (tk%nq > 0) then
      if (tk%qr(tk%nq) == segr(k)) then
        tk%qn(tk%nq) = tk%qn(tk%nq) + n
        cycle
      end if
    end if
    call lag_grow(tk, tk%nq + 1)
    tk%nq = tk%nq + 1
    tk%qr(tk%nq) = segr(k)
    tk%qn(tk%nq) = n
  end do

  ! --- 先頭から nk ステップを取り出す ---
  allocate(tl(1:tk%nq), tr(1:tk%nq))
  nt = 0
  i = 1
  do while (nk > 0)
    take = min(tk%qn(i), nk)
    nt = nt + 1
    tl(nt) = real(take, real64) * h
    tr(nt) = tk%qr(i)
    tk%qn(i) = tk%qn(i) - take
    nk = nk - take
    if (tk%qn(i) == 0) i = i + 1
  end do
  ! 取り出し終えた区間を詰める
  j = 0
  do k = i, tk%nq
    j = j + 1
    tk%qr(j) = tk%qr(k)
    tk%qn(j) = tk%qn(k)
  end do
  tk%nq = j
end subroutine


!----------------------------------------------------------------------
! 遅れ列の容量を n 以上にする(倍々に伸ばす)
!----------------------------------------------------------------------
subroutine lag_grow(tk, n)
  type(t_sfmtank), intent(inout) :: tk
  integer, intent(in) :: n
  real(real64), allocatable :: tr(:)
  integer, allocatable :: tn(:)
  integer :: ncap
  if (.not. allocated(tk%qr)) then
    allocate(tk%qr(1:max(n, 4)), tk%qn(1:max(n, 4)))
    return
  end if
  ncap = size(tk%qr)
  if (n <= ncap) return
  ncap = max(n, 2 * ncap)
  allocate(tr(1:ncap), tn(1:ncap))
  tr(1:tk%nq) = tk%qr(1:tk%nq)
  tn(1:tk%nq) = tk%qn(1:tk%nq)
  call move_alloc(tr, tk%qr)
  call move_alloc(tn, tk%qn)
end subroutine


!----------------------------------------------------------------------
! 遅れ列の雨の量(単位面積 m。移動中の水)= Σ r·n·dt
!----------------------------------------------------------------------
pure real(real64) function lag_volume(tk, h) result(v)
  type(t_sfmtank), intent(in) :: tk
  real(real64), intent(in) :: h
  integer :: i
  v = 0.0_real64
  do i = 1, tk%nq
    v = v + tk%qr(i) * real(tk%qn(i), real64) * h
  end do
end function


!----------------------------------------------------------------------
! タンクを区分一定の入力の区間で進める(ステップ二分比較の刻み制御)
!   vout: 区間の流出 (m。単位面積)。ok = .false. は刻みが dtmin を下回った
!   誤差の尺度: 貯留の相対誤差は流出強度の相対誤差の P 倍(q ∝ S^(1/P))なので、
!   |S_fine − S_coarse| ≤ tol·P·(S_fine + s_abs) を受理の条件とする
!----------------------------------------------------------------------
subroutine tank_advance(tk, nseg, segl, segr, tol, dtmin, vout, ok)
  type(t_sfmtank), intent(inout) :: tk
  integer, intent(in) :: nseg
  real(real64), intent(in) :: segl(:), segr(:)
  real(real64), intent(in) :: tol, dtmin
  real(real64), intent(out) :: vout
  logical, intent(out) :: ok
  real(real64), parameter :: fmax = 2.0_real64, fmin = 0.2_real64, safety = 0.9_real64
  integer :: ks
  real(real64) :: trem, h, r, s0, sc, sh, sf, s1, err, sc_err, fac

  vout = 0.0_real64
  ok = .true.
  do ks = 1, nseg
    r = segr(ks)
    trem = segl(ks)
    do while (trem > 0.0_real64)
      h = min(tk%hnext, trem)
      s0 = tk%s
      sc = be_step(tk, s0, r, h)
      sh = be_step(tk, s0, r, 0.5_real64 * h)
      sf = be_step(tk, sh, r, 0.5_real64 * h)
      err = abs(sf - sc)
      sc_err = tol * tk%p * (sf + s_abs)
      if (err > 0.0_real64) then
        fac = min(fmax, max(fmin, safety * sqrt(sc_err / err)))
      else
        fac = fmax
      end if
      if (err <= sc_err) then
        ! 受理: 局所外挿(2 次)。区間 [0, S0 + h·r] を外れれば細かい枝
        s1 = 2.0_real64 * sf - sc
        if (s1 < 0.0_real64 .or. s1 > s0 + h * r) s1 = sf
        vout = vout + (s0 + h * r - s1)
        tk%s = s1
        trem = trem - h
        tk%nacc = tk%nacc + 1
        if (h < tk%hnext) then
          tk%hnext = min(tk%hnext, h * fac)  ! 区間端で切った刻み: 提案は広げない
        else
          tk%hnext = h * fac
        end if
      else
        tk%nrej = tk%nrej + 1
        tk%hnext = h * fac
        if (tk%hnext < dtmin) then
          ok = .false.
          return
        end if
      end if
    end do
  end do
end subroutine


!----------------------------------------------------------------------
! 後退 Euler の 1 歩: S1 + h·q(S1) = S0 + h·r を解く(q は S の増加関数なので
! 解は [0, S0 + h·r] に一意。Newton 法を二分法で保護する。P = 1 は直接解く)
!----------------------------------------------------------------------
real(real64) function be_step(tk, s0, r, h) result(s)
  type(t_sfmtank), intent(in) :: tk
  real(real64), intent(in) :: s0, r, h
  integer :: it
  real(real64) :: bb, lo, hi, f, dq, snew

  bb = s0 + h * r
  if (bb <= 0.0_real64) then
    s = 0.0_real64
    return
  end if
  if (tk%m == 1.0_real64) then
    s = bb / (1.0_real64 + h * tk%c)
    return
  end if
  lo = 0.0_real64
  hi = bb
  s = max(0.0_real64, min(bb, s0 + h * (r - qfun(tk, s0))))   ! 陽的 Euler の予測から
  do it = 1, 200
    f = s + h * qfun(tk, s) - bb
    if (f == 0.0_real64) return
    if (f > 0.0_real64) then
      hi = s
    else
      lo = s
    end if
    if (s > 0.0_real64) then
      dq = tk%c * tk%m * s**(tk%m - 1.0_real64)
    else
      dq = 0.0_real64                ! m > 1 なので dq/dS → 0
    end if
    snew = s - f / (1.0_real64 + h * dq)
    if (.not. (snew > lo .and. snew < hi)) snew = 0.5_real64 * (lo + hi)
    if (abs(snew - s) <= 4.0_real64 * epsilon(1.0_real64) * bb) then
      s = snew
      return
    end if
    s = snew
  end do
end function


!----------------------------------------------------------------------
! タンクから引く蒸発散の量 (m。§106.7)。d はそのステップの要求 E·dt。
!   el = 0: 供給制限のみ(min(S, d))。
!   el > 0: dS/dt = −E·min(1, S/el) をステップ内で E 一定として厳密に解いた減少量
!   (地下水の段の hg_draw と同じ式。§27.2。タンクの状態は real64 なので real64 で書く)。
!   結果は S を超えない
!----------------------------------------------------------------------
pure real(real64) function tank_et_draw(s, d, el) result(w)
  real(real64), intent(in) :: s, d, el
  real(real64) :: lin, x
  if (s <= 0.0_real64) then
    w = 0.0_real64
  else if (el <= 0.0_real64) then
    w = min(s, d)
  else if (s - d >= el) then
    w = d                                     ! ステップの間ずっと抑制なし
  else
    lin = max(s - el, 0.0_real64)             ! el まで線形に引ける分(時間 lin/E)
    x = (d - lin) / el
    if (x < 1.0e-2_real64) then               ! 1 − exp(−x) の桁落ち対策(hg_draw と同じ級数)
      w = lin + (s - lin) * (x * (1.0_real64 - 0.5_real64 * x * (1.0_real64 - x / 3.0_real64 &
          * (1.0_real64 - 0.25_real64 * x * (1.0_real64 - 0.2_real64 * x)))))
    else
      w = lin + (s - lin) * (1.0_real64 - exp(-x))
    end if
  end if
end function


!----------------------------------------------------------------------
! 流出強度 q(S) = c·S^m (m/s。S [m])
!----------------------------------------------------------------------
pure real(real64) function qfun(tk, s) result(q)
  type(t_sfmtank), intent(in) :: tk
  real(real64), intent(in) :: s
  if (s <= 0.0_real64) then
    q = 0.0_real64
  else if (tk%m == 1.0_real64) then
    q = tk%c * s
  else
    q = tk%c * s**tk%m
  end if
end function


!----------------------------------------------------------------------
! 全区画のタンク貯留と移動中の水を柱状換算の総和で返す
! (Σ (S_g·A_g + 遅れ列の水)/(dx·dy)。calcstat 用。遅れなしなら vlag = 0)
!----------------------------------------------------------------------
real(real64) function total_storage(sf)
  type(t_sfm), intent(in) :: sf
  integer :: z
  total_storage = 0.0_real64
  do z = 1, sf%zr%nzone
    total_storage = total_storage + (sf%tanks(z)%vstore + sf%tanks(z)%vlag)
  end do
  total_storage = total_storage / sf%zr%dxdy
end function


!----------------------------------------------------------------------
! 区画確認表(初期化時に画面へ。Log.txt には書かない)
!----------------------------------------------------------------------
subroutine report_zones(sf)
  type(t_sfm), intent(in) :: sf
  integer :: z
  character(len=512) :: line
  call par_info("sfm: "//itoa(sf%zr%nzone)//" zone(s) (one storage tank per zone)")
  do z = 1, sf%zr%nzone
    associate (tk => sf%tanks(z), zc => sf%zr%zones(z))
      write(line, '(a,i0,a,i0,a,es11.4,a,g0.6,a,g0.6,a,g0.6,a,g0.6,a)') "  zone ", z, ": cells ", zc%ncell, &
            ", area ", zc%area, " m2, K ", tk%k, ", P ", tk%p, ", initial q ", tk%q0mmh, " mm/h (S ", &
            tk%s * 1.0e3_real64, " mm)"
      call par_info(trim(line))
      if (tk%elim > 0.0_real64) then
        write(line, '(a,g0.6,a)') "    evapotranspiration reduced linearly below S = ", tk%elim * 1.0e3_real64, " mm"
        call par_info(trim(line))
      end if
      if (tk%nlag > 0) then
        write(line, '(a,g0.8,a,i0,a)') "    lag time T_L ", tk%tlah, " h (", tk%nlag, &
              " steps of dt; the rain enters the tank T_L later)"
        call par_info(trim(line))
      end if
      call zr_report_outlets(sf%zr, z)
    end associate
  end do
end subroutine


!----------------------------------------------------------------------
! CSV を開く(rank0)
!----------------------------------------------------------------------
subroutine open_csv(sf, p)
  type(t_sfm), intent(inout) :: sf
  type(t_sysparam), intent(in) :: p
  if (.not. is_root) return
  open(newunit=sf%un_zone, file=trim(p%dir_result)//"/sfm_zone.csv", status='replace')
  write(sf%un_zone, '(a)', advance='no') "time(s),zone,area(m2),rain(mm/h),q(mm/h),S(mm),vin(m3)," // &
                                         "vstore(m3),vdrain(m3),vsurface(m3),vexternal(m3),residual(m3)"
  if (sf%have_lag) write(sf%un_zone, '(a)', advance='no') ",vlag(m3)"
  if (sf%et) write(sf%un_zone, '(a)', advance='no') ",vevap(m3)"
  if (sf%zr%have_base) write(sf%un_zone, '(a)', advance='no') ",vbase(m3)"
  write(sf%un_zone, '(a)') ""
end subroutine


!----------------------------------------------------------------------
! 保存(私有ファイル sfm.dat。rank0 が書く。読み並びは restore_state と対)。
! 出口の繰越は共通基盤の zr_gather_carry で全ランク同値に集めてから書く(collective)
!----------------------------------------------------------------------
subroutine save_state(sf, p)
  type(t_sfm), intent(in) :: sf
  type(t_sysparam), intent(in) :: p
  integer :: un, z
  real(real64), allocatable :: carry(:)
  call zr_gather_carry(sf%zr, carry)
  if (.not. is_root) return
  call sysdep_mkdir(p%dir_save)
  open(newunit=un, file=trim(p%dir_save)//'/sfm.dat', form='unformatted', status='replace')
  write(un) save_version, sf%zr%nzone, sf%zr%nocell
  do z = 1, sf%zr%nzone
    write(un) sf%zr%zones(z)%ncell, sf%tanks(z)%k, sf%tanks(z)%p, sf%tanks(z)%nlag
  end do
  do z = 1, sf%zr%nzone
    associate (tk => sf%tanks(z), zc => sf%zr%zones(z))
      write(un) tk%s, tk%hnext, tk%nacc, tk%nrej, sf%zr%rlast(z), tk%vin, tk%vdrain, zc%vint, zc%vext, &
                tk%vstore0, tk%dvlast, zc%vbase, tk%vevap
      write(un) tk%nq                  ! 遅れ列(遅れなしなら 0 で中身なし)
      if (tk%nq > 0) write(un) tk%qr(1:tk%nq), tk%qn(1:tk%nq)
    end associate
  end do
  if (sf%zr%nocell > 0) then
    write(un) sf%zr%ocell(:, 1:sf%zr%nocell)
    write(un) carry(1:sf%zr%nocell), sf%zr%ovcum(1:sf%zr%nocell)
  end if
  close(un)
end subroutine


!----------------------------------------------------------------------
! 復元(全ランクが同じファイルを読む。小さいベクトルだけなので配布はしない)。
! 構成の識別(区画・出口の数、区画のセル数・K・P)が保存時と違えば停止する
!----------------------------------------------------------------------
subroutine restore_state(sf, p)
  type(t_sfm), intent(inout) :: sf
  type(t_sysparam), intent(in) :: p
  character(:), allocatable :: fname
  logical :: found, mismatch
  integer :: un, ver, nzn, noc, z, ncell, ios, nlag, nq
  real(real64) :: kk, pp
  real(real64), allocatable :: tmp(:)
  integer, allocatable :: oc(:,:)

  fname = trim(p%dir_save)//'/sfm.dat'
  inquire(file=fname, exist=found)
  if (.not. found) call par_stop("sfm: state file not found (was fn_sfm enabled when saving): "//fname)
  mismatch = .false.
  open(newunit=un, file=fname, form='unformatted', status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("sfm: cannot open "//fname)
  read(un) ver, nzn, noc
  if (ver /= save_version) then
    close(un)
    call par_stop("sfm: state file format version "//itoa(ver)//" does not match the version this " &
                  //"executable reads ("//itoa(save_version)//"): "//fname)
  end if
  if (nzn /= sf%zr%nzone .or. noc /= sf%zr%nocell) then
    mismatch = .true.
  else
    do z = 1, nzn
      read(un) ncell, kk, pp, nlag
      if (ncell /= sf%zr%zones(z)%ncell .or. kk /= sf%tanks(z)%k .or. pp /= sf%tanks(z)%p .or. &
          nlag /= sf%tanks(z)%nlag) mismatch = .true.
    end do
  end if
  if (mismatch) then
    close(un)
    call par_stop("sfm: the configuration (zones, K, P, lag steps or outlets) differs from the saved state "//fname)
  end if
  do z = 1, nzn
    associate (tk => sf%tanks(z), zc => sf%zr%zones(z))
      read(un) tk%s, tk%hnext, tk%nacc, tk%nrej, sf%zr%rlast(z), tk%vin, tk%vdrain, zc%vint, zc%vext, &
               tk%vstore0, tk%dvlast, zc%vbase, tk%vevap
      read(un) nq
      tk%nq = 0
      if (nq > 0) then
        call lag_grow(tk, nq)
        read(un) tk%qr(1:nq), tk%qn(1:nq)
        tk%nq = nq
      end if
    end associate
  end do
  if (noc > 0) then
    allocate(oc(1:2, 1:noc), tmp(1:noc))
    read(un) oc
    if (any(oc /= sf%zr%ocell(:, 1:noc))) then
      close(un)
      call par_stop("sfm: the outlet cells differ from the saved state "//fname)
    end if
    read(un) tmp, sf%zr%ovcum(1:noc)
    sf%zr%ocarry(1:noc) = tmp
  end if
  close(un)
end subroutine


!----------------------------------------------------------------------
! 無効なのに私有ファイルが dir_save にあれば停止する(保存時のタンク貯留を
! 黙って捨てない。§16.2 の stop_if_orphan_state と同じ門番)
!----------------------------------------------------------------------
subroutine stop_if_orphan(p)
  type(t_sysparam), intent(in) :: p
  logical :: found
  inquire(file=trim(p%dir_save)//'/sfm.dat', exist=found)
  if (found) then
    call par_stop("sfm: sfm.dat exists in "//trim(p%dir_save)//" but the storage function runoff is not" &
                  //" enabled at restart (its stored state would be dropped); enable fn_sfm or remove the" &
                  //" file if the drop is intended")
  end if
end subroutine

end module
