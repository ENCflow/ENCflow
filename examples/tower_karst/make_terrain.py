#!/usr/bin/env python3
"""タワーカルスト実験用の入力を生成する(z.txt, sd.txt, ksv.txt)。

平野(z ≈ 0、土層 1 m、浸透能 40 mm/h)の上に、裸岩の丘(高さ 40 m・
半径 90 m の釣鐘形 × 4 と小丘 2 つ。土層 1e-3 m、浸透能 1 mm/h)を置く。
平野には相関長 ≈ 30 m・標準偏差 0.3 m の起伏(シード固定)を与える。
丘と平野の境は z = 5 m(それより高いセルが裸岩)。
  python3 make_terrain.py        # 1000 × 1000 m、Δx = 10 m
  python3 make_terrain.py --steady   # 準定常強制(param_steady.txt)用の浸透能 ksv_steady.txt も書く:
                                     #   裸岩の浸透能を年平均の雨 0.228 mm/h の下で豪雨と同じ年浸透率
                                     #   (1 mm/h × 1 h / 40 mm = 2.5 %)になる 0.0057 mm/h にする
  python3 make_terrain.py --base     # 基準面つき(param_base.txt)の入力も書く: 東端の 1 列を基準面の
                                     #   河道(z = ZRIVER)にした z_base.txt、管路層の水頭底 gwc_bot.txt
                                     #   (一様 ZBOT)、東端の吐口 gwc_outfall.txt、隆起の倍率 uplift.txt
                                     #   (東端の河道 0 = 基準面固定、ほか 1)
"""
import sys
import numpy as np

LX, LY, DX = 1000.0, 1000.0, 10.0
HILLS = [(300.0, 300.0, 40.0, 90.0), (700.0, 320.0, 40.0, 90.0),
         (320.0, 720.0, 40.0, 90.0), (690.0, 700.0, 40.0, 90.0),
         (500.0, 520.0, 20.0, 60.0), (150.0, 850.0, 20.0, 60.0)]   # (xc, yc, 高さ H, 半径 R)
ANOISE, SIGMA, SEED = 0.3, 3.0, 20261022
ZROCK = 5.0                                    # これより高いセルは裸岩
SD_PLAIN, SD_ROCK = 1.0, 1.0e-3                # 土層厚 (m)
KSV_PLAIN, KSV_ROCK = 40.0, 1.0                # 浸透能 (mm/h)
RAIN_STORM, DUR_STORM, STORMS_PER_YR = 40.0, 1.0, 50.0   # 代表豪雨 (mm/h, h) と年回数 → 年雨量 2000 mm
RAIN_STEADY = RAIN_STORM * DUR_STORM * STORMS_PER_YR / (365.25 * 24.0)   # 年平均 0.228 mm/h
KSV_ROCK_STEADY = RAIN_STEADY * (KSV_ROCK * DUR_STORM) / (RAIN_STORM * DUR_STORM)   # 同じ年浸透率 2.5 %
ZRIVER, ZBOT, CA_OUT = -5.0, -45.0, 0.15        # --base: 東端の河道の標高 (m)、管路層の水頭底 (m)、吐口 Cd·A (m2)

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
if '--base' in sys.argv:
    zb = z.copy()
    zb[:, -1] = ZRIVER                                   # 東端の 1 列 = 基準面の河道(自由流出の辺に接する)
    np.savetxt('z_base.txt', zb, fmt='%.4f')
    np.savetxt('gwc_bot.txt', np.full_like(z, ZBOT), fmt='%.2f')
    out = np.zeros_like(z); out[:, -1] = CA_OUT
    np.savetxt('gwc_outfall.txt', out, fmt='%.3f')
    up = np.ones_like(z); up[:, -1] = 0.0
    np.savetxt('uplift.txt', up, fmt='%.1f')
    # 河道の列は不溶・不浸透: 吐口から出た水(飽和した地下水)が河床で再浸透して溶食に数えられ、
    # 河床が安全弁の速さで掘れて基準面が落ちる(試走で実検出)のを防ぐ。河床は基準面として固定
    sol = np.ones_like(z); sol[:, -1] = 0.0
    np.savetxt('sol_base.txt', sol, fmt='%.1f')
    ksvb = np.where(rock, KSV_ROCK_STEADY, KSV_PLAIN); ksvb[:, -1] = 0.0
    np.savetxt('ksv_base.txt', ksvb, fmt='%.4f')
    print('z_base.txt (east column z = %.1f m) / gwc_bot.txt (%.1f m) / gwc_outfall.txt (east column Cd A = %.2f m2) / uplift.txt, sol_base.txt, ksv_base.txt (east column 0) written'
          % (ZRIVER, ZBOT, CA_OUT))
if '--steady' in sys.argv:
    np.savetxt('ksv_steady.txt', np.where(rock, KSV_ROCK_STEADY, KSV_PLAIN), fmt='%.4f')
    print('ksv_steady.txt written: rock %.4f mm/h under the steady rain %.3f mm/h (same annual infiltration fraction)'
          % (KSV_ROCK_STEADY, RAIN_STEADY))
print('z.txt / sd.txt / ksv.txt written: %d x %d (dx = %g m), z = %.2f .. %.2f m, rock cells = %d (%.1f %%)'
      % (nx, ny, DX, z.min(), z.max(), int(rock.sum()), 100.0 * rock.mean()))
