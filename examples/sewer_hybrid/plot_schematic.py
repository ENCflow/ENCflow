#!/usr/bin/env python3
"""sewer_hybrid の説明図(計算結果を使わない。gen_data.py が書く data_sewer/ の入力と式だけ)。

  figs/setup.png      構成: 平面(枝管網・枡・幹線・川・吐口)と幹線の行の縦断(地表・管・川)
  figs/mechanism.png  仕組み: 1 つのセルの管路を水槽で見た図(幅 = 貯留係数。疑似スロットと幻の貯留)、
                      地表とのやり取りの強さ(枡の堰式・オリフィス式)、幹線と吐口の流せる量
引数 en で英語ラベル版を en/figs/ に描く(形・値・描画処理は共通で、ラベルだけが切り替わる)。
data_sewer/ がなければ先に gen_data.py を実行する。
"""
import os
import subprocess
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon
from matplotlib.lines import Line2D

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


here = os.path.dirname(os.path.abspath(__file__))
os.chdir(here)
FIGDIR = "en/figs" if EN else "figs"
os.makedirs(FIGDIR, exist_ok=True)
plt.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAPGothic", "IPAGothic", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
if not os.path.isfile("data_sewer/cap_T.txt"):
    subprocess.run([sys.executable, "gen_data.py"], check=True)

C_INK, C_MUTED, C_GRID = "#1f1f1f", "#8a8983", "#e3ddd0"
C_BLUE, C_ORANGE, C_AQUA, C_RED, C_PURPLE = "#2a78d6", "#eb6834", "#1baf7a", "#c8102e", "#7b4fb3"
C_SOIL, C_WATER, C_RIVER, C_PIPE = "#ece3d1", "#9cc3ec", "#cfe3f3", "#4a4a4a"
C_SLOT = "#f6c9ae"

NX, NY, DX = 40, 21, 10.0
JT, I1, I2, IR = 11, 2, 38, 39          # 幹線の行、幹線の列の範囲、川の最初の列(1 始まり)
G = 9.8
D_B, D_T, DEP_B, DEP_T, N_MAN = 0.4, 1.0, 2.0, 5.0, 0.013
INLET, CW, CO, CA_OUT = 0.01, 2.66, 0.15, 0.6 * np.pi / 4.0   # 枡の密度 (個/m2)、堰・オリフィス係数、吐口 Cd·A
RAIN = 60.0                              # mm/h
SLOPE, RIVER_LEVEL = 0.005, 1.5


def load(name):
    return np.loadtxt(os.path.join("data_sewer", name))


def pipe(D, length=10.0):
    a = np.pi * D * D / 4.0
    c = (1.0 / N_MAN) * a * (D / 4.0) ** (2.0 / 3.0)
    cap = a * length / (DX * DX)
    return c, cap


C_BR, CAP_BR = pipe(D_B)
C_TR, CAP_TRP = pipe(D_T)
CAP_TC = CAP_TRP + CAP_BR                # 幹線のセル = 幹線 + 枝管
SY_BR, SY_TC = CAP_BR / D_B, CAP_TC / D_T


def style(ax, grid=True):
    if grid:
        ax.grid(color="#eceae6", lw=0.6)
        ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(labelsize=8.5)


def panel_title(ax, s, x=0.0, y=1.02):
    ax.text(x, y, s, transform=ax.transAxes, fontsize=11, ha="left", va="bottom", color=C_INK)


