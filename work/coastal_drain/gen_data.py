# -*- coding: utf-8 -*-
# coastal_drain: §46.5 (7)(8) の検証ケースのデータ生成
#   海抜下ポルダー(地盤 0.2 m)+海(海底 -2 m、潮位 0.5 m 一定)。
#   幹線(j=8, i=2..26)の管底は z-2 = -1.8 m(負値 = (7) の検証)。
#   吐口 (8b): (26,8)。海に隣接(海は i>=27)。Cd*A = 0.15 m2。
#   機場 (8a): 取水 (20,8)(param 側 &list_struct_pump f_pump_src=1)。
import os

nx, ny = 30, 15
jline = 8
i1, i2 = 2, 26        # 幹線(i2 = 吐口セル)
isea = 27             # これ以東が海

def write_mat(fn, fval):
    with open(fn, "w") as f:
        for j in range(1, ny + 1):
            f.write(" ".join("%.4f" % fval(i, j) for i in range(1, nx + 1)))
            f.write("\n")

here = os.path.dirname(os.path.abspath(__file__))
d = os.path.join(here, "data_cd")
os.makedirs(d, exist_ok=True)

on_line = lambda i, j: (j == jline and i1 <= i <= i2)

write_mat(os.path.join(d, "z.txt"), lambda i, j: -2.0 if i >= isea else 0.2)
with open(os.path.join(d, "sw.txt"), "w") as f:   # 海域マスクは整数
    for j in range(1, ny + 1):
        f.write(" ".join("1" if i >= isea else "0" for i in range(1, nx + 1)) + "\n")
write_mat(os.path.join(d, "cap.txt"), lambda i, j: 0.1 if on_line(i, j) else 0.0)
write_mat(os.path.join(d, "bot.txt"),
          lambda i, j: (0.2 - 2.0) if on_line(i, j) else (-2.0 if i >= isea else 0.2))
write_mat(os.path.join(d, "cnd.txt"), lambda i, j: 0.05 if on_line(i, j) else 0.0)
write_mat(os.path.join(d, "inlet.txt"), lambda i, j: 0.01 if on_line(i, j) else 0.0)
write_mat(os.path.join(d, "outfall.txt"),
          lambda i, j: 0.15 if (i == i2 and j == jline) else 0.0)
print("maps written to data_cd/ (trunk bot = -1.8 m: negative elevation)")
