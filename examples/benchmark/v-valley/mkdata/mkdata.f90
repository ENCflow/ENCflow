program mkdata
  implicit none
  integer :: nx, ny
  real :: lx, ly
  real :: dx, dy
  real, allocatable :: elev(:,:)
  integer, allocatable :: mask(:,:)
  integer, allocatable :: luse(:,:)
  integer :: j

  dx = 10.
  dy = 10.

  lx = (800. * 2 + 20.)
  ly = lx

  nx = nint(lx / dx)
  ny = nint(ly / dy)
  print *, nx, ny

  allocate(elev(1:nx,1:ny), source=0.0)
  allocate(mask(1:nx,1:ny), source=0)
  allocate(luse(1:nx,1:ny), source=0)

  call  mkdata_main(nx, ny, lx, ly, dx, dy, elev, luse, mask)

  open(1, file='elev.txt')
  open(2, file='mask.txt')
  open(3, file='luse.txt')
  do j = 1, ny
    write(1, '(*(f12.5))') elev(1:nx,j)
    write(2, '(*(i5))') mask(1:nx,j)
    write(3, '(*(i5))') luse(1:nx,j)
  end do
  close(1)
  close(2)
  close(3)


end program

!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine mkdata_main(nx, ny, lx, ly, dx, dy, elev, luse, mask)
  implicit none
  integer :: nx, ny
  real :: lx, ly
  real :: dx, dy
  real, intent(inout) :: elev(1:nx,1:ny)
  integer, intent(inout) :: mask(1:nx,1:ny)
  integer, intent(inout) :: luse(1:nx,1:ny)

  integer :: i, j
  real :: x, y

  real :: z
  integer :: lu
  integer :: msk
  
  do j = 1, ny
    y = j * dy  - dy / 2

    do i = 1, nx
      x = i * dx - dx / 2

      call  get_data(x, y, z, lu, msk)
      elev(i,j) = z
      luse(i,j) = lu
      mask(i,j) = msk

    end do
  end do

end subroutine

!contains
  ! - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
  subroutine get_data(x, y, z, lu, msk)
    real, intent(in) :: x, y
    real, intent(out) :: z
    integer, intent(out) :: lu, msk

    real :: lsx,lcx
    real :: ssx, ssy, scy
    real :: x0, y0, z0
    real :: zc0, zs0

    real :: xx, xxx
    real :: yy, yyy
    real :: zz
    real :: zs, zc

    lsx = 800.0 ! 斜面長
    !lcx = 20.0  ! 水路幅
    lcx = 0.0  ! 水路幅
    scy = 0.02  ! 水路のy方向勾配
    !ssy = 0.0   ! 斜面のy方向勾配
    ssy = 0.02   ! 斜面のy方向勾配
    ssx = 0.03  ! 斜面のx方向勾配
    x0 = 810.0  ! 領域の内部原点のx座標
    y0 = 620.0  ! 領域の内部原点のy座標
    z0 = 0.0    ! 領域の内部原点の標高
    zc0 = z0                         ! 領域下端での水路の標高

    !zs0 = z0 + scy * (1620. - y0) + 1.  ! 領域下端での斜面下端の標高
    zs0 = z0 + scy * (1620. - y0) + 0.  ! 領域下端での斜面下端の標高

    if (y < 0. .or. y > 1620. .or. x < 0 .or. x > 1620) then
      z = 0.
      lu = 0
      msk = 0
    else
      msk = 1
    end if

      yy = y - y0
      yyy = -(yy + y0 / 2)
      if (yyy > 0) then
        zz = zc0 + (- y0 / 2) * scy - yyy / 1000
        z = zz
        lu = 1
        msk = 1
        return
      end if

      zc = zc0 + yy * scy
      zs = zs0 + yy * ssy

      xx = abs(x - x0)
      xxx = xx - lcx / 2
      if (xxx < 0) then
        z = zc
        lu = 1
      else
        z = zs + xxx * ssx
        !if (yy < 0 .and. xxx > 10.) z = z + 5
        lu = 0
      end if

  end subroutine


!end subroutine
