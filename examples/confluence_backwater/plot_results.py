#!/usr/bin/env python3
"""confluence_backwater の図と数表(事前に make run・make coarse・make steady・make junction を計算しておく)。

  figs/mechanism.png  支川の背水による氾濫の模式図(縦断と平面。平面は本編の地形を使う。計算結果は使わない)
  figs/setup.png      地形と計測の位置、支川の口の横断、流量の時系列
  figs/maps.png       6 ケースの最大浸水深
  figs/profiles.png   支川の最大水位の縦断(流量の組み合わせの 4 ケースと対策の 2 ケース)
  figs/series.png     合流点の本川の水位、支川の口の流量(逆流)、堤内地の水量、支川の水位観測所の水位と流量の関係
  figs/measures.png   対策の 2 ケース(堤内地の水量、合流点の本川の水位、水門の内外の水位とポンプ)
  figs/coarse_masks.png  粗い格子(Δx = 100 m)の河道マスクの作り方 3 通り(合流点と狭窄部のまわり)
  figs/coarse.png     粗い格子の 3 通りと本編の比較(最大浸水深、合流点の本川の水位、堤内地の水量)
  figs/backwater.png  定常の支川の背水曲線と 1 次元の理論(漸変流の式)
  figs/junction.png   補足「合流の形と水位」(合流角・格子の大きさ・湾曲部の外岸と内岸)
引数 en で英語ラベル版を en/figs/ に描く(データと描画処理は共通)。計算していないケースの図と表は飛ばす。
"""
import glob
import math
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, FancyArrowPatch

import make_terrain as m
import make_coarse as mc
sys.path.insert(0, "junction")
import make_junction as mj

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
SEP = ", " if EN else "・"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)

G = 9.81
CASES = [("trib", T("支川だけの出水", "tributary flood only"), "#4d9221", ":"),
         ("main", T("本川だけの出水", "main-river flood only"), "#1f5f8b", "-"),
         ("early", T("両方(支川のピークが 3 h 早い)", "both (tributary peak 3 h earlier)"), "#e08214", "--"),
         ("same", T("両方(ピークが重なる)", "both (peaks coincide)"), "#c0392b", "-")]
MEASURES = [("same", T("対策なし(ピークが重なる)", "no measure (peaks coincide)"), "#c0392b", "-"),
            ("raise", T("対策 A 背水区間の堤防のかさ上げ", "measure A: raise levees in the backwater section"), "#7b3294", "-."),
            ("gate", T("対策 B 水門と排水ポンプ", "measure B: gate and drainage pump"), "#008080", "--")]
LABEL = {c: lab for c, lab, _, _ in CASES + MEASURES[1:]}
C_GROUND, C_WATER, C_LEVEE = "#d9c7a0", "#2a78d6", "#555555"
EXT = [0, m.NX * m.DX, 0, m.NY * m.DX]                  # x 東、y 北(行 1 = 北を上に)
COLS_T = [128, 129, 130, 131]                            # 支川の列(0 始まり)
CREST_M = m.ZMJ + m.LEV_M


# ---------------------------------------------------------------- 読み込み
def have(case, d="."):
    return os.path.exists(os.path.join(d, f"result_{case}", "H9999.txt"))


def frames(case, var="H", d="."):
    fs = glob.glob(os.path.join(d, f"result_{case}", f"{var}[0-9][0-9][0-9][0-9].txt"))
    fs = [f for f in fs if int(os.path.basename(f)[len(var):len(var) + 4]) < 9000]
    return sorted(fs)


def flux(case, n, d="."):
    a = np.loadtxt(os.path.join(d, f"result_{case}", "fluxes", f"flux{n:04d}.csv"), delimiter=",", comments="#")
    return a[:, 1], a[:, 2]


def probe(case, n, d="."):
    """時刻(分)・水位・水深"""
    a = np.loadtxt(os.path.join(d, f"result_{case}", "probes", f"probe{n:04d}.csv"), delimiter=",", comments="#")
    return a[:, 1], a[:, 2] + a[:, 3], a[:, 3]


KIND = np.loadtxt("data/kind.txt", dtype=int)
Z = np.loadtxt("data/z.txt")
FP = KIND == 5
ROWS_T = [j for j in range(m.NY) if KIND[j, 129] == 3]
Y_T = np.array([m.LY - (j + 0.5) * m.DX - m.Y_MOUTH for j in ROWS_T])   # 支川の口からの距離 (m)
ZB_T = np.array([Z[j, 129] for j in ROWS_T])
CREST_T = np.array([Z[j, 127] for j in ROWS_T])


def fp_volume(case, d=".", kind=None, area=None):
    kind = KIND if kind is None else kind
    area = m.DX * m.DX if area is None else area
    fs = frames(case, d=d)
    v = np.array([float((np.loadtxt(f) * (kind == 5)).sum() * area) for f in fs])
    return np.arange(len(v)) * 0.5, v


def trib_max_level(case):
    hm = np.loadtxt(f"result_{case}/H9999.txt")
    return np.array([ZB_T[n] + hm[j, COLS_T].mean() for n, j in enumerate(ROWS_T)])


def overflow_extent(case, z_crest):
    """支川の最大水位が堤防の天端を超えた区間の上流端(口からの距離 m)"""
    e = trib_max_level(case)
    over = Y_T[(e > z_crest) & (Y_T > 0)]
    return float(over.max()) if len(over) else 0.0


