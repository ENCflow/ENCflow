#!/usr/bin/env python3
"""saltledger の入力データ(data_saltledger/)を作る。置いてあるファイルと同じものを作り直すだけで、
検定(Run.sh)は置いてあるファイルを使う。行は北から南、列は西から東。"""
import math
import os

D = "data_saltledger"
os.makedirs(D, exist_ok=True)


def write(name, rows, fmt="%.4f"):
    with open(os.path.join(D, name), "w") as f:
        for r in rows:
            f.write(" ".join(fmt % v for v in r) + "\n")


def cells(name, pairs):
    with open(os.path.join(D, name), "w") as f:
        for i, j in pairs:
            f.write("%d %d\n" % (i, j))


# --- sea・gwsea: 西端の 1 列が海域マスク(1 = 海) ---
write("sw_sea.txt", [[1 if i == 0 else 0 for i in range(24)] for _ in range(8)], "%d")
write("sw_gw.txt", [[1 if i == 0 else 0 for i in range(12)] for _ in range(8)], "%d")

# --- sea2d: 24 × 16 セル。西端の 1 列が海。陸の地盤高は 0.8〜1.2 m の凹凸(x・y の両方で変わる。
#     MPI の帯の境をまたいで流れの向きが変わる構成) ---
write("sw_sea2d.txt", [[1 if i == 0 else 0 for i in range(24)] for _ in range(16)], "%d")
write("z_sea2d.txt", [[1.0 if i == 0 else 1.0 + 0.2 * math.sin(2.0 * math.pi * i / 7.0 + 0.9 * j) * math.cos(2.0 * math.pi * j / 5.0)
                       for i in range(24)] for j in range(16)])

# --- pump0・pump1・pump2: 4 × 8 セルの全セルが取水セル(8 行 = MPI の 4 ランクまで分けられる)---
cells("cells_all.txt", [(i, j) for j in range(1, 9) for i in range(1, 5)])

# --- xfer: 9 × 8 セル。列 5 が高さ 5 m の尾根。西の池(列 1〜4)から東の池(列 6〜9)へポンプで送る ---
write("z_two.txt", [[5.0 if i == 4 else 0.0 for i in range(9)] for _ in range(8)])
write("h_two.txt", [[1.0 if i < 4 else (0.0 if i == 4 else 0.2) for i in range(9)] for _ in range(8)])
write("hss_two.txt", [[0.3 if i < 4 else 0.0 for i in range(9)] for _ in range(8)])
cells("cells_west.txt", [(i, j) for j in range(1, 9) for i in range(1, 5)])
cells("cells_east.txt", [(i, j) for j in range(1, 9) for i in range(6, 10)])

# --- exout: 20 × 8 セル。斜面(z = 1 → 0 m。列 1〜17)と窪地(z = −0.5 m。列 18〜20)。帯水層の底は
#     −1 m(土層厚 = z + 1)、初期の地下の塩水 = 容量の 8 割(淡水なし)。test/salt の模式実験 C2 と同じ ---
nx, ny = 20, 8
zrow = [1.0 - i / 16.0 if i < 17 else -0.5 for i in range(nx)]
write("z_slope.txt", [zrow for _ in range(ny)])
write("sd_slope.txt", [[z + 1.0 for z in zrow] for _ in range(ny)])
write("hgs0_slope.txt", [[0.8 * (z + 1.0) * 0.2 for z in zrow] for _ in range(ny)])
print("wrote", sorted(os.listdir(D)))
