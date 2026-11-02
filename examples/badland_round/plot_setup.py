#!/usr/bin/env python3
"""examples/badland_round の機構の模式図と設定の図(計算結果は使わない)。

  python3 plot_setup.py        # figs/mechanism.png, figs/setup.png
  python3 plot_setup.py en     # 英語ラベル版を en/figs/ に描く

  figs/mechanism.png  (a) 移流型(乾式斜面侵食)と拡散型(クリープ)が作る丘の形、
                      (b) 長さ尺度 L と丘の大きさ、(c) 硬軟の互層と L の比で決まる段と縞
  figs/setup.png      初期地形(平面)と 4 つの丘の頂を通る横断(互層の帯つき)、設定の要約

入力は make_terrain.py が書く z.txt(make で作る)。
依存: numpy, matplotlib
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)

C_SOFT, C_HARD, C_ERODE, C_CREEP = "#d9c49c", "#9c8a6a", "#c0392b", "#2c7fb8"


def _arrow(ax, x0, y0, x1, y1, color, lw=1.4, style="-|>", ms=9):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw, shrinkA=0, shrinkB=0, mutation_scale=ms))


def _hill(ax, x, z, color=C_SOFT):
    ax.fill_between(x, 0, z, color=color, zorder=1)
    ax.plot(x, z, "k-", lw=1.2, zorder=2)


def _advective(ax):
    """移流型: 勾配のべき乗で削れ、凹部で速い → 尖った稜線、直線〜凹の側面。"""
    x = np.linspace(-10, 10, 401)
    z = np.maximum(8.0 - 1.15 * np.abs(x) ** 1.0 - 0.02 * x ** 2, 0.0)
    _hill(ax, x, z)
    for xi in (-6, -4, -2, 2, 4, 6):
        zi = np.interp(xi, x, z)
        n = np.array([np.sign(xi) * 1.15, 1.0]); n /= np.hypot(*n)
        ln = 1.6 + 0.35 * abs(xi)
        _arrow(ax, xi + n[0] * ln, zi + n[1] * ln, xi + n[0] * 0.15, zi + n[1] * 0.15, C_ERODE)
    ax.text(0, 9.3, T("尖った稜線", "sharp crest"), ha="center", fontsize=8.5)
    ax.text(0, -2.3, T("侵食 ∝ P k_t S^h(1 + c_b κ)\n急な側面ほど速く削れる", "erosion ∝ P k_t S^h (1 + c_b κ)\nsteeper sides erode faster"),
            ha="center", fontsize=8, color=C_ERODE, va="top")
    ax.set_title(T("移流型(乾式斜面侵食): 尖る", "Advective (dry-slope erosion): sharpens"), fontsize=9.5)


def _diffusive(ax):
    """拡散型: 勾配に比例した流束で土が下る → 上に凸の丸い頂。"""
    x = np.linspace(-10, 10, 401)
    z = np.maximum(7.0 * (1 - (x / 9.0) ** 2), 0.0)
    _hill(ax, x, z)
    for xi in (-6.5, -3.5, 3.5, 6.5):
        zi = np.interp(xi, x, z)
        s = -14.0 * xi / 81.0
        t = np.array([np.sign(xi), -abs(s)]); t /= np.hypot(*t)
        _arrow(ax, xi - 1.2 * t[0], zi + 0.35 - 1.2 * t[1], xi + 1.2 * t[0], zi + 0.35 + 1.2 * t[1], C_CREEP)
    ax.text(0, 8.2, T("丸い頂(上に凸)", "rounded, convex crest"), ha="center", fontsize=8.5)
    ax.text(0, -2.3, T("流束 q = −D ∇z(クリープ)\n頂から裾へ土を運ぶ", "flux q = −D ∇z (creep)\ncarries soil from crest to foot"),
            ha="center", fontsize=8, color=C_CREEP, va="top")
    ax.set_title(T("拡散型(クリープ): 丸める", "Diffusive (creep): rounds"), fontsize=9.5)


def _scale(ax):
    """長さ尺度 L と丘の大きさ。L より小さい丘は全体がドーム、大きい丘は頂だけ丸い。"""
    L = 4.0
    for x0, R, lab in ((-16, 3.0, T("丘の半径 < L:\n全体がドーム", "hill radius < L:\nall dome")),
                       (-1, 5.0, T("半径 ≈ L:\n丸いマウンド", "radius ≈ L:\nrounded mound")),
                       (18, 9.5, T("半径 > L: 頂だけ丸く\n側面は直線で刻まれる", "radius > L: only the top\nrounds; straight sides gullied"))):
        x = np.linspace(x0 - R - 1, x0 + R + 1, 400)
        r = np.abs(x - x0)
        S = 0.9
        rc = min(L, R) * 0.9
        zc = R * S * 0.55 + rc * S / 2
        z = np.where(r < rc, zc - S * r ** 2 / (2 * rc), zc - S * rc / 2 - S * (r - rc))
        z = np.maximum(z, 0.0)
        _hill(ax, x, z)
        ax.text(x0, -1.0, lab, ha="center", va="top", fontsize=8)
    ax.annotate("", xy=(18 - L * 0.9, 9.6), xytext=(18 + L * 0.9, 9.6),
                arrowprops=dict(arrowstyle="<->", color=C_CREEP, lw=1.1))
    ax.text(18, 10.2, T("丸い部分の幅 ~ L", "rounded part ~ L"), ha="center", fontsize=8, color=C_CREEP)
    ax.text(-21, 11.3, T("L = D / (P k_t S^(h−1)): 拡散(クリープ)と移流(下刻)の比の長さ",
                         "L = D / (P k_t S^(h−1)): length set by diffusion (creep) over advection (incision)"),
            fontsize=8.5)
    ax.set_xlim(-21, 30)
    ax.set_ylim(-5.5, 12.5)
    ax.axis("off")
    ax.set_title(T("(b) 長さ尺度 L と丘の大きさ: 低い(小さい)丘ほど丸い", "(b) Length scale L and hill size: lower (smaller) hills are rounder"),
                 loc="left", fontsize=10)


def _strata(ax, kind):
    """硬軟の互層。kind: none(クリープなし)= 段、thin(層厚 < L)= 縞だけ、thick(層厚 > L)= 丸い段。"""
    x = np.linspace(0, 12, 600)
    t = 2.0
    for k in range(5):
        ax.axhspan(k * 2 * t + t, k * 2 * t + 2 * t, color=C_HARD, alpha=0.35, lw=0)
    if kind == "none":
        z = np.zeros_like(x)
        for k, xb in enumerate(np.arange(1.2, 12, 2.2)):
            z = np.where(x > xb, z, z)
        steps = []
        zz = 12.0
        xs = 0.0
        pts = [(0, 12)]
        for k in range(3):
            pts += [(xs + 1.6, zz), (xs + 2.0, zz - t)]
            xs += 2.0; zz -= t
            pts += [(xs + 1.4, zz), (xs + 2.6, zz - t)]
            xs += 2.6; zz -= t
        px, pz = zip(*pts)
        z = np.interp(x, px, pz, right=0.0)
        title = T("クリープなし: 軟層が削れ、硬層の上面に段", "No creep: soft beds retreat, benches on hard beds")
    elif kind == "thick":
        z = 12.0 - x * 1.0 + 0.55 * np.sin(2 * np.pi * (x - 0.3) / 4.0)
        title = T("層厚 > L: 段が丸まって残る", "Bed thickness > L: rounded steps remain")
    else:
        z = 12.0 - x * 1.0 + 0.12 * np.sin(2 * np.pi * (x - 0.3) / 4.0)
        title = T("層厚 ≪ L: 段は消え、縞だけ", "Bed thickness ≪ L: no steps, bands only")
    z = np.clip(z, 0, None)
    ax.fill_between(x, 0, z, color=C_SOFT, alpha=0.75)
    ax.plot(x, z, "k-", lw=1.2)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 13)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(title, fontsize=8.5)


def mechanism():
    fig = plt.figure(figsize=(13, 10))
    gs = fig.add_gridspec(3, 6, height_ratios=[1, 1.05, 0.9], hspace=0.55, wspace=0.35, top=0.87)
    a1 = fig.add_subplot(gs[0, 0:3]); _advective(a1)
    a2 = fig.add_subplot(gs[0, 3:6]); _diffusive(a2)
    for a in (a1, a2):
        a.set_xlim(-12, 12); a.set_ylim(-5.5, 10.5); a.axis("off")
    fig.text(0.125, 0.905, T("(a) 丘の形を決める 2 つの型", "(a) Two kinds of process that shape a hill"), fontsize=10)
    _scale(fig.add_subplot(gs[1, :]))
    axs = [fig.add_subplot(gs[2, 2 * k:2 * k + 2]) for k in range(3)]
    for a, kind in zip(axs, ("none", "thick", "thin")):
        _strata(a, kind)
    axs[0].text(0, 15.2, T("(c) 硬軟の互層(灰色 = 硬層。乾式侵食だけを遅くする)と、クリープの長さ L",
                           "(c) Alternating hard and soft beds (grey = hard; slows dry erosion only) and the creep length L"),
                fontsize=10)
    fig.savefig(f"{FIGDIR}/mechanism.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


def setup():
    z = np.loadtxt("z.txt")
    ny, nx = z.shape
    dx = 176.0 / nx
    ext = [0, nx * dx, 0, ny * dx]
    fig = plt.figure(figsize=(14, 6.6))
    gs = fig.add_gridspec(2, 3, width_ratios=[1.65, 0.16, 1], height_ratios=[1, 1], wspace=0.15, hspace=0.45)
    ax = fig.add_subplot(gs[0, 0])
    im = ax.imshow(z, origin="lower", extent=ext, cmap="terrain", vmin=-6, vmax=26)
    for xc, H in ((35, 24), (90, 15), (128, 9), (154, 5)):
        ax.text(xc, 74, "H₀ = %d m" % H, ha="center", fontsize=8)
    ax.axhline(40, color="k", lw=0.6, ls="--")
    ax.set_ylim(0, 80)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title(T("初期地形: 平地(z = 0 = 侵食基準面)に円錐丘 4 つ(側面 tanθ = 0.8、丘の上に白色雑音 ±0.4 m)",
                   "Initial terrain: four cones on a plain (z = 0 = base level; sides tanθ = 0.8, white noise ±0.4 m on the hills)"),
                 fontsize=9)
    fig.colorbar(im, ax=ax, shrink=0.8).set_label(T("地盤高 (m)", "elevation (m)"))
    ax = fig.add_subplot(gs[1, 0])
    x = (np.arange(nx) + 0.5) * dx
    ax.fill_between(x, 0, z[ny // 2], color="#d9c49c", alpha=0.8)
    ax.plot(x, z[ny // 2], "k-", lw=1.2)
    ax.set_xlim(0, 176)
    ax.set_ylim(0, 26)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("z (m)")
    ax.set_title(T("4 つの丘の頂を通る横断(y = 40 m)", "Section through the four summits (y = 40 m)"), fontsize=9)
    # 互層の柱状図(互層のケースだけ。灰色 = 硬層、倍率 0.3)
    ax = fig.add_subplot(gs[1, 1])
    for k in range(16):
        ax.add_patch(plt.Rectangle((0.0, 3 * k + 1.5), 0.45, 1.5, color="0.45"))
    for k in range(8):
        ax.add_patch(plt.Rectangle((0.55, 6 * k + 3), 0.45, 3.0, color="0.45"))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 26)
    ax.set_xticks([0.225, 0.775])
    ax.set_xticklabels(["1.5 m", "3 m"], fontsize=8)
    ax.set_yticklabels([])
    ax.set_title(T("互層\n(灰 = 硬層)", "strata\n(grey = hard)"), fontsize=8)
    ax = fig.add_subplot(gs[:, 2])
    ax.axis("off")
    rows = [
        (T("領域", "domain"), T("176 × 80 m、Δx = 1 m", "176 × 80 m, Δx = 1 m")),
        (T("降雨・浸透", "rain"), T("一様 10 mm/h を継続、Green-Ampt 36 mm/h\n→ 全量浸透(表面流ゼロ)", "uniform 10 mm/h, Green-Ampt 36 mm/h\n→ all infiltrates (no surface flow)")),
        (T("乾式侵食", "dry erosion"), T("f_splash(badland と同じ係数)\nk_r 2e-4, k_t 0.05, h 1.5, c_b 32 m, ℓ 2 m", "f_splash (same as badland)\nk_r 2e-4, k_t 0.05, h 1.5, c_b 32 m, ℓ 2 m")),
        (T("クリープ", "creep"), T("D = 0 / 3e-7 / 1e-6 / 3e-6 m²/s\n(L ≈ 0 / 2.4 / 8 / 24 m)", "D = 0 / 3e-7 / 1e-6 / 3e-6 m²/s\n(L ≈ 0 / 2.4 / 8 / 24 m)")),
        (T("互層", "strata"), T("厚さ 1.5 m(16 層)/ 3 m(8 層)\n軟層 1、硬層 0.3 の倍率", "1.5 m (16 beds) / 3 m (8 beds)\nfactor 1 soft, 0.3 hard")),
        (T("時間", "time"), T("dt 2 s、地形更新 2 s ごと × morfac 500\n24 h = T_geo 4.3×10⁷ s、2 h ごとに Z", "dt 2 s, update every 2 s × morfac 500\n24 h = T_geo 4.3×10⁷ s, Z every 2 h")),
    ]
    yv = 0.97
    for k, v in rows:
        ax.text(0.0, yv, k, fontsize=9, va="top", color="0.2")
        ax.text(0.27, yv, v, fontsize=9, va="top")
        yv -= 0.085 + 0.06 * v.count("\n")
    ax.set_title(T("設定の要約", "Summary of settings"), fontsize=9, loc="left")
    fig.savefig(f"{FIGDIR}/setup.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    mechanism()
    setup()
    print(f"{FIGDIR}/mechanism.png, {FIGDIR}/setup.png written")
