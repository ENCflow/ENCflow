#!/usr/bin/env python3
# examples/debris_bedrock の図と数表(make_init.py と定数を対で保守)
#   python3 plot_results.py      figs/*.png(日本語)と数表(標準出力)
#   python3 plot_results.py en   en/figs/*.png(英語)
# 最終時刻の分布出力(bil = 単精度)の Ri・Sd・Z と、Screen_<構成>.log の終了時の台帳を読む。
import sys, struct, re
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from make_init import DX, NX, NY, BREAKS, CASES, TT, DTF, CMIX, QPEAK, TEND, SDCOV, zc

EN = len(sys.argv) > 1 and sys.argv[1] == "en"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
OUT = "en/figs/" if EN else "figs/"
LAM = 0.4
KEND = int(round(TT / DTF))
INK, MUTED, GRID = "#1f1e1c", "#52514e", "#e4e2dc"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
RAMP = ("#86b6ef", "#2a78d6", "#104281")
REACH = [(BREAKS[k][0], BREAKS[k + 1][0] if k + 1 < len(BREAKS) else NY * DX, BREAKS[k][1])
         for k in range(len(BREAKS))]
SPOS = [(j - 0.5) * DX for j in range(1, NY + 1)]


def T(ja, en):
    return en if EN else ja


def bil(case, name, k):
    data = open("result_%s/%s%04d.bil" % (case, name, k), "rb").read()
    a = struct.unpack("<%df" % (NX * NY), data)
    return [a[j * NX:(j + 1) * NX] for j in range(NY)]


def rowmean(a):
    return [sum(r) / NX for r in a]


def ledger(case):
    """終了時の台帳(土石流の項 / 流水の剥離)のかさ体積 (m3)"""
    pats = (r"rock erosion by debris flows: eroded\s+(\S+) m3", r"rock incision: plucked\s+(\S+) m3")
    v = None
    for line in open("Screen_%s.log" % case, encoding="utf-8", errors="replace"):
        for p in pats:
            m = re.search(p, line)
            if m:
                v = float(m.group(1))
    return v


def reach_means(prof):
    out = []
    for a, b, s in REACH:
        sel = [v for x, v in zip(SPOS, prof) if a <= x < b]
        out.append(sum(sel) / len(sel))
    return out


def style(ax):
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    for a, b, s in REACH:
        ax.axvline(a, color=GRID, lw=1, zorder=0)


def fig_erosion(ri, sd):
    fig, axs = plt.subplots(4, 1, figsize=(7.4, 9.6), sharex=True,
                            gridspec_kw={"height_ratios": [0.9, 1.3, 1.3, 1.0]})
    ax = axs[0]
    ax.plot(SPOS, [zc(j) for j in range(1, NY + 1)], color=INK, lw=1.5)
    for a, b, s in REACH:
        ax.text((a + b) / 2, 86, "S = %.2f" % s, ha="center", va="top", color=MUTED, fontsize=8)
    ax.set_ylabel(T("河床標高 (m)", "bed elevation (m)"))
    ax.set_ylim(0, 88)
    style(ax)
    ax = axs[1]
    for c, col, lab in (("T_b", BLUE, T("高橋・中川則", "Takahashi–Nakagawa")),
                        ("C_b", ORANGE, T("クーロン + Manning", "Coulomb + Manning")),
                        ("W", AQUA, T("同じ流量の清水の出水", "clear-water flood, same discharge"))):
        ax.plot(SPOS, [100 * v for v in ri[c]], color=col, lw=2, label=lab)
    ax.set_ylabel(T("1 回の岩盤侵食 (cm)", "rock erosion per event (cm)"))
    ax.set_title(T("裸岩", "bare rock"), loc="left", fontsize=9, color=INK)
    ax.legend(loc="upper right", frameon=False, fontsize=8)
    style(ax)
    ax = axs[2]
    for c, col, ls, lab in (("T_b", BLUE, "-", T("高橋・中川則・裸岩", "Takahashi–Nakagawa, bare")),
                            ("T_c", BLUE, "--", T("高橋・中川則・堆積層 0.3 m", "Takahashi–Nakagawa, 0.3 m deposit")),
                            ("C_b", ORANGE, "-", T("クーロン + Manning・裸岩", "Coulomb + Manning, bare")),
                            ("C_c", ORANGE, "--", T("クーロン + Manning・堆積層 0.3 m", "Coulomb + Manning, 0.3 m deposit"))):
        ax.plot(SPOS, [100 * v for v in ri[c]], color=col, lw=2, ls=ls, label=lab)
    ax.set_ylabel(T("1 回の岩盤侵食 (cm)", "rock erosion per event (cm)"))
    ax.set_title(T("被覆の効き", "effect of the cover"), loc="left", fontsize=9, color=INK)
    ax.legend(loc="upper right", frameon=False, fontsize=8)
    style(ax)
    ax = axs[3]
    for c, col, ls in (("T_b", BLUE, "-"), ("T_c", BLUE, "--"), ("C_b", ORANGE, "-"), ("C_c", ORANGE, "--")):
        ax.plot(SPOS, [100 * v for v in sd[c]], color=col, lw=2, ls=ls)
    ax.axhline(100 * SDCOV, color=MUTED, lw=0.8, ls=":")
    ax.text(395, 100 * SDCOV + 3, T("初期の堆積層", "initial deposit"), ha="right", va="bottom",
            color=MUTED, fontsize=8)
    ax.set_ylabel(T("終了時の可動層 (cm)", "mobile layer at the end (cm)"))
    ax.set_xlabel(T("谷頭からの距離 (m)", "distance from the head (m)"))
    style(ax)
    fig.tight_layout()
    fig.savefig(OUT + "erosion.png", dpi=150)
    plt.close(fig)


