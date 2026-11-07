"""Wave-driven longshore transport fn_wave (geomorph.md): what one landform update does.

(a) plan view of a delta: surf zone, local shoreline orientation from smoothed
depths, exposure that is blocked behind dry land (shadow), the river-mouth rule
wave_vmax, and the alongshore flux along t-hat; (b) the deep-water CERC shape
cos^(6/5) a sin a; (c) the four steps and options. The plan view evaluates the
flux shape for the drawn shoreline; it is a schematic, not solver output.

Generate: python docs/figs/make_guide_figs.py geomorph_wave
"""
import numpy as np
from matplotlib.path import Path
from _geomorph import (canvas, header, panel, rule, box, poly, chart, run,
                       text, block, line, arrow, INK, MUTED, RULE,
                       SOIL, WATER, BLUE, SED, GREEN, ORANGE, PANEL)

H = 980
DIR = np.radians(30.0)                       # travel direction, CCW from east (north = 90 deg)
WV = np.array([np.cos(DIR), -np.sin(DIR)])   # pixel frame (y down)

T = {
 'ja': {
    'title': '波浪による沿岸漂砂  |  1 回の地形更新で行うこと(fn_wave の簡易モード)',
    'sub': '波は解かない。沖の波(H₀・T・進行方向 φ₀)を与件に、砕波帯の岸平行の流束を掃流砂の経路に乗せる(f_fluvial = 1 が必須)。図は説明用。',
    'a': '(a) 平面: デルタの汀線と砕波帯',
    'land': '陸', 'sea': '海(通常セル+初期水位)', 'surf': '砕波帯(湿潤で h ≤ H_b/γ)',
    'waves': '沖の波の進行方向 φ₀', 'shadow': '陰: 波の風上に乾いた陸がある(露出度 0)',
    'mouth': '|V| > wave_vmax のセルは\n源にも砕波帯にもならない', 'river': '河道',
    'normal': 'n̂(沖向きの法線)', 'alpha': 'α', 'flux': '岸平行の流束 q = Q_s / W_b(t̂ の向き)',
    'b': '(b) 沖波で書いた CERC 式の角度依存',
    'bx': '波の進行方向と岸向き法線のなす角 α (度)', 'by': 'cos^{6/5}α sin α',
    'low': '低角: 凹凸を均す', 'high': '高角: 凸部が育つ', 'peak': '最大 ≈ 42°',
    'c': '(c) 4 つの手順と主な選択',
    'steps': ['砕波帯: 湿潤で水深 h ≤ H_b/γ のセル\n(砕波波高 H_b = 0.39 g^{1/5} (T H₀²)^{2/5}、γ = wave_gamma)',
              '汀線方位: 平滑化した水深(wave_lsm、既定 0 はセル半径 wave_smooth の核)の勾配から n̂・t̂。勾配 < wave_smin と、波が岸から離れる向きのセルは対象外',
              '露出度: 砕波帯より深い湿潤セルを源に、波の風上から 1 更新 1 セルずつ伝える。乾いたセルで途切れる(回折なし)',
              '流束: Q_s = K₂ H₀^{12/5} T^{1/5} cos^{6/5}α sin α を砕波帯の幅 W_b = max((H_b/γ)/S, Δx) で割り、掃流砂と同じエッジ流束に(供給量制限・dzmax・保存則は共通)'],
    'opts': ['wave_vmax: 可動河床の河口では必須(流速が超えるセルは陰)',
             'f_wave_shadow = 1: 水没砂州の陰の流束を (h_天端 / h_トラフ)^{5/2} 倍',
             '乾いたセルへは運ばない(乾いた浜の後退は f_repose)。海域マスクのセルは源にも砕波帯にもならない'],
    'foot': '回折・岸沖輸送・セットアップ・離岸流・多方向スペクトルは扱わない。波を解いて過程の漂砂を求めるのは f_wfsed(沿岸の波浪場)。',
 },
 'en': {
    'title': 'Wave-driven longshore transport  |  What one landform update does (fn_wave simple mode)',
    'sub': 'Waves are not solved: given offshore waves (H₀, T, direction φ₀), an alongshore flux in the surf zone is put on the bedload path (requires f_fluvial = 1). Illustrative.',
    'a': '(a) Plan view: delta shoreline and surf zone',
    'land': 'land', 'sea': 'sea (ordinary cells + initial level)', 'surf': 'surf zone (wet, h ≤ H_b/γ)',
    'waves': 'offshore wave direction φ₀', 'shadow': 'shadow: dry land upwind (exposure 0)',
    'mouth': 'cells with |V| > wave_vmax are\nneither sources nor surf zone', 'river': 'channel',
    'normal': 'n̂ (offshore normal)', 'alpha': 'α', 'flux': 'alongshore flux q = Q_s / W_b (along t̂)',
    'b': '(b) Angle dependence of the deep-water CERC formula',
    'bx': 'angle α between wave direction and shoreward normal (deg)', 'by': 'cos^{6/5}α sin α',
    'low': 'low: smooths bumps', 'high': 'high: bumps grow', 'peak': 'max ≈ 42°',
    'c': '(c) The four steps and main options',
    'steps': ['Surf zone: wet cells with depth h ≤ H_b/γ\n(breaking height H_b = 0.39 g^{1/5} (T H₀²)^{2/5}, γ = wave_gamma)',
              'Shoreline orientation: n̂, t̂ from the gradient of the smoothed depth; wave_lsm sets the smoothing (default 0: a kernel of wave_smooth cells). Cells with a gradient < wave_smin or waves heading offshore are skipped',
              'Exposure: from wet cells deeper than the surf zone, passed one cell per update from the upwind side; dry cells interrupt it (no diffraction)',
              'Flux: Q_s = K₂ H₀^{12/5} T^{1/5} cos^{6/5}α sin α divided by the surf-zone width W_b = max((H_b/γ)/S, Δx), applied as bedload edge fluxes (shared supply limit, dzmax and conservation)'],
    'opts': ['wave_vmax: required at mobile-bed river mouths (faster cells are shadowed)',
             'f_wave_shadow = 1: flux behind submerged bars × (h_crest/h_trough)^{5/2}',
             'No transport onto dry cells (dry beach retreat is f_repose). Sea-mask cells are neither sources nor surf zone'],
    'foot': 'No diffraction, cross-shore transport, setup, rip currents or directional spectra. Solving the waves for process-based transport is f_wfsed (coastal wave field).',
 },
}


