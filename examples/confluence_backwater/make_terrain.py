#!/usr/bin/env python3
# examples/confluence_backwater の本編の入力生成(data/ に書く。make が呼ぶ)
#   地形: 北から南へ流れる支川が、西から東へ流れる本川の湾曲部の外岸(北岸)に直角に合流する谷底平野。
#   本川は合流点の 1.6 km 下流に狭窄部(幅 200 m → 120 m)があり、洪水時は合流点の水位が上がる。
#   支川は勾配が緩く、堤防が本川より低い。支川の両岸は丘陵に囲まれた低地(堤内地)。
#   Δx = 20 m、300 列 × 370 行(6.0 km × 7.4 km)。丘陵は領域マスクの外(計算しない)。
#   z.txt          地盤高(河道・堤防・堤内地)
#   z_raise.txt    対策 A: 背水区間の支川の堤防を本川の堤防の天端の高さまでかさ上げした地盤高
#   z_gate.txt     対策 B: 支川の口を本川の堤防の天端の高さの締切で閉じた地盤高(水門のカルバートとポンプは param)
#   mask.txt       領域マスク(1: 計算する)
#   rn.txt         粗度(本川 0.03、支川 0.035、堤防・堤内地 0.05)
#   h0.txt         初期水深(本川 300 m3/s・支川 20 m3/s の等流水深)
#   cells_*.txt    区間流入・水位規定のセル(各行 "i j")
#   q_*.txt        流量・水位の時系列(各行 "時刻(min) 値")
import os
import math
import numpy as np

DX = 20.0
NX, NY = 300, 370
LY = NY * DX
# 本川(中心線の y は直線区間 YS、湾曲は頂点 XJ で北へ 2 AM 膨らむ余弦の形 = 頂点の曲率半径 LAM²/(4π² AM) ≈ 430 m)
YS, XJ, AM, LAM = 700.0, 2600.0, 150.0, 1600.0
BM, SM, ZM0, RNM = 200.0, 1.0 / 1500.0, 20.0, 0.03
LEV_M = 8.5                                  # 本川の堤防の天端 = 河床 + 8.5 m
XC1, XC2, LTR, BC = 4200.0, 4800.0, 200.0, 120.0   # 狭窄部(幅 BC の区間と前後の遷移の長さ)
# 支川(列 129〜132 = x 2,560〜2,640 m。中心 XT = XJ)
XT, BT, ST, RNT = XJ, 80.0, 1.0 / 1000.0, 0.035
D_STEP = 1.0                                 # 支川の口の河床 = 本川の河床 + 1 m
LEV_T, FP_T = 4.5, 2.5                       # 支川の堤防の天端 = 河床 + 4.5 m、堤内地 = 支川の河床 + 2.5 m
RNF = 0.05
# 堤内地の谷(西端・東端の x は北へ細くなる)
XFW0, XFE0, XFW1, XFE1 = 1400.0, 3800.0, 2100.0, 3100.0
G_LAT = 1.0 / 1000.0                         # 谷の縁へ向かう地盤の上がり
# 対策 A: 背水区間(合流点から、支川の元の堤防の天端が本川の堤防の天端に届くまで)の支川の堤防をかさ上げ
L_RAISE = 3000.0
# 流量
QM_BASE, QM_PEAK = 300.0, 2800.0
QT_BASE, QT_PEAK = 20.0, 300.0
QM_STEADY, QT_STEADY = 1500.0, 100.0         # 補足: 背水曲線を 1 次元の理論と比べる定常の流量(支川はあふれない)


def yc(x):
    """本川の中心線の y"""
    if abs(x - XJ) <= LAM / 2:
        return YS + AM * (1.0 + math.cos(2.0 * math.pi * (x - XJ) / LAM))
    return YS


