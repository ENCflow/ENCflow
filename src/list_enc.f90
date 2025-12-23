module list_enc
  use m_sysparam, only : t_sysparam
  implicit none
  private

  public :: t_list_enc
  public :: list_enc_read


  type t_list_enc
    integer :: f_gravity_correction = 0       ! 重力の補正
    integer :: f_exflux_reduction = 1         ! reduction of excessive flux
    integer :: f_hcap_upwind = 1              ! 上流側水深によるセル境界水深の制限
    integer :: f_adaptive_runge = 1           ! 適応的ルンゲクッタ
    integer :: f_friction_fastmath = 0        ! 摩擦項計算の高速化
    integer :: f_advection_tvd = 0            ! 移流項にTVDスキームを使用　
    integer :: f_rivermouth_drop = 0          ! 河口から海へ段落ち
    real :: p_diagratio = 2 / (2 + sqrt(2.))  ! ratio of diagonal component
    real :: p_adv_upwind_index = 0.0          ! upwind index of advection term
    real :: p_adprunge_thresh = 2.0           ! threshold of adaptive Runge-Kutta (1.1~)
  end type


contains
 
!======================================================================
!========================== PUBLIC ROUTINES ===========================
!======================================================================

!----------------------------------------------------------------------
! ENC設定ファイルを読み込む　
!----------------------------------------------------------------------
subroutine list_enc_read(p, list)
  type(t_sysparam), intent(in) :: p
  type(t_list_enc), intent(inout) :: list
  integer :: f_gravity_correction       ! 重力の補正
  integer :: f_exflux_reduction         ! reduction of excessive flux
  integer :: f_hcap_upwind              ! 上流側水深によるセル境界水深の制限
  integer :: f_adaptive_runge           ! 適応的簡易ルンゲクッタ
  integer :: f_friction_fastmath        ! 摩擦項計算の高速化
  integer :: f_advection_tvd            ! 移流項にTVDスキームを使用　
  integer :: f_rivermouth_drop          ! 河口から海へ段落ち
  real :: p_diagratio                   ! ratio of diagonal component
  real :: p_adv_upwind_index            ! upwind index of advection term
  real :: p_adprunge_thresh             ! threshold of adaptive Runge-Kutta (1.1~)
  integer :: un

  namelist /list_enc/ f_gravity_correction, f_exflux_reduction, f_hcap_upwind, &
                      f_friction_fastmath, f_advection_tvd, f_rivermouth_drop, &
                      f_adaptive_runge, p_diagratio, p_adv_upwind_index, p_adprunge_thresh

  f_gravity_correction = list%f_gravity_correction 
  f_exflux_reduction = list%f_exflux_reduction 
  f_hcap_upwind = list%f_hcap_upwind 
  f_adaptive_runge = list%f_adaptive_runge 
  f_friction_fastmath = list%f_friction_fastmath 
  f_advection_tvd = list%f_advection_tvd 
  f_rivermouth_drop = list%f_rivermouth_drop 
  p_diagratio = list%p_diagratio 
  p_adv_upwind_index = list%p_adv_upwind_index 
  p_adv_upwind_index = list%p_adv_upwind_index 
  p_adprunge_thresh = list%p_adprunge_thresh 

  ! ネームリストにありながらファイルに記述のなかった変数は、
  ! 事前に保存されていた値がそのまま保持される
  print *, "reading list_enc in ", trim(p%fn_enc)
  open(newunit=un, file=trim(p%fn_enc), status='old')
  read(un, list_enc)
  close(un)

  list%f_gravity_correction = f_gravity_correction 
  list%f_exflux_reduction = f_exflux_reduction 
  list%f_hcap_upwind = f_hcap_upwind 
  list%f_adaptive_runge = f_adaptive_runge 
  list%f_friction_fastmath = f_friction_fastmath 
  list%f_advection_tvd = f_advection_tvd 
  list%f_rivermouth_drop = f_rivermouth_drop 
  list%p_diagratio = min(max(p_diagratio, 0.0), 1.0)                ! 値を0.0~1.0に制限
  list%p_adv_upwind_index = min(max(p_adv_upwind_index, 0.0), 1.0)  ! 値を0.0~1.0に制限
  list%p_adprunge_thresh = max(p_adprunge_thresh, 1.1)              ! 値を1.1以上に制限

end subroutine


!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

end module
