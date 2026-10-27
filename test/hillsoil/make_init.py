#!/usr/bin/env python3
# test/hillsoil の入力生成(Check_hillsoil.py / param*.txt と定数を対で保守)
# 構成 wthr(W1 風化の分布。developer.md §88.13): 水のない平らな台地(NX × NY、Δx = 1 m)。
#   生成速度の倍率 m(i, j) = 0.25 ((i + 4j) mod 9)(0〜2。0 のセルを含み、並びが 9 行周期で
#   ずれるので、帯の配布の行ずれを検出できる)、初期の土層厚 sd0(i, j) = 0.1 ((2i + j) mod 4)。
#   python3 make_init.py wmap > wmap.txt        倍率の分布
#   python3 make_init.py wbad > wmap_bad.txt    1 セル(i = BAD_I, j = BAD_J)だけ負の倍率
#                                              (停止の検査。np = 4 では最後のランクの帯)
#   python3 make_init.py sd0 > sdinit.txt       初期の土層厚
import sys

NX, NY, DX = 8, 12, 1.0
Z0 = 10.0
BAD_I, BAD_J, BAD_V = 4, 11, -0.5


def wmult(i, j):
    return 0.25 * ((i + 4 * j) % 9)


def sd0(i, j):
    return 0.1 * ((2 * i + j) % 4)


def dump(fn):
    for j in range(1, NY + 1):
        print(" ".join("%.6f" % fn(i, j) for i in range(1, NX + 1)))


if __name__ == "__main__":
    kind = sys.argv[1]
    if kind == "wmap":
        dump(wmult)
    elif kind == "wbad":
        dump(lambda i, j: BAD_V if (i, j) == (BAD_I, BAD_J) else wmult(i, j))
    elif kind == "sd0":
        dump(sd0)
    else:
        sys.exit("unknown kind: " + kind)
