"""Dense snow avalanche read through the sediment model (geomorph_applications.md §5).

Cross-section of a slope showing how the sediment containers are read for
snow (z = snow-surface elevation, sd = entrainable snow on the path, z - sd =
ground, release depth D of fn_dbinit, hs = flowing snow, f_dbstop deposit),
the settings, and what cannot be done. Schematic following the text; not solver
output.

Generate: python docs/figs/make_guide_figs.py geomorph_app_avalanche
"""
import numpy as np
from _geomorph import (canvas, header, panel, rule, box, poly, dim, run, text, kblock as block, line, arrow,
                       INK, MUTED, RULE, SED, GREEN, BLUE, ORANGE, ROCK, PANEL)

H = 760
SNOW, SNOW_EDGE, FLOW, DEBRIS = '#f3f6fa', '#8ea3ba', '#c9d8e8', '#dfe7f0'

T = {
 'ja': {
    'title': '流れ型雪崩の読み替え  |  土砂の入れ物を雪の言葉で使う',
    'sub': '適用例 §5 の設定の型。Voellmy 則は駆動も抵抗も加速度の形で密度が相殺するので、雪が水より軽くても同じ式で到達距離を解ける。断面は模式。',
    'a': '(a) 断面で見た対応(パラメータ名は土砂の語彙のまま)',
    'rel': '発生区: fn_dbinit の崩壊深 D\n= 破断深(db_reltime に発生)',
    'snow': 'sd = 走路の連行できる\n雪の厚さ', 'surf': 'z = 雪面込みの標高',
    'ground': 'z − sd = 地山', 'flow': 'hs = 流動中の雪\n(連行で育つ)', 'ent': '連行 E = δe |V|\n(f_dbed = 4)',
    'scour': '通過後は雪が\n削られて薄い', 'dep': '停止した雪(デブリ)\n= f_dbstop の河床固定',
    'b': '(b) 設定の型',
    'items': [
        'f_debris = 1、f_dbed = 4(連行。不要なら 0)、f_dbstop = 1',
        'f_dbres = 4: μ = db_mu ≈ 0.15〜0.3、ξ = db_xi ≈ 1000〜3000 m/s²(雪崩の慣用域)',
        '発生区と破断深は fn_dbinit の分布、発生時刻は db_reltime',
        '走路の雪の厚さは sd(sd0 / fn_sd)。連行係数 db_delte は 0.01〜0.05 程度から校正',
        'fluv_porosity を小さめ(例 0.1)にすると hs ≈ 雪厚の読み',
        'db_relsat は小さめ(0.1〜0.15)。混ぜる少量の水が停止後に残って流れる癖がある',
        '急斜面なので f_gravity_correction を 0 にしない(既定 2)',
    ],
    'c': '(c) できないこと',
    'limits': [
        '煙型(粉雪)雪崩: 空気中のサスペンションは浅水近似の外',
        '発生の予測: 発生域・破断深は入力(雪崩の専用モデルも同じ。実務ではシナリオとして与える)',
        '衝撃圧の絶対値: F9999 は清水の密度が基準。流動雪の密度 200〜400 kg/m³ で読み替える',
        '積雪(SWE)との自動連成: 冬季の積雪計算からつなぐには、SWE を前処理で sd に変換する',
    ],
    'foot': '例題 test/avalanche(放出 → 連行で成長 → 平坦部で停止、固体の台帳は機械精度)。Voellmy の等流の解析解は test/volcano で検定。実事例のランアウトとの突合は未実施。',
 },
 'en': {
    'title': 'Reading a dense snow avalanche through the sediment model  |  Sediment containers in the language of snow',
    'sub': '§5 of the applications page. Voellmy driving and resistance are both accelerations, so density cancels for snow. Schematic section.',
    'a': '(a) Correspondence on a section (parameter names keep the sediment vocabulary)',
    'rel': 'release zone: release depth D of\nfn_dbinit = fracture depth (at db_reltime)',
    'snow': 'sd = entrainable\nsnow on the path', 'surf': 'z = elevation including the snow surface',
    'ground': 'z − sd = ground', 'flow': 'hs = flowing snow\n(grows by entrainment)', 'ent': 'entrainment\nE = δe |V| (f_dbed = 4)',
    'scour': 'after passage the\nsnow is scoured thin', 'dep': 'stopped snow (debris)\n= bed fixing of f_dbstop',
    'b': '(b) Setup pattern',
    'items': [
        'f_debris = 1, f_dbed = 4 (entrainment; 0 if not needed), f_dbstop = 1',
        'f_dbres = 4: μ = db_mu ≈ 0.15–0.3, ξ = db_xi ≈ 1000–3000 m/s² (usual range for avalanches)',
        'release zone and fracture depth: the fn_dbinit map; release time: db_reltime',
        'snow thickness on the path: sd (sd0 / fn_sd); calibrate db_delte starting from about 0.01–0.05',
        'a small fluv_porosity (e.g. 0.1) makes hs read as snow thickness',
        'a small db_relsat (0.1–0.15); the little water mixed in tends to remain and flow after stopping',
        'steep slopes: do not set f_gravity_correction to 0 (default 2)',
    ],
    'c': '(c) What cannot be done',
    'limits': [
        'powder (airborne) avalanches: a suspension in air is outside the shallow-water approximation',
        'predicting release: release zones and depths are inputs (also in dedicated avalanche models; practice gives them as scenarios)',
        'absolute impact pressure: F9999 uses the density of clear water; rescale with a flowing-snow density of 200–400 kg/m³',
        'automatic coupling with the snowpack (SWE): convert SWE to sd in preprocessing to start from a winter snow run',
    ],
    'foot': 'Example test/avalanche (release → growth by entrainment → stop on the flat; solid ledger at machine precision). The Voellmy uniform-flow solution is checked in test/volcano. Runouts of real events have not been compared.',
 },
}


