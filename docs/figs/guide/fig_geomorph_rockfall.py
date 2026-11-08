"""Rockfall and talus f_rockfall (geomorph.md): the five raster rules.

(a) how the free-face height is measured (adjacent step vs window drop);
(b) rules 1-3: collapse of the excess over H_c, talus, protection;
(c) rule 4: talus-supported faces and column collapse (one column at a time);
(d) rule 5: collapse by undercutting of a softer foot; (e) parameters by rule.
Columns are raster cells (one z per cell, so no overhang). Heights and
thicknesses are illustrative, not solver output.

Generate: python docs/figs/make_guide_figs.py geomorph_rockfall
"""
import numpy as np
from _geomorph import (canvas, header, panel, rule, box, poly, dim, badge, run,
                       text, block, line, arrow, INK, MUTED, RULE,
                       SOIL, ROCK, WATER, BLUE, SED, GREEN, TALUS, ORANGE, PANEL)

H = 1500
CLIFF, CAP, SOFT = '#cdbf9f', '#a8a294', '#e2cfa4'

T = {
 'ja': {
    'title': '崩落と崖錐の規則  |  ラスタで垂直な崖の崩落・崖錐・保護を近似する(f_rockfall)',
    'sub': 'セルごとに 1 つの z しか持たないので、オーバーハングは表せない。列は格子のセル。高さ・厚さは説明用で、計算結果ではない。',
    'a': '(a) 自由面の高さの測り方',
    'a1': 'rf_rc = 0: 隣接セル間の段差', 'a2': 'rf_rc > 0: 窓内の最低点との落差 H_w',
    'step': '段差 < H_c', 'nofall': '崖が何セルにもまたがると、どの段差も\nH_c に届かず崩れない(Δx に依存する)',
    'win': '窓: 半径 nint(r_c/Δx) セル', 'hw': 'H_w > H_c', 'fall': '面全体が対象になり、\n限界高さが Δx に依らない',
    'b': '(b) 規則 1〜3: 崩落 → 崖錐 → 保護',
    'before': '前', 'after': '後', 'excess': '超過分', 'hc': 'H_c',
    'talus': '崖錐 ht', 'spread': 'ht ≥ h_min の崖錐は\n安息角 φ_t まで動く', 'protect': '崖錐の乾式侵食は\n× rf_ftalus\n(先に崖錐を削る)',
    'rules': ['崩落: 段差が H_c を超えた分を、1 更新に relax × 超過分 / 2 / 8 ずつ高い側から低い側へ移す(保存形)',
              '崖錐: 移った体積は低い側の崖錐 ht になる。ht ≥ h_min の崖錐は安息角 φ_t を超えた分も動く',
              '保護: 崖錐に覆われたセルの乾式侵食 f_splash は rf_ftalus 倍(> 0)。剥離はまず崖錐を減らす'],
    'b_note': '崖錐の除去速度(rf_ftalus × 乾式侵食)が崖の後退速度を律する。',
    'c': '(c) 規則 4: 支え方式(rf_fface ≥ 0、窓版 rf_rc > 0 が前提) — 垂直な面が 1 列ずつ後退する',
    's1': '脚部が崖錐に覆われ、面は支えられる', 's1b': 'H_w ≤ H_c。面の乾式侵食は rf_fface 倍(0 なら削れない)',
    's2': '崖錐が乾式侵食で除かれる', 's2b': '崖錐は rf_ftalus 倍で削れる。H_w が H_c を超える',
    's3': '面の頂の柱が崩落する', 's3b': '低い隣接と同じ高さまで落ちる(1 エッジ・1 更新は tan φ_t × dist / 32 まで)。この柱を脚にする柱は待つ',
    's4': '面は垂直のまま 1 列後退', 's4b': '落ちた柱の岩盤は崖錐の上端の棚として埋もれる。崖錐が厚くなり H_w ≤ H_c で止まる → 1 へ',
    'col': '崩落中', 'wait': '待つ', 'shelf': '棚', 'sup': '支えられた面',
    'c_note': '定常では 後退速度 × 崖高 ≈ 崖錐の除去率 × 崖錐幅。崩落中の柱のフラグは私有ファイル geomorph_rockfall.dat で再開時に引き継ぐ。',
    'd': '(d) 規則 5: 張り出しによる崩落(rf_uc > 0。規則 4 と spl_strata が前提)',
    'capl': 'キャップ(硬い)', 'softl': '軟層(倍率が大)',
    'u': 'u: 前回の埋没以降に\n脚部の岩盤が\n削られた深さ', 'uc': 'u ≥ u_c で頂の柱が落ちる\n(H_w ≤ H_c でも)',
    'd_note': '脚部が柱より軟らかいときだけ働く(同じ材料の斜面では働かない)。崖錐の消耗分は u に数えない。'
              'H_c を面の高さに合わせる較正が要らず、後退速度 ≈ 脚部の岩盤の侵食速度 × Δx / u_c が崖錐の除去に律速される。',
    'e': '(e) パラメータと規則',
    'tab': [('rf_hc', '1', '限界高さ H_c(必須)'), ('rf_rc', '1', '窓の半径 r_c(0 = 隣接の段差)'),
            ('rf_relax', '1', '1 更新に緩和する超過分の割合'), ('rf_phi / rf_hmin', '2', '崖錐の安息角 / 動く最小厚さ'),
            ('rf_ftalus', '3', '崖錐に覆われたセルの乾式侵食の倍率'), ('rf_fface', '4', '支えられた面の倍率(≥ 0 で有効)'),
            ('rf_uc', '5', '限界張り出し量 u_c'), ('rf_bedrock', '—', '土層 sd ≤ 0 の基岩も崩れる'),
            ('rf_bank', '—', '河岸モード(掃流砂の図の (d))')],
    'e_note': '1 エッジ・1 更新の変動は fluv_dzmax で頭打ち(f_fluvial なしでも与える)。海セル(fn_sw)へ崩れた分は系外へ出る。',
    'foot': '既定(rf_bedrock = 0)では崩れる岩は土層 sd の柱として与える(examples/mesa は台地全体を sd = 100 m にして spl_strata で硬さを与える)。',
 },
 'en': {
    'title': 'Rules of rockfall and talus  |  Approximating the collapse, talus and protection of vertical cliffs on a raster (f_rockfall)',
    'sub': 'Each cell has a single z, so overhangs cannot be represented. Columns are grid cells; heights and thicknesses are illustrative, not computed results.',
    'a': '(a) How the free-face height is measured',
    'a1': 'rf_rc = 0: step between adjacent cells', 'a2': 'rf_rc > 0: drop H_w within a window',
    'step': 'step < H_c', 'nofall': 'a cliff spread over several cells has no step\nreaching H_c and never fails (depends on Δx)',
    'win': 'window: radius nint(r_c/Δx) cells', 'hw': 'H_w > H_c', 'fall': 'the whole face is targeted; the\ncritical height does not depend on Δx',
    'b': '(b) Rules 1–3: collapse → talus → protection',
    'before': 'before', 'after': 'after', 'excess': 'excess', 'hc': 'H_c',
    'talus': 'talus ht', 'spread': 'talus with ht ≥ h_min\nmoves to the repose\nangle φ_t', 'protect': 'dry erosion of talus\n× rf_ftalus\n(talus removed first)',
    'rules': ['Collapse: the part of a step above H_c moves from the high to the low side by relax × excess / 2 / 8 per update (conservative)',
              'Talus: the moved volume becomes talus ht on the low side; talus with ht ≥ h_min also moves beyond its repose angle φ_t',
              'Protection: dry erosion f_splash of talus-covered cells is scaled by rf_ftalus (> 0); detachment removes the talus first'],
    'b_note': 'The talus removal rate (rf_ftalus × dry erosion) controls the cliff retreat rate.',
    'c': '(c) Rule 4: talus-supported faces (rf_fface ≥ 0; requires the window, rf_rc > 0) — a vertical face retreats one column at a time',
    's1': 'talus covers the foot: face supported', 's1b': 'H_w ≤ H_c. Dry erosion of the face × rf_fface (0: none)',
    's2': 'dry erosion removes the talus', 's2b': 'talus erodes at rf_ftalus; H_w exceeds H_c',
    's3': 'the top column collapses', 's3b': 'it drops to its lower neighbour\'s height, at most tan φ_t × dist / 32 per edge and update; columns with it as their foot wait',
    's4': 'the face retreats by one column', 's4b': 'still vertical; the fallen rock stays as a buried shelf at the talus top. Thicker talus gives H_w ≤ H_c: collapse stops → 1',
    'col': 'collapsing', 'wait': 'waits', 'shelf': 'shelf', 'sup': 'supported face',
    'c_note': 'In steady state, retreat rate × cliff height ≈ talus removal rate × talus width. Flags of collapsing columns carry over restarts in the private file geomorph_rockfall.dat.',
    'd': '(d) Rule 5: undercut collapse (rf_uc > 0; needs rule 4 and spl_strata)',
    'capl': 'cap (hard)', 'softl': 'soft (larger multiplier)',
    'u': 'u: depth eroded from\nthe foot\'s rock since\nits last burial', 'uc': 'u ≥ u_c drops\nthe top column\n(even with H_w ≤ H_c)',
    'd_note': 'Acts only where the foot is softer than the column (never on a slope of one material). Talus wear does not count in u. '
              'No calibration of H_c to the face height is needed: retreat rate ≈ erosion rate of the foot rock × Δx / u_c, limited by talus removal.',
    'e': '(e) Parameters by rule',
    'tab': [('rf_hc', '1', 'critical height H_c (required)'), ('rf_rc', '1', 'window radius r_c (0 = adjacent step)'),
            ('rf_relax', '1', 'fraction of the excess relaxed per update'), ('rf_phi / rf_hmin', '2', 'talus repose angle / minimum moving thickness'),
            ('rf_ftalus', '3', 'dry-erosion multiplier of talus-covered cells'), ('rf_fface', '4', 'multiplier of supported faces (on if ≥ 0)'),
            ('rf_uc', '5', 'critical undercut u_c'), ('rf_bedrock', '—', 'bedrock with sd ≤ 0 also fails'),
            ('rf_bank', '—', 'bank mode (panel (d) of the bedload figure)')],
    'e_note': 'The change per edge and update is capped by fluv_dzmax (give it even without f_fluvial). Material falling into sea cells (fn_sw) leaves the system.',
    'foot': 'By default (rf_bedrock = 0) the failing rock is given as columns of soil sd (examples/mesa sets sd = 100 m over the whole plateau and gives hardness through spl_strata).',
 },
}


