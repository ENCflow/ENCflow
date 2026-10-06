#!/usr/bin/env python3
"""test/salt の図を figs/salt.png に描く(事前に ./Run.sh と ./Run_sea.sh を実行しておく)。
模式実験 A(プール仕切り = ロック交換): 塩水層厚 Hss の初期・最終と解析終状態 10/21 m。
模式実験 B(海水浸入の静的平衡): 地下水位 Hg と解析値 0.5(Ghyben-Herzberg の縮退形)。
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

fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))
hss0 = np.loadtxt("result/Hss0000.txt"); hss1 = np.loadtxt("result/Hss9998.txt"); h1 = np.loadtxt("result/H9998.txt")
im = axes[0].imshow(hss0, origin="lower", extent=[0, 42, 0, 42], cmap="Blues", vmin=0, vmax=1); axes[0].set_title("A: 初期の塩水層厚 Hss (m)(左 10 列 = 1 m)", fontsize=9); fig.colorbar(im, ax=axes[0], shrink=0.8)
im = axes[1].imshow(hss1, origin="lower", extent=[0, 42, 0, 42], cmap="Blues", vmin=0, vmax=1); axes[1].set_title(f"A: 600 s 後の Hss (m)。解析終状態 10/21 = 0.4762(計算 {hss1.mean():.4f}、ばらつき {hss1.std():.1e})", fontsize=9); fig.colorbar(im, ax=axes[1], shrink=0.8)
for ax in axes[:2]:
    ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
if os.path.isdir("result_sea"):
    hg = sorted(glob.glob("result_sea/Hg[0-9]*.txt"))
    hg1 = np.loadtxt(hg[-1])
    x = (np.arange(hg1.shape[1]) + 0.5) * 2.0
    axes[2].plot(x, hg1.mean(axis=0), "C0o-", ms=3, label="計算 Hg(行平均、t = 40,000 s)")
    axes[2].axhline(0.5, color="k", ls="--", lw=1, label="解析値 0.5(海水 1 m × ρf/ρs の縮退形)")
    axes[2].set_xlabel("x (m)"); axes[2].set_ylabel("Hg (m)"); axes[2].set_title("B: 海水浸入の静的平衡(地下水位)", fontsize=9); axes[2].grid(alpha=0.3); axes[2].legend(fontsize=8)
    print("B: Hg land cells %.4f..%.4f" % (hg1[:, 1:].min(), hg1[:, 1:].max()))
print("A: Hss final mean %.10f (10/21 = %.10f), std %.2e, H unchanged? max|H9998-H0000| = %.2e, salt volume ratio %.9f" % (hss1.mean(), 10 / 21, hss1.std(), np.abs(h1 - np.loadtxt("result/H0000.txt")).max(), hss1.sum() / hss0.sum()))
fig.suptitle("地表塩水層(f_salt_surf): 密度差による交換流(模式実験 A)と海水浸入の平衡(模式実験 B)", fontsize=10)
fig.tight_layout(); fig.savefig("figs/salt.png", dpi=110); plt.close(fig)
