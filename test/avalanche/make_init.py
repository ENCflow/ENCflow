#!/usr/bin/env python3
# 発生区の破断深分布 dbinit.txt の生成(D=0.5m, i∈[3,10], j∈[8,13])
# 範囲・値は Check_avalanche.py の期待値と対で保守する(D = sd0 とし
# クリップ警告を出さない)
NX, NY = 60, 20
for j in range(1, NY + 1):
    print(" ".join("0.5" if (3 <= i <= 10 and 8 <= j <= 13) else "0.0"
                   for i in range(1, NX + 1)))
