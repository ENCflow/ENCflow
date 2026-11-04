#!/usr/bin/env python3
"""石林(stone forest)実験用の入力を生成する(z.txt, joints.txt)。

平らな石灰岩台地(z = ZTOP。相関長 ≈ 10 m・標準偏差 0.1 m の起伏、シード固定)に、
直交する 2 組の節理(x = 一定の線を SPACING_X 間隔、y = 一定の線を SPACING_Y 間隔。
各線の位置は ±1 セルの乱れ)を 1 セル幅で置き、節理のセルの可溶率を FSOL_JOINT、
ほかを 1 にした地図 joints.txt(fn_dissol)を書く。土層・浸透能は namelist の一様値。
  python3 make_terrain.py        # 200 × 200 m、Δx = 2 m
"""
import numpy as np

LX, LY, DX = 200.0, 200.0, 2.0
ZTOP = 30.0                                    # 台地の高さ (m)(溝が 20 m 級に深まっても 0 m を割らない)
ANOISE, SIGMA, SEED = 0.1, 5.0, 20261103
SPACING_X, SPACING_Y = 14.0, 18.0              # 節理の間隔 (m)(石林の柱の幅 10〜20 m)
FSOL_JOINT = 6.0                               # 節理のセルの可溶率(ほかは 1)

nx, ny = int(round(LX / DX)), int(round(LY / DX))
rng = np.random.default_rng(SEED)
w = rng.standard_normal((ny, nx))
ky = np.fft.fftfreq(ny)[:, None]
kx = np.fft.fftfreq(nx)[None, :]
g = np.exp(-2.0 * (np.pi * SIGMA) ** 2 * (kx ** 2 + ky ** 2))
s = np.real(np.fft.ifft2(np.fft.fft2(w) * g))
z = ZTOP + ANOISE * s / s.std()
joints = np.ones((ny, nx))
for x0 in np.arange(SPACING_X / 2.0, LX, SPACING_X):
    i = int(x0 / DX) + rng.integers(-1, 2)
    if 0 <= i < nx:
        joints[:, i] = FSOL_JOINT
for y0 in np.arange(SPACING_Y / 2.0, LY, SPACING_Y):
    j = int(y0 / DX) + rng.integers(-1, 2)
    if 0 <= j < ny:
        joints[j, :] = FSOL_JOINT
np.savetxt('z.txt', z, fmt='%.4f')
np.savetxt('joints.txt', joints, fmt='%.1f')
print('z.txt / joints.txt written: %d x %d (dx = %g m), z = %.2f .. %.2f m, joint cells = %d (%.1f %%)'
      % (nx, ny, DX, z.min(), z.max(), int((joints > 1).sum()), 100.0 * (joints > 1).mean()))