def cells(ax, x0, w, base, rock, talus=None, face=CLIFF, z=3):
    """Rock columns from base up to rock[k]; talus from rock[k] up by talus[k] (pixels)."""
    for k, top in enumerate(rock):
        box(ax, x0 + k * w, top, w, base - top, face=face, edge='#9d8a63', lw=.7, z=z)
        if talus is not None and talus[k] > 0:
            box(ax, x0 + k * w, top - talus[k], w, talus[k], face=TALUS, edge=SED, lw=.6, z=z + 1, hatch='..')


def hc_bar(ax, x, ybot, hc, label='H_c'):
    dim(ax, (x, ybot), (x, ybot - hc), None, color=GREEN)
    text(ax, x + 6, ybot - hc / 2, label, size=8.2, color=GREEN, ha='left', va='center')


def panel_measure(ax, t):
    panel(ax, 35, 108, t['a'])
    w, base, hc = 40, 430, 100
    tops = [200, 200, 200, 250, 300, 350, 400, 400]
    # Adjacent steps: each below H_c.
    x0 = 55
    text(ax, x0, 146, t['a1'], size=8.6, weight='bold', color=MUTED)
    cells(ax, x0, w, base, tops)
    dim(ax, (x0 + 4 * w + 8, 250), (x0 + 4 * w + 8, 300), None, color=ORANGE)
    text(ax, x0 + 4 * w + 14, 262, t['step'], size=8.2, color=ORANGE, ha='left', va='center')
    hc_bar(ax, x0 + 8 * w + 14, 400, hc)
    block(ax, x0, 480, t['nofall'], 340, size=8.3)
    # Window: drop to the lowest point within nint(r_c/dx) cells.
    x0 = 430
    text(ax, x0, 146, t['a2'], size=8.6, weight='bold', color=MUTED)
    cells(ax, x0, w, base, tops)
    c = 3
    xc = x0 + (c + .5) * w
    ax.plot(xc, 250, 'o', ms=4, color=INK, zorder=12)
    text(ax, xc, 242, 'c', size=8.4, weight='bold', ha='center', va='bottom')
    line(ax, [(x0, 438), (x0, 444), (x0 + 7 * w, 444), (x0 + 7 * w, 438)], BLUE, 1.0, z=12)
    text(ax, x0 + 3.5 * w, 450, t['win'], size=7.9, color=BLUE, ha='center', va='top')
    line(ax, [(xc, 400), (x0 + 7 * w, 400)], BLUE, .8, ls='--', z=12)
    ax.plot(x0 + 6.5 * w, 400, 'o', ms=4, color=BLUE, zorder=12)
    dim(ax, (xc + 10, 250), (xc + 10, 400), None, color=ORANGE)
    text(ax, xc + 16, 330, t['hw'], size=8.2, color=ORANGE, ha='left', va='center')
    hc_bar(ax, x0 + 8 * w + 14, 400, hc)
    block(ax, x0, 480, t['fall'], 340, size=8.3)


