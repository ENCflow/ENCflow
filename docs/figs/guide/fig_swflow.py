"""ENC/STG storage locations; published adaptive-RK panel is preserved.

Panels (a)/(b) use shared grid geometry. Panel (c), including its title and
notes, is a lossless crop from commit 82f3a2734abecc60b2e0fd2c75fd632b8feb992d.
See m_swflow_enc.f90 / m_swflow_stg.f90 for actual stored quantities.
"""
from _style import *
from pathlib import Path as FilePath
from io import BytesIO, StringIO
import base64
import hashlib
import numpy as np
from PIL import Image
from _schematic import drawing_style, text, block, line, INK, MUTED, RULE

T = {'ja': {'a': '(a) ENC 格子',
        'b': '(b) STG 格子',
        'a_sub': '8近傍連結  |  f_gridsystem = 0（既定）',
        'b_sub': '4近傍連結  |  f_gridsystem = 1',
        'hint': '中央セルの接続と量の位置を強調',
        'cell': 'セル中心: h・z',
        'axis': '軸方向4エッジ: uv・mn',
        'diag': '対角4エッジ: uv・mn',
        'enc_note': 'uv: エッジ法線流速、mn: 単位幅流量。\nセル流速 u, v はエッジ流速から再構成。\np_diagratio で対角方向の通過幅を配分。',
        'stg_cell': 'セル中心: h・z（内部名 D・H）',
        'stg_x': '東西面: M（x 方向の単位幅流量）',
        'stg_y': '南北面: N（y 方向の単位幅流量）',
        'stg_note': 'セル流速 u, v は面流量と水深から算出。\n旧互換・比較用。再開は非対応。',
        'c': '(c) 適応的ルンゲクッタ(f_adaptive_runge = 1)\n ',
        'c_top': '各エッジで、陽解法で得た流量 mn(新) を\n前ステップの mn(前) と比べる',
        'c_lo': '急減・逆転',
        'c_hi': '急増',
        'c_in': '閾値内: 陽解法の値をそのまま採用',
        'c_out': '閾値外のエッジだけ 4 段 RK で再計算\n(他エッジは前ステップ値を参照)\n→ 画面の Runge 列 = 再計算したエッジの割合',
        'c_ratio': '横軸: 比 mn(新) / mn(前)',
        'c_thr': 'p_adprunge_thresh(既定 1.5。\n小さいほど高精度・高コスト、1.1〜)'},
 'en': {'a': '(a) ENC grid',
        'b': '(b) STG grid',
        'a_sub': '8 neighbours  |  f_gridsystem = 0 (default)',
        'b_sub': '4 neighbours  |  f_gridsystem = 1',
        'hint': 'Central-cell connections and quantity locations',
        'cell': 'Cell centres: h, z',
        'axis': '4 axis edges: uv, mn',
        'diag': '4 diagonal edges: uv, mn',
        'enc_note': 'uv: edge-normal velocity; mn: flux per unit width.\n'
                    'Cell u, v are reconstructed from edge velocities.\n'
                    'p_diagratio weights diagonal passage widths.',
        'stg_cell': 'Cell centres: h, z (internal D, H)',
        'stg_x': 'East/west faces: M (x flux per unit width)',
        'stg_y': 'North/south faces: N (y flux per unit width)',
        'stg_note': 'Cell u, v are derived from face fluxes and depth.\n'
                    'Legacy comparison; restart is unsupported.',
        'c': '(c) Adaptive Runge-Kutta (f_adaptive_runge = 1)\n ',
        'c_top': "each edge: compare the explicit flux mn(new)\nwith the previous step's mn(old)",
        'c_lo': 'drop /\nreversal',
        'c_hi': 'rise',
        'c_in': 'inside the band: keep the explicit value',
        'c_out': 'only edges outside the band are recomputed with\n'
                 '4-stage RK (other edges keep their old value)\n'
                 '-> Runge column on screen = share of recomputed edges',
        'c_ratio': 'axis: ratio mn(new) / mn(old)',
        'c_thr': 'p_adprunge_thresh (default 1.5;\nsmaller = more accurate, costlier; 1.1 and up)'}}

CANVAS = (1575, 645)
DPI = 150
RK_BOX = (1020, 0, 1575, 645)  # top-left pixel coordinates; identical in both languages
RK_SHA256 = {
    'ja': '20a95b6334a0ac49610d99fc4791df462bf5c64a7ebecccb29fb181c1903fadf',
    'en': '275cc1a0e07b9258f7e90ddf5a9c3934b3d317e2c0cac6e1a25044834900cd4b',
}
CENTRE = np.array([1.5, 1.5])
AXIS = np.array([(1, 0), (-1, 0), (0, 1), (0, -1)], float)
DIAGONAL = np.array([(1, 1), (-1, 1), (1, -1), (-1, -1)], float)
GRID_BOXES = [(106, 125, 264, 264), (611, 125, 264, 264)]


