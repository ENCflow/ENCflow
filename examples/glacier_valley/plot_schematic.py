#!/usr/bin/env python3
"""examples/glacier_valley の機構の説明図(計算結果を使わない。式と param_glacial.txt の値と make_terrain.py の地形だけ)。

  python3 plot_schematic.py        # figs/mechanism.png
  python3 plot_schematic.py en     # 英語ラベル版を en/figs/ に描く

  figs/mechanism.png  (a) 谷氷河の縦断の模式図(平衡線・涵養と消耗・雪 → 氷・雪崩・変形と滑動・侵食・末端)
                      (b) この例題の値で描いた法則: 表面の質量収支と標高(と初期地形の標高分布)、SIA の氷の流量、
                          Weertman 滑動、侵食則、侵食の結合長の重み
                      (c) 時間の加速(gl_morfac)と地形時間・計算時間の対応
値は param_glacial.txt(補足の侵食係数は param_glacial_x10.txt)から読み、書いていない値は src の既定値
(list_glacier.f90 の gl_afl・gl_dens・gl_tmelt、m_glacier.f90 の gl_lc の既定 max(500 m, 2Δx)、
list_sysparam.f90 の gg)を使う。式は m_glacier.f90・m_snow.f90・m_meteo.f90 の実装に合わせる。
初期地形の標高分布は make_terrain.py の terrain() で作る(ファイルは書かない)。
"""
import os
import re
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


here = os.path.dirname(os.path.abspath(__file__))
os.chdir(here)
from make_terrain import terrain, DX, SLOPE  # noqa: E402  (初期地形。ファイルは書かない)

FIGDIR = "en/figs" if EN else "figs"
os.makedirs(FIGDIR, exist_ok=True)
plt.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAPGothic", "IPAGothic", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


# ---------------------------------------------------------------- 値(param_glacial.txt と src の既定)
def read_param(fn):
    """param_*.txt の「名前 = 値」(引用符の文字列も)を読む"""
    p = {}
    with open(fn, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"\s*(\w+)\s*=\s*(\"[^\"]*\"|'[^']*'|[^,\s!]+)", line.split("!")[0])
            if m:
                p[m.group(1)] = m.group(2).strip("'\"")
    return p


def seconds(s):
    """時間文字列(m_util の str2sec と同じ単位 d/day・h/hour・m/min・s/sec)を秒に"""
    m = re.match(r"\s*([-+0-9.eE]+)\s*([a-z]*)\s*$", s)
    unit = {"": 1, "s": 1, "sec": 1, "m": 60, "min": 60, "h": 3600, "hour": 3600, "d": 86400, "day": 86400}
    return float(m.group(1)) * unit[m.group(2)]


PAR = read_param("param_glacial.txt")
PAR_X10 = read_param("param_glacial_x10.txt")
with open("param_glacial.txt", encoding="utf-8") as _f:
    P_MMH = float(re.search(r"prval\(1:2,1\)\s*=\s*[-0-9.eE+]+\s*,\s*([-0-9.eE+]+)", _f.read()).group(1))   # 降水 (mm/h)
YR = 365.25 * 86400.0                          # 1 年 (s)(m_glacier の yr_s)
TT, DT_OUT = float(PAR["tt"]), float(PAR["dt_file"])
DTG = seconds(PAR["dt_glacier_c"])             # 氷河の更新間隔(計算時間)
MORFAC = float(PAR["gl_morfac"])
T0, GAM, ZT = float(PAR["temp0"]), float(PAR["temp_lapse"]) / 100.0, float(PAR["temp_zref"])
BETA, ZP = float(PAR["prec_lapse"]) / 1.0e4, float(PAR["prec_zref"])          # %/100 m → 1/m
TSNOW, TRAIN, TMELT_S = (float(PAR[k]) for k in ("snow_t_snow", "snow_t_rain", "snow_t_melt"))
DDFI = float(PAR["gl_ddfi"])                   # mm/℃/day
TFIRN = float(PAR["gl_tfirn_yr"])              # 年(計算時間)
AS = float(PAR.get("gl_as", 1.0e-13))          # m/yr/Pa^3
KG, LEXP = float(PAR.get("gl_kg", 1.0e-4)), float(PAR.get("gl_lexp", 1.0))
KG_X10 = float(PAR_X10["gl_kg"])
TANC = float(PAR.get("gl_ava_tanc", 0.6))
A_GLEN = float(PAR.get("gl_afl", 1.0e-16))     # Pa^-3/yr(list_glacier.f90 の既定)
RHO_I = float(PAR.get("gl_dens", 900.0))       # kg/m3(同)
TMELT_I = float(PAR.get("gl_tmelt", 0.0))      # ℃(同)
G = float(PAR.get("gg", 9.8))                  # m/s2(list_sysparam.f90 の既定)
GL_LC = float(PAR.get("gl_lc", max(500.0, 2.0 * DX)))   # m(m_glacier.f90 の既定)
# 雨と雪の境・融雪・氷面融解の閾値がすべて同じ(季節のない気候で、平衡線より上は雪だけ、下は雨だけ)
# という前提で質量収支を描く(m_snow.f90 の二重閾値の混合域は描かない)
assert TSNOW == TRAIN == TMELT_S == TMELT_I, "smb() assumes equal rain/snow and melt thresholds"
ELA = ZT + (T0 - TSNOW) / GAM                  # 気温が雪の閾値になる高さ(平衡線。2680 m)
RHOG = RHO_I * G
H_STAR = 5.0 * AS / (2.0 * A_GLEN)             # 滑動/変形の流量比が 1 になる氷厚 (m)
UPDATE_YR = DTG * MORFAC / YR                  # 1 回の更新の地形時間(年)
H_EX = 300.0                                   # 例に使う氷厚 (m)(主谷の谷底の勾配と組み合わせる)

