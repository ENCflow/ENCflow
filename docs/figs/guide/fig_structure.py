"""内部水理構造物の 4 型(排水ポンプ・カルバート・分水・ダム/湖沼)の模式図(structure.md)。"""
from _style import *

T = {"ja": {
    "a": "(a) 排水ポンプ(&list_struct_pump)\n取水セル群 → 吐口セル群(または域外)への強制転送",
    "b": "(b) カルバート(&list_struct_culvert)\n盛土を横断する矩形暗渠 B×D。水頭差で双方向",
    "c": "(c) 分水(&list_struct_diversion)\n取水セル群から域外(または送水先)へ一方向・受動的",
    "d": "(d) ダム・湖沼(&list_struct_dam)\n湖面セルが到達水を全量捕捉 → 貯留 V(H) → 運転則で放流",
    "pump_in": "pump_in_cell\n(取水セル群)", "pump_out": "pump_out_cell\n(吐口セル群)",
    "pump_q": "Q = pump_q0(一定)\n  or pump_rule(基準値→Q の折れ線)\n基準 f_pump_ref: 0 = η, 1 = h\n(取水代表セル=先頭)",
    "pump_outside": "省略 → 域外排水\n(系から除去)", "pump_src": "f_pump_src = 1:\n管路連続体層 hgc から汲む",
    "pump_pond": "ため池セル(rscap>0)\nなら貯留から汲む", "levee": "堤防・盛土", "river": "河道",
    "culv_in": "culv_in_cell", "culv_out": "culv_out_cell", "culv_zin": "culv_zin", "culv_zout": "culv_zout",
    "culv_BD": "culv_width B\nculv_height D", "culv_L": "culv_length L(culv_manning n、culv_ce)",
    "culv_regime": "水位に応じて 無流 → 自由水面(堰)→ 満管(オリフィス+摩擦)",
    "culv_flap": "culv_flap = 1: out→in の逆流を遮断",
    "culv_gate": "culv_gate_rule(基準水位→開度 0〜1)\nculv_gate_ref: 0 = in 側, 1 = out 側(河川側)",
    "div_in": "div_in_cell\n(取水セル群。堰直上流)", "div_q": "Q = div_q0(一定)\n  or div_rule(取水代表セルの η → Q)",
    "div_outside": "省略 → 域外分水", "div_out": "div_out_cell(送水先)\n送水先の η ≥ 取水側 なら自動停止",
    "div_passive": "重力では登れない(強制は ポンプ)", "flow": "流下",
    "lake_cells": "湖面 = 捕捉集合: dam_in_cell / fn_dam_in_cell / fn_dam_map(湖沼番号ラスタ)",
    "capture": "到達水を\n毎ステップ全量吸収", "H": "水位 H(絶対標高)", "V": "V(H): dam_hv(HV 曲線)\n  or dam_hmin [+dam_hsur]\n  (線形 A·(H−hmin))",
    "hsur": "サーチャージ → 超過分は強制スピル", "hmin": "最低水位 = 死水\n(dam_hmin / HV の第1点)",
    "tadashigaki": "dam_tadashigaki: 但し書き操作(モード 1, 2)",
    "release": "放流 Q → dam_out_cell\nf_dam_mode 1: dam_q0 / 2: dam_rate×Qin / 3: Q(H)\n (dam_hq_rule / オリフィス / dam_qmax √則)",
    "lake": "dam_lake(n) = m: 追加の放流工\n湖沼 m の貯留から別の運転則・\n放流セルで引く", "gw": "dam_gw = 1: 湖面セルの地下水頭 = H\n(要 f_gwlateral=1。交換量 Qgw)",
    "noout": "放流セルなし+モード指定なし = 水位固定湖沼(流入は消失)", "dam": "堤体",
    "hinit": "dam_h_init(初期水位)",
}, "en": {
    "a": "(a) Drainage pump (&list_struct_pump)\nforced transfer: intake cells -> outlet cells (or outside)",
    "b": "(b) Culvert (&list_struct_culvert)\nB x D box through an embankment; head-driven, bidirectional",
    "c": "(c) Diversion (&list_struct_diversion)\npassive one-way withdrawal, to outside or receiving cells",
    "d": "(d) Dam / lake (&list_struct_dam)\nlake cells capture inflow -> storage V(H) -> release by rule",
    "pump_in": "pump_in_cell\n(intake cells)", "pump_out": "pump_out_cell\n(outlet cells)",
    "pump_q": "Q = pump_q0 (constant)\n  or pump_rule (reference -> Q polyline)\nreference f_pump_ref: 0 = eta, 1 = h\n(first intake cell)",
    "pump_outside": "omitted -> out of domain\n(removed from system)", "pump_src": "f_pump_src = 1:\ndraws from conduit layer hgc",
    "pump_pond": "pond cell (rscap>0):\ndraws from pond storage", "levee": "levee / embankment", "river": "river",
    "culv_in": "culv_in_cell", "culv_out": "culv_out_cell", "culv_zin": "culv_zin", "culv_zout": "culv_zout",
    "culv_BD": "culv_width B\nculv_height D", "culv_L": "culv_length L (culv_manning n, culv_ce)",
    "culv_regime": "by water level: no flow -> free surface (weir) -> full pipe (orifice + friction)",
    "culv_flap": "culv_flap = 1: blocks out->in backflow",
    "culv_gate": "culv_gate_rule (reference level -> opening 0-1)\nculv_gate_ref: 0 = in side, 1 = out side (river)",
    "div_in": "div_in_cell\n(intake cells, just upstream of weir)", "div_q": "Q = div_q0 (constant)\n  or div_rule (eta of first intake cell -> Q)",
    "div_outside": "omitted -> out of domain", "div_out": "div_out_cell (receiving cells)\nstops when receiving eta >= intake eta",
    "div_passive": "gravity cannot climb (use a pump to force)", "flow": "flow",
    "lake_cells": "lake surface = capture set: dam_in_cell / fn_dam_in_cell / fn_dam_map (lake-number raster)",
    "capture": "absorbs all arriving\nwater every step", "H": "level H (absolute elevation)", "V": "V(H): dam_hv (HV curve)\n  or dam_hmin [+dam_hsur]\n  (linear A·(H−hmin))",
    "hsur": "surcharge -> excess is forced spill", "hmin": "minimum level = dead storage\n(dam_hmin / 1st HV point)",
    "tadashigaki": "dam_tadashigaki: emergency rule",
    "release": "release Q -> dam_out_cell\nf_dam_mode 1: dam_q0 / 2: dam_rate x Qin / 3: Q(H)\n (dam_hq_rule / orifice / dam_qmax sqrt law)",
    "lake": "dam_lake(n) = m: extra outlet\ndrawing lake m's storage with\nits own rule and outlet cells", "gw": "dam_gw = 1: groundwater head in lake cells = H\n(needs f_gwlateral=1; exchange Qgw)",
    "noout": "no outlet cells + no mode = fixed-level lake (inflow vanishes)", "dam": "dam body",
    "hinit": "dam_h_init (initial level)",
}}

