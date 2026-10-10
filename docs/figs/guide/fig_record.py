"""record_transect: 計測 — プローブ(セル番号)とフラックス測線(セル番号の DDA 階段面 / 実座標の線分)、符号規約。"""
from _style import *

T = {"ja": {
    "ta": "(a) セル番号指定(pbxytype = flxytype = 0。1 スタート)",
    "tb": "(b) 実座標指定の測線(flxytype = 1)",
    "north": "北", "flow": "流れ\n(下流)", "chan": "河道",
    "probe": "プローブ pbxy(:,1) = 3, 2\n→ probes/probe0001.csv",
    "rb": "右岸(始点)", "lb": "左岸(終点)",
    "fl": "測線 flxy(:,1) = 右岸 ix, iy, 左岸 ix, iy\n→ fluxes/flux0001.csv",
    "dda": "DDA 階段面(両端セルの中心を結ぶ線を\nセル境界に沿う階段に)。横切るセル間の流量の和",
    "sign": "正(+): 始点→終点の右側へ抜ける流れ\n(右岸→左岸なら下流向きが正)",
    "same": "両端に同一セルは不可",
    "seg": "線分がかすめる各セルで\n(線分に直交する流量成分)× セル内線分長 を積算",
    "short": "1 セル内の短い\n測線も可",
    "sign2": "正(+): 同じ規約(進行方向の右側)",
    "xy": "x 東・y 北(地理参照があれば絶対座標、なければ南西端原点)",
}, "en": {
    "ta": "(a) Cell-number specification (pbxytype = flxytype = 0; 1-based)",
    "tb": "(b) Transect by real coordinates (flxytype = 1)",
    "north": "N", "flow": "flow\n(downstream)", "chan": "channel",
    "probe": "probe pbxy(:,1) = 3, 2\n→ probes/probe0001.csv",
    "rb": "right bank (start)", "lb": "left bank (end)",
    "fl": "transect flxy(:,1) = right-bank ix, iy, left-bank ix, iy\n→ fluxes/flux0001.csv",
    "dda": "DDA staircase surface (the line joining the end-cell\ncentres, stepped along cell interfaces); sum of crossing fluxes",
    "sign": "positive (+): flow passing to the right of start→end\n(right bank→left bank makes downstream positive)",
    "same": "the two ends must not be the same cell",
    "seg": "in every cell the segment grazes:\n(flux component normal to the segment) × in-cell length",
    "short": "a short transect\ninside one cell is fine",
    "sign2": "positive (+): same rule (right of the direction of travel)",
    "xy": "x east, y north (absolute if georeferenced, else SW-corner origin)",
}}


