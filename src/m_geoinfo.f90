!======================================================================
module m_geoinfo
  use m_sysparam, only : t_sysparam
  use list_geoinfo, only : t_list_geoinfo, list_geoinfo_read
  use m_fileio
  implicit none
  private

  public :: t_geoinfo
  public :: m_geoinfo_init
  public :: m_geoinfo_dispose


  type t_geoinfo
    integer :: nx                                     ! x方向セル数
    integer :: ny                                     ! y方向セル数
    real :: dx
    real :: dy
    real :: dr
    real :: lx
    real :: ly
    real :: min_gv                                    ! 家屋の空隙率の最小値
    real :: min_bb                                    ! 家屋の平均サイズの最小値
    real, allocatable :: z(:,:)                       ! 標高(m)
    real, allocatable :: rn(:,:)                      ! 粗度係数
    real, allocatable :: gv(:,:)                      ! 家屋の空隙率
    real, allocatable :: bb(:,:)                      ! 家屋の平均寸法
    integer, allocatable :: x(:,:)                    ! 対象領域判別マスク
    integer, allocatable :: sw(:,:)                   ! 海域マスク
    integer, allocatable :: rw(:,:)                   ! 河道マスク
    integer, allocatable :: lu(:,:)                   ! 土地利用
    integer, allocatable :: wx(:,:)                   ! 行ごとの計算対象範囲
    integer :: wy(1:2)                                ! 行の計算対象範囲
    logical :: initialized = .false.
  end type


  interface
    module subroutine init_geoinfo_user_1(p, g)
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(inout) :: g
    end subroutine
    module subroutine init_geoinfo_user_2(p, g)
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(inout) :: g
    end subroutine
    module subroutine init_geoinfo_user_3(p, g)
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(inout) :: g
    end subroutine
    module subroutine init_geoinfo_user_4(p, g)
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(inout) :: g
    end subroutine
    module subroutine init_geoinfo_user_5(p, g)
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(inout) :: g
    end subroutine
  end interface

contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! 地理情報構造体を初期化する
!----------------------------------------------------------------------
subroutine m_geoinfo_init(g, p)
  type(t_sysparam), intent(inout) :: p             ! システムパラメータ構造体
  type(t_geoinfo), intent(out) :: g             ! 地理情報構造体
  type(t_list_geoinfo) :: list                     ! パラメータファイル中の変数


  call list_geoinfo_read(p, list)
  call set_params(p, g, list)

  call allocate_arrays(g)
  call read_sw(p, g, list)     ! read_maskよりも先に実行する
  call read_mask(p, g, list)
  call read_z(p, g, list)
  call read_lu(p, g, list)
  call read_rw(p, g, list)
  call read_rn(p, g, list)
  call read_gvbb(p, g, list)

  select case (list%f_user_routine_id)
    case (0)
      continue
    case (1)
      call init_geoinfo_user_1(p, g)
    case (2)
      call init_geoinfo_user_2(p, g)
    case (3)
      call init_geoinfo_user_3(p, g)
    case (4)
      call init_geoinfo_user_4(p, g)
    case (5)
      call init_geoinfo_user_5(p, g)
    case default
      print *, "error: undefined f_user_routine_id in list_geoinfo", list%f_user_routine_id
      stop
  end select


  call calc_wxy(p, g)



  g%initialized = .true.

end subroutine

!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine m_geoinfo_dispose(g)
  type(t_geoinfo), intent(inout) :: g
  if (allocated(g%z)) deallocate(g%z)
  if (allocated(g%rn)) deallocate(g%rn)
  if (allocated(g%lu)) deallocate(g%lu)
  if (allocated(g%gv)) deallocate(g%gv)
  if (allocated(g%bb)) deallocate(g%bb)
  if (allocated(g%x)) deallocate(g%x)
  if (allocated(g%sw)) deallocate(g%sw)
  if (allocated(g%rw)) deallocate(g%rw)
  if (allocated(g%wx)) deallocate(g%wx)
end subroutine

!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

!----------------------------------------------------------------------
! パラメータファイル中の変数を地理情報構造体にセット
!----------------------------------------------------------------------
subroutine set_params(p, g, list)
  type(t_sysparam), intent(inout) :: p
  type(t_geoinfo), intent(inout) :: g
  type(t_list_geoinfo), intent(in) :: list

  g%nx = list%nx
  g%ny = list%ny
  g%dx = list%dx
  g%dy = list%dy
  g%lx = list%lx
  g%ly = list%ly
  g%dr = sqrt(g%dx**2 + g%dy**2)
  g%min_gv = list%min_gv
  g%min_bb = list%min_bb

  p%nx = list%nx
  p%ny = list%ny
  p%dx = list%dx
  p%dy = list%dy
  p%dr = sqrt(g%dx**2 + g%dy**2)
  p%dtpdx = p%dt / min(g%dx, g%dy)
