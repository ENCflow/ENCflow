"""Nesting layout and exchange, with integer-aligned parent/child geometry.

Drawn example: r=3, nb=3, nest_bc=2, no sponge. Feedback illustrates
nest_fb=1 with unit effective area fraction. See m_nest.setup/prolong/restrict.
This module is called by make_nest_figs.py; it does not draw nest_time/nest_bc.
"""
from io import StringIO
from pathlib import Path
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
from guide._schematic import drawing_style, text, line, INK, MUTED, RULE

CANVAS, DPI = (1575, 1080), 150
NXP, NYP, R, NB = 14, 11, 3, 3
I0, J0, NFP = 5, 3, 6
NC = NFP*R
IP, JP = 8, 6  # feedback destination; its complete 3 x 3 child block
BAND_CELL = (1, 4)
PARENT_BOX = (100, 173, 560, 440)
STENCIL_BOX = (850, 186, 180, 180)
SOURCE_BOX = (855, 665, 180, 180)
TARGET_BOX = (1320, 665, 180, 180)
PARENT, CHILD, BAND, FLOW, FEEDBACK = '#6b6a66', '#2a78d6', '#f7d487', '#eb6834', '#639845'
CHILD_FILL, GREEN_FILL = '#eaf2fc', '#e1efd7'
T = {
    'ja': {
        'a': '(a) 親の中に子格子を配置',
        'a_sub': '親: 14 × 11 セル / 子: 18 × 18 セル / r = 3',
        'i': 'i（西 → 東）', 'j': 'j（北 → 南）',
        'rim': '斜線: 親の外縁1セルには子を置かない',
        'corner': '北西角: 親 (i0, j0) = (5, 3) と子 (1, 1) が一致',
        'band': '境界帯: nb = 3 子セル（親1セル分の幅）',
        'footprint': '子の全体は、親の6 × 6セルと同じ範囲。',
        'selected': '緑枠: 親 (8, 6) と重なる3 × 3子セル',
        'interior': 'この例の置換対象: 親 i = 6…9、j = 4…7。\n境界帯を含む親セルは置換しない。',
        'b': '(b) 親子の交換',
        'b_sub': '例: nest_bc = 2 / nest_fb = 1 / スポンジなし',
        'p2c': '親 → 子: 各サブステップの開始時',
        'p2c_note': '親の値を時空間補間し、\n境界帯の子セルに置く。',
        'quantities': 'nest_bc = 2:\n水位・流速・エッジ流量',
        'width': 'nb = 3',
        'stencil': '■ 親セル中心 / ● 帯の子セル中心 (1, 4)',
        'stencil_note': 'セル中心量の空間補間を図示（親4点が湿潤の例）。',
        'c2p': '子 → 親: 親のステップ終了時',
        'c2p_note': 'nest_fb = 1 の例: 内部の3 × 3子セルを面積平均',
        'average': '面積平均',
        'source': '子 i = 10…12\nj = 10…12',
        'target': '親 (8, 6)',
        'same_area': '同じ範囲を覆う親セルへ戻す（右の親セルは別置き表示）。',
        'modes': 'Flather（nest_bc = 3）は帯なし。スポンジ（nest_bc = 4）も子→親の置換対象から除く。',
        'auto': '帯幅の自動値: 移流スキーム1は2セル、2・3は3セル。平均の例は有効面積率 = 1。',
    },
    'en': {
        'a': '(a) Place the child inside its parent',
        'a_sub': 'Parent: 14 × 11 cells / child: 18 × 18 cells / r = 3',
        'i': 'i (west → east)', 'j': 'j (north → south)',
        'rim': 'Hatching: keep the outer parent-cell rim free',
        'corner': 'Same NW corner: parent (i0, j0) = (5, 3), child (1, 1)',
        'band': 'Band: nb = 3 child cells (one parent-cell width)',
        'footprint': 'The child covers the same area as 6 × 6 parent cells.',
        'selected': 'Green: 3 × 3 child cells covering parent (8, 6)',
        'interior': 'Replaced here: parent i = 6…9, j = 4…7.\nParent cells containing the band are excluded.',
        'b': '(b) Exchange between parent and child',
        'b_sub': 'Example: nest_bc = 2 / nest_fb = 1 / no sponge',
        'p2c': 'Parent → child: at each sub-step start',
        'p2c_note': 'Interpolate parent values in space\nand time into child band cells.',
        'quantities': 'nest_bc = 2:\nlevel, velocity, edge discharge',
        'width': 'nb = 3',
        'stencil': '■ Parent cell centres / ● child band cell centre (1, 4)',
        'stencil_note': 'Spatial interpolation of cell quantities; all 4 parent points are wet.',
        'c2p': 'Child → parent: at the parent-step end',
        'c2p_note': 'nest_fb = 1: area average of 3 × 3 interior child cells',
        'average': 'Area average',
        'source': 'Child i = 10…12\nj = 10…12',
        'target': 'Parent (8, 6)',
        'same_area': 'Return to the parent cell over the same area (shown separately).',
        'modes': 'Flather (nest_bc = 3) has no band. The sponge (nest_bc = 4) is also excluded from child-to-parent replacement.',
        'auto': 'Automatic band: 2 cells for advection scheme 1; 3 for schemes 2 and 3. Mean shown for area fraction = 1.',
    },
}


