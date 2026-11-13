#!/usr/bin/env python3
"""bridge_wood_jam の図と数表(事前に make run と make sens で 8 ケースを計算しておく)。

  figs/setup.png   平面の配置(河道・氾濫原・台地・橋・流木の供給の区間・プローブ・測線)と出水の波形
  figs/laws.png    集積の実材積と堰上げの関係(式の積分。あふれないとした場合)と、計算の値
  figs/series.png  橋に集積した流木、橋のすぐ上流の水深、橋の断面を通る流量の時間変化
  figs/maps.png    出水のピークの河道の縦断(水面形)、最大浸水深、流木が残った場所
  figs/sens.png    捕捉の仮定(集積が進むと掛かりやすくなる速さ・捕捉率)と集積の抵抗の係数を変えた比較
引数 en で英語ラベル版を en/figs/ に描く(データと描画処理は共通)。引数 table で README 用の数表を出す。
"""
import glob
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Rectangle

from make_terrain import (NX, NY, DX, S, Z0, D_BANK, D_TER, J_CH1, J_CH2, I_BR, I_ST1, I_ST2,
                          N_CH, Q_BASE, Q_PEAK, uniform_depth)

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
# ---- 色(役割ごとに固定。系列の色は 3 色までで、ケースと色の対応は全図で同じ)----
SURF, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
C_JAM, C_LEDGER, C_NOWOOD = "#2a78d6", "#eb6834", "#1baf7a"      # 集積の抵抗あり / 台帳だけ / 流木なし
C_BYPASS = "#104281"                                             # 氾濫原を回る流量(集積ありの色の濃い段)
PHI_RAMP = {0.2: "#86b6ef", 0.3: "#2a78d6", 0.4: "#104281"}      # 充填率(順序のある 3 段。1 色相の淡 → 濃)
DEPTH_RAMP = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#0d366b"]     # 浸水深(1 色相の淡 → 濃)
WOOD_RAMP = ["#ee9a78", "#eb6834", "#c4521f", "#9c3f14", "#732c0b"]      # 流木(同)
C_FP, C_TER, C_CH = "#f0efec", "#d5d3ca", "#cde2fb"              # 氾濫原・台地・河道(背景)

matplotlib.rcParams.update({
    "font.family": ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"],
    "axes.unicode_minus": False,
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "axes.titlecolor": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelcolor": INK2, "ytick.labelcolor": INK2,
    "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "grid.linestyle": "-",
    "axes.spines.top": False, "axes.spines.right": False, "axes.axisbelow": True,
    "lines.linewidth": 2.0, "lines.solid_capstyle": "round", "lines.solid_joinstyle": "round",
    "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "legend.frameon": False, "legend.fontsize": 9.5,
})
os.makedirs(FIGDIR, exist_ok=True)

LX, LY = NX * DX, NY * DX
EXT = [0, LX, LY, 0]                    # 行 1 = 北を上に
X_BR = (I_BR - 0.5) * DX                # 橋の x (m)
Y_CH1, Y_CH2 = (J_CH1 - 1) * DX, J_CH2 * DX
SENS = [("jam", T("基本(捕捉率 0.3 → 1 層で全量)", "base (capture 0.3, all at 1 layer)")),
        ("slow", T("捕捉率 0.3 → 10 層で全量", "capture 0.3, all at 10 layers")),
        ("e03", T("捕捉率 0.3 のまま", "capture ratio stays 0.3")),
        ("e01", T("捕捉率 0.1 のまま", "capture ratio stays 0.1")),
        ("loose", T("基本で、すき間の多い集積(φ = 0.2)", "base, loose jam (φ = 0.2)")),
        ("dense", T("基本で、詰まった集積(φ = 0.4)", "base, dense jam (φ = 0.4)"))]
PROBES = [(238, 50), (160, 50), (260, 50), (238, 40), (280, 30)]
T_PROFILE = 90                          # 縦断を描く時刻(分。ピークの流量が続いている間)


