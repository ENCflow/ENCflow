#!/usr/bin/env python3
"""examples/vz_tani2023 の計算の構成を示す模式図(論文の数値を使わない)

  python3 plot_setup.py        # figs/setup.png
  python3 plot_setup.py en     # 英語ラベル版を en/figs/setup.png に描く

格子は make_case.py の SITES、柱の設定は param_*.txt から読む(図と入力が食い違わない
ように)。降雨・流出・圧力水頭など論文の図から取り出す数値は使わないので、data/ がなくても
描ける。依存: matplotlib
"""
import os
import re
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Rectangle, FancyArrowPatch, FancyBboxPatch

import make_case

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
_fonts = {f.name for f in font_manager.fontManager.ttflist}
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else \
    [next((f for f in ("Noto Sans CJK JP", "IPAGothic") if f in _fonts), "DejaVu Sans")]
matplotlib.rcParams["axes.unicode_minus"] = False
INK, MUTED, ORANGE, BLUE, SOIL = "#282c30", "#6b6a66", "#c45a26", "#2a78d6", "#e4d9c8"
CMAP = plt.get_cmap("YlOrBr")
DMAX = 2.6                          # 土層厚の軸の上限 (m)


def read_param(fn):
    """param_*.txt の「名前 = 値」(柱 1 の添字付きも)を読む"""
    p = {}
    for line in open(fn, encoding="utf-8"):
        for m in re.finditer(r"(\w+(?:\(1\))?)\s*=\s*([^,!\s]+)", line.split("!")[0]):
            p[m.group(1).replace("(1)", "")] = m.group(2).strip("'")
    return p


def box(ax, x, y, w, h, s, fc="white", ec=INK, fs=8.2, color=INK, weight="normal"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.004,rounding_size=0.012",
                                fc=fc, ec=ec, lw=0.9))
    ax.text(x + w / 2, y + h / 2, s, ha="center", va="center", fontsize=fs, color=color,
            weight=weight, linespacing=1.35)


def arrow(ax, p, q, color=INK, lw=1.1):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=10, color=color, lw=lw))


def workflow(ax):
    ax.set(xlim=(0, 1), ylim=(0, 1)); ax.axis("off")
    ax.text(0, 1.0, T("(a) 処理の流れ(./Run.sh <論文の PDF>)", "(a) Processing flow (./Run.sh <PDF of the paper>)"),
            fontsize=10, weight="bold", va="top")
    h = 0.30
    y1, y2 = 0.42, 0.04
    box(ax, 0.00, y1, 0.11, h, T("論文の PDF\n(利用者が入手)", "PDF of the paper\n(obtained by the user)"),
        fc="#f2f1ee")
    box(ax, 0.14, y1, 0.13, h, "extract_tani2023.py")
    box(ax, 0.30, y1, 0.19, h, T("data/ 降雨・基底流(KI2)\n論文の値(同梱しない)",
                                 "data/ rain, baseflow (KI2)\npaper's values (not shipped)"), fc="#fbe9dd")
    box(ax, 0.14, y2, 0.13, h, "make_case.py")
    box(ax, 0.30, y2, 0.19, h, T("data/grid_*/\n区画番号・土層厚", "data/grid_*/\nzones, soil depth"), fc="#fbe9dd")
    yc = (y1 + y2) / 2 + h / 2
    box(ax, 0.53, yc - h / 2, 0.12, h, T("encflow\nparam_<事例>.txt", "encflow\nparam_<event>.txt"))
    box(ax, 0.68, yc - h / 2, 0.12, h, T("result_<事例>/\nvz_zone.csv 等", "result_<event>/\nvz_zone.csv etc."))
    box(ax, 0.83, yc - h / 2, 0.17, h, T("compare_tani2023.py\n指標・図(手元のみ)", "compare_tani2023.py\nmetrics, figures (local)"))
    arrow(ax, (0.11, y1 + h / 2), (0.14, y1 + h / 2))
    arrow(ax, (0.27, y1 + h / 2), (0.30, y1 + h / 2))
    arrow(ax, (0.27, y2 + h / 2), (0.30, y2 + h / 2))
    arrow(ax, (0.49, y1 + h / 2), (0.53, yc + 0.05))
    arrow(ax, (0.49, y2 + h / 2), (0.53, yc - 0.05))
    arrow(ax, (0.65, yc), (0.68, yc))
    arrow(ax, (0.80, yc), (0.83, yc))


