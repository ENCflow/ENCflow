#!/usr/bin/env python3
"""examples/joganji_flume の結果と計測の比較の図と数表。

  python3 plot_results.py      # figs/*.png(日本語ラベル)と数表
  python3 plot_results.py en   # en/figs/*.png(英語ラベル)と数表

  figs/setup.png       初期の河床高・移動層・表層の細粒の割合と、水位計・区間流入の位置
  figs/waterlevel.png  上流端の流量と、水位計 4 か所の水位の時系列(計測と計算)
  figs/bedchange.png   240 分の河床変化 z − z0 の平面分布(計測と各構成)
  figs/profile.png     低水路の河床変化の縦断(断面平均と最深河床)と、表層の粒径集団の割合の縦断
  figs/surface.png     240 分の表層の細粒(粒径集団 1)の割合の平面分布(計測と混合粒径の構成)
  figs/velocity.png    93 分の流速の大きさ(計測の点と各構成)

数表(標準出力。README の表はこれを写したもの):
  表 1  水位計 21 か所の水位の誤差(計算 − 計測。5 分平均で比べた RMSE と平均)
  表 2  移動床の河床変化の比較(相関・RMSE・BSS、区間ごとの正味の体積変化)
  表 3  表層の粒径集団の割合(移動床の平均)と、粒径集団 1 の割合の比較(相関・RMSE)
  表 4  画面出力の台帳(粒径階ごとの給砂・開境界の流出・在庫の変化)
  表 5  93 分の流速の大きさの比較(相関・RMSE・平均)
  表 6  感度の構成(下層 = 表層、下流端 = 固定床高)を基本の構成と 124 分で比べる(区間の正味の変化と表層の細粒の割合)
終わった計算の結果ディレクトリだけを扱う(9998 がないものは表と図から外す)。
依存: numpy, matplotlib(make_init.py の写し方を使う)
"""
import csv
import glob
import os
import re
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_init as mi  # noqa: E402

EN = len(sys.argv) > 1 and sys.argv[1] == "en"
FIGS = os.path.join(HERE, "en", "figs") if EN else os.path.join(HERE, "figs")
plt.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

RUNS = [("result", "混合粒径", "mixed sizes"),
        ("result_single", "単一粒径", "single size"),
        ("result_sub", "混合粒径(下層 = 表層)", "mixed (substrate = surface)"),
        ("result_outlet", "混合粒径(下流端 = 固定床高)", "mixed (outlet at base)")]
GAUGES_FIG = ["19.2k", "16.6k", "13.3k", "9.7k"]
REACHES = [(0, 500), (500, 1000), (1000, 1500), (1500, 2000), (2000, 2362)]
MAP_RUNS = ["result", "result_single"]          # 河床変化・流速の平面図に描く構成(感度の構成は縦断と数表で)
SURF_RUNS = ["result", "result_sub"]            # 表層の粒度の平面図に描く構成
QMIN = 5.0                      # 水位の比較に使う流量の下限 (L/s)。基底流量では水位計の多くが干上がる
I_CMP = 650                     # 17.1k(I = 651)。これより上流は計測の河床変化が厳密に 0 の点が多い(README)
BC = mi.read_csv("bc_2-1.csv.gz")


def L(ja, en):
    return en if EN else ja


def done_runs():
    return [(d, L(ja, en)) for d, ja, en in RUNS if os.path.exists(os.path.join(HERE, d, "Z9998.txt"))]


def load(d, name):
    return np.loadtxt(os.path.join(HERE, d, name))


def sections_dist():
    sec = mi.read_csv("sections.csv")
    o = np.argsort(sec["I"])
    return sec["I"][o] - 1.0, sec["dist"][o], sec["name"][o]


