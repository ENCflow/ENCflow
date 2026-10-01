submodule(m_swflow_enc) m_swflow_enc_adv
  use m_state, only : t_state
  use m_parallel, only : dcp   ! 親経由のホスト結合は nvfortran バグ回避のため直接 use
  implicit none

  type t_enc_adv
    ! --- スキーム1(セル中心勾配 v1)の内部場 ---
    ! セル中心での移流項(第1添字は1~4,それぞれ風上差分と中心差分のx,y成分)
    real, allocatable :: taxy(:,:,:)
    real, allocatable :: ulm(:,:)    ! セル中心でのu*lm (移流項計算用)
    real, allocatable :: vlm(:,:)    ! セル中心でのv*lm (移流項計算用)
    ! --- スキーム2,3(運動量保存形。developer.md §68.6)の内部場 ---
    ! エッジ上の移流項(1:4, 0:nx, jsh-1:jeh。uv/mn と同じ格納規約)。
    ! prepare が時刻 n の uv/m/n/h から全エッジぶんを前計算し、momentum の
    ! adv_edge は読むだけ(uv は単一バッファで momentum 中に更新されるため、
    ! 他エッジの uv を momentum 内で読んではならない。§7・§8)
    real, allocatable :: tae(:,:,:)
    real :: w8lt(1:4) = 0.0          ! k 方向エッジの運動量検査体積の横断幅
  end type
  type(t_enc_adv) :: tx_mod

  ! 運動量保存形の方位定数(k=1..4 のみ。prepare は基準セルから k=1..4 の
  ! エッジを書くため)。線 k の方向 d = (din, djn)、横断方向 +t = (-d_y, d_x)
  ! に平行な隣接エッジの基準セルのオフセット δ+:
  !   k=1 d=(-1,-1) → δ+=( 1,-1)   k=2 d=(0,-1) → δ+=(1, 0)
  !   k=3 d=( 1,-1) → δ+=( 1, 1)   k=4 d=(-1,0) → δ+=(0,-1)
  integer, parameter :: dti(1:4) = [ 1, 1, 1, 0 ]
  integer, parameter :: dtj(1:4) = [ -1, 0, 1, -1 ]
  ! 対角エッジ(k=1,3)の側方面は中心を通るセルが1つに定まる:
  !   面の中心 = c + (δ± + d)/2。k=1: +側 (0,-1) / -側 (-1,0)、
  !   k=3: +側 (1,0) / -側 (0,-1)。軸エッジ(k=2,4)は面の中心がセルの
  !   角になるため、角を囲む4セル(c, n, c+δ, n+δ)の平均を使う
  integer, parameter :: dfpi(1:4) = [ 0, 0, 1, 0 ]
  integer, parameter :: dfpj(1:4) = [ -1, 0, 0, 0 ]
  integer, parameter :: dfmi(1:4) = [ -1, 0, 0, 0 ]
  integer, parameter :: dfmj(1:4) = [ 0, 0, -1, 0 ]

