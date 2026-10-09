#!/usr/bin/env python3
"""nest_reflect の入力を生成する(ガウス型初期水位を各格子のセル中心で評価)。
   η(x,y) = a·exp(−((x−xc)² + (y−yc)²)/σ²), 静水深 h0 = 1 m。領域 100 m × 100 m、
   親 385×385(dx = 100/385)。子は親セル 160..226(67 セル)を覆い、比 3 → 201×201、
   比 5 → 335×335。一様細格子(基準)は 1155×1155(= 比 3 の解像度で全域)。
   使い方: python3 make_inputs.py
"""
import math, os
A, SIG, XC, YC, H0 = 0.2, 5.0, 50.0, 50.0, 1.0
NXP, LX = 385, 100.0
DXP = LX / NXP
I0 = 160          # 子セル (1,1) が整列する親セル
NP_FOOT = 67      # 子が覆う親セル数

def eta(x, y):
    return A * math.exp(-((x - XC) ** 2 + (y - YC) ** 2) / SIG ** 2)

def write(fn, nx, ny, x0, y0, dx):
    with open(fn, "w") as f:
        for j in range(1, ny + 1):
            y = y0 + (j - 0.5) * dx
            f.write(" ".join("%.17g" % (H0 + eta(x0 + (i - 0.5) * dx, y)) for i in range(1, nx + 1)) + "\n")
    print(fn, nx, ny, "dx=%.17g" % dx)

os.makedirs("data", exist_ok=True)
write("data/e_parent.txt", NXP, NXP, 0.0, 0.0, DXP)
for r in (3, 5):
    nxc = NP_FOOT * r
    write("data/e_child_r%d.txt" % r, nxc, nxc, (I0 - 1) * DXP, (I0 - 1) * DXP, DXP / r)
write("data/e_fine.txt", NXP * 3, NXP * 3, 0.0, 0.0, DXP / 3)
# 2 段: 孫(比 3 の子の中の比 3)。子セル 61..141(81 セル)を覆う 243×243
G0, NG_FOOT = 61, 81
write("data/e_grand.txt", NG_FOOT * 3, NG_FOOT * 3, (I0 - 1) * DXP + (G0 - 1) * DXP / 3, (I0 - 1) * DXP + (G0 - 1) * DXP / 3, DXP / 9)
