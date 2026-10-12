"""Cell indices and input coordinates, matching m_record.resolve_xy.

Both panels share a 7 x 5 square-cell geometry. Panel (b) is explicitly a
local-coordinate example; georeferenced input is explained separately.
"""
from pathlib import Path
from io import StringIO
import math
from _style import plt, Rectangle, FancyArrowPatch, C_P, C_C, C_B, C_X, out_path
from _schematic import drawing_style, text, block, line, INK, MUTED, RULE

CANVAS = (1575, 975)
DPI = 150
NX, NY = 7, 5
POINT = (3.4, 1.6)  # local coordinates, in units of dx and dy
CELL = (math.floor(POINT[0])+1, math.floor(NY-POINT[1])+1)
GRID_BOXES = [(156, 180, 490, 350), (936, 180, 490, 350)]
T = {
    'ja': {
        'a': '(a) セル番号とセル中心',
        'a_sub': '番号は1始まり。i は西→東、j は北→南。',
        'b': '(b) 座標からセルを求める',
        'b_sub': '地理参照なしの例: 南西端が (0, 0)、単位は m。',
        'i': 'i = 1 … nx（東向きに増加）',
        'axes': 'x は東向き正、y は北向き正',
        'centre': 'セル中心: 水深 h・地盤高 z などの位置',
        'selected': '強調セル: (i, j) = (4, 4)',
        'centre_xy': '中心のローカル座標: (3.5 dx, 1.5 dy)',
        'point': '指定点 P = (3.4 dx, 1.6 dy)',
        'resolved': 'P を含むセル: (i, j) = (4, 4)',
        'example': 'nx = 7, ny = 5 の例。P はセル中心でなくてもよい。',
        'gis_title': '0始まりの行・列番号を使う場合',
        'gis': 'i = 列番号 + 1、j = 行番号 + 1。\nGISツールが表示する番号の規約を確認する。',
        'abs_title': '地理参照がある場合は絶対座標を入力',
        'absolute': '入力ラスタと同じ座標系・単位で指定する。\n投影座標は m、経緯度は（経度, 緯度）の度。',
        'abs_note': 'この場合、南西端を (0, 0) とする指定は使わない。',
        'check': 'セル境界ちょうどを避けて内部の点を指定し、初期化時に表示されるセル番号を確認する。',
    },
    'en': {
        'a': '(a) Cell indices and cell centres',
        'a_sub': '1-based indices. i increases eastward; j southward.',
        'b': '(b) From coordinates to a cell',
        'b_sub': 'No georeferencing: SW corner at (0, 0); units are m.',
        'i': 'i = 1 … nx (increases eastward)',
        'axes': 'x is positive east; y is positive north',
        'centre': 'Cell centre: depth h, ground elevation z, etc.',
        'selected': 'Highlighted cell: (i, j) = (4, 4)',
        'centre_xy': 'Local coordinates of its centre: (3.5 dx, 1.5 dy)',
        'point': 'Specified point P = (3.4 dx, 1.6 dy)',
        'resolved': 'Cell containing P: (i, j) = (4, 4)',
        'example': 'Example: nx = 7, ny = 5. P need not be a cell centre.',
        'gis_title': 'When using 0-based row / column indices',
        'gis': 'i = column + 1; j = row + 1.\nCheck the index convention used by your GIS tool.',
        'abs_title': 'With georeferencing, enter absolute coordinates',
        'absolute': 'Use the coordinate system and units of the input raster.\nProjected: m; geographic: (longitude, latitude) in degrees.',
        'abs_note': 'Do not use coordinates relative to the SW corner in this case.',
        'check': 'Point inside a cell, away from its boundaries. Check the resolved cell indices printed at initialization.',
    },
}


def _axes(fig, box, xlim, ylim):
    left, top, width, height = box
    ax = fig.add_axes([left/CANVAS[0], (CANVAS[1]-top-height)/CANVAS[1],
                       width/CANVAS[0], height/CANVAS[1]])
    ax.set(xlim=xlim, ylim=ylim)
    ax.axis('off')
    return ax


def _grid(fig, box):
    ax = _axes(fig, box, (0, NX), (0, NY))
    ax.set_aspect('equal')
    ax.add_patch(Rectangle((CELL[0]-1, NY-CELL[1]), 1, 1,
                           fc=C_B, alpha=.55, ec='none', zorder=1))
    for i in range(NX+1):
        line(ax, [(i, 0), (i, NY)], C_P, .75, z=2)
    for j in range(NY+1):
        line(ax, [(0, j), (NX, j)], C_P, .75, z=2)
    return ax


