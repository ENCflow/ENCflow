#!/usr/bin/env python3
# examples/tsunami_fault の地形: 200 km × 150 km、dx = dy = 1 km。x ≥ 60 km は水深 2000 m の平坦な海、
#   x < 60 km は海岸へ向かう一様斜面(x = 0 で +100 m。汀線 x ≈ 2.9 km)。行順は北 → 南
NX, NY, DX = 200, 150, 1000.0
for j in range(1, NY + 1):
    row = []
    for i in range(1, NX + 1):
        x = (i - 0.5) * DX
        z = -2000.0 if x >= 60000.0 else 100.0 - 2100.0 * x / 60000.0
        row.append("%.2f" % z)
    print(" ".join(row))