def profile(x, x0, x1, ytop, ybot, k=2.6):
    s = (np.asarray(x, float) - x0) / (x1 - x0)
    return ytop + (ybot - ytop) * (1 - np.exp(-k * s)) / (1 - np.exp(-k))


def panel_section(ax, t):
    panel(ax, 35, 108, t['a'])
    x0, x1, ytop, ybot, base = 50, 900, 190, 470, 505
    xs = np.linspace(x0, x1, 300)
    yg = profile(xs, x0, x1, ytop, ybot)                       # ground (z - sd)
    snow = np.full_like(xs, 16.0)                              # snow cover thickness (px)
    scour = (xs > 230) & (xs < 610)
    snow[scour] = 16.0 - 9.0 * np.sin(np.pi * (xs[scour] - 230) / 380) ** .4
    rel = xs < 200
    snow[rel] = 22.0
    ys = yg - snow                                             # snow surface (z)
    poly(ax, list(zip(xs, yg)) + [(x1, base), (x0, base)], ROCK, z=2)
    poly(ax, list(zip(xs, ys)) + list(zip(xs[::-1], yg[::-1])), SNOW, z=3)
    line(ax, list(zip(xs, ys)), SNOW_EDGE, 1.1, z=6)
    line(ax, list(zip(xs, yg)), INK, 1.0, z=6)
    # Release slab outline and depth D.
    k0, k1 = np.searchsorted(xs, 70), np.searchsorted(xs, 195)
    line(ax, list(zip(xs[k0:k1], ys[k0:k1])) + [(xs[k1], yg[k1]), (xs[k0], yg[k0]), (xs[k0], ys[k0])], ORANGE, 1.4,
         ls='--', z=8)
    dim(ax, (130, float(profile(130, x0, x1, ytop, ybot)) - 22), (130, float(profile(130, x0, x1, ytop, ybot))), None,
        color=ORANGE)
    text(ax, 235, 160, t['rel'], size=7.8, color=ORANGE)
    line(ax, [(232, 186), (185, 252)], ORANGE, .8, z=9)
    # Flowing avalanche with entrainment.
    xa, xb = 380, 520
    m = (xs >= xa) & (xs <= xb)
    hth = 30 * np.sin(np.pi * (xs[m] - xa) / (xb - xa)) ** .6
    poly(ax, list(zip(xs[m], ys[m])) + list(zip(xs[m][::-1], (ys[m] - hth)[::-1])), FLOW, edge=SNOW_EDGE, lw=.8, z=7)
    arrow(ax, [(440, float(np.interp(440, xs, ys)) - 44), (545, float(np.interp(545, xs, ys)) - 34)], INK, lw=1.4, size=10)
    for xe in (500, 530):
        ye = float(np.interp(xe, xs, ys))
        arrow(ax, [(xe, ye + 6), (xe - 6, ye - 12)], BLUE, lw=1.1, size=7)
    text(ax, 450, float(np.interp(450, xs, ys)) - 92, t['flow'], size=7.8, ha='center')
    text(ax, 548, float(np.interp(548, xs, yg)) + 14, t['ent'], size=7.6, color=BLUE)
    text(ax, 330, float(np.interp(420, xs, yg)) + 40, t['scour'], size=7.4, color=INK, ha='center')
    line(ax, [(360, float(np.interp(420, xs, yg)) + 38), (420, float(np.interp(420, xs, yg)) - 4)], INK, .7, z=9)
    # Deposit.
    xd0, xd1 = 680, 870
    md = (xs >= xd0) & (xs <= xd1)
    dth = 22 * np.sin(np.pi * (xs[md] - xd0) / (xd1 - xd0)) ** .5
    poly(ax, list(zip(xs[md], ys[md])) + list(zip(xs[md][::-1], (ys[md] - dth)[::-1])), DEBRIS, edge=SNOW_EDGE, lw=.9, z=7)
    text(ax, 880, float(np.interp(775, xs, ys)) - 76, t['dep'], size=7.6, ha='right')
    # Labels of the layers.
    ysf = float(np.interp(640, xs, ys))
    text(ax, 600, ysf - 108, t['surf'], size=7.8, color='#5f7790')
    line(ax, [(640, ysf - 86), (640, ysf - 2)], '#5f7790', .8, z=9)
    text(ax, 70, 338, t['snow'], size=7.8, color=INK)
    line(ax, [(120, 335), (205, float(np.interp(205, xs, yg)) - 6)], INK, .7, z=9)
    text(ax, 600, 485, t['ground'], size=7.8, color=INK)


