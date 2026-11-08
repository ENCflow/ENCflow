#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# examples/tsunami_fault の結果の図(result_h / result_inst / result_nh を読んで figs/ に保存)
#   figs/profiles.png    : 中央の行(y = 75.5 km)の水面の時間発展(静水圧 / 瞬時 / 非静水圧 + 加速度項)
#   figs/probes.png      : プローブの水位の時系列(最高の時刻の印つき)
#   標準出力に数表(README 用。最高 (m) / 最高の時刻 (s) / 最低 (m))
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

DX, J = 1.0, 74                       # km、中央の行(0 始まり。y = 75.5 km)
CASES = [("result_h", T("静水圧(30 s 立ち上がり)", "Hydrostatic (30 s rise)"), "#2a78d6"),
         ("result_inst", T("静水圧(瞬時変位)", "Hydrostatic (instantaneous)"), "#8a8983"),
         ("result_nh", T("非静水圧 + 加速度項", "Non-hydrostatic + acceleration term"), "#eb6834")]
x = (np.arange(200) + 0.5) * DX
os.makedirs(FIGDIR, exist_ok=True)


def times(rdir):
    return {int(l.split(",")[0]): float(l.split(",")[2]) for l in open(rdir + "/FILENUMBER.csv") if not l.startswith("#")}


def surf(rdir, k):
    e = np.loadtxt("%s/E%04d.txt" % (rdir, k)); z = np.loadtxt("%s/Z%04d.txt" % (rdir, k))
    return np.where(e - z > 0.01, e, np.nan)


def probe(rdir, n):
    d = np.loadtxt("%s/probes/probe%04d.csv" % (rdir, n), delimiter=",", comments="#")
    return d[:, 0] * 3600, d[:, 2] + d[:, 3]


