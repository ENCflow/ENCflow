"""Three raster wood ledgers, their thresholds and volume accounting.

Illustrative section, not particle trajectories or a computed result. The
ground, water fill and shoreline use one sampled bed with inserted shore
vertices. The dashed reference bank is a line only, never a second fill.
Generate only this figure: python docs/figs/make_guide_figs.py driftwood
"""
from io import StringIO
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib.patches import Polygon, Rectangle, Circle, Ellipse
from _schematic import drawing_style, text, block, line, arrow, monotone_cubic, wet_profile, INK, MUTED, RULE

CANVAS, DPI = (1575, 1600), 150
GREEN, BLUE, BROWN = '#52744b', '#287ca5', '#876342'
SOIL, WATER, WOOD = '#e4d7bd', '#d7eaf5', '#a58a63'
LEVEL, BASE = 1.6, -.30

T = {
 'ja': {
    'title':'流木  |  3つの台帳と、移動・停止の条件',
    'sub':'fn_driftwood / &list_driftwood  •  材積をセルごとのラスタ場で扱う。樹木・丸太の位置や大きさは説明用。',
    'a':'(a) 立木 → 流動 → 堆積',
    'stock':'立木ストック wst', 'mobile':'流動流木 hd', 'deposit':'堆積流木 wd',
    'stocknote':'不動 / dw_stock0 または fn_dwstock',
    'mobilenote':'水・混合体の流れで移流', 'depositnote':'不動 / 再流動は任意',
    'recruit':'① / ② 流木化', 'stop':'③ 停止', 'refloat':'④ 再流動（既定: 無効）',
    'water':'水面', 'flow':'流れ V', 'oldbed':'基準地盤 zref（破線）', 'newbed':'現在の地盤 z',
    'lowering':'地盤低下 zref − z', 'dry':'乾燥部',
    'raster':'丸太の個別軌跡・姿勢や閉塞は解かない。堆積材積 wd を地盤標高 z に加える処理も行わない。',
    'b':'(b) 台帳を移す条件  |  H = h + max(hs, 0)、V = セル流速、hf = 喫水',
    'cards':[
        ('① 水理的流失  |  wst → hd', 'H > dw_hrec  かつ  V > dw_vrec', 'レート dw_wrec。残る wst の量まで流木化。'),
        ('② 侵食連行  |  wst → hd', 'zref − z > dw_droot', '残る wst を全量流木化。水深・流速の条件なし。\n侵食増分の累積和ではなく、基準からの標高差。'),
        ('③ 停止・堆積  |  hd → wd', 'h ≤ dd: 全量 / それ以外は次の条件', 'H < hf  または  V < dw_vstop → レート dw_wstop\n各レート移送量は、その時点の hd の量まで。'),
        ('④ 再流動  |  wd → hd', 'H > dw_rfloat × hf  かつ  V > dw_vfloat', 'dw_wfloat > 0 のとき、レート dw_wfloat で移送。\n残る wd の量まで。既定 dw_wfloat = 0 は無効。'),
    ],
    'order':'番号は経路の識別用。局所処理の順序: ② → ① → ③ → ④ → ダム捕捉 → 最大値更新。',
    'c':'(c) 喫水 hf の定義', 'draft':'hf', 'diameter':'D',
    'drafttext':'横向き円柱の断面で浮力平衡。\nD = dw_dlog、sg = dw_sglog\n水没断面積 / 全断面積 = sg\n図は sg = 0.5、hf = D / 2 の例。',
    'draftnote':'代表材の喫水を求める図で、\n個別丸太の姿勢計算ではない。',
    'd':'(d) 出力と材積収支',
    'output':'Hd = hd、Wd = wd（m³/m²、実効面積当たり）\nWd9999 = セルごとの期間最大 maxₜ(hd + wd)\n累積通過量ではなく、その時点の材積の最大値。',
    'volume':'材積 Q = Σ A [wst + f (hd + wd)]\nA = dx × dy、f = gv × wfrac（幅指定なしは wfrac = 1）',
    'budget':'閉領域・ダム捕捉なしなら Q を保存。\n流出・ダム捕捉は別途計上。CSV の貯留量は換算済み。',
    'footer':'判定の H と乾燥判定の h を区別する。土砂がなければ H = h。閾値・併用条件・再開時の統計は本文参照。',
 },
 'en': {
    'title':'Driftwood  |  Three ledgers and conditions for motion and deposition',
    'sub':'fn_driftwood / &list_driftwood  •  Cell-based raster wood volume; tree and log positions and sizes are illustrative.',
    'a':'(a) Standing → moving → deposited wood',
    'stock':'Standing stock wst', 'mobile':'Moving wood hd', 'deposit':'Deposited wood wd',
    'stocknote':'Immobile / dw_stock0 or fn_dwstock',
    'mobilenote':'Advected with water / mixture', 'depositnote':'Immobile / optional refloat',
    'recruit':'① / ② Recruit', 'stop':'③ Stop', 'refloat':'④ Refloat (default: off)',
    'water':'Water surface', 'flow':'Flow V', 'oldbed':'Reference bed zref (dashed)', 'newbed':'Current bed z',
    'lowering':'Bed lowering zref − z', 'dry':'Dry ground',
    'raster':'Individual log paths, orientation and jamming are not resolved. Deposited wood wd is not added to bed elevation z.',
    'b':'(b) Transfer conditions  |  H = h + max(hs, 0), V = cell speed, hf = draft',
    'cards':[
        ('① Hydraulic recruitment  |  wst → hd', 'H > dw_hrec  and  V > dw_vrec', 'Rate dw_wrec, capped by the remaining stock wst.'),
        ('② Erosion entrainment  |  wst → hd', 'zref − z > dw_droot', 'Recruit all remaining wst; no depth or speed test.\nNet lowering from the reference, not summed erosion.'),
        ('③ Stopping / deposition  |  hd → wd', 'h ≤ dd: all hd / otherwise use the test below', 'H < hf  or  V < dw_vstop → rate dw_wstop\nEach rate transfer is capped by the available hd.'),
        ('④ Refloating  |  wd → hd', 'H > dw_rfloat × hf  and  V > dw_vfloat', 'If dw_wfloat > 0, transfer at rate dw_wfloat,\nup to the available wd. Default dw_wfloat = 0: off.'),
    ],
    'order':'Numbers identify paths. Local order: ② → ① → ③ → ④ → dam capture → maximum update.',
    'c':'(c) Definition of draft hf', 'draft':'hf', 'diameter':'D',
    'drafttext':'Buoyancy balance of a horizontal cylinder.\nD = dw_dlog, sg = dw_sglog\nSubmerged area / total area = sg\nShown: sg = 0.5, giving hf = D / 2.',
    'draftnote':'A representative draft calculation,\nnot the orientation of individual logs.',
    'd':'(d) Outputs and volume accounting',
    'output':'Hd = hd, Wd = wd (m³/m² of effective area)\nWd9999 = per-cell period maximum maxₜ(hd + wd)\nPeak instantaneous volume, not cumulative passage.',
    'volume':'Volume Q = Σ A [wst + f (hd + wd)]\nA = dx × dy, f = gv × wfrac (wfrac = 1 without widths)',
    'budget':'Q is conserved in a closed domain without dam capture.\nAccount for outflow / capture separately; CSV stocks use m³.',
    'footer':'H is used for thresholds; h is used for the dry-cell test. Without sediment H = h. See text for coupling and restart statistics.',
 },
}


