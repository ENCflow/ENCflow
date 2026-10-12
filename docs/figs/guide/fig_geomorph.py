"""Illustrative geomorphic processes and the states they change.

Not a simultaneous configuration or a computed terrain. Sediment branches
that cannot coexist are explicitly distinguished in the key. Surface, soil,
moving layer and water polygons share sampled boundaries; shoreline roots
are inserted into both the water fill and the free-surface line.

Generate only processes: python docs/figs/make_guide_figs.py geomorph
Run control is independent: python docs/figs/make_guide_figs.py geomorph_morfac
"""
from io import StringIO
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib.patches import Polygon, Rectangle, Circle
from _schematic import drawing_style, text, block, line, arrow, monotone_cubic, INK, MUTED, RULE

CANVAS, DPI = (1575, 1630), 150
SOIL, ROCK, WATER = '#dfc58e', '#d4d1c9', '#d7eaf5'
BLUE, SED, MOVING, GREEN = '#287ca5', '#ad5b29', '#da9760', '#52744b'
BASE = -0.40

T = {
 'ja': {
    'title':'地形変化過程  |  土砂の行き先と、変化する状態量',
    'sub':'fn_geomorph / &list_geomorph  •  過程の概念配置。位置・形・厚さは説明用で、計算結果ではない。',
    'rule1':'併用条件: f_wash は f_suspend が必須。f_suspend と f_debris は併用不可。',
    'rule2':'f_slide（1: 判定＋流動化 / 2: 判定のみ）と fn_dbinit は f_debris が必須。',
    'rule3':'土石流・動く底層は morfac = 1。すべての番号を同時に有効化する設定例ではない。',
    'rain':'地表到達降雨 P', 'out':'系外排出', 'hillslope':'斜面', 'channel':'河道', 'lake':'湖・海: 通常セル＋初期水位',
    'mixture':'混合体 h + hs', 'move':'hb', 'exchange':'E: 巻き上げ / D: 沈降',
    'soil':'土層 sd', 'rock':'基岩（上面 z − sd）', 'water':'水 h（浮遊砂は hs）',
    'bed':'地表・河床 z', 'mobile':'動く底層 hb（sd の内数）',
    'cards':[
       ('乾式斜面侵食','f_splash','乾燥セル h ≤ dd、河道外。\n土砂は hs へ入れず系外へ。\nz・sd が減る。'),
       ('湿潤斜面の侵食','f_wash → f_suspend','湿潤セル h > dd、河道外。\n雨滴・面状侵食で hs へ供給。\nz・sd が減る。'),
       ('斜面クリープ','f_creep / creep_d','標高 z を線形拡散で平滑化。\nsd は更新せず、sd = 0 でも作用。\n有限の土層輸送とは異なる近似。'),
       ('掃流砂','f_fluvial','流砂量の収支（Exner 式）で\nz・sd を共に更新。\n侵食量は可動土層で制限。'),
       ('浮遊砂','f_suspend','hs を水とともに移流。\nE・D で河床と交換し z・sd を更新。\n乾燥時は残る hs を河床へ。'),
       ('土石流・斜面崩壊','f_debris / f_slide / fn_dbinit','混合体 h + hs と河床の交換。\nf_slide = 1: Fs < 1 で流動化。\nf_dbstop = 1: 低速時の固定を追加。'),
       ('動く底層','f_bedslide / fn_bsinit','hb は z・sd の内側を移動。\n移送時は h を保ち、水面も上下。\n停止後も質量は z・sd に残る。'),
       ('基岩風化・土層生成','f_wthr','z を保ち、sd を増やす。\n土層底 z − sd が下がる。\n土層が厚いほど生成は遅い。'),
       ('隆起・沈降','f_uplift / uplift0','z を上下させ、sd は保つ。\n土層底も同じだけ上下する。\nuplift0 < 0 なら沈降。'),
    ],
    'foot1':'sd = 0 は、土層からの侵食・流動化を止める条件。全過程で z が固定される条件ではない。',
    'foot2':'水域でも通常セルなら土砂過程を計算する。海域マスク sw > 0 では地形更新を行わない。',
    'foot3':'図の1〜9は説明用の番号で、処理順ではない。併用条件・物性値・更新間隔は本文参照。',
 },
 'en': {
    'title':'Geomorphic processes  |  Sediment pathways and changing states',
    'sub':'fn_geomorph / &list_geomorph  •  Conceptual placement; illustrative shapes and thicknesses, not computed results.',
    'rule1':'Coupling: f_wash requires f_suspend. f_suspend and f_debris cannot be combined.',
    'rule2':'f_slide (1: judge + mobilize / 2: judge only) and fn_dbinit both require f_debris.',
    'rule3':'Debris flow and moving bed layer require morfac = 1. This is not an all-process configuration.',
    'rain':'Rain reaching the ground P', 'out':'Leaves system', 'hillslope':'Hillslope', 'channel':'Channel', 'lake':'Lake / sea: ordinary cells + initial level',
    'mixture':'Mixture h + hs', 'move':'hb', 'exchange':'E: entrainment / D: settling',
    'soil':'Soil depth sd', 'rock':'Bedrock (top: z − sd)', 'water':'Water h (suspended load: hs)',
    'bed':'Ground / bed z', 'mobile':'Moving layer hb (part of sd)',
    'cards':[
       ('Dry-slope erosion','f_splash','Dry cells h ≤ dd; outside channels.\nSediment leaves the system, not into hs.\nBoth z and sd decrease.'),
       ('Wet-slope erosion','f_wash → f_suspend','Wet cells h > dd; outside channels.\nRain / sheet erosion supplies hs.\nBoth z and sd decrease.'),
       ('Hillslope creep','f_creep / creep_d','Linear diffusion smooths z.\nsd is unchanged; acts even at sd = 0.\nNot transport of a finite soil layer.'),
       ('Bedload','f_fluvial','Sediment-flux balance (Exner)\nupdates z and sd together.\nErosion is limited by available soil.'),
       ('Suspended sediment','f_suspend','Advect hs with water; exchange E / D\nwith the bed updates z and sd.\nResidual hs deposits when cells dry.'),
       ('Debris flow / slope failure','f_debris / f_slide / fn_dbinit','Mixture h + hs exchanges with the bed.\nf_slide = 1: mobilize where Fs < 1.\nf_dbstop = 1 adds low-speed fixing.'),
       ('Moving bed layer','f_bedslide / fn_bsinit','hb moves within z and sd.\nTransport keeps h; the surface shifts.\nStopped mass remains in z and sd.'),
       ('Weathering / soil production','f_wthr','Keep z, increase sd.\nThe soil base z − sd lowers.\nProduction slows under thicker soil.'),
       ('Uplift / subsidence','f_uplift / uplift0','Shift z; keep sd unchanged.\nThe soil base shifts equally.\nuplift0 < 0 gives subsidence.'),
    ],
    'foot1':'sd = 0 stops erosion / mobilization of soil; it does not fix z for every process.',
    'foot2':'Sediment processes act in ordinary submerged cells. Sea-mask cells (sw > 0) receive no landform updates.',
    'foot3':'Numbers 1–9 identify explanations, not execution order. See text for coupling, parameters and update intervals.',
 },
}


