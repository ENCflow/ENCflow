#!/usr/bin/env python3
# test/sedfeed の入力生成(Check_sedfeed.py / param*.txt と定数を対で保守)
#   乾いた高い地盤(+BANK)に挟まれた幅 W セルの直線水路(勾配 S、西が高い)。
#   河床は全域可動(土層厚 sd0 は param)。西端の区間流入 Q = q·W(q は Manning の
#   等流水深 H0 の単位幅流量)、東辺は自由流出(qb 構成は壁)。
#   python3 make_init.py z > zinit.txt / python3 make_init.py h > hinit.txt
#   qbturn 構成: 流入セルの東隣(i = TURN_I)の行 TURN_J1〜J2 を乾いた高い地盤(+BANK)にして、
#   流入した水を北の 2 行へ曲げる(流入セルで流れが横に振れる。developer.md §19.12)
#   python3 make_init.py zturn > zturn.txt / python3 make_init.py hturn > hturn.txt
import sys, math

NX, NY, DX = 300, 16, 1.0
W = 5
J1, J2 = 6, 10
S, N, Z0, BANK, H0 = 0.002, 0.03, 10.0, 2.0, 0.5
Q_UNIT = H0 ** (5.0 / 3.0) * math.sqrt(S) / N      # Manning の単位幅流量 (m2/s)
X1, X2 = 20, 120                                    # 上流区間(給砂の効果を見る)
X3, X4 = 150, 200                                   # 参照区間
TURN_I, TURN_J1 = 2, J1 + 2                         # qbturn の高い地盤(列 TURN_I、行 TURN_J1〜J2)


def z_of(i, j):
    return Z0 - S * (i - 0.5) * DX + (0.0 if J1 <= j <= J2 else BANK)


def h_of(i, j):
    return H0 if J1 <= j <= J2 else 0.0


def blocked(i, j):
    return i == TURN_I and TURN_J1 <= j <= J2


def z_turn(i, j):
    return z_of(i, j) + (BANK if blocked(i, j) else 0.0)


def h_turn(i, j):
    return 0.0 if blocked(i, j) else h_of(i, j)


if __name__ == "__main__":
    kind = sys.argv[1]
    fn = {"z": z_of, "h": h_of, "zturn": z_turn, "hturn": h_turn}[kind]
    for j in range(1, NY + 1):
        print(" ".join("%.6f" % fn(i, j) for i in range(1, NX + 1)))
