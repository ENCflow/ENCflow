#!/usr/bin/env python3
# examples/delta の図化: 堆積厚(Z − Z0000)の時間発展、最終地形・水深・流速・泥割合、
#   デルタ体積と前進距離の時系列。使い方: python3 plot_results.py <case>(base|baseqb|sand|mud|varq|fix|wave|wfsed)
#   result_<case>/ を読み、fig_<case>_evolution.png・fig_<case>_final.png・fig_<case>_timeseries.png と
#   timeseries_<case>.csv を書く。python3 plot_results.py <case> en で英語ラベル版の PNG を en/figs/ に書く
#   (basename は同じ。timeseries_<case>.csv はケース直下のまま)。
#   python3 plot_results.py mechanism は機構の模式図 figs/mechanism.png を、setup は設定の図 figs/setup.png
#   (make_init.py の初期地形から)を書く。どちらも計算結果を使わない。en を足すと en/figs/ に英語版を書く。
import sys, os, csv, glob, re
import numpy as np
import matplotlib
matplotlib.use("Agg")
EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


ARGS = [a for a in sys.argv[1:] if a != "en"]
FIGDIR = "en/figs" if EN else "."
matplotlib.rcParams["axes.unicode_minus"] = False
if EN:
    matplotlib.rcParams["font.family"] = ["DejaVu Sans"]
else:
    for f in ("IPAPGothic", "IPAGothic", "Noto Sans CJK JP", "WenQuanYi Zen Hei"):   # 日本語ラベル(無ければ既定フォント)
        try:
            import matplotlib.font_manager as fm
            if any(x.name == f for x in fm.fontManager.ttflist):
                matplotlib.rcParams["font.family"] = f; break
        except Exception:
            pass
import matplotlib.pyplot as plt

# ---------------------------------------------------------------- 模式図・設定の図(計算結果を使わない)
#   python3 plot_results.py mechanism|setup [en]。既定は figs/、en では en/figs/ に書く
from matplotlib.patches import Polygon, Ellipse, Rectangle, FancyArrowPatch
SCHEMDIR = "en/figs" if EN else "figs"
C_SEA, C_LAND, C_WATER = "#d6e9f5", "#e3d3ad", "#3d85c6"
C_SAND, C_MUD, C_VEG = "#f1c55e", "#9c7a4c", "#3c8d3c"
C_WAVE, C_SED, C_GREY = "#1f3f7a", "#c0392b", "0.45"


def _smooth(pts, n=200):
    """折れ線を Catmull-Rom で滑らかにする。"""
    p = np.asarray(pts, float)
    p = np.vstack([2 * p[0] - p[1], p, 2 * p[-1] - p[-2]])
    out = []
    for k in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[k - 1], p[k], p[k + 1], p[k + 2]
        for t in np.linspace(0, 1, max(n // (len(p) - 3), 4), endpoint=False):
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(p[-2])
    return np.array(out)


def _line(ax, pts, color, lw, z=3, ls="-", alpha=1.0):
    c = _smooth(pts)
    ax.plot(c[:, 0], c[:, 1], color=color, lw=lw, ls=ls, solid_capstyle="round", zorder=z, alpha=alpha)


def _blob(ax, cx, cy, rx, ry, color, z=2, alpha=1.0, seed=0, amp=0.08, ec="none", lw=0.0):
    th = np.linspace(0, 2 * np.pi, 120)
    rng = np.random.default_rng(seed)
    ph = rng.uniform(0, 2 * np.pi, 3)
    r = 1 + amp * (np.sin(3 * th + ph[0]) + 0.6 * np.sin(5 * th + ph[1]) + 0.4 * np.sin(8 * th + ph[2]))
    ax.add_patch(Polygon(np.c_[cx + rx * r * np.cos(th), cy + ry * r * np.sin(th)], closed=True,
                         fc=color, ec=ec, lw=lw, alpha=alpha, zorder=z))


def _arrow(ax, x0, y0, x1, y1, color, lw=1.6, z=6, style="-|>", ms=10, ls="-"):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle=style, mutation_scale=ms,
                                 color=color, lw=lw, zorder=z, linestyle=ls, shrinkA=0, shrinkB=0))


def _label(ax, x, y, s, size=8, color="k", ha="left", va="center", z=8, **kw):
    ax.text(x, y, s, fontsize=size, color=color, ha=ha, va=va, zorder=z, **kw)


def _plan(ax, title, river=True, coast=2.0, grey=False):
    """平面の模式(西 = 陸と川、東 = 海。上が北)。"""
    ax.set_xlim(0, 10)
    ax.set_ylim(-5, 5)
    ax.set_aspect("equal")
    ax.add_patch(Rectangle((0, -5), 10, 10, fc=C_SEA, ec="none", zorder=0))
    ax.add_patch(Rectangle((0, -5), coast, 10, fc=C_LAND, ec="none", zorder=1))
    if river:
        ax.add_patch(Rectangle((0, -0.32), coast + 0.05, 0.64, fc=C_WATER, ec="none", zorder=3))
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color("0.3")
    ax.set_title(title, fontsize=9.5, loc="left", color=C_GREY if grey else "k")


