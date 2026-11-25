#!/usr/bin/env python3
"""coastal_compound_flood の図と数表。

  python3 plot_results.py            figs/*.png(日本語)と数表
  python3 plot_results.py en         en/figs/*.png(英語。形・値・描画は共通で、ラベルだけが替わる)
  python3 plot_results.py lag        図の名前(setup・mechanism・ladder・maps・profile・lag・tracer)を書くと、その図だけ
  python3 plot_results.py tables     数表だけ

  setup.png      構成: 平面・幹線に沿う断面・外力(入力から描く。計算の前に描ける)
  mechanism.png  仕組み: 潮位と排水の能力、流出と排水の差(入力と式から描く。計算の前に描ける)
  ladder.png     本体の 6 ケース: 地表の水の量の時系列と、雨の行き先
  maps.png       浸水した 3 ケースの最大浸水深
  profile.png    窪地を通る断面の、管の中の水頭と地表の水(雨だけ・複合)
  lag.png        雨と高潮のピークのずれの 9 ケース
  tracer.png     補足: 地表の水のうち下水道を通ってきた水の割合
計算していないケースの図は飛ばす。色は、ケース・雨の行き先・浸水深の区分ごとに固定している。
"""
import csv
import math
import os
import re
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Patch, Rectangle
from matplotlib.lines import Line2D
import matplotlib.patheffects as pe

import gen_data as gd

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
FIGDIR = "en/figs" if EN else "figs"
os.makedirs(FIGDIR, exist_ok=True)
plt.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAPGothic", "IPAGothic", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["font.size"] = 9.5

# ---- 色(役割ごとに固定。ケースの色はどの図でも同じ)----
INK, INK2, GRID, AXIS = "#191919", "#666666", "#e7e7e7", "#c2c2c2"
C_BOTH, C_COMP, C_NOPUMP = "#257de0", "#f47230", "#00b894"       # 雨 + 高潮、複合、機場停止
C_MUTE = "#a3a3a3"                                                # 浸水しないケース、背景の線
C_SOIL, C_PIPE, C_GRAV, C_PUMP = "#f2a600", "#ee7fac", "#008a17", "#6a4ce2"   # 雨の行き先
C_RAIN, C_TIDE = "#6aabf1", "#666666"
DEPTH_EDGES = [0.02, 0.1, 0.2, 0.3, 0.5, 9.9]                     # 浸水深の区分 (m)
DEPTH_COLS = ["#84b9f3", "#519ced", "#257de0", "#1757ac", "#0e3d7e"]   # 1 色の濃淡(白地で検証した 5 段)
FRAC_EDGES = [0.0, 0.2, 0.4, 0.6, 0.8, 1.001]                     # 下水道を通った水の割合
FRAC_COLS = ["#f4a071", "#ef7d3f", "#d45a1c", "#a8440f", "#763009"]
C_SEA, C_LAND, C_GROUND = "#dfe9f2", "#ffffff", "#d9d2c3"
HALO = [pe.withStroke(linewidth=2.2, foreground="white")]         # 地図の上の文字の白い縁

G = 9.8
g20 = gd.build(20.0)
NSEA, NX, NY, DX, JT = g20["nsea"], g20["nx"], g20["ny"], g20["dx"], g20["jt"]
LAND = ~g20["sea"]
AREA = LAND.sum() * DX * DX
ZL = g20["z"][:, NSEA:]                      # 陸の地盤高
XL = (np.arange(NX - NSEA) + 0.5) * DX      # 防潮堤からの距離 (m)
YL = (np.arange(NY) + 0.5) * DX             # 北端からの距離 (m)
CELLS = gd.cells(g20)
SP = gd.specs()
RAIN_TOTAL = gd.RAIN_PEAK * (gd.RAIN_TOP + gd.RAIN_RAMP) / 60.0     # mm
SOIL_CAP = float(gd.base_value("sd0")) * float(gd.base_value("sy0")) * 1e3   # 土層にためられる水 (mm) = sd0 × sy0
K_INF = float(gd.base_value("gw_ksv_mmh"))   # 浸透能 (mm/h)
SAT_HIGH = float(gd.base_value("gw_sat0"))   # 地下水位が高いケースの初期の飽和度
T_END = 12.0


# ---------------------------------------------------------------- 読み込み
def have(case):
    return os.path.isfile("result_%s/H9999.txt" % case)


def read_log(case):
    """Log.txt の時刻 (h) と S_surf・S_grnd・S_total (m)"""
    rows = [l.split() for l in open("result_%s/Log.txt" % case) if l.strip() and l.strip()[0].isdigit()]
    t = np.array([sum(float(x) * m for x, m in zip(r[0].split(":"), (1.0, 1 / 60.0, 1 / 3600.0))) for r in rows])
    return t, np.array([[float(r[k]) for k in (2, 3, 4)] for r in rows]).T


def read_probe(case, n):
    a = np.loadtxt("result_%s/probes/probe%04d.csv" % (case, n), delimiter=",", comments="#")
    return a[:, 0], a[:, 3]                  # 時刻 (h)、水深 (m)


def read_field(case, name, k):
    return np.loadtxt("result_%s/%s%04d.txt" % (case, name, k))


def outfall_total(case):
    """吐口から海へ出た累積の体積 (m3)。画面出力の outfall discharge total"""
    m = re.search(r"outfall discharge total =\s*([0-9.E+-]+)", open("Screen_%s.log" % case).read())
    return float(m.group(1)) if m else float("nan")


def read_wq(case):
    rows = list(csv.reader(open("result_%s/wq.csv" % case)))
    hd = [h.strip() for h in rows[0]]
    a = np.array([[float(x) for x in r] for r in rows[1:]])
    return {h: a[:, i] for i, h in enumerate(hd)}


def conduit_head(hgc, g=g20):
    """管路の貯留 hgc (m) → 水頭 (m)。満管までは bot + hgc/sy、その後は疑似スロット"""
    cap, bot, sy, sl = g["cap"], g["bot"], g["sy"], g["slot"]
    with np.errstate(divide="ignore", invalid="ignore"):
        h = np.where(hgc <= cap, bot + hgc / sy, bot + cap / sy + (hgc - cap) / sl)
    return np.where(cap > 0, h, np.nan)


def rain_at(t_h, lag=0):
    """雨の強さ (mm/h)。t_h は時刻 (h)。lag = None は雨なし"""
    if lag is None:
        return np.zeros_like(np.asarray(t_h, dtype=float))
    r = gd.rain_rows(lag)
    return np.interp(np.asarray(t_h) * 60.0, [p[0] for p in r], [p[1] for p in r], left=0.0, right=0.0)


def tide_at(t_h, surge=True):
    r = gd.tide_rows(surge)
    return np.interp(np.asarray(t_h) * 60.0, [p[0] for p in r], [p[1] for p in r])


def budget(case):
    """雨の行き先 (mm。町の平均)。土は最終の Hg の分布から初期の水を引いた分、管は最終の Hgc の分布、
    吐口は画面出力の累積、地表は最終の S_surf。機場は台帳がないので残り(機場のないケースの残りは収支の残差)"""
    lag, sat0, pump = gd.CASES[case][1], gd.CASES[case][3], gd.CASES[case][4]
    t, (ss, sg, st) = read_log(case)
    rain = 0.0 if lag is None else RAIN_TOTAL
    hgc = np.loadtxt("result_%s/Hgc9998.txt" % case)[LAND].sum() * DX * DX / AREA * 1e3
    hg = np.loadtxt("result_%s/Hg9998.txt" % case)[LAND].sum() * DX * DX / AREA * 1e3
    soil = hg - sat0 * SOIL_CAP                   # 初期の水(初期の飽和度 × 土層にためられる水)を引く
    grav = outfall_total(case) / AREA * 1e3
    surf = ss[-1] * 1e3
    pumpv = rain - soil - hgc - grav - surf       # 残りが機場の排水(機場には台帳がない)
    if not pump:
        pumpv = 0.0
    return dict(rain=rain, soil=soil, pipe=hgc, grav=grav, pump=pumpv, surf=surf,
                resid=rain - soil - hgc - grav - surf - pumpv, peak=ss.max() * AREA, tpeak=t[ss.argmax()])


