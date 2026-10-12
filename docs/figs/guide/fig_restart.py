"""State save and two restore modes, based on m_state / m_main / m_swflow_enc.

Both modes restore shared fields, ENC edge state and saved module state.
Mode 1 retains the time axis and counters; mode 2 resets them. Timeline
coordinates are schematic, not numerical results. Shared statistics and
compatibility checks are separate from the state-transfer arrows.
Generate only this figure: python docs/figs/make_guide_figs.py restart
"""
from io import StringIO
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle, Circle
from _schematic import drawing_style, text, block, line, arrow, INK, MUTED, RULE

CANVAS, DPI = (1575, 1470), 150
BLUE, GREEN, GOLD = '#287ca5', '#52744b', '#a47728'
SAVE_BOX = (35, 260, 1505, 197)
MODE_BOXES = ((35, 535, 740, 580), (800, 535, 740, 580))
FORK = (787.5, 493)
RESTORE_ROUTES = {
    'restore_mode1': [FORK, (405, 493), (405, 535)],
    'restore_mode2': [FORK, (1170, 493), (1170, 535)],
    'scenario_a': [(990, 715), (1030, 715)],
    'scenario_b': [(990, 815), (1030, 815)],
}
T = {
 'ja': {
  'title': '状態保存と再開  |  同じ保存状態から、継続または新しい時間軸へ',
  'sub': '2つのモードは保存対象の状態を共通に復元する。違うのは時間軸と、ステップ・出力番号の扱い。',
  'saving': '(a) 保存側のラン\nf_state_save = 1',
  'saved_time': '保存時刻 t_s',
  'write': '終了処理で保存',
  'store': 'dir_save（既定: save/）  |  両モードが読む保存一式',
  'fields': '共有の場  /  state.dat\n水深・地形・貯留・土砂など\nh, z, hrs, hg, sd, hs',
  'edges': 'ENCの力学状態  /  swflow_enc.dat\nエッジの流速 uv・流量 mn\n有効時は動的な配分・通水率の表も保存',
  'modules': '保存対象のモジュール内部状態\n地下水・積雪・流木・瓦礫など\n有効な機能の私有ファイル',
  'metadata': 'save_info.txt: 保存時刻 t_s・ステップ it・出力番号 ifn・t0・dt と、形式・格子数・実数精度など',
  'm1': '(b) モード1  |  同じ時間軸を継続',
  'm2': '(c) モード2  |  初期条件として利用',
  'clock1': 't = t0 + dt × it  を継続',
  'clock2': '新しい t0・date0_c から開始（dt も変更可）',
  'history': '保存までの区間',
  'later': '延長した終了時刻',
  'zero1': '0000: t_s での復元状態\n以後の通常出力は保存した ifn の続き番号。',
  'same': '同じ\n保存状態',
  'scenario_a': 'A', 'scenario_b': 'B',
  'zero2': 'A・Bとも 0000: 新しい t0 に置いた復元状態',
  'details1': 't0・dt は保存時と同じ。暦・入力・設定も揃える。\n保存した it・ifn を引き継いで計算を進める。\ntt は次のステップへ進める値まで延長する。\n再保存する場合も f_state_save = 1 を指定。\n厳密一致の条件と例外は本文を参照。',
  'details2': '各シナリオで it = 0・ifn = 0 から開始。\n時系列外力は新しい時間軸に合わせて読み直す。\nシナリオ先頭の外力と保存状態を整合させる。\n分岐元の保存一式をA・Bそれぞれで利用する。\n中断なしランとの厳密一致を目的としない。',
  'common': '両モードに共通すること',
  'cards': [
   ('0000 と統計は役割が異なる',
    '0000 は各ランの開始状態。時刻ゼロとは限らない。\n最大値統計（H9999など）・積算線流量 qcum は\n保存対象外。復元後のランで再集計する。\n全期間の統計が必要なら、各区間の出力から後処理。'),
   ('互換性の検査と、利用者が揃える条件',
    '保存形式・格子数・実数精度・成分数を検査。\nモード1は t0・dt と終了ステップも検査する。\n格子の位置・入力内容の一致を保証する検査ではない。\nENCが対象。STGは復元に対応していない。'),
  ],
  'footer': '時間軸と分岐は手順の模式図。保存時刻 t_s は save_info.txt の t。数値計算結果を示す図ではない。',
 },
 'en': {
  'title': 'State save and restore  |  Continue a run or start a new time axis',
  'sub': 'Both modes restore the saved state. They differ in the time axis and in the step and output counters.',
  'saving': '(a) Saving run\nf_state_save = 1',
  'saved_time': 'Saved time t_s',
  'write': 'Save during finalization',
  'store': 'dir_save (default: save/)  |  One set of saved files for either mode',
  'fields': 'Shared fields  /  state.dat\nDepth, terrain, storage, sediment, etc.\nh, z, hrs, hg, sd, hs',
  'edges': 'ENC dynamics  /  swflow_enc.dat\nEdge velocity uv and discharge mn\nDynamic allocation / conveyance tables if active',
  'modules': 'Module state included in the save\nGroundwater, snow, wood, debris, etc.\nPrivate files of the active features',
  'metadata': 'save_info.txt: saved time t_s, step it, output counter ifn, t0, dt, plus format, grid counts, real precision, etc.',
  'm1': '(b) Mode 1  |  Continue the same time axis',
  'm2': '(c) Mode 2  |  Use as an initial condition',
  'clock1': 'Continue with t = t0 + dt × it',
  'clock2': 'New t0 and date0_c (dt may also change)',
  'history': 'Before the save',
  'later': 'Extended end time',
  'zero1': '0000: restored state at t_s\nRegular outputs continue from the saved counter ifn.',
  'same': 'Same\nsaved state',
  'scenario_a': 'A', 'scenario_b': 'B',
  'zero2': 'Both A and B: 0000 is the restored state at the new t0.',
  'details1': 'Keep t0 and dt; retain the calendar, inputs and settings.\nContinue from the saved step it and output counter ifn.\nExtend tt far enough to allow another step.\nSet f_state_save = 1 to save again at the end.\nSee the text for exact-match conditions and exceptions.',
  'details2': 'Start each scenario with it = 0 and ifn = 0.\nRead time-series forcing on the new time axis.\nAlign initial forcing values with the restored state.\nUse the original saved files separately for A and B.\nExact agreement with an uninterrupted run is not the aim.',
  'common': 'Shared by both restore modes',
  'cards': [
   ('0000 and statistics serve different roles',
    '0000 is this run’s initial state, not necessarily time zero.\nMaxima (such as H9999) and cumulative cell discharge\nqcum are not saved. Recompute them within the new run.\nFor whole-run statistics, post-process all intervals.'),
   ('Compatibility checks and user-supplied consistency',
    'Check format, grid counts, real precision and field count.\nMode 1 also checks t0, dt and the end step.\nThese checks do not establish grid or input identity.\nRestore supports ENC. STG cannot restore a saved state.'),
  ],
  'footer': 'Schematic timelines and branches, not numerical results. Saved time t_s is the value t in save_info.txt.',
 },
}


