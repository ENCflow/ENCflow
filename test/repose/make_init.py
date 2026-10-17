#!/usr/bin/env python3
# test/repose の入力生成(Check_repose.py / param.txt と定数を対で保守)
#   zinit.txt: 乾いた砂山(円錐。側面勾配 SLOPE0 = 1.0 = 45°、頂上 ZTOP)。
#              四周壁の閉領域、水なし。安息角 30° まで崩れる
import sys, math

NX, NY, DX = 41, 41, 1.0
ZTOP, SLOPE0 = 3.0, 1.0


def z_of(i, j):
    r = math.hypot((i - 0.5) - NX / 2.0, (j - 0.5) - NY / 2.0) * DX
    return max(0.0, ZTOP - SLOPE0 * r)


if __name__ == "__main__":
    for j in range(1, NY + 1):
        print(" ".join("%.6f" % z_of(i, j) for i in range(1, NX + 1)))
