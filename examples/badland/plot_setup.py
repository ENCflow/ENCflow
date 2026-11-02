#!/usr/bin/env python3
"""examples/badland の機構の模式図と設定の図(計算結果は使わない)。

  python3 plot_setup.py        # figs/mechanism.png, figs/setup.png
  python3 plot_setup.py en     # 英語ラベル版を en/figs/ に描く

  figs/mechanism.png  (a) 台地と崖の縦断の模式図(全量浸透・雨滴のはね・粒子の転落・
                      海への排出・侵食基準面)、(b) 崖面を横切る断面の模式図(凹部ほど
                      速く削れる)、(c) 擾乱の成長率と谷の間隔(線形理論)
  figs/setup.png      主ケースの地形(平面)、縦断(主ケースと系列の地形)、崖縁の白色雑音

入力は make_terrain.py が書く z_main.txt / sw_main.txt / z_sweep.txt(make で作る)。
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

C_GROUND, C_SEA, C_RAIN, C_GRAIN, C_ERODE = "#c9b48a", "#6fa8dc", "#2c7fb8", "#8c510a", "#c0392b"


def _arrow(ax, x0, y0, x1, y1, color, lw=1.6, style="-|>", ms=10):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw, shrinkA=0, shrinkB=0, mutation_scale=ms))


def _profile(ax):
    """台地 → 崖 → 海の縦断(主ケースの寸法。発達後の谷底は結果の縦断を模したもの)。"""
    x = np.linspace(0, 120, 601)
    z = np.where(x < 60, 30.0, np.maximum(30.0 - 1.5 * (x - 60), 0.0))
    ax.fill_between(x, -6, z, color=C_GROUND, zorder=1)
    ax.fill_between(x, 0, -6, where=x >= 80, color=C_SEA, alpha=0.8, zorder=2)
    ax.plot(x, z, "k-", lw=1.2, zorder=3)
    # 発達後の谷底(谷頭が台地へ食い込む)
    xv = [0, 24, 26, 29, 80]
    zv = [30, 30, 24, 4, 0]
    ax.plot(xv, zv, color=C_ERODE, ls="--", lw=1.4, zorder=3)
    ax.text(31, 9.5, T("発達後の谷底:\n谷頭が台地へ後退する", "valley floor later on:\nthe valley head cuts back"),
            color=C_ERODE, fontsize=8, va="center")
    # 雨と浸透
    for xi in np.arange(4, 118, 7.5):
        _arrow(ax, xi, 41, xi - 0.8, 36.5, C_RAIN, lw=1.0, ms=7)
    ax.text(2, 42.5, T("一様な雨 10 mm/h(地形時間を通して降り続ける)", "uniform rain 10 mm/h (throughout the landform time)"),
            fontsize=8.5, color=C_RAIN)
    for xi in (8, 20, 44):
        _arrow(ax, xi, 28.5, xi, 23.5, C_RAIN, lw=1.4, ms=8)
    ax.text(3, 20.0, T("雨は全量しみ込む\n(浸透能 36 mm/h > 10 mm/h):\n地表流は生じない",
                       "all rain soaks in\n(capacity 36 mm/h > 10 mm/h):\nno overland flow"),
            fontsize=8, color=C_RAIN, va="top")
    # 雨滴のはね(台地の上でも働く)
    for xc in (36, 50):
        t = np.linspace(0, 1, 20)
        ax.plot(xc + 3 * t, 30 + 2.2 * np.sin(np.pi * t), color=C_GRAIN, lw=1.0)
        ax.plot(xc - 3 * t, 30 + 2.2 * np.sin(np.pi * t), color=C_GRAIN, lw=1.0)
    ax.text(33, 33.3, T("雨滴のはね(k_r。台地の上でも)", "raindrop splash (k_r, also on the plateau)"),
            fontsize=8, color=C_GRAIN)
    # 崖面を転がり落ちる粒子(sandball・dry ravel)
    for xi in (63, 68.5, 74):
        zi = 30 - 1.5 * (xi - 60)
        ax.add_patch(plt.Circle((xi + 0.9, zi + 1.0), 0.75, color=C_GRAIN, zorder=4))
        _arrow(ax, xi + 1.8, zi - 0.2, xi + 4.2, zi - 3.8, C_GRAIN, lw=1.3, ms=8)
    ax.text(70, 24, T("乾いた粒子が急斜面を転がり落ちる\n(k_t S^h。凹部で増幅 1 + c_b κ)",
                      "dry grains roll down the steep face\n(k_t S^h, amplified in hollows by 1 + c_b κ)"),
            fontsize=8, color=C_GRAIN)
    # 系外へ
    _arrow(ax, 80, 1.6, 95, 1.6, C_GRAIN, lw=1.8)
    ax.text(82, 2.4, T("剥離した土砂は系外へ\n(海が運び去る)", "detached sediment leaves the domain\n(the sea removes it)"),
            fontsize=8, color=C_GRAIN)
    ax.axhline(0, color="k", lw=0.8, ls=":")
    ax.text(96, -3.0, T("海 = 侵食基準面 z = 0(spl_zbase)\n谷底はこれより下がらない",
                        "sea = base level z = 0 (spl_zbase)\nvalley floors stop here"), fontsize=8, va="center")
    ax.text(10, 31.2, T("台地 30 m", "plateau 30 m"), fontsize=8.5)
    ax.text(62, 9, T("崖 56°", "cliff 56°"), fontsize=8.5)
    ax.set_xlim(0, 120)
    ax.set_ylim(-6, 45)
    ax.set_xlabel(T("x (m)  台地 → 崖 → 海", "x (m)  plateau → cliff → sea"))
    ax.set_ylabel("z (m)")
    ax.set_title(T("(a) 台地と崖の縦断: 表面流なしで谷を刻む過程", "(a) Plateau and cliff in profile: valleys cut without overland flow"),
                 loc="left", fontsize=10)


def _cross(ax):
    """崖面を横切る断面(y 方向)。凹部ほど侵食が速い(凹地形増幅)。"""
    y = np.linspace(0, 40, 801)
    z0 = 12.0 + 1.6 * np.cos(2 * np.pi * (y - 6.5) / 13.0)
    ax.fill_between(y, 0, z0, color=C_GROUND)
    ax.plot(y, z0, "k-", lw=1.2)
    # 曲率(平滑化した z の 2 階微分)に比例する侵食の矢印
    lap = -1.6 * (2 * np.pi / 13.0) ** 2 * np.cos(2 * np.pi * (y - 6.5) / 13.0)
    for yi in np.arange(1.0, 40, 2.0):
        k = np.interp(yi, y, lap)
        e = 1.0 + 8.0 * max(k, 0.0)
        zi = np.interp(yi, y, z0)
        _arrow(ax, yi, zi + 0.5 + 0.9 * e, yi, zi + 0.3, C_ERODE, lw=1.3, ms=8)
    yh = 6.5 + 6.5      # 谷(凹部)の中心
    ax.text(yh, 17.3, T("凹部(κ > 0)は\n×(1 + c_b κ) で速く削れて谷になる", "hollows (κ > 0) erode\nfaster by ×(1 + c_b κ) → valleys"),
            ha="center", fontsize=8, color=C_ERODE)
    ax.text(32.5, 15.6, T("凸部(尾根)は\n増幅なし", "spurs (ridges):\nno amplification"), ha="center", fontsize=8)
    # 曲率を測る幅 ℓ
    ax.annotate("", xy=(yh - 2.0, 7.0), xytext=(yh + 2.0, 7.0),
                arrowprops=dict(arrowstyle="<->", color="k", lw=1.0))
    ax.text(yh, 5.3, T("ℓ: 曲率を測る幅\n(リルが集水する幅。spl_lc)", "ℓ: width over which κ is measured\n(collection width of rills; spl_lc)"),
            ha="center", fontsize=8, va="top")
    ax.set_xlim(0, 40)
    ax.set_ylim(0, 21)
    ax.set_xlabel(T("y (m)(崖縁に沿う向き)", "y (m) (along the cliff edge)"))
    ax.set_ylabel(T("z(模式)", "z (schematic)"))
    ax.set_title(T("(b) 崖面を横切る断面: 凹部ほど速く削れる", "(b) Across the cliff face: hollows erode faster"),
                 loc="left", fontsize=10)


def _growth(ax):
    """擾乱の成長率 σ(λ) ∝ k² exp(−ℓ²k²/2)(相関長 ℓ)と格子の κ(Δx = 1 m)。"""
    lam = np.logspace(np.log10(1.0), np.log10(80.0), 600)
    k = 2 * np.pi / lam
    dx = 1.0
    grid = np.where(lam >= 2 * dx, (4 / dx ** 2) * np.sin(np.pi * dx / lam) ** 2, np.nan)
    ax.plot(lam, grid / np.nanmax(grid), color="0.45", ls="--", lw=1.3,
            label=T("格子の κ(spl_lc = 0、Δx = 1 m): 最短波長 2Δx が最速",
                    "grid κ (spl_lc = 0, Δx = 1 m): the shortest wave 2Δx is fastest"))
    for ell, c in ((1.0, "C0"), (2.0, "C1"), (4.0, "C2")):
        s = k ** 2 * np.exp(-0.5 * (ell * k) ** 2)
        ax.plot(lam, s / s.max(), color=c, lw=1.8, label="ℓ = %g m" % ell)
        ls = 2 * np.pi * ell / np.sqrt(2.0)
        ax.axvline(ls, color=c, lw=0.8, ls=":")
        ax.text(ls * 1.04, 1.02, "λ* = %.1f m" % ls, color=c, fontsize=8)
    ax.set_xscale("log")
    ax.set_xticks([1, 2, 5, 10, 20, 50])
    ax.set_xticklabels(["1", "2", "5", "10", "20", "50"])
    ax.set_ylim(0, 1.95)
    ax.set_xlabel(T("擾乱の波長 λ (m)(崖縁に沿う向き)", "wavelength λ of a perturbation (m) (along the edge)"))
    ax.set_ylabel(T("成長率(各曲線の最大で正規化)", "growth rate (normalised by each maximum)"))
    ax.legend(fontsize=7.5, loc="upper left")
    ax.text(78, 1.42, T("σ(k) = D_a k² exp(−ℓ²k²/2)\n最速の波長 λ* = 2πℓ/√2 ≈ 4.4 ℓ\n最大の成長率 ∝ 1/ℓ²",
                          "σ(k) = D_a k² exp(−ℓ²k²/2)\nfastest wavelength λ* = 2πℓ/√2 ≈ 4.4 ℓ\nmaximum rate ∝ 1/ℓ²"),
            fontsize=7.5, va="top", ha="right")
    ax.set_title(T("(c) 谷の間隔を決めるもの(線形理論)", "(c) What sets the valley spacing (linear theory)"),
                 loc="left", fontsize=10)


def mechanism():
    fig = plt.figure(figsize=(13.5, 9.6))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.15, 1], hspace=0.32, wspace=0.22)
    _profile(fig.add_subplot(gs[0, :]))
    _cross(fig.add_subplot(gs[1, 0]))
    _growth(fig.add_subplot(gs[1, 1]))
    fig.savefig(f"{FIGDIR}/mechanism.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


def setup():
    z = np.loadtxt("z_main.txt")
    sw = np.loadtxt("sw_main.txt")
    zs = np.loadtxt("z_sweep.txt")
    ny, nx = z.shape
    dx = 120.0 / nx
    fig = plt.figure(figsize=(14, 6.4))
    gs = fig.add_gridspec(2, 3, width_ratios=[0.8, 1.6, 1.3], height_ratios=[1, 1], wspace=0.35, hspace=0.45)
    # 平面(主ケース)
    ax = fig.add_subplot(gs[:, 0])
    zz = np.where(sw > 0, np.nan, z)
    im = ax.imshow(zz, origin="lower", extent=[0, nx * dx, 0, ny * dx], cmap="terrain", vmin=-8, vmax=32)
    ax.imshow(np.where(sw > 0, 1.0, np.nan), origin="lower", extent=[0, nx * dx, 0, ny * dx],
              cmap="Blues", vmin=0, vmax=1.6)
    ax.text(100, 120, T("海(海域マスク)", "sea (sea mask)"), rotation=90, ha="center", va="center", fontsize=8)
    ax.text(30, 120, T("台地 30 m", "plateau 30 m"), rotation=90, ha="center", va="center", fontsize=8)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title(T("主ケースの地形\n120 m × 240 m、Δx = 1 m", "Main case terrain\n120 m × 240 m, Δx = 1 m"), fontsize=9)
    fig.colorbar(im, ax=ax, shrink=0.6).set_label(T("地盤高 (m)", "elevation (m)"))
    # 縦断
    ax = fig.add_subplot(gs[0, 1])
    x = (np.arange(nx) + 0.5) * dx
    xs = (np.arange(zs.shape[1]) + 0.5) * (100.0 / zs.shape[1])
    j = ny // 2
    ax.fill_between(x, -2, z[j], color=C_GROUND, alpha=0.7)
    ax.plot(x, z[j], "k-", lw=1.3, label=T("主ケース(param.txt。台地 30 m・幅 60 m)", "main case (param.txt; plateau 30 m, 60 m wide)"))
    ax.plot(xs, zs[j], color="C3", lw=1.3, ls="--",
            label=T("系列・格子収束(台地 15 m・幅 40 m。領域 100 m)", "series and grid tests (plateau 15 m, 40 m wide; 100 m domain)"))
    ax.axhline(0, color=C_SEA, lw=1.2)
    ax.text(103, 1.0, T("海面 = 侵食基準面", "sea level = base level"), fontsize=8, color="#1f4e9c")
    ax.text(71, 18, "tanθ = 1.5 (56°)", fontsize=8)
    ax.set_xlim(0, 120)
    ax.set_ylim(-2, 46)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("z (m)")
    ax.legend(fontsize=7.5, loc="upper right")
    ax.set_title(T("縦断(y = 120 m の行)", "Profile (row y = 120 m)"), fontsize=9)
    # 崖縁の白色雑音
    ax = fig.add_subplot(gs[1, 1])
    # 崖縁の位置: 台地(z = 30 m)を外れた最初のセルの z から崖の勾配 1.5 で逆算する
    i1 = np.argmax(z < 30.0 - 1e-9, axis=1)
    xe = x[i1] - (30.0 - z[np.arange(ny), i1]) / 1.5
    yy = (np.arange(ny) + 0.5) * dx
    ax.step(yy, xe - 60.0, where="mid", color="k", lw=0.9)
    ax.axhline(0, color="0.5", lw=0.6)
    ax.set_xlim(0, 240)
    ax.set_ylim(-1.2, 1.2)
    ax.set_xlabel("y (m)")
    ax.set_ylabel(T("崖縁の位置 − 60 m", "edge position − 60 m"))
    ax.set_title(T("崖縁の白色雑音(一様 ±0.5 m、1 m ごと、シード固定。格子幅を変えても同じ形)",
                   "White noise on the cliff edge (uniform ±0.5 m per 1 m, fixed seed)"),
                 fontsize=9)
    # 設定の要約
    ax = fig.add_subplot(gs[:, 2])
    ax.axis("off")
    rows = [
        (T("降雨", "rain"), T("一様 10 mm/h を降らせ続ける", "uniform 10 mm/h, continuous")),
        (T("浸透", "infiltration"), T("Green-Ampt 36 mm/h\n→ 全量浸透、地表流ゼロ", "Green-Ampt 36 mm/h\n→ all infiltrates, no surface flow")),
        (T("土層", "soil"), T("厚さ 100 m(崖より十分厚く)", "100 m thick (much thicker than the cliff)")),
        (T("侵食", "erosion"), T("乾式斜面侵食 f_splash\nk_r 2e-4, k_t 0.05, h 1.5,\nc_b 32 m, ℓ 2 m", "dry hillslope erosion f_splash\nk_r 2e-4, k_t 0.05, h 1.5,\nc_b 32 m, ℓ 2 m")),
        (T("基準面", "base level"), T("海面 z = 0(spl_zbase)", "sea level z = 0 (spl_zbase)")),
        (T("時間", "time"), T("dt 2 s、地形更新 2 s ごと × morfac 500\n5 時間 = 地形時間 9×10⁶ s", "dt 2 s, landform update every 2 s × morfac 500\n5 h = landform time 9×10⁶ s")),
    ]
    yv = 0.97
    for k, v in rows:
        ax.text(0.0, yv, k, fontsize=9, fontweight="bold", va="top")
        ax.text(0.31, yv, v, fontsize=9, va="top")
        yv -= 0.075 + 0.055 * v.count("\n")
    ax.set_title(T("主ケースの設定", "Main case settings"), fontsize=9, loc="left")
    fig.savefig(f"{FIGDIR}/setup.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    mechanism()
    setup()
    print(f"{FIGDIR}/mechanism.png, {FIGDIR}/setup.png written")