C_INK, C_MUTED = "#1f1f1f", "#6b6a66"
C_ROCK, C_ICE, C_ICE_E = "#a19f99", "#d8ebf7", "#5b9bd5"
C_ACC, C_ABL, C_AVA, C_ERO, C_WATER = "#2a78d6", "#d9822b", "#e8692e", "#c0392b", "#1f5f8b"
C_FLOW = "#1f4e8c"
SLOPES = [(SLOPE, "#1f4e8c"), (0.06, "#2a9d8f"), (0.12, "#c0392b")]   # 氷面の勾配の例(0.03 = 主谷の谷底)
BOX = dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85)


def smb(z):
    """表面の質量収支 b (m 水当量/地形時間の年)。z = 氷面(氷がなければ地表)の標高 (m)。
    T <= 閾値: 降水はすべて雪で、氷化の時定数を経て全量が氷になる(定常で b = P(z))。
    T > 閾値: 雨は流れ去り、雪のない氷面が度日係数で融ける(b = −d_i (T − T_melt))。
    gl_morfac 倍は涵養と融解の両方に掛かるので、地形時間で見た b は加速によらない。"""
    t = T0 - GAM * (z - ZT)
    acc = P_MMH * 24.0 * 365.25 / 1000.0 * np.maximum(0.0, 1.0 + BETA * (z - ZP))
    melt = DDFI * 365.25 / 1000.0 * np.maximum(t - TMELT_I, 0.0)
    return np.where(t <= TSNOW, acc, -melt)


def kernel2d():
    """侵食の結合長の 5 点核の反復(m_glacier.f90 の init と smooth_tau。境界とマスクは無視)"""
    nsm = max(1, int(np.floor(4.0 * (GL_LC / DX) ** 2 + 0.5)))
    w = min(0.125, GL_LC ** 2 / (2.0 * nsm * DX ** 2))
    k = np.zeros((2 * nsm + 1, 2 * nsm + 1))
    k[nsm, nsm] = 1.0
    for _ in range(nsm):
        k = (1.0 - 4.0 * w) * k + w * (np.roll(k, 1, 0) + np.roll(k, -1, 0) + np.roll(k, 1, 1) + np.roll(k, -1, 1))
    return k, nsm


def sci(v):
    """1e-04 → 1×10⁻⁴(mathtext。日本語のフォントにない上付きの記号を使わない)"""
    m, e = f"{v:.0e}".split("e")
    return f"${m}\\times10^{{{int(e)}}}$"


def style(ax, grid=True):
    if grid:
        ax.grid(color="#e4e2dc", lw=0.6, which="major")
        ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(labelsize=8.5)


def title(ax, s):
    ax.set_title(s, loc="left", fontsize=10, color=C_INK)


def arrow(ax, x0, y0, x1, y1, color, lw=1.5, ms=10):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, shrinkA=0, shrinkB=0, mutation_scale=ms))


# ---------------------------------------------------------------- (a) 縦断の模式図
ZELA_S = 29.0                                    # 模式図の平衡線の高さ(図の単位)
X0_S, XT_S = 5.0, 72.0                           # 模式図の氷河の上端と末端


def bed(x):
    return 4.0 + 0.2 * (100.0 - x) + 22.0 * np.exp(-x / 8.0)


def ice_thick(x):
    s = np.clip((np.asarray(x, float) - X0_S) / (XT_S - X0_S), 0.0, 1.0)
    return np.where((s > 0) & (s < 1), 13.0 * s ** 0.3 * np.sqrt(np.clip(1.0 - s ** 2.0, 0.0, 1.0)), 0.0)


def surf(x):
    return bed(x) + ice_thick(x)


