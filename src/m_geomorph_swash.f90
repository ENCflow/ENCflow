!======================================================================
! m_geomorph の submodule: 遡上域(swash)の輸送(f_wfswash。§90.21)
!   位相平均の波浪場(fn_wavefield)は汀線の手前で止まり、遡上の流れを持たない。汀線の面
!   (湿ったセル w と、地盤が w より高い乾いたセル d の間)に、遡上の 1 周期で積分した正味の
!   輸送の経験式を与える。前浜が平衡勾配より緩ければ砂を遡上の届く高さまで積み上げ、急なら削る。
!
!   岸沖(Larson, Kubota & Erikson 2004 式 (8)。正 = 沖向き。かさ体積の単位幅輸送 m2/s):
!     q_c = K_c 2√(2g) R^{3/2} (1 − z/R)² · tanφ_m/(tan²φ_m − tan²β) · (tanβ − tanβ_e)
!   沿岸(Larson & Wamsley 2007 式 (4)・(6)・(7)。u_o = u_s √(1 − z/R)、t_o/T = √(1 − z/R)、v_o = v_s):
!     q_l = K_l tanφ_m/(tan²φ_m − tan²β) · (u_o² v_o/g) · (t_o/T)
!   R: 遡上高(摩擦のない弾道の遡上で R = u_s²/2g。u_s = 遡上の初速の岸沖成分)、z: 静水面からの
!   高さ、tanβ: 前浜の勾配、tanβ_e: 平衡勾配(利用者が与える)、φ_m: 動く粒子の摩擦角。
!   既定の K_c = 1.6e-3 は Larson らの 4 例の較正の平均(細砂の代表値)、K_l = K_c は
!   Larson & Wamsley の仮定。式は緩い前浜・遡上の周期 ≈ 入射波の周期(ξ0 ≳ 1)を前提とする。
!
!   遡上高 R(Stockdon ら 2006 式 (19) の振れ幅の部分。独自の組み合わせ): 2 % 超過の遡上
!   R2 = 1.1 (⟨η⟩ + S/2)、S = √(H0 L0 (0.563 β² + 0.004)) のうち、setup ⟨η⟩ は流れが解く
!   (wf_flow ≥ 1。w の水位 η_w = z_w + h_w に入っている)ので、R = 1.1 S/2 を η_w から測る。
!   Larson らは R を Mayer & Kriebel 1994・Hunt 1959 の式(有義波高)で求めて K_c を較正した
!   (R の定義の違いの分、K_c の値の意味はずれ得る)。H0 は沖の境界の入射波高 H_inc(深海へ
!   逆算しない)に露出度 E を掛けたもの、L0 = gT²/2π(T は波浪場の代表周期)。
!   露出度(独自): 汀線セルの ±2 セルの波浪セルの波高と、飽和した波高 min(H_inc, γ_s h)
!   (γ_s = 不規則波 √2 γmax、規則波 γ)の比の最大(1 で頭打ち)。開けた海浜の汀線では波高が
!   水深で飽和して E = 1、デルタの陰・河道の内部では小さい。近くに波浪セルがなければ遡上なし。
!
!   格子への当てはめ(独自):
!   - 汀線セル = 4 近傍(東西南北)に地盤の高い乾いたセルを持つ湿ったセル。湿った領域と乾いた
!     領域の境は 4 近傍の面の階段で、単位長さあたりの x 法線の面の数は |n_x|/Δy、y 法線は |n_y|/Δx
!     (n̂ = 汀線の法線)。
!   - 岸沖は汀線の 4 近傍の面ごと: 両側のセルの中央差分の勾配の平均 G を前浜の勾配とし
!     (tanβ = |G|、岸向き n̂ = G/|G|)、q_c の沖向きのベクトルの面の向きへの射影 × セルの辺の
!     長さ(x 法線は Δy、y 法線は Δx)を流束にする。階段の面の数の上の比で、平面の海浜なら汀線の
!     向きによらず単位長さあたり q_c になる(斜めの面は使わない。使うと、斜めの面の先のセルが
!     遡上の届かない高さになる粗い格子で、45° の汀線の総量が軸に沿う汀線の 1/√2 になる)。
!     式は方向微分ではなく |G| で評価する(平衡勾配で 0)。z = max(z_d − η_w, 0)(乾いたセルの
!     地盤の静水面からの高さ)。z ≥ R なら流束なし = 堆積は η_w + R を越えない。掃流砂の規則
!     R1・R2(§84.2)の例外として乾いたセルへ積もり、乾いたセルから削る。岸向きは 1 面の堆積の
!     厚さを (η_w + R − z_d)/n_d(n_d = d に 4 近傍で接する地盤の低い湿ったセルの数)まで、両向き
!     とも変動上限 fluv_dzmax まで縮める(陽解法の行き過ぎの防止。流量の段階なので保存則は保つ)。
!   - 沿岸は汀線セルのベクトル(沿岸漂砂 calc_wave_longshore と同じ両セル平均の射影): 遡上域の
!     幅 R/tanβ(セルの大きさ Δ で頭打ち)で q_l を積分した Q_l = K_l f (u_s² v_s/g) ∫(1 − z/R)^{3/2} dx
!     を、汀線セルの 1 セル幅の帯に置く。帯の幅 W = max(|t_y| Δx, |t_x| Δy)(t̂ = 汀線の接線。
!     汀線セルは汀線の向きによらず 8 連結の 1 列で、単位長さあたりの面積が W)で割り、帯を
!     通る総量を Q_l にする。面は斜めも含めて 8 方向(帯の流れは斜めの面も通る)。規則は、両側が湿っていれば掃流砂の R1・R2、
!     片側が乾いていれば、その地盤が隣の汀線セルの遡上の届く高さ η + R より下のときだけ通す
!     (遡上域は汀線を挟む = 乾いた側の斜めの面も帯の流れの一部)。v_s = u_s tanθ(θ = 汀線の
!     法線と平均波向のなす角。θ ≥ 80° は沿岸なし)。ベクトルは遡上域があるとき = 4 近傍の地盤の
!     高い乾いたセルのどれかが遡上の届く高さ(z_d − η_w < R。岸沖と同じ条件)のときだけ置く。遡上の
!     届かない崖・護岸の前の汀線セル(深い)には遡上域がない(この条件がないと、帯が崖の前で砂を
!     運ぶ速いベルトになり、examples/delta で河口の砂が北の壁際まで運ばれた)。
!   - tanφ_m/(tan²φ_m − tan²β) と遡上高の β は 0.9 tanφ_m で頭打ち(急な面の特異の回避)。
!   - 水の流路の幅の係数(河道幅 frw・塞がれた開口の振り替え fwd。掃流砂・沿岸漂砂は水と同じに
!     掛ける)は掛けない: 遡上域の流束は面の幅ではなく汀線の長さ(岸沖)と帯の幅(沿岸)で決めて
!     おり、振り替えを掛けると汀線の面で 1 + 1/√2 倍になる(乾いた側の斜めの面が水の流れでは
!     塞がり、その幅が正規の面へ振り替わるため)。堤防の面の遮断(bank_active)は掃流砂と同じ。
!
!   MPI: 汀線セルの R と沿岸のベクトルは自帯で求めてハロ交換(3 回)、面の流束は
!   calc_wave_longshore と同じ 2 ループ(書き手一意、je+1 行の冗長計算)。面は両側のセルの
!   中央差分と d の 4 近傍(±1 行)を読む = z・h のハロ ±2 行で足りる(呼び出し側が最新化)。
!   露出度の窓は ±2 行の wvh・h を読む(wvh のハロは波浪場が埋める)。全域の端は 1..nx・1..ny を
!   明示的に判定する(§84.15 と同じ。sw・h は余白なし)。collective はハロ交換と apply_edge_flux の
!   中だけで、凪の判定(入射波)は全ランク同じ値。状態なし(save/restore 不要)。
!   無効時は配列未確保・呼び出しなし(ゼロコスト)。
!======================================================================
submodule(m_geomorph) m_geomorph_swash
  use m_parallel, only : par_info, par_warn, par_stop, dcp, par_halo_cell
  use m_swflow_enc, only : chn
  use m_util, only : rtoa, itoa
  implicit none
  real, parameter :: deg = acos(-1.0) / 180.0
  real, parameter :: pi = acos(-1.0)

