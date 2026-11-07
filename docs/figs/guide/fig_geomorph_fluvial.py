"""Graphs for bedload formulas (geomorph.md, f_fluvial).

(a) transverse bed slope at which the cross-channel bedload of the direction
    law q_b/|q_b| = t + r n - gamma grad z vanishes in a uniform bend:
    S_n = r / gamma, r = min(N* h/R, sec_rmax), gamma = sqrt(tau*c / (mu_s mu_k tau*));
(b) resistance-partition factor of f_taupart, phi = (1 + 6.76 (h/D84)^(-5/3))^(-e/2);
(c) bedload capacity with phi relative to without (Ashida-Michiue, f_qbform = 1).
Closed forms evaluated for illustrative values (code: m_geomorph_fluvial.f90,
m_geomorph.f90 taufac_h); not solver output.

Generate: python docs/figs/make_guide_figs.py geomorph_fluvial
"""
import numpy as np
from _geomorph import (canvas, header, panel, rule, chart, run, text, block, line,
                       INK, MUTED, RULE, SED, GREEN, BLUE, ORANGE)

H = 676
NSTAR, MUS, MUK, RMAX, TAUSC = 7.0, 1.0, 0.45, 1.0, 0.05

T = {
 'ja': {
    'title': '掃流砂の式の振る舞い  |  湾曲部の横断勾配・急勾配礫床の抵抗分割',
    'sub': '式の曲線(既定値と説明用の値)。計算結果ではない。',
    'a': '(a) 湾曲部で横断方向の流砂が釣り合う勾配',
    'ax': '水深 / 曲率半径  h / R', 'ay': '横断勾配 S_n = r / γ',
    'tau': 'τ*/τ*c = {:g}', 'cap': '|r| ≤ sec_rmax(= 1)で頭打ち', 'rep': '安息角 30° の勾配(f_repose の既定)',
    'a_note': 'r = N* h/R(N* = 7)、γ = √(τ*c / (μs μk τ*))(μs = 1.0、μk = 0.45)。fluv_slope だけ(r = 0)では平坦のまま、f_secflow だけ(γ = 0)では釣り合う勾配がない。',
    'b': '(b) f_taupart の係数 φ(h)', 'bx': '相対水深 h / D84', 'by': '流砂量式に渡す τ* の倍率 φ',
    'e': 'e = {:g}', 'edef': 'e = 1.5(既定 taupart_e)',
    'b_note': 'φ = {1 + 6.76 (h/D84)^(−5/3)}^(−e/2)。深い流れでは 1、礫の大きさ程度の浅い流れでは τ* が大きく減る。',
    'c': '(c) 抵抗分割による掃流砂の容量の比', 'cx': '相対水深 h / D84', 'cy': '容量の比 q_b(φτ*) / q_b(τ*)',
    'k': 'τ*/τ*c = {:g}', 'ktitle': '分割なしの τ*',
    'c_note': '芦田・道上(f_qbform = 1)で、同じ流れ(n・V・h)の分割あり・なしを比べた比。e = 1.5。φ τ* ≤ τ*c では動かない。',
    'foot': '(a) は式から導いた目安で、実際の河床形状は流れとの相互作用で決まる。(b)(c) の出典は表の f_taupart の行と sediment.md §3。',
 },
 'en': {
    'title': 'Behaviour of the bedload equations  |  Transverse slope in bends, resistance partition on steep gravel beds',
    'sub': 'Curves of the equations (defaults and illustrative values); not computed results.',
    'a': '(a) Balancing transverse slope in a bend',
    'ax': 'depth / radius of curvature  h / R', 'ay': 'transverse slope S_n = r / γ',
    'tau': 'τ*/τ*c = {:g}', 'cap': 'capped by |r| ≤ sec_rmax (= 1)', 'rep': 'slope of a 30° repose angle (f_repose default)',
    'a_note': 'r = N* h/R (N* = 7), γ = √(τ*c / (μs μk τ*)) (μs = 1.0, μk = 0.45). With fluv_slope alone (r = 0) the bed stays flat; with f_secflow alone (γ = 0) no slope balances.',
    'b': '(b) Factor φ(h) of f_taupart', 'bx': 'relative depth h / D84', 'by': 'factor φ on τ*',
    'e': 'e = {:g}', 'edef': 'e = 1.5 (default taupart_e)',
    'b_note': 'φ = {1 + 6.76 (h/D84)^(−5/3)}^(−e/2). It is 1 in deep flow and strongly reduces τ* in flows as shallow as the gravel.',
    'c': '(c) Capacity ratio with the partition', 'cx': 'relative depth h / D84', 'cy': 'capacity ratio q_b(φτ*) / q_b(τ*)',
    'k': 'τ*/τ*c = {:g}', 'ktitle': 'τ* without partition',
    'c_note': 'Ashida–Michiue (f_qbform = 1), same flow (n, V, h) with and without the partition, e = 1.5. No transport while φ τ* ≤ τ*c.',
    'foot': '(a) is an estimate derived from the equations; the actual bed shape results from the interaction with the flow. Sources of (b)(c): the f_taupart row of the table and sediment.md §3.',
 },
}


