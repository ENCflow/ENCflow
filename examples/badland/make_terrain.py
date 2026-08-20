#!/usr/bin/env python3
# 台地(z=15 m)+急崖(tanθ=1.5 ≈ 56°)の地形を生成する(z.txt)
# 崖縁の位置 xe(y) に**白色雑音**(一様分布 ±0.5 m、シード固定)を与える。
# 特定の波長を持ち込まないため、形成される谷の位置・間隔は
# 侵食則と平滑化(creep)の側で決まる(自己組織化の実験)。
# シードを固定しているので何度生成しても同一地形(再現性)。
import numpy as np

rng = np.random.default_rng(20260820)
nx, ny = 80, 60
noise = rng.uniform(-0.5, 0.5, ny)
z = np.zeros((ny, nx))
for j in range(ny):
    xe = 20.0 + noise[j]
    for i in range(nx):
        x = i + 0.5
        if x < xe:
            z[j, i] = 15.0
        else:
            z[j, i] = max(15.0 - 1.5 * (x - xe), 0.0)
np.savetxt('z.txt', z, fmt='%.6f')
print('z.txt written (%d x %d), edge noise std = %.3f m' % (nx, ny, noise.std()))
