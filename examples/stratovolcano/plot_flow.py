#!/usr/bin/env python3
"""examples/stratovolcano の最後の段(run_flow.py)の図を描き、数値を表示する(事前に python3 run_flow.py)。

  python3 plot_flow.py        # 引数 en で英語版を en/figs/ に

- figs/flow.png      : 3 本(山頂・山頂から東へ 300 m・山頂で 4 倍の噴出率)の固まった溶岩の厚さ
- figs/flow_temp.png : 山頂の火口の 1 本の溶岩の温度の時間変化と、3 本の先端の距離・
                       溶けている溶岩の量の時間変化
"""
import csv
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource, ListedColormap

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)

# run_flow.py と対で保守する定数
CASE = "P"
NX = NY = 100
DX = 50.0
DZ_FOOT = 0.05
RNAME = {"S": T("山頂の火口\n50 m³/s × 6 時間", "vent at the summit\n50 m³/s × 6 h"),
         "E": T("山頂から東へ 300 m の火口\n50 m³/s × 6 時間", "vent 300 m east of the summit\n50 m³/s × 6 h"),
         "S4": T("山頂の火口・同じ体積を 4 倍の噴出率で\n200 m³/s × 1.5 時間",
                 "vent at the summit, same volume at 4× the rate\n200 m³/s × 1.5 h")}
RCOL = {"S": "C0", "E": "C2", "S4": "C3"}
RUNS = ["S", "E", "S4"]

top = f"result_{CASE}"
fn = os.path.join(top, "flow.csv")
if not os.path.exists(fn):
    sys.exit(f"{fn} not found (run python3 run_flow.py first)")
led = {r["run"]: r for r in csv.DictReader(open(fn))}
z0 = np.loadtxt(os.path.join(top, "data", "z_10.txt"))
x = (np.arange(NX) + 0.5) * DX
KM = [x[0] / 1000 - DX / 2000, x[-1] / 1000 + DX / 2000]
W = [1.25, 3.75]                                  # 拡大する範囲 (km)
ls = LightSource(azdeg=315, altdeg=45)
shade = ls.hillshade(z0, vert_exag=2, dx=DX, dy=DX)


def base(ax, ylabel=True):
    ax.imshow(shade, cmap="gray", vmin=-0.6, vmax=1.25, origin="upper", extent=[KM[0], KM[1], KM[0], KM[1]])
    # 配列の先頭行が北端なので、行の座標は北から南へ減らす(陰影の imshow origin="upper" と合わせる)
    ax.contour(x / 1000, x[::-1] / 1000, z0, levels=np.arange(10, z0.max(), 10), colors="k",
               linewidths=0.35, alpha=0.55)
    ax.set_xlim(W); ax.set_ylim(W)
    ax.set_xlabel("km")
    if ylabel:
        ax.set_ylabel("km")
    else:
        ax.tick_params(labelleft=False)


def vent(ax, r):
    i, j = int(led[r]["vent_i"]), int(led[r]["vent_j"])
    ax.plot((i - 0.5) * DX / 1000, (NY - j + 0.5) * DX / 1000, marker="^", ms=9, mfc="cyan", mec="k", zorder=5)
    return i, j


def frames(r):
    """1 時間ごとの (時刻 h, 溶岩の厚さ Hl, 地盤高の変化 dz, 温度 Tl)"""
    res = os.path.join(top, f"flow_{r}")
    out = []
    for k in range(1, 100):
        f = os.path.join(res, f"Hl{k:04d}.txt")
        if not os.path.exists(f):
            break
        out.append((k, np.loadtxt(f), np.loadtxt(os.path.join(res, f"Z{k:04d}.txt")) - z0,
                    np.loadtxt(os.path.join(res, f"Tl{k:04d}.txt"))))
    return out


def ycoord(j):
    return (NY - j + 0.5) * DX / 1000


# ---------------------------------------------------------------- flow.png
fig, axes = plt.subplots(1, 3, figsize=(15, 5.6), constrained_layout=True)
print(T("温度を考慮した 1 回の溶岩流(到達距離、面積、最大の厚さ、固まり終えた時刻)",
        "One lava flow with temperature (reach, area, maximum thickness, time when all has solidified)"))
for m, r in enumerate(RUNS):
    ax = axes[m]
    base(ax, ylabel=(m == 0))
    dz = np.loadtxt(os.path.join(top, f"flow_{r}", "Z9998.txt")) - z0
    im = ax.imshow(np.ma.masked_less(dz, DZ_FOOT), cmap="inferno_r", vmin=0, vmax=20, alpha=0.9,
                   origin="upper", extent=[KM[0], KM[1], KM[0], KM[1]], zorder=3)
    vent(ax, r)
    L = led[r]
    ax.set_title("(" + "abc"[m] + ") " + RNAME[r], fontsize=10)
    ax.text(0.02, 0.02, T(f"到達 {float(L['reach_m']) / 1000:.2f} km、最大の厚さ {float(L['max_thick_m']):.0f} m\n"
                          f"面積 {float(L['area_km2']):.2f} km²、{float(L['solid_by_h']):.0f} 時間後までに全量が固化",
                          f"reach {float(L['reach_m']) / 1000:.2f} km, max thickness {float(L['max_thick_m']):.0f} m\n"
                          f"area {float(L['area_km2']):.2f} km², all solid by {float(L['solid_by_h']):.0f} h"),
            transform=ax.transAxes, fontsize=9, va="bottom", bbox=dict(fc="white", ec="none", alpha=0.85), zorder=6)
    print(f"  {r}: reach {float(L['reach_m']):.0f} m, area {float(L['area_km2']):.3f} km2, "
          f"max {float(L['max_thick_m']):.1f} m, solid by {float(L['solid_by_h']):.0f} h, "
          f"radiated/convected heat {float(L['heat_radiated_J']) / float(L['heat_erupted_J']):.1%}"
          f"/{float(L['heat_convected_J']) / float(L['heat_erupted_J']):.1%} of erupted")
