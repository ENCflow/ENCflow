"""BMI control, array orientation and exchange timing (Japanese / English).

Rebuild from the repository root:
    python docs/figs/make_guide_figs.py bmi

Implementation sources:
  bmi/python/live_view.py: main / draw (synchronous update-and-draw loop)
  bmi/python/encflow.py: get / get2d / set (copies and C-order reshape)
  bmi/bmi_encflow.f90: get_field / set_field (row reversal at the BMI boundary)
  src/m_main.f90: m_main_set_value / run_step (staging and next-step application)

The numbered cells are identifiers, not simulation results. All marks are
vector geometry; SVG text is outlined, with no embedded bitmap or font.
"""
from io import StringIO
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle

from _schematic import drawing_style, text, block, line, arrow, INK, MUTED, RULE

DPI = 150
WIDTH = 1800
BLUE, GREEN, ORANGE = '#2a78d6', '#527d37', '#cf5a27'
PALE_BLUE, PALE_GREEN, PALE_ORANGE = '#eef4fc', '#f0f5e9', '#fcf0e9'
ROW_COLORS = ['#dceafa', '#f6eed7', '#e4edda']  # south to north
NX, NY = 4, 3
PROBE_I, PROBE_J = 3, 1  # ENCflow's one-based cell address


def choose(lang, ja, en):
    return ja if lang == 'ja' else en


