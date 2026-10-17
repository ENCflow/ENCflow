#!/usr/bin/env python3
# examples/meander_cutoff の入力生成: 頸部の狭い蛇行(正弦波生成曲線)
#   (生成に 10 秒ほどかかる: 各セルから中心線への最近接距離を総当たりで求める)
#   中心線の方向角 θ(s) = ω sin(2π s/Λ)(Langbein-Leopold の sine-generated curve。
#   ω が大きいほど蛇行度が高く、隣り合うループの間の頸部が狭くなる)。
#   河岸(氾濫原)は河床 + BANK、頸部(2 つの河道区間の両方に近い陸)は河床 +
#   BANKNECK(低い。出水で越流し短絡の種になる)。
#   z.txt / h.txt / sd.txt、rows(西端の流入セル)、dims
import sys, math

W, LAM, OMEGA = 20.0, 320.0, 105.0        # 幅、曲線の弧長波長、最大方向角 (deg)
NLOOP = 2.0                                # 波長の数
S0, Z0, BANK, BANKNECK, H0, SD = 0.001, 10.0, 1.6, 0.95, 0.8, 5.0
NECKW = 8.0                                # 頸部とみなす「河岸からの距離」(m)
LIN, LOUT = 60.0, 80.0                     # 入口・出口の直線長
DX = 2.0
MARGIN = 30.0
XFIX_UP, XFIX_DN, LRAMP = 30.0, 30.0, 150.0
DS = 0.5

# --- 中心線(弧長 s で積分) ---
om = math.radians(OMEGA)
LCURVE = NLOOP * LAM
pts = []   # (s, x, y, loop index)
x, y, s = 0.0, 0.0, 0.0
while s <= LIN + LCURVE + LOUT:
    if s < LIN or s > LIN + LCURVE:
        th = 0.0
    else:
        th = om * math.sin(2 * math.pi * (s - LIN) / LAM)
    pts.append((s, x, y, int((s - LIN) // (LAM / 2)) if LIN <= s <= LIN + LCURVE else -1))
    x += DS * math.cos(th); y += DS * math.sin(th); s += DS
xs = [p[1] for p in pts]; ys = [p[2] for p in pts]
XMIN, XMAX = 0.0, max(xs)
YMIN, YMAX = min(ys) - MARGIN - W / 2, max(ys) + MARGIN + W / 2
NX = int(math.ceil((XMAX - XMIN) / DX)); NY = int(math.ceil((YMAX - YMIN) / DX))

import bisect
# 半ループ(index)ごとの最近接距離を求めるために index で分ける
from collections import defaultdict
seg = defaultdict(list)
for p in pts:
    seg[p[3]].append(p)

def nearest(xc, yc):
    """全体の最近接 (s, 符号付き n) と、半ループごとの最近接距離の辞書"""
    best = (1e9, None, None); per = {}
    for idx, lst in seg.items():
        bd, bp = 1e9, None
        for p in lst:
            d = math.hypot(xc - p[1], yc - p[2])
            if d < bd: bd, bp = d, p
        per[idx] = bd
        if bd < best[0]: best = (bd, bp, idx)
    d, p, idx = best
    # 符号付き横距離(左が正): 接線方向との外積
    k = min(len(pts) - 2, max(0, int(p[0] / DS)))
    tx, ty = pts[k + 1][1] - pts[k][1], pts[k + 1][2] - pts[k][2]
    n = ((xc - p[1]) * ty - (yc - p[2]) * tx) / math.hypot(tx, ty)
    return p[0], -n if d > 0 else 0.0, d, per

def cellxy(i, j):
    return XMIN + (i - 0.5) * DX, YMIN + (j - 0.5) * DX

CACHE = {}
def info(i, j):
    if (i, j) not in CACHE:
        xc, yc = cellxy(i, j)
        CACHE[(i, j)] = nearest(xc, yc)
    return CACHE[(i, j)]

def in_channel(i, j):
    return info(i, j)[2] <= W / 2

# 氾濫原の高さ: 近く(半径 RFP)にある河道の河床の最大値 + BANK(どの隣接区間の
# 水面より上にする。路長や谷勾配で決めると蛇行度の高い所で上流の水面より低くなり
# 出水前から溢れる — 実検出)。頸部(2 つ以上の半ループに近い陸)は + BANKNECK
RFP = 24.0
import numpy as _np
_ZB = None
def _bed_field():
    global _ZB
    if _ZB is None:
        zb = _np.full((NY, NX), -1e9)
        for j in range(1, NY + 1):
            for i in range(1, NX + 1):
                sc, nc, dc, perc = info(i, j)
                if dc <= W / 2:
                    zb[j - 1, i - 1] = Z0 - S0 * sc
        r = int(RFP / DX)
        mx = zb.copy()
        for dj in range(-r, r + 1):
            for di in range(-r, r + 1):
                if di * di + dj * dj > r * r: continue
                mx = _np.maximum(mx, _np.roll(_np.roll(zb, dj, 0), di, 1))
        _ZB = mx
    return _ZB

def z_of(i, j):
    s, n, d, per = info(i, j)
    if d <= W / 2:
        return Z0 - S0 * s
    zfp = _bed_field()[j - 1, i - 1]
    if zfp < -1e8:
        zfp = Z0 - S0 * s
    near = sorted(v for v in per.values())
    neck = len(near) >= 2 and near[1] <= W / 2 + NECKW
    return zfp + (BANKNECK if neck else BANK)

def h_of(i, j):
    return H0 if in_channel(i, j) else 0.0

def sd_of(i, j):
    xc, yc = cellxy(i, j)
    xl = xc - XMIN
    if xl > NX * DX - XFIX_DN: return 0.0
    return SD * min(1.0, max(0.0, (xl - XFIX_UP) / LRAMP))

if __name__ == "__main__":
    kind = sys.argv[1]
    if kind == "dims":
        print(NX, NY, "%.1f %.1f" % (NX * DX, NY * DX)); sys.exit(0)
    if kind == "rows":
        # 最初に河道があるxの列(西側余白の次)と、その列の河道の行
        i0 = next(i for i in range(1, NX + 1) if any(in_channel(i, j) for j in range(1, NY + 1)))
        print(i0, " ".join(str(j) for j in range(1, NY + 1) if in_channel(i0, j))); sys.exit(0)
    fn = {"z": z_of, "h": h_of, "sd": sd_of}[kind]
    for j in range(1, NY + 1):
        print(" ".join("%.4f" % fn(i, j) for i in range(1, NX + 1)))