def _tree(ax, x, y, ang, length, depth, lw, tips, spread=26.0, rmax=3.2, seed=1):
    """分岐を繰り返す分流路(砂の扇)。"""
    rng = np.random.default_rng(seed + depth * 7 + int(abs(ang) * 3))
    a = np.deg2rad(ang)
    x1, y1 = x + length * np.cos(a), y + length * np.sin(a)
    if np.hypot(x1 - 2.0, y1) > rmax:
        s = rmax / np.hypot(x1 - 2.0, y1)
        x1, y1 = 2.0 + (x1 - 2.0) * s, y1 * s
    _line(ax, [(x, y), ((x + x1) / 2 + 0.05 * rng.normal(), (y + y1) / 2 + 0.05 * rng.normal()), (x1, y1)],
          C_WATER, lw, z=4)
    if depth == 0 or np.hypot(x1 - 2.0, y1) > rmax - 0.25:
        tips.append((x1, y1))
        return
    for sgn in (-1, 1):
        _tree(ax, x1, y1, ang + sgn * spread * (0.8 + 0.4 * rng.random()), length * 0.72, depth - 1,
              max(lw * 0.7, 0.8), tips, spread, rmax, seed)


def _panel_section(ax):
    """(a) 河口の縦断: 噴流の減速、河口砂州(頂部・前置斜面)、泥のプロデルタ。"""
    x = np.linspace(0, 10, 600)
    xm = 3.0
    bed0 = np.where(x <= xm, -0.82 - 0.05 * x, np.where(x <= xm + 1.2, -0.97 - 1.23 * (x - xm) / 1.2, -2.2))
    xs = np.array([xm, xm + 0.6, xm + 1.5, xm + 1.8, xm + 2.7])
    zs = np.array([-0.97, -0.55, -0.22, -0.42, -2.2])
    top = np.interp(x, xs, zs)
    sand = np.where((x >= xm) & (x <= xs[-1]), np.maximum(top, bed0), np.nan)
    mud = np.where(x >= xs[-1] - 0.35, -2.2 + 0.13 * np.exp(-np.maximum(x - xs[-1] + 0.35, 0) / 2.0), np.nan)
    mud = np.where(~np.isnan(mud), np.maximum(mud, np.where(np.isnan(sand), -9, sand)), np.nan)
    surf = np.where(np.isnan(sand), np.where(np.isnan(mud), bed0, mud), sand)
    ax.fill_between(x, -2.6, bed0, color=C_LAND, lw=0, zorder=1)
    ax.fill_between(x, surf, 0, where=x >= xm, color=C_SEA, lw=0, zorder=0.5)
    ax.fill_between(x, bed0, 0, where=x <= xm, color=C_WATER, alpha=0.55, lw=0, zorder=0.5)
    # 泥の濁り(沖へ薄くなる)
    xx, zz = np.meshgrid(np.linspace(xm, 10, 300), np.linspace(-2.2, 0, 120))
    a = 0.38 * np.exp(-(xx - xm) / 2.6) * (zz > np.interp(xx, x, surf))
    rgba = np.zeros(xx.shape + (4,))
    rgba[..., :3] = matplotlib.colors.to_rgb(C_MUD)
    rgba[..., 3] = a
    ax.imshow(rgba, extent=[xm, 10, -2.2, 0], origin="lower", aspect="auto", zorder=0.8, interpolation="bilinear")
    ax.fill_between(x, bed0, mud, where=~np.isnan(mud), color=C_MUD, lw=0, zorder=3)
    ax.fill_between(x, bed0, sand, where=~np.isnan(sand), color=C_SAND, lw=0, zorder=3)
    ax.plot(x, bed0, color="0.3", lw=0.8, ls=(0, (2, 2)), zorder=4)
    ax.plot(x, surf, color="0.15", lw=1.0, zorder=4)
    ax.plot([0, 10], [0, 0], color=C_WATER, lw=1.3, zorder=4)
    ax.plot([xm, xm], [-2.6, 0.75], color="k", lw=0.6, ls="--", zorder=4)
    _arrow(ax, 0.35, -0.42, 2.6, -0.42, "white", lw=2.6, ms=14)
    for x0, L in ((3.4, 1.15), (5.0, 0.75), (6.35, 0.45), (7.5, 0.28), (8.5, 0.16)):
        _arrow(ax, x0, -0.1, x0 + L, -0.1, C_WATER, lw=2.0, ms=10)
    _label(ax, xm + 0.06, 0.62, T("河口", "mouth"), size=8)
    _label(ax, 0.3, 0.35, T("川(砂と泥を運ぶ)", "river (carries sand and mud)"), size=8.5)
    _label(ax, 3.5, 0.35, T("流れは海に出て広がり、遅くなる", "the flow spreads into the sea and slows down"),
           size=8.5, color=C_WATER)
    _label(ax, 5.55, -0.95, T("砂は河口のすぐ前に積もる\n(河口砂州。沖側は急な斜面)",
                               "sand settles just off the mouth\n(mouth bar; steep seaward slope)"), size=8)
    _arrow(ax, 5.5, -0.82, 4.6, -0.3, "0.2", lw=0.8, ms=7)
    _label(ax, 6.7, -1.62, T("泥はゆっくり沈み、沖まで運ばれて\n薄く広く積もる(プロデルタ)",
                              "mud settles slowly, travels offshore and\nforms a thin, wide layer (prodelta)"),
           size=8, color="#5b4325")
    _arrow(ax, 7.9, -1.9, 8.1, -2.1, "#5b4325", lw=0.8, ms=7)
    _label(ax, 0.3, -2.35, T("河床(削れる)", "river bed (erodible)"), size=7.5, color="0.3")
    _label(ax, 3.9, -2.42, T("点線 = 元の海底", "dotted = original bed"), size=7.5, color="0.3")
    _label(ax, 9.9, 0.08, T("海面", "sea level"), size=7.5, ha="right", va="bottom", color=C_WATER)
    ax.set_xlim(0, 10)
    ax.set_ylim(-2.6, 0.75)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(T("(a) 河口で起きること(縦断。base)", "(a) What happens at the mouth (section; base)"),
                 fontsize=9.5, loc="left")


