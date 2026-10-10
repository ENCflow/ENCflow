"""潮位の章の図: 潮位時系列(tival)と、海セルの見かけ水柱厚 hsea0・上げ潮の浸水・干潮の排水の断面。"""
from _style import *
import numpy as np

T = {"ja": {
    "a": "(a) 潮位の時系列(titype = 2: tival)",
    "b": "(b) 上げ潮・高潮(時刻 A): η が陸の地盤より高い → 陸側の浸水を浅水計算で解く",
    "c": "(c) 干潮(時刻 B): η が下がり、陸側の滞留水が海へ抜ける",
    "xlabel": "時刻 (min)", "ylabel": "潮位 η (m)",
    "sea": "海セル(fn_sw = 1)\n潮位 η(t) を水位として強制\n流れは解かない",
    "interp": "線形補間。範囲外は端値保持\n更新間隔 dt_tiupdate",
    "hsea0": "見かけ水柱厚 hsea0\n(乾燥判定・エッジ水深・\n摩擦を賄う。標準 1 m、\ndd の数十倍以上)",
    "land": "陸セル(通常の浅水計算)",
    "flood": "浸水", "drain": "排水",
    "datum": "標高基準 0(z と同じ)",
    "pond": "滞留水",
}, "en": {
    "a": "(a) tide-level time series (titype = 2: tival)",
    "b": "(b) rising tide / surge (time A): η above the land -> flooding on land is solved",
    "c": "(c) low tide (time B): η drops and ponded water on land drains to the sea",
    "xlabel": "time (min)", "ylabel": "tide level η (m)",
    "sea": "sea cells (fn_sw = 1)\nη(t) forced as the water level\nno flow is solved",
    "interp": "linear interpolation, end values\nheld outside; update dt_tiupdate",
    "hsea0": "apparent water column hsea0\n(serves the dry test, edge depth\nand friction; typically 1 m,\nseveral tens of dd or more)",
    "land": "land cells (ordinary shallow-water computation)",
    "flood": "flooding", "drain": "drainage",
    "datum": "elevation datum 0 (same as z)",
    "pond": "ponded water",
}}

TIV = [(0, 0.0), (180, 0.8), (360, 0.0), (540, -0.8)]
TA, TB = 180, 540
HSEA = 1.0
NSEA = 4
XL = np.linspace(NSEA, 12, 300)


def land_z(x):
    # 海岸で 0.3 まで上がり、内陸に浅い低地(0.1)をもつ地盤
    return 0.3 + 0.25 * np.exp(-((x - 5.0) / 0.5) ** 2) - 0.2 * np.exp(-((x - 8.5) / 1.6) ** 2) + 0.06 * np.maximum(x - 10.5, 0) ** 2


