#!/usr/bin/env python3
"""wfcurrent の地形 z.txt・z_rot.txt を書く(test/wfshoal と同じ断面)(Python 標準ライブラリのみ)

一様勾配 1/80 の海浜。西(i = 1)が沖、東の x = 1100 m が汀線で、その東は陸。
セル中心 x_i = (i − 0.5)Δx、z = (x − 1100)/80(Δx = 10 m なので z は 1/16 の
倍数 = 10 進 4 桁で厳密)。沖の端(i = 1)の水深は 13.6875 m。
z_rot.txt は同じ断面を時計回りに 90° 回した格子(8 列 × 120 行。北 j = 1 が沖、南が陸。
param_rot.txt。W・E の側方 Neumann と y 方向の外力の符号の検定)。
"""
NX, NY, DX = 120, 8, 10.0
XS, SLOPE = 1100.0, 1.0 / 80.0


def z(i):
    return ((i + 0.5) * DX - XS) * SLOPE


with open("z.txt", "w") as f:
    for j in range(NY):
        f.write(" ".join("%9.4f" % z(i) for i in range(NX)) + "\n")

with open("z_rot.txt", "w") as f:
    for i in range(NX):
        f.write(" ".join("%9.4f" % z(i) for _ in range(NY)) + "\n")
