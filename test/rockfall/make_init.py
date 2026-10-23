#!/usr/bin/env python3
# test/rockfall の入力生成(Check_rockfall.py / param.txt と定数を対で保守)
#   zinit.txt: 平地(z = 0)の上の四角い台地(一辺 2 HALF、高さ ZTOP。垂直な自由面)。
#              四周壁の閉領域、水なし。自由面 ZTOP > 限界高さ H_c なので崩落し、
#              落下分が崖錐(安息角 PHI)として裾に広がる
#   --sea: 西側(x < XSEA)を海セル(sw = 1、z = 0)にし、台地の西壁が海に面する構成
#          (zinit_sea.txt / sw_sea.txt)。海へ落ちた分は系外へ出る(台帳 vsea)
#   --sdzero: 土層厚 0 の地図 sd_zero.txt(基岩版 rf_bedrock = 1。一様値 sd0 = 0 は
#          list_geoinfo が受け付けないのでファイルで与える)
import sys

NX, NY, DX = 41, 41, 1.0
ZTOP, HALF = 10.0, 10.0
XSEA = 10.0     # --sea: x < XSEA を海セルにする(台地の西端 x = NX/2 − HALF = 10.5 に接する)


def z_of(i, j):
    x = (i - 0.5) * DX - NX / 2.0
    y = (j - 0.5) * DX - NY / 2.0
    return ZTOP if (abs(x) <= HALF and abs(y) <= HALF) else 0.0


def sea_of(i, j):
    return 1 if (i - 0.5) * DX < XSEA else 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--sdzero":
        with open("sd_zero.txt", "w") as f:
            for j in range(1, NY + 1):
                f.write(" ".join("0.0" for i in range(1, NX + 1)) + "\n")
    elif len(sys.argv) > 1 and sys.argv[1] == "--sea":
        with open("zinit_sea.txt", "w") as f:
            for j in range(1, NY + 1):
                f.write(" ".join("%.6f" % (0.0 if sea_of(i, j) else z_of(i, j)) for i in range(1, NX + 1)) + "\n")
        with open("sw_sea.txt", "w") as f:
            for j in range(1, NY + 1):
                f.write(" ".join("%d" % sea_of(i, j) for i in range(1, NX + 1)) + "\n")
    else:
        for j in range(1, NY + 1):
            print(" ".join("%.6f" % z_of(i, j) for i in range(1, NX + 1)))