def style(ax):
    ax.grid(color="#eceae6", lw=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


# --- 1. 中央の行の水面 ---
fig, axes = plt.subplots(2, 2, figsize=(13, 8.0))
notes = {120.0: [(T("盛り上がりが西(海岸)と東へ\n2 つに分かれて進む", "the hump splits into two waves\nheading west (coast) and east"), 6, 0.42, "left")],
         300.0: [(T("← 西へ", "← west"), 66, 0.6, "center"), (T("東へ →", "east →"), 174, 0.6, "center")],
         600.0: [(T("非静水圧は先頭波が 2 割低く、\n後ろにうねりが続く(分散)", "non-hydrostatic: the leading wave is\n20 % lower and trailed by undulations\n(dispersion)"), 52, 0.62, "left")],
         1200.0: [(T("海岸で遡上", "run-up at the coast"), 14, 1.8, "left")]}
for ax, tsel in zip(axes.flat, (120.0, 300.0, 600.0, 1200.0)):
    for rdir, lab, col in CASES:
        tm = times(rdir); k = min(tm, key=lambda q: abs(tm[q] - tsel))
        ax.plot(x, surf(rdir, k)[J], color=col, lw=1.3, label=lab)
    ax.axvspan(120, 149, color="#f6dccc", alpha=0.55, lw=0, zorder=0)
    ax.set_title(T("t = %.0f s(%.0f 分)", "t = %.0f s (%.0f min)") % (tsel, tsel / 60), fontsize=10, loc="left")
    style(ax)
    ax.set_xlabel("x (km)")
    ax.set_ylabel(T("水位 (m)", "water level (m)"))
    ax.set_xlim(0, 200)
    for txt, tx, ty, ha in notes.get(tsel, []):
        ax.text(tx, ty, txt, fontsize=8.5, color="#1f1f1f", ha=ha, va="center")
axes.flat[0].text(134.5, -0.38, T("断層の\n投影", "fault\nprojection"), fontsize=8, color="#b0624a", ha="center")
axes.flat[0].legend(fontsize=8.5, loc="upper left", frameon=False)
fig.suptitle(T("中央の行(y = 75.5 km)の水面(薄い橙 = 断層面を地表へ投影した範囲 x = 120〜149 km)",
               "Water surface along the central row (y = 75.5 km; light orange = surface projection of the fault, x = 120–149 km)"),
             fontsize=12)
plt.tight_layout(rect=(0, 0, 1, 0.97))
plt.savefig(os.path.join(FIGDIR, "profiles.png"), dpi=110)
plt.close()

# --- 2. プローブ ---
PR = [(1, T("1 上端の真上 x = 120.5 km(水深 2000 m)", "1 Directly above the upper edge x = 120.5 km (depth 2000 m)")),
      (2, T("2 斜面の下端 x = 60.5 km", "2 Foot of the slope x = 60.5 km")),
      (3, T("3 沿岸 x = 10.5 km(水深 268 m)", "3 Coast x = 10.5 km (depth 268 m)")),
      (4, T("4 東 x = 180.5 km", "4 East x = 180.5 km")),
      (5, T("5 南 y = 30.5 km(断層の端の外)", "5 South y = 30.5 km (beyond the end of the fault)"))]
fig, axes = plt.subplots(5, 1, figsize=(10.5, 12.5), sharex=True)
rows = []
for ax, (n, lab) in zip(axes, PR):
    vals = []
    for rdir, cl, col in CASES:
        t, e = probe(rdir, n)
        ax.plot(t / 60, e, color=col, lw=1.2, label=cl)
        i = int(np.argmax(e))
        vals.append((e.max(), t[i], e.min()))
        ax.plot([t[i] / 60], [e[i]], marker="v", color=col, ms=6, zorder=5)
    rows.append((lab, vals))
    ax.axhline(0, color="#8a8983", lw=0.5)
    ax.set_ylabel(T("水位 (m)", "water level (m)"), fontsize=9)
    style(ax)
    ax.set_title(lab, fontsize=9.5, loc="left")
axes[0].annotate(T("瞬時変位は水面が地盤と一緒に一度に 2.0 m 上がる。\n30 s の立ち上がりでは、その間に波が出ていき 1.77 m",
                   "instantaneous: the surface jumps 2.0 m with the ground;\nwith the 30 s rise, waves leave meanwhile: 1.77 m"),
                 xy=(0.12, 2.0), xytext=(2.5, 1.2), fontsize=8.3, color="#1f1f1f", arrowprops=dict(arrowstyle="-", color="#8a8983", lw=0.7))
axes[2].annotate(T("非静水圧は 24 % 低い(分散で先頭波が低くなる)", "non-hydrostatic is 24 % lower (dispersion lowers the leading wave)"),
                 xy=(16.5, 0.92), xytext=(19, 1.05), fontsize=8.3, color="#b04a1f", arrowprops=dict(arrowstyle="-", color="#b04a1f", lw=0.7))
axes[0].legend(fontsize=8.5, loc="upper right", frameon=False)
axes[-1].set_xlabel(T("時刻 t (分)", "time t (min)"))
fig.text(0.99, 0.004, T("▼ = 各ケースで水位が最高になる時刻(数表の「最高の時刻」)", "▼ = time of the maximum level in each case (\"time of max\" in the table)"),
         fontsize=8.5, color="#6f6f6f", ha="right")
fig.suptitle(T("プローブの水位(z + h)の時系列: 3 ケース", "Water level (z + h) at the probes: three cases"), fontsize=12.5, y=0.997)
plt.tight_layout(rect=(0, 0.012, 1, 0.99))
plt.savefig(os.path.join(FIGDIR, "probes.png"), dpi=110)
plt.close()

print(T("| プローブ | ", "| Probe | ") + " | ".join(T("%s 最高 (m) / 最高の時刻 (s) / 最低 (m)", "%s max (m) / time of max (s) / min (m)") % c[1] for c in CASES) + " |")
print("|---|" + "---:|" * len(CASES))
for lab, vals in rows:
    print("| %s | " % lab + " | ".join("%.3f / %.0f / %.3f" % v for v in vals) + " |")
