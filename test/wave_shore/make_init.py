#!/usr/bin/env python3
# wave_shore 検定の入力: 一様勾配 S の海浜(北が陸)に正弦波状の汀線の擾乱
#   z = -S (y - YL - a sin(2 pi x / L))。水位 0 なので y < YL + η は乾いた浜(z > 0)、
#   南へ深くなる。汀線は領域の内側にある(領域の縁の扱いに依らない)ので、検定は
#   等深線(h = 0.5 m と 0.8 m)の位置で測る。
#   bar 構成(段 3 (b) の検定): 擾乱のない直線汀線の沖に水没砂州(x = XB1〜XB2、y = YB1〜YB2、
#   天端の水深 HBAR、非侵食 = 水没離岸堤)を置く。遮蔽ありでは砂州の陰の浜に舌状砂州(サリエント)ができる。
#   python3 make_init.py z > zinit.txt / sd > sdinit.txt /  z bar > zinit_bar.txt / sd bar > sdinit_bar.txt
import sys
import numpy as np
NX, NY, DX = 320, 96, 2.5        # 800 m x 240 m
YL, S, A, L = 20.0, 0.02, 6.0, 200.0  # 汀線の位置 y (m)、海底勾配、擾乱振幅 (m)、波長 (m)
SD = 10.0
XB1, XB2, YB1, YB2, HBAR = 350.0, 450.0, 45.0, 55.0, 0.2   # 水没砂州の範囲 (m) と天端の水深 (m)

def fields(bar=False):
    x = (np.arange(NX) + 0.5) * DX
    y = (np.arange(NY) + 0.5) * DX
    X, Y = np.meshgrid(x, y)
    eta = 0.0 if bar else A * np.sin(2 * np.pi * X / L)
    z = -S * (Y - YL - eta)
    if bar:
        inb = (X >= XB1) & (X < XB2) & (Y >= YB1) & (Y < YB2)
        z = np.where(inb, -HBAR, z)
    sd = np.full_like(z, SD)
    if bar:
        sd = np.where(inb, 0.0, sd)          # 砂州は非侵食(水没離岸堤)。遮蔽の効果を持続させる
    return z, sd

if __name__ == "__main__":
    z, sd = fields(bar=(len(sys.argv) > 2 and sys.argv[2] == "bar"))
    np.savetxt(sys.stdout, {"z": z, "sd": sd}[sys.argv[1]], fmt="%.4f")
