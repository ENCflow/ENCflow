"""Graphs for debris flow and slope failure (geomorph.md, f_debris / f_slide).

(a) steady uniform speed of the Voellmy law (f_dbres = 4) on a planar slope,
    with the default f_gravity_correction = 2:
    V_s^2 = xi h_t cos(theta) (sin(theta) - mu cos(theta))  (massflow.md §2),
    for the mu, xi of the recommended-value table; no flow where tan(theta) <= mu;
(b) safety factor of the infinite slope (f_slide) versus slope angle for the
    saturated fraction hw/sd:
    Fs = (c' + (gamma_t sd - gamma_w hw) cos^2(theta) tan(phi)) / (gamma_t sd sin(theta) cos(theta))
    (src/m_geomorph_debris.f90 slide_pass1).
Closed forms for illustrative values; not solver output.

Generate: python docs/figs/make_guide_figs.py geomorph_debris
"""
import numpy as np
from _geomorph import (canvas, header, panel, rule, chart, run, text, block, line,
                       INK, MUTED, RULE, SED, GREEN, BLUE, ORANGE)

H = 676
HT = 2.0                                   # flow depth h_t (m) for (a)
GW, GT, PHI = 9810.0, 18000.0, 30.0        # gamma_w (rho_w g), slide_gamma, slide_phi defaults

T = {
 'ja': {
    'title': '土石流と斜面崩壊の式の振る舞い  |  Voellmy の定常速度・無限長斜面の安全率',
    'sub': '式の曲線(推奨値と既定値)。計算結果ではない。',
    'a': '(a) Voellmy 則(f_dbres = 4)の斜面の定常速度(流動深 h_t = 2 m)',
    'ax': '斜面の傾斜角 θ (度)', 'ay': '斜面に沿う定常速度 V_s (m/s)',
    'pat': [('流れ型雪崩(既定)', 0.2, 1000), ('岩屑なだれ', 0.1, 300), ('土石流(Voellmy 型)', 0.11, 450), ('ラハール(細粒)', 0.07, 700)],
    'stop': 'tan θ ≤ μ では止まる',
    'a_note': 'V_s² = ξ h_t cos θ (sin θ − μ cos θ)(既定 f_gravity_correction = 2。RAMMS と同じ形)。μ は止まる勾配(見かけ摩擦 H/L の目安)を、ξ は急斜面での速さを決める。流動深が 4 倍なら速さは 2 倍。',
    'b': '(b) 無限長斜面の安全率(f_slide)と飽和厚',
    'bx': '斜面の傾斜角 θ (度)', 'by': '安全率 Fs',
    'm': 'hw/sd = {:g}', 'coh': "c' = 3 kPa、sd = 1.5 m、hw/sd = 1",
    'fail': 'Fs < 1: 崩壊(f_slide = 1 で流動化)',
    'b_note': "Fs = (c' + (γt sd − γw hw) cos²θ tan φ) / (γt sd sin θ cos θ)。既定 slide_c = 0、slide_phi = 30°、slide_gamma = 18 kN/m³。飽和厚 hw は地下水計算の hg/sy0(sd が上限)。地下水位が上がると、崩れる最小の勾配が 30° から 15° まで下がる。",
    'foot': "(a) の μ・ξ は章末の「パターン別の推奨値」の代表値(校正で変わる)。(b) は粘着力 c' = 0 では sd によらず、c' > 0 では薄い土層ほど安定。",
 },
 'en': {
    'title': 'Behaviour of the debris-flow and slope-failure equations  |  Voellmy steady speed, infinite-slope safety factor',
    'sub': 'Curves of the equations (recommended and default values); not computed results.',
    'a': '(a) Voellmy (f_dbres = 4) steady speed, depth h_t = 2 m',
    'ax': 'slope angle θ (deg)', 'ay': 'steady speed along the slope V_s (m/s)',
    'pat': [('dense snow avalanche (default)', 0.2, 1000), ('debris avalanche', 0.1, 300), ('debris flow (Voellmy type)', 0.11, 450), ('lahar (fine)', 0.07, 700)],
    'stop': 'stops where tan θ ≤ μ',
    'a_note': 'V_s² = ξ h_t cos θ (sin θ − μ cos θ) (default f_gravity_correction = 2; same form as RAMMS). μ sets the slope at which the flow stops (about the apparent friction H/L) and ξ the speed on steep slopes. Four times the depth doubles the speed.',
    'b': '(b) Infinite-slope safety factor (f_slide)',
    'bx': 'slope angle θ (deg)', 'by': 'safety factor Fs',
    'm': 'hw/sd = {:g}', 'coh': "c' = 3 kPa, sd = 1.5 m, hw/sd = 1",
    'fail': 'Fs < 1: failure (mobilized with f_slide = 1)',
    'b_note': "Fs = (c' + (γt sd − γw hw) cos²θ tan φ) / (γt sd sin θ cos θ). Defaults slide_c = 0, slide_phi = 30°, slide_gamma = 18 kN/m³. The saturated thickness hw is hg/sy0 of the groundwater model (capped by sd). A rising water table lowers the smallest failing slope from 30° to 15°.",
    'foot': "μ and ξ in (a) are representative values of the table \"Recommended values by pattern\" at the end of the chapter (they change with calibration). In (b), Fs does not depend on sd when the cohesion c' = 0; with c' > 0 thinner soil is more stable.",
 },
}


