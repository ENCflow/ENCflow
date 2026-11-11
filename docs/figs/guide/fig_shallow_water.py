"""shallow_water_*: teaching diagrams for docs/users_guide/shallow_water.md (ja/en).

Three schematics, no solver output: (1) the symbols of a shallow flow and the forces on a
column of water, (2) the five terms of the momentum equation and which of them the dynamic,
local-inertia, diffusion and kinematic wave models keep, (3) the relative size of the terms
in four typical situations.  The numbers of (3) are order-of-magnitude estimates made for
this page (function `situations`; the assumptions are the table of section 4 of the page).

Regenerate only this page with make_guide_figs.py shallow_water.
`python3 fig_shallow_water.py` prints the table of the estimates.
"""
import math
from matplotlib.patches import Polygon, Circle, FancyBboxPatch, FancyArrowPatch
from _terms import canvas, plot_axes, export, text, line, arrow, INK, MUTED, RULE, BLUE, ORANGE, GREEN, WATER, SOIL, BED

W = 1500
GRID, WHITE = '#c7d0d7', '#ffffff'
# term colours (fill, edge): inertia, pressure, gravity, friction
C_IN, C_PR, C_GR, C_FR = ('#fbe3cf', ORANGE), (WATER, BLUE), ('#dcebd0', GREEN), (SOIL, BED)
G = 9.8

