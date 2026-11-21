#!/usr/bin/env python3
# test/brink の検定(標準ライブラリだけ)。池の出口の段落ちと、運動量保存形移流の屈曲直後の辺の風上値
# f_advection_bend(developer.md §110)
#   Check_brink.py [old|new](古い値の組み合わせの組・4 つの値の組み合わせの組。下の「組」)
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
#   構成 dg0(同じ水路。f_advection_bend = 0。0 の性質の記録):
#     (9) 棚の先頭のセルのエネルギー水頭が、池を E_EXCESS より大きく上回る(屈曲の直後の辺が上流からの
#         慣性を持たず、流速が水面勾配と摩擦の釣り合いまで上がる。(6) がこの違いを見分けていることの確認)
#   構成 sr0・sr1(東と北東のリンクが交互に並ぶ水路の等流。f_advection_bend = 0・1):
#     (10) 路の 40〜80 % の区間の平均水深が、0 と 1 で ±TOL_ST(斜めのリンクは通過幅が 0.707 倍で流速が
#          1.41 倍になるが、1 はこの幅の違いを加減速に数えない)
#     (11) 1 の同じ区間の水深の幅 (最大 − 最小) / 平均が RANGE_ST 以下
#   落差の先の池の構成(result_ps1・pf0・pf1・pb0・pb1。上の池 → 段差 → 水平な下の池 → 段差 → 棚)も、流量の
#   3 段の終わりの値を読む。下の池には、段差を落ちた射流(H3)と、2 つ目の段差から上流へ延びる常流(H2)が
#   あり、その間に跳水が立つ。理論の跳水の位置は、両者の運動量関数 q²/(g h) + h²/2 が等しくなる所
#   (make_brink.py の jump_position)。モデルの跳水の位置は、下の池のセル中心のフルード数を線形に内挿して
#   1 になる所(足元からの距離)。
#   構成 ps1(直線。f_advection_bend = 1。直線の水路は 0 でも同じ = (5)):
#     (12) 跳水の位置が、理論の位置の JUMP_UP 上流〜JUMP_DN 下流の範囲(段落ちで水頭を失う分と、数値の跳水の
#          幅で、理論より 1〜2 セル上流に出る)
#     (13) 跳水より下流の常流の水深が H2 の理論に ±TOL_SUB(跳水の位置のセルから N_SKIP セル下流〜2 つ目の
#          段差の 125 m 上流)
#     (14) 足元のセルが射流で、水深が H3 の理論の FOOT_LO〜FOOT_HI 倍
#   構成 pf1(1 つ目の段差の足元のセルの直後で水路が斜めに 1 行ずれる。f_advection_bend = 1):
#     (15) 直線の水路と同じ水面形: 跳水の位置の差が TOL_JUMP_SAME 以下、足元のセルの水深が ±TOL_FOOT_SAME、
#          跳水より下流の水深が ±TOL_SUB_SAME、上の池の水深が ±TOL_UP_SAME(落ちてきた流れの勢いが、
#          足元の屈曲を越えて残る。屈曲は格子に載せたときの向きの違いで、水路は同じ)
#   構成 pf0(同じ水路。f_advection_bend = 0。0 の性質の記録):
#     (16) 足元のセルが常流で、水深が直線の水路の足元の FOOT_DROWN 倍より大きい(足元の屈曲の直後の辺が
#          落ちてきた流れの運動量を受け取らず、射流の区間が消える。(15) がこの違いを見分けていることの確認)
#   構成 pb1(1 つ目の段差の直前で水路が斜めに 1 行ずれる。f_advection_bend = 1):
#     (17) 下の池の 1〜4 番目のセルのエネルギー水頭が上の池を TOL_E を超えて上回らず、跳水が下の池の中に
#          あって、直線の水路の位置より TOL_JUMP_SAME を超えて下流にない(屈曲の分の損失で、射流の区間は
#          直線より短い)
#   構成 pb0(同じ水路。f_advection_bend = 0。0 の性質の記録):
#     (18) 跳水が直線の水路より JUMP_SWEEP を超えて下流にあるか、下の池の中にない(段差の直前の屈曲で
#          エネルギー水頭を得た射流が、跳水を押し流す。(9) と同じ性質)
#   構成 wd0・wd1(幅 2 セルの直線の水路の等流。f_advection_bend = 0・1):
#     (19) 路の 40〜80 % の区間の水深が、0 も 1 もマニングの等流の水深に ±TOL_WD で、0 と 1 の差が TOL_WD_SAME
#          以下(幅が 2 セル以上の水路では、岸沿いの斜めのリンクの風上側が壁になり、1 の経路の値が等流の中でも
#          使われる。経路の値は等流で u_e に一致して、損失を作らない)
#   合流部の池の構成(result_jp0・jp1・jt0・jt1。行き止まりの湾を持つ水平な池に、落差から 2 本の流れが入る)は、
#   流量の 3 段それぞれの終わりの 10 分(30〜40・70〜80・110〜120 分)の、池の 4 セル(湾の奥 A、B、C、D)の
#   水深の平均と振れ幅(最大 − 最小)を読む。流入は一定なので、定常な水面に落ち着くのが正しい。
#   構成 jp0(本流が斜めに入る池。f_advection_bend = 0):
#     (20) 測線の流量が湧き出しの合計に ±TOL_Q で、池の 4 セルの水深の振れ幅が RANGE_JP 以下(定常)
#   構成 jp1(同じ池。f_advection_bend = 1):
#     (21) jp0 と同じ結果: 池の 4 セルの水深の振れ幅が RANGE_JP 以下(定常)で、水深が jp0 に ±TOL_JP_SAME
#          (湾の奥へ落ちてくる浅く速い流入は、同じ線の先の池のセルへ続いている。その運動量は通常の風上が運ぶので、
#          経路の値は、池の中で曲がって出る辺へ同じ運動量を足さない。足すと、湾の水が余分に押し出されて水面が
#          揺れる。developer.md §110.14・§110.16)
#   構成 jt0(本流が南からまっすぐ入る T 字の合流。f_advection_bend = 0・f_advection_lateral = 0。この組み合わせの
#   性質の記録):
#     (22) 3 段とも、A の水深の振れ幅が RANGE_JP_DEF より大きい(この組み合わせは、この形の池では定常に
#          落ち着かない。f_advection_lateral = 1(古い値の組み合わせ)に f_advection_bend = 0 を組み合わせると、2 段目は
#          揺れず、1・3 段目は揺れる)
#   構成 jt1(同じ池。f_advection_bend = 1):
#     (23) 3 段とも、池の 4 セルの水深の振れ幅が RANGE_JT 以下(定常)
import sys, os, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_brink import (G, DX, NX, I_BRINK, N_APRON, Z_POOL, Q_LEVELS, T_RAMP, T_HOLD,
                        bed_brink, hcrit, pool_depth, apron_depth, path_stair,
                        NX_PL, N_MID, I_DROP1, I_DROP2, bed_pool, jump_position,
                        NX_WD, ROWS_WD, S_ST, N_ST_MAN, Q_ST, QW_LEVELS, QM_LEVELS)

