#!/usr/bin/env python3
"""examples/mountain_valley の機構の模式図と設定の図(計算結果は使わない)。

  python3 plot_setup.py        # figs/mechanism.png, figs/setup.png
  python3 plot_setup.py en     # 英語ラベル版を en/figs/ に描く

  figs/mechanism.png  (a) 谷の横断の模式図(隆起・風化による土層生成・深さ依存クリープ・渓流の被覆と
                      下刻)、(b) 渓流の縦断の模式図(斜面からの供給が下流ほど被覆を厚くする・出口の
                      基準面)、(c) 時間の扱い(代表出水と間欠係数による換算)と定常の式
  figs/setup.png      初期の地形(平面)、横断、倍率の分布(基準面と風化しない渓流)、設定の要約

入力は make_init.py が書く z_init.txt・up_base.txt・wthr_hill.txt・rock_base.txt(make で作る)。
依存: numpy, matplotlib
"""
import os
import sys
import math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_init import (Grid, VAL_LEN, HILL_L, S0, SH, QF, N, D50, LAM, HSTAR, KP, TAUC, PM, BETA, YR, F_FLOOD,
                       U_CAL, W0_CAL, D_CAL, SDSTAR, HC, UPLIFT0, WTHR_P0, CREEP_D, T_RUN, T_OUT, T_DROP)

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)

C_ROCK, C_SOIL, C_GRAVEL, C_WATER = "#9a9a9a", "#b98a52", "#d2b074", "#bcd8ee"
C_UP, C_WTHR, C_CREEP, C_INC, C_FLOW = "#7b4ea3", "#8c510a", "#2a78d6", "#c0392b", "#2c7fb8"
IF = F_FLOOD / YR                                        # 間欠係数
H_SS = SDSTAR * math.log(W0_CAL / U_CAL)                 # 定常の土層厚 (m)
D_EFF = D_CAL * (1.0 - math.exp(-H_SS / HC))             # 実効クリープ係数 (m2/yr)


def _arrow(ax, x0, y0, x1, y1, color, lw=1.5, style="-|>", ms=10):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw, shrinkA=0, shrinkB=0, mutation_scale=ms))


