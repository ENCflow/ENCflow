"""Boundary families: outer faces versus prescribed cell sets.

Illustrative 16 by 11 raster, with the original highlighted cell indices.
The west inflow replaces exactly three wall faces. All faces, cell fills,
index labels and arrows derive from the same grid geometry. Not an ENC
flux-stencil diagram or a computed result. Generate only this figure:
python docs/figs/make_guide_figs.py boundary
"""
from io import StringIO
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle
from _schematic import drawing_style, text, block, line, arrow, INK, MUTED, RULE

CANVAS, DPI = (1575, 1550), 150
NX, NY = 16, 11
X0, Y0, CELL = 355, 285, 45
SOURCE=[(5,4),(5,5)]
STAGE=[(12,9),(13,9),(13,10)]
INFLOW=[(1,6),(1,7),(1,8)]
GREEN, BLUE, PURPLE, ORANGE = '#52744b','#287ca5','#80579a','#b56432'
T={
 'ja':{
    'title':'境界条件  |  外縁の面と、セルに与える条件',
    'sub':'fn_boundary の4グループ  •  ENC格子での配置例（16列 × 11行）。添字は1スタート。',
    'a':'(a) 適用する位置と、指定する量',
    'i':'i: 列（西 → 東）','j':'j: 行（北 → 南）',
    'north':'北辺 j = 1  |  f_bc_n = 0（壁）',
    'west':'西辺 i = 1\nf_bc_w = 0\n壁（D の区間を除く）',
    'east':'東辺 i = nx\nf_bc_e = 2\n長波放射\n流出・流入の両方を許す',
    'south':'南辺 j = ny  |  f_bc_s = 1（自由流出のみ）',
    'inflow':'D  区間流入 Q(t) ≥ 0\n(1, 6), (1, 7), (1, 8)\n橙色の法線面を上書き',
    'source':'B  内部ソース\n(5, 4), (5, 5)\nセル集合への Q(t)',
    'stage':'C  水位規定\n(12, 9), (13, 9), (13, 10)\nセル集合に η(t) を規定',
    'gridnote':'B・C・D の色と記号はそれぞれ1つのセル集合を示す。矢印は流量の大きさや計算結果を表さない。',
    'b':'(b) 4つの設定グループ',
    'cards':[
        ('A  辺境界', '&list_bound_edge',
         '0: 壁（既定） / 1: 自由流出（流入なし）\n2: 長波放射（基準からの水位偏差に応答）\n未指定の辺は壁。区間流入は指定面だけを上書き。'),
        ('B  内部ソース', '&list_bound_source',
         'Q > 0: 湧き出し / Q < 0: 吸い込み\n集合の総流量を等分配。流速・向きは直接指定しない。\n吸い込みは各セルにある水量まで。'),
        ('C  水位規定', '&list_bound_stage',
         'stage_eta: 固定値 / stage_val: 時系列\n水深 h = max(η − z, 0)。周囲との流量は計算する。\nη ≤ z のセルは排水口として使える。\n区間流入と同じセルには指定しない。'),
        ('D  区間流入', '&list_bound_inflow',
         '外縁法線面へ総流量 Q(t) を内向きに規定。\ninflow_dist: 0 開口幅 / 1 水深 / 2 通水能 h^(5/3)\n1・2 は均等配分と混合する。乾燥セルへの流入もあり得る。'),
    ],
    'footer1':'source・stage・inflow はグループを省略すれば追加なし。外縁は辺境界を省略しても既定の壁。',
    'footer2':'辺境界は格子の外枠に接する有効な非海域セルに作用する。ポンプ・カルバート等は別の fn_structure。',
    'footer3':'図中のセル番号は配置説明用で、本文の入力例とは別。ファイル書式・放射基準水位・配分の詳細は本文参照。',
 },
 'en':{
    'title':'Boundary conditions  |  Outer faces and conditions imposed on cells',
    'sub':'Four groups in fn_boundary  •  Illustrative ENC layout (16 columns × 11 rows), with 1-based indices.',
    'a':'(a) Where each condition acts and what it prescribes',
    'i':'i: columns (west → east)','j':'j: rows (north → south)',
    'north':'North j = 1  |  f_bc_n = 0 (wall)',
    'west':'West i = 1\nf_bc_w = 0\nWall, except segment D',
    'east':'East i = nx\nf_bc_e = 2\nLong-wave radiation\nAllows outflow and inflow',
    'south':'South j = ny  |  f_bc_s = 1 (outflow only)',
    'inflow':'D  Segment Q(t) ≥ 0\n(1, 6), (1, 7), (1, 8)\nOverride orange normal faces',
    'source':'B  Internal source\n(5, 4), (5, 5)\nQ(t) for the cell set',
    'stage':'C  Prescribed level\n(12, 9), (13, 9), (13, 10)\nImpose η(t) on the cell set',
    'gridnote':'Each color / letter B, C or D identifies one cell set. Arrows do not show discharge magnitudes or computed results.',
    'b':'(b) The four configuration groups',
    'cards':[
        ('A  Edge boundaries', '&list_bound_edge',
         '0: wall (default) / 1: free outflow (no inflow)\n2: long-wave radiation (response to level deviation)\nUnspecified edges stay walls; D overrides selected faces.'),
        ('B  Internal sources', '&list_bound_source',
         'Q > 0: injection / Q < 0: extraction\nShare total Q equally; no prescribed speed or direction.\nExtraction is capped by the water available in each cell.'),
        ('C  Prescribed water level', '&list_bound_stage',
         'stage_eta: fixed / stage_val: time series\nDepth h = max(η − z, 0); surrounding fluxes are computed.\nA cell with η ≤ z can act as a drain.\nDo not overlap these cells with segment inflow.'),
        ('D  Segment inflow', '&list_bound_inflow',
         'Prescribe total Q(t) inward through outer normal faces.\ninflow_dist: 0 width / 1 depth / 2 conveyance h^(5/3)\n1 / 2 blend with uniform flow; dry cells can receive inflow.'),
    ],
    'footer1':'Omitting source / stage / inflow adds no such condition. Omitting edge settings keeps the default walls.',
    'footer2':'Edge rules act on valid non-sea cells touching the grid frame. Pumps, culverts, etc. belong to the separate fn_structure.',
    'footer3':'Cell indices illustrate this layout; the input examples in the text are separate. See text for formats, radiation references and weights.',
 },
}