def have(case):
    return os.path.exists(f"result_{case}/FILENUMBER.csv")


def rd(path):
    return np.loadtxt(path)


def flux(case, n):
    """フラックス測線 n の時刻(分)と流量 (m3/s)"""
    a = np.loadtxt(f"result_{case}/fluxes/flux{n:04d}.csv", delimiter=",", comments="#")
    return a[:, 1], a[:, 2]


def probe(case, n):
    """プローブ n の時刻(分)・水深 (m)・流速 (m/s)"""
    a = np.loadtxt(f"result_{case}/probes/probe{n:04d}.csv", delimiter=",", comments="#")
    return a[:, 1], a[:, 3], a[:, 6]


def ledger(case):
    """driftwood.csv(時刻は分に直す)"""
    a = np.genfromtxt(f"result_{case}/driftwood.csv", delimiter=",", names=True)
    return a["time_s"] / 60.0, a


def frame_at(case, var, minute):
    """時刻 minute(分)の分布出力"""
    for line in open(f"result_{case}/FILENUMBER.csv"):
        f = [s.strip() for s in line.split(",")]
        if line.startswith("#") or len(f) < 3:
            continue
        if abs(float(f[2]) - 60.0 * minute) < 1.0:
            return rd(f"result_{case}/{var}{int(f[0]):04d}.txt")
    raise RuntimeError(f"no frame at {minute} min in result_{case}")


def last_frame(case, var):
    ks = sorted(int(f[-8:-4]) for f in glob.glob(f"result_{case}/{var}0*.txt"))
    return rd(f"result_{case}/{var}{ks[-1]:04d}.txt")


def inflow_series():
    """param.txt の流入波形(分、m3/s)"""
    ts, qs = [], []
    for line in open("param.txt", encoding="utf-8"):
        if line.strip().startswith("inflow_val"):
            v = line.split("=")[1].split("!")[0].split(",")
            ts.append(float(v[0]))
            qs.append(float(v[1]))
    return np.array(ts), np.array(qs)


def metrics(case):
    """README の表と感度の図に使う数値"""
    m = {}
    t, h, _ = probe(case, 1)
    m["hmax"] = h.max()
    m["rise"] = h.max() - uniform_depth(Q_PEAK)          # 流木なしのピークの水深(等流)からの上昇
    m["t_over"] = next((tt for tt, hh in zip(t, h) if hh > D_BANK), None)
    tq, qb = flux(case, 2)
    m["qby"] = qb.max()
    m["t_by"] = next((tt for tt, q in zip(tq, qb) if q > 1.0), None)
    _, qc = flux(case, 1)
    m["qch_at_peak"] = qc[np.argmax(qb)] if qb.max() > 1.0 else qc.max()
    hmax = rd(f"result_{case}/H9999.txt")
    fp = np.zeros_like(hmax, dtype=bool)
    fp[:J_CH1 - 1, :] = True
    m["area"] = np.count_nonzero((hmax > 0.1) & fp) * DX * DX / 1.0e4          # ha
    m["hfp"] = hmax[fp].max()
    if os.path.exists(f"result_{case}/driftwood.csv"):
        tl, a = ledger(case)
        m["rec"] = a["rec_hyd_m3"][-1]
        m["jam"] = a["vol_jam_m3"][-1] if "vol_jam_m3" in a.dtype.names else 0.0
        m["dep"] = a["vol_deposit_m3"][-1]
        m["flt"] = a["vol_float_m3"][-1]
        m["stock"] = a["vol_stock_m3"][-1]
        m["out"] = a["vol_stock_m3"][0] - m["stock"] - m["jam"] - m["dep"] - m["flt"]
        if m["jam"] > 0:
            m["t_jam"] = next((tt for tt, v in zip(tl, a["vol_jam_m3"]) if v > 1.0), None)
    return m