def panel_profile(ax):
    x = np.linspace(0.0, 100.0, 1001)
    zb, hi = bed(x), ice_thick(x)
    zs = zb + hi
    ice = hi > 0
    ax.fill_between(x, -16.0, zb, color=C_ROCK, zorder=1)
    ax.fill_between(x, zb, zs, where=ice, color=C_ICE, zorder=2)
    ax.plot(x[ice], zs[ice], color=C_ICE_E, lw=1.4, zorder=3)
    ax.plot(x, zb, color="0.25", lw=1.0, zorder=3)
    # 地表の水(氷の下も地盤の上を流れる)
    ax.plot(x[x > 3], zb[x > 3] + 0.3, color=C_WATER, lw=1.0, zorder=4)
    arrow(ax, 97.0, bed(97.0) + 0.3, 100.0, bed(100.0) + 0.3, C_WATER, lw=1.6)
    # 侵食: 滑る氷の下の岩盤(赤の帯と下向きの矢印)
    m = hi > 0.5
    ax.fill_between(x[m], zb[m] - 1.3, zb[m], color=C_ERO, alpha=0.4, lw=0, zorder=2)
    for xa in (22.0, 38.0, 54.0):
        arrow(ax, xa, bed(xa) - 0.3, xa, bed(xa) - 3.2, C_ERO, lw=1.5, ms=8)
    ax.text(7.0, 9.0, T("侵食: 滑る氷の下の岩盤を削る($\\dot e = K_g u_b$。b4)\n削った岩屑は系外へ運び去る(モレーンは作らない)",
                        "erosion: the bed under sliding ice is cut ($\\dot e = K_g u_b$; b4);\nthe debris is carried out of the domain (no moraines)"),
            fontsize=8.6, color=C_ERO, ha="left", va="top", zorder=6, bbox=BOX)
    # 平衡線
    ax.axhline(ZELA_S, color=C_INK, lw=0.9, ls=(0, (5, 3)), zorder=4)
    ax.text(99.5, ZELA_S + 0.5, T(f"平衡線 {ELA:.0f} m(気温 0 ℃)", f"equilibrium line {ELA:.0f} m (0 °C)"),
            fontsize=9, ha="right", va="bottom", color=C_INK, zorder=6)
    # 涵養域: 雪が降り、氷になる
    for xa in (11.0, 17.0, 23.0, 29.0):
        za = surf(xa)
        arrow(ax, xa, za + 4.6, xa, za + 0.5, C_ACC, lw=1.4, ms=8)
        ax.plot(xa, za + 5.4, marker=(6, 2, 0), color=C_ACC, ms=7, mew=1.0, zorder=5)
    ax.text(32.0, 41.3, T(f"涵養域: 降水はすべて雪(気温 ≤ 0 ℃)。雪は時定数 gl_tfirn_yr\n(地形時間 {TFIRN * MORFAC:.0f} 年)で氷になる(b1)",
                          f"accumulation area: all precipitation is snow (≤ 0 °C); the snow turns into ice\nwith time constant gl_tfirn_yr ({TFIRN * MORFAC:.0f} years of landform time) (b1)"),
            fontsize=8.6, color=C_ACC, va="center", ha="left", zorder=6)
    # 消耗域: 雪のない氷面の融解
    for xa in (51.0, 57.0, 63.0):
        za = surf(xa)
        arrow(ax, xa, za + 4.2, xa, za + 0.5, C_ABL, lw=1.4, ms=8)
    ax.text(50.0, 33.6, T(f"消耗域: 雪のない氷面が融ける(度日係数 gl_ddfi = {DDFI:g} mm/℃/日。気温は氷面の標高で)。\n"
                          "融解水は加速せずに地表の水へ(b1)",
                          f"ablation area: the snow-free ice surface melts\n(degree-day factor gl_ddfi = {DDFI:g} mm/°C/day; "
                          "temperature at the ice surface);\nthe meltwater joins the surface water without acceleration (b1)"),
            fontsize=8.6, color=C_ABL, va="center", ha="left", zorder=6)
    # 雨(平衡線より下)
    for xa in (86.0, 93.0):
        for dx_ in (0.0, 1.8):
            ax.plot([xa + dx_ + 0.8, xa + dx_], [bed(xa) + 8.5, bed(xa) + 6.3], color=C_WATER, lw=1.0, zorder=5)
    ax.text(89.5, bed(89.5) + 9.4, T("雨", "rain"), fontsize=8.6, color=C_WATER, ha="center", va="bottom", zorder=6)
    # 雪崩: 急な斜面の雪が氷河の頭へ
    xs = np.linspace(0.8, 5.0, 40)
    ax.plot(xs, bed(xs) + 1.8, color=C_AVA, lw=1.8, zorder=5)
    arrow(ax, xs[-1], bed(xs[-1]) + 1.8, 8.6, surf(8.6) + 0.9, C_AVA, lw=1.8)
    ax.text(4.0, 48.5, T(f"雪崩(f_glava): 勾配 tanθ > {TANC:g} の斜面の雪を、1 回の更新で割合 min(1, (tanθ − {TANC:g})/{TANC:g}) だけ"
                         "最も急な下りの向きの隣へ移す",
                         f"avalanching (f_glava): on slopes tanθ > {TANC:g}, a share min(1, (tanθ − {TANC:g})/{TANC:g}) of the snow moves"
                         " to the steepest-descent neighbours at each update"),
            fontsize=8.6, color=C_AVA, va="center", ha="left", zorder=6)
    # 氷の流れ: 底面滑動 + 変形(速度の縦分布。n = 3 の SIA の形。滑動と変形の比はこの例題の値で厚さ H_EX)
    xv = 44.0
    zb_v, h_v = bed(xv), float(ice_thick(xv))
    ub = AS                                   # 滑動 u_b = A_s τ³(τ³ は共通なので係数で比をとる)
    us_def = A_GLEN / 2.0 * H_EX              # 変形の表面速度 (A/2) τ³ H
    scale = 6.0 / (ub + us_def)
    for zeta in (0.08, 0.37, 0.66, 0.92):
        u = ub + us_def * (1.0 - (1.0 - zeta) ** 4)
        arrow(ax, xv, zb_v + zeta * h_v, xv + u * scale, zb_v + zeta * h_v, C_FLOW, lw=1.5, ms=8)
    zeta = np.linspace(0, 1, 50)
    ax.plot(xv + (ub + us_def * (1 - (1 - zeta) ** 4)) * scale, zb_v + zeta * h_v, color=C_FLOW, lw=0.8, ls=":", zorder=5)
    ax.plot([xv, xv], [zb_v, zb_v + h_v], color=C_FLOW, lw=0.9, zorder=5)
    share = H_STAR / (H_STAR + H_EX)
    ax.annotate(T(f"氷の流れ = 底面滑動(Weertman。b3)+ 内部の変形(SIA。b2)。矢印は厚さ {H_EX:.0f} m の\n"
                  f"速度の縦分布の例で、この例題の値では流量の {share:.0%} が滑動",
                  f"ice flow = basal sliding (Weertman; b3) + internal deformation (SIA; b2); the arrows show\n"
                  f"the velocity profile for {H_EX:.0f} m of ice: with this example's values {share:.0%} of the flux is sliding"),
                xy=(xv + 2.5, zb_v + 0.15 * h_v), xytext=(48.0, 7.5), fontsize=8.6, color=C_FLOW, ha="left", va="top", zorder=6,
                bbox=BOX, arrowprops=dict(arrowstyle="-", color=C_FLOW, lw=0.8))
    # 末端
    ax.annotate(T("末端: 流れてくる氷 = 融ける量", "terminus: ice inflow = melt"), xy=(XT_S - 0.2, bed(XT_S) + 0.4),
                xytext=(XT_S + 2.5, bed(XT_S) + 4.6), fontsize=8.6, color=C_INK, zorder=6,
                arrowprops=dict(arrowstyle="-", color=C_MUTED, lw=0.8))
    ax.text(99.5, -2.8, T("雨と融解水は地表の水(浅水流)として地盤の上を流れ(氷の下も)、東の端から出る",
                           "rain and meltwater flow as surface water (shallow-water flow) on the bed (under the ice too) and leave at the east edge"),
            fontsize=8.6, color=C_WATER, ha="right", va="center", zorder=6, bbox=BOX)
    ax.set_xlim(0, 100)
    ax.set_ylim(-6, 51)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    title(ax, T("(a) 谷氷河の縦断(模式。形と縮尺は概念的)", "(a) Long section of the valley glacier (schematic; shapes and scale are conceptual)"))


