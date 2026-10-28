!======================================================================
! m_geomorph の submodule: 流水による岩盤下刻(f_rockinc)
!   docs/mountain_stream_plan.md(第 1 段)、developer.md §89。
!   岩盤面 R = z − sd を、流水の剥離(plucking)と、運ばれる礫の研磨(abrasion。
!   tools 効果)で下げる。可動層 H = sd が露出率 P_r = exp(−H/H*) で下刻を抑え
!   (被覆)、掃流砂の流出には利用可能率 F_s = 1 − P_r を掛ける(calc_fluvial):
!     τ_b  = ρ_w g n² |V|² / h_e^{1/3}  (既存の流砂と同じ Manning 閉じ。h_e = max(h, d_v))
!     E_p0 = f_r k_p max(τ_b/τ_c − 1, 0)^m   剥離(超過せん断応力型 k_e (τ − τ_c)^m を
!                                            k_p = k_e τ_c^m と置いた比形)
!     E_a0 = f_r β q_b F_s(H^n)              研磨(q_b: セルの掃流砂容量 = 単位幅の固体流砂量。
!                                            q_b F_s がセルから出る掃流砂 = 床を叩く礫の量)
!     dR/dt = −(E_p0 + E_a0) P_r、  dH/dt = E_p0 P_r(研磨の細粒分は被覆に加えない)
!   換算は 1:1(剥離した岩の厚さ = 可動層の厚さ。風化 f_wthr・基岩の崩落 rf_bedrock と
!   同じ規約で、岩盤の厚さを可動層のかさ厚換算で数える。独自の簡略化)。z は剥離では
!   動かず(sd だけが増える)、研磨の分だけ下がる(細粒分は系外 = 台帳に記録)。
!   時間積分: 水理(τ_b, q_b)と F_s(H^n) を更新の頭で固定し、露出率だけを厳密に積分する
!   (e^{H/H*} が時間に比例して増える):
!     B_p = H* ln(1 + (E_p0 dts/H*) e^{−H^n/H*})   (風化 calc_wthr の伝播子と同じ形)
!     B_a = (E_a0/E_p0) B_p(E_p0 > 0)、 E_a0 dts e^{−H^n/H*}(E_p0 = 0)
!   B は自己被覆で ln の速さでしか増えないので dzmax 型の安全弁は置かず、最大の B/H* を
!   診断として報告する。薄層の排出率 L = q_b/(Δ (1 − λ) H*)と dts の積の最大も診断として
!   報告する(目安 L·dts <= 0.5。plan §4.3)。
!   適用は湿潤(h > dd)・非海域の有効セル(河道マスク rw は見ない)。セル局所で近傍を
!   読まない(冒頭のハロ交換は不要)。末尾で sd(研磨があれば z も)のハロを交換する
!   (続く calc_fluvial が近傍の sd・z を読む。判定は namelist 由来で全ランク同一)。
!   状態: s%ri(累積下刻 = ΣB。出力 Ri。私有 save geomorph_rockinc.dat。契約 5・§83)。
!   侵食性倍率 f_r は fn_rock(方式 2 の配布。未指定なら確保しない)。台帳は剥離・研磨の
!   かさ体積の行部分和(real64 → par_sum_rows = 決定的)。
!   無効時は呼ばれない(配列なし。calc_fluvial の分岐の判定だけ)。
!
!   土石流の項(rock_kdb > 0。f_debris の構成。§89.18、plan §12): 準静的な駆動応力の超過形
!     τ_d  = ρ_w (1 + sC) g_e h_t tanθ_f   (h_t = h + h_s、θ_f は流向の河床勾配(下りのみ)、
!                                           g_e は運動方程式と同じ有効重力)
!     E_d0 = f_r k_d max(τ_d/τ_cd − 1, 0)^{m_d}
!   を、濃い混合体(C >= db_cmin)が流れている(|V| >= db_vstop)湿潤セルに掛ける。生成物は
!   剥離と同じく 1:1 で可動層へ(z は不変)、被覆は同じ伝播子 rock_cover_inc で積分する。
!   計算は calc_debris の 2 パスの中(パス 1 が E_d0 を作業配列 edb に、パス 2 が E-D の適用後の
!   sd で積分)。ここは検査・確保・台帳と伝播子だけ。土石流の構成では流水の項(rock_kp・
!   rock_beta)を使わない(暦の勘定を出水の計算と混ぜない。§89.18 の 6)ので calc_rockinc は
!   呼ばれない。
!======================================================================
submodule(m_geomorph) m_geomorph_rockinc
  use m_parallel, only : par_info, par_stop, dcp, is_root, par_halo_cell, par_scatter_cell, &
                         par_sum_rows, par_allreduce_max
  use m_fileio, only : fileio_read_matrix
  use m_restart, only : restart_write_cell, restart_read_cell
  use m_sysdep_util, only : sysdep_mkdir
  use m_util, only : rtoa
  implicit none

  real, parameter :: rhow = 1000.0       ! 水の密度 (kg/m3。淡水。debris・bedslide と同じ)
  real, parameter :: xsmall = 0.01       ! ln(1 + x)・1 − exp(−x) を級数で評価する引数の上限
                                         ! (これ以上では組込み関数の相対誤差が 1e-14 以下)

