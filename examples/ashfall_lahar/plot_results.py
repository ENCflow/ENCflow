#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# examples/ashfall_lahar の図化(result_lahar / result_noash を読んで figs/ に保存)
#   figs/maps.png     : 降灰厚、終了時の地形変化 z−z0(侵食=負・堆積=正)、泥流の最大流動深
#   figs/profiles.png : 谷筋(y=147.5 m)の縦断。地形変化と流動深・濃度の時間発展
#   figs/probes.png   : 3 プローブ(斜面・谷出口・扇状地)の流動深と土砂柱状量の時系列(降灰あり/なし)
# 数表(README 用)を標準出力に書く
import os, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DX, NX, NY = 5.0, 120, 60
J = 29                                   # 谷筋の行(0 始まり。y = 147.5 m)
CASES = [("result_lahar", "ashfall -> lahar", "#2a78d6"),
         ("result_noash", "no ash (clear water)", "#8a8983")]
x = (np.arange(NX) + 0.5) * DX
y = (np.arange(NY) + 0.5) * DX
os.makedirs("figs", exist_ok=True)


def rd(rdir, name, k):
    return np.loadtxt("%s/%s%04d.txt" % (rdir, name, k))


def times(rdir):
    return {int(l.split(",")[0]): float(l.split(",")[2])
            for l in open(rdir + "/FILENUMBER.csv") if not l.startswith("#") and int(l.split(",")[0]) < 9000}


def probe(rdir, n):
    f = "%s/probes/probe%04d.csv" % (rdir, n)
    xx = float(open(f).readlines()[1].split(",")[1])
    return xx, np.loadtxt(f, delimiter=",", comments="#")   # t(h), t(min), z, h, u, v, |V|, q, hg, hs, sd


R = CASES[0][0]
tm = times(R); K = max(tm)
ash = np.loadtxt("ash.txt")
z0 = rd(R, "Z", 0); dz = rd(R, "Z", K) - z0
hmax = np.zeros((NY, NX))
for k in tm:
    hmax = np.maximum(hmax, rd(R, "H", k) + rd(R, "Hs", k))

# --- 1. 平面図 ---
fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))
ext = [0, NX * DX, 0, NY * DX]
im = axes[0].imshow(ash, origin="lower", extent=ext, cmap="Oranges", vmin=0, vmax=0.3)
axes[0].set_title("ash thickness (m)"); plt.colorbar(im, ax=axes[0], shrink=0.8)
lim = max(abs(dz.min()), abs(dz.max()))
im = axes[1].imshow(dz, origin="lower", extent=ext, cmap="RdBu_r", vmin=-lim, vmax=lim)
axes[1].set_title("bed change z - z0 at t = %.0f min (erosion < 0 < deposit)" % (tm[K] / 60)); plt.colorbar(im, ax=axes[1], shrink=0.8)
im = axes[2].imshow(np.where(hmax > 0.005, hmax, np.nan), origin="lower", extent=ext, cmap="Blues", vmin=0)
axes[2].set_title("max flow depth h + hs (m)"); plt.colorbar(im, ax=axes[2], shrink=0.8)
for ax in axes:
    ax.axvline(300, color="k", lw=0.5, ls="--"); ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
    ax.contour(x, y, z0, levels=np.arange(0, 140, 10), colors="k", linewidths=0.3)
plt.tight_layout(); plt.savefig("figs/maps.png", dpi=110); plt.close()

# --- 2. 谷筋の縦断 ---
fig, axes = plt.subplots(3, 1, figsize=(10, 9), sharex=True)
axes[0].plot(x, z0[J], "k-", lw=1, label="z0 (with ash)")
axes[0].plot(x, z0[J] - ash[J], color="#8a8983", lw=1, ls="--", label="original ground")
axes[0].plot(x, rd(R, "Z", K)[J], color="#2a78d6", lw=1.2, label="z at t = %.0f min" % (tm[K] / 60))
axes[0].set_ylabel("elevation (m)"); axes[0].legend(fontsize=8); axes[0].grid()
for k in sorted(tm):
    if k == 0 or k % 3:
        continue
    h = rd(R, "H", k)[J]; hs = rd(R, "Hs", k)[J]
    axes[1].plot(x, np.where(h + hs > 0.002, h + hs, np.nan), lw=1, label="t=%.0f min" % (tm[k] / 60))
    axes[2].plot(x, np.where(h + hs > 0.002, hs / (h + hs + 1e-12), np.nan), lw=1)