end subroutine

!----------------------------------------------------------------------
! 地理情報構造体中の配列を確保
!----------------------------------------------------------------------
subroutine allocate_arrays(g)
  type(t_geoinfo), intent(inout) :: g
  allocate(g%z(1:g%nx,1:g%ny), source = 0.0)
  allocate(g%rn(1:g%nx,1:g%ny), source = 0.0)
  allocate(g%gv(1:g%nx,1:g%ny), source = 1.0)    ! 空隙率は1.0で初期化
  allocate(g%bb(1:g%nx,1:g%ny), source = 1.e10)  ! 家屋サイズは大きな値で初期化
  allocate(g%x(0:g%nx+1,0:g%ny+1), source = 0)   ! 領域マスクは全て領域外で初期化
  allocate(g%sw(1:g%nx,1:g%ny), source = 0)
  allocate(g%rw(1:g%nx,1:g%ny), source = 0)
  allocate(g%lu(1:g%nx,1:g%ny), source = 0)
  allocate(g%wx(1:2,1:g%ny))
end subroutine


!----------------------------------------------------------------------
! 海域マスクを読み込む
!----------------------------------------------------------------------
subroutine read_sw(p, g, list)
  type(t_sysparam), intent(in) :: p             ! システムパラメータ構造体
  type(t_geoinfo), intent(inout) :: g
  type(t_list_geoinfo), intent(in) :: list
  character(:), allocatable :: fname

  if (len_trim(list%fn_sw) > 0) then
    fname = trim(p%dir_data) // "/" // trim(list%fn_sw)
    print *, "reading ", fname
    call fileio_read_matrix(fname, g%nx, g%ny, g%sw, p%f_input_mode)
  end if

end subroutine

!----------------------------------------------------------------------
! 領域マスクデータを読み込む
!----------------------------------------------------------------------
subroutine read_mask(p, g, list)
  type(t_sysparam), intent(in) :: p             ! システムパラメータ構造体
  type(t_geoinfo), intent(inout) :: g
  type(t_list_geoinfo), intent(in) :: list
  character(:), allocatable :: fname
  integer :: a(1:g%nx,1:g%ny)

  if (list%f_masktype == 0) then
    ! マスク無しを指定の場合
    ! 領域マスク全域を1にセット
    g%x(1:g%nx,1:g%ny) = 1
  else if (list%f_masktype == 1) then
    ! 流域マスクを指定の場合
    ! ファイルから読み込む
    fname = trim(p%dir_data) // "/" // trim(list%fn_mask)
    print *, "reading ", fname
    call fileio_read_matrix(fname, g%nx, g%ny, a, p%f_input_mode)
        block
        integer :: i, j
        do j = 1, g%ny
          do i = 1, g%nx
            if (a(i,j) /= 0 .and. a(i,j) /= 1) then
              print *, "list_geoinfo: invalid data in mask data", i, j, a(i,j)
            end if
          end do
        end do
        end block
    ! g%xは(0:nx+1,0:ny+1)なので範囲を指定してコピー
    g%x(1:g%nx,1:g%ny) = a(1:g%nx,1:g%ny)
  else if (list%f_masktype == 2) then
    ! 海域マスクから生成を指定の場合
    if (len_trim(list%fn_sw) == 0) then
      print *, 'list_geoinfo: f_mastype=2 but fn_sw=""'
      stop
    end if
    call do_sw2x
  else
    ! 不正なマスクタイプ
    print *, "list_geoinfo: unknown mask type", list%f_masktype
    stop
  end if


  ! 領域の外側が海の場合、領域を1セル分拡張
  !if (.false.) then
  if (.true.) then
        block
        integer :: i, j, k, ii, jj
        integer :: x1(0:g%nx+1,0:g%ny+1)
        integer, parameter :: din(1:8) = [ -1,  0,  1, -1,  1, -1,  0,  1]
        integer, parameter :: djn(1:8) = [ -1, -1, -1,  0,  0,  1,  1,  1]
        x1(:,:) = g%x(:,:)
        do j = 2, g%ny-1
          do i = 2, g%nx-1
            if (g%x(i,j) <= 0) cycle
            do k = 1, 8
              ii = i + din(k)
              jj = j + djn(k)
              if (g%x(ii,jj) <= 0 .and. g%sw(ii,jj) > 0) then
                ! 近傍セルが領域外かつ海の場合
                ! 近傍セルを領域内に
                x1(ii,jj) = 1
              end if
            end do
          end do
        end do
        g%x(:,:) = x1(:,:)
        end block
  end if


  ! 四辺を強制的に海域に
  if (list%f_edge_sw > 0) then
      block
      integer :: i, j
      do j = 1, g%ny
        g%sw(1,j) = 1
        g%sw(g%ny,j) = 1
      end do
      do i = 1, g%nx
        g%sw(i,1) = 1
        g%sw(i,g%ny) = 1
      end do
      end block
  end if

