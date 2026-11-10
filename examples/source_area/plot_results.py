#!/usr/bin/env python3
"""source_area の図と数表(事前に make run。比較の図と表は make sweep の結果も使う)。

  figs/mechanism.png    3 つの計算(過程計算・浸透なし・鉛直浸透のみ)の違いの模式図(データを使わない)
  figs/setup.png        集水域の位置、地形と河道、降雨
  figs/source_area.png  土層の飽和度と飽和域(流出寄与域)の分布の時間変化(過程計算)
  figs/series.png       過程計算の流出、飽和域の割合、貯留、積算の雨と流出
  figs/compare.png      過程計算と、浸透なし・鉛直浸透のみのハイドログラフ
  figs/roughness.png    浸透なしの計算の斜面の粗度と、ピーク・立ち上がり・適合度
引数 en で英語ラベル版を en/figs/ に描く(データと描画処理は共通)。
数表(README の表)は標準出力に書く。計算が済んでいないケースは飛ばす。
"""
import os
import re
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource, ListedColormap, LinearSegmentedColormap
from matplotlib.patches import Patch, Polygon, FancyArrowPatch
from matplotlib.lines import Line2D

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)

# ---------------------------------------------------------------- 色と線(役割ごとに固定)
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"      # 文字・過程計算の線
GRID, AXIS = "#e1e0d9", "#c3c2b7"
BLUE, BLUE_D = "#2a78d6", "#1c5cab"                      # 土層の水・飽和域
RAINC = "#d9d7d0"                                        # 雨(淡い面)
S_RAMP = {0.3: "#f8986c", 1.0: "#ed7940", 3.0: "#d75e16", 5.0: "#b84800", 10.0: "#923400",
          30.0: "#662703"}                               # 浸透なし(粗度の順。1 色相の明→暗)
V_RAMP = {0.3: "#1baf7a", 3.0: "#0d6e4c"}                # 鉛直浸透のみ
matplotlib.rcParams.update({
    "axes.edgecolor": AXIS, "axes.linewidth": 0.8, "axes.labelcolor": INK2, "axes.titlesize": 10,
    "axes.labelsize": 9, "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelcolor": INK2,
    "ytick.labelcolor": INK2, "xtick.labelsize": 8.5, "ytick.labelsize": 8.5, "grid.color": GRID,
    "grid.linewidth": 0.6, "axes.grid": True, "axes.axisbelow": True, "axes.spines.top": False,
    "axes.spines.right": False, "legend.frameon": False, "legend.fontsize": 8.5, "text.color": INK,
    "lines.linewidth": 1.8, "lines.solid_capstyle": "round", "figure.facecolor": "white",
    "savefig.facecolor": "white", "savefig.dpi": 150})

# ---------------------------------------------------------------- 入力と設定
SRC = "../../test/chichibu/data_chichibu_50m"
DX = 50.0
KM = DX / 1000.0


def read_info():
    d = {}
    for line in open("data/catchment.txt", encoding="utf-8"):
        if "=" in line:
            k, v = line.split("=", 1)
            d[k.strip()] = v.strip()
    return d


INFO = read_info()
NX, NY = int(INFO["nx"]), int(INFO["ny"])
MASK = np.loadtxt("data/mask.txt") > 0
RW = np.loadtxt("data/rw.txt") > 0
Z = np.loadtxt("data/z.txt")
ACC = np.loadtxt("data/acc.txt")
NCELL = int(MASK.sum())
AREA = NCELL * DX * DX                       # 集水域の面積 (m2)
EXT = [0, NX * KM, 0, NY * KM]               # x 東向き、y 北向き (km)。行 1 が北端
OUTLET = tuple(int(v) for v in INFO["outlet_ij"].split())
GAUGE = tuple(int(v) for v in INFO["gauge_ij"].split())


def param_value(fn, key):
    m = re.search(rf"^\s*{key}\s*=\s*([-+0-9.eE]+)", open(fn, encoding="utf-8").read(), re.M)
    return float(m.group(1))


CAP = param_value("param.txt", "sd0") * param_value("param.txt", "sy0")    # 土層の容量 (m)
SAT_TOL = 1.0e-4                             # 飽和の判定: 容量との差が 0.1 mm 以内
TEND = 96.0
CYCLE = 48.0                                 # 雨 1 回分の区間(雨 12 時間 + 36 時間)


def rain_series():
    """param_common.txt の prval(時刻 min, mm/h)を読む。点の間は直線補間。"""
    txt = open("param_common.txt", encoding="utf-8").read()
    pts = re.findall(r"^\s*prval\(:,\s*\d+\)\s*=\s*([-0-9.]+)\s*,\s*([-0-9.]+)", txt, re.M)
    a = np.array([[float(t) / 60.0, float(v)] for t, v in pts])
    return a[:, 0], a[:, 1]


RT, RV = rain_series()


def rain(t):
    return np.interp(t, RT, RV)


STORMS = [(RT[i], RT[i + 1]) for i in range(len(RT) - 1) if RV[i] > 0 and RV[i + 1] > 0]   # 雨の開始・終了 (h)
RAIN_MMH = RV.max()

# ケース名 → (結果のディレクトリ, 種類, 斜面の粗度, 拡散波か)
CASES = {
    "process": ("result_process", "P", 0.3, False),
    "surface": ("result_surface", "S", 0.3, False),
    "vertical": ("result_vertical", "V", 0.3, False),
    "surface_n1": ("result_sweep_surface_n1", "S", 1.0, False),
    "surface_n3": ("result_sweep_surface_n3", "S", 3.0, False),
    "surface_n5": ("result_sweep_surface_n5", "S", 5.0, False),
    "surface_n10": ("result_sweep_surface_n10", "S", 10.0, False),
    "surface_n30": ("result_sweep_surface_n30", "S", 30.0, False),
    "surface_dif_n03": ("result_sweep_surface_dif_n03", "S", 0.3, True),
    "surface_dif_n3": ("result_sweep_surface_dif_n3", "S", 3.0, True),
    "surface_dif_n10": ("result_sweep_surface_dif_n10", "S", 10.0, True),
    "vertical_n3": ("result_sweep_vertical_n3", "V", 3.0, False),
    "process_n1": ("result_sweep_process_n1", "P", 1.0, False),
    "process_dif": ("result_sweep_process_dif", "P", 0.3, True),
    "process_k10000": ("result_sweep_process_k10000", "P", 0.3, False),
    "process_sd1": ("result_sweep_process_sd1", "P", 0.3, False),
}


def rdir(case):
    return CASES[case][0]


def hydro(case):
    """測線 1 の流量を流出高にして返す: 時刻 (h)、流出高 (mm/h)。"""
    a = np.loadtxt(f"{rdir(case)}/fluxes/flux0001.csv", delimiter=",", comments="#")
    return a[:, 0], a[:, 2] / AREA * 3.6e6


def have(case):
    f = f"{rdir(case)}/fluxes/flux0001.csv"
    if not os.path.exists(f):
        return False
    rows = [line for line in open(f) if line.strip() and not line.startswith("#")]
    return len(rows) > 1 and float(rows[-1].split(",")[0]) >= TEND - 1e-6


