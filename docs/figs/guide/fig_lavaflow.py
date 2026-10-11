"""Lava supply, yield-limited flow, solidification and terrain-mediated water flow.

Bilingual PNG/SVG schematics, not a model solution. See m_lavaflow.f90
(tick_vent, tick_flow, tick_solidify) and developer.md section 51.
"""
from pathlib import Path as FilePath
import numpy as np
from _style import *
from _schematic import (drawing_style, text, block, paragraph, line,
                        arrow as profile_arrow, monotone_cubic, export,
                        INK, MUTED, RULE)

T = {
    'ja': dict(
        title='溶岩の流動・停止・固化と、水の流れへのつながり',
        subtitle='ENCflow の等温 Bingham モデル  |  fn_lavaflow / &list_lavaflow',
        a='(a) 供給・流動と、厚さを残した停止',
        b='(b) 固化による地盤の上昇と、その上の水流',
        vent='噴火口セル', flow='溶岩の流れ', lava='未固化の溶岩 hl',
        bed='地盤 z', front='有限の\n前縁厚', rain='降雨・洪水',
        water='地表水 h', newbed='更新後の地盤 z', solid='固化した溶岩',
        oldbed='破線: 固化前の地盤',
        supply_head='1  噴火口から供給',
        supply='噴火口セル lv_cell に噴出量を等分配。\n指定: lv_q0 / lv_val [m³/s]（運動量は与えない）。',
        flow_head='2  溶岩面の勾配で流動',
        flow_rule=r'$\rho g h_e S > \tau_y$ のエッジで流動',
        flow_note='$h_e$: 両セルの平均溶岩厚。$S$: 溶岩面 z + hl の勾配。\nρ = lv_rho、η = lv_visc、$\\tau_y$ = lv_tauy。',
        stop_head='3  降伏応力による停止',
        stop_rule=r'一様斜面での目安: $h_\infty = \tau_y / (\rho g\,\tan\theta)$',
        stop_note='$\\tau_y > 0$ で、溶岩面が斜面と平行な場合。\n上の前縁は模式的で、この式の解を描いたものではない。',
        solid_head='4  停止セルの固化（lv_wsol > 0）',
        solid_note='$\\max |u_e|$ < lv_vsol のセルを転換。\n$u_e$: 各エッジの深さ平均流速。Δt: 溶岩の更新間隔。',
        transfer=r'$\Delta z = \min(\mathrm{hl},\; \mathrm{lv\_wsol}\,\Delta t)$'+'\n'+r'$\mathrm{hl} \leftarrow \mathrm{hl}-\Delta z \qquad z \leftarrow z+\Delta z$',
        rock_note='不可逆。土層 sd は増やさず、侵食されない岩盤として扱う。',
        water_head='5  地形を介して水流へ反映',
        water_note='地表水は更新後の地盤 z に従い、同じランで計算を続ける。\n未固化の hl は水の地盤に含めず、熱交換や未固化溶岩による\n直接のせき止めは扱わない。',
        model='固化は速度とレートによる近似。冷却過程は計算しない。\n出力: 溶岩厚 Hl、地盤高 Z（f_out_z）。',
        foot='模式図・縮尺任意。(b) は (a) の溶岩がすべて固化した場合の例。形状・水深・矢印は計算結果ではない。',
    ),
    'en': dict(
        title='Lava flow, stopping and solidification: how the terrain affects water',
        subtitle='ENCflow isothermal Bingham model  |  fn_lavaflow / &list_lavaflow',
        a='(a) Supply, flow and a finite-thickness front',
        b='(b) Solidified lava raises the bed beneath water',
        vent='vent cells', flow='lava flow', lava='unsolidified lava hl',
        bed='bed z', front='finite front\nthickness', rain='rain / flood',
        water='surface water h', newbed='updated bed z', solid='solidified lava',
        oldbed='dashed: bed before solidification',
        supply_head='1  Supply from vent cells',
        supply='Divide the effusion rate equally among lv_cell cells.\nSet lv_q0 / lv_val [m³/s]; no momentum is imposed.',
        flow_head='2  Flow down the lava-surface gradient',
        flow_rule=r'Flow across edges where $\rho g h_e S > \tau_y$',
        flow_note='$h_e$: mean lava thickness of the two cells.\n$S$: gradient of z + hl.  ρ = lv_rho, η = lv_visc, $\\tau_y$ = lv_tauy.',
        stop_head='3  Stopping due to yield stress',
        stop_rule=r'Uniform-slope reference: $h_\infty = \tau_y / (\rho g\,\tan\theta)$',
        stop_note='For $\\tau_y > 0$ and a lava surface parallel to the slope.\nThe front above is schematic, not a solution of this equation.',
        solid_head='4  Solidify stopped cells (lv_wsol > 0)',
        solid_note='Convert cells where $\\max |u_e|$ < lv_vsol.\n$u_e$: depth-averaged edge speed. Δt: lava update interval.',
        transfer=r'$\Delta z = \min(\mathrm{hl},\; \mathrm{lv\_wsol}\,\Delta t)$'+'\n'+r'$\mathrm{hl} \leftarrow \mathrm{hl}-\Delta z \qquad z \leftarrow z+\Delta z$',
        rock_note='Irreversible, non-erodible bedrock; soil thickness sd is not increased.',
        water_head='5  Water responds to the new terrain',
        water_note='Surface water follows the updated bed z in the same run.\nUnsolidified hl is excluded from the water bed: no heat exchange\nor direct damming by unsolidified lava.',
        model='Solidification uses a speed threshold and a rate, not cooling.\nOutputs: lava thickness Hl and bed elevation Z (f_out_z).',
        foot='Schematic, not to scale. (b) illustrates complete solidification of the lava in (a). Shapes, water depths and arrows are not simulation results.',
    ),
}

