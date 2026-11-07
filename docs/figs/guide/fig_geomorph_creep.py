"""Graphs for hillslope creep and soil production (geomorph.md, f_creep / f_wthr).

(a) depth-dependent creep factor 1 - exp(-H/H_c) (creep_hstar);
(b) soil production W0 exp(-H/H*) (wthr_p0, wthr_sdstar) and the steady soil
    thickness H_ss = H* ln(W0/U) under uplift U (creep_hstar > 0);
(c) explicit stability limit of creep: largest dts for a cell size, from the
    positivity bound of m_geomorph_creep (9-point default: dts <= 0.3 dx^2 / D
    on square cells; 5-point: 0.25 dx^2 / D).
Closed-form curves for illustrative values; not solver output.

Generate: python docs/figs/make_guide_figs.py geomorph_creep
"""
import numpy as np
from _geomorph import (canvas, header, panel, rule, chart, run, text, block, line,
                       INK, MUTED, RULE, SED, GREEN, BLUE, ORANGE)

H = 706
W0, HSTAR = 50.0, 0.5            # mm/kyr, m (defaults wthr_p0, wthr_sdstar)

T = {
 'ja': {
    'title': '斜面クリープと土層生成の式  |  深さ依存・定常の土層厚・陽解法の安定条件',
    'sub': '式の曲線(説明用の値)。計算結果ではない。',
    'a': '(a) 深さ依存クリープの係数  creep_hstar = H_c',
    'ax': '土層厚 / H_c', 'ay': '流量の係数 1 − exp(−H/H_c)',
    'lin': 'creep_hstar = 0: 従来の線形拡散(係数 1。sd によらない)',
    'bare': '裸岩(H = 0)からは運ばない',
    'b': '(b) 土層の生成と、隆起の下の定常の土層厚',
    'bx': '土層厚 H (m)', 'by': '速度 (mm/kyr)',
    'prod': '生成 W0 exp(−H/H*)(W0 = 50 mm/kyr、H* = 0.5 m)', 'U': 'U = {} mm/kyr',
    'ss': '交点 = 定常の土層厚\nH_ss = H* ln(W0/U)', 'none': 'U ≥ W0 では交点がない\n= 定常の土層厚がない', 'w0': 'W0(裸岩での生成)',
    'c': '(c) クリープの陽解法の安定条件',
    'cx': '格子幅 Δx (m)', 'cy': '1 回の更新の dts の上限 (年)',
    'nine': '9 点(既定 creep_diagratio = 1/3): dts ≤ 0.3 Δx²/D', 'five': '5 点(creep_diagratio = 0): dts ≤ 0.25 Δx²/D',
    'dlab': 'D = {} m²/yr',
    'c_note': 'dts = dtw × morfac、正方格子。上限を超える設定は開始時に停止する(上限は「creep stability dt limit」として表示)。',
    'foot': '(a)(b) は creep_hstar > 0 の深さ依存クリープと風化 f_wthr の式、(b) の定常は隆起 U と生成が釣り合う土層厚。(c) の D は creep_d(深さ依存でも実効の係数は D 以下)。',
 },
 'en': {
    'title': 'Equations of hillslope creep and soil production  |  Depth dependence, steady soil thickness, explicit stability',
    'sub': 'Curves of the equations for illustrative values; not computed results.',
    'a': '(a) Depth-dependent creep factor (creep_hstar)',
    'ax': 'soil depth / H_c', 'ay': 'flux factor 1 − exp(−H/H_c)',
    'lin': 'creep_hstar = 0: linear diffusion (factor 1, independent of sd)',
    'bare': 'nothing moves from bare rock (H = 0)',
    'b': '(b) Soil production and steady soil depth',
    'bx': 'soil depth H (m)', 'by': 'rate (mm/kyr)',
    'prod': 'production W0 exp(−H/H*) (W0 = 50 mm/kyr, H* = 0.5 m)', 'U': 'U = {} mm/kyr',
    'ss': 'crossing = steady soil depth\nH_ss = H* ln(W0/U)', 'none': 'no crossing for U ≥ W0\n= no steady soil depth', 'w0': 'W0 (production on bare rock)',
    'c': '(c) Stability limit of explicit creep',
    'cx': 'cell size Δx (m)', 'cy': 'upper limit of dts per update (yr)',
    'nine': '9-point (default creep_diagratio = 1/3): dts ≤ 0.3 Δx²/D', 'five': '5-point (creep_diagratio = 0): dts ≤ 0.25 Δx²/D',
    'dlab': 'D = {} m²/yr',
    'c_note': 'dts = dtw × morfac, square cells. Settings above the limit stop at start-up; the limit is printed as "creep stability dt limit".',
    'foot': '(a)(b): equations of depth-dependent creep (creep_hstar > 0) and weathering f_wthr; the steady state in (b) is the soil depth at which production balances the uplift U. D in (c) is creep_d (the effective coefficient of depth-dependent creep is at most D).',
 },
}


