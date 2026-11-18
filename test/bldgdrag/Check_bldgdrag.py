#!/usr/bin/env python3
# bldgdrag 検定(developer.md §107)
#   result_{shallow,deep,dense} の出力 H, V(x = X1〜X2)を読み、構成ごとに
#     (1) 定常: 後半の 2 時刻(45 分・90 分)の水深の差が TOL_STEADY 以内
#     (2) 等流: 水面勾配が河床勾配 S に ±2 % で一致
#     (3) 質量収支: 行ごとの V·h の和(断面流量)が Q に 1e-3 で一致
#     (4) 家屋の抗力を含む等流の理論値に一致: 水深 h/h_u と流速 V/V_u が全行で 1 ± TOL_U
#         (h_u は gv g S = [gv g n²/h^{4/3} + (kk·cd/2)(1 − gv)/B] V²、q = V h の解)
#   と、3 構成を通して
#     (5) 家屋の抗力が効いている: 等流水深が、家屋のない水路のマニングの水深より深い
#         (浅い構成で 1.05 倍以上、深い 2 構成で 1.5 倍以上)
#   を判定する。係数に水深を掛けた式(2026-11-12 までの誤り)では、深い構成の水深が理論値の
#   2 倍を超えるので (4) で検出される
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_init import NX, NY, DX, S, N, G, W, X1, X2, Z0, CONFIGS, rows, uniform_depth, manning_depth, drag_coef

TOL_STEADY, TOL_SLOPE, TOL_Q, TOL_U = 1.0e-3, 0.02, 1.0e-3, 0.005


def load(rdir, name, k):
    return [[float(v) for v in line.split()] for line in open("%s/%s%04d.txt" % (rdir, name, k))]


def section(cfg):
    rdir = "result_%s" % cfg
    h1 = load(rdir, "H", 1); h = load(rdir, "H", 2); v = load(rdir, "V", 2)
    j1, j2 = rows()
    i1, i2 = int(X1 / DX), int(X2 / DX)
    hrow = [sum(h[j - 1][i1:i2]) / (i2 - i1) for j in range(j1, j2 + 1)]
    vrow = [sum(v[j - 1][i1:i2]) / (i2 - i1) for j in range(j1, j2 + 1)]
    dsteady = max(abs(h[j - 1][i] - h1[j - 1][i]) for j in range(j1, j2 + 1) for i in range(i1, i2))
    # 水面 = 河床(make_init.py と同じ式)+ 水深。区間の両端の差から水面勾配
    ws = [sum(h[j - 1][i] for j in range(j1, j2 + 1)) / W + Z0 - S * (i + 0.5) * DX for i in range(i1, i2)]
    slope = (ws[0] - ws[-1]) / ((i2 - i1 - 1) * DX)
    qsum = sum(hr * vr for hr, vr in zip(hrow, vrow)) * DX
    return hrow, vrow, dsteady, slope, qsum


ok = True
for cfg, c in CONFIGS.items():
    hu = uniform_depth(c); vu = c["q"] / hu; hm = manning_depth(c["q"])
    hrow, vrow, dsteady, slope, qsum = section(cfg)
    qtot = c["q"] * W * DX
    print("%s: gv = %g, B = %g m, cd = %g, kk = %g, q = %g m2/s → 理論の等流 h_u = %.4f m, V_u = %.4f m/s"
          "(家屋なしのマニング %.4f m。抗力の係数 %.5f 1/m)" % (cfg, c["gv"], c["bb"], c["cd"], c["kk"], c["q"], hu, vu, hm, drag_coef(c)))
    g1 = dsteady < TOL_STEADY
    g2 = abs(slope / S - 1.0) < TOL_SLOPE
    g3 = abs(qsum / qtot - 1.0) < TOL_Q
    hr = max(abs(x / hu - 1.0) for x in hrow); vr = max(abs(x / vu - 1.0) for x in vrow)
    g4 = hr < TOL_U and vr < TOL_U
    print("(1) %-7s 定常: 45 分と 90 分の水深の差の最大 %.2e m (< %.0e) : %s" % (cfg, dsteady, TOL_STEADY, "PASS" if g1 else "FAIL"))
    print("(2) %-7s 水面勾配 %.5f (S = %.5f, ±%.0f%%) : %s" % (cfg, slope, S, 100 * TOL_SLOPE, "PASS" if g2 else "FAIL"))
    print("(3) %-7s 断面流量 Σ V h dy / Q = %.5f (±%.0e) : %s" % (cfg, qsum / qtot, TOL_Q, "PASS" if g3 else "FAIL"))
    print("(4) %-7s 理論の等流に一致: h/h_u = %.4f、V/V_u = %.4f(行ごとの最大の差 %.4f・%.4f、tol %.3f) : %s"
          % (cfg, sum(hrow) / W / hu, sum(vrow) / W / vu, hr, vr, TOL_U, "PASS" if g4 else "FAIL"))
    lim = 1.05 if cfg == "shallow" else 1.5
    g5 = sum(hrow) / W / hm > lim
    print("(5) %-7s 家屋の抗力が効いている: h / (家屋なしのマニングの水深) = %.3f (> %.2f) : %s"
          % (cfg, sum(hrow) / W / hm, lim, "PASS" if g5 else "FAIL"))
    ok = ok and g1 and g2 and g3 and g4 and g5
print("=== bldgdrag checks %s ===" % ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
