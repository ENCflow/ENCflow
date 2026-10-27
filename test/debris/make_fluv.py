#!/usr/bin/env python3
# 構成 5(param_fluv.txt)の地形 z_fluv.txt の生成: slope_break を転置した斜面
#   20 × 60 セル(Δx = 1 m)。流れは j 方向(南向き)で帯の界面を横切る。
#   y < 40 m で tanθ = 0.4、それより下流は平坦(z = 0)。
#   定数は Check_debris.py の fluv モードと対で保守する
NX, NY, ST, YB = 20, 60, 0.4, 40.0
for j in range(1, NY + 1):
    y = j - 0.5
    z = ST * (YB - y) if y < YB else 0.0
    print(" ".join("%.6f" % z for i in range(NX)))