def qb_am(taus):
    taus = np.asarray(taus, float)
    out = np.zeros_like(taus)
    m = taus > TAUSC
    out[m] = 17.0 * taus[m] ** 1.5 * (1 - TAUSC / taus[m]) * (1 - np.sqrt(TAUSC / taus[m]))
    return out


def phi(x, e):
    return (1 + 6.76 * x ** (-5.0 / 3.0)) ** (-e / 2)


def build(lang):
    t = T[lang]
    fig, ax = canvas(H)
    header(ax, t['title'], t['sub'])
    # (a) balanced transverse slope.
    panel(ax, 35, 108, t['a'])
    hr = np.linspace(0, 0.18, 300)
    c = chart(fig, 100, 150, 380, 270, (0, 0.18), (0, 1.25), xlabel=t['ax'], ylabel=t['ay'])
    for k, col, pos in [(1.5, GREEN, (0.176, 0.84)), (3.0, SED, (0.176, 1.18)), (6.0, BLUE, (0.088, 1.12))]:
        gam = np.sqrt(1.0 / (MUS * MUK * k))
        r = np.minimum(NSTAR * hr, RMAX)
        c.plot(hr, r / gam, color=col, lw=2.0 if k == 3.0 else 1.6)
        c.text(pos[0], pos[1], t['tau'].format(k), fontsize=7.4, color=col, ha='right', va='bottom')
    c.axvline(RMAX / NSTAR, color=MUTED, lw=.8, ls=':')
    c.text(RMAX / NSTAR - 0.003, 0.08, t['cap'], fontsize=7.4, color=MUTED, ha='right')
    c.axhline(np.tan(np.radians(30)), color=ORANGE, lw=.9, ls='--')
    c.text(0.004, np.tan(np.radians(30)) + 0.02, t['rep'], fontsize=7.4, color=ORANGE, va='bottom')
    block(ax, 35, 500, t['a_note'], 470, size=7.9)
    # (b) phi(h/D84).
    panel(ax, 545, 108, t['b'])
    x = np.logspace(np.log10(0.5), 2, 300)
    c = chart(fig, 610, 150, 380, 270, (0.5, 100), (0, 1.05), xlabel=t['bx'], ylabel=t['by'])
    c.set_xscale('log')
    for e, col, lw in [(1.33, GREEN, 1.4), (1.5, SED, 2.2), (2.0, BLUE, 1.4)]:
        c.plot(x, phi(x, e), color=col, lw=lw, label=t['edef'] if e == 1.5 else t['e'].format(e))
    c.legend(loc='lower right', fontsize=7.6, frameon=False)
    block(ax, 545, 500, t['b_note'], 470, size=7.9)
    # (c) capacity ratio.
    panel(ax, 1055, 108, t['c'])
    c = chart(fig, 1120, 150, 400, 270, (0.5, 100), (0, 1.05), xlabel=t['cx'], ylabel=t['cy'])
    c.set_xscale('log')
    for k, col in [(2, GREEN), (4, SED), (8, BLUE)]:
        taus = k * TAUSC
        c.plot(x, qb_am(phi(x, 1.5) * taus) / qb_am(np.array([taus]))[0], color=col, lw=2.0 if k == 4 else 1.6,
               label=t['k'].format(k))
    c.legend(loc='lower right', fontsize=7.6, frameon=False, title=t['ktitle'], title_fontsize=7.6)
    block(ax, 1055, 500, t['c_note'], 485, size=7.9)
    line(ax, [(527, 105), (527, 604)], RULE, .8)
    line(ax, [(1037, 105), (1037, 604)], RULE, .8)
    rule(ax, 35, 1540, 612)
    block(ax, 35, 622, t['foot'], 1505, size=7.9, color=MUTED)
    return fig


def draw(lang):
    return run(build, 'geomorph_fluvial', lang,
               'Curves of the bedload equations: transverse slope balancing the bend direction law (fluv_slope, '
               'f_secflow), the resistance-partition factor of f_taupart and its effect on the Ashida-Michiue capacity. '
               'Closed forms for illustrative values.')
