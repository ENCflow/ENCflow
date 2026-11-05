"""steep-slope gravity correction explanation (docs/users_guide/steep_slope.md and its English mirror):
the 1-D meaning of the effective gravity, the stencils used for an axis edge and a
diagonal edge, and the edge-direction bias of the old per-edge definition.

Regenerate only this page with make_guide_figs.py steepslope.  The bias curves are
closed-form (developer.md §91); no result files are needed.
"""
from _terms import *

T = {'ja': {
 'c_title': '(a) 1 次元の意味: 地盤に直角な静水圧と水平の格子間隔',
 'c_h': 'h(鉛直の水深)', 'c_hn': 'h cosθ(地盤に直角な厚さ)',
 'c_dx': 'Δx(格子は水平に等間隔)', 'c_ds': 'Δx / cosθ(地盤に沿う長さ)',
 'c_pb': '底面の圧力 p_b = ρ g cosθ · h cosθ = ρ g h cos²θ',
 'c_g': 'g', 'c_gs': 'g sinθ', 'c_gn': 'g cosθ',
 'c_note': '等流の駆動力(水平面積あたり、水平成分)は p_b · tanθ = ρ g h cos²θ tanθ = ρ g_e h tanθ。\n'
           '斜面に沿う式の ρ g (h cosθ) sinθ と同じになる。水平座標の式の g を g_e = g cos²θ に置き換えるのはこのため。',
 's_a': '(b) 軸方向の辺(c = (i, j) と n = (i+1, j))',
 's_b': '(c) 斜めの辺(c = (i, j) と n = (i+1, j+1))',
 's_cn': '辺の両セル(法線成分 s_n)', 's_tan': '接線成分 s_t に使う両隣',
 's_zero': '計算はするが、この辺の接線には効かない(∂z/∂x)',
 's_n_a': 's_n = (z_n − z_c) / Δx', 's_n_b': 's_n = (z_n − z_c) / Δr',
 's_t_a': 's_t = −(∂z/∂y|_c + ∂z/∂y|_n) / 2',
 's_t_b': 's_t = [(∂z/∂x|_c + ∂z/∂x|_n) n_y − (∂z/∂y|_c + ∂z/∂y|_n) n_x] / 2',
 's_ge': 'g_e = g / (1 + s_n² + s_t²)',
 's_mm': 'セルの勾配: ∂z/∂x|_(i,j) = minmod(z_(i+1,j) − z_(i,j), z_(i,j) − z_(i−1,j)) / Δx(∂z/∂y も同様。軸方向の 4 近傍)',
 'b_title': '(d) 一様な斜面での辺の有効重力(勾配 G、下り向きと辺の法線のなす角 α)',
 'b_x': '辺の法線と下り向きのなす角 α (°)', 'b_y': 'g_e / g',
 'b_old': '旧: 辺の法線方向の勾配だけ 1/(1 + G² cos²α)', 'b_new': '現行: 1/(1 + |∇z|²) = cos²θ(向きによらない)',
}, 'en': {
 'c_title': '(a) Meaning in 1-D: bed-normal hydrostatic pressure and a horizontal grid',
 'c_h': 'h (vertical depth)', 'c_hn': 'h cosθ (bed-normal thickness)',
 'c_dx': 'Δx (grid uniform in the horizontal)', 'c_ds': 'Δx / cosθ (along the bed)',
 'c_pb': 'bed pressure p_b = ρ g cosθ · h cosθ = ρ g h cos²θ',
 'c_g': 'g', 'c_gs': 'g sinθ', 'c_gn': 'g cosθ',
 'c_note': 'Driving force of uniform flow (per horizontal area, horizontal component): p_b · tanθ = ρ g h cos²θ tanθ = ρ g_e h tanθ,\n'
           'equal to ρ g (h cosθ) sinθ of the along-slope equation. Hence g is replaced by g_e = g cos²θ in the horizontal-coordinate equations.',
 's_a': '(b) Axis edge (c = (i, j) and n = (i+1, j))',
 's_b': '(c) Diagonal edge (c = (i, j) and n = (i+1, j+1))',
 's_cn': 'cells of the edge (normal component s_n)', 's_tan': 'neighbours used for the tangential component s_t',
 's_zero': 'evaluated but not used by this edge’s tangent (∂z/∂x)',
 's_n_a': 's_n = (z_n − z_c) / Δx', 's_n_b': 's_n = (z_n − z_c) / Δr',
 's_t_a': 's_t = −(∂z/∂y|_c + ∂z/∂y|_n) / 2',
 's_t_b': 's_t = [(∂z/∂x|_c + ∂z/∂x|_n) n_y − (∂z/∂y|_c + ∂z/∂y|_n) n_x] / 2',
 's_ge': 'g_e = g / (1 + s_n² + s_t²)',
 's_mm': 'Cell gradient: ∂z/∂x|_(i,j) = minmod(z_(i+1,j) − z_(i,j), z_(i,j) − z_(i−1,j)) / Δx (likewise ∂z/∂y; the four axis neighbours)',
 'b_title': '(d) Effective gravity of an edge on a uniform slope (gradient G, angle α between the edge normal and the downslope direction)',
 'b_x': 'angle α between the edge normal and the downslope direction (°)', 'b_y': 'g_e / g',
 'b_old': 'old: edge-normal gradient only, 1/(1 + G² cos²α)', 'b_new': 'now: 1/(1 + |∇z|²) = cos²θ (direction-independent)',
}}

