"""淡塩2層(鋭利界面)の断面模式図: 地表の塩水層 hss・地下の塩水 zone hgs・海との接続(salt.md)。"""
from _style import *

T = {"ja": {
    "title": "淡塩2層(fn_salt): 合計 h・hg はそのまま、その内数として最下層の塩水層厚 hss・hgs を追跡する(鋭利界面)",
    "sea": "海域セル(sw > 0)\n全塩水・水位 = 潮位(fn_tide)", "land": "陸", "ground": "地表 z",
    "soil": "土層(帯水層: sd, sy0。f_gwlateral=1 が前提)", "fresh": "淡水(hg − hgs)", "saltgw": "地下の塩水 zone hgs(f_salt_gw=1)",
    "iface": "界面標高 ζ", "phi": "駆動水頭: 淡水 Φf = η、塩水 Φs = η + ε·ζ\nε = (salt_rhos − salt_rhof)/salt_rhof(既定 1025/1000 → 2.5 %)",
    "gh": "平衡界面は Ghyben-Herzberg 関係",
    "surf": "地表水 h", "hss": "地表の塩水層 hss(f_salt_surf=1)\n移流に相乗り(分担率 salt_alpha)+ 底層重力流(salt_ni)",
    "ex_gw": "塩水: 水頭差で双方向交換\n淡水: 海へ流出のみ",
    "ex_surf": "遡上した海水は塩水として追跡\n(海へ戻れば消える)",
    "init": "初期値: salt_hss0 / salt_hgs0(一様値かマップ)。出力 Hss・Hgs",
    "tide": "潮位 η_sea",
}, "en": {
    "title": "Fresh/salt two layers (fn_salt): h and hg stay totals; the salt-layer thicknesses hss, hgs are tracked as their lowest part (sharp interface)",
    "sea": "sea cells (sw > 0)\nall salt, level = tide (fn_tide)", "land": "land", "ground": "ground z",
    "soil": "soil layer (aquifer: sd, sy0; requires f_gwlateral=1)", "fresh": "fresh water (hg − hgs)", "saltgw": "subsurface salt zone hgs (f_salt_gw=1)",
    "iface": "interface elevation ζ", "phi": "driving heads: fresh Φf = η, salt Φs = η + ε·ζ\nε = (salt_rhos − salt_rhof)/salt_rhof (default 1025/1000 -> 2.5 %)",
    "gh": "equilibrium interface: Ghyben-Herzberg relation",
    "surf": "surface water h", "hss": "surface salt layer hss (f_salt_surf=1)\nrides on advection (share salt_alpha) + bottom gravity current (salt_ni)",
    "ex_gw": "salt: two-way exchange by head difference\nfresh: outflow to sea only",
    "ex_surf": "run-up seawater is tracked as salt\n(vanishes when it returns to sea)",
    "init": "initial: salt_hss0 / salt_hgs0 (uniform or map). Output Hss, Hgs",
    "tide": "tide η_sea",
}}