def section(ax, t, eta, title, mode):
    ax.axis("off")
    z = land_z(XL)
    ax.fill_between(XL, -2.2, z, color=C_GROUND_L, zorder=1)
    ax.plot(XL, z, color=C_GROUND, lw=1.4, zorder=2)
    # 海セル: 上面 η、厚さ hsea0
    for i in range(NSEA):
        ax.add_patch(Rectangle((i, eta - HSEA), 1, HSEA, fc=C_SEA, ec="white", lw=0.8, alpha=0.85, zorder=2))
    ax.add_patch(Rectangle((0, -2.2), NSEA, eta - HSEA + 2.2, fc="#d9d8d3", ec="none", zorder=1, hatch="..", alpha=0.6))
    ax.plot([0, NSEA], [eta, eta], color=C_WATER, lw=1.6, zorder=3)
    ax.plot([-0.4, 12], [0, 0], color=C_P, lw=0.6, ls=":", zorder=1.5)
    ax.text(11.9, 0.03, t["datum"], fontsize=7.5, color=C_P, ha="right", va="bottom")
    ax.text(NSEA / 2, eta + 0.08, "η(t)", color=C_WATER, fontsize=9, ha="center", va="bottom", zorder=4)
    if mode == "flood":
        # 陸へ浸水: 海岸〜低地に η までの水(低地側は進入途中)
        m = (XL <= 9.4)
        ax.fill_between(XL[m], z[m], np.minimum(eta, np.where(XL[m] < 6.0, eta, eta - 0.25 * (XL[m] - 6.0))), where=z[m] < eta, color=C_WATER_L, zorder=1.5)
        arrow(ax, (4.6, eta + 0.25), (7.2, eta + 0.05), C_X, text=t["flood"], lw=2.0, dxy=(0, 0.3), fs=9)
        # hsea0 の寸法線
        ax.annotate("", (NSEA + 0.0 - 0.25, eta), (NSEA - 0.25, eta - HSEA), arrowprops=dict(arrowstyle="<->", color="k", lw=0.9))
        ax.text(NSEA + 0.0 - 0.45, eta - HSEA / 2, "hsea0", fontsize=9, color="k", ha="right", va="center")
        ax.text(0.15, eta - HSEA - 0.12, t["sea"], fontsize=8.5, color=C_WATER, ha="left", va="top", zorder=5,
                bbox=dict(fc="white", ec="none", alpha=0.8, pad=1.5))
        ax.text(6.3, -1.0, t["hsea0"], fontsize=8.5, color="k", ha="left", va="top")
        ax.text(12.0, -0.45, t["land"], fontsize=8.5, color=C_GROUND, ha="right", va="center")
    else:
        # 低地に滞留水、海へ排水
        m = (XL >= 6.3) & (XL <= 10.8)
        lvl = 0.26
        ax.fill_between(XL[m], z[m], lvl, where=z[m] < lvl, color=C_WATER_L, zorder=1.5)
        ax.text(8.5, lvl + 0.08, t["pond"], fontsize=8.5, color=C_WATER, ha="center", va="bottom")
        ax.fill_between(XL[XL <= 6.3], z[XL <= 6.3], z[XL <= 6.3] + 0.05, color=C_WATER_L, zorder=1.5)
        arrow(ax, (6.0, 0.55), (3.6, 0.0), C_G, text=t["drain"], lw=2.0, dxy=(0.9, 0.55), fs=9)
    ax.set_xlim(-0.4, 12.2); ax.set_ylim(-2.25, 1.75)
    ax.set_title(title, loc="left", fontsize=9.5)


def draw(lang):
    t = T[lang]
    fig = plt.figure(figsize=(10.5, 6.2), layout="constrained")
    gs = fig.add_gridspec(2, 2, width_ratios=[0.9, 1.5])
    # (a) 時系列
    ax = fig.add_subplot(gs[:, 0])
    tt = [p[0] for p in TIV]; ee = [p[1] for p in TIV]
    ax.plot(tt + [660], ee + [ee[-1]], color=C_WATER, lw=2.0)
    ax.plot(tt, ee, "o", color=C_WATER, ms=6)
    for (tm, lab, c) in [(TA, "A", C_X), (TB, "B", C_G)]:
        ax.axvline(tm, color=c, lw=1.2, ls="--")
        ax.text(tm, 1.02, lab, color=c, fontsize=10, ha="center", va="bottom", fontweight="bold")
    for (tm, e) in TIV:
        ax.text(tm + 8, e + (0.07 if e >= 0 else -0.07), f"({tm}, {e:+.1f})".replace("+0.0", "0.0"), fontsize=7.5, color=C_P,
                ha="left", va="bottom" if e >= 0 else "top")
    ax.axhline(0, color=C_P, lw=0.6, ls=":")
    ax.text(330, -1.05, t["interp"], fontsize=8, color=C_P, ha="center", va="bottom")
    ax.set_xlim(0, 680); ax.set_ylim(-1.15, 1.15)
    ax.set_xlabel(t["xlabel"]); ax.set_ylabel(t["ylabel"])
    ax.set_title(t["a"], loc="left", fontsize=9.5)
    # (b)(c) 断面
    section(fig.add_subplot(gs[0, 1]), t, 0.8, t["b"], "flood")
    section(fig.add_subplot(gs[1, 1]), t, -0.8, t["c"], "drain")
    return save(fig, "tide_section", lang)
