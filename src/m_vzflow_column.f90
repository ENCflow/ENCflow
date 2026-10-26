module m_vzflow_column
  ! ========== VZ 共有参照柱の計算核: 1 次元 Richards 式(混合形) ==========
  ! 谷(2023)の VZ 流出モデルの「十分深い参照土壌柱」を 1 本解く汎用手続き
  ! (developer.md §87、docs/vz_plan.md §5)。水平格子・区画・出口・MPI を
  ! 知らない(呼び出し側 m_vzflow が全ランクで同じ入力を与えて冗長に解く)。
  !
  ! 【基礎式と出典】
  !   下向きの深さ ζ、下向き正の流束 f = K(ψ)(1 − ∂ψ/∂ζ)、
  !   ∂θ(ψ)/∂t = −∂f/∂ζ(吸水なし)。
  !   保水・透水特性は小杉式(Kosugi 1996, WRR 32(9)):
  !     x = (ln|ψ| − ln|ψm|)/σ、Q(x) = erfc(x/√2)/2、
  !     θ = θr + (θs − θr) Q(x)、K = Ks Q(x)^{1/2} Q(x+σ)²、ψ ≥ 0 は θs・Ks。
  !   離散化は有限体積(層平均の θ、界面の f)+後退 Euler。収束判定の正本は
  !   元の残差 R_k = Δζ_k(θ(ψ_k) − θ_k^old) + δt(f_k − f_{k−1})
  !   (Celia ら 1990, WRR 26(7) の保存的な混合形を有限体積で書いたもの。
  !   有限体積への展開は独自)。反復は修正 Picard(K を固定、貯留を
  !   C = dθ/dψ で線形化)、線形解法は Thomas 法。
  !
  ! 【時間刻みと受理】(vz_plan.md §5.2。解法補足の骨格のうち初版に入れた部分)
  !   同じ旧状態から粗い 1 歩(δt)と細かい 2 歩(δt/2 × 2)を解き、ψ・θ・
  !   全界面の積算流束 F の差で時間誤差を判定する(ステップ二分比較)。
  !   F の尺度は界面ごとの相対値で、下限を柱内の最大流束の q_floor 倍とする
  !   (流束がほぼ 0 の界面で相対判定が極端に厳しくなるのを防ぐ。独自)。
  !   合格なら細かい枝の状態と流束を一組で採用する(Richardson 外挿はしない)。
  !   非収束・数値範囲外・時間誤差過大は旧状態に戻して δt を半分にする。
  !   L スキーム・残差の直線探索・Newton は未実装(単体試験で必要が示されたら
  !   足す。§0-6)。
  !
  ! 【境界】
  !   上端: 規定流束(地上雨量。区間内一定の区分一定値で与える)。受理した
  !   解で地表面の圧力の再構成が正を要したら湛水 = 適用外として返す。
  !   下端: 自由排水 f_N = K(ψ_N)(既定)/ 固定圧 ψ_b(検証用)。
  !
  ! 【精度】状態・係数・残差・積算水量は real64 固定(developer.md §1 の例外)。
  !   リテラルは _real64 を付ける(単精度ビルドで定数の精度が落ちないように)。
  ! ====================================================================
  use, intrinsic :: iso_fortran_env, only : real64, int64
  implicit none
  private
  public :: t_vzcol, t_vzctl, t_vzgeo
  public :: vzcol_init, vzcol_advance, vzcol_props, vzcol_dispose
  public :: vzcol_steady_psi
  public :: vz_ok, vz_fail_time, vz_fail_ponding

  ! 前進の結果(vzcol_advance の stat)
  integer, parameter :: vz_ok = 0            ! 成功
  integer, parameter :: vz_fail_time = 1     ! 時間刻みが dt_min を下回っても受理できない
  integer, parameter :: vz_fail_ponding = 2  ! 収束解で湛水が必要(適用外)

  ! 失敗の種類(診断用。t_vzcol%lastfail)
  integer, parameter :: fk_none = 0, fk_nonlin = 1, fk_range = 2, fk_linear = 3, fk_terr = 4

  real(real64), parameter :: sqrt2 = 1.4142135623730950488_real64
  real(real64), parameter :: sqrt2pi = 2.5066282746310005024_real64
  real(real64), parameter :: psi_range = 1.0e6_real64   ! |ψ| がこれを超えた試行は数値範囲外(m)

  !-------------------------------------------
  ! 数値制御(全柱共通。値の既定・検証は m_vzflow_init)
  !-------------------------------------------
  type t_vzctl
    integer :: kface = 1                     ! 界面透水係数 1: 算術平均 / 2: 調和平均
    integer :: maxit = 25                    ! Picard 反復の上限
    real(real64) :: dt_init = 1.0_real64     ! 初期の試行刻み (s)
    real(real64) :: dt_min = 1.0e-3_real64   ! 試行刻みの下限 (s)
    real(real64) :: dt_max = 3600.0_real64   ! 試行刻みの上限 (s)
    real(real64) :: grow = 1.5_real64        ! 刻みの増加率の上限
    real(real64) :: tol_th = 1.0e-3_real64   ! 時間誤差の θ 尺度(θs − θr に対する比)
    real(real64) :: tol_psi_a = 1.0e-3_real64 ! 時間誤差の ψ 尺度(絶対 m)
    real(real64) :: tol_psi_r = 1.0e-3_real64 ! 時間誤差の ψ 尺度(相対)
    real(real64) :: tol_q_a = 1.0e-10_real64 ! 時間誤差の積算流束の尺度(絶対。m/s × δt)
    real(real64) :: tol_q_r = 1.0e-2_real64  ! 時間誤差の積算流束の尺度(相対)
    real(real64) :: q_floor = 1.0e-2_real64  ! 相対尺度の下限 = 柱内の最大流束 × この比
                                             !   (流束がほぼ 0 の界面 = 毛管上昇と重力排水の
                                             !   境目などを過剰に厳しく判定しない)
    real(real64) :: nl_factor = 1.0e-2_real64 ! 非線形許容 = 時間許容 × この係数
    real(real64) :: mb_rate = 1.0e-11_real64 ! 柱全体の非線形水収支誤差の予算 (m/s)
  end type

  !-------------------------------------------
  ! 柱の幾何と物性(計算中は不変。手続きへは intent(in) で渡す)
  !-------------------------------------------
  type t_vzgeo
    integer :: nz = 0                        ! 層数
    real(real64) :: depth = 0.0_real64       ! 計算柱の深さ L (m)
    real(real64), allocatable :: zf(:)       ! 界面の深さ (0:nz)。zf(0) = 0、zf(nz) = L
    real(real64), allocatable :: zc(:)       ! 層中心の深さ (1:nz)
    real(real64), allocatable :: dzl(:)      ! 層厚 (1:nz)
    real(real64), allocatable :: ell(:)      ! 層中心間の距離 (1:nz−1)
    ! --- 小杉式のパラメータ(柱内一様) ---
    real(real64) :: ks = 0.0_real64          ! 飽和透水係数 (m/s)
    real(real64) :: ths = 0.0_real64         ! 飽和含水率
    real(real64) :: thr = 0.0_real64         ! 残留含水率
    real(real64) :: psim = 0.0_real64        ! 中央値の圧力水頭 ψm (m。負)
    real(real64) :: sigma = 0.0_real64       ! 対数標準偏差 σ
    real(real64) :: lnpm = 0.0_real64        ! ln|ψm|
    ! --- 下端 ---
    integer :: bottom = 1                    ! 1: 自由排水 / 2: 固定圧
    real(real64) :: psibot = 0.0_real64      ! 固定圧の ψ_b (m。bottom = 2)
    real(real64) :: kbot = 0.0_real64        ! K(ψ_b)
  end type

  !-------------------------------------------
  ! 後退 Euler 1 歩の作業領域(結果 psi・th・f もここに置き、呼び出し側が
  ! 枝の配列へ写す。仮引数どうしの重なりを作らないための分離)
  !-------------------------------------------
  type t_vzwork
    real(real64), allocatable :: psi(:), th(:), f(:)
    real(real64), allocatable :: cap(:), kk(:), kf(:), r(:)
    real(real64), allocatable :: ta(:), tb(:), tc(:), td(:), thp(:)
  end type

  !-------------------------------------------
  ! 1 本の柱(成分は呼び出し側が読む。書くのは本モジュールの手続きだけ)
  !-------------------------------------------
  type t_vzcol
    type(t_vzgeo) :: geo                     ! 幾何と物性
    ! --- 状態(受理済み) ---
    real(real64), allocatable :: psi(:)      ! 圧力水頭 (1:nz。m)
    real(real64), allocatable :: th(:)       ! 含水率 (1:nz。psi から導出)
    real(real64) :: dtnext = 0.0_real64      ! 次の試行刻み (s)
    ! --- 診断(累積) ---
    integer(int64) :: nacc = 0               ! 受理した刻みの数
    integer(int64) :: nrej = 0               ! 棄却した刻みの数(非収束・範囲外・時間誤差)
    integer(int64) :: nit = 0                ! Picard 反復の総数
    integer :: lastfail = fk_none            ! 直近の棄却の種類
    real(real64) :: dtlast = 0.0_real64      ! 直近に受理した刻み (s)
    ! --- 二分比較の枝(柱ごとに所有。OpenMP で柱を並列に解くため) ---
    real(real64), allocatable :: pc(:), thc(:), fc(:)     ! 粗い枝
    real(real64), allocatable :: ph(:), thh(:), fh1(:)    ! 細かい枝の 1 歩目
    real(real64), allocatable :: pf(:), thf(:), fh2(:)    ! 細かい枝の 2 歩目
    type(t_vzwork) :: w                      ! 後退 Euler の作業領域
    logical :: initialized = .false.
  end type