def _panel_bifurcation(ax):
    """(b) 河口砂州で分岐し、ローブが伸び、流路が乗り換える(平面)。"""
    _plan(ax, T("(b) 河口砂州・分岐・ローブ(base)", "(b) Mouth bar, bifurcation, lobes (base)"))
    _blob(ax, 4.3, 0.2, 2.9, 3.6, C_SAND, z=1.5, alpha=0.35, seed=3, amp=0.05)        # 水中の前縁
    _blob(ax, 4.0, 2.0, 2.1, 1.25, C_SAND, z=2, seed=4, amp=0.07)                     # 北のローブ
    _blob(ax, 3.6, -1.7, 1.6, 1.05, C_SAND, z=2, seed=5, amp=0.07)                    # 南のローブ
    _blob(ax, 3.15, 0.0, 0.55, 0.62, C_SAND, z=3.5, seed=6, amp=0.04, ec="0.35", lw=0.6)  # 河口砂州
    _line(ax, [(2.0, 0.18), (2.7, 0.55), (3.5, 1.1), (4.5, 1.9), (5.4, 2.5)], C_WATER, 3.2)
    _line(ax, [(2.0, -0.18), (2.7, -0.55), (3.4, -1.1), (4.2, -1.65), (4.9, -2.0)], C_WATER, 3.0)
    _blob(ax, 5.6, 2.62, 0.28, 0.3, C_SAND, z=3.5, seed=7, amp=0.04, ec="0.35", lw=0.5)
    _line(ax, [(5.35, 2.5), (5.75, 3.0), (6.3, 3.5)], C_WATER, 2.0)
    _line(ax, [(5.35, 2.5), (5.95, 2.4), (6.5, 2.1)], C_WATER, 2.0)
    _line(ax, [(2.25, -0.25), (2.6, -1.4), (3.0, -2.7), (3.4, -3.8)], C_WATER, 2.0, ls=(0, (3, 2)), alpha=0.9)
    _label(ax, 3.2, -0.05, "①", size=9, ha="center")
    _label(ax, 5.7, 0.75, T("① 河口砂州", "① mouth bar"), size=8)
    _arrow(ax, 5.65, 0.7, 3.75, 0.1, "0.25", lw=0.7, ms=7)
    _label(ax, 4.6, 1.15, "②", size=9, ha="center")
    _label(ax, 6.0, -0.45, T("② 砂州の両脇へ\n   分岐する", "② flow splits\n   around the bar"), size=8)
    _label(ax, 6.65, 3.75, T("③ ローブが伸び\n   また分岐する", "③ lobes extend\n   and split again"), size=8)
    _label(ax, 3.55, -3.95, T("④ 流路の乗り換え\n   (短い経路へ)", "④ avulsion\n   (to a shorter path)"), size=8)
    _blob(ax, 7.3, 0.0, 1.6, 2.6, C_MUD, z=1.2, alpha=0.13, seed=8, amp=0.06)
    _label(ax, 7.9, -2.2, T("泥", "mud"), size=8, color="#5b4325")


def _panel_sand(ax):
    _plan(ax, T("(c) 砂の多いデルタ(sand)", "(c) Sand-rich delta (sand)"))
    th = np.linspace(-np.pi / 2, np.pi / 2, 200)
    r = 2.75 + 0.16 * np.sin(9 * th) + 0.09 * np.sin(17 * th + 1)
    ax.add_patch(Polygon(np.c_[2.0 + r * np.cos(th), r * np.sin(th)], closed=True, fc=C_SAND, ec="none",
                         zorder=2))
    ax.add_patch(Polygon(np.c_[2.0 + (r + 0.6) * np.cos(th), (r + 0.6) * np.sin(th)], closed=True, fc=C_SAND,
                         ec="none", alpha=0.35, zorder=1.5))
    tips = []
    _tree(ax, 2.0, 0.0, 0.0, 0.95, 4, 2.6, tips, spread=36.0, rmax=2.8, seed=2)
    _blob(ax, 6.6, 0.0, 1.3, 3.4, C_MUD, z=1.2, alpha=0.10, seed=9, amp=0.05)
    _label(ax, 5.6, 4.35, T("短い分流路が多数", "many short distributaries"), size=8)
    _label(ax, 5.6, -4.35, T("半円の扇状", "semicircular fan"), size=8)


