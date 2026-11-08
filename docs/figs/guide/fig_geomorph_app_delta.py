"""Setup pattern of a river-mouth delta (geomorph_applications.md §2).

Plan view and centre-line profile of the minimal configuration (sea as ordinary
cells with an initial level, radiating far edge, channel cut between dry
non-erodible banks, inflow with mud concentration and capacity sand feed), the
mechanisms to switch on, and the expected shapes for high and low mud
concentration. Schematic with exaggerated scales, following the text and
examples/delta; not solver output.

Generate: python docs/figs/make_guide_figs.py geomorph_app_delta
"""
import numpy as np
from matplotlib.patches import Rectangle
from _geomorph import (canvas, header, panel, rule, box, poly, dim, run, text, kblock as block, line, arrow,
                       INK, MUTED, RULE, SED, GREEN, BLUE, ORANGE, SOIL, ROCK, WATER, MOVING, PANEL)

H = 830

T = {
 'ja': {
    'title': '河口デルタの設定の型  |  海の表し方・境界・川からの供給・入れる機構',
    'sub': '適用例 §2 の最小構成(examples/delta の段 1 と同じ型)。平面と縦断は模式図で、縮尺は誇張。',
    'a': '(a) 平面',
    'land': '陸: 乾いた\n非侵食の地盤\n(sd = 0)',
    'chan': '河道\n(掘り込み水路)',
    'inflow': '区間流入 Q\n+ 泥 inflow_cs\n+ 砂は容量給砂',
    'basin': '海盆: 水深 1.5〜2 m の平坦な通常セル\n+ 初期水位 e0 = 海面(f_htype = 2)',
    'far': '沖の辺: 長波放射(f_bc = 2)',
    'band': '潮汐を加えるとき: 海域マスクの帯 + fn_tide',
    'ns': '南北の辺: 壁(潮汐を加えるときは f_bc = 3)',
    'off': '河口から沖へ 1500 m 以上', 'lat': '横に\n±1300 m\n以上',
    'b': '(b) 河道の中心の縦断',
    'sea': '初期水位 e0 = 海面', 'bank': '両岸の陸(+1.5 m 程度。乾いている)',
    'cbed': '河道の河床', 'floor': '海盆の底(水深 1.5〜2 m)', 'soil': '侵食できる層 sd(河道と海底)',
    'c': '(c) 入れる機構と値の目安',
    'items': [
        ('砂', 'f_fluvial + fluv_bcfeed = 1(上流から平衡量の砂が来る)'),
        ('泥', 'f_suspend(susp_wf ≈ 1 mm/s を直接)+ f_bedfines = 1(積もった泥だけが再浮上)'),
        ('必須', 'fluv_slope = 1(砂州の側面へ広げる)と f_repose = 1。f_secflow は使わない'),
        ('時間', 'morfac 100〜200 で地形時間 1000〜4000 h(河道幅 30 m でデルタ幅 1000 m なら 4000 h)'),
        ('分流路', '出水・低水の繰り返し + f_fixation = 1(fix_tdec ≈ 出水の継続時間、fix_ctau_bank < c_τ)。幅/5 以上のセル数で解像'),
        ('潮汐', '潮の 1 周期の地形変化が小さくなるまで morfac を下げる。小さな海盆は潮位を毎ステップ更新'),
    ],
    'd': '(d) 泥の濃度と形',
    'mud_hi': '泥の濃度が高い(0.001 程度)\n→ 少数の細長い分流路(鳥趾状)',
    'mud_lo': '泥の濃度が低い(0.0002 程度)\n→ 多くの短い分流路(扇状)',
    'd_note': '形は実現ごとに違う(分岐の不安定性が丸め誤差を増幅する)が、積分量は変わらない。地盤高に数 cm の擾乱を入れた複数実現の統計で論じる。',
    'foot': '値は本文と examples/delta の目安(校正で変わる)。区間流入と潮位の与え方は境界条件と潮位の章。',
 },
 'en': {
    'title': 'Setup pattern of a river-mouth delta  |  Sea, boundaries, supply from the river, mechanisms to switch on',
    'sub': 'Minimal configuration of §2 of the applications page (same pattern as stage 1 of examples/delta). Plan and profile are schematic with exaggerated scales.',
    'a': '(a) Plan',
    'land': 'land: dry,\nnon-erodible\nground (sd = 0)',
    'chan': 'channel\n(cut)',
    'inflow': 'inflow Q\n+ mud inflow_cs\n+ capacity\n   sand feed',
    'basin': 'basin: flat ordinary cells 1.5–2 m deep\n+ initial level e0 = sea level (f_htype = 2)',
    'far': 'offshore edge: long-wave radiation (f_bc = 2)',
    'band': 'with tides: a sea-mask band + fn_tide',
    'ns': 'north and south edges: walls (f_bc = 3 with tides)',
    'off': '1500 m or more offshore of the mouth', 'lat': '±1300 m\nor more\nalongshore',
    'b': '(b) Profile along the channel centre',
    'sea': 'initial level e0 = sea level', 'bank': 'land on both banks (about +1.5 m, dry)',
    'cbed': 'channel bed', 'floor': 'basin floor (1.5–2 m deep)', 'soil': 'erodible layer sd (channel and sea floor)',
    'c': '(c) Mechanisms and guide values',
    'items': [
        ('sand', 'f_fluvial + fluv_bcfeed = 1 (the equilibrium amount of sand arrives from upstream)'),
        ('mud', 'f_suspend (give susp_wf ≈ 1 mm/s directly) + f_bedfines = 1 (only deposited mud is resuspended)'),
        ('required', 'fluv_slope = 1 (spreads sand onto bar flanks) and f_repose = 1; f_secflow is not used'),
        ('time', 'morfac 100–200 for 1000–4000 h of landform time (4000 h for a 1000 m delta from a 30 m channel)'),
        ('channels', 'floods and low flows + f_fixation = 1 (fix_tdec ≈ flood duration, fix_ctau_bank < c_τ); resolve a distributary with width/5 cells or more'),
        ('tides', 'lower morfac until one tidal cycle changes the bed little; update the tide every step in small basins'),
    ],
    'd': '(d) Mud concentration and shape',
    'mud_hi': 'high mud concentration (about 0.001)\n→ few long distributaries (bird-foot)',
    'mud_lo': 'low mud concentration (about 0.0002)\n→ many short distributaries (fan)',
    'd_note': 'The shape differs between realizations (the bifurcation instability amplifies round-off), while integral quantities do not; discuss statistics of several realizations with a few-cm perturbation of the bed.',
    'foot': 'Values are guides from the text and examples/delta (they change with calibration). Inflow sections and tides: the boundary-condition and tide chapters.',
 },
}


