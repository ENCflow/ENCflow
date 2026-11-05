#!/usr/bin/env python3
"""slopefric(急斜面の薄層流の摩擦)の検定。

  使い方: Check_slopefric.py [table]   (table を付けると判定の前にケースごとの値を表で出す)

一様な急斜面(make_init.py。傾斜角 30°)に一定の雨を降らせた定常の薄層流で、壁と流出の辺から
MARGIN セル以上離れ、水深が HMIN 以上のセルの、水深 h(鉛直)と水平の単位幅流量 q = h |V|
(出力の H・u・v)を、等流の関係(水深の勾配と移流が勾配に比べて小さい局所の釣り合い)と比べる。
  f_gravity_correction = 1(g1): 古典の水平投影のマニング式 h = (n² q² / tanθ)^{3/10}
      (有効重力 g_e が勾配と摩擦の両方に掛かって相殺する。developer.md §91・docs/steep_slope_design.md §2.3)
  f_gravity_correction = 2(g2): 斜面に沿う式の等流 h_n = (n² q² / sinθ)^{3/10}、h = h_n / cosθ
      (摩擦を斜面に沿う速さと地盤に直角な水深で評価。developer.md §93。Chow 1959、Van Emelen ら 2014)
  (1) 関係: 評価するセルの h / h_解析 の平均が 1 から TOL_MEAN 以内、各セルが TOL_CELL 以内
  (2) 向き・近傍によらない: 下り向き 0°・22.5°・45° と 8・4 近傍の全部で (1) が成り立つ
  (3) 検出力: g2 の水深は g1 の式から cos^{-13/10}θ(30° で 1.206 倍)ずれる(2 つの式が区別できる)
  (4) 流砂のせん断(_sed の構成): 掃流砂の侵食の始まりが、無次元掃流力が τ*c に達する流下方向の
      水平距離 ℓ_c(make_init.sed_lc。g1 は古典の τ* = h tanθ/(s d)、g2 は斜面に沿う底面せん断
      τ* = h_n sinθ/(s d))と合う: 内部のセルで ℓ <= ℓ_c − SED_UP は侵食なし、
      ℓ_c + SED_DOWN <= ℓ <= ℓ_c + SED_DOWN2 は侵食(侵食は流砂量の発散で、辺の τ* は両セルの平均なので、
      始まりは ℓ_c の前後 1 セル程度でぶれる。下流の帯を始まりの近くに限るのは、始まりから離れると
      流砂量が増えて河床の変化が流れと干渉しうるため)。g1 と g2 の ℓ_c の差(約 4.6 m)はこの幅より大きく、
      取り違えると (4) が落ちる
出力の H は小数 4 桁(0.1 mm)なので、印字の丸めが 1 % 未満になる HMIN 以上のセルで比べる。
"""
import math
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_init as mi

MARGIN = 5                   # 壁・流出の辺からのセル数
SED_UP, SED_DOWN, SED_DOWN2 = 1.5, 2.0, 6.0   # 侵食の始まりの判定の幅 (m)
SED_CORNER = 3.0             # 斜めの斜面で除く、上の角を通る流線(西と南の壁の流線の合わせ目)からの距離 (m)
DZ_EPS = 5.0e-5              # 侵食とみなす河床の低下 (m)(Z の印字の半量子)
HMIN = 0.008                 # 評価する水深の下限 (m)(印字の丸め 0.05 mm が 0.6 % 以下)
TOL_MEAN, TOL_CELL = 0.005, 0.015


def read_txt(path):
    return [[float(v) for v in line.split()] for line in open(path) if line.strip()]


def last_frame(rdir):
    return max(int(l.split(",")[0]) for l in open(f"{rdir}/FILENUMBER.csv")
               if not l.startswith("#") and int(l.split(",")[0]) < 9000)


def h_analytic(q, gc):
    th = math.radians(mi.THETA)
    if gc == 1:
        return (mi.RN ** 2 * q * q / math.tan(th)) ** 0.3
    return (mi.RN ** 2 * q * q / math.sin(th)) ** 0.3 / math.cos(th)


def ratios(case, gc):
    rdir = f"result_{case}"
    k = last_frame(rdir)
    h = read_txt(f"{rdir}/H{k:04d}.txt")
    u = read_txt(f"{rdir}/u{k:04d}.txt")
    v = read_txt(f"{rdir}/v{k:04d}.txt")
    n = len(h)
    out = []
    for j in range(MARGIN, n - MARGIN):
        for i in range(MARGIN, n - MARGIN):
            hh = h[j][i]
            if hh < HMIN:
                continue
            q = hh * math.hypot(u[j][i], v[j][i])
            out.append(hh / h_analytic(q, gc))
    return out


