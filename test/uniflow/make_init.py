#!/usr/bin/env python3
# test/uniflow の入力生成(Check_uniflow.py / param*.txt と定数を対で保守)
#   乾いた高い地盤(+BANK)に挟まれた幅 W セルの直線水路(勾配 S、西が高い)。
#   西端の区間流入 Q = q·W(q は Manning の等流水深 H0 に対応する単位幅流量)、
#   東辺は自由流出。長さ 1000 m のうち下流端の低下背水(〜250 m)を避けた
#   x = 400〜700 m で等流を測る。構成 w1_sc は同じ q を勾配 S_SC の幅 1 セルの水路に流す
#   射流の区間流入(初期水深は Manning の等流水深 H_SC。developer.md §88.25)
#   python3 make_init.py z W [sc] > zinit.txt / python3 make_init.py h W [sc] > hinit.txt
import sys, math

NX, NY, DX = 1000, 20, 1.0
S, N, Z0, BANK, H0 = 0.002, 0.03, 10.0, 2.0, 0.5
Q_UNIT = H0 ** (5.0 / 3.0) * math.sqrt(S) / N      # Manning の単位幅流量 (m2/s)
X1, X2 = 400, 700                                   # 計測区間 (m)
S_SC, Z0_SC = 0.05, 60.0                            # 射流の構成の勾配・上流端の河床 (m)
H_SC = (Q_UNIT * N / math.sqrt(S_SC)) ** 0.6        # その Manning の等流水深 (m)


def rows(W):
    j1 = (NY - W) // 2 + 1
    return j1, j1 + W - 1


def z_of(i, j, W, s=S, z0=Z0):
    j1, j2 = rows(W)
    return z0 - s * (i - 0.5) * DX + (0.0 if j1 <= j <= j2 else BANK)


def h_of(i, j, W, h0=H0):
    j1, j2 = rows(W)
    return h0 if j1 <= j <= j2 else 0.0


if __name__ == "__main__":
    kind, W = sys.argv[1], int(sys.argv[2])
    sc = len(sys.argv) > 3 and sys.argv[3] == "sc"
    if kind == "z":
        fn = (lambda i, j: z_of(i, j, W, S_SC, Z0_SC)) if sc else (lambda i, j: z_of(i, j, W))
    else:
        fn = (lambda i, j: h_of(i, j, W, H_SC)) if sc else (lambda i, j: h_of(i, j, W))
    for j in range(1, NY + 1):
        print(" ".join("%.6f" % fn(i, j) for i in range(1, NX + 1)))
