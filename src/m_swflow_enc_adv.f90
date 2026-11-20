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
  ! 流れごとの重み(f_advection_donor = 4)と流量の似かより(f_advection_lateral = 2)の、流量の比のしきい κ。
  ! 「κ 倍までの違いは、同じ流れとみなす」。一様な流れで、流れの向きから ±61° 以内の辺の重みが 1 になる値
  ! (stream_share の注。ENCflow 独自。developer.md §113)
  real, parameter :: p_stream_kappa = 2.0
  real, parameter :: sgn8(1:8) = [ 1., 1., 1., 1., -1., -1., -1., -1. ]
  integer, parameter :: kkp(1:4) = [ 3, 5, 8, 2 ]   ! +t 側に隣接するセルの 8 近傍番号
  integer, parameter :: kkm(1:4) = [ 6, 4, 1, 7 ]   ! -t 側
  ! 軸エッジ k の ±t 側方面を横切る斜めリンク(c 側: (±t, +k) 方向、n 側: (±t, −k) 方向)
  ! の 8 近傍番号。k = 5, 7(adv_neumann_mc の逆向き)は 9 − k の面の c, n を入れ替えたもの。
  ! 斜めエッジ(1, 3, 6, 8)は使わない(0)
  integer, parameter :: kdp_c(1:8) = [ 0, 3, 0, 1, 8, 0, 6, 0 ]   ! +t 面、c 側
  integer, parameter :: kdp_n(1:8) = [ 0, 8, 0, 3, 6, 0, 1, 0 ]   ! +t 面、n 側
  integer, parameter :: kdm_c(1:8) = [ 0, 1, 0, 6, 3, 0, 8, 0 ]   ! −t 面、c 側
  integer, parameter :: kdm_n(1:8) = [ 0, 6, 0, 8, 1, 0, 3, 0 ]   ! −t 面、n 側
  ! 斜めエッジ k(1, 3。側方 Neumann の逆向きは 6, 8)の ±t 側方面を横切る軸リンクの 8 近傍番号
  ! (c 側は c から面を前方へ横切る軸リンク、n 側は n から後方へ横切る軸リンク。斜めエッジの
  ! 側方面の開口率に使う。§68.43)。軸エッジ(2, 4, 5, 7)は使わない(0)
  integer, parameter :: pax_c(1:8) = [ 2, 0, 5, 0, 0, 4, 0, 7 ]   ! +t 面、c 側
  integer, parameter :: pax_n(1:8) = [ 5, 0, 7, 0, 0, 2, 0, 4 ]   ! +t 面、n 側
  integer, parameter :: nax_c(1:8) = [ 4, 0, 2, 0, 0, 7, 0, 5 ]   ! −t 面、c 側
  integer, parameter :: nax_n(1:8) = [ 7, 0, 4, 0, 0, 5, 0, 2 ]   ! −t 面、n 側
  integer, parameter :: dti(1:4) = [ 1, 1, 1, 0 ]
  integer, parameter :: dtj(1:4) = [ -1, 0, 1, -1 ]

