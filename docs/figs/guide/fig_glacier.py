"""氷河(docs/users_guide/glacier.md)の説明図: 氷河の縦断面に質量収支・流動・滑動・侵食・雪崩再配分を配置。

  glacier_profile.png
データ不要の模式図(matplotlib のみ)。
"""
import numpy as np
from _style import *

T = {
    "ja": dict(
        title="氷河の縦断面とプロセス(fn_glacier。fn_meteo の気温と fn_snow の降雪が必須。状態は氷厚 hi → 出力 Hi)",
        ava="雪崩再配分 f_glava\n氷面勾配 > gl_ava_tanc の雪を\n最急下方の隣接セルへ",
        acc="涵養: 越年した雪だけが氷になる\n(時定数 gl_tfirn_yr、氷密度 gl_dens)\n季節の雪は融けて流出",
        ela="平衡線は指定しない(気温と降水から自動)\n気温は氷面標高 z + hi で評価(f_temp_lapse と組)",
        abl="消耗: 氷面の度日融解 gl_ddfi(T > gl_tmelt)\n雪に覆われていないときだけ",
        melt="融解水 → 地表水\n(実時間。gl_morfac で加速しない)",
        flow="氷体流動 f_glflow(SIA。Glen 則 gl_afl)",
        slide="底面滑動 f_glslide(Weertman 型 gl_as。f_glflow 必須)",
        ero="氷河侵食 f_glero(f_glslide 必須): ė = Kg·usˡ(gl_kg, gl_lexp)\n滑動する氷の下だけ z を下げる(土層 sd があれば先に減る)\n岩屑は系外へ(堆積モレーンなし)",
        init="初期: 既定は氷なし(hi = 0)から降雪で育てる(スピンアップ)。実在氷河は fn_glacier_hi0 で氷厚を与える",
        time="時間: 氷化・流動・侵食は dt_glacier_c ごとに更新、1 回の更新 = gl_morfac 回分(fn_geomorph 併用時は morfac と同値に)",
        snow="積雪(SWE)", ice="氷 hi", rock="地盤 z",
        acc_z="涵養域", abl_z="消耗域",
    ),
    "en": dict(
        title="Glacier long profile and processes (fn_glacier; needs fn_meteo temperature and fn_snow snowfall; state = ice thickness hi → output Hi)",
        ava="avalanche redistribution f_glava\nsnow on surface slopes > gl_ava_tanc\nmoves to the steepest downhill neighbour",
        acc="accumulation: only perennial snow turns to ice\n(time constant gl_tfirn_yr, ice density gl_dens)\nseasonal snow melts and runs off",
        ela="equilibrium line not prescribed\n(emerges from temperature and precipitation;\ntemperature evaluated at z + hi with f_temp_lapse)",
        abl="ablation: degree-day melt of the ice surface\ngl_ddfi (T > gl_tmelt), only where no snow covers it",
        melt="meltwater → surface water\n(real time; not scaled by gl_morfac)",
        flow="ice flow f_glflow (SIA; Glen's law gl_afl)",
        slide="basal sliding f_glslide (Weertman type gl_as; needs f_glflow)",
        ero="glacial erosion f_glero (needs f_glslide): ė = Kg·usˡ (gl_kg, gl_lexp)\nlowers z only under sliding ice (soil sd is consumed first)\nthe debris leaves the system (no moraine deposition)",
        init="initial state: default is no ice (hi = 0), grown from snowfall (spin-up); real glaciers take fn_glacier_hi0",
        time="time: firnification, flow and erosion update every dt_glacier_c; one update = gl_morfac repetitions (equal to morfac when fn_geomorph is on)",
        snow="snow (SWE)", ice="ice hi", rock="bed z",
        acc_z="accumulation zone", abl_z="ablation zone",
    ),
}


