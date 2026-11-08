"""Adaptation of suspended sediment toward the equilibrium (sediment.md §4).

Steady uniform flow with unit discharge q: q dC/dx = w_f (C_eq - beta C), so the
concentration approaches C_eq / beta over the adaptation length L = q / (beta w_f)
(the continuous solution that test/suspend compares with: decay exp(-w_f beta dy / q)
per cell). (a) C(x) for clear-water inflow and for an overloaded inflow;
(b) L versus grain size with the Rubey settling velocity (sed_rubey_wf of
src/m_sedform.f90) and the floc band of mud, for q = 1 m^2/s and beta = 1.
Closed forms for illustrative values; not solver output.

Generate: python docs/figs/make_guide_figs.py sediment_adapt
"""
import numpy as np
from _geomorph import (canvas, header, panel, rule, chart, run, text, kblock as block, line,
                       INK, MUTED, RULE, SED, GREEN, BLUE, ORANGE, PANEL)

H = 660
S, G, NU = 1.65, 9.8, 1.0e-6
Q, BETA = 1.0, 1.0

T = {
 'ja': {
    'title': '浮遊砂の適応距離  |  平衡濃度に近づく距離 L = q / (β w_f)',
    'sub': '定常・一様な流れで q dC/dx = w_f (C_eq − β C) を解いた形(test/suspend が比べる連続解)。説明用の値で、計算結果ではない。',
    'a': '(a) 流下方向の濃度', 'a2': '一様な流れ(C_eq は一定)、β = 1',
    'ax': '流下距離 x / L', 'ay': 'C / (C_eq / β)',
    'clear': '清水が流入(C0 = 0): 巻き上げで増える', 'over': '過剰に流入(C0 = 2 C_eq/β): 沈降で減る',
    'l1': 'x = L で差の 63 %', 'l3': 'x = 3L で 95 %',
    'a_note': '平衡までの差は exp(−x/L) で減る。L は流れが運ぶ水の量 q = hV と、沈降で河床へ戻る速さ β w_f の比で、'
              '巻き上げの式(平衡濃度)にはよらない。',
    'b': '(b) 粒径と適応距離', 'b2': 'q = hV = 1 m²/s、β = 1、w_f は Rubey 式',
    'bx': '粒径 d (m)', 'by': '適応距離 L (m)',
    'rubey': 'Rubey 式の w_f', 'floc': '泥のフロック\n(w_f = 10⁻⁴〜10⁻³ m/s を直接)',
    'cell': '格子幅の目安 10 m', 'dom': '領域の目安 1 km', 'def': '既定 susp_d50 = 0.2 mm: L ≈ 40 m',
    'clay': '粘土', 'silt': 'シルト', 'sand': '砂',
    'b_note': 'L が格子幅より短い砂は、ほぼその場の平衡濃度で運ばれる(掃流砂に近い振る舞い)。L が領域より長い泥は、'
              '巻き上がった場所から遠くまで運ばれてから積もる(河口デルタの前面の泥など)。q が 10 倍なら L も 10 倍。',
    'foot': '濃度は水の体積あたり(hs を矩形換算水深で割った値)。離散の減衰率は格子と時間刻みで連続解からわずかにずれる(test/suspend で 1 % ほど速い)。',
 },
 'en': {
    'title': 'Adaptation length of suspended sediment  |  Distance to approach the equilibrium, L = q / (β w_f)',
    'sub': 'Solution of q dC/dx = w_f (C_eq − β C) in steady uniform flow (the continuous solution test/suspend compares with). Illustrative values; not computed results.',
    'a': '(a) Concentration along the flow', 'a2': 'uniform flow (C_eq constant), β = 1',
    'ax': 'distance downstream x / L', 'ay': 'C / (C_eq / β)',
    'clear': 'clear-water inflow (C0 = 0): rises by entrainment', 'over': 'overloaded inflow (C0 = 2 C_eq/β): falls by settling',
    'l1': 'x = L: 63 % of the gap', 'l3': 'x = 3L: 95 %',
    'a_note': 'The gap to the equilibrium decays as exp(−x/L). L is the ratio of the water carried, q = hV, to the speed of '
              'return to the bed by settling, β w_f, and does not depend on the entrainment formula (equilibrium concentration).',
    'b': '(b) Grain size and adaptation length', 'b2': 'q = hV = 1 m²/s, β = 1, Rubey w_f',
    'bx': 'grain size d (m)', 'by': 'adaptation length L (m)',
    'rubey': 'with the Rubey w_f', 'floc': 'mud flocs\n(give w_f = 10⁻⁴–10⁻³ m/s directly)',
    'cell': 'typical cell size 10 m', 'dom': 'typical domain 1 km', 'def': 'default susp_d50 = 0.2 mm: L ≈ 40 m',
    'clay': 'clay', 'silt': 'silt', 'sand': 'sand',
    'b_note': 'Sand with L shorter than a cell is carried near the local equilibrium concentration (close to bedload '
              'behaviour). Mud with L longer than the domain travels far from where it was entrained before it settles '
              '(e.g. mud on the front of a river-mouth delta). Ten times q gives ten times L.',
    'foot': 'Concentrations are per volume of water (hs divided by the rectangular-equivalent depth). The discrete decay rate '
            'departs slightly from the continuous solution with the grid and time step (about 1 % faster in test/suspend).',
 },
}


