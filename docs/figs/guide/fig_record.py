"""Probes and transects: DDA selection, ENC cut, and coordinate segments.

The original probe, end cells, coordinate endpoints and grid sizes are kept.
The ENC cut follows the short-axis-positive faces of the DDA cell sequence
(m_record.f90: set_flux / flux_edges / side); it is not the STG quadrature
path through cell centres. Both panels use the same displayed cell size.
All coordinates illustrate placement, not a simulation or an input dataset.
Generate only this figure: python docs/figs/make_guide_figs.py record
"""
from io import StringIO
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle, Circle
from _schematic import drawing_style, text, block, line, arrow, INK, MUTED, RULE

CANVAS, DPI = (1575, 1470), 150
CELL = 70
GRID_A = (90, 265, 10, 8)
GRID_B = (1040, 265, 5, 4)
PROBE = (3, 2)
START, END = (3, 6), (8, 5)
P1, P2 = (0.6, 0.7), (3.6, 2.6)
SHORT1, SHORT2 = (3.3, 1.3), (3.9, 1.75)
BLUE, TEAL, ORANGE, GREEN = '#287ca5', '#538688', '#b56432', '#52744b'
T = {
 'ja': {
  'title':'流量測線とプローブ  |  指定する位置と、集計する流れ',
  'sub':'セル番号と実座標では集計方法が異なる。どちらも始点 R → 終点 L の右側へ抜ける流れを正とする。',
  'a':'(a) セル番号指定  |  ENCの集計境界',
  'amode':'flxytype = 0   /   pbxytype = 0',
  'axes_a':'i は西 → 東、j は北 → 南。ともに1スタート。',
  'b':'(b) 実座標指定  |  セル内の線分で積算',
  'bmode':'flxytype = 1   /   pbxytype = 1',
  'units':'例: 南西端が原点、Δx = Δy = 1 m',
  'x':'x: 東へ','y':'y: 北へ',
  'startend':'R: 右岸 (3, 6) → L: 左岸 (8, 5)',
  'probe':'P: プローブ (3, 2)。そのセルの時系列を記録。',
  'channel':'淡緑色: 河道 i = 5, 6。下流は南向き。',
  'specified':'破線: 指定した両端セルの中心を結ぶ線',
  'cut':'青実線: ENCがエッジ流量を集計する境界',
  'positive':'緑矢印: 流量の正側（流速の大きさは示さない）',
  'coords':'R = (0.6, 0.7) → L = (3.6, 2.6) m',
  'pieces':'色分けした各線分: 通過セル内の区間\n白丸: セル境界との交点',
  'short':'1セル内の短い測線も指定できる',
  'shortcoords':'(3.3, 1.3) → (3.9, 1.75) m\n向きと長さを座標で与える。',
  'shortcell':'x = 3…4 m, y = 1…2 m のセル',
  'notes':'指定法による違いと、共通の出力',
  'cards':[
   ('セル番号  |  階段状のセル列を選ぶ',
    '両端を含めて長手方向に1セルずつ選択。\n図では (3,6), (4,6), (5,6), (6,5), (7,5), (8,5)。\nENCはその短手正側の境界（図では南側）を\n横切る8方向のエッジ流量を符号付きで合計。\nSTGはセル値から踏面・段差の寄与を積算する。\n同一セルを両端に指定することはできない。'),
   ('実座標  |  指定された線分を測る',
    'ENC・STGともセルの流量ベクトルを使う。\n各セルで「法線方向成分 × セル内線分長」を加算。\n端点をセル外縁まで延ばさない。\n地理参照あり: その座標系の絶対座標。\n地理参照なし: 南西端原点、x東・y北のm座標。\n同一点を両端に指定することはできない。'),
  ],
  'output':'出力: probes/probe0001.csv（セルの q: m²/s） / fluxes/flux0001.csv（測線の Q: m³/s）',
  'footer':'本文にSTGの細い対角河道・事後計測の注意点を記載。図の座標は配置説明用。本文の入力例とは別。',
 },
 'en': {
  'title':'Transects and probes  |  Specified locations and measured flow',
  'sub':'Cell indices and real coordinates use different integrations. Both count flow to the right of start R → end L as positive.',
  'a':'(a) Cell indices  |  ENC integration boundary',
  'amode':'flxytype = 0   /   pbxytype = 0',
  'axes_a':'i increases east; j increases south. Both are 1-based.',
  'b':'(b) Real coordinates  |  In-cell segments',
  'bmode':'flxytype = 1   /   pbxytype = 1',
  'units':'Example: SW origin, Δx = Δy = 1 m',
  'x':'x: east','y':'y: north',
  'startend':'R: right bank (3, 6) → L: left bank (8, 5)',
  'probe':'P: probe (3, 2). Record the time series of that cell.',
  'channel':'Pale green: channel i = 5, 6. Downstream is south.',
  'specified':'Dashed: line joining the two specified cell centres',
  'cut':'Solid blue: boundary used for the ENC edge-flux sum',
  'positive':'Green arrows: positive side (not velocity magnitude)',
  'coords':'R = (0.6, 0.7) → L = (3.6, 2.6) m',
  'pieces':'Alternating colors: portions in successive cells\nWhite circles: intersections with cell boundaries',
  'short':'A short transect inside one cell is valid',
  'shortcoords':'(3.3, 1.3) → (3.9, 1.75) m\nCoordinates define orientation and length.',
  'shortcell':'Cell spanning x = 3…4 m, y = 1…2 m',
  'notes':'How integration differs, and the shared outputs',
  'cards':[
   ('Cell indices  |  Select a staircase of cells',
    'Select one cell per major-axis step, including both ends.\nHere: (3,6), (4,6), (5,6), (6,5), (7,5), (8,5).\nENC sums signed 8-neighbor edge flows across their\npositive short-axis boundary (south faces here).\nSTG integrates cell values over treads and risers.\nThe two end cells must differ.'),
   ('Real coordinates  |  Measure the specified segment',
    'Both ENC and STG use the cell flux vectors.\nSum normal flux × in-cell segment length over cells.\nDo not extend endpoints to the cell edges.\nGeoreferenced: absolute coordinates in that system.\nOtherwise: SW origin, x east / y north, in metres.\nThe two endpoints must differ.'),
  ],
  'output':'Output: probes/probe0001.csv (cell q: m²/s) / fluxes/flux0001.csv (transect Q: m³/s)',
  'footer':'See text for STG diagonal-channel and post-hoc limitations. Coordinates illustrate placement; input examples in the text are separate.',
 },
}


