"""Coastal wave field explained (users_guide/wavefield_models.md).

Two figures:
  wavefield_scheme   directional bins and their cos^s spectrum, the two-link upwind
                     decomposition on the 8-neighbour grid, the virtual senders of the
                     sides and the corner priority, and the width of shadow edges.
  wavefield_current  waves on a current: the dispersion relation with a current
                     solved graphically, wavenumber and height along an opposing or
                     following current up to blocking, the blocking speed against
                     period and depth, and a schematic river-mouth jet.

What is computed here: the bin weights (cos^s with the Kuik et al. 1988 spreading,
normalised over the bins as in sec. 2.4), the steady two-link upwind solution of a
half-plane in a uniform medium (sec. 3: E_ij = (1 - tan t) E_i-1,j + tan t E_i-1,j-1),
the dispersion relation with a current (omega - k U)^2 = g k tanh kh on the branch
continuous from U = 0, wave action flux conservation (c_g + U) E/sigma = const
(sec. 7), and the blocking point c_g + U = 0.  The river-mouth panel is a schematic.
Regenerate only this page with make_guide_figs.py wavefield_models.
"""
from _terms import *
from _wave import G, wavenumber, group, spreading_exponent, paragraph, fit_height
from matplotlib.colors import LinearSegmentedColormap

