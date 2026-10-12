"""Groundwater storage and exchange: a shallow section and a conduit schematic.

The section illustrates Green-Ampt + lateral flow + optional layer 2. The
separate conduit panel is an equivalent-continuum connection diagram, not a
third geological stratum or a resolved pipe/well network. See m_gwflow*.f90.
"""
from pathlib import Path as FilePath
import numpy as np
from _style import *
from _schematic import (drawing_style, text, block, paragraph, line,
                        arrow as flow_arrow, curve, export, INK, MUTED, RULE)

T = {
    'ja': dict(
        title='地下水の貯留と交換経路',
        subtitle='土層・任意の風化基岩層に、管路連続体と揚水を追加  |  fn_gwflow / &list_gwflow',
        a='(a) 浅層地下水の断面例',
        a_sub='Green-Ampt + 側方流 + 風化基岩層',
        b='(b) 管路連続体の交換関係',
        b_sub='f_gwconduit = 1（任意）',
        surf='地表水 h', soil='土層', layer2='層2', base='基盤',
        infil='鉛直浸透', lateral='側方流', down='層1 → 2',
        up='容量超過\n層1へ戻る', seep='湧出', pump='揚水 → 系外\n（土層からの例）',
        sat_depth='飽和帯厚',
        surface_node='地表水 h', conduit_node='管路連続体 hgc',
        neighbour='隣接セル', eight='8近傍', inlet='流入', surcharge='噴出',
        leak='水頭差で\n双方向交換', selected='交換相手を選択\n土層 hg または 層2 hg2',
        outlet='吐口の受け先\n海隣接: 海（系外）\nそれ以外: 自セル地表',
        outflow='吐口放流',
        store_head='1  貯留量と飽和帯の厚さ',
        store='hg・hg2・hgc は水量をセル面積で割った柱状換算水深。\n飽和帯厚は hg / sy0、hg2 / gw2_sy。青い帯はこの厚さを示す。\n土層容量 = sd × sy0（sd・sy0 は &list_geoinfo）。',
        soil_head='2  浸透・側方流と凍土',
        soil_note='f_gwvertical=2: Green-Ampt。f_gwlateral=1: 水頭差で動く8近傍流。\n土層の容量超過分は地表へ湧出する。\nf_gwfrost=1: 気温から凍結指数を求め、鉛直浸透能だけを低減。\nバケツ（f_gwvertical=1）は側方流・層2と併用しない別構成。',
        layer_head='3  風化基岩層・揚水（任意）',
        layer_note='f_gwlayer2=1: 層1 → 2 に浸透し、層2の容量超過分は層1へ戻す。\n容量 = gw2_depth × gw2_sy。gw2_ksh_mmh=0 なら層2の側方流なし。\nf_gwpump=1: 井戸ごとに土層 / 層2 を選び、貯留量を上限に系外へ取水。\n井戸孔の水理は解かない。',
        conduit_head='4  任意に重ねる等価連続体',
        conduit_note='下水道網・岩盤亀裂網などをセル別の容量と通水能で表す。\n管路水頭 H_c は貯留 hgc、容量 cap（gwc_cap）、管底と貯留係数で決まる。\n容量超過分も層内に保持（被圧）。側方通水は8方向の水頭差で駆動。\nf_gwc_fluxlaw: 1 = 線形、2 = sqrt。',
        exchange_head='5  枡・吸込穴からの地表交換',
        exchange_note='gwc_inlet（または分布マップ）が正のセルで有効。\n流入: 地表に水があり H_s > H_c。不圧は堰式、満管はオリフィス式。\n噴出: hgc > cap かつ H_c > H_s（オリフィス式）。H_s = z + h。',
        out_head='6  地下層との交換・吐口',
        out_note='gwc_leak_layer=1 / 2 で交換相手の土層 / 層2 を選び、水頭差で双方向交換。\n吐口 fn_gwc_outfall は受け先より管路水頭が高いときだけ放流。\n海隣接なら海へ系外排出、それ以外は自セルの地表水へ戻す。\n吐口は不圧・被圧のどちらでも働く（逆流なし）。',
        foot='模式図・縮尺任意。矢印は交換経路を示す。管路図の位置・大きさは、埋設深・実管径・必須の地層を意味しない。',
    ),
    'en': dict(
        title='Groundwater storage and exchange pathways',
        subtitle='Soil and optional weathered bedrock, with conduit storage and pumping  |  fn_gwflow / &list_gwflow',
        a='(a) Example shallow-groundwater section',
        a_sub='Green-Ampt + lateral flow + weathered bedrock',
        b='(b) Conduit-continuum exchanges',
        b_sub='f_gwconduit = 1 (optional)',
        surf='surface water h', soil='soil', layer2='layer 2', base='base',
        infil='infiltration', lateral='lateral flow', down='layer 1 → 2',
        up='overflow\nto layer 1', seep='exfiltration', pump='pumping → outside\n(soil-layer example)',
        sat_depth='saturated\nthickness',
        surface_node='surface water h', conduit_node='conduit storage hgc',
        neighbour='neighbour', eight='8 neighbours', inlet='inflow', surcharge='surcharge',
        leak='head-driven\nexchange', selected='choose one partner\nsoil hg or layer 2 hg2',
        outlet='outfall destination\nsea neighbour: sea (outside)\notherwise: own surface cell',
        outflow='outfall',
        store_head='1  Stored water versus saturated thickness',
        store='hg, hg2 and hgc are water volume divided by cell area.\nSaturated thickness = hg / sy0 or hg2 / gw2_sy, shown by the blue bands.\nSoil capacity = sd × sy0 (sd and sy0 are set in &list_geoinfo).',
        soil_head='2  Infiltration, lateral flow and frozen ground',
        soil_note='f_gwvertical=2: Green-Ampt. f_gwlateral=1: head-driven, 8-neighbour flow.\nSoil storage above capacity returns to the surface.\nf_gwfrost=1: air-temperature freezing index reduces vertical infiltration only.\nThe bucket (f_gwvertical=1) is an alternative, incompatible with lateral flow / layer 2.',
        layer_head='3  Weathered bedrock and pumping (optional)',
        layer_note='f_gwlayer2=1: infiltration from layer 1; excess storage returns to layer 1.\nCapacity = gw2_depth × gw2_sy. gw2_ksh_mmh=0 disables layer-2 lateral flow.\nf_gwpump=1: each well abstracts from soil OR layer 2, limited by stored water.\nWater leaves the system; borehole-scale hydraulics are not resolved.',
        conduit_head='4  An optional equivalent continuum',
        conduit_note='Sewer or fracture networks are represented by cell capacity and conveyance.\nConduit head H_c depends on hgc, cap (gwc_cap), invert and storage coefficients.\nExcess storage is retained under pressure. Lateral flow follows head differences\nin 8 directions. f_gwc_fluxlaw: 1 = linear, 2 = sqrt.',
        exchange_head='5  Surface exchange through inlets',
        exchange_note='Active where gwc_inlet (or its map) is positive.\nInflow: surface water present and H_s > H_c; weir if unfilled, orifice if full.\nSurcharge: hgc > cap AND H_c > H_s (orifice). Surface head H_s = z + h.',
        out_head='6  Groundwater exchange and outfalls',
        out_note='gwc_leak_layer=1 / 2 selects soil / layer 2 for head-driven, two-way exchange.\nOutfalls (fn_gwc_outfall) discharge only when conduit head exceeds receiving head.\nWith a sea neighbour: water leaves to sea; otherwise: to its own surface cell.\nOutfalls work in both unpressurized and pressurized states; no reverse flow.',
        foot='Schematic, not to scale. Arrows show exchange routes. Conduit-box positions and sizes do not represent burial depth, pipe diameter or required geological strata.',
    ),
}

