#!/usr/bin/env python3
# examples/debris_bedrock 後半(長期)の図と数表(make_long.py と定数を対で保守)
#   python3 plot_long.py      figs/long_*.png(日本語)と数表(標準出力)
#   python3 plot_long.py en   en/figs/long_*.png(英語)
# long/<構成>/track.csv(Run_chain.sh が各段の後に書く。台帳の表示とセルごとの z・Ri・sd)を読む。
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from make_long import (NX, NY, NYR, DY, SLOPES, TRS, D50S, TR_INF, NSKIP, U, UPLIFT_RUNS, TR_U, D50_U, MID, CMIX,
                       name_fixed, zrow)

EN = len(sys.argv) > 1 and sys.argv[1] == "en"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
OUT = "en/figs/" if EN else "figs/"
INK, MUTED, GRID = "#1f1e1c", "#52514e", "#e4e2dc"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
RAMP = ("#86b6ef", "#2a78d6", "#104281")          # T_r = 100・30・10 年(頻度が上がるほど濃い)
SDB, TANPHI = 1.65, 0.70021                      # 土石流の平衡勾配(高橋・中川の平衡濃度 = 流入の濃度)
S_EQ = SDB * CMIX * TANPHI / (1.0 + SDB * CMIX)
MIDR = [j for j in range(NY) if MID[0] <= (j + 0.5) * DY < MID[1]]     # 中央区間の行
LOW = 60.0                                       # 下流区間の平均勾配: 基準面(水路の最後の行)から LOW m まで
EDGE = (0.0, 0.0)                                # 谷頭と基準面の近くの除く幅 (m)。0 = 水路全体(流向の勾配と流入面の
                                                 # 床を直した後は 2 セル周期の段差が育たない。developer.md §88.23〜88.26)
YLIM = (-2.0, 4.2)                               # 図 1 の縦軸(粒径 0.4 m の緩い勾配の堆積は範囲外)
SNAP = (1500, 3000, 4530)                        # 隆起ありの縦断を比べる時刻 (年)


def T(ja, en):
    return en if EN else ja


def load(name):
    """track.csv の各行を辞書に(段の順)。z・ri・sd は (行 = 谷頭から, 列) の配列"""
    n, rows = NX * NY, []
    for line in open("long/%s/track.csv" % name):
        v = line.strip().split(",")
        f = np.array([float(x) for x in v[2:]])
        rows.append({"cycle": int(v[0]), "stage": v[1], "sumri": f[0], "plucked": f[1], "eroded": f[2],
                     "deposited": f[3], "z": f[4:4 + n].reshape(NY, NX), "ri": f[4 + n:4 + 2 * n].reshape(NY, NX),
                     "sd": f[4 + 2 * n:4 + 3 * n].reshape(NY, NX)})
    return rows


def floods(rows):
    return [r for r in rows if r["stage"] in ("flood0", "flood")]


def mid(a):
    """中央区間の平均"""
    return a[MIDR].mean()


def rates(name, tr):
    """固定勾配の連鎖: 地表の低下速度(サイクル NSKIP+1 以降の平均。mm/年)と、最初の出水・土石流の足し合わせ"""
    rows = load(name)
    fl = floods(rows)
    keep = range(NSKIP, len(fl) - 1)                  # fl[k] → fl[k+1] がサイクル k+1
    per = [1000.0 * (mid(fl[k]["z"]) - mid(fl[k + 1]["z"])) / tr for k in range(len(fl) - 1)]
    deb = [r for r in rows if r["stage"] == "debris"]
    if deb:
        b1 = mid(deb[0]["ri"]) - mid(fl[0]["ri"])     # 1 回目の土石流(出水の後の裸岩)
        esup = 1000.0 * (mid(fl[0]["ri"]) + b1) / tr
        bd = 100.0 * sum(mid(deb[k]["ri"]) - mid(fl[k]["ri"]) for k in keep) / len(keep)   # 1 回 (cm)
    else:
        esup, bd = 1000.0 * mid(fl[0]["ri"]) / tr, 0.0
    return {"e": sum(per[k] for k in keep) / len(keep), "per": per, "esup": esup, "bd": bd,
            "sd": 100.0 * sum(mid(fl[k + 1]["sd"]) for k in keep) / len(keep), "rows": rows}


