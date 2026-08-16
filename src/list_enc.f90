module list_enc
  use m_sysparam, only : t_sysparam
  use m_parallel, only : par_info, par_stop
  implicit none
  private

  public :: t_list_enc
  public :: list_enc_read


  type t_list_enc
    integer :: f_gravity_correction = 1       ! 重力の補正(急勾配地形での斜面方向
                                              !   重力の誤差を補正)
    integer :: f_exflux_reduction = 1         ! reduction of excessive flux
    integer :: f_hcap_upwind = 1              ! 上流側水深によるセル境界水深の制限
    integer :: f_adaptive_runge = 1           ! 適応的ルンゲクッタ
    integer :: f_friction_fastmath = 0        ! 摩擦項計算の高速化 (0:厳密,
                                              !   1~5:テーブル近似。大きいほど粗く速い)
    integer :: f_advection_tvd = 0            ! 移流項にTVDスキームを使用　
    integer :: f_advection_runge = 0          ! 移流項をルンゲクッタで更新
    integer :: f_rivermouth_drop = 0          ! 河口から海へ段落ち
    integer :: f_diffusion_term = 0           ! 拡散項の計算 (0:無効, 1:定数, 2:ゼロ方程式)
    real :: p_diagratio = 2 / (2 + sqrt(2.))  ! ratio of diagonal component
    real :: p_adv_upwind_index = 0.5          ! 移流項の風上化指数 (0~1。
                                              !   0:中心差分, 1:1次精度風上差分)
    real :: p_adprunge_thresh = 1.5           ! threshold of adaptive Runge-Kutta (1.1~)
    real :: p_diffusion_nu = 0.0              ! 拡散項の動粘性係数 (m2/s。モデル2では
                                              !   加算のバックグラウンド粘性)
    real :: p_diffusion_alpha = 0.41 / 6      ! ゼロ方程式モデルの係数 α (ν=ν0+α·u*·h。
                                              !   既定はカルマン定数/6 = Elder 型)
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
  integer :: f_advection_runge          ! 移流項をルンゲクッタで更新
  integer :: f_rivermouth_drop          ! 河口から海へ段落ち
  integer :: f_diffusion_term           ! 拡散項の計算 (0:無効, 1:定数, 2:ゼロ方程式)
  real :: p_diagratio                   ! ratio of diagonal component
  real :: p_adv_upwind_index            ! upwind index of advection term
  real :: p_adprunge_thresh             ! threshold of adaptive Runge-Kutta (1.1~)
  real :: p_diffusion_nu                ! 拡散項の動粘性係数 (m2/s)
  real :: p_diffusion_alpha             ! ゼロ方程式モデルの係数 α
  integer :: un
  integer :: ios
  character(len=1024) :: iom

  namelist /list_enc/ f_gravity_correction, f_exflux_reduction, f_hcap_upwind, &
                      f_friction_fastmath, f_advection_tvd, f_advection_runge, f_rivermouth_drop, &
                      f_adaptive_runge, p_diagratio, p_adv_upwind_index, p_adprunge_thresh, &
                      f_diffusion_term, p_diffusion_nu, p_diffusion_alpha

  f_gravity_correction = list%f_gravity_correction 
  f_exflux_reduction = list%f_exflux_reduction 
  f_hcap_upwind = list%f_hcap_upwind 
  f_adaptive_runge = list%f_adaptive_runge 
  f_friction_fastmath = list%f_friction_fastmath 
  f_advection_tvd = list%f_advection_tvd 
  f_advection_runge = list%f_advection_runge 
  f_rivermouth_drop = list%f_rivermouth_drop
  f_diffusion_term = list%f_diffusion_term
  p_diffusion_alpha = list%p_diffusion_alpha
  p_diagratio = list%p_diagratio
  p_adv_upwind_index = list%p_adv_upwind_index
  p_adv_upwind_index = list%p_adv_upwind_index
  p_adprunge_thresh = list%p_adprunge_thresh
  p_diffusion_nu = list%p_diffusion_nu

  ! ネームリストにありながらファイルに記述のなかった変数は、
  ! 事前に保存されていた値がそのまま保持される
  call par_info("reading list_enc in "//trim(p%fn_enc))
  open(newunit=un, file=trim(p%fn_enc), status='old')
  read(un, nml=list_enc, iostat=ios, iomsg=iom)
  if (ios /= 0) call par_stop("list_enc: failed to read namelist: "//trim(iom))
  close(un)

  list%f_gravity_correction = f_gravity_correction 
  list%f_exflux_reduction = f_exflux_reduction 
  list%f_hcap_upwind = f_hcap_upwind 
  list%f_adaptive_runge = f_adaptive_runge 
  list%f_friction_fastmath = f_friction_fastmath 
  list%f_advection_tvd = f_advection_tvd 
  list%f_advection_runge = f_advection_runge 
  list%f_rivermouth_drop = f_rivermouth_drop
  list%f_diffusion_term = f_diffusion_term
  list%p_diagratio = min(max(p_diagratio, 0.0), 1.0)                ! 値を0.0~1.0に制限
  list%p_adv_upwind_index = min(max(p_adv_upwind_index, 0.0), 1.0)  ! 値を0.0~1.0に制限
  list%p_adprunge_thresh = max(p_adprunge_thresh, 1.1)              ! 値を1.1以上に制限
  list%p_diffusion_nu = max(p_diffusion_nu, 0.0)                    ! 値を0.0以上に制限
  list%p_diffusion_alpha = max(p_diffusion_alpha, 0.0)              ! 値を0.0以上に制限

end subroutine


!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

end module
