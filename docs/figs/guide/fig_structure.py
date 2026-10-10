"""内部水理構造物の 4 型(排水ポンプ・カルバート・分水・ダム/湖沼)の模式図(structure.md)。"""
from _style import *

T = {"ja": {
    "a": "(a) 排水ポンプ(&list_struct_pump)\n取水セル群 → 吐口セル群(または域外)への強制転送",
    "b": "(b) カルバート(&list_struct_culvert)\n盛土を横断する矩形暗渠 B×D。水頭差で双方向",
    "c": "(c) 分水(&list_struct_diversion)\n取水セル群から域外(または送水先)へ一方向・受動的",
    "d": "(d) ダム・湖沼(&list_struct_dam)\n湖面セルが到達水を全量捕捉 → 貯留 V(H) → 運転則で放流",
    "pump_in": "pump_in_cell\n(取水セル群)", "pump_out": "pump_out_cell\n(吐口セル群)",
    "pump_q": "Q = pump_q0(一定)\n  or pump_rule(基準値→Q の折れ線)\n基準 f_pump_ref: 0 = η, 1 = h\n(取水代表セル=先頭)",
    "pump_outside": "省略 → 域外排水\n(系から除去)", "pump_src": "f_pump_src = 1:\n管路連続体層 hgc から汲む",
    "pump_pond": "ため池セル(rscap>0)\nなら貯留から汲む", "levee": "堤防・盛土", "river": "河道",
    "culv_in": "culv_in_cell", "culv_out": "culv_out_cell", "culv_zin": "culv_zin", "culv_zout": "culv_zout",
    "culv_BD": "culv_width B\nculv_height D", "culv_L": "culv_length L(culv_manning n、culv_ce)",
    "culv_regime": "水位に応じて 無流 → 自由水面(堰)→ 満管(オリフィス+摩擦)",
    "culv_flap": "culv_flap = 1: out→in の逆流を遮断",
    "culv_gate": "culv_gate_rule(基準水位→開度 0〜1)\nculv_gate_ref: 0 = in 側, 1 = out 側(河川側)",
    "div_in": "div_in_cell\n(取水セル群。堰直上流)", "div_q": "Q = div_q0(一定)\n  or div_rule(取水代表セルの η → Q)",
    "div_outside": "省略 → 域外分水", "div_out": "div_out_cell(送水先)\n送水先の η ≥ 取水側 なら自動停止",
    "div_passive": "重力では登れない(強制は ポンプ)", "flow": "流下",
    "lake_cells": "湖面 = 捕捉集合: dam_in_cell / fn_dam_in_cell / fn_dam_map(湖沼番号ラスタ)",
    "capture": "到達水を\n毎ステップ全量吸収", "H": "水位 H(絶対標高)", "V": "V(H): dam_hv(HV 曲線)\n  or dam_hmin [+dam_hsur]\n  (線形 A·(H−hmin))",
    "hsur": "サーチャージ → 超過分は強制スピル", "hmin": "最低水位 = 死水\n(dam_hmin / HV の第1点)",
    "tadashigaki": "dam_tadashigaki: 但し書き操作(モード 1, 2)",
    "release": "放流 Q → dam_out_cell\nf_dam_mode 1: dam_q0 / 2: dam_rate×Qin / 3: Q(H)\n (dam_hq_rule / オリフィス / dam_qmax √則)",
    "lake": "dam_lake(n) = m: 追加の放流工\n湖沼 m の貯留から別の運転則・\n放流セルで引く", "gw": "dam_gw = 1: 湖面セルの地下水頭 = H\n(要 f_gwlateral=1。交換量 Qgw)",
    "noout": "放流セルなし+モード指定なし = 水位固定湖沼(流入は消失)", "dam": "堤体",
    "hinit": "dam_h_init(初期水位)",
}, "en": {
    "a": "(a) Drainage pump (&list_struct_pump)\nforced transfer: intake cells -> outlet cells (or outside)",
    "b": "(b) Culvert (&list_struct_culvert)\nB x D box through an embankment; head-driven, bidirectional",
    "c": "(c) Diversion (&list_struct_diversion)\npassive one-way withdrawal, to outside or receiving cells",
    "d": "(d) Dam / lake (&list_struct_dam)\nlake cells capture inflow -> storage V(H) -> release by rule",
    "pump_in": "pump_in_cell\n(intake cells)", "pump_out": "pump_out_cell\n(outlet cells)",
    "pump_q": "Q = pump_q0 (constant)\n  or pump_rule (reference -> Q polyline)\nreference f_pump_ref: 0 = eta, 1 = h\n(first intake cell)",
    "pump_outside": "omitted -> out of domain\n(removed from system)", "pump_src": "f_pump_src = 1:\ndraws from conduit layer hgc",
    "pump_pond": "pond cell (rscap>0):\ndraws from pond storage", "levee": "levee / embankment", "river": "river",
    "culv_in": "culv_in_cell", "culv_out": "culv_out_cell", "culv_zin": "culv_zin", "culv_zout": "culv_zout",
    "culv_BD": "culv_width B\nculv_height D", "culv_L": "culv_length L (culv_manning n, culv_ce)",
    "culv_regime": "by water level: no flow -> free surface (weir) -> full pipe (orifice + friction)",
    "culv_flap": "culv_flap = 1: blocks out->in backflow",
    "culv_gate": "culv_gate_rule (reference level -> opening 0-1)\nculv_gate_ref: 0 = in side, 1 = out side (river)",
    "div_in": "div_in_cell\n(intake cells, just upstream of weir)", "div_q": "Q = div_q0 (constant)\n  or div_rule (eta of first intake cell -> Q)",
    "div_outside": "omitted -> out of domain", "div_out": "div_out_cell (receiving cells)\nstops when receiving eta >= intake eta",
    "div_passive": "gravity cannot climb (use a pump to force)", "flow": "flow",
    "lake_cells": "lake surface = capture set: dam_in_cell / fn_dam_in_cell / fn_dam_map (lake-number raster)",
    "capture": "absorbs all arriving\nwater every step", "H": "level H (absolute elevation)", "V": "V(H): dam_hv (HV curve)\n  or dam_hmin [+dam_hsur]\n  (linear A·(H−hmin))",
    "hsur": "surcharge -> excess is forced spill", "hmin": "minimum level = dead storage\n(dam_hmin / 1st HV point)",
    "tadashigaki": "dam_tadashigaki: emergency rule",
    "release": "release Q -> dam_out_cell\nf_dam_mode 1: dam_q0 / 2: dam_rate x Qin / 3: Q(H)\n (dam_hq_rule / orifice / dam_qmax sqrt law)",
    "lake": "dam_lake(n) = m: extra outlet\ndrawing lake m's storage with\nits own rule and outlet cells", "gw": "dam_gw = 1: groundwater head in lake cells = H\n(needs f_gwlateral=1; exchange Qgw)",
    "noout": "no outlet cells + no mode = fixed-level lake (inflow vanishes)", "dam": "dam body",
    "hinit": "dam_h_init (initial level)",
}}