# These helpers do not change the style or rendering of other guide figures.
from _schematic import (drawing_style, text, block, paragraph, line,
                        arrow as flow_arrow, curve, ground, water as wet_water,
                        patch, export, INK, MUTED, RULE)
import numpy as np

PUMP_X = np.array([0, 2.6, 4.0, 4.6, 5.6, 6.2, 7.2, 8.6, 10.2])
PUMP_Z = np.array([1.0, 0.9, 1.3, 2.6, 2.6, 1.3, 0.3, 0.3, 1.6])
CULVERT_X = np.array([0, 3.2, 4.4, 5.8, 7.0, 10.2])
CULVERT_Z = np.array([.8, .8, 3., 3., .8, .8])
DAM_X = np.array([0, .8, 1.6, 3.4, 5., 6.5, 10.7])
DAM_Z = np.array([2.6, 2., 1., .5, .5, .2, .0])


def _heading(ax, t, key):
    ax.set_xlim(-.2, 10.9); ax.set_ylim(*getattr(ax, '_schematic_ylim', (-5.6,5.8)))
    ax.set_aspect('equal'); ax.axis('off')
    ax.figure.canvas.draw()
    title, subtitle = t[key].split('\n', 1)
    text(ax, 0, 5.56, title, size=11.1, weight='bold')
    block(ax, 0, 5.03, subtitle, 10.65, size=9.0)
    line(ax, [(0,-.91),(10.65,-.91)], RULE, .7, z=1)


