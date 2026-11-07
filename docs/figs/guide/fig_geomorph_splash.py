"""Dry-slope erosion f_splash (geomorph.md): where each term acts, the valley feedback,
the curvature length spl_lc that sets the valley spacing, horizontal strata
spl_strata and the amplification saturation spl_ksat.

The growth-rate curves are the linear-stage expressions quoted in the text
(sigma ~ k^2 without smoothing; sigma ~ k^2 exp(-l^2 k^2 / 2) with spl_lc = l,
peak at k* = sqrt(2)/l, spacing 2 pi l / sqrt(2) ~ 4.4 l). Profiles are
illustrative, not computed terrain.

Generate: python docs/figs/make_guide_figs.py geomorph_splash
"""
import numpy as np
from _geomorph import (canvas, header, panel, rule, box, poly, badge, chart, ground_px, run,
                       text, block, line, arrow, INK, MUTED, RULE,
                       SOIL, ROCK, WATER, BLUE, SED, GREEN, ORANGE, PANEL)

H = 1190

T = {
 'ja': {
    'title': '乾式斜面侵食の機構  |  項の働く場所・谷の正のフィードバック・谷間隔の長さ・層理',
    'sub': 'f_splash。河道外の乾いたセル(h ≤ dd、rw = 0)だけに働き、剥離した土砂は系外へ出す。断面は説明用で、計算結果ではない。',
    'a': '(a) 侵食速度  E = P [ spl_kr (1 + spl_ca κ) + spl_kt (1 + spl_cb κ) S^spl_h ]',
    'rain': '地表到達降雨 P(湿潤セルは f_wash の担当)',
    'k1': '台地(S = 0, κ = 0): 雨滴項 P kr だけ',
    'k2': '急斜面: リル項 P kt S^h が加わる',
    'k3': '凹部(κ > 0): (1 + c κ) 倍に増幅',
    'k4': 'z は spl_zbase を下回らない\n(崖下が海なら海面)',
    'out': '剥離分は系外へ\n(hs に入れない)',
    'sd': '土層 sd(0 で岩盤露出・停止)',
    'trans': '斜面を横切る断面',
    'valley': '谷: κ > 0 → 増幅', 'ridge': '尾根: κ < 0 は 0 として扱う\n(増幅なし)',
    'loop': '谷が深まる → κ が増す → E が増す\n(正のフィードバック)',
    'b': '(b) 谷の間隔を決める長さ ℓ(spl_lc)  — 線形段階の成長率',
    'kx': '波数 k ℓ', 'sy': '成長率(正規化)',
    'l0': 'spl_lc = 0: σ ∝ k²(格子の 5 点ラプラシアン)', 'l1': 'spl_lc = ℓ: σ ∝ k² exp(−ℓ²k²/2)', 'norm': '各曲線をその最大で正規化',
    'grid': '格子の限界 k = π/Δ\n(図は ℓ/Δ = 2)', 'peak': 'k* = √2 / ℓ\n間隔 λ* = 2πℓ/√2 ≈ 4.4 ℓ',
    'b_note': 'ℓ = 0 では最短波長(2Δ)が最も速く育ち、谷の間隔が格子幅に張り付く(2〜3Δ。格子を細かくすると谷が増える)。'
              'ℓ > 0 では z を標準偏差 ℓ のガウス核で平滑化してから κ を取り(勾配 S は生の z から)、間隔が ℓ で決まる。'
              'ℓ/Δ ≥ 2 で格子を細かくしても間隔が収束する。谷が深くなってからの発達速度には格子依存が残る。',
    'c': '(c) 水平層理  spl_strata(1:2, k) = (z_k, f_k)',
    'cap': 'f = 0(キャップロック)', 'soft': 'f = 2.5(軟層)', 'hard': 'f = 0.4(硬層)', 'below': '最下層より下は 1',
    'c_note': 'セルの地表標高 z が属する層の倍率 f_k を E に掛ける。層は水平(標高だけの関数)で、'
              'z が下がると下の層が露出する。クリープには掛けない。',
    'd': '(d) 増幅の飽和  spl_ksat = κ_s',
    'dx': 'κ / κ_s', 'dy': '増幅 1 + c κ',
    'lin': 'spl_ksat = 0: 1 + c κ', 'sat': 'spl_ksat = κ_s: 1 + c κ/(1 + κ/κ_s)', 'asym': '1 + c κ_s に飽和',
    'd_note': '崖の基部(硬層の上面)のような強い凹部で増幅を有界にし、段(ベンチ)を残す。'
              'κ ≪ κ_s では従来どおりで、谷間隔の選択則は変わらない。図は c κ_s = 10。',
    'foot': '係数の既定・校正の考え方は本文と sediment.md §6。谷形成の対照(固結度)は f_slide との併用(test/splashslide)。',
 },
 'en': {
    'title': 'Dry-slope erosion  |  Where each term acts, valley feedback, valley-spacing length, strata',
    'sub': 'f_splash. Acts only on dry cells outside channels (h ≤ dd, rw = 0); detached sediment leaves the system. Illustrative sections, not computed results.',
    'a': '(a) Erosion rate  E = P [ spl_kr (1 + spl_ca κ) + spl_kt (1 + spl_cb κ) S^spl_h ]',
    'rain': 'rain reaching the ground P (wet cells belong to f_wash)',
    'k1': 'plateau (S = 0, κ = 0): splash term P kr only',
    'k2': 'steep slope: rill term P kt S^h added',
    'k3': 'concavity (κ > 0): amplified by (1 + c κ)',
    'k4': 'z never drops below spl_zbase (sea level below a sea cliff)',
    'out': 'detached sediment\nleaves (not into hs)',
    'sd': 'soil sd (stops at bedrock, sd = 0)',
    'trans': 'section across the slope',
    'valley': 'valley: κ > 0 → amplified', 'ridge': 'ridge: κ < 0 is treated as 0\n(no amplification)',
    'loop': 'valley deepens → κ grows → E grows\n(positive feedback)',
    'b': '(b) Valley-spacing length ℓ (spl_lc): linear-stage growth rate',
    'kx': 'wavenumber k ℓ', 'sy': 'growth rate (normalized)',
    'l0': 'spl_lc = 0: σ ∝ k² (grid 5-point Laplacian)', 'l1': 'spl_lc = ℓ: σ ∝ k² exp(−ℓ²k²/2)', 'norm': 'each curve normalized by its maximum',
    'grid': 'grid limit k = π/Δ\n(ℓ/Δ = 2 here)', 'peak': 'k* = √2 / ℓ\nspacing λ* = 2πℓ/√2 ≈ 4.4 ℓ',
    'b_note': 'With ℓ = 0 the shortest wavelength (2Δ) grows fastest and the valley spacing sticks to the grid (2–3Δ; a finer grid gives more valleys). '
              'With ℓ > 0, κ is taken from z smoothed by a Gaussian of standard deviation ℓ (the slope S uses the raw z), so ℓ sets the spacing. '
              'The spacing converges under refinement for ℓ/Δ ≥ 2; the growth rate of deep valleys keeps some grid dependence.',
    'c': '(c) Horizontal strata  spl_strata(1:2, k) = (z_k, f_k)',
    'cap': 'f = 0 (caprock)', 'soft': 'f = 2.5 (soft)', 'hard': 'f = 0.4 (hard)', 'below': '1 below the lowest layer',
    'c_note': 'E is multiplied by f_k of the layer that contains the ground elevation z of the cell. Layers are horizontal '
              '(a function of elevation only); as z drops, the layer below is exposed. Not applied to creep.',
    'd': '(d) Saturation of the amplification  spl_ksat = κ_s',
    'dx': 'κ / κ_s', 'dy': 'amplification 1 + c κ',
    'lin': 'spl_ksat = 0: 1 + c κ', 'sat': 'spl_ksat = κ_s: 1 + c κ/(1 + κ/κ_s)', 'asym': 'saturates at 1 + c κ_s',
    'd_note': 'Bounds the amplification in strong concavities, e.g. at the foot of a cliff on top of a hard layer, so that benches survive. '
              'Unchanged for κ ≪ κ_s, so the valley-spacing selection is the same. Drawn with c κ_s = 10.',
    'foot': 'Defaults and calibration of the coefficients: the text and sediment.md §6. Contrast of valley formation by consolidation: combine with f_slide (test/splashslide).',
 },
}


