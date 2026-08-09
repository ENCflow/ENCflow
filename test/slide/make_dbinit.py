#!/usr/bin/env python3
# 崩壊深分布 dbinit.txt の生成(D=1m, i∈[5,15], j∈[5,16])
# 範囲は Check_slide.py の水収支・活性検定の期待値と対で保守する
NX, NY = 60, 20
for j in range(1, NY + 1):
    print(" ".join("1.0" if (5 <= i <= 15 and 5 <= j <= 16) else "0.0"
                   for i in range(1, NX + 1)))
