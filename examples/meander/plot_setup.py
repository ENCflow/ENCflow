#!/usr/bin/env python3
"""examples/meander の機構の模式図と設定の図(計算結果は使わない)。

  python3 plot_setup.py        # figs/mechanism.png, figs/setup.png
  python3 plot_setup.py en     # 英語ラベル版を en/figs/ に描く

  figs/mechanism.png  (a) 湾曲部の平面(主流・河床近傍の二次流・外岸の淵と後退・内岸の砂州)、
                      (b) 湾曲頂部の横断(流砂の向きの釣り合い・河岸の崩れ方 3 種・砂州の天端)、
                      (c) 出水と低水の繰り返しと、低水期に露出した砂州の定着度 a の育ち方
  figs/setup.png      初期地形の平面(河道・土層厚の区分・流入と流出・指標の範囲)、
                      河道に沿う縦断(河床・氾濫原・水面・土層の底)、湾曲頂部の横断、
                      流入ハイドログラフ 3 種と出力時刻

幾何は make_init.py の関数から直接作る(make を実行していなくても描ける)。
依存: numpy, matplotlib
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import make_init as mi

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)

C_WATER, C_DEEP, C_LAND, C_BAR, C_SOIL, C_ROCK = "#9ecae1", "#3182bd", "#d9c89e", "#e6b85c", "#c9b48a", "#8c7a5b"
C_SEC, C_ERODE, C_FIX, C_Q = "#c0392b", "#c0392b", "#2a9d5a", "#2c7fb8"
MORFAC = 50.0


def _arrow(ax, x0, y0, x1, y1, color, lw=1.6, ms=10, style="-|>", zorder=5):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0), zorder=zorder,
                arrowprops=dict(arrowstyle=style, color=color, lw=lw, shrinkA=0, shrinkB=0, mutation_scale=ms))


# ---------------------------------------------------------------- 機構の模式図
def _plan(ax):
    """(a) 湾曲部の平面の模式図(1 波長。寸法は模式)。"""
    lam, amp, w = 200.0, 30.0, 20.0
    s = np.linspace(-45, 245, 800)
    yc = amp * np.sin(2 * np.pi * s / lam)
    dy = np.gradient(yc, s)
    nx, ny = -dy / np.hypot(1, dy), 1 / np.hypot(1, dy)          # 左手(北)向きの単位法線
    xl, yl = s + nx * w / 2, yc + ny * w / 2
    xr, yr = s - nx * w / 2, yc - ny * w / 2
    ax.add_patch(Polygon(np.c_[np.r_[xl, xr[::-1]], np.r_[yl, yr[::-1]]], closed=True, fc=C_WATER, ec="none", zorder=1))
    ax.plot(xl, yl, "k-", lw=1.2, zorder=3); ax.plot(xr, yr, "k-", lw=1.2, zorder=3)
    # 頂部(s = 50: 北へ張り出す = 外岸は北。s = 150: 南へ)の淵と砂州。淵は頂部のやや下流に寄る
    for sc, out in ((50.0, 1.0), (150.0, -1.0)):
        m = (s > sc - 35) & (s < sc + 55)
        f = np.clip(1 - ((s[m] - sc - 12) / 45) ** 2, 0, 1)
        xo, yo = s[m] + nx[m] * out * w / 2, yc[m] + ny[m] * out * w / 2
        xi, yi = s[m] + nx[m] * out * (w / 2 - 0.3 * w * f), yc[m] + ny[m] * out * (w / 2 - 0.3 * w * f)
        ax.add_patch(Polygon(np.c_[np.r_[xo, xi[::-1]], np.r_[yo, yi[::-1]]], closed=True, fc=C_DEEP, ec="none", alpha=0.8, zorder=2))
        m2 = (s > sc - 45) & (s < sc + 40)
        g = np.clip(1 - ((s[m2] - sc + 3) / 42) ** 2, 0, 1)
        xo, yo = s[m2] - nx[m2] * out * w / 2, yc[m2] - ny[m2] * out * w / 2
        xi, yi = s[m2] - nx[m2] * out * (w / 2 - 0.45 * w * g), yc[m2] - ny[m2] * out * (w / 2 - 0.45 * w * g)
        ax.add_patch(Polygon(np.c_[np.r_[xo, xi[::-1]], np.r_[yo, yi[::-1]]], closed=True, fc=C_BAR, ec="none", zorder=2))
        for so in (sc - 6, sc + 10, sc + 26):                    # 河床近傍の流れ(二次流)は内岸へ
            k = np.argmin(abs(s - so))
            _arrow(ax, s[k] + nx[k] * out * 6, yc[k] + ny[k] * out * 6, s[k] - nx[k] * out * 3, yc[k] - ny[k] * out * 3,
                   C_SEC, lw=1.3, ms=8)
        m3 = (s > sc - 25) & (s < sc + 60)                       # 外岸の後退(破線 = 後の河岸)
        bump = 9.0 * np.clip(1 - ((s[m3] - sc - 15) / 40) ** 2, 0, 1)
        ax.plot(s[m3] + nx[m3] * out * (w / 2 + bump), yc[m3] + ny[m3] * out * (w / 2 + bump), color=C_ERODE, ls="--", lw=1.3, zorder=3)
        k = np.argmin(abs(s - (sc + 15)))
        _arrow(ax, s[k] + nx[k] * out * (w / 2 + 1), yc[k] + ny[k] * out * (w / 2 + 1),
               s[k] + nx[k] * out * (w / 2 + 9.5), yc[k] + ny[k] * out * (w / 2 + 9.5), C_ERODE, lw=1.4, ms=9)
    for so in (-30, 100, 230):                                   # 主流
        k = np.argmin(abs(s - so))
        _arrow(ax, s[k] - 13, yc[k] - 13 * dy[k], s[k] + 13, yc[k] + 13 * dy[k], "#08306b", lw=2.0, ms=12)
    ax.text(-44, 14, T("主流", "main flow"), color="#08306b", fontsize=9)
    ax.text(68, 58, T("外岸の後退(破線 = 後の河岸)", "outer bank retreats (dashed = later bank)"), color=C_ERODE, fontsize=8.5, ha="center")
    ax.annotate(T("河床近傍の流れ(二次流)は内岸へ", "near-bed (secondary) flow turns inward"),
                xy=(57, 25), xytext=(-44, -44), fontsize=8, color=C_SEC,
                arrowprops=dict(arrowstyle="-", color=C_SEC, lw=0.8))
    ax.annotate(T("内岸の砂州", "point bar"), xy=(48, 14), xytext=(10, -30), fontsize=8.5, color="#8a5a00",
                arrowprops=dict(arrowstyle="-", color="#8a5a00", lw=0.8))
    ax.annotate(T("外岸の淵", "pool at the outer bank"), xy=(165, -36), xytext=(185, -62), fontsize=8.5, color=C_DEEP,
                arrowprops=dict(arrowstyle="-", color=C_DEEP, lw=0.8))
    ax.set_xlim(-48, 248); ax.set_ylim(-68, 66); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title(T("(a) 湾曲部の平面(模式)", "(a) Plan view of the bends (schematic)"), fontsize=10, loc="left")


def _cross(ax):
    """(b) 湾曲頂部の横断の模式図(内岸 = 左、外岸 = 右。寸法は例題の桁)。"""
    yb = np.array([-24, -10, -10, -6, 0, 6, 9, 10, 10.6, 33])
    zb = np.array([1.0, 1.0, 0.55, 0.35, -0.3, -1.1, -1.7, -1.8, 1.0, 1.0])
    ax.fill_between(yb, -2.6, zb, color=C_SOIL, zorder=1)
    ax.plot(yb, zb, "k-", lw=1.2, zorder=3)
    wl = 0.8
    yw = np.linspace(-10, 10.4, 50)
    ax.fill_between(yw, np.interp(yw, yb, zb), wl, where=np.interp(yw, yb, zb) < wl, color=C_WATER, zorder=2)
    ax.plot([-10, 10.4], [wl, wl], color=C_Q, lw=1.0, zorder=3)
    ax.text(-9.6, 0.84, T("出水時の水面", "flood water level"), color=C_Q, fontsize=7.5)
    # 初期の河床(破線)
    ax.plot([-24, -10, -10, 10, 10, 24], [1, 1, 0, 0, 1, 1], color="0.35", ls=":", lw=1.0, zorder=3)
    ax.text(-4.6, 0.08, T("初期の河床", "initial bed"), color="0.3", fontsize=7.5)
    # 二次流の循環(水面で外岸へ、河床近傍で内岸へ)
    _arrow(ax, -3, 0.62, 5, 0.62, C_SEC, lw=1.4, ms=9)
    _arrow(ax, 6.5, -0.85, -1.5, -0.05, C_SEC, lw=1.4, ms=9)
    ax.text(0.5, 1.30, T("二次流(水面は外岸へ、河床近傍は内岸へ)", "secondary flow (outward at the surface, inward near the bed)"),
            color=C_SEC, fontsize=8, ha="center")
    # 流砂の向きの釣り合い
    _arrow(ax, -0.5, -0.62, -4.5, -0.10, "#6a3d9a", lw=1.2, ms=8)
    _arrow(ax, -0.5, -0.62, 3.0, -1.10, "#6a3d9a", lw=1.2, ms=8)
    ax.text(-8.0, -1.45, T("流砂: 二次流で内岸へ / 重力で横断斜面を下る\n→ 釣り合う横断勾配(淵と砂州)",
                           "bed load: inward by the secondary flow,\ndown the transverse slope by gravity\n→ a balanced transverse bed slope"),
            color="#6a3d9a", fontsize=7.5, ha="center", va="top")
    # 砂州の天端は水面まで
    ax.annotate(T("砂州の天端は水面まで\n(掃流砂は水面より上に積もらない)\n低水期に露出 → 定着",
                  "bar top grows up to the water level\n(bed load does not deposit above it);\nexposed at low flow → fixation"),
                xy=(-8.3, 0.62), xytext=(-23.5, -0.55), fontsize=7.5, color="#8a5a00",
                arrowprops=dict(arrowstyle="-", color="#8a5a00", lw=0.8))
    # 外岸の崩れ方
    ax.add_patch(Polygon([[10.6, 1.0], [12.4, 1.0], [10.0, -1.2]], closed=True, fc="none", ec=C_ERODE, ls="--", lw=1.1, zorder=4))
    ax.add_patch(Polygon([[8.6, -1.6], [10.2, -1.8], [10.0, -0.9]], closed=True, fc=C_ROCK, ec="k", lw=0.6, zorder=4))
    ax.text(13.6, 0.2, T("外岸の後退:\n・脚部の洗掘で河岸面が安息角を\n  超えて崩れる(非粘着性)\n・側岸侵食則 E_b(粘着性)\n・限界高さ H_c を超えると塊で崩れ、\n  土塊が脚部を覆う(崩落土塊)",
                         "outer bank retreat:\n- toe scour steepens the face\n  beyond the angle of repose\n  (non-cohesive)\n- bank erosion law E_b (cohesive)\n- above the critical height H_c\n  the bank fails as a block\n  that shields the toe"),
            fontsize=7.5, color=C_ERODE, va="center")
    ax.set_xlim(-24, 33); ax.set_ylim(-2.6, 1.7)
    ax.set_xlabel(T("横断方向の位置 (m)(左 = 内岸、右 = 外岸)", "cross-channel position (m) (left = inner, right = outer bank)"), fontsize=8)
    ax.set_ylabel(T("高さ (m)", "elevation (m)"), fontsize=8)
    ax.tick_params(labelsize=7.5)
    ax.set_title(T("(b) 湾曲頂部の横断(模式。縦は誇張)", "(b) Cross-section at a bend apex (schematic, vertical exaggeration)"), fontsize=10, loc="left")


def _qcycle(tmin):
    """矩形波の流入(param_varq / fix 系): 出水 20 分、2 分で低水、低水 18 分、2 分で出水。周期 42 分。"""
    t = np.mod(tmin, 42.0)
    return np.interp(t, [0, 20, 22, 40, 42], [15, 15, 1.5, 1.5, 15])


def _fixation(ax):
    """(c) 出水と低水の繰り返しと、低水期に露出する砂州のセルの定着度 a。"""
    th = np.linspace(0, 126, 2521)                       # 水理の時間 (分)
    q = _qcycle(th)
    tg = th * MORFAC / 60.0                              # 地形時間 (h)
    # 砂州のセル: Q < 5 m3/s のとき乾く(模式)。a は乾いている間 1 − (1 − a) exp(−dt/T_fix)
    tfix, ctau = 10.0, 10.0
    a = np.zeros_like(tg)
    for n in range(1, len(tg)):
        dt = tg[n] - tg[n - 1]
        a[n] = 1 - (1 - a[n - 1]) * np.exp(-dt / tfix) if q[n] < 5.0 else a[n - 1]
    ax.fill_between(tg, 0, q, color=C_Q, alpha=0.25, lw=0)
    ax.plot(tg, q, color=C_Q, lw=1.4)
    ax.set_ylabel(T("流入 Q (m³/s)", "inflow Q (m³/s)"), color=C_Q, fontsize=8.5)
    ax.set_ylim(0, 17); ax.set_xlim(0, tg[-1])
    ax.set_xlabel(T("地形時間 (h)(水理 42 分の周期 = 地形 35 h)", "landform time (h) (one 42-min hydraulic cycle = 35 h)"), fontsize=8.5)
    ax.tick_params(labelsize=7.5)
    ax2 = ax.twinx()
    ax2.plot(tg, 1 + ctau * a, color=C_FIX, lw=1.8)
    ax2.set_ylim(0, 12)
    ax2.set_ylabel(T("τ*c,eff / τ*c = 1 + c_τ a", "τ*c,eff / τ*c = 1 + c_τ a"), color=C_FIX, fontsize=8.5)
    ax2.tick_params(labelsize=7.5)
    ax.text(1.0, 16.0, T("出水 15 m³/s", "flood 15 m³/s"), color=C_Q, fontsize=8)
    ax.text(19.5, 3.2, T("低水 1.5 m³/s:\n砂州が露出して定着が進む", "low flow 1.5 m³/s:\nthe bar is exposed and fixes"), color=C_Q, fontsize=8)
    ax2.text(57, 6.4, T("定着度 a は乾いている間 1 − exp(−t/T_fix) で 1 へ(T_fix = 10 h)。\n出水で水没しても保たれ、定着面から 0.1 m 以上削られると 0 に戻る。\n定着したセルから流れ出す掃流砂の限界掃流力は τ*c (1 + c_τ a)(c_τ = 10)",
                          "fixation degree a grows as 1 − exp(−t/T_fix) while dry (T_fix = 10 h);\nit is kept under water and reset to 0 when scoured > 0.1 m below the fixed surface;\nbed load leaving a fixed cell needs τ*c (1 + c_τ a) (c_τ = 10)"),
             color=C_FIX, fontsize=7.8, va="top", bbox=dict(fc="white", ec="none", alpha=0.85))
    ax.set_title(T("(c) 出水と低水の繰り返しと定着(露出する砂州のセルの模式)",
                   "(c) Alternating floods and low flows, and fixation of a bar cell exposed at low flow (schematic)"),
                 fontsize=10, loc="left")


def mechanism():
    fig = plt.figure(figsize=(13.5, 8.6))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.35, 1.0], width_ratios=[1.0, 1.15], hspace=0.32, wspace=0.12)
    _plan(fig.add_subplot(gs[0, 0]))
    _cross(fig.add_subplot(gs[0, 1]))
    _fixation(fig.add_subplot(gs[1, :]))
    fig.subplots_adjust(left=0.05, right=0.94, top=0.95, bottom=0.07)
    fig.savefig(os.path.join(FIGDIR, "mechanism.png"), dpi=110)
    plt.close(fig)


# ---------------------------------------------------------------- 設定の図
def _fields():
    i = np.arange(1, mi.NX + 1); j = np.arange(1, mi.NY + 1)
    z = np.array([[mi.z_of(ii, jj) for ii in i] for jj in j])
    h = np.array([[mi.h_of(ii, jj) for ii in i] for jj in j])
    return z, h


def _hyd(rows):
    t = np.array([r[0] for r in rows], float); q = np.array([r[1] for r in rows], float)
    return t, q


def setup():
    z, h = _fields()
    x = (np.arange(mi.NX) + 0.5) * mi.DX
    y = (np.arange(mi.NY) + 0.5) * mi.DX
    L = mi.NX * mi.DX
    fig = plt.figure(figsize=(14, 9.0))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.05, 1.0], hspace=0.38, wspace=0.28)
    # --- 平面 ---
    ax = fig.add_subplot(gs[0, :])
    ext = [0, L, 0, mi.NY * mi.DX]
    ax.imshow(np.where(h > 0, 1.0, 0.0), origin="lower", extent=ext, aspect="equal",
              cmap=matplotlib.colors.ListedColormap([C_LAND, C_WATER]), vmin=0, vmax=1)
    ax.contour(x, y, h > 0, levels=[0.5], colors="k", linewidths=0.7)
    for xa in (mi.XFIX_UP, mi.XFIX_UP + mi.LRAMP, L - mi.XFIX_DN):
        ax.axvline(xa, color="0.25", ls="--", lw=0.8)
    yt = mi.NY * mi.DX + 3
    ax.text(mi.XFIX_UP / 2, yt, T("非侵食", "non-\nerodible"), ha="center", fontsize=7.5, va="bottom")
    ax.text(mi.XFIX_UP + mi.LRAMP / 2, yt, T("土層厚のランプ 0 → 5 m(sd.txt)", "soil-depth ramp 0 → 5 m (sd.txt)"), ha="center", fontsize=8, va="bottom")
    ax.text((mi.XFIX_UP + mi.LRAMP + L - mi.XFIX_DN) / 2, yt, T("土層 5 m", "soil 5 m"), ha="center", fontsize=8, va="bottom")
    ax.text(L - mi.XFIX_DN / 2, yt, T("非侵食", "non-\nerodible"), ha="center", fontsize=7.5, va="bottom")
    _arrow(ax, -40, mi.YC, 2, mi.YC, C_Q, lw=2.2, ms=13)
    ax.text(-22, mi.YC + 9, T("流入 Q\n(10 セル)", "inflow Q\n(10 cells)"), color=C_Q, fontsize=8, ha="center", va="bottom")
    _arrow(ax, L - 2, mi.YC, L + 36, mi.YC, C_Q, lw=2.2, ms=13)
    ax.text(L + 18, mi.YC + 9, T("自由流出", "free\noutflow"), color=C_Q, fontsize=8, ha="center", va="bottom")
    for xa in (250, 350, 450, 550, 650):
        ax.plot([xa, xa], [6, 16], color=C_ERODE, lw=1.4)
        ax.text(xa, 18, "%d" % xa, color=C_ERODE, fontsize=7.5, ha="center", va="bottom")
    ax.annotate("", xy=(650, 40), xytext=(150, 40), arrowprops=dict(arrowstyle="<->", color=C_ERODE, lw=1.0))
    ax.text(400, 43, T("指標を測る範囲 x = 150〜650 m(赤い目盛 = 湾曲の頂点)", "range of the metrics x = 150–650 m (red ticks = bend apexes)"),
            color=C_ERODE, fontsize=8, ha="center", va="bottom")
    ax.text(200, 165, T("振幅は x = 100〜300 m で 0 → 10 m", "amplitude ramps 0 → 10 m\nover x = 100–300 m"), fontsize=7.5, ha="center")
    ax.text(500, 175, T("正弦波(振幅 10 m・波長 200 m・幅 20 m)", "sine curve (amplitude 10 m, wavelength 200 m, width 20 m)"), fontsize=8, ha="center")
    ax.text(745, 165, T("振幅 7.5 m の\n湾曲が残る", "a 7.5 m bend\nremains"), fontsize=7.5, ha="center")
    ax.text(400, 205, T("氾濫原 = 河床 + 1 m(乾燥)", "floodplain = bed + 1 m (dry)"), fontsize=8, ha="center", color="#6b4f1d")
    ax.set_xlim(-60, L + 55); ax.set_ylim(0, mi.NY * mi.DX + 20)
    ax.set_xlabel("x (m)", fontsize=8.5); ax.set_ylabel("y (m)", fontsize=8.5); ax.tick_params(labelsize=7.5)
    ax.set_title(T("初期地形(青 = 河道、初期水深 0.8 m。河床は x 方向に勾配 0.001)",
                   "Initial terrain (blue = channel, initial depth 0.8 m; the bed slopes 0.001 in x)"), fontsize=10, loc="left")
    # --- 縦断(河道の中心線に沿う) ---
    ax = fig.add_subplot(gs[1, 0])
    xs = np.linspace(0, L, 801)
    zbed = mi.Z0 - mi.S0 * xs
    sd = mi.SD * np.clip((xs - mi.XFIX_UP) / mi.LRAMP, 0, 1); sd[xs > L - mi.XFIX_DN] = 0
    sdf = np.full_like(xs, mi.SD); sdf[xs > L - mi.XFIX_DN] = 0
    ax.fill_between(xs, zbed - sd, zbed, color=C_SOIL, lw=0)
    ax.fill_between(xs, 2.0, zbed - sd, color=C_ROCK, lw=0, alpha=0.6)
    ax.plot(xs, zbed + mi.BANK, color="#8a5a00", lw=1.0, label=T("氾濫原(河床 + 1 m)", "floodplain (bed + 1 m)"))
    ax.plot(xs, zbed + mi.H0, color=C_Q, lw=1.0, label=T("初期の水面(水深 0.8 m)", "initial water surface (0.8 m)"))
    ax.plot(xs, zbed, "k-", lw=1.0, label=T("河床(勾配 0.001)", "bed (slope 0.001)"))
    ax.plot(xs, zbed - sdf, color="k", ls="--", lw=0.9, label=T("土層の底(給砂の構成。sd_feed.txt)", "base of the soil (feed runs, sd_feed.txt)"))
    ax.text(420, 6.3, T("土層(可動)", "soil (erodible)"), fontsize=8)
    ax.text(420, 3.0, T("非侵食の底", "non-erodible base"), fontsize=8, color="w")
    ax.set_xlim(0, L); ax.set_ylim(2.0, 14.2)
    ax.set_xlabel("x (m)", fontsize=8.5); ax.set_ylabel(T("高さ (m)", "elevation (m)"), fontsize=8.5); ax.tick_params(labelsize=7.5)
    ax.legend(fontsize=6.8, loc="upper right", framealpha=0.95)
    ax.set_title(T("縦断(河道に沿う)", "Longitudinal section along the channel"), fontsize=10, loc="left")
    # --- 湾曲頂部の横断 ---
    ax = fig.add_subplot(gs[1, 1])
    i = int(350 / mi.DX)
    yy = np.repeat(np.arange(mi.NY + 1) * mi.DX, 2)[1:-1]
    zz = np.repeat(z[:, i], 2)
    zbed0 = mi.Z0 - mi.S0 * x[i]
    ax.fill_between(yy, zbed0 - 2.0, zz, color=C_SOIL, lw=0)
    ax.plot(yy, zz, "k-", lw=1.0)
    wet = h[:, i] > 0
    yw = y[wet]
    ax.fill_between([yw.min() - 1, yw.max() + 1], [zbed0, zbed0], [zbed0 + mi.H0] * 2, color=C_WATER, lw=0)
    ax.text(yw.mean(), zbed0 + 0.25, T("水深 0.8 m", "depth 0.8 m"), ha="center", fontsize=8, color=C_DEEP)
    ax.annotate("", xy=(yw.min() - 1, zbed0 - 0.35), xytext=(yw.max() + 1, zbed0 - 0.35),
                arrowprops=dict(arrowstyle="<->", lw=0.9))
    ax.text(yw.mean(), zbed0 - 0.55, T("幅 20 m(10 セル)", "width 20 m (10 cells)"), ha="center", va="top", fontsize=8)
    ax.text(yw.max() + 1.5, zbed0 + 1.18, T("河岸 1 m / 2 m = 26.6°\n(安息角 32° より緩い)", "bank 1 m / 2 m = 26.6°\n(gentler than 32° repose)"),
            fontsize=7.5, va="bottom")
    ax.set_xlim(yw.mean() - 30, yw.mean() + 30); ax.set_ylim(zbed0 - 1.6, zbed0 + 2.0)
    ax.set_xlabel("y (m)", fontsize=8.5); ax.set_ylabel(T("高さ (m)", "elevation (m)"), fontsize=8.5); ax.tick_params(labelsize=7.5)
    ax.set_title(T("湾曲頂部 x = 350 m の横断(初期)", "Cross-section at the apex x = 350 m (initial)"), fontsize=10, loc="left")
    # --- 流入ハイドログラフ ---
    ax = fig.add_subplot(gs[1, 2])
    tm = np.linspace(0, 126, 2521)
    rec_t, rec_q = _hyd([(0, 1.5), (2, 15), (12, 15), (32, 1.5), (42, 1.5)])
    qrec = np.interp(np.mod(tm, 42.0), rec_t, rec_q)
    ax.plot(tm, np.full_like(tm, 15.3), color="0.3", lw=1.4, ls=":", label=T("一定 15 m³/s", "constant 15 m³/s"))
    ax.plot(tm, _qcycle(tm), color=C_Q, lw=1.4, label=T("出水 20 分・低水 18 分の矩形波", "square wave: 20-min flood, 18-min low"))
    ax.plot(tm, qrec, color="#e08214", lw=1.1, ls="--", label=T("緩い減水期(param_fixrec)", "gentle recession (param_fixrec)"))
    ax.set_xlim(0, 126); ax.set_ylim(0, 24)
    sx = ax.secondary_xaxis("top", functions=(lambda t: t * MORFAC / 60.0, lambda h: h * 60.0 / MORFAC))
    sx.set_xlabel(T("地形時間 (h)", "landform time (h)"), fontsize=8); sx.tick_params(labelsize=7)
    ax.set_xlabel(T("水理の時間 (分)(周期 42 分。計算は 240 分 = 地形 200 h)", "hydraulic time (min) (42-min period; runs end at 240 min = 200 h)"), fontsize=8)
    ax.set_ylabel("Q (m³/s)", fontsize=8.5); ax.tick_params(labelsize=7.5)
    ax.legend(fontsize=6.8, loc="upper right", framealpha=0.95)
    ax.set_title(T("流入(最初の 3 周期)", "Inflow (first three cycles)"), fontsize=10, loc="left", pad=22)
    fig.subplots_adjust(left=0.05, right=0.97, top=0.95, bottom=0.07)
    fig.savefig(os.path.join(FIGDIR, "setup.png"), dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    mechanism()
    setup()
    print("figures: %s/mechanism.png %s/setup.png" % (FIGDIR, FIGDIR))