def logtab(case):
    """Log.txt の表: 時刻 (h) と各列(地下水ありは S_surf・S_grnd・S_total (m)、なしは S (m) …)。"""
    rows = []
    for line in open(f"{rdir(case)}/Log.txt"):
        p = line.split()
        if len(p) > 4 and p[0].count(":") == 2:
            h, m, s = p[0].split(":")
            rows.append([int(h) + int(m) / 60.0 + float(s) / 3600.0] + [float(x.rstrip("%")) for x in p[1:]])
    return np.array(rows)


def bil(case, var, k):
    return np.fromfile(f"{rdir(case)}/{var}{k:04d}.bil", dtype="<f4").reshape(NY, NX).astype(float)


def file_times(case):
    """分布ファイルの番号と時刻 (h)。"""
    out = []
    for line in open(f"{rdir(case)}/FILENUMBER.csv"):
        p = [x.strip() for x in line.split(",")]
        if p[0].isdigit() and int(p[0]) < 9000:
            out.append((int(p[0]), float(p[2]) / 3600.0))
    return out


def case_cap(case):
    """そのケースの土層の容量 (m)。結果のディレクトリに写された設定から読む。"""
    for fn in sorted(os.listdir(rdir(case))):
        if fn.startswith("param") and fn.endswith(".txt") and fn != "param_common.txt":
            return param_value(f"{rdir(case)}/{fn}", "sd0") * param_value(f"{rdir(case)}/{fn}", "sy0")
    return CAP


def sat_series(case):
    """飽和域(地下貯留が土層の容量に達したセル)の割合の時系列。"""
    cap = case_cap(case)
    ts, fr = [], []
    for k, t in file_times(case):
        hg = bil(case, "Hg", k)
        ts.append(t)
        fr.append(float((hg[MASK] >= cap - SAT_TOL).mean()))
    return np.array(ts), np.array(fr)


def cum(t, q):
    """台形則の積算 (mm)。"""
    return np.concatenate([[0.0], np.cumsum(0.5 * (q[1:] + q[:-1]) * np.diff(t))])


def event(t, q, t0):
    """雨 1 回分(t0 から 48 時間)の指標。時刻は雨の開始から。"""
    k = (t >= t0 - 1e-9) & (t <= t0 + CYCLE + 1e-9)
    tt, qq = t[k] - t0, q[k]
    ip = int(np.argmax(qq))
    over = np.where(qq >= 1.0)[0]
    return dict(peak=qq[ip], tpeak=tt[ip], onset=(tt[over[0]] if len(over) else np.nan),
                vol=float(np.sum(0.5 * (qq[1:] + qq[:-1]) * np.diff(tt))), q24=float(np.interp(24.0, tt, qq)))


def nse(t, q, qref, t0):
    k = (t >= t0 - 1e-9) & (t <= t0 + CYCLE + 1e-9)
    return 1.0 - np.sum((q[k] - qref[k]) ** 2) / np.sum((qref[k] - qref[k].mean()) ** 2)


def xy(ij):
    """セル番号 (i, j)(1 始まり、j は北から)をセル中心の (x, y) km(y は北向き)に。"""
    return (ij[0] - 0.5) * KM, (NY - ij[1] + 0.5) * KM


def shade_storms(ax, label=False):
    """雨の時間帯を淡い帯で示す(軸の単位が mm/h でない図用)。"""
    for n, (a, b) in enumerate(STORMS):
        ax.axvspan(a, b, color=RAINC, alpha=0.45, lw=0, zorder=0,
                   label=(T("雨の時間帯", "rain period") if (label and n == 0) else None))


def rain_fill(ax, label=True):
    """雨を流出高と同じ mm/h の軸に淡い面で描く。"""
    t = np.linspace(0.0, TEND, 5761)
    ax.fill_between(t, 0.0, rain(t), color=RAINC, lw=0, zorder=1,
                    label=T("雨", "rain") if label else None)


def time_axis(ax, label=True):
    ax.set_xlim(0, TEND)
    ax.set_xticks(np.arange(0, TEND + 1, 12))
    if label:
        ax.set_xlabel(T("時刻 (h)", "time (h)"))


def panel_label(ax, s, x=0.0, y=1.03):
    ax.text(x, y, s, transform=ax.transAxes, fontsize=10, color=INK, ha="left", va="bottom")