TOL_Q = 0.015                     # (1) 流量の一致
TOL_POOL, TOL_POOL75 = 0.02, 0.04 # (2) 池の水深と理論の一致(125 m 以上上流、75 m 上流)
APRON_LO, APRON_HI = 0.95, 1.12   # (3) 棚の水深 / 理論
FR_ST = 1.2                       # (4) 棚のフルード数の下限(直線)
TOL_SAME = 1.0e-9                 # (5) 直線の 0 と 1 の水深の差 (m)
TOL_E = 0.2                       # (6) 棚のエネルギー水頭が池を上回ってよい幅 (m)
TOL_POOL_DG = 0.06                # (7) 斜めの構成の池の水深と理論の一致
APRON_HI_DG, FR_DG = 1.30, 1.1    # (8) 斜めの構成の棚の水深 / 理論の上限、フルード数の下限
E_EXCESS = 5.0                    # (9) 0 の棚のエネルギー水頭の超過の下限 (m)
TOL_ST, RANGE_ST = 0.01, 0.04     # (10)(11) 等流の階段状の水路
X_POOL = [75.0, 125.0, 225.0, 475.0, 725.0]     # (2)(7) 池の水深を比べる位置(段落ちから上流へ。m)
X_EPOOL = 475.0                   # (6)(9) 池のエネルギー水頭を取る位置
N_CHK = 4                         # (3)(4)(6)(8) 棚の先頭から比べるセル数(最後のセルは流出区間の引き込みの中)
JUMP_UP, JUMP_DN = 150.0, 25.0    # (12) 直線の水路の跳水の位置 − 理論の位置の範囲(上流側・下流側。m)
TOL_SUB, N_SKIP = 0.02, 3         # (13) 跳水より下流の水深と H2 の理論の一致、跳水の位置から飛ばすセル数
FOOT_LO, FOOT_HI = 0.95, 1.18     # (14) 足元のセルの水深 / H3 の理論
TOL_JUMP_SAME = 50.0              # (15)(17) 直線の水路との跳水の位置の差 (m)
TOL_FOOT_SAME, TOL_SUB_SAME, TOL_UP_SAME = 0.05, 0.015, 0.01     # (15) 足元・跳水より下流・上の池の水深(直線との比 − 1)
FOOT_DROWN = 1.5                  # (16) 0 の足元のセルの水深 / 直線の水路の足元の水深 の下限
JUMP_SWEEP = 250.0                # (18) 0 の跳水が直線の水路より下流へ押し出される距離の下限 (m)
X_EPOOL_PL = 325.0                # (17) 上の池のエネルギー水頭を取る位置(1 つ目の段差から上流へ。m)
TOL_WD, TOL_WD_SAME = 0.002, 1.0e-4     # (19) 幅 2 セルの等流の水深と理論の一致、0 と 1 の差(比 − 1)
T_WIN = 10.0                      # (20)〜(23) 各段の終わりの、水深の平均と振れ幅を取る時間 (min)
RANGE_JP = 0.05                   # (20)(21) 定常とみなす水深の振れ幅の上限 (m)
TOL_JP_SAME = 0.10                # (21) jp1 と jp0 の水深の差の上限 (m。古い組)
TOL_JP_SAME_NEW = 0.20            # (21) 同(新しい組。2 本の流入が合わさって速く出ていく加速を数える分、+0.05〜0.15 m)
RANGE_JP_DEF = 0.3                # (22) 揺れの記録の、振れ幅の下限 (m)
RANGE_JT = 0.10                   # (23) jt1 を定常とみなす水深の振れ幅の上限 (m)
JP_NAMES = "ABCD"                 # 合流部の池のプローブ 1〜4 のセル

