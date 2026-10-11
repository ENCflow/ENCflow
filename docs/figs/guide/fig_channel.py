"""河道の章の図: サブグリッド河道幅と σ 断面・堤防の仮想壁面(断面)、壁エッジと破堤サイト(平面)、破堤の時系列。"""
from _style import *
import numpy as np
from pathlib import Path as FilePath
from io import BytesIO, StringIO
import base64
import hashlib
from PIL import Image
from matplotlib.patches import PathPatch
from _schematic import (drawing_style, text, block, paragraph, line, curve,
                        arrow as flow_arrow, INK, MUTED, RULE)

T = {"ja": {
    "a": "(a) 断面: 河道セル 1 つ(セル幅 dx)とその両側の堤内地セル",
    "b": "(b) 平面: 壁エッジと破堤サイト",
    "c": "(c) 破堤 &list_channel_breach",
    "W": "河道セル(fn_rw)の河道幅 W(fn_width、W < dx)",
    "rest": "セル内の非河道部分は\n扱わない(状態量は河道部分のみ)",
    "wall": "堤防 = 仮想壁面(bank0 / fn_bank)\n天端 = 堤内地標高 + bank0(f_bank_datum = 1)",
    "weir": "天端を超えた分は\n本間公式の堰越流",
    "D": "D = 天端 − 河床\n(≈ bank0 + depth_rw)",
    "drw": "depth_rw",
    "sigma": "断面形 σ(h) = (h/D)^m(p_sect_m)\nm = 0 矩形(既定)、0.5 放物線的、1 三角形的\nh ≥ D では矩形に戻る",
    "land": "堤内地セル", "ch": "河道セル(fn_rw)",
    "edges": "壁エッジ = 河道セル × 堤内地セルの全エッジ(対角を含む)\n天端は河道側セルの値(fn_bank は河道セル位置に与える)",
    "site": "破堤サイト = 隣接する河道セル (ic, jc) と\n堤内地セル (il, jl) の対(エッジ 1 本)\nbr_cell(:,n) = ic, jc, il, jl",
    "xlabel": "時刻 (min)", "ylabel": "天端の残存割合 f",
    "eff": "実効天端 = 堤内地盤高\n + f × (天端 − 堤内地盤高)",
    "ws": "水位(河道部分の状態量)",
    "series": "br_series(:,k,n) = t, f",
}, "en": {
    "a": "(a) Section: one channel cell (cell width dx) and the landside cells on both sides",
    "b": "(b) Plan: wall edges and a breach site",
    "c": "(c) Breach &list_channel_breach",
    "W": "width W of the channel cell (fn_rw) (fn_width, W < dx)",
    "rest": "non-channel part of the cell is\nnot represented (state = channel part only)",
    "wall": "levee = virtual wall (bank0 / fn_bank)\ncrest = landside elevation + bank0 (f_bank_datum = 1)",
    "weir": "excess over the crest spills\nas Honma weir overtopping",
    "D": "D = crest − bed\n(≈ bank0 + depth_rw)",
    "drw": "depth_rw",
    "sigma": "section shape σ(h) = (h/D)^m (p_sect_m)\nm = 0 rectangle (default), 0.5 parabolic, 1 triangular\nback to the rectangle for h ≥ D",
    "land": "landside cells", "ch": "channel cells (fn_rw)",
    "edges": "wall edges = every edge between channel and landside cells (diagonals included)\ncrest = value of the channel-side cell (fn_bank is given at channel cells)",
    "site": "breach site = pair of adjacent channel cell (ic, jc)\nand landside cell (il, jl) (one edge)\nbr_cell(:,n) = ic, jc, il, jl",
    "xlabel": "time (min)", "ylabel": "remaining crest fraction f",
    "eff": "effective crest = landside ground\n + f × (crest − landside ground)",
    "ws": "water level (state of the channel part)",
    "series": "br_series(:,k,n) = t, f",
}}



# Fixed canvas and chart box preserve the published chart's physical placement.
CANVAS = (1575, 1080)
DPI = 150
CHART_BOX = (860, 500, 1575, 1080)  # x0, y0, x1, y1; top-left pixel coordinates
CHART_SHA256 = {
    'ja': 'eabe03245e8665217e4fcd91b6a0a21361618534b55de5b65a62c2ff16408207',
    'en': '20b6a125941f6fe6ebddbc3ff3a1190acb3b45f7e921f81b1e32b41f9945ee9a',
}
# The assets are lossless crops of channel_subgrid{,_en}.png in commit
# 251e8b575fdc1c4fdb8e9f3da5b8d37841ff6d05 (unchanged through f5cfd54).
# Titles, axes, ticks, labels, sample points and the time series remain pixels
# from that publication. Do not regenerate these assets with panel_breach.

