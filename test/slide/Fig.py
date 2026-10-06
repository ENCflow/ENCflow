#!/usr/bin/env python3
"""test/slide の図を figs/*.png に描く(事前に ./Run.sh を実行しておく)。

  python3 Fig.py

- figs/release.png : 構成 1(瞬時流動化 f_release)。崩壊深 D、t = 10 s の地形変化 dz と流動深
- figs/fslide.png  : 構成 2(斜面安定判定 f_slide = 1)。期間最小安全率 Fs9999、崩壊で露出した
                     岩盤(sd = 0)、最大流動深 D9999。構成 3(f_slide = 2 診断のみ)の Fs9999
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
EXT = [0, 60, 0, 20]
x = (np.arange(NX) + 0.5) * DX
z0 = np.tile(np.where(x < XB, ST * (XB - x), 0.0), (NY, 1))


def panel(ax, a, title, cmap, **kw):
    im = ax.imshow(a, origin="lower", extent=EXT, cmap=cmap, **kw)
    ax.axvline(XB, color="k", lw=0.6, ls=":")
    ax.set_title(title, fontsize=9); ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
    return im


# ---- 構成 1 ----
st = load_state("save", NX, NY)
db = np.loadtxt("dbinit.txt")
dz = st["z"] - z0
fig, axes = plt.subplots(1, 3, figsize=(14, 3.6))
fig.colorbar(panel(axes[0], np.where(db > 0, db, np.nan), "崩壊深 D (m)(t = 1 s に流動化)", "Oranges"), ax=axes[0], shrink=0.8)
fig.colorbar(panel(axes[1], dz, "地形変化 z − z₀ (m)、t = 10 s", "RdBu_r", vmin=-1, vmax=1), ax=axes[1], shrink=0.8)
fig.colorbar(panel(axes[2], np.where(st["h"] + st["hs"] > 1e-4, st["h"] + st["hs"], np.nan), "流動深 h + hs (m)、t = 10 s", "viridis"), ax=axes[2], shrink=0.8)
fig.suptitle("構成 1: 瞬時流動化(D = 1 m を斜面上の 11 × 12 セルに与え、放出した土塊が遷緩点下へ流下)", fontsize=10)
fig.tight_layout(); fig.savefig("figs/release.png", dpi=110); plt.close(fig)
print("release: min dz %.3f m, max dz (outside) %.3f m, sum h %.4f (expected λ relsat ΣD = %.4f), solids %.2e"
      % (dz.min(), np.where(db > 0, -9, dz).max(), st["h"].sum(), 0.4 * 1.0 * db.sum(), st["hs"].sum() + 0.6 * dz.sum()))

# ---- 構成 2・3 ----
fig, axes = plt.subplots(1, 4, figsize=(18, 3.6))
fs = np.loadtxt("result/Fs9999.txt"); d9 = np.loadtxt("result/D9999.txt")
st2 = load_state("save_fs", NX, NY)
fig.colorbar(panel(axes[0], np.where(fs > 0, fs, np.nan), "構成 2: 期間最小安全率 Fs9999(< 1 で崩壊)", "RdYlGn", vmin=0, vmax=2), ax=axes[0], shrink=0.8)
fig.colorbar(panel(axes[1], st2["sd"], "構成 2: 最終土層厚 sd (m)(0 = 崩壊して岩盤露出)", "YlOrBr_r"), ax=axes[1], shrink=0.8)
fig.colorbar(panel(axes[2], np.where(d9 > 1e-4, d9, np.nan), "構成 2: 最大流動深 D9999 (m)", "viridis"), ax=axes[2], shrink=0.8)
if os.path.isfile("result_fs2/Fs9999.txt"):
    fs2 = np.loadtxt("result_fs2/Fs9999.txt")
    fig.colorbar(panel(axes[3], np.where(fs2 > 0, fs2, np.nan), "構成 3: Fs9999(f_slide = 2、診断のみ・流動化なし)", "RdYlGn", vmin=0, vmax=2), ax=axes[3], shrink=0.8)
    print("fs2: min Fs9999 = %.3f, evaluated cells = %d" % (fs2[fs2 > 0].min(), (fs2 > 0).sum()))
fig.suptitle("構成 2・3: 無限長斜面安定判定 f_slide(降雨 → Green-Ampt 浸透で間隙水圧が上がり Fs < 1 で全層流動化)", fontsize=10)
fig.tight_layout(); fig.savefig("figs/fslide.png", dpi=110); plt.close(fig)
print("fslide: min Fs9999 = %.3f, cells with sd = 0: %d, max D9999 = %.3f m" % (fs[fs > 0].min(), (st2["sd"] <= 1e-12).sum(), d9.max()))