# 組(引数。省略は old): old = 古い値の組み合わせ(f_advection_donor・f_advection_lateral・f_dry_head_cap = 3・1・3)の
# 構成(上の名前)、new = 4 つの値の組み合わせ(4・2・4)の構成(0 の構成は名前の末尾に n、1 の構成は 1 を 2 に替えた名前。
# f_advection_bend = 1 の項目を 2 で判定する)。どちらも 4 つのスイッチを明示している。jt0・jt0n は f_advection_lateral = 0
GROUP = sys.argv[1] if len(sys.argv) > 1 else "old"
if GROUP not in ("old", "new"):
    sys.exit("usage: Check_brink.py [old|new]")
BEND = 1 if GROUP == "old" else 2
if GROUP == "new":
    TOL_JP_SAME = TOL_JP_SAME_NEW


def N(base):
    """構成名(古い組の名前)→ この組の構成名"""
    if GROUP == "old":
        return base
    return base[:-1] + "2" if base.endswith("1") else base + "n"

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
    print("=== %s: straight channel (f_advection_bend = 0) vs 1-D theory ===" % N("st0"))
    c = Case(N("st0"))
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
    print("=== %s: straight channel, f_advection_bend = %d ===" % (N("st1"), BEND))
    c1 = Case(N("st1"))
    dmax = max(abs(a[3] - b[3]) for pa, pb in zip(c.pb, c1.pb) for a, b in zip(pa, pb))
    check(dmax <= TOL_SAME, "(5) same depths as st0 (max difference %.1e m <= %.0e)" % (dmax, TOL_SAME))