T = {
    'ja': {
        'k_title': '浅水流の見取り図と、水の柱に働く力',
        'k_sub': '川を横から見た断面。縦方向を大きく拡大して描いています(実際は水平の広がりが水深よりずっと大きい)。',
        'k_a': '(a) 記号', 'k_b': '(b) 水の柱に働く力(流れの向きの成分)',
        'k_z': 'z 地盤高', 'k_h': 'h 水深', 'k_eta': 'η = z + h 水位', 'k_u': 'u 流速(水深方向の平均)',
        'k_datum': '基準面', 'k_x': 'x(流れに沿う距離)', 'k_bed': '地盤', 'k_surf': '水面',
        'k_press': '圧力の差: 深い側が浅い側を押す', 'k_grav': '重力: 斜面を下る向きの成分', 'k_fric': '摩擦: 底面が流れを引き止める',
        'k_sum': '差し引きが、水を加速(または減速)させる = 慣性',
        'k_deep': '深い', 'k_shallow': '浅い',
        'k_foot': '圧力は水面からの深さに比例する(静水圧)と仮定し、流速は水深方向の平均で代表させます。',
        't_title': '運動方程式の 5 つの項と、近似ごとに残す項',
        't_sub': '流れに沿う 1 次元の形。左辺が水の加速(慣性)、右辺が水に働く力(単位質量あたり)。',
        't_names': [('局所項', '(局所加速度項)', 'その場所の流速が\n時間とともに変わる'),
                    ('移流項', '(対流項)', '流速の違う場所へ\n水が移動する'),
                    ('圧力項', '(水深勾配項)', '深い側が\n浅い側を押す'),
                    ('重力項', '(底面勾配項)', '斜面を下る向きの\n重力の成分'),
                    ('摩擦項', '(底面摩擦項・抵抗項)', '底面が流れを\n引き止める')],
        't_inertia': '慣性項(加速度項)', 't_surface': r'水面勾配項(2 つの和は $-g\,\partial\eta/\partial x$、$\eta = z + h$)',
        't_keep': '残す項',
        't_models': [('力学波', 'すべての項を残す'), ('局所慣性', '移流項だけを省く'),
                     ('拡散波', '慣性項を省く'), ('運動波', '水深勾配も省く')],
        't_foot': '●: 残す項　○: 省く項。連続式(水量の保存)は、どの近似でも同じです。',
        'm_title': '現象によって、効く項が違う',
        'm_sub': '各項の大きさを、その場面で最大の項を 1 として比べた試算(横軸は対数目盛)。',
        'm_terms': ['局所項', '移流項', '圧力項(水深勾配)', '重力項(底面勾配)', '摩擦項'],
        'm_cases': [('急な斜面の薄い流れ', '重力 ≈ 摩擦\n→ 運動波'), ('緩い勾配の川の洪水', '+ 水深勾配\n→ 拡散波'),
                    ('ダム破壊の直後', '慣性 ≈ 圧力\n→ 力学波'), ('外洋の津波', '局所項 ≈ 圧力\n→ 線形長波')],
        'm_small': '0.0001 未満', 'm_zero': '0(平坦と仮定)',
        'm_x': '最大の項を 1 としたときの大きさ',
        'm_foot': '前提は本文 4 節の表。桁の目安であり、値は条件によって変わります。',
    },
    'en': {
        'k_title': 'Sketch of a shallow flow and the forces on a column of water',
        'k_sub': 'A river seen from the side. The vertical scale is greatly exaggerated (the horizontal extent is far larger than the depth).',
        'k_a': '(a) Symbols', 'k_b': '(b) Forces on a water column (along the flow)',
        'k_z': 'z  bed elevation', 'k_h': 'h  depth', 'k_eta': 'η = z + h  water level', 'k_u': 'u  velocity (depth-averaged)',
        'k_datum': 'datum', 'k_x': 'x (distance along the flow)', 'k_bed': 'bed', 'k_surf': 'water surface',
        'k_press': 'pressure: the deeper side pushes the shallower', 'k_grav': 'gravity: component down the slope', 'k_fric': 'friction: the bed holds the flow back',
        'k_sum': 'The net force accelerates the water = inertia',
        'k_deep': 'deep', 'k_shallow': 'shallow',
        'k_foot': 'Pressure is assumed proportional to the depth below the surface (hydrostatic), and the velocity is represented by its depth average.',
        't_title': 'The five terms of the momentum equation and which ones each approximation keeps',
        't_sub': 'One-dimensional form along the flow. Left: acceleration of the water (inertia). Right: forces on the water (per unit mass).',
        't_names': [('local term', '(local acceleration)', 'velocity at a point\nchanges with time'),
                    ('advection term', '(convective term)', 'water moves to where\nthe velocity differs'),
                    ('pressure term', '(depth-gradient term)', 'the deeper side\npushes the shallower'),
                    ('gravity term', '(bed-slope term)', 'component of gravity\ndown the slope'),
                    ('friction term', '(bed friction, resistance)', 'the bed holds\nthe flow back')],
        't_inertia': 'inertia terms (acceleration)', 't_surface': r'water-surface gradient (the sum is $-g\,\partial\eta/\partial x$, $\eta = z + h$)',
        't_keep': 'terms kept',
        't_models': [('dynamic wave', 'keeps all terms'), ('local inertia', 'drops advection only'),
                     ('diffusion wave', 'drops the inertia terms'), ('kinematic wave', 'also drops the depth gradient')],
        't_foot': '●: kept　○: dropped. The continuity equation (conservation of water) is the same in every approximation.',
        'm_title': 'Different terms matter in different phenomena',
        'm_sub': 'Estimated size of each term relative to the largest term of that situation (logarithmic axis).',
        'm_terms': ['local term', 'advection term', 'pressure (depth gradient)', 'gravity (bed slope)', 'friction term'],
        'm_cases': [('thin flow on\na steep hillslope', 'gravity ≈ friction\n→ kinematic wave'), ('flood in a gently\nsloping river', '+ depth gradient\n→ diffusion wave'),
                    ('just after\na dam break', 'inertia ≈ pressure\n→ dynamic wave'), ('tsunami in\nthe open ocean', 'local term ≈ pressure\n→ linear long wave')],
        'm_small': 'below 0.0001', 'm_zero': '0 (flat bed assumed)',
        'm_x': 'size relative to the largest term',
        'm_foot': 'Assumptions: the table in section 4 of the page. Orders of magnitude only; the values change with the conditions.',
    },
}


def title(ax, t, sub=None):
    text(ax, 48, 36, t, 14, weight='bold')
    if sub:
        text(ax, 48, 82, sub, 10, color=MUTED)


def darrow(ax, p, q, color, lw=1.2, size=10):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle='<->', mutation_scale=size, color=color, lw=lw,
                                 shrinkA=0, shrinkB=0, zorder=8))


