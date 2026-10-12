"""Raster order, encodings and result-file names (native bilingual vectors).

The original 4 x 5 values and their north-to-south / west-to-east order are
preserved. File numbering and precision follow m_output, m_record, m_fileio
and m_geotiff. This is a file-layout example, not simulation output.
"""
from io import StringIO
from pathlib import Path
from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle
from _schematic import drawing_style, text, block, line, arrow, MUTED, RULE

CANVAS = (1575, 1650)
DPI = 150
BLUE, GREEN = '#24678a', '#507640'
VALUES = (('0.0', '0.0', '0.3', '1.2', '0.1'),
          ('0.0', '0.4', '1.5', '0.8', '0.0'),
          ('0.2', '1.1', '1.9', '0.3', '0.0'),
          ('0.6', '1.4', '0.5', '0.0', '0.0'))
GRID = (935, 204, 100, 60)

T = {'ja': {
    'a': '(a) ラスタの並び — 先頭行が北端',
    'order': '行 j は北→南、列 i は西→東。地図と同じ向きで読み書きします。',
    'file': 'H0001.txt：行列テキストの例',
    'map': '同じ20セルを地図上に配置',
    'columns': '西 → 東   i = 1 … 5', 'north': '北',
    'first': '先頭行：j = 1', 'last': '最終行：j = 4',
    'example': '4行×5列の例（小数点以下1桁で表示）。色の濃さは値の大きさを表します。',
    'formats': '入力 f_input_mode：1・2・4のいずれかを選択。出力 f_output_mode：ビット和で併用（例：7 = 1 + 2 + 4）。',
    'txt': '1  行列テキスト  .txt', 'txt_body': '実数の出力は小数点以下4桁。\n格子・座標情報は別途指定。',
    'bil': '2  生バイナリ  .bil', 'bil_body': '実数の出力はfloat32。\n地理参照が有効なら .hdr を併記。',
    'tif': '4  GeoTIFF  .tif', 'tif_body': '実数の出力はfloat32、無圧縮。\n地理参照が必須（位置情報を格納）。',
    'b': '(b) 分布出力 — ファイル名と4桁番号',
    'root': '保存先：dir_result（既定 result/）',
    'prefix': '接頭辞：量（H = 水深）', 'number': '4桁の出力番号',
    'suffix': '接尾辞（既定は空文字）', 'extension': '出力形式の拡張子',
    'selection': '出力する量は f_out_* と有効な物理過程で決定。以下は接尾辞なしの例です。',
    'start': '開始状態\n再開時は復元状態', 'periodic': 'dt_file と出力窓で決まる通常出力\n時刻との対応：FILENUMBER.csv',
    'end': '最終ステップ\nの状態', 'stats': '9999：期間統計',
    'stats_body': '最大値などの分布。\n瞬間の状態とは別に保存。',
    'fixed': '0000・9998 は通常出力の窓とは別に保存。9999 の集計範囲と再開時の扱いは本文を参照。',
    'c': '(c) result/ に保存される補助ファイルと計測CSV',
    'aux': '分布の付随情報・実行の記録', 'measure': 'fn_record で設定した地点・測線の計測',
    'mapping': '番号・暦時刻・t(s)・ステップ it の対応表。',
    'always': '常に保存：開始時の地盤高 Z と領域マスク X。\nマスクは 0：領域外、1：陸域、2：海域。',
    'log_title': 'Log.txt ＋ 設定ファイルの控え',
    'log': 'ログ名は fn_log で変更可能。\n使用したパラメータファイル一式をコピー。',
    'probe': '各地点の時系列。0001 は地点番号。',
    'flux': '各測線の時系列。0001 は測線番号。',
    'summary': '地点・測線がある場合に保存する計測集計。',
    'cadence': '時系列は初期状態と dt_recrd・計測窓の判定時に記録。',
    'footer': 'outfn_suffix は分布・計測CSVの拡張子直前に付きます。FILENUMBER.csv・ログ・設定の控えには付きません。\n複数ランを分けるときは dir_result を分けてください。',
}, 'en': {
    'a': '(a) Raster order — the first row is the northern edge',
    'order': 'Rows j run north to south; columns i run west to east, as on a map.',
    'file': 'H0001.txt: matrix-text example',
    'map': 'The same 20 cells on a map',
    'columns': 'west → east   i = 1 … 5', 'north': 'N',
    'first': 'first row: j = 1', 'last': 'last row: j = 4',
    'example': 'A 4-row by 5-column example, shown with one decimal. Darker cells indicate larger values.',
    'formats': 'Input f_input_mode: choose 1, 2 or 4. Output f_output_mode: combine bits (e.g. 7 = 1 + 2 + 4).',
    'txt': '1  Matrix text  .txt', 'txt_body': 'Real output: four decimal places.\nGrid / coordinates supplied separately.',
    'bil': '2  Raw binary  .bil', 'bil_body': 'Real output: float32.\nAn active georeference adds .hdr.',
    'tif': '4  GeoTIFF  .tif', 'tif_body': 'Real output: float32, uncompressed.\nGeoreference required.',
    'b': '(b) Distributed output — names and 4-digit numbers',
    'root': 'Destination: dir_result (default result/)',
    'prefix': 'Prefix: quantity (H = depth)', 'number': '4-digit output number',
    'suffix': 'Suffix (empty by default)', 'extension': 'Format extension',
    'selection': 'Fields depend on f_out_* and active processes. The examples below use an empty suffix.',
    'start': 'State at start\nrestored on restart', 'periodic': 'Regular output: dt_file and its window\nTime mapping: FILENUMBER.csv',
    'end': 'State at the\nfinal step', 'stats': '9999: run statistics',
    'stats_body': 'Maps of maxima, etc.\nSeparate from state snapshots.',
    'fixed': '0000 and 9998 bypass the regular output window. See the text for the scope of 9999 and restart behavior.',
    'c': '(c) Auxiliary files and measurement CSVs in result/',
    'aux': 'Raster metadata and run records', 'measure': 'Points / transects configured in fn_record',
    'mapping': 'Output number, calendar time, t(s), and step it.',
    'always': 'Always saved: starting ground Z and domain mask X.\nMask: 0 outside, 1 land, 2 sea.',
    'log_title': 'Log.txt + copies of configuration files',
    'log': 'The log name can be changed with fn_log.\nThe parameter files used by the run are copied.',
    'probe': 'One time series per point; 0001 is the point ID.',
    'flux': 'One time series per transect; 0001 is its ID.',
    'summary': 'Measurement summary, when points / transects exist.',
    'cadence': 'Record the initial state, then at dt_recrd / window checks.',
    'footer': 'outfn_suffix goes before the extension of rasters and measurement CSVs, but not FILENUMBER.csv, logs or configuration copies.\nUse separate dir_result directories for separate runs.',
}}


