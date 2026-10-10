"""地下水の鉛直構造(土層・風化基岩層・管路連続体層・揚水・凍土)の断面模式図(gwflow.md)。"""
from _style import *

T = {"ja": {
    "title": "地下水の層構成と各モジュール(断面。土層 + 風化基岩層 + 管路連続体層。選択子は &list_gwflow)",
    "surf": "地表水 h", "soil": "土層(厚さ sd、比湧水量 sy0: &list_geoinfo)", "hg": "地下貯留 hg(飽和帯)",
    "vert": "鉛直 f_gwvertical\n1: バケツ(gw_infil_mmh, gw_capacity)\n2: Green-Ampt(gw_ksv_mmh, gw_psif\n   / fn_gw_ksv, fn_gw_psif)",
    "frost": "f_gwfrost=1: 凍土\n鉛直浸透能 × fac(FI)\nFI: 凍結指数(気温 fn_meteo)\nfro_fifull, fro_fmin, fro_tf …",
    "lat": "側方 f_gwlateral=1\nDarcy 流(8近傍)gw_ksh_mmh",
    "seep": "飽和超過\n→ 湧出",
    "l2": "風化基岩層 f_gwlayer2=1(gw2_depth, gw2_sy)", "l2in": "層1→2 浸透\ngw2_infil_mmh", "l2lat": "側方 gw2_ksh_mmh\n(0 = 容量のみ)", "l2up": "飽和超過\n→ 層1へ",
    "bed": "不透水(基盤)",
    "cond": "管路連続体層 f_gwconduit=1(下水道網・岩盤亀裂網)  貯留 hgc\ngwc_cap(容量), gwc_cnd(通水能), 管底 gwc_depth / fn_gwc_bot, gwc_sy・gwc_slot_sy",
    "inlet": "枡 gwc_inlet\n流入(堰 gwc_cw / 満管はオリフィス gwc_co)",
    "surcharge": "被圧(hgc > cap)\n→ 噴出", "clat": "8方向 f_gwc_fluxlaw\n(1: 線形, 2: sqrt)",
    "leak": "層間交換 gwc_leak_layer\n1: 土層 / 2: 風化基岩層\n(gwc_leak_mmh)",
    "outfall": "吐口 fn_gwc_outfall\n海隣接: 海へ(系外)\nなし: 自セル地表へ",
    "pump": "井戸 f_gwpump=1\ngwp_q0 / gwp_val\ngwp_layer 1: 土層\n          2: 層2\n(系外へ除去)",
    "sea": "海域 /\n河道",
}, "en": {
    "title": "Groundwater layers and modules (section: soil layer + weathered bedrock + conduit continuum; selectors in &list_gwflow)",
    "surf": "surface water h", "soil": "soil layer (thickness sd, specific yield sy0: &list_geoinfo)", "hg": "storage hg (saturated zone)",
    "vert": "vertical f_gwvertical\n1: bucket (gw_infil_mmh, gw_capacity)\n2: Green-Ampt (gw_ksv_mmh, gw_psif\n   / fn_gw_ksv, fn_gw_psif)",
    "frost": "f_gwfrost=1: frozen ground\nvertical infiltration x fac(FI)\nFI: freezing index (air temp. fn_meteo)\nfro_fifull, fro_fmin, fro_tf ...",
    "lat": "lateral f_gwlateral=1\nDarcy flow (8 neighbours) gw_ksh_mmh",
    "seep": "saturation excess\n-> exfiltration",
    "l2": "weathered bedrock layer f_gwlayer2=1 (gw2_depth, gw2_sy)", "l2in": "layer 1->2\ngw2_infil_mmh", "l2lat": "lateral gw2_ksh_mmh\n(0 = capacity only)", "l2up": "saturation excess\n-> back to layer 1",
    "bed": "impermeable base",
    "cond": "conduit continuum layer f_gwconduit=1 (sewer / fracture network)  storage hgc\ngwc_cap (capacity), gwc_cnd (conveyance), invert gwc_depth / fn_gwc_bot, gwc_sy, gwc_slot_sy",
    "inlet": "inlets gwc_inlet\ninflow (weir gwc_cw / orifice gwc_co when full)",
    "surcharge": "pressurized (hgc > cap)\n-> surcharge to surface", "clat": "8 directions f_gwc_fluxlaw\n(1: linear, 2: sqrt)",
    "leak": "leakage gwc_leak_layer\n1: soil / 2: bedrock layer\n(gwc_leak_mmh)",
    "outfall": "outfall fn_gwc_outfall\nnext to sea: to sea (removed)\nelse: to own cell surface",
    "pump": "well f_gwpump=1\ngwp_q0 / gwp_val\ngwp_layer 1: soil\n          2: layer 2\n(removed from system)",
    "sea": "sea /\nriver",
}}

ROT = -10   # 層に沿う文字の回転(視覚上の勾配)


