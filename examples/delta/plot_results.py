#!/usr/bin/env python3
# examples/delta の図化: 堆積厚(Z − Z0000)の時間発展、最終地形・水深・流速・泥割合、
#   デルタ体積と前進距離の時系列。使い方: python3 plot_results.py <case>(base|baseqb|sand|mud|varq|fix|wave|wfsed)
#   result_<case>/ を読み、fig_<case>_evolution.png・fig_<case>_final.png・fig_<case>_timeseries.png と
#   timeseries_<case>.csv を書く。python3 plot_results.py <case> en で英語ラベル版の PNG を en/figs/ に書く
#   (basename は同じ。timeseries_<case>.csv はケース直下のまま)。
#   python3 plot_results.py mechanism は機構の模式図 figs/mechanism.png を、setup は設定の図 figs/setup.png
#   (make_init.py の初期地形から)を書く。どちらも計算結果を使わない。en を足すと en/figs/ に英語版を書く。
#   段 6・7(潮汐): python3 plot_results.py tide(tidedom)は上の 3 図に加えて fig_<case>_phases.png(最後の 1 周期の
#   流れ)と fig_<case>_series.png(水位・河口の流量)を書く。3 図は平均潮位(上げ)のフレームで描く。
#   python3 plot_results.py tidecmp は潮汐なしの基準との比較図 figs/tide_cmp.png(notide と tide)・
#   figs/tidedom_cmp.png(smallq と tidedom)(en は en/figs/)と数表を書く。
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
    _plan(ax, T("(g) 潮汐の影響(tide・tidedom)", "(g) Tidal influence (tide, tidedom)"), river=False, coast=0.0)
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
    ax.add_patch(Rectangle((985, 0), 15, 600, fc="none", ec="#c0392b", lw=1.0, ls="--", hatch="////"))
    ax.text(978, 300, T("東の辺: 長波放射(海面 0 m を保つ)\n段 6・7 は東端 3 列(赤の斜線)を潮位の帯に",
                        "east side: long-wave radiation (holds sea level 0 m);\nstages 6, 7: easternmost 3 columns (red hatch) = tidal strip"),
            fontsize=8, rotation=90, ha="right", va="center")
    ax.text(600, 18, T("北の辺: 壁", "north side: wall"), fontsize=8, ha="center", va="top")
    ax.text(600, 590, T("南の辺: 壁", "south side: wall"), fontsize=8, ha="center", va="bottom")
    ax.set_xlabel("x (m)")
    ax.set_ylabel(T("y (m)(上が北)", "y (m) (north up)"))
    ax.set_title(T("base の地形と境界(段 4〜7 のケースも同じ)", "Terrain and boundaries of base (same for the cases of stages 4–7)"),
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
                            lw=0, label=T("可動の土層 3 m(河道。固定給砂の段 4〜7 では 0)",
                                          "erodible soil 3 m (channel; 0 in stages 4–7 with fixed feed)"))
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
    doms = ((T("段 1・4〜7", "stages 1, 4–7"), 150, 1000, 600, "C0"),
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

# ---------------------------------------------------------------- 段 6(潮汐)の図と集計
#   tide・tidedom は潮の 1/4 周期ごとに出力する(4 枚で 1 周期: 平均潮位の上げ・満潮・平均潮位の下げ・干潮)。
#   堆積・陸化などは平均潮位(上げ)のフレーム(番号が 4 の倍数)で比べる。
TIDE_T = 44712.0                     # M2 の周期 (s)
TIDE_A = 1.0                         # 潮の振幅 (m)
TIDE_PH = 4                          # 1 周期あたりの出力枚数


def read_rec(path):
    """観測点・測線の CSV(# の見出し行、カンマ区切り)を数値の配列で読む。"""
    rows_ = [[float(s) for s in ln.replace(",", " ").split()] for ln in open(path) if ln.strip() and not ln.lstrip().startswith("#")]
    return np.array(rows_)


def tide_metrics(rdir, pfile_, lch=150.0, mouth_q=30.0):
    """1 ケースの最終(平均潮位の上げ)の地形の集計と、河口の流量・干潟の潮の出入りの集計。"""
    ptxt_ = open(pfile_).read()
    dx = float(re.search(r"^\s*lx\s*=\s*([0-9.eE+-]+)", ptxt_, re.M).group(1)) / \
        float(re.search(r"^\s*nx\s*=\s*([0-9.eE+-]+)", ptxt_, re.M).group(1))
    nums = sorted(int(os.path.basename(f)[1:5]) for f in glob.glob(os.path.join(rdir, "Z[0-9][0-9][0-9][0-9].txt"))
                  if int(os.path.basename(f)[1:5]) < 9000)
    tidal = re.search(r"^\s*fn_tide\s*=", ptxt_, re.M) is not None
    nf = max(k for k in nums if k % TIDE_PH == 0) if tidal else max(nums)   # 潮汐は平均潮位(上げ)の最後
    rd = lambda pfx, k: np.loadtxt(os.path.join(rdir, "%s%04d.txt" % (pfx, k)))
    z0, z, h = rd("Z", 0), rd("Z", nf), rd("H", nf)
    sf = rd("Sf", nf)
    xx = (np.arange(z.shape[1]) + 0.5) * dx
    sea = xx[None, :] > lch
    dz = z - z0
    dep = np.where(dz > 0, dz, 0.0)
    m = {"nf": nf, "deposit": dep.sum() * dx * dx, "mud": np.minimum(sf, dep).sum() * dx * dx}
    m["sand"] = m["deposit"] - m["mud"]
    land = (h < 0.05) & sea
    m["land"] = land.sum() * dx * dx
    m["advance"] = ((xx[None, :] * land).max() - lch) if land.any() else 0.0
    built = sea & (dz > 0.05)
    sand_thk = dep - np.minimum(sf, dep)                            # 砂の厚さ(堆積から泥の厚さを除く)
    foot = sea & (sand_thk > 0.3)                                   # 砂 0.3 m 以上の範囲(デルタの砂の本体)
    if foot.any():
        jj = np.where(foot.any(axis=1))[0]
        m["along"] = (jj.max() - jj.min() + 1) * dx                 # 海岸沿いの長さ
        m["across"] = (xx[None, :] * foot).max() - lch               # 河口からの沖への広がり
    m["supra"] = (built & (z >= TIDE_A)).sum() * dx * dx            # 満潮より高い
    m["inter"] = (built & (z > -TIDE_A) & (z < TIDE_A)).sum() * dx * dx   # 干潮と満潮の間(潮間帯の高さ)
    m["above_msl"] = (built & (z > 0.0)).sum() * dx * dx
    fq = os.path.join(rdir, "fluxes", "flux0001.csv")
    if os.path.exists(fq):
        q = read_rec(fq)[:, [0, 2]]
        tlast = q[:, 0].max()
        cyc = q[q[:, 0] >= tlast - TIDE_T / 3600.0 + 1e-6]
        m["q_max"], m["q_min"], m["q_mean"] = cyc[:, 1].max(), cyc[:, 1].min(), cyc[:, 1].mean()
    hi, lo = nf - TIDE_PH + 1, nf - 1               # 最後の周期の満潮・干潮
    if tidal and os.path.exists(os.path.join(rdir, "E%04d.txt" % hi)):
        eh, el, zl = rd("E", hi), rd("E", lo), rd("Z", lo)
        hh, hl = rd("H", hi), rd("H", lo)
        flat = sea & (hl < 0.05) & (hh > 0.05)       # 干潮で干上がり、満潮で冠水する(干潟)
        m["flat"] = flat.sum() * dx * dx
        m["prism_flat"] = np.where(flat, hh, 0.0).sum() * dx * dx
        m["q_flat"] = np.pi * m["prism_flat"] / TIDE_T
    return m


def finished(c):
    """計算が最後の出力まで進んだか(tt / dt_file 番の Z があるか)。"""
    ptxt_ = open({"base": "param.txt"}.get(c, "param_%s.txt" % c)).read()
    g = lambda k: float(re.search(r"^\s*%s\s*=\s*([0-9.eE+-]+)" % k, ptxt_, re.M).group(1))
    return os.path.exists(os.path.join("result_%s" % c, "Z%04d.txt" % round(g("tt") / g("dt_file"))))


def tidecmp():
    """潮汐なしの基準と潮汐のケースの最終の堆積厚と地盤高の区分(段 6: notide と tide、段 7: smallq と tidedom)。"""
    from matplotlib.colors import ListedColormap
    pairs = (("tide_cmp.png", (("notide", T("潮汐なし(notide)", "no tide (notide)")), ("tide", T("潮汐あり(tide)", "with tide (tide)")))),
             ("tidedom_cmp.png", (("smallq", T("潮汐なし(smallq)", "no tide (smallq)")),
                                  ("tidedom", T("潮汐あり(tidedom)", "with tide (tidedom)")))))
    for fname, cases in pairs:
        if not all(finished(c) for c, _ in cases):
            print("skip %s (results missing or still running)" % fname)
            continue
        fig, axs = plt.subplots(2, 2, figsize=(13, 8.6), constrained_layout=True)
        for col, (c, lab) in enumerate(cases):
            rdir = "result_%s" % c
            pf = {"base": "param.txt"}.get(c, "param_%s.txt" % c)
            mt = tide_metrics(rdir, pf)
            nf = mt["nf"]
            z0 = np.loadtxt(os.path.join(rdir, "Z0000.txt")); z = np.loadtxt(os.path.join(rdir, "Z%04d.txt" % nf))
            h = np.loadtxt(os.path.join(rdir, "H%04d.txt" % nf))
            ny_, nx_ = z.shape; dx = 5.0
            xx = (np.arange(nx_) + 0.5) * dx; yy = (np.arange(ny_) + 0.5) * dx
            ex = [0, nx_ * dx, ny_ * dx, 0]
            ax = axs[0, col]
            im = ax.imshow(z - z0, extent=ex, cmap="RdBu_r", vmin=-2, vmax=2)
            ax.contour(xx, yy, h, levels=[0.05], colors="k", linewidths=0.6)
            ax.set_title(T("%s: 堆積厚 Δz (m)\n黒線 = 汀線(潮汐のケースは平均潮位)",
                           "%s: deposit thickness Δz (m)\nblack = shoreline (mean tide in the tidal case)") % lab, fontsize=10)
            ax.set_xlim(0, 700)
            if col == 1: fig.colorbar(im, ax=axs[0, :], shrink=0.8, label="Δz (m)")
            ax = axs[1, col]
            cls = np.full(z.shape, np.nan)
            sea = xx[None, :] > 150.0
            cls[sea & (z <= -TIDE_A)] = 0; cls[sea & (z > -TIDE_A) & (z < TIDE_A)] = 1; cls[sea & (z >= TIDE_A)] = 2
            im2 = ax.imshow(cls, extent=ex, cmap=ListedColormap(["#9ecae1", "#f1c55e", "#7a5c2e"]), vmin=-0.5, vmax=2.5)
            ax.contour(xx, yy, z, levels=[0.0], colors="k", linewidths=0.5, linestyles=":")
            ax.set_title(T("%s: 地盤高の区分(点線 = 0 m)", "%s: bed elevation classes (dotted = 0 m)") % lab, fontsize=10)
            ax.set_xlim(0, 700)
            for a in axs[:, col]:
                a.set_xlabel("x (m)"); a.set_ylabel("y (m)")
            print("%-8s frame %d: deposit %.0f m3 (sand %.0f, mud %.0f), land(h<0.05) %.0f m2, advance %.0f m, "
                  "bed>=+1 %.0f m2, -1<bed<+1 %.0f m2, bed>0 %.0f m2, sand body(>0.3 m) along %.0f m x across %.0f m"
                  % (c, nf, mt["deposit"], mt["sand"], mt["mud"], mt["land"], mt["advance"], mt["supra"], mt["inter"],
                     mt["above_msl"], mt.get("along", 0), mt.get("across", 0)))
            if "q_max" in mt:
                print("         mouth Q last cycle: max %.2f, min %.2f, mean %.2f m3/s" % (mt["q_max"], mt["q_min"], mt["q_mean"]))
            if "flat" in mt:
                print("         flats (dry at low, wet at high) %.0f m2, prism %.0f m3, pi*P/T = %.2f m3/s"
                      % (mt["flat"], mt["prism_flat"], mt["q_flat"]))
        cb = fig.colorbar(im2, ax=axs[1, :], shrink=0.8, ticks=[0, 1, 2])
        cb.ax.set_yticklabels([T("−1 m 以下(干潮で水中)", "≤ −1 m (under water at low tide)"), T("−1〜+1 m(潮間帯)", "−1 to +1 m (intertidal)"),
                               T("+1 m 以上(満潮でも陸)", "≥ +1 m (land at high tide)")])
        os.makedirs(SCHEMDIR, exist_ok=True)
        fig.savefig(os.path.join(SCHEMDIR, fname), dpi=110)
        plt.close(fig)


def tide_figures(rdir, frames_all, dx, lch=150.0):
    """tide の最後の 1 周期の流れ(上げ潮・満潮・下げ潮・干潮)と、水位・河口の流量の時系列。"""
    nf = max(n for n, _ in frames_all if n % TIDE_PH == 0)
    phases = [(nf - 4, T("上げ潮(平均潮位)", "flood (mean tide)")), (nf - 3, T("満潮", "high tide")),
              (nf - 2, T("下げ潮(平均潮位)", "ebb (mean tide)")), (nf - 1, T("干潮", "low tide"))]
    fig, axs = plt.subplots(2, 2, figsize=(11.5, 11.5), constrained_layout=True)
    rd = lambda pfx, k: np.loadtxt(os.path.join(rdir, "%s%04d.txt" % (pfx, k)))
    for ax, (k, lab) in zip(axs.flat, phases):
        h, u, v, e = rd("H", k), rd("u", k), rd("v", k), rd("E", k)
        ny_, nx_ = h.shape
        xx = (np.arange(nx_) + 0.5) * dx; yy = (np.arange(ny_) + 0.5) * dx
        sp = np.hypot(u, v)
        wet = h > 0.05
        im = ax.imshow(np.where(wet, sp, np.nan), extent=[0, nx_ * dx, ny_ * dx, 0], cmap="PuBu", vmin=0, vmax=1.2)
        ax.contourf(xx, yy, np.where(wet, 0.0, 1.0), levels=[0.5, 1.5], colors=["#e3d3ad"])
        st = 3
        X, Y = np.meshgrid(xx[::st], yy[::st])
        uu, vv = u[::st, ::st], v[::st, ::st]
        ok = wet[::st, ::st] & (np.hypot(uu, vv) > 0.03)
        ax.quiver(X[ok], Y[ok], uu[ok], vv[ok], color="#c0392b", scale=12, width=0.0022, headwidth=3.5)
        ax.set_xlim(100, 600); ax.set_ylim(ny_ * dx, 0)
        eta = float(np.median(e[:, -10][np.isfinite(e[:, -10])]))
        ax.set_title(T("%s(潮位 %+.2f m)", "%s (tide level %+.2f m)") % (lab, eta), fontsize=10)
        ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
    fig.colorbar(im, ax=axs, shrink=0.7, label=T("流速 |V| (m/s)。矢印 = 流れの向き。黄土色 = 乾いた所",
                                                 "speed |V| (m/s); arrows = flow direction; tan = dry"))
    fig.savefig(out("fig_%s_phases.png" % case), dpi=110)
    plt.close(fig)
    # 時系列: 水位(観測点)と河口の流量
    fig, axs = plt.subplots(2, 1, figsize=(12, 6.4), sharex=True, constrained_layout=True)
    for k, lab in ((1, T("河口の手前の河道", "channel just inside the mouth")), (2, T("河口の前 100 m", "100 m off the mouth")),
                   (3, T("海盆の中央", "middle of the basin"))):
        f = os.path.join(rdir, "probes", "probe%04d.csv" % k)
        if os.path.exists(f):
            a = read_rec(f)
            axs[0].plot(a[:, 0], a[:, 2] + a[:, 3], lw=1, label=lab)
    tt_ = np.linspace(0, frames_all[-1][1] / 3600.0, 600)
    axs[0].plot(tt_, TIDE_A * np.sin(2 * np.pi * tt_ * 3600 / TIDE_T), "k:", lw=1, label=T("与えた潮位", "imposed tide"))
    axs[0].set_ylabel(T("水位 (m)", "water level (m)")); axs[0].legend(fontsize=8, ncol=4, loc="lower center")
    axs[0].set_ylim(-1.45, 1.15); axs[0].grid(alpha=0.3)
    f = os.path.join(rdir, "fluxes", "flux0001.csv")
    if os.path.exists(f):
        a = read_rec(f)
        axs[1].plot(a[:, 0], a[:, 2], lw=1, color="C3", label=T("河口を通る流量(海へ向かう向きが正)", "discharge through the mouth (seaward positive)"))
    qr = float(re.search(r"inflow_val\(1:2,1,1\)\s*=\s*0\s*,\s*([0-9.eE+-]+)", open("param_%s.txt" % case).read()).group(1))
    axs[1].axhline(qr, color="k", lw=0.8, ls="--", label=T("川の流量 %g m³/s", "river discharge %g m³/s") % qr)
    axs[1].axhline(0.0, color="0.5", lw=0.6)
    axs[1].set_ylabel(T("流量 (m³/s)", "discharge (m³/s)")); axs[1].legend(fontsize=8, loc="lower right"); axs[1].grid(alpha=0.3)
    mf = float(re.search(r"^\s*morfac\s*=\s*([0-9.eE+-]+)", open("param_%s.txt" % case).read(), re.M).group(1))
    axs[1].set_xlabel(T("水理時間 (h)(地形時間 = 水理時間 × morfac %g)", "hydraulic time (h) (landform time = hydraulic time × morfac %g)") % mf)
    fig.savefig(out("fig_%s_series.png" % case), dpi=110)
    plt.close(fig)


case = ARGS[0] if ARGS else "base"
if case in ("mechanism", "setup", "tidecmp"):
    {"mechanism": mechanism, "setup": setup, "tidecmp": tidecmp}[case]()
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
LCH = {"base": 150.0, "baseqb": 150.0, "wave": 150.0, "wfsed": 150.0, "tide": 150.0, "notide": 150.0, "tidedom": 150.0, "smallq": 150.0}.get(case, 200.0)
ZSEA = {"base": -2.0, "baseqb": -2.0, "wave": -2.0, "wfsed": -2.0, "tide": -2.0, "notide": -2.0, "tidedom": -2.0, "smallq": -2.0}.get(case, -1.5)

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
frames_all = list(frames)
if case in ("tide", "tidedom"):   # 潮の 1/4 周期ごとの出力: 平均潮位(上げ)のフレームだけで比べる
    frames = [(n, t) for n, t in frames if n % TIDE_PH == 0]
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
if case in ("tide", "tidedom"):
    tide_figures(d, frames_all, DX, LCH)