T = {'ja': {
 # scheme
 'sa': '(a) 方向ビンと沖の波の方向分布',
 'sb': '(b) 2 リンク分解の風上法',
 'sc': '(c) 辺の外の仮想の送り手',
 'sd': '(d) 陰の縁の幅(一様な媒質の半平面。2 リンク分解の定常解)',
 'a1': 'N_θ = 40(既定。ビン幅 9°)。8 の倍数なので軸(0°・90°…)と対角(45°・135°…)の向きがビンの中心に乗る',
 'a2': '棒: 沖の波のビン別エネルギー。cos^s(θ − θ₀)、θ₀ = 20°、方向分散 σθ = 20°',
 'a3': '屈折: c_θ でエネルギーが隣のビンへ移る(セルごとに陰的に解く)',
 'vel': 'c_g ê_m',
 'axis': '軸へ: 率 |p_x| − |p_y|',
 'diag': '対角へ: 率 |p_y|',
 'b1': 'ビン m の伝播速度を、その向きを挟む 2 本の格子方向(軸と対角)へ非負に分ける。p_x = c_g cos θ/Δx、p_y = c_g sin θ/Δy(|p_x| ≥ |p_y| のとき)',
 'b2': '向きが軸(0°)か対角(45°)なら 1 本のリンクだけを使い、格子方向の伝播に横断の数値拡散がない',
 'b3': '受け手が 8 近傍の送り手から集める形で、セルの処理順に依らない',
 'inc': '1 入射: 沖の波のビン別エネルギー',
 'sideW': '入射の辺(W)', 'sideS': '側方 Neumann の辺(S)', 'inside': '領域の内側',
 'neu': '2 側方 Neumann: 内側のセルの値を写す',
 'corner': '角: 入射 > 側方 Neumann > 吸収 の優先 → 沖の波',
 'c1': '0 吸収の辺の仮想の送り手は 0。各リンクの送り手は 1 つで、角で二重に注入しない。外へ出る波は自由に出る(反射なし)',
 'c2': '図の向き: θ = 25°(東と北東のリンクで運ぶ)',
 'ang0': 'θ = 0°(軸)', 'ang1': 'θ = 22.5°', 'ang2': 'θ = 45°(対角)',
 'bw': '防波堤', 'geo': '幾何の陰の縁',
 'px': '縁に直角な距離(セル。陰が負)',
 'py': 'E/E₀',
 'd1': '縁の幅(10〜90 %)は 100 セル進んだ位置で、格子方向で 1 セル未満、その間の向きで約 10〜12 セル。数値拡散によるぼけで、回折(陰に回り込む波)ではない。周期 8 s・水深 10 m の半平面回折の幅は距離 1 km で約 220 m(Δx = 10 m なら 22 セル)',
 # current
 'ca': '(a) 流れの上の分散関係の作図解(水深 3 m・周期 2.5 s)',
 'cb': '(b) 流れに沿う波数と波高',
 'cc': '(c) 阻止の流速(深海の極限は gT/8π)',
 'cd': '(d) 河口の噴流と沖からの波(模式図)',
 'k': '波数 k (rad/m)',
 'om': '角周波数 (rad/s)',
 'sig0': '流れのない分散関係 σ₀(k) = √(gk tanh kh)',
 'l0': 'U = 0: σ = ω',
 'lopp': '逆流 U = −0.5 m/s',
 'lfol': '順流 U = +0.5 m/s',
 'lblk': '阻止 U = −0.98 m/s(接する)',
 'a_opp': '逆流: k が大きく(波長が縮み)σ > ω',
 'a_fol': '順流: 波長が伸びる',
 'a_blk': 'これより強い逆流では根がない(阻止)。接点で c_g + U = 0',
 'U': '波の進む向きの流速成分 U (m/s)。負 = 逆流',
 'kk0': 'k/k₀',
 'HH0': 'H/H₀',
 'sigom': 'σ/ω',
 'blk': '阻止',
 'b_note': '(a) と同じ波で、作用量の流束 (c_g + U)E/σ を保存し、砕波は入れていない。阻止の手前の急峻化は砕波で頭打ちになる(モデルはこれを表す)',
 'T': '周期 T (s)',
 'Ub': '阻止の流速 |U| (m/s)',
 'deep': '深海の極限 gT/8π',
 'hlab': '水深 {h} m',
 'c_note': '周期の短い風波ほど弱い逆流で止まる。うねり(周期 8 s 以上)を止めるには、水深 1〜10 m で 2〜3 m/s を超える逆流が要る',
 'river': '河道', 'jet': '噴流(逆流)', 'wavesin': '沖からの波',
 'blocked': '灰色: 阻止(分散関係の根がない)。届いた作用量は台帳の blocked に記録して除く',
 'dopp': '逆流の上で波長が縮み、波高が増す(ドップラー効果)',
 'refr': '流れの速さの差で峰が曲がる(流れによる屈折)',
 'd_note': '水深 3 m・周期 2.5 s。峰は各位置の流れの上の波数で位相を岸沖方向に積分して描いた説明用の模式図(波向線の曲がりは入れていない。ENCflow の計算結果ではない)',
}, 'en': {
 'sa': '(a) Directional bins and spectrum',
 'sb': '(b) Two-link upwind decomposition',
 'sc': '(c) Virtual senders outside the sides',
 'sd': '(d) Width of shadow edges (half-plane in a uniform medium; steady two-link solution)',
 'a1': 'N_θ = 40 (default; bin width 9°). A multiple of 8, so the axis (0°, 90°, ...) and diagonal (45°, 135°, ...) directions are bin centres',
 'a2': 'bars: offshore energy per bin. cos^s(θ − θ₀), θ₀ = 20°, spreading σθ = 20°',
 'a3': 'refraction: c_θ moves energy to the neighbouring bins (solved implicitly in each cell)',
 'vel': 'c_g ê_m',
 'axis': 'to the axis: rate |p_x| − |p_y|',
 'diag': 'to the diagonal: rate |p_y|',
 'b1': 'The propagation velocity of bin m is split non-negatively into the two grid directions (axis and diagonal) that bracket it. p_x = c_g cos θ/Δx, p_y = c_g sin θ/Δy (when |p_x| ≥ |p_y|)',
 'b2': 'A direction along an axis (0°) or a diagonal (45°) uses a single link: no crosswind numerical diffusion for propagation along the grid directions',
 'b3': 'Receivers gather from their 8 neighbouring senders, so the result does not depend on the order of the cells',
 'inc': '1 incident: offshore energy per bin',
 'sideW': 'incident side (W)', 'sideS': 'lateral Neumann side (S)', 'inside': 'inside the domain',
 'neu': '2 lateral Neumann: copy of the inside cell',
 'corner': 'corner: incident > lateral Neumann > absorbing → offshore waves',
 'c1': 'The virtual sender of an absorbing (0) side holds 0. Each link has one sender, so nothing is injected twice at a corner. Outgoing waves leave freely (no reflection)',
 'c2': 'direction drawn: θ = 25° (carried by the east and north-east links)',
 'ang0': 'θ = 0° (axis)', 'ang1': 'θ = 22.5°', 'ang2': 'θ = 45° (diagonal)',
 'bw': 'breakwater', 'geo': 'geometric edge',
 'px': 'distance normal to the edge (cells; shadow negative)',
 'py': 'E/E₀',
 'd1': 'The 10–90 % edge width 100 cells downstream is under one cell along the grid directions and about 10–12 cells in between. This is blurring by numerical diffusion, not diffraction (waves bending into the shadow). The half-plane diffraction width for an 8 s period in 10 m depth is about 220 m at 1 km (22 cells for Δx = 10 m)',
 'ca': '(a) Dispersion relation on a current (depth 3 m, period 2.5 s)',
 'cb': '(b) Wavenumber and height along the current',
 'cc': '(c) Blocking current speed (deep-water limit gT/8π)',
 'cd': '(d) A river-mouth jet and waves from offshore (schematic)',
 'k': 'wavenumber k (rad/m)',
 'om': 'angular frequency (rad/s)',
 'sig0': 'dispersion without current σ₀(k) = √(gk tanh kh)',
 'l0': 'U = 0: σ = ω',
 'lopp': 'opposing U = −0.5 m/s',
 'lfol': 'following U = +0.5 m/s',
 'lblk': 'blocking U = −0.98 m/s (tangent)',
 'a_opp': 'opposing: larger k (shorter waves), σ > ω',
 'a_fol': 'following: longer waves',
 'a_blk': 'no root for a stronger opposing current (blocking); c_g + U = 0 at the tangent point',
 'U': 'current component in the wave direction U (m/s); negative = opposing',
 'kk0': 'k/k₀',
 'HH0': 'H/H₀',
 'sigom': 'σ/ω',
 'blk': 'blocking',
 'b_note': 'Same wave as (a), with the wave action flux (c_g + U)E/σ conserved and no breaking. The steepening before blocking is capped by breaking, which the model represents',
 'T': 'period T (s)',
 'Ub': 'blocking current speed |U| (m/s)',
 'deep': 'deep-water limit gT/8π',
 'hlab': 'depth {h} m',
 'c_note': 'The shorter the period, the weaker the opposing current that blocks it. Blocking swell (8 s or longer) needs an opposing current of more than 2–3 m/s in depths of 1–10 m',
 'river': 'river', 'jet': 'jet (opposing current)', 'wavesin': 'waves from offshore',
 'blocked': 'grey: blocking (no root of the dispersion relation); the wave action that arrives is removed and recorded as blocked in the ledger',
 'dopp': 'over the opposing current the waves shorten and grow (Doppler shift)',
 'refr': 'crests turn where the current speed differs (refraction by currents)',
 'd_note': 'Depth 3 m, period 2.5 s. Crests drawn by integrating the phase cross-shore with the wavenumber on the local current: a schematic without ray bending, not an ENCflow result',
}}

