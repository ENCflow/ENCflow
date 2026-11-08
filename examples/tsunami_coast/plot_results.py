#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# examples/tsunami_coast の結果の図(result_full / result_inst / result_offshore → figs/)
#   figs/probes.png      : プローブの水位時系列(3 ケース。到達時刻の印と、波の成り立ちの注記)
#   figs/snapshots.png   : 時刻歴ありケースの水位分布(t = 2, 5, 10, 20, 30 分)と湾の周りの陸の最大浸水深
#   標準出力に数表(到達時刻・最高・最低、湾奥の陸の最大浸水深、陸の浸水面積)
#   入力だけから描く図(構成・地盤変位・仕組み)は plot_schematic.py
#   python3 plot_results.py en で英語ラベル版を en/figs/ に描く
import os, sys, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


here = os.path.dirname(os.path.abspath(__file__))
os.chdir(here)
FIGDIR = "en/figs" if EN else "figs"
plt.rcParams.update({"font.family": ["DejaVu Sans"] if EN else ["IPAPGothic", "IPAGothic", "DejaVu Sans"], "font.size": 10,
                     "axes.unicode_minus": False})

DX = 0.5                                  # km
NX, NY = 240, 160
CASES = [("result_full", T("時刻歴あり(fn_bedmotion)", "With time history (fn_bedmotion)"), "#eb6834"),
         ("result_inst", T("瞬時変位(従来法)", "Instantaneous displacement (conventional method)"), "#8a8983"),
         ("result_offshore", T("沖の断層だけ(沿岸変動なし)", "Offshore fault only (no coastal deformation)"), "#2a78d6")]
PR = [(1, T("1 湾の頭 x = 9 km(水深 4 m)", "1 Bay head x = 9 km (depth 4 m)")),
      (2, T("2 湾口 x = 20 km", "2 Bay mouth x = 20 km")),
      (3, T("3 湾の外の海岸(北)y = 65 km", "3 Coast outside the bay (north) y = 65 km")),
      (4, T("4 南の岬の海岸 y = 15 km(隆起域)", "4 Coast of the southern cape y = 15 km (uplifted area)")),
      (5, T("5 棚 x = 40 km", "5 Shelf x = 40 km")),
      (6, T("6 沖の断層の上 x = 90 km", "6 Above the offshore fault x = 90 km")),
      (7, T("7 湾奥の陸 x = 7 km(沈降で浸水。浸水する前の線は地盤高)", "7 Land at the bay head x = 7 km (flooded by subsidence; before flooding the line is the ground height)"))]
x = (np.arange(NX) + 0.5) * DX; y = (NY - np.arange(NY) - 0.5) * DX
os.makedirs(FIGDIR, exist_ok=True)
z0 = np.loadtxt("z.txt")


def times(rdir):
    return {int(l.split(",")[0]): float(l.split(",")[2]) for l in open(rdir + "/FILENUMBER.csv") if not l.startswith("#")}


def field(rdir, name, k):
    return np.loadtxt("%s/%s%04d.txt" % (rdir, name, k))


def probe(rdir, n):
    a = np.loadtxt("%s/probes/probe%04d.csv" % (rdir, n), delimiter=",", comments="#")
    return a[:, 0] * 3600, a[:, 2] + a[:, 3], a[:, 3]


