program modify_elevation600
  implicit none
  integer, parameter :: nx = 983
  integer, parameter :: ny = 853
  integer, parameter :: nmod = 16
  !integer :: ixmod(1:nmod)
  !integer :: iymod(1:nmod)
  integer :: imod(1:2,1:nmod)
  real :: z(1:nx,1:ny)
  integer :: i
  integer :: ix, iy
  !real :: a, b

!  ! 修正セルのリストを読み込む
!  open(1, file="correlev600.txt", status='old')
!  do i = 1, nmod
!    print *, i
!    !read(1,*) a, b
!    read(1,'(2i6)') a, b
!    print *, i, a, b
!    read(1,*) ixmod(i), iymod(i)
!    ixmod(i) = ixmod(i) + 1
!    iymod(i) = iymod(i) + 1
!  end do
!  close(1)
  imod(1:2,1) = [666, 237]
  imod(1:2,2) = [666, 238]
  imod(1:2,3) = [666, 239]
  imod(1:2,4) = [666, 240]
  imod(1:2,5) = [666, 241]
  imod(1:2,6) = [665, 239]
  imod(1:2,7) = [665, 240]
  imod(1:2,8) = [665, 241]
  imod(1:2,9) = [665, 237]
  imod(1:2,10) = [664, 237]
  imod(1:2,11) = [664, 238]
  imod(1:2,12) = [663, 238]
  imod(1:2,13) = [663, 239]
  imod(1:2,14) = [662, 239]
  imod(1:2,15) = [662, 240]
  imod(1:2,16) = [662, 241]

  ! 修正前の標高の読み込み
  open(1, file="Elev_filled600.bil", form='unformatted', status='old', access='stream')
  read(1) z
  close(1)

  ! 標高の修正
  do i = 1, nmod
    !ix = ixmod(i)
    !iy = iymod(i)
    ix = imod(1,i)
    iy = imod(2,i)
    print *, i, ix, iy, z(ix,iy)
    z(ix,iy) = z(ix,iy) + 20
    print *, i, ix, iy, z(ix,iy)
  end do

  z(495,617) = 8.0
  z(495,616) = 8.0
  z(494,616) = 8.0
  z(494,615) = 8.0
  z(494,614) = 8.0
  z(494,613) = 8.0
  z(494,612) = 8.0
  z(493,611) = 8.0

  ! 修正済みの標高の書き込み
  open(1, file="Elev_filled600cor.bil", form='unformatted', status='replace', access='stream')
  write(1) z
  close(1)


end program
