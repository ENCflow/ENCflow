"""Setup patterns of volcanic mass flows and lahars (geomorph_applications.md §3, §4).

(a) equivalent fluid (f_dbed = 0 with Voellmy or a constant yield stress): no
    exchange with the bed, stop fixed into the terrain; optional entrainment
    (f_dbed = 4);
(b) concentration-varying mixture for lahars: bulking by erosion and pore water,
    then deposition and dilution into a flood; the concentration curve is a
    sketch of that sequence, not a computed result;
(c) the four ways to start the flow, and what is out of scope.
Schematic profiles following the text; not solver output.

Generate: python docs/figs/make_guide_figs.py geomorph_app_volcanic
"""
import numpy as np
from _geomorph import (canvas, header, panel, rule, box, poly, badge, chart, run, text, kblock as block, line, arrow,
                       INK, MUTED, RULE, SED, GREEN, BLUE, ORANGE, SOIL, ROCK, WATER, MOVING, TALUS, PANEL)

H = 880

T = {
 'ja': {
    'title': '火山流動とラハールの組み方  |  等価流体と濃度が変わる混合体、発生の与え方',
    'sub': '適用例 §3・§4 の設定の型。縦断と濃度の線は模式で、計算結果ではない。',
    'a': '(a) 等価流体: 岩屑なだれ・火砕流(§3)',
    'a_mass': '組成の変わらない流れ', 'a_stop': '止まった分は地形に固定\n(f_dbstop = 1)',
    'a_list': [
        'f_dbed = 0: 河床と交換しない(濃度 C は一定)',
        'f_dbres = 4(Voellmy)か 5(一定停止応力)',
        '走路の堆積物を取り込むなら f_dbed = 4(E = δe |V|。取り込める層 = sd。雪崩と同じ)',
    ],
    'b': '(b) 濃度が変わる混合体: ラハール(§4)',
    'cy': '濃度 C', 'bulk': '増水(bulking)\n侵食 + 間隙水', 'dilute': '堆積して希薄化\n→ 洪水へ',
    'src': '融雪・火口湖の決壊\n・降灰層の侵食',
    'b_list': [
        'f_debris = 1、E-D は f_dbed = 1(δd で堆積の速さを校正)か 2(江頭・芦田)',
        '細粒の灰スラリーは f_dbres = 4(μ 0.05〜0.1、ξ 500)か 1。2(江頭)は細粒で発散する',
        '岩塊主体(山体崩壊起源・石礫型)は f_dbed = 3 + f_dbres = 3(高橋・中川)',
        'f_dbwet = 1 で走路の間隙水を取り込む(浸透を計算するなら f_dbwet = 2)',
    ],
    'c': '(c) 発生の与え方',
    'routes': [
        ('崩壊深の分布 fn_dbinit', '瞬時流動化。山体崩壊起源の岩屑なだれ・ラハール'),
        ('濃度付きの区間流入 inflow_cs', '上流端に供給ハイドログラフ(噴火の供給率、融雪水)。融雪の量そのものは計算しない'),
        ('侵食起動', '降灰層を侵食できる層 sd で与え、降雨の表面流の侵食で濃度が上がる。浸透能の低下は地下水の浸透能で直接与える。シート流では dd を 0.2 mm 程度に'),
        ('連鎖', 'f_dbstop = 1 で固定した堆積 → 天然ダム → 越流・決壊 → 下流の堆積物の連行。降雨による二次泥流まで 1 つの計算でつながる'),
    ],
    'out': '対象外: 希薄系(火砕サージ・噴煙・降灰の大気輸送)と、高温の火砕物と氷雪の熱的な相互作用(融解量は流入で与える)',
    'foot': 'μ・ξ・d50 などの目安は章末の「パターン別の推奨値」。例題: examples/ashfall_lahar(降灰 → 降雨 → 泥流 → 扇状地、砂防堰堤との比較)。',
 },
 'en': {
    'title': 'Setting up volcanic mass flows and lahars  |  Equivalent fluid vs concentration-varying mixture, how to start',
    'sub': 'Setup patterns of §3 and §4 of the applications page. Profiles and the concentration line are sketches, not computed results.',
    'a': '(a) Equivalent fluid: debris avalanches, pyroclastic flows (§3)',
    'a_mass': 'flow of fixed composition', 'a_stop': 'stopped material is fixed\ninto the terrain (f_dbstop = 1)',
    'a_list': [
        'f_dbed = 0: no exchange with the bed (concentration C constant)',
        'f_dbres = 4 (Voellmy) or 5 (constant yield stress)',
        'to pick up path deposits, f_dbed = 4 (E = δe |V|; erodible layer = sd; as for avalanches)',
    ],
    'b': '(b) Concentration-varying mixture: lahars (§4)',
    'cy': 'C', 'bulk': 'bulking: erosion\n+ pore water', 'dilute': 'deposits and dilutes\n→ becomes a flood',
    'src': 'snowmelt, crater-lake\nbreach, ash erosion',
    'b_list': [
        'f_debris = 1; E-D f_dbed = 1 (calibrate the deposition speed with δd) or 2 (Egashira–Ashida)',
        'fine ash slurries: f_dbres = 4 (μ 0.05–0.1, ξ 500) or 1; law 2 (Egashira) diverges for fine grains',
        'boulder-rich flows (flank collapse, stony type): f_dbed = 3 + f_dbres = 3 (Takahashi–Nakagawa)',
        'f_dbwet = 1 takes up pore water along the path (f_dbwet = 2 when infiltration is computed)',
    ],
    'c': '(c) How to start the flow',
    'routes': [
        ('release depth map fn_dbinit', 'instant mobilization; debris avalanches and lahars from flank collapse'),
        ('inflow section with concentration inflow_cs', 'a supply hydrograph at the upstream end (eruption supply rate, meltwater); the amount of melt itself is not computed'),
        ('erosion start', 'give the ash layer as the erodible layer sd; rain-driven overland flow erodes it and the concentration rises. Give the reduced infiltration capacity directly in groundwater; for sheet flow set dd to about 0.2 mm'),
        ('chain', 'deposit fixed with f_dbstop = 1 → natural dam → overtopping and breach → entrainment of downstream deposits; rain-induced secondary lahars follow in the same run'),
    ],
    'out': 'Out of scope: dilute flows (pyroclastic surges, plumes, atmospheric transport of ash) and the thermal interaction of hot pyroclasts with snow and ice (give the melt as inflow)',
    'foot': 'Guide values of μ, ξ, d50 etc.: "Recommended values by pattern" at the end of the chapter. Example: examples/ashfall_lahar (ash fall → rain → lahar → fan, comparison with a check dam).',
 },
}


