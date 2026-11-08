"""Graphs for the resistance laws of the mixture flow (massflow.md §2, f_dbres).

(a) slope at which the yield term stops the flow (and below which a resting
    mixture does not start), tan(theta_y) = a_y / g_e, versus the mixture
    concentration C for f_dbres = 1-5: a_y of src/m_swflow_enc.f90 (yield of
    laws 1-3 applied for every C > 0; laws 4 and 5 have no yield below db_cmin);
    for law 5 the stopping slope solves g cos^2(theta) tan(theta) = tau_y/(rho_m h_t);
(b) steady uniform speed along a 20-degree slope versus grain size d50 for the
    Egashira law (2), the Takahashi-Nakagawa stony law (3; Manning for
    h_t/d >= 30) and Voellmy (4), from the uniform-flow balances that
    test/dbslope checks (default f_gravity_correction = 2, flow down the
    steepest descent);
(c) curvature term (f_dbcurv): multiplier max(0, 1 + a_c/g_n) of the yield term.
Closed forms for illustrative values; not solver output.

Generate: python docs/figs/make_guide_figs.py massflow_resist
"""
import math
import numpy as np
from _geomorph import (canvas, header, panel, rule, chart, run, text, kblock as block, line, poly, arrow,
                       INK, MUTED, RULE, SED, GREEN, BLUE, ORANGE, SOIL, MOVING, PANEL)

H = 880
G, S, CSTAR, TANPHI = 9.8, 1.65, 0.6, math.tan(math.radians(35.0))   # db_phi, fluv_sgrav, 1 - fluv_porosity
CMIN, MU, XI, TAUY = 0.02, 0.2, 1000.0, 1.0e4                     # db_cmin, db_mu, db_xi, db_tauy
KF, KD, EREST, TANA, APR, HDMUD = 0.16, 0.0828, 0.85, 0.45, 4.0, 30.0
TH_B, HT_B, C_B = 20.0, 1.0, 0.4                                   # slope (deg), depth (m), C for (b)
YC, HC = 172, 280                                                  # chart top and height (px)
YN = 612                                                           # notes