def canvas(height, title, subtitle):
    fig = plt.figure(figsize=(WIDTH / DPI, height / DPI), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set(xlim=(0, WIDTH), ylim=(height, 0))
    ax.axis('off')
    text(ax, 55, 36, title, 20, weight='bold')
    text(ax, 57, 98, subtitle, 11.5, color=MUTED)
    return fig, ax


def rect(ax, x, y, w, h, fill='white', edge=RULE, lw=1, gid=None):
    patch = Rectangle((x, y), w, h, facecolor=fill, edgecolor=edge,
                      linewidth=lw, gid=gid)
    ax.add_patch(patch)
    return patch


def card(ax, x, y, w, h, title, detail='', color=BLUE, fill=PALE_BLUE,
         title_size=12, detail_size=10.5):
    rect(ax, x, y, w, h, fill, 'none')
    rect(ax, x, y, 5, h, color, 'none')
    text(ax, x + 22, y + 17, title, title_size, color=color, weight='bold')
    if detail:
        block(ax, x + 22, y + 58, detail, w - 44, detail_size)


def build_control(lang):
    """Trace the actual live_view.py calls, including its initial draw."""
    t = lambda ja, en: choose(lang, ja, en)
    fig, ax = canvas(1180,
        t('BMI：Python が計算と描画を交互に進める',
          'BMI: Python alternates computation and visualization'),
        t('live_view.py の制御順序。図の上下方向は呼び出し順を示す。',
          'Call order in live_view.py, from top to bottom.'))
    text(ax, 120, 156, 'Python / live_view.py', 13, color=BLUE, weight='bold')
    text(ax, 1050, 156, 'ENCflow / BMI', 13, color=GREEN, weight='bold')

    card(ax, 120, 205, 650, 84, 'ENCflow(param)',
         t('モデルを作成して initialize', 'Create the model and initialize'),
         BLUE, detail_size=10)
    card(ax, 1040, 205, 700, 84, t('初期化', 'Initialize'),
         t('入力を読み、初期状態を準備', 'Read inputs and prepare the initial state'),
         GREEN, PALE_GREEN, detail_size=10)
    arrow(ax, [(788, 247), (1018, 247)], BLUE)
    text(ax, 900, 209, 'initialize', 10, ha='center', color=MUTED)

    card(ax, 120, 330, 650, 115, t('初期状態を描画', 'Draw the initial state'),
         'get2d(z) ' + t('は最初に一度だけ', 'once at the start') + '\n'
         + 'get2d(h) → draw(time)')
    card(ax, 1040, 330, 700, 115, t('現在の標高 z と水深 h', 'Current elevation z and depth h'),
         t('get は状態を変更せず、配列をコピーして返す',
           'get copies the fields without changing the model state'),
         GREEN, PALE_GREEN)
    arrow(ax, [(1018, 386), (788, 386)], GREEN)
    text(ax, 901, 350, t('コピー', 'copy'), 10, ha='center', color=MUTED)

    rect(ax, 56, 475, 1684, 360, '#f7f8fa', RULE)
    text(ax, 80, 488, t('終了時刻まで繰り返す', 'Repeat until the end time'),
         11, weight='bold')
    card(ax, 120, 540, 650, 100, 'update_until(target)',
         'target = min(time + interval, end_time)')
    card(ax, 1040, 540, 670, 100, t('dt 刻みで target まで計算', 'Advance to target in dt steps'),
         t('Python は、この呼び出しが戻るまで待つ',
           'Python waits until this call returns'), GREEN, PALE_GREEN)
    arrow(ax, [(788, 587), (1018, 587)], BLUE)
    text(ax, 901, 550, t('計算を依頼', 'advance'), 10, ha='center', color=MUTED)
    arrow(ax, [(1374, 650), (1374, 680)], GREEN)
    card(ax, 1040, 690, 670, 110, t('計算後の水深 h', 'Depth h after the advance'),
         t('時刻と状態は target に進んでいる',
           'The model time and state have advanced to target'), GREEN, PALE_GREEN)
    card(ax, 120, 690, 650, 110, 'get2d(h) → draw(time)',
         t('水深分布を更新し、水深時系列に1点追加',
           'Refresh the depth map and append one depth sample'))
    arrow(ax, [(1018, 744), (788, 744)], GREEN)
    text(ax, 901, 707, t('コピー', 'copy'), 10, ha='center', color=MUTED)
    arrow(ax, [(111, 757), (84, 757), (84, 585), (111, 585)], BLUE, size=9)

    card(ax, 120, 874, 650, 76, 'finalize()', color=BLUE)
    card(ax, 1040, 874, 700, 76, t('最終出力・終了処理', 'Final output and cleanup'),
         color=GREEN, fill=PALE_GREEN)
    arrow(ax, [(788, 911), (1018, 911)], BLUE)
    text(ax, 80, 991, t('計算・画面表示・ファイル出力の間隔は別々に考える',
                       'Distinguish model steps, display intervals and file output'),
         11.5, weight='bold')
    card(ax, 56, 1040, 538, 106, 'dt',
         t('モデルの時間刻み', 'Model time step'), GREEN, PALE_GREEN)
    card(ax, 630, 1040, 538, 106, '--interval',
         t('描画間隔（dt の正の整数倍）', 'Display interval (a positive multiple of dt)'))
    card(ax, 1204, 1040, 536, 106, 'dt_file',
         t('通常の結果ファイルの出力間隔', 'Regular result-file output interval'),
         ORANGE, PALE_ORANGE)
    return fig


def cell_values():
    """Distinct IDs in BMI order; never use these as physical field values."""
    return np.arange(1, NX * NY + 1).reshape(NY, NX)


def draw_cells(ax, x, y, array, rows, selected, gid):
    for row in range(NY):
        for col in range(NX):
            value = int(array[row, col])
            color = ROW_COLORS[(value - 1) // NX]
            is_probe = (row, col) == selected
            patch = rect(ax, x + 90 * col, y + 80 * row, 90, 80,
                 PALE_ORANGE if is_probe else color,
                 ORANGE if is_probe else 'white', 2,
                 gid=f'{gid}-cell-{value}')
            if is_probe:
                patch.set_zorder(3)
            text(ax, x + 90 * col + 45, y + 80 * row + 40,
                 str(value), 16, color=ORANGE if is_probe else INK,
                 ha='center', va='center', weight='bold' if is_probe else 'normal')
        text(ax, x - 16, y + 80 * row + 40, rows[row], 10,
             ha='right', va='center', color=MUTED)


def build_arrays(lang):
    """Derive every cell and index from the same 3x4 reference array."""
    t = lambda ja, en: choose(lang, ja, en)
    fig, ax = canvas(1190,
        t('BMI：セル番地・NumPy 配列・地図表示の対応',
          'BMI: cell addresses, NumPy arrays and map orientation'),
        t('例：nx = 4、ny = 3。1～12 はセルの識別番号で、計算値ではない。',
          'Example: nx = 4, ny = 3. Numbers 1–12 identify cells; they are not simulated values.'))
    a = cell_values()
    titles = [t('(a) ENCflow の内部セル', '(a) ENCflow internal cells'),
              '(b) get2d() → NumPy',
              '(c) imshow(origin="lower")']
    for x, title in zip([55, 650, 1245], titles):
        text(ax, x, 186, title, 13, weight='bold')
    for i in range(NX):
        text(ax, 140 + 90 * i + 45, 262, f'i={i+1}', 10, ha='center', color=MUTED)
        text(ax, 735 + 90 * i + 45, 262, str(i), 10, ha='center', color=MUTED)
    text(ax, 915, 234, t('列 index', 'column index'), 10, ha='center', color=MUTED)
    draw_cells(ax, 140, 304, a[::-1], ['j=1', 'j=2', 'j=3'], (PROBE_J - 1, PROBE_I - 1), 'internal')
    draw_cells(ax, 735, 304, a, ['0', '1', '2'], (NY - PROBE_J, PROBE_I - 1), 'numpy')
    draw_cells(ax, 1330, 304, a[::-1], ['N', '', 'S'], (PROBE_J - 1, PROBE_I - 1), 'map')
    for x in [140, 1330]:
        text(ax, x, 560, 'W', 10, color=MUTED)
        text(ax, x + 360, 560, 'E', 10, ha='right', color=MUTED)
    arrow(ax, [(535, 424), (634, 424)], BLUE)
    arrow(ax, [(1130, 424), (1229, 424)], BLUE)
    block(ax, 75, 611, t('j = 1 は北端。i は西→東へ増加。',
                        'j = 1 is the north edge. i increases west to east.'), 485, 11)
    block(ax, 670, 611, t('行 0 は南端。列は西→東。\nBMI が行順を変換済み。',
                         'Row 0 is the south edge; columns run west to east. BMI has reversed the rows.'), 485, 11)
    block(ax, 1265, 611, t('行 0 を下側に表示すれば、\n北が上の地図になる。',
                          'Put row 0 at the bottom\nto display north at the top.'), 470, 11)
    line(ax, [(55, 723), (1740, 723)], RULE)
    text(ax, 60, 750, t('get() の1次元配列', 'The flat get() array'), 12, weight='bold')
    text(ax, 60, 814, t('index（0始まり）', 'index (zero-based)'), 10, color=MUTED)
    text(ax, 60, 870, t('セル識別番号', 'cell ID'), 10, color=MUTED)
    for k, value in enumerate(a.ravel()):
        x = 330 + 112 * k
        text(ax, x + 56, 811, str(k), 11, ha='center', color=MUTED)
        selected = k == (NY - PROBE_J) * NX + PROBE_I - 1
        patch = rect(ax, x, 851, 112, 61, PALE_ORANGE if selected else ROW_COLORS[k // NX],
             ORANGE if selected else 'white', 2, gid=f'flat-cell-{value}')
        if selected:
            patch.set_zorder(3)
        text(ax, x + 56, 881, str(value), 13, ha='center', va='center',
             color=ORANGE if selected else INK, weight='bold' if selected else 'normal')
    rect(ax, 55, 955, 1685, 153, PALE_ORANGE, 'none')
    text(ax, 80, 974, t('橙色のセル：ENCflow (i, j) = (3, 1)',
                       'Orange cell: ENCflow (i, j) = (3, 1)'), 12, color=ORANGE, weight='bold')
    text(ax, 80, 1026, 'get2d():  h[ny - j, i - 1] = h[2, 2]', 12)
    text(ax, 80, 1065, 'get():     k = (ny - j) * nx + (i - 1) = 10', 12)
    block(ax, 1090, 1026, t('同じセル識別番号 11 を指す。\nset にもこの BMI 配列順で渡す。',
                           'Both refer to cell ID 11.\nUse this BMI ordering for set too.'), 620, 11)
    text(ax, 57, 1140, t('get2d() の結果を手作業で反転する必要はない。配列はコピーで、書き換えだけではモデルに戻らない。',
                        'No manual flip after get2d(). The returned array is a copy; editing it alone does not change the model.'),
         10.5, color=MUTED)
    return fig


def build_exchange(lang):
    """Distinguish staged values, one-shot state replacement and persistence."""
    t = lambda ja, en: choose(lang, ja, en)
    fig, ax = canvas(1240,
        t('BMI：外部入力は次の計算ステップで適用される',
          'BMI: external inputs take effect on the next model step'),
        t('get / set は時刻を進めない。update（または update_until 内の次のステップ）で反映。',
          'get / set do not advance time. Values take effect in update, or the next step inside update_until.'))
    phases = [
        ('1  get()', t('現在の場をコピー\n外部で値を準備',
                      'Copy the current field;\nprepare values externally'), BLUE, PALE_BLUE),
        ('2  set(values)', t('値を受け付けて保留\n計算状態はまだ変わらない',
                            'Accept and stage values;\nthe applied field is unchanged'), ORANGE, PALE_ORANGE),
        ('3  update()', t('保留値を適用してから\nそのステップを計算',
                         'Apply staged values, then\ncompute that model step'), GREEN, PALE_GREEN),
        ('4  get()', t('計算後の場をコピー\n物理過程の変化も含む',
                      'Copy the resulting field,\nincluding physical evolution'), BLUE, PALE_BLUE),
    ]
    for i, (title, detail, color, fill) in enumerate(phases):
        x = 55 + 435 * i
        card(ax, x, 203, 375, 165, title, detail, color, fill, detail_size=11)
        if i < 3:
            arrow(ax, [(x + 390, 285), (x + 423, 285)], MUTED)
    line(ax, [(57, 399), (864, 399)], ORANGE, 2)
    text(ax, 57, 419, t('ここまでモデル時刻は同じ', 'The model time has not advanced yet'), 11, color=ORANGE)
    line(ax, [(930, 399), (1735, 399)], GREEN, 2)
    text(ax, 930, 419, t('1ステップなら時刻が dt 進む', 'One step advances model time by dt'), 11, color=GREEN)
    block(ax, 57, 473, t('set 直後の get で読めるのは、まだ適用前の場。保留した値そのものを返すわけではない。',
                         'A get immediately after set still reads the field before application, rather than the staged values.'),
          1680, 11, color=MUTED)

    text(ax, 60, 573, t('入力の種類', 'Input type'), 12, weight='bold')
    text(ax, 488, 573, t('次のステップで適用', 'Apply on the next step'), 12, weight='bold')
    text(ax, 1110, 573, t('その後のステップ', 'Subsequent steps'), 12, weight='bold')
    rows = [
        (BLUE, PALE_BLUE, t('降水強度 pre', 'Precipitation pre'), 'm/s',
         t('供給した降水強度を使う', 'Use the supplied precipitation rate'),
         t('同じ強度の外力が持続', 'The forcing rate persists'),
         t('変更・停止には再度 set\n雨を止めるときはゼロを与える',
           'Set again to change or stop rainfall;\nsupply zero to stop it')),
        (GREEN, PALE_GREEN, t('水深などの状態 h', 'State, e.g. depth h'), 'm',
         t('状態を一度だけ置換', 'Replace the state once'),
         t('以後は物理過程で変化', 'Then evolve through model physics'),
         t('加算でも、値の固定でもない\n計算後の h は設定値と異なり得る',
           'Neither added nor held fixed;\nh after the step may differ from the input')),
        (ORANGE, PALE_ORANGE, t('粗度係数 rn', "Manning's n (rn)"), 's/m^(1/3)',
         t('係数を一度だけ上書き', 'Override the coefficient once'),
         t('次の set まで係数が持続', 'The coefficient persists until set again'),
         t('ENC 格子系の有効セル全体\nsave されないため再開時は再 set',
           'All valid cells of the ENC grid system;\nnot saved: set again after a restart')),
    ]
    for index, (color, fill, title, unit, apply, later, note) in enumerate(rows):
        y = 633 + index * 180
        rect(ax, 55, y, 1690, 154, fill, 'none')
        rect(ax, 55, y, 5, 154, color, 'none')
        text(ax, 80, y + 22, title, 12.5, color=color, weight='bold')
        text(ax, 80, y + 79, unit, 11, color=MUTED)
        block(ax, 488, y + 36, apply, 465, 12, color=color, weight='bold')
        arrow(ax, [(996, y + 70), (1079, y + 70)], color)
        text(ax, 1110, y + 18, later, 11.5, color=color, weight='bold')
        block(ax, 1110, y + 67, note, 602, 10.5)
    block(ax, 57, 1181, t('適用できる変数・セルには条件がある。降水・地形・地下貯留などの受理条件は本文を参照。',
                          'Acceptance and cell masks depend on the variable. See the text for precipitation, terrain and subsurface-state rules.'),
          1670, 10.5, color=MUTED)
    return fig


BUILDERS = {'bmi_control': build_control, 'bmi_arrays': build_arrays,
            'bmi_exchange': build_exchange}


def export(fig, stem, lang):
    dest = Path(__file__).resolve().parents[1] / (stem + ('' if lang == 'ja' else '_en'))
    fig.savefig(dest.with_suffix('.png'), dpi=DPI)
    svg = StringIO()
    fig.savefig(svg, format='svg', metadata={'Date': None})
    content = '\n'.join(s.rstrip() for s in svg.getvalue().splitlines()) + '\n'
    dest.with_suffix('.svg').write_text(content, encoding='utf-8', newline='\n')
    plt.close(fig)
    return str(dest.with_suffix('.png'))


def draw(lang):
    with drawing_style():
        for stem, builder in BUILDERS.items():
            result = export(builder(lang), stem, lang)
    return result
