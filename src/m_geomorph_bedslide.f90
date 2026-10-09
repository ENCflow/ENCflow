!======================================================================
! m_geomorph の submodule: 動く底層(f_bedslide。地滑り土塊の底層すべり)
!   設計の正本は docs/landslide_tsunami_plan.md(§4 定式・§4.6 離散化)。
!
!   【状態と簿記】s%hb = 動いている底層の厚さ(m。かさ体積 = 間隙込み)。
!   s%z と s%sd の内数で常に土層の最上部にある。hb が Δ だけセル間を
!   動けば送り手の z・sd が Δ 減り、受け手の z・sd が Δ 増える(共動更新。
!   岩盤面 z − sd は不変)。水柱 h は変えない(geomorph の契約)ので、
!   z の上下がそのまま水面 e = z + h の変位になる = 移動海底の津波源。
!   発火(fn_bsinit)は hb = min(D, sd) と「可動化」するだけで z・sd・h・e は
!   変えない(土塊は既に z の中にある)。停止は bs_vstop 未満のセルの hb を
!   0 にするだけ(質量は既に z・sd にある。不可逆)。
!
!   【定式(慣性なし Voellmy。f_bsres=1)】
!     駆動水頭  Φ = z + r·h(r = ρw/ρs。乾燥で Φ=z、平水面下で ∇Φ=(1−r)∇z)
!     セル勾配  S_c = Φ の 8 近傍最急降下勾配
!     浮力係数  b = 1 − r·w、浸水率 w = min(1, h/hb)
!     速度      S_c − μb ≤ 0 : V = 0(降伏 = 停止)
!               0 < sy < ε_S : V = √(ξ hb ε_S)·sy/ε_S(線形化枝)
!               sy ≥ ε_S     : V = √(ξ hb sy)
!     配分      下り方向(ΔΦ_k > 0)のエッジへ q_k = hb·V·(ΔΦ_k/dist_k)·wl_k / S_c
!               (= ENC 本体の「射影速度 × 通過幅 l8」と同じ配分。8 近傍・
!                bs_diagratio。速度はセル勾配で一度だけ決め、斜めエッジの
!                勾配低下が降伏に効く歪みを避ける — §4.3)。総流出
!               Q_c = hb·V·Σ_k (ΔΦ_k/dist_k)·wl_k / S_c は、一様勾配では
!               格子沿いで hb·V·dy、45° で hb·V·dx に等しく、どちらも
!               質量流束ベクトル hb·V·û を与える(斜めの 1 ホップは
!               √2 倍の距離を運ぶので「面通過流量の和」とは一致しない —
!               検出器 test/bedslide 構成2 で実検出。投影幅 W_c を掛ける
!               形は 45° で √2 倍の過大輸送になる)
!     ドナー律速 1 サブサイクルの総流出 ≤ hb·A(係数 f = min(1, hb·A/(dt·Q_c))
!               を送り手の全エッジに一様に掛ける → hb ≥ 0 が構造的に成立)
!
!   【段階2: 混合体からの引き渡し(プランジ。bs_hplunge > 0 かつ f_debris=1)】
!   滞水深 ≥ bs_hplunge のセルで(滞水深は f_bsplunge=0: 現在の h、
!   1: 静水深 = 初期水面 eref − 現在の底面 z。突入で一時的に離水した汀線帯
!   でも引き渡す。初期に乾いたセルは対象外)、水柱に混ざる固体 hs をかさ体積
!   Δ = hs/(1−λ) に換算して hb・z・sd へ移す(hs → 0)。表面 z+h+hs は
!   固体分だけ保存され、間隙分は f_dbwet=1 なら水柱から埋没(h −= λ·s_b·Δ。
!   残量でクランプ)、f_dbwet=0 なら表面が間隙分だけ上がる(乾燥セルの
!   全量繰り入れと同じ規約)。混合体の運動量は失われる(底層は慣性なし)。
!   セル局所(近傍参照なし)。陸上を混合体で流下した土石流が滞水域に
!   入った瞬間に底層へ変わり、水中を走る — landslide_tsunami_plan.md §4.7
!
!   【1 tick の処理】
!     (0') プランジ引き渡し(自帯。上記)
!     (0) hb の全域最大が 0 なら return(allreduce。全ランク同一)
!     (1) z・h・hb のハロ交換(他プロセスの帯内 z 更新・swflow の h 更新・
!         前 tick の停止を配布。§28.2 の実バグの教訓)
!     (2) サブサイクル: パス0(セル量 V・Q_c・Σ重み。帯±1 行)→
!         安定条件(V_max・hb·dV/dS の allreduce_max → dt_sub。決定的)→
!         パスB(エッジ流量。帯界面は je+1 行の書き手が冗長計算)→
!         パスC(発散。hb・z・sd の共動更新。自帯のみ)→ hb・z のハロ交換
!     (3) 停止: パス0 を再評価し V < bs_vstop が bs_tstop 秒(= bs_nstop tick)
!         続いたセルの hb を 0 に(一時的な失速 — 突入時の水の押し出しで
!         汀線帯が離水し、水の盛り上がりが逆勾配を作る数秒〜十数秒 — で
!         誤固定しない。bs_tstop=0 なら即時 = lavaflow の固化と同じ閉じ)
!     e の回復と sd のハロ交換は m_geomorph_calc の末尾が行う
!
!   MPI 規約(developer.md §11): 更新は自帯 js..je のみ、エッジは
!   書き手一意(k=1..4 が所有成分)、collective の判定は全ランク同一。
!   エッジ作業領域は本プロセス私有(gm%bsl%q)。共有の gm%wrk%q は fluvial が
!   開境界面の k>=5 スロットを書くため、古い値を拾う危険がある
!======================================================================
submodule(m_geomorph) m_geomorph_bedslide
  use m_parallel, only : par_info, par_warn, par_stop, dcp, is_root, par_halo_cell, &
                         par_allreduce_max, par_allreduce_sumr, par_gather_to, &
                         par_scatter_cell
  use m_fileio, only : fileio_read_matrix, fileio_write_rle, fileio_read_rle
  use m_sysdep_util, only : sysdep_mkdir
  use m_util, only : itoa, rtoa
  implicit none

  real, parameter :: bs_rhow = 1000.0     ! 水の密度 (kg/m3。浮力比 r = ρw/ρs)
  ! 未指定(0)時の既定値(§61.9。「崩壊深分布だけを与えて回す」ための無難な値。
  ! examples/landslide_tsunami・test/bedslide の校正値と同じ。init が採用値を表示)
  real, parameter :: bs_rho_def = 2000.0  ! 飽和土塊・岩屑のかさ密度 → r = 0.5
  real, parameter :: bs_mu_def = 0.15     ! 慣性なし Voellmy の μ
  real, parameter :: bs_xi_def = 500.0    ! 同 ξ (m/s²)
  real, parameter :: bs_vstop_def = 0.05  ! 停止判定の速度閾値 (m/s。db_vstop の既定と同じ)
  real, parameter :: bs_hbmin = 1.0e-4    ! 可動とみなす底層厚の下限 (m)。これ未満は V=0 として
                                          ! tick 末尾の停止で z に固定する(配分の裾が
                                          ! 非正規化数まで痩せて 0 除算になるのを防ぐ数値的閉じ。
                                          ! 0.1 mm の裾の固定は結果に影響しない)

contains

!----------------------------------------------------------------------
! 動く底層の初期化(検証・幾何・状態確保・発火与件の読み込み・restore)
!----------------------------------------------------------------------
module subroutine init_bedslide(gm, p, g, s, list)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_list_geomorph), intent(in) :: list
  integer :: k, i, j
  real :: lpx, lpy, ldx, ldy, dr
  real :: rho, mu, xi, vstop           ! 既定値を反映した有効値(§61.9)
  real, allocatable :: wk(:,:)

  ! --- 検証 ---
  if (gm%morfac /= 1.0) then
    call par_stop("list_geomorph: f_bedslide requires morfac=1 (event-scale computation)")
  end if
  if (list%bs_hplunge < 0.0) call par_stop("list_geomorph: bs_hplunge must be >= 0")
  if (list%bs_hplunge > 0.0 .and. gm%f_debris <= 0) then
    call par_stop("list_geomorph: bs_hplunge > 0(混合体からの引き渡し)requires f_debris=1")
  end if
  if (len_trim(list%fn_bsinit) == 0 .and. list%bs_hplunge <= 0.0) then
    call par_stop("list_geomorph: f_bedslide=1 requires fn_bsinit(崩壊深分布 = 発火与件)" &
                  // " or bs_hplunge > 0(混合体からの引き渡し)")
  end if
  ! 物性・校正値の既定(§61.9): 0(未指定)なら「とりあえず崩壊深分布だけで
  ! 回す」ための無難な値を入れ、採用値を明示表示する(黙って使わない)。
  ! 負値や 1000 以下の密度など明示された不正値は従来どおり停止
  rho = gm_param("bs_rho", list%bs_rho, bs_rho_def, " kg/m3")
  mu = gm_param("bs_mu", list%bs_mu, bs_mu_def, "")
  xi = gm_param("bs_xi", list%bs_xi, bs_xi_def, " m/s2")
  vstop = gm_param("bs_vstop", list%bs_vstop, bs_vstop_def, " m/s")
  if (rho <= bs_rhow) then
    call par_stop("list_geomorph: f_bedslide requires bs_rho > 1000 kg/m3" &
                  // "(土塊のかさ密度は水より大きい)")
  end if
  select case (list%f_bsres)
    case (1)
      if (mu <= 0.0) call par_stop("list_geomorph: f_bsres=1 requires bs_mu > 0")
      if (xi <= 0.0) call par_stop("list_geomorph: f_bsres=1 requires bs_xi > 0 (m/s2)")
    case (2)
      call par_stop("list_geomorph: f_bsres=2 (Bingham) is reserved and not implemented yet" &
                    // " — landslide_tsunami_plan.md sec.4.3")
    case default
      call par_stop("list_geomorph: f_bsres must be 1(Voellmy) or 2(Bingham, reserved)")
  end select
  if (vstop <= 0.0) call par_stop("list_geomorph: f_bedslide requires bs_vstop > 0 (m/s)")
  if (list%bs_eps_s <= 0.0) call par_stop("list_geomorph: bs_eps_s must be > 0")
  if (list%bs_diagratio < 0.0 .or. list%bs_diagratio > 1.0) then
    call par_stop("list_geomorph: bs_diagratio must be in [0,1]")
  end if
  if (list%bs_cfl <= 0.0 .or. list%bs_cfl > 1.0) call par_stop("list_geomorph: bs_cfl must be in (0,1]")
  if (list%bs_nsubmax < 1) call par_stop("list_geomorph: bs_nsubmax must be >= 1")

  gm%bs_r = bs_rhow / rho
  gm%f_bsres = list%f_bsres
  gm%bs_mu = mu
  gm%bs_xi = xi
  gm%bs_vstop = vstop
  gm%bs_eps_s = list%bs_eps_s
  gm%bs_cfl = list%bs_cfl
  gm%bs_nsubmax = list%bs_nsubmax
  gm%bs_reltime = list%bs_reltime
  gm%bs_hplunge = list%bs_hplunge
  if (list%bs_tstop < 0.0) call par_stop("list_geomorph: bs_tstop must be >= 0")
  if (list%f_bsplunge /= 0 .and. list%f_bsplunge /= 1) then
    call par_stop("list_geomorph: f_bsplunge must be 0(current depth h) or 1(still-water depth)")
  end if
  gm%f_bsplunge = list%f_bsplunge
  if (list%f_bsvplunge /= 0 .and. list%f_bsvplunge /= 1) then
    call par_stop("list_geomorph: f_bsvplunge must be 0(immediate) or 1(after deceleration)")
  end if
  gm%f_bsvplunge = list%f_bsvplunge
  gm%bs_nstop = max(1, nint(list%bs_tstop / (p%dt * gm%idt_geomorph)))

  ! --- 8近傍の幾何(m_gwflow_lateral / init_fluvial と同一の配分則) ---
  dr = sqrt(g%dx**2 + g%dy**2)
  if (g%dy > g%dx) then
    lpy = 1 - (g%dx / g%dy)**2 * list%bs_diagratio
    ldy = list%bs_diagratio / 2 * (g%dx / g%dy)**2
    lpx = 1 - list%bs_diagratio
    ldx = list%bs_diagratio / 2
  else
    lpy = 1 - list%bs_diagratio
    ldy = list%bs_diagratio / 2
    lpx = 1 - (g%dy / g%dx)**2 * list%bs_diagratio
    ldx = list%bs_diagratio / 2 * (g%dy / g%dx)**2
  end if
  gm%bsl%wl(1) = sqrt((ldy * g%dy)**2 + (ldx * g%dx)**2)
  gm%bsl%wl(2) = lpx * g%dx
  gm%bsl%wl(3) = gm%bsl%wl(1)
  gm%bsl%wl(4) = lpy * g%dy
  gm%bsl%wl(5) = gm%bsl%wl(4)
  gm%bsl%wl(6) = gm%bsl%wl(3)
  gm%bsl%wl(7) = gm%bsl%wl(2)
  gm%bsl%wl(8) = gm%bsl%wl(1)
  do k = 1, 8
    gm%bsl%rdr(k) = 1.0 / sqrt((din(k) * g%dx)**2 + (djn(k) * g%dy)**2)
  end do
  gm%bsl%area = g%dx * g%dy
  gm%bsl%rdx2 = 1.0 / g%dx**2 + 1.0 / g%dy**2
  gm%bsl%dxmin = min(g%dx, g%dy)

  ! --- 状態と作業領域(有効時のみ確保 = 無効時ゼロコスト) ---
  if (.not. allocated(s%hb)) allocate(s%hb(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  if (.not. allocated(s%vb)) allocate(s%vb(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(gm%bsl%vc(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(gm%bsl%qt(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(gm%bsl%ws(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(gm%bsl%q(1:4, 0:g%nx, dcp%jsh-1:dcp%jeh), source = 0.0)
  allocate(gm%bsl%nst(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  ! f_bsplunge=1 の基準水面 = 初期の水面 z+h(乾いたセルは -huge)。restore 時は
  ! 私有 save の値が勝つ(初期状態でなく復元状態を読んでしまわないため)
  allocate(gm%bsl%eref(1:g%nx, dcp%jsh:dcp%jeh), source = -huge(1.0))
  if (gm%f_bsplunge == 1) then
    do j = dcp%jsh, dcp%jeh
      do i = 1, g%nx
        if (s%h(i,j) > p%dd) gm%bsl%eref(i,j) = s%z(i,j) + s%h(i,j)
      end do
    end do
  end if

  ! --- 発火与件(崩壊深分布。全ランク冗長の全域読み。read_release と同じ流儀。
  !     未指定(プランジ引き渡しのみ)なら rel は未確保 = 発火なし) ---
  if (len_trim(list%fn_bsinit) > 0) then
    allocate(wk(1:g%nx, 1:g%ny), source = 0.0)
    call fileio_read_matrix(trim(p%dir_data)//"/"//trim(list%fn_bsinit), g%nx, g%ny, wk, &
                            p%f_input_mode)
    if (minval(wk) < 0.0) then
      call par_stop("list_geomorph: fn_bsinit release depth has negative values: " &
                    // trim(list%fn_bsinit))
    end if
    allocate(gm%bsl%rel(1:g%nx, dcp%js:dcp%je), source = wk(1:g%nx, dcp%js:dcp%je))
    deallocate(wk)
  end if

  ! --- restore(私有ファイル。契約5) ---
  if (p%f_state_restore > 0) call restore_bedslide(gm, p, g, s)

  call par_info("geomorph: bedslide enabled (Voellmy mu=" // rtoa(gm%bs_mu) &
                // ", xi=" // rtoa(gm%bs_xi) // ", r=rho_w/rho_s=" // rtoa(gm%bs_r) // ")")
end subroutine


!----------------------------------------------------------------------
! 発火(可動化)。時刻交差で 1 回だけ(release_debris と同じ判定 =
! リスタート後に再発火しない)。hb = min(D, sd)。z・sd・h・e は不変
!----------------------------------------------------------------------
module subroutine release_bedslide(gm, p, g, s)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: i, j
  real :: tprev, dd, vsum

  if (.not. allocated(gm%bsl%rel)) return          ! この run で発火済み
  if (gm%bs_reltime > s%t) return
  if (s%it - gm%idt_geomorph > 0) then
    tprev = p%t0 + p%dt * (s%it - gm%idt_geomorph)
    if (gm%bs_reltime <= tprev) return          ! 前回呼び出し以前に発火済み
  end if

  vsum = 0.0
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      dd = gm%bsl%rel(i,j)
      if (dd <= 0.0) cycle
      if (dd > s%sd(i,j)) then
        dd = s%sd(i,j)                          ! 可動層クランプ(dispose で報告)
        gm%bsl%nrelclip = gm%bsl%nrelclip + 1
        if (dd <= 0.0) cycle
      end if
      s%hb(i,j) = s%hb(i,j) + dd
      vsum = vsum + dd
    end do
  end do
  gm%bsl%vrel = gm%bsl%vrel + vsum * gm%bsl%area
  deallocate(gm%bsl%rel)                           ! 発火は1回だけ
  ! 帯の hb をハロへ(calc_bedslide の冒頭交換が担うのでここでは不要)
end subroutine


!----------------------------------------------------------------------
! パス0: セル量の評価(帯±1 行。近傍の Φ を読む。書き込みは bsl の
! 作業配列のみ)。vmax・dmax は安定条件用の局所最大
!----------------------------------------------------------------------
subroutine eval_cells(gm, g, s, vmax, dmax)
  type(t_geomorph), intent(inout) :: gm
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  real, intent(out) :: vmax, dmax
  integer :: i, j, k, in, jn, j1, j2, kmax
  real :: phic, phin, dphi, sl, smax, ws, hb, hw, bb, sy, vv, dvds

  j1 = max(dcp%js - 1, 1)
  j2 = min(dcp%je + 1, g%ny)
  vmax = 0.0
  dmax = 0.0
  !$omp parallel do schedule(static) reduction(max: vmax, dmax) &
  !$omp   private(i, j, k, in, jn, kmax, phic, phin, dphi, sl, smax, ws, hb, hw, bb, sy, vv, dvds)
  do j = j1, j2
    do i = g%wx(1,j), g%wx(2,j)
      gm%bsl%vc(i,j) = 0.0
      gm%bsl%qt(i,j) = 0.0
      gm%bsl%ws(i,j) = 0.0
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      hb = s%hb(i,j)
      if (hb <= bs_hbmin) cycle                 ! 薄い裾は不動(停止で固定される)
      hw = max(s%h(i,j), 0.0)
      phic = s%z(i,j) + gm%bs_r * hw
      smax = 0.0
      kmax = 0
      ws = 0.0
      do k = 1, 8
        in = i + din(k)
        jn = j + djn(k)
        if (g%x(in,jn) <= 0) cycle
        if (g%sw(in,jn) > 0) cycle
        phin = s%z(in,jn) + gm%bs_r * max(s%h(in,jn), 0.0)
        dphi = phic - phin
        if (dphi <= 0.0) cycle
        sl = dphi * gm%bsl%rdr(k)
        ws = ws + sl * gm%bsl%wl(k)
        if (sl > smax) then
          smax = sl
          kmax = k
        end if
      end do
      if (kmax == 0) cycle
      ! 浮力係数 b = 1 − r·w(浸水率 w = min(1, h/hb))
      bb = 1.0 - gm%bs_r * min(1.0, hw / hb)
      sy = smax - gm%bs_mu * bb
      if (sy <= 0.0) cycle                      ! 降伏 = 停止
      if (sy < gm%bs_eps_s) then
        dvds = sqrt(gm%bs_xi * hb / gm%bs_eps_s)
        vv = dvds * sy
      else
        vv = sqrt(gm%bs_xi * hb * sy)
        dvds = 0.5 * sqrt(gm%bs_xi * hb / sy)
      end if
      gm%bsl%vc(i,j) = vv
      gm%bsl%qt(i,j) = hb * vv * ws / smax     ! 総流出 = 配分重みの和 / セル勾配
      gm%bsl%ws(i,j) = ws
      vmax = max(vmax, vv)
      dmax = max(dmax, hb * dvds)
    end do
  end do
  !$omp end parallel do
end subroutine


!----------------------------------------------------------------------
! 1 tick の底層流動(サブサイクル)+停止
!----------------------------------------------------------------------
module subroutine calc_bedslide(gm, g, s, dtw)
  type(t_geomorph), intent(inout) :: gm
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: dtw
  integer :: i, j, k, in, jn, jt, nsub
  real :: w1(2), vmax, dmax, trem, dtsub, dlim, ainv
  real :: phic, phin, dphi, gq, fdon, dv, dd, vsum
  logical :: okc, last

  ainv = 1.0 / gm%bsl%area

  ! --- (0') 混合体からの引き渡し(プランジ。自帯。終端速度の見積りが近傍の
  !          z・h を読むため、先に z・h のハロを最新化する) ---
  if (gm%bs_hplunge > 0.0) then
    call par_halo_cell(s%z)
    call par_halo_cell(s%h)
    call plunge_cells(gm, g, s)
  end if

  ! --- (0) 動く底層があるか(全ランク同一の判定) ---
  w1(1) = 0.0
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (s%hb(i,j) > w1(1)) w1(1) = s%hb(i,j)
    end do
  end do
  w1(2) = 0.0
  call par_allreduce_max(w1)
  if (w1(1) <= 0.0) return

  ! --- (1) 入力の時刻整合(z: 他プロセスの帯内更新、h: swflow の帯内更新、
  !         hb: 前 tick の停止・帯内更新)---
  call par_halo_cell(s%z)
  call par_halo_cell(s%h)
  call par_halo_cell(s%hb)

  gm%bsl%ntick = gm%bsl%ntick + 1
  jt = min(dcp%je + 1, dcp%jeh)
  trem = dtw
  nsub = 0

  do while (trem > 0.0)
    nsub = nsub + 1
    if (nsub > gm%bs_nsubmax) then
      call par_stop("geomorph: bedslide subcycle count exceeded bs_nsubmax = " &
                    // itoa(gm%bs_nsubmax) // " (increase bs_eps_s / bs_nsubmax or reduce dt)")
    end if

    ! --- パス0 + 安定条件(決定的: 全ランク同一の dt_sub) ---
    call eval_cells(gm, g, s, vmax, dmax)
    w1(1) = vmax
    w1(2) = dmax
    call par_allreduce_max(w1)
    vmax = w1(1)
    dmax = w1(2)
    dtsub = trem
    last = .true.
    if (vmax > 0.0) then
      dlim = gm%bs_cfl * gm%bsl%dxmin / vmax
      if (dlim < dtsub) then
        dtsub = dlim
        last = .false.
      end if
    end if
    if (dmax > 0.0) then
      dlim = gm%bs_cfl * 0.5 / (dmax * gm%bsl%rdx2)
      if (dlim < dtsub) then
        dtsub = dlim
        last = .false.
      end if
    end if

    ! --- パスB: エッジ流量(書き手一意。帯界面は je+1 行が冗長計算) ---
    !$omp parallel do schedule(static) private(i, j, k, in, jn, okc, phic, phin, dphi, gq, fdon)
    do j = dcp%js, jt
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0) cycle
        okc = (g%sw(i,j) <= 0)
        phic = s%z(i,j) + gm%bs_r * max(s%h(i,j), 0.0)
        do k = 1, 4
          in = i + din(k)
          jn = j + djn(k)
          ! 状態は毎回変わるため、条件を満たさない場合も必ず 0 を代入する
          gq = 0.0
          if (okc .and. g%x(in,jn) > 0) then
            if (g%sw(in,jn) <= 0) then
              phin = s%z(in,jn) + gm%bs_r * max(s%h(in,jn), 0.0)
              dphi = phic - phin
              if (dphi > 0.0) then
                ! 送り手 = 自セル(c → n が正)
                if (gm%bsl%qt(i,j) > 0.0) then
                  ! ドナー律速(除算は 総流出 > 保有量 のときだけ = 0 除算なし)
                  fdon = 1.0
                  if (dtsub * gm%bsl%qt(i,j) > s%hb(i,j) * gm%bsl%area) then
                    fdon = s%hb(i,j) * gm%bsl%area / (dtsub * gm%bsl%qt(i,j))
                  end if
                  gq = fdon * gm%bsl%qt(i,j) * (dphi * gm%bsl%rdr(k) * gm%bsl%wl(k)) / gm%bsl%ws(i,j)
                end if
              else if (dphi < 0.0) then
                ! 送り手 = 近傍(n → c。格納は c→n 正なので負)
                if (gm%bsl%qt(in,jn) > 0.0) then
                  fdon = 1.0
                  if (dtsub * gm%bsl%qt(in,jn) > s%hb(in,jn) * gm%bsl%area) then
                    fdon = s%hb(in,jn) * gm%bsl%area / (dtsub * gm%bsl%qt(in,jn))
                  end if
                  gq = -fdon * gm%bsl%qt(in,jn) * (-dphi * gm%bsl%rdr(k) * gm%bsl%wl(k)) / gm%bsl%ws(in,jn)
                end if
              end if
            end if
          end if
          gm%bsl%q(k, i+die(k), j+dje(k)) = gq
        end do
      end do
    end do
    !$omp end parallel do

    ! --- パスC: 発散を取り hb・z・sd を共動更新(自帯のみ) ---
    !$omp parallel do schedule(static) private(i, j, k, dv, dd)
    do j = dcp%js, dcp%je
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0) cycle
        if (g%sw(i,j) > 0) cycle
        dv = 0.0
        do k = 1, 8
          dv = dv + sign_e(k) * gm%bsl%q(ke(k), i+die(k), j+dje(k))
        end do
        if (dv == 0.0) cycle
        dd = -dv * dtsub * ainv
        s%hb(i,j) = s%hb(i,j) + dd
        s%z(i,j) = s%z(i,j) + dd
        s%sd(i,j) = s%sd(i,j) + dd
      end do
    end do
    !$omp end parallel do

    call par_halo_cell(s%hb)
    call par_halo_cell(s%z)

    if (last) exit
    trem = trem - dtsub
  end do
  gm%bsl%nsubtot = gm%bsl%nsubtot + nsub
  gm%bsl%nsubpk = max(gm%bsl%nsubpk, nsub)

  ! --- (3) 停止: 更新後の場で速度を再評価し、閾値未満の hb を固定。
  !         診断の速度場 s%vb(自帯)もここで更新する(停止セルは 0) ---
  call eval_cells(gm, g, s, vmax, dmax)
  vsum = 0.0
  !$omp parallel do schedule(static) private(i, j) reduction(+: vsum)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      s%vb(i,j) = 0.0
      if (g%x(i,j) <= 0) cycle
      if (s%hb(i,j) <= 0.0) then
        gm%bsl%nst(i,j) = 0.0
        cycle
      end if
      if (gm%bsl%vc(i,j) >= gm%bs_vstop) then
        s%vb(i,j) = gm%bsl%vc(i,j)
        gm%bsl%nst(i,j) = 0.0                    ! 動いた: 低速の連続を打ち切る
        cycle
      end if
      gm%bsl%nst(i,j) = gm%bsl%nst(i,j) + 1.0
      if (gm%bsl%nst(i,j) < real(gm%bs_nstop)) cycle   ! まだ持続時間に満たない
      vsum = vsum + s%hb(i,j)
      s%hb(i,j) = 0.0
      gm%bsl%nst(i,j) = 0.0
    end do
  end do
  !$omp end parallel do
  gm%bsl%vstop = gm%bsl%vstop + vsum * gm%bsl%area
  ! 停止後の hb のハロは次 tick 冒頭の交換が配布する(この後 hb を読む者はいない)
end subroutine


!----------------------------------------------------------------------
! 混合体(hs)から底層(hb)への引き渡し(プランジ。ヘッダ参照)
!   Δ = hs·poroi(かさ体積)。hs → 0、hb・z・sd += Δ。間隙水は f_dbwet=1 の
!   ときだけ水柱から埋没(h −= λ·s_b·Δ、残量でクランプ)。e の回復は
!   m_geomorph_calc の末尾(本モジュールの契約)
!----------------------------------------------------------------------
subroutine plunge_cells(gm, g, s)
  type(t_geomorph), intent(inout) :: gm
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: i, j, k, in, jn
  real :: dd, dhw, vsum, psum1, psum2, hbq, hw, phic, phin, dphi, sl, smax, bb, sy, vb

  vsum = 0.0
  psum1 = 0.0
  psum2 = 0.0
  !$omp parallel do schedule(static) reduction(+: vsum, psum1, psum2) &
  !$omp   private(i, j, k, in, jn, dd, dhw, hbq, hw, phic, phin, dphi, sl, smax, bb, sy, vb)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      if (s%hs(i,j) <= 0.0) cycle
      if (gm%f_bsplunge == 1) then
        if (gm%bsl%eref(i,j) - s%z(i,j) < gm%bs_hplunge) cycle    ! 静水深(初期水面 − 底面)
      else
        if (s%h(i,j) < gm%bs_hplunge) cycle                    ! 現在の水深
      end if
      dd = s%hs(i,j) * gm%poroi
      ! 引き渡し後の底層の終端速度 V_b(eval_cells と同じ式。hb_eq = 既存 hb + Δ)。
      ! f_bsvplunge=1 では、混合体の速度がこれ以下に落ちるまで引き渡さない
      ! (速いうちは慣性のある混合体として水柱に運動量を渡す。引き渡しで
      !  底層が混合体より遅くなることがない = 運動量に対して単調)。
      ! 診断: 引き渡し時の混合体速度と V_b の体積重み平均を dispose で報告
      hbq = s%hb(i,j) + dd
      hw = max(s%h(i,j), 0.0)
      phic = s%z(i,j) + gm%bs_r * hw
      smax = 0.0
      do k = 1, 8
        in = i + din(k)
        jn = j + djn(k)
        if (g%x(in,jn) <= 0) cycle
        if (g%sw(in,jn) > 0) cycle
        phin = s%z(in,jn) + gm%bs_r * max(s%h(in,jn), 0.0)
        dphi = phic - phin
        if (dphi <= 0.0) cycle
        sl = dphi * gm%bsl%rdr(k)
        if (sl > smax) smax = sl
      end do
      bb = 1.0 - gm%bs_r * min(1.0, hw / hbq)
      sy = smax - gm%bs_mu * bb
      vb = 0.0
      if (sy > 0.0) vb = sqrt(gm%bs_xi * hbq * sy)
      if (gm%f_bsvplunge == 1) then
        if (s%vv(i,j) > max(vb, gm%bs_vstop)) cycle           ! まだ速い: 混合体のまま
      end if
      psum1 = psum1 + dd * s%vv(i,j)
      psum2 = psum2 + dd * vb
      s%hs(i,j) = 0.0
      s%hb(i,j) = s%hb(i,j) + dd
      s%z(i,j) = s%z(i,j) + dd
      s%sd(i,j) = s%sd(i,j) + dd
      if (gm%f_dbwet == 1) then
        dhw = -gm%db_lamsb * dd
        dhw = max(dhw, -max(s%h(i,j), 0.0))
        s%h(i,j) = s%h(i,j) + dhw
      end if
      vsum = vsum + dd
    end do
  end do
  !$omp end parallel do
  gm%bsl%vplunge = gm%bsl%vplunge + vsum * gm%bsl%area
  gm%bsl%pmix = gm%bsl%pmix + psum1 * gm%bsl%area
  gm%bsl%pbed = gm%bsl%pbed + psum2 * gm%bsl%area
end subroutine


!----------------------------------------------------------------------
! 台帳の報告・私有 save・作業領域の解放
!----------------------------------------------------------------------
module subroutine dispose_bedslide(gm, p, g, s)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  real :: vsum(1:6), hsum
  integer :: i, j
  character(len=256) :: msg

  if (gm%f_bedslide <= 0) return
  if (p%f_state_save > 0) call save_bedslide(gm, p, g, s)

  hsum = 0.0
  if (allocated(s%hb)) then
    do j = dcp%js, dcp%je
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0) cycle
        hsum = hsum + s%hb(i,j)
      end do
    end do
  end if
  vsum(1) = gm%bsl%vrel
  vsum(2) = gm%bsl%vstop
  vsum(3) = hsum * gm%bsl%area
  vsum(4) = gm%bsl%vplunge
  vsum(5) = gm%bsl%pmix
  vsum(6) = gm%bsl%pbed
  call par_allreduce_sumr(vsum)
  if (is_root) then
    write(msg,'(a,es12.4,a,es12.4,a,es12.4,a,es12.4,a)') &
      " geomorph: bedslide released ", vsum(1), " m3, plunged ", vsum(4), &
      " m3, stopped ", vsum(2), " m3, still moving ", vsum(3), " m3"
    call par_info(trim(msg))
    if (vsum(4) > 0.0) then
      ! 引き渡し時の速度の対比(体積重み平均)。混合体 >> 底層なら、引き渡しで
      ! 失う運動量が大きい(近地波の過小側の偏り。landslide_tsunami_plan.md §4.4)
      write(msg,'(a,f8.3,a,f8.3,a)') &
        " geomorph: bedslide plunge speeds (volume-weighted): mixture ", vsum(5) / vsum(4), &
        " m/s -> bed layer ", vsum(6) / vsum(4), " m/s"
      call par_info(trim(msg))
    end if
  end if
  if (gm%bsl%ntick > 0) then
    call par_info(" geomorph: bedslide subcycles total = " // itoa(gm%bsl%nsubtot) &
                  // " over " // itoa(gm%bsl%ntick) // " active updates (max " &
                  // itoa(gm%bsl%nsubpk) // " per update; see developer.md sec.61.10)")
  end if
  if (gm%bsl%nrelclip > 0) then
    call par_warn("geomorph: bedslide release depth exceeded soil depth sd " &
                  // "and was clipped to sd in " // itoa(gm%bsl%nrelclip) // " cells" &
                  // " (check consistency between fn_bsinit and the soil depth input)")
  end if

  if (allocated(gm%bsl%vc)) deallocate(gm%bsl%vc)
  if (allocated(gm%bsl%qt)) deallocate(gm%bsl%qt)
  if (allocated(gm%bsl%ws)) deallocate(gm%bsl%ws)
  if (allocated(gm%bsl%q)) deallocate(gm%bsl%q)
  if (allocated(gm%bsl%rel)) deallocate(gm%bsl%rel)
  if (allocated(gm%bsl%nst)) deallocate(gm%bsl%nst)
  if (allocated(gm%bsl%eref)) deallocate(gm%bsl%eref)
  gm%bsl%nrelclip = 0
  gm%bsl%vrel = 0.0
  gm%bsl%vstop = 0.0
  gm%bsl%vplunge = 0.0
  gm%bsl%pmix = 0.0
  gm%bsl%pbed = 0.0
  gm%bsl%nsubtot = 0
  gm%bsl%ntick = 0
  gm%bsl%nsubpk = 0
end subroutine


!----------------------------------------------------------------------
! 内部状態の保存・復元(モデル私有ファイル geomorph_bedslide.dat。契約5。§7)
!----------------------------------------------------------------------
subroutine save_bedslide(gm, p, g, s)
  type(t_geomorph), intent(in) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  real, allocatable :: wk(:,:)
  integer :: un
  if (is_root) then
    allocate(wk(1:g%nx, 1:g%ny), source = 0.0)
  else
    allocate(wk(1, 1), source = 0.0)
  end if
  call par_gather_to(wk, s%hb)
  if (is_root) then
    call sysdep_mkdir(p%dir_save)
    open(newunit=un, file=trim(p%dir_save)//'/geomorph_bedslide.dat', form='unformatted', &
         status='replace')
    call fileio_write_rle(un, wk)
  end if
  ! 低速の連続 tick 数(bs_tstop の途中経過。書き並びは restore と同時に更新)
  call par_gather_to(wk, gm%bsl%nst)
  if (is_root) call fileio_write_rle(un, wk)
  ! f_bsplunge=1 の基準水面(3 面目。0 でも書く = 面数固定)
  call par_gather_to(wk, gm%bsl%eref)
  if (is_root) then
    call fileio_write_rle(un, wk)
    close(un)
  end if
end subroutine


subroutine restore_bedslide(gm, p, g, s)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, allocatable :: wk(:,:)
  real :: dum(1,1)
  character(:), allocatable :: fname
  logical :: found
  integer :: un

  fname = trim(p%dir_save)//'/geomorph_bedslide.dat'
  inquire(file=fname, exist=found)
  if (.not. found) then
    call par_stop("geomorph: bedslide state file not found (was f_bedslide enabled when saving): " &
                  // fname)
  end if
  if (is_root) then
    allocate(wk(1:g%nx, 1:g%ny), source = 0.0)
    open(newunit=un, file=fname, form='unformatted', status='old')
    call fileio_read_rle(un, wk)
    call par_scatter_cell(wk, s%hb)
    call fileio_read_rle(un, wk)
    call par_scatter_cell(wk, gm%bsl%nst)
    call fileio_read_rle(un, wk)
    close(un)
    call par_scatter_cell(wk, gm%bsl%eref)
  else
    call par_scatter_cell(dum, s%hb)
    call par_scatter_cell(dum, gm%bsl%nst)
    call par_scatter_cell(dum, gm%bsl%eref)
  end if
end subroutine


end submodule