T = {
 'ja': {
    'title': '混合体の抵抗則の振る舞い  |  止まる勾配と濃度、粒径と定常速度、曲率項',
    'sub': 'src/m_swflow_enc.f90 の抵抗則(既定 f_gravity_correction = 2)を説明用の値で評価した曲線。計算結果ではない。',
    'a': '(a) 降伏で止まる勾配と濃度', 'a2': 'tan θ_y = a_y / g_e(f_dbres ごと)',
    'ax': '混合体積濃度 C', 'ay': '止まる勾配 tan θ_y',
    'l1': '1 クーロン + Manning', 'l2': '2 江頭', 'l3': '3 高橋・中川', 'l4': '4 Voellmy(μ = 0.2)',
    'l5': '5 τ_y = 10 kPa(h_t = 3 m)',
    'cmin': 'c_min', 'deg': '{:g}°',
    'a_note': '勾配が線より緩いと流れは止まり、静止した混合体は動き出さない。1〜3 は濃度とともに上がるので、希薄な流れ'
              'ほど緩い勾配でも流れる。4 は濃度によらず μ、5 は流動深で決まる(厚いほど緩い勾配まで流れ、h_t = 5 m なら'
              '3 m の約 0.6 倍)。4・5 は C < c_min(既定 0.02)で降伏なし。1 の線は江頭・芦田の平衡勾配 θ_e(§3)と同じ式。',
    'b': '(b) 定常速度と粒径', 'b2t': '勾配 20°、h_t = 1 m、C = 0.4 の等流',
    'bx': '粒径 d50 (m)', 'by': '斜面に沿う定常速度 V_s (m/s)',
    'b2': '2 江頭: 層流抵抗が (d/h_t)² に比例', 'b3': '3 高橋・中川(石礫型。h_t/d ≥ 30 では Manning)',
    'b4': '4 Voellmy(μ = 0.2、ξ = 1000): 粒径によらない',
    'mud': 'h_t/d ≥ 30', 'div': '粒径 mm では\n数百 m/s(抵抗が消える)',
    'def': '既定 db_d50',
    'b_note': '等流の釣り合い(test/dbslope と同じ式)を斜面に沿う速さにしたもの。2 は粒径が小さいほど抵抗が消えて'
              '速度が発散するので、細粒のスラリーには 4 か 1 を使う。1(クーロン + Manning)の速さは Manning n で決まり、'
              '粒径によらない。',
    'c': '(c) 曲率項(f_dbcurv = 1)', 'c2t': '地形の曲率で降伏項を増減する',
    'conc': '凹(谷・遷緩点):\n遠心力が地面を押す\n→ 摩擦が増える', 'conv': '凸(尾根・遷急点): 押す力が減る\n→ 摩擦が減る',
    'lift': '浮く条件では 0',
    'cx': 'a_c / g_n', 'cy': '降伏項の倍率',
    'c_note': 'a_y ← a_y max(0, 1 + a_c/g_n)、a_c = uᵀHu/√(1 + |∇z|²)、g_n = √(g g_e)。H は z の Hessian。'
              'RAMMS(Fischer ら)と同じ扱いで、RAMMS で校正した μ・ξ を使う比較では有効にする。',
    'foot': 'φ = 35°、s = 1.65、C* = 0.6、μ = 0.2、ξ = 1000 m/s²、τ_y = 10 kPa、c_min = 0.02 は既定値。最急勾配の向きの流れ'
            '(降伏の倍率 1)。抵抗則の式は本文の表、急勾配での評価の倍率は本文。',
 },
 'en': {
    'title': 'Behaviour of the mixture resistance laws  |  Stopping slope vs concentration, speed vs grain size, curvature term',
    'sub': 'Curves of the resistance laws of src/m_swflow_enc.f90 (default f_gravity_correction = 2) for illustrative values; not computed results.',
    'a': '(a) Stopping slope and concentration', 'a2': 'tan θ_y = a_y / g_e for each f_dbres',
    'ax': 'mixture volume concentration C', 'ay': 'stopping slope tan θ_y',
    'l1': '1 Coulomb + Manning', 'l2': '2 Egashira', 'l3': '3 Takahashi–Nakagawa', 'l4': '4 Voellmy (μ = 0.2)',
    'l5': '5 τ_y = 10 kPa (h_t = 3 m)',
    'cmin': 'c_min', 'deg': '{:g}°',
    'a_note': 'On slopes gentler than the curve the flow stops and a resting mixture does not start. Laws 1–3 rise with '
              'concentration, so dilute flows run on gentler slopes; 4 is μ whatever the concentration, and 5 depends on the '
              'flow depth (thicker flows run on gentler slopes; h_t = 5 m gives about 0.6 times the slope of 3 m). Laws 4 and 5 '
              'have no yield below c_min (default 0.02). The curve of law 1 is the same expression as the Egashira–Ashida '
              'equilibrium slope θ_e (§3).',
    'b': '(b) Steady speed and grain size', 'b2t': 'uniform flow on a 20° slope, h_t = 1 m, C = 0.4',
    'bx': 'grain size d50 (m)', 'by': 'steady speed along the slope V_s (m/s)',
    'b2': '2 Egashira: laminar resistance ∝ (d/h_t)²', 'b3': '3 Takahashi–Nakagawa (stony; Manning for h_t/d ≥ 30)',
    'b4': '4 Voellmy (μ = 0.2, ξ = 1000): independent of grain size',
    'mud': 'h_t/d ≥ 30', 'div': 'mm grains: hundreds\nof m/s (no resistance)',
    'def': 'default db_d50',
    'b_note': 'Uniform-flow balances (the same expressions as test/dbslope) turned into the speed along the slope. In law 2 '
              'the resistance vanishes for small grains and the speed diverges, so use law 4 or 1 for fine slurries. The '
              'speed of law 1 (Coulomb + Manning) is set by Manning n and does not depend on grain size.',
    'c': '(c) Curvature term (f_dbcurv = 1)', 'c2t': 'the terrain curvature scales the yield term',
    'conc': 'concave (valley, slope break):\ncentrifugal force presses\non the ground → more friction',
    'conv': 'convex (ridge, crest): less pressure\n→ less friction',
    'lift': 'zero when lifting off',
    'cx': 'a_c / g_n', 'cy': 'yield multiplier',
    'c_note': 'a_y ← a_y max(0, 1 + a_c/g_n), a_c = uᵀHu/√(1 + |∇z|²), g_n = √(g g_e); H is the Hessian of z. Same '
              'treatment as in RAMMS by Fischer et al.; enable it when comparing with μ, ξ calibrated in RAMMS.',
    'foot': 'φ = 35°, s = 1.65, C* = 0.6, μ = 0.2, ξ = 1000 m/s², τ_y = 10 kPa and c_min = 0.02 are defaults. Flow down the '
            'steepest descent (yield multiplier 1). The laws are in the table of the text, and the multipliers for steep slopes in the text.',
 },
}


