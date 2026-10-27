"""VZ runoff: how the zone raster, shared reference columns, soil depth and outlets relate.

Schematic only (not solver output). Cell counts, layer lines and the depth scale
are illustrative; the column depth is broken between 2 m and L = 10 m. The roles
follow src/m_vzflow.f90 (zones read the column flux at each cell's soil depth and
send the zone drainage to an outlet cell or out of the system).
"""
from pathlib import Path as FilePath
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from _style import out_path, C_X, C_C, C_P
from _schematic import drawing_style, text, block, wrap, line, arrow, export, INK, MUTED, RULE

T = {
    'ja': dict(
        title='VZ 流出の部品の関係: 区画番号ラスタ・共有参照柱・土層厚・出口',
        sub='fn_vz  |  &list_vz(fn_vz_zone)/ &list_vz_column / &list_vz_zone  +  土層厚 sd(&list_geoinfo)',
        a='(a) 区画番号ラスタ fn_vz_zone(平面)',
        a_sub='数字 = 区画番号。0 = 適用外(河道・谷底など。地表流のまま)',
        b='(b) 共有参照柱 &list_vz_column(土壌ごとに 1 本の深い 1 次元柱)',
        col1='柱 1', col2='柱 2', refs1='区画 1・2 が参照', refs2='区画 3 が参照',
        rain='雨(参照するセルの雨)',
        out_sys='系外へ(区画 2: vz_out_kind = 2)',
        outs=('出口1', '出口3'),
        legend='出口1・出口3: 区画 1・3 の出口セル(vz_out_cell)    水色: 河道(区画 0)    橙の矢印: 区画の排水の移送(瞬時)',
        depth='深さ (m)', bottom='L = 10 m(既定)\n下端は自由排水',
        reads=['A: 土層厚 0.3 m', 'B: 土層厚 0.8 m', 'C: 土層厚 1.5 m'],
        read_note='セルの土層厚の\n深さで柱を読む',
        col2_note='区画 3 のセルも\nそれぞれの土層厚で読む',
        notes=[
            ('1  区画番号ラスタ(fn_vz_zone)',
             '同じ番号のセル群が 1 つの区画。区画は排水をまとめて出口へ送る単位です。'
             '0 のセルは VZ を適用せず、地表流のまま解きます。'),
            ('2  共有参照柱(&list_vz_column)',
             '土壌(物性・初期状態・雨)ごとに 1 本の深い 1 次元柱を解きます。区画は vz_zone_col で柱を選び'
             '(省略時は区画番号と同じ番号の柱)、土壌が同じなら別の区画とも共有できます(図の区画 1・2)。'
             '柱の上端には、その柱を参照するセルの雨を与えます。'),
            ('3  土層厚(&list_geoinfo の sd)',
             'セルごとの「柱を読む深さ」です。セルの排水 = その深さの下向きの積算流束、'
             'セルの貯留 = 地表からその深さまでの水。区画の排水は Σ(セル面積 × 排水)。'
             '土層厚 0 のセルは雨がそのまま排水になります。'),
            ('4  出口(&list_vz_zone の vz_out_kind)',
             '1: 出口セル vz_out_cell の地表水へ(複数なら配分率 vz_out_w)、2: 系外へ。'
             'dt_vz ごとに瞬時に移し、側方の地下流は解きません。出口は VZ でないセル(区画 0)に置きます。'),
        ],
        foot='模式図(計算結果ではない)。セルの数・柱の層の線・深さの縮尺は説明用で、柱の深さは 2 m と 10 m の間を省略。',
    ),
    'en': dict(
        title='VZ runoff components: zone raster, shared reference columns, soil depth and outlets',
        sub='fn_vz  |  &list_vz (fn_vz_zone) / &list_vz_column / &list_vz_zone  +  soil depth sd (&list_geoinfo)',
        a='(a) Zone number raster fn_vz_zone (plan view)',
        a_sub='Number = zone number. 0 = not applied (channel, valley floor, etc.; surface flow as usual)',
        b='(b) Shared reference columns &list_vz_column (one deep 1D column per soil)',
        col1='Column 1', col2='Column 2', refs1='used by zones 1 and 2', refs2='used by zone 3',
        rain='Rain (on the cells using it)',
        out_sys='Out of the system (zone 2: vz_out_kind = 2)',
        outs=('Out 1', 'Out 3'),
        legend='Out 1, Out 3: outlet cells of zones 1 and 3 (vz_out_cell)    Light blue: channel (zone 0)    Orange arrows: transfer of zone drainage (instantaneous)',
        depth='Depth (m)', bottom='L = 10 m (default)\nfree drainage at the bottom',
        reads=['A: soil depth 0.3 m', 'B: soil depth 0.8 m', 'C: soil depth 1.5 m'],
        read_note='Read the column at\neach cell\'s soil depth',
        col2_note='Zone 3 cells also read it\nat their own soil depths',
        notes=[
            ('1  Zone number raster (fn_vz_zone)',
             'Cells with the same number form one zone, the unit whose drainage is collected and sent to an '
             'outlet. Cells with 0 are not VZ and keep the usual surface flow.'),
            ('2  Shared reference columns (&list_vz_column)',
             'One deep 1D column is solved per soil (properties, initial state, rain). A zone chooses its column '
             'with vz_zone_col (default: the column with the zone\'s number); zones with the same soil can share '
             'one (zones 1 and 2 in the figure). The top of a column receives the rain on the cells using it.'),
            ('3  Soil depth (sd in &list_geoinfo)',
             'The depth at which each cell reads the column. Cell drainage = cumulative downward flux at that '
             'depth; cell storage = water from the surface to that depth. Zone drainage = Σ (cell area × '
             'drainage). A cell with soil depth 0 passes the rain on as drainage.'),
            ('4  Outlets (vz_out_kind in &list_vz_zone)',
             '1: to the surface water of the outlet cells vz_out_cell (split by vz_out_w if several); 2: out of '
             'the system. Moved instantly every dt_vz; lateral subsurface flow is not solved. Outlets must be '
             'non-VZ cells (zone 0).'),
        ],
        foot='Schematic, not solver output. Cell counts, layer lines and the depth scale are illustrative; '
             'the column is broken between 2 m and 10 m.',
    ),
}

