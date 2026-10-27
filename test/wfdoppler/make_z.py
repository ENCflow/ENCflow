#!/usr/bin/env python3
"""wfdoppler の地形を書く(Python 標準ライブラリのみ)

z.txt: 長さ 600 m・幅 40 m(120 × 8 セル、Δx = Δy = 5 m)の水路。河床は西端の −3 m から
  東端の −1.5 m へ一様に上がる(セル中心 x_i = (i − 0.5)Δx、z = −3 + 1.5 x/600。値は
  0.00625 の倍数 = 10 進 5 桁で厳密)。流量一定の流れでは流速 U = q/h が東へ大きくなる
  (作用量の流束の保存と阻止の検定。段 W3 の V9)。
z_river.txt: 300 m × 200 m(120 × 80 セル、Δx = 2.5 m。test/wave_river と同型)。西の陸地
  (+1.5 m)を幅 10 m・河床 −1.2 m の河道(行 39〜42)が貫き、東の海(海浜勾配 0.02、沖は
  水深 2 m)に出る。河口の噴流が沖からの波を河道へ遡らせない(V10)。
"""
NX, NY, DX = 120, 8, 5.0
L = NX * DX


def z(i):
    return -3.0 + 1.5 * (i + 0.5) * DX / L


with open("z.txt", "w") as f:
    for j in range(NY):
        f.write(" ".join("%10.5f" % z(i) for i in range(NX)) + "\n")

RNX, RNY, RDX = 120, 80, 2.5
XL, ZLAND = 100.0, 1.5              # 陸地の東端 x (m)、陸地の高さ (m)
ZCH = -1.2                          # 河道の河床高 (m)
Z0, SL, ZSEA = 0.2, 0.02, 2.0       # 汀線の水深 (m)、海浜勾配、沖の水深 (m)
JC1, JC2 = 38, 42                   # 河道の行(0 始まり。JC1 <= j < JC2 = 4 行 = 10 m)


def zr(i, j):
    x = (i + 0.5) * RDX
    zz = ZLAND if x < XL else -min(Z0 + SL * (x - XL), ZSEA)
    if JC1 <= j < JC2 and zz > ZCH:
        zz = ZCH
    return zz


with open("z_river.txt", "w") as f:
    for j in range(RNY):
        f.write(" ".join("%8.4f" % zr(i, j) for i in range(RNX)) + "\n")
