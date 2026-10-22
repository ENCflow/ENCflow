#!/usr/bin/env python3
"""メサ・ビュート実験の地形(z.txt): 平地(z = 0 = 基準面)に高さ 20 m の台地を 2 つ置く。
台地の縁は急崖(tanθ = 2 ≈ 63°)で、縁の位置に白色雑音(±0.5 m、シード固定)を与える。
  大: 半径 30 m(メサ)、小: 半径 12 m(ビュート候補)。領域 200 × 100 m、Δx = 1 m。"""
import numpy as np
LX, LY, DX, HP, TANB = 200.0, 100.0, 1.0, 20.0, 2.0
PLATEAUS = [(60.0, 50.0, 30.0), (150.0, 50.0, 12.0)]   # (xc, yc, 半径)
rng = np.random.default_rng(20261022)
nx, ny = int(LX / DX), int(LY / DX)
x = (np.arange(nx) + 0.5) * DX
y = (np.arange(ny) + 0.5) * DX
X, Y = np.meshgrid(x, y)
z = np.zeros((ny, nx))
for xc, yc, R in PLATEAUS:
    r = np.hypot(X - xc, Y - yc)
    th = np.arctan2(Y - yc, X - xc)
    # 縁の半径に方位の白色雑音(1° 刻み)を与える
    nb = rng.uniform(-0.5, 0.5, 360)
    Re = R + nb[((np.degrees(th) + 360) % 360).astype(int)]
    z = np.maximum(z, np.clip(HP - TANB * (r - Re), 0.0, HP))
np.savetxt("z.txt", z, fmt="%.6f")
print("z.txt: %d x %d, plateau cells (z >= 19 m) = %d" % (nx, ny, int((z >= 19).sum())))
