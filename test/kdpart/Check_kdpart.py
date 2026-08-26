#!/usr/bin/env python3
# =====================================================================
# kdpart: wq.csv の reference 非依存検定(水質 K1。developer.md §30.6)
#   closure  : in_point = mass_surface + mass_gw + mass_pool
#              (閉領域・減衰なし・f_wq_settle=1 = プール行き沈降は
#               内部移動、の帰結)と、分配・浸透の活性
#              (settle_g・to_gw_g・mass_pool_g > 0)
#   monotonic: Kd 1000 倍(result_hi)で settle 増・to_gw 減
#   許容は es15.7(有効8桁)の出力精度相当の相対 1e-6
# =====================================================================
import csv
import sys


def last_row(path):
    rows = list(csv.reader(open(path)))
    return dict(zip(rows[0], (float(x) for x in rows[-1])))


mode = sys.argv[1]
tol = 1.0e-6
rc = 0

if mode == "closure":
    d = last_row(sys.argv[2])
    tot = d["mass_surface_g"] + d["mass_gw_g"] + d["mass_pool_g"]
    ok = abs(tot - d["in_point_g"]) <= tol * d["in_point_g"]
    print(f"  in_point = surf+gw+pool: {d['in_point_g']:.7e} vs {tot:.7e} "
          f"-> {'OK' if ok else 'NG'}")
    if not ok:
        rc = 1
    if d["settle_g"] > 0.0 and d["to_gw_g"] > 0.0 and d["mass_pool_g"] > 0.0:
        print("  settle/to_gw/pool all positive -> OK")
    else:
        print(f"  NG: settle_g={d['settle_g']:.3e} to_gw_g={d['to_gw_g']:.3e} "
              f"mass_pool_g={d['mass_pool_g']:.3e} (partition inactive?)")
        rc = 1
elif mode == "monotonic":
    lo = last_row(sys.argv[2])
    hi = last_row(sys.argv[3])
    if hi["settle_g"] > lo["settle_g"]:
        print(f"  settle_g: {lo['settle_g']:.7e} -> {hi['settle_g']:.7e} (Kd x1000) -> OK")
    else:
        print(f"  NG: settle_g must increase with Kd "
              f"({lo['settle_g']:.3e} -> {hi['settle_g']:.3e})")
        rc = 1
    if hi["to_gw_g"] < lo["to_gw_g"]:
        print(f"  to_gw_g : {lo['to_gw_g']:.7e} -> {hi['to_gw_g']:.7e} (Kd x1000) -> OK")
    else:
        print(f"  NG: to_gw_g must decrease with Kd "
              f"({lo['to_gw_g']:.3e} -> {hi['to_gw_g']:.3e})")
        rc = 1
else:
    print(f"usage: Check_kdpart.py closure wq.csv | monotonic wq_lo.csv wq_hi.csv (got '{mode}')")
    rc = 2
sys.exit(rc)