contains
  ! 海域マスクから領域マスクを作る
  !   このとき陸域と隣接する海域セルを計算領域に入れる
  subroutine do_sw2x
    integer :: i, j, k, ii, jj
    integer, parameter :: din(1:8) = [ -1,  0,  1, -1,  1, -1,  0,  1]
    integer, parameter :: djn(1:8) = [ -1, -1, -1,  0,  0,  1,  1,  1]
    do j = 1, g%ny
      do i = 1, g%nx
        if (g%sw(i,j) <= 0) then
          ! 海でないセルは有効セル
          g%x(i,j) = 1
          cycle
        end if
        ! 海域セルのうち陸域に隣接するセルは有効セルにする
        do k = 1, 8
          ii = i + din(k)
          jj = j + djn(k)
          if (ii < 1 .or. ii > g%nx) cycle
          if (jj < 1 .or. jj > g%ny) cycle
          if (g%sw(ii,jj) <= 0) then
            ! 近傍に海でないセルがある場合は有効セル
            g%x(i,j) = 1
            exit
          end if
        end do
      end do
    end do
  end subroutine

end subroutine


!----------------------------------------------------------------------
! 標高データを読み込む
!----------------------------------------------------------------------
subroutine read_z(p, g, list)
  type(t_sysparam), intent(in) :: p             ! システムパラメータ構造体
  type(t_geoinfo), intent(inout) :: g
  type(t_list_geoinfo), intent(in) :: list
  character(:), allocatable :: fname
  integer :: i, j

  if (list%f_ztype == 0) then
    g%z = list%z0 * list%mag_z
  else
    fname = trim(p%dir_data) // "/" // trim(list%fn_z)
    print *, "reading ", fname
    call fileio_read_matrix(fname, g%nx, g%ny, g%z, p%f_input_mode)
    g%z(:,:) = g%z(:,:) * list%mag_z
  end if

  ! 海域の標高を0に強制
  do j = 1, g%ny
    do i = 1, g%nx
      if (g%sw(i,j) > 0) g%z(i,j) = 0
    end do
  end do

  ! 鳴瀬川の河口を加工
  !g%z(4214,3656) = g%z(4214,3656) + 100.
  !g%z(4216,3658) = g%z(4216,3658) + 100.
  !g%z(4215,3655) = g%z(4215,3655) + 100.
  !g%z(4213,3655) = g%z(4213,3655) + 100.
  !g%z(4214,3654) = g%z(4214,3654) + 100.
  !g%z(4214,3653) = g%z(4214,3653) + 100.
  !g%z(4211,3653) = g%z(4211,3653) + 100.
  !g%z(4211,3652) = g%z(4211,3652) + 100.
  !g%z(4212,3650) = g%z(4212,3650) + 100.
  !g%z(4211,3649) = g%z(4211,3649) + 100.
  !g%z(4209,3649) = g%z(4209,3649) - 100.

end subroutine


!----------------------------------------------------------------------
! 土地利用データを読み込む
!----------------------------------------------------------------------
subroutine read_lu(p, g, list)
  type(t_sysparam), intent(in) :: p             ! システムパラメータ構造体
  type(t_geoinfo), intent(inout) :: g
  type(t_list_geoinfo), intent(in) :: list
  character(:), allocatable :: fname

  if (list%f_lusetype == 0) then
    g%lu = 0
  else
    fname = trim(p%dir_data) // "/" // trim(list%fn_luse)
    print *, "reading ", fname
    call fileio_read_matrix(fname, g%nx, g%ny, g%lu, p%f_input_mode)
  end if

!  ! 秩父の河道を掘り下げる
!  block
!  integer :: i, j
!  do j = 1, g%ny
!    do i = 1, g%nx
!      ! 河道を掘り下げる
!      if (g%lu(i,j) > 0) g%z(i,j) = g%z(i,j) - 100
!      ! 河道を閉塞させる
!      if (i == 296 .and. j >= 205 .and. j <= 207 .and. g%lu(i,j) > 0)  g%z(i,j) = g%z(i,j) + 100
!      if (i == 147 .and. j >= 102 .and. j <= 105 .and. g%lu(i,j) > 0)  g%z(i,j) = g%z(i,j) + 100
!    end do
!  end do
!  end block

end subroutine

!----------------------------------------------------------------------
! 河道マスクを読み込む
!----------------------------------------------------------------------
subroutine read_rw(p, g, list)
  type(t_sysparam), intent(in) :: p             ! システムパラメータ構造体
  type(t_geoinfo), intent(inout) :: g
  type(t_list_geoinfo), intent(in) :: list
  character(:), allocatable :: fname

  if (len_trim(list%fn_rw) > 0) then
    fname = trim(p%dir_data) // "/" // trim(list%fn_rw)
    print *, "reading ", fname
    call fileio_read_matrix(fname, g%nx, g%ny, g%rw, p%f_input_mode)
  end if

