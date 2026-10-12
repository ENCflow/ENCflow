#!/usr/bin/env python3
"""test/culvert の図を figs/*.png に描く(事前に ./Run.sh を実行しておく)。

  python3 Fig.py

- figs/law.png : Log の S(m) から復元した流量 Q = -A_total dS/dt を上流水深
                 h1 = S A_total / A_up に対して描き、流量則(堰・管路・min)と重ねる
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
matplotlib.rcParams["font.family"] = ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs("figs", exist_ok=True)

G = 9.8; B = D = 1.0; CE = 0.5
A_TOT = 132 * 100.0; A_UP = 110 * 100.0


def read_log(path):
    t, s = [], []
    for line in open(path):
        f = line.split()
        if len(f) < 3 or ":" not in f[0]:
            continue
        hh, mm, ss = f[0].split(":")
        t.append(int(hh) * 3600 + int(mm) * 60 + float(ss)); s.append(float(f[2]))
    return np.array(t), np.array(s)


def law(h1):
    qw = 0.35 * B * h1 * np.sqrt(2 * G * h1)
    cp = B * D * np.sqrt(2 * G / (1 + CE))
    dc = np.minimum(D, (qw ** 2 / (G * B ** 2)) ** (1 / 3))
    qp = np.where(h1 >= D, cp * np.sqrt(np.maximum(h1 - 0.5 * (dc + D), 0)), np.nan)
    q = np.where(h1 >= D, np.minimum(qw, np.nan_to_num(qp, nan=np.inf)), qw)
    return qw, qp, q


t, s = read_log("result/Log.txt")
q_num = -A_TOT * np.diff(s) / np.diff(t)
h1_mid = 0.5 * (s[1:] + s[:-1]) * A_TOT / A_UP
h = np.linspace(0.05, 3.0, 600); qw, qp, q = law(h)

fig, ax = plt.subplots(figsize=(7, 4.5))
ax.plot(h, qw, "--", color="tab:blue", lw=1.2, label="堰 Q_w = 0.35 B h₁√(2g h₁)")
ax.plot(h, qp, "--", color="tab:orange", lw=1.2, label="管路 Q_p = C_p√(η_u − (z_out + (d_c+D)/2))")
ax.plot(h, q, "-", color="k", lw=1.8, label="流量則 Q = min(Q_w, Q_p)(h₁ ≥ D)")
ax.plot(h1_mid, q_num, "o", color="tab:red", ms=3.5, label="計算(S の差分から復元)")
ax.axvline(D, color="gray", lw=0.8, ls=":")
ax.set(xlim=(0, 3.05), ylim=(0, 6), xlabel="上流水深 h₁ = η_u − z_in (m)", ylabel="Q (m³/s)",
       title="カルバート 1×1 m の排水試験: 復元流量と流量則")
ax.legend(fontsize=8, loc="upper left"); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig("figs/law.png", dpi=120)

# 所見用の数値
mono = np.all(np.diff(q_num) <= 1e-9) and np.all(np.diff(h1_mid) < 0)
print("Q monotone decreasing with falling h1:", mono)
print("Q range: %.3f -> %.3f m3/s, h1: %.3f -> %.3f m" % (q_num[0], q_num[-1], h1_mid[0], h1_mid[-1]))
for hc in (2.5, 1.5, 1.0, 0.6):
    k = np.argmin(abs(h1_mid - hc)); _, _, ql = law(np.array([h1_mid[k]]))
    print("h1=%.3f  Q_num=%.3f  Q_law=%.3f  (%.1f%%)" % (h1_mid[k], q_num[k], ql[0], 100 * (q_num[k] / ql[0] - 1)))
