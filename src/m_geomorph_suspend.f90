!======================================================================
! m_geomorph の submodule: 浮遊砂の E-D 交換(f_suspend)
!   移流本体は m_swflow_enc のステップ内輸送(advect_scalar)が担い、
!   ここは浸食・沈降(E-D)と平衡濃度式のみ。平衡濃度式・沈降速度の
!   補助関数は submodule レベルの私有手続き(contained は使わない。§13)
!======================================================================
submodule(m_geomorph) m_geomorph_suspend
  use m_parallel, only : par_info, par_stop, dcp
  implicit none

contains

!----------------------------------------------------------------------
module subroutine init_suspend(gm, p, list)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_list_geomorph), intent(in) :: list
  character(len=256) :: msg

  if (list%susp_d50 <= 0.0) call par_stop("list_geomorph: f_suspend requires susp_d50 > 0")
  if (list%susp_tausc <= 0.0) call par_stop("list_geomorph: susp_tausc must be > 0")
  if (list%susp_beta <= 0.0) call par_stop("list_geomorph: susp_beta must be > 0")
  if (list%susp_wf < 0.0) call par_stop("list_geomorph: susp_wf must be >= 0")
  select case (list%f_esform)
    case (1)      ! 超過掃流力線形(簡易式)。esa が必須
      if (list%susp_esa <= 0.0) then
        call par_stop("list_geomorph: f_esform=1 requires susp_esa > 0")
      end if
    case (2)      ! 板倉・岸(定数は原式固定。esa/tausc は不使用)
      continue
    case default
      call par_stop("list_geomorph: f_esform must be 1(excess-shear linear) or 2(Itakura-Kishi)")
  end select

  gm%f_esform = list%f_esform
  gm%sd50 = list%susp_d50
  gm%stausc = list%susp_tausc
  gm%beta = list%susp_beta
  gm%esa = list%susp_esa
  if (list%susp_wf > 0.0) then
    gm%wf = list%susp_wf
  else
    gm%wf = rubey_wf(gm%sgrav, p%gg, gm%sd50)
    write(msg,'(a,es10.3,a)') "geomorph suspend: settling velocity (Rubey) = ", gm%wf, " m/s"
    call par_info(trim(msg))
  end if
end subroutine


!----------------------------------------------------------------------
module subroutine calc_suspend(gm, p, g, s, dtw)
  type(t_geomorph), intent(in) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: dtw       ! 水柱側の実効時間刻み(morfac を含まない)
  integer :: i, j
  real :: hh, taus, ceq, cc, fx, dzb, cap, fxg

  !$omp parallel do schedule(static) private(i, j, hh, taus, ceq, cc, fx, dzb, cap, fxg)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      if (s%h(i,j) <= p%dd) then
        ! 乾燥セル: 浮遊分を全量河床へ
        if (s%hs(i,j) <= 0.0) cycle
        fx = -s%hs(i,j)
      else
        ! 平衡濃度(浸食レート E = wf・ceq に相当する濃度換算)
        hh = max(s%h(i,j), p%dv)
        taus = g%rn(i,j)**2 * s%vv(i,j)**2 / (gm%sgrav * gm%sd50 * hh**(1.0/3.0))
        ceq = 0.0
        if (gm%f_esform == 1) then
          ! 超過掃流力線形(簡易式)
          if (taus > gm%stausc) ceq = gm%esa * (taus / gm%stausc - 1.0)
        else
          ! 板倉・岸(ceq = q_su / wf)
          ceq = ceq_itakura(gm, p%gg, taus)
        end if
        cc = 0.0
        if (s%hs(i,j) > 0.0) cc = s%hs(i,j) / s%h(i,j)
        ! 正味の交換(>0: 浸食で hs へ、<0: 沈降で河床へ)
        fx = gm%wf * (ceq - gm%beta * cc) * dtw
        if (fx > 0.0) then
          ! 可動層クランプ(河床側は ×morfac・poroi で減るため換算して制限)
          fx = min(fx, s%sd(i,j) / (gm%morfac * gm%poroi))
        else
          fx = max(fx, -max(s%hs(i,j), 0.0))    ! 沈降は浮遊量まで
        end if
        if (fx == 0.0) cycle
      end if
      s%hs(i,j) = s%hs(i,j) + fx
      ! 共動更新(z と sd が同じ Δz で動く → 帯水層底 (z - sd) は不変)
      dzb = -fx * gm%morfac * gm%poroi
      s%z(i,j) = s%z(i,j) + dzb
      s%sd(i,j) = s%sd(i,j) + dzb
      ! 浸食で地下水容量が現在の貯留を下回ったら、超過分を地表水へ渡す
      ! (calc_fluvial と同じ整合。反対称適用)
      if (s%gw_active) then
        cap = s%sd(i,j) * g%sy0
        if (s%hg(i,j) > cap) then
          fxg = s%hg(i,j) - cap
          s%hg(i,j) = cap
          s%h(i,j) = s%h(i,j) + fxg
        end if
      end if
    end do
  end do
  !$omp end parallel do

end subroutine


!----------------------------------------------------------------------
pure function ceq_itakura(gm, gg, taus) result(ceq)
  type(t_geomorph), intent(in) :: gm
  real, intent(in) :: gg      ! 重力加速度
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
  ustar = sqrt(taus * gm%sgrav * gg * gm%sd50)
  qsu = ik_k * (ik_alpha / (gm%sgrav + 1.0) &
                * (gm%sgrav * gg * gm%sd50 / ustar) * omega - gm%wf)
  ceq = max(qsu, 0.0) / gm%wf
end function


!----------------------------------------------------------------------
pure function rubey_wf(sgrav, gg, d) result(wf)
  real, intent(in) :: sgrav, gg, d
  real :: wf
  real :: bb
  real, parameter :: nu = 1.0e-6
  bb = 36.0 * nu**2 / (sgrav * gg * d**3)
  wf = (sqrt(2.0 / 3.0 + bb) - sqrt(bb)) * sqrt(sgrav * gg * d)
end function


end submodule
