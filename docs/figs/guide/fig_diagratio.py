"""Supplement on choosing the diagonal share d (users_guide/diagratio.md).

One figure with four panels against d (the share of each cell face lent to the
two diagonal edges): (a) the direction bias of the 9-point diffusion operator
(ratio of the decay rates at 45 deg and 0 deg for the same wavenumber; for
gravity waves it is the ratio of the squared phase speeds), (b) the stable time
step of the explicit schemes relative to the 4-neighbour grid, (c) the conveyance
of a one-cell-wide line feature (channel, conduit) without reassignment, diagonal
over axis, and (d) the largest and smallest crosswind numerical diffusion of
first-order upwind over the flow directions.

All curves are computed here from closed forms (developer.md sec. 93 and 95,
users_guide/diagonal_diffusion.md sec. 2.3); the crosswind coefficient is the
share-weighted sum (1 - d) F(phi) + d sqrt(2) F(phi - 45 deg) of the
4-neighbour coefficient F, which reproduces the measured ENC table at
d = 2/(2+sqrt(2)).  Regenerate only this page with make_guide_figs.py diagratio.
"""
from _terms import *

T = {'ja': {
 'title_a': '(a) 誤差の向きの偏り(45° と 0° の比 − 1)',
 'title_b': '(b) 陽解法の時間刻みの上限(4 近傍に対する比)',
 'title_c': '(c) 1 セル幅の線状の要素の通水能(振り替えなし)',
 'title_d': '(d) 1 次風上の横断の数値拡散(向きによる最大と最小)',
 'x': '斜めの配分比 d',
 'ya': '減衰率の比 − 1 (%。波では位相速度の 2 乗)',
 'yb': '時間刻みの上限の比',
 'yc': '斜めの向き / 軸の向き',
 'yd': '係数 c(D = c |u| Δ)',
 'l8': '波長 8Δ', 'l4': '波長 4Δ',
 'bd': '拡散(正値性)', 'bw': '重力波',
 'ca': '同じ勾配での流量(管路など)',
 'cn': '自然幅(軸 Δ、斜め 0.707Δ)に対する比',
 'dmax': '最大', 'dmin': '最小',
 'm13': '1/3 等方', 'm41': '0.414 均一', 'm50': '0.5 自然幅', 'm58': '0.586 等長',
}, 'en': {
 'title_a': '(a) Direction bias of the error (45° vs 0°)',
 'title_b': '(b) Explicit time-step limit (vs 4 neighbours)',
 'title_c': '(c) One-cell-wide line feature, no reassignment',
 'title_d': '(d) First-order crosswind diffusion over directions',
 'x': 'diagonal share d',
 'ya': 'decay-rate ratio − 1 (%; waves: phase speed squared)',
 'yb': 'ratio of the time-step limit',
 'yc': 'diagonal / axis direction',
 'yd': 'coefficient c (D = c |u| Δ)',
 'l8': 'wavelength 8Δ', 'l4': 'wavelength 4Δ',
 'bd': 'diffusion (positivity)', 'bw': 'gravity waves',
 'ca': 'flow for the same gradient (conduits etc.)',
 'cn': 'relative to natural widths (Δ, 0.707Δ)',
 'dmax': 'largest', 'dmin': 'smallest',
 'm13': '1/3 isotropic', 'm41': '0.414 uniform', 'm50': '0.5 natural', 'm58': '0.586 equal',
}}

DS = np.linspace(0.0, 1.0, 401)
MARKS = [(1.0 / 3.0, 'm13', GREEN), (np.sqrt(2.0) - 1.0, 'm41', BLUE), (0.5, 'm50', MUTED),
         (2.0 / (2.0 + np.sqrt(2.0)), 'm58', ORANGE)]


def symbol(kx, ky, d):
    """Symbol of the 9-point Laplacian with axis weight (1 - d) and diagonal weight d/2 (unit cells)."""
    return (1 - d) * (2 * np.cos(kx) + 2 * np.cos(ky) - 4) + 2 * d * (np.cos(kx) * np.cos(ky) - 1)