NAVY, SKY = '#1d4f91', '#8fb3dc'
CMAP = LinearSegmentedColormap.from_list('wf', ['#ffffff', '#d6e6f8', '#8db9ea', '#4a8fdc'])


# ----------------------------------------------------------------------------- scheme
NTH, TH0, SIG = 40, 20.0, 20.0


def bin_weights():
    """cos^s(theta - theta0) on the bin centres m 360/N, normalised so that sum D dtheta = 1."""
    th = np.arange(NTH) * 2 * np.pi / NTH
    d = np.angle(np.exp(1j * (th - np.radians(TH0))))
    s = spreading_exponent(SIG)
    D = np.clip(np.cos(d), 0.0, None)**s                       # zero beyond 90 deg from theta0
    return th, D / (D.sum() * 2 * np.pi / NTH)


def half_plane(theta, nx, ny, j0, lit_below=True):
    """Steady two-link upwind solution, 0 <= theta <= 45 deg, unit cells, uniform speed.

    Inflow column i = 0 lit for j < j0 (breakwater above) when lit_below, else lit for j >= j0.
    The south side feeds the diagonal links with the lit (lit_below) or shadow value.
    """
    t = np.tan(np.radians(theta))
    E = np.zeros((nx, ny))
    E[0] = (np.arange(ny) < j0) if lit_below else (np.arange(ny) >= j0)
    south = 1.0 if lit_below else 0.0
    for i in range(1, nx):
        E[i, 0] = (1 - t) * E[i - 1, 0] + t * south
        E[i, 1:] = (1 - t) * E[i - 1, 1:] + t * E[i - 1, :-1]
    return E


