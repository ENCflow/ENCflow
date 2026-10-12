"""advection_*: 移流項のスキーム(users_guide/advection.md)の模式図。

  advection_cv.png     (a) スキーム 1 のステンシル(セル中心勾配 → 両側平均)
                       (b) スキーム 2・3 の運動量検査体積(軸エッジ)
                       (c) 同(対角エッジ)
  advection_muscl.png  (a) 線 k 上の面値の再構成(1 次風上と MUSCL)
                       (b) van Leer 限定器 ψ(r) と TVD 領域
  幾何は m_swflow_enc_adv.f90(adv_prepare_mc / adv_prepare_v1)に合わせる。
"""
import numpy as np
from _style import *

T = {"ja": {
    "a": "(a) スキーム 1: セル中心勾配(非保存形)",
    "b": "(b) スキーム 2・3: 運動量検査体積(軸エッジ)",
    "c": "(c) 同(対角エッジ)",
    "a_c": "c", "a_n": "n", "a_e": "u_e",
    "a_sten": "3×3 の重み付き差分で\n∇u, ∇v(風上側を重く)",
    "a_avg": "両セルの −(u·∇)u を平均し\n法線 n_k に投影 → A_e",
    "a_foot": "実効ステンシル: 4×3 セル(両側セル平均で勾配が 5 エッジ幅に鈍る)",
    "cv": "検査体積 A = L·W",
    "L_ax": "L = Δx(c–n 間)", "W_ax": "W = Δy",
    "L_dg": "L = Δr", "W_dg": "W = 2ΔxΔy/Δr",
    "face_c": "面 c(q_c)", "face_n": "面 n(q_n)",
    "lat_p": "側方面 +t(q_t+)", "lat_m": "側方面 −t(q_t−)",
    "line_k": "線 k 上のエッジ流速(風上側の供給元)",
    "par": "平行な隣接エッジ u_t±\n(側方面の 1 次風上値)",
    "mn": "側方面の流束 = 面を横切る\n2 本の ENC エッジ流量の平均",
    "qproj": "q_c, q_n: セル流量 (m, n) の k 方向投影",
    "legend_cell": "セル中心: h, z, (u, v), (m, n)",
    "legend_edge": "エッジ: 法線流速 uv・流量 mn",
    "legend_cv": "運動量検査体積とその面",
}, "en": {
    "a": "(a) Scheme 1: cell-centre gradient (non-conservative)",
    "b": "(b) Schemes 2, 3: momentum control volume (axis edge)",
    "c": "(c) Same (diagonal edge)",
    "a_c": "c", "a_n": "n", "a_e": "u_e",
    "a_sten": "weighted 3×3 differences give\n∇u, ∇v (upwind side weighted more)",
    "a_avg": "average −(u·∇)u of both cells,\nproject onto the normal n_k → A_e",
    "a_foot": "effective stencil: 4×3 cells\n(the two-cell average smears the gradient over 5 edges)",
    "cv": "control volume A = L·W",
    "L_ax": "L = Δx (c to n)", "W_ax": "W = Δy",
    "L_dg": "L = Δr", "W_dg": "W = 2ΔxΔy/Δr",
    "face_c": "face c (q_c)", "face_n": "face n (q_n)",
    "lat_p": "lateral face +t (q_t+)", "lat_m": "lateral face −t (q_t−)",
    "line_k": "edge velocities on line k (upwind donors)",
    "par": "parallel neighbouring edges u_t±\n(first-order upwind value of the lateral faces)",
    "mn": "lateral flux = mean of the two ENC\nedge fluxes crossing the face",
    "qproj": "q_c, q_n: cell flux (m, n) projected onto k",
    "legend_cell": "cell centre: h, z, (u, v), (m, n)",
    "legend_edge": "edge: normal velocity uv, flux mn",
    "legend_cv": "momentum control volume and its faces",
}}

