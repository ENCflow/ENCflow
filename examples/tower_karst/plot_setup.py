#!/usr/bin/env python3
"""examples/tower_karst の機構の模式図と設定の図(計算結果は使わない)。

  python3 plot_setup.py        # figs/mechanism.png, figs/setup.png
  python3 plot_setup.py en     # 英語ラベル版を en/figs/ に描く

  figs/mechanism.png  (a) 裸岩の塔と土層に覆われた平野の断面(どこで水がしみ込み、どこが溶けるか)、
                      (b) 平野が下がって塔の比高が増し、裾が堀・ノッチ・崩落で切られていく様子
  figs/setup.png      初期地形(平面と塔 1 を通る横断)、土層厚と浸透能、1 日の降雨、設定の要約

入力は make_terrain.py が書く z.txt / sd.txt / ksv.txt(make で作る)。
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

C_ROCK, C_SOIL, C_WATER, C_DISS, C_TALUS = "#d6d2c4", "#a0522d", "#2c7fb8", "#c0392b", "#8f8f8f"
HILLS = [(300.0, 300.0, 40.0, 90.0), (700.0, 320.0, 40.0, 90.0), (320.0, 720.0, 40.0, 90.0),
         (690.0, 700.0, 40.0, 90.0), (500.0, 520.0, 20.0, 60.0), (150.0, 850.0, 20.0, 60.0)]


def _arrow(ax, x0, y0, x1, y1, color, lw=1.5, style="-|>", ms=9):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw, shrinkA=0, shrinkB=0, mutation_scale=ms))


def _tower(x, H=40.0, R=90.0, xc=0.0, plain=0.0):
    r = np.abs(x - xc)
    return plain + np.where(r < R, H * np.clip(1.0 - (r / R) ** 2, 0, None) ** 1.5, 0.0)


def _section(ax):
    """塔と平野の断面: 塔の雨は裾へ流れ下り、平野と裾で浸透して溶かす。"""
    x = np.linspace(-200, 200, 801)
    z = _tower(x)
    ax.fill_between(x, -14, z, color=C_ROCK)
    plain = np.abs(x) >= 85
    ax.fill_between(x, z - 1.6, z, where=plain, color=C_SOIL, alpha=0.85)
    ax.plot(x, z, "k-", lw=1.1)
    for xi in np.arange(-195, 200, 22):
        _arrow(ax, xi, 52, xi - 3, 46.5, C_WATER, lw=1.0, ms=7)
    ax.text(-195, 53.5, T("代表豪雨 40 mm/h × 1 時間(1 日周期)", "representative storm 40 mm/h × 1 h (daily)"), fontsize=8.5, color=C_WATER)
    # 塔: 裸岩、浸透能 1 mm/h → 雨は表面流として裾へ
    for sgn in (-1, 1):
        _arrow(ax, sgn * 30, 36, sgn * 70, 12, C_WATER, lw=1.8)
    ax.text(0, 26, T("裸岩の塔: 浸透能 1 mm/h\n雨はほぼ全量が表面流で裾へ\n岩面は流出水の 0.3 倍だけ溶ける",
                     "bare-rock tower: capacity 1 mm/h\nalmost all rain runs off to the foot\nthe rock face dissolves with 0.3 × runoff"),
            ha="center", fontsize=8)
    # 平野: 土層 1 m、40 mm/h で浸透し、攻撃性の高い水が溶かす
    for xi in (-170, -140, 140, 170):
        _arrow(ax, xi, 0.5, xi, -5.0, C_WATER, lw=1.3, ms=8)
    ax.text(-195, -8.5, T("平野: 土層 1 m・浸透能 40 mm/h\nしみ込んだ水(土壌 CO₂)が溶かす",
                          "plain: soil 1 m, capacity 40 mm/h\ninfiltrating water (soil CO₂) dissolves"),
            fontsize=8, color=C_DISS)
    # 裾: 集水して深く溶ける(堀)、湛水が壁を溶かす(ノッチ)、崩落
    for sgn in (-1, 1):
        xs = sgn * 92
        ax.fill_between([xs - 6, xs + 6], [-3.5, -3.5], [0.3, 0.3], color=C_WATER, alpha=0.75)
        _arrow(ax, xs, -1.0, xs, -9.0, C_DISS, lw=1.6)
        _arrow(ax, xs - sgn * 2, -1.0, xs - sgn * 9, -1.0, C_DISS, lw=1.4)
    ax.text(105, -11.5, T("裾: 塔の水が集まって深く溶ける(堀・穴)\n湛水が岩壁を溶かす(ノッチ)",
                          "foot: tower water gathers and\ndissolves deeply (moat, holes);\nponded water dissolves the wall (notch)"),
            fontsize=8, color=C_DISS)
    ax.add_patch(plt.Polygon([(-80, 9.0), (-96, 0.3), (-86, 0.3)], color=C_TALUS))
    ax.text(-128, 14, T("露出した壁が H_c = 10 m を\n超えると崩れて崖錐に", "walls exposed above H_c = 10 m\ncollapse into talus"), fontsize=8)
    ax.set_xlim(-200, 200)
    ax.set_ylim(-14, 57)
    ax.set_xticks([])
    ax.set_yticks([])


def _evolution(ax):
    """平野が下がり、塔の比高が増す(fenglin)。"""
    x = np.linspace(-200, 200, 801)
    z0 = _tower(x)
    z1 = _tower(x, plain=-8.0) + np.where(np.abs(x) < 90, 8.0 - 1.6 * (1 - (np.abs(x) / 90.0)) - 6.4 * (np.abs(x) / 90.0) ** 6, 0.0)
    z1 = np.where((np.abs(x) > 84) & (np.abs(x) < 100), z1 - 5.0 * np.exp(-((np.abs(x) - 92) / 4.0) ** 2), z1)
    ax.fill_between(x, -16, z1, color=C_ROCK)
    ax.plot(x, z0, color="0.4", lw=1.0, ls="--", label=T("初めの地形", "initial terrain"))
    ax.plot(x, z1, "k-", lw=1.2, label=T("後の地形(模式)", "later terrain (schematic)"))
    _arrow(ax, 160, 0.0, 160, -7.5, C_DISS, lw=1.6)
    ax.text(150, -2.5, T("平野は速く下がる", "the plain lowers fast"), fontsize=8, color=C_DISS, ha="right")
    _arrow(ax, 0, 41.5, 0, 40.2, C_DISS, lw=1.2, ms=6)
    ax.text(5, 43.5, T("塔の頂は遅く下がる(平野の 1/3〜1/4)", "the top lowers slowly (1/3 to 1/4 of the plain)"), fontsize=8, color=C_DISS)
    ax.annotate("", xy=(-150, 40), xytext=(-150, -8.0), arrowprops=dict(arrowstyle="<->", color="k", lw=1.0))
    ax.text(-145, 15, T("比高が増す\n(平野に残る塔 = fenglin)", "relative height grows\n(towers on a plain = fenglin)"), fontsize=8)
    ax.legend(fontsize=7.5, loc="upper right")
    ax.set_xlim(-200, 200)
    ax.set_ylim(-16, 48)
    ax.set_xticks([])
    ax.set_yticks([])


def mechanism():
    fig = plt.figure(figsize=(13.5, 9.6))
    gs = fig.add_gridspec(2, 1, height_ratios=[1.2, 0.9], hspace=0.2)
    ax = fig.add_subplot(gs[0])
    _section(ax)
    ax.set_title(T("(a) 塔と平野の断面(模式。縦は誇張): 雨がどこでしみ込み、どこが溶けるか",
                   "(a) Section of a tower and the plain (schematic, vertical exaggeration): where rain soaks in and what dissolves"),
                 loc="left", fontsize=10)
    ax = fig.add_subplot(gs[1])
    _evolution(ax)
    ax.set_title(T("(b) 平野が下がって塔の比高が増し、裾は堀・ノッチ・崩落で切られていく",
                   "(b) The plain lowers, the towers grow in relative height, and their feet are cut by moats, notches and collapse"),
                 loc="left", fontsize=10)
    fig.savefig(f"{FIGDIR}/mechanism.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


def setup():
    z = np.loadtxt("z.txt")
    sd = np.loadtxt("sd.txt")
    ksv = np.loadtxt("ksv.txt")
    ny, nx = z.shape
    dx = 10.0
    ext = [0, nx * dx, 0, ny * dx]
    fig = plt.figure(figsize=(14, 6.8))
    gs = fig.add_gridspec(2, 3, width_ratios=[1.15, 1.25, 1.05], height_ratios=[1, 1], wspace=0.32, hspace=0.5)
    ax = fig.add_subplot(gs[:, 0])
    im = ax.imshow(z, origin="lower", extent=ext, cmap="terrain", vmin=-8, vmax=42)
    ax.contour((np.arange(nx) + 0.5) * dx, (np.arange(ny) + 0.5) * dx, ksv, levels=[20.0], colors="k", linewidths=0.8)
    for k, (xc, yc, H, R) in enumerate(HILLS):
        ax.text(xc, yc, "%d" % (k + 1), ha="center", va="center", fontsize=9, fontweight="bold")
    ax.axhline(305, color="k", lw=0.6, ls="--")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title(T("初期地形と塔の番号\n(黒線の内側 = 裸岩)", "Initial terrain and tower numbers\n(inside the black line = bare rock)"),
                 fontsize=9)
    fig.colorbar(im, ax=ax, shrink=0.6).set_label(T("地盤高 (m)", "elevation (m)"))
    ax = fig.add_subplot(gs[0, 1])
    x = (np.arange(nx) + 0.5) * dx
    j = 30
    ax.fill_between(x, -3, z[j], color=C_ROCK)
    ax.fill_between(x, z[j] - sd[j], z[j], color=C_SOIL, alpha=0.9)
    ax.plot(x, z[j], "k-", lw=1.1)
    ax.set_xlim(0, 1000)
    ax.set_ylim(-3, 44)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("z (m)")
    ax.set_title(T("塔 1・2 を通る横断(y = 305 m)\n茶 = 土層(平野 1 m、裸岩 0.001 m)",
                   "Section through towers 1 and 2 (y = 305 m)\nbrown = soil (plain 1 m, bare rock 0.001 m)"), fontsize=9)
    ax = fig.add_subplot(gs[1, 1])
    t = np.array([0, 1, 1, 24])
    p = np.array([40, 40, 0, 0])
    ax.fill_between(t, 0, p, color="#9ecae1", label=T("降雨 40 mm/h × 1 時間", "rain 40 mm/h × 1 h"))
    ax.axhline(40, color="C1", ls="--", lw=1.2)
    ax.text(4, 41.5, T("平野の浸透能 40 mm/h(全量しみ込む)", "plain capacity 40 mm/h (all soaks in)"), fontsize=8, color="C1")
    ax.axhline(1, color="k", ls="--", lw=1.2)
    ax.text(4, 2.5, T("裸岩の浸透能 1 mm/h(ほぼ全量が表面流)", "bare-rock capacity 1 mm/h (almost all runs off)"), fontsize=8)
    ax.set_xlim(0, 24)
    ax.set_ylim(0, 52)
    ax.set_xlabel(T("時刻 (h)。1 日周期で 60 日繰り返す", "time (h); the day repeats for 60 days"))
    ax.set_ylabel("mm/h")
    ax.legend(fontsize=7.5, loc="upper right")
    ax.set_title(T("1 日の降雨と浸透能", "Rain of one day and infiltration capacities"), fontsize=9)
    ax = fig.add_subplot(gs[:, 2])
    ax.axis("off")
    rows = [
        (T("領域", "domain"), T("1000 × 1000 m、Δx = 10 m、四周は壁", "1000 × 1000 m, Δx = 10 m, closed walls")),
        (T("塔", "towers"), T("1〜4: 高さ 40 m・半径 90 m\n5・6: 高さ 20 m・半径 60 m(釣鐘形)", "1–4: 40 m high, radius 90 m\n5, 6: 20 m high, radius 60 m (bell-shaped)")),
        (T("土層・浸透", "soil"), T("平野 1 m・40 mm/h、裸岩 0.001 m・1 mm/h\n土層の水は管路層へ 20 mm/h で抜ける\n(吸込穴なし)", "plain 1 m, 40 mm/h; bare rock 0.001 m, 1 mm/h\nsoil water drains to the conduit layer\nat 20 mm/h (no sinks)")),
        (T("溶食", "dissolution"), T("c_eq 300 mg/L(k_d = 1.2×10⁻⁴)\n浸透量 + 裸岩の流出水 × 0.3\n残渣率 0.1、側方溶食(自動配分)", "c_eq 300 mg/L (k_d = 1.2×10⁻⁴)\ninfiltration + 0.3 × runoff on bare rock\nresidue 0.1, lateral dissolution (auto)")),
        (T("崩落", "collapse"), T("H_c = 10 m、窓 10 m、崖錐 35°\n基岩も崩す(rf_bedrock = 1)", "H_c = 10 m, window 10 m, talus 35°\nbedrock collapses (rf_bedrock = 1)")),
        (T("時間", "time"), T("dt 2 s、地形更新 10 分 × morfac 5×10³\n1 日 = 5000 豪雨 = 100 年(年 50 回)\n60 日 = 地形時間 6000 年", "dt 2 s, update every 10 min × morfac 5×10³\n1 day = 5000 storms = 100 years (50 a year)\n60 days = landform time 6000 years")),
    ]
    yv = 0.97
    for k, v in rows:
        ax.text(0.0, yv, k, fontsize=9, va="top", color="0.2")
        ax.text(0.29, yv, v, fontsize=9, va="top")
        yv -= 0.08 + 0.055 * v.count("\n")
    ax.set_title(T("設定の要約", "Summary of settings"), fontsize=9, loc="left")
    fig.savefig(f"{FIGDIR}/setup.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    mechanism()
    setup()
    print(f"{FIGDIR}/mechanism.png, {FIGDIR}/setup.png written")
