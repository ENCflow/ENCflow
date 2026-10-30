submodule(m_swflow_enc) m_swflow_enc_adv
  use m_state, only : t_state
  use m_parallel, only : dcp   ! 親経由のホスト結合は nvfortran バグ回避のため直接 use
  use m_boundary, only : e_bc_neumann, e_side_w, e_side_e, e_side_n, e_side_s   ! adv_neumann の辺の型
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
    allocate(tx_mod%tae(1:4, dcp%ish-1:dcp%ieh, dcp%jsh-1:dcp%jeh), source = 0.0)
    ! 検査体積の横断幅 = 平行な隣接リンクとの垂直距離(偶奇を問わない)
    !   軸エッジ: k=2(法線 y)は dx、k=4(法線 x)は dy
    !   対角エッジ: dx·dy/dr(dx=dy なら dx/√2)。平行な斜めリンクは t 方向に
    !   この間隔で (i+j) の偶奇が交互に並ぶ。同じ偶奇のリンクとの距離 2·dx·dy/dr
    !   を幅にしていた 2026-10-17 までは、偶数・奇数の副格子で逆回転する斜め
    !   循環に移流項が作用しなかった(§68.36。test/sublattice)
    dr = sqrt(g%dx**2 + g%dy**2)
    tx_mod%w8lt(1:4) = [ g%dx * g%dy / dr, g%dx, g%dx * g%dy / dr, g%dy ]
    return
  end if
  allocate(tx_mod%taxy(1:2, dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  ! TODO(分割時): ulm/vlm/taxy はハロ行でも計算が必要(ステンシル幅2の源。developer.md §11)
  allocate(tx_mod%ulm(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
  allocate(tx_mod%vlm(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
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
!   c-n 間距離、横断幅 w8lt(k) = 平行な隣接リンクとの距離。斜めエッジでは
!   反対偶奇のリンクまでの dx·dy/dr。§68.36)を取り、
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
!     ū は 1 次風上(u_e か、平行な隣接リンクの流速。斜めエッジでは面の
!     前後にある反対偶奇の平行リンク 2 本の平均。§68.36)。
!   - h̄_e = (h_c + h_n)/2(下限 dd/2)。サブグリッド河道(§18・§26)では
!     水量 h×wfrac(σ 有効時 sect_v(h)×wfrac)を使う(§68.9)。lm は v1 と
!     同じ流儀で乗じる(輸送項は dtl = dt/lme の減衰を相殺する。§20)。
!   - 確保範囲外のエッジ・セルは 0 として読む(領域外・無効セルの格納値
!     と同じ扱い。線 k が壁に当たると風上値が 0 = 壁)。
!   - 海セル(§68.35)に接するエッジと、区間流入の法線面を持つ外縁セルから
!     区間の内側へ向かうエッジ(§68.40)は移流項を持たない(規定境界の
!     セル平均流量は検査体積の面流束として整合しない)。流入面に沿うエッジと
!     区間の両端から外へ出るエッジは移流項を残す(§68.40 の改定)。
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
  real :: ue, um, umm, up, upp
  real :: qc, qn, qtp, qtm
  real :: ubc, ubn, ubtp, ubtm
  real :: ta
  logical :: donor_rw               ! このエッジの流下方向の供給元を河道セルに限るか(§68.18)

  !$omp parallel do schedule(dynamic) &
  !$omp private(i, j, k, in, jn, ie, je, hc, hn, hb, lme, ue, um, umm, up, upp, &
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
        ! 海セル(sw>0。水位を強制する規定境界。§23)に接するエッジは移流項を
        ! 持たない。海セルの h は見かけ水柱厚 hsea0(一定)で m, n は 0 なので、
        ! そのエッジの検査体積は水量 h̄ も海側面の流束も実際の水柱と無関係に
        ! なる。沖の水深(9 m)に対し hsea0 = 2 m の examples/tsunami_town では
        ! 海陸エッジの流速が陸側のセル流速の数倍の尺度になり、隣のエッジへの
        ! 流入運動量として読まれて押し波の 10 分で発散した(§68.35)
        if (g%sw(i,j) > 0 .or. g%sw(in,jn) > 0) cycle
        ! 区間流入の法線面を持つ外縁セル(bt_cell = e_bc_inflow)から区間の内側へ
        ! 向かうエッジ(流入面から内側への法線エッジと、区間の幅の中の斜めエッジ。
        ! bc_inflow_inward)も移流項を持たない(海セルと同じ扱い)。流入セルの
        ! 平均流量 (m, n) は、規定面が通過幅 0.414 dx の法線面に区間の全量を通す
        ! (単位幅流量がセル平均の 2.4 倍)うえに枠外の斜めリンクを欠くため、
        ! 検査体積の面流束として整合せず、規定値 uv1 = q/he は内部の運動量と
        ! 無関係な境界値。壁(領域外縁)に挟まれた 5 列の直線河道に区間流入を
        ! 与えると、角セルの閉鎖(§69.9)で中央 3 列に集中した流入が境界行の
        ! 移流項と結合し、スキーム 2・3 とも 5 分周期・±8〜16 % の限界周期振動を
        ! 自励した(奇数幅 3・5・7 列。スキーム 1 は無振動。§68.40。2026-10-24)。
        ! 内側へ向かうエッジの移流項を外せば振動は消える(test/inflowadv)。
        ! 面に沿うエッジ(両端とも流入セル)と区間の両端から外へ出るエッジは
        ! 移流項を残す。2026-10-24〜29 は流入セルに接するエッジをすべて外して
        ! いたが、移流項がないとエッジの流速は水面勾配と摩擦の釣り合いに向かい、
        ! 区間の端へ向かう流れや横の外縁セルへの横溢で、流入セルのエネルギーから
        ! 許される流速を超えた(エネルギーを作った)。容量給砂で河床が固定された
        ! 流入セルの横の外縁セルが掘れると、掘れと境界に沿う噴流の正帰還になり
        ! examples/meander の param_feed が 1:10:47 に Courant 数 1 を超えた
        ! (§68.40 の改定。2026-10-29)。移流項のない内側エッジでも、緩勾配の
        ! 河道では流入直下に射流のジェット(エネルギー水頭を作る)が立つため、
        ! その流速は calc_kth_momentum がエネルギー上限で抑える(§68.40 の改定 2)。
        ! 区間流入のない計算は have_inflow が偽で判定ごと通らない
        if (bcs%have_inflow) then
          if (bc_inflow_inward(i, j, in, jn)) cycle
        end if
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
        ! 側方面の流入流速 ū_t(流出面では u_e。lateral_u)。
        ! 法線エッジ: 平行な隣接エッジ(距離 dx = w8lt)の 1 次風上。
        ! 斜めエッジ: 平行な斜めリンクは t 方向に dx/√2(= w8lt)間隔で偶奇が
        ! 交互に並ぶ。隣接する反対偶奇のリンク 2 本(面の前後に 1 本ずつ)の
        ! 平均を 1 次風上の流入値に使う(1 本しか無い面はその 1 本が面と同程度の
        ! 深さ(1/2〜2 倍)のときだけ使い、浅い岸のリンク・薄い膜の面に深い池の
        ! リンクは壁面扱い。§68.37・§68.39)。同じ偶奇のリンク(距離 √2·dx)だけを
        ! 見ていた 2026-10-17 までは、偶数・奇数の副格子で逆回転する斜め循環
        ! (発散ゼロで圧力項も効かない)に移流項が一切作用せず、低速の滞留域で
        ! 市松模様が残った(§68.36)。滑らかな場では (ū_t − u_e)/w8lt の主要項が
        ! 従来と同一(一様流・段波の整合は不変)で、副格子モードには
        ! |q_t|·2u_e/w8lt の減衰が働く(test/sublattice)
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
        else
          ubtp = lateral_u(i, j, k, 1, ue, hb)
        end if
        if (qtm >= 0) then
          ubtm = ue
        else
          ubtm = lateral_u(i, j, k, -1, ue, hb)
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

  ! 枠外の位置 (ci, cj) が側方 Neumann の辺だけの外なら、辺の法線方向に枠内へ寄せた
  ! 鏡像セル(境界面の運動方程式と同じ。§90)の添字を返す。それ以外はそのまま
  ! (Neumann の辺がなければ常にそのまま = 従来の経路)
  pure subroutine mirror_cell(ci, cj, mi, mj)
    integer, intent(in) :: ci, cj
    integer, intent(out) :: mi, mj
    logical :: ok
    mi = ci
    mj = cj
    if (.not. bcs%have_neumann) return
    if (ci >= 1 .and. ci <= g%nx .and. cj >= 1 .and. cj <= dcp%ny_g) return
    call bc_neumann_cell(ci, cj, ok, mi, mj)
    if (.not. ok) then
      mi = ci
      mj = cj
    end if
  end subroutine

  ! セル (ci, cj) を基準セルとする k 方向エッジの法線流速(確保範囲外は 0)。
  ! 両端のセルがともに側方 Neumann の辺の外のエッジは、基準セルを鏡像へ平行移動した
  ! エッジ(枠内か境界面)を読む(枠外と枠内を結ぶエッジは境界面そのもの。§90)
  pure function uvk(ci, cj, kk) result(u)
    integer, intent(in) :: ci, cj, kk
    real :: u
    integer :: ei, ej, mi, mj
    mi = ci
    mj = cj
    if (bcs%have_neumann) then
      ei = ci + din(kk)
      ej = cj + djn(kk)
      if (ei < 1 .or. ei > g%nx .or. ej < 1 .or. ej > dcp%ny_g) call mirror_cell(ci, cj, mi, mj)
    end if
    ei = mi + die(kk)
    ej = mj + dje(kk)
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

  ! MUSCL の upup の向こうのセルが領域内で有効か(乾湿は見ない)。海セルは
  ! 領域外と同じ(海陸エッジの流速は見かけ水柱厚 hsea0 の尺度で、upup に
  ! 使うと限定器が反拡散側に振れる。§68.35)。ここで見る行は j − 3 .. j + 2
  ! で、g%x(jsh-1:jeh+1)・g%sw(max(1,jsh-1):min(ny,jeh+1)。
  ! m_geoinfo_band_shrink)の確保範囲に収まるので全ランクで同じ判定になる。
  ! sw を jsh:jeh のまま読むと行 j − 3 が帯外読みになり np=1 と np=2 が
  ! 一致しない(2026-10-13 に実発生)
  pure function far_ok(ci, cj) result(ok)
    integer, intent(in) :: ci, cj
    logical :: ok
    integer :: mi, mj
    call mirror_cell(ci, cj, mi, mj)      ! 側方 Neumann の辺の外は鏡像(§90)
    ok = .false.
    if (mi < 1 .or. mi > g%nx .or. mj < 1 .or. mj > dcp%ny_g) return
    ok = g%x(mi,mj) > 0 .and. g%sw(mi,mj) == 0
  end function

  ! セルが運動量の供給元になれるか(確保範囲内・有効・海セルでない・移動限界以上の水深)
  pure function cell_ok(ci, cj) result(ok)
    integer, intent(in) :: ci, cj
    logical :: ok
    integer :: mi, mj
    call mirror_cell(ci, cj, mi, mj)      ! 側方 Neumann の辺の外は鏡像(§90)
    ok = .false.
    if (mi < 1 .or. mi > ubound(s%h, 1) .or. mj < dcp%jsh .or. mj > dcp%jeh) return
    if (g%x(mi,mj) <= 0) return
    if (g%sw(mi,mj) > 0) return      ! 海セルは運動量を供給しない(規定境界。§68.35)
    ok = s%h(mi,mj) >= p%dd
  end function

  ! セルの水深(側方 Neumann の辺の外は鏡像。cell_ok が真のセルにだけ使う)
  pure function hcell(ci, cj) result(h)
    integer, intent(in) :: ci, cj
    real :: h
    integer :: mi, mj
    call mirror_cell(ci, cj, mi, mj)
    h = s%h(mi,mj)
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
    integer :: mi, mj
    ok = cell_ok(ci, cj)
    if (ok .and. drw) then
      call mirror_cell(ci, cj, mi, mj)
      ok = g%rw(mi,mj) > 0
    end if
  end function

  ! 側方面(sgn = ±1 の t 側)の流入流速(1 次風上。供給元が壁・乾床・海なら u_e)。
  !   法線エッジ: 平行な隣接エッジ(c + sgn·δt から kk 方向)。
  !   斜めエッジ: 側方面(距離 dx/√2)の上にある最近接の平行リンク 2 本
  !   (c + sgn·(dti, 0) と c + sgn·(0, dtj) から kk 方向。反対偶奇で、面の前後に
  !   1 本ずつ)の平均。両端セルが有効なリンクだけを使う(§68.36)
  pure function lateral_u(ci, cj, kk, sgn, ue0, he) result(u)
    integer, intent(in) :: ci, cj, kk, sgn
    real, intent(in) :: ue0, he     ! he: 面(エッジ)の検査体積の水深 h̄
    real :: u, usum, u1, h1
    integer :: n, oi, oj
    if (kk == 2 .or. kk == 4) then
      oi = ci + sgn * dti(kk)
      oj = cj + sgn * dtj(kk)
      if (cell_ok(oi, oj) .and. cell_ok(oi + din(kk), oj + djn(kk))) then
        u = uvk(oi, oj, kk)
      else
        u = ue0
      end if
      return
    end if
    usum = 0.0
    n = 0
    u1 = ue0
    h1 = 0.0
    oi = ci + sgn * dti(kk)
    oj = cj
    if (cell_ok(oi, oj) .and. cell_ok(oi + din(kk), oj + djn(kk))) then
      u1 = uvk(oi, oj, kk)
      h1 = 0.5 * (hcell(oi, oj) + hcell(oi + din(kk), oj + djn(kk)))
      usum = usum + u1
      n = n + 1
    end if
    oi = ci
    oj = cj + sgn * dtj(kk)
    if (cell_ok(oi, oj) .and. cell_ok(oi + din(kk), oj + djn(kk))) then
      u1 = uvk(oi, oj, kk)
      h1 = 0.5 * (hcell(oi, oj) + hcell(oi + din(kk), oj + djn(kk)))
      usum = usum + u1
      n = n + 1
    end if
    ! 2 本揃うときは平均。1 本しか無い面は、その 1 本の水深(両端セルの平均)が
    ! 面の水深 h̄ と同程度(h̄/2 以上 2h̄ 以下。壁際の行の隣のリンク)のときだけ
    ! その値を使い、それ以外は壁面と同じ扱い ū = u_e(流入運動量なし)。
    !   - 1 本の値を無条件に使うと(2026-10-17 の初版)、深い湛水の不規則な縁で
    !     浅い岸のリンクの流速が深い横断流束に乗って注入され、反減衰で有限時間
    !     発散した(§68.37。秩父 12 h の出口湛水)
    !   - 1 本しか無い面を無条件に壁面扱いにすると(§68.37 の修正)、壁際の行の
    !     対角エッジが隣のエッジとの運動量交換を失い、乾いた河岸に挟まれた水路で
    !     壁沿いの行が有限時間で加速した(§68.39。test/sedfeed qb: 15 分で
    !     6 m/s、2 m の河岸に水が登る)
    !   - 下限だけ(h1 >= h̄/2)で切ると、池の縁の薄い膜の面(h̄ 0.01〜0.7 m)に
    !     深い池のリンク(1〜6 m、速い)の値が入り、1/h̄ で増幅されて秩父 Step 5
    !     (浸透あり)が 5.75 h で発散した。上限(h1 <= 2h̄)を加えて両方向を
    !     遮ると、水路・池 12 h・Step 5 のすべてが安定(§68.39)
    if (n == 2) then
      u = usum / 2
    else if (n == 1 .and. h1 >= 0.5 * he .and. h1 <= 2.0 * he) then
      u = u1
    else
      u = ue0
    end if
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


!----------------------------------------------------------------------
! 側方 Neumann の境界面の移流項(運動量保存形 f_advection_scheme = 2, 3。§90.19)
!   adv_prepare の後に親が呼ぶ(bcs%adv_neumann が真 = 側方 Neumann の辺があり、移流項が
!   運動量保存形のとき。それ以外は呼ばない = ゼロ追加)。
!   境界面(格子の枠のセル c から枠外の相手 n へ出る面)の検査体積を、内部の面
!   (adv_prepare_mc)と同じ式で、枠外の位置を鏡像セル(bc_neumann_cell。辺の法線方向に
!   枠内へ寄せたセル)で読んで求め、境界面の格納位置 tae(ke8(k), c + de) に書く
!   (put_neumann_face が読む)。法線方向の勾配が 0 なので、線 k 上の枠外のエッジ流速は
!   境界面と同じ(法線の面)か同じ列の境界面(斜めの面)になり、外から入る流れを加速する項を
!   持たない。斜めの面と側方面による岸沖の運動量の交換は内部の面と同じに残る(岸沿いに
!   一様な場では、読む値がすべて一つ内側の面のものと同じになり、同じ値になる)。
!   2026-10-28 までは辺の法線方向に一つ内側の内部の面の値を写していた。辺に向かって強まる
!   流入では、内側の面の移流項(枠外寄りの速い流れが運ばれてくる向き)が境界面の流入を
!   強め、それがまた内側の面の上流の値になる正帰還で発散した(examples/delta の V12 の
!   当初の構成。§90.16)。
!   - 面の選別は put_neumann_faces と同じ(有効・海でない枠のセル、bc_open_face の面、
!     スロット行 js-1..je)。相手 n の鏡像 m は put_neumann_face と同じく枠内へ寄せたセル。
!     m が無効・海セル、c か m が区間流入のセル、両側が乾燥、通過幅ゼロの方位の面は
!     移流項 0(内部の面の除外条件と同じ)。角の外でもう一方の辺が側方 Neumann でない斜めの
!     面(bc_neumann_cell が偽)も 0。
!   - 線 k 上のエッジ、側方面を横切るエッジ、MUSCL と供給元の判定のセルは、枠外の位置を
!     鏡像で読む(両端が枠外のエッジは基準セルを鏡像へ平行移動したエッジ。adv_prepare_mc の
!     mirror_cell・uvk と同じ規則)。
!   - 東西辺の共有行 js-1 / je の面は、隣接する両ランクが同じ入力から冗長に計算する(読む
!     行は j−3..j+3。エッジ流速は交換幅 2 の jsh-1..jeh、流量 mn は js-2..je+1、セルは
!     ハロ 2、g%x・g%sw は jsh-1..jeh+1 の中)。一つ内側の面を写していたときに要った tae の
!     界面補完(par_edge_merge)は要らない。
!   - 式と補助関数は adv_prepare_mc の写しを 8 方向に広げたもの(k = 5..8 は 9 − k の
!     逆向きのエッジ: 符号 sgn8・成分 ke8。側方の近傍 kkp/kkm とオフセット dti/dtj は
!     9 − k のものの ± を入れ替える)。adv_prepare_mc を変えずに別の手続きにする
!     (-Ofast で側方 Neumann のない reference が最終桁でずれないように。§90)
!----------------------------------------------------------------------
module subroutine adv_neumann(p, g, s, sx)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  type(t_enc_status), intent(in) :: sx
  call adv_neumann_mc(p, g, s, sx, tx_mod)
end subroutine


subroutine adv_neumann_mc(p, g, s, sx, tx)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  type(t_enc_status), intent(in) :: sx
  type(t_enc_adv), intent(inout) :: tx
  ! 各辺を横切る面の方位(boundary_uvmn と同じ。1 番目が法線、2・3 番目が斜め)
  integer, parameter :: kfw(1:3) = [4, 1, 6]   ! 西辺(セル (1,j))
  integer, parameter :: kfe(1:3) = [5, 3, 8]   ! 東辺(セル (nx,j))
  integer, parameter :: kfn(1:3) = [2, 1, 3]   ! 北辺(セル (i,1))
  integer, parameter :: kfs(1:3) = [7, 6, 8]   ! 南辺(セル (i,ny))
  integer :: i, j

  ! 辺の走査は boundary_uvmn と同じ(東西辺は自帯+共有行のセル js-1..je+1、南北辺は行の
  ! 所有ランクのみ)。格納の列 0・nx が確保範囲(列窓 ± ハロ)の外なら、その辺に接する有効
  ! セルがないので何もしない(bc_neumann_fwd と同じ)。角の斜め面は二つの辺の走査が同じ値を
  ! 書く
  if (bcs%f_bc_side(e_side_w) == e_bc_neumann .and. dcp%ish == 1) then
    do j = max(dcp%js - 1, 1), min(dcp%je + 1, dcp%ny_g)
      call neumann_cell_faces(1, j, kfw)
    end do
  end if
  if (bcs%f_bc_side(e_side_e) == e_bc_neumann .and. dcp%ieh == dcp%nx_g) then
    do j = max(dcp%js - 1, 1), min(dcp%je + 1, dcp%ny_g)
      call neumann_cell_faces(dcp%nx_g, j, kfe)
    end do
  end if
  if (bcs%f_bc_side(e_side_n) == e_bc_neumann .and. dcp%js <= 1 .and. 1 <= dcp%je) then
    do i = g%wx(1,1), g%wx(2,1)
      call neumann_cell_faces(i, 1, kfn)
    end do
  end if
  if (bcs%f_bc_side(e_side_s) == e_bc_neumann .and. dcp%js <= dcp%ny_g .and. dcp%ny_g <= dcp%je) then
    do i = g%wx(1,dcp%ny_g), g%wx(2,dcp%ny_g)
      call neumann_cell_faces(i, dcp%ny_g, kfs)
    end do
  end if

contains

  ! 枠のセル (ci, cj) の境界面(kf の 3 面)のうち、put_neumann_faces が書く面の移流項
  subroutine neumann_cell_faces(ci, cj, kf)
    integer, intent(in) :: ci, cj
    integer, intent(in) :: kf(1:3)
    integer :: mf, k, in, jn, ie, je, im, jm, kp, km
    real :: hc, hn, hb, lme
    real :: ue, um, umm, up, upp
    real :: qc, qn, qtp, qtm
    real :: ubc, ubn, ubtp, ubtm
    real :: ta
    logical :: donor_rw, ok

    if (g%x(ci,cj) <= 0) return
    if (g%sw(ci,cj) > 0) return
    do mf = 1, 3
      k = kf(mf)
      in = ci + din(k)
      jn = cj + djn(k)
      if (.not. bc_open_face(in, jn)) cycle
      ie = ci + die(k)
      je = cj + dje(k)
      if (je < dcp%js - 1 .or. je > dcp%je) cycle
      tx%tae(ke8(k),ie,je) = 0.0
      ! 相手 n の鏡像(境界面の運動方程式 put_neumann_face と同じ枠内へ寄せたセル)。角の外で
      ! もう一方の辺が側方 Neumann でない斜めの面(放射・自由流出などの辺との角)は、枠外を
      ! 鏡像で読む検査体積が作れないので移流項 0(一つ内側の面を写していた 2026-10-28 までも、
      ! 角の斜めの面の写し元は隣の辺の境界面で 0 だった)
      call bc_neumann_cell(in, jn, ok, im, jm)
      if (.not. ok) cycle
      if (g%x(im,jm) <= 0) cycle
      if (g%sw(im,jm) > 0) cycle
      if (geo%skip8(k)) cycle
      if (bc_inflow_cell(ci, cj) .or. bc_inflow_cell(im, jm)) cycle
      hc = s%h(ci,cj)
      hn = s%h(im,jm)
      if (hc < p%dd .and. hn < p%dd) cycle
      hb = (vol_depth(ci, cj) + vol_depth(im, jm)) / 2
      donor_rw = .false.
      if (opt%f_advection_donor == 1) donor_rw = g%rw(ci,cj) > 0 .and. g%rw(im,jm) > 0

      ! 線 k 上のエッジ流速(k 方向。枠外は鏡像)
      ue  = sgn8(k) * sx%uv(ke8(k),ie,je)
      um  = uvk8(ci - din(k), cj - djn(k), k)
      umm = uvk8(ci - 2 * din(k), cj - 2 * djn(k), k)
      up  = uvk8(in, jn, k)
      upp = uvk8(in + din(k), jn + djn(k), k)

      ! 流向面(c, n)を通る単位幅流量(k 方向投影。n は鏡像のセル)
      qc = s%m(ci,cj) * geo%n8x(k) + s%n(ci,cj) * geo%n8y(k)
      qn = s%m(im,jm) * geo%n8x(k) + s%n(im,jm) * geo%n8y(k)

      ! 流向面の風上化流速(adv_prepare_mc と同じ)
      if (qc >= 0) then
        if (donor_ok(ci - din(k), cj - djn(k), donor_rw)) then
          ubc = face_value(um, ue, umm, far_ok(ci - 2 * din(k), cj - 2 * djn(k)))
        else
          ubc = ue
        end if
      else
        ubc = face_value(ue, um, up, far_ok(in + din(k), jn + djn(k)))
      end if
      if (qn >= 0) then
        ubn = face_value(ue, up, um, far_ok(ci - din(k), cj - djn(k)))
      else
        if (donor_ok(in + din(k), jn + djn(k), donor_rw)) then
          ubn = face_value(up, ue, upp, far_ok(in + 2 * din(k), jn + 2 * djn(k)))
        else
          ubn = ue
        end if
      end if
      ta = -(qn * (ubn - ue) - qc * (ubc - ue)) / geo%w8dr(k)

      ! 側方面(±t)。k = 5..8 の +t 側は 9 − k の −t 側
      if (k <= 4) then
        kp = kkp(k)
        km = kkm(k)
      else
        kp = kkm(9 - k)
        km = kkp(9 - k)
      end if
      qtp = 0.5 * (mnk8(ci, cj, kp) + mnk8(in, jn, kp))
      qtm = 0.5 * (mnk8(ci, cj, km) + mnk8(in, jn, km))
      if (qtp >= 0) then
        ubtp = ue
      else
        ubtp = lateral_u8(ci, cj, k, 1, ue, hb)
      end if
      if (qtm >= 0) then
        ubtm = ue
      else
        ubtm = lateral_u8(ci, cj, k, -1, ue, hb)
      end if
      ta = ta - (qtp * (ubtp - ue) + qtm * (ubtm - ue)) / tx%w8lt(ke8(k))

      lme = (s%lm(ci,cj) + s%lm(im,jm)) / 2
      tx%tae(ke8(k),ie,je) = sgn8(k) * ta / max(hb, p%dd / 2) * lme
    end do
  end subroutine

  ! 枠外の位置 (ci, cj) が側方 Neumann の辺だけの外なら鏡像セルの添字(adv_prepare_mc と同じ)
  pure subroutine mirror_cell(ci, cj, mi, mj)
    integer, intent(in) :: ci, cj
    integer, intent(out) :: mi, mj
    logical :: ok
    mi = ci
    mj = cj
    if (ci >= 1 .and. ci <= g%nx .and. cj >= 1 .and. cj <= dcp%ny_g) return
    call bc_neumann_cell(ci, cj, ok, mi, mj)
    if (.not. ok) then
      mi = ci
      mj = cj
    end if
  end subroutine

  ! セル (ci, cj) からその kk 近傍(kk = 1..8)へ向かうエッジの kk 方向の流速(確保範囲外は 0)。
  ! 遠端が枠外のエッジは基準セルを鏡像へ平行移動したエッジを読む(基準セルが枠内なら境界面
  ! そのもの。uvk と同じ規則)
  pure function uvk8(ci, cj, kk) result(u)
    integer, intent(in) :: ci, cj, kk
    real :: u
    integer :: ei, ej, mi, mj
    mi = ci
    mj = cj
    ei = ci + din(kk)
    ej = cj + djn(kk)
    if (ei < 1 .or. ei > g%nx .or. ej < 1 .or. ej > dcp%ny_g) call mirror_cell(ci, cj, mi, mj)
    ei = mi + die(kk)
    ej = mj + dje(kk)
    if (ei < lbound(sx%uv, 2) .or. ei > ubound(sx%uv, 2) .or. ej < dcp%jsh - 1 .or. ej > dcp%jeh) then
      u = 0.0
    else
      u = sgn8(kk) * sx%uv(ke8(kk),ei,ej)
    end if
  end function

  ! セル (ci, cj) からその kk 近傍へ向かう ENC エッジの単位幅流量(時刻 n の mn。流出が正。
  ! 枠外の扱いは uvk8 と同じ。確保範囲外は 0)
  pure function mnk8(ci, cj, kk) result(q)
    integer, intent(in) :: ci, cj, kk
    real :: q
    integer :: ei, ej, mi, mj
    mi = ci
    mj = cj
    ei = ci + din(kk)
    ej = cj + djn(kk)
    if (ei < 1 .or. ei > g%nx .or. ej < 1 .or. ej > dcp%ny_g) call mirror_cell(ci, cj, mi, mj)
    ei = mi + die(kk)
    ej = mj + dje(kk)
    if (ei < lbound(sx%mn, 2) .or. ei > ubound(sx%mn, 2) .or. ej < dcp%jsh - 1 .or. ej > dcp%jeh) then
      q = 0.0
    else
      q = sgn8(kk) * sx%mn(ke8(kk),ei,ej)
    end if
  end function

  ! セルの単位面積あたり水量(水深換算。adv_prepare_mc と同じ)
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

  ! MUSCL の upup の向こうのセルが領域内で有効か(枠外は鏡像。adv_prepare_mc と同じ)
  pure function far_ok(ci, cj) result(ok)
    integer, intent(in) :: ci, cj
    logical :: ok
    integer :: mi, mj
    call mirror_cell(ci, cj, mi, mj)
    ok = .false.
    if (mi < 1 .or. mi > g%nx .or. mj < 1 .or. mj > dcp%ny_g) return
    ok = g%x(mi,mj) > 0 .and. g%sw(mi,mj) == 0
  end function

  ! セルが運動量の供給元になれるか(枠外は鏡像。adv_prepare_mc と同じ)
  pure function cell_ok(ci, cj) result(ok)
    integer, intent(in) :: ci, cj
    logical :: ok
    integer :: mi, mj
    call mirror_cell(ci, cj, mi, mj)
    ok = .false.
    if (mi < lbound(s%h, 1) .or. mi > ubound(s%h, 1) .or. mj < dcp%jsh .or. mj > dcp%jeh) return
    if (g%x(mi,mj) <= 0) return
    if (g%sw(mi,mj) > 0) return
    ok = s%h(mi,mj) >= p%dd
  end function

  ! セルの水深(枠外は鏡像。cell_ok が真のセルにだけ使う)
  pure function hcell(ci, cj) result(h)
    integer, intent(in) :: ci, cj
    real :: h
    integer :: mi, mj
    call mirror_cell(ci, cj, mi, mj)
    h = s%h(mi,mj)
  end function

  ! 流下方向の風上供給元になれるか(adv_prepare_mc と同じ。drw は引数で受ける)
  pure function donor_ok(ci, cj, drw) result(ok)
    integer, intent(in) :: ci, cj
    logical, intent(in) :: drw
    logical :: ok
    integer :: mi, mj
    ok = cell_ok(ci, cj)
    if (ok .and. drw) then
      call mirror_cell(ci, cj, mi, mj)
      ok = g%rw(mi,mj) > 0
    end if
  end function

  ! 側方面(sgn = ±1 の t 側)の流入流速(adv_prepare_mc の lateral_u を 8 方向に広げたもの)
  pure function lateral_u8(ci, cj, kk, sgn, ue0, he) result(u)
    integer, intent(in) :: ci, cj, kk, sgn
    real, intent(in) :: ue0, he
    real :: u, usum, u1, h1
    integer :: n, oi, oj, ti, tj
    if (kk <= 4) then
      ti = sgn * dti(kk)
      tj = sgn * dtj(kk)
    else
      ti = -sgn * dti(9 - kk)
      tj = -sgn * dtj(9 - kk)
    end if
    if (kk == 2 .or. kk == 4 .or. kk == 5 .or. kk == 7) then
      oi = ci + ti
      oj = cj + tj
      if (cell_ok(oi, oj) .and. cell_ok(oi + din(kk), oj + djn(kk))) then
        u = uvk8(oi, oj, kk)
      else
        u = ue0
      end if
      return
    end if
    usum = 0.0
    n = 0
    u1 = ue0
    h1 = 0.0
    oi = ci + ti
    oj = cj
    if (cell_ok(oi, oj) .and. cell_ok(oi + din(kk), oj + djn(kk))) then
      u1 = uvk8(oi, oj, kk)
      h1 = 0.5 * (hcell(oi, oj) + hcell(oi + din(kk), oj + djn(kk)))
      usum = usum + u1
      n = n + 1
    end if
    oi = ci
    oj = cj + tj
    if (cell_ok(oi, oj) .and. cell_ok(oi + din(kk), oj + djn(kk))) then
      u1 = uvk8(oi, oj, kk)
      h1 = 0.5 * (hcell(oi, oj) + hcell(oi + din(kk), oj + djn(kk)))
      usum = usum + u1
      n = n + 1
    end if
    if (n == 2) then
      u = usum / 2
    else if (n == 1 .and. h1 >= 0.5 * he .and. h1 <= 2.0 * he) then
      u = u1
    else
      u = ue0
    end if
  end function

  ! 面値の再構成(adv_prepare_mc と同じ)
  pure function face_value(up, dn, upup, upup_ok) result(f)
    real, intent(in) :: up, dn, upup
    logical, intent(in) :: upup_ok
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
  real, intent(in) :: u(dcp%ish:, dcp%jsh:)
  real, intent(in) :: v(dcp%ish:, dcp%jsh:)
  real, intent(in) :: h(dcp%ish:, dcp%jsh:)
  real, intent(in) :: dd
  real, intent(in) :: wx(1:8), wy(1:8)
  ! x も帯縮小後は下限指定が必須(§12。静的配列への適用第1号)。列も ish-1 から
  ! (g%x は ish-1..ieh+1 で確保。0: のままだと窓が列 1 から始まらないケースで
  ! 列が ish-1 だけずれて読まれる実バグ。§80)
  integer, intent(in) :: x(dcp%ish-1:, dcp%jsh-1:)
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