def width(x):
    """本川の幅(狭窄部で BC)"""
    if XC1 <= x <= XC2:
        return BC
    if XC1 - LTR < x < XC1:
        return BM + (BC - BM) * (x - (XC1 - LTR)) / LTR
    if XC2 < x < XC2 + LTR:
        return BC + (BM - BC) * (x - XC2) / LTR
    return BM


def centerline():
    xs = np.arange(-200.0, NX * DX + 200.0, 1.0)
    ys = np.array([yc(x) for x in xs])
    ds = np.hypot(np.diff(xs), np.diff(ys))
    s = np.concatenate([[0.0], np.cumsum(ds)])
    s -= np.interp(0.0, xs, s)                 # 西端 x = 0 で s = 0
    return xs, ys, s


def geometry():
    """中心線と、それで決まる合流点の諸量(湾曲の振幅 AM を変えたら呼び直す。coarse_check/make_check.py が使う)"""
    global XS, YSC, SC, S_J, ZMJ, Y_MOUTH, ZTJ
    XS, YSC, SC = centerline()
    S_J = float(np.interp(XJ, XS, SC))         # 合流点の本川の中心線の距離
    ZMJ = ZM0 - SM * S_J                       # 合流点の本川の河床
    Y_MOUTH = yc(XJ) + BM / 2                  # 支川の口(本川の北岸)の y
    ZTJ = ZMJ + D_STEP                         # 支川の口の河床


geometry()


def zt(y):
    return ZTJ + ST * (y - Y_MOUTH)


def nearest(x, y):
    """本川の中心線への最近点の (距離の符号付き値 = 北が正, s, x)"""
    k0 = int(np.searchsorted(XS, x))
    lo, hi = max(k0 - 400, 0), min(k0 + 400, len(XS))
    d2 = (XS[lo:hi] - x) ** 2 + (YSC[lo:hi] - y) ** 2
    k = lo + int(np.argmin(d2))
    d = math.sqrt(d2[k - lo])
    # 北側か南側か: 中心線の法線(左 = 北)との内積
    if 0 < k < len(XS) - 1:
        tx, ty = XS[k + 1] - XS[k - 1], YSC[k + 1] - YSC[k - 1]
    else:
        tx, ty = 1.0, 0.0
    side = 1.0 if (-ty * (x - XS[k]) + tx * (y - YSC[k])) >= 0 else -1.0
    return side * d, SC[k], XS[k]


def valley(y):
    f = min(max((y - Y_MOUTH) / (LY - Y_MOUTH), 0.0), 1.0)
    return XFW0 + (XFW1 - XFW0) * f, XFE0 + (XFE1 - XFE0) * f


def hn(q, n, s):
    return (n * q / math.sqrt(s)) ** 0.6