contains


!----------------------------------------------------------------------
! 柱を初期化する(一様格子。ψ の初期値は一様 psi0)
!   ok = .false. は格子の不整合(depth が dz の整数倍でない・層数 < 2)。
!   物性の値域は呼び出し側(m_vzflow_init)が検証済みの前提
!----------------------------------------------------------------------
subroutine vzcol_init(col, ctl, ks, ths, thr, psim, sigma, depth, dz, bottom, psibot, psi0, ok)
  type(t_vzcol), intent(inout) :: col
  type(t_vzctl), intent(in) :: ctl
  real(real64), intent(in) :: ks, ths, thr, psim, sigma
  real(real64), intent(in) :: depth, dz
  integer, intent(in) :: bottom
  real(real64), intent(in) :: psibot, psi0
  logical, intent(out) :: ok
  integer :: k, nz
  real(real64) :: dum1, dum2

  ok = .false.
  nz = nint(depth / dz)
  if (nz < 2) return
  if (abs(real(nz, real64) * dz - depth) > 1.0e-9_real64 * depth) return
  associate (geo => col%geo)
    geo%nz = nz
    geo%depth = depth
    geo%ks = ks
    geo%ths = ths
    geo%thr = thr
    geo%psim = psim
    geo%sigma = sigma
    geo%lnpm = log(-psim)
    geo%bottom = bottom
    geo%psibot = psibot
    allocate(geo%zf(0:nz), geo%zc(1:nz), geo%dzl(1:nz), geo%ell(1:nz-1))
    do k = 0, nz
      geo%zf(k) = real(k, real64) * dz
    end do
    geo%zf(nz) = depth
    do k = 1, nz
      geo%dzl(k) = geo%zf(k) - geo%zf(k-1)
      geo%zc(k) = 0.5_real64 * (geo%zf(k-1) + geo%zf(k))
    end do
    do k = 1, nz - 1
      geo%ell(k) = geo%zc(k+1) - geo%zc(k)
    end do
    call vzcol_props(geo, psibot, dum1, dum2, geo%kbot)
  end associate

  allocate(col%psi(1:nz), source = psi0)
  allocate(col%th(1:nz))
  do k = 1, nz
    call vzcol_props(col%geo, col%psi(k), col%th(k), dum1, dum2)
  end do
  allocate(col%pc(1:nz), col%thc(1:nz), col%fc(0:nz))
  allocate(col%ph(1:nz), col%thh(1:nz), col%fh1(0:nz))
  allocate(col%pf(1:nz), col%thf(1:nz), col%fh2(0:nz))
  associate (w => col%w)
    allocate(w%psi(1:nz), w%th(1:nz), w%f(0:nz))
    allocate(w%cap(1:nz), w%kk(1:nz), w%kf(0:nz), w%r(1:nz))
    allocate(w%ta(1:nz), w%tb(1:nz), w%tc(1:nz), w%td(1:nz), w%thp(1:nz))
  end associate
  col%dtnext = ctl%dt_init
  col%nacc = 0
  col%nrej = 0
  col%nit = 0
  col%lastfail = fk_none
  col%dtlast = 0.0_real64
  col%initialized = .true.
  ok = .true.
