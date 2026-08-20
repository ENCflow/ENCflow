#!/usr/bin/env python3
# 台地+擾乱付き急崖(tanθ=1.5 ≈ 56°)の地形を生成する(z.txt)
# 崖縁の位置 xe(y) に 2 モードの正弦擾乱(±1.3 m)を与える。
# 検定(Check_contrast.py)の初期起伏の期待値と対で保守すること。
import numpy as np

nx, ny = 40, 24
z = np.zeros((ny, nx))
for j in range(ny):
    y = (j + 0.5) * 2.0
    xe = 20.0 + 0.8 * np.sin(2 * np.pi * y * 2.0 / 24.0) \
              + 0.5 * np.sin(2 * np.pi * y * 2.0 / 11.4)
    for i in range(nx):
        x = (i + 0.5) * 2.0
        if x < xe:
            z[j, i] = 9.0
        else:
            z[j, i] = max(9.0 - 1.5 * (x - xe), 0.0)
np.savetxt('z.txt', z, fmt='%.6f')