def draw(lang):
    t = T[lang]
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 5.4), gridspec_kw={"width_ratios": [1.25, 1]})
    # ------------------------------------------------ (a) cell numbers
    ax = axs[0]; ax.set_aspect("equal"); ax.set_anchor("N"); ax.axis("off")
    NX, NY = 10, 8
    # channel: columns i = 5..6 flowing south (j increasing)
    ax.add_patch(Rectangle((4, 0), 2, NY, fc=C_WATER_L, ec="none", zorder=0))
    grid(ax, 0, 0, NX, NY, 1, C_P, 0.6)
    label(ax, 5, NY - 0.5, t["chan"], color=C_C, fs=9)
    arrow(ax, (5, NY - 1.0), (5, NY - 2.3), C_C, lw=2.0)
    label(ax, 5, NY - 2.6, t["flow"], color=C_C, fs=8.5, va="top", box=True)
    # probe at (i, j) = (3, 2)
    pi, pj = 3, 2
    ax.add_patch(Rectangle((pi - 1, NY - pj), 1, 1, fc=C_B, ec="none", alpha=0.8, zorder=1))
    ax.plot([pi - 0.5], [NY - pj + 0.5], "o", color=C_X, ms=7, zorder=6)
    label(ax, pi - 0.5, NY + 0.25, t["probe"], color=C_X, fs=8.5, ha="left", va="bottom")
    ax.plot([pi - 0.5, pi - 0.5], [NY - pj + 0.5, NY + 0.2], color=C_X, lw=0.8, zorder=5)
    # transect: start cell (3,6) -> end cell (8,5); DDA staircase along cell interfaces
    si, sj, ei, ej = 3, 6, 8, 5
    sx, sy, ex, ey = si - 0.5, NY - sj + 0.5, ei - 0.5, NY - ej + 0.5
    ax.plot([sx, ex], [sy, ey], color=C_X, lw=1.0, ls="--", zorder=4)
    ax.plot([sx], [sy], "s", color=C_X, ms=8, zorder=6); ax.plot([ex], [ey], "s", color=C_X, ms=8, zorder=6)
    ax.add_patch(FancyArrowPatch((sx, sy), (ex, ey), arrowstyle="-|>", mutation_scale=14, color=C_X, lw=0, zorder=5))
    stair = [(2, 3), (5, 3), (5, 4), (8, 4)]
    ax.plot([p[0] for p in stair], [p[1] for p in stair], color=C_X, lw=3.0, solid_capstyle="round", zorder=5)
    label(ax, sx - 0.6, sy, t["rb"], color=C_X, fs=8.5, ha="right")
    label(ax, ex + 0.6, ey, t["lb"], color=C_X, fs=8.5, ha="left")
    # positive direction: to the right of start->end = south = downstream
    arrow(ax, (5.0, 3.9), (5.0, 2.1), C_G, lw=2.4)
    label(ax, 5.5, 2.0, "+", color="#3f7a2a", fs=14, ha="left", va="top", fontweight="bold")
    label(ax, 0, -0.4, t["sign"], color="#3f7a2a", fs=8.8, ha="left", va="top")
    label(ax, 0, -1.25, t["dda"], color=C_X, fs=8.5, ha="left", va="top")
    label(ax, 0, -2.15, t["same"], color=C_P, fs=8.5, ha="left", va="top")
    label(ax, 0, NY + 1.35, t["fl"], color=C_X, fs=8.5, ha="left", va="bottom")
    label(ax, NX + 0.8, NY - 0.5, t["north"], color=C_P, fs=10, fontweight="bold")
    ax.annotate("", (NX + 0.8, NY - 0.65), (NX + 0.8, NY - 1.4), arrowprops=dict(arrowstyle="-|>", color=C_P, lw=1.2))
    ax.set_xlim(-2.3, NX + 1.6); ax.set_ylim(-2.7, NY + 2.4)
    ax.set_title(t["ta"], loc="left", fontsize=10)
    # ------------------------------------------------ (b) real coordinates
    ax = axs[1]; ax.set_aspect("equal"); ax.set_anchor("N"); ax.axis("off")
    nx, ny = 5, 4
    ax.add_patch(Rectangle((0, 0), nx, ny, fc="white", ec="none", zorder=0))
    grid(ax, 0, 0, nx, ny, 1, C_P, 0.6)
    # long segment crossing several cells
    p1, p2 = (0.6, 0.7), (3.6, 2.6)
    ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=C_X, lw=2.6, solid_capstyle="round", zorder=4)
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=14, color=C_X, lw=0, zorder=5))
    ax.plot([p1[0], p2[0]], [p1[1], p2[1]], "o", color=C_X, ms=6, zorder=6)
    # in-cell pieces: mark the crossings with grid lines
    import math
    vx, vy = p2[0] - p1[0], p2[1] - p1[1]
    L = math.hypot(vx, vy); ux, uy = vx / L, vy / L
    nxv, nyv = uy, -ux                       # right-hand normal of the direction of travel
    ts = [0.0] + sorted([(k - p1[0]) / vx for k in range(1, nx) if 0 < (k - p1[0]) / vx < 1] +
                        [(k - p1[1]) / vy for k in range(1, ny) if 0 < (k - p1[1]) / vy < 1]) + [1.0]
    for a, b in zip(ts[:-1], ts[1:]):
        m = ((a + b) / 2)
        mx, my = p1[0] + m * vx, p1[1] + m * vy
        ax.plot([p1[0] + a * vx, p1[0] + b * vx], [p1[1] + a * vy, p1[1] + b * vy], "|", color="k", ms=9, mew=1.2, zorder=6)
        arrow(ax, (mx, my), (mx + 0.45 * nxv, my + 0.45 * nyv), C_G, lw=1.5)
    label(ax, p2[0] + 0.15, p2[1] + 0.15, "+", color="#3f7a2a", fs=14, ha="left", va="bottom", fontweight="bold")
    # short segment inside one cell
    q1, q2 = (3.3, 1.3), (3.9, 1.75)
    ax.plot([q1[0], q2[0]], [q1[1], q2[1]], color=C_X, lw=2.6, solid_capstyle="round", zorder=4)
    ax.add_patch(FancyArrowPatch(q1, q2, arrowstyle="-|>", mutation_scale=14, color=C_X, lw=0, zorder=5))
    ax.plot([q1[0], q2[0]], [q1[1], q2[1]], "o", color=C_X, ms=6, zorder=6)
    label(ax, 4.1, 1.35, t["short"], color=C_X, fs=8.5, ha="left", va="top", box=True)
    # axes
    ax.add_patch(FancyArrowPatch((0, 0), (nx + 0.5, 0), arrowstyle="-|>", mutation_scale=11, color="k", lw=1.2, zorder=3))
    ax.add_patch(FancyArrowPatch((0, 0), (0, ny + 0.5), arrowstyle="-|>", mutation_scale=11, color="k", lw=1.2, zorder=3))
    label(ax, nx + 0.6, 0, "x", fs=9.5, ha="left"); label(ax, 0, ny + 0.6, "y", fs=9.5, va="bottom")
    label(ax, 0, ny + 1.3, t["xy"], color=C_P, fs=8.5, ha="left", va="bottom")
    label(ax, 0, -0.5, t["seg"], color="#3f7a2a", fs=8.8, ha="left", va="top")
    label(ax, 0, -1.4, t["sign2"], color="#3f7a2a", fs=8.5, ha="left", va="top")
    ax.set_xlim(-0.5, nx + 2.2); ax.set_ylim(-2.1, ny + 2.1)
    ax.set_title(t["tb"], loc="left", fontsize=10)
    fig.tight_layout()
    return save(fig, "record_transect", lang)
