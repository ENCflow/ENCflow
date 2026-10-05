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
    integer :: f_hcap_upwind = 1              ! セル境界水深 (0:両側平均, 1:上流側水深で
                                              !   頭打ち(既定), 2:上流側水深そのもの)
    integer :: f_adaptive_runge = 1           ! 適応的ルンゲクッタ
    integer :: f_friction_fastmath = 0        ! 摩擦項計算の高速化 (0:厳密,
                                              !   1~5:テーブル近似。大きいほど粗く速い)
    integer :: f_advection_scheme = 3         ! 移流項のスキーム (1: セル中心勾配(旧既定。非保存形),
                                              !   2: 運動量保存形・1次風上, 3: 運動量保存形+MUSCL(既定。
                                              !   2026-10-03 に 1 から昇格。developer.md §68.19))
    integer :: f_advection_donor = 0          ! 運動量保存形移流(スキーム 2, 3)の風上供給元の
                                              !   制限 (0:湿潤セルすべて(既定), 1:河道セル間の
                                              !   エッジでは流下方向の供給元を河道セル(rw>0)に
                                              !   限る。fn_rw 必須)。
                                              !   屈曲で線上の供給元が浸水した非河道セルに落ちる
                                              !   人工損失の対策(developer.md §68.18)
    integer :: f_dry_head_cap = 1             ! 乾燥セルへ向かうエッジ水深のエネルギー頭による
                                              !   頭打ち (0:なし, 1:有効(既定))。受け手が乾燥の
                                              !   とき he ≤ max(η + u_n²/2g − z_受け手, 0) とし、
                                              !   水面+速度水頭より高い地盤へは流さない
                                              !   (developer.md §68.16)
    integer :: f_opening_dynamic = 1          ! 塞がれた開口の動的振り替え (0:なし,
                                              !   1:河道セル間のエッジのみ(既定。河道マスク
                                              !   fn_rw がなければ対象エッジがなく無効),
                                              !   2:全エッジ)。水面より高い隣接地盤で塞がれた
                                              !   斜め/軸の通過幅シェアを開いたエッジへ毎
                                              !   ステップ振り替える(developer.md §68.14)
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
    ! --- 非静水圧(1 層 NH)補正(研究用。docs/nonhydrostatic_plan.md、developer.md §69) ---
    integer :: f_nonhydrostatic = 0           ! 0: 静水圧(既定), 1: 1 層 NH 補正(β = h²/4)
    real :: nh_hmin = 0.1                     ! この水深未満のセルは静水圧に退化 (m)
    integer :: nh_solver = 2                  ! 反復ソルバ (1: Jacobi, 2: CG(既定))
    integer :: nh_itmax = 500                 ! 反復回数の上限
    real :: nh_tol = 1.0e-6                   ! 相対収束判定(Jacobi: 残差最大/右辺最大、CG: ||r||/||b||)
    integer :: f_nh_adaptive = 0              ! 活性集合 (0: NH マスク内全域で解く, 1: 検出セル+縁だけ)
    integer :: nh_detector = 1                ! 検出量 (1: 分散型 χ = |βDa*|/(|a*|+|βDa*|), 2: 絶対型 |βDa*|/g)
    real :: nh_chi_on = 0.06                  ! 検出の閾値(χ > nh_chi_on のセルが種)
    integer :: nh_margin = 0                  ! 種のまわりの縁の幅(セル数。0: 2H/Δx から自動)
    real :: nh_amin = 1.0e-5                  ! 検出の下限 |βDa*| (m/s²)。未満は種にしない(丸め誤差の前駆波を除く)
    real :: nh_arel = 1.0e-3                  ! 検出の相対下限: |βDa*| がそのステップの領域最大の nh_arel 倍未満なら種にしない
    integer :: f_nh_breaking = 0              ! 砕波スイッチ (0: なし, 1: 水面上昇速度 ∂η/∂t > α√(gh) のセルを静水圧に)
    real :: nh_break_alpha = 0.6              ! 砕波開始の閾値 α(SWASH の既定 0.6)
    real :: nh_break_beta = 0.3               ! 砕波セルに接するセルの閾値 β(前線の伝播。SWASH の既定 0.3)
    integer :: nh_break_type = 3              ! 砕波の判定量 (1: 水面上昇速度 ∂η/∂t/√(gh) > α, 2: フルード数 |V|/√(gh) > nh_break_fr,
                                              !   3: 水面勾配 |∇η| > nh_break_slope(既定))
    real :: nh_break_fr = 0.6                 ! フルード数判定の閾値
    real :: nh_break_slope = 0.3              ! 水面勾配判定の閾値(8 近傍の最大 |Δη|/距離)
    integer :: nh_break_margin = 0            ! 砕波セルの周りを静水圧にする縁の幅(セル数。0: 2H/Δx から自動)
    integer :: nh_bc_margin = 0               ! 強制境界(水位規定セル・区間流入/自由流出/放射の面)から静水圧のままにする
                                              !   セル数(0: 2H/Δx から自動)。規定流束と射影の干渉を避ける
    real :: nh_break_visc = 0.0               ! 砕波域の渦粘性係数 δ_b²(0: なし。1.44 = Kennedy et al. 2000 相当。
                                              !   ν_b = nh_break_visc·B·h·√(gh)·|∇η| を運動量の拡散項に加える。plan §15)
    integer :: f_nh_slope = 0                 ! 底面勾配項 (0: 平坦床の線形 NH(Version 1), 1: 底面の運動学条件 w_b = u·∇z_b と
                                              !   圧力項 (φ/h)∇(h+2z_b) を含む(Version 2))
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
  integer :: f_advection_scheme         ! 移流項のスキーム
  integer :: f_opening_dynamic          ! 塞がれた開口の動的振り替え (0:なし, 1:河道, 2:全域)
  integer :: f_dry_head_cap             ! 乾燥セルへのエッジ水深のエネルギー頭による頭打ち (0/1)
  integer :: f_advection_donor          ! 運動量保存形移流の供給元制限 (0:全湿潤セル, 1:河道セル)
  integer :: f_rivermouth_drop          ! 河口から海へ段落ち
  integer :: f_diffusion_term           ! 拡散項の計算 (0:無効, 1:定数, 2:ゼロ方程式)
  real :: p_diagratio                   ! ratio of diagonal component
  real :: p_adv_upwind_index            ! upwind index of advection term
  real :: p_adprunge_thresh             ! threshold of adaptive Runge-Kutta (1.1~)
  real :: p_diffusion_nu                ! 拡散項の動粘性係数 (m2/s)
  real :: p_diffusion_alpha             ! ゼロ方程式モデルの係数 α
  integer :: f_nonhydrostatic           ! 非静水圧補正 (0:静水圧, 1:1 層 NH)
  real :: nh_hmin                       ! NH を適用する最小水深 (m)
  integer :: nh_solver                  ! NH の反復ソルバ (1:Jacobi, 2:CG)
  integer :: nh_itmax                   ! NH の反復回数上限
  real :: nh_tol                        ! NH の相対収束判定
  integer :: f_nh_adaptive              ! NH の活性集合 (0:全域, 1:検出セル+縁)
  integer :: nh_detector                ! NH の検出量 (1:分散型 χ, 2:絶対型)
  real :: nh_chi_on                     ! NH の検出閾値
  integer :: nh_margin                  ! NH の縁の幅(セル数。0:自動)
  real :: nh_amin                       ! NH の検出下限 (m/s²)
  real :: nh_arel                       ! NH の検出の相対下限
  integer :: f_nh_breaking              ! NH の砕波スイッチ (0/1)
  real :: nh_break_alpha                ! 砕波開始の閾値
  real :: nh_break_beta                 ! 砕波前線の伝播の閾値
  integer :: nh_break_type              ! 砕波の判定量 (1:∂η/∂t, 2:フルード数)
  real :: nh_break_fr                   ! フルード数判定の閾値
  real :: nh_break_slope                ! 水面勾配判定の閾値
  integer :: nh_break_margin            ! 砕波セルの縁の幅(セル数)
  real :: nh_break_visc                 ! 砕波域の渦粘性係数 δ_b²
  integer :: nh_bc_margin               ! 強制境界から静水圧のままにするセル数
  integer :: f_nh_slope                 ! NH の底面勾配項 (0/1)
  integer :: un
  integer :: ios
  character(len=1024) :: iom

  namelist /list_enc/ f_gravity_correction, f_exflux_reduction, f_hcap_upwind, &
                      f_friction_fastmath, f_advection_scheme, &
                      f_rivermouth_drop, f_opening_dynamic, f_dry_head_cap, f_advection_donor, &
                      f_adaptive_runge, p_diagratio, p_adv_upwind_index, p_adprunge_thresh, &
                      f_diffusion_term, p_diffusion_nu, p_diffusion_alpha, &
                      f_nonhydrostatic, nh_hmin, nh_solver, nh_itmax, nh_tol, &
                      f_nh_adaptive, nh_detector, nh_chi_on, nh_margin, nh_amin, nh_arel, &
                      f_nh_breaking, nh_break_alpha, nh_break_beta, nh_break_type, nh_break_fr, &
                      nh_break_slope, nh_break_margin, nh_break_visc, nh_bc_margin, f_nh_slope

  f_gravity_correction = list%f_gravity_correction 
  f_exflux_reduction = list%f_exflux_reduction 
  f_hcap_upwind = list%f_hcap_upwind 
  f_adaptive_runge = list%f_adaptive_runge 
  f_friction_fastmath = list%f_friction_fastmath 
  f_advection_scheme = list%f_advection_scheme
  f_rivermouth_drop = list%f_rivermouth_drop
  f_opening_dynamic = list%f_opening_dynamic
  f_dry_head_cap = list%f_dry_head_cap
  f_advection_donor = list%f_advection_donor
  f_diffusion_term = list%f_diffusion_term
  p_diffusion_alpha = list%p_diffusion_alpha
  p_diagratio = list%p_diagratio
  p_adv_upwind_index = list%p_adv_upwind_index
  p_adv_upwind_index = list%p_adv_upwind_index
  p_adprunge_thresh = list%p_adprunge_thresh
  p_diffusion_nu = list%p_diffusion_nu
  f_nonhydrostatic = list%f_nonhydrostatic
  nh_hmin = list%nh_hmin
  nh_solver = list%nh_solver
  nh_itmax = list%nh_itmax
  nh_tol = list%nh_tol
  f_nh_adaptive = list%f_nh_adaptive
  nh_detector = list%nh_detector
  nh_chi_on = list%nh_chi_on
  nh_margin = list%nh_margin
  nh_amin = list%nh_amin
  nh_arel = list%nh_arel
  f_nh_breaking = list%f_nh_breaking
  nh_break_alpha = list%nh_break_alpha
  nh_break_beta = list%nh_break_beta
  nh_break_type = list%nh_break_type
  nh_break_fr = list%nh_break_fr
  nh_break_slope = list%nh_break_slope
  nh_break_margin = list%nh_break_margin
  nh_break_visc = list%nh_break_visc
  nh_bc_margin = list%nh_bc_margin
  f_nh_slope = list%f_nh_slope

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
  list%f_advection_scheme = f_advection_scheme
  list%f_rivermouth_drop = f_rivermouth_drop
  list%f_opening_dynamic = f_opening_dynamic
  list%f_dry_head_cap = f_dry_head_cap
  list%f_advection_donor = f_advection_donor
  list%f_diffusion_term = f_diffusion_term
  list%p_diagratio = min(max(p_diagratio, 0.0), 1.0)                ! 値を0.0~1.0に制限
  list%p_adv_upwind_index = min(max(p_adv_upwind_index, 0.0), 1.0)  ! 値を0.0~1.0に制限
  list%p_adprunge_thresh = max(p_adprunge_thresh, 1.1)              ! 値を1.1以上に制限
  list%p_diffusion_nu = max(p_diffusion_nu, 0.0)                    ! 値を0.0以上に制限
  list%p_diffusion_alpha = max(p_diffusion_alpha, 0.0)              ! 値を0.0以上に制限
  list%f_nonhydrostatic = f_nonhydrostatic
  list%nh_hmin = nh_hmin
  list%nh_solver = nh_solver
  list%nh_itmax = nh_itmax
  list%nh_tol = nh_tol
  list%f_nh_adaptive = f_nh_adaptive
  list%nh_detector = nh_detector
  list%nh_chi_on = nh_chi_on
  list%nh_margin = nh_margin
  list%nh_amin = nh_amin
  list%nh_arel = nh_arel
  list%f_nh_breaking = f_nh_breaking
  list%nh_break_alpha = nh_break_alpha
  list%nh_break_beta = nh_break_beta
  list%nh_break_type = nh_break_type
  list%nh_break_fr = nh_break_fr
  list%nh_break_slope = nh_break_slope
  list%nh_break_margin = nh_break_margin
  list%nh_break_visc = nh_break_visc
  list%nh_bc_margin = nh_bc_margin
  list%f_nh_slope = f_nh_slope

end subroutine


!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================

end module
