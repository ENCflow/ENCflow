!=======================================================================
!
! [1] 流向データから落水方向データを作成する
!
!   入力データ
!     Ddd9998.bil: 卓越流向 (2~256)
!     H9998.bil: 水深
!     Z0000.bil: 標高
!     SeaLand.bil: 海域マスク
!
!   出力データ
!     Dd9998.bil: 落水方向 (1~8)
!
!-----------------------------------------------------------------------
!
! [1] mkdowndir:  卓越流下方向データから落水方向データを作成
! [2] chkdowndir: 落水方向データの連続性を確認・修正
! [3] calcarea:   落水方向データから集水面積と累積雨量を計算
! [4] pickuparea: 測線リストから観測点の集水面積と累積雨量を計算
!
!=======================================================================
module mod_mkdowndir
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
  integer, allocatable :: ddd(:,:)    ! 卓越流向(2~256)
  integer, allocatable :: ddx(:,:)    ! 流下方向(卓越流向より)(1~8)
  integer, allocatable :: ddy(:,:)    ! 流下方向(水位より)(1~8)
  integer, allocatable :: ddz(:,:)    ! 流下方向(標高より)(1~8)
  integer, allocatable :: sw(:,:)     ! 海域マスク
  real, allocatable :: h(:,:)         ! 水深
  real, allocatable :: z(:,:)         ! 標高
  real, allocatable :: e(:,:)         ! 水位
  real, allocatable :: e0(:,:)        ! 水位(移動平均)

  allocate(ddd(1:nx,1:ny), source = 0)
  allocate(ddx(1:nx,1:ny), source = -1)
  allocate(ddy(1:nx,1:ny), source = -1)
  allocate(ddz(1:nx,1:ny), source = -1)
  allocate(sw(1:nx,1:ny), source = 0)
  allocate(h(1:nx,1:ny), source = 0.0)
  allocate(z(1:nx,1:ny), source = 0.0)
  allocate(e(1:nx,1:ny), source = 0.0)
  allocate(e0(1:nx,1:ny), source = 0.0)

  ! 卓越流向ファイルの読み込み
  print *, "Reading Ddd"
  open(1, file="data/Ddd9998.bil", form='unformatted', status='old', access='stream')
  read(1) ddd
  close(1)

  ! 水深の読み込み
  print *, "Reading H"
  open(1, file="data/H9998.bil", form='unformatted', status='old', access='stream')
  read(1) h
  close(1)

  ! 標高の読み込み
  print *, "Reading Elev"
  open(1, file="data/Elev_250_down100carved_20251127.bil", form='unformatted', status='old', access='stream')
  read(1) z
  close(1)

  ! 海域マスクの読み込み
  print *, "Reading SeaLand"
  open(1, file="data/SeaLand250_20251127.bil", form='unformatted', status='old', access='stream')
  read(1) sw
  close(1)

  ! 流下方向を計算
  call mk_ddx(ddd, sw, ddx)    ! 卓越流下方向から落水方向を計算

  ! 以下は不採用
  e(:,:) = z(:,:) + h(:,:)     ! 水位を計算
  call mk_e0(e, sw, e0)        ! 水位の移動平均を計算
  call mk_ddy(e, e0, sw, ddy)  ! 水位から落水方向を計算
  call mk_ddz(z, sw, ddz)      ! 標高から落水方向を計算


  ! 結果出力ディレクトリを作成
  call execute_command_line("mkdir -p result")

  ! 流下方向の書き込み
  print *, "Writing Dd"
  open(1, file="result/Dd9998.bil", form='unformatted', status='replace', access='stream')
  write(1) ddx
  close(1)

  !---- 以下は不採用 ----
  !open(1, file="Ddy0002.bil", form='unformatted', status='replace', access='stream')
  !write(1) ddy
  !close(1)
  !open(1, file="Ddz0001.bil", form='unformatted', status='replace', access='stream')
  !write(1) ddz
  !close(1)
  !open(1, file="E0002.bil", form='unformatted', status='replace', access='stream')
  !write(1) e(:,:)
  !close(1)
  !open(1, file="Ea0002.bil", form='unformatted', status='replace', access='stream')
  !write(1) e0(:,:)
  !close(1)

end subroutine


