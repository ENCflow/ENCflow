"""Co-registered geographic input layers, not vertical strata or solver output.

All nine panels share one illustrative 10 x 8 raster and one marked cell P.
Cell fills, grid lines and outlines use the same coordinate transform. The
seawall panel depicts land-side crest-holder cells (including diagonal
neighbours), with channel cells left open; it does not thicken the terrain.
Generate only this figure: python docs/figs/make_guide_figs.py geoinfo
"""
from io import StringIO
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle
from _schematic import drawing_style, text, block, line, INK, MUTED, RULE

CANVAS, DPI = (1575, 1790), 150
NX, NY, CELL = 10, 8, 20
MARK = (6, 4)  # Zero-based; label P corresponds to one-based cell (7, 5).
ALL = {(i,j) for i in range(NX) for j in range(NY)}
SEA = {(i,j) for i,j in ALL if i < 2 + (j >= 4)}
CHANNEL = {(2,1),(3,1),(3,2),(4,2),(5,2),(5,3),(6,3),(6,4),(7,4),(8,4),(9,4)}
OUTSIDE = {(8,7),(9,7),(9,6)}
BUILDINGS = {(7,2),(8,2),(7,3),(8,3),(8,5),(8,6)}
PONDS = {(4,5),(5,5),(7,0)}
NEIGHBOURS = tuple((di,dj) for di in (-1,0,1) for dj in (-1,0,1) if (di,dj)!=(0,0))
COAST = {c for c in ALL-SEA-OUTSIDE if any((c[0]+di,c[1]+dj) in SEA for di,dj in NEIGHBOURS)}
CRESTS = COAST-CHANNEL
KEYS = ('z','n','mask','sw','rw','gv','rs','sd','wall')
WHITE, SEA_C, RIVER_C, WALL_C = '#ffffff', '#a9d3ed', '#4d9ccf', '#cd6634'
SOIL = ('#eee5d3','#d9c8a6','#baa37d','#9c815f')
GREEN, GOLD, BUILD_C = '#cfe0bb', '#ecc869', '#969a9b'

