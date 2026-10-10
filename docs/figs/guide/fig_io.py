"""io_files: 入出力 — ラスタの並び(先頭行 = 北端)と、出力ファイルの体系(接頭辞 + 4 桁番号、プローブ・測線・ログ)。"""
from _style import *

T = {"ja": {
    "ta": "(a) ラスタの共通規約: 先頭行が北端(行 = 北→南、列 = 西→東)",
    "tb": "(b) 出力ファイルの体系(dir_result、既定 result/)",
    "fname": "H0001.txt(行列テキスト)",
    "row1": "1 行目 = 北端の行(j = 1)", "rown": "最終行 = 南端の行(j = ny)", "col": "列 = 西→東(i = 1 … nx)",
    "north": "北", "map": "地図(GIS)と同じ向き",
    "same": "txt / bil(+.hdr) / GeoTIFF は同じ並び・同じ値\n(形式はコンテナの違いだけ)",
    "tl": "時間軸", "n0000": "0000\n開始状態\n(再開ランでは\n復元状態)", "nk": "dt_file ごとの連番 0001, 0002, …\n(時刻との対応表 FILENUMBER.csv)",
    "n9998": "9998\n最終ステップ", "n9999": "9999\n期間統計\n(最大値など)",
    "tree": ("result/\n"
             " ├ H0000  H0001 … H9998  H9999   接頭辞 = 量(H: 水深。f_out_* で選択)\n"
             " │   拡張子 .txt / .bil(+.hdr) / .tif(f_output_mode のビット和)\n"
             " ├ Z0000(地盤高の初期値)、X0000(領域マスク)   常に出力\n"
             " ├ FILENUMBER.csv   番号 ↔ 時刻\n"
             " ├ Log.txt(画面表示と同一)、パラメータファイルの控え\n"
             " ├ probes/probe0001.csv …   プローブ(fn_record。dt_recrd ごと)\n"
             " ├ fluxes/flux0001.csv …    フラックス測線\n"
             " └ summary.csv              計測の集計"),
}, "en": {
    "ta": "(a) Raster order: first row = north (rows N→S, columns W→E)",
    "tb": "(b) Output file scheme (dir_result, default result/)",
    "fname": "H0001.txt (matrix text)",
    "row1": "line 1 = northernmost row (j = 1)", "rown": "last line = southernmost row (j = ny)", "col": "columns = west→east (i = 1 … nx)",
    "north": "N", "map": "same orientation as a map (GIS)",
    "same": "txt / bil (+.hdr) / GeoTIFF hold the same order and values\n(the format is only a difference of container)",
    "tl": "time axis", "n0000": "0000\nstate at start\n(restored state\nin a restart run)", "nk": "every dt_file: 0001, 0002, …\n(number ↔ time: FILENUMBER.csv)",
    "n9998": "9998\nfinal step", "n9999": "9999\nrun statistics\n(maxima etc.)",
    "tree": ("result/\n"
             " ├ H0000  H0001 … H9998  H9999   prefix = quantity (H: depth; f_out_* flags)\n"
             " │   extension .txt / .bil (+.hdr) / .tif (bit sum f_output_mode)\n"
             " ├ Z0000 (initial ground elevation), X0000 (domain mask)   always written\n"
             " ├ FILENUMBER.csv   number ↔ time\n"
             " ├ Log.txt (identical to the screen), copy of the parameter file\n"
             " ├ probes/probe0001.csv …   probes (fn_record; every dt_recrd)\n"
             " ├ fluxes/flux0001.csv …    flux transects\n"
             " └ summary.csv              measurement summary"),
}}