def water(ax, xs, ybot, ytop, color=C_WATER_L, ec=C_WATER, z=2):
    ax.add_patch(Polygon(list(zip(xs, ybot)) + list(zip(xs[::-1], ytop[::-1])), closed=True, fc=color, ec=ec, lw=1.0, zorder=z))


def panel_pump(ax, t):
    ax.axis("off"); ax.set_xlim(-0.2, 10.4); ax.set_ylim(-0.6, 4.4)
    # 地盤: 低地(左)・堤防・河道(右)
    gx = [0, 2.6, 4.0, 4.6, 5.6, 6.2, 7.2, 8.6, 10.2]
    gz = [1.0, 0.9, 1.3, 2.6, 2.6, 1.3, 0.3, 0.3, 1.6]
    ax.add_patch(Polygon(list(zip(gx, gz)) + [(10.2, -0.6), (0, -0.6)], fc=C_GROUND_L, ec=C_GROUND, lw=1, zorder=1))
    # 低地の内水
    water(ax, [0, 2.6, 4.0, 4.3], [1.0, 0.9, 1.3, 1.6], [1.6] * 4)
    # 河道の水
    water(ax, [6.5, 7.2, 8.6, 9.6], [0.9, 0.3, 0.3, 0.9], [1.1] * 4)
    # ポンプと管
    ax.add_patch(Rectangle((4.65, 2.65), 0.9, 0.55, fc=C_X, ec="k", lw=0.8, zorder=5))
    label(ax, 5.1, 2.92, "P", color="white", fs=10, fontweight="bold")
    ax.plot([2.0, 2.0, 4.65], [1.2, 2.92, 2.92], color=C_X, lw=2.2, zorder=4)
    ax.plot([5.55, 7.6, 7.6], [2.92, 2.92, 1.3], color=C_X, lw=2.2, zorder=4)
    arrow(ax, (7.6, 1.6), (7.6, 1.15), color=C_X, lw=2.2)
    arrow(ax, (2.0, 1.15), (2.0, 1.6), color=C_X, lw=2.2)
    # 域外
    ax.plot([5.55, 6.4], [2.92, 3.7], color=C_X, lw=1.4, ls="--", zorder=4)
    arrow(ax, (6.4, 3.7), (7.0, 4.2), color=C_X, lw=1.4, ls="--")
    label(ax, 7.15, 3.95, t["pump_outside"], color=C_X, fs=8, ha="left", va="center")
    # ラベル
    label(ax, 1.3, 1.95, t["pump_in"], color=C_C, fs=8.5)
    label(ax, 8.3, 1.55, t["pump_out"], color=C_C, fs=8.5)
    label(ax, 0.1, 3.9, t["pump_q"], color=C_X, fs=8, ha="left", va="top")
    label(ax, 5.1, 2.3, t["levee"], color=C_GROUND, fs=8)
    label(ax, 9.6, 0.1, t["river"], color=C_GROUND, fs=8, ha="right")
    label(ax, 2.75, 0.5, t["pump_pond"], color=C_P, fs=7.5, ha="left", va="center")
    # 管路層からの取水
    ax.add_patch(Rectangle((1.3, -0.35), 1.6, 0.35, fc="none", ec=C_P, lw=1.0, ls="--", zorder=3))
    label(ax, 2.1, -0.18, "hgc", color=C_P, fs=8)
    ax.plot([2.0, 2.0], [0.0, 1.0], color=C_P, lw=1.2, ls=":", zorder=3)
    label(ax, 3.0, -0.2, t["pump_src"], color=C_P, fs=7.5, ha="left", va="center")
    ax.set_title(t["a"], loc="left", fontsize=9)


