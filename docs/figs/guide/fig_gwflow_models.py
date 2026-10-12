"""gwflow supplement: Green-Ampt infiltration capacity and the piecewise head of the
conduit layer. Regenerate only this page with make_guide_figs.py gwflow_models.
"""
from _terms import *

T = {'ja': {'a': '(a) Green-Ampt の浸透能 f_v(F)(Δθ = 0.2)',
            'b': '(b) 管路層の水頭 H(h_gc)(折れ線。被圧で疑似スロット)',
            'xa': '累積浸透深 F = h_g (m)', 'ya': 'f_v (mm/h)',
            'sand': '砂: K_s 118 mm/h、ψ_f 0.05 m', 'sl': '砂壌土(既定の K_s): 11 mm/h、ψ_f 0.11 m',
            'cl': '粘土質壌土: 1.0 mm/h、ψ_f 0.21 m', 'flat': 'ψ_f = 0: 一定浸透能(既定)',
            'xb': '貯留 h_gc (m 柱状)', 'yb': 'H − z_b (m)',
            'free': '不圧: H = z_b + h_gc/s_y(s_y = 0.05)', 'surch': '被圧: 勾配 1/s_slot(s_slot = s_y/50)',
            'cap': '容量 c = 0.01 m(満管)',
            'note': '(a) F_eff = max(F, K_sv dt) の正則化で F → 0 の発散を抑える。(b) 満管を超えると水頭が 50 倍の勾配で立ち上がり、圧力流(サーチャージ)と噴出を表す。'},
     'en': {'a': '(a) Green-Ampt infiltration capacity f_v(F) (Δθ = 0.2)',
            'b': '(b) Head of the conduit layer H(h_gc) (piecewise; pseudo-slot when surcharged)',
            'xa': 'cumulative infiltration F = h_g (m)', 'ya': 'f_v (mm/h)',
            'sand': 'sand: K_s 118 mm/h, ψ_f 0.05 m', 'sl': 'sandy loam (default K_s): 11 mm/h, ψ_f 0.11 m',
            'cl': 'clay loam: 1.0 mm/h, ψ_f 0.21 m', 'flat': 'ψ_f = 0: constant capacity (default)',
            'xb': 'storage h_gc (m, column)', 'yb': 'H − z_b (m)',
            'free': 'free: H = z_b + h_gc/s_y (s_y = 0.05)', 'surch': 'surcharged: slope 1/s_slot (s_slot = s_y/50)',
            'cap': 'capacity c = 0.01 m (full pipe)',
            'note': '(a) The regularisation F_eff = max(F, K_sv dt) bounds the divergence at F → 0. (b) Above the capacity the head rises 50 times faster, which represents pressurised flow (surcharge) and surcharge outflow.'}}


def build(lang):
    t = T[lang]; fig, base = canvas(860)
    text(base, 48, 32, t['a'], 13, weight='bold'); text(base, 940, 32, t['b'], 13, weight='bold')
    ax = plot_axes(fig, 110, 90, 700, 480)
    F = np.linspace(0.0005, 0.2, 400); dth = 0.2
    items = []
    for K, psi, col, ls, key in [(118, 0.05, BLUE, '-', 'sand'), (11, 0.11, ORANGE, '-', 'sl'), (1.0, 0.21, '#8fbf6a', '-', 'cl')]:
        ax.plot(F, K * (1 + psi * dth / F), color=col, lw=1.8, ls=ls, gid=key); items.append((col, ls, t[key]))
    ax.axhline(11, color=ORANGE, lw=1, ls=':', gid='flat'); items.append((ORANGE, ':', t['flat']))
    ax.set(xlim=(0, 0.2), ylim=(0, 150), xlabel=t['xa'], ylabel=t['ya'])
    legend_rows(base, 48, 640, items, 760, 36, 9.3)
    ax = plot_axes(fig, 1000, 90, 700, 480)
    cap, sy = 0.01, 0.05; slot = sy / 50
    h1 = np.linspace(0, cap, 50); h2 = np.linspace(cap, 0.0105, 50)
    ax.plot(h1, h1 / sy, color=BLUE, lw=2, gid='free')
    ax.plot(h2, cap / sy + (h2 - cap) / slot, color=ORANGE, lw=2, gid='surcharged')
    ax.axvline(cap, color=MUTED, lw=1, ls=':', gid='cap')
    ax.set(xlim=(0, 0.0105), ylim=(0, 0.7), xlabel=t['xb'], ylabel=t['yb'])
    legend_rows(base, 940, 640, [(BLUE, '-', t['free']), (ORANGE, '-', t['surch']), (MUTED, ':', t['cap'])], 760, 36, 9.3)
    block(base, 48, 800, t['note'], 1650, 9.3, color=MUTED)
    return fig


def draw(lang):
    with drawing_style(): return export(build(lang), 'gwflow_models', lang)
