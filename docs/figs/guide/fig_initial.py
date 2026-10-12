"""Initial depth, level and depression filling (m_state.set_h).

Panels (a)/(b) show the fixed-value cases 0/2; files 1/3 may vary spatially.
Panel (c) compares water and bed filling on the SAME illustrative channel
profile, before h0_rw is added. All interfaces share sampled bed vertices.
No solver results or input files are used or modified.
"""
from pathlib import Path
from io import StringIO
import numpy as np
from _style import (plt, Polygon, out_path,
                    C_WATER, C_WATER_L, C_GROUND, C_GROUND_L, C_SOIL)
from _schematic import (drawing_style, text, line, ground, wet_profile,
                        monotone_cubic, MUTED, RULE)

CANVAS = (1575, 1110)
DPI = 150
H0, E0, H0_RW = 0.4, 1.25, 0.35
CHANNEL = (6.2, 7.0)
CHANNEL_CUT = 0.45  # illustrative incision, deeper than the added water depth
# Include channel boundaries in the common sampling: the depth step is exact.
X = np.unique(np.r_[np.linspace(0, 10, 601), CHANNEL])
SPILL_X, SPILL_LEVEL = 6.8, 1.8
PIT_KNOTS_X = np.array([0, 1.0, 3.0, 4.0, SPILL_X, 8.2, 10.0])
PIT_KNOTS_Z = np.array([2.6, 2.3, 0.7, 0.85, SPILL_LEVEL, 1.05, 0.45])
PIT_X = np.unique(np.r_[np.linspace(0, 10, 601), PIT_KNOTS_X])
PIT_Z = monotone_cubic(PIT_KNOTS_X, PIT_KNOTS_Z, PIT_X)
T = {
    'ja': {
        'a': '(a) 水深を指定する',
        'a_sub': '図示: f_htype = 0（一様水深 h0）',
        'b': '(b) 水位を指定する',
        'b_sub': '図示: f_htype = 2（一定水位 e0）',
        'h': 'h = h0',
        'rw': '掘り込み河道: + h0_rw',
        'z': '地盤高 z',
        'e': '水面標高 e0',
        'dry': 'z ≥ e0: 乾燥',
        'a_note': 'f_htype = 1: h = max(H, 0)\nH は fn_hinit の水深分布。一様とは限らない。',
        'b_note': 'f_htype = 3: h = max(E − z, 0)\nE は fn_hinit の水位分布。水平とは限らない。',
        'b_formula': 'h = max(e0 − z, 0)',
        'c': '(c) 窪地を埋める: f_fill_depres',
        'c_sub': '同じ河道の窪地を比較。h0_rw を加える前の状態。',
        'water': '1 / 2: 水で満たす',
        'soil': '3: 充填水を地盤高に転換（河道のみ）',
        'spill': '越流点',
        'new_z': '新しい地盤',
        'old_z': '元の地盤',
        'water_note': '1: 海を除く陸域が対象。2: 河道セルだけが対象。\n残留水深が初期水深になる（既存の水深は置換）。',
        'soil_note': '河道で z ← z + h、h ← 0。\n水として残さず、河床を持ち上げる。',
        'order': '設定順: f_htype → f_fill_depres（> 0）→ h0_rw の加算（> 0、河道のみ）',
        'foot': '水位 E・e0 は z と同じ標高基準。模式断面であり、計算結果ではない。',
    },
    'en': {
        'a': '(a) Specify water depth',
        'a_sub': 'Shown: f_htype = 0 (uniform depth h0)',
        'b': '(b) Specify water level',
        'b_sub': 'Shown: f_htype = 2 (constant level e0)',
        'h': 'h = h0',
        'rw': 'Incised channel: + h0_rw',
        'z': 'Ground z',
        'e': 'Surface level e0',
        'dry': 'z ≥ e0: dry',
        'a_note': 'f_htype = 1: h = max(H, 0)\nH is the depth in fn_hinit; it need not be uniform.',
        'b_note': 'f_htype = 3: h = max(E − z, 0)\nE is the level in fn_hinit; it need not be horizontal.',
        'b_formula': 'h = max(e0 − z, 0)',
        'c': '(c) Fill depressions: f_fill_depres',
        'c_sub': 'The same channel hollow in both views, before adding h0_rw.',
        'water': '1 / 2: Fill with water',
        'soil': '3: Convert fill water to bed elevation (channels only)',
        'spill': 'Spill point',
        'new_z': 'Raised bed',
        'old_z': 'Original bed',
        'water_note': '1: land cells, excluding sea. 2: channel cells only.\nRetained depth replaces the initial depth on target cells.',
        'soil_note': 'On channels: z ← z + h, h ← 0.\nRaise the bed instead of retaining water.',
        'order': 'Order: f_htype → f_fill_depres (> 0) → add h0_rw (> 0, channels only)',
        'foot': 'E and e0 use the same elevation datum as z. Schematic sections, not simulation results.',
    },
}


