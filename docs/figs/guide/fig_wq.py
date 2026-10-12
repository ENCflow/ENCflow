"""Water-quality mass pathways, phase partition and ledger interpretation.

Schematic only; no input parameters or solver output are used. Matches
m_wq.calc/record, m_gwflow_lateral and the scalar advection in swflow_enc.
"""
from io import StringIO
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
from matplotlib.path import Path as MplPath
from _schematic import drawing_style, text, block, line, INK, MUTED, RULE

CANVAS, DPI = (1575, 1870), 150
INPUT, WATER, RETURN, LOSS = '#c45a26', '#2a78d6', '#4d812f', '#6b6a66'
NODES = {f'input{i}': (30+255*i,140,235,180) for i in range(6)}
NODES.update(surface=(30,390,1510,160), pool=(30,790,335,205),
             gw=(425,790,335,205), dam=(820,790,335,205), rs=(1215,790,325,205),
             buildup=(30,1055,730,158), loss=(820,1055,720,158))
ROUTES = [(f'input{i}', 'surface', [(147.5+255*i,320),(147.5+255*i,390)], INPUT, False)
          for i in range(6)]
ROUTES += [
    ('surface','pool',[(86,550),(86,790)],WATER,False),
    ('pool','surface',[(296,790),(296,550)],RETURN,False),
    ('surface','gw',[(475,550),(475,790)],WATER,False),
    ('gw','surface',[(710,790),(710,550)],RETURN,False),
    ('surface','dam',[(870,550),(870,790)],WATER,False),
    ('dam','surface',[(1105,790),(1105,550)],RETURN,False),
    ('surface','rs',[(1270,550),(1270,790)],WATER,False),
    ('buildup','pool',[(195,1055),(195,995)],INPUT,False),
    ('surface','loss',[(1540,480),(1558,480),(1558,1134),(1540,1134)],LOSS,True),
]
T = {
 'ja': {
    'title':'水質の物質収支  |  入力・貯留・移動・除去',
    'sub':'単一物質の主な経路（fn_wq）。矢印は物質の移動方向、_g は result/wq.csv の質量列 [g]。',
    'a':'(a) 物質が入る場所と移る先',
    'inputs': ['点源','面源','分布面源','降雨中濃度','境界流入濃度','管路噴出・吐口'],
    'input_body': ['wq_pt_cell\nwq_pt_load [g/s]\n/ wq_pt_series',
                   'wq_ar_cell\nwq_ar_load [kg/ha/day]\n/ wq_ar_series',
                   'fn_wq_map\n× wq_map_factor\nf_wq_map = 0',
                   'wq_rain_conc [mg/L]\n/ wq_rain_series\n× 地表到達雨量',
                   'wq_in_conc(n) [mg/L]\n/ wq_in_series\n区間流入へ指定',
                   'wq_gwc_conc [mg/L]\n× 噴出・陸側吐口水量\n要 f_gwconduit = 1'],
    'no_column':'CSVの独立列なし',
    'surface':'地表水',
    'concentration':'濃度 C [mg/L] = cq / v_h（湿潤セル）',
    'mass':'mass_surface_g は地表全体の現在質量 [g]。C とは別量。',
    'transport':'溶存態と粒子態の全量を水とともに移流。\n蒸発では物質が残り、濃度が上がる。',
    'pool':'表面蓄積プール B',
    'pool_body':'初期: wq_bd0 / fn_wq_bd0\n蓄積上限: wq_bd_max\n洗い出し・沈降で地表水と交換',
    'gw':'地下プール',
    'gw_body':'側方輸送: f_gwlateral = 1\n地下濃度の 1/R 倍、R = wq_rg\n層2の物質輸送は未対応',
    'dam':'貯留型ダム・湖沼',
    'dam_body':'完全混合: 放流濃度 M/V\nスピルも同濃度\n池内の沈降は未実装',
    'rs':'ため池 rscap',
    'rs_body':'吸収・蓄積（戻り経路なし）\n減衰あり\n蒸発では質量が残留',
    'settle':'沈降 → プール\nf_wq_settle = 1\nsettle_g',
    'wash':'洗い出し / wash_g\nwq_wash_kr（雨滴）\nwq_wash_kf（せん断）\n+ wq_wash_tauc',
    'infil':'浸透 / to_gw_g\nf_wq_infil = 1\nKd時は溶存分 f_d のみ',
    'seep':'飽和湧出 / seep_g\n地下濃度の 1/R 倍で地表へ',
    'capture':'捕捉 / to_dam_g',
    'release':'放流 / rel_dam_g',
    'absorb':'吸収 / to_rs_g',
    'buildup':'表面プールへの蓄積入力  |  in_bldup_g',
    'buildup_body':'wq_bd_rate または fn_wq_map（f_wq_map = 1）\n分布には wq_map_factor を適用。初期量は累積入力と別。',
    'loss':'地表から追跡対象外へ（破線）',
    'loss_body':'河床への沈降: f_wq_settle = 0 / settle_g\n枡流入: f_wq_gwc_in = 1 / to_gwc_g\n水位固定湖沼: to_dam_g / 境界流出: CSV独立列なし',
    'decay':'5つの貯留すべてで一次減衰  |  decay_g',
    'decay_body':'地表・地下・表面プール・ダム・ため池。wq_thalf または wq_k20 を指定（排他）。',
    'b':'(b) 分配と沈降の二つの方式（同時指定不可）',
    'single':'wq_vs: 全量を対象とする単相の沈降',
    'single_body':'入力は [m/day]。速度 v_s = wq_vs / 86400 [m/s]。',
    'kd':'wq_kd: 溶存態・粒子態の平衡分配（要 f_suspend）',
    'kd_units':'Kd_SI [m³/kg] = 10⁻³ × wq_kd [L/kg]\nCss [kg/m³]: 浮遊砂の質量濃度',
    'fractions':'浸透は f_d、沈降は粒子態 (1 − f_d) が同伴。\n粒子態は浮遊砂の沈降速度で沈む。',
    'dest':'両方式の沈降先は f_wq_settle で選ぶ（1: プール / 0: 消失）。',
    'c':'(c) 台帳の読み方',
    'ledger':'mass_*_g は現在貯留、入力・移動・減衰は累積量。\n内部移動を系外損失として二重に数えない。',
    'settle_ledger':'settle_g は行き先0・1の両方で計上。\n行き先1のとき、全貯留の合計から差し引かない。',
    'dam_ledger':'to_dam_g は貯留型と水位固定型の捕捉を合算。\n管内の物質輸送は解かず、管路への除去と噴出入力は別。',
    'boundary_ledger':'境界流入・流出・収支残差の独立列はない。\n境界を通る輸送がある収支検算では、別途それを含める。',
    'footer':'模式図。初期量・入力条件・有効な経路をそろえて収支を検算する。v_h は断面形状を考慮した矩形換算水深。',
 },
 'en': {
    'title':'Water-quality mass budget  |  Inputs, storage, transfers and removal',
    'sub':'Main pathways for one substance (fn_wq). Arrows show mass transfer; _g names are mass columns [g] in result/wq.csv.',
    'a':'(a) Where mass enters and moves',
    'inputs':['Point source','Areal source','Distributed source','Rain concentration','Boundary inflow','Sewer surcharge'],
    'input_body':['wq_pt_cell\nwq_pt_load [g/s]\n/ wq_pt_series',
                  'wq_ar_cell\nwq_ar_load [kg/ha/day]\n/ wq_ar_series',
                  'fn_wq_map\n× wq_map_factor\nf_wq_map = 0',
                  'wq_rain_conc [mg/L]\n/ wq_rain_series\n× rain reaching ground',
                  'wq_in_conc(n) [mg/L]\n/ wq_in_series\non inflow segments',
                  'wq_gwc_conc [mg/L]\n× surcharge/outfall water\nneeds f_gwconduit = 1'],
    'no_column':'No separate CSV column',
    'surface':'Surface water',
    'concentration':'Concentration C [mg/L] = cq / v_h (wet cells)',
    'mass':'mass_surface_g is the current surface total [g], distinct from C.',
    'transport':'Both dissolved and particulate mass advect with water.\nEvaporation leaves mass behind, increasing concentration.',
    'pool':'Surface buildup pool B',
    'pool_body':'Initial: wq_bd0 / fn_wq_bd0\nBuildup cap: wq_bd_max\nExchange by washoff and settling',
    'gw':'Groundwater pool',
    'gw_body':'Lateral flow: f_gwlateral = 1\nGroundwater concentration / R\nR = wq_rg; no layer-2 transport',
    'dam':'Storage-type dam / lake',
    'dam_body':'Fully mixed: release at M/V\nSpill has the same concentration\nNo in-reservoir settling',
    'rs':'Retention pond rscap',
    'rs_body':'Absorbs mass; no return path\nDecay acts here too\nEvaporation leaves mass behind',
    'settle':'Settle → pool\nf_wq_settle = 1\nsettle_g',
    'wash':'Washoff / wash_g\nwq_wash_kr (rain)\nwq_wash_kf (shear)\n+ wq_wash_tauc',
    'infil':'Infiltrate / to_gw_g\nf_wq_infil = 1\nKd: dissolved f_d only',
    'seep':'Seep back / seep_g\nAt groundwater concentration / R',
    'capture':'Capture / to_dam_g',
    'release':'Release / rel_dam_g',
    'absorb':'Absorb / to_rs_g',
    'buildup':'Input to the buildup pool  |  in_bldup_g',
    'buildup_body':'wq_bd_rate OR fn_wq_map (f_wq_map = 1)\nApply wq_map_factor to the map. Initial mass is separate.',
    'loss':'Removal from surface storage (dashed)',
    'loss_body':'To bed: f_wq_settle = 0 / settle_g\nInlet removal: f_wq_gwc_in = 1 / to_gwc_g\nFixed-level lake: to_dam_g / boundary outflow: no CSV column',
    'decay':'First-order decay in all five stores  |  decay_g',
    'decay_body':'Surface, groundwater, buildup, dams and ponds. Specify either wq_thalf or wq_k20.',
    'b':'(b) Two alternative settling treatments (choose one)',
    'single':'wq_vs: single-phase settling of the total mass',
    'single_body':'Input [m/day]; velocity v_s = wq_vs / 86400 [m/s].',
    'kd':'wq_kd: dissolved/particulate equilibrium (needs f_suspend)',
    'kd_units':'Kd_SI [m³/kg] = 10⁻³ × wq_kd [L/kg]\nCss [kg/m³]: suspended-sediment mass concentration',
    'fractions':'Infiltration carries f_d; settling removes (1 − f_d).\nParticles settle at the suspended-sediment settling velocity.',
    'dest':'Both use f_wq_settle for the destination (1: pool / 0: loss).',
    'c':'(c) Reading the ledger',
    'ledger':'mass_*_g columns are current stores; other mass columns are cumulative.\nAvoid double-counting internal transfers as system losses.',
    'settle_ledger':'settle_g counts settling for both destinations 0 and 1.\nFor destination 1, do not subtract it from total stored mass.',
    'dam_ledger':'to_dam_g combines captures by storage and fixed-level lakes.\nPipe transport is not solved; removal and surcharge are separate.',
    'boundary_ledger':'No separate columns for boundary inflow, outflow or residual.\nInclude boundary transport separately when checking closure.',
    'footer':'Schematic. Check budgets with consistent initial mass, inputs and active pathways. v_h is the section-equivalent rectangular water depth.',
 },
}
INPUT_LEDGER = ['in_point_g','in_area_g','in_map_g','in_rain_g',None,'in_gwc_g']
STORE_LEDGER = ['mass_surface_g','mass_pool_g','mass_gw_g','mass_dam_g','mass_rs_g']