ROWS = [("grid_ty", T("TY1・TY2(竜ノ口山): 3 区画が TY の柱を共有", "TY1, TY2 (Tatsunokuchi-yama): 3 zones share the TY column")),
        ("grid_ki", T("KI1・KI2(桐生)", "KI1, KI2 (Kiryu)")),
        ("grid_mr", T("MREX・MR1(Mettman Ridge)", "MREX, MR1 (Mettman Ridge)"))]


def grids(ax):
    ax.set(xlim=(-0.95, 4.35), ylim=(0.6, 11.6)); ax.axis("off")
    ax.text(-0.95, 11.6, T("(b) 格子: 土層厚の線形分布を 1 行のセル列で表す(make_case.py)",
                           "(b) Grids: the linear distribution of soil depth as one row of cells (make_case.py)"),
            fontsize=10, weight="bold", va="top")
    y = 10.4
    for site, title in ROWS:
        ax.text(-0.95, y - 0.05, title + "  —  data/" + site, fontsize=8.2, color=MUTED, va="top")
        y -= 0.35
        for name, zone, dmax in make_case.SITES[site]:
            n = int(round(dmax / make_case.DZ)) + 1
            y -= 1.25
            for i in range(n):
                d = i * make_case.DZ
                ax.add_patch(Rectangle((d, y), make_case.DZ, 0.9, fc=CMAP(0.15 + 0.8 * d / DMAX), ec="white", lw=0.25))
            ax.add_patch(Rectangle((0, y), n * make_case.DZ, 0.9, fc="none", ec=INK, lw=0.7))
            ax.text(-0.05, y + 0.45, T("%s(区画 %d)" % (name, zone), "%s (zone %d)" % (name, zone)),
                    ha="right", va="center", fontsize=8.4)
            ax.text(n * make_case.DZ + 0.06, y + 0.45,
                    T("0〜%d cm・%d セル" % (round(dmax * 100), n), "0–%d cm, %d cells" % (round(dmax * 100), n)),
                    va="center", fontsize=8, color=MUTED)
        y -= 0.55
    for d in (0, 0.5, 1.0, 1.5, 2.0, 2.5):
        ax.plot([d, d], [y + 0.55, y + 0.35], color=INK, lw=0.8)
        ax.text(d, y + 0.2, "%g" % d, ha="center", va="top", fontsize=7.8)
    ax.plot([0, 2.5 + make_case.DZ], [y + 0.55, y + 0.55], color=INK, lw=0.8)
    ax.text(1.3, y - 0.45, T("セルの土層厚 = 左からの位置 (m)", "Soil depth of a cell = position from the left (m)"),
            ha="center", va="top", fontsize=8.2, color=MUTED)
    ax.text(3.25, 9.6, T("1 セル = 2.5 cm 刻みの 1 区分\n= 1 m²(dx = dy = 1 m)\n\nどの区分も同じ面積\n= 土層厚の線形分布\n\n"
                         "区画 = 1 行。全セルが VZ で\n地表流は生じない\n排水は系外へ(vz_out_kind = 2)",
                         "1 cell = one 2.5 cm class\n= 1 m² (dx = dy = 1 m)\n\nEvery class has the same area\n"
                         "= linear distribution of\nsoil depth\n\nZone = one row. All cells are VZ;\nno surface flow. "
                         "Drainage leaves\nthe system (vz_out_kind = 2)"),
            fontsize=8.0, va="top", linespacing=1.35)


COLS = [("param_ty1.txt", "TY", T("TY1・TY2", "TY1, TY2"), [(1.75, "KT"), (2.50, "MN"), (1.00, "SL")]),
        ("param_ki1.txt", "KI", T("KI1・KI2", "KI1, KI2"), [(1.30, "KI")]),
        ("param_mr1.txt", "MR", T("MREX・MR1", "MREX, MR1"), [(2.00, "CB1")]),
        ("param_kiex.txt", "KI", "KIEX", [(0.50, "Plot 2")])]
YS, YM, YB = 9.0, 2.6, -0.6          # 地表の y、1 m の長さ(0〜2.6 m)、10 m の y


def dy(d):
    return YS - YM * d


