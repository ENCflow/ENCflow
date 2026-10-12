"""nonhydro_*: 非静水圧補正(users_guide/nonhydrostatic.md)の模式図。

  nonhydro_scheme.png      (a) 1 層モデルの鉛直構造と変数
                           (b) 1 ステップの流れ(静水圧予測子 → 射影 → 連続式)
                           (c) NH マスクと活性集合(どこを非静水圧で解くか)
  nonhydro_dispersion.png  (a) 線形波の分散関係(位相速度比 対 kH)
                           (b) 底面変位 → 水面のフィルタ F(kH)(f_nh_bottom)
  式は docs/nonhydrostatic_plan.md §3・§16、m_swflow_enc_nh.f90 のヘッダに合わせる。
"""
import numpy as np
from _style import *

T = {"ja": {
    "a": "(a) 1 層モデルの鉛直構造",
    "b": "(b) 1 ステップの流れ(射影法)",
    "c": "(c) どこを非静水圧で解くか(マスクと活性集合)",
    "eta": "水面 η = z_b + h", "zb": "底面 z_b", "u": "u(水深平均)",
    "ws": "w_s = ∂η/∂t + u·∇η", "wb": "w_b = ∂z_b/∂t + u·∇z_b",
    "wbar": "w̄ = (w_s + w_b)/2 = −(h/2)∇·u + u·∇z_b + ∂z_b/∂t",
    "q": "非静水圧 q(z): 水面 0、底面 q_b\n(鉛直に線形)",
    "phi": "φ = −q_b/2 = (h²/4)∇·a − (h/2) a·∇z_b − (h/2) z̈_b",
    "beta": "β = h²/4",
    "s0": "ステップ頭: u^n, h^n(u^n を複製)",
    "s1": "静水圧予測子(従来どおり)\nmomentum: 適応 RK・運動量保存形移流・摩擦\n堤防・構造物・境界 → u*, mn*",
    "s2": "射影 nh_project(f_nonhydrostatic = 1 のときだけ)\n a* = (u* − u^n)/Δt\n (1 − β∇²)φ = β ∇·a*  を反復で解く(CG / Jacobi)\n u^{n+1} = u* + Δt ∇φ,  mn = u^{n+1} h_e",
    "s3": "連続式(従来どおり): mn → h^{n+1}",
    "off": "f_nonhydrostatic = 0 なら\nこの箱を通らない\n(メモリ・計算・通信の\n追加ゼロ)",
    "nh": "NH 候補セル(h ≥ nh_hmin、gv = 1 …)",
    "hyd": "静水圧のまま(φ = 0)",
    "shallow": "浅い・乾燥\nh < nh_hmin",
    "brk": "砕波セル+縁\n(f_nh_breaking)",
    "bcm": "強制境界の縁\n(nh_bc_margin)",
    "seed": "種: χ > nh_chi_on",
    "margin": "縁 nh_margin\n(自動 2H/Δx)",
    "act": "活性集合(f_nh_adaptive = 1)で解く範囲",
    "legend": "■ 種(検出)  ■ 縁  ■ 砕波\n▨ 浅い・境界の縁  □ 候補だが不活性(φ = 0)",
}, "en": {
    "a": "(a) Vertical structure of the one-layer model",
    "b": "(b) One time step (projection method)",
    "c": "(c) Where the non-hydrostatic correction is solved (mask and active set)",
    "eta": "surface η = z_b + h", "zb": "bottom z_b", "u": "u (depth-averaged)",
    "ws": "w_s = ∂η/∂t + u·∇η", "wb": "w_b = ∂z_b/∂t + u·∇z_b",
    "wbar": "w̄ = (w_s + w_b)/2 = −(h/2)∇·u + u·∇z_b + ∂z_b/∂t",
    "q": "non-hydrostatic pressure q(z):\n0 at the surface, q_b at the bottom\n(linear in z)",
    "phi": "φ = −q_b/2 = (h²/4)∇·a − (h/2) a·∇z_b − (h/2) z̈_b",
    "beta": "β = h²/4",
    "s0": "start of step: u^n, h^n (u^n is copied)",
    "s1": "hydrostatic predictor (unchanged)\nmomentum: adaptive RK, conservative advection, friction,\nlevees, structures, boundaries → u*, mn*",
    "s2": "projection nh_project (only with f_nonhydrostatic = 1)\n a* = (u* − u^n)/Δt\n solve (1 − β∇²)φ = β ∇·a* iteratively (CG / Jacobi)\n u^{n+1} = u* + Δt ∇φ,  mn = u^{n+1} h_e",
    "s3": "continuity (unchanged): mn → h^{n+1}",
    "off": "f_nonhydrostatic = 0:\nthis box is skipped\n(no extra memory,\nwork or communication)",
    "nh": "NH candidates (h ≥ nh_hmin, gv = 1, …)",
    "hyd": "stays hydrostatic (φ = 0)",
    "shallow": "shallow / dry\nh < nh_hmin",
    "brk": "breaking cells + margin\n(f_nh_breaking)",
    "bcm": "margin of forced\nboundaries (nh_bc_margin)",
    "seed": "seeds: χ > nh_chi_on",
    "margin": "margin nh_margin\n(auto 2H/Δx)",
    "act": "solved with the active set (f_nh_adaptive = 1)",
    "legend": "■ seeds (detected)  ■ margin  ■ breaking\n▨ shallow / boundary margin  □ candidate but inactive (φ = 0)",
}}

