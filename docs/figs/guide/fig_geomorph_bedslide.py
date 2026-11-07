"""Moving bed layer f_bedslide (geomorph.md): bookkeeping, driving head, collapse-depth
geometry and the hand-over from the mixture model.

(a) hb is part of z and sd; moving it keeps h, so the water surface moves (moving
seabed); (b) driving head Phi = z + r h and the inertia-free Voellmy speed;
(c) how to give fn_bsinit (plane slip surface vs constant-depth box);
(d) hand-over from the debris mixture where the ponded depth >= bs_hplunge.
The Phi line in (b) is evaluated from the drawn profile with r = 0.5
(bs_rho = 2000). Schematic, not solver output.

Generate: python docs/figs/make_guide_figs.py geomorph_bedslide
"""
import numpy as np
from _geomorph import (canvas, header, panel, rule, box, poly, dim, cross, water_px, ground_px, run, chart,
                       text, block, line, arrow, INK, MUTED, RULE,
                       SOIL, ROCK, WATER, BLUE, SED, MOVING, GREEN, ORANGE, PANEL)

H = 1612

T = {
 'ja': {
    'title': '動く底層  |  地形の内側を動く土塊と、水面の変位(f_bedslide)',
    'sub': '慣性なしの摩擦支配流(Voellmy)で陸上から水中まで走る。morfac = 1 が必須。断面は説明用で、計算結果ではない。',
    'a': '(a) 状態と簿記: hb は z・sd の内数',
    'before': '移送の前', 'after': 'Δ を移送した後',
    'D': '送り手 D', 'R': '受け手 R',
    'e0': '元の水面',
    'dD': 'z・sd が Δ 減る\n水面も Δ 下がる', 'dR': 'z・sd が Δ 増える\n水面も Δ 上がる',
    'hkeep': 'h は保つ', 'rock': '岩盤面 z − sd\nは不変',
    'a_notes': ['この水面の変位が水理計算へ渡る(移動海底方式の津波源)。',
                '発火: hb = min(D, sd)。z・sd・h は変えない(土塊はもとから z の中)。',
                '停止: V < bs_vstop が bs_tstop 秒続いたセルの hb を 0 に。質量は z・sd に残る(不可逆)。'],
    'leg_hb': '動く底層 hb', 'leg_sd': '土層 sd', 'leg_rock': '基岩',
    'b': '(b) 駆動水頭と速度',
    'z': '地表 z', 'phi': '駆動水頭 Φ = z + r h',
    'land': '陸上: ∇Φ = ∇z', 'under': '平らな水面の下:\n∇Φ = (1 − r) ∇z',
    'r': 'r = ρw / ρs(bs_rho = 2000 で 0.5)',
    'eqs': 'S = Φ の 8 近傍最急降下勾配、浮力係数 b = 1 − r min(1, h/hb)\n'
           'S ≤ μ b: V = 0(降伏 = 停止)\n'
           'S > μ b: V = √(ξ hb (S − μ b))(慣性なし Voellmy。μ・ξ = bs_mu・bs_xi)',
    'b_note': '水中では駆動と摩擦が浮力で同時に減るので、水面が平らな水中でも走る(混合体の土石流モデルとの違い)。'
              '発火直後から終端速度で動く(加速期間を省略)。',
    'c': '(c) 崩壊深 D(fn_bsinit)の与え方',
    'ok': '平面すべり面: 下端で地表に抜ける', 'ng': '一定深さの箱型',
    'okn': '深さが下端に向かって 0 になる形。\n土塊は斜面に沿って抜け出る。',
    'ngn': '空になると下流側に壁のある穴になる。\n表面勾配で動く慣性なしの流れは\n段差を登れない(土石流モデルでも同じ)。',
    'd': '(d) 混合体からの引き渡し  bs_hplunge > 0(f_debris = 1)',
    'mix': '陸上: 混合体 h + hs(慣性あり)', 'pl': '滞水深 ≥ bs_hplunge のセル\nhs → hb(かさ hs/(1 − λ))',
    'bed': '水中: 動く底層 hb(慣性なし)',
    'd_items': ['f_bsvplunge = 1: 混合体が底層の終端速度まで減速してから引き渡す(高速突入の運動量は混合体のまま水柱へ)',
                'f_bsplunge = 1: 静水時の水深(初期水面 − 現在の z)で判定(突入で一時的に離水した汀線帯でも引き渡す)',
                'bs_tstop = 10〜15 s: 突入直後の汀線帯の一時的な失速で誤って固定しない'],
    'e': '(e) 速度と地盤の勾配(陸上と、平らな水面の下)',
    'ex': '地盤の勾配 |∇z|', 'ey': '底層の速度 V (m/s)',
    'v_land': '陸上(h = 0): V = √(ξ hb (|∇z| − μ))',
    'v_sub': '水中(h ≥ hb、平らな水面): V = √(ξ hb (1 − r)(|∇z| − μ))',
    'lin': '降伏の近傍(S − μ b < bs_eps_s)は線形化',
    'e_items': ['水中でも動き出す勾配は陸上と同じ μ(駆動の勾配と摩擦がともに 1 − r 倍になる)。速さは √(1 − r) 倍(r = 0.5 で約 0.71 倍)。',
                '慣性なしなので、勾配が μ を下回ったセルではその場で止まりにかかる(停止の固定は bs_vstop・bs_tstop)。',
                '降伏の近傍では V を勾配の超過分に比例させ(幅 bs_eps_s)、サブサイクルの刻みが細かくなりすぎるのを防ぐ。'],
    'e_par': '図の値: hb = 5 m、μ = bs_mu = 0.15、ξ = bs_xi = 500 m/s²、r = 0.5(bs_rho = 2000)、bs_eps_s = 0.02',
    'foot': '間隙分の扱いは f_dbwet(0: 表面が上がる、1: 水柱から埋没、2: 地下貯留へ)。水の抗力・付加質量は ξ に含め、非静水圧・分散性は扱わない。',
 },
 'en': {
    'title': 'Moving bed layer  |  A slide moving inside the terrain and the displacement of the water surface (f_bedslide)',
    'sub': 'Inertia-free friction-controlled flow (Voellmy) running from land into water. Requires morfac = 1. Illustrative sections, not computed results.',
    'a': '(a) State and bookkeeping: hb is part of z and sd',
    'before': 'before the transfer', 'after': 'after moving Δ',
    'D': 'donor D', 'R': 'receiver R',
    'e0': 'original surface',
    'dD': 'z, sd drop by Δ;\nsurface drops by Δ', 'dR': 'z, sd rise by Δ;\nsurface rises by Δ',
    'hkeep': 'h kept', 'rock': 'bedrock surface\nz − sd unchanged',
    'a_notes': ['This displacement of the water surface is passed to the hydraulics (a moving-seabed tsunami source).',
                'Ignition: hb = min(D, sd); z, sd and h are unchanged (the mass is already inside z).',
                'Stop: hb → 0 where V < bs_vstop lasts bs_tstop s; the mass stays in z and sd (irreversible).'],
    'leg_hb': 'moving layer hb', 'leg_sd': 'soil sd', 'leg_rock': 'bedrock',
    'b': '(b) Driving head and speed',
    'z': 'ground z', 'phi': 'driving head Φ = z + r h',
    'land': 'on land: ∇Φ = ∇z', 'under': 'under a flat surface:\n∇Φ = (1 − r) ∇z',
    'r': 'r = ρw / ρs (0.5 for bs_rho = 2000)',
    'eqs': 'S = steepest 8-neighbour descent of Φ; buoyancy factor b = 1 − r min(1, h/hb)\n'
           'S ≤ μ b: V = 0 (yield = stop)\n'
           'S > μ b: V = √(ξ hb (S − μ b)) (inertia-free Voellmy; μ, ξ = bs_mu, bs_xi)',
    'b_note': 'Under water, buoyancy reduces driving and friction together, so the layer runs even under a flat water surface '
              '(unlike the mixture debris-flow model). It moves at its terminal speed from ignition (no acceleration phase).',
    'c': '(c) How to give the collapse depth D (fn_bsinit)',
    'ok': 'slip plane reaching the toe', 'ng': 'constant-depth box',
    'okn': 'Depth tapers to 0 toward the toe;\nthe mass slides out along the slope.',
    'ngn': 'Once emptied it becomes a hole with a\ndownstream wall: an inertia-free flow\ndriven by the surface gradient cannot\nclimb steps, as in the debris-flow model.',
    'd': '(d) Hand-over from the mixture  bs_hplunge > 0 (f_debris = 1)',
    'mix': 'on land: mixture h + hs (with inertia)', 'pl': 'cells with ponded depth ≥ bs_hplunge:\nhs → hb (bulk hs/(1 − λ))',
    'bed': 'under water: moving layer hb (inertia-free)',
    'd_items': ['f_bsvplunge = 1: hand over only after the mixture slows to the layer\'s terminal speed (fast-entry momentum stays in the mixture and goes to the water)',
                'f_bsplunge = 1: judge by the still-water depth (initial surface − current z), so shoreline cells briefly exposed by the entry still hand over',
                'bs_tstop = 10–15 s: avoids false fixing during the brief stall of the shoreline zone right after entry'],
    'e': '(e) Speed versus ground slope (on land and under a flat water surface)',
    'ex': 'ground slope |∇z|', 'ey': 'layer speed V (m/s)',
    'v_land': 'on land (h = 0): V = √(ξ hb (|∇z| − μ))',
    'v_sub': 'under water (h ≥ hb, flat surface): V = √(ξ hb (1 − r)(|∇z| − μ))',
    'lin': 'linearized near yield (S − μ b < bs_eps_s)',
    'e_items': ['Under water the layer starts to move at the same slope μ as on land (driving slope and friction are both scaled by 1 − r); the speed is √(1 − r) times smaller (about 0.71 for r = 0.5).',
                'Without inertia, a cell whose slope falls below μ starts to stop at once (fixing to the terrain follows bs_vstop and bs_tstop).',
                'Near yield, V is made proportional to the excess slope (width bs_eps_s) so that the subcycle step does not become too small.'],
    'e_par': 'Values: hb = 5 m, μ = bs_mu = 0.15, ξ = bs_xi = 500 m/s², r = 0.5 (bs_rho = 2000), bs_eps_s = 0.02',
    'foot': 'The pore part follows f_dbwet (0: surface rises, 1: buried from the water column, 2: to groundwater storage). Water drag and added mass are lumped into ξ; no non-hydrostatic pressure or dispersion.',
 },
}


