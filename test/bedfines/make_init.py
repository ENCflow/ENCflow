#!/usr/bin/env python3
# test/bedfines の channel 構成の入力生成(Check_bedfines.py / param_feed.txt と定数を対で保守)
#   zinit.txt: 幅 NW = J2−J1+1 セルの直線水路(河床勾配 S、西が高い)。両側は河床より
#              BANK 高い乾いた河岸。東辺は自由流出(param の f_bc_e)
#   hinit.txt: 水路内に等流相当の初期水深 H0。河岸は乾燥
#   sdinit.txt: 土層厚。流入端の I_FIX 列は 0(非侵食)、I_RAMP 列まで線形に SD0 へ、
#              I_END 列から I_DOWN 列へ 0 に戻す(自由流出面の洗掘を止める)
#   python3 make_init.py z > zinit.txt / h > hinit.txt / sd > sdinit.txt
import sys

NX, NY, DX = 60, 20, 1.0
J1, J2 = 6, 15                 # 水路の行範囲(1 始まり)
S, Z0, BANK = 0.002, 10.0, 2.0
H0 = 0.3                       # 初期水深
SD0, I_FIX, I_RAMP = 10.0, 5, 25
I_END, I_DOWN = 50, 55


def in_channel(j):
    return J1 <= j <= J2


def z_of(i, j):
    zb = Z0 - S * (i - 0.5) * DX
    return zb if in_channel(j) else zb + BANK


def h_of(i, j):
    return H0 if in_channel(j) else 0.0


def sd_of(i, j):
    if i <= I_FIX or i >= I_DOWN:
        return 0.0
    return SD0 * min(1.0, (i - I_FIX) / float(I_RAMP - I_FIX), (I_DOWN - i) / float(I_DOWN - I_END))


if __name__ == "__main__":
    kind = sys.argv[1] if len(sys.argv) > 1 else "z"
    fn = {"z": z_of, "h": h_of, "sd": sd_of}[kind]
    for j in range(1, NY + 1):
        print(" ".join("%.6f" % fn(i, j) for i in range(1, NX + 1)))
