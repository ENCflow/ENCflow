"""Supplement on numerical diffusion by diagonal-edge fluxes (users_guide/diagonal_diffusion.md).

Two figures: the mechanism (scalar first-order upwind, link-wise MUSCL, and the
momentum control volumes of an axis and a diagonal edge in an x-directed shear
flow) and the measured magnitudes (crosswind coefficient against the flow angle,
and the jet profiles after 50 s).

Regenerate only this page with make_guide_figs.py diagdiff.  The numbers are
copied so that the figure needs no result files: the scalar angle table from
docs/wavefield_plan.md sec. 6.1 (Gaussian-blob advection, units u*Delta), the
link-wise MUSCL value from test/tracer (README, configuration B), and the jet
measurements and profiles from developer.md sec. 68.45 (flat, frictionless
closed channel, Delta = 1 m, U0 = 1 m/s, sigma = 10 m, 50 s); refresh them when
those records change.
"""
from _terms import *

T = {'ja': {
 'm_a': '(a) スカラーの 1 次風上: 横断方向の 3 点の平均',
 'm_b': '(b) リンクごとの MUSCL: 面の値をリンクの中点に',
 'm_c': '(c) 運動量の検査体積(x 方向のせん断流 u(y))',
 'flow': '流れ',
 'recv': '受け手',
 'a_note': '受け手が受け取る値: 0.414 C_j + 0.293 (C_j+1 + C_j−1)。自分の値は同じ割合で下流へ出すので、差し引き 0.293 u (C_j+1 − 2C_j + C_j−1)/Δ の拡散になる。',
 'b_note': '斜めのリンクも斜めに沿って再構成する。横断に線形な分布では面の値が C_j±1/2 になり、出入りの重み付き和が釣り合って拡散の主要項が消える。',
 'c_axis': '軸のエッジ: 上流のエッジは同じ行。側方面を横切る 2 本の斜めのリンクは逆向きに同じ量を流し、横断の交換がない',
 'c_diag': '斜めのエッジ: 流向面の上流は 1 行上、側方面の風上値は同じ行と 1 行下の平均。横断方向の差を取り込み、u Δ/2(スキーム 2)・u Δ/4(スキーム 3)の拡散になる',
 'up_flow': '流向面の風上', 'up_lat': '側方面の風上(2 本の平均)', 'cv': '検査体積',
 'row_m1': '1 行上', 'row_0': '同じ行', 'row_p1': '1 行下',
 'g_a': '(a) 横断の数値拡散係数の向きによる違い', 'g_b': '(b) 軸に沿う噴流の横断分布(50 秒後)',
 'g_x': '最寄りの軸からの角度 φ (°)', 'g_y': '横断の数値拡散係数 c(D = c |u| Δ)',
 'enc1': 'スカラー: ENC の 1 次風上', 'nb4': 'スカラー: 4 近傍の 1 次風上', 'two': '波のエネルギー: 2 リンク分解',
 'muscl': 'スカラー: ENC のリンクごとの MUSCL(test/tracer)',
 's2': '運動量: スキーム 2(計測)', 's3': '運動量: スキーム 3(計測)', 'th': '導出(0°・45°)',
 'p_y': '横断位置 y (m)', 'p_u': 'セル流速 u (m/s)', 'p0': '初期(t = 0)', 'p2': 'スキーム 2(50 秒後)', 'p3': 'スキーム 3(50 秒後)',
}, 'en': {
 'm_a': '(a) Scalar, first-order upwind: a three-point crosswind average',
 'm_b': '(b) Link-wise MUSCL: face values at link midpoints',
 'm_c': '(c) Momentum control volumes (x-directed shear flow u(y))',
 'flow': 'flow',
 'recv': 'receiver',
 'a_note': 'The receiver takes 0.414 C_j + 0.293 (C_j+1 + C_j−1) and sends its own value downstream in the same proportions, leaving a diffusion 0.293 u (C_j+1 − 2C_j + C_j−1)/Δ.',
 'b_note': 'Diagonal links are reconstructed along the diagonal. For a crosswind-linear field the face values become C_j±1/2, inflow and outflow balance, and the leading diffusion term vanishes.',
 'c_axis': 'Axis edge: the upstream edge is on the same row; the two diagonal links crossing each lateral face carry equal and opposite fluxes, so there is no crosswind exchange',
 'c_diag': 'Diagonal edge: the flow-face upwind edge is one row up, the lateral-face upwind value is the mean of the same row and one row down; the crosswind differences give a diffusion of u Δ/2 (scheme 2) or u Δ/4 (scheme 3)',
 'up_flow': 'flow-face upwind', 'up_lat': 'lateral-face upwind (mean of 2)', 'cv': 'control volume',
 'row_m1': 'row above', 'row_0': 'same row', 'row_p1': 'row below',
 'g_a': '(a) Crosswind numerical diffusion against the flow angle', 'g_b': '(b) Cross-stream profile of an axis-aligned jet (after 50 s)',
 'g_x': 'angle from the nearest axis φ (°)', 'g_y': 'crosswind coefficient c (D = c |u| Δ)',
 'enc1': 'scalar: ENC first-order upwind', 'nb4': 'scalar: 4-neighbour first-order upwind', 'two': 'wave energy: two-link decomposition',
 'muscl': 'scalar: ENC link-wise MUSCL (test/tracer)',
 's2': 'momentum: scheme 2 (measured)', 's3': 'momentum: scheme 3 (measured)', 'th': 'derived (0°, 45°)',
 'p_y': 'cross-stream position y (m)', 'p_u': 'cell velocity u (m/s)', 'p0': 'initial (t = 0)', 'p2': 'scheme 2 (after 50 s)', 'p3': 'scheme 3 (after 50 s)',
}}