def panel_terms(ax, t):
    panel(ax, 35, 108, t['a'])
    # Longitudinal profile: plateau, cliff edge, steep slope, concave foot, base at sea level.
    xs = np.array([50, 250, 272, 300, 520, 560, 600, 640, 760])
    ys = np.array([238, 238, 242, 256, 404, 428, 440, 445, 445])
    sd = 22
    poly(ax, list(zip(xs, ys)) + [(760, 470), (50, 470)], ROCK, z=1)
    poly(ax, list(zip(xs, ys)) + list(zip(xs[::-1], ys[::-1] + sd)), SOIL, z=2)
    line(ax, list(zip(xs, ys)), INK, 1.1, z=6)
    poly(ax, [(640, 445), (760, 445), (760, 470), (640, 470)], WATER, z=3)
    line(ax, [(612, 445), (760, 445)], BLUE, 1.2, ls='--', z=7)
    for xr in np.arange(70, 540, 42):
        yr = float(np.interp(xr, xs, ys))
        line(ax, [(xr + 6, yr - 52), (xr, yr - 30)], BLUE, .9)
    text(ax, 52, 150, t['rain'], size=8.3, color=BLUE)
    arrow(ax, [(420, 330), (470, 300)], SED, lw=1.6, size=10)
    text(ax, 476, 280, t['out'], size=8.2, color=SED)
    badge(ax, 150, 214, '1', r=12, size=8)
    badge(ax, 395, 300, '2', r=12, size=8)
    badge(ax, 555, 405, '3', r=12, size=8)
    badge(ax, 700, 425, '4', r=12, size=8)
    text(ax, 210, 470, t['sd'], size=8.0, color='#8a6d3b', ha='center')
    yy = 500
    for k, key in enumerate(['k1', 'k2', 'k3', 'k4']):
        badge(ax, 62, yy + 9, str(k + 1), r=10, size=7.6)
        a = block(ax, 82, yy, t[key], 370, size=8.4)
        yy += 26 * (a.get_text().count('\n') + 1)
    block(ax, 35, yy + 12, t['loop'], 420, size=8.4, color=SED)
    # Section across the slope: valleys amplified, ridges not.
    x0, x1, yb = 480, 760, 600
    xx = np.linspace(x0, x1, 200)
    yy = 566 + 18 * np.cos(2 * np.pi * (xx - x0) / 96.0)
    poly(ax, list(zip(xx, yy)) + [(x1, yb), (x0, yb)], SOIL, z=2)
    line(ax, list(zip(xx, yy)), INK, 1.0)
    text(ax, x0, 506, t['trans'], size=8.2, weight='bold', color=MUTED)
    for xv in x0 + 48 + 96 * np.arange(3):
        if xv < x1:
            arrow(ax, [(xv, 574), (xv, 590)], SED, lw=1.4, size=8)
    text(ax, x0, 610, t['valley'], size=8.0, color=SED)
    block(ax, x0, 636, t['ridge'], 280, size=8.0, color=MUTED)