def _pixel_axes(fig, left, top, width, height, xlim=(0, 1), ylim=(0, 1)):
    ax = fig.add_axes([left/CANVAS[0], (CANVAS[1]-top-height)/CANVAS[1],
                       width/CANVAS[0], height/CANVAS[1]])
    ax.set(xlim=xlim, ylim=ylim)
    ax.axis('off')
    return ax


def _grid(ax):
    ax.set_aspect('equal')
    ax.add_patch(Rectangle((1, 1), 1, 1, fc='#eaf2fc', ec='none', zorder=0))
    for v in range(4):
        line(ax, [(v, 0), (v, 3)], RULE, .8, z=1)
        line(ax, [(0, v), (3, v)], RULE, .8, z=1)


def _centres(ax):
    for i in range(3):
        for j in range(3):
            ax.plot(i+.5, j+.5, 'o', color=MUTED, ms=4.1, zorder=5)
    ax.plot(*CENTRE, 'o', color=INK, ms=6.2, zorder=7)


def panel_enc(ax):
    _grid(ax)
    for vectors, ls, fill in [(AXIS, '-', C_C), (DIAGONAL, '--', 'white')]:
        for d in vectors:
            line(ax, [CENTRE, CENTRE+d], C_C, 1.3, ls=ls, z=3)
            ax.plot(*(CENTRE+.5*d), 's', ms=6.0, mfc=fill, mec=C_C, mew=1.1, zorder=6)
    _centres(ax)


def panel_stg(ax):
    _grid(ax)
    for d in AXIS:
        line(ax, [CENTRE, CENTRE+d], C_C, 1.3, z=3)
        horizontal = d[0] != 0
        ax.plot(*(CENTRE+.5*d), 's' if horizontal else 'D', ms=6.0,
                mfc=C_C if horizontal else 'white', mec=C_C, mew=1.1, zorder=6)
    _centres(ax)


def _legend(fig, left, top, label, marker, fill, color):
    ax = _pixel_axes(fig, left, top, 460, 31)
    ax.plot(.016, .5, marker, ms=5.4, mfc=fill, mec=color, mew=1., clip_on=False)
    text(ax, .065, .5, label, size=8.5, color=color, va='center')


def build(lang):
    """Draw only the new schematics; leave all RK pixels blank for exact pasting."""
    if lang not in T:
        raise ValueError('lang must be ja or en')
    t = T[lang]
    fig = plt.figure(figsize=(CANVAS[0]/DPI, CANVAS[1]/DPI), dpi=DPI)
    for left, title, sub in [(26, 'a', 'a_sub'), (531, 'b', 'b_sub')]:
        heading = _pixel_axes(fig, left, 21, 460, 82)
        text(heading, 0, 1, t[title], size=10.6, weight='bold')
        text(heading, 0, .58, t[sub], size=8.6, color=MUTED)
        text(heading, 0, .13, t['hint'], size=8.0, color=MUTED)
    for box, draw_panel in zip(GRID_BOXES, (panel_enc, panel_stg)):
        ax = _pixel_axes(fig, *box, xlim=(0, 3), ylim=(0, 3))
        draw_panel(ax)
    for left, entries in [
            (26, [('cell', 'o', INK, INK), ('axis', 's', C_C, C_C),
                  ('diag', 's', 'white', C_C)]),
            (531, [('stg_cell', 'o', INK, INK), ('stg_x', 's', C_C, C_C),
                   ('stg_y', 'D', 'white', C_C)])]:
        for row, (key, marker, fill, color) in enumerate(entries):
            _legend(fig, left, 410+row*32, t[key], marker, fill, color)
    for left, key in [(26, 'enc_note'), (531, 'stg_note')]:
        note = _pixel_axes(fig, left, 525, 460, 101)
        line(note, [(0, 1.08), (1, 1.08)], RULE, .8, clip_on=False)
        block(note, 0, 1, t[key], 1, size=8.2)
    return fig


def _rk_asset(lang):
    suffix = '' if lang == 'ja' else '_en'
    path = FilePath(FIGS)/f'swflow_rk_preserved{suffix}.png'
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != RK_SHA256[lang]:
        raise ValueError('Protected RK panel differs from published crop: '+str(path))
    return data


