#!/usr/bin/env python3
"""paddy_dam の図と数表(事前に make run で計算しておく)。

同じ地区を 2 つの表現で解いた結果を描く。表現 B(Δx = 10 m。区画を解像。ケース B10_*)と表現 A(Δx = 30 m。
サブグリッドの水田タンク。ケース A30_*)。

  figs/district.png  地区と 2 つの表現(入力だけ。計算結果を使わない): 表現 A の地区、表現 B の地区、表現 B の拡大
  figs/maps.png      結果 1: 表現 B の最大水深(N と D)
  figs/series.png    結果 1: 表現 B の雨、集落の浸水深、排水機場の前の水位、区画の平均水深(N・D・Du・Dd)
  figs/scale.png     結果 2: 同じ条件の表現 B と表現 A(片方向・双方向)の比べ(集落の浸水深と水田の平均水深)
数表(README の 2 つの表)は標準出力に Markdown で出す。引数 en で英語ラベル版を en/figs/ に描く(データと描画処理は
共通)。図のパネルの番号は (1)(2)… とする(表現 A・B の記号と紛れないように)。
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
matplotlib.rcParams["axes.spines.top"] = False
matplotlib.rcParams["axes.spines.right"] = False
os.makedirs(FIGDIR, exist_ok=True)

NX, NY, DX = 63, 96, 10.0                     # 表現 B の格子(make_district.py と同じ)
NXA, NYA, DXA = 21, 32, 30.0                  # 表現 A の格子(10 m の 3 × 3)
EXT = [0, NX * DX, NY * DX, 0]                # 行 1 = 北を上に(両方の格子で同じ範囲)
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
# 系列の色(図の種類によらず同じ系列に同じ色。dataviz の既定の分類色の順)
C1, C2, C3, C4 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
REP_B = T("表現 B(Δx = 10 m)", "representation B (Δx = 10 m)")
REP_A = T("表現 A(Δx = 30 m)", "representation A (Δx = 30 m)")
SCEN = {"N": T("N: 全て通常の落水口", "N: all normal outlets"),
        "D": T("D: 全て田んぼダム", "D: all paddy-field dams"),
        "Du": T("Du: 上流側の半分が田んぼダム", "Du: upstream half dams"),
        "Dd": T("Dd: 下流側の半分が田んぼダム", "Dd: downstream half dams")}
CASES_B = [("B10_N", "N", C1), ("B10_D", "D", C2), ("B10_Du", "Du", C3), ("B10_Dd", "Dd", C4)]
PROBES = {1: T("集落", "settlement"), 2: T("排水機場の前", "pumping station"), 3: T("支線排水路", "branch drain")}
PUMP = (2, 94)                                # 表現 B の吸水槽のセル
PROBES_A = {1: (4, 31), 2: (1, 32)}           # 表現 A のプローブのセル(30 m)
PUMP_A = (1, 32)


def have(case):
    """計算が終わっているか(最大水深 H9999 は計算の終わりに書かれる)"""
    return os.path.isfile(f"result_{case}/H9999.txt")


def probe(case, n):
    """プローブ n の時刻 (h)・地盤高・水深"""
    a = np.loadtxt(f"result_{case}/probes/probe{n:04d}.csv", delimiter=",", comments="#")
    return a[:, 0], a[:, 2], a[:, 3]


def paddy(case):
    with open(f"result_{case}/paddy.csv") as f:
        head = f.readline().strip().split(",")
    a = np.loadtxt(f"result_{case}/paddy.csv", delimiter=",", skiprows=1)
    return {k: a[:, i] for i, k in enumerate(head)}


def mean_depth(p):
    """水田(区画・タンク)の平均水深 (mm)。時刻 0 の事前の湛水 30 mm を頭に足す"""
    hm = (p["store1(m3)"] + p["store2(m3)"]) / (p["area1(m2)"] + p["area2(m2)"]) * 1000.0
    return np.concatenate([[0.0], p["time(s)"] / 3600.0]), np.concatenate([[30.0], hm])


def rain_series():
    """param_B10_N.txt の雨(時刻 h, mm/h)を区分一定の段として"""
    tt, rr = [], []
    for line in open("param_B10_N.txt"):
        s = line.split("!")[0].strip()
        if s.startswith("prval(1:2,"):
            t, r = [float(x) for x in s.split("=")[1].split(",")]
            tt.append(t / 60.0)
            rr.append(r)
    return np.array(tt), np.array(rr)


def label_end(ax, x, y, text, color):
    ax.annotate(text, xy=(x[-1], y[-1]), xytext=(4, 0), textcoords="offset points", va="center",
                fontsize=8, color=INK2)
    ax.plot([x[-1]], [y[-1]], "o", ms=3, color=color)


def style(ax):
    ax.grid(True, color=GRID, lw=0.6)
    ax.tick_params(colors=INK2, labelsize=8)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(INK2)


def axes_map(ax, title):
    ax.set_title(title, fontsize=9, loc="left", color=INK)
    ax.set_xlabel("x (m)", fontsize=8, color=INK2)
    ax.tick_params(colors=INK2, labelsize=8)


# ---------------------------------------------------------------- 地区と 2 つの表現の図
def fig_district():
    use = np.loadtxt("data/use.txt", dtype=int)
    plot = np.loadtxt("data/plot.txt", dtype=int)
    outl = np.loadtxt("data/outlet.txt", dtype=int)
    frac = np.loadtxt("data/frac30.txt")
    rw = np.loadtxt("data/rw30.txt")
    gv = np.loadtxt("data/gv30.txt")
    # 表現 B の土地利用: 1 農道・2 小排水路・3 支線・4 幹線・5 区画・6 集落・7 畑・8 台地
    cols = ["#b9b7b0", "#6da7ec", "#2a78d6", "#1c5cab", "#cfe7c9", "#eb6834", "#f2dca0", "#e8e6e0"]
    cmap = ListedColormap(cols)
    fig, axs = plt.subplots(1, 3, figsize=(14.2, 7.4), gridspec_kw={"width_ratios": [1.0, 1.0, 0.95]})

    # (1) 表現 A の地区: 水田面積率(5 段の順序の色)、河道のセル、集落
    ax = axs[0]
    greens = ["#f3f2ee", "#e2f0dd", "#c3e2ba", "#9dcd90", "#6fb262", "#43903b"]
    code = np.digitize(frac, [1e-6, 0.2, 0.4, 0.6, 0.8])          # 0 = 水田なし、1..5 = 面積率の段
    code = np.where(gv < 0.999, 6, code)
    code = np.where(rw > 0, 7, code)
    cmapa = ListedColormap(greens + ["#eb6834", "#2a78d6"])
    ax.imshow(code, cmap=cmapa, vmin=-0.5, vmax=7.5, extent=EXT, interpolation="nearest")
    for k in range(NXA + 1):
        ax.plot([k * DXA] * 2, [0, NYA * DXA], color="#ffffff", lw=0.5)
    for k in range(NYA + 1):
        ax.plot([0, NXA * DXA], [k * DXA] * 2, color="#ffffff", lw=0.5)
    for n, (i, j) in PROBES_A.items():
        ax.plot((i - 0.5) * DXA, (j - 0.5) * DXA, "o", ms=6, mfc="white", mec=INK, mew=1.0)
        ax.annotate("%d %s" % (n, PROBES[n]), ((i - 0.5) * DXA, (j - 0.5) * DXA),
                    xytext=(8, 10) if n == 1 else (8, -14), textcoords="offset points", fontsize=8, color=INK)
    ax.plot((PUMP_A[0] - 0.85) * DXA, (PUMP_A[1] - 0.5) * DXA, "s", ms=7, mfc=INK, mec="white", mew=1.0)
    axes_map(ax, T("(1) %s: 21 × 32 セル。水田はセルの面積率、\n支線・幹線排水路は河道のセル" % REP_A,
                   "(1) %s: 21 × 32 cells; paddies as area\nfraction, branch and main drains as channel cells" % REP_A))
    ax.set_ylabel(T("北端からの距離 (m)", "distance from the north edge (m)"), fontsize=8, color=INK2)
    names = [T("水田なし(農道・畑・台地)", "no paddy (roads, fields, upland)"),
             T("水田面積率 0〜0.2", "paddy fraction 0–0.2"), T("0.2〜0.4", "0.2–0.4"), T("0.4〜0.6", "0.4–0.6"),
             T("0.6〜0.8", "0.6–0.8"),
             T("0.8〜0.95(上限)", "0.8–0.95 (cap)"), T("集落(建物の空隙率 < 1)", "settlement (void ratio < 1)"),
             T("河道のセル(サブグリッド幅 10 m)", "channel cell (subgrid width 10 m)")]
    hs = [plt.Rectangle((0, 0), 1, 1, fc=c, ec="none") for c in greens + ["#eb6834", "#2a78d6"]]
    ax.legend(hs, names, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=2, frameon=False)

    # (2) 表現 B の地区
    ax = axs[1]
    ax.imshow(use, cmap=cmap, vmin=0.5, vmax=8.5, extent=EXT, interpolation="nearest")
    for j in range(NY):
        for i in range(NX):
            if plot[j, i] > 0:
                if i + 1 < NX and plot[j, i + 1] != plot[j, i]:
                    ax.plot([(i + 1) * DX] * 2, [j * DX, (j + 1) * DX], color="#5f8f55", lw=0.4)
                if j + 1 < NY and plot[j + 1, i] != plot[j, i]:
                    ax.plot([i * DX, (i + 1) * DX], [(j + 1) * DX] * 2, color="#5f8f55", lw=0.4)
    offs = {1: (8, 10), 2: (8, -14), 3: (-6, 10)}
    for n, (i, j) in {1: (12, 92), 2: (3, 94), 3: (61, 60)}.items():
        ax.plot((i - 0.5) * DX, (j - 0.5) * DX, "o", ms=6, mfc="white", mec=INK, mew=1.0)
        ax.annotate("%d %s" % (n, PROBES[n]), ((i - 0.5) * DX, (j - 0.5) * DX), xytext=offs[n],
                    textcoords="offset points", fontsize=8, color=INK, ha="right" if n == 3 else "left")
    ax.plot((PUMP[0] - 1.0) * DX, (PUMP[1] - 0.5) * DX, "s", ms=7, mfc=INK, mec="white", mew=1.0)
    ax.add_patch(plt.Rectangle((0, 0), 20 * DX, 24 * DX, fill=False, ec=INK, lw=1.0, ls="--"))
    ax.annotate("(3)", (20 * DX, 24 * DX), xytext=(3, -3), textcoords="offset points", fontsize=8, color=INK,
                va="top")
    axes_map(ax, T("(2) %s: 63 × 96 セル。区画 152 枚と\n全ての排水路をセルで解く" % REP_B,
                   "(2) %s: 63 × 96 cells; the 152 plots\nand all drains are solved by cells" % REP_B))
    names = [T("農道", "farm road"), T("小排水路", "small drain"), T("支線排水路", "branch drain"),
             T("幹線排水路", "main drain"), T("区画(水田)", "plot (paddy)"), T("集落", "settlement"),
             T("畑", "upland field"), T("台地・堤防", "upland / levee")]
    hs = [plt.Rectangle((0, 0), 1, 1, fc=c, ec="none") for c in cols]
    hs.append(plt.Line2D([], [], ls="none", marker="s", ms=7, mfc=INK, mec="white"))
    names.append(T("排水機場(0.6 m³/s で域外へ)", "pumping station (0.6 m³/s out)"))
    hs.append(plt.Line2D([], [], ls="none", marker="o", ms=6, mfc="white", mec=INK))
    names.append(T("プローブ", "probe"))
    ax.legend(hs, names, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=2, frameon=False)

    # (3) 表現 B の拡大: 北西の 20 × 24 セル(区画の境 = 畦畔、落水口の向き)
    ax = axs[2]
    sub = use[:24, :20]
    ax.imshow(sub, cmap=cmap, vmin=0.5, vmax=8.5, extent=[0, 20 * DX, 24 * DX, 0], interpolation="nearest")
    for j in range(24):
        for i in range(20):
            p = plot[j, i]
            if p > 0:
                if i + 1 < 20 and plot[j, i + 1] != p:
                    ax.plot([(i + 1) * DX] * 2, [j * DX, (j + 1) * DX], color="#3d6b35", lw=1.2)
                if j + 1 < 24 and plot[j + 1, i] != p:
                    ax.plot([i * DX, (i + 1) * DX], [(j + 1) * DX] * 2, color="#3d6b35", lw=1.2)
                if j - 1 >= 0 and plot[j - 1, i] != p:
                    ax.plot([i * DX, (i + 1) * DX], [j * DX] * 2, color="#3d6b35", lw=1.2)
                if i - 1 >= 0 and plot[j, i - 1] != p:
                    ax.plot([i * DX] * 2, [j * DX, (j + 1) * DX], color="#3d6b35", lw=1.2)
            k = outl[j, i]
            if k > 0:
                dy = DX * (0.75 if k == 7 else -0.75)
                ax.annotate("", xy=((i + 0.5) * DX, (j + 0.5) * DX + dy), xytext=((i + 0.5) * DX, (j + 0.5) * DX),
                            arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.0, mutation_scale=8))
    axes_map(ax, T("(3) %s の北西の拡大((2) の破線の枠)。\n緑の線 = 畦畔、矢印 = 落水口と向き" % REP_B,
                   "(3) %s, north-west corner (dashed box in (2)).\ngreen = levees, arrow = outlet and direction" % REP_B))
    fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, "district.png"), dpi=130, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------- 結果 1: 表現 B の最大水深
def fig_maps():
    cases = [c for c in CASES_B if have(c[0])][:2]
    if not cases:
        return
    levels = [0.0, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 1.5, 2.0]
    ramp = ["#ffffff", "#cde2fb", "#b7d3f6", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
    cmap = ListedColormap(ramp)
    norm = BoundaryNorm(levels, cmap.N)
    use = np.loadtxt("data/use.txt", dtype=int)
    fig, axs = plt.subplots(1, len(cases), figsize=(4.2 * len(cases) + 1.0, 6.4))
    axs = np.atleast_1d(axs)
    for n, (ax, (c, s, _)) in enumerate(zip(axs, cases)):
        h = np.loadtxt(f"result_{c}/H9999.txt")
        im = ax.imshow(h, cmap=cmap, norm=norm, extent=EXT, interpolation="nearest")
        ax.contour(np.arange(NX) * DX + DX / 2, np.arange(NY) * DX + DX / 2, (use == 6).astype(float), [0.5],
                   colors=[C2], linewidths=1.2)
        axes_map(ax, "(%d) %s\n%s" % (n + 1, REP_B, SCEN[s]))
    axs[0].set_ylabel(T("北端からの距離 (m)", "distance from the north edge (m)"), fontsize=8, color=INK2)
    cb = fig.colorbar(im, ax=list(axs), shrink=0.8, ticks=levels)
    cb.set_label(T("最大水深 (m)(オレンジの線 = 集落)", "maximum depth (m) (orange line = settlement)"), fontsize=8)
    cb.ax.tick_params(labelsize=8)
    fig.savefig(os.path.join(FIGDIR, "maps.png"), dpi=130, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------- 結果 1: 表現 B の時間変化
def fig_series():
    cases = [c for c in CASES_B if have(c[0])]
    if not cases:
        return
    fig, axs = plt.subplots(4, 1, figsize=(7.6, 9.4), sharex=True,
                            gridspec_kw={"height_ratios": [0.6, 1, 1, 1]})
    tr, rr = rain_series()
    axs[0].fill_between(tr, rr, step="post", color="#9ec5f4", lw=0)
    axs[0].step(tr, rr, where="post", color=C1, lw=1.2)
    axs[0].set_ylabel(T("雨 (mm/h)", "rain (mm/h)"), fontsize=8, color=INK2)
    axs[0].set_title(T("(1) 一様な雨(24 h で 207 mm。2 つの表現で共通)", "(1) uniform rain (207 mm in 24 h; common to both representations)"),
                     fontsize=9, loc="left", color=INK)
    for c, s, col in cases:
        name = SCEN[s]
        t, z, h = probe(c, 1)
        axs[1].plot(t, h, color=col, lw=2, label=name)
        label_end(axs[1], t, h, s, col)
        t, z, h = probe(c, 2)
        axs[2].plot(t, z + h, color=col, lw=2, label=name)
        label_end(axs[2], t, z + h, s, col)
        tp, hm = mean_depth(paddy(c))
        axs[3].plot(tp, hm, color=col, lw=2, label=name)
        label_end(axs[3], tp, hm, s, col)
    z_house = probe(cases[0][0], 1)[1][0]
    axs[1].set_ylabel(T("水深 (m)", "depth (m)"), fontsize=8, color=INK2)
    axs[1].set_title(T("(2) %s: 集落の浸水深(プローブ 1。地盤 %.2f m)" % (REP_B, z_house),
                       "(2) %s: inundation depth in the settlement (probe 1; ground %.2f m)" % (REP_B, z_house)),
                     fontsize=9, loc="left", color=INK)
    axs[2].axhline(z_house, color=INK2, lw=0.8, ls="--")
    axs[2].annotate(T("集落の地盤", "settlement ground"), (47.5, z_house), xytext=(0, 3), textcoords="offset points",
                    ha="right", fontsize=7, color=INK2)
    axs[2].set_ylabel(T("水位 (m)", "water level (m)"), fontsize=8, color=INK2)
    axs[2].set_title(T("(3) %s: 排水機場の前の幹線排水路の水位(プローブ 2)" % REP_B,
                       "(3) %s: water level of the main drain at the pumping station (probe 2)" % REP_B),
                     fontsize=9, loc="left", color=INK)
    axs[3].axhline(300.0, color=INK2, lw=0.8, ls="--")
    axs[3].annotate(T("畦畔高 0.30 m", "levee height 0.30 m"), (47.5, 300.0), xytext=(0, 3), textcoords="offset points",
                    ha="right", fontsize=7, color=INK2)
    axs[3].set_ylabel(T("平均水深 (mm)", "mean depth (mm)"), fontsize=8, color=INK2)
    axs[3].set_title(T("(4) %s: 区画の平均水深(全 152 区画)" % REP_B, "(4) %s: mean water depth of the plots (all 152 plots)" % REP_B),
                     fontsize=9, loc="left", color=INK)
    axs[3].set_xlabel(T("時刻 (h)", "time (h)"), fontsize=8, color=INK2)
    axs[3].set_xlim(0, 48)
    axs[3].set_xticks(range(0, 49, 6))
    for ax in axs:
        style(ax)
    axs[1].legend(fontsize=7, frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, "series.png"), dpi=130)
    plt.close(fig)


# ---------------------------------------------------------------- 結果 2: 同じ条件の表現 B と表現 A
REPS = [("B10_%s", REP_B, C1),
        ("A30_%s", T("%s・片方向" % REP_A, "%s, one-way" % REP_A), C2),
        ("A30_%s2", T("%s・双方向" % REP_A, "%s, two-way" % REP_A), C3)]


def fig_scale():
    groups = ["N", "D"]
    if not any(have(r[0] % g) for g in groups for r in REPS):
        return
    fig, axs = plt.subplots(2, 2, figsize=(9.8, 6.8), sharex=True, sharey="row")
    for col, g in enumerate(groups):
        for fmt, rname, color in REPS:
            c = fmt % g
            if not have(c):
                continue
            t, z, h = probe(c, 1)
            axs[0, col].plot(t, h, color=color, lw=2, label=rname)
            tp, hm = mean_depth(paddy(c))
            axs[1, col].plot(tp, hm, color=color, lw=2, label=rname)
        axs[0, col].set_title(T("(%d) 集落の浸水深 — %s" % (col + 1, SCEN[g]), "(%d) settlement depth — %s" % (col + 1, SCEN[g])),
                              fontsize=9, loc="left", color=INK)
        axs[1, col].set_title(T("(%d) 水田の平均水深 — %s" % (col + 3, SCEN[g]),
                                "(%d) mean water depth of the paddies — %s" % (col + 3, SCEN[g])),
                              fontsize=9, loc="left", color=INK)
        axs[1, col].set_xlabel(T("時刻 (h)", "time (h)"), fontsize=8, color=INK2)
        axs[1, col].set_xlim(0, 48)
        axs[1, col].set_xticks(range(0, 49, 6))
        axs[1, col].axhline(300.0, color=INK2, lw=0.8, ls="--")
    axs[0, 0].set_ylabel(T("水深 (m)", "depth (m)"), fontsize=8, color=INK2)
    axs[1, 0].set_ylabel(T("平均水深 (mm)", "mean depth (mm)"), fontsize=8, color=INK2)
    for ax in axs.flat:
        style(ax)
    axs[0, 0].legend(fontsize=7, frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, "scale.png"), dpi=130)
    plt.close(fig)


# ---------------------------------------------------------------- 数表
def stats(c):
    """集落の最大浸水深と時刻、0.1 m を超えた時間、排水機場の前の最高水位、水田の最大の平均水深、台帳"""
    t, z, h = probe(c, 1)
    k = int(np.argmax(h))
    wet = t[h > 0.1]
    if len(wet) == 0:
        dur = "0"
    elif h[-1] > 0.1:
        dur = T("%.0f 以上(48 h でも続く)", "%.0f or more (still at 48 h)") % (t[-1] - wet[0])
    else:
        dur = "%.0f" % (wet[-1] - wet[0])
    t2, z2, h2 = probe(c, 2)
    p = paddy(c)
    hm = mean_depth(p)[1].max()
    return h[k], t[k], dur, (z2 + h2).max(), hm, p


def table():
    # 表 1(結果 1): 表現 B の 4 ケース
    print(T("表 1(結果 1。%s)" % REP_B, "Table 1 (result 1; %s)" % REP_B))
    print(T("| 落水口 | 集落の最大浸水深 m(時刻) | 集落の浸水深 > 0.1 m の時間 h | 排水機場の前の最高水位 m | "
            "区画の最大の平均水深 mm | 落水口からの逆流 m³ | 畦畔を越えた流入 m³ | 畦畔を越えた流出 m³ |",
            "| Outlets | max settlement depth m (time) | hours with settlement depth > 0.1 m | max level at the pumping "
            "station m | max mean depth of the plots mm | backflow through outlets m³ | inflow over the levees m³ | "
            "outflow over the levees m³ |"))
    print("|---|---:|---:|---:|---:|---:|---:|---:|")
    for c, s, _ in CASES_B:
        if not have(c):
            continue
        hx, tx, dur, lv, hm, p = stats(c)
        print("| %s | %.2f(%.1f h) | %s | %.2f | %.0f | %.0f | %.0f | %.0f |"
              % (SCEN[s], hx, tx, dur, lv, hm, p["inflow(m3)"][-1], p["levee_in(m3)"][-1], p["spill(m3)"][-1]))
    # 表 2(結果 2): 同じ条件の表現 B と表現 A
    print()
    print(T("表 2(結果 2。同じ条件の %s と %s)" % (REP_B, REP_A),
            "Table 2 (result 2; %s and %s under the same conditions)" % (REP_B, REP_A)))
    print(T("| 落水口 | 表現 | 集落の最大浸水深 m(時刻) | 集落の浸水深 > 0.1 m の時間 h | 排水機場の前の最高水位 m | "
            "水田の最大の平均水深 mm | 落水口からの逆流 m³ | 畦畔を越えた流入 m³ |",
            "| Outlets | Representation | max settlement depth m (time) | hours with settlement depth > 0.1 m | "
            "max level at the pumping station m | max mean depth of the paddies mm | backflow through outlets m³ | "
            "inflow over the levees m³ |"))
    print("|---|---|---:|---:|---:|---:|---:|---:|")
    for g in ["N", "D"]:
        for fmt, rname, _ in REPS:
            c = fmt % g
            if not have(c):
                continue
            hx, tx, dur, lv, hm, p = stats(c)
            if c.startswith("A30") and not c.endswith("2"):
                back, levin = "—", "—"            # 片方向は地表の水が水田に入らない
            else:
                back, levin = "%.0f" % p["inflow(m3)"][-1], "%.0f" % p["levee_in(m3)"][-1]
            print("| %s | %s | %.2f(%.1f h) | %s | %.2f | %.0f | %s | %s |"
                  % (g, rname, hx, tx, dur, lv, hm, back, levin))


if __name__ == "__main__":
    fig_district()
    fig_maps()
    fig_series()
    fig_scale()
    table()
