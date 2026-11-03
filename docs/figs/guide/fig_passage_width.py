"""Passage-width page: how a cell side is shared among the eight edges, why a
diagonal one-cell valley stays connected on the ENC grid, the reassignment in a
one-cell channel, and how values 2 and 3 of f_opening_dynamic measure blockage.
Regenerate only this page with make_guide_figs.py passage_width.
"""
from _terms import *

G = {'ja': {'a': '(a) 辺の分け方(正方セル)',
            'a_axis': '法線エッジ: 辺の中央 (1 − p_d)Δ',
            'a_diag': '斜めエッジ: 角を挟む 2 辺の端\n(p_d/2)Δ ずつ。通過幅は、斜めに\n直交する向きへの投影 (p_d/2)√2Δ',
            'a_note': '既定 p_d = 0.586 で 8 本とも 0.414Δ。\n自然幅は軸 Δ、斜め 0.707Δ。\np_d = 0 は斜めに貸さない 4 近傍格子。',
            'b': '(b) 斜めに走る 1 セル幅の谷',
            'b_4nb': '4 近傍格子',
            'b_enc': 'ENC 格子',
            'b_4nb_t': '角の 1 点でしか接しないので、\n流れがとぎれる。つなぐには 4 連結の\n階段に描き直すか、格子を細かくする',
            'b_enc_t': '斜めエッジがつなぐ。振り替えで\n斜めの自然幅 0.707Δ まで流す',
            'c': '(c) 両岸が高い 1 セル幅の河道',
            'c_off': '振り替えなし',
            'c_on': '振り替えあり',
            'c_off_t': '斜めの隣は高い河岸で、斜めエッジは\n流れない。使えるのは辺の中央 0.414Δ だけ。\nエッジ流速はセル流速の 2.4 倍、\n等流水深は Manning の値より 30 % 深い',
            'c_on_t': '塞がれた端の分を軸エッジへ返す。\n通過幅は辺の全体 Δ(自然幅)で、\n等流は Manning に一致する',
            'bank': '河岸',
            'chan': '河道',
            'd': '(d) 塞がりの測り方(f_opening_dynamic の 2 と 3)',
            'd_slope': '一様な斜面(流れの向きの断面)',
            'd_bank': '両岸が高い 1 セル河道(横断面)',
            'd_slope_t': '2: z_d − z_c = SΔ を塞がりと数え、\ns = SΔ/h(何も塞いでいないのに\n斜めの配分を軸へ返す)\n3: z_d − z_o = 0 なので s = 0',
            'd_bank_t': '2・3 とも塞ぎの高さは H。\n水面が岸より低ければ s = 1、\n越えれば越えた分を斜めが運ぶ',
            'd_beside': 'd: o の真横のセル(o と同じ高さ)',
            'd_formula': '3: dz = min(z_d − z_c, z_d − z_o, κ)、s = clamp(dz / h, 0, 1)',
            'd_kappa': 'κ: 面の横断方向の 2 階差分(平面の上で 0)'},
     'en': {'a': '(a) How a side is shared (square cell)',
            'a_axis': 'axis edge: middle of the side,\n(1 − p_d)Δ',
            'a_diag': 'diagonal edge: the ends of the two\nsides at the corner, (p_d/2)Δ each;\nwidth = projection normal to the\ndiagonal, (p_d/2)√2Δ',
            'a_note': 'Default p_d = 0.586: all eight widths\nare 0.414Δ. Natural width: Δ along an\naxis, 0.707Δ along a diagonal. p_d = 0\nlends nothing to the diagonals\n(4-neighbour grid).',
            'b': '(b) A one-cell-wide valley running diagonally',
            'b_4nb': '4-neighbour grid',
            'b_enc': 'ENC grid',
            'b_4nb_t': 'the cells touch only at a corner, so\nthe flow is cut; joining them needs a\n4-connected staircase or a finer grid',
            'b_enc_t': 'the diagonal edges connect them;\nreassignment lets them carry up to\nthe diagonal natural width 0.707Δ',
            'c': '(c) A one-cell-wide channel between high banks',
            'c_off': 'no reassignment',
            'c_on': 'with reassignment',
            'c_off_t': 'the diagonal neighbours are high banks, so\nthe diagonal edges carry nothing. Only the\nmiddle 0.414Δ of the side is used: the edge\nvelocity is 2.4 times the cell velocity and\nthe uniform-flow depth is 30 % above Manning',
            'c_on_t': 'the blocked end shares go back to the axis\nedge. The passage width is the whole side Δ\n(natural width) and the uniform flow\nmatches Manning',
            'bank': 'bank',
            'chan': 'channel',
            'd': '(d) Measuring blockage (values 2 and 3 of f_opening_dynamic)',
            'd_slope': 'uniform slope (section along the flow)',
            'd_bank': 'one-cell channel between high banks (cross-section)',
            'd_slope_t': '2: counts z_d − z_c = SΔ as blockage,\ns = SΔ/h (moves the diagonal share to\nthe axis although nothing blocks)\n3: z_d − z_o = 0, so s = 0',
            'd_bank_t': 'both 2 and 3 take the blocking height\nH. With the water surface below the\nbank, s = 1; above it, the diagonal\nedges carry the excess',
            'd_beside': 'd: beside o (same height as o)',
            'd_formula': '3: dz = min(z_d − z_c, z_d − z_o, κ), s = clamp(dz / h, 0, 1)',
            'd_kappa': 'κ: second difference across the face (0 on a plane)'}}

