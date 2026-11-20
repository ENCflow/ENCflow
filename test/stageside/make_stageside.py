#!/usr/bin/env python3
"""stageside の地形を書く(Python 標準ライブラリのみ)

ss_z.txt: 長さ 600 m・幅 40 m(120 × 8 セル、Δx = Δy = 5 m)の水路。河床は西端の −3 m から東端の
  −1.5 m へ一様に上がる(セル中心 x_i = (i − 0.5)Δx、z = −3 + 1.5 x/600。値は 0.00625 の倍数 =
  10 進 5 桁で厳密。test/wfdoppler の水路と同じ形)。南北(8 行)に一様。
使い方: python3 make_stageside.py > ss_z.txt
"""
NX, NY, DX = 120, 8, 5.0
L = NX * DX


def z(i):
    return -3.0 + 1.5 * (i + 0.5) * DX / L


for j in range(NY):
    print(" ".join("%10.5f" % z(i) for i in range(NX)))
