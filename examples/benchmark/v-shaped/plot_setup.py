#!/usr/bin/env python3
"""V 字流域の設定の図 figs/setup.png(計算結果を使わない。make の後ならいつでも描ける)。

  python3 plot_setup.py        日本語 → figs/setup.png
  python3 plot_setup.py en     英語   → en/figs/setup.png

(a) 流域の平面(流域の座標 s, n。色 = 地盤高)と下流の区間・延長・海、計測線・プローブ、(b) 横断と縦断、
(c) 格子 20 m を流域に 0° と 45° で重ねたときの出口付近のセル(水路は 45° で斜めの 1 列)、
(d) 運動学的波の理論解(出口と斜面の脚)。寸法と式は make_inputs.py・analytic.py のもの。
"""
import math
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon
import make_inputs as M

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)
C_HILL, C_CHAN, C_EXT, C_SEA, C_OUT, C_HILL2 = "#d9c9a3", "#4a90c2", "#86b8d8", "#1f3f8b", "#f2f2f2", "#ece2c9"


def kind_color(kind):
    return {0: C_OUT, 1: C_HILL, 2: C_CHAN, 3: C_EXT, 4: C_SEA, 5: C_HILL2}[kind]


def panel_plan(ax):
    ds = 5.0
    s_hill = M.L + M.L_EXT
    s = np.arange(0, s_hill, ds) + ds / 2
    n = np.arange(-M.WH, M.WH, ds) + ds / 2
    S, N = np.meshgrid(s, n)
    inch = np.abs(N) < M.W / 2
    Z = np.where(inch, M.Z_OUT + M.S_C * (M.L - S), M.Z_OUT + M.S_C * M.L + M.D_UP + M.S_S * (np.abs(N) - M.W / 2))
    im = ax.imshow(Z, origin="lower", extent=[0, s_hill, -M.WH, M.WH], cmap="YlOrBr", vmin=0, vmax=75, aspect="equal")
    ax.axhspan(-M.W / 2, M.W / 2, xmin=0.0, xmax=1.0, color=C_CHAN, alpha=0.9)
    ax.add_patch(Rectangle((M.L, -M.W / 2), M.L_EXT, M.W, color=C_EXT))
    ax.add_patch(Rectangle((s_hill, -M.W / 2), 60, M.W, color=C_EXT))
    ax.add_patch(Rectangle((s_hill + 60, -M.W / 2), 60, M.W, color=C_SEA))
    ax.plot([M.L, M.L], [-M.WH, M.WH], color="k", lw=0.8, ls="--")
    ax.plot([s_hill, s_hill], [-M.WH, M.WH], color="k", lw=0.8, ls=":")
    ax.plot([M.L - 5, M.L - 5], [-M.WH + 5, M.WH - 5], color="#c0392b", lw=2.0, label=T("出口の計測面(全幅)", "outlet face (full width)"))
    ax.plot([5, M.L - 5], [M.W / 2 + 10, M.W / 2 + 10], color="#2b8a3e", lw=2.0, label=T("斜面の脚の計測線(左岸側)", "hillslope-foot line (left side)"))
    ax.plot(M.L - 5, 0, "o", ms=6, color="k", mfc="w", label=T("P1 出口の水路の水深", "P1 depth in the outlet channel cell"))
    ax.plot(M.L / 2, M.W / 2 + 30, "s", ms=6, color="k", mfc="w", label=T("P2 斜面の水路から 2 列目の水深", "P2 depth in the second hillslope cell from the channel"))
    ax.legend(loc="lower left", fontsize=7, framealpha=0.9)
    ax.annotate("", xy=(s_hill + 118, 0), xytext=(s_hill + 60, 0), arrowprops=dict(arrowstyle="-|>", color="w"))
    ax.text(M.L + M.L_EXT / 2, -M.WH / 2 + 80, T("下流の区間 200 m(同じ断面。雨も降る。流域には数えない)", "downstream section 200 m (same cross-section, rained on; not part of the catchment)"), fontsize=7, ha="center", va="center", rotation=90)
    ax.text(s_hill + 10, 120, T("延長 + 海(吸い込み)", "extension + sea (sink)"), fontsize=7, rotation=90, va="bottom")
    for y, txt in ((M.WH / 2 + 150, T("斜面: 水路へ S_S = 0.05、水路方向 S_O = 0\nn = 0.015", "hillslope: S_S = 0.05 toward the channel, S_O = 0 along it\nn = 0.015")),
                   (-M.WH / 2 - 150, T("斜面(同じ)", "hillslope (same)"))):
        ax.text(M.L / 2 + 60, y, txt, ha="center", fontsize=8)
    ax.text(M.L / 2 + 60, -M.W / 2 - 40, T("水路: 幅 20 m、S_C = 0.02、n = 0.15", "channel: 20 m wide, S_C = 0.02, n = 0.15"), ha="center", va="top", fontsize=8, color="#1f3f8b")
    ax.annotate("", xy=(M.L, -M.WH - 60), xytext=(0, -M.WH - 60), arrowprops=dict(arrowstyle="<->", color="k"))
    ax.text(M.L / 2, -M.WH - 80, "L = 1000 m", ha="center", va="top", fontsize=8)
    ax.annotate("", xy=(-60, M.WH), xytext=(-60, M.W / 2), arrowprops=dict(arrowstyle="<->", color="k"))
    ax.text(-80, (M.WH + M.W / 2) / 2, "B = 800 m", rotation=90, ha="right", va="center", fontsize=8)
    ax.annotate("", xy=(300, 0), xytext=(100, 0), arrowprops=dict(arrowstyle="-|>", color="k"))
    ax.text(200, 30, "s", fontsize=9, ha="center")
    ax.annotate("", xy=(100, 200), xytext=(100, 0), arrowprops=dict(arrowstyle="-|>", color="k"))
    ax.text(120, 180, "n", fontsize=9)
    ax.set_xlim(-130, s_hill + 130)
    ax.set_ylim(-M.WH - 120, M.WH + 20)
    ax.set_xlabel("s (m)")
    ax.set_ylabel("n (m)")
    ax.set_title(T("(a) 流域の平面(色 = 地盤高 m。雨 10.8 mm/h × 90 分を全域に)", "(a) Plan of the catchment (colour = elevation, m; rain 10.8 mm/h for 90 min everywhere)"), fontsize=9)
    plt.colorbar(im, ax=ax, fraction=0.03, pad=0.01).set_label(T("地盤高 (m)", "elevation (m)"), fontsize=8)