def frac(c):
    return S * c / (1.0 + S * c)


def stop_law5(c, ht):
    """Stopping slope of the constant stress law: g cos^2(th) tan(th) = tau_y / (rho_m h_t)."""
    out = np.full_like(c, np.nan)
    for k, cc in enumerate(c):
        if cc < CMIN:
            continue
        r = 2.0 * TAUY / (1000.0 * (1.0 + S * cc) * G * ht)
        if r <= 1.0:
            out[k] = math.tan(0.5 * math.asin(r))
    return out


def speed(law, d, th_deg=TH_B, ht=HT_B, c=C_B):
    """Steady speed along the slope (m/s) for flow down the steepest descent (test/dbslope balances)."""
    tn = math.tan(math.radians(th_deg))
    c2 = 1.0 / (1.0 + tn * tn)          # cos^2
    ge, fv = G * c2, 1.0 / c2 ** 2
    d = np.asarray(d, float)
    if law == 4:
        v = math.sqrt(XI * ht * (tn - MU) / fv) * np.ones_like(d)
    elif law == 2:
        dy = tn - TANPHI * frac(c) * (c / CSTAR) ** 0.2
        kk = 6.25 * (KF * (1 - c) ** (5 / 3) / c ** (2 / 3) + KD * (S + 1) * (1 - EREST ** 2) * c ** (1 / 3))
        v = (ht / d) * math.sqrt(ge * dy * (1 + S * c) * ht / (fv * kk))
    else:
        dy = tn - TANA * frac(c)
        kk = APR * ((1 - c) / c) ** (2 / 3)
        v = (ht / d) * math.sqrt(ge * dy * (1 + S * c) * ht / (fv * kk))
        v = np.where(ht / d < HDMUD, v, np.nan)
    return v / math.sqrt(c2)            # |V_s| = |V| / cos(theta)


def legend(c, handles, ncol, y=-0.21, x=-0.17):
    c.legend(handles=handles, loc='upper left', bbox_to_anchor=(x, y), ncol=ncol, fontsize=7.6, frameon=False,
             handlelength=2.2, columnspacing=1.2, labelspacing=0.35)


def panel_a(fig, ax, t):
    panel(ax, 35, 108, t['a'])
    text(ax, 35, 136, t['a2'], size=8, color=MUTED)
    c = chart(fig, 100, YC, 400, HC, (0, 0.6), (0, 0.62), xlabel=t['ax'], ylabel=t['ay'])
    cc = np.linspace(1e-4, 0.6, 600)
    for deg in (10, 20, 30):
        y = math.tan(math.radians(deg))
        c.axhline(y, color=RULE, lw=.7, zorder=0)
        c.text(0.607, y, t['deg'].format(deg), fontsize=7.4, color=MUTED, ha='left', va='center', clip_on=False)
    c.axvspan(0, CMIN, color=PANEL, lw=0, zorder=0)
    c.text(CMIN + 0.004, 0.6, t['cmin'], fontsize=7.4, color=MUTED, va='top')
    h1, = c.plot(cc, TANPHI * frac(cc), color=SED, lw=2.0, label=t['l1'])
    h2, = c.plot(cc, TANPHI * frac(cc) * (cc / CSTAR) ** 0.2, color=ORANGE, lw=2.0, label=t['l2'])
    h3, = c.plot(cc, TANA * frac(cc), color=GREEN, lw=2.0, label=t['l3'])
    h4, = c.plot(cc, np.where(cc >= CMIN, MU, np.nan), color=BLUE, lw=2.0, label=t['l4'])
    h5, = c.plot(cc, stop_law5(cc, 3.0), color=MUTED, lw=1.5, ls='--', label=t['l5'])
    legend(c, [h1, h2, h3, h4, h5], 2)
    block(ax, 35, YN, t['a_note'], 470, size=7.9)


