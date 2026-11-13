#!/usr/bin/env python3
# test/bankcap の入力生成と定数(Check_bankcap.py・param_*.txt と定数を対で保守。標準ライブラリだけ)
#   掘込河道(幅 W セル、勾配 S、西が高い)。北に氾濫原(河床 + D_BANK)、南に台地(河床 + D_TER)。
#   西端の河道に Q を入れ(等流水深 H0)、東辺は自由流出。初期流速に等流の流速を与える。
#   河道の水位は河岸(氾濫原の地盤)より D_BANK − H0 = 1 m 低い。氾濫原は、薄い水膜 FILM で
#   濡らす構成(wet)と、乾いた構成(dry)。
#   python3 make_bankcap.py z > bc_z.txt / rn > bc_rn.txt / h wet > bc_h_wet.txt / h dry > bc_h_dry.txt
import sys, math

NX, NY, DX = 80, 16, 5.0
S, Z0, G = 0.002, 10.0, 9.8
D_BANK, D_TER = 3.5, 7.0
J_FP2 = 8                           # 氾濫原は行 1〜J_FP2(行 1 が北)。J_FP2 = 河道に接する河岸の列
J_CH1, J_CH2 = 9, 12                # 河道の行
W = J_CH2 - J_CH1 + 1
N_CH, N_FP = 0.03, 0.05
Q = 137.3                           # 流量 (m3/s)
H0 = (Q / (W * DX) * N_CH / math.sqrt(S)) ** 0.6     # 等流水深 (m) = 2.50
U0 = Q / (W * DX * H0)              # 等流の流速 (m/s) = 2.746
FILM = 0.02                         # 氾濫原の初期の水膜 (m)


def main(kind, wet):
    for j in range(1, NY + 1):
        row = []
        for i in range(1, NX + 1):
            bed = Z0 - S * (i - 0.5) * DX
            if kind == "z":
                row.append("%.4f" % (bed + (D_BANK if j <= J_FP2 else 0.0 if j <= J_CH2 else D_TER)))
            elif kind == "rn":
                row.append("%.3f" % (N_CH if J_CH1 <= j <= J_CH2 else N_FP))
            else:
                row.append("%.4f" % ((FILM if wet else 0.0) if j <= J_FP2 else H0 if j <= J_CH2 else 0.0))
        print(" ".join(row))


if __name__ == "__main__":
    if sys.argv[1] == "consts":
        print("H0 = %.6f m, U0 = %.6f m/s, Q = %.1f m3/s" % (H0, U0, Q))
    else:
        main(sys.argv[1], len(sys.argv) > 2 and sys.argv[2] == "wet")
