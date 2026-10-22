#!/usr/bin/env python3
# wave_river 検定の入力: 西の陸地を貫く河道(幅 10 m、河床 −1.2 m)が東の海(海浜勾配 0.02、
#   沖は水深 2 m)に出る。河道の水深 1.2 m は砕波水深 h_b/γ = 0.86 m より深い = 河道は
#   「波の源」の候補。河道の途中に早瀬(x = XR1〜XR2、河床 ZR = −0.5 m、水深 ≈ 0.6 m < h_b/γ)
#   を置く: 規則 wave_vmax が無いと下流の淵が源になって早瀬が砕波帯と判定され、沿岸漂砂が
#   河道内で働く(examples/delta で発散した機構の最小再現)。
#   土層: 河道内 1 m(可動)、陸地と海底は 0(非侵食。堆積は可)。
#   python3 make_init.py z > zinit.txt / sd > sdinit.txt
import sys
import numpy as np
NX, NY, DX = 120, 80, 2.5          # 300 m x 200 m
XL, ZLAND = 100.0, 1.5              # 陸地の東端 x (m)、陸地の高さ (m)
ZCH, WCH, SDCH = -1.2, 10.0, 1.0    # 河道の河床高 (m)、幅 (m)、土層 (m)
Z0, S, ZSEA = 0.2, 0.02, 2.0        # 汀線の水深 (m)、海浜勾配、沖の水深 (m)
JC1, JC2 = 38, 42                   # 河道の行(0 始まり。JC1 <= j < JC2 = 4 行 = 10 m)
XR1, XR2, ZR = 40.0, 60.0, -0.5     # 早瀬の区間 (m) と河床高 (m)

def fields():
    x = (np.arange(NX) + 0.5) * DX
    y = (np.arange(NY) + 0.5) * DX
    X, Y = np.meshgrid(x, y)
    z = np.where(X < XL, ZLAND, -np.minimum(Z0 + S * (X - XL), ZSEA))
    sd = np.zeros_like(z)
    inch = (np.arange(NY)[:, None] >= JC1) & (np.arange(NY)[:, None] < JC2) & (z > ZCH)
    z = np.where(inch, ZCH, z)
    z = np.where(inch & (X >= XR1) & (X < XR2), ZR, z)
    sd = np.where(inch, SDCH, 0.0)
    return z, sd

if __name__ == "__main__":
    z, sd = fields()
    np.savetxt(sys.stdout, {"z": z, "sd": sd}[sys.argv[1]], fmt="%.4f")
