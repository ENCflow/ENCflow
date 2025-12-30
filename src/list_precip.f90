module list_precip
  use m_sysparam, only : t_sysparam
  implicit none
  private

  public :: t_list_precip
  public :: list_precip_read

  integer, parameter :: maxpathlen = 256
  integer, parameter :: nprmax = 999


  type t_list_precip
    integer :: prtype = 0              ! 0:降雨なし, 1:一様時系列, 2:分布×割合時系列, 3:分布時ファイルリスト
    real :: dt_prupdate = 1                        ! 降雨分布更新時間間隔 (min)
    real :: prval(1:2,1:nprmax) = -9999            ! 降水量時系列 (無意味な値で初期化しておく)
    character(len=maxpathlen) :: fn_prmap = ""     ! 降雨分布ファイル名
    real :: dt_maplist = 60                        ! 降雨分布ファイル時間間隔 (min)
    character(len=maxpathlen) :: fn_maplist = ""   ! 降雨分布ファイル名リスト名
  end type

contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! 降水設定ファイルを読み込む
!----------------------------------------------------------------------
subroutine list_precip_read(p, list)
  type(t_sysparam), intent(in) :: p
  type(t_list_precip), intent(inout) :: list
  integer :: prtype
  real :: dt_prupdate
  real :: prval(1:2,1:nprmax)
  character(:), allocatable :: fn_prmap
  real :: dt_maplist
  character(:), allocatable :: fn_maplist
  integer :: un
  namelist /list_precip/ prtype, dt_prupdate, prval, fn_prmap, dt_maplist, fn_maplist


  fn_prmap = list%fn_prmap
  dt_prupdate = list%dt_prupdate
  prtype = list%prtype
  prval = list%prval
  fn_prmap = list%fn_prmap
  dt_maplist = list%dt_maplist
  fn_maplist = list%fn_maplist

  !---- 設定ファイルを読み込む ----
  print *, "reading list_precip in ", trim(p%fn_precip)
  open(newunit=un, file=trim(p%fn_precip), status='old')
  read(un, list_precip)
  close(un)

  list%prtype = prtype
  list%dt_prupdate = dt_prupdate
  list%prval = prval
  list%fn_prmap = fn_prmap
  list%dt_maplist = dt_maplist
  list%fn_maplist = fn_maplist


end subroutine


!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

end module
