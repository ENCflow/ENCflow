"""Bedrock incision f_rockinc and rock erosion by debris flows rock_kdb (geomorph.md).

(a) the three actions on a bedrock channel cell: plucking (rock -> mobile layer,
z unchanged), abrasion by moving gravel (fines leave, z lowered) and cover by
the mobile layer; (b) exposure exp(-H/H*) and availability 1 - exp(-H/H*);
(c) steady abrasion beta q_s (1 - q_s/q_c): the tools-and-cover hump;
(d) the debris-flow term and its gates. Curves are the closed forms quoted in
the text; the section is a schematic, not solver output.

Generate: python docs/figs/make_guide_figs.py geomorph_rockinc
"""
import numpy as np
from _geomorph import (canvas, header, panel, rule, box, poly, dim, chart, badge, run,
                       text, block, line, arrow, INK, MUTED, RULE,
                       SOIL, ROCK, WATER, BLUE, SED, MOVING, GREEN, ORANGE, PANEL)

H = 1075
GRAVEL = '#cbb07a'

T = {
 'ja': {
    'title': '流水による岩盤下刻  |  剥離・研磨・被覆と薄層の輸送(f_rockinc)',
    'sub': '岩盤面は z − sd で表し、新しい状態量は持たない。f_fluvial = 1 が必須(土石流の項は f_debris = 1)。断面は説明用で、計算結果ではない。',
    'a': '(a) 1 つの渓流セルで起きること',
    'water': '流れ(τ_b、掃流砂容量 q_c)', 'cover': '可動層 sd(被覆。厚さ H)', 'rockl': '岩盤(上面 R = z − sd)',
    'p_t': '剥離', 'p_b': 'τ_b > τ_c で裸岩が k_p (τ_b/τ_c − 1)^m の速さで削れる。\n→ 同じ厚さの可動層になる(sd が増え、z は変わらない)',
    'a_t': '研磨(tools)', 'a_b': '運ばれる礫が床を叩く(β q_c F_s の速さ)。\n→ 細粒分は系外へ(z が下がる。被覆に加えない)',
    'c_t': '被覆', 'c_b': '剥離・研磨とも露出率 exp(−H/H*) を掛ける\n(H* = rock_hstar。岩盤面の起伏の高さの目安)',
    't_t': '薄層の輸送', 't_b': '掃流砂の流出に利用可能率 F_s = 1 − exp(−H/H*) を掛ける\n(岩盤が削れないセルでも薄い層の輸送が変わる)',
    'b': '(b) 露出率と利用可能率', 'bx': 'H / H*(可動層の厚さ ÷ 被覆の長さ)', 'by': '割合',
    'exp': '露出率 exp(−H/H*)(下刻を許す割合)', 'avail': '利用可能率 1 − exp(−H/H*)(運べる割合)',
    'c': '(c) 定常の研磨速度: 道具と被覆の山形', 'cx': '流砂量 / 容量  q_s / q_c', 'cy': 'E / (β q_c)',
    'hump': 'E = β q_s (1 − q_s/q_c)', 'tools': '道具が足りない', 'covered': '全被覆(E = 0)', 'max': 'q_s/q_c = 0.5 で最大',
    'c_note': '定常では利用可能率 = q_s/q_c(被覆率が供給比に一致)、露出率 = 1 − q_s/q_c。',
    'd': '(d) 土石流による岩盤侵食  rock_kdb > 0(f_debris = 1、morfac = 1)',
    'd_eq': 'τ_d = ρ_w (1 + sC) g_e h_t tan θ(準静的な駆動応力。h_t = h + hs、θ は流向の河床勾配で下りだけ)\n'
            'E_d = k_d (τ_d / τ_cd − 1)^{m_d} × exp(−H/H*)  → 削った岩は同じ厚さの可動層へ(z は変わらない)',
    'gate1': '濃い混合体 C ≥ db_cmin', 'gate2': '流れている |V| ≥ db_vstop',
    'gate3': '希薄な尾部・清水・止まった土塊は削らない',
    'd_note': '流水の項(rock_kp・rock_beta)とは同じ計算で併用しない(出水の計算と f_state_restore = 2 で交互に回す)。'
              'rock_kp・rock_tauc・rock_beta・rock_kdb・rock_taucdb は文献に標準値のない校正値。',
    'foot': '剥離は露出率を厳密に積分するので dt_geomorph・morfac によらず安定。薄い層の排出は陽的で、終了時の「max thin-layer drainage rate x dts」≤ 0.5 が目安(本文)。',
 },
 'en': {
    'title': 'Bedrock incision by flowing water  |  Plucking, abrasion, cover and thin-layer transport (f_rockinc)',
    'sub': 'The bedrock surface is z − sd; no new state variable. Requires f_fluvial = 1 (the debris-flow term: f_debris = 1). Illustrative section, not computed results.',
    'a': '(a) What happens in one channel cell',
    'water': 'flow (τ_b, bedload capacity q_c)', 'cover': 'mobile layer sd (cover, thickness H)', 'rockl': 'bedrock (surface R = z − sd)',
    'p_t': 'Plucking', 'p_b': 'bare rock erodes at k_p (τ_b/τ_c − 1)^m when τ_b > τ_c\n→ mobile layer of the same thickness\n(sd up, z unchanged)',
    'a_t': 'Abrasion (tools)', 'a_b': 'moving gravel hits the bed at the rate β q_c F_s\n→ fines leave the system\n(z lowered; not added to the cover)',
    'c_t': 'Cover', 'c_b': 'plucking and abrasion are scaled by the exposure\nexp(−H/H*) (H* = rock_hstar, about the bed relief)',
    't_t': 'Thin-layer transport', 't_b': 'bedload outflow is scaled by the availability\nF_s = 1 − exp(−H/H*) (also where rock does not erode)',
    'b': '(b) Exposure and availability', 'bx': 'H / H* (mobile-layer thickness ÷ cover length)', 'by': 'fraction',
    'exp': 'exposure exp(−H/H*) (share that may incise)', 'avail': 'availability 1 − exp(−H/H*) (share that can move)',
    'c': '(c) Steady abrasion: the tools-and-cover hump', 'cx': 'supply / capacity  q_s / q_c', 'cy': 'E / (β q_c)',
    'hump': 'E = β q_s (1 − q_s/q_c)', 'tools': 'too few tools', 'covered': 'fully covered (E = 0)', 'max': 'maximum at q_s/q_c = 0.5',
    'c_note': 'At steady state, availability = q_s/q_c (cover fraction equals the supply ratio) and exposure = 1 − q_s/q_c.',
    'd': '(d) Rock erosion by debris flows  rock_kdb > 0 (f_debris = 1, morfac = 1)',
    'd_eq': 'τ_d = ρ_w (1 + sC) g_e h_t tan θ (quasi-static driving stress; h_t = h + hs, θ = downhill bed slope along the flow)\n'
            'E_d = k_d (τ_d / τ_cd − 1)^{m_d} × exp(−H/H*)  → the eroded rock becomes mobile layer of the same thickness (z unchanged)',
    'gate1': 'dense mixture C ≥ db_cmin', 'gate2': 'flowing |V| ≥ db_vstop',
    'gate3': 'dilute tails, clear water and stopped deposits do not erode',
    'd_note': 'Not combined with the flowing-water terms (rock_kp, rock_beta) in the same run (alternate with flood runs via f_state_restore = 2). '
              'rock_kp, rock_tauc, rock_beta, rock_kdb and rock_taucdb are calibration values without standard literature values.',
    'foot': 'Plucking integrates the exposure exactly, so it is stable for any dt_geomorph or morfac. Thin-layer drainage is explicit; keep the end-of-run "max thin-layer drainage rate x dts" ≤ 0.5 (see text).',
 },
}