# ---------------------------------------------------------------- (b) 法則
def panel_smb(ax, axh):
    z = np.linspace(1500.0, 4400.0, 2901)
    b = smb(z)
    lo, hi_ = z < ELA, z >= ELA
    ax.axvline(0.0, color="0.5", lw=0.8)
    ax.axhline(ELA, color=C_INK, lw=0.9, ls=(0, (5, 3)))
    ax.plot(b[lo], z[lo], color=C_ABL, lw=2.0)
    ax.plot(b[hi_], z[hi_], color=C_ACC, lw=2.0)
    ax.set_xlim(-17.0, 4.0)
    ax.set_ylim(1500, 4400)
    ax.set_xlabel(T("表面の質量収支 b(m 水当量/年。地形時間)", "surface mass balance b (m water equivalent per year of landform time)"), fontsize=8.8)
    ax.set_ylabel(T("氷面(氷がなければ地表)の標高 z (m)", "elevation z of the ice surface (ground if no ice) (m)"), fontsize=8.8)
    p0 = P_MMH * 24.0 * 365.25
    ax.text(-16.5, 4330.0, T(f"気温 ≤ 0 ℃(z ≥ {ELA:.0f} m): 降水はすべて雪 → 氷\n"
                             f"b = P(z) = {p0:.0f} mm/年 × (1 + {BETA * 1e4:g} % × (z − {ZP:.0f} m)/100 m)",
                             f"≤ 0 °C (z ≥ {ELA:.0f} m): all precipitation is snow → ice\n"
                             f"b = P(z) = {p0:.0f} mm/yr × (1 + {BETA * 1e4:g} % × (z − {ZP:.0f} m)/100 m)"),
            fontsize=8.3, color=C_ACC, va="top")
    grad = DDFI * 365.25 * GAM * 100.0 / 1000.0
    ax.text(-16.5, 3880.0, T(f"気温 > 0 ℃(z < {ELA:.0f} m): 雨は流れ去り、雪のない氷面が融ける\n"
                             f"b = −{DDFI:g} mm/℃/日 × T、T = {T0:g} ℃ − {GAM * 100:g} ℃/100 m × z\n"
                             f"(100 m 下がるごとに b は {grad:.2f} m/年 小さくなる)",
                             f"> 0 °C (z < {ELA:.0f} m): rain runs off; the snow-free ice surface melts\n"
                             f"b = −{DDFI:g} mm/°C/day × T, T = {T0:g} °C − {GAM * 100:g} °C/100 m × z\n"
                             f"(b falls by {grad:.2f} m/yr for every 100 m lower)"),
            fontsize=8.3, color=C_ABL, va="top")
    ax.text(-0.3, ELA + 40.0, T(f"平衡線 {ELA:.0f} m", f"equilibrium line {ELA:.0f} m"), fontsize=8.3, ha="right", va="bottom")
    style(ax)
    title(ax, T("(b1) 表面の質量収支と標高(この例題の値)", "(b1) Surface mass balance against elevation (this example's values)"))
    # 初期地形の標高分布(50 m ごとの面積)
    z0 = terrain()
    edges = np.arange(1500.0, 4450.0, 50.0)
    area, _ = np.histogram(z0, bins=edges)
    area = area * DX * DX / 1.0e6
    axh.barh(edges[:-1], area, height=50.0, align="edge", color=np.where(edges[:-1] >= ELA, C_ACC, "#b9b6ae"), alpha=0.75)
    axh.axhline(ELA, color=C_INK, lw=0.9, ls=(0, (5, 3)))
    above = (z0 >= ELA).sum() * DX * DX / 1.0e6
    total = z0.size * DX * DX / 1.0e6
    axh.text(0.97, 0.985, T(f"初期地形の面積\n(50 m ごと)\n平衡線より上\n{above:.0f} / {total:.0f} km²",
                            f"initial terrain\narea (per 50 m)\nabove the line:\n{above:.0f} of {total:.0f} km²"),
             transform=axh.transAxes, fontsize=7.8, ha="right", va="top", color=C_INK)
    axh.set_xlabel("km²", fontsize=8.5)
    axh.set_ylim(1500, 4400)
    axh.tick_params(labelleft=False)
    style(axh)


