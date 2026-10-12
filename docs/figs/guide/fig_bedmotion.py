"""Prescribed bed motion: input routes, local update and raster windows.

Panel (a), including its graph, table, labels and annotations, is retained
at the ORIGINAL coordinates and pixel scale from commit 4002fd6. PNG and
SVG embed the protected PNG without resampling; panels (b)(c) are vectors.
See the guide for exact step-switch timing and the first-step application
of a one-row table. No solver or numerical graph is regenerated here.
Generate only this figure: python docs/figs/make_guide_figs.py bedmotion
"""
from io import BytesIO, StringIO
from pathlib import Path
import base64, hashlib
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyArrowPatch
from PIL import Image
from _schematic import drawing_style, text, block, line, arrow, INK, MUTED, RULE

CANVAS, DPI = (1575, 1575), 150
BLUE, ORANGE, GREEN, BROWN = '#287ca5', '#b56432', '#52744b', '#876342'
HISTORY_BOX = {'ja': (0,0,915,570), 'en': (0,0,945,570)}
HISTORY_SHA = {
 'ja': '3a9e0cc4a4b9084564e2e54cd2b385ea778e68b017e48525477969406f010de8',
 'en': 'daaf0608f9de69336be12ccabbe612e90386bac99f6adc9622d978763a289e28',
}
INPUT_BOXES = {'A': (975,60,495,155), 'B': (975,242,495,143),
               'C': (975,412,495,115), 'reader': (975,584,560,107)}