def panel_sections(ax1, ax2):
    n = np.linspace(-M.WH, M.WH, 1001)
    zc = M.Z_OUT + M.S_C * (M.L - M.L / 2)
    z = np.where(np.abs(n) < M.W / 2, zc, M.Z_OUT + M.S_C * M.L + M.D_UP + M.S_S * (np.abs(n) - M.W / 2))
    ax1.fill_between(n, 0, z, color=C_HILL)
    ax1.plot(n, z, color="#6b4f2a", lw=1.2)
    ax1.text(0, zc + 6, T("水路(s = 500 m)", "channel (s = 500 m)"), ha="center", fontsize=8)
    ax1.text(420, 56, "1 : 20", fontsize=8)
    ax1.set_xlabel("n (m)")
    ax1.set_ylabel(T("標高 (m)", "elevation (m)"))
    ax1.set_title(T("(b) 横断(s = 500 m)と縦断", "(b) Cross-section (s = 500 m) and long profile"), fontsize=9)
    ax1.set_ylim(0, 75)
    s_hill = M.L + M.L_EXT
    s = np.linspace(0, s_hill + 120, 700)
    zch = M.Z_OUT + M.S_C * (M.L - s)
    zft = np.full_like(s, M.Z_OUT + M.S_C * M.L + M.D_UP)
    ax2.plot(s[s <= M.L], zch[s <= M.L], color="#1f3f8b", lw=1.4, label=T("水路床(1 : 50)", "channel bed (1 : 50)"))
    ax2.plot(s[s <= s_hill], zft[s <= s_hill], color="#6b4f2a", lw=1.4, label=T("斜面の脚(水平)", "hillslope foot (level)"))
    ax2.plot(s[(s > M.L) & (s <= s_hill + 60)], zch[(s > M.L) & (s <= s_hill + 60)], color=C_EXT, lw=1.4, label=T("下流の区間と延長", "downstream section and extension"))
    ax2.axhline(M.H_SEA, color=C_SEA, lw=1.4, ls="--", label=T("海の水位 1 m", "sea level 1 m"))
    ax2.axvline(M.L, color="k", lw=0.8, ls="--")
    ax2.axvline(s_hill, color="k", lw=0.8, ls=":")
    ax2.annotate("1 m", xy=(0, M.Z_OUT + M.S_C * M.L + 0.5), xytext=(60, M.Z_OUT + M.S_C * M.L + 4), fontsize=8, arrowprops=dict(arrowstyle="-", color="k", lw=0.5))
    ax2.annotate("21 m", xy=(M.L - 110, M.Z_OUT + 10), fontsize=8)
    ax2.set_xlabel("s (m)")
    ax2.set_ylabel(T("標高 (m)", "elevation (m)"))
    ax2.set_ylim(0, 35)
    ax2.legend(fontsize=7, loc="upper right")
    ax2.grid(alpha=0.3)


