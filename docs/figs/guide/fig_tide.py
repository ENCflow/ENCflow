"""Tide boundary sections; the published time-series panel stays unchanged.

Panel (a), including its title, axes and notes, is a lossless crop from
f17ccad218822b7f19a776f4647f3ed84e6e34f6 at its original pixel position.
Only (b)/(c) are drawn. They are illustrative, not computed A/B snapshots.
See m_tide.f90 for the forced sea-column representation.
"""
from pathlib import Path as FilePath
from io import BytesIO, StringIO
import base64
import hashlib
import numpy as np
from PIL import Image
from _style import (plt, Rectangle, Polygon, FIGS, out_path, C_WATER, C_WATER_L,
                    C_GROUND, C_GROUND_L, C_SEA, C_X, C_G)
from _schematic import drawing_style, text, block, line, arrow, curve, INK, MUTED, RULE

CANVAS = (1575, 930)
DPI = 150
SERIES_BOX = (0, 0, 650, 930)
SERIES_SHA256 = {
    'ja': 'd005ae7b5950070b4c4dce2dfabdaedac14e876b053c8fe3b4c44df55a1c9210',
    'en': '14d2987fa838ef744c0ae265a9f6c15bf8d357336bb50637e243894a740765e4',
}
HSEA = 1.0
SEA_EDGE = 4.0
ETA_A, ETA_B = .8, -.8  # unchanged A/B values in the preserved time series
POND_LEVEL = .26
LAND_X = np.linspace(SEA_EDGE, 12.0, 1601)
SECTION_BOXES = [(684, 98, 866, 255), (684, 545, 866, 255)]

T = {
    'ja': {
        'b': '(b) 高潮位（時刻 A）: 海から陸への浸水',
        'c': '(c) 低潮位（時刻 B）: 排水と低地の滞留',
        'sea': '海セル: 水位を強制',
        'land': '陸セル: 水深・流れを計算',
        'flood': '浸水',
        'front': '浸水前縁',
        'drain': '海へ排水',
        'ridge': '地形の高まり',
        'pond': '低地に残る水',
        'ground': '地盤 z',
        'base': '計算上の z = η − hsea0',
        'sea_note': 'h = hsea0（一定）、水面は η(t)。\n水柱の底は実際の海底ではない。',
        'flux_note': '海陸境界の流量は通常のエッジ計算。\n陸側の水面と地盤の交点が浸水前縁。',
        'drain_note': '海へ通じる流路がある水は、\n条件に応じて排水される。',
        'pond_note': '高まりで隔てられた低地には水が残り得る。\n潮位の低下だけで全域が排水されるわけではない。',
        'note': '断面・陸側の水面・矢印は模式図（A/Bの数値計算結果ではない）。',
    },
    'en': {
        'b': '(b) High tide (time A): flooding from sea to land',
        'c': '(c) Low tide (time B): drainage and retained water',
        'sea': 'Sea cells: prescribed level',
        'land': 'Land cells: solve depth and flow',
        'flood': 'Flooding',
        'front': 'Wetting front',
        'drain': 'Drainage to sea',
        'ridge': 'Topographic rise',
        'pond': 'Water retained in a hollow',
        'ground': 'Ground z',
        'base': 'Computational z = η − hsea0',
        'sea_note': 'h = hsea0 (constant); surface η(t).\nColumn base is not the physical seabed.',
        'flux_note': 'Sea–land flux uses the usual edge calculation.\nThe land surface and water surface meet at the front.',
        'drain_note': 'Water with a route to the sea can drain\nwhen the hydraulic conditions allow it.',
        'pond_note': 'A rise can retain water in a low-lying hollow.\nLowering the tide need not drain all flooded land.',
        'note': 'Sections, land-side water surfaces and arrows are schematic, not computed A/B snapshots.',
    },
}


def land_z(x):
    """Shared smooth land profile: coastal rise and inland hollow."""
    x = np.asarray(x)
    return (.3 + .25*np.exp(-((x-5)/.5)**2)
            - .2*np.exp(-((x-8.5)/1.6)**2) + .06*np.maximum(x-10.5, 0)**2)


def flood_surface(x):
    """Smooth illustrative surface, clipped at its intersection with land."""
    return ETA_A - .04*np.maximum(np.asarray(x)-5.5, 0)**2


