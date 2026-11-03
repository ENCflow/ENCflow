#!/usr/bin/env python3
# 雪崩再配分の等方性の検定(構成 4: param_ava.txt)
#   円錐山体に一様な雪(SWE 1000 mm)を置き、雪崩再配分だけを 1 日動かした
#   最終の SWE(Sw9998)を、山頂から同じ距離の円周上で比べる。判定:
#     (1) 等方性: 半径 800・1000・1200・1400・1600 m の円周上(方位 0.5° 刻み、
#         双一次補間)の SWE の変動係数 < TOL_CV。送り先を 8 近傍の最急降下の
#         1 セルにする方式(D8)では、雪が格子軸と斜めの 8 方向の線に残り、
#         その間で減るため 0.23〜0.35 になる(2026-11-03 の修正前のコード。
#         developer.md §45.2)
#     (2) 再配分が働いている: 半径 400 m の円周上の平均 SWE が初期の 90% 未満
#         (何も動かなければ (1) は自明に通るため)
#     (3) 水当量の保存: Screen.log の S_total の初値/終値の相対差 < TOL_VOL
#   使い方: Check_ava.py [resultdir] [screenlog]
import sys
import math

# param_ava.txt / Make_input.py と対で保守する定数
NX = NY = 81
DX = 50.0
IC = 41                         # 山頂のセル(1 始まり)
SWE0 = 1000.0                   # 初期 SWE (mm)
RINGS = (800.0, 1000.0, 1200.0, 1400.0, 1600.0)
TOL_CV = 0.08                   # (1) 円周上の変動係数
TOL_MOVED = 0.9                 # (2) 半径 400 m の平均 / 初期
TOL_VOL = 1.0e-12               # (3) 水当量の保存の相対許容差

resultdir = sys.argv[1] if len(sys.argv) > 1 else "result_ava"
screenlog = sys.argv[2] if len(sys.argv) > 2 else "Screen_ava.log"


def read_field(fn):
    rows = []
    for line in open(fn):
        vals = [float(w) for w in line.split()]
        if vals:
            rows.append(vals)
    assert len(rows) == NY and len(rows[0]) == NX, f"bad shape in {fn}"
    return rows


swe = read_field(f"{resultdir}/Sw9998.txt")
c = IC - 1


def at(x, y):
    """セル番号(0 始まり、セル中心が整数)で表した位置 (x, y) の双一次補間"""
    i0, j0 = int(math.floor(x)), int(math.floor(y))
    fx, fy = x - i0, y - j0
    return (swe[j0][i0] * (1 - fx) * (1 - fy) + swe[j0][i0 + 1] * fx * (1 - fy)
            + swe[j0 + 1][i0] * (1 - fx) * fy + swe[j0 + 1][i0 + 1] * fx * fy)


def ring(r):
    rc = r / DX
    v = []
    for a10 in range(0, 3600, 5):
        a = math.radians(a10 / 10.0)
        v.append(at(c + rc * math.cos(a), c + rc * math.sin(a)))
    mean = sum(v) / len(v)
    sd = math.sqrt(sum((x - mean) ** 2 for x in v) / len(v))
    return mean, sd / mean, min(v), max(v)


rc = 0

# ---- (1) 等方性 ----
for r in RINGS:
    mean, cv, vmin, vmax = ring(r)
    verdict = "ok" if cv < TOL_CV else "FAIL"
    print(f"avalanche: r = {r:6.0f} m  mean SWE {mean:7.1f} mm  min {vmin:7.1f}  "
          f"max {vmax:7.1f}  CV {cv:.3f} (tol {TOL_CV})  {verdict}")
    if cv >= TOL_CV:
        rc = 1
if rc:
    print("FAIL: snow is not redistributed isotropically (biased by the grid directions)")

# ---- (2) 再配分が働いている ----
mean400 = ring(400.0)[0]
print(f"avalanche: mean SWE on the 400 m ring = {mean400:.1f} mm (initial {SWE0:.0f}; "
      f"must be < {TOL_MOVED * SWE0:.0f})")
if mean400 >= TOL_MOVED * SWE0:
    print("FAIL: the avalanche redistribution did not move snow off the upper slope")
    rc = 1

# ---- (3) 水当量の保存(S_total 列の初値/終値)----
stotals = []
for line in open(screenlog):
    w = line.split()
    # 行形式: time progress% S_surf S_grnd S_total progress% Runge ...
    if len(w) >= 5 and ":" in w[0] and w[1].endswith("%"):
        try:
            stotals.append(float(w[4]))
        except ValueError:
            pass
if len(stotals) < 2:
    print("FAIL: could not parse S_total from " + screenlog)
    rc = 1
else:
    s0, s1 = stotals[0], stotals[-1]
    rel = abs(s1 - s0) / max(abs(s0), 1e-30)
    print(f"avalanche: water equivalent S_total {s0:.15e} -> {s1:.15e} (rel diff {rel:.2e})")
    if rel >= TOL_VOL:
        print("FAIL: water equivalent is not conserved")
        rc = 1

sys.exit(rc)