def profile(x, x0=55, x1=760, ytop=0.0, ybot=1.0, k=3.0):
    s = (np.asarray(x, float) - x0) / (x1 - x0)
    return ytop + (ybot - ytop) * (1 - np.exp(-k * s)) / (1 - np.exp(-k))


class Prof:
    """Concave slope profile between pixel x0..x1 and heights ytop..ybot."""
    def __init__(self, x0, x1, ytop, ybot):
        self.x0, self.x1, self.ytop, self.ybot = x0, x1, ytop, ybot

    def y(self, x):
        return profile(x, self.x0, self.x1, self.ytop, self.ybot)

    def ground(self, ax, base):
        xs = np.linspace(self.x0, self.x1, 200)
        ys = self.y(xs)
        poly(ax, list(zip(xs, ys)) + [(self.x1, base), (self.x0, base)], SOIL, z=2)
        line(ax, list(zip(xs, ys)), INK, 1.1, z=6)

    def layer(self, ax, xa, xb, thick, face, z=3, alpha=1.0):
        xs = np.linspace(xa, xb, 60)
        yb = self.y(xs)
        th = thick(np.linspace(0, 1, 60)) if callable(thick) else np.full(60, float(thick))
        poly(ax, list(zip(xs, yb)) + list(zip(xs[::-1], (yb - th)[::-1])), face, z=z, alpha=alpha)
        return xs, yb, th


def dots(ax, xs, yb, th, n, seed):
    rng = np.random.default_rng(seed)
    for _ in range(n):
        k = rng.integers(0, len(xs))
        if th[k] < 6:
            continue
        ax.scatter([xs[k] + rng.uniform(-3, 3)], [yb[k] - rng.uniform(2, th[k] - 2)], s=5, color=SED, zorder=8,
                   linewidths=0)


def bullets(ax, x, y, items, width, size=8.0):
    for s in items:
        a = block(ax, x + 14, y, s, width - 14, size=size)
        text(ax, x, y, '•', size=size)
        y += 23 * (a.get_text().count('\n') + 1) + 4
    return y