T = {
 'ja': {
    'title':'地理情報レイヤー  |  ひとつの格子に、異なる属性を与える',
    'sub':'&list_geoinfo  •  同じ範囲を並べた入力分布の模式図。上下の地層や計算結果を表すものではない。',
    'grid_title':'共通の格子',
    'grid':'nx・ny と dx・dy または lx・ly で定義。epsg は座標系（既定 0: 不明）。',
    'alignment':'セル数・位置・解像度・座標系を統一。P は左上から列7・行5（全パネル共通）。',
    'z':('地盤高 z','f_ztype: 0 → z0 / 1 → fn_z\nmag_z: 固定値・分布の両方に乗じる',
         '未指定でも z0 = 0 m を使用。', [('低い',SOIL[0]),('高い',SOIL[-1])]),
    'n':('粗度（Manning の n）','f_rntype: 0 → rn0 / 1 → fn_rn\n値を直接入力（土地利用からの変換は前処理）',
         '未指定でも rn0 = 0.015 を使用。', [('小さい',GREEN),('大きい',GOLD)]),
    'mask':('領域マスク','f_masktype: 0 → 全域 / 1 → fn_mask\n2 → 陸域 + 隣接する海域1セル幅',
         '0のセルは物理計算から除外。配列の記憶領域までゼロになるわけではない。', [('1: 領域内',WHITE),('0: 対象外','#d6d8d8')]),
    'sw':('海域マスク sw','fn_sw: 1 → 海域セル\n水位境界として扱う海域（潮位など）',
         'このセルでは流れを解かない。波を伝播させる海は通常セルで扱う。', [('1: 海域',SEA_C),('0: 通常セル',WHITE)]),
    'rw':('河道マスク rw','fn_rw: 1 → 河道セル\ndepth_rw / fn_depth_rw: 掘り込み\nrn0_rw > 0: 河道粗度を上書き',
         '掘り込みと粗度の上書きは独立。幅・断面・河川堤防は fn_channel。', [('1: 河道',RIVER_C),('0: 非河道',WHITE)]),
    'gv':('家屋群の空隙率・寸法','fn_gv: 空隙率（建蔽されない割合）\nfn_bb: 家屋の平均寸法 [m]',
         'セル平均の貯留空間と抗力を表す。建物1棟ずつの輪郭ではない。', [('家屋群のあるセル',BUILD_C),('家屋群なし',WHITE)]),
    'rs':('ため池の貯留容量','fn_rscap: 限界貯留高 [m]\n正値のセルがため池',
         '地表水とは別枠の貯留 hrs。未指定の容量は0。', [('容量 > 0',RIVER_C),('容量 = 0',WHITE)]),
    'sd':('土層厚 sd','f_sdtype: 0 → sd0 / 1 → fn_sd\n地下水・地形変化の各過程で使用',
         'sy0 は地下水の比湧水量。土層を要する過程の条件に従って入力する。', [('土層あり',SOIL[1]),('土層厚 = 0',WHITE)]),
    'wall':('海岸堤防の天端・海側','fn_seaside: 海側判定（sw > 0 も海側）\nfn_seawall / seawall0: 陸側セルの天端\nf_seawall_datum / f_seawall_mode',
         '斜めの隣接も対象。河道セルは開口。壁面の仕組みと設定値は本文参照。', [('海側',SEA_C),('天端を持つ陸側',WALL_C),('河口の開口',RIVER_C)]),
    'defaults':'固定値・既定値と、分布ファイルを使い分ける',
    'default_note':'基本場は未指定でも既定値で初期化する。追加の場は利用過程や入力設定に応じて扱う。',
    'mask_note':'領域マスクは計算対象を選ぶ設定、海域マスクはセルの役割を指定する設定。両者は別のもの。',
    'footer':'10 × 8セルの説明用配置。色は各パネルの凡例に対応し、パネル間で共通の物理量・数値尺度を表さない。',
 },
 'en': {
    'title':'Geographic layers  |  Different attributes on one shared grid',
    'sub':'&list_geoinfo  •  Schematic input maps of the same area; not vertical strata or solver output.',
    'grid_title':'Shared grid',
    'grid':'Define nx, ny and dx, dy or lx, ly. epsg identifies the CRS (default 0: unknown).',
    'alignment':'Match cell counts, location, resolution and CRS. P: column 7, row 5 from the top left (all panels).',
    'z':('Ground elevation z','f_ztype: 0 → z0 / 1 → fn_z\nmag_z scales both fixed and file values.',
         'Default: z0 = 0 m, even without a file.', [('Lower',SOIL[0]),('Higher',SOIL[-1])]),
    'n':('Roughness (Manning n)','f_rntype: 0 → rn0 / 1 → fn_rn\nSupply values directly; map land use beforehand.',
         'Default: rn0 = 0.015, even without a file.', [('Lower',GREEN),('Higher',GOLD)]),
    'mask':('Domain mask','f_masktype: 0 → all / 1 → fn_mask\n2 → land + one adjacent sea-cell strip',
         'Cells with 0 are excluded from physics; their array storage is not eliminated.', [('1: in domain',WHITE),('0: excluded','#d6d8d8')]),
    'sw':('Sea mask sw','fn_sw: 1 → sea cell\nSea treated as a water-level boundary (e.g. tide)',
         'Flow is not solved in these cells. Use ordinary cells for wave propagation at sea.', [('1: sea',SEA_C),('0: ordinary cell',WHITE)]),
    'rw':('Channel mask rw','fn_rw: 1 → channel cell\ndepth_rw / fn_depth_rw: incision\nrn0_rw > 0: override channel roughness',
         'Incision and roughness override are independent. Width, section, levees: fn_channel.', [('1: channel',RIVER_C),('0: non-channel',WHITE)]),
    'gv':('Building void fraction and size','fn_gv: void fraction (unbuilt fraction)\nfn_bb: mean building size [m]',
         'Cell-averaged storage space and drag, not individual building outlines.', [('Building clusters',BUILD_C),('No buildings',WHITE)]),
    'rs':('Pond storage capacity','fn_rscap: storage limit depth [m]\nPositive values identify pond cells.',
         'Storage hrs is separate from surface water. Unspecified capacity is zero.', [('Capacity > 0',RIVER_C),('Capacity = 0',WHITE)]),
    'sd':('Soil depth sd','f_sdtype: 0 → sd0 / 1 → fn_sd\nUsed by groundwater / landform processes',
         'sy0: groundwater specific yield. Supply soil depth as required by the active processes.', [('Soil present',SOIL[1]),('Soil depth = 0',WHITE)]),
    'wall':('Seawall crest and sea side','fn_seaside: sea side (also includes sw > 0)\nfn_seawall / seawall0: crest at land cells\nf_seawall_datum / f_seawall_mode',
         'Diagonal neighbours count. Channel cells stay open. See text for wall behaviour and settings.', [('Sea side',SEA_C),('Land-side crest',WALL_C),('River-mouth opening',RIVER_C)]),
    'defaults':'Use fixed/default values or spatial files as appropriate',
    'default_note':'Basic fields are initialized even without explicit input. Additional fields depend on the active processes and settings.',
    'mask_note':'The domain mask selects the computed area; the sea mask assigns a cell role. They serve different purposes.',
    'footer':'Illustrative 10 × 8 grid. Colours refer to each panel legend; they do not share a physical quantity or numerical scale across panels.',
 },
}


def cell_xy(x, y, i, j):
    """Top-left display corner; raster row j increases southwards."""
    return x+i*CELL, y+j*CELL


