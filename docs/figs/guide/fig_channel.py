"""河道の章の図: サブグリッド河道幅と σ 断面・堤防の仮想壁面(断面)、壁エッジと破堤サイト(平面)、破堤の時系列。"""
from _style import *
import numpy as np

T = {"ja": {
    "a": "(a) 断面: 河道セル 1 つ(セル幅 dx)とその両側の堤内地セル",
    "b": "(b) 平面: 壁エッジと破堤サイト",
    "c": "(c) 破堤 &list_channel_breach",
    "W": "河道セル(fn_rw)の河道幅 W(fn_width、W < dx)",
    "rest": "セル内の非河道部分は\n扱わない(状態量は河道部分のみ)",
    "wall": "堤防 = 仮想壁面(bank0 / fn_bank)\n天端 = 堤内地標高 + bank0(f_bank_datum = 1)",
    "weir": "天端を超えた分は\n本間公式の堰越流",
    "D": "D = 天端 − 河床\n(≈ bank0 + depth_rw)",
    "drw": "depth_rw",
    "sigma": "断面形 σ(h) = (h/D)^m(p_sect_m)\nm = 0 矩形(既定)、0.5 放物線的、1 三角形的\nh ≥ D では矩形に戻る",
    "land": "堤内地セル", "ch": "河道セル(fn_rw)",
    "edges": "壁エッジ = 河道セル × 堤内地セルの全エッジ(対角を含む)\n天端は河道側セルの値(fn_bank は河道セル位置に与える)",
    "site": "破堤サイト = 隣接する河道セル (ic, jc) と\n堤内地セル (il, jl) の対(エッジ 1 本)\nbr_cell(:,n) = ic, jc, il, jl",
    "xlabel": "時刻 (min)", "ylabel": "天端の残存割合 f",
    "eff": "実効天端 = 堤内地盤高\n + f × (天端 − 堤内地盤高)",
    "ws": "水位(河道部分の状態量)",
    "series": "br_series(:,k,n) = t, f",
}, "en": {
    "a": "(a) Section: one channel cell (cell width dx) and the landside cells on both sides",
    "b": "(b) Plan: wall edges and a breach site",
    "c": "(c) Breach &list_channel_breach",
    "W": "width W of the channel cell (fn_rw) (fn_width, W < dx)",
    "rest": "non-channel part of the cell is\nnot represented (state = channel part only)",
    "wall": "levee = virtual wall (bank0 / fn_bank)\ncrest = landside elevation + bank0 (f_bank_datum = 1)",
    "weir": "excess over the crest spills\nas Honma weir overtopping",
    "D": "D = crest − bed\n(≈ bank0 + depth_rw)",
    "drw": "depth_rw",
    "sigma": "section shape σ(h) = (h/D)^m (p_sect_m)\nm = 0 rectangle (default), 0.5 parabolic, 1 triangular\nback to the rectangle for h ≥ D",
    "land": "landside cells", "ch": "channel cells (fn_rw)",
    "edges": "wall edges = every edge between channel and landside cells (diagonals included)\ncrest = value of the channel-side cell (fn_bank is given at channel cells)",
    "site": "breach site = pair of adjacent channel cell (ic, jc)\nand landside cell (il, jl) (one edge)\nbr_cell(:,n) = ic, jc, il, jl",
    "xlabel": "time (min)", "ylabel": "remaining crest fraction f",
    "eff": "effective crest = landside ground\n + f × (crest − landside ground)",
    "ws": "water level (state of the channel part)",
    "series": "br_series(:,k,n) = t, f",
}}


