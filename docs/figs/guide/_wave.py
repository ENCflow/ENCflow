"""Helpers shared by the coastal wave field figures (fig_wavefield, fig_wavefield_models).

Linear wave theory, the cos^s spreading exponent, Japanese-aware line breaking on the
pixel canvas of _terms (y downwards), and cropping the canvas to its content.
No global style changes.  Matplotlib and NumPy only.
"""
import re
import numpy as np
import matplotlib
from matplotlib.font_manager import FontProperties
from _schematic import text, INK

G, RHO = 9.81, 1025.0


def wavenumber(sigma, h):
    """sigma^2 = g k tanh(kh), Newton from Eckart's approximation."""
    h = np.maximum(np.asarray(h, float), 1e-6)
    k = sigma**2 / G / np.sqrt(np.tanh(sigma**2 * h / G))
    for _ in range(40):
        t = np.tanh(k * h)
        k = k - (G * k * t - sigma**2) / (G * t + G * k * h * (1 - t * t))
    return k


def group(sigma, k, h):
    """n = c_g/c, phase speed c and group velocity c_g of linear theory."""
    kh = k * h
    n = 0.5 * (1 + 2 * kh / np.sinh(2 * kh))
    return n, sigma / k, n * sigma / k


def spreading_exponent(sig_deg):
    """s of cos^s with the Kuik et al. (1988) spreading sigma^2 = 2 (1 - m1)."""
    th = np.radians(np.linspace(-90, 90, 3601))[1:-1]
    target = 1 - np.radians(sig_deg)**2 / 2
    lo, hi = 0.1, 400.0
    for _ in range(80):
        s = 0.5 * (lo + hi)
        w = np.cos(th)**s
        m1 = np.sum(w * np.cos(th)) / np.sum(w)
        lo, hi = (s, hi) if m1 < target else (lo, s)
    return 0.5 * (lo + hi)


CLOSE = set('。、,.:;)」』】〕・ー°%′')


def jwrap(ax, s, width, size=9):
    """Like _schematic.wrap, but a closing mark never starts a line (Japanese line breaking)."""
    renderer = ax.figure.canvas.get_renderer()
    px = abs(ax.transData.transform((width, 0))[0] - ax.transData.transform((0, 0))[0])
    fp = FontProperties(family=matplotlib.rcParams['font.family'], size=size)
    fits = lambda u: renderer.get_text_width_height_descent(u, fp, False)[0] <= px
    out = []
    for para in s.split('\n'):
        # keep short relations ('θ = 20°', 'gv < 1') and numbers with units ('10 m') on one line
        toks = re.findall(r'[θA-Za-z_][A-Za-z0-9_′]* ?[=<>≤≥] ?[−-]?[0-9]+(?:[.][0-9]+)?°?'
                          r'|[0-9]+(?:[.][0-9]+)?(?:[〜–-][0-9]+(?:[.][0-9]+)?)? ?(?:m/s|rad/m|km|cm|mm|m|s)(?![A-Za-z])'
                          r'|[0-9]+/[0-9]+|[0-9]+(?:[.][0-9]+)?|[A-Za-z_][A-Za-z0-9_]*|\s+|.', para)
        merged = []
        for tk in toks:                                         # glue closing marks to what precedes them
            if merged and tk in CLOSE:
                merged[-1] += tk
            else:
                merged.append(tk)
        cur = ''
        for tk in merged:
            if cur and not fits(cur + tk):
                out.append(cur.rstrip()); cur = tk.lstrip()
            else:
                cur += tk
        out.append(cur.rstrip())
    return '\n'.join(out)


def paragraph(ax, x, y, s, width, size=9, color=INK, gap=8):
    """Wrapped text block on the pixel canvas (y downwards); returns the y below it."""
    a = text(ax, x, y, jwrap(ax, s, width, size), size, color=color)
    ax.figure.canvas.draw()
    bb = a.get_window_extent(ax.figure.canvas.get_renderer())
    return ax.transData.inverted().transform((bb.x0, bb.y0))[1] + gap


def fit_height(fig, ax, height):
    """Crop the pixel canvas to the given height, keeping every axes at its pixel position."""
    W, H1 = fig.get_size_inches() * fig.dpi
    boxes = [(a, a.get_position()) for a in fig.axes if a is not ax]
    fig.set_size_inches(W / fig.dpi, height / fig.dpi)
    ax.set_ylim(height, 0)
    for a, p in boxes:
        top = (1 - p.y1) * H1
        a.set_position([p.x0, 1 - (top + p.height * H1) / height, p.width, p.height * H1 / height])