# One geometric definition for all faces. Values are conceptual, not inputs.
SOIL_DEPTH, ROCK_DEPTH, END = 1.35, 1.55, 9.6
GREEN = '#51813b'
SOIL_FILL, ROCK_FILL = '#dfcba3', '#d4d2cd'
WATER2 = '#bcd3ee'


def surface(x):
    return 5.0-.20*np.asarray(x, float)


def smoothstep(x):
    u = np.clip(x, 0, 1)
    return u*u*(3-2*u)


def saturated_thickness(x):
    # Saturation is reached before the upward/exfiltration arrows.
    x = np.asarray(x, float)
    return .50+.85*smoothstep(x/8.4), .70+.85*smoothstep(x/7.4)


def profiles():
    x = np.unique(np.round(np.r_[np.linspace(0, END, 961), 7.4, 7.85, 8.4, 8.9], 10))
    ground = surface(x)
    soil_bottom = ground-SOIL_DEPTH
    rock_bottom = soil_bottom-ROCK_DEPTH
    h1, h2 = saturated_thickness(x)
    return x, ground, soil_bottom, rock_bottom, soil_bottom+h1, rock_bottom+h2


def _axes(fig, box, xlim=(0, 1), ylim=(0, 1)):
    ax = fig.add_axes(box)
    ax.set(xlim=xlim, ylim=ylim)
    ax.axis('off')
    return ax


def _dimension(ax, x, z0, z1, label):
    ax.annotate('', (x, z1), (x, z0), arrowprops=dict(
        arrowstyle='<->', color=C_C, lw=.8, shrinkA=0, shrinkB=0,
        mutation_scale=8), zorder=10)
    for z in (z0, z1):
        line(ax, [(END, z), (x+.08, z)], C_C, .55)
    text(ax, x+.23, (z0+z1)/2, label, size=8.4, color=C_C, va='center')