# ---------------------------------------------------------------- 描画の部品
def style(ax, grid="y"):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(AXIS)
    ax.tick_params(colors=INK2, length=3, color=AXIS)
    ax.xaxis.label.set_color(INK2)
    ax.yaxis.label.set_color(INK2)
    if grid:
        ax.grid(axis=grid, color=GRID, lw=0.8)
        ax.set_axisbelow(True)


def title(ax, s, **kw):
    ax.set_title(s, loc="left", fontsize=10.5, color=INK, **kw)


def hours(ax, t1=T_END, step=2):
    ax.set_xlim(0, t1)
    ax.set_xticks(np.arange(0, t1 + 0.01, step))


def save(fig, name):
    path = os.path.join(FIGDIR, name)
    fig.savefig(path, dpi=150, facecolor="white")
    plt.close(fig)
    print("wrote", path)


def pad_edges(a):
    """セル中心の場 a(陸)を領域の縁まで延ばす(等値線を縁まで描くため)。x・y の座標も返す"""
    x = np.concatenate([[0.0], XL, [gd.LX_LAND]])
    y = np.concatenate([[0.0], YL, [gd.LY]])
    return x, y, np.pad(a, 1, mode="edge")


def draw_plan(ax, labels=True):
    """平面の下地: 海・防潮堤・幹線・ポンプ井。軸は防潮堤からの距離 x と北端からの距離 y (m)"""
    ax.add_patch(Rectangle((-gd.LX_SEA, 0), gd.LX_SEA, gd.LY, fc=C_SEA, ec="none"))
    ax.plot([0, 0], [0, gd.LY], color=INK, lw=2.6, solid_capstyle="butt")
    ax.plot([0, gd.LX_LAND], [gd.Y_TRUNK, gd.Y_TRUNK], color=INK, lw=1.3)
    ax.plot([DX / 2], [gd.Y_TRUNK], marker="s", ms=6.5, mfc="white", mec=INK, mew=1.4, zorder=5)
    ax.set_xlim(-gd.LX_SEA, gd.LX_LAND)
    ax.set_ylim(gd.LY, 0)
    ax.set_aspect("equal")
    ax.set_xticks([0, 200, 400, 600, 800])
    ax.set_yticks([0, 250, 500])
    style(ax, grid=None)
    if labels:
        ax.set_xlabel(T("防潮堤からの距離 (m)", "distance from the seawall (m)"))
        ax.set_ylabel(T("北端からの距離 (m)", "distance from the north edge (m)"))