def panel_culvert(ax, t):
    ax.axis("off"); ax.set_xlim(-0.2, 10.4); ax.set_ylim(-0.6, 4.4)
    # 盛土(台形)と地盤
    ax.add_patch(Rectangle((0, -0.6), 10.2, 1.4, fc=C_GROUND_L, ec="none", zorder=1))
    ax.add_patch(Polygon([(3.2, 0.8), (4.4, 3.0), (5.8, 3.0), (7.0, 0.8)], fc=C_GROUND_L, ec=C_GROUND, lw=1, zorder=2))
    ax.plot([0, 3.2], [0.8, 0.8], color=C_GROUND, lw=1, zorder=2); ax.plot([7.0, 10.2], [0.8, 0.8], color=C_GROUND, lw=1, zorder=2)
    # 水(上流側高い)
    water(ax, [0, 3.8], [0.8, 0.8], [2.3, 2.3], z=1.5)
    water(ax, [6.4, 10.2], [0.8, 0.8], [1.7, 1.7], z=1.5)
    # 暗渠(矩形 B×D) 敷高 zin(左) > zout(右)
    zin, zout, D = 1.05, 0.95, 0.75
    ax.add_patch(Polygon([(3.3, zin), (6.9, zout), (6.9, zout + D), (3.3, zin + D)], fc="white", ec="k", lw=1.4, zorder=3))
    arrow(ax, (3.6, zin + D / 2 + 0.08), (6.6, zout + D / 2 + 0.08), color=C_C, lw=2)
    arrow(ax, (6.6, zout + D / 2 - 0.15), (3.6, zin + D / 2 - 0.15), color=C_C, lw=1.2, ls="--")
    # フラップ(右端)
    ax.plot([6.9, 6.75], [zout + D, zout + 0.15], color=C_X, lw=2.2, zorder=5)
    label(ax, 7.05, zout + D + 0.1, t["culv_flap"], color=C_X, fs=7.5, ha="left", va="bottom")
    # 敷高・寸法
    label(ax, 3.0, zin - 0.25, t["culv_zin"], color=C_P, fs=8, ha="right")
    label(ax, 7.1, zout - 0.3, t["culv_zout"], color=C_P, fs=8, ha="left")
    ax.plot([2.75, 3.3], [zin, zin], color=C_P, lw=0.8, zorder=4); ax.plot([6.9, 7.3], [zout, zout], color=C_P, lw=0.8, zorder=4)
    label(ax, 5.1, 2.35, t["culv_BD"], color="k", fs=8)
    label(ax, 5.1, 0.45, t["culv_L"], color=C_P, fs=7.5)
    # セル名
    label(ax, 1.6, 2.6, t["culv_in"], color=C_C, fs=8.5)
    label(ax, 8.4, 2.0, t["culv_out"], color=C_C, fs=8.5)
    # 水位線
    ax.plot([0, 3.8], [2.3, 2.3], color=C_WATER, lw=1); ax.plot([6.4, 10.2], [1.7, 1.7], color=C_WATER, lw=1)
    # ゲート・レジーム
    label(ax, 0.1, 4.2, t["culv_regime"], color="k", fs=8, ha="left", va="top")
    label(ax, 10.2, 3.75, t["culv_gate"], color=C_X, fs=7.5, ha="right", va="top")
    ax.set_title(t["b"], loc="left", fontsize=9)


