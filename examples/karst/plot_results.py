#!/usr/bin/env python3
"""examples/karst の図化と数表(事前に param.txt を実行しておく)。

  python3 plot_results.py | tee analysis.txt

図(figs/):
  maps.png        初期地形・最終地形の陰影図、削剥深 z0 − z、最大湛水深 H9999
  evolution.png   削剥深の時間発展(出力時刻ごとの陰影+等深線)
  sections.png    最も深いドリーネを通る x・y 断面の時間発展
  hydrograph.png  Log の S_surf(湛水)と S_grnd(地下貯留)の時系列(最初の 3 日と最後の 3 日)
  stats.png       削剥深の分布(ヒストグラム)と、深さ別のドリーネ数・最大深・平均削剥の時系列
数表(標準出力): 水収支、溶けた岩の体積の検算(Z の体積差 ÷ (1 − 残渣率) vs 台帳)、
  面的削剥と集中削剥の分離、ドリーネの個数と深さ

依存: numpy, matplotlib
"""
import csv
import os
import re
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource
matplotlib.rcParams["font.family"] = ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs("figs", exist_ok=True)

PARAM = "param.txt"
SCREEN = "Screen.log"
RIM = 3                     # make_terrain.py の不溶の縁(セル)


def read_param(fn):
    p = {}
    for line in open(fn, encoding="utf-8"):
        line = line.split("!")[0]
        m = re.match(r"\s*(\w+)\s*=\s*([^,\s]+)", line)
        if m:
            p[m.group(1)] = m.group(2).strip("'\"")
    return p


def file_times(resdir):
    t = {}
    for row in csv.reader(open(os.path.join(resdir, "FILENUMBER.csv"))):
        if row[0].startswith("#"):
            continue
        t[int(row[0])] = float(row[2])
    return t


def hillshade(z, dx):
    ls = LightSource(azdeg=315, altdeg=40)
    return ls.hillshade(z, vert_exag=3.0, dx=dx, dy=dx)


p = read_param(PARAM)
res = p["dir_result"]
dx = float(p["lx"]) / int(p["nx"])
morfac = float(p["morfac"])
kd = float(p["dissol_ceq"]) * 1.0e-3 / float(p["dissol_rho"])
fres = float(p.get("dissol_fres", 0.0))
YR = 365.25 * 86400.0
times = file_times(res)
snaps = []
for n in sorted(times):
    if n >= 9998:
        continue
    f = os.path.join(res, "Z%04d.txt" % n)
    if os.path.exists(f):
        snaps.append((times[n] * morfac / YR, np.loadtxt(f)))
z0 = snaps[0][1]
zf = np.loadtxt(os.path.join(res, "Z9998.txt"))
tend = times[9998] * morfac / YR
if snaps[-1][0] < tend:
    snaps.append((tend, zf))
hmax = np.loadtxt(os.path.join(res, "H9999.txt"))
ny, nx = z0.shape
ext = [0, nx * dx, 0, ny * dx]
inner = np.zeros_like(z0, dtype=bool)
inner[RIM:-RIM, RIM:-RIM] = True
d = z0 - zf                                   # 削剥深 (m)

# ---------------------------------------------------------------- 数表
log = open(SCREEN, errors="ignore").read() if os.path.exists(SCREEN) else ""
rows = [l.split() for l in log.splitlines() if re.match(r"\s*\d+:\d\d:\d\d", l)]
m = re.search(r"dissolution removed\s*([0-9.Ee+-]+)\s*m3", log)
vled = float(m.group(1)) if m else np.nan
vz = d.sum() * dx * dx                        # 地表の体積減少 (m3)
print("== 水収支(Log の S 列。m = 領域平均の柱状水量)")
if rows:
    print("  最終 S_surf = %s, S_grnd = %s, S_total = %s (降雨累計 = 40 mm × %d 日 = %.3f m)"
          % (rows[-1][2], rows[-1][3], rows[-1][4], int(round(times[9998] / 86400)), 0.04 * times[9998] / 86400))
print("== 溶けた岩の体積の検算")
print("  地表の体積減少 Σ(z0 − z)Δx² = %.1f m3、÷(1 − f_res = %.2f) = %.1f m3、台帳 = %.1f m3"
      % (vz, fres, vz / (1.0 - fres), vled))