axes[1].set_ylabel("flow depth h + hs (m)"); axes[1].legend(fontsize=7, ncol=3); axes[1].grid()
axes[2].set_ylabel("concentration C"); axes[2].set_ylim(0, 0.6); axes[2].grid(); axes[2].set_xlabel("x (m)")
for ax in axes:
    ax.axvline(300, color="k", lw=0.5, ls="--")
axes[0].set_title("valley axis (y = %.1f m)" % y[J], fontsize=10)
plt.tight_layout(); plt.savefig("figs/profiles.png", dpi=100); plt.close()

# --- 3. プローブ ---
fig, axes = plt.subplots(3, 2, figsize=(12, 8), sharex=True)
for n in (1, 2, 3):
    for rdir, lab, col in CASES:
        xx, d = probe(rdir, n)
        axes[n - 1][0].plot(d[:, 1], d[:, 3] + d[:, 9], color=col, lw=1.2, label=lab)
        axes[n - 1][1].plot(d[:, 1], d[:, 9], color=col, lw=1.2, label=lab)
    axes[n - 1][0].set_ylabel("h + hs (m)\nx = %.0f m" % xx); axes[n - 1][1].set_ylabel("hs (m)")
    axes[n - 1][0].grid(); axes[n - 1][1].grid()
axes[0][0].legend(fontsize=8); axes[0][0].set_title("flow depth"); axes[0][1].set_title("sediment column hs")
axes[-1][0].set_xlabel("t (min)"); axes[-1][1].set_xlabel("t (min)")
plt.tight_layout(); plt.savefig("figs/probes.png", dpi=100); plt.close()

# --- 数表 ---
A = DX * DX
ero = -np.clip(dz, None, 0).sum() * A; dep = np.clip(dz, 0, None).sum() * A
hs_end = rd(R, "Hs", K).sum() * A
print("ash volume %.0f m3 | eroded %.0f m3 (%.0f%%) | deposited %.0f m3 | hs remaining %.0f m3 | outflow (solid) %.0f m3"
      % (ash.sum() * A, ero, 100 * ero / (ash.sum() * A), dep, hs_end, (0.5 * (ero - dep) - hs_end) / 0.5 * 0.5))
for a, b in ((0, 300), (300, 350), (350, 400), (400, 600)):
    m = (x >= a) & (x < b)
    print("  x %3d-%3d m: eroded %6.0f  deposited %6.0f m3  max dz %+.2f m" % (a, b, -np.clip(dz[:, m], None, 0).sum() * A, np.clip(dz[:, m], 0, None).sum() * A, dz[:, m].max()))
lobe = (dz > 0.1) & (x[None, :] < 500)
print("lobe (dz > 0.1 m): x = %.0f-%.0f m, width %.0f m, volume %.0f m3, max thickness %.2f m"
      % (x[np.where(lobe)[1]].min(), x[np.where(lobe)[1]].max(), DX * len(set(np.where(lobe)[0])), dz[lobe].sum() * A, dz.max()))
for n in (1, 2, 3):
    for rdir, lab, col in CASES:
        xx, d = probe(rdir, n)
        i = (d[:, 3] + d[:, 9]).argmax()
        print("probe %d x=%3.0f %-22s max h+hs %.3f m @ %5.1f min  max hs %.3f  max |V| %.2f m/s" % (n, xx, lab, d[i, 3] + d[i, 9], d[i, 1], d[:, 9].max(), d[:, 6].max()))
