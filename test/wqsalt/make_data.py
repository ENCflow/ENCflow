#!/usr/bin/env python3
"""wqsalt の入力データ(data_wqsalt/)を作る。置いてあるファイルと同じものを作り直すだけで、
検定(Run.sh)は置いてあるファイルを使う。行は北から南、列は西から東。"""
import os

D = "data_wqsalt"
os.makedirs(D, exist_ok=True)


def write(name, rows, fmt="%.4f"):
    with open(os.path.join(D, name), "w") as f:
        for r in rows:
            f.write(" ".join(fmt % v for v in r) + "\n")


# --- mixflow: 40 × 20 セル。西半分の水深 1.2 m、東半分 0.8 m(段のある静水 = 動き出して揺れる) ---
nx, ny = 40, 20
write("h_step.txt", [[1.2 if i < nx // 2 else 0.8 for i in range(nx)] for _ in range(ny)])

# --- mixwall: 40 × 20 セル。列 21 に高さ 2 m の乾いた尾根(水位 1 m では水面の上) ---
write("z_ridge.txt", [[2.0 if i == 20 else 0.0 for i in range(nx)] for _ in range(ny)])
# --- dis・disk・inf: 10 × 10 セル。初期の析出物(表面蓄積プール kg/ha)を西半分と東半分で変える ---
#   dis・disk: 西 100 kg/m2(水深 0.2 m の水が飽和しても余る)、東 30 kg/m2(溶けきる)
#   inf:       西 100 kg/m2(36 mm の浸透水では溶けきらない)、東 0.5 kg/m2(溶けきる)
n = 10
write("pool_dis.txt", [[1.0e6 if i < n // 2 else 3.0e5 for i in range(n)] for _ in range(n)], "%.1f")
write("pool_inf.txt", [[1.0e6 if i < n // 2 else 5.0e3 for i in range(n)] for _ in range(n)], "%.1f")
# --- sea: 24 × 8 セル。西端の 1 列が海域マスク(1 = 海) ---
write("sw_sea.txt", [[1 if i == 0 else 0 for i in range(24)] for _ in range(8)], "%d")

# --- c0map: 40 × 20 セル(z_ridge.txt と同じ)。初期濃度 (mg/L) を尾根の西で 100、東で 300 ---
write("c0_ridge.txt", [[100.0 if i < 20 else 300.0 for i in range(nx)] for _ in range(ny)], "%.1f")
# --- mixgv: 24 × 12 セル。家屋の空隙率を西半分 1.0、東半分 0.5 にする ---
write("gv_half.txt", [[1.0 if i < 12 else 0.5 for i in range(24)] for _ in range(12)], "%.1f")
# --- mixwd: 24 × 12 セル。列 13 を幅 2 m のサブグリッド河道にする(河道マスクと河道幅) ---
write("rw_col.txt", [[1 if i == 12 else 0 for i in range(24)] for _ in range(12)], "%d")
write("width_col.txt", [[2.0 if i == 12 else 0.0 for i in range(24)] for _ in range(12)], "%.1f")
print("wrote", sorted(os.listdir(D)))