def panel_cell(ax, t):
    from matplotlib.patches import Ellipse
    panel(ax, 35, 108, t['a'])
    # Section along a channel cell row: water, patchy gravel cover, bedrock.
    x0, x1 = 60, 760
    rock_top = 292
    xs = np.linspace(x0, x1, 300)
    rough = rock_top + 6 * np.sin((xs - x0) / 23.0) + 4 * np.sin((xs - x0) / 9.0)
    cov = np.zeros_like(xs)
    m = (xs > 380) & (xs < 720)
    cov[m] = 28 * np.sin(np.pi * (xs[m] - 380) / 340) ** .6
    poly(ax, [(x0, 165), (x1, 165)] + list(zip(xs[::-1], (rough - cov)[::-1])), WATER, z=0)
    line(ax, [(x0, 165), (x1, 165)], BLUE, 1.2, z=5)
    poly(ax, list(zip(xs, rough)) + [(x1, 360), (x0, 360)], ROCK, z=1)
    line(ax, list(zip(xs, rough)), '#7d7a73', 1.0, z=5)
    poly(ax, list(zip(xs, rough - cov)) + list(zip(xs[::-1], rough[::-1])), GRAVEL, z=2)
    for xc in np.arange(392, 712, 15):
        if np.interp(xc, xs, cov) > 7:
            yc = float(np.interp(xc, xs, rough - cov / 2))
            ax.add_patch(Ellipse((xc, yc), 10, 7, facecolor='#b0925b', edgecolor='none', zorder=3))
    arrow(ax, [(80, 186), (190, 186)], BLUE, lw=1.6, size=10)
    text(ax, 200, 178, t['water'], size=8.2, color=BLUE)
    # 1 plucking: a block lifted from bare rock into the mobile layer.
    box(ax, 140, rock_top - 4, 36, 16, face='white', edge=SED, lw=.9, z=6, hatch='///')
    arrow(ax, [(158, rock_top - 8), (205, rock_top - 40)], SED, lw=1.4, size=9)
    badge(ax, 120, rock_top - 32, '1', r=10, size=7.6)
    # 2 abrasion: a moving gravel hits the floor; fines leave the system.
    ax.add_patch(Ellipse((300, rock_top - 12), 14, 10, facecolor='#b0925b', edgecolor=SED, zorder=7))
    arrow(ax, [(262, rock_top - 34), (294, rock_top - 15)], SED, lw=1.2, size=8)
    for k in range(4):
        ax.plot(318 + 8 * k, rock_top - 6 - 5 * k, 'o', ms=1.6, color='#7d7a73', zorder=7)
    arrow(ax, [(322, rock_top - 8), (352, rock_top - 32)], MUTED, lw=1.0, size=7, ls='--')
    badge(ax, 250, rock_top - 50, '2', r=10, size=7.6)
    # 3 cover; 4 thin-layer transport along the gravel patch.
    badge(ax, 545, rock_top - 50, '3', r=10, size=7.6)
    line(ax, [(545, rock_top - 40), (548, rock_top - 24)], MUTED, .7, z=9)
    arrow(ax, [(600, rock_top - 40), (700, rock_top - 40)], SED, lw=1.5, size=9)
    badge(ax, 722, rock_top - 40, '4', r=10, size=7.6)
    for k, (key, face) in enumerate([('cover', GRAVEL), ('rockl', ROCK)]):
        lx = 60 + 340 * k
        box(ax, lx, 374, 24, 14, face=face)
        text(ax, lx + 32, 370, t[key], size=8.0)
    y = 404
    for k, (tt, bb, col) in enumerate([('p_t', 'p_b', SED), ('a_t', 'a_b', SED), ('c_t', 'c_b', GREEN), ('t_t', 't_b', SED)]):
        badge(ax, 70, y + 10, str(k + 1), r=10, size=7.6)
        text(ax, 88, y, t[tt], size=8.6, weight='bold', color=col)
        a = block(ax, 262, y + 1, t[bb].replace('\n', ' '), 508, size=8.0)
        y += 21 * (a.get_text().count('\n') + 1) + 7


