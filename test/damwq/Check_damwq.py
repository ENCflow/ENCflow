#!/usr/bin/env python3
# =====================================================================
# damwq: reference 非依存検定(水質 §30.7。ダム完全混合+ため池同伴)
#   closure : 初期質量 4000 g = mass_surface + mass_dam + mass_rs
#             (閉領域・減衰なし・gwflow なし)、ダムプールの閉合
#             to_dam − rel_dam = mass_dam、各経路の活性
#   uniform : 最終 C 場の湿潤セルが ≈ 100 mg/L(捕捉→完全混合→放流・
#             ため池吸収の全経路で濃度が保たれる端到端の確認)
#   許容: 台帳は es15.7(有効8桁)相当の相対 1e-6、C 場は ±0.1
# =====================================================================
import csv
import glob
import sys

mode = sys.argv[1]
rc = 0
tol = 1.0e-6

if mode == "closure":
    rows = list(csv.reader(open(sys.argv[2])))
    d = dict(zip(rows[0], (float(x) for x in rows[-1])))
    m0 = 100.0 * 0.05 * 40 * 20     # 初期質量 = c0 × h0 × 面積 = 4000 g
    tot = d["mass_surface_g"] + d["mass_dam_g"] + d["mass_rs_g"]
    ok = abs(tot - m0) <= tol * m0
    print(f"  surf+dam+rs = init: {tot:.7e} vs {m0:.7e} -> {'OK' if ok else 'NG'}")
    if not ok:
        rc = 1
    ok = abs(d["to_dam_g"] - d["rel_dam_g"] - d["mass_dam_g"]) <= tol * d["to_dam_g"]
    print(f"  to_dam - rel_dam = mass_dam: {d['to_dam_g'] - d['rel_dam_g']:.7e} vs "
          f"{d['mass_dam_g']:.7e} -> {'OK' if ok else 'NG'}")
    if not ok:
        rc = 1
    if d["to_dam_g"] > 0 and d["rel_dam_g"] > 0 and d["to_rs_g"] > 0 and d["mass_rs_g"] > 0:
        print("  to_dam/rel_dam/to_rs/mass_rs all positive -> OK")
    else:
        print(f"  NG: to_dam={d['to_dam_g']:.3e} rel_dam={d['rel_dam_g']:.3e} "
              f"to_rs={d['to_rs_g']:.3e} mass_rs={d['mass_rs_g']:.3e}")
        rc = 1
elif mode == "uniform":
    fn = sorted(glob.glob(sys.argv[2] + "/C0*.txt"))[-1]
    vals = []
    for line in open(fn):
        vals += [float(v) for v in line.split()]
    wet = [v for v in vals if v > 0.0]
    lo, hi = min(wet), max(wet)
    ok = 99.9 <= lo and hi <= 100.1
    print(f"  {fn}: wet cells {len(wet)}, C in [{lo:.4f}, {hi:.4f}] -> {'OK' if ok else 'NG'}")
    if not ok:
        rc = 1
else:
    print(f"usage: Check_damwq.py closure wq.csv | uniform result_dir (got '{mode}')")
    rc = 2
sys.exit(rc)
