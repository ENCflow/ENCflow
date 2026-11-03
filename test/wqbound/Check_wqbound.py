#!/usr/bin/env python3
# =====================================================================
# wqbound: wq.csv と濃度分布の reference 非依存検定(developer.md §30.9)
#   closure DIR : 全行で台帳が閉じる
#                 M(0) + 入力の累積 − 除去・系外への流出 = M(t)
#                 (M = mass_* の合計。入力 = in_* の列、除去 = decay・to_gwc・
#                 out_sea・out_edge・out_stage。settle_g・to_dam_g はこのケースでは 0)
#   paths DIR   : 系外との出入りの各経路が働いている(param.txt: in_point・in_edge・
#                 out_sea・out_edge・out_stage がすべて正)
#   reverse DIR : 逆流のケース(param_rev.txt): 全時刻・全セルで濃度が初期値 1 mg/L を
#                 超えない(規定セルに溜まった質量が戻らない)、最終時刻の規定セルに
#                 接するセルの濃度が境界濃度 0.5 mg/L、in_stage・out_stage がともに正
#   許容は es15.7(有効 8 桁)の出力精度相当の相対 1e-6
# =====================================================================
import csv
import glob
import os
import sys

TOL = 1.0e-6
IN_COLS = ["in_point_g", "in_area_g", "in_map_g", "in_rain_g", "in_gwc_g", "in_bldup_g",
           "in_edge_g", "in_stage_g"]
OUT_COLS = ["decay_g", "to_gwc_g", "out_sea_g", "out_edge_g", "out_stage_g"]
MASS_COLS = ["mass_surface_g", "mass_gw_g", "mass_pool_g", "mass_dam_g", "mass_rs_g"]
rc = 0


def ledger(d):
    rows = list(csv.reader(open(os.path.join(d, "wq.csv"))))
    head = rows[0]
    return [dict(zip(head, (float(x) for x in r))) for r in rows[1:]]


def ng(msg):
    global rc
    print("  NG:", msg)
    rc = 1


def closure(d):
    rows = ledger(d)
    m0 = sum(rows[0][c] for c in MASS_COLS)
    worst = 0.0
    for r in rows:
        ins = sum(r[c] for c in IN_COLS)
        outs = sum(r[c] for c in OUT_COLS)
        res = m0 + ins - outs - sum(r[c] for c in MASS_COLS)
        scale = max(m0 + ins, 1.0)
        worst = max(worst, abs(res) / scale)
    last = rows[-1]
    print(f"  M(0) = {m0:.7e}, inputs = {sum(last[c] for c in IN_COLS):.7e}, "
          f"outflows = {sum(last[c] for c in OUT_COLS):.7e}, "
          f"M(end) = {sum(last[c] for c in MASS_COLS):.7e}")
    print(f"  max relative closure residual over {len(rows)} rows = {worst:.2e}")
    if worst > TOL:
        ng(f"ledger does not close (relative residual {worst:.2e} > {TOL})")


def positive(d, cols):
    last = ledger(d)[-1]
    for c in cols:
        print(f"  {c} = {last[c]:.7e}")
        if not last[c] > 0.0:
            ng(f"{c} must be positive (path inactive?)")


def read_matrix(path):
    return [[float(x) for x in line.split()] for line in open(path) if line.strip()]


def reverse(d):
    cmax = 0.0
    files = sorted(glob.glob(os.path.join(d, "C[0-9][0-9][0-9][0-9].txt")))
    files = [f for f in files if not f.endswith("C9998.txt") and not f.endswith("C9999.txt")]
    for f in files:
        cmax = max(cmax, max(max(row) for row in read_matrix(f)))
    print(f"  max C over {len(files)} outputs = {cmax:.7e} (initial 1 mg/L)")
    if cmax > 1.0 * (1.0 + TOL):
        ng("concentration exceeds the initial 1 mg/L (mass returned from the water-level cell?)")
    clast = read_matrix(files[-1])[0]
    print(f"  final C next to the water-level cell (i = 29) = {clast[28]:.7e} (boundary 0.5 mg/L)")
    if abs(clast[28] - 0.5) > 1.0e-3:
        ng("inflow from the water-level cell does not carry the boundary concentration")
    positive(d, ["in_stage_g", "out_stage_g"])


if len(sys.argv) != 3 or sys.argv[1] not in ("closure", "paths", "reverse"):
    print("usage: Check_wqbound.py {closure|paths|reverse} RESULT_DIR")
    sys.exit(2)
mode, d = sys.argv[1], sys.argv[2]
print(f"Check_wqbound {mode}: {d}")
if mode == "closure":
    closure(d)
elif mode == "paths":
    positive(d, ["in_point_g", "in_edge_g", "out_sea_g", "out_edge_g", "out_stage_g"])
else:
    reverse(d)
sys.exit(rc)