end subroutine


!----------------------------------------------------------------------
! 柱を破棄する
!----------------------------------------------------------------------
subroutine vzcol_dispose(col)
  type(t_vzcol), intent(inout) :: col
  if (allocated(col%geo%zf)) deallocate(col%geo%zf, col%geo%zc, col%geo%dzl, col%geo%ell)
  if (allocated(col%psi)) deallocate(col%psi, col%th)
  if (allocated(col%pc)) deallocate(col%pc, col%thc, col%fc, col%ph, col%thh, col%fh1, &
                                    col%pf, col%thf, col%fh2)
  if (allocated(col%w%psi)) deallocate(col%w%psi, col%w%th, col%w%f, col%w%cap, col%w%kk, &
                                       col%w%kf, col%w%r, col%w%ta, col%w%tb, col%w%tc, &
                                       col%w%td, col%w%thp)
  col%geo%nz = 0
  col%initialized = .false.
end subroutine


!----------------------------------------------------------------------
! 小杉式: ψ → θ, C = dθ/dψ, K(ψ ≥ 0 は飽和枝 θs・C = 0・Ks)
!   x は ln|ψ| − ln|ψm| の差で作る(ψ/ψm を先に作らない)。Q は erfc を
!   直接使う(1 − erf の差し引きをしない)
!----------------------------------------------------------------------
pure subroutine vzcol_props(geo, psi, th, cap, kk)
  type(t_vzgeo), intent(in) :: geo
  real(real64), intent(in) :: psi
  real(real64), intent(out) :: th, cap, kk
  real(real64) :: x, se, q2
  if (psi >= 0.0_real64) then
    th = geo%ths
    cap = 0.0_real64
    kk = geo%ks
    return
  end if
  x = (log(-psi) - geo%lnpm) / geo%sigma
  se = 0.5_real64 * erfc(x / sqrt2)
  q2 = 0.5_real64 * erfc((x + geo%sigma) / sqrt2)
  th = geo%thr + (geo%ths - geo%thr) * se
  kk = geo%ks * sqrt(se) * q2 * q2
  cap = (geo%ths - geo%thr) * exp(-0.5_real64 * x * x) / (geo%sigma * sqrt2pi * (-psi))
