#!/usr/bin/env python3
"""V 字流域の降雨流出を運動学的波の理論解と比べて合否を判定する(Python の標準ライブラリだけ)。

  python3 Check_vshaped.py [result_r0 result_r45 ...]    既定は result_r0 と result_r45

読むもの: <resdir>/fluxes/flux0001.csv(出口の計測面の流量)、flux0002.csv(左岸側の斜面の脚から水路へ
入る流量)、<resdir>/H9998.txt(終了時の水深)、対応する data_<向き>/catch.txt(流域のセル)。

理論解(examples/benchmark/v-shaped/analytic.py と同じ式。こちらは標準ライブラリで独立に計算する):
  斜面  q = α h^(5/3)(α = √S_S / n_S)。立ち上がり q(B, t) = α (i t)^(5/3)(t ≤ t_e)、平衡 i B、
        雨の後は B − α h^m / i = m α h^(m−1)(t − t_r) の解(Overton & Brakensiek 1973)
  水路  側方流入 q_L = 2 q(B, t) + i W の運動学的波(広幅。Q = (√S_C / n_C) W h^(5/3))を特性曲線
        dx/dt = dQ/dA、dh/dt = q_L / W に沿って数値積分(Di Giammarco ら 1996 の解法。時間刻み 1 s、
        特性曲線の間隔 10 s)。出口のピークは i (2BL + WL) = 4.86 m³/s

指標と合否(1 分ごとの値。examples/benchmark/v-shaped/check.py と同じ目安):
  NRMSE  = √(平均((Q − Q_理論)²)) / 理論のピーク          ≤ 0.04(出口)、≤ 0.04(斜面の脚)
  格子比 = ピーク / (降雨強度 × 格子上の流域の面積)         |格子比 − 1| ≤ 0.01
  t50    = 理論のピークの半分に初めて達する時刻 (min)       |t50 − t50_理論| ≤ 3 分
  収支   = (出口を通った水量 + 終了時に流域に残る水量)/ 流域に降った雨   |収支 − 1| ≤ 0.01
終了コード: 0 = 全ケース PASS、1 = FAIL あり
"""
import math
import os
import sys

# 幾何・雨(make_init.py と対で保守する)
L, W, B = 1000.0, 20.0, 800.0
S_C, S_S = 0.02, 0.05
N_S, N_C = 0.015, 0.15
DX = 20.0
I = 10.8 / 1000.0 / 3600.0          # 降雨強度 (m/s)
T_R = 90.0 * 60.0                   # 雨の終わり (s)
T_END = 180.0 * 60.0
M = 5.0 / 3.0
ALPHA_S = math.sqrt(S_S) / N_S
ALPHA_C = math.sqrt(S_C) / N_C
Q_TH = 2.0 * I * B * L + I * W * L  # 出口のピーク 4.86 m3/s
QH_TH = I * B * L                   # 斜面 1 側 × 1000 m の平衡 2.4 m3/s
TOL = {"nrmse": 0.04, "nrmse_h": 0.04, "ratio": 0.01, "t50": 3.0, "closure": 0.01}


def hill_q(t):
    """斜面の脚の単位幅流量 (m2/s)。"""
    te = (B / (ALPHA_S * I ** (M - 1.0))) ** (1.0 / M)
    if t <= T_R:
        return ALPHA_S * (I * t) ** M if t < te else I * B
    he = (I * B / ALPHA_S) ** (1.0 / M)
    tr = t - T_R
    lo, hi = 0.0, he
    for _ in range(60):      # B − α h^m / i − m α h^(m−1) tr = 0 を二分法
        mid = 0.5 * (lo + hi)
        f = B - ALPHA_S * mid ** M / I - M * ALPHA_S * mid ** (M - 1.0) * tr
        if f > 0.0:
            lo = mid
        else:
            hi = mid
    return ALPHA_S * (0.5 * (lo + hi)) ** M


def theory(dt=1.0, dtau=10.0):
    """1 分ごとの (t(min), Q_hill(m3/s), Q_out(m3/s))。"""
    nt = int(T_END / dt) + 1
    t = [k * dt for k in range(nt)]
    ql = [2.0 * hill_q(tk) + (I * W if tk < T_R else 0.0) for tk in t]      # 側方流入 (m2/s)
    H = [0.0] * nt                                                           # ∫ q_L / W dt
    for k in range(1, nt):
        H[k] = H[k - 1] + 0.5 * (ql[k] + ql[k - 1]) * dt / W

    def celerity(h):
        return M * ALPHA_C * max(h, 0.0) ** (M - 1.0)

    arrivals = []          # (到着時刻 s, 出口の水深)
    tau = 0.0
    while tau < T_END:
        k0 = int(round(tau / dt))
        x = 0.0
        k = k0
        while k + 1 < nt:
            h0 = H[k] - H[k0]
            h1 = H[k + 1] - H[k0]
            c = 0.5 * (celerity(h0) + celerity(h1))
            xn = x + c * dt
            if xn >= L:
                frac = (L - x) / (xn - x) if xn > x else 1.0
                arrivals.append((t[k] + frac * dt, h0 + frac * (h1 - h0)))
                break
            x = xn
            k += 1
        tau += dtau
    T_L = arrivals[0][0]

    def h_out(tm):
        if tm < T_L:
            k = min(int(tm / dt), nt - 1)
            return H[k]
        for (ta, ha), (tb, hb) in zip(arrivals, arrivals[1:]):
            if ta <= tm <= tb:
                return ha + (hb - ha) * (tm - ta) / (tb - ta) if tb > ta else ha
        return arrivals[-1][1]

    out = []
    for m in range(int(T_END / 60.0) + 1):
        tm = m * 60.0
        out.append((float(m), hill_q(tm) * L, ALPHA_C * W * h_out(tm) ** M))
    return out


