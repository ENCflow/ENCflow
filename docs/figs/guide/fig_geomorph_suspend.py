"""Graphs for suspended sediment (geomorph.md, f_suspend).

(a) settling velocity of the Rubey formula versus grain size (used when
    susp_wf = 0), with the effective floc settling velocity band given
    directly for cohesive mud (1e-4 to 1e-3 m/s);
(b) equilibrium concentration c_eq versus tau* for f_esform = 1 (linear,
    susp_esa = 1e-4, tau*c = 0.05) and f_esform = 2 (Itakura-Kishi).
Same formulas as src/m_sedform.f90 (sed_rubey_wf, sed_ceq, sed_ceq_itakura),
evaluated for illustrative values; not solver output.

Generate: python docs/figs/make_guide_figs.py geomorph_suspend
"""
import math
import numpy as np
from _geomorph import (canvas, header, panel, rule, chart, run, text, block, line,
                       INK, MUTED, RULE, SED, GREEN, BLUE, ORANGE)

H = 676
S, G, NU = 1.65, 9.8, 1.0e-6
IK_K, IK_A, IK_B, IK_E0 = 0.008, 0.14, 0.143, 0.5

T = {
 'ja': {
    'title': '浮遊砂の式の振る舞い  |  沈降速度(Rubey 式)と平衡濃度(f_esform)',
    'sub': 'src/m_sedform.f90 と同じ式を説明用の値で評価した曲線。計算結果ではない。',
    'a': '(a) 沈降速度 w_f(susp_wf = 0 のとき d50 から Rubey 式で導出)',
    'ax': '粒径 d (m)', 'ay': '沈降速度 w_f (m/s)',
    'rubey': 'Rubey 式(水中比重 1.65、ν = 10⁻⁶ m²/s)',
    'floc': '泥(粘着性)の実効沈降速度\n10⁻⁴〜10⁻³ m/s を\nsusp_wf に直接与える',
    'clay': '粘土', 'silt': 'シルト', 'sand': '砂',
    'def': '既定 susp_d50 = 0.2 mm\n→ w_f ≈ 2.5 cm/s',
    'a_note': '粘土の粒径では、Rubey 式の値はフロックの実効値より 1〜2 桁小さく、ほとんど沈降しない計算になる。泥は susp_wf を直接与える(本文「泥(粘着性)」)。',
    'b': '(b) 平衡濃度 c_eq と無次元掃流力 τ*',
    'bx': '無次元掃流力 τ*', 'by': '平衡濃度 c_eq(体積濃度)',
    'lin': 'f_esform = 1(既定): esa (τ*/τ*c − 1)、esa = 10⁻⁴',
    'ik': 'f_esform = 2(板倉・岸)、{} mm',
    'b_note': '巻き上げ E = w_f c_eq。mm の値は d50(susp_d50)。板倉・岸は浮上量が沈降を上回るまで 0 で、粒径が大きいほど立ち上がりが遅い(校正パラメータなし)。f_esform = 1 は τ*c を超えると直線に増え、esa は校正値。',
    'foot': '濃度は水の体積あたり(hs を矩形換算水深で割った値)。高濃度の泥水流(密度流)は対象外。',
 },
 'en': {
    'title': 'Behaviour of the suspended-sediment equations  |  Settling velocity (Rubey) and equilibrium concentration (f_esform)',
    'sub': 'Curves of the same formulas as src/m_sedform.f90 for illustrative values; not computed results.',
    'a': '(a) Settling velocity w_f (Rubey formula; susp_wf = 0)',
    'ax': 'grain size d (m)', 'ay': 'settling velocity w_f (m/s)',
    'rubey': 'Rubey formula (submerged specific gravity 1.65, ν = 10⁻⁶ m²/s)',
    'floc': 'effective settling of cohesive mud (flocs):\ngive 10⁻⁴–10⁻³ m/s directly in susp_wf',
    'clay': 'clay', 'silt': 'silt', 'sand': 'sand',
    'def': 'default susp_d50 = 0.2 mm\n→ w_f ≈ 2.5 cm/s',
    'a_note': 'At clay sizes the Rubey value is one to two orders of magnitude below the effective floc value, so mud would hardly settle. Give susp_wf directly for mud ("mud (cohesive)" in the text).',
    'b': '(b) Equilibrium concentration c_eq and τ*',
    'bx': 'Shields number τ*', 'by': 'c_eq (volume concentration)',
    'lin': 'f_esform = 1 (default): esa (τ*/τ*c − 1), esa = 10⁻⁴',
    'ik': 'f_esform = 2 (Itakura–Kishi), {} mm',
    'b_note': 'Entrainment E = w_f c_eq; mm values are d50 (susp_d50). Itakura–Kishi is 0 until the upward flux exceeds settling, and rises later for coarser grains (no calibration parameter). f_esform = 1 grows linearly above τ*c; esa is a calibration value.',
    'foot': 'Concentrations are per volume of water (hs divided by the rectangular-equivalent depth). High-concentration mud flows (density currents) are out of scope.',
 },
}


