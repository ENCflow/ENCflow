#!/usr/bin/env python3
# Halfar ドーム・ベンチマークの解析解比較
#   Hi0000(初期)と Hi9998(最終)を読み、平坦床 SIA の相似解
#     H(r,t) = H0 (t0/t)^{1/9} [1 - ((t0/t)^{1/18} r/R0)^{4/3}]^{3/7}
#     t0 = (1/(18Γ)) (7/4)^3 R0^4 / H0^7,  Γ = 2A(ρi g)^3/(n+2), n=3
#   と比較する。判定:
#     (1) 最終場の平均絶対誤差 < TOL_MEAN と最大絶対誤差 < TOL_MAX。
#         最大誤差は氷縁で出る: 解析解は氷縁で勾配が無限大のため、
#         セル半分の縁位置ずれでも数十 m の厚さ誤差になる(TOL_MAX は
#         縁 1.5 セルずれ相当。実測は 1 セル未満 ≈ 38 m)
#     (2) 中心セルの誤差 < TOL_CTR(「流れていない/流れ過ぎ」の検出。
#         流れないと誤差 23 m、正しく流れると ~5 m)
#     (3) Screen.log の S_total(氷の水当量)の初値/終値の相対差 < TOL_VOL
#         (反対称フラックスにより機械精度で保存。実測 ~1e-15)
#   使い方: Check_halfar.py <resultdir> <screenlog>
import sys
import math

# param.txt / Make_input.py と対で保守する定数
NX = NY = 61
DX = 25.0
IC = JC = 31
H0, R0 = 200.0, 600.0
A_YR = 1.0e-16                  # Glen A (Pa^-3 yr^-1)
RHOI, GG = 900.0, 9.8
YR_S = 365.25 * 86400.0
TT, MORFAC = 86400.0, 80.0      # 地形時間 = TT*MORFAC
TOL_MEAN = 4.0                  # (1) 平均絶対誤差 (m)
TOL_MAX = 45.0                  # (1) 最大絶対誤差 (m。氷縁 1.5 セルずれ相当)
TOL_CTR = 6.0                   # (2) 中心セル誤差 (m)
TOL_VOL = 1.0e-7                # (3) 体積保存の相対許容差

resultdir = sys.argv[1] if len(sys.argv) > 1 else "result"
screenlog = sys.argv[2] if len(sys.argv) > 2 else "Screen.log"

GAM = 2.0 * (A_YR / YR_S) * (RHOI * GG) ** 3 / 5.0
T0 = (7.0 / 4.0) ** 3 * R0 ** 4 / H0 ** 7 / (18.0 * GAM)
TFIN = T0 + TT * MORFAC


def read_field(fn):
    rows = []
    for line in open(fn):
        vals = [float(w) for w in line.split()]
        if vals:
            rows.append(vals)
    assert len(rows) == NY and len(rows[0]) == NX, f"bad shape in {fn}"
    return rows


def halfar(r, t):
    s = (T0 / t) ** (1.0 / 18.0) * r / R0
    if s >= 1.0:
        return 0.0
    return H0 * (T0 / t) ** (1.0 / 9.0) * (1.0 - s ** (4.0 / 3.0)) ** (3.0 / 7.0)


rc = 0

# ---- (1)(2) 最終場と解析解の比較 ----
hi = read_field(f"{resultdir}/Hi9998.txt")
xc = (IC - 0.5) * DX
maxerr, sumerr, ctrerr = 0.0, 0.0, None
for j in range(NY):
    for i in range(NX):
        x = (i + 0.5) * DX - xc
        y = (j + 0.5) * DX - xc
        r = math.hypot(x, y)
        err = abs(hi[j][i] - halfar(r, TFIN))
        maxerr = max(maxerr, err)
        sumerr += err
        if i + 1 == IC and j + 1 == JC:
            ctrerr = err
meanerr = sumerr / (NX * NY)

hctr_ana = halfar(0.0, TFIN)
print(f"Halfar: t0 = {T0:.4e} s, t_fin = {TFIN:.4e} s (= {TFIN/T0:.3f} t0)")
print(f"Halfar: analytic center H = {hctr_ana:.3f} m, "
      f"computed = {hi[JC-1][IC-1]:.3f} m (err {ctrerr:.3f} m)")
print(f"Halfar: mean |err| = {meanerr:.3f} m (tol {TOL_MEAN}), "
      f"max |err| = {maxerr:.3f} m (tol {TOL_MAX}), "
      f"center |err| = {ctrerr:.3f} m (tol {TOL_CTR})")
if meanerr >= TOL_MEAN:
    print("FAIL: mean error exceeds tolerance")
    rc = 1
if maxerr >= TOL_MAX:
    print("FAIL: max error exceeds tolerance")
    rc = 1
if ctrerr >= TOL_CTR:
    print("FAIL: center error exceeds tolerance")
    rc = 1

# ---- (3) 体積保存(S_total 列の初値/終値)----
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
    print(f"Halfar: ice volume S_total {s0:.15e} -> {s1:.15e} (rel diff {rel:.2e})")
    if rel >= TOL_VOL:
        print("FAIL: ice volume is not conserved")
        rc = 1

sys.exit(rc)