def style(ax):
    ax.grid(color="#eceae6", lw=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


# --- 1. プローブ ---
fig, axes = plt.subplots(7, 1, figsize=(10.5, 16.5), sharex=True)
rows = []
for ax, (n, lab) in zip(axes, PR):
    vals = []
    for rdir, cl, col in CASES:
        t, e, h = probe(rdir, n)
        ax.plot(t / 60, e, color=col, lw=1.2, label=cl)
        # 到達 = 水深の変化 |h(t) − h(0)| が 0.1 m を超える時刻(地盤と一緒に動く分は水深を変えないので、
        #   波・流入だけを拾う。陸のプローブでは浸水開始)
        idx = np.where(np.abs(h - h[0]) > 0.1)[0]
        ta = t[idx[0]] if len(idx) else np.nan
        vals.append((ta, e.max(), e.min(), h.max()))
    lo, hi = ax.get_ylim()
    for (rdir, cl, col), v in zip(CASES, vals):
        if np.isfinite(v[0]):
            ax.plot([v[0] / 60], [lo + 0.04 * (hi - lo)], marker="^", color=col, ms=7, clip_on=False, zorder=6)
    ax.set_ylim(lo, hi)
    ax.axhline(0, color="#8a8983", lw=0.5)
    rows.append((lab, vals))
    ax.set_ylabel(T("水位 (m)", "water level (m)"), fontsize=9)
    style(ax)
    ax.set_title(lab, fontsize=9.5, loc="left")
ax = axes[1]
ax.annotate(T("① 沿岸の変動による波(棚の外側の隆起から来る。\n沖の断層だけのケースにはない)", "① wave from the coastal\ndeformation (outer-shelf uplift;\nabsent in the offshore-only case)"),
            xy=(15.9, 1.32), xytext=(1.5, 2.6), fontsize=8.3, color="#b04a1f", arrowprops=dict(arrowstyle="-", color="#b04a1f", lw=0.7))
ax.annotate(T("② 沖の断層の津波", "② tsunami from the offshore fault"), xy=(23.9, 3.78), xytext=(28, 3.2), fontsize=8.3, color="#1f1f1f",
            arrowprops=dict(arrowstyle="-", color="#8a8983", lw=0.7))
ax = axes[0]
ax.annotate(T("湾の底が沈降し、水面も −0.6 m", "the bay floor subsides and the surface drops 0.6 m"), xy=(2, -0.6), xytext=(4, 1.6), fontsize=8.3,
            color="#b04a1f", arrowprops=dict(arrowstyle="-", color="#b04a1f", lw=0.7))
ax = axes[3]
ax.annotate(T("岬の隆起で水面も上がり、すぐ波になる", "the cape uplift raises the surface,\nwhich at once becomes a wave"), xy=(0.3, 0.7),
            xytext=(2.0, 2.0), fontsize=8.3, color="#b04a1f", arrowprops=dict(arrowstyle="-", color="#b04a1f", lw=0.7))
ax = axes[6]
ax.annotate(T("地盤が海面下に(0.38 → −0.18 m)", "the ground sinks below sea level (0.38 → −0.18 m)"), xy=(3, -0.18), xytext=(4, 1.0), fontsize=8.3,
            color="#b04a1f", arrowprops=dict(arrowstyle="-", color="#b04a1f", lw=0.7))
ax.annotate(T("浸水の始まり(▲)", "start of flooding (▲)"), xy=(27.5, 0.3), xytext=(14, 2.0), fontsize=8.3, color="#1f1f1f",
            arrowprops=dict(arrowstyle="-", color="#8a8983", lw=0.7))
axes[0].legend(fontsize=8.5, loc="upper left", frameon=False)
axes[-1].set_xlabel(T("時刻 t (分)", "time t (min)"))
axes[-1].set_xlim(-1, 61)
fig.text(0.99, 0.004, T("▲ = 到達(水深の変化が 0.1 m を超える時刻。陸では浸水の始まり)", "▲ = arrival (the time at which the change in depth exceeds 0.1 m; on land, the start of flooding)"),
         fontsize=8.5, color="#6f6f6f", ha="right")
fig.suptitle(T("プローブの水位(z + h)の時系列: 3 ケース", "Water level (z + h) at the probes: three cases"), fontsize=12.5, y=0.997)
plt.tight_layout(rect=(0, 0.01, 1, 0.99))
plt.savefig(os.path.join(FIGDIR, "probes.png"), dpi=110)
plt.close()

# --- 2. 水位分布(時刻歴あり)と湾奥の浸水 ---
tm = times("result_full")
fig, axes = plt.subplots(2, 3, figsize=(15, 9.2), constrained_layout=True)
notes = {120.0: [(T("湾: 地盤と\nともに\n約 −0.6 m", "bay:\n−0.6 m with\nthe ground"), 14, 40, "#103a6b"),
                 (T("棚の外側〜斜面の\n隆起(断層 1)", "uplift of the outer\nshelf and slope (fault 1)"), 52, 62, "#6b1d10"),
                 (T("沖の隆起\n(断層 2)", "offshore uplift\n(fault 2)"), 96, 52, "white")],
         1200.0: [(T("沖の断層の津波が\n棚を渡って海岸へ", "the offshore tsunami crosses\nthe shelf to the coast"), T(46, 58), 70, "#1f1f1f")]}
for ax, tsel in zip(axes.flat[:5], (120.0, 300.0, 600.0, 1200.0, 1800.0)):
    k = min(tm, key=lambda q: abs(tm[q] - tsel))
    h = field("result_full", "H", k); z = field("result_full", "Z", k)
    eta = np.where(h > 0.01, z + h, np.nan)
    im = ax.imshow(eta, extent=[0, 120, 0, 80], origin="upper", cmap="RdBu_r", vmin=-2, vmax=2)
    ax.contour(x, y, z0, levels=[0], colors="k", linewidths=0.6)
    ax.set_title(T("t = %.0f 分: 水位 (m)", "t = %.0f min: water level (m)") % (tm[k] / 60), fontsize=10)
    ax.set_xlim(0, 120)
    ax.set_xlabel("x (km)", fontsize=9)
    ax.set_ylabel("y (km)", fontsize=9)
    ax.tick_params(labelsize=8.5)
    for txt, tx, ty, col in notes.get(tsel, []):
        ax.text(tx, ty, txt, fontsize=8.2, color=col, ha="center", va="center", linespacing=1.15)
fig.colorbar(im, ax=list(axes.flat[:5]), location="bottom", shrink=0.5, aspect=50, label=T("水位 (m)", "water level (m)"))
ax = axes.flat[5]
hmax = np.zeros_like(z0)
for k in tm:
    if tm[k] <= 0:
        continue
    h = field("result_full", "H", k); hmax = np.maximum(hmax, h)
land = z0 > 0
fl = np.where(land & (hmax > 0.01), hmax, np.nan)
im = ax.imshow(fl, extent=[0, 120, 0, 80], origin="upper", cmap="Blues", vmin=0, vmax=3)
ax.contour(x, y, z0, levels=[0], colors="k", linewidths=0.6)
ax.plot([7.25], [40.25], "o", ms=5, mfc="white", mec="k")
ax.text(6.6, 41.2, "7", fontsize=9, ha="right")
ax.set_xlim(0, 30); ax.set_ylim(25, 55)
ax.set_xlabel("x (km)", fontsize=9)
ax.set_ylabel("y (km)", fontsize=9)
ax.tick_params(labelsize=8.5)
ax.set_title(T("陸の最大浸水深 (m)。湾の周り(時刻歴あり)", "Maximum flood depth on land (m). Around the bay (with time history)"), fontsize=10)
fig.colorbar(im, ax=ax, shrink=0.8, label=T("最大浸水深 (m)", "maximum flood depth (m)"))
fig.suptitle(T("時刻歴ありのケースの水位の分布(黒線 = 動く前の海岸線)と、湾の周りの陸の最大浸水深",
               "Water level in the case with time history (black = coastline before the motion), and the maximum flood depth on land around the bay"),
             fontsize=12)
plt.savefig(os.path.join(FIGDIR, "snapshots.png"), dpi=100)
plt.close()

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
        if tmm[k] <= 0:
            continue
        hh = np.maximum(hh, field(rdir, "H", k))
    hm[cl] = (hh[land] > 0.01).sum() * DX * DX
print(T("陸の浸水面積 (km²): ", "Flooded land area (km²): ") + ", ".join("%s %.1f" % (k, v) for k, v in hm.items()))
