!======================================================================
module list_tide
  use m_sysparam, only : t_sysparam
  use m_parallel, only : par_info, par_stop
  implicit none
  private

  public :: t_list_tide
  public :: list_tide_read

  integer, parameter :: maxpathlen = 256
  integer, parameter :: ntimax = 999


  type t_list_tide
    ! 潮位タイプ (0:なし, 1:一様固定値, 2:一様時系列,
    !             3:分布×倍率時系列, 4:分布ファイルリスト)
    integer :: titype = 0
    real :: ti0 = 0.0                              ! 一様固定潮位 (m。titype=1)
    real :: hsea0 = 1.0                            ! 海セルの見かけ水柱厚 (m)
    real :: dt_tiupdate = 1                        ! 潮位更新時間間隔 (min)
    real :: tival(1:2,1:ntimax) = -9999            ! 潮位時系列 (時刻(min), 潮位(m)または倍率)
    character(len=maxpathlen) :: fn_timap = ""     ! 潮位分布ファイル名 (titype=3)
    character(len=maxpathlen) :: fn_timaplist = "" ! 潮位分布ファイルリスト名 (titype=4)
    real :: dt_timaplist = 60                      ! 潮位分布ファイル時間間隔 (min)
    character(len=80) :: dt_timaplist_c = ""       ! 潮位分布ファイル時間間隔 (h, m, s)
  end type

contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! 潮位設定ファイルを読み込む
!----------------------------------------------------------------------
subroutine list_tide_read(p, list)
  type(t_sysparam), intent(in) :: p
  type(t_list_tide), intent(inout) :: list
  integer :: titype
  real :: ti0
  real :: hsea0
  real :: dt_tiupdate
  real :: tival(1:2,1:ntimax)
  character(:), allocatable :: fn_timap
  character(:), allocatable :: fn_timaplist
  real :: dt_timaplist
  character(:), allocatable :: dt_timaplist_c
  integer :: un
  integer :: ios
  character(len=1024) :: iom
  namelist /list_tide/ titype, ti0, hsea0, dt_tiupdate, tival, &
                       fn_timap, fn_timaplist, dt_timaplist, dt_timaplist_c

  titype = list%titype
  ti0 = list%ti0
  hsea0 = list%hsea0
  dt_tiupdate = list%dt_tiupdate
  tival = list%tival
  fn_timap = list%fn_timap
  fn_timaplist = list%fn_timaplist
  dt_timaplist = list%dt_timaplist
  dt_timaplist_c = list%dt_timaplist_c

  !---- 設定ファイルを読み込む ----
  call par_info("reading list_tide in "//trim(p%fn_tide))
  open(newunit=un, file=trim(p%fn_tide), status='old')
  read(un, nml=list_tide, iostat=ios, iomsg=iom)
  if (ios /= 0) call par_stop("list_tide: failed to read namelist: "//trim(iom))
  close(un)

  ! 解釈・検証・導出は m_tide の init が行う(list_* 層の共通契約)

  list%titype = titype
  list%ti0 = ti0
  list%hsea0 = hsea0
  list%dt_tiupdate = dt_tiupdate
  list%tival = tival
  list%fn_timap = fn_timap
  list%fn_timaplist = fn_timaplist
  list%dt_timaplist = dt_timaplist
  list%dt_timaplist_c = dt_timaplist_c

end subroutine


!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

end module
