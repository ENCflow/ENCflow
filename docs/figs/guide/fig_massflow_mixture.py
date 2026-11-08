"""Single-layer mixture of the debris-flow model and its exchange with the bed (massflow.md §1, §3).

(a) state of one cell: water h and solid column hs move together (h_t = h + hs,
    C = hs / h_t, rho_m / rho = 1 + sC), the bed z and the erodible layer sd;
(b) the exchange at the landform update: Delta z = -Delta hs / C* applied to z
    and sd together, clamps, pore water (f_dbwet), stopping (f_dbstop);
(c) bed change per unit distance travelled versus C on one slope for
    f_dbed = 1 (relaxation toward C_inf, delta_e / delta_d) and f_dbed = 2
    (Egashira-Ashida), the exchange rates of src/m_geomorph_debris.f90 divided by
    C* |V|, for the default coefficients. Schematic and closed-form curves; not
    solver output.

Generate: python docs/figs/make_guide_figs.py massflow_mixture
"""
import math
import numpy as np
from _geomorph import (canvas, header, panel, rule, box, poly, dim, chart, run, text, kblock as block, line, arrow,
                       INK, MUTED, RULE, SED, GREEN, BLUE, ORANGE, SOIL, ROCK, WATER, MOVING, TALUS, PANEL)

H = 900
S, CSTAR, TANPHI = 1.65, 0.6, math.tan(math.radians(35.0))
DE, DD, TANTH = 0.0007, 0.05, 0.3          # db_delte, db_deltd, slope of (c)
LBL = dict(facecolor=WATER, edgecolor='none', pad=1.5)   # label backing inside the water