LIGHT = '#eef3fb'
# wavefield_plan.md sec. 6.1 (units u*Delta)
ANG = [0, 10, 15, 21, 22.5, 30, 45]
ENC1 = [0.293, 0.312, 0.308, 0.293, 0.287, 0.249, 0.146]
NB4 = [0, 0.099, 0.153, 0.216, 0.231, 0.296, 0.354]
# test/tracer README, configuration B: D_y = 0.19 m2/s at u = 1.0 m/s, Delta = 10 m
MUSCL0 = 0.019
# developer.md sec. 68.45: c = 2*sqrt(2)*D_eff/(U0*Delta) from the growth of sigma^2 (10-50 s)
M_ANG = [0, 22.5, 45]
M_S2 = [0.263, 0.259, 0.134]
M_S3 = [0.138, 0.167, 0.070]
TH_ANG = [0, 45]
TH_S2 = [0.293, 0.146]
TH_S3 = [0.146, 0.073]
# developer.md sec. 68.45: cell-velocity profile after 50 s (axis-aligned jet, mean of columns 201-400), y = -35..35 m
PY = list(range(-35, 36))
P_S2 = [0.0022, 0.0032, 0.0044, 0.0062, 0.0085, 0.0116, 0.0157, 0.0211, 0.028, 0.037, 0.0485, 0.0631, 0.0811, 0.1032, 0.1296, 0.1604, 0.1954, 0.2342, 0.2767, 0.3222, 0.37, 0.4197, 0.4704, 0.5217, 0.5725, 0.6224, 0.6706, 0.7162, 0.7585, 0.7968, 0.8304, 0.8588, 0.8814, 0.8979, 0.9078, 0.9112, 0.9078, 0.8979, 0.8814, 0.8588, 0.8304, 0.7968, 0.7585, 0.7162, 0.6706, 0.6224, 0.5725, 0.5217, 0.4704, 0.4197, 0.37, 0.3222, 0.2767, 0.2342, 0.1954, 0.1604, 0.1296, 0.1032, 0.0811, 0.0631, 0.0485, 0.037, 0.028, 0.0211, 0.0157, 0.0116, 0.0085, 0.0062, 0.0044, 0.0032, 0.0022]
P_S3 = [0.0022, 0.0032, 0.0044, 0.0061, 0.0084, 0.0114, 0.0154, 0.0205, 0.0271, 0.0356, 0.0462, 0.0594, 0.0756, 0.0954, 0.119, 0.1469, 0.1791, 0.2158, 0.2568, 0.3018, 0.3503, 0.4018, 0.4554, 0.5105, 0.566, 0.621, 0.6744, 0.7254, 0.7729, 0.816, 0.8539, 0.8858, 0.9112, 0.9295, 0.9406, 0.9443, 0.9406, 0.9295, 0.9112, 0.8858, 0.8539, 0.816, 0.7729, 0.7254, 0.6744, 0.621, 0.566, 0.5105, 0.4554, 0.4018, 0.3503, 0.3018, 0.2568, 0.2158, 0.1791, 0.1469, 0.119, 0.0954, 0.0756, 0.0594, 0.0462, 0.0356, 0.0271, 0.0205, 0.0154, 0.0114, 0.0084, 0.0061, 0.0044, 0.0032, 0.0022]


