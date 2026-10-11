"""Precision drawing helpers used ONLY by fig_structure and fig_salt.

No global rcParams or changes to the other guide/result figures. Matplotlib and
NumPy only. Shared coordinates define boundaries; labels are wrapped using the
actual renderer, not estimated character counts. SVGs contain vector paths,
not embedded raster images or font binaries.
"""
from pathlib import Path as FilePath
from contextlib import contextmanager
import re
import numpy as np
import matplotlib as mpl
from matplotlib import pyplot as plt, font_manager
from matplotlib.path import Path
from matplotlib.patches import PathPatch, Polygon, FancyArrowPatch
from matplotlib.font_manager import FontProperties

INK = '#282c30'
MUTED = '#6b6a66'
RULE = '#d8d6d1'

@contextmanager
def drawing_style():
    available = {f.name for f in font_manager.fontManager.ttflist}
    jp = next((f for f in ('Noto Sans CJK JP', 'IPAGothic', 'IPAexGothic',
                           'Yu Gothic', 'Hiragino Sans') if f in available), None)
    if jp is None:
        raise RuntimeError('Japanese font required: install Noto Sans CJK JP or IPAGothic.')
    with mpl.rc_context({'font.family': [jp, 'DejaVu Sans'],
                         'font.size': 9, 'text.color': INK,
                         'svg.fonttype': 'path', 'svg.hashsalt': 'encflow-schematic-v1',
                         'path.simplify': False, 'lines.solid_capstyle': 'round',
                         'lines.solid_joinstyle': 'round', 'figure.facecolor': 'white',
                         'savefig.facecolor': 'white'}):
        yield


def text(ax, x, y, s, size=9, color=INK, ha='left', va='top', weight='normal', **kwargs):
    return ax.text(x, y, s, fontsize=size, color=color, ha=ha, va=va,
                   fontweight=weight, linespacing=1.45, zorder=20, **kwargs)


def wrap(ax, s, width, size=9, weight='normal'):
    """Wrap without deleting words. Explicit upstream line breaks are kept."""
    renderer = ax.figure.canvas.get_renderer()
    px = abs(ax.transData.transform((width, 0))[0] - ax.transData.transform((0, 0))[0])
    fp = FontProperties(family=mpl.rcParams['font.family'], size=size, weight=weight)
    def fits(t):
        return renderer.get_text_width_height_descent(t, fp, False)[0] <= px
    lines = []
    for paragraph in s.split('\n'):
        if not paragraph:
            lines.append(''); continue
        # Keep parameter names intact, while Japanese can wrap between characters.
        tokens = re.findall(r'[0-9]+(?:[.][0-9]+)?(?:[-–][0-9]+(?:[.][0-9]+)?)?|[A-Za-z_][A-Za-z0-9_]*(?:=[0-9.]+)?|\s+|.', paragraph)
        line = ''
        for token in tokens:
            cand = line + token
            if line and not fits(cand):
                lines.append(line.rstrip()); line = token.lstrip()
            else:
                line = cand
        lines.append(line.rstrip())
    return '\n'.join(lines)


def block(ax, x, y, s, width, size=8.3, color=INK, weight='normal'):
    return text(ax, x, y, wrap(ax, s, width, size, weight), size=size,
                color=color, weight=weight)


def paragraph(ax, x, y, s, width, size=8.3, color=INK, gap=0.12):
    a = block(ax, x, y, s, width, size, color)
    ax.figure.canvas.draw()
    bb = a.get_window_extent(ax.figure.canvas.get_renderer())
    return ax.transData.inverted().transform((bb.x0, bb.y0))[1] - gap


def line(ax, xy, color=INK, lw=1.15, ls='-', z=6, **kw):
    p = np.asarray(xy)
    return ax.plot(p[:, 0], p[:, 1], color=color, lw=lw, ls=ls,
                   zorder=z, solid_capstyle='round', solid_joinstyle='round', **kw)[0]


def arrow(ax, xy, color, lw=1.65, ls='-', size=11, z=10):
    p = xy if isinstance(xy, Path) else Path(np.asarray(xy),
                            [Path.MOVETO] + [Path.LINETO] * (len(xy) - 1))
    a = FancyArrowPatch(path=p, arrowstyle='-|>', mutation_scale=size,
                        linewidth=lw, color=color, linestyle=ls,
                        capstyle='round', joinstyle='round', zorder=z)
    ax.add_patch(a)
    return a


def curve(start, commands):
    v, c = [start], [Path.MOVETO]
    for command in commands:
        kind, *pts = command
        if kind == 'L': v.append(pts[0]); c.append(Path.LINETO)
        elif kind == 'C': v.extend(pts); c.extend([Path.CURVE4]*3)
        elif kind == 'Q': v.extend(pts); c.extend([Path.CURVE3]*2)
        elif kind == 'Z': v.append(start); c.append(Path.CLOSEPOLY)
        else: raise ValueError(kind)
    return Path(v, c)


