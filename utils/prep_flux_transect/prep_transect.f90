!
! 測線データを修正する
!
!  単独セルの測線を流路と交差する方向に拡張する
!  右岸から左岸に向かい始点・終点となるようにするために流向データを使用する
!  卓越流下方向データでは必ずしも河道全体の流下方向を反映しないためダメ
!
module m_prep_transect
  implicit none
  private
  public :: do_main

  integer, parameter :: nx = 6080
  integer, parameter :: ny = 8960

  type t_transect
    integer :: id       ! ID
    integer :: x, y     ! 流向判断の基準点
    integer :: x0, y0   ! 測線の始点
    integer :: x1, y1   ! 測線の終点
    integer :: n        ! 測線のセル数
    integer :: nr       ! 測線中の河道セル数
  end type

  integer :: rw(1:nx,1:ny)                   ! 河道マスク
  real :: qd(1:nx,1:ny)                      ! 流向(-π ~ π)

contains
!=======================================================================
!=======================================================================
subroutine do_main
  type(t_transect), allocatable :: tt(:)      ! 測線データ


  call read_rw("RiverMask_20251127.bil")            ! 河道マスクを読み込む
  call read_qd("Qd9998.bil")                        ! 流向データを読み込む
  call read_field(tt, "field_rev.csv")              ! 測線データを読み込む
  call mk_ft(tt, "Field_20251127.bil")              ! 修正前の測線マップを出力

  ! No.63は河道でなく、かつ1セルのため
  ! 機械的に方向を決めることができない
  ! そのため目視で終点を北に1セルずらすこととした
  tt(63)%y1 = tt(63)%y0 - 1

  call modify(tt)                                   ! 測線を拡張する
  call chk_dir(tt)                                  ! 流向に合わせて測線の向きを修正する
  call mk_ft(tt, "Field_rev20251127.bil")           ! 修正後の測線マップを出力
  call write_field(tt, "flxy_20251127.csv")         ! 修正後の測線データを書き出す

end subroutine

!----------------------------------------------------------------------
! 測線データを修正する
!----------------------------------------------------------------------
subroutine modify(tt)
  type(t_transect), intent(inout) :: tt(:)
  integer :: it
  do it = 1, size(tt)
    if (tt(it)%nr == 0) cycle
    if (tt(it)%n == 1) then
      call expand(tt(it))   ! 測線の方向を決めて拡張する
    else
      call set_xy(tt(it))   ! 流向判断の基準点を決める
    end if
  end do
end subroutine


!----------------------------------------------------------------------
! 流向判断の基準点を決める
!----------------------------------------------------------------------
subroutine set_xy(t)
  type(t_transect), intent(inout) :: t
  integer :: x, y
  ! 両端点の中心を基準点とする
  x = int(aint((real(t%x0) + real(t%x1)) / 2))       ! 四捨五入
  y = int(aint((real(t%y0) + real(t%y1)) / 2))       ! 四捨五入
  if (rw(x,y) < 1) then
    x = ceiling((real(t%x0) + real(t%x1)) / 2)  ! 切り上げ
    y = ceiling((real(t%y0) + real(t%y1)) / 2)  ! 切り上げ
    if (rw(x,y) < 1) then
      x = floor((real(t%x0) + real(t%x1)) / 2)  ! 切り捨て
      y = floor((real(t%y0) + real(t%y1)) / 2)  ! 切り捨て
      if (rw(x,y) < 1) then
        print *, "Warning, need check", t%id, t%x0, t%y0, t%x1, t%y1
      end if
    end if
  end if
  t%x = x
  t%y = y
end subroutine


!----------------------------------------------------------------------
! 単独セルの測線データを拡張する
!----------------------------------------------------------------------
subroutine expand(t)
  type(t_transect), intent(inout) :: t
  integer :: x0x, y0x, x1x, y1x
  integer :: x0y, y0y, x1y, y1y
  integer :: nrx, nry

  ! 流向判断の基準点をセット
  t%x = t%x0
  t%y = t%y0

  ! x方向に拡張
  nrx = 1
  x0x = t%x0 - 1
  y0x = t%y0
  do while (rw(x0x,y0x) > 0)
    nrx = nrx + 1
    x0x = x0x - 1
  end do
  x1x = t%x1 + 1
  y1x = t%y1
  do while (rw(x1x,y1x) > 0)
    nrx = nrx + 1
    x1x = x1x + 1
  end do

  ! y方向に拡張
  nry = 1
  x0y = t%x0
  y0y = t%y0 - 1
  do while (rw(x0y,y0y) > 0)
    nry = nry + 1
    y0y = y0y - 1
  end do
  x1y = t%x1
  y1y = t%y1 + 1
  do while (rw(x1y,y1y) > 0)
    nry = nry + 1
    y1y = y1y + 1
  end do

  ! 方向を判定
  if (nrx <= nry) then
    t%x0 = x0x
    t%y0 = y0x
    t%x1 = x1x
    t%y1 = y1x
  else
    t%x0 = x0y
    t%y0 = y0y
    t%x1 = x1y
    t%y1 = y1y
  end if

end subroutine