def colour(key, c):
    i,j=c
    if key=='z': return SOIL[0] if c in SEA else SOIL[min(3,(i+j)//5)]
    if key=='n': return GOLD if c in BUILDINGS or (3<=i<=5 and j>=5) else GREEN
    if key=='mask': return '#d6d8d8' if c in OUTSIDE else WHITE
    if key=='sw': return SEA_C if c in SEA else WHITE
    if key=='rw': return RIVER_C if c in CHANNEL else WHITE
    if key=='gv': return BUILD_C if c in BUILDINGS else WHITE
    if key=='rs': return RIVER_C if c in PONDS else WHITE
    if key=='sd': return SOIL[1] if c not in SEA else WHITE
    if key=='wall':
        if c in SEA: return SEA_C
        if c in CRESTS: return WALL_C
        if c in COAST & CHANNEL: return RIVER_C
        return WHITE
    raise ValueError(key)


def raster(ax, x, y, key):
    for j in range(NY):
        for i in range(NX):
            p=Rectangle(cell_xy(x,y,i,j),CELL,CELL,facecolor=colour(key,(i,j)),edgecolor='none',zorder=2)
            p.set_gid(f'{key}_cell_{i}_{j}'); ax.add_patch(p)
    for i in range(NX+1):
        line(ax,[(x+i*CELL,y),(x+i*CELL,y+NY*CELL)],'#b8bcbb',.4,z=3)
    for j in range(NY+1):
        line(ax,[(x,y+j*CELL),(x+NX*CELL,y+j*CELL)],'#b8bcbb',.4,z=3)
    border=Rectangle((x,y),NX*CELL,NY*CELL,facecolor='none',edgecolor=MUTED,linewidth=.85,zorder=4)
    border.set_gid(f'{key}_border'); ax.add_patch(border)
    xp,yp=cell_xy(x,y,*MARK)
    p=Rectangle((xp,yp),CELL,CELL,facecolor='none',edgecolor=INK,linewidth=1.4,zorder=8)
    p.set_gid(f'{key}_mark'); ax.add_patch(p)
    text(ax,xp+CELL/2,yp+CELL/2,'P',size=6.4,ha='center',va='center',weight='bold')


def panel(ax,x,y,key,lang,index):
    title,params,note,legend=T[lang][key]
    ax.add_patch(Rectangle((x,y),485,420,facecolor='#f8f9f8',edgecolor=RULE,linewidth=.65,zorder=0))
    text(ax,x+20,y+17,f'({chr(97+index)}) {title}',size=9.6,weight='bold')
    raster(ax,x+20,y+76,key)
    for k,(label,fc) in enumerate(legend):
        ly=y+85+k*47
        ax.add_patch(Rectangle((x+243,ly+3),15,15,facecolor=fc,edgecolor=MUTED,linewidth=.5))
        block(ax,x+268,ly,label,197,size=8)
    block(ax,x+20,y+263,params,445,size=8.3)
    block(ax,x+20,y+358,note,445,size=8.0,color=MUTED)


def build(lang):
    t=T[lang]
    fig=plt.figure(figsize=(CANVAS[0]/DPI,CANVAS[1]/DPI),dpi=DPI)
    ax=fig.add_axes([0,0,1,1]); ax.set(xlim=(0,CANVAS[0]),ylim=(CANVAS[1],0)); ax.axis('off')
    text(ax,30,20,t['title'],size=12,weight='bold')
    text(ax,30,66,t['sub'],size=9,color=MUTED)
    ax.add_patch(Rectangle((30,112),1515,105,facecolor='#edf3f5',edgecolor='none',zorder=0))
    text(ax,50,130,t['grid_title'],size=10,weight='bold')
    text(ax,310,130,t['grid'],size=9.2)
    text(ax,310,174,t['alignment'],size=8.9)
    for k,key in enumerate(KEYS):
        panel(ax,30+(k%3)*515,246+(k//3)*445,key,lang,k)
    text(ax,30,1590,t['defaults'],size=10,weight='bold')
    text(ax,30,1637,t['default_note'],size=9)
    text(ax,30,1679,t['mask_note'],size=9)
    line(ax,[(30,1731),(1545,1731)],RULE,.8)
    text(ax,30,1754,t['footer'],size=8.0,color=MUTED)
    return fig


def draw(lang):
    if lang not in T: raise ValueError('lang must be ja or en')
    out=Path(__file__).resolve().parents[1]/('geoinfo_layers'+('' if lang=='ja' else '_en')+'.png')
    with drawing_style():
        fig=build(lang)
        try:
            fig.savefig(out,dpi=DPI)
            svg=StringIO()
            fig.savefig(svg,format='svg',metadata={'Date':None,
                'Description':'ENCflow geographic input layers on one shared illustrative grid. Not vertical strata, not solver output. Seawall crest-holder cells include diagonal adjacency and exclude channel openings.'})
            out.with_suffix('.svg').write_text('\n'.join(s.rstrip() for s in svg.getvalue().splitlines())+'\n',encoding='utf-8',newline='\n')
        finally:
            plt.close(fig)
    return str(out)