# Conceptual geometry only; finite jumps at the start/front are intentional.
START, FRONT, END = 1.0, 7.3, 10.4
BED_X = np.array([0., 1., 2.5, 4.5, 6.5, 8.2, END])
BED_Z = np.array([2.6, 2.45, 1.9, 1.2, .75, .55, .5])
LAVA_EDGE, SOLID = '#9c391f', '#ac6c5b'


def bed_elevation(x):
    """Monotone, C1 terrain through the original conceptual control points."""
    return monotone_cubic(BED_X, BED_Z, x)


def lava_thickness(x):
    """Smooth interior profile with finite, explicit start/front faces."""
    x = np.asarray(x, float)
    u = np.clip((x-START)/(FRONT-START), 0, 1)
    h = .30+.25*u*u*(3-2*u)
    return np.where((x >= START) & (x <= FRONT), h, 0.)


def profiles():
    # All fills, strokes and dimensions use the same exact contacts.
    x = np.unique(np.r_[np.linspace(0, END, 2081), BED_X, START, FRONT])
    bed = bed_elevation(x)
    mask = (x >= START) & (x <= FRONT)
    lx = x[mask]
    lower = bed[mask]
    upper = lower+lava_thickness(lx)
    return x, bed, lx, lower, upper


def deposit_outline():
    """New bed as a path, retaining vertical faces instead of mesh diagonals."""
    x, bed, lx, lower, upper = profiles()
    before, after = x < START, x > FRONT
    return np.vstack([np.c_[x[before], bed[before]],
                      [START, lower[0]], np.c_[lx, upper],
                      [FRONT, lower[-1]], np.c_[x[after], bed[after]]])


def _axes(fig, box, xlim=(0, 1), ylim=(0, 1)):
    ax = fig.add_axes(box)
    ax.set(xlim=xlim, ylim=ylim)
    ax.axis('off')
    return ax


def _dimension(ax, x, z0, z1, witness_x, color=LAVA_EDGE):
    ax.annotate('', (x, z1), (x, z0), arrowprops=dict(
        arrowstyle='<->', color=color, lw=.85, shrinkA=0, shrinkB=0,
        mutation_scale=8), zorder=10)
    for z in (z0, z1):
        line(ax, [(witness_x, z), (x+.09, z)], color, .6)


def _terrain(ax, solid=False):
    x, bed, lx, lower, upper = profiles()
    ax.fill_between(x, -.16, bed, color=C_GROUND_L, lw=0, zorder=1)
    ax.fill_between(lx, lower, upper, color=SOLID if solid else C_LAVA,
                    lw=0, zorder=2)
    if solid:
        line(ax, np.c_[lx, lower], '#745c45', 1.0, ls=(0, (4, 3)), z=4)
        line(ax, deposit_outline(), INK, 1.1)
    else:
        line(ax, np.c_[x, bed], INK, 1.)
        line(ax, np.vstack([[START, lower[0]], np.c_[lx, upper],
                           [FRONT, lower[-1]]]), LAVA_EDGE, 1.05)


def panel_lava(ax, t):
    _terrain(ax)
    text(ax, .1, 3.48, t['vent'], size=9.1, color=LAVA_EDGE)
    profile_arrow(ax, [(1.3, 3.08), (1.3, float(bed_elevation(1.3)+lava_thickness(1.3))+.03)],
                  LAVA_EDGE, 1.7, size=10)
    fx = np.linspace(2.25, 5.15, 150)
    profile_arrow(ax, np.c_[fx, bed_elevation(fx)+lava_thickness(fx)+.20], C_X, 1.8)
    text(ax, 3.65, 2.93, t['flow'], size=9.5, color=C_X)
    text(ax, 1.75, .57, t['lava'], size=9.2, color=LAVA_EDGE)
    line(ax, [(2.6, .71), (3.1, float(bed_elevation(3.1)+.20))], MUTED, .7)
    text(ax, .35, .17, t['bed'], size=8.5, color=C_GROUND)
    z0 = float(bed_elevation(FRONT))
    _dimension(ax, 7.60, z0, z0+float(lava_thickness(FRONT)), FRONT)
    text(ax, 7.95, z0+.48, t['front'], size=8.8, color=LAVA_EDGE)


