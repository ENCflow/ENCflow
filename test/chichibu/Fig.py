#!/usr/bin/env python3
"""test/chichibu の回帰ケース(param.txt。100 m 格子、6 h)の結果を図にする。

  python3 Fig.py [result_dir]      既定 result → figs/chichibu.png

左: 6 時間の最大水深(10 分ごとの出力 H*.txt の最大。流域マスク外は灰色)。
    河道マスクを細線で重ね、測線 1〜4 とプローブを描く。
中: 測線 1〜4 のハイドログラフ(fluxes/flux000N.csv の Q)と降雨。
右: プローブ 2 点の水深。
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
data = os.path.join(here, "data_chichibu")
DX = 100.0

def grid(path):
    return np.loadtxt(path)

z = grid(os.path.join(data, "Chichibu_100m_filled2.txt"))
rw = grid(os.path.join(data, "Chichibu_100m_river.txt")) > 0
mask = grid(os.path.join(data, "Chichibu_100m_basin.txt")) > 0
ny, nx = z.shape

hfiles = sorted(f for f in glob.glob(os.path.join(res, "H[0-9][0-9][0-9][0-9].txt"))
                if int(re.findall(r"(\d{4})\.txt", f)[0]) < 9000)
hmax = np.zeros_like(z)
for f in hfiles:
    hmax = np.maximum(hmax, grid(f))
hmax[~mask] = np.nan

# 測線・プローブ(param.txt から)
flx = [(165, 212, 165, 208), (215, 205, 215, 200), (296, 207, 296, 204), (433, 80, 433, 74)]
pbs = [(165, 210), (215, 203)]

fig = plt.figure(figsize=(16, 5.2))
gs = fig.add_gridspec(1, 3, width_ratios=[1.45, 1, 0.8], wspace=0.28)
ax = fig.add_subplot(gs[0])
ext = [0, nx * DX / 1000, 0, ny * DX / 1000]
ax.imshow(np.where(mask, 1.0, 0.0), origin="lower", extent=ext, cmap="Greys", vmin=-0.3, vmax=4, interpolation="nearest")
hm = np.where(hmax > 0.01, hmax, np.nan)
im = ax.imshow(hm, origin="lower", extent=ext, cmap="Blues", norm=LogNorm(vmin=0.01, vmax=10), interpolation="nearest")
yy, xx = np.nonzero(rw & mask)
ax.plot((xx + 0.5) * DX / 1000, (yy + 0.5) * DX / 1000, ",", color="k", alpha=0.35)
for n, (xr, yr, xl, yl) in enumerate(flx, 1):
    ax.plot([(xr - 0.5) * DX / 1000, (xl - 0.5) * DX / 1000], [(yr - 0.5) * DX / 1000, (yl - 0.5) * DX / 1000], "r-", lw=2)
    ax.text((xr + 3) * DX / 1000, (yr + 2) * DX / 1000, f"測線{n}", color="r", fontsize=10, fontweight="bold")
for n, (xp, yp) in enumerate(pbs, 1):
    ax.plot((xp - 0.5) * DX / 1000, (yp - 0.5) * DX / 1000, "o", mfc="none", mec="darkorange", mew=2, ms=8)
fig.colorbar(im, ax=ax, shrink=0.8, pad=0.02, label="6 時間の最大水深 (m)")
ax.set_xlabel("x (km)"); ax.set_ylabel("y (km)")
ax.set_title("最大水深と河道マスク(灰 = 流域外)")

ax = fig.add_subplot(gs[1])
peaks = []
for n in range(1, 5):
    d = np.loadtxt(os.path.join(res, "fluxes", f"flux{n:04d}.csv"), delimiter=",", comments="#")
    t, q = d[:, 0], d[:, 2]
    ax.plot(t, q, lw=1.6, label=f"測線{n}")
    k = np.argmax(q); peaks.append((n, q[k], t[k]))
ax.set_xlabel("時間 (h)"); ax.set_ylabel("流量 Q (m³/s)")
ax.set_xlim(0, 6); ax.grid(alpha=0.4); ax.legend(loc="upper left")
ax2 = ax.twinx()
ax2.bar([0.25], [200], width=0.5, color="steelblue", alpha=0.25, align="center")
ax2.set_ylim(800, 0); ax2.set_ylabel("降雨強度 (mm/h)", color="steelblue")
ax.set_title("測線の流量(0.5 h × 200 mm/h)")

ax = fig.add_subplot(gs[2])
for n in range(1, 3):
    d = np.loadtxt(os.path.join(res, "probes", f"probe{n:04d}.csv"), delimiter=",", comments="#")
    ax.plot(d[:, 0], d[:, 3], lw=1.6, label=f"プローブ{n}")
ax.set_xlabel("時間 (h)"); ax.set_ylabel("水深 h (m)")
ax.set_xlim(0, 6); ax.grid(alpha=0.4); ax.legend()
ax.set_title("河道セルの水深")

fig.suptitle("test/chichibu — 秩父流域 100 m 格子の回帰ケース(6 h)", fontsize=13)
os.makedirs(os.path.join(here, "figs"), exist_ok=True)
fig.savefig(os.path.join(here, "figs", "chichibu.png"), dpi=110, bbox_inches="tight")
print("figs/chichibu.png")
for n, q, t in peaks:
    print(f"flux{n}: peak {q:.1f} m3/s at {t:.2f} h")
print("max depth in basin: %.2f m, max channel depth: %.2f m" % (np.nanmax(hmax), np.nanmax(np.where(rw, hmax, np.nan))))