# ================================================================ 模式図
def fig_mechanism():
    fig, axs = plt.subplots(1, 3, figsize=(13.2, 3.25))
    xs = np.linspace(0.0, 8.6, 200)
    d = 0.75                                               # 土層厚(図の単位)

    def surf(x):
        return 0.75 + 3.4 * ((8.6 - x) / 8.6) ** 1.35

    def arrow(ax, p0, p1, color, lw=1.4, ms=9):
        ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=ms, lw=lw, color=color,
                                     shrinkA=0, shrinkB=0, zorder=6))

    def base(ax, soil=True):
        ys = surf(xs)
        ax.add_patch(Polygon(np.r_[np.c_[xs, ys - (d if soil else 0.0)], [[8.6, 0.0], [0.0, 0.0]]],
                             closed=True, fc="#cfcdc6", ec="none", zorder=1))          # 基岩
        if soil:
            ax.add_patch(Polygon(np.r_[np.c_[xs, ys], np.c_[xs[::-1], ys[::-1] - d]], closed=True,
                                 fc="#efe6d4", ec="none", zorder=2))                   # 土層
        ax.plot(xs, ys, color=INK2, lw=1.0, zorder=5)
        ax.add_patch(Polygon([[8.6, 0.0], [8.6, 0.75], [10.0, 0.75], [10.0, 0.0]], closed=True,
                             fc="#cfcdc6", ec="none", zorder=1))
        ax.add_patch(Polygon([[8.6, 0.75], [8.6, 1.02], [10.0, 1.02], [10.0, 0.75]], closed=True,
                             fc=BLUE, ec="none", alpha=0.85, zorder=3))                # 河道の水
        ax.text(9.3, 0.36, T("河道", "channel"), ha="center", va="center", fontsize=8.5, color=INK2)
        for x in (1.0, 2.9, 4.8, 6.7, 8.2):                                            # 雨
            arrow(ax, (x, surf(x) + 1.25), (x, surf(x) + 0.42), MUTED, lw=1.1, ms=8)
        ax.text(0.25, surf(0.0) + 0.95, T("雨", "rain"), fontsize=9, color=INK2, ha="left")
        ax.set_xlim(-0.1, 10.1)
        ax.set_ylim(0.0, 5.75)
        ax.set_aspect("equal")
        ax.axis("off")

    # (a) 過程計算
    ax = axs[0]
    base(ax)
    ys = surf(xs)
    hw = d * np.clip((xs / 6.3) ** 1.8, 0.0, 1.0)                                      # 飽和帯厚
    ax.add_patch(Polygon(np.r_[np.c_[xs, ys - d + hw], np.c_[xs[::-1], ys[::-1] - d]], closed=True,
                         fc="#86b6ef", ec="none", zorder=3))
    ax.plot(xs, ys - d + hw, color=BLUE_D, lw=1.0, zorder=4)
    ksat = xs >= 6.3
    ax.plot(xs[ksat], ys[ksat] + 0.05, color=BLUE, lw=3.0, zorder=5, solid_capstyle="butt")   # 飽和域の地表の水
    for x in (1.0, 2.9, 4.8):                                                          # 浸透
        arrow(ax, (x, surf(x) - 0.05), (x, surf(x) - 0.45), BLUE_D, lw=1.0, ms=7)
    for x0 in (2.2, 4.1, 5.8):                                                         # 側方流
        x1 = x0 + 0.9
        arrow(ax, (x0, surf(x0) - d + 0.14), (x1, surf(x1) - d + 0.14), BLUE_D, lw=1.2, ms=8)
    arrow(ax, (7.2, surf(7.2) - 0.42), (7.2, surf(7.2) + 0.02), BLUE_D, lw=1.2, ms=8)     # 復帰流
    arrow(ax, (7.5, surf(7.5) + 0.22), (8.5, surf(8.5) + 0.22), BLUE, lw=1.4, ms=9)       # 飽和域の地表流
    ax.annotate(T("浸透", "infiltration"), (2.9, surf(2.9) - 0.25), (3.3, surf(2.9) + 1.5), fontsize=8.5,
                color=INK2, ha="left", arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6))
    ax.annotate(T("土層の側方流", "lateral flow in the soil"), (4.5, surf(4.5) - d + 0.12), (0.2, 0.45),
                fontsize=8.5, color=INK2, ha="left", arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6))
    ax.annotate(T("飽和域(流出寄与域)\n雨がしみ込めず地表を流れ、\n地下水も湧き出す",
                  "saturated area (source area):\nrain cannot infiltrate and runs off;\ngroundwater seeps out"),
                (7.4, surf(7.4) + 0.12), (5.1, 3.95), fontsize=8.5, color=INK2, ha="left", va="bottom",
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6))
    panel_label(ax, T("(a) 過程計算: 浸透 → 側方流 → 飽和域 → 河道",
                      "(a) Process run"), y=0.93)

    # (b) 浸透なし
    ax = axs[1]
    base(ax, soil=False)
    ax.plot(xs, surf(xs) + 0.06, color=BLUE, lw=3.0, zorder=5, solid_capstyle="butt")
    for x0 in (1.4, 3.6, 5.8, 7.5):
        x1 = x0 + 1.0
        arrow(ax, (x0, surf(x0) + 0.24), (x1, surf(x1) + 0.24), BLUE, lw=1.4, ms=9)
    ax.text(0.3, 0.42, T("しみ込まない", "no infiltration"), fontsize=8.5, color=INK2, ha="left")
    ax.annotate(T("雨の全量が地表を流れる。\n遅らせるのは斜面の粗度 n だけ",
                  "all rain flows over the surface;\nonly the slope roughness n delays it"),
                (5.2, surf(5.2) + 0.12), (4.6, 3.95), fontsize=8.5, color=INK2, ha="left", va="bottom",
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6))
    panel_label(ax, T("(b) 浸透なし: 雨 → 地表流(粗度 n)→ 河道",
                      "(b) No infiltration (overland flow only)"), y=0.93)

    # (c) 鉛直浸透のみ
    ax = axs[2]
    base(ax)
    ys = surf(xs)
    ax.add_patch(Polygon(np.r_[np.c_[xs, ys - d + 0.45 * d], np.c_[xs[::-1], ys[::-1] - d]], closed=True,
                         fc="#86b6ef", ec="none", zorder=3))
    ax.plot(xs, ys - d + 0.45 * d, color=BLUE_D, lw=1.0, zorder=4)
    for x in np.arange(0.86, 8.6, 0.86):                                               # セルの仕切り
        ax.plot([x, x], [surf(x) - d, surf(x)], color=INK2, lw=0.7, zorder=5)
    for x in (1.0, 2.9, 4.8, 6.7):
        arrow(ax, (x, surf(x) - 0.05), (x, surf(x) - 0.38), BLUE_D, lw=1.0, ms=7)
    ax.annotate(T("土層の水は横へ動かない。\nどのセルも同じ速さで貯まり、\n満ちるまで流出しない",
                  "soil water does not move sideways;\nevery cell fills at the same rate,\nno runoff until full"),
                (4.3, surf(4.3) - d + 0.2), (4.6, 3.75), fontsize=8.5, color=INK2, ha="left", va="bottom",
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6))
    panel_label(ax, T("(c) 鉛直浸透のみ: 浸透 → 各セルの土層に貯まる",
                      "(c) Vertical infiltration only"), y=0.93)

    fig.subplots_adjust(left=0.005, right=0.995, top=0.995, bottom=0.005, wspace=0.02)
    fig.savefig(f"{FIGDIR}/mechanism.png")
    plt.close(fig)


# ================================================================ 設定の図
def hillshade(z, mask):
    zz = np.where(mask, z, np.nan)
    zf = np.where(mask, z, np.nanmean(zz))
    hs = LightSource(azdeg=315, altdeg=45).hillshade(zf, vert_exag=1.0, dx=DX, dy=DX)
    return np.where(mask, hs, np.nan)


