#!/usr/bin/env python3
"""test/coastal_drain(海抜下ポルダーの排水。§46.5 (7)(8))の結果を図にする。

  python3 Fig.py [result_dir]      既定 result → figs/coastal_drain.png

左: プローブ 3 点(吐口そば (26,8)、機場取水 (20,8)、西の低地 (4,4))の水位
    z + h と潮位 0.5 m。中: 管路行(j = 8)の管内水頭 hgc の最終分布と
    解析平衡 cap + (潮位 − 管頂水頭)·slot_sy。右: 最終の水位 E の分布。
"""
import glob, os, re, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = ["IPAGothic", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

here = os.path.dirname(os.path.abspath(__file__))
res = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "result")
data = os.path.join(here, "data_cd")
DX = 10.0
z = np.loadtxt(os.path.join(data, "z.txt")); sw = np.loadtxt(os.path.join(data, "sw.txt")) > 0
cnd = np.loadtxt(os.path.join(data, "cnd.txt")) > 0
ny, nx = z.shape

def last(pre):
    fs = sorted(f for f in glob.glob(os.path.join(res, pre + "[0-9][0-9][0-9][0-9].txt"))
                if int(re.findall(r"(\d{4})\.txt", f)[0]) < 9000)
    return np.loadtxt(fs[-1])

E = last("E"); Hgc = last("Hgc")
fig, axs = plt.subplots(1, 3, figsize=(16, 4.6), gridspec_kw=dict(width_ratios=[1.1, 1, 1.2]))
ax = axs[0]
names = ["吐口そば (26,8)", "機場取水 (20,8)", "西の低地 (4,4)"]
for n, lab in enumerate(names, 1):
    d = np.loadtxt(os.path.join(res, "probes", f"probe{n:04d}.csv"), delimiter=",", comments="#")
    ax.plot(d[:, 0] * 60, d[:, 2] + d[:, 3], lw=1.6, label=lab)
ax.axhline(0.5, color="k", ls="--", lw=1, label="潮位 0.5 m")
ax.set_xlabel("時間 (min)"); ax.set_ylabel("水位 z + h (m)"); ax.set_xlim(0, 120)
ax.grid(alpha=0.4); ax.legend(fontsize=9); ax.set_title("ポルダーの水位(堤防なし → 潮位へ平衡)")

ax = axs[1]
j = 7
xi = np.arange(nx)[cnd[j]] + 1
ax.plot(xi, Hgc[j][cnd[j]], "o-", ms=4, label="計算 hgc(t = 2 h)")
ax.axhline(0.1 + (0.5 - (-0.8)) * 0.02, color="r", ls="--", label="解析平衡 0.1 + 1.3×0.02 = 0.126")
ax.set_xlabel("i(管路行 j = 8)"); ax.set_ylabel("管内水頭 hgc (m)"); ax.set_ylim(0.10, 0.14)
ax.grid(alpha=0.4); ax.legend(fontsize=9); ax.set_title("管路セルの等化上限")

ax = axs[2]
ext = [0, nx * DX, 0, ny * DX]
im = ax.imshow(E, origin="lower", extent=ext, cmap="viridis", vmin=0.45, vmax=0.55, interpolation="nearest")
yy, xx = np.nonzero(cnd); ax.plot((xx + 0.5) * DX, (yy + 0.5) * DX, "w.", ms=3)
yy, xx = np.nonzero(sw); ax.plot((xx + 0.5) * DX, (yy + 0.5) * DX, "c,", alpha=0.8)
ax.plot([(26 - 0.5) * DX], [(8 - 0.5) * DX], "rs", mfc="none", mew=2, ms=10)
ax.plot([(20 - 0.5) * DX], [(8 - 0.5) * DX], "r^", mfc="none", mew=2, ms=10)
ax.plot([(4 - 0.5) * DX], [(4 - 0.5) * DX], "rv", mfc="none", mew=2, ms=10)
fig.colorbar(im, ax=ax, shrink=0.85, label="水位 E (m)")
ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
ax.set_title("最終水位(白点 = 管路、□ 吐口、△ 機場取水、▽ 機場放流)")
fig.suptitle("test/coastal_drain — 負の管底・海域吐口・機場(潮位 0.5 m、地盤 0.2 m)", fontsize=13)
fig.tight_layout()
fig.savefig(os.path.join(here, "figs", "coastal_drain.png"), dpi=110, bbox_inches="tight")
print("figs/coastal_drain.png")
print("E: min %.4f max %.4f ; hgc on conduit: min %.4f max %.4f" % (E.min(), E.max(), Hgc[cnd].min(), Hgc[cnd].max()))
