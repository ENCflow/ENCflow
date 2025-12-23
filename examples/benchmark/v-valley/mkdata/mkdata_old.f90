program mkdata
  implicit none
  integer :: nx, ny
  real :: dx, dy
  real :: lsx = 800.
  real :: lcx = 20.
  real :: lx = 800. * 2 + 20.
  real :: ly = 1620.
  real :: ssx, ssy
  real :: scy
  real :: z0 = 0.0
  real :: y0 = 620.0
  integer :: i, j
  real :: x, y
  real :: zc0, zc
  real :: zs0, zs
  real :: zz
  real :: yy
  integer :: lu
  real, allocatable :: z(:,:)
  integer, allocatable :: mask(:,:)
  integer, allocatable :: luse(:,:)

  dx = 2.
  dy = 2.

  scy = 0.02
  ssy = 0.0
  ssx = 0.05

  zc0 = z0
  zs0 = z0 + scy * (ly - y0) + 1.

  nx = nint(lx / dx)
  ny = nint(ly / dy)

  allocate(z(1:nx,1:ny), source=0.0)
  allocate(mask(1:nx,1:ny), source=0)
  allocate(luse(1:nx,1:ny), source=0)

  print *, nx, ny

  do j = 1, ny
    y = (j * dy  - dy / 2) - y0
    zc = zc0 + y * scy
    zs = zs0 + y * ssy
    do i = 1, nx
      x = (i * dx - dx / 2)
      if (x < lsx) then
        zz = zs + (lsx - x) * ssx
        lu = 0
      else if (x < lsx + lcx) then
        zz = zc
        lu = 1
      else
        zz = zs + (x - lsx - lcx) * ssx
        lu = 0
      end if
      yy = -(y + y0 / 2)
      !if (y < - y0 / 2) then
      if (yy > 0) then
        !zz = zc0 + (- y0 / 2) * scy
        zz = zc0 + (- y0 / 2) * scy - yy / 1000
      end if
      z(i,j) = zz
      mask(i,j) = 1
      luse(i,j) = lu
    end do
  end do

  open(1, file='elev.txt')
  open(2, file='mask.txt')
  open(3, file='luse.txt')
  do j = 1, ny
    write(1, '(*(f12.5))') z(1:nx,j)
    write(2, '(*(i5))') mask(1:nx,j)
    write(3, '(*(i5))') luse(1:nx,j)
  end do
  close(1)
  close(2)
  close(3)


end program