def terrain(x):
    """Original illustrative terrain, retained for the depth/level comparison."""
    return 1.0 + .55*np.sin(.75*x+.6) + .25*np.cos(2*x) + .05*x


def depth_profile():
    """An incised channel with its final surface just below neighbouring water.

    Duplicate x coordinates at the banks preserve vertical terrain steps.
    This incision represents the supplied terrain; h0_rw only adds water.
    """
    masks = (X <= CHANNEL[0], (X >= CHANNEL[0]) & (X <= CHANNEL[1]),
             X >= CHANNEL[1])
    beds = [np.column_stack((X[m], terrain(X[m]))) for m in masks]
    beds[1][:, 1] -= CHANNEL_CUT
    surfaces = [b + [0, H0 + (H0_RW if i == 1 else 0)]
                for i, b in enumerate(beds)]
    channel = beds[1]
    increment = np.column_stack((channel[:, 0], channel[:, 1]+H0,
                                  channel[:, 1]+H0+H0_RW))
    return np.vstack(beds), np.vstack(surfaces), increment


def level_regions():
    return wet_profile(X, terrain(X), E0)


def pit_region():
    # The downstream slope is not flooded. Fill stops at the local sill.
    parts = wet_profile(PIT_X, PIT_Z, SPILL_LEVEL, xmax=SPILL_X)
    if len(parts) != 1:
        raise ValueError('The illustrated channel must contain one hollow.')
    return parts[0]


def axes(fig, box, xlim, ylim):
    left, top, width, height = box
    ax = fig.add_axes([left/CANVAS[0], (CANVAS[1]-top-height)/CANVAS[1],
                       width/CANVAS[0], height/CANVAS[1]])
    ax.set(xlim=xlim, ylim=ylim)
    ax.axis('off')
    return ax


def leader(ax, points, color):
    return line(ax, points, color, lw=.85, z=12)


def fill_region(ax, bed, level, soil=False):
    verts = np.vstack((bed, [bed[-1, 0], level], [bed[0, 0], level]))
    p = Polygon(verts, closed=True, facecolor=C_SOIL if soil else C_WATER_L,
                edgecolor=C_GROUND if soil else 'none', linewidth=0,
                hatch='///' if soil else None, zorder=3)
    ax.add_patch(p)
    line(ax, [(bed[0, 0], level), (bed[-1, 0], level)],
         C_GROUND if soil else C_WATER, lw=1.6, z=7)
    return p


def panel_a(ax, t):
    bed, surface, increment = depth_profile()
    ground(ax, bed[:, 0], bed[:, 1], -.35, C_GROUND_L, C_GROUND)
    verts = np.vstack((bed, surface[::-1]))
    ax.add_patch(Polygon(verts, closed=True, fc=C_WATER_L, ec='none', zorder=3))
    # The dashed channel surface is the state before adding h0_rw.
    line(ax, increment[:, :2], C_WATER, .9, ls='--')
    poly = np.vstack((increment[:, :2], increment[::-1][:, (0, 2)]))
    ax.add_patch(Polygon(poly, closed=True, fc='#90b8e9', ec='none', zorder=4))
    # Small downward water-surface steps mark the initial cell-wise levels.
    line(ax, surface, C_WATER, 1.5)
    text(ax, .15, 3.45, t['h'], size=9.2, color=C_WATER)
    leader(ax, [(.9, 3.05), (2.2, np.interp(2.2, X, terrain(X))+H0)], C_WATER)
    text(ax, 5.3, 3.45, t['rw'], size=9.2, color=C_WATER)
    leader(ax, [(6.4, 3.05), (6.6, np.interp(6.6, increment[:, 0], increment[:, 2]))], C_WATER)
    text(ax, 9.8, -.02, t['z'], size=8.7, ha='right', color=C_GROUND)


