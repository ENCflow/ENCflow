module list_tide
  use m_sysparam, only : t_sysparam
  use m_parallel, only : par_info
  implicit none
  private

  public :: t_list_tide
  public :: list_tide_read

  integer, parameter :: maxpathlen = 256
  integer, parameter :: ntimax = 999


  type t_list_tide
    integer :: titype = 0                          ! 0:潮位なし, 1:時系列, 2:分布ファイル
    real :: tival(1:2,1:ntimax) = -9999            ! 潮位時系列 (無意味な値で初期化しておく)
    !character(len=maxpathlen) :: fn_timap = ""     ! 潮位分布ファイル名
  end type

contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! 潮位　設定ファイルを読み込む
!----------------------------------------------------------------------
subroutine list_tide_read(p, list)
  type(t_sysparam), intent(in) :: p
  type(t_list_tide), intent(inout) :: list
  integer :: titype
  real :: tival(1:2,1:ntimax)
  !character(:), allocatable :: fn_timap
  integer :: un
  namelist /list_tide/ titype, tival !, fn_timap


  !fn_timap = list%fn_timap
  titype = list%titype
  tival = list%tival

  !---- 設定ファイルを読み込む ----
  call par_info("reading list_tide in "//trim(p%fn_tide))
  open(newunit=un, file=trim(p%fn_tide), status='old')
  read(un, list_tide)
  close(un)

  list%titype = titype
  list%tival = tival
  !list%fn_timap = fn_timap


end subroutine


!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

end module
