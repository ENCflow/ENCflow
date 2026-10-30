#!/usr/bin/env python3
"""qanat の図と数表(事前に make run で 3 ケースを計算しておく)。

  figs/mechanism.png カナートの仕組みと、揚水井で湧出が細る機構の模式図(データを使わない)
  figs/setup.png     地形と坑道・涵養の帯・揚水井・排水路(平面)、坑道に沿う縦断
  figs/profile.png   坑道に沿う地下水位(坑道の床からの高さ)と坑道の水深(揚水を始める前と 300 日後)
  figs/plan.png      300 日後の地下水位の低下(カナートだけのケースとの差)
  figs/series.png    湧出量の時間変化と、終了前 20 日の水収支(涵養の行き先)
引数 en で英語ラベル版を en/figs/ に描く(データと描画処理は共通)。
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)

NX, NY, DX = 50, 21, 10.0
J = 10                                    # 坑道の行(0 始まり)
I1, I2 = 2, 35                            # 坑道のセル範囲(1 始まり)
WELL = (8, 7)                             # 揚水井(1 始まり)
SD, D2, SY2 = 1.0, 8.0, 0.2               # 土層厚、帯水層の厚さ・比湧水量
SYC, X_LINED = 0.1, 160.0                 # 坑道の貯留係数(水深 = Hgc / SYC)、漏れない区間の始まり (m)
RECH, T_PUMP, T_END = 0.010, 150.0, 300.0 # 涵養 (m3/s)、揚水を始める日、計算終了の日
X = (np.arange(NX) + 0.5) * DX
Y = (np.arange(NY) + 0.5) * DX
A = NX * NY * DX * DX
EXT = [0, NX * DX, NY * DX, 0]            # 行1 = 北を上に
CASES = [("qanat", T("カナートだけ", "qanat only"), 0.0, "#1f5f8b", "-"),
         ("well2", T("揚水井 2 L/s", "well 2 L/s"), 0.002, "#e08214", "--"),
         ("well5", T("揚水井 5 L/s", "well 5 L/s"), 0.005, "#c0392b", "-.")]
C_GROUND, C_AQ, C_WATER, C_TUNNEL = "#d9c7a0", "#cfe3f2", "#2a78d6", "#555555"
BOX = dict(facecolor="w", alpha=0.8, edgecolor="none", pad=1.5)


def rd(path):
    return np.loadtxt(path)


def frames(case):
    out = {}
    for line in open(f"result_{case}/FILENUMBER.csv"):
        if line.startswith("#"):
            continue
        f = line.split(",")
        if int(f[0]) < 9000:
            out[int(f[0])] = float(f[2]) / 86400.0
    return out


def wt(case, k):
    """地下水位 (m)(帯水層の底 + 貯留 / 比湧水量)。"""
    z = rd("data_qanat/z.txt")
    return z - SD - D2 + rd(f"result_{case}/Hg2{k:04d}.txt") / SY2


def flux(case, n):
    """フラックス測線 n の日と流量 (m3/s。東向きが正)。"""
    d = np.loadtxt(f"result_{case}/fluxes/flux{n:04d}.csv", delimiter=",", comments="#")
    return d[:, 0] / 24.0, d[:, 2]


def pumped(case):
    """終了時の表示から井戸の要求量と実際の揚水量 (m3)。"""
    for line in open(f"Screen_{case}.log"):
        if "demand" in line:
            f = line.replace("(", " ").split()
            return float(f[f.index("demand") + 1]), float(f[f.index("pumped") + 1])
    return 0.0, 0.0


# ---------------------------------------------------------------- 模式図
def _arrow(ax, x0, y0, x1, y1, color, lw=1.6, style="-|>"):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw, shrinkA=0, shrinkB=0))


def _panel(ax, well):
    x = np.linspace(0, 10, 501)
    ground = np.where(x < 1.2, 9.0 - 1.5 * x, 7.2 - 0.55 * (x - 1.2))
    ground = np.where(x > 8.0, ground - 1.8 * np.clip((x - 8.0) / 0.8, 0, 1), ground)
    base = 0.6 - 0.05 * x
    ax.fill_between(x, base, ground, color=C_GROUND)
    tunnel = 3.3 - 0.17 * x                                     # 坑道(勾配は地表よりゆるい)
    if well:
        table = 4.3 - 0.42 * x - 1.6 * np.exp(-((x - 3.2) / 1.1) ** 2)
    else:
        table = 4.6 - 0.37 * x
    table = np.minimum(table, ground - 0.3)
    table = np.maximum(table, base + 0.4)
    ax.fill_between(x, base, table, color=C_AQ)
    ax.plot(x, table, color=C_WATER, lw=1.6)
    i_out = np.argmin(np.abs(tunnel - (ground - 0.05)) + (x < 6) * 10)
    xt = x[: i_out + 1]
    tt = tunnel[: i_out + 1]
    coll = tt < table[: i_out + 1]
    ax.plot(xt, tt, color=C_TUNNEL, lw=3)
    ax.plot(xt[coll], tt[coll], color=C_WATER, lw=3)
    for xs in np.arange(0.8, x[i_out] - 0.3, 0.75):           # 縦坑
        gs = np.interp(xs, x, ground)
        ts = np.interp(xs, x, tunnel)
        ax.plot([xs, xs], [ts, gs], color="0.45", lw=0.8)
    ax.plot([0.8, 0.8], [np.interp(0.8, x, tunnel), np.interp(0.8, x, ground)], color="0.2", lw=1.6)
    ax.text(0.85, np.interp(0.8, x, ground) + 0.25, T("母井戸", "mother well"), fontsize=8)
    for xa in (0.25, 0.55):                                    # 山からの涵養
        _arrow(ax, xa, 9.6, xa, 8.4, "#2b8a3e", lw=1.4)
    ax.text(0.05, 9.75, T("山からの涵養", "recharge from the mountains"), fontsize=8, color="#2b8a3e")
    xo, zo = x[i_out], tunnel[i_out]
    _arrow(ax, xo, zo, xo + 0.7, zo - 0.25, C_WATER, lw=2.2)
    ax.text(xo + 0.75, zo + 0.35, T("出口(村・畑へ)", "outlet (to village and fields)"), fontsize=8, ha="right")
    if not well:
        xc = xt[coll][-1]
        ax.annotate("", xy=(0.8, 1.15), xytext=(xc, 1.15), arrowprops=dict(arrowstyle="<->", color=C_WATER))
        ax.text(0.9, 0.75, T("集水区間(地下水面より下。地下水が入る)", "collection section (below the water table)"),
                fontsize=8, color=C_WATER)
        ax.annotate("", xy=(xc, 1.15), xytext=(xo, 1.15), arrowprops=dict(arrowstyle="<->", color="0.3"))
        ax.text(xc + 0.1, 0.75, T("導水区間(水を運ぶ。漏れもある)", "conveyance section (carries water, some leaks)"),
                fontsize=8, color="0.3")
        for xa in (2.0, 3.2, 4.4):
            _arrow(ax, xa, np.interp(xa, x, table) - 0.2, xa + 0.15, np.interp(xa, x, tunnel) + 0.15, C_WATER, lw=1.2)
        ax.text(2.4, np.interp(2.4, x, table) + 0.35, T("地下水面", "water table"), fontsize=8, color=C_WATER)
        title = T("(a) カナート: 地下水を勾配のゆるい横穴で地表まで導く", "(a) Qanat: a gently sloping tunnel brings groundwater to the surface")
    else:
        xw = 3.2
        gw_ = np.interp(xw, x, ground)
        ax.plot([xw, xw], [base[0] + 0.5, gw_ + 0.4], color="#c0392b", lw=3)
        _arrow(ax, xw, gw_ + 0.2, xw, gw_ + 1.0, "#c0392b", lw=2)
        ax.text(xw + 0.12, gw_ + 0.85, T("深井戸の揚水", "deep well pumping"), fontsize=8, color="#c0392b")
        ax.text(xw - 0.15, np.interp(xw, x, table) - 0.1, T("地下水面が下がる", "the water table falls"),
                fontsize=8, color=C_WATER, ha="right")
        ax.text(4.3, 0.25, T("集水区間が短くなり、地下水面より上の区間で坑道の水が漏れる → 湧出が細る・枯れる",
                             "the collection section shortens and the tunnel leaks above the water table → the flow falls or stops"),
                fontsize=8, color="0.2")
        title = T("(b) 近くに深井戸ができると", "(b) When a deep well is drilled nearby")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10.3)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(title, fontsize=10, loc="left")


def mechanism():
    fig, axs = plt.subplots(2, 1, figsize=(12, 8.6))
    _panel(axs[0], False)
    _panel(axs[1], True)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in (C_GROUND, C_AQ)] + \
              [plt.Line2D([0], [0], color=C_WATER, lw=3), plt.Line2D([0], [0], color=C_TUNNEL, lw=3)]
    fig.legend(handles, [T("地盤", "ground"), T("帯水層の地下水", "groundwater in the aquifer"),
                         T("集水区間の坑道", "tunnel in the collection section"),
                         T("導水区間の坑道", "tunnel in the conveyance section")],
               loc="upper center", ncol=4, fontsize=9, frameon=False, bbox_to_anchor=(0.5, 1.0))
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    fig.savefig(f"{FIGDIR}/mechanism.png", dpi=100)
    plt.close(fig)


# ---------------------------------------------------------------- 設定
def setup():
    z = rd("data_qanat/z.txt")
    zb = rd("data_qanat/gwc_bot.txt")[J]
    fig = plt.figure(figsize=(13, 9.4))
    gs = fig.add_gridspec(2, 1, height_ratios=[1.15, 1])
    ax = fig.add_subplot(gs[0])
    zz = np.ma.masked_where(np.broadcast_to(np.arange(NX)[None, :] == NX - 1, z.shape), z)
    im = ax.imshow(zz, extent=EXT, cmap="YlOrBr", vmin=0, vmax=9)
    cs = ax.contour(X[:-1], Y, z[:, :-1], levels=np.arange(1, 9, 1), colors="0.35", linewidths=0.5)
    ax.clabel(cs, fontsize=7, fmt="%d m")
    ax.add_patch(plt.Rectangle((0, 0), 50, NY * DX, facecolor="none", edgecolor="#2b8a3e", hatch="///", lw=1.2))
    ax.text(25, -6, T("涵養の帯", "recharge strip"), ha="center", fontsize=8, color="#1b5e20")
    ax.plot(X[I1 - 1:I2], [Y[J]] * (I2 - I1 + 1), color=C_WATER, lw=3)
    ax.plot([X_LINED, X[I2 - 1]], [Y[J]] * 2, color=C_TUNNEL, lw=3)
    ax.plot(X[I1 - 1], Y[J], "s", color="k", ms=6)
    ax.text(X[I1 - 1], Y[J] + 16, T("母井戸", "mother well"), fontsize=8, ha="center", bbox=BOX)
    ax.plot(X[I2 - 1], Y[J], "v", color=C_WATER, ms=9)
    ax.text(X[I2 - 1], Y[J] - 12, T("出口", "outlet"), fontsize=8, color=C_WATER, ha="center", bbox=BOX)
    ax.text(90, Y[J] + 16, T("集水区間", "collection section"), fontsize=8, color=C_WATER, ha="center", bbox=BOX)
    ax.text(255, Y[J] + 16, T("漏れない導水区間", "watertight conveyance section"), fontsize=8, color=C_TUNNEL, ha="center", bbox=BOX)
    ax.plot(X[WELL[0] - 1], Y[WELL[1] - 1], "o", color="#c0392b", ms=8)
    ax.text(X[WELL[0] - 1] + 7, Y[WELL[1] - 1] + 3, T("揚水井", "well"), fontsize=8, color="#c0392b", bbox=BOX)
    ax.add_patch(plt.Rectangle((NX * DX - DX, 0), DX, NY * DX, color="#1f5f8b", alpha=0.6))
    ax.text(NX * DX - 5, 105, T("排水路", "drain"), fontsize=8, color="w", rotation=90, ha="center", va="center")
    ax.plot([355, 355], [75, 135], color="k", lw=1.5)
    ax.text(358, 70, T("測線 1(湧出量)", "transect 1 (qanat flow)"), fontsize=8, bbox=BOX)
    ax.set_xlabel(T("x (m)  ← 山側   扇状地 → 段丘崖 → 平野", "x (m)  ← mountain side   fan → scarp → plain"))
    ax.set_ylabel("y (m)")
    ax.set_title(T("地形(等高線 1 m)と坑道・涵養の帯・揚水井・排水路", "Terrain (1 m contours), tunnel, recharge strip, well and drain"), fontsize=10)
    fig.colorbar(im, ax=ax, shrink=0.85, pad=0.01).set_label(T("地盤高 (m)", "ground elevation (m)"))
    ax = fig.add_subplot(gs[1])
    wt0 = z - SD - D2 + 0.9 * D2
    ax.fill_between(X, z[J] - SD - D2, z[J] - SD, color=C_AQ, label=T("帯水層(層 2、厚さ 8 m)", "aquifer (layer 2, 8 m thick)"))
    ax.plot(X, z[J], color="k", lw=1.5, label=T("地表", "ground surface"))
    xl = X[I1 - 1:I2]
    ax.plot(xl[xl < X_LINED], zb[I1 - 1:I2][xl < X_LINED], color=C_WATER, lw=3, label=T("坑道の床: 集水区間(勾配 0.004)", "tunnel floor: collection section (gradient 0.004)"))
    ax.plot(xl[xl >= X_LINED - DX], zb[I1 - 1:I2][xl >= X_LINED - DX], color=C_TUNNEL, lw=3, label=T("坑道の床: 漏れない導水区間", "tunnel floor: watertight conveyance section"))
    ax.plot(X, wt0[J], color=C_WATER, ls=":", lw=1.4, label=T("初期の地下水位(地表下 1.8 m)", "initial water table (1.8 m below ground)"))
    ax.set_xlim(0, NX * DX)
    ax.set_xlabel("x (m)")
    ax.set_ylabel(T("標高 (m)", "elevation (m)"))
    ax.set_title(T("坑道に沿う縦断(中央の行)", "Longitudinal section along the tunnel (centre row)"), fontsize=10)
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/setup.png", dpi=100)
    plt.close(fig)


# ---------------------------------------------------------------- 結果
def k_at(case, day):
    fr = frames(case)
    return min(fr, key=lambda k: abs(fr[k] - day))


def profile():
    zb = rd("data_qanat/gwc_bot.txt")[J]
    xl = X[I1 - 1:I2]
    fig, axs = plt.subplots(2, 1, figsize=(12, 7.6), sharex=True, constrained_layout=True)
    runs = [("qanat", T_PUMP, T(f"揚水の前({T_PUMP:.0f} 日)", f"before pumping (day {T_PUMP:.0f})"), "k", ":")] + \
           [(c, T_END, T(f"{lab}({T_END:.0f} 日)", f"{lab} (day {T_END:.0f})"), col, ls) for c, lab, qw, col, ls in CASES]
    for case, day, lab, col, ls in runs:
        k = k_at(case, day)
        axs[0].plot(xl, (wt(case, k)[J] - rd("data_qanat/gwc_bot.txt")[J])[I1 - 1:I2], ls, color=col, lw=1.8, marker=".", label=lab)
        axs[1].plot(xl, rd(f"result_{case}/Hgc{k:04d}.txt")[J, I1 - 1:I2] / SYC * 100, ls, color=col, lw=1.8, marker=".", label=lab)
    axs[0].axhline(0, color=C_TUNNEL, lw=2)
    axs[0].text(5, -0.045, T("坑道の床", "tunnel floor"), fontsize=8, color=C_TUNNEL)
    axs[0].set_ylim(-0.6, 0.3)
    axs[0].set_ylabel(T("地下水位 − 坑道の床 (m)", "water table − tunnel floor (m)"))
    axs[0].set_title(T("坑道に沿う地下水位(正 = 坑道が地下水面より下)", "Water table along the tunnel (positive = tunnel below the water table)"), fontsize=10)
    axs[1].set_ylabel(T("坑道の水深 (cm)", "water depth in the tunnel (cm)"))
    axs[1].set_title(T("坑道の水深(出口まで水が届くか)", "Water depth in the tunnel (does the water reach the outlet?)"), fontsize=10)
    axs[1].set_xlabel(T("x (m)(坑道に沿う。出口 x = 345 m)", "x (m) (along the tunnel; outlet at x = 345 m)"))
    for ax in axs:
        ax.axvspan(0, X_LINED, color=C_WATER, alpha=0.06)
        ax.axvline(X_LINED, color="0.4", lw=1, ls="--")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8, loc="lower right" if ax is axs[0] else "upper right")
    axs[0].text(X_LINED - 4, 0.25, T("← 交換能あり(集水または漏水)", "← exchange with the aquifer (collection or leakage)"), fontsize=8, ha="right")
    axs[0].text(X_LINED + 4, 0.25, T("漏れない導水区間 →", "watertight conveyance section →"), fontsize=8)
    axs[1].set_xlim(0, 360)
    fig.savefig(f"{FIGDIR}/profile.png", dpi=100)
    plt.close(fig)


def plan():
    fig, axs = plt.subplots(1, 2, figsize=(14, 4.0), constrained_layout=True)
    base = wt("qanat", k_at("qanat", T_END))
    for ax, (case, lab, qw, col, ls) in zip(axs, CASES[1:]):
        dd = base - wt(case, k_at(case, T_END))
        im = ax.imshow(dd[:, :-1], extent=[0, (NX - 1) * DX, NY * DX, 0], cmap="Reds", vmin=0, vmax=1.0)
        cs = ax.contour(X[:-1], Y, dd[:, :-1], levels=[0.05, 0.1, 0.2, 0.5, 1.0], colors="k", linewidths=0.5)
        ax.clabel(cs, fontsize=7, fmt="%.2g")
        ax.plot(X[I1 - 1:I2], [Y[J]] * (I2 - I1 + 1), color=C_WATER, lw=2)
        ax.plot(X[WELL[0] - 1], Y[WELL[1] - 1], "o", color="k", ms=5)
        ax.set_title(T(f"{lab}: {T_END:.0f} 日の地下水位の低下(カナートだけとの差)", f"{lab}: water-table drop at day {T_END:.0f} (vs qanat only)"), fontsize=10)
        ax.set_xlabel("x (m)")
        ax.set_ylabel("y (m)")
        fig.colorbar(im, ax=ax, shrink=0.9, extend="max").set_label("m")
    fig.savefig(f"{FIGDIR}/plan.png", dpi=100)
    plt.close(fig)


def storage(case):
    """Log の全水量 S_total (m。領域平均の水深)を 1 日ごとに(見出しの行を除いて数える)。"""
    out = []
    for line in open(f"result_{case}/Log.txt"):
        f = line.split()
        if len(f) > 4 and f[1].endswith("%"):
            out.append(float(f[4]))
    return np.array(out)


def budget(case, t0, t1):
    """期間 (t0, t1] 日の平均の水収支 (L/s): 湧出・揚水・排水路・貯留の減少と東の辺の測線。
    排水路 = 涵養 − 湧出 − 揚水 + 貯留の減少(東の辺の測線は平野の流れが脈動するので平均の確認に使う)。"""
    t, q = flux(case, 1)
    t3, q3 = flux(case, 3)
    st = storage(case)
    dem, act = pumped(case)
    m = (t > t0) & (t <= t1)
    qq = q[m].mean() * 1000
    pw = act / ((T_END - T_PUMP) * 86400.0) * 1000 if t1 > T_PUMP else 0.0
    ds = -(st[int(t1)] - st[int(t0)]) * A / ((t1 - t0) * 86400.0) * 1000
    return dict(qanat=qq, well=pw, drain=RECH * 1000 - qq - pw + ds, dstore=ds, east=q3[m].mean() * 1000)


def series():
    fig, axs = plt.subplots(1, 2, figsize=(14, 4.6), constrained_layout=True, gridspec_kw=dict(width_ratios=[1.6, 1]))
    ax = axs[0]
    for case, lab, qw, col, ls in CASES:
        t, q = flux(case, 1)
        ax.plot(t, q * 1000, ls, color=col, lw=1.6, label=lab)
    ax.axhline(RECH * 1000, color="#2b8a3e", lw=1, ls=":")
    ax.text(T_END - 5, RECH * 1000 + 0.3, T("涵養量 10 L/s", "recharge 10 L/s"), fontsize=8, color="#2b8a3e", ha="right")
    ax.axvline(T_PUMP, color="0.4", lw=1, ls="--")
    ax.text(T_PUMP + 3, 12.5, T("揚水の開始", "pumping starts"), fontsize=8, color="0.3")
    ax.set_ylabel(T("湧出量 (L/s)", "qanat flow (L/s)"))
    ax.set_title(T("カナートの湧出量(出口のすぐ下流の測線 1)", "Qanat flow (transect 1 just below the outlet)"), fontsize=10)
    ax.set_xlabel(T("日", "days"))
    ax.set_xlim(0, T_END)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, loc="upper right")
    ax = axs[1]
    parts = [("qanat", T("カナートの湧出", "qanat flow"), C_WATER), ("well", T("揚水井", "well"), "#c0392b"),
             ("drain", T("排水路へ湧き出す地下水", "groundwater seeping into the drain"), "0.6")]
    rows = [(T(f"揚水の前({T_PUMP - 20:.0f}〜{T_PUMP:.0f} 日)", f"before pumping (days {T_PUMP - 20:.0f}-{T_PUMP:.0f})"),
             budget("qanat", T_PUMP - 20, T_PUMP))]
    rows += [(T(f"{lab}({T_END - 20:.0f}〜{T_END:.0f} 日)", f"{lab} (days {T_END - 20:.0f}-{T_END:.0f})"), budget(case, T_END - 20, T_END))
             for case, lab, qw, col, ls in CASES[1:]]
    for r, (lab, b) in enumerate(rows):
        x0 = 0.0
        for key, name, col in parts:
            v = b[key]
            ax.barh(r, v, left=x0, color=col, edgecolor="w", label=name if r == 0 else None)
            if v > 0.4:
                ax.text(x0 + v / 2, r, f"{v:.1f}", ha="center", va="center", fontsize=8, color="w")
            x0 += v
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([lab for lab, b in rows], fontsize=8)
    ax.invert_yaxis()
    ax.set_xlim(0, 10.5)
    ax.set_xlabel("L/s")
    ax.set_title(T("涵養 10 L/s の行き先(20 日の平均)", "Where the 10 L/s of recharge goes (20-day means)"), fontsize=10)
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, frameon=False)
    fig.savefig(f"{FIGDIR}/series.png", dpi=100)
    plt.close(fig)


def table():
    zb = rd("data_qanat/gwc_bot.txt")[J]
    print(T("ケース | 期間 | 湧出 | 揚水 | 排水路 | 貯留の減少 | (東の辺の測線) | 地下水面より下の坑道 (m)",
            "case | period | qanat | well | drain | storage loss | (east-edge transect) | tunnel below the water table (m)"))
    for case, lab, qw, col, ls in CASES:
        for t0, t1 in ((T_PUMP - 20, T_PUMP), (T_END - 20, T_END)):
            b = budget(case, t0, t1)
            nc = int((wt(case, k_at(case, t1))[J, I1 - 1:I2] > zb[I1 - 1:I2]).sum())
            print(f"{lab} | {t0:.0f}-{t1:.0f} | {b['qanat']:.2f} | {b['well']:.2f} | {b['drain']:.2f} | {b['dstore']:.2f} | {b['east']:.2f} | {nc * DX:.0f}")
        dem, act = pumped(case)
        print(f"   demand / pumped (m3): {dem:.0f} / {act:.0f}")


if __name__ == "__main__":
    mechanism()
    setup()
    if all(os.path.exists(f"result_{c}/FILENUMBER.csv") for c, _, _, _, _ in CASES):
        profile()
        plan()
        series()
        table()