def section(ax, t):
    x, z, b1, b2, w1, w2 = profiles()
    ax.fill_between(x, b1, z, color=SOIL_FILL, lw=0, zorder=1)
    ax.fill_between(x, b2, b1, color=ROCK_FILL, lw=0, zorder=1)
    ax.fill_between(x, b2-.25, b2, color='#b8b5ad', lw=0, zorder=1)
    ax.fill_between(x, b1, w1, color=C_WATER_L, lw=0, zorder=2)
    ax.fill_between(x, b2, w2, color=WATER2, lw=0, zorder=2)
    ax.fill_between(x, z, z+.13, color=C_WATER_L, lw=0, zorder=3)
    for y, color, width in [(z, INK, 1.15), (b1, C_GROUND, 1.0),
                             (b2, C_GROUND, 1.0), (w1, C_C, .9), (w2, C_C, .9),
                             (z+.13, C_C, 1.)]:
        line(ax, np.c_[x, y], color, width)
    text(ax, .12, 5.43, t['surf'], size=9, color=C_C)
    text(ax, .13, 4.69, t['soil'], size=9.4, color='#70501f')
    text(ax, .13, 3.31, t['layer2'], size=9.2, color=MUTED)
    text(ax, .14, 1.70, t['base'], size=8.2, color=MUTED)
    text(ax, .40, 3.82, 'hg', size=9.3, color=C_C)
    text(ax, .42, 2.65, 'hg2', size=9.3, color=C_C)
    # Infiltration crosses the surface into layer-1 storage.
    xv = 1.15
    h1, _ = saturated_thickness(xv)
    flow_arrow(ax, [(xv, float(surface(xv))+.14),
                    (xv, float(surface(xv))-SOIL_DEPTH+float(h1)*.65)], C_X, 1.8)
    text(ax, 1.70, 5.07, t['infil'], size=9.1, color=C_X)
    # Both lateral arrows lie inside their own saturated bands.
    for depth, band in [(SOIL_DEPTH, 0), (SOIL_DEPTH+ROCK_DEPTH, 1)]:
        fx = np.linspace(3.1, 5.6, 120)
        h = saturated_thickness(fx)[band]
        flow_arrow(ax, np.c_[fx, surface(fx)-depth+.45*h], C_C, 1.7)
    text(ax, 3.20, 3.69, t['lateral'], size=8.8, color=C_C)
    text(ax, 3.18, 2.25, t['lateral'], size=8.8, color=C_C)
    # Downward percolation and capacity overflow have different rules.
    xv = 1.85
    boundary = float(surface(xv))-SOIL_DEPTH
    flow_arrow(ax, [(xv, boundary+.12), (xv, boundary-.71)], C_X, 1.6)
    text(ax, 2.10, 3.00, t['down'], size=8.6, color=C_X)
    xv = 7.85
    boundary = float(surface(xv))-SOIL_DEPTH
    flow_arrow(ax, [(xv, boundary-.60), (xv, boundary+.25)], GREEN, 1.7)
    text(ax, 7.60, 1.75, t['up'], size=8.6, color=GREEN, ha='right')
    xv = 8.9
    ground = float(surface(xv))
    flow_arrow(ax, [(xv, ground-.78), (xv, ground+.47)], GREEN, 1.8)
    text(ax, 8.25, 4.10, t['seep'], size=8.8, color=GREEN)
    # A sink arrow, not a borehole with simultaneous screens in two layers.
    xv = 6.45
    h1, _ = saturated_thickness(xv)
    intake = float(surface(xv))-SOIL_DEPTH+float(h1)*.42
    ax.add_patch(Circle((xv, intake), .07, fc='white', ec=C_X, lw=1.1, zorder=11))
    flow_arrow(ax, [(xv, intake+.09), (xv, float(surface(xv))+.82)], C_X, 1.6)
    text(ax, 5.32, 5.17, t['pump'], size=8.8, color=C_X)
    text(ax, 10.00, 3.90, t['sat_depth'], size=8.5, color=MUTED)
    _dimension(ax, 9.96, b1[-1], w1[-1], 'hg / sy0')
    _dimension(ax, 9.96, b2[-1], w2[-1], 'hg2 /\ngw2_sy')


# A graph of storage/exchange, with explicit node rectangles and boundary ports.
NODES = {
    'surface': (.35, 4.90, 9.70, .80),
    'conduit': (2.90, 2.65, 4.15, 1.10),
    'neighbour': (8.02, 2.65, 2.03, 1.10),
    'soil': (.35, .35, 4.50, 1.05),
    'outlet': (5.25, .35, 4.80, 1.25),
}