CELL_C, CELL_T, CELL_Z = '#cfe0f6', '#fbe3cf', '#efeeea'


def build_concept(lang):
    t = T[lang]; fig, ax = canvas(780)
    text(ax, 48, 30, t['c_title'], 13, weight='bold')
    th = np.radians(25.0); tn = np.tan(th)
    x0, y0, x1 = 160, 250, 1000                     # bed from (x0, y0) down to the right (y down)
    bed = lambda x: y0 + (x - x0) * tn
    hn = 95.0                                        # bed-normal thickness (px)
    nvec = np.array([np.sin(th), -np.cos(th)])       # upward bed normal on the canvas
    tdown = np.array([np.cos(th), np.sin(th)])       # downslope unit vector
    ax.add_patch(Polygon([(x0, bed(x0)), (x1, bed(x1)), (x1, 640), (x0, 640)], closed=True, fc=SOIL, ec='none', zorder=1))
    line(ax, [(x0, bed(x0)), (x1, bed(x1))], BED, 1.6, z=3)
    top = [np.array([x0, bed(x0)]) + hn * nvec, np.array([x1, bed(x1)]) + hn * nvec]
    ax.add_patch(Polygon([(x0, bed(x0)), (x1, bed(x1)), tuple(top[1]), tuple(top[0])], closed=True, fc=WATER, ec='none', zorder=2))
    line(ax, [tuple(top[0]), tuple(top[1])], BLUE, 1.4, z=3)
    # vertical depth h
    xa = 400; hv = hn / np.cos(th)
    ax.add_patch(FancyArrowPatch((xa, bed(xa)), (xa, bed(xa) - hv), arrowstyle='<->', mutation_scale=10, color=INK, lw=1.2, zorder=8))
    text(ax, xa + 6, bed(xa) - hv - 6, t['c_h'], 10, ha='left', va='bottom')
    # bed-normal thickness
    xb = 560; pb = np.array([xb, bed(xb)]); pt = pb + hn * nvec
    ax.add_patch(FancyArrowPatch(tuple(pb), tuple(pt), arrowstyle='<->', mutation_scale=10, color=ORANGE, lw=1.2, zorder=8))
    text(ax, pt[0] + 10, pt[1] - 6, t['c_hn'], 10, color=ORANGE, va='bottom')
    # theta
    xt = 860
    line(ax, [(xt, bed(xt)), (xt + 150, bed(xt))], MUTED, 0.9, ls='--')
    ang = np.linspace(0, th, 20); r = 110
    line(ax, list(zip(xt + r * np.cos(ang), bed(xt) + r * np.sin(ang))), MUTED, 0.9)
    text(ax, xt + r + 10, bed(xt) + 26, 'θ', 12, color=MUTED, va='center')
    # horizontal spacing (below the bed) and length along the bed (in the ground, parallel to it)
    xa0, xa1 = 230, 330
    yd = bed(xa1) + 150
    line(ax, [(xa0, bed(xa0)), (xa0, yd + 8)], MUTED, 0.6, ls=':'); line(ax, [(xa1, bed(xa1)), (xa1, yd + 8)], MUTED, 0.6, ls=':')
    dimension(ax, (xa0, yd), (xa1, yd), t['c_dx'], (xa0 + 50, yd + 12))
    p0 = np.array([xa0, bed(xa0)]) - 40 * nvec; p1 = np.array([xa1, bed(xa1)]) - 40 * nvec
    ax.add_patch(FancyArrowPatch(tuple(p0), tuple(p1), arrowstyle='<->', mutation_scale=9, color=GREEN, lw=1, zorder=8))
    text(ax, p0[0] - 30, p1[1] + 24, t['c_ds'], 10, color=GREEN, va='top')
    # gravity components (inset to the right)
    q = np.array([1250.0, 250.0]); L = 150
    line(ax, [tuple(q - 130 * tdown), tuple(q + 130 * tdown)], BED, 1.6, z=3)
    qq = q + 40 * nvec
    arrow(ax, [tuple(qq), (qq[0], qq[1] + L)], INK, 1.5)
    text(ax, qq[0] + 8, qq[1] + L, t['c_g'], 11, va='center')
    gs = qq + L * np.sin(th) * tdown
    arrow(ax, [tuple(qq), tuple(gs)], GREEN, 1.4)
    text(ax, gs[0] + 8, gs[1] - 2, t['c_gs'], 10, color=GREEN, va='bottom')
    gn = qq - L * np.cos(th) * nvec
    arrow(ax, [tuple(qq), tuple(gn)], ORANGE, 1.4)
    text(ax, gn[0] - 10, gn[1] + 4, t['c_gn'], 10, color=ORANGE, ha='right', va='top')
    text(ax, 1100, 440, t['c_pb'], 10.5)
    block(ax, 48, 680, t['c_note'], 1700, 10)
    return fig


