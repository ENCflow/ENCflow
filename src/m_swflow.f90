module m_swflow
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_boundary, only : t_boundary
  use m_state, only : t_state
  use m_swflow_enc
  use m_swflow_stg
  use m_swflow_enc0
  implicit none
  private

  public :: t_swflow
  public :: m_swflow_init
  public :: m_swflow_calc
  public :: m_swflow_dispose


  type t_swflow
    logical :: initialized = .false.
  end type


  ! 地表水計算ルーチンのポインタを宣言しヌルポインタで初期化
  procedure(procedure_swflow_init), pointer :: swflow_init => null()
  procedure(procedure_swflow_calc), pointer :: swflow_calc => null()
  procedure(procedure_swflow_dispose), pointer :: swflow_dispose => null()


  !-------------------------------------------
  ! 地表水計算ルーチンのインターフェース
  !-------------------------------------------
  interface
    subroutine procedure_swflow_init(p, g, s)
      use m_sysparam
      use m_geoinfo
      use m_state
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_state), intent(in) :: s
    end subroutine

    subroutine procedure_swflow_calc(p, g, b, s, ierror)
      use m_sysparam
      use m_geoinfo
      use m_boundary
      use m_state
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_boundary), intent(in) :: b
      type(t_state), intent(inout) :: s
      integer, intent(inout) :: ierror
    end subroutine

    subroutine procedure_swflow_dispose(p)
      use m_sysparam
      type(t_sysparam), intent(in) :: p
    end subroutine
  end interface
  !-------------------------------------------


contains

!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! 
!----------------------------------------------------------------------
subroutine m_swflow_init(sw, p, g, s)
  type(t_swflow), intent(inout) :: sw
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo) :: g
  type(t_state) :: s

  ! 地表水計算ルーチンのポインタをセット
  if (p%f_gridsystem == 0) then
    swflow_init => m_swflow_enc_init
    swflow_calc => m_swflow_enc_calc
    swflow_dispose => m_swflow_enc_dispose
  else if (p%f_gridsystem == 1) then
    swflow_init => m_swflow_stg_init
    swflow_calc => m_swflow_stg_calc
    swflow_dispose => m_swflow_stg_dispose
  else if (p%f_gridsystem == 2) then
    swflow_init => m_swflow_enc0_init
    swflow_calc => m_swflow_enc0_calc
    swflow_dispose => m_swflow_enc0_dispose
  else
    print *, "invalid gridsystem"
    stop
  end if
  sw%initialized = .true.

  call swflow_init(p, g, s)
end subroutine

!----------------------------------------------------------------------
! 
!----------------------------------------------------------------------
subroutine m_swflow_calc(sw, p, g, b, s, ierror)
  type(t_swflow), intent(in) :: sw
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(in) :: b
  type(t_state), intent(inout) :: s
  integer, intent(inout) :: ierror
  if (sw%initialized) continue
  call swflow_calc(p, g, b, s, ierror)
end subroutine


!----------------------------------------------------------------------
! 
!----------------------------------------------------------------------
subroutine m_swflow_dispose(sw, p)
  type(t_swflow), intent(inout) :: sw
  type(t_sysparam), intent(in) :: p
  call swflow_dispose(p)
  swflow_init => null()
  swflow_calc => null()
  !swflow_dispose => null()
  sw%initialized = .false.
end subroutine


end module
