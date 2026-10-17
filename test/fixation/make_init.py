#!/usr/bin/env python3
# test/fixation の入力生成(Check_fixation.py / param*.txt と定数を対で保守)
#   zinit.txt: 幅 NW = J2−J1+1 セルの直線水路(河床勾配 S、西が高い)。南側
#              JB1..JB2 の 3 行は河床より BAR 高い砂州(低水時は乾く)。両側は
#              河床より BANK 高い乾いた河岸。東辺は自由流出(param の f_bc_e)
#   hinit.txt: 砂州を除く水路内に低水の等流水深 H_LOW。砂州・河岸は乾燥
#   sdinit.txt: 土層厚。流入端の I_FIX 列は 0(非侵食)、I_RAMP 列まで線形に
#              SD0 へ(無給砂の流入端の段差に穴が育つのを岩盤で止める)、
#              I_END 列から I_DOWN 列へ 0 に戻す(自由流出面の洗掘を止める)。
#              検定は I_RAMP < i < I_END の区間だけを見る
#   python3 make_init.py z > zinit.txt / h > hinit.txt / sd > sdinit.txt
import sys

NX, NY, DX = 60, 20, 1.0
J1, J2 = 6, 15                 # 水路の行範囲(1 始まり)
JB1, JB2 = 13, 15              # 砂州の行範囲(水路内の南側 3 行)
S, Z0, BANK, BAR = 0.002, 10.0, 2.0, 0.1
H_LOW = 0.06                   # 低水の初期水深(砂州の高さ BAR より浅い)
SD0, I_FIX, I_RAMP = 10.0, 5, 25   # 土層厚、非侵食の流入端の列数、ランプの終端列
I_END, I_DOWN = 50, 55         # 下流端のランプ開始列と非侵食の開始列(自由流出面の洗掘を止める)


def in_channel(j):
    return J1 <= j <= J2


def on_bar(j):
    return JB1 <= j <= JB2


def z_of(i, j):
    zb = Z0 - S * (i - 0.5) * DX
    if not in_channel(j):
        return zb + BANK
    return zb + BAR if on_bar(j) else zb


def h_of(i, j):
    return H_LOW if (in_channel(j) and not on_bar(j)) else 0.0


def sd_of(i, j):
    if i <= I_FIX or i >= I_DOWN:
        return 0.0
    return SD0 * min(1.0, (i - I_FIX) / float(I_RAMP - I_FIX), (I_DOWN - i) / float(I_DOWN - I_END))


if __name__ == "__main__":
    kind = sys.argv[1] if len(sys.argv) > 1 else "z"
    fn = {"z": z_of, "h": h_of, "sd": sd_of}[kind]
    for j in range(1, NY + 1):
        print(" ".join("%.6f" % fn(i, j) for i in range(1, NX + 1)))