def column(ax, x, w, rock, z, hbtop_thick, e, base):
    """One cell: bedrock base..rock, soil rock..z, moving layer z..z+hb (top of soil), water e..z."""
    box(ax, x, rock, w, base - rock, face=ROCK, edge='#9d9a92', lw=.7, z=2)
    box(ax, x, z, w, rock - z, face=SOIL, edge='#9d8a63', lw=.7, z=2)
    if hbtop_thick > 0:
        box(ax, x, z, w, hbtop_thick, face=MOVING, edge=SED, lw=.7, z=3, hatch='///')
    if e < z:
        box(ax, x, e, w, z - e, face=WATER, edge='none', z=1)
        line(ax, [(x, e), (x + w, e)], BLUE, 1.3, z=5)


def panel_bookkeeping(ax, t):
    panel(ax, 35, 108, t['a'])
    w, base, d = 92, 460, 22
    # Before: donor D (upslope, shallower) and receiver R (deeper).
    xb, xa = 60, 430
    text(ax, xb, 148, t['before'], size=8.6, weight='bold', color=MUTED)
    text(ax, xa, 148, t['after'], size=8.6, weight='bold', color=MUTED)
    e0 = 222
    column(ax, xb, w, 390, 302, 34, e0, base)
    column(ax, xb + w, w, 430, 372, 0, e0, base)
    column(ax, xa, w, 390, 302 + d, 34 - d, e0 + d, base)
    column(ax, xa + w, w, 430, 372 - d, d, e0 - d, base)
    line(ax, [(xa - 10, e0), (xa + 2 * w + 10, e0)], BLUE, .8, ls='--', z=6)
    text(ax, xa + 2 * w + 14, e0, t['e0'], size=7.8, color=BLUE, ha='left', va='center')
    arrow(ax, [(xb + 2 * w + 20, 330), (xa - 24, 330)], SED, lw=1.6, size=11)
    text(ax, (xb + 2 * w + xa) / 2, 340, 'Δ', size=9, color=SED, ha='center', va='top')
    for x0 in (xb, xa):
        text(ax, x0 + w / 2, 470, t['D'], size=8.2, ha='center')
        text(ax, x0 + 1.5 * w, 470, t['R'], size=8.2, ha='center')
    # Same h, shifted surfaces.
    dim(ax, (xa + 14, e0 + d), (xa + 14, 302 + d), t['hkeep'], color=BLUE, offset=(8, 0), ha='left', size=7.8)
    dim(ax, (xa + w + 14, e0 - d), (xa + w + 14, 372 - d), t['hkeep'], color=BLUE, offset=(8, 0), ha='left', size=7.8)
    text(ax, xa + 2 * w + 14, 262, t['dR'], size=7.9, color=SED, ha='left')
    text(ax, xa - 12, 246, t['dD'], size=7.9, color=SED, ha='right')
    text(ax, xa + 2 * w + 14, 400, t['rock'], size=7.9, color=MUTED, ha='left')
    for k, (key, face, hatch) in enumerate([('leg_hb', MOVING, '///'), ('leg_sd', SOIL, None), ('leg_rock', ROCK, None)]):
        lx = 60 + 175 * k
        box(ax, lx, 500, 24, 14, face=face, edge=SED if hatch else 'none', lw=.6, hatch=hatch)
        text(ax, lx + 32, 496, t[key], size=8.0)
    y = 530
    for s in t['a_notes']:
        a = block(ax, 45, y, '• ' + s, 725, size=8.3)
        y += 23 * (a.get_text().count('\n') + 1)