# ---------------------------------------------------------------- estimates of section 4
def situations():
    """Order-of-magnitude size of each term divided by g (a slope), for four situations.

    Returns [(key, {local, adv, dh, bed, fr})].  local = dU/(g T), adv = U dU/(g L), dh = dh/L,
    bed = S0, fr = n^2 U^2 / h^(4/3).  For the sinusoidal tsunami: omega U/g, k U^2/g, k a.
    """
    fric = lambda n, U, h: n * n * U * U / h ** (4 / 3)
    out = []
    # A: sheet flow on a steep hillslope (the slope of examples/benchmark/v-shaped at equilibrium)
    S0, n, rain, B = 0.05, 0.015, 10.8e-3 / 3600, 800.0
    al = math.sqrt(S0) / n
    q = rain * B
    h = (q / al) ** 0.6
    U = q / h
    te = (B / (al * rain ** (2 / 3))) ** 0.6
    out.append(('A', dict(local=U / (G * te), adv=U * U / (G * B), dh=h / B, bed=S0, fr=fric(n, U, h))))
    # B: flood in a gently sloping river (depth 3 -> 6 m in 12 h, Manning uniform flow)
    S0, n, Tr = 1 / 5000, 0.03, 12 * 3600.0
    u = lambda d: d ** (2 / 3) * math.sqrt(S0) / n
    U1, U2, Um = u(3.0), u(6.0), u(4.5)
    L = 5 / 3 * Um * Tr
    out.append(('B', dict(local=(U2 - U1) / (G * Tr), adv=Um * (U2 - U1) / (G * L), dh=3.0 / L, bed=S0, fr=fric(n, Um, 4.5))))
    # C: just after a dam break (depth 10 -> 4 m and velocity 0 -> 7 m/s over 300 m, within 30 s)
    L, Tr, dU, dh, Um, hm, n = 300.0, 30.0, 7.0, 6.0, 3.5, 7.0, 0.03
    out.append(('C', dict(local=dU / (G * Tr), adv=Um * dU / (G * L), dh=dh / L, bed=0.0, fr=fric(n, Um, hm))))
    # D: tsunami in the open ocean (depth 4000 m, amplitude 1 m, period 20 min)
    H, a, Tw, n = 4000.0, 1.0, 1200.0, 0.025
    c = math.sqrt(G * H)
    k, om, U = 2 * math.pi / (c * Tw), 2 * math.pi / Tw, a * c / H
    out.append(('D', dict(local=om * U / G, adv=k * U * U / G, dh=k * a, bed=0.0, fr=fric(n, U, H))))
    return out


