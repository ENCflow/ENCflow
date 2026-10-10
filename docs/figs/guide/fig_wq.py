"""水質の物質収支: 投入・減衰・沈降・Kd 分配・地下水経由・貯水池・蓄積-洗い出しの流れ図(wq.md)。"""
from _style import *

T = {"ja": {
    "title": "水質(fn_wq)の物質収支: 地表水・地下プール・表面蓄積プール・貯水池の間の移動(カッコ内は result/wq.csv の台帳列)",
    "in_pt": "点源\nwq_pt_cell\nwq_pt_load (g/s)\n/ wq_pt_series",
    "in_ar": "面源\nwq_ar_cell\nwq_ar_load\n(kg/ha/day)",
    "in_map": "分布面源\nfn_wq_map\n× wq_map_factor\n(f_wq_map=0)",
    "in_rain": "降雨中濃度\nwq_rain_conc\n/ wq_rain_series\n(mg/L)",
    "in_bc": "境界流入濃度\nwq_in_conc(n)\n/ wq_in_series",
    "in_gwc": "管路噴出・吐口\nwq_gwc_conc\n(要 f_gwconduit)",
    "surf": "地表水  濃度 C(mass_surface_g)\n移流は水と一緒に全量(溶存も粒子態も)\n減衰 wq_thalf / wq_k20(decay_g)\nKd 二相分配 wq_kd(要 f_suspend): fd = 1/(1 + Kd·Css)",
    "pool": "表面蓄積プール B\n(mass_pool_g)\n蓄積 wq_bd_rate\n/ fn_wq_map(f_wq_map=1)\n上限 wq_bd_max\n初期 wq_bd0 / fn_wq_bd0",
    "wash": "洗い出し(wash_g)\nwq_wash_kr(雨滴)\nwq_wash_kf, wq_wash_tauc(せん断)",
    "settle1": "沈降 f_wq_settle=1 → プールへ\n(粒子態 1−fd / wq_vs)",
    "settle0": "f_wq_settle=0: 河床へ消失\n(settle_g)",
    "gw": "地下プール(mass_gw_g)\nf_gwlateral=1 なら地下水と一緒に側方移動(速度 1/R、R = wq_rg)\n減衰も働く。風化基岩層 f_gwlayer2 内の輸送は未対応",
    "infil": "浸透 f_wq_infil=1(to_gw_g)\n溶存分 fd のみ同伴",
    "seep": "飽和湧出で地表へ\n濃度は 1/R 側(seep_g)",
    "dam": "ダム・湖沼(貯留型)\n完全混合池(mass_dam_g)\n放流濃度 M/V(スピルも)\n減衰あり・池内沈降なし\n水位固定湖沼 → 系外",
    "to_dam": "捕捉(to_dam_g)", "rel_dam": "放流(rel_dam_g)",
    "rs": "ため池 rscap\n(mass_rs_g) 蓄積のみ\n蒸発では濃縮",
    "to_rs": "吸収(to_rs_g)",
    "to_gwc": "枡に飲まれ管路側へ除去\nf_wq_gwc_in=1(to_gwc_g)",
    "out": "系外流出(境界)",
}, "en": {
    "title": "Substance budget of water quality (fn_wq): transfers between surface water, groundwater pool, surface buildup pool and reservoirs (ledger columns of result/wq.csv in brackets)",
    "in_pt": "point source\nwq_pt_cell\nwq_pt_load (g/s)\n/ wq_pt_series",
    "in_ar": "areal source\nwq_ar_cell\nwq_ar_load\n(kg/ha/day)",
    "in_map": "distributed source\nfn_wq_map\nx wq_map_factor\n(f_wq_map=0)",
    "in_rain": "rain concentration\nwq_rain_conc\n/ wq_rain_series\n(mg/L)",
    "in_bc": "boundary inflow\nwq_in_conc(n)\n/ wq_in_series",
    "in_gwc": "sewer surcharge\n/ outfall\nwq_gwc_conc\n(needs f_gwconduit)",
    "surf": "Surface water  concentration C (mass_surface_g)\nadvected entirely with the water (dissolved and particulate)\ndecay wq_thalf / wq_k20 (decay_g)\nKd two-phase partition wq_kd (needs f_suspend): fd = 1/(1 + Kd·Css)",
    "pool": "Surface buildup pool B\n(mass_pool_g)\nbuildup wq_bd_rate\n/ fn_wq_map (f_wq_map=1)\ncap wq_bd_max\ninitial wq_bd0 / fn_wq_bd0",
    "wash": "washoff (wash_g)\nwq_wash_kr (raindrop)\nwq_wash_kf, wq_wash_tauc (shear)",
    "settle1": "settling f_wq_settle=1 -> pool\n(particulate 1−fd / wq_vs)",
    "settle0": "f_wq_settle=0: lost to the bed\n(settle_g)",
    "gw": "Groundwater pool (mass_gw_g)\nwith f_gwlateral=1 moves with the groundwater (speed 1/R, R = wq_rg)\ndecay also acts; no transport inside the bedrock layer f_gwlayer2",
    "infil": "infiltration f_wq_infil=1 (to_gw_g)\ndissolved fraction fd only",
    "seep": "exfiltration back to surface\nconcentration on the 1/R side (seep_g)",
    "dam": "Dam / lake (storage type)\ncompletely mixed (mass_dam_g)\nrelease concentration M/V (spill too)\ndecay yes, in-lake settling no\nfixed-level lake -> leaves system",
    "to_dam": "capture (to_dam_g)", "rel_dam": "release (rel_dam_g)",
    "rs": "retention pond rscap\n(mass_rs_g) accumulates only\nevaporation concentrates",
    "to_rs": "absorbed (to_rs_g)",
    "to_gwc": "swallowed by inlets, removed to conduit\nf_wq_gwc_in=1 (to_gwc_g)",
    "out": "outflow across boundary",
}}


