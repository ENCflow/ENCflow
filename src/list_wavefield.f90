module list_wavefield
  ! 沿岸の波浪場モデルの設定ファイル(fn_wavefield の namelist)の読み込み専任
  ! (層契約 §12)。生の値を t_list_wavefield に運ぶだけで、解釈・検証・既定値の
  ! 適用・導出は m_wavefield の init が行う(developer.md §88、docs/wavefield_plan.md)。
  !   &list_wavefield : 有効化・方向ビン・解法(非定常/準定常)・境界の型・沖の波
  !                     (固定値または時系列)・砕波と摩擦の係数・出力・流れへの作用
  !                     (段 W2: 外力・GLM・波・流れの摩擦・ローラー)
  ! 未指定の番兵は実数 −9999、整数 −9999。グループ不在は全番兵のまま(init が判定)。
  use m_sysparam, only : t_sysparam
  use m_parallel, only : par_info, par_stop
  implicit none
  private
  public :: t_list_wavefield
  public :: list_wavefield_read
  public :: wf_nvalmax

  integer, parameter :: wf_nvalmax = 2000    ! 沖の波の時系列の最大行数

  type t_list_wavefield
    integer :: f_wavefield = 1                   ! 0 で書いたまま一時無効化
    integer :: wf_ntheta = -9999                 ! 方向ビン数(8 の倍数)
    integer :: wf_mode = -9999                   ! 1: 非定常(物理時間) / 2: 準定常(dt_wave ごと)
    real :: dt_wave = -9999.0                    ! 準定常の更新間隔 (s)
    integer :: wf_itmax = -9999                  ! 準定常の反復の上限
    real :: wf_tol = -9999.0                     ! 準定常の収束判定(波高の相対変化)
    integer :: f_wf_init = -9999                 ! 1: 開始時に準定常解 / 0: 静穏から
    integer :: wf_bc_side(1:4) = -9999           ! 辺(W, E, N, S)の型 0: 吸収 / 1: 入射 / 2: 側方 Neumann
    integer :: wf_wavetype = -9999               ! 1: 不規則波(H_m0) / 2: 規則波(H。飽和砕波。検定用)
    real :: wf_hm0 = -9999.0                     ! 沖の波高 (m。不規則波は H_m0、規則波は H)
    real :: wf_trep = -9999.0                    ! 代表周期 (s。既定の解釈は T_m-1,0。§88.1 D7)
    real :: wf_dir = -9999.0                     ! 進行方向 (deg。x 軸から反時計回り、北 = 90)
    real :: wf_spread = -9999.0                  ! 方向分散 σθ (deg。Kuik ら 1988 の定義)
    real :: wf_val(1:5, 1:wf_nvalmax) = -9999.0  ! 時系列: 時刻 (min)・波高・周期・方向・方向分散
    integer :: wf_clock = -9999                  ! 時系列の時計 0: 水理時間 / 1: 地形時間
    integer :: wf_break = -9999                  ! 砕波 1: Baldock ら 1998 / 2: Janssen & Battjes 2007
    real :: wf_gamma = -9999.0                   ! 砕波指標 γ
    real :: wf_alpha = -9999.0                   ! 砕波の散逸係数 α
    real :: wf_gammax = -9999.0                  ! 水深による上限 H_rms <= γmax h(不規則波)
    real :: wf_fw = -9999.0                      ! 底面摩擦係数 f_w
    real :: wf_hmin = -9999.0                    ! 波浪セルの最小水深 (m)
    integer :: f_wf_outdiag = -9999              ! 1: 診断量(砕波散逸・軌道流速)も分布出力
    integer :: wf_flow = -9999                   ! 流れへの作用 0: なし / 1: 外力 / 2: 外力+GLM+摩擦
    integer :: f_wf_roller = -9999               ! 1: ローラーのエネルギー平衡(wf_flow >= 1)
    real :: wf_beta = -9999.0                    ! ローラーの散逸係数 β
    real :: wf_tramp = -9999.0                   ! 外力の立ち上げ時間 (s)
    integer :: f_wf_current = -9999              ! 1: 流れの波への作用(ドップラー・屈折・輸送・阻止。段 W3)
  end type

contains


