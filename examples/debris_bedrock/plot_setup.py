#!/usr/bin/env python3
"""examples/debris_bedrock の機構の模式図と設定の図(計算結果は使わない)。

  python3 plot_setup.py        # figs/mechanism.png, figs/setup.png
  python3 plot_setup.py en     # 英語ラベル版を en/figs/ に描く

  figs/mechanism.png  (a) 渓流の縦断の模式図(谷頭からの土石流・急な区間の岩盤侵食・勾配の変わり目の
                      堆積・被覆)、(b) 混合体のハイドログラフ、(c) 岩盤侵食則と勾配、(d) 長期の連鎖
                      (出水と土石流を交互につなぐ)
  figs/setup.png      前半の渓流の縦断(5 区間の勾配)、後半の一様勾配の水路と落ち口、設定の要約

入力は make_init.py が書く z.txt(make で作る)。定数は make_init.py・make_long.py から読む。
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
from make_init import DX, NX, NY, BREAKS, QPEAK, TPEAK, TEND, CMIX, SDCOV, KD, TAUCD, MD, HSTAR, TT, DT, zc
from make_long import (NYR, NC, DY, SC, SLOPES, TRS, D50S, F, IF, MORFAC, QF, KP, TAUC, MP, U, NCYC, TDEB, DT_F,
                       UPLIFT_RUNS, NCYC_U, TR_U, D50_U, MID, W, zrow)

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)

C_ROCK, C_DEP, C_MIX, C_WATER = "#9a9a9a", "#d2b074", "#a0785a", "#bcd8ee"
C_ERODE, C_FLOW, C_TXT = "#c0392b", "#2c7fb8", "#52514e"
RHO, G, SG = 1000.0, 9.8, 1.65
REACH = [(BREAKS[k][0], BREAKS[k + 1][0] if k + 1 < len(BREAKS) else NY * DX, BREAKS[k][1]) for k in range(len(BREAKS))]


def _arrow(ax, x0, y0, x1, y1, color, lw=1.5, style="-|>", ms=10):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw, shrinkA=0, shrinkB=0, mutation_scale=ms))


def _profile(ax):
    """前半の渓流の縦断(実際の地形)に、土石流・侵食・堆積を模式的に重ねる。"""
    x = np.array([(j - 0.5) * DX for j in range(1, NY + 1)])
    z = np.array([zc(j) for j in range(1, NY + 1)])
    ax.fill_between(x, z.min() - 8, z, color=C_ROCK, zorder=1)
    ax.plot(x, z, "k-", lw=1.0, zorder=3)
    # 混合体(急な区間で厚く、緩む所で堆積する模式)
    ht = np.where(x < 120, 1.1 * 6, np.where(x < 220, 0.8 * 6, np.where(x < 300, 0.45 * 6, 0.2 * 6)))
    ht = ht * (1.0 - 0.35 * np.clip((x - 330) / 70.0, 0, 1))
    ax.fill_between(x, z, z + ht, color=C_MIX, alpha=0.85, zorder=2)
    dep = np.where((x > 100) & (x < 150), 3.0 * np.exp(-((x - 128) / 12.0) ** 2), 0.0) + \
        np.where((x > 200) & (x < 260), 5.0 * np.exp(-((x - 228) / 14.0) ** 2), 0.0)
    ax.fill_between(x, z, z + dep, color=C_DEP, zorder=2.5)
    # 侵食の矢印(急な区間)
    for xi in (20, 50, 80, 110, 150, 190):
        zi = np.interp(xi, x, z)
        _arrow(ax, xi, zi + 0.3, xi, zi - 7.0 if xi < 120 else zi - 4.0, C_ERODE, lw=1.8, ms=10)
    # ラベル
    _arrow(ax, -30, z[0] + 7, -3, z[0] + 7, C_MIX, lw=2.2)
    ax.text(-32, z[0] + 9.5, T("谷頭: 混合体のハイドログラフ\n(ピーク %g m³/s、C = %g。水 %g + 固体 %g m³/s)" % (QPEAK, CMIX, QPEAK * (1 - CMIX), QPEAK * CMIX),
                                "head: hydrograph of the mixture\n(peak %g m³/s, C = %g: water %g + solids %g m³/s)" % (QPEAK, CMIX, QPEAK * (1 - CMIX), QPEAK * CMIX)),
            fontsize=8, color=C_MIX, va="bottom")
    ax.text(6, 33, T("急な区間だけ削る: 駆動応力 τ_d = ρ(1 + sC) g_e h_t tanθ が\n閾値 τ_cd を超える。侵食速度 k_d (τ_d/τ_cd − 1)^m × 露出率 e^{−sd/H*}\n削った岩は 1:1 で可動層へ",
                     "erosion only on the steep reaches: the driving stress\nτ_d = ρ(1 + sC) g_e h_t tanθ exceeds the threshold τ_cd\nrate k_d (τ_d/τ_cd − 1)^m × exposure e^{−sd/H*}; eroded rock joins the mobile layer 1:1"),
            fontsize=8, color=C_ERODE, va="top")
    ax.text(228, np.interp(228, x, z) + 8.5, T("勾配が緩む所で堆積\n(平衡濃度に向かう)", "deposition where the slope eases\n(towards the equilibrium concentration)"),
            ha="center", fontsize=8, color="#8c510a", va="bottom")
    ax.text(300, np.interp(300, x, z) + 10, T("堆積層(sd)が床を守る: 露出率 e^{−sd/H*}、H* = %g m\n厚さ %g m の堆積層の構成では、剥がれるまで削れない" % (HSTAR, SDCOV),
                                             "a deposit (sd) protects the bed: exposure e^{−sd/H*}, H* = %g m\nwith the %g m deposit the rock erodes only once stripped" % (HSTAR, SDCOV)),
            fontsize=8, color=C_TXT, va="bottom")
    for a, b, s in REACH:
        ax.text((a + b) / 2, np.interp((a + b) / 2, x, z) - 5.5 if a >= 120 else np.interp((a + b) / 2, x, z) - 7.5,
                T("勾配 %g" % s, "slope %g" % s), ha="center", fontsize=8)
        ax.axvline(b, color="0.75", lw=0.6, ls=":")
    _arrow(ax, 401, z[-1] + 2.5, 418, z[-1] + 2.5, C_FLOW, lw=1.8)
    ax.text(402, z[-1] + 4.5, T("南辺: 自由流出", "south: free outflow"), fontsize=8, color=C_FLOW)
    ax.text(300, z[-1] + 24, T("混合体 = 単層(水 + 土砂。抵抗則と侵食・堆積式は 2 通り)", "single-layer mixture (water + sediment; two resistance laws with their erosion–deposition equations)"),
            fontsize=8, color=C_MIX, ha="center")
    ax.set_xlim(-34, 424)
    ax.set_ylim(z.min() - 8, z.max() + 16)
    ax.set_xlabel(T("谷頭からの距離 (m)", "distance from the head (m)"))
    ax.set_ylabel("z (m)")
    ax.set_title(T("(a) 渓流の縦断: 1 回の土石流がどこで岩盤を削り、どこに積もるか(模式)",
                   "(a) Stream profile: where one debris flow erodes the rock and where it deposits (schematic)"),
                 loc="left", fontsize=10)


def _hydro(ax):
    t = np.array([0.0, TPEAK, TEND, 100.0])
    q = np.array([0.0, QPEAK, 0.0, 0.0])
    ax.fill_between(t, 0, q * (1 - CMIX), color=C_WATER, label=T("水 (1 − C) Q", "water (1 − C) Q"))
    ax.fill_between(t, q * (1 - CMIX), q, color=C_MIX, alpha=0.8, label=T("固体 C Q(総量 %g m³)" % (QPEAK * TEND / 2 * CMIX), "solids C Q (%g m³ in total)" % (QPEAK * TEND / 2 * CMIX)))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 46)
    ax.set_xlabel(T("時刻 (s)", "time (s)"))
    ax.set_ylabel(T("谷頭の流量 (m³/s)", "discharge at the head (m³/s)"))
    ax.legend(fontsize=7.5, loc="upper right")
    ax.text(72, 30, T("計算は %g s(dt = %g s)\n岩盤は毎ステップ更新(morfac 1)" % (TT, DT), "run of %g s (dt = %g s)\nrock updated every step (morfac 1)" % (TT, DT)), fontsize=7.5)
    ax.set_title(T("(b) 谷頭の混合体のハイドログラフ", "(b) Hydrograph of the mixture at the head"), loc="left", fontsize=10)


def _law(ax):
    s = np.linspace(0.0, 0.42, 300)
    th = np.arctan(s)
    for ht, c in ((0.5, "#86b6ef"), (1.0, "#2a78d6"), (1.5, "#104281")):
        tau = RHO * (1 + SG * CMIX) * G * np.cos(th) ** 2 * ht * s
        e = KD * np.maximum(tau / TAUCD - 1.0, 0.0) ** MD * 1000.0 * 60.0
        ax.plot(s, e, color=c, lw=1.8, label=T("流動深 h_t = %g m" % ht, "flow depth h_t = %g m" % ht))
    ax.axhline(0, color="k", lw=0.6)
    for a, b, sl in REACH:
        ax.axvline(sl, color="0.8", lw=0.7, ls=":")
    ax.text(0.36, 0.5, T("この渓流の区間の勾配", "reach slopes of this stream"), fontsize=7, color="0.4", ha="right")
    ax.set_xlim(0, 0.42)
    ax.set_ylim(-2, 100)
    ax.set_xlabel(T("流向の河床勾配 tanθ", "bed slope tanθ along the flow"))
    ax.set_ylabel(T("裸岩の侵食速度 (mm/min)", "erosion rate of bare rock (mm/min)"))
    ax.legend(fontsize=7.5, loc="center left")
    ax.text(0.01, 98, T("k_d = %.1e m/s、τ_cd = %g kPa、m = %g\nρ(1 + sC) = %.0f kg/m³、g_e = g cos²θ" % (KD, TAUCD / 1000, MD, RHO * (1 + SG * CMIX)),
                         "k_d = %.1e m/s, τ_cd = %g kPa, m = %g\nρ(1 + sC) = %.0f kg/m³, g_e = g cos²θ" % (KD, TAUCD / 1000, MD, RHO * (1 + SG * CMIX))),
            fontsize=7.5, ha="left", va="top")
    ax.set_title(T("(c) 岩盤侵食則: 勾配と流動深で決まる閾値つきの速度", "(c) Rock erosion law: a rate with a threshold set by slope and flow depth"),
                 loc="left", fontsize=10)


def _chain(ax):
    ax.axis("off")
    boxes = [(0.02, T("出水\n(T_r 年分)", "floods\n(T_r years)"), C_WATER), (0.30, T("土石流\n1 回", "one debris\nflow"), C_MIX),
             (0.58, T("出水\n(T_r 年分)", "floods\n(T_r years)"), C_WATER), (0.86, "…", "white")]
    for xb, lab, c in boxes:
        ax.add_patch(plt.Rectangle((xb, 0.62), 0.12, 0.26, facecolor=c, edgecolor="k", lw=0.8))
        ax.text(xb + 0.06, 0.75, lab, ha="center", va="center", fontsize=8)
        if xb < 0.8:
            _arrow(ax, xb + 0.125, 0.75, xb + 0.275, 0.75, "k", lw=1.2, ms=9)
    ax.text(0.5, 0.95, T("f_state_restore = 2 でつなぐ(新しい時間軸、dt を変えられる)。累積下刻 Ri は続く",
                         "chained with f_state_restore = 2 (new time axis; dt can change); cumulative incision Ri continues"),
            ha="center", va="top", fontsize=8)
    lines = [
        T("出水: 清水 %g m³/s を年 %g s(i_f = %.1e)、morfac %g。流水の剥離 k_p = %.1e m/s、τ_c = %g Pa" % (QF, F, IF, MORFAC, KP, TAUC),
          "floods: clear water %g m³/s for %g s per year (i_f = %.1e), morfac %g; plucking k_p = %.1e m/s, τ_c = %g Pa" % (QF, F, IF, MORFAC, KP, TAUC)),
        T("土石流: 前半と同じ(高橋・中川、k_d・τ_cd・m_d)。%g s、morfac 1。暦には数えない" % TDEB,
          "debris flow: as in the first part (Takahashi–Nakagawa, k_d, τ_cd, m_d); %g s, morfac 1; not counted in the calendar" % TDEB),
        T("間隔 T_r = %s 年に 1 回と出水だけ。粒径 %s m。水路は横断 1 セル(幅 %g m)、一様勾配 %s + 落ち口 %g"
          % ("・".join(str(t) for t in TRS), "・".join(str(d) for d in D50S), W, "〜".join(str(s) for s in (SLOPES[0], SLOPES[-1])), SC),
          "once in T_r = %s years and floods only; sizes %s m; channel one cell across (%g m wide), uniform slopes %s + outfall %g"
          % (", ".join(str(t) for t in TRS), ", ".join(str(d) for d in D50S), W, "–".join(str(s) for s in (SLOPES[0], SLOPES[-1])), SC)),
        T("固定勾配: %d サイクルの中央区間(%g〜%g m)の低下速度 E(S) → 定常勾配は E(S*) = U(隆起 %g mm/年)を補間"
          % (NCYC, MID[0], MID[1], U),
          "fixed slopes: lowering rate E(S) of the middle reach (%g–%g m) over %d cycles → steady slope from E(S*) = U (uplift %g mm/yr)"
          % (MID[0], MID[1], NCYC, U)),
        T("確認: 隆起ありの連鎖 %d サイクル(粒径 %g m、%d 年に 1 回、初期勾配 %s)を 1 次元の予測 z_t = U − E(S) と比べる"
          % (NCYC_U, D50_U, TR_U, "・".join(str(s) for _, s in UPLIFT_RUNS)),
          "check: chains with uplift, %d cycles (size %g m, once in %d years, initial slopes %s), against the 1-D prediction z_t = U − E(S)"
          % (NCYC_U, D50_U, TR_U, ", ".join(str(s) for _, s in UPLIFT_RUNS))),
    ]
    yv = 0.5
    for ln in lines:
        ax.text(0.0, yv, ln, fontsize=7.5, va="top")
        yv -= 0.12
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_title(T("(d) 補足の長期の連鎖: 出水と土石流を交互につなぐ", "(d) Long-term chain of the supplement: floods and debris flows alternately"),
                 loc="left", fontsize=10)


def mechanism():
    fig = plt.figure(figsize=(14.5, 10.5))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.15, 1], hspace=0.35, wspace=0.3)
    _profile(fig.add_subplot(gs[0, :]))
    _hydro(fig.add_subplot(gs[1, 0]))
    _law(fig.add_subplot(gs[1, 1]))
    _chain(fig.add_subplot(gs[1, 2]))
    fig.savefig(f"{FIGDIR}/mechanism.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


def setup():
    z = np.loadtxt("z.txt")
    x = (np.arange(NY) + 0.5) * DX
    fig = plt.figure(figsize=(14.5, 6.2))
    gs = fig.add_gridspec(2, 3, width_ratios=[1.4, 1.1, 1.15], height_ratios=[1, 1], wspace=0.32, hspace=0.5)
    # 前半の縦断
    ax = fig.add_subplot(gs[:, 0])
    ax.fill_between(x, 0, z.mean(axis=1), color=C_ROCK, alpha=0.8)
    ax.plot(x, z.mean(axis=1), "k-", lw=1.2)
    for k, (a, b, s) in enumerate(REACH):
        if k % 2 == 0:
            ax.axvspan(a, b, color="0.93", zorder=0)
        ax.text((a + b) / 2, np.interp((a + b) / 2, x, z.mean(axis=1)) + 6, T("勾配 %g\n%g〜%g m" % (s, a, b), "slope %g\n%g–%g m" % (s, a, b)),
                ha="center", fontsize=7.5)
    ax.text(395, 97, T("幅 %g m(%d セル、Δx = %g m、両岸は壁)、長さ %g m\n谷頭の %d セルから混合体を流入、南端は自由流出、n = 0.05\n河床: 裸岩(sd = 0)、または厚さ %g m の堆積層" % (NX * DX, NX, DX, NY * DX, NX, SDCOV),
                        "%g m wide (%d cells, Δx = %g m, walls on both banks), %g m long\nmixture inflow at the %d head cells, free outflow at the south end, n = 0.05\nbed: bare rock (sd = 0) or a %g m deposit" % (NX * DX, NX, DX, NY * DX, NX, SDCOV)),
            fontsize=7.5, va="top", ha="right")
    ax.set_xlim(0, NY * DX)
    ax.set_ylim(0, 100)
    ax.set_xlabel(T("谷頭からの距離 (m)", "distance from the head (m)"))
    ax.set_ylabel("z (m)")
    ax.set_title(T("前半: 1 回の土石流を流す渓流(z.txt)", "First part: the stream for one debris flow (z.txt)"), fontsize=9)
    # 後半の水路
    ax = fig.add_subplot(gs[0, 1])
    yy = np.array([(j - 0.5) * DY for j in range(1, NYR + NC + 1)])
    for s, c in zip(SLOPES, plt.cm.viridis(np.linspace(0.1, 0.9, len(SLOPES)))):
        ax.plot(yy, [zrow(s, j) for j in range(1, NYR + NC + 1)], color=c, lw=1.3, label="S = %g" % s)
    ax.axvspan(NYR * DY, (NYR + NC) * DY, color="#f1dcdc")
    ax.text(NYR * DY + 1, 95, T("落ち口\n勾配 %g" % SC, "outfall\nslope %g" % SC), fontsize=7, va="top")
    ax.set_xlim(0, (NYR + NC) * DY)
    ax.set_xlabel(T("谷頭からの距離 (m)", "distance from the head (m)"))
    ax.set_ylabel("z (m)")
    ax.legend(fontsize=6.5, loc="lower left", ncol=2)
    ax.set_title(T("補足(長期): 一様勾配の水路(横断 1 セル、幅 %g m)" % W, "Supplement (long term): uniform channels (one cell across, %g m wide)" % W), fontsize=9)
    # ケースの一覧
    ax = fig.add_subplot(gs[1, 1])
    ax.axis("off")
    rows = [
        ("T_b / T_c", T("高橋・中川、裸岩 / 堆積層 %g m" % SDCOV, "Takahashi–Nakagawa, bare rock / %g m deposit" % SDCOV)),
        ("C_b / C_c", T("クーロン + Manning、裸岩 / 堆積層", "Coulomb + Manning, bare rock / deposit")),
        ("T_b05 / T_b20", T("T_b の閾値 τ_cd を 0.5 / 2 kPa に", "T_b with τ_cd = 0.5 / 2 kPa")),
        ("W", T("同じ流量の清水の出水(流水の剥離則に同じ係数)", "clear-water flood of the same discharge (fluvial plucking, same coefficients)")),
    ]
    yv = 0.95
    for k, v in rows:
        ax.text(0.0, yv, k, fontsize=8, fontweight="bold", va="top")
        ax.text(0.3, yv, v, fontsize=8, va="top")
        yv -= 0.2
    ax.set_title(T("前半の構成", "Configurations of the first part"), fontsize=9, loc="left")
    # 設定の要約
    ax = fig.add_subplot(gs[:, 2])
    ax.axis("off")
    rows = [
        (T("土石流", "debris flow"), T("谷頭の混合体の三角形のハイドログラフ\nピーク %g m³/s(%g s)、%g s で終了、C = %g" % (QPEAK, TPEAK, TEND, CMIX),
                                   "triangular hydrograph of the mixture at the head\npeak %g m³/s at %g s, end at %g s, C = %g" % (QPEAK, TPEAK, TEND, CMIX))),
        (T("土石流の則", "laws"), T("高橋・中川(f_dbres = 3・f_dbed = 3)と\nクーロン + Manning(f_dbres = 1・f_dbed = 1)\nφ = 35°、λ = 0.4、低速凝集 f_dbstop = 1",
                                     "Takahashi–Nakagawa (f_dbres = 3, f_dbed = 3) and\nCoulomb + Manning (f_dbres = 1, f_dbed = 1)\nφ = 35°, λ = 0.4, low-velocity settling f_dbstop = 1")),
        (T("岩盤侵食", "rock erosion"), T("k_d = %.1e m/s、τ_cd = %g kPa、m_d = %g\nH* = %g m" % (KD, TAUCD / 1000, MD, HSTAR),
                                     "k_d = %.1e m/s, τ_cd = %g kPa, m_d = %g\nH* = %g m" % (KD, TAUCD / 1000, MD, HSTAR))),
        (T("時間(前半)", "time (first part)"), T("%g s、dt = %g s、岩盤は毎ステップ更新(morfac 1)" % (TT, DT), "%g s, dt = %g s, rock updated every step (morfac 1)" % (TT, DT))),
        (T("出水(補足)", "floods (suppl.)"), T("清水 %g m³/s、年 %g s(i_f = %.1e)、morfac %g\n剥離 k_p = %.1e m/s、τ_c = %g Pa、研磨なし" % (QF, F, IF, MORFAC, KP, TAUC),
                                       "clear water %g m³/s, %g s per year (i_f = %.1e), morfac %g\nplucking k_p = %.1e m/s, τ_c = %g Pa, no abrasion" % (QF, F, IF, MORFAC, KP, TAUC))),
        (T("連鎖(補足)", "chain (suppl.)"), T("土石流 %s 年に 1 回と出水だけ、粒径 %s m\n固定勾配 %d サイクル、隆起ありの確認 %d サイクル" % ("・".join(str(t) for t in TRS), "・".join(str(d) for d in D50S), NCYC, NCYC_U),
                                       "debris flows once in %s years and floods only; sizes %s m\n%d cycles at fixed slopes, %d cycles for the check with uplift" % (", ".join(str(t) for t in TRS), ", ".join(str(d) for d in D50S), NCYC, NCYC_U))),
    ]
    yv = 0.98
    for k, v in rows:
        ax.text(0.0, yv, k, fontsize=8.5, fontweight="bold", va="top")
        ax.text(0.3, yv, v, fontsize=8.5, va="top")
        yv -= 0.07 + 0.052 * v.count("\n")
    ax.set_title(T("設定の要約", "Summary of the settings"), fontsize=9, loc="left")
    fig.savefig(f"{FIGDIR}/setup.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    mechanism()
    setup()
    print(f"{FIGDIR}/mechanism.png, {FIGDIR}/setup.png written")
