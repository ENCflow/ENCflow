"""Configuration-file routing for the opening user guide (Japanese / English).

Rebuild from the repository root:
    python docs/figs/make_guide_figs.py config

Source contracts:
  src/list_sysparam.f90: defaults and replacement of '-' by fn_sysparam
  src/list_geoinfo.f90: required named-group read
  src/m_state.f90, src/m_swflow_enc.f90: empty paths keep base defaults
  src/m_geomorph.f90: empty path leaves the optional process disabled
  src/list_precip.f90, src/m_precip.f90: rainfall settings and time-series units

The left file is a minimal flat, dry setup. The right side illustrates
adding rainfall later; omitted optional entries are deliberately not drawn.
"""
from io import StringIO
from pathlib import Path

from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle

from _schematic import drawing_style, text, arrow, INK, MUTED, RULE

DPI, WIDTH, HEIGHT = 150, 1800, 1220
BLUE, ORANGE = '#2a78d6', '#cf5a27'
PALE_BLUE, PALE_ORANGE = '#eef4fc', '#fcf0e9'


def rect(ax, x, y, w, h, fill='white', edge=RULE, gid=None):
    patch = Rectangle((x, y), w, h, facecolor=fill, edgecolor=edge,
                      linewidth=1, gid=gid)
    ax.add_patch(patch)
    return patch


def build(lang):
    t = lambda ja, en: ja if lang == 'ja' else en
    fig = plt.figure(figsize=(WIDTH / DPI, HEIGHT / DPI), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set(xlim=(0, WIDTH), ylim=(HEIGHT, 0))
    ax.axis('off')
    text(ax, 55, 36, t('小さく始めて、必要な設定だけ追加する',
                      'Start small. Add settings as you need them.'),
         20, weight='bold')
    text(ax, 57, 98, t('機能の設定で必須なのは地理情報だけ。初期条件・計算法は既定値から始められる。',
                      'Only geographic input is required among feature settings. Start with the defaults for the rest.'),
         11.5, color=MUTED)

    text(ax, 60, 173, t('①  まずはこれだけ', '1   Start here'), 14, color=BLUE, weight='bold')
    text(ax, 1050, 173, t('②  降雨を加えたくなったら', '2   When you want to add rainfall'),
         14, color=ORANGE, weight='bold')

    # Complete minimal file: time settings plus a small uniform grid.
    rect(ax, 60, 235, 790, 727, gid='system-file')
    text(ax, 87, 258, 'param.txt', 16, weight='bold')
    rect(ax, 126, 325, 690, 257, '#f7f8fa', 'none', gid='system-group')
    for y, label in [(345,'&list_sysparam'), (394,'dt = 0.01'), (437,'tt = 8.0'),
                     (480,'fn_geoinfo = "-"'), (531,'/')]:
        text(ax, 153, y, label, 13 if y == 345 else 12.5,
             color=BLUE if y == 480 else INK, weight='bold' if y == 345 else 'normal')
    rect(ax, 126, 641, 690, 294, PALE_BLUE, 'none', gid='geoinfo-group')
    for y, label in [(661,'&list_geoinfo'), (710,'nx = 10,  ny = 10'),
                     (753,'dx = 10.0,  dy = 10.0'), (804,'/')]:
        text(ax, 153, y, label, 13 if y == 661 else 12.5,
             color=BLUE if y == 661 else INK, weight='bold' if y == 661 else 'normal')
    text(ax, 153, 888, t('"-" → 同じファイルの設定を使う',
                         '"-" → use settings in this same file'), 11, color=BLUE)
    arrow(ax, [(126, 495), (88, 495), (88, 795), (120, 795)], BLUE)
    text(ax, 60, 989, './encflow param.txt', 13, weight='bold')
    text(ax, 60, 1040, t('平坦な地形・乾いた状態で開始', 'Start with flat terrain and a dry surface'),
         11, color=MUTED)

    # A single added entry selects a rainfall file; no unused fn_* entries.
    rect(ax, 1050, 235, 690, 220, PALE_ORANGE, 'none', gid='added-entry')
    text(ax, 1075, 256, t('&list_sysparam に1行追加', 'Add one line to &list_sysparam'),
         12.5, color=ORANGE, weight='bold')
    text(ax, 1075, 326, 'fn_precip = "rain.txt"', 14, color=ORANGE)
    text(ax, 1075, 397, t('使いたい機能だけ書き足す', 'Add only the feature you want'), 11)
    arrow(ax, [(866, 345), (1029, 345)], ORANGE)
    arrow(ax, [(1395, 468), (1395, 554)], ORANGE)
    text(ax, 1423, 500, t('指定したファイルへ', 'Read the named file'), 10.5, color=MUTED)

    rect(ax, 1050, 569, 690, 344, gid='external-file')
    text(ax, 1075, 592, 'rain.txt', 16, weight='bold')
    rect(ax, 1075, 654, 640, 231, PALE_ORANGE, 'none', gid='precip-group')
    for y, label in [(672,'&list_precip'), (721,'prtype = 1'),
                     (764,'prval(:,1) = 0, 10'), (815,'/')]:
        text(ax, 1100, y, label, 13 if y == 672 else 12.5,
             color=ORANGE if y == 672 else INK, weight='bold' if y == 672 else 'normal')

    text(ax, 1050, 956, t('降雨の設定も param.txt にまとめるなら',
                         'To put the rainfall settings in param.txt too'), 11.5)
    text(ax, 1050, 1008, 'fn_precip = "-"', 13, color=BLUE, weight='bold')

    rect(ax, 60, 1100, 1680, 90, '#f1f4f7', 'none', gid='omission-note')
    text(ax, 87, 1126, t('使わない設定は省略。fn_XXX = "" を書き並べる必要はありません。',
                         'Leave unused settings out. You do not need to write fn_XXX = "" for each one.'),
         13, weight='bold')
    return fig


def export(fig, lang):
    stem = 'config_structure' + ('' if lang == 'ja' else '_en')
    dest = Path(__file__).resolve().parents[1] / stem
    fig.savefig(dest.with_suffix('.png'), dpi=DPI)
    svg = StringIO()
    fig.savefig(svg, format='svg', metadata={'Date': None})
    content = '\n'.join(s.rstrip() for s in svg.getvalue().splitlines()) + '\n'
    dest.with_suffix('.svg').write_text(content, encoding='utf-8', newline='\n')
    plt.close(fig)
    return str(dest.with_suffix('.png'))


def draw(lang):
    with drawing_style():
        return export(build(lang), lang)