def panel_pump(ax, t):
    _heading(ax,t,'a')
    # Water polygons and terrain use identical bed samples and exact shore roots.
    ground(ax, PUMP_X, PUMP_Z, -.55, C_GROUND_L, C_GROUND)
    wet_water(ax,PUMP_X,PUMP_Z,1.6,C_WATER_L,C_WATER,xmax=4.6)
    wet_water(ax,PUMP_X,PUMP_Z,1.1,C_WATER_L,C_WATER,xmin=5.6)
    line(ax,list(zip(PUMP_X,PUMP_Z)),C_GROUND,1.1,z=5)
    # Tangent-continuous pipe elbows. One path per directed connection.
    incoming=curve((2.,1.22), [('L',(2.,2.67)),
        ('C',(2.,2.805),(2.105,2.91),(2.24,2.91)),('L',(4.65,2.91))])
    outgoing=curve((5.55,2.91), [('L',(7.38,2.91)),
        ('C',(7.50,2.91),(7.60,2.81),(7.60,2.69)),('L',(7.60,.94))])
    flow_arrow(ax,incoming,C_X,2.0,size=11,z=8)
    flow_arrow(ax,outgoing,C_X,2.0,size=11,z=8)
    ax.add_patch(Rectangle((4.65,2.6),.9,.62,fc=C_X,ec=INK,lw=1.0,zorder=10))
    text(ax,5.10,2.91,'P',size=11,ha='center',va='center',color='white',weight='bold')
    flow_arrow(ax,curve((5.55,2.91),[('C',(6.15,2.91),(6.12,3.85),(6.82,3.85)),
                                ('L',(8.20,3.85))]),C_X,1.25,ls='--',size=9)
    text(ax,8.40,3.85,'域外' if t is T['ja'] else 'outside',size=9.5,va='center',color=C_X)
    block(ax,.30,2.22,t['pump_in'],3.0,size=8.7,color=C_C)
    block(ax,8.10,2.17,t['pump_out'],2.45,size=8.7,color=C_C)
    text(ax,5.10,2.25,t['levee'],size=8.5,ha='center',color=C_GROUND)
    text(ax,9.90,.35,t['river'],size=8.5,ha='right',color=C_GROUND)
    # Optional source: only a schematic connection, not a geological layer.
    ax.add_patch(Rectangle((1.30,-.34),1.40,.34,fc='none',ec=MUTED,lw=.95,ls='--',zorder=5))
    text(ax,2.,-.17,'hgc',size=8.5,ha='center',va='center',color=MUTED)
    line(ax,[(2,0),(2,float(np.interp(2,PUMP_X,PUMP_Z)))],MUTED,.9,ls=':',z=5)
    y=paragraph(ax,0,-1.19,t['pump_q'],5.0,size=8.5,color=C_X)
    paragraph(ax,0,y-.08,t['pump_pond'],5.0,size=8.5,color=MUTED)
    y=paragraph(ax,5.55,-1.19,t['pump_outside'],5.10,size=8.5,color=C_X)
    paragraph(ax,5.55,y-.18,t['pump_src'],5.10,size=8.5,color=MUTED)


