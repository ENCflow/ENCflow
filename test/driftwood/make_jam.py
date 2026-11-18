#!/usr/bin/env python3
# test/driftwood の集積流木の構成(param_jam*.txt)の入力生成と定数
#   (Check_woodjam.py・param_jam*.txt と定数を対で保守。標準ライブラリだけ)
#   乾いた高い地盤(+BANK)に挟まれた幅 W セルの直線水路(勾配 S、西が高い)。西端の区間流入
#   Q = q·W·DX(等流水深 H0 の流量)、東辺は自由流出。上流の列 I_ST1〜I_ST2 の水路に立木を置き、
#   水理的流失で流木にする。列 I_TRAP の水路の 4 セルを捕捉セルにする(橋・透過型堰堤の位置)。
#   python3 make_jam.py z > jam_z.txt / h > jam_h.txt / stock > jam_stock.txt / trap E > jam_trap_E.txt
#   構成 6(カルバート): python3 make_jam.py cz > jam_cz.txt / ch > jam_ch.txt /
#                         cstock > jam_cstock.txt / cstock3 > jam_cstock3.txt / cstage > jam_cstage.txt
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


# ---- 構成 6(カルバートの流入口の集積。param_jamculv*.txt): test/culvert と同じ排水試験の配置
#   平坦な上流槽 10 × 11 セル(Δx = 10 m)の水深 3 m を、盛土(列 11)を横断する 1 m × 1 m の
#   カルバート (10,6) → (12,6) だけで排水する。下流の列 12 は完全排水口(水位規定)。
#   cstock: 流入口のセル (10,6) に立木 C_STOCK (m3/m2) を置く(全部で 0.5 m3。大きい集積)
#   cstock3: 取水セル群を 3 セル (10,5)・(10,6)・(10,7) にした構成用。3 セルに C_STOCK3 ずつ
#            (全部で 0.06 m3。小さい集積 = 満管と堰の両方のレジームを通る)
C_NX, C_NY, C_DX = 12, 11, 10.0
C_H0, C_BW, C_D, C_CE = 3.0, 1.0, 1.0, 0.5
C_IN = (10, 6)
C_IN3 = ((10, 6), (10, 5), (10, 7))
C_STOCK, C_STOCK3 = 0.005, 0.0002
C_ATOT, C_AUP = C_NX * C_NY * C_DX * C_DX, 10 * C_NY * C_DX * C_DX


def culv_main(kind):
    for j in range(1, C_NY + 1):
        if kind == "cz":
            print(" ".join("10.0" if i == 11 else "0.0" for i in range(1, C_NX + 1)))
        elif kind == "ch":
            print(" ".join("%.1f" % (C_H0 if i <= 10 else 0.0) for i in range(1, C_NX + 1)))
        elif kind == "cstock":
            print(" ".join("%.4f" % (C_STOCK if (i, j) == C_IN else 0.0) for i in range(1, C_NX + 1)))
        elif kind == "cstock3":
            print(" ".join("%.4f" % (C_STOCK3 if (i, j) in C_IN3 else 0.0) for i in range(1, C_NX + 1)))
        elif kind == "cstage":
            print("%d %d" % (C_NX, j))


if __name__ == "__main__":
    kind = sys.argv[1]
    if kind in ("cz", "ch", "cstock", "cstock3", "cstage"):
        culv_main(kind)
        sys.exit(0)
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