def panel_head(ax, t):
    panel(ax, 805, 108, t['b'])
    xs = np.array([820, 1050, 1300, 1530])
    ys = np.array([180, 300, 420, 430])
    level, r = 300, .5
    ground_px(ax, xs, ys, 470, face=SOIL)
    water_px(ax, xs, ys, level)
    xx = np.linspace(820, 1530, 300)
    yy = np.interp(xx, xs, ys)
    phi = np.where(yy > level, yy - r * (yy - level), yy)
    line(ax, list(zip(xx, phi)), ORANGE, 1.6, ls='--', z=8)
    text(ax, 860, 168, t['z'], size=8.2, color=INK)
    text(ax, 1330, 380, t['phi'], size=8.2, color=ORANGE)
    text(ax, 965, 205, t['land'], size=8.2, color=MUTED)
    text(ax, 1062, 418, t['under'], size=8.2, color=MUTED)
    text(ax, 1180, 262, t['r'], size=7.9, color=MUTED)
    box(ax, 805, 484, 735, 84, face=PANEL)
    block(ax, 818, 492, t['eqs'], 712, size=8.2)
    block(ax, 805, 578, t['b_note'], 735, size=8.2)


def slope_section(ax, x0, x1, y0, y1, base):
    xs = np.array([x0, x1])
    ys = np.array([y0, y1])
    poly(ax, [(x0, y0), (x1, y1), (x1, base), (x0, base)], SOIL, z=2)
    line(ax, [(x0, y0), (x1, y1)], INK, 1.1, z=6)
    return xs, ys


