"""time_axis: simulation time, integer-step schedules and fixed output slots.

The 18-step example is a schematic, not solver output. Markers follow
m_sysparam's rounding and m_main's step/window decisions.
"""
from io import StringIO
from pathlib import Path
import math
from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle
from _schematic import drawing_style, text, block, line, arrow, INK, MUTED, RULE

CANVAS, DPI = (1575, 1530), 150
X0, X1, N = 330, 1320, 18
BLUE, GREEN, ORANGE = '#2a78d6', '#498237', '#c95c2c'
T = {
    'ja': {
        'title': '計算時刻・出力間隔・時間窓',
        'sub': '&list_sysparam の時間設定。t0 と tt は t = 0 を基準にした同じ時間軸上の時刻。',
        'a': '(a) 時刻と計算期間を区別する',
        'origin': 't = 0（時間軸の原点）', 'start': 't0（開始時刻）', 'end': 'tt（指定終了時刻）',
        'duration': '指定する計算期間 = tt − t0',
        'formula': 't = t0 + dt × it     /     N = ceiling((tt − t0)/dt)     /     通常終了時刻 = t0 + dt × N',
        'round': 'it はステップ番号。N は切り上げなので、割り切れない場合は実際の終了時刻が tt を超える。',
        'date': 'date0_c = "2019-10-11 09:00" は t = 0 の暦。\n暦が必要な機能だけが参照し、t0 を暦の原点にする指定ではない。',
        'restart': '再開（f_state_restore = 1）: tt を先へ延長する。\nt0・dt を維持し、保存したステップ番号と出力番号から継続。',
        'b': '(b) 18ステップの出力例（新規ラン、t0 = 0）',
        'example': 'tt = 18 s、dt = 1 s。dt_disp = 2 s、dt_file = 4 s、dt_recrd = 1 s。\nst_file = 0、et_file = −1（全期間）。st_recrd = 5 s、et_recrd = 16 s。',
        'axis': '計算時刻 t [s]', 'disp': '画面・ログ\ndt_disp = 2 s',
        'file': '分布ファイル\ndt_file = 4 s', 'record': 'プローブ・測線\ndt_recrd = 1 s',
        'dt': 'dt = 1 s', 'window': '記録窓: 5〜16 s（両端を含む）',
        'initial_record': '開始時も記録', 'st': 'st_recrd = 5', 'et': 'et_recrd = 16',
        'file_note': '0001〜0004 は通常の連番。9998 は終了処理の固定番号で、次の連番ではない。',
        'schedule': '通常出力は「間隔の整数倍のステップ」かつ「窓の中」。st_* から間隔を数え直す方式ではない。',
        'fixed_title': '開始・終了の固定出力',
        'fixed': '0000: そのランの開始状態。\n9998: 実際に到達した最終ステップの状態。\nどちらも通常の出力間隔・時間窓とは別に出力。',
        'stats_title': '9999 は期間統計',
        'stats': '最大値などをラン内で集計し、終了処理で出力。\n9998 の瞬間値とは区別する。\n番号と時刻の対応は FILENUMBER.csv を参照。',
        'footer1': '出力間隔は max(nint(間隔/dt), 1) ステップへ丸める。図は dt の整数倍を指定した例。',
        'footer2': '文字列指定: tt_c = "24h"、dt_file_c = "10min"（両方書けば _c が優先。上の出力例とは別の指定例）。',
        'footer3': '計測・分布・統計の出力は各機能・出力フラグが有効な場合。t0 ≠ 0 の窓指定と再開の制約は本文を参照。',
    },
    'en': {
        'title': 'Simulation time, output intervals and time windows',
        'sub': 'Time settings in &list_sysparam. t0 and tt are positions on the same axis measured from t = 0.',
        'a': '(a) Distinguish time coordinates from the run duration',
        'origin': 't = 0 (time origin)', 'start': 't0 (start time)', 'end': 'tt (requested end time)',
        'duration': 'Requested duration = tt − t0',
        'formula': 't = t0 + dt × it     /     N = ceiling((tt − t0)/dt)     /     Normal end time = t0 + dt × N',
        'round': 'it is the step index. N rounds up, so the actual end time can exceed tt when the duration is not a multiple of dt.',
        'date': 'date0_c = "2019-10-11 09:00" anchors the calendar at t = 0.\nOnly calendar-dependent features use it; it does not anchor t0.',
        'restart': 'Restart (f_state_restore = 1): extend tt on the same axis.\nKeep t0 and dt; continue the saved step and output numbers.',
        'b': '(b) An 18-step output example (fresh run, t0 = 0)',
        'example': 'tt = 18 s, dt = 1 s. dt_disp = 2 s, dt_file = 4 s, dt_recrd = 1 s.\nst_file = 0, et_file = −1 (whole run). st_recrd = 5 s, et_recrd = 16 s.',
        'axis': 'Simulation time t [s]', 'disp': 'Screen / log\ndt_disp = 2 s',
        'file': 'Distributed files\ndt_file = 4 s', 'record': 'Probes / transects\ndt_recrd = 1 s',
        'dt': 'dt = 1 s', 'window': 'Record window: 5–16 s (inclusive)',
        'initial_record': 'Also record at start', 'st': 'st_recrd = 5', 'et': 'et_recrd = 16',
        'file_note': '0001–0004 are regular sequence numbers. 9998 is a fixed final-output slot, not the next sequence number.',
        'schedule': 'Regular output requires both a multiple of the interval in steps and a step inside the window. The interval is not restarted at st_*.',
        'fixed_title': 'Fixed outputs at start and finish',
        'fixed': '0000: the starting state of this run.\n9998: the state at the last step actually reached.\nBoth bypass the regular output interval and window.',
        'stats_title': '9999 holds period statistics',
        'stats': 'Accumulate maxima, etc. over this run; write at finalization.\nThese differ from the instantaneous state in 9998.\nSee FILENUMBER.csv for the number-to-time mapping.',
        'footer1': 'Output intervals round to max(nint(interval/dt), 1) steps. This example uses exact multiples of dt.',
        'footer2': 'String forms: tt_c = "24h", dt_file_c = "10min" (_c takes precedence; these are separate examples, not the settings above).',
        'footer3': 'Recording, fields and statistics require their features/output flags. See the text for windows with t0 ≠ 0 and restart restrictions.',
    },
}


