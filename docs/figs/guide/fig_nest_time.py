"""Nested time stepping: physical time, interpolation times and recursion.

Illustrated ratios: parent/child 3 and child/grandchild 2. The timeline is
an algorithm schematic, not simulation output or a wall-clock schedule.
Source: m_main.nest_advance; m_nest.nest_capture/prolong/fill_phi/restrict.
"""
from pathlib import Path
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle
from guide._schematic import drawing_style, text, block, line, arrow, INK, MUTED, RULE

CANVAS, DPI = (1575, 1275), 150
RT, RG = 3, 2
X0, X1 = 330, 1320
YP, YC, YG = 260, 400, 540
PARENT, CHILD, GRAND = '#6b6a66', '#2a78d6', '#5a9bd5'
START, END, FEEDBACK = '#c95c2c', '#675ba6', '#498237'
T = {
    'ja': {
        'title': '親子格子の時間進行と境界値の時間補間',
        'sub': '親の1歩 Δt を子が3分割し、子の各1歩を孫が2分割する例。r_t は、それぞれ直上の親との時間比。',
        'a': '(a) 同じ計算時刻へ進む3段の格子',
        'parent': '親（格子1）\n1歩 = Δt',
        'child': '子（r_t = 3）\n1歩 = Δt/3',
        'grand': '孫（r_t = 2）\n1歩 = Δt/6',
        'capture': '親が先に1歩進み、前後の親の値を保持',
        'child_steps': ['子の1歩目', '子の2歩目', '子の3歩目'],
        'feedback': '子→親\n同期して置換',
        'legend': '橙破線: 子の開始時刻の補間係数 α   /   緑矢印: 同期した子から直上の親へ置換（nest_fb = 1〜3）',
        'order': '実行順: 親1歩 → [子1歩 → 孫2歩 → 孫から子へ置換] × 3 → 子から親へ置換。横軸は計算上の時刻。',
        'b': '(b) 通常の境界値は開始時刻、非静水圧の φ は終了時刻',
        'start_title': '水位・流速など: サブステップ開始',
        'start_time': '開始係数  α = k/r_t',
        'start_values': 'k = 0, 1, 2  →  α = 0/3, 1/3, 2/3',
        'start_note': 'Q は親の窓に保持した量。時間補間後に、子の境界方式に応じて空間補間・乾湿判定などを行う。',
        'end_title': '非静水圧ポテンシャル φ: サブステップ終了',
        'end_time': '終了係数  β = α + 1/r_t',
        'end_values': 'k = 0, 1, 2  →  β = 1/3, 2/3, 3/3',
        'end_note': '非静水圧の子で nest_nh = 1、nest_bc = 1・2・4 の場合。帯の φ を親から与える既知値にする。',
        'footer1': '孫は直上の子の2時刻から補間する。孫→子の置換は子の各1歩の終わり、子→親の置換は tⁿ⁺¹ に行う。',
        'footer2': 'nest_fb = 0 では置換しない。1〜3では対象内部を親へ戻し、3では界面流束の保存修正も行う。',
        'footer3': '帯・スポンジを含む親セルは置換対象から除外する。境界方式・乾湿処理・複数の子の詳細は本文を参照。',
    },
    'en': {
        'title': 'Nested time stepping and boundary-value interpolation',
        'sub': 'One parent step Δt contains 3 child steps; each child step contains 2 grandchild steps. Each r_t is relative to the immediate parent.',
        'a': '(a) Three grid levels advancing to the same physical time',
        'parent': 'Parent (grid 1)\nStep = Δt',
        'child': 'Child (r_t = 3)\nStep = Δt/3',
        'grand': 'Grandchild (r_t = 2)\nStep = Δt/6',
        'capture': 'Advance parent first; retain its values before and after',
        'child_steps': ['Child step 1', 'Child step 2', 'Child step 3'],
        'feedback': 'Child → parent\nReplace at sync',
        'legend': 'Orange dashes: child-start weight α   /   Green arrows: replacement into the immediate parent at synchronization (nest_fb = 1–3)',
        'order': 'Execution: parent step → [child step → 2 grandchild steps → replace into child] × 3 → replace into parent. The axis shows physical time.',
        'b': '(b) Ordinary boundary data use the start; non-hydrostatic φ uses the end',
        'start_title': 'Water level, velocity, etc.: sub-step start',
        'start_time': 'Start weight  α = k/r_t',
        'start_values': 'k = 0, 1, 2  →  α = 0/3, 1/3, 2/3',
        'start_note': 'Q is a quantity in the parent window. Time interpolation precedes spatial interpolation, wet/dry rules and other boundary-method operations.',
        'end_title': 'Non-hydrostatic potential φ: sub-step end',
        'end_time': 'End weight  β = α + 1/r_t',
        'end_values': 'k = 0, 1, 2  →  β = 1/3, 2/3, 3/3',
        'end_note': 'For a non-hydrostatic child with nest_nh = 1 and nest_bc = 1, 2 or 4. The band holds known φ values supplied by the parent.',
        'footer1': 'The grandchild interpolates between two states of its immediate parent. Grandchild → child replacement follows each child step;',
        'footer2': 'child → parent replacement occurs at tⁿ⁺¹. nest_fb = 0 skips replacement; 1–3 return the eligible interior, and 3 adds flux correction.',
        'footer3': 'Exclude parent cells containing a boundary band or sponge. See the text for boundary methods, wet/dry handling and multiple children.',
    },
}


