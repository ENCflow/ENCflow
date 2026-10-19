!======================================================================
! m_sedform: 浮遊砂の平衡濃度式と沈降速度式(葉モジュール。依存なし)
!   m_geomorph_suspend(E-D)と m_boundary(区間流入の平衡濃度給砂 inflow_cs_eq。
!   §84.9)が同じ式を使うために切り出した。係数の組 ceqpar は geomorph の
!   init_suspend が sedform_set_ceq で登録する(単一インスタンス前提の
!   モジュール変数。m_boundary → m_geomorph の依存を作ると
!   m_geomorph → m_swflow_enc → m_boundary と循環するため、両者が参照する
!   葉モジュールに置く)。
!   板倉・岸の浮上量式の定数は原式の値(実践河川水理学(iRIC)第4章 式(3)-(5)。
!   原典: 板倉忠興, 土木試験所報告 第83号, 1984)で namelist にしない。
!======================================================================
module m_sedform
  implicit none
  private
  public :: t_ceqpar, ceqpar, have_ceq, sedform_set_ceq, sed_ceq, sed_ceq_itakura, sed_rubey_wf

  type t_ceqpar
    integer :: form = 1              ! 平衡濃度式(1: 超過掃流力線形, 2: 板倉・岸)
    real :: esa = 0.0                ! 線形式の係数
    real :: stausc = 0.05            ! 浮遊の限界無次元掃流力
    real :: sgrav = 1.65             ! 土粒子の水中比重
    real :: d50 = 0.0                ! 浮遊砂の代表粒径 (m)
    real :: wf = 0.0                 ! 沈降速度 (m/s)
    real :: gg = 9.8                 ! 重力加速度
  end type

  type(t_ceqpar), protected :: ceqpar
  logical, protected :: have_ceq = .false.   ! geomorph の浮遊砂が係数を登録したか

  real, parameter :: ik_k = 0.008        ! K
  real, parameter :: ik_alpha = 0.14     ! α*
  real, parameter :: ik_bstar = 0.143    ! B*
  real, parameter :: ik_eta0 = 0.5       ! η0

contains

subroutine sedform_set_ceq(par)
  type(t_ceqpar), intent(in) :: par
  ceqpar = par
  have_ceq = .true.
end subroutine


! 平衡濃度(浸食レート E = wf・ceq に相当する濃度換算)
pure function sed_ceq(par, taus) result(ceq)
  type(t_ceqpar), intent(in) :: par
  real, intent(in) :: taus
  real :: ceq
  ceq = 0.0
  if (par%form == 1) then
    if (taus > par%stausc) ceq = par%esa * (taus / par%stausc - 1.0)
  else
    ceq = sed_ceq_itakura(par%sgrav, par%gg, par%d50, par%wf, taus)
  end if
end function


! 板倉・岸(ceq = q_su / wf)
pure function sed_ceq_itakura(sgrav, gg, d50, wf, taus) result(ceq)
  real, intent(in) :: sgrav, gg, d50, wf
  real, intent(in) :: taus    ! 無次元掃流力 τ*
  real :: ceq
  real :: ap, ratio, omega, ustar, qsu
  real, parameter :: pi = acos(-1.0)

  ceq = 0.0
  if (taus <= 0.0) return
  ap = ik_bstar / taus - 1.0 / ik_eta0
  if (ap > 20.0) return
  ratio = exp(-ap**2) / (sqrt(pi) * erfc(ap))
  omega = taus / ik_bstar * ratio + taus / (ik_bstar * ik_eta0) - 1.0
  ustar = sqrt(taus * sgrav * gg * d50)
  qsu = ik_k * (ik_alpha / (sgrav + 1.0) &
                * (sgrav * gg * d50 / ustar) * omega - wf)
  ceq = max(qsu, 0.0) / wf
end function


! Rubey 式の沈降速度
pure function sed_rubey_wf(sgrav, gg, d) result(wf)
  real, intent(in) :: sgrav, gg, d
  real :: wf
  real :: bb
  real, parameter :: nu = 1.0e-6
  bb = 36.0 * nu**2 / (sgrav * gg * d**3)
  wf = (sqrt(2.0 / 3.0 + bb) - sqrt(bb)) * sqrt(sgrav * gg * d)
end function

end module
