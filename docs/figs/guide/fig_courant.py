"""courant_*: teaching diagrams for docs/users_guide/courant.md (ja/en).

Six schematics, no solver output: the Courant number as "cells per step",
current plus wave speed, explicit vs implicit updates, the local maximum
behind Cn_max, the estimate-try-check procedure, and sub-cycling. The
numbers drawn are the worked examples of the text (a = 5 m/s, dx = 10 m,
h = 1 m, V = 2 m/s, a 1 s base step with five 0.2 s sub-steps).
"""
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch
from _terms import canvas, export, text, line, arrow, INK, MUTED, RULE, BLUE, ORANGE, DPI

PALE, GRID, WHITE = '#edf4fc', '#c7d0d7', '#ffffff'
T = {
    'ja': {
        'd_title': 'クーラン数 = 1 回の計算で進む距離 ÷ セル幅',
        'd_sub': '波の速さ a = 5 m/s、セル幅 Δx = 10 m',
        'd_cells': '{c:g} セル分',
        'd_foot': '○: 初めの位置　●: 1 回進めた後の位置。位置は距離に比例して描いています。',
        'w_title': '流れに乗って、波の情報も伝わる',
        'w_sub': '水深 h = 1 m、水に対する波速 c ≈ 3.13 m/s',
        'w_rows': [('水の流れ', '2.00 m/s → 下流'), ('下流向きの波', '2 + 3.13 = 5.13 m/s → 下流'),
                   ('上流向きの波', '3.13 − 2 = 1.13 m/s ← 上流')],
        'w_up': '上流', 'w_down': '下流',
        'w_foot': '地面から見た速さの比較。水の粒は、波と同じ速さで移動するわけではありません。',
        'm_title': '陽解法と陰解法: どの時刻の状態を使うか',
        'm_sub': '●: 分かっている状態　○: これから求める状態',
        'm_exp': '陽解法', 'm_imp': '陰解法', 'm_now': '今', 'm_next': '次',
        'm_cells': ['左のセル', '中央セル', '右のセル'],
        'm_exp_note': '既知の値から更新', 'm_imp_note': '次の時刻の未知量も、互いに関係する',
        'm_foot': 'セル間の関係を単純化した模式図です。矢印は水の流れではなく、計算上の依存関係です。',
        'x_title': '全体が穏やかでも、1 か所の最大値に注目する',
        'x_max': '最大値は 0.90',
        'x_note': '平均値が小さくても、このセルには\n小さい刻みが必要かもしれません。',
        'x_foot': '値は説明用に設定したものです。実際のログでは、さらに表示区間内の最大を取ります。',
        's_title': '時間刻みは「見積もる → 試す → 確かめる」',
        's_steps': [('格子幅を確認', '短い方の格子間隔を m で確認する'),
                    ('大きな速さを見積もる', '流速 + √(重力加速度 × 水深)'),
                    ('刻みを計算する', '目標クーラン数 × 格子幅 ÷ 速さ'),
                    ('小さめに丸めて試す', '出水ピークなど、厳しい時期まで確認する'),
                    ('結果を比較する', 'Cn_max・収支・波形と、dt を半分にした差を見る')],
        's_loop': '大きすぎれば\n刻みを縮めて再試行',
        's_foot': '小さい Cn_max は、精度や物理的妥当性まで保証するものではありません。',
        'c_title': '細かい刻みが必要な処理だけ、内側で進める',
        'c_sub': '説明例: 基本刻み 1 s、内部刻み 0.2 s',
        'c_surf': '地表流', 'c_fine': '細かい処理', 'c_base': '1 s', 'c_sub5': '0.2 s × 5 回',
        'c_foot': '全体を 0.2 秒にするのではなく、必要な処理だけを 5 回進めます。\n内部計算を細かくしても、プロセス間の情報交換の誤差は別に確認します。',
    },
    'en': {
        'd_title': 'Courant number = distance travelled in one step ÷ cell width',
        'd_sub': 'wave speed a = 5 m/s, cell width Δx = 10 m',
        'd_cells': '{c:g} cells',
        'd_foot': '○: initial position　●: position after one step. Positions are drawn to scale.',
        'w_title': 'Wave information is carried by the current too',
        'w_sub': 'depth h = 1 m, wave speed relative to the water c ≈ 3.13 m/s',
        'w_rows': [('current', '2.00 m/s → downstream'), ('downstream wave', '2 + 3.13 = 5.13 m/s → downstream'),
                   ('upstream wave', '3.13 − 2 = 1.13 m/s ← upstream')],
        'w_up': 'upstream', 'w_down': 'downstream',
        'w_foot': 'Speeds as seen from the ground. Water parcels do not move at the speed of the wave.',
        'm_title': 'Explicit and implicit methods: which time level is used',
        'm_sub': '●: known state　○: state to be computed',
        'm_exp': 'explicit', 'm_imp': 'implicit', 'm_now': 'now', 'm_next': 'next',
        'm_cells': ['left cell', 'centre cell', 'right cell'],
        'm_exp_note': 'update from known values', 'm_imp_note': 'the unknowns at the next time are coupled to each other',
        'm_foot': 'A simplified sketch of the coupling between cells. Arrows are computational dependencies, not water flow.',
        'x_title': 'Even when most of the domain is calm, watch the single largest value',
        'x_max': 'maximum 0.90',
        'x_note': 'Even if the mean is small, this cell\nmay need a smaller time step.',
        'x_foot': 'Illustrative values. The log additionally takes the maximum over the display interval.',
        's_title': 'Time step: estimate → try → check',
        's_steps': [('check the cell width', 'the shorter grid spacing, in m'),
                    ('estimate a large speed', 'velocity + √(gravity × depth)'),
                    ('compute the step', 'target Courant number × cell width ÷ speed'),
                    ('round down and try', 'check through the demanding period, e.g. the flood peak'),
                    ('compare the results', 'Cn_max, water balance, waveforms, and a run with half the dt')],
        's_loop': 'too large?\nshrink dt and retry',
        's_foot': 'A small Cn_max does not guarantee accuracy or physical validity.',
        'c_title': 'Only the process that needs a finer step is advanced inside',
        'c_sub': 'example: base step 1 s, inner step 0.2 s',
        'c_surf': 'surface flow', 'c_fine': 'fine process', 'c_base': '1 s', 'c_sub5': '0.2 s × 5',
        'c_foot': 'Rather than using 0.2 s for everything, only the process that needs it is advanced five times.\nA finer inner step does not by itself remove the coupling error between processes; check that separately.',
    },
}
W = 1500


