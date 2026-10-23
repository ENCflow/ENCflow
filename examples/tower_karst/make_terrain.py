#!/usr/bin/env python3
"""タワーカルスト実験用の入力を生成する(z.txt, sd.txt, ksv.txt)。

平野(z ≈ 0、土層 1 m、浸透能 40 mm/h)の上に、裸岩の丘(高さ 40 m・
半径 90 m の釣鐘形 × 4 と小丘 2 つ。土層 1e-3 m、浸透能 1 mm/h)を置く。
平野には相関長 ≈ 30 m・標準偏差 0.3 m の起伏(シード固定)を与える。
丘と平野の境は z = 5 m(それより高いセルが裸岩)。
  python3 make_terrain.py        # 1000 × 1000 m、Δx = 10 m
"""
import numpy as np

LX, LY, DX = 1000.0, 1000.0, 10.0
HILLS = [(300.0, 300.0, 40.0, 90.0), (700.0, 320.0, 40.0, 90.0),
         (320.0, 720.0, 40.0, 90.0), (690.0, 700.0, 40.0, 90.0),
         (500.0, 520.0, 20.0, 60.0), (150.0, 850.0, 20.0, 60.0)]   # (xc, yc, 高さ H, 半径 R)
ANOISE, SIGMA, SEED = 0.3, 3.0, 20261022
ZROCK = 5.0                                    # これより高いセルは裸岩
SD_PLAIN, SD_ROCK = 1.0, 1.0e-3                # 土層厚 (m)
KSV_PLAIN, KSV_ROCK = 40.0, 1.0                # 浸透能 (mm/h)

nx, ny = int(round(LX / DX)), int(round(LY / DX))
x = (np.arange(nx) + 0.5) * DX
y = (np.arange(ny) + 0.5) * DX
X, Y = np.meshgrid(x, y)
rng = np.random.default_rng(SEED)
w = rng.standard_normal((ny, nx))
ky = np.fft.fftfreq(ny)[:, None]
kx = np.fft.fftfreq(nx)[None, :]
g = np.exp(-2.0 * (np.pi * SIGMA) ** 2 * (kx ** 2 + ky ** 2))
s = np.real(np.fft.ifft2(np.fft.fft2(w) * g))
s = s / s.std()
z = ANOISE * s
for xc, yc, H, R in HILLS:
    r = np.hypot(X - xc, Y - yc)
    # 釣鐘形(半径 R で裾、頂は丸い): H (1 - (r/R)^2)^1.5
    z = z + np.where(r < R, H * (1.0 - (r / R) ** 2) ** 1.5, 0.0)
rock = z > ZROCK
sd = np.where(rock, SD_ROCK, SD_PLAIN)
ksv = np.where(rock, KSV_ROCK, KSV_PLAIN)
np.savetxt('z.txt', z, fmt='%.4f')
np.savetxt('sd.txt', sd, fmt='%.4f')
np.savetxt('ksv.txt', ksv, fmt='%.2f')
print('z.txt / sd.txt / ksv.txt written: %d x %d (dx = %g m), z = %.2f .. %.2f m, rock cells = %d (%.1f %%)'
      % (nx, ny, DX, z.min(), z.max(), int(rock.sum()), 100.0 * rock.mean()))