# ---------------------------------------------------------------- 図 1: 模式図
def fig_mechanism():
    fig = plt.figure(figsize=(12.5, 5.6))
    ax = fig.add_axes([0.05, 0.12, 0.43, 0.78])
    # 支川の洪水(300 m3/s、幅 80 m、n 0.035、勾配 1/1000。等流水深 2.35 m)の水面を、口の水深 5.0 m(本川の水位)から
    # 漸変流の式で上流へ積分する(模式の値。本編の地形に近い)
    q, n_, s0 = m.QT_PEAK / m.BT, m.RNT, m.ST
    hn_ = (n_ * q / math.sqrt(s0)) ** 0.6

    def f(h):
        return -(s0 - n_ ** 2 * q ** 2 / h ** (10.0 / 3.0)) / (1.0 - q ** 2 / (G * h ** 3))
    s, eta, h = [0.0], [5.0], 5.0
    while s[-1] < 6000:
        d = 5.0
        k1 = f(h); k2 = f(h + 0.5 * d * k1); k3 = f(h + 0.5 * d * k2); k4 = f(h + d * k3)
        h += d * (k1 + 2 * k2 + 2 * k3 + k4) / 6.0
        s.append(s[-1] + d)
        eta.append(h + s0 * s[-1])
    s, eta = np.array(s), np.array(eta)
    zb = s0 * s
    crest = zb + m.LEV_T
    fpl = zb + m.FP_T
    own = zb + hn_
    ax.fill_between(s, zb - 0.6, zb, color=C_GROUND, lw=0)
    ax.plot(s, zb, color="k", lw=1)
    ax.plot(s, crest, color=C_LEVEE, lw=1.6, ls="--", label=T("支川の堤防の天端", "tributary levee crest"))
    ax.plot(s, fpl, color="#8c6d31", lw=1, ls=":", label=T("堤内地の地盤", "landside ground"))
    ax.fill_between(s, zb, eta, color=C_WATER, alpha=0.25, lw=0)
    ax.plot(s, own, color="#4d9221", lw=1.2, label=T("支川の流量だけの水面(等流)", "water surface of the tributary flow alone (uniform)"))
    ax.plot(s, eta, color=C_WATER, lw=2, label=T("本川の水位による背水の水面", "water surface backed up by the main river"))
    over = eta > crest
    ax.fill_between(s, crest, eta, where=over, color="#c0392b", alpha=0.7, lw=0)
    x_end = float(s[(eta - own) > 0.1].max())
    ax.annotate("", xy=(0, -0.9), xytext=(x_end, -0.9), arrowprops=dict(arrowstyle="<->", color="k", lw=1))
    ax.text(x_end / 2, -1.3, T("背水が及ぶ範囲(等流より 0.1 m 以上高い)", "reach affected by backwater (> 0.1 m above uniform flow)"),
            ha="center", fontsize=9)
    ax.annotate(T("越水", "overtopping"), xy=(200, 4.85), xytext=(900, 6.7), color="#c0392b", fontsize=10,
                arrowprops=dict(arrowstyle="-", color="#c0392b", lw=0.8))
    ax.text(500, 1.9, T("合流点の本川の水位が支川をさかのぼる(背水)", "the main-river stage backs up the tributary (backwater)"),
            fontsize=8.5, color="#1f5f8b")
    ax.set_xlim(0, 6000)
    ax.set_ylim(-1.5, 9)
    ax.set_xlabel(T("支川の口からの距離 (m。上流が右)", "distance from the tributary mouth (m, upstream to the right)"))
    ax.set_ylabel(T("支川の河床から測った高さ (m。口の河床 = 0)", "height above the tributary bed at the mouth (m)"))
    ax.set_title(T("(a) 支川の縦断: 本川の水位が支川をさかのぼり、低い堤防を越える",
                   "(a) Along the tributary: backwater overtops the lower levees"),
                 fontsize=10, loc="left")
    ax.legend(fontsize=8, loc="lower right", bbox_to_anchor=(1.0, 0.1))
    # (b) 平面(本編の地形)
    ax = fig.add_axes([0.53, 0.06, 0.45, 0.86])
    img = np.full(KIND.shape + (3,), 1.0)
    col = {1: (0.55, 0.75, 0.95), 2: (0.33, 0.33, 0.33), 3: (0.55, 0.75, 0.95), 4: (0.33, 0.33, 0.33), 5: (0.85, 0.78, 0.63)}
    for kk, cc in col.items():
        img[KIND == kk] = cc
    hills = KIND == 0
    img[hills] = (0.72, 0.80, 0.66)
    ax.imshow(img, extent=EXT, interpolation="nearest")
    ax.set_xlim(800, 5600)
    ax.set_ylim(300, 4200)
    ax.set_xticks([])
    ax.set_yticks([])
    # 浸水の模式(合流点の近くの堤内地)
    for pts in ([(1720, 850), (2530, 1130), (2530, 2700), (1720, 1500)],
                [(2670, 1130), (3480, 850), (3480, 1500), (2670, 2700)]):
        ax.add_patch(Polygon(pts, closed=True, facecolor=C_WATER, alpha=0.5, edgecolor="none"))
    arrow = dict(arrowstyle="-|>", mutation_scale=14, lw=1.6)
    ax.add_patch(FancyArrowPatch((1000, 700), (1700, 720), color="#1f5f8b", **arrow))
    ax.add_patch(FancyArrowPatch((3600, 760), (4300, 700), color="#1f5f8b", **arrow))
    ax.add_patch(FancyArrowPatch((2600, 1200), (2600, 1900), color="#c0392b", **arrow))
    for y in (1400, 1700):
        ax.add_patch(FancyArrowPatch((2560, y), (2300, y + 80), color="#c0392b", **arrow))
        ax.add_patch(FancyArrowPatch((2640, y), (2900, y + 80), color="#c0392b", **arrow))
    ax.add_patch(FancyArrowPatch((2600, 3600), (2600, 2900), color="#4d9221", **arrow))
    ax.text(1000, 820, T("本川", "main river"), color="#1f5f8b", fontsize=10)
    ax.text(2680, 3400, T("支川", "tributary"), color="#4d9221", fontsize=10)
    ax.text(2680, 1900, T("本川の水が逆流", "main-river water flows back"), color="#c0392b", fontsize=9)
    ax.text(1650, 2350, T("越水した水が\n堤内地にたまる", "overtopped water\nponds on the landside"), fontsize=9, ha="center")
    ax.text(4500, 950, T("狭窄部\n(合流点の水位を上げる)", "narrows\n(raises the stage at the confluence)"), fontsize=9, ha="center")
    ax.text(2600, 450, T("湾曲部の外岸に合流", "joins on the outer bank of a bend"), fontsize=9, ha="center")
    ax.set_title(T("(b) 平面: 逆流・越水・浸水の経路(本編の地形)", "(b) Plan: reverse flow, overtopping, ponding"),
                 fontsize=10, loc="left")
    fig.savefig(os.path.join(FIGDIR, "mechanism.png"), dpi=120)
    plt.close(fig)


# ---------------------------------------------------------------- 図 2: 地形と設定
PROBES = [(130, 316), (130, 325), (81, 335), (130, 305), (130, 215), (130, 115), (115, 300), (145, 300), (129, 313)]
LINES = [(128, 314, 133, 314), (128, 305, 133, 305), (128, 215, 133, 215), (100, 339, 100, 328), (165, 340, 165, 329),
         (285, 341, 285, 330)]


def cxy(i, j):
    return (i - 0.5) * m.DX, m.LY - (j - 0.5) * m.DX


def fig_setup():
    fig = plt.figure(figsize=(13, 7.2))
    ax = fig.add_axes([0.07, 0.08, 0.40, 0.86])
    zz = np.where(KIND > 0, Z, np.nan)
    im = ax.imshow(zz, extent=EXT, cmap="terrain", vmin=15, vmax=31, interpolation="nearest")
    ax.contour(np.where(KIND == 5, Z, np.nan), levels=np.arange(20, 31, 1.0), colors="k", linewidths=0.3,
               extent=EXT, origin="upper")
    for n, (i, j) in enumerate(PROBES, 1):
        x, y = cxy(i, j)
        ax.plot(x, y, "o", ms=4, color="w", mec="k")
        ax.text(x + 60, y + 40, f"P{n}", fontsize=7)
    for n, (i1, j1, i2, j2) in enumerate(LINES, 1):
        (x1, y1), (x2, y2) = cxy(i1, j1), cxy(i2, j2)
        ax.plot([x1, x2], [y1, y2], "-", color="#c0392b", lw=2)
        ax.text(x2 + 50, y2, f"L{n}", fontsize=7, color="#c0392b")
    ax.set_xlim(0, m.NX * m.DX)
    ax.set_ylim(300, m.NY * m.DX)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    cb = fig.colorbar(im, ax=ax, shrink=0.6, pad=0.01)
    cb.set_label(T("地盤高 (m)", "ground elevation (m)"))
    ax.set_title(T("(a) 地形(白 = 丘陵。計算しない)と計測の位置", "(a) Terrain (white = hills, not computed) and gauges"),
                 fontsize=10, loc="left")
    ax.text(600, 900, T("本川", "main river"), fontsize=9)
    ax.text(4300, 480, T("狭窄部", "narrows"), fontsize=9)
    ax.text(2700, 5600, T("支川", "tributary"), fontsize=9)
    ax.text(1650, 4300, T("堤内地", "landside"), fontsize=9)
    # (b) 支川の口の近くの横断(行 300 = 口から 300 m)
    ax = fig.add_axes([0.55, 0.58, 0.42, 0.36])
    j = 299
    xs = (np.arange(m.NX) + 0.5) * m.DX
    sel = (xs > 1300) & (xs < 3900)
    zrow = np.where(KIND[j] > 0, Z[j], np.nan)
    ax.fill_between(xs[sel], 15, zrow[sel], step="mid", color=C_GROUND)
    ax.step(xs[sel], zrow[sel], where="mid", color="k", lw=0.8)
    if have("same"):
        e = probe("same", 4)[1]
        ax.axhline(e.max(), color=C_WATER, lw=1.2, ls="--")
        ax.text(1350, e.max() + 0.15, T("ケース same の支川の最高水位", "highest tributary level, case same"), fontsize=8, color=C_WATER)
    if have("trib"):
        e = probe("trib", 4)[1]
        ax.axhline(e.max(), color="#4d9221", lw=1.0, ls=":")
        ax.text(1350, e.max() + 0.15, T("ケース trib(支川だけの出水)の最高水位", "highest level, case trib (tributary flood only)"),
                fontsize=8, color="#4d9221")
    ax.set_xlim(1300, 3900)
    ax.set_ylim(18.5, 26.5)
    ax.set_xlabel("x (m)")
    ax.set_ylabel(T("標高 (m)", "elevation (m)"))
    ax.set_title(T("(b) 支川の口から 300 m 上流の横断(支川・堤防・堤内地)", "(b) Cross-section 300 m above the tributary mouth"),
                 fontsize=10, loc="left")
    # (c) 流量
    ax = fig.add_axes([0.55, 0.08, 0.42, 0.36])
    for fn, lab, col, ls in (("q_main_flood.txt", T("本川の出水", "main-river flood"), "#1f5f8b", "-"),
                             ("q_trib_early.txt", T("支川の出水(early)", "tributary flood (early)"), "#e08214", "--"),
                             ("q_trib_same.txt", T("支川の出水(same・trib)", "tributary flood (same, trib)"), "#c0392b", "-")):
        a = np.loadtxt(os.path.join("data", fn))
        ax.plot(a[:, 0] / 60, a[:, 1], ls, color=col, label=lab)
    ax.axhline(m.QM_BASE, color="#1f5f8b", lw=0.6, ls=":")
    ax.axhline(m.QT_BASE, color="#c0392b", lw=0.6, ls=":")
    ax.set_xlim(0, 14)
    ax.set_yscale("log")
    ax.set_ylim(10, 5000)
    ax.set_xlabel(T("時刻 (h)", "time (h)"))
    ax.set_ylabel(T("流入の流量 (m³/s)", "inflow (m³/s)"))
    ax.legend(fontsize=8, loc="lower right")
    ax.set_title(T("(c) 上流端の流量(点線 = 平水)", "(c) Inflows at the upstream ends (dotted = base flow)"), fontsize=10, loc="left")
    fig.savefig(os.path.join(FIGDIR, "setup.png"), dpi=120)
    plt.close(fig)


