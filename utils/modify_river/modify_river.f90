!
! 河道マスクを修正して、同時に河道を掘り下げた標高データも修正する
!
!   入力データ
!     river_add.txt: 河道マスクに追加するセルのx,y番号を列挙した、タブ・空白区切りのテキストファイル
!     river_remove.txt: 河道マスクから削除するセルのx,y番号を列挙した、タブ・空白区切りのテキストファイル
!     RiverMask_XXX.bil: 修正すべき河道マスク
!     Elev_XXX.bil: 修正すべき河道掘削済み標高
!
!   出力データ
!     RiverMask_YYY.bil: 修正後の河道マスク
!     Elev_YYY.bil: 修正後の河道掘削済み標高
!     RiverModified.bil: 修正された河道セル(integer*4)
!
program modify_river
  implicit none
  integer, parameter :: nx = 6080
  integer, parameter :: ny = 8960
  integer, parameter :: nad = 457    ! river_add.txtの行数
  integer, parameter :: nrm = 110    ! river_remove.txtの行数
  integer :: ixad(1:nad)
  integer :: iyad(1:nad)
  integer :: ixrm(1:nrm)
  integer :: iyrm(1:nrm)
  integer :: rw(1:nx,1:ny)    ! 河道マスク
  real :: z(1:nx,1:ny)        ! 標高(掘込済み)
  real :: z0(1:nx,1:ny)        ! 標高(掘込前)
  integer :: i, j
  integer :: ix, iy

  ! 追加セルのリストを読み込む
  open(1, file="river_add.txt")
  do i = 1, nad
    read(1,*) ixad(i), iyad(i)
    ixad(i) = ixad(i) + 1
    iyad(i) = iyad(i) + 1
  end do
  close(1)

  ! 削除セルのリストを読み込む
  open(1, file="river_remove.txt")
  do i = 1, nrm
    read(1,*) ixrm(i), iyrm(i)
    ixrm(i) = ixrm(i) + 1
    iyrm(i) = iyrm(i) + 1
  end do
  close(1)


  ! 修正前の河道マスクの読み込み
  open(1, file="RiverMask_20251123.bil", form='unformatted', status='old', access='stream')
  read(1) rw
  close(1)

  ! 修正前の河道掘り込み済み標高の読み込み
  open(1, file="remake_Elev250_down100_20251123.bil", form='unformatted', status='old', access='stream')
  read(1) z
  close(1)

  ! 河道セルの追加
  do i = 1, nad
    ix = ixad(i)
    iy = iyad(i)
    if (rw(ix,iy) > 0) then
      print *, "The cell in river_add.txt is already river cell", i, ix, iy
    end if
    rw(ix,iy) = 1                 ! 河道マスクON
    z(ix,iy) = z(ix,iy) - 100.0   ! 掘り込み
  end do

  ! 河道セルの削除
  do i = 1, nrm
    ix = ixrm(i)
    iy = iyrm(i)
    if (rw(ix,iy) <= 0) then
      print *, "The cell in river_remove.txt is not river cell", i, ix, iy
    end if
    rw(ix,iy) = 0                 ! 河道マスクOFF
    z(ix,iy) = z(ix,iy) + 100.0   ! 埋める
  end do

  ! 掘込前標高の作成
  z0(:,:) = z(:,:)
  do j = 1, ny
    do i = 1, nx
      if (rw(i,j) > 0) z0(i,j) = z(i,j) + 100.0
    end do
  end do

  ! 修正済みの河道マスクの書き込み
  open(1, file="RiverMask_20251127.bil", form='unformatted', status='replace', access='stream')
  write(1) rw
  close(1)

  ! 修正済みの河道掘り込み済み標高の書き込み
  open(1, file="remake_Elev250_down100_20251127.bil", form='unformatted', status='replace', access='stream')
  write(1) z
  close(1)

  ! 修正済みの河道掘り込み済み前標高の書き込み
  open(1, file="remake_Elev250_20251127.bil", form='unformatted', status='replace', access='stream')
  write(1) z0
  close(1)


end program
