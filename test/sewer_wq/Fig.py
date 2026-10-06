#!/usr/bin/env python3
"""test/sewer_wq(下水噴出の衛生リスク = 水質 × 管路連続体層)の結果を図にする。

  python3 Fig.py [result_dir]      既定 result → figs/sewer_wq.png

左: wq.csv の台帳(噴出 in_gwc、枡再取込 to_gwc、死滅 decay、地表残存)。
中: 最終の地表水の濃度 C(対数)。右: 最終の水深 h と管路。
"""
import glob, os, re, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
plt.rcParams["font.family"] = ["IPAGothic", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

here = os.path.dirname(os.path.abspath(__file__))
res = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "result")
data = os.path.join(here, "data_sewer")
DX = 10.0
cnd = np.loadtxt(os.path.join(data, "cnd_T.txt")) > 0
inlet = np.loadtxt(os.path.join(data, "inlet.txt")) > 0
ny, nx = cnd.shape

def read_wq(path):
    with open(path) as f:
        names = [s.strip() for s in f.readline().split(",")]
    d = np.loadtxt(path, delimiter=",", skiprows=1)
    return {n: d[:, i] for i, n in enumerate(names)}

def last(pre):
    fs = sorted(f for f in glob.glob(os.path.join(res, pre + "[0-9][0-9][0-9][0-9].txt"))
                if int(re.findall(r"(\d{4})\.txt", f)[0]) < 9000)
    return np.loadtxt(fs[-1]) if fs else None

w = read_wq(os.path.join(res, "wq.csv"))
t = w["time_s"] / 60
fig, axs = plt.subplots(1, 3, figsize=(16, 4.6), gridspec_kw=dict(width_ratios=[1.1, 1.1, 1.1]))
ax = axs[0]
ax.plot(t, w["in_gwc_g"], lw=2, label="噴出・吐口 in_gwc")
ax.plot(t, w["to_gwc_g"], lw=1.5, label="枡で再取込 to_gwc")
ax.plot(t, w["decay_g"], lw=1.5, label="死滅 decay(T90 = 1 日)")
ax.plot(t, w["mass_surface_g"], lw=2, ls="--", label="地表残存 mass_surface")
ax.plot(t, w["in_gwc_g"] - w["to_gwc_g"] - w["decay_g"] - w["mass_surface_g"], "k:", lw=1, label="閉合残差")
ax.set_xlabel("時間 (min)"); ax.set_ylabel("質量(単位: g = 10⁶ CFU)"); ax.set_xlim(0, 60)
ax.grid(alpha=0.4); ax.legend(fontsize=8.5); ax.set_title("水質台帳(降雨 100 mm/h × 30 min)")

C = last("C"); H = last("H")
ext = [0, nx * DX, 0, ny * DX]
ax = axs[1]
if C is not None:
    Cm = np.where((C > 1e-3) & (H > 1e-4), C, np.nan)
    im = ax.imshow(Cm, origin="lower", extent=ext, cmap="magma_r", norm=LogNorm(vmin=1e-2, vmax=1e4), interpolation="nearest")
    fig.colorbar(im, ax=ax, shrink=0.85, label="濃度 C(g/m³ = 10⁶ CFU/m³)")
yy, xx = np.nonzero(cnd); ax.plot((xx + 0.5) * DX, (yy + 0.5) * DX, "c.", ms=2)
ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)"); ax.set_title("最終の濃度(t = 1 h)")

ax = axs[2]
im = ax.imshow(np.where(H > 1e-4, H, np.nan), origin="lower", extent=ext, cmap="Blues", interpolation="nearest")
fig.colorbar(im, ax=ax, shrink=0.85, label="水深 h (m)")
yy, xx = np.nonzero(cnd); ax.plot((xx + 0.5) * DX, (yy + 0.5) * DX, "k.", ms=2, label="管路")
yy, xx = np.nonzero(inlet); ax.plot((xx + 0.5) * DX, (yy + 0.5) * DX, "r+", ms=5, label="枡")
ax.legend(fontsize=8, loc="upper right")
ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)"); ax.set_title("最終の水深(幹線 + 枝管網)")
fig.suptitle("test/sewer_wq — 下水噴出の衛生リスク(wq_gwc_conc = 1e4、サブサイクル N = 3)", fontsize=13)
fig.tight_layout()
fig.savefig(os.path.join(here, "figs", "sewer_wq.png"), dpi=110, bbox_inches="tight")
print("figs/sewer_wq.png")
k = -1
print("in_gwc %.4e to_gwc %.4e decay %.4e surface %.4e residual %.3e" % (w["in_gwc_g"][k], w["to_gwc_g"][k], w["decay_g"][k], w["mass_surface_g"][k], w["in_gwc_g"][k] - w["to_gwc_g"][k] - w["decay_g"][k] - w["mass_surface_g"][k]))
if C is not None: print("C max %.3e" % np.nanmax(C))