LAND, BED, CREST, WATER = 1.0, .4, 1.5, 1.65
LEFT, RIGHT, CENTRE = 1.25, 1.75, 1.5
NX, NY, CHANNEL_ROW, BREACH_COL = 6, 5, 2, 3


def _pixel_axes(fig, left, top, width, height, xlim=(0, 1), ylim=(0, 1)):
    ax = fig.add_axes([left/CANVAS[0], (CANVAS[1]-top-height)/CANVAS[1],
                       width/CANVAS[0], height/CANVAS[1]])
    ax.set(xlim=xlim, ylim=ylim)
    ax.axis('off')
    return ax


def _dimension(ax, p, q, color=MUTED, tick=.045):
    """Dimension tips reach the shared endpoints; witness marks cross each tip."""
    p, q = np.asarray(p), np.asarray(q)
    ax.annotate('', q, p, arrowprops=dict(arrowstyle='<->', color=color,
                lw=.8, shrinkA=0, shrinkB=0, mutation_scale=8), zorder=9)
    v = q-p
    n = np.array([-v[1], v[0]])/np.linalg.norm(v)*tick
    for end in (p, q):
        line(ax, [end-n, end+n], color, .7, z=9)


def section_curve(m):
    """Exact illustrative sigma profiles, including a smooth parabolic bottom."""
    if m == .5:
        # One quadratic Bezier: z = BED + (CREST-BED)*u**2, -1 <= u <= 1.
        return curve((LEFT, CREST), [('Q', (CENTRE, 2*BED-CREST), (RIGHT, CREST))])
    if m == 1:
        return curve((LEFT, CREST), [('L', (CENTRE, BED)), ('L', (RIGHT, CREST))])
    raise ValueError('Illustrated exponents are .5 and 1')


def panel_section(ax, t):
    # One ground polygon: no independently positioned rectangles at the steps.
    ground = [(0, LAND), (1, LAND), (1, BED), (2, BED), (2, LAND), (3, LAND)]
    ax.add_patch(Polygon(ground+[(3, -.10), (0, -.10)], fc=C_GROUND_L, ec='none', zorder=1))
    line(ax, ground, C_GROUND, 1.1, z=2)
    for a, b in ((1, LEFT), (RIGHT, 2)):
        ax.add_patch(Rectangle((a, BED), b-a, LAND-BED, fc='none', ec=MUTED,
                              hatch='///', lw=0, zorder=3))
    ax.add_patch(Rectangle((LEFT, BED), RIGHT-LEFT, WATER-BED, fc=C_WATER_L, ec='none', zorder=3))
    line(ax, [(LEFT, WATER), (RIGHT, WATER)], C_WATER, 1.3)
    # Dashed extensions stop at the solid water surface (no stacked strokes).
    for a, b in ((1, LEFT), (RIGHT, 2)):
        line(ax, [(a, WATER), (b, WATER)], C_WATER, .9, ls='--')
    for side in (LEFT, RIGHT):
        line(ax, [(side, BED), (side, WATER)], C_WATER, .65, z=4)
    for m, ls in ((.5, '--'), (1., ':')):
        p = PathPatch(section_curve(m), fill=False, ec=C_WATER, lw=1.1,
                      ls=ls, joinstyle='miter', capstyle='butt', zorder=6)
        ax.add_patch(p)
    pool_end, pool_level = 2.58, LAND+.12
    ax.add_patch(Rectangle((2, LAND), pool_end-2, pool_level-LAND,
                          fc=C_WATER_L, ec='none', zorder=3))
    line(ax, [(2, pool_level), (pool_end, pool_level)], C_WATER, 1.)
    for x in (0, 1, 2, 3):
        line(ax, [(x, -.10), (x, 2.27)], RULE, .65, z=0)
    for x in (1, 2):
        # Virtual walls are sharp vertical segments, not rounded embankments.
        ax.plot([x, x], [BED, CREST], color=C_X, lw=3.4,
                solid_capstyle='butt', zorder=8)
    flow_arrow(ax, curve((2, CREST+.08), [
        ('C', (2.16, CREST+.08), (2.30, pool_level+.045), (2.52, pool_level+.045))]),
        C_X, 1.6, size=10)
    _dimension(ax, (1, 2.12), (2, 2.12))
    text(ax, CENTRE, 2.17, 'dx', size=9, color=MUTED, ha='center', va='bottom')
    _dimension(ax, (LEFT, .22), (RIGHT, .22), C_C)
    text(ax, CENTRE, .17, 'W', size=9, color=C_C, ha='center')
    for x in (LEFT, RIGHT):
        line(ax, [(x, .18), (x, BED)], C_C, .6, z=7)
    _dimension(ax, (.86, BED), (.86, CREST), INK)
    text(ax, .78, LAND+.18, 'D', size=9.4, color=INK, ha='right', va='center')
    for z in (BED, CREST):
        line(ax, [(.81, z), (1, z)], MUTED, .55)
    _dimension(ax, (2.13, BED), (2.13, LAND), C_GROUND)
    text(ax, 2.23, (BED+LAND)/2, t['drw'], size=8.6, color=C_GROUND, va='center')
    for z in (BED, LAND):
        line(ax, [(2, z), (2.18, z)], C_GROUND, .55)
    text(ax, .42, LAND+.11, t['land'], size=8.5, color=C_GROUND, ha='center', va='bottom')
    text(ax, 2.68, LAND+.30, t['land'], size=8.5, color=C_GROUND, ha='center', va='bottom')
    water_label = t['ws'].replace(' (', '\n(')
    text(ax, CENTRE, WATER+(.05 if '\n' in water_label else .11), water_label,
         size=8.3, color=C_WATER, ha='center', va='bottom')


