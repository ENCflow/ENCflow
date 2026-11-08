"""Hillslope erosion by wet detachment (geomorph.md, f_wash; sediment.md §5).

(a) where f_wash acts compared with f_splash and the channel cells;
(b) detachment rate E = k_r P + k_f max(tau*/tau*c - 1, 0) versus tau* for three
    rainfall intensities with the default coefficients (src/m_geomorph_wash.f90);
(c) the lateral spreading of the detachment depth by wet_lw: a Gaussian kernel
    of standard deviation l_w moves the bed change to neighbouring cells while
    keeping the total (hs stays in the source cell).
Schematic and closed-form curves for illustrative values; not solver output.

Generate: python docs/figs/make_guide_figs.py geomorph_wash
"""
import numpy as np
from _geomorph import (canvas, header, panel, rule, box, poly, chart, run, text, kblock as block, line, arrow,
                       INK, MUTED, RULE, SED, GREEN, BLUE, ORANGE, SOIL, ROCK, WATER, MOVING, PANEL)

H = 700
KR, KF, TSC = 0.01, 1.0e-5, 0.05          # wash_kr, wash_kf (m/s), wash_tausc
LW = 1.5                                  # wet_lw in cells for (c)

T = {
 'ja': {
    'title': '斜面浸食(f_wash)  |  働く場所、剥離の速さ、剥離深の横方向の広げ方',
    'sub': '(a) は説明図、(b) は src/m_geomorph_wash.f90 の式を既定の係数で評価した曲線、(c) は核の形の説明。計算結果ではない。',
    'a': '(a) 働く場所', 'a2': '湿潤・乾燥と河道で受け持ちが分かれる',
    'dry': '乾燥(h ≤ dd)\nf_splash: 剥離分は系外へ',
    'wet': '湿潤(h > dd)で河道外(rw = 0)\nf_wash: 剥離分を hs へ\n(f_suspend が運ぶ)',
    'chan': '河道セル(rw > 0)\n対象外(掃流砂・浮遊砂)',
    'rain': '地表到達降雨 P',
    'a_note': '剥離分は z と sd から同じだけ差し引く(sd = 0 で止まる)。非河道セルでは浮遊砂の巻き上げと面状侵食の項が'
              '重なるので、両方を使うときは係数の校正で管理する。',
    'b': '(b) 剥離の速さ E(固体の体積)', 'b2': 'E = k_r P + k_f max(τ*/τ*c − 1, 0)',
    'bx': '無次元掃流力 τ*(浮遊砂の粒径で評価)', 'by': 'E (mm/h)',
    'p': 'P = {:g} mm/h', 'tc': 'τ*c = 0.05',
    'rainonly': '← 閾値までは雨滴の項だけ\n   (k_r P。流れがなくても働く)',
    'b_note': '既定 k_r = 0.01、k_f = 1e-5 m/s(経験値で校正が前提)。河床の低下は E × morfac / (1 − λ)。閾値を超えると'
              '面状侵食の項がすぐに雨滴の項を上回る。',
    'c': '(c) 剥離深の横方向拡散(wet_lw)', 'c2': 'ℓ_w = 1.5 Δx の例。総量は同じ',
    'cx': 'セル(Δx 単位)', 'cy': '河床の低下(相対)',
    'before': 'wet_lw = 0: 流れが集まった 1 セルだけ', 'after': 'wet_lw = ℓ_w: 標準偏差 ℓ_w のガウス核で配る',
    'c_note': '1 セルを削る正帰還には長さのスケールがなく、ガリーの幅と間隔が格子幅で決まる。ℓ_w(リルの幅の目安)を'
              '与えると Δx ≤ ℓ_w/2 で谷の間隔が格子に依らない。浮遊砂 hs は源セルに入る。受け側の sd が足りない分は'
              '岩盤露出として捨て、終了時に報告する。',
    'foot': '値は説明用。f_wash は f_suspend が必須。wet_lw は f_suspend の巻き上げにも効く(沈降は対象外)。',
 },
 'en': {
    'title': 'Hillslope erosion (f_wash)  |  Where it acts, detachment rate, lateral spreading of the detachment depth',
    'sub': '(a) explanatory sketch; (b) curves of src/m_geomorph_wash.f90 with the default coefficients; (c) shape of the kernel. Not computed results.',
    'a': '(a) Where it acts', 'a2': 'wet, dry and channel cells are handled separately',
    'dry': 'dry (h ≤ dd)\nf_splash: detached\nsediment leaves',
    'wet': 'wet (h > dd), rw = 0\nf_wash: detached → hs\n(carried by f_suspend)',
    'chan': 'channel cells (rw > 0)\nnot treated (bedload, suspension)',
    'rain': 'rain reaching the ground P',
    'a_note': 'The detached amount is subtracted equally from z and sd (stops at sd = 0). Outside channels the entrainment of '
              'suspended sediment and the sheet-erosion term overlap, so manage them by calibrating the coefficients when '
              'both are used.',
    'b': '(b) Detachment rate E (solid volume)', 'b2': 'E = k_r P + k_f max(τ*/τ*c − 1, 0)',
    'bx': 'Shields number τ* (with the suspended grain size)', 'by': 'E (mm/h)',
    'p': 'P = {:g} mm/h', 'tc': 'τ*c = 0.05',
    'rainonly': '← below the threshold only the rain\n   term (k_r P; acts without flow)',
    'b_note': 'Defaults k_r = 0.01, k_f = 1e-5 m/s (empirical; calibration assumed). The bed lowers at E × morfac / (1 − λ). '
              'Above the threshold the sheet-erosion term soon exceeds the rain term.',
    'c': '(c) Lateral spreading by wet_lw', 'c2': 'example ℓ_w = 1.5 Δx; same total',
    'cx': 'cell (in Δx)', 'cy': 'bed lowering (relative)',
    'before': 'wet_lw = 0: only the cell where flow concentrates', 'after': 'wet_lw = ℓ_w: Gaussian of std. dev. ℓ_w',
    'c_note': 'Eroding one cell is a positive feedback without a length scale, so gully width and spacing follow the grid. '
              'With ℓ_w (about the rill width) the valley spacing is grid-independent for Δx ≤ ℓ_w/2. hs enters the source '
              'cell; what the receiving sd cannot supply is discarded as bedrock exposure and reported.',
    'foot': 'Values are illustrative. f_wash requires f_suspend. wet_lw also acts on the entrainment of f_suspend (not on settling).',
 },
}


