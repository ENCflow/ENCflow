#!/usr/bin/env python3
"""V 字谷の設定と疑似窪地の仕組みの図 figs/setup.png(計算結果を使わない)。

  python3 plot_setup.py        日本語 → figs/setup.png
  python3 plot_setup.py en     英語   → en/figs/setup.png

(a) 谷の平面(色 = 地盤高)と計測面・プローブ、(b) 横断(斜面の勾配 4 通り)、
(c) 向き 45° の格子の谷底付近のセルと地盤高: 4 近傍では谷底のセルの隣 4 つがすべて高い(疑似窪地)、
(d) 疑似窪地の深さ H_p = (√2/2)(S_S − S_V) Δx と、谷全体の貯留の見積もり。
"""
import math
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import make_inputs as M

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)


def panel_plan(ax, ss=M.S_S_BASE):
    ds = 5.0
    s = np.arange(0, M.L, ds) + ds / 2
    n = np.arange(-M.WH, M.WH, ds) + ds / 2
    S, N = np.meshgrid(s, n)
    Z = M.terrain(ss, S, N)
    im = ax.imshow(Z, origin="lower", extent=[0, M.L, -M.WH, M.WH], cmap="YlOrBr", vmin=0, vmax=50, aspect="equal")
    ax.add_patch(Rectangle((M.L, -M.WH), 40, 2 * M.WH, color="#1f3f8b"))
    ax.plot([0, M.L], [0, 0], color="#2b8a3e", lw=1.0, ls="--", label=T("谷底の軸(幅 0)", "valley axis (zero width)"))
    ax.plot([M.L - 5, M.L - 5], [-M.WH + 5, M.WH - 5], color="#c0392b", lw=2.0, label=T("下流端の計測面(全幅)", "outlet face (full width)"))
    ax.plot(M.L - 5, 0, "o", ms=6, color="k", mfc="w", label=T("P1 下流端の谷底", "P1 valley floor at the outlet"))
    ax.plot(M.L / 2, 0, "s", ms=6, color="k", mfc="w", label=T("P2 谷の中央の谷底", "P2 valley floor at mid-length"))
    ax.text(M.L + 20, 0, T("海(吸い込み)", "sea (sink)"), rotation=90, va="center", ha="left", fontsize=7, color="#1f3f8b")
    ax.text(M.L / 2, M.WH / 2, T(f"斜面 S_S = {ss}(谷底へ)\nn = 0.1", f"hillslope S_S = {ss} (toward the floor)\nn = 0.1"), ha="center", fontsize=8)
    ax.text(M.L / 2, -M.WH / 2, T("斜面(同じ)", "hillslope (same)"), ha="center", fontsize=8)
    ax.annotate("", xy=(M.L, M.WH + 60), xytext=(0, M.WH + 60), arrowprops=dict(arrowstyle="<->", color="k"))
    ax.text(M.L / 2, M.WH + 80, T("L = 1000 m(谷の勾配 S_V = 0.02)", "L = 1000 m (valley slope S_V = 0.02)"), ha="center", va="bottom", fontsize=8)
    ax.annotate("", xy=(-60, M.WH), xytext=(-60, 0), arrowprops=dict(arrowstyle="<->", color="k"))
    ax.text(-80, M.WH / 2, "810 m", rotation=90, ha="right", va="center", fontsize=8)
    ax.annotate("", xy=(300, -300), xytext=(100, -300), arrowprops=dict(arrowstyle="-|>", color="k"))
    ax.text(200, -270, "s", fontsize=9, ha="center")
    ax.annotate("", xy=(100, -100), xytext=(100, -300), arrowprops=dict(arrowstyle="-|>", color="k"))
    ax.text(120, -130, "n", fontsize=9)
    ax.legend(loc="lower left", fontsize=7, framealpha=0.9)
    ax.set_xlim(-130, M.L + 80)
    ax.set_ylim(-M.WH - 20, M.WH + 160)
    ax.set_xlabel("s (m)")
    ax.set_ylabel("n (m)")
    ax.set_title(T("(a) 谷の平面(色 = 地盤高 m。雨 10.8 mm/h × 60 分)", "(a) Plan of the valley (colour = elevation, m; rain 10.8 mm/h for 60 min)"), fontsize=9)
    plt.colorbar(im, ax=ax, fraction=0.03, pad=0.01).set_label(T("地盤高 (m)", "elevation (m)"), fontsize=8)