# ============================== figs/setup.png ==============================
def fig_setup():
    z = load("z.txt")
    cap = load("cap_T.txt")
    inlet = load("inlet.txt")
    zr = load("z_R.txt")
    xc = (np.arange(NX) + 0.5) * DX
    yc = (np.arange(NY) + 0.5) * DX

    fig = plt.figure(figsize=(11.6, 9.0), facecolor="white")
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 0.78], width_ratios=[1.0, 0.36],
                          hspace=0.34, wspace=0.04)
    ax = fig.add_subplot(gs[0, 0])
    # 地表の標高(東へ下る一様斜面)と等高線
    ax.imshow(z, extent=[0, NX * DX, NY * DX, 0], cmap="Greys", vmin=5.0, vmax=12.0,
              interpolation="bilinear", alpha=0.35)
    for x0 in np.arange(0, NX * DX + 1, DX):
        ax.plot([x0, x0], [0, NY * DX], color=C_GRID, lw=0.5, zorder=1)
    for y0 in np.arange(0, NY * DX + 1, DX):
        ax.plot([0, NX * DX], [y0, y0], color=C_GRID, lw=0.5, zorder=1)
    for zz in (7.5, 7.0, 6.5):
        xx = (8.0 - zz) / SLOPE
        ax.plot([xx, xx], [0, NY * DX], color="#b5ad9c", lw=0.9, ls=(0, (4, 3)), zorder=2)
        ax.text(xx + 2, 6, "%.1f m" % zz, fontsize=7.5, color="#8d8676", va="top")
    # 枡(全セル 1 個。幹線の末端のセルは 10 個)
    jj, ii = np.nonzero(inlet > 0)
    small = inlet[jj, ii] < 0.05
    ax.scatter(xc[ii[small]], yc[jj[small]], s=2.5, color="#8f897c", zorder=3, lw=0)
    # 川(ラン E・F)
    ax.add_patch(Rectangle(((IR - 1) * DX, 0), 2 * DX, NY * DX, facecolor=C_RIVER, edgecolor=C_BLUE,
                           hatch="////", lw=0.8, zorder=4))
    # 幹線(行 11 の列 2〜38)
    yt = (JT - 0.5) * DX
    ax.plot([(I1 - 1) * DX, I2 * DX], [yt, yt], color=C_PIPE, lw=4.2, solid_capstyle="butt", zorder=5)
    ax.plot([(I1 - 1) * DX, I2 * DX], [yt, yt], color="white", lw=1.4, solid_capstyle="butt", zorder=6)
    xe = (I2 - 0.5) * DX
    ax.scatter([xe], [yt], s=46, marker="s", facecolor="white", edgecolor=C_INK, lw=1.0, zorder=7)
    ax.scatter([I2 * DX], [yt], s=60, marker=">", color=C_PURPLE, zorder=8)
    ax.plot([0, NX * DX, NX * DX, 0, 0], [0, 0, NY * DX, NY * DX, 0], color=C_INK, lw=1.6, zorder=9)
    ax.set_xlim(-2, NX * DX + 2)
    ax.set_ylim(NY * DX + 2, -2)
    ax.set_aspect("equal")
    ax.set_xlabel("x (m)", fontsize=9)
    ax.set_ylabel(T("北端からの距離 (m)", "distance from the north edge (m)"), fontsize=9)
    style(ax, grid=False)
    ax.text(1.0, 1.02, T("東へ下る一様斜面(勾配 0.005。等高線は 0.5 m ごと)→",
                         "uniform slope down to the east (gradient 0.005; contours every 0.5 m) →"),
            transform=ax.transAxes, fontsize=8.5, color=C_MUTED, ha="right", va="bottom")
    panel_title(ax, T("(a) 平面(上が北)", "(a) Plan (north up)"))

    # 凡例(右)
    axl = fig.add_subplot(gs[0, 1])
    axl.axis("off")
    items = [
        (Line2D([], [], color=C_PIPE, lw=4.2), T("幹線: 行 j = 11 の列 2〜38\nD 1.0 m、管底 = 地表 − 5 m",
                                                 "trunk main: row j = 11, columns 2–38\nD 1.0 m, invert = ground − 5 m")),
        (Line2D([], [], color=C_GRID, lw=6), T("枝管網: 全セル\nD 0.4 m、セルあたり 10 m(街路 1 本)、\n管底 = 地表 − 2 m",
                                               "branch network: every cell\nD 0.4 m, 10 m per cell (one street),\ninvert = ground − 2 m")),
        (Line2D([], [], color="#8f897c", marker="o", ms=2.5, lw=0), T("雨水枡: 各セル 1 個(0.01 個/m²)",
                                                                      "inlets: one per cell (0.01 per m²)")),
        (Line2D([], [], color="white", marker="s", ms=6.5, mec=C_INK, lw=0), T("幹線の末端のセル: 枡 10 個\n(A〜E で幹線の水の出口)",
                                                                             "trunk end cell: 10 inlets\n(the outlet of the trunk in A–E)")),
        (Line2D([], [], color=C_PURPLE, marker=">", ms=7, lw=0), T("開放吐口(ラン F のみ)\nCd·A = 0.47 m²、フラップ付き",
                                                                  "open outfall (run F only)\nCd·A = 0.47 m², with a flap")),
        (Rectangle((0, 0), 1, 1, facecolor=C_RIVER, edgecolor=C_BLUE, hatch="////"),
         T("川(ラン E・F のみ): 東端 2 列\n地盤 0 m、水位 1.5 m に固定",
           "river (runs E, F only): 2 east columns\nbed 0 m, level fixed at 1.5 m")),
        (Line2D([], [], color=C_INK, lw=1.6), T("四周は壁(水は出入りしない)", "walls on all sides (no flow through)")),
    ]
    axl.legend([h for h, _ in items], [s for _, s in items], loc="upper left", frameon=False, fontsize=8.5,
               handlelength=2.2, labelspacing=1.05, borderaxespad=0.0)

    # ---- (b) 幹線の行の縦断 ----
    axs = fig.add_subplot(gs[1, :])
    xg = np.linspace(0, NX * DX, 401)
    zg = 8.0 - SLOPE * xg
    xr0 = (IR - 1) * DX
    land = xg <= xr0
    axs.fill_between(xg[land], zg[land], -0.3, color=C_SOIL, lw=0, zorder=1)
    axs.plot(xg[land], zg[land], color=C_INK, lw=1.2, zorder=6)
    axs.plot(xg[~land], zg[~land], color=C_INK, lw=1.0, ls=(0, (3, 2)), zorder=6)
    # 枝管(他の行の位置。D 0.4 m)
    axs.fill_between(xg[land], (zg - DEP_B)[land], (zg - DEP_B + D_B)[land], color="white", lw=0, zorder=2)
    axs.plot(xg[land], (zg - DEP_B)[land], color="#8f897c", lw=0.9, zorder=3)
    axs.plot(xg[land], (zg - DEP_B + D_B)[land], color="#8f897c", lw=0.9, zorder=3)
    # 幹線(行 11、列 2〜38)
    xt = np.linspace((I1 - 1) * DX, I2 * DX, 200)
    zt = 8.0 - SLOPE * xt
    axs.fill_between(xt, zt - DEP_T, zt - DEP_T + D_T, color="white", lw=0, zorder=2)
    axs.plot(xt, zt - DEP_T, color=C_PIPE, lw=1.6, zorder=4)
    axs.plot(xt, zt - DEP_T + D_T, color=C_PIPE, lw=1.6, zorder=4)
    for xx in ((I1 - 1) * DX, I2 * DX):
        z0 = 8.0 - SLOPE * xx
        axs.plot([xx, xx], [z0 - DEP_T, z0 - DEP_T + D_T], color=C_PIPE, lw=1.6, zorder=4)
    # 川(E・F): 列 39・40 の地盤 0 m と水位 1.5 m
    axs.add_patch(Rectangle((xr0, -0.3), 2 * DX, 0.3, facecolor=C_SOIL, lw=0, zorder=7))
    axs.add_patch(Rectangle((xr0, 0.0), 2 * DX, RIVER_LEVEL, facecolor=C_RIVER, edgecolor=C_BLUE,
                            hatch="////", lw=0.8, zorder=7))
    zcl = float(zr[JT - 1, IR - 2])
    axs.plot([xr0, xr0], [0.0, zcl], color=C_INK, lw=1.2, zorder=8)
    axs.text(xr0 + 10, zcl + 0.25, T("A〜D の地表", "ground in A–D"), fontsize=7.5, color=C_MUTED, ha="center")
    # 吐口(F): 幹線の末端(管底 1.125 m)
    zinv = (8.0 - SLOPE * (I2 - 0.5) * DX) - DEP_T
    axs.plot([xr0 + 0.6, xr0 + 2.4], [zinv + D_T, zinv + 0.05], color=C_PURPLE, lw=2.2, zorder=9)
    axs.set_xlim(0, NX * DX)
    axs.set_ylim(-0.3, 8.6)
    axs.set_xlabel("x (m)", fontsize=9)
    axs.set_ylabel(T("標高 (m)", "elevation (m)"), fontsize=9)
    style(axs, grid=False)
    axs.text(30, 8.12, T("地表", "ground"), fontsize=8.5, color=C_INK)
    axs.text(30, 8.0 - SLOPE * 30 - DEP_B + D_B + 0.18, T("枝管(全セル。この行では幹線と同じセルに入る)",
                                                         "branch pipes (every cell; in this row they share the cells with the trunk)"),
             fontsize=8.0, color="#6d675b")
    axs.text(30, 8.0 - SLOPE * 30 - DEP_T + D_T + 0.18, T("幹線(列 2〜38)", "trunk main (columns 2–38)"),
             fontsize=8.5, color=C_PIPE)
    axs.annotate(T("幹線の末端の管底 1.125 m", "invert at the trunk end 1.125 m"), xy=(I2 * DX - 1, zinv),
                 xytext=(352, 0.45), fontsize=8.0, color=C_PIPE, ha="right",
                 arrowprops=dict(arrowstyle="-", color=C_MUTED, lw=0.8))
    axs.text(xr0 + 11, RIVER_LEVEL + 0.12, T("川", "river"), fontsize=7.5, color=C_BLUE, ha="center", va="bottom")
    axs.annotate(T("吐口(F)", "outfall (F)"), xy=(xr0 + 1.6, zinv + 0.8), xytext=(360, 2.75), fontsize=7.5,
                 color=C_PURPLE, ha="center", arrowprops=dict(arrowstyle="-", color=C_PURPLE, lw=0.7))
    axs.text(399, 8.45, T("標高は基準面 +8 m(管底を正の値にするため)。縦は横の約 20 倍に拡大",
                          "elevations use a datum raised by 8 m (to keep inverts positive); vertical scale ≈ 20× horizontal"),
             fontsize=8.0, color=C_MUTED, ha="right", va="top")
    panel_title(axs, T("(b) 幹線の行(j = 11)の縦断", "(b) Long profile along the trunk row (j = 11)"))

    fig.suptitle(T("sewer_hybrid の構成(入力ファイルから描いた図で、計算結果ではない)",
                   "Setup of sewer_hybrid (drawn from the input files; not computed results)"), fontsize=13, y=0.985)
    out = os.path.join(FIGDIR, "setup.png")
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print("saved", out)
    _ = cap