def panel_section(ax, t):
    ax.axis("off")
    zL, drw, bank0 = 1.0, 0.6, 0.5
    zb, zc = zL - drw, zL + bank0          # 河床、天端
    D = zc - zb
    x0, x1 = 1.25, 1.75                    # 河道幅 W(セルは x = 1..2)
    ws = 1.65                              # 河道の水位(天端を少し超える)
    # 堤内地セル(左右)と河道セルの地盤
    ax.add_patch(Rectangle((0, -0.2), 1, zL + 0.2, fc=C_GROUND_L, ec="none", zorder=1))
    ax.add_patch(Rectangle((2, -0.2), 1, zL + 0.2, fc=C_GROUND_L, ec="none", zorder=1))
    ax.plot([0, 1], [zL, zL], color=C_GROUND, lw=1.4, zorder=2); ax.plot([2, 3], [zL, zL], color=C_GROUND, lw=1.4, zorder=2)
    ax.add_patch(Rectangle((1, -0.2), 1, zb + 0.2, fc=C_GROUND_L, ec="none", zorder=1))
    ax.plot([1, 2], [zb, zb], color=C_GROUND, lw=1.4, zorder=2)
    # 非河道部分(扱わない)
    for (xa, xb) in [(1, x0), (x1, 2)]:
        ax.add_patch(Rectangle((xa, zb), xb - xa, zL - zb, fc="none", ec=C_P, hatch="///", lw=0, zorder=1.5))
    # 河道の水(幅 W)。水位はセルの状態量なのでセル幅に破線で示す
    ax.add_patch(Rectangle((x0, zb), x1 - x0, ws - zb, fc=C_WATER_L, ec="none", zorder=1.6))
    ax.plot([x0, x1], [ws, ws], color=C_WATER, lw=1.4, zorder=3)
    ax.plot([1, 2], [ws, ws], color=C_WATER, lw=1.0, ls="--", zorder=3)
    ax.text(1.5, ws + 0.06, t["ws"], fontsize=8, color=C_WATER, ha="center", va="bottom")
    ax.add_patch(Rectangle((2, zL), 0.5, 0.12, fc=C_WATER_L, ec="none", zorder=1.6))
    ax.plot([2, 2.5], [zL + 0.12, zL + 0.12], color=C_WATER, lw=1.0, zorder=3)
    # σ の断面形(m = 0.5, 1)
    hh = np.linspace(0, D, 60); xc = (x0 + x1) / 2
    for m, ls in [(0.5, "--"), (1.0, ":")]:
        hw = (x1 - x0) / 2 * (hh / D) ** m
        ax.plot(xc - hw, zb + hh, color=C_WATER, lw=1.1, ls=ls, zorder=3.5)
        ax.plot(xc + hw, zb + hh, color=C_WATER, lw=1.1, ls=ls, zorder=3.5)
    # 仮想壁面(セル面 x = 1, 2)
    for x in (1, 2):
        ax.plot([x, x], [zb, zc], color=C_X, lw=4.0, solid_capstyle="butt", zorder=4)
    # 越流の矢印
    arrow(ax, (2.0, zc + 0.08), (2.45, zL + 0.2), C_X, lw=1.6)
    # 寸法線: D と depth_rw
    ax.annotate("", (0.86, zc), (0.86, zb), arrowprops=dict(arrowstyle="<->", color="k", lw=0.9))
    ax.text(0.8, zb + 0.32, t["D"], fontsize=8.5, color="k", ha="right", va="center")
    ax.annotate("", (2.12, zL), (2.12, zb), arrowprops=dict(arrowstyle="<->", color=C_GROUND, lw=0.9))
    ax.text(2.18, (zL + zb) / 2, t["drw"], fontsize=8.5, color=C_GROUND, ha="left", va="center")
    # セル境界とセル幅
    for x in (0, 1, 2, 3):
        ax.plot([x, x], [-0.2, 2.2], color="#c9c8c3", lw=0.6, zorder=0.5)
    ax.annotate("", (2, 2.0), (1, 2.0), arrowprops=dict(arrowstyle="<->", color=C_P, lw=0.9))
    ax.text(1.5, 2.05, "dx", fontsize=8.5, color=C_P, ha="center", va="bottom")
    ax.annotate("", (x1, zb - 0.1), (x0, zb - 0.1), arrowprops=dict(arrowstyle="<->", color=C_C, lw=0.9))
    ax.text(1.5, zb - 0.16, "W", fontsize=8.5, color=C_C, ha="center", va="top")
    # ラベル
    ax.text(0.4, zL + 0.6, t["land"], fontsize=8.5, color=C_GROUND, ha="center", va="bottom")
    ax.text(2.5, zL + 0.3, t["land"], fontsize=8.5, color=C_GROUND, ha="center", va="bottom")
    ax.text(1.5, -0.35, t["W"] + "\n" + t["rest"], fontsize=8.5, color=C_C, ha="center", va="top")
    ax.annotate(t["wall"], (1.0, zc - 0.05), (-0.05, 2.5), fontsize=8.5, color=C_X, ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color=C_X, lw=0.7))
    ax.annotate(t["weir"], (2.25, zc + 0.12), (2.55, 2.15), fontsize=8.5, color=C_X, ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color=C_X, lw=0.7))
    ax.text(3.05, 0.45, t["sigma"], fontsize=8.5, color=C_WATER, ha="left", va="center")
    ax.set_xlim(-0.1, 5.3); ax.set_ylim(-1.0, 2.75)
    ax.set_title(t["a"], loc="left", fontsize=9.5)