def child_corner(i, j):
    """North-west cell corner in parent-cell units, x east and y south."""
    return np.array([I0-1+(i-1)/R, J0-1+(j-1)/R])


def feedback_indices():
    i1, j1 = (IP-I0)*R+1, (JP-J0)*R+1
    return i1, i1+R-1, j1, j1+R-1


def band_mask():
    j, i = np.mgrid[1:NC+1, 1:NC+1]
    return (i <= NB) | (i > NC-NB) | (j <= NB) | (j > NC-NB)


def interpolation_geometry():
    centre = child_corner(*BAND_CELL) + .5/R
    ia, ja = np.floor(centre+.5).astype(int)
    points = np.array([[ia-.5, ja-.5], [ia+.5, ja-.5],
                       [ia-.5, ja+.5], [ia+.5, ja+.5]])
    wx, wy = centre-[ia-.5, ja-.5]
    weights = np.array([(1-wx)*(1-wy), wx*(1-wy), (1-wx)*wy, wx*wy])
    return centre, points, weights


def axes(fig, box, xlim, ylim):
    left, top, width, height = box
    ax = fig.add_axes([left/CANVAS[0], (CANVAS[1]-top-height)/CANVAS[1],
                       width/CANVAS[0], height/CANVAS[1]])
    ax.set(xlim=xlim, ylim=ylim)
    ax.axis('off')
    return ax


def rect(ax, x, y, w, h, face='none', edge='none', lw=1, z=2, **kwargs):
    p = Rectangle((x, y), w, h, facecolor=face, edgecolor=edge,
                  linewidth=lw, zorder=z, **kwargs)
    ax.add_patch(p)
    return p


def grid(ax, x, y, nx, ny, step, color, lw=.6, z=4):
    for i in range(nx+1):
        line(ax, [(x+i*step, y), (x+i*step, y+ny*step)], color, lw, z=z)
    for j in range(ny+1):
        line(ax, [(x, y+j*step), (x+nx*step, y+j*step)], color, lw, z=z)


def arrow(ax, p, q, color, style='-|>', lw=1.4, size=10):
    a = FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=size,
                        color=color, lw=lw, shrinkA=0, shrinkB=0, zorder=10)
    ax.add_patch(a)
    return a


def layout(fig):
    ax = axes(fig, PARENT_BOX, (0, NXP), (NYP, 0))
    ax.set_aspect('equal')
    # Four non-overlapping rim strips. Child bounds leave one parent-cell margin.
    for box in [(0, 0, NXP, 1), (0, NYP-1, NXP, 1),
                (0, 1, 1, NYP-2), (NXP-1, 1, 1, NYP-2)]:
        rect(ax, *box, face='#f4f3f0', edge='#c8c6c0', lw=0, hatch='////', z=1)
    grid(ax, 0, 0, NXP, NYP, 1, PARENT, .65)
    x, y = child_corner(1, 1)
    rect(ax, x, y, NFP, NFP, CHILD_FILL, z=5)
    width = NB/R
    for box in [(x, y, NFP, width), (x, y+NFP-width, NFP, width),
                (x, y+width, width, NFP-2*width),
                (x+NFP-width, y+width, width, NFP-2*width)]:
        rect(ax, *box, face=BAND, z=6)
    rect(ax, IP-1, JP-1, 1, 1, GREEN_FILL, z=6)
    grid(ax, x, y, NC, NC, 1/R, CHILD, .35, z=7)
    rect(ax, x, y, NFP, NFP, edge=CHILD, lw=1.7, z=8)
    rect(ax, IP-1, JP-1, 1, 1, edge=FEEDBACK, lw=2, z=9)
    ax.plot(x, y, 'o', color=FLOW, ms=6.2, zorder=10)
    return ax


def prolongation(fig):
    # Exact parent-cell coordinates around child band cell (1,4).
    ax = axes(fig, STENCIL_BOX, (3, 5), (4, 2))
    ax.set_aspect('equal')
    rect(ax, 4, 2, 1, 2, BAND)
    grid(ax, 3, 2, 2, 2, 1, PARENT, .9)
    grid(ax, 4, 2, R, 2*R, 1/R, CHILD, .55, z=5)
    line(ax, [(4, 2), (4, 4)], CHILD, 1.6)
    corner = child_corner(*BAND_CELL)
    centre, points, _ = interpolation_geometry()
    rect(ax, *corner, 1/R, 1/R, face='#fce2ce', edge=FLOW, lw=1.4, z=6)
    for p in points:
        line(ax, [p, centre], FLOW, .85, z=8)
    ax.plot(points[:, 0], points[:, 1], 's', color=PARENT, ms=5.2, zorder=9)
    ax.plot(*centre, 'o', color=FLOW, ms=5, zorder=10)
    return ax


