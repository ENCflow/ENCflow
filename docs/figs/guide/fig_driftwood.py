"""流木(docs/users_guide/driftwood.md)の説明図: 3 つの台帳(立木 wst → 流動 hd → 堆積 wd)を断面に配置。

  driftwood_ledgers.png  発生 (a)(b)・移流・停止・再流動と喫水の決め方
データ不要の模式図(matplotlib のみ)。
"""
import numpy as np
from _style import *

T = {
    "ja": dict(
        title="流木の 3 つの台帳(柱状材積 m³/m² のラスタ場。閉領域なら wst + hd + wd の総和が保存)",
        stock="立木ストック wst(不動)\ndw_stock0 / fn_dwstock",
        rec_a="(a) 水理的流失\nh > dw_hrec かつ V > dw_vrec\n→ レート dw_wrec で hd へ",
        rec_b="(b) 侵食連行\n累積侵食深 > dw_droot → 全量 hd へ\n(geomorph の侵食と自動連動)",
        hd="流動流木 hd: 水と同速で移流\n(f_debris 有効時は混合体と同速)",
        flow="流れ V",
        draft="喫水(浮遊限界水深)= 円柱の浮力平衡\ndw_dlog・dw_sglog から自動導出\n(sg = 0.5 → 半没 = 0.5 × dw_dlog)",
        stop="停止 → 堆積流木 wd\nh < 喫水 または V < dw_vstop → レート dw_wstop\n乾燥セルでは全量が wd へ",
        refloat="再流動 dw_wfloat(既定 0 = 動かない)\nh > dw_rfloat × 喫水 かつ V > dw_vfloat",
        out="出力: Hd = hd、Wd = wd、Wd9999 = 期間最大の max(hd + wd)",
        dry="乾燥セル",
        wl="水面",
    ),
    "en": dict(
        title="The three driftwood ledgers (raster field of wood volume m³/m²; in a closed domain wst + hd + wd is conserved)",
        stock="standing stock wst (immobile)\ndw_stock0 / fn_dwstock",
        rec_a="(a) hydraulic recruitment\nh > dw_hrec and V > dw_vrec\n→ to hd at rate dw_wrec",
        rec_b="(b) erosion entrainment\ncumulative erosion depth > dw_droot → all to hd\n(coupled automatically to geomorph erosion)",
        hd="floating wood hd: advected at the water velocity\n(at the mixture velocity when f_debris is on)",
        flow="flow V",
        draft="draft (buoyant depth) = buoyancy balance of a cylinder\nderived from dw_dlog and dw_sglog\n(sg = 0.5 → half submerged = 0.5 × dw_dlog)",
        stop="stopping → deposited wood wd\nh < draft or V < dw_vstop → rate dw_wstop\nin dry cells everything goes to wd",
        refloat="refloating dw_wfloat (default 0 = stays put)\nh > dw_rfloat × draft and V > dw_vfloat",
        out="output: Hd = hd, Wd = wd, Wd9999 = period maximum of max(hd + wd)",
        dry="dry cell",
        wl="water surface",
    ),
}


def _tree(ax, x, z, h=0.5):
    ax.plot([x, x], [z, z + h], color=C_GROUND, lw=2.0, zorder=6)
    ax.add_patch(Polygon([(x - 0.2, z + h * 0.55), (x + 0.2, z + h * 0.55), (x, z + h + 0.35)], fc=C_G, ec="none", zorder=6))


def _log(ax, x, y, w=0.3, h=0.11, color=C_GROUND, z=6):
    from matplotlib.patches import Ellipse
    ax.add_patch(Ellipse((x, y), w, h, fc=color, ec="#5a4a35", lw=0.6, zorder=z))


