module list_reservoir
  use m_sysparam, only : t_sysparam
  use m_parallel, only : par_info, par_stop
  implicit none
  private

  public :: t_list_reservoir
  public :: list_reservoir_read

  integer, parameter :: maxpathlen = 256


  type t_list_reservoir
    integer :: rstype = 0
  end type

contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! 降水設定ファイルを読み込む
!----------------------------------------------------------------------
subroutine list_reservoir_read(p, list)
  type(t_sysparam), intent(in) :: p
  type(t_list_reservoir), intent(inout) :: list
  integer :: rstype
  integer :: un
  integer :: ios
  character(len=1024) :: iom
  namelist /list_reservoir/ rstype

  rstype = list%rstype

  !---- 設定ファイルを読み込む ----
  call par_info("reading list_reservoir in "//trim(p%fn_precip))
  open(newunit=un, file=trim(p%fn_reservoir), status='old')
  read(un, nml=list_reservoir, iostat=ios, iomsg=iom)
  if (ios /= 0) call par_stop("list_reservoir 読込失敗: "//trim(iom))
  close(un)

  list%rstype = rstype

end subroutine


!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

end module
