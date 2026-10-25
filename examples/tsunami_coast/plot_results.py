#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# examples/tsunami_coast の図化(result_full / result_inst / result_offshore → figs/)
#   figs/deformation.png : 最終地盤変位と地形(湾の軸 y = 40 km の断面)
#   figs/probes.png      : プローブの水位時系列(3 ケース)
#   figs/snapshots.png   : 時刻歴ありケースの水位分布(t = 2, 5, 10, 20 分)と湾奥の浸水
#   標準出力に数表(到達時刻・最高・最低)
#   python3 plot_results.py en で英語ラベル版を en/figs/ に描く
import os, sys, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
plt.rcParams.update({"font.family": ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"], "font.size": 10})

DX = 0.5                                  # km
NX, NY = 240, 160
CASES = [("result_full", T("時刻歴あり(fn_bedmotion)", "With time history (fn_bedmotion)"), "#eb6834"),
         ("result_inst", T("瞬時変位(従来法)", "Instantaneous displacement (conventional method)"), "#8a8983"),
         ("result_offshore", T("沖の断層だけ(沿岸変動なし)", "Offshore fault only (no coastal deformation)"), "#2a78d6")]
PR = [(1, T("湾の頭 x = 9 km(水深 4 m)", "Bay head x = 9 km (depth 4 m)")),
      (2, T("湾口 x = 20 km", "Bay mouth x = 20 km")),
      (3, T("湾の外の海岸(北)y = 65 km", "Coast outside the bay (north) y = 65 km")),
      (4, T("南の岬の海岸 y = 15 km(隆起域)", "Coast of the southern cape y = 15 km (uplifted area)")),
      (5, T("棚 x = 40 km", "Shelf x = 40 km")),
      (6, T("沖の断層の上 x = 90 km", "Above the offshore fault x = 90 km")),
      (7, T("湾奥の陸 x = 7 km(沈降で浸水)", "Land at the bay head x = 7 km (flooded by subsidence)"))]
x = (np.arange(NX) + 0.5) * DX; y = (NY - np.arange(NY) - 0.5) * DX
os.makedirs(FIGDIR, exist_ok=True)
z0 = np.loadtxt("z.txt"); d = np.loadtxt("bm/disp_0010.txt")
JB = NY - int(40 / DX)                    # y = 40 km の行(0 始まり)

def times(rdir):
    return {int(l.split(",")[0]): float(l.split(",")[2]) for l in open(rdir + "/FILENUMBER.csv") if not l.startswith("#")}
def field(rdir, name, k):
    return np.loadtxt("%s/%s%04d.txt" % (rdir, name, k))
DOFF = {"result_full": np.loadtxt("bm/disp_0010.txt"), "result_inst": np.loadtxt("bm/disp_0010.txt"),
        "result_offshore": np.loadtxt("bm_off/disp_0010.txt")}
PIJ = {1: (19, 80), 2: (40, 80), 3: (43, 30), 4: (43, 130), 5: (81, 80), 6: (181, 80), 7: (15, 80)}   # param の pbxy
def probe(rdir, n):
    a = np.loadtxt("%s/probes/probe%04d.csv" % (rdir, n), delimiter=",", comments="#")
    i, j = PIJ[n]
    return a[:, 0] * 3600, a[:, 2] + a[:, 3], a[:, 3], float(DOFF[rdir][j - 1, i - 1])

# --- 1. 変位と地形 ---
fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(13, 4.8), gridspec_kw={"width_ratios": [1.3, 1]})
im = ax0.imshow(d, extent=[0, 120, 0, 80], origin="upper", cmap="RdBu_r", vmin=-3.5, vmax=3.5)
ax0.contour(x, y, z0, levels=[0], colors="k", linewidths=0.8)
ax0.contour(x, y, z0, levels=[-1000, -200], colors="#52514e", linewidths=0.5, linestyles="--")
for n, _ in PR:
    pass
ax0.set_xlabel("x (km)"); ax0.set_ylabel("y (km)"); ax0.set_title(T("最終地盤変位 (m)。黒 = 海岸線、破線 = 200・1000 m 等深線", "Final ground displacement (m). Black = coastline, dashed = 200 and 1000 m isobaths"), fontsize=10)
plt.colorbar(im, ax=ax0, fraction=0.03)
ax1.plot(x, z0[JB], "k-", lw=1.2, label=T("地盤 z", "Bed z"))
ax1.plot(x, d[JB] * 100, color="#eb6834", lw=1.2, label=T("変位 × 100", "Displacement × 100"))
ax1.axhline(0, color="#8a8983", lw=0.6); ax1.set_xlim(0, 120); ax1.set_ylim(-1100, 400)
ax1.set_xlabel("x (km)"); ax1.set_ylabel("z (m)"); ax1.grid(); ax1.legend(fontsize=8); ax1.set_title(T("湾の軸 y = 40 km の断面", "Profile along the bay axis y = 40 km"), fontsize=10)
plt.tight_layout(); plt.savefig(os.path.join(FIGDIR, "deformation.png"), dpi=100); plt.close()

# --- 2. プローブ ---
fig, axes = plt.subplots(7, 1, figsize=(10, 15), sharex=True)
rows = []
for ax, (n, lab) in zip(axes, PR):
    vals = []
    for rdir, cl, col in CASES:
        t, e, h, doff = probe(rdir, n)
        ax.plot(t / 60, e, color=col, lw=1.1, label=cl)
        # 到達 = 水深の変化 |h(t) − h(0)| が 0.1 m を超える時刻(地盤と一緒に動く分は水深を変えないので、
        #   波・流入だけを拾う。陸のプローブでは浸水開始)
        idx = np.where(np.abs(h - h[0]) > 0.1)[0]
        ta = t[idx[0]] if len(idx) else np.nan
        vals.append((ta, e.max(), e.min(), h.max()))
    ax.axhline(0, color="#8a8983", lw=0.5)
    rows.append((lab, vals))
    ax.set_ylabel(T("水位 (m)", "Water level (m)")); ax.grid(); ax.set_title(lab, fontsize=9, loc="left")
axes[0].legend(fontsize=8); axes[-1].set_xlabel("t (min)")
plt.tight_layout(); plt.savefig(os.path.join(FIGDIR, "probes.png"), dpi=100); plt.close()

# --- 3. 水位分布(時刻歴あり)と湾奥の浸水 ---
tm = times("result_full")
fig, axes = plt.subplots(2, 3, figsize=(15, 9), constrained_layout=True)
for ax, tsel in zip(axes.flat[:5], (120.0, 300.0, 600.0, 1200.0, 1800.0)):
    k = min(tm, key=lambda q: abs(tm[q] - tsel))
    h = field("result_full", "H", k); z = field("result_full", "Z", k)
    eta = np.where(h > 0.01, z + h, np.nan)
    im = ax.imshow(eta, extent=[0, 120, 0, 80], origin="upper", cmap="RdBu_r", vmin=-2, vmax=2)
    ax.contour(x, y, z0, levels=[0], colors="k", linewidths=0.6)
    ax.set_title(T("t = %.0f 分: 水位 (m)", "t = %.0f min: water level (m)") % (tm[k] / 60), fontsize=10); ax.set_xlim(0, 120)
fig.colorbar(im, ax=list(axes.flat[:5]), location="bottom", shrink=0.5, aspect=50, label=T("水位 (m)", "Water level (m)"))
ax = axes.flat[5]
hmax = np.zeros_like(z0)
for k in tm:
    if tm[k] <= 0: continue
    h = field("result_full", "H", k); hmax = np.maximum(hmax, h)
land = z0 > 0
fl = np.where(land & (hmax > 0.01), hmax, np.nan)
im = ax.imshow(fl, extent=[0, 120, 0, 80], origin="upper", cmap="Blues", vmin=0, vmax=3)
ax.contour(x, y, z0, levels=[0], colors="k", linewidths=0.6)
ax.set_xlim(0, 30); ax.set_ylim(25, 55); ax.set_title(T("陸の最大浸水深 (m)。湾の周り(時刻歴あり)", "Maximum flood depth on land (m). Around the bay (with time history)"), fontsize=10)
fig.colorbar(im, ax=ax, shrink=0.8, label=T("最大浸水深 (m)", "Maximum flood depth (m)"))
plt.savefig(os.path.join(FIGDIR, "snapshots.png"), dpi=100); plt.close()

print(T("| プローブ | ", "| Probe | ") + " | ".join(T("%s: 到達 (min) / 最高 / 最低 (m)", "%s: arrival (min) / max / min (m)") % c[1] for c in CASES) + T(" |  (到達 = 水深の変化が 0.1 m を超える時刻)", " |  (arrival = the time at which the change in depth exceeds 0.1 m)"))
print("|---|" + "---:|" * len(CASES))
for lab, vals in rows:
    print("| %s | " % lab + " | ".join("%.1f / %.2f / %.2f" % (v[0] / 60, v[1], v[2]) for v in vals) + " |")
print()
print(T("湾奥の陸(プローブ 7)の最大浸水深 (m): ", "Maximum flood depth on the land at the bay head (probe 7) (m): ") + ", ".join("%s %.2f" % (c[1], v[3]) for c, v in zip(CASES, rows[6][1])))
hm = {}
for rdir, cl, col in CASES:
    tmm = times(rdir); hh = np.zeros_like(z0)
    for k in tmm:
        if tmm[k] <= 0: continue
        hh = np.maximum(hh, field(rdir, "H", k))
    hm[cl] = (hh[land] > 0.01).sum() * DX * DX
print(T("陸の浸水面積 (km²): ", "Flooded land area (km²): ") + ", ".join("%s %.1f" % (k, v) for k, v in hm.items()))