def _cross(ax):
    """谷の横断(模式。定常に近い形): 岩盤面・土層・渓流。"""
    x = np.linspace(-22, 22, 441)
    # 地表(放物線形の斜面)と岩盤面(土層 H_ss だけ下)
    zs = 0.9 + 0.0085 * (22.0 - np.abs(x)) * (22.0 + np.abs(x)) * 0.0 + 0.0065 * (np.abs(x) * (2 * 22.0 - np.abs(x)))
    zs = np.where(np.abs(x) <= 2.0, 0.0, zs)
    zr = zs - 0.55
    zr = np.where(np.abs(x) <= 2.0, -0.15, zr)
    ax.fill_between(x, -2.5, zr, color=C_ROCK, zorder=1)
    ax.fill_between(x, zr, zs, where=np.abs(x) > 2.0, color=C_SOIL, zorder=2)
    ax.fill_between(x, -0.15, -0.05, where=np.abs(x) <= 2.0, color=C_GRAVEL, zorder=2)
    ax.fill_between(x, -0.05, 0.07, where=np.abs(x) <= 2.0, color=C_WATER, zorder=2)
    ax.plot(x, zs, "k-", lw=1.0, zorder=3)
    ax.plot(x, zr, color="0.3", lw=0.8, ls="--", zorder=3)
    # 隆起
    for xi in (-17, -9, 9, 17):
        _arrow(ax, xi, -2.3, xi, -1.4, C_UP, lw=1.6, ms=9)
    ax.text(0, -2.15, T("隆起 U(fn_uplift の倍率 1。出口の行は 0)", "uplift U (multiplier 1 of fn_uplift; 0 on the outlet row)"),
            ha="center", fontsize=8, color=C_UP)
    # 風化(岩盤 → 土層)
    for xi in (-13, 13):
        zi = np.interp(xi, x, zr)
        _arrow(ax, xi, zi - 0.45, xi, zi + 0.05, C_WTHR, lw=1.3, ms=8)
    ax.text(13.5, np.interp(13, x, zr) - 0.75, T("風化: 岩盤が土層になる\nW0 e^{−H/sd*}(厚いほど遅い)", "weathering turns rock into soil\nW0 e^{−H/sd*} (slower under thick soil)"),
            fontsize=8, color=C_WTHR, va="top")
    # クリープ(土層が渓流へ)
    for xi in (-15, -9, 9, 15):
        zi = np.interp(xi, x, zs) + 0.28
        d = -1 if xi > 0 else 1
        _arrow(ax, xi, zi, xi + 3.2 * d, np.interp(xi + 3.2 * d, x, zs) + 0.28, C_CREEP, lw=1.5, ms=9)
    ax.text(-20.5, 2.45, T("深さ依存クリープ: 土層が斜面を下る\nq = D (1 − e^{−H/H_c}) S", "depth-dependent creep carries the soil downslope\nq = D (1 − e^{−H/H_c}) S"),
            fontsize=8, color=C_CREEP, va="top")
    # 渓流
    _arrow(ax, 0, -0.15, 0, -0.9, C_INC, lw=1.6, ms=9)
    ax.text(2.6, -0.5, T("渓流: 出水が岩盤を剥がし(剥離)、礫が削る(研磨)\n礫の被覆 e^{−H/H*} が下刻を抑える。定常では下刻 = 隆起",
                        "stream: the flood plucks the rock and gravel abrades it;\nthe cover e^{−H/H*} limits incision. Steady state: incision = uplift"),
            fontsize=8, color=C_INC, va="center")
    ax.text(0, 0.35, T("幅 1 セル", "one cell wide"), ha="center", fontsize=7.5, color=C_FLOW)
    ax.text(-6.5, np.interp(-6.5, x, zr) + 0.12, T("土層 H", "soil H"), fontsize=8, color="w", ha="right")
    ax.text(-6.5, np.interp(-6.5, x, zr) - 0.55, T("岩盤", "bedrock"), fontsize=8, ha="right")
    ax.text(-21.5, 3.0, T("分水界(壁)", "divide (wall)"), fontsize=7.5)
    ax.text(21.5, 3.0, T("分水界(壁)", "divide (wall)"), fontsize=7.5, ha="right")
    ax.set_xlim(-22, 22)
    ax.set_ylim(-2.5, 3.4)
    ax.set_xlabel(T("渓流からの距離 (m)(東西)", "distance from the stream (m) (east–west)"))
    ax.set_yticks([])
    ax.set_title(T("(a) 谷の横断: 隆起・風化・クリープと渓流の下刻(定常に近い形。模式)",
                   "(a) Valley cross-section: uplift, weathering, creep and stream incision (near steady state; schematic)"),
                 loc="left", fontsize=10)


