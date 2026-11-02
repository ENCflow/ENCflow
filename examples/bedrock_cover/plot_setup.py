#!/usr/bin/env python3
"""examples/bedrock_cover の機構の模式図と設定の図(計算結果は使わない)。

  python3 plot_setup.py        # figs/mechanism.png, figs/setup.png
  python3 plot_setup.py en     # 英語ラベル版を en/figs/ に描く

  figs/mechanism.png  (a) 岩盤河道の縦断の模式図(剥離・研磨・被覆・薄層の輸送)、
                      (b) 定常の下刻速度と給砂比(道具と被覆)、(c) 定常の被覆の厚さと露出率
  figs/setup.png      水路の配置(平面)、縦断(一様な水路と段差)、給砂の時系列(一定とパルス)、
                      設定の要約

入力は make_init.py が書く zinit_6.txt・zinit_2_step.txt(make で作る)。定数は make_init.py から読む。
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
from make_init import (NY, DX, S, N, H0, V0, Q, D50, LAM, HSTAR, KP, TAUC, PM, BETA, QC, DT, MORFAC, J1, J2,
                       R_SWEEP, R_MEAN, R_ON, P_SHORT, P_LONG, SD_INIT, R_COVER, J_STEP, DZ_STEP, R_KNICK,
                       qb_const, qb_pulse)

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)

C_ROCK, C_GRAVEL, C_WATER, C_FLOW = "#9a9a9a", "#d2b074", "#bcd8ee", "#2c7fb8"
C_PLUCK, C_TOOL, C_COVER = "#c0392b", "#8c510a", "#52744b"
RHO, G = 1000.0, 9.8
TAUB = RHO * G * N ** 2 * V0 ** 2 / H0 ** (1.0 / 3.0)              # 等流の底面せん断 (Pa)
EP0 = KP * (TAUB / TAUC - 1.0) ** PM if TAUB > TAUC else 0.0      # 裸岩の剥離速度 (m/s)
QC_UNI = 1.83e-3                                                  # 等流の掃流砂容量(README の値。m2/s 固体)


def _arrow(ax, x0, y0, x1, y1, color, lw=1.5, style="-|>", ms=10):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw, shrinkA=0, shrinkB=0, mutation_scale=ms))


def _profile(ax):
    """岩盤河道の縦断(模式。縦は誇張)。上流で薄く、下流で厚くなる被覆。"""
    x = np.linspace(0, 100, 401)
    zr = 10.0 - 0.06 * x                                 # 岩盤面 R(模式の勾配)
    hcov = 0.25 + 1.6 * (x / 100.0) ** 2                 # 可動層の厚さ H(模式。下流ほど厚い)
    hw = 2.2                                             # 水深(模式)
    ax.fill_between(x, zr - 4.0, zr, color=C_ROCK, zorder=1)
    ax.fill_between(x, zr, zr + hcov, color=C_GRAVEL, zorder=2)
    ax.fill_between(x, zr + hcov, zr + hcov + hw, color=C_WATER, zorder=1.5)
    ax.plot(x, zr, color="k", lw=1.0, zorder=3)
    ax.plot(x, zr + hcov, color=C_TOOL, lw=0.9, zorder=3)
    ax.plot(x, zr + hcov + hw, color=C_FLOW, lw=1.0, zorder=3)
    # 流れと給砂
    _arrow(ax, 2, 10.0 + hcov[0] + hw + 1.3, 16, 10.0 - 0.06 * 16 + 1.9 + hw + 1.3, C_FLOW, lw=1.8)
    ax.text(2, 15.2, T("出水の流れ(一定の流量 Q。浅水流)", "flood flow (constant Q; shallow water)"),
            fontsize=8.5, color=C_FLOW)
    _arrow(ax, -7, 10.5, 1, 10.5, C_TOOL, lw=2.0)
    ax.text(-7.5, 11.1, T("給砂 q_in = r q_c\n(inflow_qb)", "supply q_in = r q_c\n(inflow_qb)"),
            fontsize=8, color=C_TOOL)
    _arrow(ax, 99, 4.0 + 1.0, 107, 4.0 + 1.0, C_TOOL, lw=2.0)
    ax.text(100.5, 6.1, T("流出 q = q_c (1 − e^{−H/H*})\n(薄い層は運び切れない)",
                           "outflow q = q_c (1 − e^{−H/H*})\n(a thin layer is not fully carried)"),
            fontsize=8, color=C_TOOL, ha="left")
    # 剥離(上流の露出した岩盤)
    for xi in (14, 24, 34):
        zi = 10.0 - 0.06 * xi
        _arrow(ax, xi, zi + 0.15, xi, zi - 1.1, C_PLUCK, lw=1.4, ms=9)
    ax.text(5, 10.0 - 0.06 * 24 - 2.2,
            T("剥離 E_p0 e^{−H/H*}\nE_p0 = k_p (τ_b/τ_c − 1)^m\n剥がれた岩は 1:1 で可動層へ(道具にもなる)",
              "plucking E_p0 e^{−H/H*}\nE_p0 = k_p (τ_b/τ_c − 1)^m\nplucked rock joins the mobile layer 1:1 (and serves as tools)"),
            fontsize=8, color=C_PLUCK, va="top")
    # 研磨(運ばれる礫 = 道具)
    for xi in (52, 60, 68):
        zi = 10.0 - 0.06 * xi + 0.25 + 1.6 * (xi / 100.0) ** 2
        t = np.linspace(0, 1, 20)
        ax.plot(xi + 6 * t, zi + 0.9 * np.sin(np.pi * t) + 0.05, color=C_TOOL, lw=1.1, zorder=4)
        ax.add_patch(plt.Circle((xi + 6, zi + 0.12), 0.22, color=C_TOOL, zorder=5))
    for xi in (58, 66):
        zi = 10.0 - 0.06 * xi
        _arrow(ax, xi, zi + 0.12, xi, zi - 0.8, C_PLUCK, lw=1.0, ms=7)
    ax.text(47, 10.0 - 0.06 * 60 - 1.6,
            T("研磨 β q e^{−H/H*}\n(運ばれる礫が岩盤を叩く = 道具。\n削れた細粒分は系外へ)",
              "abrasion β q e^{−H/H*}\n(transported gravel hammers the rock = tools;\nthe fines leave the domain)"),
            fontsize=8, color=C_TOOL, va="top")
    # 被覆
    _arrow(ax, 80, 10.0 - 0.06 * 80 + 0.25 + 1.6 * 0.8 ** 2 + hw + 1.0, 80, 10.0 - 0.06 * 80 + 0.25 + 1.6 * 0.8 ** 2 + 0.1,
           C_COVER, lw=1.0, ms=7)
    ax.text(80, 10.0 - 0.06 * 80 + 0.25 + 1.6 * 0.8 ** 2 + hw + 1.2,
            T("被覆 H(可動層。下流ほど厚い)\n露出率 e^{−H/H*}: 厚いほど岩盤は守られる",
              "cover H (mobile layer; thicker downstream)\nexposure e^{−H/H*}: a thicker cover protects the rock"),
            fontsize=8, color=C_COVER, ha="center", va="bottom")
    ax.text(97, 10.0 - 0.06 * 97 - 2.0, T("岩盤 R", "bedrock R"), fontsize=8.5, ha="right")
    ax.text(97, 10.0 - 0.06 * 97 + 0.25 + 1.6 * 0.97 ** 2 + hw + 0.3, T("水面", "water surface"),
            fontsize=8, color=C_FLOW, ha="right")
    ax.set_xlim(-10, 118)
    ax.set_ylim(0.5, 16.5)
    ax.set_xlabel(T("x (m)  上流 → 下流(幅 1 セルの掘り込み水路)", "x (m)  upstream → downstream (incised channel one cell wide)"))
    ax.set_yticks([])
    ax.set_title(T("(a) 岩盤河道の縦断: 剥離・研磨・被覆と薄層の輸送(縦は誇張)",
                   "(a) Bedrock channel in profile: plucking, abrasion, cover and thin-layer transport (vertical exaggerated)"),
                 loc="left", fontsize=10)


def _hump(ax):
    """定常の下刻速度 E = (1 − r)(E_p0 + β q_c r) と給砂比 r(道具と被覆)。"""
    r = np.linspace(0, 1, 201)
    ep = EP0 * 1.0e6
    ea = BETA * QC_UNI * 1.0e6
    ax.plot(r, ep * (1 - r), color="#287ca5", lw=2.0, label=T("剥離だけ: E_p0 (1 − r)", "plucking only: E_p0 (1 − r)"))
    ax.plot(r, ea * r * (1 - r), color="#ad5b29", lw=2.0, label=T("研磨だけ: β q_c r (1 − r)", "abrasion only: β q_c r (1 − r)"))
    ax.plot(r, (1 - r) * (ep + ea * r), color="#52744b", lw=2.0, label=T("両方", "both"))
    ax.axvline(0.5, color="0.6", lw=0.8, ls=":")
    ax.text(0.51, ea * 0.25 + 0.15, T("研磨の最大 r = 1/2\n(道具と被覆の釣り合い)", "abrasion peaks at r = 1/2\n(tools balance cover)"),
            fontsize=7.5, color="#ad5b29")
    ax.text(0.02, ep + 0.1, T("給砂なし: 剥離だけが削る", "no supply: only plucking wears"), fontsize=7.5, color="#287ca5")
    ax.text(0.98, 1.9, T("全被覆 r → 1:\n下刻は 0", "full cover r → 1:\nno incision"), fontsize=7.5, ha="right")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 3.6)
    ax.set_xlabel(T("給砂比 r = q_in / q_c", "supply ratio r = q_in / q_c"))
    ax.set_ylabel(T("定常の下刻速度 (10⁻⁶ m/s)", "steady incision rate (10⁻⁶ m/s)"))
    ax.legend(fontsize=7.5, loc="upper right")
    ax.set_title(T("(b) 定常の下刻速度と給砂比(道具と被覆)", "(b) Steady incision rate against supply ratio (tools and cover)"),
                 loc="left", fontsize=10)
    ax.text(0.1, 0.1, T("この例題の値: E_p0 = %.1f, β q_c = %.1f (10⁻⁶ m/s)" % (ep, ea),
                        "values of this example: E_p0 = %.1f, β q_c = %.1f (10⁻⁶ m/s)" % (ep, ea)),
            fontsize=7.5, va="bottom")


def _cover(ax):
    """定常の被覆の厚さ H = H* ln(1/(1 − r)) と露出率 1 − r。"""
    r = np.linspace(0, 0.98, 200)
    h = HSTAR * 100.0 * np.log(1.0 / (1.0 - r))
    ax.plot(r, h, color="#52744b", lw=2.0, label=T("被覆の厚さ H = H* ln(1/(1 − r))", "cover thickness H = H* ln(1/(1 − r))"))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 4.5)
    ax.set_xlabel(T("給砂比 r = q_in / q_c", "supply ratio r = q_in / q_c"))
    ax.set_ylabel(T("被覆の厚さ H (cm)", "cover thickness H (cm)"), color="#52744b")
    ax2 = ax.twinx()
    ax2.plot(r, 1 - r, color="#c0392b", lw=1.6, ls="--", label=T("露出率 e^{−H/H*} = 1 − r", "exposure e^{−H/H*} = 1 − r"))
    ax2.set_ylim(0, 1.1)
    ax2.set_ylabel(T("露出率", "exposed fraction"), color="#c0392b")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=7.5, loc="upper left")
    ax.text(0.9, 3.6, T("H* = %g cm。定常では流出 = 流入:\nq_c (1 − e^{−H/H*}) = q_in" % (HSTAR * 100),
                        "H* = %g cm. Steady state: outflow = inflow:\nq_c (1 − e^{−H/H*}) = q_in" % (HSTAR * 100)),
            fontsize=7.5, ha="right", va="top")
    ax.set_title(T("(c) 定常の被覆の厚さと露出率", "(c) Steady cover thickness and exposure"), loc="left", fontsize=10)


def mechanism():
    fig = plt.figure(figsize=(13.5, 9.4))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.05, 1], hspace=0.34, wspace=0.3)
    _profile(fig.add_subplot(gs[0, :]))
    _hump(fig.add_subplot(gs[1, 0]))
    _cover(fig.add_subplot(gs[1, 1]))
    fig.savefig(f"{FIGDIR}/mechanism.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


def setup():
    z6 = np.loadtxt("zinit_6.txt")
    zs = np.loadtxt("zinit_2_step.txt")
    ny, nx = z6.shape
    fig = plt.figure(figsize=(14.5, 6.6))
    gs = fig.add_gridspec(2, 3, width_ratios=[0.75, 1.5, 1.25], height_ratios=[1, 1], wspace=0.38, hspace=0.5)
    # 平面(A の 6 本の水路)
    ax = fig.add_subplot(gs[:, 0])
    ax.imshow(z6, origin="upper", extent=[0, nx * DX, ny * DX, 0], cmap="terrain", vmin=9.5, vmax=13.5, aspect="auto")
    for k, r in enumerate(R_SWEEP):
        ax.text((2 * k + 1.5) * DX, 12.0, "r = %g" % r, rotation=90, ha="center", va="top", fontsize=7,
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.8, pad=1.0))
    ax.axhline(J1 * DX, color="k", lw=0.9, ls="--")
    ax.axhline(J2 * DX, color="k", lw=0.9, ls="--")
    ax.text(1.03, 1 - (J1 + J2) / 2.0 / ny, T("測る区間\n30〜90 m", "measured\nreach\n30–90 m"), fontsize=7.5, va="center",
            transform=ax.transAxes)
    ax.text(0.5, 1.02, T("北端: 区間流入 Q と給砂 ↓", "north: inflow Q and supply ↓"), ha="center", fontsize=7.5,
            transform=ax.transAxes)
    ax.set_xlabel(T("x (m)\n南辺: 自由流出。濃い縞 = 水路、淡い縞 = 岸 (+2 m)", "x (m)\nsouth: free outflow. dark stripes = channels, light = banks (+2 m)"),
                  fontsize=8)
    ax.set_ylabel(T("y (m)(流れは上から下へ)", "y (m) (flow from top to bottom)"))
    ax.set_title(T("水路の配置(構成 A。水路 6 本と岸)\n", "Channel layout (configuration A: 6 channels and banks)\n"), fontsize=9)
    # 縦断
    ax = fig.add_subplot(gs[0, 1])
    y = (np.arange(ny) + 0.5) * DX
    ax.fill_between(y, 9.6, z6[:, 1], color="#d9d9d9")
    ax.plot(y, z6[:, 1], "k-", lw=1.3, label=T("一様な水路(勾配 0.01)", "uniform channel (slope 0.01)"))
    ax.plot(y, zs[:, 1], color="C3", lw=1.3, ls="--", label=T("段差 0.3 m(構成 D。70 m より下流)", "0.3 m step (configuration D; below 70 m)"))
    ax.plot(y, z6[:, 0], color="0.5", lw=0.9, ls=":", label=T("岸(+2 m、乾いたまま)", "banks (+2 m, dry)"))
    ax.axvspan(J1 * DX, J2 * DX, color="0.92")
    ax.text((J1 + J2) / 2 * DX, 12.7, T("測る区間", "measured reach"), ha="center", fontsize=7.5)
    ax.set_xlim(0, ny * DX)
    ax.set_ylim(9.6, 13.4)
    ax.set_xlabel(T("流入端からの距離 (m)", "distance from the inflow end (m)"))
    ax.set_ylabel("z (m)")
    ax.legend(fontsize=7, loc="upper right")
    ax.set_title(T("縦断(水路の列)", "Profile (channel column)"), fontsize=9)
    # 給砂の時系列(B)
    ax = fig.add_subplot(gs[1, 1])
    tg = np.linspace(0, 6.0e4, 12001)

    def series(pts):
        t = np.array([p[0] * 60.0 * MORFAC for p in pts])      # 分(流れの時間)→ 地形の時間 (s)
        v = np.array([p[1] / (QC * DX) for p in pts])
        return np.interp(tg, t, v)

    ax.plot(tg, series(qb_const(R_MEAN)), color="k", lw=1.4, label=T("一定給砂 r = %g" % R_MEAN, "constant supply r = %g" % R_MEAN))
    ax.plot(tg, series(qb_pulse(R_ON, P_LONG, 6000)), color="C1", lw=1.2,
            label=T("パルス 周期 %g s(半分の時間だけ r = %g)" % (P_LONG, R_ON), "pulses, period %g s (r = %g half of the time)" % (P_LONG, R_ON)))
    ax.plot(tg[tg <= 3000], series(qb_pulse(R_ON, P_SHORT, 6000))[tg <= 3000], color="C0", lw=0.8,
            label=T("パルス 周期 %g s(最初の 3000 s だけ表示)" % P_SHORT, "pulses, period %g s (first 3000 s shown)" % P_SHORT))
    ax.set_xlim(0, 6.0e4)
    ax.set_ylim(-0.05, 0.95)
    ax.set_xlabel(T("地形の時間 (s)(流れの時間 × morfac %g)" % MORFAC, "morphological time (s) (flow time × morfac %g)" % MORFAC))
    ax.set_ylabel(T("給砂比 r", "supply ratio r"))
    ax.legend(fontsize=7, loc="upper right")
    ax.set_title(T("給砂の時系列(構成 B。同じ総量の一定給砂とパルス)", "Supply series (configuration B: constant and pulsed, same total)"), fontsize=9)
    # 設定の要約
    ax = fig.add_subplot(gs[:, 2])
    ax.axis("off")
    rows = [
        (T("水路", "channel"), T("幅 1 セル(Δx = 1 m)、長さ 100 m\n勾配 0.01、n = 0.04、両岸は +2 m", "one cell wide (Δx = 1 m), 100 m long\nslope 0.01, n = 0.04, banks at +2 m")),
        (T("流れ", "flow"), T("区間流入 Q = %.3f m³/s\n等流水深 %.1f m、V = %.2f m/s、τ_b = %.1f Pa" % (Q, H0, V0, TAUB),
                           "segment inflow Q = %.3f m³/s\nuniform depth %.1f m, V = %.2f m/s, τ_b = %.1f Pa" % (Q, H0, V0, TAUB))),
        (T("礫と被覆", "gravel, cover"), T("d50 = %g cm、空隙率 %g、H* = %g cm\n容量 q_c = %.2e m²/s(芦田・道上)" % (D50 * 100, LAM, HSTAR * 100, QC_UNI),
                                   "d50 = %g cm, porosity %g, H* = %g cm\ncapacity q_c = %.2e m²/s (Ashida–Michiue)" % (D50 * 100, LAM, HSTAR * 100, QC_UNI))),
        (T("岩盤下刻", "incision"), T("剥離 k_p = %.0e m/s、τ_c = %g Pa、m = %g\n(裸岩の E_p0 = %.1e m/s)\n研磨 β = %g 1/m(最大 β q_c/4 = %.1e m/s)" % (KP, TAUC, PM, EP0, BETA, BETA * QC_UNI / 4),
                                 "plucking k_p = %.0e m/s, τ_c = %g Pa, m = %g\n(bare-rock E_p0 = %.1e m/s)\nabrasion β = %g 1/m (max β q_c/4 = %.1e m/s)" % (KP, TAUC, PM, EP0, BETA, BETA * QC_UNI / 4))),
        (T("給砂", "supply"), T("流入セルの掃流砂 inflow_qb\n給砂比 r = q_in/q_c(q_c の概算 %.2e m²/s)" % QC,
                             "bedload at the inflow cell, inflow_qb\nsupply ratio r = q_in/q_c (estimate of q_c %.2e m²/s)" % QC)),
        (T("時間", "time"), T("dt = %g s、毎ステップ更新 × morfac %g(dts = 1 s)\n流れの時間 3000 s(B は 6000 s)\n= 地形の時間 3×10⁴ s(6×10⁴ s)" % (DT, MORFAC),
                           "dt = %g s, update every step × morfac %g (dts = 1 s)\nflow time 3000 s (6000 s for B)\n= morphological time 3×10⁴ s (6×10⁴ s)" % (DT, MORFAC))),
        (T("測る区間", "measured"), T("流入端から 30〜90 m の平均", "mean over 30–90 m from the inflow end")),
    ]
    yv = 0.98
    for k, v in rows:
        ax.text(0.0, yv, k, fontsize=8.5, fontweight="bold", va="top")
        ax.text(0.27, yv, v, fontsize=8.5, va="top")
        yv -= 0.065 + 0.05 * v.count("\n")
    ax.set_title(T("共通の設定", "Common settings"), fontsize=9, loc="left")
    fig.savefig(f"{FIGDIR}/setup.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    mechanism()
    setup()
    print(f"{FIGDIR}/mechanism.png, {FIGDIR}/setup.png written")
