#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# examples/meander の図化(result / result_cohesive / result_varq / result_fix を読んで figs/ に保存)
#   figs/planform.png : 初期と終了時の水深(河道の位置)と河床変化 z−z0(4 構成)
#   figs/sections.png : 湾曲頂点(x = 350, 450 m)の横断面の時間発展(非粘着性)
#   figs/metrics.png  : 頂点の河道中心の横移動と河幅の時間発展
#   figs/fixation.png : 定着構成の定着度 Fx と終了時の河道(result_fix があるとき)
# 数表(README 用)を標準出力に書く
import os, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import make_init as mi

DX, NX, NY = mi.DX, mi.NX, mi.NY
MORFAC = 50.0
CASES = [("result", "non-cohesive banks (f_repose)", "#2a78d6"),
         ("result_cohesive", "cohesive banks (f_berode + f_repose)", "#d6572a"),
         ("result_varq", "non-cohesive, Q 15/1.5 m3/s without fixation", "#8a6fd1"),
         ("result_fix", "non-cohesive + fixation (f_fixation, Q 15/1.5 m3/s)", "#2a9d5a")]
CASES = [c for c in CASES if os.path.isdir(c[0])]
APEX = [250, 350, 450, 550, 650]                   # 頂点付近の x (m)
x = (np.arange(NX) + 0.5) * DX
y = (np.arange(NY) + 0.5) * DX
os.makedirs("figs", exist_ok=True)
z0 = np.loadtxt("z.txt"); h0 = np.loadtxt("h.txt")


def rd(rdir, name, k):
    return np.loadtxt("%s/%s%04d.txt" % (rdir, name, k))


def times(rdir):
    return {int(l.split(",")[0]): float(l.split(",")[2])
            for l in open(rdir + "/FILENUMBER.csv") if not l.startswith("#") and int(l.split(",")[0]) < 9000}


def centerline(h):
    c = np.full(NX, np.nan); w = np.zeros(NX)
    for i in range(NX):
        m = h[:, i] > 0.1
        if m.any():
            c[i] = y[m].mean(); w[i] = m.sum() * DX
    return c, w


# --- 1. 平面図 ---
fig, axes = plt.subplots(len(CASES) + 1, 1, figsize=(14, 3.2 * (len(CASES) + 1)), sharex=True)
ext = [0, NX * DX, 0, NY * DX]
axes[0].imshow(np.where(h0 > 0.05, h0, np.nan), origin="lower", extent=ext, cmap="Blues", vmin=0, vmax=2)
axes[0].set_title("initial channel (depth, m)")
for ax, (rdir, label, col) in zip(axes[1:], CASES):
    tm = times(rdir); K = max(tm)
    h = rd(rdir, "H", K); z = rd(rdir, "Z", K); dz = z - z0
    im = ax.imshow(dz, origin="lower", extent=ext, cmap="RdBu_r", vmin=-1.0, vmax=1.0)
    ax.contour(x, y, h0 > 0.05, levels=[0.5], colors="k", linewidths=0.4)
    ax.contour(x, y, h > 0.05, levels=[0.5], colors=col, linewidths=0.8)
    ax.set_title("%s: bed change z - z0 after %.0f h (morphological time); black = initial banks, colour = final" % (label, tm[K] * MORFAC / 3600))
    plt.colorbar(im, ax=ax, shrink=0.8)
for ax in axes:
    ax.set_ylabel("y (m)")
axes[-1].set_xlabel("x (m)")
plt.tight_layout(); plt.savefig("figs/planform.png", dpi=100); plt.close()

# --- 2. 横断面(非粘着性。頂点 2 箇所) ---
rdir = CASES[0][0]; tm = times(rdir); ks = sorted(tm)
fig, axes = plt.subplots(1, 2, figsize=(13, 4.2))
for ax, xa in zip(axes, (350, 450)):
    i = int(xa / DX)
    for k in ks:
        z = rd(rdir, "Z", k); h = rd(rdir, "H", k)
        ax.plot(y, z[:, i], color=plt.cm.viridis(k / max(ks)), lw=1.2, label="%.0f h" % (tm[k] * MORFAC / 3600))
        if k == ks[-1]:
            ax.plot(y, (z + np.where(h > 0.05, h, np.nan))[:, i], "k--", lw=0.8, label="water surface (final)")
    jc = np.where(h0[:, i] > 0)[0]
    ax.set_xlim(y[jc.min()] - 20, y[jc.max()] + 20); ax.set_ylim(z0[jc, i].min() - 2.5, z0[jc, i].min() + 2.0)
    ax.set_title("cross section at x = %d m (outer bank on the %s side)" % (xa, "high-y" if xa == 350 else "low-y"))
    ax.set_xlabel("y (m)"); ax.set_ylabel("z (m)"); ax.grid(alpha=0.3)