def draw(lang):
    t = T[lang]
    fig, ax = plt.subplots(figsize=(10.5, 6.8), layout="constrained")
    ax.axis("off"); ax.set_xlim(-0.2, 11.8); ax.set_ylim(-2.3, 7.6)
    def zs(x):
        return 5.2 - 0.25 * x
    SD, D2 = 1.3, 1.5
    def zb(x):
        return zs(x) - SD - D2
    xs = [0, 2, 4, 6, 8, 9.2]
    surf = [zs(x) for x in xs]
    base = [zb(x) for x in xs]
    # 層2(風化基岩)・土層・基盤
    ax.add_patch(Polygon([(x, z - SD) for x, z in zip(xs, surf)] + [(x, b) for x, b in zip(xs[::-1], base[::-1])], fc=C_ROCK, ec=C_GROUND, lw=0.8, alpha=0.55, zorder=1))
    ax.add_patch(Polygon([(x, z) for x, z in zip(xs, surf)] + [(x, z - SD) for x, z in zip(xs[::-1], surf[::-1])], fc=C_SOIL, ec=C_GROUND, lw=0.8, alpha=0.75, zorder=1))
    ax.add_patch(Polygon([(x, b) for x, b in zip(xs, base)] + [(11.8, base[-1]), (11.8, -2.3), (0, -2.3)], fc="#d9d8d3", ec="none", hatch="///", zorder=0.5))
    # 飽和帯(層1・層2)
    sat1 = [z - SD + 0.35 + 0.08 * x for x, z in zip(xs, surf)]
    ax.add_patch(Polygon([(x, s) for x, s in zip(xs, sat1)] + [(x, z - SD) for x, z in zip(xs[::-1], surf[::-1])], fc=C_WATER_L, ec=C_WATER, lw=0.8, zorder=2))
    sat2 = [b + 0.6 for b in base]
    ax.add_patch(Polygon([(x, s) for x, s in zip(xs, sat2)] + [(x, b) for x, b in zip(xs[::-1], base[::-1])], fc="#bcd3ee", ec=C_WATER, lw=0.6, zorder=2))
    # 海 / 河道(右端の水体のみ)
    ax.add_patch(Rectangle((9.2, zb(9.2)), 1.0, zs(9.2) + 0.2 - zb(9.2), fc=C_SEA, ec="none", alpha=0.35, zorder=1.5))
    label(ax, 9.7, zs(9.2) - 1.1, t["sea"], color=C_C, fs=8.5)
    # 地表水(薄い帯)
    ax.add_patch(Polygon([(x, z) for x, z in zip(xs, surf)] + [(x, z + 0.2) for x, z in zip(xs[::-1], surf[::-1])], fc=C_WATER_L, ec=C_WATER, lw=0.8, zorder=2))
    label(ax, 0.1, zs(0) + 0.45, t["surf"], color=C_C, fs=8.5, ha="left")
    # 層のラベル(勾配に沿わせる)
    label(ax, 0.3, zs(0.3) - 0.42, t["soil"], color="#6b4f1d", fs=8, ha="left", rotation=ROT, rotation_mode="anchor")
    label(ax, 0.3, zs(0.3) - SD + 0.12, t["hg"], color=C_C, fs=8, ha="left", rotation=ROT, rotation_mode="anchor")
    label(ax, 0.3, zs(0.3) - SD - 0.85, t["l2"], color="#3f3d3a", fs=8, ha="left", rotation=ROT, rotation_mode="anchor")
    label(ax, 0.4, zb(0.4) + 0.22, "hg2", color=C_C, fs=8, ha="left")
    label(ax, 6.0, -2.0, t["bed"], color=C_P, fs=8, ha="center", box=True)
    # --- 上段の説明: 鉛直・凍土・管路層
    label(ax, 0.0, 7.5, t["vert"], color=C_X, fs=8, ha="left", va="top")
    label(ax, 3.9, 7.5, t["frost"], color="#2f6fb3", fs=7.5, ha="left", va="top")
    label(ax, 11.7, 7.5, t["cond"], color=C_P, fs=7.5, ha="right", va="top")
    # 鉛直浸透
    arrow(ax, (1.0, zs(1.0) + 0.2), (1.0, zs(1.0) - 0.6), color=C_X, lw=2.2)
    # --- 側方流(層1)
    arrow(ax, (2.6, zs(2.6) - SD + 0.4), (4.6, zs(4.6) - SD + 0.5), color=C_C, lw=2.2)
    label(ax, 1.4, zs(1.4) + 0.95, t["lat"], color=C_C, fs=8, ha="left", va="bottom")
    ax.plot([2.3, 2.9], [zs(1.4) + 0.95, zs(2.9) - SD + 0.65], color=C_C, lw=0.7, ls=":", zorder=5)
    # --- 湧出(右の低地)
    arrow(ax, (8.4, zs(8.4) - SD + 0.4), (8.4, zs(8.4) + 0.35), color=C_G, lw=2.2)
    label(ax, 8.55, zs(8.4) + 0.75, t["seep"], color="#3f7a2a", fs=8, ha="left", va="center")
    # --- 層2: 浸透・側方・戻り
    arrow(ax, (2.3, zs(2.3) - SD + 0.05), (2.3, zs(2.3) - SD - 0.7), color=C_X, lw=1.8)
    label(ax, 2.45, zs(2.3) - SD - 0.38, t["l2in"], color=C_X, fs=7.5, ha="left", va="center")
    arrow(ax, (4.2, zb(4.2) + 0.32), (5.4, zb(5.4) + 0.32), color=C_C, lw=1.8)
    label(ax, 4.1, zb(4.1) + 0.95, t["l2lat"], color=C_C, fs=7.5, ha="left", va="center")
    arrow(ax, (6.3, zs(6.3) - SD - 0.7), (6.3, zs(6.3) - SD + 0.1), color=C_G, lw=1.8)
    label(ax, 6.45, zs(6.3) - SD - 0.45, t["l2up"], color="#3f7a2a", fs=7.5, ha="left", va="center")
    # --- 管路連続体層(右側の土層内、埋設深 gwc_depth)
    cx0, cx1 = 6.0, 9.0
    cz = [zs(x) - 0.55 for x in (cx0, cx1)]
    ax.add_patch(Polygon([(cx0, cz[0]), (cx1, cz[1]), (cx1, cz[1] - 0.3), (cx0, cz[0] - 0.3)], fc="white", ec=C_P, lw=1.4, ls="--", zorder=3))
    ax.add_patch(Polygon([(cx0, cz[0] - 0.05), (cx1, cz[1] - 0.05), (cx1, cz[1] - 0.3), (cx0, cz[0] - 0.3)], fc="#bcd3ee", ec="none", zorder=3.5))
    label(ax, 6.35, zs(6.35) - 0.7, "hgc", color=C_C, fs=8)
    # 枡流入(地表→管)・噴出(管→地表)
    arrow(ax, (6.5, zs(6.5) + 0.2), (6.5, zs(6.5) - 0.5), color=C_X, lw=2.0)
    arrow(ax, (7.1, zs(7.1) - 0.55), (7.1, zs(7.1) + 0.5), color=C_G, lw=2.0)
    label(ax, 5.6, zs(5.6) + 1.3, t["inlet"], color=C_X, fs=7.5, ha="left", va="bottom")
    label(ax, 6.3, zs(7.1) + 0.65, t["surcharge"], color="#3f7a2a", fs=7.5, ha="left", va="bottom")
    # 側方(管)
    arrow(ax, (6.9, zs(6.9) - 0.72), (8.7, zs(8.7) - 0.72), color=C_C, lw=1.4)
    label(ax, 10.4, zs(9.2) - 1.1, t["clat"], color=C_C, fs=7.2, ha="left", va="center")
    # 層間交換(管↔土層 / 層2)
    arrow(ax, (7.9, zs(7.9) - 0.9), (7.9, zs(7.9) - 1.5), color=C_P, lw=1.4, ls="--")
    arrow(ax, (8.1, zs(8.1) - 1.5), (8.1, zs(8.1) - 0.9), color=C_P, lw=1.4, ls="--")
    label(ax, 10.4, zs(9.2) - 1.9, t["leak"], color=C_P, fs=7.2, ha="left", va="center")
    ax.plot([8.2, 10.35], [zs(8.1) - 1.55, zs(9.2) - 1.9], color=C_P, lw=0.7, ls=":", zorder=5)
    # 吐口
    arrow(ax, (9.0, zs(9.0) - 0.7), (9.9, zs(9.0) - 0.7), color=C_G, lw=1.8)
    label(ax, 10.4, zs(9.2) - 0.25, t["outfall"], color="#3f7a2a", fs=7.2, ha="left", va="center")
    # --- 井戸揚水
    wx = 3.9
    ax.add_patch(Rectangle((wx - 0.08, zb(wx) + 0.3), 0.16, SD + D2 + 0.4, fc="white", ec="k", lw=1.0, zorder=4))
    ax.add_patch(Rectangle((wx - 0.08, zs(wx) - SD + 0.1), 0.16, 0.55, fc=C_WATER_L, ec="k", lw=1.0, zorder=5))
    ax.add_patch(Rectangle((wx - 0.08, zb(wx) + 0.3), 0.16, 0.5, fc="#bcd3ee", ec="k", lw=1.0, zorder=5))
    arrow(ax, (wx, zs(wx) + 0.75), (wx, zs(wx) + 1.6), color=C_X, lw=2.0)
    label(ax, wx + 0.2, zs(wx) + 1.4, t["pump"], color=C_X, fs=7.5, ha="left", va="center")
    ax.set_title(t["title"], loc="left", fontsize=9.5)
    return save(fig, "gwflow_layers", lang)