def panel_b(fig, ax, t):
    x0 = 545
    panel(ax, x0, 108, t['b'])
    text(ax, x0, 136, t['b2t'], size=8, color=MUTED)
    d = np.logspace(math.log10(5e-4), math.log10(0.5), 400)
    c = chart(fig, x0 + 70, YC, 400, HC, (5e-4, 0.5), (1, 3000), xlabel=t['bx'], ylabel=t['by'])
    c.set_xscale('log'); c.set_yscale('log')
    dmud = HT_B / HDMUD
    c.axvspan(5e-4, dmud, color=PANEL, lw=0, zorder=0)
    c.text(dmud * 0.92, 1.2, t['mud'], fontsize=7.4, color=MUTED, ha='right', va='bottom')
    h2, = c.plot(d, speed(2, d), color=ORANGE, lw=2.0, label=t['b2'])
    h3, = c.plot(d, speed(3, d), color=GREEN, lw=2.0, label=t['b3'])
    h4, = c.plot(d, speed(4, d), color=BLUE, lw=2.0, label=t['b4'])
    c.annotate(t['div'], xy=(1.2e-3, float(speed(2, [1.2e-3])[0])), xytext=(6e-4, 90), fontsize=7.4, color=ORANGE,
               va='center', arrowprops=dict(arrowstyle='-|>', color=ORANGE, lw=.8))
    c.axvline(0.05, color=MUTED, lw=.8, ls='--')
    c.text(0.055, 2500, t['def'], fontsize=7.2, color=MUTED, va='top')
    legend(c, [h2, h3, h4], 1)
    block(ax, x0, YN, t['b_note'], 480, size=7.9)


def panel_c(fig, ax, t):
    x0 = 1065
    panel(ax, x0, 108, t['c'])
    text(ax, x0, 136, t['c2t'], size=8, color=MUTED)
    # Schematic bed: plateau, convex upper bend, slope, concave lower bend, floor (flow left to right).
    xs = np.linspace(0, 1, 240)
    bed = 0.5 - 0.5 * np.tanh((xs - 0.5) / 0.13)
    px = x0 + 15 + 450 * xs
    py = 240 + 80 * (1.0 - bed)
    poly(ax, list(zip(px, py)) + [(px[-1], 352), (px[0], 352)], SOIL, z=2)
    line(ax, list(zip(px, py)), INK, 1.1, z=6)
    flow = py - 12
    poly(ax, list(zip(px, flow)) + list(zip(px[::-1], py[::-1])), MOVING, z=3, alpha=.85)
    kv = int(0.33 * 239); kc = int(0.67 * 239)
    arrow(ax, [(px[kv], py[kv] - 14), (px[kv], py[kv] - 46)], BLUE, lw=1.4, size=9)
    arrow(ax, [(px[kc], py[kc] - 48), (px[kc], py[kc] - 14)], ORANGE, lw=1.4, size=9)
    text(ax, x0 + 15, 168, t['conv'], size=7.6, color=BLUE)
    text(ax, x0 + 465, 200, t['conc'], size=7.6, color=ORANGE, ha='right')
    c = chart(fig, x0 + 65, 392, 380, 100, (-1.5, 1.5), (0, 2.6), xlabel=t['cx'], ylabel=t['cy'])
    xx = np.linspace(-1.5, 1.5, 300)
    c.plot(xx, np.maximum(0, 1 + xx), color=SED, lw=2.0)
    c.axvline(0, color=RULE, lw=.7)
    c.text(-1.45, 0.75, t['lift'], fontsize=7.4, color=MUTED, va='bottom')
    block(ax, x0, YN, t['c_note'], 475, size=7.9)


def build(lang):
    t = T[lang]
    fig, ax = canvas(H)
    header(ax, t['title'], t['sub'])
    panel_a(fig, ax, t)
    line(ax, [(527, 105), (527, 810)], RULE, .8)
    panel_b(fig, ax, t)
    line(ax, [(1047, 105), (1047, 810)], RULE, .8)
    panel_c(fig, ax, t)
    rule(ax, 35, 1540, 818)
    block(ax, 35, 828, t['foot'], 1505, size=7.9, color=MUTED)
    return fig


def draw(lang):
    return run(build, 'massflow_resist', lang,
               'Curves of the stopping slope of the yield term versus concentration for the five resistance laws, of the '
               'steady speed versus grain size for the Egashira, Takahashi-Nakagawa and Voellmy laws, and of the curvature '
               'multiplier. Not solver output.')