def draw(lang):
    t = T[lang]
    fig, ax = plt.subplots(figsize=(10.5, 4.9), layout="constrained")
    ax.axis("off"); ax.set_xlim(-0.1, 10.5); ax.set_ylim(-0.35, 4.55)
    xs = [0, 1.9, 2.8, 5.0, 7.6, 9.0, 10.4]
    zs = [1.0, 1.0, 0.4, 0.4, 1.45, 1.6, 1.7]
    x = np.linspace(0, 10.4, 521)
    z = np.interp(x, xs, zs)
    wl = 1.45
    ax.fill_between(x, -0.35, z, color=C_GROUND_L, lw=0, zorder=1)
    # 侵食前の河岸(破線)と侵食後(実線)
    ax.plot([1.9, 2.8], [1.0, 0.4], color=C_P, lw=1.0, ls="--", zorder=4)
    z[(x > 1.75) & (x < 2.9)] = np.interp(x[(x > 1.75) & (x < 2.9)], [1.75, 2.1, 2.9], [1.0, 0.45, 0.4])
    ax.fill_between(x, -0.35, z, color=C_GROUND_L, lw=0, zorder=1.5)
    ax.plot(x, z, color="k", lw=1.0, zorder=5)
    wet = z < wl
    ax.fill_between(x, z, wl, where=wet, color=C_WATER_L, lw=0, zorder=2)
    ax.plot([0, 7.6], [wl, wl], color=C_WATER, lw=1.2, zorder=4)
    label(ax, 0.1, wl + 0.1, t["wl"], color=C_WATER, fs=8, ha="left", va="bottom")
    # 立木
    for xt in (0.6, 1.05, 1.5):
        _tree(ax, xt, 1.0)
    label(ax, 0.05, 2.35, t["stock"], color="#3f7a2a", fs=8.5, ha="left", va="bottom")
    # (a) 水理的流失
    arrow(ax, (1.75, 1.3), (2.95, 1.3), color=C_X, lw=2.0)
    ax.annotate(t["rec_a"], (2.35, 1.36), (1.95, 3.0), fontsize=8.5, color=C_X, ha="left", va="bottom",
                arrowprops=dict(arrowstyle="-", color=C_P, lw=0.7), zorder=8)
    # (b) 侵食連行(河岸の抉れ)
    ax.annotate(t["rec_b"], (2.15, 0.75), (0.1, 0.1), fontsize=8.5, color=C_X, ha="left", va="bottom",
                arrowprops=dict(arrowstyle="-", color=C_P, lw=0.7), zorder=8, bbox=dict(fc="white", ec="none", alpha=0.85))
    # 流動流木と流れ
    for xl in (3.4, 4.3, 5.2, 6.1):
        _log(ax, xl, wl - 0.03)
    arrow(ax, (3.3, 0.95), (4.3, 0.95), color=C_C, lw=1.6, text=t["flow"], dxy=(0, -0.2), fs=8.5)
    arrow(ax, (3.5, wl + 0.2), (6.2, wl + 0.2), color=C_X, lw=1.4)
    label(ax, 4.75, 2.25, t["hd"], color=C_X, fs=8.5)
    # 喫水の説明(円柱断面)
    cx, cy, r = 4.3, 3.65, 0.32
    ax.add_patch(Rectangle((cx - 0.6, cy - 0.55), 1.2, 0.55, fc=C_WATER_L, ec="none", zorder=5))
    ax.plot([cx - 0.6, cx + 0.6], [cy, cy], color=C_WATER, lw=1.2, zorder=6)
    ax.add_patch(Circle((cx, cy), r, fc=C_GROUND, ec="#5a4a35", lw=0.8, zorder=7))
    ax.annotate("", (cx + 0.5, cy - r), (cx + 0.5, cy), arrowprops=dict(arrowstyle="<->", color=C_X, lw=1.0), zorder=8)
    label(ax, cx + 1.0, cy - 0.3, t["draft"], color=C_X, fs=8.5, ha="left", va="bottom")
    # 停止・堆積
    for xl, dz in ((7.15, 0.02), (7.45, 0.0), (8.15, 0.0)):
        _log(ax, xl, np.interp(xl, x, z) + 0.055 + dz)
    arrow(ax, (6.45, wl + 0.2), (7.2, wl + 0.2), color=C_X, lw=1.4)
    label(ax, 6.95, 2.55, t["stop"], color=C_X, fs=8.5, ha="left", va="bottom")
    label(ax, 8.9, np.interp(8.9, x, z) + 0.3, t["dry"], color=C_P, fs=8)
    # 再流動(破線)
    ax.add_patch(FancyArrowPatch((7.35, 1.62), (6.45, 1.75), connectionstyle="arc3,rad=0.4", arrowstyle="-|>",
                                 mutation_scale=12, color=C_G, lw=1.4, ls="--", zorder=6))
    label(ax, 7.95, 0.55, t["refloat"], color="#3f7a2a", fs=8.5, ha="left", box=True)
    label(ax, 3.25, 0.05, t["out"], color="k", fs=8.5, ha="left", box=True)
    ax.set_title(t["title"], loc="left", fontsize=10)
    return save(fig, "driftwood_ledgers", lang)
