!======================================================================
! m_geomorph の submodule: 乾式斜面侵食(f_splash。無流水の雨滴・
! サブグリッドリル侵食。developer.md §48)
!
!   表面流も地下水も存在しない高透水斜面(バッドランド・火砕丘の
!   海食崖など)で、雨滴の衝突とサブグリッドスケールのリル・転動
!   (DEM に表現されない微地形の集水)が谷を刻む過程の
!   パラメータ化。凹地形(谷)で侵食効率が増大する正のフィードバックが
!   核心で、「移流(表面流)なしの谷形成」を表す。
!
!   浸食レート(m/s。固体体積。P = 地表到達降雨強度 s%pre [m/s]):
!     E = P・[ spl_kr・(1 + spl_ca・κ) + spl_kt・(1 + spl_cb・κ)・S^spl_h ]
!       κ = max(∇²z, 0): 凹(谷)で正の曲率 (1/m)。5点ラプラシアン
!       S = |∇z|: 勾配の大きさ(中央差分)
!       第1項: 雨滴(スプラッシュ)侵食。S→0 の台地上でも生じる(加算)
!       第2項: サブグリッドリル・転動の集中。S→0 で消える(乗算構造)
!   適用範囲: 陸の乾燥セル(h <= dd)のみ = f_wash(湿潤セル)と相補で
!   二重計上しない。河道セル(rw > 0)は対象外(wash と同じ意味論)。
!   海セルの z は勾配・曲率の近傍としては読む(海食崖の縁がまさに対象)。
!
!   剥離土砂は**系外排出**(開いた系): hs に注入せず(無流水なので
!   移流できない)、体積を台帳 gm%spl%vout に積んで dispose で報告する。
!   z と sd は共動更新(帯水層底 z − sd 不変)+ gwflow 容量引き渡しは
!   wash と同一規約。sd=0 で岩盤露出・停止(風化 f_wthr と収支が閉じる)。
!
!   曲率の相関長 ℓ(spl_lc > 0。§48.3): κ を格子の 5 点ラプラシアンで取ると
!   最短波長(2Δ)が最速成長し(Smith & Bretherton の無限波数問題)、谷間隔と
!   V 字谷底の κ(∝ 1/Δ)が格子幅に張り付く。ℓ > 0 では z を標準偏差 ℓ の
!   ガウス核(5 点核 w = 1/8 の反復。各方向の分散 2wΔ² × パス数)で平滑化した zs から
!   κ を取る: 成長率 σ(k) = Da k² e^{−ℓ²k²/2} が有限波数 k* = √2/ℓ で極大を
!   持ち、谷間隔 λ* = 2πℓ/√2 ≈ 4.4 ℓ が ℓ で決まる物理量になり、Δ を細かく
!   しても収束する(拡散項は要らない。クリープは力学的モデルでないため併用しない)。
!   勾配 S は生の z から取る(位置依存の侵食率そのもの)。
!   侵食基準面(spl_zbase): 崖下が海なら海面以下は削らない(開いた系の
!   基準面。sd による岩盤露出と独立に与える)。
!
!   2パス構造(MPI 規約): eval_splash が時刻 n の z(近傍参照)から
!   侵食深 gm%spl%fx を評価し(debris の適用より前に呼ぶ=全プロセスが
!   時刻 n の z を見る)、apply_splash が局所適用する(debris の後)。
!   これにより帯界面でランク数に依存しない。
!
!   積み残し(§48。Phase 2: 風向依存の雨滴項 Φ_A(θ_wind)、
!   Phase 3: 容量式の堆積 D = max(0, ΣQs − Qc)/δ²(D8 経路))
!======================================================================
submodule(m_geomorph) m_geomorph_splash
  use m_parallel, only : par_info, par_stop, dcp, par_halo_cell
  implicit none

contains

