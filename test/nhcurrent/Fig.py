#!/usr/bin/env python3
"""test/nhcurrent(一様流上の線形波の分散関係)の結果を図にする。

  python3 Fig.py        → figs/nhcurrent.png

前提: ./Run.sh と ./encflow param_{0,c,h,hc}.txt で result, result_0, result_c,
      result_h, result_hc があること。Current.py の解析(窓内の複素振幅から
      波数 k を測る)をそのまま使う。
左: 順流 NH(result)の x = 60〜100 m のプローブの水位 η(t)の空間分布
    (t = 70 s の瞬間の η(x))と複素振幅の位相。
右: 5 ケースの計測 k と理論(1 層 NH・静水圧・連続理論)。
"""
import math, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = ["IPAGothic", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
os.chdir(here)
import Current as cur

labels = {"result_0": "静水 NH", "result": "順流 NH", "result_h": "順流 静水圧", "result_c": "逆流 NH", "result_hc": "逆流 静水圧"}
fig, axs = plt.subplots(1, 2, figsize=(14, 4.8))
ax = axs[0]
x, km, amp, dec = cur.analyze("result", *cur.CASES["result"])
import glob
files = sorted(glob.glob(os.path.join("result", "probes", "probe*.csv")))
eta_t = []
for f in files:
    t, h = cur.probe(f)
    sel = (t >= 45) & (t < 95)
    k = np.argmin(abs(t - 70.0)); eta_t.append(h[k] - h[sel].mean())
ax.plot(x, np.array(eta_t) * 100, "o-", ms=3, label="η(x, t = 70 s)")
knh = abs(cur.solve_k(cur.U0, +1, "nh"))
xx = np.linspace(60, 100, 400)
ph0 = np.angle(np.sum(np.array(eta_t) * np.exp(-1j * knh * (x - 60))))
ax.plot(xx, amp[0] * 100 * np.cos(knh * (xx - 60) + ph0), "r--", lw=1, label=f"理論 k_NH = {knh:.3f} /m(振幅は x = 60 m の計測値)")
ax.set_xlabel("x (m)"); ax.set_ylabel("水位偏差 η (cm)"); ax.grid(alpha=0.4); ax.legend(fontsize=9)
ax.set_title(f"順流 NH: 波長 {2*math.pi/km:.2f} m(計測 k = {km:.3f} /m)")

ax = axs[1]
rows = []
for i, d in enumerate(["result_0", "result", "result_h", "result_c", "result_hc"]):
    if not os.path.isdir(d): continue
    u0, sgn, t1, t2 = cur.CASES[d]
    try:
        _, km, amp, _ = cur.analyze(d, u0, sgn, t1, t2)
    except Exception:
        continue
    knh, khy, kex = [abs(cur.solve_k(u0, sgn, m)) for m in ("nh", "hydro", "exact")]
    rows.append((labels[d], km, knh, khy, kex, amp[0]))
    ax.plot([i - 0.2], [knh], "s", color="C3", ms=8, label="1 層 NH 理論" if i == 0 else None)
    ax.plot([i], [khy], "D", color="C0", ms=7, label="静水圧理論" if i == 0 else None)
    ax.plot([i + 0.2], [kex], "^", color="gray", ms=7, label="連続理論 ω² = gk tanh kH" if i == 0 else None)
    ax.plot([i - 0.2, i, i + 0.2], [km] * 3, "k-", lw=2, label="計測" if i == 0 else None)
ax.set_xticks(range(len(labels))); ax.set_xticklabels(list(labels.values()), fontsize=9)
ax.set_ylabel("波数 k (1/m)"); ax.grid(alpha=0.4, axis="y"); ax.legend(fontsize=9)
ax.set_title("波数の計測値と理論(T = 2.24 s、H = 1 m、U₀ = 0.5 m/s)")
fig.suptitle("test/nhcurrent — 一様流上の線形波の分散関係(非静水圧 Phase 5 Test 2)", fontsize=13)
fig.tight_layout()
fig.savefig(os.path.join(here, "figs", "nhcurrent.png"), dpi=110, bbox_inches="tight")
print("figs/nhcurrent.png")
for r in rows: print("%-12s k=%.4f k_NH=%.4f k_hyd=%.4f k_exact=%.4f a=%.2f cm" % (r[0], r[1], r[2], r[3], r[4], r[5] * 100))
