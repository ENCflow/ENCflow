!======================================================================
! fault2disp: 断層パラメータ → 地盤変位のスナップショット表(fn_bedmotion の入力)
!   docs/bedmotion_plan.md §6(段階 2)。計算本体には依存しない独立ユーティリティ。
!
!   使い方:  fault2disp fault2disp.txt
!   入力(&list_fault2disp): 格子(nx, ny, dx, dy、左下隅の外縁座標 x_ll, y_ll)、
!   出力先、出力時刻列、断層セグメント(最大 nsegmax)。座標は格子と同じ
!   投影座標 (m)。x は東、y は北に増える。出力の行順は ENCflow の z と同じ
!   北 → 南(行 j の中心 y = y_ll + (ny − j + 1/2) dy)。
!
!   変位: Okada (1985) の半無限弾性体(Poisson 比 0.25)における矩形断層の
!   地表変位(BSSA 75, 1135–1154 の式 (25)〜(30)、Chinnery の記法)。
!   セグメントの参照点は上端の中心(x_top, y_top)と上端深さ(d_top > 0)、
!   走向 strike(北から時計回り、度)、傾斜 dip(度。断層は走向の右側に
!   下がる)、すべり角 rake(度。断層面上で走向方向から反時計回り。
!   90 = 逆断層)、長さ L(走向方向)、幅 W(傾斜方向)、すべり量 U (m)。
!   時間: 破壊開始 t_r (s) と立ち上がり時間 τ (s)、関数 1: 線形、2: 半正弦
!   ((1 − cos)/2)。τ = 0 は瞬時。複数セグメントは重ね合わせ。
!   鉛直変位 u_z に、オプションで水平変位の寄与 u_h·∇z(Tanioka & Satake
!   1996。fn_z を与えたとき)を加える。
!
!   出力: dir_out/disp_NNNN.txt(nout + 1 枚。全域の累積変位。テキスト行列)
!   と dir_out/bmlist.txt(「時刻 ファイル名」。ファイル名は dir_out 相対の
!   前に prefix_list を付ける = ENCflow の dir_data からの相対にする)。
!
!   検算: Okada (1985) Table 2 の有限矩形断層のケース(x=2, y=3, d=4, δ=70°,
!   L=3, W=2)を -check で再現する(fault2disp -check)。
!======================================================================
program fault2disp
  implicit none
  integer, parameter :: dp = kind(1.0d0)
  integer, parameter :: nsegmax = 50
  real(dp), parameter :: pi = 3.14159265358979323846d0
  real(dp), parameter :: deg = pi / 180.0d0
  ! --- namelist ---
  integer :: nx = 0, ny = 0
  real(dp) :: dx = 0.0d0, dy = 0.0d0, x_ll = 0.0d0, y_ll = 0.0d0
  character(len=256) :: dir_out = 'bm', prefix_list = 'bm/', fn_z = ''
  integer :: nout = 20
  real(dp) :: t_start = -1.0d0, t_end = -1.0d0
  integer :: nseg = 0
  real(dp) :: x_top(nsegmax) = 0, y_top(nsegmax) = 0, d_top(nsegmax) = 0
  real(dp) :: strike(nsegmax) = 0, dip(nsegmax) = 0, rake(nsegmax) = 0
  real(dp) :: flength(nsegmax) = 0, fwidth(nsegmax) = 0, slip(nsegmax) = 0
  real(dp) :: t_r(nsegmax) = 0, t_rise(nsegmax) = 0
  integer :: f_rise(nsegmax) = 2
  namelist /list_fault2disp/ nx, ny, dx, dy, x_ll, y_ll, dir_out, prefix_list, fn_z, nout, t_start, t_end, &
                             nseg, x_top, y_top, d_top, strike, dip, rake, flength, fwidth, slip, t_r, t_rise, f_rise
  ! --- work ---
  character(len=256) :: fn, arg
  real(dp), allocatable :: uz(:,:,:), z(:,:), d(:,:)
  real(dp) :: xc, yc, ux, uy, uzz, t, r, dzdx, dzdy, umax, umin
  integer :: un, ios, i, j, k, m
  character(len=1024) :: iom

  if (command_argument_count() < 1) then
    print '(a)', "usage: fault2disp fault2disp.txt | fault2disp -check"
    stop 2
  end if
  call get_command_argument(1, arg)
  if (trim(arg) == '-check') then
    call self_check()
    stop
  end if

  open(newunit=un, file=trim(arg), status='old', action='read', iostat=ios, iomsg=iom)
  if (ios /= 0) then
    print '(a)', "fault2disp: cannot open "//trim(arg)//": "//trim(iom); stop 1
  end if
  read(un, nml=list_fault2disp, iostat=ios, iomsg=iom)
  if (ios /= 0) then
    print '(a)', "fault2disp: cannot read namelist list_fault2disp: "//trim(iom); stop 1
  end if
  close(un)
  if (nx < 1 .or. ny < 1 .or. dx <= 0 .or. dy <= 0) then
    print '(a)', "fault2disp: nx, ny, dx, dy are required"; stop 1
  end if
  if (nseg < 1 .or. nseg > nsegmax) then
    print '(a,i0)', "fault2disp: nseg must be 1..", nsegmax; stop 1
  end if
  if (nout < 1) then
    print '(a)', "fault2disp: nout must be >= 1"; stop 1
  end if
  do k = 1, nseg
    if (d_top(k) < 0 .or. flength(k) <= 0 .or. fwidth(k) <= 0 .or. t_rise(k) < 0) then
      print '(a,i0)', "fault2disp: invalid geometry/time in segment ", k; stop 1
    end if
    if (dip(k) <= 0 .or. dip(k) > 90) then
      print '(a,i0)', "fault2disp: dip must be in (0, 90] in segment ", k; stop 1
    end if
    if (d_top(k) == 0 .and. dip(k) < 90) then
      print '(a,i0)', "fault2disp: note: segment ", k, " reaches the surface (d_top = 0)"
    end if
  end do

  ! --- 各セグメントの最終変位(鉛直 + 水平の ∇z 寄与)を格子で評価 ---
  allocate(uz(nx, ny, nseg), source = 0.0d0)
  if (len_trim(fn_z) > 0) then
    allocate(z(nx, ny))
    open(newunit=un, file=trim(fn_z), status='old', action='read', iostat=ios, iomsg=iom)
    if (ios /= 0) then
      print '(a)', "fault2disp: cannot open fn_z "//trim(fn_z)//": "//trim(iom); stop 1
    end if
    do j = 1, ny
      read(un, *, iostat=ios) z(1:nx, j)
      if (ios /= 0) then
        print '(a,i0)', "fault2disp: cannot read fn_z row ", j; stop 1
      end if
    end do
    close(un)
    print '(a)', "fault2disp: horizontal-displacement contribution u_h.grad(z) ON (Tanioka & Satake 1996)"
  end if
  do k = 1, nseg
    do j = 1, ny
      yc = y_ll + (dble(ny - j) + 0.5d0) * dy
      do i = 1, nx
        xc = x_ll + (dble(i) - 0.5d0) * dx
        call segment_disp(k, xc, yc, ux, uy, uzz)
        uz(i, j, k) = uzz
        if (allocated(z)) then
          ! ∇z は中心差分(端は片側)。行 j は北→南なので ∂z/∂y = −(z(j+1) − z(j−1))/(2dy)
          dzdx = (z(min(i+1, nx), j) - z(max(i-1, 1), j)) / (dble(min(i+1, nx) - max(i-1, 1)) * dx)
          dzdy = -(z(i, min(j+1, ny)) - z(i, max(j-1, 1))) / (dble(min(j+1, ny) - max(j-1, 1)) * dy)
          uz(i, j, k) = uz(i, j, k) + ux * dzdx + uy * dzdy
        end if
      end do
    end do
    print '(a,i0,a,f0.4,a,f0.4,a)', "fault2disp: segment ", k, ": final u_z max ", maxval(uz(:,:,k)), &
          " m, min ", minval(uz(:,:,k)), " m"
  end do

  ! --- 出力時刻列と書き出し ---
  if (t_start < 0) t_start = minval(t_r(1:nseg))
  if (t_end < 0) t_end = maxval(t_r(1:nseg) + t_rise(1:nseg))
  if (t_end < t_start) t_end = t_start
  call execute_command_line("mkdir -p "//trim(dir_out))
  open(newunit=un, file=trim(dir_out)//"/bmlist.txt", status='replace', action='write')
  write(un, '(a)') "# time(s)  file   (fault2disp: "//trim(adjustl(itoa(nseg)))//" segment(s))"
  allocate(d(nx, ny))
  do m = 0, nout
    if (t_end > t_start) then
      t = t_start + (t_end - t_start) * dble(m) / dble(nout)
    else
      t = t_start
      if (m > 0) exit
    end if
    d = 0.0d0
    do k = 1, nseg
      r = ramp(k, t)
      if (r /= 0.0d0) d = d + r * uz(:,:,k)
    end do
    write(fn, '(a,i4.4,a)') "disp_", m, ".txt"
    call write_matrix(trim(dir_out)//"/"//trim(fn), d)
    write(un, '(f0.3,2x,a)') t, trim(prefix_list)//trim(fn)
  end do
  close(un)
  umax = maxval(d); umin = minval(d)
  print '(a,i0,a,f0.3,a,f0.3,a)', "fault2disp: wrote ", min(nout, max(0, nout)) + 1, " snapshot(s) to "//trim(dir_out)// &
        "/ (t = ", t_start, " .. ", t_end, " s)"
  print '(a,f0.4,a,f0.4,a)', "fault2disp: final displacement max ", umax, " m, min ", umin, " m"

contains

  !--------------------------------------------------------------------
  ! 立ち上がり関数 r(t) ∈ [0, 1]
  !--------------------------------------------------------------------
  function ramp(k, t) result(r)
    integer, intent(in) :: k
    real(dp), intent(in) :: t
    real(dp) :: r, s
    if (t <= t_r(k)) then
      r = 0.0d0
    else if (t_rise(k) <= 0.0d0 .or. t >= t_r(k) + t_rise(k)) then
      r = 1.0d0
    else
      s = (t - t_r(k)) / t_rise(k)
      if (f_rise(k) == 1) then
        r = s
      else
        r = 0.5d0 * (1.0d0 - cos(pi * s))
      end if
    end if
  end function

  !--------------------------------------------------------------------
  ! セグメント k による地表点 (xc, yc) の変位(東 ux、北 uy、上 uz)
  !   上端中心 → 下端中心: 傾斜方向(走向の右)に W cosδ、深さ d = d_top + W sinδ。
  !   Okada の座標: 原点を下端の中心に置き、x は走向方向、y は up-dip 方向
  !   (逆断層では断層の投影上(浅い端の近く)が隆起し、下端の先(down-dip 側)が沈降)
  !--------------------------------------------------------------------
  subroutine segment_disp(k, xc, yc, ux, uy, uzo)
    integer, intent(in) :: k
    real(dp), intent(in) :: xc, yc
    real(dp), intent(out) :: ux, uy, uzo
    real(dp) :: sn, cs, sd, cd, xb, yb, dbot, xf, yf, u1, u2, ex, ey, ez
    sn = sin(strike(k) * deg); cs = cos(strike(k) * deg)
    sd = sin(dip(k) * deg);    cd = cos(dip(k) * deg)
    ! 下端中心(傾斜方向の単位ベクトルは (cosφ, −sinφ))
    xb = x_top(k) + fwidth(k) * cd * cs
    yb = y_top(k) - fwidth(k) * cd * sn
    dbot = d_top(k) + fwidth(k) * sd
    ! 断層座標(Okada): xf は走向方向(下端中心から)、yf は上方(up-dip)方向
    !   = 傾斜方向の逆(断層は原点 = 下端から +yf へ向かって浅くなる)
    xf = (xc - xb) * sn + (yc - yb) * cs
    yf = -((xc - xb) * cs - (yc - yb) * sn)
    u1 = slip(k) * cos(rake(k) * deg)
    u2 = slip(k) * sin(rake(k) * deg)
    call okada85(xf, yf, dbot, dip(k) * deg, flength(k), fwidth(k), u1, u2, ex, ey, ez)
    ! 断層座標 (走向, up-dip) → (東, 北)
    ux = ex * sn - ey * cs
    uy = ex * cs + ey * sn
    uzo = ez
  end subroutine

  !--------------------------------------------------------------------
  ! Okada (1985) 式 (25)〜(30): 下端中心を原点、x 走向方向、y 傾斜方向、
  !   下端深さ d、傾斜 δ、長さ L(x ∈ [−L/2, L/2])、幅 W(下端から上方へ)
  !--------------------------------------------------------------------
  subroutine okada85(x, y, d, delta, L, W, u1, u2, ux, uy, uz)
    real(dp), intent(in) :: x, y, d, delta, L, W, u1, u2
    real(dp), intent(out) :: ux, uy, uz
    real(dp) :: p, q, sd, cd, f(3,4), g(3,4)
    integer :: n
    sd = sin(delta); cd = cos(delta)
    p = y * cd + d * sd
    q = y * sd - d * cd
    ux = 0; uy = 0; uz = 0
    ! Chinnery: f(ξ,η)|| = f(x+L/2, p) − f(x+L/2, p−W) − f(x−L/2, p) + f(x−L/2, p−W)
    call kernels(x + L/2, p,     q, sd, cd, f(:,1), g(:,1))
    call kernels(x + L/2, p - W, q, sd, cd, f(:,2), g(:,2))
    call kernels(x - L/2, p,     q, sd, cd, f(:,3), g(:,3))
    call kernels(x - L/2, p - W, q, sd, cd, f(:,4), g(:,4))
    do n = 1, 3
      f(n,1) = f(n,1) - f(n,2) - f(n,3) + f(n,4)
      g(n,1) = g(n,1) - g(n,2) - g(n,3) + g(n,4)
    end do
    ux = -u1 / (2*pi) * f(1,1) - u2 / (2*pi) * g(1,1)
    uy = -u1 / (2*pi) * f(2,1) - u2 / (2*pi) * g(2,1)
    uz = -u1 / (2*pi) * f(3,1) - u2 / (2*pi) * g(3,1)
  end subroutine

  !--------------------------------------------------------------------
  ! 走向すべり(f)・傾斜すべり(g)のカーネル(Poisson 比 1/4: μ/(λ+μ) = 1/2)
  !--------------------------------------------------------------------
  subroutine kernels(xi, eta, q, sd, cd, f, g)
    real(dp), intent(in) :: xi, eta, q, sd, cd
    real(dp), intent(out) :: f(3), g(3)
    real(dp), parameter :: mu = 0.5d0, eps = 1.0d-12
    real(dp) :: R, X, yt, dt, I1, I2, I3, I4, I5, at, lnReta, lnRdt
    R = sqrt(xi*xi + eta*eta + q*q)
    X = sqrt(xi*xi + q*q)
    yt = eta * cd + q * sd
    dt = eta * sd - q * cd
    if (abs(q) < eps) then
      at = 0.0d0
    else
      at = atan(xi * eta / (q * R))
    end if
    lnReta = safelog(R + eta)
    lnRdt = safelog(R + dt)
    if (abs(cd) < 1.0d-10) then
      I1 = -mu / 2 * xi * q / (R + dt)**2
      I3 = mu / 2 * (eta / (R + dt) + yt * q / (R + dt)**2 - lnReta)
      I4 = -mu * q / (R + dt)
      I5 = -mu * xi * sd / (R + dt)
    else
      if (abs(xi) < eps) then
        I5 = 0.0d0
      else
        I5 = mu * 2 / cd * atan((eta * (X + q * cd) + X * (R + X) * sd) / (xi * (R + X) * cd))
      end if
      I4 = mu / cd * (lnRdt - sd * lnReta)
      I3 = mu * (yt / (cd * (R + dt)) - lnReta) + sd / cd * I4
      I1 = mu * (-xi / (cd * (R + dt))) - sd / cd * I5
    end if
    I2 = mu * (-lnReta) - I3
    ! strike-slip
    f(1) = xi * q / (R * (R + eta)) + at + I1 * sd
    f(2) = yt * q / (R * (R + eta)) + q * cd / (R + eta) + I2 * sd
    f(3) = dt * q / (R * (R + eta)) + q * sd / (R + eta) + I4 * sd
    ! dip-slip
    g(1) = q / R - I3 * sd * cd
    g(2) = yt * q / (R * (R + xi)) + cd * at - I1 * sd * cd
    g(3) = dt * q / (R * (R + xi)) + sd * at - I5 * sd * cd
  end subroutine

  function safelog(v) result(r)
    real(dp), intent(in) :: v
    real(dp) :: r
    r = log(max(v, 1.0d-30))
  end function

  !--------------------------------------------------------------------
  ! Okada (1985) Table 2 の検算(有限矩形断層。原点 = 下端の左端、x ∈ [0, L])
  !--------------------------------------------------------------------
  subroutine self_check()
    real(dp) :: ux, uy, uz
    print '(a)', "Okada (1985) Table 2, case 2: x=2, y=3, d=4, dip=70 deg, L=3, W=2 (origin at the lower-left corner)"
    call okada85(2.0d0 - 1.5d0, 3.0d0, 4.0d0, 70.0d0 * deg, 3.0d0, 2.0d0, 1.0d0, 0.0d0, ux, uy, uz)
    print '(a,3es13.4)', "  strike-slip U1=1: ux, uy, uz = ", ux, uy, uz
    print '(a)',         "  Okada Table 2     :              -8.689E-03  -4.298E-03  -2.747E-03"
    call okada85(2.0d0 - 1.5d0, 3.0d0, 4.0d0, 70.0d0 * deg, 3.0d0, 2.0d0, 0.0d0, 1.0d0, ux, uy, uz)
    print '(a,3es13.4)', "  dip-slip    U2=1: ux, uy, uz = ", ux, uy, uz
    print '(a)',         "  Okada Table 2     :              -4.682E-03  -3.527E-02  -3.564E-02"
  end subroutine

  function itoa(i) result(s)
    integer, intent(in) :: i
    character(len=16) :: s
    write(s, '(i0)') i
  end function

  subroutine write_matrix(fname, a)
    character(len=*), intent(in) :: fname
    real(dp), intent(in) :: a(:,:)
    integer :: u, jj
    open(newunit=u, file=fname, status='replace', action='write')
    do jj = 1, size(a, 2)
      write(u, '(*(1x,f0.6))') a(:, jj)
    end do
    close(u)
  end subroutine

end program
