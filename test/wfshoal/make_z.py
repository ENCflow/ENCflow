#!/usr/bin/env python3
"""wfshoal の地形 z.txt を書く(Python 標準ライブラリのみ)

一様勾配 1/80 の海浜。西(i = 1)が沖、東の x = 1100 m が汀線で、その東は陸。
セル中心 x_i = (i − 0.5)Δx、z = (x − 1100)/80(Δx = 10 m なので z は 1/16 の
倍数 = 10 進 4 桁で厳密)。沖の端(i = 1)の水深は 13.6875 m。
"""
NX, NY, DX = 120, 8, 10.0
XS, SLOPE = 1100.0, 1.0 / 80.0

with open("z.txt", "w") as f:
    for j in range(NY):
        f.write(" ".join("%9.4f" % (((i + 0.5) * DX - XS) * SLOPE) for i in range(NX)) + "\n")
