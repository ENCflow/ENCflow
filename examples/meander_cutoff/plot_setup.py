#!/usr/bin/env python3
"""examples/meander_cutoff の機構の模式図と設定の図(計算結果は使わない)。

  python3 plot_setup.py        # figs/mechanism.png, figs/setup.png
  python3 plot_setup.py en     # 英語ラベル版を en/figs/ に描く

  figs/mechanism.png  (a) 出水の越流による短絡(平面の模式)、(b) 河岸の後退による短絡
                      (ループの脚の間の陸を横切る断面の模式)、(c) 短絡の後の旧河道
                      (滞水域と出入口の堆積。三日月湖への途中)
  figs/setup.png      初期地形(河床からの高さ。ループ・最も狭い陸(ループの脚の間と 2 つのループの間)・
                      出水で流れが横切る 3 つの陸)、中心線に沿う両岸の高さ、流入ハイドログラフ 2 種

入力は make_init.py が書く z.txt / h.txt / sd.txt(make で作る)と、make_init.py の中心線。
依存: numpy, matplotlib
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import make_init as mi

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)

C_WATER, C_DEEP, C_LAND, C_SOIL, C_STILL = "#9ecae1", "#3182bd", "#d9c89e", "#c9b48a", "#dfe9f0"
C_FLOOD, C_ERODE, C_NEW, C_PLUG, C_Q = "#6baed6", "#c0392b", "#08519c", "#e6b85c", "#2c7fb8"
MORFAC = 10.0


def _arrow(ax, x0, y0, x1, y1, color, lw=1.6, ms=10, style="-|>", zorder=5):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0), zorder=zorder,
                arrowprops=dict(arrowstyle=style, color=color, lw=lw, shrinkA=0, shrinkB=0, mutation_scale=ms))


def _band(ax, xc, yc, w, **kw):
    """中心線 (xc, yc) に沿う幅 w の帯を描く。"""
    dx, dy = np.gradient(xc), np.gradient(yc)
    n = np.hypot(dx, dy)
    nx, ny = -dy / n, dx / n
    p = np.c_[np.r_[xc + nx * w / 2, (xc - nx * w / 2)[::-1]], np.r_[yc + ny * w / 2, (yc - ny * w / 2)[::-1]]]
    ax.add_patch(Polygon(p, closed=True, **kw))
    return xc + nx * w / 2, yc + ny * w / 2, xc - nx * w / 2, yc - ny * w / 2


def _omega():
    """Ω 形のループ 1 個の中心線: 例題と同じ正弦波生成曲線(ω = 105°、Λ = 320 m)の
    s = 60〜380 m(ループ 1 個)の前後を直線にしたもの。"""
    om, lam = np.radians(105.0), 320.0
    s = np.arange(-20.0, 460.0, 0.5)
    th = np.where((s >= 60) & (s <= 380), om * np.sin(2 * np.pi * (s - 60) / lam), 0.0)
    x = np.cumsum(np.cos(th)) * 0.5
    y = np.cumsum(np.sin(th)) * 0.5
    k1, k2 = np.argmin(abs(s - 112)), np.argmin(abs(s - 328))     # 脚の間の最も狭い所
    xn, yn = 0.5 * (x[k1] + x[k2]), 0.5 * (y[k1] + y[k2])
    return s, x - xn, y - yn, (x[k1] - xn, y[k1] - yn), (x[k2] - xn, y[k2] - yn)


def _frame(ax):
    ax.add_patch(Polygon([[-120, -88], [120, -88], [120, 170], [-120, 170]], closed=True, fc=C_LAND, ec="none", zorder=0))
    ax.set_xlim(-120, 120); ax.set_ylim(-88, 170); ax.set_aspect("equal"); ax.axis("off")


# ---------------------------------------------------------------- 機構の模式図
def _flood_cutoff(ax):
    s, x, y, p1, p2 = _omega()
    _frame(ax)
    ax.add_patch(Polygon([[-75, -40], [75, -40], [70, 30], [30, 55], [-30, 55], [-70, 30]], closed=True,
                         fc=C_FLOOD, ec="none", alpha=0.45, zorder=1))
    _band(ax, x, y, 20.0, fc=C_WATER, ec="k", lw=1.0, zorder=2)
    for sk in (20, 200, 380 + 20):
        k = np.argmin(abs(s - sk))
        _arrow(ax, x[k], y[k], x[k + 30], y[k + 30], C_NEW, lw=1.6, ms=10)
    for dy in (-12, 0, 12):                                       # 脚の間の陸を越える出水の流れ
        _arrow(ax, p1[0] + 4, p1[1] + dy, p2[0] - 4, p2[1] + dy, C_FLOOD, lw=2.2, ms=11)
    ax.text(0, -84, T("出水で冠水した陸を越える流れが、\n脚の間の狭い陸に新流路を刻む",
                      "flood water crossing the inundated land\ncuts a new channel through the narrow neck"),
            fontsize=8, color=C_NEW, ha="center", va="bottom")
    ax.text(0, 150, T("ループ", "loop"), fontsize=9, ha="center")
    ax.set_title(T("(a) 出水の越流による短絡", "(a) Cutoff by flood overflow"), fontsize=10, loc="left")


def _bank_cutoff(ax):
    """ループの脚の間の陸を横切る断面(左右の河道の外岸がこの陸に面する)。"""
    yb = np.array([-30, -22, -22, -18, -12, -10.6, -10, -9.8, 9.8, 10, 10.6, 12, 18, 22, 22, 30])
    zb = np.array([1.6, 1.6, 0.4, -0.2, -1.2, -1.6, 1.6, 1.6, 1.6, 1.6, -1.6, -1.2, -0.2, 0.4, 1.6, 1.6])
    ax.fill_between(yb, -2.4, zb, color=C_SOIL, zorder=1)
    ax.plot(yb, zb, "k-", lw=1.1, zorder=3)
    for side in (-1, 1):
        yw = np.linspace(min(side * 22, side * 10), max(side * 22, side * 10), 40)
        ax.fill_between(yw, np.interp(yw, yb, zb), 0.8, where=np.interp(yw, yb, zb) < 0.8, color=C_WATER, zorder=2)
        ax.plot([side * 22, side * 10.3], [0.8, 0.8], color=C_Q, lw=1.0, zorder=3)
        _arrow(ax, side * 10.6, 0.6, side * 5.0, 0.6, C_ERODE, lw=1.6, ms=10)
        ax.add_patch(Polygon([[side * 10.0, 1.6], [side * 7.0, 1.6], [side * 10.4, -1.2]], closed=True, fc="none",
                             ec=C_ERODE, ls="--", lw=1.0, zorder=4))
    ax.text(0, 1.95, T("脚の間の陸(この例題で幅 22 m)", "land between the limbs (22 m wide here)"), ha="center", fontsize=8)
    ax.text(0, -0.6, T("両側の外岸が\nこの陸に面して後退し、\n陸が切れると短絡", "both outer banks face\nthis land and retreat;\nthe cutoff occurs\nwhen it is breached"),
            ha="center", va="top", fontsize=8, color=C_ERODE)
    ax.text(-26, 0.95, T("水面", "water"), fontsize=7.5, color=C_Q, ha="center")
    ax.text(-16, -1.95, T("外岸の淵", "pool"), fontsize=7.5, color=C_DEEP, ha="center")
    ax.text(16, -1.95, T("外岸の淵", "pool"), fontsize=7.5, color=C_DEEP, ha="center")
    ax.set_xlim(-30, 30); ax.set_ylim(-2.4, 2.5)
    ax.set_xlabel(T("脚を横切る位置 (m)", "position across the limbs (m)"), fontsize=8)
    ax.set_ylabel(T("河床からの高さ (m)", "height above the bed (m)"), fontsize=8)
    ax.tick_params(labelsize=7.5)
    ax.set_title(T("(b) 河岸の後退による短絡(断面の模式)", "(b) Cutoff by bank retreat (schematic section)"), fontsize=10, loc="left")


def _after(ax):
    s, x, y, p1, p2 = _omega()
    _frame(ax)
    loop = (s > 112) & (s < 328)
    _band(ax, x[loop], y[loop], 20.0, fc=C_STILL, ec="k", lw=1.0, zorder=2)
    up = s <= 116; dn = s >= 324
    _band(ax, x[up], y[up], 20.0, fc=C_WATER, ec="k", lw=1.0, zorder=2)
    _band(ax, x[dn], y[dn], 20.0, fc=C_WATER, ec="k", lw=1.0, zorder=2)
    xn = np.linspace(p1[0], p2[0], 20)
    _band(ax, xn, np.linspace(p1[1], p2[1], 20), 20.0, fc=C_WATER, ec="none", zorder=3)
    _arrow(ax, p1[0] - 2, p1[1], p2[0] + 2, p2[1], C_NEW, lw=2.2, ms=12)
    for sk in (20, 400):
        k = np.argmin(abs(s - sk))
        _arrow(ax, x[k], y[k], x[k + 30], y[k + 30], C_NEW, lw=1.6, ms=10)
    for p, sg in ((p1, 1), (p2, -1)):                              # ループの出入口に積もる土砂
        ax.add_patch(plt.Circle((p[0] - sg * 2, p[1] + 16), 8.5, fc=C_PLUG, ec="none", zorder=4))
    ax.text(0, 112, T("旧河道(ループ)は\n滞水域になる", "the old loop\nbecomes still water"), ha="center", fontsize=8.5, color="0.25")
    ax.annotate(T("出入口に\n土砂が積もる\n(塞がると\n三日月湖)", "sediment\nplugs the\nentrances\n(an oxbow\nlake once\nclosed)"),
                xy=(p2[0] + 4, p2[1] + 20), xytext=(56, 40), ha="left", fontsize=8, color="#8a5a00",
                arrowprops=dict(arrowstyle="-", color="#8a5a00", lw=0.8))
    ax.text(0, -84, T("流れは新流路に集まる", "flow concentrates in the new channel"), ha="center", va="bottom", fontsize=8, color=C_NEW)
    ax.set_title(T("(c) 短絡の後(三日月湖への途中)", "(c) After the cutoff (on the way to an oxbow lake)"), fontsize=10, loc="left")


def mechanism():
    fig, axes = plt.subplots(1, 3, figsize=(14.5, 4.9), gridspec_kw=dict(width_ratios=[1.0, 1.15, 1.0]))
    _flood_cutoff(axes[0])
    _bank_cutoff(axes[1])
    _after(axes[2])
    fig.subplots_adjust(left=0.02, right=0.99, top=0.9, bottom=0.12, wspace=0.18)
    fig.savefig(os.path.join(FIGDIR, "mechanism.png"), dpi=110)
    plt.close(fig)


# ---------------------------------------------------------------- 設定の図
# 出水で流れが横切る 3 つの陸の範囲 ((x0, x1), (y0, y1)) m: ループ 1 の脚の間、2 つのループの間、
# ループ 2 の脚の間(plot_results.py の数表と同じ。初期の陸のセルだけを数える)
LANDS_XY = [((100, 120), (55, 90)), ((150, 175), (90, 140)), ((205, 225), (100, 145))]


def loops(h0):
    """plot_results.py と同じ定義のループ: 初期河道のうち y > 70 m(x = 160 m より西がループ 1、東がループ 2)"""
    y = (np.arange(h0.shape[0]) + 0.5) * mi.DX
    return (h0 > 0) & (y[:, None] > 70.0)


def setup():
    z0 = np.loadtxt("z.txt"); h0 = np.loadtxt("h.txt")
    NY, NX = z0.shape
    DX = mi.DX
    x = (np.arange(NX) + 0.5) * DX; y = (np.arange(NY) + 0.5) * DX
    P = np.array([(p[0], p[1] - mi.XMIN, p[2] - mi.YMIN) for p in mi.pts])
    # 各セルの最寄りの中心線の点(河床は路長 s に沿って Z0 − S0 s)。総当たりを行の塊ごとに
    XX, YY = np.meshgrid(x, y)
    cx, cy = XX.ravel(), YY.ravel()
    k = np.empty(cx.size, int)
    for a in range(0, cx.size, 2000):
        d2 = (cx[a:a + 2000, None] - P[None, :, 1]) ** 2 + (cy[a:a + 2000, None] - P[None, :, 2]) ** 2
        k[a:a + 2000] = d2.argmin(axis=1)
    zbed = (mi.Z0 - mi.S0 * P[k, 0]).reshape(z0.shape)
    fig = plt.figure(figsize=(15.0, 6.9))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.5, 1.0], height_ratios=[1.0, 1.0], hspace=0.55, wspace=0.16)
    ax = fig.add_subplot(gs[:, 0])
    hr = np.where(h0 > 0, np.nan, z0 - zbed)
    cm = matplotlib.colors.LinearSegmentedColormap.from_list("land", ["#fffbe8", "#ecdcae", "#c49a5a", "#6b4a26"])
    im = ax.imshow(hr, origin="lower", extent=[0, NX * DX, 0, NY * DX], cmap=cm, vmin=0.5, vmax=3.0)
    ax.imshow(np.where(h0 > 0, 1.0, np.nan), origin="lower", extent=[0, NX * DX, 0, NY * DX], cmap="Blues", vmin=0, vmax=1.6)
    ax.contour(x, y, h0 > 0, levels=[0.5], colors="k", linewidths=0.6)
    ax.axhline(70.0, color="0.3", ls=":", lw=0.9)
    ax.text(343, 72, "y = 70 m", fontsize=7.5, color="0.2", ha="right")
    for (xa, ya) in ((112, 76), (163, 130), (214, 76)):
        ax.plot([xa - 11, xa + 11], [ya, ya], color=C_ERODE, lw=2.0)
    ax.text(163, 186, T("赤線 = 最も狭い陸(幅 22 m)\n左右はループの脚の間、中央は 2 つのループの間",
                        "red = narrowest land (22 m)\nbetween the limbs of each loop (left, right) and between the loops (centre)"),
            fontsize=7.5, color=C_ERODE, ha="center", va="bottom")
    for (xa, xb), (ya, yb) in LANDS_XY:
        ax.plot([xa, xb, xb, xa, xa], [ya, ya, yb, yb, ya], color="0.25", lw=0.8, ls="--")
    for xa, ya, lab in ((112, 132, T("ループ 1", "loop 1")), (214, 89, T("ループ 2", "loop 2"))):
        ax.text(xa, ya, lab, fontsize=8, ha="center", va="center", color="0.1",
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.8))
    _arrow(ax, -14, 40, 2, 40, C_Q, lw=2.0, ms=12)
    ax.text(4, 52, T("流入", "inflow"), color=C_Q, fontsize=8)
    _arrow(ax, NX * DX - 2, 40, NX * DX + 14, 40, C_Q, lw=2.0, ms=12)
    ax.text(NX * DX - 30, 52, T("自由流出", "free outflow"), color=C_Q, fontsize=8)
    for xa in (mi.XFIX_UP, mi.XFIX_UP + mi.LRAMP, NX * DX - mi.XFIX_DN):
        ax.axvline(xa, color="0.45", ls="--", lw=0.7)
    ax.text(mi.XFIX_UP + mi.LRAMP / 2, NY * DX + 2, T("土層厚のランプ 0 → 5 m", "soil-depth ramp 0 → 5 m"), ha="center", fontsize=7.5, va="bottom")
    ax.text(mi.XFIX_UP / 2, NY * DX + 2, T("非侵食", "fixed"), ha="center", fontsize=7, va="bottom")
    ax.text(NX * DX - mi.XFIX_DN / 2, NY * DX + 2, T("非侵食", "fixed"), ha="center", fontsize=7, va="bottom")
    ax.plot([], [], color="0.25", lw=0.8, ls="--", label=T("出水で流れが横切る 3 つの陸(結果の数表)", "the three lands the flood flow crosses (result tables)"))
    ax.legend(fontsize=7, loc="upper center", framealpha=0.95, bbox_to_anchor=(0.5, -0.1), ncol=1)
    ax.set_xlim(-16, NX * DX + 16); ax.set_ylim(0, NY * DX + 10)
    ax.set_xlabel("x (m)", fontsize=8.5); ax.set_ylabel("y (m)", fontsize=8.5); ax.tick_params(labelsize=7.5)
    cb = fig.colorbar(im, ax=ax, shrink=0.6, pad=0.01)
    cb.set_label(T("最寄りの河床からの高さ (m)", "height above the nearest channel bed (m)"), fontsize=8); cb.ax.tick_params(labelsize=7)
    ax.set_title(T("初期地形(青 = 河道、初期水深 0.8 m)", "Initial terrain (blue = channel, initial depth 0.8 m)"), fontsize=10, loc="left")
    # --- 中心線に沿う両岸の高さ ---
    ax = fig.add_subplot(gs[0, 1])
    s = P[:, 0]
    th = np.arctan2(np.gradient(P[:, 2]), np.gradient(P[:, 1]))
    for side, col, lab in ((1, "#1b9e77", T("左岸(流れの向きに左)", "left bank")), (-1, "#d95f02", T("右岸", "right bank"))):
        xb = P[:, 1] - side * np.sin(th) * 12.0
        yb = P[:, 2] + side * np.cos(th) * 12.0
        ib = np.clip((xb / DX).astype(int), 0, NX - 1); jb = np.clip((yb / DX).astype(int), 0, NY - 1)
        hb = z0[jb, ib] - (mi.Z0 - mi.S0 * s)
        ax.plot(s, hb, color=col, lw=1.0, label=lab)
    ax.axhline(0.8, color=C_Q, lw=0.9, ls="--")
    ax.text(88, 0.84, T("初期の水面(水深 0.8 m)", "initial water surface (0.8 m)"), color=C_Q, fontsize=7.5, va="bottom")
    for sa in (220, 380, 540):
        ax.axvline(sa, color="0.75", lw=0.7, zorder=0)
    ax.text(220, 2.75, T("頂部", "apex"), ha="center", fontsize=7)
    ax.text(380, 2.75, T("頂部", "apex"), ha="center", fontsize=7)
    ax.text(540, 2.75, T("頂部", "apex"), ha="center", fontsize=7)
    ax.set_xlim(0, s.max()); ax.set_ylim(0, 3.0)
    ax.set_xlabel(T("中心線に沿う距離 s (m)(河床 = 10 − 0.001 s)", "distance along the centreline s (m) (bed = 10 − 0.001 s)"), fontsize=8)
    ax.set_ylabel(T("中心線から 12 m の陸の高さ\n(河床から、m)", "height of the land 12 m off\nthe centreline (above the bed, m)"), fontsize=8)
    ax.tick_params(labelsize=7.5); ax.legend(fontsize=7, loc="lower right", framealpha=0.95)
    ax.set_title(T("河岸の高さ(近くの河床の最大値 + 1.6 m)", "Bank height (highest nearby bed + 1.6 m)"), fontsize=10, loc="left")
    # --- 流入 ---
    ax = fig.add_subplot(gs[1, 1])
    tg = np.linspace(0, 30, 601)
    qf = np.interp(tg * 60 / MORFAC, [0, 30, 40, 100, 110, 180], [15, 15, 40, 40, 15, 15])
    ax.plot(tg, qf, color=C_Q, lw=1.6, label=T("出水あり(param・param_slump。地形 30 h)", "with a flood (param, param_slump; 30 h)"))
    ax.plot([0, 30], [15, 15], color="0.3", lw=1.2, ls=":", label=T("出水なし: 15 m³/s 一定(地形 180 h)", "no flood: constant 15 m³/s (180 h)"))
    for tk in range(5, 31, 5):
        ax.axvline(tk, color="0.8", lw=0.6, zorder=0)
    ax.set_xlim(0, 30); ax.set_ylim(0, 48)
    sx = ax.secondary_xaxis("top", functions=(lambda t: t * 60 / MORFAC, lambda m: m * MORFAC / 60))
    sx.set_xlabel(T("水理の時間 (分)", "hydraulic time (min)"), fontsize=8); sx.tick_params(labelsize=7)
    ax.set_xlabel(T("地形時間 (h)(morfac = 10。灰色の縦線 = 出力時刻)", "landform time (h) (morfac = 10; grey lines = outputs)"), fontsize=8)
    ax.set_ylabel("Q (m³/s)", fontsize=8.5); ax.tick_params(labelsize=7.5)
    ax.legend(fontsize=7, loc="upper right", framealpha=0.95)
    ax.set_title(T("流入", "Inflow"), fontsize=10, loc="left", pad=20)
    fig.subplots_adjust(left=0.04, right=0.98, top=0.93, bottom=0.17)
    fig.savefig(os.path.join(FIGDIR, "setup.png"), dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    mechanism()
    setup()
    print("figures: %s/mechanism.png %s/setup.png" % (FIGDIR, FIGDIR))