# ---------------------------------------------------------------- 図 3: 最大浸水深
def fig_maps():
    cases = [c for c in ["trib", "main", "early", "same", "raise", "gate"] if have(c)]
    if not cases:
        return
    fig, axs = plt.subplots(2, 3, figsize=(11.5, 9.6))
    fig.subplots_adjust(left=0.02, right=0.88, top=0.93, bottom=0.03, wspace=0.08, hspace=0.18)
    cmap = plt.get_cmap("Blues").copy()
    cmap.set_under("w")
    for ax, c in zip(axs.flat, cases):
        hm = np.loadtxt(f"result_{c}/H9999.txt")
        land = np.where((KIND == 5), hm, np.nan)
        bg = np.full(KIND.shape + (3,), 1.0)
        bg[KIND == 0] = (0.72, 0.80, 0.66)
        bg[(KIND == 1) | (KIND == 3)] = (0.80, 0.86, 0.95)
        bg[(KIND == 2) | (KIND == 4)] = (0.35, 0.35, 0.35)
        bg[KIND == 5] = (0.93, 0.90, 0.82)
        ax.imshow(bg, extent=EXT, interpolation="nearest")
        im = ax.imshow(np.where(land > 0.01, land, np.nan), extent=EXT, cmap=cmap, vmin=0.0, vmax=2.5, interpolation="nearest")
        if c == "raise":
            zr = np.loadtxt("data/z_raise.txt")
            ax.imshow(np.where(zr != Z, 1.0, np.nan), extent=EXT, cmap="Purples", vmin=0, vmax=1.2, interpolation="nearest")
        ax.set_xlim(1300, 3900)
        ax.set_ylim(500, 4300)
        ax.set_xticks([])
        ax.set_yticks([])
        t, v = fp_volume(c)
        area = float(((hm > 0.1) & FP).sum()) * m.DX * m.DX / 1e6
        ax.set_title(f"{LABEL[c]}\n" + T(f"堤内地の最大水量 {v.max() / 1e6:.2f} 百万 m³・浸水 {area:.2f} km²",
                                        f"max landside volume {v.max() / 1e6:.2f} Mm³, flooded {area:.2f} km²"), fontsize=9)
    for ax in axs.flat[len(cases):]:
        ax.axis("off")
    cax = fig.add_axes([0.90, 0.25, 0.015, 0.5])
    cb = fig.colorbar(im, cax=cax)
    cb.set_label(T("最大浸水深 (m。0.01 m 未満は白)", "maximum flood depth (m, below 0.01 m white)"))
    fig.savefig(os.path.join(FIGDIR, "maps.png"), dpi=110)
    plt.close(fig)


# ---------------------------------------------------------------- 図 4: 支川の縦断
def fig_profiles():
    if not have("same"):
        return
    fig, axs = plt.subplots(1, 2, figsize=(13, 5.0))
    for ax, group, title in ((axs[0], CASES, T("(a) 流量の組み合わせ", "(a) Combinations of floods")),
                             (axs[1], MEASURES, T("(b) 対策(ケース same と同じ流量)", "(b) Measures (same floods as case same)"))):
        ax.fill_between(Y_T / 1000, ZB_T - 1, ZB_T, color=C_GROUND, lw=0)
        ax.plot(Y_T / 1000, ZB_T, "k-", lw=0.8)
        ax.plot(Y_T / 1000, CREST_T, "--", color=C_LEVEE, lw=1.2, label=T("支川の堤防の天端", "tributary levee crest"))
        ax.plot(Y_T / 1000, ZB_T + m.FP_T, ":", color="#8c6d31", lw=1, label=T("堤内地(支川沿い)", "landside next to the tributary"))
        if group is MEASURES:
            zr = np.loadtxt("data/z_raise.txt")
            cr = np.array([zr[j, 127] for j in ROWS_T])
            ax.plot(Y_T / 1000, cr, "-.", color="#7b3294", lw=1.0, label=T("かさ上げした天端(対策 A)", "raised crest (measure A)"))
        for c, lab, col, ls in group:
            if not have(c):
                continue
            ax.plot(Y_T / 1000, trib_max_level(c), ls, color=col, lw=1.6, label=lab)
        ax.set_xlim(0, 6.2)
        ax.set_ylim(19, 27.5)
        ax.set_xlabel(T("支川の口からの距離 (km)", "distance from the tributary mouth (km)"))
        ax.set_ylabel(T("最大水位・標高 (m)", "maximum water level, elevation (m)"))
        ax.legend(fontsize=8, loc="lower right")
        ax.set_title(title, fontsize=10, loc="left")
        ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, "profiles.png"), dpi=120)
    plt.close(fig)


# ---------------------------------------------------------------- 図 5: 時系列
def rating_q(h):
    """支川の等流の水位と流量の関係(幅 80 m、n 0.035、勾配 1/1000、R = h)"""
    return m.BT * h ** (5.0 / 3.0) * math.sqrt(m.ST) / m.RNT


def fig_series():
    if not have("same"):
        return
    fig, axs = plt.subplots(2, 2, figsize=(13, 8.6))
    gauge_bed = Z[214, 129]
    for c, lab, col, ls in CASES:
        if not have(c):
            continue
        t, e, _ = probe(c, 1)
        axs[0, 0].plot(t / 60, e, ls, color=col, lw=1.4, label=lab)
        t1, q1 = flux(c, 1)
        axs[0, 1].plot(t1 / 60, q1, ls, color=col, lw=1.4, label=lab)
        tv, v = fp_volume(c)
        axs[1, 0].plot(tv, v / 1e6, ls, color=col, lw=1.4, label=lab)
        if c in ("trib", "main", "same"):
            tg, eg, hg = probe(c, 5)
            t2, q2 = flux(c, 3)
            n = min(len(q2), len(eg))
            axs[1, 1].plot(q2[:n], eg[:n], ls, color=col, lw=1.4, label=lab)
    hh = np.linspace(0.3, 3.0, 50)
    axs[1, 1].plot([rating_q(h) for h in hh], gauge_bed + hh, color="k", lw=0.8, ls=":",
                   label=T("等流の水位と流量の関係", "uniform-flow rating curve"))
    axs[0, 0].axhline(Z[304, 127], color=C_LEVEE, ls="--", lw=1)
    axs[0, 0].text(0.2, Z[304, 127] + 0.08, T("支川の口から 200 m の堤防の天端", "tributary crest 200 m above the mouth"), fontsize=8)
    axs[0, 0].set_ylabel(T("水位 (m)", "water level (m)"))
    axs[0, 0].set_title(T("(a) 合流点の本川の水位(北岸 = 外岸。P1)", "(a) Main-river stage at the confluence (north = outer bank, P1)"),
                        fontsize=10, loc="left")
    axs[0, 1].axhline(0, color="k", lw=0.6)
    axs[0, 1].set_ylabel(T("流量 (m³/s。負 = 逆流)", "discharge (m³/s, negative = reverse flow)"))
    axs[0, 1].set_title(T("(b) 支川の口の流量(L1)", "(b) Discharge at the tributary mouth (L1)"), fontsize=10, loc="left")
    axs[1, 0].set_ylabel(T("堤内地の水量 (百万 m³)", "water on the landside (million m³)"))
    axs[1, 0].set_title(T("(c) 堤内地にたまった水の量", "(c) Water ponded on the landside"), fontsize=10, loc="left")
    for ax in (axs[0, 0], axs[0, 1], axs[1, 0]):
        ax.set_xlabel(T("時刻 (h)", "time (h)"))
        ax.set_xlim(0, 14)
        ax.grid(alpha=0.3)
    axs[0, 1].legend(fontsize=7, loc="upper left")
    axs[1, 1].set_xlabel(T("流量 (m³/s。L3)", "discharge (m³/s, L3)"))
    axs[1, 1].set_ylabel(T("水位 (m。P5)", "water level (m, P5)"))
    axs[1, 1].set_title(T("(d) 支川の水位観測所(口から 2 km)の水位と流量", "(d) Stage and discharge at the tributary gauge (2 km above the mouth)"),
                        fontsize=10, loc="left")
    axs[1, 1].legend(fontsize=8, loc="lower right")
    axs[1, 1].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, "series.png"), dpi=120)
    plt.close(fig)