def panel_bins(fig, X0, Y0, S):
    th, D = bin_weights()
    fw, fh = fig.get_size_inches() * fig.dpi
    pa = fig.add_axes([X0 / fw, 1 - (Y0 + S) / fh, S / fw, S / fh], projection='polar')
    pa.bar(th, D / D.max(), width=2 * np.pi / NTH * 0.9, color=WATER, edgecolor=BLUE, linewidth=0.8, zorder=3)
    for d in range(0, 360, 45):
        pa.plot([np.radians(d)] * 2, [0, 1.12], color=MUTED if d % 90 else INK, lw=0.9,
                ls=(0, (3, 2)) if d % 90 else '-', zorder=2)
    pa.set_ylim(0, 1.18)
    pa.set_yticks([])
    pa.set_xticks(np.radians(np.arange(0, 360, 45)))
    pa.set_xticklabels([f'{d}°' for d in range(0, 360, 45)], fontsize=8.5)
    pa.grid(False)
    pa.spines['polar'].set_color(RULE)
    pa.annotate('', xy=(np.radians(TH0), 1.07), xytext=(0, 0),
                arrowprops=dict(arrowstyle='-|>', color=ORANGE, lw=1.6))
    pa.text(np.radians(TH0 + 6), 1.16, 'θ₀', color=ORANGE, fontsize=10, ha='center', va='center')
    pa.annotate('', xy=(np.radians(4), 0.97), xytext=(np.radians(44), 0.97),
                arrowprops=dict(arrowstyle='-|>', color=GREEN, lw=2.0, connectionstyle='arc3,rad=-0.3'))
    return pa


def panel_links(ax, t, X0, Y0, d):
    for i in range(3):
        for j in range(3):
            rect(ax, X0 + i * d, Y0 + j * d, d, d, '#eef4fb' if (i, j) in ((2, 1), (2, 0)) else 'white')
    grid(ax, X0, Y0, 3, 3, d)
    c = lambda i, j: np.array([X0 + (i + .5) * d, Y0 + (j + .5) * d])
    o = c(1, 1)
    for i in range(3):
        for j in range(3):
            if (i, j) != (1, 1):
                line(ax, [o, c(i, j)], '#c9c6bf', 1.0, z=3)
            dot(ax, c(i, j), MUTED)
    dot(ax, o, BLUE)
    th = np.radians(25.0)
    L = 1.32 * d
    v = L * np.array([np.cos(th), -np.sin(th)])                 # screen, y down
    a = L * (np.cos(th) - np.sin(th)) * np.array([1.0, 0.0])
    b = np.sqrt(2) * L * np.sin(th) * np.array([1.0, -1.0]) / np.sqrt(2)
    arrow(ax, [o, o + a], ORANGE, 2.6, size=13, z=8)
    arrow(ax, [o, o + b], GREEN, 2.6, size=13, z=8)
    line(ax, [o + a, o + v], GREEN, 1.1, ls=(0, (3, 2)), z=7)
    line(ax, [o + b, o + v], ORANGE, 1.1, ls=(0, (3, 2)), z=7)
    arrow(ax, [o, o + v], BLUE, 2.2, size=13, z=9)
    text(ax, *(o + v + [8, -6]), t['vel'], 10, color=BLUE, va='bottom')
    text(ax, *(o + a * 0.5 + [0, 10]), t['axis'], 9, color=ORANGE, ha='center')
    text(ax, *(o + b + [-8, -6]), t['diag'], 9, color=GREEN, ha='right', va='bottom')
    return 3 * d


def panel_sides(ax, t, X0, Y0, d):
    """SW corner: incident west side, lateral Neumann south side, interior 4 x 3 cells."""
    nx, ny = 4, 3
    for i in range(nx):
        for j in range(ny):
            rect(ax, X0 + i * d, Y0 + j * d, d, d, WATER, 'white', 1.0, zorder=2)
    grid(ax, X0, Y0, nx, ny, d)
    rect(ax, X0, Y0, nx * d, ny * d, 'none', INK, 1.5, zorder=6)
    dash = (0, (4, 3))
    for j in range(ny):                                         # incident virtual senders (west)
        rect(ax, X0 - d, Y0 + j * d, d, d, '#fde3d6', ORANGE, 1.0, ls=dash, zorder=2)
    for i in range(nx):                                         # Neumann virtual senders (south)
        rect(ax, X0 + i * d, Y0 + ny * d, d, d, '#e8f0fa', SKY, 1.0, ls=dash, zorder=2)
    rect(ax, X0 - d, Y0 + ny * d, d, d, '#fde3d6', ORANGE, 1.4, ls=dash, zorder=2)
    c = lambda i, j: np.array([X0 + (i + .5) * d, Y0 + (j + .5) * d])
    for j in range(ny):                                         # axis links from the west senders
        arrow(ax, [c(-1, j) + [8, 0], c(0, j) - [12, 0]], ORANGE, 1.5, size=10, z=8)
    for j in range(ny - 1):                                     # diagonal links from the west senders
        arrow(ax, [c(-1, j + 1) + [8, -8], c(0, j) + [-10, 10]], ORANGE, 1.2, size=9, z=8)
    arrow(ax, [c(-1, ny) + [8, -8], c(0, ny - 1) + [-10, 10]], ORANGE, 1.8, size=10, z=8)   # corner
    for i in range(nx - 1):                                     # diagonal links from the south senders
        arrow(ax, [c(i, ny) + [8, -8], c(i + 1, ny - 1) + [-10, 10]], SKY, 1.4, size=9, z=8)
    for i in range(nx):                                         # value copies (inside -> virtual sender)
        arrow(ax, [c(i, ny - 1) + [22, 12], c(i, ny) + [22, -10]], NAVY, 1.0, ls=(0, (2, 2)), size=8, z=7)
    text(ax, X0 - d - 16, Y0 + ny * d / 2, t['sideW'], 9, color=ORANGE, ha='right', va='center', rotation=90)
    text(ax, X0 + nx * d / 2, Y0 + (ny + 1) * d + 8, t['sideS'], 9, color=NAVY, ha='center')
    text(ax, X0 + nx * d / 2, Y0 + ny * d / 2, t['inside'], 9.5, color=INK, ha='center', va='center')
    return nx * d, ny * d


