"""Bank and bend mechanisms added on top of bedload (f_fluvial section of geomorph.md).

(a) bend cross-section: secondary flow (f_secflow) versus the bed-slope term
(fluv_slope); (b) bank erosion f_berode; (c) angle-of-repose collapse f_repose;
(d) slump-block self-protection (f_rockfall bank mode rf_bank + berode_hcover).
Cells are drawn as raster columns (one z per cell). Schematic, not solver output.

Generate: python docs/figs/make_guide_figs.py geomorph_bank
"""
import numpy as np
from _geomorph import (canvas, header, panel, rule, box, poly, dim, columns, water_px, ground_px,
                       run, text, block, line, arrow, INK, MUTED, RULE,
                       SOIL, WATER, BLUE, SED, MOVING, GREEN, TALUS, ORANGE)

H = 1170

T = {
 'ja': {
    'title': '掃流砂の河岸と湾曲部の機構  |  横断形状・側岸侵食・安息角崩落・崩落土塊',
    'sub': 'f_fluvial に重ねる任意の補正。断面と格子は説明用で、計算結果ではない。',
    'a': '(a) 湾曲部の横断形状  fluv_slope + f_secflow',
    'surface': '水面',
    'sec': '二次流(f_secflow)\n河床近傍は内岸へ  r = N* h κ',
    'slope': '河床勾配項(fluv_slope)\n横断斜面を下る向き  q⃗ = q_b(t̂ − γ∇z)',
    'inner': '内岸: 堆積(砂州)', 'outer': '外岸: 洗掘(淵)',
    'plan': '平面', 'pin': '内岸', 'pout': '外岸', 'center': '曲率中心', 'kappa': '流線の曲率 κ',
    'section': '断面 A–A′\n(下流向きに見る)',
    'a_note': '内岸へ引きずる二次流と、斜面を下る重力の項が釣り合って横断勾配ができる。'
              '両方を組で使う(片方だけでは横断勾配が平衡しない)。',
    'b': '(b) 側岸侵食  f_berode',
    'bank': '河岸セル b(地盤 ≥ 脚部の水面)',
    'face': '河岸面エッジ: 掃流砂は通らない',
    'shear': 'τ*_w: 脚部セル w(湿潤 h > dd)の掃流力',
    'eb': 'E_b = K_b (τ*_w / τ*c,b − 1)^m',
    'cut': '削る', 'put': '同じ体積を積む',
    'b_note': '河岸の地盤を下げ、同じ体積を脚部に積む(土砂は保存。以後は掃流砂が運ぶ)。'
              'berode_kb は校正値で既定なし。堤防エッジ(fn_rw の壁)では起きない。',
    'c': '(c) 安息角崩落  f_repose',
    'repose': '破線: 安息角 φ_r の勾配\n(repose_phi)',
    'excess': '超過分 excess', 'dist': 'dist',
    'c_rule': 'excess = (z_c − z_n)\n             − dist × tan φ_r\n1 更新にエッジごとに\nrelax × excess / 2 / 8 を\n高い側 c → 低い側 n へ移す\n(8 方向同時でも行き過ぎない)',
    'after': '点線: 多くの更新の後\n(安息角の勾配まで緩む)',
    'c_note': '乾湿を問わない(乾いた砂山・掘削面・河岸脚部の崩落土砂)。掃流砂なしでも使える。'
              '1 更新に 1 スイープなので、崩落は地形時間で 1 セルずつ伝わる。'
              '非粘着性の河岸は脚部の洗掘+崩落だけで後退するので、berode_kb と二重に与えない。',
    'd': '(d) 崩落土塊による河岸の自己保護  rf_bank = 1 + berode_hcover',
    'hc': '限界高さ H_c(rf_hc)', 'over': '超過分が崩れる',
    'talus': '崖錐 ht(崩落土塊)', 'shield': '崖錐のある脚部では、河岸面に届く掃流力が\n(1 − ht / h_cover)⁺ 倍に減る(berode_hcover)',
    'carry': '流出で減る(搬出)',
    'd_note': '崩れた土塊が脚部を覆い、流れが運び去るまで河岸の侵食を止める。崖錐は掃流砂・側岸侵食・'
              '安息角崩落の流出で減る(流入は崖錐にしない)。水面下の段(淵の壁)は崩落の対象外。'
              '定着 f_fixation があれば限界高さは H_c (1 + c_τ,b a)。',
    'foot': '各項は f_fluvial = 1 の上の任意の補正(f_repose だけは掃流砂なしでも使える)。'
            '式・係数の出典は本文と sediment.md §3。',
 },
 'en': {
    'title': 'Bank and bend mechanisms of bedload  |  Cross-section, bank erosion, repose, slump blocks',
    'sub': 'Optional corrections on top of f_fluvial. Sections and cells are illustrative, not computed results.',
    'a': '(a) Cross-section of a bend  fluv_slope + f_secflow',
    'surface': 'water surface',
    'sec': 'Secondary flow (f_secflow)\nnear-bed flow toward the inner bank  r = N* h κ',
    'slope': 'Bed-slope term (fluv_slope)\ndown the transverse slope  q⃗ = q_b(t̂ − γ∇z)',
    'inner': 'inner bank: deposition (bar)', 'outer': 'outer bank: scour (pool)',
    'plan': 'Plan', 'pin': 'inner', 'pout': 'outer', 'center': 'centre of\ncurvature', 'kappa': 'streamline curvature κ',
    'section': 'section A–A′\n(looking downstream)',
    'a_note': 'The secondary flow drags sediment inward while the gravity term moves it down the slope; '
              'their balance sets the transverse slope. Use the two together (either one alone does not reach a balanced slope).',
    'b': '(b) Bank erosion  f_berode',
    'bank': 'bank cell b (ground ≥ toe water surface)',
    'face': 'bank-face edge: no bedload across',
    'shear': 'τ*_w: shear of the toe cell w (wet, h > dd)',
    'eb': 'E_b = K_b (τ*_w / τ*c,b − 1)^m',
    'cut': 'cut', 'put': 'same volume placed',
    'b_note': 'Lowers the bank ground and places the same volume at the toe (sediment conserved; bedload carries it on). '
              'berode_kb is a calibration value with no default. No bank erosion across levee edges (walls of fn_rw).',
    'c': '(c) Angle-of-repose collapse  f_repose',
    'repose': 'dashed: slope at the angle of\nrepose φ_r (repose_phi)',
    'excess': 'excess', 'dist': 'dist',
    'c_rule': 'excess = (z_c − z_n)\n             − dist × tan φ_r\neach update moves\nrelax × excess / 2 / 8 per edge\nfrom c (high) to n (low);\nno overshoot even in 8 directions',
    'after': 'dotted: after many updates\n(relaxed to the repose slope)',
    'c_note': 'Acts wet or dry (dry sand piles, excavated faces, failed material at bank toes) and works without bedload. '
              'One sweep per update, so a collapse propagates one cell at a time in landform time. '
              'Non-cohesive banks retreat by toe scour + collapse alone; do not add the same retreat again through berode_kb.',
    'd': '(d) Self-protection of banks by slump blocks  rf_bank = 1 + berode_hcover',
    'hc': 'critical height H_c (rf_hc)', 'over': 'the excess fails',
    'talus': 'talus ht (slump blocks)', 'shield': 'with talus at the toe, the shear reaching the bank\nface is scaled by (1 − ht / h_cover)⁺ (berode_hcover)',
    'carry': 'removed by outflows',
    'd_note': 'Failed blocks cover the toe and stop bank erosion until the flow removes them. The talus is reduced by '
              'outflows of bedload, bank erosion and repose collapse (inflows do not become talus). Steps below the '
              'water surface (pool walls) do not fail. With f_fixation the critical height becomes H_c (1 + c_τ,b a).',
    'foot': 'Each item is an optional correction on top of f_fluvial = 1 (only f_repose also works without bedload). '
            'Equations and sources of the coefficients: the text and sediment.md §3.',
 },
}