def draw(lang):
    t = T[lang]
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 5.4), gridspec_kw={"width_ratios": [1, 1.3]})
    # ------------------------------------------------ (a) raster order
    ax = axs[0]; ax.set_aspect("equal", adjustable="datalim"); ax.axis("off")
    NX, NY = 5, 4
    vals = [["0.0", "0.0", "0.3", "1.2", "0.1"], ["0.0", "0.4", "1.5", "0.8", "0.0"],
            ["0.2", "1.1", "1.9", "0.3", "0.0"], ["0.6", "1.4", "0.5", "0.0", "0.0"]]
    fx, fy = 0.0, 0.0
    ax.add_patch(FancyBboxPatch((fx, fy), 4.6, NY * 0.6 + 0.9, boxstyle="round,pad=0.05", fc="white", ec=C_P, lw=1))
    label(ax, fx + 0.15, fy + NY * 0.6 + 0.65, t["fname"], color=C_P, fs=8.5, ha="left")
    for j in range(NY):
        label(ax, fx + 0.2, fy + NY * 0.6 - 0.3 - j * 0.6, "  ".join(vals[j]), fs=9, ha="left", family="DejaVu Sans Mono")
    mx, my, d = 6.0, 0.1, 0.6
    for j in range(NY):
        for i in range(NX):
            v = float(vals[j][i])
            ax.add_patch(Rectangle((mx + i * d, my + (NY - 1 - j) * d), d, d, fc=C_WATER if v > 0 else "white",
                                   alpha=min(1.0, 0.25 + v * 0.4) if v > 0 else 1, ec="none", zorder=1))
    grid(ax, mx, my, NX, NY, d, C_P, 0.7, z=2)
    label(ax, mx + NX * d / 2, my + NY * d + 0.75, t["north"], color=C_P, fs=10, fontweight="bold")
    ax.annotate("", (mx + NX * d / 2, my + NY * d + 0.62), (mx + NX * d / 2, my + NY * d + 0.25), arrowprops=dict(arrowstyle="-|>", color=C_P, lw=1.2))
    label(ax, mx + NX * d / 2, my - 0.2, t["map"], color=C_P, fs=8.5, va="top")
    arrow(ax, (fx + 4.7, fy + NY * 0.6 - 0.3), (mx - 0.1, my + (NY - 0.5) * d), C_X, lw=1.3)
    arrow(ax, (fx + 4.7, fy + 0.3), (mx - 0.1, my + 0.5 * d), C_P, lw=1.1)
    label(ax, fx, fy + NY * 0.6 + 1.3, t["row1"], color=C_X, fs=9, ha="left")
    label(ax, fx, fy - 0.5, t["rown"], color=C_P, fs=9, ha="left")
    label(ax, fx, fy - 0.9, t["col"], color=C_P, fs=9, ha="left")
    label(ax, fx, fy - 1.45, t["same"], color=C_P, fs=8.5, ha="left", va="top")
    ax.set_xlim(-0.3, 9.4); ax.set_ylim(-2.2, NY * 0.6 + 2.0)
    ax.set_title(t["ta"], loc="left", fontsize=9.5)
    # ------------------------------------------------ (b) output families
    ax = axs[1]; ax.axis("off")
    yT = 8.6
    x0, x1 = 1.0, 7.8
    ax.add_patch(FancyArrowPatch((x0 - 0.4, yT), (x1 + 0.8, yT), arrowstyle="-|>", mutation_scale=12, color="k", lw=1.4))
    label(ax, x0 - 0.5, yT, t["tl"], fs=9, ha="right")
    xs = [x0 + k * (x1 - x0) / 5 for k in range(6)]
    for xk in xs:
        ax.plot([xk], [yT], "s", color=C_C, ms=8, zorder=4)
    label(ax, xs[0], yT - 0.35, t["n0000"], color=C_C, fs=8.5, va="top")
    label(ax, xs[1] + 0.2, yT - 0.35, t["nk"], color=C_C, fs=8.5, va="top", ha="left")
    label(ax, xs[5], yT - 0.35, t["n9998"], color=C_C, fs=8.5, va="top")
    ax.plot([x1 + 2.0], [yT], "D", color=C_G, ms=8, zorder=4)
    label(ax, x1 + 2.0, yT - 0.35, t["n9999"], color="#3f7a2a", fs=8.5, va="top")
    ax.text(0.0, 5.6, t["tree"], fontsize=8.5, family=["IPAGothic", "DejaVu Sans Mono"], va="top", ha="left", linespacing=1.5)
    ax.set_xlim(-0.2, 11.0); ax.set_ylim(-0.3, 9.5)
    ax.set_title(t["tb"], loc="left", fontsize=9.5)
    fig.tight_layout()
    return save(fig, "io_files", lang)
