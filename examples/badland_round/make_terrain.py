#!/usr/bin/env python3
"""丸い峰のバッドランド実験用の地形を生成する(z.txt)。

平地(z = 0 = 侵食基準面)の上に、大きさの異なる 4 つの円錐丘を一列に置く。
側面の勾配は共通 tanθ = 0.8(≈ 39°)、高さ H = 24 / 15 / 9 / 5 m
(底面半径 30 / 18.75 / 11.25 / 6.25 m)。丘の上にだけ白色雑音(一様 ±0.4 m、
シード固定)を与え、リルの種にする(特定の波長を持ち込まない)。
  python3 make_terrain.py        # z.txt(176 × 80 m、Δx = 1 m)
"""
import numpy as np

LX, LY, DX = 176.0, 80.0, 1.0
TANB = 0.8
HILLS = [(35.0, 24.0), (90.0, 15.0), (128.0, 9.0), (154.0, 5.0)]   # (中心 x, 高さ H)
YC = LY / 2
ANOISE, SEED = 0.4, 20261021

nx, ny = int(round(LX / DX)), int(round(LY / DX))
x = (np.arange(nx) + 0.5) * DX
y = (np.arange(ny) + 0.5) * DX
X, Y = np.meshgrid(x, y)
z = np.zeros((ny, nx))
for xc, H in HILLS:
    r = np.hypot(X - xc, Y - YC)
    z = np.maximum(z, H - TANB * r)
rng = np.random.default_rng(SEED)
noise = rng.uniform(-ANOISE, ANOISE, z.shape)
z = np.where(z > 0.0, np.maximum(z + noise, 0.0), 0.0)
np.savetxt('z.txt', z, fmt='%.6f')
print('z.txt written: %d x %d (dx = %g m), zmax = %.2f m, hill cells = %d'
      % (nx, ny, DX, z.max(), int((z > 0).sum())))