def card(ax, x, y, w, h, fill, gid):
    p = Rectangle((x, y), w, h, facecolor=fill, edgecolor='none', gid=gid, zorder=0)
    ax.add_patch(p)
    return p


def build(lang):
    t = T[lang]
    fig = plt.figure(figsize=(CANVAS[0]/DPI, CANVAS[1]/DPI), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set(xlim=(0, CANVAS[0]), ylim=(CANVAS[1], 0)); ax.axis('off')
    text(ax, 48, 32, t['a'], 13, weight='bold')
    text(ax, 48, 83, t['order'], 10)
    text(ax, 115, 150, t['file'], 10.5, color=BLUE, weight='bold')
    text(ax, 935, 135, t['map'], 10.5, color=BLUE, weight='bold')
    text(ax, 1185, 171, t['columns'], 9, color=MUTED, ha='center')
    card(ax, 115, 204, 505, 240, '#f5f7f7', 'matrix')
    gx, gy, dx, dy = GRID
    for j, row in enumerate(VALUES):
        y = gy+(j+.5)*dy
        text(ax, 82, y, str(j+1), 9, color=MUTED, ha='right', va='center')
        for i, val in enumerate(row):
            text(ax, 163+100*i, y, val, 12, ha='center', va='center', family='DejaVu Sans Mono', gid=f'matrix-{j}-{i}')
            v = float(val)
            cell = Rectangle((gx+i*dx, gy+j*dy), dx, dy, fc='#76bad7' if v else 'white',
                             alpha=min(1, .25+.4*v) if v else 1, ec='none', gid=f'cell-{j}-{i}', zorder=1)
            ax.add_patch(cell)
            text(ax, gx+(i+.5)*dx, y, val, 10, ha='center', va='center', gid=f'value-{j}-{i}')
    for i in range(6): line(ax, [(gx+i*dx, gy), (gx+i*dx, gy+4*dy)], BLUE, .8)
    for j in range(5): line(ax, [(gx, gy+j*dy), (gx+5*dx, gy+j*dy)], BLUE, .8)
    arrow(ax, [(1488, 255), (1488, 180)], BLUE, 1.3)
    text(ax, 1488, 141, t['north'], 11, color=BLUE, ha='center', weight='bold')
    for j, key in [(0, 'first'), (3, 'last')]:
        y=gy+(j+.5)*dy
        arrow(ax, [(650, y), (905, y)], BLUE, 1.25).set_gid('row-arrow-'+str(j))
        text(ax, 778, y+(16 if j==0 else -43), t[key], 9.5, ha='center', color=BLUE)
    text(ax, 48, 473, t['example'], 9.2, color=MUTED)
    text(ax, 48, 518, t['formats'], 9.5)
    for x, k in [(48, 'txt'), (550, 'bil'), (1052, 'tif')]:
        card(ax, x, 561, 475, 111, '#f4f5f2', 'format-'+k)
        text(ax, x+20, 576, t[k], 10, weight='bold')
        block(ax, x+20, 615, t[k+'_body'], 435, 8.9)

    line(ax, [(48, 695), (1527, 695)], RULE, .8)
    text(ax, 48, 720, t['b'], 13, weight='bold')
    text(ax, 48, 770, t['root'], 9.5, color=MUTED)
    for x, w, val, key in [(48, 305, 'H', 'prefix'), (373, 290, '0001', 'number'),
                            (683, 430, 'outfn_suffix', 'suffix'), (1133, 394, '.txt / .bil / .tif', 'extension')]:
        card(ax, x, 811, w, 93, '#edf4f8', 'name-'+key)
        text(ax, x+w/2, 824, val, 12, color=BLUE, ha='center', weight='bold')
        text(ax, x+w/2, 866, t[key], 9, ha='center')
    text(ax, 48, 923, t['selection'], 9.2)
    arrow(ax, [(115, 993), (1132, 993)], BLUE, 1.1)
    for x, num in [(140, '0000'), (430, '0001'), (710, '0002 …'), (1055, '9998')]:
        ax.plot(x, 993, 's', ms=7, color=BLUE, gid='number-'+num, zorder=10)
        text(ax, x, 960, num, 10.5, ha='center', color=BLUE, weight='bold')
    text(ax, 140, 1016, t['start'], 8.8, ha='center')
    text(ax, 580, 1016, t['periodic'], 8.8, ha='center')
    text(ax, 1055, 1016, t['end'], 8.8, ha='center')
    card(ax, 1191, 966, 336, 111, '#edf3e9', 'statistics')
    text(ax, 1209, 979, t['stats'], 10, color=GREEN, weight='bold')
    block(ax, 1209, 1016, t['stats_body'], 300, 8.6)
    block(ax, 48, 1102, t['fixed'], 1479, 9.1, color=MUTED)

    line(ax, [(48, 1149), (1527, 1149)], RULE, .8)
    text(ax, 48, 1174, t['c'], 13, weight='bold')
    text(ax, 48, 1228, t['aux'], 10.5, color=BLUE, weight='bold')
    text(ax, 817, 1228, t['measure'], 10.5, color=GREEN, weight='bold')
    line(ax, [(780, 1230), (780, 1556)], RULE, .8)
    for y, label, key in [(1280, 'FILENUMBER.csv', 'mapping'),
                          (1371, 'Z0000 / X0000', 'always'),
                          (1484, t['log_title'], 'log')]:
        text(ax, 48, y, label, 10.5, color=BLUE, weight='bold')
        block(ax, 48, y+38, t[key], 690, 9)
    for y, label, key in [(1280, 'probes/probe0001.csv …', 'probe'),
                          (1371, 'fluxes/flux0001.csv …', 'flux'),
                          (1462, 'summary.csv', 'summary')]:
        text(ax, 817, y, label, 10.5, color=GREEN, weight='bold')
        block(ax, 817, y+38, t[key], 710, 9)
    block(ax, 817, 1535, t['cadence'], 710, 8.6, color=MUTED)
    block(ax, 48, 1590, t['footer'], 1479, 8.6, color=MUTED)
    return fig


def draw(lang):
    if lang not in T: raise ValueError('lang must be ja or en')
    dest=Path(__file__).resolve().parents[1]/('io_files'+('' if lang=='ja' else '_en'))
    with drawing_style():
        fig=build(lang); fig.savefig(dest.with_suffix('.png'), dpi=DPI)
        svg=StringIO(); fig.savefig(svg, format='svg', metadata={'Date': None})
        dest.with_suffix('.svg').write_text(svg.getvalue(), encoding='utf-8', newline='\n')
        plt.close(fig)
    return str(dest.with_suffix('.png'))
