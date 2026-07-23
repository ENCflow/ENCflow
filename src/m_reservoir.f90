module m_reservoir
  use m_sysparam, only : t_sysparam
  use m_parallel, only : par_info, par_stop, dcp
  use list_reservoir, only : t_list_reservoir, list_reservoir_read
  implicit none
  private

  public :: t_reservoir
  public :: m_reservoir_init
  public :: m_reservoir_dispose


  type t_reservoir
    integer :: rstype = 0
    logical :: initialized = .false.
  end type

contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine m_reservoir_init(rs, p)
  type(t_reservoir), intent(out) :: rs
  type(t_sysparam), intent(in) :: p
  type(t_list_reservoir) :: list
  if (p%initialized) continue
  !--- システムパラメータファイル内で設定ファイルが指定されている場合 ---
  if (len_trim(p%fn_reservoir) > 0) then
    !---- 設定ファイルを読み込む ----
    call list_reservoir_read(p, list)
    rs%rstype = list%rstype
  else
    rs%rstype = 0
    return
  end if
  rs%initialized = .true.
end subroutine

!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine m_reservoir_dispose(rs)
  type(t_reservoir), intent(inout) :: rs
  rs%initialized = .false.
end subroutine

end module
