"""sediment / massflow supplements: bedload formulas and the debris-flow equilibrium
concentration. Regenerate only this page with make_guide_figs.py sediment.
"""
from _terms import *

T = {'ja': {'a': '(a) 無次元流砂量 q_b*(τ*)(τ*c = 0.05)',
            'b': '(b) 土石流の平衡濃度 C∞(tanθ)(φ = 35°、s = 1.65、C* = 0.6)',
            'am': '芦田・道上(f_qbform = 1)', 'mpm': 'MPM(f_qbform = 2)',
            'xa': 'τ*', 'ya': 'q_b* = q_b / √(s g d50³)',
            'xb': 'tanθ', 'yb': 'C∞',
            'stony': '石礫型 tanθ/(s(tanφ − tanθ))', 'imm': '未成熟 6.7 C∞d²', 'cap': '上限 0.9 C*',
            'note': '勾配 0.03 以下は堆積側(C∞ = 0)。濃度 C が C∞ より低ければ侵食、高ければ堆積(§3)。'},
     'en': {'a': '(a) Dimensionless bedload q_b*(τ*) (τ*c = 0.05)',
            'b': '(b) Equilibrium concentration C∞(tanθ) of debris flow (φ = 35°, s = 1.65, C* = 0.6)',
            'am': 'Ashida–Michiue (f_qbform = 1)', 'mpm': 'MPM (f_qbform = 2)',
            'xa': 'τ*', 'ya': 'q_b* = q_b / √(s g d50³)',
            'xb': 'tanθ', 'yb': 'C∞',
            'stony': 'stony: tanθ/(s(tanφ − tanθ))', 'imm': 'immature: 6.7 C∞d²', 'cap': 'cap 0.9 C*',
            'note': 'below slope 0.03 the bed only deposits (C∞ = 0). C below C∞ erodes, above deposits (§3).'}}


def build(lang):
    t = T[lang]; fig, base = canvas(820)
    text(base, 48, 32, t['a'], 13, weight='bold'); text(base, 940, 32, t['b'], 13, weight='bold')
    # (a) bedload
    ax = plot_axes(fig, 110, 90, 700, 480)
    tc = 0.05; ts = np.linspace(tc, 1.0, 300)
    am = 17 * ts ** 1.5 * (1 - tc / ts) * (1 - np.sqrt(tc / ts))
    mpm = 8 * (ts - tc) ** 1.5
    ax.plot(ts, am, color=BLUE, lw=2, gid='ashida'); ax.plot(ts, mpm, color=ORANGE, lw=1.8, ls='--', gid='mpm')
    ax.set(xlim=(0, 1), ylim=(0, 10), xlabel=t['xa'], ylabel=t['ya'])
    legend_rows(base, 48, 640, [(BLUE, '-', t['am']), (ORANGE, '--', t['mpm'])], 760, 44, 9.5)
    # (b) equilibrium concentration
    ax = plot_axes(fig, 1000, 90, 700, 480)
    phi = np.tan(np.radians(35.)); s = 1.65; cstar = 0.6
    th = np.linspace(0.0, 0.6, 600)
    stony = th / (s * (phi - th)); stony = np.where(th > 0.138, np.minimum(stony, 0.9 * cstar), np.nan)
    imm = np.where((th > 0.03) & (th <= 0.138), 6.7 * (th / (s * (phi - th))) ** 2, np.nan)
    ax.plot(th, stony, color=BLUE, lw=2, gid='stony'); ax.plot(th, imm, color=ORANGE, lw=2, gid='immature')
    ax.axhline(0.9 * cstar, color=MUTED, lw=1, ls=':', gid='cap')
    ax.plot([0, 0.03], [0, 0], color=MUTED, lw=2)
    ax.set(xlim=(0, 0.6), ylim=(0, 0.6), xlabel=t['xb'], ylabel=t['yb'])
    legend_rows(base, 940, 640, [(BLUE, '-', t['stony']), (ORANGE, '-', t['imm']), (MUTED, ':', t['cap'])], 760, 40, 9.5)
    block(base, 48, 775, t['note'], 1650, 9.5, color=MUTED)
    return fig


def draw(lang):
    with drawing_style(): return export(build(lang), 'sediment_laws', lang)
