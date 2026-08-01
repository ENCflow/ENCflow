module m_sysdep_util
  use m_parallel, only : is_root
  implicit none
  private

  public :: sysdep_mkdir
  public :: sysdep_copy_to_dir

contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! ディレクトリを作成
!----------------------------------------------------------------------
subroutine sysdep_mkdir(dirname)
  !type(t_sysparam), intent(in) :: p
  character(len=*), intent(in) :: dirname
  character(len=256) :: command
  integer :: i
  if (.not. is_root) return
  command = "mkdir -p "//trim(dirname)
  call execute_command_line(trim(command), exitstat=i)
  if (i /= 0) then
    stop
  end if
end subroutine


!----------------------------------------------------------------------
! ファイルをディレクトリにコピー
!----------------------------------------------------------------------
subroutine sysdep_copy_to_dir(filename, dirname)
  character(len=*), intent(in) :: filename
  character(len=*), intent(in) :: dirname
  character(len=256) :: command
  integer :: i
  if (.not. is_root) return
  if (len_trim(filename) > 0) then
    command = "cp -f "//trim(filename)//" "//trim(dirname)
    call execute_command_line(trim(command), exitstat=i)
    if (i /= 0) stop
  end if
end subroutine


end module
