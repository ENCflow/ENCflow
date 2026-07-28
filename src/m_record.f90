!======================================================================
module m_record
  ! ================= MPI 化の方針(改良時に読むこと) =================
  ! 計測ロジック(整形・総和・最大値更新・出力)はすべて rank0 上の
  ! 逐次コードのまま維持している。MPI 対応は「セル値の取得」だけを
  ! 点集約バッファ経由に差し替える方式:
  !   (1) 全ランクが所有セル(dcp%js <= iy <= dcp%je)の値をバッファに
  !       格納する(他ランクの要素は 0 のまま)
  !   (2) par_reduce_points で rank0 に総和集約する。各要素の所有者は
  !       ちょうど1ランクなので「総和=所有値」でビット厳密
  !   (3) rank0 が従来ロジックでバッファから読んで整形・出力する
  ! 計測に新しい量を足す手順: 格納ループに1行(wk(k,i) = s%新量(ix,iy))、
  ! バッファの第1次元を +1、読み出し側で wk(k,i) を参照する。この3点だけ。
  ! 注意: (1)(2) は collective なので is_root ガードより前に置くこと。
  !       所有判定に halo 行(jsh..js-1 等)を含めると二重計上になる。
  ! ====================================================================
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use m_parallel, only : is_root
  use m_util, only : itoa
  use list_record, only : t_list_record, list_record_read
  use m_parallel, only : is_root, par_info, par_abort, dcp, par_reduce_points
  implicit none
  private

  public :: t_record
  public :: m_record_init
  public :: m_record_dispose
  public :: m_record_probe
  public :: m_record_flux
  public :: m_record_summary

  integer, parameter :: ncellmax = 1000
  integer, parameter :: nflmax = 1000


  type t_probe
    real :: xy(1:2)                        ! 測点の実座標(m)
    integer :: ixy(1:2)                    ! 測点のセルの座標
    real :: z                              ! 測点の標高
    real :: tp                             ! 最大流量の発生時刻(s)
    real :: qmax                           ! 最大流量
    real :: hmax                           ! 最大流量のときの水深
    integer :: un                          ! 出力ファイルの装置番号
  end type

  type t_flux
    real :: trlen                          ! 測線の長さ(m)
    real :: trnvec(1:2)                    ! 測線の単位法線ベクトル
    real :: xy0(1:4)                       ! 測線の両端点の実座標(m)
    integer :: ixy0(1:4)                   ! 測線の両端点のセルの座標
    integer :: ncell                       ! 測線が通過するセルの数
    integer :: ixy(1:2,1:ncellmax)         ! 測線が通過するセルの座標
    real :: w(1:ncellmax)                  ! セルの重み
    real :: tp                             ! 最大流量の発生時刻(s)
    real :: qmax                           ! 最大流量
    real :: hmax                           ! 最大流量のときの水深
    integer :: un                          ! 出力ファイルの装置番号
  end type

  type t_record
    logical :: initialized = .false.
    real :: ss0                            ! 領域内の水の総量の初期値
    real :: ss                             ! 領域内の水の総量
    integer :: npb                         ! プローブ計測の測点の数
    type(t_probe), allocatable :: probe(:) ! プローブ計測の測点の情報
    integer :: nfl                         ! フラックス計測の測線の数
    type(t_flux), allocatable :: flux(:)   ! フラックス計測の測線の情報
  end type


contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! レコード構造体を初期化
!----------------------------------------------------------------------
subroutine m_record_init(r, p, g)
  type(t_record), intent(out) :: r
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_list_record) :: list
  integer :: pbxytype
  real, allocatable :: pbxy(:,:)
  integer :: flxyfile
  integer :: flxytype
  real :: flxy(1:4,1:nflmax) = -9999

  ! リスト構築・検証は全ランクが冗長に実行する(全ランクが所有セルを
  ! 判定できるようにするため。§11 の「静的データは全ランク保持」)。
  ! ファイルの open とヘッダ出力だけ rank0 に限定する(set_probe/set_flux 内)

  if (len_trim(p%fn_record) > 0) then
    !---- 設定ファイルを読み込む ----
    call list_record_read(p, list)
    pbxytype = list%pbxytype
    pbxy = list%pbxy
    flxyfile = list%flxyfile
    flxytype = list%flxytype

    !---- フラックスの測線データをセット ----
    if (flxyfile > 0) then
      call read_flxy(p, list%fn_flxy, flxy)
    else
      flxy = list%flxy
    end if

    !---- 設定ファイルの情報を構造体に保存 ----
    call set_probe
    call set_flux
    !call set_probe(p)
    !call set_flux(p)
  else
    r%npb = 0
    r%nfl = 0
  end if

  !---- 初期値をセット ---
  r%ss0 = 0.0
  r%ss = 0.0

  r%initialized = .true.

contains
!---------------------------------------------------------------------
subroutine set_probe
!subroutine set_probe(p)
!  type(t_sysparam), intent(in) :: p
  integer :: npb, un
  integer :: i, ix, iy
  real :: x, y
  character(len=80) :: fn_pb
  character(len=4) :: cun
  character(len=1024) :: msg

  !---- プローブ数をカウント ----
  npb = 0
  !do i = 1, size(pbxy, 2)
  do i = 1, ubound(pbxy, 2)
    if (pbxy(1,i) < -999) exit   ! 有効なデータが無い場合は終了
    npb = npb + 1
  end do
  r%npb = npb
  if (npb < 1) return

  !---- プローブ情報を保存 ----
  allocate(r%probe(1:npb))
  do i = 1, npb
    if (pbxytype == 0) then
      ! 設定ファイルでセルの座標を指定
      ix = nint(pbxy(1,i))
      iy = nint(pbxy(2,i))
      x = (ix - 0.5) * g%dx 
      y = (iy - 0.5) * g%dy
    else
      ! 設定ファイルで実座標を指定
      x = pbxy(1,i)
      y = pbxy(2,i)
      ix = int(x / g%dx) + 1
      iy = int(y / g%dy) + 1
    end if
    if (ix < 1 .or. ix > g%nx .or. iy < 1 .or. iy > g%ny) then
      write(msg, '("error: probe ",i0," is out of area.",2f15.2,2i7)') i, x, y, ix, iy
      call par_abort(trim(msg))
    end if
    if (g%x(ix,iy) < 1) then
      write(msg, '("error: probe ",i0," is not in valid area.",2f15.2,2i7)') i, x, y, ix, iy
      call par_abort(trim(msg))
    end if
    r%probe(i)%xy(1) = x
    r%probe(i)%xy(2) = y
    r%probe(i)%ixy(1) = ix
    r%probe(i)%ixy(2) = iy
    r%probe(i)%z = g%z(ix,iy)
    r%probe(i)%tp = 0
    r%probe(i)%qmax = -1.
  end do

  !---- プローブ出力ファイルを初期化(rank0 のみ)----
  if (.not. is_root) return
  do i = 1, r%npb
    ix = r%probe(i)%ixy(1)
    iy = r%probe(i)%ixy(2)
    write(cun, '(i4.4)') i
    fn_pb = trim(p%dir_result)//"/probes/"//"probe"//cun//trim(p%outfn_suffix)//".csv"
    open(newunit=un, file=trim(fn_pb), status='replace')
    write(un, '("# probe number =,",i3)') i
    write(un, '("# x(m) =,",f14.3)') r%probe(i)%xy(1)
    write(un, '("# y(m) =,",f14.3)') r%probe(i)%xy(2)
    write(un, '("# z(m) =,",f14.3)') r%probe(i)%z
    write(un, '("# ix =,",i7)') r%probe(i)%ixy(1)
    write(un, '("# iy =,",i7)') r%probe(i)%ixy(2)
    write(un, '("# t(hour), t(min), z(m), h(m), u(m/s), v(m/s), |V|(m/s), q(m2/s)")')
    r%probe(i)%un = un
  end do
end subroutine