def fig_setup():
    fig = plt.figure(figsize=(13.0, 6.3))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.0, 1.55], height_ratios=[1.25, 1.0], wspace=0.14, hspace=0.36)

    # (a) 秩父の流域の中の位置
    ax = fig.add_subplot(gs[0, 0])
    basin = np.loadtxt(f"{SRC}/Chichibu_50m_basin.txt") > 0
    river = np.loadtxt(f"{SRC}/Chichibu_50m_river.txt") > 0
    ny0, nx0 = basin.shape
    i1, i2 = [int(v) for v in INFO["window_source_i"].split()]
    j1, j2 = [int(v) for v in INFO["window_source_j"].split()]
    sub = np.zeros_like(basin)
    sub[j1 - 1:j2, i1 - 1:i2] = MASK
    img = np.full(basin.shape, np.nan)
    img[basin] = 0.0
    img[basin & river] = 1.0
    img[sub] = 2.0
    cmap = ListedColormap(["#e7e5df", "#a9a79f", BLUE])
    ax.imshow(img, cmap=cmap, vmin=0, vmax=2, extent=[0, nx0 * KM, 0, ny0 * KM], interpolation="nearest")
    ax.set_xlabel("x (km)")
    ax.set_ylabel("y (km)")
    ax.grid(False)
    ax.set_aspect("equal")
    ax.legend(handles=[Patch(fc=BLUE, label=T("この例題の集水域(38 km²)", "catchment of this example (38 km²)")),
                       Patch(fc="#e7e5df", label=T("秩父の流域(test/chichibu)", "Chichibu basin (test/chichibu)")),
                       Patch(fc="#a9a79f", label=T("河道マスク", "river mask"))],
              loc="lower right", fontsize=8, handlelength=1.2)
    panel_label(ax, T("(a) 位置(元の 50 m 格子。上が北)", "(a) Location (source 50 m grid; north up)"))

    # (b) 地形と河道
    ax = fig.add_subplot(gs[:, 1])
    hs = hillshade(Z, MASK)
    ax.imshow(hs, cmap="gray", vmin=0.0, vmax=1.0, extent=EXT, interpolation="nearest", alpha=0.55)
    zc = np.where(MASK, Z, np.nan)
    xg = (np.arange(NX) + 0.5) * KM
    yg = (NY - np.arange(NY) - 0.5) * KM
    cs = ax.contour(xg, yg, zc, levels=np.arange(800, 2200, 200), colors=INK2, linewidths=0.5)
    ax.clabel(cs, fmt="%d", fontsize=7, inline_spacing=2)
    rw = np.where(RW & MASK, 1.0, np.nan)
    ax.imshow(rw, cmap=ListedColormap([BLUE]), extent=EXT, interpolation="nearest")
    xo, yo = xy(OUTLET)
    ax.plot([xo], [yo], marker="o", ms=8, mfc="white", mec=INK, mew=1.6, zorder=5, ls="none")
    ax.annotate(T("出口(排水口セル)。\nすぐ上流の列で流量を測る", "outlet (drain cell);\ndischarge is measured\nin the column just upstream"),
                (xo, yo), (EXT[1] - 0.03, yo + 0.85), fontsize=8.5, color=INK, ha="right", va="bottom",
                arrowprops=dict(arrowstyle="-", color=INK2, lw=0.7))
    ax.set_xlabel("x (km)")
    ax.set_ylabel("y (km)")
    ax.grid(False)
    ax.set_aspect("equal")
    ax.set_xlim(EXT[0], EXT[1])
    ax.set_ylim(EXT[2], EXT[3])
    ax.legend(handles=[Patch(fc=BLUE, label=T("河道セル", "channel cells")),
                       Line2D([], [], color=INK2, lw=0.6, label=T("等高線(200 m ごと)", "contours (every 200 m)"))],
              loc="lower right", fontsize=8.5, handlelength=1.4)
    panel_label(ax, T(f"(b) 地形と河道(50 m 格子、{NCELL:,} セル、標高 {Z[MASK].min():.0f}〜{Z[MASK].max():.0f} m)",
                      f"(b) Terrain and channels (50 m grid, {NCELL:,} cells, elevation {Z[MASK].min():.0f}–{Z[MASK].max():.0f} m)"),
                y=1.01)

    # (c) 降雨
    ax = fig.add_subplot(gs[1, 0])
    rain_fill(ax, label=False)
    for n, (a, b) in enumerate(STORMS):
        ax.text(0.5 * (a + b), RAIN_MMH + 0.5, T(f"{n + 1} 回目\n{RAIN_MMH * (b - a):.0f} mm", f"storm {n + 1}\n{RAIN_MMH * (b - a):.0f} mm"),
                ha="center", va="bottom", fontsize=8.5, color=INK2)
    time_axis(ax)
    ax.set_ylim(0, RAIN_MMH * 1.6)
    ax.set_ylabel(T("雨 (mm/h)", "rain (mm/h)"))
    panel_label(ax, T("(c) 降雨(全域一様)", "(c) Rainfall (uniform over the catchment)"))

    fig.subplots_adjust(left=0.055, right=0.985, top=0.94, bottom=0.085)
    fig.savefig(f"{FIGDIR}/setup.png")
    plt.close(fig)


# ================================================================ 飽和域の分布
MAP_TIMES = [5, 7, 12, 24, 48, 60]


def fig_source_area():
    case = "process"
    ft = dict((round(t), k) for k, t in file_times(case))
    gray = LinearSegmentedColormap.from_list("soil", ["#f6f5f2", "#a3a19a"])
    fig, axs = plt.subplots(2, 3, figsize=(13.0, 7.0))
    note = {5: T("1 回目の雨の途中", "during storm 1"), 7: T("1 回目の雨の途中", "during storm 1"),
            12: T("1 回目の雨の終わり", "end of storm 1"), 24: T("雨の 12 時間後", "12 h after the rain"),
            48: T("2 回目の雨の直前", "just before storm 2"), 60: T("2 回目の雨の終わり", "end of storm 2")}
    for ax, th in zip(axs.ravel(), MAP_TIMES):
        hg = bil(case, "Hg", ft[th])
        ratio = np.where(MASK, np.clip(hg / CAP, 0.0, 1.0), np.nan)
        sat = MASK & (hg >= CAP - SAT_TOL)
        im = ax.imshow(ratio, cmap=gray, vmin=0.0, vmax=1.0, extent=EXT, interpolation="nearest")
        ax.imshow(np.where(sat, 1.0, np.nan), cmap=ListedColormap([BLUE_D]), extent=EXT, interpolation="nearest")
        ax.set_aspect("equal")
        ax.grid(False)
        ax.set_xticks([])
        ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_visible(False)
        ax.set_title(T(f"{th} h({note[th]})  飽和域 {100 * sat.sum() / NCELL:.1f} %",
                       f"{th} h ({note[th]}): saturated {100 * sat.sum() / NCELL:.1f} %"), fontsize=10, color=INK)
    ax = axs[1, 0]
    x0, y0 = 0.35, 0.35
    ax.plot([x0, x0 + 2.0], [y0, y0], color=INK2, lw=2.0, solid_capstyle="butt")
    ax.text(x0 + 1.0, y0 + 0.12, "2 km", ha="center", va="bottom", fontsize=8.5, color=INK2)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.95, bottom=0.11, wspace=0.03, hspace=0.12)
    cax = fig.add_axes([0.30, 0.07, 0.25, 0.016])
    cb = fig.colorbar(im, cax=cax, orientation="horizontal")
    cb.set_label(T("土層の飽和度(地下貯留 ÷ 土層の容量)", "soil saturation (groundwater storage / soil capacity)"), fontsize=8.5)
    cb.outline.set_visible(False)
    fig.legend(handles=[Patch(fc=BLUE_D, label=T("飽和域(土層が満ちたセル = 流出寄与域)",
                                                 "saturated area (soil full = runoff source area)"))],
               loc="lower left", bbox_to_anchor=(0.60, 0.045), fontsize=9)
    fig.savefig(f"{FIGDIR}/source_area.png")
    plt.close(fig)


