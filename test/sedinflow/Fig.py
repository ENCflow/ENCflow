#!/usr/bin/env python3
"""test/sedinflow の図を figs/sedinflow.png に描く(事前に ./Run.sh を実行しておく)。
乾いた閉領域の西辺に一定流入(Q = 5 m³/s、濃度 C = 0.001 または Qs 指定)。最終の水深・浮遊砂・河床変動と台帳。
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
fig, axes = plt.subplots(2, 3, figsize=(15, 7.5))
for row, (d, lab, exp) in enumerate([("save_serial", "構成 1: 濃度指定 inflow_cs = 0.001", 0.001 * 5 * 8), ("save", "構成 2: 流砂量指定 inflow_qs(param_qs)", None)]):  # Run.sh は構成 1 を save_serial に退避し、構成 2 を save/ に書く
    st = load_state(d, NX, NY)
    solids = st["hs"].sum() + (1 - PORO) * st["z"].sum()
    for ax, a, title, cmap in [(axes[row, 0], np.where(st["h"] > 1e-6, st["h"], np.nan), "水深 h (m)", "Blues"),
                               (axes[row, 1], np.where(st["hs"] > 1e-9, st["hs"] * 1e3, np.nan), "浮遊砂 hs (mm)", "YlOrBr"),
                               (axes[row, 2], st["z"] * 1e3, "河床変動 z − z₀ (mm)", "RdBu_r")]:
        kw = {"vmin": -np.abs(a[np.isfinite(a)]).max(), "vmax": np.abs(a[np.isfinite(a)]).max()} if cmap == "RdBu_r" else {}
        im = ax.imshow(a, origin="lower", extent=[0, 101, 0, 101], cmap=cmap, **kw)
        ax.set_title(f"{lab.split(':')[0]}: {title}", fontsize=9); ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
        fig.colorbar(im, ax=ax, shrink=0.8)
    print("%-8s sum h %.6f (Q tt = 40)  solids %.10f (C Q tt = %s)  max hs %.2e  min dz %.2e" % (d, st["h"].sum(), solids, exp, st["hs"].max(), st["z"].min()))
fig.suptitle("土砂流入境界(sedinflow): 西辺 4 セルから Q = 5 m³/s を 8 s 流入。t = 8 s の分布", fontsize=10)
fig.tight_layout(); fig.savefig("figs/sedinflow.png", dpi=110); plt.close(fig)