def step_count(value, dt):
    """Positive time values: Fortran nint rounds a half away from zero."""
    return max(math.floor(value/dt + .5), 1)


def scheduled_steps(nt, dt, interval, start, end):
    n, lo, hi = step_count(interval,dt), step_count(start,dt), step_count(end,dt)
    return [it for it in range(1,nt+1) if lo <= it <= hi and it % n == 0]


def example():
    return dict(display=list(range(0,19,2)),
        files=scheduled_steps(N,1,4,0,18),
        records=scheduled_steps(N,1,1,5,16))


def xpos(it):
    return X0 + (X1-X0)*it/N


def marker(ax, x, y, color, style, gid, filled=True, size=6):
    line(ax, [(x,y)], color, marker=style, markersize=size,
         markerfacecolor=color if filled else 'white', markeredgewidth=1.3).set_gid(gid)


def build(lang):
    t=T[lang]
    fig=plt.figure(figsize=(CANVAS[0]/DPI,CANVAS[1]/DPI),dpi=DPI)
    ax=fig.add_axes([0,0,1,1]);ax.set_xlim(0,CANVAS[0]);ax.set_ylim(CANVAS[1],0);ax.axis('off')
    text(ax,48,35,t['title'],17,weight='bold');block(ax,48,93,t['sub'],1479,9.5)
    text(ax,48,149,t['a'],12,weight='bold')
    arrow(ax,[(300,234),(1430,234)],INK,1.5,size=11)
    for x,k in [(330,'origin'),(650,'start'),(1320,'end')]:
        text(ax,x,195,t[k],10,ha='center');marker(ax,x,234,INK,'o','axis-'+k)
    line(ax,[(650,270),(650,284),(1320,284),(1320,270)],MUTED,1)
    text(ax,985,296,t['duration'],10,ha='center')
    text(ax,48,346,t['formula'],10.4)
    block(ax,48,389,t['round'],1479,9.2)
    block(ax,48,440,t['date'],719,9,color=ORANGE)
    block(ax,807,440,t['restart'],720,9,color=GREEN)
    line(ax,[(48,518),(1527,518)],RULE,.9)
    text(ax,48,544,t['b'],12,weight='bold')
    block(ax,48,592,t['example'],1479,9.5)
    text(ax,48,700,t['axis'],10,va='center')
    arrow(ax,[(X0-15,700),(X1+70,700)],INK,1.4,size=11)
    for it in range(N+1):
        x=xpos(it);line(ax,[(x,694),(x,706)],MUTED,.9).set_gid(f'tick-{it}')
        if it in (0,4,8,12,16,18):text(ax,x,663,str(it),9.5,ha='center')
    xa,xb=xpos(4),xpos(5)
    arrow(ax,[(xa,744),(xb,744)],ORANGE,1.1,size=8)
    arrow(ax,[(xb,744),(xa,744)],ORANGE,1.1,size=8)
    text(ax,(xa+xb)/2,758,t['dt'],8.5,color=ORANGE,ha='center')
    for y,k in [(825,'disp'),(935,'file'),(1100,'record')]:
        text(ax,48,y-22,t[k],10,color=MUTED);line(ax,[(X0,y),(X1,y)],RULE,.9)
    e=example()
    for it in e['display']:
        line(ax,[(xpos(it),815),(xpos(it),835)],MUTED,1.5).set_gid(f'display-{it}')
    file_slots=[(0,'0000','s',False)]+[(it,f'{k:04d}','s',True) for k,it in enumerate(e['files'],1)]+[(18,'9998','D',True)]
    for it,label,shape,fill in file_slots:
        marker(ax,xpos(it),935,BLUE,shape,'file-'+label,fill)
        text(ax,xpos(it),962,label,9.5,color=BLUE,ha='center')
    block(ax,330,1005,t['file_note'],1175,8.7,color=BLUE)
    ax.add_patch(Rectangle((xpos(5),1076),xpos(16)-xpos(5),48,facecolor='#f9e5b4',edgecolor='none',zorder=0,gid='record-window'))
    text(ax,(xpos(5)+xpos(16))/2,1046,t['window'],9,color='#826016',ha='center')
    for it in e['records']:marker(ax,xpos(it),1100,GREEN,'o',f'record-{it}',size=4.5)
    marker(ax,X0,1100,GREEN,'o','record-initial',False,size=5)
    text(ax,X0,1132,t['initial_record'],8.5,color=GREEN,ha='center')
    text(ax,xpos(5),1132,t['st'],8.8,color='#826016',ha='center')
    text(ax,xpos(16),1132,t['et'],8.8,color='#826016',ha='center')
    block(ax,48,1184,t['schedule'],1479,9.2)
    for x,k,fill,color in [(48,'fixed','#edf4fc',BLUE),(807,'stats','#f0f5ed',GREEN)]:
        ax.add_patch(Rectangle((x,1237),720,157,facecolor=fill,edgecolor='none',gid=k+'-card'))
        text(ax,x+24,1257,t[k+'_title'],10.5,color=color,weight='bold')
        block(ax,x+24,1303,t[k],672,8.9)
    for i in range(1,4):block(ax,48,1420+(i-1)*34,t['footer'+str(i)],1479,8.5,color=MUTED)
    return fig


def draw(lang):
    if lang not in T:raise ValueError('lang must be ja or en')
    dest=Path(__file__).resolve().parents[1]/('time_axis'+('' if lang=='ja' else '_en'))
    with drawing_style():
        fig=build(lang);fig.savefig(dest.with_suffix('.png'),dpi=DPI)
        svg=StringIO();fig.savefig(svg,format='svg',metadata={'Date':None})
        dest.with_suffix('.svg').write_text(svg.getvalue(),encoding='utf-8',newline='\n')
        plt.close(fig)
    return str(dest.with_suffix('.png'))