def ij(a, b):
    """(i+a, j+b) の表記(負の符号は −)。"""
    f = lambda s, k: s if k == 0 else f"{s}+{k}" if k > 0 else f"{s}−{-k}"
    return f"({f('i', a)}, {f('j', b)})"


def stencil(ax, x0, y0, d, cells):
    """cells: dict (i, j) -> (fill, label); draws the grid of the given extent."""
    ii = [c[0] for c in cells]; jj = [c[1] for c in cells]
    imin, imax, jmin, jmax = min(ii), max(ii), min(jj), max(jj)
    for (i, j), (fill, lab) in cells.items():
        rect(ax, x0 + (i - imin) * d, y0 + (j - jmin) * d, d, d, fill)
        text(ax, x0 + (i - imin + .5) * d, y0 + (j - jmin + .5) * d, lab, 9.5, ha='center', va='center', color=INK)
    grid(ax, x0, y0, imax - imin + 1, jmax - jmin + 1, d)
    cen = lambda i, j: np.array([x0 + (i - imin + .5) * d, y0 + (j - jmin + .5) * d])
    return cen


def build_stencil(lang):
    t = T[lang]; fig, ax = canvas(1000)
    d = 140
    # (b) axis edge: columns i-1..i+2, rows j-1..j+1
    text(ax, 48, 30, t['s_a'], 13, weight='bold')
    cells = {}
    for i in range(-1, 3):
        for j in range(-1, 2):
            if (i, j) in [(0, 0), (1, 0)]: cells[(i, j)] = (CELL_C, 'c' if i == 0 else 'n')
            elif (i, j) in [(0, -1), (1, -1), (0, 1), (1, 1)]: cells[(i, j)] = (CELL_T, ij(i, j))
            elif (i, j) in [(-1, 0), (2, 0)]: cells[(i, j)] = (CELL_Z, ij(i, j))
            else: cells[(i, j)] = ('white', '')
    cen = stencil(ax, 110, 90, d, cells)
    c, n = cen(0, 0), cen(1, 0)
    arrow(ax, [tuple(c + [18, -26]), tuple(n + [-18, -26])], BLUE, 1.6)
    edge(ax, tuple((c + n) / 2), BLUE)
    for p in (c, n):
        arrow(ax, [tuple(p + [0, -d + 26]), tuple(p + [0, -22])], ORANGE, 1.2)
        arrow(ax, [tuple(p + [0, 22]), tuple(p + [0, d - 26])], ORANGE, 1.2)
    # (c) diagonal edge: columns i-1..i+2, rows j-1..j+2
    xo = 940
    text(ax, xo - 40, 30, t['s_b'], 13, weight='bold')
    nb_c = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    nb_n = [(0, 1), (2, 1), (1, 0), (1, 2)]
    labd = {(0, 0): 'c', (1, 1): 'n'}
    cells = {}
    for i in range(-1, 3):
        for j in range(-1, 3):
            if (i, j) in labd: cells[(i, j)] = (CELL_C, labd[(i, j)])
            elif (i, j) in nb_c or (i, j) in nb_n: cells[(i, j)] = (CELL_T, ij(i, j))
            else: cells[(i, j)] = ('white', '')
    cen = stencil(ax, xo, 90, d, cells)
    c, n = cen(0, 0), cen(1, 1)
    u = (n - c) / np.hypot(*(n - c))
    arrow(ax, [tuple(c + 30 * u + [14, -14]), tuple(n - 30 * u + [14, -14])], BLUE, 1.6)
    edge(ax, tuple((c + n) / 2), BLUE, diag=True)
    tv = np.array([u[1], -u[0]]) * 95
    m = (c + n) / 2
    line(ax, [tuple(m - tv), tuple(m + tv)], ORANGE, 1.2, ls='--')
    # legend and formulas
    yl = 720
    for k, (fill, key) in enumerate([(CELL_C, 's_cn'), (CELL_T, 's_tan'), (CELL_Z, 's_zero')]):
        rect(ax, 110, yl + k * 40, 34, 24, fill, edge=RULE)
        text(ax, 156, yl + k * 40 + 2, t[key], 10)
    text(ax, 940, yl, t['s_n_a'] + '      ' + t['s_n_b'], 10.5)
    text(ax, 940, yl + 40, t['s_t_a'], 10.5)
    text(ax, 940, yl + 80, t['s_t_b'], 10.5)
    text(ax, 940, yl + 120, t['s_ge'], 11, weight='bold')
    block(ax, 110, yl + 190, t['s_mm'], 1640, 10)
    return fig