def panel_sia(ax):
    h = np.logspace(1.0, np.log10(500.0), 200)
    for s, c in SLOPES:
        tau = RHOG * h * s
        qd = 2.0 * A_GLEN / 5.0 * tau ** 3 * h ** 2       # 変形 (2A/5) τ³ H² = (2A/5)(ρg|∇s|)³ H⁵
        qs = AS * tau ** 3 * h                            # 滑動 u_b H = A_s (ρg|∇s|)³ H⁴
        ax.plot(h, qd + qs, color=c, lw=2.0, label=T(f"|∇s| = {s:g}(計)", f"|∇s| = {s:g} (total)"))
        ax.plot(h, qd, color=c, lw=1.0, ls="--")
    ax.plot([], [], color="0.4", lw=1.0, ls="--", label=T("うち変形の分", "of which deformation"))
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(10, 500)
    ax.set_ylim(1.0e-1, 1.0e7)
    ax.set_xlabel(T("氷厚 $H$ (m)", "ice thickness $H$ (m)"), fontsize=8.8)
    ax.set_ylabel(T("単位幅の氷の流量 $q$ (m$^2$/年)", "ice flux per unit width $q$ (m$^2$/yr)"), fontsize=8.8)
    lines = [r"$q = D\,|\nabla s| = \frac{2A}{5}(\rho_i g|\nabla s|)^3 H^5 + A_s(\rho_i g|\nabla s|)^3 H^4$",
             T("$A$ = %s Pa$^{-3}$ 年$^{-1}$(Glen $n$ = 3。既定)、$A_s$ = %s m 年$^{-1}$ Pa$^{-3}$、$\\rho_i$ = %.0f kg/m$^3$"
               % (sci(A_GLEN), sci(AS), RHO_I),
               "$A$ = %s Pa$^{-3}$ yr$^{-1}$ (Glen $n$ = 3; default), $A_s$ = %s m yr$^{-1}$ Pa$^{-3}$, $\\rho_i$ = %.0f kg/m$^3$"
               % (sci(A_GLEN), sci(AS), RHO_I)),
             T("滑動/変形 = $5A_s/(2AH)$ = %.0f m / $H$(この例題ではほぼ滑動で流れる)" % H_STAR,
               "sliding/deformation = $5A_s/(2AH)$ = %.0f m / $H$ (mostly sliding here)" % H_STAR)]
    ax.text(0.02, 0.98, "\n".join(lines), transform=ax.transAxes, fontsize=8.2, va="top", ha="left", linespacing=1.5)
    ax.legend(fontsize=7.8, loc="lower right", framealpha=0.9)
    style(ax)
    title(ax, T("(b2) SIA の氷の流量(変形 + 滑動)と氷厚・氷面の勾配", "(b2) SIA ice flux (deformation + sliding) against thickness and surface slope"))