# ================================================================ 過程計算の時系列
def fig_series():
    case = "process"
    t, q = hydro(case)
    ts, fs = sat_series(case)
    lg = logtab(case)
    fig = plt.figure(figsize=(13.0, 8.2))
    outer = fig.add_gridspec(1, 2, width_ratios=[2.25, 1.0], wspace=0.17)
    gs = outer[0, 0].subgridspec(4, 1, hspace=0.30)
    gr = outer[0, 1].subgridspec(2, 1, hspace=0.36)

    ax1 = fig.add_subplot(gs[0])
    rain_fill(ax1)
    direct = rain(t) * np.interp(t, ts, fs)
    ax1.fill_between(t, 0.0, direct, color=BLUE, alpha=0.35, lw=0, zorder=2,
                     label=T("飽和域に降った雨(雨 × 飽和域の割合)", "rain on the saturated area (rain × saturated fraction)"))
    ax1.plot(t, q, color=INK, lw=2.0, zorder=3, label=T("流域からの流出", "runoff from the catchment"))
    ax1.set_ylim(0, RAIN_MMH * 1.12)
    ax1.set_ylabel(T("雨・流出高 (mm/h)", "rain, runoff (mm/h)"))
    ax1.legend(loc="upper right", ncol=3, fontsize=8, bbox_to_anchor=(1.0, 1.2), columnspacing=1.2)
    time_axis(ax1, label=False)
    panel_label(ax1, T("(a) 雨と流出", "(a) Rain and runoff"))

    ax2 = fig.add_subplot(gs[1], sharex=ax1)
    shade_storms(ax2)
    ax2.plot(ts, 100 * fs, color=BLUE_D, lw=2.0)
    ax2.set_ylim(0, None)
    ax2.set_ylabel(T("飽和域の割合 (%)", "saturated area (%)"))
    panel_label(ax2, T("(b) 飽和域(流出寄与域)の割合", "(b) Saturated (source) area fraction"))

    ax3 = fig.add_subplot(gs[2], sharex=ax1)
    shade_storms(ax3)
    ax3.plot(lg[:, 0], 1000 * lg[:, 3], color=BLUE, lw=2.0, label=T("土層の水(地下貯留)", "soil water (groundwater storage)"))
    ax3.plot(lg[:, 0], 1000 * lg[:, 2], color="#eb6834", lw=2.0, label=T("地表の水", "surface water"))
    ax3.set_ylim(0, None)
    ax3.set_ylabel(T("貯留高 (mm)", "storage (mm)"))
    ax3.legend(loc="upper right", ncol=2, fontsize=8, bbox_to_anchor=(1.0, 1.16))
    panel_label(ax3, T("(c) 流域平均の貯留", "(c) Catchment-mean storage"))

    ax4 = fig.add_subplot(gs[3], sharex=ax1)
    shade_storms(ax4)
    tf = np.linspace(0.0, TEND, 5761)
    ax4.plot(tf, cum(tf, rain(tf)), color=MUTED, lw=2.0, label=T("積算の雨", "cumulative rain"))
    ax4.plot(t, cum(t, q), color=INK, lw=2.0, label=T("積算の流出", "cumulative runoff"))
    ax4.set_ylim(0, None)
    ax4.set_ylabel(T("積算 (mm)", "cumulative (mm)"))
    ax4.legend(loc="upper left", ncol=1, fontsize=8)
    panel_label(ax4, T("(d) 積算の雨と流出", "(d) Cumulative rain and runoff"))
    time_axis(ax4)
    for a in (ax1, ax2, ax3):
        plt.setp(a.get_xticklabels(), visible=False)

    # (e) 貯留と飽和域の関係(発達と縮小の経路)
    ax5 = fig.add_subplot(gr[0])
    sg = np.interp(ts, lg[:, 0], 1000 * lg[:, 3])
    seg = [(12, 48, T("雨の後(縮小)", "after the rain (shrinking)"), MUTED, "-"), (60, 96, None, MUTED, "-"),
           (0, 12, T("1 回目の雨(発達)", "storm 1 (growth)"), BLUE_D, "-"),
           (48, 60, T("2 回目の雨(発達)", "storm 2 (growth)"), BLUE_D, (0, (4, 2)))]
    for a, b, lab, col, ls in seg:
        k = (ts >= a - 1e-9) & (ts <= b + 1e-9)
        ax5.plot(sg[k], 100 * fs[k], color=col, lw=2.0, ls=ls, label=lab)
    off = {6: ((8, -4), "left"), 12: ((8, -12), "left"), 24: ((8, -4), "left"), 48: ((-6, -13), "center"),
           60: ((8, 2), "left")}
    for th in (6, 12, 24, 48, 60):
        k = int(np.argmin(np.abs(ts - th)))
        ax5.plot([sg[k]], [100 * fs[k]], marker="o", ms=5.5, mfc="white", mec=INK, mew=1.2, ls="none", zorder=5,
                 clip_on=False)
        ax5.annotate(f"{th} h", (sg[k], 100 * fs[k]), textcoords="offset points", xytext=off[th][0], fontsize=8,
                     color=INK2, ha=off[th][1])
    ax5.set_xlabel(T("土層の水(流域平均。mm)", "soil water, catchment mean (mm)"))
    ax5.set_ylabel(T("飽和域の割合 (%)", "saturated area (%)"))
    ax5.set_xlim(0, 1.18 * sg.max())
    ax5.set_ylim(0, 110 * fs.max())
    ax5.legend(loc="upper left", fontsize=8)
    panel_label(ax5, T("(e) 貯留と飽和域(発達と縮小の経路)", "(e) Storage vs saturated area"))

    # (f) 斜面の位置ごとの飽和の進み方(落水線の集水面積の階級別)
    ax6 = fig.add_subplot(gr[1])
    classes = [(1, 1, T("1 セル(尾根)", "1 cell (ridge)")), (2, 9, T("2〜9 セル", "2–9 cells")),
               (10, 99, T("10〜99 セル", "10–99 cells")), (100, 10 ** 9, T("100 セル以上(谷)", "≥ 100 cells (valley)"))]
    ramp = ["#9ec5f4", "#5598e7", "#256abf", "#0d366b"]
    fr = {c[2]: [] for c in classes}
    for k, tt in file_times(case):
        hg = bil(case, "Hg", k)
        sat = hg >= CAP - SAT_TOL
        for lo, hi, lab in classes:
            sel = MASK & (ACC >= lo) & (ACC <= hi)
            fr[lab].append(100.0 * sat[sel].mean())
    shade_storms(ax6)
    for (lo, hi, lab), col in zip(classes, ramp):
        ax6.plot(ts, fr[lab], color=col, lw=2.0, label=lab)
    time_axis(ax6)
    ax6.set_ylim(0, 100)
    ax6.set_ylabel(T("飽和したセルの割合 (%)", "saturated cells (%)"))
    ax6.legend(loc="lower center", fontsize=8, ncol=2, title=T("上流の集水面積(落水線)", "upslope area (flow tree)"),
               title_fontsize=8, bbox_to_anchor=(0.56, 0.17), columnspacing=1.2, handlelength=1.6)
    panel_label(ax6, T("(f) 地形の位置ごとの飽和", "(f) Saturation by topographic position"))

    fig.subplots_adjust(left=0.055, right=0.985, top=0.955, bottom=0.065)
    fig.savefig(f"{FIGDIR}/series.png")
    plt.close(fig)
    return dict(t=t, q=q, ts=ts, fs=fs, lg=lg, classes=classes, fr=fr)


# ================================================================ 3 つの計算の比較
def nlabel(n):
    return f"{n:g}"