contains
!----------------------------------------------------------------------
! 移流項の内部場の確保
!----------------------------------------------------------------------
module subroutine adv_init(p, g, b)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(in) :: b
  real :: dr
  integer :: l, kk, n, i, j
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
    ! 斜めエッジの側方面を横切る軸リンク 1 本が面の流束に占める割合(流向の方向平均。
    ! 正方セルで ldx = ldy = p_diagratio/2 = 0.293。§68.43 の開口率)
    tx_mod%cwd = 0.5 * (geo%ldx + geo%ldy)
    ! 流れごとの重み(f_advection_donor = 4。§113)の幾何の表。面のセルへ l 近傍から入る実流量 Q_l(m³/s)が、
    ! セルの平均の単位幅流量 (m, n) の、kk 近傍から面のセルへ向かう向きの成分に占める分は
    ! Q_l (w8mx(l) n8x(kk) + w8my(l) n8y(kk)) / l8(l)(m, n の合成の重みと同じ。calc_continuity)。これに検査体積の
    ! 横断幅 w8lt を掛けたものが、面の流束(m³/s)に占める分になる。直交する連結の値は、丸めの大きさの数に
    ! なり得るので、最大の 1e-6 倍に満たない値は 0 にそろえる(前向き・直交・後ろ向きの区別を、丸めで決めない)
    if (opt%adv_stream) then
      allocate(tx_mod%gst(1:8, 1:8), source = 0.0)
      do kk = 1, 8
        do l = 1, 8
          if (geo%l8(l) <= 0.0) cycle
          tx_mod%gst(l,kk) = (geo%w8mx(l) * geo%n8x(kk) + geo%w8my(l) * geo%n8y(kk)) * tx_mod%w8lt(ke8(kk)) / geo%l8(l)
        end do
      end do
      where (abs(tx_mod%gst) <= 1.0e-6 * maxval(abs(tx_mod%gst))) tx_mod%gst = 0.0
    end if
    ! 連結の実流量の表(毎ステップ adv_prepare_mc が作る。セルの確保範囲。§113.7)
    if (opt%adv_stream .or. opt%adv_energy .or. opt%adv_latflux) then
      allocate(tx_mod%ql(1:8, dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = 0.0)
    end if
    ! 流れごとの重みの控え(エッジの確保範囲。§113.7)
    if (opt%adv_stream .and. opt%f_advection_bend > 0) then
      allocate(tx_mod%wst(1:2, 1:4, dcp%ish-1:dcp%ieh, dcp%jsh-1:dcp%jeh), source = -1.0)
    end if
    ! 境界として与えたセル(水位規定セルと、湧き出し・吸い込みのセル)の印(f_advection_bend = 2 か
    ! f_advection_lateral = 2 で、どちらかがあるときだけ。§113.9)。セルの並びは全ランクが同じものを持つ(m_boundary)
    ! ので、自分の確保範囲に入るセルだけに印を付ける
    if ((opt%adv_energy .or. opt%adv_latflux) .and. (b%nstage > 0 .or. b%nsrc > 0)) then
      allocate(tx_mod%gvn(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh), source = .false.)
      do n = 1, b%nstage
        do l = 1, b%stage(n)%ncell
          i = b%stage(n)%cell(1,l)
          j = b%stage(n)%cell(2,l)
          if (i < dcp%ish .or. i > dcp%ieh .or. j < dcp%jsh .or. j > dcp%jeh) cycle
          tx_mod%gvn(i,j) = .true.
        end do
      end do
      do n = 1, b%nsrc
        do l = 1, b%src(n)%ncell
          i = b%src(n)%cell(1,l)
          j = b%src(n)%cell(2,l)
          if (i < dcp%ish .or. i > dcp%ieh .or. j < dcp%jsh .or. j > dcp%jeh) cycle
          tx_mod%gvn(i,j) = .true.
        end do
      end do
    end if
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
    ! 屈曲直後の辺の慣性(f_advection_bend = 1。§110)。内部の面の tae に差分を足す
    if (opt%f_advection_bend > 0) call adv_bend_mc(p, g, s, sx, tx_mod, .false.)
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
  if (allocated(tx_mod%gst)) deallocate(tx_mod%gst)
  if (allocated(tx_mod%ql)) deallocate(tx_mod%ql)
  if (allocated(tx_mod%wst)) deallocate(tx_mod%wst)
  if (allocated(tx_mod%gvn)) deallocate(tx_mod%gvn)
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
!     前後にある反対偶奇の平行リンク 2 本の平均。§68.36)。f_advection_donor = 3
!     では平行リンクの乾湿判定を dd 未満で連続な重みにする(lateral_u_w。§102)。
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
  real :: wsh                       ! 線 k の供給元の重み(f_advection_donor = 3。§102)
  logical :: tab                    ! 連結の実流量の表 tx%ql を読むか(§113.7)
  logical :: wsv                    ! 流れごとの重みを tx%wst に控えるか(adv_bend_mc が読む。§113.7)

  ! 連結の実流量の表(f_advection_donor = 4・f_advection_bend = 2・f_advection_lateral = 2 の有効時だけ。§113.7)と、
  ! 流れごとの重みの控え(f_advection_donor = 4 で、f_advection_bend が 1 以上のときだけ)
  tab = allocated(tx%ql)
  if (tab) call fill_links()
  wsv = allocated(tx%wst)

  !$omp parallel do schedule(dynamic) &
  !$omp private(i, j, k, in, jn, ie, je, hc, hn, hb, lme, ue, um, umm, up, upp, &
  !$omp         qc, qn, qtp, qtm, ubc, ubn, ubtp, ubtm, ta, wsh)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      do k = 1, 4
        in = i + din(k)
        jn = j + djn(k)
        ie = i + die(k)
        je = j + dje(k)
        tx%tae(k,ie,je) = 0.0
        if (wsv) tx%wst(1:2,k,ie,je) = -1.0      ! 重みの控えを「計算していない」に戻す(§113.7)
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
        ! 区間流入の法線面を持つ外縁セル(bt_cell = e_bc_inflow)に接するエッジも
        ! 移流項を持たない(海セルと同じ扱い)。流入セルの平均流量 (m, n) は、
        ! 規定面が通過幅 0.414 dx の法線面に区間の全量を通す(単位幅流量が
        ! セル平均の 2.4 倍)うえに枠外の斜めリンクを欠くため、検査体積の面流束
        ! として整合せず、規定値 uv1 = q/he は内部の運動量と無関係な境界値。
        ! 壁(領域外縁)に挟まれた 5 列の直線河道に区間流入を与えると、角セルの
        ! 閉鎖(§69.9)で中央 3 列に集中した流入が境界行の移流項と結合し、
        ! スキーム 2・3 とも 5 分周期・±8〜16 % の限界周期振動を自励した
        ! (奇数幅 3・5・7 列。スキーム 1 は無振動)。境界行に触れるエッジの
        ! 移流項を外すと幅 3・5・7 とも 0.00 % になる(§68.40。2026-10-24)。
        ! f_inflow_edge = 1・2 は外すのを流入セルから区間の内側へ向かうエッジ
        ! (bc_inflow_inward。流入面から内側への法線エッジと、区間の幅の中の斜め
        ! エッジ)だけにし、面に沿うエッジと区間の両端から外へ出るエッジは移流項を
        ! 残す。移流項がないとエッジの流速は水面勾配と摩擦の釣り合いに向かい、
        ! 区間の端から横へ落ちる流れが流入セルのエネルギーから許される流速を超える
        ! (examples/meander の param_feed が 1:10:47 に Courant 数 1 を超えた。
        ! §68.40 の改定)。2 は内側へ向かうエッジの流速を calc_kth_momentum が
        ! エネルギー水頭で頭打ちする(流入直下の射流のジェット。§68.40 の改定 2)。
        ! 区間流入のない計算は have_inflow が偽で判定ごと通らない
        if (bcs%have_inflow) then
          if (opt%f_inflow_edge == 0) then
            if (bc_inflow_cell(i, j) .or. bc_inflow_cell(in, jn)) cycle
          else
            if (bc_inflow_inward(i, j, in, jn)) cycle
          end if
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
        ! f_advection_donor = 3: 線 k 上の供給元のリンクが面のセルへ運ぶ実流量 Q_k が、面のセルへの
        ! 最大の流入リンクの実流量 Q_max の ε(p_adv_donor_eps)倍に満たず、かつ供給元が薄い(水深が
        ! 面のセルの水深の ε 倍未満)ときだけ、MUSCL の風上値を u_e へ寄せる(ū = u_e + w(ū_k − u_e)、
        ! w = max((Q_k/Q_max)/ε, (h_d/h_c)/ε)。w = 1 なら 0 と同じ値。donor_share。§102)。
        ! 線 k 上の 1 本のリンクの流速に面の全流束を掛ける取り方だと、線上の
        ! リンクが河岸の薄い水膜で面の流束の主部が斜めのリンクから来るとき、「深いセルの質量流束 ×
        ! 薄いリンクの流速」の人工的な減速になり、水膜の乾湿判定(cell_ok)の切り替わりで減速が
        ! 一度に外れてハイドログラフの跳ねになる(tutorials/chichibu Step 3 の 232 min)。3 はこの
        ! 減速だけを消し、他のリンクの水の運動量は持ち込まない(面のセルへの全流入リンクの流量で
        ! 重み付けした平均を風上値にする旧 2 は持ち込むので、河岸の段差をまたぐ交換リンクへ本流の
        ! 運動量が注入されて横流入の水路が深くなり、渦・壁の検定も悪くした。2026-11-07 廃止。§102)
        if (qc >= 0) then
          if (cell_ok(i - din(k), j - djn(k))) then
            ubc = face_value(um, ue, umm, far_ok(i - 2 * din(k), j - 2 * djn(k)))
            if (opt%f_advection_donor == 3) then
              wsh = donor_share(i, j, 9 - k)      ! 面のセル c と線 k の供給元 c − d(c の 9 − k 近傍)
              if (opt%adv_stream) then
                wsh = stream_share(i, j, 9 - k, qc, wsh)
                if (wsv) tx%wst(1,k,ie,je) = wsh
              end if
              if (wsh < 1.0) ubc = ue + wsh * (ubc - ue)
            end if
          else
            ubc = ue
          end if
        else
          ubc = face_value(ue, um, up, far_ok(in + din(k), jn + djn(k)))
        end if
        if (qn >= 0) then
          ubn = face_value(ue, up, um, far_ok(i - din(k), j - djn(k)))
        else
          if (cell_ok(in + din(k), jn + djn(k))) then
            ubn = face_value(up, ue, upp, far_ok(in + 2 * din(k), jn + 2 * djn(k)))
            if (opt%f_advection_donor == 3) then
              wsh = donor_share(in, jn, k)        ! 面のセル n と線 k の供給元 n + d(n の k 近傍)
              if (opt%adv_stream) then
                wsh = stream_share(in, jn, k, -qn, wsh)
                if (wsv) tx%wst(2,k,ie,je) = wsh
              end if
              if (wsh < 1.0) ubn = ue + wsh * (ubn - ue)
            end if
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
        ! 軸エッジの側方面の流束は、面を横切るリンクの実流量(連続式が水深変化に換算する
        ! mn·l8·fw)の和を面の長さ w8dr で割る: c, n の ±t 軸リンク(通過幅 lp の帯は面の
        ! 半分ずつ)と、c の (±t, +k)・n の (±t, −k) の斜めリンク(帯の全幅)。一様流では
        ! 軸 0.414 + 斜め 2×0.293 = 1 で従来の ½(mn_c + mn_n)·w8dr と厳密に一致し、斜め
        ! リンクが地形・壁で塞がれる面では軸リンクの実流量だけになる。単位幅流量 mn に面の
        ! 全長を掛けていた 2026-10-31 までは、斜めが塞がれた面で実流量の 1/lp = 2.4 倍
        ! (動的振り替え fwd で 1.4〜1.7 倍)の水が横切る扱いになり、質量と整合しない
        ! 運動量の注入が深い湛水の縁(段々の棚と溝が壁に挟まれた支谷の口)のヘルムホルツ型
        ! の振動を反減衰にして有限時間で発散した(tutorials/chichibu Step 5 の 5:14 h、
        ! 出口湛水 12 h の 10:42 h。f_opening_dynamic 2 では fwd の分だけ遅いだけ。§68.42)。
        ! 斜めエッジの側方面は従来の ½(mn_c + mn_n)·w8dr(直交する斜めリンク = 同じ族の
        ! 流量で標本。一様流で厳密。斜めが塞がれた面では過小 = 散逸側)に、面を横切る軸リンク
        ! の開口率 φ = 1 − cwd × (壁・乾床で塞がれた横切り軸リンクの本数。c 側・n 側の各 1 本)を
        ! 掛ける。両方塞がれば 0.414 で、斜めリンクだけが開く面の過大評価(従来 2.4 倍)が消える。
        ! 横切るリンクの実流量の和に置き換える案(軸エッジと同じ式)は、どの定式でも dambreak の
        ! 段波を 1.5〜5 % 遅らせる(斜めリンクの族の運動量流入が軸リンクの位置で評価されて
        ! 族ごとに流速が分かれる)ので採らない(§68.43)
        if (k == 2 .or. k == 4) then
          if (tab) then                 ! 表から読む(同じ値。§113.7)
            qtp = (0.5 * (tx%ql(kkp(k),i,j) + tx%ql(kkp(k),in,jn)) &
                   + tx%ql(kdp_c(k),i,j) + tx%ql(kdp_n(k),in,jn)) / geo%w8dr(k)
            qtm = (0.5 * (tx%ql(kkm(k),i,j) + tx%ql(kkm(k),in,jn)) &
                   + tx%ql(kdm_c(k),i,j) + tx%ql(kdm_n(k),in,jn)) / geo%w8dr(k)
          else
            qtp = (0.5 * (qlk(i, j, kkp(k)) + qlk(in, jn, kkp(k))) &
                   + qlk(i, j, kdp_c(k)) + qlk(in, jn, kdp_n(k))) / geo%w8dr(k)
            qtm = (0.5 * (qlk(i, j, kkm(k)) + qlk(in, jn, kkm(k))) &
                   + qlk(i, j, kdm_c(k)) + qlk(in, jn, kdm_n(k))) / geo%w8dr(k)
          end if
        else
          qtp = axis_open(i, j, k, 1) * 0.5 * (mnk(i, j, kkp(k)) + mnk(in, jn, kkp(k)))
          qtm = axis_open(i, j, k, -1) * 0.5 * (mnk(i, j, kkm(k)) + mnk(in, jn, kkm(k)))
        end if
        ! 側方面も同様: 平行な隣接エッジの両セルが有効・湿潤のときだけ
        ! その流速を流入値に使う(壁・乾床側からは ū = u_e)
        ! f_advection_donor = 3 は、この乾湿判定(水深 ≥ dd で有効、未満で無効の切り替え)と斜めエッジの
        ! 開口率 axis_open の乾湿判定を、dd 未満では水深に比例して中立へ寄せる連続な重み min(1, h/dd)
        ! にする(lateral_u_w・wet_weight。dd 以上の水深では 0 と同じ値)。河岸の水膜が dd を割った瞬間に
        ! 平行リンクの遅い流速による減速が一度に外れ、ハイドログラフの跳ねになるのを防ぐ
        ! (tutorials/chichibu 200 m の測線 3 の 120 min・測線 4 の 310 min。§102)
        ! f_advection_lateral = 1(f_advection_donor = 3 が前提)は、平行リンクが、面を横切って入ってくる水に
        ! 比べて薄い水膜のとき、その流速を使わず(代表性 R'。lateral_rep)、辺の線に沿う流れへ別の向きから
        ! 入る水の、辺の向きの運動量の不足を数える(lateral_join)。斜めエッジの開口率 axis_open も、横切る
        ! 軸リンクの向こうのセルを同じ R' で数える(lateral_u_j。developer.md §110.25)
        if (qtp >= 0) then
          ubtp = ue
        else if (opt%f_advection_lateral == 1) then
          ubtp = lateral_u_j(i, j, k, 1, ue, hb)
        else if (opt%f_advection_donor == 3) then
          ubtp = lateral_u_w(i, j, k, 1, ue, hb)
        else
          ubtp = lateral_u(i, j, k, 1, ue, hb)
        end if
        if (qtm >= 0) then
          ubtm = ue
        else if (opt%f_advection_lateral == 1) then
          ubtm = lateral_u_j(i, j, k, -1, ue, hb)
        else if (opt%f_advection_donor == 3) then
          ubtm = lateral_u_w(i, j, k, -1, ue, hb)
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

  ! 連結の実流量の表 tx%ql を作る(developer.md §113.7。結果を変えない): ql(l, i, j) = qlk(i, j, l)。
  !   面ごと・関数ごとに qlk を計算し直す代わりに、供給元の重み(donor_share)・斜めの流入元の向き(src_fwd)・
  !   軸エッジの側方面の流束と流入(lateral_inflow)・line_flow と、adv_bend_mc の経路の値・到着した水の速さ・
  !   供給元の重みと src_fwd の写しが読む(同じ式・同じ時刻の値。面ごとに計算すると、1 つのセルの 8 本の連結を、
  !   そのセルを面のセルとする面の数 × 関数の数だけ読み直すことになる)。流れごとの重み stream_share だけは、
  !   表を読まない(理由は stream_share のコメント)。
  !   - 作る範囲。表を読むセルは、計算する面のセル(c・n のどちらかが濡れている = 水深が dd 以上)、その 8 近傍の
  !     セル(src_fwd)、濡れたセル(line_flow)で、どれも、濡れたセルから行・列とも 2 つ以内にある。そこで、行ごとに
  !     濡れたセルの列の範囲を調べ、行 j − 2 .. j + 2 の範囲を合わせて ± 2 列に広げた所だけを作る(濡れたセルが
  !     河道だけの計算で、乾いた所の表を作らない)。範囲の外の表は、前のステップの値のまま残るが、読まれない。
  !   - 行は、セルの確保範囲 jsh .. jeh(表を読むセルの行は js − 2 .. je + 1。側方 Neumann の境界面の屈曲では
  !     je + 1 の枠のセルも読む)、列は ish .. ieh で切る。確保範囲の外のエッジは、qlk が 0 と読む(面ごとに計算して
  !     いたときと同じ)。濡れたセルの判定は、面を計算するかどうかの判定(水深 s%h が dd 以上)と同じ
  subroutine fill_links()
    integer :: fi, fj, fl, i1, i2, jj
    integer :: wa(dcp%jsh:dcp%jeh), wb(dcp%jsh:dcp%jeh)     ! 行ごとの、濡れたセルの列の範囲(なければ wa > wb)
    !$omp parallel private(fi, fj, fl, i1, i2, jj)
    !$omp do schedule(static)
    do fj = dcp%jsh, dcp%jeh
      i1 = dcp%ieh + 1
      i2 = dcp%ish - 1
      do fi = g%wx(1,fj), g%wx(2,fj)
        if (s%h(fi,fj) >= p%dd) then
          i1 = min(i1, fi)
          i2 = fi
        end if
      end do
      wa(fj) = i1
      wb(fj) = i2
    end do
    !$omp end do
    !$omp do schedule(static)
    do fj = dcp%jsh, dcp%jeh
      i1 = dcp%ieh + 1
      i2 = dcp%ish - 1
      do jj = max(fj - 2, dcp%jsh), min(fj + 2, dcp%jeh)
        if (wa(jj) <= wb(jj)) then
          i1 = min(i1, wa(jj) - 2)
          i2 = max(i2, wb(jj) + 2)
        end if
      end do
      do fi = max(i1, dcp%ish), min(i2, dcp%ieh)
        do fl = 1, 8
          tx%ql(fl,fi,fj) = qlk(fi, fj, fl)
        end do
      end do
    end do
    !$omp end do
    !$omp end parallel
  end subroutine

  ! 線 k の供給元の重み(f_advection_donor = 3。developer.md §102)。面のセル (ci, cj) へ線 k 上の
  ! 供給元(kk 近傍)から入る実流量 Q_k と、面のセルへの 8 リンクの流入の最大 Q_max の比
  ! r = Q_k/Q_max に対し w_r = min(1, r/ε)(ε = p_adv_donor_eps)。面のセルへの流入がなければ 1。
  ! 薄い供給元に限る: w_r < 1 でも、供給元の水深 h_d が面のセルの水深 h_c の ε 倍以上なら寄せない
  ! (w = 1 = 0 と同じ)。それ未満は w = max(w_r, h_d/(ε h_c))(水膜が薄くなるほど流量比の重みに
  ! 近づく)。流量比だけだと、平坦部の深い淀み(流入の 1 割前後)を供給元とする本流の面で r が ε の
  ! 境目を行き来し、重みが 0 と 1 で切り替わって区間が振動した(補足の 100 m・幅 50 m の測線 2。§102)。
  ! 読むのは面のセル(行 j − 1・j)の 8 リンクの qlk(時刻 n の mn。エッジ幅 2 の交換済み)と、面の
  ! セルと供給元の水深(hcell。呼び出し側の cell_ok と同じく、側方 Neumann の辺の外は鏡像のセルを
  ! 読む。辺の外のハロを s%h で直接読むと、リスタートの継続が通し計算と一致しなかった。test/wfcurrent・
  ! wfsed。§102)だけで、エッジの行は j − 2 .. j(MPI の np = 1・2・4 が逐次とバイト一致。§102)。海セルからの流入も最大に数える(海セルは
  ! 運動量を供給しないので、寄せる側 = u_e で安全)。
  ! 割り算は Q_k < εQ_max のときだけ行う(商は 1 未満)。Q_max が正でも極小のとき εQ_max が 0 に
  ! アンダーフローして 0 で割る(-ffpe-trap=zero で停止。test/slopefric の計算開始直後)ことを避ける。
  ! 水深の比も h_d < εh_c のときだけ割る(面のセルが乾いていれば εh_c = 0 で w = 1)
  pure function donor_share(ci, cj, kk) result(w)
    integer, intent(in) :: ci, cj, kk
    real :: w, qk, qmax, qe, hd, he
    integer :: l
    if (tab) then                     ! 表から読む(同じ値。§113.7)
      qk = max(0.0, -tx%ql(kk,ci,cj))
      qmax = 0.0
      do l = 1, 8
        qmax = max(qmax, -tx%ql(l,ci,cj))
      end do
    else
      qk = max(0.0, -qlk(ci, cj, kk))
      qmax = 0.0
      do l = 1, 8
        qmax = max(qmax, -qlk(ci, cj, l))
      end do
    end if
    qe = opt%p_adv_donor_eps * qmax
    w = 1.0
    if (qk < qe) then
      w = qk / qe
      hd = hcell(ci + din(kk), cj + djn(kk))        ! 供給元の水深(辺の外は鏡像。cell_ok と同じセル)
      he = opt%p_adv_donor_eps * hcell(ci, cj)      ! 面のセルの水深の ε 倍
      if (hd >= he) then
        w = 1.0
      else
        w = max(w, hd / he)
      end if
    end if
  end function

  ! 流れごとの重み(f_advection_donor = 4。developer.md §112.3・§113。ENCflow 独自)。
  !   3 の重み(donor_share)は、線 k の供給元が薄い水膜でなければ 1 で、線 k の連結の流速を、面を通る流束の全量に
  !   掛ける。面のセルへの水のほとんどが別の連結から来て、線 k の連結が、深くて遅い岸・淵のセルにつながっている
  !   とき、これは「面の全量 × 遅い連結の流速」の人工的な減速になり、岸や淵が濡れると働くので、同じ流量に 2 つの
  !   水深ができる(test/stairbank。§112.1)。4 は、面の流束 F を、面のセルへ入ってくる連結 l ごとの流れに分け、
  !   線 k の連結の流速を、その連結が代表する流れの分だけに掛ける:
  !     F_l = g_l Q_l + (F − Σ g_l Q_l) Q_l / Σ Q_l      (Q_l: l からの流入の実流量。g_l: 幾何の表 gst。第 2 項は、
  !                                                        面の流束のうち流出の側の分を、流入の割合で配ったもの)
  !     w   = Σ ω_l F_l / Σ F_l                         (F_l > 0 の流れについて。0 ≤ w ≤ 1)
  !     ω_l = 1                                          線 k の連結(l = kk)
  !         = θ_l + (1 − θ_l)(1 − ω_o) w_3               前向きの斜めの連結(g_l > 0)。θ_l = min(1, κ Q_k / Q_l)
  !         = w_3                                        直交・後ろ向きの連結(g_l ≤ 0)。w_3 は 3 の重み
  !   - θ_l: 線 k の連結が、前向きの斜めの流れの 1/κ 以上の流量を運んでいれば、その流れも代表する(θ = 1)。
  !     一様な流れでは、線 k の連結と前向きの斜めの連結の流量の比は cos φ / cos(φ − 45°)(φ は流れと辺のなす角)で、
  !     辺が流れの向きから ±45° 以内なら 0.707 以上になる。κ = 2 は、しきいを 0.5(±61° 以内)に置いて、一様で
  !     ない流れにも余裕を持たせた値(p_stream_kappa。1〜2 で結果はほとんど変わらない。§112.11)。格子で
  !     解像された流れは w = 1(3・0 と同じ)になり、線 k の連結がほとんど水を運ばない面だけが中立へ寄る。
  !   - ω_o: 斜めの流入元のセルへの流入のうち、辺の向きに前向きの連結から入った割合(src_fwd)。1 なら、斜めの
  !     流れは、同じ河道の階段を辺の向きに流れてきた水で、線 k の連結の遅い流速を掛けない。0 なら、別の向きから
  !     来た水(支川)が斜めに入るので、直交して入る流れと同じ扱い(w_3)にする。これがないと、45° 回した合流で、
  !     合流の上流の水深が、損失なしの理論より浅くなる(エネルギーが増える。§112.11)。
  !   - 重みが 1 より小さい分は中立(ū = u_e)で、f_advection_bend が経路の値(と、2 ではエネルギー形の項)を足す。
  !   - 分ける元の流れが、取るに足らない大きさのときは、w を w_3 へ寄せる(ε = p_adv_donor_eps。§113.9):
  !       w ← w_3 + (w − w_3) min(1, Σ Q_l / (ε Q_out)) min(1, q_f / (ε │q_e│))
  !     (Q_out = 面のセルの流出の和、q_f = 面の単位幅流量、q_e = この辺の単位幅流量)。
  !     (a) 流入が流出の ε 倍に満たない面のセル(水が四方へ出ていくセル、流量を与えるセル): 面の流束を流入の比
  !         Q_l / Σ Q_l で分けるので、流入が丸めの大きさだと、分け方が丸めで決まり、流入がちょうど 0 のときの値(w_3)
  !         から飛ぶ。ω_o も、斜めの流入元のセルについて、同じ形で 1(流入がないときの値)へ寄せる(src_fwd)。
  !     (b) 面の流量が、この辺の流量の ε 倍に満たない面(水が、辺の線の両側へ分かれて出ていくセルの面。面のセルの
  !         平均の流量の、辺の向きの成分が 0 に近い): 分ける元の面の流束がほとんどないのに、分けた流れの比だけが残り、
  !         1 未満の重みが、面の流量に比例しない項(f_advection_bend = 2 のエネルギー形の項)に掛かる。q_f の符号
  !         (流入面かどうか)が丸めで決まる面で、項があるか・ないかが飛ぶ。
  !     どちらも、対称な流れ(円形の水の盛り上がり)で、丸めの大きさの差を 1 ステップで 4〜6 桁育てた(test/nest_identity の
  !     非静水圧の項目)。(b) を、エネルギー形の項そのものを面の流量の比で下げる形にはしない: 線の上流側が壁の、
  !     折り返しのセル(平均の流量は小さいが、辺の流量は大きい)で、要る項まで弱まる(test/cascade で、流れの水頭の
  !     超過が +3.2 → +7.0 m)。線の上流側が壁・乾床の面(w = 0)は、この関数を通らないので、変わらない
  !   読むのは、面のセルの 8 リンクの実流量(donor_share と同じ)と、斜めの流入元のセル(面のセルの隣)の 8 リンクの
  !   実流量(行 j − 3 のエッジまで。mn・fwd・frw をエッジ幅 2 で交換しておく = opt%adv_wide。line_flow と同じ)。
  !   8 本のリンクの和は、格子の対称操作(鏡映・90° 回転)で入れ替わる対ごとに取る(path_value と同じ)
  !   - この関数は、面のセルの実流量を、連結の実流量の表 tx%ql から読まず、その場で qlk で計算する(adv_bend_mc の
  !     写しも同じ)。表から読む形と、w = 1 が決まる面を先に抜ける近道を足した形は、どちらも、-Ofast が下の 8 本の和の
  !     結合の順を変えて、結果の最終桁が動いた(印字の結果は同じで、保存した状態の最終桁が違う。§113.7)。斜めの
  !     流入元の向き src_fwd は、表から読む(同じ値)。代わりに、呼び出し側が、ここで計算した重みを面ごとに tx%wst に
  !     控え、adv_bend_mc は、同じ面の重みを計算し直さずに読む(2 つの写しは、同じ面に同じ値を返す。§113.7)
  pure function stream_share(ci, cj, kk, qf, w3) result(w)
    integer, intent(in) :: ci, cj     ! 面のセル
    integer, intent(in) :: kk         ! 面のセルから見た、線 k の供給元の 8 近傍番号
    real, intent(in) :: qf            ! 面を通る単位幅流量(検査体積へ入る向きが正)
    real, intent(in) :: w3            ! 3 の重み(donor_share)
    real :: w
    real :: ql(1:8), qo(1:8), fl(1:8), wl(1:8), q, qin, qth, isg, oh, th, num, den
    integer :: l
    w = w3
    if (qf <= 0.0) return
    do l = 1, 8
      q = qlk(ci, cj, l)
      ql(l) = max(0.0, -q)
      qo(l) = max(0.0, q)
      fl(l) = tx%gst(l,kk) * ql(l)
    end do
    qin = ((ql(2) + ql(7)) + (ql(4) + ql(5))) + ((ql(1) + ql(8)) + (ql(3) + ql(6)))
    if (qin <= 0.0) return
    isg = ((fl(2) + fl(7)) + (fl(4) + fl(5))) + ((fl(1) + fl(8)) + (fl(3) + fl(6)))
    oh = qf * tx%w8lt(ke8(kk)) - isg
    do l = 1, 8
      wl(l) = 0.0
      if (ql(l) <= 0.0) then
        fl(l) = 0.0
        cycle
      end if
      fl(l) = fl(l) + oh * (ql(l) / qin)
      if (fl(l) <= 0.0) then
        fl(l) = 0.0
        cycle
      end if
      if (l == kk) then
        wl(l) = fl(l)
      else if (tx%gst(l,kk) > 0.0) then
        th = 1.0
        if (p_stream_kappa * ql(kk) < ql(l)) then
          th = p_stream_kappa * ql(kk) / ql(l)
          th = th + (1.0 - th) * (1.0 - src_fwd(ci + din(l), cj + djn(l), kk)) * w3
        end if
        wl(l) = fl(l) * th
      else
        wl(l) = fl(l) * w3
      end if
    end do
    den = ((fl(2) + fl(7)) + (fl(4) + fl(5))) + ((fl(1) + fl(8)) + (fl(3) + fl(6)))
    if (den <= 0.0) return
    num = ((wl(2) + wl(7)) + (wl(4) + wl(5))) + ((wl(1) + wl(8)) + (wl(3) + wl(6)))
    w = min(1.0, max(0.0, num / den))
    ! 流入が流出の ε 倍に満たないとき・面の流量がこの辺(面のセルの 9 − kk 近傍へ向かう辺)の単位幅流量の ε 倍に
    ! 満たないときは、3 の重みへ寄せる(割り算は、そのときだけ。商は 1 未満)。w = w_3 の面(大半の面)は、寄せても
    ! 同じ値なので、流出の和と辺の流量を読まない
    if (w /= w3) then
      qth = opt%p_adv_donor_eps * (((qo(2) + qo(7)) + (qo(4) + qo(5))) + ((qo(1) + qo(8)) + (qo(3) + qo(6))))
      if (qin < qth) w = w3 + (w - w3) * (qin / qth)
      qth = opt%p_adv_donor_eps * abs(mnk(ci, cj, 9 - kk))
      if (qf < qth) w = w3 + (w - w3) * (qf / qth)
    end if
  end function

  ! セル (si, sj) への流入のうち、kk 近傍から面のセルへ向かう向きに前向きの連結(gst > 0)から入る割合
  ! (stream_share の ω_o)。流入がなければ 1。流入が、このセルの流出の ε 倍に満たないときは、その比で 1 へ寄せる
  ! (流入が丸めの大きさであるか・ないかで値が飛ばない。§113.9)。領域の枠の外のセル(側方 Neumann の辺の外。
  ! 8 リンクを持たない)も 1
  pure function src_fwd(si, sj, kk) result(r)
    integer, intent(in) :: si, sj, kk
    real :: r, q(1:8), qa, qf, qth
    integer :: l
    r = 1.0
    if (si < 1 .or. si > g%nx .or. sj < 1 .or. sj > dcp%ny_g) return
    q(1:8) = max(0.0, tx%ql(1:8,si,sj))       ! 8 近傍への流出(連結の実流量の表)
    qth = opt%p_adv_donor_eps * (((q(2) + q(7)) + (q(4) + q(5))) + ((q(1) + q(8)) + (q(3) + q(6))))
    q(1:8) = max(0.0, -tx%ql(1:8,si,sj))      ! 8 近傍からの流入
    qa = ((q(2) + q(7)) + (q(4) + q(5))) + ((q(1) + q(8)) + (q(3) + q(6)))
    if (qa <= 0.0) return
    do l = 1, 8
      if (tx%gst(l,kk) <= 0.0) q(l) = 0.0
    end do
    qf = ((q(2) + q(7)) + (q(4) + q(5))) + ((q(1) + q(8)) + (q(3) + q(6)))
    r = qf / qa
    if (qa < qth) r = 1.0 - (1.0 - r) * (qa / qth)
  end function

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

  ! 側方面の供給元の重み(f_advection_donor = 3。developer.md §102): cell_ok の乾湿判定(水深 ≥ dd で 1、
  ! 未満で 0)を、dd 未満では水深に比例して 0 へ寄せる連続な値 min(1, h/dd) にしたもの。確保範囲外・
  ! 無効・海セルは cell_ok と同じく 0。h ≥ dd なら厳密に 1 で、h = 0 なら 0
  pure function wet_weight(ci, cj) result(w)
    integer, intent(in) :: ci, cj
    real :: w
    integer :: mi, mj
    call mirror_cell(ci, cj, mi, mj)      ! 側方 Neumann の辺の外は鏡像(§90)
    w = 0.0
    if (mi < 1 .or. mi > ubound(s%h, 1) .or. mj < dcp%jsh .or. mj > dcp%jeh) return
    if (g%x(mi,mj) <= 0) return
    if (g%sw(mi,mj) > 0) return
    w = min(1.0, max(0.0, s%h(mi,mj)) / p%dd)
  end function

  ! lateral_u の f_advection_donor = 3 版(developer.md §102)。平行リンクの有効判定(両端セルの cell_ok)
  ! を、両端セルの wet_weight の小さい方 w ∈ [0, 1] に置き換える。
  !   法線エッジ: ū = u_e + w (u_par − u_e)。
  !   斜めエッジ: 2 本の重み w1, w2 で ū = u_e + (w1 f1 (u1 − u_e) + w2 f2 (u2 − u_e)) / max(1, w1 + w2)。
  !     1 本しか無い面の深さ条件(h̄/2 ≤ h1 ≤ 2h̄。§68.37・§68.39)は、もう一方のリンクの重みが欠ける分だけ
  !     効かせる(f1 = w2 + (1 − w2)·[リンク 1 の深さ条件]、f2 も同様)。
  ! 重みが 0 か 1 だけの面(dd 未満の水膜を含まない面)は lateral_u と同じ式・同じ値(丸めも同じ)
  pure function lateral_u_w(ci, cj, kk, sgn, ue0, he) result(u)
    integer, intent(in) :: ci, cj, kk, sgn
    real, intent(in) :: ue0, he     ! he: 面(エッジ)の検査体積の水深 h̄
    real :: u, w1, w2, u1, u2, h1, h2, f1, f2
    logical :: ok1, ok2
    integer :: oi, oj
    if (kk == 2 .or. kk == 4) then
      oi = ci + sgn * dti(kk)
      oj = cj + sgn * dtj(kk)
      w1 = min(wet_weight(oi, oj), wet_weight(oi + din(kk), oj + djn(kk)))
      if (w1 >= 1.0) then
        u = uvk(oi, oj, kk)
      else if (w1 > 0.0) then
        u = ue0 + w1 * (uvk(oi, oj, kk) - ue0)
      else
        u = ue0
      end if
      return
    end if
    u1 = ue0
    h1 = 0.0
    oi = ci + sgn * dti(kk)
    oj = cj
    w1 = min(wet_weight(oi, oj), wet_weight(oi + din(kk), oj + djn(kk)))
    if (w1 > 0.0) then
      u1 = uvk(oi, oj, kk)
      h1 = 0.5 * (hcell(oi, oj) + hcell(oi + din(kk), oj + djn(kk)))
    end if
    u2 = ue0
    h2 = 0.0
    oi = ci
    oj = cj + sgn * dtj(kk)
    w2 = min(wet_weight(oi, oj), wet_weight(oi + din(kk), oj + djn(kk)))
    if (w2 > 0.0) then
      u2 = uvk(oi, oj, kk)
      h2 = 0.5 * (hcell(oi, oj) + hcell(oi + din(kk), oj + djn(kk)))
    end if
    ok1 = h1 >= 0.5 * he .and. h1 <= 2.0 * he     ! 1 本しか無い面の深さ条件
    ok2 = h2 >= 0.5 * he .and. h2 <= 2.0 * he
    if (w1 >= 1.0 .and. w2 >= 1.0) then           ! 以下 4 つは lateral_u と同じ
      u = (u1 + u2) / 2
    else if (w1 >= 1.0 .and. w2 <= 0.0) then
      u = ue0
      if (ok1) u = u1
    else if (w1 <= 0.0 .and. w2 >= 1.0) then
      u = ue0
      if (ok2) u = u2
    else if (w1 <= 0.0 .and. w2 <= 0.0) then
      u = ue0
    else                                          ! dd 未満の水膜を含む面: 連続に寄せる
      f1 = w2
      if (ok1) f1 = 1.0
      f2 = w1
      if (ok2) f2 = 1.0
      u = ue0 + (w1 * f1 * (u1 - ue0) + w2 * f2 * (u2 - ue0)) / max(1.0, w1 + w2)
    end if
  end function

  ! lateral_u_w の f_advection_lateral = 1 版(developer.md §110.25。ENCflow 独自)。lateral_u_w に 2 つを足す。
  !   (1) 平行リンクの重み(両端セルの wet_weight の小さい方)に、代表性 R'(lateral_rep。h_p = 平行リンクの
  !       両端のセルの浅い方)を掛ける。河岸の水膜の遅い流速を、支川や隣の列から入ってくる深い水の流速と
  !       みなさない(水膜が dd 以上あるだけで平行リンクを使う lateral_u_w は、雨で濡れた岸に接する河道に
  !       人工的な減速を作り、合流の損失を、岸が濡れているときだけ数える。test/wetbank・test/tjunction)。
  !   (2) 平行リンクが代表しない分は、合流の不足分 Δ(lateral_join)で数える。
  !   軸エッジ: ū = u_e + w (u_par − u_e) + (1 − w) Δ。
  !   斜めエッジ: lateral_u_w の式(重み w1, w2 は R' を掛けたもの)+ (1 − w_rep) Δ。w_rep は平行リンクが面を
  !     代表する度合い(2 本とも使えれば 1。重みの欠ける分・深さ条件で使えない分だけ小さい)。
  ! 重みが 1 の面(薄い水膜を含まない一様な流れ)は lateral_u_w・lateral_u と同じ式・同じ値
  pure function lateral_u_j(ci, cj, kk, sgn, ue0, he) result(u)
    integer, intent(in) :: ci, cj, kk, sgn
    real, intent(in) :: ue0, he     ! he: 面(エッジ)の検査体積の水深 h̄
    real :: u, w1, w2, u1, u2, h1, h2, f1, f2, wrep
    logical :: ok1, ok2
    integer :: oi, oj
    if (kk == 2 .or. kk == 4) then
      oi = ci + sgn * dti(kk)
      oj = cj + sgn * dtj(kk)
      w1 = min(wet_weight(oi, oj), wet_weight(oi + din(kk), oj + djn(kk)))
      if (w1 > 0.0) w1 = w1 * lateral_rep(ci, cj, kk, sgn, min(hcell(oi, oj), hcell(oi + din(kk), oj + djn(kk))))
      if (opt%adv_latflux .and. w1 > 0.0) w1 = w1 * lateral_flux(ci, cj, kk, sgn, oi, oj)
      if (w1 >= 1.0) then
        u = uvk(oi, oj, kk)
      else if (w1 > 0.0) then
        u = ue0 + w1 * (uvk(oi, oj, kk) - ue0)
        u = u + (1.0 - w1) * lateral_join(ci, cj, kk, sgn, ue0)
      else
        u = ue0 + lateral_join(ci, cj, kk, sgn, ue0)
      end if
      return
    end if
    u1 = ue0
    h1 = 0.0
    oi = ci + sgn * dti(kk)
    oj = cj
    w1 = min(wet_weight(oi, oj), wet_weight(oi + din(kk), oj + djn(kk)))
    if (w1 > 0.0) w1 = w1 * lateral_rep(ci, cj, kk, sgn, min(hcell(oi, oj), hcell(oi + din(kk), oj + djn(kk))))
    if (opt%adv_latflux .and. w1 > 0.0) w1 = w1 * lateral_flux(ci, cj, kk, sgn, oi, oj)
    if (w1 > 0.0) then
      u1 = uvk(oi, oj, kk)
      h1 = 0.5 * (hcell(oi, oj) + hcell(oi + din(kk), oj + djn(kk)))
    end if
    u2 = ue0
    h2 = 0.0
    oi = ci
    oj = cj + sgn * dtj(kk)
    w2 = min(wet_weight(oi, oj), wet_weight(oi + din(kk), oj + djn(kk)))
    if (w2 > 0.0) w2 = w2 * lateral_rep(ci, cj, kk, sgn, min(hcell(oi, oj), hcell(oi + din(kk), oj + djn(kk))))
    if (opt%adv_latflux .and. w2 > 0.0) w2 = w2 * lateral_flux(ci, cj, kk, sgn, oi, oj)
    if (w2 > 0.0) then
      u2 = uvk(oi, oj, kk)
      h2 = 0.5 * (hcell(oi, oj) + hcell(oi + din(kk), oj + djn(kk)))
    end if
    ok1 = h1 >= 0.5 * he .and. h1 <= 2.0 * he     ! 1 本しか無い面の深さ条件
    ok2 = h2 >= 0.5 * he .and. h2 <= 2.0 * he
    wrep = 0.0
    if (w1 >= 1.0 .and. w2 >= 1.0) then           ! 以下 4 つは lateral_u と同じ
      u = (u1 + u2) / 2
      wrep = 1.0
    else if (w1 >= 1.0 .and. w2 <= 0.0) then
      u = ue0
      if (ok1) then
        u = u1
        wrep = 1.0
      end if
    else if (w1 <= 0.0 .and. w2 >= 1.0) then
      u = ue0
      if (ok2) then
        u = u2
        wrep = 1.0
      end if
    else if (w1 <= 0.0 .and. w2 <= 0.0) then
      u = ue0
    else                                          ! 重みが 0 と 1 の間の平行リンクを含む面: 連続に寄せる
      f1 = w2
      if (ok1) f1 = 1.0
      f2 = w1
      if (ok2) f2 = 1.0
      u = ue0 + (w1 * f1 * (u1 - ue0) + w2 * f2 * (u2 - ue0)) / max(1.0, w1 + w2)
      wrep = min(1.0, (w1 * f1 + w2 * f2) / max(1.0, w1 + w2))
    end if
    if (wrep < 1.0) u = u + (1.0 - wrep) * lateral_join(ci, cj, kk, sgn, ue0)
  end function

  ! 側方面を横切って入るリンクの組(lateral_rep・lateral_join が同じ組を使う)。辺 (ci, cj) → kk 近傍
  ! (kk = 1..4)の sgn = ±1 側の面について、リンクの数 nl、各リンクの「入る先のセル」(oc = 0: c、1: n)、
  ! 入る先のセルから見たリンクの 8 近傍番号 kl、流量に掛ける係数 wt を返す。
  !   軸エッジ: c・n の ±t 軸リンク(面の半分ずつ = 0.5)と、面を横切る斜めリンク 2 本(全幅 = 1)。流量は
  !     実流量 qlk(側方面の流束 qtp・qtm と同じ組・同じ係数)。
  !   斜めエッジ: c・n の直交する斜めリンク。流量は単位幅流量 mnk(同上)
  pure subroutine lateral_links(kk, sgn, nl, oc, kl, wt)
    integer, intent(in) :: kk, sgn
    integer, intent(out) :: nl, oc(1:4), kl(1:4)
    real, intent(out) :: wt(1:4)
    if (kk == 2 .or. kk == 4) then
      nl = 4
      if (sgn > 0) then
        kl = [ kkp(kk), kkp(kk), kdp_c(kk), kdp_n(kk) ]
      else
        kl = [ kkm(kk), kkm(kk), kdm_c(kk), kdm_n(kk) ]
      end if
      oc = [ 0, 1, 0, 1 ]
      wt = [ 0.5, 0.5, 1.0, 1.0 ]
    else
      nl = 2
      if (sgn > 0) then
        kl = [ kkp(kk), kkp(kk), 0, 0 ]
      else
        kl = [ kkm(kk), kkm(kk), 0, 0 ]
      end if
      oc = [ 0, 1, 0, 0 ]
      wt = [ 1.0, 1.0, 0.0, 0.0 ]
    end if
  end subroutine

  ! 側方面を横切ってセル (xi, xj) へ、その kl 近傍から入る流量(流入が正。軸エッジは実流量 × wt、斜めエッジは
  ! 単位幅流量)
  pure function lateral_inflow(xi, xj, kk, kl, wt) result(q)
    integer, intent(in) :: xi, xj, kk, kl
    real, intent(in) :: wt
    real :: q
    if (kk == 2 .or. kk == 4) then
      if (tab) then                   ! 表から読む(同じ値。§113.7)
        q = -wt * tx%ql(kl,xi,xj)
      else
        q = -wt * qlk(xi, xj, kl)
      end if
    else
      q = -mnk(xi, xj, kl)
    end if
  end function

  ! 代表性 R'(f_advection_lateral = 1。developer.md §110.25。ENCflow 独自): 面の脇の水(水深 h_p。平行リンクの
  ! 両端のセルの浅い方か、斜めエッジの面を横切る軸リンクの向こうのセル)が、側方面を横切って入ってくる水を
  ! 代表する度合い。面を横切るリンク l のうち流入するもの(流量 Q_l、流入元のセル o_l)について
  !   r_l = min(1, h_p / (ε min(h_o,l, h_e)))     (ε = p_adv_donor_eps、h_e = この辺の両端のセルの浅い方)
  ! を流量で重み付けして平均する(R' = Σ Q_l r_l / Σ Q_l。流入がなければ 1)。
  !   = 脇の水が、入ってくる水の元のセルに比べても、この辺自身に比べても、ε 倍より薄いときだけ、代表しないと
  !     数える。入ってくる水そのものが薄い(岸の水膜からの流入)ときと、この辺自身が薄い(段波・遡上の先端)
  !     ときは 1 で、従来と同じ扱いになる。
  ! 流入元が乾燥・無効・海(cell_ok が偽)のリンクは r_l = 1。割り算は h_p < ε min(h_o, h_e) のときだけ行う
  ! (商は 1 未満。分母が 0 にアンダーフローしても 0 で割らない。donor_share と同じ)。
  ! h_p ≥ ε h_e なら、どのリンクも r_l = 1(min(h_o, h_e) ≤ h_e)なので、リンクの流量を読まずに 1 を返す
  ! (同じ値。脇の水が薄い水膜でない大部分の面は、ここで終わる)
  pure function lateral_rep(ci, cj, kk, sgn, hp) result(r)
    integer, intent(in) :: ci, cj, kk, sgn
    real, intent(in) :: hp
    real :: r, q, qs, qr, hem, ho, wt(1:4)
    integer :: l, nl, oc(1:4), kl(1:4), xi, xj, oi, oj
    hem = min(hcell(ci, cj), hcell(ci + din(kk), cj + djn(kk)))
    r = 1.0
    if (hp >= opt%p_adv_donor_eps * hem) return
    call lateral_links(kk, sgn, nl, oc, kl, wt)
    qs = 0.0
    qr = 0.0
    do l = 1, nl
      xi = ci + oc(l) * din(kk)
      xj = cj + oc(l) * djn(kk)
      q = lateral_inflow(xi, xj, kk, kl(l), wt(l))
      if (q <= 0.0) cycle
      qs = qs + q
      oi = xi + din(kl(l))
      oj = xj + djn(kl(l))
      ho = 0.0
      if (cell_ok(oi, oj)) ho = opt%p_adv_donor_eps * min(hcell(oi, oj), hem)
      if (hp >= ho) then
        qr = qr + q
      else
        qr = qr + q * (hp / ho)
      end if
    end do
    r = 1.0
    if (qs > 0.0) r = qr / qs
  end function

  ! 流量の似かより(f_advection_lateral = 2。developer.md §112.11・§113。ENCflow 独自): 平行リンク(基準セル
  ! (pi, pj) から kk 近傍へ)の流速を、側方面を横切って入ってくる水の流速として使う度合い。1 の代表性 R'
  ! (lateral_rep。平行リンクが、入ってくる水より薄い水膜なら使わない)に掛ける。
  !   平行リンクの単位幅流量 a と、面を横切るリンク l の流入元のセル o_l の、辺の向きの単位幅流量 b_l(セルの
  !   平均の流量 (m, n) の成分)を比べ、平行リンクの方が κ 倍より多く流していれば、その比で下げる:
  !     r_l = min(1, κ (b⁺_l + q0) / (│a│ + q0))        b⁺_l = b_l の、a の向きの成分(同じ向きなら │b_l│、逆向きなら 0)
  !     R  = Σ Q_l r_l / Σ Q_l                           (流入するリンクについて。流入がなければ 1)
  !     q0 = ε ×(面を横切って入ってくる、単位長さあたりの流量)、ε = p_adv_donor_eps、κ = p_stream_kappa
  !   = 速い平行リンクの運動量を、遅い水が入ってくる辺へ持ち込まない。角のセル・淵を通る辺へ、隣を走る本流の
  !     斜めの連結の流速を持ち込むと、角のセルと河道のセルの間を水が回って、エネルギーが増える(test/stairbank の
  !     sab。§112.8)。a も b_l も、面を横切る流量の ε 倍より小さければ 1(どちらもほとんど流れていない)。一様な
  !     流れは a = b_l で 1。
  !   - a と b_l が逆向きのときは、b_l の大きさでは下げない(a の大きさだけで下げる): a → 0 で、同じ向きの側
  !     (r_l = 1)とつながる。b_l の大きさでも下げていた初めの形 κ q0 / (max(│a│, │b_l│) + q0) は、平行リンクの流量が
  !     丸めの大きさの面(対称な流れの、対称軸をまたぐリンク)で、a の丸めの符号で r_l が 1 と κ q0 / (│b_l│ + q0) の
  !     間を飛び、丸めの大きさの差が 1 ステップで 6 桁育った(test/nest_identity の非静水圧の項目。§113.9)。
  !   - 平行リンクが、この辺と向かい合って流れているときは、下げない: この辺の単位幅流量 q_e を、平行リンクの向きに
  !     測って、その大きさで割った s = q_e sign(a) / │a│ が負のとき、R ← 1 − (1 − R) max(0, 1 + κ s)(s ≤ −1/κ で
  !     R = 1。s = 0 = 止まっている辺で、上の R とつながる)。向かい合う平行リンクの流速は、この辺を減速する向き
  !     (ブレーキ)で、1 の規則のまま使う。これも下げると、(i + j) の偶奇で逆回転する斜めの副格子の循環(セルの
  !     平均の流量が 0 なので b_l ≈ 0。§68.36)に、移流項の減衰が働かなくなる(test/sublattice の、背景の流れのない
  !     構成の 60 分後の振幅が 0.04 → 0.22。§113.9)。同じ向きで、辺の方が速いとき(これもブレーキの向き)まで
  !     下げないことにすると、切り出した秩父の区間で、水深が 3〜7 m 下がり、最大流速が 17 → 22 m/s に上がる
  !     (エネルギーが増える流れに戻る)ので、向かい合うときだけにする。
  !   - 平行リンクの方が遅い向き(ブレーキの向き)は、下げない(1 の規則のまま)。この向きも下げると、流れに沿って
  !     流量が急に変わる所(段波の前面)で、上流側にある流入元のセルと平行リンクの流量の違いを「似ていない」と
  !     数えてしまい、ダム破壊の段波の位置の誤差が 1.25 → 1.44 % に、行ごとの位置のばらつきが 2 倍に増える
  !     (test/dambreak。§112.11)。
  !   読むのは、平行リンクの mn、面を横切るリンクの流量(lateral_rep と同じ)、流入元のセルの m, n(行 j − 2 .. j + 1。
  !   ステップ頭にセル幅で交換済み)。流入元が乾燥・無効・海(cell_ok が偽)のリンクは r_l = 1。流入元が、境界として
  !   与えたセル(水位規定セルと、流量を湧き出しで与えるセル。given_cell)のリンクも r_l = 1: 与えたセルの平均の流量
  !   (m, n) は、外から入ってくる分の連結を持たないので、流れの向きに、内側の連結の半分ほどにしかならず(壁との
  !   角では、もっと小さい)、流れが一様でも「平行リンクの方が κ 倍より速い」と数えてしまう(test/nhcurrent の流入の
  !   角の 4 つの面で 0.70〜0.76。§113.9)
  pure function lateral_flux(ci, cj, kk, sgn, pi, pj) result(r)
    integer, intent(in) :: ci, cj, kk, sgn
    integer, intent(in) :: pi, pj     ! 平行リンクの基準セル
    real :: r, q, qs, qr, a, b, bp, q0, rl, sr, ql(1:4), wt(1:4)
    integer :: l, nl, oc(1:4), kl(1:4), xi, xj, oi, oj, mi, mj
    r = 1.0
    a = mnk(pi, pj, kk)
    call lateral_links(kk, sgn, nl, oc, kl, wt)
    qs = 0.0
    do l = 1, nl
      xi = ci + oc(l) * din(kk)
      xj = cj + oc(l) * djn(kk)
      ql(l) = max(0.0, lateral_inflow(xi, xj, kk, kl(l), wt(l)))
      qs = qs + ql(l)
    end do
    if (qs <= 0.0) return
    ! 面を横切って入る、単位長さあたりの流量。軸エッジは実流量の和 ÷ 面の長さ、斜めエッジは単位幅流量の平均
    ! (側方面の流束 qtp・qtm と同じ取り方)
    if (kk == 2 .or. kk == 4) then
      q0 = opt%p_adv_donor_eps * qs / geo%w8dr(kk)
    else
      q0 = opt%p_adv_donor_eps * qs / 2
    end if
    qr = 0.0
    do l = 1, nl
      q = ql(l)
      if (q <= 0.0) cycle
      oi = ci + oc(l) * din(kk) + din(kl(l))
      oj = cj + oc(l) * djn(kk) + djn(kl(l))
      rl = 1.0
      if (cell_ok(oi, oj) .and. .not. given_cell(oi, oj)) then
        call mirror_cell(oi, oj, mi, mj)
        b = s%m(mi,mj) * geo%n8x(kk) + s%n(mi,mj) * geo%n8y(kk)
        bp = abs(b)                               ! b_l の、a の向きの成分(逆向きなら 0)
        if (a * b < 0.0) bp = 0.0
        if (abs(a) > bp) then
          if (p_stream_kappa * (bp + q0) < abs(a) + q0) rl = p_stream_kappa * (bp + q0) / (abs(a) + q0)
        end if
      end if
      qr = qr + q * rl
    end do
    r = qr / qs
    ! 平行リンクが、この辺と向かい合って流れているときは、下げない(r < 1 になるのは │a│ > 0 のときだけ)
    if (r < 1.0) then
      sr = mnk(ci, cj, kk) * sign(1.0, a) / abs(a)
      if (sr < 0.0) r = 1.0 - (1.0 - r) * max(0.0, 1.0 + p_stream_kappa * sr)
    end if
  end function

  ! セル (ci, cj) が、境界として与えたセル(水位規定セルか、流量を湧き出しで与えるセル。§113.9)か。印がなければ偽。
  ! 側方 Neumann の辺の外の位置は、鏡像のセル(辺の法線方向に枠内へ寄せたセル)の印を読む(cell_ok・hcell と同じ
  ! 規則。読まないと、与えたセルの列が側方 Neumann の辺に接する角で、枠の中の面と境界面の扱いが食い違う。
  ! §113.9 (7))。確保範囲の外は偽(adv_bend_mc の given_cell と同じ)
  pure function given_cell(ci, cj) result(r)
    integer, intent(in) :: ci, cj
    logical :: r
    integer :: mi, mj
    r = .false.
    if (.not. allocated(tx%gvn)) return
    call mirror_cell(ci, cj, mi, mj)
    if (mi < dcp%ish .or. mi > dcp%ieh .or. mj < dcp%jsh .or. mj > dcp%jeh) return
    r = tx%gvn(mi,mj)
  end function

  ! 斜めエッジ (ci, cj) → kk の sgn 側の側方面を横切る軸リンクの向こうのセル (oi, oj) が開いている度合い
  ! (f_advection_lateral = 1 の axis_open)。wet_weight に、代表性 R'(h_p = そのセルの水深)を掛ける
  pure function open_rep(ci, cj, kk, sgn, oi, oj) result(w)
    integer, intent(in) :: ci, cj, kk, sgn, oi, oj
    real :: w
    w = wet_weight(oi, oj)
    if (w > 0.0) w = w * lateral_rep(ci, cj, kk, sgn, hcell(oi, oj))
  end function

  ! 合流の不足分 Δ(f_advection_lateral = 1。developer.md §110.25。ENCflow 独自): 側方面を横切って入る水が、
  ! この辺の線に沿う流れへ、別の向きから合流する分の、ū_t − u_e に足す量。面を横切るリンク l のうち流入する
  ! もの(流量 Q_l、流入元のセル o_l、入る先のセル X_l = c か n)について
  !   Δ = −u_e Σ Q_l ω_X (1 − ω_o) (1 − cos θ_l) / Σ Q_l
  !   ω_X: 入る先のセルに、この辺の線に沿う流れがある度合い(join_share = donor_share(X, 線の上流側の隣)。0 なら、曲がって
  !        入ってくる流れそのものがこの辺の流れ = 屈曲で、合流ではない)。この辺の下流側のセルへ入る分には、
  !        上流側のセルの ω も掛ける(上流側が屈曲なら、下流側のセルへ近道で入る斜めの流入も同じ流れ)。
  !   ω_o: 流入元のセルに、この辺の線と同じ向きの流れがある度合い(line_flow。1 なら、並んで流れている水の
  !        列の間の出入りで、合流ではない。格子の階段を直線の河道として流す性質を保つ)。
  !   θ_l: 入ってくるリンクと辺の線のなす角。直交するリンク(軸エッジの ±t 軸リンク、斜めエッジの直交する
  !        斜めリンク)は 90°(cos θ = 0 = 辺の向きの運動量を持たない。開水路の合流の標準的な扱い。Taylor 1944)、
  !        軸エッジの面を横切る斜めリンクは、向きによらず 45°(正方セル。一般には軸と対角線のなす角)。
  !        8 近傍の格子は、直角の合流を「直交するリンク + 斜めのリンク」の組で表す。斜めのリンクの水を
  !        運動量 0、または上流側のセルへ入る分を逆向き(135°)と数えると、合流部の池が揺れ続けた(§110.23・
  !        §110.25)ので、斜めのリンクは cos 45° ぶんの運動量を持つと数える(独自の簡略化)。
  ! 流入元が乾燥・無効・海(cell_ok が偽)のリンクは不足分 0(流量は分母に数える)。流入がなければ 0
  pure function lateral_join(ci, cj, kk, sgn, ue0) result(d)
    integer, intent(in) :: ci, cj, kk, sgn
    real, intent(in) :: ue0
    real :: d, q, qs, qd, om(0:1), cs, wt(1:4), lf
    integer :: l, nl, oc(1:4), kl(1:4), kb, xi, xj, oi, oj
    logical :: have_om
    kb = 9 - kk                                   ! この辺の流れの上流側の、線上の隣の 8 近傍番号
    if (ue0 < 0.0) kb = kk
    ! ω_X(join_share。セルの 8 リンクを 2 回読む)は、ω_o < 1 のリンクが初めて出たときに数える。ω_o = 1 の
    ! リンクの項は ω_X によらず 0 なので、それまでは 1 を置いておく(結果は同じ。§110.28)
    have_om = .false.
    om(:) = 1.0
    call lateral_links(kk, sgn, nl, oc, kl, wt)
    qs = 0.0
    qd = 0.0
    do l = 1, nl
      xi = ci + oc(l) * din(kk)
      xj = cj + oc(l) * djn(kk)
      q = lateral_inflow(xi, xj, kk, kl(l), wt(l))
      if (q <= 0.0) cycle
      qs = qs + q
      oi = xi + din(kl(l))
      oj = xj + djn(kl(l))
      if (.not. cell_ok(oi, oj)) cycle
      cs = 0.0                                    ! cos θ_l(直交するリンクは 0)
      if (l >= 3) cs = abs(geo%n8x(kk) * geo%n8x(kl(l)) + geo%n8y(kk) * geo%n8y(kl(l)))
      lf = line_flow(oi, oj, kb)
      if (lf < 1.0 .and. .not. have_om) then
        om(0) = join_share(ci, cj, kb)
        om(1) = join_share(ci + din(kk), cj + djn(kk), kb)
        if (ue0 >= 0.0) then                      ! 下流側のセルへ入る分には、上流側のセルの度合いも掛ける
          om(1) = om(1) * om(0)
        else
          om(0) = om(0) * om(1)
        end if
        have_om = .true.
      end if
      qd = qd + q * om(oc(l)) * (1.0 - lf) * (cs - 1.0) * ue0
    end do
    d = 0.0
    if (qs > 0.0) d = qd / qs
  end function

  ! セル (xi, xj) に、その kb 近傍(線の上流側)から、この辺の線に沿う流れが入る度合い(lateral_join の ω_X)。
  ! donor_share(線 k の供給元の重み)と同じ値。kb 近傍が確保範囲の外(領域の縁の外。側方 Neumann の辺の外は
  ! 鏡像のセルで判定。cell_ok・wet_weight と同じ条件)のときは、そこからは流れが入らないので 0 を返す。
  ! donor_share は、供給元のリンクの流量が小さいときに供給元の水深(hcell)を読むので、範囲の外の供給元では
  ! 呼べない(流向面は、供給元が cell_ok のときだけ donor_share を呼ぶ。ここは、線の上流側が領域の縁に接する
  ! 辺でも通る。確かめずに呼んでいた初めの形は、-fcheck=all の np = 2 で、向きを変えた 45° の合流の領域の縁の
  ! 辺が s%h の範囲外を読んで止まった。developer.md §110.25)
  pure function join_share(xi, xj, kb) result(w)
    integer, intent(in) :: xi, xj, kb
    real :: w
    integer :: mi, mj
    call mirror_cell(xi + din(kb), xj + djn(kb), mi, mj)
    w = 0.0
    if (mi < 1 .or. mi > ubound(s%h, 1) .or. mj < dcp%jsh .or. mj > dcp%jeh) return
    w = donor_share(xi, xj, kb)
  end function

  ! セル (ci, cj) に、その kk 近傍(線の上流側)から入る流れがある度合い(lateral_join の ω_o)。流量だけで
  ! 測る: min(1, kk 近傍からの流入 / (ε × 8 リンクの流入の最大))。流入がなければ 0。
  ! donor_share と違い、水深による例外(流量が小さくても、供給元が深ければ 1)を持たない: 支川の脇の岸が
  ! 浸水しただけで、支川の水を「並んで流れている水」と数えないため(§110.23)。
  ! 側方 Neumann の辺の外のセルは、鏡像のセル(辺の法線方向に枠内へ寄せたセル)の値を読む(cell_ok・hcell と
  ! 同じ扱い。辺の外は、内側の流れの続きとみなす)。
  ! 読むエッジは、セルの 8 リンク。斜めエッジの n 側の流入元は行 j − 2 にあるので、行 j − 3 のエッジ(成分
  ! 1〜3)と行 j − 2 の成分 4 まで読む: mn・fwd・frw を、エッジ幅 2 で交換しておく(m_swflow_enc の
  ! calc_enc_flux の冒頭と init。f_advection_lateral = 1 のときだけ。§110.25)。
  ! 割り算は、流入が ε × 最大 に満たないときだけ行う(商は 1 未満。donor_share と同じ)
  pure function line_flow(ci, cj, kk) result(w)
    integer, intent(in) :: ci, cj, kk
    real :: w, qk, qmax, qe
    integer :: l, mi, mj
    call mirror_cell(ci, cj, mi, mj)
    w = 0.0
    if (tab) then
      ! 表から読む(同じ値。§113.7)。下の、8 本を読み切らない形と同じ場合分け: 線の上流の隣からの流入がなければ、
      ! ε × 最大 が正なら 0、0 にアンダーフローするほど小さい流入だけなら 1、流入が全くなければ 0
      qk = max(0.0, -tx%ql(kk,mi,mj))
      qmax = 0.0
      do l = 1, 8
        qmax = max(qmax, -tx%ql(l,mi,mj))
      end do
      if (qk <= 0.0) then
        if (qmax > 0.0 .and. .not. opt%p_adv_donor_eps * qmax > 0.0) w = 1.0
      else
        qe = opt%p_adv_donor_eps * qmax
        w = 1.0
        if (qk < qe) w = qk / qe
      end if
      return
    end if
    qk = max(0.0, -qlk(mi, mj, kk))
    qmax = 0.0
    if (qk <= 0.0) then
      ! 線の上流の隣からの流入がない: ε × 最大 が正になるリンクが 1 本でもあれば 0(8 本を読み切らない。
      ! 同じ値。§110.28)。流入が全くなければ 0。ε × 最大 が 0 にアンダーフローするほど小さいときだけ、
      ! 下の式と同じく 1
      do l = 1, 8
        qmax = max(qmax, -qlk(mi, mj, l))
        if (opt%p_adv_donor_eps * qmax > 0.0) return
      end do
      if (qmax > 0.0) w = 1.0
      return
    end if
    do l = 1, 8
      qmax = max(qmax, -qlk(mi, mj, l))
    end do
    if (qmax > 0.0) then
      qe = opt%p_adv_donor_eps * qmax
      w = 1.0
      if (qk < qe) w = qk / qe
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

  ! 斜めエッジ kk(1, 3)の sgn = ±1 側の側方面の開口率 φ(§68.43): 面を横切る軸リンク
  ! (c 側 1 本、n 側 1 本)の向こうのセルが有効・海でない・湿潤(cell_ok)でなければ、その
  ! リンクが面の流束に占める割合 cwd(正方セルで 0.293)を 1 から引く。全開で 1、両方塞がれば
  ! 1 − 2 cwd = 0.414(斜めリンクの帯だけ)。f_advection_donor = 3 は塞がりを向こうのセルの
  ! wet_weight で連続に数える(φ = 1 − cwd (1 − w_c) − cwd (1 − w_n)。w が 0 か 1 なら上と同じ値)。
  ! f_advection_lateral = 1 は、その重みに代表性 R'(lateral_rep。h_p = 向こうのセルの水深)を掛ける:
  ! 向こうのセルが、面を横切って入ってくる水の元のセルに比べても、この辺自身に比べても ε 倍より薄い
  ! 水膜なら、塞がれていると数える。wet_weight だけだと、dd 以上の水膜があれば全開(φ = 1)になり、
  ! 支川が直交する斜めリンクから入る面で、水膜の岸をはさむ軸リンクにも支川と同じ単位幅流量が通ると
  ! 数えて、面の流束が乾いた岸の 2.4 倍になる(45° 回した合流の堰上げが岸の濡れで変わる。§110.25)
  pure function axis_open(ci, cj, kk, sgn) result(phi)
    integer, intent(in) :: ci, cj, kk, sgn
    real :: phi, wc, wn
    integer :: kc, kn
    if (sgn > 0) then
      kc = pax_c(kk)
      kn = pax_n(kk)
    else
      kc = nax_c(kk)
      kn = nax_n(kk)
    end if
    phi = 1.0
    if (opt%f_advection_lateral == 1) then
      wc = open_rep(ci, cj, kk, sgn, ci + din(kc), cj + djn(kc))
      wn = wc       ! c 側と n 側の軸リンクの向こうは同じセル(面の脇の角のセル)。違う表になっても正しいように確かめる
      if (din(kk) + din(kn) /= din(kc) .or. djn(kk) + djn(kn) /= djn(kc)) then
        wn = open_rep(ci, cj, kk, sgn, ci + din(kk) + din(kn), cj + djn(kk) + djn(kn))
      end if
      phi = phi - tx%cwd * (1.0 - wc)
      phi = phi - tx%cwd * (1.0 - wn)
      return
    end if
    if (opt%f_advection_donor == 3) then
      phi = phi - tx%cwd * (1.0 - wet_weight(ci + din(kc), cj + djn(kc)))
      phi = phi - tx%cwd * (1.0 - wet_weight(ci + din(kk) + din(kn), cj + djn(kk) + djn(kn)))
      return
    end if
    if (.not. cell_ok(ci + din(kc), cj + djn(kc))) phi = phi - tx%cwd
    if (.not. cell_ok(ci + din(kk) + din(kn), cj + djn(kk) + djn(kn))) phi = phi - tx%cwd
  end function

  ! セル (ci, cj) からその kk 近傍へ向かう ENC エッジの実流量 [m³/s](時刻 n。流出が正。
  ! 連続式が水深変化に換算する mn·l8·frw·fwd と同じ = m_swflow_enc_edge_flux の定義。
  ! 確保範囲外は 0)。軸エッジの側方面の流束に使う
  pure function qlk(ci, cj, kk) result(q)
    integer, intent(in) :: ci, cj, kk
    real :: q, fw
    integer :: ei, ej
    ei = ci + die(kk)
    ej = cj + dje(kk)
    if (ei < 0 .or. ei > ubound(sx%mn, 2) .or. ej < dcp%jsh - 1 .or. ej > dcp%jeh) then
      q = 0.0
    else
      fw = 1.0
      if (chn%have_frw) fw = chn%frw(ke8(kk), ei, ej)
      if (chn%have_fwd) fw = fw * chn%fwd(ke8(kk), ei, ej)
      q = sgn8(kk) * sx%mn(ke8(kk), ei, ej) * geo%l8(kk) * fw
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
  ! 屈曲直後の辺の慣性(f_advection_bend = 1。§110)。側方 Neumann の境界面の tae に差分を足す
  if (opt%f_advection_bend > 0) call adv_bend_mc(p, g, s, sx, tx_mod, .true.)
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
    logical :: ok

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
        if (cell_ok(ci - din(k), cj - djn(k))) then
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
        if (cell_ok(in + din(k), jn + djn(k))) then
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
      ! 軸の面は横切るリンクの実流量の和(adv_prepare_mc と同じ。枠外は鏡像で読む)
      if (k == 2 .or. k == 4 .or. k == 5 .or. k == 7) then
        qtp = (0.5 * (qlk8(ci, cj, kp) + qlk8(in, jn, kp)) &
               + qlk8(ci, cj, kdp_c(k)) + qlk8(in, jn, kdp_n(k))) / geo%w8dr(k)
        qtm = (0.5 * (qlk8(ci, cj, km) + qlk8(in, jn, km)) &
               + qlk8(ci, cj, kdm_c(k)) + qlk8(in, jn, kdm_n(k))) / geo%w8dr(k)
      else
        ! 斜めの面は従来式 × 横切る軸リンクの開口率(adv_prepare_mc と同じ。§68.43。
        ! 逆向きの k = 6, 8 の表は pax_*・nax_* に含む)
        qtp = axis_open8(ci, cj, k, 1) * 0.5 * (mnk8(ci, cj, kp) + mnk8(in, jn, kp))
        qtm = axis_open8(ci, cj, k, -1) * 0.5 * (mnk8(ci, cj, km) + mnk8(in, jn, km))
      end if
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

  ! セル (ci, cj) からその kk 近傍へ向かう ENC エッジの実流量 mn·l8·frw·fwd(枠外の扱いは
  ! mnk8 と同じ。adv_prepare_mc の qlk と同じ定義)
  pure function qlk8(ci, cj, kk) result(q)
    integer, intent(in) :: ci, cj, kk
    real :: q, fw
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
      fw = 1.0
      if (chn%have_frw) fw = chn%frw(ke8(kk), ei, ej)
      if (chn%have_fwd) fw = fw * chn%fwd(ke8(kk), ei, ej)
      q = sgn8(kk) * sx%mn(ke8(kk),ei,ej) * geo%l8(kk) * fw
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

  ! 斜めエッジ kk(1, 3, 6, 8)の sgn 側の側方面の開口率(adv_prepare_mc の axis_open と同じ。
  ! 枠外のセルは cell_ok が鏡像で判定する)
  pure function axis_open8(ci, cj, kk, sgn) result(phi)
    integer, intent(in) :: ci, cj, kk, sgn
    real :: phi
    integer :: kc, kn
    if (sgn > 0) then
      kc = pax_c(kk)
      kn = pax_n(kk)
    else
      kc = nax_c(kk)
      kn = nax_n(kk)
    end if
    phi = 1.0
    if (.not. cell_ok(ci + din(kc), cj + djn(kc))) phi = phi - tx%cwd
    if (.not. cell_ok(ci + din(kk) + din(kn), cj + djn(kk) + djn(kn))) phi = phi - tx%cwd
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


!----------------------------------------------------------------------
! 屈曲直後の辺の慣性(運動量保存形 f_advection_scheme = 2, 3 の f_advection_bend = 1。developer.md §110。
! ENCflow 独自)
!   adv_prepare_mc(内部の面。boundary = 偽)と adv_neumann_mc(側方 Neumann の境界面。boundary = 真)が tae を
!   書いた後に呼ぶ(f_advection_bend = 0 では呼ばない = ゼロ追加)。
!
!   運動量保存形移流の流向面の流入面は、風上側(線 k 上)の供給元が壁・乾床のとき ū = u_e(中立。§68.8)、
!   薄い水膜のとき ū = u_e + w (ū_k − u_e)(f_advection_donor = 3。w = donor_share。§102)にしている。中立の
!   分は「水は、いまの辺の流速ですでに動いて入ってくる」と数えるので、流速が経路に沿って変わらない屈曲では
!   正しい(屈曲の損失を作らない)が、屈曲が急な加速部(池の出口・段落ちの直前)に重なると、加速に要る慣性を
!   数えないことになり、その辺の流速は水面勾配と摩擦の釣り合いまで上がって、流れ出す元の池より高い
!   エネルギー水頭の射流を下流へ送り出す(1 セル幅の水路の段落ちの直前が斜めのつながりのとき、棚の上の
!   エネルギー水頭が池より 9〜29 m 高い。test/brink)。
!   ここでは、中立の分 (1 − w) を、面のセルへ実際に流入する水の経路の値 ū_p(path_value)に置き換える:
!     ū ← ū + (1 − w) (ū_p − u_e)     (w = 0: 供給元が壁・乾床、0 < w < 1: 薄い供給元、w = 1: 置き換えなし)
!   移流項 tae への差分は、流向面 c・n の流入面の分を
!     Δtae = −(q_n Δū_n − q_c Δū_c) / w8dr / max(h̄, dd/2) · lm
!   で足す(q_c・q_n・h̄・lm は adv_prepare_mc と同じ量)。側方面は変えない。
!   - adv_prepare_mc・adv_neumann_mc の中へ分岐を足さず、別の手続きにしている: 足すと -Ofast が既存の式の
!     計算の順序を変え、f_advection_bend = 0(当時の既定)の結果が最終桁で動く(coastal_drain が 14 桁目で 1、
!     dambreak・gwsect も reference と不一致。§110)。
!   - 面と除外の条件は adv_prepare_mc(無効な近傍・通過幅ゼロ・海セル・区間流入・両側乾燥)と
!     adv_neumann_mc(put_neumann_faces の面、鏡像セル)に合わせる。境界面には、従来どおり薄い供給元の
!     重み w を掛けない(供給元が壁・乾床の面だけ)。岸沿いに一様な場では、境界面の差分は一つ内側の面と
!     同じ値になる。
!   - 読む量: 面のセル(行 j − 1・j)の 8 リンクの uv・mn・通過幅(時刻 n。エッジ幅 2 の交換済み)、面のセルと
!     供給元の水深、g%x・g%sw、s%m・s%n・s%lm。donor_share と同じ範囲で、通信・メモリの追加はない。
!     補助関数は adv_neumann_mc の写し(枠外は鏡像で読む。枠内の面では adv_prepare_mc のものと同じ値)。
!----------------------------------------------------------------------
subroutine adv_bend_mc(p, g, s, sx, tx, boundary)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  type(t_enc_status), intent(in) :: sx
  type(t_enc_adv), intent(inout) :: tx
  logical, intent(in) :: boundary     ! 偽: 内部の面、真: 側方 Neumann の境界面
  ! 各辺を横切る面の方位(adv_neumann_mc と同じ)
  integer, parameter :: kfw(1:3) = [4, 1, 6]
  integer, parameter :: kfe(1:3) = [5, 3, 8]
  integer, parameter :: kfn(1:3) = [2, 1, 3]
  integer, parameter :: kfs(1:3) = [7, 6, 8]
  integer :: i, j, k
  logical :: tab                      ! 連結の実流量の表 tx%ql を読むか(adv_prepare_mc が同じステップに作った表。§113.7)
  logical :: wsv                      ! 流れごとの重みの控え tx%wst を読むか(同上。内部の面だけ)

  tab = allocated(tx%ql)
  wsv = allocated(tx%wst)
  if (.not. boundary) then
    ! 内部の面(adv_prepare_mc と同じ走査。書き込み先 tae(k, c + de) は (c, k) ごとに一意で競合なし)
    !$omp parallel do schedule(dynamic) private(i, j, k)
    do j = dcp%js, dcp%je
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) <= 0) cycle
        do k = 1, 4
          call bend_inner(i, j, k)
        end do
      end do
    end do
    !$omp end parallel do
  else
    ! 側方 Neumann の境界面(adv_neumann_mc と同じ走査)
    if (bcs%f_bc_side(e_side_w) == e_bc_neumann .and. dcp%ish == 1) then
      do j = max(dcp%js - 1, 1), min(dcp%je + 1, dcp%ny_g)
        call bend_boundary(1, j, kfw)
      end do
    end if
    if (bcs%f_bc_side(e_side_e) == e_bc_neumann .and. dcp%ieh == dcp%nx_g) then
      do j = max(dcp%js - 1, 1), min(dcp%je + 1, dcp%ny_g)
        call bend_boundary(dcp%nx_g, j, kfe)
      end do
    end if
    if (bcs%f_bc_side(e_side_n) == e_bc_neumann .and. dcp%js <= 1 .and. 1 <= dcp%je) then
      do i = g%wx(1,1), g%wx(2,1)
        call bend_boundary(i, 1, kfn)
      end do
    end if
    if (bcs%f_bc_side(e_side_s) == e_bc_neumann .and. dcp%js <= dcp%ny_g .and. dcp%ny_g <= dcp%je) then
      do i = g%wx(1,dcp%ny_g), g%wx(2,dcp%ny_g)
        call bend_boundary(i, dcp%ny_g, kfs)
      end do
    end if
  end if

