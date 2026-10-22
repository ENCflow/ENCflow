#!/usr/bin/env python3
# test/rockfall の入力生成(Check_rockfall.py / param.txt と定数を対で保守)
#   zinit.txt: 平地(z = 0)の上の四角い台地(一辺 2 HALF、高さ ZTOP。垂直な自由面)。
#              四周壁の閉領域、水なし。自由面 ZTOP > 限界高さ H_c なので崩落し、
#              落下分が崖錐(安息角 PHI)として裾に広がる
import sys

NX, NY, DX = 41, 41, 1.0
ZTOP, HALF = 10.0, 10.0


def z_of(i, j):
    x = (i - 0.5) * DX - NX / 2.0
    y = (j - 0.5) * DX - NY / 2.0
    return ZTOP if (abs(x) <= HALF and abs(y) <= HALF) else 0.0


if __name__ == "__main__":
    for j in range(1, NY + 1):
        print(" ".join("%.6f" % z_of(i, j) for i in range(1, NX + 1)))