def _panel_mud(ax):
    _plan(ax, T("(d) 泥の多いデルタ(mud)", "(d) Mud-rich delta (mud)"))
    _blob(ax, 6.2, 0.4, 3.6, 3.9, C_MUD, z=1.1, alpha=0.16, seed=10, amp=0.06)
    fingers = [[(2.0, 0.0), (3.6, 0.15), (5.6, 0.55), (7.6, 0.9), (9.2, 1.4)],
               [(4.6, 0.3), (5.6, 1.4), (6.6, 2.6), (7.6, 3.7)],
               [(3.3, 0.05), (4.3, -0.9), (5.4, -2.0), (6.4, -3.2)]]
    for f in fingers:
        _line(ax, f, C_SAND, 11, z=2)
        _line(ax, f, "#c9a24a", 11, z=1.9, alpha=0.5)
    for f, w in zip(fingers, (2.6, 2.0, 2.0)):
        _line(ax, f, C_WATER, w, z=4)
    _label(ax, 5.0, -3.9, T("少数の長い分流路が\n沖へ伸びる(鳥趾状)", "a few long channels\nreach offshore\n(bird's-foot)"),
           size=8)
    _label(ax, 2.3, 3.6, T("泥の岸が流路を\n固定する", "muddy banks hold\nthe channels"), size=8)
    _label(ax, 8.2, -1.5, T("泥", "mud"), size=8, color="#5b4325")


def _panel_veg(ax):
    _plan(ax, T("(e) 出水と植生(varq・fix)", "(e) Floods and vegetation (varq, fix)"))
    _blob(ax, 3.7, 0.1, 2.0, 3.0, C_SAND, z=1.5, alpha=0.35, seed=12, amp=0.05)
    bars = [(3.0, 1.2, 0.55, 0.85), (3.15, -1.15, 0.6, 0.8), (4.2, 0.05, 0.5, 0.65), (4.25, 2.15, 0.4, 0.55),
            (4.25, -2.2, 0.45, 0.6)]
    rng = np.random.default_rng(5)
    for k, (cx, cy, rx, ry) in enumerate(bars):
        _blob(ax, cx, cy, rx, ry, C_SAND, z=2, seed=20 + k, amp=0.06, ec="0.4", lw=0.5)
        n = 9
        px = cx + rx * 0.7 * rng.uniform(-1, 1, n)
        py = cy + ry * 0.7 * rng.uniform(-1, 1, n)
        ax.scatter(px, py, s=9, color=C_VEG, zorder=3, lw=0)
    _line(ax, [(2.0, 0.12), (2.6, 0.35), (3.6, 0.7), (4.6, 1.15), (5.2, 1.4)], C_WATER, 2.6)
    _line(ax, [(2.0, -0.12), (2.6, -0.3), (3.6, -0.65), (4.6, -1.1), (5.2, -1.5)], C_WATER, 2.6)
    _line(ax, [(3.6, 0.7), (3.75, 1.6), (4.0, 2.7)], C_WATER, 1.6)
    _line(ax, [(3.6, -0.65), (3.8, -1.7), (4.05, -2.9)], C_WATER, 1.6)
    # 流量の繰り返し(出水と低水)
    tx = np.array([5.6, 6.1, 6.15, 6.65, 6.7, 7.2, 7.25, 7.75, 7.8, 8.3, 8.35, 8.85, 8.9, 9.4])
    ty = np.array([4.4, 4.4, 3.7, 3.7, 4.4, 4.4, 3.7, 3.7, 4.4, 4.4, 3.7, 3.7, 4.4, 4.4])
    ax.plot(tx, ty, color=C_WATER, lw=1.3, zorder=5)
    _label(ax, 5.55, 4.4, T("出水", "flood"), size=7.5, ha="right")
    _label(ax, 5.55, 3.7, T("低水", "low flow"), size=7.5, ha="right")
    _label(ax, 5.35, -0.15, T("低水期に現れた砂州に\n植生(緑)が根付く\n→ 削られにくい",
                              "vegetation (green) takes\nroot on bars exposed at\nlow flow → harder to erode"),
           size=8)
    _label(ax, 5.35, -2.6, T("冠水が続くと弱まる。\n分流路の位置が安定する", "weakens if submerged long;\nchannels stay in place"),
           size=8)