# ============================== figs/mechanism.png ==============================
def tank(ax, x0, s_pipe, cap, depth, s_slot, d_real, k, color_pipe=C_WATER, label=None):
    """幅 = 貯留係数 × k の水槽。管の部分(高さ cap/s_pipe)とスロット(地表まで)に地表まで水を満たす"""
    hc = cap / s_pipe
    wp, ws = s_pipe * k, max(s_slot * k, 0.012)
    top = depth
    ax.add_patch(Rectangle((x0, 0), wp, min(hc, top), facecolor=color_pipe, edgecolor=C_PIPE, lw=1.0, zorder=3))
    if hc < top:
        ax.add_patch(Rectangle((x0 + (wp - ws) / 2, hc), ws, top - hc, facecolor=C_SLOT, edgecolor=C_ORANGE,
                               hatch="////", lw=0.9, zorder=3))
    ax.plot([x0 - 0.06, x0 + wp + 0.06], [d_real, d_real], color=C_INK, lw=0.9, ls=(0, (3, 2)), zorder=4)
    s_ground = cap + s_slot * max(top - hc, 0.0)
    return s_ground, hc


def fig_mechanism():
    fig = plt.figure(figsize=(12.4, 9.6), facecolor="white")
    gs = fig.add_gridspec(2, 3, height_ratios=[1.05, 0.82], hspace=0.26, wspace=0.34, top=0.93)

    # ---- (a) 水槽 ----
    ax = fig.add_subplot(gs[0, :])
    ax.set_xlim(0, 12.4)
    ax.set_ylim(-2.3, 6.1)
    ax.axis("off")
    k = 10.0
    runs = [(T("A: 一様 sy = 0.031\n(枝管の値)\nslot = 0.03", "A: uniform\nsy = 0.031 (branch)\nslot = 0.03"), SY_BR, 0.03, C_BLUE),
            (T("B: 一様 sy = 0.091\n(幹線の値)\nslot = 0.03", "B: uniform\nsy = 0.091 (trunk)\nslot = 0.03"), SY_TC, 0.03, C_ORANGE),
            (T("D・E・F: セル別 sy\nslot = sy/5", "D, E, F: per-cell sy\nslot = sy/5"), None, 0.2, C_RED),
            (T("既定: セル別 sy\nslot = sy/50", "default: per-cell sy\nslot = sy/50"), None, 0.02, C_MUTED)]
    groups = [(T("枝管のセル(D 0.4 m、管底は地表 − 2 m。cap = 12.6 mm)",
                 "branch cell (D 0.4 m, invert 2 m below ground; cap = 12.6 mm)"), CAP_BR, SY_BR, DEP_B, D_B, 0.25, 2.55),
              (T("幹線のセル(D 1.0 m + 枝管、管底は地表 − 5 m。cap = 91.1 mm)",
                 "trunk cell (D 1.0 m + branch, invert 5 m below ground; cap = 91.1 mm)"), CAP_TC, SY_TC, DEP_T, D_T, 6.45, 5.95)]
    for gtitle, cap, sy_ok, depth, d_real, gx, ty in groups:
        ax.text(gx, ty, gtitle, fontsize=9.5, color=C_INK, ha="left", va="top")
        ax.plot([gx, gx + 5.45], [0, 0], color=C_INK, lw=0.8)
        ax.plot([gx, gx + 5.45], [depth, depth], color="#7a6a4c", lw=1.1)
        ax.text(gx + 5.47, depth, T("地表", "ground"), fontsize=8, color="#7a6a4c", va="center")
        ax.text(gx + 5.47, 0, T("管底", "invert"), fontsize=8, color=C_INK, va="center")
        ax.text(gx + 5.47, d_real, T("管頂", "crown"), fontsize=8, color=C_INK, va="center")
        for n, (rlabel, s_pipe, slot, col) in enumerate(runs):
            x0 = gx + 0.12 + 1.36 * n
            sp = sy_ok if s_pipe is None else s_pipe
            ss = slot if n < 2 else slot * sy_ok
            sg, hc = tank(ax, x0, sp, cap, depth, ss, d_real, k)
            ax.text(x0, -0.12, rlabel, fontsize=7.4, color=col, ha="left", va="top", linespacing=1.15)
            note = T("地表まで %.0f mm\n(cap の %.1f 倍)" % (sg * 1000, sg / cap),
                     "%.0f mm to ground\n(%.1f × cap)" % (sg * 1000, sg / cap))
            ax.text(x0, -1.12, note, fontsize=7.4, color=C_INK, ha="left", va="top", linespacing=1.15)
            if abs(hc - d_real) > 0.05:
                rise = (T("水頭が %.1f 倍速く上がる" % (hc / d_real), "head rises %.1f× faster" % (hc / d_real)) if hc > d_real
                        else T("水頭が %.1f 倍遅く上がる" % (d_real / hc), "head rises %.1f× slower" % (d_real / hc)))
                ax.text(x0, -1.83, rise, fontsize=7.4, color=col, ha="left", va="top")
    lx = 0.25
    ax.text(lx, 5.95, T("水槽の幅 = 貯留係数(水頭 1 m あたりに入る水)", "tank width = storage coefficient (water per 1 m of head)"),
            fontsize=8.3, va="top")
    ax.text(lx, 5.55, T("水槽の高さ = 水頭(管底からの高さ)、面積 = 貯まる水の量", "tank height = head (above the invert); area = stored water"),
            fontsize=8.3, va="top")
    ax.add_patch(Rectangle((lx, 4.82), 0.28, 0.2, facecolor=C_WATER, edgecolor=C_PIPE, lw=0.8))
    ax.text(lx + 0.38, 4.92, T("管の体積の分(cap まで。実在する水)", "pipe volume (up to cap; real water)"), fontsize=8.0, va="center")
    ax.add_patch(Rectangle((lx, 4.40), 0.28, 0.2, facecolor=C_SLOT, edgecolor=C_ORANGE, hatch="////", lw=0.8))
    ax.text(lx + 0.38, 4.50, T("疑似スロットの分(満管の後。実在しない「幻の貯留」)", "pseudo slot (after pipe-full; phantom storage that does not exist)"),
            fontsize=8.0, va="center")
    ax.plot([lx, lx + 0.28], [4.08, 4.08], color=C_INK, lw=0.9, ls=(0, (3, 2)))
    ax.text(lx + 0.38, 4.08, T("実際の管頂", "actual pipe crown"), fontsize=8.0, va="center")
    ax.text(lx, 3.68, T("水頭が地表を超えると、枡から地表へ噴出する。それまでに\n管に入る水 = 水槽を地表まで満たした面積",
                        "Once the head exceeds the ground, water erupts from the inlets.\nThe water the pipes take before that = the tank filled to the ground"),
            fontsize=8.3, color=C_INK, va="top", linespacing=1.3)
    panel_title(ax, T("(a) 1 つのセルの管路を水槽で見る(幅と高さは実際の比。管の部分は幅 sy・高さ cap/sy、その上の細い溝が疑似スロット)",
                      "(a) The conduit of one cell seen as a tank (true proportions: the pipe part is sy wide and cap/sy tall; the narrow slot above is the pseudo slot)"),
                y=1.0)

    # ---- (b) 地表とのやり取りの強さ ----
    axb = fig.add_subplot(gs[1, 0])
    hh = np.linspace(0.05, 50, 500)                     # mm
    weir = INLET * CW * (hh / 1000.0) ** 1.5 * 3.6e6     # mm/h(セルあたり枡 1 個)
    orif = INLET * CO * np.sqrt(2 * G * hh / 1000.0) * 3.6e6
    axb.plot(hh, weir, color=C_BLUE, lw=2.0)
    axb.plot(hh, orif, color=C_ORANGE, lw=2.0)
    axb.text(27, 290, T("管が満杯でないときの流入\n堰式 $N c_w h^{1.5}$", "inflow, pipe not full\nweir $N c_w h^{1.5}$"),
             fontsize=8, color=C_BLUE, va="top")
    axb.text(2, 5e4, T("満管の流入・被圧の噴出: オリフィス式 $N c_o \\sqrt{2g\\Delta H}$",
                         "inflow when full, eruption: orifice $N c_o \\sqrt{2g\\Delta H}$"),
             fontsize=8, color=C_ORANGE, va="center")
    axb.axhline(RAIN, color=C_MUTED, lw=1.0, ls="--")
    hreq = (RAIN / 3.6e6 / (INLET * CW)) ** (2.0 / 3.0) * 1000.0
    axb.plot([hreq], [RAIN], "o", color=C_BLUE, ms=5, zorder=5)
    axb.annotate(T("雨 60 mm/h を飲み込む水深 %.1f mm" % hreq, "depth to take in 60 mm/h of rain: %.1f mm" % hreq),
                 xy=(hreq, RAIN), xytext=(12, 14), fontsize=8, color=C_BLUE,
                 arrowprops=dict(arrowstyle="-", color=C_BLUE, lw=0.7))
    o10 = INLET * CO * np.sqrt(2 * G * 0.01) * 3.6e6
    axb.plot([10], [o10], "o", color=C_ORANGE, ms=5, zorder=5)
    axb.annotate(T("水頭差 1 cm で %s mm/h\n(雨の %d 倍)" % (format(int(round(o10, -1)), ","), int(round(o10 / RAIN))),
                   "%s mm/h at 1 cm of head difference\n(%d× the rain)" % (format(int(round(o10, -1)), ","), int(round(o10 / RAIN)))),
                 xy=(10, o10), xytext=(16, 1.2e4), fontsize=8, color=C_ORANGE,
                 arrowprops=dict(arrowstyle="-", color=C_ORANGE, lw=0.7))
    axb.text(49, RAIN * 0.9, T("雨 60 mm/h", "rain 60 mm/h"), fontsize=8, color=C_MUTED, ha="right", va="top")
    axb.set_yscale("log")
    axb.set_xlim(0, 50)
    axb.set_ylim(1, 1e5)
    axb.text(49, 1.3, T("枡はセルに 1 個(N = 0.01 個/m²)\n$c_w$ = 2.66、$c_o$ = 0.15 m²",
                        "1 inlet per cell (N = 0.01 per m²)\n$c_w$ = 2.66, $c_o$ = 0.15 m²"),
             fontsize=7.5, color=C_MUTED, ha="right", va="bottom")
    axb.set_xlabel(T("地表の水深 h、または水頭差 ΔH (mm)", "surface depth h or head difference ΔH (mm)"), fontsize=9)
    axb.set_ylabel(T("セルあたりの交換の強さ (mm/h)", "exchange per cell (mm/h)"), fontsize=9)
    style(axb)
    panel_title(axb, T("(b) 地表とのやり取り(枡 1 個/セル)", "(b) Exchange with the surface"))

    # ---- (c) 幹線が流せる量 ----
    axc = fig.add_subplot(gs[1, 1])
    S = np.linspace(0, 0.01, 200)
    axc.plot(S, C_TR * np.sqrt(S), color=C_PIPE, lw=2.0, label=T("満管の幹線 $Q = C\\sqrt{S}$", "full trunk $Q = C\\sqrt{S}$"))
    axc.plot(S, 0.5 * C_TR * np.sqrt(S), color=C_PIPE, lw=1.2, ls="--", label=T("充満率 0.5(Q は充満率に比例)",
                                                                                 "filling 0.5 (Q ∝ filling)"))
    q_rain = RAIN / 3.6e6 * NX * NY * DX * DX
    axc.axhline(q_rain, color=C_BLUE, lw=1.0, ls="--")
    axc.text(0.0099, q_rain + 0.05, T("領域の雨 60 mm/h\n= %.2f m³/s" % q_rain, "domain rain 60 mm/h\n= %.2f m³/s" % q_rain),
             fontsize=8, color=C_BLUE, va="bottom", ha="right")
    axc.axvline(SLOPE, color=C_MUTED, lw=0.9, ls=":")
    qs = C_TR * np.sqrt(SLOPE)
    axc.plot([SLOPE], [qs], "o", color=C_PIPE, ms=5, zorder=5)
    axc.annotate(T("地表の勾配 0.005 で %.2f m³/s" % qs, "%.2f m³/s at the ground slope 0.005" % qs), xy=(SLOPE, qs),
                 xytext=(0.0004, 2.3), fontsize=8, color=C_PIPE, arrowprops=dict(arrowstyle="-", color=C_MUTED, lw=0.7))
    axc.set_xlim(0, 0.01)
    axc.set_ylim(0, 2.6)
    axc.set_xlabel(T("動水勾配 S", "hydraulic gradient S"), fontsize=9)
    axc.set_ylabel(T("流量 (m³/s)", "discharge (m³/s)"), fontsize=9)
    axc.legend(loc="lower right", frameon=False, fontsize=7.6)
    style(axc)
    panel_title(axc, T("(c) 幹線が流せる量(C = %.1f m³/s)" % C_TR, "(c) Trunk capacity (C = %.1f m³/s)" % C_TR))

    # ---- (d) 吐口が流せる量 ----
    axd = fig.add_subplot(gs[1, 2])
    dH = np.linspace(0, 1.0, 200)
    axd.plot(dH, CA_OUT * np.sqrt(2 * G * dH), color=C_PURPLE, lw=2.0)
    axd.axhline(q_rain, color=C_BLUE, lw=1.0, ls="--")
    dreq = (q_rain / CA_OUT) ** 2 / (2 * G)
    axd.plot([dreq], [q_rain], "o", color=C_PURPLE, ms=5, zorder=5)
    hout = RIVER_LEVEL + dreq
    zinv = (8.0 - SLOPE * (I2 - 0.5) * DX) - DEP_T
    axd.annotate(T("%.2f m³/s を吐くには\n川の水位より %.2f m 高い水頭\n(= %.2f m。管頂 %.3f m の下)" % (q_rain, dreq, hout, zinv + D_T),
                   "to discharge %.2f m³/s the head must be\n%.2f m above the river level\n(= %.2f m, below the crown %.3f m)" % (q_rain, dreq, hout, zinv + D_T)),
                 xy=(dreq, q_rain), xytext=(0.36, 0.25), fontsize=8, color=C_PURPLE,
                 arrowprops=dict(arrowstyle="-", color=C_PURPLE, lw=0.7))
    axd.set_xlim(0, 1.0)
    axd.set_ylim(0, 2.6)
    axd.set_xlabel(T("管路の水頭 − 川の水位 ΔH (m)", "conduit head − river level ΔH (m)"), fontsize=9)
    axd.set_ylabel(T("流量 (m³/s)", "discharge (m³/s)"), fontsize=9)
    style(axd)
    panel_title(axd, T("(d) 吐口(F)が流せる量 $C_d A\\sqrt{2g\\Delta H}$", "(d) Outfall (F): $C_d A\\sqrt{2g\\Delta H}$"))

    fig.suptitle(T("管路連続体層の仕組み(式と入力の値から描いた図で、計算結果ではない)",
                   "How the conduit continuum layer works (drawn from the formulas and input values; not computed results)"),
                 fontsize=13, y=0.995)
    out = os.path.join(FIGDIR, "mechanism.png")
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print("saved", out)


if __name__ == "__main__":
    fig_setup()
    fig_mechanism()