def draw(lang):
    if lang not in T:
        raise ValueError('lang must be ja or en')
    rk_bytes = _rk_asset(lang)
    with Image.open(BytesIO(rk_bytes)) as rk:
        rk.load()
        if rk.size != (RK_BOX[2]-RK_BOX[0], RK_BOX[3]-RK_BOX[1]):
            raise ValueError('Protected RK panel has an unexpected size')
        with drawing_style():
            fig = build(lang)
            try:
                png = FilePath(out_path('swflow_enc', lang))
                png_buffer, svg_buffer = BytesIO(), StringIO()
                fig.savefig(png_buffer, format='png', dpi=DPI)
                fig.savefig(svg_buffer, format='svg', metadata={'Date': None,
                    'Description': 'ENC/STG schematics; adaptive RK is the unchanged published raster.'})
            finally:
                plt.close(fig)
        with Image.open(BytesIO(png_buffer.getvalue())) as rendered:
            combined = rendered.convert('RGBA')
        if combined.size != CANVAS:
            raise ValueError('Schematic canvas has an unexpected size')
        # Exact paste, with no resampling or alpha compositing.
        combined.paste(rk, RK_BOX[:2])
        combined.save(png, dpi=(DPI, DPI))
    scale = 72/DPI
    x0, y0, x1, y1 = RK_BOX
    embedded = (f'<image id="preserved-adaptive-rk" x="{x0*scale:g}" y="{y0*scale:g}" '
                f'width="{(x1-x0)*scale:g}" height="{(y1-y0)*scale:g}" '
                f'preserveAspectRatio="none" xlink:href="data:image/png;base64,'
                +base64.b64encode(rk_bytes).decode('ascii')+'"/>\n')
    svg = svg_buffer.getvalue().replace('</svg>', embedded+'</svg>')
    # Path-data line-end spaces are immaterial; keep generated SVG diffs clean.
    svg = '\n'.join(s.rstrip() for s in svg.splitlines())+'\n'
    png.with_suffix('.svg').write_text(svg, encoding='utf-8', newline='\n')
    return str(png)


# Historical drawing function retained verbatim for provenance only. The
# supported draw() path never calls it: the published pixels are the authority.
def panel_rk(ax, t):
    ax.axis("off")
    # 比の帯: 対数目盛風に 1/thr, 1, thr を等間隔に置く
    x_lo, x1, x_hi = 2.2, 4.2, 6.2
    y0, hh = 2.0, 0.6
    ax.add_patch(Rectangle((0.2, y0), x_lo - 0.2, hh, fc=C_X, ec="none", alpha=0.8, zorder=1))
    ax.add_patch(Rectangle((x_lo, y0), x_hi - x_lo, hh, fc=C_G, ec="none", alpha=0.8, zorder=1))
    ax.add_patch(Rectangle((x_hi, y0), 8.0 - x_hi, hh, fc=C_X, ec="none", alpha=0.8, zorder=1))
    for x, s in [(x_lo, "1/thr"), (x1, "1"), (x_hi, "thr")]:
        ax.plot([x, x], [y0 - 0.1, y0 + hh + 0.1], color="k", lw=1.0, zorder=3)
        ax.text(x, y0 - 0.18, s, ha="center", va="top", fontsize=9, color="k")
    ax.text(x1, y0 + hh + 0.18, t["c_in"], ha="center", va="bottom", fontsize=8.5, color="#3f7a2a", zorder=4)
    ax.text((0.2 + x_lo) / 2, y0 + hh / 2, t["c_lo"], ha="center", va="center", fontsize=8, color="white", zorder=4)
    ax.text((x_hi + 8.0) / 2, y0 + hh / 2, t["c_hi"], ha="center", va="center", fontsize=8, color="white", zorder=4)
    ax.annotate("", (8.35, y0 + hh / 2), (8.05, y0 + hh / 2), arrowprops=dict(arrowstyle="-|>", color="k", lw=1))
    ax.text(x1, y0 - 0.55, t["c_ratio"], ha="center", va="top", fontsize=8.5, color="k")
    ax.text(0.2, y0 + hh + 1.0, t["c_top"], ha="left", va="center", fontsize=8.5, color="k")
    ax.text(0.2, y0 - 1.15, "thr = " + t["c_thr"], ha="left", va="center", fontsize=8.5, color=C_P)
    ax.text(0.2, y0 - 2.05, t["c_out"], ha="left", va="center", fontsize=8.5, color="#b0481f")
    ax.set_xlim(0, 8.6); ax.set_ylim(-0.6, 3.9)
    ax.set_title(t["c"], loc="left", fontsize=10)
