#!/usr/bin/env python3
"""catchment_metal の図と数表(事前に make run で 8 ケースを計算しておく)。

  figs/mechanism.png  各ステップで加える機構の模式図(データを使わない)
  figs/setup.png      流域の地形・河道・ため池・農地・鉱山・観測点と、降雨・負荷の時系列
  figs/step1.png … figs/step6.png、figs/step6b.png  各ステップの結果(前のステップとの
                      比較。ステップ 6 は蒸発散なしのステップ 4、6b は抑制なしのステップ 6 と
                      比べ、(c) を水の行き先にする)
  figs/summary.png    物質の行き先の比較(8 ケース)
引数 en で英語ラベル版を en/figs/ に描く(データと描画処理は共通)。
数表(README の表)は標準出力に書く。
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm, LightSource
from matplotlib.patches import Rectangle, Circle
import matplotlib.patheffects as pe

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)

NX, NY, DX = 80, 48, 250.0
KM = DX / 1000.0
EXT = [0, NX * KM, 0, NY * KM]          # x 東向き、y 北向き (km)。行 1 が北端
DAY = 86400.0
TEND = 180                               # 計算日数
STORMS = [3 + 10 * k for k in range(10)]  # 降雨の開始日(各 3 時間、20 mm/h)
FARM_END = 60                            # 農地の負荷の終了日
MG2UG = 1000.0                           # mg/L -> µg/L

CASES = ["step1", "step2", "step3", "step4", "step5", "step5_notank", "step6", "step6b"]
TANK_CASES = ("step4", "step5", "step6", "step6b")  # ため池ありの地形
ET_CASES = ("step6", "step6b")           # 蒸発散あり((c) を水の行き先にする)
LABEL = {"step1": T("1 地表水", "1 surface water"),
         "step2": T("2 +地下水流動", "2 +groundwater flow"),
         "step3": T("3 +吸着の遅れ", "3 +sorption delay"),
         "step4": T("4 +ため池", "4 +tanks"),
         "step5": T("5 粒子態+ため池", "5 particulate + tanks"),
         "step5_notank": T("5' 粒子態・ため池なし", "5' particulate, no tanks"),
         "step6": T("6 +蒸発散(溶存態・ため池)", "6 +evapotranspiration (dissolved, tanks)"),
         "step6b": T("6b +土の乾き具合による抑制", "6b +reduction by dry soil")}
PET = 4.0                                # ステップ 6・6b の可能蒸発散 (mm/day)
HGLIM = 0.05                             # ステップ 6b の evap_hglim (m)
AREA = 3430 * DX * DX                    # 流域(陸域)の面積 (m2)
RAIN_MM = 600.0                          # 雨の総量 (mm)
# 観測点(プローブ番号 = 測線番号。param_common.txt の並び)
GAUGES = ["G1", "G2", "G3", "G4", "G5"]
GCOL = {"G1": "#c0392b", "G2": "#e67e22", "G3": "#27ae60", "G4": "#2980b9", "G5": "#2c3e50"}
GDESC = {"G1": T("G1 鉱山の下流(T1)", "G1 below the mine (T1)"),
         "G2": T("G2 本川(T1 合流後)", "G2 main river (below T1)"),
         "G3": T("G3 農地の支川の出口(T2)", "G3 farm tributary outlet (T2)"),
         "G4": T("G4 本川(T2 合流後)", "G4 main river (below T2)"),
         "G5": T("G5 河口の近く", "G5 near the mouth")}
L_SEA = 6                                # 海への出口の測線番号


# ---------------------------------------------------------------- 入力・結果の読み込み
def cells():
    out = {}
    for line in open("data/cells.txt"):
        p = line.split()
        if p[0].startswith("tank"):
            out[p[0]] = dict(spill=(int(p[2]), int(p[3])), fsl=float(p[5]),
                             vol=float(p[9]), deep=(int(p[11]), int(p[12])))
        else:
            out[p[0]] = (int(p[1]), int(p[2]))
    return out


def xy(ij):
    """セル番号 (i, j)(1 始まり、j は北から)をセル中心の (x, y) km(y は北向き)に。"""
    return (ij[0] - 0.5) * KM, (NY - ij[1] + 0.5) * KM


def data(name):
    return np.loadtxt(f"data/{name}.txt")


def bil(case, var, k):
    return np.fromfile(f"result_{case}/{var}{k:04d}.bil", dtype="<f4").reshape(NY, NX).astype(float)


def ledger(case):
    return np.genfromtxt(f"result_{case}/wq.csv", delimiter=",", names=True)


def probe(case, k):
    """列: 0 時(h) 1 分 2 z 3 h 4 u 5 v 6 |V| 7 q 8 hg 9 hs 10 sd 11 C(mg/L) 12 cq"""
    return np.loadtxt(f"result_{case}/probes/probe{k:04d}.csv", delimiter=",", comments="#")


def flux(case, k):
    """列: 0 時(h) 1 分 2 Q(m3/s) 3 Hmax 4 Vmax 5 B 6 L(g/s) 7 Lcum(kg)"""
    return np.loadtxt(f"result_{case}/fluxes/flux{k:04d}.csv", delimiter=",", comments="#")


def hillshade(z, mask):
    ls = LightSource(azdeg=315, altdeg=45)
    hs = ls.hillshade(np.where(mask > 0, z, np.nan), vert_exag=8, dx=DX, dy=DX)
    return np.ma.masked_where(mask == 0, hs)


def storm_bands(ax, color="#9ecae1", alpha=0.25):
    for s in STORMS:
        ax.axvspan(s, s + 0.125, color=color, alpha=alpha, lw=0)


def _arrow(ax, x0, y0, x1, y1, color, lw=2.0, style="-|>", ls="-"):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw, ls=ls, shrinkA=0, shrinkB=0))


# ---------------------------------------------------------------- 模式図
C_WATER, C_SOIL, C_GW, C_METAL, C_FARM = "#9ecae1", "#e8d9b5", "#2c7fb8", "#c0392b", "#d9c55a"
C_ET = "#e6550d"                         # 蒸発散


def _num(ax, x, y, n, color="k"):
    ax.add_patch(Circle((x, y), 0.17, facecolor="white", edgecolor=color, lw=1.2, zorder=6))
    ax.text(x, y, str(n), ha="center", va="center", fontsize=8.5, color=color, zorder=7)


def mechanism():
    """流域の断面(模式。縮尺は誇張): 斜面の農地 → ため池 → 河道 → 海と、鉱山の排水。"""
    fig, ax = plt.subplots(figsize=(13, 5.6))
    x = np.linspace(0, 13, 1301)
    # 地表: 丘陵 → 農地の斜面 → ため池の窪地と堤 → 河道 → 海
    zs = 4.2 - 0.38 * x
    zs = np.where((x > 5.6) & (x < 7.6), np.minimum(zs, 1.15 + 0.5 * ((x - 6.6) / 1.0) ** 2), zs)
    zs = np.where((x >= 7.6) & (x <= 7.9), 2.0, zs)                       # 堤
    zs = np.where((x > 7.9) & (x < 10.0), 1.35 - 0.12 * (x - 7.9), zs)
    zs = np.where((x >= 10.0) & (x <= 10.6), 0.35, zs)                     # 河道
    zs = np.where((x > 10.6) & (x < 11.6), 0.9 - 0.4 * (x - 10.6), zs)
    zs = np.where(x >= 11.6, -0.2, zs)                                     # 海
    zb = 2.6 - 0.362 * x                                                   # 土層の底(基盤)
    land = x < 11.6
    ax.fill_between(x[land], zb[land], zs[land], color=C_SOIL, zorder=1)
    ax.fill_between(x[land], -3.0, zb[land], color="#cfc6b8", zorder=0)
    ax.fill_between(x[x >= 11.6], -3.0, 0.0, color="#6baed6", zorder=0)
    ax.plot(x[land], zs[land], color="0.25", lw=1.0, zorder=2)
    # 地下水位(谷で地表に出る = 湧出)
    wt = np.minimum(zs - 0.05, np.interp(x, [0.3, 4.0, 5.6, 7.6, 9.9, 10.65, 11.6],
                                         [2.9, 1.55, 1.1, 0.95, 0.6, 0.6, -0.2]))
    ax.plot(x[land & (x > 0.3)], wt[land & (x > 0.3)], color=C_GW, ls="--", lw=1.2, zorder=3)
    # ため池の水と河道の水
    pond = (x > 5.65) & (x < 7.6)
    ax.fill_between(x[pond], zs[pond], 1.75, where=zs[pond] < 1.75, color=C_WATER, zorder=2)
    riv = (x >= 9.95) & (x <= 10.65)
    ax.fill_between(x[riv], zs[riv], 0.75, color=C_WATER, zorder=2)
    # 農地(斜面)と鉱山
    for xf in np.arange(2.2, 5.2, 0.25):
        zf = 4.2 - 0.38 * xf
        ax.plot([xf, xf + 0.12], [zf + 0.04, zf + 0.04 - 0.045], color="#7a8f1f", lw=2.2, zorder=3)
    ax.text(3.6, 3.55, T("農地(面源: 施用期 60 日)", "farmland (area source, 60-day application)"),
            ha="center", fontsize=8.5, color="#5a6a10")
    ax.add_patch(Rectangle((0.15, 4.1), 0.55, 0.38, color="0.35", zorder=4))
    ax.text(0.42, 4.65, T("鉱山(点源: 排水 0.05 m³/s)", "mine (point source: 0.05 m³/s effluent)"),
            ha="left", fontsize=8.5)
    _arrow(ax, 0.75, 4.05, 1.45, 3.62, C_METAL, lw=2.2)
    # 雨
    for xr in np.arange(0.6, 11.4, 0.55):
        _arrow(ax, xr, 5.75, xr - 0.08, 5.2, "#6baed6", lw=1.0)
    ax.text(11.5, 5.45, T("雨(10 回 × 60 mm)", "rain (10 × 60 mm)"), fontsize=8.5, color="#3182bd")
    # ① 地表流と浸透
    _arrow(ax, 4.5, 2.75, 5.45, 2.28, C_METAL, lw=2.4)
    _num(ax, 4.75, 3.05, 1)
    ax.text(4.95, 2.95, T("地表流(出水で川へ)", "surface runoff (in storms)"), fontsize=8)
    for xi in (1.6, 2.6, 3.6):
        zi = 4.2 - 0.38 * xi
        _arrow(ax, xi, zi - 0.1, xi, zi - 0.75, C_GW, lw=1.6)
    _num(ax, 1.25, 3.1, 1)
    ax.text(0.15, 2.05, T("浸透(溶存態は水に同伴。鉱山の排水も\n河床から浸透する。ステップ 1 では\n地下で行き止まり)",
                          "infiltration (dissolved metal goes with the\nwater; mine water also sinks into the\nriver bed; a dead end in step 1)"),
            fontsize=7.8, color="0.15", va="top")
    # ② 地下水の側方流動と湧出(基底流)
    for xa in (4.3, 6.2, 8.1):
        _arrow(ax, xa, wt[int(xa * 100)] - 0.45, xa + 1.0, wt[int((xa + 1.0) * 100)] - 0.45, C_GW, lw=1.8)
    _arrow(ax, 9.55, 0.05, 9.98, 0.42, C_GW, lw=1.8)
    _num(ax, 6.0, -0.2, 2, C_GW)
    ax.text(6.25, -0.3, T("地下水の流れ → 谷で湧き出して基底流", "groundwater flow → seeps out in the valley (baseflow)"),
            fontsize=8, color=C_GW)
    # ③ 吸着の遅れ
    for k, xg in enumerate(np.arange(2.9, 5.2, 0.32)):
        yg = 4.2 - 0.38 * xg - 1.15 - 0.12 * (k % 2)
        ax.add_patch(Circle((xg, yg), 0.06, color="#8c6d46", zorder=4))
        ax.add_patch(Circle((xg + 0.07, yg + 0.05), 0.028, color=C_METAL, zorder=5))
    _num(ax, 2.0, 0.25, 3, "#8c6d46")
    ax.text(2.25, 0.25, T("土粒子への吸着: 物質は地下水の 1/R の\n速さでしか動かない(R = 遅延化係数)",
                          "sorption to soil grains: the metal moves at\n1/R of the groundwater speed (R: retardation)"),
            fontsize=7.8, color="#6b4f2a", va="center")
    # ④ ため池
    _num(ax, 7.1, 2.62, 4, "#1f78b4")
    ax.text(7.33, 2.62, T("ため池: 水を貯めて混ぜ、満水であふれる", "tank: stores and mixes water, spills when full"),
            fontsize=8, color="#1f78b4", va="center")
    _arrow(ax, 7.35, 1.85, 8.3, 1.3, C_WATER, lw=2.2)
    # ⑤ 粒子態の沈降と再懸濁
    for xp in np.arange(6.0, 7.3, 0.18):
        ax.add_patch(Circle((xp, 1.15 + 0.5 * ((xp - 6.6) / 1.0) ** 2 + 0.05), 0.035, color=C_METAL, zorder=4))
    for xp in (6.2, 6.6, 7.0):
        _arrow(ax, xp, 1.62, xp, 1.33, C_METAL, lw=1.1)
    _num(ax, 8.35, 2.15, 5, C_METAL)
    ax.text(8.58, 2.2, T("粒子態: 流れの緩い所で沈み(ため池)、\n出水のせん断で再び流れに戻る(河道)",
                         "particulate: settles where the flow is slow (tank)\nand is re-suspended by flood shear (channel)"),
            fontsize=7.8, color=C_METAL, va="top")
    _arrow(ax, 10.15, 0.45, 10.35, 0.68, C_METAL, lw=1.2, style="-|>")
    _arrow(ax, 10.55, 0.68, 10.75, 0.45, C_METAL, lw=1.2, style="-|>")
    # ⑥ 蒸発散(水だけが抜け、物質は残る)
    for xe in (5.95, 6.35, 6.75):
        _arrow(ax, xe, 1.85, xe + 0.06, 2.45, C_ET, lw=1.5)
    for xe in (9.3, 9.65):
        ze = 1.35 - 0.12 * (xe - 7.9)
        _arrow(ax, xe, ze + 0.04, xe + 0.06, ze + 0.48, C_ET, lw=1.5)
    _num(ax, 8.35, 3.3, 6, C_ET)
    ax.text(8.58, 3.3, T("蒸発散: 水だけが抜け、物質は残る(ため池で濃縮)。\n乾季には土の水が尽きて基底流が減る",
                         "evapotranspiration: only water leaves, the metal stays\n(tanks concentrate); in the dry season the soil water\nruns out and the baseflow shrinks"),
            fontsize=7.8, color=C_ET, va="center")
    # 河道と海
    ax.text(10.3, 1.0, T("河道", "river"), ha="center", fontsize=8.5, color="#1f78b4")
    _arrow(ax, 10.9, 0.5, 12.3, 0.1, C_METAL, lw=2.4)
    ax.text(12.3, -0.75, T("海へ(out_sea_g)", "to the sea\n(out_sea_g)"), ha="center", fontsize=8.5, color="w")
    ax.text(12.2, -2.4, T("海域マスク", "sea mask"), ha="center", fontsize=8, color="w")
    ax.set_xlim(0, 13)
    ax.set_ylim(-3.0, 6.0)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in (C_SOIL, C_WATER)] + \
              [plt.Line2D([0], [0], color=C_GW, ls="--"), plt.Line2D([0], [0], color=C_METAL, lw=2.4)]
    ax.legend(handles, [T("土層(帯水層)", "soil layer (aquifer)"), T("地表水", "surface water"),
                        T("地下水位", "water table"), T("物質の主な経路", "main pathways of the metal")],
              loc="lower left", fontsize=8, ncol=4, frameon=False, bbox_to_anchor=(0.0, -0.06))
    ax.set_title(T("番号はその機構を加えるステップ(断面の模式図。縮尺は誇張)",
                   "Numbers = the step that adds the mechanism (schematic section, exaggerated)"),
                 fontsize=10, loc="left")
    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/mechanism.png", dpi=110)
    plt.close(fig)


# ---------------------------------------------------------------- 設定の図
def setup():
    c = cells()
    z = data("z_tank")
    mask, sw = data("mask"), data("sw")
    rw, tid = data("rw_tank"), data("tank_id")
    farm = np.loadtxt("data/farm_cells.txt", dtype=int)
    fig = plt.figure(figsize=(13, 5.6))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.75, 1], height_ratios=[1, 1], wspace=0.18, hspace=0.45)
    ax = fig.add_subplot(gs[:, 0])
    land = (mask > 0) & (sw == 0)
    zz = np.ma.masked_where(~land, z)
    im = ax.imshow(zz, extent=EXT, cmap="terrain", vmin=-20, vmax=190, origin="upper")
    ax.imshow(hillshade(z, land.astype(int)), extent=EXT, cmap="gray", alpha=0.25, origin="upper")
    ax.contour(np.ma.masked_where(~land, z), levels=np.arange(10, 200, 10), colors="0.35",
               linewidths=0.3, extent=EXT, origin="upper")
    ax.imshow(np.ma.masked_where(rw == 0, rw), extent=EXT, cmap="Blues", vmin=0, vmax=1.2, origin="upper")
    ax.imshow(np.ma.masked_where(tid == 0, tid), extent=EXT, cmap="cool", vmin=0, vmax=0.5, origin="upper")
    ax.imshow(np.ma.masked_where(sw == 0, sw), extent=EXT, cmap="Blues", vmin=0, vmax=1.0, origin="upper")
    fm = np.zeros((NY, NX))
    fm[farm[:, 1] - 1, farm[:, 0] - 1] = 1
    ax.imshow(np.ma.masked_where(fm == 0, fm), extent=EXT, cmap="Wistia", vmin=0, vmax=1.3, alpha=0.4, origin="upper")
    ax.fill_between([], [], color=plt.get_cmap("Wistia")(1 / 1.3), alpha=0.4,
                    label=T("農地(290 セル、1812 ha)", "farmland (290 cells, 1812 ha)"))
    mx, my = xy(c["mine"])
    ax.plot(mx, my, marker="*", color="k", ms=14, mec="w", ls="none", label=T("鉱山の排水口", "mine outlet"))
    halo = [pe.withStroke(linewidth=2.5, foreground="w")]
    for g in GAUGES:
        gx, gy = xy(c[g])
        ax.plot(gx, gy, marker="^", color=GCOL[g], ms=8, mec="k", ls="none")
        dx, dy = (-0.9, 0.3) if g == "G5" else (0.15, 0.25)
        ax.text(gx + dx, gy + dy, g, fontsize=9, color="k", path_effects=halo)
    for k in (1, 2, 3):
        tx, ty = xy(c[f"tank{k}"]["deep"])
        ax.text(tx - 1.1, ty - 0.15, f"P{k}", fontsize=8.5, color="#7a0177", path_effects=halo)
    ax.text(19.55, 7.6, T("入り江\n(海域\nマスク)", "bay\n(sea\nmask)"), fontsize=7, ha="center", va="bottom")
    for name, (px, py) in {"T1": (4.4, 10.4), "T2": (12.4, 0.6), "T3": (15.5, 10.4), "T4": (2.6, 3.0),
                           "T5": (16.6, 1.0)}.items():
        ax.text(px, py, name, fontsize=9, color="#08519c", style="italic", path_effects=halo)
    ax.text(0.5, 6.85, T("本川", "main river"), fontsize=9, color="#08519c", style="italic", path_effects=halo)
    ax.legend(loc="lower left", fontsize=8, framealpha=0.85)
    ax.set_xlabel("x (km)")
    ax.set_ylabel("y (km)")
    ax.set_title(T("(a) 流域(250 m 格子、陸域 214 km²)。P1〜P3 = ため池 1〜3",
                   "(a) Catchment (250 m grid, land 214 km²). P1–P3 = tanks 1–3"), fontsize=10, loc="left")
    cb = fig.colorbar(im, ax=ax, shrink=0.75, pad=0.02)
    cb.set_label(T("地盤高 (m)", "ground elevation (m)"))
    # 降雨
    ax1 = fig.add_subplot(gs[0, 1])
    t = np.arange(0, TEND + 1)
    for s in STORMS:
        ax1.bar(s, 60, width=1.5, color="#3182bd", align="edge")
    ax1.set_xlim(0, TEND)
    ax1.set_ylim(0, 75)
    ax1.set_ylabel(T("日雨量 (mm)", "daily rain (mm)"))
    ax1.set_title(T("(b) 雨: 20 mm/h × 3 時間を 10 日おきに 10 回", "(b) Rain: 20 mm/h × 3 h, ten times every 10 days"),
                  fontsize=10, loc="left")
    ax1.axvspan(100, TEND, color="0.9", lw=0)
    ax1.text(140, 62, T("乾季(雨なし)", "dry season (no rain)"), ha="center", fontsize=8.5)
    ax1.text(50, 66, T("雨季", "wet season"), ha="center", fontsize=8.5)
    # 負荷
    ax2 = fig.add_subplot(gs[1, 1])
    farm_g = 0.002 * len(farm) * 6.25 * 1000.0      # kg/ha/day × ha -> g/day
    ax2.step([0, FARM_END, FARM_END, TEND], np.array([farm_g, farm_g, 0, 0]) / 1000.0, where="post",
             color="#7a8f1f", lw=2, label=T("農地 0.002 kg/ha/日(計 217 kg)", "farmland 0.002 kg/ha/day (217 kg in all)"))
    ax2.plot([0, TEND], [0.025 * DAY / 1000.0] * 2, color="k", lw=2,
             label=T("鉱山 0.025 g/s = 0.5 mg/L(計 389 kg)", "mine 0.025 g/s = 0.5 mg/L (389 kg in all)"))
    ax2.set_xlim(0, TEND)
    ax2.set_ylim(0, 4.5)
    ax2.set_xlabel(T("経過日", "day"))
    ax2.set_ylabel(T("負荷 (kg/日)", "load (kg/day)"))
    ax2.legend(fontsize=8, loc="upper right")
    ax2.set_title(T("(c) 物質の負荷(全ステップ共通)", "(c) Metal loads (all steps)"), fontsize=10, loc="left")
    fig.savefig(f"{FIGDIR}/setup.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------- 結果の図
D_WET, D_DRY = 54, 150                   # 地図の日: 雨季(6 回目の雨の翌日)と乾季
PREV = {"step2": "step1", "step3": "step2", "step4": "step3", "step5": "step5_notank", "step6": "step4",
        "step6b": "step6"}
# 前のステップと比べる観測点(ため池の効果は農地の支川の出口 G3 に、蒸発散の効果は
# 鉱山の下流 G1 と河口近くの G5 の乾季に出る)
PREV_GAUGE = {"step2": ["G5"], "step3": ["G5"], "step4": ["G3"], "step5": ["G3"], "step6": ["G1", "G5"],
              "step6b": ["G1", "G5"]}
STORE_NORM = LogNorm(1e-3, 3.0)          # 留まる物質量 (g/m2)
C_NORM = LogNorm(0.3, 500.0)             # 濃度 (µg/L)


def base_map(ax, tank):
    """地図の下地: 陰影・河道・ため池・海。"""
    z = data("z_tank" if tank else "z_notank")
    mask, sw = data("mask"), data("sw")
    rw = data("rw_tank" if tank else "rw_notank")
    land = ((mask > 0) & (sw == 0)).astype(int)
    ax.imshow(hillshade(z, land), extent=EXT, cmap="gray", vmin=-1.2, vmax=1.4, origin="upper")
    ax.imshow(np.ma.masked_where(rw == 0, rw), extent=EXT, cmap="Blues", vmin=0, vmax=2.5, origin="upper")
    if tank:
        tid = data("tank_id")
        ax.contour(np.where(tid > 0, 1.0, 0.0), levels=[0.5], colors="#7a0177", linewidths=0.8,
                   extent=EXT, origin="upper")
    ax.imshow(np.ma.masked_where(sw == 0, sw), extent=EXT, cmap="Blues", vmin=0, vmax=1.0, origin="upper")
    ax.set_xlim(0, NX * KM)
    ax.set_ylim(0, NY * KM)
    ax.set_xticks([0, 5, 10, 15, 20])
    ax.set_yticks([0, 4, 8, 12])
    ax.tick_params(labelsize=7)


def conc_map(ax, case, day, title):
    c = bil(case, "C", day) * MG2UG
    h = bil(case, "H", day)
    base_map(ax, case in TANK_CASES)
    show = np.ma.masked_where((h <= 1e-3) | (c <= 0.01), np.maximum(c, C_NORM.vmin))
    im = ax.imshow(show, extent=EXT, cmap="viridis", norm=C_NORM, origin="upper", interpolation="nearest")
    ax.set_title(title, fontsize=9, loc="left")
    return im


def store_map(ax, case, day, title):
    """地中(Cg、g/m2)と地表の堆積(B、kg/ha -> g/m2)に留まる物質量。"""
    st = bil(case, "Cg", day) if os.path.exists(f"result_{case}/Cg{day:04d}.bil") else np.zeros((NY, NX))
    if os.path.exists(f"result_{case}/B{day:04d}.bil"):
        st = st + bil(case, "B", day) / 10.0
    base_map(ax, case in TANK_CASES)
    show = np.ma.masked_where(st <= STORE_NORM.vmin * 0.1, np.maximum(st, STORE_NORM.vmin))
    im = ax.imshow(show, extent=EXT, cmap="YlGnBu", norm=STORE_NORM, origin="upper", interpolation="nearest")
    ax.set_title(title, fontsize=9, loc="left")
    return im


def prev_label(case, g):
    if case == "step5":
        return T(f"{g}(ため池なし 5')", f"{g} (no tanks, 5')")
    if case == "step6":
        return T(f"{g}(蒸発散なし 4)", f"{g} (no evapotranspiration, 4)")
    if case == "step6b":
        return T(f"{g}(抑制なし 6)", f"{g} (no reduction, 6)")
    return T(f"{g}(前のステップ)", f"{g} (previous step)")


PREV_LS = ["--", ":"]                    # 比べる観測点が 2 つのときの線種


def series_q(ax, case, prev):
    own = (["G1"] if "G1" in PREV_GAUGE.get(case, []) else []) + ["G3", "G5"]   # 6・6b は本文が引く G1 も
    for g in own:
        d = flux(case, GAUGES.index(g) + 1)
        ax.plot(d[:, 0] / 24, np.maximum(d[:, 2], 1e-4), color=GCOL[g], lw=0.9, label=GDESC[g])
    if prev:
        for g, ls in zip(PREV_GAUGE[case], PREV_LS):
            d = flux(prev, GAUGES.index(g) + 1)
            ax.plot(d[:, 0] / 24, np.maximum(d[:, 2], 1e-4), color="0.55", lw=0.8, ls=ls,
                    label=prev_label(case, g))
    ax.set_yscale("log")
    ax.set_ylim(1e-3, 1e3)
    ax.set_xlim(0, TEND)
    ax.set_ylabel(T("流量 (m³/s)", "discharge (m³/s)"))
    ax.legend(fontsize=7, loc="upper right", ncol=1)
    storm_bands(ax)


def series_c(ax, case, prev):
    for g, k in (("G1", 1), ("G3", 3), ("G5", 5)):
        p = probe(case, k)
        cc = np.where(p[:, 3] > 1e-3, p[:, 11] * MG2UG, np.nan)
        ax.plot(p[:, 0] / 24, cc, color=GCOL[g], lw=0.9, label=GDESC[g])
    if prev:
        for g, ls in zip(PREV_GAUGE[case], PREV_LS):
            p = probe(prev, GAUGES.index(g) + 1)
            cc = np.where(p[:, 3] > 1e-3, p[:, 11] * MG2UG, np.nan)
            ax.plot(p[:, 0] / 24, cc, color="0.55", lw=0.8, ls=ls, label=prev_label(case, g))
    ax.set_yscale("log")
    ax.set_ylim(0.1, 2000)
    ax.set_xlim(0, TEND)
    ax.set_ylabel(T("濃度 (µg/L)", "concentration (µg/L)"))
    ax.legend(fontsize=7, loc="upper right")
    storm_bands(ax)


def fractions(case):
    w = ledger(case)
    inp = w["in_point_g"] + w["in_area_g"]
    tot = np.maximum(inp, 1e-9)
    return dict(t=w["time_s"] / DAY, inp=inp, sea=w["out_sea_g"], surf=w["mass_surface_g"],
                gw=w["mass_gw_g"], pool=w["mass_pool_g"])


def series_budget(ax, case, prev):
    f = fractions(case)
    kg = 1e-3
    ax.stackplot(f["t"], f["sea"] * kg, f["surf"] * kg, f["gw"] * kg, f["pool"] * kg,
                 colors=["#08519c", "#9ecae1", "#d8b365", "#7fbc41"],
                 labels=[T("海へ流出", "exported to the sea"), T("地表水の中", "in surface water"),
                         T("地中(浸透した分)", "in the ground (infiltrated)"),
                         T("地表に堆積", "deposited on the surface")])
    ax.plot(f["t"], f["inp"] * kg, color="k", lw=1.0, label=T("累積投入", "cumulative input"))
    if prev:
        g = fractions(prev)
        lab = T("海へ流出(ため池なし 5')", "exported (no tanks, 5')") if case == "step5" else \
            T("海へ流出(蒸発散なし 4)", "exported (no evapotranspiration, 4)") if case == "step6" else \
            T("海へ流出(抑制なし 6)", "exported (no reduction, 6)") if case == "step6b" else \
            T("海へ流出(前のステップ)", "exported (previous step)")
        ax.plot(g["t"], g["sea"] * kg, color="0.4", lw=1.0, ls="--", label=lab)
    ax.set_xlim(0, TEND)
    ax.set_ylim(0, 650)
    ax.set_ylabel(T("物質量 (kg)", "mass (kg)"))
    ax.legend(fontsize=7, loc="upper left")


def rain_cum(t):
    """雨の累積 (mm)。降雨は STORMS の日の 0 時から 3 時間、20 mm/h(param_common.txt)。"""
    out = np.zeros_like(t)
    for d0 in STORMS:
        out += 20.0 * np.clip((t - d0) * 24.0, 0.0, 3.0)
    return out


def water(case):
    """水の行き先(流域平均 mm): 雨・蒸発散・海への流出の累積と、流域の貯留(Log.txt の S_total)。"""
    f = flux(case, L_SEA)
    t = f[:, 0] / 24
    dt = np.diff(np.concatenate(([0.0], f[:, 0]))) * 3600.0
    out = dict(t=t, rain=rain_cum(t), sea=np.cumsum(f[:, 2] * dt) / AREA * 1e3)
    et = np.zeros_like(t)
    if os.path.exists(f"result_{case}/evap.csv"):
        e = np.genfromtxt(f"result_{case}/evap.csv", delimiter=",", names=True)
        et = np.interp(t, e["time_s"] / DAY, e["ev_total_m3"] / AREA * 1e3)
    out["et"] = et
    ts, st = [], []
    for line in open(f"result_{case}/Log.txt"):
        p = line.split()
        if len(p) >= 5 and p[1].endswith("%"):      # 時の欄は 1000 時間で桁あふれするので進捗から
            ts.append(float(p[1][:-1]) / 100.0 * TEND)
            st.append(float(p[4]) * 1e3)
    out["ts"], out["store"] = np.array(ts), np.array(st)
    return out


def series_water(ax, case, prev):
    w = water(case)
    ax.plot(w["t"], w["rain"], color="k", lw=1.0, label=T("雨(累積)", "rain (cumulative)"))
    ax.plot(w["t"], w["et"], color=C_ET, lw=1.4, label=T("蒸発散(累積)", "evapotranspiration (cumulative)"))
    ax.plot(w["t"], w["sea"], color="#08519c", lw=1.4, label=T("海へ流出(累積)", "outflow to the sea (cumulative)"))
    ax.plot(w["ts"], w["store"], color="#a6761d", lw=1.4, marker="o", ms=2.5,
            label=T("流域の貯留(地表 + 地中)", "storage in the catchment (surface + ground)"))
    if prev:
        g = water(prev)
        tag = T("蒸発散なし 4", "no ET, 4") if prev == "step4" else T("抑制なし 6", "no reduction, 6")
        ax.plot(g["t"], g["sea"], color="0.4", lw=1.0, ls="--", label=T(f"海へ流出({tag})", f"outflow ({tag})"))
        ax.plot(g["ts"], g["store"], color="0.4", lw=1.0, ls=":", label=T(f"貯留({tag})", f"storage ({tag})"))
        if prev != "step4":
            ax.plot(g["t"], g["et"], color=C_ET, lw=1.0, ls="--", label=T(f"蒸発散({tag})", f"evapotranspiration ({tag})"))
    ax.set_xlim(0, TEND)
    ax.set_ylim(0, 650)
    ax.set_xlabel(T("経過日", "day"), fontsize=8)
    ax.set_ylabel(T("流域平均の水深 (mm)", "depth over the catchment (mm)"), fontsize=8)
    ax.tick_params(labelsize=8)
    ax.legend(fontsize=6.5, loc="upper left")
    storm_bands(ax)


def step_figure(case, title):
    prev = PREV.get(case)
    fig = plt.figure(figsize=(15, 6.2))
    gs = fig.add_gridspec(2, 3, height_ratios=[0.82, 1.0], hspace=0.3, wspace=0.18,
                          top=0.93, bottom=0.08)
    ax = [fig.add_subplot(gs[0, k]) for k in range(3)]
    im = conc_map(ax[0], case, D_WET, T(f"(a) 地表水の濃度 {D_WET} 日目(雨季)",
                                         f"(a) Concentration, day {D_WET} (wet season)"))
    conc_map(ax[1], case, D_DRY, T(f"(b) 地表水の濃度 {D_DRY} 日目(乾季)", f"(b) Concentration, day {D_DRY} (dry season)"))
    cb = fig.colorbar(im, ax=ax[:2], shrink=0.85, pad=0.01, aspect=30)
    cb.set_label(T("濃度 (µg/L)", "concentration (µg/L)"))
    if case in ET_CASES:
        series_water(ax[2], case, prev)
        if case == "step6b":
            ttl = T(f"(c) 水の行き先(PET {PET:g} mm/day、evap_hglim {HGLIM:g} m)",
                    f"(c) Where the water went (PET {PET:g} mm/day, evap_hglim {HGLIM:g} m)")
        else:
            ttl = T(f"(c) 水の行き先(PET {PET:g} mm/day)", f"(c) Where the water went (PET {PET:g} mm/day)")
        ax[2].set_title(ttl, fontsize=9, loc="left")
    else:
        im2 = store_map(ax[2], case, TEND, T(f"(c) 地中・地表の堆積に留まる量 {TEND} 日目", f"(c) Metal held in the ground / deposits, day {TEND}"))
        cb2 = fig.colorbar(im2, ax=ax[2], shrink=0.85, pad=0.02)
        cb2.set_label(T("物質量 (g/m²)", "metal (g/m²)"))
    bx = [fig.add_subplot(gs[1, k]) for k in range(3)]
    series_q(bx[0], case, prev)
    bx[0].set_title(T("(d) 流量", "(d) Discharge"), fontsize=9, loc="left")
    series_c(bx[1], case, prev)
    bx[1].set_title(T("(e) 濃度(川が流れている時刻だけ)", "(e) Concentration (only while the river flows)"), fontsize=9, loc="left")
    series_budget(bx[2], case, prev)
    bx[2].set_title(T("(f) 物質の行き先(流域全体)", "(f) Where the metal is (whole catchment)"), fontsize=9, loc="left")
    for b in bx:
        b.set_xlabel(T("経過日", "day"))
        b.tick_params(labelsize=8)
    fig.suptitle(title, fontsize=11, x=0.125, y=0.995, ha="left")
    fig.savefig(f"{FIGDIR}/{case}.png", dpi=100, bbox_inches="tight")
    plt.close(fig)


def tank_mass(case, day):
    """ため池の水の中と池底の堆積の物質量 (g)。"""
    tid = data("tank_id")
    sel = tid > 0
    c = bil(case, "C", day)
    h = bil(case, "H", day)
    water = float(np.sum((c * h)[sel])) * DX * DX
    dep = 0.0
    if os.path.exists(f"result_{case}/B{day:04d}.bil"):
        dep = float(np.sum(bil(case, "B", day)[sel])) * DX * DX / 1e4 * 1e3
    return water, dep


def numbers(case):
    w = ledger(case)
    last = -1
    inp = w["in_point_g"][last] + w["in_area_g"][last]
    out = dict(inp=inp, sea=w["out_sea_g"][last], surf=w["mass_surface_g"][last],
               gw=w["mass_gw_g"][last], pool=w["mass_pool_g"][last], togw=w["to_gw_g"][last],
               seep=w["seep_g"][last])
    out["resid"] = inp - out["sea"] - out["surf"] - out["gw"] - out["pool"] \
        - w["mass_dam_g"][last] - w["mass_rs_g"][last] - w["decay_g"][last] - w["out_edge_g"][last] \
        + w["in_edge_g"][last] - w["out_stage_g"][last] + w["in_stage_g"][last]
    out["tank_water"], out["tank_dep"] = tank_mass(case, TEND) if case in TANK_CASES else (0.0, 0.0)
    g3 = flux(case, 3)
    out["g3"] = g3[-1, 7] * 1e3
    p = probe(case, 5)
    t = p[:, 0] / 24
    wet = p[:, 3] > 1e-3
    dry = (t >= 120) & wet
    out["g5_dry"] = float(np.mean(p[dry, 11])) * MG2UG if dry.any() else np.nan
    out["g5_dryfrac"] = float(np.mean(wet[t >= 120]))
    out["g5_max"] = float(np.max(p[:, 11])) * MG2UG
    d5 = flux(case, 5)
    out["q5_dry"] = float(np.mean(d5[d5[:, 0] / 24 >= 120, 2]))
    p1, d1 = probe(case, 1), flux(case, 1)          # 鉱山の 1.5 km 下流 G1 の乾季(120 日目以降)
    dry1 = (p1[:, 0] / 24 >= 120) & (p1[:, 3] > 1e-3)
    out["g1_dry"] = float(np.mean(p1[dry1, 11])) * MG2UG if dry1.any() else np.nan
    out["q1_dry"] = float(np.mean(d1[d1[:, 0] / 24 >= 120, 2]))
    return out


def summary():
    rows = [(c, numbers(c)) for c in CASES]
    kg = 1e-3
    fig, axs = plt.subplots(1, 2, figsize=(14, 4.2), gridspec_kw={"width_ratios": [1.6, 1]})
    ax = axs[0]
    cols = [("sea", "#08519c", T("海へ流出", "exported to the sea")),
            ("surf_out", "#9ecae1", T("地表水の中(ため池の水を除く)", "in surface water (excluding tanks)")),
            ("tank_water", "#3690c0", T("ため池の水の中", "in tank water")),
            ("gw", "#d8b365", T("地中(浸透した分)", "in the ground (infiltrated)")),
            ("dep_out", "#7fbc41", T("地表に堆積(ため池の外)", "deposited (outside tanks)")),
            ("tank_dep", "#276419", T("ため池の底に堆積", "deposited in tanks"))]
    for k, (c, r) in enumerate(rows):
        r["surf_out"] = r["surf"] - r["tank_water"]
        r["dep_out"] = r["pool"] - r["tank_dep"]
        left = 0.0
        for key, color, lab in cols:
            v = r[key] * kg
            ax.barh(k, v, left=left, color=color, label=lab if k == 0 else None)
            left += v
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([LABEL[c] for c, _ in rows], fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel(T(f"{TEND} 日目の物質量 (kg)。投入 606 kg", f"metal on day {TEND} (kg); input 606 kg"))
    ax.legend(fontsize=7.5, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3, frameon=False)
    ax.set_title(T("(a) 物質の行き先", "(a) Where the metal went"), fontsize=10, loc="left", pad=36)
    ax = axs[1]
    y = np.arange(len(rows))
    ax.barh(y - 0.2, [r["g3"] * kg for _, r in rows], height=0.4, color=GCOL["G3"],
            label=T("G3(農地の支川の出口)を通った量", "passed G3 (farm tributary outlet)"))
    ax.barh(y + 0.2, [r["sea"] * kg for _, r in rows], height=0.4, color="#08519c",
            label=T("海へ流出した量", "exported to the sea"))
    ax.set_yticks(y)
    ax.set_yticklabels([])
    ax.invert_yaxis()
    ax.set_xscale("log")
    ax.set_xlim(0.01, 1000)                 # ステップ 6・6b の G3 の 0.01 kg の桁の棒も見えるように
    ax.set_xlabel(T("180 日の累積 (kg)", "cumulative over 180 days (kg)"))
    ax.legend(fontsize=7.5, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=1, frameon=False)
    ax.set_title(T("(b) 農地の支川と海への流出", "(b) Farm tributary and export to the sea"), fontsize=10,
                 loc="left", pad=36)
    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/summary.png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    if EN:
        return
    print("| ケース | 海へ流出 kg (%) | 地表水 kg | 地中 kg | 地表の堆積 kg | うちため池(水・堆積) kg | G3 通過 kg "
          "| G5 乾季の平均濃度 µg/L | G5 最大濃度 µg/L | G5 乾季の平均流量 m³/s | 収支残差 g |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for c, r in rows:
        print(f"| {c} | {r['sea'] * kg:.1f} ({100 * r['sea'] / r['inp']:.1f}) | {r['surf'] * kg:.1f} | {r['gw'] * kg:.1f} "
              f"| {r['pool'] * kg:.1f} | {r['tank_water'] * kg:.1f}・{r['tank_dep'] * kg:.1f} | {r['g3'] * kg:.2f} "
              f"| {r['g5_dry']:.2f} | {r['g5_max']:.1f} | {r['q5_dry']:.3f} | {r['resid']:.1e} |")
    for c, r in rows:
        print(f"{c}: to_gw {r['togw'] * kg:.1f} kg, seep {r['seep'] * kg:.1f} kg, river wet at G5 in dry season "
              f"{100 * r['g5_dryfrac']:.0f} %, G1 in dry season (day >= 120) {r['q1_dry']:.3f} m3/s, "
              f"{r['g1_dry']:.0f} ug/L")


def main():
    mechanism()
    setup()
    step_figure("step1", T("ステップ 1: 地表水と物質(溶存態)", "Step 1: surface water and a dissolved metal"))
    step_figure("step2", T("ステップ 2: + 地下水の流れ(点線 = ステップ 1)", "Step 2: + groundwater flow (dashed = step 1)"))
    step_figure("step3", T("ステップ 3: + 吸着による地下の遅れ R = 100(点線 = ステップ 2)",
                           "Step 3: + sorption delay R = 100 (dashed = step 2)"))
    step_figure("step4", T("ステップ 4: + ため池(点線 = ステップ 3)", "Step 4: + tanks (dashed = step 3)"))
    step_figure("step5", T("ステップ 5: 粒子態+ため池(点線 = ため池なし 5')", "Step 5: particulate + tanks (dashed = no tanks, 5')"))
    step_figure("step6", T(f"ステップ 6: + 蒸発散 PET {PET:g} mm/day(灰色の線 = 蒸発散なしのステップ 4)",
                           f"Step 6: + evapotranspiration, PET {PET:g} mm/day (grey lines = step 4 without it)"))
    step_figure("step6b", T(f"ステップ 6b: + 土の乾き具合による抑制 evap_hglim {HGLIM:g} m(灰色の線 = 抑制なしのステップ 6)",
                            f"Step 6b: + reduction by dry soil, evap_hglim {HGLIM:g} m (grey lines = step 6 without it)"))
    summary()


if __name__ == "__main__":
    main()
