#!/usr/bin/env python3
# splashslide: 固結/未固結の対照検定(developer.md §48)
#   構成1(param_c: f_splash のみ = 固結崖)では、崖縁の y 方向起伏
#   (谷の指標)が初期擾乱から成長する。
#   構成2(param_l: + f_debris/f_slide, c'=0 = 未固結崖)では、凹部が
#   安定判定 Fs<1 → 流動化 → 埋め戻しでリセットされ、起伏は成長しない
#   (白ママ型)。
# 検定:
#   (1) 固結:   relief(final)/relief(init) >= 1.25(谷の成長)
#   (2) 未固結: relief(final)/relief(init) <= 0.9(谷が維持されない)
#   (3) 両構成: 台地内部(x <= 6)は無傷(|Δz| < 0.05 m)
#   (4) 両構成: 侵食の下限が有界(z >= -1.5。sd0=1.3 + creep の岩盤
#       ドリフト分。creep は sd に触れない仕様のため z−sd は厳密不変で
#       ない — m_geomorph ヘッダの既知の妥協)
import sys
import numpy as np

def relief(z):
    """崖面帯(列平均標高が台地と平地の間)の y 方向起伏の平均"""
    cols = [c for c in range(z.shape[1]) if 0.5 < z[:, c].mean() < 8.5]
    assert cols, "no cliff-zone columns found"
    return float(np.mean([z[:, c].std() for c in cols]))

rc = 0
def check(name, ok, detail):
    global rc
    print("%s %s (%s)" % ("PASS:" if ok else "FAIL:", name, detail))
    if not ok:
        rc = 1

zc0 = np.loadtxt("result_c/Z0000.txt"); zc1 = np.loadtxt("result_c/Z9998.txt")
zl0 = np.loadtxt("result_l/Z0000.txt"); zl1 = np.loadtxt("result_l/Z9998.txt")

gc = relief(zc1) / relief(zc0)
gl = relief(zl1) / relief(zl0)
check("coherent cliff: relief grows", gc >= 1.25, "x%.2f >= 1.25" % gc)
check("loose cliff: relief does not grow", gl <= 0.9, "x%.2f <= 0.9" % gl)

dpc = np.abs(zc0[:, :6] - zc1[:, :6]).max()
dpl = np.abs(zl0[:, :6] - zl1[:, :6]).max()
check("plateau interior intact (coherent)", dpc < 0.05, "max|dz| = %.4f m" % dpc)
check("plateau interior intact (loose)", dpl < 0.05, "max|dz| = %.4f m" % dpl)

check("erosion bounded (coherent, incl. creep bedrock drift)", zc1.min() >= -1.5,
      "zmin = %.2f" % zc1.min())
check("erosion bounded (loose, incl. creep bedrock drift)", zl1.min() >= -1.5,
      "zmin = %.2f" % zl1.min())

sys.exit(rc)