# ---------------------------------------------------------------- 1. sketch and forces
def build_sketch(lang):
    t = T[lang]
    fig, ax = canvas(830, W)
    title(ax, t['k_title'], t['k_sub'])
    # (a) symbols
    text(ax, 48, 135, t['k_a'], 12, weight='bold')
    xa, xb, yd = 70, 800, 690
    bed = lambda x: 505 + (x - xa) * 0.16
    srf = lambda x: 300 + (x - xa) * 0.25
    ax.add_patch(Polygon([(xa, bed(xa)), (xb, bed(xb)), (xb, yd), (xa, yd)], closed=True, fc=SOIL, ec='none', zorder=1))
    ax.add_patch(Polygon([(xa, srf(xa)), (xb, srf(xb)), (xb, bed(xb)), (xa, bed(xa))], closed=True, fc=WATER, ec='none', zorder=2))
    line(ax, [(xa, bed(xa)), (xb, bed(xb))], BED, 1.8, z=4)
    line(ax, [(xa, srf(xa)), (xb, srf(xb))], BLUE, 1.6, z=4)
    line(ax, [(xa, yd), (xb, yd)], MUTED, 1.0, ls=(0, (5, 4)))
    text(ax, xb + 10, yd - 8, t['k_datum'], 9.5, color=MUTED)
    text(ax, xa + 14, srf(xa) - 28, t['k_surf'], 9.5, color=BLUE)
    text(ax, xb - 12, bed(xb) + 10, t['k_bed'], 9.5, color=BED, ha='right')
    x1 = 190
    darrow(ax, (x1, yd), (x1, bed(x1)), BED)
    text(ax, x1 + 10, (yd + bed(x1)) / 2 - 9, t['k_z'], 10.5, color=BED)
    x2 = 330
    darrow(ax, (x2, bed(x2)), (x2, srf(x2)), BLUE)
    text(ax, x2 + 10, (bed(x2) + srf(x2)) / 2 - 9, t['k_h'], 10.5, color=BLUE)
    x3 = 470
    darrow(ax, (x3, yd), (x3, srf(x3)), INK)
    text(ax, x3 + 10, srf(x3) - 58, t['k_eta'], 10.5)
    line(ax, [(x3 + 6, srf(x3) - 30), (x3 + 2, srf(x3) - 6)], INK, 0.8)
    x4 = 640
    line(ax, [(x4, bed(x4)), (x4, srf(x4))], ORANGE, 1.0, ls=(0, (3, 3)))
    for f in (0.2, 0.5, 0.8):
        yy = srf(x4) + f * (bed(x4) - srf(x4))
        arrow(ax, [(x4, yy), (x4 + 95, yy + 95 * 0.2)], ORANGE, 1.8, size=11)
    text(ax, 866, srf(x4) - 46, t['k_u'], 10.5, color=ORANGE, ha='right')
    arrow(ax, [(xa, yd + 34), (xa + 260, yd + 34)], MUTED, 1.2, size=10)
    text(ax, xa + 272, yd + 25, t['k_x'], 9.5, color=MUTED)
    # (b) forces on a column: the three labels sit outside the water, joined to their arrows by thin leaders
    xo = 890
    text(ax, xo, 135, t['k_b'], 12, weight='bold')
    xc, xe, ys = xo + 20, 1450, 610
    bed2 = lambda x: 478 + (x - xc) * 0.16
    srf2 = lambda x: 296 + (x - xc) * 0.30
    ax.add_patch(Polygon([(xc, bed2(xc)), (xe, bed2(xe)), (xe, ys), (xc, ys)], closed=True, fc=SOIL, ec='none', zorder=1))
    ax.add_patch(Polygon([(xc, srf2(xc)), (xe, srf2(xe)), (xe, bed2(xe)), (xc, bed2(xc))], closed=True, fc='#e7eff9', ec='none', zorder=2))
    line(ax, [(xc, bed2(xc)), (xe, bed2(xe))], BED, 1.8, z=4)
    line(ax, [(xc, srf2(xc)), (xe, srf2(xe))], BLUE, 1.2, z=4)
    c1, c2 = 1130, 1270                                   # the column
    cm = (c1 + c2) / 2
    ax.add_patch(Polygon([(c1, srf2(c1)), (c2, srf2(c2)), (c2, bed2(c2)), (c1, bed2(c1))], closed=True,
                         fc=WATER, ec=BLUE, lw=1.6, zorder=3))
    text(ax, c1 - 8, srf2(c1) - 34, t['k_deep'], 9.5, color=BLUE, ha='right')
    text(ax, c2 + 10, srf2(c2) - 34, t['k_shallow'], 9.5, color=BLUE)
    # pressure: a long arrow pushing from the deep side and a short one from the shallow side
    ym = (srf2(c1) + bed2(c1)) / 2 + 8
    arrow(ax, [(c1 - 112, ym), (c1 - 6, ym)], BLUE, 3.2, size=16)
    arrow(ax, [(c2 + 64, ym + 22), (c2 + 6, ym + 22)], BLUE, 3.2, size=16)
    text(ax, xc, 196, t['k_press'], 10, color=BLUE)
    line(ax, [(xc + 70, 226), (c1 - 60, ym - 12)], BLUE, 0.8)
    # gravity: along the bed, from the middle of the column
    gy = (srf2(cm) + bed2(cm)) / 2 - 4
    arrow(ax, [(cm - 46, gy - 46 * 0.16), (cm + 50, gy + 50 * 0.16)], GREEN, 3.2, size=16)
    text(ax, xe, 246, t['k_grav'], 10, color=GREEN, ha='right')
    line(ax, [(1300, 276), (cm + 10, gy - 14)], GREEN, 0.8)
    # friction: at the bed, against the flow
    fy = bed2(cm) + 15
    arrow(ax, [(c2 - 8, fy + 11), (c1 + 14, fy - 11)], BED, 3.2, size=16)
    text(ax, xc, ys + 22, t['k_fric'], 10, color=BED)
    line(ax, [(xc + 60, ys + 20), (c1 + 40, fy + 14)], BED, 0.8)
    ax.add_patch(FancyBboxPatch((xo + 6, 690), 556, 58, boxstyle='round,pad=0,rounding_size=8', fc=WHITE, ec=GRID, lw=1.2, zorder=3))
    text(ax, xo + 284, 719, t['k_sum'], 10.5, ha='center', va='center')
    text(ax, 48, 792, t['k_foot'], 9, color=MUTED)
    return fig