def read_flux(path):
    t, q = [], []
    for line in open(path):
        if line.startswith("#"):
            continue
        c = line.split(",")
        if len(c) < 3:
            continue
        t.append(float(c[1]))
        q.append(float(c[2]))
    return t, q


def interp(x, xs, ys):
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    lo, hi = 0, len(xs) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if xs[mid] <= x:
            lo = mid
        else:
            hi = mid
    return ys[lo] + (ys[hi] - ys[lo]) * (x - xs[lo]) / (xs[hi] - xs[lo])


def t50(t, q, q50):
    for tk, qk in zip(t, q):
        if qk >= q50:
            return tk
    return float("nan")


def read_matrix(path):
    return [[float(v) for v in line.split()] for line in open(path) if line.strip()]


def check_case(resdir, th):
    datadir = "data_" + resdir.split("_", 1)[1]
    t, q = read_flux(os.path.join(resdir, "fluxes", "flux0001.csv"))
    th_t = [r[0] for r in th]
    th_qh = [r[1] for r in th]
    th_q = [r[2] for r in th]
    qth = [interp(tk, th_t, th_q) for tk in t]
    _, qh = read_flux(os.path.join(resdir, "fluxes", "flux0002.csv"))
    qhth = [interp(tk, th_t, th_qh) for tk in t]
    nrmse = math.sqrt(sum((a - b) ** 2 for a, b in zip(q, qth)) / len(q)) / Q_TH
    nrmse_h = math.sqrt(sum((a - b) ** 2 for a, b in zip(qh, qhth)) / len(qh)) / QH_TH
    H = read_matrix(os.path.join(resdir, "H9998.txt"))
    catch = read_matrix(os.path.join(datadir, "catch.txt"))
    ncatch = sum(int(v) for row in catch for v in row)
    v_end = sum(h for hr, cr in zip(H, catch) for h, c in zip(hr, cr) if c > 0.5) * DX * DX
    v_out = sum(0.5 * (q[k] + q[k - 1]) * (t[k] - t[k - 1]) * 60.0 for k in range(1, len(t)))
    a_catch = ncatch * DX * DX
    r = {"nrmse": nrmse, "nrmse_h": nrmse_h, "peak": max(q), "grid_ratio": max(q) / (I * a_catch),
         "t50": t50(t, q, 0.5 * Q_TH), "t50_th": t50(th_t, th_q, 0.5 * Q_TH),
         "closure": (v_out + v_end) / (I * T_R * a_catch), "area": a_catch / 1e6}
    r["pass"] = (r["nrmse"] <= TOL["nrmse"] and r["nrmse_h"] <= TOL["nrmse_h"]
                 and abs(r["grid_ratio"] - 1.0) <= TOL["ratio"]
                 and abs(r["t50"] - r["t50_th"]) <= TOL["t50"] and abs(r["closure"] - 1.0) <= TOL["closure"])
    return r


def main():
    resdirs = sys.argv[1:] or ["result_r0", "result_r45"]
    th = theory()
    print("theory: peak %.3f m3/s, t50 %.0f min, hillslope equilibrium %.3f m3/s" % (Q_TH, t50([r[0] for r in th], [r[2] for r in th], 0.5 * Q_TH), QH_TH))
    nfail = 0
    for d in resdirs:
        r = check_case(d, th)
        print("%s: area %.4f km2, NRMSE outlet %.4f (tol %.2f), NRMSE hillslope %.4f (tol %.2f), peak %.3f, grid ratio %.4f (tol %.2f), "
              "t50 %.0f min (theory %.0f, tol %.0f), closure %.4f (tol %.2f) : %s"
              % (d, r["area"], r["nrmse"], TOL["nrmse"], r["nrmse_h"], TOL["nrmse_h"], r["peak"], r["grid_ratio"], TOL["ratio"],
                 r["t50"], r["t50_th"], TOL["t50"], r["closure"], TOL["closure"], "PASS" if r["pass"] else "FAIL"))
        if not r["pass"]:
            nfail += 1
    print("== vshaped: %d case(s), %d FAIL ==" % (len(resdirs), nfail))
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
