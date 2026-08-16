#!/usr/bin/env python3
# test/volcano の入力生成
#   zinit.txt   : 等勾配斜面 tanθ=0.2(構成1 Voellmy 定常等流ベンチマーク。
#                 nx=150, ny=8, dx=1。z = ST*(LX - x)、x = (i-0.5)*dx)
#   dbinit.txt  : 瞬時流動化の崩壊深分布 D=2m(構成2 τ_y ランアウト検定。
#                 slope_break 地形 60x20 の斜面上 i∈[5,15], j∈[8,13])
# 範囲・定数は param*.txt / Check_volcano.py の期待値と対で保守する
import sys

kind = sys.argv[1] if len(sys.argv) > 1 else "z"
if kind == "z":
    NX, NY, DX, ST, LX = 150, 8, 1.0, 0.2, 150.0
    for j in range(1, NY + 1):
        print(" ".join("%.6f" % (ST * (LX - (i - 0.5) * DX))
                       for i in range(1, NX + 1)))
else:
    NX, NY = 60, 20
    for j in range(1, NY + 1):
        print(" ".join("2.0" if (5 <= i <= 15 and 8 <= j <= 13) else "0.0"
                       for i in range(1, NX + 1)))