T = {
 'ja': {
    'title': '単層混合体と河床との交換  |  状態量・交換の簿記・平衡濃度へ向かう速さ',
    'sub': 'f_debris。(a)(b) は 1 つのセルと河床の説明図、(c) は src/m_geomorph_debris.f90 の交換率を既定の係数で評価した曲線。計算結果ではない。',
    'a': '(a) 1 つのセルの状態(§1)', 'a2': '水と固体を 1 つの層として解く',
    'surf': '水面 = z + h + hs(圧力項)', 'vel': '同じ速度 V\n(固体と水)',
    'hs': 'hs\n(固体の厚さ換算)', 'h': 'h(水)', 'ht': 'h_t = h + hs\n(摩擦の深さ)',
    'z': '地盤高 z', 'rock': '基岩面 z − sd', 'sd': 'sd\n(侵食できる層)',
    'a_list': [
        'C = hs / (h + hs)(混合体積濃度)、ρm / ρ = 1 + sC',
        '堆積層の固体濃度 C* = 1 − λ(fluv_porosity から)',
        'hs は水と同じエッジ流量で移流(浮遊砂と同じ)',
        '抵抗則(§2)は h_t と C で摩擦を置き換える',
    ],
    'b': '(b) 河床との交換(§3)', 'b2': '地形更新の時刻に行う',
    'ero': '侵食', 'dep': '堆積', 'pore': '間隙水\n(f_dbwet = 1)', 'stop': '停止して固定\n(f_dbstop = 1)',
    'old': '元の河床',
    'b_list': [
        'Δz = −Δh_s / C* を z と sd に同じだけ(基岩面 z − sd は動かない)',
        '侵食は sd まで、堆積は hs まで。乾いたセル(h ≤ dd)は hs を全量河床へ',
        'f_dbwet = 1: 侵食で λ s_b |Δz| を h に加え(増水)、堆積で引く。2: 地下貯留 h_g と授受',
        'f_dbstop = 1: |V| < v_stop で C > C∞ の超過分を w_stop の率で z へ(天然ダムの地形)',
        '基岩は削らない(岩盤侵食は f_rockinc の rock_kdb)',
    ],
    'c': '(c) 交換の向きと速さ(§3)', 'c2': 'tan θ = 0.3 の斜面(C∞ = 0.45)',
    'cx': '混合体積濃度 C', 'cy': '1 m 進む間の河床の変化 (m)',
    'ero_side': '侵食\n(C < C∞)', 'dep_side': '堆積\n(C > C∞)', 'cinf': 'C∞ = 0.45',
    'f1': 'f_dbed = 1(δe = 0.0007、δd = 0.05)', 'f2': 'f_dbed = 2(江頭・芦田。係数なし)',
    'solid': '実線: 侵食、破線: 堆積',
    'c_note': '侵食深(堆積厚)÷ 走行距離。どちらの則も同じ C∞ へ向かう。f_dbed = 1 の速さは δe・δd(到達距離の校正係数)で'
              '決まり、既定では堆積が侵食より速い。f_dbed = 2 は係数がなく、清水に近い流れは強く削る(上限は sd)。',
    'foot': '値は説明用(φ = 35°、s = 1.65、C* = 0.6、δe・δd は既定値)。f_dbed = 3(高橋・中川)・4(速度比例連行)・0(交換なし)は本文。',
 },
 'en': {
    'title': 'Single-layer mixture and its exchange with the bed  |  State, bookkeeping of the exchange, speed toward the equilibrium',
    'sub': 'f_debris. (a)(b) explain one cell and the bed; (c) evaluates the exchange rates of src/m_geomorph_debris.f90 with the default coefficients. Not computed results.',
    'a': '(a) State of one cell (§1)', 'a2': 'water and solid solved as one layer',
    'surf': 'surface = z + h + hs (pressure term)', 'vel': 'one velocity V\n(solid and water)',
    'hs': 'hs (solid as\na thickness)', 'h': 'h (water)', 'ht': 'h_t = h + hs\n(friction depth)',
    'z': 'bed z', 'rock': 'bedrock z − sd', 'sd': 'sd\n(erodible\nlayer)',
    'a_list': [
        'C = hs / (h + hs) (mixture volume concentration), ρm / ρ = 1 + sC',
        'solid concentration of the deposit C* = 1 − λ (from fluv_porosity)',
        'hs is advected by the same edge fluxes as the water (as suspended sediment)',
        'the resistance law (§2) replaces the friction using h_t and C',
    ],
    'b': '(b) Exchange with the bed (§3)', 'b2': 'done at the landform update',
    'ero': 'erosion', 'dep': 'deposition', 'pore': 'pore water\n(f_dbwet = 1)', 'stop': 'stopped and fixed\n(f_dbstop = 1)',
    'old': 'former bed',
    'b_list': [
        'Δz = −Δh_s / C* applied equally to z and sd (the bedrock z − sd does not move)',
        'erosion up to sd, deposition up to hs; a dry cell (h ≤ dd) returns all hs to the bed',
        'f_dbwet = 1: erosion adds λ s_b |Δz| to h (bulking), deposition removes it; 2: exchange with groundwater storage h_g',
        'f_dbstop = 1: where |V| < v_stop and C > C∞ the excess goes into z at the rate w_stop (natural-dam topography)',
        'bedrock is not eroded (bedrock erosion is rock_kdb of f_rockinc)',
    ],
    'c': '(c) Direction and speed of the exchange (§3)', 'c2': 'on a slope tan θ = 0.3 (C∞ = 0.45)',
    'cx': 'mixture volume concentration C', 'cy': 'bed change per metre travelled (m)',
    'ero_side': 'erosion\n(C < C∞)', 'dep_side': 'deposition\n(C > C∞)', 'cinf': 'C∞ = 0.45',
    'f1': 'f_dbed = 1 (δe = 0.0007, δd = 0.05)', 'f2': 'f_dbed = 2 (Egashira–Ashida; no coefficient)',
    'solid': 'solid: erosion, dashed: deposition',
    'c_note': 'Erosion depth (deposit thickness) divided by the distance travelled. Both laws move toward the same C∞. The '
              'speed of f_dbed = 1 is set by δe and δd (calibration coefficients of the runout), and by default deposition is '
              'faster than erosion. f_dbed = 2 has no coefficient, and flows close to clear water erode strongly (up to sd).',
    'foot': 'Values are illustrative (φ = 35°, s = 1.65, C* = 0.6; δe and δd are the defaults). f_dbed = 3 (Takahashi–Nakagawa), 4 (entrainment proportional to speed) and 0 (no exchange) are in the text.',
 },
}


def cinf_stony(tn):
    return min(tn / (S * (TANPHI - tn)), 0.9 * CSTAR)


def rates(c):
    """Bed lowering per unit distance travelled (positive = erosion) for f_dbed = 1 and 2."""
    ci = cinf_stony(TANTH)
    r1 = np.where(c < ci, DE * (ci - c) / (CSTAR - ci), DD * (ci - c) / CSTAR)
    the = np.arctan(S * c / (S * c + 1.0) * TANPHI)
    r2 = np.tan(math.atan(TANTH) - the)
    return r1, r2, ci