# 面的削剥(縁から離れた、湛水しなかったセルの代表値 = 中央値)と集中削剥
dry = inner & (hmax < 0.01)
dif = np.median(d[dry]) if dry.any() else np.nan
print("== 面的削剥と集中削剥(地形時間 %.0f 年)" % tend)
print("  湛水しなかったセルの削剥深の中央値 = %.4f m(= %.1f mm/kyr。涵養 × k_d の面的溶食)"
      % (dif, dif / tend * 1.0e6))
print("  最大削剥深 = %.3f m(面的の %.0f 倍)、削剥深 > 1 m のセル数 = %d、> 2 m = %d"
      % (d.max(), d.max() / max(dif, 1e-9), int((d > 1.0).sum()), int((d > 2.0).sum())))
vdif = dif * inner.sum() * dx * dx
print("  体積の内訳: 面的 ≈ %.0f m3(%.0f %%)、集中 ≈ %.0f m3(%.0f %%)"
      % (vdif, 100 * vdif / vz, vz - vdif, 100 * (vz - vdif) / vz))


def basins(dd, thr):
    """削剥深 > thr の連結成分(8 近傍)の個数と各成分の最大深"""
    mask = dd > thr
    lab = np.zeros(dd.shape, dtype=int)
    n = 0
    for j in range(dd.shape[0]):
        for i in range(dd.shape[1]):
            if mask[j, i] and lab[j, i] == 0:
                n += 1
                stack = [(j, i)]
                lab[j, i] = n
                while stack:
                    jj, ii = stack.pop()
                    for dj in (-1, 0, 1):
                        for di in (-1, 0, 1):
                            a, b = jj + dj, ii + di
                            if 0 <= a < dd.shape[0] and 0 <= b < dd.shape[1] and mask[a, b] and lab[a, b] == 0:
                                lab[a, b] = n
                                stack.append((a, b))
    depths = [dd[lab == k].max() for k in range(1, n + 1)]
    return n, depths, lab


for thr in (0.5, 1.0, 2.0):
    n, depths, _ = basins(d, thr)
    print("  削剥深 > %.1f m の窪み: %d 個(最大深 %s m)"
          % (thr, n, ", ".join("%.1f" % v for v in sorted(depths, reverse=True)[:8])))
print("== 削剥深の時系列(地形時間 年: 最大 / 中央値 / 平均 m)")
series = []
for t, z in snaps:
    dd = z0 - z
    series.append((t, dd.max(), np.median(dd[inner]), dd[inner].mean(), basins(dd, 1.0)[0]))
    print("  %6.0f: %.3f / %.4f / %.4f  (> 1 m の窪み %d 個)" % series[-1])

# ---------------------------------------------------------------- 図: maps
fig, axes = plt.subplots(2, 2, figsize=(11, 10))
x = (np.arange(nx) + 0.5) * dx
y = (np.arange(ny) + 0.5) * dx
ax = axes[0, 0]
ax.imshow(hillshade(z0, dx), cmap="gray", extent=ext, origin="lower", vmin=0, vmax=1)
cs = ax.contour(x, y, z0, levels=np.arange(296, 306, 1), colors="tab:blue", linewidths=0.4)
ax.set_title("初期地形(等高線 1 m)")
ax = axes[0, 1]
ax.imshow(hillshade(zf, dx), cmap="gray", extent=ext, origin="lower", vmin=0, vmax=1)
ax.contour(x, y, zf, levels=np.arange(290, 306, 1), colors="tab:blue", linewidths=0.4)
ax.set_title("最終地形(地形時間 %.0f 年)" % tend)
ax = axes[1, 0]
im = ax.imshow(d, extent=ext, origin="lower", cmap="magma_r", vmin=0, vmax=max(d.max(), 0.1))
plt.colorbar(im, ax=ax, label="削剥深 z0 − z (m)")
ax.set_title("削剥深(面的 %.2f m + ドリーネ)" % dif)
ax = axes[1, 1]
im = ax.imshow(hmax, extent=ext, origin="lower", cmap="Blues", vmin=0, vmax=max(hmax.max(), 0.1))
plt.colorbar(im, ax=ax, label="最大湛水深 (m)")
ax.set_title("期間最大の湛水深(H9999)")
for ax in axes.flat:
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
plt.tight_layout()
plt.savefig("figs/maps.png", dpi=130)
plt.close()

