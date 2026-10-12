"""ENC grid supplement: passage widths of the eight edges and the cell-velocity
reconstruction weights. Regenerate only this page with make_guide_figs.py encgrid.
"""
from _terms import *

G = {'ja': {'a': '(a) 8 本のエッジの通過幅(正方セル)',
            'b': '(b) セル流速 u の再構成の重み',
            'axis': '法線エッジ: L = (1 − p_d) Δ',
            'diag': '斜めエッジ: L = (p_d/2)·√2 Δ',
            'share': '一辺の分け方: (1 − p_d) + 2·(p_d/2) = 1',
            'default': '既定 p_d = 2/(2+√2) = 0.586 → 8 本とも L = 0.414 Δ',
            'pd0': 'p_d = 0: 4 近傍格子(斜めは通過幅ゼロ)',
            'u_formula': 'u = ½ Σ (ℓ^y_k / n_{k,x}) u_{n,k}',
            'w_axis': '東西: ±(1 − p_d)/2',
            'w_diag': '斜め: ±p_d/(2√2)',
            'check': '一様流 (u, 0) では法線成分が ±u、±u/√2 で\n重みの和 = (1 − p_d) + p_d = 1 → u が返る',
            'smooth': '横断方向に変わる流れでは隣の行を拾い\nu_c = u + (p_d/4) Δ² ∂²u/∂y² の平滑化を含む'},
     'en': {'a': '(a) Passage widths of the eight edges (square cell)',
            'b': '(b) Weights of the cell-velocity reconstruction (u)',
            'axis': 'axis edge: L = (1 − p_d) Δ',
            'diag': 'diagonal edge: L = (p_d/2)·√2 Δ',
            'share': 'one side is shared as (1 − p_d) + 2·(p_d/2) = 1',
            'default': 'default p_d = 2/(2+√2) = 0.586 → all eight L = 0.414 Δ',
            'pd0': 'p_d = 0: 4-neighbour grid (diagonals carry no width)',
            'u_formula': 'u = ½ Σ (ℓ^y_k / n_{k,x}) u_{n,k}',
            'w_axis': 'east/west: ±(1 − p_d)/2',
            'w_diag': 'diagonal: ±p_d/(2√2)',
            'check': 'uniform flow (u, 0): normal components ±u, ±u/√2;\nweights sum to (1 − p_d) + p_d = 1 → returns u',
            'smooth': 'a flow varying across rows samples the neighbouring rows:\nu_c = u + (p_d/4) Δ² ∂²u/∂y² (second-order smoothing)'}}

PD = 2 / (2 + 2 ** .5)


def cell_grid(base, x0, y0, d):
    # 3x3 cells, centre cell shaded; returns centre of the central cell
    rect(base, x0 + d, y0 + d, d, d, '#eaf2fc')
    grid(base, x0, y0, 3, 3, d)
    return np.array([x0 + 1.5 * d, y0 + 1.5 * d])


def build(lang):
    t = G[lang]; fig, base = canvas(900)
    text(base, 48, 32, t['a'], 13, weight='bold'); text(base, 940, 32, t['b'], 13, weight='bold')
    # ---- (a) passage widths
    d = 170; c = cell_grid(base, 110, 95, d)
    lp, ld = (1 - PD), PD / 2
    # eight edges from the centre
    for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
        line(base, [c, c + d * np.array([dx, dy])], BLUE, 1.4)
    for dx, dy in [(1, 1), (-1, 1), (1, -1), (-1, -1)]:
        line(base, [c, c + d * np.array([dx, dy])], BLUE, 1.2, ls='--')
    # passage width segments on the east side of the centre cell (x = c.x + d/2)
    xe = c[0] + d / 2
    ya, yb = c[1] - d / 2, c[1] + d / 2
    # normal (axis) share in the middle, diagonal shares at the ends
    segs = [(ya, ya + ld * d, ORANGE), (ya + ld * d, yb - ld * d, BLUE), (yb - ld * d, yb, ORANGE)]
    for y1, y2, col in segs:
        line(base, [(xe + 14, y1), (xe + 14, y2)], col, 5.0)
    text(base, xe + 26, ya + 2, '(p_d/2)Δ', 8.5, color=ORANGE)
    text(base, xe + 30, c[1] + 10, '(1 − p_d)Δ', 8.5, color=BLUE)
    text(base, xe + 26, yb - 16, '(p_d/2)Δ', 8.5, color=ORANGE)
    dot(base, c, INK)
    for i in range(3):
        for j in range(3):
            if (i, j) != (1, 1): dot(base, (110 + (i + .5) * d, 95 + (j + .5) * d))
    legend_rows(base, 48, 640, [(BLUE, '-', t['axis']), (ORANGE, '--', t['diag'])], 760, 44, 9.5)
    block(base, 48, 745, t['share'] + '\n' + t['default'] + '\n' + t['pd0'], 800, 9.5, color=MUTED)
    # ---- (b) reconstruction weights
    c2 = cell_grid(base, 1000, 95, d)
    text(base, 940, 640, t['u_formula'], 11)
    wa, wd = lp / 2, PD / (2 * 2 ** .5)
    labels = {(1, 0): f'+{wa:.3f}', (-1, 0): f'−{wa:.3f}', (1, 1): f'+{wd:.3f}', (1, -1): f'+{wd:.3f}',
              (-1, 1): f'−{wd:.3f}', (-1, -1): f'−{wd:.3f}', (0, 1): '0', (0, -1): '0'}
    for (dx, dy), lab in labels.items():
        p = c2 + d * np.array([dx, dy]) * .5
        col = BLUE if dy == 0 and dx != 0 else (ORANGE if dx != 0 else MUTED)
        line(base, [c2, c2 + d * np.array([dx, dy])], col, 1.2, ls='-' if dy == 0 else '--')
        text(base, p[0] + (8 if dx >= 0 else -8), p[1] - 6, lab, 8.5, color=col,
             ha='left' if dx >= 0 else 'right')
    dot(base, c2, INK)
    legend_rows(base, 940, 680, [(BLUE, '-', t['w_axis']), (ORANGE, '--', t['w_diag'])], 760, 44, 9.5)
    block(base, 940, 775, t['check'] + '\n' + t['smooth'], 800, 9.5, color=MUTED)
    return fig


def draw(lang):
    with drawing_style(): return export(build(lang), 'encgrid_geometry', lang)