def profile():
    x=np.unique(np.r_[np.linspace(0,10.4,1041),1.0,1.55])
    knots=[1.55,2.6,4.3,5.1,5.55,5.9,6.3,6.9,7.4,7.9,8.6,9.4,10.4]
    heights=[2.85,2.3,1.45,1.13,.76,.76,1.03,1.46,1.58,1.23,.45,.24,.22]
    z=np.empty_like(x)
    z[x<=1]=4
    cliff=(x>1)&(x<1.55)
    z[cliff]=4+(2.85-4)*(x[cliff]-1)/.55  # Deliberate cliff breaks.
    z[x>=1.55]=monotone_cubic(knots,heights,x[x>=1.55])
    sd=.30-.17*np.exp(-((x-1.38)/.27)**4)
    # Illustrative weathering lowers the soil base below the plateau, not z.
    sd+=.22*np.maximum(0,1-((x-.55)/.42)**2)**2
    hb=np.zeros_like(x); mask=(x>=7.4)&(x<=9.25)
    hb[mask]=.21*np.sin(np.pi*(x[mask]-7.4)/1.85)**.65
    return x,z,sd,hb


def xy(x,z):
    return np.column_stack((60+139*np.asarray(x),770-110*np.asarray(z)))


def layer(ax,key,x,bottom,top,face,edge='none',hatch=None,zorder=2):
    polygon=Polygon(np.vstack([xy(x,top),xy(x[::-1],bottom[::-1])]),closed=True,
        facecolor=face,edgecolor=edge,linewidth=.5,hatch=hatch,zorder=zorder)
    polygon.set_gid(key); ax.add_patch(polygon)
    return polygon


def wet_sections(x,z,surface):
    """Clip two piecewise-linear profiles at their exact shared intersections."""
    groups=[]; part=[]
    for a,b,za,zb,wa,wb in zip(x[:-1],x[1:],z[:-1],z[1:],surface[:-1],surface[1:]):
        da,db=wa-za,wb-zb
        if da<=0 and db<=0:
            if part: groups.append(np.array(part)); part=[]
            continue
        left,right=(a,za,wa),(b,zb,wb)
        if da<0 or db<0:
            f=-da/(db-da); c=a+f*(b-a); v=za+f*(zb-za)
            if da<0: left=(c,v,v)
            else: right=(c,v,v)
        if not part: part=[left]
        part.append(right)
        if db<0: groups.append(np.array(part)); part=[]
    if part: groups.append(np.array(part))
    return groups


