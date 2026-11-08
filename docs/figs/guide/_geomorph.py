"""Shared canvas, palette and export for the geomorph mechanism figures (fig_geomorph_*.py).

Same conventions as fig_geomorph.py and fig_geomorph_morfac.py: a pixel canvas
(x right, y down), the _schematic text helpers (renderer-measured wrapping) and
the geomorph palette. Every figure is an explanatory schematic, not solver
output; curves drawn on small charts are the closed-form expressions quoted in
docs/users_guide/geomorph.md, evaluated for illustrative parameter values.
Matplotlib and NumPy only (outside the computational core, policy 10).
"""
from io import StringIO
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle, Polygon, Circle, FancyArrowPatch
import re
from matplotlib.font_manager import FontProperties
from _schematic import drawing_style, text, block, line, arrow, INK, MUTED, RULE

DPI = 150
WIDTH = 1575
# Palette shared with fig_geomorph.py (materials) and the morfac figure (accents).
SOIL, ROCK, WATER = '#dfc58e', '#d4d1c9', '#d7eaf5'
BLUE, SED, MOVING, GREEN = '#287ca5', '#ad5b29', '#da9760', '#52744b'
TALUS, PANEL, SKY = '#b98d5f', '#f4f3ee', '#eef5fa'
ORANGE = '#eb6834'


# Line-breaking rules for kblock: no line starts with a closing mark, no line ends with an opening one.
CLOSE = set('。、,.)）」』]】:;!?%・…')
OPEN = set('(（「『[【')
NBSP = '\u00a0'
# Formulas stay on one line: spaces around binary operators become no-break spaces, and runs joined by them are one token.
GLUE = re.compile(r' ([=+−/×<>≤≥∝]) ')
_F = r'(?:[^\s\u3000-\u30ff\u3400-\u9fff\uff00-\uffef]|\u00a0)'   # formula characters (no CJK, no full-width)
TOKEN = re.compile(_F + r'*\u00a0' + _F + r'*'
                   r'|[0-9]+(?:[.][0-9]+)?(?:[-–][0-9]+(?:[.][0-9]+)?)?|[A-Za-z_][A-Za-z0-9_]*(?:=[0-9.]+)?|\s+|.')


def kwrap(ax, s, width, size=9, weight='normal'):
    """Like _schematic.wrap (renderer-measured), with the two line-breaking rules above."""
    renderer = ax.figure.canvas.get_renderer()
    px = abs(ax.transData.transform((width, 0))[0] - ax.transData.transform((0, 0))[0])
    fp = FontProperties(family=matplotlib.rcParams['font.family'], size=size, weight=weight)

    def fits(t):
        return renderer.get_text_width_height_descent(t, fp, False)[0] <= px
    lines = []
    for par in s.split('\n'):
        if not par:
            lines.append(''); continue
        par = GLUE.sub(NBSP + r'\1' + NBSP, par)
        cur = ''
        for tok in TOKEN.findall(par):
            cand = cur + tok
            if not cur or fits(cand) or tok in CLOSE:
                cur = cand
                continue
            if not tok.strip():
                lines.append(cur.rstrip()); cur = ''
                continue
            head, carry = cur.rstrip(), ''
            while head and head[-1] in OPEN:
                carry, head = head[-1] + carry, head[:-1]
            if head:
                lines.append(head.rstrip()); cur = carry + tok
            else:
                cur = cand
        lines.append(cur.rstrip())
    return '\n'.join(lines)


def kblock(ax, x, y, s, width, size=8.3, color=INK, weight='normal'):
    return text(ax, x, y, kwrap(ax, s, width, size, weight), size=size, color=color, weight=weight)


def canvas(height, width=WIDTH):
    fig = plt.figure(figsize=(width / DPI, height / DPI), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set(xlim=(0, width), ylim=(height, 0))
    ax.axis('off')
    return fig, ax


def header(ax, title, sub, x=35):
    text(ax, x, 22, title, size=12, weight='bold')
    text(ax, x, 66, sub, size=8.8, color=MUTED)


def panel(ax, x, y, s, size=10):
    return text(ax, x, y, s, size=size, weight='bold')


def rule(ax, x0, x1, y):
    line(ax, [(x0, y), (x1, y)], RULE, .8)


def box(ax, x, y, w, h, face=PANEL, edge='none', lw=.8, z=0, **kw):
    p = Rectangle((x, y), w, h, facecolor=face, edgecolor=edge, linewidth=lw, zorder=z, **kw)
    ax.add_patch(p)
    return p


def poly(ax, pts, face, edge='none', lw=.8, z=2, **kw):
    p = Polygon(np.asarray(pts, float), closed=True, facecolor=face, edgecolor=edge,
                linewidth=lw, zorder=z, **kw)
    ax.add_patch(p)
    return p


def dim(ax, a, b, label=None, color=MUTED, size=8.4, offset=(0, 0), ha='center', va='center', lw=.9):
    """Two-headed dimension arrow with an optional label at its midpoint (+ offset)."""
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle='<->', mutation_scale=8, color=color, lw=lw,
                                 shrinkA=0, shrinkB=0, zorder=12))
    if label:
        mx, my = (a[0] + b[0]) / 2 + offset[0], (a[1] + b[1]) / 2 + offset[1]
        text(ax, mx, my, label, size=size, color=color, ha=ha, va=va)