!-----------------------------------------------------------------------
! 卓越流下方向データ(2~256)を落水方向(1~8)に変換する
!-----------------------------------------------------------------------
subroutine mk_ddx(ddd, sw, dd)
  integer, intent(in) :: ddd(1:nx,1:ny)
  integer, intent(in) :: sw(1:nx,1:ny)
  integer, intent(out) :: dd(1:nx,1:ny)
  integer :: i, j
  dd(:,:) = -1
  do j = 1, ny
    do i = 1, nx
      if (sw(i,j) > 0) cycle
      if (ddd(i,j) > 0) then
        dd(i,j) = nint(log(real(ddd(i,j))) / log(2.0))
      else
        dd(i,j) = 0
      end if
    end do
  end do
end subroutine


!-----------------------------------------------------------------------
! 水位から落水方向を計算する
!-----------------------------------------------------------------------
subroutine mk_ddy(e, e0, sw, dd)
  real, intent(in) :: e(1:nx,1:ny)
  real, intent(in) :: e0(1:nx,1:ny)
  integer, intent(in) :: sw(1:nx,1:ny)
  integer, intent(out) :: dd(1:nx,1:ny)
  real :: ec, en
  real :: e0c, e0n
  real :: de, demax
  real :: de0, de0max
  integer :: i, j, k, ii, jj
  integer :: neq

  dd(:,:) = -1
  do j = 2, ny - 1
    do i = 2, nx - 1
      if (sw(i,j) > 0) cycle

      ec = e(i,j)
      e0c = e0(i,j)
      demax = -10000.
      de0max = -10000.
      neq = 0

      do k = 1, 8
        ii = i + din(k)
        jj = j + djn(k)
        en = e(ii,jj)
        e0n = e0(ii,jj)

        if (sw(ii,jj) > 0) then ! 隣接セルが海の場合は海に流下
          dd(i,j) = k
          exit
        end if

        de = ec - en
        de0 = e0c - e0n
        if (de < 0) then
          cycle
        else if (de > demax) then
          dd(i,j) = k
          demax = de
          de0max = de0
        else if (de == 0) then
          if (de0 > de0max) then
            dd(i,j) = k
            demax = de
            de0max = de0
          else if (de0 == 0) then
            neq = neq + 1
          end if
        end if
      end do

      if (neq == 8) dd(i,j) = 0
    end do
  end do
end subroutine


!-----------------------------------------------------------------------
! 水位の移動平均
!-----------------------------------------------------------------------
subroutine mk_e0(a, sw, a0)
  real, intent(in) :: a(1:nx,1:ny)
  integer, intent(in) :: sw(1:nx,1:ny)
  real, intent(out) :: a0(1:nx,1:ny)
  integer :: i, j, k, ii, jj
  integer :: n
  real :: s

  a0(:,:) = a(:,:)

  do j = 2, ny - 1
    do i = 2, nx - 1
      if (sw(i,j) > 0) cycle
      n = 0
      s = a(i,j)
      do k = 1, 8
        ii = i + din(k)
        jj = j + djn(k)
        if (sw(ii,jj) > 0) cycle
        s = s + a(ii,jj)
        n = n + 1
      end do
      if (n > 0) a0(i,j) = s / real(n)
    end do
  end do
end subroutine

!-----------------------------------------------------------------------
! 標高から落水方向を計算する
!-----------------------------------------------------------------------
subroutine mk_ddz(z, sw, dd)
  real, intent(in) :: z(1:nx,1:ny)
  integer, intent(in) :: sw(1:nx,1:ny)
  integer, intent(out) :: dd(1:nx,1:ny)
  real :: zc, zn
  real :: dz, dzmax
  integer :: i, j, k, ii, jj
  integer :: neq

  dd(:,:) = -1
  do j = 2, ny - 1
    do i = 2, nx - 1
      if (sw(i,j) > 0) cycle
      zc = z(i,j)
      dzmax = -10000.
      neq = 0
      do k = 1, 8
        ii = i + din(k)
        jj = j + djn(k)
        zn = z(ii,jj)
        if (sw(ii,jj) > 0) then ! 隣接セルが海の場合は海に流下
          dd(i,j) = k
          exit
        end if
        dz = zc - zn
        if (dz > dzmax) then
          dd(i,j) = k
          dzmax = dz
        end if
        if (dz == 0) neq = neq + 1
      end do
      if (neq == 8) dd(i,j) = 0
    end do
  end do
end subroutine

!-----------------------------------------------------------------------
end module

!=======================================================================
!=======================================================================
program mkdowndir
  use mod_mkdowndir
  call do_main
end program
