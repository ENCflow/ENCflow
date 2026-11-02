#!/usr/bin/env python3
# test/taupart の入力生成(Check_taupart.py / param*.txt と定数を対で保守)
#   乾いた高い地盤(+BANK)に挟まれた幅 1 セル(行 JC)の急勾配(S)の直線水路(西が高い)。
#   西端の区間流入 Q_UNIT × 1 m(test/uniflow の射流の構成と同じ単位幅流量。Manning の等流水深 H0)、
#   東辺は自由流出。下流端の影響と上流端の河床低下波を避けた x = X1〜X2 で等流と流砂を測る。
#   python3 make_init.py z > zinit.txt / python3 make_init.py h > hinit.txt
import sys, math

NX, NY, DX = 500, 8, 1.0
S, N, Z0, BANK = 0.05, 0.03, 40.0, 2.0
Q_UNIT = 0.469545                                   # 単位幅流量 (m2/s)
H0 = (Q_UNIT * N / math.sqrt(S)) ** 0.6             # Manning の等流水深 (m)(0.190)
X1, X2 = 250, 400                                   # 計測区間 (m)
JC = 4                                              # 水路の行(1 始まり。両側の乾いた行は MPI の分割のため)


def z_of(i, j):
    return Z0 - S * (i - 0.5) * DX + (0.0 if j == JC else BANK)


def h_of(i, j):
    return H0 if j == JC else 0.0


if __name__ == "__main__":
    fn = z_of if sys.argv[1] == "z" else h_of
    for j in range(1, NY + 1):
        print(" ".join("%.6f" % fn(i, j) for i in range(1, NX + 1)))