def badge(ax, cx, cy, s, r=14, size=8.6, color=INK):
    ax.add_patch(Circle((cx, cy), r, facecolor='white', edgecolor=color, linewidth=.9, zorder=15))
    text(ax, cx, cy, s, size=size, weight='bold', ha='center', va='center', color=color)


def cross(ax, cx, cy, r=7, color=ORANGE, lw=1.6):
    line(ax, [(cx - r, cy - r), (cx + r, cy + r)], color, lw, z=14)
    line(ax, [(cx - r, cy + r), (cx + r, cy - r)], color, lw, z=14)


def columns(ax, x0, w, base, tops, face=SOIL, edge='#9d8a63', lw=.7, z=3):
    """Raster cells as columns: cell k spans [x0 + k w, x0 + (k+1) w] from y = base up to tops[k]."""
    for k, top in enumerate(tops):
        if top < base:
            box(ax, x0 + k * w, top, w, base - top, face=face, edge=edge, lw=lw, z=z)


def wet_px(xs, ys, level):
    """Water polygons over a piecewise-linear bed in pixel space (wet where y > level).

    Shore crossings are inserted exactly, so the water fill, the free-surface
    segment and the bed share vertices. Returns a list of (N, 2) arrays.
    """
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    pieces, part = [], []
    for a, b, ya, yb in zip(xs[:-1], xs[1:], ys[:-1], ys[1:]):
        if ya <= level and yb <= level:
            if part:
                pieces.append(part); part = []
            continue
        pa, pb = (a, ya), (b, yb)
        if ya < level:
            pa = (a + (level - ya) * (b - a) / (yb - ya), level)
        if yb < level:
            pb = (a + (level - ya) * (b - a) / (yb - ya), level)
        if not part:
            part = [pa]
        part.append(pb)
        if yb < level:
            pieces.append(part); part = []
    if part:
        pieces.append(part)
    out = []
    for bed in pieces:
        bed = np.asarray(bed)
        out.append(np.vstack([bed, [bed[-1, 0], level], [bed[0, 0], level]]))
    return out


def water_px(ax, xs, ys, level, face=WATER, edge=BLUE, z=3):
    polys = wet_px(xs, ys, level)
    for p in polys:
        poly(ax, p, face, z=z)
        line(ax, [(p[0, 0], level), (p[-3, 0], level)], edge, 1.2, z=z + 1)
    return polys


def ground_px(ax, xs, ys, base, face=SOIL, edge=INK, lw=1.1, z=2):
    pts = list(zip(xs, ys)) + [(xs[-1], base), (xs[0], base)]
    poly(ax, pts, face, z=z)
    line(ax, list(zip(xs, ys)), edge, lw, z=z + 4)


def chart(fig, x, y, w, h, xlim, ylim, xlabel=None, ylabel=None, size=8.4):
    """Numerical axes placed by pixel box (top-left x, y; width, height)."""
    fw, fh = fig.get_size_inches() * fig.dpi
    a = fig.add_axes([x / fw, 1 - (y + h) / fh, w / fw, h / fh])
    a.set(xlim=xlim, ylim=ylim)
    a.spines[['top', 'right']].set_visible(False)
    for s in ('left', 'bottom'):
        a.spines[s].set_color(MUTED)
        a.spines[s].set_linewidth(.8)
    a.tick_params(labelsize=size - .6, colors=MUTED, length=3)
    if xlabel:
        a.set_xlabel(xlabel, fontsize=size, color=INK)
    if ylabel:
        a.set_ylabel(ylabel, fontsize=size, color=INK)
    return a


def export(fig, name, lang, description):
    """Write docs/figs/<name>(_en).png and the matching .svg (no date; trailing spaces stripped)."""
    out = Path(__file__).resolve().parents[1] / (name + ('' if lang == 'ja' else '_en') + '.png')
    try:
        fig.savefig(out, dpi=DPI)
        svg = StringIO()
        fig.savefig(svg, format='svg', metadata={'Date': None, 'Description': description})
        out.with_suffix('.svg').write_text('\n'.join(s.rstrip() for s in svg.getvalue().splitlines()) + '\n',
                                           encoding='utf-8', newline='\n')
    finally:
        plt.close(fig)
    return str(out)


def run(build, name, lang, description):
    if lang not in ('ja', 'en'):
        raise ValueError('lang must be ja or en')
    with drawing_style():
        fig = build(lang)
        return export(fig, name, lang, description)