end subroutine


!----------------------------------------------------------------------
! 定常重力排水の初期条件: K(ψ0) = q0 を満たす一様な ψ0(< 0)を求める
!   自由排水の下端では一様 ψ が厳密な定常解(f = K(ψ0) が全界面で一様)。
!   K は ψ について単調増加なので u = ln|ψ| の二分法で求める。
!   ok = .false. は 0 < q0 < Ks の範囲で解が表現できないとき
!----------------------------------------------------------------------
subroutine vzcol_steady_psi(geo, q0, psi0, ok)
  type(t_vzgeo), intent(in) :: geo
  real(real64), intent(in) :: q0
  real(real64), intent(out) :: psi0
  logical, intent(out) :: ok
  real(real64) :: ulo, uhi, um, th, cap, kk
  integer :: it
  ok = .false.
  psi0 = 0.0_real64
  if (q0 <= 0.0_real64 .or. q0 >= geo%ks) return
  ! |ψ| の探索範囲 1e-8 m 〜 psi_range(K は ulo 側で Ks に、uhi 側で 0 に近づく)
  ulo = log(1.0e-8_real64)
  uhi = log(psi_range)
  call vzcol_props(geo, -exp(uhi), th, cap, kk)
  if (kk >= q0) return               ! q0 が表現範囲の乾燥側より小さい
  call vzcol_props(geo, -exp(ulo), th, cap, kk)
  if (kk <= q0) return               ! q0 が Ks に近すぎる
  do it = 1, 200
    um = 0.5_real64 * (ulo + uhi)
    if (um <= ulo .or. um >= uhi) exit
    call vzcol_props(geo, -exp(um), th, cap, kk)
    if (kk > q0) then
      ulo = um                       ! まだ湿りすぎ = |ψ| をもっと大きく
    else
      uhi = um
    end if
  end do
  psi0 = -exp(0.5_real64 * (ulo + uhi))
  ok = .true.