# ---------------------------------------------------------------- 図: 構成
def fig_setup():
    fig = plt.figure(figsize=(12.6, 7.9))
    outer = fig.add_gridspec(1, 2, width_ratios=[1.62, 1.0], left=0.06, right=0.98, top=0.945, bottom=0.075, wspace=0.16)
    left = outer[0].subgridspec(2, 1, height_ratios=[1.72, 1.0], hspace=0.2)
    right = outer[1].subgridspec(2, 1, hspace=0.42)
    lead = dict(arrowstyle="-", color=INK2, lw=0.8)
    kw = dict(fontsize=8.8, color=INK)

    # (a) 平面
    ax = fig.add_subplot(left[0])
    lev = [0.6, 0.7, 0.8, 0.9, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 3.7]
    cols = ["#cfe0cd", "#dbe7d2", "#e7eedb", "#f1f1e2", "#f4ecd9", "#eedfc4", "#e6d0ae", "#dcc098", "#d2b184", "#c8a271"]
    xe, ye, ze = pad_edges(ZL)
    ax.contourf(xe, ye, ze, levels=lev, colors=cols)
    ax.contour(xe, ye, ze, levels=[0.7, 0.8, 0.9, 1.0, 1.5, 2.5, 3.0, 3.5], colors=INK2, linewidths=0.6)
    ax.contour(xe, ye, ze, levels=[2.0], colors=[C_COMP], linewidths=1.8)
    draw_plan(ax)
    ax.tick_params(labelbottom=False)
    ax.set_xlabel("")
    zt = ZL[JT - 1]
    for lv in (1.0, 1.5, 2.5, 3.0, 3.5):                       # 等高線の値(北の縁に書く)
        ax.text(np.interp(lv, zt, XL) + 5, 22, "%.1f" % lv, fontsize=7.8, color=INK2)
    ax.text(np.interp(2.0, zt, XL) + 6, 484, T("+2.0 m = 高潮のピークの高さ", "+2.0 m = level of the surge peak"), fontsize=8.6, color=INK)
    ax.text(np.interp(2.0, zt, XL) + 5, 22, "2.0", fontsize=7.8, color=INK2)
    ax.text(-gd.LX_SEA / 2, 60, T("海", "sea"), ha="center", **kw)
    ax.annotate(T("防潮堤(天端 +3.5 m)", "seawall (crest +3.5 m)"), (0, 455), (40, 478), arrowprops=lead, **kw)
    ax.annotate(T("ポンプ井(吐口と機場)", "pump well (outfall and pumping station)"), (DX / 2, gd.Y_TRUNK + 6), (40, 298), arrowprops=lead, **kw)
    ax.text(520, gd.Y_TRUNK - 10, T("幹線(函渠 2.5 m × 1.0 m)", "trunk (box culvert 2.5 m × 1.0 m)"), **kw)
    ax.annotate(T("窪地(底 +0.64 m。等高線は 0.7・0.8・0.9 m)", "depression (bottom +0.64 m; contours 0.7, 0.8, 0.9 m)"),
                (gd.DEP_X + 14, gd.DEP_Y - 12), (150, 62), arrowprops=lead, **kw)
    ax.text(62, 395, T("低地\n(+0.9 m)", "lowland\n(+0.9 m)"), ha="center", **kw)
    ax.text(600, 395, T("斜面(勾配 1/250)\n全セルに枝管網と枡", "slope (1/250)\nbranch network and inlets in every cell"), ha="center", **kw)
    for key, lab, dxy in (("dep", "P2", (-34, 26)), ("low", "P3", (10, 22)), ("slope", "P4", (10, 22))):
        i, j = CELLS[key]
        px, py = (i - NSEA - 0.5) * DX, (j - 0.5) * DX
        ax.plot([px], [py], marker="o", ms=5, mfc=INK, mec="white", mew=0.9, zorder=6)
        ax.text(px + dxy[0], py + dxy[1], lab, fontsize=8.3, color=INK)
    title(ax, T("(a) 平面(色と等高線は地盤高 m。P2〜P4 はプローブ)", "(a) Plan (colours and contours: ground elevation in m; P2–P4 are probes)"))

    # (b) 幹線に沿う断面((a) と横軸をそろえる)
    ax = fig.add_subplot(left[1])
    xs = np.concatenate([[0.0], XL, [gd.LX_LAND]])
    zs = np.concatenate([[zt[0]], zt, [zt[-1]]])
    ax.fill_between(xs, -3.2, zs, color=C_GROUND, lw=0)
    ax.fill_between(xs, zs - gd.BURY_T, zs - gd.BURY_T + gd.H_T, color="#7a7a7a", lw=0)        # 幹線
    ax.fill_between(xs, zs - gd.BURY_B, zs - gd.BURY_B + gd.D_B, color="#b9b9b9", lw=0)        # 枝管網
    ax.plot(xs, zs - 0.1, color=C_BOTH, lw=1.4)
    ax.plot(xs, zs - 1.0, color=C_BOTH, lw=1.4, ls=(0, (4, 2)))
    ax.fill_between([-gd.LX_SEA, 0], -3.2, 0.0, color="#9cc3ec", lw=0)
    ax.fill_between([-gd.LX_SEA, 0], 0.0, gd.ETA_SURGE, color="#cfe3f3", lw=0)
    ax.plot([0, 0], [-3.2, 3.5], color=INK, lw=2.6, solid_capstyle="butt")
    ax.add_patch(Rectangle((2, zt[0] - gd.BURY_T), DX - 2, gd.BURY_T, fc="white", ec=INK, lw=1.0))
    ax.set_xlim(-gd.LX_SEA, gd.LX_LAND)
    ax.set_ylim(-3.2, 4.3)
    ax.set_yticks([-2, 0, 2, 4])
    ax.set_xticks([0, 200, 400, 600, 800])
    style(ax, grid=None)
    ax.set_ylabel(T("標高 (m)", "elevation (m)"))
    ax.set_xlabel(T("防潮堤からの距離 (m)", "distance from the seawall (m)"))
    kw = dict(fontsize=8.6, color=INK)
    ax.annotate(T("防潮堤の天端 +3.5 m", "seawall crest +3.5 m"), (0, 3.5), (28, 3.72), arrowprops=lead, **kw)
    ax.annotate(T("高潮のピーク +2.0 m", "surge peak +2.0 m"), (-28, 2.0), (28, 2.55), arrowprops=lead, **kw)
    ax.annotate(T("平常の潮位 0 m", "normal tide 0 m"), (-28, 0.0), (28, 1.5), arrowprops=lead, **kw)
    ax.annotate(T("ポンプ井(底 −1.6 m)", "pump well (bottom −1.6 m)"), (DX / 2, -1.2), (50, -2.75), arrowprops=lead, **kw)
    ax.annotate(T("幹線(管底は地表 − 2.5 m)", "trunk (invert 2.5 m below ground)"), (430, np.interp(430, XL, zt) - 2.0), (470, -1.8), arrowprops=lead, **kw)
    ax.annotate(T("枝管網(管底は地表 − 1.5 m)", "branch network (invert 1.5 m below ground)"), (250, np.interp(250, XL, zt) - 1.3), (300, -2.7), arrowprops=lead, **kw)
    ax.legend(handles=[Line2D([], [], color=C_BOTH, lw=1.4, label=T("地下水面が高い(地表 − 0.1 m)", "high water table (0.1 m below ground)")),
                       Line2D([], [], color=C_BOTH, lw=1.4, ls=(0, (4, 2)), label=T("低い(土層の底 = 地表 − 1 m より下)", "low (below the soil base, 1 m down)"))],
              loc="upper center", bbox_to_anchor=(0.56, 1.03), frameon=False, fontsize=8.5, handlelength=2.6, borderaxespad=0.3)
    fig.canvas.draw()
    bb = ax.get_window_extent()
    ex = (bb.height / 7.5) / (bb.width / (gd.LX_SEA + gd.LX_LAND))
    title(ax, T("(b) 幹線に沿う断面(縦は横の約 %d 倍)" % (5 * round(ex / 5)), "(b) Section along the trunk (vertical exaggeration about %d)" % (5 * round(ex / 5))))

    # (c)(d) 外力
    th = np.linspace(0, T_END, 721)
    ax = fig.add_subplot(right[0])
    ax.fill_between(th, tide_at(th), color="#cfe3f3", lw=0)
    ax.plot(th, tide_at(th), color=C_TIDE, lw=2)
    for y, lab in ((3.5, T("防潮堤の天端 +3.5 m", "seawall crest +3.5 m")), (0.9, T("低地の地盤 +0.9 m", "lowland ground +0.9 m"))):
        ax.axhline(y, color=INK, lw=0.9, ls=(0, (5, 3)))
        ax.text(11.85, y + 0.1, lab, fontsize=8.6, color=INK, ha="right")
    hours(ax)
    ax.set_ylim(0, 4.2)
    ax.set_yticks([0, 1, 2, 3, 4])
    ax.set_ylabel(T("潮位 (m)", "tide (m)"))
    ax.set_xlabel(T("時刻 (時間)", "time (h)"))
    style(ax)
    title(ax, T("(c) 高潮(2.5 時間で +2.0 m。ピークは 5.5 時間)", "(c) Storm surge (+2.0 m in 2.5 h; peak at 5.5 h)"))
    ax = fig.add_subplot(right[1])
    ax.fill_between(th, rain_at(th, -2), color="none", edgecolor=C_MUTE, lw=1.2, ls=(0, (4, 2)))
    ax.fill_between(th, rain_at(th), color=C_RAIN, lw=0, alpha=0.85)
    ax.text(7.0, 40, T("基本の時刻(ピークの中央が\n高潮のピークの 5.5 時間)", "base timing (peak centred\non the surge peak, 5.5 h)"), ha="left", fontsize=8.6, color=INK)
    ax.text(2.3, 30, T("ずれ −2 時間\n(雨が先)", "lag −2 h\n(rain first)"), ha="right", fontsize=8.6, color=INK2)
    hours(ax)
    ax.set_ylim(0, 62)
    ax.set_yticks([0, 25, 50])
    ax.set_ylabel(T("雨 (mm/h)", "rain (mm/h)"))
    ax.set_xlabel(T("時刻 (時間)", "time (h)"))
    style(ax)
    title(ax, T("(d) 雨(3 時間で 100 mm。ピーク 50 mm/h)", "(d) Rain (100 mm in 3 h; peak 50 mm/h)"))
    save(fig, "setup.png")


# ---------------------------------------------------------------- 図: 仕組み(入力と式だけ)
H_FLOOD = gd.Z_COAST                # ポンプ井の水頭がここに達すると低地の枡から水が出る (m)
Q_TRUNK = SP["c_t"] * math.sqrt(gd.S_UP)


def q_gravity(eta):
    """潮位 eta のとき、低地を浸水させずに吐口が流せる量 (m3/s)。幹線の能力が上限"""
    return np.minimum(Q_TRUNK, gd.CDA_OUT * np.sqrt(2 * G * np.maximum(H_FLOOD - np.asarray(eta, dtype=float), 0.0)))


def runoff(t_h, room_mm, lag=0, k_mmh=K_INF):
    """流出 (m3/s) = (雨 − 浸透) × 面積。浸透は雨と浸透能の小さい方で、土の空きがなくなるまで"""
    r = rain_at(t_h, lag)
    f = np.minimum(r, k_mmh)
    cum = np.concatenate([[0.0], np.cumsum(0.5 * (f[1:] + f[:-1]) * np.diff(t_h))])
    f = np.where(cum < room_mm, f, 0.0)
    return (r - f) / 3.6e6 * AREA


