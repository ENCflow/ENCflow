#!/usr/bin/env python3
# test/bankface の入力生成(Check_bankface.py / param*.txt と定数を対で保守)
#   zinit.txt: 幅 NW セルの直線水路(河床勾配 S、西が高い)の両側に、河床より
#              BANK 高い乾いた河岸(氾濫原)を置く。四周は壁(閉領域)
#   hinit.txt: 水路内だけに水。上流半分 H_UP、下流半分 H_DN のダム破壊型。
#              河岸は乾燥(h = 0)
#   python3 make_init.py z > zinit.txt / python3 make_init.py h > hinit.txt
import sys

NX, NY, DX = 60, 20, 1.0
J1, J2 = 6, 15                 # 水路の行範囲(1 始まり)
S, Z0, BANK = 0.002, 10.0, 2.0
H_UP, H_DN, I_DAM = 1.0, 0.2, 30


def in_channel(j):
    return J1 <= j <= J2


def z_of(i, j):
    zb = Z0 - S * (i - 0.5) * DX
    return zb if in_channel(j) else zb + BANK


def h_of(i, j):
    if not in_channel(j):
        return 0.0
    return H_UP if i <= I_DAM else H_DN


if __name__ == "__main__":
    kind = sys.argv[1] if len(sys.argv) > 1 else "z"
    fn = z_of if kind == "z" else h_of
    for j in range(1, NY + 1):
        print(" ".join("%.6f" % fn(i, j) for i in range(1, NX + 1)))
