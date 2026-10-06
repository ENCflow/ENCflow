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
!   出力: dir_out/disp_NNNN.txt(nout + 1 枚。累積変位のテキスト行列)と
!   dir_out/bmlist.txt(「時刻 ファイル名 [i1 j1 ni nj]」。ファイル名は dir_out
!   相対の前に prefix_list を付ける = ENCflow の dir_data からの相対にする)。
!   f_window = 1 なら |u_z| > d_min の外接矩形(全セグメントの和集合)だけを
!   書き、表に窓の列・行・大きさを付ける(広域の計算でファイルを小さくする)。
!
!   地理参照: fn_z が bil+hdr または GeoTIFF(f_input_mode = 2 / 4)なら、
!   f_georef = 1(既定)で格子(nx, ny, dx, dy, x_ll, y_ll)をファイルから取る
!   (ENCflow 本体と同じ m_georef / m_geotiff で読む)。namelist の値は検査・
!   上書き用。f_jpr = 1 で x_top/y_top・x_ll/y_ll を日本の平面直角座標系の
!   順「X(北距) Y(東距)」で受け取る(内部で東・北に入れ替える)。
!   本体のライブラリ libencflow.a をリンクする(utils/rerecord と同じ型)。
!
!   検算: Okada (1985) Table 2 の有限矩形断層のケース(x=2, y=3, d=4, δ=70°,
!   L=3, W=2)を -check で再現する(fault2disp -check)。
!======================================================================
program fault2disp
  use m_fileio, only : fileio_read_matrix, e_fmt_txt, e_fmt_bil, e_fmt_gtif
  use m_georef, only : t_georef, georef_hdr_name, georef_read_hdr
  use m_geotiff, only : t_gtif_info, gtif_inquire
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
  integer :: f_window = 0               ! 1: |u_z| > d_min の外接矩形(全セグメントの和集合)だけを書く
  real(dp) :: d_min = 1.0d-3            ! 窓の閾値 (m)
  ! --- 経緯度入力(f_lonlat = 1): 横メルカトル(Gauss–Krüger)投影で格子座標へ ---
  integer :: f_lonlat = 0               ! 1: 断層位置を lon_top, lat_top(度)で与える
  real(dp) :: lon_top(nsegmax) = 0, lat_top(nsegmax) = 0
  real(dp) :: lon_ll = -999.0d0, lat_ll = -999.0d0   ! 格子左下隅の経緯度(与えると x_ll, y_ll を投影で求める)
  real(dp) :: proj_lon0 = 0, proj_lat0 = 0           ! 投影原点(度)。UTM: 帯の中央子午線と 0、平面直角座標系: 系の原点
  real(dp) :: proj_k0 = 0.9996d0                     ! 中央子午線の縮尺係数(UTM 0.9996、平面直角座標系 0.9999)
  real(dp) :: proj_fe = 500000.0d0, proj_fn = 0.0d0  ! 偽東距・偽北距 (m)(UTM 北半球 500000, 0。平面直角 0, 0)
  real(dp) :: ell_a = 6378137.0d0, ell_rf = 298.257222101d0  ! 楕円体(GRS80。WGS84 は 1/f = 298.257223563)
  integer :: f_strike_conv = 1          ! 1: 走向を子午線収差 γ で格子北基準に補正(strike_grid = strike − γ)
  ! --- 地理参照と座標の並び ---
  integer :: f_input_mode = 1           ! fn_z の形式(1: text, 2: bil+hdr, 4: GeoTIFF。ENCflow と同じ)
  integer :: f_georef = 1               ! 1: fn_z の地理参照(bil の hdr / GeoTIFF)から nx, ny, dx, dy, x_ll, y_ll を取る
  integer :: f_jpr = 0                  ! 1: x_top/y_top と x_ll/y_ll を「X(北距) Y(東距)」の順で与える(平面直角座標系)
  integer :: nseg = 0
  real(dp) :: x_top(nsegmax) = 0, y_top(nsegmax) = 0, d_top(nsegmax) = 0
  real(dp) :: strike(nsegmax) = 0, dip(nsegmax) = 0, rake(nsegmax) = 0
  real(dp) :: flength(nsegmax) = 0, fwidth(nsegmax) = 0, slip(nsegmax) = 0
  real(dp) :: t_r(nsegmax) = 0, t_rise(nsegmax) = 0
  integer :: f_rise(nsegmax) = 2
  namelist /list_fault2disp/ nx, ny, dx, dy, x_ll, y_ll, dir_out, prefix_list, fn_z, nout, t_start, t_end, f_window, d_min, &
                             nseg, x_top, y_top, d_top, strike, dip, rake, flength, fwidth, slip, t_r, t_rise, f_rise, &
                             f_lonlat, lon_top, lat_top, lon_ll, lat_ll, proj_lon0, proj_lat0, proj_k0, proj_fe, proj_fn, &
                             ell_a, ell_rf, f_strike_conv, f_input_mode, f_georef, f_jpr
  ! --- work ---
  character(len=256) :: fn, arg
  real(dp), allocatable :: uz(:,:,:), z(:,:), d(:,:)
  real, allocatable :: zwk(:,:)         ! ライブラリの実数種別(PREC)で読む作業配列
  type(t_georef) :: gr
  type(t_gtif_info) :: tinfo
  integer :: ncols, nrows, stat
  character(len=512) :: msg
  character(len=512) :: hname
  logical :: ex
  real(dp) :: xc, yc, ux, uy, uzz, t, r, dzdx, dzdy, umax, umin, gam
  integer :: un, ios, i, j, k, m, i1, i2, j1, j2
  character(len=64) :: wstr
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

  ! --- 平面直角座標系の並び(X 北距, Y 東距)→ (x 東, y 北) ---
  if (f_jpr == 1) then
    do k = 1, nseg
      t = x_top(k); x_top(k) = y_top(k); y_top(k) = t
    end do
    t = x_ll; x_ll = y_ll; y_ll = t
    print '(a)', "fault2disp: f_jpr = 1: x_top/y_top and x_ll/y_ll were read as (X north, Y east)"
  end if

  ! --- 地理参照: fn_z の hdr / GeoTIFF から格子を取る ---
  if (len_trim(fn_z) > 0 .and. f_georef == 1 .and. (f_input_mode == e_fmt_bil .or. f_input_mode == e_fmt_gtif)) then
    ncols = 0; nrows = 0
    if (f_input_mode == e_fmt_bil) then
      hname = georef_hdr_name(trim(fn_z))
      inquire(file=trim(hname), exist=ex)
      if (.not. ex) then
        print '(a)', "fault2disp: hdr not found for fn_z: "//trim(hname); stop 1
      end if
      call georef_read_hdr(trim(hname), gr, ncols, nrows)
    else
      call gtif_inquire(trim(fn_z), tinfo, stat, msg)
      if (stat /= 0) then
        print '(a)', "fault2disp: cannot probe GeoTIFF "//trim(fn_z)//": "//trim(msg); stop 1
      end if
      ncols = tinfo%nx; nrows = tinfo%ny
      gr%active = tinfo%has_georef
      gr%xul = tinfo%xul; gr%yul = tinfo%yul; gr%csx = tinfo%csx; gr%csy = tinfo%csy
      gr%is_geog = tinfo%is_geog
    end if
    if (nx > 0 .and. nx /= ncols) then
      print '(a,i0,a,i0,a)', "fault2disp: nx(", nx, ") does not match the file (", ncols, ")"; stop 1
    end if
    if (ny > 0 .and. ny /= nrows) then
      print '(a,i0,a,i0,a)', "fault2disp: ny(", ny, ") does not match the file (", nrows, ")"; stop 1
    end if
    nx = ncols; ny = nrows
    if (gr%active) then
      if (gr%is_geog) then
        print '(a)', "fault2disp: fn_z is georeferenced in degrees; project the grid to metres first"; stop 1
      end if
      if (dx > 0 .and. abs(dx - gr%csx) > 1.0d-6 * gr%csx) then
        print '(a,f0.4,a,f0.4,a)', "fault2disp: dx(", dx, ") does not match the file cell size (", gr%csx, ")"; stop 1
      end if
      if (dy > 0 .and. abs(dy - gr%csy) > 1.0d-6 * gr%csy) then
        print '(a,f0.4,a,f0.4,a)', "fault2disp: dy(", dy, ") does not match the file cell size (", gr%csy, ")"; stop 1
      end if
      dx = gr%csx; dy = gr%csy
      x_ll = gr%xul
      y_ll = gr%yul - dble(ny) * gr%csy
      print '(a,i0,a,i0,a,f0.4,a,f0.4,a,f0.3,a,f0.3,a)', "fault2disp: georeference from "//trim(fn_z)//": nx = ", nx, &
            ", ny = ", ny, ", dx = ", dx, " m, dy = ", dy, " m, x_ll = ", x_ll, " m, y_ll = ", y_ll, " m"
    else
      print '(a)', "fault2disp: note: fn_z has no georeference; using namelist dx, dy, x_ll, y_ll"
    end if
  end if
  if (nx < 1 .or. ny < 1 .or. dx <= 0 .or. dy <= 0) then
    print '(a)', "fault2disp: nx, ny, dx, dy are required (or a georeferenced fn_z)"; stop 1
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

  ! --- 経緯度 → 格子座標(横メルカトル)。走向は子午線収差で格子北基準に ---
  if (f_lonlat == 1) then
    if (lon_ll > -999.0d0 .and. lat_ll > -999.0d0) then
      call tm_forward(lon_ll, lat_ll, x_ll, y_ll, gam)
      print '(a,f0.3,a,f0.3,a)', "fault2disp: grid lower-left corner projected to x_ll = ", x_ll, " m, y_ll = ", y_ll, " m"
    end if
    do k = 1, nseg
      call tm_forward(lon_top(k), lat_top(k), x_top(k), y_top(k), gam)
      if (f_strike_conv == 1) strike(k) = strike(k) - gam
      print '(a,i0,a,f0.6,a,f0.6,a,f0.1,a,f0.1,a,f0.4,a,f0.3,a)', "fault2disp: segment ", k, ": lon ", lon_top(k), ", lat ", &
            lat_top(k), " -> x ", x_top(k), " m, y ", y_top(k), " m; convergence ", gam, " deg, strike (grid) ", strike(k), " deg"
    end do
  end if

  ! --- 各セグメントの最終変位(鉛直 + 水平の ∇z 寄与)を格子で評価 ---
  allocate(uz(nx, ny, nseg), source = 0.0d0)
  if (len_trim(fn_z) > 0) then
    allocate(z(nx, ny), zwk(nx, ny))
    call fileio_read_matrix(trim(fn_z), nx, ny, zwk, f_input_mode)
    z = dble(zwk)
    deallocate(zwk)
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

  ! --- 窓(変位がゼロでない外接矩形。全域格子の列・行) ---
  i1 = 1; i2 = nx; j1 = 1; j2 = ny
  wstr = ''
  if (f_window == 1) then
    i1 = nx + 1; i2 = 0; j1 = ny + 1; j2 = 0
    do k = 1, nseg
      do j = 1, ny
        do i = 1, nx
          if (abs(uz(i, j, k)) > d_min) then
            i1 = min(i1, i); i2 = max(i2, i); j1 = min(j1, j); j2 = max(j2, j)
          end if
        end do
      end do
    end do
    if (i2 < i1) then
      i1 = 1; i2 = 1; j1 = 1; j2 = 1          ! 変位なし: 1 セルの窓
    end if
    write(wstr, '(4(1x,i0))') i1, j1, i2 - i1 + 1, j2 - j1 + 1
    print '(a,i0,a,i0,a,i0,a,i0,a,f0.1,a)', "fault2disp: window columns ", i1, "..", i2, ", rows ", j1, "..", j2, &
          " (", 100.0d0 * dble(i2 - i1 + 1) * dble(j2 - j1 + 1) / (dble(nx) * dble(ny)), "% of the grid)"
  end if

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
    call write_matrix(trim(dir_out)//"/"//trim(fn), d(i1:i2, j1:j2))
    write(un, '(f0.3,2x,a,a)') t, trim(prefix_list)//trim(fn), trim(wstr)
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
    ! 横メルカトル: Krüger 級数と Snyder 級数の照合(UTM 54 帯、東京駅付近)
    proj_lon0 = 141.0d0; proj_lat0 = 0.0d0; proj_k0 = 0.9996d0; proj_fe = 500000.0d0; proj_fn = 0.0d0
    call tm_forward(139.7671d0, 35.6812d0, ux, uy, uz)
    print '(a)', "Transverse Mercator (UTM zone 54, GRS80) at lon 139.7671, lat 35.6812:"
    print '(a,f0.3,a,f0.3,a,f0.5,a)', "  Krueger series : E = ", ux, " m, N = ", uy, " m, convergence = ", uz, " deg"
    call tm_snyder(139.7671d0, 35.6812d0, ux, uy)
    print '(a,f0.3,a,f0.3,a)', "  Snyder series  : E = ", ux, " m, N = ", uy, " m"
    ! 日本の平面直角座標系 IX 系(原点 lon 139°50′, lat 36°、k0 = 0.9999)
    proj_lon0 = 139.0d0 + 50.0d0/60.0d0; proj_lat0 = 36.0d0; proj_k0 = 0.9999d0; proj_fe = 0.0d0; proj_fn = 0.0d0
    call tm_forward(139.7671d0, 35.6812d0, ux, uy, uz)
    print '(a,f0.3,a,f0.3,a,f0.5,a)', "  JGD plane rectangular IX: Y(east) = ", ux, " m, X(north) = ", uy, " m, convergence = ", uz, " deg"
    call tm_snyder(139.7671d0, 35.6812d0, ux, uy)
    print '(a,f0.3,a,f0.3,a)', "  (Snyder)                : Y = ", ux, " m, X = ", uy, " m"
  end subroutine

  !--------------------------------------------------------------------
  ! 横メルカトル(Gauss–Krüger)順変換。Krüger の級数(n の 6 次。Karney 2011)。
  !   (lon, lat) [度] → (x 東距, y 北距) [m]、γ = 子午線収差 [度](格子北の真北からの
  !   方位。中央子午線の東・北半球で正)。原点 (proj_lon0, proj_lat0)、縮尺 k0、偽距。
  !   UTM と日本の平面直角座標系はこの特殊形(平面直角座標系の X は北距、Y は東距
  !   なので、ENCflow の x_ll = Y、y_ll = X)
  !--------------------------------------------------------------------
  subroutine tm_forward(lon, lat, x, y, gam)
    real(dp), intent(in) :: lon, lat
    real(dp), intent(out) :: x, y, gam
    real(dp) :: f, n, a_, al(6), phi, lam, tt, xi, eta, sx, sy, p, q, n0, xi0, s0
    integer :: jj
    f = 1.0d0 / ell_rf
    n = f / (2.0d0 - f)
    a_ = ell_a / (1.0d0 + n) * (1.0d0 + n**2 / 4 + n**4 / 64 + n**6 / 256)
    al(1) = n/2 - 2*n**2/3 + 5*n**3/16 + 41*n**4/180 - 127*n**5/288 + 7891*n**6/37800
    al(2) = 13*n**2/48 - 3*n**3/5 + 557*n**4/1440 + 281*n**5/630 - 1983433*n**6/1935360
    al(3) = 61*n**3/240 - 103*n**4/140 + 15061*n**5/26880 + 167603*n**6/181440
    al(4) = 49561*n**4/161280 - 179*n**5/168 + 6601661*n**6/7257600
    al(5) = 34729*n**5/80640 - 3418889*n**6/1995840
    al(6) = 212378941*n**6/319334400
    phi = lat * deg
    lam = (lon - proj_lon0) * deg
    tt = sinh(atanh(sin(phi)) - 2*sqrt(n)/(1+n) * atanh(2*sqrt(n)/(1+n) * sin(phi)))
    xi = atan2(tt, cos(lam))
    eta = atanh(sin(lam) / sqrt(1 + tt*tt))
    sx = eta; sy = xi; p = 1.0d0; q = 0.0d0
    do jj = 1, 6
      sx = sx + al(jj) * cos(2*jj*xi) * sinh(2*jj*eta)
      sy = sy + al(jj) * sin(2*jj*xi) * cosh(2*jj*eta)
      p = p + 2*jj*al(jj) * cos(2*jj*xi) * cosh(2*jj*eta)
      q = q + 2*jj*al(jj) * sin(2*jj*xi) * sinh(2*jj*eta)
    end do
    ! 原点緯度の子午線弧長(η = 0)
    n0 = sinh(atanh(sin(proj_lat0*deg)) - 2*sqrt(n)/(1+n) * atanh(2*sqrt(n)/(1+n) * sin(proj_lat0*deg)))
    xi0 = atan(n0)
    s0 = xi0
    do jj = 1, 6
      s0 = s0 + al(jj) * sin(2*jj*xi0)
    end do
    x = proj_fe + proj_k0 * a_ * sx
    y = proj_fn + proj_k0 * a_ * (sy - s0)
    gam = (atan(tan(xi) * tanh(eta)) + atan2(q, p)) / deg
  end subroutine

  !--------------------------------------------------------------------
  ! 横メルカトル順変換の別式(Snyder 1987, USGS PP 1395 の級数)。-check の照合用
  !--------------------------------------------------------------------
  subroutine tm_snyder(lon, lat, x, y)
    real(dp), intent(in) :: lon, lat
    real(dp), intent(out) :: x, y
    real(dp) :: f, e2, ep2, phi, lam, nn, tt, cc, aa, mm, m0
    f = 1.0d0 / ell_rf
    e2 = 2*f - f*f
    ep2 = e2 / (1 - e2)
    phi = lat * deg
    lam = (lon - proj_lon0) * deg
    nn = ell_a / sqrt(1 - e2 * sin(phi)**2)
    tt = tan(phi)**2
    cc = ep2 * cos(phi)**2
    aa = lam * cos(phi)
    mm = marc_tm(phi, e2); m0 = marc_tm(proj_lat0 * deg, e2)
    x = proj_fe + proj_k0 * nn * (aa + (1 - tt + cc) * aa**3 / 6 + (5 - 18*tt + tt*tt + 72*cc - 58*ep2) * aa**5 / 120)
    y = proj_fn + proj_k0 * (mm - m0 + nn * tan(phi) * (aa**2 / 2 + (5 - tt + 9*cc + 4*cc*cc) * aa**4 / 24 &
        + (61 - 58*tt + tt*tt + 600*cc - 330*ep2) * aa**6 / 720))
  end subroutine

  ! 子午線弧長(Snyder 3-21)
  function marc_tm(ph, e2) result(mv)
    real(dp), intent(in) :: ph, e2
    real(dp) :: mv
    mv = ell_a * ((1 - e2/4 - 3*e2**2/64 - 5*e2**3/256) * ph - (3*e2/8 + 3*e2**2/32 + 45*e2**3/1024) * sin(2*ph) &
         + (15*e2**2/256 + 45*e2**3/1024) * sin(4*ph) - 35*e2**3/3072 * sin(6*ph))
  end function

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