contains

!----------------------------------------------------------------------
module subroutine init_wfswash(gm, s, list)
  type(t_geomorph), intent(inout) :: gm
  type(t_state), intent(inout) :: s
  type(t_list_geomorph), intent(in) :: list
  real :: phim

  if (gm%f_wfsed <= 0) then
    call par_stop("list_geomorph: f_wfswash requires f_wfsed=1 (the swash reads the coastal wave field)")
  end if
  if (gm%f_fluvial <= 0) then
    call par_stop("list_geomorph: f_wfswash requires f_fluvial=1 (the swash transport rides the bed-load path)")
  end if
  ! 岩盤下刻(§89)の利用可能率を掛けるかの規約が未定(沿岸漂砂 §84.15 と同じ)のため、初期版は併用しない
  if (gm%f_rockinc > 0) call par_stop("list_geomorph: f_wfswash cannot be combined with f_rockinc yet")
  gm%sws%kc = gm_param("wfswash_kc", list%wfswash_kc, 1.6e-3, "", unset=-9999.0)
  if (gm%sws%kc <= 0.0) call par_stop("list_geomorph: wfswash_kc must be > 0")
  gm%sws%kl = gm_param("wfswash_kl", list%wfswash_kl, gm%sws%kc, "", unset=-9999.0)
  if (gm%sws%kl < 0.0) call par_stop("list_geomorph: wfswash_kl must be >= 0 (0 = no longshore swash transport)")
  phim = gm_param("wfswash_phim", list%wfswash_phim, 30.0, " deg", unset=-9999.0)
  if (phim <= 0.0 .or. phim >= 90.0) call par_stop("list_geomorph: wfswash_phim must be in (0, 90) deg")
  gm%sws%tphi = tan(phim * deg)
  if (list%wfswash_tanbe < -9000.0) then
    call par_stop("list_geomorph: f_wfswash requires wfswash_tanbe (the equilibrium foreshore slope)")
  end if
  if (list%wfswash_tanbe <= 0.0 .or. list%wfswash_tanbe >= gm%sws%tphi) then
    call par_stop("list_geomorph: wfswash_tanbe must be in (0, tan(wfswash_phim))")
  end if
  gm%sws%tbe = list%wfswash_tanbe
  ! 作業配列(有効時のみ確保 = 無効時ゼロコスト)
  allocate(gm%sws%r(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(gm%sws%qx(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(gm%sws%qy(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  s%wv_swash = .true.
  call par_info("geomorph: swash-zone transport on (Larson et al. 2004, Larson & Wamsley 2007; K_c = " &
                // rtoa(gm%sws%kc) // ", K_l = " // rtoa(gm%sws%kl) // ", tan(beta_e) = " // rtoa(gm%sws%tbe) &
                // "; runup from the swash of Stockdon et al. 2006)")
end subroutine


!----------------------------------------------------------------------
! 遡上域の輸送のエッジ流束(calc_fluvial の後、calc_repose の前。z・sd・h のハロは呼び出し側、
! wvh・wvex・wvey のハロは波浪場が最新化済み)
!----------------------------------------------------------------------
module subroutine calc_wfswash(gm, p, g, s, dts)
  type(t_geomorph), intent(inout) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  real, intent(in) :: dts
  integer :: i, j, k, a, b, ii, jj, in, jn, iw, jw, id, jd, im, jm, m, nd, jt, nact, nclip
  real :: hinc, l0, hsr, c2g, tphi, tbe, kc, kl, tfm, dl, cmin
  real :: e, hm, hsat, wxs, wys, wn, gx, gy, gx2, gy2, tb, tf, fac, rr, h0
  real :: nx, ny, tx, ty, cosa, sina, us, vs, ws, aint, wb, ql
  real :: qe, gl, gc, gwd, sgn, etaw, zr, pr, qc, ls, dze, hr, winv
  real :: von, voff, vlong
  logical :: shore, reach, okc, okbank, okl, wetc, wetn

  hinc = s%wv_hinc
  if (hinc <= 0.0 .or. s%wv_tinc <= 0.0) return        ! 凪: 何もしない(入射波は全ランク同じ値)
  l0 = p%gg * s%wv_tinc**2 / (2.0 * pi)                ! 深海の波長 L0 = gT²/2π
  hsr = s%wv_hsat
  c2g = 2.0 * sqrt(2.0 * p%gg)
  tphi = gm%sws%tphi
  tbe = gm%sws%tbe
  kc = gm%sws%kc
  kl = gm%sws%kl
  tfm = 0.9 * tphi                                     ! 式の tanβ の頭打ち
  dl = min(g%dx, g%dy)                                 ! 沿岸の積分の遡上域の幅の頭打ち Δ
  cmin = cos(80.0 * deg)                               ! 沿岸の輸送の入射角の上限 80°

  ! --- 汀線セルの遡上高 R と沿岸のベクトル(自帯)---
  nact = 0
  !$omp parallel do schedule(static) reduction(+: nact) &
  !$omp   private(i, j, k, a, b, ii, jj, in, jn, shore, reach, etaw, e, hm, hsat, wxs, wys, wn, gx, gy, tb, tf, &
  !$omp           fac, h0, rr, nx, ny, tx, ty, cosa, sina, us, vs, ws, aint, wb, ql)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      gm%sws%r(i,j) = 0.0
      gm%sws%qx(i,j) = 0.0
      gm%sws%qy(i,j) = 0.0
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      if (s%h(i,j) <= p%dd) cycle
      ! 汀線セル = 4 近傍(k = 2, 4, 5, 7)に地盤の高い乾いたセルがある湿ったセル
      shore = .false.
      do k = 2, 7
        if (din(k) /= 0 .and. djn(k) /= 0) cycle          ! 斜め(k = 3, 6)は除く
        in = i + din(k)
        jn = j + djn(k)
        if (in < 1 .or. in > g%nx .or. jn < 1 .or. jn > g%ny) cycle
        if (g%x(in,jn) <= 0) cycle
        if (g%sw(in,jn) > 0) cycle
        if (s%h(in,jn) <= p%dd .and. s%z(in,jn) > s%z(i,j)) then
          shore = .true.
          exit
        end if
      end do
      if (.not. shore) cycle
      ! 露出度と平均波向(±2 セルの波浪セル。向きは波のエネルギー H² の重み)
      e = 0.0
      wxs = 0.0
      wys = 0.0
      do b = -2, 2
        jj = j + b
        if (jj < 1 .or. jj > g%ny) cycle
        do a = -2, 2
          ii = i + a
          if (ii < 1 .or. ii > g%nx) cycle
          if (g%x(ii,jj) <= 0) cycle
          hm = s%wvh(ii,jj)
          if (hm <= 0.0) cycle
          hsat = min(hinc, hsr * s%h(ii,jj))
          if (hsat > 0.0) e = max(e, hm / hsat)
          wxs = wxs + hm * hm * s%wvex(ii,jj)
          wys = wys + hm * hm * s%wvey(ii,jj)
        end do
      end do
      e = min(e, 1.0)
      if (e <= 0.0) cycle
      ! 前浜の勾配(中央差分)と遡上高 R = 1.1 S/2(Stockdon ら 2006 式 (19) の振れ幅)
      call swash_zgrad(g, s, i, j, gx, gy)
      tb = sqrt(gx * gx + gy * gy)
      tf = min(tb, tfm)
      h0 = e * hinc
      rr = 0.55 * sqrt(h0 * l0 * (0.563 * tf * tf + 0.004))
      gm%sws%r(i,j) = rr
      nact = nact + 1
      ! 沿岸(Larson & Wamsley 2007): 遡上域があり、平均波向が汀線の法線から 80° 以内のときだけ
      if (kl <= 0.0 .or. tb < 1.0e-4) cycle
      ! 遡上域 = 4 近傍の地盤の高い乾いたセルのどれかが遡上の届く高さ(岸沖と同じ z_d − η_w < R)
      reach = .false.
      etaw = s%z(i,j) + s%h(i,j)
      do k = 2, 7
        if (din(k) /= 0 .and. djn(k) /= 0) cycle
        in = i + din(k)
        jn = j + djn(k)
        if (in < 1 .or. in > g%nx .or. jn < 1 .or. jn > g%ny) cycle
        if (g%x(in,jn) <= 0) cycle
        if (g%sw(in,jn) > 0) cycle
        if (s%h(in,jn) <= p%dd .and. s%z(in,jn) > s%z(i,j) .and. s%z(in,jn) - etaw < rr) then
          reach = .true.
          exit
        end if
      end do
      if (.not. reach) cycle
      wn = sqrt(wxs * wxs + wys * wys)
      if (wn <= 0.0) cycle
      nx = gx / tb                                     ! 岸向きの法線(上り勾配の向き)
      ny = gy / tb
      tx = -ny                                         ! 汀線の接線(法線を +90° 回す)
      ty = nx
      cosa = (wxs * nx + wys * ny) / wn
      if (cosa < cmin) cycle
      sina = (wxs * tx + wys * ty) / wn
      us = sqrt(2.0 * p%gg * rr)                       ! 遡上の初速の岸沖成分(R = u_s²/2g)
      vs = us * sina / cosa                            ! 沿岸成分 v_s = u_s tanθ
      fac = tphi / (tphi * tphi - tf * tf)
      ! 遡上域の幅 R/tanβ(Δ で頭打ち)で (1 − z/R)^{3/2} を積分 = (R/tanβ)(2/5)[1 − (1 − x tanβ/R)^{5/2}]
      ws = rr / tb
      if (ws <= dl) then
        aint = 0.4 * ws
      else
        aint = 0.4 * ws * (1.0 - (1.0 - dl / ws)**2.5)
      end if
      wb = max(abs(ty) * g%dx, abs(tx) * g%dy)        ! 帯の幅 W(単位長さあたりの帯の面積)
      ql = kl * fac * us * us * vs / p%gg * aint / wb / gm%poroi   ! 帯の固体の流束 (m2/s)
      gm%sws%qx(i,j) = ql * tx
      gm%sws%qy(i,j) = ql * ty
    end do
  end do
  !$omp end parallel do
  gm%sws%nact = gm%sws%nact + nact
  call par_halo_cell(gm%sws%r)
  call par_halo_cell(gm%sws%qx)
  call par_halo_cell(gm%sws%qy)

  ! --- エッジ流束(書き手一意。calc_wave_longshore と同じ 2 ループ)---
  von = 0.0
  voff = 0.0
  vlong = 0.0
  nclip = 0
  jt = min(dcp%je + 1, dcp%jeh)
  !$omp parallel do schedule(static) reduction(+: von, voff, vlong, nclip) &
  !$omp   private(i, j, k, m, in, jn, iw, jw, id, jd, im, jm, nd, okc, okbank, okl, wetc, wetn, qe, gl, gc, gwd, &
  !$omp           sgn, rr, etaw, zr, gx, gy, gx2, gy2, tb, tf, fac, pr, qc, ls, dze, hr, winv)
  do j = dcp%js, jt
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      okc = (g%sw(i,j) <= 0)
      do k = 1, 4
        in = i + din(k)
        jn = j + djn(k)
        gl = 0.0
        gc = 0.0
        if (okc .and. g%x(in,jn) > 0) then
          if (g%sw(in,jn) <= 0) then
            okbank = .true.
            if (g%bank_active) okbank = ((g%rw(i,j) > 0) .eqv. (g%rw(in,jn) > 0))
            if (okbank) then
              wetc = (s%h(i,j) > p%dd)
              wetn = (s%h(in,jn) > p%dd)
              ! 沿岸: 汀線セルのベクトルの両セル平均の射影。両側が湿っていれば掃流砂の規則 R1・R2、
              ! 片側が乾いていれば、その地盤が隣の汀線セルの遡上の届く高さより下のときだけ通す
              qe = 0.5 * (gm%sws%qx(i,j) + gm%sws%qx(in,jn)) * gm%flv%ex(k) &
                 + 0.5 * (gm%sws%qy(i,j) + gm%sws%qy(in,jn)) * gm%flv%ey(k)
              if (qe /= 0.0) then
                if (.not. wetc) then
                  okl = (s%z(i,j) < s%z(in,jn) + s%h(in,jn) + gm%sws%r(in,jn))
                else if (.not. wetn) then
                  okl = (s%z(in,jn) < s%z(i,j) + s%h(i,j) + gm%sws%r(i,j))
                else if (qe > 0.0) then
                  okl = (s%z(in,jn) < s%z(i,j) + s%h(i,j))
                else
                  okl = (s%z(i,j) < s%z(in,jn) + s%h(in,jn))
                end if
                if (okl) gl = qe * gm%flv%wl(k)
              end if
              ! 岸沖: 汀線の 4 近傍の面(湿ったセル w と、地盤が w より高い乾いたセル d の間)
              iw = 0
              if (k == 1 .or. k == 3) then
                continue                                 ! 斜めの面は使わない(ヘッダ)
              else if (wetc .and. .not. wetn .and. s%z(in,jn) > s%z(i,j)) then
                iw = i; jw = j; id = in; jd = jn; sgn = 1.0         ! c → n が岸向き
              else if (wetn .and. .not. wetc .and. s%z(i,j) > s%z(in,jn)) then
                iw = in; jw = jn; id = i; jd = j; sgn = -1.0
              end if
              if (iw > 0) then
                rr = gm%sws%r(iw,jw)
                etaw = s%z(iw,jw) + s%h(iw,jw)
                zr = max(s%z(id,jd) - etaw, 0.0)
                if (rr > 0.0 .and. zr < rr) then
                  call swash_zgrad(g, s, iw, jw, gx, gy)
                  call swash_zgrad(g, s, id, jd, gx2, gy2)
                  gx = 0.5 * (gx + gx2)
                  gy = 0.5 * (gy + gy2)
                  tb = sqrt(gx * gx + gy * gy)
                  pr = 0.0
                  if (tb > 0.0) pr = sgn * (gx * gm%flv%ex(k) + gy * gm%flv%ey(k)) / tb
                  if (pr > 0.0) then                     ! 岸向きの法線 n̂ の w → d の向きへの射影
                    tf = min(tb, tfm)
                    fac = tphi / (tphi * tphi - tf * tf)
                    qc = kc * c2g * rr**1.5 * (1.0 - zr / rr)**2 * fac * (tb - tbe)   ! かさ (m2/s)。正 = 沖向き
                    ls = g%dy                                ! セルの辺の長さ(x 法線 k = 4 は Δy、y 法線 k = 2 は Δx)
                    if (k == 2) ls = g%dx
                    gwd = -qc * pr * ls / gm%poroi           ! 固体 (m3/s)。正 = w → d(岸向き)
                    winv = 1.0
                    if (chn%have_width) winv = 1.0 / chn%wfrac(id,jd)
                    dze = abs(gwd) * dts * gm%wrk%ainv * winv * gm%poroi
                    if (gwd > 0.0) then
                      ! 岸向き: 1 面の堆積の厚さを遡上の上限までの余裕 / n_d まで
                      nd = 0
                      do m = 2, 7
                        if (din(m) /= 0 .and. djn(m) /= 0) cycle
                        im = id + din(m)
                        jm = jd + djn(m)
                        if (im < 1 .or. im > g%nx .or. jm < 1 .or. jm > g%ny) cycle
                        if (g%x(im,jm) <= 0) cycle
                        if (g%sw(im,jm) > 0) cycle
                        if (s%h(im,jm) > p%dd .and. s%z(im,jm) < s%z(id,jd)) nd = nd + 1
                      end do
                      hr = (etaw + rr - s%z(id,jd)) / real(max(nd, 1))
                      if (dze > hr) then
                        gwd = gwd * (hr / dze)
                        dze = hr
                        nclip = nclip + 1
                      end if
                    end if
                    if (dze > gm%dzmax) then                ! 変動上限(fluv_dzmax。掃流砂と同じ)
                      gwd = gwd * (gm%dzmax / dze)
                      nclip = nclip + 1
                    end if
                    gc = sgn * gwd
                  end if
                end if
              end if
              if (j <= dcp%je) then
                vlong = vlong + abs(gl) * dts
                if (gc /= 0.0) then                    ! gc /= 0 なら sgn は設定済み
                  if (sgn * gc > 0.0) then
                    von = von + abs(gc) * dts
                  else
                    voff = voff + abs(gc) * dts
                  end if
                end if
              end if
            end if
          end if
        end if
        gm%wrk%q(k, i+die(k), j+dje(k)) = gl + gc        ! 必ず上書き(書き手の契約)
      end do
      ! 域外(x<=0)に向く面スロットは 0
      do k = 5, 8
        in = i + din(k)
        jn = j + djn(k)
        if (g%x(in,jn) <= 0) gm%wrk%q(ke(k), i+die(k), j+dje(k)) = 0.0
      end do
    end do
  end do
  !$omp end parallel do
  gm%sws%von = gm%sws%von + von
  gm%sws%voff = gm%sws%voff + voff
  gm%sws%vlong = gm%sws%vlong + vlong
  gm%sws%nclip = gm%sws%nclip + nclip

  call apply_edge_flux(gm, g, s, dts)
end subroutine


!----------------------------------------------------------------------
! セル (i, j) の地盤の勾配 ∇z(中央差分。全域の外・域外 x <= 0 の側は片側差分。y は南が正)
!----------------------------------------------------------------------
pure subroutine swash_zgrad(g, s, i, j, gx, gy)
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  integer, intent(in) :: i, j
  real, intent(out) :: gx, gy
  logical :: oke, okw, oks, okn

  oke = .false.
  okw = .false.
  oks = .false.
  okn = .false.
  if (i < g%nx) oke = (g%x(i+1,j) > 0)
  if (i > 1) okw = (g%x(i-1,j) > 0)
  if (j < g%ny) oks = (g%x(i,j+1) > 0)
  if (j > 1) okn = (g%x(i,j-1) > 0)
  if (oke .and. okw) then
    gx = (s%z(i+1,j) - s%z(i-1,j)) / (2.0 * g%dx)
  else if (oke) then
    gx = (s%z(i+1,j) - s%z(i,j)) / g%dx
  else if (okw) then
    gx = (s%z(i,j) - s%z(i-1,j)) / g%dx
  else
    gx = 0.0
  end if
  if (oks .and. okn) then
    gy = (s%z(i,j+1) - s%z(i,j-1)) / (2.0 * g%dy)
  else if (oks) then
    gy = (s%z(i,j+1) - s%z(i,j)) / g%dy
  else if (okn) then
    gy = (s%z(i,j) - s%z(i,j-1)) / g%dy
  else
    gy = 0.0
  end if
end subroutine


!----------------------------------------------------------------------
module subroutine dispose_wfswash(gm)
  type(t_geomorph), intent(inout) :: gm
  ! ランク局所の診断(自帯の面を通った固体体積)
  call par_warn("geomorph: swash-zone transport moved " // rtoa(gm%sws%von) // " m3 (solid) onto and " &
                // rtoa(gm%sws%voff) // " m3 off the dry foreshore, and " // rtoa(gm%sws%vlong) &
                // " m3 alongshore, over " // itoa(gm%sws%nact) // " shoreline cell-updates (" &
                // itoa(gm%sws%nclip) // " face clips)")
  gm%sws%nact = 0
  gm%sws%nclip = 0
  gm%sws%von = 0.0
  gm%sws%voff = 0.0
  gm%sws%vlong = 0.0
end subroutine

end submodule
