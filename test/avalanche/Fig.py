#!/usr/bin/env python3
"""test/avalanche の図を figs/*.png に描く(事前に ./Run.sh を実行しておく)。

  python3 Fig.py

- figs/avalanche.png : 発生区の破断深 D、連行された雪の厚さ −(sd − sd₀)、停止後の雪面変化 z − z₀、
                       全行平均の縦断(連行・堆積の収支)
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


NX, NY, DX, XB, ST, SD0, PORO = 60, 20, 1.0, 30.0, 0.4, 0.5, 0.1
EXT = [0, 60, 0, 20]
x = (np.arange(NX) + 0.5) * DX
z0 = np.tile(np.where(x < XB, ST * (XB - x), 0.0), (NY, 1))
st = load_state("save", NX, NY)
db = np.loadtxt("dbinit.txt")
dz = st["z"] - z0
ent = -(st["sd"] - SD0)
fig, axes = plt.subplots(2, 2, figsize=(12, 7))
ax = axes[0, 0]
im = ax.imshow(np.where(db > 0, db, np.nan), origin="lower", extent=EXT, cmap="Oranges")
ax.set_title("発生区の破断深 D (m)(t = 1 s に流動化。走路の雪 sd₀ = 0.5 m)", fontsize=9); fig.colorbar(im, ax=ax, shrink=0.8)
ax = axes[0, 1]
im = ax.imshow(np.where(ent > 1e-4, ent, np.nan), origin="lower", extent=EXT, cmap="Blues", vmin=0, vmax=SD0)
ax.set_title("連行された雪の厚さ sd₀ − sd (m)(走路)", fontsize=9); fig.colorbar(im, ax=ax, shrink=0.8)
ax = axes[1, 0]
im = ax.imshow(dz, origin="lower", extent=EXT, cmap="RdBu_r", vmin=-1, vmax=1)
ax.set_title("雪面の変化 z − z₀ (m)(負: 削剥、正: 停止デブリの堆積)、t = 60 s", fontsize=9); fig.colorbar(im, ax=ax, shrink=0.8)
for ax in axes.flat[:3]:
    ax.axvline(XB, color="k", lw=0.6, ls=":"); ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
ax = axes[1, 1]
ax.plot(x, dz.mean(axis=0), "C3", lw=1.5, label="z − z₀(全行平均)")
ax.plot(x, -ent.mean(axis=0), "C0--", lw=1.2, label="−(sd₀ − sd)(連行分)")
ax.plot(x, st["hs"].mean(axis=0), "C2:", lw=1.2, label="残存 hs")
ax.axvline(XB, color="0.5", ls=":")
ax.set_xlabel("x (m)"); ax.set_ylabel("(m)")
ax.set_title("縦断(全行平均)", fontsize=9); ax.grid(alpha=0.3); ax.legend(fontsize=8)
fig.suptitle("流れ型雪崩(等価流体 Voellmy μ = 0.2・ξ = 1500 + 速度比例連行 E = δe|V|、δe = 0.05)", fontsize=10)
fig.tight_layout(); fig.savefig("figs/avalanche.png", dpi=110); plt.close(fig)
rel = (db > 0)
released = (1 - PORO) * db.sum()
entrained = (1 - PORO) * ent[~rel].clip(0).sum()
print("released solid %.1f, entrained solid %.1f (ratio %.2f), remaining hs %.2f (%.3f of total), min dz on path %.3f m, max deposit dz %.3f m"
      % (released, entrained, entrained / released, st["hs"].sum(), st["hs"].sum() / (released + entrained), ent[~rel].max() * -1, dz.max()))
