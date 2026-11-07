"""Limestone dissolution f_dissol (geomorph.md): which water dissolves rock, the update
of z and sd, and lateral dissolution of ponded depressions.

(a) the water sources dissol_src = 1..5 and the sink term on a karst section;
(b) dissolved thickness w and the update z, sd (residue, talus first);
(c) lateral dissolution dissol_lat: split between floor and walls, and the
shapes it leads to. Schematic, not solver output.

Generate: python docs/figs/make_guide_figs.py geomorph_dissol
"""
import numpy as np
from _geomorph import (canvas, header, panel, rule, box, poly, dim, badge, columns, run,
                       text, block, line, arrow, INK, MUTED, RULE,
                       SOIL, WATER, BLUE, SED, GREEN, TALUS, ORANGE, PANEL)

H = 1010
LIME, CONDUIT = '#c9cfd6', '#7fa7c9'

T = {
 'ja': {
    'title': '石灰岩の溶食  |  溶かす水の選び方・z と sd の更新・側方溶食(f_dissol)',
    'sub': '化学的削剥。土砂を出さず z を下げる(風化 f_wthr の対)。溶食の化学(炭酸平衡・温度)は解かず、有効溶解能 dissol_ceq を与える。断面は説明用。',
    'a': '(a) 溶かす水の量  dissol_src と吸込穴の項',
    'rain': '降雨(遮断後)', 'soil': '土層 sd', 'lime': '石灰岩', 'conduit': '管路連続体層(f_gwconduit)',
    'bare': '裸岩(sd < dissol_sdsurf)', 'sink': '吸込穴(枡)',
    'src': [('1', '浸透量(地下水モジュールの鉛直交換。fn_gwflow が必要)'),
            ('2', '地上降雨量(地下水なしで動く最大削剥速度のモデル)'),
            ('3', '1 + 裸岩で発生する流出水 × dissol_fsurf'),
            ('4', '岩への涵養(土層・層 2 → 管路層。管路の水頭が高い所では止まる)'),
            ('5', '4 + 裸岩の流出水(管路層のある計算では 4・5)')],
    'sinkt': 'dissol_sink = 1: 吸込穴への流入水 × dissol_fsink をそのセルに加える\n(窪みが深まる → 湛水が増える → 流入が増える、の正帰還でドリーネ)',
    'b': '(b) 溶ける厚さと更新',
    'eq': 'w = (dissol_ceq / dissol_rho) × f_sol × (F_r + f_sink F_sink) × morfac',
    'eqn': 'F_r: 更新間隔に積算した水量 (m)、f_sol: fn_dissol の可溶率\n既定 100 mg/L ÷ 2500 kg/m³ = 水 1 m あたり 4×10⁻⁵ m\n(涵養 1 m/yr で 40 mm/kyr)',
    'before': '前', 'after': '後', 'zdown': 'z が (1 − f_res) w 下がる', 'res': '残渣 f_res w が sd に残る\n(dissol_fres。テラロッサ)',
    'talus': '崖錐 ht があれば先に崖錐を溶かす(f_rockfall 併用時)',
    'c': '(c) 側方溶食  dissol_lat — 湛水セルの溶解能を床と岩壁に配る',
    'wall': '岩壁: 床が水面 e_w より\n高い隣接セル', 'floor': '床', 'pond': '湛水 h',
    'share': '壁へ p\n(接触幅 L_k の比で配る)\n床へ 1 − p',
    'auto': 'dissol_lat = −1(推奨):\np = h ΣL / (h ΣL + Δx²)\n= 濡れ面の面積比。深い湛水ほど\n壁の分け前が増える',
    'p0': 'p = 0: 吸込穴のセルが幅 1 セルの深い穴になる', 'p1': 'p > 0: 集水の大きい窪みほど広く深い漏斗形(窪みの併合 = コックピット、塔の裾の後退)',
    'foot': '流下に伴う飽和、陥没ドリーネ・洞窟の幾何は扱わない。深さ 10 m 級のドリーネには 100 kyr 級の地形時間(morfac × リスタート連鎖)が要る。',
 },
 'en': {
    'title': 'Limestone dissolution  |  Which water dissolves, update of z and sd, lateral dissolution (f_dissol)',
    'sub': 'Chemical denudation: lowers z without producing sediment (the counterpart of f_wthr). The carbonate chemistry is not solved; give the effective solubility dissol_ceq. Illustrative.',
    'a': '(a) Amount of dissolving water  dissol_src and the sink term',
    'rain': 'rain (after interception)', 'soil': 'soil sd', 'lime': 'limestone', 'conduit': 'conduit continuum layer (f_gwconduit)',
    'bare': 'bare rock (sd < dissol_sdsurf)', 'sink': 'sink inlet',
    'src': [('1', 'infiltration (vertical exchange of the groundwater module; needs fn_gwflow)'),
            ('2', 'rainfall at the ground (a maximum-denudation model that runs without groundwater)'),
            ('3', '1 + runoff generated on bare rock × dissol_fsurf'),
            ('4', 'recharge to the rock (soil/layer 2 → conduit layer; stops where the conduit head is higher)'),
            ('5', '4 + bare-rock runoff (use 4 or 5 with a conduit layer)')],
    'sinkt': 'dissol_sink = 1: inflow to sink inlets × dissol_fsink is added to that cell\n(deeper hollow → more ponding → more inflow: the feedback that makes dolines)',
    'b': '(b) Dissolved thickness and update',
    'eq': 'w = (dissol_ceq / dissol_rho) × f_sol × (F_r + f_sink F_sink) × morfac',
    'eqn': 'F_r: water summed over the update interval (m); f_sol: solubility map fn_dissol\ndefault 100 mg/L ÷ 2500 kg/m³ = 4×10⁻⁵ m per m of water\n(1 m/yr of recharge gives 40 mm/kyr)',
    'before': 'before', 'after': 'after', 'zdown': 'z drops by (1 − f_res) w', 'res': 'residue f_res w stays in sd\n(dissol_fres; terra rossa)',
    'talus': 'talus ht, if present, dissolves first (with f_rockfall)',
    'c': '(c) Lateral dissolution  dissol_lat — the solvent of a ponded cell is split between floor and walls',
    'wall': 'wall: neighbour whose floor\nis above the water surface e_w', 'floor': 'floor', 'pond': 'ponded h',
    'share': 'to the walls: p\n(split by contact widths L_k)\nto the floor: 1 − p',
    'auto': 'dissol_lat = −1 (recommended):\np = h ΣL / (h ΣL + Δx²)\n= wetted-area ratio;\ndeeper ponds give the walls\na larger share',
    'p0': 'p = 0: a sink cell becomes a deep one-cell hole', 'p1': 'p > 0: wider, deeper funnels where the catchment is larger (merging = cockpits; tower feet retreat)',
    'foot': 'No saturation along the flow path and no collapse dolines or cave geometry. A 10 m deep doline needs ~100 kyr of landform time (morfac × restart chains).',
 },
}