def box(ax, x, y, w, h, text, fc, ec, fs=7.5, tc="k", z=4, ha="center", lw=1.3):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fc, ec=ec, lw=lw, zorder=z))
    tx = x + 0.1 if ha == "left" else x + w / 2
    ax.text(tx, y + h / 2, text, fontsize=fs, color=tc, ha=ha, va="center", zorder=z + 1, linespacing=1.25)


def draw(lang):
    t = T[lang]
    fig, ax = plt.subplots(figsize=(10.5, 7.2), layout="constrained")
    ax.axis("off"); ax.set_xlim(0, 11.0); ax.set_ylim(-0.1, 7.3)
    # 投入(上段)
    keys = ["in_pt", "in_ar", "in_map", "in_rain", "in_bc", "in_gwc"]
    xin = [2.6, 3.95, 5.3, 6.65, 8.0, 9.35]
    for k, x in zip(keys, xin):
        box(ax, x, 5.85, 1.25, 1.3, t[k], "#fde6dc", C_X, fs=7)
    # 地表水
    SX, SY, SW, SH = 2.6, 3.1, 4.5, 1.45
    box(ax, SX, SY, SW, SH, t["surf"], "#eaf2fc", C_C, fs=7.6, lw=1.8)
    targets = [2.9, 3.6, 4.3, 5.0, 5.7, 6.4]
    for x, tx, k in zip(xin, targets, keys):
        arrow(ax, (x + 0.625, 5.82), (tx, SY + SH + 0.03), color=C_X, lw=1.4)
    # 管路側への除去(戻り矢印)
    arrow(ax, (6.9, SY + SH + 0.03), (9.6, 5.82), color=C_P, lw=1.2, ls="--")
    label(ax, 8.9, 4.95, t["to_gwc"], color=C_P, fs=7, ha="left", va="center", box=True)
    # 表面蓄積プール(左)
    box(ax, 0.1, 2.75, 2.0, 2.1, t["pool"], "#fdf3dc", "#b8860b", fs=7)
    arrow(ax, (1.1, 5.75), (1.1, 4.9), color=C_X, lw=1.4)
    arrow(ax, (2.13, 4.3), (SX - 0.03, 4.3), color=C_G, lw=1.8)
    label(ax, 2.35, 5.3, t["wash"], color="#3f7a2a", fs=7, ha="center", va="center")
    arrow(ax, (SX - 0.03, 3.5), (2.13, 3.5), color=C_P, lw=1.4)
    label(ax, 1.1, 2.45, t["settle1"], color=C_P, fs=7, ha="center", va="center")
    # 河床消失
    arrow(ax, (3.0, SY - 0.03), (3.0, 2.05), color=C_P, lw=1.4, ls="--")
    label(ax, 2.9, 1.78, t["settle0"], color=C_P, fs=7, ha="right", va="center")
    # 地下プール
    GX, GY, GW, GH = 2.6, 0.2, 4.5, 1.2
    box(ax, GX, GY, GW, GH, t["gw"], "#f1ece4", C_GROUND, fs=7.3)
    arrow(ax, (3.6, SY - 0.03), (3.6, GY + GH + 0.03), color=C_X, lw=1.8)
    label(ax, 3.75, 2.6, t["infil"], color=C_X, fs=7, ha="left", va="center")
    arrow(ax, (6.3, GY + GH + 0.03), (6.3, SY - 0.03), color=C_G, lw=1.8)
    label(ax, 6.15, 1.85, t["seep"], color="#3f7a2a", fs=7, ha="right", va="center")
    # ダム・湖沼(右)
    DX, DY, DW, DH = 8.2, 2.9, 2.7, 1.75
    box(ax, DX, DY, DW, DH, t["dam"], "#eaf2fc", C_C, fs=7)
    arrow(ax, (SX + SW + 0.03, 4.25), (DX - 0.03, 4.25), color=C_X, lw=1.6, text=t["to_dam"], dxy=(0, 0.2), fs=7)
    arrow(ax, (DX - 0.03, 3.55), (SX + SW + 0.03, 3.55), color=C_G, lw=1.6, text=t["rel_dam"], dxy=(0, -0.2), fs=7)
    # ため池
    box(ax, 8.2, 0.5, 2.7, 1.1, t["rs"], "#eaf2fc", C_C, fs=7)
    arrow(ax, (SX + SW + 0.03, 3.15), (DX - 0.03, 1.3), color=C_X, lw=1.4)
    label(ax, 7.5, 1.6, t["to_rs"], color=C_X, fs=7, ha="right", va="center")
    # 系外流出
    arrow(ax, (6.4, SY - 0.03), (6.9, 2.3), color=C_P, lw=1.4, ls="--")
    label(ax, 6.95, 2.2, t["out"], color=C_P, fs=7, ha="left", va="center")
    ax.set_title(t["title"], loc="left", fontsize=9, wrap=True)
    return save(fig, "wq_budget", lang)