def setup():
    fig = plt.figure(figsize=(11, 6.4))
    gs = fig.add_gridspec(2, 1, height_ratios=[1.25, 1.0], hspace=0.42, left=0.07, right=0.97, top=0.93, bottom=0.09)
    ax = fig.add_subplot(gs[0])
    ax.grid(False)
    ax.add_patch(Rectangle((0, 0), LX, Y_CH1, fc=C_FP, ec="none"))
    ax.add_patch(Rectangle((0, Y_CH1), LX, Y_CH2 - Y_CH1, fc=C_CH, ec="none"))
    ax.add_patch(Rectangle((0, Y_CH2), LX, LY - Y_CH2, fc=C_TER, ec="none"))
    xs1, xs2 = (I_ST1 - 1) * DX, I_ST2 * DX
    ax.add_patch(Rectangle((xs1, Y_CH1), xs2 - xs1, Y_CH2 - Y_CH1, fc=WOOD_RAMP[0], ec="none"))
    ax.plot([X_BR, X_BR], [Y_CH1 - 12, Y_CH2 + 12], color=INK, lw=3.0, solid_capstyle="butt")
    ax.text(X_BR + 10, 0.5 * (Y_CH2 + LY) + 2, T("橋(捕捉セル 4 つ)", "bridge (4 capture cells)"), fontsize=9.5, color=INK, va="center")
    ax.text(0.5 * (xs1 + xs2), Y_CH1 - 12, T("流木の供給の代用(立木 180 m³)", "stand-in for the wood supply (180 m³ of stock)"),
            ha="center", va="bottom", fontsize=9.5, color=INK)
    ax.text(30, 60, T("氾濫原(住宅地を想定した平地。河床 + 3.5 m)", "floodplain (flat land standing for a residential area; bed + 3.5 m)"),
            fontsize=10, color=INK2, va="center")
    ax.text(30, 0.5 * (Y_CH2 + LY), T("台地(河床 + 7 m)", "terrace (bed + 7 m)"), fontsize=10, color=INK2, va="center")
    ax.annotate("", (LX - 25, 0.5 * (Y_CH1 + Y_CH2)), xytext=(LX - 95, 0.5 * (Y_CH1 + Y_CH2)),
                arrowprops=dict(arrowstyle="-|>", color=C_JAM, lw=1.6))
    ax.text(X_BR + 140, 0.5 * (Y_CH1 + Y_CH2), T("河道(幅 20 m)", "channel (20 m wide)"), ha="left", va="center", fontsize=9.5, color=INK)
    for k, (i, j) in enumerate(PROBES, 1):
        x, y = (i - 0.5) * DX, (j - 0.5) * DX
        ax.plot([x], [y], "o", ms=8, mfc=INK2, mec=SURF, mew=1.5, zorder=5)
        ax.text(x - 9 if k == 1 else x + 9, y - 10, str(k), fontsize=9, color=INK, va="center", ha="right" if k == 1 else "left")
    ax.plot([X_BR, X_BR], [0, Y_CH1 - 14], color=MUTED, lw=1.0)
    ax.text(X_BR - 8, 14, T("測線 2(橋を迂回する流量)", "transect 2 (discharge bypassing the bridge)"), fontsize=9, color=INK2, va="center", ha="right")
    ax.set_xlim(0, LX)
    ax.set_ylim(LY, 0)
    ax.set_aspect("equal")
    ax.set_xlabel(T("x (m)  西 → 東(下流)", "x (m)  west → east (downstream)"))
    ax.set_ylabel(T("y (m)  北が上", "y (m)  north at the top"))
    ax.set_title(T("(a) 配置(丸はプローブ 1〜5)", "(a) Layout (dots are probes 1–5)"))

    ax = fig.add_subplot(gs[1])
    t, q = inflow_series()
    ax.plot(t, q, color=INK2)
    ax.set_xlim(0, t[-1])
    ax.set_ylim(0, 160)
    ax.set_xlabel(T("時刻 (分)", "time (min)"))
    ax.set_ylabel(T("流入量 (m³/s)", "inflow (m³/s)"))
    ax.set_title(T("(b) 出水の波形(西端の河道から流入)", "(b) Flood hydrograph (inflow at the west end of the channel)"))
    ax.annotate(T("ピーク %.1f m³/s(等流水深 %.2f m。満杯は 3.5 m)", "peak %.1f m³/s (uniform depth %.2f m; bankfull 3.5 m)")
                % (Q_PEAK, uniform_depth(Q_PEAK)), (70, Q_PEAK), xytext=(70, Q_PEAK + 9), ha="center", fontsize=9.5, color=INK)
    ax.annotate(T("平水 %.0f m³/s(%.2f m)", "base flow %.0f m³/s (%.2f m)") % (Q_BASE, uniform_depth(Q_BASE)),
                (5, Q_BASE), xytext=(3, Q_BASE - 14), fontsize=9.5, color=INK)
    fig.savefig(f"{FIGDIR}/setup.png", dpi=110)
    plt.close(fig)