M = {"ja": {
    "a": "(a) 線 k 上の面値の再構成(面 c、q_c > 0 の場合)",
    "b": "(b) 限定器 $\\psi$(r)",
    "flow": "流れ q_c > 0", "face": "面 c", "cell_c": "セル c", "cell_n": "セル n",
    "s2": "スキーム 2: ū_c = u_m(1 次風上)",
    "s3": "スキーム 3: ū_c = u_m + $\\psi$(r)/2 · (u_e − u_m)",
    "r": "r = (u_m − u_mm)/(u_e − u_m)",
    "vl": "van Leer  $\\psi$ = (r + |r|)/(1 + |r|)",
    "central": "$\\psi$ = 1: 中心差分", "lw": "$\\psi$ = r", "tvd": "TVD 領域(Sweby)",
    "upwind": "$\\psi$ = 0: 1 次風上(スキーム 2)",
    "ext": "$r \\leq 0$(極値・不連続)で $\\psi = 0$ → 風上に退化",
    "xlabel": "r(風上側勾配 / 風下側勾配)",
}, "en": {
    "a": "(a) Face-value reconstruction on line k (face c, q_c > 0)",
    "b": "(b) Limiter $\\psi$(r)",
    "flow": "flow q_c > 0", "face": "face c", "cell_c": "cell c", "cell_n": "cell n",
    "s2": "scheme 2: ū_c = u_m (first-order upwind)",
    "s3": "scheme 3: ū_c = u_m + $\\psi$(r)/2 · (u_e − u_m)",
    "r": "r = (u_m − u_mm)/(u_e − u_m)",
    "vl": "van Leer  $\\psi$ = (r + |r|)/(1 + |r|)",
    "central": "$\\psi$ = 1: central", "lw": "$\\psi$ = r", "tvd": "TVD region (Sweby)",
    "upwind": "$\\psi$ = 0: first-order upwind (scheme 2)",
    "ext": "$\\psi = 0$ for $r \\leq 0$ (extrema, discontinuities) → degrades to upwind",
    "xlabel": "r (upwind slope / downwind slope)",
}}

C_CV = "#d9922a"       # 検査体積(橙)
C_CV_F = "#fdf1dc"
C_STEN_C = "#dbe8fa"   # c のステンシル(青)
C_STEN_N = "#fbefd8"   # n のステンシル(黄)


def edge_marker(ax, x, y, color=C_C, diag=False, size=0.16, z=8, fill=True):
    """エッジ量の位置(軸: 塗り四角、対角: 白抜き四角。fig_swflow と同じ流儀)。"""
    fc = color if fill else "white"
    ax.add_patch(Rectangle((x - size / 2, y - size / 2), size, size, fc=fc, ec=color, lw=1.1,
                           zorder=z, angle=45 if diag else 0, rotation_point="center"))


def cell_dot(ax, x, y, color=C_P, z=7):
    ax.add_patch(Circle((x, y), 0.07, fc=color, ec="none", zorder=z))


def panel_scheme1(ax, t):
    NX, NY = 6, 3
    grid(ax, 0, 0, NX, NY, 1, C_P, 0.6)
    cx, cy = 2.5, 1.5        # c
    nx_, ny_ = 3.5, 1.5      # n
    ax.add_patch(Rectangle((cx - 1.5, cy - 1.5), 3, 3, fc=C_STEN_C, ec="none", zorder=0))
    ax.add_patch(Rectangle((nx_ - 1.5, ny_ - 1.5), 3, 3, fc=C_STEN_N, ec="none", zorder=0, alpha=0.75))
    for i in range(NX):
        for j in range(NY):
            cell_dot(ax, i + 0.5, j + 0.5)
    for (x0, y0) in ((cx, cy), (nx_, ny_)):
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                if di == dj == 0:
                    continue
                ax.annotate("", (x0 + di * 0.78, y0 + dj * 0.78), (x0 + di * 0.22, y0 + dj * 0.22),
                            arrowprops=dict(arrowstyle="-", color=C_C if x0 == cx else "#b07a10", lw=0.8, alpha=0.8), zorder=3)
    edge_marker(ax, 3.0, 1.5, C_X, size=0.2)
    label(ax, cx, cy + 0.22, t["a_c"], color=C_C, fs=10, fontweight="bold")
    label(ax, nx_, ny_ + 0.22, t["a_n"], color="#b07a10", fs=10, fontweight="bold")
    label(ax, 3.0, 1.22, t["a_e"], color=C_X, fs=9, va="top")
    label(ax, cx - 0.05, -0.35, t["a_sten"], color=C_C, fs=8.5, va="top")
    label(ax, nx_ + 1.1, NY + 0.35, t["a_avg"], color=C_X, fs=8.5, va="bottom", ha="center")
    ax.annotate("", (3.05, 1.62), (4.4, NY + 0.3), arrowprops=dict(arrowstyle="-|>", color=C_X, lw=1.0), zorder=5)
    ax.add_patch(Rectangle((1, 0), 4, 3, fill=False, ec=C_X, lw=1.4, ls="--", zorder=4))
    label(ax, NX / 2, -1.25, t["a_foot"], color=C_P, fs=8.3, va="top")
    ax.set_xlim(-0.5, NX + 0.5); ax.set_ylim(-1.9, NY + 1.3)