def panel_section(ax):
    n = np.linspace(-M.WH, M.WH, 401)
    for ss, col in zip(M.S_S_LIST, ("#1f5f8b", "#2b8a3e", "#d08c00", "#c0392b")):
        ax.plot(n, M.terrain(ss, M.L / 2, n), color=col, lw=1.4, label=f"S_S = {ss}")
    ax.set_xlabel("n (m)")
    ax.set_ylabel(T("標高 (m)", "elevation (m)"))
    ax.set_title(T("(b) 横断(s = 500 m)", "(b) Cross-section (s = 500 m)"), fontsize=9)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)


def panel_cells(ax, ss=M.S_S_BASE, dx=20.0):
    """向き 45° の格子の、谷底の軸の 1 セルとその 8 近傍の地盤高(軸のセルからの差)。"""
    nx, ny, ox, oy, c, sn, _ = M.frame(dx, 45.0)
    i0, j0 = M.ij_of(dx, 45.0, M.L / 2, 0.0)
    _, kind, s, n = M.grid(ss, dx, 45.0)
    # 軸のセル(|n| 最小)に合わせる
    I, J = np.meshgrid(np.arange(nx), np.arange(ny))
    axis = (kind == 1) & (np.abs(n) < 1e-6)
    jj, ii = np.nonzero(axis)
    k = np.argmin(np.abs(s[jj, ii] - M.L / 2))
    i0, j0 = ii[k], jj[k]
    z0 = M.terrain(ss, s[j0, i0], n[j0, i0])
    for di in (-2, -1, 0, 1, 2):
        for dj in (-2, -1, 0, 1, 2):
            i, j = i0 + di, j0 + dj
            dz = M.terrain(ss, s[j, i], n[j, i]) - z0
            near = abs(di) <= 1 and abs(dj) <= 1
            ax.add_patch(Rectangle((di - 0.5, dj - 0.5), 1, 1, facecolor=plt.get_cmap("YlOrBr")(0.15 + 0.6 * np.clip(dz / 1.2, 0, 1)) if dz >= -1e-9 else "#9ecae1",
                                   edgecolor="k" if near else "0.6", lw=1.2 if near else 0.5, alpha=1.0 if near else 0.6))
            ax.text(di, dj, f"{dz:+.2f}", ha="center", va="center", fontsize=8 if near else 7, color="k" if near else "0.4")
    ax.text(0, 0.28, T("谷底", "floor"), ha="center", fontsize=8, color="#1f3f8b")
    # 4 近傍の隣(赤の ×)と 8 近傍の斜めの隣(緑の矢印)
    for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ax.annotate("", xy=(di * 0.75, dj * 0.75), xytext=(di * 0.3, dj * 0.3), arrowprops=dict(arrowstyle="-|>", color="#c0392b", lw=1.5))
    # 下流の斜めの隣(s が増える向き = 格子の南東)
    ds_ = np.array([s[j0 + dj, i0 + di] - s[j0, i0] for di, dj in ((1, -1), (-1, 1), (1, 1), (-1, -1))])
    kdn = int(np.argmax(ds_))
    di, dj = ((1, -1), (-1, 1), (1, 1), (-1, -1))[kdn]
    ax.annotate("", xy=(di * 0.8, dj * 0.8), xytext=(di * 0.3, dj * 0.3), arrowprops=dict(arrowstyle="-|>", color="#2b8a3e", lw=2.5))
    c_, sn_ = math.cos(math.radians(45)), math.sin(math.radians(45))
    ax.annotate("", xy=(-1.6 + 0.9 * c_, -1.9 - 0.9 * sn_), xytext=(-1.6, -1.9), arrowprops=dict(arrowstyle="-|>", color="k"))
    ax.text(-1.6 + 1.0 * c_, -1.9 - 1.0 * sn_, "s", fontsize=9)
    ax.annotate("", xy=(-1.6 + 0.9 * sn_, -1.9 + 0.9 * c_), xytext=(-1.6, -1.9), arrowprops=dict(arrowstyle="-|>", color="k"))
    ax.text(-1.6 + 1.0 * sn_, -1.9 + 1.0 * c_, "n", fontsize=9)
    ax.set_xlim(-2.6, 2.6)
    ax.set_ylim(-2.6, 2.6)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    hp = math.sqrt(2) / 2 * (ss - M.S_V) * dx
    ax.set_title(T(f"(c) 45° の格子 {dx:g} m、S_S = {ss}: 谷底のセルからの地盤高の差 (m)\n赤 = 4 近傍の隣(すべて +{hp:.2f} m 以上)、緑 = 下流の斜めの隣(低い)",
                   f"(c) 45° grid, {dx:g} m, S_S = {ss}: elevation relative to the floor cell (m)\nred = 4 neighbours (all at least +{hp:.2f} m), green = diagonal downstream neighbour (lower)"), fontsize=8.5)


