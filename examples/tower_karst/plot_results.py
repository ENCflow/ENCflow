#!/usr/bin/env python3
"""examples/tower_karst の図化と数表(事前に param.txt を実行しておく)。

  python3 plot_results.py | tee analysis.txt

図(figs/):
  maps.png        初期・最終地形の陰影図、削剥深(対数)、最終の土層厚(岩屑・残渣)
  sections.png    塔 1(左下)の中心を通る x 断面と y 断面の時間発展
  towers.png      各丘の頂高・平野からの比高・裾の半径(z > 平野 + 5 m の等価半径)の時間発展
  hydrograph.png  Log の S_surf・S_grnd(最初の 3 日と最後の 3 日)
数表(標準出力): 水収支、溶けた岩の体積の検算、平野・裾・塔の削剥、崩落の台帳

依存: numpy, matplotlib
"""
import csv
import os
import re
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource, LogNorm
matplotlib.rcParams["font.family"] = ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs("figs", exist_ok=True)

PARAM = sys.argv[1] if len(sys.argv) > 1 else "param.txt"
SUFFIX = "" if PARAM == "param.txt" else "_" + PARAM[6:-4]
SCREEN = "Screen%s.log" % SUFFIX
HILLS = [(300.0, 300.0, 40.0, 90.0), (700.0, 320.0, 40.0, 90.0),
         (320.0, 720.0, 40.0, 90.0), (690.0, 700.0, 40.0, 90.0),
         (500.0, 520.0, 20.0, 60.0), (150.0, 850.0, 20.0, 60.0)]   # make_terrain.py と同じ
STORMS_PER_YR = 50.0
YR = 86400.0 * STORMS_PER_YR


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
    return LightSource(azdeg=315, altdeg=40).hillshade(z, vert_exag=2.0, dx=dx, dy=dx)


p = read_param(PARAM)
res = p["dir_result"]
dx = float(p["lx"]) / int(p["nx"])
morfac = float(p["morfac"])
fres = float(p.get("dissol_fres", 0.0))
times = file_times(res)
snaps = []
for n in sorted(times):
    if n >= 9998:
        continue
    f = os.path.join(res, "Z%04d.txt" % n)
    if os.path.exists(f):
        snaps.append((times[n] * morfac / YR, np.loadtxt(f), np.loadtxt(os.path.join(res, "Sd%04d.txt" % n))))
z0, sd0 = snaps[0][1], snaps[0][2]
zf = np.loadtxt(os.path.join(res, "Z9998.txt"))
sdf = np.loadtxt(os.path.join(res, "Sd9998.txt"))
tend = times[9998] * morfac / YR
if snaps[-1][0] < tend:
    snaps.append((tend, zf, sdf))
hmax = np.loadtxt(os.path.join(res, "H9999.txt"))
ny, nx = z0.shape
ext = [0, nx * dx, 0, ny * dx]
x = (np.arange(nx) + 0.5) * dx
y = (np.arange(ny) + 0.5) * dx
X, Y = np.meshgrid(x, y)
d = z0 - zf
rock0 = z0 > 5.0
plain0 = ~rock0

# ---------------------------------------------------------------- 数表
log = open(SCREEN, errors="ignore").read() if os.path.exists(SCREEN) else ""
rows = [l.split() for l in log.splitlines() if re.match(r"\s*[\d*]+:\d\d:\d\d", l)]
m = re.search(r"dissolution removed\s*([0-9.Ee+-]+)\s*m3", log)
vled = float(m.group(1)) if m else np.nan
m = re.search(r"rockfall moved\s*([0-9.Ee+-]+)\s*m3", log)
vrock = float(m.group(1)) if m else np.nan
bulk = float(p.get("rockfall_bulk", 1.5))
print("== 水収支: 最終 S_total = %s m(降雨累計 40 mm × %d 日 = %.3f m)"
      % (rows[-1][4] if rows else "?", int(round(times[9998] / 86400)), 0.04 * times[9998] / 86400))
