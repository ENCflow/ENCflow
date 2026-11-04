#!/usr/bin/env python3
# test/lava の入力生成
#   zinit.txt : 等勾配斜面 tanθ=0.2(構成2 Bingham 停止・固化検定。
#               nx=100, ny=8, dx=1。z = ST*(LX - x)、x = (i-0.5)*dx)。引数なし
#   zwall.txt : 平坦な床と高さ 10 m の段(構成5 壁の前の溶岩だまりの固化検定。
#               nx=40, ny=8, dx=1。i <= 30 は z = 0、i >= 31 は z = 10 m の
#               乾いた段 = 溶岩面より高い壁)。引数 wall
#   cool_cells.txt : 全セル(nx=4, ny=8)の噴火口のセル集合(構成7 静止した層の
#               冷却。fn_lv_cell の "i j" の行列挙)。引数 cool
#   zrun.txt  : 等勾配斜面 tanθ=0.1(構成9 冷えて止まる流れ。nx=64, ny=8, dx=5。
#               z = ST*(LX - x)、x = (i-0.5)*dx)。引数 run
# 構成1(Huppert)・構成4(ドーム)は平坦床 f_ztype=0 のため生成不要。
# 範囲・定数は param_ty.txt / param_wall.txt / param_cool.txt / param_run*.txt /
# Check_lava.py の期待値と対で保守する
import sys

kind = sys.argv[1] if len(sys.argv) > 1 else "slope"
if kind == "run":
    NXR, NYR, DXR, STR = 64, 8, 5.0, 0.1
    LXR = NXR * DXR
    for j in range(1, NYR + 1):
        print(" ".join("%.6f" % (STR * (LXR - (i - 0.5) * DXR))
                       for i in range(1, NXR + 1)))
elif kind == "cool":
    NXC, NYC = 4, 8
    for j in range(1, NYC + 1):
        for i in range(1, NXC + 1):
            print("%d %d" % (i, j))
elif kind == "wall":
    NXW, NYW, IWALL, ZWALL = 40, 8, 31, 10.0
    for j in range(1, NYW + 1):
        print(" ".join("%.6f" % (ZWALL if i >= IWALL else 0.0)
                       for i in range(1, NXW + 1)))
else:
    NX, NY, DX, ST, LX = 100, 8, 1.0, 0.2, 100.0
    for j in range(1, NY + 1):
        print(" ".join("%.6f" % (ST * (LX - (i - 0.5) * DX))
                       for i in range(1, NX + 1)))
