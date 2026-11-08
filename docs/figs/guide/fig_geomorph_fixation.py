"""Fixation degree a of exposed bars (f_fixation; bedload section of geomorph.md).

(a) evolution of a at one bar cell through low water and floods: growth while
dry (T_fix), decay while submerged (T_dec), reset when the fixed surface is
eroded deeper than fix_dzreset; (b) where a acts. The curves evaluate the update
rules of m_geomorph_fixation for illustrative periods and parameters; the water
depth and bed history are prescribed, not computed.

Generate: python docs/figs/make_guide_figs.py geomorph_fixation
"""
import numpy as np
from _geomorph import (canvas, header, panel, rule, box, chart, run, text, block, line,
                       INK, MUTED, RULE, BLUE, SED, GREEN, WATER, PANEL, ORANGE)

H = 900
TFIX, TDEC, DZRESET = 1.0, 1.5, 10.0       # time in units of T_fix; bed in cm
WET = [(2.2, 3.0), (5.6, 6.6)]             # submerged periods (h > dd)
TEND = 9.0

T = {
 'ja': {
    'title': '内岸砂州の定着  |  定着度 a の育ち方・失い方と、効く場所',
    'sub': 'f_fixation(f_fluvial = 1 が必須)。1 つの砂州セルの説明例で、水深と河床の履歴は与えた形、a は更新則どおり。',
    'a': '(a) 1 つの砂州セルの定着度 a  — 時間は地形時間(morfac 込み)を T_fix で割った値',
    'rules': '乾燥(h ≤ dd): a ← 1 − (1 − a) exp(−Δt/T_fix)、z_ref = z\n'
             '冠水(h > dd): a ← a exp(−Δt/T_dec)(fix_tdec > 0 のとき)、z_ref = max(z_ref, z)\n'
             'z_ref − z > fix_dzreset なら a = 0、z_ref = z(定着した表層が剥がれる)',
    'h': '水深 h', 'dd': 'dd', 'wet': '冠水(出水)', 'dry': '乾燥(低水)',
    'aax': '定着度 a', 'tdec': 'fix_tdec = 1.5 T_fix(冠水中に減衰)', 'notdec': 'fix_tdec = 0(減衰なし)',
    'zax': '河床 (cm)', 'z': '河床 z', 'zref': '定着面の基準 z_ref',
    'reset': 'z_ref − z > fix_dzreset\n(10 cm) → a = 0', 'small': '削れても 10 cm 未満\nなら a は残る',
    'time': '地形時間 / T_fix',
    'b': '(b) a が効く場所',
    'eff': [
        ('掃流砂', '供給側(風上)セルの τ*c → τ*c (1 + c_τ a)', 'fix_ctau。受け手の a は見ないので、\n定着面への堆積は妨げない'),
        ('側岸侵食', '河岸セルの τ*c,b → τ*c,b (1 + c_τ,b a)', 'fix_ctau_bank(負なら c_τ、0 で河岸には効かない)'),
        ('浮遊砂', '浸食項(平衡濃度)だけを同じ c_τ で減らす', '沈降は変えない → 出水の細粒分が定着した砂州に積もる'),
        ('流れの粗度', 'Manning n → n (1 + c_n a)', 'fix_cn。流砂の τ* は変えない(植生の形状抵抗)'),
        ('河岸モードの崩落', '限界高さ → H_c (1 + c_τ,b a)', 'rf_bank = 1 のとき(崩落と崖錐)'),
    ],
    'none': '効かないもの: 安息角崩落、標高・体積(a は浸食のしにくさだけを変える)',
    'foot': '値は説明用(T_fix・T_dec・期間は推奨値ではない)。T_fix・c_τ は文献に標準値がなく必須。出水の回帰時間との比で選ぶ(本文)。',
 },
 'en': {
    'title': 'Fixation of inner-bank bars  |  How the fixation degree a grows and is lost, and where it acts',
    'sub': 'f_fixation (requires f_fluvial = 1). Illustration for one bar cell: water depth and bed history are prescribed; a follows the update rules.',
    'a': '(a) Fixation degree a of one bar cell  — time is landform time (morfac included) divided by T_fix',
    'rules': 'dry (h ≤ dd): a ← 1 − (1 − a) exp(−Δt/T_fix), z_ref = z\n'
             'submerged (h > dd): a ← a exp(−Δt/T_dec) (when fix_tdec > 0), z_ref = max(z_ref, z)\n'
             'if z_ref − z > fix_dzreset: a = 0, z_ref = z (the fixed surface layer is stripped)',
    'h': 'depth h', 'dd': 'dd', 'wet': 'submerged (flood)', 'dry': 'dry (low water)',
    'aax': 'fixation a', 'tdec': 'fix_tdec = 1.5 T_fix (decay when submerged)', 'notdec': 'fix_tdec = 0 (no decay)',
    'zax': 'bed (cm)', 'z': 'bed z', 'zref': 'reference of the fixed surface z_ref',
    'reset': 'z_ref − z > fix_dzreset\n(10 cm) → a = 0', 'small': 'eroded by less than\n10 cm: a is kept',
    'time': 'landform time / T_fix',
    'b': '(b) Where a acts',
    'eff': [
        ('Bedload', 'τ*c of the donor (upwind) cell → τ*c (1 + c_τ a)', 'fix_ctau. The receiver\'s a is not used, so deposition on a fixed surface is not hindered'),
        ('Bank erosion', 'τ*c,b of the bank cell → τ*c,b (1 + c_τ,b a)', 'fix_ctau_bank (negative: same as c_τ; 0: no effect on banks)'),
        ('Suspended sediment', 'only the erosion term (equilibrium concentration) is reduced by the same c_τ', 'settling unchanged → flood fines settle on fixed bars'),
        ('Flow roughness', 'Manning n → n (1 + c_n a)', 'fix_cn. The τ* of sediment is unchanged (form drag of vegetation)'),
        ('Bank-mode failure', 'critical height → H_c (1 + c_τ,b a)', 'with rf_bank = 1 (rockfall and talus)'),
    ],
    'none': 'No effect on: angle-of-repose collapse, elevation or volume (a only changes how hard it is to erode)',
    'foot': 'Values are illustrative (T_fix, T_dec and the periods are not recommendations). T_fix and c_τ have no standard literature values and are required; choose them relative to the flood return period (see text).',
 },
}