INPUT_PORTS = {'A': (1470,137.5), 'B': (1470,313.5), 'C': (1470,469.5)}
BED_Y, RISE, DEPTH, DATUM = 1230, 70, 170, 1340
COLUMNS = ((110, BED_Y), (480, BED_Y-RISE))
COL_WIDTH = 180
GRID = (970, 1020, 16, 10, 29)
WINDOW = (5, 2, 7, 5)  # i1, j1, ni, nj; the original illustrative window.
T = {
 'ja': {
  'b': '(b) 変位入力を作り、1つの表へ',
  'inputs': [
   ('A', 'A  断層パラメータから',
    '位置・走向・傾斜・すべり角・長さ・幅・\nすべり量・t_r・t_rise（複数セグメント可）\nutils/fault2disp が変位ラスタと表を作成。'),
   ('B', 'B  自分で用意した変位場から',
    '前処理で z と同じ格子・形式に揃える。\n各時刻の累積変位 d のラスタと表を作成。\n本体は空間的な再格子化を行わない。'),
   ('C', 'C  最終変位を1行で与える',
    '0.0  bm/disp_0010.txt\nA・Bの最終変位を使う入力方法。'),
  ],
  'reader': '&list_bedmotion: fn_bmlist',
  'readerbody': '表を読む: f_bminterp / bm_tscale',
  'choice': '用意した表を読む',
  'history_note': '(a)は1セルの累積変位 d の例。表の時刻は t0 からの相対値。\n階段補間の厳密な切替時刻と、1行入力の初回適用は本文を参照。',
  'first': 'C: 変位は最初の時間ステップの頭で適用。初期出力 0000 は変位前。',
  'c': '(c) 累積変位から増分を求め、対象セルの地盤高を更新',
  'formula': 'Δd = d(tₙ₊₁) − d_prev     →     z ← z + Δd,   e ← z + h',
  'eligible': '対象: x > 0 かつ sw = 0\n海域マスク外の水中セルも含む。',
  'section': '地盤と水面の変位  |  隆起 Δd > 0 の例',
  'before': '更新直前', 'after': '更新直後', 'datum': '基準高',
  'water': '水深 h は同じ',
  'bed_note': '地盤と水面は同じ Δd だけ動く。沈降では Δd < 0。\nこの局所更新は h・運動量・土層厚 sd を直接変えない。\nその後の流れの計算では、水深や流速が変化する。',
  'window_title': '窓付き入力  |  北西から列・行を数える',
  'grid_size': '全域: nx = 16, ny = 10',
  'col': '列 i → 東', 'row': '行 j → 南',
  'corner': '(i1, j1) = (5, 2)',
  'window': 'ni = 7, nj = 5',
  'outside': '窓外は d = 0',
  'window_range': '列 5…11、行 2…6 の35セルを格子に対応させる。',
  'window_line': '表示例: 0.0  bm/disp_0000.txt  5 2 7 5',
  'window_note': '4整数を省略すれば全域入力。窓の左上とセル境界を一致させる。\n各時刻の窓外はゼロ。適用ループは全窓を包む矩形内を走査する。',
  'footer': '本文の入力例とは別の配置模式図。窓 ni × nj のラスタも累積変位を持つ。海域マスク sw > 0 と無効セルは変位の対象外。',
 },
 'en': {
  'b': '(b) Prepare displacement and its table',
  'inputs': [
   ('A', 'A  From fault parameters',
    'Position, strike, dip, rake, length, width,\nslip, t_r, t_rise; multiple segments allowed.\nutils/fault2disp writes rasters and the table.'),
   ('B', 'B  From your own displacement fields',
    'Preprocess to the same grid and format as z.\nWrite cumulative d rasters and their table.\nThe solver does not regrid them spatially.'),
   ('C', 'C  A one-row table for the final field',
    '0.0  bm/disp_0010.txt\nA way to use the final field from A or B.'),
  ],
  'reader': '&list_bedmotion: fn_bmlist',
  'readerbody': 'Read table: f_bminterp / bm_tscale',
  'choice': 'Read the prepared table',
  'history_note': 'Panel (a) shows cumulative d at one cell. Table times are relative to t0.\nSee the text for exact step-switch timing and first application of a one-row table.',
  'first': 'C: apply at the head of the first time step. Initial output 0000 precedes bed motion.',
  'c': '(c) Convert cumulative displacement to an increment and update eligible cells',
  'formula': 'Δd = d(tₙ₊₁) − d_prev     →     z ← z + Δd,   e ← z + h',
  'eligible': 'Eligible: x > 0 and sw = 0\nIncludes submerged cells outside the sea mask.',
  'section': 'Bed and surface displacement  |  Uplift Δd > 0',
  'before': 'Before update', 'after': 'After update', 'datum': 'Datum',
  'water': 'Same depth h',
  'bed_note': 'Bed and surface move by the same Δd; subsidence has Δd < 0.\nThis local update does not directly change h, momentum or sd.\nThe subsequent flow calculation can change depth and velocity.',
  'window_title': 'Windowed input  |  Count from the NW corner',
  'grid_size': 'Full grid: nx = 16, ny = 10',
  'col': 'Column i → east', 'row': 'Row j → south',
  'corner': '(i1, j1) = (5, 2)',
  'window': 'ni = 7, nj = 5',
  'outside': 'Outside: d = 0',
  'window_range': '35 cells: columns 5…11 and rows 2…6.',
  'window_line': 'Illustration: 0.0  bm/disp_0000.txt  5 2 7 5',
  'window_note': 'Omit the four integers for a full-grid file. Align the window with cell edges.\nZero outside each snapshot window. Scan the rectangle enclosing all windows.',
  'footer': 'Illustrative placement, separate from the text’s input example. Window rasters also store cumulative d. Sea-mask and inactive cells are excluded.',
 },
}


def rect(ax, key, box, fill, edge=RULE, z=1):
    p=Rectangle(box[:2],*box[2:],fc=fill,ec=edge,lw=.8,zorder=z)
    ax.add_patch(p); p.set_gid(key); return p


def arr(ax,key,xy,color=ORANGE):
    p=arrow(ax,xy,color,lw=1.5,size=10);p.set_gid(key);return p


def dimension(ax,key,x,y0,y1,label,color):
    p=FancyArrowPatch((x,y0),(x,y1),arrowstyle='<->',mutation_scale=10,
                      color=color,lw=1.1,shrinkA=0,shrinkB=0,zorder=10)
    ax.add_patch(p);p.set_gid(key)
    text(ax,x+14,(y0+y1)/2,label,size=9,color=color,va='center')