def panel_geometry(ax, t):
    y0 = 682
    panel(ax, 35, y0, t['c'])
    base = 950
    # OK: lens thinning to zero at the toe of the slope.
    x0, x1 = 50, 380
    ya, yb = 740, 900
    slope_section(ax, x0, x1, ya, yb, base)
    poly(ax, [(x1, yb), (x1 + 20, yb), (x1 + 20, base), (x1, base)], SOIL, z=2)
    line(ax, [(x1, yb), (x1 + 20, yb)], INK, 1.1, z=6)
    xs = np.linspace(90, 360, 60)
    top = ya + (yb - ya) * (xs - x0) / (x1 - x0)
    depth = 40 * np.sin(np.pi * (xs - 90) / 270) ** .8 * (1 - (xs - 90) / 270) ** .3
    poly(ax, list(zip(xs, top)) + list(zip(xs[::-1], (top + depth)[::-1])), MOVING, edge=SED, lw=.7, z=3, hatch='///')
    line(ax, list(zip(xs, top + depth)), SED, 1.0, ls='--', z=7)
    arrow(ax, [(250, 845), (365, 912)], SED, lw=1.6, size=11)
    text(ax, x0, 712, t['ok'], size=8.4, weight='bold', color=GREEN)
    block(ax, x0, 960, t['okn'], 340, size=8.1)
    # NG: constant-depth box; after emptying, a hole with a downstream wall.
    x0, x1 = 425, 760
    bx0, bx1, dep = 480, 690, 42
    ty0 = ya + (yb - ya) * (bx0 - x0) / (x1 - x0)
    ty1 = ya + (yb - ya) * (bx1 - x0) / (x1 - x0)
    # Emptied box: the ground surface now follows the hole (walls up- and downstream).
    surf = [(x0, ya), (bx0, ty0), (bx0, ty0 + dep), (bx1, ty1 + dep), (bx1, ty1), (x1, yb)]
    poly(ax, surf + [(x1, base), (x0, base)], SOIL, z=2)
    line(ax, surf, INK, 1.1, z=6)
    line(ax, [(bx0, ty0), (bx1, ty1)], MUTED, .8, ls=':', z=6)
    poly(ax, [(bx0 + 120, ty0 + 0.57 * (ty1 - ty0) + dep - 14), (bx1, ty1 + dep - 22), (bx1, ty1 + dep), (bx0 + 120, ty0 + 0.57 * (ty1 - ty0) + dep)],
         MOVING, edge=SED, lw=.7, z=5, hatch='///')
    line(ax, [(bx1, ty1), (bx1, ty1 + dep)], ORANGE, 2.4, z=8)
    arrow(ax, [(bx1 - 40, ty1 + dep - 30), (bx1 + 10, ty1 - 18)], SED, lw=1.4, size=10)
    cross(ax, bx1 - 8, ty1 - 2)
    text(ax, x0, 712, t['ng'], size=8.4, weight='bold', color=ORANGE)
    block(ax, x0, 960, t['ngn'], 345, size=8.1)


