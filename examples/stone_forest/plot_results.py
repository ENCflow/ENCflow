#!/usr/bin/env python3
"""examples/stone_forest の図化と数表(事前に param.txt を実行しておく)。

  python3 plot_results.py | tee analysis.txt
  python3 plot_results.py en        # 英語ラベル版を en/figs/ に描く

図(figs/):
  maps.png        節理の地図(可溶率)、最終地形の陰影図、最終の基岩面 z − sd、崖錐と土層
  sections.png    y = 中央の x 断面の時間発展(柱と溝)
  stats.png       溝の深さ(台地面と節理セルの差)・柱の数・崖錐の体積の時系列
数表(標準出力): 溶けた岩の検算、溝の深さと柱の数、崩落と崖錐の台帳

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
from matplotlib.colors import LightSource
EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)
PARAM = "param.txt"
YR = 86400.0 * 365.25        # 定常強制: 地形時間 = 水理時間 × morfac


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
    return LightSource(azdeg=315, altdeg=40).hillshade(z, vert_exag=1.0, dx=dx, dy=dx)


def count_regions(mask):
    """4 近傍の連結領域の数(numpy だけで。scipy は使わない)"""
    ny, nx = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    n = 0
    for j in range(ny):
        for i in range(nx):
            if mask[j, i] and not seen[j, i]:
                n += 1
                stack = [(j, i)]
                seen[j, i] = True
                while stack:
                    cj, ci = stack.pop()
                    for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nj, ni = cj + dj, ci + di
                        if 0 <= nj < ny and 0 <= ni < nx and mask[nj, ni] and not seen[nj, ni]:
                            seen[nj, ni] = True
                            stack.append((nj, ni))
    return n


def load(res, n):
    out = {}
    for v in ("Z", "Sd", "Ht"):
        f = os.path.join(res, "%s%04d.txt" % (v, n))
        out[v] = np.loadtxt(f) if os.path.exists(f) else None
    return out


p = read_param(PARAM)
res = p["dir_result"]
dx = float(p["lx"]) / int(p["nx"])
morfac = float(p["morfac"])
fres = float(p.get("dissol_fres", 0.0))
joints = np.loadtxt(p["fn_dissol"])
jmask = joints > 1.0
times = file_times(res)
snaps = []
for n in sorted(times):
    if n >= 9998:
        continue
    d = load(res, n)
    if d["Z"] is not None:
        snaps.append((times[n] * morfac / YR, d))
tend = times[9998] * morfac / YR
dfin = load(res, 9998)
if snaps[-1][0] < tend:
    snaps.append((tend, dfin))
z0 = snaps[0][1]["Z"]
zf, sdf, htf = dfin["Z"], dfin["Sd"], dfin["Ht"]
if htf is None:
    htf = np.zeros_like(zf)
ny, nx = z0.shape
ext = [0, nx * dx, 0, ny * dx]
x = (np.arange(nx) + 0.5) * dx


def stats(d):
    """溝の深さ(非節理セルの中央値 − 節理セルの中央値)、柱の数(基岩面が台地面 − 5 m より高い連結領域)、崖錐の体積"""
    z, sd, ht = d["Z"], d["Sd"], d["Ht"]
    zb = z - sd if sd is not None else z
    plate = np.median(zb[~jmask])
    depth = plate - np.median(zb[jmask])
    npil = count_regions(zb > plate - 5.0)
    vt = (ht.sum() * dx * dx) if ht is not None else 0.0
    return plate, depth, npil, vt


# ---------------------------------------------------------------- 数表
log = open("Screen.log", errors="ignore").read() if os.path.exists("Screen.log") else ""
vled = sum(float(v) for v in re.findall(r"dissolution removed\s*([0-9.Ee+-]+)\s*m3 of rock", log))
vtal = sum(float(v) for v in re.findall(r"removed talus[^=]*=\s*([0-9.Ee+-]+)", log))
vrock = sum(float(v) for v in re.findall(r"rockfall moved\s*([0-9.Ee+-]+)\s*m3", log))
vz = -(zf - z0).sum() * dx * dx
print("== 体積の検算(地形時間 %.0f 年 = 水理時間 × morfac。年平均の定常強制)" % tend)
print("  溶けた岩(台帳)= %.0f m3(うち崖錐 %.0f m3)、崩落で移した岩(台帳。かさ)= %.0f m3、最終の崖錐 = %.0f m3(最大 %.2f m)"
      % (vled, vtal, vrock, htf.sum() * dx * dx, htf.max()))
print("  地表の体積減少 Σ(z0 − z)Δx² = %.0f m3 ≈ 溶食 × (1 − f_res) = %.0f m3" % (vz, vled * (1.0 - fres)))
print("== 溝と柱(基岩面 z − sd で評価)")
series = []
for t, d in snaps:
    plate, depth, npil, vt = stats(d)
    series.append((t, plate, depth, npil, vt))
    print("  %6.0f 年: 台地面 %.2f m、溝の深さ %.2f m、柱(台地面 − 5 m より高い連結領域)%d 個、崖錐 %.0f m3" % (t, plate, depth, npil, vt))
zb = zf - sdf
gy, gx = np.gradient(zb, dx)
print("  最終の基岩面の最大勾配角 %.0f°、節理セルの削剥 中央値 %.2f m / 非節理セル %.2f m(比 %.1f)"
      % (np.degrees(np.arctan(np.hypot(gx, gy).max())), np.median((z0 - zf)[jmask]), np.median((z0 - zf)[~jmask]),
         np.median((z0 - zf)[jmask]) / max(np.median((z0 - zf)[~jmask]), 1e-9)))

# ---------------------------------------------------------------- 図: maps
fig, axes = plt.subplots(2, 2, figsize=(11, 10))
ax = axes[0, 0]
im = ax.imshow(joints, extent=ext, origin="lower", cmap="Greys", vmin=0, vmax=joints.max())
plt.colorbar(im, ax=ax, label=T("可溶率(節理 6、ほか 1)", "soluble fraction (joints 6, else 1)"))
ax.set_title(T("節理の地図(入力)", "Joint map (input)"))
ax = axes[0, 1]
ax.imshow(hillshade(zf, dx), cmap="gray", extent=ext, origin="lower", vmin=0, vmax=1)
ax.contour(x, x, zf, levels=np.arange(0, 35, 2), colors="tab:blue", linewidths=0.4)
ax.set_title(T("最終地形(地形時間 %.0f 年。等高線 2 m)", "Final surface (%.0f yr; contours 2 m)") % tend)
ax = axes[1, 0]
im = ax.imshow(zb, extent=ext, origin="lower", cmap="terrain")
plt.colorbar(im, ax=ax, label=T("基岩面 z − sd (m)", "bedrock surface z − sd (m)"))
ax.set_title(T("最終の基岩面(柱と溝)", "Final bedrock surface (pillars and clefts)"))
ax = axes[1, 1]
im = ax.imshow(sdf, extent=ext, origin="lower", cmap="YlOrBr", vmin=0, vmax=max(sdf.max(), 1.0))
plt.colorbar(im, ax=ax, label=T("土層 + 崖錐 sd (m)", "soil + talus sd (m)"))
ax.set_title(T("最終の土層厚(溝に沈んだ土層・崖錐の残り)", "Final soil thickness (soil sunk into the clefts, remaining talus)"))
for ax in axes.flat:
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
plt.tight_layout()
plt.savefig("%s/maps.png" % FIGDIR, dpi=130)
plt.close()

# ---------------------------------------------------------------- 図: sections
jc = ny // 2 + 1
fig, ax = plt.subplots(figsize=(12, 4))
for t, d in snaps:
    ax.plot(x, d["Z"][jc, :], lw=0.9, label=T("%.0f 年", "%.0f yr") % t)
ax.plot(x, zb[jc, :], "k--", lw=0.8, label=T("最終の基岩面 z − sd", "final bedrock z − sd"))
ax.set_title(T("x 断面(y = %.0f m)の時間発展", "x-section (y = %.0f m) through time") % ((jc + 0.5) * dx))
ax.set_xlabel(T("距離 (m)", "distance (m)"))
ax.set_ylabel("z (m)")
ax.grid(alpha=0.3)
ax.legend(fontsize=7, ncol=4)
plt.tight_layout()
plt.savefig("%s/sections.png" % FIGDIR, dpi=130)
plt.close()

# ---------------------------------------------------------------- 図: stats
ts = np.array([s[0] for s in series]) / 1000.0      # 千年(年のままでは目盛の数字が続いて読めない)
fig, axes = plt.subplots(1, 3, figsize=(14, 3.8))
axes[0].plot(ts, [s[2] for s in series], "-o", ms=3)
axes[0].set_ylabel(T("溝の深さ (m。台地面 − 節理セル)", "cleft depth (m; plateau − joint cells)"))
axes[1].plot(ts, [s[3] for s in series], "-o", ms=3)
axes[1].set_ylabel(T("柱の数(台地面 − 5 m より高い連結領域)", "number of pillars (regions above plateau − 5 m)"))
axes[2].plot(ts, [s[4] for s in series], "-o", ms=3)
axes[2].set_ylabel(T("崖錐の体積 (m³)", "talus volume (m³)"))
for ax in axes:
    ax.set_xlabel(T("地形時間 (千年。定常強制)", "Morphological time (kyr; steady forcing)"))
    ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("%s/stats.png" % FIGDIR, dpi=130)
plt.close()
print("%s/maps.png, sections, stats written" % FIGDIR)
