"""wq supplement: dissolved fraction of the Kd partitioning and the buildup–washoff
cycle. Regenerate only this page with make_guide_figs.py wq_models.
"""
from _terms import *

T = {'ja': {'a': '(a) Kd 分配の溶存率 f_d = 1/(1 + K_d C_ss)',
            'b': '(b) 表面蓄積と洗い出し(晴天 5 日 → 降雨 1 日)',
            'xa': '浮遊砂濃度 C_ss (kg/m³)', 'ya': '溶存率 f_d',
            'k3': 'K_d = 10³ L/kg(Zn)', 'k4': 'K_d = 10⁴ L/kg(Cs、Pb の下限)', 'k5': 'K_d = 10⁵ L/kg(Pb)',
            'xb': '時間 (day)', 'yb': 'プール B / B_max',
            'build': '蓄積 dB/dt = r(1 − B/B_max)', 'wash': '洗い出し B(1 − e^{−λt})、λ = k_r P',
            'note': '(a) 浮遊砂が濃いほど粒子態の割合 1 − f_d が増え、浮遊砂と一緒に沈む。(b) 蓄積は B_max に飽和し、降雨で指数的に流出する(ファーストフラッシュ)。'},
     'en': {'a': '(a) Dissolved fraction of the Kd partitioning f_d = 1/(1 + K_d C_ss)',
            'b': '(b) Surface buildup and washoff (5 dry days, then 1 day of rain)',
            'xa': 'suspended-sediment concentration C_ss (kg/m³)', 'ya': 'dissolved fraction f_d',
            'k3': 'K_d = 10³ L/kg (Zn)', 'k4': 'K_d = 10⁴ L/kg (Cs; low end of Pb)', 'k5': 'K_d = 10⁵ L/kg (Pb)',
            'xb': 'time (day)', 'yb': 'pool B / B_max',
            'build': 'buildup dB/dt = r(1 − B/B_max)', 'wash': 'washoff B(1 − e^{−λt}), λ = k_r P',
            'note': '(a) The richer the suspended sediment, the larger the particulate share 1 − f_d that settles with it. (b) Buildup saturates at B_max and rain releases it exponentially (first flush).'}}


def build(lang):
    t = T[lang]; fig, base = canvas(820)
    text(base, 48, 32, t['a'], 13, weight='bold'); text(base, 940, 32, t['b'], 13, weight='bold')
    ax = plot_axes(fig, 110, 90, 700, 480)
    css = np.logspace(-3, 1, 300); items = []
    for kd, col, ls, key in [(1e3, BLUE, '-', 'k3'), (1e4, ORANGE, '--', 'k4'), (1e5, '#8fbf6a', '-.', 'k5')]:
        ax.plot(css, 1 / (1 + 1e-3 * kd * css), color=col, lw=1.8, ls=ls, gid=key); items.append((col, ls, t[key]))
    ax.set(xscale='log', xlim=(1e-3, 10), ylim=(0, 1.05), xlabel=t['xa'], ylabel=t['ya'])
    legend_rows(base, 48, 640, items, 760, 40, 9.3)
    ax = plot_axes(fig, 1000, 90, 700, 480)
    tb = np.linspace(0, 5, 200); r, bmax = 0.5, 1.0
    B = bmax * (1 - np.exp(-r * tb / bmax))
    tw = np.linspace(5, 6, 200); lam = 4.0
    W = B[-1] * np.exp(-lam * (tw - 5))
    ax.plot(tb, B, color=BLUE, lw=2, gid='buildup'); ax.plot(tw, W, color=ORANGE, lw=2, gid='washoff')
    ax.axvspan(5, 6, color='#eef3fa', zorder=0, gid='rain')
    ax.set(xlim=(0, 6), ylim=(0, 1.05), xlabel=t['xb'], ylabel=t['yb'])
    legend_rows(base, 940, 640, [(BLUE, '-', t['build']), (ORANGE, '-', t['wash'])], 760, 40, 9.3)
    block(base, 48, 745, t['note'], 1650, 9.3, color=MUTED)
    return fig


def draw(lang):
    with drawing_style(): return export(build(lang), 'wq_models', lang)