def panel_handover(ax, t):
    y0 = 682
    panel(ax, 805, y0, t['d'])
    xs = np.array([820, 1080, 1250, 1530])
    ys = np.array([755, 875, 945, 960])
    level = 875
    ground_px(ax, xs, ys, 990, face=SOIL)
    water_px(ax, xs, ys, level)
    # Mixture on land (h + hs) and the moving layer under water.
    xm = np.linspace(880, 1065, 40)
    tm = np.interp(xm, xs, ys)
    dm = 22 * np.sin(np.pi * (xm - 880) / 185) ** .7
    poly(ax, list(zip(xm, tm)) + list(zip(xm[::-1], (tm - dm)[::-1])), '#e9b98b', edge=SED, lw=.7, z=4)
    arrow(ax, [(930, 783), (1040, 837)], SED, lw=1.5, size=10)
    xb = np.linspace(1150, 1420, 40)
    tb = np.interp(xb, xs, ys)
    db = 14 * np.sin(np.pi * (xb - 1150) / 270) ** .7
    poly(ax, list(zip(xb, tb)) + list(zip(xb[::-1], (tb + db)[::-1])), MOVING, edge=SED, lw=.7, z=4, hatch='///')
    arrow(ax, [(1230, 930), (1380, 945)], SED, lw=1.5, size=10)
    line(ax, [(1105, 855), (1105, 895)], ORANGE, 2.0, z=9)
    text(ax, 828, 722, t['mix'], size=8.2, color=SED)
    text(ax, 1110, 805, t['pl'], size=8.0, color=ORANGE)
    text(ax, 1190, 966, t['bed'], size=8.0, color=SED)
    y = 1004
    for s in t['d_items']:
        a = block(ax, 812, y, '• ' + s, 728, size=8.1)
        y += 22 * (a.get_text().count('\n') + 1) + 2