def panel_axis(ax, t):
    NX, NY = 7, 3
    grid(ax, 0, 0, NX, NY, 1, C_P, 0.6)
    j = 1.5
    cx, nx_ = 3.5, 4.5
    # control volume
    ax.add_patch(Rectangle((cx, j - 0.5), 1, 1, fc=C_CV_F, ec=C_CV, lw=2.0, zorder=2))
    for i in range(NX):
        for jj in range(NY):
            cell_dot(ax, i + 0.5, jj + 0.5)
    # line k edges
    for x, s in zip((2, 3, 4, 5, 6), ("u_mm", "u_m", "u_e", "u_p", "u_pp")):
        edge_marker(ax, x, j, C_X if x == 4 else C_C, size=0.2 if x == 4 else 0.16)
        label(ax, x, j - 0.3, s, color=C_X if x == 4 else C_C, fs=8.5, va="top")
    # parallel edges
    for y, s in ((j + 1, "u_t+"), (j - 1, "u_t−")):
        edge_marker(ax, 4, y, C_G)
        label(ax, 4.28, y, s, color="#3f7a2a", fs=8.5, ha="left")
    # faces and fluxes
    label(ax, cx - 0.12, j + 0.62, t["face_c"], color=C_CV, fs=8.3, va="bottom", ha="right")
    label(ax, nx_ + 0.12, j + 0.62, t["face_n"], color=C_CV, fs=8.3, va="bottom", ha="left")
    arrow(ax, (cx - 0.45, j + 0.25), (cx + 0.05, j + 0.25), C_CV, lw=1.4)
    arrow(ax, (nx_ - 0.05, j + 0.25), (nx_ + 0.45, j + 0.25), C_CV, lw=1.4)
    arrow(ax, (4.0, j + 0.3), (4.0, j + 0.72), C_CV, lw=1.2)
    arrow(ax, (4.0, j - 0.3), (4.0, j - 0.72), C_CV, lw=1.2)
    label(ax, 4.0, NY + 0.15, t["lat_p"], color=C_CV, fs=8.3, va="bottom")
    label(ax, 4.0, -0.15, t["lat_m"], color=C_CV, fs=8.3, va="top")
    # dimensions
    ax.annotate("", (cx, NY + 0.95), (nx_, NY + 0.95), arrowprops=dict(arrowstyle="<->", color=C_CV, lw=1))
    label(ax, 4.0, NY + 1.05, t["L_ax"], color=C_CV, fs=8.3, va="bottom")
    ax.annotate("", (NX + 0.3, j - 0.5), (NX + 0.3, j + 0.5), arrowprops=dict(arrowstyle="<->", color=C_CV, lw=1))
    label(ax, NX + 0.45, j, t["W_ax"], color=C_CV, fs=8.3, ha="left")
    label(ax, 0.2, -0.85, t["line_k"], color=C_C, fs=8.3, ha="left", va="top")
    label(ax, 0.2, -1.3, t["qproj"], color=C_CV, fs=8.3, ha="left", va="top")
    ax.set_xlim(-0.3, NX + 2.3); ax.set_ylim(-1.8, NY + 1.7)