contains
!----------------------------------------------------------------------
! 移流項の内部場の確保
!----------------------------------------------------------------------
module subroutine adv_init(p, g)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  real :: dr
  if (p%initialized) continue  ! 引数未使用の警告を抑制
  if (f_advection_scheme >= 2) then
    ! 運動量保存形: エッジ上の移流項だけを持つ(taxy/ulm/vlm は不要)
    allocate(tx_mod%tae(1:4,0:g%nx,dcp%jsh-1:dcp%jeh), source = 0.0)
    ! 検査体積の横断幅 = 平行な隣接エッジとの垂直距離
    !   軸エッジ: k=2(法線 y)は dx、k=4(法線 x)は dy
    !   対角エッジ: 2·dx·dy/dr(dx=dy なら √2·dx)
    dr = sqrt(g%dx**2 + g%dy**2)
    tx_mod%w8lt(1:4) = [ 2 * g%dx * g%dy / dr, g%dx, 2 * g%dx * g%dy / dr, g%dy ]
    return
  end if
  if (f_advection_tvd > 0) then
    allocate(tx_mod%taxy(1:4,1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
  else
    allocate(tx_mod%taxy(1:2,1:g%nx,dcp%jsh:dcp%jeh), source = 0.0)
  end if
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

  if (f_advection_scheme >= 2) then
    call adv_prepare_mc(p, g, s, sx, tx_mod)
  else
    call adv_prepare_v1(p, g, s, sx, tx_mod)
    !call adv_prepare_v2(p, g, s, sx, tx_mod)
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

  if (f_advection_scheme >= 2) then
    ta = tx_mod%tae(k,ie,je)
  else
    ta = adv_edge_v1(s, sx, tx_mod, i, j, k, in, jn, ie, je)
    !ta = adv_edge_v2(s, sx, tx_mod, i, j, k, in, jn, ie, je)
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
!   - 側方面(±t): Q = q_t·w8dr、q_t は面中心のセル流量の t 方向投影
!     (対角エッジは面中心のセル 1 つ、軸エッジは角を囲む 4 セル平均)。
!     ū は 1 次風上(u_e か、平行な隣接エッジの流速)。
!   - h̄_e = (h_c + h_n)/2(下限 dd/2)。lm は v1 と同じ流儀で乗じる
!     (輸送項は dtl = dt/lme の減衰を相殺する。§20)。
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
  real :: thx, thy
  real :: ta

  !$omp parallel do schedule(dynamic) &
  !$omp private(i, j, k, in, jn, ie, je, hc, hn, hb, lme, ue, um, umm, up, upp, utp, utm, &
  !$omp         qc, qn, qtp, qtm, ubc, ubn, ubtp, ubtm, thx, thy, ta)
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
        if (skip8(k)) cycle
        hc = s%h(i,j)
        hn = s%h(in,jn)
        if (hc < p%dd .and. hn < p%dd) cycle
        hb = (hc + hn) / 2

        ! 線 k 上のエッジ流速(基準セルから k 方向。確保範囲外は 0)
        ue  = sx%uv(k,ie,je)
        um  = uvk(i - din(k), j - djn(k), k)
        umm = uvk(i - 2 * din(k), j - 2 * djn(k), k)
        up  = uvk(in, jn, k)
        upp = uvk(in + din(k), jn + djn(k), k)

        ! 流向面(c, n)を通る単位幅流量(k 方向投影。c→n が正)
        qc = s%m(i,j) * n8x(k) + s%n(i,j) * n8y(k)
        qn = s%m(in,jn) * n8x(k) + s%n(in,jn) * n8y(k)

        ! 流向面の風上化流速(面 c: 流入なら u_m 側、流出なら u_e 側)
        if (qc >= 0) then
          ubc = face_value(um, ue, umm)
        else
          ubc = face_value(ue, um, up)
        end if
        if (qn >= 0) then
          ubn = face_value(ue, up, um)
        else
          ubn = face_value(up, ue, upp)
        end if
        ta = -(qn * (ubn - ue) - qc * (ubc - ue)) / w8dr(k)

        ! 側方面(±t。t = (-n8y, n8x))。流出が正
        thx = -n8y(k)
        thy = n8x(k)
        utp = uvk(i + dti(k), j + dtj(k), k)
        utm = uvk(i - dti(k), j - dtj(k), k)
        if (k == 1 .or. k == 3) then
          qtp =  qproj(i + dfpi(k), j + dfpj(k), thx, thy)
          qtm = -qproj(i + dfmi(k), j + dfmj(k), thx, thy)
        else
          qtp =  (qproj(i, j, thx, thy) + qproj(in, jn, thx, thy) &
                + qproj(i + dti(k), j + dtj(k), thx, thy) &
                + qproj(in + dti(k), jn + dtj(k), thx, thy)) / 4
          qtm = -(qproj(i, j, thx, thy) + qproj(in, jn, thx, thy) &
                + qproj(i - dti(k), j - dtj(k), thx, thy) &
                + qproj(in - dti(k), jn - dtj(k), thx, thy)) / 4
        end if
        if (qtp >= 0) then
          ubtp = ue
        else
          ubtp = utp
        end if
        if (qtm >= 0) then
          ubtm = ue
        else
          ubtm = utm
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

  ! セル流量 (m, n) の単位ベクトル (tx_, ty_) 方向投影(確保範囲外は 0)
  pure function qproj(ci, cj, tx_, ty_) result(q)
    integer, intent(in) :: ci, cj
    real, intent(in) :: tx_, ty_
    real :: q
    if (ci < 1 .or. ci > ubound(s%m, 1) .or. cj < dcp%jsh .or. cj > dcp%jeh) then
      q = 0.0
    else
      q = s%m(ci,cj) * tx_ + s%n(ci,cj) * ty_
    end if
  end function

  ! 面値の再構成: 風上側 up、風下側 dn、さらに風上側 upup
  !   スキーム2: 1 次風上(up)
  !   スキーム3: MUSCL  up + ψ(r)/2·(dn - up)、r = (up - upup)/(dn - up)、
  !              ψ = van Leer (r+|r|)/(1+|r|)(r=1 で中心差分、極値で 0)
  pure function face_value(up, dn, upup) result(f)
    real, intent(in) :: up, dn, upup
    real :: f
    real :: d, r, psi
    if (f_advection_scheme == 2) then
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

  if (f_advection_term == 0) return

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
      forall(k=1:8) wwx(k) = w8x(k) * ww(k)
      forall(k=1:8) wwy(k) = w8y(k) * ww(k)
      call get_diff_v1(tx%ulm, tx%vlm, s%h, p%dd, wwx, wwy, g%x, i, j, dux, duy, dvx, dvy)
      tx%taxy(1,i,j) = -(s%u(i,j) * dux + s%v(i,j) * duy)
      tx%taxy(2,i,j) = -(s%u(i,j) * dvx + s%v(i,j) * dvy)
      if (f_advection_tvd > 0) then
        ! 中心差分による移流項の計算
        call get_diff_v1(tx%ulm, tx%vlm, s%h, p%dd, w8x, w8y, g%x, i, j, dux, duy, dvx, dvy)
        tx%taxy(3,i,j) = -(s%u(i,j) * dux + s%v(i,j) * duy)
        tx%taxy(4,i,j) = -(s%u(i,j) * dvx + s%v(i,j) * dvy)
      end if
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
  if (p_adv_upwind_index > 0 .and. vv > 0) then
    do k = 1, 8
      wk = -(u * n8x(k) + v * n8y(k)) / vv                    ! -1~1
      wk = max(1 - (1 - wk) * p_adv_upwind_index / 2, 0.0)    ! 0～1
      ww_upw(k) = wk
    end do
  else
    ww_upw(:) = 1
  end if
end function

!----------------------------------------------------------------------
! 移流項を計算する
!----------------------------------------------------------------------
function adv_edge_v1(s, sx, tx, i, j, k, in, jn, ie, je) result(ta)
  type(t_state), intent(in) :: s
  type(t_enc_status), intent(in) :: sx
  type(t_enc_adv), intent(in) :: tx
  integer, intent(in) :: i, j, k, in, jn, ie, je
  real :: ta

  real :: taxe, taye
  real :: taxe2, taye2, tae2
  integer :: inn, jnn, ino, jno
  real :: unn, vnn, uno, vno
  real :: duvc, duvr, duvl, duv0
  real :: rr, phi
  real :: uve

  uve = sx%uv(k,ie,je)
  if (uve > 0.0) continue
  ! 風上差分による移流項
  taxe = (tx%taxy(1,i,j) + tx%taxy(1,in,jn)) / 2  ! 移流項(x方向, 符合は座標軸方向が正)
  taye = (tx%taxy(2,i,j) + tx%taxy(2,in,jn)) / 2  ! 移流項(y方向, 符合は座標軸方向が正)
  ta = taxe * n8x(k) + taye * n8y(k)             ! 移流項(符合は中心セルから近傍セルに向かい正)
  !ta = ta * 1.5
  ! TVD(風上差分と中心差分の混合。developer.md §68.3 段 1)
  !   旧実装は両側の比 rl, rr の minmod(どちらかが負なら 0)で φ を決め、
  !   中心差分側に ×1.5 を掛けていたため、ほぼ全域で φ→0(風上一色)かつ
  !   長波で反拡散になっていた(§68.2)。ここでは風上側 1 本の比 r と
  !   van Leer 限定器(1 で頭打ち)に改める。v1 の構造上、限定器は
  !   「2 つの微分推定の混合比」としてしか働かない(面値の再構成は
  !   段 2 の運動量保存形移流が担う)
  if (f_advection_tvd > 0) then
    ! 中心差分による移流項
    taxe2 = (tx%taxy(3,i,j) + tx%taxy(3,in,jn)) / 2
    taye2 = (tx%taxy(4,i,j) + tx%taxy(4,in,jn)) / 2
    tae2 = taxe2 * n8x(k) + taye2 * n8y(k)
    inn = in + din(k)  ! k近傍のさらに外側のセル
    jnn = jn + djn(k)  ! k近傍のさらに外側のセル
    ino = i + din(9-k) ! k近傍の反対側のセル
    jno = j + djn(9-k) ! k近傍の反対側のセル
    ! ±2ステンシルは u/v の確保範囲(1:nx, jsh:jeh)の外に出うる
    ! (格子枠に接したエッジ)。枠外は u=v=0 として扱う
    ! (領域外・無効セル x=0 の格納値と同じ扱いに揃える)
    if (inn >= 1 .and. inn <= dcp%nx_g .and. jnn >= dcp%jsh .and. jnn <= dcp%jeh) then
      unn = s%u(inn,jnn)
      vnn = s%v(inn,jnn)
    else
      unn = 0
      vnn = 0
    end if
    if (ino >= 1 .and. ino <= dcp%nx_g .and. jno >= dcp%jsh .and. jno <= dcp%jeh) then
      uno = s%u(ino,jno)
      vno = s%v(ino,jno)
    else
      uno = 0
      vno = 0
    end if
    ! 線 k 上の投影流速の差分(o→c, c→n, n→nn)
    duvr = (unn - s%u(in ,jn )) * n8x(k) + (vnn - s%v(in ,jn )) * n8y(k)
    duvc = (s%u(in ,jn ) - s%u(i  ,j  )) * n8x(k) + (s%v(in ,jn ) - s%v(i  ,j  )) * n8y(k)
    duvl = (s%u(i  ,j  ) - uno) * n8x(k) + (s%v(i  ,j  ) - vno) * n8y(k)
    duv0 = duvc + sign(1.E-5, duvc)
    ! 風上側 1 本の勾配比 r(uve>0: c が風上 → o→c の差分、uve<0: n が風上)
    if (uve > 0) then
      rr = duvl / duv0
    else if (uve < 0) then
      rr = duvr / duv0
    else
      rr = 0.0
    end if
    ! van Leer 限定器 φ(r) = (r+|r|)/(1+|r|) を 1 で頭打ち(1 = 中心差分)
    phi = min(1.0, (rr + abs(rr)) / (1 + abs(rr)))
    ! 風上差分と中心差分の混合
    ta = ta + phi * (tae2 - ta)
  end if
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
    dux = dux + du * r8x(k) * wwx
    dvx = dvx + dv * r8x(k) * wwx
    duy = duy + du * r8y(k) * wwy
    dvy = dvy + dv * r8y(k) * wwy
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


!======================================================================
!======================================================================
!----------------------------------------------------------------------
! 移流項の計算(局所型)
!----------------------------------------------------------------------
subroutine adv_prepare_v2(p, g, s, sx, tx)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(in) :: s
  type(t_enc_status), intent(in) :: sx
  type(t_enc_adv), intent(inout) :: tx

  integer :: i, j, k
  real :: ww(1:8), wwx(1:8), wwy(1:8)
  real :: uu(1:3,1:3), vv(1:3,1:3), uv(1:3,1:3)
  real :: hh(1:3,1:3)
  integer :: xx(0:4,0:4)
  real :: u(0:8), v(0:8)
  integer :: ii(1:8), jj(1:8)
        real :: dux, duy, dvx, dvy
        real :: duux, dvvy, duvx, duvy

  if (f_advection_term == 0) return

  !$omp parallel do schedule(dynamic) &
  !$omp private(i, j, k, ww, wwx, wwy, ii, jj, u, v, uu, vv, uv, hh, xx, dux, duy, dvx, dvy, duux, dvvy, duvx, duvy)
  ! 全域窓の端でのみ1行縮める(dcp%js+1 とはしないこと)。
  ! taxy はハロ行 js-1/je+1 でも再計算する(案A: u,v の交換で賄う)
  do j = max(dcp%js - 1, dcp%jw1 + 1), min(dcp%je + 1, dcp%jw2 - 1)
    do i = g%wx(1,j)+1, g%wx(2,j)-1
      if (g%x(i,j) <= 0) cycle
      if (g%sw(i,j) > 0) cycle
      if (s%h(i,j) < p%dd) cycle

      ! 風上差分による重みの計算
      ww(:) = get_ww_upw_v2(s%u(i,j), s%v(i,j), s%vv(i,j))
      forall(k=1:8) wwx(k) = w8x(k) * ww(k)
      forall(k=1:8) wwy(k) = w8y(k) * ww(k)

      ! 水深と領域フラグを切り出す
      hh(1:3,1:3) = s%h(i-1:i+1,j-1:j+1)
      xx(0:4,0:4) = g%x(i-2:i+2,j-2:j+2)

      ! セル中心の流速
      u(0) = s%u(i,j)
      v(0) = s%v(i,j)

      !if (.true.) then   ! 隣接セル  tada
      if (.false.) then  ! セル界面上
        ! 隣接セルの流速を使用
        do k = 1, 8
          u(k) = s%u(i+din(k),j+djn(k))
          v(k) = s%v(i+din(k),j+djn(k))
        end do
      else
        ! セル界面上(頂点)の流速を使用
        do k = 1, 8
          ii(k) = i + die(k)    ! セルi,jの界面上のベクトルのインデックス
          jj(k) = j + dje(k)    ! セルi,jの界面上のベクトルのインデックス
          select case(k)
            case (1, 3, 6, 8)
              ! 頂点の流速はU1とU3を軸方向に変換して平均化
              u(k) = (sx%uv(1, ii(k),jj(k)) / n8x(1) + sx%uv(3, ii(k),jj(k)) / n8x(3)) / 2
              v(k) = (sx%uv(1, ii(k),jj(k)) / n8y(1) + sx%uv(3, ii(k),jj(k)) / n8y(3)) / 2
            case default
              ! 2,4,5,7は後で計算するのでここでは何もしない
          end select
        end do
        ! セル界面上(辺の中点)の流速
        u(2) = (u(1) + u(3)) / 2               ! 辺の左右端から補間
        v(2) = -sx%uv(2, ii(2),jj(2))          ! yの正の方向に変換
        u(4) = -sx%uv(4, ii(4),jj(4))          ! xの正の方向に変換
        v(4) = (v(1) + v(6)) / 2               ! 辺の上限端から補間
        u(5) = -sx%uv(4, ii(5),jj(5))          ! 右のセルのu5をxの正方向に変換
        v(5) = (v(3) + v(8)) / 2               ! 辺の上下端から補間
        u(7) = (u(6) + u(8)) / 2               ! 辺の左右端から補間
        v(7) = -sx%uv(2, ii(7),jj(7))          ! 上のセルのv2をyの正方向に変換
      end if

      !if (.true.) then   ! 非保存形 tada
      if (.false.) then  ! 保存形
        ! 非保存形
        ! uとvを並べてuuとvvの形に整形して代入
        uu = reshape([ u(1), u(2), u(3), u(4), u(0), u(5), u(6), u(7), u(8) ], shape(uu))
        vv = reshape([ v(1), v(2), v(3), v(4), v(0), v(5), v(6), v(7), v(8) ], shape(vv))
        ! 勾配を計算
        call get_diff_v2(uu, vv, hh, p%dd, wwx, wwy, xx, 2, 2, 3, 3, dux, duy, dvx, dvy)
        ! 移流項を計算
        tx%taxy(1,i,j) = -(s%u(i,j) * dux + s%v(i,j) * duy) * s%lm(i,j)
        tx%taxy(2,i,j) = -(s%u(i,j) * dvx + s%v(i,j) * dvy) * s%lm(i,j)
      else
        ! 保存形
        ! uとvを並べてuu,vv,uvの形に整形して代入
        uu = reshape([ u(1)**2, u(2)**2, u(3)**2, &
                       u(4)**2, u(0)**2, u(5)**2, &
                       u(6)**2, u(7)**2, u(8)**2 ], shape(uu))
        vv = reshape([ v(1)**2, v(2)**2, v(3)**2, &
                       v(4)**2, v(0)**2, v(5)**2, &
                       v(6)**2, v(7)**2, v(8)**2 ], shape(vv))
        uv = reshape([ u(1)*v(1), u(2)*v(2), u(3)*v(3), &
                       u(4)*v(4), u(0)*v(0), u(5)*v(5), &
                       u(6)*v(6), u(7)*v(7), u(8)*v(8) ], shape(uv))
        ! 勾配を計算
        call get_diff2_v2(uu, vv, uv, hh, p%dd, wwx, wwy, xx, duux, dvvy, duvx, duvy)
        ! 移流項を計算
        tx%taxy(1,i,j) = -(duux + duvy) * s%lm(i,j)
        tx%taxy(2,i,j) = -(duvx + dvvy) * s%lm(i,j)
      end if

    end do
  end do
  !$omp end parallel do

end subroutine


!----------------------------------------------------------------------
! 移流項を計算する
!----------------------------------------------------------------------
function adv_edge_v2(s, sx, tx, i, j, k, in, jn, ie, je) result(ta)
  type(t_state), intent(in) :: s
  type(t_enc_status), intent(in) :: sx
  type(t_enc_adv), intent(in) :: tx
  integer, intent(in) :: i, j, k, in, jn, ie, je
  real :: ta
  real :: taxe, taye
  real :: uve
  if (s%initialized) continue  ! 引数未使用の警告を抑制
  if (f_advection_term <= 0) then
    ta = 0
    return
  end if
  if (.true.) then    ! 両側セル平均  tada
  !if (.false.) then   ! 風上セル
    ! 境界の両側セルの平均移流項を用いる
    taxe = (tx%taxy(1,i,j) + tx%taxy(1,in,jn)) / 2
    taye = (tx%taxy(2,i,j) + tx%taxy(2,in,jn)) / 2
  else
    ! 境界から見て風上側のセルの移流項を用いる
    uve = sx%uv(k,ie,je)
    if (uve > 0) then
      taxe = tx%taxy(1,i,j)
      taye = tx%taxy(2,i,j)
    else if (uve < 0) then
      taxe = tx%taxy(1,in,jn)
      taye = tx%taxy(2,in,jn)
    else
      taxe = 0
      taye = 0
    endif
  end if
  ta = taxe * n8x(k) + taye * n8y(k)             ! 移流項(符合は中心セルから近傍セルに向かい正)
  !ta = ta * 1.5
end function


!----------------------------------------------------------------------
! 風上差分用のウェイトを計算
!----------------------------------------------------------------------
function get_ww_upw_v2(u, v, vv) result(ww_upw)
  real, intent(in) :: u, v
  real, intent(in) :: vv
  real :: ww_upw(1:8)
  real :: wk
  integer :: k
  if (p_adv_upwind_index > 0 .and. vv > 0) then
    do k = 1, 8
      wk = -(u * n8x(k) + v * n8y(k)) / vv                    ! -1~1
      wk = max(1 - (1 - wk) * p_adv_upwind_index / 2, 0.0)    ! 0～1
      ww_upw(k) = wk
    end do
  else
    ww_upw(:) = 1
  end if
end function


!----------------------------------------------------------------------
! 変数uu, vv, uvの微分(保存形)
!----------------------------------------------------------------------
subroutine get_diff2_v2(uu, vv, uv, h, dd, wx, wy, x, duux, dvvy, duvx, duvy)
  real, intent(in) :: uu(1:3,1:3)
  real, intent(in) :: vv(1:3,1:3)
  real, intent(in) :: uv(1:3,1:3)
  real, intent(in) :: h(1:3,1:3)
  real, intent(in) :: dd
  real, intent(in) :: wx(1:8), wy(1:8)
  integer, intent(in) :: x(0:4,0:4)
  real, intent(out) :: duux, dvvy
  real, intent(out) :: duvx, duvy

  real :: duu, dvv, duv
  real :: swx, swy, wwx, wwy
  integer :: in, jn, k

  duux = 0
  dvvy = 0
  duvx = 0
  duvy = 0
  swx = 0
  swy = 0

  do k = 1, 8
    in = 2 + din(k)
    jn = 2 + djn(k)
    if (h(in,jn) < dd) cycle
    wwx = x(in,jn) * wx(k)
    wwy = x(in,jn) * wy(k)
    duu = (uu(in,jn) - uu(2,2))
    dvv = (vv(in,jn) - vv(2,2))
    duv = (uv(in,jn) - uv(2,2))
    duux = duux + duu * r8x(k) * wwx
    dvvy = dvvy + dvv * r8y(k) * wwy
    duvx = duvx + duv * r8x(k) * wwx
    duvy = duvy + duv * r8y(k) * wwy
    swx = swx + wwx
    swy = swy + wwy
  end do

  if (swx > 0) then
    duux = duux / swx
    duvx = duvx / swx
  end if
  if (swy > 0) then
    dvvy = dvvy / swy
    duvy = duvy / swy
  end if

end subroutine


!----------------------------------------------------------------------
! 変数u, vの微分(非保存形)
!----------------------------------------------------------------------
subroutine get_diff_v2(u, v, h, dd, wx, wy, x, i, j, nx, ny, dux, duy, dvx, dvy)
  real, intent(in) :: u(1:nx,1:ny)
  real, intent(in) :: v(1:nx,1:ny)
  real, intent(in) :: h(1:nx,1:ny)
  real, intent(in) :: dd
  real, intent(in) :: wx(1:8), wy(1:8)
  integer, intent(in) :: x(0:nx+1,0:ny+1)
  integer, intent(in) :: i, j, nx, ny
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
    dux = dux + du * r8x(k) * wwx
    dvx = dvx + dv * r8x(k) * wwx
    duy = duy + du * r8y(k) * wwy
    dvy = dvy + dv * r8y(k) * wwy
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