PD = 2 / (2 + 2 ** .5)
INKC = '#282c30'
LABEL_BOX = dict(fc='white', ec='none', pad=1.2, alpha=.9)


def cell(ax, x, y, d, fill, edge='#9c9a94', lw=.8):
    rect(ax, x, y, d, d, fill, edge, lw)


def cross(ax, p, r=7, color=INKC, lw=1.6):
    line(ax, [(p[0] - r, p[1] - r), (p[0] + r, p[1] + r)], color, lw, z=12)
    line(ax, [(p[0] - r, p[1] + r), (p[0] + r, p[1] - r)], color, lw, z=12)


def side_shares(ax, x, y0, d, blocked=False, whole=False):
    """The three shares of the vertical side at x (y0 .. y0 + d)."""
    ld = PD / 2 * d
    if whole:
        line(ax, [(x, y0), (x, y0 + d)], BLUE, 5.0, z=11)
        return
    line(ax, [(x, y0 + ld), (x, y0 + d - ld)], BLUE, 5.0, z=11)
    for a, b in [(y0, y0 + ld), (y0 + d - ld, y0 + d)]:
        line(ax, [(x, a), (x, b)], ORANGE, 5.0, z=11)
        if blocked:
            cross(ax, (x, (a + b) / 2), 6)


def panel_a(ax, t):
    text(ax, 48, 30, t['a'], 13, weight='bold')
    d = 128; x0, y0 = 70, 82
    for i in range(3):
        for j in range(3):
            cell(ax, x0 + i * d, y0 + j * d, d, '#eaf2fc' if (i, j) == (1, 1) else 'white')
    cx, cy = x0 + 1.5 * d, y0 + 1.5 * d
    ld = PD / 2 * d
    xl, xr, yt, yb = x0 + d, x0 + 2 * d, y0 + d, y0 + 2 * d
    for (p, q) in [((xl, yt + ld), (xl, yb - ld)), ((xr, yt + ld), (xr, yb - ld)),
                   ((xl + ld, yt), (xr - ld, yt)), ((xl + ld, yb), (xr - ld, yb))]:
        line(ax, [p, q], BLUE, 5.0, z=11)
    for (xc, yc, sx, sy) in [(xl, yt, 1, 1), (xr, yt, -1, 1), (xl, yb, 1, -1), (xr, yb, -1, -1)]:
        line(ax, [(xc, yc + sy * ld), (xc, yc), (xc + sx * ld, yc)], ORANGE, 5.0, z=11)
    for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
        arrow(ax, [(cx, cy), (cx + .86 * d * dx, cy + .86 * d * dy)], BLUE, 1.4, size=9)
    for dx, dy in [(1, 1), (-1, 1), (1, -1), (-1, -1)]:
        arrow(ax, [(cx, cy), (cx + .86 * d * dx, cy + .86 * d * dy)], ORANGE, 1.3, ls='--', size=9)
    dot(ax, (cx, cy), INKC)
    legend_rows(ax, 485, 92, [(BLUE, '-', t['a_axis']), (ORANGE, '--', t['a_diag'])], 415, 62, 9.5)
    block(ax, 485, 318, t['a_note'], 415, 9.5, color=MUTED)


def valley(ax, x0, y0, d, enc):
    n = 5
    for i in range(n):
        for j in range(n):
            cell(ax, x0 + i * d, y0 + j * d, d, WATER if j == n - 1 - i else SOIL)
    centres = [(x0 + (i + .5) * d, y0 + (n - 1 - i + .5) * d) for i in range(n)]
    for a, b in zip(centres[:-1], centres[1:]):
        if enc:
            arrow(ax, [(a[0] + .12 * d, a[1] - .12 * d), (b[0] - .12 * d, b[1] + .12 * d)], ORANGE, 1.6, ls='--', size=9)
        else:
            cross(ax, ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), 8)
    for p in centres:
        dot(ax, p, INKC)


def panel_b(ax, t):
    text(ax, 940, 30, t['b'], 13, weight='bold')
    d = 50
    for x0, enc in [(975, False), (1385, True)]:
        text(ax, x0 + 2.5 * d, 76, t['b_enc'] if enc else t['b_4nb'], 11, ha='center', weight='bold')
        valley(ax, x0, 106, d, enc)
        block(ax, x0 - 15, 380, t['b_enc_t'] if enc else t['b_4nb_t'], 370, 9.5)


