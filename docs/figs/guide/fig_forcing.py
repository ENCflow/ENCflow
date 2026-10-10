"""降雨・気象の 5 機能の作用順(降水 → 遮断 → 雨雪判定・積雪 → 地表水、蒸発散)の模式図(forcing.md)。"""
from _style import *

T = {"ja": {
    "title": "気象強制の鎖: 降水 → 樹冠遮断 → 雨雪判定・積雪 → 地表水(蒸発散で減る)。各段を制御する namelist グループ",
    "precip": "降水 P(fn_precip, &list_precip)\nprtype 1: 一様時系列 prval / 2: 固定分布 fn_prmap × 倍率 prval\n/ 3: 分布ファイル群 fn_maplist(dt_maplist)。× runoff_rate",
    "icept": "樹冠遮断(fn_intercept, &list_intercept)\nf_icmodel 1: 固定遮断率 ic_alpha → 有効雨量 (1−α)P\nf_icmodel 2: 初期損失 ic_smax_mm まで貯留、満たせば素通し",
    "loss": "遮断損失",
    "snow": "雨雪判定・積雪(fn_snow, &list_snow)\nT ≤ snow_t_snow: 全て雪 / T ≥ snow_t_rain: 全て雨(間は線形混合)",
    "pack": "積雪 SWE\n(初期 snow_swe0 / fn_snow_swe0)",
    "melt": "融雪(度日法)\n= snow_ddf ×\n(T − snow_t_melt)",
    "rain": "雨", "snowfall": "雪",
    "surf": "地表水 h(浅水流)",
    "evap": "蒸発散(fn_evap, &list_evap)\nf_evmodel 1: evap0 / 2: evap_monthly\n/ 3: Hamon(lat) / 4: Thornthwaite(temp_normal)\n× evap_kc。地表水から供給制限つきで減らす",
    "infil": "浸透 → 地下水\n(fn_gwflow。地下水の章)",
    "meteo": "気象強制場(fn_meteo, &list_meteo)\n気温 T: temp0 / tempval / fn_tempmap\nf_temp_lapse=1: T(z) = T − temp_lapse×(z − temp_zref)\ntempofs: 長周期の気温オフセット\nf_prec_lapse=1: 降水に 1 + prec_lapse×(z − prec_zref)",
    "T": "気温 T", "Tsnow": "T", "Tevap": "気温 T(モード 3, 4)", "Plapse": "降水の標高勾配",
    "ground": "地表",
}, "en": {
    "title": "Forcing chain: precipitation -> interception -> rain/snow & snowpack -> surface water (minus ET), with the namelist group of each stage",
    "precip": "Precipitation P (fn_precip, &list_precip)\nprtype 1: uniform series prval / 2: fixed map fn_prmap x factor prval\n/ 3: map files fn_maplist (dt_maplist). x runoff_rate",
    "icept": "Canopy interception (fn_intercept, &list_intercept)\nf_icmodel 1: fixed rate ic_alpha -> effective rain (1−α)P\nf_icmodel 2: initial loss stored up to ic_smax_mm, then passes",
    "loss": "interception loss",
    "snow": "Rain/snow split and snowpack (fn_snow, &list_snow)\nT <= snow_t_snow: all snow / T >= snow_t_rain: all rain (linear mix between)",
    "pack": "Snowpack SWE\n(initial snow_swe0 / fn_snow_swe0)",
    "melt": "melt (degree-day)\n= snow_ddf x\n(T − snow_t_melt)",
    "rain": "rain", "snowfall": "snow",
    "surf": "Surface water h (shallow-water flow)",
    "evap": "Evapotranspiration (fn_evap, &list_evap)\nf_evmodel 1: evap0 / 2: evap_monthly\n/ 3: Hamon (lat) / 4: Thornthwaite (temp_normal)\nx evap_kc; removed from surface water, supply-limited",
    "infil": "infiltration -> groundwater\n(fn_gwflow; groundwater chapter)",
    "meteo": "Meteorological field (fn_meteo, &list_meteo)\nair temperature T: temp0 / tempval / fn_tempmap\nf_temp_lapse=1: T(z) = T − temp_lapse x (z − temp_zref)\ntempofs: long-period temperature offset\nf_prec_lapse=1: precipitation x (1 + prec_lapse x (z − prec_zref))",
    "T": "air temp. T", "Tsnow": "T", "Tevap": "air temp. T (modes 3, 4)", "Plapse": "elevation gradient of P",
    "ground": "ground",
}}


def box(ax, x, y, w, h, text, fc, ec, fs=8, tc="k", z=4, ha="left"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fc, ec=ec, lw=1.2, zorder=z))
    tx = x + 0.12 if ha == "left" else x + w / 2
    ax.text(tx, y + h / 2, text, fontsize=fs, color=tc, ha=ha, va="center", zorder=z + 1)


