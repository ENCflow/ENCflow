#!/usr/bin/env python3
"""test/driftwood の図を figs/*.png に描く(事前に ./Run.sh を実行しておく)。

  python3 Fig.py

- figs/driftwood.png : 構成 1(土石流 + 侵食連行)と構成 2(洪水の水理的流失)の
                       流木の分布: 流動中 hd、堆積 wd、流木化したストック stock₀ − wst(save*/driftwood.dat)
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


NX, NY, XB = 60, 20, 30.0
EXT = [0, 60, 0, 20]


def load_dw(savedir):
    with open(os.path.join(savedir, "driftwood.dat"), "rb") as f:
        return {k: read_rle(f, NX * NY).reshape(NY, NX) for k in ["hd", "wd", "wst"]}


cases = [("save", "構成 1: 土石流 + 侵食連行(降雨 200 mm/h、30 s)"),
         ("save_flood", "構成 2: 洪水の水理的流失(地形変化なし、60 s)")]
fig, axes = plt.subplots(2, 3, figsize=(15, 6.2))
for row, (d, lab) in enumerate(cases):
    dw = load_dw(d)
    stock0 = 0.01
    for ax, a, title, cmap in [(axes[row, 0], dw["hd"] * 1e3, "流動中の流木 hd (mm)", "Blues"),
                               (axes[row, 1], dw["wd"] * 1e3, "堆積した流木 wd (mm)", "Oranges"),
                               (axes[row, 2], (stock0 - dw["wst"]) * 1e3, "流木化したストック stock₀ − wst (mm)", "Greens")]:
        im = ax.imshow(np.where(a > 1e-6, a, np.nan), origin="lower", extent=EXT, cmap=cmap)
        ax.axvline(XB, color="k", lw=0.6, ls=":")
        ax.set_title(f"{lab.split(':')[0]}: {title}", fontsize=9); ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
        fig.colorbar(im, ax=ax, shrink=0.8)
    print("%-11s rec %.4e  hd %.4e  wd %.4e  total-stock0 %.2e  reach max(hd+wd) x>=30: %.2e" % (
        d, (stock0 - dw["wst"]).sum(), dw["hd"].sum(), dw["wd"].sum(),
        dw["hd"].sum() + dw["wd"].sum() + dw["wst"].sum() - stock0 * NX * NY, (dw["hd"] + dw["wd"])[:, 29:].max()))
fig.suptitle("流木ラスタ場(slope_break 地形。上: 構成 1 土石流 + 侵食連行、下: 構成 2 洪水の水理的流失。立木ストック 0.01 m³/m²)", fontsize=10)
fig.tight_layout(); fig.savefig("figs/driftwood.png", dpi=110); plt.close(fig)
