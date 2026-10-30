#!/usr/bin/env python3
# test/gwlateral の入力生成(初期水深の分布。最初のステップで全量が地下へ浸透する)
#   data_gwlateral/h_gauss.txt : 構成 1。121 × 121 セルの中央にガウス形の小山
#                                h = H0 + A exp(−r² / (2 σ²))(A = 4 mm、σ = 4 m)
#   data_gwlateral/h_strip.txt : 構成 2。3 × 40 セル(南北に長い帯)に南北方向のコサイン形の
#                                起伏 h = H0 + A cos(π s / L)(L = 40 m。四周が無流束なので
#                                離散の固有関数になる。MPI の帯分割が起伏の方向に入るよう、
#                                帯を j 方向に置く)
#   セル中心は x = (i − 0.5) Δx、s = (j − 0.5) Δy(s は北端から南向き。Δx = Δy = 1 m)。
#   H0 = 0.2 m は sy0 = 0.2 で飽和帯厚 1 m。
# 値は param*.txt・Check_gwlateral.py と対で保守する
import math
import os

H0, A = 0.2, 0.004
NG, SIG = 121, 4.0          # 構成 1(中心はセル 61 の中心 = 60.5 m)
NX2, NY2 = 3, 40            # 構成 2

os.makedirs("data_gwlateral", exist_ok=True)
xc = NG * 0.5
with open("data_gwlateral/h_gauss.txt", "w") as f:
    for j in range(1, NG + 1):
        y = j - 0.5 - xc
        f.write(" ".join("%.12f" % (H0 + A * math.exp(-((i - 0.5 - xc) ** 2 + y * y) / (2 * SIG * SIG)))
                         for i in range(1, NG + 1)) + "\n")
with open("data_gwlateral/h_strip.txt", "w") as f:
    for j in range(1, NY2 + 1):
        f.write(" ".join(["%.12f" % (H0 + A * math.cos(math.pi * (j - 0.5) / NY2))] * NX2) + "\n")