end subroutine


!----------------------------------------------------------------------
! 柱を区分一定の上端流束で進める
!   nseg 個の区間(長さ tlen(k) s、上端流束 rate(k) m/s)を順に進め、
!   受理した細かい枝の界面積算流束を fsum(0:nz)(m。下向き正)に足す
!   (fsum は呼び出し側がゼロにしておく)。内部刻みは区間の境界をまたがない。
!   stat /= vz_ok のとき柱の状態は失敗した区間の途中のまま(呼び出し側は
!   停止する。初版は同期区間を不可分にする = 部分的な水量を外へ渡さない)
!----------------------------------------------------------------------
subroutine vzcol_advance(col, ctl, nseg, tlen, rate, fsum, stat)
  type(t_vzcol), intent(inout) :: col
  type(t_vzctl), intent(in) :: ctl
  integer, intent(in) :: nseg
  real(real64), intent(in) :: tlen(:), rate(:)
  real(real64), intent(inout) :: fsum(0:)
  integer, intent(out) :: stat
  integer :: iseg, k, nz, it1, it2, it3, fk1, fk2, fk3
  real(real64) :: t, tend, dtry, dt, e, eth, eps, ef, sth, sps, sf, ffine, fcoarse, fmax
  logical :: cut

  stat = vz_ok
  nz = col%geo%nz
  sth = ctl%tol_th * (col%geo%ths - col%geo%thr)
  do iseg = 1, nseg
    t = 0.0_real64
    tend = tlen(iseg)
    do while (t < tend)
      dtry = min(col%dtnext, ctl%dt_max)
      ! 区間の終端に合わせる。残りが試行刻みの 1e-6 未満になる刻みは残りごと
      ! 取る(極小の端数の刻みを作らない)
      cut = (t + dtry * (1.0_real64 + 1.0e-6_real64) >= tend)
      if (cut) then
        dt = tend - t
      else
        dt = dtry
      end if
      if (.not. (dt > 0.0_real64)) exit   ! 浮動小数の端数で前進しない場合の保護

      ! --- 粗い枝(δt × 1)と細かい枝(δt/2 × 2)。同じ旧状態から ---
      fk2 = fk_none
      fk3 = fk_none
      it2 = 0
      it3 = 0
      call be_step(col%geo, ctl, col%w, col%psi, col%th, dt, rate(iseg), it1, fk1)
      if (fk1 == fk_none) then
        col%pc(:) = col%w%psi(:)
        col%thc(:) = col%w%th(:)
        col%fc(:) = col%w%f(:)
        call be_step(col%geo, ctl, col%w, col%psi, col%th, 0.5_real64 * dt, rate(iseg), it2, fk2)
        if (fk2 == fk_none) then
          col%ph(:) = col%w%psi(:)
          col%thh(:) = col%w%th(:)
          col%fh1(:) = col%w%f(:)
          call be_step(col%geo, ctl, col%w, col%ph, col%thh, 0.5_real64 * dt, rate(iseg), it3, fk3)
          if (fk3 == fk_none) then
            col%pf(:) = col%w%psi(:)
            col%thf(:) = col%w%th(:)
            col%fh2(:) = col%w%f(:)
          end if
        end if
      end if
      col%nit = col%nit + it1 + it2 + it3

      if (fk1 /= fk_none .or. fk2 /= fk_none .or. fk3 /= fk_none) then
        ! 数値的失敗: 両枝を棄却して刻みを半分に(状態は旧のまま)
        col%lastfail = max(fk1, fk2, fk3)
        col%nrej = col%nrej + 1
        col%dtnext = 0.5_real64 * dt
        if (col%dtnext < ctl%dt_min) then
          stat = vz_fail_time
          return
        end if
        cycle
      end if

      ! --- 時間誤差(状態 θ・ψ と全界面の積算流束 F) ---
      e = 0.0_real64
      do k = 1, nz
        eth = abs(col%thf(k) - col%thc(k)) / sth
        sps = ctl%tol_psi_a + ctl%tol_psi_r * max(abs(col%pf(k)), abs(col%pc(k)))
        eps = abs(col%pf(k) - col%pc(k)) / sps
        e = max(e, eth, eps)
      end do
      fmax = 0.0_real64
      do k = 0, nz
        fmax = max(fmax, abs(0.5_real64 * dt * (col%fh1(k) + col%fh2(k))), abs(dt * col%fc(k)))
      end do
      do k = 0, nz
        ffine = 0.5_real64 * dt * (col%fh1(k) + col%fh2(k))
        fcoarse = dt * col%fc(k)
        sf = ctl%tol_q_a * dt + ctl%tol_q_r * max(abs(ffine), abs(fcoarse), ctl%q_floor * fmax)
        ef = abs(ffine - fcoarse) / sf
        e = max(e, ef)
      end do
      if (e > 1.0_real64) then
        col%nrej = col%nrej + 1
        col%lastfail = fk_terr
        col%dtnext = 0.5_real64 * dt
        if (col%dtnext < ctl%dt_min) then
          stat = vz_fail_time
          return
        end if
        cycle
      end if

      ! --- 受理: 細かい枝の状態と、その 2 歩の積算流束を一組で採用 ---
      col%psi(:) = col%pf(:)
      col%th(:) = col%thf(:)
      do k = 0, nz
        fsum(k) = fsum(k) + 0.5_real64 * dt * (col%fh1(k) + col%fh2(k))
      end do
      col%nacc = col%nacc + 1
      col%dtlast = dt
      if (cut) then
        t = tend
      else
        t = t + dt
      end if
      ! 刻みの更新(時間誤差だけで決める。反復の容易さでは拡大しない。
      ! 端数に切った刻みでは試行値を保ち、切った刻みでも試行値以上なら拡大)
      if (e <= 0.2_real64 .and. dt >= dtry) then
        col%dtnext = min(dtry * ctl%grow, ctl%dt_max)
      else if (.not. cut) then
        col%dtnext = dt
      end if

      ! --- 適用範囲: 地表面の圧力の再構成(受理した解で判定) ---
      if (ponding_needed(col%geo, ctl, col%psi(1), rate(iseg))) then
        stat = vz_fail_ponding
        return
      end if
    end do
  end do