def rect(ax, key, box, fill, edge=RULE):
    x, y, w, h = box
    p = Rectangle((x, y), w, h, fc=fill, ec=edge, lw=.7, zorder=1)
    ax.add_patch(p); p.set_gid(key)
    return p


def dot(ax, key, xy, color):
    p = Circle(xy, 5.5, fc=color, ec='white', lw=1, zorder=12)
    ax.add_patch(p); p.set_gid(key)


def arr(ax, key, xy, color):
    p = arrow(ax, xy, color, lw=1.6, size=10)
    p.set_gid(key)
    return p


def build(lang):
    t = T[lang]
    fig = plt.figure(figsize=(CANVAS[0]/DPI, CANVAS[1]/DPI), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set(xlim=(0, CANVAS[0]), ylim=(CANVAS[1], 0)); ax.axis('off')
    text(ax, 35, 30, t['title'], size=13, weight='bold')
    text(ax, 35, 78, t['sub'], size=8.8, color=MUTED)
    text(ax, 35, 150, t['saving'], size=9.8, weight='bold', color=GOLD)
    text(ax, 345, 152, 't0', size=9, color=GOLD, ha='center')
    text(ax, 1000, 152, t['saved_time'], size=9, color=GOLD, ha='center')
    arr(ax, 'saving_timeline', [(345, 199), (1000, 199)], GOLD)
    dot(ax, 'saving_start', (345, 199), GOLD)
    dot(ax, 'saving_end', (1000, 199), GOLD)
    arr(ax, 'write_state', [(1000, 211), (1000, 260)], GOLD)
    text(ax, 1030, 221, t['write'], size=8.6, color=GOLD)
    rect(ax, 'save_box', SAVE_BOX, '#fbf5e9')
    text(ax, 55, 278, t['store'], size=10, weight='bold', color=GOLD)
    for x, key, width in [(55, 'fields', 465), (552, 'edges', 488), (1065, 'modules', 450)]:
        block(ax, x, 326, t[key], width, size=8.4)
    line(ax, [(55, 415), (1520, 415)], '#e4d4b5', .7)
    text(ax, 55, 430, t['metadata'], size=8, color=MUTED)
    line(ax, [(787.5, 457), FORK], MUTED, 1.6).set_gid('restore_trunk')
    for key, color in [('restore_mode1', BLUE), ('restore_mode2', GREEN)]:
        arr(ax, key, RESTORE_ROUTES[key], color)
    for n, (key, color) in enumerate([('m1', BLUE), ('m2', GREEN)]):
        x = MODE_BOXES[n][0]
        rect(ax, f'mode_{n+1}', MODE_BOXES[n], '#f6f9fb' if n==0 else '#f6f9f3')
        text(ax, x+22, 557, t[key], size=10, weight='bold', color=color)
        text(ax, x+22, 603, f'f_state_restore = {n+1}', size=9.5, weight='bold', color=color)
        text(ax, x+22, 652, t[f'clock{n+1}'], size=8.6, color=color)
    text(ax, 110, 707, t['history'], size=7.8, color=MUTED)
    text(ax, 312, 707, 't_s', size=9, color=BLUE, ha='center')
    text(ax, 718, 707, 'tt', size=9, color=BLUE, ha='center')
    line(ax, [(95, 751), (312, 751)], MUTED, 1.4, ls='--').set_gid('past_interval')
    arr(ax, 'continuation', [(312, 751), (718, 751)], BLUE)
    dot(ax, 'mode1_initial', (312, 751), BLUE)
    text(ax, 718, 779, t['later'], size=8, color=BLUE, ha='right')
    text(ax, 57, 831, t['zero1'], size=8.5, color=BLUE)
    # Explicit branches to BOTH scenarios; neither branch crosses a timeline.
    rect(ax, 'scenario_state', (826, 697, 140, 136), 'white', '#bdcbb6')
    text(ax, 896, 744, t['same'], size=8.5, color=GREEN, ha='center', va='center')
    line(ax, [(966, 765), (990, 765)], GREEN, 1.6).set_gid('scenario_stem')
    line(ax, [(990, 715), (990, 815)], GREEN, 1.6).set_gid('scenario_trunk')
    for key, yy in [('scenario_a', 715), ('scenario_b', 815)]:
        arr(ax, key, RESTORE_ROUTES[key], GREEN)
        arr(ax, key+'_timeline', [(1030, yy), (1450, yy)], GREEN)
        dot(ax, key+'_initial', (1030, yy), GREEN)
        text(ax, 1030, yy-32, 't0', size=8.5, color=GREEN, ha='center')
        text(ax, 1450, yy-32, 'tt', size=8.5, color=GREEN, ha='center')
        text(ax, 1480, yy, t[key], size=9.5, color=GREEN, weight='bold', va='center')
    text(ax, 822, 862, t['zero2'], size=8.4, color=GREEN)
    for x, key, color in [(57, 'details1', BLUE), (822, 'details2', GREEN)]:
        line(ax, [(x, 909), (x+696, 909)], RULE, .7)
        block(ax, x, 934, t[key], 696, size=8.5)
    text(ax, 35, 1150, t['common'], size=10.5, weight='bold')
    for n, (head, body) in enumerate(t['cards']):
        x = 35+765*n
        rect(ax, f'common_{n}', (x, 1196, 740, 205), '#fafaf7')
        text(ax, x+20, 1214, head, size=9.1, weight='bold')
        block(ax, x+20, 1261, body, 700, size=8.4)
    text(ax, 35, 1426, t['footer'], size=8, color=MUTED)
    return fig


def draw(lang):
    if lang not in T:
        raise ValueError('lang must be ja or en')
    out = Path(__file__).resolve().parents[1]/('restart_modes'+('' if lang=='ja' else '_en')+'.png')
    with drawing_style():
        fig = build(lang)
        try:
            fig.savefig(out, dpi=DPI)
            svg = StringIO()
            fig.savefig(svg, format='svg', metadata={'Date': None, 'Description':
                'ENCflow state save and two restore modes: shared saved state, continuing versus new time axes, explicit A/B branches, and statistics reset. Schematic, not a computed result.'})
            out.with_suffix('.svg').write_text('\n'.join(s.rstrip() for s in svg.getvalue().splitlines())+'\n', encoding='utf-8', newline='\n')
        finally:
            plt.close(fig)
    return str(out)
