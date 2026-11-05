module list_lavaflow
  ! ============== 溶岩流設定ファイルの読み込み(&list_lavaflow) ==============
  ! list_* は namelist を読むだけ。解釈・検証・導出(単位換算、噴火口の
  ! 組み立て、相互依存の検査)は m_lavaflow の init が行う(developer.md §12)
  ! ==========================================================================
  use m_sysparam, only : t_sysparam
  use m_parallel, only : par_info, par_stop
  implicit none
  private
  public :: t_list_lavaflow
  public :: list_lavaflow_read
  public :: lvmax, lvcmax, lvvmax
  public :: lv_cell, lv_val

  integer, parameter :: maxpathlen = 256
  integer, parameter :: lvmax = 20     ! 噴火口の最大数
  integer, parameter :: lvcmax = 99    ! 1噴火口あたりの最大セル数(インライン。
                                       !   それ以上は fn_lv_cell のファイルで)
  integer, parameter :: lvvmax = 999   ! 噴出率時系列の最大データ数(インライン)

  ! namelist 読み込み用の静的作業配列(スタックに置かないための措置。
  ! m_gwflow_pump と同じ実バグ対策。init のみ使用。m_lavaflow_init が読む)
  integer :: lv_cell(1:2,1:lvcmax,1:lvmax)
  real :: lv_val(1:2,1:lvvmax,1:lvmax)

  type t_list_lavaflow
    integer :: f_lavaflow = 1                ! 0 でファイルを残したまま一時無効化
    character(len=80) :: dt_lavaflow_c = ""  ! 溶岩更新間隔(時間文字列。空 = 毎ステップ)
    real :: lv_rho = 2600.0                  ! 溶岩の密度 ρ (kg/m3)
    real :: lv_visc = -9999.0                ! 粘度 η (Pa s。未指定なら既定 1e4。§66)
    real :: lv_tauy = 0.0                    ! 降伏応力 τ_y (Pa。0 = Newton 流体)
    real :: lv_wsol = 0.0                    ! 停止セルの固化レート (m/s。0 = 固化なし)
    real :: lv_vsol = -9999.0                ! 停止判定の速度閾値 (m/s。lv_wsol>0 で未指定なら既定 5e-4)
    real :: lv_cfl = 0.4                     ! 陽解法サブサイクルの安全係数 (0-1)
    integer :: lv_nsubmax = 10000            ! 1回の更新のサブサイクル数上限(暴走ガード)
    real :: lv_q0(1:lvmax) = -9999.0         ! 一定噴出率 (m3/s。時系列の代わり)
    character(len=maxpathlen) :: fn_lv_cell(1:lvmax) = ""  ! セル集合ファイル(i j の行列挙)
    character(len=maxpathlen) :: fn_lv_val(1:lvmax) = ""   ! 噴出率時系列ファイル(分, m3/s)
    ! --- 温度(段階2。lava_plan.md §8・developer.md §51.7)。f_lvtemp=1 のときだけ読む。
    !     既定は置かない(溶岩の種類で桁が変わる値と、原典を確かめていない値。番兵 -9999) ---
    integer :: f_lvtemp = 0                  ! 1: 溶岩の深さ平均温度を計算する(0 = 等温)
    integer :: f_lvtemp_scheme = 3           ! 熱の移流の面の温度 (3: MUSCL + van Leer = 既定(2026-11-05 から),
                                             !   1: 1次風上 = 送り手の温度。developer.md §94)
    real :: lv_temp0(1:lvmax) = -9999.0      ! 噴火口ごとの噴出温度 (°C)
    real :: lv_tref = -9999.0                ! レオロジーの基準温度 T_r (°C。lv_visc・lv_tauy はこの温度の値)
    real :: lv_bvisc = -9999.0               ! 粘度の温度感度 β_η (1/K)
    real :: lv_btau = -9999.0                ! 降伏応力の温度感度 β_τ (1/K)
    real :: lv_tsol = -9999.0                ! 固化温度 T_sol (°C)
    real :: lv_emis = -9999.0                ! 有効放射率 ε (0-1。表面の殻の断熱を含めた有効値)
    real :: lv_hconv = -9999.0               ! 対流の熱伝達係数 h_c (W/m2/K)
    real :: lv_cp = -9999.0                  ! 溶岩の比熱 c_p (J/kg/K。結晶化の潜熱を含めた有効値でよい)
    real :: lv_tair = -9999.0                ! 気温 (°C。fn_meteo がないときに必須)
  end type

