#!/usr/bin/env python3
"""landslide_tsunami の説明図(計算結果を使わない。入力 z.txt・slide.txt・submarine.txt と式だけ)。

  figs/setup.png      共通の幾何: 平面(地形・崩壊体・境界・プローブ)と中央の行の縦断
  figs/mechanism.png  4 つのパターン(A・B・B0・C)の仕組みの模式図
  figs/properties.png 知っておくべき性質(崩壊面の形、汀線の一時的な離水と bs_tstop、
                      引き渡しの判定、偏りの向き)の模式図
  figs/nh_theory.png  1 層非静水圧の分散関係と、底面変位を水面へ写すフィルタ(線形解析の式)
引数 en で英語ラベル版を en/figs/ に描く(形・値・描画処理は共通で、ラベルだけが切り替わる)。
模式図の形と水面の変位は説明用(水面は誇張)で、計算結果ではない。
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, FancyBboxPatch, FancyArrowPatch

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)

DX, NX, NY, J = 5.0, 120, 40, 19        # 格子幅、列数、行数、中央の行(0 始まり。北端から 97.5 m)
ST, XSHORE, ZBOT, STF = 0.4, 200.0, -40.0, 0.25
G, H = 9.8, 40.0                        # 重力、湖の水深
PROBES = [(1, 187.5, 97.5), (2, 212.5, 97.5), (3, 297.5, 97.5), (4, 397.5, 97.5), (5, 547.5, 97.5),
          (6, 397.5, 27.5)]             # 番号、x、北端からの距離(param の pbxy)
X = (np.arange(NX) + 0.5) * DX
C_SOIL, C_ROCK, C_WATER, C_EDGE = "#dfc58e", "#cfc9bd", "#d7eaf5", "#287ca5"
C_MOVE, C_DEP, C_MIX, C_SUB = "#da9760", "#b98d5f", "#a9784e", "#7d9a6b"
C_INK, C_MUTED, C_ORANGE, C_BLUE, C_GREEN = "#1f1f1f", "#6f6f6f", "#eb6834", "#287ca5", "#52744b"


def load(name):
    return np.loadtxt(name)


def zline(x):
    return np.maximum(ST * (XSHORE - x), ZBOT)


def depth_line(x, x0, x1, dmax=12.0):
    d = np.where((x >= x0) & (x <= x1), np.minimum(dmax, (ST - STF) * (x1 - x)), 0.0)
    return np.maximum(d, 0.0)


def profile_axes(ax, zmin=-46, zmax=86, xmax=600):
    ax.set_xlim(0, xmax)
    ax.set_ylim(zmin, zmax)
    ax.set_aspect("equal")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(labelsize=8)


def ground(ax, x, z, base=-46, face=C_SOIL):
    ax.fill_between(x, z, base, color=face, lw=0, zorder=1)
    ax.plot(x, z, color=C_INK, lw=1.0, zorder=5)


def lake(ax, x, z, level=0.0, surf=None):
    s = np.full_like(x, level) if surf is None else surf
    wet = z < s
    ax.fill_between(x, z, s, where=wet, color=C_WATER, lw=0, zorder=2, interpolate=True)
    xs = np.where(wet, x, np.nan)
    ax.plot(xs, np.where(wet, s, np.nan), color=C_EDGE, lw=1.1, zorder=6)


def body(ax, x, ztop, d, face, z=3, alpha=1.0, edge=None, ls="-"):
    m = d > 0
    if not m.any():
        return
    xs, zt, zb = x[m], ztop[m], ztop[m] - d[m]
    pts = np.vstack([np.c_[xs, zt], np.c_[xs[::-1], zb[::-1]]])
    ax.add_patch(Polygon(pts, closed=True, facecolor=face, edgecolor=edge or "none", lw=1.0, ls=ls,
                         alpha=alpha, zorder=z))


def lens(ax, x, xa, xb, th, face, z=4, alpha=1.0, edge="none"):
    """A layer of thickness th*sin(pi s)^0.6 lying on the bed between xa and xb."""
    m = (x >= xa) & (x <= xb)
    s = (x[m] - xa) / (xb - xa)
    t = th * np.sin(np.pi * s) ** 0.6
    zb = zline(x[m])
    pts = np.vstack([np.c_[x[m], zb + t], np.c_[x[m][::-1], zb[::-1]]])
    ax.add_patch(Polygon(pts, closed=True, facecolor=face, edgecolor=edge, lw=0.8, alpha=alpha, zorder=z))


def arrow(ax, p0, p1, color=C_INK, lw=1.4, ms=10, z=8):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=ms, color=color, lw=lw, zorder=z))


def note(ax, x, y, s, size=8, color=C_INK, ha="left", va="top", **kw):
    return ax.text(x, y, s, fontsize=size, color=color, ha=ha, va=va, zorder=20, linespacing=1.4, **kw)


# ----------------------------------------------------------------------------------------------
def setup():
    z = load("z.txt")
    d_land, d_sub = load("slide.txt"), load("submarine.txt")
    fig = plt.figure(figsize=(12.6, 7.6))
    gs = fig.add_gridspec(2, 1, height_ratios=[1.0, 1.05], hspace=0.32, left=0.07, right=0.97, top=0.93, bottom=0.07)
    # (a) plan, north up; the vertical axis is the distance from the north edge (row 1 = north).
    ax = fig.add_subplot(gs[0])
    ax.set_anchor("W")
    ext = [0, NX * DX, NY * DX, 0]
    land = np.ma.masked_where(z < 0, z)
    water = np.ma.masked_where(z >= 0, -z)
    ax.imshow(land, extent=ext, origin="upper", cmap="YlOrBr", vmin=-60, vmax=260, interpolation="nearest")
    ax.imshow(water, extent=ext, origin="upper", cmap="Blues", vmin=-20, vmax=110, interpolation="nearest")
    yy = (np.arange(NY) + 0.5) * DX
    ax.contour(X, yy, z, levels=np.arange(-30, 81, 10), colors="#7a6a50", linewidths=0.5, linestyles="solid")
    ax.contour(X, yy, z, levels=[0], colors=C_EDGE, linewidths=1.6)
    ax.contour(X, yy, d_land, levels=[0.01], colors=C_ORANGE, linewidths=1.6)
    ax.contour(X, yy, d_sub, levels=[0.01], colors=C_GREEN, linewidths=1.6)
    ax.contourf(X, yy, np.where(d_land > 0.01, 1, np.nan), levels=[0.5, 1.5], colors="none", hatches=["////"])
    ax.contourf(X, yy, np.where(d_sub > 0.01, 1, np.nan), levels=[0.5, 1.5], colors="none", hatches=["\\\\\\\\"])
    ax.axvline(300, color=C_INK, lw=0.8, ls="--")
    ax.axhline(97.5, color=C_INK, lw=0.8, ls=":")
    for n, px, py in PROBES:
        ax.plot(px, py, marker="^", color=C_INK, ms=6, zorder=10)
        ax.text(px + 4, py - 5, str(n), fontsize=8, color=C_INK, zorder=10)
    note(ax, 75, 62, T("陸上の崩壊体(A・B)", "land block (A, B)"), color=C_ORANGE, ha="center", va="bottom", size=8.5)
    note(ax, 255, 62, T("水中の崩壊体(C)", "underwater block (C)"), color=C_GREEN, ha="center", va="bottom", size=8.5)
    note(ax, 203, 192, T("汀線 x = 200 m", "shoreline x = 200 m"), color=C_EDGE, size=8, va="bottom")
    note(ax, 303, 192, T("湖底の平坦部 x ≥ 300 m(z = −40 m)", "flat lake floor x ≥ 300 m (z = −40 m)"), size=8, va="bottom")
    note(ax, 470, 94, T("中央の行(縦断の位置)", "centre row (profile below)"), size=8, ha="center", va="bottom")
    ax.set_xlabel("x (m)", fontsize=9)
    ax.set_ylabel(T("北端からの距離 (m)", "distance from the north edge (m)"), fontsize=9)
    ax.set_title(T("(a) 平面: 地形(10 m ごとの等高線)、崩壊体、プローブ 1〜6(▲)。上が北",
                   "(a) Plan: terrain (10 m contours), release blocks, probes 1–6 (▲); north up"), fontsize=10, loc="left")
    ax.tick_params(labelsize=8)
    fig.text(0.745, 0.905, T("境界\n西辺: 壁(山側)\n東・北・南辺: 長波放射\n\n"
                             "プローブ(▲)\n1 汀線の手前の陸(x = 187.5 m)\n2 汀線のすぐ沖(212.5 m)\n"
                             "3 斜面の下端(297.5 m)\n4 湖央(397.5 m)\n5 対岸側(547.5 m)\n"
                             "6 北寄りの湖央(397.5 m、北端から 27.5 m)\n\n"
                             "崩壊体の斜線: 崩壊深 > 0 の範囲",
                             "Boundaries\nwest: wall (mountain side)\neast, north, south: long-wave radiation\n\n"
                             "Probes (▲)\n1 land above the shoreline (x = 187.5 m)\n2 just offshore (212.5 m)\n"
                             "3 foot of the slope (297.5 m)\n4 lake centre (397.5 m)\n5 far side (547.5 m)\n"
                             "6 lake centre near the north edge\n   (397.5 m; 27.5 m from the edge)\n\n"
                             "hatching: where the release depth > 0"),
             fontsize=8.2, va="top", ha="left", linespacing=1.45)
    # (b) centre-row profile with the two blocks.
    ax = fig.add_subplot(gs[1])
    profile_axes(ax, zmin=-46, zmax=86)
    zc = z[J]
    xs = np.r_[0.0, X, 600.0]
    zs = np.r_[zc[0] + ST * DX / 2, zc, zc[-1]]
    ground(ax, xs, zs)
    lake(ax, xs, zs)
    dl, dsu = d_land[J], d_sub[J]
    body(ax, X, zc, dl, C_MOVE, edge=C_ORANGE)
    body(ax, X, zc, dsu, C_SUB, edge=C_GREEN, alpha=0.9)
    xx = np.linspace(40, 110, 50)
    ax.plot(xx, zline(xx) - depth_line(xx, 40, 110), color=C_ORANGE, lw=1.0, ls="--", zorder=6)
    for n, px, py in PROBES[:5]:
        zt = max(zline(px), -40)
        ax.plot([px, px], [zt, 6], color=C_MUTED, lw=0.8, zorder=4)
        ax.text(px, 7, str(n), fontsize=8, ha="center", va="bottom", color=C_INK)
    note(ax, 8, 30, T("斜面 tan θ = 0.4", "slope tan θ = 0.4"), size=8.5)
    note(ax, 112, 66, T("崩壊体(A・B): すべり面の勾配 0.25 の平面で、下端で地表に抜ける\n"
                        "崩壊深は上端のセルで約 10 m(10.1 m)、体積 19,110 m³(C の崩壊体も同じ形)",
                        "block (A, B): planar slip surface of gradient 0.25 that daylights at its lower end;\n"
                        "release depth about 10 m (10.1 m) in the uppermost cells, volume 19,110 m³ (the C block has the same shape)"),
         size=8.2, color=C_ORANGE)
    note(ax, 318, -3, T("静水面 e0 = 0(初期水位 f_htype = 2。海域マスクは使わない)",
                        "still water e0 = 0 (initial level f_htype = 2; no sea mask)"), size=8, color=C_EDGE)
    note(ax, 262, -11, T("水中も同じ勾配", "same slope under water"), size=8)
    note(ax, 590, -33, T("湖底 z = −40 m", "lake floor z = −40 m"), size=8, ha="right")
    note(ax, 196, -30, T("崩壊体(C)", "block (C)"), size=8.2, color=C_GREEN)
    ax.set_xlabel("x (m)", fontsize=9)
    ax.set_ylabel(T("標高 (m)", "elevation (m)"), fontsize=9)
    ax.set_title(T("(b) 中央の行の縦断(縦横比 1:1)。縦線はプローブ 1〜5",
                   "(b) Profile along the centre row (true scale); vertical lines are probes 1–5"), fontsize=10, loc="left")
    fig.savefig(f"{FIGDIR}/setup.png", dpi=110)
    plt.close(fig)


# ----------------------------------------------------------------------------------------------
def wave_surface(x, centre, amp, width):
    return amp * np.exp(-((x - centre) / width) ** 2)


def mechanism():
    x = np.linspace(0, 600, 1201)
    zb = zline(x)
    fig, axes = plt.subplots(4, 1, figsize=(12.6, 13.2))
    fig.subplots_adjust(left=0.05, right=0.98, top=0.95, bottom=0.03, hspace=0.32)
    fig.suptitle(T("4 つのパターンの仕組み(模式。水面の変位は約 5 倍に誇張)",
                   "How the four patterns work (schematic; the water-surface displacement is exaggerated about five times)"),
                 fontsize=11, x=0.05, ha="left")
    rows = [
        ("A", T("A 岩屑なだれ: 底層だけで陸上から水中まで(param_rockslide.txt)",
                "A Debris avalanche: bed layer only, from land into the water (param_rockslide.txt)")),
        ("B", T("B 土石流 → 滞水域で底層へ引き渡し(param_debrisflow.txt)",
                "B Debris flow → handed over to the bed layer in the ponded zone (param_debrisflow.txt)")),
        ("B0", T("B0 混合体のまま(B の対照。param_mixture_only.txt)",
                 "B0 Mixture only (control of B; param_mixture_only.txt)")),
        ("C", T("C 海底地滑り(param_submarine.txt)", "C Submarine landslide (param_submarine.txt)")),
    ]
    for ax, (key, title) in zip(axes, rows):
        profile_axes(ax, zmin=-46, zmax=86)
        ax.set_title(title, fontsize=10, loc="left")
        ax.set_xlabel("x (m)", fontsize=8)
        if key == "A":
            surf = wave_surface(x, 262, 7.0, 28) - wave_surface(x, 215, 3.5, 14)
            ground(ax, x, zb)
            lake(ax, x, zb, surf=np.where(zb < 0, surf, 0))
            body(ax, x, zb, depth_line(x, 40, 110), "none", edge=C_ORANGE, ls="--", z=6)
            lens(ax, x, 225, 285, 9, C_MOVE)
            lens(ax, x, 288, 345, 6, C_DEP)
            arrow(ax, (70, 52), (150, 20))
            arrow(ax, (238, -2), (282, -26))
            note(ax, 25, 80, T("t = 1 s に崩壊体を底層 hb として可動化(fn_bsinit)",
                               "the block is mobilized as the bed layer hb at t = 1 s (fn_bsinit)"), size=8.2)
            note(ax, 300, 80, T("・慣性なしの Voellmy 流: 速さは駆動水頭 Φ = z + r h の勾配で決まる(r = ρw/ρs = 0.5)\n"
                                "・水中では駆動が (1 − r)∇z に下がり、浮力で摩擦も下がる\n"
                                "・底層が動いた分 z が上下し、h を保つので水面が動く → 波(移動海底の津波源)\n"
                                "・湖底の平坦部(勾配 0)で止まり、斜面の下端に堆積する",
                                "• inertia-free Voellmy flow: the speed follows the gradient of the driving head\n"
                                "  Φ = z + r h (r = ρw/ρs = 0.5)\n"
                                "• under water the driving drops to (1 − r)∇z and buoyancy lowers the friction too\n"
                                "• the bed layer moves z up and down while h is kept, so the water surface moves → waves\n"
                                "• it stops on the flat lake floor (slope 0) and deposits at the foot of the slope"),
                 size=8.2)
            note(ax, 316, -20, T("堆積", "deposit"), size=8, color=C_DEP)
        elif key == "B":
            surf = wave_surface(x, 268, 5.5, 30) - wave_surface(x, 214, 3.0, 12)
            ground(ax, x, zb)
            lake(ax, x, zb, surf=np.where(zb < 0, surf, 0))
            lens(ax, x, 120, 185, 6, C_MIX)
            lens(ax, x, 196, 215, 2.5, C_MIX, alpha=0.8)
            lens(ax, x, 232, 285, 8, C_MOVE)
            lens(ax, x, 288, 345, 6, C_DEP)
            arrow(ax, (128, 46), (180, 26))
            ax.plot([205, 205], [-2, 14], color=C_ORANGE, lw=1.2, zorder=7)
            ax.plot(205, -2, "o", color=C_ORANGE, ms=4, zorder=8)
            note(ax, 207, 16, T("引き渡し", "handover"), size=8.2, color=C_ORANGE, va="bottom")
            note(ax, 25, 80, T("陸上: 慣性のある混合体 hs(土石流モデル。fn_dbinit で t = 1 s に流動化)",
                               "on land: mixture hs with inertia (debris-flow model; mobilized at t = 1 s by fn_dbinit)"),
                 size=8.2, color=C_MIX)
            note(ax, 300, 62, T("・静水時の水深 ≥ bs_hplunge = 2 m のセルで(f_bsplunge = 1)\n"
                                "・混合体の速さが底層の終端速度以下に落ちてから(f_bsvplunge = 1)\n"
                                "  hs を底層 hb へ移す(かさ体積 hs/(1 − λ)。運動量は失う)\n"
                                "・水中は A と同じ底層で走り、低速が 15 s 続いたセルだけ固定(bs_tstop)",
                                "• in cells whose still-water depth ≥ bs_hplunge = 2 m (f_bsplunge = 1)\n"
                                "• after the mixture has slowed to the terminal velocity of the bed layer (f_bsvplunge = 1)\n"
                                "  hs moves to the bed layer hb (bulk volume hs/(1 − λ); momentum is lost)\n"
                                "• under water it runs as the bed layer of A; cells are fixed only after\n  15 s of low speed (bs_tstop)"),
                 size=8.2)
            note(ax, 40, 16, T("突入の運動量は混合体が\n水柱に渡す",
                               "the mixture passes the\nentry momentum to the water"), size=7.8, color=C_INK)
        elif key == "B0":
            surf = wave_surface(x, 262, 3.5, 30)
            ground(ax, x, zb)
            lake(ax, x, zb, surf=np.where(zb < 0, surf, 0))
            lens(ax, x, 120, 185, 6, C_MIX)
            lens(ax, x, 192, 248, 8, C_MIX)
            arrow(ax, (128, 46), (180, 26))
            note(ax, 25, 80, T("陸上は B と同じ混合体。引き渡しをしない",
                               "on land the same mixture as B; no handover"), size=8.2, color=C_MIX)
            note(ax, 300, 62, T("・水面が平らな水中では、混合体の自由表面の勾配がなくなり駆動を失う\n"
                                "  → 一層の混合体は水中を走らず、汀線から 50 m 以内に積み上がる\n"
                                "・突入直後に水柱が高くなる分の波は出る\n"
                                "・地形の結果(堆積の位置・厚さ)を使うなら B か A",
                                "• under a flat water surface the free surface of the mixture has no gradient, so it loses its driving\n"
                                "  → a single-layer mixture does not run under water and piles up within 50 m of the shoreline\n"
                                "• the wave from the column rising right after entry still appears\n"
                                "• for terrain results (where and how thick the deposit is) use B or A"),
                 size=8.2)
            note(ax, 214, 14, T("汀線に残る", "stays at the shoreline"), size=8, color=C_MIX, va="bottom")
        else:
            surf = -wave_surface(x, 255, 6.0, 26) + wave_surface(x, 318, 6.0, 20)
            ground(ax, x, zb)
            lake(ax, x, zb, surf=np.where(zb < 0, surf, 0))
            dsub = depth_line(x, 220, 290)
            ax.fill_between(x, zb - dsub, zb, where=dsub > 0, color=C_WATER, lw=0, zorder=3)
            body(ax, x, zb, dsub, "none", edge=C_GREEN, ls="--", z=6)
            lens(ax, x, 290, 350, 7, C_SUB, alpha=0.95)
            arrow(ax, (238, -22), (286, -38))
            note(ax, 25, 80, T("水中の崩壊体を t = 1 s に底層として可動化(fn_bsinit = submarine.txt)",
                               "the underwater block is mobilized as the bed layer at t = 1 s (fn_bsinit = submarine.txt)"),
                 size=8.2)
            note(ax, 300, 62, T("・スカー(x 220〜290 m)で底面が下がり、上の水面が下がる → 引き波が先行\n"
                                "・堆積前線で底面が上がり、上の水面が上がる\n"
                                "・水中発火の底層はすぐに終端速度で動くので、近地の波は過大側に偏る",
                                "• the bed drops in the scar (x 220–290 m) and the water above drops → the trough leads\n"
                                "• the bed rises at the deposit front and the water above rises\n"
                                "• a bed layer released under water moves at its terminal velocity at once,\n  so near-field waves lean high"),
                 size=8.2)
            note(ax, 262, -9, T("スカー", "scar"), size=8, color=C_GREEN, ha="center")
    fig.savefig(f"{FIGDIR}/mechanism.png", dpi=100)
    plt.close(fig)


# ----------------------------------------------------------------------------------------------
def flowbox(ax, x, y, w, h, s, face="#f4f3ee", edge=C_MUTED, size=8.2, color=C_INK):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.01,rounding_size=0.015", facecolor=face,
                                edgecolor=edge, lw=0.9, transform=ax.transAxes, zorder=3, clip_on=False))
    ax.text(x + w / 2, y + h / 2, s, fontsize=size, ha="center", va="center", transform=ax.transAxes, color=color,
            zorder=4, linespacing=1.35)


def properties():
    fig = plt.figure(figsize=(12.6, 8.4))
    gs = fig.add_gridspec(2, 2, hspace=0.26, wspace=0.16, left=0.05, right=0.98, top=0.92, bottom=0.04)
    fig.suptitle(T("知っておくべき性質(設定の理由)— 模式。計算結果ではない",
                   "Properties to know (reasons for the settings) — schematic, not computed results"),
                 fontsize=11, x=0.05, ha="left")
    # (a) shape of the failure surface.
    ax = fig.add_subplot(gs[0, 0])
    ax.set_title(T("(a) 崩壊面の形", "(a) Shape of the failure surface"), fontsize=10, loc="left")
    ax.set_xlim(0, 230); ax.set_ylim(-10, 95); ax.set_aspect("equal"); ax.axis("off")
    for k, (x0, kind) in enumerate(((0, "plane"), (120, "box"))):
        xs = np.linspace(x0, x0 + 100, 101)
        zg = 60 - 0.4 * (xs - x0)
        ax.fill_between(xs, zg, -10, color=C_SOIL, lw=0, zorder=1)
        ax.plot(xs, zg, color=C_INK, lw=1.0, zorder=5)
        a, b = x0 + 20, x0 + 70
        m = (xs >= a) & (xs <= b)
        if kind == "plane":
            d = np.minimum(12, 0.15 * (b - xs[m]))
            ax.add_patch(Polygon(np.vstack([np.c_[xs[m], zg[m]], np.c_[xs[m][::-1], (zg[m] - d)[::-1]]]),
                                 facecolor=C_MOVE, edgecolor=C_ORANGE, zorder=3))
            arrow(ax, (x0 + 40, 58), (x0 + 88, 38), color=C_ORANGE)
            note(ax, x0, 92, T("平面すべり(勾配 0.25)が\n下端で地表に抜ける\n→ 土塊が滑り出せる",
                               "planar slip surface (0.25)\ndaylights at its lower end\n→ the mass can slide out"),
                 size=8, color=C_INK)
        else:
            d = np.full(m.sum(), 8.0)
            ax.add_patch(Polygon(np.vstack([np.c_[xs[m], zg[m]], np.c_[xs[m][::-1], (zg[m] - d)[::-1]]]),
                                 facecolor=C_MOVE, edgecolor=C_ORANGE, zorder=3))
            ax.plot([b, b], [zg[m][-1] - 8, zg[m][-1]], color=C_INK, lw=2.0, zorder=6)
            arrow(ax, (x0 + 38, 50), (x0 + 66, 36), color=C_ORANGE)
            ax.plot(x0 + 72, 36, marker="x", color=C_ORANGE, ms=10, mew=2.2, zorder=9)
            note(ax, x0, 92, T("深さ一定の箱型は下流側に壁の\nある穴になり、慣性なしの流れは\n段差を登れず穴に残る(混合体も同じ)",
                               "a constant-depth box is a hole with\na downstream wall; inertia-free flow\ncannot climb the step (nor the mixture)"),
                 size=8, color=C_INK)
    # (b) temporary drying of the shoreline zone and bs_tstop (two stacked schematic series).
    ax = fig.add_subplot(gs[0, 1])
    ax.set_title(T("(b) 突入時の汀線帯の一時的な離水と bs_tstop", "(b) Temporary drying of the shoreline zone and bs_tstop"),
                 fontsize=10, loc="left")
    ax.axis("off")
    t = np.linspace(0, 40, 801)
    dry = np.exp(-((t - 18) / 6.0) ** 8)
    hdep = 2.0 - 1.9 * dry
    vb = np.where(t < 5, 0, 3.0 * (1 - np.exp(-(t - 5) / 1.2))) * (1 - 0.99 * np.exp(-((t - 18) / 5.0) ** 8))
    vb = np.where(t > 31, vb * np.exp(-(t - 31) / 2.5), vb)
    a1 = ax.inset_axes([0.07, 0.58, 0.90, 0.34])
    a2 = ax.inset_axes([0.07, 0.12, 0.90, 0.34])
    for a in (a1, a2):
        a.axvspan(12.0, 24.0, color="#f4f3ee", lw=0)
        a.set_xlim(0, 40)
        a.tick_params(labelsize=7.6)
        for sp in ("top", "right"):
            a.spines[sp].set_visible(False)
    a1.plot(t, hdep, color=C_BLUE, lw=1.8)
    a1.set_ylim(0, 2.6); a1.set_yticks([0, 1, 2]); a1.set_xticklabels([])
    a1.set_ylabel(T("汀線帯の水深 (m)", "depth at the shoreline (m)"), fontsize=8)
    a1.annotate("", xy=(24.0, 2.35), xytext=(12.0, 2.35), arrowprops=dict(arrowstyle="<->", color=C_INK, lw=0.9))
    a1.text(18, 2.42, T("突入で水が沖へ押し出され、十数秒だけ 0.1 m 程度に",
                        "entry pushes the water offshore: about 0.1 m for over ten seconds"),
            fontsize=7.6, ha="center", va="bottom")
    a2.plot(t, vb, color=C_ORANGE, lw=1.8)
    a2.axhline(0.15, color=C_MUTED, lw=0.8, ls="--")
    a2.text(39.5, 0.25, "v_stop", fontsize=7.6, color=C_MUTED, ha="right")
    a2.set_ylim(0, 5.2); a2.set_yticks([])
    a2.set_ylabel(T("底層の速さ", "bed-layer speed"), fontsize=8)
    a2.set_xlabel(T("時刻 (s)(模式)", "time (s) (schematic)"), fontsize=8)
    a2.annotate(T("この間に失速する。即時に固定すると\n汀線に人工のローブが残る",
                  "stalls meanwhile; fixing at once\nleaves an artificial shoreline lobe"),
                xy=(17.0, 0.25), xytext=(0.5, 5.1), fontsize=7.6, color=C_ORANGE, va="top",
                arrowprops=dict(arrowstyle="-|>", color=C_ORANGE, lw=0.8))
    a2.text(39.8, 5.1, T("bs_tstop = 15 s: 低速が 15 s 続いた\nセルだけ固定 → 水が戻ると再び動く",
                         "bs_tstop = 15 s: fixed only after\n15 s of low speed; moves on later"),
            fontsize=7.6, ha="right", va="top", color=C_INK)
    # (c) decision of the handover (case B).
    ax = fig.add_subplot(gs[1, 0])
    ax.set_title(T("(c) 引き渡しの判定(B)", "(c) Deciding the handover (B)"), fontsize=10, loc="left")
    ax.axis("off")
    flowbox(ax, 0.01, 0.80, 0.45, 0.13, T("混合体 hs のあるセル", "a cell with mixture hs"))
    flowbox(ax, 0.01, 0.50, 0.45, 0.20, T("静水時の水深 e0 − z ≥ bs_hplunge(2 m)?\n"
                                          "(f_bsplunge = 1。離水中でも判定できる)",
                                          "still-water depth e0 − z ≥ bs_hplunge (2 m)?\n"
                                          "(f_bsplunge = 1; works while dry)"), size=7.6)
    flowbox(ax, 0.01, 0.20, 0.45, 0.20, T("混合体の速さ ≤ 底層の終端速度?\n(f_bsvplunge = 1)",
                                          "mixture speed ≤ bed-layer terminal velocity?\n(f_bsvplunge = 1)"), size=7.6)
    flowbox(ax, 0.56, 0.20, 0.42, 0.20, T("hs を底層 hb へ移す\n(かさ体積 hs/(1 − λ)。運動量は失う)",
                                          "move hs to the bed layer hb\n(bulk volume hs/(1 − λ); momentum lost)"),
            face="#fbe9df", edge=C_ORANGE, size=7.6)
    flowbox(ax, 0.56, 0.55, 0.42, 0.18, T("混合体のまま流れる\n(慣性で水柱に運動量を渡す)",
                                          "keeps flowing as the mixture\n(passes momentum to the water)"), size=7.6)
    for (x0, y0, x1, y1) in ((0.235, 0.80, 0.235, 0.70), (0.235, 0.50, 0.235, 0.40), (0.46, 0.30, 0.56, 0.30)):
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0), xycoords="axes fraction",
                    arrowprops=dict(arrowstyle="-|>", color=C_INK, lw=1.0))
    ax.annotate("", xy=(0.56, 0.64), xytext=(0.46, 0.60), xycoords="axes fraction",
                arrowprops=dict(arrowstyle="-|>", color=C_MUTED, lw=1.0))
    ax.annotate("", xy=(0.62, 0.55), xytext=(0.46, 0.34), xycoords="axes fraction",
                arrowprops=dict(arrowstyle="-|>", color=C_MUTED, lw=1.0, connectionstyle="arc3,rad=-0.25"))
    ax.text(0.25, 0.445, T("はい", "yes"), fontsize=8, transform=ax.transAxes)
    ax.text(0.25, 0.745, T("", ""), fontsize=8, transform=ax.transAxes)
    ax.text(0.49, 0.315, T("はい", "yes"), fontsize=8, transform=ax.transAxes)
    ax.text(0.49, 0.645, T("いいえ", "no"), fontsize=8, color=C_MUTED, transform=ax.transAxes)
    ax.text(0.53, 0.43, T("いいえ", "no"), fontsize=8, color=C_MUTED, transform=ax.transAxes)
    ax.text(0.02, 0.04, T("現在の水深で判定すると、離水中に着いた混合体が渡されずに汀線に残る。\n"
                          "高速の突入(30〜50 m/s)では引き渡し時の速さを Log の plunge speeds で確かめる。",
                          "Judging by the current depth leaves mixture that arrives during drying at the shoreline.\n"
                          "For fast entries (30–50 m/s) check the speeds at handover in the plunge speeds of the Log."),
            fontsize=7.8, color=C_MUTED, transform=ax.transAxes, va="bottom")
    # (d) direction of the bias of the inertia-free bed layer.
    ax = fig.add_subplot(gs[1, 1])
    ax.set_title(T("(d) 慣性なしの底層の偏りの向き", "(d) Direction of the bias of the inertia-free bed layer"),
                 fontsize=10, loc="left")
    ax.axis("off")
    for k, (ttl, kind) in enumerate(((T("水中で発火(C)", "released under water (C)"), "sub"),
                                     (T("高速で陸上から突入(A の経路)", "fast entry from land (path of A)"), "land"))):
        sub = ax.inset_axes([0.04 + 0.50 * k, 0.30, 0.42, 0.55])
        s = np.linspace(0, 1, 300)
        env = np.exp(-np.maximum(s - 0.78, 0) ** 2 / 0.006)          # stops at the end of the path
        if kind == "sub":
            real = 6.0 * (1 - np.exp(-s / 0.15)) * env
            nin = np.where(s < 0.01, 0, 6.0) * env
            sub.axvline(0.0, color=C_MUTED, lw=0.6)
            note_txt = T("終端速度にすぐ達し、初めが速すぎる\n→ 近地の波は過大側",
                         "reaches the terminal velocity at once; too fast\nat first → near-field waves lean high")
        else:
            land = s < 0.4
            real = np.where(land, 11.0 * (1 - np.exp(-s / 0.08)),
                            5.0 + 6.0 * np.exp(-(s - 0.4) / 0.12)) * env
            nin = np.where(land, np.where(s < 0.01, 0, 11.0), 5.0) * env
            sub.axvline(0.4, color=C_EDGE, lw=0.9, ls="--")
            sub.text(0.41, 13.8, T("汀線", "shoreline"), fontsize=7.6, color=C_EDGE)
            note_txt = T("汀線でその場の水中の終端速度に落ちる\n→ 近地の波は過小側。高速突入は B の経路を推奨",
                         "drops to the underwater terminal velocity\nat the shoreline → near-field waves lean low;\nprefer the path of B for fast entries")
        sub.plot(s, real, color=C_INK, lw=1.6, label=T("慣性あり(実際)", "with inertia (actual)"))
        sub.plot(s, nin, color=C_ORANGE, lw=1.6, ls="--", label=T("慣性なしの底層", "inertia-free bed layer"))
        sub.set_title(ttl, fontsize=8.6)
        sub.set_xticks([]); sub.set_yticks([])
        sub.set_xlabel(T("走行距離", "distance travelled"), fontsize=8)
        sub.set_ylabel(T("速さ", "speed"), fontsize=8)
        sub.set_ylim(0, 15)
        for sp in ("top", "right"):
            sub.spines[sp].set_visible(False)
        if k == 0:
            sub.legend(fontsize=7.6, frameon=False, loc="upper right")
        ax.text(0.04 + 0.50 * k, 0.16, note_txt, fontsize=7.8, transform=ax.transAxes, va="top")
    fig.savefig(f"{FIGDIR}/properties.png", dpi=100)
    plt.close(fig)


# ----------------------------------------------------------------------------------------------
def nh_theory():
    kh = np.linspace(1e-3, 6, 600)
    beta = kh ** 2 / 4
    c_swe = np.ones_like(kh)
    c_nh = 1 / np.sqrt(1 + beta)
    cg_nh = 1 / (1 + beta) ** 1.5
    c_ex = np.sqrt(np.tanh(kh) / kh)
    cg_ex = 0.5 * c_ex * (1 + 2 * kh / np.sinh(2 * kh))
    f_nh = 1 / (1 + beta) ** 2
    f_ex = 1 / np.cosh(kh)
    fig, axes = plt.subplots(1, 3, figsize=(12.6, 4.6))
    fig.subplots_adjust(left=0.06, right=0.98, top=0.80, bottom=0.30, wspace=0.28)
    fig.suptitle(T("1 層非静水圧の振る舞い(平坦・微小振幅の線形解析。nonhydrostatic_plan.md §16.1 の式)",
                   "Behaviour of the one-layer non-hydrostatic model (linear analysis, flat bed, small amplitude; "
                   "nonhydrostatic_plan.md §16.1)"), fontsize=10.5, x=0.06, ha="left")
    band = dict(color="#f4f3ee", lw=0)
    ax = axes[0]
    ax.axvspan(1, 3, **band)
    ax.plot(kh, c_swe, color=C_MUTED, lw=1.6, label=T("静水圧(浅水方程式)", "hydrostatic (shallow water)"))
    ax.plot(kh, c_nh, color=C_BLUE, lw=1.8, label=T("1 層非静水圧: 位相速度", "one-layer NH: phase speed"))
    ax.plot(kh, cg_nh, color=C_BLUE, lw=1.4, ls="--", label=T("1 層非静水圧: 群速度", "one-layer NH: group velocity"))
    ax.plot(kh, c_ex, color=C_INK, lw=1.2, label=T("厳密(線形の水面波): 位相速度", "exact (linear water waves): phase"))
    ax.plot(kh, cg_ex, color=C_INK, lw=1.0, ls=":", label=T("厳密: 群速度", "exact: group"))
    ax.set_xlim(0, 6); ax.set_ylim(0, 1.08)
    ax.set_xlabel("kH", fontsize=9)
    ax.set_ylabel(T("速さ / √(gH)", "speed / √(gH)"), fontsize=9)
    ax.set_title(T("(a) 分散関係: 短い波ほど遅い", "(a) Dispersion: shorter waves are slower"), fontsize=9.5, loc="left")
    ax.text(2.0, 1.02, T("この例題", "this example"), fontsize=8, ha="center", va="bottom")
    ax.legend(fontsize=7.2, frameon=False, loc="upper left", bbox_to_anchor=(-0.02, -0.18), ncol=1)
    ax = axes[1]
    ax.axvspan(1, 3, **band)
    ax.plot(kh, np.ones_like(kh), color=C_MUTED, lw=1.6,
            label=T("静水圧・非静水圧(加速度項なし): 1", "hydrostatic, NH without the acceleration term: 1"))
    ax.plot(kh, f_nh, color=C_BLUE, lw=1.8, label=T("非静水圧 + 加速度項: 1/(1 + k²H²/4)²", "NH + acceleration term: 1/(1 + k²H²/4)²"))
    ax.plot(kh, f_ex, color=C_INK, lw=1.2, label=T("厳密(Kajiura): 1/cosh(kH)", "exact (Kajiura): 1/cosh(kH)"))
    ax.set_xlim(0, 6); ax.set_ylim(0, 1.08)
    ax.set_xlabel("kH", fontsize=9)
    ax.set_ylabel(T("水面に写る割合 F", "fraction passed to the surface F"), fontsize=9)
    ax.set_title(T("(b) 底面変位を水面に写すフィルタ", "(b) Filter from bed displacement to the surface"),
                 fontsize=9.5, loc="left")
    ax.legend(fontsize=7.2, frameon=False, loc="upper left", bbox_to_anchor=(-0.02, -0.18), ncol=1)
    ax = axes[2]
    lam = np.logspace(np.log10(5), np.log10(2000), 400)
    k = 2 * np.pi / lam
    t_swe = 2 * np.pi / (k * np.sqrt(G * H))
    t_nh = 2 * np.pi * np.sqrt(1 + (k * H) ** 2 / 4) / (k * np.sqrt(G * H))
    t_ex = 2 * np.pi / np.sqrt(G * k * np.tanh(k * H))
    tinf = np.pi * np.sqrt(H / G)
    ax.axvspan(2 * np.pi * H / 3, 2 * np.pi * H / 1, **band)
    ax.plot(lam, t_swe, color=C_MUTED, lw=1.6, label=T("静水圧", "hydrostatic"))
    ax.plot(lam, t_nh, color=C_BLUE, lw=1.8, label=T("1 層非静水圧", "one-layer NH"))
    ax.plot(lam, t_ex, color=C_INK, lw=1.2, label=T("厳密", "exact"))
    ax.axhline(tinf, color=C_ORANGE, lw=1.0, ls="--")
    ax.text(5.6, 12.0, T("1 層非静水圧の短い波の\n周期の下限 π√(H/g) = %.1f s\n(群速度 0 = その場に留まる)" % tinf,
                         "short-wave limit of the period\nof one-layer NH: π√(H/g) = %.1f s\n(group velocity 0 = waves stay)" % tinf),
            fontsize=7.6, color=C_ORANGE, va="bottom")
    ax.set_xscale("log")
    ax.set_xlim(5, 2000); ax.set_ylim(0, 40)
    ax.set_xlabel(T("波長 (m)", "wavelength (m)"), fontsize=9)
    ax.set_ylabel(T("周期 (s)", "period (s)"), fontsize=9)
    ax.set_title(T("(c) 水深 40 m の周期と波長", "(c) Period and wavelength at 40 m depth"), fontsize=9.5, loc="left")
    ax.legend(fontsize=7.2, frameon=False, loc="upper left", bbox_to_anchor=(-0.02, -0.18), ncol=3)
    for a in axes:
        a.tick_params(labelsize=8)
        for s in ("top", "right"):
            a.spines[s].set_visible(False)
    fig.savefig(f"{FIGDIR}/nh_theory.png", dpi=100)
    plt.close(fig)


if __name__ == "__main__":
    setup()
    mechanism()
    properties()
    nh_theory()
    print(" ".join(f"{FIGDIR}/{n}.png" for n in ("setup", "mechanism", "properties", "nh_theory")))