def _panel_wave(ax):
    _plan(ax, T("(f) 波の影響(wave・wfsed)", "(f) Wave influence (wave, wfsed)"))
    # 前縁が滑らかな弧状の陸地と、風下(北)へ伸びる砂嘴
    th = np.linspace(-np.pi / 2, np.pi / 2, 200)
    r = 2.0 + 0.55 * np.cos(th - 0.25)
    xs, ys = 2.0 + r * np.cos(th) * 0.95, -0.15 + 1.25 * r * np.sin(th)
    ax.add_patch(Polygon(np.c_[xs, ys], closed=True, fc=C_SAND, ec="none", zorder=2))
    ax.add_patch(Polygon(np.c_[2.0 + 1.3 * (xs - 2.0), -0.15 + 1.22 * (ys + 0.15)], closed=True, fc=C_SAND,
                         ec="none", alpha=0.32, zorder=1.5))
    _line(ax, [(2.45, 2.4), (2.55, 3.1), (2.5, 3.8), (2.38, 4.5)], C_SAND, 6, z=2)   # 砂嘴
    _line(ax, [(2.0, 0.0), (2.8, 0.05), (3.6, 0.15)], C_WATER, 2.6)
    # 波の峰(進む向き 150°: 東南東から北西へ)
    d = np.array([np.cos(np.deg2rad(150)), np.sin(np.deg2rad(150))])
    c = np.array([-d[1], d[0]])
    clip = Rectangle((6.0, -5.0), 4.0, 8.2, transform=ax.transData)
    for s in np.arange(-4, 5) * 0.85:
        p0 = np.array([8.4, -0.8]) + s * d
        seg = np.array([p0 - 6 * c, p0 + 6 * c])
        ln, = ax.plot(seg[:, 0], seg[:, 1], color=C_WAVE, lw=1.0, zorder=3)
        ln.set_clip_path(clip)
    _arrow(ax, 9.6, 3.55, 9.6 + 2.0 * d[0], 3.55 + 2.0 * d[1], C_WAVE, lw=2.0, ms=13)
    _label(ax, 9.9, 4.95, T("波の進む向き", "wave direction"), size=7.5, ha="right", va="top", color=C_WAVE)
    # 沿岸漂砂(砕波帯で岸沿いに北へ)
    for a0, a1 in ((-62, -32), (-12, 18), (30, 58)):
        t0, t1 = np.deg2rad(a0), np.deg2rad(a1)
        rr = lambda t: 2.0 + 0.55 * np.cos(t - 0.25) + 0.35
        p0 = (2.0 + rr(t0) * np.cos(t0) * 0.95, -0.15 + 1.25 * rr(t0) * np.sin(t0))
        p1 = (2.0 + rr(t1) * np.cos(t1) * 0.95, -0.15 + 1.25 * rr(t1) * np.sin(t1))
        ax.add_patch(FancyArrowPatch(p0, p1, connectionstyle="arc3,rad=0.15", arrowstyle="-|>",
                                     mutation_scale=10, color=C_SED, lw=1.8, zorder=6))
    _arrow(ax, 2.85, 2.5, 2.85, 4.3, C_SED, lw=1.8, ms=10)
    _label(ax, 3.05, 4.65, T("風下へ砂嘴", "spit grows\ndowndrift"), size=8, va="top")
    _label(ax, 5.0, 4.75, T("沿岸漂砂\n(砕波帯で\n岸沿いに)", "longshore\ntransport\n(surf zone)"), size=8,
           color=C_SED, va="top")
    _arrow(ax, 5.35, 3.35, 4.45, 2.35, C_SED, lw=0.7, ms=6)
    _label(ax, 2.3, -4.4, T("前縁は滑らかな弧状", "smooth arcuate front"), size=8)
    _label(ax, 1.0, 4.75, T("↑ 北\n(風下)", "↑ north\n(downdrift)"), size=7.5, color="0.25", va="top", ha="center")


def _panel_tide(ax):
    _plan(ax, T("(g) 潮汐の影響(この例題では計算していない)", "(g) Tidal influence (not computed here)"),
          river=False, coast=0.0, grey=True)
    # 海へ広がる漏斗状の河口
    xs = np.linspace(0, 10, 100)
    half = 0.35 + 0.0045 * xs ** 3.1
    top, bot = np.minimum(half, 5), -np.minimum(half, 5)
    ax.fill_between(xs, top, 5, color=C_LAND, zorder=1, lw=0)
    ax.fill_between(xs, -5, bot, color=C_LAND, zorder=1, lw=0)
    for (cx, cy, rx, ry) in ((4.2, 0.25, 0.9, 0.22), (5.6, -0.55, 1.15, 0.28), (6.0, 0.95, 1.1, 0.25),
                             (7.4, -1.6, 1.3, 0.3), (7.6, 0.2, 1.4, 0.32), (7.8, 2.0, 1.2, 0.28),
                             (9.0, -0.7, 1.0, 0.3)):
        ax.add_patch(Ellipse((cx, cy), 2 * rx, 2 * ry, fc=C_SAND, ec="0.45", lw=0.5, zorder=2))
    for y0 in (-0.12, 1.45, -1.05):
        _arrow(ax, 4.6 + 0.3 * abs(y0), y0, 6.3 + 0.3 * abs(y0), y0, C_WAVE, lw=1.4, style="<|-|>", ms=9)
    _label(ax, 1.0, 3.2, T("海へ広がる\n漏斗状の河口", "funnel-shaped mouth\nwidening seaward"), size=8, color="0.25")
    _label(ax, 3.3, -3.4, T("上げ潮・下げ潮で\n流れが往復する", "flow reverses with\nflood and ebb tides"), size=8,
           color=C_WAVE)
    _label(ax, 6.3, 3.6, T("流れに沿う\n細長い砂州", "bars elongated\nalong the flow"), size=8, color="0.25")


