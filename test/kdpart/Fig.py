#!/usr/bin/env python3
"""test/kdpart の図を figs/kdpart.png に描く(事前に ./Run.sh を実行しておく)。
平衡分配(Kd)と粒子態沈降: 点源 50 g/s × 8 s = 400 g の行き先(地表・地下・沈降プール)を
Kd = 200 と 2e5 L/kg で比べる。最終の濃度 C と浮遊砂 B の分布。
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

cases = [("result", "Kd = 200 L/kg"), ("result_hi", "Kd = 2e5 L/kg")]
fig, axes = plt.subplots(1, 3, figsize=(15, 4.2), gridspec_kw={"width_ratios": [1, 1.2, 1.2]})
ax = axes[0]
for k, (d, lab) in enumerate(cases):
    w = read_wq(os.path.join(d, "wq.csv"))
    vals = [w["mass_surface_g"][-1], w["mass_gw_g"][-1], w["mass_pool_g"][-1]]
    ax.bar(np.arange(3) + (k - 0.5) * 0.35, vals, 0.35, label=f"{lab}(合計 {sum(vals):.4f} g、投入 {w['in_point_g'][-1]:.1f} g)")
    print("%-9s in %.4f surface %.4f gw %.6f pool %.4f sum %.6f settle %.4f to_gw %.3e" % (d, w["in_point_g"][-1], vals[0], vals[1], vals[2], sum(vals), w["settle_g"][-1], w["to_gw_g"][-1]))
ax.set_xticks(range(3)); ax.set_xticklabels(["地表 mass_surface", "地下 mass_gw", "沈降プール mass_pool"], fontsize=8)
ax.set_ylabel("質量 (g)"); ax.set_yscale("log"); ax.legend(fontsize=7); ax.grid(alpha=0.3, axis="y")
ax.set_title("t = 8 s の質量の行き先(閉合: 合計 = 投入 400 g)", fontsize=9)
c = np.loadtxt("result/C9998.txt"); b = np.loadtxt("result/B9998.txt"); h = np.loadtxt("result/H9998.txt")
im = axes[1].imshow(np.where(h > 1e-6, c, np.nan), origin="lower", extent=[0, 101, 0, 101], cmap="magma", norm=matplotlib.colors.LogNorm(vmin=max(c[c > 0].min(), 1e-3), vmax=c.max()))
axes[1].set_title("Kd = 200: 最終の濃度 C (mg/L)", fontsize=9); fig.colorbar(im, ax=axes[1], shrink=0.8)
im = axes[2].imshow(np.where(b > 1e-9, b, np.nan), origin="lower", extent=[0, 101, 0, 101], cmap="YlOrBr")
axes[2].set_title("Kd = 200: 粒子態(浮遊砂に付着)B", fontsize=9); fig.colorbar(im, ax=axes[2], shrink=0.8)
for ax in axes[1:]:
    ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
fig.suptitle("Kd 分配(kdpart): 閉領域ダムブレイク + 中央点源 + Green-Ampt 浸透 + 浮遊砂。溶存態は浸透、粒子態は沈降", fontsize=10)
fig.tight_layout(); fig.savefig("figs/kdpart.png", dpi=110); plt.close(fig)
