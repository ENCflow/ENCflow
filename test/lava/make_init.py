#!/usr/bin/env python3
# test/lava の入力生成
#   zinit.txt : 等勾配斜面 tanθ=0.2(構成2 Bingham 停止・固化検定。
#               nx=100, ny=8, dx=1。z = ST*(LX - x)、x = (i-0.5)*dx)。引数なし
#   zwall.txt : 平坦な床と高さ 10 m の段(構成5 壁の前の溶岩だまりの固化検定。
#               nx=40, ny=8, dx=1。i <= 30 は z = 0、i >= 31 は z = 10 m の
#               乾いた段 = 溶岩面より高い壁)。引数 wall
# 構成1(Huppert)・構成4(ドーム)は平坦床 f_ztype=0 のため生成不要。
# 範囲・定数は param_ty.txt / param_wall.txt / Check_lava.py の期待値と対で保守する
import sys

kind = sys.argv[1] if len(sys.argv) > 1 else "slope"
if kind == "wall":
    NXW, NYW, IWALL, ZWALL = 40, 8, 31, 10.0
    for j in range(1, NYW + 1):
        print(" ".join("%.6f" % (ZWALL if i >= IWALL else 0.0)
                       for i in range(1, NXW + 1)))
else:
    NX, NY, DX, ST, LX = 100, 8, 1.0, 0.2, 100.0
    for j in range(1, NY + 1):
        print(" ".join("%.6f" % (ST * (LX - (i - 0.5) * DX))
                       for i in range(1, NX + 1)))