def fig_mechanism():
    fig, axs = plt.subplots(1, 2, figsize=(12.0, 4.5), gridspec_kw=dict(width_ratios=[1.0, 1.25], left=0.06, right=0.975, top=0.86, bottom=0.13, wspace=0.2))
    q50 = gd.RAIN_PEAK / 3.6e6 * AREA
    q30 = (gd.RAIN_PEAK - K_INF) / 3.6e6 * AREA
    # (a) 潮位と排水の能力
    ax = axs[0]
    eta = np.linspace(0, 2.2, 441)
    qg = q_gravity(eta)
    ax.fill_between(eta, 0, gd.QP, color=C_PUMP, alpha=0.30, lw=0)
    ax.fill_between(eta, gd.QP, gd.QP + qg, color=C_GRAV, alpha=0.25, lw=0)
    ax.plot(eta, gd.QP + qg, color=INK, lw=2)
    for q, lab in ((q50, T("50 mm/h の雨の流出(浸透なし)%.1f m³/s", "runoff at 50 mm/h (no infiltration) %.1f m³/s") % q50),
                   (q30, T("同(%g mm/h が浸透)%.1f m³/s", "same (%g mm/h infiltrates) %.1f m³/s") % (K_INF, q30))):
        ax.axhline(q, color=INK, lw=0.9, ls=(0, (5, 3)))
        ax.text(2.18, q + 0.12, lab, ha="right", fontsize=8.6, color=INK)
    ax.text(0.2, gd.QP / 2, T("機場 %.1f m³/s(潮位によらない)", "pumping station %.1f m³/s (independent of the tide)") % gd.QP, va="center", fontsize=8.8, color=INK)
    ax.text(0.04, 4.6, T("吐口の自然排水\n(幹線の能力\n %.1f m³/s まで)", "gravity outfall\n(up to the trunk\n capacity %.1f m³/s)") % Q_TRUNK, va="center", fontsize=8.8, color=INK)
    ax.annotate(T("潮位が低地の地盤 +0.9 m に\n届くと、吐口は流せない", "once the tide reaches the lowland\nground (+0.9 m), no gravity flow"), (0.9, gd.QP), (1.12, 2.15),
                arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8), fontsize=8.8, color=INK)
    ax.set_xlim(0, 2.2)
    ax.set_xticks([0, 0.5, 1.0, 1.5, 2.0])
    ax.set_ylim(0, 8.6)
    ax.set_xlabel(T("潮位 (m)", "tide level (m)"))
    ax.set_ylabel(T("流量 (m³/s)", "discharge (m³/s)"))
    style(ax)
    title(ax, T("(a) 低地を浸水させずに海へ出せる量と潮位", "(a) Discharge possible without flooding the lowland, against the tide"))
    # (b) 流出と排水の能力の時間変化(雨と高潮のピークが重なるとき)
    ax = axs[1]
    th = np.linspace(0, T_END, 2881)
    cap = gd.QP + q_gravity(tide_at(th))
    ax.fill_between(th, 0, gd.QP, color=C_PUMP, alpha=0.30, lw=0)
    ax.fill_between(th, gd.QP, cap, color=C_GRAV, alpha=0.25, lw=0)
    ax.plot(th, cap, color=INK, lw=2, label=T("海へ出せる量(機場 + 吐口)", "discharge capacity (pumps + outfall)"))
    for room, col, lab in ((SOIL_CAP, C_BOTH, T("流出: 地下水位が低い(超過 %s m³)", "runoff: low water table (excess %s m³)")),
                           ((1.0 - SAT_HIGH) * SOIL_CAP, C_COMP, T("流出: 地下水位が高い(超過 %s m³)", "runoff: high water table (excess %s m³)"))):
        q = runoff(th, room)
        ex = np.maximum(q - cap, 0.0)
        vol = float(np.sum(0.5 * (ex[1:] + ex[:-1]) * np.diff(th * 3600.0)))   # 台形則(NumPy の版によらない)
        ax.plot(th, q, color=col, lw=2, label=lab % format(int(round(vol, -2)), ","))
        ax.fill_between(th, cap, np.maximum(q, cap), color=col, alpha=0.22, lw=0)
        print("mechanism: excess volume (room %g mm) = %.0f m3" % (room, vol))
    ax.set_xlim(3, 8.5)
    ax.set_ylim(0, 8.6)
    ax.set_xlabel(T("時刻 (時間)", "time (h)"))
    ax.set_ylabel(T("流量 (m³/s)", "discharge (m³/s)"))
    style(ax)
    ax.legend(loc="upper center", bbox_to_anchor=(0.455, 1.0), frameon=False, fontsize=8.8)
    ax.annotate(T("海へ出せずに町にたまる分(超過)", "cannot leave: stays in the town (excess)"), (5.6, 4.6), (5.6, 6.15), ha="center",
                arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8), fontsize=8.8, color=INK)
    title(ax, T("(b) 雨と高潮のピークが重なるときの流出と、海へ出せる量", "(b) Runoff and capacity when the rain and surge peaks coincide"))
    fig.suptitle(T("仕組み: 潮位が上がると吐口が閉じ、流出が海へ出せる量を超える(入力と式から描いた図)",
                   "Mechanism: a high tide closes the outfall and the runoff exceeds what can leave (drawn from the inputs and formulas)"), fontsize=11.5, x=0.06, ha="left", y=0.975)
    save(fig, "mechanism.png")


# ---------------------------------------------------------------- 図: 本体の 6 ケース
MAIN = ["surge", "rain", "rain_gw", "both", "compound", "nopump"]
CASE_COL = {"surge": C_MUTE, "rain": C_MUTE, "rain_gw": C_MUTE, "both": C_BOTH, "compound": C_COMP, "nopump": C_NOPUMP}


def case_label(c):
    return {"surge": T("高潮だけ", "surge only"),
            "rain": T("雨だけ", "rain only"),
            "rain_gw": T("雨だけ・地下水位が高い", "rain only, high water table"),
            "both": T("雨 + 高潮", "rain + surge"),
            "compound": T("雨 + 高潮 + 高い地下水位(複合)", "rain + surge + high water table (compound)"),
            "nopump": T("複合 + 機場の停止", "compound + pumps stopped")}[c]


def case_label2(c):
    """棒グラフの軸に書く 2 行のラベル(長いものだけ折る)"""
    return {"rain_gw": T("雨だけ・\n地下水位が高い", "rain only,\nhigh water table"),
            "compound": T("雨 + 高潮 +\n高い地下水位(複合)", "rain + surge + high\nwater table (compound)"),
            "nopump": T("複合 +\n機場の停止", "compound +\npumps stopped")}.get(c, case_label(c))


def closed_window():
    """潮位が低地の地盤 +0.9 m より高い時間帯 (h)"""
    th = np.linspace(0, T_END, 14401)
    m = tide_at(th) > H_FLOOD
    return th[m][0], th[m][-1]


def flood_stats(case):
    h9 = np.loadtxt("result_%s/H9999.txt" % case)[:, NSEA:]
    cell = DX * DX / 1e4
    return dict(hmax=h9.max(), a10=(h9 >= 0.1).sum() * cell, a30=(h9 >= 0.3).sum() * cell, a50=(h9 >= 0.5).sum() * cell)


