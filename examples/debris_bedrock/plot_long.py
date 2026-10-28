#!/usr/bin/env python3
# examples/debris_bedrock 後半(長期)の図と数表(make_long.py と定数を対で保守)
#   python3 plot_long.py      figs/long_*.png(日本語)と数表(標準出力)
#   python3 plot_long.py en   en/figs/long_*.png(英語)
# long/<構成>/track.csv(Run_chain.sh が各段の後に書く。台帳の表示とセルごとの z・Ri・sd)を読む。
# 低下速度と定常勾配は水路の床(壁に接する両端の列を除く中央 3 列)の値で求める。壁の列は出水では
# ほとんど削れず段のように残るので、全幅の平均は水路の低下を小さく見せる(数表に並べて出す)。
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from make_long import (NX, NY, DX, SLOPES, TRS, D50S, TR_INF, NSKIP, U, UPLIFT_RUNS, TR_U, D50_U, MID, CH,
                       CMIX, name_fixed, zrow)

EN = len(sys.argv) > 1 and sys.argv[1] == "en"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
OUT = "en/figs/" if EN else "figs/"
INK, MUTED, GRID = "#1f1e1c", "#52514e", "#e4e2dc"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
RAMP = ("#86b6ef", "#2a78d6", "#104281")          # T_r = 100・30・10 年(頻度が上がるほど濃い)
SDB, TANPHI = 1.65, 0.70021                      # 土石流の平衡勾配(高橋・中川の平衡濃度 = 流入の濃度)
S_EQ = SDB * CMIX * TANPHI / (1.0 + SDB * CMIX)
MIDR = [j for j in range(NY) if MID[0] <= (j + 0.5) * DX < MID[1]]     # 中央区間の行
CHL, WALL, MIDC = list(CH), [0, NX - 1], NX // 2
LOW = (NY - 23, NY - 3)                          # 下流区間の勾配: 出口の行の中心から 44 m と 4 m の行
SNAP = (1500.0, 3000.0, 4530.0)                  # 隆起ありの縦断を比べる時刻 (年)


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


def chan(a):
    """中央区間の水路の床の平均"""
    return a[MIDR][:, CHL].mean()


def full(a):
    """中央区間の全幅の平均"""
    return a[MIDR].mean()


def lateral(z):
    """横断の形 (m): 壁の列の段の高さ(壁の列 − 水路の床)と、中央の列の溝の深さ(両隣 − 中央)"""
    zz = z[MIDR]
    return (zz[:, WALL].mean() - zz[:, CHL].mean(),
            (0.5 * (zz[:, MIDC - 1] + zz[:, MIDC + 1]) - zz[:, MIDC]).mean())


def rates(name, tr):
    """固定勾配の連鎖: 地表の低下速度(サイクル NSKIP+1 以降の平均。mm/年)と、最初の出水・土石流の足し合わせ"""
    rows = load(name)
    fl = floods(rows)
    keep = range(NSKIP, len(fl) - 1)                  # fl[k] → fl[k+1] がサイクル k+1
    def rate(f, key, sign):
        return 1000.0 * sum(sign * (f(fl[k + 1][key]) - f(fl[k][key])) for k in keep) / len(keep) / tr
    deb = [r for r in rows if r["stage"] == "debris"]
    if deb:
        b1 = chan(deb[0]["ri"]) - chan(fl[0]["ri"])   # 1 回目の土石流(出水の後の裸岩)
        esup = 1000.0 * (chan(fl[0]["ri"]) + b1) / tr
        bd = 100.0 * sum(chan(deb[k]["ri"]) - chan(fl[k]["ri"]) for k in keep) / len(keep)   # 1 回 (cm)
    else:
        esup, bd = 1000.0 * chan(fl[0]["ri"]) / tr, 0.0
    return {"e": rate(chan, "z", -1.0), "efull": rate(full, "z", -1.0), "erock": rate(chan, "ri", 1.0),
            "esup": esup, "bd": bd, "sd": 100.0 * sum(chan(fl[k + 1]["sd"]) for k in keep) / len(keep),
            "lat": lateral(fl[-1]["z"]), "rows": rows}


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


def profile(z):
    """水路の床の縦断(行ごとの中央 3 列の平均)"""
    return z[:, CHL].mean(axis=1)


def slopes(p):
    """隣り合う行の勾配の 10 m(5 区間)の移動平均。位置は谷頭からの距離"""
    sl = (p[:-1] - p[1:]) / DX
    sm = np.array([sl[max(0, j - 2):j + 3].mean() for j in range(NY - 1)])
    return np.arange(1, NY) * DX, sm