def profile():
    x=np.linspace(0,10.4,1041)
    # Deliberate bank break; smooth channel bed and depositional shore.
    z=np.empty_like(x)
    z[x<=1.85]=1.18
    cut=(x>1.85)&(x<2.75)
    z[cut]=1.18+(0.22-1.18)*(x[cut]-1.85)/.9
    z[x>=2.75]=monotone_cubic([2.75,3.6,4.9,6.3,7.5,8.6,9.5,10.4],
                            [.22,.18,.20,.55,1.08,1.6,1.9,2.0],x[x>=2.75])
    wet=wet_profile(x,z,LEVEL)[0]
    # Insert shoreline in the ground too, so boundaries use identical vertices.
    x=np.unique(np.r_[x,wet[:,0]])
    return x,np.interp(x,np.linspace(0,10.4,1041),z)


def xy(x,z):
    return np.column_stack((55+141*np.asarray(x),605-78*np.asarray(z)))


def rect(ax,key,x,y,w,h,face,edge=RULE):
    p=Rectangle((x,y),w,h,fc=face,ec=edge,lw=.8,zorder=0)
    ax.add_patch(p);p.set_gid(key)
    return p


def connector(ax,key,points,color):
    p=arrow(ax,points,color,lw=1.5,size=10);p.set_gid(key)
    return p


