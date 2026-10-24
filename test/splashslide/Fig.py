#!/usr/bin/env python3
"""test/splashslide の図を figs/splashslide.png に描く(事前に ./Run.sh を実行しておく)。
固結崖(f_splash のみ)と未固結崖(+ f_debris/f_slide、c′ = 0)の対照: 初期地形、最終地形、
崖面帯の y 方向起伏(谷の指標)の変化。引数 en で英語版を en/figs/ に。
"""
import glob, os, struct, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


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

zc0 = np.loadtxt("result_c/Z0000.txt"); zc1 = np.loadtxt("result_c/Z9998.txt")
zl0 = np.loadtxt("result_l/Z0000.txt"); zl1 = np.loadtxt("result_l/Z9998.txt")
ny, nx = zc0.shape; DX = 2.0
ext = [0, nx * DX, 0, ny * DX]


def relief(z):
    cols = [c for c in range(nx) if 0.5 < z[:, c].mean() < 8.5]
    return np.mean([z[:, c].std() for c in cols]), cols


fig, axes = plt.subplots(2, 3, figsize=(15, 7))
for row, (z0, z1, lab) in enumerate([(zc0, zc1, T("構成 1: 固結崖(f_splash のみ)", "Configuration 1: consolidated cliff (f_splash only)")),
                                           (zl0, zl1, T("構成 2: 未固結崖(+ f_debris・f_slide、c′ = 0)", "Configuration 2: unconsolidated cliff (+ f_debris, f_slide, c′ = 0)"))]):
    r0, cols = relief(z0); r1, _ = relief(z1)
    im = axes[row, 0].imshow(z0, origin="lower", extent=ext, cmap="terrain"); axes[row, 0].set_title(f"{lab.split(':')[0]}: " + T("初期地形 z (m)", "initial terrain z (m)"), fontsize=9); fig.colorbar(im, ax=axes[row, 0], shrink=0.8)
    im = axes[row, 1].imshow(z1 - z0, origin="lower", extent=ext, cmap="RdBu_r", vmin=-1, vmax=1); axes[row, 1].set_title(T("地形変化 z − z₀ (m)、20 min", "terrain change z − z₀ (m), 20 min"), fontsize=9); fig.colorbar(im, ax=axes[row, 1], shrink=0.8)
    y = (np.arange(ny) + 0.5) * DX
    c = cols[len(cols) // 2]
    axes[row, 2].plot(y, z0[:, c] - z0[:, c].mean(), "0.5", label=T("初期(崖面帯の列 ix = ", "initial (cliff-face band column ix = ") + f"{c+1})")
    axes[row, 2].plot(y, z1[:, c] - z1[:, c].mean(), "C3", label=T("最終", "final"))
    axes[row, 2].set_title(T(f"崖面帯の y 方向起伏: 標準偏差 {r0:.3f} → {r1:.3f} m(× {r1/r0:.2f})", f"y-direction relief of the cliff-face band: std {r0:.3f} → {r1:.3f} m (× {r1/r0:.2f})"), fontsize=9)
    axes[row, 2].set_xlabel("y (m)"); axes[row, 2].set_ylabel(T("z − 平均 (m)", "z − mean (m)")); axes[row, 2].grid(alpha=0.3); axes[row, 2].legend(fontsize=8)
    print("%s relief %.4f -> %.4f (x%.2f), plateau max|dz| %.3e, min z %.3f" % (lab[:5], r0, r1, r1 / r0, np.abs(z1 - z0)[:, :3].max(), z1.min()))
for ax in axes[:, :2].flat:
    ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
fig.suptitle(T("白ママ対照: 台地 + 擾乱付き急崖(56°)、降雨 30 mm/h。谷が成長するのは固結崖だけ(§48.1)",
                "Shiromama contrast: plateau + perturbed steep cliff (56°), rainfall 30 mm/h. Only the consolidated cliff grows valleys (§48.1)"), fontsize=10)
fig.tight_layout(); fig.savefig(f"{FIGDIR}/splashslide.png", dpi=110); plt.close(fig)