def box(ax, key, face, edge):
    p = Rectangle(NODES[key][:2], *NODES[key][2:], facecolor=face, edgecolor=edge,
                  linewidth=1.2, zorder=2)
    p.set_gid(key); ax.add_patch(p)


def route(ax, points, color, dashed):
    path = MplPath(points,[MplPath.MOVETO]+[MplPath.LINETO]*(len(points)-1))
    p = FancyArrowPatch(path=path,arrowstyle='-|>',mutation_scale=10,
                        lw=1.5,color=color,linestyle='--' if dashed else '-',
                        capstyle='round',joinstyle='round',zorder=5)
    ax.add_patch(p)


def build(lang):
    t = T[lang]
    fig = plt.figure(figsize=(CANVAS[0]/DPI,CANVAS[1]/DPI),dpi=DPI)
    ax = fig.add_axes([0,0,1,1]); ax.set(xlim=(0,CANVAS[0]),ylim=(CANVAS[1],0)); ax.axis('off')
    text(ax,30,20,t['title'],size=12,weight='bold')
    text(ax,30,65,t['sub'],size=8.6,color=MUTED)
    text(ax,30,105,t['a'],size=10.4,weight='bold')
    for i in range(6):
        x,y,w,h = NODES[f'input{i}']
        box(ax,f'input{i}','#fdf0e8',INPUT)
        text(ax,x+14,y+12,t['inputs'][i],size=9.1,color=INPUT,weight='bold')
        block(ax,x+14,y+54,t['input_body'][i],w-28,size=7.9)
        text(ax,x+14,y+148,INPUT_LEDGER[i] or t['no_column'],size=7.8,color=INPUT)
    box(ax,'surface','#edf4fc',WATER)
    text(ax,55,408,t['surface'],size=11,weight='bold',color=WATER)
    text(ax,1170,412,STORE_LEDGER[0]+' [g]',size=9.0,color=WATER)
    text(ax,55,457,t['concentration'],size=9.4)
    text(ax,55,505,t['mass'],size=8.1,color=MUTED)
    text(ax,795,459,t['transport'],size=8.6,color=WATER)
    for key,ledger,face,edge in [('pool',STORE_LEDGER[1],'#fbf2da','#aa8123'),
                               ('gw',STORE_LEDGER[2],'#f2eee7','#8c7b63'),
                               ('dam',STORE_LEDGER[3],'#edf4fc',WATER),
                               ('rs',STORE_LEDGER[4],'#edf4fc',WATER)]:
        box(ax,key,face,edge)
        x,y,w,h=NODES[key]
        text(ax,x+15,y+15,t[key],size=9.5,weight='bold',color=edge)
        text(ax,x+15,y+54,ledger,size=8.7,color=edge)
        block(ax,x+15,y+98,t[key+'_body'],w-30,size=8.2)
    for _,_,points,color,dashed in ROUTES: route(ax,points,color,dashed)
    for x,y,key,width,color in [(103,590,'settle',183,WATER),(104,678,'wash',182,RETURN),
                               (491,590,'infil',209,WATER),(491,720,'seep',209,RETURN),
                               (887,611,'capture',208,WATER),(887,721,'release',208,RETURN),
                               (1287,635,'absorb',240,WATER)]:
        block(ax,x,y,t[key],width,size=8.0,color=color)
    for key,face,edge in [('buildup','#fdf0e8',INPUT),('loss','#f4f3f0',LOSS)]:
        box(ax,key,face,edge)
        x,y,w,h=NODES[key]
        text(ax,x+18,y+14,t[key],size=9.4,color=edge,weight='bold')
        block(ax,x+18,y+60,t[key+'_body'],w-36,size=8.1)
    line(ax,[(30,1250),(1540,1250)],RULE,.8)
    text(ax,30,1270,t['decay'],size=9.7,weight='bold')
    text(ax,30,1310,t['decay_body'],size=8.6,color=MUTED)
    line(ax,[(30,1350),(1540,1350)],RULE,.8)
    text(ax,30,1375,t['b'],size=10.0,weight='bold')
    text(ax,30,1425,t['single'],size=8.9,color=WATER)
    text(ax,30,1462,t['single_body'],size=8.2)
    text(ax,30,1513,t['kd'],size=8.9,color=WATER)
    text(ax,30,1550,t['kd_units'],size=8.3)
    text(ax,30,1619,r'$f_d = 1/(1 + K_{d,\mathrm{SI}}\,C_{ss})$',size=11,color=WATER)
    text(ax,30,1675,t['fractions'],size=8.4)
    text(ax,30,1765,t['dest'],size=7.9,color=MUTED)
    text(ax,815,1375,t['c'],size=10.0,weight='bold')
    for y,key in [(1425,'ledger'),(1520,'settle_ledger'),(1620,'dam_ledger'),(1720,'boundary_ledger')]:
        block(ax,815,y,t[key],710,size=8.3)
    line(ax,[(30,1820),(1540,1820)],RULE,.8)
    text(ax,30,1840,t['footer'],size=7.9,color=MUTED)
    return fig


def draw(lang):
    if lang not in T: raise ValueError('lang must be ja or en')
    out = Path(__file__).resolve().parents[1]/('wq_budget'+('' if lang=='ja' else '_en')+'.png')
    with drawing_style():
        fig=build(lang)
        try:
            fig.savefig(out,dpi=DPI)
            svg=StringIO()
            fig.savefig(svg,format='svg',metadata={'Date':None,'Description':'ENCflow water-quality mass pathways and ledger interpretation; schematic.'})
            out.with_suffix('.svg').write_text('\n'.join(x.rstrip() for x in svg.getvalue().splitlines())+'\n',encoding='utf-8',newline='\n')
        finally: plt.close(fig)
    return str(out)
