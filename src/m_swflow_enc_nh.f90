!======================================================================
! 非静水圧(1 層 NH)補正(m_swflow_enc の submodule)
!
!   設計の正本は docs/nonhydrostatic_plan.md(§5 推奨方式、§6 活性集合)、
!   決定の記録は developer.md §69。要点:
!
!   - 現行の静水圧ステップ(momentum: 適応 RK・保存形移流・摩擦・堤防・
!     構造物 → par_edge_merge → boundary_uvmn)を predictor とし、その
!     直後(continuous の前)に 1 回だけ補正する(fractional step)。
!   - 静水圧の全加速度 a*_e = (u*_e − u^n_e)/Δt に対し、1 層 NH を
!         (I − β G D) a = a*,   β_i = (h_i^n)² / 4
!     とみなす。セルスカラー φ_i = β_i (D a)_i を導入すると
!         φ_i − β_i Σ_k w_k (φ_{n_k} − φ_i) = β_i (D a*)_i
!     (w_k = l8(k)/(A·w8dr(k))、和は NH エッジ)で、これを反復で解き
!         u^{n+1}_e = u*_e + Δt (φ_n − φ_c)/w8dr(k),  mn1_e = u^{n+1}_e · he
!     と NH エッジを補正する。he は momentum が面流束に使ったエッジ水深
!     (nh_he)。両セルが同じ mn1 を見るので質量保存は現行どおり厳密。
!   - 線形(1 次元・平坦床)では ω² = gHΛ/(1 + βΛ)(1 層 Keller-box 型)
!     を半離散で厳密に再現する。補正は加速度に 0 < P ≤ 1 のフィルタを
!     掛けるだけなので新しい速い波を生まず CFL は変わらない。
!   - NH セル: x>0・sw=0・h ≥ nh_hmin・gv=1・幅河道外・σ 非適用。
!     NH エッジ: 両セルが NH かつ 堤防壁・skip8 でない。マスク外は
!     φ = 0(Dirichlet)で補正しない(静水圧に退化)。
!   - ソルバ: 1 Jacobi(二重バッファ・毎掃引 halo 交換・残差最大の
!     allreduce)、2 CG(対称形 (1/β)φ + Lφ = Da*。内積は行部分和 →
!     par_sum_rows の決定的総和)。いずれもスレッド数・ランク数に依らず
!     ビット一致する。反復回数は全ランク同一(collective を同じ回数)。
!   - NH OFF(f_nonhydrostatic=0)では配列を確保せず、何も呼ばない
!     (メモリ・CPU・通信ゼロ追加 = 既存 reference とビット一致)。
!   - リスタート状態なし(φ はステップ内の診断量。cold start)。
!======================================================================
submodule(m_swflow_enc) m_swflow_enc_nh
  use m_state, only : t_state
  use m_parallel, only : dcp, par_halo_cell, par_edge_merge, par_allreduce_max, &
                         par_allreduce_sumi, par_sum_rows, par_info, par_warn, par_stop
  use m_util, only : itoa
  use, intrinsic :: iso_fortran_env, only : real64
  implicit none

  type t_enc_nh
    real, allocatable :: uv0(:,:,:)       ! ステップ頭のエッジ流速 u^n (1:4, 0:nx, jsh-1:jeh)
    real, allocatable :: phi(:,:)         ! NH ポテンシャル φ (1:nx, jsh:jeh)
    real, allocatable :: phi1(:,:)        ! Jacobi の書き込み先 / CG の方向ベクトル p
    real, allocatable :: rhs(:,:)         ! Jacobi: β D a*、CG: D a*
    real, allocatable :: beta(:,:)        ! h²/4(NH セル以外 0)
    real, allocatable :: diag(:,:)        ! Jacobi: 1 + β Σ w、CG: 1/β + Σ w
    real, allocatable :: rr(:,:)          ! CG 残差
    real, allocatable :: ap(:,:)          ! CG の M p
    real, allocatable :: dast(:,:)        ! D a*(NH 候補セル。検出と右辺に使う)
    real, allocatable :: work(:,:)        ! 活性集合の膨張用(0/1。halo 交換のため実数)
    integer, allocatable :: cmask(:,:)    ! NH セル (1:nx, jsh:jeh)
    logical, allocatable :: emask(:,:,:)  ! NH エッジ (1:4, 0:nx, jsh-1:jeh)
    real :: wd(1:8) = 0.0                 ! 発散の重み l8(k)/(dx·dy)
    real :: wl(1:8) = 0.0                 ! ラプラシアンの重み l8(k)/(dx·dy·w8dr(k))
    ! 統計(dispose で表示)
    integer :: nstep = 0
    integer(8) :: itsum = 0
    integer :: itmax_seen = 0
    integer(8) :: actsum = 0              ! 活性セル数の累計(ランク局所)
    integer :: nfail = 0                  ! 不収束のステップ数
  end type
  type(t_enc_nh) :: nh_mod

  ! 8 近傍番号 → エッジ成分・符号(continuous と同じ規約)
  integer, parameter :: ke8(1:8) = [ 1, 2, 3, 4, 4, 3, 2, 1 ]
  real, parameter :: sgn8(1:8) = [ 1., 1., 1., 1., -1., -1., -1., -1. ]

