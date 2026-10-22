#!/usr/bin/env python3
# wave_shore 検定の入力: 一様勾配の水没した海浜(北が浅い)に正弦波状の等深線の擾乱
#   z = -Z0 - S (y - a sin(2 pi x / L))。全域が湿潤(水位 0)なので「汀線」は等深線で測る。
#   python3 make_init.py z > zinit.txt / sd > sdinit.txt
import sys
import numpy as np
NX, NY, DX = 320, 96, 2.5        # 800 m x 240 m
Z0, S, A, L = 0.2, 0.02, 6.0, 200.0   # 北端の水深 (m)、海底勾配、擾乱振幅 (m)、波長 (m)
SD = 10.0

def fields():
    x = (np.arange(NX) + 0.5) * DX
    y = (np.arange(NY) + 0.5) * DX
    X, Y = np.meshgrid(x, y)
    eta = A * np.sin(2 * np.pi * X / L)
    z = -Z0 - S * (Y - eta)
    sd = np.full_like(z, SD)
    return z, sd

if __name__ == "__main__":
    z, sd = fields()
    np.savetxt(sys.stdout, {"z": z, "sd": sd}[sys.argv[1]], fmt="%.4f")
