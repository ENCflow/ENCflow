"""地理情報の章の図: 1 枚の格子に重ねるラスタ層(fn_* と固定値)の積み重ね。"""
from _style import *

T = {"ja": {
    "title": "地理情報(&list_geoinfo)= 同じ格子に重ねるラスタ層。必須は格子だけで、他は指定した層だけが有効",
    "grid": ("格子(必須)", "nx, ny と dx か lx(各方向)、epsg"),
    "z": ("地盤高 z", "f_ztype: 0 固定値 z0 / 1 ファイル fn_z(mag_z 倍率)"),
    "n": ("粗度(Manning の n)", "f_rntype: 0 固定値 rn0 / 1 ファイル fn_rn"),
    "mask": ("領域マスク", "f_masktype: 1 fn_mask(0 = 対象外: メモリ・計算なし)\n/ 2 海域マスクから自動生成"),
    "sw": ("海域マスク", "fn_sw(1 = 海域。潮位・高潮・津波の海)"),
    "rw": ("河道マスク", "fn_rw(1 = 河道セル)\n+ 掘り込み depth_rw / fn_depth_rw、粗度の上書き rn0_rw"),
    "gv": ("家屋群の抵抗", "fn_gv(空隙率)・fn_bb(平均寸法)"),
    "rs": ("ため池", "fn_rscap(限界貯留高。値のあるセルがため池)"),
    "sd": ("土層(地下水用)", "f_sdtype: sd0 / fn_sd(土層厚)、sy0(比湧水量)"),
    "wall": ("海岸堤防", "fn_seaside(海側)+ fn_seawall / seawall0(天端。陸側セル持ち)\nf_seawall_datum(基準)、f_seawall_mode(水理モード)"),
    "out": "対象外",
}, "en": {
    "title": "Geographic information (&list_geoinfo) = raster layers stacked on one grid. Only the grid is mandatory; a layer exists only if specified",
    "grid": ("Grid (mandatory)", "nx, ny and dx or lx (per direction), epsg"),
    "z": ("Ground elevation z", "f_ztype: 0 fixed z0 / 1 file fn_z (multiplier mag_z)"),
    "n": ("Roughness (Manning n)", "f_rntype: 0 fixed rn0 / 1 file fn_rn"),
    "mask": ("Domain mask", "f_masktype: 1 fn_mask (0 = excluded: no memory, no CPU)\n/ 2 derived from the sea mask"),
    "sw": ("Sea mask", "fn_sw (1 = sea; the sea for tide, storm surge, tsunami)"),
    "rw": ("Channel mask", "fn_rw (1 = channel cell)\n+ incision depth_rw / fn_depth_rw, roughness override rn0_rw"),
    "gv": ("Building drag", "fn_gv (void fraction), fn_bb (mean size)"),
    "rs": ("Ponds", "fn_rscap (storage limit depth; cells with a value are ponds)"),
    "sd": ("Soil layer (groundwater)", "f_sdtype: sd0 / fn_sd (soil depth), sy0 (specific yield)"),
    "wall": ("Seawall", "fn_seaside (sea side) + fn_seawall / seawall0 (crest, at land-side cells)\nf_seawall_datum (datum), f_seawall_mode (hydraulic mode)"),
    "out": "excluded",
}}

W, SK, HH, NX, NY = 3.6, 1.5, 1.4, 10, 10   # 層の幅・斜行量・奥行き・セル数
DY = 1.02                                   # 層の間隔


def xy(y0, i, j):
    return (i * W / NX + j * SK / NY, y0 + j * HH / NY)


def cell(ax, y0, i, j, fc, z, ni=1, nj=1, ec="none", lw=0.0, alpha=1.0):
    pts = [xy(y0, i, j), xy(y0, i + ni, j), xy(y0, i + ni, j + nj), xy(y0, i, j + nj)]
    ax.add_patch(Polygon(pts, closed=True, fc=fc, ec=ec, lw=lw, zorder=z, alpha=alpha))


def slab(ax, y0, z, fc="white"):
    pts = [(0, y0), (W, y0), (W + SK, y0 + HH), (SK, y0 + HH)]
    ax.add_patch(Polygon(pts, closed=True, fc=fc, ec=C_P, lw=0.9, zorder=z))


