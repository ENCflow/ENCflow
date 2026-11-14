#!/usr/bin/env python3
# test/brink の検定(標準ライブラリだけ)。池の出口の段落ちと、運動量保存形移流の屈曲直後の辺の風上値
# f_advection_bend(developer.md §110)
#   Check_brink.py
#   段落ちの構成(result_st0・st1・dg0・dg1)は、流量の 3 段(2,000・4,000・6,000 m3/s)それぞれの終わり
#   (40・80・120 分)のプローブの水深 h と測線の流量 Q を読む。単位幅流量 q = Q / Δx、
#   エネルギー水頭 E = z + h + (q/h)²/2g。理論の水面形は make_brink.py(1 次元の定常。広い矩形断面、
#   Manning。段落ちで限界水深、池は水平床の H2、棚は段差の分のエネルギーを得た射流の H3)。
#   構成 st0(直線の水路。f_advection_bend = 0):
#     (1) 測線の流量が湧き出しの流量に ±TOL_Q
#     (2) 池の水深が H2 の理論に、段落ちの 125 m 以上上流で ±TOL_POOL、75 m 上流で ±TOL_POOL75
#         (段落ちの直前のセルは低下背水の中で、比べない)
#     (3) 棚の 1〜4 番目のセルの水深が H3 の理論の APRON_LO〜APRON_HI 倍(段落ちで 1 m 前後の損失が出て、
#         損失のない理論より数 % 深い)
#     (4) 棚の 1〜4 番目のセルが射流(フルード数 > FR_ST)
#   構成 st1(直線。f_advection_bend = 1):
#     (5) st0 と同じ結果(全プローブの全時刻の水深の差が TOL_SAME 以下。直線の水路には、風上側の
#         供給元が壁で、かつ流入のある面がない)
#   構成 dg1(段落ちの直前で水路が斜めに 1 行ずれる。f_advection_bend = 1):
#     (6) 棚の 1〜4 番目のセルのエネルギー水頭が、池(段落ちの 475 m 上流)のエネルギー水頭を
#         TOL_E を超えて上回らない(流れは、流れ出す元の池より高いエネルギーを持てない)
#     (7) 池の水深が H2 の理論に、125 m 以上上流で ±TOL_POOL_DG
#     (8) 棚の 1〜4 番目のセルの水深が H3 の理論の 1〜APRON_HI_DG 倍(屈曲の損失は直線より大きいが、
#         限られる)で、射流(フルード数 > FR_DG)
#   構成 dg0(同じ水路。f_advection_bend = 0。既定の性質の記録):
#     (9) 棚の先頭のセルのエネルギー水頭が、池を E_EXCESS より大きく上回る(屈曲の直後の辺が上流からの
#         慣性を持たず、流速が水面勾配と摩擦の釣り合いまで上がる。(6) がこの違いを見分けていることの確認)
#   構成 sr0・sr1(東と北東のリンクが交互に並ぶ水路の等流。f_advection_bend = 0・1):
#     (10) 路の 40〜80 % の区間の平均水深が、0 と 1 で ±TOL_ST(斜めのリンクは通過幅が 0.707 倍で流速が
#          1.41 倍になるが、1 はこの幅の違いを加減速に数えない)
#     (11) 1 の同じ区間の水深の幅 (最大 − 最小) / 平均が RANGE_ST 以下
import sys, os, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_brink import (G, DX, NX, I_BRINK, N_APRON, Z_POOL, Q_LEVELS, T_RAMP, T_HOLD,
                        bed_brink, hcrit, pool_depth, apron_depth, path_stair)