def mechanism():
    """機構の模式図(計算結果を使わない)。figs/mechanism.png(en は en/figs/)。"""
    fig = plt.figure(figsize=(16, 8.4))
    gs = fig.add_gridspec(2, 4, hspace=0.18, wspace=0.06, top=0.9, bottom=0.02, left=0.01, right=0.99)
    _panel_section(fig.add_subplot(gs[0, 0:2]))
    _panel_bifurcation(fig.add_subplot(gs[0, 2]))
    _panel_sand(fig.add_subplot(gs[0, 3]))
    _panel_mud(fig.add_subplot(gs[1, 0]))
    _panel_veg(fig.add_subplot(gs[1, 1]))
    _panel_wave(fig.add_subplot(gs[1, 2]))
    _panel_tide(fig.add_subplot(gs[1, 3]))
    handles = [Rectangle((0, 0), 1, 1, fc=c, alpha=a, ec="none") for c, a in
               ((C_SEA, 1), (C_LAND, 1), (C_WATER, 1), (C_SAND, 1), (C_MUD, 0.6), (C_VEG, 1))]
    handles.append(plt.Line2D([0], [0], color=C_WAVE, lw=1.0))
    handles.append(plt.Line2D([0], [0], color=C_SED, lw=1.8))
    fig.legend(handles, [T("海", "sea"), T("元の陸地", "original land"), T("川・分流路", "river, distributaries"),
                         T("砂(新しい陸地・砂州。薄い色は水中)", "sand (new land, bars; pale = underwater)"),
                         T("泥(濁り・プロデルタ)", "mud (turbid water, prodelta)"), T("植生", "vegetation"),
                         T("波の峰", "wave crests"), T("砂の運ばれる向き", "sand transport")],
               loc="upper center", ncol=8, fontsize=8.5, frameon=False, bbox_to_anchor=(0.5, 0.995))
    os.makedirs(SCHEMDIR, exist_ok=True)
    fig.savefig(os.path.join(SCHEMDIR, "mechanism.png"), dpi=110)
    plt.close(fig)


# ---------------------------------------------------------------- 設定の図(make_init.py の入力から)
def setup():
    """設定の図(make_init.py が作る初期地形から)。figs/setup.png(en は en/figs/)。"""
    import make_init
    from matplotlib.colors import ListedColormap
    z, sd, rows = make_init.build("base")
    ny, nx = z.shape
    dx = 5.0
    ext = [0, nx * dx, ny * dx, 0]
    fig = plt.figure(figsize=(16, 5.4))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.75, 1.0, 0.75], wspace=0.22, left=0.04, right=0.99, top=0.88,
                          bottom=0.13)
    ax = fig.add_subplot(gs[0, 0])
    depth = np.where(z < 0, -z, np.nan)
    land = np.where(z >= 0, 1.0, np.nan)
    ax.imshow(land, extent=ext, cmap=ListedColormap([C_LAND]), vmin=0, vmax=1)
    im = ax.imshow(depth, extent=ext, cmap="Blues", vmin=0, vmax=4.0)
    cb = fig.colorbar(im, ax=ax, shrink=0.85, pad=0.02)
    cb.set_label(T("初期の水深 (m)", "initial depth (m)"))
    jc = (min(rows) + max(rows)) / 2 * dx - dx / 2
    _arrow(ax, -0.5, jc, 60, jc, "white", lw=2.2, ms=12)
    ax.annotate(T("西の辺の河道から流入 30 m³/s(泥を含む)。\n砂は入口の河床から(容量給砂)",
                  "inflow 30 m³/s through the channel on the west side (with mud);\nsand from the inlet bed (capacity feed)"),
                xy=(40, jc - 8), xytext=(240, 150), fontsize=8, arrowprops=dict(arrowstyle="-", lw=0.6, color="0.2"))
    ax.text(8, 520, T("陸 +1.5 m\n(削れない)", "land +1.5 m\n(non-erodible)"), fontsize=7.5, ha="left")
    ax.annotate(T("河道 幅 30 m・河床 −1 m・土層 3 m", "channel 30 m wide, bed −1 m, soil 3 m"), xy=(110, jc + 12),
                xytext=(240, 400), fontsize=8, arrowprops=dict(arrowstyle="-", lw=0.6, color="0.2"))
    ax.text(600, 490, T("海盆 水深 2 m(初期水位 0 m。通常のセル)", "basin, depth 2 m (initial level 0 m; ordinary cells)"),
            fontsize=8, ha="center")
    ax.text(985, 300, T("東の辺: 長波放射\n(海面 0 m を保つ)", "east side: long-wave radiation\n(holds sea level 0 m)"),
            fontsize=8, rotation=90, ha="right", va="center")
    ax.text(600, 18, T("北の辺: 壁", "north side: wall"), fontsize=8, ha="center", va="top")
    ax.text(600, 590, T("南の辺: 壁", "south side: wall"), fontsize=8, ha="center", va="bottom")
    ax.set_xlabel("x (m)")
    ax.set_ylabel(T("y (m)(上が北)", "y (m) (north up)"))
    ax.set_title(T("base の地形と境界(baseqb・wave・wfsed も同じ)", "Terrain and boundaries of base (same for baseqb, wave, wfsed)"),
                 fontsize=10)
    # 河道中心の縦断
    ax = fig.add_subplot(gs[0, 1])
    for case, ls, lab in (("base", "-", T("base 系(海盆 2 m、河道 150 m)", "base series (basin 2 m, channel 150 m)")),
                          ("sand", "--", T("sand・mud・varq・fix(海盆 1.5 m、河道 200 m)", "sand, mud, varq, fix (basin 1.5 m, channel 200 m)"))):
        zc, sdc, rc = make_init.build(case)
        j = (min(rc) + max(rc)) // 2 - 1
        xx = (np.arange(zc.shape[1]) + 0.5) * dx
        sel = xx <= 600
        ax.plot(xx[sel], zc[j, sel], "k", ls=ls, lw=1.3, label=lab)
        if case == "base":
            ax.fill_between(xx[sel], zc[j, sel] - sdc[j, sel], zc[j, sel], where=sdc[j, sel] > 0, color=C_SAND, alpha=0.6,
                            lw=0, label=T("可動の土層 3 m(河道。固定給砂の baseqb・wave・wfsed では 0)",
                                          "erodible soil 3 m (channel; 0 in baseqb, wave, wfsed with fixed feed)"))
    ax.axhline(0, color=C_WATER, lw=1.2, label=T("初期水位 0 m(海面)", "initial level 0 m (sea level)"))
    ax.axhline(1.5, color="0.4", lw=1, ls=":", label=T("両岸の陸 +1.5 m", "land on both banks +1.5 m"))
    ax.set_xlim(0, 600)
    ax.set_ylim(-4.6, 3.8)
    ax.set_xlabel(T("x (m)  ← 川   海 →", "x (m)  ← river   sea →"))
    ax.set_ylabel(T("標高 (m)", "elevation (m)"))
    ax.set_title(T("河道の中心の縦断(初期)", "Section along the channel centre (initial)"), fontsize=10)
    ax.legend(fontsize=7.5, loc="upper right")
    ax.grid(alpha=0.3)
    # 領域の大きさ(河口を原点に)
    ax = fig.add_subplot(gs[0, 2])
    doms = ((T("base・baseqb・wave・wfsed", "base, baseqb, wave, wfsed"), 150, 1000, 600, "C0"),
            (T("sand・varq・fix", "sand, varq, fix"), 200, 1200, 1600, "C1"),
            (T("mud", "mud"), 200, 1600, 2600, "C2"))
    for lab, lch, lx, ly, col in doms:
        ax.add_patch(Rectangle((-lch, -ly / 2), lx, ly, fc="none", ec=col, lw=1.6))
        ax.text(-lch + 25, ly / 2 - 35, lab, color=col, fontsize=7.5, ha="left", va="top")
    ax.axvline(0, color="0.3", lw=0.8, ls="--")
    ax.plot([-200, 0], [0, 0], color=C_WATER, lw=2)
    ax.text(10, -60, T("河口", "mouth"), fontsize=8, va="top")
    ax.set_xlim(-300, 1500)
    ax.set_ylim(-1400, 1400)
    ax.set_aspect("equal")
    ax.set_xlabel(T("河口からの距離 (m)", "distance from the mouth (m)"))
    ax.set_title(T("ケースごとの領域", "Domain of each case"), fontsize=10)
    ax.grid(alpha=0.3)
    os.makedirs(SCHEMDIR, exist_ok=True)
    fig.savefig(os.path.join(SCHEMDIR, "setup.png"), dpi=110)
    plt.close(fig)