def main():
    os.makedirs(FIGS, exist_ok=True)
    g = mi.build(0.1)
    ras, mask, sd = g["ras"], g["mask"], g["sd"]
    nodes, mesh = g["nodes"], g["mesh"]
    A, B, S, T = g["A"], g["B"], g["S"], g["T"]
    mov = mask & (sd > 0) & (A >= 0)
    dz_meas = mi.interp_nodes(nodes["z240"], A, B, S, T) - mi.interp_nodes(nodes["z0"], A, B, S, T)
    f_meas0 = [mi.mesh_value(mesh["f%d_0" % k], A, B) / 100.0 for k in (1, 2, 3)]
    f_meas = [mi.mesh_value(mesh["f%d_240" % k], A, B) / 100.0 for k in (1, 2, 3)]
    si, sdist, sname = sections_dist()
    dist = np.interp(g["ipos"], si, sdist)
    ext = [ras.x0, ras.x0 + ras.nx * ras.dx, ras.y1 - ras.ny * ras.dx, ras.y1]
    runs = done_runs()

    # ---- 表 1: 水位 ----
    wl = mi.read_csv("wl_2-1.csv.gz")
    gauges = list(dict.fromkeys(wl["gauge"]))
    print("表 1  水位の誤差(計算 − 計測。5 分平均のうち流量 %g L/s 以上の時間。計算は水位計を中心とする 3 × 3 セルの"
          "濡れたセルの平均。mm)" % QMIN)
    print("%-8s" % "gauge" + "".join("%22s" % r[1][:20] for r in runs))
    wl_model = {}
    for d, lab in runs:
        wl_model[d] = {}
        for n, gname in enumerate(gauges):
            wl_model[d][gname] = gauge_level(d, n)
    for gname in gauges:
        sel = wl["gauge"] == gname
        tm, lv = wl["t_min"][sel], wl["level"][sel]
        line = "%-8s" % gname
        for d, lab in runs:
            t, e = wl_model[d][gname]
            err = []
            for t0 in range(5, 240, 5):
                if np.interp(t0, BC["t_min"], BC["q_lps"]) < QMIN:
                    continue
                a = (tm >= t0 - 2.5) & (tm < t0 + 2.5)
                b = (t >= t0 - 2.5) & (t < t0 + 2.5) & np.isfinite(e)
                if a.any() and b.any():
                    err.append(e[b].mean() - lv[a].mean())
            err = np.array(err) * 1000
            if err.size == 0:
                line += "%22s" % "—"
            else:
                line += "%22s" % ("%6.1f / %6.1f" % (np.sqrt((err ** 2).mean()), err.mean()))
        print(line)
    print("  (各欄: RMSE / 平均。mm。— は水位計を中心とする 3 × 3 セルが比べる時間に一度も濡れなかった水位計)")

    # ---- 表 2: 河床変化 ----
    print("\n表 2  移動床の河床変化 z(240 分) − z0 の比較(格子 10 cm のセル)")
    print("  計測: 平均 %.2f mm、標準偏差 %.2f mm" % (1000 * dz_meas[mov].mean(), 1000 * dz_meas[mov].std()))
    area = ras.dx ** 2
    print("%-22s %6s %7s %6s %6s %7s %6s" % ("", "corr", "RMSE", "BSS", "corr", "RMSE", "BSS")
          + "".join("  I%4d-%4d" % (a + 1, b) for a, b in REACHES))
    line = "%-22s %43s" % (L("計測", "measured"), "")
    for a, b in REACHES:
        s = mov & (g["ipos"] >= a) & (g["ipos"] < b)
        line += "  %9.1f" % (1000 * dz_meas[s].sum() * area)
    print(line)
    dz_model = {}
    down = mov & (g["ipos"] >= I_CMP)
    for d, lab in runs:
        dzm = load(d, "Z9998.txt") - load(d, "Z0000.txt")
        dz_model[d] = dzm
        line = "%-22s" % lab[:22]
        for sel in (mov, down):
            x, y = dzm[sel], dz_meas[sel]
            corr = np.corrcoef(x, y)[0, 1]
            rmse = np.sqrt(((x - y) ** 2).mean())
            bss = 1 - ((x - y) ** 2).sum() / (y ** 2).sum()
            line += " %6.3f %5.1fmm %6.3f" % (corr, 1000 * rmse, bss)
        for a, b in REACHES:
            s = mov & (g["ipos"] >= a) & (g["ipos"] < b)
            line += "  %9.1f" % (1000 * dzm[s].sum() * area)
        print(line)
    print("  (左の 3 列: 移動床の全体の相関・RMSE・BSS、次の 3 列: 17.1k より下流(I ≥ %d)の同じ値。"
          "BSS = 1 − Σ(計算 − 計測)² / Σ計測²。区間の欄: 正味の体積変化 L(かさ))" % (I_CMP + 1))
    up = mov & (g["ipos"] < I_CMP)
    print("  計測の河床変化が厳密に 0 のセルの割合: 17.1k より上流 %.1f %%、下流 %.1f %%"
          % (100 * np.mean(np.abs(dz_meas[up]) < 1e-9), 100 * np.mean(np.abs(dz_meas[down]) < 1e-9)))

    # ---- 表 3: 表層の粒度 ----
    print("\n表 3  表層の粒径集団の割合(移動床のセルの平均、%)と粒径集団 1 の割合の比較")
    print("%-22s %7s %7s %7s %8s %8s" % ("", "F1", "F2", "F3", "corr F1", "RMSE F1"))
    print("%-22s %7.1f %7.1f %7.1f" % (L("計測 0 分", "measured 0 min"), *[100 * np.nanmean(f[mov]) for f in f_meas0]))
    print("%-22s %7.1f %7.1f %7.1f" % (L("計測 240 分", "measured 240 min"), *[100 * np.nanmean(f[mov]) for f in f_meas]))
    fa_model = {}
    for d, lab in runs:
        if not os.path.exists(os.path.join(HERE, d, "Fa1_9998.txt")):
            continue
        fa = [load(d, "Fa%d_9998.txt" % k) for k in (1, 2, 3)]
        fa_model[d] = fa
        x, y = fa[0][mov], f_meas[0][mov]
        ok = np.isfinite(y)
        print("%-22s %7.1f %7.1f %7.1f %8.3f %8.3f" % (lab[:22], *[100 * f[mov].mean() for f in fa],
                                                    np.corrcoef(x[ok], y[ok])[0, 1], np.sqrt(((x[ok] - y[ok]) ** 2).mean())))

    # ---- 表 4: 台帳 ----
    print("\n表 4  画面出力の台帳(m3 固体)")
    for d, lab in runs:
        logs = glob.glob(os.path.join(HERE, "Screen_%s.log" % d))
        if not logs:
            continue
        txt = open(logs[0], encoding="utf-8", errors="replace").read()
        for m in re.finditer(r"ledger class (\d+) .*", txt):
            print("  %-20s %s" % (lab[:20], m.group(0)[:150]))
        for m in re.finditer(r"(net bed load out through open boundaries.*|class supply limiter.*|bedrock floor clip.*)", txt):
            print("  %-20s %s" % (lab[:20], m.group(0)[:150]))

    # ---- 図 ----
    fig_setup(g, ext, dist, si, sdist, sname)
    fig_waterlevel(wl, wl_model, runs)
    fig_bedchange(dz_meas, dz_model, runs, mov, mask, ext)
    fig_profile(dz_meas, dz_model, f_meas0, f_meas, fa_model, runs, mov, dist, g)
    fig_surface(f_meas0, f_meas, fa_model, runs, mov, mask, ext)
    velocity(ras, mask, runs, ext)
    sensitivity(g, mov, dz_meas, f_meas, area)