def along(ax,key,x,z,color=SED,lw=1.7):
    a=arrow(ax,xy(x,z),color,lw=lw,size=10)
    a.set_gid(key)
    return a


def badge(ax,n,cx,cy,target=None):
    if target is not None:
        direction=np.asarray(target)-[cx,cy]
        start=np.asarray([cx,cy])+17*direction/np.linalg.norm(direction)
        line(ax,[start,target],MUTED,.8,z=9).set_gid(f'leader_{n}')
    p=Circle((cx,cy),17,facecolor='white',edgecolor=INK,linewidth=.9,zorder=15)
    p.set_gid(f'badge_{"plot" if target is not None else "key"}_{n}'); ax.add_patch(p)
    text(ax,cx,cy,str(n),size=9.3,weight='bold',ha='center',va='center')


def build(lang):
    t=T[lang]
    fig=plt.figure(figsize=(CANVAS[0]/DPI,CANVAS[1]/DPI),dpi=DPI)
    ax=fig.add_axes([0,0,1,1]); ax.set(xlim=(0,CANVAS[0]),ylim=(CANVAS[1],0)); ax.axis('off')
    text(ax,35,22,t['title'],size=12,weight='bold')
    text(ax,35,66,t['sub'],size=8.8,color=MUTED)
    ax.add_patch(Rectangle((35,108),1505,123,facecolor='#f4f3ee',edgecolor='none',zorder=0))
    for k in range(3): text(ax,55,124+k*34,t[f'rule{k+1}'],size=9)
    x,z,sd,hb=profile()
    layer(ax,'rock',x,np.full_like(x,BASE),z-sd,ROCK)
    layer(ax,'soil',x,z-sd,z,SOIL)
    line(ax,xy(x,z-sd),'#9d8a63',.65).set_gid('soil_base')
    # The orange bed layer is wholly inside the same soil profile.
    b=(x>=7.4)&(x<=9.25)
    layer(ax,'moving_bed',x[b],z[b]-hb[b],z[b],MOVING,edge=SED,hatch='///',zorder=3)
    surface=np.ones_like(x)
    surface+=.15*np.exp(-((x-8.85)/.36)**2)  # Qualitative free-surface disturbance.
    for k,p in enumerate(wet_sections(x,z,surface)):
        layer(ax,f'water_{k}',p[:,0],p[:,1],p[:,2],WATER,zorder=4)
        line(ax,xy(p[:,0],p[:,2]),BLUE,1.2,z=6).set_gid(f'water_surface_{k}')
    # Wet-slope sheet water and debris mixture are separate conceptual patches.
    for key,a,b,h,fill in [('sheet',2.4,3.55,.17,WATER),('mixture',3.8,5.15,.29,MOVING)]:
        m=(x>=a)&(x<=b); xx=x[m]; zz=z[m]
        depth=h*np.maximum(0,np.sin(np.pi*(xx-a)/(b-a)))**.65
        layer(ax,key,xx,zz,zz+depth,fill,zorder=4)
    line(ax,xy(x,z),INK,1.1,z=7).set_gid('ground_surface')
    # Rain and local sediment movement.
    for xr in np.arange(.12,.95,.17):
        zr=float(np.interp(xr,x,z))
        line(ax,xy([xr+.04,xr],[zr+.55,zr+.29]),BLUE,.9)
    for xr in np.arange(2.5,3.5,.22):
        zr=float(np.interp(xr,x,z))
        line(ax,xy([xr+.04,xr],[zr+.68,zr+.45]),BLUE,.9)
    text(ax,62,241,t['rain'],size=8.4,color=BLUE)
    along(ax,'dry_export',[1.23,1.65],[float(np.interp(1.23,x,z)),3.83],SED)
    text(ax,300,337,t['out'],size=8.2,color=SED)
    xx=np.linspace(2.61,3.28,20); zz=np.interp(xx,x,z)+.07
    along(ax,'sheet_sediment',xx,zz,SED,1.4)
    xx=np.linspace(1.75,2.16,20); zz=np.interp(xx,x,z)-.13
    along(ax,'creep_direction',xx,zz,GREEN,1.5)
    xx=np.linspace(4.03,4.9,30); zz=np.interp(xx,x,z)+.12
    along(ax,'debris_direction',xx,zz,SED)
    text(ax,795,555,t['mixture'],size=8.4,color=SED)
    xx=np.linspace(5.5,6.04,25); zz=np.interp(xx,x,z)+.04
    along(ax,'bedload_direction',xx,zz,SED,1.4)
    # E and D are exchanges at the lake bed; suspended particles lie in water.
    for xr in [9.2,9.4,9.7,10.1]:
        for height in [.46,.73,.88]:
            ax.add_patch(Circle(tuple(xy([xr],[height])[0]),2.2,facecolor=SED,edgecolor='none',zorder=8))
    along(ax,'entrainment',[9.55,9.55],[float(np.interp(9.55,x,z)),.92],SED,1.4)
    along(ax,'deposition',[9.95,9.95],[.92,float(np.interp(9.95,x,z))],SED,1.4)
    text(ax,1240,610,t['exchange'],size=8.3,color=SED)
    xx=np.linspace(7.75,8.9,35); zz=np.interp(xx,x,z)-np.interp(xx,x,hb)*.5
    along(ax,'bed_layer_direction',xx,zz,SED)
    text(ax,1156,712,t['move'],size=8.6,color=SED)
    # Weathering: old soil base is dashed, present base is deeper; z stays fixed.
    xx=np.linspace(.2,.9,25)
    line(ax,xy(xx,np.full_like(xx,3.7)),GREEN,1,ls='--',z=8).set_gid('weathering_old_base')
    along(ax,'weathering',[.55,.55],[3.7,float(np.interp(.55,x,z-sd))],GREEN,1.5)
    for xr in [2.8,4.5,6.8]: along(ax,f'uplift_{xr}',[xr,xr],[-.24,.18],GREEN,1.5)
    text(ax,530,310,t['hillslope'],size=9,color=MUTED)
    text(ax,807,615,t['channel'],size=8.8,color=BLUE)
    text(ax,1150,475,t['lake'],size=8.8,color=BLUE)
    # Badge positions are shared by both languages; long notes live below.
    tags=[(1,284,305,1.27,float(np.interp(1.27,x,z))),(2,473,407,2.9,2.2),(3,338,573,1.95,2.48),
          (4,858,746,5.75,.8),(5,1537,555,10.1,.73),(6,734,490,4.55,1.57),
          (7,1212,548,8.3,.57),(8,120,443,.55,3.48),(9,492,776,4.5,-.04)]
    for n,cx,cy,tx,tz in tags: badge(ax,n,cx,cy,tuple(xy([tx],[tz])[0]))
    # Legend uses the same material palette and surface stroke as the section.
    for lx,key,fill in [(40,'soil',SOIL),(410,'rock',ROCK),(840,'water',WATER)]:
        ax.add_patch(Rectangle((lx,845),28,17,facecolor=fill,edgecolor='none'))
        text(ax,lx+40,840,t[key],size=8.7)
    line(ax,[(40,895),(68,895)],INK,1.1)
    text(ax,80,882,t['bed'],size=8.7)
    ax.add_patch(Rectangle((410,889),28,17,facecolor=MOVING,edgecolor=SED,hatch='///',linewidth=.5))
    text(ax,450,882,t['mobile'],size=8.7)
    # Nine keys preserve a landscape overview without crossing text leaders.
    for k,(title,flag,body) in enumerate(t['cards']):
        left=35+(k%3)*510; top=938+(k//3)*181
        line(ax,[(left,top),(left+475,top)],RULE,.8)
        badge(ax,k+1,left+18,top+32)
        text(ax,left+47,top+18,title,size=9.5,weight='bold')
        text(ax,left+47,top+58,flag,size=8.5,color=SED if k in [0,1,3,4,5,6] else GREEN)
        block(ax,left+47,top+91,body,425,size=8.6)
    for k in range(3): text(ax,35,1500+36*k,t[f'foot{k+1}'],size=8.6,color=MUTED)
    return fig


def fig_processes(lang):
    if lang not in T: raise ValueError('lang must be ja or en')
    out=Path(__file__).resolve().parents[1]/('geomorph_processes'+('' if lang=='ja' else '_en')+'.png')
    with drawing_style():
        fig=build(lang)
        try:
            fig.savefig(out,dpi=DPI)
            svg=StringIO()
            fig.savefig(svg,format='svg',metadata={'Date':None,
                'Description':'Conceptual ENCflow geomorphic processes, not a computed terrain or an all-process configuration. Water, soil and moving-layer boundaries share coordinates. The key distinguishes state changes and incompatible sediment branches.'})
            out.with_suffix('.svg').write_text('\n'.join(s.rstrip() for s in svg.getvalue().splitlines())+'\n',encoding='utf-8',newline='\n')
        finally: plt.close(fig)
    return str(out)


def fig_morfac(lang):
    """Retain the explicit legacy entry point without regenerating it in draw."""
    from fig_geomorph_morfac import draw as draw_morfac
    return draw_morfac(lang)


def draw(lang):
    return fig_processes(lang)