def wet_regions(x, bed, surface):
    """Clip sampled profiles at shared linear intersections.

    Each returned Nx3 array is (x, ground, water surface). Endpoints are exact
    intersections except at open domain boundaries. No negative-depth fill.
    """
    x, bed, surface = (np.asarray(v, float) for v in (x, bed, surface))
    if x.ndim != 1 or len(x) < 2 or bed.shape != x.shape or surface.shape != x.shape:
        raise ValueError('Profiles must be equal-length 1D arrays')
    if np.any(np.diff(x) <= 0) or not np.all(np.isfinite([x, bed, surface])):
        raise ValueError('Profiles must be finite, with increasing x')
    points = []
    depth = surface-bed
    for i in range(len(x)-1):
        points.append((x[i], bed[i], surface[i]))
        if depth[i]*depth[i+1] < 0:
            f = depth[i]/(depth[i]-depth[i+1])
            xx = x[i]+f*(x[i+1]-x[i])
            zz = bed[i]+f*(bed[i+1]-bed[i])
            points.append((xx, zz, zz))
    points.append((x[-1], bed[-1], surface[-1]))
    regions, part = [], []
    for a, b in zip(points[:-1], points[1:]):
        if (a[2]-a[1])+(b[2]-b[1]) > 1e-12:
            if not part:
                part.append(a)
            part.append(b)
        elif part:
            regions.append(np.array(part)); part = []
    if part:
        regions.append(np.array(part))
    return regions


def geometry(mode):
    z = land_z(LAND_X)
    if mode == 'flood':
        return wet_regions(LAND_X, z, flood_surface(LAND_X))
    if mode == 'drain':
        # Seaward residual film and inland pond separated by a dry rise.
        coast = LAND_X <= 5.0
        u = (LAND_X[coast]-SEA_EDGE)/(5.0-SEA_EDGE)
        film = .13*(1-3*u*u+2*u*u*u)
        coastal = wet_regions(LAND_X[coast], z[coast], z[coast]+film)
        pond = wet_regions(LAND_X, z, np.full_like(z, POND_LEVEL))
        return coastal+pond
    raise ValueError('mode must be flood or drain')


def _axes(fig, box, xlim, ylim):
    left, top, width, height = box
    ax = fig.add_axes([left/CANVAS[0], (CANVAS[1]-top-height)/CANVAS[1],
                       width/CANVAS[0], height/CANVAS[1]])
    ax.set(xlim=xlim, ylim=ylim)
    ax.axis('off')
    return ax


def section(ax, lang, mode):
    t = T[lang]
    eta = ETA_A if mode == 'flood' else ETA_B
    regions = geometry(mode)
    x = np.unique(np.r_[LAND_X, np.concatenate([r[:, 0] for r in regions])])
    z = np.interp(x, LAND_X, land_z(LAND_X))
    ax.add_patch(Polygon(np.r_[np.c_[x, z], [[12, -1.96], [4, -1.96]]],
                         fc=C_GROUND_L, ec='none', zorder=1))
    # Neutral field below the computational column, not a physical seabed.
    ax.add_patch(Rectangle((0, -1.96), SEA_EDGE, eta-HSEA+1.96,
                           fc='#f1f0ec', ec='none', zorder=1))
    ax.add_patch(Rectangle((0, eta-HSEA), SEA_EDGE, HSEA,
                           fc=C_SEA, alpha=.85, ec='none', zorder=2))
    for xx in (1, 2, 3):
        line(ax, [(xx, eta-HSEA), (xx, eta)], 'white', .65, z=3)
    line(ax, [(0, eta), (4, eta)], C_WATER, 1.5, z=5)
    line(ax, [(0, eta-HSEA), (4, eta-HSEA)], MUTED, .95, ls='--', z=5)
    line(ax, [(4, -1.96), (4, z[0])], C_GROUND, .9, z=5)
    for region in regions:
        xx, bottom, top = region.T
        polygon = np.r_[np.c_[xx, bottom], np.c_[xx[::-1], top[::-1]]]
        ax.add_patch(Polygon(polygon, closed=True, fc=C_WATER_L, ec='none', zorder=3))
        line(ax, np.c_[xx, top], C_WATER, 1.25, z=6)
    line(ax, np.c_[x, z], C_GROUND, 1.35, z=7)
    from matplotlib.patches import FancyArrowPatch
    ax.add_patch(FancyArrowPatch((3.0, eta-HSEA), (3.0, eta), arrowstyle='<->',
                 color=INK, lw=1, mutation_scale=10, shrinkA=0, shrinkB=0, zorder=10))
    text(ax, 2.82, eta-.5, 'hsea0', size=8.5, ha='right', va='center')
    text(ax, .08, eta+.37, f'η = {eta:+.1f} m', size=8.5, color=C_WATER)
    text(ax, .08, eta-HSEA-.11, t['base'], size=7.6, color=MUTED)
    text(ax, 11.75, -.14, t['ground'], size=8.2, color=C_GROUND, ha='right')
    if mode == 'flood':
        arrow(ax, curve((4.68, 1.05), [('C', (5.35, 1.05), (6.35, .97), (7.28, .84))]), C_X, 1.7)
        text(ax, 5.95, 1.43, t['flood'], size=8.7, ha='center', color=C_X)
        front = regions[0][-1]
        text(ax, 10.35, .88, t['front'], size=8.3, ha='center', color=C_WATER)
        line(ax, [(10.13, .60), (front[0], front[1]+.015)], MUTED, .75, z=9)
    else:
        arrow(ax, curve((4.75, .79), [
            ('C', (4.34, .79), (3.88, .71), (3.78, .30)),
            ('C', (3.68, -.12), (3.30, -.48), (2.96, -.62))]), C_G, 1.8)
        text(ax, .08, 1.30, t['drain'], size=8.5, color='#477a32')
        text(ax, 5.80, 1.44, t['ridge'], size=8.3, color=C_GROUND, ha='center')
        line(ax, [(5.7, 1.09), (5.12, float(land_z(5.12))+.025)], MUTED, .75, z=9)
        text(ax, 9.1, .89, t['pond'], size=8.3, color=C_WATER, ha='center')
        line(ax, [(9.1, .60), (9.1, POND_LEVEL+.02)], MUTED, .75, z=9)
    return regions


