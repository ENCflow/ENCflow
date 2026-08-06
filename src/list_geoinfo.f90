!======================================================================
module list_geoinfo
  use m_sysparam, only : t_sysparam
  use m_parallel, only : par_info, par_stop
  implicit none
  private

  public :: t_list_geoinfo
  public :: list_geoinfo_read

  integer, parameter :: maxpathlen = 256
  integer, parameter :: maxnluse = 100
  integer, parameter :: maxnamelen = 32

  type t_list_geoinfo
    integer :: nx = 0
    integer :: ny = 0
    real :: dx = 0
    real :: dy = 0
    real :: lx = 0
    real :: ly = 0
    integer :: epsg = 0                        ! 格子の CRS の EPSG コード(0:不明。GeoTIFF 用)
    real :: z0 = 0                             ! 地盤高固定値
    real :: rn0 = 0.015                        ! 粗度係数固定値
    real :: mag_z = 1                          ! 地盤高倍率
    real :: min_gv = 0.001                     ! 家屋の空隙率の最小値
    real :: min_bb = 0.001                     ! 家屋の平均サイズの最小値
    real :: depth_rw = 0.0                     ! 河道マスク部の掘り込み深さ(河道マスク有りの場合のみ有効)
    real :: rn0_rw = -1.0                      ! 河道マスク部の固定粗度係数(負値の場合は設定せず)
    integer :: f_sdtype = 0                    ! 土層厚タイプ (0:固定値, 1:ファイル)。gwflow 用
    real :: sd0 = 0.0                          ! 土層厚固定値 (m)
    real :: sy0 = 0.2                          ! 比湧水量(= 有効間隙率 n_e。gwflow 用)
    character(len=maxnamelen) :: f_user_routine = ""  ! ユーザールーチン識別名
    integer :: f_ztype = 0                     ! 地盤高タイプ (0:固定値, 1:ファイル)
    integer :: f_lusetype = 0                  ! 土地利用データの有無 (0:なし, 1:ファイル)
    integer :: f_rntype = 0                    ! 粗度係数タイプ (0:固定値, 1:ファイル, 2:土地利用から計算)
    integer :: f_masktype = 0                  ! 領域マスクのタイプ (0:なし, 1:ファイル, 2:自動)
    integer :: f_edge_sw = 0                   ! 領域端部を海に設定
    character(len=maxpathlen) :: fn_z = ""     ! 地盤高ファイル名
    character(len=maxpathlen) :: fn_mask = ""  ! 領域マスクファイル名
    character(len=maxpathlen) :: fn_sw = ""    ! 海域マスクファイル名
    character(len=maxpathlen) :: fn_rw = ""    ! 河道マスクファイル名
    character(len=maxpathlen) :: fn_depth_rw = ""  ! 河床掘り込み深さ分布ファイル名(河道セルのみ有効。無指定なら depth_rw)
    character(len=maxpathlen) :: fn_rn = ""    ! 地盤高ファイル名
    character(len=maxpathlen) :: fn_luse = ""  ! 土地利用ファイル名
    character(len=maxpathlen) :: fn_gv = ""    ! 家屋の空隙率ファイル名
    character(len=maxpathlen) :: fn_bb = ""    ! 家屋の平均寸法ファイル名
    character(len=maxpathlen) :: fn_rscap = "" ! ため池の限界貯留高ファイル名
    character(len=maxpathlen) :: fn_sd = ""    ! 土層厚ファイル名
    real :: lu2rn(1:2,1:maxnluse) = -999       ! 土地利用と粗度係数の対応
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
  integer :: epsg               ! 格子の CRS の EPSG コード(0:不明)
  real :: z0                    ! 地盤高固定値
  real :: rn0                   ! 粗度係数固定値
  real :: mag_z                 ! 地盤高倍率
  real :: min_gv                ! 家屋の空隙率の最小値
  real :: min_bb                ! 家屋の平均サイズの最小値
  real :: depth_rw              ! 河道マスク部の掘り込み深さ
  real :: rn0_rw                ! 河道マスク部の固定粗度係数
  integer :: f_sdtype           ! 土層厚タイプ (0:固定値, 1:ファイル)
  real :: sd0                   ! 土層厚固定値 (m)
  real :: sy0                   ! 比湧水量(= 有効間隙率 n_e)
  character(len=maxnamelen) :: f_user_routine  ! ユーザールーチン識別名
  integer :: f_ztype            ! 地盤高タイプ (0:固定値, 1:テキストファイル)
  integer :: f_lusetype         ! 土地利用データの有無 (0:なし, 1:テキストファイル)
  integer :: f_rntype           ! 粗度係数タイプ (0:固定値, 1:土地利用ファイル)
  integer :: f_masktype         ! 粗度係数タイプ (0:なし, 1:テキストファイル)
  integer :: f_edge_sw          ! 領域単部を海に設定
  character(:), allocatable :: fn_z      ! 地盤高ファイル名
  character(:), allocatable :: fn_rn     ! 粗度係数ファイル名
  character(:), allocatable :: fn_mask   ! 領域マスクファイル名
  character(:), allocatable :: fn_sw     ! 海域マスクファイル名
  character(:), allocatable :: fn_rw     ! 河道マスクファイル名
  character(:), allocatable :: fn_depth_rw  ! 河床掘り込み深さ分布ファイル名
  character(:), allocatable :: fn_luse   ! 土地利用ファイル名
  character(:), allocatable :: fn_gv     ! 家屋の空隙率ファイル名
  character(:), allocatable :: fn_bb     ! 家屋の平均寸法ファイル名
  character(:), allocatable :: fn_rscap  ! ため池の限界貯留高ファイル名
  character(:), allocatable :: fn_sd     ! 土層厚ファイル名
  real :: lu2rn(1:2,1:maxnluse)          ! 土地利用と粗度係数の対応
  integer :: un
  integer :: ios
  character(len=1024) :: iom
  namelist /list_geoinfo/ nx, ny, dx, dy, lx, ly, epsg, z0, rn0, mag_z, min_gv, min_bb, depth_rw, rn0_rw, &
                          sd0, sy0, &
                          f_user_routine, &
                          f_ztype, f_lusetype, f_rntype, f_masktype, f_edge_sw, f_sdtype, &
                          fn_z, fn_mask, fn_sw, fn_rw, fn_depth_rw, &
                          fn_rn, fn_luse, fn_gv, fn_bb, fn_rscap, fn_sd, lu2rn
  ! ネームリストにありながらファイルに記述のなかった変数は、
  ! 事前に保存されていた値がそのまま保持される
  nx = list%nx
  ny = list%ny
  dx = list%dx
  dy = list%dy
  lx = list%lx
  ly = list%ly
  epsg = list%epsg
  z0 = list%z0
  rn0 = list%rn0
  mag_z = list%mag_z
  min_gv = list%min_gv
  min_bb = list%min_bb
  depth_rw = list%depth_rw
  rn0_rw = list%rn0_rw
  f_sdtype = list%f_sdtype
  sd0 = list%sd0
  sy0 = list%sy0
  f_user_routine = list%f_user_routine
  f_ztype = list%f_ztype
  f_lusetype = list%f_lusetype
  f_rntype = list%f_rntype
  f_masktype = list%f_masktype
  f_edge_sw = list%f_edge_sw
  fn_z = list%fn_z
  fn_mask = list%fn_mask
  fn_sw = list%fn_sw
  fn_rw = list%fn_rw
  fn_depth_rw = list%fn_depth_rw
  fn_rn = list%fn_rn
  fn_luse = list%fn_luse
  fn_gv = list%fn_gv
  fn_bb = list%fn_bb
  fn_rscap = list%fn_rscap
  fn_sd = list%fn_sd
  lu2rn = list%lu2rn

  call par_info("reading list_geoinfo in "//trim(p%fn_geoinfo))
  open(newunit=un, file=trim(p%fn_geoinfo), status='old')
  read(un, nml=list_geoinfo, iostat=ios, iomsg=iom)
  if (ios /= 0) call par_stop("list_geoinfo 読込失敗: "//trim(iom))
  close(un)

  ! 領域指定の判別・補完・検証は m_geoinfo(resolve_geometry)が行う。
  ! この層は生の値(未指定 = 0 の番兵)を運ぶだけ(list_* 層の共通契約)

  list%nx = nx
  list%ny = ny
  list%dx = dx
  list%dy = dy
  list%lx = lx
  list%ly = ly
  list%epsg = epsg
  list%z0 = z0
  list%rn0 = rn0
  list%mag_z = mag_z
  list%min_gv = min_gv
  list%min_bb = min_bb
  list%depth_rw = depth_rw
  list%rn0_rw = rn0_rw
  list%f_sdtype = f_sdtype
  list%sd0 = sd0
  list%sy0 = sy0
  list%f_user_routine = f_user_routine
  list%f_ztype = f_ztype
  list%f_lusetype = f_lusetype
  list%f_rntype = f_rntype
  list%f_masktype = f_masktype
  list%f_edge_sw = f_edge_sw
  list%fn_z = fn_z
  list%fn_mask = fn_mask
  list%fn_sw = fn_sw
  list%fn_rw = fn_rw
  list%fn_depth_rw = fn_depth_rw
  list%fn_rn = fn_rn
  list%fn_luse = fn_luse
  list%fn_gv = fn_gv
  list%fn_bb = fn_bb
  list%fn_rscap = fn_rscap
  list%fn_sd = fn_sd
  list%lu2rn = lu2rn

end subroutine

!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

end module