D = {"ja": {
    "a": "(a) 線形波の分散関係(平坦床)",
    "b": "(b) 底面変位 → 水面のフィルタ F(kH)(f_nh_bottom)",
    "exact": "厳密(Airy)  √(tanh kH / kH)",
    "nh1": "1 層 NH(ENCflow、β = h²/4)  1/√(1 + (kH)²/4)",
    "nh2": "2 次圧力分布(Green–Naghdi 相当)  1/√(1 + (kH)²/3)",
    "hyd": "静水圧 SWE  1",
    "xlabel": "kH(H: 水深、k: 波数 2π/L)", "ylabel": "位相速度 c / √(gH)",
    "range": "実用範囲の目安 kH ≲ 2(誤差 2.5% 以下)",
    "fex": "厳密  1/cosh kH",
    "fimp": "f_nh_bottom = 1(平滑化源項)  1/(1 + (kH)²/4)²",
    "fnaive": "素朴な源項 −(h/2)z̈  (1 − (kH)²/4)/(1 + (kH)²/4)",
    "fnone": "加速度項なし・静水圧  1",
    "fylabel": "F(kH)",
    "fnote": "素朴な源項は kH > 2 で符号が反転し、\n慣性なしの底層と正帰還で発散した(§7)",
}, "en": {
    "a": "(a) Linear dispersion relation (flat bed)",
    "b": "(b) Bottom-motion to surface filter F(kH) (f_nh_bottom)",
    "exact": "exact (Airy)  √(tanh kH / kH)",
    "nh1": "one-layer NH (ENCflow, β = h²/4)  1/√(1 + (kH)²/4)",
    "nh2": "quadratic pressure (Green–Naghdi type)  1/√(1 + (kH)²/3)",
    "hyd": "hydrostatic SWE  1",
    "xlabel": "kH (H: depth, k: wavenumber 2π/L)", "ylabel": "phase speed c / √(gH)",
    "range": "practical range kH ≲ 2 (error below 2.5%)",
    "fex": "exact  1/cosh kH",
    "fimp": "f_nh_bottom = 1 (smoothed source)  1/(1 + (kH)²/4)²",
    "fnaive": "naive source −(h/2)z̈  (1 − (kH)²/4)/(1 + (kH)²/4)",
    "fnone": "no acceleration term / hydrostatic  1",
    "fylabel": "F(kH)",
    "fnote": "the naive source changes sign for kH > 2 and\nblew up in feedback with the inertialess bed layer (§7)",
}}

C_SEED, C_MARG, C_BRK, C_SHAL = "#2a78d6", "#cfe0f6", "#f2b84b", "#d8d6d1"