def panel_bend(ax, t):
    panel(ax, 35, 108, t['a'])
    # Cross-section looking downstream: inner bank (left) shallow bar, outer bank (right) pool.
    xs = [50, 95, 140, 200, 260, 320, 380, 430, 462, 482, 496, 504, 510, 548]
    ys = [222, 224, 238, 256, 276, 300, 330, 362, 380, 372, 310, 240, 205, 203]
    level = 250
    ground_px(ax, xs, ys, 460)
    water_px(ax, xs, ys, level)
    text(ax, 210, 232, t['surface'], size=8.2, color=BLUE, ha='center', va='bottom')
    # Helical circulation: outward at the surface, inward near the bed.
    th = np.linspace(0, 2 * np.pi, 200)
    ex, ey = 398 + 74 * np.cos(th), 296 + 30 * np.sin(th)
    line(ax, np.column_stack((ex, ey)), BLUE, .9, ls='--')
    arrow(ax, [(350, 267), (440, 267)], BLUE, lw=1.6, size=11)
    arrow(ax, [(446, 324), (352, 324)], BLUE, lw=1.6, size=11)
    # Bed-slope term: down the transverse slope, drawn just inside the bed.
    arrow(ax, [(232, 282), (392, 352)], SED, lw=1.8, size=11)
    text(ax, 52, 140, t['sec'], size=8.4, color=BLUE)
    text(ax, 60, 384, t['slope'], size=8.4, color=SED)
    text(ax, 52, 472, t['inner'], size=8.6, color=INK)
    text(ax, 548, 472, t['outer'], size=8.6, color=INK, ha='right')
    # Plan-view inset of a left-turning bend; A–A′ is the section on the left.
    cx, cy, rin, rout = 612, 352, 60, 115
    th = np.radians(np.linspace(-55, 95, 80))
    inner = np.column_stack((cx + rin * np.cos(th), cy - rin * np.sin(th)))
    outer = np.column_stack((cx + rout * np.cos(th), cy - rout * np.sin(th)))
    poly(ax, np.vstack([inner, outer[::-1]]), WATER, z=2)
    line(ax, inner, INK, 1.0)
    line(ax, outer, INK, 1.0)
    tc = np.radians(np.linspace(-45, 80, 50))
    arrow(ax, np.column_stack((cx + 88 * np.cos(tc), cy - 88 * np.sin(tc))), BLUE, lw=1.3, size=10)
    a0 = np.radians(12)
    pa = (cx + (rin - 4) * np.cos(a0), cy - (rin - 4) * np.sin(a0))
    pb = (cx + (rout + 6) * np.cos(a0), cy - (rout + 6) * np.sin(a0))
    line(ax, [pa, pb], ORANGE, 1.4, z=9)
    text(ax, pa[0] + 2, pa[1] + 6, 'A', size=8.6, color=ORANGE, ha='left', va='top')
    text(ax, pb[0] + 4, pb[1], 'A′', size=8.6, color=ORANGE, ha='left', va='center')
    ax.plot(cx, cy, 'o', ms=3.5, color=MUTED, zorder=9)
    text(ax, cx - 6, cy + 6, t['center'], size=7.8, color=MUTED, ha='right')
    text(ax, 575, 140, t['plan'], size=8.6, weight='bold', color=MUTED)
    text(ax, cx + 33 * np.cos(np.radians(48)), cy - 33 * np.sin(np.radians(48)), t['pin'], size=7.8, color=INK, ha='center', va='center')
    text(ax, cx + 96, cy + 88, t['pout'], size=7.8, color=INK, ha='left')
    text(ax, 770, 170, t['section'], size=7.8, color=ORANGE, ha='right', va='top')
    block(ax, 35, 505, t['a_note'], 735, size=8.5)