def columns(ax):
    ax.set(xlim=(-0.6, 12.4), ylim=(-5.3, 12.4)); ax.axis("off")
    ax.text(-0.6, 12.4, T("(c) 共有参照柱と読み出しの深さ(param_*.txt)", "(c) Shared reference columns and read-out depths (param_*.txt)"),
            fontsize=10, weight="bold", va="top")
    for k, (fn, soil, events, reads) in enumerate(COLS):
        p = read_param(fn)
        x = 0.55 + k * 3.0
        depth = float(p.get("vz_depth", 10.0))
        fixed = p.get("f_vz_bottom", "1") == "2"
        ax.text(x + 0.35, 10.6, events, ha="center", fontsize=9, weight="bold")
        ax.text(x + 0.35, 10.0, T("土壌 %s" % soil, "soil %s" % soil), ha="center", fontsize=7.8, color=MUTED)
        for j in range(3):
            arrow(ax, (x + 0.15 + 0.2 * j, 9.75), (x + 0.15 + 0.2 * j, YS + 0.08), color=BLUE, lw=0.9)
        if depth <= DMAX:
            ax.add_patch(Rectangle((x, dy(depth)), 0.7, YS - dy(depth), fc=SOIL, ec=INK, lw=0.9))
            ax.plot([x - 0.15, x + 0.85], [dy(depth), dy(depth)], color=ORANGE, lw=2.0)
            bottom = T("下端 ψ = %g m に固定\n(浸出)" % float(p.get("vz_psibot", 0)),
                       "bottom fixed at\nψ = %g m (seepage)" % float(p.get("vz_psibot", 0)))
            ax.text(x + 0.35, dy(depth) - 0.25, bottom, ha="center", va="top", fontsize=7.4, color=ORANGE)
        else:
            ax.add_patch(Rectangle((x, dy(DMAX)), 0.7, YS - dy(DMAX), fc=SOIL, ec=INK, lw=0.9))
            ax.add_patch(Rectangle((x, YB), 0.7, dy(DMAX) - 0.5 - YB, fc=SOIL, ec=INK, lw=0.9))
            for off in (0.0, 0.22):
                ax.plot([x - 0.12, x + 0.35, x + 0.82], [dy(DMAX) - 0.12 - off, dy(DMAX) - 0.02 - off, dy(DMAX) - 0.2 - off],
                        color=INK, lw=0.7)
            arrow(ax, (x + 0.35, YB + 0.5), (x + 0.35, YB - 0.55), color=BLUE, lw=0.9)
            ax.text(x + 0.35, YB - 0.65, T("%g m・自由排水" % depth, "%g m, free drainage" % depth),
                    ha="center", va="top", fontsize=7.4, color=MUTED)
        # 読み出しの深さの範囲(線形分布: 0 〜 最大値)
        for j, (dmax, name) in enumerate(reads):
            xx = x + 0.95 + 0.32 * j
            if dmax == depth:          # KIEX: 柱の下端の 1 深さ
                ax.plot([x + 0.7, xx + 0.1], [dy(dmax), dy(dmax)], color=ORANGE, lw=1.2)
                ax.text(xx + 0.15, dy(dmax), name, va="center", fontsize=7.4, color=ORANGE)
                continue
            ax.plot([xx, xx], [YS, dy(dmax)], color=ORANGE, lw=2.4, solid_capstyle="butt")
            ax.text(xx, dy(dmax) - 0.12, name, ha="center", va="top", fontsize=7.2, color=ORANGE, rotation=90)
        init = (T("初期: ψ = %g m" % float(p["vz_psi0"]), "initial: ψ = %g m" % float(p["vz_psi0"]))
                if "vz_psi0" in p else
                T("初期: 静水圧\n(地下水面 %g m)" % float(p["vz_wt0"]), "initial: hydrostatic\n(water table %g m)"
                  % float(p["vz_wt0"])))
        ax.text(x + 0.35, -2.4, ("Ks %g mm/h\nψm %g m, σ %g\n%s" % (float(p["vz_ks_mmh"]), float(p["vz_psim"]),
                                                                 float(p["vz_sigma"]), init)).replace("-", "−"),
                ha="center", va="top", fontsize=7.4, linespacing=1.3)
    for d in (0, 0.5, 1.0, 1.5, 2.0, 2.5):
        ax.plot([0.35, 0.55], [dy(d), dy(d)], color=INK, lw=0.7)
        ax.text(0.3, dy(d), "%g" % d, ha="right", va="center", fontsize=7.4)
    ax.text(0.3, YB + 0.1, "10", ha="right", va="center", fontsize=7.4)
    ax.text(0.3, YS + 0.65, T("深さ (m)", "depth (m)"), ha="right", fontsize=7.6, color=MUTED)
    ax.text(-0.6, -4.95, T("橙の縦線: 各区画のセルが柱を読む深さの範囲(0〜土層厚の最大値)。層厚 2.5 cm。雨は柱の上端へ",
                         "Orange bars: range of depths at which the cells of each zone read the column (0 to the largest "
                         "soil depth). Layers 2.5 cm. Rain enters the top"),
            ha="left", fontsize=7.6, color=MUTED)