def panel_diversion(ax, t):
    ax.axis("off"); ax.set_xlim(-0.2, 10.4); ax.set_ylim(-0.6, 4.4)
    # 平面図: 河道の帯(左→右)と分水路(右上へ)
    ax.add_patch(Polygon([(0, 1.0), (10.2, 0.8), (10.2, 1.9), (0, 2.1)], fc=C_WATER_L, ec=C_WATER, lw=1, zorder=2))
    arrow(ax, (0.6, 1.6), (2.8, 1.55), color=C_WATER, lw=2, text=t["flow"], dxy=(0, -0.4), fs=8)
    arrow(ax, (7.4, 1.45), (9.6, 1.4), color=C_WATER, lw=2)
    # 堰(取水セル直下流)
    ax.plot([4.9, 4.9], [0.9, 2.1], color="k", lw=3, zorder=4)
    # 取水セル群(堰直上流)
    for k in range(3):
        ax.add_patch(Rectangle((3.6 + 0.4 * k, 1.1), 0.4, 0.95, fc=C_B, ec=C_X, lw=0.8, alpha=0.8, zorder=3))
    label(ax, 4.2, 0.45, t["div_in"], color=C_X, fs=8.5)
    # 分水路: 取水セルから上へ
    ax.add_patch(Polygon([(3.9, 2.05), (4.6, 2.05), (4.6, 3.3), (7.4, 3.3), (7.4, 3.9), (3.9, 3.9)], fc=C_WATER_L, ec=C_WATER, lw=1, zorder=2))
    arrow(ax, (4.25, 2.3), (4.25, 3.3), color=C_X, lw=2)
    arrow(ax, (4.9, 3.6), (7.0, 3.6), color=C_X, lw=2)
    ax.plot([7.4, 8.4], [3.6, 3.6], color=C_X, lw=1.4, ls="--", zorder=4)
    arrow(ax, (8.4, 3.6), (9.3, 3.6), color=C_X, lw=1.4, ls="--")
    label(ax, 9.4, 3.95, t["div_outside"], color=C_X, fs=8, ha="right", va="bottom")
    # 送水先セル
    for k in range(2):
        ax.add_patch(Rectangle((8.3 + 0.45 * k, 2.55), 0.45, 0.45, fc=C_WATER_L, ec=C_C, lw=1.0, zorder=3))
    ax.plot([7.4, 8.5], [3.5, 3.0], color=C_C, lw=1.2, ls=":", zorder=4)
    label(ax, 10.3, 2.45, t["div_out"], color=C_C, fs=8, ha="right", va="top")
    label(ax, 10.3, 0.05, t["div_passive"], color=C_P, fs=7.5, ha="right", va="center")
    label(ax, 0.1, 4.25, t["div_q"], color=C_X, fs=8, ha="left", va="top")
    ax.set_title(t["c"], loc="left", fontsize=9)