def panel_formula(ax):
    d = np.linspace(0, 0.03, 100)
    for dx, col in ((20.0, "#c0392b"), (10.0, "#2b8a3e"), (5.0, "#1f5f8b")):
        hp = math.sqrt(2) / 2 * d * dx
        vp = 0.5 * M.L * d * dx * dx
        rain = M.P_MMH / 1000 / 3600 * M.T_RAIN * 60 * 2 * M.WH * M.L
        ax.plot(d, vp / rain * 100, color=col, lw=1.5, label=T(f"Δx = {dx:g} m(H_p は S_S − S_V = 0.01 で {hp[np.argmin(np.abs(d - 0.01))]:.2f} m)",
                                                                  f"Δx = {dx:g} m (H_p = {hp[np.argmin(np.abs(d - 0.01))]:.2f} m at S_S − S_V = 0.01)"))
    for ss in M.S_S_LIST:
        if ss > M.S_V:
            ax.axvline(ss - M.S_V, color="0.7", lw=0.8, ls=":")
    ax.set_xlabel("S_S − S_V")
    ax.set_ylabel(T("Σ V_p / 雨の量 (%)", "Σ V_p / rainfall (%)"))
    ax.set_title(T("(d) 4 近傍で谷底の軸のセルが溜める量の見積もり\nH_p = (√2/2)(S_S − S_V) Δx、Σ V_p = (L/2)(S_S − S_V) Δx²",
                   "(d) Estimated storage in the floor cells with 4 neighbours\nH_p = (√2/2)(S_S − S_V) Δx, Σ V_p = (L/2)(S_S − S_V) Δx²"), fontsize=8.5)
    ax.set_xlim(0, 0.03)
    ax.set_ylim(0, 40)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7)


def main():
    fig = plt.figure(figsize=(14, 9.0), constrained_layout=True)
    gs = fig.add_gridspec(2, 4, height_ratios=[1.3, 1.0])
    panel_plan(fig.add_subplot(gs[0, :2]))
    panel_section(fig.add_subplot(gs[0, 2:]))
    panel_cells(fig.add_subplot(gs[1, :2]))
    panel_formula(fig.add_subplot(gs[1, 2:]))
    fig.savefig(f"{FIGDIR}/setup.png", dpi=110)
    print(f"{FIGDIR}/setup.png")


if __name__ == "__main__":
    main()