def ledger_check(rows):
    """各段の ΣΔRi·A と終了時の表示(剥離・土石流の侵食)の最大相対差"""
    worst, prev = 0.0, 0.0
    for r in rows:
        d = r["sumri"] - prev
        prev = r["sumri"]
        lg = r["plucked"] if r["stage"] in ("flood0", "flood") else r["eroded"]
        if lg > 0.0:
            worst = max(worst, abs(d / lg - 1.0))
    return worst


def crossing(ss, es, target):
    """E(S) = target の勾配(折れ線で補間)。範囲外は None"""
    for k in range(len(ss) - 1):
        if (es[k] - target) * (es[k + 1] - target) <= 0.0 and es[k + 1] != es[k]:
            return ss[k] + (ss[k + 1] - ss[k]) * (target - es[k]) / (es[k + 1] - es[k])
    return None


def fmt(v):
    return "None" if v is None else "%.3f" % v


def slopes(z):
    """水路(落ち口を除く)の隣り合う行の勾配の 10 m(5 区間)の移動平均。位置は谷頭からの距離"""
    p = z[:NYR].mean(axis=1)
    sl = (p[:-1] - p[1:]) / DY
    return np.arange(1, NYR) * DY, np.array([sl[max(0, j - 2):j + 3].mean() for j in range(NYR - 1)])


def low_slope(z):
    """基準面から LOW m 上流までの平均勾配(両端の標高の差)"""
    p = z[:NYR].mean(axis=1)
    k = int(round(LOW / DY))
    return float((p[NYR - 1 - k] - p[NYR - 1]) / LOW)


def inner(x):
    """谷頭と基準面の近く(EDGE)を除く位置"""
    return (x >= EDGE[0]) & (x <= NYR * DY - EDGE[1])


def model_1d(s0, es, times, dt=1.0):
    """1 次元の予測: z_t = U − E(S)(E は固定勾配の交互計算の折れ線、範囲外は端の値)。水路の最後の行
    (基準面)は固定。勾配は下流側の差分(変化は上流へ伝わる)"""
    z = np.array([zrow(s0, j) for j in range(1, NYR + 1)])
    out, t = {}, 0.0
    for tk in sorted(times):
        while t < tk - 1e-9:
            s = (z[:-1] - z[1:]) / DY
            z[:-1] += dt * (U - np.interp(s, SLOPES, es)) / 1000.0
            t += dt
        out[tk] = z.reshape(NYR, 1).copy()
    return out


def style(ax):
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.set_axisbelow(True)


