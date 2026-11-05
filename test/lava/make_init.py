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
#   wrk_zx0.txt / wrk_zx45.txt : 構成10(熱の横断の数値拡散)の等勾配斜面 tanθ=0.1。
#               x0 は x 方向(nx=60, ny=20, dx=5)、x45 は (1,1) 方向
#               (nx=ny=60、z = ST*(2*N*dx - (x + y))/√2)。引数 x0 / x45
#   wrk_x0c1.txt / wrk_x0c2.txt : 構成10 の 0° の噴火口(列 i=3 の j=1..10 と
#               j=11..20)。引数 x0c1 / x0c2
#   wrk_x45c1.txt / wrk_x45c2.txt : 構成10 の 45° の噴火口(反対角線 i+j=33 の
#               i=3..16(i<j)と i=17..30(i>j))。引数 x45c1 / x45c2
#   (wrk_* は git の対象外。Run.sh・Run_MPI.sh が毎回作る)
# 構成1(Huppert)・構成4(ドーム)は平坦床 f_ztype=0 のため生成不要。
# 範囲・定数は param_ty.txt / param_wall.txt / param_cool.txt / param_run*.txt /
# Check_lava.py の期待値と対で保守する
import math
import sys

kind = sys.argv[1] if len(sys.argv) > 1 else "slope"
if kind == "x0":
    NXA, NYA, DXA, STA = 60, 20, 5.0, 0.1
    LXA = NXA * DXA
    for j in range(1, NYA + 1):
        print(" ".join("%.6f" % (STA * (LXA - (i - 0.5) * DXA))
                       for i in range(1, NXA + 1)))
elif kind == "x45":
    NB, DXB, STB = 60, 5.0, 0.1
    for j in range(1, NB + 1):
        print(" ".join("%.6f" % (STB * (2 * NB * DXB - (i + j - 1.0) * DXB) / math.sqrt(2.0))
                       for i in range(1, NB + 1)))
elif kind in ("x0c1", "x0c2"):
    js = 1 if kind == "x0c1" else 11
    for j in range(js, js + 10):
        print("%d %d" % (3, j))
elif kind in ("x45c1", "x45c2"):
    i1, i2 = (3, 16) if kind == "x45c1" else (17, 30)
    for i in range(i1, i2 + 1):
        print("%d %d" % (i, 33 - i))
elif kind == "run":
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
