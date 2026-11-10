#!/usr/bin/env python3
"""V 字流域の降雨流出の理論解(運動学的波)を data/analytic.csv に書く(make が呼ぶ)。

  python3 analytic.py            data/analytic.csv(1 分ごと。列: t(min), q_hill(m2/s), Q_hill(m3/s),
                                 Q_out(m3/s), h_out(m))と、要点の数値を表示する
  python3 analytic.py --rect     水路を矩形断面(径深 Wh/(W + 2h))として解く(比較用。既定は広幅 = 径深 h)

式(Overton & Brakensiek 1973、Di Giammarco ら 1996、Stephenson & Meadows 1986):

  斜面(幅 B、勾配 S_S、粗度 n_S、一様な雨 i): 単位幅流量 q = α h^m(α = √S_S / n_S、m = 5/3)。
    立ち上がり  q(B, t) = α (i t)^m      (t ≤ t_e)         t_e = (B / (α i^(m−1)))^(1/m)
    平衡        q = i B                 (t_e ≤ t ≤ t_r)   t_r = 雨の終わり
    逓減(t > t_r。雨が止んだ後は特性曲線に沿って h が一定): 脚の水深 h は
                B − α h^m / i = m α h^(m−1) (t − t_r) の解、q = α h^m
    閉じた式で、数値計算は逓減の非線形方程式を解くだけ。この問題では t_e(29.4 分)< t_r(90 分)
    なので平衡に達してから逓減に入る。

  水路(幅 W、勾配 S_C、粗度 n_C、側方流入 q_L(t) = 2 q(B, t) + i(t) W): 運動学的波
    ∂A/∂t + ∂Q/∂x = q_L(t)、 Q = (√S_C / n_C) A R^(2/3)、 A = W h、 R = h(広幅。ENCflow の水路の
    セルも底面の摩擦だけで岸の摩擦を持たないので、これに合わせる。--rect の R = Wh/(W + 2h) では
    立ち上がりが最大 2 % 遅い)
    を特性曲線 dx/dt = dQ/dA、dh/dt = q_L / W に沿って数値積分する(側方流入が時刻だけの関数なので、
    上流端 x = 0 を時刻 τ に出た特性曲線の水深は h = H(t) − H(τ)、H(t) = ∫ q_L / W dt)。
    上流端 x = 0 を t = 0 に出た特性曲線が出口に着くまでは、水路の水深は場所によらず H(t)。
    出口のピーク Q = 2 i B L + i W L = 4.86 m³/s は水路の式によらない。
    閉じた式はなく、特性曲線の積分(時間刻み 0.5 s、特性曲線の間隔 2 s)の結果を「理論解」と呼ぶ。

寸法と粗度は make_inputs.py から読む(同じ値を使う)。
"""
import os
import sys
import numpy as np
import make_inputs as M

G_M = 5.0 / 3.0
I = M.P_MMH / 1000.0 / 3600.0            # 降雨強度 (m/s)
T_R = M.T_RAIN * 60.0                     # 雨の終わり (s)
T_END = M.T_END * 60.0
ALPHA_S = np.sqrt(M.S_S) / M.N_S
WIDE = "--rect" not in sys.argv[1:]


def hill_q(t):
    """斜面の脚の単位幅流量 q(B, t) (m2/s)。t は配列可。"""
    t = np.asarray(t, dtype=float)
    te = (M.B / (ALPHA_S * I ** (G_M - 1.0))) ** (1.0 / G_M)
    if te > T_R:
        sys.exit("雨が平衡の前に止む(t_e > t_r)場合は実装していない")
    q = np.where(t < te, ALPHA_S * (I * np.clip(t, 0.0, None)) ** G_M, I * M.B)
    rec = t > T_R
    if rec.any():
        tr = t[rec] - T_R
        he = (I * M.B / ALPHA_S) ** (1.0 / G_M)
        # B − α h^m / i − m α h^(m−1) tr = 0 を h ∈ (0, he] で二分法
        lo, hi = np.zeros_like(tr), np.full_like(tr, he)
        for _ in range(80):
            mid = 0.5 * (lo + hi)
            f = M.B - ALPHA_S * mid ** G_M / I - G_M * ALPHA_S * mid ** (G_M - 1.0) * tr
            lo = np.where(f > 0.0, mid, lo)
            hi = np.where(f > 0.0, hi, mid)
        q[rec] = ALPHA_S * (0.5 * (lo + hi)) ** G_M
    return q, te


