module m_tide
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use list_tide, only : t_list_tide, list_tide_read
  implicit none
  private

  public :: t_tide
  public :: m_tide_init
  public :: m_tide_dispose

  type t_tide
    integer :: titype
    logical :: initialized = .false.
  end type


contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine m_tide_init(ti, p, g)
  type(t_tide), intent(inout) :: ti
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_list_tide) :: list
  if (p%initialized) continue
  if (g%initialized) continue

  if (len_trim(p%fn_tide) > 0) then
    !---- 設定ファイルを読み込む ----
    call list_tide_read(p, list)
    ti%titype = list%titype
    !tival = list%tival
  else
    ti%titype = 0
  end if


  ti%initialized = .true.
end subroutine

!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine m_tide_dispose(ti)
  type(t_tide), intent(inout) :: ti
  if (ti%initialized) continue
end subroutine

!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

end module