def panel_b(ax, t):
    z = terrain(X)
    ground(ax, X, z, -.35, C_GROUND_L, C_GROUND)
    for bed in level_regions():
        fill_region(ax, bed, E0)
    # A level marker outside the terrain is not a water line through dry land.
    text(ax, .15, 3.45, t['e'], size=9.2, color=C_WATER)
    leader(ax, [(1.65, 3.05), (4.6, E0)], C_WATER)
    text(ax, 7.4, 3.45, t['dry'], size=9.2, color=C_GROUND)
    leader(ax, [(8.5, 3.05), (9.3, np.interp(9.3, X, z))], C_GROUND)
    text(ax, 4.95, 2.0, t['b_formula'], size=8.6, color=C_WATER, ha='center')
    text(ax, 9.8, -.02, t['z'], size=8.7, ha='right', color=C_GROUND)


def panel_c(ax, t, soil=False):
    bed = pit_region()
    # In the soil case the visible solid boundary is the raised surface.
    if soil:
        # Insert the interpolated left contact into the ground polygon too.
        xx = np.unique(np.r_[PIT_X, bed[0, 0]])
        zz = np.interp(xx, PIT_X, PIT_Z)
        zz[(xx >= bed[0, 0]) & (xx <= bed[-1, 0])] = SPILL_LEVEL
        ground(ax, xx, zz, -.35, C_GROUND_L, C_GROUND)
    else:
        ground(ax, PIT_X, PIT_Z, -.35, C_GROUND_L, C_GROUND)
    fill_region(ax, bed, SPILL_LEVEL, soil=soil)
    if soil:
        line(ax, bed, C_GROUND, .95, ls='--', z=8)
        text(ax, 3.2, 2.35, t['new_z'], size=9.0, color=C_GROUND, ha='center')
        text(ax, 3.1, .17, t['old_z'], size=8.6, color=C_GROUND, ha='center')
    text(ax, 8.0, 2.9, t['spill'], size=9, color=MUTED, ha='center')
    leader(ax, [(8.0, 2.48), (SPILL_X, SPILL_LEVEL)], MUTED)
    ax.plot(SPILL_X, SPILL_LEVEL, 'o', color=C_GROUND, ms=3.1, zorder=9)


def build(lang):
    t = T[lang]
    fig = plt.figure(figsize=(CANVAS[0]/DPI, CANVAS[1]/DPI), dpi=DPI)
    page = axes(fig, (0, 0, *CANVAS), (0, CANVAS[0]), (CANVAS[1], 0))
    for left, title, sub in [(30, 'a', 'a_sub'), (815, 'b', 'b_sub')]:
        text(page, left, 22, t[title], size=11.8, weight='bold')
        text(page, left, 69, t[sub], size=9.5, color=MUTED)
    a = axes(fig, (45, 122, 690, 315), (0, 10), (-.4, 3.65))
    b = axes(fig, (830, 122, 690, 315), (0, 10), (-.4, 3.65))
    panel_a(a, t)
    panel_b(b, t)
    text(page, 30, 461, t['a_note'], size=9.0)
    text(page, 815, 461, t['b_note'], size=9.0)
    line(page, [(30, 546), (1545, 546)], RULE, .9)
    text(page, 30, 570, t['c'], size=11.8, weight='bold')
    text(page, 30, 613, t['c_sub'], size=9.0, color=MUTED)
    text(page, 30, 662, t['water'], size=10, color=C_WATER, weight='bold')
    text(page, 815, 662, t['soil'], size=9.5, color=C_GROUND, weight='bold')
    c1 = axes(fig, (45, 713, 690, 205), (0, 10), (-.4, 3.1))
    c2 = axes(fig, (830, 713, 690, 205), (0, 10), (-.4, 3.1))
    panel_c(c1, t)
    panel_c(c2, t, soil=True)
    text(page, 30, 939, t['water_note'], size=8.6)
    text(page, 815, 939, t['soil_note'], size=8.6)
    line(page, [(30, 1021), (1545, 1021)], RULE, .9)
    text(page, 30, 1040, t['order'], size=9.2, weight='bold')
    text(page, 30, 1080, t['foot'], size=8.0, color=MUTED)
    return fig


def draw(lang):
    if lang not in T:
        raise ValueError('lang must be ja or en')
    png = Path(out_path('initial_htype', lang))
    with drawing_style():
        fig = build(lang)
        try:
            fig.savefig(png, dpi=DPI)
            svg = StringIO()
            fig.savefig(svg, format='svg', metadata={'Date': None,
                'Description': 'ENCflow initial depth, level and depression filling. Schematic.'})
            clean = '\n'.join(s.rstrip() for s in svg.getvalue().splitlines())+'\n'
            png.with_suffix('.svg').write_text(clean, encoding='utf-8', newline='\n')
        finally:
            plt.close(fig)
    return str(png)
