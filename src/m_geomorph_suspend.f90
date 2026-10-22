!======================================================================
! m_geomorph の submodule: 浮遊砂の E-D 交換(f_suspend)
!   移流本体は m_swflow_enc のステップ内輸送(advect_scalar)が担い、
!   ここは浸食・沈降(E-D)と平衡濃度式のみ。平衡濃度式・沈降速度の
!   補助関数は submodule レベルの私有手続き(contained は使わない。§13)
!======================================================================
submodule(m_geomorph) m_geomorph_suspend
  use m_parallel, only : par_info, par_stop, dcp
  use m_swflow_enc, only : sct, sect_v, sect_sigma   ! σ 断面の濃度解釈(sct%have_sect, sct%sdep。§26)
  use m_sedform, only : t_ceqpar, sedform_set_ceq, sed_ceq_itakura, sed_rubey_wf   ! 平衡濃度・沈降速度の式(§84.9)
  implicit none

contains

!----------------------------------------------------------------------
module subroutine init_suspend(gm, p, list)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_list_geomorph), intent(in) :: list
  character(len=256) :: msg
  real :: d50, esa                     ! 既定適用後の有効値(§62)

  esa = list%susp_esa
  d50 = gm_param("susp_d50", list%susp_d50, 0.0002, " m")   ! 細砂(§62)
  if (d50 <= 0.0) call par_stop("list_geomorph: f_suspend requires susp_d50 > 0")
  if (list%susp_tausc <= 0.0) call par_stop("list_geomorph: susp_tausc must be > 0")
  if (list%susp_beta <= 0.0) call par_stop("list_geomorph: susp_beta must be > 0")
  if (list%susp_wf < 0.0) call par_stop("list_geomorph: susp_wf must be >= 0")
  select case (list%f_esform)
    case (1)      ! 超過掃流力線形(簡易式)。esa は校正係数(既定 1e-4。§62)
      esa = gm_param("susp_esa", list%susp_esa, 1.0e-4, "")
      if (esa <= 0.0) then
        call par_stop("list_geomorph: f_esform=1 requires susp_esa > 0")
      end if
    case (2)      ! 板倉・岸(定数は原式固定。esa/tausc は不使用)
      continue
    case default
      call par_stop("list_geomorph: f_esform must be 1(excess-shear linear) or 2(Itakura-Kishi)")
  end select

  gm%f_esform = list%f_esform
  gm%sd50 = d50
  gm%stausc = list%susp_tausc
  gm%beta = list%susp_beta
  gm%esa = esa
  if (list%susp_wf > 0.0) then
    gm%wf = list%susp_wf
  else
    gm%wf = sed_rubey_wf(gm%sgrav, p%gg, gm%sd50)
    write(msg,'(a,es10.3,a)') "geomorph: suspended sediment settling velocity (Rubey) = ", &
                              gm%wf, " m/s"
    call par_info(trim(msg))
  end if
  ! 平衡濃度式の係数を葉モジュールに登録する(区間流入の平衡濃度給砂
  ! inflow_cs_eq が m_boundary から同じ式で評価するため。§84.9)
  block
    type(t_ceqpar) :: par
    par%form = gm%f_esform; par%esa = gm%esa; par%stausc = gm%stausc
    par%sgrav = gm%sgrav; par%d50 = gm%sd50; par%wf = gm%wf; par%gg = p%gg
    call sedform_set_ceq(par)
  end block
end subroutine