axes[0].legend(fontsize=8, ncol=2)
plt.tight_layout(); plt.savefig("figs/sections.png", dpi=100); plt.close()

# --- 3. 指標の時間発展と数表 ---
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
print("| case | t (h) | " + " | ".join("x=%d: dy (m) / width (m)" % xa for xa in APEX) + " | min dz (m) |")
print("|---|---|" + "---|" * len(APEX) + "---|")
c0, w0 = centerline(h0)
for rdir, label, col in CASES:
    tm = times(rdir); ks = sorted(tm)
    T = []; D = {xa: [] for xa in APEX}; Wd = {xa: [] for xa in APEX}
    for k in ks:
        h = rd(rdir, "H", k); z = rd(rdir, "Z", k)
        c, w = centerline(h)
        T.append(tm[k] * MORFAC / 3600)
        for xa in APEX:
            i = int(xa / DX); D[xa].append(c[i] - c0[i]); Wd[xa].append(w[i])
        print("| %s | %.0f | " % (label.split(" (")[0], T[-1]) + " | ".join("%+.1f / %.0f" % (D[xa][-1], Wd[xa][-1]) for xa in APEX) + " | %.2f |" % (z - z0).min())
    for xa in APEX[1:3]:
        axes[0].plot(T, D[xa], "-o", color=col, alpha=0.5 + 0.5 * (xa == 350), ms=3, label="%s, x=%d" % (label.split(" (")[0], xa))
        axes[1].plot(T, Wd[xa], "-o", color=col, alpha=0.5 + 0.5 * (xa == 350), ms=3)
axes[0].set_title("lateral shift of the channel centre at the apexes"); axes[0].set_xlabel("morphological time (h)"); axes[0].set_ylabel("dy (m)"); axes[0].grid(alpha=0.3); axes[0].legend(fontsize=8)
axes[1].set_title("channel width at the apexes"); axes[1].set_xlabel("morphological time (h)"); axes[1].set_ylabel("width (m)"); axes[1].grid(alpha=0.3)
plt.tight_layout(); plt.savefig("figs/metrics.png", dpi=100); plt.close()

# --- 4. 定着度(result_fix) ---
if os.path.isdir("result_fix"):
    rdir = "result_fix"; tm = times(rdir); K = max(tm)
    fx = rd(rdir, "Fx", K); h = rd(rdir, "H", K); z = rd(rdir, "Z", K)
    fig, axes = plt.subplots(2, 1, figsize=(14, 6.4), sharex=True)
    im = axes[0].imshow(np.where(fx > 0.01, fx, np.nan), origin="lower", extent=ext, cmap="YlGn", vmin=0, vmax=1)
    axes[0].contour(x, y, h0 > 0.05, levels=[0.5], colors="k", linewidths=0.4)
    axes[0].contour(x, y, h > 0.05, levels=[0.5], colors="#2a9d5a", linewidths=0.8)
    axes[0].set_title("fixation degree a after %.0f h (black = initial banks, green = final channel at the output discharge)" % (tm[K] * MORFAC / 3600))
    plt.colorbar(im, ax=axes[0], shrink=0.8)
    im = axes[1].imshow(np.where(h > 0.05, h, np.nan), origin="lower", extent=ext, cmap="Blues", vmin=0, vmax=2)
    axes[1].contour(x, y, h0 > 0.05, levels=[0.5], colors="k", linewidths=0.4)
    axes[1].set_title("final depth (m) at the output time")
    plt.colorbar(im, ax=axes[1], shrink=0.8)
    for ax in axes:
        ax.set_ylabel("y (m)")
    axes[-1].set_xlabel("x (m)")
    plt.tight_layout(); plt.savefig("figs/fixation.png", dpi=100); plt.close()
    # 砂州の定着面積(a > 0.5 で初期河道の内側)
    inside = h0 > 0.05
    print("fixation: cells with a > 0.5 inside the initial channel = %d (%.0f m2), outside = %d" % (
        ((fx > 0.5) & inside).sum(), ((fx > 0.5) & inside).sum() * DX * DX, ((fx > 0.5) & ~inside).sum()))
print("figures: figs/planform.png figs/sections.png figs/metrics.png" + (" figs/fixation.png" if os.path.isdir("result_fix") else ""))