def series():
    fig, axs = plt.subplots(3, 1, figsize=(9.5, 9.2), sharex=True)
    fig.subplots_adjust(left=0.09, right=0.84, top=0.95, bottom=0.07, hspace=0.24)
    tmax = 150.0

    ax = axs[0]
    tl, a = ledger("ledger")
    tj, b = ledger("jam")
    ax.plot(tl, a["vol_jam_m3"], color=C_LEDGER, label=T("台帳だけ(流れに作用させない)", "ledger only (no effect on the flow)"))
    ax.plot(tj, b["vol_jam_m3"], color=C_JAM, label=T("集積の抵抗あり", "with the drag of the jam"))
    ax.axhline(b["vol_stock_m3"][0], color=AXIS, lw=1.0)
    ax.text(2, b["vol_stock_m3"][0] + 4, T("供給した流木 %.0f m³", "wood supplied %.0f m³") % b["vol_stock_m3"][0], fontsize=9, color=INK2)
    ax.text(tmax + 2, a["vol_jam_m3"][-1], T("台帳だけ", "ledger only"), va="center", fontsize=9.5, color=INK2)
    ax.text(tmax + 2, b["vol_jam_m3"][-1], T("抵抗あり", "with drag"), va="center", fontsize=9.5, color=INK2)
    ax.set_ylim(0, 205)
    ax.set_ylabel(T("材積 (m³)", "volume (m³)"))
    ax.set_title(T("(a) 橋に集積した流木の実材積", "(a) Solid volume of the wood jammed at the bridge"))
    ax.legend(loc="center right")

    ax = axs[1]
    tn, hn, _ = probe("nowood", 1)
    tj, hj, _ = probe("jam", 1)
    ax.axhline(D_BANK, color=AXIS, lw=1.0)
    ax.text(2, D_BANK + 0.08, T("氾濫原の高さ(河床 + 3.5 m)", "floodplain level (bed + 3.5 m)"), fontsize=9, color=INK2)
    ax.plot(tn, hn, color=C_NOWOOD, label=T("流木なし(台帳だけのケースも同じ)", "no driftwood (the ledger-only case is identical)"))
    ax.plot(tj, hj, color=C_JAM, label=T("集積の抵抗あり", "with the drag of the jam"))
    ax.text(tmax + 2, hn[-1], T("流木なし", "no driftwood"), va="center", fontsize=9.5, color=INK2)
    ax.text(tmax + 2, hj[-1], T("抵抗あり", "with drag"), va="center", fontsize=9.5, color=INK2)
    ax.set_ylim(0, max(5.0, np.ceil(hj.max() * 2) / 2 + 0.5))
    ax.set_ylabel(T("水深 (m)", "depth (m)"))
    ax.set_title(T("(b) 橋の 10 m 上流の河道の水深(プローブ 1)", "(b) Depth in the channel 10 m upstream of the bridge (probe 1)"))
    ax.legend(loc="lower right")

    ax = axs[2]
    tn, qn = flux("nowood", 1)
    tj, qc = flux("jam", 1)
    _, qb = flux("jam", 2)
    ax.plot(tn, qn, color=C_NOWOOD, label=T("流木なし: 河道(橋の下)", "no driftwood: channel (under the bridge)"))
    ax.plot(tj, qc, color=C_JAM, label=T("抵抗あり: 河道(橋の下)", "with drag: channel (under the bridge)"))
    ax.plot(tj, qb, color=C_BYPASS, label=T("抵抗あり: 氾濫原(橋を迂回)", "with drag: floodplain (bypassing the bridge)"))
    k = int(np.argmin(np.abs(tj - 85.0)))
    ax.annotate(T("河道", "channel"), (tj[k], qc[k]), xytext=(tj[k], qc[k] + 9), ha="center", fontsize=9.5, color=INK2)
    ax.annotate(T("氾濫原(迂回)", "floodplain (bypass)"), (tj[k], qb[k]), xytext=(tj[k], qb[k] - 11), ha="center", fontsize=9.5, color=INK2)
    ax.set_ylim(0, 160)
    ax.set_xlim(0, tmax)
    ax.set_xlabel(T("時刻 (分)", "time (min)"))
    ax.set_ylabel(T("流量 (m³/s)", "discharge (m³/s)"))
    ax.set_title(T("(c) 橋の断面を通る流量(測線 1・2)", "(c) Discharge through the bridge section (transects 1 and 2)"))
    ax.legend(loc="upper right", bbox_to_anchor=(1.19, 1.0))
    fig.savefig(f"{FIGDIR}/series.png", dpi=110)
    plt.close(fig)


