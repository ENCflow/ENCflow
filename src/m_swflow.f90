module m_swflow
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_boundary, only : t_boundary
  use m_state, only : t_state
  use m_swflow_enc, only : m_swflow_enc_init, m_swflow_enc_calc, m_swflow_enc_dispose
  use m_swflow_stg, only : m_swflow_stg_init, m_swflow_stg_calc, m_swflow_stg_dispose
  use m_parallel, only : par_stop
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
    subroutine procedure_swflow_init(p, g, b, s)
      use m_sysparam, only : t_sysparam
      use m_geoinfo, only : t_geoinfo
      use m_boundary, only : t_boundary
      use m_state, only : t_state
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_boundary), intent(in) :: b
      type(t_state), intent(inout) :: s
    end subroutine

    subroutine procedure_swflow_calc(p, g, b, s, ierror)
      use m_sysparam, only : t_sysparam
      use m_geoinfo, only : t_geoinfo
      use m_boundary, only : t_boundary
      use m_state, only : t_state
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_boundary), intent(in) :: b
      type(t_state), intent(inout) :: s
      integer, intent(inout) :: ierror
    end subroutine

    subroutine procedure_swflow_dispose(p)
      use m_sysparam, only : t_sysparam
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
subroutine m_swflow_init(sw, p, g, b, s)
  type(t_swflow), intent(inout) :: sw
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(in) :: b
  type(t_state), intent(inout) :: s

  ! 地表水計算ルーチンのポインタをセット
  if (p%f_gridsystem == 0) then
    swflow_init => m_swflow_enc_init
    swflow_calc => m_swflow_enc_calc
    swflow_dispose => m_swflow_enc_dispose
  else if (p%f_gridsystem == 1) then
    swflow_init => m_swflow_stg_init
    swflow_calc => m_swflow_stg_calc
    swflow_dispose => m_swflow_stg_dispose
  else
    call par_stop("invalid gridsystem")
  end if
  sw%initialized = .true.

  call swflow_init(p, g, b, s)
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
  if (sw%initialized) continue  ! 引数未使用の警告を抑制
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