def dda_cells(start=START, end=END):
    """Nearest short-axis index; Fortran NINT rounds half away from zero."""
    d = np.asarray(end) - start
    major = int(abs(d[1]) > abs(d[0]))
    if not np.any(d):
        raise ValueError('Different end cells required')
    short = 1 - major
    cells = []
    for k in range(abs(d[major]) + 1):
        c = list(start)
        c[major] += int(np.sign(d[major])) * k
        v = k * d[short] / abs(d[major])
        c[short] += int(np.sign(v) * np.floor(abs(v) + .5))
        cells.append(tuple(c))
    return cells


def enc_cut():
    """South faces for this x-major example, in local raster-edge units."""
    cells = dda_cells()
    path = [(cells[0][0]-1, cells[0][1])]
    for n,(i,j) in enumerate(cells):
        path.append((i,j))
        if n+1 < len(cells) and cells[n+1][1] != j:
            path.append((i,cells[n+1][1]))
    return np.asarray(path,float)


def segment_parts(p=P1, q=P2):
    """Split the example at actual cell interfaces; endpoints stay exact."""
    p,q=np.asarray(p,float),np.asarray(q,float)
    ts=[0.,1.]
    for axis in range(2):
        if q[axis] != p[axis]:
            for v in range(int(np.floor(min(p[axis],q[axis])))+1,int(np.ceil(max(p[axis],q[axis])))):
                t=(v-p[axis])/(q[axis]-p[axis])
                if 0<t<1:ts.append(t)
    return p+np.asarray(sorted(set(ts)))[:,None]*(q-p)


def axy(i,j):
    return np.asarray([GRID_A[0]+(i-.5)*CELL,GRID_A[1]+(j-.5)*CELL])


def bxy(x,y):
    return np.asarray([GRID_B[0]+x*CELL,GRID_B[1]+(GRID_B[3]-y)*CELL])


def rect(ax,key,x,y,w,h,fill,edge=RULE,lw=.7,z=1):
    p=Rectangle((x,y),w,h,fc=fill,ec=edge,lw=lw,zorder=z)
    ax.add_patch(p);p.set_gid(key);return p