def diagonal_edges():
    """One segment for each valid channel-to-landside diagonal adjacency."""
    edges = []
    for i in range(NX):
        for dx in (-1, 1):
            if 0 <= i+dx < NX:
                for dy in (-1, 1):
                    start = np.array([i+.5, CHANNEL_ROW+.5])
                    step = np.array([dx, dy])
                    edges.append((start, start+step))
    return edges


def panel_plan(ax, t):
    ax.set_aspect('equal')
    ax.add_patch(Rectangle((0, CHANNEL_ROW), NX, 1, fc='#eaf2fc', ec='none', zorder=1))
    ax.add_patch(Rectangle((BREACH_COL, CHANNEL_ROW+1), 1, 1,
                          fc=C_WATER_L, ec='none', zorder=1))
    grid(ax, 0, 0, NX, NY, 1, RULE, .65, z=2)
    for start, end in diagonal_edges():
        # Two equal dashes leave a clear gap at the shared corner/normal wall.
        d = end-start
        for lo, hi in ((.22, .43), (.57, .78)):
            a, b = start+lo*d, start+hi*d
            ax.plot([a[0], b[0]], [a[1], b[1]], color=C_X, lw=1.15,
                    solid_capstyle='butt', zorder=4)
    # The top normal wall is split at the breach rather than painted over.
    for p, q in [((0, CHANNEL_ROW), (NX, CHANNEL_ROW)),
                 ((0, CHANNEL_ROW+1), (BREACH_COL, CHANNEL_ROW+1)),
                 ((BREACH_COL+1, CHANNEL_ROW+1), (NX, CHANNEL_ROW+1))]:
        ax.plot([p[0], q[0]], [p[1], q[1]], color=C_X, lw=2.8,
                solid_capstyle='butt', zorder=5)
    line(ax, [(BREACH_COL, CHANNEL_ROW+1), (BREACH_COL+1, CHANNEL_ROW+1)],
         C_X, 1.0, ls=':', z=6)
    cy = CHANNEL_ROW+.5
    for lo, hi in ((.25, 2.75), (4.20, 5.75)):
        flow_arrow(ax, [(lo, cy), (hi, cy)], C_C, 1.35, size=9)
    cx = BREACH_COL+.5
    flow_arrow(ax, [(cx, cy+.13), (cx, cy+.90)], C_X, 1.8, size=11)
    for y in (cy, cy+1):
        ax.add_patch(Circle((cx, y), .065, fc='white', ec=C_X, lw=.9, zorder=8))
    # Keep the source-cell label clear of all four diagonal wall markers.
    line(ax, [(cx, cy), (4.48, 1.35), (6.10, 1.35)], MUTED, .65, z=3)
    text(ax, 6.32, 1.35, '(ic, jc)', size=8.4, va='center')
    text(ax, cx, CHANNEL_ROW+1.93, '(il, jl)', size=8.4, ha='center')
    text(ax, 6.32, 4.58, t['land'], size=8.8, color=C_GROUND, va='center')
    text(ax, 6.32, cy, t['ch'], size=8.8, color=C_C, va='center')
    text(ax, 6.32, .48, t['land'], size=8.8, color=C_GROUND, va='center')


