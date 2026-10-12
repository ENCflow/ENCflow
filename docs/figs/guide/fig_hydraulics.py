"""hydraulics supplement: Honma weir formula and the three regimes of a culvert.
Regenerate only this page with make_guide_figs.py hydraulics.
"""
from _terms import *

T = {'ja': {'a': '(a) 本間公式: 単位幅流量 q と下流水深比 h₂/h₁(h₁ = 1 m)',
            'b': '(b) カルバートの 3 レジーム(B = D = 1 m、c_e = 0.5、L = 0)',
            'xa': '下流水深比 h₂/h₁', 'ya': 'q (m²/s)',
            'free': '自由越流 0.35 h₁√(2g h₁)', 'sub': '潜り越流 0.91 h₂√(2g(h₁ − h₂))', 'sw': '切替 h₂/h₁ = 2/3',
            'xb': '上流水深 h₁ = η_u − z_in (m)(下流は乾燥)', 'yb': 'Q (m³/s)',
            'weir': '堰 Q_w = B q(h₁, 0)', 'pipe': '管路 Q_p = C_p √(η_u − (z_out + D))', 'qq': 'Q = min(Q_w, Q_p)',
            'note': '(a) 両式は h₂/h₁ = 2/3 で連続に接続する。(b) 浅いうちは堰支配、水位が管頂を超えると満管容量が上限になる。管頂直上で管路式が 0 から立ち上がる凹みは現行の接続の仕様(本文 §2 の注)。'},
     'en': {'a': '(a) Honma formula: unit discharge q versus the tailwater ratio h₂/h₁ (h₁ = 1 m)',
            'b': '(b) Three regimes of a culvert (B = D = 1 m, c_e = 0.5, L = 0)',
            'xa': 'tailwater ratio h₂/h₁', 'ya': 'q (m²/s)',
            'free': 'free overflow 0.35 h₁√(2g h₁)', 'sub': 'submerged 0.91 h₂√(2g(h₁ − h₂))', 'sw': 'switch at h₂/h₁ = 2/3',
            'xb': 'upstream depth h₁ = η_u − z_in (m) (dry tailwater)', 'yb': 'Q (m³/s)',
            'weir': 'weir Q_w = B q(h₁, 0)', 'pipe': 'pipe Q_p = C_p √(η_u − (z_out + D))', 'qq': 'Q = min(Q_w, Q_p)',
            'note': '(a) The two branches join continuously at h₂/h₁ = 2/3. (b) Weir-controlled while shallow; once the level exceeds the crown the full-pipe capacity caps the discharge. The dip just above the crown, where the pipe formula starts from zero, is how the current connection behaves (note in §2).'}}


def build(lang):
    t = T[lang]; fig, base = canvas(820); g = 9.8
    text(base, 48, 32, t['a'], 13, weight='bold'); text(base, 940, 32, t['b'], 13, weight='bold')
    ax = plot_axes(fig, 110, 90, 700, 480)
    h1 = 1.0; r = np.linspace(0, 1, 400); h2 = r * h1
    qf = 0.35 * h1 * np.sqrt(2 * g * h1) * np.ones_like(r)
    qs = 0.91 * h2 * np.sqrt(2 * g * np.maximum(h1 - h2, 0))
    ax.plot(r[r < 2/3], qf[r < 2/3], color=BLUE, lw=2, gid='free')
    ax.plot(r[r >= 2/3], qs[r >= 2/3], color=ORANGE, lw=2, gid='submerged')
    ax.plot(r, qs, color=ORANGE, lw=0.8, ls=':', gid='submerged-ext')
    ax.axvline(2/3, color=MUTED, lw=1, ls=':', gid='switch')
    ax.set(xlim=(0, 1), ylim=(0, 2.0), xlabel=t['xa'], ylabel=t['ya'])
    legend_rows(base, 48, 640, [(BLUE, '-', t['free']), (ORANGE, '-', t['sub']), (MUTED, ':', t['sw'])], 760, 38, 9.3)
    ax = plot_axes(fig, 1000, 90, 700, 480)
    B = D = 1.0; ce = 0.5; zin = 0.0; zout = 0.0
    h = np.linspace(0.01, 3.0, 400)
    qw = B * 0.35 * h * np.sqrt(2 * g * h)
    cp = B * D * np.sqrt(2 * g / (1 + ce))
    qp = np.where(h > D, cp * np.sqrt(np.maximum(h - (zout + D), 0)), np.nan)
    q = np.where(h > D, np.minimum(qw, cp * np.sqrt(np.maximum(h - D, 0))), qw)
    ax.plot(h, qw, color=BLUE, lw=1.2, ls='--', gid='weir'); ax.plot(h, qp, color=ORANGE, lw=1.2, ls='--', gid='pipe')
    ax.plot(h, q, color=INK, lw=2.2, gid='q')
    ax.set(xlim=(0, 3), ylim=(0, 6), xlabel=t['xb'], ylabel=t['yb'])
    legend_rows(base, 940, 640, [(BLUE, '--', t['weir']), (ORANGE, '--', t['pipe']), (INK, '-', t['qq'])], 760, 38, 9.3)
    block(base, 48, 760, t['note'], 1650, 9.3, color=MUTED)
    return fig


def draw(lang):
    with drawing_style(): return export(build(lang), 'hydraulics_laws', lang)