def panel_slide(ax):
    tau = np.linspace(0.0, 160.0, 321)                    # kPa
    ub = AS * (tau * 1.0e3) ** 3
    ax.axvspan(50, 150, color="#eef3f8", zorder=0)
    ax.text(146, 12, T("典型の底面せん断応力\n50〜150 kPa", "typical basal shear\nstress 50–150 kPa"),
            fontsize=7.8, ha="right", va="bottom", color=C_MUTED)
    ax.plot(tau, ub, color=C_FLOW, lw=2.0)
    ax.plot(100, AS * 1.0e15, "o", color=C_FLOW, ms=5)
    ax.annotate(T("100 kPa で 100 m/年\n(既定の $A_s$ の根拠)", "100 m/yr at 100 kPa\n(basis of the default $A_s$)"),
                xy=(100, AS * 1.0e15), xytext=(112, 66), fontsize=7.8, color=C_FLOW,
                arrowprops=dict(arrowstyle="-", color=C_FLOW, lw=0.7))
    t_ex = RHOG * H_EX * SLOPE
    u_ex = AS * t_ex ** 3
    ax.plot([t_ex / 1e3, t_ex / 1e3, 0], [0, u_ex, u_ex], color=C_ERO, lw=0.9, ls=":")
    ax.plot(t_ex / 1e3, u_ex, "s", color=C_ERO, ms=5)
    ax.text(t_ex / 1e3 - 2, u_ex + 12, T("例: $H$ = %.0f m、$|\\nabla s|$ = %g\n→ $\\tau_b$ = %.0f kPa、$u_b$ = %.0f m/年"
                                         % (H_EX, SLOPE, t_ex / 1e3, u_ex),
                                         "e.g. $H$ = %.0f m, $|\\nabla s|$ = %g\n→ $\\tau_b$ = %.0f kPa, $u_b$ = %.0f m/yr"
                                         % (H_EX, SLOPE, t_ex / 1e3, u_ex)),
            fontsize=7.8, color=C_ERO, ha="right", va="bottom")
    ax.text(0.03, 0.97, T("$u_b = A_s\\,\\tau_b^3$、$\\tau_b = \\rho_i g H|\\nabla s|$\n$A_s$ = %s m 年$^{-1}$ Pa$^{-3}$(既定)" % sci(AS),
                          "$u_b = A_s\\,\\tau_b^3$, $\\tau_b = \\rho_i g H|\\nabla s|$\n$A_s$ = %s m yr$^{-1}$ Pa$^{-3}$ (default)" % sci(AS)),
            transform=ax.transAxes, fontsize=8.2, va="top", linespacing=1.5)
    ax.set_xlim(0, 160)
    ax.set_ylim(0, 400)
    ax.set_xlabel(T("底面せん断応力 $\\tau_b$ (kPa)", "basal shear stress $\\tau_b$ (kPa)"), fontsize=8.8)
    ax.set_ylabel(T("滑動速度 $u_b$ (m/年)", "sliding speed $u_b$ (m/yr)"), fontsize=8.8)
    style(ax)
    title(ax, T("(b3) Weertman 滑動", "(b3) Weertman sliding"))


def panel_erosion(ax):
    ub = np.logspace(-1, 3, 200)
    ax.plot(ub, KG * ub ** LEXP * 1e3, color=C_ERO, lw=2.0)
    ax.plot(ub, KG_X10 * ub ** LEXP * 1e3, color=C_ERO, lw=1.2, ls="--")
    ax.text(8.0, 0.4, T(f"本番 $K_g$ = {sci(KG)}(既定)", f"main run $K_g$ = {sci(KG)} (default)"), fontsize=8.0, color=C_ERO,
            ha="left", va="center")
    ax.text(0.13, 6.0, T(f"補足 $K_g$ = {sci(KG_X10)}", f"supplement $K_g$ = {sci(KG_X10)}"), fontsize=8.0, color=C_ERO,
            ha="left", va="center")
    # 実測の侵食速度の範囲(Hallet ら 1996。README の「実際の氷河の谷で起きていること」)。全幅の薄い帯で描き、
    # ラベルは線と重ならない側に置く
    bands = [(0.01, T("極地・薄い台地氷河 0.01", "polar, thin plateau 0.01"), "right"),
             (0.1, T("ノルウェーの谷氷河 0.1", "Norwegian valley 0.1"), "right"),
             (1.0, T("アルプスの小さな氷河 1", "small Alpine 1"), "right"),
             ((10.0, 100.0), T("南東アラスカ 10〜100", "SE Alaska 10–100"), "left")]
    for v, lab, side in bands:
        if isinstance(v, tuple):
            ax.axhspan(v[0], v[1], color="#8c8a85", alpha=0.13, lw=0)
            yl = np.sqrt(v[0] * v[1])
        else:
            ax.axhline(v, color="#8c8a85", lw=4.0, alpha=0.3, solid_capstyle="butt")
            yl = v * 1.45
        ax.text(900 if side == "right" else 0.12, yl, lab, fontsize=7.4, va="center", ha=side, color=C_MUTED)
    ax.text(900, 0.0068, T("灰色 = 実測(Hallet ら 1996。mm/年)", "grey = measured (Hallet et al. 1996; mm/yr)"),
            fontsize=7.4, va="center", ha="right", color=C_MUTED)
    u_ex = AS * (RHOG * H_EX * SLOPE) ** 3
    ax.plot(u_ex, KG * u_ex * 1e3, "s", color=C_ERO, ms=5)
    ax.text(70.0, 3.0, T(f"b3 の例: {KG * u_ex * 1e3:.0f} mm/年", f"e.g. (b3): {KG * u_ex * 1e3:.0f} mm/yr"), fontsize=7.8,
            color=C_ERO, ha="left", va="center")
    ax.text(0.03, 0.97, T("$\\dot e = K_g\\,u_b^{\\,l}$($l$ = %g、$u_b$ は m/年)" % LEXP,
                          "$\\dot e = K_g\\,u_b^{\\,l}$ ($l$ = %g, $u_b$ in m/yr)" % LEXP),
            transform=ax.transAxes, fontsize=8.2, ha="left", va="top")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(0.1, 1000)
    ax.set_ylim(0.005, 400)
    ax.set_xlabel(T("滑動速度 $u_b$ (m/年)", "sliding speed $u_b$ (m/yr)"), fontsize=8.8)
    ax.set_ylabel(T("侵食速度 $\\dot e$ (mm/年)", "erosion rate $\\dot e$ (mm/yr)"), fontsize=8.8)
    style(ax)
    title(ax, T("(b4) 侵食則(滑動速度に比例)", "(b4) Erosion law (proportional to sliding speed)"))