contains

!----------------------------------------------------------------------
! 溶岩流設定ファイルを読み込む
!----------------------------------------------------------------------
subroutine list_lavaflow_read(p, list)
  type(t_sysparam), intent(in) :: p
  type(t_list_lavaflow), intent(inout) :: list

  integer :: f_lavaflow, lv_nsubmax, f_lvtemp, f_lvtemp_scheme
  real :: lv_rho, lv_visc, lv_tauy, lv_wsol, lv_vsol, lv_cfl
  real :: lv_q0(1:lvmax), lv_temp0(1:lvmax)
  real :: lv_tref, lv_bvisc, lv_btau, lv_tsol, lv_emis, lv_hconv, lv_cp, lv_tair
  character(len=80) :: dt_lavaflow_c
  character(len=maxpathlen) :: fn_lv_cell(1:lvmax), fn_lv_val(1:lvmax)
  integer :: un, ios
  character(len=1024) :: iom

  namelist /list_lavaflow/ f_lavaflow, dt_lavaflow_c, lv_rho, lv_visc, &
                           lv_tauy, lv_wsol, lv_vsol, lv_cfl, lv_nsubmax, &
                           lv_cell, lv_q0, lv_val, fn_lv_cell, fn_lv_val, &
                           f_lvtemp, f_lvtemp_scheme, lv_temp0, lv_tref, &
                           lv_bvisc, lv_btau, lv_tsol, lv_emis, lv_hconv, lv_cp, &
                           lv_tair

  ! ネームリストにありながらファイルに記述のなかった変数は、
  ! 事前に保存されていた値がそのまま保持される
  f_lavaflow = list%f_lavaflow
  dt_lavaflow_c = list%dt_lavaflow_c
  lv_rho = list%lv_rho
  lv_visc = list%lv_visc
  lv_tauy = list%lv_tauy
  lv_wsol = list%lv_wsol
  lv_vsol = list%lv_vsol
  lv_cfl = list%lv_cfl
  lv_nsubmax = list%lv_nsubmax
  lv_q0 = list%lv_q0
  fn_lv_cell = list%fn_lv_cell
  fn_lv_val = list%fn_lv_val
  f_lvtemp = list%f_lvtemp
  f_lvtemp_scheme = list%f_lvtemp_scheme
  lv_temp0 = list%lv_temp0
  lv_tref = list%lv_tref
  lv_bvisc = list%lv_bvisc
  lv_btau = list%lv_btau
  lv_tsol = list%lv_tsol
  lv_emis = list%lv_emis
  lv_hconv = list%lv_hconv
  lv_cp = list%lv_cp
  lv_tair = list%lv_tair
  lv_cell = -9999
  lv_val = -9999.0

  call par_info("reading list_lavaflow in "//trim(p%fn_lavaflow))
  open(newunit=un, file=trim(p%fn_lavaflow), status='old', iostat=ios, iomsg=iom)
  if (ios /= 0) call par_stop("list_lavaflow: cannot open "//trim(p%fn_lavaflow)//": "//trim(iom))
  read(un, nml=list_lavaflow, iostat=ios, iomsg=iom)
  if (ios /= 0) call par_stop("list_lavaflow: cannot read namelist: "//trim(iom))
  close(un)

  list%f_lavaflow = f_lavaflow
  list%dt_lavaflow_c = dt_lavaflow_c
  list%lv_rho = lv_rho
  list%lv_visc = lv_visc
  list%lv_tauy = lv_tauy
  list%lv_wsol = lv_wsol
  list%lv_vsol = lv_vsol
  list%lv_cfl = lv_cfl
  list%lv_nsubmax = lv_nsubmax
  list%lv_q0 = lv_q0
  list%fn_lv_cell = fn_lv_cell
  list%fn_lv_val = fn_lv_val
  list%f_lvtemp = f_lvtemp
  list%f_lvtemp_scheme = f_lvtemp_scheme
  list%lv_temp0 = lv_temp0
  list%lv_tref = lv_tref
  list%lv_bvisc = lv_bvisc
  list%lv_btau = lv_btau
  list%lv_tsol = lv_tsol
  list%lv_emis = lv_emis
  list%lv_hconv = lv_hconv
  list%lv_cp = lv_cp
  list%lv_tair = lv_tair

end subroutine

end module