def bias(d, wavelength):
    k = 2 * np.pi / wavelength
    return 100.0 * (symbol(k / np.sqrt(2), k / np.sqrt(2), d) / symbol(k, 0.0, d) - 1.0)


def f4(th):
    c, s = np.abs(np.cos(th)), np.abs(np.sin(th))
    return 0.5 * (c * s * s + s * c * c)


def crosswind(d):
    phi = np.radians(np.linspace(0.0, 45.0, 451))
    v = (1 - d) * f4(phi) + d * np.sqrt(2.0) * f4(phi - np.pi / 4)
    return v.max(), v.min()


def marks(ax, t, labels=False):
    for d, key, color in MARKS:
        ax.axvline(d, color=color, lw=1.0, ls=':', zorder=1)
        if labels:
            ax.text(d, 1.02, t[key], transform=ax.get_xaxis_transform(), rotation=90, ha='center',
                    va='bottom', fontsize=8, color=color)


def build(lang):
    t = T[lang]
    fig, base = canvas(1500)
    text(base, 48, 30, t['title_a'], 12, weight='bold')
    text(base, 948, 30, t['title_b'], 12, weight='bold')
    text(base, 48, 875, t['title_c'], 12, weight='bold')
    text(base, 948, 875, t['title_d'], 12, weight='bold')

    ax = plot_axes(fig, 110, 230, 740, 450)
    ax.plot(DS, bias(DS, 8.0), '-', color=INK, lw=1.6, label=t['l8'])
    ax.plot(DS, bias(DS, 4.0), '--', color=INK, lw=1.3, label=t['l4'])
    ax.axhline(0.0, color=RULE, lw=0.8)
    marks(ax, t, labels=True)
    ax.set(xlabel=t['x'], ylabel=t['ya'], xlim=(0, 1), ylim=(-16, 13))
    ax.grid(color=RULE, lw=.5)
    ax.legend(fontsize=9, frameon=False, loc='lower left')

    ax = plot_axes(fig, 1010, 230, 740, 450)
    smax = np.maximum(4.0, 8.0 * (1.0 - DS))
    ax.plot(DS, 4.0 / (4.0 - 2.0 * DS), '-', color=INK, lw=1.6, label=t['bd'])
    ax.plot(DS, np.sqrt(8.0 / smax), '--', color=INK, lw=1.3, label=t['bw'])
    marks(ax, t, labels=True)
    ax.set(xlabel=t['x'], ylabel=t['yb'], xlim=(0, 1), ylim=(0.95, 2.05))
    ax.grid(color=RULE, lw=.5)
    ax.legend(fontsize=9, frameon=False, loc='upper left')

    ax = plot_axes(fig, 110, 950, 740, 450)
    dd = DS[(DS > 0.02) & (DS < 0.98)]
    ax.semilogy(dd, (dd / np.sqrt(2.0)) / (1.0 - dd), '-', color=INK, lw=1.6, label=t['ca'])
    ax.semilogy(dd, dd / (1.0 - dd), '--', color=INK, lw=1.3, label=t['cn'])
    ax.axhline(1.0, color=RULE, lw=0.8)
    marks(ax, t)
    ax.set(xlabel=t['x'], ylabel=t['yc'], xlim=(0, 1), ylim=(0.02, 50))
    ax.grid(color=RULE, lw=.5, which='both')
    ax.legend(fontsize=8.5, frameon=False, loc='upper left')

    ax = plot_axes(fig, 1010, 950, 740, 450)
    mm = np.array([crosswind(d) for d in DS])
    ax.fill_between(DS, mm[:, 1], mm[:, 0], color='#eef3fb', zorder=0)
    ax.plot(DS, mm[:, 0], '-', color=INK, lw=1.6, label=t['dmax'])
    ax.plot(DS, mm[:, 1], '--', color=INK, lw=1.3, label=t['dmin'])
    marks(ax, t)
    ax.set(xlabel=t['x'], ylabel=t['yd'], xlim=(0, 1), ylim=(0, 0.52))
    ax.grid(color=RULE, lw=.5)
    ax.legend(fontsize=9, frameon=False, loc='upper left')
    return fig


def draw(lang):
    with drawing_style():
        return export(build(lang), 'diagratio_tradeoff', lang)
