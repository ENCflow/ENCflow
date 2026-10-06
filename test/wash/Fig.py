#!/usr/bin/env python3
"""test/wash の図を figs/wash.png に描く(事前に ./Run.sh を実行しておく)。
降雨 50 mm/h + 閉領域ダムブレイクの斜面侵食(雨滴 + 面状)。河床変動 dz と浮遊砂 hs の分布・断面。
"""
import glob, os, struct
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


def read_wq(path):
    names = open(path).readline().strip().split(",")
    a = np.loadtxt(path, delimiter=",", skiprows=1)
    return {n: a[:, i] for i, n in enumerate(names)}

NX = NY = 101; SD0 = 10.0; PORO = 0.4
st = load_state("save", NX, NY)
dz = st["z"]; x = np.arange(NX) + 0.5; jc = NY // 2
fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))
im = axes[0].imshow(dz * 1e3, origin="lower", extent=[0, 101, 0, 101], cmap="RdBu_r", vmin=-np.abs(dz).max() * 1e3, vmax=np.abs(dz).max() * 1e3)
axes[0].set_title("河床変動 z − z₀ (mm)、t = 8 s", fontsize=10); fig.colorbar(im, ax=axes[0], shrink=0.8)
im = axes[1].imshow(st["hs"] * 1e3, origin="lower", extent=[0, 101, 0, 101], cmap="YlOrBr")
axes[1].set_title("浮遊砂(ウォッシュロード)hs (mm)", fontsize=10); fig.colorbar(im, ax=axes[1], shrink=0.8)
for ax in axes[:2]:
    ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
axes[2].plot(x, dz[jc] * 1e3, "C3", label="z − z₀ (mm)")
axes[2].plot(x, st["hs"][jc] * 1e3, "C1--", label="hs (mm)")
axes[2].set_title("中央行の断面", fontsize=10); axes[2].grid(alpha=0.3); axes[2].legend(fontsize=8); axes[2].set_xlabel("x (m)")
fig.suptitle("斜面侵食(f_wash): 雨滴侵食 kr = 0.01 と面状侵食 kf = 1e-5 m/s が全域で河床を削り、浮遊砂として運ぶ", fontsize=10)
fig.tight_layout(); fig.savefig("figs/wash.png", dpi=110); plt.close(fig)
print("solids %.2e  coupling %.2e  mean dz %.3e m  max hs %.3e m  uniform part(dz std away from hump) %.2e" % (st["hs"].sum() + (1 - PORO) * dz.sum(), np.abs((st["sd"] - SD0) - dz).max(), dz.mean(), st["hs"].max(), dz[:10, :10].std()))
