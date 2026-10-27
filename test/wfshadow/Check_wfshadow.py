#!/usr/bin/env python3
"""wfshadow: 沿岸の波浪場(fn_wavefield。developer.md §88)の 2 次元の検定

Python 標準ライブラリのみ。使い方:
  python3 Check_wfshadow.py base    result           # 方向分散 20° の不規則波
  python3 Check_wfshadow.py aligned result_aligned   # 格子の軸に揃った単一方向の波

地形は make_z.py と同じ(水深 10 m 一様、行 60・列 1..50 の防波堤、
|i − 75| + |j − 30| = 8 の菱形の壁)。添字は 1 始まり、j は南向き。

参照解(本スクリプトで独立に実装):
  離散の定常方程式 c_g (q_a + q_b) E_ij = Σ_{l = a, b} q_l c_g E_送り手(l) を、送り手が
  先に決まる順(伝播の上流から)の掃引で直接解く(反復なし)。一様水深なので c_g は
  打ち消し、屈折もない(砕波は H_rms/h = 0.07 で無視できる)。規則は m_wavefield と同じ:
    - ビン m の向き θ_m = (m − 1)Δθ を、軸(率 |p_x| − |p_y| など)と対角(率 min)の
      2 本の格子方向へ非負に分解する(p = 向き/格子幅)
    - 格子の外の仮想の送り手: 内側に寄せたセルが非波浪なら 0、入射の辺は沖の波の
      ビン別エネルギー、側方 Neumann の辺は寄せたセルの値、吸収の辺は 0。角(x・y とも
      外)は 入射 > Neumann > 吸収 の優先
    - 対角のリンクは、角を共有する 2 セルがともに格子内の非波浪セルなら閉じる
  沖の波のビン別エネルギーは cos^s 分布(s は方向分散 σθ から Kuik ら 1988 の定義で
  逆算)をビンで離散的に正規化したもの。
"""
import math
import struct
import sys

NX = NY = 100
DX = DY = 10.0
G = 9.8
RHO = 1025.0
NTH = 40
LDI = [1, 1, 0, -1, -1, -1, 0, 1]      # 格子方向 E, NE, N, NW, W, SW, S, SE の (di, dj)
LDJ = [0, -1, -1, -1, 0, 1, 1, 1]
BCSIDE = (2, 2, 0, 1)                    # W, E, N, S

failed = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        failed.append(msg)


def land(i, j):
    if j == 60 and i <= 50:
        return True
    return abs(i - 75) + abs(j - 30) == 8


def read_bil(path):
    with open(path, "rb") as f:
        data = f.read()
    v = struct.unpack("<%df" % (NX * NY), data)
    return [list(v[j * NX:(j + 1) * NX]) for j in range(NY)]


def cos_power(sig):
    """方向分散 σθ (rad) → cos^s の指数 s(Kuik ら 1988: σθ² = 2(1 − m1))"""
    target = 1.0 - 0.5 * sig * sig

    def m1(s):
        return math.exp(2 * math.lgamma(0.5 * (s + 2)) - math.lgamma(0.5 * (s + 1)) - math.lgamma(0.5 * (s + 3)))

    lo, hi = 0.0, 1.0e5
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if m1(mid) < target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def incident(hm0, dir_deg, spread_deg):
    dth = 2.0 * math.pi / NTH
    e0 = RHO * G * hm0 * hm0 / 16.0
    eb = [0.0] * NTH
    if spread_deg <= 0.0:
        x = (dir_deg % 360.0) * math.pi / 180.0 / dth
        m1 = int(x)
        fr = x - m1
        eb[m1 % NTH] += (1.0 - fr) * e0 / dth
        eb[(m1 + 1) % NTH] += fr * e0 / dth
        return eb, dth
    s = cos_power(math.radians(spread_deg))
    for m in range(NTH):
        c = math.cos(m * dth - math.radians(dir_deg))
        eb[m] = c ** s if c > 1e-6 else 0.0
    tot = sum(eb) * dth
    return [e0 * v / tot for v in eb], dth