TOL_Q = 0.015                     # (1) 流量の一致
TOL_POOL, TOL_POOL75 = 0.02, 0.04 # (2) 池の水深と理論の一致(125 m 以上上流、75 m 上流)
APRON_LO, APRON_HI = 0.95, 1.12   # (3) 棚の水深 / 理論
FR_ST = 1.2                       # (4) 棚のフルード数の下限(直線)
TOL_SAME = 1.0e-9                 # (5) 直線の 0 と 1 の水深の差 (m)
TOL_E = 0.2                       # (6) 棚のエネルギー水頭が池を上回ってよい幅 (m)
TOL_POOL_DG = 0.06                # (7) 斜めの構成の池の水深と理論の一致
APRON_HI_DG, FR_DG = 1.30, 1.1    # (8) 斜めの構成の棚の水深 / 理論の上限、フルード数の下限
E_EXCESS = 5.0                    # (9) 既定(0)の棚のエネルギー水頭の超過の下限 (m)
TOL_ST, RANGE_ST = 0.01, 0.04     # (10)(11) 等流の階段状の水路
X_POOL = [75.0, 125.0, 225.0, 475.0, 725.0]     # (2)(7) 池の水深を比べる位置(段落ちから上流へ。m)
X_EPOOL = 475.0                   # (6)(9) 池のエネルギー水頭を取る位置
N_CHK = 4                         # (3)(4)(6)(8) 棚の先頭から比べるセル数(最後のセルは流出区間の引き込みの中)

nfail = 0


def check(ok, msg):
    global nfail
    print("  %s %s" % ("ok  " if ok else "FAIL", msg))
    if not ok:
        nfail += 1


def series(fn):
    return [[float(v) for v in ln.split(",")] for ln in open(fn) if ln.strip() and not ln.startswith("#")]


def at(rows, tmin, col):
    return min(rows, key=lambda r: abs(r[1] - tmin))[col]


class Case:
    """段落ちの構成の結果(プローブ n は列 n + 2 の水路のセル。測線は棚の 2 番目のセルの列)"""
    def __init__(self, name):
        self.name = name
        self.pb = [series("result_%s/probes/probe%04d.csv" % (name, n)) for n in range(1, NX - 1)]
        self.fl = series("result_%s/fluxes/flux0001.csv" % name)

    def q(self, t):
        return at(self.fl, t, 2) / DX

    def h(self, i, t):
        return at(self.pb[i - 3], t, 3)

    def energy(self, i, t):
        h = self.h(i, t)
        return bed_brink(i) + h + (self.q(t) / h) ** 2 / (2 * G)

    def froude(self, i, t):
        h = self.h(i, t)
        return self.q(t) / h / (G * h) ** 0.5


def col_pool(x_up):
    """段落ちから x_up (m) 上流のセルの列(段落ちの直前のセルの中心が 25 m 上流)"""
    return I_BRINK - int(round((x_up - 0.5 * DX) / DX))


def levels():
    t = 0.0
    for q_in in Q_LEVELS:
        t += T_RAMP + T_HOLD
        yield t, q_in


def check_straight():
    print("=== st0: straight channel (f_advection_bend = 0) vs 1-D theory ===")
    c = Case("st0")
    for t, q_in in levels():
        q = c.q(t)
        check(abs(q * DX / q_in - 1.0) <= TOL_Q,
              "(1) t = %3.0f min: transect discharge %.1f m3/s = inflow %.0f (%+.2f %%)"
              % (t, q * DX, q_in, 100 * (q * DX / q_in - 1.0)))
        dev = [(x, c.h(col_pool(x), t) / pool_depth(q, x) - 1.0) for x in X_POOL]
        ok = all(abs(d) <= (TOL_POOL75 if x < 100.0 else TOL_POOL) for x, d in dev)
        check(ok, "(2) pond depth / H2 theory - 1 at x = %s m upstream: %s"
              % ("/".join("%.0f" % x for x, _ in dev), " ".join("%+.3f" % d for _, d in dev)))
        rat = [c.h(I_BRINK + k, t) / apron_depth(q, (k - 0.5) * DX) for k in range(1, N_CHK + 1)]
        check(all(APRON_LO <= r <= APRON_HI for r in rat),
              "(3) apron depth / H3 theory (cells 1-%d): %s (allowed %.2f-%.2f)"
              % (N_CHK, " ".join("%.3f" % r for r in rat), APRON_LO, APRON_HI))
        fr = [c.froude(I_BRINK + k, t) for k in range(1, N_CHK + 1)]
        check(min(fr) > FR_ST, "(4) apron is supercritical: Fr = %s (> %.1f)" % (" ".join("%.2f" % f for f in fr), FR_ST))
    print("=== st1: straight channel, f_advection_bend = 1 ===")
    c1 = Case("st1")
    dmax = max(abs(a[3] - b[3]) for pa, pb in zip(c.pb, c1.pb) for a, b in zip(pa, pb))
    check(dmax <= TOL_SAME, "(5) same depths as st0 (max difference %.1e m <= %.0e)" % (dmax, TOL_SAME))