def dot(ax,key,xy,color,r=5,edge='white'):
    p=Circle(xy,r,fc=color,ec=edge,lw=1,zorder=12)
    ax.add_patch(p);p.set_gid(key);return p


def arr(ax,key,xy,color=GREEN):
    p=arrow(ax,xy,color,lw=1.5,size=10);p.set_gid(key);return p


def grid(ax,key,geo):
    x,y,nx,ny=geo
    for i in range(nx+1):line(ax,[(x+i*CELL,y),(x+i*CELL,y+ny*CELL)],RULE,.7,z=3).set_gid(f'{key}_col_{i}')
    for j in range(ny+1):line(ax,[(x,y+j*CELL),(x+nx*CELL,y+j*CELL)],RULE,.7,z=3).set_gid(f'{key}_row_{j}')


def build(lang):
    t=T[lang]
    fig=plt.figure(figsize=(CANVAS[0]/DPI,CANVAS[1]/DPI),dpi=DPI)
    ax=fig.add_axes([0,0,1,1]);ax.set(xlim=(0,CANVAS[0]),ylim=(CANVAS[1],0));ax.axis('off')
    text(ax,35,30,t['title'],size=13,weight='bold')
    text(ax,35,77,t['sub'],size=8.6,color=MUTED)
    for x,key,mode in [(35,'a','amode'),(855,'b','bmode')]:
        text(ax,x,126,t[key],size=10,weight='bold')
        text(ax,x,172,t[mode],size=9,color=BLUE)
    text(ax,90,210,t['axes_a'],size=8.2,color=MUTED)
    text(ax,1040,220,t['units'],size=8.1,color=MUTED)
    x,y,nx,ny=GRID_A
    rect(ax,'a_domain',x,y,nx*CELL,ny*CELL,'#fcfbf8',edge='none',z=0)
    rect(ax,'channel',x+4*CELL,y,2*CELL,ny*CELL,'#e5ede3',edge='none',z=1)
    for i,j in dda_cells():
        px,py=axy(i,j)-CELL/2
        rect(ax,f'dda_{i}_{j}',px,py,CELL,CELL,'#f5e5d1',edge='none',z=2)
    grid(ax,'a',GRID_A)
    for i in range(1,nx+1):text(ax,axy(i,1)[0],y-25,str(i),size=8,color=MUTED,ha='center')
    for j in range(1,ny+1):text(ax,x-20,axy(1,j)[1],str(j),size=8,color=MUTED,ha='right',va='center')
    p0,p1=axy(*START),axy(*END)
    line(ax,[p0,p1],ORANGE,1.4,ls='--',z=7).set_gid('specified_centres')
    line(ax,np.array([x,y])+enc_cut()*CELL,BLUE,2.2,z=8).set_gid('enc_cut')
    for letter,point in [('R',p0),('L',p1)]:
        dot(ax,f'endpoint_{letter}',point,ORANGE,r=6)
        text(ax,point[0],point[1]-25,letter,size=8.5,color=ORANGE,weight='bold',ha='center')
    point=axy(*PROBE);dot(ax,'probe',point,INK,r=6)
    text(ax,point[0],point[1]-25,'P',size=8.5,weight='bold',ha='center')
    # Flow direction and positive discharge are separate, non-overlapping arrows.
    arr(ax,'downstream',[(x+4.5*CELL,y+1.65*CELL),(x+4.5*CELL,y+2.7*CELL)])
    arr(ax,'a_positive',[(x+6*CELL,y+5*CELL),(x+6*CELL+14,y+6*CELL)])
    text(ax,90,852,t['startend'],size=9,color=ORANGE)
    text(ax,90,888,t['probe'],size=8.6)
    text(ax,90,924,t['channel'],size=8.6,color=GREEN)
    # Real-coordinate panel, same cell scale as the raster-index panel.
    x,y,nx,ny=GRID_B
    rect(ax,'b_domain',x,y,nx*CELL,ny*CELL,'#fcfbf8',edge='none',z=0)
    parts=segment_parts()
    for k,(p,q) in enumerate(zip(parts[:-1],parts[1:])):
        mid=(p+q)/2;ix,iy=np.floor(mid).astype(int)
        rect(ax,f'segment_cell_{k}',x+ix*CELL,y+(ny-iy-1)*CELL,CELL,CELL,'#e7eff2',edge='none',z=1)
    grid(ax,'b',GRID_B)
    for k,(p,q) in enumerate(zip(parts[:-1],parts[1:])):
        line(ax,[bxy(*p),bxy(*q)],BLUE if k%2==0 else TEAL,2.6,z=8).set_gid(f'segment_{k}')
    for k,p in enumerate(parts[1:-1]):dot(ax,f'crossing_{k}',bxy(*p),'white',r=3.5,edge=BLUE)
    for letter,p in [('R',P1),('L',P2)]:
        point=bxy(*p);dot(ax,f'b_endpoint_{letter}',point,ORANGE,r=5)
        text(ax,point[0]-15 if letter=='R' else point[0]+16,point[1]+10 if letter=='R' else point[1]-20,
             letter,size=8.5,color=ORANGE,ha='center',weight='bold')
    mid=bxy(*((np.asarray(P1)+P2)/2));d=np.asarray(P2)-P1
    normal=np.array([d[1],d[0]])/np.linalg.norm(d)
    arr(ax,'b_positive',[mid,mid+normal*64])
    arr(ax,'x_axis',[(x,y+ny*CELL+23),(x+125,y+ny*CELL+23)],MUTED)
    text(ax,x+142,y+ny*CELL+12,t['x'],size=8.5,color=MUTED)
    arr(ax,'y_axis',[(x-23,y+ny*CELL),(x-23,y+ny*CELL-125)],MUTED)
    text(ax,x-65,y+ny*CELL-85,t['y'],size=8.5,color=MUTED,rotation=90,ha='center',va='center')
    text(ax,855,608,t['coords'],size=9,color=ORANGE)
    text(ax,855,645,t['pieces'],size=8.6,color=BLUE)
    text(ax,855,733,t['short'],size=9,weight='bold')
    # An isolated copy of the original short-segment cell, at the same scale.
    sx,sy=890,786
    rect(ax,'short_cell',sx,sy,CELL,CELL,'#fcfbf8')
    sp=lambda p: np.array([sx+(p[0]-3)*CELL,sy+(2-p[1])*CELL])
    line(ax,[sp(SHORT1),sp(SHORT2)],ORANGE,2.1).set_gid('short_segment')
    dot(ax,'short_start',sp(SHORT1),ORANGE,r=4)
    dot(ax,'short_end',sp(SHORT2),ORANGE,r=4)
    text(ax,1000,786,t['shortcoords'],size=8.5,color=ORANGE)
    text(ax,855,888,t['shortcell'],size=8.4,color=MUTED)
    # One shared visual key keeps labels clear of the geometry.
    line(ax,[(35,978),(1540,978)],RULE,.8)
    for k,(label,color,ls) in enumerate([('specified',ORANGE,'--'),('cut',BLUE,'-')]):
        yy=1004+39*k
        line(ax,[(35,yy+10),(80,yy+10)],color,1.8,ls=ls)
        text(ax,100,yy,t[label],size=8.2,color=color)
    arr(ax,'positive_key',[(860,1014),(905,1014)])
    text(ax,925,1004,t['positive'],size=8.1,color=GREEN)
    text(ax,35,1100,t['notes'],size=10,weight='bold')
    for n,(head,body) in enumerate(t['cards']):
        cx=35+765*n
        rect(ax,f'card_{n}',cx,1145,740,223,'#fafaf7')
        text(ax,cx+18,1161,head,size=9.2,weight='bold',color=BLUE)
        block(ax,cx+18,1200,body,704,size=8.4)
    text(ax,35,1394,t['output'],size=8.8)
    text(ax,35,1435,t['footer'],size=8,color=MUTED)
    return fig


def draw(lang):
    if lang not in T:raise ValueError('lang must be ja or en')
    out=Path(__file__).resolve().parents[1]/('record_transect'+('' if lang=='ja' else '_en')+'.png')
    with drawing_style():
        fig=build(lang)
        try:
            fig.savefig(out,dpi=DPI)
            svg=StringIO()
            fig.savefig(svg,format='svg',metadata={'Date':None,'Description':
                'Probes and discharge transects: ENC cell-index edge cut, distinct from STG cell-value quadrature, and real-coordinate in-cell segments. Illustrative placement; not a computed result.'})
            out.with_suffix('.svg').write_text('\n'.join(s.rstrip() for s in svg.getvalue().splitlines())+'\n',encoding='utf-8',newline='\n')
        finally:plt.close(fig)
    return str(out)
