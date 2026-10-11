"""淡塩2層(鋭利界面)の断面模式図: 地表の塩水層 hss・地下の塩水 zone hgs・海との接続(salt.md)。"""
from _style import *

T = {"ja": {
    "title": "淡塩2層(fn_salt): 合計 h・hg はそのまま、その内数として最下層の塩水層厚 hss・hgs を追跡する(鋭利界面)",
    "sea": "海域セル(sw > 0)\n全塩水・水位 = 潮位(fn_tide)", "land": "陸", "ground": "地表 z",
    "soil": "土層(帯水層: sd, sy0。f_gwlateral=1 が前提)", "fresh": "淡水(hg − hgs)", "saltgw": "地下の塩水 zone hgs(f_salt_gw=1)",
    "iface": "界面標高 ζ", "phi": "駆動水頭: 淡水 Φf = η、塩水 Φs = η + ε·ζ\nε = (salt_rhos − salt_rhof)/salt_rhof(既定 1025/1000 → 2.5 %)",
    "gh": "平衡界面は Ghyben-Herzberg 関係",
    "surf": "地表水 h", "hss": "地表の塩水層 hss(f_salt_surf=1)\n移流に相乗り(分担率 salt_alpha)+ 底層重力流(salt_ni)",
    "ex_gw": "塩水: 水頭差で双方向交換\n淡水: 海へ流出のみ",
    "ex_surf": "遡上した海水は塩水として追跡\n(海へ戻れば消える)",
    "init": "初期値: salt_hss0 / salt_hgs0(一様値かマップ)。出力 Hss・Hgs",
    "tide": "潮位 η_sea",
}, "en": {
    "title": "Fresh/salt two layers (fn_salt): h and hg stay totals; the salt-layer thicknesses hss, hgs are tracked as their lowest part (sharp interface)",
    "sea": "sea cells (sw > 0)\nall salt, level = tide (fn_tide)", "land": "land", "ground": "ground z",
    "soil": "soil layer (aquifer: sd, sy0; requires f_gwlateral=1)", "fresh": "fresh water (hg − hgs)", "saltgw": "subsurface salt zone hgs (f_salt_gw=1)",
    "iface": "interface elevation ζ", "phi": "driving heads: fresh Φf = η, salt Φs = η + ε·ζ\nε = (salt_rhos − salt_rhof)/salt_rhof (default 1025/1000 -> 2.5 %)",
    "gh": "equilibrium interface: Ghyben-Herzberg relation",
    "surf": "surface water h", "hss": "surface salt layer hss (f_salt_surf=1)\nrides on advection (share salt_alpha) + bottom gravity current (salt_ni)",
    "ex_gw": "salt: two-way exchange by head difference\nfresh: outflow to sea only",
    "ex_surf": "run-up seawater is tracked as salt\n(vanishes when it returns to sea)",
    "init": "initial: salt_hss0 / salt_hgs0 (uniform or map). Output Hss, Hgs",
    "tide": "tide η_sea",
}}

from _schematic import (drawing_style, text, block, paragraph, line, curve,
    arrow as flow_arrow, water as wet_water, monotone_cubic, export, INK, MUTED, RULE)
import numpy as np

COAST = 7.6
TIDE = 2.0
POND_LEVEL = 3.12
POND_INTERFACE = 2.87
POND_BOUNDS = (.6, 3.4)


def profiles():
    """Shared schematic curves, not a model run or an equilibrium solution.

    The local surface depression is part of the ground. Bedrock follows the
    broader coastal slope, so the illustrative soil thickness varies locally.
    hgs is storage: no misleading geometric 'hgs' dimension line is drawn.
    """
    knots=np.array([0.,.6,2.,3.4,4.5,6.5,COAST,9.,11.6])
    gvals=np.array([3.45,3.40,2.65,3.40,2.72,2.20,TIDE,1.55,1.4])
    x=np.unique(np.r_[np.linspace(0,11.6,1601),knots,2.0])
    ground=monotone_cubic(knots,gvals,x)
    bx=np.array([0.,2.,4.5,6.5,COAST,9.,11.6])
    bz=np.array([.9,.75,.45,.15,0.,-.45,-.6])
    base=monotone_cubic(bx,bz,x)
    land=x<=COAST
    wx=np.array([0.,2.,4.5,6.5,COAST])
    wz=np.array([2.65,2.43,2.35,2.10,TIDE])
    wt=monotone_cubic(wx,wz,x[land])
    fraction=np.clip((x[land]-2.0)/(COAST-2.0),0,1)**1.75
    interface=base[land]+fraction*(wt-base[land])
    return x,ground,base,land,wt,interface


