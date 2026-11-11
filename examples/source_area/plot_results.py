#!/usr/bin/env python3
"""source_area の図と数表(事前に make run。比較の図と表は make sweep の結果も使う)。

  figs/mechanism.png    3 つの計算(過程計算・浸透なし・鉛直浸透のみ)の違いの模式図(データを使わない)
  figs/setup.png        集水域の位置、地形と河道、降雨
  figs/source_area.png  土層の飽和度と飽和域(流出寄与域)の分布の時間変化(過程計算)
  figs/series.png       過程計算の流出、飽和域の割合、貯留、積算の雨と流出
  figs/compare.png      過程計算と、浸透なし・鉛直浸透のみのハイドログラフ
  figs/roughness.png    浸透なしの計算の斜面の粗度と、ピーク・立ち上がり・適合度
  figs/equivalent.png   過程計算の側方の透水係数ごとの、最も近い粗度の浸透なしとの比較
  figs/intensity.png    雨の強さ(10 mm/h と 30 mm/h)による、流出と飽和域の違い
  figs/layer2.png       土層の側方を遅くして比湧水量の小さい第 2 層を置いた計算と、単層の計算の比較
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
S_RAMP = {0.3: "#f8986c", 0.6: "#f38956", 1.0: "#ed7940", 2.0: "#e26b2b", 3.0: "#d75e16", 5.0: "#b84800",
          10.0: "#923400", 30.0: "#662703"}              # 浸透なし(粗度の順。1 色相の明→暗)
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


def flat_channel():
    """窪地処理でできた平らな段の河道セル: 8 近傍の河道セルのどれかと標高が同じ河道セル。"""
    ch = RW & MASK
    zp = np.pad(np.where(ch, Z, np.nan), 1, constant_values=np.nan)
    out = np.zeros(Z.shape, dtype=bool)
    for dj in (-1, 0, 1):
        for di in (-1, 0, 1):
            if dj or di:
                with np.errstate(invalid="ignore"):
                    out |= np.abs(zp[1 + dj:1 + dj + NY, 1 + di:1 + di + NX] - Z) < 1e-6
    return out & ch


FLATCH = flat_channel()
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
    "surface_n06": ("result_sweep_surface_n06", "S", 0.6, False),
    "surface_n1": ("result_sweep_surface_n1", "S", 1.0, False),
    "surface_n2": ("result_sweep_surface_n2", "S", 2.0, False),
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
    "process_k3600": ("result_sweep_process_k3600", "P", 0.3, False),
    "process_k10000": ("result_sweep_process_k10000", "P", 0.3, False),
    "process_k100000": ("result_sweep_process_k100000", "P", 0.3, False),
    "process_sd1": ("result_sweep_process_sd1", "P", 0.3, False),
    "process_l2": ("result_sweep_process_l2", "P", 0.3, False),
    "process_r30": ("result_sweep_process_r30", "P", 0.3, False),
    "surface_r30_n03": ("result_sweep_surface_r30_n03", "S", 0.3, False),
    "surface_r30_n1": ("result_sweep_surface_r30_n1", "S", 1.0, False),
    "surface_r30_n3": ("result_sweep_surface_r30_n3", "S", 3.0, False),
}


# 側方飽和透水係数を変えた過程計算(mm/h。基本は param.txt の値)と、粗度を変えた浸透なし(力学波)
KSH = {"process_k3600": 3600, "process_k10000": 10000, "process_k100000": 100000}
KBASE = int(round(param_value("param.txt", "gw_ksh_mmh")))
KREFS = sorted([("process", KBASE)] + list(KSH.items()), key=lambda v: v[1])     # 透水係数の小さい順
SDYN = ("surface", "surface_n06", "surface_n1", "surface_n2", "surface_n3", "surface_n5", "surface_n10", "surface_n30")
STORE_TIMES = [2, 3, 4, 6, 12, 14, 24, 48, 50, 51, 60]  # 貯留の内訳の表の時刻 (h)
# 雨を強くしたケース(降雨は param_rain30.txt。時刻は param_common.txt と同じ)
R30_PROCESS = "process_r30"
R30_SDYN = ("surface_r30_n03", "surface_r30_n1", "surface_r30_n3")
R30_MMH = max(float(v) for v in re.findall(r"^\s*prval\(:,\s*\d+\)\s*=\s*[-0-9.]+\s*,\s*([-0-9.]+)",
                                           open("param_rain30.txt", encoding="utf-8").read(), re.M))


def rain_of(case):
    """そのケースの雨の強さ (mm/h)。"""
    return R30_MMH if "_r30" in case else RAIN_MMH


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
        if fn.startswith("param") and fn.endswith(".txt"):
            txt = open(f"{rdir(case)}/{fn}", encoding="utf-8").read()
            if re.search(r"^\s*sd0\s*=", txt, re.M) and re.search(r"^\s*sy0\s*=", txt, re.M):   # 降雨・共通設定の写しは飛ばす
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


def reach(t, q, storm, frac, rmm=None):
    """雨の間に流出高が雨の強さ(rmm。既定は基本の雨)の frac 倍に達する時刻(雨の開始から。達しなければ nan)。"""
    a, b = storm
    k = (t >= a - 1e-9) & (t <= b + 1e-9)
    i = np.where(q[k] >= frac * (RAIN_MMH if rmm is None else rmm))[0]
    return float(t[k][i[0]] - a) if len(i) else np.nan


def best_roughness(ref, cands=None):
    """過程計算 ref に最も近い浸透なし(力学波)のケースを雨ごとに返す: [(適合度, ケース名), …]。"""
    tr, qr = hydro(ref)
    out = []
    for a, b in STORMS:
        fits = [(float(nse(*hydro(c), qr, a)), c) for c in (SDYN if cands is None else cands) if have(c)]
        out.append(max(fits) if fits else (np.nan, None))
    return out


def has_var(case, var):
    return os.path.exists(f"{rdir(case)}/{var}0000.bil")


def slope_water(case, k):
    """斜面のセル(河道セル以外)にある水(地表 + 土層 + 第 2 層)を流域平均の水深 (mm) で返す。"""
    slope = MASK & ~RW
    v = bil(case, "H", k)[slope].sum()
    for var in ("Hg", "Hg2"):
        if has_var(case, var):
            v += bil(case, var, k)[slope].sum()
    return 1000.0 * v / NCELL


_STAGES = {}


def stages(case, storm=1):
    """stages_calc の結果を覚えておく(分布を 100 枚近く読むので)。"""
    if (case, storm) not in _STAGES:
        _STAGES[(case, storm)] = stages_calc(case, storm)
    return _STAGES[(case, storm)]


def stages_calc(case, storm=1):
    """雨から出口までの遅れ(雨 1 回分の 48 時間の重心の差。h)を、斜面の段(雨 → 河道セルへの流入)と
    河道の段(河道セルへの流入 → 出口)に分ける。河道セルへの流入は、1 時間ごとの分布の水収支
    (雨 − 斜面のセルにある水の増加)で求める。
    返り値: (斜面の段, 河道の段, 雨の終わりに斜面のセルにある水(斜面のセルの平均の水深 mm))。"""
    ft = dict((round(tt), k) for k, tt in file_times(case))
    hours = np.arange(0, int(TEND) + 1)
    st = np.array([slope_water(case, ft[h]) for h in hours])
    tm = hours[:-1] + 0.5
    fine = np.linspace(0.0, TEND, int(TEND) * 60 + 1)
    rf = rain(fine) * rain_of(case) / RAIN_MMH
    t, q = hydro(case)
    rh = np.array([np.trapezoid(rf[(fine >= h) & (fine <= h + 1)], fine[(fine >= h) & (fine <= h + 1)]) for h in hours[:-1]])
    qh = np.array([np.trapezoid(q[(t >= h - 1e-9) & (t <= h + 1 + 1e-9)], t[(t >= h - 1e-9) & (t <= h + 1 + 1e-9)])
                   for h in hours[:-1]])
    inflow = rh - np.diff(st)
    a = STORMS[storm][0]
    k = (tm >= np.floor(a)) & (tm <= np.floor(a) + CYCLE)
    cen = lambda v: float(np.sum(tm[k] * v[k]) / np.sum(v[k]))
    nslope = float((MASK & ~RW).sum())
    return cen(inflow) - cen(rh), cen(qh) - cen(inflow), float(st[int(round(STORMS[storm][1]))]) * NCELL / nslope


def same_lag_roughness(lag, cands):
    """斜面の段の遅れ lag (h) と同じ遅れになる浸透なしの粗度(cands の遅れを両対数で内挿・外挿)。"""
    pts = sorted((CASES[c][2], stages(c)[0]) for c in cands if have(c))
    if len(pts) < 2:
        return np.nan
    x, y = np.log([v[0] for v in pts]), np.log([v[1] for v in pts])
    ly = np.log(lag)
    i = 0 if ly <= y[0] else (len(y) - 2 if ly >= y[-1] else int(np.searchsorted(y, ly)) - 1)
    return float(np.exp(x[i] + (ly - y[i]) * (x[i + 1] - x[i]) / (y[i + 1] - y[i])))


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
    ax.legend(handles=[Patch(fc=BLUE, label=T(f"この例題の集水域({AREA / 1e6:.0f} km²)", f"catchment of this example ({AREA / 1e6:.0f} km²)")),
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
    ax.annotate(T("出口(排水口セル)。\nすぐ上流の列で\n流量を測る", "outlet (drain cell);\ndischarge is measured\nin the column\njust upstream"),
                (xo, yo), (EXT[1] - 0.03, yo + 1.0), fontsize=8.5, color=INK, ha="right", va="bottom",
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
MAP_TIMES = [2, 3, 12, 16, 24, 48]


def fig_source_area():
    case = "process"
    ft = dict((round(t), k) for k, t in file_times(case))
    gray = LinearSegmentedColormap.from_list("soil", ["#f6f5f2", "#a3a19a"])
    fig, axs = plt.subplots(2, 3, figsize=(13.0, 7.0))
    note = {2: T("1 回目の雨の途中", "during storm 1"), 3: T("1 回目の雨の途中", "during storm 1"),
            12: T("1 回目の雨の終わり", "end of storm 1"), 16: T("雨の 4 時間後", "4 h after the rain"),
            24: T("雨の 12 時間後", "12 h after the rain"), 48: T("2 回目の雨の直前", "just before storm 2")}
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
    cap = 1000 * CAP                              # 土層の容量 (mm)
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
    ax2.set_ylim(0, 5.0 * np.ceil(1.2 * 100 * fs.max() / 5.0))      # 最大の少し上の切りのよい値まで
    ax2.set_ylabel(T("飽和域の割合 (%)", "saturated area (%)"))
    panel_label(ax2, T("(b) 飽和域(流出寄与域)の割合", "(b) Saturated (source) area fraction"))

    ax3 = fig.add_subplot(gs[2], sharex=ax1)
    shade_storms(ax3)
    ax3.plot(lg[:, 0], 1000 * lg[:, 3], color=BLUE, lw=2.0, label=T("土層の水(地下貯留)", "soil water (groundwater storage)"))
    ax3.plot(lg[:, 0], 1000 * lg[:, 2], color="#eb6834", lw=2.0, label=T("地表の水", "surface water"))
    stop = 10.0 * np.ceil(1.15 * 1000 * max(lg[:, 3].max(), lg[:, 2].max()) / 10.0)
    if stop >= cap:                               # 土層の容量が図の範囲に入るときは、線で示す
        ax3.axhline(cap, color=MUTED, lw=1.0, ls=(0, (4, 3)), zorder=1)
        ax3.text(30.0, cap - 3.0, T(f"土層の容量 {cap:.0f} mm", f"soil capacity {cap:.0f} mm"), fontsize=8, color=INK2,
                 ha="center", va="top")
        stop = 1.08 * cap
    ax3.set_ylim(0, stop)
    ax3.set_ylabel(T("貯留高 (mm)", "storage (mm)"))
    ax3.legend(loc="upper right", ncol=2, fontsize=8, bbox_to_anchor=(1.0, 1.16))
    panel_label(ax3, T(f"(c) 流域平均の貯留(土層の容量は {cap:.0f} mm)", f"(c) Catchment-mean storage (soil capacity {cap:.0f} mm)"))

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

    # (e) 貯留と飽和域の関係(発達と縮小の経路)。軸は原点から取り、横(土層の水 ÷ 容量)と縦(飽和域の割合)を
    # 同じ比率にする(容量と全域(100 %)を上限に、経路の最大の少し上の切りのよい値まで)。
    # 飽和したセルは容量いっぱいの水を持つので、飽和域の割合は「土層の水 / 容量」を超えない(点線 = 図の対角線)
    ax5 = fig.add_subplot(gr[0])
    sg = np.interp(ts, lg[:, 0], 1000 * lg[:, 3])
    lim = min(cap, 10.0 * np.ceil(1.1 * max(sg.max(), fs.max() * cap) / 10.0))     # 横軸の上限 (mm)
    ax5.plot([0, lim], [0, 100 * lim / cap], color=MUTED, lw=1.0, ls=(0, (1.5, 2.5)), zorder=1,
             label=T("上限(土層の水がすべて飽和域にある)", "upper bound (all soil water in saturated cells)"))
    seg = [(12, 48, T("雨の後(縮小)", "after the rain (shrinking)"), MUTED, "-"), (60, 96, None, MUTED, "-"),
           (0, 12, T("1 回目の雨(発達)", "storm 1 (growth)"), BLUE_D, "-"),
           (48, 60, T("2 回目の雨(発達)", "storm 2 (growth)"), BLUE_D, (0, (4, 2)))]
    for a, b, lab, col, ls in seg:
        k = (ts >= a - 1e-9) & (ts <= b + 1e-9)
        ax5.plot(sg[k], 100 * fs[k], color=col, lw=2.0, ls=ls, label=lab)
    off = {2: ((7, -9), "left"), 3: ((8, -3), "left"), 12: ((7, 3), "left"), 16: ((-7, 4), "right"), 24: ((-7, 4), "right"),
           48: ((7, -10), "left")}
    for th in MAP_TIMES:                          # 丸は分布の図と同じ時刻
        k = int(np.argmin(np.abs(ts - th)))
        ax5.plot([sg[k]], [100 * fs[k]], marker="o", ms=5.5, mfc="white", mec=INK, mew=1.2, ls="none", zorder=5,
                 clip_on=False)
        ax5.annotate(f"{th} h", (sg[k], 100 * fs[k]), textcoords="offset points", xytext=off.get(th, ((7, 3), "left"))[0],
                     fontsize=8, color=INK2, ha=off.get(th, ((7, 3), "left"))[1])
    ax5.set_xlabel(T("土層の水(流域平均。mm)", "soil water, catchment mean (mm)"))
    ax5.set_ylabel(T("飽和域の割合 (%)", "saturated area (%)"))
    ax5.set_xlim(0, lim)
    ax5.set_ylim(0, 100 * lim / cap)
    step = 10.0 if lim <= 50.0 else 20.0
    ax5.set_xticks(np.arange(0, lim + 1, step))
    ax5.set_yticks(np.arange(0, 100 * lim / cap + 1, 100 * step / cap))
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
    for case in ("surface", "surface_n1", "surface_n2", "surface_n3", "surface_n5", "surface_n10"):
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
    sd = [c for c in SDYN if c in stats]
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
            ax.set_xticks([0.3, 0.6, 1, 2, 3, 5, 10, 30])
            ax.set_xticklabels(["0.3", "0.6", "1", "2", "3", "5", "10", "30"])
            ax.set_xlim(0.2, 45)
            ax.minorticks_off()
            if c == 0:
                ax.set_ylabel(ylabel)
            if r == 0:
                ax.set_title(T(f"{c + 1} 回目の雨({'乾いた土' if c == 0 else '湿った土'})",
                               f"storm {c + 1} ({'dry soil' if c == 0 else 'wet soil'})"), fontsize=10, color=INK)
            if r == 2:
                ax.set_xlabel(T("斜面の粗度 n (m$^{-1/3}$ s)", "slope roughness n (m$^{-1/3}$ s)"))
                low = min(stats[k][j]["nse"] for k in sd + sf + vv for j in range(2))
                ax.set_ylim(min(-0.5, 0.5 * np.floor(2.0 * (low - 0.1))), 1.1)      # 両方の雨で同じ範囲
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


# ================================================================ 側方の透水係数と等価粗度
def fig_equivalent():
    """過程計算の側方飽和透水係数ごとに、最も近い粗度の浸透なし(力学波)と重ねる。"""
    refs = [(c, k) for c, k in KREFS if have(c)]
    if len(refs) < 2 or not any(have(c) for c in SDYN):
        return
    height = 2.75 * len(refs) + 0.7
    fig, axs = plt.subplots(len(refs), 1, figsize=(13.0, height), sharex=True)
    for m, (ax, (ref, kval)) in enumerate(zip(axs, refs)):
        rain_fill(ax, label=(m == 0))
        tr, qr = hydro(ref)
        best = best_roughness(ref)
        done = []
        for fit, c in best:
            if c is None or c in done:
                continue
            done.append(c)
            n = CASES[c][2]
            which = [i + 1 for i, (f2, c2) in enumerate(best) if c2 == c]
            fits = "・".join(f"{f2:.2f}" for f2, c2 in best if c2 == c) if not EN else ", ".join(f"{f2:.2f}" for f2, c2 in best if c2 == c)
            if len(which) == len(best):
                lab = T(f"浸透なし n = {nlabel(n)}(どちらの雨にも最も近い。適合度 {fits})",
                        f"no infiltration, n = {nlabel(n)} (closest for both storms; fit {fits})")
            else:
                lab = T(f"浸透なし n = {nlabel(n)}({which[0]} 回目の雨に最も近い。適合度 {fits})",
                        f"no infiltration, n = {nlabel(n)} (closest for storm {which[0]}; fit {fits})")
            t, q = hydro(c)
            ax.plot(t, q, color=S_RAMP[n], lw=1.8, zorder=3, label=lab)
        ax.plot(tr, qr, color=INK, lw=2.2, zorder=4, label=T("過程計算", "process run"))
        ax.set_ylim(0, RAIN_MMH * 1.12)
        ax.set_ylabel(T("雨・流出高 (mm/h)", "rain, runoff (mm/h)"))
        ax.legend(loc="upper right", ncol=1, fontsize=8)
        tsc, fsc = sat_series(ref)
        panel_label(ax, T(f"({'abcdef'[m]}) 側方飽和透水係数 {kval} mm/h{'(基本)' if ref == 'process' else ''}: 飽和域の最大 {100 * fsc.max():.0f} %",
                          f"({'abcdef'[m]}) Lateral conductivity {kval} mm/h{' (base)' if ref == 'process' else ''}: maximum saturated area {100 * fsc.max():.0f} %"))
    time_axis(axs[-1])
    fig.subplots_adjust(left=0.055, right=0.985, top=1.0 - 0.36 / height, bottom=0.58 / height, hspace=0.24)
    fig.savefig(f"{FIGDIR}/equivalent.png")
    plt.close(fig)


# ================================================================ 雨の強さ
def fig_intensity():
    """基本の雨(10 mm/h)と強い雨(30 mm/h)で、過程計算と浸透なしの流出、飽和域の割合を比べる。"""
    if not have(R30_PROCESS):
        return
    fig, axs = plt.subplots(3, 1, figsize=(13.0, 9.2), sharex=True)
    tf = np.linspace(0.0, TEND, 5761)
    rows = [(RAIN_MMH, "process", ("surface", "surface_n1", "surface_n3")), (R30_MMH, R30_PROCESS, R30_SDYN)]
    for m, (rmm, ref, cands) in enumerate(rows):
        ax = axs[m]
        ax.fill_between(tf, 0.0, rain(tf) * rmm / RAIN_MMH, color=RAINC, lw=0, zorder=1, label=T("雨", "rain"))
        for c in cands:
            if not have(c):
                continue
            n = CASES[c][2]
            t, q = hydro(c)
            ax.plot(t, q, color=S_RAMP[n], lw=1.8, zorder=3, label=T(f"浸透なし n = {nlabel(n)}", f"no infiltration, n = {nlabel(n)}"))
        t, q = hydro(ref)
        ax.plot(t, q, color=INK, lw=2.2, zorder=4, label=T("過程計算", "process run"))
        ax.set_ylim(0, rmm * 1.12)
        ax.set_ylabel(T("雨・流出高 (mm/h)", "rain, runoff (mm/h)"))
        ax.legend(loc="upper right", ncol=1, fontsize=8)
        panel_label(ax, T(f"({'ab'[m]}) 雨 {rmm:g} mm/h × 12 時間{'(基本)' if m == 0 else ''}",
                          f"({'ab'[m]}) Rain {rmm:g} mm/h for 12 h{' (base)' if m == 0 else ''}"))
    ax = axs[2]
    shade_storms(ax)
    for ref, rmm, col in (("process", RAIN_MMH, BLUE), (R30_PROCESS, R30_MMH, "#12447f")):
        ts, fs = sat_series(ref)
        ax.plot(ts, 100 * fs, color=col, lw=2.0, label=T(f"雨 {rmm:g} mm/h(最大 {100 * fs.max():.0f} %)",
                                                         f"rain {rmm:g} mm/h (maximum {100 * fs.max():.0f} %)"))
    ax.set_ylim(0, 10.0 * np.ceil(1.15 * max(100 * sat_series(r)[1].max() for r in ("process", R30_PROCESS)) / 10.0))
    ax.set_ylabel(T("飽和域の割合 (%)", "saturated area (%)"))
    ax.legend(loc="upper right", ncol=1, fontsize=8)
    panel_label(ax, T("(c) 過程計算の飽和域(流出寄与域)の割合", "(c) Saturated (source) area fraction of the process runs"))
    time_axis(ax)
    fig.subplots_adjust(left=0.055, right=0.985, top=0.96, bottom=0.06, hspace=0.22)
    fig.savefig(f"{FIGDIR}/intensity.png")
    plt.close(fig)


# ================================================================ 第 2 層を伝わる波
def fig_layer2():
    """土層の側方を遅くして比湧水量の小さい第 2 層を置いた計算を、単層の 2 つの計算と比べる。"""
    if not (have("process_l2") and have("process_k3600")):
        return
    k_slow = KSH["process_k3600"]
    sy2 = param_value("param.txt", "gw2_sy")
    runs = [("process_k3600", MUTED, 1.8, T(f"単層: 側方 {k_slow} mm/h", f"single layer, lateral {k_slow} mm/h")),
            ("process", INK, 2.2, T(f"単層: 側方 {KBASE} mm/h(基本)", f"single layer, lateral {KBASE} mm/h (base)")),
            ("process_l2", BLUE, 2.0, T(f"2 層: 側方 {k_slow} mm/h + 第 2 層({k_slow} mm/h、比湧水量 {sy2:g})",
                                        f"two layers: {k_slow} mm/h + layer 2 ({k_slow} mm/h, specific yield {sy2:g})"))]
    fig, axs = plt.subplots(2, 1, figsize=(13.0, 6.6), sharex=True)
    ax = axs[0]
    rain_fill(ax)
    for c, col, lw, lab in runs:
        t, q = hydro(c)
        ax.plot(t, q, color=col, lw=lw, zorder=3 if c != "process" else 4, label=lab)
    ax.set_ylim(0, RAIN_MMH * 1.12)
    ax.set_ylabel(T("雨・流出高 (mm/h)", "rain, runoff (mm/h)"))
    ax.legend(loc="upper center", ncol=1, fontsize=8, bbox_to_anchor=(0.315, 1.0))     # 2 回の雨の間の空いた所
    panel_label(ax, T("(a) 流域からの流出", "(a) Runoff from the catchment"))
    ax = axs[1]
    shade_storms(ax)
    for c, col, lw, lab in runs:
        ts, fs = sat_series(c)
        ax.plot(ts, 100 * fs, color=col, lw=lw, zorder=3)
    cap2 = param_value("param.txt", "gw2_depth") * param_value("param.txt", "gw2_sy")
    ts2, f2 = [], []
    for k, tt in file_times("process_l2"):
        ts2.append(tt)
        f2.append(100.0 * float((bil("process_l2", "Hg2", k)[MASK] >= cap2 - SAT_TOL).mean()))
    ax.plot(ts2, f2, color=BLUE, lw=1.6, ls=(0, (4, 2)), zorder=3)
    h = [Line2D([], [], color=INK2, lw=1.8, label=T("実線: 土層が満ちたセル(飽和域)", "solid: cells with the soil full (saturated area)")),
         Line2D([], [], color=BLUE, lw=1.6, ls=(0, (4, 2)), label=T("破線: 第 2 層が満ちたセル(2 層の計算)", "dashed: cells with layer 2 full (two-layer run)"))]
    ax.legend(handles=h, loc="upper right", ncol=1, fontsize=8)
    ax.set_ylim(0, 50)
    ax.set_ylabel(T("セルの割合 (%)", "share of cells (%)"))
    panel_label(ax, T("(b) 満ちたセルの割合(線の色は (a) と同じ)", "(b) Share of full cells (line colours as in (a))"))
    time_axis(ax)
    fig.subplots_adjust(left=0.055, right=0.985, top=0.945, bottom=0.085, hspace=0.22)
    fig.savefig(f"{FIGDIR}/layer2.png")
    plt.close(fig)


# ================================================================ 数表
def kind_label(case):
    _, kind, n, dif = CASES[case]
    base = {"P": T("過程計算", "process run"), "S": T("浸透なし", "no infiltration"),
            "V": T("鉛直浸透のみ", "vertical infiltration only")}[kind]
    extra = []
    if case in KSH:
        extra.append(T(f"側方 {KSH[case]} mm/h", f"lateral {KSH[case]} mm/h"))
    if case == "process_sd1":
        extra.append(T("土層 1 m", "soil 1 m"))
    if case == "process_l2":
        extra.append(T(f"側方 {KSH['process_k3600']} mm/h + 第 2 層", f"lateral {KSH['process_k3600']} mm/h + layer 2"))
    if "_r30" in case:
        extra.append(T(f"雨 {R30_MMH:g} mm/h", f"rain {R30_MMH:g} mm/h"))
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
    if "slope_median_p10_p90" in INFO:
        sm, s10, s90 = (float(v) for v in INFO["slope_median_p10_p90"].split())
        print(T(f"最急勾配の中央値 {sm:.2f}({np.degrees(np.arctan(sm)):.0f}°。セルの 8 割が {s10:.2f}〜{s90:.2f})、"
                f"河道網 {INFO['channel_km']} km(平らな区間 {INFO['channel_flat_percent']} %)、"
                f"本川 {INFO['main_stem_km']} km(平らな区間 {INFO['main_stem_flat_percent']} %、最長 {INFO['longest_flat_reach_m']} m)、"
                f"河道マスクのない谷の集水面積は {INFO['largest_area_without_channel_km2']} km2 まで、"
                f"平らな段の河道セル {int(FLATCH.sum())}(河道セルの {100 * FLATCH.sum() / (RW & MASK).sum():.0f} %)",
                f"median steepest slope {sm:.2f} ({np.degrees(np.arctan(sm)):.0f} deg; 80 % of the cells within {s10:.2f}-{s90:.2f}), "
                f"channel network {INFO['channel_km']} km (flat reaches {INFO['channel_flat_percent']} %), "
                f"main stem {INFO['main_stem_km']} km (flat reaches {INFO['main_stem_flat_percent']} %, longest {INFO['longest_flat_reach_m']} m), "
                f"valleys without the channel mask up to {INFO['largest_area_without_channel_km2']} km2, "
                f"channel cells on flat steps {int(FLATCH.sum())} ({100 * FLATCH.sum() / (RW & MASK).sum():.0f} % of the channel cells)"))

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

    # 流域に貯まっている水の内訳
    print(T("\n## 過程計算: 流域に貯まっている水の内訳(流域平均の水深 mm)",
            "\n## Process run: where the water in the catchment is (catchment-mean depth, mm)"))
    print(T("| 時刻 (h) | 流出 (mm/h) | 土層の水 | うち飽和域のセル | 地表の水 | うち河道セル | 合計 |",
            "| Time (h) | Runoff (mm/h) | Soil water | of which in saturated cells | Surface water | of which on channel cells | Total |"))
    print("|---:|---:|---:|---:|---:|---:|---:|")
    ftp = dict((round(tt), k) for k, tt in file_times("process"))
    for th in STORE_TIMES:
        h, hg = bil("process", "H", ftp[th]), bil("process", "Hg", ftp[th])
        sat = MASK & (hg >= CAP - SAT_TOL)
        soil, soil_sat = 1000 * hg[MASK].sum() / NCELL, 1000 * hg[sat].sum() / NCELL
        surf, surf_ch = 1000 * h[MASK].sum() / NCELL, 1000 * h[RW & MASK].sum() / NCELL
        print(f"| {th} | {np.interp(th, t, q):.2f} | {soil:.1f} | {soil_sat:.1f} | {surf:.1f} | {surf_ch:.1f} | {soil + surf:.1f} |")

    print(T("\n## 過程計算: 1 時間ごとの流出 (mm/h)・飽和域の割合 (%)・土層の水と地表の水 (mm)",
            "\n## Process run: hourly runoff (mm/h), saturated area (%), soil water and surface water (mm)"))
    for h0 in (0, 12, 48, 60):
        hh = list(range(h0, h0 + 13))
        print("t (h)     " + " ".join(f"{h:6d}" for h in hh))
        print("runoff    " + " ".join(f"{np.interp(h, t, q):6.2f}" for h in hh))
        print("saturated " + " ".join(f"{100 * np.interp(h, ts, fs):6.1f}" for h in hh))
        print("soil      " + " ".join(f"{1000 * np.interp(h, lg[:, 0], lg[:, 3]):6.1f}" for h in hh))
        print("surface   " + " ".join(f"{1000 * np.interp(h, lg[:, 0], lg[:, 2]):6.1f}" for h in hh))

    print(T("\n## 過程計算: 河道セルの水(流域平均の水深 mm)と、そのうち平らな段の河道セルの水、水深の最大",
            "\n## Process run: water on channel cells (catchment-mean depth, mm), the part on the channel cells of flat steps, and the maximum depth"))
    for th in (8, 12, 48):
        h = bil("process", "H", ftp[th])
        print(f"t = {th:2d} h: channel {1000 * h[RW & MASK].sum() / NCELL:.1f} mm, flat steps {1000 * h[FLATCH].sum() / NCELL:.1f} mm "
              f"(mean depth {h[FLATCH].mean():.2f} m), other channel cells mean depth {h[RW & MASK & ~FLATCH].mean():.2f} m, max depth {h[MASK].max():.2f} m")

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
    pvar = ["process", "process_n1", "process_dif", "process_k3600", "process_k10000", "process_k100000", "process_sd1", "process_l2"]
    order = pvar + list(SDYN) + ["surface_dif_n03", "surface_dif_n3", "surface_dif_n10", "vertical", "vertical_n3"]
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
            "process_sd1": T("土層厚 0.5 → 1 m", "soil depth 0.5 → 1 m"),
            "process_l2": T(f"側方飽和透水係数 {KBASE} → {KSH['process_k3600']} mm/h + 第 2 層",
                            f"lateral conductivity {KBASE} → {KSH['process_k3600']} mm/h + layer 2")}
    for case, kval in KSH.items():
        vlab[case] = T(f"側方飽和透水係数 {KBASE} → {kval} mm/h", f"lateral conductivity {KBASE} → {kval} mm/h")
    for case in pvar:
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
    rows(["process"] + list(SDYN) + ["surface_dif_n03", "surface_dif_n3", "surface_dif_n10", "vertical", "vertical_n3"])

    # 過程計算の条件を変えたとき、どの粗度の「浸透なし」が最も近いか
    print(T("\n## 過程計算の条件ごとの、浸透なし(力学波)の適合度(1 回目 / 2 回目の雨)",
            "\n## Fit of the no-infiltration runs (dynamic wave) to each variant of the process run (storm 1 / storm 2)"))
    sdyn = [c for c in SDYN if have(c)]
    print(T("| 過程計算の条件 | ", "| Process-run variant | ") + " | ".join(f"n = {nlabel(CASES[c][2])}" for c in sdyn) + " |")
    print("|---|" + "---:|" * len(sdyn))
    for ref in ("process", "process_n1", "process_k3600", "process_k10000", "process_k100000", "process_sd1", "process_l2"):
        if not have(ref):
            continue
        tr, qr = hydro(ref)
        cells = []
        for c in sdyn:
            tc, qc = hydro(c)
            cells.append(" / ".join("%.2f" % nse(tc, qc, qr, a) for a, b in STORMS))
        lab = {"process": T(f"基本(土層 0.5 m、側方 {KBASE} mm/h、斜面の粗度 0.3)", f"base (soil 0.5 m, lateral {KBASE} mm/h, slope roughness 0.3)"),
               "process_n1": T("斜面の粗度 1", "slope roughness 1"),
               "process_sd1": T("土層 1 m", "soil 1 m"),
               "process_l2": T(f"側方 {KSH['process_k3600']} mm/h + 第 2 層", f"lateral {KSH['process_k3600']} mm/h + layer 2")}.get(ref) \
            or T(f"側方 {KSH[ref]} mm/h", f"lateral {KSH[ref]} mm/h")
        print(f"| {lab} | " + " | ".join(cells) + " |")

    # 側方の透水係数と、最も近い粗度
    slope = MASK & ~RW
    s0 = None                                             # 粗度 0.3 の浸透なしの、雨の終わりの斜面の水深 (mm)
    if have("surface"):
        s0 = 1000 * bil("surface", "H", dict((round(tt), k) for k, tt in file_times("surface"))[12])[slope].mean()
    print(T("\n## 側方の透水係数と等価粗度(過程計算に最も近い浸透なしの粗度。到達時刻は 1 回目 / 2 回目の雨、— は雨の間に達しない)",
            "\n## Lateral conductivity and the equivalent roughness (the no-infiltration roughness closest to each process run; times for storm 1 / storm 2, — = not reached during the rain)"))
    print(T("| 側方飽和透水係数 (mm/h) | 飽和域の最大 (%) | 雨の終わりに斜面にある水 (mm) | 同じ水を地表に貯める粗度 | 流出が雨の 90 % に達する時刻 (h) | 最も近い粗度(適合度): 1 回目の雨 | 2 回目の雨 |",
            "| Lateral conductivity (mm/h) | Max. saturated area (%) | Water on the slopes at the end of the rain (mm) | Roughness that stores the same water on the surface | Time when runoff reaches 90 % of the rain (h) | Closest roughness (fit): storm 1 | storm 2 |"))
    print("|---:|---:|---:|---:|---:|---:|---:|")
    for ref, kval in KREFS + [("process_l2", None)]:
        if not have(ref):
            continue
        tr, qr = hydro(ref)
        tsc, fsc = sat_series(ref)
        ftr = dict((round(tt), k) for k, tt in file_times(ref))
        store = 1000 * sum(bil(ref, v, ftr[12])[slope].mean() for v in ("H", "Hg", "Hg2") if has_var(ref, v))
        neq = "—" if s0 is None else "%.1f" % (CASES["surface"][2] * (store / s0) ** (5.0 / 3.0))
        t90 = " / ".join(fmt(reach(tr, qr, st, 0.9), "%.1f") for st in STORMS)
        best = " | ".join(("—" if c is None else f"{nlabel(CASES[c][2])} ({fit:.2f})") for fit, c in best_roughness(ref))
        klab = (T(f"{KSH['process_k3600']} + 第 2 層", f"{KSH['process_k3600']} + layer 2") if kval is None
                else f"{kval}{T('(基本)', ' (base)') if ref == 'process' else ''}")
        print(f"| {klab} | {100 * fsc.max():.1f} | {store:.1f} | {neq} | {t90} | {best} |")

    # 遅れの内訳(斜面の段と河道の段)
    print(T("\n## 雨から出口までの遅れの内訳(2 回目の雨。雨と流出の重心の差を、河道セルへの流入を境に分ける)",
            "\n## Split of the lag from rain to the outlet (storm 2; the difference of the centroids, split at the inflow to the channel cells)"))
    print(T("| 計算 | 斜面の段 (h) | 河道の段 (h) | 合計 (h) | 雨の終わりに斜面にある水 (mm) | 斜面の段が同じになる粗度 |",
            "| Run | Slope stage (h) | Channel stage (h) | Total (h) | Water on the slopes at the end of the rain (mm) | Roughness with the same slope stage |"))
    print("|---|---:|---:|---:|---:|---:|")
    slag = [c for c in sdyn if CASES[c][2] <= 10.0]         # 粗度 30 は 48 時間で出きらないので除く
    for c in slag:
        a1, a2, st = stages(c)
        print(f"| {T('浸透なし', 'no infiltration')} n = {nlabel(CASES[c][2])} | {a1:.1f} | {a2:.1f} | {a1 + a2:.1f} | {st:.1f} | — |")
    for ref, kval in KREFS + [("process_l2", None)]:
        if not have(ref):
            continue
        a1, a2, st = stages(ref)
        klab = (T(f"側方 {KSH['process_k3600']} mm/h + 第 2 層", f"lateral {KSH['process_k3600']} mm/h + layer 2") if kval is None
                else T(f"側方 {kval} mm/h{'(基本)' if ref == 'process' else ''}", f"lateral {kval} mm/h{' (base)' if ref == 'process' else ''}"))
        print(f"| {T('過程計算', 'process run')} {klab} | {a1:.1f} | {a2:.1f} | {a1 + a2:.1f} | {st:.1f} | {fmt(same_lag_roughness(a1, slag), '%.1f')} |")
    lags = [stages(c)[0] for c in slag]
    ns = [CASES[c][2] for c in slag]
    if len(slag) >= 2:
        ex = [np.log(lags[i + 1] / lags[i]) / np.log(ns[i + 1] / ns[i]) for i in range(len(ns) - 1)]
        print(T(f"浸透なしの斜面の段の遅れは、粗度のほぼ {min(ex):.2f}〜{max(ex):.2f} 乗",
                f"the slope-stage lag of the no-infiltration runs grows as roughness to the power {min(ex):.2f}-{max(ex):.2f}"))

    # 浸透なし: 雨と釣り合うまでの時刻と、斜面の水深(マニングの等流なら粗度の 0.6 乗に比例)
    if sdyn:
        print(T("\n## 浸透なし(力学波): 流出が雨の強さに達する時刻と、雨の終わりの斜面の水深(1 回目の雨。— は雨の間に達しない)",
                "\n## No infiltration (dynamic wave): time for the runoff to reach the rain rate, and depth on the slopes at the end of the rain (storm 1; — = not reached during the rain)"))
        print(T("| 斜面の粗度 | ", "| Slope roughness | ") + " | ".join(nlabel(CASES[c][2]) for c in sdyn) + " |")
        print("|---|" + "---:|" * len(sdyn))
        hy = {c: hydro(c) for c in sdyn}
        d12 = {c: 1000 * bil(c, "H", dict((round(tt), k) for k, tt in file_times(c))[12])[slope].mean() for c in sdyn}
        print(T("| 雨の 50 % に達する時刻 (h) | ", "| Time to reach 50 % of the rain (h) | ")
              + " | ".join(fmt(reach(*hy[c], STORMS[0], 0.5), "%.1f") for c in sdyn) + " |")
        print(T("| 雨の 90 % に達する時刻 (h) | ", "| Time to reach 90 % of the rain (h) | ")
              + " | ".join(fmt(reach(*hy[c], STORMS[0], 0.9), "%.1f") for c in sdyn) + " |")
        print(T("| 12 h の斜面の水深の平均 (mm) | ", "| Mean depth on the slopes at 12 h (mm) | ")
              + " | ".join(f"{d12[c]:.1f}" for c in sdyn) + " |")
        if s0 is not None:
            print(T("| 粗度 0.3 の水深 × (n / 0.3)^0.6 (mm) | ", "| Depth for roughness 0.3 × (n / 0.3)^0.6 (mm) | ")
                  + " | ".join(f"{s0 * (CASES[c][2] / CASES['surface'][2]) ** 0.6:.1f}" for c in sdyn) + " |")
    kf = lambda rmm: 290.0 * (AREA / 1e6) ** 0.22 * rmm ** -0.35 / 60.0
    print(T(f"\n角屋・福島の洪水到達時間 tp = 290 A^0.22 re^-0.35 (分): A = {AREA / 1e6:.1f} km2、re = {RAIN_MMH:g} mm/h で {kf(RAIN_MMH):.1f} 時間、"
            f"re = {R30_MMH:g} mm/h で {kf(R30_MMH):.1f} 時間",
            f"\nFlood concentration time of Kadoya & Fukushima, tp = 290 A^0.22 re^-0.35 (min): {kf(RAIN_MMH):.1f} h for A = {AREA / 1e6:.1f} km2 "
            f"and re = {RAIN_MMH:g} mm/h, {kf(R30_MMH):.1f} h for re = {R30_MMH:g} mm/h"))

    # 雨の強さ(基本の雨と強い雨。粗度は両方にある 0.3・1・3 で比べる)
    if have(R30_PROCESS):
        common = {RAIN_MMH: [c for c in ("surface", "surface_n1", "surface_n3") if have(c)], R30_MMH: [c for c in R30_SDYN if have(c)]}
        print(T("\n## 雨の強さと過程計算(時刻は雨の開始から、1 回目 / 2 回目の雨。同じ遅れになる粗度は 0.3・1・3 の遅れから内挿)",
                "\n## Rain intensity and the process run (times from the start of each storm, storm 1 / storm 2; the roughness with the same lag is interpolated from the lags for 0.3, 1 and 3)"))
        print(T("| 雨 (mm/h) | 飽和域の最大 (%) | 雨の 10 % に達する時刻 (h) | 50 % (h) | 90 % (h) | 48 時間の流出高 ÷ 雨 (%) | 12 h の土層の水 (mm) | 斜面の段の遅れ (h) | 同じ遅れになる粗度 | 洪水到達時間の式 (h) |",
                "| Rain (mm/h) | Max. saturated area (%) | Time to reach 10 % of the rain (h) | 50 % (h) | 90 % (h) | Runoff in 48 h / rain (%) | Soil water at 12 h (mm) | Slope-stage lag (h) | Roughness with the same lag | Concentration-time formula (h) |"))
        print("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for rmm, ref in ((RAIN_MMH, "process"), (R30_MMH, R30_PROCESS)):
            tr, qr = hydro(ref)
            tsc, fsc = sat_series(ref)
            ftr = dict((round(tt), k) for k, tt in file_times(ref))
            rr = lambda f: " / ".join(fmt(reach(tr, qr, st, f, rmm), "%.1f") for st in STORMS)
            vol = " / ".join("%.0f" % (100 * event(tr, qr, a)["vol"] / (rmm * (b - a + 1.0 / 60.0))) for a, b in STORMS)
            a1, a2, st = stages(ref)
            print(f"| {rmm:g} | {100 * fsc.max():.1f} | {rr(0.1)} | {rr(0.5)} | {rr(0.9)} | {vol} | {1000 * bil(ref, 'Hg', ftr[12])[MASK].mean():.1f} | "
                  f"{a1:.1f} | {fmt(same_lag_roughness(a1, common[rmm]), '%.1f')} | {kf(rmm):.1f} |")
        print(T("\n## 雨の強さと浸透なし(1 回目 / 2 回目の雨の適合度は、同じ雨の過程計算に対するもの)",
                "\n## Rain intensity and the no-infiltration runs (fits for storm 1 / storm 2 are against the process run under the same rain)"))
        print(T("| 雨 (mm/h) | 斜面の粗度 | 雨の 50 % に達する時刻 (h) | 90 % (h) | 12 h の斜面の水深の平均 (mm) | 斜面の段の遅れ (h) | 河道の段の遅れ (h) | 適合度 |",
                "| Rain (mm/h) | Slope roughness | Time to reach 50 % of the rain (h) | 90 % (h) | Mean depth on the slopes at 12 h (mm) | Slope-stage lag (h) | Channel-stage lag (h) | Fit |"))
        print("|---:|---:|---:|---:|---:|---:|---:|---:|")
        for rmm, ref in ((RAIN_MMH, "process"), (R30_MMH, R30_PROCESS)):
            tr, qr = hydro(ref)
            for c in common[rmm]:
                tc, qc = hydro(c)
                d12 = 1000 * bil(c, "H", dict((round(tt), k) for k, tt in file_times(c))[12])[slope].mean()
                a1, a2, st = stages(c)
                print(f"| {rmm:g} | {nlabel(CASES[c][2])} | {fmt(reach(tc, qc, STORMS[0], 0.5, rmm), '%.1f')} | {fmt(reach(tc, qc, STORMS[0], 0.9, rmm), '%.1f')} | "
                      f"{d12:.1f} | {a1:.1f} | {a2:.1f} | " + " / ".join("%.2f" % nse(tc, qc, qr, a) for a, b in STORMS) + " |")
        a1, a2, st = stages(R30_PROCESS)
        b1, b2, sb = stages("process")
        print(T(f"過程計算の河道の段の遅れ: 雨 {RAIN_MMH:g} mm/h で {b2:.1f} 時間、{R30_MMH:g} mm/h で {a2:.1f} 時間。雨の終わりに斜面にある水: {sb:.1f} mm と {st:.1f} mm",
                f"channel-stage lag of the process run: {b2:.1f} h under {RAIN_MMH:g} mm/h, {a2:.1f} h under {R30_MMH:g} mm/h; water on the slopes at the end of the rain: {sb:.1f} mm and {st:.1f} mm"))

    # 第 2 層を置いた計算: 土層と第 2 層の満ちたセルの割合と、貯まっている水
    if have("process_l2"):
        cap2 = param_value("param.txt", "gw2_depth") * param_value("param.txt", "gw2_sy")
        ft2 = dict((round(tt), k) for k, tt in file_times("process_l2"))
        print(T("\n## 第 2 層を置いた計算(process_l2): 満ちたセルの割合 (%) と、流域平均の水 (mm)",
                "\n## Run with layer 2 (process_l2): share of full cells (%) and catchment-mean water (mm)"))
        print(T("| 時刻 (h) | 流出 (mm/h) | 第 2 層が満ちたセル | 土層が満ちたセル(飽和域) | 第 2 層の水 | 土層の水 | 地表の水 |",
                "| Time (h) | Runoff (mm/h) | Cells with layer 2 full | Cells with the soil full (saturated area) | Water in layer 2 | Soil water | Surface water |"))
        print("|---:|---:|---:|---:|---:|---:|---:|")
        t2, q2 = hydro("process_l2")
        for th in (2, 3, 4, 6, 12, 24, 48):
            h, hg, hg2 = (bil("process_l2", v, ft2[th]) for v in ("H", "Hg", "Hg2"))
            print(f"| {th} | {np.interp(th, t2, q2):.2f} | {100 * (hg2[MASK] >= cap2 - SAT_TOL).mean():.1f} | {100 * (hg[MASK] >= CAP - SAT_TOL).mean():.1f} | "
                  f"{1000 * hg2[MASK].mean():.1f} | {1000 * hg[MASK].mean():.1f} | {1000 * h[MASK].mean():.1f} |")

    # 地表に載る水(流域平均の貯留高と、河道セル以外の水深)
    print(T("\n## 地表の水(流域平均の貯留高の最大と、雨の終わりの河道セル以外の水深)",
            "\n## Surface water (maximum catchment-mean storage, and depth on non-channel cells at the end of each storm)"))
    print(T("| ケース | 斜面の粗度 | 地表の水の最大 (mm) | 12 h の水深の平均 (mm) | 12 h の水深の最大 (m) | 60 h の水深の平均 (mm) |",
            "| Case | Slope roughness | Max. surface water (mm) | Mean depth at 12 h (mm) | Max. depth at 12 h (m) | Mean depth at 60 h (mm) |"))
    print("|---|---:|---:|---:|---:|---:|")
    for case in order + [R30_PROCESS] + list(R30_SDYN):
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
    for case in order + [R30_PROCESS] + list(R30_SDYN):
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
    fig_equivalent()
    fig_intensity()
    fig_layer2()


if __name__ == "__main__":
    main()