def shoreline(x):
    return 330 + 190 * np.exp(-((x - 430) / 112) ** 2)


def offset(x, y, d):
    """Offset a polyline by d along its seaward (downward) unit normal."""
    dx, dy = np.gradient(x), np.gradient(y)
    n = np.column_stack((-dy, dx))
    n /= np.linalg.norm(n, axis=1)[:, None]
    n[n[:, 1] < 0] *= -1
    return x + d * n[:, 0], y + d * n[:, 1], n


def panel_plan(ax, t):
    panel(ax, 35, 108, t['a'])
    x0, x1, y0, y1 = 50, 900, 140, 790
    xs = np.linspace(x0, x1, 400)
    ys = shoreline(xs)
    box(ax, x0, y0, x1 - x0, y1 - y0, face='#cfe3f2', z=0)
    for d, col in [(150, '#bcd8ee'), (230, '#a9cce8')]:
        yo = ys + d
        poly(ax, list(zip(xs, np.convolve(yo, np.ones(41) / 41, 'same'))) + [(x1, y1), (x0, y1)], col, z=0)
    box(ax, x0, y1 - 4, x1 - x0, 4, face='#a9cce8', z=0)
    bx, by, nrm = offset(xs, ys, 46)
    surf = poly(ax, list(zip(xs, ys)) + list(zip(bx[::-1], by[::-1])), '#e9f2df', z=1)
    poly(ax, list(zip(xs, ys)) + [(x1, y0), (x0, y0)], SOIL, z=2)
    line(ax, list(zip(xs, ys)), INK, 1.1, z=6)
    line(ax, list(zip(bx, by)), GREEN, .9, ls='--', z=6)
    # Shadow: points of the surf band whose upwind ray meets dry land before deep water.
    band = Path(np.vstack([np.column_stack((xs, ys)), np.column_stack((bx[::-1], by[::-1]))]))
    land = Path(np.vstack([np.column_stack((xs, ys)), [[x1, y0], [x0, y0]]]))
    gx, gy = np.meshgrid(np.arange(x0, x1, 3.0), np.arange(y0, y1, 3.0))
    pts = np.column_stack((gx.ravel(), gy.ravel()))
    inb = band.contains_points(pts)
    shadow = np.zeros(len(pts), bool)
    steps = np.arange(4, 260, 4)
    for k in np.where(inb)[0]:
        ray = pts[k] - np.outer(steps, WV)
        shadow[k] = land.contains_points(ray).any()
    sp = pts[inb & shadow]
    ax.scatter(sp[:, 0], sp[:, 1], s=1.2, color='#8a8a8a', marker='s', lw=0, zorder=3)
    # River channel and the fast plume at its mouth.
    poly(ax, [(422, y0), (438, y0), (438, shoreline(430) + 2), (422, shoreline(430) + 2)], '#8fc3e6', z=4)
    th = np.linspace(0, np.pi, 40)
    plume = np.column_stack((430 + 30 * np.cos(th), shoreline(430) + 52 * np.sin(th)))
    plume_path = Path(np.vstack([plume, [[460, shoreline(460) - 30], [400, shoreline(400) - 30]]]))
    poly(ax, plume, 'white', edge=ORANGE, lw=1.0, z=5, hatch='////', alpha=.9)
    poly(ax, [(422, 300), (438, 300), (438, shoreline(430)), (422, shoreline(430))], 'white', edge=ORANGE, lw=.8, z=5, hatch='////')
    text(ax, 470, 590, t['mouth'], size=8.0, color=ORANGE)
    line(ax, [(468, 598), (452, 560)], MUTED, .7, z=9)
    text(ax, 446, 200, t['river'], size=8.0, color=BLUE)
    # Offshore wave crests and direction.
    tvec = np.array([WV[1], -WV[0]])
    for c in np.arange(-2, 3):
        p0 = np.array([200, 680]) + c * 40 * WV
        line(ax, [p0 - 55 * tvec, p0 + 55 * tvec], BLUE, 1.0, z=6)
    arrow(ax, [(110, 735), (110 + 130 * WV[0], 735 + 130 * WV[1])], BLUE, lw=2.0, size=12)
    text(ax, 62, 748, t['waves'], size=8.2, color=BLUE)
    # Alongshore flux arrows on exposed shore sections (length ~ Q shape).
    def q_at(i):
        n = nrm[i]
        a = np.arctan2(WV[0] * n[1] - WV[1] * n[0], -(WV @ n))   # angle from the shoreward normal
        if -(WV @ n) <= 0:
            return 0.0, a
        return np.cos(a) ** 1.2 * np.sin(a), a
    for i in range(18, 390, 26):
        p = np.array([xs[i], ys[i]]) + 23 * nrm[i]
        if band.contains_point(p) and not plume_path.contains_point(p) and not (land.contains_points(p - np.outer(steps, WV)).any()):
            q, a = q_at(i)
            tdir = np.array([nrm[i][1], -nrm[i][0]])
            if q != 0:
                L = 70 * q
                arrow(ax, [p - .5 * L * tdir, p + .5 * L * tdir], SED, lw=1.6, size=9)
    # Orientation and angle at one point on the west flank.
    i = 58
    p = np.array([xs[i], ys[i]])
    n = nrm[i]
    arrow(ax, [p, p + 58 * n], INK, lw=1.1, size=8)
    text(ax, p[0] - 6, p[1] + 62, t['normal'], size=8.0, ha='left', va='top')
    arrow(ax, [p - 70 * WV, p], BLUE, lw=1.4, size=9)
    line(ax, [p, p - 80 * n], INK, .9, ls=':', z=8)
    line(ax, [p, p + 80 * WV], BLUE, .9, ls=':', z=8)
    a1, a2 = np.arctan2(n[1], -n[0]), np.arctan2(-WV[1], WV[0])
    arc = np.linspace(min(a1, a2), max(a1, a2), 24)
    line(ax, np.column_stack((p[0] + 52 * np.cos(arc), p[1] - 52 * np.sin(arc))), BLUE, 1.1, z=8)
    am = (a1 + a2) / 2
    text(ax, p[0] + 66 * np.cos(am), p[1] - 66 * np.sin(am), t['alpha'], size=10, color=BLUE, ha='center', va='center')
    text(ax, 60, 150, t['land'], size=8.6, weight='bold', color='#7a6236')
    text(ax, 620, 700, t['sea'], size=8.2, color=BLUE)
    text(ax, 600, 420, t['surf'], size=8.2, color=GREEN)
    text(ax, 560, 262, t['shadow'], size=8.0, color='#555')
    line(ax, [(640, 280), (660, 342)], MUTED, .7, z=9)
    arrow(ax, [(52, 812), (92, 812)], SED, lw=1.6, size=9)
    text(ax, 100, 804, t['flux'], size=8.2, color=SED)


