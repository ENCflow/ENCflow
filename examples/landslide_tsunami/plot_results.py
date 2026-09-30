#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# examples/landslide_tsunami の図化(result_A/B/B0/C を読んで figs/ に保存)
#   figs/profiles.png : 各ケースの中央断面(y=97.5 m)。地盤の変化と自由表面 z+h+hs の時間発展
#   figs/probes.png   : 湖内プローブ(x=298, 398, 548 m)の水面時系列の比較
#   figs/deposit.png  : t=120 s の地形変化 z−z0(中央断面)の比較
import os, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DX, J = 5.0, 19                         # 格子幅、中央行(0 始まり)
CASES = [("result_A",  "A: rockslide (bed layer only)",            "#2a78d6"),
         ("result_B",  "B: debris flow -> handover to bed layer",  "#eb6834"),
         ("result_B0", "B0: debris flow, mixture only",            "#8a8983"),
         ("result_C",  "C: submarine slide",                        "#2e9e5b")]
x = (np.arange(120) + 0.5) * DX
os.makedirs("figs", exist_ok=True)

def rd(rdir, name, k):
    return np.loadtxt("%s/%s%04d.txt" % (rdir, name, k))

def times(rdir):
    return {int(l.split(",")[0]): float(l.split(",")[2])
            for l in open(rdir + "/FILENUMBER.csv") if not l.startswith("#")}

# --- 1. 縦断図(4 ケース × [全体 / 湖面の拡大]) ---
fig, axes = plt.subplots(len(CASES), 2, figsize=(13, 3.2 * len(CASES)))
for (rdir, lab, col), (ax0, ax1) in zip(CASES, axes):
    tm = times(rdir)
    z0 = rd(rdir, "Z", 0)[J]
    ax0.plot(x, z0, "k-", lw=1, label="z0")
    for k in (2, 3, 4, 5, 6, 8, 12, 24):
        if k not in tm:
            continue
        h = rd(rdir, "H", k)[J]; z = rd(rdir, "Z", k)[J]
        try:
            hs = rd(rdir, "Hs", k)[J]
        except OSError:
            hs = np.zeros_like(h)
        s = np.where(h + hs > 0.01, z + h + hs, np.nan)
        ax0.plot(x, s, lw=1, label="t=%.0f s" % tm[k])
        ax1.plot(x, np.where(z0 < 0, s, np.nan), lw=1, label="t=%.0f s" % tm[k])
    ax0.plot(x, rd(rdir, "Z", 24)[J], "k--", lw=1, label="z (t=120 s)")
    ax0.set_ylim(-45, 90); ax0.set_ylabel("elevation (m)"); ax0.grid(); ax0.set_title(lab, fontsize=10)
    ax1.set_ylim(-3.5, 3.5); ax1.set_xlim(180, 600); ax1.set_ylabel("lake surface (m)"); ax1.grid()
axes[0][0].legend(fontsize=7, ncol=3); axes[-1][0].set_xlabel("x (m)"); axes[-1][1].set_xlabel("x (m)")
plt.tight_layout(); plt.savefig("figs/profiles.png", dpi=100); plt.close()

# --- 2. 湖内プローブの水面時系列 ---
fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
for ax, n in zip(axes, (3, 4, 5)):
    for rdir, lab, col in CASES:
        f = "%s/probes/probe%04d.csv" % (rdir, n)
        xx = float(open(f).readlines()[1].split(",")[1])
        d = np.loadtxt(f, delimiter=",", comments="#")
        ax.plot(d[:, 0] * 3600, d[:, 2] + d[:, 3] + d[:, 9], color=col, lw=1.2, label=lab)
    ax.set_ylabel("surface (m)\nx=%.0f m" % xx); ax.grid()
axes[0].legend(fontsize=8); axes[-1].set_xlabel("t (s)")
axes[0].set_title("lake free surface at probes (y = 97.5 m)")
plt.tight_layout(); plt.savefig("figs/probes.png", dpi=100); plt.close()

# --- 3. 地形変化の比較 ---
fig, ax = plt.subplots(figsize=(10, 4))
for rdir, lab, col in CASES:
    dz = rd(rdir, "Z", 24)[J] - rd(rdir, "Z", 0)[J]
    ax.plot(x, dz, color=col, lw=1.4, label=lab)
ax.axvline(200, color="k", lw=0.5); ax.axvline(300, color="k", lw=0.5)
ax.text(200, ax.get_ylim()[1] * 0.9, " shoreline", fontsize=8); ax.text(300, ax.get_ylim()[1] * 0.9, " basin floor", fontsize=8)
ax.set_xlabel("x (m)"); ax.set_ylabel("bed change z - z0 at t = 120 s (m)"); ax.grid(); ax.legend(fontsize=8)
plt.tight_layout(); plt.savefig("figs/deposit.png", dpi=100); plt.close()

# --- 数表(README 用) ---
A = DX * DX
for rdir, lab, col in CASES:
    z0 = rd(rdir, "Z", 0); dz = rd(rdir, "Z", 24) - z0
    bands = [np.clip(dz[:, (x >= a) & (x < b)], 0, None).sum() * A for a, b in ((200, 275), (275, 350))]
    reach = x[np.where(dz > 0.01)[1]].max()
    ex = []
    for n in (2, 3, 4, 5):
        f = "%s/probes/probe%04d.csv" % (rdir, n)
        d = np.loadtxt(f, delimiter=",", comments="#"); s = d[:, 2] + d[:, 3] + d[:, 9]; t = d[:, 0] * 3600
        ex.append("%+.2f@%.0fs/%+.2f" % (s.max(), t[s.argmax()], s.min()))
    print("%-10s shore(200-275) %6.0f  floor(275-350) %6.0f m3  reach %.0f m | x=212 %s | 298 %s | 398 %s | 548 %s"
          % (rdir, bands[0], bands[1], reach, *ex))
print("figs/profiles.png figs/probes.png figs/deposit.png")
