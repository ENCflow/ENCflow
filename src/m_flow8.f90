module m_flow8
  ! ==============================================================
  ! 8 近傍の非線形拡散型の流れ(溶岩流 m_lavaflow・氷河の SIA m_glacier)の
  ! 共通部品(lv_diagratio・gl_diagratio = d > 0。developer.md §96)
  !
  !   - flow8_weights: 9 点の通過幅の伝導度(軸・斜め)と、振り替えの伝導度の増分
  !   - flow8_open:    エッジの振り替え量(塞がり率の和の 1/2。案 A)
  !   - flow8_diag_gs2: 斜めのエッジの流れの面の勾配の大きさの 2 乗(角点の勾配)
  !
  ! 案 A(landslide_tsunami_plan.md §11.1): 水の f_opening_dynamic = 3(m_swflow_enc の
  ! build_fwd・sblk。developer.md §68.14・§68.41)と同じ規則を、流れの面 s = z + h(h = 溶岩厚・
  ! 氷厚)に当てはめる。斜め先のセルの地盤が始点の流れの面より高いと、その斜めの配分は
  ! 流れられないので、同じ界面を横切る軸のエッジへ返す(軸のエッジ)。軸の両側の先が
  ! 塞がれた斜めの谷では、軸の配分を斜めへ返す(斜めのエッジ)。振り替えないと、軸の向きの
  ! 1 セル幅の谷の通水能が 1 − d 倍に落ち、斜めの 1 セル幅の谷の通水能は d/2 の配分だけになる。
  !
  ! 引数の z・h は帯確保の配列(dcp%ish:dcp%ieh, dcp%jsh:dcp%jeh)。読むのはエッジの両端と
  ! その横 ±1 のセル(書き手の行 js..je+1 で行 js−1..je+2・列は行窓 ±1)= ハロ幅 2 の内側。
  ! x は全域+1 周・sw は全域で確保されているので、x > 0 を確かめてから sw を読む。
  ! どれも純関数(状態を持たない)。8近傍の規約は m_lavaflow・m_glacier と同一(書き手 c = (i,j) の
  ! 所有エッジ k の近傍 n: k = 1: (i−1, j−1) = 北西、2: (i, j−1) = 北、3: (i+1, j−1) = 北東、
  ! 4: (i−1, j) = 西。j は北端が 1 で南向きに増える)
  ! ==============================================================
  use m_geoinfo, only : t_geoinfo
  use m_parallel, only : dcp
  implicit none
  private

  public :: flow8_weights
  public :: flow8_open
  public :: flow8_diag_gs2

  integer, parameter :: din(1:4) = [ -1,  0,  1, -1]
  integer, parameter :: djn(1:4) = [ -1, -1, -1,  0]

contains

!----------------------------------------------------------------------
! 9 点の通過幅の伝導度(d > 0)
!   通過幅の配分は m_swflow_enc の init_weights・calc_creep の 9 点(§93)と同じ規則
!   (短い辺に d、長い辺は (Δmin/Δmax)² 倍。軸 lp、斜め ld の面長に対する割合)。
!   cw = 通過幅 / 中心間距離(k = 1・3: 斜め、2: 法線 y、4: 法線 x)。cwd は振り替えの
!   伝導度の増分: 軸は塞がれた斜め 1 本分の ld·面長(水の fwd の (lp + nb·ld)/lp と同じ。
!   nb 倍して足す)、斜めは斜め先 1 つ分の (自然幅 − 斜めの通過幅)/2(水の fwd の s1d と
!   同じ。flow8_open の値を掛けて足す。両側の斜め先が両端から全て塞がれると自然幅
!   ΔxΔy/√(Δx² + Δy²))。内部では任意の d・Δx ≠ Δy で f_xx・f_yy の係数が 1 の 9 点
!----------------------------------------------------------------------
pure subroutine flow8_weights(g, d, cw, cwd, dist)
  type(t_geoinfo), intent(in) :: g
  real, intent(in) :: d
  real, intent(out) :: cw(1:4), cwd(1:4), dist(1:4)
  real :: lpx, lpy, ldx, ldy, dr, wd

  dr = sqrt(g%dx**2 + g%dy**2)
  if (g%dy > g%dx) then
    lpy = 1 - (g%dx / g%dy)**2 * d
    ldy = d / 2 * (g%dx / g%dy)**2
    lpx = 1 - d
    ldx = d / 2
  else
    lpy = 1 - d
    ldy = d / 2
    lpx = 1 - (g%dy / g%dx)**2 * d
    ldx = d / 2 * (g%dy / g%dx)**2
  end if
  wd = sqrt((ldy * g%dy)**2 + (ldx * g%dx)**2)        ! 斜めの通過幅 (m)
  cw(1) = wd / dr
  cw(2) = lpx * g%dx / g%dy                           ! 通過幅 lpx·dx、距離 dy
  cw(3) = wd / dr
  cw(4) = lpy * g%dy / g%dx                           ! 通過幅 lpy·dy、距離 dx
  cwd(1) = max(g%dx * g%dy / dr - wd, 0.0) / 2 / dr
  cwd(2) = ldx * g%dx / g%dy
  cwd(3) = cwd(1)
  cwd(4) = ldy * g%dy / g%dx
  dist(1) = dr
  dist(2) = g%dy
  dist(3) = dr
  dist(4) = g%dx