# ---------------------------------------------------------------- 図 5b: 対策
PUMP_RULE = ((21.2, 0.0), (21.7, 50.0))          # param_gate.txt と同じ(水位 m, 流量 m3/s)


def fig_measures():
    if not (have("same") and (have("raise") or have("gate"))):
        return
    fig, axs = plt.subplots(1, 3, figsize=(14, 4.6))
    for c, lab, col, ls in MEASURES:
        if not have(c):
            continue
        tv, v = fp_volume(c)
        axs[0].plot(tv, v / 1e6, ls, color=col, lw=1.6, label=lab)
        t, e, _ = probe(c, 1)
        axs[1].plot(t / 60, e, ls, color=col, lw=1.6, label=lab)
    axs[0].set_ylabel(T("堤内地の水量 (百万 m³)", "water on the landside (million m³)"))
    axs[0].set_title(T("(a) 堤内地にたまった水の量", "(a) Water ponded on the landside"), fontsize=10, loc="left")
    axs[0].legend(fontsize=8, loc="upper left")
    axs[1].axhline(CREST_M, color=C_LEVEE, ls="--", lw=1)
    axs[1].text(0.2, CREST_M - 0.3, T("本川の堤防の天端(合流点)", "main-river levee crest (confluence)"), fontsize=8)
    axs[1].set_ylabel(T("水位 (m)", "water level (m)"))
    axs[1].set_ylim(19, 27.2)
    axs[1].set_title(T("(b) 合流点の本川の水位(P1)", "(b) Main-river stage at the confluence (P1)"), fontsize=10, loc="left")
    if have("gate"):
        t, ein, _ = probe("gate", 9)
        t1, eout, _ = probe("gate", 1)
        axs[2].plot(t / 60, ein, "-", color="#008080", lw=1.6, label=T("水門の内側(支川。P9)", "inside the gate (tributary, P9)"))
        axs[2].plot(t1 / 60, eout, "--", color="#1f5f8b", lw=1.2, label=T("水門の外側(本川。P1)", "outside the gate (main river, P1)"))
        axs[2].axhline(Z[304, 127], color=C_LEVEE, ls=":", lw=1)
        axs[2].text(0.2, Z[304, 127] + 0.08, T("支川の堤防の天端(口から 200 m)", "tributary crest (200 m above the mouth)"), fontsize=8)
        ax2 = axs[2].twinx()
        qp = np.interp(ein, [a for a, b in PUMP_RULE], [b for a, b in PUMP_RULE])
        ax2.fill_between(t / 60, 0, qp, color="#7fbfbf", alpha=0.35, lw=0)
        ax2.set_ylim(0, 160)
        ax2.set_ylabel(T("ポンプの排水量 (m³/s。運転の則から)", "pump discharge (m³/s, from the rule)"))
        axs[2].set_ylabel(T("水位 (m)", "water level (m)"))
        axs[2].set_ylim(19, 26)
        axs[2].legend(fontsize=8, loc="upper left")
        axs[2].set_title(T("(c) ケース gate: 水門の内外の水位とポンプ", "(c) Case gate: levels across the gate and the pump"), fontsize=10, loc="left")
    for ax in axs:
        ax.set_xlabel(T("時刻 (h)", "time (h)"))
        ax.set_xlim(0, 14)
        ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, "measures.png"), dpi=120)
    plt.close(fig)


# ---------------------------------------------------------------- 図 6: 粗い格子
EXTC = [0, mc.NXC * mc.DXC, 0, mc.NYC * mc.DXC]
M_LABEL = {"simple": T("簡便", "simple"), "occ": T("占有率のまま", "covered fraction as is"),
           "fixed": T("直したもの", "corrected")}
M_STYLE = {"fine": ("k", "-", 1.8), "simple": ("#e08214", "--", 1.5), "occ": ("#7b3294", "-.", 1.5),
           "fixed": ("#1f8b6e", "-", 1.5)}


def coarse_data(method):
    """粗い格子の入力(kind、河道幅)。簡便は幅を与えないので 0"""
    d = f"data_coarse_{method}"
    if not os.path.exists(os.path.join(d, "kind.txt")):
        return None, None
    kind = np.loadtxt(os.path.join(d, "kind.txt"), dtype=int)
    fw = os.path.join(d, "width.txt")
    width = np.loadtxt(fw) if os.path.exists(fw) else np.zeros(kind.shape)
    return kind, width


def fig_coarse_masks():
    data = {r: coarse_data(r) for r in mc.METHODS}
    if any(v[0] is None for v in data.values()):
        return
    title = {"simple": T("(a) 簡便: 占有率 50 % 以上のセルを河道にし、幅は与えない",
                         "(a) Simple: cells covered 50 % or more are channel cells, no width given"),
             "occ": T("(b) 占有率のまま: 占有率 5 % 以上のセルをすべて河道にし、幅 = 占有率 × 100 m",
                      "(b) Covered fraction as is: every cell covered 5 % or more, width = fraction × 100 m"),
             "fixed": T("(c) 直したもの: 格子の軸に沿う区間を、解像したセル + 残りの幅のセル 1 つに詰め直す",
                        "(c) Corrected: along grid-axis reaches, packed into resolved cells + one remainder cell")}
    x0, x1, y0, y1 = 1300.0, 5300.0, 400.0, 1500.0
    fig, axs = plt.subplots(3, 1, figsize=(12, 9.6))
    xs = np.arange(x0, x1 + 1.0, 5.0)
    yc = np.array([m.yc(x) for x in xs])
    bw = np.array([m.width(x) for x in xs])
    for ax, r in zip(axs, mc.METHODS):
        kind, width = data[r]
        bg = np.full(kind.shape + (3,), 1.0)
        bg[kind == 0] = (0.80, 0.86, 0.76)
        bg[kind == 5] = (0.95, 0.93, 0.87)
        chan = (kind == 1) | (kind == 3)
        sub = chan & (width > 0.0) & (width < mc.RESOLVED)
        bg[chan & ~sub] = (0.16, 0.42, 0.78)
        bg[sub] = (0.62, 0.78, 0.95)
        ax.imshow(bg, extent=EXTC, interpolation="nearest")
        for j, i in zip(*np.nonzero(sub)):
            x, y = (i + 0.5) * mc.DXC, mc.LYC - (j + 0.5) * mc.DXC
            if x0 < x < x1 and y0 < y < y1:
                ax.text(x, y, f"{width[j, i]:.0f}", ha="center", va="center", fontsize=6.5, color="#0b2e5c")
        for g in np.arange(x0, x1 + 1.0, mc.DXC):
            ax.axvline(g, color="w", lw=0.4, alpha=0.7)
        for g in np.arange(y0, y1 + 1.0, mc.DXC):
            ax.axhline(g, color="w", lw=0.4, alpha=0.7)
        ax.plot(xs, yc + bw / 2, "k-", lw=0.9)
        ax.plot(xs, yc - bw / 2, "k-", lw=0.9)
        ytop = m.yc(m.XT) + m.BM / 2
        for xt in (m.XT - m.BT / 2, m.XT + m.BT / 2):
            ax.plot([xt, xt], [ytop, y1], "k-", lw=0.9)
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
        ax.set_aspect("equal")
        ax.set_xticks(np.arange(1500, 5300, 500))
        ax.set_yticks([500, 1000, 1500])
        ax.tick_params(labelsize=7)
        ax.set_title(title[r], fontsize=9.5, loc="left")
    axs[-1].set_xlabel(T("x (m)。本川は西から東へ、支川は北から合流する。狭窄部(幅 120 m)は x = 4,200〜4,800 m",
                         "x (m). The main river flows west to east, the tributary joins from the north. "
                         "Narrows (120 m wide) at x = 4,200–4,800 m"), fontsize=8)
    handles = [plt.Rectangle((0, 0), 1, 1, color=(0.16, 0.42, 0.78)),
               plt.Rectangle((0, 0), 1, 1, color=(0.62, 0.78, 0.95)),
               plt.Rectangle((0, 0), 1, 1, color=(0.95, 0.93, 0.87)),
               plt.Line2D([], [], color="k", lw=0.9)]
    labels = [T("解像した河道のセル(セル幅いっぱい)", "resolved channel cell (full cell width)"),
              T("サブグリッド河道のセル(数字は幅 m)", "subgrid channel cell (number = width in m)"),
              T("堤内地", "landside"),
              T("Δx = 20 m の河道の岸(元の河道マスク)", "banks of the Δx = 20 m channel (the source mask)")]
    fig.legend(handles, labels, loc="lower center", ncol=4, fontsize=8, frameon=False)
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    fig.savefig(os.path.join(FIGDIR, "coarse_masks.png"), dpi=110)
    plt.close(fig)