def low_slope(p):
    return (p[LOW[0]] - p[LOW[1]]) / ((LOW[1] - LOW[0]) * DX)


def model_1d(s0, es, times, dt=1.0):
    """1 次元の予測: z_t = U − E(S)(E は固定勾配の交互計算の折れ線、範囲外は端の値)。出口の行は固定。
    勾配は下流側の差分(変化は上流へ伝わる)"""
    z = np.array([zrow(s0, j) for j in range(1, NY + 1)])
    out, t = {}, 0.0
    for tk in sorted(times):
        while t < tk - 1e-9:
            s = (z[:-1] - z[1:]) / DX
            z[:-1] += dt * (U - np.interp(s, SLOPES, es)) / 1000.0
            t += dt
        out[tk] = z.copy()
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
            for key in ("e", "efull", "esup"):
                sstar[(d50, tr, key)] = crossing(SLOPES, [res[(d50, tr, s)][key] for s in SLOPES], U)

    # --- 図 1: 固定勾配の長期の低下速度 ---
    fig, axs = plt.subplots(1, 2, figsize=(7.6, 3.8), sharey=True)
    for ax, d50 in zip(axs, D50S):
        ax.axhline(U, color=MUTED, lw=0.8, ls=":")
        ax.text(SLOPES[0], U + 0.05, T("隆起 1 mm/年", "uplift 1 mm/yr"), color=MUTED, fontsize=8, va="bottom")
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
    axs[0].set_ylabel(T("水路の床の長期の低下速度 (mm/年)", "long-term lowering of the channel floor (mm/yr)"))
    axs[1].legend(loc="upper left", frameon=False, fontsize=7.5)
    fig.text(0.99, 0.01, T("破線: 出水と土石流を別々に計算した足し合わせ", "dashed: sum of floods and debris flows computed separately"),
             ha="right", va="bottom", fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
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
            ax.plot([r["cycle"] for r in fl], [100 * chan(r["sd"]) for r in fl], color=col, lw=1.6, ls=ls,
                    label=T("勾配 %.2f・%d 年に 1 回", "slope %.2f, once in %d yr") % (s, tr))
    ax.set_xlabel(T("サイクル(出水の後)", "cycle (after the flood)"))
    ax.set_ylabel(T("水路の床の可動層 (cm)", "mobile layer on the channel floor (cm)"))
    ax.set_title(T("堆積物の粒径 0.4 m(中央区間)", "sediment size 0.4 m (middle reach)"), loc="left", fontsize=9,
                 color=INK)
    ax.legend(loc="upper left", frameon=False, fontsize=7, ncol=3)
    style(ax)
    fig.tight_layout()
    fig.savefig(OUT + "long_cover.png", dpi=150)
    plt.close(fig)

    # --- 図 4: 隆起ありの確認と 1 次元の予測 ---
    es = [res[(D50_U, TR_U, s)]["e"] for s in SLOPES]
    sst = sstar[(D50_U, TR_U, "e")]
    fig, axs = plt.subplots(1, 3, figsize=(10.4, 3.6), gridspec_kw={"width_ratios": (1.25, 1.0, 1.0)})
    up = {}
    for (name, s0), col in zip(UPLIFT_RUNS, (ORANGE, BLUE)):
        fl = floods(load(name))
        tyr = [(k + 1) * TR_U for k in range(len(fl))]      # 出水 k の終わり(最初の出水も T_r 年分)
        pred = model_1d(s0, es, tyr)
        for tk, a in zip(SNAP, (0.35, 0.65, 1.0)):
            k = tyr.index(tk)
            x, sm = slopes(profile(fl[k]["z"]))
            axs[0].plot(x, sm, color=col, lw=1.3, alpha=a)
            xp, smp = slopes(pred[tk])
            axs[0].plot(xp, smp, color=MUTED, lw=0.9, ls="--", alpha=a)
        axs[1].plot(tyr, [low_slope(profile(r["z"])) for r in fl], color=col, lw=1.6,
                    label=T("初期勾配 %.2f", "initial slope %.2f") % s0)
        axs[1].plot(tyr, [low_slope(pred[t]) for t in tyr], color=MUTED, lw=1, ls="--")
        lat = [lateral(r["z"]) for r in fl]
        axs[2].plot(tyr, [v[0] for v in lat], color=col, lw=1.6)
        axs[2].plot(tyr, [v[1] for v in lat], color=col, lw=1.0, ls=":")
        k1 = tyr.index(SNAP[0])
        e0 = float(np.interp(s0, SLOPES, es))
        up[name] = {"s0": s0, "low": low_slope(profile(fl[-1]["z"])), "lowp": low_slope(pred[tyr[-1]]), "t": tyr[-1],
                    "drift": 1000.0 * (chan(fl[k1]["z"]) - chan(fl[0]["z"])) / (tyr[k1] - tyr[0]),
                    "pdrift": U - e0, "lat": lat[-1], "lat1": lat[k1]}
    axs[0].axhline(sst, color=MUTED, lw=0.8, ls=":")
    axs[0].text(5, sst + 0.002, T("固定勾配の定常勾配 %.3f", "steady slope from fixed slopes %.3f") % sst,
                color=MUTED, fontsize=7.5, va="bottom")
    axs[0].set_xlabel(T("谷頭からの距離 (m)", "distance from the head (m)"))
    axs[0].set_ylabel(T("水路の床の勾配(10 m の移動平均)", "channel-floor slope (10 m running mean)"))
    axs[0].set_title(T("%d・%d・%d 年(濃いほど遅い)。破線: 1 次元の予測", "%d, %d, %d yr (darker = later); dashed: 1-D") %
                     SNAP, loc="left", fontsize=8.5, color=INK)
    axs[1].axhline(sst, color=MUTED, lw=0.8, ls=":")
    axs[1].set_xlabel(T("暦の時間 (年)", "calendar time (yr)"))
    axs[1].set_ylabel(T("出口から 4〜44 m の勾配", "slope 4-44 m above the outlet"))
    axs[1].legend(loc="center right", frameon=False, fontsize=7.5)
    axs[1].set_title(T("破線: 1 次元の予測", "dashed: 1-D prediction"), loc="left", fontsize=8.5, color=INK)
    axs[2].set_xlabel(T("暦の時間 (年)", "calendar time (yr)"))
    axs[2].set_ylabel(T("横断の形 (m)", "cross-section shape (m)"))
    axs[2].set_title(T("実線: 壁の列の段 / 点線: 中央の溝", "solid: wall-column bench / dotted: centre groove"),
                     loc="left", fontsize=8.5, color=INK)
    for ax in axs:
        style(ax)
    fig.tight_layout()
    fig.savefig(OUT + "long_uplift.png", dpi=150)
    plt.close(fig)

    if EN:
        return
    print("水路の床の長期の低下速度 E と全幅の平均 Ef (mm/年。サイクル %d 以降の平均)、足し合わせ Esup、"
          "1 回の土石流の侵食 Bd (cm)、出水の後の可動層 sd (cm)、終了時の壁の列の段と中央の溝 (m)" % (NSKIP + 1))
    for d50 in D50S:
        for tr in [None] + TRS:
            lab = "出水だけ" if tr is None else "T_r = %3d 年" % tr
            print("  粒径 %.1f m  %s" % (d50, lab))
            for s in SLOPES:
                r = res[(d50, tr, s)]
                print("    S=%.2f: E %6.3f Ef %6.3f Esup %6.3f Bd %5.2f sd %6.1f 段 %6.2f 溝 %6.2f" % (
                    s, r["e"], r["efull"], r["esup"], r["bd"], r["sd"], r["lat"][0], r["lat"][1]))
    print("定常勾配 S*(E = U = %.1f mm/年。範囲外は None): 交互計算 / 足し合わせ / 全幅の平均で求めた交互計算" % U)
    for d50 in D50S:
        print("  粒径 %.1f m: " % d50 + "  ".join(
            "%s %s / %s / %s" % ("出水だけ" if tr is None else "T_r=%d" % tr, fmt(sstar[(d50, tr, "e")]),
                                 fmt(sstar[(d50, tr, "esup")]), fmt(sstar[(d50, tr, "efull")]))
            for tr in [None] + TRS))
    print("土石流の平衡勾配 %.3f" % S_EQ)
    print("台帳: 各段の ΣΔRi·A と表示の最大相対差 %.2e" % worst)
    print("隆起ありの確認(粒径 %.1f m、T_r = %d 年、固定勾配の定常勾配 %s)" % (D50_U, TR_U, fmt(sst)))
    for name, v in up.items():
        print("  %s: 初期勾配 %.2f、%d 年後の出口から 4〜44 m の勾配 %.3f(1 次元の予測 %.3f)、"
              "最初の %d 年の中央区間の床の変化 %+.3f mm/年(予測 U − E(S0) = %+.3f)、"
              "壁の列の段 %.2f m・中央の溝 %.2f m(%d 年 %.2f m・%.2f m)" % (
                  name, v["s0"], v["t"], v["low"], v["lowp"], SNAP[0] - TR_U, v["drift"], v["pdrift"],
                  v["lat"][0], v["lat"][1], SNAP[0], v["lat1"][0], v["lat1"][1]))


if __name__ == "__main__":
    main()