def _zones(ax):
    ax.grid(False)
    ax.add_patch(Rectangle((0, 0), LX, Y_CH1, fc=C_FP, ec="none", zorder=0))
    ax.add_patch(Rectangle((0, Y_CH1), LX, Y_CH2 - Y_CH1, fc=C_FP, ec="none", zorder=0))
    ax.add_patch(Rectangle((0, Y_CH2), LX, LY - Y_CH2, fc=C_TER, ec="none", zorder=0))
    ax.plot([X_BR, X_BR], [Y_CH1 - 10, Y_CH2 + 10], color=INK, lw=2.5, solid_capstyle="butt", zorder=6)
    ax.set_xlim(0, LX)
    ax.set_ylim(LY, 0)
    ax.set_aspect("equal")
    ax.set_ylabel("y (m)")


def _classed(ax, field, bounds, ramp, label):
    cmap = ListedColormap(ramp)
    cmap.set_under((0, 0, 0, 0))
    norm = BoundaryNorm(bounds + [1.0e9], cmap.N)       # 最後の階級は上限なし
    im = ax.imshow(np.ma.masked_less(field, bounds[0]), extent=EXT, cmap=cmap, norm=norm, interpolation="nearest", zorder=2)
    cax = ax.inset_axes([1.015, 0.0, 0.016, 1.0])
    cb = plt.colorbar(im, cax=cax, ticks=bounds)
    cb.ax.set_yticklabels([("%g" % b) for b in bounds])
    cb.ax.tick_params(length=0, labelsize=9, labelcolor=INK2)
    cb.set_label(label, color=INK2, fontsize=9.5)
    cb.outline.set_visible(False)
    return im


