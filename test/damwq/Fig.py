#!/usr/bin/env python3
"""test/damwq の図を figs/damwq.png に描く(事前に ./Run.sh を実行しておく)。
ダム(完全混合プール、一定放流)とため池パッチ(容量到達で吸収)の水質台帳の時系列と、最終の濃度分布。
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

w = read_wq("result/wq.csv"); t = w["time_s"] / 60
fig, axes = plt.subplots(1, 2, figsize=(13, 4.2), gridspec_kw={"width_ratios": [1.2, 1]})
ax = axes[0]
ax.plot(t, w["mass_surface_g"], "C0", lw=1.5, label="地表 mass_surface")
ax.plot(t, w["mass_dam_g"], "C1", lw=1.5, label="ダム貯留 mass_dam")
ax.plot(t, w["mass_rs_g"], "C2", lw=1.5, label="ため池 mass_rs")
ax.plot(t, w["mass_surface_g"] + w["mass_dam_g"] + w["mass_rs_g"], "k--", lw=1, label="合計(初期 4000 g)")
ax.plot(t, w["to_dam_g"], "C1:", lw=1.2, label="累積 捕捉 to_dam")
ax.plot(t, w["rel_dam_g"], "C3:", lw=1.2, label="累積 放流 rel_dam(解析 0.005 m³/s × t × 100 g/m³)")
ax.set_xlabel("t (min)"); ax.set_ylabel("質量 (g)"); ax.grid(alpha=0.3); ax.legend(fontsize=7)
ax.set_title("台帳: to_dam − rel_dam = mass_dam、地表 + ダム + ため池 = 4000 g", fontsize=9)
c = np.loadtxt("result/C9998.txt"); h = np.loadtxt("result/H9998.txt")
im = axes[1].imshow(np.where(h > 1e-3, c, np.nan), origin="lower", extent=[0, 40, 0, 20], cmap="viridis", vmin=99, vmax=101)
axes[1].set_title("最終の濃度 C (mg/L)(湿潤セル。全経路で 100 が保たれる)", fontsize=9); axes[1].set_xlabel("x (m)"); axes[1].set_ylabel("y (m)")
fig.colorbar(im, ax=axes[1], shrink=0.8)
fig.suptitle("ダム・ため池の水質(damwq): 閉領域斜面 + ため池パッチ 24 セル × 0.05 m + 捕捉列 20 セルのダム(放流 5 L/s)、1.5 h", fontsize=10)
fig.tight_layout(); fig.savefig("figs/damwq.png", dpi=110); plt.close(fig)
print("end: to_dam %.4f rel_dam %.4f (analytic 2700) mass_dam %.4f to_rs %.5f mass_rs %.5f (analytic 120) total %.4f; C wet %.4f..%.4f" % (w["to_dam_g"][-1], w["rel_dam_g"][-1], w["mass_dam_g"][-1], w["to_rs_g"][-1], w["mass_rs_g"][-1], w["mass_surface_g"][-1] + w["mass_dam_g"][-1] + w["mass_rs_g"][-1], c[h > 1e-6].min(), c[h > 1e-6].max()))
