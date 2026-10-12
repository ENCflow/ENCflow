"""Soil Water Index: fixed three-tank parameters and nonnegative outlets.

The illustrative storages are drawing values, not model input or solver output.
All tank levels and outlet heights share one mm-to-pixel scale. Only outlets
with positive discharge have arrows. Constants match src/m_swi.f90 and JMA.
"""
from io import StringIO
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle
from _schematic import drawing_style, text, block, line, arrow, INK, MUTED, RULE

CANVAS, DPI = (1575, 1700), 150
WATER, OUTFLOW, FILL = '#2a78d6', '#c45a26', '#dbeafa'
X, WIDTH, SCALE, HEIGHT = 245, 390, 3.0, 80.0
BOTTOMS = (470, 840, 1210)
STORAGES = (40.0, 30.0, 10.0)
OUTLETS = ((0,60.0,.15,'L2'), (0,15.0,.1,'L1'),
           (1,15.0,.05,'L3'), (2,15.0,.01,'L4'))
BETAS = (.12,.05,.01)
T = {
 'ja': {
    'title':'土壌雨量指数  |  直列3段タンクの貯留と流出',
    'sub':'fn_swi  •  石原・小葉竹モデルの固定定数（気象庁標準）  •  SWI = S1 + S2 + S3 [mm]',
    'a':'(a) 説明用の貯留例: S1 = 40、S2 = 30、S3 = 10 mm → SWI = 80 mm',
    'rain':'地上雨量 → 第1タンク',
    'rain_note':'fn_precip。定率遮断を併用した場合は遮断後の雨量。',
    'tanks':['第1タンク','第2タンク','第3タンク'],
    'lateral':'側方流出（タンク系外へ）',
    'active':'この貯留例では {value:g} mm/h',
    'inactive':'この貯留例では 0 mm/h（孔高以下）',
    'percolation':'底面浸透',
    'next':['第2タンクへ','第3タンクへ','タンク系外へ'],
    'zero_title':'水位が孔高以下なら、側方流出はゼロ',
    'zero_body':'各孔の流出 = α × max(S − L, 0)\n橙の矢印: 流出あり。灰色の孔: 流出なし。',
    'units':'S・孔高 L: mm  /  α・β: 1/h  /  流出・浸透: mm/h',
    'scale':'3タンク共通の高さ縮尺。タンクの間隔・幅・矢印の長さは模式的。',
    'b':'(b) 初期値と計算条件',
    'init':'swi0 = (S1, S2, S3) [mm]（既定: すべて0）\n初期値は3段別に指定。合計SWIだけでは配分は決まらない。',
    'contract':'dt ≤ 600 s。タンク定数は固定。\n各陸セルで独立に計算し、物理場へ流出・浸透を渡さない。\n併用設定は定率遮断 f_icmodel=1 のみ。',
    'c':'(c) 出力と再開',
    'output':'Swi0001…: SWIの分布 [mm]\nSwi9999: 計算区間の最大SWI [mm]\nSwit9999: 最大の発生時刻 [min]',
    'restart':'swi.dat: 3タンクの貯留状態を保存・復元。\n最大値とその時刻の統計は引き継がない。',
    'footer':'模式図・説明用の瞬間値（計算結果ではない）。SWIの期間最大値だけでは、CL線による警戒判定はできない。',
 },
 'en': {
    'title':'Soil Water Index  |  Storage and discharge in three serial tanks',
    'sub':'fn_swi  •  Fixed Ishihara–Kobatake parameters (JMA standard)  •  SWI = S1 + S2 + S3 [mm]',
    'a':'(a) Illustrative storages: S1 = 40, S2 = 30, S3 = 10 mm → SWI = 80 mm',
    'rain':'Ground rainfall → tank 1',
    'rain_note':'fn_precip; after interception if fixed-rate interception is enabled.',
    'tanks':['Tank 1','Tank 2','Tank 3'],
    'lateral':'Lateral discharge (leaves the tank system)',
    'active':'For these storages: {value:g} mm/h',
    'inactive':'For these storages: 0 mm/h (at/below the outlet)',
    'percolation':'Bottom percolation',
    'next':['To tank 2','To tank 3','Leaves the tank system'],
    'zero_title':'At or below an outlet, lateral discharge is zero',
    'zero_body':'Discharge per outlet = α × max(S − L, 0)\nOrange arrow: flowing. Grey outlet: no discharge.',
    'units':'S and outlet L: mm  /  α and β: 1/h  /  discharge and percolation: mm/h',
    'scale':'One vertical scale for all tanks; spacing, widths and arrow lengths are schematic.',
    'b':'(b) Initial values and calculation settings',
    'init':'swi0 = (S1, S2, S3) [mm] (default: all zero)\nSpecify all three storages; their sum alone cannot determine them.',
    'contract':'dt ≤ 600 s; tank parameters are fixed.\nIndependent land cells; no discharge is fed to physical states.\nOnly fixed-rate interception f_icmodel=1 may be combined.',
    'c':'(c) Output and restart',
    'output':'Swi0001…: SWI maps [mm]\nSwi9999: maximum SWI for the run segment [mm]\nSwit9999: time of that maximum [min]',
    'restart':'swi.dat saves/restores the three tank storages.\nMaximum-value and timing statistics are not carried over.',
    'footer':'Schematic snapshot, not solver output. The period maximum SWI alone cannot be used for a CL-line warning assessment.',
 },
}


def level_y(tank, mm):
    return BOTTOMS[tank] - SCALE * mm