# 区画番号(行 0 が上)。列 3 は河道(区画 0)
ZONES = [[2, 2, 2, 0, 1, 1, 1, 0],
         [2, 2, 2, 0, 1, 1, 1, 1],
         [2, 2, 2, 0, 1, 1, 1, 1],
         [3, 3, 3, 0, 1, 1, 1, 1],
         [3, 3, 3, 0, 1, 1, 1, 0],
         [0, 3, 3, 0, 0, 1, 1, 0],
         [0, 0, 0, 0, 0, 0, 0, 0]]
CHANNEL_COL = 3
FILL = {0: 'white', 1: '#f6c89a', 2: '#f7e3a1', 3: '#c8e2b4'}
CH_FILL = '#cfe0f6'
X0, Y0, D = 4.0, 6.0, 5.0                 # 平面図の左下と格子間隔
OUTLETS = [(2, 3), (4, 3)]                # 区画 1・3 の出口セル(行, 列)
READS = [(0, 6, 0.3), (2, 5, 0.8), (4, 4, 1.5)]   # セル A・B・C(行, 列, 土層厚 m)
CX1, CX2, CW = 61.0, 88.0, 6.5            # 柱 1・2 の左端と幅
YS, YM = 40.0, 13.0                       # 地表の y と 1 m あたりの長さ(0〜2 m)
YB = 7.5                                  # 柱の下端(10 m)の y


def cell_xy(r, c):
    return X0 + c * D, Y0 + (len(ZONES) - 1 - r) * D


def depth_y(d):
    return YS - YM * d


