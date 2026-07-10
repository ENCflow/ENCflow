!=======================================================================
!
! [2] 落水方向データの連続性を確認・修正する
!
!   入力データ
!     result/Dd9998.bil: 落水方向 (1~8)
!
!   出力データ(result/)
!     result/Dd0000.bil: 修正済み落水方向 (1~8)
!     result/Path0000.bil: ループ確認用 (-1はループの一部)
!
!-----------------------------------------------------------------------
!
! [1] mkdowndir:  卓越流下方向データから落水方向データを作成
! [2] chkdowndir: 落水方向データの連続性を確認・修正
! [3] calcarea:   落水方向データから集水面積と累積雨量を計算
! [4] pickuparea: 測線リストから観測点の集水面積と累積雨量を計算
!
!=======================================================================
module mod_chkdowndir
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
  integer, allocatable :: path(:,:)   ! ループ確認用
  integer :: ierr

  allocate(dd(1:nx,1:ny), source = 0)
  allocate(path(1:nx,1:ny), source = 0)

  ! 落水方向ファイルの読み込み
  print *, "Reading Dd9998.bil"
  open(1, file="result/Dd9998.bil", form='unformatted', status='old', access='stream')
  read(1) dd
  close(1)

  print *, "Correcting dd"
  ! 琵琶湖の北部にある3箇所の小さな渦を破る
  dd(2606,5069) = 6
  dd(2623,5079) = 4
  dd(2638,5144) = 1

  print *, "Tracing streamlines"
  call chk_dd(dd, path, ierr)

  ! ループ確認データの書き込み(-1がループの一部)
  if (ierr > 0) then
    print *, "Writing Path0000.bil"
    open(1, file="result/Path0000.bil", form='unformatted', status='replace', access='stream')
    write(1) path
  end if

  ! 修正後落水方向ファイルの読み込み
  print *, "Writing Dd0000.bil"
  open(1, file="result/Dd0000.bil", form='unformatted', status='replace', access='stream')
  write(1) dd
  close(1)

end subroutine


!-----------------------------------------------------------------------
! 落水方向データのチェック
!-----------------------------------------------------------------------
subroutine chk_dd(dd, path, ierr)
  integer, intent(in) :: dd(1:nx,1:ny)
  integer, intent(out) :: path(1:nx,1:ny)
  integer, intent(out) :: ierr
  integer :: i, j, k
  integer :: id, n
  integer :: ic, jc, in, jn

  id = 0
  ierr = 0

  do j = 1, ny
    if (mod(j, 100) == 0) print *, j
    do i = 1, nx
      if (dd(i,j) < 0) cycle

      !---- 流線の追跡開始 ----
      id = id + 1                      ! 流線ID
      n = 1                            ! 流線上のセル数
      ic = i                           ! 現在セル
      jc = j                           ! 現在セル
      do
        k = dd(ic,jc)                  ! 落水方向
        in = ic + din(k)               ! 次のセル
        jn = jc + djn(k)               ! 次のセル
        if (path(in,jn) == id) then    ! 既に通過した場所に戻った
          path(ic,jc) = -1
          ierr = ierr + 1
          print *, "Loop ", id, n, ic, jc
          exit
        else
          path(ic,jc) = id
        end if
        if (dd(in,jn) < 0) then        ! 海に到達
          exit
        else
          ic = in
          jc = jn
          n = n + 1
        end if
      end do
      !---- 流線の追跡ここまで ----

    end do
  end do

end subroutine


!-----------------------------------------------------------------------
end module

!=======================================================================
!=======================================================================
program chkdowndir
  use mod_chkdowndir
  call do_main
end program
