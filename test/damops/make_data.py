#!/usr/bin/env python3
# =====================================================================
# damops: 入力データの生成(data_damops/mask.txt・z.txt・level4.txt)
#   領域 24 × 14 セル(dx = dy = 10 m)。i = 2 の列に孤立した 1 セルの
#   捕捉帯を 5 つ(j = 2, 4, 6, 8, 10)置き、周りの 8 近傍をすべて領域外
#   (マスク 0)にする。i = 5〜24 は放流を受ける平坦な閉じた池(四周は壁)。
#   捕捉帯は流れのやり取りをしないので、内部ソースで入れた水は次の歩に
#   全量が吸収される(ダムの流入 Qin = 1 歩前のソースの流量)。
#   level4.txt はダム 4(貯水位の時系列 f_dam_mode = 5)の目標水位
#   (各行 "時刻(min) 水位(m)")。
#   使い方: python3 make_data.py
# =====================================================================
import os

nx, ny = 24, 14
capture = [(2, 2), (2, 4), (2, 6), (2, 8), (2, 10)]   # (i, j)。1 始まり
d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_damops")
os.makedirs(d, exist_ok=True)

mask = [[0] * nx for _ in range(ny)]
for j in range(ny):
    for i in range(4, nx):          # i = 5..24(0 始まりで 4..23)
        mask[j][i] = 1
for (i, j) in capture:
    mask[j - 1][i - 1] = 1

with open(os.path.join(d, "mask.txt"), "w") as f:
    for row in mask:
        f.write(" ".join(str(v) for v in row) + "\n")
with open(os.path.join(d, "z.txt"), "w") as f:
    for _ in range(ny):
        f.write(" ".join("0.0" for _ in range(nx)) + "\n")
with open(os.path.join(d, "level4.txt"), "w") as f:
    for t, h in [(0, 104.0), (60, 104.0), (180, 105.5), (240, 105.5), (330, 104.5)]:
        f.write(f"{t} {h}\n")
print("wrote", d)