def fig_compare():
    tp, qp = hydro("process")
    fig, axs = plt.subplots(3, 1, figsize=(13.0, 9.6), sharex=True)

    # (a) 浸透なし(斜面の粗度を変える)
    ax = axs[0]
    rain_fill(ax)
    for case in ("surface", "surface_n1", "surface_n3", "surface_n5", "surface_n10", "surface_n30"):
        if not have(case):
            continue
        n = CASES[case][2]
        t, q = hydro(case)
        ax.plot(t, q, color=S_RAMP[n], lw=1.8, zorder=3, label=T(f"浸透なし n = {nlabel(n)}", f"no infiltration, n = {nlabel(n)}"))
    ax.plot(tp, qp, color=INK, lw=2.2, zorder=4, label=T("過程計算", "process run"))
    ax.set_ylim(0, RAIN_MMH * 1.12)
    ax.set_ylabel(T("雨・流出高 (mm/h)", "rain, runoff (mm/h)"))
    ax.legend(loc="upper right", ncol=1, fontsize=8)
    panel_label(ax, T("(a) 浸透なし: 斜面の粗度 n を変える", "(a) No infiltration: varying the slope roughness n"))

    # (b) 鉛直浸透のみ
    ax = axs[1]
    rain_fill(ax)
    for case in ("vertical", "vertical_n3"):
        if not have(case):
            continue
        n = CASES[case][2]
        t, q = hydro(case)
        ax.plot(t, q, color=V_RAMP[n], lw=1.8, zorder=3, label=T(f"鉛直浸透のみ n = {nlabel(n)}", f"vertical infiltration only, n = {nlabel(n)}"))
    ax.plot(tp, qp, color=INK, lw=2.2, zorder=4, label=T("過程計算", "process run"))
    ax.set_ylim(0, RAIN_MMH * 1.12)
    ax.set_ylabel(T("雨・流出高 (mm/h)", "rain, runoff (mm/h)"))
    ax.legend(loc="upper left", ncol=1, fontsize=8, bbox_to_anchor=(0.14, 1.0))
    panel_label(ax, T("(b) 鉛直浸透のみ(土層の側方流なし)", "(b) Vertical infiltration only (no lateral flow in the soil)"))

    # (c) 地表の流れを拡散波にする
    ax = axs[2]
    rain_fill(ax, label=False)
    pairs = [("surface", "surface_dif_n03"), ("surface_n3", "surface_dif_n3"), ("surface_n10", "surface_dif_n10")]
    for dyn, dif in pairs:
        n = CASES[dyn][2]
        if have(dyn):
            t, q = hydro(dyn)
            ax.plot(t, q, color=S_RAMP[n], lw=1.8, zorder=3)
        if have(dif):
            t, q = hydro(dif)
            ax.plot(t, q, color=S_RAMP[n], lw=1.8, ls=(0, (4, 2)), zorder=3)
    ax.plot(tp, qp, color=INK, lw=2.2, zorder=4)
    if have("process_dif"):
        t, q = hydro("process_dif")
        ax.plot(t, q, color=MUTED, lw=1.8, ls=(0, (4, 2)), zorder=5)
    h = [Line2D([], [], color=INK, lw=2.2, label=T("過程計算", "process run"))]
    h += [Line2D([], [], color=S_RAMP[n], lw=1.8, label=T(f"浸透なし n = {nlabel(n)}", f"no infiltration, n = {nlabel(n)}")) for n in (0.3, 3.0, 10.0)]
    h += [Line2D([], [], color=INK2, lw=1.8, label=T("実線: 力学波", "solid: dynamic wave")),
          Line2D([], [], color=INK2, lw=1.8, ls=(0, (4, 2)), label=T("破線: 拡散波", "dashed: diffusion wave"))]
    ax.legend(handles=h, loc="upper right", ncol=1, fontsize=8)
    ax.set_ylim(0, RAIN_MMH * 1.12)
    ax.set_ylabel(T("雨・流出高 (mm/h)", "rain, runoff (mm/h)"))
    panel_label(ax, T("(c) 地表の流れ: 力学波と拡散波", "(c) Surface flow: dynamic wave vs diffusion wave"))
    time_axis(ax)
    fig.subplots_adjust(left=0.055, right=0.985, top=0.96, bottom=0.055, hspace=0.22)
    fig.savefig(f"{FIGDIR}/compare.png")
    plt.close(fig)


# ================================================================ 粗度と指標
def fig_roughness(stats):
    """stats[case] = [1 回目の指標, 2 回目の指標](event の dict に nse を足したもの)。"""
    fig, axs = plt.subplots(3, 2, figsize=(11.5, 8.6), sharex=True)
    rows = [("peak", T("ピークの流出高 (mm/h)", "peak runoff (mm/h)")),
            ("onset", T("流出高が 1 mm/h を超える時刻 (h)", "time when runoff exceeds 1 mm/h (h)")),
            ("nse", T("過程計算との適合度(Nash–Sutcliffe)", "fit to the process run (Nash–Sutcliffe)"))]
    sd = [c for c in ("surface", "surface_n1", "surface_n3", "surface_n5", "surface_n10", "surface_n30") if c in stats]
    sf = [c for c in ("surface_dif_n03", "surface_dif_n3", "surface_dif_n10") if c in stats]
    vv = [c for c in ("vertical", "vertical_n3") if c in stats]
    orange, aqua = "#cf5604", "#1baf7a"
    for r, (key, ylabel) in enumerate(rows):
        for c in range(2):
            ax = axs[r, c]
            if key != "nse":
                ax.axhline(stats["process"][c][key], color=INK, lw=1.6, zorder=2)
            else:
                ax.axhline(1.0, color=INK, lw=1.6, zorder=2)
            if sd:
                ax.plot([CASES[k][2] for k in sd], [stats[k][c][key] for k in sd], color=orange, lw=1.8, marker="o",
                        ms=7, mec="white", mew=1.2, zorder=4)
            if sf:
                ax.plot([CASES[k][2] for k in sf], [stats[k][c][key] for k in sf], color=orange, lw=1.2, ls=(0, (4, 2)),
                        marker="o", ms=7, mfc="white", mec=orange, mew=1.5, zorder=3)
            if vv:
                ax.plot([CASES[k][2] for k in vv], [stats[k][c][key] for k in vv], color=aqua, lw=0, marker="s",
                        ms=7, mec="white", mew=1.2, zorder=4)
            ax.set_xscale("log")
            ax.set_xticks([0.3, 1, 3, 5, 10, 30])
            ax.set_xticklabels(["0.3", "1", "3", "5", "10", "30"])
            ax.set_xlim(0.2, 45)
            ax.minorticks_off()
            if c == 0:
                ax.set_ylabel(ylabel)
            if r == 0:
                ax.set_title(T(f"{c + 1} 回目の雨({'乾いた土' if c == 0 else '湿った土'})",
                               f"storm {c + 1} ({'dry soil' if c == 0 else 'wet soil'})"), fontsize=10, color=INK)
            if r == 2:
                ax.set_xlabel(T("斜面の粗度 n (m$^{-1/3}$ s)", "slope roughness n (m$^{-1/3}$ s)"))
                ax.set_ylim(-2.0, 1.1)
            else:
                ax.set_ylim(0, None)
    h = [Line2D([], [], color=INK, lw=1.6, label=T("過程計算(斜面の粗度 0.3)", "process run (slope roughness 0.3)")),
         Line2D([], [], color=orange, lw=1.8, marker="o", ms=7, mec="white", mew=1.2, label=T("浸透なし(力学波)", "no infiltration (dynamic wave)")),
         Line2D([], [], color=orange, lw=1.2, ls=(0, (4, 2)), marker="o", ms=7, mfc="white", mec=orange, mew=1.5,
                label=T("浸透なし(拡散波)", "no infiltration (diffusion wave)")),
         Line2D([], [], color=aqua, lw=0, marker="s", ms=7, mec="white", mew=1.2, label=T("鉛直浸透のみ", "vertical infiltration only"))]
    fig.legend(handles=h, loc="upper center", ncol=4, fontsize=8.5, bbox_to_anchor=(0.5, 0.995))
    fig.subplots_adjust(left=0.075, right=0.985, top=0.905, bottom=0.07, hspace=0.16, wspace=0.14)
    fig.savefig(f"{FIGDIR}/roughness.png")
    plt.close(fig)


