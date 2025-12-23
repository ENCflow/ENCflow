module m_boundary
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  implicit none
  private

  public :: t_boundary
  public :: m_boundary_init
  public :: m_boundary_dispose

  type t_bd
    integer :: bdtype
    real :: val
    integer, allocatable :: ncell(:)
    integer, allocatable :: bdx(:)
    integer, allocatable :: bdy(:)
  end type

  type t_boundary
    integer :: nbd
    integer :: ninf
    integer :: noutf
    integer, allocatable :: bdinf(:)
    integer, allocatable :: bdoutf(:)
    type(t_bd), allocatable :: bd
    logical :: initialized = .false.           ! 初期化済みフラグ
  end type


contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine m_boundary_init(b, p, g)
  type(t_boundary), intent(inout) :: b
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  if (p%initialized) continue
  if (g%initialized) continue
  b%initialized = .true.
end subroutine

!----------------------------------------------------------------------
!----------------------------------------------------------------------
subroutine m_boundary_dispose(b)
  type(t_boundary), intent(inout) :: b
  if (b%initialized) continue
end subroutine

!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

end module
