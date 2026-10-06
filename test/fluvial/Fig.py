#!/usr/bin/env python3
"""test/fluvial の図を figs/*.png に描く(事前に ./Run.sh を実行しておく)。

  python3 Fig.py

- figs/fluvial.png : 閉領域ダムブレイク型(wave_hump の水の山が崩れる)で掃流砂 Exner が
                     動かした河床変動 z − z₀ の分布と中央行の断面、最終水位
"""
import os, struct
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
matplotlib.rcParams["font.family"] = ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs("figs", exist_ok=True)


def read_rec(f):
    n = struct.unpack("<i", f.read(4))[0]; p = f.read(n); f.read(4); return p


def read_rle(f, ntot):
    n, nrun = struct.unpack("<2q", read_rec(f))
    runs = struct.unpack("<%dq" % (2 * nrun), read_rec(f))
    raw = read_rec(f); packed = struct.unpack("<%dd" % (len(raw) // 8), raw)
    out = np.zeros(n); i = k = 0
    for r in range(nrun):
        i += runs[2 * r]; lit = runs[2 * r + 1]
        out[i:i + lit] = packed[k:k + lit]; i += lit; k += lit
    return out


def load_state(savedir, nx, ny):
    with open(os.path.join(savedir, "state.dat"), "rb") as f:
        return {k: read_rle(f, nx * ny).reshape(ny, nx) for k in ["h", "z", "hrs", "hg", "sd", "hs"]}


NX = NY = 101; DX = 1.0; SD0 = 10.0
st = load_state("save", NX, NY)
dz = st["z"]            # z0 = 0
x = (np.arange(NX) + 0.5) * DX
fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))
im = axes[0].imshow(dz * 1000, origin="lower", extent=[0, 101, 0, 101], cmap="RdBu_r", vmin=-2, vmax=2)
axes[0].set_title("河床変動 z − z₀ (mm)、t = 8 s", fontsize=10); fig.colorbar(im, ax=axes[0], shrink=0.8)
im = axes[1].imshow(st["z"] + st["h"], origin="lower", extent=[0, 101, 0, 101], cmap="viridis")
axes[1].set_title("水位 z + h (m)、t = 8 s", fontsize=10); fig.colorbar(im, ax=axes[1], shrink=0.8)
for ax in axes[:2]:
    ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
jc = NY // 2
axes[2].plot(x, dz[jc] * 1000, "C3", lw=1.5, label="z − z₀ (mm)")
axes[2].plot(x, (st["sd"][jc] - SD0) * 1000, "C0--", lw=1, label="sd − sd₀ (mm)(共動更新 = 同じ曲線)")
axes[2].set_xlabel("x (m)"); axes[2].set_ylabel("(mm)"); axes[2].set_title("中央行の断面", fontsize=10)
axes[2].grid(alpha=0.3); axes[2].legend(fontsize=8)
fig.suptitle("掃流砂 Exner(芦田・道上、d50 = 1 mm): 静水 0.5 m 上の水の山(+1 m)が崩れて河床を動かす閉領域", fontsize=10)
fig.tight_layout(); fig.savefig("figs/fluvial.png", dpi=110); plt.close(fig)
print("sum dz = %.2e, max|dz| = %.2e m, max|(sd-sd0)-dz| = %.2e, sum h = %.4f" % (dz.sum(), np.abs(dz).max(), np.abs((st["sd"] - SD0) - dz).max(), st["h"].sum()))