def build(lang):
    t=T[lang]
    fig=plt.figure(figsize=(CANVAS[0]/DPI,CANVAS[1]/DPI),dpi=DPI)
    ax=fig.add_axes([0,0,1,1]);ax.set(xlim=(0,CANVAS[0]),ylim=(CANVAS[1],0));ax.axis('off')
    text(ax,975,12,t['b'],size=10,weight='bold')
    for key,head,body in t['inputs']:
        x,y,w,h=INPUT_BOXES[key]
        rect(ax,'input_'+key,(x,y,w,h),'#fbf2e9')
        text(ax,x+16,y+14,head,size=8.8,weight='bold',color=ORANGE)
        block(ax,x+16,y+52,body,w-32,size=8.1)
        px,py=INPUT_PORTS[key]
        line(ax,[(px,py),(1515,py)],ORANGE,1.5).set_gid('port_'+key)
    line(ax,[(1515,137.5),(1515,558),(1255,558)],ORANGE,1.5).set_gid('input_trunk')
    arr(ax,'read_table',[(1255,558),(1255,584)])
    text(ax,975,545,t['choice'],size=8.1,color=ORANGE)
    rect(ax,'reader',INPUT_BOXES['reader'],'#edf4f8')
    text(ax,995,602,t['reader'],size=9.4,weight='bold',color=BLUE)
    text(ax,995,648,t['readerbody'],size=8.5,color=BLUE)
    rect(ax,'history_note',(35,590,880,110),'#fafaf7')
    block(ax,52,610,t['history_note'],844,size=8.2,color=MUTED)
    text(ax,35,714,t['first'],size=8.2,color=ORANGE)
    text(ax,35,764,t['c'],size=10,weight='bold')
    arr(ax,'to_update',[(1255,691),(1255,810)],BLUE)
    rect(ax,'update',(35,810,1500,83),'#f3f7ed')
    text(ax,55,839,t['formula'],size=10,weight='bold',color=GREEN)
    text(ax,920,827,t['eligible'],size=8.4,color=GREEN)
    text(ax,35,923,t['section'],size=9.5,weight='bold')
    text(ax,840,923,t['window_title'],size=9.5,weight='bold')
    # The same depth and displacement define both surfaces and both bed levels.
    for k,(x,bed) in enumerate(COLUMNS):
        surface=bed-DEPTH
        rect(ax,f'ground_{k}',(x,bed,COL_WIDTH,DATUM-bed),'#ded2bd',BROWN)
        rect(ax,f'water_{k}',(x,surface,COL_WIDTH,DEPTH),'#deedf4',BLUE)
        line(ax,[(x,bed),(x+COL_WIDTH,bed)],BROWN,1.3).set_gid(f'bed_{k}')
        line(ax,[(x,surface),(x+COL_WIDTH,surface)],BLUE,1.5).set_gid(f'surface_{k}')
        text(ax,x+COL_WIDTH/2,bed-DEPTH/2,'h',size=10,color=BLUE,ha='center',va='center')
        text(ax,x+COL_WIDTH/2,(bed+DATUM)/2,'z',size=10,color=BROWN,ha='center',va='center')
        text(ax,x,surface-33,'e = z + h',size=9,color=BLUE)
        text(ax,x+COL_WIDTH/2,DATUM+24,t['before' if k==0 else 'after'],size=8.5,ha='center',color=MUTED)
    for yy,color in [(BED_Y,ORANGE),(BED_Y-RISE,ORANGE),(BED_Y-DEPTH,BLUE),(BED_Y-RISE-DEPTH,BLUE)]:
        line(ax,[(300,yy),(465,yy)],color,.8,ls='--').set_gid('level_'+str(yy))
    dimension(ax,'bed_rise',375,BED_Y,BED_Y-RISE,'Δd',ORANGE)
    dimension(ax,'surface_rise',375,BED_Y-DEPTH,BED_Y-RISE-DEPTH,'Δd',BLUE)
    dimension(ax,'water_depth',690,BED_Y-RISE,BED_Y-RISE-DEPTH,'h',BLUE)
    line(ax,[(100,DATUM),(705,DATUM)],MUTED,.8,ls='--').set_gid('datum')
    text(ax,720,DATUM-9,t['datum'],size=8,color=MUTED)
    text(ax,55,980,t['water'],size=8.5,color=BLUE)
    block(ax,35,1412,t['bed_note'],755,size=8.3)
    # A 7 x 5 window placed on the ORIGINAL 16 x 10 lattice, not between cells.
    gx,gy,nx,ny,d=GRID;i1,j1,ni,nj=WINDOW
    rect(ax,'full_grid',(gx,gy,nx*d,ny*d),'#fafaf7')
    wx,wy=gx+(i1-1)*d,gy+(j1-1)*d
    rect(ax,'window',(wx,wy,ni*d,nj*d),'#f6e4be',ORANGE,z=2)
    for i in range(nx+1):line(ax,[(gx+i*d,gy),(gx+i*d,gy+ny*d)],'#c9cbc7',.6,z=3)
    for j in range(ny+1):line(ax,[(gx,gy+j*d),(gx+nx*d,gy+j*d)],'#c9cbc7',.6,z=3)
    rect(ax,'window_outline',(wx,wy,ni*d,nj*d),'none',ORANGE,z=4)
    dot=Circle((wx,wy),4.5,fc=ORANGE,ec='white',lw=.7,zorder=12);ax.add_patch(dot);dot.set_gid('window_nw')
    text(ax,970,970,t['grid_size'],size=8.5,color=MUTED)
    arr(ax,'i_axis',[(970,1000),(1140,1000)],MUTED)
    text(ax,1160,990,t['col'],size=8,color=MUTED)
    arr(ax,'j_axis',[(947,1020),(947,1160)],MUTED)
    text(ax,910,1100,t['row'],size=8,color=MUTED,ha='center',va='center',rotation=90)
    # Labels live outside the grid; leaders meet its exact corner and centre.
    line(ax,[(wx,wy),(wx,1013),(1460,1013)],ORANGE,.8).set_gid('corner_leader')
    text(ax,1460,987,t['corner'],size=7.5,color=ORANGE,ha='right')
    text(ax,gx,1328,t['window'],size=8.2,color=BROWN)
    text(ax,gx+nx*d,1328,t['outside'],size=8,color=MUTED,ha='right')
    text(ax,840,1355,t['window_range'],size=8.5,color=ORANGE)
    text(ax,840,1394,t['window_line'],size=8.2)
    block(ax,840,1437,t['window_note'],695,size=8.1)
    text(ax,35,1532,t['footer'],size=7.8,color=MUTED)
    return fig