end subroutine


!======================================================================
!========================= PRIVATE ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! 地表面の圧力の再構成(vz_plan.md §5.4)
!   最上層中心(深さ a0)と地表面の間の流束 g(ψb) = K̄(ψb, ψ1)(1 − (ψ1 − ψb)/a0)
!   は ψb について単調増加で、ψb = ψ1 − a0 で 0。したがって上端流束 r を
!   非正の地表圧で受け入れられる ⇔ r ≤ g(0)。r > g(0) なら湛水が必要
!----------------------------------------------------------------------
logical function ponding_needed(geo, ctl, psi1, rtop)
  type(t_vzgeo), intent(in) :: geo
  type(t_vzctl), intent(in) :: ctl
  real(real64), intent(in) :: psi1, rtop
  real(real64) :: th1, cap1, k1, kbar, a0
  ponding_needed = .false.
  if (rtop <= 0.0_real64) return
  call vzcol_props(geo, psi1, th1, cap1, k1)
  kbar = face_mean(ctl%kface, geo%ks, k1, 0.5_real64, 0.5_real64)
  a0 = geo%zc(1)
  ponding_needed = (rtop > kbar * (1.0_real64 - psi1 / a0))
end function


!----------------------------------------------------------------------
! 界面の透水係数(上側 kup・下側 kdn、界面までの距離 a・b の重み)
!   1: 算術平均 (b·kup + a·kdn)/(a + b)(界面での線形補間)
!   2: 調和平均 (a + b)/(a/kup + b/kdn)(直列抵抗。ゼロを含めば 0)
!----------------------------------------------------------------------
pure real(real64) function face_mean(kface, kup, kdn, a, b)
  integer, intent(in) :: kface
  real(real64), intent(in) :: kup, kdn, a, b
  if (kface == 2) then
    if (kup <= 0.0_real64 .or. kdn <= 0.0_real64) then
      face_mean = 0.0_real64
    else
      face_mean = (a + b) / (a / kup + b / kdn)
    end if
  else
    face_mean = (b * kup + a * kdn) / (a + b)
  end if
