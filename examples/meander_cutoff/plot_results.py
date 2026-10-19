#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# examples/meander_cutoff の図化(result を読んで figs/ に保存)
#   figs/sequence.png : 出水の前・中・後の流速分布と河床変化(短絡の経過)
#   figs/final.png    : 終了時の水深・流速・河床変化と、初期河道(黒線)・新流路
# 数表(README 用): 旧河道(ループ)と新流路(頸部)の流れているセル数の推移
import os, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import make_init as mi

DX, NX, NY, MORFAC = mi.DX, mi.NX, mi.NY, 10.0
x = (np.arange(NX) + 0.5) * DX
y = (np.arange(NY) + 0.5) * DX
os.makedirs("figs", exist_ok=True)
z0 = np.loadtxt("z.txt"); h0 = np.loadtxt("h.txt")
R = "result"


def rd(name, k):
    return np.loadtxt("%s/%s%04d.txt" % (R, name, k))


tm = {int(l.split(",")[0]): float(l.split(",")[2])
      for l in open(R + "/FILENUMBER.csv") if not l.startswith("#") and int(l.split(",")[0]) < 9000}
ks = sorted(tm)
# 初期の河道のうち「ループ」(y > 70 m の部分)と、頸部ゾーン(初期に乾いていて
# 低い河岸 = z − 近傍河床の最大 < 1.2 m)を領域として定義する
loop = (h0 > 0) & (y[:, None] > 70.0)
zb = np.where(h0 > 0, z0, -1e9)
mx = zb.copy()
r = int(mi.RFP / DX)
for dj in range(-r, r + 1):
    for di in range(-r, r + 1):
        if di * di + dj * dj <= r * r:
            mx = np.maximum(mx, np.roll(np.roll(zb, dj, 0), di, 1))
neck = (h0 == 0) & (mx > -1e8) & (z0 - mx < 1.2)


def Q(t):
    tmin = t / 60.0
    return 40.0 if 40.0 <= tmin <= 100.0 else 15.0


print("| t (min) | 地形時間 (h) | Q (m³/s) | ループで流れているセル(|V| > 0.3 m/s) | 頸部ゾーンで流れているセル | 初期河道の外で湿潤 | 最深の洗掘 (m) |")
print("|---|---|---|---|---|---|---|")
ext = [0, NX * DX, 0, NY * DX]
fig, axes = plt.subplots(len(ks), 2, figsize=(14, 2.6 * len(ks)))
for n, k in enumerate(ks):
    h = rd("H", k); vv = rd("V", k); z = rd("Z", k); dz = z - z0
    flowing = (h > 0.05) & (vv > 0.3)
    print("| %.0f | %.0f | %.0f | %d | %d | %d | %.2f |" % (tm[k] / 60, tm[k] * MORFAC / 3600, Q(tm[k]), (flowing & loop).sum(), (flowing & neck).sum(), ((h > 0.05) & (h0 == 0)).sum(), dz.min()))
    ax = axes[n, 0]
    ax.imshow(np.where(h > 0.05, vv, np.nan), origin="lower", extent=ext, cmap="magma", vmin=0, vmax=2)
    ax.contour(x, y, h0 > 0, levels=[0.5], colors="c", linewidths=0.4)
    ax.set_title("|V| (m/s)  t = %.0f min, Q = %.0f m3/s (morphological %.0f h)" % (tm[k] / 60, Q(tm[k]), tm[k] * MORFAC / 3600))
    ax = axes[n, 1]
    im = ax.imshow(dz, origin="lower", extent=ext, cmap="RdBu_r", vmin=-2, vmax=2)
    ax.contour(x, y, h0 > 0, levels=[0.5], colors="k", linewidths=0.3)
    ax.set_title("bed change z - z0 (m)")
plt.tight_layout(); plt.savefig("figs/sequence.png", dpi=80); plt.close()

k = ks[-1]
h = rd("H", k); vv = rd("V", k); z = rd("Z", k); dz = z - z0
fig, axes = plt.subplots(1, 3, figsize=(18, 4.6))
im = axes[0].imshow(np.where(h > 0.05, h, np.nan), origin="lower", extent=ext, cmap="Blues", vmin=0, vmax=3); axes[0].set_title("depth (m), final"); plt.colorbar(im, ax=axes[0], shrink=0.8)
im = axes[1].imshow(np.where(h > 0.05, vv, np.nan), origin="lower", extent=ext, cmap="magma", vmin=0, vmax=2); axes[1].set_title("|V| (m/s), final"); plt.colorbar(im, ax=axes[1], shrink=0.8)
im = axes[2].imshow(dz, origin="lower", extent=ext, cmap="RdBu_r", vmin=-2, vmax=2); axes[2].set_title("z - z0 (m), final"); plt.colorbar(im, ax=axes[2], shrink=0.8)
for ax in axes:
    ax.contour(x, y, h0 > 0, levels=[0.5], colors="k", linewidths=0.4)
    ax.contour(x, y, neck, levels=[0.5], colors="orange", linewidths=0.6)
    ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
plt.tight_layout(); plt.savefig("figs/final.png", dpi=100); plt.close()
print("figures: figs/sequence.png figs/final.png")
