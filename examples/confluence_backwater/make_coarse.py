#!/usr/bin/env python3
# examples/confluence_backwater の補足: 同じ地区を Δx = 100 m の粗い格子で表す入力(data_coarse/ に書く。make が呼ぶ)
#   本編(make_terrain.py)と同じ地形の式を 100 m のセルの中心で評価する。流域規模の計算での表し方:
#   - 本川(幅 200 m)は 2 セル前後の解像した河道、狭窄部(幅 100 m)は 1 セル。河道マスク fn_rw に入れ、幅は 9999(解像扱い)
#   - 支川(幅 80 m)は 1 セルのサブグリッド河道(幅 80 m。fn_width)
#   - 堤防は地形で表せないので、河道の堤防(仮想壁面。fn_bank、絶対標高 f_bank_datum = 2)で天端を与える
#   - 堤内地の地盤高は本編と同じ式(セルの中心)
#   z.txt, mask.txt, rw.txt, width.txt, bank.txt, rn.txt, h0.txt, cells_*.txt(本編と同じ流量・水位の時系列は data/ から写す)
import os
import shutil
import math
import numpy as np
import make_terrain as m

DXC = 100.0
NXC, NYC = int(m.NX * m.DX / DXC), int(m.NY * m.DX / DXC)    # 60 × 74
LYC = NYC * DXC


def build(qm0=m.QM_BASE, qt0=m.QT_BASE, margin=0.0):
    z = np.full((NYC, NXC), -9999.0)
    rn = np.full((NYC, NXC), m.RNF)
    rw = np.zeros((NYC, NXC), dtype=int)
    width = np.zeros((NYC, NXC))
    bank = np.full((NYC, NXC), -9999.0)
    mask = np.zeros((NYC, NXC), dtype=int)
    h0 = np.zeros((NYC, NXC))
    kind = np.zeros((NYC, NXC), dtype=int)       # 1 本川、3 支川、5 堤内地
    for j in range(1, NYC + 1):
        y = LYC - (j - 0.5) * DXC
        for i in range(1, NXC + 1):
            x = (i - 0.5) * DXC
            dn, s, xn = m.nearest(x, y)
            b = m.width(xn)
            zm = m.ZM0 - m.SM * s
            # 本川の中心線(直線区間 y = 700 m)は粗い格子のセルの境目にあるので、幅 200 m は 2 セルになる。
            # 幅がセル以下の狭窄部(100 m)は南側の 1 セルにする(中心線から両側 50 m のセルを両方取ると 200 m になる)
            if (b > DXC and abs(dn) <= b / 2 + margin) or (b <= DXC and -DXC < dn <= 0.0):
                kind[j-1, i-1] = 1
                z[j-1, i-1] = zm
                rn[j-1, i-1] = m.RNM
                bank[j-1, i-1] = zm + m.LEV_M
                h0[j-1, i-1] = m.hn(qm0 / b, m.RNM, m.SM)
                continue
            if dn < 0:
                continue
            xw, xe = m.valley(y)
            if m.XT - DXC < x <= m.XT and dn > b / 2:   # 支川の中心 x = 2,600 m を含む西側の列(中心 2,550 m)
                kind[j-1, i-1] = 3
                z[j-1, i-1] = m.zt(y)
                rn[j-1, i-1] = m.RNT
                bank[j-1, i-1] = m.zt(y) + m.LEV_T
                h0[j-1, i-1] = m.hn(qt0 / m.BT, m.RNT, m.ST)
                continue
            if xw <= x <= xe:
                kind[j-1, i-1] = 5
                z[j-1, i-1] = m.zt(y) + m.FP_T + m.G_LAT * max(0.0, abs(x - m.XT) - m.BT / 2 - m.DX)
    rw[(kind == 1) | (kind == 3)] = 1
    width[kind == 1] = 9999.0
    width[kind == 3] = m.BT
    mask[kind > 0] = 1
    return z, rn, rw, width, bank, mask, h0, kind


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "data_coarse")
    os.makedirs(out, exist_ok=True)
    z, rn, rw, width, bank, mask, h0, kind = build()
    for name, a, fmt in (("z", z, "%.3f"), ("rn", rn, "%.3f"), ("rw", rw, "%d"), ("width", width, "%.1f"),
                         ("bank", bank, "%.3f"), ("mask", mask, "%d"), ("h0", h0, "%.3f"), ("kind", kind, "%d")):
        np.savetxt(os.path.join(out, f"{name}.txt"), a, fmt=fmt)
    np.savetxt(os.path.join(out, "h0_steady.txt"), build(m.QM_STEADY, m.QT_STEADY)[6], fmt="%.3f")
    with open(os.path.join(out, "cells_main.txt"), "w") as f:
        for j in range(1, NYC + 1):
            if kind[j-1, 0] == 1:
                f.write(f"1 {j}\n")
    with open(os.path.join(out, "cells_trib.txt"), "w") as f:
        for i in range(1, NXC + 1):
            if kind[0, i-1] == 3:
                f.write(f"{i} 1\n")
    with open(os.path.join(out, "cells_out.txt"), "w") as f:
        for j in range(1, NYC + 1):
            if kind[j-1, NXC-1] == 1:
                f.write(f"{NXC} {j}\n")
    # 流量の時系列は本編と同じ。下流端の水位は、粗い格子の下流端のセルの河床で等流水深を足し直す
    src = os.path.join(here, "data")
    for fn in os.listdir(src):
        if fn.startswith("q_"):
            shutil.copy(os.path.join(src, fn), os.path.join(out, fn))
    zc_out = float(np.mean([z[j-1, NXC-1] for j in range(1, NYC + 1) if kind[j-1, NXC-1] == 1]))
    zf_out = m.ZM0 - m.SM * float(np.interp((m.NX - 0.5) * m.DX, m.XS, m.SC))
    for fn in os.listdir(src):
        if fn.startswith("stage_"):
            a = np.loadtxt(os.path.join(src, fn))
            a[:, 1] += zc_out - zf_out
            np.savetxt(os.path.join(out, fn), a, fmt="%.1f %.3f")
    print(f"粗い格子 {NXC} × {NYC}、有効セル {int(mask.sum())}、本川のセル {int((kind == 1).sum())}、支川のセル {int((kind == 3).sum())}")


if __name__ == "__main__":
    main()