end function


!----------------------------------------------------------------------
! 後退 Euler の 1 歩(修正 Picard + Thomas 法)
!   旧状態 (psi0, th0) から刻み dt・上端流束 rtop で解き、収束した ψ と
!   それに整合する θ・界面流束 f(0:nz) を w%psi・w%th・w%f に返す。
!   fk = fk_none が成功。収束: 直前の更新 |δψ|・|δθ| が非線形許容以内、
!   かつ更新後の状態の元の残差 |R_k| が局所予算 b_k 以内(小さい更新
!   だけでは受理しない)
!----------------------------------------------------------------------
subroutine be_step(geo, ctl, w, psi0, th0, dt, rtop, nit, fk)
  type(t_vzgeo), intent(in) :: geo
  type(t_vzctl), intent(in) :: ctl
  type(t_vzwork), intent(inout) :: w
  real(real64), intent(in) :: psi0(:), th0(:)
  real(real64), intent(in) :: dt, rtop
  integer, intent(out) :: nit, fk
  integer :: m, k, nz
  real(real64) :: g0, g1, bk, dpsi, tolp, tolt, rfloor, piv, gb, dthmax
  logical :: upd_ok, res_ok

  nz = geo%nz
  fk = fk_nonlin
  nit = 0
  w%psi(:) = psi0(:)
  upd_ok = .false.
  tolt = ctl%nl_factor * ctl%tol_th * (geo%ths - geo%thr)
  do m = 1, ctl%maxit
    nit = m
    ! --- 物性・流束・元の残差(現在の反復値で) ---
    do k = 1, nz
      call vzcol_props(geo, w%psi(k), w%th(k), w%cap(k), w%kk(k))
    end do
    if (m > 1) then
      ! 直前の更新による θ の変化(飽和近傍で θ が動かないことを収束の
      ! 証拠にしないよう、ψ の更新判定と併用する)
      dthmax = 0.0_real64
      do k = 1, nz
        dthmax = max(dthmax, abs(w%th(k) - w%thp(k)))
      end do
      upd_ok = upd_ok .and. (dthmax <= tolt)
    end if
    call fluxes(geo, ctl, w, rtop)
    res_ok = .true.
    do k = 1, nz
      w%r(k) = geo%dzl(k) * (w%th(k) - th0(k)) + dt * (w%f(k) - w%f(k-1))
      ! 局所予算: 柱全体の予算 mb_rate·dt を層厚で配分(丸めの下限つき)
      bk = (geo%dzl(k) / geo%depth) * ctl%mb_rate * dt
      rfloor = 64.0_real64 * epsilon(1.0_real64) * geo%dzl(k) * geo%ths
      if (.not. (abs(w%r(k)) <= max(bk, rfloor))) res_ok = .false.
    end do
    if (m > 1 .and. upd_ok .and. res_ok) then
      fk = fk_none
      return
    end if

    ! --- 三重対角系の組立(修正 Picard: K の係数は固定、貯留は C) ---
    !   −δt G_{k−1} δψ_{k−1} + [Δζ_k C_k + δt(G_{k−1} + G_k)] δψ_k − δt G_k δψ_{k+1} = −R_k
    !   上端は規定流束(G_0 = 0)、自由排水の下端は f_N を当該反復で固定(G_N = 0)
    do k = 1, nz
      if (k > 1) then
        g0 = w%kf(k-1) / geo%ell(k-1)
      else
        g0 = 0.0_real64
      end if
      if (k < nz) then
        g1 = w%kf(k) / geo%ell(k)
      else
        g1 = 0.0_real64
      end if
      w%ta(k) = -dt * g0
      w%tc(k) = -dt * g1
      w%tb(k) = geo%dzl(k) * w%cap(k) + dt * (g0 + g1)
      w%td(k) = -w%r(k)
    end do
    if (geo%bottom == 2) then
      gb = w%kf(nz) / (geo%depth - geo%zc(nz))
      w%tb(nz) = w%tb(nz) + dt * gb
    end if

    ! --- Thomas 法(前進消去・後退代入。ピボットの異常は失敗として返す) ---
    piv = w%tb(1)
    if (.not. (piv > 0.0_real64)) then
      fk = fk_linear
      return
    end if
    w%tc(1) = w%tc(1) / piv
    w%td(1) = w%td(1) / piv
    do k = 2, nz
      piv = w%tb(k) - w%ta(k) * w%tc(k-1)
      if (.not. (piv > 0.0_real64)) then
        fk = fk_linear
        return
      end if
      w%tc(k) = w%tc(k) / piv
      w%td(k) = (w%td(k) - w%ta(k) * w%td(k-1)) / piv
    end do
    do k = nz - 1, 1, -1
      w%td(k) = w%td(k) - w%tc(k) * w%td(k+1)
    end do

    ! --- 更新と更新幅の判定(減衰なし。範囲外は失敗として刻みを縮める) ---
    upd_ok = .true.
    do k = 1, nz
      dpsi = w%td(k)
      tolp = ctl%nl_factor * (ctl%tol_psi_a + ctl%tol_psi_r * max(abs(w%psi(k)), abs(w%psi(k) + dpsi)))
      if (.not. (abs(dpsi) <= tolp)) upd_ok = .false.
      w%thp(k) = w%th(k)
      w%psi(k) = w%psi(k) + dpsi
      if (.not. (abs(w%psi(k)) <= psi_range)) then
        fk = fk_range
        return
      end if
    end do
  end do
  ! 反復上限に達した(fk = fk_nonlin のまま)