def build(qm0=QM_BASE, qt0=QT_BASE):
    z = np.full((NY, NX), -9999.0)
    rn = np.full((NY, NX), RNF)
    mask = np.zeros((NY, NX), dtype=int)
    h0 = np.zeros((NY, NX))
    kind = np.zeros((NY, NX), dtype=int)       # 1 本川、2 本川の北の堤防、3 支川、4 支川の堤防、5 堤内地
    for j in range(1, NY + 1):
        y = LY - (j - 0.5) * DX
        for i in range(1, NX + 1):
            x = (i - 0.5) * DX
            dn, s, xn = nearest(x, y)
            b = width(xn)
            zm = ZM0 - SM * s
            # 河道は中心線から南へ b/2 未満・北へ b/2 以下のセル。直線区間の中心線(y = 700 m)はセルの境目にあるので、
            # 両側の端を含めると端のセルを 2 つ取りすぎる(幅 100 m が 6 セル = 120 m になる)
            if -b / 2 < dn <= b / 2:
                kind[j-1, i-1] = 1
                z[j-1, i-1] = zm
                rn[j-1, i-1] = RNM
                h0[j-1, i-1] = hn(qm0 / b, RNM, SM)
                continue
            if dn < 0:
                continue                        # 本川の南: 丘陵(計算しない)
            xw, xe = valley(y)
            in_valley = xw <= x <= xe
            if abs(x - XT) < BT / 2 and dn > b / 2:
                kind[j-1, i-1] = 3
                z[j-1, i-1] = zt(y)
                rn[j-1, i-1] = RNT
                h0[j-1, i-1] = hn(qt0 / BT, RNT, ST)
                continue
            if dn <= b / 2 + DX:
                if in_valley or abs(x - XT) < BT / 2 + DX:
                    kind[j-1, i-1] = 2
                    z[j-1, i-1] = zm + LEV_M
                continue
            if abs(x - XT) < BT / 2 + DX:
                kind[j-1, i-1] = 4
                z[j-1, i-1] = zt(y) + LEV_T
                continue
            if in_valley:
                kind[j-1, i-1] = 5
                z[j-1, i-1] = zt(y) + FP_T + G_LAT * max(0.0, abs(x - XT) - BT / 2 - DX)
    # 河道(本川・支川)のセルと 8 近傍で接する堤内地のセルは堤防にする(斜めのリンクで堤防を素通りさせない)
    for j in range(NY):
        for i in range(NX):
            if kind[j, i] != 5:
                continue
            nb = kind[max(j-1, 0):j+2, max(i-1, 0):i+2]
            if (nb == 1).any():
                x = (i + 0.5) * DX; y = LY - (j + 0.5) * DX
                dn, s, xn = nearest(x, y)
                kind[j, i] = 2
                z[j, i] = ZM0 - SM * s + LEV_M
            elif (nb == 3).any():
                y = LY - (j + 0.5) * DX
                kind[j, i] = 4
                z[j, i] = zt(y) + LEV_T
    mask[kind > 0] = 1
    return z, rn, mask, h0, kind


def wtxt(path, a, fmt):
    np.savetxt(path, a, fmt=fmt)


def series(path, pts):
    with open(path, "w") as f:
        for t, v in pts:
            f.write(f"{t:.1f} {v:.3f}\n")


def hydro_main():
    # 1 h は平水(初期の調整)、1 → 6 h で ピーク、8 h まで続き、13 h で平水に戻る
    return [(0, QM_BASE), (60, QM_BASE), (360, QM_PEAK), (480, QM_PEAK), (780, QM_BASE), (1440, QM_BASE)]


