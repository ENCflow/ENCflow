"""初期条件の章の図: f_htype(水深 / 水位)と f_fill_depres(窪地の充填)の断面。"""
from _style import *
import numpy as np

T = {"ja": {
    "a": "(a) f_htype = 0 / 1: 水深を与える\n(h0 の固定値 / fn_hinit の分布)",
    "b": "(b) f_htype = 2 / 3: 水位を与える\n(e0 の固定値 / fn_hinit の分布)",
    "c": "(c) f_fill_depres: 窪地(流出先のない凹み)を\n計算前に埋める",
    "a_h": "h = h0(地形に沿った一様な水深)",
    "a_rw": "河道セル(fn_rw)は + h0_rw",
    "b_e": "e0(z と同じ標高基準)",
    "b_h": "h = max(e0 − z, 0)",
    "b_dry": "水面より高い地盤は乾いたまま",
    "c_1": "1: 全域の窪地を水で満たす\n2: 河道セルの窪地だけ",
    "c_3": "3: 2 の充填水を\n地盤高に転換",
    "c_sea": "海へ排水できる窪地は埋めない",
    "z": "地盤高 z",
}, "en": {
    "a": "(a) f_htype = 0 / 1: give a depth\n(fixed h0 / distribution fn_hinit)",
    "b": "(b) f_htype = 2 / 3: give a water level\n(fixed e0 / distribution fn_hinit)",
    "c": "(c) f_fill_depres: fill depressions\n(hollows without outlet) before the run",
    "a_h": "h = h0 (uniform depth on the terrain)",
    "a_rw": "channel cells (fn_rw): + h0_rw",
    "b_e": "e0 (same elevation datum as z)",
    "b_h": "h = max(e0 − z, 0)",
    "b_dry": "ground above the surface stays dry",
    "c_1": "1: fill every depression with water\n2: channel-cell depressions only",
    "c_3": "3: convert the water of 2\ninto ground elevation",
    "c_sea": "hollows that can drain to the sea are not filled",
    "z": "ground z",
}}

X = np.linspace(0, 10, 400)


def terrain(x):
    return 1.0 + 0.55 * np.sin(0.75 * x + 0.6) + 0.25 * np.cos(2.0 * x) + 0.05 * x


def ground(ax, z, t):
    ax.fill_between(X, -0.4, z, color=C_GROUND_L, zorder=1)
    ax.plot(X, z, color=C_GROUND, lw=1.4, zorder=2)
    ax.text(9.8, z[-1] - 0.35, t["z"], ha="right", va="top", fontsize=8.5, color=C_GROUND)


def base(ax, title):
    ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(-0.5, 3.7)
    ax.set_title(title, loc="left", fontsize=10)


def panel_a(ax, t):
    z = terrain(X); h0 = 0.4
    base(ax, t["a"]); ground(ax, z, t)
    ax.fill_between(X, z, z + h0, color=C_WATER_L, zorder=1.5)
    ax.plot(X, z + h0, color=C_WATER, lw=1.4, zorder=3)
    # 河道セル: x = 6.2..7.0 に h0_rw を上乗せ
    m = (X >= 6.2) & (X <= 7.0)
    ax.fill_between(X[m], z[m] + h0, z[m] + h0 + 0.35, color=C_C, alpha=0.55, zorder=2.5)
    ax.plot([6.2, 6.2], [z[m][0] + h0, z[m][0] + h0 + 0.35], color=C_WATER, lw=1); ax.plot([7.0, 7.0], [z[m][-1] + h0, z[m][-1] + h0 + 0.35], color=C_WATER, lw=1)
    ax.annotate(t["a_h"], (2.2, terrain(2.2) + h0), (0.3, 3.4), fontsize=8.5, color=C_WATER, ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color=C_WATER, lw=0.7))
    ax.annotate(t["a_rw"], (6.6, terrain(6.6) + h0 + 0.35), (4.6, 2.95), fontsize=8.5, color=C_WATER, ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color=C_WATER, lw=0.7))


def panel_b(ax, t):
    z = terrain(X); e0 = 1.25
    base(ax, t["b"]); ground(ax, z, t)
    ax.fill_between(X, z, e0, where=z < e0, color=C_WATER_L, zorder=1.5)
    ax.plot([0, 10], [e0, e0], color=C_WATER, lw=1.4, ls="--", zorder=3)
    ax.text(0.2, e0 + 0.08, t["b_e"], fontsize=8.5, color=C_WATER, ha="left", va="bottom",
            bbox=dict(fc="white", ec="none", alpha=0.85, pad=1.5))
    ax.annotate(t["b_h"], (3.3, (terrain(3.3) + e0) / 2), (0.3, 2.9), fontsize=8.5, color=C_WATER, ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color=C_WATER, lw=0.7))
    xs = X[z > e0 + 0.2]
    xd = xs[len(xs) // 2] if len(xs) else 6.5
    ax.annotate(t["b_dry"], (xd, terrain(xd) + 0.03), (3.6, 3.4), fontsize=8.5, color=C_GROUND, ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color=C_GROUND, lw=0.7))


def panel_c(ax, t):
    # 2 つの窪地を持つ地形(右へ下る)
    z = 2.0 - 0.1 * X + 0.45 * np.cos(1.6 * X + 0.4)
    base(ax, t["c"]); ground(ax, z, t)
    def fill_hollow(xa, xb, color, hatch=None, alpha=1.0, zo=1.5):
        m = (X >= xa) & (X <= xb)
        lvl = max(z[m][0], z[m][-1])
        ax.fill_between(X[m], z[m], lvl, where=z[m] < lvl, color=color, hatch=hatch, alpha=alpha, zorder=zo, lw=0)
        return lvl
    # 左の窪地: 水で充填(1, 2)。右の窪地: 地盤で充填(3)
    l1 = fill_hollow(1.2, 4.0, C_WATER_L)
    ax.plot([1.6, 3.65], [l1, l1], color=C_WATER, lw=1.2, zorder=3)
    l2 = fill_hollow(5.2, 8.0, C_GROUND, hatch="///", alpha=0.45)
    ax.annotate(t["c_1"], (2.6, l1 - 0.1), (0.3, 3.3), fontsize=8.5, color=C_WATER, ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color=C_WATER, lw=0.7))
    ax.annotate(t["c_3"], (6.6, l2 - 0.1), (6.0, 2.75), fontsize=8.5, color=C_GROUND, ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color=C_GROUND, lw=0.7))
    ax.text(9.9, -0.1, t["c_sea"], fontsize=8, color=C_P, ha="right", va="top")


def draw(lang):
    t = T[lang]
    fig, axs = plt.subplots(1, 3, figsize=(10.5, 3.6))
    panel_a(axs[0], t); panel_b(axs[1], t); panel_c(axs[2], t)
    fig.tight_layout(w_pad=0.5)
    return save(fig, "initial_htype", lang)