def strip(ax, x0, y0, d, on, t):
    for i in range(4):
        for j in range(3):
            cell(ax, x0 + i * d, y0 + j * d, d, WATER if j == 1 else SOIL)
    for j, key, col in [(0, 'bank', MUTED), (1, 'chan', BLUE), (2, 'bank', MUTED)]:
        text(ax, x0 - 8, y0 + (j + .5) * d, t[key], 9, color=col, ha='right', va='center')
    c = (x0 + 1.5 * d, y0 + 1.5 * d)
    if not on:
        for dy in (-1, 1):
            line(ax, [c, (c[0] + d, c[1] + dy * d)], ORANGE, 1.2, ls='--', z=9, alpha=.75)
    side_shares(ax, x0 + 2 * d, y0 + d, d, blocked=not on, whole=on)
    arrow(ax, [(x0 + .25 * d, y0 + 1.5 * d), (x0 + 3.75 * d, y0 + 1.5 * d)], BLUE, 1.5, size=10, z=8)


def panel_c(ax, t):
    text(ax, 48, 515, t['c'], 13, weight='bold')
    d = 68
    for k, (on, key, keyt) in enumerate([(False, 'c_off', 'c_off_t'), (True, 'c_on', 'c_on_t')]):
        y0 = 600 + k * 280
        text(ax, 125, y0 - 32, t[key], 11, weight='bold', color=GREEN if on else INKC)
        strip(ax, 125, y0, d, on, t)
        block(ax, 440, y0 + 4, t[keyt], 455, 9.5)


def panel_d(ax, t):
    text(ax, 940, 515, t['d'], 13, weight='bold')
    # uniform slope, section along the flow: o (upstream) - c - n
    text(ax, 975, 562, t['d_slope'], 10.5, weight='bold')
    gy = lambda x: 652 + (x - 975) * 80 / 365
    ax.add_patch(Polygon([(975, gy(975)), (1340, gy(1340)), (1340, 775), (975, 775)], closed=True, fc=SOIL, ec='none', zorder=1))
    ax.add_patch(Polygon([(975, gy(975) - 14), (1340, gy(1340) - 14), (1340, gy(1340)), (975, gy(975))], closed=True, fc=WATER, ec='none', zorder=2))
    line(ax, [(975, gy(975)), (1340, gy(1340))], BED, 1.4)
    line(ax, [(975, gy(975) - 14), (1340, gy(1340) - 14)], BLUE, 1.2)
    for xc, lab in [(1040, 'o'), (1160, 'c'), (1280, 'n')]:
        dot(ax, (xc, gy(xc)), INKC); text(ax, xc, gy(xc) + 9, lab, 10, ha='center')
    zo, zc = gy(1040), gy(1160)
    line(ax, [(1040, zo), (1175, zo)], ORANGE, 1.1, ls=':')
    line(ax, [(1160, zo), (1160, zc)], INKC, 1.1)
    text(ax, 1166, (zo + zc) / 2 - 9, 'SΔ', 9.5, bbox=LABEL_BOX)
    line(ax, [(1040, zo - 3), (1060, 604)], ORANGE, .9)
    text(ax, 1062, 594, t['d_beside'], 8.8, color=ORANGE, bbox=LABEL_BOX)
    block(ax, 1385, 585, t['d_slope_t'], 390, 9.3)
    # one-cell channel between high banks, cross-section
    text(ax, 975, 805, t['d_bank'], 10.5, weight='bold')
    bx = [(975, 870), (1100, 870), (1100, 930), (1220, 930), (1220, 870), (1340, 870)]
    ax.add_patch(Polygon(bx + [(1340, 965), (975, 965)], closed=True, fc=SOIL, ec='none', zorder=1))
    rect(ax, 1100, 895, 120, 35, WATER, 'none')
    line(ax, bx, BED, 1.4)
    line(ax, [(1100, 895), (1220, 895)], BLUE, 1.2)
    text(ax, 1037, 850, 'd', 10.5, color=ORANGE, ha='center'); text(ax, 1280, 850, 'd', 10.5, color=ORANGE, ha='center')
    text(ax, 1160, 936, 'c', 10, ha='center')
    line(ax, [(1232, 870), (1232, 930)], INKC, 1.0); text(ax, 1238, 890, 'H', 9.5)
    line(ax, [(1113, 895), (1113, 930)], BLUE, 1.0); text(ax, 1119, 902, 'h', 9.5, color=BLUE)
    block(ax, 1385, 840, t['d_bank_t'], 390, 9.3)
    text(ax, 975, 1005, t['d_formula'], 10.5, weight='bold')
    text(ax, 975, 1040, t['d_kappa'], 9.5, color=MUTED)


def build(lang):
    t = G[lang]; fig, ax = canvas(1110)
    panel_a(ax, t); panel_b(ax, t); panel_c(ax, t); panel_d(ax, t)
    line(ax, [(905, 22), (905, 1090)], RULE, 1.0)
    line(ax, [(30, 492), (1770, 492)], RULE, 1.0)
    return fig


def draw(lang):
    with drawing_style(): return export(build(lang), 'passage_width', lang)