contains

!----------------------------------------------------------------------
! 初期化: パラメータ検査と NH ON 時だけの確保
!----------------------------------------------------------------------
module subroutine nh_init(p, g, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer :: k

  nh_active = (f_nonhydrostatic > 0)
  if (.not. nh_active) return

  if (f_nonhydrostatic /= 1) call par_stop("list_enc: f_nonhydrostatic must be 0(off) or 1(1-layer)")
  if (s%debris_active) call par_stop("list_enc: f_nonhydrostatic cannot be combined with debris flow")
  if (nh_hmin <= p%dd) call par_stop("list_enc: nh_hmin must exceed dd (moving depth threshold)")
  select case (nh_solver)
    case (1)
      call par_info("swflow_enc: non-hydrostatic correction ON (1-layer, beta=h^2/4), solver=Jacobi")
    case (2)
      call par_info("swflow_enc: non-hydrostatic correction ON (1-layer, beta=h^2/4), solver=CG")
    case default
      call par_stop("list_enc: nh_solver must be 1(Jacobi) or 2(CG)")
  end select
  if (nh_itmax < 1) call par_stop("list_enc: nh_itmax must be >= 1")
  if (nh_tol <= 0.0) call par_stop("list_enc: nh_tol must be > 0")
  call par_info("  nh_hmin = "//trim(rtoa(nh_hmin))//" m, nh_itmax = "//itoa(nh_itmax)// &
                ", nh_tol = "//trim(rtoa(nh_tol)))
  select case (f_nh_adaptive)
    case (0)
    case (1)
      select case (nh_detector)
        case (1)
          call par_info("  adaptive active set: detector = dispersion chi = |bDa*|/(|a*|+|bDa*|), chi_on = " &
                        //trim(rtoa(nh_chi_on)))
        case (2)
          call par_info("  adaptive active set: detector = |bDa*|/g, chi_on = "//trim(rtoa(nh_chi_on)))
        case default
          call par_stop("list_enc: nh_detector must be 1(dispersion chi) or 2(absolute)")
      end select
      if (nh_chi_on <= 0.0) call par_stop("list_enc: nh_chi_on must be > 0")
      if (nh_amin < 0.0) call par_stop("list_enc: nh_amin must be >= 0")
      if (nh_arel < 0.0 .or. nh_arel >= 1.0) call par_stop("list_enc: nh_arel must be in [0, 1)")
      call par_info("  seed floor |bDa*| >= max("//trim(rtoa(nh_amin))//" m/s2, "// &
                    trim(rtoa(nh_arel))//" x domain max)")
      if (nh_margin > 0) then
        call par_info("  margin = "//itoa(nh_margin)//" cells")
      else
        call par_info("  margin = automatic (2H/dx)")
      end if
    case default
      call par_stop("list_enc: f_nh_adaptive must be 0(whole mask) or 1(active set)")
  end select

  allocate(nh_mod%uv0(1:4, 0:g%nx, dcp%jsh-1:dcp%jeh), source = 0.0)
  allocate(nh_he(1:4, 0:g%nx, dcp%jsh-1:dcp%jeh), source = 0.0)
  allocate(nh_mod%phi(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(nh_mod%phi1(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(nh_mod%rhs(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(nh_mod%beta(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(nh_mod%diag(1:g%nx, dcp%jsh:dcp%jeh), source = 1.0)
  allocate(nh_mod%cmask(1:g%nx, dcp%jsh:dcp%jeh), source = 0)
  allocate(nh_mod%dast(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  if (f_nh_adaptive == 1) allocate(nh_mod%work(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(nh_mod%emask(1:4, 0:g%nx, dcp%jsh-1:dcp%jeh), source = .false.)
  if (nh_solver == 2) then
    allocate(nh_mod%rr(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
    allocate(nh_mod%ap(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  end if
  do k = 1, 8
    nh_mod%wd(k) = l8(k) / (g%dx * g%dy)
    nh_mod%wl(k) = l8(k) / (g%dx * g%dy * w8dr(k))
  end do
  nh_mod%nstep = 0
  nh_mod%itsum = 0
  nh_mod%itmax_seen = 0
  nh_mod%actsum = 0
  nh_mod%nfail = 0

contains
  function rtoa(x) result(str)
    real, intent(in) :: x
    character(len=16) :: str
    write(str, '(es10.3)') x
    str = adjustl(str)
  end function
end subroutine


!----------------------------------------------------------------------
! ステップ頭: u^n の複製(uv は momentum が上書きする単一バッファ。§7)
!----------------------------------------------------------------------
module subroutine nh_prepare(sx)
  type(t_enc_status), intent(in) :: sx
  integer :: j
  !$omp parallel do schedule(static) private(j)
  do j = dcp%jsh-1, dcp%jeh
    nh_mod%uv0(:,:,j) = sx%uv(:,:,j)
  end do
  !$omp end parallel do
end subroutine


!----------------------------------------------------------------------
! NH 補正(boundary_uvmn の後、continuous の前)
!----------------------------------------------------------------------
module subroutine nh_project(p, g, s, sx)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  type(t_enc_status), intent(inout) :: sx
  integer :: i, j, k, kk, in, jn, ie, je
  integer :: nact, iters
  real :: da, wsum, dtinv
  real :: phic, phin
  logical :: ok

  dtinv = 1.0 / p%dt

  ! --- 1. NH 候補セルのマスクと β(確保範囲 jsh..jeh で局所に決まる) ---
  !$omp parallel do schedule(static) private(i, j)
  do j = dcp%jsh, dcp%jeh
    do i = 1, g%nx
      nh_mod%cmask(i,j) = 0
      nh_mod%beta(i,j) = 0.0
      nh_mod%phi(i,j) = 0.0
      nh_mod%phi1(i,j) = 0.0
      nh_mod%rhs(i,j) = 0.0
      nh_mod%dast(i,j) = 0.0
      nh_mod%diag(i,j) = 1.0
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      if (s%h(i,j) < nh_hmin) cycle
      if (s%gv(i,j) < 1.0) cycle
      if (have_width) then
        if (wfrac(i,j) < 1.0) cycle
      end if
      if (have_sect) then
        if (sdep(i,j) > 0.0) cycle
      end if
      nh_mod%cmask(i,j) = 1
      nh_mod%beta(i,j) = s%h(i,j)**2 / 4
    end do
  end do
  !$omp end parallel do

  ! --- 2. 静水圧加速度の発散 D a*(担当帯。エッジ行 js-1..je は merge 済み) ---
  !   全 8 エッジの寄与(非 NH エッジも含む。momentum が触らなかったエッジは
  !   uv = uv0 で寄与 0)
  !$omp parallel do schedule(static) private(i, j, kk, da)
  do j = dcp%js, dcp%je
    do i = 1, g%nx
      if (nh_mod%cmask(i,j) == 0) cycle
      da = 0.0
      do kk = 1, 8
        da = da + sgn8(kk) * (sx%uv(ke8(kk), i+die(kk), j+dje(kk)) &
                              - nh_mod%uv0(ke8(kk), i+die(kk), j+dje(kk))) * dtinv * nh_mod%wd(kk)
      end do
      nh_mod%dast(i,j) = da
    end do
  end do
  !$omp end parallel do

  ! --- 2b. 活性集合(f_nh_adaptive=1): 検出セル + 縁だけを NH セルに絞る ---
  if (f_nh_adaptive == 1) call active_set(p, g, s, sx)

  ! --- 3. NH エッジ(基準セル jsh..jeh の k=1..4。両セルが NH、壁でない) ---
  !$omp parallel do schedule(static) private(i, j, k, in, jn, ie, je)
  do j = dcp%jsh, dcp%jeh
    do i = 1, g%nx
      do k = 1, 4
        ie = i + die(k)
        je = j + dje(k)
        nh_mod%emask(k,ie,je) = .false.
        if (nh_mod%cmask(i,j) == 0) cycle
        if (skip8(k)) cycle
        in = i + din(k)
        jn = j + djn(k)
        if (in < 1 .or. in > g%nx) cycle
        if (jn < dcp%jsh .or. jn > dcp%jeh) cycle
        if (nh_mod%cmask(in,jn) == 0) cycle
        if (have_bank) then
          if (bank_edge(g, s, i, j, in, jn)) cycle
        end if
        nh_mod%emask(k,ie,je) = .true.
      end do
    end do
  end do
  !$omp end parallel do

  ! --- 3b. 右辺と対角(担当帯 js..je) ---
  nact = 0
  !$omp parallel do schedule(static) private(i, j, kk, wsum) reduction(+:nact)
  do j = dcp%js, dcp%je
    do i = 1, g%nx
      if (nh_mod%cmask(i,j) == 0) cycle
      nact = nact + 1
      wsum = 0.0
      do kk = 1, 8
        if (nh_mod%emask(ke8(kk), i+die(kk), j+dje(kk))) wsum = wsum + nh_mod%wl(kk)
      end do
      if (nh_solver == 1) then
        nh_mod%rhs(i,j) = nh_mod%beta(i,j) * nh_mod%dast(i,j)
        nh_mod%diag(i,j) = 1.0 + nh_mod%beta(i,j) * wsum
      else
        nh_mod%rhs(i,j) = nh_mod%dast(i,j)
        nh_mod%diag(i,j) = 1.0 / nh_mod%beta(i,j) + wsum
      end if
    end do
  end do
  !$omp end parallel do

  ! --- 4. 反復解 ---
  if (nh_solver == 1) then
    call solve_jacobi(g, iters, ok)
  else
    call solve_cg(g, iters, ok)
  end if
  nh_mod%nstep = nh_mod%nstep + 1
  nh_mod%itsum = nh_mod%itsum + iters
  nh_mod%itmax_seen = max(nh_mod%itmax_seen, iters)
  nh_mod%actsum = nh_mod%actsum + nact
  if (.not. ok) nh_mod%nfail = nh_mod%nfail + 1

  ! --- 5. エッジ流速・流量の補正(基準セル js..je の k=1..4。界面行は merge) ---
  call par_halo_cell(nh_mod%phi)
  !$omp parallel do schedule(static) private(i, j, k, in, jn, ie, je, phic, phin)
  do j = dcp%js, dcp%je
    do i = 1, g%nx
      if (nh_mod%cmask(i,j) == 0) cycle
      phic = nh_mod%phi(i,j)
      do k = 1, 4
        ie = i + die(k)
        je = j + dje(k)
        if (.not. nh_mod%emask(k,ie,je)) cycle
        in = i + din(k)
        jn = j + djn(k)
        phin = nh_mod%phi(in,jn)
        sx%uv(k,ie,je) = sx%uv(k,ie,je) + p%dt * (phin - phic) / w8dr(k)
        sx%mn1(k,ie,je) = sx%uv(k,ie,je) * nh_he(k,ie,je)
      end do
    end do
  end do
  !$omp end parallel do
  call par_edge_merge(sx%uv,  esync_s, esync_n)
  call par_edge_merge(sx%mn1, esync_s, esync_n)

end subroutine


!----------------------------------------------------------------------
! 活性集合(plan §6): 検出量が閾値を超えるセルを種にし、8 近傍で
!   nh_margin セルぶん膨張させた集合だけを NH セルに残す(残りは φ = 0 の
!   静水圧)。楕円型作用素の影響距離は H/2 で減衰するので、縁を 2H
!   程度取れば切り捨て誤差は exp(−2·縁幅/H) ≈ 2% 以下。
!   検出量 1(分散型): χ = |β D a*| / (ā* + |β D a*| + ε)、ā* は 8 エッジの
!     |a*| の RMS。長波では χ ≈ (kH)²/4 で振幅に依らない。
!   検出量 2(絶対型): |β D a*| / g。
!   膨張は 8 近傍の論理和(走査順に依らない)。各掃引で halo 交換するので
!   ランク境界で連結が切れない。ステップ間の状態は持たない(stateless)。
!----------------------------------------------------------------------
subroutine active_set(p, g, s, sx)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  type(t_enc_status), intent(in) :: sx
  integer :: i, j, kk, m, margin
  real :: bda, a2, chi, dtinv, hmax, bmax, floor
  real :: vmax(2)
  real, parameter :: eps = 1.0e-30

  dtinv = 1.0 / p%dt

  ! 下限: 絶対値 nh_amin と、そのステップの領域最大 |βDa*| の nh_arel 倍
  !   (比の検出量 χ は振幅に依らないため、陽解法の前駆ノイズ(丸め誤差
  !   レベルの短波)まで拾ってしまう。補正量が無視できるセルを種から外す)
  hmax = 0.0
  bmax = 0.0
  !$omp parallel do schedule(static) private(i, j) reduction(max:hmax, bmax)
  do j = dcp%js, dcp%je
    do i = 1, g%nx
      if (nh_mod%cmask(i,j) == 0) cycle
      hmax = max(hmax, s%h(i,j))
      bmax = max(bmax, abs(nh_mod%beta(i,j) * nh_mod%dast(i,j)))
    end do
  end do
  !$omp end parallel do
  vmax(1) = hmax
  vmax(2) = bmax
  call par_allreduce_max(vmax)
  hmax = vmax(1)
  floor = max(nh_amin, nh_arel * vmax(2))

  ! 種: 検出量 > nh_chi_on(担当帯。候補セルのみ)
  !$omp parallel do schedule(static) private(i, j, kk, bda, a2, chi)
  do j = dcp%js, dcp%je
    do i = 1, g%nx
      nh_mod%work(i,j) = 0.0
      if (nh_mod%cmask(i,j) == 0) cycle
      bda = abs(nh_mod%beta(i,j) * nh_mod%dast(i,j))
      if (bda < floor) cycle
      if (nh_detector == 1) then
        a2 = 0.0
        do kk = 1, 8
          a2 = a2 + ((sx%uv(ke8(kk), i+die(kk), j+dje(kk)) &
                      - nh_mod%uv0(ke8(kk), i+die(kk), j+dje(kk))) * dtinv)**2
        end do
        chi = bda / (sqrt(a2 / 8) + bda + eps)
      else
        chi = bda / p%gg
      end if
      if (chi > nh_chi_on) nh_mod%work(i,j) = 1.0
    end do
  end do
  !$omp end parallel do

  ! 縁の幅(自動なら 2H/Δx。hmax は全ランクで集約済み)
  if (nh_margin > 0) then
    margin = nh_margin
  else
    margin = max(2, ceiling(2.0 * hmax / min(g%dx, g%dy)))
  end if

  ! 膨張(各掃引: halo 交換 → 8 近傍の論理和。候補セルの中だけに広がる)
  do m = 1, margin
    call par_halo_cell(nh_mod%work)
    !$omp parallel do schedule(static) private(i, j, kk)
    do j = dcp%js, dcp%je
      do i = 1, g%nx
        nh_mod%phi1(i,j) = 0.0
        if (nh_mod%cmask(i,j) == 0) cycle
        if (nh_mod%work(i,j) > 0.5) then
          nh_mod%phi1(i,j) = 1.0
          cycle
        end if
        do kk = 1, 8
          if (i+din(kk) < 1 .or. i+din(kk) > g%nx) cycle
          if (nh_mod%work(i+din(kk), j+djn(kk)) > 0.5) then
            nh_mod%phi1(i,j) = 1.0
            exit
          end if
        end do
      end do
    end do
    !$omp end parallel do
    !$omp parallel do schedule(static) private(j)
    do j = dcp%js, dcp%je
      nh_mod%work(:,j) = nh_mod%phi1(:,j)
      nh_mod%phi1(:,j) = 0.0
    end do
    !$omp end parallel do
  end do
  call par_halo_cell(nh_mod%work)

  ! 候補セル ∧ 活性 → NH セル(ハロ行も交換済みの値で同じ判定)
  !$omp parallel do schedule(static) private(i, j)
  do j = dcp%jsh, dcp%jeh
    do i = 1, g%nx
      if (nh_mod%cmask(i,j) == 1 .and. nh_mod%work(i,j) < 0.5) then
        nh_mod%cmask(i,j) = 0
        nh_mod%beta(i,j) = 0.0
      end if
    end do
  end do
  !$omp end parallel do
end subroutine


!----------------------------------------------------------------------
! Jacobi 反復: φ_new = (rhs + β Σ_k w_k φ_n) / diag(NH セルのみ)
!   収束判定は残差 |diag·(φ_new − φ)| の最大(allreduce。max は順序不変)
!   が nh_tol × max|rhs| 以下。全ランクが同じ回数だけ halo と allreduce を
!   呼ぶ(collective 規律 §5)
!----------------------------------------------------------------------
subroutine solve_jacobi(g, iters, ok)
  type(t_geoinfo), intent(in) :: g
  integer, intent(out) :: iters
  logical, intent(out) :: ok
  integer :: i, j, kk, it
  real :: rsum, resmax, rhsmax, pnew
  real :: vmax(1)

  rhsmax = 0.0
  !$omp parallel do schedule(static) private(i, j) reduction(max:rhsmax)
  do j = dcp%js, dcp%je
    do i = 1, g%nx
      rhsmax = max(rhsmax, abs(nh_mod%rhs(i,j)))
    end do
  end do
  !$omp end parallel do
  vmax(1) = rhsmax
  call par_allreduce_max(vmax)
  rhsmax = vmax(1)
  ok = .true.
  iters = 0
  if (rhsmax <= 0.0) return        ! 補正の源がない(静止水など)

  do it = 1, nh_itmax
    call par_halo_cell(nh_mod%phi)
    resmax = 0.0
    !$omp parallel do schedule(static) private(i, j, kk, rsum, pnew) reduction(max:resmax)
    do j = dcp%js, dcp%je
      do i = 1, g%nx
        if (nh_mod%cmask(i,j) == 0) cycle
        rsum = 0.0
        do kk = 1, 8
          if (nh_mod%emask(ke8(kk), i+die(kk), j+dje(kk))) then
            rsum = rsum + nh_mod%wl(kk) * nh_mod%phi(i+din(kk), j+djn(kk))
          end if
        end do
        pnew = (nh_mod%rhs(i,j) + nh_mod%beta(i,j) * rsum) / nh_mod%diag(i,j)
        resmax = max(resmax, abs(nh_mod%diag(i,j) * (pnew - nh_mod%phi(i,j))))
        nh_mod%phi1(i,j) = pnew
      end do
    end do
    !$omp end parallel do
    ! 担当帯の値を φ へ(非 NH セルは 0 のまま。ハロ行は次の交換で更新)
    !$omp parallel do schedule(static) private(j)
    do j = dcp%js, dcp%je
      nh_mod%phi(:,j) = nh_mod%phi1(:,j)
    end do
    !$omp end parallel do
    iters = it
    vmax(1) = resmax
    call par_allreduce_max(vmax)
    if (vmax(1) <= nh_tol * rhsmax) return
  end do
  ok = .false.
  call par_warn("swflow_enc_nh: Jacobi did not converge in "//itoa(nh_itmax)//" sweeps")
end subroutine


!----------------------------------------------------------------------
! CG: M φ = b、M = diag(1/β) + L(L は NH エッジの重み w の graph Laplacian。
!   対称正定値)。内積は行部分和 → par_sum_rows(決定的総和)。
!   収束判定は ||r|| ≤ nh_tol·||b||
!----------------------------------------------------------------------
subroutine solve_cg(g, iters, ok)
  type(t_geoinfo), intent(in) :: g
  integer, intent(out) :: iters
  logical, intent(out) :: ok
  integer :: i, j, kk, it
  real(real64) :: bb, rr0, rr1, pap, alpha, bet
  real :: lsum

  ! x = φ = 0, r = b, p = r
  !$omp parallel do schedule(static) private(j)
  do j = dcp%jsh, dcp%jeh
    nh_mod%rr(:,j) = nh_mod%rhs(:,j)
    nh_mod%phi1(:,j) = nh_mod%rhs(:,j)
    nh_mod%ap(:,j) = 0.0
  end do
  !$omp end parallel do
  bb = dot(nh_mod%rr, nh_mod%rr)
  ok = .true.
  iters = 0
  if (bb <= 0.0_real64) return
  rr0 = bb

  do it = 1, nh_itmax
    call par_halo_cell(nh_mod%phi1)
    !$omp parallel do schedule(static) private(i, j, kk, lsum)
    do j = dcp%js, dcp%je
      do i = 1, g%nx
        if (nh_mod%cmask(i,j) == 0) cycle
        lsum = 0.0
        do kk = 1, 8
          if (nh_mod%emask(ke8(kk), i+die(kk), j+dje(kk))) then
            lsum = lsum + nh_mod%wl(kk) * nh_mod%phi1(i+din(kk), j+djn(kk))
          end if
        end do
        nh_mod%ap(i,j) = nh_mod%diag(i,j) * nh_mod%phi1(i,j) - lsum
      end do
    end do
    !$omp end parallel do
    pap = dot(nh_mod%phi1, nh_mod%ap)
    if (pap <= 0.0_real64) exit
    alpha = rr0 / pap
    !$omp parallel do schedule(static) private(i, j)
    do j = dcp%js, dcp%je
      do i = 1, g%nx
        if (nh_mod%cmask(i,j) == 0) cycle
        nh_mod%phi(i,j) = nh_mod%phi(i,j) + real(alpha) * nh_mod%phi1(i,j)
        nh_mod%rr(i,j) = nh_mod%rr(i,j) - real(alpha) * nh_mod%ap(i,j)
      end do
    end do
    !$omp end parallel do
    rr1 = dot(nh_mod%rr, nh_mod%rr)
    iters = it
    if (sqrt(rr1) <= nh_tol * sqrt(bb)) return
    bet = rr1 / rr0
    rr0 = rr1
    !$omp parallel do schedule(static) private(i, j)
    do j = dcp%js, dcp%je
      do i = 1, g%nx
        if (nh_mod%cmask(i,j) == 0) cycle
        nh_mod%phi1(i,j) = nh_mod%rr(i,j) + real(bet) * nh_mod%phi1(i,j)
      end do
    end do
    !$omp end parallel do
  end do
  ok = .false.
  call par_warn("swflow_enc_nh: CG did not converge in "//itoa(nh_itmax)//" iterations")

contains
  ! 決定的内積: 行ごとの部分和(行内は逐次)→ par_sum_rows
  function dot(a, b) result(tot)
    real, intent(in) :: a(1:, dcp%jsh:), b(1:, dcp%jsh:)
    real(real64) :: tot
    real(real64) :: rowsum(dcp%js:dcp%je)
    integer :: i, j
    !$omp parallel do schedule(static) private(i, j)
    do j = dcp%js, dcp%je
      rowsum(j) = 0.0_real64
      do i = 1, g%nx
        rowsum(j) = rowsum(j) + real(a(i,j), real64) * real(b(i,j), real64)
      end do
    end do
    !$omp end parallel do
    call par_sum_rows(rowsum, tot)
  end function
end subroutine


!----------------------------------------------------------------------
! 終了処理: 統計の表示と解放
!----------------------------------------------------------------------
module subroutine nh_dispose()
  integer :: ivals(2)
  if (.not. nh_active) return
  if (nh_mod%nstep > 0) then
    ivals(1) = int(min(nh_mod%actsum, int(huge(1), 8)))
    ivals(2) = nh_mod%nfail
    call par_allreduce_sumi(ivals(1:1))
    call par_info("swflow_enc_nh: steps "//itoa(nh_mod%nstep)// &
                  ", iterations avg "//itoa(int(nh_mod%itsum / nh_mod%nstep))// &
                  " max "//itoa(nh_mod%itmax_seen)// &
                  ", active cells avg "//itoa(ivals(1) / nh_mod%nstep)// &
                  ", not converged "//itoa(ivals(2)))
  end if
  if (allocated(nh_mod%uv0)) deallocate(nh_mod%uv0)
  if (allocated(nh_he)) deallocate(nh_he)
  if (allocated(nh_mod%phi)) deallocate(nh_mod%phi)
  if (allocated(nh_mod%phi1)) deallocate(nh_mod%phi1)
  if (allocated(nh_mod%rhs)) deallocate(nh_mod%rhs)
  if (allocated(nh_mod%beta)) deallocate(nh_mod%beta)
  if (allocated(nh_mod%diag)) deallocate(nh_mod%diag)
  if (allocated(nh_mod%rr)) deallocate(nh_mod%rr)
  if (allocated(nh_mod%ap)) deallocate(nh_mod%ap)
  if (allocated(nh_mod%cmask)) deallocate(nh_mod%cmask)
  if (allocated(nh_mod%dast)) deallocate(nh_mod%dast)
  if (allocated(nh_mod%work)) deallocate(nh_mod%work)
  if (allocated(nh_mod%emask)) deallocate(nh_mod%emask)
  nh_active = .false.
end subroutine

end submodule
