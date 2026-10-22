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
  use m_parallel, only : par_info, par_stop, dcp, par_halo_cell
  implicit none

contains

!----------------------------------------------------------------------
! 斜面浸食の初期化(検証のみ。エッジ作業領域は不要=セル内注入のみ)
!----------------------------------------------------------------------
module subroutine init_wash(gm, list)
  type(t_geomorph), intent(inout) :: gm
  type(t_list_geomorph), intent(in) :: list
  real :: kr, kf                       ! 既定適用後の有効値(§62)

  ! 浮遊砂が輸送を担う(注入先 hs の移流・沈降がないと土砂が動けない)
  if (gm%f_suspend <= 0) then
    call par_stop("list_geomorph: f_wash requires f_suspend=1 " &
                  // "(detached soil is transported as suspended sediment)")
  end if
  ! どちらも未指定なら両方に既定(経験係数。校正前提。§62)。片方だけ指定なら
  ! 他方の 0 は「その項なし」の明示として尊重する
  kr = list%wash_kr
  kf = list%wash_kf
  if (kr < 0.0) call par_stop("list_geomorph: wash_kr must be >= 0")
  if (kf < 0.0) call par_stop("list_geomorph: wash_kf must be >= 0")
  if (kr == 0.0 .and. kf == 0.0) then
    kr = gm_param("wash_kr", kr, 0.01, "")
    kf = gm_param("wash_kf", kf, 1.0e-5, " m/s")
  end if
  if (list%wash_tausc <= 0.0) call par_stop("list_geomorph: wash_tausc must be > 0")

  gm%wkr = kr
  gm%wkf = kf
  gm%wtausc = list%wash_tausc
end subroutine


!----------------------------------------------------------------------
! 斜面浸食(セル内の剥離→hs 注入のみ=エッジ・ハロ不要)
!----------------------------------------------------------------------
module subroutine calc_wash(gm, p, g, s, dtw)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: dtw       ! 水柱側の実効時間刻み(morfac を含まない)
  integer :: i, j
  real :: hh, taus, er, fx, dzb, cap, fxg
  logical :: spread

  spread = (gm%wlw%nsm > 0)
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
      ! 河床の細粒分の帳簿(§84.10): 利用可能率 f = min(1, sf/L_a) を乗じる
      if (gm%f_bedfines > 0) er = er * min(1.0, s%sf(i,j) * gm%fin%lainv)
      ! 可動層クランプ(河床側は ×morfac・poroi で減るため換算して制限)
      fx = min(er * dtw, s%sd(i,j) / (gm%morfac * gm%poroi))
      if (gm%f_bedfines > 0) fx = min(fx, s%sf(i,j) / (gm%morfac * gm%poroi))
      if (fx <= 0.0) cycle
      s%hs(i,j) = s%hs(i,j) + fx
      ! 剥離深の横方向拡散(wet_lw > 0。§84.15): 集積面に積み spread_wet に委ねる
      if (spread) then
        gm%wlw%e(i,j) = gm%wlw%e(i,j) + fx * gm%morfac * gm%poroi
        cycle
      end if
      ! 共動更新(z と sd が同じ Δz で動く → 帯水層底 (z - sd) は不変)
      dzb = -fx * gm%morfac * gm%poroi
      s%z(i,j) = s%z(i,j) + dzb
      s%sd(i,j) = s%sd(i,j) + dzb
      if (gm%f_bedfines > 0) s%sf(i,j) = max(s%sf(i,j) + dzb, 0.0)
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


!----------------------------------------------------------------------
! 剥離深の横方向拡散の初期化(wet_lw > 0。§84.15)
!   核は spl_lc(init_splash)と同じ: パス数 N = 4(ℓ_w/Δmin)²、重み
!   w = ℓ_w²/(2NΔ²) ≤ 1/8(市松モードで伝達関数が非負)。f_suspend が必須
!   (剥離を集積するのは calc_suspend の巻き上げと calc_wash の剥離)
!----------------------------------------------------------------------
module subroutine init_wetlw(gm, g, list)
  type(t_geomorph), intent(inout) :: gm
  type(t_geoinfo), intent(in) :: g
  type(t_list_geomorph), intent(in) :: list
  real :: dmin
  character(len=160) :: msg

  if (gm%f_suspend <= 0) then
    call par_stop("list_geomorph: wet_lw requires f_suspend=1 (it spreads the wet detachment)")
  end if
  gm%wlw%lw = list%wet_lw
  dmin = min(g%dx, g%dy)
  gm%wlw%nsm = max(1, nint(4.0 * (gm%wlw%lw / dmin)**2))
  gm%wlw%wsx = min(0.125, gm%wlw%lw**2 / (2.0 * gm%wlw%nsm * g%dx**2))
  gm%wlw%wsy = min(0.125, gm%wlw%lw**2 / (2.0 * gm%wlw%nsm * g%dy**2))
  write(msg, '(a,es10.3,a,i0,a)') "geomorph: wet detachment spreading length wet_lw = ", gm%wlw%lw, &
                                 " m (", gm%wlw%nsm, " smoothing passes)"
  call par_info(trim(msg))
  if (.not. allocated(gm%wlw%e)) then
    allocate(gm%wlw%e(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
    allocate(gm%wlw%et(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  end if
end subroutine


!----------------------------------------------------------------------
! 剥離深の横方向拡散(wet_lw > 0。§84.15)
!   calc_suspend(巻き上げ)・calc_wash(剥離)が帯内に集積した剥離深 e [m]
!   (源セルの可動層クランプ済み。hs は源セルに注入済み)を、5 点ガウス核
!   (自セル 1−2wx−2wy、x 近傍 wx、y 近傍 wy)で nsm 回平滑化してから
!   各セルの z・sd から引く。無効な近傍(範囲外・x=0・海セル)は自セル値で
!   鏡像 = その方向の移動なし。核が対称で鏡像が保存的なので Σe は不変
!   (固体総量が保存される)。受け側の sd が足りない分は岩盤露出として捨て、
!   台帳 vlost に積む(dispose で報告。0 なら厳密保存)。
!   ハロ: 集積は帯内のみなので最初に e のハロを交換し、各パスの後にも
!   交換する(smooth_z と同じ。パス数は namelist 由来で全ランク同一)。
!   適用後に帯内の e を 0 に戻す(ハロ行は次回の交換で上書きされる)
!----------------------------------------------------------------------
module subroutine spread_wet(gm, g, s)
  type(t_geomorph), intent(inout) :: gm
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: i, j, n
  real :: ec, ee, ew, en, es, wx, wy, w0, ez, cap, fxg, area, vl

  wx = gm%wlw%wsx
  wy = gm%wlw%wsy
  w0 = 1.0 - 2.0 * (wx + wy)
  area = g%dx * g%dy
  call par_halo_cell(gm%wlw%e)
  do n = 1, gm%wlw%nsm
    !$omp parallel do schedule(static) private(i, j, ec, ee, ew, en, es)
    do j = dcp%js, dcp%je
      gm%wlw%et(:, j) = gm%wlw%e(:, j)
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0) cycle
        if (g%sw(i,j) > 0) cycle
        ec = gm%wlw%e(i,j)
        ee = ec; ew = ec; en = ec; es = ec
        if (i < g%nx) then
          if (g%x(i+1,j) > 0 .and. g%sw(i+1,j) <= 0) ee = gm%wlw%e(i+1,j)
        end if
        if (i > 1) then
          if (g%x(i-1,j) > 0 .and. g%sw(i-1,j) <= 0) ew = gm%wlw%e(i-1,j)
        end if
        if (g%x(i,j+1) > 0 .and. g%sw(i,j+1) <= 0) en = gm%wlw%e(i,j+1)
        if (g%x(i,j-1) > 0 .and. g%sw(i,j-1) <= 0) es = gm%wlw%e(i,j-1)
        gm%wlw%et(i,j) = w0 * ec + wx * (ee + ew) + wy * (en + es)
      end do
    end do
    !$omp end parallel do
    gm%wlw%e(:, dcp%js:dcp%je) = gm%wlw%et(:, dcp%js:dcp%je)
    call par_halo_cell(gm%wlw%e)
  end do

  vl = 0.0
  !$omp parallel do schedule(static) private(i, j, ez, cap, fxg) reduction(+:vl)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      ez = gm%wlw%e(i,j)
      if (ez <= 0.0) cycle
      gm%wlw%e(i,j) = 0.0
      ! 受け側の可動層クランプ(岩盤露出で止まる。不足分は台帳へ)
      if (ez > s%sd(i,j)) then
        vl = vl + (ez - s%sd(i,j)) * area
        ez = s%sd(i,j)
        if (ez <= 0.0) cycle
      end if
      ! 共動更新(z と sd が同じ Δz で動く → 帯水層底 (z - sd) は不変)
      s%z(i,j) = s%z(i,j) - ez
      s%sd(i,j) = s%sd(i,j) - ez
      if (gm%f_bedfines > 0) s%sf(i,j) = max(s%sf(i,j) - ez, 0.0)
      ! 浸食で地下水容量が現在の貯留を下回ったら、超過分を地表水へ渡す
      ! (calc_suspend と同じ整合)
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
  gm%wlw%vlost = gm%wlw%vlost + vl
end subroutine

end submodule