def check_diag():
    print("=== %s: diagonal link just before the brink, f_advection_bend = %d ===" % (N("dg1"), BEND))
    c = Case(N("dg1"))
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
    print("=== %s: same channel, f_advection_bend = 0 (record of the behaviour with 0) ===" % N("dg0"))
    c0 = Case(N("dg0"))
    for t, q_in in levels():
        de = c0.energy(I_BRINK + 1, t) - c0.energy(ip, t)
        check(de > E_EXCESS,
              "(9) t = %3.0f min (q = %.1f m2/s): apron energy head exceeds the pond's by %+.2f m (> %.1f; "
              "depth %.2f m, velocity %.1f m/s)"
              % (t, c0.q(t), de, E_EXCESS, c0.h(I_BRINK + 1, t), c0.q(t) / c0.h(I_BRINK + 1, t)))


class PoolCase:
    """落差の先の池の構成の結果(プローブ n は列 n + 2 の水路のセル。測線は棚の 2 番目のセルの列)"""
    def __init__(self, name):
        self.name = name
        self.pb = [series("result_%s/probes/probe%04d.csv" % (name, n)) for n in range(1, NX_PL - 1)]
        self.fl = series("result_%s/fluxes/flux0001.csv" % name)

    def q(self, t):
        return at(self.fl, t, 2) / DX

    def h(self, i, t):
        return at(self.pb[i - 3], t, 3)

    def mid(self, t):
        """下の池の水深(足元のセルから 2 つ目の段差の直前のセルまで)"""
        return [self.h(i, t) for i in range(I_DROP1 + 1, I_DROP2 + 1)]

    def energy(self, i, t):
        h = self.h(i, t)
        return bed_pool(i) + h + (self.q(t) / h) ** 2 / (2 * G)

    def jump(self, t):
        """下の池で流れが射流から常流へ変わる位置(足元から。m)。セル中心のフルード数を線形に内挿して
        1 になる所。足元のセルが常流なら 0、下の池の終わりまで射流なら None"""
        q = self.q(t)
        fr = [q / h / (G * h) ** 0.5 for h in self.mid(t)]
        if fr[0] < 1.0:
            return 0.0
        for j in range(1, len(fr)):
            if fr[j] < 1.0:
                return (j - 0.5 + (fr[j - 1] - 1.0) / (fr[j - 1] - fr[j])) * DX
        return None


def fmt_x(x):
    return "none" if x is None else "%.0f m" % x


