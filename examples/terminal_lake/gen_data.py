#!/usr/bin/env python3
"""terminal_lake の入力(data_lake/)を作る。
  z.txt             放物面のすり鉢 z = 10 m × (r / 5 km)²(61 × 61 セル、dx = 200 m。中心が最も深い)
  inflow_cells.txt  流入を入れるセル(湖の中心の 5 × 5 セル = 1 km 四方。1 行 1 セルの「i j」)
水位 η の湖の面積は A = k·η、体積は V = k·η²/2(k = π·(5 km)²/10 m)で、水収支 dV/dt = Q − E·A を
常微分方程式として解ける(plot_results.py が、このラスタ地形の面積・体積で解いて計算と比べる)。
行は北から南、列は西から東(対称なので向きは結果に効かない)。"""
import math
import os

NX = NY = 61
DX = 200.0
R0, ZC = 5000.0, 10.0
D = "data_lake"
os.makedirs(D, exist_ok=True)
ic = (NX + 1) / 2.0
with open(os.path.join(D, "z.txt"), "w") as f:
    for j in range(1, NY + 1):
        f.write(" ".join("%.5f" % (ZC * (math.hypot((i - ic) * DX, (j - ic) * DX) / R0) ** 2)
                         for i in range(1, NX + 1)) + "\n")
with open(os.path.join(D, "inflow_cells.txt"), "w") as f:
    for j in range(29, 34):
        for i in range(29, 34):
            f.write("%d %d\n" % (i, j))
print("wrote", D + "/z.txt", D + "/inflow_cells.txt")