!----------------------------------------------------------------------
module subroutine calc_suspend(gm, p, g, s, dtw)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: dtw       ! 水柱側の実効時間刻み(morfac を含まない)
  integer :: i, j
  real :: hh, taus, ceq, cc, fx, dzb, cap, fxg, afx, tsce
  logical :: spread

  spread = (gm%wlw%nsm > 0)
  !$omp parallel do schedule(static) private(i, j, hh, taus, ceq, cc, fx, dzb, cap, fxg, afx, tsce)
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
          ceq = sed_ceq_itakura(gm%sgrav, p%gg, gm%sd50, gm%wf, taus)
        end if
        ! 定着(§84.8): 浸食項(平衡濃度)だけを定着度 a で減らす。沈降は不変。
        ! f_esform=1 は限界掃流力を τ*c,s (1 + c_τ a) に上げ、2(τ*c を持たない)は
        ! ceq に 1/(1 + c_τ a) を乗じる。a = 0 のセルは分岐に入らず厳密に不変
        if (gm%f_fixation > 0 .and. ceq > 0.0) then
          afx = s%fx(i,j)
          if (afx > 0.0) then
            if (gm%f_esform == 1) then
              tsce = gm%stausc * (1.0 + gm%fix%ctau * afx)
              ceq = 0.0
              if (taus > tsce) ceq = gm%esa * (taus / tsce - 1.0)
            else
              ceq = ceq / (1.0 + gm%fix%ctau * afx)
            end if
          end if
        end if
        ! 河床の細粒分の帳簿(§84.10): 浸食は在庫の利用可能率 f = min(1, sf/L_a)
        ! で減らす(f = 1 のセルは 1.0 の乗算で厳密に不変)
        if (gm%f_bedfines > 0) ceq = ceq * min(1.0, s%sf(i,j) * gm%fin%lainv)
        ! 濃度は水の体積あたり = hs / vh(vh = σ の矩形換算水深。swflow の
        ! 移流の供給元濃度・水質の cqc と同じ解釈。σ 非適用セルは vh = h)
        cc = 0.0
        if (s%hs(i,j) > 0.0) then
          if (sct%have_sect) then
            cc = s%hs(i,j) / sect_v(s%h(i,j), sct%sdep(i,j))
          else
            cc = s%hs(i,j) / s%h(i,j)
          end if
        end if
        ! 正味の交換(>0: 浸食で hs へ、<0: 沈降で河床へ)。σ 有効セルでは
        ! 水に接する河床の幅が湿潤幅率 σ(h) 倍なので、河道平面積あたりの
        ! 交換量に σ(h) を掛ける(満杯以上・矩形では 1)。河床変動 Δz は
        ! 平面積平均のまま(§26 の近似)
        fx = gm%wf * (ceq - gm%beta * cc) * dtw
        if (sct%have_sect) fx = fx * sect_sigma(s%h(i,j), sct%sdep(i,j))
        if (fx > 0.0) then
          ! 可動層クランプ(河床側は ×morfac・poroi で減るため換算して制限)
          fx = min(fx, s%sd(i,j) / (gm%morfac * gm%poroi))
          ! 細粒分の在庫を超えない(sf = sd なら同じ値 = 厳密に不変)
          if (gm%f_bedfines > 0) fx = min(fx, s%sf(i,j) / (gm%morfac * gm%poroi))
        else
          fx = max(fx, -max(s%hs(i,j), 0.0))    ! 沈降は浮遊量まで
        end if
        if (fx == 0.0) cycle
      end if
      s%hs(i,j) = s%hs(i,j) + fx
      ! 剥離深の横方向拡散(wet_lw > 0。§84.16): 巻き上げ分は河床から直接引かず
      ! 集積面に積み、spread_wet が ℓ_w で平滑化して z・sd から引く。沈降
      ! (fx < 0)と乾燥繰り入れは従来どおり局所適用(堆積は水のある所に起きる)
      if (spread .and. fx > 0.0) then
        gm%wlw%e(i,j) = gm%wlw%e(i,j) + fx * gm%morfac * gm%poroi
        cycle
      end if
      ! 共動更新(z と sd が同じ Δz で動く → 帯水層底 (z - sd) は不変)
      dzb = -fx * gm%morfac * gm%poroi
      ! 土層を使い切るとき sd を厳密に 0 で止める(上のクランプ fx = sd/(morfac·poroi)
      ! は往復の丸めで sd を −1e-22 にし得る。負の sd は掃流砂の可動層クランプで
      ! 流砂の符号を反転させ FPE に至った実バグ。§84.5)
      if (dzb < -s%sd(i,j)) dzb = -s%sd(i,j)
      s%z(i,j) = s%z(i,j) + dzb
      s%sd(i,j) = s%sd(i,j) + dzb
      ! 細粒分の帳簿: 浸食も沈降も細粒分なので sf を同じ Δz で動かす(sd − sf は
      ! 不変)。在庫クランプの往復の丸めで僅かに負になれば 0 で止める
      if (gm%f_bedfines > 0) s%sf(i,j) = max(s%sf(i,j) + dzb, 0.0)
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





end submodule