def panel_plan(ax, t):
    ax.set_aspect("equal"); ax.axis("off")
    NXp, NYp, JC = 6, 5, 2          # 河道は行 y = JC..JC+1(中央行)
    grid(ax, 0, 0, NXp, NYp, 1, "#c9c8c3", 0.6)
    ax.add_patch(Rectangle((0, JC), NXp, 1, fc="#eaf2fc", ec="none", zorder=0.5))
    arrow(ax, (0.3, JC + 0.6), (NXp - 0.3, JC + 0.6), C_C, lw=1.4, z=2)
    # 壁エッジ: 軸(河道行の上下の面)
    ax.plot([0, NXp], [JC, JC], color=C_X, lw=3.2, zorder=4)
    ax.plot([0, NXp], [JC + 1, JC + 1], color=C_X, lw=3.2, zorder=4)
    # 壁エッジ: 対角(河道セル中心 → 斜めの堤内地セル中心 を短い橙線で)
    for i in range(NXp):
        for (dx, dy) in [(1, 1), (-1, 1), (1, -1), (-1, -1)]:
            cx, cy = i + 0.5, JC + 0.5
            if 0 <= i + dx < NXp:
                ax.plot([cx + 0.25 * dx, cx + 0.75 * dx], [cy + 0.25 * dy, cy + 0.75 * dy], color=C_X, lw=1.4, ls="--", zorder=3)
    # 破堤サイト: 河道セル (4, 3) と堤内地セル (4, 2)(上側 = 北) の間のエッジを白抜きに
    ic = 3  # 0 始まりの列
    ax.plot([ic, ic + 1], [JC + 1, JC + 1], color="white", lw=4.0, zorder=5)
    ax.plot([ic, ic + 1], [JC + 1, JC + 1], color=C_X, lw=1.2, ls=":", zorder=6)
    arrow(ax, (ic + 0.5, JC + 0.7), (ic + 0.5, JC + 1.55), C_X, lw=2.0, z=7)
    ax.add_patch(Rectangle((ic, JC + 1), 1, 1, fc=C_WATER_L, ec="none", zorder=0.6))
    ax.text(ic + 0.5, JC + 0.25, "(ic, jc)", fontsize=8, color="k", ha="center", va="center", zorder=8, bbox=dict(fc="white", ec="none", alpha=0.8, pad=1))
    ax.text(ic + 0.5, JC + 1.8, "(il, jl)", fontsize=8, color="k", ha="center", va="center", zorder=8)
    ax.text(NXp + 0.15, JC + 0.5, t["ch"], fontsize=8.5, color=C_C, ha="left", va="center")
    ax.text(NXp + 0.15, JC + 2.5, t["land"], fontsize=8.5, color=C_GROUND, ha="left", va="center")
    ax.text(NXp + 0.15, JC - 1.5, t["land"], fontsize=8.5, color=C_GROUND, ha="left", va="center")
    ax.text(0, -0.35, t["edges"], fontsize=8.5, color=C_X, ha="left", va="top")
    ax.text(0, -1.4, t["site"], fontsize=8.5, color="k", ha="left", va="top")
    ax.set_xlim(-0.2, NXp + 3.2); ax.set_ylim(-2.7, NYp + 0.3)
    ax.set_title(t["b"], loc="left", fontsize=9.5)


def panel_breach(ax, t):
    ts = [0, 60, 70, 90, 110]; fs = [1.0, 1.0, 0.2, 0.0, 0.0]
    ax.plot(ts, fs, color=C_X, lw=2.0)
    ax.plot(ts[:4], fs[:4], "o", color=C_X, ms=6)
    ax.set_ylim(-0.08, 1.2); ax.set_xlim(0, 110)
    ax.set_xlabel(t["xlabel"]); ax.set_ylabel(t["ylabel"])
    ax.text(2, 1.1, t["series"], fontsize=8.5, color=C_X, ha="left", va="center")
    ax.text(3, 0.4, t["eff"], fontsize=8.5, color="k", ha="left", va="center")
    ax.set_title(t["c"], loc="left", fontsize=9.5)


def draw(lang):
    t = T[lang]
    fig = plt.figure(figsize=(10.5, 7.2), layout="constrained")
    gs = fig.add_gridspec(2, 2, width_ratios=[1.35, 1.0], height_ratios=[1.0, 1.0])
    panel_section(fig.add_subplot(gs[0, :]), t)
    panel_plan(fig.add_subplot(gs[1, 0]), t)
    panel_breach(fig.add_subplot(gs[1, 1]), t)
    return save(fig, "channel_subgrid", lang)
