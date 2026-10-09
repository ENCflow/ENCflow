submodule(m_swflow_enc) m_swflow_enc_adv
  use m_state, only : t_state
  use m_parallel, only : dcp   ! 親経由のホスト結合は nvfortran バグ回避のため直接 use
  implicit none

  ! 私有状態 t_enc_adv / tx_mod は親モジュールに置く(§13 の様式。文脈の付け替えの対象)

  ! 運動量保存形の方位定数(k=1..4 のみ。prepare は基準セルから k=1..4 の
  ! エッジを書くため)。線 k の方向 d = (din, djn)、横断方向 +t = (-d_y, d_x)
  ! に平行な隣接エッジの基準セルのオフセット δ+:
  !   k=1 d=(-1,-1) → δ+=( 1,-1)   k=2 d=(0,-1) → δ+=(1, 0)
  !   k=3 d=( 1,-1) → δ+=( 1, 1)   k=4 d=(-1,0) → δ+=(0,-1)
  integer, parameter :: ke8(1:8) = [ 1, 2, 3, 4, 4, 3, 2, 1 ]      ! 8 近傍番号 → エッジ成分
  real, parameter :: sgn8(1:8) = [ 1., 1., 1., 1., -1., -1., -1., -1. ]
  integer, parameter :: kkp(1:4) = [ 3, 5, 8, 2 ]   ! +t 側に隣接するセルの 8 近傍番号
  integer, parameter :: kkm(1:4) = [ 6, 4, 1, 7 ]   ! -t 側
  integer, parameter :: dti(1:4) = [ 1, 1, 1, 0 ]
  integer, parameter :: dtj(1:4) = [ -1, 0, 1, -1 ]

