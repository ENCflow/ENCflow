#!/usr/bin/env python3
# examples/confluence_backwater の補足 1: 同じ地区を Δx = 100 m の粗い格子で表す入力(data_coarse_<作り方>/ に書く。make が呼ぶ)
#   粗い格子の河道マスクは、本編の Δx = 20 m の河道マスク(make_terrain.py の本川のセル)を「高解像度の河道マスク」と
#   みなし、100 m のセルごとに本川が占める割合(占有率 f。20 m のセル 25 個のうち本川のセルの数)から機械的に作る
#   (作り方の系統的な比べは examples/coarse_channel)。作り方は 3 通り(METHODS):
#     simple  簡便: f ≥ 50 % のセルを本川の河道にする。幅は与えない(解像)。支川は中心線の 1 列(解像)
#     occ     占有率のまま: f ≥ 5 % のセルをすべて本川の河道にし、幅を f·Δ にする(f ≈ 1 は解像)。支川(幅 80 m。
#             セル幅より狭い)は中心線の 1 列にし、幅 80 m を与える
#     fixed   occ を直したもの: 格子の軸に沿う区間(中心線の傾きが AXIS_TOL 未満の列)で、列ごとに横断の占有率を足し、
#             中心線に近いセルから順に「解像したセル + 残りの幅のセル 1 つ」に詰め直す(狭窄部の 60 m × 2 → 100 m + 20 m)。
#             横に並んだ半端なセルは、斜めの辺でもつながって多めに流れるため(examples/coarse_channel の 5 節)
#   ほかは 3 通りとも同じ: 河道のセルの地盤は河床(本川の中心線の距離で決まる)、堤防は地形で表せないので河道の堤防
#   (仮想壁面。fn_bank、絶対標高 f_bank_datum = 2)で天端を与える、堤内地の地盤高は本編と同じ式(セルの中心)
#   z.txt, mask.txt, rw.txt, width.txt(simple にはない), bank.txt, rn.txt, h0.txt, h0_steady.txt, kind.txt,
#   occ.txt(本川の占有率)、cells_*.txt(本編と同じ流量・水位の時系列は data/ から写す)
#   python3 make_coarse.py            3 通りとも書く
#   python3 make_coarse.py fixed      1 つだけ書く
import os
import sys
import shutil
import math
import numpy as np
import make_terrain as m

DXC = 100.0
NXC, NYC = int(m.NX * m.DX / DXC), int(m.NY * m.DX / DXC)    # 60 × 74
LYC = NYC * DXC
RESOLVED = 9999.0                                            # 解像した河道の幅(セルより広い = 幅で絞らない)
METHODS = ("simple", "occ", "fixed")
FMIN = 0.05                                                  # これより小さい占有率のセルは河道にしない
AXIS_TOL = math.tan(math.radians(3.0))                       # 格子の軸に沿うとみなす中心線の傾き
_OCC = {}


def occupancy():
    """本編の 20 m の河道マスク(kind 1 = 本川)から、100 m のセルごとの本川の占有率。地形(湾曲の振幅・狭窄部の幅)ごとに
    1 回だけ数える(coarse_check/make_check.py が地形を変える)"""
    key = (m.AM, m.BC)
    if key not in _OCC:
        kind20 = m.build(m.QM_BASE, m.QT_BASE)[4]
        r = int(round(DXC / m.DX))
        _OCC[key] = (kind20 == 1).astype(float).reshape(NYC, r, NXC, r).mean(axis=(1, 3))
    return _OCC[key]


def main_widths(method, f, dn):
    """本川のセルの幅(0: 河道でない、RESOLVED: 解像、それ以外: サブグリッド河道の幅)。f は占有率、dn は中心線からの距離"""
    w = np.zeros_like(f)
    if method == "simple":
        w[f >= 0.5] = RESOLVED
        return w
    keep = f >= FMIN
    w[keep] = np.where(f[keep] >= 0.999, RESOLVED, f[keep] * DXC)
    if method == "occ":
        return w
    # fixed: 格子の軸に沿う列で、横断の占有率を中心線に近い順に解像 + 残り 1 つへ詰め直す
    for i in range(NXC):
        x = (i + 0.5) * DXC
        if abs(m.yc(x + 1.0) - m.yc(x - 1.0)) / 2.0 >= AXIS_TOL:
            continue
        rows = [j for j in range(NYC) if keep[j, i]]
        if not rows:
            continue
        total = float(f[rows, i].sum())
        # 中心線に近い順(同じ距離なら南のセル = 行の番号が大きい方から)
        rows.sort(key=lambda j: (round(abs(dn[j, i]), 6), -j))
        n = int(math.floor(total + 1e-9))
        rem = total - n
        for k, j in enumerate(rows):
            if k < n:
                w[j, i] = RESOLVED
            elif k == n and rem >= FMIN:
                w[j, i] = rem * DXC
            else:
                w[j, i] = 0.0
    return w