def panel_culvert(ax,t):
    _heading(ax,t,'b')
    ground(ax,CULVERT_X,CULVERT_Z,-.55,C_GROUND_L,C_GROUND)
    wet_water(ax,CULVERT_X,CULVERT_Z,2.3,C_WATER_L,C_WATER,xmax=4.4)
    wet_water(ax,CULVERT_X,CULVERT_Z,1.7,C_WATER_L,C_WATER,xmin=5.8)
    line(ax,list(zip(CULVERT_X,CULVERT_Z)),C_GROUND,1.1,z=5)
    zin,zout,D=1.05,.95,.75
    # A structural opening is intentionally layered over the embankment.
    ax.add_patch(Polygon([(3.3,zin),(6.9,zout),(6.9,zout+D),(3.3,zin+D)],
                  closed=True,fc='white',ec=INK,lw=1.3,zorder=7))
    flow_arrow(ax,[(3.65,1.55),(6.52,1.47)],C_C,1.6,size=10,z=9)
    flow_arrow(ax,[(6.52,1.23),(3.65,1.31)],C_C,1.15,ls='--',size=8,z=9)
    line(ax,[(6.9,zout+D),(6.75,zout+.15)],C_X,1.8,z=10)
    text(ax,1.75,2.59,t['culv_in'],size=9,ha='center',color=C_C)
    text(ax,8.72,2.03,t['culv_out'],size=9,ha='center',color=C_C)
    text(ax,5.10,2.56,'B × D',size=10,ha='center')
    text(ax,7.18,3.42,'フラップ（任意）' if t is T['ja'] else 'flap (optional)',size=8.6,color=C_X)
    line(ax,[(7.15,3.12),(7.28,2.41),(6.9,1.7)],MUTED,.75,z=10)
    line(ax,[(2.75,zin),(3.3,zin)],MUTED,.75)
    line(ax,[(6.9,zout),(7.55,zout)],MUTED,.75)
    text(ax,2.9,.75,t['culv_zin'],size=8.3,ha='right',color=MUTED)
    text(ax,7.25,.59,t['culv_zout'],size=8.3,color=MUTED)
    ax.annotate('',(3.3,.18),(6.9,.18),arrowprops=dict(arrowstyle='<->',lw=.75,
                           shrinkA=0,shrinkB=0,color=MUTED,mutation_scale=8))
    for x in (3.3,6.9): line(ax,[(x,.06),(x,.30)],MUTED,.65)
    text(ax,5.1,-.02,'L',size=9,ha='center',color=MUTED)
    y=paragraph(ax,0,-1.19,t['culv_regime'],10.65,size=8.5)
    y-=.10
    yl=paragraph(ax,0,y,t['culv_flap'],5.0,size=8.4,color=C_X)
    paragraph(ax,0,yl-.12,t['culv_BD'],5.0,size=8.4,color=MUTED)
    yr=paragraph(ax,5.55,y,t['culv_gate'],5.1,size=8.4,color=C_X)
    paragraph(ax,5.55,yr-.12,t['culv_L'],5.1,size=8.4,color=MUTED)


def diversion_outline():
    """One connected water outline; no shore line crosses the open intake."""
    upper=lambda x:2.1-.2*x/10.2
    return curve((0.,1.),[
      ('L',(10.2,.8)),('L',(10.2,1.9)),('L',(5.2,upper(5.2))),
      ('C',(4.85,upper(4.85)),(4.65,2.22),(4.65,2.55)),
      ('L',(4.65,2.9)),('C',(4.65,3.12),(4.83,3.3),(5.05,3.3)),
      ('L',(7.4,3.3)),('L',(7.4,4.0)),('L',(4.5,4.0)),
      ('C',(4.058,4.0),(3.7,3.642),(3.7,3.2)),('L',(3.7,2.6)),
      ('C',(3.7,2.277),(3.45,upper(3.45)),(3.1,upper(3.1))),
      ('L',(0.,2.1)),('Z',)])


