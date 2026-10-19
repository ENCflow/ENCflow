#!/usr/bin/env python3
# 台地(z = 15 m)+急崖(tanθ = 1.5)が海(z ≤ 0 = 海域マスク)に落ちる地形を
# 生成する(z.txt, sw.txt)。崖縁の位置 xe(y) に 2 波長の正弦擾乱
#   短波長 λ1 = 4 m(4Δx)、長波長 λ2 = 20 m(いずれも振幅 0.3 m)
# を与える。Check_select.py はこの 2 モードのフーリエ振幅の成長比を検定する
# ので、波長・振幅を変えるときは対で保守すること。
import numpy as np

nx, ny, dx = 50, 40, 1.0
lam1, lam2, amp = 4.0, 20.0, 0.3
z = np.zeros((ny, nx)); sw = np.zeros((ny, nx), dtype=int)
for j in range(ny):
    y = (j + 0.5) * dx
    xe = 20.0 + amp * np.sin(2 * np.pi * y / lam1) + amp * np.sin(2 * np.pi * y / lam2)
    for i in range(nx):
        x = (i + 0.5) * dx
        z[j, i] = 15.0 if x < xe else max(15.0 - 1.5 * (x - xe), 0.0)
        if z[j, i] <= 0.0:
            sw[j, i] = 1
np.savetxt('z.txt', z, fmt='%.6f')
np.savetxt('sw.txt', sw, fmt='%d')
