#!/usr/bin/env python3
# dissol の解析解比較(developer.md §86、docs/karst_plan.md §3)
#   bil(float32)の終了時出力 Z9998(・Sd9998・Hgc0003)を読み、各構成の
#   解析値と内部セルで比較する。
#   使い方: Check_analytic.py {a|b|c} <resultdir> [rtol]
#     a: result      Δz = -3e-4 m、Δsd = +1e-4 m(全セル)
#     b: result_sink Δz(中心 5x5) = -0.2 x Hgc0003、Δz(外側) = 0
#     c: result_rain Δz = -1.2e-3 m(全セル)
#   終了コード: 0 = PASS、1 = FAIL
import sys, numpy as np

NX = NY = 21
KD = 100.0e-3 / 2500.0           # c_eq/ρ_r (m/m)。param.txt と対で保守する

def read_bil(fn):
    a = np.fromfile(fn, dtype="<f4")
    if a.size != NX * NY:
        raise SystemExit("FAIL: unexpected size in " + fn)
    return a.reshape(NY, NX).astype(np.float64)

def check(label, num, ana, rtol, atol=0.0):
    err = np.abs(num - ana)
    tol = atol + rtol * np.abs(ana)
    ok = bool(np.all(err <= tol))
    print("%-28s max|num - ana| = %.3e  (ana = %.6e)  %s"
          % (label, float(err.max()), float(np.abs(ana).max()), "PASS" if ok else "FAIL"))
    return ok

case = sys.argv[1]
rdir = sys.argv[2]
rtol = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0e-6
ok = True
z = read_bil(rdir + "/Z9998.bil")
if case == "a":
    # 浸透 1e-3 m × k_d × morfac 1e4 = 4e-4 m、残渣率 0.25
    w = KD * 1.0e-3 * 1.0e4
    sd = read_bil(rdir + "/Sd9998.bil")
    ok &= check("A: z  (z0 - 0.75 w)", z, np.full_like(z, -0.75 * w), rtol)
    ok &= check("A: sd (sd0 + 0.25 w)", sd, np.full_like(sd, 1.0 + 0.25 * w), rtol)
elif case == "b":
    hgc = read_bil(rdir + "/Hgc0003.bil")
    c = NX // 2
    inner = np.zeros((NY, NX), dtype=bool)
    inner[c-2:c+3, c-2:c+3] = True
    ana = np.where(inner, -KD * 0.5 * hgc * 1.0e4, 0.0)
    ok &= check("B: z (center 5x5)", z[inner], ana[inner], rtol)
    ok &= check("B: z (outside = z0)", z[~inner], ana[~inner], rtol, atol=1.0e-12)
elif case == "c":
    w = KD * (30.0 / 3.6e6 * 3600.0) * 1000.0
    ok &= check("C: z (z0 - w)", z, np.full_like(z, -w), rtol)
else:
    raise SystemExit("usage: Check_analytic.py {a|b|c} <resultdir> [rtol]")
print("== dissol %s: %s ==" % (case.upper(), "PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