def build(method, qm0=m.QM_BASE, qt0=m.QT_BASE):
    f = occupancy()
    dn = np.zeros((NYC, NXC))
    ss = np.zeros((NYC, NXC))
    bb = np.zeros((NYC, NXC))
    for j in range(NYC):
        y = LYC - (j + 0.5) * DXC
        for i in range(NXC):
            dn[j, i], ss[j, i], xn = m.nearest((i + 0.5) * DXC, y)
            bb[j, i] = m.width(xn)
    wmain = main_widths(method, f, dn)
    z = np.full((NYC, NXC), -9999.0)
    rn = np.full((NYC, NXC), m.RNF)
    rw = np.zeros((NYC, NXC), dtype=int)
    width = np.zeros((NYC, NXC))
    bank = np.full((NYC, NXC), -9999.0)
    mask = np.zeros((NYC, NXC), dtype=int)
    h0 = np.zeros((NYC, NXC))
    kind = np.zeros((NYC, NXC), dtype=int)       # 1 本川、3 支川、5 堤内地
    for j in range(NYC):
        y = LYC - (j + 0.5) * DXC
        for i in range(NXC):
            x = (i + 0.5) * DXC
            if wmain[j, i] > 0.0:
                zm = m.ZM0 - m.SM * ss[j, i]
                kind[j, i] = 1
                z[j, i] = zm
                rn[j, i] = m.RNM
                width[j, i] = wmain[j, i]
                bank[j, i] = zm + m.LEV_M
                h0[j, i] = m.hn(qm0 / bb[j, i], m.RNM, m.SM)
                continue
            if dn[j, i] < 0:
                continue
            xw, xe = m.valley(y)
            # 支川(幅 80 m、中心 x = 2,600 m はセルの境目): 中心線の西側の列(中心 2,550 m)の 1 列
            if m.XT - DXC < x <= m.XT and dn[j, i] > bb[j, i] / 2:
                kind[j, i] = 3
                z[j, i] = m.zt(y)
                rn[j, i] = m.RNT
                width[j, i] = RESOLVED if method == "simple" else m.BT
                bank[j, i] = m.zt(y) + m.LEV_T
                h0[j, i] = m.hn(qt0 / m.BT, m.RNT, m.ST)
                continue
            if xw <= x <= xe:
                kind[j, i] = 5
                z[j, i] = m.zt(y) + m.FP_T + m.G_LAT * max(0.0, abs(x - m.XT) - m.BT / 2 - m.DX)
    rw[(kind == 1) | (kind == 3)] = 1
    mask[kind > 0] = 1
    if method == "simple":
        width[:] = 0.0                           # 幅は与えない(河道マスクだけ)
    return z, rn, rw, width, bank, mask, h0, kind, f


def write(method):
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, f"data_coarse_{method}")
    os.makedirs(out, exist_ok=True)
    z, rn, rw, width, bank, mask, h0, kind, f = build(method)
    for name, a, fmt in (("z", z, "%.3f"), ("rn", rn, "%.3f"), ("rw", rw, "%d"), ("width", width, "%.1f"),
                         ("bank", bank, "%.3f"), ("mask", mask, "%d"), ("h0", h0, "%.3f"), ("kind", kind, "%d"),
                         ("occ", f, "%.2f")):
        if name == "width" and method == "simple":
            continue                             # 簡便は幅を与えない(param の fn_width = '-')
        np.savetxt(os.path.join(out, f"{name}.txt"), a, fmt=fmt)
    np.savetxt(os.path.join(out, "h0_steady.txt"), build(method, m.QM_STEADY, m.QT_STEADY)[6], fmt="%.3f")
    with open(os.path.join(out, "cells_main.txt"), "w") as fo:
        fo.writelines(f"1 {j + 1}\n" for j in range(NYC) if kind[j, 0] == 1)
    with open(os.path.join(out, "cells_trib.txt"), "w") as fo:
        fo.writelines(f"{i + 1} 1\n" for i in range(NXC) if kind[0, i] == 3)
    with open(os.path.join(out, "cells_out.txt"), "w") as fo:
        fo.writelines(f"{NXC} {j + 1}\n" for j in range(NYC) if kind[j, NXC - 1] == 1)
    # 流量の時系列は本編と同じ。下流端の水位は、粗い格子の下流端のセルの河床で等流水深を足し直す
    src = os.path.join(here, "data")
    for fn in os.listdir(src):
        if fn.startswith("q_"):
            shutil.copy(os.path.join(src, fn), os.path.join(out, fn))
    zc_out = float(np.mean([z[j, NXC - 1] for j in range(NYC) if kind[j, NXC - 1] == 1]))
    zf_out = m.ZM0 - m.SM * float(np.interp((m.NX - 0.5) * m.DX, m.XS, m.SC))
    for fn in os.listdir(src):
        if fn.startswith("stage_"):
            a = np.loadtxt(os.path.join(src, fn))
            a[:, 1] += zc_out - zf_out
            np.savetxt(os.path.join(out, fn), a, fmt="%.1f %.3f")
    sub = int(((kind == 1) & (width > 0.0) & (width < RESOLVED)).sum())
    print(f"粗い格子 {method}: {NXC} × {NYC}、有効セル {int(mask.sum())}、本川のセル {int((kind == 1).sum())}"
          f"(うちサブグリッド河道 {sub})、支川のセル {int((kind == 3).sum())}")


def main():
    for method in (sys.argv[1:] or METHODS):
        if method not in METHODS:
            sys.exit(f"作り方は {', '.join(METHODS)} のどれか: {method}")
        write(method)


if __name__ == "__main__":
    main()