end subroutine


!----------------------------------------------------------------------
! 書き手 c = (i,j) の所有エッジ k(c → n = c + (din(k), djn(k)))の振り替え量
!   = 塞がり率(blk)の和の 1/2。伝導度は cw(k) + (この値)·cwd(k)。
!   軸のエッジ(k = 2・4): 界面を横切る斜め 4 本 = c から n の左右のセルへ(相手の端 o = n、
!     κ = n の横断の 2 階差分)と、n から c の左右のセルへ(o = c、κ = c の横断の 2 階差分)。
!     値は塞がれた本数 nb(水の build_fwd の成分 2・4 と同じ)。
!   斜めのエッジ(k = 1・3): 角を共有する 2 セル A = (in, j)・B = (i, jn) へ、c と n の両端から
!     (κ = z_A + z_B − z_c − z_n。水の build_fwd の成分 1・3 と同じ)。
!   c・n の役割を入れ替えても同じ値(和の項が入れ替わるだけ)
!----------------------------------------------------------------------
pure function flow8_open(g, z, h, k, i, j) result(sh)
  type(t_geoinfo), intent(in) :: g
  real, intent(in) :: z(dcp%ish:, dcp%jsh:), h(dcp%ish:, dcp%jsh:)
  integer, intent(in) :: k, i, j
  real :: sh
  integer :: in, jn
  real :: ka, kb

  in = i + din(k)
  jn = j + djn(k)
  select case (k)
  case (2)
    ka = kap_lat(g, z, in, jn, 1, 0)
    kb = kap_lat(g, z, i, j, 1, 0)
    sh = blk(g, z, h, i, j, in-1, jn, in, jn, ka) + blk(g, z, h, i, j, in+1, jn, in, jn, ka) &
       + blk(g, z, h, in, jn, i-1, j, i, j, kb) + blk(g, z, h, in, jn, i+1, j, i, j, kb)
  case (4)
    ka = kap_lat(g, z, in, jn, 0, 1)
    kb = kap_lat(g, z, i, j, 0, 1)
    sh = blk(g, z, h, i, j, in, jn-1, in, jn, ka) + blk(g, z, h, i, j, in, jn+1, in, jn, ka) &
       + blk(g, z, h, in, jn, i, j-1, i, j, kb) + blk(g, z, h, in, jn, i, j+1, i, j, kb)
  case default
    ka = kap_diag(g, z, in, j, i, jn, i, j, in, jn)
    sh = blk(g, z, h, i, j, in, j, in, jn, ka) + blk(g, z, h, i, j, i, jn, in, jn, ka) &
       + blk(g, z, h, in, jn, in, j, i, j, ka) + blk(g, z, h, in, jn, i, jn, i, j, ka)
  end select
  sh = 0.5 * sh
end function


!----------------------------------------------------------------------
! 斜めのエッジ(書き手 c = (i,j) の k = 1・3)の流れの面の勾配の大きさの 2 乗 |∇s|²
!   c と n = c + (din(k), djn(k)) が共有する角点の勾配を、対角の差 Dn = s_n − s_c と、角を
!   共有する 2 セル A = (in, j)・B = (i, jn) の差 Dab = s_A − s_B から解く(Δx ≠ Δy でも
!   x・y 成分に直してから 2 乗和を取る):
!     k = 1(n − c = (−Δx, −Δy)、A − B = (−Δx, +Δy)): s_x = −(Dn + Dab)/(2Δx)、s_y = (Dab − Dn)/(2Δy)
!     k = 3(n − c = (+Δx, −Δy)、A − B = (+Δx, +Δy)): s_x = (Dn + Dab)/(2Δx)、s_y = (Dab − Dn)/(2Δy)
!   A・B は流れのある有効セル(flow_cell)だけを使う(軸のエッジの接線勾配 edge_tslope と同じ
!   考え。流れのないセルの地盤高は流れの面ではない): 片方だけなら角点の値 (s_c + s_n)/2 との
!   片側差分の 2 倍、両方なければ Dab = 0(角点を横切る向きの勾配なし)。Dn ≠ 0 なら結果は正
!----------------------------------------------------------------------
pure function flow8_diag_gs2(g, z, h, k, i, j) result(gs2)
  type(t_geoinfo), intent(in) :: g
  real, intent(in) :: z(dcp%ish:, dcp%jsh:), h(dcp%ish:, dcp%jsh:)
  integer, intent(in) :: k, i, j
  real :: gs2
  integer :: in, jn
  real :: sc, sn_, dn, dab, sx, sy
  logical :: oka, okb

  in = i + din(k)
  jn = j + djn(k)
  sc = z(i,j) + h(i,j)
  sn_ = z(in,jn) + h(in,jn)
  dn = sn_ - sc
  oka = flow_cell(g, h, in, j)
  okb = flow_cell(g, h, i, jn)
  if (oka .and. okb) then
    dab = (z(in,j) + h(in,j)) - (z(i,jn) + h(i,jn))
  else if (oka) then
    dab = 2.0 * (z(in,j) + h(in,j)) - (sc + sn_)
  else if (okb) then
    dab = (sc + sn_) - 2.0 * (z(i,jn) + h(i,jn))
  else
    dab = 0.0
  end if
  if (k == 1) then
    sx = -(dn + dab) / (2.0 * g%dx)
  else
    sx = (dn + dab) / (2.0 * g%dx)
  end if
  sy = (dab - dn) / (2.0 * g%dy)
  gs2 = sx * sx + sy * sy