case = ARGS[0] if ARGS else "base"
if case in ("mechanism", "setup"):
    {"mechanism": mechanism, "setup": setup}[case]()
    sys.exit(0)
d = "result_%s" % case
os.makedirs(FIGDIR, exist_ok=True)


def out(name):                       # 既定はケース直下(従来どおり)。EN では en/figs/
    return os.path.join(FIGDIR, name) if EN else name
pfile = {"base": "param.txt"}.get(case, "param_%s.txt" % case)
ptxt = open(pfile).read()
def pget(key, default):
    m = re.search(r"^\s*%s\s*=\s*([0-9.eE+-]+)" % key, ptxt, re.M)
    return float(m.group(1)) if m else default
DX = pget("lx", 1000.0) / pget("nx", 200.0)
MORFAC = pget("morfac", 100.0)
DT_FILE = pget("dt_file", 3600.0)
LCH = {"base": 150.0, "baseqb": 150.0, "wave": 150.0, "wfsed": 150.0}.get(case, 200.0)
ZSEA = {"base": -2.0, "baseqb": -2.0, "wave": -2.0, "wfsed": -2.0}.get(case, -1.5)

frames = []
fn = os.path.join(d, "FILENUMBER.csv")
if os.path.exists(fn):
    for row in csv.reader(open(fn)):
        if row[0].startswith("#"): continue
        n = int(row[0]); t = float(row[2])
        if n < 9000: frames.append((n, t))
if not frames:   # FILENUMBER.csv は終了時に書かれる。途中なら Z ファイルの連番から復元
    frames = [(int(os.path.basename(f)[1:5]), int(os.path.basename(f)[1:5]) * DT_FILE)
              for f in sorted(glob.glob(os.path.join(d, "Z[0-9][0-9][0-9][0-9].txt")))
              if int(os.path.basename(f)[1:5]) < 9000]
z0 = np.loadtxt(os.path.join(d, "Z0000.txt"))
ny, nx = z0.shape
x = (np.arange(nx) + 0.5) * DX; y = (np.arange(ny) + 0.5) * DX
ext = [0, nx * DX, ny * DX, 0]

def load(pfx, n):
    return np.loadtxt(os.path.join(d, "%s%04d.txt" % (pfx, n)))