end subroutine


!----------------------------------------------------------------------
! 界面流束 w%f(0:nz)(下向き正)と界面透水係数 w%kf(0:nz)
!   物性 w%kk は呼び出し側が w%psi で評価済み
!----------------------------------------------------------------------
subroutine fluxes(geo, ctl, w, rtop)
  type(t_vzgeo), intent(in) :: geo
  type(t_vzctl), intent(in) :: ctl
  type(t_vzwork), intent(inout) :: w
  real(real64), intent(in) :: rtop
  integer :: j, nz
  real(real64) :: a, b
  nz = geo%nz
  w%f(0) = rtop
  w%kf(0) = 0.0_real64
  do j = 1, nz - 1
    a = geo%zf(j) - geo%zc(j)          ! 上側の層中心から界面まで
    b = geo%zc(j+1) - geo%zf(j)        ! 界面から下側の層中心まで
    w%kf(j) = face_mean(ctl%kface, w%kk(j), w%kk(j+1), a, b)
    w%f(j) = w%kf(j) * (1.0_real64 - (w%psi(j+1) - w%psi(j)) / geo%ell(j))
  end do
  if (geo%bottom == 2) then
    ! 固定圧(検証用): 層中心と下端面の半格子で ψ_b を既知項にする
    w%kf(nz) = face_mean(ctl%kface, w%kk(nz), geo%kbot, 0.5_real64, 0.5_real64)
    w%f(nz) = w%kf(nz) * (1.0_real64 - (geo%psibot - w%psi(nz)) / (geo%depth - geo%zc(nz)))
  else
    ! 自由排水(単位動水勾配): f_N = K(ψ_N)
    w%kf(nz) = w%kk(nz)
    w%f(nz) = w%kk(nz)
  end if
end subroutine

end module