def panel_spacing(fig, ax, t):
    panel(ax, 805, 108, t['b'])
    k = np.linspace(1e-3, 7.0, 600)
    kgrid = 2 * np.pi            # pi / Delta with l / Delta = 2
    s0 = k ** 2 / kgrid ** 2
    s1 = k ** 2 * np.exp(-k ** 2 / 2)
    s1 /= s1.max()
    c = chart(fig, 880, 150, 620, 290, (0, 7.0), (0, 1.1), xlabel=t['kx'], ylabel=t['sy'])
    m = k <= kgrid
    c.plot(k[m], s0[m], color=MUTED, lw=1.6, ls='--')
    c.plot(k, s1, color=GREEN, lw=2.0)
    c.axvline(kgrid, color=ORANGE, lw=1.0, ls=':')
    c.text(kgrid - .08, .1, t['grid'], color=ORANGE, fontsize=8, ha='right', va='center')
    c.plot([np.sqrt(2)], [1.0], 'o', color=GREEN, ms=5)
    c.annotate(t['peak'], xy=(np.sqrt(2), 1.0), xytext=(2.25, .86), fontsize=8.2, color=GREEN,
               arrowprops=dict(arrowstyle='-|>', color=GREEN, lw=.9), va='center')
    for k2, (key, col, ls) in enumerate([('l0', MUTED, '--'), ('l1', GREEN, '-')]):
        yy = 496 + 26 * k2
        line(ax, [(810, yy + 10), (850, yy + 10)], col, 1.8, ls=ls)
        text(ax, 862, yy, t[key], size=8.3)
    text(ax, 862, 548, t['norm'], size=8.0, color=MUTED)
    block(ax, 805, 580, t['b_note'], 735, size=8.4)