# --- 堆積厚の時間発展(6 枚)
sel = frames[1:] if len(frames) > 1 else frames
idx = np.linspace(0, len(sel) - 1, min(6, len(sel))).astype(int)
fig, axs = plt.subplots(2, 3, figsize=(15, 6.5), constrained_layout=True)
for ax, k in zip(axs.flat, idx):
    n, t = sel[k]
    dz = load("Z", n) - z0; h = load("H", n)
    im = ax.imshow(dz, extent=ext, cmap="RdBu_r", vmin=-2, vmax=2)
    ax.contour(x, y, h, levels=[0.05], colors="k", linewidths=0.6)
    ax.set_title(T("地形 %.0f h (水理 %.1f h): Δz (m)", "landform %.0f h (hydraulic %.1f h): Δz (m)") % (t * MORFAC / 3600, t / 3600))
    ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
fig.colorbar(im, ax=axs, shrink=0.8, label="Δz = Z − Z0 (m)")
fig.savefig(out("fig_%s_evolution.png" % case), dpi=110)

# --- 最終: 標高・水深・流速・細粒分
n, t = frames[-1]
z = load("Z", n); h = load("H", n); v = load("V", n)
sf = load("Sf", n) if os.path.exists(os.path.join(d, "Sf%04d.txt" % n)) else None
fig, axs = plt.subplots(2, 2, figsize=(13, 8), constrained_layout=True)
im = axs[0, 0].imshow(z, extent=ext, cmap="terrain", vmin=ZSEA, vmax=1.5)
axs[0, 0].contour(x, y, h, levels=[0.05], colors="k", linewidths=0.6)
axs[0, 0].set_title(T("最終地盤高 Z (m)。黒線 = 汀線 (h = 0.05 m)", "final bed elevation Z (m); black line = shoreline (h = 0.05 m)")); fig.colorbar(im, ax=axs[0, 0])
im = axs[0, 1].imshow(h, extent=ext, cmap="Blues", vmin=0, vmax=-ZSEA + 0.2)
axs[0, 1].set_title(T("最終水深 H (m)", "final depth H (m)")); fig.colorbar(im, ax=axs[0, 1])
im = axs[1, 0].imshow(v, extent=ext, cmap="magma", vmin=0, vmax=1.2)
axs[1, 0].set_title(T("最終流速 |V| (m/s)", "final velocity |V| (m/s)")); fig.colorbar(im, ax=axs[1, 0])
if sf is not None:
    dz = z - z0
    frac = np.where(dz > 0.01, sf / np.maximum(dz, 1e-6), np.nan)
    im = axs[1, 1].imshow(np.clip(frac, 0, 1), extent=ext, cmap="YlOrBr", vmin=0, vmax=1)
    axs[1, 1].set_title(T("堆積物に占める泥(細粒分)の割合 Sf/Δz", "mud (fines) fraction of the deposit Sf/Δz")); fig.colorbar(im, ax=axs[1, 1])
for ax in axs.flat:
    ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
fig.savefig(out("fig_%s_final.png" % case), dpi=110)

# --- 時系列: デルタ体積(堆積 bulk)、陸地の最大前進、陸化面積、浅瀬の面積
rows = []
for n, t in frames:
    dz = load("Z", n) - z0; h = load("H", n)
    dep = dz[dz > 0].sum() * DX * DX
    land = (h < 0.05) & (x[None, :] > LCH)
    xmax = (x[None, :] * land).max() if land.any() else LCH
    shallow = (h < 0.5) & (x[None, :] > LCH + 50.0)
    rows.append((t * MORFAC / 3600, dep, xmax - LCH, land.sum() * DX * DX, shallow.sum() * DX * DX))
rows = np.array(rows)
np.savetxt("timeseries_%s.csv" % case, rows, delimiter=",",
           header="morph_time_h,deposit_bulk_m3,land_advance_m,land_area_m2,shallow_area_m2(h<0.5)", comments="", fmt="%.3f")
fig, axs = plt.subplots(1, 3, figsize=(14, 4), constrained_layout=True)
axs[0].plot(rows[:, 0], rows[:, 1] / 1e3, "o-"); axs[0].set_ylabel(T("堆積体積 (10³ m³ bulk)", "deposit volume (10³ m³ bulk)"))
axs[1].plot(rows[:, 0], rows[:, 2], "o-"); axs[1].set_ylabel(T("河口からの陸地の最大前進 (m)", "maximum land advance from the river mouth (m)"))
axs[2].plot(rows[:, 0], rows[:, 3] / 1e3, "o-", label=T("陸化 (h<0.05)", "emerged land (h<0.05)")); axs[2].plot(rows[:, 0], rows[:, 4] / 1e3, "s-", label=T("浅瀬 (h<0.5)", "shallows (h<0.5)"))
axs[2].set_ylabel(T("面積 (10³ m²)", "area (10³ m²)")); axs[2].legend()
for ax in axs: ax.set_xlabel(T("地形時間 (h)", "landform time (h)")); ax.grid(alpha=0.3)
fig.savefig(out("fig_%s_timeseries.png" % case), dpi=110)
print("final: morph %.0f h, deposit %.0f m3, land advance %.0f m, land area %.0f m2" % (rows[-1, 0], rows[-1, 1], rows[-1, 2], rows[-1, 3]))
