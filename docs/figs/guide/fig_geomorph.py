"""土砂・地形変化(docs/users_guide/geomorph.md)の説明図。

  geomorph_processes.png  斜面〜河道〜水域の断面に各プロセス(f_*)を配置
  geomorph_morfac.png     実行制御(dt_geomorph・morfac)の考え方
データ不要の模式図(matplotlib のみ)。draw(lang) は最初の図の path を返す。
"""
import numpy as np
from _style import *

T = {
    "ja": dict(
        title1="地形変化のプロセス(重ね合わせ。有効化は各 f_* = 1、全体は fn_geomorph)",
        rain="降雨(fn_precip)",
        splash="乾式斜面侵食 f_splash\n乾燥セル(h ≤ dd)のみ\n剥離分は系外へ排出",
        wash="斜面浸食 f_wash\n雨滴+面状侵食 → 浮遊砂\n(f_suspend 必須)",
        creep="斜面クリープ f_creep(線形拡散 creep_d)",
        slide="斜面崩壊 f_slide(Fs < 1 で流動化)\n瞬時流動化 fn_dbinit(崩壊深 D)",
        debris="土石流 f_debris(混合体 h + hs)\n停止分は f_dbstop で z へ固定",
        fluvial="掃流砂 f_fluvial\n(Exner 式)",
        suspend="浮遊砂 f_suspend\nhs の移流、E 巻き上げ・D 沈降",
        wthr="基岩風化 f_wthr\n(裸岩 → 土層 sd)",
        uplift="隆起 f_uplift(uplift0。負で沈降)",
        bedslide="動く底層 f_bedslide(hb。fn_bsinit)\nz・sd の内数、水中でも走る\n→ 水面を持ち上げ地滑り津波",
        sea="湖・海(通常セル+初期水位)",
        lg_soil="土層 sd(可動層。sd = 0 は不侵食)", lg_rock="基岩 z − sd", lg_water="水 h", lg_z="z(計算標高)",
        title2="実行制御: 流れは実時間、地形変化は dt_geomorph ごとに morfac 倍",
        hyd="水理(毎ステップ Δt。実時間)", geo="地形変化の更新",
        dtg="dt_geomorph(0 = 毎ステップ)",
        dz="1 更新の Δz × morfac",
        m1="morfac = 1: イベント計算(f_debris・f_bedslide は 1 が必須)",
        mN="morfac > 1: 平衡地形・年〜千年(f_creep・f_fluvial・f_wthr・f_uplift)。計算時間 tt × morfac = 地形の年数",
        zold="更新前の z", znew="更新後の z",
    ),
    "en": dict(
        title1="Landform-change processes (superposed; each enabled by f_* = 1, module by fn_geomorph)",
        rain="rainfall (fn_precip)",
        splash="dry-slope erosion f_splash\ndry cells (h ≤ dd) only\ndetached material leaves the system",
        wash="hillslope erosion f_wash\nrainsplash + sheet erosion → suspended\n(requires f_suspend)",
        creep="hillslope creep f_creep (linear diffusion creep_d)",
        slide="slope failure f_slide (fluidized when Fs < 1)\ninstant fluidization fn_dbinit (failure depth D)",
        debris="debris flow f_debris (mixture h + hs)\nstopped part fixed into z by f_dbstop",
        fluvial="bedload f_fluvial\n(Exner equation)",
        suspend="suspended sediment f_suspend\nadvection of hs,\nentrainment E, settling D",
        wthr="bedrock weathering f_wthr\n(bare rock → soil sd)",
        uplift="uplift f_uplift (uplift0; negative = subsidence)",
        bedslide="moving bed layer f_bedslide (fn_bsinit)\nhb inside z and sd, runs under water too\n→ lifts the surface: landslide tsunami",
        sea="lake / sea (ordinary cells\n+ initial level)",
        lg_soil="soil sd (mobile layer; sd = 0 is non-erodible)", lg_rock="bedrock z − sd", lg_water="water h", lg_z="z (computational elevation)",
        title2="Run control: the flow runs in real time, landform change is applied every dt_geomorph, scaled by morfac",
        hyd="hydraulics (every step Δt, real time)", geo="landform update",
        dtg="dt_geomorph (0 = every step)",
        dz="Δz of one update × morfac",
        m1="morfac = 1: event runs (f_debris and f_bedslide require 1)",
        mN="morfac > 1: equilibrium landforms, years to millennia (f_creep, f_fluvial, f_wthr, f_uplift). Run time tt × morfac = landform years",
        zold="z before update", znew="z after update",
    ),
}


