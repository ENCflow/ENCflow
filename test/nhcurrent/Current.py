#!/usr/bin/env python3
"""nhcurrent: 一様流 U0 上の線形波の波数を測り、分散関係と比べる(docs/nonhydrostatic_plan.md §11 Phase 5 Test 2)

  使い方: ./Current.py [result_dir ...]   既定は result(順流 NH)、result_c(逆流 NH)、result_0(静水 NH)、
                                          result_h(順流 静水圧)、result_hc(逆流 静水圧)
  両端の水位規定セル群の一方を振動させて波を出す(順流: 西端、逆流・静水: 東端)。
  x = 60〜100 m のプローブ 41 点の h(t) から、波列が定常で反射が戻る前の窓(順流 45〜95 s、
  逆流・静水 65〜100 s)で複素振幅 A(x) = (2/Tw)∫ η e^{−iωt} dt を取り、位相の x 勾配から波数 k、
  |A| から振幅の減衰を得る。理論: (ω − U0 k)² = gH Λ(k)/(1 + βΛ(k))(ENC の半離散 Λ、β = H²/4)。
  静水圧理論 (ω − U0 k)² = gHΛ と連続理論 (ω − U0 k)² = gk tanh kH も併記。
  順流は k > 0 の根(ω − U0 k > 0)、逆流は x の負方向へ進む波(k < 0)。計算本体の外(方針 10)。numpy。
"""
import sys, os, glob, math
import numpy as np
G = 9.8; H = 1.0; DX = 0.25; T = 2.24; U0 = 0.5
PD = 2.0 / (2.0 + math.sqrt(2.0))
OMEGA = 2 * math.pi / T
CASES = {"result": (U0, +1, 45, 95), "result_c": (U0, -1, 65, 100), "result_0": (0.0, -1, 65, 100),
         "result_h": (U0, +1, 45, 95), "result_hc": (U0, -1, 65, 100)}

def enc_lambda(k, dx=DX):
    lp = 1.0 - PD; ld = PD / 2.0
    return 2.0 * (lp * (1 - math.cos(k * dx)) + 2 * ld * (1 - math.cos(k * dx))) / dx**2

def solve_k(u0, sgn, model):
    """sgn = +1: +x へ進む波(k > 0)、−1: −x へ進む波(k < 0)。model: 'nh', 'hydro', 'exact'"""
    def f(k):
        lam = enc_lambda(abs(k))
        if model == "nh":
            w2 = G * H * lam / (1 + 0.25 * H * H * lam)
        elif model == "hydro":
            w2 = G * H * lam
        else:
            w2 = G * abs(k) * math.tanh(abs(k) * H)
        return (OMEGA - u0 * k) ** 2 - w2
    # 二分法: k の絶対値 0.05〜5 /m
    lo, hi = 0.05 * sgn, 5.0 * sgn
    flo = f(lo)
    for _ in range(200):
        mid = 0.5 * (lo + hi); fm = f(mid)
        if (fm > 0) == (flo > 0): lo, flo = mid, fm
        else: hi = mid
    return 0.5 * (lo + hi)

def probe(csv):
    t, h = [], []
    for line in open(csv):
        if line.startswith("#"): continue
        c = [float(x) for x in line.split(",")]
        t.append(c[0] * 3600.0); h.append(c[3])
    return np.array(t), np.array(h)

def analyze(resdir, u0, sgn, t1, t2):
    files = sorted(glob.glob(os.path.join(resdir, "probes", "probe*.csv")))
    x = 60.125 + np.arange(len(files)) * 1.0
    n_per = int((t2 - t1) / T); tw = n_per * T
    A = []
    for f in files:
        t, h = probe(f)
        sel = (t >= t1) & (t < t1 + tw)
        eta = h[sel] - h[sel].mean()
        A.append(2.0 / sel.sum() * np.sum(eta * np.exp(-1j * OMEGA * t[sel])))
    A = np.array(A)
    phase = np.unwrap(np.angle(A))
    k_meas = abs(np.polyfit(x, phase, 1)[0])     # |dφ/dx|(符号は進行方向の約束に依るので大きさで比べる)
    amp = np.abs(A)
    decay = np.polyfit(x, np.log(np.maximum(amp, 1e-12)), 1)[0]
    return x, k_meas, amp, decay

if __name__ == "__main__":
    dirs = sys.argv[1:] or list(CASES)
    print(f"{'case':10s} {'U0':>5s} dir {'k_meas':>8s} {'k_NH':>8s} {'k_hyd':>8s} {'k_exact':>8s} {'k/k_NH':>7s} {'k/k_hyd':>7s} {'kH':>5s} {'a(60m)':>7s} {'decay/40m':>9s}")
    for d in dirs:
        if not os.path.isdir(d): continue
        u0, sgn, t1, t2 = CASES.get(d, (U0, +1, 45, 95))
        x, km, amp, dec = analyze(d, u0, sgn, t1, t2)
        knh, khy, kex = solve_k(u0, sgn, "nh"), solve_k(u0, sgn, "hydro"), solve_k(u0, sgn, "exact")
        knh, khy, kex = abs(knh), abs(khy), abs(kex)
        print(f"{d:10s} {u0:5.2f} {'+x' if sgn > 0 else '-x':>3s} {km:8.4f} {knh:8.4f} {khy:8.4f} {kex:8.4f} {km/knh:7.4f} {km/khy:7.4f} {abs(km)*H:5.2f} {amp[0]*100:6.2f}cm {math.exp(dec*40)-1:+9.3f}")
