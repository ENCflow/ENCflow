#!/usr/bin/env python3
"""tsunami_fault の説明図(計算結果を使わない。make が作る入力 z.txt・bm/ と式だけ)。

  figs/setup.png        構成: 平面(地形・断層面の投影・プローブ・境界)と中央の行の縦断(地形と断層面)
  figs/deformation.png  地盤変位: 最終変位の地図と、中央の行に沿う変位
  figs/mechanism.png    仕組み: 立ち上がりの時刻歴と波が隆起を横切る時間、1 層非静水圧の分散、
                        長波の速さ √(gh) で各プローブまで進む時間
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
for f in ("z.txt", "bm/bmlist.txt"):
    if not os.path.isfile(f):
        sys.exit("%s がありません。先に make を実行してください / %s is missing; run make first" % (f, f))

C_INK, C_MUTED = "#1f1f1f", "#8a8983"
C_F, C_SEA, C_LAND, C_WATER = "#eb6834", "#2a78d6", "#d9c7a0", "#cfe3f3"
C_NH, C_EX = "#2a78d6", "#1f1f1f"
DX = 1.0                                                 # km
NX, NY = 200, 150
G, H = 9.8, 2000.0
x = (np.arange(NX) + 0.5) * DX
y = (NY - np.arange(NY) - 0.5) * DX                      # km(北が先頭行)
z0 = np.loadtxt("z.txt")
J = 74                                                   # 中央の行(0 始まり。y = 75.5 km、プローブ 1〜4 の行)
# 断層(fault2disp.txt。上端の中心 (120, 75) km、走向 0°(北)で東へ傾斜)
FT = dict(xt=120.0, yt=75.0, dt=5.0, dip=15.0, L=60.0, W=30.0, slip=5.0, trise=30.0)
XB = FT["xt"] + FT["W"] * np.cos(np.radians(FT["dip"]))
DB = FT["dt"] + FT["W"] * np.sin(np.radians(FT["dip"]))
PIJ = {1: (121, 75), 2: (61, 75), 3: (11, 75), 4: (181, 75), 5: (121, 120)}
PXY = {n: ((i - 0.5) * DX, (NY - j + 0.5) * DX) for n, (i, j) in PIJ.items()}
PNAME = {1: T("上端の真上", "above the upper edge"), 2: T("斜面の下端", "foot of the slope"), 3: T("沿岸(水深 268 m)", "coast (depth 268 m)"),
         4: T("東", "east"), 5: T("南(断層の端の外)", "south (beyond the fault end)")}


def style(ax, grid=True):
    if grid:
        ax.grid(color="#eceae6", lw=0.6)
        ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(labelsize=8.5)


def panel_title(ax, s, y=1.02):
    ax.text(0.0, y, s, transform=ax.transAxes, fontsize=11, ha="left", va="bottom", color=C_INK)


def probes(ax, ms=5):
    for n, (px, py) in PXY.items():
        ax.plot(px, py, "o", ms=ms, mfc="white", mec=C_INK, mew=1.0, zorder=7)
        ax.text(px + 2.0, py + 3.0, str(n), fontsize=9, color=C_INK, zorder=8,
                bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.85))


# ============================== figs/setup.png ==============================
def fig_setup():
    fig = plt.figure(figsize=(12.6, 10.6), facecolor="white")
    gs0 = fig.add_gridspec(2, 1, height_ratios=[1.0, 0.62], hspace=0.2, top=0.93)
    gs = gs0[0].subgridspec(1, 2, width_ratios=[1.0, 0.34], wspace=0.03)
    gsb = gs0[1].subgridspec(2, 1, height_ratios=[0.34, 0.40], hspace=0.10)
    ax = fig.add_subplot(gs[0, 0])
    sea = np.ma.masked_where(z0 >= 0, -z0)
    land = np.ma.masked_where(z0 < 0, z0)
    ext = [0, NX * DX, 0, NY * DX]
    ax.imshow(sea, extent=ext, origin="upper", cmap="Blues", norm=LogNorm(20, 4000), interpolation="nearest")
    ax.imshow(land, extent=ext, origin="upper", cmap=LinearSegmentedColormap.from_list("l", ["#efe6cf", "#cdb98c"]),
              norm=Normalize(0, 100), interpolation="nearest")
    ax.contour(x, y, z0, levels=[0], colors=C_INK, linewidths=0.9)
    cs = ax.contour(x, y, z0, levels=[-1500, -1000, -500], colors="#4a6b8a", linewidths=0.6, linestyles="--")
    for tl in ax.clabel(cs, fmt=lambda v: "%d m" % -v, fontsize=7.5, inline=True):
        tl.set_color("#1f3550")
        tl.set_bbox(dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.75))
    y1, y2 = FT["yt"] - FT["L"] / 2, FT["yt"] + FT["L"] / 2
    ax.add_patch(Rectangle((FT["xt"], y1), XB - FT["xt"], y2 - y1, facecolor=C_F, alpha=0.22, edgecolor="none", zorder=3))
    ax.add_patch(Rectangle((FT["xt"], y1), XB - FT["xt"], y2 - y1, facecolor="none", edgecolor=C_F, lw=0.9, ls="--", zorder=4))
    ax.plot([FT["xt"]] * 2, [y1, y2], color=C_F, lw=2.0, zorder=5)
    for yy in np.linspace(y1 + 5, y2 - 5, 6):
        ax.add_patch(Polygon([[FT["xt"], yy - 1.6], [FT["xt"], yy + 1.6], [FT["xt"] + 2.6, yy]], closed=True,
                             facecolor=C_F, edgecolor="none", zorder=5))
    probes(ax)
    ax.text(31, 8, T("斜面(海岸 x ≈ 2.9 km\n→ 水深 2000 m)", "slope (coast at x ≈ 2.9 km\n→ 2000 m deep)"), fontsize=8.5,
            color=C_INK, ha="center")
    ax.text(170, 140, T("平坦な海 2000 m", "flat sea 2000 m"), fontsize=8.5, color="white", ha="center")
    ax.text(203, 75, T("長波放射", "radiation"), fontsize=8.5, color=C_MUTED, ha="left", va="center", rotation=90)
    ax.text(100, 152, T("長波放射", "radiation"), fontsize=8.5, color=C_MUTED, ha="center", va="bottom")
    ax.set_xlim(0, NX * DX)
    ax.set_ylim(0, NY * DX)
    ax.set_aspect("equal")
    ax.set_xlabel("x (km)", fontsize=9)
    ax.set_ylabel("y (km)", fontsize=9)
    style(ax, grid=False)
    panel_title(ax, T("(a) 平面(上が北)", "(a) Plan (north up)"), y=1.05)

    axn = fig.add_subplot(gs[0, 1])
    axn.axis("off")
    axn.add_patch(Rectangle((0.0, 0.94), 0.07, 0.035, transform=axn.transAxes, facecolor=C_F, alpha=0.35, edgecolor=C_F))
    axn.text(0.10, 0.975, T("逆断層(すべり角 90°)\n上端の中心 (120, 75) km・深さ 5 km\n走向 北、傾斜 15°(東へ下がる)\n長さ 60 km、幅 30 km、すべり 5 m\nt = 0 から 30 s の半正弦の立ち上がり",
                            "reverse fault (rake 90°)\nupper-edge centre (120, 75) km, depth 5 km\nstrike north, dip 15° (down to the east)\nlength 60 km, width 30 km, slip 5 m\nhalf-sine rise over 30 s from t = 0"),
             transform=axn.transAxes, fontsize=8.3, va="top", linespacing=1.32)
    notes = T("矩形 = 断層面を地表へ投影した範囲\n太線 = 上端(三角は傾斜の向き)\n\n○ = プローブ 1〜5\n" +
              "\n".join("%d %s" % (n, PNAME[n]) for n in PXY) +
              "\n\n格子 200 × 150、Δx = Δy = 1 km\n西は陸(壁)、東・北・南は長波放射\n海は「解く海」(静水面 0)",
              "rectangle = surface projection of the fault plane\nthick line = upper edge (triangles point down-dip)\n\n○ = probes 1–5\n" +
              "\n".join("%d %s" % (n, PNAME[n]) for n in PXY) +
              "\n\ngrid 200 × 150, Δx = Δy = 1 km\nwest: land (wall); east, north, south: radiation\nthe sea is solved (still water level 0)")
    axn.text(0.0, 0.66, notes, transform=axn.transAxes, fontsize=8.2, va="top", color=C_INK, linespacing=1.32)

    axp = fig.add_subplot(gsb[0])
    zr = z0[J]
    axp.fill_between(x, np.minimum(zr, 0), 0, color=C_WATER, lw=0)
    axp.fill_between(x, zr, -2300, color=C_LAND, lw=0, alpha=0.8)
    axp.plot(x, zr, color=C_INK, lw=1.0)
    axp.axhline(0, color=C_SEA, lw=0.8)
    for n in (1, 2, 3, 4):
        px = PXY[n][0]
        axp.plot([px], [0], "v", color=C_INK, ms=6, zorder=5)
        axp.text(px, 120, str(n), fontsize=8.5, ha="center", va="bottom")
    axp.set_ylim(-2300, 250)
    axp.set_xlim(0, NX * DX)
    axp.set_ylabel(T("標高 (m)", "elevation (m)"), fontsize=9)
    axp.tick_params(labelbottom=False)
    style(axp)
    axp.text(30, -1500, T("一様な斜面(0.035)", "uniform slope (0.035)"), fontsize=8.5, ha="center")
    axp.text(140, -1500, T("水深 2000 m の平坦な海", "flat sea 2000 m deep"), fontsize=8.5, ha="center")
    panel_title(axp, T("(b) 中央の行(y = 75.5 km)の縦断: 地形と断層面(▼ = プローブ 1〜4)",
                       "(b) Section along the central row (y = 75.5 km): terrain and fault plane (▼ = probes 1–4)"))

    axf = fig.add_subplot(gsb[1], sharex=axp)
    axf.fill_between([0, 200], 0, 16, color="#f3efe6", lw=0)
    axf.fill_between(x, np.maximum(-zr, 0) / 1000.0, 0, color=C_WATER, lw=0)
    axf.plot(x, np.maximum(-zr, 0) / 1000.0, color=C_SEA, lw=0.9)
    axf.plot([FT["xt"], XB], [FT["dt"], DB], color=C_F, lw=3.2, solid_capstyle="round")
    c, s = np.cos(np.radians(FT["dip"])), np.sin(np.radians(FT["dip"]))
    xm, dm = (FT["xt"] + XB) / 2, (FT["dt"] + DB) / 2
    ux, ud = -c, -s                                      # 上り傾斜(西・上)
    nx_, nd_ = s, -c                                     # 上盤側(東上)へのずらし
    for sgn, (a, b) in ((1, (-4.5, 4.5)), (-1, (4.5, -4.5))):
        off = 1.0 * sgn
        axf.add_patch(FancyArrowPatch((xm + a * ux + off * nx_, dm + a * ud + off * nd_), (xm + b * ux + off * nx_, dm + b * ud + off * nd_),
                                      arrowstyle="-|>", mutation_scale=10, color=C_F, lw=1.3))
    axf.text(152, 5.2, T("断層面: 5 m ずれる\n(上盤 = 東側が西へ乗り上げる)", "fault plane: slips 5 m\n(the hanging wall, east side,\nrides up to the west)"),
             fontsize=8.3, color=C_F, va="top")
    axf.text(FT["xt"] - 2, FT["dt"] - 0.4, T("上端 5 km", "upper edge 5 km"), fontsize=8, color=C_F, ha="right")
    axf.text(XB + 2, DB - 1.4, T("下端 12.8 km", "lower edge 12.8 km"), fontsize=8, color=C_F, ha="left")
    axf.set_ylim(16, -0.5)
    axf.set_xlim(0, NX * DX)
    axf.set_xlabel("x (km)", fontsize=9)
    axf.set_ylabel(T("深さ (km)", "depth (km)"), fontsize=9)
    style(axf, grid=False)
    fig.canvas.draw()
    bb = axf.get_window_extent()
    vex = (bb.height / 16.5) / (bb.width / 200.0)
    axf.text(199, 15.4, T("縦は横の約 %.1f 倍に拡大。水色 = 海(水深 2 km まで)" % vex, "vertical scale ≈ %.1f× horizontal; light blue = sea (down to 2 km)" % vex),
             fontsize=8, color=C_MUTED, ha="right", va="bottom")

    fig.suptitle(T("tsunami_fault の構成(入力ファイルから描いた図で、計算結果ではない)",
                   "Setup of tsunami_fault (drawn from the input files; not computed results)"), fontsize=13, y=0.985)
    out = os.path.join(FIGDIR, "setup.png")
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print("saved", out)


# ============================== figs/deformation.png ==============================
def fig_deformation():
    d = np.loadtxt("bm/disp_0010.txt")
    fig = plt.figure(figsize=(13.2, 5.4), facecolor="white")
    gs = fig.add_gridspec(2, 2, width_ratios=[1.2, 1.0], height_ratios=[1.0, 0.55], hspace=0.12, wspace=0.34)
    ax0 = fig.add_subplot(gs[:, 0])
    im = ax0.imshow(d, extent=[0, 200, 0, 150], origin="upper", cmap="RdBu_r", vmin=-2.2, vmax=2.2)
    y1, y2 = FT["yt"] - FT["L"] / 2, FT["yt"] + FT["L"] / 2
    ax0.plot([FT["xt"]] * 2, [y1, y2], "k-", lw=1.5, label=T("上端(深さ 5 km)", "upper edge (depth 5 km)"))
    ax0.plot([XB] * 2, [y1, y2], "k--", lw=1.0, label=T("下端(深さ 12.8 km)", "lower edge (depth 12.8 km)"))
    ax0.contour(x, y, z0, levels=[0], colors="#52514e", linewidths=0.8)
    for n, (px, py) in PXY.items():
        ax0.plot(px, py, "o", ms=4, mfc="white", mec=C_INK, mew=0.9)
    ax0.axhline(PXY[1][1], color=C_INK, lw=0.7, ls=":")
    ax0.set_xlabel("x (km)", fontsize=9)
    ax0.set_ylabel("y (km)", fontsize=9)
    ax0.tick_params(labelsize=8.5)
    ax0.legend(loc="lower left", fontsize=8, frameon=True)
    cb = plt.colorbar(im, ax=ax0, fraction=0.03, pad=0.02)
    cb.set_label(T("最終の地盤変位 (m)", "final ground displacement (m)"), fontsize=9)
    panel_title(ax0, T("(a) 最終の地盤変位(赤 = 隆起、青 = 沈降)。○ = プローブ、\n点線 = (b) の断面、灰色の線 = 海岸線",
                       "(a) Final ground displacement (red = uplift, blue = subsidence);\n○ = probes, dotted = section of (b), grey line = coastline"), y=1.01)

    ax1 = fig.add_subplot(gs[0, 1])
    ax1.axhline(0, color=C_MUTED, lw=0.7)
    ax1.fill_between(x, d[J], 0, where=d[J] > 0, color="#e8b4a4", alpha=0.6, lw=0, interpolate=True)
    ax1.fill_between(x, d[J], 0, where=d[J] < 0, color="#a9c8ea", alpha=0.6, lw=0, interpolate=True)
    ax1.plot(x, d[J], color=C_INK, lw=1.8)
    ax1.axvline(FT["xt"], color=C_F, lw=1.0)
    ax1.axvline(XB, color=C_F, lw=1.0, ls="--")
    imax, imin = int(np.argmax(d[J])), int(np.argmin(d[J]))
    ax1.annotate(T("最大の隆起 %.2f m(上端の真上)" % d[J, imax], "max uplift %.2f m\n(above the upper edge)" % d[J, imax]), xy=(x[imax], d[J, imax]),
                 xytext=(5, 1.2), fontsize=8, color=C_INK, arrowprops=dict(arrowstyle="-", color=C_MUTED, lw=0.7))
    ax1.annotate(T("最大の沈降 %.2f m(下端の先)" % d[J, imin], "max subsidence %.2f m (beyond the lower edge)" % d[J, imin]),
                 xy=(x[imin], d[J, imin]), xytext=(5, -0.85), fontsize=8, color=C_INK, va="center", arrowprops=dict(arrowstyle="-", color=C_MUTED, lw=0.7))
    ax1.text(FT["xt"] - 1, 2.25, T("上端", "upper edge"), fontsize=8, color=C_F, ha="right")
    ax1.text(XB + 1, 2.25, T("下端", "lower edge"), fontsize=8, color=C_F, ha="left")
    ax1.set_xlim(0, 200)
    ax1.set_ylim(-1.1, 2.5)
    ax1.set_ylabel(T("変位 (m)", "displacement (m)"), fontsize=9)
    ax1.tick_params(labelbottom=False)
    style(ax1)
    panel_title(ax1, T("(b) 中央の行 y = 75.5 km に沿う最終の地盤変位", "(b) Final ground displacement along the central row y = 75.5 km"))
    ax2 = fig.add_subplot(gs[1, 1], sharex=ax1)
    zr = z0[J]
    ax2.fill_between(x, np.minimum(zr, 0), 0, color=C_WATER, lw=0)
    ax2.fill_between(x, zr, -2300, color=C_LAND, lw=0, alpha=0.8)
    ax2.plot(x, zr, color=C_INK, lw=1.0)
    ax2.set_ylim(-2200, 200)
    ax2.set_xlabel("x (km)", fontsize=9)
    ax2.set_ylabel(T("標高 (m)", "elevation (m)"), fontsize=9)
    style(ax2)
    fig.suptitle(T("断層による地盤変位(fault2disp の出力 bm/ から描いた図で、計算結果ではない)",
                   "Ground displacement by the fault (drawn from the fault2disp output bm/; not computed results)"), fontsize=12.5, y=1.04)
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


def fig_mechanism():
    t, f = bm_series()
    dfin = f[-1]
    c0 = np.sqrt(G * H)
    fig = plt.figure(figsize=(12.8, 9.0), facecolor="white")
    gs = fig.add_gridspec(2, 2, width_ratios=[1.0, 1.0], height_ratios=[1.0, 0.95], hspace=0.42, wspace=0.22, top=0.92)

    # ---- (a) 立ち上がりと、波が隆起を横切る時間 ----
    ax = fig.add_subplot(gs[0, 0])
    imax = int(np.argmax(dfin[J]))
    vv = f[:, J, imax]
    ax.plot(np.concatenate([t, [240.0]]), np.concatenate([vv, [vv[-1]]]), color=C_F, lw=2.0, marker="o", ms=3,
            label=T("隆起の頂(30 s の半正弦。bm/ の 3 s 刻み 11 枚)", "uplift crest (half-sine over 30 s; 11 snapshots every 3 s in bm/)"))
    ax.plot([0, 0, 240], [0, vv[-1], vv[-1]], color=C_MUTED, lw=1.2, ls="--", label=T("瞬時変位(最終変位を t = 0 に)", "instantaneous (final at t = 0)"))
    tcross = FT["W"] * np.cos(np.radians(FT["dip"])) * 1000.0 / c0
    ax.annotate("", xy=(tcross, 0.65), xytext=(0, 0.65), arrowprops=dict(arrowstyle="<->", color=C_SEA, lw=1.3))
    ax.text(tcross / 2, 0.75, T("波(%.0f m/s)が断層の幅(水平に 29 km)を横切る時間 %.0f s" % (c0, tcross),
                                "time for the wave (%.0f m/s) to cross the fault width\n(29 km horizontally): %.0f s" % (c0, tcross)),
            fontsize=8.2, color=C_SEA, ha="center", va="bottom")
    ax.annotate("", xy=(FT["trise"], 0.3), xytext=(0, 0.3), arrowprops=dict(arrowstyle="<->", color=C_F, lw=1.3))
    ax.text(FT["trise"] + 4, 0.3, T("立ち上がり 30 s", "rise 30 s"), fontsize=8.2, color=C_F, va="center")
    ax.set_xlim(-5, 240)
    ax.set_ylim(0, 2.6)
    ax.set_xlabel(T("時刻 t (s)", "time t (s)"), fontsize=9)
    ax.set_ylabel(T("地盤の変位 (m)", "ground displacement (m)"), fontsize=9)
    ax.legend(loc="upper right", fontsize=7.8, frameon=False)
    style(ax)
    panel_title(ax, T("(a) 立ち上がりは、波が断層の幅を横切る時間より十分短い", "(a) The rise is much shorter than the wave's crossing of the fault"))

    # ---- (b) 1 層非静水圧の分散 ----
    axb = fig.add_subplot(gs[0, 1])
    lam = np.logspace(np.log10(5), np.log10(300), 400)          # km
    kh = 2 * np.pi * H / (lam * 1000.0)
    c_nh = 1 / np.sqrt(1 + kh ** 2 / 4)
    c_ex = np.sqrt(np.tanh(kh) / kh)
    axb.axvspan(15, 30, color="#f4f3ee", lw=0)
    axb.plot(lam, np.ones_like(lam), color=C_MUTED, lw=1.6, label=T("静水圧(浅水方程式): 分散なし", "hydrostatic (shallow water): no dispersion"))
    axb.plot(lam, c_nh, color=C_NH, lw=2.0, label=T("1 層非静水圧 $1/\\sqrt{1 + k^2H^2/4}$", "one-layer NH $1/\\sqrt{1 + k^2H^2/4}$"))
    axb.plot(lam, c_ex, color=C_EX, lw=1.2, ls=":", label=T("厳密(線形の水面波)$\\sqrt{\\tanh kH / kH}$", "exact (linear water waves) $\\sqrt{\\tanh kH / kH}$"))
    axb.text(21.2, 0.715, T("隆起・沈降の\n幅 15〜30 km\n(kH 0.4〜0.8):\n2〜8 % 遅い", "uplift and\nsubsidence\n15–30 km wide\n(kH 0.4–0.8):\n2–8 % slower"),
             fontsize=8, ha="center", va="bottom", color=C_INK)
    lam_c = 70.0
    axb.axvline(lam_c, color=C_F, lw=1.0, ls="--")
    axb.text(lam_c * 1.05, 0.79, T("変位の主な成分\n(中央の行のスペクトル\nの重心 ≈ 70 km、kH ≈ 0.18)", "main component of the\ndisplacement (centroid of\nthe spectrum ≈ 70 km, kH ≈ 0.18)"),
             fontsize=8, color=C_F, va="bottom")
    axb.set_xscale("log")
    axb.set_xlim(5, 300)
    axb.set_ylim(0.6, 1.04)
    axb.set_xlabel(T("波長 (km)。水深 2000 m", "wavelength (km), depth 2000 m"), fontsize=9)
    axb.set_ylabel(T("波の速さ / $\\sqrt{gH}$", "wave speed / $\\sqrt{gH}$"), fontsize=9)
    axb.legend(loc="lower right", fontsize=7.8, frameon=False)
    style(axb)
    panel_title(axb, T("(b) 非静水圧では短い成分ほど遅れ、波が分散する", "(b) With non-hydrostatic pressure, shorter components lag: dispersion"))

    # ---- (c) √(gh) で各プローブまで進む時間 ----
    axc = fig.add_subplot(gs[1, :])
    zr = z0[J]
    h = np.maximum(-zr, 0.5)
    dt_cell = DX * 1000.0 / np.sqrt(G * h)
    i0 = imax
    tt = np.full(NX, np.nan)
    for i in range(NX):
        a, b = sorted((i, i0))
        tt[i] = dt_cell[a:b + 1].sum() - 0.5 * (dt_cell[a] + dt_cell[b])
    wet = zr < 0
    axc.plot(np.where(wet, x, np.nan), np.where(wet, tt, np.nan), color=C_INK, lw=2.0,
             label=T("隆起の頂(x = %.1f km)から $\\sqrt{gh}$ で進む時間" % x[i0], "travel time from the uplift crest (x = %.1f km) at $\\sqrt{gh}$" % x[i0]))
    obs = {2: 432.0, 3: 960.0, 4: 414.0}                  # 瞬時変位のケースの最高の時刻 (s)(plot_results.py の数表)
    for n, to in obs.items():
        px = PXY[n][0]
        i = int(px / DX)
        axc.plot([px], [tt[i]], "o", color=C_F, ms=7, zorder=5)
        axc.plot([px], [to], "x", color=C_SEA, ms=8, mew=2, zorder=6)
        axc.annotate(T("%d %s: %.0f s(計算の最高 %.0f s)" % (n, PNAME[n], tt[i], to), "%d %s: %.0f s (max in the run: %.0f s)" % (n, PNAME[n], tt[i], to)),
                     xy=(px, tt[i]), xytext=(px + (8 if n == 2 else (-62 if n == 4 else 20)), tt[i] + {2: 90, 3: -150, 4: 230}[n]), fontsize=8.3, color=C_INK,
                     arrowprops=dict(arrowstyle="-", color=C_MUTED, lw=0.7))
    axc.plot([], [], "o", color=C_F, ms=7, label=T("プローブまでの時間(式)", "time to the probe (formula)"))
    axc.plot([], [], "x", color=C_SEA, ms=8, mew=2, label=T("瞬時変位のケースで水位が最高になる時刻", "time of the maximum level in the instantaneous case"))
    axc.set_xlim(0, 200)
    axc.set_ylim(0, 1100)
    axc.set_xlabel("x (km)", fontsize=9)
    axc.set_ylabel(T("時間 (s)", "time (s)"), fontsize=9)
    axc.legend(loc="upper center", fontsize=8.3, frameon=False)
    style(axc)
    axc.text(30, 120, T("斜面では浅くなるほど遅い\n(水深 268 m で 51 m/s)", "slower as the slope shoals\n(51 m/s at 268 m depth)"), fontsize=8.2, color=C_INK, ha="center")
    axc.text(165, 120, T("水深 2000 m: %.0f m/s" % c0, "depth 2000 m: %.0f m/s" % c0), fontsize=8.2, color=C_INK, ha="center")
    panel_title(axc, T("(c) 中央の行に沿って、長波の速さ $\\sqrt{gh}$ で進む時間(式)と、計算で水位が最高になる時刻",
                       "(c) Travel time along the central row at the long-wave speed $\\sqrt{gh}$ (formula), and the time of the maximum level in the run"))

    fig.suptitle(T("断層による津波の仕組み(入力と式から描いた図で、計算結果ではない。(c) の × だけは計算の値)",
                   "How the fault tsunami works (drawn from the inputs and formulas; not computed results, except the × in (c))"),
                 fontsize=12.5, y=0.99)
    out = os.path.join(FIGDIR, "mechanism.png")
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print("saved", out)


if __name__ == "__main__":
    fig_setup()
    fig_deformation()
    fig_mechanism()
