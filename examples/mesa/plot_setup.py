#!/usr/bin/env python3
"""examples/mesa の機構の模式図と設定の図(計算結果は使わない)。

  python3 plot_setup.py        # figs/mechanism.png, figs/setup.png
  python3 plot_setup.py en     # 英語ラベル版を en/figs/ に描く

  figs/mechanism.png  (a) メサの崖の後退(帽岩・軟層の掘り込み・崩落・崖錐)、
                      (b) 台地 → メサ → ビュート → 尖塔、(c) 崩落の 4 つの規則
  figs/setup.png      初期地形(平面)、2 つの台地の中心を通る横断、層理の柱状図、設定の要約

入力は make_terrain.py が書く z.txt(make で作る)。
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

C_CAP, C_SOFT, C_HARD, C_TALUS, C_ERODE = "#8c6d46", "#e3cfa6", "#b39a6e", "#9e9e9e", "#c0392b"


def _arrow(ax, x0, y0, x1, y1, color, lw=1.5, style="-|>", ms=9):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw, shrinkA=0, shrinkB=0, mutation_scale=ms))


def _mesa(ax):
    """メサの縁の断面: 帽岩が平らな頂を守り、軟層が削れて掘り込まれ、帽岩が崩れて崖錐が脚部を覆う。"""
    ax.add_patch(plt.Polygon([(0, 0), (46, 0), (38, 6), (32, 12), (29.6, 15.6), (29.0, 17), (0, 17)], color=C_SOFT))
    ax.add_patch(plt.Polygon([(0, 17), (30.6, 17), (30.6, 20), (0, 20)], color=C_CAP))
    ax.add_patch(plt.Polygon([(32, 12), (33.6, 12), (50.7, 0), (46, 0), (38, 6)], color=C_TALUS, alpha=0.9))
    ax.add_patch(plt.Rectangle((33.2, 16.4), 1.6, 1.3, angle=-25, color=C_CAP))
    _arrow(ax, 34.4, 15.8, 35.6, 13.2, "0.3", lw=1.4)
    ax.text(12, 18.4, T("帽岩(硬い。倍率 0.05)", "cap rock (hard; factor 0.05)"), fontsize=8.5, color="w")
    ax.text(8, 8, T("軟らかい層(倍率 1)", "soft layer (factor 1)"), fontsize=8.5)
    ax.text(44.0, 3.0, T("崖錐", "talus"), fontsize=8.5)
    _arrow(ax, 24.5, 13.0, 29.2, 16.0, C_ERODE, lw=1.6)
    ax.text(10.5, 12.2, T("軟層が速く削れて\n帽岩の下が掘り込まれる", "the soft layer erodes faster\nand undercuts the cap"),
            fontsize=8, color=C_ERODE)
    ax.text(36.5, 16.6, T("支えを失った帽岩が\n崩れ落ちる(崩落)", "the unsupported cap\ncollapses (rockfall)"), fontsize=8)
    ax.text(50.5, 8.0, T("岩屑は崖錐になり、\n脚部の軟層を覆って守る", "the debris forms talus that\ncovers and protects the soft foot"),
            fontsize=8, color="0.3")
    _arrow(ax, 26, 22.5, 18, 22.5, "k", lw=1.2)
    ax.text(14.5, 23.3, T("縁は急なまま後退(平行後退)", "the edge retreats while staying steep (parallel retreat)"), fontsize=8)
    ax.set_xlim(0, 68)
    ax.set_ylim(-1, 25)
    ax.axis("off")


def _sequence(ax):
    """台地 → メサ → ビュート → 尖塔(横断の模式)。"""
    x0 = 0.0
    for w, lab in ((26, T("台地", "plateau")), (14, T("メサ\n(幅 > 高さ)", "mesa\n(wider than tall)")),
                   (6, T("ビュート\n(幅 < 高さ)", "butte\n(narrower than tall)")), (1.6, T("尖塔", "pinnacle"))):
        xc = x0 + max(w, 6) / 2 + 3
        top = 10.0 if w > 2 else 8.0
        ax.add_patch(plt.Polygon([(xc - w / 2 - 4, 0), (xc - w / 2, 7.5), (xc - w / 2, top), (xc + w / 2, top),
                                  (xc + w / 2, 7.5), (xc + w / 2 + 4, 0)], color=C_SOFT, ec="k", lw=0.8))
        if w > 2:
            ax.add_patch(plt.Rectangle((xc - w / 2, 8.6), w, 1.4, color=C_CAP))
        ax.text(xc, -1.0, lab, ha="center", va="top", fontsize=8)
        x0 = xc + max(w, 6) / 2 + 5
        if w > 2:
            _arrow(ax, x0 - 3.6, 5, x0 - 1.4, 5, "k", lw=1.0)
    ax.set_xlim(-1, x0 + 1)
    ax.set_ylim(-5, 12)
    ax.axis("off")


def _rule(ax, kind):
    """崩落の規則の模式(1 列ずつの柱で描く)。"""
    if kind == "step":
        h = [10, 10, 10, 4, 3, 2.5]
        title = T("段差の規則:\n隣のセルとの段差 > H_c", "step rule:\ndrop to the neighbour\n> H_c")
    elif kind == "window":
        h = [10, 10, 9.0, 7.5, 5.5, 3.0, 1.0]
        title = T("窓版:\n窓の中の最低点との落差 > H_c", "window rule: drop to\nthe lowest point in\nthe window > H_c")
    elif kind == "face":
        h = [10, 10, 10, 2.2, 1.6, 1.0]
        title = T("支え方式:\n脚部が崖錐に覆われた面は削れない", "support: a face whose\nfoot is buried in talus\nis not eroded")
    else:
        h = [10, 10, 10, 3.0, 2.0, 1.2]
        title = T("張り出し:\n軟らかい脚部が u_c 削れると柱が落ちる", "undercut: a column\nfalls when its soft\nfoot loses u_c")
    for i, hi in enumerate(h):
        ax.add_patch(plt.Rectangle((i, 0), 1, hi, color=C_SOFT, ec="0.4", lw=0.6))
    if kind in ("face", "undercut"):
        for i in range(3):
            ax.add_patch(plt.Rectangle((i, 8.5), 1, 1.5, color=C_CAP))
    if kind == "step":
        ax.annotate("", xy=(3.15, 4), xytext=(3.15, 10), arrowprops=dict(arrowstyle="<->", color=C_ERODE))
        ax.text(3.3, 7, "> H_c", color=C_ERODE, fontsize=8)
        _arrow(ax, 2.5, 9.0, 3.5, 5.0, "0.3", lw=1.2)
    elif kind == "window":
        ax.add_patch(plt.Rectangle((0.5, -0.3), 6.0, 10.6, fill=False, ec="C0", lw=1.0, ls="--"))
        ax.text(0.6, 10.6, T("窓(半径 r_c)", "window (radius r_c)"), color="C0", fontsize=7.5)
        ax.annotate("", xy=(6.3, 1.0), xytext=(6.3, 10), arrowprops=dict(arrowstyle="<->", color=C_ERODE))
        ax.text(7.3, 11.3, "H_w > H_c", color=C_ERODE, fontsize=8, ha="right")
    elif kind == "face":
        ax.add_patch(plt.Polygon([(3, 2.2), (3, 6.5), (5.5, 2.0), (5.5, 1.6)], color=C_TALUS))
        ax.text(3.1, 7.2, T("崖錐", "talus"), fontsize=7.5, color="0.3")
        ax.text(0.2, 6.0, T("削れない", "not eroded"), fontsize=8, color=C_ERODE)
    else:
        ax.add_patch(plt.Rectangle((2, 3.0), 1, 4.0, color="w", ec=C_ERODE, lw=1.0, ls="--"))
        ax.text(0.2, 4.2, "u_c", fontsize=8, color=C_ERODE)
        _arrow(ax, 1.0, 4.6, 2.0, 4.6, C_ERODE, lw=1.0)
        _arrow(ax, 2.5, 11.0, 2.5, 8.4, "0.3", lw=1.2)
    ax.set_xlim(-0.2, 7.4)
    ax.set_ylim(-0.6, 12.5)
    ax.axis("off")
    ax.set_title(title, fontsize=8.5)


def mechanism():
    fig = plt.figure(figsize=(13.5, 10.5))
    gs = fig.add_gridspec(3, 4, height_ratios=[1.3, 0.75, 0.85], hspace=0.38, wspace=0.18)
    ax = fig.add_subplot(gs[0, :])
    _mesa(ax)
    ax.set_title(T("(a) メサの崖の後退: 帽岩が頂を守り、軟層の掘り込みと崩落で縁が後退する",
                   "(a) Retreat of a mesa cliff: the cap protects the top; undercutting and collapse make the edge retreat"),
                 loc="left", fontsize=10)
    ax = fig.add_subplot(gs[1, :])
    _sequence(ax)
    ax.set_title(T("(b) 台地は縮んでメサ → ビュート → 尖塔になり、消える", "(b) A plateau shrinks to a mesa → butte → pinnacle and disappears"),
                 loc="left", fontsize=10)
    axs = [fig.add_subplot(gs[2, k]) for k in range(4)]
    for a, kind in zip(axs, ("step", "window", "face", "undercut")):
        _rule(a, kind)
    fig.text(0.125, 0.362, T("(c) 崩落と崖錐(f_rockfall)の規則。ラスタでは張り出しを表せないので、柱(セル)の高さの規則で近似する",
                             "(c) Rules of rockfall and talus (f_rockfall). A raster cannot hold overhangs, so collapse is approximated by rules on column (cell) heights"),
             fontsize=10)
    fig.savefig(f"{FIGDIR}/mechanism.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


def setup():
    z = np.loadtxt("z.txt")
    ny, nx = z.shape
    fig = plt.figure(figsize=(14, 6.6))
    gs = fig.add_gridspec(2, 3, width_ratios=[1.65, 0.3, 1.0], height_ratios=[1, 1], wspace=0.18, hspace=0.45)
    ax = fig.add_subplot(gs[0, 0])
    im = ax.imshow(z, origin="lower", extent=[0, nx, 0, ny], cmap="terrain", vmin=-6, vmax=22)
    ax.axhline(50, color="k", lw=0.6, ls="--")
    ax.text(60, 92, T("R₀ = 30 m(メサ)", "R₀ = 30 m (mesa)"), ha="center", fontsize=8)
    ax.text(150, 92, T("R₀ = 12 m(ビュートの候補)", "R₀ = 12 m (butte candidate)"), ha="center", fontsize=8)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title(T("初期地形: 平地(z = 0 = 侵食基準面)に高さ 20 m の台地 2 つ(縁 tanθ = 2 ≈ 63°、縁に白色雑音 ±0.5 m)",
                   "Initial terrain: two plateaus 20 m high on a plain (z = 0 = base level; edges tanθ = 2 ≈ 63°, white noise ±0.5 m on the edges)"),
                 fontsize=9)
    fig.colorbar(im, ax=ax, shrink=0.8).set_label(T("地盤高 (m)", "elevation (m)"))
    ax = fig.add_subplot(gs[1, 0])
    x = np.arange(nx) + 0.5
    ax.fill_between(x, 0, z[50], color=C_SOFT)
    ax.plot(x, z[50], "k-", lw=1.2)
    ax.set_xlim(0, 200)
    ax.set_ylim(0, 23)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("z (m)")
    ax.set_title(T("2 つの台地の中心を通る横断(y = 50 m)", "Section through the centres of the two plateaus (y = 50 m)"), fontsize=9)
    ax = fig.add_subplot(gs[1, 1])
    cols = [("cap", [(17, 20, 0.05), (8, 10, 0.3)]), ("bench2", [(17, 20, 0.05), (5, 10, 0.02)]),
            ("uc_cap", [(13, 20, 0.05), (5, 10, 0.02)])]
    for k, (nm, lays) in enumerate(cols):
        for z1, z2, f in lays:
            ax.add_patch(plt.Rectangle((k, z1), 0.8, z2 - z1, color=C_CAP if f <= 0.05 else C_HARD))
            ax.text(k + 0.4, (z1 + z2) / 2, "%g" % f, ha="center", va="center", fontsize=6.5, color="w")
    ax.set_xlim(-0.1, 2.9)
    ax.set_ylim(0, 23)
    ax.set_xticks([0.4, 1.4, 2.4])
    ax.set_xticklabels(["cap", "bench2 …", "uc_cap"], fontsize=7, rotation=90)
    ax.set_yticklabels([])
    ax.set_title(T("硬い層\n(数字 = 倍率)", "hard beds\n(factor)"), fontsize=8)
    ax = fig.add_subplot(gs[:, 2])
    ax.axis("off")
    rows = [
        (T("領域", "domain"), T("200 × 100 m、Δx = 1 m(Δx = 4 m の対照あり)", "200 × 100 m, Δx = 1 m (control with Δx = 4 m)")),
        (T("降雨", "rain"), T("一様 10 mm/h、全量浸透(表面流ゼロ)", "uniform 10 mm/h, all infiltrates (no surface flow)")),
        (T("乾式侵食", "dry erosion"), T("f_splash(badland_round と同じ係数)", "f_splash (same as badland_round)")),
        (T("層理", "strata"), T("主ケース: 帽岩 z ≥ 17 m(0.05)、\n中間硬層 8〜10 m(0.3)、ほかは 1。\n対照: 層理なし", "main case: cap z ≥ 17 m (0.05),\nhard bed 8–10 m (0.3), others 1;\ncontrol: no strata")),
        (T("クリープ", "creep"), T("弱い D = 3×10⁻⁷ m²/s(裾の土の移動)", "weak D = 3×10⁻⁷ m²/s (soil at the foot)")),
        (T("崩落", "rockfall"), T("補足 3 の系列だけ(f_rockfall)", "only in the supplement-3 series (f_rockfall)")),
        (T("時間", "time"), T("dt 2 s、地形更新 2 s × morfac 500\n48 h = T_geo 8.6×10⁷ s、4 h ごとに Z", "dt 2 s, update every 2 s × morfac 500\n48 h = T_geo 8.6×10⁷ s, Z every 4 h")),
    ]
    yv = 0.97
    for k, v in rows:
        ax.text(0.0, yv, k, fontsize=9, va="top", color="0.2")
        ax.text(0.24, yv, v, fontsize=9, va="top")
        yv -= 0.08 + 0.055 * v.count("\n")
    ax.set_title(T("設定の要約", "Summary of settings"), fontsize=9, loc="left")
    fig.savefig(f"{FIGDIR}/setup.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    mechanism()
    setup()
    print(f"{FIGDIR}/mechanism.png, {FIGDIR}/setup.png written")