def panel_diversion(ax,t):
    _heading(ax,t,'c')
    domain=patch(ax,diversion_outline(),C_WATER_L,C_WATER,1.15,z=2)
    for k in range(3):
        p=Rectangle((3.50+.4*k,1.00),.4,.96,fc=C_B,ec=C_X,lw=.8,zorder=4)
        p.set_clip_path(domain);ax.add_patch(p)
    # Weir end points are evaluated from the same two river banks.
    xw=5.25
    line(ax,[(xw,1.-.2*xw/10.2),(xw,2.1-.2*xw/10.2)],INK,2.4,z=6)
    text(ax,5.55,2.56,'堰' if t is T['ja'] else 'weir',size=8.5)
    line(ax,[(5.55,2.24),(xw,2.1-.2*xw/10.2)],MUTED,.7)
    flow_arrow(ax,[(.55,1.55),(2.70,1.51)],C_C,1.7,size=10)
    flow_arrow(ax,[(7.35,1.40),(9.72,1.35)],C_C,1.7,size=10)
    text(ax,1.60,1.30,t['flow'],size=8.6,ha='center',color=C_C)
    flow_arrow(ax,curve((4.15,1.43),[('L',(4.15,2.95)),
        ('C',(4.15,3.337),(4.463,3.65),(4.85,3.65)),('L',(7.06,3.65))]),C_X,1.9,size=11)
    flow_arrow(ax,[(7.4,3.65),(9.88,3.65)],C_X,1.3,ls='--',size=9)
    text(ax,9.95,4.23,'域外' if t is T['ja'] else 'outside',size=9,ha='right',color=C_X)
    for k in range(2):
        ax.add_patch(Rectangle((8.45+.45*k,2.40),.45,.45,fc=C_WATER_L,ec=C_C,lw=.9,zorder=4))
    flow_arrow(ax,curve((7.4,3.65),[('C',(7.92,3.65),(8.45,3.22),(8.67,2.65))]),
               C_C,1.05,ls=':',size=8)
    block(ax,2.35,.51,t['div_in'],4.7,size=8.6,color=C_X)
    text(ax,9.40,2.22,'div_out_cell',size=8.3,ha='right',color=C_C)
    y=paragraph(ax,0,-1.19,t['div_q'],5.,size=8.5,color=C_X)
    paragraph(ax,0,y-.20,t['div_outside'],5.,size=8.5,color=C_X)
    y=paragraph(ax,5.55,-1.19,t['div_out'],5.1,size=8.5,color=C_C)
    paragraph(ax,5.55,y-.20,t['div_passive'],5.1,size=8.5,color=MUTED)


def dam_upstream_x(level):
    return 5.0+.3*(level-.5)/(3.4-.5)