def panel_a(ax, t):
    panel(ax, 35, 108, t['a'])
    text(ax, 35, 136, t['a2'], size=8, color=MUTED)
    xs = np.linspace(50, 510, 200)
    yg = 190 + 190 * ((xs - 50) / 460) ** 1.15
    ch = (xs > 440) & (xs < 480)
    yg[ch] += 22 * np.sin(np.pi * (xs[ch] - 440) / 40)
    poly(ax, list(zip(xs, yg)) + [(510, 420), (50, 420)], SOIL, z=2)
    # Sheet flow on the lower slope, deeper water in the channel.
    mw = (xs > 230) & (xs <= 440)
    th = 3.5 + 6 * (xs[mw] - 230) / 210
    poly(ax, list(zip(xs[mw], yg[mw])) + list(zip(xs[mw][::-1], (yg[mw] - th)[::-1])), WATER, edge=BLUE, lw=.6, z=4)
    lvl = float(np.interp(440, xs, yg)) - 7
    mc = ch
    poly(ax, list(zip(xs[mc], np.minimum(yg[mc], 1e9))) + [(480, lvl), (440, lvl)], WATER, z=4)
    line(ax, [(440, lvl), (480, lvl)], BLUE, 1.0, z=5)
    line(ax, list(zip(xs, yg)), INK, 1.1, z=6)
    for x in np.arange(280, 500, 30):
        y0 = 172 + 9 * ((x * 7) % 3)
        line(ax, [(x, y0), (x - 5, y0 + 13)], BLUE, .9, z=5)
    text(ax, 55, 164, t['rain'], size=7.6, color=BLUE)
    for x in (300, 360, 410):
        y = float(np.interp(x, xs, yg))
        arrow(ax, [(x, y + 2), (x + 8, y - 14)], SED, lw=1.1, size=7)
    text(ax, 60, 258, t['dry'], size=7.6)
    text(ax, 180, 360, t['wet'], size=7.6, color=INK)
    text(ax, 505, 432, t['chan'], size=7.6, ha='right', color=MUTED)
    block(ax, 35, 515, t['a_note'], 470, size=7.9)


