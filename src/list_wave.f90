!======================================================================
! list_wave: 波浪条件(沖波の与件と沿岸漂砂の設定)の namelist を読む
!   &list_wave。fn_wave で指定(未指定なら波浪の効果は完全に不活性)。
!   解釈・検証・導出は m_geomorph の init_wave が行う(list_* 層の共通契約。
!   developer.md §12)。設計は docs/wave_plan.md、決定は developer.md §84.15
!======================================================================
module list_wave
  use m_sysparam, only : t_sysparam
  use m_parallel, only : par_info, par_stop
  implicit none
  private

  public :: t_list_wave
  public :: list_wave_read
  public :: nwvmax

  integer, parameter :: nwvmax = 999   ! 波の時系列の最大データ数

  type t_list_wave
    integer :: f_wave_longshore = 1    ! 汀線帯の沿岸漂砂(0:無効, 1:有効)。wave_plan.md 案 A
    real :: wave_h0 = 0.0              ! 沖の有義波高 H0 (m)(固定値。時系列があればそちらが優先)
    real :: wave_t = 0.0               ! 周期 T (s)(固定値)
    real :: wave_dir = 0.0             ! 波の進行方向 (deg。x 軸(東)から反時計回り。北 = 90°)
    real :: wave_val(1:4,1:nwvmax) = -9999   ! 時系列 (時刻, H0 (m), T (s), 方向 (deg))。
                                       !   時刻の単位は wave_clock による(分)。線形補間、範囲外は端値
    integer :: wave_clock = 1          ! 時系列の時計(1: 地形時間 = 水理時間 × morfac(既定。波候),
                                       !   0: 水理時間(嵐の継続時間を水理時間で与える))
    real :: wave_k2 = 0.34             ! 沖波で書いた CERC 式の係数 K2 (m^{3/5} s^{-6/5})。
                                       !   Ashton & Murray (2006) 式 (2)(K = 0.39、γ = 0.78 の換算値)
    real :: wave_gamma = 0.78          ! 砕波指標 γ = H_b / h_b
    integer :: wave_smooth = 2         ! 汀線方位を取る水深の平滑化半径(セル。1 または 2。ハロ幅の内側)
    real :: wave_smin = 1.0e-3         ! 汀線方位を定義する海底勾配の下限(これ未満は平坦 = 対象外)
    real :: wave_lsm = 0.0             ! 汀線方位を取る水深の平滑化長 σ (m)。> 0 なら wave_smooth(セル)の代わりに
                                       !   多パスの 5 点核(§84.16 と同じ。N = 4(σ/Δmin)² パス)で平滑化する。
                                       !   砕波帯の幅 W_b 程度にすると不安定の打ち切り波長が格子に依らない(§84.15 段 3 (a))
    real :: wave_bslp = 2.0            ! 多パス核(wave_lsm > 0)のときの局所勾配項の係数 β: 流束に
                                       !   β q ∇(h − h_s)(平滑化からの水深の偏差の勾配 = 局所の穴へ砂を
                                       !   押す)を加える。σ より小さい凹凸を均す(0 で無効)
    real :: wave_vmax = -1.0           ! 河口の規則: 流速 |V| がこれを超えるセルは波の源にも砕波帯にも
                                       !   しない (m/s)。負 = 無効(既定)。河川の流下流速と汀線帯の流速の
                                       !   間に置く(可動河床の河口で必須。§84.15)
  end type

contains

!----------------------------------------------------------------------
subroutine list_wave_read(p, list)
  type(t_sysparam), intent(in) :: p
  type(t_list_wave), intent(inout) :: list
  integer :: f_wave_longshore, wave_clock, wave_smooth
  real :: wave_h0, wave_t, wave_dir, wave_k2, wave_gamma, wave_smin, wave_vmax, wave_lsm, wave_bslp
  real :: wave_val(1:4,1:nwvmax)
  integer :: un, ios
  character(len=1024) :: iom
  namelist /list_wave/ f_wave_longshore, wave_h0, wave_t, wave_dir, wave_val, wave_clock, &
                       wave_k2, wave_gamma, wave_smooth, wave_smin, wave_vmax, wave_lsm, wave_bslp

  f_wave_longshore = list%f_wave_longshore
  wave_h0 = list%wave_h0
  wave_t = list%wave_t
  wave_dir = list%wave_dir
  wave_val = list%wave_val
  wave_clock = list%wave_clock
  wave_k2 = list%wave_k2
  wave_gamma = list%wave_gamma
  wave_smooth = list%wave_smooth
  wave_smin = list%wave_smin
  wave_vmax = list%wave_vmax
  wave_lsm = list%wave_lsm
  wave_bslp = list%wave_bslp

  call par_info("reading list_wave in "//trim(p%fn_wave))
  open(newunit=un, file=trim(p%fn_wave), status='old', iostat=ios, iomsg=iom)
  if (ios /= 0) call par_stop("list_wave: cannot open "//trim(p%fn_wave)//": "//trim(iom))
  read(un, nml=list_wave, iostat=ios, iomsg=iom)
  if (ios /= 0) call par_stop("list_wave: failed to read namelist: "//trim(iom))
  close(un)

  list%f_wave_longshore = f_wave_longshore
  list%wave_h0 = wave_h0
  list%wave_t = wave_t
  list%wave_dir = wave_dir
  list%wave_val = wave_val
  list%wave_clock = wave_clock
  list%wave_k2 = wave_k2
  list%wave_gamma = wave_gamma
  list%wave_smooth = wave_smooth
  list%wave_smin = wave_smin
  list%wave_vmax = wave_vmax
  list%wave_lsm = wave_lsm
  list%wave_bslp = wave_bslp
end subroutine

end module