def check_diag():
    print("=== dg1: diagonal link just before the brink, f_advection_bend = 1 ===")
    c = Case("dg1")
    ip = col_pool(X_EPOOL)
    for t, q_in in levels():
        q = c.q(t)
        ep = c.energy(ip, t)
        de = [c.energy(I_BRINK + k, t) - ep for k in range(1, N_CHK + 1)]
        check(max(de) <= TOL_E,
              "(6) t = %3.0f min (q = %.1f m2/s): apron energy head - pond energy head = %s m (<= %.1f)"
              % (t, q, " ".join("%+.2f" % d for d in de), TOL_E))
        dev = [(x, c.h(col_pool(x), t) / pool_depth(q, x) - 1.0) for x in X_POOL if x >= 100.0]
        check(all(abs(d) <= TOL_POOL_DG for _, d in dev),
              "(7) pond depth / H2 theory - 1 at x = %s m upstream: %s"
              % ("/".join("%.0f" % x for x, _ in dev), " ".join("%+.3f" % d for _, d in dev)))
        rat = [c.h(I_BRINK + k, t) / apron_depth(q, (k - 0.5) * DX) for k in range(1, N_CHK + 1)]
        fr = [c.froude(I_BRINK + k, t) for k in range(1, N_CHK + 1)]
        check(all(1.0 <= r <= APRON_HI_DG for r in rat) and min(fr) > FR_DG,
              "(8) apron depth / H3 theory: %s (allowed 1.00-%.2f), Fr = %s (> %.1f)"
              % (" ".join("%.3f" % r for r in rat), APRON_HI_DG, " ".join("%.2f" % f for f in fr), FR_DG))
    print("=== dg0: same channel, f_advection_bend = 0 (record of the default behaviour) ===")
    c0 = Case("dg0")
    for t, q_in in levels():
        de = c0.energy(I_BRINK + 1, t) - c0.energy(ip, t)
        check(de > E_EXCESS,
              "(9) t = %3.0f min (q = %.1f m2/s): apron energy head exceeds the pond's by %+.2f m (> %.1f; "
              "depth %.2f m, velocity %.1f m/s)"
              % (t, c0.q(t), de, E_EXCESS, c0.h(I_BRINK + 1, t), c0.q(t) / c0.h(I_BRINK + 1, t)))


def last_depth(rdir):
    fs = sorted(f for f in glob.glob(rdir + "/H[0-9][0-9][0-9][0-9].txt") if int(f[-8:-4]) < 9000)
    return [[float(v) for v in ln.split()] for ln in open(fs[-1])]


def check_stair():
    print("=== sr0, sr1: uniform flow in a channel of alternating east and north-east links ===")
    cells = path_stair()
    a, b = int(0.4 * len(cells)), int(0.8 * len(cells))
    stat = {}
    for name in ("sr0", "sr1"):
        hh = last_depth("result_" + name)
        seg = [hh[j - 1][i - 1] for i, j, _ in cells[a:b]]
        stat[name] = (sum(seg) / len(seg), min(seg), max(seg))
        print("  %s: mean depth %.4f m (min %.4f, max %.4f)" % ((name,) + stat[name]))
    r = stat["sr1"][0] / stat["sr0"][0] - 1.0
    check(abs(r) <= TOL_ST, "(10) mean depth with f_advection_bend = 1 / 0 - 1 = %+.4f (within %.2f)" % (r, TOL_ST))
    rng = (stat["sr1"][2] - stat["sr1"][1]) / stat["sr1"][0]
    check(rng <= RANGE_ST, "(11) depth range (max - min) / mean with 1 = %.4f (<= %.2f)" % (rng, RANGE_ST))


if __name__ == "__main__":
    check_straight()
    check_diag()
    check_stair()
    if nfail:
        print("=== Check_brink.py: FAIL (%d) ===" % nfail)
        sys.exit(1)
    print("=== Check_brink.py: PASS ===")