# ================================================================ 数表
def kind_label(case):
    _, kind, n, dif = CASES[case]
    base = {"P": T("過程計算", "process run"), "S": T("浸透なし", "no infiltration"),
            "V": T("鉛直浸透のみ", "vertical infiltration only")}[kind]
    extra = []
    if case == "process_k10000":
        extra.append(T("側方 10000 mm/h", "lateral 10000 mm/h"))
    if case == "process_sd1":
        extra.append(T("土層 1 m", "soil 1 m"))
    if dif:
        extra.append(T("拡散波", "diffusion wave"))
    return base + ("(" + "、".join(extra) + ")" if (extra and not EN) else (" (" + ", ".join(extra) + ")" if extra else ""))


def fmt(v, f="%.2f"):
    return "—" if (v is None or not np.isfinite(v)) else f % v


def tables(ser):
    t, q, ts, fs, lg = ser["t"], ser["q"], ser["ts"], ser["fs"], ser["lg"]
    print(T("\n## 集水域", "\n## Catchment"))
    print(f"cells = {NCELL}, area = {AREA / 1e6:.2f} km2, z = {Z[MASK].min():.1f} .. {Z[MASK].max():.1f} m, "
          f"channel cells = {int((RW & MASK).sum())} ({100 * (RW & MASK).sum() / NCELL:.1f} %), capacity = {1000 * CAP:.0f} mm")

    # 過程計算の指標
    print(T("\n## 過程計算: 雨 1 回ごとの指標(時刻は雨の開始から)", "\n## Process run: per-storm indices (time from the start of each storm)"))
    print(T("| 雨 | 雨の前の土層の水 (mm) | 雨の前の飽和域 (%) | 流出高が 1 mm/h を超える時刻 (h) | ピーク (mm/h) | ピークの時刻 (h) | 飽和域の最大 (%) | 48 時間の流出高 (mm) | 雨に対する比 (%) |",
            "| Storm | Soil water before the rain (mm) | Saturated area before the rain (%) | Time when runoff exceeds 1 mm/h (h) | Peak (mm/h) | Time of peak (h) | Max. saturated area (%) | Runoff in 48 h (mm) | Ratio to rain (%) |"))
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for n, (a, b) in enumerate(STORMS):
        e = event(t, q, a)
        k = (ts >= a - 1e-9) & (ts <= a + CYCLE + 1e-9)
        p_mm = float(np.trapezoid(rain(np.linspace(a, a + CYCLE, 2881)), np.linspace(a, a + CYCLE, 2881)))
        print(f"| {n + 1} | {1000 * np.interp(a, lg[:, 0], lg[:, 3]):.1f} | {100 * np.interp(a, ts, fs):.1f} | {fmt(e['onset'], '%.1f')} | "
              f"{e['peak']:.2f} | {e['tpeak']:.1f} | {100 * fs[k].max():.1f} | {e['vol']:.1f} | {100 * e['vol'] / p_mm:.0f} |")

    # 飽和域に降った雨の割合
    print(T("\n## 過程計算: 雨の間の流出の内訳(飽和域に降った雨 = 雨 × 飽和域の割合 の積算)",
            "\n## Process run: split of the runoff (rain on the saturated area = integral of rain × saturated fraction)"))
    for n, (a, b) in enumerate(STORMS):
        tt = np.linspace(a, a + CYCLE, 2881)
        direct = float(np.trapezoid(rain(tt) * np.interp(tt, ts, fs), tt))
        e = event(t, q, a)
        print(T(f"{n + 1} 回目: 飽和域に降った雨 {direct:.1f} mm、48 時間の流出高 {e['vol']:.1f} mm(飽和域に降った雨はその {100 * direct / e['vol']:.0f} %)",
                f"storm {n + 1}: rain on the saturated area {direct:.1f} mm, runoff in 48 h {e['vol']:.1f} mm ({100 * direct / e['vol']:.0f} % of it)"))

    # 水収支
    print(T("\n## 過程計算: 水収支(積算の雨 − 測線の積算流出 − 流域に残る水)", "\n## Process run: water balance (cumulative rain − cumulative runoff at the transect − water left in the catchment)"))
    tf = np.linspace(0.0, TEND, 5761)
    pc, rc = cum(tf, rain(tf)), cum(t, q)
    for th in (12.0, 48.0, 60.0, 96.0):
        p_mm, r_mm = float(np.interp(th, tf, pc)), float(np.interp(th, t, rc))
        s_mm = 1000 * float(np.interp(th, lg[:, 0], lg[:, 4]))
        print(f"t = {th:4.0f} h: rain {p_mm:7.2f} mm, runoff {r_mm:7.2f} mm, storage {s_mm:6.1f} mm, residual {p_mm - r_mm - s_mm:+.2f} mm")

    # 地形の位置ごとの飽和
    print(T("\n## 過程計算: 上流の集水面積(落水線)の階級ごとの、飽和したセルの割合 (%)",
            "\n## Process run: saturated cells (%) by class of upslope area (flow tree)"))
    hdr = " | ".join(f"{th} h" for th in MAP_TIMES)
    print(T(f"| 階級 | セルの割合 (%) | {hdr} |", f"| Class | Share of cells (%) | {hdr} |"))
    print("|---|---:|" + "---:|" * 6)
    for lo, hi, lab in ser["classes"]:
        share = 100.0 * (MASK & (ACC >= lo) & (ACC <= hi)).sum() / NCELL
        vals = " | ".join(f"{np.interp(th, ts, ser['fr'][lab]):.0f}" for th in MAP_TIMES)
        print(f"| {lab} | {share:.0f} | {vals} |")

    # 比較の表(過程計算の設定を変えた表と、浸透なし・鉛直浸透のみの表)
    stats = {}
    head = T("| ケース | 斜面の粗度 | 雨 | 1 mm/h を超える時刻 (h) | ピーク (mm/h) | ピークの時刻 (h) | 雨の 12 時間後の流出高 (mm/h) | 48 時間の流出高 (mm) | 適合度 |",
             "| Case | Slope roughness | Storm | Time above 1 mm/h (h) | Peak (mm/h) | Time of peak (h) | Runoff 12 h after the rain (mm/h) | Runoff in 48 h (mm) | Fit |")
    order = ["process", "process_n1", "process_dif", "process_k10000", "process_sd1", "surface", "surface_n1", "surface_n3", "surface_n5",
             "surface_n10", "surface_n30", "surface_dif_n03", "surface_dif_n3", "surface_dif_n10", "vertical", "vertical_n3"]
    for case in order:
        if not have(case):
            continue
        tc, qc = hydro(case)
        stats[case] = []
        for n, (a, b) in enumerate(STORMS):
            e = event(tc, qc, a)
            e["nse"] = float(nse(tc, qc, q, a)) if case != "process" else 1.0
            stats[case].append(e)

    def rows(cases):
        for case in cases:
            if case not in stats:
                continue
            for n, e in enumerate(stats[case]):
                print(f"| {kind_label(case)} | {nlabel(CASES[case][2])} | {n + 1} | {fmt(e['onset'], '%.1f')} | {e['peak']:.2f} | {e['tpeak']:.1f} | "
                      f"{e['q24']:.2f} | {e['vol']:.1f} | {('—' if case == 'process' else '%.2f' % e['nse'])} |")

    print(T("\n## 過程計算の設定を 1 つずつ変えた計算(時刻は雨の開始から)",
            "\n## Process run with one setting changed at a time (time from the start of each storm)"))
    print(T("| 変えた設定 | 雨 | 1 mm/h を超える時刻 (h) | ピーク (mm/h) | ピークの時刻 (h) | 雨の 12 時間後の流出高 (mm/h) | 48 時間の流出高 (mm) | 飽和域の最大 (%) |",
            "| Changed setting | Storm | Time above 1 mm/h (h) | Peak (mm/h) | Time of peak (h) | Runoff 12 h after the rain (mm/h) | Runoff in 48 h (mm) | Max. saturated area (%) |"))
    print("|---|---:|---:|---:|---:|---:|---:|---:|")
    vlab = {"process": T("基本", "base"), "process_n1": T("斜面の粗度 0.3 → 1", "slope roughness 0.3 → 1"),
            "process_dif": T("地表の流れを拡散波に", "surface flow as a diffusion wave"),
            "process_k10000": T("側方飽和透水係数 3600 → 10000 mm/h", "lateral conductivity 3600 → 10000 mm/h"),
            "process_sd1": T("土層厚 0.5 → 1 m", "soil depth 0.5 → 1 m")}
    for case in ("process", "process_n1", "process_dif", "process_k10000", "process_sd1"):
        if case not in stats:
            continue
        tsc, fsc = sat_series(case)
        for n, (a, b) in enumerate(STORMS):
            e = stats[case][n]
            k = (tsc >= a - 1e-9) & (tsc <= a + CYCLE + 1e-9)
            print(f"| {vlab[case]} | {n + 1} | {fmt(e['onset'], '%.1f')} | {e['peak']:.2f} | {e['tpeak']:.1f} | {e['q24']:.2f} | "
                  f"{e['vol']:.1f} | {100 * fsc[k].max():.1f} |")
    print(T("\n## 浸透なし・鉛直浸透のみと過程計算(時刻は雨の開始から。適合度は過程計算に対する Nash–Sutcliffe 係数)",
            "\n## No infiltration and vertical infiltration only versus the process run (time from the start of each storm; fit = Nash–Sutcliffe efficiency against the process run)"))
    print(head)
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    rows(["process", "surface", "surface_n1", "surface_n3", "surface_n5", "surface_n10", "surface_n30", "surface_dif_n03",
          "surface_dif_n3", "surface_dif_n10", "vertical", "vertical_n3"])

    # 過程計算の条件を変えたとき、どの粗度の「浸透なし」が最も近いか
    print(T("\n## 過程計算の条件ごとの、浸透なし(力学波)の適合度(1 回目 / 2 回目の雨)",
            "\n## Fit of the no-infiltration runs (dynamic wave) to each variant of the process run (storm 1 / storm 2)"))
    sdyn = [c for c in ("surface", "surface_n1", "surface_n3", "surface_n5", "surface_n10", "surface_n30") if have(c)]
    print(T("| 過程計算の条件 | ", "| Process-run variant | ") + " | ".join(f"n = {nlabel(CASES[c][2])}" for c in sdyn) + " |")
    print("|---|" + "---:|" * len(sdyn))
    for ref in ("process", "process_n1", "process_k10000", "process_sd1"):
        if not have(ref):
            continue
        tr, qr = hydro(ref)
        cells = []
        for c in sdyn:
            tc, qc = hydro(c)
            cells.append(" / ".join("%.2f" % nse(tc, qc, qr, a) for a, b in STORMS))
        lab = {"process": T("基本(土層 0.5 m、側方 3600 mm/h、斜面の粗度 0.3)", "base (soil 0.5 m, lateral 3600 mm/h, slope roughness 0.3)"),
               "process_n1": T("斜面の粗度 1", "slope roughness 1"),
               "process_k10000": T("側方 10000 mm/h", "lateral 10000 mm/h"),
               "process_sd1": T("土層 1 m", "soil 1 m")}[ref]
        print(f"| {lab} | " + " | ".join(cells) + " |")

    # 地表に載る水(流域平均の貯留高と、河道セル以外の水深)
    print(T("\n## 地表の水(流域平均の貯留高の最大と、雨の終わりの河道セル以外の水深)",
            "\n## Surface water (maximum catchment-mean storage, and depth on non-channel cells at the end of each storm)"))
    print(T("| ケース | 斜面の粗度 | 地表の水の最大 (mm) | 12 h の水深の平均 (mm) | 12 h の水深の最大 (m) | 60 h の水深の平均 (mm) |",
            "| Case | Slope roughness | Max. surface water (mm) | Mean depth at 12 h (mm) | Max. depth at 12 h (m) | Mean depth at 60 h (mm) |"))
    print("|---|---:|---:|---:|---:|---:|")
    slope = MASK & ~RW
    for case in order:
        if not have(case):
            continue
        L = logtab(case)
        ssurf = 1000 * L[:, 2].max()                      # 地下水ありは S_surf、なしは S
        ft = dict((round(tt), k) for k, tt in file_times(case))
        h12, h60 = bil(case, "H", ft[12]), bil(case, "H", ft[60])
        print(f"| {kind_label(case)} | {nlabel(CASES[case][2])} | {ssurf:.1f} | {1000 * h12[slope].mean():.1f} | "
              f"{h12[slope].max():.2f} | {1000 * h60[slope].mean():.1f} |")

    # 計算の様子(Cn・最大水深)
    print(T("\n## 計算の様子(Log の列の最大)", "\n## Run diagnostics (maxima of the Log columns)"))
    for case in order:
        if not have(case):
            continue
        L = logtab(case)
        print(f"{case:18s} Cn_max {L[:, -3].max():.3f}  h_max {L[:, -2].max():6.2f} m  V_max {L[:, -1].max():5.2f} m/s  "
              f"Runge(max, after 1 h) {L[2:, -5].max():.1f} %  ex_flux total {int(L[:, -4].sum())}")
    return stats


def main():
    fig_mechanism()
    fig_setup()
    if not have("process"):
        print("plot_results.py: result_process がない(make run を先に)。mechanism.png と setup.png だけを描いた")
        return
    fig_source_area()
    ser = fig_series()
    stats = tables(ser)
    fig_compare()
    fig_roughness(stats)


if __name__ == "__main__":
    main()
