#!/usr/bin/env python3
# examples/tsunami_coast の地形(z.txt。行順は北 → 南)。120 km × 80 km、dx = dy = 500 m。
#   西が陸、海岸線 x = 20 km。y = 30〜50 km に奥行き 12 km の湾(頭 x = 8 km、水深 2 → 25 m)。
#   棚: x = 20〜40 km で 25 → 200 m、斜面: 40〜80 km で 200 → 1000 m、x ≥ 80 km は 1000 m。
#   陸: 最寄りの水域から 5 km までは 0.5 m/km の海岸平野(沈降 0.6 m で岸から 1.2 km が海面下)、その先は 2 m/km
import math
NX, NY, DX = 240, 160, 500.0
XC, XB, YB1, YB2 = 20.0, 8.0, 30.0, 50.0       # km: 海岸線、湾の頭、湾の南北端
for j in range(1, NY + 1):
    y = (NY - j + 0.5) * DX / 1000.0           # km(北が j = 1)
    row = []
    for i in range(1, NX + 1):
        x = (i - 0.5) * DX / 1000.0
        if x >= XC:
            if x < 40.0:
                z = -(25.0 + 175.0 * (x - XC) / 20.0)
            elif x < 80.0:
                z = -(200.0 + 800.0 * (x - 40.0) / 40.0)
            else:
                z = -1000.0
        elif XB <= x < XC and YB1 <= y <= YB2:
            z = -(2.0 + 23.0 * (x - XB) / (XC - XB))
        else:
            dsea = XC - x
            dbay = math.hypot(max(0.0, XB - x, x - XC), max(0.0, YB1 - y, y - YB2))
            dd = min(dsea, dbay)
            z = 0.5 * dd if dd <= 5.0 else 2.5 + 2.0 * (dd - 5.0)
        row.append("%.2f" % z)
    print(" ".join(row))
