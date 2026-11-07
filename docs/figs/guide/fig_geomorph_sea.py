"""How to represent the sea for sediment and landform processes (geomorph.md):
ordinary cells with an initial water level versus the sea mask fn_sw.

Left: the sea as ordinary cells (all processes act; deposits form offshore).
Right: sea-mask cells (no flow is solved and no landform update; each sediment
path meets a different boundary). Schematic, not solver output.

Generate: python docs/figs/make_guide_figs.py geomorph_sea
"""
import numpy as np
from _geomorph import (canvas, header, panel, rule, box, poly, cross, water_px, ground_px, run,
                       text, block, line, arrow, INK, MUTED, RULE,
                       SOIL, WATER, BLUE, SED, MOVING, GREEN, ORANGE, PANEL)

H = 826
MASK = '#9fc1de'

T = {
 'ja': {
    'title': '海の表し方と土砂の行き先  |  通常セル+初期水位と、海域マスク fn_sw の違い',
    'sub': '土砂・地形の計算では、海の表し方で結果が変わる。関心域の海は通常セルで表し、海域マスクを使うなら関心域より沖に置く。断面は説明用。',
    'a': '(a) 通常セル+初期水位(f_htype = 2。沖の辺は f_bc = 2)',
    'a_items': ['流れを解き、全ての地形過程が水中のセルにも働く',
                '浮遊砂は沈降して海底に積もる(津波堆積物・河口テラス・デルタ)',
                '掃流砂は汀線を越えて沖へ運ばれる',
                '動く底層(f_bedslide)は水中を走り、水面の変位が波を起こす'],
    'b': '(b) 海域マスク sw > 0 のセル',
    'mask': '海域マスク: 流れを解かず、地形も更新しない',
    'b_items': [('浮遊砂・土石流の hs・流木', '海セルへ出ると系外へ(吸い込み)。海からの流入は清水'),
                ('掃流砂', '海セルとの境界エッジを通らない(壁)。海側の前面に溜まる'),
                ('崩落(f_rockfall)', '海セルへ崩れた分は系外へ(海セルの z は変わらない)'),
                ('土石流の河床勾配', '海側の近傍を勾配 0 として扱う(落ち込みの加速は起きない)'),
                ('沿岸漂砂(fn_wave)', '源にも砕波帯にもならず、平滑化では陸(水深 0)として扱う')],
    'shore': '汀線', 'sea': '海', 'land': '陸',
    'dep': '海底への堆積', 'pile': '前面に溜まる', 'out': '系外へ',
    'foot': '海セルの z は利用者が置けない(読み込み時に 0。fn_tide ありでは毎ステップ 潮位 − hsea0)。潮位を与えるときは沖の辺に海域マスクの帯を置く(適用例の河口デルタ)。',
 },
 'en': {
    'title': 'Representing the sea and where sediment goes  |  Ordinary cells + initial level versus the sea mask fn_sw',
    'sub': 'In sediment and landform runs the result depends on how the sea is represented. Model the sea of interest as ordinary cells; place any sea mask offshore of it. Illustrative.',
    'a': '(a) Ordinary cells + initial level (f_htype = 2; f_bc = 2 offshore)',
    'a_items': ['the flow is solved and every landform process also acts in submerged cells',
                'suspended sediment settles and deposits on the seabed (tsunami deposits, mouth terraces, deltas)',
                'bedload is carried across the shoreline offshore',
                'the moving bed layer (f_bedslide) runs under water and its surface displacement makes waves'],
    'b': '(b) Sea-mask cells, sw > 0',
    'mask': 'sea mask: no flow solved, no landform update',
    'b_items': [('suspended sediment, debris hs, driftwood', 'leaves the system on entering sea cells (sink); inflow from the sea is clear water'),
                ('bedload', 'does not cross edges with sea cells (wall); piles up at the seaward front'),
                ('rockfall (f_rockfall)', 'material falling into sea cells leaves the system (their z is unchanged)'),
                ('bed slope of debris flows', 'seaward neighbours count as zero slope (no plunge acceleration)'),
                ('longshore transport (fn_wave)', 'neither source nor surf zone; treated as land (depth 0) when smoothing')],
    'shore': 'shoreline', 'sea': 'sea', 'land': 'land',
    'dep': 'deposits on the seabed', 'pile': 'piles at the front', 'out': 'leaves',
    'foot': 'The z of sea cells cannot be set by the user (0 at input; with fn_tide reset every step to tide − hsea0). To impose tides, put a band of sea mask at the offshore edge (see river-mouth deltas on the applications page).',
 },
}