def _profile():
    xs = [0, 1.0, 1.6, 2.6, 4.2, 5.2, 5.5, 6.1, 6.4, 7.0, 7.4, 7.9, 8.7, 9.6, 10.4]
    zs = [4.0, 4.0, 2.9, 2.3, 1.45, 1.05, 0.8, 0.8, 1.05, 1.45, 1.6, 1.25, 0.45, 0.22, 0.2]
    x = np.linspace(0, 10.4, 521)
    z = np.interp(x, xs, zs)
    th = np.full_like(x, 0.25)
    th[(x > 1.02) & (x < 1.7)] = 0.08          # 崖面は土層が薄い
    return x, z, th


def fig_processes(lang):
    t = T[lang]
    en = lang == "en"
    fig, ax = plt.subplots(figsize=(10.5, 5.9), layout="constrained")
    ax.axis("off"); ax.set_xlim(-0.2, 10.5); ax.set_ylim(-1.05, 5.75)
    x, z, th = _profile()
    yb = -0.7
    ax.fill_between(x, yb, z - th, color=C_ROCK, lw=0, zorder=1)
    ax.fill_between(x, z - th, z, color=C_SOIL, lw=0, zorder=2)
    ax.plot(x, z, color="k", lw=1.0, zorder=5)
    # 水(河道と湖・海)。湖面には底層の突入による持ち上がり
    wl = 1.0
    chan = (x > 5.2) & (x < 6.2)
    ax.fill_between(x, z, wl, where=chan & (z < wl), color=C_WATER_L, lw=0, zorder=3)
    ax.plot(x[chan & (z < wl)], np.full(np.sum(chan & (z < wl)), wl), color=C_WATER, lw=1.2, zorder=4)
    lake = x >= 8.15
    surf = wl + 0.16 * np.exp(-((x - 8.75) / 0.3) ** 2)
    ax.fill_between(x, z, surf, where=lake & (z < surf), color=C_WATER_L, lw=0, zorder=3)
    ax.plot(x[lake], surf[lake], color=C_WATER, lw=1.2, zorder=4)
    label(ax, 9.75, 0.8, t["sea"], color="#1f4f8f", fs=8)
    # 雨
    for xr in np.arange(0.25, 3.75, 0.22):
        zr = np.interp(xr, x, z) + (0.3 if xr < 1.0 else 0.42)
        ax.plot([xr, xr - 0.05], [zr + 0.18, zr], color=C_C, lw=0.9, alpha=0.8, zorder=4)
    label(ax, 0.3, 4.6, t["rain"], color=C_C, fs=8, ha="left")
    # 乾式斜面侵食(崖)・斜面浸食(斜面)・クリープ
    ax.annotate(t["splash"], (1.3, 3.45), (0.0, 4.72), fontsize=8.5, ha="left", va="bottom",
                arrowprops=dict(arrowstyle="-", color=C_P, lw=0.7), zorder=8)
    ax.annotate(t["wash"], (3.0, 2.02), (1.95, 3.78), fontsize=8.5, ha="left", va="bottom",
                arrowprops=dict(arrowstyle="-", color=C_P, lw=0.7), zorder=8)
    ax.annotate(t["creep"], (2.3, 2.45), (4.05, 3.3), fontsize=8.5, ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color=C_P, lw=0.7), zorder=8)
    # 崩壊(すべり面)と土石流
    sx = np.linspace(2.75, 3.95, 40)
    sz = np.interp(sx, x, z) - 0.2 - 0.12 * np.sin(np.pi * (sx - 2.75) / 1.2)
    ax.plot(sx, sz, color=C_X, lw=1.4, ls="--", zorder=6)
    ax.annotate(t["slide"], (3.35, 1.88), (4.1, 2.68), fontsize=8.5, ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color=C_P, lw=0.7), zorder=8)
    arrow(ax, (3.0, 2.2), (5.05, 1.22), color=C_X, lw=2.2)
    label(ax, 4.7 if en else 4.95, 2.12, t["debris"], color=C_X, fs=8.5)
    # 河道: 掃流砂・浮遊砂
    arrow(ax, (5.45, 0.86), (6.0, 0.86), color=C_X, lw=1.6)
    label(ax, 5.72, 0.2, t["fluvial"], color="white", fs=8.5)
    arrow(ax, (5.5, 0.83), (5.5, 0.98), color=C_X, lw=1.2)
    arrow(ax, (5.95, 0.98), (5.95, 0.83), color=C_X, lw=1.2)
    ax.annotate(t["suspend"], (5.75, 1.0), (7.1, 2.15) if en else (6.95, 2.15), fontsize=8.5, ha="center", va="center",
                arrowprops=dict(arrowstyle="-", color=C_P, lw=0.7), zorder=8)
    # 風化・隆起
    arrow(ax, (0.9, 2.95), (0.9, 3.7), color=C_G, lw=1.8)
    label(ax, 0.15, 2.5, t["wthr"], color="white", fs=8.5, ha="left")
    for xu in (1.0, 3.5, 6.0):
        arrow(ax, (xu, -0.62), (xu, -0.2), color=C_G, lw=1.8)
    label(ax, 1.25, -0.42, t["uplift"], color="white", fs=8.5, ha="left")
    # 動く底層(水中へ走る)
    bx = (x > 7.45) & (x < 9.05)
    ax.fill_between(x, z - 0.18, z, where=bx, color=C_X, alpha=0.55, hatch="///", lw=0, zorder=2.5)
    arrow(ax, (7.75, 1.52), (8.95, 0.5), color=C_X, lw=2.2)
    ax.annotate(t["bedslide"], (8.45, 1.1), (8.05, 2.8) if en else (7.95, 2.3), fontsize=8.5, ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color=C_P, lw=0.7), zorder=8)
    # 凡例
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    handles = [Line2D([], [], color="k", lw=1.0, label=t["lg_z"]), Patch(fc=C_SOIL, label=t["lg_soil"]),
               Patch(fc=C_ROCK, label=t["lg_rock"]), Patch(fc=C_WATER_L, ec=C_WATER, label=t["lg_water"])]
    ax.legend(handles=handles, loc="lower right", fontsize=8, frameon=True, framealpha=0.9, edgecolor="none",
              bbox_to_anchor=(1.0, -0.02), ncol=2)
    ax.set_title(t["title1"], loc="left", fontsize=10)
    return save(fig, "geomorph_processes", lang)