def plan(ax, t):
    text(ax, X0, 53.6, t['a'], size=10, weight='bold')
    text(ax, X0, 51.2, t['a_sub'], size=7.8, color=MUTED)
    for r, row in enumerate(ZONES):
        for c, z in enumerate(row):
            x, y = cell_xy(r, c)
            face = CH_FILL if c == CHANNEL_COL else FILL[z]
            ax.add_patch(Rectangle((x, y), D, D, fc=face, ec=C_P, lw=0.6, zorder=1))
            text(ax, x + D / 2, y + D - 0.5, str(z), size=7.5, color=MUTED, ha='center')
    for name, (r, c) in zip(t['outs'], OUTLETS):
        x, y = cell_xy(r, c)
        ax.add_patch(Rectangle((x + 0.25, y + 0.25), D - 0.5, D - 0.5, fc='none', ec=C_X, lw=2.0, zorder=3))
        text(ax, x + D / 2, y + 2.2, name, size=7.8, color=C_X, ha='center', weight='bold')
    # 区画の排水の移送(区画 1 → 出口1、区画 3 → 出口3: 隣のセルから短い矢印。区画 2 → 系外)
    for (r, c), dx in zip(OUTLETS, (+1, -1)):
        xb, yb = cell_xy(r, c)
        xa = xb + dx * D
        arrow(ax, [(xa + D / 2, yb + 1.2), (xb + (D - 0.5 if dx > 0 else 0.5), yb + 1.2)], C_X, lw=1.6)
    x2, y2 = cell_xy(0, 1)
    arrow(ax, [(x2 + D / 2, y2 + D), (x2 + D / 2, y2 + D + 3.6)], C_X, lw=1.6)
    text(ax, x2 + D / 2 + 1.0, y2 + D + 3.6, t['out_sys'], size=7.6, color=C_X)
    # 土層厚を読むセル A・B・C
    for (r, c, d), lab in zip(READS, 'ABC'):
        x, y = cell_xy(r, c)
        ax.add_patch(Rectangle((x + 0.5, y + 0.5), D - 1.0, D - 1.0, fc='white', ec=INK, lw=1.0, zorder=3))
        text(ax, x + D / 2, y + D / 2 + 1.0, lab, size=9, ha='center', weight='bold')
    block(ax, X0, 4.6, t['legend'], 95, size=7.4, color=MUTED)


def column(ax, x, t, name, refs, reads):
    # 柱の土壌(0〜2 m を拡大)、省略記号、下端
    ax.add_patch(Rectangle((x, depth_y(2.0)), CW, YS - depth_y(2.0), fc='#e4d9c8', ec=INK, lw=1.0, zorder=1))
    for k in range(1, 20):
        yy = depth_y(0.1 * k)
        line(ax, [(x, yy), (x + CW, yy)], '#c9b79c', 0.4, z=2)
    yb2 = depth_y(2.0)
    ax.add_patch(Rectangle((x, YB), CW, yb2 - 2.2 - YB, fc='#e4d9c8', ec=INK, lw=1.0, zorder=1))
    for dy in (0.0, 0.9):
        line(ax, [(x - 0.6, yb2 - 0.8 - dy), (x + CW / 2, yb2 - 0.3 - dy), (x + CW + 0.6, yb2 - 1.0 - dy)],
             INK, 0.8, z=3)
    for k in range(3):
        xx = x + CW * (k + 1) / 4
        arrow(ax, [(xx, YS + 4.2), (xx, YS + 0.4)], C_C, lw=1.3, size=9)
    text(ax, x + CW / 2, YS + 9.0, name, size=9.5, ha='center', weight='bold')
    text(ax, x + CW / 2, YS + 6.9, refs, size=7.6, ha='center', color=MUTED)
    text(ax, x + CW + 0.8, YS + 3.4, t['rain'], size=7.2, color=C_C)
    arrow(ax, [(x + CW / 2, YB + 1.8), (x + CW / 2, YB - 1.6)], C_C, lw=1.2, size=8)
    for d, lab in reads:
        y = depth_y(d)
        line(ax, [(x - 0.3, y), (x + CW + 2.0, y)], C_X, 1.6, z=5)
        arrow(ax, [(x + CW / 2, y + 0.1), (x + CW / 2, y - 2.0)], C_X, lw=1.3, size=8, z=6)
        if lab:
            text(ax, x + CW + 2.4, y + 0.75, lab, size=8, color=C_X)


