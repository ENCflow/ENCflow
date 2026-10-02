#!/usr/bin/env python3
"""1 セル幅水路の地形・マスクを生成する(直線 / 90° 屈曲つき折れ線)。

  python3 Make_channel.py straight   → z_straight.txt, mask_straight.txt (402×5)
  python3 Make_channel.py zigzag     → z_zigzag.txt,   mask_zigzag.txt   (240×164)
  python3 Make_channel.py width      → z_width.txt, rw_width.txt, width_width.txt (400×5。
                                       サブグリッド河道幅 W = 4 m の直線水路。堤内地は河床+3 m、
                                       マスクなし = 高さ0堤防が自動有効。§68.9)

いずれも路長 400 セル(dx = 10 m)、河床勾配 S = 0.005(路長に沿って)、
西辺の始点に区間流入 Q、終点は東辺(自由流出)。折れ線は 80 セルの
直線区間 5 本(東→北→東→北→東)で 90° 屈曲 4 回。水路外はマスク 0(壁)。
path_*.csv に路上のセル (i, j, 路長 s) を書く(解析用)。
"""
import sys
DX, S, Z0 = 10.0, 0.005, 100.0
kind = sys.argv[1] if len(sys.argv) > 1 else "straight"

if kind == "width":
    nx, ny = 400, 5
    z = [[0.0] * nx for _ in range(ny)]; rw = [[0] * nx for _ in range(ny)]; w = [[0.0] * nx for _ in range(ny)]
    for i in range(nx):
        bed = Z0 - S * DX * i
        for j in range(ny):
            z[j][i] = bed + (0.0 if j == 2 else 3.0)
        rw[2][i] = 1; w[2][i] = 4.0
    for name, a, fmt in (("z_width", z, "%.4f"), ("rw_width", rw, "%d"), ("width_width", w, "%.2f")):
        with open(name + ".txt", "w") as f:
            for row in a:
                f.write(" ".join(fmt % v for v in row) + "\n")
    print(kind, nx, ny)
    sys.exit(0)

if kind == "straight":
    nx, ny = 400, 5
    path = [(i, 3) for i in range(1, 401)]
else:
    nx, ny = 240, 164
    j0 = 2
    path = [(i, j0) for i in range(1, 81)]
    path += [(80, j) for j in range(j0 + 1, j0 + 81)]
    path += [(i, j0 + 80) for i in range(81, 161)]
    path += [(160, j) for j in range(j0 + 81, j0 + 161)]
    path += [(i, j0 + 160) for i in range(161, 241)]
assert len(path) == 400
z = [[Z0] * nx for _ in range(ny)]
m = [[0] * nx for _ in range(ny)]
with open(f"path_{kind}.csv", "w") as f:
    f.write("k,i,j,s\n")
    for k, (i, j) in enumerate(path):
        z[j - 1][i - 1] = Z0 - S * DX * k
        m[j - 1][i - 1] = 1
        f.write(f"{k},{i},{j},{k * DX}\n")
with open(f"z_{kind}.txt", "w") as f:
    for row in z:
        f.write(" ".join("%.4f" % v for v in row) + "\n")
with open(f"mask_{kind}.txt", "w") as f:
    for row in m:
        f.write(" ".join(str(v) for v in row) + "\n")
print(kind, nx, ny, "cells on path:", len(path))
