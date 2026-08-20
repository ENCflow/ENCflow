#!/usr/bin/env python3
# 台地(z=15 m)+擾乱付き急崖(tanθ=1.5 ≈ 56°)の地形を生成する(z.txt)
# 崖縁の位置 xe(y) に 2 モードの正弦擾乱(±0.65 m)を与える。
# param.txt(nx=80, ny=60, dx=dy=1 m)と対。
import numpy as np

nx, ny = 80, 60
z = np.zeros((ny, nx))
for j in range(ny):
    y = j + 0.5
    xe = 20 + 0.4 * np.sin(2 * np.pi * y / 15) \
            + 0.25 * np.sin(2 * np.pi * y / 7.3)
    for i in range(nx):
        x = i + 0.5
        if x < xe:
            z[j, i] = 15.0
        else:
            z[j, i] = max(15.0 - 1.5 * (x - xe), 0.0)
np.savetxt('z.txt', z, fmt='%.6f')
print('z.txt written (%d x %d)' % (nx, ny))