def maps():
    fig = plt.figure(figsize=(11, 9.0))
    gs = fig.add_gridspec(3, 1, height_ratios=[1.3, 1.0, 1.0], hspace=0.30, left=0.07, right=0.90, top=0.96, bottom=0.06)

    ax = fig.add_subplot(gs[0])
    x = (np.arange(NX) + 0.5) * DX
    bed = Z0 - S * x
    jc = J_CH1                                  # 河道の北から 2 行目(0 始まりの添字で J_CH1)
    ax.plot(x, bed, color=INK2, lw=1.2)
    ax.plot(x, bed + D_BANK, color=AXIS, lw=1.0)
    hn = frame_at("nowood", "H", T_PROFILE)[jc]
    hj = frame_at("jam", "H", T_PROFILE)[jc]
    ax.plot(x, bed + hn, color=C_NOWOOD, label=T("流木なし", "no driftwood"))
    ax.plot(x, bed + hj, color=C_JAM, label=T("集積の抵抗あり", "with the drag of the jam"))
    ax.axvline(X_BR, color=INK, lw=1.5)
    ax.text(X_BR + 8, bed[0] + D_BANK + 1.0, T("橋", "bridge"), fontsize=9.5, color=INK, va="top")
    ax.text(40, bed[7] - 0.35, T("河床", "bed"), fontsize=9, color=INK2, va="top")
    ax.text(40, bed[7] + D_BANK + 0.12, T("氾濫原の高さ", "floodplain level"), fontsize=9, color=INK2, va="bottom")
    ax.set_xlim(0, LX)
    ax.set_ylim(bed[-1] - 0.6, bed[0] + D_BANK + 1.3)
    ax.set_xlabel("x (m)")
    ax.set_ylabel(T("標高 (m)", "elevation (m)"))
    ax.set_title(T("(a) 河道の縦断の水面形(%d 分。ピークの流量が続いている間)", "(a) Water surface along the channel (%d min, during the peak discharge)") % T_PROFILE)
    ax.legend(loc="lower left", ncols=2)

    ax = fig.add_subplot(gs[1])
    _zones(ax)
    hmax = rd("result_jam/H9999.txt")
    _classed(ax, hmax, [0.01, 0.1, 0.3, 1.0, 2.0], DEPTH_RAMP, T("最大浸水深 (m)", "maximum depth (m)"))
    ax.annotate(T("河岸沿いの薄い筋と上流端のにじみは計算上のもの(本文の「精度の限界」)",
                  "the thin strip along the bank and the patch at the upstream end are numerical (see \"Limits of accuracy\")"),
                (300, Y_CH1 - 12), xytext=(60, 110), fontsize=9, color=INK2, va="center",
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8), zorder=7)
    ax.set_title(T("(b) 最大浸水深(集積の抵抗あり。流木なしでは河道の外は浸水しない)",
                   "(b) Maximum depth with the drag of the jam (without driftwood only the channel is wet)"))

    ax = fig.add_subplot(gs[2])
    _zones(ax)
    ax.add_patch(Rectangle((0, Y_CH1), LX, Y_CH2 - Y_CH1, fc=C_CH, ec="none", zorder=1))
    wood = rd("result_jam/Wd9999.txt")
    _classed(ax, wood, [0.0003, 0.001, 0.003, 0.01, 0.03], WOOD_RAMP, T("流木 (m³/m²)", "driftwood (m³/m²)"))
    m = metrics("jam")
    ax.annotate(T("橋に集積 %.0f m³", "jammed at the bridge: %.0f m³") % m["jam"], (X_BR, Y_CH2 + 6), xytext=(X_BR - 20, LY - 14),
                ha="right", va="center", fontsize=9.5, color=INK, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    ax.set_xlabel("x (m)")
    ax.set_title(T("(c) 流木が通った所と残った所(流動と堆積の和の期間最大。橋の集積は含まない)",
                   "(c) Where driftwood passed and stayed (period maximum of moving + deposited wood, without the jam)"))
    fig.savefig(f"{FIGDIR}/maps.png", dpi=110)
    plt.close(fig)


def jam_rise(vs, phi, cd=1.0, d=0.3, g=9.8):
    """集積の実材積 vs (m3) による堰上げ (m)。ピークの流量の全量が橋の下を通り、あふれないとした場合。
    漸変流の式 dh/dx = [S − n²q²/h^(10/3) − κ0·min(w/h, φ)·q²/(g h²)] / (1 − q²/(g h³)) を、集積のセルの
    両側の辺(長さ 2Δx。集積量は辺ごとに半分)について、下流の等流水深から上流へ積分する"""
    width = (J_CH2 - J_CH1 + 1) * DX
    q = Q_PEAK / width
    kap = 2.0 * cd / (np.pi * d * (1.0 - phi) ** 3)
    we = 0.5 * vs / (width * DX)

    def rhs(h):
        sf = N_CH ** 2 * q * q / h ** (10.0 / 3.0)
        sj = kap * min(we / h, phi) * q * q / (g * h * h)
        return (S - sf - sj) / (1.0 - q * q / (g * h ** 3))
    h0 = uniform_depth(Q_PEAK)
    h, n = h0, 400
    dx = -2.0 * DX / n
    for _ in range(n):
        k1 = rhs(h); k2 = rhs(h + 0.5 * dx * k1); k3 = rhs(h + 0.5 * dx * k2); k4 = rhs(h + dx * k3)
        h += dx * (k1 + 2.0 * k2 + 2.0 * k3 + k4) / 6.0
    return h - h0


def laws():
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    fig.subplots_adjust(left=0.09, right=0.80, top=0.91, bottom=0.12)
    vs = np.linspace(0.0, 200.0, 81)
    for phi, col in PHI_RAMP.items():
        r = [jam_rise(v, phi) for v in vs]
        ax.plot(vs, r, color=col, label="φ = %.1f" % phi)
        ax.text(203, r[-1], "φ = %.1f" % phi, va="center", fontsize=9.5, color=INK2)
    lim = D_BANK - uniform_depth(Q_PEAK)
    ax.axhline(lim, color=MUTED, lw=1.0)
    ax.text(198, lim + 0.06, T("この上昇で氾濫原の高さに届く(%.1f m)", "the rise that reaches the floodplain level (%.1f m)") % lim,
            ha="right", fontsize=9, color=INK2)
    done = False
    for c, phi in (("e01", 0.3), ("e03", 0.3), ("slow", 0.3), ("jam", 0.3), ("loose", 0.2), ("dense", 0.4)):
        if not have(c):
            continue
        m = metrics(c)
        ax.plot([m["jam"]], [m["rise"]], "o", ms=9, mfc=PHI_RAMP[phi], mec=SURF, mew=2.0, zorder=5,
                label=None if done else T("計算(氾濫原へあふれる)", "simulation (with overflow onto the floodplain)"))
        done = True
    ax.set_xlim(0, 200)
    ax.set_ylim(0, 4.5)
    ax.set_xlabel(T("橋に集積した流木の実材積 (m³)(河道の幅 20 m)", "solid volume of the wood jammed at the bridge (m³) (channel 20 m wide)"))
    ax.set_ylabel(T("橋の上流の水位の上昇 (m)", "rise of the level upstream of the bridge (m)"))
    ax.set_title(T("集積の量と堰上げ(線: あふれないとした場合の式の値。丸: 計算)",
                   "Jam volume and backwater (lines: formula without overflow; dots: simulation)"))
    ax.legend(loc="upper left", title=T("集積の充填率", "packing ratio of the jam"))
    fig.savefig(f"{FIGDIR}/laws.png", dpi=110)
    plt.close(fig)


def sens():
    cases = [(c, lab) for c, lab in SENS if have(c)]
    ms = [metrics(c) for c, _ in cases]
    items = [("jam", T("橋に集積した流木 (m³)\n", "wood jammed\nat the bridge (m³)"), "%.0f"),
             ("rise", T("橋の上流の水位の上昇の最大 (m)\n(縦線: 氾濫原に届く上昇)", "maximum rise upstream (m)\n(line: reaches the floodplain)"), "%.2f"),
             ("qby", T("橋を迂回する流量の最大 (m³/s)\n", "peak discharge\nbypassing the bridge (m³/s)"), "%.0f"),
             ("area", T("氾濫原の浸水面積 (ha)\n(0.1 m 以上)", "flooded floodplain area (ha)\n(depth ≥ 0.1 m)"), "%.1f")]
    fig, axs = plt.subplots(1, 4, figsize=(13, 3.7), sharey=True)
    fig.subplots_adjust(left=0.235, right=0.985, top=0.83, bottom=0.10, wspace=0.16)
    y = np.arange(len(cases))[::-1]
    for ax, (key, title, fmt) in zip(axs, items):
        v = [m[key] for m in ms]
        ax.barh(y, v, height=0.42, color=C_JAM, ec="none")
        ax.grid(axis="y", visible=False)
        ax.set_xlim(0, max(v) * 1.22 if max(v) > 0 else 1)
        for yy, vv in zip(y, v):
            ax.text(vv + max(v) * 0.02, yy, fmt % vv, va="center", fontsize=9.5, color=INK)
        ax.set_title(title, fontsize=9.5 if EN else 10)
        ax.set_yticks(y)
        ax.set_yticklabels([lab for _, lab in cases], fontsize=9.5)
        ax.tick_params(axis="y", length=0)
        if key == "rise":
            lim = D_BANK - uniform_depth(Q_PEAK)
            ax.axvline(lim, color=MUTED, lw=1.0)
    fig.savefig(f"{FIGDIR}/sens.png", dpi=110)
    plt.close(fig)


def table():
    """README 用の数表(Markdown)"""
    names = {"nowood": T("流木なし", "no driftwood"), "ledger": T("台帳だけ", "ledger only"),
             "jam": T("集積の抵抗あり(基本)", "with the drag of the jam (base)"),
             "slow": T("10 層で全量", "all at 10 layers"),
             "e03": T("捕捉率 0.3 のまま", "capture ratio stays 0.3"), "e01": T("捕捉率 0.1 のまま", "capture ratio stays 0.1"),
             "loose": T("すき間の多い集積(φ = 0.2)", "loose jam (φ = 0.2)"), "dense": T("詰まった集積(φ = 0.4)", "dense jam (φ = 0.4)")}
    cases = [c for c in names if have(c)]
    ms = {c: metrics(c) for c in cases}
    print(T("| ケース | 橋に集積 (m³) | 橋の 10 m 上流の最大水深 (m) | 迂回が始まる時刻 | 迂回流量の最大 (m³/s) | 氾濫原の浸水面積 (ha) | 氾濫原の最大浸水深 (m) |",
            "| Case | Jammed at the bridge (m³) | Max depth 10 m upstream of the bridge (m) | Bypass starts | Peak bypass discharge (m³/s) | Flooded floodplain area (ha) | Max depth on the floodplain (m) |"))
    print("|---|---:|---:|---:|---:|---:|---:|")
    for c in cases:
        m = ms[c]
        print("| %s (`%s`) | %s | %.2f | %s | %.0f | %.1f | %.2f |"
              % (names[c], c, ("%.0f" % m["jam"]) if "jam" in m else "—", m["hmax"],
                 ("%d" % int(m["t_by"] + 0.5) + T(" 分", " min")) if m["t_by"] is not None else "—", m["qby"], m["area"], m["hfp"]))
    print()
    print(T("| ケース | 流木になった量 (m³) | 橋に集積 (m³) | 氾濫原に堆積 (m³) | 領域の外へ (m³) |",
            "| Case | Recruited (m³) | Jammed at the bridge (m³) | Deposited on the floodplain (m³) | Left the domain (m³) |"))
    print("|---|---:|---:|---:|---:|")
    for c in cases:
        m = ms[c]
        if "rec" in m:
            print("| %s (`%s`) | %.0f | %.0f | %.0f | %.0f |" % (names[c], c, m["rec"], m["jam"], m["dep"], m["out"]))


if __name__ == "__main__":
    if "table" in sys.argv[1:]:
        table()
        sys.exit(0)
    setup()
    if all(have(c) for c in ("nowood", "ledger", "jam")):
        series()
        maps()
    if all(have(c) for c, _ in SENS):
        sens()
    laws()
