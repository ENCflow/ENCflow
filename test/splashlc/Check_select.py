#!/usr/bin/env python3
# splashlc: 曲率の相関長 spl_lc による谷の波長選択の検定(developer.md §48.3)
#   崖縁に 2 波長の正弦擾乱(λ1 = 4 m, λ2 = 20 m。make_terrain.py と対)を
#   与え、崖面帯の y 方向フーリエ振幅 A(λ) の成長比 A(final)/A(init) を比べる。
#   構成 g(spl_lc = 0、格子の κ): 最短波長が最速成長する(無限波数問題)ため
#     短波長 λ1 の成長比が長波長 λ2 の成長比を上回る。
#   構成 l(spl_lc = 2 m): 平滑化した κ は λ1 を見ない(ガウス核の伝達
#     exp(−ℓ²k²/2) = 0.007)ため λ1 はほぼ中立にとどまり、λ2(伝達 0.82)だけが
#     成長する(拡散項は使わないので短波長は減衰せず、成長しないだけ)。
# 検定:
#   (1) g: 成長比 λ1 > 成長比 λ2(短波長優勢)
#   (2) l: 成長比 λ2 >= 1.5(長波長が成長)、成長比 λ1 <= 1.5(短波長はほぼ中立)、
#          かつ λ2 の成長比が λ1 の 3 倍以上(長波長の選択)
#   (3) 両構成: 台地内部(x <= 12 m)は無傷(|Δz| < 0.05 m)
#   (4) 両構成: 侵食基準面 spl_zbase = 0 を下回らない(z >= 0)
import sys
import numpy as np

DX = 1.0
LAM1, LAM2 = 4.0, 20.0


def cliff_cols(z, hp=15.0):
    return [c for c in range(z.shape[1]) if 0.5 < z[:, c].mean() < hp - 0.5]


def amp(z, cols, lam):
    """崖面帯の列ごとの y 方向フーリエ振幅(波長 lam)の平均"""
    ny = z.shape[0]
    k = int(round(ny * DX / lam))
    a = []
    for c in cols:
        s = z[:, c] - z[:, c].mean()
        a.append(2.0 * abs(np.fft.rfft(s)[k]) / ny)
    return float(np.mean(a))


rc = 0


def check(name, ok, detail):
    global rc
    print("%s %s (%s)" % ("PASS:" if ok else "FAIL:", name, detail))
    if not ok:
        rc = 1


res = {}
for tag in ["g", "l"]:
    z0 = np.loadtxt("result_%s/Z0000.txt" % tag)
    z1 = np.loadtxt("result_%s/Z9998.txt" % tag)
    c0 = cliff_cols(z0); c1 = cliff_cols(z1)
    g1 = amp(z1, c1, LAM1) / amp(z0, c0, LAM1)
    g2 = amp(z1, c1, LAM2) / amp(z0, c0, LAM2)
    res[tag] = (g1, g2)
    print("config %s: growth of lambda = %g m: x%.2f, lambda = %g m: x%.2f" % (tag, LAM1, g1, LAM2, g2))
    dp = np.abs(z0[:, :12] - z1[:, :12]).max()
    check("plateau interior intact (%s)" % tag, dp < 0.05, "max|dz| = %.4f m" % dp)
    check("base level respected (%s)" % tag, z1.min() >= 0.0, "zmin = %.3f m" % z1.min())

g1, g2 = res["g"]
check("grid curvature: short wavelength grows faster", g1 > g2, "x%.2f > x%.2f" % (g1, g2))
g1, g2 = res["l"]
check("spl_lc = 2: long wavelength grows", g2 >= 1.5, "x%.2f >= 1.5" % g2)
check("spl_lc = 2: short wavelength stays near neutral", g1 <= 1.5, "x%.2f <= 1.5" % g1)
check("spl_lc = 2: long wavelength selected", g2 >= 3.0 * g1, "x%.2f >= 3 * x%.2f" % (g2, g1))
sys.exit(rc)
