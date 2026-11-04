#!/usr/bin/env python3
"""湖の段の入力を作る: 氷期の段の最終の地盤高(氷を除いた岩盤の地形)を data/z_glacial.txt に書く。

  python3 prep_lakes.py      # result_glacial/Z9998.txt(最終出力)を読む

湖の段(param_lakes.txt)は、この地形に氷も雪もない状態で 1 日強い雨を降らせ、その後の
2 日で流れ去らずに残った水を湖として見る。氷河の計算は使わない(氷が消えた後の地形だけを
使う)。
"""
import os
import sys

import numpy as np

src = sys.argv[1] if len(sys.argv) > 1 else "result_glacial/Z9998.txt"
if not os.path.exists(src):
    sys.exit(f"{src} not found (run the glacial stage first: make run)")
z = np.loadtxt(src)
os.makedirs("data", exist_ok=True)
with open("data/z_glacial.txt", "w") as f:
    for row in z:
        f.write("".join(f"{v:10.2f}" for v in row) + "\n")
print(f"wrote data/z_glacial.txt from {src} (z = {z.min():.0f} .. {z.max():.0f} m)")
