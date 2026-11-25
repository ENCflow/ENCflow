#!/usr/bin/env python3
"""paddy_dam の図と数表(事前に make run で計算しておく)。

  figs/district.png  排水区の土地利用・区画・落水口・プローブ・排水機場(入力だけ。計算結果を使わない)
  figs/maps.png      10 m の区画の解像(B)の最大水深: 通常の落水口(N)と田んぼダム(D)
  figs/series.png    雨、集落の浸水深、排水機場の前の水位、区画の平均水深の時間変化(N・D・Du・Dd)
  figs/scale.png     同じ排水区の 10 m の B と 30 m の A(片方向・双方向)の比べ(集落の浸水深と水田の平均水深)
数表(README の表)は標準出力に Markdown で出す。引数 en で英語ラベル版を en/figs/ に描く(データと描画処理は共通)。
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

NX, NY, DX = 63, 96, 10.0                     # make_district.py と同じ
EXT = [0, NX * DX, NY * DX, 0]                # 行 1 = 北を上に
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
# 系列の色(図の種類によらず同じ系列に同じ色。dataviz の既定の分類色の順)
C1, C2, C3, C4 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
CASES_B = [("N", T("N: 全て通常の落水口", "N: all normal outlets"), C1),
           ("D", T("D: 全て田んぼダム", "D: all paddy-field dams"), C2),
           ("Du", T("Du: 上流側の半分が田んぼダム", "Du: upstream half dams"), C3),
           ("Dd", T("Dd: 下流側の半分が田んぼダム", "Dd: downstream half dams"), C4)]
PROBES = {1: T("集落", "settlement"), 2: T("排水機場の前", "pumping station"), 3: T("支線排水路", "branch drain")}
PUMP = (2, 94)


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


def rain_series():
    """param_N.txt の雨(時刻 h, mm/h)を区分一定の段として"""
    tt, rr = [], []
    for line in open("param_N.txt"):
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


# ---------------------------------------------------------------- 排水区の図
def fig_district():
    use = np.loadtxt("data/use.txt", dtype=int)
    plot = np.loadtxt("data/plot.txt", dtype=int)
    outl = np.loadtxt("data/outlet.txt", dtype=int)
    # 1 農道・2 小排水路・3 支線・4 幹線・5 区画・6 集落・7 畑・8 台地
    cols = ["#b9b7b0", "#6da7ec", "#2a78d6", "#1c5cab", "#cfe7c9", "#eb6834", "#f2dca0", "#e8e6e0"]
    cmap = ListedColormap(cols)
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 6.6), gridspec_kw={"width_ratios": [1.0, 0.95]})
    ax = axs[0]
    ax.imshow(use, cmap=cmap, vmin=0.5, vmax=8.5, extent=EXT, interpolation="nearest")
    # 区画の境
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
    ax.set_title(T("(a) 排水区(630 m × 960 m、Δx = 10 m、区画 152 枚)", "(a) drainage district (630 m × 960 m, Δx = 10 m, 152 plots)"),
                 fontsize=9, loc="left", color=INK)
    ax.set_xlabel("x (m)", fontsize=8, color=INK2)
    ax.set_ylabel(T("北端からの距離 (m)", "distance from the north edge (m)"), fontsize=8, color=INK2)
    ax.tick_params(colors=INK2, labelsize=8)
    names = [T("農道", "farm road"), T("小排水路", "small drain"), T("支線排水路", "branch drain"),
             T("幹線排水路", "main drain"), T("区画(水田)", "plot (paddy)"), T("集落", "settlement"),
             T("畑", "upland field"), T("台地・堤防", "upland / levee")]
    hs = [plt.Rectangle((0, 0), 1, 1, fc=c, ec="none") for c in cols]
    hs.append(plt.Line2D([], [], ls="none", marker="s", ms=7, mfc=INK, mec="white"))
    names.append(T("排水機場(0.6 m³/s で域外へ)", "pumping station (0.6 m³/s out)"))
    ax.legend(hs, names, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.09), ncol=3, frameon=False)
    # 拡大: 北西の 20 × 24 セル(区画の境・落水口の向き)
    ax = axs[1]
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
    ax.set_title(T("(b) 北西の拡大(緑の線 = 畦畔、矢印 = 落水口と向き)", "(b) north-west corner (green = levees, arrow = outlet and direction)"),
                 fontsize=9, loc="left", color=INK)
    ax.set_xlabel("x (m)", fontsize=8, color=INK2)
    ax.tick_params(colors=INK2, labelsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, "district.png"), dpi=130)
    plt.close(fig)


# ---------------------------------------------------------------- 最大水深の図
def fig_maps():
    cases = [c for c in CASES_B if have(c[0])][:2]
    if not cases:
        return
    levels = [0.0, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 1.5, 2.0]
    ramp = ["#ffffff", "#cde2fb", "#b7d3f6", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
    cmap = ListedColormap(ramp)
    norm = BoundaryNorm(levels, cmap.N)
    use = np.loadtxt("data/use.txt", dtype=int)
    fig, axs = plt.subplots(1, len(cases), figsize=(4.2 * len(cases) + 1.0, 6.2))
    axs = np.atleast_1d(axs)
    for ax, (c, name, _) in zip(axs, cases):
        h = np.loadtxt(f"result_{c}/H9999.txt")
        im = ax.imshow(h, cmap=cmap, norm=norm, extent=EXT, interpolation="nearest")
        ax.contour(np.arange(NX) * DX + DX / 2, np.arange(NY) * DX + DX / 2, (use == 6).astype(float), [0.5],
                   colors=[C2], linewidths=1.2)
        ax.set_title(name, fontsize=9, loc="left", color=INK)
        ax.set_xlabel("x (m)", fontsize=8, color=INK2)
        ax.tick_params(colors=INK2, labelsize=8)
    axs[0].set_ylabel(T("北端からの距離 (m)", "distance from the north edge (m)"), fontsize=8, color=INK2)
    cb = fig.colorbar(im, ax=list(axs), shrink=0.8, ticks=levels)
    cb.set_label(T("最大水深 (m)(オレンジの線 = 集落)", "maximum depth (m) (orange line = settlement)"), fontsize=8)
    cb.ax.tick_params(labelsize=8)
    fig.savefig(os.path.join(FIGDIR, "maps.png"), dpi=130, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------- 時間変化の図(10 m の B)
def fig_series():
    cases = [c for c in CASES_B if have(c[0])]
    if not cases:
        return
    fig, axs = plt.subplots(4, 1, figsize=(7.6, 9.2), sharex=True,
                            gridspec_kw={"height_ratios": [0.6, 1, 1, 1]})
    tr, rr = rain_series()
    axs[0].fill_between(tr, rr, step="post", color="#9ec5f4", lw=0)
    axs[0].step(tr, rr, where="post", color=C1, lw=1.2)
    axs[0].set_ylabel(T("雨 (mm/h)", "rain (mm/h)"), fontsize=8, color=INK2)
    axs[0].set_title(T("(a) 一様な雨(24 h で 207 mm)", "(a) uniform rain (207 mm in 24 h)"), fontsize=9, loc="left", color=INK)
    for c, name, col in cases:
        t, z, h = probe(c, 1)
        axs[1].plot(t, h, color=col, lw=2, label=name)
        label_end(axs[1], t, h, c, col)
        t, z, h = probe(c, 2)
        axs[2].plot(t, z + h, color=col, lw=2, label=name)
        label_end(axs[2], t, z + h, c, col)
        p = paddy(c)
        hm = (p["store1(m3)"] + p["store2(m3)"]) / (p["area1(m2)"] + p["area2(m2)"]) * 1000.0
        tp = np.concatenate([[0.0], p["time(s)"] / 3600.0])
        hm = np.concatenate([[30.0], hm])
        axs[3].plot(tp, hm, color=col, lw=2, label=name)
        label_end(axs[3], tp, hm, c, col)
    z_house = probe(cases[0][0], 1)[1][0]
    axs[1].set_ylabel(T("水深 (m)", "depth (m)"), fontsize=8, color=INK2)
    axs[1].set_title(T("(b) 集落の浸水深(プローブ 1。地盤 %.2f m)" % z_house, "(b) inundation depth in the settlement (probe 1; ground %.2f m)" % z_house),
                     fontsize=9, loc="left", color=INK)
    axs[2].axhline(z_house, color=INK2, lw=0.8, ls="--")
    axs[2].annotate(T("集落の地盤", "settlement ground"), (47.5, z_house), xytext=(0, 3), textcoords="offset points",
                    ha="right", fontsize=7, color=INK2)
    axs[2].set_ylabel(T("水位 (m)", "water level (m)"), fontsize=8, color=INK2)
    axs[2].set_title(T("(c) 排水機場の前の幹線排水路の水位(プローブ 2)", "(c) water level of the main drain at the pumping station (probe 2)"),
                     fontsize=9, loc="left", color=INK)
    axs[3].axhline(300.0, color=INK2, lw=0.8, ls="--")
    axs[3].annotate(T("畦畔高 0.30 m", "levee height 0.30 m"), (47.5, 300.0), xytext=(0, 3), textcoords="offset points",
                    ha="right", fontsize=7, color=INK2)
    axs[3].set_ylabel(T("平均水深 (mm)", "mean depth (mm)"), fontsize=8, color=INK2)
    axs[3].set_title(T("(d) 区画の平均水深(全 152 区画)", "(d) mean water depth of the plots (all 152 plots)"), fontsize=9, loc="left", color=INK)
    axs[3].set_xlabel(T("時刻 (h)", "time (h)"), fontsize=8, color=INK2)
    axs[3].set_xlim(0, 48)
    axs[3].set_xticks(range(0, 49, 6))
    for ax in axs:
        style(ax)
    axs[1].legend(fontsize=7, frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, "series.png"), dpi=130)
    plt.close(fig)


# ---------------------------------------------------------------- 10 m の B と 30 m の A の比べ
def fig_scale():
    groups = [("N", T("通常の落水口", "normal outlets")), ("D", T("田んぼダム", "paddy-field dams"))]
    reps = [("%s", T("B 10 m(区画の解像)", "B 10 m (resolved plots)"), C1),
            ("A30_%s", T("A 30 m 片方向", "A 30 m one-way"), C2),
            ("A30_%s2", T("A 30 m 双方向", "A 30 m two-way"), C3)]
    if not any(have(r[0] % g[0]) for g in groups for r in reps):
        return
    fig, axs = plt.subplots(2, 2, figsize=(9.6, 6.6), sharex=True, sharey="row")
    for col, (g, gname) in enumerate(groups):
        for fmt, rname, color in reps:
            c = fmt % g
            if not have(c):
                continue
            t, z, h = probe(c, 1)
            axs[0, col].plot(t, h, color=color, lw=2, label=rname)
            p = paddy(c)
            hm = (p["store1(m3)"] + p["store2(m3)"]) / (p["area1(m2)"] + p["area2(m2)"]) * 1000.0
            tp = np.concatenate([[0.0], p["time(s)"] / 3600.0])
            hm = np.concatenate([[30.0], hm])
            axs[1, col].plot(tp, hm, color=color, lw=2, label=rname)
        axs[0, col].set_title(T("(%s) 集落の浸水深 — %s" % ("ab"[col], gname), "(%s) settlement depth — %s" % ("ab"[col], gname)),
                              fontsize=9, loc="left", color=INK)
        axs[1, col].set_title(T("(%s) 水田の平均水深 — %s" % ("cd"[col], gname), "(%s) mean water depth of the paddies — %s" % ("cd"[col], gname)),
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
def table():
    rows = []
    names = dict((c, n) for c, n, _ in CASES_B)
    names.update({"A30_N": T("A 30 m 片方向・通常", "A 30 m one-way, normal"), "A30_D": T("A 30 m 片方向・田んぼダム", "A 30 m one-way, dams"),
                  "A30_N2": T("A 30 m 双方向・通常", "A 30 m two-way, normal"), "A30_D2": T("A 30 m 双方向・田んぼダム", "A 30 m two-way, dams")})
    for c in ["N", "D", "Du", "Dd", "A30_N", "A30_D", "A30_N2", "A30_D2"]:
        if not have(c):
            continue
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
        area = p["area1(m2)"][0] + p["area2(m2)"][0]
        hm = (p["store1(m3)"] + p["store2(m3)"]) / area * 1000.0
        if c in ("A30_N", "A30_D"):
            back, levin = "—", "—"                 # 片方向は地表の水が水田に入らない
        else:
            back, levin = "%.0f" % p["inflow(m3)"][-1], "%.0f" % p["levee_in(m3)"][-1]
        rows.append("| %s | %.2f(%.1f h) | %s | %.2f | %.0f | %s | %s | %.0f |"
                    % (names[c], h[k], t[k], dur, (z2 + h2).max(), hm.max(), back, levin, p["spill(m3)"][-1]))
    print(T("| ケース | 集落の最大浸水深 m(時刻) | 集落の浸水深 > 0.1 m の時間 h | 排水機場の前の最高水位 m | "
            "区画・水田の最大の平均水深 mm | 落水口からの逆流 m³ | 畦畔を越えた流入 m³ | 畦畔を越えた流出 m³ |",
            "| Case | max settlement depth m (time) | hours with settlement depth > 0.1 m | max level at the pumping station m | "
            "max mean depth of plots/paddies mm | backflow through outlets m³ | inflow over the levees m³ | outflow over the levees m³ |"))
    print("|---|---:|---:|---:|---:|---:|---:|---:|")
    for r in rows:
        print(r)


if __name__ == "__main__":
    fig_district()
    fig_maps()
    fig_series()
    fig_scale()
    table()