def panel_kernel(ax):
    k, nsm = kernel2d()
    n = 9                                                  # ±9 セルを描く
    c = k.shape[0] // 2
    sub = k[c - n:c + n + 1, c - n:c + n + 1] / k[c, c]
    ext = [-(n + 0.5) * DX / 1e3, (n + 0.5) * DX / 1e3, -(n + 0.5) * DX / 1e3, (n + 0.5) * DX / 1e3]
    im = ax.imshow(sub, extent=ext, cmap="Reds", vmin=0, vmax=1, interpolation="nearest", origin="lower")
    for r, lab in ((GL_LC, "σ"), (2 * GL_LC, "2σ")):
        ax.add_patch(Circle((0, 0), r / 1e3, fill=False, ec=C_INK, lw=0.9, ls="--"))
        ax.text(r / 1e3 * 0.72, r / 1e3 * 0.72, lab, fontsize=8, color=C_INK, ha="left", va="bottom")
    ax.add_patch(Rectangle((-0.5 * DX / 1e3, -0.5 * DX / 1e3), DX / 1e3, DX / 1e3, fill=False, ec=C_INK, lw=0.8))
    ax.set_xticks(np.arange(-1.5, 1.6, 0.5))
    ax.set_yticks(np.arange(-1.5, 1.6, 0.5))
    ax.set_xlabel(T(f"km(1 マス = Δx = {DX:.0f} m)", f"km (one square = Δx = {DX:.0f} m)"), fontsize=8.8)
    cb = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
    cb.set_label(T("重み(中心のセル = 1)", "weight (centre cell = 1)"), fontsize=8)
    cb.ax.tick_params(labelsize=7.5)
    ax.tick_params(labelsize=8)
    ax.set_title(T(f"(b5) 侵食の結合長 gl_lc = {GL_LC:.0f} m の重み\n(5 点核 {nsm} 回 = 標準偏差 {GL_LC:.0f} m)",
                   f"(b5) Weights of the erosion coupling length\ngl_lc = {GL_LC:.0f} m ({nsm} passes of a 5-point kernel)"),
                 loc="left", fontsize=10, color=C_INK)