def dot(ax, x, y, r=7, fill=INK, edge=INK, lw=1.4, z=8):
    ax.add_patch(Circle((x, y), r, fc=fill, ec=edge, lw=lw, zorder=z))


def title(ax, t, sub=None):
    text(ax, 48, 36, t, 14, weight='bold')
    if sub:
        text(ax, 48, 82, sub, 10, color=MUTED)


# ---------------------------------------------------------------- 1. distance
def build_distance(lang):
    t = T[lang]
    fig, ax = canvas(850, W)
    title(ax, t['d_title'], t['d_sub'])
    x0, px_per_m = 430, 28           # 10 m = 280 px
    for r, (dt, C) in enumerate([(1, .5), (2, 1), (3, 1.5)]):
        y = 200 + 210 * r
        text(ax, 48, y + 8, f'Δt = {dt} s', 12.5, weight='bold')
        text(ax, 48, y + 60, f'$C_n$ = {C:g}', 14, color=BLUE, weight='bold')
        for j in range(4):
            x = x0 + 280 * j
            line(ax, [(x, y - 14), (x, y + 90)], GRID, 1.3)
            text(ax, x, y + 100, f'{10 * j} m', 9, color=MUTED, ha='center')
        line(ax, [(x0 - 40, y + 60), (x0 + 900, y + 60)], GRID, 1.4)
        xe = x0 + dt * 5 * px_per_m
        dot(ax, x0, y + 60, 8, WHITE, MUTED)
        arrow(ax, [(x0 + 4, y + 16), (xe - 4, y + 16)], BLUE, 2.6, size=14)
        line(ax, [(xe, y + 28), (xe, y + 58)], BLUE, 1.3, ls=(0, (4, 4)))
        dot(ax, xe, y + 60, 10, BLUE, BLUE)
        text(ax, (x0 + xe) / 2, y - 8, f'{5 * dt} m', 10.5, color=BLUE, ha='center', va='bottom', weight='bold')
        text(ax, 1440, y + 32, t['d_cells'].format(c=C), 11, ha='right')
    text(ax, 48, 800, t['d_foot'], 9, color=MUTED)
    return fig