def fig_ladder():
    cases = [c for c in MAIN if have(c)]
    if len(cases) < len(MAIN):
        print("skip ladder.png (run the six main cases first: make run)")
        return
    fig = plt.figure(figsize=(12.6, 7.6))
    outer = fig.add_gridspec(1, 2, width_ratios=[1.25, 1.0], left=0.06, right=0.975, top=0.94, bottom=0.135, wspace=0.36)
    left = outer[0].subgridspec(3, 1, height_ratios=[0.5, 0.5, 2.0], hspace=0.2)
    right = outer[1].subgridspec(2, 1, height_ratios=[1.0, 1.0], hspace=0.42)
    th = np.linspace(0, T_END, 721)
    t1, t2 = closed_window()
    ax_r = fig.add_subplot(left[0])
    ax_t = fig.add_subplot(left[1], sharex=ax_r)
    ax_v = fig.add_subplot(left[2], sharex=ax_r)
    for ax in (ax_r, ax_t, ax_v):
        ax.axvspan(t1, t2, color="#f1efe8", lw=0)
    ax_r.fill_between(th, rain_at(th), color=C_RAIN, lw=0, alpha=0.85)
    ax_r.set_ylim(0, 60)
    ax_r.set_yticks([0, 50])
    ax_r.set_ylabel(T("雨 (mm/h)", "rain (mm/h)"))
    ax_t.plot(th, tide_at(th), color=C_TIDE, lw=2)
    ax_t.axhline(H_FLOOD, color=INK, lw=0.9, ls=(0, (5, 3)))
    ax_t.text(11.85, H_FLOOD + 0.12, T("低地の地盤 +0.9 m", "lowland ground +0.9 m"), fontsize=8.4, color=INK, ha="right")
    ax_t.text(0.5 * (t1 + t2), 2.25, T("吐口が閉じる時間帯", "outfall closed"), ha="center", fontsize=8.4, color=INK)
    ax_t.set_ylim(0, 2.9)
    ax_t.set_yticks([0, 2])
    ax_t.set_ylabel(T("潮位 (m)", "tide (m)"))
    peaks = {}
    for c in ["rain", "rain_gw", "surge", "both", "compound", "nopump"]:
        t, (ss, sg, st) = read_log(c)
        v = ss * AREA / 1e3
        lw = 2.0 if CASE_COL[c] != C_MUTE else 1.4
        ax_v.plot(t, v, color=CASE_COL[c], lw=lw, solid_capstyle="round", zorder=3 if lw > 1.5 else 2)
        peaks[c] = (t[v.argmax()], v.max())
    for c in ("both", "compound", "nopump"):
        tp, vp = peaks[c]
        ax_v.plot([tp], [vp], marker="o", ms=6, mfc=CASE_COL[c], mec="white", mew=1.5, zorder=5)
    ax_v.annotate(T("雨だけ(地下水位の低・高)・高潮だけ:\n枡へ向かう薄い水(最大 %.1f 千 m³)\nのほかは、たまらない", "rain only (low or high\nwater table) and surge only:\njust the thin sheet heading to\nthe inlets (≤ %.1f thousand m³)") % peaks["rain"][1],
                  (4.95, peaks["rain"][1]), (0.25, 6.2), arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8), fontsize=8.6, color=INK)
    ax_v.set_ylim(0, 34.0)
    ax_v.set_yticks([0, 5, 10, 15, 20, 25])
    ax_v.set_ylabel(T("地表の水の量 (千 m³)", "water on the surface (thousand m³)"))
    ax_v.set_xlabel(T("時刻 (時間)", "time (h)"))
    hours(ax_v)
    for ax in (ax_r, ax_t, ax_v):
        style(ax)
    for ax in (ax_r, ax_t):
        ax.tick_params(labelbottom=False)
    ax_v.legend(handles=[Line2D([], [], color=CASE_COL[c], lw=2, marker="o", ms=5, mec="white", mew=1.0,
                                label=T("%s: 最大 %.1f 千 m³(%.1f 時間)", "%s: max %.1f thousand m³ (at %.1f h)") % (case_label(c), peaks[c][1], peaks[c][0]))
                         for c in ("both", "compound", "nopump")]
                + [Line2D([], [], color=C_MUTE, lw=1.4, label=T("雨だけ・雨だけ(地下水位が高い)・高潮だけ", "rain only, rain only (high water table), surge only"))],
                loc="upper left", frameon=False, fontsize=8.6, borderaxespad=0.2)
    title(ax_r, T("(a) 雨・潮位と、地表にある水の量(町の 40 ha の合計)", "(a) Rain, tide and the water on the surface (total over the 40 ha town)"))

    # (b) 浸水した面積
    ax = fig.add_subplot(right[0])
    ys = np.arange(len(MAIN))[::-1]
    for y, c in zip(ys, MAIN):
        fs = flood_stats(c)
        ax.barh(y, fs["a10"], height=0.4, color=CASE_COL[c], lw=0)
        lab = T("%.1f ha(最大 %.2f m)", "%.1f ha (max %.2f m)") % (fs["a10"], fs["hmax"]) if fs["a10"] > 0 else T("浸水なし", "no flooding")
        ax.text(fs["a10"] + 0.15, y, lab, va="center", fontsize=8.6, color=INK)
    ax.set_yticks(ys)
    ax.set_yticklabels([case_label2(c) for c in MAIN], fontsize=8.6, color=INK)
    ax.set_xlim(0, 11.5)
    ax.set_ylim(-0.6, len(MAIN) - 0.4)
    ax.set_xlabel(T("最大浸水深が 0.1 m 以上の面積 (ha)", "area with a maximum depth of 0.1 m or more (ha)"))
    style(ax, grid="x")
    ax.tick_params(axis="y", length=0)
    title(ax, T("(b) 浸水した面積", "(b) Flooded area"))

    # (c) 雨の行き先
    ax = fig.add_subplot(right[1])
    rc = [c for c in MAIN if gd.CASES[c][1] is not None]
    ys = np.arange(len(rc))[::-1]
    parts = (("soil", C_SOIL, T("土にしみ込んだ", "infiltrated into the soil")), ("pipe", C_PIPE, T("管の中に残った", "left in the pipes")),
             ("grav", C_GRAV, T("吐口から海へ(自然排水)", "to the sea through the outfall")), ("pump", C_PUMP, T("機場が海へ汲み出した", "pumped to the sea")))
    for y, c in zip(ys, rc):
        b = budget(c)
        x0 = 0.0
        for key, col, _ in parts:
            v = b[key]
            if v > 0.05:
                ax.barh(y, v, left=x0, height=0.44, color=col, lw=1.6, edgecolor="white")
                if v >= 7.0:
                    ax.text(x0 + v / 2, y, "%.0f" % v, ha="center", va="center", fontsize=8.4, color="white" if col in (C_GRAV, C_PUMP) else "#0b0b0b")
            x0 += v
    ax.set_yticks(ys)
    ax.set_yticklabels([case_label2(c) for c in rc], fontsize=8.6, color=INK)
    ax.set_xlim(0, 100)
    ax.set_ylim(-0.6, len(rc) - 0.4)
    ax.set_xlabel(T("総雨量 100 mm の行き先(12 時間後。mm)", "where the 100 mm of rain went (after 12 h; mm)"))
    style(ax, grid=None)
    ax.tick_params(axis="y", length=0)
    ax.legend(handles=[Patch(fc=col, ec="none", label=lab) for _, col, lab in parts], loc="upper center", bbox_to_anchor=(0.3, -0.2), ncol=2,
              frameon=False, fontsize=8.6, columnspacing=1.4, handlelength=1.2)
    title(ax, T("(c) 雨の行き先", "(c) Where the rain went"))
    save(fig, "ladder.png")


# ---------------------------------------------------------------- 図: 最大浸水深
def depth_map(ax, h, xmax=420.0):
    """浸水深の区分図(陸の列だけ。等高線は地盤高)"""
    xe = np.arange(NX - NSEA + 1) * DX
    ye = np.arange(NY + 1) * DX
    cmap = ListedColormap(DEPTH_COLS)
    norm = BoundaryNorm(DEPTH_EDGES, cmap.N)
    ax.add_patch(Rectangle((0, 0), gd.LX_LAND, gd.LY, fc=C_LAND, ec="none"))
    ax.pcolormesh(xe, ye, np.ma.masked_less(h, DEPTH_EDGES[0]), cmap=cmap, norm=norm)
    x, y, z = pad_edges(ZL)
    cs = ax.contour(x, y, z, levels=[0.7, 0.8, 0.9, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4], colors=INK2, linewidths=0.45)
    draw_plan(ax, labels=False)
    ax.set_xlim(-gd.LX_SEA, xmax)
    ax.set_xticks([0, 200, 400])
    return cs