def lobe_fan(ax, x0, yc, r, nch, seed):
    """A fan-shaped lobe with nch short distributaries (plan view)."""
    th = np.linspace(-1.25, 1.25, 60)
    rng = np.random.default_rng(seed)
    rr = r * (1 + 0.06 * np.sin(9 * th) + 0.015 * rng.standard_normal(th.size))
    pts = [(x0, yc - 14)] + [(x0 + rr[k] * np.cos(t), yc + rr[k] * np.sin(t)) for k, t in enumerate(th)] + [(x0, yc + 14)]
    poly(ax, pts, MOVING, z=3)
    for t in np.linspace(-0.9, 0.9, nch):
        L = 0.75 * r
        line(ax, [(x0, yc), (x0 + 0.35 * L * np.cos(t * 0.5), yc + 0.35 * L * np.sin(t * 0.5)),
                  (x0 + L * np.cos(t), yc + L * np.sin(t))], WATER, 2.0, z=4)


def lobe_birdfoot(ax, x0, yc, seed):
    """Few long distributaries with levee-like bars (plan view)."""
    paths = [[(x0, yc), (x0 + 60, yc - 6), (x0 + 120, yc - 30), (x0 + 170, yc - 46)],
             [(x0, yc), (x0 + 70, yc + 8), (x0 + 140, yc + 20), (x0 + 190, yc + 40)]]
    for p in paths:
        p = np.asarray(p, float)
        n = np.array([[0, 0]] + [list(p[k + 1] - p[k]) for k in range(len(p) - 1)], float)
        for k in range(1, len(n)):
            n[k] = np.array([-n[k][1], n[k][0]]) / np.hypot(*n[k])
        n[0] = n[1]
        up = p + 9 * n; dn = p - 9 * n
        poly(ax, list(map(tuple, up)) + list(map(tuple, dn[::-1])), MOVING, z=3)
        line(ax, list(map(tuple, p)), WATER, 2.2, z=4)
    poly(ax, [(x0, yc - 18), (x0 + 40, yc - 16), (x0 + 50, yc), (x0 + 40, yc + 16), (x0, yc + 18)], MOVING, z=3)
    line(ax, [(x0, yc), (x0 + 48, yc)], WATER, 2.2, z=4)


