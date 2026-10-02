#!/usr/bin/env python3
"""1 セル幅水路の地形・マスクを生成する(直線 / 90° 屈曲つき折れ線)。

  python3 Make_channel.py straight   → z_straight.txt, mask_straight.txt (402×5)
  python3 Make_channel.py zigzag     → z_zigzag.txt,   mask_zigzag.txt   (240×164)
  python3 Make_channel.py steep      → z_steep.txt(S0 = 0.03 の直線 rw 河道。rw は rw_width10.txt)
  python3 Make_channel.py sbreak     → z_sbreak.txt(0.03 → 0.003 の勾配変化点。同上)
  python3 Make_channel.py wave10     → z_wave10.txt, rw_width10.txt (400×5。直線 rw 河道、堤内地は
                                       河床+10 m。洪水波 param_wave_*_s*.txt 用。§68.13)
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

if kind.startswith("diagw"):
    # 対角 1 セル河道 + サブグリッド幅(W = 7.07 m: 自然幅、diagw10: W = 10 m)。
    # 最初の 3 セルは x 方向、以後 45°。堤内地は河床+3 m(高さ0堤防が自動有効)
    W = float(kind[5:]) if len(kind) > 5 else DX / (2 ** 0.5)
    nx, ny = 400, 405
    # 両端の 3 セルは x 方向(流入・流出境界の面集合を軸河道と同じにする。
    # 終点を対角のまま東辺に置くと、幅未補正の自由流出面が狭い河道の貯留を
    # 抜き切って発散する。§18 制約 (5))
    path = [(i, 5) for i in range(1, 4)] + [(3 + k, 5 + k) for k in range(1, 395)] \
         + [(i, 399) for i in range(398, 401)]
    z = [[0.0] * nx for _ in range(ny)]; rw = [[0] * nx for _ in range(ny)]; w = [[0.0] * nx for _ in range(ny)]
    bed = {}
    for k, (i, j) in enumerate(path):
        bed[(i, j)] = Z0 - S * (sum(DX if (kk < 3 or kk >= 397) else DX * 2 ** 0.5 for kk in range(k)))
    for j in range(ny):
        for i in range(nx):
            # 堤内地の標高: 最寄りの河道セル(同じ路長位置近傍)の河床 + 3 m で近似
            kk = min(max(i - 1, 0), 399)
            z[j][i] = bed[path[kk]] + 3.0
    for (i, j), zb in bed.items():
        z[j - 1][i - 1] = zb; rw[j - 1][i - 1] = 1; w[j - 1][i - 1] = W
    for name, a, fmt in ((f"z_{kind}", z, "%.4f"), (f"rw_{kind}", rw, "%d"), (f"width_{kind}", w, "%.2f")):
        with open(name + ".txt", "w") as f:
            for row in a:
                f.write(" ".join(fmt % v for v in row) + "\n")
    with open(f"path_{kind}.csv", "w") as f:
        f.write("k,i,j,s\n")
        for k, (i, j) in enumerate(path): f.write(f"{k},{i},{j},0\n")
    print(kind, nx, ny, "W =", W)
    sys.exit(0)

if kind in ("steep", "sbreak"):
    # 直線 rw 河道(堤内地 = 河床+10 m)の急勾配版: steep は S0 = 0.03 一様、
    # sbreak は x < 2 km が 0.03、以後 0.003(勾配変化点の跳水)。§68.17 の
    # 区間別診断の補助テスト(param_steep_s*.txt / param_sbreak_s*.txt)
    nx, ny = 400, 5
    slopes = [0.03] * nx if kind == "steep" else [0.03] * 200 + [0.003] * 200
    bed = [Z0]
    for i in range(1, nx):
        bed.append(bed[-1] - slopes[i] * DX)
    z = [[bed[i] + (0.0 if j == 2 else 10.0) for i in range(nx)] for j in range(ny)]
    with open(f"z_{kind}.txt", "w") as f:
        for row in z:
            f.write(" ".join("%.4f" % v for v in row) + "\n")
    print(kind, nx, ny)
    sys.exit(0)

if kind == "wave10":
    # 直線軸河道(rw マスク、幅なし)+ 堤内地 = 河床+10 m(洪水波のピーク h ≈ 4 m
    # でも堤内地に溢れない)。param_wave_{nolev,o0,o1}_s*.txt(§68.13)で使う
    nx, ny = 400, 5
    z = [[0.0] * nx for _ in range(ny)]; rw = [[0] * nx for _ in range(ny)]
    for i in range(nx):
        bed = Z0 - S * DX * i
        for j in range(ny):
            z[j][i] = bed + (0.0 if j == 2 else 10.0)
        rw[2][i] = 1
    for name, a, fmt in (("z_wave10", z, "%.4f"), ("rw_width10", rw, "%d")):
        with open(name + ".txt", "w") as f:
            for row in a:
                f.write(" ".join(fmt % v for v in row) + "\n")
    print(kind, nx, ny)
    sys.exit(0)

if kind.startswith("width"):
    # 直線軸河道 + サブグリッド幅(width = 4 m、width10 = 10 m など)
    W = float(kind[5:]) if len(kind) > 5 else 4.0
    nx, ny = 400, 5
    z = [[0.0] * nx for _ in range(ny)]; rw = [[0] * nx for _ in range(ny)]; w = [[0.0] * nx for _ in range(ny)]
    for i in range(nx):
        bed = Z0 - S * DX * i
        for j in range(ny):
            z[j][i] = bed + (0.0 if j == 2 else 3.0)
        rw[2][i] = 1; w[2][i] = W
    for name, a, fmt in ((f"z_{kind}", z, "%.4f"), (f"rw_{kind}", rw, "%d"), (f"width_{kind}", w, "%.2f")):
        with open(name + ".txt", "w") as f:
            for row in a:
                f.write(" ".join(fmt % v for v in row) + "\n")
    print(kind, nx, ny)
    sys.exit(0)

if kind == "zigzagw":
    # 折れ線(zigzag と同じ経路)+ 堤内地セル(河床+3 m、マスクなし → 高さ0堤防)
    # + サブグリッド幅 W = 10 m(軸区間の自然幅 = 解像)。屈曲部の挙動を測る
    nx, ny = 240, 164
    j0 = 2
    path = [(i, j0) for i in range(1, 81)]
    path += [(80, j) for j in range(j0 + 1, j0 + 81)]
    path += [(i, j0 + 80) for i in range(81, 161)]
    path += [(160, j) for j in range(j0 + 81, j0 + 161)]
    path += [(i, j0 + 160) for i in range(161, 241)]
    bed = {(i, j): Z0 - S * DX * k for k, (i, j) in enumerate(path)}
    z = [[0.0] * nx for _ in range(ny)]; rw = [[0] * nx for _ in range(ny)]; w = [[0.0] * nx for _ in range(ny)]
    for j in range(ny):
        for i in range(nx):
            # 堤内地: 最寄り(マンハッタン距離)の河道セルの河床 + 3 m
            kk = min(range(len(path)), key=lambda k: abs(path[k][0] - (i + 1)) + abs(path[k][1] - (j + 1)))
            z[j][i] = bed[path[kk]] + 3.0
    for (i, j), zb in bed.items():
        z[j - 1][i - 1] = zb; rw[j - 1][i - 1] = 1; w[j - 1][i - 1] = 10.0
    for name, a, fmt in (("z_zigzagw", z, "%.4f"), ("rw_zigzagw", rw, "%d"), ("width_zigzagw", w, "%.2f")):
        with open(name + ".txt", "w") as f:
            for row in a:
                f.write(" ".join(fmt % v for v in row) + "\n")
    with open("path_zigzagw.csv", "w") as f:
        f.write("k,i,j,s\n")
        for k, (i, j) in enumerate(path): f.write(f"{k},{i},{j},{k * DX}\n")
    print(kind, nx, ny)
    sys.exit(0)

if kind == "straight":
    nx, ny = 400, 5
    path = [(i, 3) for i in range(1, 401)]
elif kind == "diag":
    # 45° の対角 1 セル水路(8 連結)。路長は 400·dr。始点 (1,1) は西辺、
    # 終点 (400,400) は東辺・北辺に接する(自由流出は東辺・北辺)
    # 流入境界の面集合(法線+斜め)を直線区間と同じにするため、最初の 3 セルは
    # x 方向に進めてから 45° に折れる
    nx, ny = 400, 405
    path = [(i, 5) for i in range(1, 4)] + [(3 + k, 5 + k) for k in range(1, 398)]
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
        z[j - 1][i - 1] = Z0 - S * (DX * (2 ** 0.5) if kind == "diag" else DX) * k
        m[j - 1][i - 1] = 1
        f.write(f"{k},{i},{j},{k * (DX * (2 ** 0.5) if kind == 'diag' else DX)}\n")
with open(f"z_{kind}.txt", "w") as f:
    for row in z:
        f.write(" ".join("%.4f" % v for v in row) + "\n")
with open(f"mask_{kind}.txt", "w") as f:
    for row in m:
        f.write(" ".join(str(v) for v in row) + "\n")
print(kind, nx, ny, "cells on path:", len(path))