def depth_legend(fig, ax, title_txt):
    labs = ["%.2f–%.1f m" % (DEPTH_EDGES[0], DEPTH_EDGES[1])] + ["%.1f–%.1f m" % (a, b) for a, b in zip(DEPTH_EDGES[1:-2], DEPTH_EDGES[2:-1])] \
        + [T("%.1f m 以上", "%.1f m or more") % DEPTH_EDGES[-2]]
    ax.legend(handles=[Patch(fc=c, ec="none", label=l) for c, l in zip(DEPTH_COLS, labs)], title=title_txt, loc="upper left",
              bbox_to_anchor=(1.03, 1.0), frameon=False, fontsize=8.6, title_fontsize=8.8, alignment="left")


def fig_maps():
    cases = ["both", "compound", "nopump"]
    if not all(have(c) for c in cases):
        print("skip maps.png (make run)")
        return
    fig, axs = plt.subplots(1, 3, figsize=(12.6, 4.9), gridspec_kw=dict(left=0.055, right=0.86, top=0.84, bottom=0.11, wspace=0.12))
    for ax, c in zip(axs, cases):
        h = np.loadtxt("result_%s/H9999.txt" % c)[:, NSEA:]
        depth_map(ax, h)
        fs = flood_stats(c)
        ax.set_title("%s\n%s" % (case_label(c), T("0.1 m 以上 %.1f ha・0.3 m 以上 %s ha・最大 %.2f m", "≥0.1 m: %.1f ha, ≥0.3 m: %s ha, max %.2f m")
                                         % (fs["a10"], ("%.2f" if fs["a30"] < 0.095 else "%.1f") % fs["a30"], fs["hmax"])),
                     loc="left", fontsize=9.6, color=INK)
        ax.plot([gd.DEP_X], [gd.DEP_Y], marker="o", ms=4.5, mfc=INK, mec="white", mew=0.8, zorder=6)
        ax.text(gd.DEP_X + 12, gd.DEP_Y + 5, "P2", fontsize=8.4, color=INK, va="center", path_effects=HALO)
        ax.set_xlabel(T("防潮堤からの距離 (m)", "distance from the seawall (m)"))
        ax.text(-gd.LX_SEA / 2, 30, T("海", "sea"), ha="center", fontsize=8.6, color=INK)
    axs[0].set_ylabel(T("北端からの距離 (m)", "distance from the north edge (m)"))
    for ax in axs[1:]:
        ax.tick_params(labelleft=False)
    depth_legend(fig, axs[2], T("最大浸水深", "maximum depth"))
    fig.suptitle(T("最大浸水深(12 時間の最大。海側の 480 m を表示。細い線は地盤高の等高線、太い線は防潮堤と幹線、□ はポンプ井)",
                   "Maximum flood depth over the 12 h (seaward 480 m shown; thin lines: ground contours; thick lines: seawall and trunk; □: pump well)"),
                 fontsize=10.5, x=0.055, ha="left", y=0.975)
    save(fig, "maps.png")


# ---------------------------------------------------------------- 図: 窪地を通る断面
def fig_profile():
    if not (have("rain") and have("compound")):
        print("skip profile.png (make run)")
        return
    panels = [("rain", 22, T("雨だけ: 雨のピーク(5.5 時間。潮位 0 m)", "Rain only: at the rain peak (5.5 h; tide 0 m)")),
              ("compound", 22, T("複合: 雨と高潮のピーク(5.5 時間。潮位 +2.0 m)", "Compound: rain and surge peaks (5.5 h; tide +2.0 m)")),
              ("compound", 27, T("複合: 6.75 時間(潮位 +1.0 m。浸水が最大)", "Compound: 6.75 h (tide +1.0 m; flooding at its maximum)")),
              ("compound", 30, T("複合: 7.5 時間(潮位 +0.4 m。吐口が開いて水が引く)", "Compound: 7.5 h (tide +0.4 m; the outfall has reopened and the water recedes)"))]
    fig, axs = plt.subplots(len(panels), 1, figsize=(12.0, 8.8), sharex=True, gridspec_kw=dict(left=0.065, right=0.975, top=0.895, bottom=0.07, hspace=0.34))
    jr = CELLS["dep"][1] - 1
    zr = ZL[jr]
    xs = np.concatenate([[0.0], XL, [gd.LX_LAND]])
    ext = lambda a: np.concatenate([[a[0]], a, [a[-1]]])
    zs = ext(zr)
    lead = dict(arrowstyle="-", color=INK2, lw=0.8)
    for n, (ax, (c, k, lab)) in enumerate(zip(axs, panels)):
        eta = float(tide_at(k * 0.25, gd.CASES[c][2]))
        hd = conduit_head(read_field(c, "Hgc", k))[jr, NSEA:]
        h = read_field(c, "H", k)[jr, NSEA:]
        ax.fill_between(xs, -1.6, zs, color=C_GROUND, lw=0)
        ax.fill_between(xs, zs - gd.BURY_B, zs - gd.BURY_B + gd.D_B, color="#a9a9a9", lw=0)
        ax.fill_between(xs, zs, ext(zr + np.where(h > 0.005, h, 0.0)), color="#6aabf1", lw=0)
        ax.fill_between([-gd.LX_SEA, 0], -1.6, eta, color="#9cc3ec", lw=0)
        ax.plot([0, 0], [-1.6, 3.5], color=INK, lw=2.6, solid_capstyle="butt")
        ax.plot(XL, hd, color=C_COMP if c == "compound" else INK, lw=2, solid_capstyle="round")
        ax.set_xlim(-gd.LX_SEA, 500)
        ax.set_ylim(-1.6, 3.7)
        ax.set_yticks([-1, 0, 1, 2, 3])
        ax.set_ylabel(T("標高 (m)", "elevation (m)"))
        style(ax, grid=None)
        title(ax, "(%s) %s" % ("abcd"[n], lab))
        ax.text(-gd.LX_SEA + 3, eta + 0.12, T("潮位 %+.1f m", "tide %+.1f m") % eta if eta else T("潮位 0 m", "tide 0 m"), fontsize=8.4, color=INK)
        kx = 330.0
        yk = np.interp(kx, XL, hd)
        ax.annotate(T("管の中の水頭", "head in the pipes"), (kx, yk), (kx + 30, yk + (1.25 if c == "rain" else -1.0)), arrowprops=lead, fontsize=8.6, color=INK)
        if n == 0:
            ax.annotate(T("地表", "ground"), (430, np.interp(430, XL, zr)), (450, 3.15), arrowprops=lead, fontsize=8.6, color=INK)
            ax.annotate(T("枝管網の管", "branch pipes"), (210, np.interp(210, XL, zr) - 1.3), (240, -1.25), arrowprops=lead, fontsize=8.6, color=INK)
            ax.annotate(T("窪地", "depression"), (gd.DEP_X, zr.min()), (gd.DEP_X - 10, 2.2), arrowprops=lead, fontsize=8.6, color=INK, ha="center")
            ax.annotate(T("防潮堤", "seawall"), (0, 3.3), (25, 3.15), arrowprops=lead, fontsize=8.6, color=INK)
        if h.max() > 0.03:
            ax.annotate(T("地表の水(窪地の底で %.2f m)", "water on the surface (%.2f m at the bottom of the depression)") % h.max(),
                        (gd.DEP_X + 10, zr.min() + 0.6 * h.max()), (150, 2.55), arrowprops=lead, fontsize=8.6, color=INK)
    axs[-1].set_xlabel(T("防潮堤からの距離 (m)", "distance from the seawall (m)"))
    fig.suptitle(T("窪地を通る東西の断面(北端から 130 m。幹線はこの 120 m 南):\n潮位が高い間は、管の中の水頭が低地の地表まで上がり、枡から水が出る",
                   "East–west section through the depression (130 m from the north edge; the trunk is 120 m to the south): while the tide is high,\nthe head in the pipes rises to the lowland surface and water comes out of the inlets"),
                 fontsize=10.5, x=0.065, ha="left", y=0.985)
    save(fig, "profile.png")


