"""Nested-grid boundary methods and the separate non-hydrostatic option.

West-edge excerpts away from corners; the row continues to the right.
The illustrated widths are nb=3 and nest_ns=4. This is a schematic, not
simulation output. See m_nest and m_swflow_enc_bc/nh for the operations.
"""
from io import StringIO
from pathlib import Path
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
from guide._schematic import drawing_style, text, line, block, INK, MUTED, RULE

CANVAS, DPI = (1575, 1530), 150
X0, CELL, N, NB, NS = 200, 50, 13, 3, 4
ROWS = (215, 505, 806, 1155)
CHILD, FLOW, GREEN = '#2a78d6', '#eb6834', '#639845'
BAND, BLUE_FILL = '#f7d487', '#edf4fc'
T = {
    'ja': {
        'title': 'ネストの境界方式と非静水圧の設定',
        'sub': '子格子の西端付近を拡大（角から離れた一列の一部）。右側へ内部が続く。帯幅 nb = 3、スポンジ幅 nest_ns = 4 の例。',
        'a': '(a) 境界帯に親の値を指定  |  nest_bc = 1・2',
        'band': '帯: 親の値', 'interior': '子が進める内部',
        'outside': '子の外側', 'wall': '壁\nf_bc_w = 0',
        'a1': 'nest_bc = 1: 水位のみ\n流速・流量は子が計算する。',
        'a2': 'nest_bc = 2（既定）:\n水位・流速・エッジ流量を親から与える。',
        'a_note': '親の値は各サブステップの開始時刻で時間補間。\n帯での上書きは、子の擾乱の反射要因になり得る。',
        'b': '(b) 開いた辺にFlather放射条件  |  nest_bc = 3',
        'b_inner': '帯なし: 子は境界セルまで計算',
        'open': '開放\nf_bc_w = 2',
        'normal': '外向き法線 n（西端では左向き）',
        'waves': '橙: 親の波の入射 / 緑: 子の擾乱の放射',
        'b_values': 'η, h: 子の境界セルの水位・水深\nη_e, u_n,e: 親から補間した水位・外向き流速',
        'b_note': '親の値はサブステップ開始時刻で時間補間。\n開いた辺は常に湿った水域に置く。',
        'c': '(c) 境界帯 + 内側のスポンジ  |  nest_bc = 4',
        'sponge': 'スポンジ',
        'c_note': '帯は nest_bc = 2 と同じ指定。\nスポンジではセル量 q を親の補間値へ緩和。',
        'c_weight': 'd = 1…nest_ns: 帯から内側へのセル数',
        'c_legend': '緑セル内の数値は緩和重み w。内側ほど親の影響を弱める。\n帯とスポンジを含む親セルは、子→親の置換から除外する。',
        'd': '(d) 非静水圧の補足  |  nest_nh = 1（既定）',
        'd_sub': 'f_nonhydrostatic = 1 かつ nest_bc = 1・2・4 に追加する設定。内部が湿潤・射影対象である例。',
        'known': '既知の φ_e（帯）', 'unknown': '内部の φ を子の射影で解く',
        'd_time': 'φ_e = 親の φ\nサブステップ終了時刻で時間補間。',
        'd_edge': '橙線: 帯〜内部のエッジも補正',
        'd_active': '適応計算では、|φ_e| が種の下限以上の帯セルに\n接する内部候補セルも、活性集合の種に加わる。',
        'd_zero': 'nest_nh = 0:\n帯 + 内側の余白 nh_bc_margin を静水圧にする。',
        'd_flather': 'Flather（nest_bc = 3）にはこの帯設定を適用しない。\n開いた面の近くには静水圧の余白を置く。',
        'footer': '(a)〜(c) は境界方式の比較、(d) は非静水圧計算への追加設定。幅・色は模式表現。詳細な制約は本文を参照。',
    },
    'en': {
        'title': 'Nested-grid boundary methods and the non-hydrostatic option',
        'sub': 'West-edge excerpts of a child grid, away from corners. The interior continues to the right. Illustrated widths: nb = 3 and nest_ns = 4.',
        'a': '(a) Prescribe parent values in a band  |  nest_bc = 1, 2',
        'band': 'Band: parent values', 'interior': 'Interior advanced by the child',
        'outside': 'Outside child', 'wall': 'Wall\nf_bc_w = 0',
        'a1': 'nest_bc = 1: water level only\nThe child computes velocity and discharge.',
        'a2': 'nest_bc = 2 (default):\nparent level, velocity and edge discharge.',
        'a_note': 'Parent values are interpolated to each sub-step start.\nOverwriting in the band can reflect child disturbances.',
        'b': '(b) Flather radiation on an open edge  |  nest_bc = 3',
        'b_inner': 'No band: the child computes up to its edge cells',
        'open': 'Open\nf_bc_w = 2',
        'normal': 'Outward normal n (left at the west edge)',
        'waves': 'Orange: parent waves in / green: child disturbances out',
        'b_values': 'η, h: child boundary-cell level and depth\nη_e, u_n,e: interpolated parent level and outward velocity',
        'b_note': 'Parent values are interpolated to the sub-step start.\nPlace open edges in permanently wet water.',
        'c': '(c) Boundary band + inner sponge  |  nest_bc = 4',
        'sponge': 'Sponge',
        'c_note': 'The band uses the same prescription as nest_bc = 2.\nSponge cell quantities q relax towards the parent.',
        'c_weight': 'd = 1…nest_ns: cell count inward from the band',
        'c_legend': 'Green-cell numbers give relaxation weight w, decreasing inward.\nParent cells covering band/sponge are excluded from replacement.',
        'd': '(d) Non-hydrostatic supplement  |  nest_nh = 1 (default)',
        'd_sub': 'Additional setting for f_nonhydrostatic = 1 with nest_bc = 1, 2 or 4. The interior shown is wet and active in the projection.',
        'known': 'Known φ_e (band)', 'unknown': 'Interior φ solved by the child projection',
        'd_time': 'φ_e = parent φ\nInterpolate to the sub-step end time.',
        'd_edge': 'Orange: correct band–interior edges too',
        'd_active': 'Adaptive calculation also seeds interior candidates\nnext to band cells whose |φ_e| meets the seed floor.',
        'd_zero': 'nest_nh = 0:\nKeep the band + inner margin nh_bc_margin hydrostatic.',
        'd_flather': 'This band setting does not apply to Flather (nest_bc = 3).\nA hydrostatic margin remains near open faces.',
        'footer': '(a)–(c) compare boundary methods; (d) is an additional non-hydrostatic setting. Widths and colours are schematic. See the text for restrictions.',
    },
}