def panel_dam(ax, t):
    ax.axis("off"); ax.set_xlim(-0.2, 10.9); ax.set_ylim(-1.0, 4.6)
    # 地盤: 湖盆(左)→堤体→下流河道(右)
    gx = [0, 0.8, 1.6, 3.4, 4.6, 5.2, 5.2, 6.1, 6.1, 10.7]
    gz = [2.6, 2.0, 1.0, 0.5, 0.5, 0.5, 0.5, 0.2, 0.2, 0.0]
    ax.add_patch(Polygon(list(zip(gx, gz)) + [(10.7, -1.0), (0, -1.0)], fc=C_GROUND_L, ec=C_GROUND, lw=1, zorder=1))
    # 堤体
    ax.add_patch(Polygon([(5.0, 0.5), (5.3, 3.4), (5.7, 3.4), (6.5, 0.2)], fc=C_GROUND, ec="k", lw=0.8, zorder=3))
    label(ax, 5.55, 1.6, t["dam"], color="white", fs=7.5, rotation=90)
    # 湖水 H
    H, Hsur, Hmin = 2.2, 2.9, 1.0
    water(ax, [0.5, 0.8, 1.6, 3.4, 5.1], [2.2, 2.0, 1.0, 0.5, 0.5], [H] * 5)
    ax.plot([0.5, 5.1], [H, H], color=C_WATER, lw=1.2, zorder=3)
    ax.plot([0.0, 5.25], [Hsur, Hsur], color=C_X, lw=1, ls="--", zorder=3)
    ax.plot([1.6, 5.1], [Hmin, Hmin], color=C_P, lw=1, ls="--", zorder=3)
    label(ax, 0.1, Hsur + 0.07, t["hsur"], color=C_X, fs=7.5, ha="left", va="bottom")
    label(ax, 0.1, Hsur - 0.09, t["tadashigaki"], color=C_X, fs=7.5, ha="left", va="top")
    label(ax, 1.75, Hmin - 0.08, t["hmin"], color=C_P, fs=7.5, ha="left", va="top")
    label(ax, 2.9, H + 0.07, t["H"], color=C_C, fs=8, ha="center", va="bottom")
    label(ax, 1.2, 1.6, t["V"], color=C_C, fs=7.5, ha="left", va="center")
    # 湖面セル(捕捉集合)を上端に並べる
    for k in range(9):
        ax.add_patch(Rectangle((0.5 + 0.5 * k, 3.3), 0.5, 0.3, fc=C_B, ec=C_X, lw=0.7, alpha=0.85, zorder=4))
    label(ax, 0.0, 4.5, t["lake_cells"], color=C_X, fs=8, ha="left", va="top")
    arrow(ax, (2.0, 4.15), (2.0, 3.65), color=C_X, lw=1.4)
    label(ax, 3.9, 3.95, t["capture"], color=C_X, fs=7.5, ha="center", va="center")
    # 放流
    ax.plot([5.0, 6.5], [1.1, 1.1], color=C_C, lw=2.4, zorder=4)
    arrow(ax, (6.5, 1.1), (7.6, 0.6), color=C_C, lw=2.4)
    water(ax, [7.0, 10.7], [0.15, 0.0], [0.55, 0.45])
    ax.add_patch(Rectangle((7.1, 0.0), 0.5, 0.55, fc="none", ec=C_C, lw=1.2, zorder=4))
    label(ax, 6.15, 2.95, t["release"], color=C_C, fs=7.5, ha="left", va="center")
    # dam_lake: 別の放流工(点線)
    ax.plot([4.8, 9.9], [1.6, 1.6], color=C_G, lw=1.6, ls="--", zorder=4)
    arrow(ax, (9.9, 1.6), (9.9, 0.6), color=C_G, lw=1.6, ls="--")
    label(ax, 10.75, 1.72, t["lake"], color="#3f7a2a", fs=7.2, ha="right", va="bottom")
    # dam_gw: 地下水頭
    arrow(ax, (3.9, 0.45), (3.9, -0.05), color=C_P, lw=1.4, ls=":")
    arrow(ax, (4.3, -0.05), (4.3, 0.45), color=C_P, lw=1.4, ls=":")
    label(ax, 0.0, -0.1, t["gw"], color=C_P, fs=7.5, ha="left", va="top")
    label(ax, 0.0, -0.62, t["noout"], color=C_P, fs=7.5, ha="left", va="top")
    ax.set_title(t["d"], loc="left", fontsize=9)


def draw(lang):
    t = T[lang]
    fig, axs = plt.subplots(2, 2, figsize=(10.5, 8.0), layout="constrained")
    panel_pump(axs[0, 0], t); panel_culvert(axs[0, 1], t)
    panel_diversion(axs[1, 0], t); panel_dam(axs[1, 1], t)
    return save(fig, "structure_types", lang)