def decompose(th):
    c, s = math.cos(th), math.sin(th)
    if abs(c) < 1e-6:
        c = 0.0
    if abs(s) < 1e-6:
        s = 0.0
    qx, qy = c / DX, s / DY
    ax, ay = abs(qx), abs(qy)
    if abs(ax - ay) <= 1e-6 * max(ax, ay):
        ay = ax
    if ax >= ay:
        la, qa, qb = (0 if qx >= 0 else 4), ax - ay, ay
    else:
        la, qa, qb = (2 if qy >= 0 else 6), ay - ax, ax
    if qx >= 0:
        lb = 1 if qy >= 0 else 7
    else:
        lb = 3 if qy >= 0 else 5
    return la, lb, qa, qb, c, s


def sweep(eb):
    """離散の定常解 E[m][j][i](1 始まり、0 は未使用)を掃引で求める"""
    wet = [[False] * (NX + 2) for _ in range(NY + 2)]
    for j in range(1, NY + 1):
        for i in range(1, NX + 1):
            wet[j][i] = not land(i, j)

    def inside(i, j):
        return 1 <= i <= NX and 1 <= j <= NY

    def vtype(i, j):
        tx = ty = -1
        if i < 1:
            tx = BCSIDE[0]
        if i > NX:
            tx = BCSIDE[1]
        if j < 1:
            ty = BCSIDE[2]
        if j > NY:
            ty = BCSIDE[3]
        if tx < 0:
            return ty
        if ty < 0:
            return tx
        if tx == 1 or ty == 1:
            return 1
        if tx == 2 or ty == 2:
            return 2
        return 0

    def blocked(i_d, j_d, i_r, j_r):
        if not (inside(i_r, j_d) and inside(i_d, j_r)):
            return False
        return (not wet[j_d][i_r]) and (not wet[j_r][i_d])

    out = []
    for m in range(NTH):
        em = [[0.0] * (NX + 2) for _ in range(NY + 2)]
        out.append(em)
        if eb[m] == 0.0:
            continue          # 入射のないビン(Neumann の辺は内側の値を返すだけなので 0 のまま)
        la, lb, qa, qb, c, s = decompose(m * 2.0 * math.pi / NTH)
        jr = range(NY, 0, -1) if s > 0 else range(1, NY + 1)
        ir = range(1, NX + 1) if c >= 0 else range(NX, 0, -1)
        for j in jr:
            for i in ir:
                if not wet[j][i]:
                    continue
                num = 0.0
                selfq = 0.0
                for l, q in ((la, qa), (lb, qb)):
                    if q <= 0.0:
                        continue
                    i_d, j_d = i - LDI[l], j - LDJ[l]
                    if not inside(i_d, j_d):
                        ic, jc = min(max(i_d, 1), NX), min(max(j_d, 1), NY)
                        if not wet[jc][ic]:
                            continue
                        t = vtype(i_d, j_d)
                        if t == 1:
                            num += q * eb[m]
                        elif t == 2:
                            if (ic, jc) == (i, j):
                                selfq += q       # 自分自身へ寄せた Neumann(E = 他方の流入/q_他方)
                            else:
                                num += q * em[jc][ic]
                        continue
                    if not wet[j_d][i_d]:
                        continue
                    if l % 2 == 1 and blocked(i_d, j_d, i, j):
                        continue
                    num += q * em[j_d][i_d]
                den = qa + qb - selfq
                em[j][i] = num / den if den > 0.0 else 0.0
    return out


def height(e_cells, dth):
    """エネルギー密度のビン和 → H_m0"""
    return math.sqrt(2.0) * math.sqrt(8.0 * sum(e_cells) * dth / (RHO * G))


def diamond_interior():
    return [(i, j) for j in range(1, NY + 1) for i in range(1, NX + 1) if abs(i - 75) + abs(j - 30) < 8]


