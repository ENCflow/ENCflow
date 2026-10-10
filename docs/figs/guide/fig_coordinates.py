"""coordinates_cells: 座標系 — 1 始まりのセル番号 (i, j)(j は北→南)、セル中心、ローカル/絶対座標から (i, j) への解決。"""
from _style import *

T = {"ja": {
    "ta": "(a) セル番号 (i, j): 1 スタート。i は西→東、j は北→南(ラスタの行順)",
    "tb": "(b) 実座標 (x, y) の解釈と、セルへの解決",
    "north": "北", "i": "i = 1 … nx(西→東)", "j": "j = 1 … ny\n(北→南)",
    "c11": "(1,1)", "cnx1": "(nx,1)", "c1ny": "(1,ny)", "cnxny": "(nx,ny)",
    "cell": "セル (i, j)", "center": "● セル中心(量の定義点。コロケート格子)",
    "gis": "GIS(QGIS 等)のラスタは行・列が 0 始まり\n→ 拾った番号は行・列とも +1 して指定する",
    "origin": "(0, 0)", "x": "x(東向き正)", "y": "y(北向き正)", "dx": "dx", "dy": "dy",
    "local": "地理参照なし: ローカル座標 (m)。領域南西端が (0, 0)",
    "abs": "地理参照あり: 絶対座標(投影座標系なら m、経緯度格子なら度)。\nQGIS で読んだ座標をそのまま書ける",
    "pt": "(x, y)", "res": "→ セル (4, 4)",
    "note": "計算はつねにローカルな m 格子の上(地理参照は計算に影響しない)。\n解決されたセル番号は初期化時に表示される\n(例 probe 1: absolute coordinates -> cell (150,150))",
    "edge": "セル境界ちょうどの座標は避け、セル内部を指す",
}, "en": {
    "ta": "(a) Cell numbers (i, j): 1-based; i west→east, j north→south",
    "tb": "(b) Real coordinates (x, y) and their resolution to a cell",
    "north": "N", "i": "i = 1 … nx (west→east)", "j": "j = 1 … ny\n(north→south)",
    "c11": "(1,1)", "cnx1": "(nx,1)", "c1ny": "(1,ny)", "cnxny": "(nx,ny)",
    "cell": "cell (i, j)", "center": "● cell centre (where quantities live; collocated grid)",
    "gis": "GIS rasters (QGIS etc.) count rows and columns from 0\n→ add +1 to both the row and the column",
    "origin": "(0, 0)", "x": "x (positive east)", "y": "y (positive north)", "dx": "dx", "dy": "dy",
    "local": "No georeferencing: local coordinates (m), origin at the SW corner",
    "abs": "Georeferenced: absolute coordinates (m for a projected grid, degrees for lat/lon).\nCoordinates read off in QGIS can be written as they are",
    "pt": "(x, y)", "res": "→ cell (4, 4)",
    "note": "The computation always runs on the local metre grid (georeferencing never affects it).\nThe resolved cell is printed at initialization\n(e.g. probe 1: absolute coordinates -> cell (150,150))",
    "edge": "Avoid coordinates exactly on a cell boundary; point inside a cell",
}}