def gauge_level(d, n, hmin=0.002):
    """水位計 n(0 始まり)の 3 × 3 セルのうち、水深 hmin 以上のセルの水位 z + h の平均(濡れたセルがなければ nan)"""
    zs, hs = [], []
    for k in range(9):
        t, z, h = read_probe(os.path.join(HERE, d, "probes", "probe%04d.csv" % (9 * n + k + 1)), both=True)
        zs.append(z)
        hs.append(h)
    z, h = np.array(zs), np.array(hs)
    wet = h >= hmin
    cnt = wet.sum(0)
    e = np.where(cnt > 0, np.where(wet, z + h, 0.0).sum(0) / np.maximum(cnt, 1), np.nan)
    return t, e


def read_probe(path, both=False):
    """プローブの CSV(# 行の後に t(hour), t(min), z(m), h(m), ...)から時刻 (min) と水位 z + h"""
    t, e = [], []
    with open(path) as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            r = line.split(",")
            t.append(float(r[1]))
            e.append((float(r[2]), float(r[3])))
    t, e = np.array(t), np.array(e)
    if both:
        return t, e[:, 0], e[:, 1]
    return t, e[:, 0] + e[:, 1]


INK = "#333333"
MUTED = "#8a8a86"
COLORS = {"result": "#2a78d6", "result_single": "#eb6834", "result_sub": "#1baf7a", "result_outlet": "#eda100"}
NEUTRAL = "#f0efec"
BLUES = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#2a78d6", "#1c5cab", "#104281", "#0d366b"]
ORANGES = ["#fde2d6", "#f9c2aa", "#f3a07d", "#eb6834", "#c94e1d", "#9c3a12", "#6e270a"]