def panel_exposure(fig, ax, t):
    panel(ax, 805, 108, t['b'])
    hh = np.linspace(0, 4, 200)
    c = chart(fig, 880, 150, 620, 260, (0, 4), (0, 1.05), xlabel=t['bx'], ylabel=t['by'])
    c.plot(hh, np.exp(-hh), color=ORANGE, lw=2.0)
    c.plot(hh, 1 - np.exp(-hh), color=SED, lw=2.0, ls='--')
    c.text(1.6, .21, t['exp'], color=ORANGE, fontsize=8, va='bottom')
    c.text(1.6, .78, t['avail'], color=SED, fontsize=8, va='top')


def panel_hump(fig, ax, t):
    y0 = 628
    panel(ax, 35, y0, t['c'])
    r = np.linspace(0, 1.4, 300)
    e = np.where(r < 1, r * (1 - r), 0)
    c = chart(fig, 110, y0 + 42, 620, 210, (0, 1.4), (0, .3), xlabel=t['cx'], ylabel=t['cy'])
    c.plot(r, e, color=SED, lw=2.2)
    c.axvline(.5, color=MUTED, lw=.8, ls=':')
    c.text(.52, .29, t['max'], fontsize=8, color=MUTED, va='top')
    c.text(.04, .02, t['tools'], fontsize=8, color=MUTED)
    c.text(1.02, .02, t['covered'], fontsize=8, color=MUTED)
    c.text(.76, .22, t['hump'], fontsize=8.4, color=SED)
    block(ax, 35, y0 + 315, t['c_note'], 735, size=8.3)