def patch(ax, path, face, edge='none', lw=1.1, z=2):
    p = PathPatch(path, facecolor=face, edgecolor=edge, lw=lw,
                  joinstyle='round', zorder=z)
    ax.add_patch(p)
    return p


def ground(ax, x, z, base, fill, edge, lw=1.15):
    poly = Polygon(list(zip(x, z)) + [(x[-1], base), (x[0], base)],
                   closed=True, facecolor=fill, edgecolor='none', zorder=1)
    ax.add_patch(poly)
    line(ax, list(zip(x, z)), edge, lw, z=5)
    return poly


def wet_profile(x, z, level, xmin=None, xmax=None):
    """Clip a continuous piecewise-linear bed at a constant water level.

    Every shore intersection is inserted explicitly. Each returned array
    traces the *same bed* and its end points lie on the water level unless
    truncated by the requested open domain boundary. No separate water-bed
    vertices are introduced.
    """
    x, z = np.asarray(x, float), np.asarray(z, float)
    if x.ndim != 1 or len(x) < 2 or z.shape != x.shape or np.any(np.diff(x) <= 0):
        raise ValueError('x must be strictly increasing and match z.')
    lo, hi = (x[0] if xmin is None else xmin), (x[-1] if xmax is None else xmax)
    if not x[0] <= lo < hi <= x[-1]: raise ValueError('Invalid wet-profile bounds.')
    xp = np.r_[lo, x[(x > lo) & (x < hi)], hi]
    zp = np.interp(xp, x, z)
    pieces, part = [], []
    tol = 1e-11
    for a,b,za,zb in zip(xp[:-1], xp[1:], zp[:-1], zp[1:]):
        if za < level or zb < level:
            aa,bb = a,b
            if za > level: aa = a + (level-za)*(b-a)/(zb-za)
            if zb > level: bb = a + (level-za)*(b-a)/(zb-za)
            if bb-aa > tol:
                pa = (aa, float(np.interp(aa,x,z)))
                pb = (bb, float(np.interp(bb,x,z)))
                if part and abs(part[-1][0]-aa) > tol:
                    pieces.append(np.asarray(part)); part=[]
                if not part: part.append(pa)
                part.append(pb)
        elif part:
            pieces.append(np.asarray(part)); part=[]
    if part: pieces.append(np.asarray(part))
    return pieces


def water(ax, x, z, level, fill, edge, xmin=None, xmax=None, zorder=3):
    segments = wet_profile(x,z,level,xmin,xmax)
    for bed in segments:
        verts = np.vstack([bed, [bed[-1,0],level], [bed[0,0],level]])
        ax.add_patch(Polygon(verts, closed=True, fc=fill, ec='none', zorder=zorder))
        line(ax, [(bed[0,0],level),(bed[-1,0],level)], edge, 1.3, z=zorder+1)
    return segments


def monotone_cubic(x, y, q):
    """Shape-preserving piecewise cubic Hermite interpolation (NumPy only)."""
    x,y,q = np.asarray(x,float),np.asarray(y,float),np.asarray(q,float)
    if len(x)<3 or np.any(np.diff(x)<=0) or x.shape!=y.shape:
        raise ValueError('Need at least three increasing knots.')
    h=np.diff(x); d=np.diff(y)/h; m=np.zeros_like(y)
    for i in range(1,len(y)-1):
        if d[i-1]*d[i]>0:
            w1=2*h[i]+h[i-1];w2=h[i]+2*h[i-1]
            m[i]=(w1+w2)/(w1/d[i-1]+w2/d[i])
    for k,a,b,da,db in [(0,h[0],h[1],d[0],d[1]),(-1,h[-1],h[-2],d[-1],d[-2])]:
        v=((2*a+b)*da-a*db)/(a+b)
        if v*da<=0: v=0.0
        elif da*db<0 and abs(v)>3*abs(da): v=3*da
        m[k]=v
    idx=np.clip(np.searchsorted(x,q)-1,0,len(x)-2)
    u=(q-x[idx])/h[idx]
    return ((2*u**3-3*u**2+1)*y[idx] + (u**3-2*u**2+u)*h[idx]*m[idx]
            +(-2*u**3+3*u**2)*y[idx+1] +(u**3-u**2)*h[idx]*m[idx+1])


def export(fig, png_path, dpi=220):
    p=FilePath(png_path)
    p.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(p,dpi=dpi)
    fig.savefig(p.with_suffix('.svg'), metadata={'Date':None,
                    'Description':'ENCflow explanatory schematic. Not a numerical result.'})
    plt.close(fig)
    return str(p)