# ---------------------------------------------------------------- 図: 雨と高潮のピークのずれ
def lag_cases():
    return [(l, "compound" if l == 0 else "lag_%s%d" % ("m" if l < 0 else "p", abs(l))) for l in range(-4, 5)]


def depth_hours(case, thr):
    """窪地の底(プローブ 2)の水深が thr (m) 以上だった時間 (h)"""
    t, h = read_probe(case, 2)
    return float((h >= thr).sum() * (t[1] - t[0]))


def fig_lag():
    lc = lag_cases()
    if not all(have(c) for _, c in lc):
        print("skip lag.png (make run; make lag)")
        return
    fig = plt.figure(figsize=(12.6, 7.9))
    outer = fig.add_gridspec(2, 1, height_ratios=[1.45, 1.0], left=0.06, right=0.985, top=0.895, bottom=0.075, hspace=0.34)
    top = outer[0].subgridspec(3, 9, height_ratios=[0.55, 0.55, 1.5], hspace=0.16, wspace=0.09)
    bot = outer[1].subgridspec(1, 3, wspace=0.26)
    th = np.linspace(0, T_END, 721)
    t1, t2 = closed_window()
    res = {}
    for n, (lag, c) in enumerate(lc):
        ar, at, av = (fig.add_subplot(top[r, n]) for r in range(3))
        t, (ss, sg, st) = read_log(c)
        v = ss * AREA / 1e3
        tp, hp = read_probe(c, 2)
        res[lag] = dict(vmax=v.max(), hmax=hp.max(), d10=depth_hours(c, 0.1), d30=depth_hours(c, 0.3))
        for ax in (ar, at, av):
            ax.axvspan(t1, t2, color="#f1efe8", lw=0)
            style(ax)
            ax.set_xlim(0, T_END)
            ax.set_xticks([0, 6, 12])
            ax.set_xticklabels(["0", "6", "12" if n == len(lc) - 1 else ""])
            if n > 0:
                ax.tick_params(labelleft=False)
        ar.fill_between(th, rain_at(th, lag), color=C_RAIN, lw=0, alpha=0.85)
        ar.set_ylim(0, 60)
        ar.set_yticks([0, 50])
        at.plot(th, tide_at(th), color=C_TIDE, lw=1.6)
        at.set_ylim(0, 2.4)
        at.set_yticks([0, 2])
        av.plot(t, v, color=C_COMP, lw=2)
        av.fill_between(t, v, color=C_COMP, alpha=0.10, lw=0)
        av.set_ylim(0, 21.5)
        av.set_yticks([0, 5, 10, 15, 20])
        for ax in (ar, at):
            ax.tick_params(labelbottom=False)
        lab = T("同時", "together") if lag == 0 else (T("雨が %d 時間先", "rain %d h earlier") % -lag if lag < 0 else T("雨が %d 時間後", "rain %d h later") % lag)
        ar.set_title(lab, fontsize=9.3, color=INK)
        if v.max() > 2.5:
            av.text(11.7 if lag < 0 else 0.3, 21.0, T("最大\n%.1f 千 m³", "max\n%.1f k m³") % v.max(), fontsize=8.2, color=INK, va="top",
                    ha="right" if lag < 0 else "left")
        if n == 0:
            ar.set_ylabel(T("雨\n(mm/h)", "rain\n(mm/h)"))
            at.set_ylabel(T("潮位\n(m)", "tide\n(m)"))
            av.set_ylabel(T("地表の水の量\n(千 m³)", "water on the surface\n(thousand m³)"))
        if n == 4:
            av.set_xlabel(T("時刻 (時間)", "time (h)"))
    lags = np.array(sorted(res))
    specs = (("vmax", T("(b) 地表の水の量の最大 (千 m³)", "(b) Maximum water on the surface (thousand m³)"), None),
             ("hmax", T("(c) 窪地の底の最大浸水深 (m)", "(c) Maximum depth in the depression (m)"), None),
             ("d10", T("(d) 窪地の底が浸かっていた時間 (時間)", "(d) Hours the depression was under water"), "d30"))
    for n, (key, ttl, key2) in enumerate(specs):
        ax = fig.add_subplot(bot[n])
        y = np.array([res[l][key] for l in lags])
        ax.plot(lags, y, color=C_COMP, lw=2, marker="o", ms=7, mec="white", mew=1.5, zorder=3,
                label=T("水深 0.1 m 以上", "depth of 0.1 m or more") if key2 else None)
        if key2:
            y2 = np.array([res[l][key2] for l in lags])
            ax.plot(lags, y2, color="#a04310", lw=2, marker="s", ms=6, mec="white", mew=1.5, zorder=3, label=T("水深 0.3 m 以上", "depth of 0.3 m or more"))
            ax.legend(loc="upper right", frameon=False, fontsize=8.6)
        for l, v in zip(lags, y):
            if (key == "vmax" and v > 2.5) or (key == "hmax" and v > 0.05) or (key == "d10" and v > 0.05):
                ax.annotate(("%.1f" if key != "hmax" else "%.2f") % v, (l, v), ((-13 if l < 0 else 13), 7), textcoords="offset points",
                            ha="center", fontsize=8.4, color=INK)
        ax.set_xticks(lags)
        ax.set_xlim(-4.5, 4.5)
        ax.set_ylim(0, {"vmax": 19.5, "hmax": 0.58, "d10": 4.2}[key])
        if key == "vmax":
            ax.set_yticks([0, 5, 10, 15])
        ax.axvline(0, color=AXIS, lw=0.8)
        ax.set_xlabel(T("雨のピークのずれ(時間。負 = 雨が高潮より先)", "lag of the rain peak (h; negative = rain first)"))
        style(ax)
        title(ax, ttl)
    fig.text(0.06, 0.985, T("(a) 雨の時刻だけを 1 時間ずつずらした 9 ケース(雨の量・高潮・地下水位・機場は複合ケースと同じ。灰色の帯は吐口が閉じる時間帯)",
                            "(a) Nine cases that differ only in the timing of the rain (same rain, surge, water table and pumps as the compound case;\nthe grey band is when the outfall is closed)"),
             fontsize=10.5, color=INK, va="top")
    save(fig, "lag.png")
    return res