def rubey(d):
    d = np.asarray(d, float)
    bb = 36 * NU ** 2 / (S * G * d ** 3)
    return (np.sqrt(2.0 / 3.0 + bb) - np.sqrt(bb)) * np.sqrt(S * G * d)


def ceq_ik(d, taus):
    wf = float(rubey(d))
    out = []
    for ts in taus:
        ap = IK_B / ts - 1 / IK_E0
        if ap > 20:
            out.append(0.0); continue
        ratio = math.exp(-ap ** 2) / (math.sqrt(math.pi) * math.erfc(ap))
        om = ts / IK_B * ratio + ts / (IK_B * IK_E0) - 1
        us = math.sqrt(ts * S * G * d)
        q = IK_K * (IK_A / (S + 1) * (S * G * d / us) * om - wf)
        out.append(max(q, 0.0) / wf)
    return np.array(out)


def build(lang):
    t = T[lang]
    fig, ax = canvas(H)
    header(ax, t['title'], t['sub'])
    # (a) Rubey settling velocity.
    panel(ax, 35, 108, t['a'])
    d = np.logspace(-6, -2, 300)
    c = chart(fig, 110, 150, 620, 300, (1e-6, 1e-2), (1e-7, 1), xlabel=t['ax'], ylabel=t['ay'])
    c.set_xscale('log'); c.set_yscale('log')
    c.axhspan(1e-4, 1e-3, color='#e7f0e3', lw=0)
    c.axvspan(1e-6, 4e-6, color='#f4f3ee', lw=0)
    c.axvspan(6.3e-5, 2e-3, color='#fbf3e6', lw=0)
    c.plot(d, rubey(d), color=BLUE, lw=2.0)
    c.text(1.2e-6, 3e-1, t['rubey'], fontsize=7.6, color=BLUE, va='top')
    c.annotate(t['floc'], xy=(2.5e-6, 4e-4), xytext=(1.2e-6, 1.2e-2), fontsize=7.4, color=GREEN, va='center',
               arrowprops=dict(arrowstyle='-|>', color=GREEN, lw=.8))
    for x, key in [(2e-6, 'clay'), (1.6e-5, 'silt'), (3.5e-4, 'sand')]:
        c.text(x, 1.5e-7, t[key], fontsize=7.4, color=MUTED, ha='center', va='bottom')
    c.plot([2e-4], [rubey(2e-4)], 'o', color=ORANGE, ms=5, zorder=5)
    c.annotate(t['def'], xy=(2e-4, float(rubey(2e-4))), xytext=(6.0e-4, 1.5e-3), fontsize=7.6, color=ORANGE,
               arrowprops=dict(arrowstyle='-|>', color=ORANGE, lw=.8), va='center')
    block(ax, 35, 520, t['a_note'], 735, size=7.9)
    # (b) equilibrium concentration.
    panel(ax, 805, 108, t['b'])
    ts = np.linspace(0.051, 3.0, 400)
    c = chart(fig, 880, 150, 620, 300, (0.0, 3.0), (1e-5, 1.0), xlabel=t['bx'], ylabel=t['by'])
    c.set_yscale('log')
    c.plot(ts, 1e-4 * (ts / 0.05 - 1), color=SED, lw=2.0, label=t['lin'])
    for dd, col, ls in [(1e-4, GREEN, '-'), (2e-4, BLUE, '-'), (5e-4, BLUE, '--')]:
        y = ceq_ik(dd, ts)
        y = np.where(y > 0, y, np.nan)
        c.plot(ts, y, color=col, lw=1.6, ls=ls, label=t['ik'].format(f'{dd * 1000:g}'))
    c.legend(loc='upper left', bbox_to_anchor=(0.0, 1.05), fontsize=7.2, frameon=False, labelspacing=0.25)
    block(ax, 805, 520, t['b_note'], 735, size=7.9)
    line(ax, [(787, 105), (787, 608)], RULE, .8)
    rule(ax, 35, 1540, 616)
    block(ax, 35, 628, t['foot'], 1505, size=7.9, color=MUTED)
    return fig


def draw(lang):
    return run(build, 'geomorph_suspend', lang,
               'Curves of the Rubey settling velocity versus grain size with the floc band for mud, and of the '
               'equilibrium concentration of f_esform = 1 and 2 versus the Shields number. Not solver output.')