def rubey(d):
    d = np.asarray(d, float)
    bb = 36 * NU ** 2 / (S * G * d ** 3)
    return (np.sqrt(2.0 / 3.0 + bb) - np.sqrt(bb)) * np.sqrt(S * G * d)


def panel_a(fig, ax, t):
    panel(ax, 35, 108, t['a'])
    text(ax, 35, 136, t['a2'], size=8, color=MUTED)
    c = chart(fig, 110, 172, 620, 260, (0, 5), (0, 2.1), xlabel=t['ax'], ylabel=t['ay'])
    x = np.linspace(0, 5, 400)
    c.axhline(1.0, color=MUTED, lw=.8, ls=':')
    c.plot(x, 1 - np.exp(-x), color=BLUE, lw=2.0, label=t['clear'])
    c.plot(x, 1 + np.exp(-x), color=SED, lw=2.0, label=t['over'])
    for xx, key, dy in ((1.0, 'l1', -0.16), (3.0, 'l3', -0.16)):
        c.axvline(xx, color=RULE, lw=.8)
        c.plot([xx], [1 - np.exp(-xx)], 'o', color=BLUE, ms=4.5, zorder=5)
        c.text(xx + 0.06, 1 - np.exp(-xx) + dy, t[key], fontsize=7.6, color=MUTED, va='top')
    c.legend(loc='upper right', fontsize=7.6, frameon=False)
    block(ax, 35, 505, t['a_note'], 735, size=7.9)


def panel_b(fig, ax, t):
    x0 = 805
    panel(ax, x0, 108, t['b'])
    text(ax, x0, 136, t['b2'], size=8, color=MUTED)
    c = chart(fig, x0 + 75, 172, 620, 260, (1e-6, 2e-3), (1, 1e7), xlabel=t['bx'], ylabel=t['by'])
    c.set_xscale('log'); c.set_yscale('log')
    c.axvspan(1e-6, 4e-6, color='#f4f3ee', lw=0)
    c.axvspan(6.3e-5, 2e-3, color='#fbf3e6', lw=0)
    c.axhspan(Q / (BETA * 1e-3), Q / (BETA * 1e-4), color='#e7f0e3', lw=0)
    d = np.logspace(-6, np.log10(2e-3), 300)
    c.plot(d, Q / (BETA * rubey(d)), color=BLUE, lw=2.0)
    c.text(2.5e-4, Q / (BETA * float(rubey(2.5e-4))) * 3.0, t['rubey'], fontsize=7.6, color=BLUE)
    c.text(1.9e-3, 1.25e3, t['floc'], fontsize=7.4, color=GREEN, va='bottom', ha='right')
    for yy, key in ((10.0, 'cell'), (1000.0, 'dom')):
        c.axhline(yy, color=MUTED, lw=.8, ls='--')
        c.text(1.2e-6, yy * 1.25, t[key], fontsize=7.4, color=MUTED, va='bottom')
    for xx, key in ((2e-6, 'clay'), (1.6e-5, 'silt'), (3.5e-4, 'sand')):
        c.text(xx, 1.3, t[key], fontsize=7.4, color=MUTED, ha='center', va='bottom')
    c.plot([2e-4], [Q / (BETA * float(rubey(2e-4)))], 'o', color=ORANGE, ms=4.5, zorder=5)
    c.text(1.8e-4, 30, t['def'], fontsize=7.2, color=ORANGE, ha='right', va='top')
    block(ax, x0, 505, t['b_note'], 735, size=7.9)


def build(lang):
    t = T[lang]
    fig, ax = canvas(H)
    header(ax, t['title'], t['sub'])
    panel_a(fig, ax, t)
    line(ax, [(787, 105), (787, 600)], RULE, .8)
    panel_b(fig, ax, t)
    rule(ax, 35, 1540, 608)
    block(ax, 35, 618, t['foot'], 1505, size=7.8, color=MUTED)
    return fig


def draw(lang):
    return run(build, 'sediment_adapt', lang,
               'Curves of the concentration of suspended sediment approaching the equilibrium over the adaptation length '
               'L = q / (beta w_f), and of L versus grain size with the Rubey settling velocity and the floc band of mud. '
               'Not solver output.')