def restriction(fig):
    i1, i2, j1, j2 = feedback_indices()
    source = axes(fig, SOURCE_BOX, (i1-1, i2), (j2, j1-1))
    source.set_aspect('equal')
    rect(source, i1-1, j1-1, R, R, GREEN_FILL)
    grid(source, i1-1, j1-1, R, R, 1, CHILD, .75)
    # Keep the entire outline stroke visible at the axes limits.
    rect(source, i1-1, j1-1, R, R, edge=FEEDBACK, lw=1.8, z=8, clip_on=False)
    target = axes(fig, TARGET_BOX, (IP-1, IP), (JP, JP-1))
    target.set_aspect('equal')
    rect(target, IP-1, JP-1, 1, 1, face=GREEN_FILL, edge=FEEDBACK,
         lw=1.8, z=8, linestyle='--', clip_on=False)
    return source, target


def build(lang):
    t = T[lang]
    fig = plt.figure(figsize=(CANVAS[0]/DPI, CANVAS[1]/DPI), dpi=DPI)
    page = axes(fig, (0, 0, *CANVAS), (0, CANVAS[0]), (CANVAS[1], 0))
    for left, title, sub in [(30, 'a', 'a_sub'), (815, 'b', 'b_sub')]:
        text(page, left, 22, t[title], size=11.4, weight='bold')
        text(page, left, 69, t[sub], size=9.0, color=MUTED)
    layout(fig)
    arrow(page, (100, 148), (660, 148), MUTED, lw=1)
    text(page, 380, 115, t['i'], size=8.8, color=MUTED, ha='center')
    arrow(page, (72, 173), (72, 613), MUTED, lw=1)
    text(page, 46, 393, t['j'], size=8.8, color=MUTED, ha='center', va='center', rotation=90)
    rect(page, 30, 654, 22, 22, face='#f4f3f0', edge='#c8c6c0', hatch='////', lw=0)
    text(page, 67, 650, t['rim'], size=9.0)
    page.plot(41, 715, 'o', color=FLOW, ms=6.2)
    text(page, 67, 701, t['corner'], size=8.8, color=FLOW)
    rect(page, 30, 752, 22, 22, face=BAND)
    text(page, 67, 748, t['band'], size=8.8)
    text(page, 30, 794, t['footprint'], size=8.8, color=CHILD)
    rect(page, 30, 848, 22, 22, face=GREEN_FILL, edge=FEEDBACK, lw=1.5)
    text(page, 67, 843, t['selected'], size=8.8, color=FEEDBACK)
    text(page, 30, 899, t['interior'], size=8.8)
    text(page, 815, 122, t['p2c'], size=10.0, color=FLOW, weight='bold')
    prolongation(fig)
    text(page, 1090, 189, t['p2c_note'], size=9.0)
    text(page, 1090, 279, t['quantities'], size=9.0, color=FLOW)
    arrow(page, (940, 394), (1030, 394), MUTED, style='<->', lw=.9, size=8)
    text(page, 985, 408, t['width'], size=8.6, color=MUTED, ha='center')
    text(page, 815, 456, t['stencil'], size=8.6)
    text(page, 815, 493, t['stencil_note'], size=8.1, color=MUTED)
    line(page, [(815, 537), (1545, 537)], RULE, .9)
    text(page, 815, 558, t['c2p'], size=10, color=FEEDBACK, weight='bold')
    text(page, 815, 604, t['c2p_note'], size=8.9)
    restriction(fig)
    arrow(page, (1060, 755), (1293, 755), FEEDBACK, lw=1.8, size=12)
    text(page, 1177, 710, t['average'], size=9.2, color=FEEDBACK, ha='center')
    text(page, 855, 866, t['source'], size=8.8, color=CHILD)
    text(page, 1320, 866, t['target'], size=8.8, color=FEEDBACK)
    text(page, 815, 936, t['same_area'], size=8.1, color=MUTED)
    line(page, [(30, 1000), (1545, 1000)], RULE, .9)
    text(page, 30, 1020, t['modes'], size=8.6)
    text(page, 30, 1053, t['auto'], size=8.0, color=MUTED)
    return fig


def draw(lang):
    if lang not in T:
        raise ValueError('lang must be ja or en')
    png = Path(__file__).resolve().parents[1]/('nest_layout'+('' if lang == 'ja' else '_en')+'.png')
    with drawing_style():
        fig = build(lang)
        try:
            fig.savefig(png, dpi=DPI)
            svg = StringIO()
            fig.savefig(svg, format='svg', metadata={'Date': None,
                'Description': 'ENCflow nested-grid layout and exchange; r=3, nb=3. Schematic.'})
            png.with_suffix('.svg').write_text('\n'.join(s.rstrip() for s in svg.getvalue().splitlines())+'\n',
                                              encoding='utf-8', newline='\n')
        finally:
            plt.close(fig)
    return str(png)