vz = -(zf - z0).sum() * dx * dx                  # 地表の体積減少(崩落は (bulk−1)×岩 だけ増やす)
print("== 体積の検算(地形時間 %.0f 年 = 豪雨 %d 回を年 %d 回で換算)" % (tend, round(tend * STORMS_PER_YR), STORMS_PER_YR))
print("  溶けた岩(台帳)= %.0f m3、崩落した岩(台帳)= %.0f m3(岩屑 %.0f m3)" % (vled, vrock, vrock * bulk))
print("  地表の体積減少 Σ(z0 − z)Δx² = %.0f m3 ≈ 溶食 × (1 − f_res) − 崩落 × (bulk − 1) = %.0f m3"
      % (vz, vled * (1.0 - fres) - vrock * (bulk - 1.0)))
dp = np.median(d[plain0 & (hmax < 0.05)])
print("== 平野・裾・塔")
print("  平野(初期 z < 5 m、湛水なし)の削剥深の中央値 = %.2f m(= %.0f mm/kyr)" % (dp, dp / tend * 1.0e6))
foot = plain0 & (hmax >= 0.05)
print("  裾(湛水した平野セル %d 個)の削剥深の中央値 = %.2f m、最大 = %.2f m" % (int(foot.sum()), np.median(d[foot]) if foot.any() else np.nan, d[foot].max() if foot.any() else np.nan))
print("  岩屑・残渣の土層: 平野の中央値 %.2f m(初期 1 m)、裸岩域の中央値 %.3f m(初期 0.001 m)、最大 %.2f m"
      % (np.median(sdf[plain0]), np.median(sdf[rock0]), sdf.max()))


def tower_stats(z, sd):
    out = []
    plain_level = np.median(z[plain0])
    for xc, yc, H, R in HILLS:
        win = np.hypot(X - xc, Y - yc) <= R + 30.0
        top = z[win].max()
        area = ((z > plain_level + 5.0) & win).sum() * dx * dx
        req = np.sqrt(area / np.pi)
        # 側面の最大勾配(窓内の基岩面)
        zb = z - sd
        gy, gx = np.gradient(zb, dx)
        smax = np.hypot(gx, gy)[win].max()
        out.append((top, top - plain_level, req, np.degrees(np.arctan(smax))))
    return plain_level, out


print("== 塔ごとの指標(頂高 / 平野からの比高 / 平野 + 5 m より高い部分の等価半径 / 基岩面の最大勾配角)")
series = []
for t, z, sd in snaps:
    pl, st = tower_stats(z, sd)
    series.append((t, pl, st))
    print("  %6.0f 年: 平野 %.2f m | " % (t, pl) + " | ".join("%.1f/%.1f/%.0f/%.0f°" % s for s in st))

# ---------------------------------------------------------------- 図: maps
fig, axes = plt.subplots(2, 2, figsize=(11, 10))
ax = axes[0, 0]
ax.imshow(hillshade(z0, dx), cmap="gray", extent=ext, origin="lower", vmin=0, vmax=1)
ax.contour(x, y, z0, levels=np.arange(5, 45, 5), colors="tab:blue", linewidths=0.5)
ax.set_title("初期地形(等高線 5 m)")
ax = axes[0, 1]
ax.imshow(hillshade(zf, dx), cmap="gray", extent=ext, origin="lower", vmin=0, vmax=1)
ax.contour(x, y, zf, levels=np.arange(-10, 45, 5), colors="tab:blue", linewidths=0.5)
ax.set_title("最終地形(地形時間 %.0f 年)" % tend)
ax = axes[1, 0]
im = ax.imshow(np.maximum(d, 1e-3), extent=ext, origin="lower", cmap="magma_r",
               norm=LogNorm(vmin=0.1, vmax=max(d.max(), 1.0)))
plt.colorbar(im, ax=ax, label="削剥深 z0 − z (m。対数。負 = 岩屑の堆積は 0 で表示)")
ax.set_title("削剥深(平野 %.1f m、裾はより深い)" % dp)
ax = axes[1, 1]
im = ax.imshow(sdf, extent=ext, origin="lower", cmap="YlOrBr", vmin=0, vmax=max(sdf.max(), 1.0))
plt.colorbar(im, ax=ax, label="土層厚 sd (m)")
ax.set_title("最終の土層厚(岩屑の裾野 + 残渣)")
for ax in axes.flat:
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
plt.tight_layout()
plt.savefig("figs/maps%s.png" % SUFFIX, dpi=130)
plt.close()