def tank(ax, k, lang):
    bottom = BOTTOMS[k]
    top, water_y = level_y(k,HEIGHT), level_y(k,STORAGES[k])
    p=Rectangle((X,water_y),WIDTH,bottom-water_y,facecolor=FILL,edgecolor='none',zorder=2)
    p.set_gid(f'water_{k}'); ax.add_patch(p)
    line(ax,[(X,water_y),(X+WIDTH,water_y)],WATER,1.25).set_gid(f'waterline_{k}')
    line(ax,[(X,top),(X,bottom),(430-8,bottom)],INK,1.55)
    line(ax,[(430+8,bottom),(X+WIDTH,bottom)],INK,1.55)
    holes=sorted(level_y(k,l) for j,l,*_ in OUTLETS if j==k)
    start=top
    for y in holes:
        line(ax,[(X+WIDTH,start),(X+WIDTH,y-6)],INK,1.55)
        start=y+6
    line(ax,[(X+WIDTH,start),(X+WIDTH,bottom)],INK,1.55)
    text(ax,X+18,top+15,T[lang]['tanks'][k],size=10.8,weight='bold')
    text(ax,X+18,water_y-35,f'S{k+1} = {STORAGES[k]:g} mm',size=10,color=WATER)
    text(ax,X-20,bottom,'0',size=8.2,color=MUTED,ha='right',va='center')


def build(lang):
    t=T[lang]
    fig=plt.figure(figsize=(CANVAS[0]/DPI,CANVAS[1]/DPI),dpi=DPI)
    ax=fig.add_axes([0,0,1,1]); ax.set(xlim=(0,CANVAS[0]),ylim=(CANVAS[1],0)); ax.axis('off')
    text(ax,30,20,t['title'],size=12,weight='bold')
    text(ax,30,65,t['sub'],size=8.6,color=MUTED)
    text(ax,30,105,t['a'],size=9.6,weight='bold')
    text(ax,245,151,t['rain'],size=9.8,color=WATER)
    text(ax,700,152,t['rain_note'],size=8.4,color=MUTED)
    arrow(ax,[(430,188),(430,221)],WATER,size=11)
    text(ax,850,209,t['lateral'],size=10,weight='bold',color=OUTFLOW)
    for k in range(3):
        tank(ax,k,lang)
    # Bracket refers to storage, not to physical soil-layer thickness.
    line(ax,[(170,230),(150,230),(150,1210),(170,1210)],INK,1.1)
    text(ax,92,720,'SWI = S1 + S2 + S3',size=10.8,rotation=90,ha='center',va='center')
    for k,l,a,name in OUTLETS:
        y=level_y(k,l)
        q=a*max(STORAGES[k]-l,0.0)
        col=OUTFLOW if q>0 else MUTED
        # An actual gap in the side wall, with a short outlet tube.
        for dy in [-6,6]:
            line(ax,[(X+WIDTH,y+dy),(700,y+dy)],col,1.15)
        if q>0:
            arrow(ax,[(X+WIDTH,y),(812,y)],OUTFLOW,size=11).set_gid(f'outflow_{name}')
        text(ax,655,y-39,f'{name} = {l:g} mm',size=8.3,color=col)
        text(ax,850,y-18,f'{a:g} × max(S{k+1} − {l:g}, 0)',size=11,color=col)
        text(ax,850,y+21,t['active'].format(value=q) if q>0 else t['inactive'],size=8.8,color=col)
    for k,b in enumerate(BETAS):
        bottom=BOTTOMS[k]
        end=level_y(k+1,HEIGHT)-9 if k<2 else 1300
        arrow(ax,[(430,bottom),(430,end)],WATER,size=11).set_gid(f'percolation_{k}')
        text(ax,485,bottom+28,f'b{k+1} = {b:g} × S{k+1} = {b*STORAGES[k]:g} mm/h',size=10,color=WATER)
        text(ax,485,bottom+64,t['percolation']+'  |  '+t['next'][k],size=8.6,color=WATER)
    p=Rectangle((830,565),710,145,facecolor='#f4f3f0',edgecolor='none',zorder=1)
    ax.add_patch(p)
    text(ax,850,582,t['zero_title'],size=9.5,weight='bold')
    block(ax,850,625,t['zero_body'],670,size=8.7)
    text(ax,245,1320,t['scale'],size=8,color=MUTED)
    text(ax,30,1360,t['units'],size=8.5,color=MUTED)
    line(ax,[(30,1395),(1540,1395)],RULE,.8)
    text(ax,30,1416,t['b'],size=10,weight='bold')
    text(ax,815,1416,t['c'],size=10,weight='bold')
    block(ax,30,1460,t['init'],725,size=8.6)
    block(ax,30,1543,t['contract'],725,size=8.4)
    block(ax,815,1460,t['output'],725,size=8.6)
    block(ax,815,1570,t['restart'],725,size=8.4)
    line(ax,[(30,1650),(1540,1650)],RULE,.8)
    text(ax,30,1669,t['footer'],size=7.9,color=MUTED)
    return fig


def draw(lang):
    if lang not in T: raise ValueError('lang must be ja or en')
    out=Path(__file__).resolve().parents[1]/('swi_tanks'+('' if lang=='ja' else '_en')+'.png')
    with drawing_style():
        fig=build(lang)
        try:
            fig.savefig(out,dpi=DPI)
            svg=StringIO()
            fig.savefig(svg,format='svg',metadata={'Date':None,'Description':'ENCflow Soil Water Index; schematic storage example with common vertical scale, fixed parameters and nonnegative outlet discharge.'})
            out.with_suffix('.svg').write_text('\n'.join(x.rstrip() for x in svg.getvalue().splitlines())+'\n',encoding='utf-8',newline='\n')
        finally:
            plt.close(fig)
    return str(out)