def build_scheme(lang):
    t = T[lang]
    fig, ax = canvas(1900)
    text(ax, 40, 22, t['sa'], 12.5, weight='bold')
    panel_bins(fig, 100, 118, 380)
    y = paragraph(ax, 40, 548, t['a1'], 520, 9, INK)
    y = paragraph(ax, 40, y, t['a2'], 520, 9, BLUE)
    yA = paragraph(ax, 40, y, t['a3'], 520, 9, GREEN)
    text(ax, 640, 22, t['sb'], 12.5, weight='bold')
    panel_links(ax, t, 700, 120, 125)
    y = paragraph(ax, 640, 520, t['b1'], 520, 9, INK)
    y = paragraph(ax, 640, y, t['b2'], 520, 9, INK)
    yB = paragraph(ax, 640, y, t['b3'], 520, 9, MUTED)
    text(ax, 1230, 22, t['sc'], 12.5, weight='bold')
    gw, gh = panel_sides(ax, t, 1350, 120, 78)
    y = 120 + gh + 78 + 44
    y = paragraph(ax, 1230, y, t['inc'], 540, 9, ORANGE, gap=4)
    y = paragraph(ax, 1230, y, t['neu'], 540, 9, NAVY, gap=4)
    y = paragraph(ax, 1230, y, t['corner'], 540, 9, ORANGE, gap=8)
    y = paragraph(ax, 1230, y, t['c2'], 540, 9, MUTED, gap=6)
    yC = paragraph(ax, 1230, y, t['c1'], 540, 9, MUTED)
    # shadow edges
    y0 = max(yA, yB, yC) + 30
    text(ax, 40, y0, t['sd'], 12.5, weight='bold')
    nx, ny, j0 = 100, 70, 26
    mw, mh = 330, 231
    for k, (th, key) in enumerate(((0.0, 'ang0'), (22.5, 'ang1'), (45.0, 'ang2'))):
        E = half_plane(th, nx, ny, j0, lit_below=True)
        px = 60 + k * (mw + 30)
        a = plot_axes(fig, px, y0 + 80, mw, mh)
        a.imshow(E.T, origin='lower', extent=(0, nx, 0, ny), cmap=CMAP, vmin=0, vmax=1, aspect='auto',
                 interpolation='nearest')
        xx = np.array([0, nx])
        a.plot(xx, j0 + xx * np.tan(np.radians(th)), color=INK, lw=0.9, ls=(0, (4, 3)))
        a.plot([0, 0], [j0, ny], color='#4a4946', lw=5, solid_capstyle='butt', clip_on=False)
        a.set(xlim=(0, nx), ylim=(0, ny), xticks=[], yticks=[])
        for sp in a.spines.values():
            sp.set_visible(True); sp.set_color(RULE)
        for yy in (8, 18):
            a.annotate('', xy=(10 * np.cos(np.radians(th)) + 1, yy + 10 * np.sin(np.radians(th))),
                       xytext=(1, yy), arrowprops=dict(arrowstyle='-|>', color=ORANGE, lw=1.4))
        text(ax, px, y0 + 50, t[key], 10, color=INK, weight='bold')
        if k == 0:
            text(ax, px + 8, y0 + 80 + mh * 0.18, t['bw'], 8.8, color=INK)
            text(ax, px + mw * 0.55, y0 + 80 + mh * (1 - (j0 + 3) / ny), t['geo'], 8.8, color=INK, va='bottom')
    # profiles across the edge, 100 cells downstream
    pa = plot_axes(fig, 1170 + 40, y0 + 80, 560, mh)
    styles = {0.0: (INK, '-'), 10.0: (GREEN, '--'), 22.5: (ORANGE, '-'), 30.0: (BLUE, '-.'), 45.0: (MUTED, ':')}
    for th, (col, ls) in styles.items():
        E = half_plane(th, 130, 120, 40, lit_below=False)
        i = int(round(100 * np.cos(np.radians(th))))
        j = np.arange(120) + 0.5
        dperp = (j - (40 + i * np.tan(np.radians(th)))) * np.cos(np.radians(th))
        if th in (0.0, 45.0):
            pa.step(dperp, E[i], where='mid', color=col, lw=1.6, ls=ls, label=f'{th:g}°')
        else:
            pa.plot(dperp, E[i], color=col, lw=1.6, ls=ls, label=f'{th:g}°')
    pa.set(xlim=(-18, 18), ylim=(-0.03, 1.05), xlabel=t['px'], ylabel=t['py'])
    pa.xaxis.label.set_size(9); pa.yaxis.label.set_size(9)
    pa.tick_params(labelsize=8.5)
    pa.grid(color=RULE, lw=0.5)
    pa.legend(fontsize=8.5, frameon=False, loc='upper left')
    yD = paragraph(ax, 60, y0 + 80 + mh + 72, t['d1'], 1700, 9, MUTED)
    ax.set_zorder(10)
    fit_height(fig, ax, yD + 16)
    return fig



