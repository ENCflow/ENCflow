#!/usr/bin/env python3
"""test/splash の図を figs/splash.png に描く(事前に ./Run.sh を実行しておく。引数 en で英語版を en/figs/ に)。
乾式斜面侵食(f_splash)の解析検証: 列クラス別の理論値 Δz = P (kr + kt S) T_geo と、
出力 Sd9998 − Sd0000(= z の変化)の行平均の縦断。
"""
import sys, glob, os, struct
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
EN = "en" in sys.argv[1:]
def T(ja, en): return en if EN else ja
FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)


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

sd0 = np.loadtxt("result/Sd0000.txt"); sd1 = np.loadtxt("result/Sd9998.txt")
dz = sd1 - sd0
ny, nx = dz.shape
x = np.arange(nx) + 0.5
fig, axes = plt.subplots(1, 2, figsize=(12, 4), gridspec_kw={"width_ratios": [1.5, 1]})
ax = axes[0]
ax.plot(x, dz.mean(axis=0) * 1e3, "C3o-", ms=3, lw=1, label=T("計算(行平均)Δz = Sd9998 − Sd0000", "Computed (row mean) Δz = Sd9998 − Sd0000"))
ax.axhline(-1.5, color="k", ls="--", lw=1, label=T("理論: 斜面内部 −1.5 mm", "Theory: slope interior −1.5 mm"))
ax.axhline(-0.45, color="0.5", ls="--", lw=1, label=T("理論: 平坦部 −0.45 mm", "Theory: flat part −0.45 mm"))
ax.axvline(30, color="0.5", ls=":")
ax.set_xlabel("x (m)"); ax.set_ylabel("Δz (mm)"); ax.grid(alpha=0.3); ax.legend(fontsize=8)
ax.set_title(T("1 時間 × morfac 5(T_geo = 18,000 s)の侵食深。遷緩点 x = 30 m", "Erosion depth after 1 h × morfac 5 (T_geo = 18,000 s). Slope break at x = 30 m"), fontsize=10)
im = axes[1].imshow(dz * 1e3, origin="lower", extent=[0, 50, 0, 12], cmap="Reds_r")
axes[1].set_title(T("Δz (mm) の分布(横断方向に一様)", "Distribution of Δz (mm) (transversely uniform)"), fontsize=10); axes[1].set_xlabel("x (m)"); axes[1].set_ylabel("y (m)")
fig.colorbar(im, ax=axes[1], shrink=0.8)
fig.suptitle(T("乾式斜面侵食(f_splash): 降雨 30 mm/h・Green-Ampt 72 mm/h(常に h = 0)・凹地形増幅なし",
               "Dry-slope erosion (f_splash): rainfall 30 mm/h, Green-Ampt 72 mm/h (h = 0 at all times), no hollow amplification"), fontsize=10)
fig.tight_layout(); fig.savefig(f"{FIGDIR}/splash.png", dpi=110); plt.close(fig)
print("interior slope mean dz %.4e m, flat mean dz %.4e m, total eroded %.5f m3, row spread %.1e" % (dz[:, 5:25].mean(), dz[:, 35:48].mean(), -dz.sum() * 1.0, dz.std(axis=0).max()))
