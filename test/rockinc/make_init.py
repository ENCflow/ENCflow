#!/usr/bin/env python3
# test/rockinc の入力生成(Check_rockinc.py / param*.txt と定数を対で保守)
#   乾いた高い地盤(+BANK)に挟まれた幅 1 セルの直線水路(南北向き。北 j = 1 が高く、
#   勾配 S で南へ下る)。流れが MPI の帯界面(j 方向の分割)を横切る向きに置く。
#   1 セル幅では斜めの開口がすべて河岸で塞がれ、動的振り替え(f_opening_dynamic = 2)で
#   水も掃流砂も軸方向の全幅で流れる(等流は Manning に一致。§68.38)。
#   北端の区間流入 Q = q·W(q は Manning の等流水深 H0 の単位幅流量)、南辺は自由流出。
#   python3 make_init.py z > zinit.txt     地盤高(= 初期の岩盤面。裸岩)
#   python3 make_init.py h > hinit.txt     初期水深(水路は等流水深 H0)
#   python3 make_init.py sd0 > sdzero.txt  土層厚 0 の分布(裸岩)
#   python3 make_init.py q                 等流の V0・q・Q を表示(param*.txt の v0・inflow_val)
# 急勾配の等流(構成 steep。T9)は幅 W_ST = 5 セルの水路で勾配だけを変える:
#   python3 make_init.py zsteep S > zsteep_sXXX.txt、 python3 make_init.py hsteep > hsteep.txt
#   python3 make_init.py qsteep S
# 構成 box(T4)の侵食性倍率 fn_rock: 101 × 101 の箱で、行 BX_J1〜BX_J2(np = 2 の帯界面
# j = 51 を含む)を 0(侵食しない)、西半分の列 i <= BX_I を 0.5、ほかを 1 にする:
#   python3 make_init.py rockbox > rockmap_box.txt
import sys, math

NX, NY, DX = 3, 60, 1.0
I1, I2 = 2, 2                      # 水路の列(両側の 1 列は乾いた高い地盤)
W = I2 - I1 + 1
S, N, Z0, BANK, H0 = 0.01, 0.04, 10.0, 2.0, 0.3
V0 = H0 ** (2.0 / 3.0) * math.sqrt(S) / N          # Manning の等流流速 (m/s)
Q_UNIT = H0 * V0                                    # 単位幅流量 (m2/s)
Q = Q_UNIT * W * DX                                 # 区間流入の流量 (m3/s)

NX_ST, I1_ST, I2_ST = 7, 2, 6                       # 構成 steep の格子と水路の列
W_ST = I2_ST - I1_ST + 1
SLOPES_ST = (0.01, 0.05, 0.1, 0.2)

BX_NX, BX_NY = 101, 101                             # 構成 box の格子(test/fluvial と同じ)
BX_J1, BX_J2, BX_I = 45, 55, 50


def fr_box(i, j):
    if BX_J1 <= j <= BX_J2:
        return 0.0
    return 0.5 if i <= BX_I else 1.0


def z_of(i, j, s=S, i1=I1, i2=I2):
    return Z0 + s * NY * DX - s * (j - 0.5) * DX + (0.0 if i1 <= i <= i2 else BANK)


def h_of(i, j, i1=I1, i2=I2):
    return H0 if i1 <= i <= i2 else 0.0


def v_manning(s):
    return H0 ** (2.0 / 3.0) * math.sqrt(s) / N


def dump(nx, fn):
    for j in range(1, NY + 1):
        print(" ".join("%.6f" % fn(i, j) for i in range(1, nx + 1)))


if __name__ == "__main__":
    kind = sys.argv[1]
    if kind == "q":
        print("V0 = %.6f m/s, q = %.6f m2/s, Q = %.6f m3/s" % (V0, Q_UNIT, Q))
    elif kind == "qsteep":
        s = float(sys.argv[2])
        print("S = %.3f: V0 = %.6f m/s, Q = %.6f m3/s" % (s, v_manning(s), H0 * v_manning(s) * W_ST * DX))
    elif kind == "zsteep":
        s = float(sys.argv[2])
        dump(NX_ST, lambda i, j: z_of(i, j, s, I1_ST, I2_ST))
    elif kind == "hsteep":
        dump(NX_ST, lambda i, j: h_of(i, j, I1_ST, I2_ST))
    elif kind == "rockbox":
        for j in range(1, BX_NY + 1):
            print(" ".join("%.1f" % fr_box(i, j) for i in range(1, BX_NX + 1)))
    else:
        dump(NX, {"z": z_of, "h": h_of, "sd0": lambda i, j: 0.0}[kind])