# ----------------------------------------------------------------------------- current
HC, TC = 3.0, 2.5                       # depth (m) and period (s) of panels (a), (b), (d)


def sigma0(k, h):
    return np.sqrt(G * k * np.tanh(k * h))


def cg0(k, h):
    return group(sigma0(k, h), k, h)[2]


def k_current(om, U, h):
    """(om - k U)^2 = g k tanh(kh) on the branch continuous from U = 0; nan when blocked."""
    k = wavenumber(om, h)
    for _ in range(100):
        f = sigma0(k, h) + k * U - om
        df = cg0(k, h) + U
        if df <= 0:
            return np.nan
        kn = k - f / df
        if not np.isfinite(kn) or kn <= 0:
            return np.nan
        if abs(kn - k) < 1e-13 * kn:
            k = kn
            break
        k = kn
    return k if abs(sigma0(k, h) + k * U - om) < 1e-9 else np.nan


def blocking(om, h):
    """Tangent point: om = sigma0(k) - k c_g(k), U = -c_g(k) (bisection on the monotone function)."""
    f = lambda k: sigma0(k, h) - k * cg0(k, h) - om
    lo, hi = 1e-4, 1.0
    while f(hi) < 0:
        hi *= 2
    for _ in range(100):
        m = 0.5 * (lo + hi)
        lo, hi = (m, hi) if f(m) < 0 else (lo, m)
    kb = 0.5 * (lo + hi)
    return kb, -cg0(kb, h)