end subroutine

!----------------------------------------------------------------------
! 家屋の空隙率と平均寸法を読み込む
!----------------------------------------------------------------------
subroutine read_gvbb(p, g, list)
  type(t_sysparam), intent(in) :: p             ! システムパラメータ構造体
  type(t_geoinfo), intent(inout) :: g
  type(t_list_geoinfo), intent(in) :: list
  character(:), allocatable :: fname
  integer :: i, j

  if (len_trim(list%fn_gv) > 0) then
    fname = trim(p%dir_data) // "/" // trim(list%fn_gv)
    print *, "reading ", fname
    call fileio_read_matrix(fname, g%nx, g%ny, g%gv, p%f_input_mode)
  end if

  if (len_trim(list%fn_bb) > 0) then
    fname = trim(p%dir_data) // "/" // trim(list%fn_bb)
    print *, "reading ", fname
    call fileio_read_matrix(fname, g%nx, g%ny, g%bb, p%f_input_mode)
  end if

  do j = 1, g%ny
    do i = 1, g%nx
      g%gv(i,j) = max(g%gv(i,j), g%min_gv)
      g%bb(i,j) = max(g%bb(i,j), g%min_bb)
    end do
  end do

end subroutine


!----------------------------------------------------------------------
! 粗度係数データを読み込む
!----------------------------------------------------------------------
subroutine read_rn(p, g, list)
  type(t_sysparam), intent(in) :: p             ! システムパラメータ構造体
  type(t_geoinfo), intent(inout) :: g
  type(t_list_geoinfo), intent(in) :: list
  integer :: nluse
  integer :: i, j
  character(:), allocatable :: fname

  if (list%f_rntype == 0) then
    g%lu = 0
    g%rn = list%rn0
  else if (list%f_rntype == 1) then
    fname = trim(p%dir_data) // "/" // trim(list%fn_rn)
    print *, "reading ", fname
    call fileio_read_matrix(fname, g%nx, g%ny, g%rn, p%f_input_mode)
  else
    ! 土地利用と粗度係数の関係の数をカウントする
    nluse = 0
    do i = 1, ubound(list%lu2rn, 2)
      if (list%lu2rn(1,i) < 0) exit
      nluse = nluse + 1
    end do
    if (nluse < 1) then
      print *, "error in geoimfo: need lu2rn(:,:) for f_rntype=2"
      stop
    end if
    do j = 1, g%ny
      do i = 1, g%nx
        if (g%x(i,j) == 0) cycle
        g%rn(i,j) = get_rn(list%lu2rn, nluse, g%lu(i,j))
        if (g%rn(i,j) < 0) then
          print *, "error in geoinfo: landuse categoly", g%lu(i,j), " at", i, j, " not found in lu2rn"
          stop
        end if
      end do
    end do
  end if

  if (list%f_masktype > 0) then
    do j = 1, g%ny
      do i = 1, g%nx
        if (g%x(i,j) == 0) then
          g%rn(i,j) = 0
        end if
      end do
    end do
  end if



contains
  function get_rn(lu2rn, nlu, lu) result(rn)
    real :: rn
    !real, intent(in) :: lu2rn(1:2,1:maxnluse)
    real, intent(in) :: lu2rn(:,:)
    integer, intent(in) :: nlu
    integer, intent(in) :: lu
    integer :: ilu
    rn = -1
    do ilu = 1, nlu
      if (nint(lu2rn(1,ilu)) == lu) then
        rn = lu2rn(2,ilu)
        exit
      end if
    end do
  end function
         

end subroutine


!----------------------------------------------------------------------
! 行ごとの計算対象範囲を求める
!----------------------------------------------------------------------
subroutine calc_wxy(p, g)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(inout) :: g
  integer :: i, j, s

  g%wy(1) = 1
  g%wy(2) = p%ny

  g%wx(1,:) = p%nx + 1
  g%wx(2,:) = 0

  do j = 1, p%ny
    do i = 1, p%nx
      s = g%x(i,j) + g%x(i+1,j-1) + g%x(i+1,j) + g%x(i+1,j+1)
      if (s > 0) then
        g%wx(1,j) = i
        exit
      end if
    end do
  end do

  do j = 1, p%ny
    do i = p%nx, 1, -1
      s = g%x(i,j) + g%x(i-1,j-1) + g%x(i-1,j) + g%x(i-1,j+1)
      if (s > 0) then
        g%wx(2,j) = i
        exit
      end if
    end do
  end do

end subroutine



end module