def hydro_trib(tpeak_h):
    # 平水 20 m3/s。ピークの 2 h 前から上がり、3 h かけて戻る
    tp = tpeak_h * 60.0
    return [(0, QT_BASE), (tp - 120, QT_BASE), (tp, QT_PEAK), (tp + 180, QT_BASE), (1440, QT_BASE)]


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "data")
    os.makedirs(out, exist_ok=True)
    z, rn, mask, h0, kind = build()
    wtxt(os.path.join(out, "z.txt"), z, "%.3f")
    wtxt(os.path.join(out, "rn.txt"), rn, "%.3f")
    wtxt(os.path.join(out, "mask.txt"), mask, "%d")
    wtxt(os.path.join(out, "h0.txt"), h0, "%.3f")
    wtxt(os.path.join(out, "kind.txt"), kind, "%d")
    crest_m = ZMJ + LEV_M                       # 合流点の本川の堤防の天端
    # 対策 A: 背水区間の支川の堤防を、合流点の本川の堤防の天端の高さ(水平)までかさ上げする
    zr = z.copy()
    for j in range(NY):
        y = LY - (j + 0.5) * DX
        for i in range(NX):
            if kind[j, i] == 4 and y - Y_MOUTH <= L_RAISE:
                zr[j, i] = max(zr[j, i], crest_m)
    wtxt(os.path.join(out, "z_raise.txt"), zr, "%.3f")
    # 対策 B: 支川の口の 1 行(本川に接する支川のセル)を本川の堤防の天端の高さの締切で閉じる
    zg = z.copy()
    jt = [j for j in range(NY) if (kind[j] == 3).any()]
    j_close = max(jt)                            # 支川の最も南の行(0 始まり)
    cols = [i for i in range(NX) if kind[j_close, i] == 3]
    for i in cols:
        zg[j_close, i] = crest_m
    wtxt(os.path.join(out, "z_gate.txt"), zg, "%.3f")
    with open(os.path.join(out, "gate_cells.txt"), "w") as f:
        f.write("# 締切の行・支川の列(1 始まり)・内側の河床・外側の本川の河床\n")
        for i in cols:
            f.write(f"{j_close + 1} {i + 1} {z[j_close - 1, i]:.3f} {z[j_close + 1, i]:.3f}\n")
    # 区間流入: 本川(西辺の本川のセル)、支川(北辺の支川のセル)。水位規定: 東辺の本川のセル
    with open(os.path.join(out, "cells_main.txt"), "w") as f:
        for j in range(1, NY + 1):
            if kind[j-1, 0] == 1:
                f.write(f"1 {j}\n")
    with open(os.path.join(out, "cells_trib.txt"), "w") as f:
        for i in range(1, NX + 1):
            if kind[0, i-1] == 3:
                f.write(f"{i} 1\n")
    with open(os.path.join(out, "cells_out.txt"), "w") as f:
        for j in range(1, NY + 1):
            if kind[j-1, NX-1] == 1:
                f.write(f"{NX} {j}\n")
    # 下流端の水位: 本川と支川の流入の和の等流水深(幅 BM・粗度 RNM・勾配 SM。2 次元計算なので R = h)
    z_out = ZM0 - SM * float(np.interp((NX - 0.5) * DX, XS, SC))
    for name, qm, qt in (("steady", [(0, QM_STEADY), (1440, QM_STEADY)], [(0, QT_STEADY), (1440, QT_STEADY)]),
                         ("flood_base", hydro_main(), [(0, QT_BASE), (1440, QT_BASE)]),
                         ("base_base", [(0, QM_BASE), (1440, QM_BASE)], [(0, QT_BASE), (1440, QT_BASE)]),
                         ("base_same", [(0, QM_BASE), (1440, QM_BASE)], hydro_trib(7.0)),
                         ("flood_early", hydro_main(), hydro_trib(4.0)),
                         ("flood_same", hydro_main(), hydro_trib(7.0))):
        ts = sorted({t for t, v in qm} | {t for t, v in qt} | set(range(0, 1441, 15)))
        pts = []
        for t in ts:
            q = np.interp(t, [a for a, b in qm], [b for a, b in qm]) + np.interp(t, [a for a, b in qt], [b for a, b in qt])
            pts.append((t, z_out + hn(q / BM, RNM, SM)))
        series(os.path.join(out, f"stage_{name}.txt"), pts)
    series(os.path.join(out, "q_main_flood.txt"), hydro_main())
    series(os.path.join(out, "q_main_steady.txt"), [(0, QM_STEADY), (1440, QM_STEADY)])
    series(os.path.join(out, "q_trib_steady.txt"), [(0, QT_STEADY), (1440, QT_STEADY)])
    h0s = build(QM_STEADY, QT_STEADY)[3]
    wtxt(os.path.join(out, "h0_steady.txt"), h0s, "%.3f")
    series(os.path.join(out, "q_main_base.txt"), [(0, QM_BASE), (1440, QM_BASE)])
    series(os.path.join(out, "q_trib_base.txt"), [(0, QT_BASE), (1440, QT_BASE)])
    series(os.path.join(out, "q_trib_early.txt"), hydro_trib(4.0))
    series(os.path.join(out, "q_trib_same.txt"), hydro_trib(7.0))
    print(f"合流点の本川の河床 {ZMJ:.3f} m、支川の口の河床 {ZTJ:.3f} m(y = {Y_MOUTH:.0f} m)、"
          f"有効セル {int(mask.sum())}")


if __name__ == "__main__":
    main()
