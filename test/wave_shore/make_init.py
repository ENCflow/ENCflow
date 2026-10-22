#!/usr/bin/env python3
# wave_shore 検定の入力: 一様勾配 S の海浜(北が陸)に正弦波状の汀線の擾乱
#   z = -S (y - YL - a sin(2 pi x / L))。水位 0 なので y < YL + η は乾いた浜(z > 0)、
#   南へ深くなる。汀線は領域の内側にある(領域の縁の扱いに依らない)ので、検定は
#   等深線(h = 0.5 m と 0.8 m)の位置で測る。
#   python3 make_init.py z > zinit.txt / sd > sdinit.txt
import sys
import numpy as np
NX, NY, DX = 320, 96, 2.5        # 800 m x 240 m
YL, S, A, L = 20.0, 0.02, 6.0, 200.0  # 汀線の位置 y (m)、海底勾配、擾乱振幅 (m)、波長 (m)
SD = 10.0

def fields():
    x = (np.arange(NX) + 0.5) * DX
    y = (np.arange(NY) + 0.5) * DX
    X, Y = np.meshgrid(x, y)
    eta = A * np.sin(2 * np.pi * X / L)
    z = -S * (Y - YL - eta)
    sd = np.full_like(z, SD)
    return z, sd

if __name__ == "__main__":
    z, sd = fields()
    np.savetxt(sys.stdout, {"z": z, "sd": sd}[sys.argv[1]], fmt="%.4f")