def scalar_panel(ax, t, x0, y0, d, muscl):
    """3 x 3 cells; flow to the right; the centre cell is the receiver."""
    for i in range(3):
        for j in range(3):
            rect(ax, x0 + i * d, y0 + j * d, d, d, LIGHT if (i, j) == (1, 1) else 'white')
    grid(ax, x0, y0, 3, 3, d)
    cen = lambda i, j: np.array([x0 + (i + .5) * d, y0 + (j + .5) * d])
    for j in range(3):
        dot(ax, cen(0, j), MUTED)
    dot(ax, cen(1, 1), BLUE)
    names = ['C_j−1', 'C_j', 'C_j+1']   # screen row 0 is the upper row
    for j, nm in enumerate(names):
        text(ax, *(cen(0, j) + [-d * .42, -d * .36]), nm, 10, color=INK)
    text(ax, *(cen(1, 1) + [12, 10]), t['recv'], 9.5, color=BLUE)
    if not muscl:
        arrow(ax, [cen(0, 1) + [8, 0], cen(1, 1) - [10, 0]], ORANGE, 2.2)
        text(ax, *((cen(0, 1) + cen(1, 1)) / 2 + [-24, -26]), '0.414', 10, color=ORANGE)
        for j in (0, 2):
            p, q = cen(0, j), cen(1, 1)
            v = (q - p) / np.linalg.norm(q - p)
            arrow(ax, [p + v * 10, q - v * 12], ORANGE, 1.6)
            m = (p + q) / 2
            text(ax, *(m + ([6, -30] if j == 0 else [6, 10])), '0.293', 10, color=ORANGE)
    else:
        for j in (0, 2):
            p, q = cen(0, j), cen(1, 1)
            line(ax, [p, q], BLUE, 1.2, z=5)
            m = (p + q) / 2
            edge(ax, m, GREEN, True)
            text(ax, *(m + ([10, -26] if j == 0 else [10, 8])), 'C_j−1/2' if j == 0 else 'C_j+1/2', 10, color=GREEN)
        line(ax, [cen(0, 1), cen(1, 1)], BLUE, 1.2, z=5)
        edge(ax, (cen(0, 1) + cen(1, 1)) / 2, GREEN, True)
    arrow(ax, [(x0, y0 - 26), (x0 + 3 * d, y0 - 26)], MUTED, 1.2)
    text(ax, x0 + 3 * d + 8, y0 - 34, t['flow'], 9.5, color=MUTED)