def panel_rules123(ax, t):
    panel(ax, 805, 108, t['b'])
    w, base, hc = 42, 380, 100
    rock = [190, 190, 190, 190, 340, 340]
    xb, xa = 820, 1110
    text(ax, xb, 146, t['before'], size=8.6, weight='bold', color=MUTED)
    text(ax, xa, 146, t['after'], size=8.6, weight='bold', color=MUTED)
    # Before: the step c → n is 150 > H_c; the top 50 is the excess.
    cells(ax, xb, w, base, rock)
    box(ax, xb + 3 * w, 190, w, 50, face='white', edge=SED, lw=.9, z=5, hatch='///')
    text(ax, xb + 3.5 * w, 184, t['excess'], size=8.2, color=SED, ha='center', va='bottom')
    arrow(ax, [(xb + 3.6 * w, 215), (xb + 4.2 * w, 250), (xb + 4.5 * w, 332)], SED, lw=1.5, size=10)
    line(ax, [(xb + 3 * w, 240), (xb + 6 * w + 12, 240)], GREEN, .8, ls=':', z=6)
    hc_bar(ax, xb + 6 * w + 12, 340, hc, t['hc'])
    # After: half the excess moved; the low side holds it as talus, which spreads and protects.
    rock_a = [190, 190, 190, 215, 340, 340]
    tal = [0, 0, 0, 0, 18, 7]
    cells(ax, xa, w, base, rock_a, tal)
    line(ax, [(xa + 3 * w, 190), (xa + 4 * w, 190)], SED, .8, ls='--', z=6)
    arrow(ax, [(xa + 4.7 * w, 318), (xa + 5.6 * w, 328)], SED, lw=1.2, size=8)
    for xr in [xa + 4.2 * w, xa + 4.7 * w, xa + 5.4 * w]:
        line(ax, [(xr + 4, 278), (xr, 298)], BLUE, .9)
    lx = xa + 6 * w + 14
    text(ax, lx, 192, t['talus'], size=8.2, color=SED)
    line(ax, [(lx - 4, 202), (xa + 4.5 * w, 318)], MUTED, .7, z=9)
    text(ax, lx, 224, t['protect'], size=7.9, color=BLUE)
    text(ax, lx, 306, t['spread'], size=7.9, color=SED)
    y = 405
    for k, s in enumerate(t['rules']):
        badge(ax, 818, y + 10, str(k + 1), r=10, size=7.6)
        a = block(ax, 838, y, s, 700, size=8.2)
        y += 22 * (a.get_text().count('\n') + 1) + 6
    block(ax, 805, y + 4, t['b_note'], 735, size=8.3, color=SED)