def draw(lang):
    t = T[lang]
    fig, ax = plt.subplots(figsize=(10.5, 5.4), layout="constrained")
    ax.axis("off"); ax.set_xlim(-0.2, 11.6); ax.set_ylim(-1.0, 5.6)
    XS = 7.6                               # 海岸線
    # 地表: 左高 → 海岸で潮位、海底
    gx = [0, 2.0, 4.5, 6.5, XS, 9.0, 11.6]
    gz = [2.9, 2.75, 2.45, 2.15, 2.0, 1.55, 1.4]
    SD = 2.0
    tide = 2.0
    # 土層(帯水層)
    ax.add_patch(Polygon(list(zip(gx, gz)) + [(x, z - SD) for x, z in zip(gx[::-1], gz[::-1])], fc=C_SOIL, ec=C_GROUND, lw=0.8, alpha=0.7, zorder=1))
    ax.add_patch(Polygon([(x, z - SD) for x, z in zip(gx, gz)] + [(11.6, -1.0), (0, -1.0)], fc="#d9d8d3", ec="none", hatch="///", zorder=0.5))
    # 地下水面(淡水): 陸で地表近く、海岸で潮位
    wx = [0, 2.0, 4.5, 6.5, XS]
    wz = [2.65, 2.55, 2.35, 2.12, tide]
    bot = [z - SD for z in [2.9, 2.75, 2.45, 2.15, 2.0]]
    # 塩水 zone: くさび(海側で厚く、陸側で尖る)
    zeta = [bot[0], bot[1], bot[2] + 0.25, bot[3] + 0.95, tide - 0.0]
    ax.add_patch(Polygon(list(zip(wx, wz)) + list(zip(wx[::-1], bot[::-1])), fc=C_WATER_L, ec=C_WATER, lw=0.8, zorder=2))
    ax.add_patch(Polygon(list(zip(wx, zeta)) + list(zip(wx[::-1], bot[::-1])), fc=C_SEA, ec=C_WATER, lw=0.8, alpha=0.7, zorder=2.5))
    ax.plot(wx, zeta, color="#1c4f8a", lw=1.6, zorder=3)
    # 海(右): 全塩水・潮位
    ax.add_patch(Polygon([(XS, tide), (11.6, tide), (11.6, 1.4), (9.0, 1.55), (XS, 2.0)], fc=C_SEA, ec=C_WATER, lw=0.8, alpha=0.7, zorder=2.5))
    ax.add_patch(Polygon([(XS, 2.0), (9.0, 1.55), (11.6, 1.4), (11.6, 1.4 - SD), (9.0, 1.55 - SD), (XS, 0.0)], fc=C_SEA, ec="none", alpha=0.5, zorder=2.6))
    ax.plot([XS - 0.3, 11.6], [tide, tide], color=C_C, lw=1.2, ls="--", zorder=4)
    label(ax, 11.5, tide + 0.1, t["tide"], color=C_C, fs=8, ha="right", va="bottom")
    label(ax, 9.6, 3.1, t["sea"], color=C_C, fs=8.5)
    label(ax, 9.6, 0.5, "hgs = hg", color="white", fs=8)
    # 地表水(陸側のくぼみ): 合計 h に底層 hss
    px = [0.8, 1.2, 3.0, 3.6]
    ax.add_patch(Polygon([(0.8, 3.3), (1.2, 2.82), (3.0, 2.7), (3.6, 3.3)], fc=C_WATER_L, ec=C_WATER, lw=0.8, zorder=2))
    ax.add_patch(Polygon([(1.08, 2.97), (1.2, 2.82), (3.0, 2.7), (3.36, 3.06)], fc=C_SEA, ec="none", alpha=0.75, zorder=2.5))
    ax.plot([0.8, 3.6], [3.3, 3.3], color=C_C, lw=1, zorder=3)
    label(ax, 2.2, 3.5, t["surf"], color=C_C, fs=8.5, va="bottom")
    label(ax, 0.0, 4.55, t["hss"], color="#1c4f8a", fs=8, ha="left", va="center")
    ax.plot([2.2, 2.2], [2.88, 4.25], color="#1c4f8a", lw=0.7, ls=":", zorder=5)
    # ラベル(地下)
    label(ax, 3.0, 2.0, t["fresh"], color=C_C, fs=8.5)
    label(ax, 6.6, 0.6, t["saltgw"], color="white", fs=8, ha="right")
    label(ax, 5.3, 1.45, t["iface"], color="#1c4f8a", fs=8.5, ha="right")
    label(ax, 0.1, 1.3, t["soil"], color="#6b4f1d", fs=8, ha="left")
    label(ax, 0.0, -0.7, t["phi"], color="k", fs=8, ha="left", va="center", box=True)
    label(ax, 11.5, -0.6, t["gh"], color=C_P, fs=8, ha="right", va="center", box=True)
    # 海との交換(地下)
    arrow(ax, (XS + 0.1, 0.9), (XS - 0.9, 0.9), color=C_X, lw=2.0)
    arrow(ax, (XS - 0.9, 0.6), (XS + 0.1, 0.6), color=C_X, lw=2.0)
    arrow(ax, (XS - 0.9, 1.75), (XS + 0.1, 1.75), color=C_C, lw=2.0)
    label(ax, XS + 0.35, 0.95, t["ex_gw"], color=C_X, fs=7.8, ha="left", va="center", box=True)
    # 海との交換(地表): 遡上
    arrow(ax, (XS + 0.4, 2.35), (5.2, 2.6), color=C_X, lw=1.8, ls="--")
    label(ax, 7.3, 4.1, t["ex_surf"], color=C_X, fs=7.8, ha="center", va="center")
    ax.plot([6.6, 7.0], [2.5, 3.75], color=C_X, lw=0.7, ls=":", zorder=5)
    label(ax, 11.5, 5.4, t["init"], color=C_P, fs=7.8, ha="right", va="top")
    ax.set_title(t["title"], loc="left", fontsize=9.2)
    return save(fig, "salt_layers", lang)