def wet_at(t):
    return any(a <= t < b for a, b in WET)


def histories(n=1801):
    t = np.linspace(0, TEND, n)
    dt = t[1] - t[0]
    # Prescribed bed history (cm): deposition then mild erosion in flood 1, deep erosion in flood 2.
    z = np.zeros_like(t)
    for k, tk in enumerate(t):
        if tk < 2.2:
            z[k] = 0.0
        elif tk < 2.6:
            z[k] = 4.0 * (tk - 2.2) / 0.4
        elif tk < 3.0:
            z[k] = 4.0 - 3.0 * (tk - 2.6) / 0.4
        elif tk < 5.6:
            z[k] = 1.0
        elif tk < 6.6:
            z[k] = 1.0 - 13.0 * (tk - 5.6) / 1.0
        else:
            z[k] = -12.0
    out = {}
    for key, tdec in (('dec', TDEC), ('nodec', 0.0)):
        a = np.zeros_like(t); zref = np.zeros_like(t); resets = []
        ak, zr = 0.0, 0.0
        for k, tk in enumerate(t):
            if k > 0:
                if wet_at(tk):
                    if tdec > 0:
                        ak *= np.exp(-dt / tdec)
                    zr = max(zr, z[k])
                    if zr - z[k] > DZRESET:
                        ak, zr = 0.0, z[k]
                        resets.append(tk)
                else:
                    ak = 1.0 - (1.0 - ak) * np.exp(-dt / TFIX)
                    zr = z[k]
            a[k], zref[k] = ak, zr
        out[key] = (a, zref, resets)
    depth = np.zeros_like(t)
    for a0, b0 in WET:
        m = (t >= a0) & (t < b0)
        depth[m] = np.sin(np.pi * (t[m] - a0) / (b0 - a0)) ** .6
    return t, depth, z, out


def shade(ax):
    for a0, b0 in WET:
        ax.axvspan(a0, b0, color=WATER, lw=0, zorder=0)