def _arrow(ax, p, q, color=INK, style='-|>', lw=1.1):
    a = FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=10,
                       lw=lw, color=color, shrinkA=0, shrinkB=0, zorder=8)
    ax.add_patch(a)
    return a


def build(lang):
    """Build a vector-only figure with a fixed layout in both languages."""
    t = T[lang]
    fig = plt.figure(figsize=(CANVAS[0]/DPI, CANVAS[1]/DPI), dpi=DPI)
    page = _axes(fig, (0, 0, *CANVAS), (0, CANVAS[0]), (CANVAS[1], 0))
    for left, title, sub in [(26, 'a', 'a_sub'), (806, 'b', 'b_sub')]:
        text(page, left, 24, t[title], size=11.6, weight='bold')
        text(page, left, 66, t[sub], size=9, color=MUTED)
    text(page, 156, 111, t['i'], size=8.8, color=MUTED)
    _arrow(page, (156, 148), (646, 148), MUTED)
    _arrow(page, (127, 180), (127, 530), MUTED)
    text(page, 107, 355, 'j', size=10, color=MUTED, ha='right', va='center')
    text(page, 936, 111, t['axes'], size=8.8, color=MUTED)
    a, b = [_grid(fig, box) for box in GRID_BOXES]
    for i, j, label in [(1, 1, '(1, 1)'), (NX, 1, '(nx, 1)'),
                        (1, NY, '(1, ny)'), (NX, NY, '(nx, ny)')]:
        text(a, i-.5, NY-j+.5, label, size=8.0, color=MUTED,
             ha='center', va='center')
    a.plot(CELL[0]-.5, NY-CELL[1]+.5, 'o', color=C_C, ms=6.6, zorder=9)
    px, py = POINT
    line(b, [(px, 0), (px, py)], C_X, 1, ls='--', z=3)
    line(b, [(0, py), (px, py)], C_X, 1, ls='--', z=3)
    b.plot(px, py, 'o', color=C_X, ms=6.6, zorder=9)
    text(b, px+.24, py, 'P', size=10, color=C_X, va='center')
    # Coordinate axes meet at the SW outer corner, not the first cell centre.
    _arrow(page, (936, 530), (1501, 530), lw=1.35)
    _arrow(page, (936, 530), (936, 147), lw=1.35)
    page.plot(936, 530, 'o', color=INK, ms=4, zorder=9)
    text(page, 1513, 530, 'x', size=10, va='center')
    text(page, 949, 148, 'y', size=10, va='center')
    text(page, 921, 544, '(0, 0)', size=8.7, ha='right')
    _arrow(page, (1006, 562), (1076, 562), MUTED, '<->', .9)
    text(page, 1041, 573, 'dx', size=8.5, color=MUTED, ha='center')
    _arrow(page, (904, 390), (904, 460), MUTED, '<->', .9)
    text(page, 890, 425, 'dy', size=8.5, color=MUTED, ha='right', va='center')
    page.plot(40, 621, 'o', color=C_C, ms=5.5)
    text(page, 64, 608, t['centre'], size=9.0, color=C_C)
    text(page, 26, 650, t['selected'], size=9.0)
    text(page, 26, 684, t['centre_xy'], size=8.6, color=MUTED)
    page.plot(820, 621, 'o', color=C_X, ms=5.5)
    text(page, 844, 608, t['point'], size=9.0, color=C_X)
    text(page, 806, 650, t['resolved'], size=9.0)
    text(page, 806, 684, t['example'], size=8.6, color=MUTED)
    for left in (26, 806):
        line(page, [(left, 739), (left+720, 739)], RULE, .9)
    text(page, 26, 763, t['gis_title'], size=9.2, weight='bold')
    block(page, 26, 801, t['gis'], 720, size=8.8)
    text(page, 806, 763, t['abs_title'], size=9.2, weight='bold')
    block(page, 806, 801, t['absolute'], 720, size=8.8)
    text(page, 806, 864, t['abs_note'], size=8.2, color=MUTED)
    text(page, 26, 930, t['check'], size=8.6, color=MUTED)
    return fig


def draw(lang):
    if lang not in T:
        raise ValueError('lang must be ja or en')
    png = Path(out_path('coordinates_cells', lang))
    with drawing_style():
        fig = build(lang)
        try:
            fig.savefig(png, dpi=DPI)
            svg = StringIO()
            fig.savefig(svg, format='svg', metadata={'Date': None,
                'Description': 'ENCflow cell numbering and coordinate interpretation. Schematic.'})
            clean = '\n'.join(s.rstrip() for s in svg.getvalue().splitlines())+'\n'
            png.with_suffix('.svg').write_text(clean, encoding='utf-8', newline='\n')
        finally:
            plt.close(fig)
    return str(png)
