#!/usr/bin/env python3
"""examples/badland_storm の機構の模式図と設定の図(計算結果は使わない)。

  python3 plot_setup.py        # figs/mechanism.png, figs/setup.png
  python3 plot_setup.py en     # 英語ラベル版を en/figs/ に描く

  figs/mechanism.png  (a) 豪雨のあとの台地と崖の縦断(濡れたセルでは乾式斜面侵食が止まる)、
                      (b) 1 時間周期の降雨と浸透能(豪雨の超過分だけが表面流)、
                      (c) 剥離深の横方向の拡散 wet_lw(1 セル幅の流路の侵食を幅 ℓ_w に配る)
  figs/setup.png      地形(平面)、平坦な台地と 2 % 傾けた台地の縦断、降雨の時系列(2 周期)

入力は make_terrain.py が書く z_main.txt / sw_main.txt / z_main_tilt.txt(make で作る)。
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

C_GROUND, C_SEA, C_WATER, C_DRY, C_WET = "#c9b48a", "#6fa8dc", "#2c7fb8", "#8c510a", "#1a9850"


def _arrow(ax, x0, y0, x1, y1, color, lw=1.5, style="-|>", ms=9):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw, shrinkA=0, shrinkB=0, mutation_scale=ms))


def _rain(ax, ncyc=1):
    """1 時間周期の降雨(50 分 10 mm/h + 10 分 60 mm/h)と浸透能。"""
    t = []
    p = []
    for k in range(ncyc):
        t += [60 * k, 60 * k + 50, 60 * k + 50, 60 * k + 60]
        p += [10, 10, 60, 60]
    t = np.array(t, float)
    p = np.array(p, float)
    ax.fill_between(t, 0, p, color="#9ecae1", step=None, label=T("降雨強度", "rainfall intensity"))
    ax.fill_between(t, 12, np.maximum(p, 12), where=p > 12, color=C_WATER, alpha=0.8,
                    label=T("超過分 48 mm/h = 表面流", "excess 48 mm/h = surface flow"))
    ax.axhline(12, color="k", lw=1.2, ls="--")
    ax.text(1, 14, T("浸透能 12 mm/h(表面流ありのケース)", "infiltration capacity 12 mm/h (surface-flow cases)"), fontsize=8)
    ax.axhline(100, color="0.4", lw=1.2, ls=":")
    ax.text(1, 102, T("浸透能 100 mm/h(対照: 豪雨も全量しみ込む)", "capacity 100 mm/h (control: even the downpour soaks in)"),
            fontsize=8, color="0.3")
    ax.set_xlim(0, 60 * ncyc)
    ax.set_ylim(0, 115)
    ax.set_xlabel(T("時刻 (分)", "time (min)"))
    ax.set_ylabel("mm/h")
    ax.legend(fontsize=7.5, loc="upper left", bbox_to_anchor=(0.0, 0.84))


def _profile(ax):
    """豪雨のあとの縦断。台地(平坦)には水が残り、崖面は数分で乾く。"""
    x = np.linspace(0, 120, 601)
    z = np.where(x < 60, 30.0, np.maximum(30.0 - 1.5 * (x - 60), 0.0))
    ax.fill_between(x, -5, z, color=C_GROUND)
    ax.fill_between(x, 0, -5, where=x >= 80, color=C_SEA, alpha=0.8)
    ax.plot(x, z, "k-", lw=1.2)
    ax.fill_between(x, z, z + 1.1, where=x < 60, color=C_WATER, alpha=0.75)
    for xi in (8, 22, 36, 50):
        ax.text(xi, 32.0, "≈", ha="center", fontsize=11, color=C_WATER)
    ax.text(30, 35.0, T("台地: 豪雨で水が乗り、次の豪雨まで湿ったまま\n→ 乾式斜面侵食が止まる(h > 1 mm)",
                        "plateau: water stays from one downpour to the next\n→ dry-slope erosion stops (h > 1 mm)"),
            ha="center", fontsize=8, color=C_WATER)
    for xi in (64, 70, 76):
        zi = 30 - 1.5 * (xi - 60)
        ax.add_patch(plt.Circle((xi + 0.9, zi + 1.0), 0.7, color=C_DRY, zorder=4))
        _arrow(ax, xi + 1.7, zi - 0.2, xi + 3.8, zi - 3.4, C_DRY, lw=1.2, ms=8)
    ax.text(79, 21, T("崖面は数分で乾き、乾いた時間に\n乾式斜面侵食が続く", "the cliff face dries within minutes;\ndry-slope erosion goes on while dry"),
            fontsize=8, color=C_DRY)
    _arrow(ax, 55, 29.5, 66, 23.5, C_WATER, lw=2.0)
    ax.text(41, 22.0, T("傾いた台地では水が谷頭へ\n排水され、谷頭が長く湿る", "on a tilted plateau the water drains\nthrough the valley heads, which stay wet"),
            fontsize=8, color=C_WATER, ha="center")
    ax.text(30, 10, T("濡れたセル: 雨滴と面状の侵食(f_wash)+ 浮遊砂(f_suspend)",
                      "wet cells: raindrop and sheet erosion (f_wash) + suspended load (f_suspend)"),
            ha="center", fontsize=8, color=C_WET)
    ax.text(30, 6.5, T("乾いたセル: 乾式斜面侵食(f_splash)。水深 dd = 1 mm で切り替え",
                       "dry cells: dry-slope erosion (f_splash); switched at depth dd = 1 mm"),
            ha="center", fontsize=8, color=C_DRY)
    ax.text(100, -2.6, T("海: 水と土砂は系外へ", "sea: water and sediment leave"), ha="center", fontsize=8)
    ax.set_xlim(0, 120)
    ax.set_ylim(-5, 40)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("z (m)")


def _lw(ax):
    """剥離深の横方向の拡散: 1 セル幅の流路の剥離を、標準偏差 ℓ_w のガウス核で隣接セルへ配る。"""
    y = np.arange(-6, 7)
    e = np.zeros(y.size, float)
    e[y == 0] = 1.0
    ax.bar(y - 0.2, e, width=0.4, color="0.55", label=T("wet_lw = 0: 流れが集まる 1 セルだけ削る",
                                                       "wet_lw = 0: only the one cell where flow gathers"))
    lw = 2.0
    k = np.exp(-0.5 * (y / lw) ** 2)
    k /= k.sum()
    ax.bar(y + 0.2, k, width=0.4, color=C_WET, label=T("wet_lw = 2 m: 幅 ≈ 2 m のリルとして配る(総量は同じ)",
                                                       "wet_lw = 2 m: spread as a rill ≈ 2 m wide (same total)"))
    ax.set_xlabel(T("流路からの距離(セル、Δx = 1 m)", "distance from the flow path (cells, Δx = 1 m)"))
    ax.set_ylabel(T("剥離深(相対)", "detachment depth (relative)"))
    ax.set_ylim(0, 1.25)
    ax.legend(fontsize=7.5, loc="upper right")


def mechanism():
    fig = plt.figure(figsize=(13.5, 9.4))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.25, 1], hspace=0.32, wspace=0.25)
    ax = fig.add_subplot(gs[0, :])
    _profile(ax)
    ax.set_title(T("(a) 豪雨のあと: 濡れたセルでは乾式斜面侵食が止まり、湿潤侵食に切り替わる",
                   "(a) After a downpour: dry-slope erosion stops on wet cells and wet erosion takes over"),
                 loc="left", fontsize=10)
    ax = fig.add_subplot(gs[1, 0])
    _rain(ax)
    ax.set_title(T("(b) 1 時間周期の降雨と浸透能", "(b) Rainfall of a one-hour cycle and the infiltration capacity"),
                 loc="left", fontsize=10)
    ax = fig.add_subplot(gs[1, 1])
    _lw(ax)
    ax.set_title(T("(c) 流路の幅(剥離深の横方向の拡散 wet_lw)", "(c) Width of the flow path (lateral spreading wet_lw)"),
                 loc="left", fontsize=10)
    fig.savefig(f"{FIGDIR}/mechanism.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


def setup():
    z = np.loadtxt("z_main.txt")
    sw = np.loadtxt("sw_main.txt")
    zt = np.loadtxt("z_main_tilt.txt")
    ny, nx = z.shape
    fig = plt.figure(figsize=(14, 6.4))
    gs = fig.add_gridspec(2, 3, width_ratios=[0.8, 1.6, 1.25], height_ratios=[1, 1], wspace=0.35, hspace=0.45)
    ax = fig.add_subplot(gs[:, 0])
    im = ax.imshow(np.where(sw > 0, np.nan, zt), origin="lower", extent=[0, nx, 0, ny], cmap="terrain", vmin=-8, vmax=33)
    ax.imshow(np.where(sw > 0, 1.0, np.nan), origin="lower", extent=[0, nx, 0, ny], cmap="Blues", vmin=0, vmax=1.6)
    ax.text(100, 120, T("海(海域マスク)", "sea (sea mask)"), rotation=90, ha="center", va="center", fontsize=8)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title(T("地形(傾き 2 % の台地)\n120 m × 240 m、Δx = 1 m", "Terrain (plateau tilted 2 %)\n120 m × 240 m, Δx = 1 m"), fontsize=9)
    fig.colorbar(im, ax=ax, shrink=0.6).set_label(T("地盤高 (m)", "elevation (m)"))
    ax = fig.add_subplot(gs[0, 1])
    x = np.arange(nx) + 0.5
    j = ny // 2
    ax.plot(x, z[j], "k-", lw=1.3, label=T("平坦な台地(param_storm / param_dry)", "flat plateau (param_storm / param_dry)"))
    ax.plot(x, zt[j], color="C3", lw=1.3, ls="--",
            label=T("崖へ 2 % 下がる台地(*_tilt・*_wet)", "plateau falling 2 % towards the cliff (*_tilt, *_wet)"))
    ax.axhline(0, color=C_SEA, lw=1.2)
    ax.set_xlim(0, 120)
    ax.set_ylim(-2, 46)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("z (m)")
    ax.legend(fontsize=7.5, loc="upper right")
    ax.set_title(T("縦断(y = 120 m の行)。崖は tanθ = 1.5(56°)で海に落ちる",
                   "Profile (row y = 120 m); the cliff drops into the sea at tanθ = 1.5 (56°)"), fontsize=9)
    ax = fig.add_subplot(gs[1, 1])
    _rain(ax, ncyc=2)
    ax.set_title(T("降雨の時系列(1 時間周期 × 25。2 周期を表示)", "Rainfall series (one-hour cycle × 25; two cycles shown)"), fontsize=9)
    ax = fig.add_subplot(gs[:, 2])
    ax.axis("off")
    rows = [
        (T("降雨", "rain"), T("50 分 10 mm/h + 10 分 60 mm/h\nの 1 時間周期を 25 回", "50 min at 10 mm/h + 10 min at 60 mm/h,\none-hour cycle repeated 25 times")),
        (T("浸透", "infiltration"), T("Green-Ampt、psif = 0 で一定\n12 mm/h(表面流あり)/ 100 mm/h(対照)", "Green-Ampt, constant with psif = 0\n12 mm/h (surface flow) / 100 mm/h (control)")),
        (T("乾式侵食", "dry erosion"), T("f_splash(badland と同じ係数)", "f_splash (same as badland)")),
        (T("湿潤侵食", "wet erosion"), T("f_wash(雨滴 0.001、面状 2e-10 m/s)\n+ f_suspend(0.2 mm、esa 1e-6)\n強い組: 面状 2e-9、esa 1e-4", "f_wash (raindrop 0.001, sheet 2e-10 m/s)\n+ f_suspend (0.2 mm, esa 1e-6)\nstrong set: sheet 2e-9, esa 1e-4")),
        (T("時間", "time"), T("dt 0.5 s、地形更新 2 s × morfac 50\n25 時間 = T_geo 4.5×10⁶ s", "dt 0.5 s, update every 2 s × morfac 50\n25 h = T_geo 4.5×10⁶ s")),
    ]
    yv = 0.97
    for k, v in rows:
        ax.text(0.0, yv, k, fontsize=9, va="top", color="0.2")
        ax.text(0.26, yv, v, fontsize=9, va="top")
        yv -= 0.085 + 0.058 * v.count("\n")
    ax.set_title(T("設定の要約", "Summary of settings"), fontsize=9, loc="left")
    fig.savefig(f"{FIGDIR}/setup.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    mechanism()
    setup()
    print(f"{FIGDIR}/mechanism.png, {FIGDIR}/setup.png written")