def build(lang):
    t = T[lang]
    fig, ax = canvas(H)
    header(ax, t['title'], t['sub'])
    # (a) depth-dependent factor.
    panel(ax, 35, 108, t['a'])
    hh = np.linspace(0, 4, 200)
    c = chart(fig, 100, 150, 380, 300, (0, 4), (0, 1.1), xlabel=t['ax'], ylabel=t['ay'])
    c.plot(hh, 1 - np.exp(-hh), color=SED, lw=2.0)
    c.axhline(1.0, color=MUTED, lw=1.2, ls='--')
    c.text(3.95, 1.03, t['lin'], fontsize=7.6, color=MUTED, ha='right', va='bottom')
    c.plot([0], [0], 'o', color=SED, ms=5, zorder=5)
    c.annotate(t['bare'], xy=(0.02, 0.01), xytext=(0.45, 0.18), fontsize=7.8, color=SED,
               arrowprops=dict(arrowstyle='-|>', color=SED, lw=.8))
    # (b) soil production and steady soil depth.
    panel(ax, 545, 108, t['b'])
    hs = np.linspace(0, 2.5, 300)
    prod = W0 * np.exp(-hs / HSTAR)
    c = chart(fig, 610, 150, 380, 300, (0, 2.5), (0, 72), xlabel=t['bx'], ylabel=t['by'])
    c.plot(hs, prod, color=GREEN, lw=2.0)
    c.text(0.08, 70, t['prod'], fontsize=7.6, color=GREEN, va='top')
    for u, col in [(5, BLUE), (10, BLUE), (20, BLUE)]:
        hss = HSTAR * np.log(W0 / u)
        c.axhline(u, color=col, lw=.9, ls=':')
        c.plot([hss], [u], 'o', color=ORANGE, ms=5, zorder=5)
        c.text(2.45, u + 0.8, t['U'].format(u), fontsize=7.4, color=BLUE, ha='right', va='bottom')
    c.annotate(t['ss'], xy=(HSTAR * np.log(W0 / 10), 10), xytext=(1.05, 33), fontsize=7.8, color=ORANGE,
               arrowprops=dict(arrowstyle='-|>', color=ORANGE, lw=.8))
    c.annotate(t['w0'], xy=(0.0, W0), xytext=(0.28, 58), fontsize=7.6, color=GREEN, va='center',
               arrowprops=dict(arrowstyle='-|>', color=GREEN, lw=.8))
    c.text(1.3, 50, t['none'], fontsize=7.6, color=MUTED, va='top')
    # (c) stability limit of explicit creep.
    panel(ax, 1055, 108, t['c'])
    dx = np.logspace(0, 2, 100)
    c = chart(fig, 1120, 150, 400, 300, (1, 100), (1, 1e7), xlabel=t['cx'], ylabel=t['cy'])
    c.set_xscale('log'); c.set_yscale('log')
    for d, col, lw in [(0.001, GREEN, 1.6), (0.005, SED, 2.0), (0.05, BLUE, 1.6)]:
        c.plot(dx, 0.3 * dx ** 2 / d, color=col, lw=lw)
        c.text(14, 0.3 * 14 ** 2 / d, t['dlab'].format(d), fontsize=7.4, color=col, va='center', ha='center',
               bbox=dict(fc='white', ec='none', pad=1.0))
    c.plot(dx, 0.25 * dx ** 2 / 0.005, color=SED, lw=1.2, ls='--')
    line(ax, [(1060, 516), (1090, 516)], SED, 2.0)
    text(ax, 1098, 508, t['nine'], size=7.8)
    line(ax, [(1060, 540), (1090, 540)], SED, 1.2, ls='--')
    text(ax, 1098, 532, t['five'], size=7.8)
    block(ax, 1055, 562, t['c_note'], 485, size=7.8, color=MUTED)
    line(ax, [(527, 105), (527, 626)], RULE, .8)
    line(ax, [(1037, 105), (1037, 626)], RULE, .8)
    rule(ax, 35, 1540, 634)
    block(ax, 35, 644, t['foot'], 1505, size=7.9, color=MUTED)
    return fig


def draw(lang):
    return run(build, 'geomorph_creep', lang,
               'Curves of the depth-dependent creep factor, soil production and steady soil depth under uplift, '
               'and the explicit stability limit of creep versus cell size. Closed forms for illustrative values.')
