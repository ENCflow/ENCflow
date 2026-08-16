#!/usr/bin/env python3
# glacier ベンチマークの入力生成
#   (1) data/hi0.txt   : Halfar ドームの初期氷厚(平坦床 SIA の相似解 t=t0)
#                        H(r) = H0 [1 - (r/R0)^{4/3}]^{3/7}
#   (2) data/zcone.txt : カール形成スモークテスト用の円錐山体
#                        z(r) = max(0, ZTOP - SLOPE*r)
#   格子・定数は param.txt / param_cirque.txt / Check_*.py と対で保守する
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

print("wrote data/hi0.txt and data/zcone.txt")