def draw(lang):
    t = T[lang]
    en = lang == "en"
    fig, ax = plt.subplots(figsize=(10.5, 5.8), layout="constrained")
    ax.axis("off"); ax.set_xlim(-0.1, 10.5); ax.set_ylim(-0.95, 5.75)
    xs = [0, 0.6, 1.3, 2.2, 3.4, 5.0, 6.6, 8.0, 9.2, 10.5]
    zs = [4.6, 4.4, 3.0, 2.1, 1.75, 1.45, 1.1, 0.75, 0.5, 0.4]
    x = np.linspace(0, 10.5, 526)
    zb = np.interp(x, xs, zs)
    ax.fill_between(x, -0.25, zb, color=C_ROCK, lw=0, zorder=1)
    ax.plot(x, zb, color="k", lw=1.0, zorder=5)
    # 氷体
    xa, xe = 1.2, 8.0
    tt = np.clip((x - xa) / (xe - xa), 0, 1)
    hi = 1.15 * np.sin(np.pi * tt) ** 0.8
    zs_ = zb + hi
    ax.fill_between(x, zb, zs_, where=hi > 0, color=C_ICE, ec="none", zorder=2)
    ax.plot(x[hi > 0], zs_[hi > 0], color="#6aa5d0", lw=1.2, zorder=4)
    # 積雪(涵養域)
    xela = 4.3
    sn = (x >= xa) & (x <= xela)
    ax.fill_between(x, zs_, zs_ + 0.16, where=sn, color="white", ec="#9bbbd6", lw=0.8, zorder=3)
    # 崖の雪と雪崩
    ax.fill_between(x, zb, zb + 0.12, where=(x > 0.3) & (x < 1.3), color="white", ec="#9bbbd6", lw=0.8, zorder=3)
    arrow(ax, (0.75, 4.55), (1.55, 3.15), color=C_X, lw=2.0)
    ax.annotate(t["ava"], (1.05, 3.95), (1.5, 4.95), fontsize=8.5, ha="left", va="bottom",
                arrowprops=dict(arrowstyle="-", color=C_P, lw=0.7), zorder=8)
    # 涵養(雪 → 氷)
    for xv in (2.3, 2.9, 3.5):
        z0 = np.interp(xv, x, zs_)
        arrow(ax, (xv, z0 + 0.3), (xv, z0 - 0.15), color=C_C, lw=1.3)
    label(ax, 1.6, 4.2 if en else 4.25, t["acc"], color=C_C, fs=8.5, ha="left", va="bottom")
    # 平衡線
    zela = np.interp(xela, x, zs_)
    ax.plot([xela, xela], [zela - 0.05, 3.55], color=C_P, lw=1.0, ls="--", zorder=5)
    label(ax, xela + 0.1, 3.62, t["ela"], color=C_P, fs=8 if en else 8.5, ha="left", va="bottom")
    label(ax, 3.1, zela + 0.6, t["acc_z"], color=C_P, fs=8)
    label(ax, 5.9, zela + 0.6, t["abl_z"], color=C_P, fs=8)
    ax.annotate("", (xela - 0.1, zela + 0.42), (1.9, zela + 0.42), arrowprops=dict(arrowstyle="<->", color=C_P, lw=0.8))
    ax.annotate("", (7.4, zela + 0.42), (xela + 0.1, zela + 0.42), arrowprops=dict(arrowstyle="<->", color=C_P, lw=0.8))
    # 消耗と融解水
    label(ax, 5.3, 2.72, t["abl"], color=C_X, fs=8 if en else 8.5, ha="left", va="bottom")
    for xv in (6.3, 7.0):
        z0 = np.interp(xv, x, zs_)
        arrow(ax, (xv, z0 + 0.42), (xv, z0 + 0.08), color=C_X, lw=1.3)
    mx = np.linspace(7.0, 9.4, 30)
    ax.plot(mx, np.maximum(np.interp(mx, x, zs_), np.interp(mx, x, zb)) + 0.06, color=C_C, lw=1.8, zorder=6)
    ax.add_patch(FancyArrowPatch((9.3, np.interp(9.3, x, zb) + 0.06), (9.6, np.interp(9.6, x, zb) + 0.06),
                                 arrowstyle="-|>", mutation_scale=12, color=C_C, lw=1.8, zorder=6))
    label(ax, 8.05, 1.75, t["melt"], color=C_C, fs=8.5, ha="left", va="bottom")
    # 氷体流動・底面滑動
    xm = 4.9
    zm = np.interp(xm, x, zb) + np.interp(xm, x, hi) * 0.55
    arrow(ax, (3.3, zm + 0.15), (6.6, zm - 0.35), color="#2f6fb0", lw=2.2)
    label(ax, 4.6, zm + 0.48, t["flow"], color="#2f6fb0", fs=8.5)
    arrow(ax, (3.6, np.interp(3.6, x, zb) + 0.09), (6.2, np.interp(6.2, x, zb) + 0.09), color=C_X, lw=2.0)
    label(ax, 4.3 if en else 4.6, 1.0, t["slide"], color="white", fs=8 if en else 8.5)
    # 侵食(岩盤を下げる)
    ex = (x > 3.2) & (x < 6.8)
    ax.plot(x[ex], zb[ex] - 0.14, color=C_G, lw=1.3, ls="--", zorder=5)
    for xv in (3.6, 6.5):
        arrow(ax, (xv, np.interp(xv, x, zb) - 0.02), (xv, np.interp(xv, x, zb) - 0.3), color=C_G, lw=1.4)
    label(ax, 1.3, 0.5, t["ero"], color="white", fs=8 if en else 8.5, ha="left")
    # 凡例・脚注
    from matplotlib.patches import Patch
    handles = [Patch(fc="white", ec="#9bbbd6", label=t["snow"]), Patch(fc=C_ICE, ec="#6aa5d0", label=t["ice"]), Patch(fc=C_ROCK, label=t["rock"])]
    ax.legend(handles=handles, loc="upper right", fontsize=8, frameon=True, framealpha=0.9, edgecolor="none", ncol=3, bbox_to_anchor=(1.0, 1.0))
    label(ax, 0.0, -0.5, t["init"], color="k", fs=8.5, ha="left")
    label(ax, 0.0, -0.8, t["time"], color="k", fs=8.5, ha="left")
    ax.set_title(t["title"], loc="left", fontsize=9.5 if en else 10)
    return save(fig, "glacier_profile", lang)
