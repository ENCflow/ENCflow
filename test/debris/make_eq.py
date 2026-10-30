#!/usr/bin/env python3
# test/debris 構成 7(param_eq.txt)の入力生成: 勾配の違う 6 本の水路(斜面等流の平衡濃度)
#   南北に長い幅 1 セルの水路を列 i = 2, 4, …, 12 に置き、間と両外側の列は両隣の水路より
#   2 m 高い乾いた地盤。水路 k の河床は z = Z0 − tanθ_k (j − 0.5) Δy(北が高い)。初期水深は
#   水路だけ H0(土砂なし)
#   python3 make_eq.py z > z_eq.txt / python3 make_eq.py h > h_eq.txt
# 勾配・水深は param_eq.txt・Check_debris_eq.py と対で保守する
import sys

TAN = [0.60, 0.25, 0.15, 0.10, 0.05, 0.02]       # 水路 1〜6 の tanθ
NY, Z0, BANK, H0 = 300, 200.0, 2.0, 0.05
NX = 2 * len(TAN) + 1

if __name__ == "__main__":
    kind = sys.argv[1]
    for j in range(1, NY + 1):
        zc = [Z0 - t * (j - 0.5) for t in TAN]
        row = []
        for i in range(1, NX + 1):
            if i % 2 == 0:
                row.append(zc[i // 2 - 1] if kind == "z" else H0)
            else:
                nb = [zc[k] for k in (i // 2 - 1, i // 2) if 0 <= k < len(TAN)]
                row.append(max(nb) + BANK if kind == "z" else 0.0)
        print(" ".join("%.6f" % v for v in row))
