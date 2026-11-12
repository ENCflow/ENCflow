#!/usr/bin/env python3
# test/driftwood の集積流木の構成(param_jam*.txt)の入力生成と定数
#   (Check_woodjam.py・param_jam*.txt と定数を対で保守。標準ライブラリだけ)
#   乾いた高い地盤(+BANK)に挟まれた幅 W セルの直線水路(勾配 S、西が高い)。西端の区間流入
#   Q = q·W·DX(等流水深 H0 の流量)、東辺は自由流出。上流の列 I_ST1〜I_ST2 の水路に立木を置き、
#   水理的流失で流木にする。列 I_TRAP の水路の 4 セルを捕捉セルにする(橋・透過型堰堤の位置)。
#   python3 make_jam.py z > jam_z.txt / h > jam_h.txt / stock > jam_stock.txt / trap E > jam_trap_E.txt
import sys, math

NX, NY, DX = 160, 8, 5.0
S, N, Z0, BANK, H0, G = 0.002, 0.03, 10.0, 8.0, 2.0, 9.8
W = 4
I_ST1, I_ST2 = 21, 30               # 立木を置く列
I_TRAP = 100                        # 捕捉セルの列
STOCK = 0.02                        # 立木ストック (m3/m2)。全部で STOCK·(I_ST2−I_ST1+1)·W·DX² = 20 m3
Q_UNIT = H0 ** (5.0 / 3.0) * math.sqrt(S) / N       # 単位幅流量 (m2/s)


def rows():
    j1 = (NY - W) // 2 + 1
    return j1, j1 + W - 1


def total_stock():
    return STOCK * (I_ST2 - I_ST1 + 1) * W * DX * DX


if __name__ == "__main__":
    kind = sys.argv[1]
    e = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
    j1, j2 = rows()
    for j in range(1, NY + 1):
        ch = j1 <= j <= j2
        if kind == "z":
            print(" ".join("%.6f" % (Z0 - S * (i - 0.5) * DX + (0.0 if ch else BANK)) for i in range(1, NX + 1)))
        elif kind == "h":
            print(" ".join("%.6f" % (H0 if ch else 0.0) for i in range(1, NX + 1)))
        elif kind == "stock":
            print(" ".join("%.4f" % (STOCK if (ch and I_ST1 <= i <= I_ST2) else 0.0) for i in range(1, NX + 1)))
        elif kind == "trap":
            print(" ".join("%.4f" % (e if (ch and i == I_TRAP) else 0.0) for i in range(1, NX + 1)))
    if kind == "q":
        print("%.6f" % (Q_UNIT * W * DX))