# ---------------------------------------------------------------- 図: evolution
sel = snaps[1:] if len(snaps) > 1 else snaps
ncol = min(4, len(sel))
idx = np.linspace(0, len(sel) - 1, ncol).round().astype(int)
fig, axes = plt.subplots(1, ncol, figsize=(4.2 * ncol, 4.4), squeeze=False)
for ax, k in zip(axes[0], idx):
    t, z = sel[k]
    dd = z0 - z
    ax.imshow(hillshade(z, dx), cmap="gray", extent=ext, origin="lower", vmin=0, vmax=1)
    cs = ax.contour(x, y, dd, levels=[0.5, 1, 2, 4, 8], colors=["gold", "orange", "red", "purple", "black"], linewidths=0.8)
    ax.clabel(cs, fmt="%g m", fontsize=7)
    ax.set_title("%.0f 年(最大削剥 %.1f m)" % (t, dd.max()))
    ax.set_xlabel("x (m)")
axes[0, 0].set_ylabel("y (m)")
plt.tight_layout()
plt.savefig("figs/evolution.png", dpi=130)
plt.close()

# ---------------------------------------------------------------- 図: sections
jm, im_ = np.unravel_index(np.argmax(d), d.shape)
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
for ax, (lab, getter, coord) in zip(axes, [("x 断面 (y = %.0f m)" % y[jm], lambda z: z[jm, :], x),
                                           ("y 断面 (x = %.0f m)" % x[im_], lambda z: z[:, im_], y)]):
    for t, z in snaps:
        ax.plot(coord, getter(z), lw=0.9, label="%.0f 年" % t)
    ax.set_title(lab + " — 最も深いドリーネを通る")
    ax.set_xlabel("距離 (m)")
    ax.set_ylabel("z (m)")
    ax.grid(alpha=0.3)
axes[0].legend(fontsize=7, ncol=2)
plt.tight_layout()
plt.savefig("figs/sections.png", dpi=130)
plt.close()

# ---------------------------------------------------------------- 図: hydrograph
if rows:
    th = np.array([sum(float(v) * f for v, f in zip(r[0].split(":"), (1.0, 1 / 60.0, 1 / 3600.0))) for r in rows])
    ss = np.array([float(r[2]) for r in rows])
    sg = np.array([float(r[3]) for r in rows])
    fig, axes = plt.subplots(1, 2, figsize=(12, 3.8))
    for ax, (t1, t2, lab) in zip(axes, [(0, 72, "最初の 3 日"), (th[-1] - 72, th[-1], "最後の 3 日")]):
        m = (th >= t1) & (th <= t2)
        ax.plot(th[m] / 24, ss[m] * 1000, "b-", label="S_surf(湛水)")
        ax2 = ax.twinx()
        ax2.plot(th[m] / 24, sg[m] * 1000, "g-", label="S_grnd(土層+管路層)")
        ax.set_xlabel("水理時間 (日)")
        ax.set_ylabel("湛水 (mm、領域平均)", color="b")
        ax2.set_ylabel("地下貯留 (mm、領域平均)", color="g")
        ax.set_title(lab + ": 豪雨 40 mm × 1 h の後、湛水が吸込穴と土層へ消える")
        ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig("figs/hydrograph.png", dpi=130)
    plt.close()

# ---------------------------------------------------------------- 図: stats
fig, axes = plt.subplots(1, 3, figsize=(14, 3.8))
ax = axes[0]
ax.hist(d[inner].ravel(), bins=60, color="tab:brown")
ax.set_yscale("log")
ax.set_xlabel("削剥深 (m)")
ax.set_ylabel("セル数")
ax.set_title("削剥深の分布(内部セル)")
ax = axes[1]
ts = np.array(series)
ax.plot(ts[:, 0], ts[:, 1], "r-o", ms=3, label="最大")
ax.plot(ts[:, 0], ts[:, 3], "k-o", ms=3, label="平均")
ax.plot(ts[:, 0], ts[:, 2], "b-o", ms=3, label="中央値(面的)")
ax.set_xlabel("地形時間 (年)")
ax.set_ylabel("削剥深 (m)")
ax.set_yscale("log")
ax.legend(fontsize=8)
ax.grid(alpha=0.3)
ax.set_title("削剥深の時間発展")
ax = axes[2]
ax.plot(ts[:, 0], ts[:, 4], "m-o", ms=3)
ax.set_xlabel("地形時間 (年)")
ax.set_ylabel("削剥深 > 1 m の窪みの数")
ax.grid(alpha=0.3)
ax.set_title("ドリーネの数")
plt.tight_layout()
plt.savefig("figs/stats.png", dpi=130)
plt.close()
print("figs/maps.png, evolution.png, sections.png, hydrograph.png, stats.png written")
