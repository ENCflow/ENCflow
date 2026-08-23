#!/usr/bin/env python3
# test/lava の入力生成
#   zinit.txt : 等勾配斜面 tanθ=0.2(構成2 Bingham 停止・固化検定。
#               nx=100, ny=8, dx=1。z = ST*(LX - x)、x = (i-0.5)*dx)
# 構成1(Huppert)は平坦床 f_ztype=0 のため生成不要。
# 範囲・定数は param_ty.txt / Check_lava.py の期待値と対で保守する
NX, NY, DX, ST, LX = 100, 8, 1.0, 0.2, 100.0
for j in range(1, NY + 1):
    print(" ".join("%.6f" % (ST * (LX - (i - 0.5) * DX))
                   for i in range(1, NX + 1)))