def panel_sources(ax, t):
    panel(ax, 35, 108, t['a'])
    x0, x1 = 50, 760
    xs = np.array([50, 160, 200, 250, 300, 345, 390, 470, 560, 640, 760])
    zs = np.array([215, 215, 232, 250, 282, 300, 282, 248, 228, 222, 222])
    sd = np.array([28, 28, 26, 22, 0, 0, 0, 0, 4, 22, 24])
    poly(ax, list(zip(xs, zs)) + [(x1, 420), (x0, 420)], LIME, z=1)
    poly(ax, list(zip(xs, zs)) + list(zip(xs[::-1], (zs + sd)[::-1])), SOIL, z=2)
    line(ax, list(zip(xs, zs)), INK, 1.1, z=6)
    # Conduit layer and the sink inlet at the floor of the hollow.
    box(ax, x0, 372, x1 - x0, 18, face=CONDUIT, edge='none', z=2)
    poly(ax, [(338, 300), (352, 300), (350, 372), (340, 372)], CONDUIT, z=3)
    arrow(ax, [(345, 318), (345, 368)], BLUE, lw=1.4, size=9)
    # Pond in the hollow.
    poly(ax, [(318, 291), (372, 291), (345, 300)], WATER, z=4)
    for xr in np.arange(70, 740, 38):
        zr = float(np.interp(xr, xs, zs))
        line(ax, [(xr + 5, zr - 50), (xr, zr - 28)], BLUE, .9)
    text(ax, 52, 142, t['rain'], size=8.2, color=BLUE)
    for xr in (90, 130, 660, 700):
        arrow(ax, [(xr, 222), (xr, 262)], BLUE, lw=1.0, size=7)
    for xr in (110, 680):
        arrow(ax, [(xr, 272), (xr, 366)], BLUE, lw=1.0, size=7, ls='--')
    arrow(ax, [(420, 258), (382, 284)], BLUE, lw=1.2, size=8)
    arrow(ax, [(468, 244), (432, 252)], BLUE, lw=1.2, size=8)
    badge(ax, 72, 245, '1', r=9, size=7.2)
    badge(ax, 205, 190, '2', r=9, size=7.2)
    badge(ax, 452, 228, '3', r=9, size=7.2)
    badge(ax, 132, 318, '4', r=9, size=7.2)
    text(ax, 560, 300, t['lime'], size=8.0, color='#4f5a66')
    text(ax, 580, 236, t['soil'], size=8.0, color='#7a5e2a')
    text(ax, 470, 380, t['conduit'], size=7.8, color='#1f4f75', va='center')
    text(ax, 472, 197, t['bare'], size=7.8, color=INK)
    text(ax, 362, 322, t['sink'], size=7.8, color=BLUE)
    y = 436
    for k, (n, s) in enumerate(t['src']):
        badge(ax, 62, y + 9, n, r=9, size=7.2)
        a = block(ax, 80, y, s, 690, size=8.0)
        y += 21 * (a.get_text().count('\n') + 1) + 3
    block(ax, 45, y + 6, t['sinkt'], 725, size=8.0, color=BLUE)


