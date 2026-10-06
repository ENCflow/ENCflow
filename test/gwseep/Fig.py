#!/usr/bin/env python3
"""test/gwseep の図を figs/gwseep.png に描く(事前に ./Run.sh を実行しておく)。
水質の地下循環(浸透 → 側方流動 → 湧出 → 再浸透): wq.csv の台帳の時系列と最終の濃度・水深の分布。
param_rg(wq_rg = 1e12 の完全不動化)があれば重ねる。
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

w = read_wq("result/wq.csv")
t = w["time_s"] / 60
fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))
ax = axes[0]
ax.plot(t, w["mass_surface_g"], "C0", lw=1.5, label="地表 mass_surface")
ax.plot(t, w["mass_gw_g"], "C1", lw=1.5, label="地下 mass_gw")
ax.plot(t, w["mass_surface_g"] + w["mass_gw_g"], "k--", lw=1, label="合計(初期 4000 g)")
ax.plot(t, w["to_gw_g"], "C2:", lw=1.2, label="累積 浸透 to_gw")
ax.plot(t, w["seep_g"], "C3:", lw=1.2, label="累積 湧出 seep")
if os.path.isfile("result_rg/wq.csv"):
    wr = read_wq("result_rg/wq.csv")
    ax.plot(wr["time_s"] / 60, wr["mass_gw_g"], "C1", lw=1, alpha=0.5, ls="-.", label="mass_gw(wq_rg = 1e12: 不動化)")
ax.set_xlabel("t (min)"); ax.set_ylabel("質量 (g)"); ax.grid(alpha=0.3); ax.legend(fontsize=7)
ax.set_title("台帳: to_gw − seep = mass_gw、地表 + 地下 = 4000 g", fontsize=9)
c = np.loadtxt("result/C9998.txt"); h = np.loadtxt("result/H9998.txt")
im = axes[1].imshow(np.where(h > 1e-6, c, np.nan), origin="lower", extent=[0, 40, 0, 20], cmap="viridis", vmin=99.99, vmax=100.01)
axes[1].set_title("最終の濃度 C (mg/L)(湿潤セル。初期 100 が保たれる)", fontsize=9); fig.colorbar(im, ax=axes[1], shrink=0.8)
im = axes[2].imshow(np.where(h > 1e-6, h, np.nan), origin="lower", extent=[0, 40, 0, 20], cmap="Blues")
axes[2].set_title("最終の水深 H (m)(下流端で湧出・湛水)", fontsize=9); fig.colorbar(im, ax=axes[2], shrink=0.8)
for ax in axes[1:]:
    ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
fig.suptitle("水質の地下経路(gwseep): 閉領域斜面(勾配 0.1)で 初期水 0.05 m・100 mg/L が浸透・側方流動・湧出を循環(3 h)", fontsize=10)
fig.tight_layout(); fig.savefig("figs/gwseep.png", dpi=110); plt.close(fig)
print("end: to_gw %.4f seep %.4f mass_gw %.4f (to_gw-seep %.4f) total %.4f; C wet min/max %.4f/%.4f" % (w["to_gw_g"][-1], w["seep_g"][-1], w["mass_gw_g"][-1], w["to_gw_g"][-1] - w["seep_g"][-1], w["mass_surface_g"][-1] + w["mass_gw_g"][-1], c[h > 1e-6].min(), c[h > 1e-6].max()))
