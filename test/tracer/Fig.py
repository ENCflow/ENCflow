#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# tracer の図化: figs/front.png(構成 A の前線と erfc 理論)、figs/plume.png(構成 B のプルーム)
import os, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import math
erfc = np.vectorize(math.erfc)
plt.rcParams.update({"font.family": ["IPAGothic", "DejaVu Sans"], "font.size": 10})
os.makedirs("figs", exist_ok=True)

def times(rdir):
    return {int(l.split(",")[0]): float(l.split(",")[2]) for l in open(rdir + "/FILENUMBER.csv") if not l.startswith("#")}

fig, axs = plt.subplots(1, 2, figsize=(12, 4.2))
ax = axs[0]
tk = times("result"); dx = 10.0
cols = ["#2a78d6", "#eb6834", "#4caf50"]
for n, k in enumerate((3, 6, 9)):
    t = tk[k]; c = np.loadtxt("result/C%04d.txt" % k).mean(axis=1) / 100.0
    x = (np.arange(len(c)) + 0.5) * dx
    ax.plot(x / 1000, c, color=cols[n], lw=1.8, label="t = %d 分 1 次風上" % round(t / 60))
    if os.path.isdir("result_m"):
        cm = np.loadtxt("result_m/C%04d.txt" % k).mean(axis=1) / 100.0
        ax.plot(x / 1000, cm, color=cols[n], lw=1.2, ls="-.", label="t = %d 分 MUSCL" % round(t / 60))
    u = 0.911; cr = u * 1.0 / dx; d = u * dx * (1 - cr) / 2   # u は前線速度の実測値(Check_tracer.py)
    ax.plot(x / 1000, 0.5 * erfc(-(x - u * t) / (2 * np.sqrt(d * t))), color=cols[n], lw=1.0, ls="--")
ax.set_xlabel("流下距離 (km)"); ax.set_ylabel("C / C0"); ax.set_xlim(0, 6)
ax.set_title("構成 A(dx = 10 m, dt = 1 s): 清水前線(実線 1 次風上、一点鎖線 MUSCL)と\nD = u·dx·(1−Cr)/2 = 4.1 m²/s の erfc 解(破線)", fontsize=9.5)
ax.legend(frameon=False, fontsize=9)
ax = axs[1]
tk = times("result_b"); k = max(kk for kk in tk if kk < 9000)
c = np.loadtxt("result_b/C%04d.txt" % k); ny, nx = c.shape
im = ax.imshow(np.where(c > 0.01, c, np.nan), extent=[0, nx * dx / 1000, 0, ny * dx], origin="upper", aspect="auto", cmap="viridis")
ax.set_xlim(0.3, 4.0)
xs = np.arange(0.6, 4.0, 0.05); u = 0.996; dy_th = 0.293 * u * dx
sig = np.sqrt(2 * dy_th * (xs * 1000 - 500) / u)
y0 = (ny - 30.5) * dx
ax.plot(xs, y0 + 2 * sig, "w--", lw=1); ax.plot(xs, y0 - 2 * sig, "w--", lw=1)
ax.set_xlabel("x (km)"); ax.set_ylabel("y (m)")
ax.set_title("構成 B: 点源の定常プルーム(1 次風上。白破線 = ±2σy、Dy = 0.293·u·dy)", fontsize=9.5)
if os.path.isdir("result_m_b"):
    tkm = times("result_m_b"); km = max(kk for kk in tkm if kk < 9000)
    cmb = np.loadtxt("result_m_b/C%04d.txt" % km)
    ax.contour(np.linspace(0, nx * dx / 1000, nx), np.linspace(ny * dx, 0, ny), np.where(cmb > 0.01, cmb, 0), levels=[0.02], colors="#eb6834", linewidths=1.0)
    ax.text(3.9, 95, "橙線: MUSCL の C = 0.02 mg/L 等値線", color="#eb6834", ha="right", fontsize=8.5)
plt.colorbar(im, ax=ax, label="C (mg/L)", shrink=0.85)
fig.tight_layout(); fig.savefig("figs/tracer.png", dpi=120)
print("written: figs/tracer.png")