def panel_plan(ax, t):
    panel(ax, 35, 108, t['a'])
    x0, x1, y0, y1 = 50, 740, 160, 520
    xl, yc = 170, 340
    box(ax, x0, y0, xl - x0, y1 - y0, face=SOIL, edge='#9d8a63', z=1)
    box(ax, xl, y0, x1 - xl, y1 - y0, face=WATER, z=1)
    box(ax, x0, yc - 13, xl - x0, 26, face=WATER, z=2)
    line(ax, [(x0, yc - 13), (xl, yc - 13)], INK, .9, z=5)
    line(ax, [(x0, yc + 13), (xl, yc + 13)], INK, .9, z=5)
    line(ax, [(xl, y0), (xl, yc - 13)], INK, .9, z=5)
    line(ax, [(xl, yc + 13), (xl, y1)], INK, .9, z=5)
    lobe_fan(ax, xl, yc, 80, 4, 2)
    # Far edge (radiation) and the optional tide band.
    band = Rectangle((x1 - 34, y0), 34, y1 - y0, facecolor='none', edgecolor=MUTED, hatch='////', lw=0, zorder=2)
    ax.add_patch(band)
    line(ax, [(x1, y0), (x1, y1)], BLUE, 2.4, ls='--', z=6)
    line(ax, [(x0, y0), (x1, y0)], INK, 1.6, z=6)
    line(ax, [(x0, y1), (x1, y1)], INK, 1.6, z=6)
    text(ax, x1 + 8, (y0 + y1) / 2, t['far'], size=7.8, color=BLUE, va='center', rotation=90, ha='left')
    text(ax, x1 - 42, y1 - 10, t['band'], size=7.6, color=MUTED, ha='right', va='bottom')
    text(ax, (x0 + x1) / 2, y0 - 6, t['ns'], size=7.6, color=INK, ha='center', va='bottom')
    text(ax, (x0 + xl) / 2, y0 + 20, t['land'], size=7.6, color=INK, ha='center')
    text(ax, (x0 + xl) / 2, yc + 20, t['chan'], size=7.6, color=INK, ha='center')
    arrow(ax, [(x0 - 12, yc), (x0 + 30, yc)], BLUE, lw=1.8, size=10)
    text(ax, x0 + 3, yc + 70, t['inflow'], size=7.2, color=BLUE)
    text(ax, 395, 200, t['basin'], size=7.8, color=INK, ha='center')
    dim(ax, (xl + 4, 470), (x1 - 4, 470), t['off'], color=INK, offset=(0, -12), size=7.8)
    dim(ax, (610, y0 + 40), (610, y1 - 70), None, color=INK)
    text(ax, 600, 310, t['lat'], size=7.8, color=INK, va='center', ha='right')


def panel_profile(ax, t):
    x0 = 800
    panel(ax, x0, 108, t['b'])
    xa, xb = 815, 1535
    ysea, ybank, ycb, yfl, ybot = 205, 182, 235, 262, 318
    xs = [xa, 960, 1000, xb]
    zs = [ycb - 4, ycb, yfl, yfl]
    poly(ax, list(zip(xs, zs)) + [(xb, ybot), (xa, ybot)], SOIL, z=2)
    line(ax, list(zip(xs, zs)), INK, 1.2, z=6)
    poly(ax, list(zip(xs, zs))[::-1] + [(xa, ysea), (xb, ysea)][::-1][::-1], WATER, z=1)
    poly(ax, [(xa, ysea), (xb, ysea), (xb, yfl), (1000, yfl), (960, ycb), (xa, ycb - 4)], WATER, z=1)
    line(ax, [(xa, ysea), (xb, ysea)], BLUE, 1.3, z=6)
    line(ax, [(xa, ybank), (960, ybank)], MUTED, 1.0, ls=':', z=6)
    line(ax, [(xb, ysea - 25), (xb, ybot)], BLUE, 2.0, ls='--', z=7)
    text(ax, xb - 6, ysea - 8, t['sea'], size=7.6, color=BLUE, ha='right', va='bottom')
    text(ax, xa + 4, ybank - 6, t['bank'], size=7.6, color=MUTED, va='bottom')
    text(ax, 880, ycb + 8, t['cbed'], size=7.6, color=INK, ha='center')
    text(ax, 1270, yfl + 8, t['floor'], size=7.6, color=INK, ha='center')
    text(ax, 1270, 290, t['soil'], size=7.6, color='#7a6640', ha='center')


def panel_items(ax, t):
    x0 = 800
    panel(ax, x0, 345, t['c'])
    y = 380
    for k, (name, s) in enumerate(t['items']):
        rule(ax, x0, 1540, y - 6)
        text(ax, x0, y, name, size=8.2, weight='bold', color=SED)
        a = block(ax, x0 + 94, y, s, 640, size=8.0)
        y += 23 * (a.get_text().count('\n') + 1) + 12


def panel_shapes(ax, t):
    panel(ax, 35, 545, t['d'])
    for k, (key, draw) in enumerate((('mud_hi', 'bird'), ('mud_lo', 'fan'))):
        bx = 50 + k * 360
        box(ax, bx, 578, 330, 110, face=WATER, z=1)
        box(ax, bx, 578, 40, 110, face=SOIL, edge='#9d8a63', z=1)
        box(ax, bx, 627, 40, 12, face=WATER, z=2)
        if draw == 'bird':
            lobe_birdfoot(ax, bx + 40, 633, 4)
        else:
            lobe_fan(ax, bx + 40, 633, 48, 6, 5)
        text(ax, bx, 696, t[key], size=7.8)
    block(ax, 35, 750, t['d_note'], 730, size=7.8, color=MUTED)


def build(lang):
    t = T[lang]
    fig, ax = canvas(H)
    header(ax, t['title'], t['sub'])
    panel_plan(ax, t)
    line(ax, [(782, 105), (782, 800)], RULE, .8)
    panel_profile(ax, t)
    panel_items(ax, t)
    panel_shapes(ax, t)
    return fig


def draw(lang):
    return run(build, 'geomorph_app_delta', lang,
               'Schematic plan and profile of the minimal river-mouth delta setup (sea as ordinary cells with an initial '
               'level, radiating far edge, channel between dry banks, inflow with mud and capacity sand feed), the '
               'mechanisms to switch on and the expected shapes for high and low mud concentration. Not solver output.')
