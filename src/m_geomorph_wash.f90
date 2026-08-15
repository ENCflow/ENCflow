!======================================================================
! m_geomorph の submodule: 斜面浸食(f_wash。雨滴+面状侵食)
!   浸食した土砂を浮遊砂柱状量 s%hs へ注入し、河床(z, sd)から共動で
!   差し引く。**河道への土砂流入は浮遊砂の移流が自動的に実現する**
!   (斜面→河道の受け渡しに専用機構は不要。geomorph_plan.md §2.3)。
!   このため f_suspend が必須(init_wash が検証)。
!
!   浸食レート(m/s。固体体積):
!     E = wash_kr・P + wash_kf・max(τ*/τ*c − 1, 0)
!       第1項: 雨滴侵食(P = 地表到達降雨強度 s%pre [m/s]。kr は
!               「雨量あたりの剥離固体体積」の無次元係数)
!       第2項: 面状侵食(地表流せん断の超過に線形。τ* は浮遊砂粒径
!               sd50 のマニング閉じ = calc_suspend と同一)
!   適用範囲: 陸の湿潤セル(h > dd)のみ。乾燥セルは剥離しても suspend の
!   乾燥繰り入れで即時に河床へ戻る(純粋な空回り)ため対象外。
!   河道セル(rw > 0)は対象外(河道内の浸食は f_fluvial / f_suspend の
!   管轄。「斜面」プロセスの意味論を保つ。fn_rw 未指定なら rw=0 の
!   全域=全陸セルに適用される)。
!   可動層クランプ・共動更新・gwflow 容量引き渡し・MORFAC の台帳分離は
!   calc_suspend と同一の規約。
!   斜面の表層浸食が s%sd を直接減らすため、「土層が薄くなり早く飽和して
!   流出が早まる」結合(plan §2.5 のユーザー要件)がそのまま現れる。
!   sd=0 まで削れたセルは岩盤露出となり浸食が止まる(badland の挙動)
!======================================================================
submodule(m_geomorph) m_geomorph_wash
  use m_parallel, only : par_stop, dcp
  implicit none

contains

!----------------------------------------------------------------------
! 斜面浸食の初期化(検証のみ。エッジ作業領域は不要=セル内注入のみ)
!----------------------------------------------------------------------
module subroutine init_wash(gm, list)
  type(t_geomorph), intent(inout) :: gm
  type(t_list_geomorph), intent(in) :: list

  ! 浮遊砂が輸送を担う(注入先 hs の移流・沈降がないと土砂が動けない)
  if (gm%f_suspend <= 0) then
    call par_stop("list_geomorph: f_wash requires f_suspend=1 " &
                  // "(detached soil is transported as suspended sediment)")
  end if
  if (list%wash_kr < 0.0) call par_stop("list_geomorph: wash_kr must be >= 0")
  if (list%wash_kf < 0.0) call par_stop("list_geomorph: wash_kf must be >= 0")
  if (list%wash_kr <= 0.0 .and. list%wash_kf <= 0.0) then
    call par_stop("list_geomorph: f_wash requires wash_kr > 0 or wash_kf > 0")
  end if
  if (list%wash_tausc <= 0.0) call par_stop("list_geomorph: wash_tausc must be > 0")

  gm%wkr = list%wash_kr
  gm%wkf = list%wash_kf
  gm%wtausc = list%wash_tausc
end subroutine


!----------------------------------------------------------------------
! 斜面浸食(セル内の剥離→hs 注入のみ=エッジ・ハロ不要)
!----------------------------------------------------------------------
module subroutine calc_wash(gm, p, g, s, dtw)
  type(t_geomorph), intent(in) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: dtw       ! 水柱側の実効時間刻み(morfac を含まない)
  integer :: i, j
  real :: hh, taus, er, fx, dzb, cap, fxg

  !$omp parallel do schedule(static) private(i, j, hh, taus, er, fx, dzb, cap, fxg)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      if (g%rw(i,j) > 0) cycle          ! 河道セルは対象外(fluvial/suspend の管轄)
      if (s%h(i,j) <= p%dd) cycle       ! 乾燥セルは空回りのため対象外
      ! 浸食レート: 雨滴 + 面状(超過せん断線形)
      er = gm%wkr * s%pre(i,j)
      if (gm%wkf > 0.0) then
        hh = max(s%h(i,j), p%dv)
        taus = g%rn(i,j)**2 * s%vv(i,j)**2 / (gm%sgrav * gm%sd50 * hh**(1.0/3.0))
        if (taus > gm%wtausc) er = er + gm%wkf * (taus / gm%wtausc - 1.0)
      end if
      if (er <= 0.0) cycle
      ! 可動層クランプ(河床側は ×morfac・poroi で減るため換算して制限)
      fx = min(er * dtw, s%sd(i,j) / (gm%morfac * gm%poroi))
      if (fx <= 0.0) cycle
      s%hs(i,j) = s%hs(i,j) + fx
      ! 共動更新(z と sd が同じ Δz で動く → 帯水層底 (z - sd) は不変)
      dzb = -fx * gm%morfac * gm%poroi
      s%z(i,j) = s%z(i,j) + dzb
      s%sd(i,j) = s%sd(i,j) + dzb
      ! 浸食で地下水容量が現在の貯留を下回ったら、超過分を地表水へ渡す
      ! (calc_suspend と同じ整合。反対称適用)
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