def panel_rule4(ax, t):
    y0 = 665
    panel(ax, 35, y0, t['c'])
    w, base = 44, 965
    hc = 160
    dy = 125
    states = [
        ([640, 640, 640, 640, 820, 820, 820], [0, 0, 0, 0, 60, 30, 8]),
        ([640, 640, 640, 640, 820, 820, 820], [0, 0, 0, 0, 25, 8, 0]),
        ([640, 640, 640, 720, 820, 820, 820], [0, 0, 0, 0, 45, 25, 8]),
        ([640, 640, 640, 795, 820, 820, 820], [0, 0, 0, 35, 75, 53, 25]),
    ]
    xs = [45, 422, 799, 1176]
    for k, ((rock, tal), x0) in enumerate(zip(states, xs)):
        badge(ax, x0 + 10, y0 + 50, str(k + 1), r=11, size=8)
        text(ax, x0 + 28, y0 + 40, t[f's{k + 1}'], size=8.6, weight='bold')
        cells(ax, x0, w, base, [r + dy for r in rock], tal)
        hc_bar(ax, x0 + 7 * w + 14, 640 + dy + hc, hc)   # hangs from the plateau top
        line(ax, [(x0 + 4 * w, 640 + dy + hc), (x0 + 7 * w + 14, 640 + dy + hc)], GREEN, .7, ls=':', z=9)
        block(ax, x0, 980, t[f's{k + 1}b'], 350, size=8.1)
    # 1: supported face (foot covered by talus).
    x0 = xs[0]
    line(ax, [(x0 + 4 * w, 640 + dy), (x0 + 4 * w, 820 + dy)], GREEN, 2.4, z=8)
    text(ax, x0 + 4 * w + 6, 650 + dy, t['sup'], size=7.9, color=GREEN, ha='left', va='top')
    # 2: talus being removed by dry erosion.
    x0 = xs[1]
    for xr in [x0 + 4.3 * w, x0 + 4.8 * w, x0 + 5.4 * w, x0 + 6.0 * w]:
        line(ax, [(xr + 4, 740 + dy), (xr, 762 + dy)], BLUE, .9)
    arrow(ax, [(x0 + 4.5 * w, 792 + dy), (x0 + 4.9 * w, 770 + dy)], SED, lw=1.2, size=8)
    # 3: the top column collapses; the column behind waits.
    x0 = xs[2]
    box(ax, x0 + 3 * w, 640 + dy, w, 80, face='white', edge=SED, lw=.9, z=6, ls='--')
    arrow(ax, [(x0 + 3.5 * w, 690 + dy), (x0 + 4.3 * w, 720 + dy), (x0 + 4.6 * w, 768 + dy)], SED, lw=1.5, size=10)
    text(ax, x0 + 3.05 * w, 636 + dy, t['col'], size=7.6, color=ORANGE, ha='left', va='bottom')
    text(ax, x0 + 2.9 * w, 636 + dy, t['wait'], size=7.6, color=MUTED, ha='right', va='bottom')
    # 4: retreated face; buried shelf.
    x0 = xs[3]
    line(ax, [(x0 + 3 * w, 640 + dy), (x0 + 4 * w, 640 + dy)], SED, .8, ls='--', z=6)
    line(ax, [(x0 + 3 * w, 640 + dy), (x0 + 3 * w, 760 + dy)], GREEN, 2.4, z=8)
    text(ax, x0 + 3.5 * w, 812 + dy, t['shelf'], size=7.9, color=INK, ha='center', va='center')
    block(ax, 35, 1062, t['c_note'], 1505, size=8.3, color=SED)
    for xv in xs[1:]:
        line(ax, [(xv - 14, y0 + 36), (xv - 14, 1048)], RULE, .7)


