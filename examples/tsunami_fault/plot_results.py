#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# examples/tsunami_fault の図化(result_h / result_inst / result_nh を読んで figs/ に保存)
#   figs/deformation.png : 断層による最終地盤変位(fault2disp の出力)と地形の断面
#   figs/profiles.png    : 中央行(y = 75.5 km)の水面の時間発展(静水圧 / 瞬時 / NH + 加速度項)
#   figs/probes.png      : プローブの水位時系列
#   標準出力に数表(README 用)
import os, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams.update({"font.family": ["IPAGothic", "DejaVu Sans"], "font.size": 10})

DX, J = 1.0, 74                       # km、中央行(0 始まり。y = 75.5 km)
CASES = [("result_h", "静水圧(30 s 立ち上がり)", "#2a78d6"),
         ("result_inst", "静水圧(瞬時変位)", "#8a8983"),
         ("result_nh", "非静水圧 + 加速度項", "#eb6834")]
x = (np.arange(200) + 0.5) * DX
os.makedirs("figs", exist_ok=True)

def times(rdir):
    return {int(l.split(",")[0]): float(l.split(",")[2]) for l in open(rdir + "/FILENUMBER.csv") if not l.startswith("#")}

def surf(rdir, k):
    e = np.loadtxt("%s/E%04d.txt" % (rdir, k)); z = np.loadtxt("%s/Z%04d.txt" % (rdir, k))
    return np.where(e - z > 0.01, e, np.nan)

def probe(rdir, n):
    d = np.loadtxt("%s/probes/probe%04d.csv" % (rdir, n), delimiter=",", comments="#")
    return d[:, 0] * 3600, d[:, 2] + d[:, 3]

# --- 1. 変位と地形 ---
d = np.loadtxt("bm/disp_0010.txt"); z0 = np.loadtxt("z.txt")
fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(13, 4.6), gridspec_kw={"width_ratios": [1.2, 1]})
im = ax0.imshow(d, extent=[0, 200, 0, 150], origin="upper", cmap="RdBu_r", vmin=-2.2, vmax=2.2)
ax0.plot([120, 120], [45, 105], "k-", lw=1.5, label="上端(深さ 5 km)")
ax0.plot([149, 149], [45, 105], "k--", lw=1.0, label="下端(深さ 12.8 km)")
ax0.plot([2.9, 2.9], [0, 150], color="#52514e", lw=0.8)
ax0.set_xlabel("x (km)"); ax0.set_ylabel("y (km)"); ax0.set_title("最終地盤変位 (m)。逆断層、走向 N-S、傾斜 15°(東へ)", fontsize=10); ax0.legend(loc="lower left", fontsize=8)
plt.colorbar(im, ax=ax0, fraction=0.03)
ax1.plot(x, z0[J], "k-", lw=1.2, label="地盤 z")
ax1.plot(x, d[J] * 300, color="#eb6834", lw=1.2, label="変位 × 300")
ax1.axhline(0, color="#8a8983", lw=0.6); ax1.set_xlabel("x (km)"); ax1.set_ylabel("z (m)"); ax1.grid()
ax1.set_title("中央行 y = 75.5 km の地形と変位", fontsize=10); ax1.legend(fontsize=8)
plt.tight_layout(); plt.savefig("figs/deformation.png", dpi=100); plt.close()

# --- 2. 中央行の水面 ---
fig, axes = plt.subplots(2, 2, figsize=(13, 7.5))
for ax, tsel in zip(axes.flat, (120.0, 300.0, 600.0, 1200.0)):
    for rdir, lab, col in CASES:
        tm = times(rdir); k = min(tm, key=lambda q: abs(tm[q] - tsel))
        ax.plot(x, surf(rdir, k)[J], color=col, lw=1.2, label=lab)
    ax.set_title("t = %.0f s" % tsel, fontsize=10); ax.grid(); ax.set_xlabel("x (km)"); ax.set_ylabel("水位 (m)"); ax.set_xlim(0, 200)
axes.flat[0].legend(fontsize=8)
plt.tight_layout(); plt.savefig("figs/profiles.png", dpi=100); plt.close()

# --- 3. プローブ ---
PR = [(1, "上端直上 x = 120.5 km(水深 2000 m)"), (2, "斜面下端 x = 60.5 km"), (3, "沿岸 x = 10.5 km(水深 268 m)"),
      (4, "東 x = 180.5 km"), (5, "南 y = 30.5 km(断層端の外)")]
fig, axes = plt.subplots(5, 1, figsize=(10, 12), sharex=True)
rows = []
for ax, (n, lab) in zip(axes, PR):
    vals = []
    for rdir, cl, col in CASES:
        t, e = probe(rdir, n)
        ax.plot(t / 60, e, color=col, lw=1.1, label=cl)
        i = int(np.argmax(e))
        vals.append((e.max(), t[i], e.min()))
    rows.append((lab, vals))
    ax.set_ylabel("水位 (m)"); ax.grid(); ax.set_title(lab, fontsize=9, loc="left")
axes[0].legend(fontsize=8); axes[-1].set_xlabel("t (min)")
plt.tight_layout(); plt.savefig("figs/probes.png", dpi=100); plt.close()

print("| プローブ | " + " | ".join("%s 最高 (m) / 到達 (s) / 最低 (m)" % c[1] for c in CASES) + " |")
print("|---|" + "---:|" * len(CASES))
for lab, vals in rows:
    print("| %s | " % lab + " | ".join("%.3f / %.0f / %.3f" % v for v in vals) + " |")