def sponge_weights(ns=NS):
    """m_nest.nest_prolong: distance from the nearest band, in child cells."""
    d = np.arange(1, ns+1, dtype=float)
    return (1-d/(ns+1))**2


def rect(ax, x, y, w, h, face, edge='none', lw=0, **kwargs):
    p = Rectangle((x, y), w, h, facecolor=face, edgecolor=edge,
                  linewidth=lw, zorder=2, **kwargs)
    ax.add_patch(p)
    return p


def arrow(ax, p, q, color, style='-|>', lw=1.5, size=10):
    a = FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=size,
                        color=color, lw=lw, shrinkA=0, shrinkB=0, zorder=10)
    ax.add_patch(a)
    return a


def cells(ax, y, band=True, sponge=False, phi=False, opened=False):
    weights = sponge_weights()
    for i in range(N):
        face = BAND if band and i < NB else BLUE_FILL
        if sponge and NB <= i < NB+NS:
            # Discrete cell fills; the printed weights carry the quantitative meaning.
            base = np.array([99, 152, 69])/255
            face = 1-(.12+.65*weights[i-NB])*(1-base)
        p = rect(ax, X0+i*CELL, y, CELL, CELL, face, CHILD, .7)
        p.set_gid(f'cell-{y}-{i+1}')
        if sponge and NB <= i < NB+NS:
            text(ax, X0+(i+.5)*CELL, y+CELL/2, f'{weights[i-NB]:.2f}',
                 size=8.0, ha='center', va='center', color='#355921')
        if phi:
            text(ax, X0+(i+.5)*CELL, y+CELL/2, '$\\varphi_e$' if i<NB else '$\\varphi$',
                 size=10.4, ha='center', va='center', color='#80601b' if i<NB else CHILD)
    if opened:
        line(ax, [(X0,y-7),(X0,y+CELL+7)], FLOW, 1.6, ls=(0,(3,3)))
    else:
        rect(ax, X0-9, y-5, 9, CELL+10, '#deddd8', MUTED, .7, hatch='////')
        line(ax, [(X0,y-7),(X0,y+CELL+7)], INK, 2.1)
    # A continuation, not the child's opposite outer boundary.
    text(ax, X0+N*CELL+21, y+CELL/2, '…', color=CHILD, size=12,
         ha='center', va='center')


def dimension(ax, x1, x2, y, label):
    line(ax, [(x1,y-5),(x1,y+5)], MUTED, .7)
    line(ax, [(x2,y-5),(x2,y+5)], MUTED, .7)
    arrow(ax, (x1,y),(x2,y), MUTED, style='<->', lw=.8, size=7)
    text(ax, (x1+x2)/2, y+10, label, size=8.3, ha='center', color=MUTED)