def check_pool():
    print("=== %s: pond - drop - lower pond - drop, straight channel (f_advection_bend = %d) vs 1-D theory ===" % (N("ps1"), BEND))
    ps = PoolCase(N("ps1"))
    ref = {}
    for t, q_in in levels():
        q = ps.q(t)
        xj, xm = jump_position(q), ps.jump(t)
        mid = ps.mid(t)
        ok = xj is not None and xm is not None and -JUMP_UP <= xm - xj <= JUMP_DN
        check(ok, "(12) t = %3.0f min (q = %.1f m2/s): hydraulic jump at %s from the foot of the drop, theory %s "
              "(difference within -%.0f..+%.0f m)" % (t, q, fmt_x(xm), fmt_x(xj), JUMP_UP, JUMP_DN))
        if xm is None:
            continue
        c0 = int(xm / DX) + 1 + N_SKIP                     # 比べ始めるセル(下の池の中の番号。1 始まり)
        dev = [mid[c - 1] / pool_depth(q, (N_MID - c + 0.5) * DX) - 1.0 for c in range(c0, N_MID - 1)]
        check(len(dev) > 0 and max(abs(d) for d in dev) <= TOL_SUB,
              "(13) subcritical depth / H2 theory - 1 in cells %d-%d of the lower pond: %+.3f..%+.3f (within %.2f)"
              % (c0, N_MID - 2, min(dev), max(dev), TOL_SUB))
        r = mid[0] / apron_depth(q, 0.5 * DX)
        fr = q / mid[0] / (G * mid[0]) ** 0.5
        check(FOOT_LO <= r <= FOOT_HI and fr > 1.0,
              "(14) first cell below the drop: depth / H3 theory = %.3f (allowed %.2f-%.2f), Fr = %.2f (> 1)"
              % (r, FOOT_LO, FOOT_HI, fr))
        ref[t] = (xm, c0, mid, [ps.h(i, t) for i in range(5, I_DROP1 - 1)])
    print("=== %s: one diagonal link just after the first cell below the drop, f_advection_bend = %d ===" % (N("pf1"), BEND))
    c = PoolCase(N("pf1"))
    for t, q_in in levels():
        if t not in ref:
            check(False, "(15) t = %3.0f min: no jump in the straight channel to compare with" % t)
            continue
        xs, c0, mids, ups = ref[t]
        xm, mid = c.jump(t), c.mid(t)
        dfoot = mid[0] / mids[0] - 1.0
        dsub = max(abs(mid[k - 1] / mids[k - 1] - 1.0) for k in range(c0, N_MID + 1))
        dup = max(abs(c.h(i, t) / u - 1.0) for i, u in zip(range(5, I_DROP1 - 1), ups))
        ok = (xm is not None and abs(xm - xs) <= TOL_JUMP_SAME and abs(dfoot) <= TOL_FOOT_SAME
              and dsub <= TOL_SUB_SAME and dup <= TOL_UP_SAME)
        check(ok, "(15) t = %3.0f min: same profile as the straight channel: jump at %s (straight %s, within %.0f m), "
              "first cell %+.3f (within %.2f), cells %d-%d %.4f (within %.3f), upper pond %.4f (within %.2f)"
              % (t, fmt_x(xm), fmt_x(xs), TOL_JUMP_SAME, dfoot, TOL_FOOT_SAME, c0, N_MID, dsub, TOL_SUB_SAME,
                 dup, TOL_UP_SAME))
    print("=== %s: same channel, f_advection_bend = 0 (record of the behaviour with 0) ===" % N("pf0"))
    c0_ = PoolCase(N("pf0"))
    for t, q_in in levels():
        if t not in ref:
            continue
        xm, mid = c0_.jump(t), c0_.mid(t)
        r = mid[0] / ref[t][2][0]
        check(xm == 0.0 and r > FOOT_DROWN,
              "(16) t = %3.0f min: the first cell below the drop is subcritical (jump at %s) and %.2f times as deep "
              "as in the straight channel (> %.1f; %.2f m vs %.2f m)" % (t, fmt_x(xm), r, FOOT_DROWN, mid[0], ref[t][2][0]))
    print("=== %s: one diagonal link just before the drop, f_advection_bend = %d ===" % (N("pb1"), BEND))
    c = PoolCase(N("pb1"))
    ip = I_DROP1 - int(round((X_EPOOL_PL - 0.5 * DX) / DX))
    for t, q_in in levels():
        if t not in ref:
            continue
        xm = c.jump(t)
        de = [c.energy(I_DROP1 + k, t) - c.energy(ip, t) for k in range(1, N_CHK + 1)]
        ok = max(de) <= TOL_E and xm is not None and xm <= ref[t][0] + TOL_JUMP_SAME
        check(ok, "(17) t = %3.0f min: energy head of lower-pond cells 1-%d - upper pond = %s m (<= %.1f); jump at %s "
              "(straight %s; not farther downstream)"
              % (t, N_CHK, " ".join("%+.2f" % d for d in de), TOL_E, fmt_x(xm), fmt_x(ref[t][0])))
    print("=== %s: same channel, f_advection_bend = 0 (record of the behaviour with 0) ===" % N("pb0"))
    c0_ = PoolCase(N("pb0"))
    for t, q_in in levels():
        if t not in ref:
            continue
        xm = c0_.jump(t)
        check(xm is None or xm - ref[t][0] > JUMP_SWEEP,
              "(18) t = %3.0f min: the jump is swept downstream: at %s (straight %s; more than %.0f m farther, or none)"
              % (t, fmt_x(xm), fmt_x(ref[t][0]), JUMP_SWEEP))


