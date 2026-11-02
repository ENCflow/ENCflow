#!/usr/bin/env python3
"""examples/karst の機構の模式図と設定の図(計算結果は使わない)。

  python3 plot_setup.py        # figs/mechanism.png, figs/setup.png
  python3 plot_setup.py en     # 英語ラベル版を en/figs/ に描く

  figs/mechanism.png  (a) 石灰岩台地の断面: 浸透水の面的な溶食と、窪みの吸込穴に集まる水の
                      集中した溶食、(b) 窪みが深まる正のフィードバック、(c) 壁の側方溶食と崩落
  figs/setup.png      初期地形(平面と横断)、可溶率(縁の不溶の尾根)、1 日の降雨と浸透能、設定の要約

入力は make_terrain.py が書く z.txt / sol.txt(make で作る)。
依存: numpy, matplotlib
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)

C_ROCK, C_SOIL, C_WATER, C_COND, C_DISS = "#d6d2c4", "#a0522d", "#2c7fb8", "#6a51a3", "#c0392b"


def _arrow(ax, x0, y0, x1, y1, color, lw=1.5, style="-|>", ms=9):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw, shrinkA=0, shrinkB=0, mutation_scale=ms))


def _section(ax):
    """石灰岩台地の断面(模式。縦は誇張)。"""
    x = np.linspace(0, 100, 801)
    z = 10 + 1.2 * np.sin(2 * np.pi * x / 45.0) - 6.0 * np.exp(-((x - 62) / 4.0) ** 2)
    ax.fill_between(x, -8, z, color=C_ROCK)
    ax.fill_between(x, z - 0.6, z, color=C_SOIL, alpha=0.85)
    ax.plot(x, z, "k-", lw=1.1)
    # 窪みの湛水
    eta = 8.4
    ax.fill_between(x, z, eta, where=(z < eta) & (x > 50) & (x < 75), color=C_WATER, alpha=0.75)
    # 吸込穴と管路層
    ax.add_patch(plt.Rectangle((61.4, -6.5), 1.2, z.min() + 6.5, color=C_COND, alpha=0.6))
    ax.add_patch(plt.Rectangle((0, -8), 100, 1.5, color=C_COND, alpha=0.35))
    ax.text(2, -7.5, T("管路連続体層(洞窟・亀裂網。地下へ消えた水の受け皿)", "conduit continuum layer (caves, fractures; receives the water that disappears)"),
            fontsize=8, color="w")
    _arrow(ax, 62, z.min() - 0.3, 62, -5.6, C_COND, lw=2.0)
    ax.text(63.6, 0.0, T("吸込穴(ponor)\n堰の式 ∝ h^1.5", "sink (ponor)\nweir law ∝ h^1.5"), fontsize=8, color=C_COND)
    # 雨
    for xi in np.arange(3, 100, 6.5):
        _arrow(ax, xi, 17.5, xi - 0.6, 14.6, C_WATER, lw=1.0, ms=7)
    ax.text(2, 18.2, T("代表豪雨 40 mm/h × 1 時間(1 日周期で繰り返す)", "representative storm 40 mm/h × 1 h (repeated daily)"),
            fontsize=8.5, color=C_WATER)
    # 浸透 → 面的溶食
    for xi in (10, 22, 34):
        zi = np.interp(xi, x, z)
        _arrow(ax, xi, zi + 0.2, xi, zi - 2.2, C_WATER, lw=1.3, ms=8)
    ax.text(4, 3.4, T("1/4 は浸透(10 mm/h)し、\n土壌 CO₂ を取り込んで\n石灰岩を面的に溶かす", "1/4 infiltrates (10 mm/h),\ntakes up soil CO₂ and\ndissolves the rock diffusely"),
            fontsize=8, color=C_DISS)
    # 表面流 → 窪み
    _arrow(ax, 42, 11.0, 55, 9.2, C_WATER, lw=1.8)
    _arrow(ax, 84, 11.0, 70, 9.2, C_WATER, lw=1.8)
    ax.text(38, 12.6, T("3/4 は表面流になり窪みへ集まる", "3/4 runs off into the depressions"), fontsize=8, color=C_WATER)
    ax.text(72, 3.0, T("吸込穴へ落ちる水も溶かす\n→ 窪みの底が集中して溶ける", "the water entering the sink also dissolves\n→ the depression floor dissolves fast"),
            fontsize=8, color=C_DISS)
    ax.text(80, 12.6, T("土層(残渣 1 割が残る)", "soil (10 % residue stays)"), fontsize=8, color=C_SOIL)
    ax.set_xlim(0, 100)
    ax.set_ylim(-8, 20)
    ax.set_xticks([])
    ax.set_yticks([])


def _loop(ax):
    """窪みが深まる正のフィードバック。"""
    items = [T("窪みが深い", "deeper\ndepression"), T("湛水が深い", "deeper\nponding"),
             T("吸込穴への流入\n∝ h^1.5 が多い", "more inflow\nto the sink ∝ h^1.5"), T("底が速く溶ける", "floor dissolves\nfaster")]
    ang = np.radians([90, 0, -90, 180])
    for a, t in zip(ang, items):
        ax.text(np.cos(a), np.sin(a), t, ha="center", va="center", fontsize=8.5,
                bbox=dict(boxstyle="round", fc="w", ec="0.4"))
    for d0, d1 in ((68, 22), (-22, -68), (-112, -158), (158, 112)):
        a0, a1 = np.radians(d0), np.radians(d1)
        _arrow(ax, 1.05 * np.cos(a0), 1.05 * np.sin(a0), 1.05 * np.cos(a1), 1.05 * np.sin(a1), C_DISS, lw=1.4)
    ax.text(0, 0, T("正の\nフィードバック", "positive\nfeedback"), ha="center", va="center", fontsize=9, color=C_DISS)
    ax.set_xlim(-1.7, 1.7)
    ax.set_ylim(-1.45, 1.45)
    ax.set_aspect("equal")
    ax.axis("off")


def _wall(ax):
    """壁の側方溶食と崩落(補足)。"""
    x = np.linspace(0, 30, 301)
    z = np.where(np.abs(x - 15) < 2.5, 2.0, 10.0)
    z = np.where((np.abs(x - 15) >= 2.5) & (np.abs(x - 15) < 4.0), 10.0 - 8.0 * (4.0 - np.abs(x - 15)) / 1.5, z)
    ax.fill_between(x, -1, z, color=C_ROCK)
    ax.plot(x, z, "k-", lw=1.1)
    ax.fill_between(x, z, 6.0, where=z < 6.0, color=C_WATER, alpha=0.75)
    for xs in (11.5, 18.5):
        _arrow(ax, 15 + (xs - 15) * 0.6, 4.5, xs, 4.5, C_DISS, lw=1.6)
    ax.text(15, -0.6, T("湛水の溶解能を濡れた壁にも配る\n(dissol_lat = −1: 濡れ面の面積比)", "dissolving power of the pond also goes\nto wetted walls (dissol_lat = −1)"),
            ha="center", va="top", fontsize=8, color=C_DISS)
    ax.add_patch(plt.Polygon([(19.0, 10), (21.5, 10), (19.0, 6.5)], color="0.55"))
    _arrow(ax, 21.0, 11.5, 18.0, 7.0, "0.3", lw=1.2)
    ax.text(22, 11.0, T("露出した壁が H_c を\n超えると崩れて崖錐に", "exposed walls above H_c\ncollapse into talus"), fontsize=8)
    ax.set_xlim(0, 30)
    ax.set_ylim(-4.5, 13.5)
    ax.axis("off")


def mechanism():
    fig = plt.figure(figsize=(13.5, 9.6))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.25, 1], hspace=0.25, wspace=0.12)
    ax = fig.add_subplot(gs[0, :])
    _section(ax)
    ax.set_title(T("(a) 石灰岩台地の断面(模式。縦は誇張): 面的な溶食と、吸込穴に集まる水の集中した溶食",
                   "(a) Section of a limestone plateau (schematic, vertical exaggeration): diffuse dissolution and dissolution concentrated at sinks"),
                 loc="left", fontsize=10)
    ax = fig.add_subplot(gs[1, 0])
    _loop(ax)
    ax.set_title(T("(b) 集水の大きい窪みほど速く深まる", "(b) Depressions with larger catchments deepen faster"), loc="left", fontsize=10)
    ax = fig.add_subplot(gs[1, 1])
    _wall(ax)
    ax.set_title(T("(c) 補足: 壁の側方溶食と崩落", "(c) Supplements: lateral dissolution of walls and collapse"), loc="left", fontsize=10)
    fig.savefig(f"{FIGDIR}/mechanism.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


def _hillshade(z, dx):
    gy, gx = np.gradient(z, dx)
    az, alt = np.radians(315.0), np.radians(45.0)
    slope = np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gx, gy)
    return np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect)


def setup():
    z = np.loadtxt("z.txt")
    sol = np.loadtxt("sol.txt")
    ny, nx = z.shape
    dx = 10.0
    ext = [0, nx * dx, 0, ny * dx]
    fig = plt.figure(figsize=(14, 6.8))
    gs = fig.add_gridspec(2, 3, width_ratios=[1.15, 1.2, 1.05], height_ratios=[1, 1], wspace=0.32, hspace=0.5)
    ax = fig.add_subplot(gs[:, 0])
    ax.imshow(_hillshade(20.0 * z, dx), origin="lower", extent=ext, cmap="gray", vmin=-0.2, vmax=1.0)
    cs = ax.contour((np.arange(nx) + 0.5) * dx, (np.arange(ny) + 0.5) * dx, z, levels=np.arange(297, 303, 1.0),
                    colors="C0", linewidths=0.6)
    ax.contour((np.arange(nx) + 0.5) * dx, (np.arange(ny) + 0.5) * dx, sol, levels=[0.5], colors="C3", linewidths=1.2)
    ax.axhline(500, color="k", lw=0.6, ls="--")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title(T("初期地形(陰影は高さ 20 倍、等高線 1 m)\n赤線の外側は不溶の低い尾根(可溶率 0、+3 m)",
                   "Initial terrain (shading ×20 in height, contours 1 m)\noutside the red line: low insoluble rim (solubility 0, +3 m)"),
                 fontsize=9)
    ax = fig.add_subplot(gs[0, 1])
    x = (np.arange(nx) + 0.5) * dx
    ax.plot(x, z[50], "k-", lw=1.2)
    ax.fill_between(x, 295, z[50], color=C_ROCK)
    ax.set_xlim(0, 1000)
    ax.set_ylim(295, 304.5)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("z (m)")
    ax.set_title(T("横断(y = 500 m)\n標高 300 m の台地に標準偏差 1 m・相関長 ≈ 30 m の起伏",
                   "Section (y = 500 m)\nundulation of 1 m std, ≈ 30 m correlation on a plateau at 300 m"), fontsize=9)
    ax = fig.add_subplot(gs[1, 1])
    t = np.array([0, 60, 60, 1440]) / 60.0
    p = np.array([40, 40, 0, 0])
    ax.fill_between(t, 0, p, color="#9ecae1", label=T("降雨", "rain"))
    ax.fill_between([0, 1], 10, 40, color=C_WATER, alpha=0.8, label=T("浸透能を超える 30 mm/h → 表面流", "30 mm/h above capacity → runoff"))
    ax.axhline(10, color="k", ls="--", lw=1.2)
    ax.text(4, 12, T("浸透能 10 mm/h(Green-Ampt)", "infiltration capacity 10 mm/h (Green-Ampt)"), fontsize=8)
    ax.set_xlim(0, 24)
    ax.set_ylim(0, 50)
    ax.set_xlabel(T("時刻 (h)。1 日周期で 60 日繰り返す", "time (h); the day repeats for 60 days"))
    ax.set_ylabel("mm/h")
    ax.legend(fontsize=7.5, loc="upper right")
    ax.set_title(T("1 日の降雨(代表豪雨 1 回)", "Rain of one day (one representative storm)"), fontsize=9)
    ax = fig.add_subplot(gs[:, 2])
    ax.axis("off")
    rows = [
        (T("領域", "domain"), T("1000 × 1000 m、Δx = 10 m、四周は壁\n(内陸排水)", "1000 × 1000 m, Δx = 10 m, closed walls\n(internal drainage)")),
        (T("土層", "soil"), T("0.5 m(比産出率 0.2)。管路層へ 10 mm/h で抜ける", "0.5 m (specific yield 0.2); drains to the\nconduit layer at 10 mm/h")),
        (T("吸込穴", "sinks"), T("1×10⁻⁴ 個/m²(1 ha に 1 個)、堰係数 2.66", "1×10⁻⁴ per m² (one per ha), weir coefficient 2.66")),
        (T("溶食", "dissolution"), T("c_eq 100 mg/L、ρ_r 2500 kg/m³\n(k_d = 4×10⁻⁵)、残渣率 0.1\n浸透量 + 吸込穴への流入", "c_eq 100 mg/L, ρ_r 2500 kg/m³\n(k_d = 4×10⁻⁵), residue 0.1\ninfiltration + inflow to sinks")),
        (T("時間", "time"), T("dt 2 s、地形更新 10 分 × morfac 1000\n1 日 = 1000 豪雨 = 25 年(年 40 回)\n60 日 = 地形時間 1500 年", "dt 2 s, update every 10 min × morfac 1000\n1 day = 1000 storms = 25 years (40 per year)\n60 days = landform time 1500 years")),
    ]
    yv = 0.97
    for k, v in rows:
        ax.text(0.0, yv, k, fontsize=9, va="top", color="0.2")
        ax.text(0.3, yv, v, fontsize=9, va="top")
        yv -= 0.09 + 0.058 * v.count("\n")
    ax.set_title(T("設定の要約", "Summary of settings"), fontsize=9, loc="left")
    fig.savefig(f"{FIGDIR}/setup.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    mechanism()
    setup()
    print(f"{FIGDIR}/mechanism.png, {FIGDIR}/setup.png written")