def axis_cv(ax, t, x0, y0, d):
    """5 x 3 cells; the axis edge between columns 2 and 3 of the middle row."""
    for i in range(5):
        for j in range(3):
            rect(ax, x0 + i * d, y0 + j * d, d, d, 'white')
    grid(ax, x0, y0, 5, 3, d)
    cen = lambda i, j: np.array([x0 + (i + .5) * d, y0 + (j + .5) * d])
    c, n = cen(2, 1), cen(3, 1)
    rect(ax, c[0], c[1] - d / 2, d, d, '#fdf1dc', '#d9922a', 1.6, alpha=.9, zorder=3)
    for i in range(5):
        for j in range(3):
            dot(ax, cen(i, j), MUTED)
    edge(ax, (c + n) / 2, ORANGE)
    text(ax, *((c + n) / 2 + [8, -24]), 'u_e', 10, color=ORANGE)
    edge(ax, (cen(1, 1) + c) / 2, BLUE)
    text(ax, *((cen(1, 1) + c) / 2 + [-34, -34]), t['up_flow'], 8.5, color=BLUE, ha='center')
    arrow(ax, [(x0, y0 - 22), (x0 + 5 * d, y0 - 22)], MUTED, 1.2)
    text(ax, x0 + 5 * d + 8, y0 - 30, t['flow'], 9.5, color=MUTED)
    for s in (-1, 1):   # the two diagonals of the unit squares above/below the CV cross each lateral face
        a, b = c, cen(3, 1 + s)
        line(ax, [a, b], GREEN, 1.0, ls=':', z=5)
        a2, b2 = n, cen(2, 1 + s)
        line(ax, [a2, b2], GREEN, 1.0, ls=':', z=5)
    block(ax, x0, y0 + 3 * d + 16, t['c_axis'], 5 * d + 40, 9.5, color=MUTED)


def diag_cv(ax, t, x0, y0, d):
    """5 x 4 cells; the diagonal edge from c (col 2, row 1) to n (col 3, row 2), flow to the right."""
    for i in range(5):
        for j in range(4):
            rect(ax, x0 + i * d, y0 + j * d, d, d, 'white')
    grid(ax, x0, y0, 5, 4, d)
    pos = lambda p: np.array([x0, y0]) + np.asarray(p, float) * d
    c, n = np.array([2.5, 1.5]), np.array([3.5, 2.5])
    dv = (n - c) / np.linalg.norm(n - c); tv = np.array([-dv[1], dv[0]])   # +t = down-left
    W = 1 / np.sqrt(2)
    poly = np.array([c - tv * W / 2, n - tv * W / 2, n + tv * W / 2, c + tv * W / 2])
    ax.add_patch(Polygon(pos(poly), fc='#fdf1dc', ec='#d9922a', lw=1.6, zorder=3))
    for i in range(5):
        for j in range(4):
            dot(ax, pos([i + .5, j + .5]), MUTED)
    mid = (c + n) / 2
    edge(ax, pos(mid), ORANGE, True)
    text(ax, *(pos(mid) + [14, -12]), 'u_e', 10, color=ORANGE)
    # flow-face upwind edge on line k: one row up
    um = c - (n - c) / 2
    line(ax, [pos(c - (n - c)), pos(c)], BLUE, 1.2, z=5)
    edge(ax, pos(um), BLUE, True)
    text(ax, *(pos(um) + [16, -30]), t['up_flow'], 8.5, color=BLUE)
    # lateral (inflow) face: the two opposite-parity parallel links, same row and one row down
    for a in (np.array([1.5, 1.5]), np.array([2.5, 2.5])):
        b = a + (n - c)
        line(ax, [pos(a), pos(b)], GREEN, 1.2, z=5)
        edge(ax, pos((a + b) / 2), GREEN, True)
    text(ax, *(pos([2.9, 3.0]) + [0, 6]), t['up_lat'], 8.5, color=GREEN, ha='right')
    # row guides (the rows of the link midpoints) across the panel
    xr = x0 + 5 * d + 12
    for r, key in [(1.0, 'row_m1'), (2.0, 'row_0'), (3.0, 'row_p1')]:
        yy = y0 + r * d
        line(ax, [(x0, yy), (xr + 6, yy)], '#b9b6ae', .9, ls='--', z=2)
        text(ax, xr + 10, yy - 8, t[key], 8.5, color=MUTED)
    arrow(ax, [(x0, y0 - 22), (x0 + 5 * d, y0 - 22)], MUTED, 1.2)
    text(ax, x0 + 5 * d + 8, y0 - 30, t['flow'], 9.5, color=MUTED)
    block(ax, x0, y0 + 4 * d + 16, t['c_diag'], 5 * d + 120, 9.5, color=MUTED)