!----------------------------------------------------------------------
! 乾式斜面侵食の初期化(検証・係数コピー・評価配列の確保)
!----------------------------------------------------------------------
module subroutine init_splash(gm, g, list)
  type(t_geomorph), intent(inout) :: gm
  type(t_geoinfo), intent(in) :: g
  type(t_list_geomorph), intent(in) :: list
  real :: kr, kt                       ! 既定適用後の有効値(§62)
  real :: dmin
  character(len=256) :: msg

  ! どちらも未指定なら両方に既定(経験係数。校正前提。§62)。片方だけ指定なら
  ! 他方の 0 は「その項なし」の明示として尊重する
  kr = list%spl_kr
  kt = list%spl_kt
  if (kr < 0.0) call par_stop("list_geomorph: spl_kr must be >= 0")
  if (kt < 0.0) call par_stop("list_geomorph: spl_kt must be >= 0")
  if (kr == 0.0 .and. kt == 0.0) then
    kr = gm_param("spl_kr", kr, 0.0005, "")
    kt = gm_param("spl_kt", kt, 0.05, "")
  end if
  if (list%spl_ca < 0.0) call par_stop("list_geomorph: spl_ca must be >= 0")
  if (list%spl_cb < 0.0) call par_stop("list_geomorph: spl_cb must be >= 0")
  if (list%spl_h <= 0.0) call par_stop("list_geomorph: spl_h must be > 0")
  if (list%spl_dzmax < 0.0) call par_stop("list_geomorph: spl_dzmax must be >= 0")

  gm%skr = kr
  gm%sca = list%spl_ca
  gm%skt = kt
  gm%scb = list%spl_cb
  gm%shexp = list%spl_h
  gm%sdzmax = list%spl_dzmax
  if (list%spl_lc < 0.0) call par_stop("list_geomorph: spl_lc must be >= 0")
  gm%slc = list%spl_lc
  gm%szbase = list%spl_zbase
  if (list%spl_sgrad < 0 .or. list%spl_sgrad > 1) call par_stop("list_geomorph: spl_sgrad must be 0 or 1")
  gm%ssgrad = list%spl_sgrad

  if (.not. allocated(gm%spl%fx)) then
    allocate(gm%spl%fx(dcp%ish:dcp%ieh, dcp%js:dcp%je), source = 0.0)
  end if
  ! 曲率の相関長: パス数 N = 4(ℓ/Δmin)²(5 点核 1 パスの各方向の分散は
  ! 2wΔ²。w = ℓ²/(2NΔ²) で N パス後の分散が両方向とも ℓ² になる。Δx = Δy
  ! なら w = 1/8)。核の伝達関数 1 − 2wx(1−cos kxΔx) − 2wy(1−cos kyΔy) が
  ! 市松モード(格子の角)で非負であるには wx + wy ≤ 1/4 が必要(w = 1/4 の
  ! 中心重み 0 の核は市松を符号反転で保存し、平滑化が市松を消さない —
  ! 実検出 2026-10-19)。ℓ < Δ/2 は N = 1・w < 1/8 の弱い平滑化になる
  if (gm%slc > 0.0) then
    dmin = min(g%dx, g%dy)
    gm%spl%nsm = max(1, nint(4.0 * (gm%slc / dmin)**2))
    gm%spl%wsx = min(0.125, gm%slc**2 / (2.0 * gm%spl%nsm * g%dx**2))
    gm%spl%wsy = min(0.125, gm%slc**2 / (2.0 * gm%spl%nsm * g%dy**2))
    write(msg, '(a,es10.3,a,i0,a)') "geomorph: splash curvature length spl_lc = ", gm%slc, &
                                   " m (", gm%spl%nsm, " smoothing passes)"
    call par_info(trim(msg))
    if (.not. allocated(gm%spl%zs)) then
      allocate(gm%spl%zs(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
      allocate(gm%spl%zt(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
    end if
  end if
end subroutine


!----------------------------------------------------------------------
! z の平滑化(spl_lc > 0): 5 点核(自セル 1−2wx−2wy、x 近傍 wx、y 近傍 wy)を
!   nsm 回反復し gm%spl%zs に置く。無効な近傍(範囲外・領域外 x=0)は自セル値
!   で鏡像(κ の評価と同じ規約)、海セルの z は実地形として読む。
!   各パスの後に zs のハロを交換する(パス数は namelist 由来の静的量で
!   全ランク同一 = collective 安全)
!----------------------------------------------------------------------
subroutine smooth_z(gm, g, s)
  type(t_geomorph), intent(inout) :: gm
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer :: i, j, n
  real :: zc, ze, zw, zn, zsn, wx, wy, w0

  wx = gm%spl%wsx
  wy = gm%spl%wsy
  w0 = 1.0 - 2.0 * (wx + wy)
  gm%spl%zs(:, dcp%jsh:dcp%jeh) = s%z(:, dcp%jsh:dcp%jeh)
  do n = 1, gm%spl%nsm
    !$omp parallel do schedule(static) private(i, j, zc, ze, zw, zn, zsn)
    do j = dcp%js, dcp%je
      gm%spl%zt(:, j) = gm%spl%zs(:, j)
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0) cycle
        zc = gm%spl%zs(i,j)
        ze = zc; zw = zc; zn = zc; zsn = zc
        if (i < g%nx) then
          if (g%x(i+1,j) > 0) ze = gm%spl%zs(i+1,j)
        end if
        if (i > 1) then
          if (g%x(i-1,j) > 0) zw = gm%spl%zs(i-1,j)
        end if
        if (g%x(i,j+1) > 0) zn = gm%spl%zs(i,j+1)
        if (g%x(i,j-1) > 0) zsn = gm%spl%zs(i,j-1)
        gm%spl%zt(i,j) = w0 * zc + wx * (ze + zw) + wy * (zn + zsn)
      end do
    end do
    !$omp end parallel do
    gm%spl%zs(:, dcp%js:dcp%je) = gm%spl%zt(:, dcp%js:dcp%je)
    call par_halo_cell(gm%spl%zs)
  end do
end subroutine


!----------------------------------------------------------------------
! 侵食深の評価(時刻 n の z から。書き込みは gm%spl%fx のみ)
!   帯の全セルの fx を 0 を含めて必ず上書きする(gm%wrk%q と同じ契約)。
!   近傍 z の読み: x 方向は配列範囲と x>0 を検査(範囲外・領域外は
!   自セル値で鏡像=寄与ゼロ)、y 方向はハロ行(常に確保済み)。
!   海セル(sw>0)の z は実地形として読む(海食崖の縁の勾配が対象)
!----------------------------------------------------------------------
module subroutine eval_splash(gm, p, g, s, dts)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  real, intent(in) :: dts       ! 実効時間刻み(morfac 込み)
  integer :: i, j, nclip
  real :: zc, ze, zw, zn, zs, kap, sx, sy, ss, er, fx
  real :: kc, ke, kw, kn, ks
  real :: dxi, dyi, dx2i, dy2i, ddi
  real :: zn8(8), dd8(8)
  integer :: k, in, jn
  logical :: smooth

  dxi = 0.5 / g%dx
  dyi = 0.5 / g%dy
  dx2i = 1.0 / (g%dx * g%dx)
  dy2i = 1.0 / (g%dy * g%dy)
  ddi = 1.0 / sqrt(g%dx * g%dx + g%dy * g%dy)
  dd8 = [ddi, 1.0 / g%dy, ddi, 1.0 / g%dx, 1.0 / g%dx, ddi, 1.0 / g%dy, ddi]
  nclip = 0
  smooth = (gm%spl%nsm > 0)
  if (smooth) call smooth_z(gm, g, s)

  !$omp parallel do schedule(static) reduction(+:nclip) &
  !$omp   private(i, j, zc, ze, zw, zn, zs, kap, sx, sy, ss, er, fx, kc, ke, kw, kn, ks, k, in, jn, zn8)
  do j = dcp%js, dcp%je
    gm%spl%fx(:,j) = 0.0
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      if (g%rw(i,j) > 0) cycle          ! 河道セルは対象外(wash と同じ意味論)
      if (s%h(i,j) > p%dd) cycle        ! 湿潤セルは f_wash の管轄(相補)
      if (s%pre(i,j) <= 0.0) cycle      ! 侵食は降雨イベント駆動
      if (s%sd(i,j) <= 0.0) cycle       ! 岩盤露出セルは停止
      zc = s%z(i,j)
      if (gm%szbase > -9000.0) then
        if (zc <= gm%szbase) cycle      ! 侵食基準面(海面)以下は削らない
      end if
      ! 近傍 z(範囲外・領域外は鏡像 = 寄与ゼロ)
      ze = zc; zw = zc; zn = zc; zs = zc
      if (i < g%nx) then
        if (g%x(i+1,j) > 0) ze = s%z(i+1,j)
      end if
      if (i > 1) then
        if (g%x(i-1,j) > 0) zw = s%z(i-1,j)
      end if
      if (g%x(i,j+1) > 0) zn = s%z(i,j+1)
      if (g%x(i,j-1) > 0) zs = s%z(i,j-1)
      ! 曲率(凹で正。spl_lc > 0 なら平滑化した zs から、同じ鏡像規約で)と勾配
      if (smooth) then
        kc = gm%spl%zs(i,j)
        ke = kc; kw = kc; kn = kc; ks = kc
        if (i < g%nx) then
          if (g%x(i+1,j) > 0) ke = gm%spl%zs(i+1,j)
        end if
        if (i > 1) then
          if (g%x(i-1,j) > 0) kw = gm%spl%zs(i-1,j)
        end if
        if (g%x(i,j+1) > 0) kn = gm%spl%zs(i,j+1)
        if (g%x(i,j-1) > 0) ks = gm%spl%zs(i,j-1)
        kap = max((ke + kw - 2.0 * kc) * dx2i + (kn + ks - 2.0 * kc) * dy2i, 0.0)
      else
        kap = max((ze + zw - 2.0 * zc) * dx2i + (zn + zs - 2.0 * zc) * dy2i, 0.0)
      end if
      if (gm%ssgrad == 1) then
        ! 最急降下(既定): 8 近傍への下り勾配 (zc − zn)/距離 の最大(無効な近傍・
        ! 上り = 0)。中央差分(spl_sgrad = 0。旧挙動)は稜線の頂で左右が打ち消して
        ! S ≈ 0 になり 1 セル幅の尾根が削れない(§48.4)。最急降下なら頂のセルも
        ! 両面の勾配で削れ、市松(高いセルだけ S > 0)も減衰する
        ss = 0.0
        do k = 1, 8
          in = i + din(k)
          jn = j + djn(k)
          if (in < 1 .or. in > g%nx) cycle
          if (g%x(in,jn) <= 0) cycle
          ss = max(ss, (zc - s%z(in,jn)) * dd8(k))
        end do
      else
        sx = (ze - zw) * dxi
        sy = (zn - zs) * dyi
        ss = sqrt(sx * sx + sy * sy)
      end if
      ! 浸食レート(固体体積 m/s)
      er = gm%skr * (1.0 + gm%sca * kap)
      if (gm%skt > 0.0 .and. ss > 0.0) then
        er = er + gm%skt * (1.0 + gm%scb * kap) * ss**gm%shexp
      end if
      er = er * s%pre(i,j)
      if (er <= 0.0) cycle
      ! 河床変化量へ換算し、可動層(sd)と侵食上限でクランプ
      fx = er * dts * gm%poroi
      if (gm%sdzmax > 0.0 .and. fx > gm%sdzmax) then
        fx = gm%sdzmax
        nclip = nclip + 1
      end if
      fx = min(fx, s%sd(i,j))
      if (gm%szbase > -9000.0) fx = min(fx, zc - gm%szbase)
      gm%spl%fx(i,j) = fx
    end do
  end do
  !$omp end parallel do
  gm%spl%nclip = gm%spl%nclip + nclip
end subroutine


!----------------------------------------------------------------------
! 侵食の適用(局所。z・sd の共動更新+系外排出台帳+gwflow 引き渡し)
!   排出体積の集計は行別部分和 → 逐次総和(スレッド数によらず決定的)
!----------------------------------------------------------------------
module subroutine apply_splash(gm, g, s)
  type(t_geomorph), intent(inout) :: gm
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: i, j
  real :: fx, cap, fxg
  real :: rsum(dcp%js:dcp%je)

  !$omp parallel do schedule(static) private(i, j, fx, cap, fxg)
  do j = dcp%js, dcp%je
    rsum(j) = 0.0
    do i = g%wx(1,j), g%wx(2,j)
      fx = gm%spl%fx(i,j)
      if (fx <= 0.0) cycle
      ! 共動更新(z と sd が同じ Δz で動く → 帯水層底 z − sd 不変)
      s%z(i,j) = s%z(i,j) - fx
      s%sd(i,j) = s%sd(i,j) - fx
      ! 河床の細粒分の帳簿(§84.10)との併用: 粗粒として扱い sf <= sd だけ保つ
      if (allocated(s%sf)) s%sf(i,j) = min(s%sf(i,j), s%sd(i,j))
      rsum(j) = rsum(j) + fx
      ! 浸食で地下水容量が現在の貯留を下回ったら、超過分を地表水へ渡す
      ! (calc_wash と同じ整合)
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

  ! 系外排出の台帳(固体体積 = 河床変化 × (1−λ) × セル面積)
  do j = dcp%js, dcp%je
    gm%spl%vout = gm%spl%vout + rsum(j) * g%dx * g%dy / gm%poroi
  end do
end subroutine

end submodule