# ---------------------------------------------------------------- 図: sections(塔 1)
xc, yc = HILLS[0][0], HILLS[0][1]
ic, jc = int(xc / dx), int(yc / dx)
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
for ax, (lab, getz, getb, coord) in zip(axes, [("x 断面 (y = %.0f m)" % y[jc], lambda z: z[jc, :], lambda z, sd: (z - sd)[jc, :], x),
                                               ("y 断面 (x = %.0f m)" % x[ic], lambda z: z[:, ic], lambda z, sd: (z - sd)[:, ic], y)]):
    for k, (t, z, sd) in enumerate(snaps):
        ax.plot(coord, getz(z), lw=0.9, label="%.0f 年" % t)
    ax.plot(coord, getb(zf, sdf), "k--", lw=0.8, label="最終の基岩面 z − sd")
    ax.set_title(lab + " — 塔 1 の中心を通る")
    ax.set_xlabel("距離 (m)")
    ax.set_ylabel("z (m)")
    ax.set_xlim(xc - 200 if lab.startswith("x") else yc - 200, (xc if lab.startswith("x") else yc) + 200)
    ax.grid(alpha=0.3)
axes[0].legend(fontsize=7, ncol=2)
plt.tight_layout()
plt.savefig("figs/sections%s.png" % SUFFIX, dpi=130)
plt.close()

# ---------------------------------------------------------------- 図: towers
fig, axes = plt.subplots(1, 3, figsize=(14, 3.8))
ts = np.array([s[0] for s in series])
for k, (xc, yc, H, R) in enumerate(HILLS):
    rel = np.array([s[2][k][1] for s in series])
    req = np.array([s[2][k][2] for s in series])
    ang = np.array([s[2][k][3] for s in series])
    lab = "丘 %d (H0 = %.0f m)" % (k + 1, H)
    axes[0].plot(ts, rel, "-o", ms=3, label=lab)
    axes[1].plot(ts, req, "-o", ms=3, label=lab)
    axes[2].plot(ts, ang, "-o", ms=3, label=lab)
axes[0].set_ylabel("平野からの比高 (m)")
axes[1].set_ylabel("平野 + 5 m より高い部分の等価半径 (m)")
axes[2].set_ylabel("基岩面の最大勾配角 (°)")
for ax in axes:
    ax.set_xlabel("地形時間 (年。豪雨 %d 回/年換算)" % STORMS_PER_YR)
    ax.grid(alpha=0.3)
axes[0].legend(fontsize=7)
plt.tight_layout()
plt.savefig("figs/towers%s.png" % SUFFIX, dpi=130)
plt.close()

# ---------------------------------------------------------------- 図: hydrograph
if rows:
    th = np.arange(len(rows), dtype=float)
    ss = np.array([float(r[2]) for r in rows])
    sg = np.array([float(r[3]) for r in rows])
    fig, axes = plt.subplots(1, 2, figsize=(12, 3.8))
    for ax, (t1, t2, lab) in zip(axes, [(0, 72, "最初の 3 日"), (th[-1] - 72, th[-1], "最後の 3 日")]):
        mm = (th >= t1) & (th <= t2)
        ax.plot(th[mm] / 24, ss[mm] * 1000, "b-", label="S_surf(湛水)")
        ax2 = ax.twinx()
        ax2.plot(th[mm] / 24, sg[mm] * 1000, "g-")
        ax.set_xlabel("水理時間 (日)")
        ax.set_ylabel("湛水 (mm、領域平均)", color="b")
        ax2.set_ylabel("地下貯留 (mm、領域平均)", color="g")
        ax.set_title(lab)
        ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig("figs/hydrograph%s.png" % SUFFIX, dpi=130)
    plt.close()
print("figs/maps%s.png, sections, towers, hydrograph written" % SUFFIX)