def panel_items(ax, t):
    x0 = 935
    panel(ax, x0, 108, t['b'])
    y = 146
    for s in t['items']:
        a = block(ax, x0 + 14, y, s, 590, size=7.9)
        text(ax, x0, y, '•', size=7.9)
        y += 22 * (a.get_text().count('\n') + 1) + 6


def panel_limits(ax, t):
    y0 = 535
    panel(ax, 35, y0, t['c'])
    w = 372
    for k, s in enumerate(t['limits']):
        x = 35 + k * (w + 6)
        box(ax, x, y0 + 30, w, 112, face=PANEL, z=0)
        text(ax, x + 12, y0 + 40, f'({k + 1})', size=8.2, weight='bold', color=SED)
        block(ax, x + 44, y0 + 40, s, w - 56, size=7.8)


def build(lang):
    t = T[lang]
    fig, ax = canvas(H)
    header(ax, t['title'], t['sub'])
    panel_section(ax, t)
    line(ax, [(918, 105), (918, 520)], RULE, .8)
    panel_items(ax, t)
    rule(ax, 35, 1540, 527)
    panel_limits(ax, t)
    rule(ax, 35, 1540, 690)
    block(ax, 35, 698, t['foot'], 1505, size=7.6, color=MUTED)
    return fig


def draw(lang):
    return run(build, 'geomorph_app_avalanche', lang,
               'Schematic section of a dense snow avalanche read through the sediment model: snow-surface elevation z, '
               'entrainable snow sd, ground z - sd, release depth D, flowing snow hs and the stopped deposit, with the '
               'settings and the limits. Not solver output.')