def gridlines(ax, y0, z, color=C_P, lw=0.3):
    for i in range(NX + 1):
        ax.plot([xy(y0, i, 0)[0], xy(y0, i, NY)[0]], [xy(y0, i, 0)[1], xy(y0, i, NY)[1]], color=color, lw=lw, zorder=z)
    for j in range(NY + 1):
        ax.plot([xy(y0, 0, j)[0], xy(y0, NX, j)[0]], [xy(y0, 0, j)[1], xy(y0, NX, j)[1]], color=color, lw=lw, zorder=z)


SEA = [(i, j) for i in range(NX) for j in range(NY) if i + 0.6 * j < 3.2]          # 左下の海
CH = [(0, 7), (1, 7), (2, 6), (3, 6), (4, 5), (5, 5), (6, 4), (7, 4), (8, 3), (9, 3)]  # 河道(海へ)
COAST = [(i, j) for i in range(NX) for j in range(NY) if (i, j) not in SEA and
         any((i + a, j + b) in SEA for a in (-1, 0, 1) for b in (-1, 0, 1))]


def draw(lang):
    t = T[lang]
    fig, ax = plt.subplots(figsize=(10.5, 7.9)); ax.axis("off")
    keys = ["grid", "z", "n", "mask", "sw", "rw", "gv", "rs", "sd", "wall"]
    for k, key in enumerate(keys):
        y0 = k * DY
        z = 10 * k
        slab(ax, y0, z)
        if key == "grid":
            gridlines(ax, y0, z + 1, C_P, 0.5)
        elif key == "z":
            for i in range(NX):
                for j in range(NY):
                    v = min(1.0, max(0.0, (i + (NY - j)) / (NX + NY - 2)))        # 右上(北東)ほど高い
                    c = tuple(a * (1 - v) + b * v for a, b in zip((0.894, 0.851, 0.784), (0.549, 0.482, 0.388)))
                    cell(ax, y0, i, j, c, z + 1)
            gridlines(ax, y0, z + 2, "white", 0.2)
        elif key == "n":
            cell(ax, y0, 0, 0, C_G, z + 1, NX, NY, alpha=0.5)
            for (i, j, ni, nj) in [(5, 6, 4, 3), (1, 2, 3, 3), (6, 1, 3, 3)]:
                cell(ax, y0, i, j, C_B, z + 2, ni, nj, alpha=0.9)
            gridlines(ax, y0, z + 3, "white", 0.2)
        elif key == "mask":
            cell(ax, y0, 0, 0, "#d9d8d3", z + 1, NX, NY)
            for (i, j) in [(i, j) for i in range(NX) for j in range(NY) if (i - 5.5) ** 2 / 20 + (j - 5) ** 2 / 14 < 1.0 or (i, j) in COAST]:
                cell(ax, y0, i, j, "white", z + 2)
            ax.text(*xy(y0, 9.3, 0.6), t["out"], fontsize=7.5, color=C_P, ha="right", va="bottom", zorder=z + 3)
        elif key == "sw":
            for (i, j) in SEA:
                cell(ax, y0, i, j, C_SEA, z + 1)
        elif key == "rw":
            for (i, j) in CH:
                cell(ax, y0, i, j, C_C, z + 1)
        elif key == "gv":
            for (i, j) in [(5, 7), (6, 7), (6, 8), (7, 8), (5, 8), (7, 7), (8, 6), (4, 7)]:
                cell(ax, y0, i, j, C_P, z + 1, alpha=0.7)
        elif key == "rs":
            for (i, j) in [(2, 2), (3, 2), (7, 1)]:
                cell(ax, y0, i, j, C_C, z + 1)
        elif key == "sd":
            cell(ax, y0, 0, 0, C_SOIL, z + 1, NX, NY, alpha=0.6)
        elif key == "wall":
            for (i, j) in SEA:
                cell(ax, y0, i, j, C_SEA, z + 1, alpha=0.35)
            for (i, j) in COAST:
                cell(ax, y0, i, j, C_X, z + 2)
        name, params = t[key]
        xl, yl = W + SK + 0.35, y0 + HH / 2
        ax.text(xl, yl + 0.3, name, fontsize=9.5, color="k", ha="left", va="center")
        ax.text(xl, yl + 0.05, params, fontsize=8.5, color=C_P, ha="left", va="top")
    ax.set_xlim(-0.2, W + SK + 0.4 + 7.4); ax.set_ylim(-0.3, (len(keys) - 1) * DY + HH + 0.3)
    ax.set_title(t["title"], loc="left", fontsize=10)
    fig.tight_layout()
    return save(fig, "geoinfo_layers", lang)