def panel_b(fig, ax, t):
    x0 = 545
    panel(ax, x0, 108, t['b'])
    text(ax, x0, 136, t['b2'], size=8, color=MUTED)
    c = chart(fig, x0 + 70, 172, 400, 260, (0, 0.3), (0.01, 1000), xlabel=t['bx'], ylabel=t['by'])
    c.set_yscale('log')
    ts = np.linspace(0, 0.3, 600)
    sheet = KF * np.maximum(ts / TSC - 1.0, 0.0) * 3.6e6          # mm/h
    for pp, col in ((10, GREEN), (50, BLUE)):
        c.plot(ts, KR * pp + sheet, color=col, lw=2.0, label=t['p'].format(pp))
    c.plot(ts, np.where(sheet > 0, sheet, np.nan), color=SED, lw=1.6, ls='--', label=t['p'].format(0))
    c.axvline(TSC, color=MUTED, lw=.8, ls=':')
    c.text(TSC + 0.004, 600, t['tc'], fontsize=7.4, color=MUTED, va='top')
    c.text(0.058, 0.03, t['rainonly'], fontsize=7.4, color=MUTED, va='center')
    c.legend(loc='center right', fontsize=7.6, frameon=False)
    block(ax, x0, 515, t['b_note'], 480, size=7.9)


def panel_c(fig, ax, t):
    x0 = 1055
    panel(ax, x0, 108, t['c'])
    text(ax, x0, 136, t['c2'], size=8, color=MUTED)
    c = chart(fig, x0 + 70, 172, 400, 220, (-6.5, 6.5), (0, 1.05), xlabel=t['cx'], ylabel=t['cy'])
    k = np.arange(-6, 7)
    w = np.exp(-0.5 * (k / LW) ** 2)
    w /= w.sum()
    c.bar(k, np.where(k == 0, 1.0, 0.0), width=0.8, color=PANEL, edgecolor=MUTED, lw=.8, label=t['before'])
    c.bar(k, w / w.max() * 0 + w, width=0.5, color=SED, label=t['after'])
    c.set_xticks(range(-6, 7, 2))
    c.legend(loc='upper left', bbox_to_anchor=(-0.17, -0.22), fontsize=7.6, frameon=False, labelspacing=0.35)
    block(ax, x0, 515, t['c_note'], 480, size=7.9)


def build(lang):
    t = T[lang]
    fig, ax = canvas(H)
    header(ax, t['title'], t['sub'])
    panel_a(ax, t)
    line(ax, [(527, 105), (527, 640)], RULE, .8)
    panel_b(fig, ax, t)
    line(ax, [(1037, 105), (1037, 640)], RULE, .8)
    panel_c(fig, ax, t)
    rule(ax, 35, 1540, 648)
    block(ax, 35, 658, t['foot'], 1505, size=7.8, color=MUTED)
    return fig


def draw(lang):
    return run(build, 'geomorph_wash', lang,
               'Where wet hillslope erosion acts compared with dry erosion and channel cells, curves of the detachment rate '
               'versus the Shields number for three rainfall intensities, and the Gaussian spreading of the detachment '
               'depth by wet_lw. Not solver output.')
