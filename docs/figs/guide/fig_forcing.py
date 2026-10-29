"""Water pathways, meteorological controls and ET withdrawal priority.

This is a process schematic, not a numerical result or a full water budget.
Blue arrows carry water; dashed grey arrows carry information; orange arrows
pass remaining ET demand. Every connection uses shared node-edge coordinates.
Only generate this figure: python docs/figs/make_guide_figs.py forcing
"""
from io import StringIO
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle
from _schematic import drawing_style, text, block, line, arrow, INK, MUTED, RULE

CANVAS, DPI = (1575, 1730), 150
WATER, DEMAND = '#287ca5', '#b85c2c'
BLUE, GREEN, GREY = '#eef6fa', '#f0f5ea', '#f5f4f0'
# x, y, width, height; pixels at the nominal export resolution.
NODES = {
    'precip': (40, 180, 900, 140),
    'intercept': (40, 380, 900, 170),
    'split': (40, 610, 900, 155),
    'rain': (40, 835, 380, 125),
    'swe': (500, 835, 440, 125),
    'surface': (40, 1080, 900, 100),
    'meteo': (1030, 180, 505, 890),
    'et': (40, 1280, 1495, 355),
}
STORES = [(65 + k*374, 1465, 323, 98) for k in range(4)]

T = {
 'ja': {
    'title':'外力のつながり  |  降水の行き先と蒸発散',
    'sub':'水の移動、気象による補正、蒸発散の適用順を分けて読む。対象は陸域の使用セル。',
    'legend_water':'水の流れ', 'legend_info':'気象情報・補正', 'legend_demand':'残った蒸発散要求',
    'a':'(a) 降水から地表水へ', 'b':'(b) 気象強制場',
    'precip_title':'降水 P  |  fn_precip / &list_precip',
    'precip':'prtype: 1 一様時系列 / 2 固定分布 × 時系列倍率 / 3 分布ファイル列\nprval / fn_prmap / fn_maplist、積算時間の単位を設定する。\nここでは runoff_rate = 1（水収支と Pr に同率で掛かる係数。本文参照）。',
    'ic_title':'樹冠遮断  |  fn_intercept / &list_intercept',
    'ic':'f_icmodel = 1: ic_alpha の割合を損失にし、残り (1 − α)P を通す。\nf_icmodel = 2: ic_smax_mm まで保水し、残容量を超えた分を通す。\n貯留型の空き容量は、(c) の蒸発散によって回復する。',
    'split_title':'雨・雪の分離  |  fn_snow / &list_snow',
    'split':'T ≤ snow_t_snow: 全雪 / T ≥ snow_t_rain: 全雨（閾値が異なる場合）\n間は線形混合。同じ閾値では、その温度以下が全雪、超えると全雨。\n遮断は雨・雪を分ける前に適用する。',
    'rain_title':'雨（液体分）', 'rain':'降雨として地表へ',
    'swe_title':'雪 → 積雪水量 SWE', 'swe':'初期値 [mm]:\nsnow_swe0 / fn_snow_swe0',
    'melt':'融雪要求 [mm/day]:\nsnow_ddf × max(T − snow_t_melt, 0)\n1ステップの融雪量は SWE が上限',
    'surface_title':'地表水 h', 'surface':'雨と融雪水を受け取る。',
    'after':'地表流・浸透などの計算後に (c) を適用。地下水の過程は fn_gwflow。',
    'meteo_title':'fn_meteo / &list_meteo',
    'prec_title':'降水の標高補正',
    'prec':'f_prec_lapse = 1 のとき\n倍率 = max(0, 1 + β(z − prec_zref))\nβ = prec_lapse / 10000 [1/m]\nprec_lapse の入力単位: %/100 m',
    'temp_title':'気温 T の供給',
    'temp':'temp0 / tempval / fn_tempmap\nのいずれか1つ。\n一様入力で f_temp_lapse = 1 のとき\nT = T入力 + ΔT − γ(z − temp_zref)\nγ = temp_lapse / 100 [℃/m]\nΔT: tempofs による気温の加算',
    'temp_note':'分布気温には標高減率を重ねない。\ntempofs は一様・分布の両方へ加算。\n降水補正と積雪の気温評価では、\n氷河があれば氷面標高を使う。',
    'temp_use':'T → 雨雪判定・融雪',
    'pet_link':'T → PET（モード3・4）',
    'et_title':'(c) 蒸発散  |  fn_evap / &list_evap',
    'pet':'f_evmodel: 1 一定 evap0 / 2 月別 evap_monthly / 3 Hamon / 4 Thornthwaite。共通で × evap_kc。',
    'et_order':'PET を日ごとに評価し、各ステップで以下の順に差し引く。矢印は残った要求を次の貯留へ渡す順序。',
    'stores':('① 樹冠保水','② 地表水 h','③ 貯留 hrs','④ 地下水 hg'),
    'store_notes':('貯留型遮断のみ','地表の水','ため池・ダム／湖沼捕捉帯','地下水の貯留'),
    'et_note':'存在する水量まで差し引く。SWE からの昇華は扱わない。貯留間で水を移す矢印ではない。',
    'footer':'模式図。遮断・積雪を使わない場合はその処理を省略（積雪なしでは全量を雨として扱う）。設定の詳細は本文参照。',
 },
 'en': {
    'title':'Forcing chain  |  Where precipitation goes, and how ET removes water',
    'sub':'Separate water pathways, meteorological controls and ET withdrawal order. Applies to active land cells.',
    'legend_water':'Water pathway', 'legend_info':'Meteorological control', 'legend_demand':'Remaining ET demand',
    'a':'(a) Precipitation to surface water', 'b':'(b) Meteorological forcing',
    'precip_title':'Precipitation P  |  fn_precip / &list_precip',
    'precip':'prtype: 1 uniform series / 2 fixed map × multiplier series / 3 map sequence\nSet prval / fn_prmap / fn_maplist and the accumulation time unit.\nShown with runoff_rate = 1 (a factor on both the water budget and Pr; see the text).',
    'ic_title':'Canopy interception  |  fn_intercept / &list_intercept',
    'ic':'f_icmodel = 1: remove the ic_alpha fraction; pass the remainder (1 − α)P.\nf_icmodel = 2: store up to ic_smax_mm; pass water beyond the spare capacity.\nET in (c) restores spare capacity in the storage model.',
    'split_title':'Rain/snow partition  |  fn_snow / &list_snow',
    'split':'Distinct thresholds: T ≤ snow_t_snow → all snow; T ≥ snow_t_rain → all rain.\nLinear mixture between them. Equal thresholds: all snow at or below, else rain.\nInterception acts before the rain/snow split.',
    'rain_title':'Rain (liquid part)', 'rain':'To the surface as rainfall',
    'swe_title':'Snow → snow water equivalent', 'swe':'Initial SWE [mm]:\nsnow_swe0 / fn_snow_swe0',
    'melt':'Melt demand [mm/day]:\nsnow_ddf × max(T − snow_t_melt, 0)\nMelt per step is capped by SWE.',
    'surface_title':'Surface water h', 'surface':'Receives rain and snowmelt.',
    'after':'Apply (c) after surface flow and infiltration, etc. Groundwater processes: fn_gwflow.',
    'meteo_title':'fn_meteo / &list_meteo',
    'prec_title':'Elevation factor for precipitation',
    'prec':'When f_prec_lapse = 1:\nfactor = max(0, 1 + β(z − prec_zref))\nβ = prec_lapse / 10000 [1/m]\nprec_lapse input unit: %/100 m',
    'temp_title':'Supply air temperature T',
    'temp':'Choose exactly one of\ntemp0 / tempval / fn_tempmap.\nUniform input with f_temp_lapse = 1:\nT = Tinput + ΔT − γ(z − temp_zref)\nγ = temp_lapse / 100 [°C/m]\nΔT: temperature offset from tempofs',
    'temp_note':'No lapse correction on temperature maps.\nAdd tempofs to uniform and map inputs.\nPrecipitation correction and snow use\nice-surface elevation if a glacier is active.',
    'temp_use':'T → partition / melt',
    'pet_link':'T → PET (modes 3, 4)',
    'et_title':'(c) Evapotranspiration  |  fn_evap / &list_evap',
    'pet':'f_evmodel: 1 constant evap0 / 2 monthly evap_monthly / 3 Hamon / 4 Thornthwaite. All scaled by evap_kc.',
    'et_order':'Evaluate PET daily; subtract each step in this order. Arrows pass the remaining demand to the next store.',
    'stores':('① Canopy water','② Surface water h','③ Storage hrs','④ Groundwater hg'),
    'store_notes':('Storage interception only','Water at the surface','Ponds / dam–lake capture cells','Groundwater storage'),
    'et_note':'Withdraw only available water. No sublimation from SWE. These arrows do not transfer water between stores.',
    'footer':'Schematic. Skip interception / snow processing when inactive (all precipitation is rain without snow). See text for settings.',
 },
}