def panel_a(ax, t):
    panel(ax, 35, 108, t['a'])
    pr = Prof(50, 740, 175, 330)
    pr.ground(ax, 352)
    pr.layer(ax, 200, 350, lambda s: 26 * np.sin(np.pi * s) ** .7, MOVING, z=4)
    arrow(ax, [(300, float(pr.y(300)) - 40), (390, float(pr.y(390)) - 30)], INK, lw=1.4, size=10)
    text(ax, 280, float(pr.y(280)) - 64, t['a_mass'], size=7.8, ha='center')
    pr.layer(ax, 555, 730, lambda s: 16 * np.sin(np.pi * s) ** .5, TALUS, z=4)
    text(ax, 730, float(pr.y(640)) - 60, t['a_stop'], size=7.6, ha='right')
    bullets(ax, 50, 372, t['a_list'], 700)


def panel_b(fig, ax, t):
    x0 = 800
    panel(ax, x0, 108, t['b'])
    xa, xb, xdep, xfl = 815, 1530, 1190, 1360
    # Sketch of the concentration along the path (not computed).
    c = chart(fig, 860, 150, xb - 860, 56, (xa, xb), (0, 1.0), ylabel=t['cy'], size=7.6)
    xx = np.linspace(xa, xb, 300)
    peak = 0.15 + 0.7 * (1 - np.exp(-(xdep - xa) / 110))
    cc = np.where(xx < xdep, 0.15 + 0.7 * (1 - np.exp(-(xx - xa) / 110)), peak * np.exp(-(xx - xdep) / 90))
    c.plot(xx, cc, color=SED, lw=2.0)
    c.set_xticks([]); c.set_yticks([])
    c.axvspan(xdep, xfl, color=PANEL, lw=0)
    text(ax, (xa + xdep) / 2 + 95, 214, t['bulk'], size=7.6, color=SED, ha='center')
    text(ax, (xdep + xfl) / 2, 214, t['dilute'], size=7.6, color=INK, ha='center')
    pr = Prof(xa, xb, 262, 352)
    pr.ground(ax, 372)
    xs, yb, th = pr.layer(ax, xa + 25, xdep, lambda s: 6 + 20 * s, MOVING, z=4)
    dots(ax, xs, yb, th, 80, 4)
    pr.layer(ax, xdep, xfl, lambda s: 12 * np.sin(np.pi * (0.3 + 0.7 * s)), TALUS, z=4)
    pr.layer(ax, xdep, xfl, lambda s: 12 * np.sin(np.pi * (0.3 + 0.7 * s)) + 14 - 4 * s, MOVING, z=3, alpha=.55)
    pr.layer(ax, xfl, xb, 10, WATER, z=4)
    for xa_ in (960, 1080):
        ya = float(pr.y(xa_))
        arrow(ax, [(xa_, ya + 8), (xa_, ya - 18)], SED, lw=1.3, size=8)
    ya = float(pr.y(1020))
    arrow(ax, [(1020, ya + 8), (1030, ya - 16)], BLUE, lw=1.1, size=7)
    box(ax, xa + 2, 262 - 26, 24, 16, face=WATER, edge=BLUE, lw=.8, z=5)
    text(ax, xa + 32, 262 - 30, t['src'], size=7.2, color=BLUE)
    bullets(ax, x0 + 15, 386, t['b_list'], 725, size=7.9)


def panel_c(ax, t):
    y0 = 555
    panel(ax, 35, y0, t['c'])
    w = 372
    for k, (head, body) in enumerate(t['routes']):
        x = 35 + k * (w + 6)
        box(ax, x, y0 + 32, w, 192, face=PANEL, z=0)
        badge(ax, x + 18, y0 + 52, str(k + 1))
        a = block(ax, x + 40, y0 + 42, head, w - 52, size=8.4, color=SED, weight='bold')
        yb = y0 + 42 + 24 * (a.get_text().count('\n') + 1) + 10
        block(ax, x + 12, yb, body, w - 24, size=7.9)
    block(ax, 35, y0 + 236, t['out'], 1505, size=7.9, color=MUTED)


def build(lang):
    t = T[lang]
    fig, ax = canvas(H)
    header(ax, t['title'], t['sub'])
    panel_a(ax, t)
    line(ax, [(782, 105), (782, 535)], RULE, .8)
    panel_b(fig, ax, t)
    rule(ax, 35, 1540, 543)
    panel_c(ax, t)
    rule(ax, 35, 1540, 828)
    block(ax, 35, 836, t['foot'], 1505, size=7.6, color=MUTED)
    return fig


def draw(lang):
    return run(build, 'geomorph_app_volcanic', lang,
               'Schematic profiles of an equivalent-fluid volcanic mass flow and of a lahar whose concentration rises by '
               'bulking and falls by deposition, with the settings and the four ways to start the flow. Not solver output.')