def _long(ax):
    """渓流の縦断(模式): 谷頭の形成流量、斜面からの供給で下流ほど厚い被覆、出口の行は基準面。"""
    x = np.linspace(0, 200, 401)
    zr = 7.0 - 0.03 * x
    hcov = 0.08 + 0.55 * (x / 200.0) ** 1.5
    hw = 1.0
    ax.fill_between(x, zr - 3.0, zr, color=C_ROCK, zorder=1)
    ax.fill_between(x, zr, zr + hcov, color=C_GRAVEL, zorder=2)
    ax.fill_between(x, zr + hcov, zr + hcov + hw, color=C_WATER, zorder=1.5)
    ax.plot(x, zr, "k-", lw=1.0, zorder=3)
    ax.plot(x, zr + hcov + hw, color=C_FLOW, lw=1.0, zorder=3)
    # 出口の行(基準面)
    ax.fill_between([196, 204], [-1, -1], [9.5, 9.5], color="#f1dcdc", zorder=0.5)
    ax.text(200, 9.3, T("出口の行 = 基準面\n(隆起・風化・下刻なし)", "outlet row = base level\n(no uplift, weathering or incision)"),
            ha="center", va="top", fontsize=8, color=C_INC)
    # 流入
    _arrow(ax, -14, 7.0 + 0.08 + 0.5, -1, 7.0 + 0.08 + 0.5, C_FLOW, lw=2.0)
    ax.text(-14, 8.4, T("谷頭: 形成流量 Q = %g m³/s\n(一定。乾いた斜面に雨はない)" % QF, "head: formative discharge Q = %g m³/s\n(constant; no rain on the dry slopes)" % QF),
            fontsize=8, color=C_FLOW, va="bottom")
    # 斜面からの供給
    for xi in (40, 90, 140):
        zi = 7.0 - 0.03 * xi + 0.08 + 0.55 * (xi / 200.0) ** 1.5 + hw
        _arrow(ax, xi, zi + 1.6, xi, zi + 0.15, C_CREEP, lw=1.4, ms=8)
    ax.text(90, 7.0 - 0.03 * 90 + 0.08 + 0.55 * 0.45 ** 1.5 + hw + 1.75,
            T("斜面からクリープで届く土層(定常で両側 2 U L)\n→ 下流ほど流砂量が増え、被覆が厚くなる",
              "soil delivered by creep from the slopes (2 U L in steady state)\n→ transport and cover grow downstream"),
            ha="center", va="bottom", fontsize=8, color=C_CREEP)
    # 隆起と下刻
    for xi in (30, 100, 170):
        _arrow(ax, xi, 7.0 - 0.03 * xi - 2.8, xi, 7.0 - 0.03 * xi - 1.9, C_UP, lw=1.4, ms=8)
    ax.text(100, 7.0 - 0.03 * 100 - 2.2, T("隆起 U", "uplift U"), ha="center", fontsize=8, color=C_UP)
    for xi in (60, 130):
        _arrow(ax, xi, 7.0 - 0.03 * xi + 0.02, xi, 7.0 - 0.03 * xi - 0.7, C_INC, lw=1.4, ms=8)
    ax.text(130, 7.0 - 0.03 * 130 - 0.85, T("下刻 (E_p0 + β q)(1 − q/q_c) = U\n→ 勾配が決まる", "incision (E_p0 + β q)(1 − q/q_c) = U\n→ sets the slope"),
            fontsize=8, color=C_INC, va="top", ha="center")
    _arrow(ax, 201, 7.0 - 0.03 * 200 + 0.3, 212, 7.0 - 0.03 * 200 + 0.3, C_GRAVEL, lw=2.0)
    ax.text(203, 7.0 - 0.03 * 200 + 0.6, T("掃流砂は南辺から出る", "bedload leaves at the south edge"), fontsize=7.5)
    ax.set_xlim(-16, 216)
    ax.set_ylim(-1.0, 10.5)
    ax.set_xlabel(T("谷頭からの距離 (m)(北 → 南)", "distance from the valley head (m) (north → south)"))
    ax.set_yticks([])
    ax.set_title(T("(b) 渓流の縦断: 斜面の供給と被覆、出口の基準面(縦は誇張。模式)",
                   "(b) Stream profile: supply from the slopes, cover and the base level at the outlet (vertical exaggerated; schematic)"),
                 loc="left", fontsize=10)


