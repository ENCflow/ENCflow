!=======================================================================
!
! [4] 落水方向データから集水面積を計算する
!     降水分布データと合わせて累積流量を計算する
!
!   入力データ
!     Dd0000.bil: 流向 (1~8)
!     Exprecip.bil: 降水量 (mm)
!
!   出力データ
!     Ca0000.bil: 集水面積 (cell)
!     Cq0000.bil: 累積流量 (m*cell)
!
!-----------------------------------------------------------------------
!
! [1] mkdowndir:  卓越流下方向データから落水方向データを作成
! [2] chkdowndir: 落水方向データの連続性を確認・修正
! [3] calcarea:   落水方向データから集水面積と累積雨量を計算
! [4] pickuparea: 測線リストから観測点の集水面積と累積雨量を計算
!
!=======================================================================
module mod_pickuparea
  implicit none
  private
  public :: do_main

  type t_transect
    integer :: id        ! 測線番号
    integer :: x0, y0    ! 測線の始点
    integer :: x1, y1    ! 測線の終点
    integer :: nr        ! 河道セルの数 (cell)
    integer :: idir      ! 測線の方向
    integer :: ca        ! 集水面積 (cell)
    real :: cq           ! 累積流量 (m*cell)
  end type

  integer, parameter :: nx = 6080
  integer, parameter :: ny = 8960

  integer, parameter :: idir_ew = 1
  integer, parameter :: idir_ns = 2

  integer, parameter :: din(1:8) = [ -1,  0,  1, -1,  1, -1,  0,  1]
  integer, parameter :: djn(1:8) = [ -1, -1, -1,  0,  0,  1,  1,  1]

contains
!=======================================================================
subroutine do_main
  integer, allocatable :: dd(:,:)       ! 流下方向
  integer, allocatable :: ca(:,:)       ! 集水面積 (cell)
  real, allocatable :: cq(:,:)          ! 累積流量 (m*cell)
  integer, allocatable :: rw(:,:)       ! 河道マスク
  type(t_transect), allocatable :: t(:)

  allocate(dd(1:nx,1:ny), source = 0)
  allocate(ca(1:nx,1:ny), source = 0)
  allocate(cq(1:nx,1:ny), source = 0.0)
  allocate(rw(1:nx,1:ny), source = 0)

  ! 落水方向ファイルの読み込み
  print *, "Reading Dd0000.bil"
  open(1, file="result/Dd0000.bil", form='unformatted', status='old', access='stream')
  read(1) dd
  close(1)

  ! 集水面積ファイルの読み込み
  print *, "Reading Ca0000.bil"
  open(1, file="result/Ca0000.bil", form='unformatted', status='old', access='stream')
  read(1) ca
  close(1)

  ! 累積流量ファイルの読み込み
  print *, "Reading Cq0000.bil"
  open(1, file="result/Cq0000.bil", form='unformatted', status='old', access='stream')
  read(1) cq
  close(1)

  ! 河道マスクファイルの読み込み
  print *, "Reading RiverMask.bil"
  open(1, file="data/RiverMask_20251127.bil", form='unformatted', status='old', access='stream')
  read(1) rw
  close(1)

  ! 測線ファイルの読み込み
  block
    integer :: i, n
    open(1, file='data/flxy_20251127.csv', status='old')
    n = 0
    do
      read(1, *, end=99)
      n = n + 1
    end do
    99 continue
    rewind(1)
    allocate(t(1:n))
    do i = 1, n
      read(1, *) t(i)%x0, t(i)%y0, t(i)%x1, t(i)%y1
    end do
    close(1)
  end block

  ! 測線の集水面積と累積流量を計算
  block
    integer :: i
    do i = 1, size(t)
      t(i)%id = i
      call pickup_area(dd, ca, cq, rw, t(i))
      !print *, i, t(i)%nr, t(i)%ca, t(i)%cq
    end do
  end block

  ! 結果の書き込み
  block
    integer :: i
    print *, "Writing CatchmentArea.csv"
    open(1, file='result/CatchmentArea.csv', status='replace')
    write(1, '(a)') "# No., Area (cell), Cumulative Discharge (m*cell)"
    do i = 1, size(t)
      write(1, '(i5,a,i10,a,f15.3)') i, ",", t(i)%ca, ",", t(i)%cq
    end do
    close(1)
  end block


end subroutine


!-----------------------------------------------------------------------
! 集水面積の計算
!-----------------------------------------------------------------------
subroutine pickup_area(dd, ca, cq, rw, t)
  integer, intent(in) :: dd(1:nx,1:ny)      ! 落水方向
  integer, intent(in) :: ca(1:nx,1:ny)      ! 集水面積 (cell)
  real, intent(in) :: cq(1:nx,1:ny)         ! 累積流量 (m*cell)
  integer, intent(in) :: rw(1:nx,1:ny)      ! 河道マスク
  type(t_transect), intent(inout) :: t      ! 測線
  integer :: i, j
  integer :: nr, idir
  integer :: ddr, in, jn

  nr = count_rw(rw, t)                    ! 河道セルの数をカウント
  idir = check_idir(t)                    ! 測線の向きを確認

  t%nr = nr
  t%idir = idir
  t%ca = 0
  t%cq = 0.0
  do j = t%y0, t%y1, sign(1, t%y1 - t%y0)
    do i = t%x0, t%x1, sign(1, t%x1 - t%x0)
      if (rw(i,j) == 0 .and. nr > 0) cycle   ! 河道以外は無視、ただし河道がゼロの測線は全て加算
      ! 測線上で同じ流線のセルを重複して加算しないように
      ddr = dd(i,j)
      in = i + din(ddr)
      jn = j + djn(ddr)
      if (idir == idir_ew .and. (ddr == 4 .or. ddr == 5) .and. rw(in,jn) > 0) then
        !print *, "XXXXX", t%d
      end if
      if (idir == idir_ns .and. (ddr == 2 .or. ddr == 7) .and. rw(in,jn) > 0) then
        !print *, "YYYYY", t%d
      end if
      t%ca = t%ca + ca(i,j)
      t%cq = t%cq + cq(i,j)
    end do
  end do

end subroutine

!-----------------------------------------------------------------------
! 測線上の河道セルの数を計算
!-----------------------------------------------------------------------
function count_rw(rw, t) result(nr)
  integer, intent(in) :: rw(1:nx,1:ny)   ! 河道マスク
  type(t_transect), intent(in) :: t      ! 測線
  integer :: nr
  integer :: i, j
  nr = 0
  do j = t%y0, t%y1, sign(1, t%y1 - t%y0)
    do i = t%x0, t%x1, sign(1, t%x1 - t%x0)
      if (rw(i,j) > 0) nr = nr + 1
    end do
  end do
end function

!-----------------------------------------------------------------------
! 測線の向きを確認
!-----------------------------------------------------------------------
function check_idir(t) result(idir)
  type(t_transect), intent(in) :: t      ! 測線
  integer :: idir
  if (abs(t%x0 - t%x1) > 0 .and. t%y0 == t%y1) then
    idir = idir_ew
  else if (abs(t%y0 - t%y1) > 0 .and. t%x0 == t%x1) then
    idir = idir_ns
  else
    print *, "Error, invalid transect direction", t%id, t%x0, t%y0, t%x1, t%y1
    stop
  end if
end function


!-----------------------------------------------------------------------
end module

!=======================================================================
!=======================================================================
program pickuparea
  use mod_pickuparea
  call do_main
end program
