#!/usr/bin/env python3
"""test/suspend の図を figs/suspend.png に描く(事前に ./Run.sh を実行しておく)。
閉領域ダムブレイク(wave_hump)の浮遊砂: 2 つの平衡濃度式(1: 超過掃流力線形、2: 板倉・岸)の
最終の浮遊砂 hs と河床変動 dz の分布・中央行の断面。
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
x = np.arange(NX) + 0.5
fig, axes = plt.subplots(2, 3, figsize=(15, 7.5))
for row, (d, lab) in enumerate([("save_serial", "構成 1: 平衡濃度式 1(超過掃流力線形)"), ("save", "構成 2: 板倉・岸(param_ik)")]):  # Run.sh は 2 構成とも save/ に書き、構成 1 を save_serial に退避する
    st = load_state(d, NX, NY)
    dz = st["z"]
    im = axes[row, 0].imshow(dz * 1e3, origin="lower", extent=[0, 101, 0, 101], cmap="RdBu_r", vmin=-np.abs(dz).max() * 1e3, vmax=np.abs(dz).max() * 1e3)
    axes[row, 0].set_title(f"{lab}: 河床変動 z − z₀ (mm)", fontsize=9); fig.colorbar(im, ax=axes[row, 0], shrink=0.8)
    im = axes[row, 1].imshow(np.where(st["hs"] > 1e-9, st["hs"] * 1e3, np.nan), origin="lower", extent=[0, 101, 0, 101], cmap="YlOrBr")
    axes[row, 1].set_title("浮遊砂 hs (mm)、t = 8 s", fontsize=9); fig.colorbar(im, ax=axes[row, 1], shrink=0.8)
    jc = NY // 2
    axes[row, 2].plot(x, dz[jc] * 1e3, "C3", label="z − z₀ (mm)")
    axes[row, 2].plot(x, st["hs"][jc] * 1e3, "C1--", label="hs (mm)")
    axes[row, 2].set_title("中央行の断面", fontsize=9); axes[row, 2].grid(alpha=0.3); axes[row, 2].legend(fontsize=8); axes[row, 2].set_xlabel("x (m)")
    print("%-8s solids %.2e  coupling %.2e  max hs %.2e m  min dz %.2e m" % (d, st["hs"].sum() + (1 - PORO) * dz.sum(), np.abs((st["sd"] - SD0) - dz).max(), st["hs"].max(), dz.min()))
for ax in axes[:, :2].flat:
    ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
fig.suptitle("浮遊砂(f_suspend): 静水 0.5 m 上の水の山が崩れ、河床から巻き上がった砂が移流・再堆積する閉領域(Δx = 1 m、8 s)", fontsize=10)
fig.tight_layout(); fig.savefig("figs/suspend.png", dpi=110); plt.close(fig)