def panel_update(ax, t):
    panel(ax, 805, 108, t['b'])
    box(ax, 805, 146, 735, 40, face=PANEL)
    text(ax, 818, 166, t['eq'], size=8.6, va='center')
    block(ax, 818, 196, t['eqn'], 712, size=8.0, color=MUTED)
    # Before / after one cell: z lowered, residue added to sd, talus first.
    w = 90
    xb, xa = 860, 1100
    text(ax, xb, 278, t['before'], size=8.4, weight='bold', color=MUTED)
    text(ax, xa, 278, t['after'], size=8.4, weight='bold', color=MUTED)
    box(ax, xb, 330, w, 120, face=LIME, edge='#8a96a3', lw=.7)
    box(ax, xb, 312, w, 18, face=SOIL, edge='#9d8a63', lw=.7)
    box(ax, xa, 360, w, 90, face=LIME, edge='#8a96a3', lw=.7)
    box(ax, xa, 336, w, 24, face=SOIL, edge='#9d8a63', lw=.7)
    box(ax, xa, 330, w, 30, face='white', edge=ORANGE, lw=.9, ls='--', fill=False, z=6)
    line(ax, [(xa - 10, 312), (xa + w + 10, 312)], MUTED, .8, ls=':', z=6)
    dim(ax, (xa + w + 14, 312), (xa + w + 14, 336), None, color=ORANGE)
    text(ax, xa + w + 22, 318, t['zdown'], size=7.9, color=ORANGE, ha='left', va='center')
    text(ax, xa + w + 22, 350, t['res'], size=7.9, color=SED, ha='left', va='top')
    arrow(ax, [(xb + w + 20, 380), (xa - 20, 380)], MUTED, lw=1.3, size=9)
    block(ax, 818, 470, t['talus'], 712, size=8.0, color=SED)


def panel_lateral(ax, t):
    y0 = 648
    panel(ax, 35, y0, t['c'])
    # One ponded cell w and its walls (cells higher than the water surface).
    x0, w, base = 60, 70, 920
    tops = [740, 740, 810, 810, 740, 740]
    columns(ax, x0, w, base, tops, face=LIME, edge='#8a96a3')
    lev = 765
    box(ax, x0 + 2 * w, lev, 2 * w, 810 - lev, face=WATER, z=4)
    line(ax, [(x0 + 2 * w, lev), (x0 + 4 * w, lev)], BLUE, 1.2, z=5)
    for xw in (x0 + 2 * w - 4, x0 + 4 * w + 4):
        arrow(ax, [(x0 + 3 * w, 786), (xw, 786)], ORANGE, lw=1.5, size=9)
    arrow(ax, [(x0 + 3 * w, 790), (x0 + 3 * w, 822)], SED, lw=1.5, size=9)
    from _geomorph import dim as _dim
    _dim(ax, (x0 + 4 * w - 12, lev), (x0 + 4 * w - 12, 810), 'h', color=BLUE, offset=(-8, 6), ha='right', size=8.0)
    text(ax, x0 + 3 * w, 840, t['floor'], size=8.0, color=SED, ha='center', va='top')
    text(ax, x0, 686, t['wall'], size=8.0, color=ORANGE)
    line(ax, [(x0 + 60, 726), (x0 + 1.5 * w, 748)], MUTED, .7, z=9)
    block(ax, 500, 690, t['share'], 270, size=8.1, color=ORANGE)
    box(ax, 500, 772, 270, 120, face=PANEL)
    block(ax, 510, 778, t['auto'], 255, size=7.9)
    # Shapes: p = 0 versus p > 0.
    block(ax, 830, y0 + 42, t['p0'], 330, size=8.1, color=MUTED)
    xx0, yb = 830, y0 + 142
    xs = np.array([0, 150, 150, 170, 170, 330])
    ys = np.array([0, 0, 90, 90, 0, 0])
    poly(ax, list(zip(xx0 + xs, yb + ys)) + [(xx0 + 330, yb + 125), (xx0, yb + 125)], LIME, z=1)
    line(ax, list(zip(xx0 + xs, yb + ys)), INK, 1.1, z=6)
    block(ax, 1200, y0 + 42, t['p1'], 330, size=8.1, color=GREEN)
    xx = np.linspace(0, 330, 200)
    yy = 70 * np.exp(-((xx - 165) / 70) ** 2)
    poly(ax, list(zip(1200 + xx, yb + yy)) + [(1530, yb + 125), (1200, yb + 125)], LIME, z=1)
    line(ax, list(zip(1200 + xx, yb + yy)), INK, 1.1, z=6)


def build(lang):
    t = T[lang]
    fig, ax = canvas(H)
    header(ax, t['title'], t['sub'])
    panel_sources(ax, t)
    line(ax, [(787, 105), (787, 625)], RULE, .8)
    panel_update(ax, t)
    rule(ax, 35, 1540, 634)
    panel_lateral(ax, t)
    rule(ax, 35, 1540, 944)
    block(ax, 35, 954, t['foot'], 1505, size=8.1, color=MUTED)
    return fig


def draw(lang):
    return run(build, 'geomorph_dissol', lang,
               'Schematic of limestone dissolution f_dissol: water sources dissol_src and the sink term, the '
               'update of z and sd with residue and talus, and lateral dissolution dissol_lat. Not solver output.')
