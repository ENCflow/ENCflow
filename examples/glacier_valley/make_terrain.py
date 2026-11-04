#!/usr/bin/env python3
"""examples/glacier_valley の初期地形(川が刻んだ V 字谷と支谷)を data/z.txt に書く。

  python3 make_terrain.py

24 km × 8 km、Δx = 200 m(120 × 40 セル)。行は北 → 南(行 1 が北端)。
- 主谷: 西から東へ流れる V 字谷。谷の軸は y = 4 km(中央の 2 行の境界)。
    谷底 z_f(x) = 2200 − 0.03 (x − 3 km)(x ≥ 3 km。東端で 1570 m)、
    谷頭 x < 3 km は盆地状に 3100 m(x = 0)まで上がる(指数 1.5)。
    谷壁の勾配 0.4、谷の肩(台地)は谷底から hs(x) = 600 + 700 (1 − x/5 km)² m の高さ。
- 支谷: 北の端から主谷へ直角に合流する V 字谷(谷の軸 x = 11 km。格子の軸に沿う)。
    谷底 z_t(y) = z_j + 0.12 (y_c − y) + 500 (1 − y/1.5 km)²(z_j は合流点の主谷の谷底)、
    谷壁の勾配 0.4、肩は谷底から 600 + 500 (1 − y/2 km)² m。
    合流点では支谷の谷底と主谷の谷底が同じ高さ(川の谷の合流 = Playfair の法則)。
定数は param_*.txt・plot_results.py と対で保守する。
"""
import os

import numpy as np

NX, NY, DX = 120, 40, 200.0
YC = NY * DX / 2.0           # 主谷の軸(m。北端から)
XT = 11000.0                 # 支谷の軸(m。西端から)
SLOPE = 0.03                 # 主谷の谷底の勾配(x ≥ 3 km)
WALL = 0.4                   # 谷壁の勾配


def terrain():
    x = (np.arange(NX) + 0.5) * DX
    y = (np.arange(NY) + 0.5) * DX
    X, Y = np.meshgrid(x, y)
    zf = np.where(X >= 3000.0, 2200.0 - SLOPE * (X - 3000.0),
                  2200.0 + 900.0 * np.clip((3000.0 - X) / 3000.0, 0.0, 1.0) ** 1.5)
    hs = 600.0 + 700.0 * np.maximum(0.0, 1.0 - X / 5000.0) ** 2
    zmain = zf + np.minimum(WALL * np.abs(Y - YC), hs)
    zj = 2200.0 - SLOPE * (XT - 3000.0)
    zt = zj + 0.12 * (YC - Y) + 500.0 * np.maximum(0.0, 1.0 - Y / 1500.0) ** 2
    hst = 600.0 + 500.0 * np.maximum(0.0, 1.0 - Y / 2000.0) ** 2
    ztrib = np.where(Y <= YC, zt + np.minimum(WALL * np.abs(X - XT), hst), 1.0e9)
    return np.minimum(zmain, ztrib)


if __name__ == "__main__":
    z = terrain()
    os.makedirs("data", exist_ok=True)
    with open("data/z.txt", "w") as f:
        for row in z:
            f.write("".join(f"{v:10.2f}" for v in row) + "\n")
    print(f"wrote data/z.txt ({NX} x {NY}, dx = {DX:.0f} m), z = {z.min():.0f} .. {z.max():.0f} m")