def panel_diag(ax, t):
    NX, NY = 6, 6
    grid(ax, 0, 0, NX, NY, 1, C_P, 0.6)
    c = np.array([2.5, 2.5]); n = np.array([3.5, 3.5])
    d = (n - c) / np.linalg.norm(n - c)
    tt = np.array([d[1], -d[0]])              # +t = (-n8y, n8x) の向きは図では無関係
    hw = 1 / np.sqrt(2)                       # W/2 = ΔxΔy/Δr
    poly = [c + hw * tt, n + hw * tt, n - hw * tt, c - hw * tt]
    ax.add_patch(Polygon(poly, closed=True, fc=C_CV_F, ec=C_CV, lw=2.0, zorder=2))
    for i in range(NX):
        for jj in range(NY):
            cell_dot(ax, i + 0.5, jj + 0.5)
    # line k edges (diagonal, at cell corners)
    for s, m in zip((-2, -1, 0, 1, 2), ("u_mm", "u_m", "u_e", "u_p", "u_pp")):
        p = np.array([3.0, 3.0]) + s * np.array([1.0, 1.0])
        edge_marker(ax, p[0], p[1], C_X if s == 0 else C_C, diag=True, size=0.2 if s == 0 else 0.16, fill=False)
        if s == 0:
            label(ax, p[0], p[1] - 0.22, m, color=C_X, fs=8.5, va="top")
        else:
            label(ax, p[0] + 0.3, p[1] - 0.15, m, color=C_C, fs=8.5, ha="left", va="top")
    # parallel neighbouring edges (offset by δ = (1,-1), (-1,1))
    for off, m in (((1, -1), "u_t+"), ((-1, 1), "u_t−")):
        p = np.array([3.0, 3.0]) + np.array(off)
        edge_marker(ax, p[0], p[1], C_G, diag=True, fill=False)
        label(ax, p[0] + 0.3, p[1] + 0.05, m, color="#3f7a2a", fs=8.5, ha="left")
    # faces
    label(ax, c[0] - 0.95, c[1] - 0.5, t["face_c"], color=C_CV, fs=8.3, ha="right")
    label(ax, n[0] - 0.25, n[1] + 1.25, t["face_n"], color=C_CV, fs=8.3, ha="right")
    arrow(ax, c - 0.5 * d, c + 0.02 * d, C_CV, lw=1.4)
    arrow(ax, n - 0.02 * d, n + 0.5 * d, C_CV, lw=1.4)
    mid = (c + n) / 2
    arrow(ax, mid + 0.3 * tt, mid + hw * tt + 0.35 * tt, C_CV, lw=1.2)
    arrow(ax, mid - 0.3 * tt, mid - hw * tt - 0.35 * tt, C_CV, lw=1.2)
    # the two ENC edges crossing the +t lateral face (c -> c+δ, n -> n+δ)
    for p0 in (c, n):
        q = p0 + np.array([1.0, -1.0])
        ax.plot([p0[0], q[0]], [p0[1], q[1]], color="#3f7a2a", lw=1.0, ls=":", zorder=5)
    label(ax, NX + 1.3, -0.2, t["mn"], color="#3f7a2a", fs=8.0, ha="right", va="top")
    # dimensions
    label(ax, 0.1, -0.2, t["L_dg"] + "   " + t["W_dg"], color=C_CV, fs=8.3, ha="left", va="top")
    ax.set_xlim(-0.3, NX + 1.4); ax.set_ylim(-1.1, NY + 0.3)


def draw_cv(lang):
    t = T[lang]
    fig, axs = plt.subplots(1, 3, figsize=(15.0, 5.0), gridspec_kw={"width_ratios": [1.0, 1.25, 1.0]})
    for ax, key in zip(axs, ("a", "b", "c")):
        ax.set_aspect("equal"); ax.set_anchor("N"); ax.axis("off")
        ax.set_title(t[key], loc="left", fontsize=9.8)
    panel_scheme1(axs[0], t)
    panel_axis(axs[1], t)
    panel_diag(axs[2], t)
    # legend
    fig.text(0.02, 0.035, "●  " + t["legend_cell"] + "     ■  " + t["legend_edge"] + "     ▭  " + t["legend_cv"],
             fontsize=8.5, color=C_P)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.93, bottom=0.08, wspace=0.05)
    return save(fig, "advection_cv", lang)