def panel_solid(ax, t):
    _terrain(ax, solid=True)
    for xr in np.linspace(.8, 3.65, 10):
        line(ax, [(xr, 3.41), (xr-.07, 3.19)], C_C, .85)
    text(ax, 4.05, 3.46, t['rain'], size=9.1, color=C_C)
    # Local water ribbons avoid implying a resolved waterfall at the sharp toe.
    for lo, hi in [(1.8, 6.65), (7.9, END)]:
        wx = np.linspace(lo, hi, 250)
        wz = bed_elevation(wx)+lava_thickness(wx)
        ax.fill_between(wx, wz, wz+.105, color=C_WATER_L, lw=0, zorder=3)
        line(ax, np.c_[wx, wz+.105], C_WATER, 1.05)
    for lo, hi in [(2.40, 4.55), (8.10, 9.85)]:
        wx = np.linspace(lo, hi, 150)
        profile_arrow(ax, np.c_[wx, bed_elevation(wx)+lava_thickness(wx)+.26], C_C, 1.7)
    text(ax, 6.45, 2.76, t['water'], size=9.1, color=C_C)
    line(ax, [(6.62, 2.49), (6.25, float(bed_elevation(6.25)+lava_thickness(6.25)+.10))], C_C, .7)
    text(ax, 2.00, .66, t['solid'], size=9.1, color=LAVA_EDGE)
    line(ax, [(3.30, .79), (4.05, float(bed_elevation(4.05)+.23))], MUTED, .7)
    text(ax, 7.45, 1.87, t['newbed'], size=8.5, color=INK)
    line(ax, [(7.72, 1.63), (FRONT, float(bed_elevation(FRONT)+lava_thickness(FRONT)))], MUTED, .7)
    text(ax, .35, .17, t['oldbed'], size=8.2, color=C_GROUND)


def _heading(ax, y, s, color=INK):
    a = block(ax, 0, y, s, 1, size=9.4, color=color, weight='bold')
    ax.figure.canvas.draw()
    return ax.transData.inverted().transform(
        (0, a.get_window_extent(ax.figure.canvas.get_renderer()).y0))[1]-.023


def build(lang):
    if lang not in T:
        raise ValueError('lang must be ja or en')
    t = T[lang]
    fig = plt.figure(figsize=(13.2, 7.4))
    header = _axes(fig, [.04, .912, .92, .07])
    block(header, 0, 1, t['title'], 1, size=14, weight='bold')
    text(header, 0, .35, t['subtitle'], size=8.7, color=MUTED)
    for left, key, draw_panel in [(.04, 'a', panel_lava), (.535, 'b', panel_solid)]:
        head = _axes(fig, [left, .839, .425, .049])
        block(head, 0, 1, t[key], 1, size=10.1, weight='bold')
        ax = _axes(fig, [left, .420, .425, .414], (-.12, 10.62), (-.18, 3.7))
        draw_panel(ax, t)
    # Detail stays out of the cross-sections; each column follows its panel.
    for left, side in [(.04, 'left'), (.535, 'right')]:
        notes = _axes(fig, [left, .037, .425, .348])
        line(notes, [(0, 1.03), (1, 1.03)], RULE, .8, clip_on=False)
        y = 1
        if side == 'left':
            y = _heading(notes, y, t['supply_head'], LAVA_EDGE)
            y = paragraph(notes, 0, y, t['supply'], 1, size=8.8, gap=.046)
            y = _heading(notes, y, t['flow_head'], C_X)
            y = paragraph(notes, 0, y, t['flow_rule'], 1, size=9.1, color=LAVA_EDGE, gap=.014)
            y = paragraph(notes, 0, y, t['flow_note'], 1, size=8.7, gap=.046)
            y = _heading(notes, y, t['stop_head'], LAVA_EDGE)
            y = paragraph(notes, 0, y, t['stop_rule'], 1, size=9.1, color=LAVA_EDGE, gap=.016)
            paragraph(notes, 0, y, t['stop_note'], 1, size=8.6, color=MUTED)
        else:
            y = _heading(notes, y, t['solid_head'], LAVA_EDGE)
            y = paragraph(notes, 0, y, t['solid_note'], 1, size=8.7, gap=.018)
            y = paragraph(notes, 0, y, t['transfer'], 1, size=9.2, color=LAVA_EDGE, gap=.018)
            y = paragraph(notes, 0, y, t['rock_note'], 1, size=8.6, gap=.042)
            y = _heading(notes, y, t['water_head'], C_C)
            y = paragraph(notes, 0, y, t['water_note'], 1, size=8.7, gap=.039)
            paragraph(notes, 0, y, t['model'], 1, size=8.4, color=MUTED)
    foot = _axes(fig, [.04, .015, .92, .025])
    line(foot, [(0, 1.14), (1, 1.14)], RULE, .8, clip_on=False)
    block(foot, 0, 1, t['foot'], 1, size=8.1, color=MUTED)
    return fig


def draw(lang):
    with drawing_style():
        png = export(build(lang), out_path('lavaflow_profile', lang))
        svg = FilePath(png).with_suffix('.svg')
        svg.write_bytes(svg.read_bytes().replace(b'\r\n', b'\n'))
        return png