def panel_rule5(ax, t):
    y0 = 1122
    panel(ax, 35, y0, t['d'])
    w, base = 44, 1400
    x0 = 50
    rock = [1210, 1210, 1210, 1210, 1320, 1320, 1320, 1320]
    cap_bot = 1260
    for k, top in enumerate(rock):
        xk = x0 + k * w
        if top < cap_bot:
            box(ax, xk, top, w, cap_bot - top, face=CAP, edge='#7d776b', lw=.7, z=3)
            box(ax, xk, cap_bot, w, base - cap_bot, face=SOFT, edge='#9d8a63', lw=.7, z=3)
        else:
            box(ax, xk, top, w, base - top, face=SOFT, edge='#9d8a63', lw=.7, z=3)
    line(ax, [(x0, cap_bot), (x0 + 8 * w, cap_bot)], MUTED, .7, ls=':', z=6)
    text(ax, x0 + 8, 1235, t['capl'], size=7.9, color='white', ha='left', va='center')
    text(ax, x0 + 4, 1392, t['softl'], size=7.9, color=INK, ha='left', va='bottom')
    # Foot rock eroded by u since the last burial.
    box(ax, x0 + 4 * w, 1320, w, 26, face='white', edge=SED, lw=.9, z=5, hatch='///')
    dim(ax, (x0 + 5 * w + 8, 1320), (x0 + 5 * w + 8, 1346), None, color=SED)
    text(ax, x0 + 5.4 * w, 1322, t['u'], size=7.9, color=SED, ha='left', va='top')
    box(ax, x0 + 3 * w, 1210, w, 50, face='white', edge=ORANGE, lw=1.0, z=6, ls='--', fill=False)
    arrow(ax, [(x0 + 3.5 * w, 1230), (x0 + 4.2 * w, 1262), (x0 + 4.5 * w, 1312)], ORANGE, lw=1.5, size=10)
    text(ax, x0 + 4.3 * w, 1206, t['uc'], size=8.0, color=ORANGE, ha='left', va='top')
    block(ax, 470, 1164, t['d_note'], 300, size=8.1)


