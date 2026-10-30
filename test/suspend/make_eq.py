#!/usr/bin/env python3
# test/suspend 構成 3(param_eq.txt)の入力生成: 南北に長い幅 1 セルの直線水路
#   z = Z0 − S (j − 0.5) Δy(北が高い)。水路は中央の列 i = 2、両側の列は河床 +BANK の
#   乾いた地盤。初期水深は水路だけ Manning の等流水深 H0。北端の区間流入 Q = q·Δx
#   (q は H0 に対応する単位幅流量)、南辺は自由流出
#   python3 make_eq.py z > zinit_eq.txt / python3 make_eq.py h > hinit_eq.txt
# 定数は param_eq.txt・Check_suspend.py と対で保守する
import math
import sys

NX, NY, DX = 3, 1000, 1.0
S, N, Z0, BANK, H0 = 0.002, 0.03, 10.0, 2.0, 0.5
Q_UNIT = H0 ** (5.0 / 3.0) * math.sqrt(S) / N      # Manning の単位幅流量 (m2/s)

if __name__ == "__main__":
    kind = sys.argv[1]
    for j in range(1, NY + 1):
        zc = Z0 - S * (j - 0.5) * DX
        if kind == "z":
            row = [zc + BANK, zc, zc + BANK]
        elif kind == "h":
            row = [0.0, H0, 0.0]
        else:
            print("%.6f" % Q_UNIT)
            sys.exit(0)
        print(" ".join("%.6f" % v for v in row))
