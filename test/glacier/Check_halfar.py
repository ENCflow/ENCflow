#!/usr/bin/env python3
# Halfar ドーム・ベンチマークの解析解比較
#   Hi0000(初期)と Hi9998(最終)を読み、平坦床 SIA の相似解
#     H(r,t) = H0 (t0/t)^{1/9} [1 - ((t0/t)^{1/18} r/R0)^{4/3}]^{3/7}
#     t0 = (1/(18Γ)) (7/4)^3 R0^4 / H0^7,  Γ = 2A(ρi g)^3/(n+2), n=3
#   と比較する。判定:
#     (1) 最終場の平均絶対誤差 < TOL_MEAN と最大絶対誤差 < TOL_MAX。
#         最大誤差は氷縁で出る: 解析解は氷縁で勾配が無限大のため、
#         セル半分の縁位置ずれでも数十 m の厚さ誤差になる(TOL_MAX は
#         縁 1.5 セルずれ相当。実測 12.5 m。2026-11-03 の §45.1 の修正前は 38.6 m)
#     (2) 中心セルの誤差 < TOL_CTR(「流れていない/流れ過ぎ」の検出。
#         流れないと誤差 23 m、正しく流れると 0.13 m。修正前は 4.7 m)
#     (3) Screen.log の S_total(氷の水当量)の初値/終値の相対差 < TOL_VOL
#         (反対称フラックスにより機械精度で保存。実測 ~1e-15)
#     (4) 等方性: セル中心の方位角で、格子軸の方向(軸から ±22.5° 以内)と
#         斜めの方向(45° ± 22.5° 以内)の扇形に分け、氷の体積の比(斜め/軸)を
#         同じ分け方の解析解の比と比べ、差 < TOL_ISO。拡散係数を法線方向の
#         勾配だけで評価すると斜めの方向の D が 1/2 になり、氷が格子軸の方向へ
#         偏る(developer.md §45.1。2026-11-03 の修正前のコードで 5.49% 不足、修正後 +0.59%)
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
TOL_ISO = 0.02                  # (4) 斜め/軸の体積比の解析解との相対差

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

# ---- (4) 等方性(格子軸の方向と斜めの方向の扇形の氷の体積比)----
#   方位角がちょうど 22.5° の倍数のセルはどちらにも入れない(この格子では現れない)
vol = {"axis": 0.0, "diag": 0.0}
vana = {"axis": 0.0, "diag": 0.0}
area = {"axis": 0.0, "diag": 0.0}
for j in range(NY):
    for i in range(NX):
        x = (i + 0.5) * DX - xc
        y = (j + 0.5) * DX - xc
        if x == 0.0 and y == 0.0:
            continue
        th = math.degrees(math.atan2(y, x)) % 90.0
        if abs(th - 22.5) < 1e-9 or abs(th - 67.5) < 1e-9:
            continue
        sec = "axis" if (th < 22.5 or th > 67.5) else "diag"
        vol[sec] += hi[j][i]
        vana[sec] += halfar(math.hypot(x, y), TFIN)
        if hi[j][i] > 0.0:
            area[sec] += DX * DX
ratio_c = vol["diag"] / vol["axis"]
ratio_a = vana["diag"] / vana["axis"]
dev = ratio_c / ratio_a - 1.0
req = {sec: math.sqrt(2.0 * area[sec] / math.pi) for sec in area}
print(f"Halfar: ice volume diagonal/axis sectors = {ratio_c:.4f} "
      f"(analytic {ratio_a:.4f}, diff {100.0*dev:+.2f}%, tol {100.0*TOL_ISO:.1f}%); "
      f"area-equivalent radius axis {req['axis']:.1f} m, diagonal {req['diag']:.1f} m")
if abs(dev) >= TOL_ISO:
    print("FAIL: the dome is not isotropic (ice biased toward the grid axes or the diagonals)")
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