end function


!----------------------------------------------------------------------
! 始点 c = (ic,jc) から斜め先 d = (id,jd) への塞がり率(0〜1。水の sblk と同じ規則)
!   領域外・無効・海のセルは壁(1。溶岩・氷は海へ流れない)。それ以外は
!   dz = min(z_d − z_c, z_d − z_o, κ)(o はエッジのもう一方の端、κ は局所の平面からの
!   盛り上がり。一様な斜面の上流側の地盤を壁と数えない)で、dz <= 0 なら 0、始点の流れの
!   厚さ h_c が dz 以下なら 1、それより厚ければ dz/h_c(流れの面が斜め先の地盤を越えた分は
!   斜めが運ぶので、地盤より下の流れの割合だけ塞がる)
!----------------------------------------------------------------------
pure function blk(g, z, h, ic, jc, id, jd, io, jo, kap) result(res)
  type(t_geoinfo), intent(in) :: g
  real, intent(in) :: z(dcp%ish:, dcp%jsh:), h(dcp%ish:, dcp%jsh:)
  integer, intent(in) :: ic, jc, id, jd, io, jo
  real, intent(in) :: kap
  real :: res
  real :: dz, hc

  res = 1.0
  if (g%x(id,jd) <= 0) return
  if (g%sw(id,jd) > 0) return
  res = 0.0
  dz = min(z(id,jd) - z(ic,jc), z(id,jd) - z(io,jo), kap)
  if (dz <= 0.0) return
  hc = h(ic,jc)
  if (hc <= dz) then
    res = 1.0
  else
    res = dz / hc
  end if
end function


!----------------------------------------------------------------------
! 振り替えの頭打ち κ(m_swflow_enc の kap_lat・kap_diag と同じ形)。kap_lat: セル (i,j) の
! (di,dj) 方向の地盤の 2 階差分 z(i+di,j+dj) + z(i−di,j−dj) − 2 z(i,j)。kap_diag: 斜めの
! エッジ (ia,ja)-(ib,jb) と角を共有する 2 セル (i1,j1)・(i2,j2) の z1 + z2 − za − zb。
! 使うセルが領域外・無効・海なら huge(頭打ちなし)
!----------------------------------------------------------------------
pure function kap_lat(g, z, i, j, di, dj) result(res)
  type(t_geoinfo), intent(in) :: g
  real, intent(in) :: z(dcp%ish:, dcp%jsh:)
  integer, intent(in) :: i, j, di, dj
  real :: res

  res = huge(1.0)
  if (.not. (kap_cell(g, i+di, j+dj) .and. kap_cell(g, i-di, j-dj))) return
  res = z(i+di,j+dj) + z(i-di,j-dj) - 2 * z(i,j)
end function

pure function kap_diag(g, z, i1, j1, i2, j2, ia, ja, ib, jb) result(res)
  type(t_geoinfo), intent(in) :: g
  real, intent(in) :: z(dcp%ish:, dcp%jsh:)
  integer, intent(in) :: i1, j1, i2, j2, ia, ja, ib, jb
  real :: res

  res = huge(1.0)
  if (.not. (kap_cell(g, i1, j1) .and. kap_cell(g, i2, j2))) return
  res = z(i1,j1) + z(i2,j2) - z(ia,ja) - z(ib,jb)
end function

! κ に使えるセルか(領域内の有効な陸セル。x の読みは範囲の検査の内側)
pure logical function kap_cell(g, i, j)
  type(t_geoinfo), intent(in) :: g
  integer, intent(in) :: i, j

  kap_cell = .false.
  if (i < 1 .or. i > g%nx .or. j < 1 .or. j > g%ny) return
  if (g%x(i,j) <= 0) return
  kap_cell = (g%sw(i,j) <= 0)
end function

! 流れのある有効セルか(領域内・海でない・h > 0。m_lavaflow の lava_cell・m_glacier の
! ice_cell と同じ条件)。x を先に見る
pure logical function flow_cell(g, h, i, j)
  type(t_geoinfo), intent(in) :: g
  real, intent(in) :: h(dcp%ish:, dcp%jsh:)
  integer, intent(in) :: i, j

  flow_cell = .false.
  if (g%x(i,j) <= 0) return
  if (g%sw(i,j) > 0) return
  if (h(i,j) <= 0.0) return
  flow_cell = .true.
end function

end module
