"""Landform update cadence and effective process time, independent of processes.

Generate only this pair with: python docs/figs/make_guide_figs.py geomorph_morfac
The timeline is an illustrative fresh run, not solver output. The uplift inset
uses one shared profile translated vertically; its displacement is schematic.
"""
from io import StringIO
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle, Polygon
from _schematic import drawing_style, text, block, line, arrow, INK, MUTED, RULE

CANVAS, DPI = (1575, 1320), 150
HYD, GEO, LAND = '#2878bc', '#bc5727', '#397958'
DT, REQUESTED, M = 10, 26, 4
N = int(np.floor(REQUESTED / DT + 0.5))  # Fortran NINT for this positive example.
DTW, DTS = N * DT, N * DT * M
T0, TT = 3600, 3720
STEPS = (TT - T0) // DT
UPDATES = tuple(range(N, STEPS + 1, N))
PROFILE_X = np.array([895, 995, 1110, 1255, 1355, 1485])
PROFILE_BEFORE = np.array([735, 735, 780, 797, 797, 822])
UPLIFT_PX = 43

T = {
 'ja': {
    'title':'地形変化の実行制御  |  更新間隔と加速係数',
    'sub':'dt_geomorph: 地形を更新する頻度  /  morfac: 地形過程に使う時間の倍率',
    'a':'(a) 更新時刻  —  説明用の新規計算: dt = 10 s、dt_geomorph = 26 s、morfac = 4',
    'cadence':'n = NINT(dt_geomorph / dt) = 3   →   実際の更新間隔 dtw = n × dt = 30 s',
    'hyd':'水理\n毎ステップ',
    'geo':'地形\nn ステップごと',
    'origin':'初期状態\n更新なし',
    'interval':'dtw = 30 s',
    'rounding':'NINT: 最も近い整数に丸める（0.5 は切り上げ）。dt_geomorph = 0 なら n = 1。',
    'b':'(b) 1回の更新に使う時間と、過程ごとの適用先',
    'effective':'実効時間刻み dts = dtw × morfac = 120 s',
    'processes':'掃流砂・クリープ・乾式斜面侵食・風化・隆起\n各過程を dts で評価する（風化は土層厚 sd を更新）。',
    'exchange_title':'浮遊砂・斜面浸食の場合',
    'exchange':'水柱 hs との交換は dtw で評価し、対応する河床変化に morfac を掛ける。\nhs の移流は水理時間。',
    'limits':'土砂供給量や侵食制限が効くため、最終的な Δz が常に morfac に比例するわけではない。',
    'uplift':'例: 一様な隆起だけを有効化',
    'before':'更新前の z',
    'after':'更新後の z',
    'uplift_note':'U: 隆起速度 [m/s]。土層厚 sd は一定。',
    'c':'(c) 経過時間の読み方と適用条件',
    'elapsed':'水理の経過時間: tt − t0 = 120 s  /  地形側: 4回 × dts = 480 s（8分）',
    'years':'更新回数を Nupdate とすると、地形側の累積時間 [年] = Nupdate × dts / (365.25 × 86400)',
    'whole':'更新間隔をちょうど使い切る新規計算では、Nupdate × dts = (tt − t0) × morfac。',
    'events':'morfac = 1: 土石流 f_debris・動く底層 f_bedslide では必須。',
    'longterm':'morfac > 1: 長期変化の近似。降雨・境界条件の時刻は加速せず、過程の安定条件も満たす必要がある。',
    'footer':'更新タイミングと隆起の模式図（計算結果ではない）。数値は説明用で、推奨設定ではない。併用制約の詳細は本文を参照。',
 },
 'en': {
    'title':'Landform run control  |  Update interval and acceleration factor',
    'sub':'dt_geomorph: how often landform processes run  /  morfac: time multiplier for landform processes',
    'a':'(a) Update timing  —  Illustrative fresh run: dt = 10 s, dt_geomorph = 26 s, morfac = 4',
    'cadence':'n = NINT(dt_geomorph / dt) = 3   →   Actual update interval dtw = n × dt = 30 s',
    'hyd':'Hydraulics\nevery step',
    'geo':'Landform\nevery n steps',
    'origin':'Initial state\nno update',
    'interval':'dtw = 30 s',
    'rounding':'NINT: nearest integer (positive half-ties round up). dt_geomorph = 0 gives n = 1.',
    'b':'(b) Time used in one update and where acceleration applies',
    'effective':'Effective time step dts = dtw × morfac = 120 s',
    'processes':'Bedload, creep, dry-slope erosion, weathering, uplift:\neach uses dts (weathering updates soil depth sd).',
    'exchange_title':'Suspended sediment and hillslope erosion',
    'exchange':'Exchange with water-column hs uses dtw; the corresponding bed change is scaled by morfac. Advection of hs uses hydraulic time.',
    'limits':'Sediment supply and erosion limits can prevent the final Δz from being proportional to morfac.',
    'uplift':'Example: uniform uplift alone',
    'before':'z before update',
    'after':'z after update',
    'uplift_note':'U: uplift rate [m/s]. Soil depth sd is unchanged.',
    'c':'(c) Elapsed time and conditions for use',
    'elapsed':'Hydraulic duration: tt − t0 = 120 s  /  Landform time: 4 updates × dts = 480 s (8 min)',
    'years':'With Nupdate updates, accumulated landform time [yr] = Nupdate × dts / (365.25 × 86400)',
    'whole':'For a fresh run with complete update intervals: Nupdate × dts = (tt − t0) × morfac.',
    'events':'morfac = 1 is required for debris flow f_debris and the moving bed layer f_bedslide.',
    'longterm':'morfac > 1 approximates long-term change. Rainfall/boundary clocks stay unchanged; process stability limits still apply.',
    'footer':'Schematic update timing and uplift, not solver output. Numbers are illustrative, not recommended settings. See the text for coupling restrictions.',
 },
}