def cmap_seq(colors):
    from matplotlib.colors import LinearSegmentedColormap
    return LinearSegmentedColormap.from_list("seq", colors)


def cmap_div():
    from matplotlib.colors import LinearSegmentedColormap
    # 侵食(負)= 赤、堆積(正)= 青、0 = 灰
    return LinearSegmentedColormap.from_list("div", ["#7a1514", "#e34948", "#f4b3b2", NEUTRAL,
                                                     "#9ec5f4", "#2a78d6", "#0d366b"])


def map_axes(ax, ext):
    ax.set_xlim(ext[0], ext[1])
    ax.set_ylim(ext[2], ext[3])
    ax.set_aspect("equal")
    ax.tick_params(labelsize=8, color=MUTED)
    for s in ax.spines.values():
        s.set_color(MUTED)


def show(ax, a, ext, mask, **kw):
    im = ax.imshow(np.where(mask, a, np.nan), extent=ext, interpolation="nearest", **kw)
    return im


def fig_setup(g, ext, dist, si, sdist, sname):
    ras, mask = g["ras"], g["mask"]
    fig, axs = plt.subplots(3, 1, figsize=(12, 7.2), constrained_layout=True)
    sec = mi.read_csv("sections.csv")
    o = np.argsort(sec["I"])
    zref = np.interp(g["ipos"], sec["I"][o] - 1.0, sec["zbank"][o])
    im = show(axs[0], g["z"] - zref, ext, mask, cmap=cmap_seq(BLUES[::-1]), vmin=-0.1, vmax=0.15)
    fig.colorbar(im, ax=axs[0], shrink=0.8, label=L("起伏 (m)", "relief (m)"))
    wl = mi.read_csv("wl_2-1.csv.gz")
    names = list(dict.fromkeys(wl["gauge"]))
    for gname in names:
        k = np.nonzero(wl["gauge"] == gname)[0][0]
        axs[0].plot(wl["x"][k], wl["y"][k], "o", ms=4, mfc="white", mec=INK, mew=1)
        if gname in GAUGES_FIG:
            axs[0].annotate(gname, (wl["x"][k], wl["y"][k]), xytext=(0, -13), textcoords="offset points",
                            ha="center", fontsize=8, color=INK)
    cells = np.loadtxt(os.path.join(HERE, "inflow_cells.txt"))
    axs[0].plot(ras.x0 + (cells[:, 0] - 0.5) * ras.dx, ras.y1 - (cells[:, 1] - 0.5) * ras.dx, "s", ms=2, color="#eb6834")
    axs[0].annotate(L("流入", "inflow"), (ras.x0 + ras.nx * ras.dx, ras.y1 - cells[:, 1].mean() * ras.dx),
                    xytext=(-30, 18), textcoords="offset points", fontsize=8, color=INK,
                    arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    axs[0].set_title(L("(a) 初期の河床の起伏(断面の低水路平均河床高から)と水位計(○)", "(a) initial bed relief (above the section mean bed) and water-level gauges (○)"), fontsize=10, loc="left")
    im = show(axs[1], np.where(g["sd"] > 0, g["sd"], np.nan), ext, mask, cmap=cmap_seq(ORANGES), vmin=0, vmax=0.25)
    axs[1].imshow(np.where(mask & (g["sd"] <= 0), 1.0, np.nan), extent=ext, cmap=cmap_seq([NEUTRAL, NEUTRAL]), interpolation="nearest")
    fig.colorbar(im, ax=axs[1], shrink=0.8, label=L("移動層厚 (m)", "movable-layer thickness (m)"))
    axs[1].set_title(L("(b) 移動層の厚さ(灰色は固定床: 高水敷・床固め・流入部)",
                       "(b) movable-layer thickness (gray: fixed bed - floodplains, sills, inlet)"), fontsize=10, loc="left")
    mov = mask & (g["sd"] > 0)
    im = show(axs[2], g["fa"][0], ext, mov, cmap=cmap_seq(BLUES), vmin=0, vmax=1)
    fig.colorbar(im, ax=axs[2], shrink=0.8, label=L("割合", "fraction"))
    axs[2].set_title(L("(c) 初期の表層の細粒(粒径集団 1、0.57 mm)の割合(計測)",
                       "(c) initial surface fraction of the fine group (group 1, 0.57 mm), measured"), fontsize=10, loc="left")
    for ax in axs:
        map_axes(ax, ext)
        ax.set_ylabel("y (m)", fontsize=8)
    axs[2].set_xlabel("x (m)", fontsize=8)
    fig.savefig(os.path.join(FIGS, "setup.png"), dpi=150)
    plt.close(fig)


def fig_waterlevel(wl, wl_model, runs):
    bc = mi.read_csv("bc_2-1.csv.gz")
    fig, axs = plt.subplots(1 + len(GAUGES_FIG), 1, figsize=(10, 9), sharex=True, constrained_layout=True,
                            gridspec_kw=dict(height_ratios=[1.2] + [1] * len(GAUGES_FIG)))
    axs[0].plot(bc["t_min"], bc["q_lps"], lw=1, color=INK)
    axs[0].set_ylabel(L("流量 (L/s)", "discharge (L/s)"), fontsize=9)
    axs[0].set_title(L("上流端の流量(計測)", "upstream discharge (measured)"), fontsize=10, loc="left")
    for ax, gname in zip(axs[1:], GAUGES_FIG):
        s = wl["gauge"] == gname
        tm, lv = wl["t_min"][s], wl["level"][s]
        tb = np.arange(0.5, 240.0, 1.0)
        lm = np.array([lv[(tm >= c - 0.5) & (tm < c + 0.5)].mean() if ((tm >= c - 0.5) & (tm < c + 0.5)).any() else np.nan
                       for c in tb])
        ax.plot(tb, lm, lw=1.4, color=INK, label=L("計測(1 分平均)", "measured (1-min mean)"))
        for d, lab in runs:
            t, e = wl_model[d][gname]
            ax.plot(t, e, lw=1.2, color=COLORS[d], label=lab)
        ax.set_ylabel(L("水位 (m)", "water level (m)"), fontsize=9)
        ax.set_title(L("水位計 %s", "gauge %s") % gname, fontsize=10, loc="left")
    axs[1].legend(fontsize=8, frameon=False, ncol=3, loc="upper right")
    axs[-1].set_xlabel(L("時間 (分)", "time (min)"), fontsize=9)
    for ax in axs:
        ax.grid(color="#e6e5e1", lw=0.6)
        ax.tick_params(labelsize=8)
        ax.set_xlim(0, 240)
    fig.savefig(os.path.join(FIGS, "waterlevel.png"), dpi=150)
    plt.close(fig)


def fig_bedchange(dz_meas, dz_model, runs, mov, mask, ext):
    runs = [(d, lab) for d, lab in runs if d in MAP_RUNS]
    n = 1 + len(runs)
    fig, axs = plt.subplots(n, 1, figsize=(12, 2.3 * n + 0.6), constrained_layout=True, squeeze=False)
    axs = axs[:, 0]
    kw = dict(cmap=cmap_div(), vmin=-0.03, vmax=0.03)
    panels = [(dz_meas, L("計測", "measured"))] + [(dz_model[d], lab) for d, lab in runs]
    for k, (ax, (a, lab)) in enumerate(zip(axs, panels)):
        ax.imshow(np.where(mask & ~mov, 1.0, np.nan), extent=ext, cmap=cmap_seq([NEUTRAL, NEUTRAL]), interpolation="nearest")
        im = show(ax, a, ext, mov, **kw)
        ax.set_title("(%s) %s" % ("abcdefg"[k], lab), fontsize=10, loc="left")
        map_axes(ax, ext)
        ax.set_ylabel("y (m)", fontsize=8)
    axs[-1].set_xlabel("x (m)", fontsize=8)
    fig.colorbar(im, ax=axs, shrink=0.6, label=L("河床変化 z − z0 (m)(赤 = 侵食、青 = 堆積)",
                                                 "bed change z − z0 (m) (red = erosion, blue = deposition)"))
    fig.savefig(os.path.join(FIGS, "bedchange.png"), dpi=150)
    plt.close(fig)


def binned(dist, val, sel, edges):
    k = np.digitize(dist[sel], edges) - 1
    v = val[sel]
    out = np.full(len(edges) - 1, np.nan)
    for b in range(len(edges) - 1):
        s = (k == b) & np.isfinite(v)
        if s.sum() >= 5:
            out[b] = v[s].mean()
    return out


def fig_profile(dz_meas, dz_model, f_meas0, f_meas, fa_model, runs, mov, dist, g):
    edges = np.arange(0.0, 118.0, 2.0)
    xc = 0.5 * (edges[:-1] + edges[1:])
    sel = mov & g["in_low"]
    fig, axs = plt.subplots(3, 1, figsize=(11, 8.4), sharex=True, constrained_layout=True)
    axs[0].axhline(0, color=MUTED, lw=0.8)
    axs[0].plot(xc, 1000 * binned(dist, dz_meas, sel, edges), lw=1.8, color=INK, label=L("計測", "measured"))
    for d, lab in runs:
        axs[0].plot(xc, 1000 * binned(dist, dz_model[d], sel, edges), lw=1.3, color=COLORS[d], label=lab)
    axs[0].set_ylabel(L("河床変化 (mm)", "bed change (mm)"), fontsize=9)
    ylo, yhi = -40.0, 20.0
    axs[0].set_ylim(ylo, yhi)
    for line in axs[0].get_lines():
        yv = np.asarray(line.get_ydata(), dtype=float)
        xv = np.asarray(line.get_xdata(), dtype=float)
        if yv.size == xc.size:
            for xx, yy in zip(xv, yv):
                if np.isfinite(yy) and yy < ylo:
                    axs[0].annotate("%.0f" % yy, (xx, ylo), xytext=(0, 4), textcoords="offset points", ha="center",
                                    fontsize=7, color=line.get_color())
    axs[0].set_title(L("(a) 低水路の移動床の河床変化(縦断 2 m ごとの平均)", "(a) bed change of the movable low-water channel (2 m bins)"), fontsize=10, loc="left")
    axs[0].legend(fontsize=8, frameon=False, ncol=3)
    for ax, k, name in ((axs[1], 0, L("細粒(粒径集団 1)", "fine (group 1)")), (axs[2], 2, L("粗粒(粒径集団 3)", "coarse (group 3)"))):
        ax.plot(xc, 100 * binned(dist, f_meas0[k], sel, edges), lw=1.0, ls="--", color=MUTED, label=L("計測 0 分", "measured 0 min"))
        ax.plot(xc, 100 * binned(dist, f_meas[k], sel, edges), lw=1.8, color=INK, label=L("計測 240 分", "measured 240 min"))
        for d, lab in runs:
            if d in fa_model:
                ax.plot(xc, 100 * binned(dist, fa_model[d][k], sel, edges), lw=1.3, color=COLORS[d], label=lab)
        ax.set_ylabel(L("表層の割合 (%)", "surface fraction (%)"), fontsize=9)
        ax.set_title("(%s) %s" % ("bc"[k // 2], name), fontsize=10, loc="left")
    axs[1].legend(fontsize=8, frameon=False, ncol=3)
    axs[-1].set_xlabel(L("下流端(8.4k)からの距離 (m)", "distance from the downstream end, 8.4k (m)"), fontsize=9)
    sec = mi.read_csv("sections.csv")
    d171 = float(sec["dist"][sec["name"] == "17.1k"][0])
    for ax in axs:
        ax.grid(color="#e6e5e1", lw=0.6)
        ax.tick_params(labelsize=8)
        ax.set_xlim(0, 117)
        ax.invert_xaxis()
        ax.axvline(d171, color=MUTED, lw=0.8, ls=":")
    axs[0].annotate(L("17.1k(上流は計測の変化が 0 の点が多い)", "17.1k (upstream: many points with zero measured change)"),
                    (d171, axs[0].get_ylim()[1]), xytext=(4, -12), textcoords="offset points", fontsize=8, color=INK)
    fig.savefig(os.path.join(FIGS, "profile.png"), dpi=150)
    plt.close(fig)


def sensitivity(g, mov, dz_meas, f_meas, area, frame=4):
    """表 6: 感度の構成を基本の構成と同じ時刻(フレーム 0004 = 124 分)で比べる(240 分までの計算がなくても比べられる)"""
    cand = [("result", L("混合粒径(基本)", "mixed sizes (base)")),
            ("result_sub", L("下層 = 表層", "substrate = surface")),
            ("result_outlet", L("下流端 = 固定床高", "outlet at base")),
            ("result_single", L("単一粒径", "single size"))]
    rows = [(d, lab) for d, lab in cand if os.path.exists(os.path.join(HERE, d, "Z%04d.txt" % frame))]
    if not rows:
        return
    print("\n表 6  感度の構成の 124 分(フレーム %04d)の比較(区間の正味の体積変化 L(かさ)と、移動床の表層の細粒の割合の平均)"
          % frame)
    print("%-22s" % "" + "".join("  I%4d-%4d" % (a + 1, b) for a, b in REACHES) + "   F1 (%)")
    for d, lab in rows:
        dz = load(d, "Z%04d.txt" % frame) - load(d, "Z0000.txt")
        line = "%-22s" % lab[:22]
        for a, b in REACHES:
            s = mov & (g["ipos"] >= a) & (g["ipos"] < b)
            line += "  %9.1f" % (1000 * dz[s].sum() * area)
        fa = os.path.join(HERE, d, "Fa1_%04d.txt" % frame)
        line += "   %6.1f" % (100 * np.loadtxt(fa)[mov].mean()) if os.path.exists(fa) else "        —"
        print(line)
    line = "%-22s" % L("計測 240 分(参考)", "measured 240 min (ref.)")
    for a, b in REACHES:
        s = mov & (g["ipos"] >= a) & (g["ipos"] < b)
        line += "  %9.1f" % (1000 * dz_meas[s].sum() * area)
    print(line + "   %6.1f" % (100 * np.nanmean(f_meas[0][mov])))
    print("  (計算は 124 分、計測は 240 分で時刻が違う。構成どうしの違いを見る表)")


def velocity(ras, mask, runs, ext):
    """表 5 と figs/velocity.png: 93 分(フレーム 0003)の流速の大きさを計測の点と比べる"""
    vel = mi.read_csv("vel_2-1.csv.gz")
    sm = np.hypot(vel["u"], vel["v"])
    ix = np.floor((vel["x"] - ras.x0) / ras.dx).astype(int)
    iy = np.floor((ras.y1 - vel["y"]) / ras.dx).astype(int)
    ok = (ix >= 0) & (ix < ras.nx) & (iy >= 0) & (iy < ras.ny)
    print("\n表 5  93 分の流速の大きさ(計測の点を含むセル。計測 > 0.05 m/s かつ計算の水深 >= 2 mm の点)")
    print("%-22s %8s %8s %9s %9s %7s" % ("", "points", "corr", "RMSE", "mean", "meas."))
    spd = {}
    for d, lab in runs:
        f = [os.path.join(HERE, d, n % 3) for n in ("u%04d.txt", "v%04d.txt", "H%04d.txt")]
        if not all(os.path.exists(p) for p in f):
            continue
        u, v, h = (np.loadtxt(p) for p in f)
        s = np.hypot(u, v)
        spd[d] = np.where(h >= 0.002, s, np.nan)
        sel = ok.copy()
        sel[ok] &= (sm[ok] > 0.05) & (h[iy[ok], ix[ok]] >= 0.002)
        a, b = s[iy[sel], ix[sel]], sm[sel]
        print("%-22s %8d %8.3f %7.3fm/s %7.3fm/s %7.3f" % (lab[:22], sel.sum(), np.corrcoef(a, b)[0, 1],
                                                         np.sqrt(((a - b) ** 2).mean()), a.mean(), b.mean()))
    spd = {d: s for d, s in spd.items() if d in MAP_RUNS}
    if not spd:
        return
    n = 1 + len(spd)
    fig, axs = plt.subplots(n, 1, figsize=(12, 2.3 * n + 0.6), constrained_layout=True, squeeze=False)
    axs = axs[:, 0]
    kw = dict(cmap=cmap_seq(BLUES), vmin=0, vmax=0.8)
    for ax in axs:
        ax.imshow(np.where(mask, 1.0, np.nan), extent=ext, cmap=cmap_seq([NEUTRAL, NEUTRAL]), interpolation="nearest")
    im = axs[0].scatter(vel["x"][ok], vel["y"][ok], c=sm[ok], s=0.4, linewidths=0, **kw)
    axs[0].set_title(L("(a) 計測(93 分)", "(a) measured (93 min)"), fontsize=10, loc="left")
    for k, (d, lab) in enumerate([(d, lab) for d, lab in runs if d in spd]):
        im = axs[k + 1].imshow(spd[d], extent=ext, interpolation="nearest", **kw)
        axs[k + 1].set_title("(%s) %s" % ("bcdef"[k], lab + L("(93 分)", " (93 min)")), fontsize=10, loc="left")
    for ax in axs:
        map_axes(ax, ext)
        ax.set_ylabel("y (m)", fontsize=8)
    axs[-1].set_xlabel("x (m)", fontsize=8)
    fig.colorbar(im, ax=axs, shrink=0.6, label=L("流速の大きさ (m/s)", "speed (m/s)"))
    fig.savefig(os.path.join(FIGS, "velocity.png"), dpi=150)
    plt.close(fig)


def fig_surface(f_meas0, f_meas, fa_model, runs, mov, mask, ext):
    mixed = [(d, lab) for d, lab in runs if d in fa_model and d in SURF_RUNS]
    n = 2 + len(mixed)
    fig, axs = plt.subplots(n, 1, figsize=(12, 2.3 * n + 0.6), constrained_layout=True, squeeze=False)
    axs = axs[:, 0]
    panels = [(f_meas0[0], L("計測 0 分", "measured 0 min")), (f_meas[0], L("計測 240 分", "measured 240 min"))] + \
             [(fa_model[d][0], lab + L(" 240 分", " 240 min")) for d, lab in mixed]
    for k, (ax, (a, lab)) in enumerate(zip(axs, panels)):
        ax.imshow(np.where(mask & ~mov, 1.0, np.nan), extent=ext, cmap=cmap_seq([NEUTRAL, NEUTRAL]), interpolation="nearest")
        im = show(ax, a, ext, mov, cmap=cmap_seq(BLUES), vmin=0, vmax=1)
        ax.set_title("(%s) %s" % ("abcdefg"[k], lab), fontsize=10, loc="left")
        map_axes(ax, ext)
        ax.set_ylabel("y (m)", fontsize=8)
    axs[-1].set_xlabel("x (m)", fontsize=8)
    fig.colorbar(im, ax=axs, shrink=0.6, label=L("表層の細粒(粒径集団 1)の割合", "surface fraction of the fine group (group 1)"))
    fig.savefig(os.path.join(FIGS, "surface.png"), dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
