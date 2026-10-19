#!/usr/bin/env python3
# examples/meander の入力生成: 氾濫原の中の正弦波状の初期河道
#   z.txt  地盤高(河床は路長に沿って勾配 S0。両岸(氾濫原)は河床 + BANK)
#   h.txt  初期水深(河道内 H0、氾濫原 0)
#   sd.txt 土層厚(上流端・下流端の帯は 0 = 非侵食。他は SD)
import sys, math
NX, NY, DX = 400, 120, 2.0        # 800 m × 240 m
W, A0, LAM = 20.0, 10.0, 200.0    # 河道幅、初期振幅、波長 (m)
S0, Z0, BANK, H0, SD = 0.001, 10.0, 1.0, 0.8, 5.0
XFIX_UP, XFIX_DN = 30.0, 30.0     # 非侵食帯の長さ(上流・下流)
YC = NY * DX / 2.0
LSTR = 100.0                      # 上流の直線部(振幅は 0 から滑らかに立ち上がる)
LEND = 100.0                      # 下流の直線部(振幅は滑らかに 0 へ。出口は直線で東辺へ)

def yc_of(x):
    if x < LSTR:
        return YC
    xe = NX * DX - LEND
    ramp = min(1.0, (x - LSTR) / LAM) * (1.0 if x < xe else max(0.0, 1.0 - (x - xe) / LAM))
    return YC + A0 * ramp * math.sin(2 * math.pi * (x - LSTR) / LAM)

def cell(i, j):
    x = (i - 0.5) * DX; y = (j - 0.5) * DX
    return x, y - yc_of(x)

def z_of(i, j):
    x, n = cell(i, j)
    zb = Z0 - S0 * x
    return zb if abs(n) <= W / 2 else zb + BANK

def h_of(i, j):
    x, n = cell(i, j)
    return H0 if abs(n) <= W / 2 else 0.0

LRAMP = 300.0                     # 土層厚のランプ長(上流端のナックポイント穴を岩盤で止める)

def sd_of(i, j):
    x, n = cell(i, j)
    if x > NX * DX - XFIX_DN:
        return 0.0
    return SD * min(1.0, max(0.0, (x - XFIX_UP) / LRAMP))


def sdfeed_of(i, j):
    # 給砂構成(param_feed.txt): 上流端まで可動(容量給砂 fluv_bcfeed = 1 が入口の
    # 河床を固定するので、非侵食帯とランプは要らない)。下流端だけ非侵食
    x, n = cell(i, j)
    return 0.0 if x > NX * DX - XFIX_DN else SD

def rows_in(i):
    return [j for j in range(1, NY + 1) if h_of(i, j) > 0]

if __name__ == "__main__":
    kind = sys.argv[1]
    if kind == "rows":
        print(" ".join(str(j) for j in rows_in(1))); sys.exit(0)
    fn = {"z": z_of, "h": h_of, "sd": sd_of, "sdfeed": sdfeed_of}[kind]
    for j in range(1, NY + 1):
        print(" ".join("%.4f" % fn(i, j) for i in range(1, NX + 1)))