def draw_muscl(lang):
    t = M[lang]
    fig, axs = plt.subplots(1, 2, figsize=(12.0, 5.4), gridspec_kw={"width_ratios": [1.35, 1]})
    # ---------------------------------------------------------- (a) reconstruction
    ax = axs[0]; ax.axis("off")
    xs = np.array([0, 1, 2, 3, 4])              # u_mm, u_m, u_e, u_p, u_pp (edge positions)
    us = np.array([0.35, 0.45, 0.95, 1.05, 1.08])
    names = ("u_mm", "u_m", "u_e", "u_p", "u_pp")
    # cells (between edges) and faces at cell centres
    for x0 in (0, 1, 2, 3, 4):
        ax.axvline(x0, color="#d8d6d1", lw=0.8, zorder=1)
    ax.axvspan(1, 2, color=C_STEN_C, alpha=0.5, zorder=0)
    ax.axvspan(2, 3, color=C_STEN_N, alpha=0.5, zorder=0)
    ax.axvline(1.5, color=C_CV, lw=1.6, ls="--", zorder=3)
    label(ax, 1.5, 1.42, t["face"], color=C_CV, fs=9, va="bottom")
    label(ax, 1.5, 0.08, t["cell_c"], color=C_P, fs=8.5)
    label(ax, 2.5, 0.08, t["cell_n"], color=C_P, fs=8.5)
    ax.plot(xs, us, "o", color=C_C, ms=6, zorder=6)
    for x, u, s in zip(xs, us, names):
        label(ax, x, u - 0.09, s, color=C_X if s == "u_e" else C_C, fs=8.5, va="top")
    # scheme 2: piecewise-constant upwind value at face
    ax.plot([1.5], [us[1]], "s", color=C_G, ms=8, zorder=7, mfc="white", mew=1.6)
    ax.plot([1, 1.5], [us[1], us[1]], color=C_G, lw=1.4, ls="-", zorder=5)
    # scheme 3: limited reconstruction from u_m toward u_e
    d_ = us[2] - us[1]; r = (us[1] - us[0]) / d_; psi = (r + abs(r)) / (1 + abs(r))
    f3 = us[1] + 0.5 * psi * d_
    ax.plot([1, 1.5], [us[1], f3], color=C_X, lw=1.6, zorder=5)
    ax.plot([1.5], [f3], "D", color=C_X, ms=7, zorder=7)
    label(ax, 1.62, us[1] - 0.02, t["s2"], color="#3f7a2a", fs=8.5, ha="left", va="top")
    label(ax, 1.62, f3 + 0.04, t["s3"], color=C_X, fs=8.5, ha="left", va="bottom")
    label(ax, 1.62, f3 + 0.17, t["r"], color=C_X, fs=8.5, ha="left", va="bottom")
    arrow(ax, (0.1, 1.3), (0.9, 1.3), C_C, lw=1.4)
    label(ax, 0.5, 1.36, t["flow"], color=C_C, fs=8.5, va="bottom")
    ax.set_xlim(-0.3, 4.6); ax.set_ylim(0.0, 1.6)
    ax.set_title(t["a"], loc="left", fontsize=9.8)
    # ---------------------------------------------------------- (b) limiter
    ax = axs[1]
    rr = np.linspace(-1, 4, 400)
    tvd_lo = np.clip(np.minimum(rr, 1), 0, None); tvd_hi = np.clip(np.minimum(2 * rr, 2), 0, None)
    ax.fill_between(rr, tvd_lo, tvd_hi, color="#eef3fa", zorder=0, label=t["tvd"])
    ax.plot(rr, (rr + np.abs(rr)) / (1 + np.abs(rr)), color=C_X, lw=2.0, label=t["vl"], zorder=4)
    ax.axhline(1, color=C_C, lw=1.0, ls="--", label=t["central"], zorder=3)
    ax.plot(rr, rr, color=C_P, lw=0.9, ls=":", label=t["lw"], zorder=3)
    ax.axhline(0, color="#3f7a2a", lw=1.0, ls="-.", label=t["upwind"], zorder=3)
    ax.set_xlim(-1, 4); ax.set_ylim(-0.2, 2.5)
    ax.set_xlabel(t["xlabel"], fontsize=9); ax.set_ylabel("$\\psi$(r)", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, fontsize=7.8, frameon=False)
    ax.text(-0.95, 2.32, t["ext"], fontsize=8.3, color=C_P)
    ax.set_title(t["b"], loc="left", fontsize=9.8)
    fig.subplots_adjust(left=0.03, right=0.99, top=0.91, bottom=0.3, wspace=0.18)
    return save(fig, "advection_muscl", lang)


def draw(lang):
    draw_muscl(lang)
    return draw_cv(lang)
