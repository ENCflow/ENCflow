#!/usr/bin/env python3
# examples/ashfall_lahar の入力生成
#   make_init.py z        : 降灰後の地表 z.txt(= 元地形 + 降灰厚)
#   make_init.py z_noash  : 元地形 z_noash.txt(対照ケース用)
#   make_init.py ash      : 降灰厚 ash.txt(土層厚 sd として与える)
# 地形: 西の山体斜面(tanθ=0.35、谷底 15 m の台形谷で中央に流れを集める)
#       → x=300 m の谷出口 → 緩勾配の扇状地(tanθ=0.08。谷壁は 100 m で消える)。
#       東辺は自由流出。
# 降灰: 西(火口側)で厚く東へ薄くなる一方向の分布。斜面上 0.30 → 0.05 m、
#       扇状地 0.03 m(扇状地の灰は侵食されず、堆積の下敷きになる)
import sys

NX, NY, DX = 120, 60, 5.0                 # 600 m × 300 m
XAPEX, ST_UP, ST_FAN = 300.0, 0.35, 0.08  # 谷出口の x、斜面勾配、扇状地勾配
SV, WFLOOR, LTAPER = 0.12, 15.0, 100.0    # 谷壁の横断勾配、谷底の幅、谷出口下流でのテーパ長
ASH0, ASH1, ASHFAN = 0.30, 0.05, 0.03     # 降灰厚: 斜面上端、谷出口、扇状地
YC = NY * DX / 2


def z_ground(x, y):
    wall = SV * max(0.0, abs(y - YC) - WFLOOR / 2)   # 平らな谷底 + 両側の谷壁
    if x <= XAPEX:
        z = ST_UP * (XAPEX - x)
        v = wall
    else:
        z = -ST_FAN * (x - XAPEX)
        v = wall * max(0.0, 1.0 - (x - XAPEX) / LTAPER)
    return z + v + ST_FAN * (NX * DX - XAPEX)   # 東端で z=0


def ash(x, y):
    if x <= XAPEX:
        return ASH0 + (ASH1 - ASH0) * x / XAPEX
    return ASHFAN


kind = sys.argv[1]
for j in range(1, NY + 1):
    y = (j - 0.5) * DX
    vals = []
    for i in range(1, NX + 1):
        x = (i - 0.5) * DX
        if kind == "z":
            vals.append("%.4f" % (z_ground(x, y) + ash(x, y)))
        elif kind == "z_noash":
            vals.append("%.4f" % z_ground(x, y))
        else:
            vals.append("%.4f" % ash(x, y))
    print(" ".join(vals))