def voellmy(th_deg, mu, xi, ht=HT):
    th = np.radians(th_deg)
    v2 = xi * ht * np.cos(th) * (np.sin(th) - mu * np.cos(th))
    return np.sqrt(np.maximum(v2, 0.0))


def fs(th_deg, m, c=0.0, sd=1.0):
    th = np.radians(th_deg)
    w = GT * sd
    u = GW * m * sd
    return (c + (w - u) * np.cos(th) ** 2 * np.tan(np.radians(PHI))) / (w * np.sin(th) * np.cos(th))


def build(lang):
    t = T[lang]
    fig, ax = canvas(H)
    header(ax, t['title'], t['sub'])
    # (a) Voellmy steady speed.
    panel(ax, 35, 108, t['a'])
    th = np.linspace(0.1, 45, 400)
    c = chart(fig, 110, 150, 620, 300, (0, 45), (0, 45), xlabel=t['ax'], ylabel=t['ay'])
    cols = [BLUE, SED, ORANGE, GREEN]
    for (name, mu, xi), col in zip(t['pat'], cols):
        c.plot(th, voellmy(th, mu, xi), color=col, lw=2.0, label=f'{name}: μ = {mu:g}, ξ = {xi:g}')
        ts = np.degrees(np.arctan(mu))
        c.plot([ts], [0], 'o', color=col, ms=4.5, zorder=5, clip_on=False)
    c.annotate(t['stop'], xy=(np.degrees(np.arctan(0.2)), 0.3), xytext=(19, 3.5), fontsize=7.6, color=MUTED,
               arrowprops=dict(arrowstyle='-|>', color=MUTED, lw=.8))
    c.legend(loc='upper left', fontsize=7.4, frameon=False, labelspacing=0.3)
    block(ax, 35, 520, t['a_note'], 735, size=7.9)
    # (b) safety factor.
    panel(ax, 805, 108, t['b'])
    th = np.linspace(5, 45, 300)
    c = chart(fig, 880, 150, 620, 300, (5, 45), (0, 3), xlabel=t['bx'], ylabel=t['by'])
    c.axhspan(0, 1, color='#fbefe6', lw=0)
    for m, col in [(0, GREEN), (0.5, SED), (1.0, BLUE)]:
        c.plot(th, fs(th, m), color=col, lw=2.0, label=t['m'].format(m))
    c.plot(th, fs(th, 1.0, c=3000.0, sd=1.5), color=BLUE, lw=1.4, ls='--', label=t['coh'])
    c.axhline(1.0, color=ORANGE, lw=1.0)
    c.text(5.6, 0.1, t['fail'], fontsize=7.6, color=ORANGE, ha='left', va='bottom')
    c.legend(loc='upper right', fontsize=7.4, frameon=False, labelspacing=0.3)
    block(ax, 805, 520, t['b_note'], 735, size=7.9)
    line(ax, [(787, 105), (787, 606)], RULE, .8)
    rule(ax, 35, 1540, 612)
    block(ax, 35, 622, t['foot'], 1505, size=7.9, color=MUTED)
    return fig


def draw(lang):
    return run(build, 'geomorph_debris', lang,
               'Curves of the steady uniform speed of the Voellmy law for the recommended mu and xi, and of the '
               'infinite-slope safety factor versus slope angle for several saturated fractions. Not solver output.')