def bed_speed(slope, hb=5.0, mu=0.15, xi=500.0, r=0.5, eps=0.02, submerged=False):
    """Inertia-free Voellmy speed of m_geomorph_bedslide for a planar slope (flat water surface)."""
    s = np.asarray(slope, float)
    S = (1 - r) * s if submerged else s
    b = (1 - r) if submerged else 1.0
    sy = S - mu * b
    v = np.where(sy < eps, np.sqrt(xi * hb / eps) * sy, np.sqrt(xi * hb * np.maximum(sy, 0.0)))
    return np.where(sy > 0, v, 0.0)


def panel_speed(fig, ax, t):
    y0 = 1180
    panel(ax, 35, y0, t['e'])
    sl = np.linspace(0, 0.6, 1200)
    c = chart(fig, 110, y0 + 42, 620, 260, (0, 0.6), (0, 36), xlabel=t['ex'], ylabel=t['ey'])
    c.plot(sl, bed_speed(sl), color=SED, lw=2.0, label=t['v_land'])
    c.plot(sl, bed_speed(sl, submerged=True), color=BLUE, lw=2.0, label=t['v_sub'])
    c.axvline(0.15, color=MUTED, lw=.8, ls=':')
    c.text(0.155, 20, 'μ', fontsize=9, color=MUTED, va='center')
    c.annotate(t['lin'], xy=(0.165, 4.0), xytext=(0.27, 3.0), fontsize=7.6, color=MUTED, va='center',
               arrowprops=dict(arrowstyle='-|>', color=MUTED, lw=.8))
    c.legend(loc='upper left', fontsize=7.4, frameon=True, facecolor='white', edgecolor='none', framealpha=1,
             labelspacing=0.3)
    y = y0 + 44
    for s_ in t['e_items']:
        a = block(ax, 805, y, '• ' + s_, 735, size=8.0)
        y += 21 * (a.get_text().count('\n') + 1) + 6
    block(ax, 805, y + 6, t['e_par'], 735, size=7.8, color=MUTED)


def build(lang):
    t = T[lang]
    fig, ax = canvas(H)
    header(ax, t['title'], t['sub'])
    panel_bookkeeping(ax, t)
    line(ax, [(787, 105), (787, 1150)], RULE, .8)
    panel_head(ax, t)
    rule(ax, 35, 1540, 662)
    panel_geometry(ax, t)
    panel_handover(ax, t)
    rule(ax, 35, 1540, 1160)
    panel_speed(fig, ax, t)
    rule(ax, 35, 1540, 1552)
    block(ax, 35, 1562, t['foot'], 1505, size=8.1, color=MUTED)
    return fig


def draw(lang):
    return run(build, 'geomorph_bedslide', lang,
               'Schematic of the moving bed layer f_bedslide: hb inside z and sd with h kept (water-surface '
               'displacement), driving head Phi = z + r h and inertia-free Voellmy speed, collapse-depth geometry, '
               'and hand-over from the mixture model. Not solver output.')