def geometry():
    """One shared time coordinate for nodes, interpolation and feedback."""
    return {
        'child': np.linspace(X0, X1, RT+1),
        'grand': np.linspace(X0, X1, RT*RG+1),
        'alpha': np.arange(RT)/RT,
        'beta': (np.arange(RT)+1)/RT,
    }


def build(lang):
    t = T[lang]
    fig = plt.figure(figsize=(CANVAS[0]/DPI, CANVAS[1]/DPI), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, CANVAS[0]); ax.set_ylim(CANVAS[1], 0); ax.axis('off')
    text(ax, 48, 35, t['title'], 17, weight='bold')
    block(ax, 48, 91, t['sub'], 1479, 9)
    text(ax, 48, 151, t['a'], 12, weight='bold')
    g = geometry()
    text(ax, X0, 209, 'tⁿ', 11, ha='center')
    text(ax, X1, 209, 'tⁿ⁺¹ = tⁿ + Δt', 11, ha='center')
    text(ax, (X0+X1)/2, 210, t['capture'], 9.1, color=PARENT, ha='center')
    for key, y, xs, color in [('parent',YP,[X0,X1],PARENT),('child',YC,g['child'],CHILD),('grand',YG,g['grand'],GRAND)]:
        text(ax, 48, y-20, t[key], 10, color=color)
        line(ax, list(zip(xs, [y]*len(xs))), color, 2.5 if key=='parent' else 2.0).set_gid(key+'-timeline')
        for i, x in enumerate(xs):
            line(ax, [(x,y)], color, marker='o', markersize=5 if key!='grand' else 4).set_gid(f'{key}-node-{i}')
    for k, x in enumerate(g['child'][:-1]):
        arrow(ax, [(x,YP+14),(x,YC-15)], START, 1.3, '--', 10).set_gid(f'alpha-arrow-{k}')
        text(ax, x+18, 306, f'α = {k}/3', 10, color=START)
        text(ax, (x+g['child'][k+1])/2, 361, t['child_steps'][k], 9.1, color=CHILD, ha='center')
    for k, x in enumerate(g['grand'][:-1]):
        text(ax, (x+g['grand'][k+1])/2, 504, str(k+1), 9, color=GRAND, ha='center')
    for i, x in enumerate(g['child'][1:]):
        arrow(ax, [(x,YG-13),(x,YC+15)], FEEDBACK, 1.6, size=11).set_gid(f'grand-feedback-{i}')
    arrow(ax, [(X1,YC-15),(X1,YP+15)], FEEDBACK, 1.9, size=12).set_gid('child-feedback')
    text(ax, X1+22, 296, t['feedback'], 9, color=FEEDBACK)
    block(ax, 48, 583, t['legend'], 1479, 9)
    block(ax, 48, 637, t['order'], 1479, 9.3)
    line(ax, [(48,705),(1527,705)], RULE, 0.9)
    text(ax, 48, 731, t['b'], 12, weight='bold')
    for x, key, color, fill, formula in [
        (48,'start',START,'#fdf3ed','Q(α) = (1 − α) Qⁿ + α Qⁿ⁺¹'),
        (807,'end',END,'#f3f1fa','φ(β) = (1 − β) φⁿ + β φⁿ⁺¹')]:
        ax.add_patch(Rectangle((x,787),720,295,facecolor=fill,edgecolor='none'))
        text(ax, x+24, 811, t[key+'_title'], 10.3, color=color, weight='bold')
        text(ax, x+24, 863, t[key+'_time'], 10, color=color)
        text(ax, x+24, 908, formula, 12, color=color)
        text(ax, x+24, 954, t[key+'_values'], 10)
        block(ax, x+24, 1004, t[key+'_note'], 670, 8.7)
    for i in range(1,4):
        block(ax, 48, 1122+(i-1)*42, t['footer'+str(i)], 1479, 8.8, color=MUTED)
    return fig


def draw(lang):
    if lang not in T:
        raise ValueError('lang must be ja or en')
    dest = Path(__file__).resolve().parents[1]/('nest_time'+('' if lang=='ja' else '_en'))
    with drawing_style():
        fig = build(lang)
        fig.savefig(dest.with_suffix('.png'), dpi=DPI)
        fig.savefig(dest.with_suffix('.svg'), metadata={'Date':None})
        plt.close(fig)
    return str(dest.with_suffix('.png'))
