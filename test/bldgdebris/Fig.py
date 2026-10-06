#!/usr/bin/env python3
"""test/bldgdebris の図を figs/*.png に描く(事前に ./Run.sh を実行しておく)。

  python3 Fig.py

- figs/bldgdebris.png : 構成 1(浸水深判定)・構成 2(流木 + 瓦礫、荷重判定)・構成 4(空隙率帰還)の
                        瓦礫の分布: 流動中 hbd、堆積 wbd、破壊された家屋ストック wbs₀ − wbs、空隙率 gv
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


def load_bd(savedir):
    with open(os.path.join(savedir, "bldgdebris.dat"), "rb") as f:
        return {k: read_rle(f, NX * NY).reshape(NY, NX) for k in ["hbd", "wbd", "wbs", "wbs0", "gv0", "gv"]}


cases = [("save", "構成 1: 浸水深判定"), ("save_dw", "構成 2: 流木 + 瓦礫、荷重判定"), ("save_gv", "構成 4: 空隙率帰還 f_bdgv = 1")]
fig, axes = plt.subplots(3, 4, figsize=(18, 8.5))
for row, (d, lab) in enumerate(cases):
    bd = load_bd(d)
    panels = [(bd["hbd"] * 1e3, "流動中の瓦礫 hbd (mm)", "Blues"), (bd["wbd"] * 1e3, "堆積した瓦礫 wbd (mm)", "Oranges"),
              ((bd["wbs0"] - bd["wbs"]) * 1e3, "破壊された家屋 wbs₀ − wbs (mm)", "Reds"), (bd["gv"], "空隙率 gv", "viridis")]
    for ax, (a, title, cmap) in zip(axes[row], panels):
        isgv = title.startswith("空隙率")
        im = ax.imshow(a if isgv else np.where(a > 1e-6, a, np.nan), origin="lower", extent=EXT, cmap=cmap,
                       **({"vmin": 0.5, "vmax": 1.0} if isgv else {}))
        ax.axvline(XB, color="k", lw=0.6, ls=":")
        ax.set_title(f"{lab.split(':')[0]}: {title}", fontsize=9); ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
        fig.colorbar(im, ax=ax, shrink=0.8)
    print("%-8s destroyed %.4e  hbd %.4e  wbd %.4e  conservation %.2e  gv min %.2f" % (
        d, (bd["wbs0"] - bd["wbs"]).sum(), bd["hbd"].sum(), bd["wbd"].sum(),
        ((bd["hbd"] + bd["wbd"]) * bd["gv"]).sum() + bd["wbs"].sum() - bd["wbs0"].sum(), bd["gv"].min()))
fig.suptitle("家屋破壊・瓦礫ラスタ場(slope_break 地形、降雨 200 mm/h、60 s。家屋ストック 0.01 m³/m²)", fontsize=10)
fig.tight_layout(); fig.savefig("figs/bldgdebris.png", dpi=110); plt.close(fig)
