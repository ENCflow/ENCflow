#!/usr/bin/env python3
# =====================================================================
# gwseep: wq.csv の reference 非依存検定(水質 W3。developer.md §30.5)
#   closure : 台帳の閉合 to_gw − seep = mass_gw と総質量保存
#             (閉領域なので 地表+地下 = 初期質量 4000 g)、
#             輸送の活性(to_gw > 0 かつ seep > 0)
#   immobile: wq_rg=1e12 の完全不動化(seep ≈ 0、mass_gw = to_gw)
#   許容は es15.7(有効8桁)の出力精度相当の相対 1e-6
# =====================================================================
import csv
import sys

mode, path = sys.argv[1], sys.argv[2]
rows = list(csv.reader(open(path)))
d = dict(zip(rows[0], (float(x) for x in rows[-1])))
m0 = 100.0 * 0.05 * 40 * 20     # 初期質量 = c0 × h0 × 面積 = 4000 g
tol = 1.0e-6                    # 出力精度相当の相対許容
rc = 0


def chk(label, a, b, scale):
    global rc
    ok = abs(a - b) <= tol * abs(scale)
    print(f"  {label}: {a:.7e} vs {b:.7e} -> {'OK' if ok else 'NG'}")
    if not ok:
        rc = 1


print(f"Check_gwseep {mode}: {path} (t = {rows[-1][0]} s)")
if mode == "closure":
    chk("to_gw - seep = mass_gw", d["to_gw_g"] - d["seep_g"], d["mass_gw_g"], d["to_gw_g"])
    chk("mass_surface + mass_gw = init", d["mass_surface_g"] + d["mass_gw_g"], m0, m0)
    if d["to_gw_g"] > 0.0 and d["seep_g"] > 0.0:
        print("  to_gw/seep both positive -> OK")
    else:
        print("  NG: to_gw_g and seep_g must be positive (transport inactive?)")
        rc = 1
elif mode == "immobile":
    chk("mass_gw = to_gw (R=1e12)", d["mass_gw_g"], d["to_gw_g"], d["to_gw_g"])
    if d["seep_g"] <= tol * d["to_gw_g"]:
        print(f"  seep_g = {d['seep_g']:.3e} ~ 0 -> OK")
    else:
        print(f"  NG: seep_g = {d['seep_g']:.3e} (must be ~0 at R=1e12)")
        rc = 1
else:
    print(f"usage: Check_gwseep.py {{closure|immobile}} wq.csv (got '{mode}')")
    rc = 2
sys.exit(rc)