def panel_strata(ax, t):
    y0 = 742
    panel(ax, 35, y0, t['c'])
    # Mesa section clipped from horizontal bands; layer limits are elevations only.
    dy = 62
    bands = [(730 + dy, 776 + dy, '#cfc9bd', 'cap'), (776 + dy, 846 + dy, '#ead9b4', 'soft'),
             (846 + dy, 868 + dy, '#c4baa6', 'hard'), (868 + dy, 930 + dy, '#ead9b4', 'soft'),
             (930 + dy, 975 + dy, '#ddd6c8', 'below')]
    xs = np.array([50, 230, 232, 300, 330, 338, 400, 520, 760])
    ys = np.array([730, 730, 776, 846, 846, 868, 930, 960, 975]) + dy
    for top, bot, col, key in bands:
        pts = []
        for xa, ya in zip(xs, ys):
            pts.append((xa, max(ya, top)))
        pts += [(760, bot), (50, bot)]
        lowx = [(xa, min(max(ya, top), bot)) for xa, ya in zip(xs, ys)]
        poly(ax, lowx + [(760, bot), (50, bot)], col, z=2)
    line(ax, list(zip(xs, ys)), INK, 1.1, z=6)
    for top, bot, col, key in bands:
        line(ax, [(50, top), (760, top)], MUTED, .6, ls=':', z=5)
    labels = [(752, 752, 'cap'), (752, 811, 'soft'), (752, 857, 'hard'), (752, 899, 'soft'), (752, 952, 'below')]
    for xl, yl, key in labels:
        text(ax, xl, yl + dy, t[key], size=8.0, ha='right', va='center', color=INK)
    for zk, yk in [('z_1', 930), ('z_2', 868), ('z_3', 846), ('z_4', 776)]:
        text(ax, 46, yk + dy, zk, size=7.8, color=MUTED, ha='right', va='center')
    block(ax, 35, 1052, t['c_note'], 735, size=8.4)


def panel_ksat(fig, ax, t):
    y0 = 742
    panel(ax, 805, y0, t['d'])
    x = np.linspace(0, 8, 300)
    ck = 10.0
    c = chart(fig, 880, 782, 620, 210, (0, 8), (0, 40), xlabel=t['dx'], ylabel=t['dy'])
    c.plot(x, 1 + ck * x, color=MUTED, lw=1.6, ls='--', label=t['lin'])
    c.plot(x, 1 + ck * x / (1 + x), color=GREEN, lw=2.0, label=t['sat'])
    c.axhline(1 + ck, color=GREEN, lw=.8, ls=':')
    c.text(7.9, 1 + ck + 1.2, t['asym'], color=GREEN, fontsize=8, ha='right', va='bottom')
    c.legend(loc='upper right', fontsize=8, frameon=False)
    block(ax, 805, 1052, t['d_note'], 735, size=8.4)


def build(lang):
    t = T[lang]
    fig, ax = canvas(H)
    header(ax, t['title'], t['sub'])
    panel_terms(ax, t)
    panel_spacing(fig, ax, t)
    rule(ax, 35, 1540, 724)
    line(ax, [(787, 105), (787, 1140)], RULE, .8)
    panel_strata(ax, t)
    panel_ksat(fig, ax, t)
    rule(ax, 35, 1540, 1148)
    block(ax, 35, 1158, t['foot'], 1505, size=8.2, color=MUTED)
    return fig


def draw(lang):
    return run(build, 'geomorph_splash', lang,
               'Schematic of dry-slope erosion f_splash: where the splash and rill terms act, the valley feedback, '
               'the linear-stage growth rate with and without the curvature length spl_lc, horizontal strata '
               'spl_strata and the saturation spl_ksat. Not computed terrain.')