def fig_coarse():
    c = "same"
    runs = [r for r in mc.METHODS if have(f"coarse_{c}_{r}")]
    if not have(c) or not runs:
        return
    fig = plt.figure(figsize=(13, 8.6))
    cmap = plt.get_cmap("Blues").copy()
    panels = [(T("Δx = 20 m", "Δx = 20 m"), np.loadtxt(f"result_{c}/H9999.txt"), KIND, EXT)]
    for r in runs:
        panels.append((f"Δx = 100 m{SEP}{M_LABEL[r]}", np.loadtxt(f"result_coarse_{c}_{r}/H9999.txt"),
                       coarse_data(r)[0], EXTC))
    for k, (lab, hm, kind, ext) in enumerate(panels):
        ax = fig.add_axes([0.04 + 0.195 * k, 0.49, 0.18, 0.42])
        bg = np.full(kind.shape + (3,), 1.0)
        bg[kind == 0] = (0.72, 0.80, 0.66)
        bg[(kind == 1) | (kind == 3)] = (0.80, 0.86, 0.95)
        bg[(kind == 2) | (kind == 4)] = (0.35, 0.35, 0.35)
        bg[kind == 5] = (0.93, 0.90, 0.82)
        ax.imshow(bg, extent=ext, interpolation="nearest")
        land = np.where(kind == 5, hm, np.nan)
        im = ax.imshow(np.where(land > 0.01, land, np.nan), extent=ext, cmap=cmap, vmin=0, vmax=2.5, interpolation="nearest")
        ax.set_xlim(1300, 3900)
        ax.set_ylim(500, 4300)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(f"({'abcd'[k]}) {lab}", fontsize=9)
    fig.text(0.04, 0.965, T("(a)〜(d) ケース same(両方の出水。ピークが重なる)の最大浸水深。流量は本編と同じ",
                            "(a)–(d) Maximum flood depth, case same (both floods, peaks coincide); discharges as in the main cases"),
             fontsize=10)
    cax = fig.add_axes([0.83, 0.53, 0.01, 0.34])
    cb = fig.colorbar(im, cax=cax)
    cb.set_label(T("最大浸水深 (m)", "maximum flood depth (m)"))
    ax_e = fig.add_axes([0.06, 0.07, 0.40, 0.32])
    ax_v = fig.add_axes([0.56, 0.07, 0.40, 0.32])
    tf, ef, _ = probe(c, 1)
    tv, vf = fp_volume(c)
    on = tv[vf > 1.0e4]
    if len(on):
        ax_e.axvspan(on[0], tv[int(np.argmax(vf))], color="#e6e6e6", lw=0)
        ax_e.text(on[0] + 0.1, 0.25, T("Δx = 20 m で\n越水している間", "overflow on\nthe Δx = 20 m grid"), fontsize=8,
                  color="#555555", va="top")
    ax_e.axhline(0.0, color="k", lw=0.8)
    for r in ["fine"] + runs:
        col, ls, lw = M_STYLE[r]
        case = c if r == "fine" else f"coarse_{c}_{r}"
        lab = T("Δx = 20 m", "Δx = 20 m") if r == "fine" else f"Δx = 100 m{SEP}{M_LABEL[r]}"
        if r != "fine":
            t, e, _ = probe(case, 1)
            ax_e.plot(tf / 60, np.interp(tf, t, e) - ef, ls, color=col, lw=lw, label=lab)
            t, v = fp_volume(case, kind=coarse_data(r)[0], area=mc.DXC * mc.DXC)
        else:
            t, v = tv, vf
        ax_v.plot(t, v / 1e6, ls, color=col, lw=lw, label=lab)
    ax_e.set_ylabel(T("Δx = 100 m − Δx = 20 m (m)", "Δx = 100 m − Δx = 20 m (m)"))
    ax_e.set_ylim(-0.6, 0.3)
    ax_e.set_title(T("(e) 合流点の本川の水位の差(北岸。本編の P1 の位置)",
                     "(e) Difference of the main-river level at the confluence (north bank, P1)"), fontsize=10, loc="left")
    ax_e.legend(fontsize=8, loc="lower left")
    ax_v.set_ylabel(T("堤内地の水量 (百万 m³)", "water on the landside (million m³)"))
    ax_v.set_title(T("(f) 堤内地にたまった水の量", "(f) Water ponded on the landside"), fontsize=10, loc="left")
    ax_v.legend(fontsize=8, loc="upper left")
    for ax in (ax_e, ax_v):
        ax.set_xlabel(T("時刻 (h)", "time (h)"))
        ax.set_xlim(0, 14)
        ax.grid(alpha=0.3)
    fig.savefig(os.path.join(FIGDIR, "coarse.png"), dpi=110)
    plt.close(fig)


# ---------------------------------------------------------------- 図 7: 定常の背水曲線
Q_ST, N_ST, S_ST = m.QT_STEADY / m.BT, m.RNT, m.ST
HN_ST = (N_ST * Q_ST / math.sqrt(S_ST)) ** 0.6


def gvf_profile(y0, h0, y1, step=1.0):
    """漸変流の式 dh/dx = (S0 − Sf)/(1 − Fr²)(広い矩形・Manning)を、口からの距離 y0 の水深 h0 から上流の y1 まで
    RK4 で積分する(x は下流向き = 口からの距離の逆向き)"""
    def f(h):
        sf = N_ST ** 2 * Q_ST ** 2 / h ** (10.0 / 3.0)
        fr2 = Q_ST ** 2 / (G * h ** 3)
        return -(S_ST - sf) / (1.0 - fr2)
    ys, hs = [y0], [h0]
    y, h = y0, h0
    while y < y1 - 1e-9:
        d = min(step, y1 - y)
        k1 = f(h)
        k2 = f(h + 0.5 * d * k1)
        k3 = f(h + 0.5 * d * k2)
        k4 = f(h + d * k3)
        h += d * (k1 + 2 * k2 + 2 * k3 + k4) / 6.0
        y += d
        ys.append(y)
        hs.append(h)
    return np.array(ys), np.array(hs)


def steady_profiles():
    """(名前, 口からの距離, 水深, 理論の出発点) の並び"""
    out = []
    if os.path.exists("result_steady/E0006.txt"):
        E = np.loadtxt("result_steady/E0006.txt")
        h = np.array([E[j, COLS_T].mean() for j in ROWS_T]) - ZB_T
        out.append(("Δx = 20 m", Y_T, h))
    if os.path.exists("result_coarse_steady/E0006.txt"):          # 粗い格子は河道マスクの「直したもの」
        E = np.loadtxt("result_coarse_steady/E0006.txt")
        kc = np.loadtxt("data_coarse_fixed/kind.txt", dtype=int)
        zc = np.loadtxt("data_coarse_fixed/z.txt")
        rows = [j for j in range(mc.NYC) if kc[j, 25] == 3]
        y = np.array([mc.LYC - (j + 0.5) * mc.DXC - m.Y_MOUTH for j in rows])
        h = np.array([E[j, 25] - zc[j, 25] for j in rows])
        out.append(("Δx = 100 m", y, h))
    return out


