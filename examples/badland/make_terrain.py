#!/usr/bin/env python3
"""台地+急崖が海に落ちる地形を生成する(z_<name>.txt, sw_<name>.txt)。

  python3 make_terrain.py main            # 主ケース(120 m × 240 m、台地 60 m 幅、崖 30 m)
  python3 make_terrain.py sweep           # 相関長系列・対照用(100 m × 240 m、崖 15 m)
  python3 make_terrain.py sweep --dx 0.5  # 同じ地形を Δx = 0.5 m で(z_sweep05.txt)
  python3 make_terrain.py sweep --dx 2    # 同じ地形を Δx = 2 m で(z_sweep2.txt)

崖縁の位置 xe(y) に**白色雑音**(一様分布 ±0.5 m、シード固定)を与える。
特定の波長を持ち込まないため、形成される谷の位置・間隔は侵食則の側で決まる
(自己組織化の実験)。雑音は 1 m の基準格子上に生成し、格子幅を変えても
同じ縁の形を見るように最近傍で写す(格子収束の比較のため)。
z ≤ 0 のセルは海域マスク(崖は直接海に落ちる。海面 z = 0 が侵食基準面
spl_zbase)。シードを固定しているので何度生成しても同一地形。
"""
import argparse
import numpy as np

GEOM = {
    # lx, ly, 台地幅 wp, 台地高 hp, 崖の tanθ
    'main':  dict(lx=120.0, ly=240.0, wp=60.0, hp=30.0, tanb=1.5),
    'sweep': dict(lx=100.0, ly=240.0, wp=40.0, hp=15.0, tanb=1.5),
}
ANOISE, DNOISE, SEED = 0.5, 1.0, 20260820

ap = argparse.ArgumentParser()
ap.add_argument('name', choices=sorted(GEOM))
ap.add_argument('--dx', type=float, default=1.0)
a = ap.parse_args()
g = GEOM[a.name]
dx = a.dx
nx, ny = int(round(g['lx'] / dx)), int(round(g['ly'] / dx))

rng = np.random.default_rng(SEED)
nb = int(np.ceil(g['ly'] / DNOISE))
noise_b = rng.uniform(-ANOISE, ANOISE, nb)                  # 1 m 基準格子上の白色雑音
y = (np.arange(ny) + 0.5) * dx
noise = noise_b[np.minimum((y / DNOISE).astype(int), nb - 1)]
x = (np.arange(nx) + 0.5) * dx
xe = g['wp'] + noise
z = np.where(x[None, :] < xe[:, None], g['hp'],
             np.maximum(g['hp'] - g['tanb'] * (x[None, :] - xe[:, None]), 0.0))
sw = np.where(z <= 0.0, 1, 0)

tag = a.name if dx == 1.0 else a.name + ('%g' % dx).replace('.', '')
np.savetxt('z_%s.txt' % tag, z, fmt='%.6f')
np.savetxt('sw_%s.txt' % tag, sw, fmt='%d')
print('z_%s.txt / sw_%s.txt written (%d x %d, dx = %g m), edge noise std = %.3f m'
      % (tag, tag, nx, ny, dx, noise.std()))
