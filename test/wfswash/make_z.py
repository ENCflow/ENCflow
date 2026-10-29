#!/usr/bin/env python3
"""wfswash の地形を書く(Python 標準ライブラリのみ)

断面(南北に一様な N-S の汀線。60 列 × NY 行、Δx = Δy = 5 m。西 i = 1 が沖、東が陸):
  z_mild.txt  一様勾配 1/40(平衡勾配 0.1 より緩い)。z_i = (i − 44.5)/8(i は 0 始まり。
              0.125 の倍数 = 2 進で厳密)。汀線は i = 44(z = −0.0625)と i = 45(+0.0625)の間
  z_eq.txt    前浜(i >= 41)を平衡勾配 0.1(1 セル 0.5 m)、沖を 1/40。z_44 = −0.25、z_45 = 0.25
  z_steep.txt 前浜(i >= 41)を 0.15(1 セル 0.75 m)、沖を 1/40。z_44 = −0.5、z_45 = 0.25
  z_cliff16.txt  z_eq の汀線の陸側(i >= 45)を崖にする(z_45 = 2.0、その先は 0.5/セル)。崖の上端は
              遡上の上限(汀線セルの中央差分の勾配 0.275 で R ≒ 1.19 m)より高い = 遡上域がない
  z_diag.txt  60 × 60 の正方形で等深線が 45°(汀線は北西 → 南東の向きに陸)。z = (s − 64.5) δ、
              s = i + j(0 始まり)、δ = Δx tanβ/√2(tanβ = 1/40)。軸に沿う汀線の z_mild と同じ
              勾配・同じ汀線の高さ(z_d = δ/2 ≒ 0.0442 に近い)の 45° 版
使い方: python3 make_z.py(行数は 8 = mild・eq・steep、16 = eq16・cliff16、60 = diag)
"""
import math
import sys

NX, DX = 60, 5.0


def mild(i):
    return (i - 44.5) / 8.0


def eq(i):
    if i >= 41:
        return 0.25 + 0.5 * (i - 45)
    return -1.75 - 0.125 * (41 - i)


def steep(i):
    if i >= 41:
        return 0.25 + 0.75 * (i - 45)
    return -2.75 - 0.125 * (41 - i)


def cliff(i):
    if i >= 45:
        return 2.0 + 0.5 * (i - 45)
    return eq(i)


def write(name, f, ny):
    with open(name, "w") as fo:
        for _ in range(ny):
            fo.write(" ".join("%9.4f" % f(i) for i in range(NX)) + "\n")


write("z_mild.txt", mild, 8)
write("z_eq.txt", eq, 8)
write("z_eq16.txt", eq, 16)
write("z_steep.txt", steep, 8)
write("z_cliff16.txt", cliff, 16)

delta = DX * (1.0 / 40.0) / math.sqrt(2.0)
with open("z_diag.txt", "w") as fo:
    for j in range(NX):
        fo.write(" ".join("%12.8f" % ((i + j - 64.5) * delta) for i in range(NX)) + "\n")