contains

!----------------------------------------------------------------------
module subroutine init_rockinc(gm, p, g, s, list)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_list_geomorph), intent(in) :: list
  integer :: i, j
  real :: bad(1)

  ! --- パラメータ検証(k_p・β・τ_c・k_d・τ_cd は校正値で既定を置かない。0 は「その項なし」。§89) ---
  if (list%rock_hstar <= 0.0) then
    call par_stop("list_geomorph: f_rockinc requires rock_hstar > 0 (cover length scale H*, m)")
  end if
  if (list%rock_kp < 0.0 .or. list%rock_beta < 0.0 .or. list%rock_kdb < 0.0) then
    call par_stop("list_geomorph: rock_kp, rock_beta and rock_kdb must be >= 0")
  end if
  if (gm%f_debris > 0) then
    ! 土石流の構成は土石流の項だけ(流水の下刻は出水の計算が担う。§89.18 の 6)
    if (list%rock_kp > 0.0 .or. list%rock_beta > 0.0) then
      call par_stop("list_geomorph: with f_debris=1, f_rockinc uses only the debris-flow term; " &
                    // "set rock_kp = rock_beta = 0 (fluvial incision belongs to the flood runs)")
    end if
    if (list%rock_kdb <= 0.0) then
      call par_stop("list_geomorph: f_rockinc with f_debris=1 requires rock_kdb > 0 " &
                    // "(rock erosion by debris flows)")
    end if
    if (list%rock_taucdb <= 0.0) then
      call par_stop("list_geomorph: rock_kdb > 0 requires rock_taucdb > 0 (threshold of the " &
                    // "driving stress, Pa)")
    end if
    if (list%rock_mdb <= 0.0) call par_stop("list_geomorph: rock_mdb must be > 0")
    ! 濃い混合体の門(C >= db_cmin)。0 だと清水のセルも土石流の係数で削る
    if (list%db_cmin <= 0.0 .or. list%db_cmin >= 1.0 / gm%poroi) then
      call par_stop("list_geomorph: rock_kdb > 0 requires db_cmin in (0, C*) " &
                    // "(only dense mixtures erode the rock with the debris-flow term)")
    end if
  else
    if (list%rock_kdb > 0.0) then
      call par_stop("list_geomorph: rock_kdb > 0 requires f_debris=1 (rock erosion by debris flows)")
    end if
    if (list%rock_kp <= 0.0 .and. list%rock_beta <= 0.0) then
      call par_stop("list_geomorph: f_rockinc requires rock_kp > 0 (plucking) and/or " &
                    // "rock_beta > 0 (abrasion by bed load)")
    end if
  end if
  if (list%rock_kp > 0.0) then
    if (list%rock_tauc <= 0.0) then
      call par_stop("list_geomorph: rock_kp > 0 requires rock_tauc > 0 (plucking threshold, Pa)")
    end if
    if (list%rock_m <= 0.0) call par_stop("list_geomorph: rock_m must be > 0")
  end if
  gm%rk%kp = list%rock_kp
  gm%rk%tauc = list%rock_tauc
  gm%rk%pm = list%rock_m
  gm%rk%beta = list%rock_beta
  gm%rk%hstar = list%rock_hstar
  gm%rk%hsinv = 1.0 / list%rock_hstar
  gm%rk%fl = (gm%rk%kp > 0.0 .or. gm%rk%beta > 0.0)
  if (gm%rk%fl) then
    call par_info("geomorph: rock incision on (k_p = " // fmt_e(gm%rk%kp) // " m/s, tau_c = " &
                  // rtoa(gm%rk%tauc) // " Pa, m = " // rtoa(gm%rk%pm) // ", beta = " &
                  // fmt_e(gm%rk%beta) // " 1/m, H* = " // rtoa(gm%rk%hstar) // " m)")
  end if
  gm%rk%db = (list%rock_kdb > 0.0)
  if (gm%rk%db) then
    gm%rk%kdb = list%rock_kdb
    gm%rk%taucdb = list%rock_taucdb
    gm%rk%mdb = list%rock_mdb
    call par_info("geomorph: rock erosion by debris flows on (k_d = " // fmt_e(gm%rk%kdb) &
                  // " m/s, tau_cd = " // rtoa(gm%rk%taucdb) // " Pa, m_d = " // rtoa(gm%rk%mdb) &
                  // ", H* = " // rtoa(gm%rk%hstar) // " m)")
    ! 作業配列(calc_debris のパス 1 → パス 2)と台帳の行部分和
    allocate(gm%rk%edb(dcp%ish:dcp%ieh, dcp%js:dcp%je), source = 0.0)
    allocate(gm%rk%vdrow(dcp%js:dcp%je), source = 0.0_real64)
  end if
  if (gm%f_suspend > 0 .and. gm%f_bedfines <= 0) then
    call par_info("geomorph: note: without f_bedfines the plucked rock (coarse) can also be " &
                  // "entrained as suspended load; f_bedfines = 1 keeps it in the coarse class")
  end if
  if (digits(1.0) < 40) then
    call par_info("geomorph: note: single precision; small rock-incision increments may be lost " &
                  // "in z (double precision is recommended for long-term runs)")
  end if

  ! --- 侵食性倍率の分布(指定時のみ確保。>= 0 を検査。判定は全ランク集約 = collective) ---
  if (len_trim(list%fn_rock) > 0) then
    gm%rk%map = .true.
    allocate(gm%rk%fr(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
    call read_cellmap(p, g, list%fn_rock, gm%rk%fr)
    bad(1) = 0.0
    do j = dcp%js, dcp%je
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0) cycle
        if (.not. (gm%rk%fr(i,j) >= 0.0)) bad(1) = 1.0        ! 負値と非数
      end do
    end do
    call par_allreduce_max(bad)
    if (bad(1) > 0.0) call par_stop("list_geomorph: fn_rock must be >= 0: " // trim(list%fn_rock))
  end if

  ! --- 台帳(行部分和)と累積下刻(出力 Ri・私有 save) ---
  allocate(gm%rk%vprow(dcp%js:dcp%je), source = 0.0_real64)
  allocate(gm%rk%varow(dcp%js:dcp%je), source = 0.0_real64)
  if (.not. allocated(s%ri)) allocate(s%ri(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  if (p%f_state_restore > 0) call restore_rockinc(gm, p, g, s)
end subroutine


!----------------------------------------------------------------------
module subroutine calc_rockinc(gm, p, g, s, dts)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: dts
  integer :: i, j
  real :: hh, vv2, rn2, taub, taus, qc, h0, pr, fr, ep0, ea0, x, bp, ba
  real :: area, lcoef, bmax, lmax
  real(real64) :: vp, va
  logical :: abr

  area = 1.0 / gm%wrk%ainv
  abr = (gm%rk%beta > 0.0)
  ! 薄層の排出率の目安 L ≈ q_b / (Δ (1 − λ) H*)(セルの容量から。plan §4.3 の時間尺度。
  ! L·dts の最大を診断として報告する)
  lcoef = gm%poroi * gm%rk%hsinv / min(g%dx, g%dy)
  bmax = 0.0
  lmax = 0.0
  !$omp parallel do schedule(static) reduction(max: bmax, lmax) &
  !$omp   private(i, j, hh, vv2, rn2, taub, taus, qc, h0, pr, fr, ep0, ea0, x, bp, ba, vp, va)
  do j = dcp%js, dcp%je
    vp = 0.0_real64
    va = 0.0_real64
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      if (s%h(i,j) <= p%dd) cycle               ! 乾燥セルは流水の侵食なし
      if (s%vv(i,j) <= 0.0) cycle
      fr = 1.0
      if (gm%rk%map) fr = gm%rk%fr(i,j)
      if (fr <= 0.0) cycle                       ! 侵食しない(固定床・構造物)
      hh = max(s%h(i,j), p%dv)                   ! 極浅水深での τ の発散を防ぐ(流砂と同じ)
      vv2 = s%vv(i,j)**2
      rn2 = g%rn(i,j)**2
      h0 = max(s%sd(i,j), 0.0)
      ! セルの掃流砂容量(単位幅の固体流砂量。流砂量式・有効掃流力の比は calc_fluvial と同じ)。
      ! 研磨の駆動量と薄層の排出率の診断に使う
      qc = 0.0
      taus = gm%flv%taufac * rn2 * vv2 / (gm%sgrav * gm%d50 * hh**(1.0/3.0))
      if (taus > gm%tausc) then
        qc = qbs_rock(gm%f_qbform, taus, gm%tausc) * gm%flv%qbcoef
        lmax = max(lmax, qc * lcoef * dts)
      end if
      ! 剥離(超過せん断応力の比形)
      ep0 = 0.0
      if (gm%rk%kp > 0.0) then
        taub = rhow * p%gg * rn2 * vv2 / hh**(1.0/3.0)
        if (taub > gm%rk%tauc) ep0 = fr * gm%rk%kp * (taub / gm%rk%tauc - 1.0)**gm%rk%pm
      end if
      ! 研磨(床を叩く礫の量 q_b F_s(H^n) に比例。更新の頭の H で固定)
      ea0 = 0.0
      if (abr .and. qc > 0.0) ea0 = fr * gm%rk%beta * qc * rock_avail(h0, gm%rk%hsinv)
      if (ep0 <= 0.0 .and. ea0 <= 0.0) cycle
      ! 露出率の厳密積分(水理を固定した局所の常微分方程式の解)
      pr = exp(-h0 * gm%rk%hsinv)
      if (ep0 > 0.0) then
        x = ep0 * dts * gm%rk%hsinv * pr
        bp = gm%rk%hstar * ln1p_safe(x)
        ba = 0.0
        if (ea0 > 0.0) ba = (ea0 / ep0) * bp
      else
        bp = 0.0
        ba = ea0 * dts * pr
      end if
      ! 剥離は 1:1 で可動層へ(z 不変)、研磨は z を下げ細粒分は系外
      s%sd(i,j) = s%sd(i,j) + bp
      if (ba > 0.0) s%z(i,j) = s%z(i,j) - ba
      s%ri(i,j) = s%ri(i,j) + (bp + ba)
      vp = vp + real(bp, real64)
      va = va + real(ba, real64)
      bmax = max(bmax, (bp + ba) * gm%rk%hsinv)
    end do
    gm%rk%vprow(j) = gm%rk%vprow(j) + vp * real(area, real64)
    gm%rk%varow(j) = gm%rk%varow(j) + va * real(area, real64)
  end do
  !$omp end parallel do
  gm%rk%bmax = max(gm%rk%bmax, bmax)
  gm%rk%lmax = max(gm%rk%lmax, lmax)

  ! 続く calc_fluvial が近傍の sd(可動層クランプ・利用可能率)と z を読む
  call par_halo_cell(s%sd)
  if (abr) call par_halo_cell(s%z)
end subroutine


!----------------------------------------------------------------------
! 終了処理: 台帳の報告(全域の決定的総和。rank0 が表示)と私有 save(契約 5)
!----------------------------------------------------------------------
module subroutine dispose_rockinc(gm, p, g, s)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  real(real64) :: vp, va, vd
  real :: dmax(2), ddmax(1)

  call par_sum_rows(gm%rk%vprow, vp)
  call par_sum_rows(gm%rk%varow, va)
  dmax(1) = gm%rk%bmax
  dmax(2) = gm%rk%lmax
  call par_allreduce_max(dmax)
  if (gm%rk%fl) then
    call par_info("geomorph: rock incision: plucked " // fmt_e(real(vp)) &
                  // " m3 (bulk, into the mobile layer sd), abraded " // fmt_e(real(va)) &
                  // " m3 (bulk, exported as fines)")
    call par_info("geomorph: rock incision: max increment per update / H* = " // fmt_e(dmax(1)) &
                  // ", max thin-layer drainage rate x dts = " // fmt_e(dmax(2)))
    if (dmax(2) > 0.5) then
      call par_info("geomorph: note: thin-layer drainage rate x dts exceeds 0.5; reduce dt_geomorph " &
                    // "or morfac if the cover dynamics must not depend on the update interval")
    end if
  end if
  ! 土石流の項の台帳(判定は namelist 由来で全ランク同一 = collective 安全)
  if (gm%rk%db) then
    call par_sum_rows(gm%rk%vdrow, vd)
    ddmax(1) = gm%rk%bdmax
    call par_allreduce_max(ddmax)
    call par_info("geomorph: rock erosion by debris flows: eroded " // fmt_e(real(vd)) &
                  // " m3 (bulk, into the mobile layer sd)")
    call par_info("geomorph: rock erosion by debris flows: max increment per update / H* = " &
                  // fmt_e(ddmax(1)))
  end if
  if (p%f_state_save > 0) call save_rockinc(gm, p, g, s)
end subroutine


!----------------------------------------------------------------------
! 被覆の利用可能率 f = 1 − exp(−h·hsinv)(h <= 0 で 0。小さい引数は級数で評価して
! 桁落ちを避ける。calc_fluvial の供給側と研磨項が使う)
!----------------------------------------------------------------------
module pure function rock_avail(h, hsinv) result(f)
  real, intent(in) :: h, hsinv
  real :: f
  real :: x
  x = h * hsinv
  if (x <= 0.0) then
    f = 0.0
  else if (x < xsmall) then
    ! x − x²/2 + x³/6 − … の 6 次まで(打ち切り誤差は相対 x⁶/5040 < 2e-16)
    f = x * (1.0 - x / 2.0 * (1.0 - x / 3.0 * (1.0 - x / 4.0 * (1.0 - x / 5.0 * (1.0 - x / 6.0)))))
  else
    f = 1.0 - exp(-x)
  end if
end function


!----------------------------------------------------------------------
! 露出率を厳密に積分した 1 更新の岩盤の侵食厚(土石流の項。§89.18)
!   B = H* ln(1 + (E dts/H*) e^{−h/H*})(edt = E dts。calc_rockinc の剥離の伝播子と同じ形。
!   e^{H/H*} が時間に比例して増える自己被覆の厳密解で、更新間隔の分割によらない)
!----------------------------------------------------------------------
module pure function rock_cover_inc(edt, h, hstar, hsinv) result(b)
  real, intent(in) :: edt, h, hstar, hsinv
  real :: b
  b = hstar * ln1p_safe(edt * hsinv * exp(-max(h, 0.0) * hsinv))
end function


!----------------------------------------------------------------------
! 分布ファイル(全域の行列)を rank0 が読み、帯±ハロへ配る(方式 2。値の検査は
! 呼び出し側。fn_rock・fn_uplift・fn_wthr)。f_dissol の read_solmap と同じ経路
!----------------------------------------------------------------------
module subroutine read_cellmap(p, g, fn, a)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  character(len=*), intent(in) :: fn
  real, intent(inout) :: a(dcp%ish:, dcp%jsh:)
  real, allocatable :: wk(:,:)
  real :: dum(1,1)
  character(:), allocatable :: fname

  fname = trim(p%dir_data) // "/" // trim(fn)
  call par_info(" reading " // fname)
  if (is_root) then
    allocate(wk(1:g%nx, 1:g%ny), source = 0.0)
    call fileio_read_matrix(fname, g%nx, g%ny, wk, p%f_input_mode)
    call par_scatter_cell(wk, a)
  else
    call par_scatter_cell(dum, a)
  end if
end subroutine


!----------------------------------------------------------------------
! ln(1 + x)(x >= 0。小さい x は級数で評価して増分の桁落ちを避ける)
!----------------------------------------------------------------------
pure function ln1p_safe(x) result(f)
  real, intent(in) :: x
  real :: f
  real :: y, y2
  if (x < xsmall) then
    ! ln(1 + x) = 2 artanh(y)、y = x/(2 + x) の級数(y <= 0.005 で y⁷ までの打ち切り誤差は
    ! 相対 1e-19 以下。1 + x の丸めに頼らないので -Ofast の再結合でも崩れない)
    y = x / (2.0 + x)
    y2 = y * y
    f = 2.0 * y * (1.0 + y2 * (1.0 / 3.0 + y2 * (0.2 + y2 / 7.0)))
  else
    f = log(1.0 + x)
  end if
end function


!----------------------------------------------------------------------
! 無次元掃流砂量(m_geomorph_fluvial の qbs_form・ループ 1 の式と同じ。
! 1: 芦田・道上、2: MPM。研磨の駆動量と薄層の排出率の診断に使う)
!----------------------------------------------------------------------
pure function qbs_rock(form, taus, tsc) result(qbs)
  integer, intent(in) :: form
  real, intent(in) :: taus, tsc
  real :: qbs
  if (form == 1) then
    qbs = 17.0 * taus**1.5 * (1.0 - tsc / taus) * (1.0 - sqrt(tsc / taus))
  else
    qbs = 8.0 * (taus - tsc)**1.5
  end if
end function


! 台帳の表示用(rtoa は小数 5 桁なので小さい体積が 0 に見える)
pure function fmt_e(r) result(str)
  real, intent(in) :: r
  character(:), allocatable :: str
  character(len=32) :: buf
  write(buf, '(es16.8)') r
  str = trim(adjustl(buf))
end function


!----------------------------------------------------------------------
! 内部状態の保存・復元(モデル私有ファイル geomorph_rockinc.dat。契約5。§7・§83)
!   累積下刻 s%ri の 1 面(書き並びは restore と同時に更新すること)。台帳の行部分和は
!   ラン単位の量で保存しない
!----------------------------------------------------------------------
subroutine save_rockinc(gm, p, g, s)
  type(t_geomorph), intent(in) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer :: un
  if (g%initialized .or. gm%initialized) continue  ! 引数未使用の警告を抑制
  if (is_root) then
    call sysdep_mkdir(p%dir_save)
    open(newunit=un, file=trim(p%dir_save)//'/geomorph_rockinc.dat', form='unformatted', &
         status='replace')
  end if
  call restart_write_cell(un, s%ri)
  if (is_root) close(un)
end subroutine


subroutine restore_rockinc(gm, p, g, s)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  character(:), allocatable :: fname
  logical :: found
  integer :: un
  if (g%initialized .or. gm%initialized) continue  ! 引数未使用の警告を抑制

  fname = trim(p%dir_save)//'/geomorph_rockinc.dat'
  inquire(file=fname, exist=found)
  if (.not. found) then
    call par_stop("geomorph: rock incision state file not found (was f_rockinc enabled when saving): " &
                  // fname)
  end if
  if (is_root) open(newunit=un, file=fname, form='unformatted', status='old')
  call restart_read_cell(un, s%ri)
  if (is_root) close(un)
end subroutine

end submodule