def cell_xy(i,j):
    return X0+(i-1)*CELL,Y0+(j-1)*CELL


def rect(ax,key,x,y,w,h,fill,edge=RULE,lw=.8,z=1):
    p=Rectangle((x,y),w,h,fc=fill,ec=edge,lw=lw,zorder=z)
    ax.add_patch(p);p.set_gid(key)
    return p


def connector(ax,key,points,color,ls='-'):
    p=arrow(ax,points,color,lw=1.35,ls=ls,size=10);p.set_gid(key)
    return p


def build(lang):
    t=T[lang]
    fig=plt.figure(figsize=(CANVAS[0]/DPI,CANVAS[1]/DPI),dpi=DPI)
    ax=fig.add_axes([0,0,1,1]);ax.set(xlim=(0,CANVAS[0]),ylim=(CANVAS[1],0));ax.axis('off')
    text(ax,35,30,t['title'],size=13,weight='bold')
    text(ax,35,77,t['sub'],size=8.8,color=MUTED)
    text(ax,35,126,t['a'],size=10,weight='bold')
    connector(ax,'i_direction',[(X0,185),(X0+180,185)],MUTED)
    text(ax,X0+205,175,t['i'],size=8.6,color=MUTED)
    connector(ax,'j_direction',[(301,Y0),(301,Y0+140)],MUTED)
    text(ax,245,355,t['j'],size=8.5,color=MUTED,rotation=90,ha='center',va='center')
    text(ax,X0+NX*CELL/2,225,t['north'],size=9,ha='center')
    rect(ax,'domain',X0,Y0,NX*CELL,NY*CELL,'#fafaf7',edge='none',z=0)
    for i in range(1,NX):line(ax,[(X0+i*CELL,Y0),(X0+i*CELL,Y0+NY*CELL)],RULE,.6,z=1).set_gid(f'grid_col_{i}')
    for j in range(1,NY):line(ax,[(X0,Y0+j*CELL),(X0+NX*CELL,Y0+j*CELL)],RULE,.6,z=1).set_gid(f'grid_row_{j}')
    for i in range(1,NX+1):text(ax,X0+(i-.5)*CELL,Y0-22,str(i),size=7.7,color=MUTED,ha='center')
    for j in range(1,NY+1):text(ax,X0-71,Y0+(j-.5)*CELL,str(j),size=7.7,color=MUTED,ha='center',va='center')
    for key,cells,color,fill in [('source',SOURCE,PURPLE,'#eee4f3'),('stage',STAGE,BLUE,'#d9ecf6'),('inflow',INFLOW,ORANGE,'#f7e3d3')]:
        letter={'source':'B','stage':'C','inflow':'D'}[key]
        for i,j in cells:
            x,y=cell_xy(i,j)
            rect(ax,f'{key}_{i}_{j}',x,y,CELL,CELL,fill,color,lw=.85,z=2)
            text(ax,x+CELL/2,y+CELL/2,letter,size=9.4,color=color,weight='bold',ha='center',va='center')
    # The wall really has a gap exactly on j=6..8; no wall under inflow arrows.
    line(ax,[(X0,Y0),(X0+NX*CELL,Y0)],INK,2.2).set_gid('north_wall')
    low=cell_xy(*INFLOW[0])[1];high=cell_xy(*INFLOW[-1])[1]+CELL
    for key,ya,yb in [('west_wall_n',Y0,low),('west_wall_s',high,Y0+NY*CELL)]:
        line(ax,[(X0,ya),(X0,yb)],INK,2.2).set_gid(key)
    line(ax,[(X0,low),(X0,high)],ORANGE,2.2).set_gid('inflow_faces')
    for i,j in INFLOW:
        y=cell_xy(i,j)[1]+CELL/2
        connector(ax,f'inflow_arrow_{j}',[(306,y),(X0+10,y)],ORANGE)
    line(ax,[(X0,Y0+NY*CELL),(X0+NX*CELL,Y0+NY*CELL)],GREEN,1.7).set_gid('south_outflow')
    for i in [2,5,8,11,14]:
        x=X0+(i-.5)*CELL
        connector(ax,f'outflow_arrow_{i}',[(x,Y0+NY*CELL-13),(x,Y0+NY*CELL+34)],GREEN)
    east=X0+NX*CELL
    line(ax,[(east,Y0),(east,Y0+NY*CELL)],BLUE,1.7).set_gid('east_radiation')
    for j in [2,4,6,8,10]:
        y=Y0+(j-.5)*CELL
        connector(ax,f'radiation_out_{j}',[(east-17,y-7),(east+43,y-7)],BLUE)
        connector(ax,f'radiation_in_{j}',[(east+43,y+7),(east-17,y+7)],BLUE,ls='--')
    text(ax,35,335,t['west'],size=8.8)
    text(ax,35,538,t['inflow'],size=8.1,color=ORANGE)
    text(ax,1170,322,t['east'],size=9,color=BLUE)
    text(ax,1170,535,t['source'],size=8.7,color=PURPLE)
    text(ax,1170,674,t['stage'],size=8.3,color=BLUE)
    text(ax,X0+NX*CELL/2,838,t['south'],size=9,color=GREEN,ha='center')
    text(ax,35,894,t['gridnote'],size=8.6,color=MUTED)
    line(ax,[(35,937),(1540,937)],RULE,.8)
    text(ax,35,959,t['b'],size=10,weight='bold')
    for i,(x,y,color) in enumerate([(35,1004,INK),(800,1004,PURPLE),(35,1211,BLUE),(800,1211,ORANGE)]):
        rect(ax,f'card_{i}',x,y,740,187,'#fafaf7')
        title,group,body=t['cards'][i]
        text(ax,x+19,y+15,title,size=9.5,weight='bold',color=color)
        text(ax,x+19,y+48,group,size=8.8,color=color)
        block(ax,x+19,y+86,body,702,size=8.5)
    for k in range(1,4):text(ax,35,1432+33*(k-1),t[f'footer{k}'],size=8.1,color=MUTED)
    return fig


def draw(lang):
    if lang not in T:raise ValueError('lang must be ja or en')
    out=Path(__file__).resolve().parents[1]/('boundary_families'+('' if lang=='ja' else '_en')+'.png')
    with drawing_style():
        fig=build(lang)
        try:
            fig.savefig(out,dpi=DPI)
            svg=StringIO()
            fig.savefig(svg,format='svg',metadata={'Date':None,
                'Description':'Illustrative ENC boundary families: default outer-edge types, selected inflow faces, internal volume sources and prescribed-level cells. Not a numerical result or flux stencil.'})
            out.with_suffix('.svg').write_text('\n'.join(s.rstrip() for s in svg.getvalue().splitlines())+'\n',encoding='utf-8',newline='\n')
        finally:plt.close(fig)
    return str(out)
