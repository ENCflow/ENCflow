"""Representing sabo facilities (geomorph_applications.md §6).

Longitudinal sketches of a sediment-retarding basin (excavation in z), an
impermeable check dam (dam body in z with sd = 0; filling, full, overtopping)
and the approximation of a permeable dam by a culvert (water passes, sediment is
fully trapped: an upper bound of capture), and the with/without comparison.
Schematic following the text; not solver output.

Generate: python docs/figs/make_guide_figs.py geomorph_app_sabo
"""
import numpy as np
from matplotlib.patches import Rectangle
from _geomorph import (canvas, header, panel, rule, box, poly, badge, run, text, kblock as block, line, arrow,
                       INK, MUTED, RULE, SED, GREEN, BLUE, ORANGE, SOIL, ROCK, WATER, MOVING, TALUS, PANEL)

H = 690
W = 480

T = {
 'ja': {
    'title': '砂防施設の表し方  |  地形と土層厚で施設を置き、あり・なしの 2 ケースで比べる',
    'sub': '適用例 §6 の設定の型。縦断は模式で、計算結果ではない。',
    'a': '(a) 遊砂地', 'b': '(b) 不透過型砂防堰堤', 'c': '(c) 透過型(スリット・グリッド)の近似',
    'exc': '掘り込み・拡幅\n(前処理で z に与える)', 'dep': '減速して堆積\n(f_dbstop = 1 で固定)',
    'dam': '堤体を z に足す\n(その範囲は sd = 0)', 's1': '① 堆砂', 's2': '② 満砂', 's3': '③ 天端越流',
    'culv': 'カルバート\n(水と溶存物質だけ)', 'trap': '土砂は全量捕捉',
    'a_list': [
        '勾配の緩和と減速による堆積は自動で働く',
        '捕捉率 = 施設内の堆積量 / 流入土砂量。下流への通過量と合わせて Hs・z の時間発展と D9999・F9999 から求める',
    ],
    'b_list': [
        '堆砂 → 満砂 → 天端越流の時間発展が自動で出る(天然ダムの形成・越流と同じ枠組み)',
        'セル幅より薄い壁は河道の堤防(bank)でも表せる。越流時は hs も実フラックスで一緒に越える',
        '例題 examples/ashfall_lahar(谷の出口の手前の高さ 5 m の堰堤)',
    ],
    'c_list': [
        '単一粒径なので、粗礫・流木を選んで捕まえ細粒と水を通す選択性は表せない',
        '堤体にカルバートの抜き口を与えると「水は通し土砂は全量捕捉」= 捕捉の上限側の評価。満砂後は天端越流で通過',
        '流木もカルバートを通らないので同じく上限側(部材間隔と流木長の幾何的な捕捉は流木モジュールでも対象外)',
    ],
    'cmp': '施設あり・なしの 2 ケースで比べる: 差は入力(地形と設定)だけで、結果はランク数・スレッド数によらずビット再現するので、2 ケースの差がそのまま施設の効果(数値誤差と切り分けられる)。',
 },
 'en': {
    'title': 'Representing sabo facilities  |  Place them with terrain and soil depth, compare runs with and without',
    'sub': 'Setup patterns of §6 of the applications page. Profiles are sketches, not computed results.',
    'a': '(a) Sediment-retarding basin', 'b': '(b) Impermeable check dam', 'c': '(c) Approximating a permeable (slit, grid) dam',
    'exc': 'excavation and widening\n(given in z by preprocessing)', 'dep': 'slows and deposits\n(fixed with f_dbstop = 1)',
    'dam': 'dam body added to z\n(sd = 0 there)', 's1': '① filling', 's2': '② full', 's3': '③ overtopping',
    'culv': 'culvert (water and\ndissolved matter only)', 'trap': 'all sediment trapped',
    'a_list': [
        'deposition by the gentler slope and slower flow works by itself',
        'capture ratio = deposit in the facility / sediment inflow; with the downstream passage, from the evolution of Hs and z and from D9999 and F9999',
    ],
    'b_list': [
        'filling → full → overtopping develops by itself (the same framework as natural-dam formation and overtopping)',
        'a wall thinner than a cell can be a channel bank (bank); on overtopping, hs passes with the real flux',
        'example: examples/ashfall_lahar (a 5 m dam just upstream of the valley outlet)',
    ],
    'c_list': [
        'single grain size: selective trapping of coarse gravel and wood while passing fines and water is not represented',
        'a culvert outlet in the dam body gives "water passes, all sediment is trapped" = an upper bound of capture; after filling, sediment passes by overtopping',
        'wood does not pass a culvert either, so also an upper bound (geometric trapping by bar spacing and log length is outside the driftwood module too)',
    ],
    'cmp': 'Compare two runs, with and without the facility: they differ only in the inputs (terrain and settings), and results are bit-reproducible whatever the numbers of ranks and threads, so the difference is the effect of the facility (separated from numerical error).',
 },
}


def ground_line(x0, x1, ya, yb, n=120):
    xs = np.linspace(x0, x1, n)
    return xs, ya + (yb - ya) * (xs - x0) / (x1 - x0)