def check_sed(show):
    """(4) 掃流砂の侵食の始まりの位置。"""
    ok = True
    rows = []
    for phi, nb, gc in mi.CASES_SED:
        case = mi.case_name(phi, nb, gc, sed=True)
        rdir = f"result_{case}"
        k = last_frame(rdir)
        z0 = read_txt(f"{rdir}/Z0000.txt")[::-1]          # 行 0 が南端
        z1 = read_txt(f"{rdir}/Z{k:04d}.txt")[::-1]
        lc = mi.sed_lc(gc)
        ph = math.radians(phi)
        n = len(z0)
        nup = ndown = bad_up = bad_down = 0
        first = None
        for j in range(MARGIN, n - MARGIN):
            y = (j + 0.5) * mi.DX
            for i in range(MARGIN, n - MARGIN):
                x = (i + 0.5) * mi.DX
                if phi > 0.0 and abs(x * math.sin(ph) - y * math.cos(ph)) < SED_CORNER:
                    continue          # 流下距離 ℓ が折れる角の流線の近く(横への広がりで水深が浅く、始まりが遅れる)
                ell = x / math.cos(ph) if phi == 0.0 else min(x / math.cos(ph), y / math.sin(ph))
                eroded = (z1[j][i] - z0[j][i]) < -DZ_EPS
                if eroded and (first is None or ell < first):
                    first = ell
                if ell <= lc - SED_UP:
                    nup += 1
                    bad_up += eroded
                elif lc + SED_DOWN <= ell <= lc + SED_DOWN2:
                    ndown += 1
                    bad_down += not eroded
        rows.append((case, phi, gc, lc, first, nup, bad_up, ndown, bad_down))
        if bad_up or bad_down or nup == 0 or ndown == 0:
            print(f"FAIL (4) {case}: ℓ_c = {lc:.2f} m に対し、上流で侵食 {bad_up}/{nup}、下流で侵食なし {bad_down}/{ndown}")
            ok = False
    if show or not ok:
        print("case              phi gc  l_c(m)  first(m)  up(eroded/cells)  down(not eroded/cells)")
        for case, phi, gc, lc, first, nup, bu, nd, bd in rows:
            fs = f"{first:8.2f}" if first is not None else "     n/a"
            print(f"{case:16s} {phi:5.1f} {gc:2d} {lc:7.2f} {fs}   {bu}/{nup}   {bd}/{nd}")
    return ok


def main():
    show = "table" in sys.argv[1:]
    ok = True
    rows = []
    for phi, nb, gc in mi.CASES:
        case = mi.case_name(phi, nb, gc)
        r = ratios(case, gc)
        if not r:
            print(f"FAIL {case}: 評価するセルがない")
            ok = False
            continue
        mean = sum(r) / len(r)
        rows.append((case, phi, nb, gc, len(r), mean, min(r), max(r)))
        if abs(mean - 1.0) > TOL_MEAN:
            print(f"FAIL (1) {case}: h / h_解析 の平均 {mean:.4f} が 1 から {TOL_MEAN} を超えてずれる")
            ok = False
        if max(abs(min(r) - 1.0), abs(max(r) - 1.0)) > TOL_CELL:
            print(f"FAIL (1) {case}: h / h_解析 が {min(r):.4f}〜{max(r):.4f}(各セルの許容 {TOL_CELL})")
            ok = False
    # (3) 検出力: g2 の水深を g1 の式で測ると cos^{-13/10}θ ずれる
    expect = math.cos(math.radians(mi.THETA)) ** (-1.3)
    for phi, nb, gc in mi.CASES:
        if gc != 2:
            continue
        case = mi.case_name(phi, nb, gc)
        r1 = ratios(case, 1)
        m1 = sum(r1) / len(r1)
        if abs(m1 / expect - 1.0) > 2 * TOL_MEAN:
            print(f"FAIL (3) {case}: g1 の式に対する比 {m1:.4f} が cos^-1.3θ = {expect:.4f} と合わない")
            ok = False
    if show or not ok:
        print("case              phi  nb gc  cells  mean    min     max")
        for case, phi, nb, gc, nc, mean, lo, hi in rows:
            print(f"{case:16s} {phi:5.1f} {nb:2d} {gc:2d} {nc:6d}  {mean:.4f}  {lo:.4f}  {hi:.4f}")
    ok = check_sed(show) and ok
    print("=== slopefric " + ("PASS" if ok else "FAIL") + " ===")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