def case_base(res):
    print("== base (%s): random waves (spreading 20 deg) behind a breakwater and a diamond enclosure" % res)
    wh = read_bil(res + "/Wh0001.bil")
    eb, dth = incident(1.0, 90.0, 20.0)
    e = sweep(eb)
    worst = 0.0
    arg = None
    for j in range(1, NY + 1):
        for i in range(1, NX + 1):
            if land(i, j):
                continue
            ref = height([e[m][j][i] for m in range(NTH)], dth)
            d = abs(wh[j - 1][i - 1] - ref)
            if d > worst:
                worst, arg = d, (i, j, wh[j - 1][i - 1], ref)
    check(worst < 2e-4, "H equals the discrete steady solution solved by an independent upstream sweep:"
          " max |diff| = %.1e m (at i=%d, j=%d: %.5f vs %.5f; H0 = 1 m, wf_tol = 1e-6)" % ((worst,) + arg))
    inner = diamond_interior()
    check(all(wh[j - 1][i - 1] == 0.0 for (i, j) in inner),
          "no energy leaks through the corner-connected diagonal walls: H = 0 at all %d enclosed cells"
          % len(inner))
    check(all(wh[j - 1][i - 1] == 0.0 for j in range(1, NY + 1) for i in range(1, NX + 1) if land(i, j)),
          "land cells carry no waves")

    # 幾何光学解(各ビンが直進。陰はビンごとの見通し)との差 = 横断の数値拡散の大きさ(表示のみ)
    def visible(i, j, th):
        # セル中心から逆向きに直進し、陸のセルに当たらず南の辺(j > NY)へ抜ければ見える
        x, y = i - 0.5, j - 0.5
        dxs, dys = -math.cos(th), math.sin(th)       # j は南向き
        step = 0.05
        while True:
            x += dxs * step
            y += dys * step
            if y >= NY:
                return True
            # 東西の外は境界の列がそのまま続く(側方 Neumann = 岸沿いに一様な延長。
            # 西の辺に付いた防波堤は西へ続いているとみなす)
            ii = min(max(int(math.floor(x)) + 1, 1), NX)
            jj = int(math.floor(y)) + 1
            if jj >= 1 and land(ii, jj):
                return False

    worst_go = 0.0
    sq = 0.0
    n = 0
    for j in range(20, 59, 2):
        for i in range(10, 91, 4):
            hgo = math.sqrt(2.0) * math.sqrt(8.0 * sum(eb[m] * dth for m in range(NTH)
                                                       if eb[m] > 0.0 and visible(i, j, m * dth)) / (RHO * G))
            d = abs(wh[j - 1][i - 1] - hgo)
            worst_go = max(worst_go, d)
            sq += d * d
            n += 1
    print("     (info) behind the breakwater (rows 20-58): |H - H_geometric optics| max %.3f m, rms %.3f m"
          " -- crosswind numerical diffusion of the first-order two-link scheme at the shadow edges"
          % (worst_go, math.sqrt(sq / n)))


def case_aligned(res):
    print("== aligned (%s): unidirectional waves along the lattice axis (sharp shadows)" % res)
    wh = read_bil(res + "/Wh0001.bil")

    def shadow(i, j):
        if i <= 50 and j < 60:
            return True                               # 防波堤の陰
        d = abs(i - 75)
        if d <= 8 and j < 30 + (8 - d):
            return True                               # 菱形の南側の壁より北(内側を含む)
        return False

    lit = shad = 0
    worst_lit = 0.0
    nonzero = 0
    for j in range(1, NY + 1):
        for i in range(1, NX + 1):
            if land(i, j):
                continue
            v = wh[j - 1][i - 1]
            if shadow(i, j):
                shad += 1
                if v != 0.0:
                    nonzero += 1
            else:
                lit += 1
                worst_lit = max(worst_lit, abs(v - 1.0))
    check(worst_lit < 1e-6, "H = H0 = 1 m exactly outside the shadows (%d cells): max |H - 1| = %.1e"
          % (lit, worst_lit))
    check(nonzero == 0, "H = 0 exactly inside the geometric shadows (%d cells; %d nonzero)" % (shad, nonzero))


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    kind = sys.argv[1]
    if kind == "base":
        case_base(sys.argv[2])
    elif kind == "aligned":
        case_aligned(sys.argv[2])
    else:
        print(__doc__)
        sys.exit(2)
    if failed:
        print("FAIL: %d check(s) failed" % len(failed))
        sys.exit(1)
    print("PASS")


if __name__ == "__main__":
    main()