def panel_column(ax, t):
    x = np.linspace(0, 10, 200)
    zb = 0.6 + 0.12 * x                      # gently sloping bottom
    eta = 4.0 + 0.35 * np.sin(0.9 * x)       # wavy surface
    ax.fill_between(x, zb, eta, color=C_WATER_L, zorder=1)
    ax.fill_between(x, 0, zb, color=C_GROUND_L, zorder=1)
    ax.plot(x, zb, color=C_GROUND, lw=1.6, zorder=3)
    ax.plot(x, eta, color=C_WATER, lw=1.6, zorder=3)
    label(ax, 0.3, 4.75, t["eta"], color=C_WATER, fs=8.8, ha="left")
    label(ax, 9.6, 1.3, t["zb"], color=C_GROUND, fs=8.8, ha="right")
    # pressure profile at x = 3
    xq = 3.0
    zb_q = 0.6 + 0.12 * xq
    eta_q = 4.0 + 0.35 * np.sin(0.9 * xq)
    ax.plot([xq, xq], [zb_q, eta_q], color=C_P, lw=0.8, ls="--", zorder=4)
    tri = Polygon([(xq, eta_q), (xq, zb_q), (xq + 1.3, zb_q)], closed=True, fc="#fdf1dc", ec=C_X, lw=1.4, zorder=4)
    ax.add_patch(tri)
    label(ax, xq + 1.45, zb_q + 0.12, "q_b", color=C_X, fs=9, ha="left")
    label(ax, xq + 0.1, eta_q + 0.22, "q = 0", color=C_X, fs=8.5, ha="left")
    label(ax, xq + 1.5, 2.3, t["q"], color=C_X, fs=8.0, ha="left")
    # velocities
    arrow(ax, (7.9, 2.9), (9.4, 2.9), C_C, lw=1.6)
    label(ax, 8.65, 3.2, t["u"], color=C_C, fs=8.8)
    arrow(ax, (7.0, eta.max() - 0.1), (7.0, eta.max() + 0.7), C_C, lw=1.3)
    label(ax, 7.2, 5.1, t["ws"], color=C_C, fs=8.3, ha="left")
    arrow(ax, (1.2, 0.6 + 0.12 * 1.2 + 0.05), (1.2, 0.6 + 0.12 * 1.2 + 0.75), C_GROUND, lw=1.3)
    label(ax, 1.4, 0.3, t["wb"], color=C_GROUND, fs=8.3, ha="left")
    label(ax, 0.2, 5.9, t["wbar"], color=C_P, fs=8.5, ha="left")
    label(ax, 0.2, 6.5, t["phi"], color=C_X, fs=8.5, ha="left")
    label(ax, 0.2, 7.05, t["beta"], color=C_X, fs=8.8, ha="left")
    ax.set_xlim(-0.2, 10.4); ax.set_ylim(-0.2, 7.5)


def panel_flow(ax, t):
    boxes = [("s0", 8.6, "white", C_P), ("s1", 6.9, "#eef3fa", C_C), ("s2", 4.35, "#fdf1dc", C_X), ("s3", 2.0, "#eef3fa", C_C)]
    hs = {"s0": 0.7, "s1": 1.6, "s2": 2.1, "s3": 0.7}
    for key, yc, fc, ec in boxes:
        h = hs[key]
        ax.add_patch(FancyBboxPatch((0.5, yc - h / 2), 13.0, h, boxstyle="round,pad=0.08", fc=fc, ec=ec, lw=1.5, zorder=3))
        label(ax, 0.8, yc, t[key], color="k", fs=7.8, ha="left")
    ys = [8.6 - 0.35, 6.9 + 0.8, 6.9 - 0.8, 4.35 + 1.05, 4.35 - 1.05, 2.0 + 0.35]
    for a, b in ((ys[0], ys[1]), (ys[2], ys[3]), (ys[4], ys[5])):
        arrow(ax, (7.0, a - 0.05), (7.0, b + 0.05), C_P, lw=1.4)
    # bypass when NH is off
    ax.annotate("", (12.6, ys[5] + 0.05), (12.6, ys[2] - 0.05),
                arrowprops=dict(arrowstyle="-|>", color=C_G, lw=1.3, ls="--", connectionstyle="arc3,rad=-0.45"), zorder=2)
    label(ax, 14.4, 4.35, t["off"], color="#3f7a2a", fs=7.8, ha="left")
    ax.set_xlim(0, 19.0); ax.set_ylim(1.2, 9.3)


def panel_mask(ax, t):
    NX, NY = 16, 9
    # candidate region: white; shallow/dry at right; boundary margin at left
    cells = {}
    for i in range(NX):
        for j in range(NY):
            cells[(i, j)] = "cand"
    for i in (0,):
        for j in range(NY):
            cells[(i, j)] = "shal"
    for i in range(13, NX):
        for j in range(NY):
            cells[(i, j)] = "shal"
    for i in range(12, 13):
        for j in range(2, 7):
            cells[(i, j)] = "shal"
    for i in range(9, 12):
        for j in range(3, 6):
            cells[(i, j)] = "brk"
    seeds = [(i, j) for i in range(4, 7) for j in range(3, 6)]
    for s_ in seeds:
        cells[s_] = "seed"
    for i in range(2, 9):
        for j in range(1, 8):
            if cells[(i, j)] == "cand" and max(abs(i - 5), abs(j - 4)) <= 3:
                cells[(i, j)] = "marg"
    colors = {"cand": "white", "shal": C_SHAL, "brk": C_BRK, "seed": C_SEED, "marg": C_MARG}
    for (i, j), kind in cells.items():
        ax.add_patch(Rectangle((i, j), 1, 1, fc=colors[kind], ec="none", zorder=1,
                               hatch="///" if kind == "shal" else None))
    grid(ax, 0, 0, NX, NY, 1, C_P, 0.5)
    ax.add_patch(Rectangle((2, 1), 7, 7, fill=False, ec=C_X, lw=1.6, ls="--", zorder=4))
    label(ax, 5.5, 4.5, t["seed"], color="white", fs=8.3, fontweight="bold")
    label(ax, 5.5, 7.5, t["margin"], color=C_C, fs=8.3)
    label(ax, 10.5, 4.5, t["brk"], color="#7a4a00", fs=8.0, box=True)
    label(ax, 14.5, 4.5, t["shallow"], color=C_P, fs=8.0, box=True)
    label(ax, 0.5, -0.4, t["bcm"], color=C_P, fs=8.0, ha="left", va="top")
    label(ax, 4.0, NY + 0.35, t["act"], color=C_X, fs=8.3, va="bottom")
    label(ax, 10.5, 1.0, t["hyd"], color=C_P, fs=8.0, box=True)
    label(ax, 13.0, NY + 0.35, t["nh"], color=C_P, fs=8.0, va="bottom")
    label(ax, NX / 2 + 1.5, -1.0, t["legend"], color=C_P, fs=7.6, va="top")
    ax.set_xlim(-0.3, NX + 0.3); ax.set_ylim(-2.1, NY + 1.2)