def bullets(ax, x, y, items, width, size=7.9):
    for s in items:
        a = block(ax, x + 14, y, s, width - 14, size=size)
        text(ax, x, y, '•', size=size)
        y += 22 * (a.get_text().count('\n') + 1) + 5
    return y


def basin(ax, x0, t):
    xs, ys = ground_line(x0, x0 + W, 200, 300)
    e0, e1, d = x0 + 170, x0 + 340, 34
    yg = ys.copy()
    m = (xs > e0) & (xs < e1)
    ramp = np.minimum(1, np.minimum((xs - e0) / 25, (e1 - xs) / 25))
    yg[m] = ys[m] + d * ramp[m]
    poly(ax, list(zip(xs, yg)) + [(x0 + W, 345), (x0, 345)], SOIL, z=2)
    line(ax, list(zip(xs, ys)), MUTED, .9, ls='--', z=5)
    line(ax, list(zip(xs, yg)), INK, 1.2, z=6)
    # Deposit in the basin and the arriving flow.
    yd = np.minimum(yg, ys + 14)
    md = (xs > e0 + 5) & (xs < e1 - 5)
    poly(ax, list(zip(xs[md], yg[md])) + list(zip(xs[md][::-1], yd[md][::-1])), TALUS, z=4)
    mf = xs < e0 + 30
    poly(ax, list(zip(xs[mf], ys[mf])) + list(zip(xs[mf][::-1], (ys[mf] - 12)[::-1])), MOVING, z=4)
    arrow(ax, [(x0 + 60, 180), (x0 + 140, 196)], INK, lw=1.4, size=10)
    text(ax, (e0 + e1) / 2, 150, t['exc'], size=7.6, ha='center')
    text(ax, (e0 + e1) / 2 + 20, 302, t['dep'], size=7.6, ha='center')


def dam(ax, x0, t, culvert=False):
    xs, ys = ground_line(x0, x0 + W, 200, 300)
    xd, wd, hd = x0 + 300, 16, 50
    yb = float(np.interp(xd, xs, ys))
    poly(ax, list(zip(xs, ys)) + [(x0 + W, 345), (x0, 345)], SOIL, z=2)
    line(ax, list(zip(xs, ys)), INK, 1.2, z=6)
    crest = yb - hd
    # Deposit behind the dam (full to the crest).
    mf = xs <= xd
    ytop = np.minimum(ys, crest + (xd - xs) * 0.06)
    poly(ax, list(zip(xs[mf], ys[mf])) + list(zip(xs[mf][::-1], ytop[mf][::-1])), TALUS, z=3)
    body = Rectangle((xd, crest), wd, yb - crest + 2, facecolor=ROCK, edgecolor=INK, lw=1.0, zorder=7)
    ax.add_patch(body)
    if not culvert:
        y1 = np.minimum(ys, yb - 22 + (xd - xs) * 0.12)
        line(ax, list(zip(xs[mf], y1[mf])), SED, 1.0, ls='--', z=5)
        text(ax, xd - 92, float(np.interp(xd - 60, xs, y1)) + 4, t['s1'], size=7.4, color=SED)
        text(ax, xd - 150, float(np.interp(xd - 150, xs, ytop)) - 22, t['s2'], size=7.4, color=SED)
        arrow(ax, [(xd - 30, crest - 10), (xd + wd + 22, crest - 4), (xd + wd + 42, yb - 10)], MOVING, lw=2.0, size=10)
        text(ax, xd + 30, crest - 34, t['s3'], size=7.4, color=SED)
        text(ax, xd - 40, 300, t['dam'], size=7.4)
    else:
        box(ax, xd - 2, yb - 9, wd + 4, 8, face=WATER, edge=BLUE, lw=.8, z=8)
        arrow(ax, [(xd - 40, yb - 5), (xd + wd + 46, yb - 2)], BLUE, lw=1.4, size=9)
        text(ax, xd - 40, 300, t['culv'], size=7.4, color=BLUE)
        text(ax, xd - 170, float(np.interp(xd - 120, xs, ytop)) - 24, t['trap'], size=7.6, color=SED)


def build(lang):
    t = T[lang]
    fig, ax = canvas(H)
    header(ax, t['title'], t['sub'])
    cols = [35, 545, 1055]
    for x0, key in zip(cols, ('a', 'b', 'c')):
        panel(ax, x0, 108, t[key])
    basin(ax, cols[0], t)
    dam(ax, cols[1], t)
    dam(ax, cols[2], t, culvert=True)
    bullets(ax, cols[0], 362, t['a_list'], W)
    bullets(ax, cols[1], 362, t['b_list'], W)
    bullets(ax, cols[2], 362, t['c_list'], W)
    for xs in (527, 1037):
        line(ax, [(xs, 105), (xs, 585)], RULE, .8)
    rule(ax, 35, 1540, 593)
    box(ax, 35, 603, 1505, 64, face=PANEL, z=0)
    block(ax, 50, 612, t['cmp'], 1475, size=8.2)
    return fig


def draw(lang):
    return run(build, 'geomorph_app_sabo', lang,
               'Schematic profiles of a sediment-retarding basin, an impermeable check dam (filling, full, overtopping) '
               'and a permeable dam approximated by a culvert (all sediment trapped), with the with/without comparison. '
               'Not solver output.')