def panel_cerc(fig, ax, t):
    panel(ax, 935, 108, t['b'])
    a = np.linspace(0, 90, 400)
    q = np.cos(np.radians(a)) ** 1.2 * np.sin(np.radians(a))
    c = chart(fig, 1010, 150, 510, 230, (0, 90), (0, .5), xlabel=t['bx'], ylabel=t['by'])
    ap = np.degrees(np.arctan(np.sqrt(5 / 6)))
    c.axvspan(0, ap, color='#eef5ea', lw=0)
    c.axvspan(ap, 90, color='#fbefe6', lw=0)
    c.plot(a, q, color=SED, lw=2.0)
    c.axvline(ap, color=MUTED, lw=.8, ls=':')
    c.text(ap + 1.5, .30, t['peak'], fontsize=8, color=MUTED, va='top')
    c.text(2, .49, t['low'], fontsize=8, color=GREEN, va='top')
    c.text(89, .49, t['high'], fontsize=8, color=ORANGE, ha='right', va='top')
    c.set_xticks([0, 15, 30, 45, 60, 75, 90])


def panel_steps(ax, t):
    panel(ax, 935, 438, t['c'])
    y = 474
    for k, s in enumerate(t['steps']):
        ax.add_patch(__import__('matplotlib').patches.Circle((945, y + 10), 10, facecolor='white', edgecolor=INK, lw=.9, zorder=15))
        text(ax, 945, y + 10, str(k + 1), size=7.6, weight='bold', ha='center', va='center')
        a = block(ax, 963, y, s, 577, size=8.1)
        y += 22 * (a.get_text().count('\n') + 1) + 8
    box(ax, 935, y + 2, 605, 3, face=RULE)
    y += 14
    for s2 in t['opts']:
        a = block(ax, 935, y, '• ' + s2, 605, size=8.0, color=MUTED)
        y += 21 * (a.get_text().count('\n') + 1)


def build(lang):
    t = T[lang]
    fig, ax = canvas(H)
    header(ax, t['title'], t['sub'])
    panel_plan(ax, t)
    line(ax, [(918, 105), (918, 920)], RULE, .8)
    panel_cerc(fig, ax, t)
    panel_steps(ax, t)
    rule(ax, 35, 1540, 928)
    block(ax, 35, 938, t['foot'], 1505, size=8.1, color=MUTED)
    return fig


def draw(lang):
    return run(build, 'geomorph_wave', lang,
               'Schematic of fn_wave longshore transport: surf zone, local shoreline orientation, exposure blocked '
               'by dry land (shadow), river-mouth rule wave_vmax, alongshore flux, and the deep-water CERC angle '
               'dependence. Not solver output.')