fig.colorbar(im, ax=axes, shrink=0.8, pad=0.02, label=T("固まった溶岩の厚さ (m)", "thickness of the solidified lava (m)"))
fig.suptitle(T("主ケース P の最終地形(等高線 10 m)に、温度を考慮した 1 回の溶岩流(体積 108 万 m³。▲ 火口)",
               "One lava flow with temperature on the final terrain of case P (contours 10 m; volume 1.08 million m³; ▲ vent)"),
             fontsize=11)
fig.savefig(f"{FIGDIR}/flow.png", dpi=110)
plt.close(fig)

# ---------------------------------------------------------------- flow_temp.png
fr = {r: frames(r) for r in RUNS}
fig = plt.figure(figsize=(15, 9.0), constrained_layout=True)
gs = fig.add_gridspec(2, 4, height_ratios=[1.0, 0.85])
SNAP = [1, 3, 6, 9]
r = "S"
for m, k in enumerate(SNAP):
    ax = fig.add_subplot(gs[0, m])
    base(ax, ylabel=(m == 0))
    kk, hl, dz, tl = fr[r][k - 1]
    solid = np.ma.masked_where(~((dz > DZ_FOOT) & (hl <= 0.0)), np.ones_like(dz))
    ax.imshow(solid, cmap=ListedColormap(["0.3"]), alpha=0.85, origin="upper",
              extent=[KM[0], KM[1], KM[0], KM[1]], zorder=3)
    im = ax.imshow(np.ma.masked_where(hl <= 0.0, tl), cmap="plasma", vmin=950, vmax=1100,
                   origin="upper", extent=[KM[0], KM[1], KM[0], KM[1]], zorder=4)
    vent(ax, r)
    ax.set_title("(" + "abcd"[m] + ") " + T(f"{k} 時間後", f"after {k} h"), fontsize=10)
cb = fig.colorbar(im, ax=fig.axes[:4], shrink=0.9, pad=0.01,
                  label=T("溶けている溶岩の温度 (°C)", "temperature of molten lava (°C)"))
# 先端の距離と溶けている溶岩の量の時間変化
ax1 = fig.add_subplot(gs[1, 0:2])
ax2 = fig.add_subplot(gs[1, 2:4])
for r in RUNS:
    i, j = int(led[r]["vent_i"]), int(led[r]["vent_j"])
    hours = float(led[r]["hours"])
    erupted = float(led[r]["erupted_m3"])
    tt, reach, molten = [0.0], [0.0], [0.0]
    for k, hl, dz, tl in fr[r]:
        foot = (dz + hl) > DZ_FOOT
        fj, fi = np.nonzero(foot)
        reach.append(float(np.hypot((fi + 1 - i) * DX, (fj + 1 - j) * DX).max()) if fi.size else 0.0)
        molten.append(hl.sum() * DX * DX / erupted * 100.0)
        tt.append(float(k))
    lab = RNAME[r].replace("\n", T("、", ", "))
    if not EN:                       # 本文の「溶けている溶岩の量は噴出が終わる頃に最も多く」の値
        km = int(np.argmax(molten))
        print(f"  {r}: molten lava max {molten[km]:.0f}% of erupted at {tt[km]:.0f} h")
    ax1.plot(tt, np.array(reach) / 1000, "-o", ms=3, color=RCOL[r], label=lab)
    ax2.plot(tt, molten, "-o", ms=3, color=RCOL[r], label=lab)
    ax1.axvline(hours, color=RCOL[r], lw=0.8, ls=":")
    ax2.axvline(hours, color=RCOL[r], lw=0.8, ls=":")
ax1.set_xlabel(T("噴火の開始からの時間 (時間)", "time since the start of the eruption (h)"))
ax1.set_ylabel(T("火口から先端までの距離 (km)", "distance from the vent to the front (km)"))
ax1.set_title(T("(e) 流れの先端の距離(点線は噴出の終わり)", "(e) distance of the flow front (dotted: end of effusion)"), fontsize=10)
ax1.set_xlim(0, 15); ax1.grid(alpha=0.3); ax1.legend(fontsize=8.5, loc="lower right")
ax2.set_xlabel(T("噴火の開始からの時間 (時間)", "time since the start of the eruption (h)"))
ax2.set_ylabel(T("溶けている溶岩 (噴出量の %)", "molten lava (% of the erupted volume)"))
ax2.set_title(T("(f) まだ固まっていない溶岩の量", "(f) amount of lava not yet solidified"), fontsize=10)
ax2.set_xlim(0, 15); ax2.grid(alpha=0.3)
fig.suptitle(T("(a)〜(d) 山頂の火口(50 m³/s × 6 時間)の溶けている溶岩の温度(灰色は固まった溶岩。▲ 火口)、"
                 "(e)(f) 3 本の時間変化",
                 "(a)-(d) temperature of the molten lava from the vent at the summit (50 m³/s × 6 h; grey = solidified, "
                 "▲ vent), (e)(f) time series of the three flows"), fontsize=11)
fig.savefig(f"{FIGDIR}/flow_temp.png", dpi=110)
plt.close(fig)
print(T(f"図を {FIGDIR}/flow.png・flow_temp.png に書いた", f"figures written to {FIGDIR}/flow.png and flow_temp.png"))