def _time(ax):
    """時間の扱い: 暦の 1 年のうち出水 F = 300 s だけ計算し、連続過程の係数を 1/i_f 倍する。"""
    ax.axis("off")
    # 暦の年の帯
    ax.add_patch(plt.Rectangle((0.03, 0.74), 0.94, 0.11, color="#e4e2dc"))
    ax.add_patch(plt.Rectangle((0.03, 0.74), 0.94 * 0.06, 0.11, color=C_FLOW))
    ax.text(0.03, 0.87, T("暦の 1 年(隆起・風化・クリープは一年中働く)", "one calendar year (uplift, weathering and creep work all year)"),
            fontsize=8.5, va="bottom")
    ax.text(0.03 + 0.94 * 0.06 + 0.01, 0.795, T("出水 F = %g s/年(礫が動き、岩盤が削れるのはこの間だけ)。実際の比 i_f = F/1 年 = %.1e は帯より小さい"
                                                 % (F_FLOOD, IF),
                                                 "flood F = %g s per year (gravel moves and rock wears only then); the real ratio i_f = F/year = %.1e is smaller than drawn"
                                                 % (F_FLOOD, IF)),
            fontsize=7.5, va="center")
    lines = [
        T("計算するのは出水だけ(一定の形成流量 Q)。地形の変化は morfac で加速する。",
          "Only the flood is computed (constant formative discharge Q); the landform change is accelerated by morfac."),
        T("連続に働く過程の係数は 1/i_f 倍して与える(その過程だけを暦の時間で進めるのと同じ):",
          "Coefficients of the continuous processes are multiplied by 1/i_f (the same as advancing only those processes on calendar time):"),
        "   uplift0 = %g mm/yr / i_f = %.1f mm/yr,  wthr_p0 = %g mm/yr / i_f = %.3e mm/kyr,  creep_d = %g m²/yr / F = %.4e m²/s"
        % (U_CAL, UPLIFT0, W0_CAL, WTHR_P0, D_CAL, CREEP_D),
        T("暦の時間 = 出水の時間 / F × 1 年。20 万年 = 出水の時間 6×10⁵ s(morfac %g で流れの時間 %.0f s)。"
          % (Grid("4m").morfac, Grid("4m").flow_time(T_RUN)),
          "calendar time = flood time / F × 1 year; 200,000 years = flood time 6×10⁵ s (flow time %.0f s with morfac %g)."
          % (Grid("4m").flow_time(T_RUN), Grid("4m").morfac)),
        "",
        T("定常の予測(結果と比べる):", "Steady-state predictions (compared with the results):"),
        T("  斜面: 岩盤面が動かない W0 e^{−H/sd*} = U → 土層厚 H_ss = sd* ln(W0/U) = %.3f m" % H_SS,
          "  hillslopes: bedrock surface at rest, W0 e^{−H/sd*} = U → soil depth H_ss = sd* ln(W0/U) = %.3f m" % H_SS),
        T("        地表が動かない ∇·(D_eff ∇z) = −U → 放物線形、D_eff = D (1 − e^{−H_ss/H_c}) = %.4f m²/yr" % D_EFF,
          "        ground surface at rest, ∇·(D_eff ∇z) = −U → parabolic form, D_eff = D (1 − e^{−H_ss/H_c}) = %.4f m²/yr" % D_EFF),
        T("  渓流: 各セルで下刻 = 隆起 (E_p0(S) + β q)(1 − q/q_c(S)) = U。q は谷頭から、剥離物と斜面の供給 2 U L で増える",
          "  stream: incision = uplift in each cell, (E_p0(S) + β q)(1 − q/q_c(S)) = U; q grows from the head by plucked rock and the supply 2 U L"),
        T("        → 等流の水理で谷頭から順に解いた勾配と、被覆の厚さ H* ln(1/(1 − q/q_c))",
          "        → slope solved cell by cell from the head with uniform-flow hydraulics, and cover thickness H* ln(1/(1 − q/q_c))"),
    ]
    yv = 0.66
    for ln in lines:
        ax.text(0.03, yv, ln, fontsize=8, va="top", family=matplotlib.rcParams["font.family"])
        yv -= 0.075
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_title(T("(c) 時間の扱い(間欠係数による換算)と定常の予測", "(c) Time (conversion by the intermittency factor) and steady-state predictions"),
                 loc="left", fontsize=10)


