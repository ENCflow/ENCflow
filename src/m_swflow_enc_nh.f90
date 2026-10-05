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
!   - 底面勾配項(f_nh_slope=1。Version 2): 鉛直速度に底面の運動学条件
!     w_b = u·∇z_b を加え、圧力項に (φ/h)∇(h + 2z_b) を含める。
!         φ_i = (h_i/4) Σ_k wd_k (h_i − Δz_k) a_k^out
!         a_e = a*_e + (φ_n − φ_c)/d + (φ_c + φ_n)·σ_e,  σ_e = Δ(h+2z)/(2 h_e d)
!     (8 方向の重み Σ_k l8 d_k n_k n_kᵀ/(2A) = I により a·∇z_b を離散化)。
!     作用素が非対称になるため、CG は平坦部分を解き勾配項を Picard 反復で
!     回す(warm start)。Jacobi は全項をそのまま回す。f_nh_slope=0 では
!     Version 1 と演算が同一。
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
    real, allocatable :: rhs(:,:)         ! Jacobi: β D a*、CG: D a*(Version 2 では Picard ごとに更新)
    real, allocatable :: rhs0(:,:)        ! Version 2: Σ_k c_k a*_k(勾配項つきの右辺の a* 部分)
    real, allocatable :: work2(:,:)       ! Version 2: Picard の前回の φ
    real, allocatable :: beta(:,:)        ! h²/4(NH セル以外 0)
    real, allocatable :: diag(:,:)        ! Jacobi: 1 + β Σ w、CG: 1/β + Σ w
    real, allocatable :: rr(:,:)          ! CG 残差
    real, allocatable :: ap(:,:)          ! CG の M p
    real, allocatable :: dast(:,:)        ! D a*(NH 候補セル。検出と右辺に使う)
    real, allocatable :: work(:,:)        ! 活性集合の膨張用(0/1。halo 交換のため実数)
    real, allocatable :: brk(:,:)         ! 砕波セル(0/1。halo 交換のため実数)
    integer, allocatable :: cmask(:,:)    ! NH セル (1:nx, jsh:jeh)
    logical, allocatable :: emask(:,:,:)  ! NH エッジ (1:4, 0:nx, jsh-1:jeh)
    real :: wd(1:8) = 0.0                 ! 発散の重み l8(k)/(dx·dy)
    real :: wl(1:8) = 0.0                 ! ラプラシアンの重み l8(k)/(dx·dy·w8dr(k))
    ! 統計(dispose で表示)
    integer :: nstep = 0
    integer(8) :: itsum = 0
    integer :: itmax_seen = 0
    integer(8) :: actsum = 0              ! 活性セル数の累計(ランク局所)
    integer(8) :: brksum = 0              ! 砕波セル数の累計(ランク局所)
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
  select case (f_nh_slope)
    case (0)
    case (1)
      call par_info("  bottom-slope terms ON (Version 2: w_b = u.grad z_b, (phi/h) grad(h + 2 z_b))")
    case default
      call par_stop("list_enc: f_nh_slope must be 0(flat, Version 1) or 1(bottom-slope terms)")
  end select
  select case (f_nh_breaking)
    case (0)
    case (1)
      select case (nh_break_type)
        case (1)
          if (nh_break_alpha <= 0.0 .or. nh_break_beta <= 0.0 .or. nh_break_beta > nh_break_alpha) then
            call par_stop("list_enc: nh_break_alpha > nh_break_beta > 0 is required")
          end if
          call par_info("  breaking switch: hydrostatic where d(eta)/dt > alpha sqrt(gh), alpha = " &
                        //trim(rtoa(nh_break_alpha))//", beta = "//trim(rtoa(nh_break_beta)))
        case (2)
          if (nh_break_fr <= 0.0) call par_stop("list_enc: nh_break_fr must be > 0")
      if (nh_break_margin < 0) call par_stop("list_enc: nh_break_margin must be >= 0")
          call par_info("  breaking switch: hydrostatic where Froude number |V|/sqrt(gh) > " &
                        //trim(rtoa(nh_break_fr)))
        case (3)
          if (nh_break_slope <= 0.0) call par_stop("list_enc: nh_break_slope must be > 0")
          call par_info("  breaking switch: hydrostatic where surface slope |grad eta| > " &
                        //trim(rtoa(nh_break_slope)))
        case default
          call par_stop("list_enc: nh_break_type must be 1(d(eta)/dt), 2(Froude) or 3(surface slope)")
      end select
      if (nh_break_visc > 0.0) then
        if (nh_break_slope <= 0.0) call par_stop("list_enc: nh_break_visc > 0 requires nh_break_slope > 0 (ramp reference)")
        call par_info("  breaking eddy viscosity: nu_b = "//trim(rtoa(nh_break_visc)) &
                      //" B h sqrt(gh) |grad eta| in breaking cells (B ramps over |grad eta| = " &
                      //trim(rtoa(nh_break_slope))//" .. "//trim(rtoa(2.0 * nh_break_slope))//")")
      end if
    case default
      call par_stop("list_enc: f_nh_breaking must be 0(off) or 1(on)")
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
  if (f_nh_breaking == 1) allocate(nh_mod%brk(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  if (nh_break_visc > 0.0) allocate(nh_nub(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  if (f_nh_slope == 1) then
    allocate(nh_mod%rhs0(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
    allocate(nh_mod%work2(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  end if
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
  nh_mod%brksum = 0
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
  integer :: nact, iters, m, it2
  real :: da, wsum, dtinv, r0, ck, sig, ae, rr, dphimax, phimax
  real :: phic, phin
  real :: vmax2(2)
  logical :: ok, ok2

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

  ! --- 1b. 砕波スイッチ(f_nh_breaking=1): 水面が速く上昇するセルを静水圧に ---
  if (f_nh_breaking == 1) call breaking_switch(p, g, s, sx)

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
  !   Version 1: rhs = β D a*(Jacobi)/ D a*(CG)、diag = 1 + β Σ w / 1/β + Σ w。
  !   Version 2(f_nh_slope=1): rhs0 = Σ_k c_k a*_k(c_k = (h/4) wd_k (h − Δz_k))を
  !   Jacobi の右辺、diag = 1 + Σ_NH c_k (1/d_k − σ_k)。CG は平坦部分の
  !   diag のまま、勾配項を Picard で右辺に回す(4. を参照)
  nact = 0
  !$omp parallel do schedule(static) private(i, j, kk, wsum, r0, ck, sig, ae) reduction(+:nact)
  do j = dcp%js, dcp%je
    do i = 1, g%nx
      if (nh_mod%cmask(i,j) == 0) cycle
      nact = nact + 1
      wsum = 0.0
      if (f_nh_slope == 0) then
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
      else
        r0 = 0.0
        do kk = 1, 8
          call slope_coef(g, s, i, j, kk, ck, sig)
          ae = sgn8(kk) * (sx%uv(ke8(kk), i+die(kk), j+dje(kk)) &
                           - nh_mod%uv0(ke8(kk), i+die(kk), j+dje(kk))) * dtinv
          r0 = r0 + ck * ae
          if (nh_mod%emask(ke8(kk), i+die(kk), j+dje(kk))) then
            if (nh_solver == 1) then
              wsum = wsum + ck * (1.0 / w8dr(kk) - sig)
            else
              wsum = wsum + nh_mod%wl(kk)
            end if
          end if
        end do
        nh_mod%rhs0(i,j) = r0
        if (nh_solver == 1) then
          nh_mod%rhs(i,j) = r0
          nh_mod%diag(i,j) = 1.0 + wsum
        else
          nh_mod%rhs(i,j) = r0 / nh_mod%beta(i,j)
          nh_mod%diag(i,j) = 1.0 / nh_mod%beta(i,j) + wsum
        end if
      end if
    end do
  end do
  !$omp end parallel do

  ! --- 4. 反復解 ---
  if (nh_solver == 1) then
    call solve_jacobi(g, s, iters, ok)
  else if (f_nh_slope == 0) then
    call solve_cg(g, iters, ok, .false.)
  else
    ! Picard: 平坦部分 (1/β)φ + Lφ = [rhs0 + R(φ)]/β を CG(warm start)で解き、
    ! 勾配項 R(φ) = Σ_NH [(c_k − β wd_k)(φ_n − φ_i)/d_k + c_k (φ_i + φ_n) σ_k] を
    ! 更新して収束まで繰り返す。収束判定は max|Δφ| ≤ nh_tol·max|φ|(allreduce)
    iters = 0
    ok = .false.
    do m = 1, nh_itmax
      call par_halo_cell(nh_mod%phi)
      dphimax = 0.0
      phimax = 0.0
      !$omp parallel do schedule(static) private(i, j, kk, rr, ck, sig, phic, phin) reduction(max:phimax)
      do j = dcp%js, dcp%je
        do i = 1, g%nx
          if (nh_mod%cmask(i,j) == 0) cycle
          phic = nh_mod%phi(i,j)
          phimax = max(phimax, abs(phic))
          rr = 0.0
          do kk = 1, 8
            if (.not. nh_mod%emask(ke8(kk), i+die(kk), j+dje(kk))) cycle
            call slope_coef(g, s, i, j, kk, ck, sig)
            phin = nh_mod%phi(i+din(kk), j+djn(kk))
            rr = rr + (ck - nh_mod%beta(i,j) * nh_mod%wd(kk)) * (phin - phic) / w8dr(kk) &
                    + ck * (phic + phin) * sig
          end do
          nh_mod%rhs(i,j) = (nh_mod%rhs0(i,j) + rr) / nh_mod%beta(i,j)
          nh_mod%work2(i,j) = phic
        end do
      end do
      !$omp end parallel do
      call solve_cg(g, it2, ok2, m > 1)
      iters = iters + it2
      !$omp parallel do schedule(static) private(i, j) reduction(max:dphimax)
      do j = dcp%js, dcp%je
        do i = 1, g%nx
          if (nh_mod%cmask(i,j) == 0) cycle
          dphimax = max(dphimax, abs(nh_mod%phi(i,j) - nh_mod%work2(i,j)))
        end do
      end do
      !$omp end parallel do
      vmax2(1) = dphimax
      vmax2(2) = phimax
      call par_allreduce_max(vmax2)
      if (vmax2(1) <= nh_tol * max(vmax2(2), tiny(1.0))) then
        ok = ok2
        exit
      end if
    end do
    if (.not. ok) call par_warn("swflow_enc_nh: Picard (bottom-slope terms) did not converge")
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
        if (f_nh_slope == 0) then
          sx%uv(k,ie,je) = sx%uv(k,ie,je) + p%dt * (phin - phic) / w8dr(k)
        else
          call slope_coef(g, s, i, j, k, ck, sig)
          sx%uv(k,ie,je) = sx%uv(k,ie,je) + p%dt * ((phin - phic) / w8dr(k) + (phic + phin) * sig)
        end if
        sx%mn1(k,ie,je) = sx%uv(k,ie,je) * nh_he(k,ie,je)
      end do
    end do
  end do
  !$omp end parallel do
  call par_edge_merge(sx%uv,  esync_s, esync_n)
  call par_edge_merge(sx%mn1, esync_s, esync_n)

end subroutine


!----------------------------------------------------------------------
! 砕波スイッチ(plan §8.2。SWASH 型): 水面の上昇速度 ∂η/∂t が α√(gh) を
!   超えるセルを砕波(静水圧)とし、砕波セルに 8 近傍で接して β√(gh) を
!   超えるセルも砕波(前線の伝播)とする。砕波セルは NH マスクから外れ、
!   接するエッジは補正されない(段波として静水圧 ENC が扱う)。
!   ∂η/∂t は predictor の流束 mn1* から (h^{n+1*} − h^n)/Δt として求める
!   ので、ステップ間の状態を持たない(リスタート往復はビット一致)。
!   SWASH の「波頂が通過するまで砕波を維持」はこの stateless 版にはない。
!----------------------------------------------------------------------
subroutine breaking_switch(p, g, s, sx)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  type(t_enc_status), intent(in) :: sx
  integer :: i, j, kk, nbrk, m, margin
  real :: dhdt, bb, hmax
  real :: vmax(1)

  ! 判定(担当帯)。brk = 1: 砕波、0.5: 候補(β を超える)、0: なし
  !   前ステップに砕波だったセルは、水面が上昇している間(波頂が通過する
  !   まで)砕波を維持する(SWASH の規則。brk はステップ間で保持する状態。
  !   リスタート時は 0 から始まるため、復元直後の 1 ステップだけ履歴がない)
  !$omp parallel do schedule(static) private(i, j, kk, dhdt, bb)
  do j = dcp%js, dcp%je
    do i = 1, g%nx
      if (nh_mod%cmask(i,j) == 0) then
        nh_mod%brk(i,j) = 0.0
        cycle
      end if
      if (nh_break_type == 2) then
        ! フルード数判定(stateless。遡上の舌・射流は静水圧)
        if (s%vv(i,j) > nh_break_fr * sqrt(p%gg * s%h(i,j))) then
          nh_mod%brk(i,j) = 1.0
        else
          nh_mod%brk(i,j) = 0.0
        end if
        cycle
      else if (nh_break_type == 3) then
        ! 水面勾配判定(stateless・Galilean 不変。8 近傍への |Δη|/距離の最大。
        ! 乾いた近傍は水面が定義できないので除く)
        bb = 0.0
        do kk = 1, 8
          if (i+din(kk) < 1 .or. i+din(kk) > g%nx) cycle
          if (g%x(i+din(kk), j+djn(kk)) <= 0) cycle
          if (s%h(i+din(kk), j+djn(kk)) < p%dd) cycle
          bb = max(bb, abs(s%z(i+din(kk), j+djn(kk)) + s%h(i+din(kk), j+djn(kk)) &
                           - s%z(i,j) - s%h(i,j)) / w8dr(kk))
        end do
        if (bb > nh_break_slope) then
          nh_mod%brk(i,j) = 1.0
        else
          nh_mod%brk(i,j) = 0.0
        end if
        cycle
      end if
      dhdt = 0.0
      do kk = 1, 8
        dhdt = dhdt - sgn8(kk) * sx%mn1(ke8(kk), i+die(kk), j+dje(kk)) * nh_mod%wd(kk)
      end do
      bb = dhdt / sqrt(p%gg * s%h(i,j))
      if (bb > nh_break_alpha) then
        nh_mod%brk(i,j) = 1.0
      else if (nh_mod%brk(i,j) == 1.0 .and. dhdt > 0.0) then
        nh_mod%brk(i,j) = 1.0
      else if (bb > nh_break_beta) then
        nh_mod%brk(i,j) = 0.5
      else
        nh_mod%brk(i,j) = 0.0
      end if
    end do
  end do
  !$omp end parallel do

  ! 前線の伝播: 候補セル(0.5)が砕波セルに 8 近傍で接していれば砕波(1 回)
  call par_halo_cell(nh_mod%brk)
  !$omp parallel do schedule(static) private(i, j, kk)
  do j = dcp%js, dcp%je
    do i = 1, g%nx
      nh_mod%phi1(i,j) = nh_mod%brk(i,j)
      if (nh_mod%brk(i,j) /= 0.5) cycle
      nh_mod%phi1(i,j) = 0.0                   ! 候補は接していなければ 0 に戻す
      do kk = 1, 8
        if (i+din(kk) < 1 .or. i+din(kk) > g%nx) cycle
        if (nh_mod%brk(i+din(kk), j+djn(kk)) == 1.0) then
          nh_mod%phi1(i,j) = 1.0
          exit
        end if
      end do
    end do
  end do
  !$omp end parallel do
  !$omp parallel do schedule(static) private(j)
  do j = dcp%js, dcp%je
    nh_mod%brk(:,j) = nh_mod%phi1(:,j)
    nh_mod%phi1(:,j) = 0.0
  end do
  !$omp end parallel do

  ! 縁: 砕波セルの周り margin セル(候補セルの中)も静水圧にする。砕波した
  ! 波の前面だけでなく波頂まで含めて静水圧に落とし、NH の圧力が砕波
  ! 前線を押し続けないようにする(hybrid Boussinesq 系の「波全体を NSWE」
  ! に相当)。膨張は活性集合と同じ 8 近傍の論理和(walk 順に依らない)
  if (nh_break_margin > 0) then
    margin = nh_break_margin
  else
    hmax = 0.0
    !$omp parallel do schedule(static) private(i, j) reduction(max:hmax)
    do j = dcp%js, dcp%je
      do i = 1, g%nx
        if (nh_mod%cmask(i,j) == 1) hmax = max(hmax, s%h(i,j))
      end do
    end do
    !$omp end parallel do
    vmax(1) = hmax
    call par_allreduce_max(vmax)
    margin = max(2, ceiling(2.0 * vmax(1) / min(g%dx, g%dy)))
  end if
  do m = 1, margin
    call par_halo_cell(nh_mod%brk)
    !$omp parallel do schedule(static) private(i, j, kk)
    do j = dcp%js, dcp%je
      do i = 1, g%nx
        nh_mod%phi1(i,j) = nh_mod%brk(i,j)
        if (nh_mod%cmask(i,j) == 0 .or. nh_mod%brk(i,j) == 1.0) cycle
        do kk = 1, 8
          if (i+din(kk) < 1 .or. i+din(kk) > g%nx) cycle
          if (nh_mod%brk(i+din(kk), j+djn(kk)) == 1.0) then
            nh_mod%phi1(i,j) = 1.0
            exit
          end if
        end do
      end do
    end do
    !$omp end parallel do
    !$omp parallel do schedule(static) private(j)
    do j = dcp%js, dcp%je
      nh_mod%brk(:,j) = nh_mod%phi1(:,j)
      nh_mod%phi1(:,j) = 0.0
    end do
    !$omp end parallel do
  end do
  call par_halo_cell(nh_mod%brk)

  ! 砕波セルを NH マスクから外す(ハロ行も交換済みの値で同じ判定)
  !$omp parallel do schedule(static) private(i, j)
  do j = dcp%jsh, dcp%jeh
    do i = 1, g%nx
      if (nh_mod%brk(i,j) == 1.0) then
        nh_mod%cmask(i,j) = 0
        nh_mod%beta(i,j) = 0.0
      end if
    end do
  end do
  !$omp end parallel do
  nbrk = 0
  !$omp parallel do schedule(static) private(i, j) reduction(+:nbrk)
  do j = dcp%js, dcp%je
    do i = 1, g%nx
      if (nh_mod%brk(i,j) == 1.0) nbrk = nbrk + 1
    end do
  end do
  !$omp end parallel do
  nh_mod%brksum = nh_mod%brksum + nbrk

  ! 砕波域の渦粘性(plan §15): 砕波セル(縁を含む)に
  !   ν_b = nh_break_visc · B · h · √(gh) · |∇η|、B = clip((|∇η| − s_on)/s_on, 0, 1)
  ! を与える(Kennedy et al. 2000 の ν = B δ_b² h ∂η/∂t を進行波の運動学
  ! ∂η/∂t ≈ c|∂η/∂x| で局所・状態なしにした形。s_on = nh_break_slope)。
  ! 縁のセルは勾配が小さいので B が自然に 0 へ落ちる(距離による減衰は
  ! 持たない)。次ステップの diff_prepare が ν に加える(1 ステップ遅れ)。
  ! td は近傍 ±1 の ν を読むので、ハロ 2 まで交換する
  if (nh_break_visc > 0.0) then
    !$omp parallel do schedule(static) private(i, j, bb)
    do j = dcp%js, dcp%je
      do i = 1, g%nx
        nh_nub(i,j) = 0.0
        if (nh_mod%brk(i,j) /= 1.0) cycle
        if (s%h(i,j) < p%dd) cycle
        bb = surface_slope(p, g, s, i, j)
        if (bb <= nh_break_slope) cycle
        nh_nub(i,j) = nh_break_visc * min((bb - nh_break_slope) / nh_break_slope, 1.0) &
                    * s%h(i,j) * sqrt(p%gg * s%h(i,j)) * bb
      end do
    end do
    !$omp end parallel do
    call par_halo_cell(nh_nub)
  end if
end subroutine


!----------------------------------------------------------------------
! 水面勾配 |∇η|(8 近傍への |Δη|/距離の最大。乾いた近傍・無効セルは除く)。
!   判定 3 と同じ式(判定 3 のループは -Ofast のコード生成を変えないため
!   そのまま残し、ここでは渦粘性用に別関数とする)
!----------------------------------------------------------------------
function surface_slope(p, g, s, i, j) result(bb)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer, intent(in) :: i, j
  real :: bb
  integer :: kk
  bb = 0.0
  do kk = 1, 8
    if (i+din(kk) < 1 .or. i+din(kk) > g%nx) cycle
    if (g%x(i+din(kk), j+djn(kk)) <= 0) cycle
    if (s%h(i+din(kk), j+djn(kk)) < p%dd) cycle
    bb = max(bb, abs(s%z(i+din(kk), j+djn(kk)) + s%h(i+din(kk), j+djn(kk)) &
                     - s%z(i,j) - s%h(i,j)) / w8dr(kk))
  end do
end function


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
! 底面勾配項の係数(Version 2)。セル (i,j) の方向 kk について
!   ck  = (h_i/4) wd_k max(h_i − Δz_k, 0)   (Δz_k = z_n − z_i。φ_i = Σ_k ck a_k^out)
!   sig = Δ(h + 2z) / (2 h_e d_k)           (圧力項 (φ/h)∇(h+2z_b) の係数。
!         (φ_c + φ_n)·sig。|Δ(h+2z)/(2h_e)| ≤ 1/2 にクランプして対角優位を保つ)
!   近傍の h, z は確保範囲(x の番兵 0..nx+1、行 jsh..jeh)の中で読む
!----------------------------------------------------------------------
subroutine slope_coef(g, s, i, j, kk, ck, sig)
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer, intent(in) :: i, j, kk
  real, intent(out) :: ck, sig
  integer :: in, jn
  real :: hi, hn, dz, he, sd
  if (g%initialized) continue  ! 引数未使用の警告を抑制
  in = i + din(kk)
  jn = j + djn(kk)
  hi = s%h(i,j)
  hn = s%h(in,jn)
  dz = s%z(in,jn) - s%z(i,j)
  ck = 0.25 * hi * nh_mod%wd(kk) * max(hi - dz, 0.0)
  he = 0.5 * (hi + hn)
  if (he > 0.0) then
    sd = (hn + 2.0 * s%z(in,jn)) - (hi + 2.0 * s%z(i,j))
    sd = max(-he, min(he, sd))          ! |sd/(2 he)| ≤ 1/2
    sig = sd / (2.0 * he * w8dr(kk))
  else
    sig = 0.0
  end if
end subroutine


!----------------------------------------------------------------------
! Jacobi 反復: φ_new = (rhs + β Σ_k w_k φ_n) / diag(NH セルのみ)
!   収束判定は残差 |diag·(φ_new − φ)| の最大(allreduce。max は順序不変)
!   が nh_tol × max|rhs| 以下。全ランクが同じ回数だけ halo と allreduce を
!   呼ぶ(collective 規律 §5)
!----------------------------------------------------------------------
subroutine solve_jacobi(g, s, iters, ok)
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer, intent(out) :: iters
  logical, intent(out) :: ok
  integer :: i, j, kk, it
  real :: rsum, resmax, rhsmax, pnew, ck, sig
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
    !$omp parallel do schedule(static) private(i, j, kk, rsum, pnew, ck, sig) reduction(max:resmax)
    do j = dcp%js, dcp%je
      do i = 1, g%nx
        if (nh_mod%cmask(i,j) == 0) cycle
        rsum = 0.0
        if (f_nh_slope == 0) then
          do kk = 1, 8
            if (nh_mod%emask(ke8(kk), i+die(kk), j+dje(kk))) then
              rsum = rsum + nh_mod%wl(kk) * nh_mod%phi(i+din(kk), j+djn(kk))
            end if
          end do
          pnew = (nh_mod%rhs(i,j) + nh_mod%beta(i,j) * rsum) / nh_mod%diag(i,j)
        else
          do kk = 1, 8
            if (nh_mod%emask(ke8(kk), i+die(kk), j+dje(kk))) then
              call slope_coef(g, s, i, j, kk, ck, sig)
              rsum = rsum + ck * (1.0 / w8dr(kk) + sig) * nh_mod%phi(i+din(kk), j+djn(kk))
            end if
          end do
          pnew = (nh_mod%rhs(i,j) + rsum) / nh_mod%diag(i,j)
        end if
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
subroutine solve_cg(g, iters, ok, warm)
  type(t_geoinfo), intent(in) :: g
  integer, intent(out) :: iters
  logical, intent(out) :: ok
  logical, intent(in) :: warm     ! .true.: 現在の φ を初期値にする(r = b − Mφ)
  integer :: i, j, kk, it
  real(real64) :: bb, rr0, rr1, pap, alpha, bet
  real :: lsum

  if (warm) then
    ! x = φ(現在値), r = b − M φ, p = r
    call par_halo_cell(nh_mod%phi)
    !$omp parallel do schedule(static) private(i, j, kk, lsum)
    do j = dcp%jsh, dcp%jeh
      nh_mod%rr(:,j) = 0.0
      nh_mod%phi1(:,j) = 0.0
      nh_mod%ap(:,j) = 0.0
      if (j < dcp%js .or. j > dcp%je) cycle
      do i = 1, g%nx
        if (nh_mod%cmask(i,j) == 0) cycle
        lsum = 0.0
        do kk = 1, 8
          if (nh_mod%emask(ke8(kk), i+die(kk), j+dje(kk))) then
            lsum = lsum + nh_mod%wl(kk) * nh_mod%phi(i+din(kk), j+djn(kk))
          end if
        end do
        nh_mod%rr(i,j) = nh_mod%rhs(i,j) - (nh_mod%diag(i,j) * nh_mod%phi(i,j) - lsum)
        nh_mod%phi1(i,j) = nh_mod%rr(i,j)
      end do
    end do
    !$omp end parallel do
    bb = dot(nh_mod%rhs, nh_mod%rhs)
  else
    ! x = φ = 0, r = b, p = r
    !$omp parallel do schedule(static) private(j)
    do j = dcp%jsh, dcp%jeh
      nh_mod%rr(:,j) = nh_mod%rhs(:,j)
      nh_mod%phi1(:,j) = nh_mod%rhs(:,j)
      nh_mod%ap(:,j) = 0.0
    end do
    !$omp end parallel do
    bb = dot(nh_mod%rr, nh_mod%rr)
  end if
  ok = .true.
  iters = 0
  if (bb <= 0.0_real64) return
  rr0 = dot(nh_mod%rr, nh_mod%rr)
  if (rr0 <= 0.0_real64) return

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
  integer :: ivals(3)
  if (.not. nh_active) return
  if (nh_mod%nstep > 0) then
    ivals(1) = int(min(nh_mod%actsum, int(huge(1), 8)))
    ivals(2) = int(min(nh_mod%brksum, int(huge(1), 8)))
    ivals(3) = nh_mod%nfail
    call par_allreduce_sumi(ivals(1:2))
    call par_info("swflow_enc_nh: steps "//itoa(nh_mod%nstep)// &
                  ", iterations avg "//itoa(int(nh_mod%itsum / nh_mod%nstep))// &
                  " max "//itoa(nh_mod%itmax_seen)// &
                  ", active cells avg "//itoa(ivals(1) / nh_mod%nstep)// &
                  ", breaking cells avg "//itoa(ivals(2) / nh_mod%nstep)// &
                  ", not converged "//itoa(ivals(3)))
  end if
  if (allocated(nh_mod%uv0)) deallocate(nh_mod%uv0)
  if (allocated(nh_he)) deallocate(nh_he)
  if (allocated(nh_nub)) deallocate(nh_nub)
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
  if (allocated(nh_mod%brk)) deallocate(nh_mod%brk)
  if (allocated(nh_mod%rhs0)) deallocate(nh_mod%rhs0)
  if (allocated(nh_mod%work2)) deallocate(nh_mod%work2)
  if (allocated(nh_mod%emask)) deallocate(nh_mod%emask)
  nh_active = .false.
end subroutine

end submodule