def build(lang):
    t=T[lang]
    fig=plt.figure(figsize=(CANVAS[0]/DPI,CANVAS[1]/DPI),dpi=DPI)
    ax=fig.add_axes([0,0,1,1]);ax.set(xlim=(0,CANVAS[0]),ylim=(CANVAS[1],0));ax.axis('off')
    text(ax,35,30,t['title'],size=13,weight='bold')
    text(ax,35,76,t['sub'],size=8.6,color=MUTED)
    text(ax,35,126,t['a'],size=10,weight='bold')
    for key,x,color,fill in [('stock',35,GREEN,'#eef4e9'),('mobile',620,BLUE,'#edf5fa'),('deposit',1215,BROWN,'#f5f0e8')]:
        rect(ax,'ledger_'+key,x,179,325,77,fill)
        text(ax,x+162.5,191,t[key],size=10.2,color=color,weight='bold',ha='center')
        text(ax,x+162.5,228,t[key+'note'],size=8.1,color=MUTED,ha='center')
    connector(ax,'recruit',[(360,212),(620,212)],GREEN)
    text(ax,490,180,t['recruit'],size=8.8,color=GREEN,ha='center')
    connector(ax,'stop',[(945,212),(1215,212)],BROWN)
    text(ax,1080,180,t['stop'],size=8.8,color=BROWN,ha='center')
    connector(ax,'refloat',[(1320,256),(1320,292),(840,292),(840,256)],GREEN)
    text(ax,1080,304,t['refloat'],size=8.6,color=GREEN,ha='center')

    x,z=profile();bed=xy(x,z)
    ground=Polygon(np.vstack([bed,xy([x[-1],x[0]],[BASE,BASE])]),fc=SOIL,ec='none',zorder=1)
    ground.set_gid('ground');ax.add_patch(ground)
    for i,wet in enumerate(wet_profile(x,z,LEVEL)):
        vertices=np.vstack([xy(wet[:,0],wet[:,1]),xy([wet[-1,0],wet[0,0]],[LEVEL,LEVEL])])
        p=Polygon(vertices,fc=WATER,ec='none',zorder=2);p.set_gid(f'water_{i}');ax.add_patch(p)
        line(ax,xy([wet[0,0],wet[-1,0]],[LEVEL,LEVEL]),BLUE,1.2,z=3).set_gid(f'surface_{i}')
    line(ax,bed,INK,1.15,z=4).set_gid('bed')
    oldx=np.array([1.85,2.6,3.2]);oldz=np.array([1.18,1.18,.195])
    line(ax,xy(oldx,oldz),MUTED,.95,ls='--',z=5).set_gid('reference_bank')
    for i,xx in enumerate([.38,.92,1.46]):
        px,py=xy([xx],[1.18])[0]
        line(ax,[(px,py),(px,py-88)],BROWN,2.1,z=6)
        for cy,r in [(py-98,24),(py-119,19),(py-83,22)]:
            ax.add_patch(Circle((px,cy),r,fc='#89aa75',ec='none',zorder=7))
    for i,xx in enumerate([4.1,5.1,6.1]):
        px,py=xy([xx],[LEVEL])[0]
        p=Ellipse((px,py),59,14,fc=WOOD,ec=BROWN,lw=.9,zorder=7);p.set_gid(f'moving_log_{i}');ax.add_patch(p)
    for i,xx in enumerate([8.15,8.78,9.6]):
        zz=np.interp(xx,x,z);px,py=xy([xx],[zz])[0]
        dz=np.interp(xx+.01,x,z)-np.interp(xx-.01,x,z)
        angle=np.degrees(np.arctan2(-78*dz,141*.02))
        p=Ellipse((px,py-8),61,14,angle=angle,fc=WOOD,ec=BROWN,lw=.9,zorder=7)
        p.set_gid(f'deposited_log_{i}');ax.add_patch(p)
    text(ax,525,449,t['water'],size=8,color=BLUE)
    connector(ax,'flow',[(650,544),(875,544)],BLUE)
    text(ax,762,557,t['flow'],size=8.7,color=BLUE,ha='center')
    text(ax,387,358,t['oldbed'],size=8.4,color=MUTED)
    line(ax,[(463,393),(445,448),(414,506)],MUTED,.8)
    # Net lowering measured vertically at one x, between the two bed profiles.
    xx=2.55;yold=xy([xx],[1.18])[0,1];ynew=xy([xx],[np.interp(xx,x,z)])[0,1];px=xy([xx],[0])[0,0]
    line(ax,[(px,yold),(px,ynew)],BROWN,.9)
    for yy in [yold,ynew]:line(ax,[(px-5,yy),(px+5,yy)],BROWN,.9)
    text(ax,330,598,t['lowering'],size=8.1,color=BROWN)
    text(ax,990,598,t['newbed'],size=8.4,color=MUTED)
    text(ax,1350,402,t['dry'],size=8.3,color=MUTED)
    text(ax,35,654,t['raster'],size=8.5,color=MUTED)
    line(ax,[(35,698),(1540,698)],RULE,.8)

    text(ax,35,722,t['b'],size=10,weight='bold')
    for i,(cx,cy,color) in enumerate([(35,766,GREEN),(35,950,GREEN),(800,766,BROWN),(800,950,GREEN)]):
        rect(ax,f'condition_{i+1}',cx,cy,740,164,'#fafaf7')
        title,condition,note=t['cards'][i]
        text(ax,cx+19,cy+15,title,size=9.4,weight='bold',color=color)
        text(ax,cx+19,cy+55,condition,size=8.8)
        block(ax,cx+19,cy+94,note,702,size=8.5,color=MUTED)
    text(ax,35,1131,t['order'],size=8.5,color=MUTED)
    line(ax,[(35,1170),(1540,1170)],RULE,.8)

    text(ax,35,1194,t['c'],size=10,weight='bold')
    rect(ax,'draft_water',45,1334,245,73,WATER,edge='none')
    circle=Circle((145,1334),53,fc=WOOD,ec=BROWN,lw=1,zorder=3);circle.set_gid('draft_circle');ax.add_patch(circle)
    line(ax,[(45,1334),(92,1334)],BLUE,1.1)
    line(ax,[(198,1334),(290,1334)],BLUE,1.1)
    # D and hf dimension ticks share the actual circle extrema / water level.
    for key,xx,ya,yb in [('diameter',63,1281,1387),('draft',247,1334,1387)]:
        line(ax,[(xx,ya),(xx,yb)],BROWN,.9).set_gid('dimension_'+key)
        for yy in [ya,yb]:line(ax,[(xx-5,yy),(xx+5,yy)],BROWN,.9)
        text(ax,xx+12 if key=='draft' else 39,(ya+yb)/2,t[key],size=8.8,va='center',ha='left' if key=='draft' else 'right',color=BROWN)
    text(ax,327,1258,t['drafttext'],size=8.8)
    text(ax,327,1401,t['draftnote'],size=8.4,color=MUTED)
    text(ax,800,1194,t['d'],size=10,weight='bold')
    text(ax,800,1244,t['output'],size=8.7)
    text(ax,800,1348,t['volume'],size=8.6)
    text(ax,800,1421,t['budget'],size=8.4,color=MUTED)
    line(ax,[(35,1510),(1540,1510)],RULE,.8)
    block(ax,35,1534,t['footer'],1505,size=8.5,color=MUTED)
    return fig


def draw(lang):
    if lang not in T:raise ValueError('lang must be ja or en')
    out=Path(__file__).resolve().parents[1]/('driftwood_ledgers'+('' if lang=='ja' else '_en')+'.png')
    with drawing_style():
        fig=build(lang)
        try:
            fig.savefig(out,dpi=DPI)
            svg=StringIO()
            fig.savefig(svg,format='svg',metadata={'Date':None,
                'Description':'Three raster driftwood ledgers, recruitment and stopping thresholds, cylinder draft, area conversion and output interpretation. Illustrative, not a simulation.'})
            out.with_suffix('.svg').write_text('\n'.join(s.rstrip() for s in svg.getvalue().splitlines())+'\n',encoding='utf-8',newline='\n')
        finally:plt.close(fig)
    return str(out)