def panel_berode(ax, t):
    x0, w, base, lev = 830, 95, 460, 310
    panel(ax, 805, 108, t['b'])
    tops = [240, 240, 240, 390, 405, 400, 395]
    columns(ax, x0, w, base, tops)
    poly(ax, [(x0 + 3 * w, lev), (x0 + 7 * w, lev), (x0 + 7 * w, 395), (x0 + 6 * w, 395), (x0 + 6 * w, 400),
              (x0 + 5 * w, 400), (x0 + 5 * w, 405), (x0 + 4 * w, 405), (x0 + 4 * w, 390), (x0 + 3 * w, 390)], WATER, z=1)
    line(ax, [(x0 + 3 * w, lev), (x0 + 7 * w, lev)], BLUE, 1.2)
    # Removed part of the bank cell (dashed old top) and the same volume at the toe.
    box(ax, x0 + 2 * w, 240, w, 34, face='white', edge=SED, lw=.9, z=4, hatch='///', ls='--')
    box(ax, x0 + 3 * w, 356, w, 34, face=MOVING, edge=SED, lw=.9, z=4)
    arrow(ax, [(x0 + 2.55 * w, 260), (x0 + 3.0 * w, 280), (x0 + 3.45 * w, 350)], SED, lw=1.6, size=11)
    text(ax, x0 + 1.95 * w, 257, t['cut'], size=8.2, color=SED, ha='right', va='center')
    text(ax, x0 + 4.1 * w, 372, t['put'], size=8.2, color=SED, ha='left', va='center')
    line(ax, [(x0 + 4.08 * w, 372), (x0 + 3.85 * w, 372)], SED, .8, z=9)
    line(ax, [(x0 + 3 * w, 274), (x0 + 3 * w, 390)], ORANGE, 2.6, z=8)
    arrow(ax, [(x0 + 3.1 * w, 336), (x0 + 3.9 * w, 336)], BLUE, lw=1.3, size=9)
    text(ax, x0 + 4.0 * w, 336, t['shear'], size=8.2, color=BLUE, ha='left', va='center')
    text(ax, x0 + 2.5 * w, 226, t['bank'], size=8.3, color=INK, ha='center', va='bottom')
    text(ax, x0 + 3.22 * w, 300, t['face'], size=8.0, color=ORANGE, ha='left', va='bottom')
    box(ax, 1215, 140, 315, 34, face='white', edge=RULE, z=5)
    text(ax, 1372, 157, t['eb'], size=9, color=INK, ha='center', va='center')
    block(ax, 805, 505, t['b_note'], 735, size=8.5)