# ---------------------------------------------------------------- 2. current + wave
def build_wave(lang):
    t = T[lang]
    fig, ax = canvas(640, W)
    title(ax, t['w_title'], t['w_sub'])
    zero, scale = 500, 130            # px per m/s
    line(ax, [(zero, 150), (zero, 490)], GRID, 1.5, ls=(0, (5, 5)))
    vals = [2.0, 5.13209195, -1.13209195]
    for (label, note), v, y in zip(t['w_rows'], vals, (215, 325, 435)):
        text(ax, 48, y + 10, label, 12, weight='bold')
        end = zero + v * scale
        arrow(ax, [(zero, y), (end, y)], BLUE, 3.6, size=18)
        if v > 0:
            text(ax, zero, y - 26, note, 10, color=BLUE, va='bottom')
        else:
            text(ax, zero + 24, y + 10, note, 10, color=MUTED)
    arrow(ax, [(1120, 530), (355, 530)], MUTED, 1.4, size=10)
    arrow(ax, [(355, 530), (1120, 530)], MUTED, 1.4, size=10)
    text(ax, 335, 540, t['w_up'], 10, color=MUTED, ha='right')
    text(ax, 1140, 540, t['w_down'], 10, color=MUTED)
    text(ax, 48, 600, t['w_foot'], 9, color=MUTED)
    return fig


# ---------------------------------------------------------------- 3. explicit / implicit
def build_methods(lang):
    t = T[lang]
    fig, ax = canvas(880, W)
    title(ax, t['m_title'], t['m_sub'])
    xs = [490, 790, 1090]
    # explicit
    text(ax, 48, 165, t['m_exp'], 13, color=BLUE, weight='bold')
    text(ax, 290, 215, t['m_now'], 10, color=MUTED, ha='right')
    text(ax, 290, 365, t['m_next'], 10, color=MUTED, ha='right')
    for i, x in enumerate(xs):
        text(ax, x, 170, t['m_cells'][i], 9.5, color=MUTED, ha='center')
        arrow(ax, [(x, 233), (790 + (x - 790) * .07, 348)], BLUE, 1.8, size=12)
        dot(ax, x, 220, 11, INK, INK)
    dot(ax, 790, 368, 13, WHITE, BLUE, 2.4)
    text(ax, 850, 378, t['m_exp_note'], 11, color=BLUE)
    line(ax, [(48, 440), (1452, 440)], RULE, 1)
    # implicit
    text(ax, 48, 490, t['m_imp'], 13, color=BLUE, weight='bold')
    text(ax, 290, 545, t['m_now'], 10, color=MUTED, ha='right')
    text(ax, 290, 690, t['m_next'], 10, color=MUTED, ha='right')
    for x in xs:
        arrow(ax, [(x, 565), (x, 668)], BLUE, 1.8, size=12)
        dot(ax, x, 550, 11, INK, INK)
        dot(ax, x, 690, 13, WHITE, BLUE, 2.4)
    for xa, xb in ((xs[0], xs[1]), (xs[1], xs[2])):
        arrow(ax, [(xa + 22, 690), (xb - 22, 690)], BLUE, 2.2, size=12)
        arrow(ax, [(xb - 22, 690), (xa + 22, 690)], BLUE, 2.2, size=12)
    text(ax, 790, 760, t['m_imp_note'], 11, color=BLUE, ha='center', weight='bold')
    text(ax, 48, 835, t['m_foot'], 9, color=MUTED)
    return fig