def fig_morfac(lang):
    t = T[lang]
    fig, ax = plt.subplots(figsize=(10.5, 3.3), layout="constrained")
    ax.axis("off"); ax.set_xlim(-0.2, 10.5); ax.set_ylim(-0.1, 3.3)
    x0, x1 = 2.5, 7.0
    yH, yG = 2.6, 1.75
    ax.plot([x0, x1], [yH, yH], color=C_C, lw=2.2)
    for xt in np.arange(x0, x1 + 1e-9, 0.1875):
        ax.plot([xt, xt], [yH - 0.07, yH + 0.07], color=C_C, lw=0.9)
    label(ax, x0 - 0.15, yH, t["hyd"], color=C_C, fs=9, ha="right")
    ups = np.arange(x0, x1 + 1e-9, 1.125)
    ax.plot([x0, x1], [yG, yG], color=C_P, lw=1.0, ls=":")
    label(ax, x0 - 0.15, yG, t["geo"], color=C_X, fs=9, ha="right")
    for xu in ups:
        arrow(ax, (xu, yH - 0.1), (xu, yG + 0.08), color=C_X, lw=1.6)
        ax.plot([xu], [yG], "o", color=C_X, ms=6, zorder=7)
    ax.annotate("", (ups[2], yG - 0.25), (ups[1], yG - 0.25), arrowprops=dict(arrowstyle="<->", color=C_X, lw=1.0))
    label(ax, (ups[1] + ups[2]) / 2, yG - 0.47, t["dtg"], color=C_X, fs=8.5)
    # 地形の更新(右): 更新前と更新後の z
    px = np.linspace(7.8, 10.3, 60)
    z0 = 1.9 - 0.45 * (px - 7.8) + 0.25 * np.exp(-((px - 9.0) / 0.35) ** 2)
    z1 = 1.9 - 0.45 * (px - 7.8) + 0.02 * np.exp(-((px - 9.0) / 0.35) ** 2)
    ax.fill_between(px, 0.55, z1, color=C_GROUND_L, lw=0, zorder=1)
    ax.plot(px, z0, color=C_P, lw=1.2, ls="--", zorder=3)
    ax.plot(px, z1, color="k", lw=1.3, zorder=3)
    arrow(ax, (9.0, z0[np.argmin(abs(px - 9.0))] + 0.02), (9.0, z1[np.argmin(abs(px - 9.0))] + 0.03), color=C_X, lw=1.8)
    label(ax, 9.3, 2.15, t["dz"], color=C_X, fs=8.5)
    label(ax, 7.85, z0[0] + 0.12, t["zold"], color=C_P, fs=8, ha="left")
    label(ax, 10.25, z1[-1] - 0.14, t["znew"], color="k", fs=8, ha="right")
    arrow(ax, (ups[-1] + 0.1, yG), (7.7, 1.5), color=C_X, lw=1.2, ls="--")
    label(ax, 0.0, 0.75, t["m1"], color=C_C, fs=9, ha="left")
    label(ax, 0.0, 0.35, t["mN"], color="#8a6b17", fs=9, ha="left")
    ax.set_title(t["title2"], loc="left", fontsize=10)
    return save(fig, "geomorph_morfac", lang)


def draw(lang):
    p = fig_processes(lang)
    fig_morfac(lang)
    return p