def backwater_table():
    rows = []
    for name, y, h in steady_profiles():
        order = np.argsort(y)
        y, h = y[order], h[order]
        k0 = int(np.argmin(np.abs(y - 150.0)))
        yt, ht = gvf_profile(y[k0], h[k0], y.max())
        hti = np.interp(y[k0:], yt, ht)
        dev = h[k0:] - hti
        ext_c = float(y[k0:][(h[k0:] - HN_ST) >= 0.1].max())
        ext_t = float(yt[(ht - HN_ST) >= 0.1].max())
        rows.append((name, y[k0], h[k0], float(np.abs(dev).max()), ext_c, ext_t, y, h, yt, ht))
    return rows


def fig_backwater():
    rows = backwater_table()
    if not rows:
        return
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.8))
    cols = {"Δx = 20 m": "#1f5f8b", "Δx = 100 m": "#e08214"}
    for name, y0, h0, dmax, ext_c, ext_t, y, h, yt, ht in rows:
        axs[0].plot(y / 1000, h, "o" if "100" in name else "-", ms=3, color=cols[name], label=T(f"計算 {name}", f"model {name}"))
        axs[0].plot(yt / 1000, ht, "k:", lw=1.0)
        axs[1].semilogy(y / 1000, np.maximum(h - HN_ST, 1e-4), "o" if "100" in name else "-", ms=3, color=cols[name],
                        label=T(f"計算 {name}", f"model {name}"))
        axs[1].semilogy(yt / 1000, np.maximum(ht - HN_ST, 1e-4), "k:", lw=1.0)
    axs[0].plot([], [], "k:", label=T("1 次元の理論(漸変流の式)", "1-D theory (gradually varied flow)"))
    axs[0].axhline(HN_ST, color="#4d9221", lw=0.8, ls="--")
    axs[0].text(4.2, HN_ST + 0.08, T(f"等流水深 {HN_ST:.2f} m", f"normal depth {HN_ST:.2f} m"), fontsize=8, color="#4d9221")
    axs[0].set_xlabel(T("支川の口からの距離 (km)", "distance from the tributary mouth (km)"))
    axs[0].set_ylabel(T("水深 (m)", "depth (m)"))
    axs[0].legend(fontsize=8)
    axs[0].set_xlim(0, 6.2)
    axs[0].grid(alpha=0.3)
    axs[0].set_title(T("(a) 支川の水深(本川 1,500・支川 100 m³/s の定常)", "(a) Tributary depth (steady: main 1,500, tributary 100 m³/s)"),
                     fontsize=10, loc="left")
    le = 0.3 * HN_ST * (1 - Q_ST ** 2 / (G * HN_ST ** 3)) / S_ST
    axs[1].axhline(0.1, color="k", lw=0.6, ls="--")
    axs[1].text(0.1, 0.115, T("+0.1 m", "+0.1 m"), fontsize=8)
    axs[1].set_ylim(1e-3, 5)
    axs[1].set_xlim(0, 6.2)
    axs[1].set_xlabel(T("支川の口からの距離 (km)", "distance from the tributary mouth (km)"))
    axs[1].set_ylabel(T("等流水深からの上がり (m。対数)", "rise above the normal depth (m, log scale)"))
    axs[1].set_title(T(f"(b) 背水の上がりの減り方(減衰の長さ 0.3 h(1 − Fr²)/S = {le:.0f} m)",
                       f"(b) Decay of the rise (decay length 0.3 h(1 − Fr²)/S = {le:.0f} m)"), fontsize=10, loc="left")
    axs[1].grid(alpha=0.3, which="both")
    axs[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, "backwater.png"), dpi=120)
    plt.close(fig)


# ---------------------------------------------------------------- 図 8: 合流の形と水位
def jload(name, var, n):
    return np.loadtxt(f"junction/result_{name}/{var}{n:04d}.txt")


def jlast(name):
    fs = frames(name, d="junction")
    return int(os.path.basename(fs[-1])[1:5])


def angle_theory(dx, theta, qm, qt, h, x1, x3, h2):
    """1 次元の運動量の理論(支川の運動量の本川向き成分 = Q2² cos θ / (B2 h2))と損失なしの理論で、
    本川の x1 の水深を x3 の計算の水深から解く。h は本川の横断平均の水深の分布"""
    nx, ny, j0, ij = mj.angle_geom(dx)
    xc = (np.arange(nx) + 0.5) * dx
    xj = (ij - 0.5) * dx
    half = mj.BT / math.sin(math.radians(theta)) / 2
    Q = np.where(xc < xj - half, qm, np.where(xc > xj + half, qm + qt, qm + qt * (xc - (xj - half)) / (2 * half)))
    sf = mj.RN ** 2 * (Q / mj.BM) ** 2 / np.maximum(h, 0.01) ** (10.0 / 3.0)
    i1, i3 = int(np.argmin(np.abs(xc - x1))), int(np.argmin(np.abs(xc - x3)))
    seg = slice(i1, i3 + 1)
    force = np.trapezoid(G * mj.BM * (mj.S0 - sf[seg]) * h[seg], xc[seg])
    hf = np.trapezoid(sf[seg], xc[seg])
    L = xc[i3] - xc[i1]
    h3, q3 = h[i3], qm + qt
    M3 = G * mj.BM * h3 ** 2 / 2 + q3 ** 2 / (mj.BM * h3)
    trib = qt ** 2 / (mj.BT * h2) * math.cos(math.radians(theta))

    def bis(f, lo, hi):
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            if f(lo) * f(mid) <= 0:
                hi = mid
            else:
                lo = mid
        return 0.5 * (lo + hi)
    hc = ((qm / mj.BM) ** 2 / G) ** (1.0 / 3.0)
    hm = bis(lambda x: G * mj.BM * x * x / 2 + qm ** 2 / (mj.BM * x) + trib + force - M3, hc, 30.0)
    e3 = h3 + (q3 / mj.BM) ** 2 / (2 * G * h3 ** 2)
    he = bis(lambda x: x + (qm / mj.BM) ** 2 / (2 * G * x * x) - (e3 + hf - mj.S0 * L), hc, 30.0)
    return hm, he