def build(lang):
    t = T[lang]
    fig = plt.figure(figsize=(CANVAS[0]/DPI, CANVAS[1]/DPI), dpi=DPI)
    ax = fig.add_axes([0,0,1,1])
    ax.set(xlim=(0,CANVAS[0]), ylim=(CANVAS[1],0)); ax.axis('off')
    text(ax, 30, 22, t['title'], size=12, weight='bold')
    text(ax, 30, 69, t['sub'], size=8.6, color=MUTED)
    for y in (109,398,690,985,1467):
        line(ax, [(30,y),(1545,y)], RULE, .8)
    for y,key in [(125,'a'),(418,'b'),(718,'c')]:
        text(ax, 30, y, t[key], size=10.3, weight='bold')
    for y in (ROWS[0],ROWS[2],ROWS[3]):
        text(ax, 94, y+14, t['outside'], size=8.0, color=MUTED, ha='center')
    for y in ROWS[:1]+ROWS[2:3]:
        text(ax, 94, y+67, t['wall'], size=8.0, color=INK, ha='center')
    cells(ax, ROWS[0])
    text(ax, 275, 178, t['band'], size=8.7, ha='center', color='#80601b')
    text(ax, 600, 178, t['interior'], size=8.7, ha='center', color=CHILD)
    dimension(ax, X0, X0+NB*CELL, 284, 'nb = 3')
    text(ax, 200, 344, t['a_note'], size=8.4, color=MUTED)
    text(ax, 930, 183, t['a1'], size=9)
    text(ax, 930, 264, t['a2'], size=9, color=CHILD)

    cells(ax, ROWS[1], band=False, opened=True)
    text(ax, 525, 465, t['b_inner'], size=8.7, color=CHILD, ha='center')
    text(ax, 92, 465, t['outside'], size=8, color=MUTED, ha='center')
    arrow(ax, (128,520),(287,520), FLOW, lw=1.8)
    arrow(ax, (287,542),(128,542), GREEN, lw=1.8)
    text(ax, 94, 578, t['open'], size=8.0, color=FLOW, ha='center')
    arrow(ax, (270,588),(190,588), INK, lw=1.1, size=9)
    text(ax, 297, 576, t['normal'], size=8.4)
    text(ax, 200, 630, t['waves'], size=8.2, color=MUTED)
    text(ax, 930, 464, r'$u_n = u_{n,e} + \sqrt{g/h}\,(\eta-\eta_e)$', size=12, color=FLOW)
    text(ax, 930, 522, t['b_values'], size=8.5)
    text(ax, 930, 608, t['b_note'], size=8.4, color=MUTED)

    cells(ax, ROWS[2], sponge=True)
    for x,key,c in [(275,'band','#80601b'),(450,'sponge','#355921'),(700,'interior',CHILD)]:
        text(ax, x, 769, t[key], size=8.5, ha='center', color=c)
    dimension(ax, X0, X0+NB*CELL, 875, 'nb = 3')
    dimension(ax, X0+NB*CELL, X0+(NB+NS)*CELL, 875, 'nest_ns = 4')
    text(ax, 200, 934, t['c_legend'], size=8.2, color=MUTED)
    text(ax, 930, 768, t['c_note'], size=8.8)
    text(ax, 930, 841, r'$q \leftarrow (1-w)\,q + w\,q_{\rm parent}$', size=11, color='#355921')
    text(ax, 930, 895, r'$w = [1-d/(\mathrm{nest\_ns}+1)]^2$', size=10, color='#355921')
    text(ax, 930, 944, t['c_weight'], size=8.0, color=MUTED)

    rect(ax, 20, 1007, 1535, 437, '#f7f8fa')
    text(ax, 30, 1028, t['d'], size=10.3, weight='bold')
    text(ax, 30, 1073, t['d_sub'], size=8.4, color=MUTED)
    cells(ax, ROWS[3], phi=True)
    text(ax, 275, 1118, t['known'], size=8.6, ha='center', color='#80601b')
    text(ax, 610, 1118, t['unknown'], size=8.6, ha='center', color=CHILD)
    line(ax, [(X0+NB*CELL,1148),(X0+NB*CELL,1212)], FLOW, 2)
    line(ax, [(350,1214),(381,1242)], FLOW, .9)
    text(ax, 398, 1230, t['d_edge'], size=8.4, color=FLOW)
    text(ax, 200, 1300, t['d_active'], size=8.3, color=MUTED)
    text(ax, 930, 1118, t['d_time'], size=9, color='#80601b')
    block(ax, 930, 1230, t['d_zero'], 590, size=8.6)
    block(ax, 930, 1350, t['d_flather'], 590, size=8.3, color=MUTED)
    text(ax, 30, 1487, t['footer'], size=8.1, color=MUTED)
    return fig


def draw(lang):
    if lang not in T:
        raise ValueError('lang must be ja or en')
    png = Path(__file__).resolve().parents[1]/('nest_bc'+('' if lang=='ja' else '_en')+'.png')
    with drawing_style():
        fig = build(lang)
        try:
            fig.savefig(png, dpi=DPI)
            svg = StringIO()
            fig.savefig(svg, format='svg', metadata={'Date': None,
                'Description': 'ENCflow nested-grid boundary methods and non-hydrostatic option. Schematic.'})
            png.with_suffix('.svg').write_text('\n'.join(s.rstrip() for s in svg.getvalue().splitlines())+'\n',
                                               encoding='utf-8', newline='\n')
        finally:
            plt.close(fig)
    return str(png)