def build(lang):
    if lang not in T: raise ValueError('lang must be ja or en')
    t=T[lang];ja=lang=='ja'
    fig=plt.figure(figsize=(13.2,9.2))
    ax=fig.add_axes([.052,.045,.906,.910])
    ax.set_xlim(-.10,11.80);ax.set_ylim(-3.88,4.52);ax.set_aspect('equal');ax.axis('off')
    block(ax,0,4.42,t['title'],11.6,size=10.5,weight='bold')
    x,g,b,land,wt,zi=profiles()
    xl=x[land]
    # Solid ground and aquifer; all shared boundaries use exactly these arrays.
    ax.add_patch(Polygon(list(zip(x,b))+[(11.6,-.93),(0,-.93)],
                          fc='#d9d8d3',ec='none',zorder=1))
    ax.add_patch(Polygon(list(zip(x,g))+list(zip(x[::-1],b[::-1])),
                          fc='#e0cba1',ec='none',zorder=2))
    # Fresh water and salt do not overlap; the sharp interface is drawn once.
    ax.add_patch(Polygon(list(zip(xl,wt))+list(zip(xl[::-1],zi[::-1])),
                          fc=C_WATER_L,ec='none',zorder=3))
    sx=np.r_[xl[xl>=2.],x[x>COAST]]
    sz=np.r_[zi[xl>=2.],np.full(np.count_nonzero(x>COAST),TIDE)]
    sb=np.interp(sx,x,b)
    ax.add_patch(Polygon(list(zip(sx,sz))+list(zip(sx[::-1],sb[::-1])),
                          fc=C_SEA,ec='none',zorder=3))
    line(ax,list(zip(xl,wt)),C_C,1.15,z=5)
    line(ax,list(zip(xl[xl>=2.],zi[xl>=2.])),'#1c4f8a',1.45,z=6)
    line(ax,[(COAST,TIDE),(11.6,TIDE)],C_C,1.3,z=6)
    # Pond: both water layers are clipped to the same depression, with exact roots.
    wet_water(ax,x,g,POND_LEVEL,C_WATER_L,C_WATER,*POND_BOUNDS,zorder=4)
    wet_water(ax,x,g,POND_INTERFACE,C_SEA,'#1c4f8a',*POND_BOUNDS,zorder=5)
    line(ax,list(zip(x,g)),C_GROUND,1.25,z=7)
    line(ax,list(zip(x,b)),MUTED,.90,z=5)
    # Clear, short labels on the geometry. The full parameter text is below it.
    text(ax,2.0,3.71,t['surf'],size=10,ha='center',color=C_C)
    text(ax,2.0,2.785,'hss',size=9.0,ha='center',va='center',color='white')
    text(ax,1.30,1.92,t['fresh'],size=10,color=C_C)
    text(ax,5.65,.63,'hgs',size=10.5,color='white')
    text(ax,9.45,.36,'hgs = hg',size=9.8,color='white')
    text(ax,.05,3.29,t['land'],size=8.8,color=MUTED)
    text(ax,4.13,3.39,t['ground'],size=9.2,color=C_GROUND)
    line(ax,[(4.52,3.12),(4.57,float(np.interp(4.57,x,g)))],C_GROUND,.8,z=8)
    text(ax,4.15,1.53,t['iface'],size=9.6,color='#1c4f8a')
    xe=5.05;ze=float(np.interp(xe,xl,zi))
    line(ax,[(4.87,1.30),(xe,ze)],'#1c4f8a',.8,z=8)
    block(ax,8.77,3.58,t['sea'],2.7,size=9.4,color=C_C)
    text(ax,11.46,TIDE+.12,t['tide'],size=9.1,ha='right',va='bottom',color=C_C)
    # Exchange arrows show process directions, not computed trajectories.
    flow_arrow(ax,curve((6.1,1.92),[
        ('C',(6.65,1.98),(7.18,2.0),(COAST,TIDE)),
        ('C',(7.94,TIDE),(8.14,1.87),(8.53,1.87))]),C_C,1.65,size=11)
    flow_arrow(ax,[(8.25,.98),(7.03,.98)],C_X,1.75,size=11)
    flow_arrow(ax,[(7.03,.64),(8.25,.64)],C_X,1.75,size=11)
    flow_arrow(ax,curve((8.04,2.53),[
        ('C',(7.44,2.86),(6.80,3.22),(5.35,3.23))]),C_X,1.45,ls='--',size=10)
    text(ax,6.76,3.58,'海水の遡上' if ja else 'seawater run-up',
         size=9.2,ha='center',color=C_X)
    # Notes no longer cross soil, interface, shoreline or flow arrows.
    line(ax,[(0,-1.14),(11.60,-1.14)],RULE,.75,z=1)
    y=-1.43
    left=paragraph(ax,0,y,t['hss'],3.60,size=8.7,color='#1c4f8a',gap=.22)
    left=paragraph(ax,0,left,t['saltgw'],3.60,size=8.7,color='#1c4f8a',gap=.22)
    paragraph(ax,0,left,t['soil'],3.60,size=8.5,color=MUTED,gap=.20)
    middle=paragraph(ax,4.04,y,t['phi'],3.66,size=8.7,gap=.22)
    paragraph(ax,4.04,middle,t['gh'],3.66,size=8.5,color=MUTED)
    right=paragraph(ax,8.11,y,t['ex_gw'],3.49,size=8.7,color=C_X,gap=.22)
    paragraph(ax,8.11,right,t['ex_surf'],3.49,size=8.7,color=C_X)
    paragraph(ax,0,-3.40,t['init'],11.60,size=8.4,color=MUTED)
    text(ax,11.6,-3.83,'模式図：形状・縮尺は概念的（平衡解ではない）' if ja else
         'Schematic geometry; not to scale or an equilibrium solution.',size=7.8,
         color=MUTED,ha='right',va='bottom')
    return fig


def draw(lang):
    with drawing_style():
        return export(build(lang),out_path('salt_layers',lang))
