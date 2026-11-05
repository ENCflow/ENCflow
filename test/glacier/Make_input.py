#!/usr/bin/env python3
# glacier ベンチマークの入力生成
#   (1) data/hi0.txt   : Halfar ドームの初期氷厚(平坦床 SIA の相似解 t=t0)
#                        H(r) = H0 [1 - (r/R0)^{4/3}]^{3/7}
#   (2) data/zcone.txt : カール形成スモークテスト用の円錐山体
#                        z(r) = max(0, ZTOP - SLOPE*r)
#   (3) data/zv200.txt, data/zv100.txt, data/hiv200.txt, data/hiv100.txt :
#                        侵食の結合長の検定(構成 5)用の V 字谷と、谷を一定の
#                        深さまで満たす初期氷厚(Δx = 200 m と 100 m の 2 通り)
#   (4) data/zch0w1.txt, data/zch45w1.txt, data/zch0w3.txt, data/zch45w3.txt と
#       data/hich0w1.txt ほか : 8 近傍の谷の流れの検定(構成 7。§99)用の谷と初期氷厚。
#                        勾配 0.1 の斜面に、0° は行 j = 6(1 セル)・5..7(3 セル)、45° は
#                        |i − j| = 0(1 本)・≤ 1(3 本)の谷を残して両側を 500 m 高くし、
#                        谷に沿う座標 s(0°: (i − 0.5)Δx、45°: (i + j − 1)Δx/√2)で
#                        中心 SC = 700 m・半長 LB = 500 m の cos² の氷の盛り上がり(最大 200 m)を置く
#   格子・定数は param*.txt / Check_*.py と対で保守する
import math
import os

os.makedirs("data", exist_ok=True)

# ---- (1) Halfar ドーム(param.txt: nx=ny=61, dx=dy=25 m, 中心セル 31)----
NX = NY = 61
DX = 25.0
H0, R0 = 200.0, 600.0
xc = (31 - 0.5) * DX
with open("data/hi0.txt", "w") as f:
    for j in range(1, NY + 1):
        row = []
        for i in range(1, NX + 1):
            x = (i - 0.5) * DX - xc
            y = (j - 0.5) * DX - xc
            r = math.hypot(x, y)
            if r < R0:
                h = H0 * (1.0 - (r / R0) ** (4.0 / 3.0)) ** (3.0 / 7.0)
            else:
                h = 0.0
            row.append(f"{h:12.4f}")
        f.write("".join(row) + "\n")

# ---- (2) 円錐山体(param_cirque.txt: nx=ny=81, dx=dy=50 m, 中心セル 41)----
NX = NY = 81
DX = 50.0
ZTOP, SLOPE = 900.0, 0.35
xc = (41 - 0.5) * DX
with open("data/zcone.txt", "w") as f:
    for j in range(1, NY + 1):
        row = []
        for i in range(1, NX + 1):
            x = (i - 0.5) * DX - xc
            y = (j - 0.5) * DX - xc
            r = math.hypot(x, y)
            z = max(0.0, ZTOP - SLOPE * r)
            row.append(f"{z:12.4f}")
        f.write("".join(row) + "\n")

# ---- (3) V 字谷と初期氷厚(param_lc*.txt: 6000 m × 4000 m、Δx = 200 m / 100 m)----
#   谷底 z_f(x) = 1000 − VSLOPE·x(西から東へ下る)、谷壁 z = z_f + WALL·|y − YC|。
#   初期氷厚 H = max(0, HICE − WALL·|y − YC|)(氷面は谷を横切る方向に平ら、
#   谷に沿って谷底と平行)。谷の軸はセルの境界に来る(行数が偶数)
LX, LY = 6000.0, 4000.0
YC = LY / 2.0
VSLOPE, WALL, HICE = 0.03, 0.4, 250.0
for DX in (200.0, 100.0):
    NX, NY = int(LX / DX), int(LY / DX)
    tag = f"{int(DX)}"
    with open(f"data/zv{tag}.txt", "w") as fz, open(f"data/hiv{tag}.txt", "w") as fh:
        for j in range(1, NY + 1):
            y = (j - 0.5) * DX
            rz, rh = [], []
            for i in range(1, NX + 1):
                x = (i - 0.5) * DX
                rz.append(f"{1000.0 - VSLOPE * x + WALL * abs(y - YC):12.4f}")
                rh.append(f"{max(0.0, HICE - WALL * abs(y - YC)):12.4f}")
            fz.write("".join(rz) + "\n")
            fh.write("".join(rh) + "\n")

# ---- (4) 8 近傍の谷の流れ(param_ch*.txt。0°: nx=60, ny=11、45°: nx=ny=44、Δx = 50 m)----
DX, ST, HW, HB, SC, LB = 50.0, 0.1, 500.0, 200.0, 700.0, 500.0
for tag in ("ch0w1", "ch0w3", "ch45w1", "ch45w3"):
    m = 0 if tag.endswith("w1") else 1
    if tag.startswith("ch0"):
        NX, NY = 60, 11
        inch = lambda i, j: abs(j - 6) <= m
        sc = lambda i, j: (i - 0.5) * DX
        zf = lambda i, j: ST * (NX * DX - sc(i, j))
    else:
        NX = NY = 44
        inch = lambda i, j: abs(i - j) <= m
        sc = lambda i, j: (i + j - 1) * DX / math.sqrt(2.0)
        zf = lambda i, j: ST * (2 * NX * DX / math.sqrt(2.0) - sc(i, j))
    with open(f"data/z{tag}.txt", "w") as fz, open(f"data/hi{tag}.txt", "w") as fh:
        for j in range(1, NY + 1):
            rz, rh = [], []
            for i in range(1, NX + 1):
                rz.append(f"{zf(i, j) + (0.0 if inch(i, j) else HW):12.4f}")
                h = 0.0
                if inch(i, j) and abs(sc(i, j) - SC) < LB:
                    h = HB * math.cos(math.pi * (sc(i, j) - SC) / (2.0 * LB)) ** 2
                rh.append(f"{h:12.4f}")
            fz.write("".join(rz) + "\n")
            fh.write("".join(rh) + "\n")

print("wrote data/hi0.txt, data/zcone.txt, data/zv*.txt, data/hiv*.txt and data/zch*.txt, data/hich*.txt")