def panel_repose(ax, t):
    y0 = 610
    panel(ax, 35, y0, t['c'])
    x0, w, base = 55, 66, 950
    tops = [680, 680, 690, 850, 862, 870]
    columns(ax, x0, w, base, tops)
    # Excess of the c → n step over the repose slope (pair 2 → 3).
    tanp = np.tan(np.radians(30))
    xc, xn = x0 + 2.5 * w, x0 + 3.5 * w
    yrep = 850 - w * tanp
    line(ax, [(xn, 850), (xc - 0.9 * w, 850 - 1.9 * w * tanp)], GREEN, 1.4, ls='--')
    box(ax, x0 + 2 * w, 690, w, yrep - 690, face='white', edge=SED, lw=.9, z=4, hatch='///')
    dim(ax, (x0 + 1.9 * w, 690), (x0 + 1.9 * w, yrep), t['excess'], color=SED, offset=(-8, 0), ha='right')
    dim(ax, (xc, 968), (xn, 968), t['dist'], offset=(0, 14))
    line(ax, [(xc, 958), (xc, 978)], MUTED, .7)
    line(ax, [(xn, 958), (xn, 978)], MUTED, .7)
    ax.plot([xc, xn], [690, 850], 'o', ms=3.4, color=INK, zorder=12)
    text(ax, xc + 6, 684, 'c', size=8.6, weight='bold', ha='left', va='bottom')
    text(ax, xn + 6, 844, 'n', size=8.6, weight='bold', ha='left', va='bottom')
    arrow(ax, [(xc + 0.2 * w, 716), (xc + 0.6 * w, 770), (xn - 0.1 * w, 836)], SED, lw=1.6, size=11)
    # After many updates: the step relaxes to a repose-angle staircase (dotted outline). The high
    # side loses about what the low side gains (the remainder spreads further right).
    xs = x0 + np.arange(6) * w
    after = [684, 711, 749, 787, 825, 861]
    pts = []
    for k, top in enumerate(after):
        pts += [(xs[k], top), (xs[k] + w, top)]
    line(ax, pts, GREEN, 1.2, ls=':')
    block(ax, 470, 650, t['repose'], 300, size=8.3, color=GREEN)
    block(ax, 470, 708, t['c_rule'], 300, size=8.3)
    block(ax, 470, 892, t['after'], 300, size=8.3, color=GREEN)
    block(ax, 35, 1000, t['c_note'], 735, size=8.5)