def last_depth(rdir):
    fs = sorted(f for f in glob.glob(rdir + "/H[0-9][0-9][0-9][0-9].txt") if int(f[-8:-4]) < 9000)
    return [[float(v) for v in ln.split()] for ln in open(fs[-1])]


def check_stair():
    print("=== %s, %s: uniform flow in a channel of alternating east and north-east links ===" % (N("sr0"), N("sr1")))
    cells = path_stair()
    a, b = int(0.4 * len(cells)), int(0.8 * len(cells))
    stat = {}
    for name in (N("sr0"), N("sr1")):
        hh = last_depth("result_" + name)
        seg = [hh[j - 1][i - 1] for i, j, _ in cells[a:b]]
        stat[name] = (sum(seg) / len(seg), min(seg), max(seg))
        print("  %s: mean depth %.4f m (min %.4f, max %.4f)" % ((name,) + stat[name]))
    r = stat[N("sr1")][0] / stat[N("sr0")][0] - 1.0
    check(abs(r) <= TOL_ST, "(10) mean depth with f_advection_bend = %d / 0 - 1 = %+.4f (within %.2f)" % (BEND, r, TOL_ST))
    rng = (stat[N("sr1")][2] - stat[N("sr1")][1]) / stat[N("sr1")][0]
    check(rng <= RANGE_ST, "(11) depth range (max - min) / mean with %d = %.4f (<= %.2f)" % (BEND, rng, RANGE_ST))


def check_wide():
    print("=== %s, %s: uniform flow in a straight channel two cells wide ===" % (N("wd0"), N("wd1")))
    hn = (Q_ST / DX * N_ST_MAN / S_ST ** 0.5) ** 0.6       # マニングの等流の水深(広い矩形断面)
    a, b = int(0.4 * NX_WD), int(0.8 * NX_WD)
    mean = {}
    for name in (N("wd0"), N("wd1")):
        hh = last_depth("result_" + name)
        seg = [hh[j - 1][i] for j in ROWS_WD for i in range(a, b)]
        mean[name] = sum(seg) / len(seg)
        print("  %s: mean depth %.5f m (min %.5f, max %.5f), normal depth %.5f m"
              % (name, mean[name], min(seg), max(seg), hn))
    d0, d1, ds = mean[N("wd0")] / hn - 1.0, mean[N("wd1")] / hn - 1.0, mean[N("wd1")] / mean[N("wd0")] - 1.0
    check(abs(d0) <= TOL_WD and abs(d1) <= TOL_WD and abs(ds) <= TOL_WD_SAME,
          "(19) depth / normal depth - 1 = %+.5f with 0, %+.5f with %d (within %.3f); %d / 0 - 1 = %+.1e (within %.0e)"
          % (d0, d1, BEND, TOL_WD, BEND, ds, TOL_WD_SAME))


class JunctionCase:
    """合流部の池の構成の結果(プローブ 1〜4 は池の A・B・C・D。測線は流出区間)"""
    def __init__(self, name):
        self.name = name
        self.pb = [series("result_%s/probes/probe%04d.csv" % (name, n)) for n in range(1, 5)]
        self.fl = series("result_%s/fluxes/flux0001.csv" % name)

    def stat(self, t):
        """t (min) までの T_WIN 分間の、池の 4 セルの水深の (平均, 振れ幅) の並び"""
        out = []
        for rows in self.pb:
            seg = [r[3] for r in rows if t - T_WIN <= r[1] <= t]
            out.append((sum(seg) / len(seg), max(seg) - min(seg)))
        return out

    def discharge(self, t):
        seg = [r[2] for r in self.fl if t - T_WIN <= r[1] <= t]
        return sum(seg) / len(seg)