def hill_h(t, x):
    """斜面の尾根から x (m) の位置の水深 (m)(x = B が脚。hill_q と同じ式で、位置を変えたもの。
    plot_results.py が斜面の 2 列目のプローブと比べる)。t は配列可。"""
    t = np.asarray(t, dtype=float)
    te = (x / (ALPHA_S * I ** (G_M - 1.0))) ** (1.0 / G_M)
    he = (I * x / ALPHA_S) ** (1.0 / G_M)
    h = np.where(t < te, I * np.clip(t, 0.0, None), he)
    rec = t > T_R
    if rec.any():
        tr = t[rec] - T_R
        lo, hi = np.zeros_like(tr), np.full_like(tr, he)
        for _ in range(80):
            mid = 0.5 * (lo + hi)
            f = x - ALPHA_S * mid ** G_M / I - G_M * ALPHA_S * mid ** (G_M - 1.0) * tr
            lo = np.where(f > 0.0, mid, lo)
            hi = np.where(f > 0.0, hi, mid)
        h[rec] = 0.5 * (lo + hi)
    return h


def chan_Q(h):
    """水路の流量 Q(h) (m3/s)。既定は広幅(径深 h)、--rect で矩形断面(径深 Wh/(W + 2h))。"""
    h = np.clip(h, 0.0, None)
    R = h if WIDE else M.W * h / (M.W + 2.0 * h)
    return np.sqrt(M.S_C) / M.N_C * M.W * h * R ** (2.0 / 3.0)


def chan_c(h):
    """波速 dQ/dA = (1/W) dQ/dh(数値微分)。"""
    dh = 1e-6
    return (chan_Q(h + dh) - chan_Q(np.clip(h - dh, 0.0, None))) / (h + dh - np.clip(h - dh, 0.0, None)) / M.W


def solve(dt=0.5, dtau=2.0):
    t = np.arange(0.0, T_END + dt / 2, dt)
    qh, te = hill_q(t)
    rain = np.where(t < T_R, I, 0.0)
    qL = 2.0 * qh + rain * M.W                       # 側方流入 (m2/s)
    H = np.concatenate([[0.0], np.cumsum(0.5 * (qL[1:] + qL[:-1]) * dt)]) / M.W   # ∫ q_L/W dt
    # 特性曲線: 上流端を時刻 τ に出る(τ = 0 は t = 0 の全区間の水深も表す)
    tau = np.arange(0.0, T_END, dtau)
    x = np.zeros_like(tau)
    arrive_t = np.full_like(tau, np.nan)
    arrive_h = np.full_like(tau, np.nan)
    for k in range(1, len(t)):
        active = (t[k - 1] >= tau - 1e-9) & np.isnan(arrive_t)
        if not active.any():
            continue
        Hk = np.interp(tau[active], t, H)
        h0 = H[k - 1] - Hk
        h1 = H[k] - Hk
        c = 0.5 * (chan_c(h0) + chan_c(h1))
        xn = x[active] + c * dt
        hit = xn >= M.L
        if hit.any():
            idx = np.nonzero(active)[0][hit]
            frac = (M.L - x[idx]) / (xn[hit] - x[idx])
            arrive_t[idx] = t[k - 1] + frac * dt
            arrive_h[idx] = h0[hit] + frac * (h1[hit] - h0[hit])
        x[active] = xn
    # 出口の水深: τ = 0 の特性曲線の到着 T_L までは H(t)、以後は到着の列
    T_L = arrive_t[0]
    ok = ~np.isnan(arrive_t)
    tm = np.arange(0.0, T_END + 1e-9, 60.0)
    h_out = np.where(tm < T_L, np.interp(tm, t, H), np.interp(tm, arrive_t[ok], arrive_h[ok]))
    Q_out = chan_Q(h_out)
    qh_m, _ = hill_q(tm)
    return tm, qh_m, Q_out, h_out, te, T_L


def main():
    tm, qh, Q, h, te, T_L = solve()
    os.makedirs("data", exist_ok=True)
    with open("data/analytic.csv", "w") as f:
        f.write("# V-shaped catchment, kinematic-wave solution (analytic.py%s)\n" % ("" if WIDE else " --rect"))
        f.write("# t(min), q_hill(m2/s), Q_hill(m3/s)[one side x L], Q_out(m3/s), h_out(m)\n")
        for row in zip(tm / 60.0, qh, qh * M.L, Q, h):
            f.write("%.1f, %.6e, %.5f, %.5f, %.5f\n" % row)
    Qe = 2.0 * I * M.B * M.L + I * M.W * M.L
    he = (I * M.B / ALPHA_S) ** (1.0 / G_M)
    i50 = np.argmax(Q >= 0.5 * Qe)
    print("斜面: 平衡到達 t_e = %.1f 分, 平衡 q_e = %.4e m2/s (×1000 m = %.3f m3/s), 脚の等流水深 %.4f m"
          % (te / 60, I * M.B, I * M.B * M.L, he))
    print("水路: 上流端を t = 0 に出た波の出口到着 %.1f 分, 出口のピーク %.3f m3/s(式 %.3f), 出口の水深 %.4f m,"
          " 50 %% 到達 %.0f 分, 90 分の流量 %.3f" % (T_L / 60, Q.max(), Qe, h.max(), tm[i50] / 60, Q[90]))
    print("data/analytic.csv を書いた(%s)" % ("広幅" if WIDE else "矩形断面"))


if __name__ == "__main__":
    main()
