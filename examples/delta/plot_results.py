#!/usr/bin/env python3
# examples/delta の図化: 堆積厚(Z − Z0000)の時間発展、最終地形・水深・流速・泥割合、
#   デルタ体積と前進距離の時系列。使い方: python3 plot_results.py <case>(base|baseqb|sand|mud|varq|fix|wave)
#   result_<case>/ を読み、fig_<case>_evolution.png・fig_<case>_final.png・fig_<case>_timeseries.png と
#   timeseries_<case>.csv を書く。
import sys, os, csv, glob, re
import numpy as np
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["axes.unicode_minus"] = False
for f in ("IPAPGothic", "Noto Sans CJK JP", "WenQuanYi Zen Hei"):   # 日本語ラベル(無ければ既定フォント)
    try:
        import matplotlib.font_manager as fm
        if any(x.name == f for x in fm.fontManager.ttflist):
            matplotlib.rcParams["font.family"] = f; break
    except Exception:
        pass
import matplotlib.pyplot as plt

case = sys.argv[1] if len(sys.argv) > 1 else "base"
d = "result_%s" % case
pfile = {"base": "param.txt"}.get(case, "param_%s.txt" % case)
ptxt = open(pfile).read()
def pget(key, default):
    m = re.search(r"^\s*%s\s*=\s*([0-9.eE+-]+)" % key, ptxt, re.M)
    return float(m.group(1)) if m else default
DX = pget("lx", 1000.0) / pget("nx", 200.0)
MORFAC = pget("morfac", 100.0)
DT_FILE = pget("dt_file", 3600.0)
LCH = {"base": 150.0, "baseqb": 150.0, "wave": 150.0}.get(case, 200.0)
ZSEA = {"base": -2.0, "baseqb": -2.0, "wave": -2.0}.get(case, -1.5)

frames = []
fn = os.path.join(d, "FILENUMBER.csv")
if os.path.exists(fn):
    for row in csv.reader(open(fn)):
        if row[0].startswith("#"): continue
        n = int(row[0]); t = float(row[2])
        if n < 9000: frames.append((n, t))
if not frames:   # FILENUMBER.csv は終了時に書かれる。途中なら Z ファイルの連番から復元
    frames = [(int(os.path.basename(f)[1:5]), int(os.path.basename(f)[1:5]) * DT_FILE)
              for f in sorted(glob.glob(os.path.join(d, "Z[0-9][0-9][0-9][0-9].txt")))
              if int(os.path.basename(f)[1:5]) < 9000]
z0 = np.loadtxt(os.path.join(d, "Z0000.txt"))
ny, nx = z0.shape
x = (np.arange(nx) + 0.5) * DX; y = (np.arange(ny) + 0.5) * DX
ext = [0, nx * DX, ny * DX, 0]

def load(pfx, n):
    return np.loadtxt(os.path.join(d, "%s%04d.txt" % (pfx, n)))

# --- 堆積厚の時間発展(6 枚)
sel = frames[1:] if len(frames) > 1 else frames
idx = np.linspace(0, len(sel) - 1, min(6, len(sel))).astype(int)
fig, axs = plt.subplots(2, 3, figsize=(15, 6.5), constrained_layout=True)
for ax, k in zip(axs.flat, idx):
    n, t = sel[k]
    dz = load("Z", n) - z0; h = load("H", n)
    im = ax.imshow(dz, extent=ext, cmap="RdBu_r", vmin=-2, vmax=2)
    ax.contour(x, y, h, levels=[0.05], colors="k", linewidths=0.6)
    ax.set_title("地形 %.0f h (水理 %.1f h): Δz (m)" % (t * MORFAC / 3600, t / 3600))
    ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
fig.colorbar(im, ax=axs, shrink=0.8, label="Δz = Z − Z0 (m)")
fig.savefig("fig_%s_evolution.png" % case, dpi=110)

# --- 最終: 標高・水深・流速・細粒分
n, t = frames[-1]
z = load("Z", n); h = load("H", n); v = load("V", n)
sf = load("Sf", n) if os.path.exists(os.path.join(d, "Sf%04d.txt" % n)) else None
fig, axs = plt.subplots(2, 2, figsize=(13, 8), constrained_layout=True)
im = axs[0, 0].imshow(z, extent=ext, cmap="terrain", vmin=ZSEA, vmax=1.5)
axs[0, 0].contour(x, y, h, levels=[0.05], colors="k", linewidths=0.6)
axs[0, 0].set_title("最終地盤高 Z (m)。黒線 = 汀線 (h = 0.05 m)"); fig.colorbar(im, ax=axs[0, 0])
im = axs[0, 1].imshow(h, extent=ext, cmap="Blues", vmin=0, vmax=-ZSEA + 0.2)
axs[0, 1].set_title("最終水深 H (m)"); fig.colorbar(im, ax=axs[0, 1])
im = axs[1, 0].imshow(v, extent=ext, cmap="magma", vmin=0, vmax=1.2)
axs[1, 0].set_title("最終流速 |V| (m/s)"); fig.colorbar(im, ax=axs[1, 0])
if sf is not None:
    dz = z - z0
    frac = np.where(dz > 0.01, sf / np.maximum(dz, 1e-6), np.nan)
    im = axs[1, 1].imshow(np.clip(frac, 0, 1), extent=ext, cmap="YlOrBr", vmin=0, vmax=1)
    axs[1, 1].set_title("堆積物に占める泥(細粒分)の割合 Sf/Δz"); fig.colorbar(im, ax=axs[1, 1])
for ax in axs.flat:
    ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
fig.savefig("fig_%s_final.png" % case, dpi=110)

# --- 時系列: デルタ体積(堆積 bulk)、陸地の最大前進、陸化面積、浅瀬の面積
rows = []
for n, t in frames:
    dz = load("Z", n) - z0; h = load("H", n)
    dep = dz[dz > 0].sum() * DX * DX
    land = (h < 0.05) & (x[None, :] > LCH)
    xmax = (x[None, :] * land).max() if land.any() else LCH
    shallow = (h < 0.5) & (x[None, :] > LCH + 50.0)
    rows.append((t * MORFAC / 3600, dep, xmax - LCH, land.sum() * DX * DX, shallow.sum() * DX * DX))
rows = np.array(rows)
np.savetxt("timeseries_%s.csv" % case, rows, delimiter=",",
           header="morph_time_h,deposit_bulk_m3,land_advance_m,land_area_m2,shallow_area_m2(h<0.5)", comments="", fmt="%.3f")
fig, axs = plt.subplots(1, 3, figsize=(14, 4), constrained_layout=True)
axs[0].plot(rows[:, 0], rows[:, 1] / 1e3, "o-"); axs[0].set_ylabel("堆積体積 (10³ m³ bulk)")
axs[1].plot(rows[:, 0], rows[:, 2], "o-"); axs[1].set_ylabel("河口からの陸地の最大前進 (m)")
axs[2].plot(rows[:, 0], rows[:, 3] / 1e3, "o-", label="陸化 (h<0.05)"); axs[2].plot(rows[:, 0], rows[:, 4] / 1e3, "s-", label="浅瀬 (h<0.5)")
axs[2].set_ylabel("面積 (10³ m²)"); axs[2].legend()
for ax in axs: ax.set_xlabel("地形時間 (h)"); ax.grid(alpha=0.3)
fig.savefig("fig_%s_timeseries.png" % case, dpi=110)
print("final: morph %.0f h, deposit %.0f m3, land advance %.0f m, land area %.0f m2" % (rows[-1, 0], rows[-1, 1], rows[-1, 2], rows[-1, 3]))