def panel_params(ax, t):
    y0 = 1122
    panel(ax, 805, y0, t['e'])
    y = y0 + 40
    for name, r, desc in t['tab']:
        text(ax, 815, y, name, size=8.2, color=SED)
        text(ax, 975, y, r, size=8.2, ha='center')
        text(ax, 1000, y, desc, size=8.2)
        y += 23
    block(ax, 805, y + 8, t['e_note'], 735, size=8.1, color=MUTED)


def build(lang):
    t = T[lang]
    fig, ax = canvas(H)
    header(ax, t['title'], t['sub'])
    panel_measure(ax, t)
    line(ax, [(787, 105), (787, 640)], RULE, .8)
    panel_rules123(ax, t)
    rule(ax, 35, 1540, 650)
    panel_rule4(ax, t)
    rule(ax, 35, 1540, 1104)
    line(ax, [(787, 1112), (787, 1430)], RULE, .8)
    panel_rule5(ax, t)
    panel_params(ax, t)
    rule(ax, 35, 1540, 1438)
    block(ax, 35, 1448, t['foot'], 1505, size=8.1, color=MUTED)
    return fig


def draw(lang):
    return run(build, 'geomorph_rockfall', lang,
               'Schematic of the raster rules of f_rockfall: free-face height (adjacent step or window drop), '
               'collapse of the excess over H_c into talus and protection, talus-supported column collapse and '
               'undercut collapse. Columns are grid cells; not solver output.')
