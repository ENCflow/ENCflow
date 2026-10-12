"""diffusion_*: 運動方程式の拡散項(users_guide/diffusion.md)の模式図。

  diffusion_stencil.png  (a) エッジフラックス発散形の 9 点ステンシル(通過幅 l_k と距離 r_k)
                         (b) 乾燥・無効な近傍は no-flux 閉鎖(再正規化しない)
  diffusion_nu.png       (a) ゼロ方程式モデルの渦動粘性 ν = ν0 + α u* h
                         (b) 陽解法の安定上界 ν_max = Δx²/(2.83 dt)(既定の p_diagratio)
  式は m_swflow_enc_diff.f90 と developer.md §20 に合わせる。
"""
import numpy as np
from _style import *

T = {"ja": {
    "a": "(a) 拡散項のステンシル: エッジフラックスの発散(保存形)",
    "b": "(b) 乾燥・無効な近傍: そのエッジを欠落(no-flux 閉鎖)",
    "f0": "f_0", "flux": "エッジの拡散フラックス\nl_k · ν_e · (f_k − f_0) / r_k",
    "nue": "ν_e = (ν_0 + ν_k)/2",
    "lp": "軸: 通過幅 l = (1 − p_d)·Δ、距離 r = Δ",
    "ld": "対角: l = (p_d/√2)·Δ、r = √2·Δ",
    "sum": "∇·(ν∇f) ≈ (1/A) Σ_k l_k ν_e (f_k − f_0)/r_k\n軸 + 対角の重みで f_xx, f_yy の係数が厳密に 1(整合な 9 点ラプラシアン)",
    "dry": "乾燥\nh < dd", "inv": "無効\n(領域外)",
    "drop": "欠落したエッジ: フラックス 0\n残りの重みで再正規化しない\n(勾配 ∇u の計算とは違う)",
    "mono": "重みはすべて非負 → 拡散が新しい極値を作らない(離散最大値原理)",
}, "en": {
    "a": "(a) Stencil of the diffusion term: divergence of edge fluxes (conservative)",
    "b": "(b) Dry or invalid neighbours: the edge is dropped (no-flux closure)",
    "f0": "f_0", "flux": "diffusive flux across the edge\nl_k · ν_e · (f_k − f_0) / r_k",
    "nue": "ν_e = (ν_0 + ν_k)/2",
    "lp": "axis: passage width l = (1 − p_d)·Δ, distance r = Δ",
    "ld": "diagonal: l = (p_d/√2)·Δ, r = √2·Δ",
    "sum": "∇·(ν∇f) ≈ (1/A) Σ_k l_k ν_e (f_k − f_0)/r_k\naxis + diagonal weights give exactly 1 for the f_xx, f_yy coefficients (consistent 9-point Laplacian)",
    "dry": "dry\nh < dd", "inv": "invalid\n(outside)",
    "drop": "dropped edges: zero flux;\nthe remaining weights are not renormalised\n(unlike the gradient ∇u)",
    "mono": "all weights are non-negative → diffusion creates no new extremum (discrete maximum principle)",
}}

