#!/usr/bin/env python3
"""test/chichibu_cond の回帰ケース(100 m 格子、6 h)の結果を図にする。

  python3 Fig.py [result_dir] [ref=<dir>] [en]
      既定 result → figs/chichibu_cond.png(en で英語版を en/figs/chichibu_cond.png に)

左: 測線 1〜4 のハイドログラフ(fluxes/flux000N.csv の Q)。
右: プローブ 2 点の水深(probes/probe000N.csv)。
ref=<dir>(既定 ../chichibu/result)に test/chichibu の回帰ケースの結果があれば、
破線で重ねる(入力だけが違う 2 つの計算の比較。なければ、このケースだけを描く)。
"""
import os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

EN = "en" in sys.argv[1:]
def T(ja, en): return en if EN else ja
here = os.path.dirname(os.path.abspath(__file__))
FIGDIR = os.path.join(here, "en/figs" if EN else "figs")
args = [a for a in sys.argv[1:] if a != "en"]
ref = os.path.join(here, "..", "chichibu", "result")
for a in list(args):
    if a.startswith("ref="):
        ref = a[4:]; args.remove(a)
res = args[0] if args else os.path.join(here, "result")
plt.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

def load(path):
    return np.loadtxt(path, delimiter=",", comments="#")

has_ref = os.path.exists(os.path.join(ref, "fluxes", "flux0001.csv"))
C = ["#9467bd", "#2ca02c", "#1f9fd0", "#e08a00"]
fig, ax = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw=dict(width_ratios=[1.4, 1]))

# 左: 測線 1〜4 の流量
for n in range(1, 5):
    d = load(os.path.join(res, "fluxes", f"flux{n:04d}.csv"))
    ax[0].plot(d[:, 0], d[:, 2], color=C[n - 1], lw=1.8, label=T(f"測線 {n}", f"transect {n}"))
    i = int(np.argmax(d[:, 2]))
    print(f"flux{n}: peak {d[i, 2]:.1f} m3/s at {d[i, 0]:.2f} h")
    if has_ref:
        r = load(os.path.join(ref, "fluxes", f"flux{n:04d}.csv"))
        ax[0].plot(r[:, 0], r[:, 2], color=C[n - 1], lw=1.2, ls="--")
ax[0].plot([], [], color="k", lw=1.8, label=T("実線: このケース(河床を整えた標高・河道の粗度 0.04)",
                                              "solid: this case (conditioned bed, channel n = 0.04)"))
if has_ref:
    ax[0].plot([], [], color="k", lw=1.2, ls="--", label=T("破線: test/chichibu(窪地処理済みの標高・0.02)",
                                                          "dashed: test/chichibu (depression-filled, 0.02)"))
ax[0].set_xlabel(T("時間 (h)", "time (h)")); ax[0].set_ylabel(T("流量 (m$^3$/s)", "discharge (m$^3$/s)"))
ax[0].set_xlim(0, 6); ax[0].set_ylim(0, 9000); ax[0].grid(alpha=0.4)
ax[0].legend(fontsize=8.5, loc="upper right")
ax[0].set_title(T("測線 1〜4 の流量", "Discharge at transects 1 to 4"))

# 右: プローブの水深
for n in (1, 2):
    d = load(os.path.join(res, "probes", f"probe{n:04d}.csv"))
    ax[1].plot(d[:, 0], d[:, 3], color=C[n - 1], lw=1.8, label=T(f"プローブ {n}", f"probe {n}"))
    i = int(np.argmax(d[:, 3]))
    print(f"probe{n}: max depth {d[i, 3]:.2f} m at {d[i, 0]:.2f} h")
    if has_ref:
        r = load(os.path.join(ref, "probes", f"probe{n:04d}.csv"))
        ax[1].plot(r[:, 0], r[:, 3], color=C[n - 1], lw=1.2, ls="--")
ax[1].set_xlabel(T("時間 (h)", "time (h)")); ax[1].set_ylabel(T("水深 (m)", "depth (m)"))
ax[1].set_xlim(0, 6); ax[1].set_ylim(bottom=0); ax[1].grid(alpha=0.4); ax[1].legend(fontsize=9)
ax[1].set_title(T("プローブの水深", "Depth at the probes"))

fig.tight_layout()
os.makedirs(FIGDIR, exist_ok=True)
out = os.path.join(FIGDIR, "chichibu_cond.png")
fig.savefig(out, dpi=110)
print("saved", out)
