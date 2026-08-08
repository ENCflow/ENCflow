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


  !-------------------------------------------
  ! 地表水計算ルーチンのインターフェース
  ! (型成分で参照するため、型定義より前に置くこと)
  !-------------------------------------------
  abstract interface
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
      type(t_boundary), intent(inout) :: b   ! ダム節が診断量を更新(§22)
      type(t_state), intent(inout) :: s
      integer, intent(inout) :: ierror
    end subroutine

    subroutine procedure_swflow_dispose(p)
      use m_sysparam, only : t_sysparam
      type(t_sysparam), intent(in) :: p
    end subroutine
  end interface
  !-------------------------------------------


  type t_swflow
    ! 格子系実装(ENC/STG)への手続きポインタ。インスタンスの実体であり、
    ! モジュール変数にしないこと(将来のネスト格子等での多重化のため。
    ! nopass: 呼び出し時に自身を第1引数として渡さない通常の手続き)
    procedure(procedure_swflow_init),    pointer, nopass :: init    => null()
    procedure(procedure_swflow_calc),    pointer, nopass :: calc    => null()
    procedure(procedure_swflow_dispose), pointer, nopass :: dispose => null()
    logical :: initialized = .false.
  end type


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

  ! 地表水計算ルーチンのポインタをこのインスタンスに束縛する
  if (p%f_gridsystem == 0) then
    sw%init    => m_swflow_enc_init
    sw%calc    => m_swflow_enc_calc
    sw%dispose => m_swflow_enc_dispose
  else if (p%f_gridsystem == 1) then
    sw%init    => m_swflow_stg_init
    sw%calc    => m_swflow_stg_calc
    sw%dispose => m_swflow_stg_dispose
  else
    call par_stop("invalid gridsystem")
  end if
  sw%initialized = .true.

  call sw%init(p, g, b, s)
end subroutine

!----------------------------------------------------------------------
! 
!----------------------------------------------------------------------
subroutine m_swflow_calc(sw, p, g, b, s, ierror)
  type(t_swflow), intent(in) :: sw
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(inout) :: b
  type(t_state), intent(inout) :: s
  integer, intent(inout) :: ierror
  if (.not. sw%initialized) call par_stop("m_swflow_calc: not initialized")
  call sw%calc(p, g, b, s, ierror)
end subroutine


!----------------------------------------------------------------------
! 
!----------------------------------------------------------------------
subroutine m_swflow_dispose(sw, p)
  type(t_swflow), intent(inout) :: sw
  type(t_sysparam), intent(in) :: p
  call sw%dispose(p)
  sw%init    => null()
  sw%calc    => null()
  sw%dispose => null()
  sw%initialized = .false.
end subroutine


end module
