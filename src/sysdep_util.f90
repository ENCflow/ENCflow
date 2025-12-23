module sysdep_util
  use m_sysparam, only : t_sysparam
  implicit none
  private

  public :: sysdep_create_resultdir
  public :: sysdep_save_paramfile
  public :: sysdep_compress

contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! 計算結果保存用のディレクトリを作成
!----------------------------------------------------------------------
subroutine sysdep_create_resultdir(p)
  type(t_sysparam), intent(in) :: p
  character(len=256) :: command
  integer :: i

  command = "mkdir -p "//trim(p%dir_result)
  call execute_command_line(trim(command), exitstat=i)
  if (i /= 0) then
    stop
  end if

  command = "mkdir -p "//trim(p%dir_result)//"/fluxes"
  call execute_command_line(trim(command), exitstat=i)
  if (i /= 0) then
    stop
  end if

  command = "mkdir -p "//trim(p%dir_result)//"/probes"
  call execute_command_line(trim(command), exitstat=i)
  if (i /= 0) then
    stop
  end if
end subroutine


!----------------------------------------------------------------------
! 全てのパラメータファイルを保存用ディレクトリにコピー
!----------------------------------------------------------------------
subroutine sysdep_save_paramfile(p)
  type(t_sysparam), intent(in) :: p
  character(len=256) :: command

  call savefile(p%fn_sysparam, p%dir_result)
  call savefile(p%fn_geoinfo, p%dir_result)
  call savefile(p%fn_initial, p%dir_result)
  call savefile(p%fn_precip, p%dir_result)
  call savefile(p%fn_tide, p%dir_result)
  call savefile(p%fn_boundary, p%dir_result)
  call savefile(p%fn_record, p%dir_result)
  call savefile(p%fn_enc, p%dir_result)

contains
  subroutine savefile(filename, dirname)
    character(len=*), intent(in) :: filename
    character(len=*), intent(in) :: dirname
    integer :: i
    if (len_trim(filename) > 0) then
      command = "cp -f "//trim(filename)//" "//trim(dirname)
      call execute_command_line(trim(command), exitstat=i)
      if (i /= 0) stop
    end if
  end subroutine
end subroutine

!----------------------------------------------------------------------
! 全てのパラメータファイルを保存用ディレクトリにコピー
!----------------------------------------------------------------------
subroutine sysdep_compress(fname)
  character(len=*) :: fname
  character(len=256) :: command
  integer :: i
  command = "gzip -f --best "//trim(fname)//" &"
  call execute_command_line(trim(command), exitstat=i)
  if (i /= 0) then
    stop
  end if
end subroutine

end module