# Original chart code retained verbatim as reference; draw() uses frozen pixels.
def panel_breach(ax, t):
    ts = [0, 60, 70, 90, 110]; fs = [1.0, 1.0, 0.2, 0.0, 0.0]
    ax.plot(ts, fs, color=C_X, lw=2.0)
    ax.plot(ts[:4], fs[:4], "o", color=C_X, ms=6)
    ax.set_ylim(-0.08, 1.2); ax.set_xlim(0, 110)
    ax.set_xlabel(t["xlabel"]); ax.set_ylabel(t["ylabel"])
    ax.text(2, 1.1, t["series"], fontsize=8.5, color=C_X, ha="left", va="center")
    ax.text(3, 0.4, t["eff"], fontsize=8.5, color="k", ha="left", va="center")
    ax.set_title(t["c"], loc="left", fontsize=9.5)



def build(lang):
    """Build only panels (a)/(b); the protected chart region stays blank."""
    if lang not in T:
        raise ValueError('lang must be ja or en')
    t = T[lang]
    fig = plt.figure(figsize=(CANVAS[0]/DPI, CANVAS[1]/DPI), dpi=DPI)
    heading = _pixel_axes(fig, 35, 17, 1505, 35)
    block(heading, 0, 1, t['a'], 1, size=10.2, weight='bold')
    section = _pixel_axes(fig, 35, 90, 875, 300, (-.15, 3.35), (-.10, 2.38))
    panel_section(section, t)
    section_note = _pixel_axes(fig, 940, 75, 600, 405)
    y = 1
    for key, col in [('wall', C_X), ('weir', C_X), ('D', INK), ('sigma', C_WATER)]:
        y = paragraph(section_note, 0, y, t[key], 1, size=8.5, color=col, gap=.045)
    foot = _pixel_axes(fig, 35, 408, 865, 75)
    text(foot, .5, 1, t['W']+'\n'+t['rest'], size=8.5, color=C_C, ha='center')
    heading_b = _pixel_axes(fig, 35, 517, 790, 35)
    block(heading_b, 0, 1, t['b'], 1, size=10.2, weight='bold')
    plan = _pixel_axes(fig, 35, 560, 790, 300, (-.3, 12.3), (-.15, 5.15))
    panel_plan(plan, t)
    notes = _pixel_axes(fig, 35, 881, 790, 180)
    y = paragraph(notes, 0, 1, t['edges'], 1, size=8.4, color=C_X, gap=.085)
    paragraph(notes, 0, y, t['site'], 1, size=8.4, gap=.02)
    return fig


def _chart_asset(lang):
    suffix = '' if lang == 'ja' else '_en'
    path = FilePath(FIGS)/f'channel_breach_preserved{suffix}.png'
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != CHART_SHA256[lang]:
        raise ValueError('Protected breach chart differs from the published crop: '+str(path))
    return data


def draw(lang):
    if lang not in T:
        raise ValueError('lang must be ja or en')
    chart_bytes = _chart_asset(lang)
    with Image.open(BytesIO(chart_bytes)) as chart:
        chart.load()
        if chart.size != (CHART_BOX[2]-CHART_BOX[0], CHART_BOX[3]-CHART_BOX[1]):
            raise ValueError('Protected chart has an unexpected size')
        with drawing_style():
            fig = build(lang)
            try:
                png = FilePath(out_path('channel_subgrid', lang))
                png_buffer = BytesIO()
                fig.savefig(png_buffer, format='png', dpi=DPI)
                svg_buffer = StringIO()
                fig.savefig(svg_buffer, format='svg', metadata={'Date': None,
                    'Description': 'ENCflow channel schematics; breach chart is the unchanged published raster.'})
            finally:
                plt.close(fig)
        # No interpolation, scaling, alpha compositing or chart redraw.
        with Image.open(BytesIO(png_buffer.getvalue())) as rendered:
            combined = rendered.convert('RGBA')
        if combined.size != CANVAS:
            raise ValueError('Schematic canvas has an unexpected size')
        combined.paste(chart, CHART_BOX[:2])
        combined.save(png, dpi=(DPI, DPI))
    # The SVG's schematic panels are vectors; its only raster is the same crop.
    # Points = pixels * 72 / DPI. It occupies exactly the original chart box.
    scale = 72/DPI
    x0, y0, x1, y1 = CHART_BOX
    embedded = (f'<image id="preserved-breach-chart" x="{x0*scale:g}" y="{y0*scale:g}" '
                f'width="{(x1-x0)*scale:g}" height="{(y1-y0)*scale:g}" '
                f'preserveAspectRatio="none" xlink:href="data:image/png;base64,'
                +base64.b64encode(chart_bytes).decode('ascii')+'"/>\n')
    svg = svg_buffer.getvalue().replace('</svg>', embedded+'</svg>')
    png.with_suffix('.svg').write_text(svg, encoding='utf-8', newline='\n')
    return str(png)
