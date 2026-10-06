#!/usr/bin/env python3
"""test/debris の図を figs/*.png に描く(事前に ./Run.sh を実行しておく)。

  python3 Fig.py

- figs/profile.png : 4 構成(簡易 E-D / 江頭 / 高橋・中川 / 高橋・中川 + 間隙水連行)の
                     地形変化 dz と流動中の土砂 hs の全行平均の縦断(遷緩点 x = 30 m)
- figs/map.png     : 構成 1(param.txt)の地形変化と流動深の分布
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


NX, NY, DX, XB, ST = 60, 20, 1.0, 30.0, 0.4
x = (np.arange(NX) + 0.5) * DX
z0 = np.where(x < XB, ST * (XB - x), 0.0)
cases = [("save", "構成 1: 簡易 E-D(高橋型平衡濃度)+ クーロン・マニング合成、30 s", "C0"),
         ("save_eg", "構成 2: 江頭・芦田 E-D + 江頭構成則、30 s", "C1"),
         ("save_tk", "構成 3: 高橋・中川 (1991) E-D + 石礫型抵抗、60 s", "C2"),
         ("save_tkwet", "構成 4: 構成 3 + 間隙水連行 f_dbwet、60 s", "C3")]
fig, axes = plt.subplots(3, 1, figsize=(9, 8.5), sharex=True)
axes[0].plot(x, z0, "k", lw=1.5); axes[0].set_ylabel("z₀ (m)")
axes[0].set_title("slope_break 地形: tanθ = 0.4 の斜面 → x = 30 m の遷緩点 → 平坦。降雨 200 mm/h、可動層 5 m", fontsize=10)
axes[0].axvline(XB, color="0.5", ls=":")
for d, lab, c in cases:
    if not os.path.isfile(os.path.join(d, "state.dat")):
        continue
    st = load_state(d, NX, NY)
    dz = (st["z"] - z0).mean(axis=0)
    hs = st["hs"].mean(axis=0)
    axes[1].plot(x, dz * 100, color=c, lw=1.4, label=lab)
    axes[2].plot(x, hs * 100, color=c, lw=1.4, label=lab)
    print("%-11s min dz %.4f m  max dz %.4f m  max hs %.4f m  sum h %.3f  sum hs %.3f  solids %.2e" % (
        d, (st["z"] - z0).min(), (st["z"] - z0).max(), st["hs"].max(), st["h"].sum(), st["hs"].sum(),
        st["hs"].sum() + 0.6 * (st["z"] - z0).sum()))
for ax in axes[1:]:
    ax.axvline(XB, color="0.5", ls=":"); ax.grid(alpha=0.3); ax.legend(fontsize=8)
axes[1].set_ylabel("地形変化 dz (cm、全行平均)")
axes[2].set_ylabel("流動中の土砂 hs (cm、全行平均)")
axes[2].set_xlabel("x (m)")
fig.tight_layout(); fig.savefig("figs/profile.png", dpi=110); plt.close(fig)

st = load_state("save", NX, NY)
fig, axes = plt.subplots(1, 2, figsize=(11, 3.6))
for ax, a, title, cmap, kw in [(axes[0], (st["z"] - z0) * 100, "構成 1: 地形変化 dz (cm)", "RdBu_r", {"vmin": -0.5, "vmax": 0.5}),
                               (axes[1], (st["h"] + st["hs"]) * 100, "構成 1: 流動深 h + hs (cm)", "viridis", {})]:
    im = ax.imshow(a, origin="lower", extent=[0, 60, 0, 20], cmap=cmap, **kw)
    ax.axvline(XB, color="w", lw=0.6, ls=":")
    ax.set_title(title, fontsize=9); ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
    fig.colorbar(im, ax=ax, shrink=0.8)
fig.tight_layout(); fig.savefig("figs/map.png", dpi=110); plt.close(fig)