def river_panel(fig, X0, Y0, W, H):
    """Plan view of a river-mouth jet against waves travelling in +x (schematic).

    Depth HC everywhere; a plane jet U = -U0 sqrt(b0/b) exp(-(y/b)^2), b = b0 + 0.06 |x|.
    The phase is integrated along x for each y with the local wavenumber of the current
    (no ray bending), so the crests lag over the jet; waves stop where there is no root.
    """
    a = plot_axes(fig, X0, Y0, W, H)
    L, B, xc = 150.0, 60.0, 24.0
    a.set(xlim=(-L, xc), ylim=(-B, B), xticks=[], yticks=[])
    for sp in a.spines.values():
        sp.set_visible(True); sp.set_color(RULE)
    om = 2 * np.pi / TC
    b0, U0 = 6.0, 1.4
    bx = lambda x: b0 + 0.06 * (-x)
    U = lambda x, y: -U0 * np.sqrt(b0 / bx(x)) * np.exp(-(y / bx(x))**2)
    xs = np.linspace(-L, 0.0, 700)
    ys = np.linspace(-B, B, 241)
    PH = np.full((len(ys), len(xs)), np.nan)
    for jj, y in enumerate(ys):
        ph, kp = 0.0, None
        for ii, x in enumerate(xs):
            k = k_current(om, U(x, y), HC)
            if not np.isfinite(k):
                break
            if kp is not None:
                ph += 0.5 * (k + kp) * (xs[1] - xs[0])
            PH[jj, ii], kp = ph, k
    xx, yy = np.meshgrid(xs, ys)
    blocked = (~np.isfinite(PH)).astype(float)
    a.add_patch(Rectangle((-L, -B), L, 2 * B, fc='#eef4fb', ec='none', zorder=0))
    a.contourf(xx, yy, blocked, levels=[0.5, 1.5], colors=['#d9d6cf'], zorder=1)
    a.contour(xx, yy, blocked, levels=[0.5], colors=[ORANGE], linewidths=1.6, zorder=4)
    for n in range(1, int(np.nanmax(PH) / (2 * np.pi)) + 1):
        a.contour(xx, yy, PH, levels=[2 * np.pi * n], colors=[BLUE], linewidths=0.95, zorder=5)
    a.add_patch(Rectangle((0, -B), xc, 2 * B, fc=SOIL, ec='none', zorder=6))
    a.add_patch(Rectangle((-0.5, -b0), xc + 1, 2 * b0, fc=WATER, ec='none', zorder=7))
    for yy_ in (b0, -b0):
        a.plot([0, xc], [yy_, yy_], color=BED, lw=1.2, zorder=8)
    a.plot([0, 0], [b0, B], color=BED, lw=1.2, zorder=8)
    a.plot([0, 0], [-B, -b0], color=BED, lw=1.2, zorder=8)
    for x in (4, 20):
        a.annotate('', xy=(x - 10, 0), xytext=(x, 0), arrowprops=dict(arrowstyle='-|>', color=NAVY, lw=1.6),
                   zorder=9)
    for x in (-20, -55, -95, -135):
        a.annotate('', xy=(x - 13 * np.sqrt(b0 / bx(x)), 0), xytext=(x, 0),
                   arrowprops=dict(arrowstyle='-|>', color=NAVY, lw=1.6), zorder=9)
    for y in (-45, -22, 22, 45):
        a.annotate('', xy=(-130, y), xytext=(-148, y), arrowprops=dict(arrowstyle='-|>', color=ORANGE, lw=1.6),
                   zorder=9)
    return a, (-L, xc, -B, B)


