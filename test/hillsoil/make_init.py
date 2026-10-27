#!/usr/bin/env python3
# test/hillsoil の入力生成(Check_hillsoil.py / param*.txt と定数を対で保守)
# 構成 wthr(W1 風化の分布。developer.md §88.13): 水のない平らな台地(NX × NY、Δx = 1 m)。
#   生成速度の倍率 m(i, j) = 0.25 ((i + 4j) mod 9)(0〜2。0 のセルを含み、並びが 9 行周期で
#   ずれるので、帯の配布の行ずれを検出できる)、初期の土層厚 sd0(i, j) = 0.1 ((2i + j) mod 4)。
#   python3 make_init.py wmap > wmap.txt        倍率の分布
#   python3 make_init.py wbad > wmap_bad.txt    1 セル(i = BAD_I, j = BAD_J)だけ負の倍率
#                                              (停止の検査。np = 4 では最後のランクの帯)
#   python3 make_init.py sd0 > sdinit.txt       初期の土層厚
# 構成 c2(C2 定常斜面。docs/mountain_stream_plan.md §11.3): 中央の列 IC が南へ勾配 C2_S で下る
#   幅 1 セルの渓流(固定床: 隆起・風化なし、土層厚 0 から)、両側 C2_L セルずつの斜面(初期は
#   渓流の底より C2_BANK 高い平らな台地、土層厚 C2_SD0)。東西の端は分水界(壁)。斜面だけが
#   隆起し風化する(倍率の分布 c2_hill.txt を fn_uplift と fn_wthr の両方に使う)。
#   python3 make_init.py c2z > c2_z.txt         地盤高
#   python3 make_init.py c2h > c2_h.txt         初期水深(渓流は等流水深 C2_H0)
#   python3 make_init.py c2sd > c2_sd.txt       初期の土層厚
#   python3 make_init.py c2hill > c2_hill.txt   斜面 1・渓流 0 の倍率
#   python3 make_init.py c2q                    渓流の等流の V0・q(param_c2*.txt の v0・inflow_val)
import sys, math

NX, NY, DX = 8, 12, 1.0
Z0 = 10.0
BAD_I, BAD_J, BAD_V = 4, 11, -0.5

C2_NX, C2_NY, C2_IC, C2_L = 11, 24, 6, 5
C2_S, C2_N, C2_Z0, C2_H0, C2_BANK, C2_SD0 = 0.01, 0.04, 10.0, 0.3, 0.5, 0.3


def wmult(i, j):
    return 0.25 * ((i + 4 * j) % 9)


def sd0(i, j):
    return 0.1 * ((2 * i + j) % 4)


def c2_zch(j):
    """渓流の底(= 固定の岩盤面)の標高"""
    return C2_Z0 + C2_S * (C2_NY - j + 0.5) * DX


def c2_z(i, j):
    return c2_zch(j) + (0.0 if i == C2_IC else C2_BANK)


def dump(fn, nx=NX, ny=NY, fmt="%.6f"):
    for j in range(1, ny + 1):
        print(" ".join(fmt % fn(i, j) for i in range(1, nx + 1)))


if __name__ == "__main__":
    kind = sys.argv[1]
    if kind == "wmap":
        dump(wmult)
    elif kind == "wbad":
        dump(lambda i, j: BAD_V if (i, j) == (BAD_I, BAD_J) else wmult(i, j))
    elif kind == "sd0":
        dump(sd0)
    elif kind == "c2z":
        dump(c2_z, C2_NX, C2_NY)
    elif kind == "c2h":
        dump(lambda i, j: C2_H0 if i == C2_IC else 0.0, C2_NX, C2_NY)
    elif kind == "c2sd":
        dump(lambda i, j: 0.0 if i == C2_IC else C2_SD0, C2_NX, C2_NY)
    elif kind == "c2hill":
        dump(lambda i, j: 0.0 if i == C2_IC else 1.0, C2_NX, C2_NY, "%.1f")
    elif kind == "c2q":
        v0 = C2_H0 ** (2.0 / 3.0) * math.sqrt(C2_S) / C2_N
        print("V0 = %.6f m/s, q = %.6f m2/s" % (v0, C2_H0 * v0))
    else:
        sys.exit("unknown kind: " + kind)
