"""fault2disp: upper-edge centre, strike/dip geometry and rake (JA / EN).

Rebuild: python docs/figs/make_guide_figs.py fault

Geometry follows utils/fault2disp/fault2disp.f90: segment_disp. ENU basis:
along strike = (sin(phi), cos(phi), 0); down dip =
(cos(phi)*cos(delta), -sin(phi)*cos(delta), -sin(delta)).
Positive rake rotates from along strike towards up dip on the fault plane,
consistent with u1=slip*cos(rake), u2=slip*sin(rake).
The diagram uses illustrative angles, not a computed displacement field.
Plan and section use their own uniform scales. d_top is measured from the
flat Okada reference surface; segment_disp does not sample terrain heights.
"""
from io import StringIO
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.patches import Polygon, Rectangle, FancyArrowPatch

from _schematic import drawing_style, text, block, line, arrow, INK, MUTED, RULE

DPI, WIDTH, HEIGHT = 150, 1800, 1100
BLUE, PURPLE, ORANGE = '#2a78d6', '#76579b', '#c45d2b'
STRIKE, DIP, RAKE = np.deg2rad([30., 35., 55.])
LENGTH, FAULT_WIDTH, TOP_DEPTH = 60000., 30000., 5000.


def basis(strike=STRIKE, dip=DIP):
    along = np.array([np.sin(strike), np.cos(strike), 0.])
    down = np.array([np.cos(strike)*np.cos(dip), -np.sin(strike)*np.cos(dip), -np.sin(dip)])
    return along, down


def geometry():
    along, down = basis()
    top = np.array([0., 0., -TOP_DEPTH])
    bottom = top + FAULT_WIDTH*down
    corners = np.array([top-LENGTH/2*along, top+LENGTH/2*along,
                        bottom+LENGTH/2*along, bottom-LENGTH/2*along])
    return top, bottom, corners


def dimension(ax, p, q, color=MUTED):
    a = FancyArrowPatch(p, q, arrowstyle='<->', mutation_scale=10,
                        color=color, lw=1, zorder=9)
    ax.add_patch(a)
    return a


def dot(ax, p, color, gid):
    ax.plot(*p, marker='o', markersize=6, color=color, zorder=12, gid=gid)


def arc_arrow(ax, origin, radius, start, end, color):
    angles=np.linspace(start,end,35)
    points=origin+radius*np.column_stack([np.cos(angles),np.sin(angles)])
    return arrow(ax,points,color,lw=1.3,size=9)