def dots(ax, x0, x1, y0, y1, n, seed, color=SED, r=2.3):
    rng = np.random.default_rng(seed)
    xs = rng.uniform(x0 + 5, x1 - 5, n)
    ys = rng.uniform(y0 + 5, y1 - 5, n)
    ax.scatter(xs, ys, s=r * r, color=color, zorder=8, linewidths=0)


def panel_a(ax, t):
    panel(ax, 35, 108, t['a'])
    text(ax, 35, 136, t['a2'], size=8, color=MUTED)
    xc0, xc1 = 232, 362
    ys, yz, yr, yb = 225, 395, 465, 512           # surface, bed z, bedrock top, bottom
    box(ax, xc0, yr, xc1 - xc0, yb - yr, face=ROCK, z=2)
    box(ax, xc0, yz, xc1 - xc0, yr - yz, face=SOIL, z=2)
    box(ax, xc0, ys, xc1 - xc0, yz - ys, face=WATER, z=2)
    dots(ax, xc0, xc1, ys, yz, 44, 3)
    line(ax, [(xc0 - 8, ys), (xc1 + 8, ys)], BLUE, 1.3, z=9)
    line(ax, [(xc0 - 8, yz), (xc1 + 8, yz)], INK, 1.2, z=9)
    line(ax, [(xc0 - 8, yr), (xc1 + 8, yr)], MUTED, .9, ls='--', z=9)
    arrow(ax, [(xc0 + 22, 300), (xc1 - 22, 300)], INK, lw=1.4, size=10)
    text(ax, (xc0 + xc1) / 2, 312, t['vel'], size=7.8, ha='center', bbox=LBL)
    text(ax, xc0 - 8, ys - 8, t['surf'], size=7.8, color=BLUE, va='bottom')
    # Left: depths.
    dim(ax, (xc0 - 22, ys + 3), (xc0 - 22, yz - 3))
    text(ax, xc0 - 30, (ys + yz) / 2, t['ht'], size=7.8, ha='right', va='center')
    dim(ax, (xc0 - 22, yz + 3), (xc0 - 22, yr - 3))
    text(ax, xc0 - 30, (yz + yr) / 2, t['sd'], size=7.8, color=MUTED, ha='right', va='center')
    # Right: composition bar (hs at the bottom, h above; total h_t) and the bed labels.
    bx, bw = xc1 + 22, 18
    yhs = yz - 0.35 * (yz - ys)
    box(ax, bx, yhs, bw, yz - yhs, face=SED, z=3)
    box(ax, bx, ys, bw, yhs - ys, face=WATER, edge=BLUE, lw=.8, z=3)
    text(ax, bx + bw + 7, (yhs + yz) / 2 - 6, t['hs'], size=7.8, color=SED, va='center')
    text(ax, bx + bw + 7, (ys + yhs) / 2, t['h'], size=7.8, color=BLUE, va='center')
    text(ax, xc1 + 14, yz + 12, t['z'], size=7.8, va='center')
    text(ax, xc1 + 14, yr, t['rock'], size=7.8, color=MUTED, va='center')
    y = 540
    for s in t['a_list']:
        a = block(ax, 50, y, s, 450, size=8.0)
        text(ax, 37, y, '•', size=8.0)
        y += 24 * (a.get_text().count('\n') + 1) + 4