def draw(lang):
    t = T[lang]
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 5.4))
    NX, NY = 7, 5
    YL = (-2.6, NY + 3.0)
    # ------------------------------------------------ (a) numbering
    ax = axs[0]; ax.set_aspect("equal"); ax.set_anchor("N"); ax.axis("off")
    grid(ax, 0, 0, NX, NY, 1, C_P, 0.8)
    for (i, j, key) in ((1, 1, "c11"), (NX, 1, "cnx1"), (1, NY, "c1ny"), (NX, NY, "cnxny")):
        label(ax, i - 0.5, NY - j + 0.5, t[key], color=C_P, fs=8.5)
    I, J = 5, 3
    ax.add_patch(Rectangle((I - 1, NY - J), 1, 1, fc=C_B, ec="none", alpha=0.8, zorder=2))
    ax.plot([I - 0.5], [NY - J + 0.5], "o", color=C_C, ms=6, zorder=5)
    label(ax, I - 0.5, NY - J + 0.5 + 0.28, t["cell"], color="#8a6b17", fs=9, va="bottom")
    label(ax, 0, -0.3, t["center"], color=C_C, fs=8.5, ha="left", va="top")
    # axes of numbering
    ax.annotate("", (3.0, NY + 0.35), (0, NY + 0.35), arrowprops=dict(arrowstyle="-|>", color=C_P, lw=1))
    label(ax, 0, NY + 0.5, t["i"], color=C_P, fs=9, ha="left", va="bottom")
    ax.annotate("", (-0.35, NY - 3.0), (-0.35, NY), arrowprops=dict(arrowstyle="-|>", color=C_P, lw=1))
    label(ax, -0.5, NY - 1.4, t["j"], color=C_P, fs=9, ha="right")
    label(ax, NX / 2 + 0.5, NY + 1.25, t["north"], color=C_P, fs=10, fontweight="bold")
    ax.annotate("", (NX / 2 + 0.5, NY + 1.15), (NX / 2 + 0.5, NY + 0.75), arrowprops=dict(arrowstyle="-|>", color=C_P, lw=1.2))
    label(ax, 0, -1.0, t["gis"], color=C_X, fs=8.5, ha="left", va="top")
    ax.set_xlim(-2.6, NX + 0.6); ax.set_ylim(*YL)
    ax.set_title(t["ta"], loc="left", fontsize=9.5)
    # ------------------------------------------------ (b) coordinates
    ax = axs[1]; ax.set_aspect("equal"); ax.set_anchor("N"); ax.axis("off")
    grid(ax, 0, 0, NX, NY, 1, C_P, 0.8)
    ax.add_patch(FancyArrowPatch((0, 0), (NX + 0.7, 0), arrowstyle="-|>", mutation_scale=12, color="k", lw=1.4, zorder=4))
    ax.add_patch(FancyArrowPatch((0, 0), (0, NY + 0.7), arrowstyle="-|>", mutation_scale=12, color="k", lw=1.4, zorder=4))
    ax.plot([0], [0], "o", color="k", ms=6, zorder=5)
    label(ax, -0.15, -0.15, t["origin"], fs=9, ha="right", va="top")
    label(ax, NX + 0.75, 0, t["x"], fs=9, ha="left")
    label(ax, 0.2, NY + 0.45, t["y"], fs=9, ha="left", va="bottom")
    # dx, dy
    ax.annotate("", (2, -0.3), (1, -0.3), arrowprops=dict(arrowstyle="<->", color=C_P, lw=0.9, shrinkA=0, shrinkB=0))
    label(ax, 1.5, -0.4, t["dx"], color=C_P, fs=8.5, va="top")
    ax.annotate("", (-0.3, 2), (-0.3, 1), arrowprops=dict(arrowstyle="<->", color=C_P, lw=0.9, shrinkA=0, shrinkB=0))
    label(ax, -0.4, 1.5, t["dy"], color=C_P, fs=8.5, ha="right")
    # a point (x, y) = (3.4 dx, 1.6 dy) -> cell (i, j) = (4, ny - 1) = (4, 4)
    px, py = 3.4, 1.6
    ax.add_patch(Rectangle((3, 1), 1, 1, fc=C_B, ec="none", alpha=0.8, zorder=2))
    ax.plot([px, px], [0, py], color=C_X, lw=0.9, ls="--", zorder=3)
    ax.plot([0, px], [py, py], color=C_X, lw=0.9, ls="--", zorder=3)
    ax.plot([px], [py], "o", color=C_X, ms=7, zorder=6)
    label(ax, px + 0.12, py + 0.12, t["pt"], color=C_X, fs=9.5, ha="left", va="bottom")
    label(ax, 3.5, 1.5 - 0.3, t["res"], color="#8a6b17", fs=9.5, va="top", box=True)
    # interpretation of (x, y)
    label(ax, -0.6, NY + 2.75, t["local"], color=C_P, fs=8.6, ha="left", va="top")
    label(ax, -0.6, NY + 2.3, t["abs"], color=C_P, fs=8.6, ha="left", va="top")
    label(ax, -0.6, -0.95, t["note"], fs=8.5, ha="left", va="top")
    label(ax, -0.6, -2.15, t["edge"], color=C_P, fs=8.5, ha="left", va="top")
    ax.set_xlim(-1.0, NX + 2.4); ax.set_ylim(*YL)
    ax.set_title(t["tb"], loc="left", fontsize=9.5)
    fig.tight_layout()
    return save(fig, "coordinates_cells", lang)