# ---------------------------------------------------------------- 2. terms and models
EQ = [r'$\frac{\partial u}{\partial t}$', r'$u\,\frac{\partial u}{\partial x}$', r'$-\,g\,\frac{\partial h}{\partial x}$',
      r'$-\,g\,\frac{\partial z}{\partial x}$', r'$-\,g\,\frac{n^{2}\,u\,|u|}{h^{4/3}}$']
COLS = [C_IN, C_IN, C_PR, C_GR, C_FR]
KEEP = [(1, 1, 1, 1, 1), (1, 0, 1, 1, 1), (0, 0, 1, 1, 1), (0, 0, 0, 1, 1)]


def build_terms(lang):
    t = T[lang]
    fig, ax = canvas(1010, W)
    title(ax, t['t_title'], t['t_sub'])
    xs = [400, 615, 850, 1065, 1310]                       # column centres
    ws = [170, 170, 190, 190, 230]
    y0, bh = 135, 120
    for x, w, eq, (fill, edge) in zip(xs, ws, EQ, COLS):
        ax.add_patch(FancyBboxPatch((x - w / 2, y0), w, bh, boxstyle='round,pad=0,rounding_size=10',
                                    fc=fill, ec=edge, lw=1.8, zorder=3))
        text(ax, x, y0 + bh / 2, eq, 21, ha='center', va='center')
    text(ax, (xs[0] + ws[0] / 2 + xs[1] - ws[1] / 2) / 2, y0 + bh / 2, '+', 20, ha='center', va='center')
    text(ax, (xs[1] + ws[1] / 2 + xs[2] - ws[2] / 2) / 2, y0 + bh / 2, '=', 20, ha='center', va='center')
    for x, (name, alias, mean), (fill, edge) in zip(xs, t['t_names'], COLS):
        text(ax, x, y0 + bh + 20, name, 12.5, color=edge, ha='center', weight='bold')
        text(ax, x, y0 + bh + 54, alias, 8.5, color=MUTED, ha='center')
        text(ax, x, y0 + bh + 86, mean, 9.5, ha='center')
    # braces: inertia (columns 1-2) and water-surface gradient (columns 3-4)
    yb = y0 + bh + 160
    for a, b, lab, col, ha in ((0, 1, t['t_inertia'], ORANGE, 'center'), (2, 3, t['t_surface'], BLUE, 'center')):
        xl, xr = xs[a] - ws[a] / 2, xs[b] + ws[b] / 2
        line(ax, [(xl, yb - 10), (xl, yb), (xr, yb), (xr, yb - 10)], col, 1.4)
        xm = (xl + xr) / 2 + (95 if a == 2 else 0)
        text(ax, xm, yb + 10, lab, 9.5, color=col, ha=ha)
    # matrix of the wave models
    ym = yb + 78
    line(ax, [(48, ym), (W - 48, ym)], RULE, 1.0)
    text(ax, 48, ym + 14, t['t_keep'], 10, color=MUTED)
    rh = 106
    for r, ((name, note), keep) in enumerate(zip(t['t_models'], KEEP)):
        yy = ym + 58 + r * rh
        text(ax, 48, yy, name, 13, weight='bold')
        text(ax, 48, yy + 40, note, 9, color=MUTED)
        for x, k, (fill, edge) in zip(xs, keep, COLS):
            if k:
                ax.add_patch(Circle((x, yy + 26), 15, fc=edge, ec=edge, lw=1.5, zorder=6))
            else:
                ax.add_patch(Circle((x, yy + 26), 15, fc=WHITE, ec=GRID, lw=1.8, zorder=6))
        line(ax, [(48, yy + rh - 22), (W - 48, yy + rh - 22)], RULE, 0.8)
    text(ax, 48, ym + 58 + 4 * rh + 2, t['t_foot'], 9, color=MUTED)
    return fig