def fig_threshold(ri):
    fig, ax = plt.subplots(figsize=(7.4, 3.2))
    for c, col, lab in (("T_b05", RAMP[0], "τ_cd = 0.5 kPa"), ("T_b", RAMP[1], "τ_cd = 1 kPa"),
                        ("T_b20", RAMP[2], "τ_cd = 2 kPa")):
        ax.plot(SPOS, [100 * v for v in ri[c]], color=col, lw=2, label=lab)
    ax.set_ylabel(T("1 回の岩盤侵食 (cm)", "rock erosion per event (cm)"))
    ax.set_xlabel(T("谷頭からの距離 (m)", "distance from the head (m)"))
    ax.set_title(T("閾値の効き(高橋・中川則・裸岩)", "effect of the threshold (Takahashi–Nakagawa, bare)"),
                 loc="left", fontsize=9, color=INK)
    ax.legend(loc="upper right", frameon=False, fontsize=8)
    style(ax)
    fig.tight_layout()
    fig.savefig(OUT + "threshold.png", dpi=150)
    plt.close(fig)


def fig_cover():
    """堆積層ありの構成の、急な区間の 3 地点の可動層と岩盤侵食の推移"""
    rows = [10, 30, 50]                        # 谷頭から 21・61・101 m のセル行(0 始まり)
    kmax = int(round(150.0 / DTF))
    tt = [k * DTF for k in range(kmax + 1)]
    fig, axs = plt.subplots(2, 2, figsize=(7.4, 5.2), sharex=True, sharey="row")
    for col, (c, ttl) in enumerate((("T_c", T("高橋・中川則・堆積層 0.3 m", "Takahashi–Nakagawa, 0.3 m deposit")),
                                    ("C_c", T("クーロン + Manning・堆積層 0.3 m", "Coulomb + Manning, 0.3 m deposit")))):
        sdk = [rowmean(bil(c, "Sd", k)) for k in range(kmax + 1)]
        rik = [rowmean(bil(c, "Ri", k)) for k in range(kmax + 1)]
        for r, colr in zip(rows, RAMP):
            lab = T("谷頭から %.0f m", "%.0f m from the head") % SPOS[r]
            axs[0][col].plot(tt, [100 * a[r] for a in sdk], color=colr, lw=2, marker="o", ms=3, label=lab)
            axs[1][col].plot(tt, [100 * a[r] for a in rik], color=colr, lw=2, marker="o", ms=3, label=lab)
        axs[0][col].set_title(ttl, loc="left", fontsize=9, color=INK)
        axs[1][col].set_xlabel(T("時刻 (s)", "time (s)"))
        for ax in (axs[0][col], axs[1][col]):
            for sp in ("top", "right"):
                ax.spines[sp].set_visible(False)
            ax.grid(axis="y", color=GRID, lw=0.6)
            ax.set_axisbelow(True)
    axs[0][0].set_ylabel(T("可動層 (cm)", "mobile layer (cm)"))
    axs[1][0].set_ylabel(T("岩盤侵食 (cm)", "rock erosion (cm)"))
    axs[0][1].legend(loc="upper right", frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT + "cover.png", dpi=150)
    plt.close(fig)


def main():
    ri = {c: rowmean(bil(c, "Ri", KEND)) for c in CASES}
    sd = {c: rowmean(bil(c, "Sd", KEND)) for c in CASES}
    fig_erosion(ri, sd)
    fig_threshold(ri)
    fig_cover()
    if EN:
        return
    vin = 0.5 * TEND * QPEAK * CMIX            # 流入した固体 (m3)
    print("区間(谷頭から)               " + "  ".join("%5.0f-%3.0f m" % (a, b) for a, b, s in REACH))
    print("勾配                         " + "  ".join("   S = %.2f" % s for a, b, s in REACH))
    for c in CASES:
        rm = reach_means(ri[c])
        v = ledger(c)
        print("%-6s 1 回の岩盤侵食 (cm)   " % c + "  ".join("%11.3f" % (100 * x) for x in rm)
              + "   台帳 %8.3f m3(かさ)" % v)
    for c in ("T_b", "T_c", "C_b", "C_c"):
        v = ledger(c)
        print("%-6s 岩盤起源の固体 %.2f m3 = 流入した固体 %.0f m3 の %.1f %%"
              % (c, (1 - LAM) * v, vin, 100 * (1 - LAM) * v / vin))
    for c in ("T_c", "C_c"):
        rm = reach_means(sd[c])
        print("%-6s 終了時の可動層 (cm)   " % c + "  ".join("%11.1f" % (100 * x) for x in rm))
    for c in ("T_b", "C_b"):
        rm = reach_means(sd[c])
        print("%-6s 終了時の可動層 (cm)   " % c + "  ".join("%11.1f" % (100 * x) for x in rm))


if __name__ == "__main__":
    main()