def build_bias(lang):
    t = T[lang]; fig, ax = canvas(640)
    text(ax, 48, 30, t['b_title'], 13, weight='bold')
    pa = plot_axes(fig, 150, 90, 1050, 450)
    al = np.linspace(0, 90, 181)
    for G, col in ((0.4, BLUE), (1.0, ORANGE)):
        th = np.degrees(np.arctan(G))
        pa.plot(al, 1 / (1 + G**2 * np.cos(np.radians(al))**2), color=col, lw=1.6, ls='--')
        pa.plot(al, np.full_like(al, 1 / (1 + G**2)), color=col, lw=1.8)
        pa.text(2, 1 / (1 + G**2) - 0.012, f'G = {G:g}(θ = {th:.1f}°)', color=col, fontsize=9.5, va='top')
    pa.set_xlim(0, 90); pa.set_ylim(0.45, 1.02); pa.set_xticks([0, 22.5, 45, 67.5, 90])
    pa.set_xlabel(t['b_x']); pa.set_ylabel(t['b_y'])
    legend_rows(ax, 1250, 110, [(MUTED, '--', t['b_old']), (MUTED, '-', t['b_new'])], width=520, step=70)
    return fig


def draw(lang):
    with drawing_style():
        export(build_concept(lang), 'steepslope_concept', lang)
        export(build_stencil(lang), 'steepslope_stencil', lang)
        return export(build_bias(lang), 'steepslope_bias', lang)