def main():
    res, worst = {}, 0.0
    for d50 in D50S:
        for tr in TRS + [None]:
            for s in SLOPES:
                r = rates(name_fixed(d50, s, tr), TR_INF if tr is None else tr)
                worst = max(worst, ledger_check(r["rows"]))
                res[(d50, tr, s)] = r
    sstar = {}
    for d50 in D50S:
        for tr in TRS + [None]:
            for key in ("e", "esup"):
                sstar[(d50, tr, key)] = crossing(SLOPES, [res[(d50, tr, s)][key] for s in SLOPES], U)

    # --- 図 1: 固定勾配の長期の低下速度 ---
    fig, axs = plt.subplots(1, 2, figsize=(7.6, 3.8), sharey=True)
    for ax, d50 in zip(axs, D50S):
        ax.axhline(U, color=MUTED, lw=0.8, ls=":")
        ax.text(SLOPES[-1], U - 0.12, T("隆起 1 mm/年", "uplift 1 mm/yr"), color=MUTED, fontsize=8, va="top",
                ha="right")
        ax.set_ylim(*YLIM)
        ax.plot(SLOPES, [res[(d50, None, s)]["e"] for s in SLOPES], color=MUTED, lw=2, marker="o", ms=3,
                label=T("出水だけ", "floods only"))
        for tr, col in zip(TRS, RAMP):
            ax.plot(SLOPES, [res[(d50, tr, s)]["e"] for s in SLOPES], color=col, lw=2, marker="o", ms=3,
                    label=T("%d 年に 1 回", "once in %d yr") % tr)
            ax.plot(SLOPES, [res[(d50, tr, s)]["esup"] for s in SLOPES], color=col, lw=1, ls="--")
        ax.axvline(S_EQ, color=GRID, lw=1)
        ax.set_title(T("堆積物の粒径 %.1f m", "sediment size %.1f m") % d50, loc="left", fontsize=9, color=INK)
        ax.set_xlabel(T("勾配", "slope"))
        style(ax)
    axs[0].set_ylabel(T("長期の地表の低下速度 (mm/年)", "long-term surface lowering (mm/yr)"))
    axs[0].legend(loc="upper left", frameon=False, fontsize=7.5)
    off = sorted({(s, tr) for tr in TRS for s in SLOPES if res[(0.4, tr, s)]["e"] < YLIM[0]})
    lo = min(res[(0.4, tr, s)]["e"] for s, tr in off)
    hi = max(res[(0.4, tr, s)]["e"] for s, tr in off)
    fig.text(0.01, 0.01, T("粒径 0.4 m の勾配 0.15(全頻度)と 0.20 の一部は堆積で %.0f〜%.1f mm/年(範囲外)",
                           "size 0.4 m at slope 0.15 (all frequencies) and part of 0.20: deposition, %.0f to %.1f mm/yr "
                           "(off scale)") % (lo, hi), ha="left", va="bottom", fontsize=7, color=MUTED)
    fig.text(0.01, 0.045, T("破線: 出水と土石流を別々に計算した足し合わせ", "dashed: sum of floods and debris flows computed separately"),
             ha="left", va="bottom", fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(OUT + "long_rate.png", dpi=150)
    plt.close(fig)

    # --- 図 2: 定常勾配と土石流の頻度 ---
    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    freq = [0.0] + [100.0 / tr for tr in TRS]
    def series(d50, key):
        ys = [sstar[(d50, None, key)]] + [sstar[(d50, tr, key)] for tr in TRS]
        return [(f, y) for f, y in zip(freq, ys) if y is not None]
    for d50, col in zip(D50S, (BLUE, ORANGE)):
        pts = series(d50, "e")
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color=col, lw=2, marker="o", ms=4,
                label=T("交互計算・粒径 %.1f m", "chained runs, size %.1f m") % d50)
    pts = series(0.1, "esup")
    ax.plot([p[0] for p in pts], [p[1] for p in pts], color=MUTED, lw=1, ls="--", marker="x", ms=4,
            label=T("足し合わせ(粒径 0.1 m)", "sum of separate runs (0.1 m)"))
    ax.axhline(S_EQ, color=MUTED, lw=0.8, ls=":")
    ax.text(10.0, S_EQ + 0.004, T("土石流の平衡勾配 %.3f", "debris-flow equilibrium slope %.3f") % S_EQ,
            ha="right", va="bottom", color=MUTED, fontsize=8)
    ax.set_xlabel(T("土石流の頻度(100 年あたりの回数)", "debris-flow frequency (events per 100 yr)"))
    ax.set_ylabel(T("定常勾配", "steady slope"))
    ax.legend(loc="lower left", frameon=False, fontsize=8)
    style(ax)
    fig.tight_layout()
    fig.savefig(OUT + "long_slope.png", dpi=150)
    plt.close(fig)

    # --- 図 3: 粒径 0.4 m の堆積の推移 ---
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    for s, col in zip((0.15, 0.20, 0.25), (ORANGE, BLUE, AQUA)):
        for tr, ls in zip(TRS, (":", "--", "-")):
            fl = floods(res[(0.4, tr, s)]["rows"])
            ax.plot([r["cycle"] for r in fl], [100 * mid(r["sd"]) for r in fl], color=col, lw=1.6, ls=ls,
                    label=T("勾配 %.2f・%d 年に 1 回", "slope %.2f, once in %d yr") % (s, tr))
    ax.set_xlabel(T("サイクル(出水の後)", "cycle (after the flood)"))
    ax.set_ylabel(T("中央区間の可動層 (cm)", "mobile layer, middle reach (cm)"))
    ax.set_title(T("堆積物の粒径 0.4 m", "sediment size 0.4 m"), loc="left", fontsize=9, color=INK)
    ax.set_ylim(top=1.3 * ax.get_ylim()[1])           # 凡例(3 行)を線の上に
    ax.legend(loc="upper left", frameon=False, fontsize=7, ncol=3)
    style(ax)
    fig.tight_layout()
    fig.savefig(OUT + "long_cover.png", dpi=150)
    plt.close(fig)

    # --- 図 4: 隆起ありの確認と 1 次元の予測 ---
    es = [res[(D50_U, TR_U, s)]["e"] for s in SLOPES]
    sst = sstar[(D50_U, TR_U, "e")]
    fig, axs = plt.subplots(1, 2, figsize=(8.4, 3.6), gridspec_kw={"width_ratios": (1.3, 1.0)})
    up = {}
    for (name, s0), col in zip(UPLIFT_RUNS, (ORANGE, BLUE)):
        fl = floods(load(name))
        tyr = [(k + 1) * TR_U for k in range(len(fl))]      # 出水 k の終わり(最初の出水も T_r 年分)
        pred = model_1d(s0, es, tyr)
        for tk, a in zip(SNAP, (0.35, 0.65, 1.0)):
            x, sm = slopes(fl[tyr.index(tk)]["z"])
            axs[0].plot(x, sm, color=col, lw=1.3, alpha=a)
            xp, smp = slopes(pred[tk])
            axs[0].plot(xp, smp, color=MUTED, lw=0.9, ls="--", alpha=a)
        def rms(tk):
            x, sm = slopes(fl[tyr.index(tk)]["z"])
            return float(np.sqrt(np.mean(((sm - slopes(pred[tk])[1])[inner(x)]) ** 2)))
        axs[1].plot(tyr, [low_slope(r["z"]) for r in fl], color=col, lw=1.6,
                    label=T("初期勾配 %.2f", "initial slope %.2f") % s0)
        axs[1].plot(tyr, [low_slope(pred[t]) for t in tyr], color=MUTED, lw=1, ls="--")
        k1 = tyr.index(SNAP[0])
        up[name] = {"s0": s0, "t": tyr[-1], "low": [low_slope(fl[tyr.index(t)]["z"]) for t in SNAP],
                    "lowp": [low_slope(pred[t]) for t in SNAP],
                    "drift": 1000.0 * (mid(fl[k1]["z"]) - mid(fl[0]["z"])) / (tyr[k1] - tyr[0]),
                    "pdrift": U - float(np.interp(s0, SLOPES, es)),
                    "rms": [rms(t) for t in SNAP]}
    if max(EDGE) > 0.0:
        for x0, x1 in ((0.0, EDGE[0]), (NYR * DY - EDGE[1], NYR * DY)):
            axs[0].axvspan(x0, x1, color=GRID, alpha=0.6, lw=0)
        axs[0].text(EDGE[0] / 2, 0.152, T("境界の\n影響", "edge\neffect"), ha="center", fontsize=7, color=MUTED)
        axs[0].text(NYR * DY - EDGE[1] / 2, 0.152, T("境界の\n影響", "edge\neffect"), ha="center", fontsize=7, color=MUTED)
    axs[0].set_ylim(0.145, 0.40)
    axs[0].axhline(sst, color=MUTED, lw=0.8, ls=":")
    axs[0].text(EDGE[0] + 5, sst + 0.002, T("固定勾配の定常勾配 %.3f", "steady slope from fixed slopes %.3f") % sst,
                color=MUTED, fontsize=7.5, va="bottom")
    axs[0].set_xlabel(T("谷頭からの距離 (m)", "distance from the head (m)"))
    axs[0].set_ylabel(T("勾配(10 m の移動平均)", "slope (10 m running mean)"))
    axs[0].set_title(T("%d・%d・%d 年(濃いほど遅い)。破線: 1 次元の予測", "%d, %d, %d yr (darker = later); dashed: 1-D") %
                     SNAP, loc="left", fontsize=8.5, color=INK)
    axs[1].axhline(sst, color=MUTED, lw=0.8, ls=":")
    axs[1].set_xlabel(T("暦の時間 (年)", "calendar time (yr)"))
    axs[1].set_ylabel(T("基準面から %d m までの平均勾配", "mean slope over %d m above the base level") % LOW)
    axs[1].legend(loc="center left", frameon=False, fontsize=7.5)
    axs[1].set_title(T("破線: 1 次元の予測", "dashed: 1-D prediction"), loc="left", fontsize=8.5, color=INK)
    for ax in axs:
        style(ax)
    fig.tight_layout()
    fig.savefig(OUT + "long_uplift.png", dpi=150)
    plt.close(fig)

    if EN:
        return
    print("長期の地表の低下速度 E (mm/年。サイクル %d 以降の平均) と、サイクルごとの最小〜最大、足し合わせ Esup、"
          "1 回の土石流の侵食 Bd (cm)、出水の後の可動層 sd (cm)" % (NSKIP + 1))
    for d50 in D50S:
        for tr in [None] + TRS:
            print("  粒径 %.1f m  %s" % (d50, "出水だけ" if tr is None else "T_r = %3d 年" % tr))
            for s in SLOPES:
                r = res[(d50, tr, s)]
                kp = r["per"][NSKIP:]
                print("    S=%.2f: E %6.3f(%6.3f〜%6.3f) Esup %6.3f Bd %5.2f sd %6.1f" % (
                    s, r["e"], min(kp), max(kp), r["esup"], r["bd"], r["sd"]))
    print("定常勾配 S*(E = U = %.1f mm/年。範囲外は None): 交互計算 / 足し合わせ" % U)
    for d50 in D50S:
        print("  粒径 %.1f m: " % d50 + "  ".join(
            "%s %s / %s" % ("出水だけ" if tr is None else "T_r=%d" % tr, fmt(sstar[(d50, tr, "e")]),
                            fmt(sstar[(d50, tr, "esup")])) for tr in [None] + TRS))
    print("土石流の平衡勾配 %.3f" % S_EQ)
    print("台帳: 各段の ΣΔRi·A と表示の最大相対差 %.2e" % worst)
    print("隆起ありの確認(粒径 %.1f m、T_r = %d 年、固定勾配の定常勾配 %s)" % (D50_U, TR_U, fmt(sst)))
    for name, v in up.items():
        print("  %s: 初期勾配 %.2f、基準面から %d m までの平均勾配 %s(1 次元の予測 %s)、谷頭から %d〜%d m の勾配の"
              "縦断の予測との rms 差 %s、最初の %d 年の中央区間の変化 %+.3f mm/年(予測 U − E(S0) = %+.3f)" % (
                  name, v["s0"], LOW, "・".join("%d 年 %.3f" % (t, x) for t, x in zip(SNAP, v["low"])),
                  "・".join("%.3f" % x for x in v["lowp"]), EDGE[0], NYR * DY - EDGE[1],
                  "・".join("%.4f" % x for x in v["rms"]), SNAP[0] - TR_U, v["drift"], v["pdrift"]))


if __name__ == "__main__":
    main()