!----------------------------------------------------------------------
! 右岸から左岸に向けて始点・終点とする
!----------------------------------------------------------------------
subroutine chk_dir(tt)
  type(t_transect), intent(inout) :: tt(:)
  type(t_transect) :: t
  integer :: it
  integer :: x, y           ! 流量判断の基準位置
  real :: dxt, dyt          ! 測線ベクトル
  real :: qx, qy            ! 流向ベクトル
  real :: aa                ! 測線と流下方向の外積
  integer :: tmpx, tmpy     ! 作業用

  do it = 1, size(tt)
    t = tt(it)
    if (t%nr == 0) cycle           ! 河道を含まない測線は無視
    x = t%x
    y = t%y
    dxt = t%x1 - t%x0          ! 測線ベクトル
    dyt = t%y1 - t%y0          ! 測線ベクトル
    qx = cos(qd(x,y))
    qy = sin(qd(x,y))
    aa = (dxt * qy) - (dyt * qx)       ! 右岸から左岸の場合に正の値
    if (aa < 0) then
      print *, "exhabge", it
      tmpx = t%x0
      tmpy = t%y0
      t%x0 = t%x1
      t%y0 = t%y1
      t%x1 = tmpx
      t%y1 = tmpy
    else if (aa == 0) then
      print *, "Error, Parallel", it, t%x0, t%y0, t%x1, t%y1
      print *, "    ", t%n, dxt, dyt, qx, qy
    end if
    tt(it) = t
  end do

end subroutine


!----------------------------------------------------------------------
! 測線マスクを作成して出力する
!----------------------------------------------------------------------
subroutine mk_ft(tt, fname)
  type(t_transect), intent(inout) :: tt(:)
  character(len=*), intent(in) :: fname
  integer, allocatable :: ft(:,:)
  integer :: it
  integer :: i, j, n, nr
  integer :: x0, y0, x1, y1

  allocate(ft(1:nx,1:ny))

  ft(:,:) = 0

  do it = 1, size(tt)
    x0 = tt(it)%x0
    y0 = tt(it)%y0
    x1 = tt(it)%x1
    y1 = tt(it)%y1
    if (abs((x0 - x1) * (y0 - y1)) > 0) then
      ! 測線が斜め方向
      print *, "Error, Diagonal", it, x0, y0, x1, y1
    end if
    n = 0       ! 測線のセル数
    nr = 0      ! 測線中の河道セル数
    write(6,'(i5,a)', advance='no') it, "  "
    do j = y0, y1, sign(1, y1 - y0)
      do i = x0, x1, sign(1, x1 - x0)
        ft(i,j) = 2
        n = n + 1
        if (rw(i,j) > 0) nr = nr + 1
        write(6,'(i1)', advance='no') rw(i,j)
      end do
    end do
    write(6,*)
    tt(it)%n = n
    tt(it)%nr = nr
    if (tt(it)%nr == 0) then
      ! 測線中に河道セルが存在しない
      print *,  "Error, No river", it, x0, y0, x1, y1
    end if
    ft(x0,y0) = 1
    ft(x1,y1) = 3
  end do

  open(1,file=fname, form='unformatted', status='replace', access='stream')
  write(1) ft
  close(1)

  deallocate(ft)

end subroutine


!----------------------------------------------------------------------
! 河道マスクを読み込む
!----------------------------------------------------------------------
subroutine read_rw(fname)
  character(len=*) :: fname
  open(1,file=fname, form='unformatted', status='old', access='stream')
  read(1) rw
  close(1)
end subroutine


!----------------------------------------------------------------------
! 流向を読み込む
!----------------------------------------------------------------------
subroutine read_qd(fname)
  character(len=*) :: fname
  open(1,file=fname, form='unformatted', status='old', access='stream')
  read(1) qd
  close(1)
end subroutine


!----------------------------------------------------------------------
! 測線データを読み込む　
!----------------------------------------------------------------------
subroutine read_field(tt, fname)
  type(t_transect), allocatable, intent(inout) :: tt(:)
  character(len=*) :: fname
  integer :: nt
  integer :: i, j, k

  open(1, file=fname, status='old')
  nt = 0
  do
    read(1, *, end=99)
    nt = nt + 1
  end do
  99 continue
  nt = nt - 1   ! ヘッダー分を引く
  rewind(1)

  allocate(tt(1:nt))

  read(1, *)   ! ヘッダーを読み飛ばす
  do i = 1, nt
    read(1, *) j, k, tt(i)%x0, tt(i)%y0, tt(i)%x1, tt(i)%y1
    tt(i)%id = j
  end do
  close(1)

end subroutine


!----------------------------------------------------------------------
! 測線データを書き込む　
!----------------------------------------------------------------------
subroutine write_field(tt, fname)
  type(t_transect), allocatable, intent(inout) :: tt(:)
  character(len=*) :: fname
  integer :: i

  open(1, file=fname, status='replace')
  do i = 1, size(tt)
    write(1, '(i6,3(a,i6))') tt(i)%x0, ",", tt(i)%y0, ",", tt(i)%x1, ",", tt(i)%y1
  end do
  close(1)

end subroutine


!----------------------------------------------------------------------
end module

!=======================================================================
!=======================================================================
program prep_transect
  use m_prep_transect
  implicit none
  call do_main
end program