POST = [("TY1・TY2", "TY1, TY2", "q", "q"),
        ("KI1・KI2", "KI1, KI2", "q / 2(残りは風化基岩への深部浸透)。KI2 は\n+ 基底流(vbase の差分 ÷ 面積 ÷ 時間)も",
         "q / 2 (the rest is deep percolation). For KI2\nalso + baseflow (difference of vbase ÷ area ÷ time)"),
        ("MREX", "MREX", "(q − 0.3 mm/h) / 2 ずつ上流堰・下流堰へ\n(入力の雨は 0.8 倍 = 蒸発散を差し引く)",
         "(q − 0.3 mm/h) / 2 to each weir\n(input rain × 0.8 = minus evapotranspiration)"),
        ("MR1", "MR1", "(q − 0.3 mm/h) / 2 × 860 m² → L/s(上流堰)", "(q − 0.3 mm/h) / 2 × 860 m² → L/s (upper weir)"),
        ("KIEX", "KIEX", "q(50 cm の柱の底面の排水)", "q (drainage at the bottom of the 50 cm column)")]


def post(ax):
    ax.set(xlim=(0, 1), ylim=(0, 1)); ax.axis("off")
    ax.text(0, 1.0, T("(d) 比べる量への後処理(compare_tani2023.py)", "(d) Post-processing (compare_tani2023.py)"),
            fontsize=10, weight="bold", va="top")
    ax.text(0, 0.88, T("q = 区画の累積排水 vdrain の差分 ÷ 区画面積 ÷ 時間 (mm/h)\n   (vz_zone.csv。= 行のセルの排水の平均)",
                       "q = difference of the zone's cumulative drainage vdrain\n   ÷ zone area ÷ time (mm/h) "
                       "(vz_zone.csv; = mean\n   drainage of the cells of the row)"),
            fontsize=8.2, va="top", linespacing=1.4)
    y = 0.70
    for ja_ev, en_ev, ja, en in POST:
        ax.text(0.0, y, T(ja_ev, en_ev), fontsize=8.4, weight="bold", va="top")
        ax.text(0.25, y, T(ja, en), fontsize=8.0, va="top", linespacing=1.35)
        y -= 0.115 if "\n" not in T(ja, en) else 0.16
    ax.text(0, y - 0.02, T("論文の計算は HYDRUS-1D。TY・KI の論文の計算値には分離基底流が\n加えてある。ENCflow は KI2 だけ、観測の最初と最後を結ぶ直線を\n"
                           "区画の基底流として与える(fn_vz_base。README の結果の節)",
                           "The paper computed with HYDRUS-1D. The separated baseflow is added\nto the values "
                           "calculated in the paper for TY and KI. ENCflow gives\nonly KI2 the straight line joining "
                           "the first and last observations\nas the baseflow of the zone (fn_vz_base; results "
                           "section of the README)"),
            fontsize=7.6, va="top", color=MUTED, linespacing=1.35)


def main():
    os.makedirs(FIGDIR, exist_ok=True)
    fig = plt.figure(figsize=(13.0, 11.2))
    fig.text(0.04, 0.975, T("examples/vz_tani2023 の計算の構成", "Configuration of the computations of examples/vz_tani2023"),
             fontsize=12.5, weight="bold", va="top")
    fig.text(0.04, 0.952, T("谷(2023)の設定を ENCflow の格子・柱・出口で表す方法。模式図で、論文の数値(降雨・流出・圧力水頭)は含まない",
                            "How the settings of Tani (2023) are expressed with ENCflow grids, columns and outlets. "
                            "Schematic; contains no numbers of the paper (rain, runoff, pressure head)"),
             fontsize=8.6, color=MUTED, va="top")
    workflow(fig.add_axes([0.04, 0.82, 0.92, 0.11]))
    grids(fig.add_axes([0.04, 0.50, 0.92, 0.30]))
    columns(fig.add_axes([0.02, 0.03, 0.60, 0.455]))
    post(fig.add_axes([0.62, 0.06, 0.36, 0.425]))
    fn = os.path.join(FIGDIR, "setup.png")
    fig.savefig(fn, dpi=130)
    plt.close(fig)
    print("wrote " + fn)


if __name__ == "__main__":
    main()