def history_asset(lang):
    suffix='' if lang=='ja' else '_en'
    p=Path(__file__).resolve().parents[1]/f'bedmotion_history_preserved{suffix}.png'
    data=p.read_bytes()
    if hashlib.sha256(data).hexdigest()!=HISTORY_SHA[lang]:raise ValueError('Protected panel (a) changed')
    return data


def draw(lang):
    if lang not in T:raise ValueError('lang must be ja or en')
    data=history_asset(lang);box=HISTORY_BOX[lang];size=(box[2]-box[0],box[3]-box[1])
    out=Path(__file__).resolve().parents[1]/('bedmotion_patterns'+('' if lang=='ja' else '_en')+'.png')
    with drawing_style():
        fig=build(lang)
        try:
            png,svg=BytesIO(),StringIO()
            fig.savefig(png,format='png',dpi=DPI)
            fig.savefig(svg,format='svg',metadata={'Date':None,'Description':
                'Prescribed bed motion: input routes, depth-preserving local update and NW-indexed raster window. Panel (a) is the original losslessly embedded graph and table; all remaining artwork is vector.'})
        finally:plt.close(fig)
    with Image.open(BytesIO(png.getvalue())) as im:combined=im.convert('RGBA')
    with Image.open(BytesIO(data)) as history:
        if history.size!=size:raise ValueError('Unexpected panel (a) size')
        combined.paste(history,box[:2])  # original location, exact pixels, no blending
    combined.save(out,dpi=(DPI,DPI))
    scale=72/DPI
    embed=(f'<image id="preserved-history" x="{box[0]*scale:g}" y="{box[1]*scale:g}" '
           f'width="{size[0]*scale:g}" height="{size[1]*scale:g}" preserveAspectRatio="none" '
           'xlink:href="data:image/png;base64,'+base64.b64encode(data).decode('ascii')+'"/>\n')
    xml=svg.getvalue().replace('</svg>',embed+'</svg>')
    out.with_suffix('.svg').write_text('\n'.join(s.rstrip() for s in xml.splitlines())+'\n',encoding='utf-8',newline='\n')
    return str(out)