def panel_dam(ax,t):
    _heading(ax,t,'d')
    ground(ax,DAM_X,DAM_Z,-.55,C_GROUND_L,C_GROUND)
    H,Hsur,Hmin=2.2,2.9,1.0
    # Reservoir profile includes the actual upstream dam face, not a guessed edge.
    rx=np.array([0.,.8,1.6,3.4,5.,5.3]);rz=np.array([2.6,2.,1.,.5,.5,3.4])
    wet_water(ax,rx,rz,H,C_WATER_L,C_WATER)
    ax.add_patch(Polygon([(5.,.5),(5.3,3.4),(5.7,3.4),(6.5,.2)],
                         closed=True,fc=C_GROUND,ec=INK,lw=1.05,zorder=6))
    line(ax,[(0,Hsur),(dam_upstream_x(Hsur),Hsur)],C_X,.95,ls='--',z=8)
    line(ax,[(1.6,Hmin),(dam_upstream_x(Hmin),Hmin)],MUTED,.85,ls='--',z=8)
    text(ax,.08,Hsur+.09,'Hsur',size=8.7,color=C_X,va='bottom')
    text(ax,1.65,H+.09,t['H'],size=8.7,color=C_C,va='bottom')
    text(ax,3.0,1.64,'V(H)',size=11,ha='center',color=C_C)
    text(ax,1.72,Hmin-.14,'Hmin',size=8.5,color=MUTED)
    text(ax,5.57,2.35,t['dam'],size=8.0,ha='center',color='white',rotation=90)
    # Symbolic capture-cell set is kept distinct from the physical cross-section.
    for k in range(9):
        ax.add_patch(Rectangle((.50+.45*k,3.45),.45,.32,fc=C_B,ec=C_X,lw=.65,zorder=8))
    flow_arrow(ax,[(1.35,4.37),(1.35,3.89)],C_X,1.4,size=10)
    block(ax,2.05,4.45,t['capture'],3.20,size=8.8,color=C_X)
    # Downstream water uses the exact same bed; it meets the downstream dam face.
    dx=np.array([5.7,6.5,10.7]);dz=np.array([3.4,.2,0.])
    wet_water(ax,dx,dz,.5,C_WATER_L,C_WATER)
    flow_arrow(ax,curve((4.75,1.16),[('L',(6.40,1.16)),
                  ('C',(6.79,1.16),(6.97,.79),(7.50,.40))]),C_C,1.9,size=10,z=10)
    flow_arrow(ax,curve((4.65,1.75),[('L',(9.49,1.75)),
                  ('C',(9.661,1.75),(9.80,1.611),(9.80,1.44)),('L',(9.8,.38))]),
                  C_G,1.45,ls='--',size=9,z=10)
    text(ax,7.8,.71,'dam_out_cell',size=8.8,color=C_C,va='bottom')
    cell_x=np.array([7.10,7.75])
    cell_z=np.interp(cell_x,DAM_X,DAM_Z)
    ax.add_patch(Polygon([(cell_x[0],cell_z[0]),(cell_x[1],cell_z[1]),
                  (cell_x[1],.5),(cell_x[0],.5)],closed=True,fc='none',ec=C_C,lw=.9,zorder=8))
    text(ax,7.8,1.98,'dam_lake',size=8.8,color='#3f7a2a',va='bottom')
    flow_arrow(ax,[(3.5,.45),(3.5,-.18)],MUTED,1.05,ls=':',size=8)
    flow_arrow(ax,[(3.92,-.18),(3.92,.45)],MUTED,1.05,ls=':',size=8)
    text(ax,4.18,-.18,'Qgw',size=8.5,color=MUTED)
    y=paragraph(ax,0,-1.19,t['lake_cells'],10.65,size=8.15,color=C_X,gap=.20)
    yl=y;yr=y
    for key,col in [('V',C_C),('hmin',MUTED),('hsur',C_X),('tadashigaki',C_X)]:
        yl=paragraph(ax,0,yl,t[key],5.00,size=8.0,color=col,gap=.14)
    for key,col in [('release',C_C),('lake','#3f7a2a'),('gw',MUTED)]:
        note=t[key].replace(' / 2:', ' /\n2:') if key=='release' else t[key]
        yr=paragraph(ax,5.55,yr,note,5.10,size=8.0,color=col,gap=.14)
    paragraph(ax,0,min(yl,yr)-.08,t['noout'],10.65,size=7.8,color=MUTED)


def build(lang):
    if lang not in T: raise ValueError('lang must be ja or en')
    # Physical dimensions keep the two columns at the same drawing scale.
    width=13.2
    panel_width=.437*width
    scale=panel_width/11.1
    top_height=9.10*scale
    bottom_height=11.40*scale
    margin_top,margin_bottom,gap=.32,.35,.34
    height=margin_top+top_height+gap+bottom_height+margin_bottom
    fig=plt.figure(figsize=(width,height))
    top_y=(margin_bottom+bottom_height+gap)/height
    bottom_y=margin_bottom/height
    for x,func,low in [(.037,panel_pump,-3.3),(.526,panel_culvert,-3.3),
                       (.037,panel_diversion,-5.6),(.526,panel_dam,-5.6)]:
        is_top=func in (panel_pump,panel_culvert)
        pos=(x,top_y if is_top else bottom_y,.437,
             (top_height if is_top else bottom_height)/height)
        ax=fig.add_axes(pos)
        ax._schematic_ylim=(low,5.8)
        func(ax,T[lang])
    return fig


def draw(lang):
    with drawing_style():
        fig=build(lang)
        return export(fig,out_path('structure_types',lang))