# ---------------------------------------------------------------- 図: 補足(下水道を通ってきた水の割合)
def fig_tracer():
    cases = [("tracer_m1", -1), ("tracer", 0)]
    if not all(have(c) for c, _ in cases):
        print("skip tracer.png (make supp)")
        return
    fig = plt.figure(figsize=(12.6, 7.9))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.0, 1.25], left=0.06, right=0.975, top=0.865, bottom=0.08, hspace=0.42, wspace=0.16)
    xe = np.arange(NX - NSEA + 1) * DX
    ye = np.arange(NY + 1) * DX
    cmap = ListedColormap(FRAC_COLS)
    norm = BoundaryNorm(FRAC_EDGES, cmap.N)
    t1, t2 = closed_window()
    out = {}
    for r, (c, lag) in enumerate(cases):
        w = read_wq(c)
        tw = w["time_s"] / 3600.0
        t, (ss, sg, st) = read_log(c)
        vs = np.interp(tw, t, ss) * AREA / 1e3
        vsew = w["mass_surface_g"] / 1e3
        k = int(np.argmax([read_field(c, "H", i)[:, NSEA:].sum() for i in range(49)]))
        h = read_field(c, "H", k)[:, NSEA:]
        cc = read_field(c, "C", k)[:, NSEA:]
        lab = T("雨が 1 時間先", "Rain 1 h earlier") if lag < 0 else T("雨と高潮のピークが同時(複合)", "Rain and surge together (compound)")
        km = vs.argmax()
        out[c] = dict(blow=w["in_gwc_g"][-1], frac=vsew[km] / vs[km], d10=depth_hours(c, 0.1), d30=depth_hours(c, 0.3), hmax=read_probe(c, 2)[1].max())
        # 割合の地図(水深 0.05 m 以上の所)
        ax = fig.add_subplot(gs[r, 0])
        ax.add_patch(Rectangle((0, 0), gd.LX_LAND, gd.LY, fc=C_LAND, ec="none"))
        ax.pcolormesh(xe, ye, np.ma.masked_where(h < 0.05, cc), cmap=cmap, norm=norm)
        x, y, z = pad_edges(ZL)
        ax.contour(x, y, z, levels=[0.7, 0.8, 0.9, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4, 2.6, 2.8], colors=INK2, linewidths=0.45)
        draw_plan(ax, labels=False)
        ax.set_xlim(-gd.LX_SEA, 620)
        ax.set_xticks([0, 200, 400, 600])
        ax.set_ylabel(T("北端からの距離 (m)", "distance from the north edge (m)"))
        if r == 1:
            ax.set_xlabel(T("防潮堤からの距離 (m)", "distance from the seawall (m)"))
        ax.plot([gd.DEP_X], [gd.DEP_Y], marker="o", ms=4.5, mfc=INK, mec="white", mew=0.8, zorder=6)
        ax.text(gd.DEP_X + 12, gd.DEP_Y + 5, "P2", fontsize=8.4, color=INK, va="center", path_effects=HALO)
        title(ax, "(%s) %s\n%s" % ("ac"[r], lab, T("%.2f 時間(浸水が最大)の割合", "share at %.2f h (maximum flooding)") % (k * 0.25)))
        labs = ["%d–%d %%" % (100 * a, 100 * min(b, 1.0)) for a, b in zip(FRAC_EDGES[:-1], FRAC_EDGES[1:])]
        ax.legend(handles=[Patch(fc=cl, ec="none", label=l) for cl, l in zip(FRAC_COLS, labs)], title=T("下水道を通ってきた\n水の割合", "share that came\nthrough the sewers"),
                  loc="center left", bbox_to_anchor=(0.5, 0.5), frameon=True, facecolor="white", edgecolor="none", framealpha=0.9, fontsize=8.6, title_fontsize=8.6, alignment="left")
        # 時系列: 地表の水のうち下水道を通ってきた分
        ax = fig.add_subplot(gs[r, 1])
        ax.axvspan(t1, t2, color="#f1efe8", lw=0)
        ax.fill_between(tw, vsew, color=C_COMP, alpha=0.35, lw=0)
        ax.plot(tw, vsew, color=C_COMP, lw=2, label=T("そのうち下水道を通ってきた水", "of which came through the sewers"))
        ax.plot(tw, vs, color=INK, lw=2, label=T("地表の水の量", "water on the surface"))
        ax.set_xlim(2, 9)
        ax.set_ylim(0, 18.5)
        ax.set_yticks([0, 5, 10, 15])
        ax.set_ylabel(T("千 m³", "thousand m³"))
        if r == 1:
            ax.set_xlabel(T("時刻 (時間)", "time (h)"))
        style(ax)
        title(ax, "(%s) %s" % ("bd"[r], T("噴出の合計 %.1f 千 m³。浸水が最大のときの割合 %d %%\n窪地の底が 0.1 m 以上浸かった時間 %.1f 時間",
                                         "Surcharge total %.1f thousand m³; share at maximum flooding %d %%\nbottom of the depression under 0.1 m or more for %.1f h")
                                 % (out[c]["blow"] / 1e3, round(100 * out[c]["frac"]), out[c]["d10"])))
        if r == 0:
            ax.legend(loc="upper left", frameon=False, fontsize=8.8, borderaxespad=0.2)
            ax.text(t2 - 0.08, 17.4, T("吐口が閉じる時間帯", "outfall closed"), ha="right", fontsize=8.6, color=INK)
    fig.suptitle(T("補足: 地表の水のうち、下水道を通ってきた水(枡から噴き出した水)の割合\n(噴出した水に濃度 1 を付けた保存性のトレーサ。地図は水深 0.05 m 以上の所。細い線は地盤高の等高線)",
                   "Supplement: share of the surface water that came through the sewers (surcharged from the inlets)\n(a conservative tracer with concentration 1 on the surcharged water; maps where the depth is 0.05 m or more; thin lines: ground contours)"),
                 fontsize=10.5, x=0.06, ha="left", y=0.985)
    save(fig, "tracer.png")
    return out


# ---------------------------------------------------------------- 数表
def tables():
    print("\n%-10s %9s %7s %7s %7s %7s | %6s %6s %6s %6s %6s %7s" % ("case", "Vmax(m3)", "t(h)", "hmax", "A>=0.1", "A>=0.3", "soil", "pipe", "grav", "pump", "surf", "resid"))
    for c in MAIN + [x for _, x in lag_cases() if x != "compound"]:
        if not have(c):
            continue
        b, fs = budget(c), flood_stats(c)
        print("%-10s %9.0f %7.2f %7.2f %7.2f %7.2f | %6.1f %6.1f %6.1f %6.1f %6.2f %7.3f | P2: hmax %.2f m, >=0.1 m %.2f h, >=0.3 m %.2f h"
              % (c, b["peak"], b["tpeak"], fs["hmax"], fs["a10"], fs["a30"], b["soil"], b["pipe"], b["grav"], b["pump"], b["surf"], b["resid"],
                 read_probe(c, 2)[1].max(), depth_hours(c, 0.1), depth_hours(c, 0.3)))
    if have("nopump"):
        b = budget("nopump")          # 機場がないので、雨 = 土 + 管 + 吐口 + 地表 が独立に確かめられる
        print("\nwater budget of nopump (mm): rain %.3f = soil %.3f + pipes %.3f + outfall %.3f + surface %.3f + residual %.3f"
              % (b["rain"], b["soil"], b["pipe"], b["grav"], b["surf"], b["rain"] - b["soil"] - b["pipe"] - b["grav"] - b["surf"]))
    for c in ("chk_dt", "chk_slot", "chk_epsh", "chk_dx10"):
        if have(c) and have("compound"):
            g = gd.build(gd.GEOMS[gd.CASES[c][0]][0])
            t, (ss, sg, st) = read_log(c)
            h9 = np.loadtxt("result_%s/H9999.txt" % c)[:, g["nsea"]:]
            cell = g["dx"] ** 2 / 1e4
            print("%-10s Vmax %7.0f m3 at %.2f h, hmax %.2f m, A>=0.1 %.2f ha, A>=0.3 %.2f ha, outfall %.0f m3"
                  % (c, ss.max() * AREA, t[ss.argmax()], h9.max(), (h9 >= 0.1).sum() * cell, (h9 >= 0.3).sum() * cell, outfall_total(c)))


FIGS = {"setup": fig_setup, "mechanism": fig_mechanism, "ladder": fig_ladder, "maps": fig_maps, "profile": fig_profile,
        "lag": fig_lag, "tracer": fig_tracer}

if __name__ == "__main__":
    picked = [a for a in sys.argv[1:] if a in FIGS]
    if "tables" not in sys.argv[1:]:
        for n in picked or list(FIGS):
            FIGS[n]()
    if not picked:
        tables()