contains
!----------------------------------------------------------------------
! 移流項の内部場の確保
!----------------------------------------------------------------------
module subroutine adv_init(p, g)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  real :: dr
  if (p%initialized) continue  ! 引数未使用の警告を抑制
  if (opt%f_advection_scheme >= 2) then
    ! 運動量保存形: エッジ上の移流項だけを持つ(taxy/ulm/vlm は不要)
    allocate(tx_mod%tae(1:4,0:g%nx,dcp%jsh-1:dcp%jeh), source = 0.0)
    ! 検査体積の横断幅 = 平行な隣接エッジとの垂直距離
    !   軸エッジ: k=2(法線 y)は dx、k=4(法線 x)は dy
    !   対角エッジ: 2·dx·dy/dr(dx=dy なら √2·dx)
    dr = sqrt(g%dx**2 + g%dy**2)
    tx_mod%w8lt(1:4) = [ 2 * g%dx * g%dy / dr, g%dx, 2 * g%dx * g%dy / dr, g%dy ]
    return
  end if
  allocate(tx_mod%taxy(1:2,1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
  ! TODO(分割時): ulm/vlm/taxy はハロ行でも計算が必要(ステンシル幅2の源。developer.md §11)
  allocate(tx_mod%ulm(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
  allocate(tx_mod%vlm(1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
end subroutine


!----------------------------------------------------------------------
! 移流項の内部場を計算
!----------------------------------------------------------------------
module subroutine adv_prepare(p, g, s, sx)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  type(t_enc_status), intent(in) :: sx

  if (opt%f_advection_scheme >= 2) then
    call adv_prepare_mc(p, g, s, sx, tx_mod)
  else
    call adv_prepare_v1(p, g, s, sx, tx_mod)
  end if

end subroutine


!----------------------------------------------------------------------
! k番目の境界上の移流項を計算
!----------------------------------------------------------------------
module function adv_edge(s, sx, i, j, k, in, jn, ie, je) result(ta)
  type(t_state), intent(in) :: s
  type(t_enc_status), intent(in) :: sx
  integer, intent(in) :: i, j, k, in, jn, ie, je
  real :: ta

  if (opt%f_advection_scheme >= 2) then
    ta = tx_mod%tae(k,ie,je)
  else
    ta = adv_edge_v1(s, sx, tx_mod, i, j, k, in, jn)
  end if

end function


!----------------------------------------------------------------------
! 移流項用の内部場の破棄
!----------------------------------------------------------------------
module subroutine adv_dispose()
  if (allocated(tx_mod%taxy)) deallocate(tx_mod%taxy)
  if (allocated(tx_mod%ulm)) deallocate(tx_mod%ulm)
  if (allocated(tx_mod%vlm)) deallocate(tx_mod%vlm)
  if (allocated(tx_mod%tae)) deallocate(tx_mod%tae)
end subroutine


!======================================================================
!======================================================================
!----------------------------------------------------------------------
! 運動量保存形移流(f_advection_scheme = 2, 3。developer.md §68.6)
!
!   Stelling & Duinmeijer (2003, IJNMF 43:1329) のスタガード格子向け
!   定式化を ENC の 8 方向エッジに拡張したもの。エッジ e(基準セル c から
!   k 近傍 n へ、法線流速 u_e)の周りに運動量検査体積(長さ w8dr(k) =
!   c-n 間距離、横断幅 w8lt(k) = 平行な隣接エッジとの距離)を取り、
!   その面を通る質量流束 Q_f と面での風上化流速 ū_f から
!     adv_e = -(1/h̄_e) Σ_f Q_f (ū_f - u_e) / A_e
!   を評価する(流出面では ū_f = u_e で寄与 0、流入面では流入側の流速
!   との差で緩和)。連続式と組み合わせると離散運動量収支が保存され、
!   非保存形(v1)で生じる段波速度の誤差が消える。
!   - 流向面(c, n の中心を通る面): Q = q·w8lt、q はセル流量 (m, n) の
!     k 方向投影(ENC の連続式が見るセル平均流量と同じ定義)。
!     ū は線 k 上のエッジ流速 u_mm, u_m, u_e, u_p, u_pp から風上側を取る
!     (スキーム2: 1 次風上、スキーム3: MUSCL + van Leer の面値再構成)。
!   - 側方面(±t): Q = q_t·w8dr、q_t は面を横切る ENC エッジ(c → c+δ、
!     n → n+δ)の実流量 mn の平均(流出が正。§68.21。2026-10-03 までは
!     面中心のセル流量の t 方向投影を使っていたが、地形で遮られた面でも
!     非ゼロになり薄いエッジで発散した)。
!     ū は 1 次風上(u_e か、平行な隣接エッジの流速)。
!   - h̄_e = (h_c + h_n)/2(下限 dd/2)。サブグリッド河道(§18・§26)では
!     水量 h×wfrac(σ 有効時 sect_v(h)×wfrac)を使う(§68.9)。lm は v1 と
!     同じ流儀で乗じる(輸送項は dtl = dt/lme の減衰を相殺する。§20)。
!   - 確保範囲外のエッジ・セルは 0 として読む(領域外・無効セルの格納値
!     と同じ扱い。線 k が壁に当たると風上値が 0 = 壁)。
!   - 他エッジの uv・m・n はすべて時刻 n(ステップ頭でエッジ幅2・セル幅2
!     の交換済み)。書き込み先 tae(k, c+de) は (c, k) ごとに一意で競合なし。
!----------------------------------------------------------------------
subroutine adv_prepare_mc(p, g, s, sx, tx)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  type(t_enc_status), intent(in) :: sx
  type(t_enc_adv), intent(inout) :: tx

  integer :: i, j, k, in, jn, ie, je
  real :: hc, hn, hb, lme
  real :: ue, um, umm, up, upp, utp, utm
  real :: qc, qn, qtp, qtm
  real :: ubc, ubn, ubtp, ubtm
  real :: ta
  logical :: donor_rw               ! このエッジの流下方向の供給元を河道セルに限るか(§68.18)

  !$omp parallel do schedule(dynamic) &
  !$omp private(i, j, k, in, jn, ie, je, hc, hn, hb, lme, ue, um, umm, up, upp, utp, utm, &
  !$omp         qc, qn, qtp, qtm, ubc, ubn, ubtp, ubtm, ta, donor_rw)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      do k = 1, 4
        in = i + din(k)
        jn = j + djn(k)
        ie = i + die(k)
        je = j + dje(k)
        tx%tae(k,ie,je) = 0.0
        ! momentum と同じ除外条件(無効近傍・通過幅ゼロ・両側乾燥)
        if (g%x(in,jn) <= 0) cycle
        if (geo%skip8(k)) cycle
        hc = s%h(i,j)
        hn = s%h(in,jn)
        if (hc < p%dd .and. hn < p%dd) cycle
        ! 検査体積の水量(単位面積あたり): サブグリッド河道では h×wfrac
        ! (σ 有効時は矩形換算水深 sect_v(h)×wfrac)。連続式の水深換算
        ! (dh/wfrac、sect_v)と同じ定義で、q(セル幅あたりの流量)と整合する。
        ! gv(建物空隙率)は v1 と同様に乗じない(圧力項の ×gve と同じ流儀は
        ! 採らず、移流は輸送項として gv 非依存。§68.9)
        hb = (vol_depth(i, j) + vol_depth(in, jn)) / 2
        ! 河道セル間のエッジでは流下方向の供給元を河道セルに限る
        ! (f_advection_donor=1。屈曲・合流で線 k 上の風上エッジが浸水した
        ! 谷底・斜面セルに落ちると、その遅い水が供給元になって運動量を失う
        ! 人工損失の対策。側方面は対象外。§68.18)
        donor_rw = .false.
        if (opt%f_advection_donor == 1) donor_rw = g%rw(i,j) > 0 .and. g%rw(in,jn) > 0

        ! 線 k 上のエッジ流速(基準セルから k 方向。確保範囲外は 0)
        ue  = sx%uv(k,ie,je)
        um  = uvk(i - din(k), j - djn(k), k)
        umm = uvk(i - 2 * din(k), j - 2 * djn(k), k)
        up  = uvk(in, jn, k)
        upp = uvk(in + din(k), jn + djn(k), k)

        ! 流向面(c, n)を通る単位幅流量(k 方向投影。c→n が正)
        qc = s%m(i,j) * geo%n8x(k) + s%n(i,j) * geo%n8y(k)
        qn = s%m(in,jn) * geo%n8x(k) + s%n(in,jn) * geo%n8y(k)

        ! 流向面の風上化流速(面 c: 流入なら u_m 側、流出なら u_e 側)。
        ! 風上側の供給エッジが壁・領域外・乾燥セルに接する(cell_ok が偽)
        ! ときは ū = u_e とする(壁・乾床は運動量を供給しない。これを 0 と
        ! 読むと、ラスタ河道の屈曲セルで下流エッジが「壁側から流速 0 の
        ! 水が流入する」扱いになり、屈曲ごとに人工的な損失水頭が生じる。
        ! §68.8)。MUSCL の upup も同様に供給元が無効なら 1 次に退化
        ! MUSCL の upup(さらに風上のエッジ)は、そのエッジの向こうのセルが
        ! 領域外・無効(壁)なら使わず 1 次に退化する。uvk が返す 0 を upup に
        ! 使うと r = (up − 0)/(dn − up) ≫ 1 → ψ = 2 で面値が完全風下(dn)に
        ! なり、規定境界(区間流入・水位規定)から流れ出す線 k の最初の
        ! エッジが反拡散になって境界から指数的に発散する(§69.9。2026-10-05)。
        ! 判定は far_ok(全域で確保された g%x だけを見る): upp の向こうの
        ! セルは行 j ± 3 で帯+ハロ 2 の外に出るため、h を見る cell_ok を使うと
        ! ランク境界で判定が変わり np=1 と np=2 が一致しない
        if (qc >= 0) then
          if (donor_ok(i - din(k), j - djn(k), donor_rw)) then
            ubc = face_value(um, ue, umm, far_ok(i - 2 * din(k), j - 2 * djn(k)))
          else
            ubc = ue
          end if
        else
          ubc = face_value(ue, um, up, far_ok(in + din(k), jn + djn(k)))
        end if
        if (qn >= 0) then
          ubn = face_value(ue, up, um, far_ok(i - din(k), j - djn(k)))
        else
          if (donor_ok(in + din(k), jn + djn(k), donor_rw)) then
            ubn = face_value(up, ue, upp, far_ok(in + 2 * din(k), jn + 2 * djn(k)))
          else
            ubn = ue
          end if
        end if
        ta = -(qn * (ubn - ue) - qc * (ubc - ue)) / geo%w8dr(k)

        ! 側方面(±t。t = (-n8y, n8x))。流出が正
        utp = uvk(i + dti(k), j + dtj(k), k)
        utm = uvk(i - dti(k), j - dtj(k), k)
        ! 側方面(±t)の流束は、面を横切る ENC エッジの実流量(mn。時刻 n、
        ! 流出が正)の c 側・n 側の平均。面中心のセル平均流量 (m, n) の投影で
        ! 与えると、面の向こうのセルが地形で遮られて実際には水が通らない場合
        ! でも非ゼロになり、薄い検査体積(h̄ ≈ dd)で 1/h̄ 倍に増幅された移流項が
        ! 深い池に接する薄いエッジに生じて発散する(§68.21。2026-10-03 修正)
        qtp = 0.5 * (mnk(i, j, kkp(k)) + mnk(in, jn, kkp(k)))
        qtm = 0.5 * (mnk(i, j, kkm(k)) + mnk(in, jn, kkm(k)))
        ! 側方面も同様: 平行な隣接エッジの両セルが有効・湿潤のときだけ
        ! その流速を流入値に使う(壁・乾床側からは ū = u_e)
        if (qtp >= 0) then
          ubtp = ue
        else if (cell_ok(i + dti(k), j + dtj(k)) .and. &
                 cell_ok(i + dti(k) + din(k), j + dtj(k) + djn(k))) then
          ubtp = utp
        else
          ubtp = ue
        end if
        if (qtm >= 0) then
          ubtm = ue
        else if (cell_ok(i - dti(k), j - dtj(k)) .and. &
                 cell_ok(i - dti(k) + din(k), j - dtj(k) + djn(k))) then
          ubtm = utm
        else
          ubtm = ue
        end if
        ta = ta - (qtp * (ubtp - ue) + qtm * (ubtm - ue)) / tx%w8lt(k)

        ! 検査体積の水深は時刻 n の h̄ = (h_c + h_n)/2(下限 dd/2 = 片側乾燥
        ! エッジの最小値)。h̄^{n+1} の予測値(前ステップの流量で外挿)で
        ! 割る案は、ENC の「運動量 → 連続式」の順序では流量が 1 ステップ
        ! 遅れて段波速度を却って悪化させる(§68.6 の試行記録)
        lme = (s%lm(i,j) + s%lm(in,jn)) / 2
        tx%tae(k,ie,je) = ta / max(hb, p%dd / 2) * lme
      end do
    end do
  end do
  !$omp end parallel do

contains

  ! セル (ci, cj) を基準セルとする k 方向エッジの法線流速(確保範囲外は 0)
  pure function uvk(ci, cj, kk) result(u)
    integer, intent(in) :: ci, cj, kk
    real :: u
    integer :: ei, ej
    ei = ci + die(kk)
    ej = cj + dje(kk)
    if (ei < 0 .or. ei > ubound(sx%uv, 2) .or. ej < dcp%jsh - 1 .or. ej > dcp%jeh) then
      u = 0.0
    else
      u = sx%uv(kk,ei,ej)
    end if
  end function

  ! セルの単位面積あたり水量(水深換算)。河道幅 wfrac と断面形 σ を反映
  pure function vol_depth(ci, cj) result(v)
    integer, intent(in) :: ci, cj
    real :: v
    if (sct%have_sect) then
      v = sect_v(s%h(ci,cj), sct%sdep(ci,cj))
    else
      v = s%h(ci,cj)
    end if
    if (chn%have_width) v = v * chn%wfrac(ci,cj)
  end function

  ! MUSCL の upup の向こうのセルが領域内で有効か(g%x は全域で確保されて
  ! いるので全ランクで同じ判定。乾湿は見ない)
  pure function far_ok(ci, cj) result(ok)
    integer, intent(in) :: ci, cj
    logical :: ok
    ok = .false.
    if (ci < 1 .or. ci > g%nx .or. cj < 1 .or. cj > dcp%ny_g) return
    ok = g%x(ci,cj) > 0
  end function

  ! セルが運動量の供給元になれるか(確保範囲内・有効・移動限界以上の水深)
  pure function cell_ok(ci, cj) result(ok)
    integer, intent(in) :: ci, cj
    logical :: ok
    ok = .false.
    if (ci < 1 .or. ci > ubound(s%h, 1) .or. cj < dcp%jsh .or. cj > dcp%jeh) return
    if (g%x(ci,cj) <= 0) return
    ok = s%h(ci,cj) >= p%dd
  end function

  ! 流下方向の風上供給元になれるか: cell_ok に加え、河道セル間のエッジでは
  ! 河道セルに限る(f_advection_donor=1。§68.18)。側方面の供給元は対象外
  ! (斜面からの横流入の運動量吸い込みは物理なので残す)。
  ! drw(= 並列ループの private 変数 donor_rw)は必ず引数で受ける: 内部手続き
  ! のホスト結合はスレッドの private 複製ではなく共有の元変数(未初期化)を
  ! 読む(2026-10-03 の実バグ。§8)
  pure function donor_ok(ci, cj, drw) result(ok)
    integer, intent(in) :: ci, cj
    logical, intent(in) :: drw
    logical :: ok
    ok = cell_ok(ci, cj)
    if (ok .and. drw) ok = g%rw(ci,cj) > 0
  end function

  ! セル (ci, cj) からその kk 近傍(kk = 1..8)へ向かう ENC エッジの単位幅流量
  ! (時刻 n の mn。流出が正。確保範囲外は 0)
  pure function mnk(ci, cj, kk) result(q)
    integer, intent(in) :: ci, cj, kk
    real :: q
    integer :: ei, ej
    ei = ci + die(kk)
    ej = cj + dje(kk)
    if (ei < 0 .or. ei > ubound(sx%mn, 2) .or. ej < dcp%jsh - 1 .or. ej > dcp%jeh) then
      q = 0.0
    else
      q = sgn8(kk) * sx%mn(ke8(kk), ei, ej)
    end if
  end function

  ! 面値の再構成: 風上側 up、風下側 dn、さらに風上側 upup
  !   スキーム2: 1 次風上(up)
  !   スキーム3: MUSCL  up + ψ(r)/2·(dn - up)、r = (up - upup)/(dn - up)、
  !              ψ = van Leer (r+|r|)/(1+|r|)(r=1 で中心差分、極値で 0)
  pure function face_value(up, dn, upup, upup_ok) result(f)
    real, intent(in) :: up, dn, upup
    logical, intent(in) :: upup_ok       ! upup のエッジの向こうのセルが有効か(偽なら 1 次)
    real :: f
    real :: d, r, psi
    if (opt%f_advection_scheme == 2 .or. .not. upup_ok) then
      f = up
    else
      d = dn - up
      d = d + sign(1.E-10, d)
      r = (up - upup) / d
      psi = (r + abs(r)) / (1 + abs(r))
      f = up + 0.5 * psi * (dn - up)
    end if
  end function

end subroutine


!======================================================================
!======================================================================
!----------------------------------------------------------------------
! 移流項の計算
!----------------------------------------------------------------------
subroutine adv_prepare_v1(p, g, s, sx, tx)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  type(t_enc_status), intent(in) :: sx
  type(t_enc_adv), intent(inout) :: tx

  integer :: i, j, k
  real :: dux, duy, dvx, dvy
  real :: ww(1:8), wwx(1:8), wwy(1:8)
  if (sx%initialized) continue  ! 引数未使用の警告を抑制

  if (opt%f_advection_term == 0) return

  !$omp parallel do schedule(dynamic) private(i, j)
  ! ハロ行の ulm/vlm も構築する(taxy のハロ再計算=案Aに必要。幅2)
  do j = max(dcp%jw1, dcp%js - 2), min(dcp%jw2, dcp%je + 2)
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle   ! get_diffで陸から1セル外側まで参照することに注意
      if (s%h(i,j) < p%dd) cycle
      tx%ulm(i,j) = s%u(i,j) * s%lm(i,j)
      tx%vlm(i,j) = s%v(i,j) * s%lm(i,j)
    end do
  end do
  !$omp end parallel do

  !$omp parallel do schedule(dynamic) private(i, j, k, ww, wwx, wwy, dux, duy, dvx, dvy)
  ! 全域窓の端でのみ1行縮める(dcp%js+1 とはしないこと)。
  ! taxy はハロ行 js-1/je+1 でも再計算する(案A: u,v の交換で賄う)
  do j = max(dcp%js - 1, dcp%jw1 + 1), min(dcp%je + 1, dcp%jw2 - 1)
    do i = g%wx(1,j)+1, g%wx(2,j)-1
      ! 乾湿遷移で前ステップの値が残らないよう毎回クリアする(片乾き
      ! エッジの adv_edge が乾側の古い taxy を読む経路の遮断。拡散項と
      ! 同じ流儀。リスタート再現性の根拠も含め developer.md §21)
      tx%taxy(:,i,j) = 0
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      if (s%h(i,j) < p%dd) cycle
      ! 風上差分による移流項の計算
      ww(:) = get_ww(s%u(i,j), s%v(i,j), s%vv(i,j))
      forall(k=1:8) wwx(k) = geo%w8x(k) * ww(k)
      forall(k=1:8) wwy(k) = geo%w8y(k) * ww(k)
      call get_diff_v1(tx%ulm, tx%vlm, s%h, p%dd, wwx, wwy, g%x, i, j, dux, duy, dvx, dvy)
      tx%taxy(1,i,j) = -(s%u(i,j) * dux + s%v(i,j) * duy)
      tx%taxy(2,i,j) = -(s%u(i,j) * dvx + s%v(i,j) * dvy)
    end do
  end do
  !$omp end parallel do

end subroutine

!----------------------------------------------------------------------
! 風上差分用のウェイトを計算
!----------------------------------------------------------------------
function get_ww(u, v, vv) result(ww_upw)
  real, intent(in) :: u, v
  real, intent(in) :: vv
  integer :: k
  real :: ww_upw(1:8)
  real :: wk
  if (opt%p_adv_upwind_index > 0 .and. vv > 0) then
    do k = 1, 8
      wk = -(u * geo%n8x(k) + v * geo%n8y(k)) / vv                    ! -1~1
      wk = max(1 - (1 - wk) * opt%p_adv_upwind_index / 2, 0.0)    ! 0～1
      ww_upw(k) = wk
    end do
  else
    ww_upw(:) = 1
  end if
end function

!----------------------------------------------------------------------
! 移流項を計算する
!----------------------------------------------------------------------
function adv_edge_v1(s, sx, tx, i, j, k, in, jn) result(ta)
  type(t_state), intent(in) :: s
  type(t_enc_status), intent(in) :: sx
  type(t_enc_adv), intent(in) :: tx
  integer, intent(in) :: i, j, k, in, jn
  real :: ta

  real :: taxe, taye

  if (s%initialized .or. sx%initialized) continue  ! 引数未使用の警告を抑制
  ! 風上差分による移流項
  taxe = (tx%taxy(1,i,j) + tx%taxy(1,in,jn)) / 2  ! 移流項(x方向, 符合は座標軸方向が正)
  taye = (tx%taxy(2,i,j) + tx%taxy(2,in,jn)) / 2  ! 移流項(y方向, 符合は座標軸方向が正)
  ta = taxe * geo%n8x(k) + taye * geo%n8y(k)             ! 移流項(符合は中心セルから近傍セルに向かい正)
end function


!----------------------------------------------------------------------
! 変数u, vの微分
!----------------------------------------------------------------------
subroutine get_diff_v1(u, v, h, dd, wx, wy, x, i, j, dux, duy, dvx, dvy)
  ! u, v, h は帯確保(第2次元下限 dcp%jsh)の配列を大域添字のまま受ける。
  ! 明示形状 (1:nx,1:ny) で受けると、帯確保の実引数が並び結合で再解釈され
  ! 行が jsh-1 だけずれて読まれる(第二段で実発生した実バグ)。
  ! 帯確保の配列を渡す手続きのダミーは必ず assumed-shape + 下限指定にすること
  real, intent(in) :: u(1:, dcp%jsh:)
  real, intent(in) :: v(1:, dcp%jsh:)
  real, intent(in) :: h(1:, dcp%jsh:)
  real, intent(in) :: dd
  real, intent(in) :: wx(1:8), wy(1:8)
  ! x も帯縮小後は下限指定が必須(§12。静的配列への適用第1号)
  integer, intent(in) :: x(0:, dcp%jsh-1:)
  integer, intent(in) :: i, j
  real, intent(out) :: dux, duy
  real, intent(out) :: dvx, dvy

  real :: du, dv
  real :: swx, swy, wwx, wwy
  integer :: in, jn, k

  dux = 0
  duy = 0
  dvx = 0
  dvy = 0
  swx = 0
  swy = 0

  do k = 1, 8
    in = i + din(k)
    jn = j + djn(k)
    if (h(in,jn) < dd) cycle
    wwx = x(in,jn) * wx(k)
    wwy = x(in,jn) * wy(k)
    du = (u(in,jn) - u(i,j))
    dv = (v(in,jn) - v(i,j))
    dux = dux + du * geo%r8x(k) * wwx
    dvx = dvx + dv * geo%r8x(k) * wwx
    duy = duy + du * geo%r8y(k) * wwy
    dvy = dvy + dv * geo%r8y(k) * wwy
    swx = swx + wwx !* din2(k)
    swy = swy + wwy !* djn2(k)
  end do

  if (swx > 0) then
    dux = dux / swx
    dvx = dvx / swx
  end if
  if (swy > 0) then
    duy = duy / swy
    dvy = dvy / swy
  end if

end subroutine

end submodule
