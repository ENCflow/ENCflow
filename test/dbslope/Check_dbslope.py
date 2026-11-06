#!/usr/bin/env python3
"""test/dbslope の検定(混合体流動の抵抗則を斜面に沿って評価する f_gravity_correction = 2。developer.md §101)。

勾配 tan θ = tan30° の一様な斜面の等流(最急勾配の向き、4 近傍)で、帯の中ほどの窓(x ∈ [60, 100] m)の
混合体の鉛直の深さ h_t = h + hs の平均を、水平の流速・鉛直の深さで書いた次の釣り合いの解析解と比べる
(q = h_t |V| は流入の単位幅の混合体流量、C = cs/(1 + cs) は濃度、g_e = g cos²θ、c = cos θ、
fv は 2 で 1/c⁴(掃流状は 1/c³)、1 で 1。降伏の倍率は最急勾配の向きでは 1 と 2 とも 1):
  voellmy   : g_e tanθ = g_e μ + fv g_e |V|²/(ξ h_t)          → h_t³ = q² fv / (ξ (tanθ − μ))
  egashira  : g_e tanθ = g_e tanφ sC/(1+sC) (C/C*)^{1/5} + fv f_b |V|²/((1+sC) h_t)、
              f_b = 6.25 {k_f (1−C)^{5/3}/C^{2/3} + k_d (s+1)(1−e²) C^{1/3}} (d/h_t)²   → h_t⁵ = …
  stony     : g_e tanθ = g_e tanα' sC/(1+sC) + fv A'{(1−C)/C}^{2/3} (d/h_t)² |V|²/((1+sC) h_t)
  collective: g_e tanθ = g_e tanα' sC/(1+sC) + fv (d/h_t) |V|²/(0.49 h_t)
2 の解析解は、斜面に沿う速さと地盤に直角な厚さで書いた原式(Voellmy なら V_s² = ξ h_n (sin θ − μ cos θ))と
同じ。判定:
  (1) 各ケースの <h_t> が解析解と TOL_ANA 以内、窓の変動係数 TOL_CV 未満、濃度が流入の値
  (2) 検出力: 2 と 1 の解析解の比が 1 から DISC_MIN 以上離れる(2 つの形を区別できる)

  python3 Check_dbslope.py        判定(失敗があれば終了コード 1)
  python3 Check_dbslope.py table  判定と表
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_init as mi   # noqa: E402

GRAV = 9.8
KF, KD, TANA, APR, C49 = 0.16, 0.0828, 0.45, 4.0, 0.49   # m_swflow_enc の db_kf・db_kd・db_tana・db_apr・db_c49
X0, X1 = 60.0, 100.0                                     # 検定窓 (m)
TOL_ANA, TOL_CV, TOL_C = 0.005, 0.02, 1e-3   # 濃度は出力の H・Hs の丸め(0.1 mm)で 1e-4 程度ずれる
DISC_MIN = 0.05


def analytic(law, gc):
    """等流の混合体の深さ h_t (m)、単位幅の混合体流量 q、濃度 C。"""
    fres, cs, _ = mi.LAWS[law]
    q = mi.QIN * (1.0 + cs) / (mi.NY * mi.DX)
    cc = cs / (1.0 + cs)
    c2 = 1.0 / (1.0 + mi.G ** 2)
    ge = GRAV * c2
    s = mi.SGRAV
    sc = s * cc / (1.0 + s * cc)
    cstar = 1.0 - mi.POROSITY
    if law == "voellmy":
        fv = 1.0 / c2 ** 2 if gc >= 2 else 1.0
        h = (q * q / (mi.XI / fv * (mi.G - mi.MU))) ** (1.0 / 3.0)
    elif law in ("egashira", "stony"):
        fv = 1.0 / c2 ** 2 if gc >= 2 else 1.0
        if law == "egashira":
            dy = mi.G - math.tan(math.radians(mi.PHI)) * sc * (cc / cstar) ** 0.2
            kk = 6.25 * (KF * (1.0 - cc) ** (5.0 / 3.0) / cc ** (2.0 / 3.0)
                         + KD * (s + 1.0) * (1.0 - mi.EREST ** 2) * cc ** (1.0 / 3.0))
        else:
            dy = mi.G - TANA * sc
            kk = APR * ((1.0 - cc) / cc) ** (2.0 / 3.0)
        # g_e dy = fv kk d² q² / ((1+sC) h⁵)
        h = (fv * kk * mi.D50 ** 2 * q * q / ((1.0 + s * cc) * ge * dy)) ** 0.2
    else:   # collective
        fv1 = 1.0 / c2 ** 1.5 if gc >= 2 else 1.0
        dy = mi.G - TANA * sc
        # g_e dy = fv1 (d/h) (q/h)² / (0.49 h) → h⁴ = fv1 d q² / (0.49 g_e dy)
        h = (fv1 * mi.D50 * q * q / (C49 * ge * dy)) ** 0.25
    return h, q, cc


def last_frame(rdir):
    return max(int(l.split(",")[0]) for l in open(f"{rdir}/FILENUMBER.csv")
               if not l.startswith("#") and int(l.split(",")[0]) < 9000)


def read_txt(path):
    return [[float(v) for v in line.split()] for line in open(path) if line.strip()]


def measure(name):
    rdir = f"result_{name}"
    k = last_frame(rdir)
    h = read_txt(f"{rdir}/H{k:04d}.txt")
    hs = read_txt(f"{rdir}/Hs{k:04d}.txt")
    vals, cs = [], []
    for j in range(len(h)):
        for i in range(len(h[j])):
            x = (i + 0.5) * mi.DX
            if X0 <= x <= X1:
                ht = h[j][i] + hs[j][i]
                vals.append(ht)
                cs.append(hs[j][i] / ht if ht > 0 else 0.0)
    m = sum(vals) / len(vals)
    cv = math.sqrt(sum((v - m) ** 2 for v in vals) / len(vals)) / m
    return m, cv, sum(cs) / len(cs)


def main():
    show = len(sys.argv) > 1 and sys.argv[1] == "table"
    ok = True
    rows = ["case            law          gc   <h_t> (m)  analytic (m)   error    CV      C (theory)"]
    for law, gc in mi.CASES:
        name = mi.case_name(law, gc)
        ha, q, cc = analytic(law, gc)
        m, cv, cm = measure(name)
        err = m / ha - 1.0
        rows.append(f"{name:15s} {law:11s} {gc:3d}   {m:9.4f}  {ha:12.4f}  {100 * err:+6.2f} %  {cv:6.4f}  {cm:.4f} ({cc:.4f})")
        if abs(err) > TOL_ANA:
            print(f"FAIL (1) {name}: <h_t> = {m:.4f} m が解析解 {ha:.4f} m と {100 * err:+.2f} % ずれる(許容 ±{100 * TOL_ANA:g} %)")
            ok = False
        if cv > TOL_CV:
            print(f"FAIL (1) {name}: 窓の変動係数 {cv:.4f} が {TOL_CV} 以上(等流になっていない)")
            ok = False
        if abs(cm - cc) > TOL_C:
            print(f"FAIL (1) {name}: 濃度 {cm:.6f} が流入の値 {cc:.6f} と違う")
            ok = False
    for law in mi.LAWS:
        r = analytic(law, 2)[0] / analytic(law, 1)[0]
        rows.append(f"discrimination {law:11s}: analytic h_t (2) / (1) = {r:.4f}")
        if abs(r - 1.0) < DISC_MIN:
            print(f"FAIL (2) {law}: 2 と 1 の解析解の比 {r:.4f} が 1 に近すぎる")
            ok = False
    if show or not ok:
        print("\n".join(rows))
    print("=== dbslope verification " + ("PASS" if ok else "FAIL") + " ===")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