# ---------------------------------------------------------------- (c) 時間の加速
def panel_time(ax_bar, ax_txt):
    t_end = TT * MORFAC / YR
    ax_bar.set_xlim(0, 6000)
    ax_bar.set_ylim(0, 1)
    ax_bar.add_patch(Rectangle((0, 0.15), t_end, 0.7, fc="#dbe8f4", ec=C_FLOW, lw=0.8))
    ax_bar.set_yticks([])
    for s in ("left", "right"):
        ax_bar.spines[s].set_visible(False)
    ax_bar.set_xticks(np.arange(0, 6001, 1000))
    ax_bar.tick_params(labelsize=8.5)
    ax_bar.set_xlabel(T("地形時間(年)", "landform time (years)"), fontsize=8.8, labelpad=2)
    sec = ax_bar.secondary_xaxis("top", functions=(lambda yr: yr * YR / MORFAC / 86400.0, lambda d: d * 86400.0 * MORFAC / YR))
    sec.set_xticks([0, 2, 4, 6, 8, 10])
    sec.tick_params(labelsize=8.5)
    sec.set_xlabel(T("計算時間(日)", "computational time (days)"), fontsize=8.8, labelpad=3)
    ax_bar.text(t_end / 2, 0.5, T(f"本番: 地形時間 {t_end:.0f} 年 = 計算時間 {TT:,.0f} s({TT / 86400:.1f} 日)= {TT / DTG:,.0f} 回の更新",
                                  f"main run: {t_end:.0f} years of landform time = {TT:,.0f} s of computational time ({TT / 86400:.1f} days) = {TT / DTG:,.0f} updates"),
                ha="center", va="center", fontsize=8.6, color=C_INK)
    ax_bar.set_title(T("(c) 時間の加速: 地形時間 = 計算時間 × gl_morfac", "(c) Time acceleration: landform time = computational time × gl_morfac"),
                     loc="left", fontsize=10, color=C_INK, pad=36)
    acc1 = float(smb(np.array([ELA]))[0]) * UPDATE_YR * 1e3
    txt = T(f"・氷河は毎ステップ更新(dt_glacier_c = \"{PAR['dt_glacier_c']}\" = dt)。1 回の更新 = {DTG:g} s × gl_morfac {MORFAC / 1e5:g}×10⁵ = "
            f"{DTG * MORFAC / 1e6:.1f}×10⁶ s = 地形時間 {UPDATE_YR:.2f} 年。出力は計算時間 {DT_OUT:,.0f} s(地形時間 {DT_OUT * MORFAC / YR:.0f} 年)ごと\n"
            "・地形時間で進むもの: 氷化による氷の増加、融解による氷の減少、SIA の流動・滑動、侵食。雨と融解水の流れ(浅水流)は計算時間のまま"
            "(融解水は実時間のレートで出て、氷の減少だけが gl_morfac 倍)\n"
            f"・氷化の時定数 gl_tfirn_yr = {TFIRN:g} 年は計算時間({TFIRN * YR / 3600:.1f} 時間)で、地形時間では {TFIRN * MORFAC:.0f} 年。"
            f"1 回の更新で動く量の例: 平衡線での涵養 {acc1:.0f} mm 水当量、侵食 5 mm/年の所で {5 * UPDATE_YR:.2f} mm",
            f"• The glacier is updated every step (dt_glacier_c = \"{PAR['dt_glacier_c']}\" = dt). One update = {DTG:g} s × gl_morfac {MORFAC / 1e5:g}×10⁵ = "
            f"{DTG * MORFAC / 1e6:.1f}×10⁶ s = {UPDATE_YR:.2f} years of landform time. Output every {DT_OUT:,.0f} s of computational time"
            f" ({DT_OUT * MORFAC / YR:.0f} years)\n"
            "• On landform time: ice gain by conversion, ice loss by melt, SIA flow and sliding, erosion. Rain and meltwater flow (shallow water)"
            " stays on computational time\n   (the meltwater enters at the real-time rate; only the ice loss is multiplied by gl_morfac)\n"
            f"• The conversion time constant gl_tfirn_yr = {TFIRN:g} years is computational time ({TFIRN * YR / 3600:.1f} hours), {TFIRN * MORFAC:.0f} years"
            f" of landform time. Per update, e.g.: {acc1:.0f} mm w.e. of accumulation at the\n   equilibrium line, {5 * UPDATE_YR:.2f} mm of erosion"
            " where the rate is 5 mm/yr")
    ax_txt.axis("off")
    ax_txt.set_xlim(0, 1)
    ax_txt.set_ylim(0, 1)
    ax_txt.text(0.0, 0.66, txt, fontsize=8.6, va="top", ha="left", color=C_INK, linespacing=1.75)   # 上は時間の帯の軸ラベルの場所


def mechanism():
    fig = plt.figure(figsize=(15.5, 16.2))
    gs = fig.add_gridspec(4, 1, height_ratios=[1.35, 1.0, 1.0, 0.72], hspace=0.27,
                          left=0.06, right=0.965, top=0.975, bottom=0.012)
    panel_profile(fig.add_subplot(gs[0]))
    g1 = gs[1].subgridspec(1, 4, width_ratios=[1.0, 0.2, 0.17, 1.25], wspace=0.05)
    ax1 = fig.add_subplot(g1[0])
    axh = fig.add_subplot(g1[1], sharey=ax1)
    panel_smb(ax1, axh)
    panel_sia(fig.add_subplot(g1[3]))
    g2 = gs[2].subgridspec(1, 3, width_ratios=[1.0, 1.0, 0.85], wspace=0.3)
    panel_slide(fig.add_subplot(g2[0]))
    panel_erosion(fig.add_subplot(g2[1]))
    panel_kernel(fig.add_subplot(g2[2]))
    g3 = gs[3].subgridspec(3, 1, height_ratios=[0.42, 0.3, 1.0], hspace=0.0)
    ax_bar = fig.add_subplot(g3[1])
    panel_time(ax_bar, fig.add_subplot(g3[2]))
    fig.savefig(f"{FIGDIR}/mechanism.png", dpi=100)
    plt.close(fig)


if __name__ == "__main__":
    mechanism()
    print(f"{FIGDIR}/mechanism.png written")