def build_current(lang):
    t = T[lang]
    fig, ax = canvas(1600)
    om = 2 * np.pi / TC
    k0 = wavenumber(om, HC)
    kb, Ub = blocking(om, HC)
    # (a) graphical solution
    text(ax, 40, 22, t['ca'], 12.5, weight='bold')
    a = plot_axes(fig, 110, 80, 760, 390)
    ks = np.linspace(1e-3, 3.4, 600)
    a.plot(ks, sigma0(ks, HC), color=INK, lw=2.0, label=t['sig0'])
    for U, col, ls, key in ((0.0, MUTED, '-', 'l0'), (-0.5, ORANGE, '-', 'lopp'), (0.5, GREEN, '-', 'lfol'),
                            (Ub, NAVY, '--', 'lblk')):
        a.plot(ks, om - ks * U, color=col, lw=1.4, ls=ls, label=t[key].replace('−0.98', f'{Ub:.2f}'.replace('-', '−')))
        k = kb if U == Ub else k_current(om, U, HC)
        a.plot([k], [sigma0(k, HC)], 'o', color=col, ms=6, zorder=6)
        a.plot([k, k], [0, sigma0(k, HC)], color=col, lw=0.8, ls=':')
    a.set(xlim=(0, 3.4), ylim=(0, 6.0), xlabel=t['k'], ylabel=t['om'])
    a.xaxis.label.set_size(9); a.yaxis.label.set_size(9)
    a.tick_params(labelsize=8.5)
    a.grid(color=RULE, lw=0.5)
    a.legend(fontsize=8.5, frameon=False, loc='upper left')
    ko = k_current(om, -0.5, HC)
    a.annotate(t['a_opp'], xy=(ko, sigma0(ko, HC)), xytext=(1.25, 2.68), fontsize=8.5, color=ORANGE,
               arrowprops=dict(arrowstyle='-', color=ORANGE, lw=0.8))
    kf = k_current(om, 0.5, HC)
    a.annotate(t['a_fol'], xy=(kf, sigma0(kf, HC)), xytext=(0.15, 0.55), fontsize=8.5, color=GREEN,
               arrowprops=dict(arrowstyle='-', color=GREEN, lw=0.8))
    yA = paragraph(ax, 110, 545, t['a_blk'], 760, 9, NAVY)
    # (b) along the current
    text(ax, 940, 22, t['cb'], 12.5, weight='bold')
    b = plot_axes(fig, 1010, 80, 750, 390)
    Us = np.linspace(Ub * 0.9995, 1.0, 800)
    kk = np.array([k_current(om, U, HC) for U in Us])
    sg = om - kk * Us
    cg = cg0(kk, HC)
    HH = np.sqrt((sg / om) * cg0(k0, HC) / (cg + Us))
    b.plot(Us, kk / k0, color=BLUE, lw=1.8, label=t['kk0'])
    b.plot(Us, sg / om, color=GREEN, lw=1.5, ls='--', label=t['sigom'])
    b.plot(Us, HH, color=ORANGE, lw=1.8, label=t['HH0'])
    b.axvline(Ub, color=NAVY, lw=1.0, ls='--')
    b.axvline(0, color=RULE, lw=0.8)
    b.axhline(1, color=RULE, lw=0.8)
    b.text(Ub + 0.03, 0.12, t['blk'] + ' c_g + U = 0', fontsize=8.5, color=NAVY, va='bottom')
    b.set(xlim=(-1.05, 1.0), ylim=(0, 4.0), xlabel=t['U'])
    b.xaxis.label.set_size(9)
    b.tick_params(labelsize=8.5)
    b.grid(color=RULE, lw=0.5)
    b.legend(fontsize=8.5, frameon=False, loc='upper right')
    yB = paragraph(ax, 1010, 545, t['b_note'], 750, 9, MUTED)
    # (c) blocking speed against period and depth
    y0 = max(yA, yB) + 34
    text(ax, 40, y0, t['cc'], 12.5, weight='bold')
    c = plot_axes(fig, 110, y0 + 58, 760, 390)
    Ts = np.linspace(1.0, 14.0, 131)
    for h, col, ls in ((1.0, GREEN, ':'), (2.0, BLUE, '-.'), (5.0, ORANGE, '--'), (10.0, NAVY, '-')):
        ub = np.array([-blocking(2 * np.pi / T_, h)[1] for T_ in Ts])
        c.plot(Ts, ub, color=col, lw=1.7, ls=ls, label=t['hlab'].format(h=f'{h:g}'))
    c.plot(Ts, G * Ts / (8 * np.pi), color=MUTED, lw=1.0, label=t['deep'])
    c.plot([TC], [-Ub], 'o', color=INK, ms=5)
    c.annotate('(a)', xy=(TC, -Ub), xytext=(TC + 0.5, -Ub - 0.45), fontsize=8.5,
               arrowprops=dict(arrowstyle='-', color=INK, lw=0.7))
    c.set(xlim=(1, 14), ylim=(0, 5.0), xlabel=t['T'], ylabel=t['Ub'])
    c.xaxis.label.set_size(9); c.yaxis.label.set_size(9)
    c.tick_params(labelsize=8.5)
    c.grid(color=RULE, lw=0.5)
    c.legend(fontsize=8.5, frameon=False, loc='upper left')
    yC = paragraph(ax, 110, y0 + 58 + 390 + 64, t['c_note'], 760, 9, INK)
    # (d) river mouth
    text(ax, 940, y0, t['cd'], 12.5, weight='bold')
    X0, Y0, W, H = 1010, y0 + 58, 750, 390
    r, (x0_, x1_, y0_, y1_) = river_panel(fig, X0, Y0, W, H)
    M = lambda x, y: (X0 + (x - x0_) / (x1_ - x0_) * W, Y0 + (y1_ - y) / (y1_ - y0_) * H)
    tag = lambda x, y, s_, col: text(ax, *M(x, y), s_, 9, color=col, ha='center', va='center',
                                     bbox=dict(fc='white', ec='none', alpha=0.85, pad=1.5))
    tag(12, 30, t['river'], BED)
    tag(-75, -9, t['jet'], NAVY)
    tag(-30, 4.5, t['blk'], ORANGE)
    tag(-128, 54, t['wavesin'], ORANGE)
    yD = Y0 + H + 14
    for key, colr in (('blocked', ORANGE), ('dopp', BLUE), ('refr', BLUE)):
        yD = paragraph(ax, 1010, yD, t[key], 750, 9, colr, gap=4)
    yD = paragraph(ax, 1010, yD + 4, t['d_note'], 750, 8.8, MUTED)
    ax.set_zorder(10)
    fit_height(fig, ax, max(yC, yD) + 16)
    return fig

def draw(lang):
    with drawing_style():
        export(build_scheme(lang), 'wavefield_scheme', lang)
        return export(build_current(lang), 'wavefield_current', lang)