def build_mech(lang):
    t = T[lang]
    fig, ax = canvas(1330)
    text(ax, 48, 26, t['m_a'], 12.5, weight='bold')
    text(ax, 930, 26, t['m_b'], 12.5, weight='bold')
    scalar_panel(ax, t, 160, 110, 130, False)
    scalar_panel(ax, t, 1040, 110, 130, True)
    block(ax, 48, 530, t['a_note'], 800, 9.5, color=MUTED)
    block(ax, 930, 530, t['b_note'], 820, 9.5, color=MUTED)
    text(ax, 48, 650, t['m_c'], 12.5, weight='bold')
    axis_cv(ax, t, 70, 740, 104)
    diag_cv(ax, t, 960, 740, 88)
    return fig


def build_angle(lang):
    t = T[lang]
    fig, base = canvas(900)
    text(base, 48, 26, t['g_a'], 12.5, weight='bold')
    text(base, 960, 26, t['g_b'], 12.5, weight='bold')
    ax = plot_axes(fig, 100, 90, 760, 520)
    phi = np.linspace(0, 45, 181)
    r = np.radians(phi)
    two = 0.5 * (np.cos(r) - np.sin(r)) * np.sin(r) * np.cos(r)
    ax.plot(ANG, ENC1, 'o-', color=ORANGE, lw=1.6, ms=4, label=t['enc1'])
    ax.plot(ANG, NB4, 's--', color=MUTED, lw=1.3, ms=4, label=t['nb4'])
    ax.plot(phi, two, '-', color=GREEN, lw=1.4, label=t['two'])
    ax.plot([0], [MUSCL0], '*', color=ORANGE, ms=10, label=t['muscl'])
    ax.plot(M_ANG, M_S2, 'D', color=BLUE, ms=6, mfc='white', mew=1.4, label=t['s2'])
    ax.plot(M_ANG, M_S3, 'D', color=BLUE, ms=6, label=t['s3'])
    ax.plot(TH_ANG, TH_S2, '_', color=INK, ms=14, mew=1.6, label=t['th'])
    ax.plot(TH_ANG, TH_S3, '_', color=INK, ms=14, mew=1.6)
    ax.set(xlabel=t['g_x'], ylabel=t['g_y'], xlim=(-1.5, 46.5), ylim=(0, 0.38))
    ax.set_xticks([0, 10, 22.5, 30, 45])
    ax.set_xticklabels(['0', '10', '22.5', '30', '45'])
    ax.grid(color=RULE, lw=.6)
    ax.legend(fontsize=8.5, frameon=False, loc='upper center', bbox_to_anchor=(0.5, -0.16), ncol=2)
    ax = plot_axes(fig, 1000, 90, 740, 520)
    y = np.array(PY, float)
    ax.plot(y, np.exp(-y**2 / 200.0), '-', color=MUTED, lw=1.3, label=t['p0'])
    ax.plot(PY, P_S2, '--', color=BLUE, lw=1.4, label=t['p2'])
    ax.plot(PY, P_S3, '-', color=ORANGE, lw=1.6, label=t['p3'])
    ax.set(xlabel=t['p_y'], ylabel=t['p_u'], xlim=(-35, 35), ylim=(0, 1.05))
    ax.grid(color=RULE, lw=.6)
    ax.legend(fontsize=9, frameon=False, loc='upper left')
    return fig


def draw(lang):
    with drawing_style():
        export(build_mech(lang), 'diagdiff_mech', lang)
        return export(build_angle(lang), 'diagdiff_angle', lang)