def section(ax, x0, x1, t, masked):
    xs = np.array([x0, x0 + 140, x0 + 250, x0 + 420, x1])
    ys = np.array([190, 230, 300, 372, 392])
    level, base = 280, 430
    ground_px(ax, xs, ys, base)
    water_px(ax, xs, ys, level)
    xsh = x0 + 140 + (level - 230) / (300 - 230) * 110
    if masked:
        xm = x0 + 330
        ym = float(np.interp(xm, xs, ys))
        box(ax, xm, level, x1 - xm, base - level, face=MASK, edge='#5b8db8', z=7, hatch='//', alpha=.45, lw=.0)
        line(ax, [(xm, level - 6), (xm, base)], ORANGE, 2.0, z=8)
        text(ax, (xm + x1) / 2, level - 10, t['mask'], size=7.9, color='#1f4f75', ha='center', va='bottom')
        # Suspended sediment leaves at the mask; bedload piles at the front.
        for k in range(5):
            ax.plot(xm - 90 + 14 * k, level + 16 + 4 * (k % 2), 'o', ms=2.4, color=SED, zorder=9)
        arrow(ax, [(xm - 26, level + 18), (xm + 46, level + 18)], SED, lw=1.5, size=9)
        text(ax, xm + 52, level + 18, t['out'], size=7.9, color=SED, va='center')
        poly(ax, [(xm - 40, ym - 6), (xm, ym - 22), (xm, ym)], MOVING, edge=SED, lw=.6, z=7)
        arrow(ax, [(xm - 100, ym - 30), (xm - 8, ym - 16)], SED, lw=1.3, size=8)
        cross(ax, xm + 10, ym - 14, r=5)
        text(ax, xm - 44, ym + 8, t['pile'], size=7.9, color=SED, ha='right', va='top')
    else:
        for k in range(6):
            ax.plot(x0 + 260 + 16 * k, level + 14 + 4 * (k % 2), 'o', ms=2.4, color=SED, zorder=9)
        for xd in (x0 + 320, x0 + 380, x0 + 440):
            yb = float(np.interp(xd + 10, xs, ys))
            arrow(ax, [(xd, level + 24), (xd + 10, yb - 10)], SED, lw=1.0, size=7)
        xx = np.linspace(x0 + 290, x0 + 560, 40)
        yy = np.interp(xx, xs, ys)
        poly(ax, list(zip(xx, yy - 9 * np.sin(np.linspace(0, np.pi, 40)))) + list(zip(xx[::-1], yy[::-1])),
             MOVING, edge=SED, lw=.6, z=7)
        text(ax, x0 + 470, 402, t['dep'], size=7.9, color=SED, ha='center', va='top')
    text(ax, x0 + 30, 176, t['land'], size=8.2, weight='bold', color='#7a6236')
    if not masked:
        text(ax, x1 - 30, 262, t['sea'], size=8.2, weight='bold', color=BLUE, ha='right')
    line(ax, [(xsh, level - 46), (xsh, level - 4)], MUTED, .7, ls=':')
    text(ax, xsh, level - 50, t['shore'], size=7.8, color=MUTED, ha='center', va='bottom')


def build(lang):
    t = T[lang]
    fig, ax = canvas(H)
    header(ax, t['title'], t['sub'])
    panel(ax, 35, 108, t['a'])
    section(ax, 50, 760, t, masked=False)
    y = 452
    for s in t['a_items']:
        a = block(ax, 50, y, '• ' + s, 720, size=8.3)
        y += 23 * (a.get_text().count('\n') + 1) + 2
    line(ax, [(787, 105), (787, 738)], RULE, .8)
    panel(ax, 805, 108, t['b'])
    section(ax, 820, 1530, t, masked=True)
    y = 452
    for name, desc in t['b_items']:
        text(ax, 820, y, name, size=8.3, weight='bold', color=SED)
        a = block(ax, 820, y + 22, desc, 715, size=8.1)
        y += 22 + 21 * (a.get_text().count('\n') + 1) + 8
    rule(ax, 35, 1540, 746)
    block(ax, 35, 756, t['foot'], 1505, size=8.1, color=MUTED)
    return fig


def draw(lang):
    return run(build, 'geomorph_sea', lang,
               'Schematic comparison of representing the sea as ordinary cells with an initial water level and as '
               'sea-mask cells, and what happens to each sediment path at the mask. Not solver output.')
