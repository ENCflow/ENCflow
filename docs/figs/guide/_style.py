"""ユーザーガイドの説明図の共通様式(docs/figs/guide/fig_*.py から使う)。

  各モジュールは draw(lang) を持ち、lang = "ja" | "en" で docs/figs/<name>.png(ja)と
  docs/figs/<name>_en.png(en)を書く。データ不要の模式図。matplotlib のみ(方針 10:
  計算本体の外)。文字は T[lang][key] の辞書で日英を切り替える。
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch, Polygon, Circle, FancyBboxPatch  # noqa: F401 (各図で使う)

plt.rcParams.update({"font.family": ["IPAGothic", "DejaVu Sans"], "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})

# 配色(nest の図と同じ): 灰 = 地盤・親・補助、青 = 水・主対象、黄 = 帯・層・強調領域、橙 = 強制・注目、緑 = 戻り・結果
C_P, C_C, C_B, C_X, C_G = "#6b6a66", "#2a78d6", "#f2b84b", "#eb6834", "#8fbf6a"
C_WATER, C_WATER_L, C_GROUND, C_GROUND_L = "#2a78d6", "#cfe0f6", "#8c7b63", "#e4d9c8"
C_SOIL, C_ROCK, C_SEA, C_ICE, C_LAVA = "#c9a86a", "#9c9a94", "#5aa0d8", "#d8ecf7", "#d64a2a"
FIGS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # docs/figs

def out_path(name, lang):
    return os.path.join(FIGS, name + ("" if lang == "ja" else "_en") + ".png")

def arrow(ax, p, q, color=C_X, text=None, lw=1.6, dxy=(0, 0), ha="center", va="center", fs=9, ls="-", z=6):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=12, color=color, lw=lw, ls=ls, zorder=z))
    if text:
        ax.text((p[0] + q[0]) / 2 + dxy[0], (p[1] + q[1]) / 2 + dxy[1], text, color=color, ha=ha, va=va, fontsize=fs, zorder=z + 1)

def grid(ax, x0, y0, nx, ny, d, color=C_P, lw=0.7, z=1):
    for i in range(nx + 1):
        ax.plot([x0 + i * d, x0 + i * d], [y0, y0 + ny * d], color=color, lw=lw, zorder=z)
    for j in range(ny + 1):
        ax.plot([x0, x0 + nx * d], [y0 + j * d, y0 + j * d], color=color, lw=lw, zorder=z)

def label(ax, x, y, s, color="k", fs=9, ha="center", va="center", box=False, z=7, **kw):
    bb = dict(fc="white", ec="none", alpha=0.85, pad=1.5) if box else None
    ax.text(x, y, s, color=color, fontsize=fs, ha=ha, va=va, zorder=z, bbox=bb, **kw)

def save(fig, name, lang, dpi=150):
    fig.savefig(out_path(name, lang), dpi=dpi)
    plt.close(fig)
    return out_path(name, lang)