def panel_grid(ax, theta, dx=20.0):
    """出口付近の格子 (x, y) に流域の輪郭を重ね、セルの種類で塗る。"""
    nx, ny, ox, oy, c, sn, s_end = M.frame(dx, theta)
    _, kind, s, n = M.grid(dx, theta)
    # 出口の近く(s = L − 160 〜 L + 100、|n| < 170)のセルだけ描く
    sel = (s > M.L - 170) & (s < M.L + 120) & (np.abs(n) < 190)
    jj, ii = np.nonzero(sel)
    for i, j in zip(ii, jj):
        ax.add_patch(Rectangle((i * dx, j * dx), dx, dx, facecolor=kind_color(kind[j, i]), edgecolor="0.5", lw=0.3))
    # 流域の輪郭と水路の縁、出口の線
    def xy(ss, nn):
        return ss * c + nn * sn + ox, -ss * sn + nn * c + oy
    for nn in (-M.W / 2, M.W / 2):
        ax.plot(*zip(xy(M.L - 170, nn), xy(M.L + 120, nn)), color="#1f3f8b", lw=1.0)
    ax.plot(*zip(xy(M.L, -190), xy(M.L, 190)), color="k", lw=1.0, ls="--")
    xs, ys = xy(np.array([M.L - 170, M.L + 120, M.L + 120, M.L - 170]), np.array([-190, -190, 190, 190]))
    ax.set_xlim(xs.min(), xs.max())
    ax.set_ylim(ys.min(), ys.max())
    ax.set_aspect("equal")
    x0, y0 = xy(M.L - 150, -150)
    for (ds_, dn_, lab) in ((60, 0, "s"), (0, 60, "n")):
        x1, y1 = xy(M.L - 150 + ds_, -150 + dn_)
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="-|>", color="k"))
        ax.text(x1, y1, lab, fontsize=9)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(T(f"(c) 格子 20 m、向き {theta:g}°(出口付近)", f"(c) 20 m grid, orientation {theta:g}° (near the outlet)"), fontsize=9)


def panel_theory(ax):
    a = np.loadtxt("data/analytic.csv", delimiter=",", comments="#")
    t = a[:, 0]
    ax.plot(t, a[:, 3], color="k", lw=1.8, label=T("出口(水路の運動学的波。特性曲線の数値積分)", "outlet (channel kinematic wave; characteristics)"))
    ax.plot(t, a[:, 2], color="#2b8a3e", lw=1.8, ls="--", label=T("斜面の脚(1 側 × 1000 m。閉じた式)", "hillslope foot (one side × 1000 m; closed form)"))
    ax.axvspan(0, M.T_RAIN, color="#9ecae1", alpha=0.3)
    ax.text(45, 0.3, T("雨 10.8 mm/h", "rain 10.8 mm/h"), ha="center", fontsize=8)
    ax.axhline(4.86, color="0.6", lw=0.8)
    ax.text(150, 4.9, "4.86 m³/s = i (2BL + WL)", fontsize=8, ha="center")
    ax.axhline(2.40, color="0.6", lw=0.8)
    ax.text(150, 2.45, "2.40 m³/s = i B L", fontsize=8, ha="center")
    ax.axvline(29.4, color="#2b8a3e", lw=0.8, ls=":")
    ax.text(30.5, 1.2, T("t_e = 29.4 分", "t_e = 29.4 min"), fontsize=8, color="#2b8a3e")
    ax.set_xlabel(T("時間 (分)", "time (min)"))
    ax.set_ylabel(T("流量 (m³/s)", "discharge (m³/s)"))
    ax.set_xlim(0, 180)
    ax.set_ylim(0, 5.4)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7, loc="upper right")
    ax.set_title(T("(d) 運動学的波の理論解", "(d) Kinematic-wave theory"), fontsize=9)


def main():
    fig = plt.figure(figsize=(14, 9.2), constrained_layout=True)
    gs = fig.add_gridspec(2, 4, height_ratios=[1.25, 1.0])
    panel_plan(fig.add_subplot(gs[0, :2]))
    panel_sections(fig.add_subplot(gs[0, 2]), fig.add_subplot(gs[0, 3]))
    panel_grid(fig.add_subplot(gs[1, 0]), 0.0)
    panel_grid(fig.add_subplot(gs[1, 1]), 45.0)
    panel_theory(fig.add_subplot(gs[1, 2:]))
    fig.savefig(f"{FIGDIR}/setup.png", dpi=110)
    print(f"{FIGDIR}/setup.png")


if __name__ == "__main__":
    main()
