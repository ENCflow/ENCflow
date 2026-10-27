#!/usr/bin/env python3
"""wfshadow の地形 z.txt を書く(Python 標準ライブラリのみ)

100 × 100 セル(Δx = Δy = 10 m)、水深 10 m で一様(z = −10 m)。陸(z = +3 m)は
  - 防波堤: 行 j = 60、列 i = 1..50(西の辺から延びる 1 セル厚の堤。先端は (50, 60))
  - 菱形: |i − 75| + |j − 30| = 8 のセル(角だけで接する斜めの 1 セル厚の壁が水域を囲む)
添字は 1 始まり、j は南向き(z.txt の 1 行目が北の端)。
"""
NX = NY = 100


def land(i, j):
    if j == 60 and i <= 50:
        return True
    return abs(i - 75) + abs(j - 30) == 8


with open("z.txt", "w") as f:
    for j in range(1, NY + 1):
        f.write(" ".join("%5.1f" % (3.0 if land(i, j) else -10.0) for i in range(1, NX + 1)) + "\n")