def step_x(it):
    return 370 + it * 90


def bracket(ax, x0, x1, y, color):
    line(ax, [(x0, y-6), (x0, y+6)], color, .9)
    line(ax, [(x1, y-6), (x1, y+6)], color, .9)
    line(ax, [(x0, y), (x1, y)], color, .9)


def build(lang):
    t = T[lang]
    fig = plt.figure(figsize=(CANVAS[0]/DPI, CANVAS[1]/DPI), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set(xlim=(0, CANVAS[0]), ylim=(CANVAS[1], 0)); ax.axis('off')
    text(ax, 30, 20, t['title'], size=12, weight='bold')
    text(ax, 30, 65, t['sub'], size=9, color=MUTED)
    text(ax, 30, 113, t['a'], size=10, weight='bold')
    text(ax, 30, 160, t['cadence'], size=10, color=GEO)
    text(ax, 30, 256, t['hyd'], size=10, color=HYD, va='center')
    text(ax, 30, 365, t['geo'], size=10, color=GEO, va='center')
    line(ax, [(step_x(0), 266), (step_x(STEPS), 266)], HYD, 1.5)
    line(ax, [(step_x(0), 365), (step_x(STEPS), 365)], RULE, .9, ':')
    for it in range(STEPS+1):
        x = step_x(it)
        line(ax, [(x, 258), (x, 274)], HYD, .9).set_gid(f'hyd_{it}')
        if it % N == 0:
            text(ax, x, 291, f'{T0+it*DT} s', size=8.8, ha='center', color=HYD)
    for it in UPDATES:
        x = step_x(it)
        arrow(ax, [(x, 322), (x, 352)], GEO, size=10).set_gid(f'update_{it}')
        ax.plot(x, 365, 'o', color=GEO, ms=5, zorder=10)
    text(ax, step_x(0), 391, t['origin'], size=8.5, color=MUTED, ha='center')
    text(ax, step_x(0), 327, 't0', size=8.4, ha='center', color=MUTED)
    text(ax, step_x(STEPS), 391, 'tt', size=8.4, ha='center', color=MUTED)
    bracket(ax, step_x(0), step_x(1), 230, HYD)
    text(ax, (step_x(0)+step_x(1))/2, 200, 'dt = 10 s', size=8.7, color=HYD, ha='center')
    bracket(ax, step_x(3), step_x(6), 410, GEO)
    text(ax, (step_x(3)+step_x(6))/2, 430, t['interval'], size=9.2, color=GEO, ha='center')
    text(ax, 30, 474, t['rounding'], size=8.7, color=MUTED)
    line(ax, [(30, 518), (1545, 518)], RULE, .8)
    text(ax, 30, 539, t['b'], size=10, weight='bold')
    ax.add_patch(Rectangle((30, 583), 780, 349, facecolor='#f8f5f0', edgecolor='none'))
    ax.add_patch(Rectangle((840, 583), 705, 349, facecolor='#f2f6f3', edgecolor='none'))
    text(ax, 50, 603, t['effective'], size=9.7, color=GEO, weight='bold')
    block(ax, 50, 651, t['processes'], 740, size=8.9)
    text(ax, 50, 723, t['exchange_title'], size=9, weight='bold')
    block(ax, 50, 764, t['exchange'], 730, size=8.7)
    block(ax, 50, 858, t['limits'], 730, size=8.2, color=MUTED)
    text(ax, 865, 603, t['uplift'], size=9.7, weight='bold', color=LAND)
    line(ax, [(867, 658), (897, 658)], MUTED, 1.2, '--')
    text(ax, 909, 646, t['before'], size=8.4, color=MUTED)
    line(ax, [(1210, 658), (1240, 658)], LAND, 1.5)
    text(ax, 1252, 646, t['after'], size=8.4, color=LAND)
    new = PROFILE_BEFORE - UPLIFT_PX
    p = Polygon(list(zip(PROFILE_X, new))+[(PROFILE_X[-1], 869),(PROFILE_X[0], 869)],
                closed=True, facecolor='#d9e6d8', edgecolor='none', zorder=1)
    p.set_gid('uplift_fill'); ax.add_patch(p)
    line(ax, list(zip(PROFILE_X, PROFILE_BEFORE)), MUTED, 1.15, '--').set_gid('profile_before')
    line(ax, list(zip(PROFILE_X, new)), LAND, 1.5).set_gid('profile_after')
    # Anchor both ends at exactly the same x and their respective profile heights.
    x = 1180
    old_y = np.interp(x, PROFILE_X, PROFILE_BEFORE)
    arrow(ax, [(x, old_y), (x, old_y-UPLIFT_PX)], GEO, size=9).set_gid('uplift_arrow')
    text(ax, 1225, 704, 'Δz = U × dts', size=10, color=GEO)
    text(ax, 865, 893, t['uplift_note'], size=8.1, color=LAND)
    text(ax, 30, 965, t['c'], size=10, weight='bold')
    text(ax, 30, 1011, t['elapsed'], size=10, color=GEO)
    text(ax, 30, 1060, t['years'], size=9.2)
    text(ax, 30, 1106, t['whole'], size=8.7, color=MUTED)
    text(ax, 30, 1160, t['events'], size=9.1, color=HYD)
    block(ax, 30, 1207, t['longterm'], 1510, size=8.8)
    line(ax, [(30, 1265), (1545, 1265)], RULE, .8)
    text(ax, 30, 1285, t['footer'], size=7.6, color=MUTED)
    return fig


def draw(lang):
    if lang not in T:
        raise ValueError('lang must be ja or en')
    out = Path(__file__).resolve().parents[1]/('geomorph_morfac'+('' if lang=='ja' else '_en')+'.png')
    with drawing_style():
        fig = build(lang)
        try:
            fig.savefig(out, dpi=DPI)
            svg = StringIO()
            fig.savefig(svg, format='svg', metadata={'Date':None,
                'Description':'ENCflow landform update cadence and effective process time. Illustrative fresh run and uniform uplift; not solver output.'})
            out.with_suffix('.svg').write_text('\n'.join(x.rstrip() for x in svg.getvalue().splitlines())+'\n', encoding='utf-8', newline='\n')
        finally:
            plt.close(fig)
    return str(out)