def panel_b(ax, t):
    x0 = 545
    panel(ax, x0, 108, t['b'])
    text(ax, x0, 136, t['b2'], size=8, color=MUTED)
    xa, xb = 560, 1030
    yr, ybot, yold = 455, 500, 380
    # Bed: eroded pocket (left), deposit (middle), stopped mound (right).
    bx = [xa, 600, 620, 690, 710, 745, 760, 835, 850, 900, 925, 975, 1000, xb]
    bz = [yold, yold, 402, 402, yold, yold, 362, 362, yold, yold, 318, 318, yold, yold]
    pts = list(zip(bx, bz))
    box(ax, xa, yr, xb - xa, ybot - yr, face=ROCK, z=2)
    poly(ax, pts + [(xb, yr), (xa, yr)], SOIL, z=2)
    poly(ax, [(745, yold), (760, 362), (835, 362), (850, yold)], MOVING, z=3)
    poly(ax, [(900, yold), (925, 318), (975, 318), (1000, yold)], TALUS, z=3)
    # Mixture over the bed (thinner where it leaves the deposit behind).
    top = [(xa, 300), (700, 300), (880, 290), (910, 296), (960, 302), (xb, 340)]
    flow_bed = [(xb, yold), (1000, yold), (975, 318), (925, 318), (900, yold), (850, yold), (835, 362), (760, 362),
                (745, yold), (710, yold), (690, 402), (620, 402), (600, yold), (xa, yold)]
    poly(ax, top + flow_bed, WATER, z=1)
    line(ax, top, BLUE, 1.2, z=6)
    line(ax, pts, INK, 1.2, z=7)
    line(ax, [(600, yold), (710, yold)], MUTED, .9, ls='--', z=8)
    line(ax, [(745, yold), (850, yold)], MUTED, .9, ls='--', z=8)
    line(ax, [(xa, yr), (xb, yr)], MUTED, .9, ls='--', z=8)
    dots(ax, xa, 880, 304, 376, 40, 7)
    text(ax, 797, yold + 6, t['old'], size=7.4, color=MUTED, ha='center')
    arrow(ax, [(640, 398), (640, 334)], SED, lw=1.6, size=10)
    text(ax, 632, 340, t['ero'], size=8.2, color=SED, ha='right', weight='bold', bbox=LBL)
    arrow(ax, [(817, 318), (817, 358)], SED, lw=1.6, size=10)
    text(ax, 826, 316, t['dep'], size=8.2, color=SED, weight='bold', bbox=LBL)
    arrow(ax, [(672, 398), (690, 345)], BLUE, lw=1.2, size=8)
    text(ax, 696, 314, t['pore'], size=7.4, color=BLUE, bbox=LBL)
    text(ax, 950, 238, t['stop'], size=7.4, color=INK, ha='center')
    line(ax, [(950, 276), (950, 316)], INK, .8, z=9)
    y = 540
    for s in t['b_list']:
        a = block(ax, x0 + 15, y, s, 470, size=8.0)
        text(ax, x0 + 2, y, '•', size=8.0)
        y += 24 * (a.get_text().count('\n') + 1) + 4


def panel_c(fig, ax, t):
    x0 = 1065
    panel(ax, x0, 108, t['c'])
    text(ax, x0, 136, t['c2'], size=8, color=MUTED)
    c = chart(fig, x0 + 75, 172, 390, 280, (0, 0.62), (1e-4, 1), xlabel=t['cx'], ylabel=t['cy'])
    c.set_yscale('log')
    cc = np.linspace(0, 0.54, 800)
    r1, r2, ci = rates(cc)
    ero, dep = cc < ci, cc > ci
    for r, col, lab in ((r1, SED, t['f1']), (r2, ORANGE, t['f2'])):
        c.plot(cc[ero], r[ero], color=col, lw=2.0, label=lab)
        c.plot(cc[dep], -r[dep], color=col, lw=2.0, ls='--')
    c.axvline(ci, color=MUTED, lw=.9, ls=':')
    c.text(ci + 0.006, 0.5, t['cinf'], fontsize=7.4, color=MUTED, va='top')
    c.text(0.012, 1.4e-4, t['ero_side'], fontsize=7.6, color=MUTED, va='bottom')
    c.text(0.615, 1.4e-4, t['dep_side'], fontsize=7.6, color=MUTED, va='bottom', ha='right')
    c.legend(loc='upper left', bbox_to_anchor=(-0.19, -0.2), fontsize=7.6, frameon=False, labelspacing=0.35)
    text(ax, x0 + 4, 560, t['solid'], size=7.6, color=MUTED)
    block(ax, x0, 588, t['c_note'], 475, size=8.0)


def build(lang):
    t = T[lang]
    fig, ax = canvas(H)
    header(ax, t['title'], t['sub'])
    panel_a(ax, t)
    line(ax, [(527, 105), (527, 830)], RULE, .8)
    panel_b(ax, t)
    line(ax, [(1047, 105), (1047, 830)], RULE, .8)
    panel_c(fig, ax, t)
    rule(ax, 35, 1540, 838)
    block(ax, 35, 848, t['foot'], 1505, size=7.9, color=MUTED)
    return fig


def draw(lang):
    return run(build, 'massflow_mixture', lang,
               'Schematic of the single-layer mixture in one cell, of its exchange with the bed (co-moving update of z and '
               'sd, pore water, stopping) and curves of the bed change per unit distance travelled versus concentration for '
               'f_dbed = 1 and 2. Not solver output.')