def _node(ax, key, label, fill, color=INK, size=9.1):
    x, y, w, h = NODES[key]
    ax.add_patch(Rectangle((x, y), w, h, fc=fill, ec=RULE, lw=1., zorder=3))
    text(ax, x+w/2, y+h/2, label, size=size, color=color, ha='center', va='center')


def conduit(ax, t):
    _node(ax, 'surface', t['surface_node']+'\n'+r'$H_s = z+h$', C_WATER_L, C_C, 9.2)
    _node(ax, 'conduit', t['conduit_node']+'\n'+r'$H_c$', '#edf1f5', C_C, 9.2)
    _node(ax, 'neighbour', t['neighbour']+'\nhgc', '#edf1f5', C_C, 8.4)
    _node(ax, 'soil', t['selected'], '#f2ebdf', size=8.6)
    _node(ax, 'outlet', t['outlet'], '#edf3e9', GREEN, 8.2)
    # Two opposed arrows show alternative exchange directions.
    flow_arrow(ax, [(3.60, 4.90), (3.60, 3.75)], C_X, 1.6)
    text(ax, 2.22, 4.41, t['inlet'], size=8.6, color=C_X, ha='right')
    flow_arrow(ax, [(6.15, 3.75), (6.15, 4.90)], GREEN, 1.6)
    text(ax, 6.49, 4.41, t['surcharge'], size=8.6, color=GREEN)
    ax.annotate('', (8.02, 3.20), (7.05, 3.20), arrowprops=dict(
        arrowstyle='<->', color=C_C, lw=1.3, shrinkA=0, shrinkB=0), zorder=10)
    text(ax, 8.02, 4.0, t['eight'], size=8.1, color=C_C, ha='center')
    ax.annotate('', (3.30, 2.65), (3.30, 1.40), arrowprops=dict(
        arrowstyle='<->', color=MUTED, lw=1.2, shrinkA=0, shrinkB=0), zorder=10)
    text(ax, 2.79, 2.30, t['leak'], size=8.3, color=MUTED, ha='right')
    flow_arrow(ax, curve((6.05, 2.65), [
        ('C', (6.05, 2.13), (7.60, 2.13), (7.60, 1.60))]), GREEN, 1.5)
    text(ax, 8.04, 2.23, t['outflow'], size=8.3, color=GREEN)


def _heading(ax, y, s, color):
    a = block(ax, 0, y, s, 1, size=9.4, color=color, weight='bold')
    ax.figure.canvas.draw()
    return ax.transData.inverted().transform(
        (0, a.get_window_extent(ax.figure.canvas.get_renderer()).y0))[1]-.022


def build(lang):
    if lang not in T:
        raise ValueError('lang must be ja or en')
    t = T[lang]
    fig = plt.figure(figsize=(13.6, 9.7))
    header = _axes(fig, [.04, .931, .92, .056])
    block(header, 0, 1, t['title'], 1, size=14.2, weight='bold')
    text(header, 0, .36, t['subtitle'], size=8.7, color=MUTED)
    for left, width, title, sub in [(.04, .54, 'a', 'a_sub'), (.625, .335, 'b', 'b_sub')]:
        head = _axes(fig, [left, .858, width, .057])
        block(head, 0, 1, t[title], 1, size=10.4, weight='bold')
        text(head, 0, .39, t[sub], size=8.4, color=MUTED)
    sec = _axes(fig, [.04, .445, .54, .403], (-.15, 12.7), (-.16, 6.40))
    section(sec, t)
    conn = _axes(fig, [.625, .445, .335, .403], (0, 10.5), (0, 6.40))
    conduit(conn, t)
    for left, entries in [
            (.04, [('store_head', 'store', C_C), ('soil_head', 'soil_note', C_X),
                   ('layer_head', 'layer_note', GREEN)]),
            (.52, [('conduit_head', 'conduit_note', C_C), ('exchange_head', 'exchange_note', C_X),
                   ('out_head', 'out_note', GREEN)])]:
        notes = _axes(fig, [left, .074, .44, .334])
        line(notes, [(0, 1.035), (1, 1.035)], RULE, .8, clip_on=False)
        y = 1.
        for title, body, color in entries:
            y = _heading(notes, y, t[title], color)
            y = paragraph(notes, 0, y, t[body], 1, size=8.6, gap=.038)
    footer = _axes(fig, [.04, .018, .92, .035])
    line(footer, [(0, 1.13), (1, 1.13)], RULE, .8, clip_on=False)
    block(footer, 0, 1, t['foot'], 1, size=8., color=MUTED)
    return fig


def draw(lang):
    with drawing_style():
        png = export(build(lang), out_path('gwflow_layers', lang))
        svg = FilePath(png).with_suffix('.svg')
        svg.write_bytes(svg.read_bytes().replace(b'\r\n', b'\n'))
        return png