def angle_table():
    rows = []
    for name, dx, theta, qm, qt in (("a45", 10.0, 45, 600, 400), ("a90", 10.0, 90, 600, 400), ("a135", 10.0, 135, 600, 400),
                                    ("b45", 10.0, 45, 300, 700), ("b90", 10.0, 90, 300, 700), ("b135", 10.0, 135, 300, 700),
                                    ("fa90", 5.0, 90, 600, 400), ("fa135", 5.0, 135, 600, 400)):
        if not have(name, "junction"):
            continue
        n = jlast(name)
        H, E = jload(name, "H", n), jload(name, "E", n)
        Ep = jload(name, "E", n - 1)
        nx, ny, j0, ij = mj.angle_geom(dx)
        nb = int(mj.BM / dx)
        h = H[j0:j0 + nb, :].mean(axis=0)
        e = E[j0:j0 + nb, :].mean(axis=0)
        ep = Ep[j0:j0 + nb, :].mean(axis=0)
        xc = (np.arange(nx) + 0.5) * dx
        xj = (ij - 0.5) * dx
        x1, x3 = xj - 150.0, xj + 200.0
        i1 = int(np.argmin(np.abs(xc - x1)))
        # 支川の口から 100 m の水位と水深(中心線の両側の平均)
        d = {90: (0.0, -1.0), 45: (-1 / math.sqrt(2), -1 / math.sqrt(2)), 135: (1 / math.sqrt(2), -1 / math.sqrt(2))}[theta]
        ym0 = j0 * dx
        nn = (-d[1], d[0])
        vals_e, vals_h = [], []
        for w in np.arange(-mj.BT / 2 + dx / 2, mj.BT / 2 - dx / 2 + 1e-6, dx / 2):
            xx = xj + d[0] * 100.0 + nn[0] * w
            yy = ym0 + d[1] * 100.0 + nn[1] * w
            vals_e.append(E[int(yy // dx), int(xx // dx)])
            vals_h.append(H[int(yy // dx), int(xx // dx)])
        hm, he = angle_theory(dx, theta, qm, qt, h, x1, x3, float(np.mean(vals_h)))
        p = (h[i1] - he) / (hm - he) if hm > he + 1e-3 else float("nan")
        u = jload(name, "u", n)
        v = jload(name, "v", n)
        vmax_opp = float(np.hypot(u, v)[j0 + nb - 1, ij - 5:ij + 40].max())
        rows.append(dict(name=name, dx=dx, theta=theta, qm=qm, qt=qt, e_main=e[i1], e_trib=float(np.mean(vals_e)),
                         h1=h[i1], hm=hm, he=he, p=p, vopp=vmax_opp, steady=float(np.max(np.abs(e - ep)[5:-5]))))
    return rows


def bend_values():
    out = {}
    for kind in ("none", "outer", "inner"):
        name = f"bend_{kind}"
        if not have(name, "junction"):
            continue
        n = jlast(name)
        E, H = jload(name, "E", n), jload(name, "H", n)
        nx, ny, dx = mj.bend_geom()
        ur = (math.cos(math.pi / 4), math.sin(math.pi / 4))

        def at(x, y):
            return E[ny - 1 - int(y // dx), int(x // dx)]
        r_in, r_out = mj.RB - mj.BB / 2 + 5, mj.RB + mj.BB / 2 - 5
        cross = at(mj.XC + r_out * ur[0], mj.YC + r_out * ur[1]) - at(mj.XC + r_in * ur[0], mj.YC + r_in * ur[1])
        prof = None
        if kind != "none":
            d = ur if kind == "outer" else (-ur[0], -ur[1])
            ax0, ay0 = mj.XC + mj.RB * ur[0], mj.YC + mj.RB * ur[1]
            ss, ee = [], []
            for st in np.arange(10.0, 551.0, 10.0):
                x = ax0 + d[0] * (mj.BB / 2 + st)
                y = ay0 + d[1] * (mj.BB / 2 + st)
                i, j = int(x // dx), ny - 1 - int(y // dx)
                if 0 <= i < nx and 0 <= j < ny:
                    ss.append(st)
                    ee.append(E[j, i])
            prof = (np.array(ss), np.array(ee))
        out[kind] = (cross, prof)
    return out


def fig_junction():
    rows = angle_table()
    bend = bend_values()
    if not rows and not bend:
        return
    fig = plt.figure(figsize=(13, 9.5))
    # (a) 合流角ごとの水深と流速(流量比 b)
    for k, th in enumerate((45, 90, 135)):
        name = f"b{th}"
        if not have(name, "junction"):
            continue
        ax = fig.add_axes([0.04 + 0.31 * k, 0.70, 0.27, 0.25])
        n = jlast(name)
        H, u, v = jload(name, "H", n), jload(name, "u", n), jload(name, "v", n)
        i0, i1, j0, j1 = 128, 185, 100, 131
        im = ax.imshow(np.where(H > 0.01, H, np.nan)[j0:j1, i0:i1], extent=(i0 * 10, i1 * 10, -j1 * 10, -j0 * 10),
                       cmap="viridis", vmin=3.0, vmax=5.5)
        X, Y = np.meshgrid((np.arange(i0, i1) + 0.5) * 10, -(np.arange(j0, j1) + 0.5) * 10)
        sk = (slice(1, None, 2), slice(1, None, 2))
        msk = H[j0:j1, i0:i1] > 0.01
        ax.quiver(X[sk], Y[sk], np.where(msk, u[j0:j1, i0:i1], np.nan)[sk], np.where(msk, -v[j0:j1, i0:i1], np.nan)[sk],
                  scale=45, width=0.005, color="w")
        ax.set_xticks([])
        ax.set_yticks([])
        pre = "(a) " if k == 0 else ""
        ax.set_title(pre + T(f"合流角 {th}°(本川 300・支川 700 m³/s)", f"junction angle {th}° (main 300, tributary 700 m³/s)"), fontsize=9)
    cax = fig.add_axes([0.965, 0.71, 0.008, 0.23])
    cb = fig.colorbar(im, cax=cax)
    cb.set_label(T("水深 (m)", "depth (m)"), fontsize=8)
    # (b) 合流角と本川の上流の水深(計算と理論)
    ax = fig.add_axes([0.06, 0.38, 0.40, 0.26])
    for qm, qt, mk, lab in ((600, 400, "o", T("本川 600・支川 400", "main 600, trib. 400")), (300, 700, "s", T("本川 300・支川 700", "main 300, trib. 700"))):
        rr = [r for r in rows if r["qm"] == qm and r["dx"] == 10.0]
        if not rr:
            continue
        ths = [r["theta"] for r in rr]
        ax.plot(ths, [r["h1"] for r in rr], mk + "-", color="#1f5f8b", label=T(f"計算 Δx = 10 m・{lab}", f"model Δx = 10 m, {lab}"))
        ax.plot(ths, [r["hm"] for r in rr], mk + "--", color="#c0392b", mfc="none", label=T(f"運動量の理論・{lab}", f"momentum theory, {lab}"))
        ax.plot(ths, [r["he"] for r in rr], mk + ":", color="k", mfc="none", label=T(f"損失なし・{lab}", f"no loss, {lab}"))
        rf = [r for r in rows if r["qm"] == qm and r["dx"] == 5.0]
        if rf:
            ax.plot([r["theta"] for r in rf], [r["h1"] for r in rf], mk, color="#e08214", ms=8,
                    label=T(f"計算 Δx = 5 m・{lab}", f"model Δx = 5 m, {lab}"))
    ax.set_xticks([45, 90, 135])
    ax.set_xlabel(T("合流角 (°)", "junction angle (°)"))
    ax.set_ylabel(T("合流の 150 m 上流の本川の水深 (m)", "main-river depth 150 m above the junction (m)"))
    ax.legend(fontsize=6.5, ncol=2, loc="upper left")
    ax.grid(alpha=0.3)
    ax.set_title(T("(b) 合流角と本川の上流の水深(下流の等流水深 3.86 m)", "(b) Junction angle and upstream main-river depth (downstream normal depth 3.86 m)"),
                 fontsize=10, loc="left")
    # (c) 数表
    ax = fig.add_axes([0.52, 0.38, 0.46, 0.26])
    ax.axis("off")
    cell = [[T("格子", "grid"), T("流量比", "flows"), T("角度", "angle"), T("本川の上流\nの水位 (m)", "main up-\nstream (m)"),
             T("支川の口\nの水位 (m)", "tributary\nmouth (m)"), T("対岸の最大\n流速 (m/s)", "max. vel.\nopp. bank"), "p"]]
    for r in rows:
        cell.append([f"{r['dx']:g} m", f"{r['qm']}:{r['qt']}", f"{r['theta']}°", f"{r['e_main']:.2f}", f"{r['e_trib']:.2f}",
                     f"{r['vopp']:.2f}", "—" if math.isnan(r["p"]) else f"{r['p']:.2f}"])
    tb = ax.table(cellText=cell, loc="center", cellLoc="center")
    tb.auto_set_font_size(False)
    tb.set_fontsize(7.5)
    tb.scale(1, 1.25)
    ax.set_title(T("(c) p = 合流の損失の位置(0 = 損失なし、1 = 運動量の理論)", "(c) p = junction loss (0 = no loss, 1 = momentum theory)"), fontsize=9)
    # (d) 湾曲
    for k, kind in enumerate(("outer", "inner")):
        name = f"bend_{kind}"
        if not have(name, "junction"):
            continue
        ax = fig.add_axes([0.04 + 0.22 * k, 0.04, 0.20, 0.28])
        n = jlast(name)
        E, H, u, v = jload(name, "E", n), jload(name, "H", n), jload(name, "u", n), jload(name, "v", n)
        nx, ny, dx = mj.bend_geom()
        jj0, jj1, ii0, ii1 = 10, 120, 60, 175
        im2 = ax.imshow(np.where(H > 0.01, E, np.nan)[jj0:jj1, ii0:ii1], extent=(ii0 * 10, ii1 * 10, (ny - jj1) * 10, (ny - jj0) * 10),
                        cmap="RdYlBu_r", vmin=12.3, vmax=13.3)
        X, Y = np.meshgrid((np.arange(ii0, ii1) + 0.5) * 10, (ny - np.arange(jj0, jj1) - 0.5) * 10)
        sk = (slice(1, None, 4), slice(1, None, 4))
        msk = H[jj0:jj1, ii0:ii1] > 0.01
        ax.quiver(X[sk], Y[sk], np.where(msk, u[jj0:jj1, ii0:ii1], np.nan)[sk], np.where(msk, -v[jj0:jj1, ii0:ii1], np.nan)[sk],
                  scale=60, width=0.004)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title({"outer": T("湾曲の外岸に合流", "joins the outer bank"), "inner": T("湾曲の内岸に合流", "joins the inner bank")}[kind], fontsize=9)
    if "outer" in bend:
        cax = fig.add_axes([0.465, 0.06, 0.008, 0.24])
        cb = fig.colorbar(im2, cax=cax)
        cb.set_label(T("水位 (m)", "water level (m)"), fontsize=8)
    ax = fig.add_axes([0.60, 0.06, 0.37, 0.25])
    for kind, col in (("outer", "#c0392b"), ("inner", "#1f5f8b")):
        if kind in bend and bend[kind][1] is not None:
            ss, ee = bend[kind][1]
            ax.plot(ss, ee, color=col, label={"outer": T("外岸の支川", "tributary on the outer bank"), "inner": T("内岸の支川", "tributary on the inner bank")}[kind])
    ax.set_xlabel(T("支川の口からの距離 (m)", "distance from the tributary mouth (m)"))
    ax.set_ylabel(T("支川の水位 (m)", "tributary water level (m)"))
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    ax.set_title(T("(d) 湾曲部(半径 300 m)の外岸・内岸に入る支川の水位(本川 900・支川 100 m³/s)",
                   "(d) Tributary level, outer vs inner bank of a bend (r = 300 m; main 900, trib. 100 m³/s)"),
                 fontsize=9, loc="left")
    fig.savefig(os.path.join(FIGDIR, "junction.png"), dpi=110)
    plt.close(fig)


# ---------------------------------------------------------------- 数表
def tables():
    print("== 表 1 本編のケース(支川の最大水位は列の平均。浸水面積は最大水深 0.1 m 以上の堤内地)")
    print("ケース        本川の水位(北岸/南岸) 支川 200 m  観測所  支川の口の流量(最小/最大)  堤内地の最大水量  浸水面積  最大水深  越水の上流端  P7/P8 の最大水深")
    for c, lab, _, _ in CASES + MEASURES[1:]:
        if not have(c):
            continue
        _, e1, _ = probe(c, 1)
        _, e2, _ = probe(c, 2)
        _, e4, _ = probe(c, 4)
        _, e5, _ = probe(c, 5)
        _, q1 = flux(c, 1)
        _, v = fp_volume(c)
        hm = np.loadtxt(f"result_{c}/H9999.txt")
        area = float(((hm > 0.1) & FP).sum()) * m.DX * m.DX / 1e6
        crest = CREST_T if c != "raise" else np.array([np.loadtxt("data/z_raise.txt")[j, 127] for j in ROWS_T])
        ext = overflow_extent(c, crest)
        _, _, h7 = probe(c, 7)
        _, _, h8 = probe(c, 8)
        print(f"{c:6s} {e1.max():7.2f} / {e2.max():6.2f}      {e4.max():6.2f}   {e5.max():6.2f}    {q1.min():7.0f} / {q1.max():5.0f}"
              f"            {v.max() / 1e6:6.2f} 百万 m3   {area:5.2f} km2  {hm[FP].max():5.2f} m   {ext:6.0f} m    {h7.max():5.2f} / {h8.max():5.2f} m")
    print("== 表 2 粗い格子(Δx = 100 m)の河道マスクの作り方 3 通り(合流点の本川の水位は北岸の P1。"
          "時刻ごとの差は粗い − 細かい)")
    for c in ("main", "same"):
        if not have(c):
            continue
        _, v = fp_volume(c)
        hm = np.loadtxt(f"result_{c}/H9999.txt")
        a = float(((hm > 0.1) & FP).sum()) * m.DX * m.DX / 1e6
        t1, e1, _ = probe(c, 1)
        print(f"  {c} Δx = 20 m: 合流点の本川の最高水位 {e1.max():.2f} m、堤内地の最大水量 {v.max() / 1e6:.2f} 百万 m3、"
              f"浸水面積 {a:.2f} km2、最大水深 {hm[FP].max():.2f} m")
        for r in mc.METHODS:
            if not have(f"coarse_{c}_{r}"):
                continue
            kc = coarse_data(r)[0]
            _, vc = fp_volume(f"coarse_{c}_{r}", kind=kc, area=mc.DXC * mc.DXC)
            hc = np.loadtxt(f"result_coarse_{c}_{r}/H9999.txt")
            ac = float(((hc > 0.1) & (kc == 5)).sum()) * mc.DXC * mc.DXC / 1e6
            tc1, ec1, _ = probe(f"coarse_{c}_{r}", 1)
            print(f"  {c} {r:6s}: 合流点の本川の最高水位 {ec1.max():.2f} m({ec1.max() - e1.max():+.2f})、"
                  f"堤内地の最大水量 {vc.max() / 1e6:.2f} 百万 m3({vc.max() / v.max():.2f} 倍)、"
                  f"浸水面積 {ac:.2f} km2({ac / a:.2f} 倍)、最大水深 {hc[kc == 5].max():.2f} m")
            hh = (3.0, 4.0, 5.0, 6.0, 7.0, 8.0)
            print("      P1 の時刻ごとの差: " + "、".join(
                f"{h:.0f} h {np.interp(h * 60, tc1, ec1) - np.interp(h * 60, t1, e1):+.2f} m" for h in hh))
    rows = backwater_table()
    if rows:
        print(f"== 表 3 定常の背水曲線(等流水深 {HN_ST:.3f} m。理論は口から 150 m 前後の計算の水深から上流へ積分)")
        for name, y0, h0, dmax, ext_c, ext_t, *_ in rows:
            print(f"  {name}: 出発点 {y0:.0f} m・水深 {h0:.3f} m、理論との差の最大 {dmax:.3f} m、背水(+0.1 m)の範囲 計算 {ext_c:.0f} m・理論 {ext_t:.0f} m")
    rows = angle_table()
    if rows:
        print("== 表 4 合流角(本川の上流 = 合流点の 150 m 上流、支川の口 = 口から 100 m の水位。p = (h − 損失なし)/(運動量 − 損失なし))")
        for r in rows:
            print(f"  {r['name']:6s} Δx {r['dx']:4.0f} m {r['qm']}:{r['qt']} {r['theta']:3d}°  本川の上流 {r['e_main']:.3f} m  支川の口 {r['e_trib']:.3f} m  "
                  f"水深 {r['h1']:.3f}(理論 運動量 {r['hm']:.3f}・損失なし {r['he']:.3f}、p = {r['p']:.2f})  対岸の最大流速 {r['vopp']:.2f} m/s  "
                  f"最後の 30 分の変化 {r['steady']:.4f} m")
    bend = bend_values()
    if bend:
        print("== 表 5 湾曲(頂点の横断の水位差 = 外岸 − 内岸、支川の口から 50 m・500 m の水位)")
        for kind, (cross, prof) in bend.items():
            s = f"  {kind:6s} 横断の水位差 {cross:.3f} m"
            if prof is not None:
                ss, ee = prof
                s += f"  支川 50 m {np.interp(50, ss, ee):.3f} m・500 m {np.interp(500, ss, ee):.3f} m"
            print(s)
        u = 1000.0 / (mj.BB * mj.hn(1000.0 / mj.BB))
        print(f"  参考: U²B/(g r) = {u * u * mj.BB / (G * mj.RB):.3f} m(U = {u:.2f} m/s)")


def main():
    fig_mechanism()
    fig_setup()
    fig_maps()
    fig_profiles()
    fig_series()
    fig_measures()
    fig_coarse_masks()
    fig_coarse()
    fig_backwater()
    fig_junction()
    if not EN:
        tables()


if __name__ == "__main__":
    main()
