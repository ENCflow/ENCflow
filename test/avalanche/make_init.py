#!/usr/bin/env python3
# 入力の生成
#   make_init.py          発生区の破断深分布 dbinit.txt を標準出力へ(構成 1)
#   make_init.py sheet    一様な斜面の一斉発生(構成 2〜5)の入力 sheet_z.txt・sheet_sd.txt・sheet_dbinit.txt を書く
# 範囲・値は Check_avalanche.py・Check_sheet.py の期待値と対で保守する(構成 1 は D = sd0 とし
# クリップ警告を出さない)
import sys

if len(sys.argv) > 1 and sys.argv[1] == "sheet":
    # 勾配 S の一様な斜面(+x が下り)に、厚さ D の雪が全面で一斉に動き出す。その下に厚さ LAYER の
    # 連行できる雪。z は雪面(基盤 + 雪)。横断方向(y)は一様
    NX, NY, DX, S, D, LAYER = 300, 20, 2.0, 0.5, 0.5, 3.0
    zrow = " ".join("%.4f" % (S * (NX * DX - (i + 0.5) * DX) + D + LAYER) for i in range(NX))
    for name, row in (("sheet_z.txt", zrow),
                      ("sheet_sd.txt", " ".join(["%.4f" % (D + LAYER)] * NX)),
                      ("sheet_dbinit.txt", " ".join(["%.4f" % D] * NX))):
        with open(name, "w") as f:
            f.write("\n".join([row] * NY) + "\n")
    sys.exit(0)

NX, NY = 60, 20
for j in range(1, NY + 1):
    print(" ".join("0.5" if (3 <= i <= 10 and 8 <= j <= 13) else "0.0"
                   for i in range(1, NX + 1)))