def draw_scheme(lang):
    t = T[lang]
    fig = plt.figure(figsize=(16.0, 5.6))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.0, 1.5, 1.3], left=0.01, right=0.99, top=0.93, bottom=0.03, wspace=0.05)
    axs = [fig.add_subplot(gs[0, k]) for k in range(3)]
    for ax, key in zip(axs, ("a", "b", "c")):
        ax.set_anchor("N"); ax.axis("off")
        ax.set_title(t[key], loc="left", fontsize=9.8)
    axs[0].set_aspect("equal"); axs[2].set_aspect("equal")
    panel_column(axs[0], t)
    panel_flow(axs[1], t)
    panel_mask(axs[2], t)
    return save(fig, "nonhydro_scheme", lang)


def draw_dispersion(lang):
    t = D[lang]
    fig, axs = plt.subplots(1, 2, figsize=(12.0, 4.8))
    kh = np.linspace(0.01, 4, 400)
    ax = axs[0]
    ax.axvspan(0, 2, color="#eef3fa", zorder=0)
    ax.plot(kh, np.sqrt(np.tanh(kh) / kh), color="k", lw=2.0, label=t["exact"], zorder=4)
    ax.plot(kh, 1 / np.sqrt(1 + kh**2 / 4), color=C_X, lw=2.0, label=t["nh1"], zorder=5)
    ax.plot(kh, 1 / np.sqrt(1 + kh**2 / 3), color=C_C, lw=1.3, ls="--", label=t["nh2"], zorder=3)
    ax.axhline(1, color=C_P, lw=1.1, ls=":", label=t["hyd"], zorder=3)
    ax.set_xlim(0, 4); ax.set_ylim(0.3, 1.05)
    ax.set_xlabel(t["xlabel"], fontsize=9); ax.set_ylabel(t["ylabel"], fontsize=9)
    ax.tick_params(labelsize=8)
    ax.legend(loc="lower left", fontsize=7.8, frameon=False)
    ax.text(0.1, 1.015, t["range"], fontsize=8.0, color=C_C)
    ax.set_title(t["a"], loc="left", fontsize=9.8)
    ax = axs[1]
    b = kh**2 / 4
    ax.plot(kh, 1 / np.cosh(kh), color="k", lw=2.0, label=t["fex"], zorder=4)
    ax.plot(kh, 1 / (1 + b)**2, color=C_X, lw=2.0, label=t["fimp"], zorder=5)
    ax.plot(kh, (1 - b) / (1 + b), color=C_G, lw=1.3, ls="--", label=t["fnaive"], zorder=3)
    ax.axhline(1, color=C_P, lw=1.1, ls=":", label=t["fnone"], zorder=3)
    ax.axhline(0, color=RULE, lw=0.8, zorder=1)
    ax.set_xlim(0, 4); ax.set_ylim(-0.7, 1.1)
    ax.set_xlabel(t["xlabel"], fontsize=9); ax.set_ylabel(t["fylabel"], fontsize=9)
    ax.tick_params(labelsize=8)
    ax.legend(loc="upper right", fontsize=7.8, frameon=False)
    ax.text(0.15, -0.6, t["fnote"], fontsize=8.0, color="#3f7a2a")
    ax.set_title(t["b"], loc="left", fontsize=9.8)
    fig.subplots_adjust(left=0.06, right=0.99, top=0.91, bottom=0.13, wspace=0.22)
    return save(fig, "nonhydro_dispersion", lang)


RULE = "#d8d6d1"


def draw(lang):
    draw_dispersion(lang)
    return draw_scheme(lang)