def build(lang):
    """Draw only vectors on the right, leaving the protected strip blank."""
    if lang not in T:
        raise ValueError('lang must be ja or en')
    t = T[lang]
    fig = plt.figure(figsize=(CANVAS[0]/DPI, CANVAS[1]/DPI), dpi=DPI)
    page = _axes(fig, (0, 0, *CANVAS), (0, CANVAS[0]), (CANVAS[1], 0))
    for top, mode, box, notes in [(20, 'flood', SECTION_BOXES[0], ('sea_note', 'flux_note')),
                                  (467, 'drain', SECTION_BOXES[1], ('drain_note', 'pond_note'))]:
        text(page, 680, top, t['b' if mode=='flood' else 'c'], size=10.1, weight='bold')
        text(page, 696, top+48, t['sea'], size=8.4, color=C_WATER)
        text(page, 1000, top+48, t['land'], size=8.4, color=C_GROUND)
        ax = _axes(fig, box, (-.15, 12.15), (-2.04, 1.58))
        section(ax, lang, mode)
        for xx, key, width in [(696, notes[0], 315), (1034, notes[1], 516)]:
            block(page, xx, top+351, t[key], width, size=8.15)
    line(page, [(680, 444), (1550, 444)], RULE, .8)
    line(page, [(680, 889), (1550, 889)], RULE, .8)
    text(page, 680, 901, t['note'], size=7.8, color=MUTED)
    return fig


def _series_asset(lang):
    suffix = '' if lang == 'ja' else '_en'
    path = FilePath(FIGS)/f'tide_series_preserved{suffix}.png'
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != SERIES_SHA256[lang]:
        raise ValueError('Protected time series differs from published crop: '+str(path))
    return data


def draw(lang):
    if lang not in T:
        raise ValueError('lang must be ja or en')
    series_bytes = _series_asset(lang)
    with Image.open(BytesIO(series_bytes)) as series:
        series.load()
        if series.size != (SERIES_BOX[2], SERIES_BOX[3]):
            raise ValueError('Protected time series has an unexpected size')
        with drawing_style():
            fig = build(lang)
            try:
                png = FilePath(out_path('tide_section', lang))
                png_buffer, svg_buffer = BytesIO(), StringIO()
                fig.savefig(png_buffer, format='png', dpi=DPI)
                fig.savefig(svg_buffer, format='svg', metadata={'Date': None,
                    'Description': 'Tide boundary schematics; time series is the unchanged published raster. Sections are not numerical results.'})
            finally:
                plt.close(fig)
        with Image.open(BytesIO(png_buffer.getvalue())) as rendered:
            combined = rendered.convert('RGBA')
        if combined.size != CANVAS:
            raise ValueError('Schematic canvas has an unexpected size')
        combined.paste(series, SERIES_BOX[:2])  # no resampling or alpha blending
        combined.save(png, dpi=(DPI, DPI))
    scale = 72/DPI
    embedded = (f'<image id="preserved-tide-series" x="0" y="0" '
                f'width="{SERIES_BOX[2]*scale:g}" height="{SERIES_BOX[3]*scale:g}" '
                f'preserveAspectRatio="none" xlink:href="data:image/png;base64,'
                +base64.b64encode(series_bytes).decode('ascii')+'"/>\n')
    svg = svg_buffer.getvalue().replace('</svg>', embedded+'</svg>')
    svg = '\n'.join(s.rstrip() for s in svg.splitlines())+'\n'
    png.with_suffix('.svg').write_text(svg, encoding='utf-8', newline='\n')
    return str(png)