def draw(lang):
    t = T[lang]
    fig, ax = plt.subplots(figsize=(10.5, 6.6), layout="constrained")
    ax.axis("off"); ax.set_xlim(0, 10.5); ax.set_ylim(-0.3, 6.9)
    xc = 2.8                       # 主鎖の中心 x(矢印)
    # 降水
    box(ax, 0.2, 5.55, 6.3, 0.95, t["precip"], "#fde6dc", C_X, fs=8)
    arrow(ax, (xc, 5.5), (xc, 4.95), color=C_X, lw=2.2)
    # 遮断(損失は上右へ抜ける)
    box(ax, 0.2, 4.0, 6.3, 0.9, t["icept"], "#edf4e6", C_G, fs=8)
    arrow(ax, (6.55, 4.6), (6.85, 5.15), color=C_P, lw=1.2, ls="--")
    label(ax, 6.95, 5.3, t["loss"], color=C_P, fs=7.5, ha="left", va="center")
    arrow(ax, (xc, 3.95), (xc, 3.4), color=C_X, lw=2.2)
    # 雨雪判定・積雪(文は箱の上部、矢印は下部)
    ax.add_patch(FancyBboxPatch((0.2, 1.9), 6.3, 1.45, boxstyle="round,pad=0.02,rounding_size=0.08", fc="#eaf2fc", ec=C_C, lw=1.2, zorder=4))
    ax.text(0.32, 3.0, t["snow"], fontsize=8, color="k", ha="left", va="center", zorder=5)
    arrow(ax, (1.6, 2.7), (1.6, 1.95), color=C_X, lw=2.2, text=t["rain"], dxy=(-0.25, 0), fs=8.5)
    arrow(ax, (3.5, 2.4), (4.3, 2.4), color=C_C, lw=1.6, text=t["snowfall"], dxy=(-0.6, 0), fs=8.5)
    ax.add_patch(Rectangle((4.35, 2.02), 2.05, 0.72, fc=C_ICE, ec=C_C, lw=1.0, zorder=5))
    ax.text(5.37, 2.38, t["pack"], fontsize=7.5, color=C_C, ha="center", va="center", zorder=6)
    arrow(ax, (4.6, 1.98), (4.6, 1.2), color=C_X, lw=2.0)
    label(ax, 4.75, 1.55, t["melt"], color=C_X, fs=7.5, ha="left", va="center")
    # 地表水(帯)と地盤
    ax.add_patch(Rectangle((0.2, 0.55), 6.3, 0.6, fc=C_WATER_L, ec=C_WATER, lw=1.2, zorder=3))
    ax.text(0.35, 0.85, t["surf"], fontsize=9, color=C_C, ha="left", va="center", zorder=5)
    ax.add_patch(Rectangle((0.2, -0.3), 6.3, 0.85, fc=C_GROUND_L, ec=C_GROUND, lw=1.0, zorder=2))
    label(ax, 6.35, 0.4, t["ground"], color=C_GROUND, fs=8, ha="right", va="top")
    # 浸透(別章)
    arrow(ax, (2.8, 0.5), (2.8, -0.05), color=C_P, lw=1.4, ls="--")
    label(ax, 2.95, 0.2, t["infil"], color=C_P, fs=7.5, ha="left", va="center")
    # 蒸発散: 地表水から右の箱へ(損失)
    box(ax, 6.9, 0.2, 3.45, 1.45, t["evap"], "#edf4e6", C_G, fs=7.5)
    arrow(ax, (6.53, 0.85), (6.87, 0.85), color=C_G, lw=2.0)
    # 気象強制場(右)
    box(ax, 6.9, 2.4, 3.45, 2.2, t["meteo"], "#f6f6f4", C_P, fs=7.5)
    arrow(ax, (6.9, 3.15), (6.55, 3.15), color=C_P, lw=1.6)
    label(ax, 6.72, 3.38, t["Tsnow"], color=C_P, fs=8, ha="center", va="center")
    arrow(ax, (8.6, 2.35), (8.6, 1.7), color=C_P, lw=1.6, text=t["Tevap"], dxy=(0.1, 0), ha="left", fs=7.5)
    ax.plot([8.6, 8.6], [4.65, 5.5], color=C_P, lw=1.6, ls="--", zorder=5)
    arrow(ax, (8.6, 5.5), (6.55, 6.0), color=C_P, lw=1.6, ls="--", text=t["Plapse"], dxy=(0.55, 0.2), fs=7.5)
    ax.set_title(t["title"], loc="left", fontsize=9.5)
    return save(fig, "forcing_chain", lang)