def stages():
    t = 0.0
    for qw, qm in zip(QW_LEVELS, QM_LEVELS):
        t += T_RAMP + T_HOLD
        yield t, qw, qm


def fmt_stat(st):
    return " ".join("%s %.2f (%.2f)" % (n, m, r) for n, (m, r) in zip(JP_NAMES, st))


def check_junction():
    print("=== %s: pond with a dead-end bay, main stream entering diagonally (f_advection_bend = 0) ===" % N("jp0"))
    j0 = JunctionCase(N("jp0"))
    ref = {}
    for t, qw, qm in stages():
        st, q = j0.stat(t), j0.discharge(t)
        ref[t] = st
        print("  t = %3.0f min (inflow %.0f + %.0f m3/s): depth m (range m) %s" % (t, qw, qm, fmt_stat(st)))
        check(abs(q / (qw + qm) - 1.0) <= TOL_Q and max(r for _, r in st) <= RANGE_JP,
              "(20) steady: outflow / inflow - 1 = %+.4f (within %.3f), largest depth range %.3f m (<= %.2f)"
              % (q / (qw + qm) - 1.0, TOL_Q, max(r for _, r in st), RANGE_JP))
    print("=== %s: same pond, f_advection_bend = %d ===" % (N("jp1"), BEND))
    j1 = JunctionCase(N("jp1"))
    for t, qw, qm in stages():
        st = j1.stat(t)
        print("  t = %3.0f min (inflow %.0f + %.0f m3/s): depth m (range m) %s" % (t, qw, qm, fmt_stat(st)))
        dev = [m - m0 for (m, _), (m0, _) in zip(st, ref[t])]
        check(max(r for _, r in st) <= RANGE_JP and max(abs(d) for d in dev) <= TOL_JP_SAME,
              "(21) same as with 0: largest depth range %.3f m (<= %.2f), depth - depth with 0 = %s m (within %.2f)"
              % (max(r for _, r in st), RANGE_JP, " ".join("%+.2f" % d for d in dev), TOL_JP_SAME))
    print("=== %s: pond with a dead-end bay, main stream entering straight (f_advection_bend = 0, f_advection_lateral = 0; record) ===" % N("jt0"))
    t0 = JunctionCase(N("jt0"))
    for t, qw, qm in stages():
        st = t0.stat(t)
        print("  t = %3.0f min (inflow %.0f + %.0f m3/s): depth m (range m) %s" % (t, qw, qm, fmt_stat(st)))
        check(st[0][1] > RANGE_JP_DEF,
              "(22) the water surface keeps oscillating with bend 0 and lateral 0: depth range in the bay cell A %.2f m (> %.1f)"
              % (st[0][1], RANGE_JP_DEF))
    print("=== %s: same pond, f_advection_bend = %d ===" % (N("jt1"), BEND))
    t1 = JunctionCase(N("jt1"))
    for t, qw, qm in stages():
        st = t1.stat(t)
        print("  t = %3.0f min (inflow %.0f + %.0f m3/s): depth m (range m) %s" % (t, qw, qm, fmt_stat(st)))
        check(max(r for _, r in st) <= RANGE_JT,
              "(23) steady: largest depth range %.3f m (<= %.2f)" % (max(r for _, r in st), RANGE_JT))


if __name__ == "__main__":
    check_straight()
    check_diag()
    check_stair()
    check_pool()
    check_wide()
    check_junction()
    if nfail:
        print("=== Check_brink.py %s: FAIL (%d) ===" % (GROUP, nfail))
        sys.exit(1)
    print("=== Check_brink.py %s: PASS ===" % GROUP)