!---------------------------------------------------------------------
!
!---------------------------------------------------------------------
subroutine set_flux
!subroutine set_flux(p)
!  type(t_sysparam), intent(in) :: p
  integer :: nfl, un
  integer :: i, ix0, iy0, ix1, iy1
  real :: x0, y0, x1, y1
  real :: dx, dy, nvx, nvy, nva
  real :: a, b, c!, d
  integer :: ix, iy, ncell, ixa, ixb, iya, iyb
  real :: xa, xb, ya, yb, xc, yc
  real :: wa, wb, ww
  character(len=80) :: fn_fl
  character(len=4) :: cun
  character(len=1024) :: msg
  integer :: j

  !---- フラックス計測の測線数をカウント ----
  nfl = 0
  do i = 1, ubound(flxy, 2)
    if (flxy(1,i) < -999) exit   ! 有効なデータが無い場合は終了
    nfl = nfl + 1
  end do
  r%nfl = nfl
  if (nfl < 1) return

  !---- 測線情報を保存 ----
  allocate(r%flux(1:nfl))
  do i = 1, nfl
    if (flxytype == 0) then
      ! 設定ファイルでセルの座標を指定
      ix0 = nint(flxy(1,i))
      iy0 = nint(flxy(2,i))
      ix1 = nint(flxy(3,i))
      iy1 = nint(flxy(4,i))
      x0 = (ix0 - 0.5) * g%dx 
      y0 = (iy0 - 0.5) * g%dy
      x1 = (ix1 - 0.5) * g%dx 
      y1 = (iy1 - 0.5) * g%dy
    else
      ! 設定ファイルで実座標を指定
      x0 = flxy(1,i)
      y0 = flxy(2,i)
      x1 = flxy(3,i)
      y1 = flxy(4,i)
      ix0 = int(x0 / g%dx) + 1
      iy0 = int(y0 / g%dy) + 1
      ix1 = int(x1 / g%dx) + 1
      iy1 = int(y1 / g%dy) + 1
    end if
    if (ix0 < 1 .or. ix0 > g%nx .or. iy0 < 1 .or. iy0 > g%ny) then
      write(msg, '("error: point R of flux ",i0," is out of area.",2f15.2,2i7)') i, x0, y0, ix0, iy0
      call par_abort(trim(msg))
    end if
    if (ix1 < 1 .or. ix1 > g%nx .or. iy1 < 1 .or. iy1 > g%ny) then
      write(msg, '("error: point L flux ",i0," is out of area.",2f15.2,2i7)') i, x1, y1, ix1, iy1
      call par_abort(trim(msg))
    end if
    if (g%x(ix0,iy0) < 1) then
      write(msg, '("warning: point R of flux ",i0," is not in valid area.",2f15.2,2i7)') i, x0, y0, ix0, iy0
      call par_info(trim(msg))
    end if
    if (g%x(ix1,iy1) < 1) then
      write(msg, '("warning: point L flux ",i0," is not in valid area.",2f15.2,2i7)') i, x1, y1, ix1, iy1
      call par_info(trim(msg))
    end if


    dx = x1 - x0
    dy = y1 - y0
    ! 測線の法線ベクトルを計算
    ! 始点から終点に向かって右側が正
    nvx = -dy
    nvy = dx
    nva = sqrt(nvx**2 + nvy**2)
    if (nva <= 0.0) then
      call par_info("warning: point A == point B then IGNORE, flux No."//itoa(i))
      r%flux(i)%xy0(1) = x0
      r%flux(i)%xy0(2) = y0
      r%flux(i)%xy0(3) = x1
      r%flux(i)%xy0(4) = y1
      r%flux(i)%ixy0(1) = ix0
      r%flux(i)%ixy0(2) = iy0
      r%flux(i)%ixy0(3) = ix1
      r%flux(i)%ixy0(4) = iy1
      r%flux(i)%ncell = 0       ! これを1でなく0にしておく
      r%flux(i)%trlen = 0.0
      r%flux(i)%tp = 0
      r%flux(i)%qmax = 0.
      cycle
    end if
    nvx = nvx / nva
    nvy = nvy / nva
    r%flux(i)%trnvec(1) = nvx
    r%flux(i)%trnvec(2) = nvy
    ! a*x + b*y + c = 0
    ! y = -a/b*x - c/b
    ! x = -b/a*y - c/a
    a = y1 - y0
    b = x0 - x1
    c = x1 * y0 - x0 * y1
    if (abs(dx) >= abs(dy)) then
      ! 測線をセルの範囲いっぱいまで延長する
      ! 実座標を指定した場合はそのまま
      !   *** その場合のウェイトが現状では正しくない ***
      if (flxytype == 0) then
        if (x0 < x1) then
          x0 = (ix0 - 1) * g%dx
          x1 = ix1 * g%dx
        else
          x1 = (ix1 - 1) * g%dx
          x0 = ix0 * g%dx
        end if
        y0 = -a / b * x0 - c / b
        y1 = -a / b * x1 - c / b
      end if
      ncell = 0
      ! x方向に刻みながら処理
      do ix = ix0, ix1, sign(1, ix1 - ix0)
        ncell = ncell + 1
        xa = (ix - 1) * g%dx           ! セルの左端のx座標
        xb = ix * g%dx                 ! セルの右端のx座標
        ya = -a / b * xa - c / b       ! セルの左端での測線のy座標
        yb = -a / b * xb - c / b       ! セルの右端での測線のy座標
        iya = int(ya / g%dy) + 1       ! セルの右端での測線のy方向セル番号
        iyb = int(yb / g%dy) + 1       ! セルの左端での測線のy方向セル番号
        r%flux(i)%ixy(1,ncell) = ix
        r%flux(i)%ixy(2,ncell) = iya
        if (iya /= iyb) then           ! 測線がセル境界を跨ぐ
          ncell = ncell + 1
          r%flux(i)%ixy(1,ncell) = ix
          r%flux(i)%ixy(2,ncell) = iyb
          yc = ((iya + iyb) / 2. - 0.5) * g%dy  ! セル境界のy座標
          wa = abs(ya - yc)
          wb = abs(yb - yc)
          ww = wa + wb
          r%flux(i)%w(ncell-1) = wa / ww
          r%flux(i)%w(ncell) = wb / ww
        else
          r%flux(i)%w(ncell) = 1
        end if
      end do
    else
      ! 測線をセルの範囲いっぱいまで延長する
      ! 実座標を指定した場合はそのまま
      !   *** その場合のウェイトが現状では正しくない ***
      if (flxytype == 0) then
        if (y0 < y1) then
          y0 = (iy0 - 1) * g%dy
          y1 = iy1 * g%dy
        else
          y1 = (iy1 - 1) * g%dy
          y0 = iy0 * g%dy
        end if
                             xa = (ix0 - 1) * g%dx           ! セルの左端のx座標
                             xb = ix0 * g%dx                 ! セルの右端のx座標
        x0 = -b / a * y0 - c / a
        x1 = -b / a * y1 - c / a
        iya = int(xa / g%dx) + 1
        iyb = int(xb / g%dx) + 1
      end if
      ncell = 0
      ! y方向に刻みながら処理
      do iy = iy0, iy1, sign(1, iy1 - iy0)
        ncell = ncell + 1
        ya = (iy - 1) * g%dy           ! セルの下端のy座標
        yb = iy * g%dy                 ! セルの上端のy座標
        xa = -b / a * ya - c / a       ! セルの下端での測線のx座標
        xb = -b / a * yb - c / a       ! セルの上端での測線のx座標
        ixa = int(xa / g%dx) + 1       ! セルの下端での測線のx方向セル番号
        ixb = int(xb / g%dx) + 1       ! セルの上端での測線のx方向セル番号
        r%flux(i)%ixy(1,ncell) = ixa
        r%flux(i)%ixy(2,ncell) = iy
        if (ixa /= ixb) then           ! 測線がセル境界を跨ぐ
          ncell = ncell + 1
          r%flux(i)%ixy(1,ncell) = ixb
          r%flux(i)%ixy(2,ncell) = iy
          xc = ((ixa + ixb) / 2. - 0.5) * g%dx  ! セル境界のx座標
          wa = abs(xa - xc)
          wb = abs(xb - xc)
          ww = wa + wb
          r%flux(i)%w(ncell-1) = wa / ww
          r%flux(i)%w(ncell) = wb / ww
        else
          r%flux(i)%w(ncell) = 1
        end if
      end do
    end if

    ! 各セルの測線全体の中でのウェイトを計算
    ww = 0
    do j = 1, ncell
      ww = ww + r%flux(i)%w(j)
    end do
    if (ww > 0) then
      do j = 1, ncell
        r%flux(i)%w(j) = r%flux(i)%w(j) / ww
      end do
    end if

    r%flux(i)%xy0(1) = x0
    r%flux(i)%xy0(2) = y0
    r%flux(i)%xy0(3) = x1
    r%flux(i)%xy0(4) = y1
    r%flux(i)%ixy0(1) = ix0
    r%flux(i)%ixy0(2) = iy0
    r%flux(i)%ixy0(3) = ix1
    r%flux(i)%ixy0(4) = iy1
    r%flux(i)%ncell = ncell
    r%flux(i)%trlen = sqrt((x0 - x1)**2 + (y0 - y1)**2)
    r%flux(i)%tp = 0
    r%flux(i)%qmax = -1.
  end do

  !---- フラックス計測出力ファイルを初期化(rank0 のみ)----
  if (.not. is_root) return
  do i = 1, r%nfl
    write(cun, '(i4.4)') i
    fn_fl = trim(p%dir_result)//"/fluxes/"//"flux"//cun//trim(p%outfn_suffix)//".csv"
    open(newunit=un, file=trim(fn_fl), status='replace')
    write(un, '("# flux transect number =,",i3)') i
    write(un, '("# xR, yR, xL, yL(m) =,",f14.3,",",f14.3,",",f14.3,",",f14.3)') r%flux(i)%xy0(1:4)
    write(un, '("# ixR, iyR, ixL, iyL =,",i7,",",i7,",",i7,",",i7)') r%flux(i)%ixy0(1:4)
    write(un, '("# length of transect(m) =,",f14.3)') r%flux(i)%trlen
    write(un, '("# t(hour), t(min), Q(m3/s), Hmax(m), Vmax(m/s), B(m)(=Q/Hmax/Vmax)")')
    r%flux(i)%un = un
  end do
end subroutine

end subroutine m_record_init

!----------------------------------------------------------------------
! フラックスの測線ファイルを読み込む
!----------------------------------------------------------------------
subroutine read_flxy(p, fn_flxy, flxy)
  type(t_sysparam), intent(in) :: p
  character(len=*), intent(in) :: fn_flxy
  real, intent(inout) :: flxy(1:4,1:nflmax)
  character(:), allocatable :: fname
  integer :: un
  integer :: i, n
  integer :: ios

  fname = trim(p%dir_data)//"/"//trim(fn_flxy)
  open(newunit=un, file=fname, status='old')

  n = 0
  do
    read(un, * , iostat=ios)
    if (ios < 0) exit
    n = n + 1
  end do
  rewind(un)

  if (n > nflmax) then
    call par_abort("Error: too many flux transect"//itoa(n))
  end if

  flxy(:,:) = -9999           ! パラメータファイルの情報を上書きして初期化する
  call par_info(" reading "//fname)
  do i = 1, n
    read(un, *) flxy(1,i), flxy(2,i), flxy(3,i), flxy(4,i)
  end do
  close(un)

end subroutine


!----------------------------------------------------------------------
! レコード構造体を破棄
!----------------------------------------------------------------------
subroutine m_record_dispose(r)
  type(t_record), intent(inout) :: r
  integer :: i

  ! ファイルを開いているのは rank0 のみ。リストは全ランクが保持している
  if (is_root) then
    do i = 1, r%npb
      close(r%probe(i)%un)
    end do
    do i = 1, r%nfl
      close(r%flux(i)%un)
    end do
  end if
  if (allocated(r%probe)) deallocate(r%probe)
  if (allocated(r%flux)) deallocate(r%flux)
end subroutine

!----------------------------------------------------------------------
! プローブ計測の情報を記録
!----------------------------------------------------------------------
subroutine m_record_probe(r, p, s)
  type(t_record), intent(inout) :: r
  type(t_sysparam), intent(in) :: p
  type(t_state), intent(in) :: s
  integer :: ipb, un
  integer :: ix, iy
  real :: wk(5, r%npb)     ! 点集約バッファ: h, u, v, |V|, q
  character(len=10) :: ffmt
  character(len=80) :: afmt
  if (p%initialized) continue  ! 引数未使用の警告を抑制

  if (r%npb <= 0) return

  ! --- 全ランク: 所有セルの値を詰めて rank0 に点集約(collective) ---
  wk = 0.0
  do ipb = 1, r%npb
    ix = r%probe(ipb)%ixy(1)
    iy = r%probe(ipb)%ixy(2)
    if (dcp%js <= iy .and. iy <= dcp%je) then
      wk(1,ipb) = s%h(ix,iy)
      wk(2,ipb) = s%u(ix,iy)
      wk(3,ipb) = s%v(ix,iy)
      wk(4,ipb) = s%vv(ix,iy)
      wk(5,ipb) = s%qq(ix,iy)
    end if
  end do
  call par_reduce_points(wk)

  ! --- 以下は従来の逐次ロジック(セル値の参照だけ wk 経由) ---
  if (.not. is_root) return

  do ipb = 1, r%npb
    un = r%probe(ipb)%un
    !if (p%dble_precision) then
    !  ffmt = 'f22.16'
    !else
      ffmt = "f14.5"
    !end if
    afmt = "("//trim(ffmt)//")"
    write(un, afmt, advance='no') s%t / 3600
    write(un, '(a)', advance='no') ","
    write(un, afmt, advance='no') s%t / 60
    write(un, '(a)', advance='no') ","
    write(un, afmt, advance='no') r%probe(ipb)%z
    write(un, '(a)', advance='no') ","
    write(un, afmt, advance='no') wk(1,ipb)
    write(un, '(a)', advance='no') ","
    write(un, afmt, advance='no') wk(2,ipb)
    write(un, '(a)', advance='no') ","
    write(un, afmt, advance='no') wk(3,ipb)
    write(un, '(a)', advance='no') ","
    write(un, afmt, advance='no') wk(4,ipb)
    write(un, '(a)', advance='no') ","
    write(un, afmt, advance='no') wk(5,ipb)
    write(un, *)
    if (wk(5,ipb) > r%probe(ipb)%qmax) then
      r%probe(ipb)%tp = s%t / 60.
      r%probe(ipb)%qmax = wk(5,ipb)
      r%probe(ipb)%hmax = wk(1,ipb)
    end if
  end do
end subroutine

!----------------------------------------------------------------------
! フラックス計測の情報を記録
!----------------------------------------------------------------------
subroutine m_record_flux(r, p, s)
  type(t_record), intent(inout) :: r
  type(t_sysparam), intent(in) :: p
  type(t_state), intent(in) :: s
  integer :: ifl, un, ncell
  integer :: i, ix, iy
  real :: vn, qi, qm, q
  real :: hmax, vmax, b
  real, parameter :: eps = 1.0e-5
  real, allocatable :: wk(:,:)   ! 点集約バッファ: (4, ncell) = m, n, h, |V|
  character(len=10) :: ffmt
  character(len=80) :: afmt
  type(t_flux) :: flx
  if (p%initialized) continue  ! 引数未使用の警告を抑制

  if (r%nfl <= 0) return

  do ifl = 1, r%nfl
    flx = r%flux(ifl)
    un = flx%un
    ncell = flx%ncell

    ! --- 全ランク: 測線上の所有セルの値を詰めて rank0 に点集約(collective) ---
    allocate(wk(4, ncell), source = 0.0)
    do i = 1, ncell
      ix = flx%ixy(1,i)
      iy = flx%ixy(2,i)
      if (dcp%js <= iy .and. iy <= dcp%je) then
        wk(1,i) = s%m(ix,iy)
        wk(2,i) = s%n(ix,iy)
        wk(3,i) = s%h(ix,iy)
        wk(4,i) = s%vv(ix,iy)
      end if
    end do
    call par_reduce_points(wk)

    ! --- 以下は従来の逐次ロジック(セル値の参照だけ wk 経由) ---
    if (.not. is_root) then
      deallocate(wk)
      cycle
    end if

    qm = 0.0
    hmax = 0.0
    vmax = 0.0
    b = 0.
    do i = 1, ncell
      vn = wk(1,i) * flx%trnvec(1) + wk(2,i) * flx%trnvec(2)   ! 測線の法線方向線流量
      qi = vn
      qm = qm + qi * flx%w(i)
      hmax = max(wk(3,i), hmax)
      vmax = max(wk(4,i), vmax)
    end do
    deallocate(wk)
    q = qm * flx%trlen
    if (hmax * vmax > 0.0) b = abs(q / hmax / vmax)

    ffmt = "f13.4"
    afmt = "("//trim(ffmt)//")"
    write(un, afmt, advance='no') s%t / 3600
    write(un, '(a)', advance='no') ","
    write(un, afmt, advance='no') s%t / 60
    write(un, '(a)', advance='no') ","
    write(un, afmt, advance='no') q
    write(un, '(a)', advance='no') ","
    write(un, afmt, advance='no') hmax
    write(un, '(a)', advance='no') ","
    write(un, afmt, advance='no') vmax
    write(un, '(a)', advance='no') ","
    write(un, afmt, advance='no') b
    write(un, *)
    if (q > r%flux(ifl)%qmax) then
      r%flux(ifl)%tp = s%t / 60.
      r%flux(ifl)%qmax = q
      r%flux(ifl)%hmax = hmax
    end if
  end do

end subroutine


!----------------------------------------------------------------------
! 最大流量の一覧を出力
!----------------------------------------------------------------------
subroutine m_record_summary(r, p)
  type(t_record), intent(in) :: r
  type(t_sysparam), intent(in) :: p
  integer :: un
  integer :: i
  character(len=80) :: fn_smry

  if (.not. is_root) return

  if (r%npb <= 0 .and. r%nfl <= 0) return

  fn_smry = trim(p%dir_result)//"/"//"summary"//trim(p%outfn_suffix)//".csv"
  open(newunit=un, file=trim(fn_smry), status='replace')
  write(un, '("# type, No., t(hour), t(min), Qmax(m3/s), Hmax(m), ixR, iyR, ixL, iyL")')
  do i = 1, r%npb
    write(un, '(a,i5,a,f11.5,a,f14.5,a,f14.5,a,f12.5,a,i7,a,i7)') &
            "probe,", i, ",", r%probe(i)%tp / 60.0, ",", r%probe(i)%tp, ",", &
            r%probe(i)%qmax, ",", r%probe(i)%hmax, ",", &
            r%probe(i)%ixy(1), ",", r%probe(i)%ixy(2)
  end do
  do i = 1, r%nfl
    write(un, '(a,i5,a,f11.5,a,f14.5,a,f14.5,a,f12.5,a,i7,a,i7,a,i7,a,i7)') &
            "flux,", i, ",", r%flux(i)%tp / 60.0, ",", r%flux(i)%tp, ",", &
            r%flux(i)%qmax, ",", r%flux(i)%hmax, ",", &
            r%flux(i)%ixy0(1), ",", r%flux(i)%ixy0(2), ",", &
            r%flux(i)%ixy0(3), ",", r%flux(i)%ixy0(4)
  end do

  close(un)
end subroutine

!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

end module