def mechanism():
    fig = plt.figure(figsize=(14, 11.5))
    gs = fig.add_gridspec(3, 1, height_ratios=[1.0, 1.0, 0.95], hspace=0.38)
    _cross(fig.add_subplot(gs[0]))
    _long(fig.add_subplot(gs[1]))
    _time(fig.add_subplot(gs[2]))
    fig.savefig(f"{FIGDIR}/mechanism.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


def setup():
    g = Grid("4m")
    z = np.loadtxt("z_init.txt")
    up = np.loadtxt("up_base.txt")
    wt = np.loadtxt("wthr_hill.txt")
    ny, nx = z.shape
    dx = g.dx
    fig = plt.figure(figsize=(14.5, 6.4))
    gs = fig.add_gridspec(2, 4, width_ratios=[0.55, 1.3, 0.55, 1.2], height_ratios=[1, 1], wspace=0.5, hspace=0.5)
    # 平面(初期の地形)
    ax = fig.add_subplot(gs[:, 0])
    im = ax.imshow(z, origin="upper", extent=[0, nx * dx, ny * dx, 0], cmap="terrain", aspect="auto")
    ax.axvline((g.ic - 1) * dx, color=C_FLOW, lw=1.0, ls="--")
    ax.axvline(g.ic * dx, color=C_FLOW, lw=1.0, ls="--")
    ax.text((g.ic - 0.5) * dx, 100, T("渓流(幅 1 セル)", "stream (one cell)"), rotation=90, ha="center", va="center", fontsize=7.5, color="w")
    ax.text(0.5, 1.02, T("谷頭: 形成流量 ↓", "head: formative discharge ↓"), ha="center", fontsize=7.5, transform=ax.transAxes)
    ax.set_xlabel(T("x (m)\n南辺: 自由流出", "x (m)\nsouth: free outflow"), fontsize=8)
    ax.set_ylabel(T("y (m)(流れは上から下へ)", "y (m) (flow from top to bottom)"))
    ax.set_title(T("初期の地形(裸岩の V 字)\n", "Initial terrain (bare-rock V)\n"), fontsize=9)
    fig.colorbar(im, ax=ax, shrink=0.45, pad=0.1).set_label(T("地盤高 (m)", "elevation (m)"))
    # 横断
    ax = fig.add_subplot(gs[0, 1])
    xc = (np.arange(nx) + 0.5) * dx - (g.ic - 0.5) * dx
    j = ny // 2
    ax.fill_between(xc, z[j].min() - 1, z[j], color=C_ROCK, alpha=0.8)
    ax.plot(xc, z[j], "k-", lw=1.3, marker="o", ms=3, label=T("初期の地表 = 岩盤面(土層 0)", "initial surface = bedrock (no soil)"))
    k = np.arange(0, g.lh + 1)
    zp = (U_CAL * 1.0e-3 / D_EFF) * dx ** 2 * (k * g.lh - k * (k - 1) / 2.0) + z[j, g.ic - 1]
    ax.plot(np.concatenate([-k[::-1] * dx, k[1:] * dx]), np.concatenate([zp[::-1], zp[1:]]), color="C3", lw=1.3, ls="--",
            label=T("定常の予測(放物線形。分水界は渓流の底より %.2f m 高い)" % (zp[-1] - zp[0]),
                    "steady prediction (parabola; divide %.2f m above the stream bed)" % (zp[-1] - zp[0])))
    ax.text(-20, z[j, g.ic - 1] + 3.4, T("斜面の勾配 %g" % SH, "hillslope gradient %g" % SH), fontsize=8)
    ax.set_xlabel(T("渓流からの距離 (m)", "distance from the stream (m)"))
    ax.set_ylabel("z (m)")
    ax.legend(fontsize=7, loc="upper center")
    ax.set_title(T("横断(y = %g m の行)" % (j * dx), "Cross-section (row y = %g m)" % (j * dx)), fontsize=9)
    # 縦断
    ax = fig.add_subplot(gs[1, 1])
    yy = (np.arange(ny) + 0.5) * dx
    ax.fill_between(yy, z[:, g.ic - 1].min() - 1, z[:, g.ic - 1], color=C_ROCK, alpha=0.8)
    ax.plot(yy, z[:, g.ic - 1], "k-", lw=1.3, label=T("渓流の初期の谷底(勾配 %g)" % S0, "initial stream bed (slope %g)" % S0))
    ax.plot(yy, z[:, 0], color="0.4", lw=1.0, ls=":", label=T("分水界(東西の端)", "divide (east and west edges)"))
    ax.axvspan((ny - 1) * dx, ny * dx, color="#f1dcdc")
    ax.text((ny - 1) * dx, z[:, 0].max() - 0.5, T("出口の行 = 基準面", "outlet row = base level"), ha="right", fontsize=7.5, color=C_INC)
    ax.set_xlim(0, ny * dx)
    ax.set_xlabel(T("谷頭からの距離 (m)", "distance from the valley head (m)"))
    ax.set_ylabel("z (m)")
    ax.legend(fontsize=7, loc="upper right")
    ax.set_title(T("縦断", "Profile"), fontsize=9)
    # 倍率の分布
    ax = fig.add_subplot(gs[:, 2])
    m = np.ones_like(z)
    m[wt == 0] = 0.5
    m[up == 0] = 0.0
    ax.imshow(m, origin="upper", extent=[0, nx * dx, ny * dx, 0], cmap="viridis", vmin=0, vmax=1, aspect="auto")
    ax.set_xlabel("x (m)")
    ax.set_yticks([])
    ax.set_title(T("倍率の分布\n", "Multiplier maps\n"), fontsize=9)
    ax.text(0.5, -0.1, T("黄: 隆起・風化・下刻 1\n緑: 渓流(風化 0)\n紫: 出口の行(隆起・風化・下刻 0)",
                         "yellow: uplift, weathering, incision 1\ngreen: stream (weathering 0)\npurple: outlet row (all 0)"),
            ha="center", va="top", fontsize=7.5, transform=ax.transAxes)
    # 設定の要約
    ax = fig.add_subplot(gs[:, 3])
    ax.axis("off")
    h0, v0 = g.uniform(S0)
    rows = [
        (T("谷", "valley"), T("長さ %g m × 幅 %g m、Δx = %g m(%d × %d セル)\n中央の列が渓流、両側に長さ %g m の斜面" % (VAL_LEN, nx * dx, dx, nx, ny, HILL_L),
                           "%g m long × %g m wide, Δx = %g m (%d × %d cells)\nmiddle column = stream, %g m of hillslope each side" % (VAL_LEN, nx * dx, dx, nx, ny, HILL_L))),
        (T("初期", "initial"), T("裸岩の V 字(土層 0)。谷底の勾配 %g、斜面の勾配 %g" % (S0, SH), "bare-rock V (no soil); bed slope %g, hillslope gradient %g" % (S0, SH))),
        (T("出水", "flood"), T("谷頭に形成流量 Q = %g m³/s(等流水深 %.2f m)\n斜面は乾いたまま、南辺は自由流出" % (QF, h0),
                           "formative discharge Q = %g m³/s at the head (uniform depth %.2f m)\nslopes stay dry; free outflow at the south edge" % (QF, h0))),
        (T("渓流", "stream"), T("d50 = %g cm、空隙率 %g、H* = %g m\n剥離 k_p = %.1e m/s、τ_c = %g Pa、m = %g\n研磨 β = %.1e 1/m(出水中の値)" % (D50 * 100, LAM, HSTAR, KP, TAUC, PM, BETA),
                            "d50 = %g cm, porosity %g, H* = %g m\nplucking k_p = %.1e m/s, τ_c = %g Pa, m = %g\nabrasion β = %.1e 1/m (values during floods)" % (D50 * 100, LAM, HSTAR, KP, TAUC, PM, BETA))),
        (T("斜面(暦の値)", "slopes (calendar)"), T("隆起 U = %g mm/yr\n土層生成 W0 = %g mm/yr(sd* = %g m)\nクリープ D = %g m²/yr(H_c = %g m)" % (U_CAL, W0_CAL, SDSTAR, D_CAL, HC),
                                            "uplift U = %g mm/yr\nsoil production W0 = %g mm/yr (sd* = %g m)\ncreep D = %g m²/yr (H_c = %g m)" % (U_CAL, W0_CAL, SDSTAR, D_CAL, HC))),
        (T("時間", "time"), T("出水 %g s/年(i_f = %.1e)。dt = %g s、morfac %g(dts = %g s)\n暦の %g 万年、出力は %g 万年ごと" % (F_FLOOD, IF, g.dt, g.morfac, g.dt * g.morfac, T_RUN / 1e4, T_OUT / 1e4),
                           "flood %g s/yr (i_f = %.1e); dt = %g s, morfac %g (dts = %g s)\n%g kyr of calendar time, output every %g kyr" % (F_FLOOD, IF, g.dt, g.morfac, g.dt * g.morfac, T_RUN / 1e3, T_OUT / 1e3))),
    ]
    yv = 0.98
    for k, v in rows:
        ax.text(0.0, yv, k, fontsize=8.5, fontweight="bold", va="top")
        ax.text(0.3, yv, v, fontsize=8.5, va="top")
        yv -= 0.07 + 0.052 * v.count("\n")
    ax.set_title(T("主ケース(V_b)の設定", "Settings of the main case (V_b)"), fontsize=9, loc="left")
    fig.savefig(f"{FIGDIR}/setup.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    mechanism()
    setup()
    print(f"{FIGDIR}/mechanism.png, {FIGDIR}/setup.png written")
