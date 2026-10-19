#!/usr/bin/env python3
# uniflow 検定(developer.md §84.7)
#   result_w{1,5}_{off,on} の最終出力 H, V(x = 400〜700 m)を読み、
#     (1) 定常・等流: 水面勾配が河床勾配 S に ±2 % で一致(4 構成)
#     (2) 質量収支: 行ごとの V·h の和(断面流量)が Q に 1e-3 で一致(4 構成)
#     (3) f_opening_dynamic = 2 は Manning に一致: 水深 h/h_n と流速 V/V_n が
#         全行で 1 ± TOL_MAN(幅 1・5)
#     (4) 振り替えなし(0)の既知の性質を記録: 幅 1 で h/h_n > 1.2、幅 5 で
#         河岸行 / 内部行の流速比 < 0.9(値は表示。判定は上限の緩い確認のみ)
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_init import NX, NY, DX, S, N, H0, Q_UNIT, X1, X2, rows

TOL_SLOPE, TOL_Q, TOL_MAN = 0.02, 1.0e-3, 0.005
HN, VN = H0, Q_UNIT / H0


def load(rdir, name, k=3):
    return [[float(v) for v in line.split()] for line in open("%s/%s%04d.txt" % (rdir, name, k))]


def section(W, tag):
    rdir = "result_w%d_%s" % (W, tag)
    h = load(rdir, "H"); v = load(rdir, "V"); z = load(rdir, "Z", 0)
    j1, j2 = rows(W)
    i1, i2 = int(X1 / DX), int(X2 / DX)
    hrow = [sum(h[j - 1][i1:i2]) / (i2 - i1) for j in range(j1, j2 + 1)]
    vrow = [sum(v[j - 1][i1:i2]) / (i2 - i1) for j in range(j1, j2 + 1)]
    ws = [sum(h[j - 1][i] + z[j - 1][i] for j in range(j1, j2 + 1)) / W for i in range(i1, i2)]
    slope = (ws[0] - ws[-1]) / ((i2 - i1 - 1) * DX)
    qsum = sum(hr * vr for hr, vr in zip(hrow, vrow)) * DX
    return hrow, vrow, slope, qsum


ok = True
print("Manning: q = %.4f m2/s, h_n = %.3f m, V_n = %.3f m/s" % (Q_UNIT, HN, VN))
for W in (1, 5):
    for tag in ("off", "on"):
        hrow, vrow, slope, qsum = section(W, tag)
        g1 = abs(slope / S - 1.0) < TOL_SLOPE
        g2 = abs(qsum / (Q_UNIT * W) - 1.0) < TOL_Q
        print("(1) W=%d %-3s 水面勾配 %.5f (S = %.5f, ±%.0f%%) : %s" % (W, tag, slope, S, 100 * TOL_SLOPE, "PASS" if g1 else "FAIL"))
        print("(2) W=%d %-3s 断面流量 Σ V h dy / Q = %.5f (±%.0e) : %s" % (W, tag, qsum / (Q_UNIT * W), TOL_Q, "PASS" if g2 else "FAIL"))
        ok = ok and g1 and g2
        hr = max(abs(x / HN - 1.0) for x in hrow); vr = max(abs(x / VN - 1.0) for x in vrow)
        if tag == "on":
            g3 = hr < TOL_MAN and vr < TOL_MAN
            print("(3) W=%d on  Manning 一致: max|h/h_n − 1| = %.4f, max|V/V_n − 1| = %.4f (tol %.3f) : %s" % (W, hr, vr, TOL_MAN, "PASS" if g3 else "FAIL"))
            ok = ok and g3
        else:
            hm = sum(hrow) / len(hrow)
            if W == 1:
                g4 = hm / HN > 1.2
                print("(4) W=1 off 既知の性質: h/h_n = %.3f (> 1.2 = 壁に挟まれた 1 セル行の通水能不足) : %s" % (hm / HN, "PASS" if g4 else "FAIL"))
            else:
                ratio = vrow[0] / vrow[W // 2]
                g4 = ratio < 0.9
                print("(4) W=5 off 既知の性質: 河岸行/内部行の流速比 = %.3f (< 0.9), h/h_n = %.3f : %s" % (ratio, hm / HN, "PASS" if g4 else "FAIL"))
            ok = ok and g4
print("=== uniflow checks %s ===" % ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
