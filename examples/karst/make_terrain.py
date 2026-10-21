#!/usr/bin/env python3
"""カルスト地形実験用の地形(z.txt)と可溶率マップ(sol.txt)を生成する。

石灰岩台地(z ≈ 300 m)に、相関長をもつ滑らかな起伏(白色雑音のガウス平滑。
振幅 ±1 m 程度、シード固定)を与え、閉じた浅い窪みを多数つくる(ドリーネの
種。特定の波長を持ち込まない)。縁の 3 セルは不溶性の岩(可溶率 0)の低い
尾根(+3 m)として、内陸排水(水は域外へ出ず、吸込穴か土層へ入るだけ)を
保つ。
  python3 make_terrain.py        # z.txt, sol.txt(1000 × 1000 m、Δx = 10 m)
"""
import numpy as np

LX, LY, DX = 1000.0, 1000.0, 10.0
Z0, ANOISE, SIGMA, SEED = 300.0, 1.0, 3.0, 20261021   # 基準高、起伏の振幅 (m)、平滑の σ(セル)、シード
RIM, ZRIM = 3, 3.0                                   # 縁の幅(セル)と高さ (m)

nx, ny = int(round(LX / DX)), int(round(LY / DX))
rng = np.random.default_rng(SEED)
w = rng.standard_normal((ny, nx))
# ガウス平滑(周期畳み込み。FFT)→ 標準偏差 1 に正規化 → 振幅 ANOISE
ky = np.fft.fftfreq(ny)[:, None]
kx = np.fft.fftfreq(nx)[None, :]
g = np.exp(-2.0 * (np.pi * SIGMA) ** 2 * (kx ** 2 + ky ** 2))
s = np.real(np.fft.ifft2(np.fft.fft2(w) * g))
s = s / s.std()
z = Z0 + ANOISE * s
sol = np.ones((ny, nx))
rim = np.zeros((ny, nx), dtype=bool)
rim[:RIM, :] = rim[-RIM:, :] = rim[:, :RIM] = rim[:, -RIM:] = True
z[rim] = Z0 + ANOISE * s[rim] + ZRIM
sol[rim] = 0.0
np.savetxt('z.txt', z, fmt='%.4f')
np.savetxt('sol.txt', sol, fmt='%.0f')
print('z.txt / sol.txt written: %d x %d (dx = %g m), z = %.2f .. %.2f m, interior std %.2f m'
      % (nx, ny, DX, z[~rim].min(), z[~rim].max(), z[~rim].std()))