def box(ax, key, rect, fill):
    x,y,w,h=rect
    p=Rectangle((x,y),w,h,facecolor=fill,edgecolor=RULE,linewidth=1.0,zorder=1)
    p.set_gid(key); ax.add_patch(p)


def connect(ax, key, points, color=WATER, dashed=False):
    a=arrow(ax,points,color,lw=1.5,ls='--' if dashed else '-',size=10)
    a.set_gid(key)


def build(lang):
    t=T[lang]
    fig=plt.figure(figsize=(CANVAS[0]/DPI,CANVAS[1]/DPI),dpi=DPI)
    ax=fig.add_axes([0,0,1,1]); ax.set(xlim=(0,CANVAS[0]),ylim=(CANVAS[1],0)); ax.axis('off')
    text(ax,40,22,t['title'],size=12,weight='bold')
    text(ax,40,66,t['sub'],size=9,color=MUTED)
    for x,key,color,dashed in [(40,'legend_water',WATER,False),(460,'legend_info',MUTED,True),(1030,'legend_demand',DEMAND,False)]:
        connect(ax,key,[(x,117),(x+65,117)],color,dashed)
        text(ax,x+80,105,t[key],size=8.7,color=color)
    text(ax,40,147,t['a'],size=10,weight='bold')
    text(ax,1030,147,t['b'],size=10,weight='bold')
    for key in ['precip','intercept','split','rain','swe','surface']:
        box(ax,key,NODES[key],GREEN if key=='intercept' else BLUE)
        x,y,w,h=NODES[key]
        tk='ic' if key=='intercept' else key
        text(ax,x+20,y+15,t[tk+'_title'],size=9.8,weight='bold')
        block(ax,x+20,y+57,t[tk],w-40,size=8.8)
    # Directed water paths join the exact edges of their source and target boxes.
    connect(ax,'precip_to_ic',[(490,320),(490,380)])
    connect(ax,'ic_to_split',[(490,550),(490,610)])
    connect(ax,'split_to_rain',[(230,765),(230,835)])
    connect(ax,'split_to_swe',[(720,765),(720,835)])
    connect(ax,'rain_to_surface',[(230,960),(230,1080)])
    connect(ax,'swe_to_surface',[(540,960),(540,1080)])
    block(ax,563,986,t['melt'],377,size=8.1,color=WATER)
    block(ax,40,1201,t['after'],900,size=8.7,color=MUTED)

    box(ax,'meteo',NODES['meteo'],GREY)
    text(ax,1050,198,t['meteo_title'],size=9.5,weight='bold')
    text(ax,1050,250,t['prec_title'],size=9.3,weight='bold')
    block(ax,1050,292,t['prec'],465,size=8.7)
    line(ax,[(1050,430),(1515,430)],RULE,.8)
    text(ax,1050,454,t['temp_title'],size=9.3,weight='bold')
    block(ax,1050,498,t['temp'],465,size=8.7)
    text(ax,1050,705,t['temp_use'],size=9,color=MUTED)
    block(ax,1050,788,t['temp_note'],465,size=8.7,color=MUTED)
    connect(ax,'meteo_to_precip',[(1030,285),(940,285)],MUTED,True)
    connect(ax,'meteo_to_snow',[(1030,723),(940,723)],MUTED,True)
    connect(ax,'meteo_to_pet',[(1280,1070),(1280,1280)],MUTED,True)
    text(ax,1300,1172,t['pet_link'],size=8.4,color=MUTED)

    box(ax,'et',NODES['et'],GREY)
    text(ax,65,1301,t['et_title'],size=10,weight='bold')
    text(ax,65,1351,t['pet'],size=9)
    text(ax,65,1400,t['et_order'],size=9)
    for k,rect in enumerate(STORES):
        box(ax,f'store_{k}',rect,GREEN if k==0 else BLUE)
        x,y,w,h=rect
        text(ax,x+14,y+16,t['stores'][k],size=9.3,weight='bold')
        block(ax,x+14,y+57,t['store_notes'][k],w-28,size=8.1)
        if k<3: connect(ax,f'demand_{k}',[(x+w,y+h/2),(STORES[k+1][0],y+h/2)],DEMAND)
    text(ax,65,1589,t['et_note'],size=8.9,color=MUTED)
    line(ax,[(40,1660),(1535,1660)],RULE,.8)
    block(ax,40,1682,t['footer'],1495,size=8.5,color=MUTED)
    return fig


def draw(lang):
    if lang not in T: raise ValueError('lang must be ja or en')
    out=Path(__file__).resolve().parents[1]/('forcing_chain'+('' if lang=='ja' else '_en')+'.png')
    with drawing_style():
        fig=build(lang)
        try:
            fig.savefig(out,dpi=DPI)
            svg=StringIO()
            fig.savefig(svg,format='svg',metadata={'Date':None,
                'Description':'ENCflow forcing schematic: precipitation, interception, snow, meteorological controls and supply-limited ET withdrawal order. Arrows distinguish water, information and remaining ET demand.'})
            out.with_suffix('.svg').write_text('\n'.join(s.rstrip() for s in svg.getvalue().splitlines())+'\n',encoding='utf-8',newline='\n')
        finally:
            plt.close(fig)
    return str(out)