def build(lang):
    t=lambda ja,en:ja if lang=='ja' else en
    fig=plt.figure(figsize=(WIDTH/DPI,HEIGHT/DPI),dpi=DPI)
    ax=fig.add_axes([0,0,1,1])
    ax.set(xlim=(0,WIDTH),ylim=(HEIGHT,0));ax.axis('off')
    text(ax,55,36,t('fault2disp：断層の位置・向き・すべりを指定する',
                    'fault2disp: locate, orient and slip a fault'),20,weight='bold')
    text(ax,57,102,t('同じ矩形断層を、平面・断面・断層面の3方向から読む。',
                     'Read one rectangular fault in plan, cross-section and fault-plane views.'),12,color=MUTED)
    for x,label in [(60,t('(a)  平面図：位置と走向','(a)  Plan: location and strike')),
                    (650,t('(b)  断面図：深さと傾斜','(b)  Section: depth and dip')),
                    (1240,t('(c)  断層面：すべり角','(c)  Fault plane: rake'))]:
        text(ax,x,180,label,14,weight='bold')
    line(ax,[(610,180),(610,860)],RULE,.8)
    line(ax,[(1200,180),(1200,860)],RULE,.8)

    # Plan: rotate a rectangle with the same horizontal projection as the
    # implementation. P is the upper-edge centre, not the rectangle centre.
    top,bottom,corners=geometry()
    scale=310/LENGTH
    P=np.array([245.,480.])
    project=lambda pts:P+np.asarray(pts)[...,:2]*np.array([scale,-scale])
    poly=project(corners);Q=project(bottom)
    ax.add_patch(Polygon(poly,closed=True,fc='#f1edf6',ec=RULE,lw=1,gid='plan-projection'))
    line(ax,poly[:2],BLUE,3,gid='plan-upper-edge')
    line(ax,poly[2:],PURPLE,3,gid='plan-lower-edge')
    line(ax,[P,Q],MUTED,1,ls='--')
    dot(ax,P,BLUE,'plan-top-centre');dot(ax,Q,PURPLE,'plan-bottom-centre')
    line(ax,[P,P+[0,-200]],MUTED,1,ls='--')
    text(ax,245,245,t('N（格子北）','N (grid north)'),10.5,ha='center')
    along=np.array([np.sin(STRIKE),-np.cos(STRIKE)])
    down=np.array([np.cos(STRIKE),np.sin(STRIKE)])
    arrow(ax,[P,P+188*along],BLUE,lw=1.9)
    arc_arrow(ax,P,100,-np.pi/2,-np.pi/2+STRIKE,ORANGE)
    text(ax,268,353,'φ',13,color=ORANGE)
    text(ax,70,691,t('φ = strike：北から時計回り','φ = strike: clockwise from north'),10.5,color=ORANGE)
    dim=poly[:2]-43*down
    dimension(ax,*dim)
    line(ax,[poly[0],dim[0]],RULE,.8);line(ax,[poly[1],dim[1]],RULE,.8)
    text(ax,171,478,'flength',11,rotation=60,ha='center',va='center')
    direction_start=Q-57*along
    arrow(ax,[direction_start,direction_start+85*down],PURPLE)
    text(ax,416,632,t('下り傾斜','Down dip'),10.5,color=PURPLE)
    arrow(ax,[(87,322),(87,263)],MUTED,lw=1.1,size=8)
    arrow(ax,[(87,322),(150,322)],MUTED,lw=1.1,size=8)
    text(ax,72,233,'y / N',9,color=MUTED)
    text(ax,155,310,'x / E',9,color=MUTED)
    text(ax,262,454,'P',11,color=BLUE,weight='bold')
    block(ax,70,762,t('青点 P：上端の中心 (x_top, y_top)\n淡紫：断層面の水平投影',
                      'P (blue): upper-edge centre (x_top, y_top)\nPale fill: horizontal projection of the fault'),510,10.5)

    # Section normal to strike. Horizontal and vertical coordinates share
    # one scale; width is along the inclined plane, not its map projection.
    sec_scale=330/FAULT_WIDTH
    surface=330.
    A=np.array([780.,surface+TOP_DEPTH*sec_scale])
    B=A+FAULT_WIDTH*sec_scale*np.array([np.cos(DIP),np.sin(DIP)])
    ax.add_patch(Rectangle((650,surface),520,375,fc='#f6f3ec',ec='none',gid='section-ground'))
    line(ax,[(650,surface),(1170,surface)],MUTED,1.4)
    text(ax,663,293,t('Okada 計算の平坦な基準面','Flat reference surface for Okada'),10,color=MUTED)
    line(ax,[A,B],PURPLE,3,gid='section-fault')
    line(ax,[(A[0],surface),A],BLUE,.9,ls='--')
    line(ax,[(B[0],surface),B],MUTED,.9,ls='--')
    dot(ax,A,BLUE,'section-top-centre');dot(ax,B,PURPLE,'section-bottom-centre')
    dimension(ax,(712,surface),(712,A[1]))
    text(ax,699,349,'d_top',10.5,ha='right')
    line(ax,[A,A+[115,0]],MUTED,.9,ls='--')
    arc_arrow(ax,A,75,0,DIP,ORANGE)
    text(ax,874,405,'dip',11,color=ORANGE)
    normal=np.array([-np.sin(DIP),np.cos(DIP)])
    A2,B2=A+35*normal,B+35*normal
    dimension(ax,A2,B2)
    line(ax,[A,A2],RULE,.8);line(ax,[B,B2],RULE,.8)
    midpoint=(A2+B2)/2+20*normal
    text(ax,*midpoint,'fwidth',11,rotation=-35,ha='center',va='center')
    ydim=655
    line(ax,[A,(A[0],ydim)],RULE,.8,ls=':');line(ax,[B,(B[0],ydim)],RULE,.8,ls=':')
    dimension(ax,(A[0],ydim),(B[0],ydim))
    text(ax,(A[0]+B[0])/2,674,'fwidth × cos(dip)',10.5,ha='center')
    block(ax,650,762,t('下端深さ = d_top + fwidth × sin(dip)\n幅 fwidth は断層面に沿って測る。',
                       'Lower-edge depth = d_top + fwidth × sin(dip)\nfwidth is measured along the fault plane.'),520,10.5)

    # Fault-plane face view: along strike to the right, up dip upward.
    bottom_y=340+465*FAULT_WIDTH/LENGTH
    rect=np.array([[1270,340],[1735,340],[1735,bottom_y],[1270,bottom_y]])
    ax.add_patch(Polygon(rect,closed=True,fc='#f6f2fa',ec=RULE,lw=1,gid='rake-plane'))
    line(ax,rect[:2],BLUE,2.5);line(ax,rect[2:],PURPLE,2.5)
    text(ax,1495,284,t('上り傾斜（浅い側）','Up dip (shallower)'),10.5,ha='center',color=BLUE)
    O=np.array([1400.,540.])
    arrow(ax,[O,O+[290,0]],MUTED,lw=1.1,size=8)
    arrow(ax,[O,O+[0,-174]],MUTED,lw=1.1,size=8)
    text(ax,1675,595,t('走向方向','Along strike'),10.5,ha='right')
    text(ax,1367,372,'90°',10.5,ha='right',color=MUTED)
    text(ax,1700,528,'0°',10.5,color=MUTED)
    S=O+185*np.array([np.cos(RAKE),-np.sin(RAKE)])
    arrow(ax,[O,S],ORANGE,lw=2.7,size=14)
    text(ax,S[0]+18,S[1]+18,'slip',12,color=ORANGE,weight='bold')
    arc_arrow(ax,O,76,0,-RAKE,ORANGE)
    text(ax,1490,477,'rake',11,color=ORANGE)
    text(ax,1495,675,t('上盤の相対すべりを面内に描く','Relative hanging-wall slip in the plane'),10,ha='center')
    block(ax,1240,762,t('rake = 90°：逆断層（上り傾斜へ）\nrake = −90°：正断層（下り傾斜へ）',
                        'rake = 90°: reverse fault (up dip)\nrake = −90°: normal fault (down dip)'),520,10.5)

    ax.add_patch(Rectangle((60,891),1680,89,fc='#eff4fa',ec='none',gid='key-point'))
    text(ax,85,912,t('指定する位置は「上端の中心」。幅は地図上ではなく断層面に沿う長さ。',
                     'Locate the upper-edge centre. Measure width along the fault plane, not on the map.'),13,weight='bold')
    block(ax,60,1007,t('角度・寸法は説明用の模式例。変位分布や津波の計算結果ではない。\n経緯度入力の走向は真北基準。既定では投影後に格子北基準へ補正する。',
                       'Angles and dimensions are illustrative; this is not a displacement field or a tsunami result.\nFor longitude/latitude input, strike is relative to true north; by default it is corrected to grid north.'),1680,10.5,color=MUTED)
    return fig


def export(fig,lang):
    dest=Path(__file__).resolve().parents[1]/('fault_geometry'+('' if lang=='ja' else '_en'))
    fig.savefig(dest.with_suffix('.png'),dpi=DPI)
    svg=StringIO();fig.savefig(svg,format='svg',metadata={'Date':None})
    dest.with_suffix('.svg').write_text('\n'.join(s.rstrip() for s in svg.getvalue().splitlines())+'\n',encoding='utf-8',newline='\n')
    plt.close(fig)
    return str(dest.with_suffix('.png'))


def draw(lang):
    with drawing_style(): return export(build(lang),lang)
