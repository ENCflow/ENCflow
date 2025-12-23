module list_boundary
  use m_sysparam, only : t_sysparam
  implicit none
  private

  public :: t_list_boundary
  public :: list_boundary_read

  type t_list_boundary
    integer :: bdype = 0
  end type

contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! 降水設定ファイルを読み込む
!----------------------------------------------------------------------
subroutine list_boundary_read(p, list)
  type(t_sysparam), intent(in) :: p
  type(t_list_boundary), intent(inout) :: list
  integer :: bdype
  integer :: un
  namelist /list_boundary/ bdype


  bdype = list%bdype

  !---- 設定ファイルを読み込む ----
  print *, "reading list_boundary in ", trim(p%fn_boundary)
  open(newunit=un, file=trim(p%fn_boundary), status='old')
  read(un, list_boundary)
  close(un)

  list%bdype = bdype


end subroutine


!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

end module