def panel_debris(ax, t):
    y0 = 628
    panel(ax, 805, y0, t['d'])
    box(ax, 805, y0 + 40, 735, 112, face=PANEL)
    block(ax, 818, y0 + 48, t['d_eq'], 712, size=8.1)
    y = y0 + 168
    box(ax, 818, y, 250, 30, face='white', edge=GREEN, lw=1.0)
    text(ax, 943, y + 15, t['gate1'], size=8.2, color=GREEN, ha='center', va='center')
    text(ax, 1082, y + 15, '+', size=10, ha='center', va='center', weight='bold')
    box(ax, 1096, y, 250, 30, face='white', edge=GREEN, lw=1.0)
    text(ax, 1221, y + 15, t['gate2'], size=8.2, color=GREEN, ha='center', va='center')
    arrow(ax, [(1354, y + 15), (1384, y + 15)], GREEN, lw=1.4, size=9)
    text(ax, 1390, y + 15, 'E_d > 0', size=8.4, color=GREEN, va='center')
    block(ax, 818, y + 44, t['gate3'], 712, size=8.1, color=MUTED)
    block(ax, 805, y + 80, t['d_note'], 735, size=8.2)


def build(lang):
    t = T[lang]
    fig, ax = canvas(H)
    header(ax, t['title'], t['sub'])
    panel_cell(ax, t)
    line(ax, [(787, 105), (787, 1008)], RULE, .8)
    panel_exposure(fig, ax, t)
    rule(ax, 35, 1540, 612)
    panel_hump(fig, ax, t)
    panel_debris(ax, t)
    rule(ax, 35, 1540, 1016)
    block(ax, 35, 1026, t['foot'], 1505, size=8.1, color=MUTED)
    return fig


def draw(lang):
    return run(build, 'geomorph_rockinc', lang,
               'Schematic of bedrock incision f_rockinc (plucking, abrasion, cover, thin-layer transport), the '
               'exposure and availability functions, the steady tools-and-cover hump, and the gates of the '
               'debris-flow term rock_kdb. Not solver output.')