# ---------------------------------------------------------------- 4. local maximum
def build_max(lang):
    t = T[lang]
    fig, ax = canvas(630, W)
    title(ax, t['x_title'])
    vals = [[.18, .20, .19, .17, .16], [.21, .23, .25, .22, .20],
            [.19, .22, .90, .27, .21], [.16, .18, .20, .19, .17]]
    x0, y0, w, h = 50, 140, 150, 96
    for i, row in enumerate(vals):
        for j, v in enumerate(row):
            big = v == .90
            ax.add_patch(Rectangle((x0 + j * w, y0 + i * h), w, h, fc=PALE if big else WHITE,
                                   ec=BLUE if big else GRID, lw=3 if big else 1, zorder=3))
            text(ax, x0 + (j + .5) * w, y0 + (i + .5) * h, f'{v:.2f}', 13.5,
                 color=BLUE if big else INK, ha='center', va='center', weight='bold' if big else 'normal')
    arrow(ax, [(820, 380), (910, 380)], BLUE, 2.4, size=14)
    text(ax, 945, 250, t['x_max'], 15, color=BLUE, weight='bold')
    text(ax, 945, 320, t['x_note'], 11)
    text(ax, 48, 590, t['x_foot'], 9, color=MUTED)
    return fig


# ---------------------------------------------------------------- 5. procedure
def build_steps(lang):
    t = T[lang]
    fig, ax = canvas(920, W)
    title(ax, t['s_title'])
    for i, (head, sub) in enumerate(t['s_steps']):
        y = 140 + i * 145
        ax.add_patch(FancyBboxPatch((60, y), 1120, 112, boxstyle='round,pad=0,rounding_size=8',
                                    fc=WHITE, ec=GRID, lw=1.3, zorder=3))
        dot(ax, 112, y + 56, 29, BLUE, BLUE)
        text(ax, 112, y + 56, str(i + 1), 12, color=WHITE, ha='center', va='center', weight='bold')
        text(ax, 165, y + 24, head, 12.5, weight='bold')
        text(ax, 165, y + 68, sub, 10, color=MUTED)
        if i < 4:
            arrow(ax, [(620, y + 115), (620, y + 138)], BLUE, 1.8, size=12)
    # feedback from step 5 back to step 4
    line(ax, [(1190, 776), (1260, 776), (1260, 486)], BLUE, 2)
    arrow(ax, [(1260, 486), (1190, 486)], BLUE, 2, size=12)
    text(ax, 1280, 605, t['s_loop'], 9.5, color=BLUE)
    text(ax, 48, 885, t['s_foot'], 9, color=MUTED)
    return fig


# ---------------------------------------------------------------- 6. sub-cycling
def build_subcycle(lang):
    t = T[lang]
    fig, ax = canvas(700, W)
    title(ax, t['c_title'], t['c_sub'])
    x0, step = 360, 500
    ya, yb = 245, 430
    for sec in range(3):
        x = x0 + sec * step
        line(ax, [(x, 175), (x, 490)], GRID, 1.2, ls=(0, (5, 5)))
        text(ax, x, 150, f'{sec} s', 10, color=MUTED, ha='center')
    text(ax, 48, ya + 10, t['c_surf'], 12.5, weight='bold')
    text(ax, 48, yb + 10, t['c_fine'], 12.5, weight='bold')
    for k in range(2):
        xs = x0 + k * step
        arrow(ax, [(xs + 12, ya), (xs + step - 14, ya)], BLUE, 3, size=16)
        text(ax, xs + step / 2, ya - 24, t['c_base'], 11, color=BLUE, ha='center', va='bottom')
        for j in range(5):
            xx = xs + j * step / 5
            arrow(ax, [(xx + 6, yb), (xx + step / 5 - 8, yb)], BLUE, 2, size=11)
            dot(ax, xx, yb, 4.5, BLUE, BLUE)
        text(ax, xs + step / 2, yb + 50, t['c_sub5'], 10.5, color=BLUE, ha='center')
    for sec in range(3):
        dot(ax, x0 + sec * step, ya, 9, BLUE, BLUE)
    dot(ax, x0 + 2 * step, yb, 4.5, BLUE, BLUE)
    text(ax, 48, 585, t['c_foot'], 10, color=MUTED)
    return fig


FIGS = [('courant_distance', build_distance), ('courant_wave', build_wave),
        ('courant_methods', build_methods), ('courant_max', build_max),
        ('courant_steps', build_steps), ('courant_subcycle', build_subcycle)]


def draw(lang):
    from _schematic import drawing_style
    if lang not in T:
        raise ValueError('lang must be ja or en')
    with drawing_style():
        for stem, build in FIGS:
            last = export(build(lang), stem, lang)
    return last