!----------------------------------------------------------------------
! 設定ファイルを読み込む(グループ不在可。構文エラーは停止)
!----------------------------------------------------------------------
subroutine list_wavefield_read(p, list)
  type(t_sysparam), intent(in) :: p
  type(t_list_wavefield), intent(out) :: list
  integer :: un, ios
  character(len=256) :: msg

  integer :: f_wavefield, wf_ntheta, wf_mode, wf_itmax, f_wf_init, wf_wavetype, wf_clock, wf_break
  integer :: f_wf_outdiag, wf_flow, f_wf_roller, f_wf_current
  integer :: wf_bc_side(1:4)
  real :: dt_wave, wf_tol, wf_hm0, wf_trep, wf_dir, wf_spread
  real :: wf_gamma, wf_alpha, wf_gammax, wf_fw, wf_hmin, wf_beta, wf_tramp
  real :: wf_val(1:5, 1:wf_nvalmax)

  namelist /list_wavefield/ f_wavefield, wf_ntheta, wf_mode, dt_wave, wf_itmax, wf_tol, f_wf_init, &
                            wf_bc_side, wf_wavetype, wf_hm0, wf_trep, wf_dir, wf_spread, wf_val, &
                            wf_clock, wf_break, wf_gamma, wf_alpha, wf_gammax, wf_fw, wf_hmin, &
                            f_wf_outdiag, wf_flow, f_wf_roller, wf_beta, wf_tramp, f_wf_current

  f_wavefield = list%f_wavefield
  wf_ntheta = list%wf_ntheta
  wf_mode = list%wf_mode
  dt_wave = list%dt_wave
  wf_itmax = list%wf_itmax
  wf_tol = list%wf_tol
  f_wf_init = list%f_wf_init
  wf_bc_side = list%wf_bc_side
  wf_wavetype = list%wf_wavetype
  wf_hm0 = list%wf_hm0
  wf_trep = list%wf_trep
  wf_dir = list%wf_dir
  wf_spread = list%wf_spread
  wf_val = list%wf_val
  wf_clock = list%wf_clock
  wf_break = list%wf_break
  wf_gamma = list%wf_gamma
  wf_alpha = list%wf_alpha
  wf_gammax = list%wf_gammax
  wf_fw = list%wf_fw
  wf_hmin = list%wf_hmin
  f_wf_outdiag = list%f_wf_outdiag
  wf_flow = list%wf_flow
  f_wf_roller = list%f_wf_roller
  wf_beta = list%wf_beta
  wf_tramp = list%wf_tramp
  f_wf_current = list%f_wf_current

  call par_info("reading list_wavefield in " // trim(p%fn_wavefield))
  open(newunit=un, file=trim(p%fn_wavefield), status='old', action='read', iostat=ios)
  if (ios /= 0) call par_stop("list_wavefield: cannot open " // trim(p%fn_wavefield))
  read(un, nml=list_wavefield, iostat=ios, iomsg=msg)
  if (ios > 0) call par_stop("list_wavefield: cannot read namelist: " // trim(msg))
  close(un)

  list%f_wavefield = f_wavefield
  list%wf_ntheta = wf_ntheta
  list%wf_mode = wf_mode
  list%dt_wave = dt_wave
  list%wf_itmax = wf_itmax
  list%wf_tol = wf_tol
  list%f_wf_init = f_wf_init
  list%wf_bc_side = wf_bc_side
  list%wf_wavetype = wf_wavetype
  list%wf_hm0 = wf_hm0
  list%wf_trep = wf_trep
  list%wf_dir = wf_dir
  list%wf_spread = wf_spread
  list%wf_val = wf_val
  list%wf_clock = wf_clock
  list%wf_break = wf_break
  list%wf_gamma = wf_gamma
  list%wf_alpha = wf_alpha
  list%wf_gammax = wf_gammax
  list%wf_fw = wf_fw
  list%wf_hmin = wf_hmin
  list%f_wf_outdiag = f_wf_outdiag
  list%wf_flow = wf_flow
  list%f_wf_roller = f_wf_roller
  list%wf_beta = wf_beta
  list%wf_tramp = wf_tramp
  list%f_wf_current = f_wf_current
end subroutine

end module