# ---------------------------------------------------------------- 3. size of the terms
def build_magnitude(lang):
    t = T[lang]
    fig, ax = canvas(820, W)
    title(ax, t['m_title'], t['m_sub'])
    keys = ['local', 'adv', 'dh', 'bed', 'fr']
    cols = [ORANGE, ORANGE, BLUE, GREEN, BED]
    x0, pw, gap, y0, ph = 330, 248, 40, 272, 400
    lo = 1e-4
    for c, ((key, val), (name, bal)) in enumerate(zip(situations(), t['m_cases'])):
        px = x0 + c * (pw + gap)
        text(ax, px, 186, name, 11, weight='bold', va='bottom')
        text(ax, px, 198, bal, 9, color=MUTED)
        pa = plot_axes(fig, px, y0, pw, ph)
        m = max(val.values())
        for r, (k, col) in enumerate(zip(keys, cols)):
            v = val[k] / m
            if v >= lo:
                pa.barh(r, v - lo, left=lo, height=0.62, color=col, zorder=3)
                lab = '1' if v > 0.995 else f'{v:.2g}'
                if v > 0.2:
                    pa.text(v * 0.82, r, lab, ha='right', va='center', fontsize=9, color='white', zorder=4)
                else:
                    pa.text(v * 1.25, r, lab, ha='left', va='center', fontsize=9, color=INK, zorder=4)
            else:
                pa.text(lo * 1.25, r, t['m_zero'] if val[k] == 0 else t['m_small'], ha='left', va='center',
                        fontsize=8.5, color=MUTED, zorder=4)
        pa.set_xscale('log')
        pa.set_xlim(lo, 1.6)
        pa.set_ylim(4.6, -0.6)
        pa.set_xticks([1e-4, 1e-3, 1e-2, 1e-1, 1])
        pa.set_xticklabels(['0.0001', '', '0.01', '', '1'], fontsize=8)
        pa.minorticks_off()
        pa.set_yticks([])
        pa.spines['left'].set_color(GRID)
        pa.spines['bottom'].set_color(GRID)
        pa.tick_params(axis='x', color=GRID, labelcolor=MUTED)
        pa.grid(axis='x', color=RULE, lw=0.8, zorder=0)
        pa.set_axisbelow(True)
    for r, (lab, col) in enumerate(zip(t['m_terms'], cols)):
        yy = y0 + (r + 0.6) / 5.2 * ph
        text(ax, x0 - 22, yy, lab, 10, color=col, ha='right', va='center')
    text(ax, x0, y0 + ph + 40, t['m_x'], 9.5, color=MUTED)
    text(ax, 48, 782, t['m_foot'], 9, color=MUTED)
    return fig


FIGS = [('shallow_water_sketch', build_sketch), ('shallow_water_terms', build_terms),
        ('shallow_water_magnitude', build_magnitude)]


def draw(lang):
    from _schematic import drawing_style
    if lang not in T:
        raise ValueError('lang must be ja or en')
    with drawing_style():
        for stem, build in FIGS:
            last = export(build(lang), stem, lang)
    return last


if __name__ == '__main__':
    names = {'local': 'local', 'adv': 'advection', 'dh': 'depth gradient', 'bed': 'bed slope', 'fr': 'friction'}
    for key, val in situations():
        m = max(val.values())
        print(key, ', '.join(f'{names[k]} {v:.1e} ({v / m:.2g})' for k, v in val.items()))