N = {"ja": {
    "a": "(a) ゼロ方程式モデル  ν = ν0 + α·u*·h,  u* = √g·n·|V|·h^(−1/6)",
    "b": "(b) 陽解法の安定上界  ν_max = Δx²/(2.83·dt)(既定の p_diagratio)",
    "xlabel_a": "水深 h (m)", "ylabel_a": "ν (m²/s)",
    "l1": "α = 0.41/6(既定。Elder 型)、n = 0.03、|V| = 1 m/s",
    "l2": "α = 0.3(横断混合を強める校正例)、n = 0.03、|V| = 1 m/s",
    "l3": "α = 0.41/6、n = 0.03、|V| = 3 m/s",
    "xlabel_b": "格子幅 Δx (m)", "ylabel_b": "ν_max (m²/s)",
    "dt": "dt = {v} s",
    "band": "実用的な ν の範囲(0.01〜10 m²/s)",
    "note": "ν がこの上界を超えると\nモデル 2 はクランプ、モデル 1 は警告",
}, "en": {
    "a": "(a) Zero-equation model  ν = ν0 + α·u*·h,  u* = √g·n·|V|·h^(−1/6)",
    "b": "(b) Explicit stability bound  ν_max = Δx²/(2.83·dt) (default p_diagratio)",
    "xlabel_a": "depth h (m)", "ylabel_a": "ν (m²/s)",
    "l1": "α = 0.41/6 (default, Elder type), n = 0.03, |V| = 1 m/s",
    "l2": "α = 0.3 (calibration for stronger transverse mixing), n = 0.03, |V| = 1 m/s",
    "l3": "α = 0.41/6, n = 0.03, |V| = 3 m/s",
    "xlabel_b": "grid spacing Δx (m)", "ylabel_b": "ν_max (m²/s)",
    "dt": "dt = {v} s",
    "band": "practical range of ν (0.01–10 m²/s)",
    "note": "above this bound model 2 clamps ν\nand model 1 warns",
}}

PD = 2 / (2 + np.sqrt(2))     # 既定の p_diagratio


def cell_dot(ax, x, y, color=C_P, z=7):
    ax.add_patch(Circle((x, y), 0.07, fc=color, ec="none", zorder=z))


def draw_stencil_panel(ax, t, dead=None):
    """3×3 のセルと中央セルから 8 近傍へのフラックス。dead: 欠落させる近傍 (di, dj) → 種別"""
    dead = dead or {}
    grid(ax, 0, 0, 3, 3, 1, C_P, 0.6)
    c = np.array([1.5, 1.5])
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            x, y = 1.5 + di, 1.5 + dj
            if (di, dj) in dead:
                kind = dead[(di, dj)]
                ax.add_patch(Rectangle((x - 0.5, y - 0.5), 1, 1, fc=C_SHAL_, ec="none", zorder=0,
                                       hatch="///" if kind == "inv" else None))
                label(ax, x, y + 0.28, t[kind], color=C_P, fs=7.8, va="center", box=True)
            cell_dot(ax, x, y)
    # passage widths: axis (segment on the cell face), diagonal (segment at the corner)
    lp = 1 - PD; ld = PD / 2
    for (di, dj) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        n = np.array([di, dj]); tt = np.array([-dj, di])
        m = c + 0.5 * n
        p0, p1 = m - 0.5 * lp * tt, m + 0.5 * lp * tt
        dropped = (di, dj) in dead
        ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color=C_X if not dropped else C_P, lw=3.2 if not dropped else 1.2,
                ls="-" if not dropped else ":", zorder=5, solid_capstyle="butt")
    for (di, dj) in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        corner = c + 0.5 * np.array([di, dj])
        tt = np.array([-dj, di]) / np.sqrt(2)
        hl = ld * np.sqrt(2) / 2          # l_d = sqrt(2)·ld·Δ, half of it
        p0, p1 = corner - hl * tt, corner + hl * tt
        dropped = (di, dj) in dead
        ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color=C_X if not dropped else C_P, lw=3.2 if not dropped else 1.2,
                ls="-" if not dropped else ":", zorder=5, solid_capstyle="butt")
    # flux arrows from the centre toward each neighbour
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            if di == dj == 0: continue
            n = np.array([di, dj], dtype=float); n /= np.linalg.norm(n)
            dropped = (di, dj) in dead
            if dropped: continue
            arrow(ax, c + 0.18 * n, c + 0.62 * n, C_C, lw=1.1)
    label(ax, 1.5, 1.74, t["f0"], color="k", fs=9, fontweight="bold", box=True)