def panel_series(fig, ax, t):
    panel(ax, 35, 108, t['a'])
    box(ax, 35, 145, 990, 92, face=PANEL)
    block(ax, 52, 156, t['rules'], 960, size=8.6)
    tt, depth, z, out = histories()
    a_dec, zref_dec, resets = out['dec']
    a_no, _, _ = out['nodec']
    left, width = 130, 880
    # Water depth at the cell (shape only) and the dry threshold dd.
    c1 = chart(fig, left, 262, width, 92, (0, TEND), (-.12, 1.2), ylabel=t['h'])
    shade(c1)
    c1.plot(tt, depth, color=BLUE, lw=1.5)
    c1.axhline(.06, color=MUTED, lw=.8, ls='--')
    c1.text(TEND - .05, .1, t['dd'], color=MUTED, fontsize=8, ha='right', va='bottom')
    c1.set_yticks([]); c1.set_xticklabels([])
    c1.text(2.6, 1.08, t['wet'], color=BLUE, fontsize=8.2, ha='center', va='bottom')
    c1.text(1.1, .35, t['dry'], color=MUTED, fontsize=8.2, ha='center')
    # Fixation degree.
    c2 = chart(fig, left, 380, width, 190, (0, TEND), (-.05, 1.08), ylabel=t['aax'])
    shade(c2)
    c2.plot(tt, a_no, color=GREEN, lw=1.3, ls='--', label=t['notdec'])
    c2.plot(tt, a_dec, color=GREEN, lw=2.0, label=t['tdec'])
    c2.set_xticklabels([])
    c2.legend(loc='lower center', bbox_to_anchor=(.47, .02), fontsize=8, frameon=False)
    for r in resets:
        c2.plot([r], [0], 'o', color=ORANGE, ms=5, zorder=5)
    # Bed and the reference of the fixed surface.
    c3 = chart(fig, left, 595, width, 190, (0, TEND), (-15, 8), xlabel=t['time'], ylabel=t['zax'])
    shade(c3)
    c3.plot(tt, zref_dec, color=ORANGE, lw=1.3, ls='--', label=t['zref'])
    c3.plot(tt, z, color=SED, lw=1.8, label=t['z'])
    c3.legend(loc='lower left', fontsize=8, frameon=False)
    r = resets[0]
    c3.annotate(t['reset'], xy=(r, 1.0 - 13.0 * (r - 5.6)), xytext=(6.95, 3.2), fontsize=8.2, color=ORANGE,
                arrowprops=dict(arrowstyle='-|>', color=ORANGE, lw=1.0), va='center')
    c3.annotate(t['small'], xy=(2.95, 1.2), xytext=(3.4, 5.6), fontsize=8.2, color=MUTED,
                arrowprops=dict(arrowstyle='-|>', color=MUTED, lw=.8), va='center')


def panel_effects(ax, t):
    x = 1062
    panel(ax, x, 108, t['b'])
    y = 148
    for name, what, note in t['eff']:
        rule(ax, x, 1540, y)
        text(ax, x, y + 10, name, size=9, weight='bold')
        yb = y + 36
        a = block(ax, x, yb, what, 478, size=8.6, color=SED)
        nlines = a.get_text().count('\n') + 1
        b = block(ax, x, yb + 24 * nlines + 4, note, 478, size=8.2, color=MUTED)
        y = yb + 24 * nlines + 4 + 22 * (b.get_text().count('\n') + 1) + 14
    rule(ax, x, 1540, y)
    block(ax, x, y + 12, t['none'], 478, size=8.4)


def build(lang):
    t = T[lang]
    fig, ax = canvas(H)
    header(ax, t['title'], t['sub'])
    panel_series(fig, ax, t)
    line(ax, [(1042, 105), (1042, 835)], RULE, .8)
    panel_effects(ax, t)
    rule(ax, 35, 1540, 840)
    block(ax, 35, 852, t['foot'], 1505, size=8.2, color=MUTED)
    return fig


def draw(lang):
    return run(build, 'geomorph_fixation', lang,
               'Schematic evolution of the fixation degree a at one bar cell (growth while dry, decay while '
               'submerged, reset after erosion deeper than fix_dzreset) and where a acts. Water depth and bed '
               'history are prescribed; not solver output.')