def panel_slump(ax, t):
    y0 = 610
    panel(ax, 805, y0, t['d'])
    x0, w, base, lev = 830, 95, 950, 800
    tops = [700, 700, 700, 880, 895, 890, 885]
    columns(ax, x0, w, base, tops)
    poly(ax, [(x0 + 3 * w, lev), (x0 + 7 * w, lev), (x0 + 7 * w, 885), (x0 + 6 * w, 885), (x0 + 6 * w, 890),
              (x0 + 5 * w, 890), (x0 + 5 * w, 895), (x0 + 4 * w, 895), (x0 + 4 * w, 880), (x0 + 3 * w, 880)], WATER, z=1)
    line(ax, [(x0 + 3 * w, lev), (x0 + 7 * w, lev)], BLUE, 1.2)
    hc = 765
    line(ax, [(x0 + 1.6 * w, hc), (x0 + 4.3 * w, hc)], GREEN, 1.2, ls='--', z=9)
    text(ax, x0 + 4.35 * w, hc, t['hc'], size=8.2, color=GREEN, ha='left', va='center')
    dim(ax, (x0 + 3.5 * w, 880), (x0 + 3.5 * w, hc), None, color=GREEN)
    box(ax, x0 + 2 * w, 700, w, hc - 700, face='white', edge=SED, lw=.9, z=4, hatch='///', ls='--')
    text(ax, x0 + 2.5 * w, 686, t['over'], size=8.2, color=SED, ha='center', va='bottom')
    box(ax, x0 + 3 * w, 846, w, 34, face=TALUS, edge=SED, lw=.9, z=4, hatch='..')
    arrow(ax, [(x0 + 2.6 * w, 722), (x0 + 3.05 * w, 768), (x0 + 3.3 * w, 840)], SED, lw=1.6, size=11)
    text(ax, x0 + 3.5 * w, 962, t['talus'], size=8.3, color=SED, ha='center')
    line(ax, [(x0 + 3.5 * w, 962), (x0 + 3.5 * w, 872)], MUTED, .7, z=9)
    arrow(ax, [(x0 + 3.9 * w, 862), (x0 + 3.1 * w, 862)], BLUE, lw=1.1, size=8, ls='--')
    text(ax, x0 + 3.2 * w, 700, t['shield'], size=8.2, color=BLUE, ha='left')
    line(ax, [(x0 + 3.45 * w, 746), (x0 + 3.7 * w, 856)], MUTED, .7, z=9)
    arrow(ax, [(x0 + 4.05 * w, 830), (x0 + 4.75 * w, 830)], SED, lw=1.4, size=10)
    text(ax, x0 + 4.8 * w, 830, t['carry'], size=8.2, color=SED, ha='left', va='center')
    block(ax, 805, 1000, t['d_note'], 735, size=8.5)


def build(lang):
    t = T[lang]
    fig, ax = canvas(H)
    header(ax, t['title'], t['sub'])
    panel_bend(ax, t)
    panel_berode(ax, t)
    rule(ax, 35, 1540, 592)
    line(ax, [(787, 105), (787, 1095)], RULE, .8)
    panel_repose(ax, t)
    panel_slump(ax, t)
    rule(ax, 35, 1540, 1105)
    block(ax, 35, 1118, t['foot'], 1505, size=8.3, color=MUTED)
    return fig


def draw(lang):
    return run(build, 'geomorph_bank', lang,
               'Schematic of bend cross-section shaping (fluv_slope, f_secflow), bank erosion (f_berode), '
               'angle-of-repose collapse (f_repose) and slump-block protection (rf_bank, berode_hcover). '
               'Raster cells drawn as columns; not solver output.')
