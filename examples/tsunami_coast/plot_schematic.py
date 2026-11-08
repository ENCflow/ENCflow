#!/usr/bin/env python3
"""tsunami_coast の説明図(計算結果を使わない。make が作る入力 z.txt・bm/・bm_off/ と式だけ)。

  figs/setup.png        構成: 平面(地形・断層面の投影・プローブ・境界)と湾の軸の縦断(地形と断層面)
  figs/deformation.png  地盤変位: 最終変位の地図と、湾の軸に沿う変位の内訳(沿岸の断層 1・3 と沖の断層 2)
  figs/mechanism.png    仕組み: 地盤の動きの時刻歴(時刻歴ありと瞬時)、地盤と一緒に水面が動く規則の模式図、
                        長波の速さ √(gh) で海岸まで進む時間
引数 en で英語ラベル版を en/figs/ に描く(形・値・描画処理は共通で、ラベルだけが切り替わる)。
入力がなければ先に make を実行する。
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm, Normalize, LinearSegmentedColormap
from matplotlib.patches import Rectangle, Polygon, FancyArrowPatch

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


here = os.path.dirname(os.path.abspath(__file__))
os.chdir(here)
FIGDIR = "en/figs" if EN else "figs"
os.makedirs(FIGDIR, exist_ok=True)
plt.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAPGothic", "IPAGothic", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
for f in ("z.txt", "bm/bmlist.txt", "bm_off/disp_0010.txt"):
    if not os.path.isfile(f):
        sys.exit("%s がありません。先に make を実行してください / %s is missing; run make first" % (f, f))

C_INK, C_MUTED = "#1f1f1f", "#8a8983"
C_S1, C_S2, C_S3 = "#eb6834", "#7b4fb3", "#1baf7a"     # 深部・浅部(沖)・分岐断層
C_SEA, C_LAND, C_WATER = "#2a78d6", "#d9c7a0", "#cfe3f3"
DX = 0.5                                                 # km
NX, NY = 240, 160
G = 9.8
x = (np.arange(NX) + 0.5) * DX
y = (NY - np.arange(NY) - 0.5) * DX                      # km(北が先頭行)
z0 = np.loadtxt("z.txt")
JB = NY - 80                                             # 湾の軸の行(0 始まり。y = 40.25 km、プローブ 1・2・5〜7 の行)
# 断層(fault2disp_all.txt。x_top・y_top は上端の中心、走向 180° で西へ傾斜。km・度・m・s)
SEGS = [dict(n=1, xt=60.0, yt=40.0, dt=8.0, dip=20.0, L=80.0, W=40.0, slip=5.0, tr=0.0, trise=20.0, c=C_S1),
        dict(n=2, xt=100.0, yt=40.0, dt=5.0, dip=15.0, L=80.0, W=30.0, slip=8.0, tr=30.0, trise=20.0, c=C_S2),
        dict(n=3, xt=22.0, yt=15.0, dt=1.0, dip=60.0, L=20.0, W=8.0, slip=2.0, tr=0.0, trise=10.0, c=C_S3)]
SEGNAME = {1: T("深部(海岸の下)", "deep (under the coast)"), 2: T("浅部(沖)", "shallow (offshore)"),
           3: T("分岐断層(岬の下)", "splay (under the cape)")}
# プローブ(param の pbxy。セル番号 → セル中心 km)
PIJ = {1: (19, 80), 2: (40, 80), 3: (43, 30), 4: (43, 130), 5: (81, 80), 6: (181, 80), 7: (15, 80)}
PXY = {n: ((i - 0.5) * DX, (NY - j + 0.5) * DX) for n, (i, j) in PIJ.items()}


def style(ax, grid=True):
    if grid:
        ax.grid(color="#eceae6", lw=0.6)
        ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(labelsize=8.5)


def panel_title(ax, s, y=1.02):
    ax.text(0.0, y, s, transform=ax.transAxes, fontsize=11, ha="left", va="bottom", color=C_INK)


def bathy(ax):
    sea = np.ma.masked_where(z0 >= 0, -z0)
    land = np.ma.masked_where(z0 < 0, z0)
    ext = [0, NX * DX, 0, NY * DX]
    ax.imshow(sea, extent=ext, origin="upper", cmap="Blues", norm=LogNorm(1.5, 2500), interpolation="nearest")
    cl = LinearSegmentedColormap.from_list("land", ["#efe6cf", "#cdb98c"])
    ax.imshow(land, extent=ext, origin="upper", cmap=cl, norm=Normalize(0, 40), interpolation="nearest")
    ax.contour(x, y, z0, levels=[0], colors=C_INK, linewidths=0.9)
    cs = ax.contour(x, y, z0, levels=[-1000 + 1, -200], colors="#4a6b8a", linewidths=0.6, linestyles="--")
    return cs


def fault_rect(ax, s, alpha=0.18, lw=1.6, label=True):
    xw = s["xt"] - s["W"] * np.cos(np.radians(s["dip"]))
    y1, y2 = s["yt"] - s["L"] / 2, s["yt"] + s["L"] / 2
    ax.add_patch(Rectangle((xw, y1), s["xt"] - xw, y2 - y1, facecolor=s["c"], alpha=alpha, edgecolor="none", zorder=3))
    ax.add_patch(Rectangle((xw, y1), s["xt"] - xw, y2 - y1, facecolor="none", edgecolor=s["c"], lw=0.8, ls="--", zorder=4))
    ax.plot([s["xt"], s["xt"]], [y1, y2], color=s["c"], lw=lw, zorder=5)
    n = max(2, int(s["L"] / 10))
    for yy in np.linspace(y1 + s["L"] / (2 * n), y2 - s["L"] / (2 * n), n):   # 歯 = 傾斜の向き(西)
        ax.add_patch(Polygon([[s["xt"], yy - 1.0], [s["xt"], yy + 1.0], [s["xt"] - 1.6, yy]], closed=True,
                             facecolor=s["c"], edgecolor="none", zorder=5))
    return xw, y1, y2


# ============================== figs/setup.png ==============================
def fig_setup():
    fig = plt.figure(figsize=(12.6, 10.4), facecolor="white")
    gs0 = fig.add_gridspec(2, 1, height_ratios=[1.0, 0.70], hspace=0.20, top=0.93)
    gs = gs0[0].subgridspec(1, 2, width_ratios=[1.0, 0.33], wspace=0.03)
    gsb = gs0[1].subgridspec(2, 1, height_ratios=[0.30, 0.36], hspace=0.10)
    ax = fig.add_subplot(gs[0, 0])
    cs = bathy(ax)
    ax.clabel(cs, fmt={-999.0: "1000 m", -200.0: "200 m"}, fontsize=7.5, inline=True)
    for s in SEGS:
        xw, y1, y2 = fault_rect(ax, s)
    ax.text(62, 77.0, "1", color=C_S1, fontsize=11, ha="left", va="top")
    ax.text(102, 77.0, "2", color=C_S2, fontsize=11, ha="left", va="top")
    ax.text(23.4, 7.0, "3", color=C_S3, fontsize=11, ha="left", va="center")
    for n, (px, py) in PXY.items():
        ax.plot(px, py, "o", ms=5, mfc="white", mec=C_INK, mew=1.0, zorder=7)
        dx, dy, ha = {1: (-1.2, 2.0, "right"), 2: (1.0, 2.0, "left"), 3: (1.2, 1.6, "left"), 4: (1.2, -2.4, "left"),
                      5: (1.2, 1.8, "left"), 6: (1.2, 1.8, "left"), 7: (-1.2, -2.6, "right")}[n]
        ax.text(px + dx, py + dy, str(n), fontsize=9, color=C_INK, ha=ha, va="center", zorder=8,
                bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.85))
    ax.text(14, 40, T("湾", "bay"), fontsize=9, color=C_INK, ha="center", va="center")
    ax.text(5, 70, T("陸", "land"), fontsize=9, color="#6d5c34", ha="center")
    ax.text(30, 3, T("棚", "shelf"), fontsize=8.5, color="white", ha="center")
    ax.text(66, 3, T("斜面", "slope"), fontsize=8.5, color="white", ha="center")
    ax.text(111, 3, T("深海\n1000 m", "deep\n1000 m"), fontsize=8.5, color="white", ha="center")
    ax.text(121.5, 40, T("長波放射", "radiation"), fontsize=8.5, color=C_MUTED, ha="left", va="center", rotation=90)
    ax.text(60, 81.2, T("長波放射", "radiation"), fontsize=8.5, color=C_MUTED, ha="center", va="bottom")
    ax.set_xlim(0, NX * DX)
    ax.set_ylim(0, NY * DX)
    ax.set_aspect("equal")
    ax.set_xlabel("x (km)", fontsize=9)
    ax.set_ylabel("y (km)", fontsize=9)
    style(ax, grid=False)
    panel_title(ax, T("(a) 平面(上が北)", "(a) Plan (north up)"), y=1.05)

    axn = fig.add_subplot(gs[0, 1])
    axn.axis("off")
    lines = [
        (C_S1, T("1 深部: すべり 5 m、t = 0〜20 s\n上端 x = 60 km・深さ 8 km、幅 40 km、傾斜 20°",
                 "1 deep: slip 5 m, t = 0–20 s\ntop x = 60 km, depth 8 km, width 40 km, dip 20°")),
        (C_S2, T("2 浅部(沖): すべり 8 m、t = 30〜50 s\n上端 x = 100 km・深さ 5 km、幅 30 km、傾斜 15°",
                 "2 shallow (offshore): slip 8 m, t = 30–50 s\ntop x = 100 km, depth 5 km, width 30 km, dip 15°")),
        (C_S3, T("3 分岐断層: すべり 2 m、t = 0〜10 s\n上端 x = 22 km, y = 15 km・深さ 1 km、\n幅 8 km、傾斜 60°",
                 "3 splay: slip 2 m, t = 0–10 s\ntop x = 22 km, y = 15 km, depth 1 km,\nwidth 8 km, dip 60°")),
    ]
    yy = 0.98
    for col, txt in lines:
        axn.add_patch(Rectangle((0.0, yy - 0.045), 0.07, 0.035, transform=axn.transAxes, facecolor=col, alpha=0.35,
                                edgecolor=col))
        axn.text(0.10, yy, txt, transform=axn.transAxes, fontsize=8.3, va="top", linespacing=1.3)
        yy -= 0.155 if txt.count("\n") < 2 else 0.2
    notes = T("矩形 = 断層面を地表へ投影した範囲\n太線 = 断層面の上端(三角は傾斜の向き)\nどれも逆断層(すべり角 90°。上盤が上がる)\n\n"
              "○ = プローブ 1〜7\n1 湾の頭(水深 4 m)  2 湾口\n3 湾の外の海岸(北)  4 南の岬の海岸\n5 棚  6 沖の断層の上\n7 湾奥の陸(沈降で浸水する平野)\n\n"
              "格子 240 × 160、Δx = Δy = 500 m\n西は壁、東・北・南は長波放射\n海は「解く海」(静水面 0)",
              "rectangle = surface projection of the fault plane\nthick line = top edge (triangles point down-dip)\nall reverse faults (rake 90°: hanging wall up)\n\n"
              "○ = probes 1–7\n1 bay head (depth 4 m)  2 bay mouth\n3 coast outside the bay (north)\n4 coast of the southern cape  5 shelf\n6 above the offshore fault\n7 land at the bay head (flooded by subsidence)\n\n"
              "grid 240 × 160, Δx = Δy = 500 m\nwest: wall; east, north, south: radiation\nthe sea is solved (still water level 0)")
    axn.text(0.0, yy - 0.01, notes, transform=axn.transAxes, fontsize=8.1, va="top", color=C_INK, linespacing=1.32)

    # ---- (b) 縦断: 地形 ----
    axp = fig.add_subplot(gsb[0])
    zr = z0[JB]
    axp.fill_between(x, np.minimum(zr, 0), 0, color=C_WATER, lw=0)
    axp.fill_between(x, zr, -2000, color=C_LAND, lw=0, alpha=0.8)
    axp.plot(x, zr, color=C_INK, lw=1.0)
    axp.axhline(0, color=C_SEA, lw=0.8)
    axp.set_yscale("symlog", linthresh=10)
    axp.set_ylim(-1300, 30)
    axp.set_yticks([10, 0, -10, -100, -1000])
    axp.set_yticklabels(["10", "0", "−10", "−100", "−1000"])
    axp.set_xlim(0, NX * DX)
    axp.set_ylabel(T("標高 (m)", "elevation (m)"), fontsize=9)
    style(axp)
    for xx, lab, yv in ((5.5, T("海岸平野", "coastal plain"), 14), (14, T("湾(2→25 m)", "bay (2→25 m)"), -4),
                        (30, T("棚(25→200 m)", "shelf (25→200 m)"), -40), (60, T("斜面(200→1000 m)", "slope (200→1000 m)"), -230),
                        (100, T("深海(1000 m)", "deep sea (1000 m)"), -600)):
        axp.text(xx, yv, lab, fontsize=8.2, color=C_INK, ha="center", va="center")
    axp.tick_params(labelbottom=False)
    panel_title(axp, T("(b) 湾の軸(y = 40 km)の縦断: 地形(縦軸は 10 m より深い所を対数で縮めた)と断層面",
                       "(b) Section along the bay axis (y = 40 km): terrain (depths beyond 10 m compressed logarithmically) and fault planes"))

    # ---- (b) 縦断: 断層面(縦横同じ縮尺) ----
    axf = fig.add_subplot(gsb[1], sharex=axp)
    axf.fill_between([0, 120], 0, 26, color="#f3efe6", lw=0)
    axf.plot(x, np.maximum(-zr, 0) / 1000.0, color=C_SEA, lw=0.9)
    for s in SEGS:
        c, sd = np.cos(np.radians(s["dip"])), np.sin(np.radians(s["dip"]))
        xb, db = s["xt"] - s["W"] * c, s["dt"] + s["W"] * sd
        ls = "--" if s["n"] == 3 else "-"
        axf.plot([s["xt"], xb], [s["dt"], db], color=s["c"], lw=3.0, ls=ls, solid_capstyle="round")
        xm, dm = (s["xt"] + xb) / 2, (s["dt"] + db) / 2
        ux, ud = c, -sd                                  # 上り傾斜の向き(東・上)
        nx_, nd_ = -sd, -c                               # 上盤側(西上)へのずらし
        off = 1.4 if s["n"] != 3 else 0.9
        a1 = FancyArrowPatch((xm - 2.5 * ux + off * nx_, dm - 2.5 * ud + off * nd_), (xm + 2.5 * ux + off * nx_, dm + 2.5 * ud + off * nd_),
                             arrowstyle="-|>", mutation_scale=9, color=s["c"], lw=1.2)
        a2 = FancyArrowPatch((xm + 2.5 * ux - off * nx_, dm + 2.5 * ud - off * nd_), (xm - 2.5 * ux - off * nx_, dm - 2.5 * ud - off * nd_),
                             arrowstyle="-|>", mutation_scale=9, color=s["c"], lw=1.2)
        if s["n"] != 3:
            axf.add_patch(a1)
            axf.add_patch(a2)
    axf.text(24.0, 23.8, T("1 深部: 5 m、t = 0〜20 s", "1 deep: 5 m, t = 0–20 s"), color=C_S1, fontsize=8.5, ha="left")
    axf.text(72.0, 15.6, T("2 浅部: 8 m、t = 30〜50 s", "2 shallow: 8 m, t = 30–50 s"), color=C_S2, fontsize=8.5, ha="left")
    axf.text(10.5, 9.5, T("3 分岐断層(y = 15 km の断面を重ねた)", "3 splay (section at y = 15 km overlaid)"), color=C_S3, fontsize=8.0,
             ha="left")
    axf.set_ylim(25, -1)
    axf.set_xlim(0, NX * DX)
    axf.set_xlabel("x (km)", fontsize=9)
    axf.set_ylabel(T("深さ (km)", "depth (km)"), fontsize=9)
    style(axf, grid=False)
    axf.text(119.5, 24.0, T("縦横ほぼ同じ縮尺。矢印は上盤(西側)が上り傾斜へずれる向き", "vertical and horizontal scales nearly equal; arrows: the hanging wall (west side) moves up-dip"),
             fontsize=8, color=C_MUTED, ha="right", va="bottom")

    fig.suptitle(T("tsunami_coast の構成(入力ファイルから描いた図で、計算結果ではない)",
                   "Setup of tsunami_coast (drawn from the input files; not computed results)"), fontsize=13, y=0.985)
    out = os.path.join(FIGDIR, "setup.png")
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print("saved", out)


# ============================== figs/deformation.png ==============================
def fig_deformation():
    d = np.loadtxt("bm/disp_0010.txt")
    doff = np.loadtxt("bm_off/disp_0010.txt")
    fig = plt.figure(figsize=(13.2, 5.4), facecolor="white")
    gs = fig.add_gridspec(2, 2, width_ratios=[1.25, 1.0], height_ratios=[1.0, 0.55], hspace=0.12, wspace=0.2)
    ax0 = fig.add_subplot(gs[:, 0])
    im = ax0.imshow(d, extent=[0, 120, 0, 80], origin="upper", cmap="RdBu_r", vmin=-3.5, vmax=3.5)
    ax0.contour(x, y, z0, levels=[0], colors="k", linewidths=0.8)
    ax0.contour(x, y, z0, levels=[-999, -200], colors="#52514e", linewidths=0.5, linestyles="--")
    for s in SEGS:
        y1, y2 = s["yt"] - s["L"] / 2, s["yt"] + s["L"] / 2
        ax0.plot([s["xt"], s["xt"]], [y1, y2], color=s["c"], lw=1.6)
        ax0.text(s["xt"] + 1.0, y2 - 2.0 if s["n"] != 3 else y1 - 2.5, str(s["n"]), color=s["c"], fontsize=10,
                 va="center")
    for n, (px, py) in PXY.items():
        ax0.plot(px, py, "o", ms=4, mfc="white", mec=C_INK, mew=0.9)
    ax0.axhline(PXY[1][1], color=C_INK, lw=0.7, ls=":")
    ax0.set_xlabel("x (km)", fontsize=9)
    ax0.set_ylabel("y (km)", fontsize=9)
    ax0.tick_params(labelsize=8.5)
    cb = plt.colorbar(im, ax=ax0, fraction=0.03, pad=0.02)
    cb.set_label(T("最終の地盤変位 (m)", "final ground displacement (m)"), fontsize=9)
    panel_title(ax0, T("(a) 最終の地盤変位(赤 = 隆起、青 = 沈降)。黒 = 海岸線、破線 = 200・1000 m 等深線、\n色線 = 断層面の上端、○ = プローブ、点線 = (b) の断面",
                       "(a) Final ground displacement (red = uplift, blue = subsidence);\nblack = coastline, dashed = 200 and 1000 m isobaths,\ncoloured lines = fault top edges, ○ = probes, dotted = section (b)"), y=1.01)

    ax1 = fig.add_subplot(gs[0, 1])
    ax1.axhline(0, color=C_MUTED, lw=0.7)
    ax1.fill_between(x, d[JB] - doff[JB], 0, color=C_S1, alpha=0.18, lw=0)
    ax1.plot(x, d[JB] - doff[JB], color=C_S1, lw=1.5, label=T("沿岸の断層 1・3(t = 0〜20 s)", "coastal faults 1, 3 (t = 0–20 s)"))
    ax1.plot(x, doff[JB], color=C_S2, lw=1.5, label=T("沖の断層 2(t = 30〜50 s)", "offshore fault 2 (t = 30–50 s)"))
    ax1.plot(x, d[JB], color=C_INK, lw=2.0, label=T("最終変位(合計)", "final displacement (sum)"))
    ax1.set_xlim(0, 120)
    ax1.set_ylim(-1.8, 3.8)
    ax1.set_ylabel(T("変位 (m)", "displacement (m)"), fontsize=9)
    ax1.legend(loc="upper left", fontsize=8, frameon=False)
    ax1.tick_params(labelbottom=False)
    style(ax1)
    ax1.annotate(T("海岸〜湾の沈降 −0.6 m", "subsidence of the coast and bay −0.6 m"), xy=(12, -0.62), xytext=(4, -1.55), fontsize=8,
                 color=C_S1, arrowprops=dict(arrowstyle="-", color=C_S1, lw=0.7))
    ax1.annotate(T("沿岸の断層だけ: +2.2 m\n沖の沈降と合計: +1.4 m", "faults 1+3 alone: +2.2 m\nsum with fault 2: +1.4 m"),
                 xy=(58, 1.42), xytext=(82, -1.0), fontsize=7.8, color=C_INK, va="center", arrowprops=dict(arrowstyle="-", color=C_MUTED, lw=0.7))
    panel_title(ax1, T("(b) 湾の軸 y = 40 km に沿う変位の内訳", "(b) Displacement along the bay axis y = 40 km, by source"))

    ax2 = fig.add_subplot(gs[1, 1], sharex=ax1)
    zr = z0[JB]
    ax2.fill_between(x, np.minimum(zr, 0), 0, color=C_WATER, lw=0)
    ax2.fill_between(x, zr, -1200, color=C_LAND, lw=0, alpha=0.8)
    ax2.plot(x, zr, color=C_INK, lw=1.0)
    ax2.set_ylim(-1100, 100)
    ax2.set_xlabel("x (km)", fontsize=9)
    ax2.set_ylabel(T("標高 (m)", "elevation (m)"), fontsize=9)
    style(ax2)
    fig.suptitle(T("断層による地盤変位(fault2disp の出力 bm/ から描いた図で、計算結果ではない)",
                   "Ground displacement by the faults (drawn from the fault2disp output bm/; not computed results)"), fontsize=12.5, y=1.04)
    out = os.path.join(FIGDIR, "deformation.png")
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print("saved", out)


# ============================== figs/mechanism.png ==============================
def bm_series():
    t, f = [], []
    for line in open("bm/bmlist.txt"):
        if line.strip().startswith("#") or not line.strip():
            continue
        a, b = line.split()[:2]
        t.append(float(a))
        f.append(np.loadtxt(b))
    return np.array(t), np.array(f)


def sketch(ax, x0, kind):
    """地盤(茶)と水面(青)の前(破線)と後(実線)。kind = 'up'(海底の隆起)/'down'(湾の沈降)/'land'(陸の沈降)"""
    w, base = 3.0, 0.0
    if kind == "up":
        bed0 = np.array([[x0, 0.6], [x0 + w, 0.6]])
        ax.fill_between([x0, x0 + w], base, 0.6, color=C_LAND, lw=0)
        xs = np.linspace(x0, x0 + w, 50)
        bump = 0.45 * np.exp(-((xs - x0 - w / 2) / 0.6) ** 2)
        ax.fill_between(xs, 0.6, 0.6 + bump, color=C_LAND, lw=0)
        ax.fill_between(xs, 0.6 + bump, 1.6 + bump, color=C_WATER, lw=0)
        ax.plot(xs, 0.6 + bump, color="#7a6a4c", lw=1.2)
        ax.plot(xs, 1.6 + bump, color=C_SEA, lw=1.4)
        ax.plot([x0, x0 + w], [1.6, 1.6], color=C_SEA, lw=0.9, ls="--")
        ax.plot(bed0[:, 0], bed0[:, 1], color="#7a6a4c", lw=0.9, ls="--")
        for sgn in (-1, 1):
            ax.add_patch(FancyArrowPatch((x0 + w / 2 + sgn * 0.5, 2.25), (x0 + w / 2 + sgn * 1.35, 2.25), arrowstyle="-|>",
                                         mutation_scale=9, color=C_SEA, lw=1.1))
        return T("海底の隆起: 水面も同じだけ\n上がり、波になって広がる", "seabed uplift: the surface\nrises as much and spreads\nas waves")
    if kind == "down":
        xs = np.linspace(x0, x0 + w, 50)
        dip_ = 0.4 * np.exp(-((xs - x0 - w / 2) / 0.7) ** 2)
        ax.fill_between(xs, base, 0.9 - dip_, color=C_LAND, lw=0)
        ax.fill_between(xs, 0.9 - dip_, 1.6 - dip_, color=C_WATER, lw=0)
        ax.plot(xs, 0.9 - dip_, color="#7a6a4c", lw=1.2)
        ax.plot(xs, 1.6 - dip_, color=C_SEA, lw=1.4)
        ax.plot([x0, x0 + w], [1.6, 1.6], color=C_SEA, lw=0.9, ls="--")
        ax.plot([x0, x0 + w], [0.9, 0.9], color="#7a6a4c", lw=0.9, ls="--")
        for sgn in (-1, 1):
            ax.add_patch(FancyArrowPatch((x0 + w / 2 + sgn * 1.4, 1.95), (x0 + w / 2 + sgn * 0.45, 1.95), arrowstyle="-|>",
                                         mutation_scale=9, color=C_SEA, lw=1.1))
        return T("湾の底の沈降: 水面も下がり、\n周りから水が流れ込む(押し波)", "bay floor subsides: the\nsurface drops and water\nflows in (a flood wave)")
    xs = np.linspace(x0, x0 + w, 60)
    land0 = np.where(xs < x0 + 1.2, 1.25 + 0.25 * (x0 + 1.2 - xs), 1.25 - 0.55 * (xs - x0 - 1.2))
    land1 = land0 - np.where(xs < x0 + 2.2, 0.35, 0.35 * np.maximum(0, 1 - (xs - x0 - 2.2) / 0.8))
    sea = 1.0
    ax.fill_between(xs, base, land1, color=C_LAND, lw=0)
    ax.fill_between(xs, land1, sea, where=land1 < sea, color=C_WATER, lw=0, interpolate=True)
    ax.plot(xs, land1, color="#7a6a4c", lw=1.2)
    ax.plot(xs, land0, color="#7a6a4c", lw=0.9, ls="--")
    ax.plot([x0, x0 + w], [sea, sea], color=C_SEA, lw=1.4)
    ax.add_patch(FancyArrowPatch((x0 + 2.75, 1.25), (x0 + 1.25, 1.25), arrowstyle="-|>", mutation_scale=9, color=C_SEA, lw=1.1))
    ax.text(x0 + 0.1, 1.85, T("陸", "land"), fontsize=7.5, color="#6d5c34")
    ax.text(x0 + w - 0.1, 1.85, T("海", "sea"), fontsize=7.5, color=C_SEA, ha="right")
    return T("陸の沈降: 海面下になった\n平野へ海水が入る(浸水)", "land subsides: the sea\nenters the plain now\nbelow sea level")


def fig_mechanism():
    t, f = bm_series()
    dfin = f[-1]
    fig = plt.figure(figsize=(12.8, 9.0), facecolor="white")
    gs = fig.add_gridspec(2, 2, width_ratios=[1.0, 1.08], height_ratios=[1.0, 0.95], hspace=0.42, wspace=0.18, top=0.92)

    # ---- (a) 地盤の動きの時刻歴 ----
    ax = fig.add_subplot(gs[0, 0])
    pts = [(98.75, 40.25, C_S2, T("沖の隆起の頂(x = 99 km)", "crest of the offshore uplift (x = 99 km)")),
           (57.75, 40.25, C_S1, T("斜面の隆起の頂(x = 58 km)", "crest of the slope uplift (x = 58 km)")),
           (PXY[4][0], PXY[4][1], C_S3, T("南の岬の海岸(プローブ 4)", "coast of the southern cape (probe 4)")),
           (PXY[1][0], PXY[1][1], C_SEA, T("湾の頭(プローブ 1)", "bay head (probe 1)"))]
    ax.axvspan(0, 20, color=C_S1, alpha=0.08, lw=0)
    ax.axvspan(30, 50, color=C_S2, alpha=0.08, lw=0)
    ax.text(10, 3.75, T("1・3 が動く", "1, 3 move"), fontsize=8, color=C_S1, ha="center")
    ax.text(40, 3.75, T("2 が動く", "2 moves"), fontsize=8, color=C_S2, ha="center")
    for px, py, col, lab in pts:
        i, j = int(px / DX), NY - 1 - int(py / DX)
        tt = np.concatenate([t, [60.0]])
        vv = np.concatenate([f[:, j, i], [f[-1, j, i]]])
        ax.plot(tt, vv, color=col, lw=2.0, marker="o", ms=3)
        ax.plot([0, 0, 60], [0, dfin[j, i], dfin[j, i]], color=col, lw=1.0, ls="--")
        ax.text(61, dfin[j, i], "%+.2f m" % dfin[j, i], fontsize=8, color=col, va="center")
    ax.axhline(0, color=C_MUTED, lw=0.7)
    ax.set_xlim(-2, 68)
    ax.set_ylim(-1.3, 4.0)
    ax.set_xlabel(T("時刻 t (s)", "time t (s)"), fontsize=9)
    ax.set_ylabel(T("地盤の変位 (m)", "ground displacement (m)"), fontsize=9)
    for (px, py, col, lab), (tx, ty) in zip(pts, ((21.0, 3.15), (21.0, 2.42), (41.0, 0.40), (31.0, -0.47))):
        ax.text(tx, ty, lab, fontsize=7.8, color=col, ha="left", va="center")
    ax.text(66, -1.27, T("実線 = 時刻歴あり(bm/ の 5 s 刻み 11 枚)\n破線 = 瞬時変位(最終変位を t = 0 に)",
                         "solid = with time history (bm/, 11 snapshots every 5 s)\ndashed = instantaneous (final at t = 0)"),
            fontsize=7.6, color=C_MUTED, ha="right", va="bottom")
    style(ax)
    panel_title(ax, T("(a) 地盤の動きの時刻歴(fn_bedmotion が読む変位)", "(a) Time history of the ground motion (what fn_bedmotion reads)"))

    # ---- (b) 模式図 ----
    axs = fig.add_subplot(gs[0, 1])
    axs.set_xlim(-0.2, 11.4)
    axs.set_ylim(-1.15, 3.1)
    axs.axis("off")
    for k, kind in enumerate(("up", "down", "land")):
        x0 = 0.2 + 3.85 * k
        cap = sketch(axs, x0, kind)
        axs.text(x0, -0.12, cap, fontsize=8, va="top", linespacing=1.25)
    axs.text(0.2, 2.95, T("規則: 地盤高 z を時刻歴で動かし、水柱 h は変えない(陸・海とも)。破線 = 動く前、実線 = 動いた直後",
                          "rule: the ground height z is moved in time and the water column h is kept (on land and sea);\ndashed = before, solid = just after"),
             fontsize=8.3, va="top", linespacing=1.3)
    panel_title(axs, T("(b) 地盤と一緒に水面が動く(模式図。形は説明用)", "(b) The water surface moves with the ground (schematic; shapes illustrative)"))

    # ---- (c) 長波の到達時間 ----
    axc = fig.add_subplot(gs[1, :])
    zr = z0[JB]
    i0 = int(20.0 / DX)
    h = np.maximum(-zr, 0.1)
    dt_cell = DX * 1000.0 / np.sqrt(G * h) / 60.0       # 分
    tt = np.full(NX, np.nan)
    for i in range(i0, NX):
        tt[i] = dt_cell[i0:i + 1].sum() - 0.5 * (dt_cell[i0] + dt_cell[i])
    axc.plot(x, tt, color=C_INK, lw=2.0, label=T("海岸(湾口 x = 20 km)まで $\\sqrt{gh}$ で進む時間",
                                                   "time to reach the coast (bay mouth, x = 20 km) at $\\sqrt{gh}$"))
    axc.set_xlim(0, 120)
    axc.set_ylim(0, 30)
    axc.set_xlabel("x (km)", fontsize=9)
    axc.set_ylabel(T("到達までの時間 (分)", "travel time (min)"), fontsize=9)
    style(axc)
    for xx, col, obs in ((57.75, C_S1, 15.9), (98.75, C_S2, 23.9)):
        i = int(xx / DX)
        axc.plot([xx], [tt[i]], "o", color=col, ms=6, zorder=5)
        axc.annotate(T("%.1f 分(湾口の計算の山 %.1f 分)" % (tt[i], obs), "%.1f min (peak at the bay mouth in the run: %.1f min)" % (tt[i], obs)),
                     xy=(xx, tt[i]), xytext=(xx - 30 if xx > 80 else xx + 2, tt[i] + 3.2), fontsize=8.3, color=col,
                     arrowprops=dict(arrowstyle="-", color=col, lw=0.7))
    axd = axc.twinx()
    d = dfin[JB]
    axd.fill_between(x, d, 0, where=d > 0, color="#e8b4a4", alpha=0.45, lw=0, interpolate=True)
    axd.fill_between(x, d, 0, where=d < 0, color="#a9c8ea", alpha=0.45, lw=0, interpolate=True)
    axd.plot(x, d, color="#b0624a", lw=1.0)
    axd.set_ylim(-4, 8)
    axd.set_ylabel(T("最終の地盤変位 (m)", "final ground displacement (m)"), fontsize=9, color="#b0624a")
    axd.tick_params(labelsize=8.5, colors="#b0624a")
    axd.spines["top"].set_visible(False)
    axc.set_zorder(axd.get_zorder() + 1)
    axc.patch.set_visible(False)
    axc.text(1.0, 27.0, T("湾の軸(y = 40 km)。陸と湾の中は描いていない", "along the bay axis (y = 40 km); land and the bay are not drawn"),
             fontsize=8, color=C_MUTED)
    axc.text(42, 4.0, T("棚: 浅いので遅い(海岸から 20 km に 11 分)", "shelf: shallow, so slow (11 min for 20 km)"), fontsize=8,
             color=C_INK, ha="center")
    axc.text(119.5, 28.6, T("深海 1000 m: 99 m/s(20 km に 3.4 分)", "deep sea 1000 m: 99 m/s (3.4 min for 20 km)"), fontsize=8,
             color=C_INK, ha="right")
    axc.legend(loc="upper left", bbox_to_anchor=(0.0, 0.9), fontsize=8.3, frameon=False)
    panel_title(axc, T("(c) 長波の速さ $\\sqrt{gh}$ で海岸まで進む時間と、波の源(最終の地盤変位。右軸)",
                       "(c) Travel time to the coast at the long-wave speed $\\sqrt{gh}$, and the wave sources (final ground displacement, right axis)"))

    fig.suptitle(T("沿岸の地盤変動と沖の断層の津波の仕組み(入力と式から描いた図で、計算結果ではない)",
                   "How coastal ground motion and the offshore tsunami work (drawn from the inputs and formulas; not computed results)"),
                 fontsize=12.5, y=0.99)
    out = os.path.join(FIGDIR, "mechanism.png")
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print("saved", out)


if __name__ == "__main__":
    fig_setup()
    fig_deformation()
    fig_mechanism()
