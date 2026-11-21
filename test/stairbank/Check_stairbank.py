#!/usr/bin/env python3
"""test/stairbank の検定: 格子に斜めの 1 セル幅の河道と、脇の高いセル(段・角のセル)。

  1 セル幅の河道(8 連結)に、流量を 2,000 → 10,000 → 2,000 m3/s と段階的に上げ下げして与える。河道でないセルが
  全部、水の届かない壁の構成(壁だけ)と、河床より 10 m 高い段・角のセルを持つ構成を、古い値の組み合わせ
  (f_advection_donor・f_advection_bend・f_advection_lateral・f_dry_head_cap = 3・1・1・3)と、4 つの値の組み合わせ
  (構成名の末尾が 4。4・2・2・4)で計算する(どちらも 4 つを明示)。

  判定する項目(壁だけの 3 つの形 zw・dw・sw。どちらの規則でも):
    (1) 定常: 各段の終わり 10 分の水深の幅が TOL_RANGE 未満、測線の流量の標準偏差が与えた流量の TOL_SIGMA 未満
    (2) 質量の収支: 各段の終わり 10 分の測線の流量の平均が、与えた流量に ±TOL_MASS
    (3) 流量を上げるときと下げるときで、同じ流量の水深が同じ(差 TOL_UPDN 未満)
  記録する項目(段・角のセルのある 4 つの形 zs・ds・sa・sab の、古い値の組み合わせ。その規則の限界。README):
    (4) 同じ流量の、上げるときと下げるときの水深の差(同じ流量で 2 つの状態を持つ)と、壁だけとの差
    (5) 各段の測線の流量の標準偏差の最大
    (6) 角のセルによる、階段の直後のセルのせき上げ(壁だけの構成 sw との水深の差)
    (7) 領域の最大流速(壁だけの構成との比)と、計算の終わりに壁のセルに残る水深の最大
  判定する項目(4 つの値の組み合わせ。構成名の末尾が 4):
    (8) 壁だけの形(zw4・dw4・sw4)は、古い値の組み合わせと同じ水深(差 TOL_SAME 未満)
    (9) 段・角のセルのある形(zs4・ds4・sa4・sab4)で、上げるときと下げるときの同じ流量の水深の差が TOL_UPDN4 未満
        (同じ流量に 2 つの状態を持たない)
    (10) 同じ形で、エネルギーが増えない: 領域の最大流速が、壁だけの形の R_VMAX 倍以下で、計算の終わりに壁のセルに
         水が残らない(TOL_WALL 未満)
    (11) 同じ形で、各段の測線の流量の標準偏差が、与えた流量の TOL_SIGMA4 未満
  (9)〜(11) の形の、壁だけの形との水深の差は、残っている限界として記録する(README)。
標準ライブラリだけ。python3 Check_stairbank.py
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_stairbank import SHAPES, STAGES, T_ENDS, WALL_OF, build, probes

TOL_RANGE = 0.20         # (1) 終わり 10 分の水深の幅 (m)
TOL_SIGMA = 0.01         # (1) 終わり 10 分の測線の流量の標準偏差の、与えた流量に対する比
TOL_MASS = 0.005         # (2) 終わり 10 分の測線の流量の平均の、与えた流量からの相対差
TOL_UPDN = 0.02          # (3) 上げ下げの同じ流量の水深の差 (m)
TOL_SAME = 0.02          # (8) 壁だけの形の、古い値の組み合わせとの水深の差 (m)
TOL_UPDN4 = 0.5          # (9) 段・角のセルのある形の、上げ下げの同じ流量の水深の差 (m)
R_VMAX = 1.1             # (10) 最大流速の、壁だけの形に対する比の上限
TOL_WALL = 0.01          # (10) 計算の終わりに壁のセルに残る水深 (m)
TOL_SIGMA4 = 0.05        # (11) 測線の流量の標準偏差の、与えた流量に対する比
T_WIN = 10.0             # 各段の終わりの、平均を取る時間(分)
WALLS = ("zw", "dw", "sw")
OPENS = ("zs", "ds", "sa", "sab")


def read(path):
    rows = []
    for line in open(path):
        if line.startswith("#") or not line.strip():
            continue
        rows.append([float(v) for v in line.replace(",", " ").split()])
    return rows


def stats(vals):
    n = len(vals)
    mean = sum(vals) / n
    return mean, math.sqrt(sum((v - mean) ** 2 for v in vals) / n), max(vals) - min(vals)


def stage_table(name):
    """各段の終わり T_WIN 分の、(与えた流量, 測線の流量の平均・標準偏差, [プローブごとの水深の平均・幅])"""
    fl = read("result_%s/fluxes/flux0001.csv" % name)
    npb = len(probes(name)[0])
    pb = [read("result_%s/probes/probe%04d.csv" % (name, n + 1)) for n in range(npb)]
    out = []
    for n, q in enumerate(STAGES):
        t1 = T_ENDS[n]
        t0 = t1 - T_WIN
        qm, qs, _ = stats([r[2] for r in fl if t0 <= r[1] <= t1])
        hs = [stats([r[3] for r in p if t0 <= r[1] <= t1]) for p in pb]
        out.append((q, qm, qs, [(h[0], h[2]) for h in hs]))
    return out


def vmax(name):
    """Log.txt の V_max の列の、期間の最大"""
    v = 0.0
    for line in open("result_%s/Log.txt" % name):
        w = line.split()
        if len(w) >= 8 and w[0].count(":") == 2:
            try:
                v = max(v, float(w[7]))
            except ValueError:
                pass
    return v


def wall_depth(name):
    """計算の終わりの、壁のセル(河道でも段・角のセルでもないセル)の水深の最大"""
    nx, ny, z, rw, path, side = build(name)
    spec_shelf = name.rstrip("4") in ("zs", "ds")
    ch = set(path)
    open_cells = set(side)
    if spec_shelf:
        for j in range(1, ny + 1):
            for i in range(1, nx + 1):
                if (i, j) not in ch and min(max(abs(p[0] - i), abs(p[1] - j)) for p in path) == 1:
                    open_cells.add((i, j))
    h = [[float(v) for v in line.split()] for line in open("result_%s/H9999.txt" % name) if line.strip()]
    return max(h[j - 1][i - 1] for j in range(1, ny + 1) for i in range(1, nx + 1)
               if (i, j) not in ch and (i, j) not in open_cells)


def main():
    ok = True
    cases = [g + r for r in ("", "4") for g in SHAPES]
    tab = {c: stage_table(c) for c in cases}
    vm = {c: vmax(c) for c in cases}
    kmid = {c: (2 if c.startswith("s") else 1) for c in cases}     # 見るプローブ: 階段・対角は流路の中ほど、1 つの階段は直後のセル
    half = len(STAGES) // 2
    nst = len(STAGES)

    def judge(text, val, good, cond):
        nonlocal ok
        ok = ok and good
        print("  %s: %s (%s) : %s" % (text, val, cond, "PASS" if good else "FAIL"))

    print("=== stairbank: 斜めの 1 セル幅の河道と、脇の高いセル(流量 %s m3/s を 30 分ずつ。最後は 90 分) ===" %
          " → ".join("%.0f" % q for q in STAGES))
    print("  構成   " + " ".join("%7.0f%s" % (q, "↑" if n < half else ("  " if n == half else "↓")) for n, q in enumerate(STAGES))
          + "   流量の標準偏差の最大  最大流速")
    for c in cases:
        k = kmid[c]
        print("  %-5s  " % c + " ".join("%8.2f" % r[3][k][0] for r in tab[c])
              + "   %8.0f m3/s      %5.1f m/s" % (max(r[2] for r in tab[c]), vm[c]))
    print("  (水深 m。zw・zs・dw・ds は流路の中ほどの河道のセル、sw・sa・sab は階段の直後のセル。末尾の 4 は、4 つの値の組み合わせ)")

    print("--- 判定: 壁だけの形(古い値の組み合わせと、4 つの値の組み合わせ) ---")
    for c in [g + r for r in ("", "4") for g in WALLS]:
        rng = max(h[1] for r in tab[c] for h in r[3])
        sig = max(r[2] / r[0] for r in tab[c])
        mass = max(abs(r[1] - r[0]) / r[0] for r in tab[c])
        updn = max(abs(tab[c][n][3][k][0] - tab[c][nst - 1 - n][3][k][0])
                   for n in range(half) for k in range(len(tab[c][n][3])))
        judge("%s (1) 定常: 終わり 10 分の水深の幅の最大" % c, "%.4f m" % rng, rng < TOL_RANGE, "< %g" % TOL_RANGE)
        judge("%s (1) 定常: 測線の流量の標準偏差 / 与えた流量 の最大" % c, "%.4f" % sig, sig < TOL_SIGMA, "< %g" % TOL_SIGMA)
        judge("%s (2) 質量: 測線の流量の平均と与えた流量の相対差の最大" % c, "%.4f" % mass, mass < TOL_MASS, "< %g" % TOL_MASS)
        judge("%s (3) 上げ下げの同じ流量の水深の差の最大" % c, "%.4f m" % updn, updn < TOL_UPDN, "< %g" % TOL_UPDN)
    for g in WALLS:
        same = max(abs(tab[g + "4"][n][3][k][0] - tab[g][n][3][k][0]) for n in range(nst) for k in range(len(tab[g][n][3])))
        judge("%s4 (8) 古い値の組み合わせ(%s)との水深の差の最大" % (g, g), "%.4f m" % same, same < TOL_SAME, "< %g" % TOL_SAME)

    print("--- 記録(判定しない。古い値の組み合わせの限界): 段・角のセルのある形 ---")
    for c in OPENS:
        w = WALL_OF[c]
        k = kmid[c]
        updn = [tab[c][n][3][k][0] - tab[c][nst - 1 - n][3][k][0] for n in range(half)]
        dwall = [tab[c][n][3][k][0] - tab[w][n][3][k][0] for n in range(nst)]
        print("  %s (4) 上げるとき − 下げるとき の水深 (m。2,000・4,000・6,000・8,000): %s" %
              (c, "・".join("%+.2f" % v for v in updn)))
        print("  %s (4)(6) 壁だけ(%s)との水深の差 (m。段ごと): %s" % (c, w, "・".join("%+.2f" % v for v in dwall)))
        print("  %s (5) 測線の流量の標準偏差の最大 %.0f m3/s(壁だけ %.0f)" %
              (c, max(r[2] for r in tab[c]), max(r[2] for r in tab[w])))
        print("  %s (7) 最大流速 %.1f m/s(壁だけ %.1f の %.2f 倍)、終わりに壁のセルに残る水深の最大 %.3f m" %
              (c, vm[c], vm[w], vm[c] / vm[w], wall_depth(c)))

    print("--- 判定: 段・角のセルのある形を、4 つの値の組み合わせで ---")
    for g in OPENS:
        c, w = g + "4", WALL_OF[g] + "4"
        k = kmid[c]
        updn = [tab[c][n][3][k][0] - tab[c][nst - 1 - n][3][k][0] for n in range(half)]
        dwall = [tab[c][n][3][k][0] - tab[w][n][3][k][0] for n in range(nst)]
        sig = max(r[2] / r[0] for r in tab[c])
        hw = wall_depth(c)
        ud = max(abs(v) for v in updn)
        judge("%s (9) 上げるとき − 下げるとき の水深 (m。2,000・4,000・6,000・8,000)" % c,
              "・".join("%+.2f" % v for v in updn), ud < TOL_UPDN4, "絶対値 < %g" % TOL_UPDN4)
        judge("%s (10) 最大流速 / 壁だけの形(%s)" % (c, w), "%.1f / %.1f m/s = %.2f" % (vm[c], vm[w], vm[c] / vm[w]),
              vm[c] <= R_VMAX * vm[w], "<= %g" % R_VMAX)
        judge("%s (10) 終わりに壁のセルに残る水深の最大" % c, "%.3f m" % hw, hw < TOL_WALL, "< %g" % TOL_WALL)
        judge("%s (11) 測線の流量の標準偏差 / 与えた流量 の最大" % c, "%.4f" % sig, sig < TOL_SIGMA4, "< %g" % TOL_SIGMA4)
        print("  %s 記録: 壁だけ(%s)との水深の差 (m。段ごと): %s" % (c, w, "・".join("%+.2f" % v for v in dwall)))

    print("=== stairbank checks %s ===" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
