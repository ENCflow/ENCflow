!=======================================================================
!
! [3] 落水方向データから集水面積を計算する
!     降水分布データと合わせて累積流量を計算する
!
!   入力データ
!     Dd0000.bil: 流向 (1~8)
!     Exprecip.bil: 降水量 (任意)
!
!   出力データ
!     Ca0000.bil: 集水面積 (セル数)
!     Cq0000.bil: 累積流量 (降水の単位)
!
!-----------------------------------------------------------------------
!
! [1] mkdowndir:  卓越流下方向データから落水方向データを作成
! [2] chkdowndir: 落水方向データの連続性を確認・修正
! [3] calcarea:   落水方向データから集水面積と累積雨量を計算
! [4] pickuparea: 測線リストから観測点の集水面積と累積雨量を計算
!
!=======================================================================
module mod_calcarea
  implicit none
  private
  public :: do_main

  integer, parameter :: nx = 6080
  integer, parameter :: ny = 8960

  integer, parameter :: din(1:8) = [ -1,  0,  1, -1,  1, -1,  0,  1]
  integer, parameter :: djn(1:8) = [ -1, -1, -1,  0,  0,  1,  1,  1]

contains
!=======================================================================
subroutine do_main
  integer, allocatable :: dd(:,:)     ! 流下方向
  real, allocatable :: pr(:,:)        ! 降水量(mm)
  integer, allocatable :: ca(:,:)     ! 集水面積(cell)
  real*8, allocatable :: cq(:,:)      ! 累積流量(m*cell)
  real, allocatable :: cqs(:,:)       ! 累積流量単精度出力用(m*cell)
  integer :: sa                       ! 海への総面積(cell)
  real*8 :: sq                        ! 海への総流量(m*cell)

  allocate(dd(1:nx,1:ny), source = 0)
  allocate(pr(1:nx,1:ny), source = 0.0)
  allocate(ca(1:nx,1:ny), source = 0)
  allocate(cq(1:nx,1:ny), source = 0.d0)
  allocate(cqs(1:nx,1:ny), source = 0.0)

  ! 落水方向ファイルの読み込み
  print *, "Reading Dd0000.bil"
  open(1, file="result/Dd0000.bil", form='unformatted', status='old', access='stream')
  read(1) dd
  close(1)

  ! 降水量ファイルの読み込み
  print *, "Reading Exprecip.bil"
  open(1, file="data/Exprecip_200y_IDW_rev0507_mask.bil", form='unformatted', status='old', access='stream')
  read(1) pr
  close(1)

  call calc_calcarea(dd, pr, ca, cq, sa, sq)
  call check_sum(dd, pr, sa, sq)

  ! 集水面積ファイルの書き込み
  print *, "Writing Ca0000.bil"
  open(1, file="result/Ca0000.bil", form='unformatted', status='replace', access='stream')
  write(1) ca
  close(1)

  ! 累積流量ファイルの書き込み
  print *, "Writing Cq0000.bil"
  cqs(:,:) = real(cq(:,:))
  open(1, file="result/Cq0000.bil", form='unformatted', status='replace', access='stream')
  write(1) cqs
  close(1)



end subroutine


!-----------------------------------------------------------------------
! 集水面積の計算
!-----------------------------------------------------------------------
subroutine calc_calcarea(dd, pr, ca, cq, sa, sq)
  integer, intent(in) :: dd(1:nx,1:ny)      ! 落水方向
  real, intent(in) :: pr(1:nx,1:ny)         ! 降水量 (mm)
  integer, intent(out) :: ca(1:nx,1:ny)     ! 集水面積 (cell)
  real*8, intent(out) :: cq(1:nx,1:ny)      ! 累積流量 (m*cell)
  integer, intent(out) :: sa                ! 海への総面積 (cell)
  real*8, intent(out) :: sq                 ! 海への総流量 (m*cell)
  integer :: i, j, k
  integer :: ic, jc, in, jn
  integer :: a
  real*8 :: q

  sa = 0
  sq = 0.d0

  do j = 1, ny
    if (mod(j, 100) == 0) print *, j
    do i = 1, nx
      if (dd(i,j) < 0) cycle
      ic = i
      jc = j
      a = 0
      q = 0.d0
      do
        if (ca(ic,jc) == 0) then
          a = a + 1
          q = q + dble(pr(ic,jc)) / 1000
        end if
        ca(ic,jc) = ca(ic,jc) + a
        cq(ic,jc) = cq(ic,jc) + q
        k = dd(ic,jc)
        in = ic + din(k)
        jn = jc + djn(k)
        if (dd(in,jn) < 0) then
          sa = sa + a
          sq = sq + q
          exit
        else
          ic = in
          jc = jn
        end if
      end do
    end do
  end do

end subroutine

!-----------------------------------------------------------------------
! 総面積と総流量のチェック
!-----------------------------------------------------------------------
subroutine check_sum(dd, pr, sa, sq)
  integer, intent(in) :: dd(1:nx,1:ny)     ! 落水方向
  real, intent(in) :: pr(1:nx,1:ny)        ! 降水量 (mm)
  integer, intent(in) :: sa                ! 海への総面積 (cell)
  real*8, intent(in) :: sq                 ! 海への総流量 (m*cell)
  integer :: sa0
  real*8 :: sq0
  integer :: i, j

  sa0 = 0
  sq0 = 0.d0
  do j = 1, ny
    do i = 1, nx
      if (dd(i,j) < 0) cycle
      sa0 = sa0 + 1
      sq0 = sq0 + dble(pr(i,j)) / 1000
    end do
  end do

  print *, sa0, sa
  print *, sq0, sq

end subroutine


!-----------------------------------------------------------------------
end module

!=======================================================================
!=======================================================================
program calcarea
  use mod_calcarea
  call do_main
end program