def columns(ax, t):
    text(ax, 52.0, 53.6, t['b'], size=10, weight='bold')
    column(ax, CX1, t, t['col1'], t['refs1'], [(d, lab) for (_, _, d), lab in zip(READS, t['reads'])])
    column(ax, CX2, t, t['col2'], t['refs2'], [(0.5, ''), (1.1, '')])
    for d in (0.0, 0.5, 1.0, 1.5, 2.0):
        y = depth_y(d)
        line(ax, [(CX1 - 1.0, y), (CX1, y)], INK, 0.8)
        text(ax, CX1 - 1.4, y + 0.6, '%g' % d, size=7.4, ha='right',
             bbox=dict(fc='white', ec='none', pad=0.6))      # 結ぶ破線より手前に
    text(ax, CX1 - 1.4, YB + 0.6, '10', size=7.4, ha='right')
    text(ax, CX1 - 1.4, YS + 2.6, t['depth'], size=7.6, color=MUTED, ha='right')
    text(ax, CX1 + CW + 2.4, depth_y(1.62), t['read_note'], size=7.6, color=MUTED)
    text(ax, CX2 + CW + 0.8, depth_y(1.25), t['col2_note'], size=7.4, color=MUTED)
    text(ax, (CX1 + CX2 + CW) / 2, YB + 1.5, t['bottom'], size=7.6, color=MUTED, ha='center')
    # 平面図のセル A・B・C と柱 1 の読む深さを結ぶ
    for (r, c, d) in READS:
        x, y = cell_xy(r, c)
        line(ax, [(x + D - 0.5, y + D / 2), (45.5, y + D / 2), (CX1 - 6.2, depth_y(d)), (CX1 - 0.3, depth_y(d))],
             C_X, 0.8, ls=(0, (3, 2)), z=4)


def para(ax, x, y, s, width, size=8.3, color=INK, gap=0.06, weight='normal'):
    """折り返した段落(和文の句読点・閉じ括弧が行頭に来ないよう前の行へ寄せる)。次の段落の y を返す"""
    lines = wrap(ax, s, width, size, weight).split('\n')
    for k in range(1, len(lines)):
        while lines[k] and lines[k][0] in '、。,.)）」':
            lines[k - 1] += lines[k][0]
            lines[k] = lines[k][1:]
        while lines[k - 1].rstrip() and lines[k - 1].rstrip()[-1] in '(（「':
            head = lines[k - 1].rstrip()
            lines[k - 1], lines[k] = head[:-1].rstrip(), head[-1] + lines[k]
    a = text(ax, x, y, '\n'.join(lines), size=size, color=color, weight=weight)
    ax.figure.canvas.draw()
    bb = a.get_window_extent(ax.figure.canvas.get_renderer())
    return ax.transData.inverted().transform((bb.x0, bb.y0))[1] - gap


def build(lang):
    if lang not in T:
        raise ValueError('lang must be ja or en')
    t = T[lang]
    fig = plt.figure(figsize=(12.6, 8.2))
    head = fig.add_axes([0.04, 0.925, 0.92, 0.06]); head.axis('off')
    head.set(xlim=(0, 1), ylim=(0, 1))
    block(head, 0, 1, t['title'], 1, size=11.5, weight='bold')
    text(head, 0, 0.30, t['sub'], size=8.4, color=MUTED)
    ax = fig.add_axes([0.012, 0.30, 0.96, 0.625])
    ax.set(xlim=(0, 100), ylim=(0, 56.5), aspect='equal', anchor='W'); ax.axis('off')
    plan(ax, t)
    columns(ax, t)
    notes = fig.add_axes([0.04, 0.08, 0.92, 0.205]); notes.axis('off')
    notes.set(xlim=(0, 1), ylim=(0, 1))
    line(notes, [(0, 1.03), (1, 1.03)], RULE, 0.8, clip_on=False)
    ys = [0.98, 0.98]
    for k, (head_s, body) in enumerate(t['notes']):
        col = 0 if k < 2 else 1
        x0 = 0.0 if col == 0 else 0.52
        y = para(notes, x0, ys[col], head_s, 0.46, size=9.0, weight='bold',
                 color={1: C_C, 3: C_X}.get(k, INK), gap=0.018)
        ys[col] = para(notes, x0, y, body, 0.46, size=8.3, gap=0.07)
    foot = fig.add_axes([0.04, 0.018, 0.92, 0.035]); foot.axis('off')
    foot.set(xlim=(0, 1), ylim=(0, 1))
    line(foot, [(0, 1.1), (1, 1.1)], RULE, 0.8, clip_on=False)
    block(foot, 0, 0.95, t['foot'], 1, size=7.8, color=MUTED)
    return fig


def draw(lang):
    with drawing_style():
        png = export(build(lang), out_path('vz_layout', lang))
        svg = FilePath(png).with_suffix('.svg')
        svg.write_bytes(svg.read_bytes().replace(b'\r\n', b'\n'))
        return png
