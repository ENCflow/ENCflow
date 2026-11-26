#!/usr/bin/env python3
# =====================================================================
# bmi_dam: 入力データの生成(data_bmi_dam/mask.txt・z.txt)
#   領域 24 × 10 セル(dx = dy = 10 m)。i = 2 の列に孤立した 1 セルの捕捉帯を
#   4 つ(j = 2, 4, 6, 8)置き、周りの 8 近傍をすべて領域外(マスク 0)にする。
#   i = 5〜24 は放流を受ける平坦な閉じた池(四周は壁)。捕捉帯は流れのやり取りを
#   しないので、内部ソースで入れた水は次の歩に全量が吸収される(test/damops と同じ形)。
#   使い方: python3 make_data.py
# =====================================================================
import os

nx, ny = 24, 10
capture = [(2, 2), (2, 4), (2, 6), (2, 8)]   # (i, j)。1 始まり
d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_bmi_dam")
os.makedirs(d, exist_ok=True)
mask = [[0] * nx for _ in range(ny)]
for j in range(ny):
    for i in range(4, nx):
        mask[j][i] = 1
for (i, j) in capture:
    mask[j - 1][i - 1] = 1
with open(os.path.join(d, "mask.txt"), "w") as f:
    for row in mask:
        f.write(" ".join(str(v) for v in row) + "\n")
with open(os.path.join(d, "z.txt"), "w") as f:
    for _ in range(ny):
        f.write(" ".join("0.0" for _ in range(nx)) + "\n")
print("wrote", d)
