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
!   【1 tick の処理】
!     (0) hb の全域最大が 0 なら return(allreduce。全ランク同一)
!     (1) z・h・hb のハロ交換(他プロセスの帯内 z 更新・swflow の h 更新・
!         前 tick の停止を配布。§28.2 の実バグの教訓)
!     (2) サブサイクル: パス0(セル量 V・Q_c・Σ重み。帯±1 行)→
!         安定条件(V_max・hb·dV/dS の allreduce_max → dt_sub。決定的)→
!         パスB(エッジ流量。帯界面は je+1 行の書き手が冗長計算)→
!         パスC(発散。hb・z・sd の共動更新。自帯のみ)→ hb・z のハロ交換
!     (3) 停止: パス0 を再評価し V < bs_vstop のセルの hb を 0 に
!     e の回復と sd のハロ交換は m_geomorph_calc の末尾が行う
!
!   MPI 規約(developer.md §11): 更新は自帯 js..je のみ、エッジは
!   書き手一意(k=1..4 が所有成分)、collective の判定は全ランク同一。
!   エッジ作業領域は本プロセス私有(bsl%q)。共有の wrk%q は fluvial が
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
  integer :: k
  real :: lpx, lpy, ldx, ldy, dr
  real, allocatable :: wk(:,:)

  ! --- 検証 ---
  if (gm%morfac /= 1.0) then
    call par_stop("list_geomorph: f_bedslide requires morfac=1 (event-scale computation)")
  end if
  if (len_trim(list%fn_bsinit) == 0) then
    call par_stop("list_geomorph: f_bedslide=1 requires fn_bsinit(崩壊深分布 = 発火与件)")
  end if
  if (list%bs_rho <= bs_rhow) then
    call par_stop("list_geomorph: f_bedslide requires bs_rho > 1000 kg/m3" &
                  // "(土塊のかさ密度は水より大きい)")
  end if
  select case (list%f_bsres)
    case (1)
      if (list%bs_mu <= 0.0) call par_stop("list_geomorph: f_bsres=1 requires bs_mu > 0")
      if (list%bs_xi <= 0.0) call par_stop("list_geomorph: f_bsres=1 requires bs_xi > 0 (m/s2)")
    case (2)
      call par_stop("list_geomorph: f_bsres=2 (Bingham) is reserved and not implemented yet" &
                    // " — landslide_tsunami_plan.md sec.4.3")
    case default
      call par_stop("list_geomorph: f_bsres must be 1(Voellmy) or 2(Bingham, reserved)")
  end select
  if (list%bs_vstop <= 0.0) call par_stop("list_geomorph: f_bedslide requires bs_vstop > 0 (m/s)")
  if (list%bs_eps_s <= 0.0) call par_stop("list_geomorph: bs_eps_s must be > 0")
  if (list%bs_diagratio < 0.0 .or. list%bs_diagratio > 1.0) then
    call par_stop("list_geomorph: bs_diagratio must be in [0,1]")
  end if
  if (list%bs_cfl <= 0.0 .or. list%bs_cfl > 1.0) call par_stop("list_geomorph: bs_cfl must be in (0,1]")
  if (list%bs_nsubmax < 1) call par_stop("list_geomorph: bs_nsubmax must be >= 1")

  gm%bs_r = bs_rhow / list%bs_rho
  gm%f_bsres = list%f_bsres
  gm%bs_mu = list%bs_mu
  gm%bs_xi = list%bs_xi
  gm%bs_vstop = list%bs_vstop
  gm%bs_eps_s = list%bs_eps_s
  gm%bs_cfl = list%bs_cfl
  gm%bs_nsubmax = list%bs_nsubmax
  gm%bs_reltime = list%bs_reltime

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
  bsl%wl(1) = sqrt((ldy * g%dy)**2 + (ldx * g%dx)**2)
  bsl%wl(2) = lpx * g%dx
  bsl%wl(3) = bsl%wl(1)
  bsl%wl(4) = lpy * g%dy
  bsl%wl(5) = bsl%wl(4)
  bsl%wl(6) = bsl%wl(3)
  bsl%wl(7) = bsl%wl(2)
  bsl%wl(8) = bsl%wl(1)
  do k = 1, 8
    bsl%rdr(k) = 1.0 / sqrt((din(k) * g%dx)**2 + (djn(k) * g%dy)**2)
  end do
  bsl%area = g%dx * g%dy
  bsl%rdx2 = 1.0 / g%dx**2 + 1.0 / g%dy**2
  bsl%dxmin = min(g%dx, g%dy)

  ! --- 状態と作業領域(有効時のみ確保 = 無効時ゼロコスト) ---
  if (.not. allocated(s%hb)) allocate(s%hb(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  if (.not. allocated(s%vb)) allocate(s%vb(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(bsl%vc(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(bsl%qt(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(bsl%ws(1:g%nx, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(bsl%q(1:4, 0:g%nx, dcp%jsh-1:dcp%jeh), source = 0.0)

  ! --- 発火与件(崩壊深分布。全ランク冗長の全域読み。read_release と同じ流儀) ---
  allocate(wk(1:g%nx, 1:g%ny), source = 0.0)
  call fileio_read_matrix(trim(p%dir_data)//"/"//trim(list%fn_bsinit), g%nx, g%ny, wk, &
                          p%f_input_mode)
  if (minval(wk) < 0.0) then
    call par_stop("list_geomorph: fn_bsinit release depth has negative values: " &
                  // trim(list%fn_bsinit))
  end if
  allocate(bsl%rel(1:g%nx, dcp%js:dcp%je), source = wk(1:g%nx, dcp%js:dcp%je))
  deallocate(wk)

  ! --- restore(私有ファイル。契約5) ---
  if (p%f_state_restore > 0) call restore_bedslide(p, g, s)

  call par_info("geomorph: bedslide enabled (Voellmy mu=" // rtoa(gm%bs_mu) &
                // ", xi=" // rtoa(gm%bs_xi) // ", r=rho_w/rho_s=" // rtoa(gm%bs_r) // ")")
end subroutine


!----------------------------------------------------------------------
! 発火(可動化)。時刻交差で 1 回だけ(release_debris と同じ判定 =
! リスタート後に再発火しない)。hb = min(D, sd)。z・sd・h・e は不変
!----------------------------------------------------------------------
module subroutine release_bedslide(gm, p, g, s)
  type(t_geomorph), intent(in) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer :: i, j
  real :: tprev, dd, vsum

  if (.not. allocated(bsl%rel)) return          ! この run で発火済み
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
      dd = bsl%rel(i,j)
      if (dd <= 0.0) cycle
      if (dd > s%sd(i,j)) then
        dd = s%sd(i,j)                          ! 可動層クランプ(dispose で報告)
        bsl%nrelclip = bsl%nrelclip + 1
        if (dd <= 0.0) cycle
      end if
      s%hb(i,j) = s%hb(i,j) + dd
      vsum = vsum + dd
    end do
  end do
  bsl%vrel = bsl%vrel + vsum * bsl%area
  deallocate(bsl%rel)                           ! 発火は1回だけ
  ! 帯の hb をハロへ(calc_bedslide の冒頭交換が担うのでここでは不要)
end subroutine


!----------------------------------------------------------------------
! パス0: セル量の評価(帯±1 行。近傍の Φ を読む。書き込みは bsl の
! 作業配列のみ)。vmax・dmax は安定条件用の局所最大
!----------------------------------------------------------------------
subroutine eval_cells(gm, g, s, vmax, dmax)
  type(t_geomorph), intent(in) :: gm
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
      bsl%vc(i,j) = 0.0
      bsl%qt(i,j) = 0.0
      bsl%ws(i,j) = 0.0
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
        sl = dphi * bsl%rdr(k)
        ws = ws + sl * bsl%wl(k)
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
      bsl%vc(i,j) = vv
      bsl%qt(i,j) = hb * vv * ws / smax     ! 総流出 = 配分重みの和 / セル勾配
      bsl%ws(i,j) = ws
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
  type(t_geomorph), intent(in) :: gm
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: dtw
  integer :: i, j, k, in, jn, jt, nsub
  real :: w1(2), vmax, dmax, trem, dtsub, dlim, ainv
  real :: phic, phin, dphi, gq, fdon, dv, dd, vsum
  logical :: okc, last

  ainv = 1.0 / bsl%area

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

  bsl%ntick = bsl%ntick + 1
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
      dlim = gm%bs_cfl * bsl%dxmin / vmax
      if (dlim < dtsub) then
        dtsub = dlim
        last = .false.
      end if
    end if
    if (dmax > 0.0) then
      dlim = gm%bs_cfl * 0.5 / (dmax * bsl%rdx2)
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
                if (bsl%qt(i,j) > 0.0) then
                  ! ドナー律速(除算は 総流出 > 保有量 のときだけ = 0 除算なし)
                  fdon = 1.0
                  if (dtsub * bsl%qt(i,j) > s%hb(i,j) * bsl%area) then
                    fdon = s%hb(i,j) * bsl%area / (dtsub * bsl%qt(i,j))
                  end if
                  gq = fdon * bsl%qt(i,j) * (dphi * bsl%rdr(k) * bsl%wl(k)) / bsl%ws(i,j)
                end if
              else if (dphi < 0.0) then
                ! 送り手 = 近傍(n → c。格納は c→n 正なので負)
                if (bsl%qt(in,jn) > 0.0) then
                  fdon = 1.0
                  if (dtsub * bsl%qt(in,jn) > s%hb(in,jn) * bsl%area) then
                    fdon = s%hb(in,jn) * bsl%area / (dtsub * bsl%qt(in,jn))
                  end if
                  gq = -fdon * bsl%qt(in,jn) * (-dphi * bsl%rdr(k) * bsl%wl(k)) / bsl%ws(in,jn)
                end if
              end if
            end if
          end if
          bsl%q(k, i+die(k), j+dje(k)) = gq
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
          dv = dv + sign_e(k) * bsl%q(ke(k), i+die(k), j+dje(k))
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
  bsl%nsubtot = bsl%nsubtot + nsub

  ! --- (3) 停止: 更新後の場で速度を再評価し、閾値未満の hb を固定。
  !         診断の速度場 s%vb(自帯)もここで更新する(停止セルは 0) ---
  call eval_cells(gm, g, s, vmax, dmax)
  vsum = 0.0
  !$omp parallel do schedule(static) private(i, j) reduction(+: vsum)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      s%vb(i,j) = 0.0
      if (g%x(i,j) <= 0) cycle
      if (s%hb(i,j) <= 0.0) cycle
      if (bsl%vc(i,j) >= gm%bs_vstop) then
        s%vb(i,j) = bsl%vc(i,j)
        cycle
      end if
      vsum = vsum + s%hb(i,j)
      s%hb(i,j) = 0.0
    end do
  end do
  !$omp end parallel do
  bsl%vstop = bsl%vstop + vsum * bsl%area
  ! 停止後の hb のハロは次 tick 冒頭の交換が配布する(この後 hb を読む者はいない)
end subroutine


!----------------------------------------------------------------------
! 台帳の報告・私有 save・作業領域の解放
!----------------------------------------------------------------------
module subroutine dispose_bedslide(gm, p, g, s)
  type(t_geomorph), intent(in) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  real :: vsum(1:3), hsum
  integer :: i, j
  character(len=256) :: msg

  if (gm%f_bedslide <= 0) return
  if (p%f_state_save > 0) call save_bedslide(p, g, s)

  hsum = 0.0
  if (allocated(s%hb)) then
    do j = dcp%js, dcp%je
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0) cycle
        hsum = hsum + s%hb(i,j)
      end do
    end do
  end if
  vsum(1) = bsl%vrel
  vsum(2) = bsl%vstop
  vsum(3) = hsum * bsl%area
  call par_allreduce_sumr(vsum)
  if (is_root) then
    write(msg,'(a,es12.4,a,es12.4,a,es12.4,a)') &
      " geomorph: bedslide released ", vsum(1), " m3, stopped ", vsum(2), &
      " m3, still moving ", vsum(3), " m3"
    call par_info(trim(msg))
  end if
  if (bsl%ntick > 0) then
    call par_info(" geomorph: bedslide subcycles total = " // itoa(bsl%nsubtot) &
                  // " over " // itoa(bsl%ntick) // " active updates")
  end if
  if (bsl%nrelclip > 0) then
    call par_warn("geomorph: bedslide release depth exceeded soil depth sd " &
                  // "and was clipped to sd in " // itoa(bsl%nrelclip) // " cells" &
                  // " (check consistency between fn_bsinit and the soil depth input)")
  end if

  if (allocated(bsl%vc)) deallocate(bsl%vc)
  if (allocated(bsl%qt)) deallocate(bsl%qt)
  if (allocated(bsl%ws)) deallocate(bsl%ws)
  if (allocated(bsl%q)) deallocate(bsl%q)
  if (allocated(bsl%rel)) deallocate(bsl%rel)
  bsl%nrelclip = 0
  bsl%vrel = 0.0
  bsl%vstop = 0.0
  bsl%nsubtot = 0
  bsl%ntick = 0
end subroutine


!----------------------------------------------------------------------
! 内部状態の保存・復元(モデル私有ファイル geomorph_bedslide.dat。契約5。§7)
!----------------------------------------------------------------------
subroutine save_bedslide(p, g, s)
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
    close(un)
  end if
end subroutine


subroutine restore_bedslide(p, g, s)
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
    close(un)
    call par_scatter_cell(wk, s%hb)
  else
    call par_scatter_cell(dum, s%hb)
  end if
end subroutine

end submodule