contains

  ! 内部の面 (ci, cj) → k 近傍(k = 1..4)。除外の条件は adv_prepare_mc と同じ
  subroutine bend_inner(ci, cj, k)
    integer, intent(in) :: ci, cj, k
    integer :: in, jn
    in = ci + din(k)
    jn = cj + djn(k)
    if (g%x(in,jn) <= 0) return
    if (geo%skip8(k)) return
    if (g%sw(ci,cj) > 0 .or. g%sw(in,jn) > 0) return
    if (bcs%have_inflow) then
      if (opt%f_inflow_edge == 0) then
        if (bc_inflow_cell(ci, cj) .or. bc_inflow_cell(in, jn)) return
      else
        if (bc_inflow_inward(ci, cj, in, jn)) return
      end if
    end if
    if (s%h(ci,cj) < p%dd .and. s%h(in,jn) < p%dd) return
    call bend_face(ci, cj, k, in, jn, in, jn, opt%f_advection_donor == 3)
  end subroutine

  ! 枠のセル (ci, cj) の境界面(kf の 3 面)。面の選別と除外の条件は adv_neumann_mc と同じ
  subroutine bend_boundary(ci, cj, kf)
    integer, intent(in) :: ci, cj
    integer, intent(in) :: kf(1:3)
    integer :: mf, k, in, jn, je, im, jm
    logical :: ok
    if (g%x(ci,cj) <= 0) return
    if (g%sw(ci,cj) > 0) return
    do mf = 1, 3
      k = kf(mf)
      in = ci + din(k)
      jn = cj + djn(k)
      if (.not. bc_open_face(in, jn)) cycle
      je = cj + dje(k)
      if (je < dcp%js - 1 .or. je > dcp%je) cycle
      call bc_neumann_cell(in, jn, ok, im, jm)
      if (.not. ok) cycle
      if (g%x(im,jm) <= 0) cycle
      if (g%sw(im,jm) > 0) cycle
      if (geo%skip8(k)) cycle
      if (bc_inflow_cell(ci, cj) .or. bc_inflow_cell(im, jm)) cycle
      if (s%h(ci,cj) < p%dd .and. s%h(im,jm) < p%dd) cycle
      call bend_face(ci, cj, k, in, jn, im, jm, .false.)
    end do
  end subroutine

  ! 面 (ci, cj) → (in, jn)(k = 1..8。(im, jm) は n の水理量を読むセル = 内部の面では n 自身、境界面では鏡像)の
  ! 流向面の流入面の、中立の分を経路の値に置き換える差分を tae に足す。thin が真なら、薄い供給元の重み
  ! (donor_share)の分も置き換える
  subroutine bend_face(ci, cj, k, in, jn, im, jm, thin)
    integer, intent(in) :: ci, cj, k, in, jn, im, jm
    logical, intent(in) :: thin
    integer :: ie, je
    real :: ue, qc, qn, dc, dn, w, hb, lme, ta
    real :: ec, en        ! エネルギー形の項(f_advection_bend = 2)の、面 c・n の分((1 − w) × arrival_excess。0 以上)
    ie = ci + die(k)
    je = cj + dje(k)
    ue = sgn8(k) * sx%uv(ke8(k),ie,je)
    qc = s%m(ci,cj) * geo%n8x(k) + s%n(ci,cj) * geo%n8y(k)
    qn = s%m(im,jm) * geo%n8x(k) + s%n(im,jm) * geo%n8y(k)
    dc = 0.0
    dn = 0.0
    ec = 0.0
    en = 0.0
    if (qc >= 0) then
      w = 1.0
      if (.not. cell_ok(ci - din(k), cj - djn(k))) then
        w = 0.0
      else if (thin) then
        ! 流れごとの重みは、adv_prepare_mc が同じ面について計算した控えを読む(同じ式・同じ値。thin が真の面は
        ! 内部の面で、k = 1..4。控えがない(−1)面は、従来どおり計算する。§113.7)
        w = -1.0
        if (wsv) w = tx%wst(1,k,ie,je)
        if (w < 0.0) then
          w = donor_share(ci, cj, 9 - k)
          if (opt%adv_stream) w = stream_share(ci, cj, 9 - k, qc, w)
        end if
      end if
      if (w < 1.0) dc = (1.0 - w) * (path_value(ci, cj, k, 1.0, ue) - ue)
      ! エネルギー形の項。面のセルが、境界として与えたセル(水位規定セル・湧き出しのセル)のときは数えない(外から
      ! 入ってくる水は、流れてきた水。§113.9)
      if (opt%adv_energy) then
        if (w < 1.0 .and. ue > 0.0 .and. .not. given_cell(ci, cj)) ec = (1.0 - w) * arrival_excess(ci, cj, k, ue)
      end if
    end if
    if (qn < 0) then
      w = 1.0
      if (.not. cell_ok(in + din(k), jn + djn(k))) then
        w = 0.0
      else if (thin) then
        w = -1.0
        if (wsv) w = tx%wst(2,k,ie,je)
        if (w < 0.0) then
          w = donor_share(in, jn, k)
          if (opt%adv_stream) w = stream_share(in, jn, k, -qn, w)
        end if
      end if
      if (w < 1.0) dn = (1.0 - w) * (path_value(in, jn, 9 - k, -1.0, ue) - ue)
      if (opt%adv_energy) then
        if (w < 1.0 .and. ue < 0.0 .and. .not. given_cell(in, jn)) en = (1.0 - w) * arrival_excess(in, jn, 9 - k, ue)
      end if
    end if
    if (ec > 0.0 .or. en > 0.0) then
      call bend_energy(ci, cj, k, im, jm, ie, je, qc, qn, dc, dn, ec, en)
      return
    end if
    if (dc == 0.0 .and. dn == 0.0) return
    hb = (vol_depth(ci, cj) + vol_depth(im, jm)) / 2
    lme = (s%lm(ci,cj) + s%lm(im,jm)) / 2
    ta = -(qn * dn - qc * dc) / geo%w8dr(k)
    tx%tae(ke8(k),ie,je) = tx%tae(ke8(k),ie,je) + sgn8(k) * ta / max(hb, p%dd / 2) * lme
  end subroutine

  ! f_advection_bend = 2 の面(エネルギー形の項が正の面)の tae への差分。tc・tn は、面 c・n の項の
  ! 「辺の正の向きの加速度 × h̄ × w8dr」で、経路の値の項は、面 c が q_c Δū_c、面 n が −q_n Δū_n(1 と同じ)。
  ! これとエネルギー形の項を、面ごとに、減速の大きい方で取る:
  !   面 c(u_e > 0 の流れの上流側): tc = min(q_c Δū_c, −e_c h̄)        e_c = (1 − w) φ max(u_e² − a², 0) / 2
  !   面 n(u_e < 0 の流れの上流側): tn = max(−q_n Δū_n, +e_n h̄)
  ! どちらも「入ってきた水が、この辺の流速まで加速する分」を数える項なので、足し合わせない(1 本の経路で加速する
  ! 流れでは、運動量形の経路の値の項 q/h̄·(u_e − ū_p) が、エネルギー形の (u_e + a)/2·(u_e − a) 以上になり、1 と同じ
  ! 値になる)。h̄ で割る前の形にそろえるため、エネルギー形の項に h̄ を掛けておく
  subroutine bend_energy(ci, cj, k, im, jm, ie, je, qc, qn, dc, dn, ec, en)
    integer, intent(in) :: ci, cj, k, im, jm, ie, je
    real, intent(in) :: qc, qn, dc, dn, ec, en
    real :: hb, lme, tc, tn
    hb = (vol_depth(ci, cj) + vol_depth(im, jm)) / 2
    lme = (s%lm(ci,cj) + s%lm(im,jm)) / 2
    tc = qc * dc
    tn = -qn * dn
    if (ec > 0.0) tc = min(tc, -ec * hb)
    if (en > 0.0) tn = max(tn, en * hb)
    tx%tae(ke8(k),ie,je) = tx%tae(ke8(k),ie,je) + sgn8(k) * ((tc + tn) / geo%w8dr(k)) / max(hb, p%dd / 2) * lme
  end subroutine

  ! セル (ci, cj) が、境界として与えたセル(水位規定セルか、流量を湧き出しで与えるセル。§113.9)か。印がなければ
  ! (どちらもない)偽。側方 Neumann の境界面の、枠外の面のセル n は、鏡像のセルの印を読む(境界面の扱いを、枠の
  ! 中の面とそろえる。枠外を偽にしていた初めの形は、水位規定セルの列が側方 Neumann の辺に接する角で、枠の中の面は
  ! 「数えない」、境界面は「数える」になり、角の行に岸沿いの流れができて発散した。§113.9 (7))。確保範囲の外は偽
  pure function given_cell(ci, cj) result(r)
    integer, intent(in) :: ci, cj
    logical :: r
    integer :: mi, mj
    r = .false.
    if (.not. allocated(tx%gvn)) return
    call mirror_cell(ci, cj, mi, mj)
    if (mi < dcp%ish .or. mi > dcp%ieh .or. mj < dcp%jsh .or. mj > dcp%jeh) return
    r = tx%gvn(mi,mj)
  end function

  ! 到着した水の速さからの加速(f_advection_bend = 2。developer.md §112.11・§113。ENCflow 独自)。
  !   経路の値 ū_p = f Q_in / (W_e h̆_in) は、流入のうちこの辺へ出る分が、この辺の幅で流れたときの流速 = 連続式から
  !   決まる流速で、定常では u_e h_e / h̆_in になる。数えるのは、経路に沿って水深が変わる分の加速だけで、(a) 流入が
  !   複数の連結から合わさる面のセル(合流・角のセル)で、遅い流れが合わさって速く出ていく加速と、(b) 流出の一部
  !   だけが出ていく辺(寄せる度合いに f を掛けるので、ほぼ中立)の加速を数えない。こういう辺は、水面勾配と摩擦の
  !   つり合いの流速まで上がり、角のセルと河道のセルの間を水が回ると、周回のたびにエネルギーが増える
  !   (test/stairbank の sab。§112.8)。
  !   ここでは、面のセルへ水を運ぶ連結 l(この辺と、海セルからの流入を除く。実流量 Q_l、流速の大きさ s_l、通過幅
  !   W_l)から「到着した水の速さ」a を
  !     a² = Σ Q_l (s_l c_l)² / max(Σ Q_l, ε (Σ Q_l + Q_un))、   c_l = max(f W_l / W_e, min(1, W_l / W_e))、   f = Q_e / Q_out
  !   で取り、辺の流速がそれを上回る分 φ max(u_e² − a², 0) / 2 を返す。呼び出し側が、中立の分 (1 − w) を掛けて、
  !   検査体積の長さで割り、エネルギー水頭を保存する形の移流項 (u_e² − a²) / (2 L) として、減速の向きに足す。
  !   - Q_un = max(Q_out − Σ Q_l − Q_sea, 0) は、流出のうち流入で賄われない分(面のセルの貯留・湧き出し・降雨から
  !     出る水)。流入が、海セルからでない供給(Σ Q_l + Q_un)の ε(p_adv_donor_eps)倍以上あれば、a は流入の連結の
  !     速さそのもの(賄われない分も、流れと同じ速さで動いているとみる)。ε 倍に満たなければ、分母を ε 倍で下から
  !     止める = 流入が減るにつれて a → 0(賄われない分は、静止から動き出す水。経路の値と同じ考え方。§110)。
  !     流入のない池の出口の辺は、静止からの加速 u_e² / 2 を数えることになる。
  !     流入のリンクがないセル(Σ Q_l = 0)も a = 0 で、流入が丸めの大きさであるか・ないかで値が飛ばない。
  !     ただし、境界として与えたセル(水位規定セルと、流量を湧き出しで与えるセル)から出る水には、この項を数えない
  !     (呼び出し側が given_cell で外す): 与えたセルから入ってくる水は、外から流れてきた水で、静止から動き出す水
  !     ではない(海セル・区間流入の面と同じ扱い)。水位規定セルで数えると、流入の水位境界のすぐ内側に、速度水頭
  !     ぶんの落差ができ、壁ぎわの行(斜めの連結が欠ける)とそれ以外で落差が違うので、横断方向に一様な流れに、
  !     横断方向の差を作る(test/nhcurrent。§113.9)。湧き出しのセルで数えると、流量を与えるセルが、流出の速度水頭の
  !     分だけ深くなる(test/brink の直線の水路の上流端で +0.27〜0.63 m。§113.5)。
  !     経路の値は、流入が流出の ε 倍に満たないとき中立へ寄せる(流入のない面のセルを 0 と同じにする。§110.10)が、
  !     ここは寄せない: 寄せると、流入が流出の ε 倍に満たないセルから出る辺が、どれも中立のままになり、
  !     test/stairbank の段のある河道で、流量の標準偏差の最大が 10 → 184 m³/s に増えた(§113。境界として与えた
  !     セルだけを外す形では、10 m³/s のまま = §113.9)。
  !   - 定常で w = 0 の辺は u_e² = a² + 2g(η_上 − η_下) −(摩擦の分)になり、入ってきた水のエネルギーを超えない。
  !     流速を頭打ちする形(定常の Bernoulli の上限)は、長波の山の後ろ側(水が、水位の上がる向きへ進みながら
  !     減速している所)で流速を切ってしまい、走時が解析解から 5〜22 % ずれた(test/steepwave。§112.11)。移流項と
  !     して入れると、非定常の流れでも運動方程式の項として働く。
  !   - 辺が到着した水より遅いとき(u_e² ≤ a²)は 0(入ってきた水の運動量で、辺を押さない。§102)。
  !   - c_l は、連結 l の流速を、この辺の通過幅に直す換算。広い連結へ出るときは、幅の比で遅くなる(対角 → 軸で
  !     0.707)。狭い連結へ入るときは、流れの全部が入るなら(f = 1)幅の比で速くなる分を数え(軸 → 対角で 1.41。
  !     階段の「幅の違いは加減速に数えない」取り決め。§110.6。path_value と同じ)、一部が枝分かれして入るなら、
  !     入ってきた速さのまま。
  !   - φ = (Σ Q_l + Q_un) / (Σ Q_l + Q_un + Q_sea) は、海セルからの流入(Q_sea)でない割合。海陸エッジの流速は
  !     見かけ水柱厚の尺度で、到着の速さに使えない(§68.35)ので、海からの流入の分は数えない(path_value と同じ)。
  !   - この辺が面のセルの流出でない(Q_e ≤ 0)とき、この辺の通過幅が 0 のときは 0。
  !   読むのは、面のセルの 8 リンクの uv・mn・通過幅(path_value と同じ範囲)。8 本の和は、対称な対ごとに取る
  pure function arrival_excess(ci, cj, kout, ue0) result(e)
    integer, intent(in) :: ci, cj     ! 面のセル
    integer, intent(in) :: kout       ! 面のセルから見た、この辺の方位(8 近傍番号)
    real, intent(in) :: ue0           ! この辺の流速
    real :: e
    real :: cq(1:8), c2(1:8), co(1:8), ca(1:8), q8(1:8)
    real :: q, qin, q2, qout, qsea, qun, qe, we, wl, fsh, cl, a2
    integer :: l, mi, mj
    logical :: sea
    e = 0.0
    we = wlk8(ci, cj, kout)
    if (we <= 0.0) return
    call links8(ci, cj, q8)
    do l = 1, 8
      cq(l) = 0.0
      co(l) = 0.0
      ca(l) = 0.0
      q = q8(l)
      if (q > 0.0) then
        co(l) = q
      else if (q < 0.0 .and. l /= kout) then
        call mirror_cell(ci + din(l), cj + djn(l), mi, mj)
        sea = .false.
        if (mi >= 1 .and. mi <= g%nx .and. mj >= 1 .and. mj <= dcp%ny_g) sea = g%sw(mi,mj) > 0
        if (sea) then
          ca(l) = -q
        else
          cq(l) = -q
        end if
      end if
    end do
    qe = co(kout)
    if (qe <= 0.0) return
    qin = ((cq(2) + cq(7)) + (cq(4) + cq(5))) + ((cq(1) + cq(8)) + (cq(3) + cq(6)))
    qout = ((co(2) + co(7)) + (co(4) + co(5))) + ((co(1) + co(8)) + (co(3) + co(6)))
    qsea = ((ca(2) + ca(7)) + (ca(4) + ca(5))) + ((ca(1) + ca(8)) + (ca(3) + ca(6)))
    qun = max(qout - qin - qsea, 0.0)
    if (qin + qun <= 0.0) return      ! 流出の全部が、海セルからの流入で賄われている
    fsh = qe / qout
    do l = 1, 8
      c2(l) = 0.0
      if (cq(l) <= 0.0) cycle
      wl = wlk8(ci, cj, l)
      cl = max(fsh * wl / we, min(1.0, wl / we))
      c2(l) = cq(l) * (abs(uvk8(ci, cj, l)) * cl)**2
    end do
    q2 = ((c2(2) + c2(7)) + (c2(4) + c2(5))) + ((c2(1) + c2(8)) + (c2(3) + c2(6)))
    a2 = q2 / max(qin, opt%p_adv_donor_eps * (qin + qun))
    if (ue0**2 <= a2) return
    e = (ue0**2 - a2) / 2
    if (qsea > 0.0) e = e * ((qin + qun) / (qin + qun + qsea))
  end function

  ! 経路の値 ū_p。面のセル (ci, cj) へ実際に水を運ぶリンク l(この辺を除く。実流量 Q_l > 0、速さ s_l、辺の
  ! 水深 he_l = │mn_l│ / s_l)から
  !   ū_p = u_e + f g (σ f Q_in / (W_e h̆_in) − u_e)        (g は下の 2 つの重み。ふつうは 1)
  !   Q_in = Σ Q_l、h̆_in = Σ Q_l s_l he_l / Σ Q_l s_l(流入の水深の、運動量流束 Q s で重み付けした平均。
  !   Q s he = Q │mn│)、W_e = この辺の通過幅 l8·frw·fwd、f = Q_e / Q_out(面のセルの流出のうち、この辺が占める
  !   割合)、σ = 面のセルから出る向きを正としたときの、この辺の流速の符号の向き(面 c で +1、面 n で −1)。
  ! - σ f Q_in / (W_e h̆_in) は「この辺へ曲がる分の流入が、この辺の幅で、流入時の水深のまま流れたときの流速」。
  !   経路に沿って水深が変わらなければ(定常で Q_in = Q_out)u_e に一致して中立と同じになり、等流の屈曲に
  !   損失を作らない(§68.8 の性質を保つ)。経路に沿って水深が減る(加速する)ところでは u_e より小さく、
  !   その差が加速に要る慣性になる。
  ! - 流入するリンクの流速そのものでなく、幅をそろえた値にするのは、斜めのリンクの通過幅が軸のリンクの
  !   0.707 倍(1 セル幅の斜めの河道の自然幅)で、等流でも流速が 1.41 倍になるため。流速そのものを使うと、
  !   軸と斜めが交互に並ぶ河道で幅の違いが加減速に数えられ、等流の水深が ±6〜9 % 動く(§110.6 の試作 1)。
  ! - f を 2 度掛ける: 流入のうちこの辺へ出る分(f Q_in)を取り、中立から寄せる度合いにも f を使う。本流の
  !   横から河岸へあふれる辺(f ≪ 1)は中立のまま(本流の運動量を持ち込まない。§102 の旧 2 の失敗の型)。
  ! - この式は、流出のうち流入で賄われない分(面のセルの貯留・湧き出し・降雨から出る水)を「静止から動き出す
  !   水」と数える(r = Q_in / Q_out とすると ū_p − u_e = f u_e (r h_e / h̆_in − 1))。池の出口では正しく、流出が
  !   流入を上回ると強まり、下回ると弱まる(池の水位の揺れを抑える向き)。しかし、流入のリンクがほとんど
  !   ない面のセル(水が引いていく前線の先端、湧き出しだけのセル)まで同じに扱うと、流入が丸めの大きさで
  !   あるか・ないかで値が u_e と (1 − f) u_e の間を飛ぶ(test/wfswash の急勾配の構成で、沿岸方向に一様な
  !   場の行の差が 7e-8 m に育った。§110.10)。そこで、流入が流出の ε(p_adv_donor_eps。f_advection_donor = 3 の
  !   「ほとんど水を運ばない」のしきい値と同じ)倍に満たないときは、寄せる度合いに r / ε を掛けて中立へ
  !   連続につなぐ。流入のない面のセルは中立(u_e)のまま = 0 と同じ。
  ! - f_advection_donor = 4 のときは、流出が流入の ε 倍に満たない面のセル(水が四方から入ってくる、溜まるだけの
  !   セル)も、寄せる度合いに Q_out / (ε Q_in) を掛けて、中立へ連続につなぐ(上の扱いの、逆向きの対)。f = Q_e / Q_out は、
  !   流出がこの辺の丸めの大きさの流量だけのとき 1 になり、「流入の全部がこの辺へ出る」と数えてしまう。流れごとの
  !   重み(4)は内部の面でも 1 未満になるので、対称な流れの、流量が 0 の辺(両側のセルから水が寄ってくる辺)に、
  !   辺の流量の丸めの符号で決まる向きの力が入った(test/nest_identity の非静水圧の項目。§113.9)。f_advection_donor が
  !   3 以下のときは掛けない(経路の値が効くのは、線の上流側が壁・乾床・薄い水膜の面だけで、その結果を変えない)。
  ! - 海セルからの流入(海陸エッジの水深は見かけ水柱厚 hsea0 の尺度で、流入の水深に使えない。§68.35)は
  !   Q_in に数えず、寄せる度合いに「流入のうち海セルからでない割合」を掛ける(海からの流入だけの面の
  !   セルは中立のまま。海側のリンクの流れが反転するところで値が飛ばない)。
  ! - 流入の線が面のセルの先へ続いている(流入リンク l の反対側の隣のセルが、面のセルと同じ水体)とき、その
  !   流入の運動量は、通常の風上(線 k の供給元)が同じ線の先の辺へ運ぶ。上の式は ū_p − u_e ∝ u_e (r h_e / h̆_in − 1)
  !   (h_e = Q_e / (W_e │u_e│) はこの辺の水深)なので、流入がこの辺より浅い(h̆_in < h_e)と u_e より大きく、同じ
  !   運動量を、曲がって出るこの辺にも足すことになる(落差から浅く速い流れが落ち込む合流部の池で、湾の水を
  !   余分に押し出し、水面の揺れを育てた。§110.14)。そこで、線が続いている流入は、水深を h_e で下から止めて数える:
  !     h'_l = β_l h_l + (1 − β_l) max(h_l, h_e)、  β_l = 1 − min(1, h_o / (ε h_c))
  !   h_o は反対側の隣のセルの水深、h_c は面のセルの水深、ε は p_adv_donor_eps(壁・乾床なら β = 1 = そのまま)。
  !   足す向き(減速する屈曲)には数えず、引く向き(加速する屈曲に要る慣性。中立より運動量を増やさない)は
  !   そのまま数える。等流(水深が一様で r = 1)では h'_l = h_e で、岸の形によらず中立。流入の線の先が全て壁・
  !   乾床の 1 セル幅の水路は、この扱いの前と同じ式・同じ演算(§110.15)。
  ! - この辺が面のセルの流出でない(Q_e ≤ 0)ときは u_e(置き換えなし。Q_e → 0 で f → 0 なので連続)。
  ! - 8 本のリンクの和は、格子の対称操作(鏡映・90° 回転)で入れ替わる対(向かい合うリンク)ごとに取る。
  pure function path_value(ci, cj, kout, sg, ue0) result(u)
    integer, intent(in) :: ci, cj     ! 面のセル(境界面の面 n では枠外。リンクは鏡像で読む)
    integer, intent(in) :: kout       ! 面のセルから見た、この辺の方位(8 近傍番号)
    real, intent(in) :: sg            ! σ(面 c で +1、面 n で −1)
    real, intent(in) :: ue0           ! この辺の流速 u_e(c → n が正)
    real :: u
    real :: cq(1:8), cs(1:8), cm(1:8), co(1:8), ca(1:8)
    real :: q, qin, qs, qm, qout, qsea, qe, qth, we, den, fsh, wgt, se, he, hlim, beta
    integer :: l, mi, mj, oi, oj
    logical :: sea, tin
    u = ue0
    ! 枠内の面のセルは、連結の実流量の表を読む(有効時。qlk8 と同じ値。§113.7)
    tin = tab .and. ci >= 1 .and. ci <= g%nx .and. cj >= 1 .and. cj <= dcp%ny_g
    do l = 1, 8
      cq(l) = 0.0
      cs(l) = 0.0
      cm(l) = 0.0
      co(l) = 0.0
      ca(l) = 0.0
      if (tin) then
        q = tx%ql(l,ci,cj)
      else
        q = qlk8(ci, cj, l)
      end if
      if (q > 0.0) then
        co(l) = q
      else if (q < 0.0 .and. l /= kout) then
        call mirror_cell(ci + din(l), cj + djn(l), mi, mj)
        sea = .false.
        if (mi >= 1 .and. mi <= g%nx .and. mj >= 1 .and. mj <= dcp%ny_g) sea = g%sw(mi,mj) > 0
        if (sea) then
          ca(l) = -q
        else
          cq(l) = -q
          cs(l) = -q * abs(uvk8(ci, cj, l))
          cm(l) = -q * abs(mnk8(ci, cj, l))
        end if
      end if
    end do
    qe = co(kout)
    if (qe <= 0.0) return
    ! 線が続いている流入の水深を、この辺の水深 h_e で下から止める(Q s h' = cm + (1 − β) max(0, Q s h_e − cm)。
    ! cm = Q │mn│ = Q s h。β = 1 の流入は cm のまま)
    se = abs(uvk8(ci, cj, kout))
    hlim = opt%p_adv_donor_eps * hcell(ci, cj)
    if (se > 0.0 .and. hlim > 0.0) then
      he = abs(mnk8(ci, cj, kout)) / se
      do l = 1, 8
        if (cq(l) <= 0.0) cycle
        oi = ci + din(9 - l)
        oj = cj + djn(9 - l)
        if (.not. cell_ok(oi, oj)) cycle
        beta = 1.0 - min(1.0, hcell(oi, oj) / hlim)
        if (beta < 1.0) cm(l) = cm(l) + (1.0 - beta) * max(0.0, cs(l) * he - cm(l))
      end do
    end if
    qin = ((cq(2) + cq(7)) + (cq(4) + cq(5))) + ((cq(1) + cq(8)) + (cq(3) + cq(6)))
    qs = ((cs(2) + cs(7)) + (cs(4) + cs(5))) + ((cs(1) + cs(8)) + (cs(3) + cs(6)))
    qm = ((cm(2) + cm(7)) + (cm(4) + cm(5))) + ((cm(1) + cm(8)) + (cm(3) + cm(6)))
    qout = ((co(2) + co(7)) + (co(4) + co(5))) + ((co(1) + co(8)) + (co(3) + co(6)))
    qsea = ((ca(2) + ca(7)) + (ca(4) + ca(5))) + ((ca(1) + ca(8)) + (ca(3) + ca(6)))
    if (qin <= 0.0 .or. qs <= 0.0) return
    we = wlk8(ci, cj, kout)
    den = we * qm
    if (den <= 0.0) return
    fsh = qe / qout
    ! 中立から寄せる度合い: f ×(流入が流出の ε 倍に満たなければ、その比)×(流入のうち海セルからでない割合)。
    ! 割り算は qin < qth のときだけ(qth > qin > 0。商は 1 未満)
    wgt = fsh
    qth = opt%p_adv_donor_eps * qout
    if (qin < qth) wgt = wgt * (qin / qth)
    if (opt%adv_stream) then
      qth = opt%p_adv_donor_eps * qin
      if (qout < qth) wgt = wgt * (qout / qth)
    end if
    if (qsea > 0.0) wgt = wgt * (qin / (qin + qsea))
    u = ue0 + wgt * (sg * fsh * qin * qs / den - ue0)
  end function

  ! 線 k の供給元の重み(f_advection_donor = 3。adv_prepare_mc の donor_share と同じ値)。
  ! 式は「流量の比が ε 未満で、かつ水深の比も ε 未満のとき w = max(流量の比, 水深の比) / ε、ほかは 1」。
  ! adv_prepare_mc は流量の条件を先に見るが、ここは水深の条件を先に見る: 薄くない供給元(水深が面のセルの
  ! ε 倍以上)は流量の比によらず w = 1 なので、8 本のリンクの流量を読むのは薄い供給元のときだけになる
  ! (大半の面はここで抜ける。値は同じ。秩父の 200 m 格子で、有効時の計算時間の増分が +30 % → +20 %)。
  ! 供給元のセルは呼び出し側が cell_ok で確かめている(確保範囲内の濡れたセル)。
  pure function donor_share(ci, cj, kk) result(w)
    integer, intent(in) :: ci, cj, kk
    real :: w, qk, qmax, qe, hd, he
    integer :: l
    w = 1.0
    hd = hcell(ci + din(kk), cj + djn(kk))
    he = opt%p_adv_donor_eps * hcell(ci, cj)
    if (hd >= he) return
    if (tab .and. ci >= 1 .and. ci <= g%nx .and. cj >= 1 .and. cj <= dcp%ny_g) then    ! 表から読む(同じ値。§113.7)
      qk = max(0.0, -tx%ql(kk,ci,cj))
      qmax = 0.0
      do l = 1, 8
        qmax = max(qmax, -tx%ql(l,ci,cj))
      end do
    else
      qk = max(0.0, -qlk8(ci, cj, kk))
      qmax = 0.0
      do l = 1, 8
        qmax = max(qmax, -qlk8(ci, cj, l))
      end do
    end if
    qe = opt%p_adv_donor_eps * qmax
    if (qk < qe) w = max(qk / qe, hd / he)
  end function

  ! 流れごとの重み(f_advection_donor = 4。adv_prepare_mc の stream_share・src_fwd と同じ式・同じ値。説明はそちら。
  ! 面のセルの実流量は qlk8 で、斜めの流入元のセルの実流量は links8 で読む: 枠内のセルでは、qlk と同じ値)
  pure function stream_share(ci, cj, kk, qf, w3) result(w)
    integer, intent(in) :: ci, cj     ! 面のセル
    integer, intent(in) :: kk         ! 面のセルから見た、線 k の供給元の 8 近傍番号
    real, intent(in) :: qf            ! 面を通る単位幅流量(検査体積へ入る向きが正)
    real, intent(in) :: w3            ! 3 の重み(donor_share)
    real :: w
    real :: ql(1:8), qo(1:8), fl(1:8), wl(1:8), q, qin, qth, isg, oh, th, num, den
    integer :: l
    w = w3
    if (qf <= 0.0) return
    do l = 1, 8
      q = qlk8(ci, cj, l)
      ql(l) = max(0.0, -q)
      qo(l) = max(0.0, q)
      fl(l) = tx%gst(l,kk) * ql(l)
    end do
    qin = ((ql(2) + ql(7)) + (ql(4) + ql(5))) + ((ql(1) + ql(8)) + (ql(3) + ql(6)))
    if (qin <= 0.0) return
    isg = ((fl(2) + fl(7)) + (fl(4) + fl(5))) + ((fl(1) + fl(8)) + (fl(3) + fl(6)))
    oh = qf * tx%w8lt(ke8(kk)) - isg
    do l = 1, 8
      wl(l) = 0.0
      if (ql(l) <= 0.0) then
        fl(l) = 0.0
        cycle
      end if
      fl(l) = fl(l) + oh * (ql(l) / qin)
      if (fl(l) <= 0.0) then
        fl(l) = 0.0
        cycle
      end if
      if (l == kk) then
        wl(l) = fl(l)
      else if (tx%gst(l,kk) > 0.0) then
        th = 1.0
        if (p_stream_kappa * ql(kk) < ql(l)) then
          th = p_stream_kappa * ql(kk) / ql(l)
          th = th + (1.0 - th) * (1.0 - src_fwd(ci + din(l), cj + djn(l), kk)) * w3
        end if
        wl(l) = fl(l) * th
      else
        wl(l) = fl(l) * w3
      end if
    end do
    den = ((fl(2) + fl(7)) + (fl(4) + fl(5))) + ((fl(1) + fl(8)) + (fl(3) + fl(6)))
    if (den <= 0.0) return
    num = ((wl(2) + wl(7)) + (wl(4) + wl(5))) + ((wl(1) + wl(8)) + (wl(3) + wl(6)))
    w = min(1.0, max(0.0, num / den))
    ! 流入が流出の ε 倍に満たないとき・面の流量がこの辺(面のセルの 9 − kk 近傍へ向かう辺)の単位幅流量の ε 倍に
    ! 満たないときは、3 の重みへ寄せる(割り算は、そのときだけ。商は 1 未満)。w = w_3 の面(大半の面)は、寄せても
    ! 同じ値なので、流出の和と辺の流量を読まない
    if (w /= w3) then
      qth = opt%p_adv_donor_eps * (((qo(2) + qo(7)) + (qo(4) + qo(5))) + ((qo(1) + qo(8)) + (qo(3) + qo(6))))
      if (qin < qth) w = w3 + (w - w3) * (qin / qth)
      qth = opt%p_adv_donor_eps * abs(mnk8(ci, cj, 9 - kk))
      if (qf < qth) w = w3 + (w - w3) * (qf / qth)
    end if
  end function

  ! セル (si, sj) への流入のうち、kk 近傍から面のセルへ向かう向きに前向きの連結(gst > 0)から入る割合
  ! (stream_share の ω_o)。流入がなければ 1。領域の枠の外のセル(側方 Neumann の辺の外。8 リンクを持たない)も 1
  pure function src_fwd(si, sj, kk) result(r)
    integer, intent(in) :: si, sj, kk
    real :: r, q(1:8), q8(1:8), qa, qf, qth
    integer :: l
    r = 1.0
    if (si < 1 .or. si > g%nx .or. sj < 1 .or. sj > dcp%ny_g) return
    call links8(si, sj, q8)
    q(1:8) = max(0.0, q8(1:8))
    qth = opt%p_adv_donor_eps * (((q(2) + q(7)) + (q(4) + q(5))) + ((q(1) + q(8)) + (q(3) + q(6))))
    q(1:8) = max(0.0, -q8(1:8))
    qa = ((q(2) + q(7)) + (q(4) + q(5))) + ((q(1) + q(8)) + (q(3) + q(6)))
    if (qa <= 0.0) return
    do l = 1, 8
      if (tx%gst(l,kk) <= 0.0) q(l) = 0.0
    end do
    qf = ((q(2) + q(7)) + (q(4) + q(5))) + ((q(1) + q(8)) + (q(3) + q(6)))
    r = qf / qa
    if (qa < qth) r = 1.0 - (1.0 - r) * (qa / qth)
  end function

  ! セル (ci, cj) から 8 近傍のそれぞれへ向かう連結の実流量(流出が正。qlk8 と同じ値)。有効時、枠内のセルは、
  ! 連結の実流量の表(adv_prepare_mc の fill_links が同じステップに作った qlk の値)を読む: 枠内のセルでは、qlk8 は
  ! 鏡像を使わず、qlk と同じエッジを同じ式で読む。枠外のセル(側方 Neumann の境界面の面 n)は、qlk8 が鏡像で読むので、
  ! その場で計算する(§113.7。結果を変えない)
  pure subroutine links8(ci, cj, q8)
    integer, intent(in) :: ci, cj
    real, intent(out) :: q8(1:8)
    integer :: l
    if (tab .and. ci >= 1 .and. ci <= g%nx .and. cj >= 1 .and. cj <= dcp%ny_g) then
      q8(1:8) = tx%ql(1:8,ci,cj)
    else
      do l = 1, 8
        q8(l) = qlk8(ci, cj, l)
      end do
    end if
  end subroutine

  ! 以下は adv_neumann_mc の補助関数の写し(枠外の位置は鏡像で読む)
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

  ! 通過幅 l8·frw·fwd (m)。確保範囲外は 0
  pure function wlk8(ci, cj, kk) result(w)
    integer, intent(in) :: ci, cj, kk
    real :: w
    integer :: ei, ej, mi, mj
    mi = ci
    mj = cj
    ei = ci + din(kk)
    ej = cj + djn(kk)
    if (ei < 1 .or. ei > g%nx .or. ej < 1 .or. ej > dcp%ny_g) call mirror_cell(ci, cj, mi, mj)
    ei = mi + die(kk)
    ej = mj + dje(kk)
    if (ei < lbound(sx%mn, 2) .or. ei > ubound(sx%mn, 2) .or. ej < dcp%jsh - 1 .or. ej > dcp%jeh) then
      w = 0.0
    else
      w = geo%l8(kk)
      if (chn%have_frw) w = w * chn%frw(ke8(kk), ei, ej)
      if (chn%have_fwd) w = w * chn%fwd(ke8(kk), ei, ej)
    end if
  end function

  ! 実流量 mn·l8·frw·fwd (m3/s。流出が正。adv_neumann_mc の qlk8 と同じ式)
  pure function qlk8(ci, cj, kk) result(q)
    integer, intent(in) :: ci, cj, kk
    real :: q, fw
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
      fw = 1.0
      if (chn%have_frw) fw = chn%frw(ke8(kk), ei, ej)
      if (chn%have_fwd) fw = fw * chn%fwd(ke8(kk), ei, ej)
      q = sgn8(kk) * sx%mn(ke8(kk),ei,ej) * geo%l8(kk) * fw
    end if
  end function

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

  pure function hcell(ci, cj) result(h)
    integer, intent(in) :: ci, cj
    real :: h
    integer :: mi, mj
    call mirror_cell(ci, cj, mi, mj)
    h = s%h(mi,mj)
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
