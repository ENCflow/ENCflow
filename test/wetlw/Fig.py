#!/usr/bin/env python3
"""test/wetlw の図を figs/wetlw.png に描く(事前に ./Run.sh を実行しておく)。
構成 0(wet_lw なし)と構成 l(wet_lw = 3 m)の侵食深 Δz = z0 − z の分布と中央行の断面。
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


def load_z(savedir, nx, ny):
    with open(os.path.join(savedir, "state.dat"), "rb") as f:
        read_rle(f, nx * ny)
        return read_rle(f, nx * ny).reshape(ny, nx)

NX = NY = 101
dz0 = -load_z("save_0", NX, NY)
dzl = -load_z("save_l", NX, NY)
vmax = max(dz0.max(), dzl.max())
fig, ax = plt.subplots(1, 3, figsize=(14, 4.2))
for a, d, t in ((ax[0], dz0, "wet_lw なし"), (ax[1], dzl, "wet_lw = 3 m")):
    im = a.imshow(d * 1e3, origin="lower", extent=[0, NX, 0, NY], cmap="YlOrBr", vmin=0, vmax=vmax * 1e3)
    a.set_title("侵食深 Δz (mm): " + t, fontsize=10); a.set_xlabel("x (m)"); a.set_ylabel("y (m)")
    fig.colorbar(im, ax=a, shrink=0.8)
j = NY // 2
ax[2].plot(np.arange(NX) + 0.5, dz0[j] * 1e3, "-", lw=1, label="wet_lw なし")
ax[2].plot(np.arange(NX) + 0.5, dzl[j] * 1e3, "-", lw=1.5, label="wet_lw = 3 m")
ax[2].set_xlabel("x (m)"); ax[2].set_ylabel("Δz (mm)"); ax[2].set_title("中央行 (y = %d m) の断面" % j, fontsize=10); ax[2].legend(fontsize=8)
fig.tight_layout(); fig.savefig("figs/wetlw.png", dpi=110)
print("figs/wetlw.png written")
