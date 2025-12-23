!======================================================================
module list_geoinfo
  use m_sysparam, only : t_sysparam
  implicit none
  private

  public :: t_list_geoinfo
  public :: list_geoinfo_read

  integer, parameter :: maxpathlen = 256
  integer, parameter :: maxnluse = 100

  type t_list_geoinfo
    integer :: nx = 0
    integer :: ny = 0
    real :: dx = 0
    real :: dy = 0
    real :: lx = 0
    real :: ly = 0
    real :: z0 = 0                            ! 地盤高固定値
    real :: rn0 = 0.015                       ! 粗度係数固定値
    real :: mag_z = 1                         ! 地盤高倍率
    real :: min_gv = 0.001                    ! 家屋の空隙率の最小値
    real :: min_bb = 0.001                    ! 家屋の平均サイズの最小値
    integer :: f_user_routine_id = 0          ! ユーザールーチンID
    integer :: f_ztype = 0                    ! 地盤高タイプ (0:固定値, 1:ファイル)
    integer :: f_lusetype = 0                 ! 土地利用データの有無 (0:なし, 1:ファイル)
    integer :: f_rntype = 0                   ! 粗度係数タイプ (0:固定値, 1:ファイル, 2:土地利用から計算)
    integer :: f_masktype = 0                 ! 領域マスクのタイプ (0:なし, 1:ファイル, 2:自動)
    integer :: f_edge_sw = 0                  ! 領域単部を海に設定
    character(len=maxpathlen) :: fn_z = ""    ! 地盤高ファイル名
    character(len=maxpathlen) :: fn_mask = "" ! 領域マスクファイル名
    character(len=maxpathlen) :: fn_sw = ""   ! 海域マスクファイル名
    character(len=maxpathlen) :: fn_rw = ""   ! 河道マスクファイル名
    character(len=maxpathlen) :: fn_rn = ""   ! 地盤高ファイル名
    character(len=maxpathlen) :: fn_luse = "" ! 土地利用ファイル名
    character(len=maxpathlen) :: fn_gv = ""   ! 家屋の空隙率ファイル名
    character(len=maxpathlen) :: fn_bb = ""   ! 家屋の平均寸法ファイル名
    real :: lu2rn(1:2,1:maxnluse) = -999      ! 土地利用と粗度係数の対応
  end type


contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! 地理情報パラメータファイルを読み込む
!----------------------------------------------------------------------
subroutine list_geoinfo_read(p, list)
  type(t_sysparam), intent(in) :: p
  type(t_list_geoinfo), intent(inout) :: list
  integer :: nx, ny
  real :: dx, dy
  real :: lx, ly
  real :: z0                    ! 地盤高固定値
  real :: rn0                   ! 粗度係数固定値
  real :: mag_z                 ! 地盤高倍率
  real :: min_gv                ! 家屋の空隙率の最小値
  real :: min_bb                ! 家屋の平均サイズの最小値
  integer :: f_user_routine_id  ! ユーザールーチンID
  integer :: f_ztype            ! 地盤高タイプ (0:固定値, 1:テキストファイル)
  integer :: f_lusetype         ! 土地利用データの有無 (0:なし, 1:テキストファイル)
  integer :: f_rntype           ! 粗度係数タイプ (0:固定値, 1:土地利用ファイル)
  integer :: f_masktype         ! 粗度係数タイプ (0:なし, 1:テキストファイル)
  integer :: f_edge_sw          ! 領域単部を海に設定
  integer :: error
  character(:), allocatable :: fn_z      ! 地盤高ファイル名
  character(:), allocatable :: fn_rn     ! 粗度係数ファイル名
  character(:), allocatable :: fn_mask   ! 領域マスクファイル名
  character(:), allocatable :: fn_sw     ! 海域マスクファイル名
  character(:), allocatable :: fn_rw     ! 河道マスクファイル名
  character(:), allocatable :: fn_luse   ! 土地利用ファイル名
  character(:), allocatable :: fn_gv     ! 家屋の空隙率ファイル名
  character(:), allocatable :: fn_bb     ! 家屋の平均寸法ファイル名
  real :: lu2rn(1:2,1:maxnluse)          ! 土地利用と粗度係数の対応
  integer :: un
  namelist /list_geoinfo/ nx, ny, dx, dy, lx, ly, z0, rn0, mag_z, min_gv, min_bb, &
                          f_user_routine_id, f_ztype, f_lusetype, f_rntype, f_masktype, f_edge_sw, &
                          fn_z, fn_mask, fn_sw, fn_rw, fn_rn, fn_luse, fn_gv, fn_bb, lu2rn
  error = 0

  ! ネームリストにありながらファイルに記述のなかった変数は、
  ! 事前に保存されていた値がそのまま保持される
  nx = list%nx
  ny = list%ny
  dx = list%dx
  dy = list%dy
  lx = list%lx
  ly = list%ly
  z0 = list%z0
  rn0 = list%rn0
  mag_z = list%mag_z
  min_gv = list%min_gv
  min_bb = list%min_bb
  f_user_routine_id = list%f_user_routine_id
  f_ztype = list%f_ztype
  f_lusetype = list%f_lusetype
  f_rntype = list%f_rntype
  f_masktype = list%f_masktype
  f_edge_sw = list%f_edge_sw
  fn_z = list%fn_z
  fn_mask = list%fn_mask
  fn_sw = list%fn_sw
  fn_rw = list%fn_rw
  fn_rn = list%fn_rn
  fn_luse = list%fn_luse
  fn_gv = list%fn_gv
  fn_bb = list%fn_bb
  lu2rn = list%lu2rn

  print *, "reading list_geoinfo in ", trim(p%fn_geoinfo)
  open(newunit=un, file=trim(p%fn_geoinfo), status='old')
  read(un, list_geoinfo)
  close(un)

  if (dx == 0) then
    if (nx == 0) then
      print *, "error in list_geoinfo: nx == 0"
      error = error + 1
    end if
    if (lx == 0) then
      print *, "error in list_geoinfo: dx == 0 and lx == 0"
      error = error + 1
    end if
    if (nx > 0) dx = lx / nx
  end if

  if (dy == 0) then
    if (ny == 0) then
      print *, "error in list_geoinfo: ny == 0"
      error = error + 1
    end if
    if (ly == 0) then
      print *, "error in list_geoinfo: dy == 0 and ly == 0"
      error = error + 1
    end if
    if (ny > 0) dy = ly / ny
  end if

  if (lx == 0) then
    lx = nx * dx
  end if

  if (ly == 0) then
    ly = ny * dy
  end if

  if (error > 0) stop

  list%nx = nx
  list%ny = ny
  list%dx = dx
  list%dy = dy
  list%lx = lx
  list%ly = ly
  list%z0 = z0
  list%rn0 = rn0
  list%mag_z = mag_z
  list%min_gv = min_gv
  list%min_bb = min_bb
  list%f_user_routine_id = f_user_routine_id
  list%f_ztype = f_ztype
  list%f_lusetype = f_lusetype
  list%f_rntype = f_rntype
  list%f_masktype = f_masktype
  list%f_edge_sw = f_edge_sw
  list%fn_z = fn_z
  list%fn_mask = fn_mask
  list%fn_sw = fn_sw
  list%fn_rw = fn_rw
  list%fn_rn = fn_rn
  list%fn_luse = fn_luse
  list%fn_gv = fn_gv
  list%fn_bb = fn_bb
  list%lu2rn = lu2rn

end subroutine

!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

end module