def draw_stencil(lang):
    t = T[lang]
    fig, axs = plt.subplots(1, 2, figsize=(13.0, 4.5), gridspec_kw={"width_ratios": [1.15, 1]})
    for ax, key in zip(axs, ("a", "b")):
        ax.set_aspect("equal"); ax.set_anchor("N"); ax.axis("off")
        ax.set_title(t[key], loc="left", fontsize=9.8)
    ax = axs[0]
    draw_stencil_panel(ax, t)
    label(ax, 3.25, 2.55, t["flux"], color=C_C, fs=8.5, ha="left")
    label(ax, 3.25, 1.95, t["nue"], color=C_C, fs=8.5, ha="left")
    label(ax, 3.25, 1.35, t["lp"], color=C_X, fs=8.5, ha="left")
    label(ax, 3.25, 1.0, t["ld"], color=C_X, fs=8.5, ha="left")
    label(ax, 0.0, -0.45, t["sum"], color="k", fs=8.5, ha="left", va="top")
    ax.set_xlim(-0.2, 7.4); ax.set_ylim(-1.5, 3.3)
    ax = axs[1]
    draw_stencil_panel(ax, t, dead={(1, 0): "dry", (1, 1): "dry", (1, -1): "inv", (0, -1): "inv"})
    label(ax, 3.25, 2.3, t["drop"], color=C_P, fs=8.5, ha="left")
    label(ax, 0.0, -0.45, t["mono"], color="#3f7a2a", fs=8.5, ha="left", va="top")
    ax.set_xlim(-0.2, 6.6); ax.set_ylim(-1.5, 3.3)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.92, bottom=0.03, wspace=0.02)
    return save(fig, "diffusion_stencil", lang)


C_SHAL_ = "#e6e4df"


def draw_nu(lang):
    t = N[lang]
    fig, axs = plt.subplots(1, 2, figsize=(12.0, 4.6))
    g = 9.81
    ax = axs[0]
    h = np.linspace(0.05, 10, 300)
    def nu(alpha, n, V): return alpha * np.sqrt(g) * n * V * h**(5 / 6)
    ax.plot(h, nu(0.41 / 6, 0.03, 1.0), color=C_X, lw=2.0, label=t["l1"])
    ax.plot(h, nu(0.3, 0.03, 1.0), color=C_C, lw=1.5, ls="--", label=t["l2"])
    ax.plot(h, nu(0.41 / 6, 0.03, 3.0), color=C_G, lw=1.5, ls="-.", label=t["l3"])
    ax.set_xlabel(t["xlabel_a"], fontsize=9); ax.set_ylabel(t["ylabel_a"], fontsize=9)
    ax.set_xlim(0, 10); ax.set_ylim(0, 1.0)
    ax.tick_params(labelsize=8); ax.legend(loc="upper left", fontsize=7.8, frameon=False)
    ax.set_title(t["a"], loc="left", fontsize=9.8)
    ax = axs[1]
    dx = np.logspace(-1, 3, 200)
    ax.axhspan(0.01, 10, color="#eef3fa", zorder=0)
    ax.text(0.13, 2.0, t["band"], fontsize=8.0, color=C_C)
    for dt, col, ls in ((0.01, C_X, "-"), (0.1, C_C, "--"), (1.0, C_G, "-."), (10.0, C_P, ":")):
        ax.plot(dx, dx**2 / (2.83 * dt), color=col, lw=1.6, ls=ls, label=t["dt"].format(v=dt))
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlim(0.1, 1000); ax.set_ylim(1e-4, 1e6)
    ax.set_xlabel(t["xlabel_b"], fontsize=9); ax.set_ylabel(t["ylabel_b"], fontsize=9)
    ax.tick_params(labelsize=8); ax.legend(loc="lower right", fontsize=7.8, frameon=False)
    ax.text(0.13, 2e4, t["note"], fontsize=8.0, color=C_P)
    ax.set_title(t["b"], loc="left", fontsize=9.8)
    fig.subplots_adjust(left=0.06, right=0.99, top=0.91, bottom=0.14, wspace=0.22)
    return save(fig, "diffusion_nu", lang)


def draw(lang):
    draw_nu(lang)
    return draw_stencil(lang)
