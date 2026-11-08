#!/usr/bin/env python3
"""examples/stone_forest の機構の模式図と設定の図(計算結果は使わない)。

  python3 plot_setup.py        # figs/mechanism.png, figs/setup.png
  python3 plot_setup.py en     # 英語ラベル版を en/figs/ に描く

  figs/mechanism.png  (a) 実際の石林: 土層の下で節理に沿って溶け、後に土層が剥がれて柱が現れる
                      (b) ENCflow での表し方: 節理を横切る断面をセルの柱で描く(初期、式から求めた
                          5 kyr 後、崩落と崖錐の規則)
                      (c) 規則と値(param.txt)、(d) 2 m 格子の壁の傾きの上限 atan(H_c/Δx)
  figs/setup.png      節理の地図(入力)、初期の台地の横断、降雨と浸透、設定の要約

入力は make_terrain.py が書く z.txt / joints.txt(make で作る)と param.txt。
値は param.txt から読み、溶ける厚さは m_geomorph_dissol.f90 と同じ式 w = k_d·f_sol·F·morfac
(k_d = c_eq/ρ_r)で求める。
依存: numpy, matplotlib
"""
import os
import re
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
plt.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAPGothic", "IPAGothic", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)

C_ROCK, C_JOINT, C_SOIL, C_WATER, C_DISS, C_TALUS = "#d6d2c4", "#a49c88", "#a0522d", "#2c7fb8", "#c0392b", "#8f8f8f"
C_HEAD = "#1f4e79"                         # (c) の見出しの色
YR_H = 365.25 * 24.0                       # 1 年の時間数


def read_param(fn):
    """key = value(! 以降はコメント)と prval(1:2,n) = 時刻, 強度 を読む。"""
    p = {"prval": []}
    for line in open(fn, encoding="utf-8"):
        line = line.split("!")[0]
        m = re.match(r"\s*prval\(1:2,\s*\d+\)\s*=\s*([^,\s]+)\s*,\s*([^,\s]+)", line)
        if m:
            p["prval"].append((float(m.group(1)), float(m.group(2))))
            continue
        m = re.match(r"\s*(\w+)\s*=\s*([^,\s]+)", line)
        if m:
            p[m.group(1)] = m.group(2).strip("'\"")
    return p


def seconds(s):
    """"60d"・"10d"・"1h" などの時間文字列を秒に。"""
    m = re.match(r"([0-9.]+)\s*([dhms]?)", s)
    return float(m.group(1)) * {"d": 86400.0, "h": 3600.0, "m": 60.0, "s": 1.0, "": 1.0}[m.group(2)]


def sci(v):
    """1.2e-4 → 1.2×10⁻⁴"""
    e = int(np.floor(np.log10(abs(v))))
    sup = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")
    return "%g×10%s" % (round(v / 10.0 ** e, 2), str(e).translate(sup))


P = read_param("param.txt")
DX = float(P["lx"]) / int(P["nx"])
SD0, SY0 = float(P["sd0"]), float(P["sy0"])
KSV, KLEAK = float(P["gw_ksv_mmh"]), float(P["gwc_leak_mmh"])
RAIN = P["prval"][0][1]                    # mm/h(定常)
CEQ, RHO, FRES = float(P["dissol_ceq"]), float(P["dissol_rho"]), float(P["dissol_fres"])
KD = CEQ * 1.0e-3 / RHO                    # k_d = c_eq/ρ_r(init_dissol と同じ式)
HC, RC, PHI = float(P["rf_hc"]), float(P["rf_rc"]), float(P["rf_phi"])
NWIN = max(1, int(np.floor(RC / DX + 0.5)))   # 窓の半径のセル数 = nint(rf_rc/Δx)(init_rockfall)
RELAX, DZMAX = float(P["rf_relax"]), float(P["fluv_dzmax"])
MORFAC = float(P["morfac"])
DT, DTG = float(P["dt"]), float(P["dt_geomorph"])
DAYS = seconds(P["tt_c"]) / 86400.0        # 計算の日数
TEND_YR = DAYS * MORFAC / 365.25           # 地形時間 (年)
DAY_YR = MORFAC / 365.25                   # 1 日 = 地形時間何年
PANN = RAIN * YR_H / 1000.0                # 年雨量 (m/yr)
PANN_MM = round(PANN * 1e3, -1)            # 表示用(0.228 mm/h × 8766 h ≈ 2000 mm)
JOINTS = np.loadtxt(P["fn_dissol"])
FJ = float(JOINTS.max())                   # 節理の可溶率
RATE1 = KD * PANN                          # 可溶率 1 の基岩面の低下 (m/yr)。雨は全量浸透(F = 雨)


def _arrow(ax, x0, y0, x1, y1, color, lw=1.5, style="-|>", ms=9, rad=0.0):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw, shrinkA=0, shrinkB=0, mutation_scale=ms,
                                connectionstyle="arc3,rad=%g" % rad))


def _under(ax, s, y=-0.03):
    """パネルの下に説明を置く(セルの柱に重ねない)。"""
    ax.text(0.5, y, s, transform=ax.transAxes, ha="center", va="top", fontsize=8.4, linespacing=1.35)


# ------------------------------------------------------------------ (a) 実際の石林
def _bumps(x, xs, depth, w):
    return sum(depth * np.exp(-((x - xc) / w) ** 2) for xc in xs)


XJ = [9.0, 23.0, 37.0, 51.0]               # (a) の節理の位置(模式)


def _real_covered(ax):
    """土層に覆われた台地: 涵養水が節理に沿って集まり、土層の下で溝を溶かす。"""
    x = np.linspace(0, 60, 1201)
    zr = 20.0 - _bumps(x, XJ, 6.5, 1.9)                # 基岩面(土層の下の溝)
    zs = 22.4 + 0.25 * np.sin(2 * np.pi * x / 17.0) - _bumps(x, XJ, 0.5, 2.5)
    ax.fill_between(x, 0, zr, color=C_ROCK)
    ax.fill_between(x, zr, zs, color=C_SOIL, alpha=0.85)
    ax.plot(x, zs, "k-", lw=1.0)
    ax.plot(x, zr, color="0.35", lw=0.8)
    for xc in XJ:
        ax.plot([xc, xc], [1.0, 13.6], color="0.25", lw=1.0)
    for xi in np.arange(2, 60, 4.0):
        _arrow(ax, xi, 30.2, xi - 0.4, 27.4, C_WATER, lw=0.9, ms=6)
    ax.text(0.3, 30.7, T("雨", "rain"), color=C_WATER, fontsize=8.5)
    for xc in XJ:
        for s in (-1, 1):
            _arrow(ax, xc + s * 3.6, 21.9, xc + s * 0.9, 17.0, C_WATER, lw=1.2, ms=7)
    ax.text(30, 23.6, T("土層: 土壌 CO₂ を取り込んだ水がしみ込む", "soil: water takes up soil CO₂ as it soaks in"),
            ha="center", fontsize=8.5, color=C_SOIL)
    box = dict(boxstyle="square,pad=0.2", fc=C_ROCK, ec="none", alpha=0.92)
    ax.text(16.0, 9.0, T("涵養水が節理に集まり\n土層の下で溶かす\n(subsoil dissolution)",
                         "recharge gathers in the\njoints and dissolves below\nthe soil (subsoil dissolution)"),
            ha="center", fontsize=8.5, color=C_DISS, bbox=box)
    ax.text(44.0, 9.0, T("節理 → 溝\n(grike、カッレン)\n間の岩体 → 柱", "joint → cleft\n(grike, karren)\nrock between → pillar"),
            ha="center", fontsize=8.5, bbox=box)
    ax.text(51.6, 2.0, T("節理", "joint"), fontsize=8, color="0.25")
    ax.set_xlim(0, 60)
    ax.set_ylim(0, 32)
    ax.axis("off")


def _real_exhumed(ax):
    """土層が剥がれた後: 節理面の壁をもつ柱、崩れた岩屑は溝で溶ける。"""
    x = np.linspace(0, 60, 1201)
    zr = 21.0 - 0.6 * (1 - np.cos(2 * np.pi * (x - 2.0) / 14.0))
    for xc in XJ:
        r = np.abs(x - xc)
        zr = np.where(r < 1.4, 4.0 + 1.2 * (r / 1.4) ** 2, zr)
        zr = np.where((r >= 1.4) & (r < 2.2), 5.2 + 15.8 * np.clip((r - 1.4) / 0.8, 0, 1) ** 0.35, zr)
    zr = np.minimum(zr, 21.0)
    ax.fill_between(x, 0, zr, color=C_ROCK)
    ax.plot(x, zr, "k-", lw=1.0)
    # 壁の頂から欠け落ちた岩塊(欠けた跡は白)と、溝に落ちた岩塊
    xw = XJ[2] - 2.2
    ax.add_patch(plt.Polygon([(xw - 1.6, 21.2), (xw + 0.05, 21.2), (xw + 0.05, 17.4), (xw - 0.4, 17.6)], color="w"))
    ax.plot([xw - 1.6, xw - 0.4, xw + 0.05], [21.0, 17.6, 17.4], "k-", lw=0.8)
    ax.add_patch(plt.Polygon([(XJ[2] - 1.25, 5.3), (XJ[2] + 1.25, 5.3), (XJ[2] + 1.15, 8.2), (XJ[2] - 0.9, 9.0)], color=C_TALUS))
    _arrow(ax, xw - 0.2, 16.8, XJ[2] - 0.2, 9.6, "0.3", lw=1.2, rad=-0.15)
    ax.text(36.0, 26.6, T("壁は崩落で後退し、\n落ちた岩屑は溝で溶ける", "walls retreat by collapse;\nfallen debris dissolves in the clefts"),
            fontsize=8.5, ha="center")
    ax.annotate("", xy=(56.0, 21.0), xytext=(56.0, 4.0), arrowprops=dict(arrowstyle="<->", color="k", lw=1.0))
    ax.text(56.6, 11.5, T("数 m\n〜30 m", "a few m\nto 30 m"), fontsize=8)
    ax.text(8.0, 26.6, T("柱の壁 = 節理面", "pillar walls\n= joint faces"), fontsize=8.5, ha="center")
    _arrow(ax, 8.0, 26.0, XJ[0] + 1.9, 18.0, "k", lw=1.0)
    ax.set_xlim(0, 60)
    ax.set_ylim(0, 32)
    ax.axis("off")


# ------------------------------------------------------------------ (b) ENCflow の表し方(セルの柱)
NC = 21                                    # 断面のセル数(節理 3 本を横切る)
JC = (3, 10, 17)                           # 節理のセル(14 m 間隔 = 7 セル)
Z0 = 30.0                                  # 台地の高さ (m)
FSOL = np.array([FJ if i in JC else 1.0 for i in range(NC)])


def _cells(ax, z, sd, fsol, zbase, ht=None, outline=None):
    """セルごとの柱: 基岩(節理のセルは濃い色)、土層、崖錐(土層 sd の上部に数える)。"""
    n = len(z)
    ht = np.zeros(n) if ht is None else ht
    for i in range(n):
        x0 = i * DX
        zb = z[i] - sd[i]
        ax.add_patch(plt.Rectangle((x0, zbase), DX, zb - zbase, fc=C_JOINT if fsol[i] > 1 else C_ROCK, ec="0.55", lw=0.5))
        ax.add_patch(plt.Rectangle((x0, zb), DX, sd[i] - ht[i], fc=C_SOIL, ec="0.55", lw=0.5, alpha=0.9))
        if ht[i] > 0:
            ax.add_patch(plt.Rectangle((x0, z[i] - ht[i]), DX, ht[i], fc=C_TALUS, ec="0.4", lw=0.5))
    if outline is not None:
        xs = np.repeat(np.arange(n + 1) * DX, 2)[1:-1]
        ax.plot(xs, np.repeat(outline, 2), color="k", lw=0.9, ls="--")
    ax.set_xlim(-0.3, n * DX + 0.3)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ("top", "right", "bottom", "left"):
        ax.spines[s].set_visible(False)


ZB_B = 17.0                                # (b) の初期と 5 kyr 後の下端 (m)


def _encflow_initial(ax):
    z = np.full(NC, Z0)
    sd = np.full(NC, SD0)
    _cells(ax, z, sd, FSOL, ZB_B)
    ax.set_ylim(ZB_B, 33.4)
    for i in range(NC):
        _arrow(ax, (i + 0.5) * DX, 32.9, (i + 0.5) * DX, 31.1, C_WATER, lw=0.8, ms=5)
    for i in JC:
        ax.text((i + 0.5) * DX, 27.0, "%g" % FJ, ha="center", fontsize=9.5)
    for i in ((JC[0] + JC[1] + 1) / 2, (JC[1] + JC[2] + 1) / 2):    # 柱の中央
        ax.text(i * DX, 27.0, "1", ha="center", fontsize=9.5, color="0.35")
    ax.text(NC * DX / 2, 25.0, T("← 可溶率 f_sol(joints.txt)→", "← soluble fraction f_sol (joints.txt) →"), ha="center",
            fontsize=8.2, color="0.2")
    ax.text(NC * DX + 0.4, Z0 - SD0 / 2, T("土層", "soil"), fontsize=8, color=C_SOIL, va="center")
    _under(ax, T("節理のセル(濃い灰)は可溶率 %g、ほかは 1\n(fn_dissol)。土層 %g m(sd0)。雨 %g mm/h は\n"
                 "浸透能 %g mm/h より小さいので全量しみ込む\n(F = 雨。流出・湛水なし)" % (FJ, SD0, RAIN, KSV),
                 "Joint cells (dark grey): soluble fraction %g, others 1\n(fn_dissol). Soil %g m (sd0). The rain of %g mm/h is\n"
                 "below the capacity of %g mm/h, so all of it soaks in\n(F = rain; no runoff, no ponding)" % (FJ, SD0, RAIN, KSV)))


def _encflow_dissol(ax, tyr):
    """式から求めた tyr 年後の断面(崩落が始まる前。溶食は局所・線形)。"""
    w = RATE1 * FSOL * tyr                 # 基岩面の低下 (m)
    z = Z0 - (1.0 - FRES) * w
    sd = SD0 + FRES * w
    _cells(ax, z, sd, FSOL, ZB_B, outline=np.full(NC, Z0))
    ax.set_ylim(ZB_B, 33.4)
    zw = z[0]
    ax.plot([0, NC * DX], [zw - HC, zw - HC], color=C_DISS, lw=1.1, ls=":")
    ax.text(0.15, zw - HC + 0.3, T("壁の頂 − H_c(%g m)" % HC, "wall top − H_c (%g m)" % HC), fontsize=8, color=C_DISS,
            bbox=dict(boxstyle="square,pad=0.1", fc="w", ec="none", alpha=0.85))
    ax.text(NC * DX, Z0 + 0.4, T("破線 = 初期の地表", "dashed = initial surface"), fontsize=8, ha="right")
    i = JC[1]
    _arrow(ax, (i + 0.5) * DX, Z0, (i + 0.5) * DX, z[i], C_DISS, lw=1.3, ms=8)
    ax.text((i + 1.15) * DX, z[i] + 0.9, "%.1f m" % ((1.0 - FRES) * w[i]), fontsize=8.2, color=C_DISS,
            bbox=dict(boxstyle="square,pad=0.1", fc="w", ec="none", alpha=0.85))
    k = 6
    _arrow(ax, (k + 0.5) * DX, Z0, (k + 0.5) * DX, z[k], C_DISS, lw=1.2, ms=6)
    ax.text((k + 0.95) * DX, Z0 + 0.4, "%.1f m" % ((1.0 - FRES) * w[k]), fontsize=8.2, color=C_DISS)
    _under(ax, T("基岩面は w = k_d·f_sol·雨 で下がる:\n%.2f m/kyr(f_sol 1)、%.2f m/kyr(f_sol %g)。\n"
                 "地表は (1 − %g) w 下がり、土層は %g w 厚くなる(残渣)。\n土層は地表に載ったまま溝へ沈む"
                 % (RATE1 * 1e3, RATE1 * FJ * 1e3, FJ, FRES, FRES),
                 "The bedrock surface lowers by w = k_d·f_sol·rain:\n%.2f m/kyr (f_sol 1), %.2f m/kyr (f_sol %g). The surface\n"
                 "lowers by (1 − %g) w; the soil thickens by %g w (residue)\nand rides on the surface, sinking into the clefts"
                 % (RATE1 * 1e3, RATE1 * FJ * 1e3, FJ, FRES, FRES)))


def _encflow_collapse(ax):
    """崩落と崖錐の規則(模式。1 本の溝の拡大。量は説明用)。"""
    n, jc = 9, 4
    ztop, depth = 28.9, HC + 4.0
    zbef = np.full(n, ztop)
    zbef[jc] = ztop - depth
    sdbef = np.full(n, 1.1)
    sdbef[jc] = 1.8
    fsol = np.ones(n)
    fsol[jc] = FJ
    # 壁の超過 H_w − H_c = 4 m を、隣の 2 セル(a)と 2 つ目(b)から溝へ移すと 3a + 2b = 4 で H_w = H_c
    a, b = 1.0, 0.5
    z, sd, ht = zbef.copy(), sdbef.copy(), np.zeros(n)
    for s in (-1, 1):
        for k, dz in ((jc + s, a), (jc + 2 * s, b)):
            z[k] -= dz
            sd[k] = max(sd[k] - dz, 0.0)   # 供給側は土層から先に減る(apply_bedrock)
    z[jc] += 2 * (a + b)
    sd[jc] += 2 * (a + b)
    ht[jc] = 2 * (a + b)
    zbase = 13.0
    _cells(ax, z, sd, fsol, zbase, ht=ht, outline=zbef)
    ax.set_ylim(zbase, 31.6)
    iw = jc - 1                            # 窓の中心(壁のセル)
    ax.add_patch(plt.Rectangle(((iw - NWIN) * DX + 0.06, zbef[jc] - 0.5), (2 * NWIN + 1) * DX - 0.12, ztop - zbef[jc] + 1.1,
                               fill=False, ec="C0", lw=1.2, ls="--"))
    ax.text((iw - NWIN) * DX + 0.1, ztop + 0.85, T("窓: 壁のセル ± %d セル(rf_rc %g m)" % (NWIN, RC),
                                                   "window: wall cell ± %d cells (rf_rc %g m)" % (NWIN, RC)),
            color="C0", fontsize=8)
    # H_w(壁のセルの列に描く)と H_c、超過分
    xa = (iw + 0.5) * DX
    ax.annotate("", xy=(xa, zbef[jc]), xytext=(xa, ztop), arrowprops=dict(arrowstyle="<->", color=C_DISS, lw=1.1,
                                                                           shrinkA=0, shrinkB=0))
    ax.plot([xa, (jc + 0.5) * DX], [zbef[jc], zbef[jc]], color=C_DISS, lw=0.8, ls=":")
    ax.text(xa - 0.15, zbef[jc] + 2.2, "H_w", color=C_DISS, fontsize=9, ha="right",
            bbox=dict(boxstyle="square,pad=0.1", fc="w", ec="none", alpha=0.85))
    zc = zbef[jc] + HC
    ax.plot([(iw - 0.6) * DX, (jc + 1.5) * DX], [zc, zc], color=C_DISS, lw=1.0, ls=":")
    ax.annotate("", xy=((iw - 0.3) * DX, zc), xytext=((iw - 0.3) * DX, zbef[jc]),
                arrowprops=dict(arrowstyle="<->", color="0.25", lw=0.9, shrinkA=0, shrinkB=0))
    ax.text((iw - 0.4) * DX, zc - 2.6, T("H_c\n= %g m" % HC, "H_c\n= %g m" % HC), fontsize=8.2, ha="right", color="0.2",
            bbox=dict(boxstyle="square,pad=0.1", fc="w", ec="none", alpha=0.85))
    ax.annotate("", xy=(xa, zc), xytext=(xa, ztop), arrowprops=dict(arrowstyle="-", color=C_DISS, lw=3.2,
                                                                     shrinkA=0, shrinkB=0))
    ax.text((iw + NWIN + 1.1) * DX, (zc + ztop) / 2, T("H_w − H_c の\n超過分を低い\n側へ移す", "the excess\nH_w − H_c moves\nto the lower side"),
            color=C_DISS, fontsize=8.2, va="center", bbox=dict(boxstyle="square,pad=0.1", fc="w", ec="none", alpha=0.85))
    for s in (-1, 1):
        _arrow(ax, (jc + 0.5 + s * 0.9) * DX, ztop - 0.5, (jc + 0.5 + s * 0.15) * DX, z[jc] + 2.0, "0.2", lw=1.2, ms=8,
               rad=0.3 * s)
    ax.text((jc + 2.6) * DX, z[jc] - ht[jc] / 2, T("← 崖錐 ht", "← talus ht"), fontsize=8.2, ha="center", va="center",
            bbox=dict(boxstyle="square,pad=0.1", fc="w", ec="none", alpha=0.85))
    _arrow(ax, (jc + 0.5) * DX, z[jc] - 0.3, (jc + 0.5) * DX, z[jc] - ht[jc] + 0.4, C_DISS, lw=1.4, ms=7)
    ax.text((jc + 2.6) * DX, z[jc] - ht[jc] - 1.0, T("溶食はまず崖錐を\n溶かす(残渣 %g は\n土層に残る)" % FRES,
                                                      "dissolution takes the\ntalus first (residue %g\nstays as soil)" % FRES),
            fontsize=8, ha="center", va="top", color=C_DISS,
            bbox=dict(boxstyle="square,pad=0.15", fc="w", ec="none", alpha=0.85))
    _under(ax, T("破線 = 崩れる前。窓の中の最低点との落差 H_w が\nH_c を超えると、安息角 %g° より急なエッジで超過分を\n"
                 "低い側へ移す(基岩も崩れる: rf_bedrock = 1)。落ちたもの\n(壁の上の土層を含む)は崖錐 ht になる" % PHI,
                 "Dashed = before collapse. Where the drop H_w to the lowest\npoint in the window exceeds H_c, edges steeper than %g°\n"
                 "move the excess to the lower side (bedrock too: rf_bedrock = 1).\nWhat falls (soil on the wall included) becomes talus ht" % PHI))


# ------------------------------------------------------------------ (c) 規則、(d) 壁の傾きの上限
def _rules(ax):
    ax.axis("off")
    tc = HC / ((1.0 - FRES) * (FJ - 1.0) * RATE1)
    lines = [
        (T("溶食(f_dissol = 1、dissol_src = 1。地形更新ごと)", "Dissolution (f_dissol = 1, dissol_src = 1; at each landform update)"), True),
        (T("  w = k_d · f_sol · F · morfac。F = 更新間隔 %g 分の浸透量(= 雨)、morfac = %s" % (DTG / 60, sci(MORFAC)),
           "  w = k_d · f_sol · F · morfac; F = infiltration over the %g-min interval (= rain), morfac = %s" % (DTG / 60, sci(MORFAC))), False),
        (T("  k_d = c_eq/ρ_r = %g g/m³ ÷ %g kg/m³ = %s。基岩面 z − sd が w、地表 z が (1 − f_res) w 下がり、"
           % (CEQ, RHO, sci(KD)),
           "  k_d = c_eq/ρ_r = %g g/m³ ÷ %g kg/m³ = %s. The bedrock z − sd lowers by w, the surface z by (1 − f_res) w"
           % (CEQ, RHO, sci(KD))), False),
        (T("  土層 sd が f_res w 厚くなる(f_res = %g)。年雨量 ≈ %.0f mm → 基岩面 %.2f m/kyr × f_sol"
           % (FRES, PANN_MM, RATE1 * 1e3),
           "  and the soil sd thickens by f_res w (f_res = %g). Rain ≈ %.0f mm/yr → bedrock %.2f m/kyr × f_sol"
           % (FRES, PANN_MM, RATE1 * 1e3)), False),
        (T("  地表の溝は (1 − f_res)(%g − 1) × %.2f = %.2f m/kyr で深まり、約 %.1f kyr で H_c に達する"
           % (FJ, RATE1 * 1e3, (1 - FRES) * (FJ - 1) * RATE1 * 1e3, tc / 1e3),
           "  The cleft in the surface deepens at (1 − f_res)(%g − 1) × %.2f = %.2f m/kyr and reaches H_c in about %.1f kyr"
           % (FJ, RATE1 * 1e3, (1 - FRES) * (FJ - 1) * RATE1 * 1e3, tc / 1e3)), False),
        (T("崩落と崖錐(f_rockfall = 1、rf_bedrock = 1)", "Rockfall and talus (f_rockfall = 1, rf_bedrock = 1)"), True),
        (T("  H_w = 地表 z − 窓の中の最低の z。窓は中心 ± nint(rf_rc/Δx) = ±%d セル(%d × %d セル)"
           % (NWIN, 2 * NWIN + 1, 2 * NWIN + 1),
           "  H_w = surface z − lowest z in the window; the window is the centre ± nint(rf_rc/Δx) = ±%d cells (%d × %d)"
           % (NWIN, 2 * NWIN + 1, 2 * NWIN + 1)), False),
        (T("  H_w > H_c = %g m なら、崖錐の安息角 %g° より急なエッジで超過分を低い側へ移す(rf_relax = %g で"
           % (HC, PHI, RELAX),
           "  If H_w > H_c = %g m, edges steeper than the talus angle %g° move the excess to the lower side (gradually,"
           % (HC, PHI)), False),
        (T("  少しずつ、1 エッジ・1 更新 %g m まで)。落ちたものは受け手の崖錐 ht と土層 sd に積む" % DZMAX,
           "  rf_relax = %g, at most %g m per edge and update). What falls is added to the talus ht and soil sd" % (RELAX, DZMAX)), False),
        (T("崖錐の溶食(自動)と土層", "Talus dissolution (automatic) and the soil"), True),
        (T("  崖錐のあるセルは dh = min(ht, w) を先に溶かし、z と sd を (1 − f_res) dh 下げる(残渣 f_res dh は土層に残る)",
           "  A cell with talus dissolves dh = min(ht, w) first and lowers z and sd by (1 − f_res) dh (the residue stays)"), False),
        (T("  土層を剥ぎ取る過程はない: 土層は溶食で下がる地表に載ったまま溝へ沈む",
           "  No process strips the soil: it rides on the surface lowered by dissolution and sinks into the clefts"), False),
    ]
    y = 1.0
    for s, head in lines:
        ax.text(0.0, y, s, fontsize=8.6, va="top", color=C_HEAD if head else "k", transform=ax.transAxes)
        y -= 0.083


def _wall_angle(ax):
    """1 セルの段差は H_c まで残る → 壁の傾きの上限 atan(H_c/Δx)。"""
    lo = 2.0
    hs = [lo + HC, lo + HC, lo, lo]
    for i, h in enumerate(hs):
        ax.add_patch(plt.Rectangle((i * DX, 0), DX, h, fc=C_ROCK, ec="0.5", lw=0.6))
    xc1, xc2 = 1.5 * DX, 2.5 * DX
    ax.plot([xc1, xc2], [hs[1], hs[2]], color=C_DISS, lw=1.8)
    ax.plot([xc1, xc2 + 0.9 * DX], [hs[1], hs[1]], color="0.4", lw=0.8, ls=":")
    ang = np.degrees(np.arctan(HC / DX))
    th = np.radians(np.linspace(-ang, 0, 30))
    ax.plot(xc1 + 1.3 * np.cos(th), hs[1] + 1.3 * np.sin(th), color=C_DISS, lw=0.9)
    ax.text(xc1 + 1.45, hs[1] - 1.9, "%.0f°" % ang, color=C_DISS, fontsize=10)
    ax.annotate("", xy=(xc2 + 0.9 * DX, hs[2]), xytext=(xc2 + 0.9 * DX, hs[1]),
                arrowprops=dict(arrowstyle="<->", color="k", lw=0.9, shrinkA=0, shrinkB=0))
    ax.text(xc2 + 1.0 * DX, (hs[1] + hs[2]) / 2, "H_c = %g m" % HC, fontsize=8.5, va="center")
    ax.annotate("", xy=(xc2, -0.7), xytext=(xc1, -0.7), arrowprops=dict(arrowstyle="<->", color="k", lw=0.9, shrinkA=0, shrinkB=0))
    ax.text((xc1 + xc2) / 2, -1.1, "Δx = %g m" % DX, ha="center", va="top", fontsize=8.5)
    ax.text(-0.3, -3.4, T("隣のセルとの段差は H_c まで崩れずに残る\n→ %g m 格子の壁の傾きは atan(H_c/Δx)\n= atan(%g/%g) ≈ %.0f° が上限(格子幅で決まる形)"
                          % (DX, HC, DX, ang),
                          "a step to the neighbour stands up to H_c\n→ on a %g m grid the wall angle is at most\natan(H_c/Δx) = atan(%g/%g) ≈ %.0f° (set by the cell size)"
                          % (DX, HC, DX, ang)),
            fontsize=8.5, va="top")
    ax.set_xlim(-0.4, 4 * DX + 4.2)
    ax.set_ylim(-8.6, lo + HC + 1.0)
    ax.set_aspect("equal")
    ax.axis("off")


def mechanism():
    fig = plt.figure(figsize=(14, 12.4))
    gs = fig.add_gridspec(5, 6, height_ratios=[0.95, 0.2, 1.05, 0.42, 0.95], hspace=0.12, wspace=0.14)
    ax = fig.add_subplot(gs[0, 0:3])
    _real_covered(ax)
    ax.set_title(T("(a) 実際の石林(模式): 土層に覆われた台地で、\n節理に沿って溶ける",
                   "(a) A real stone forest (schematic): below a soil\ncover, dissolution follows the joints"),
                 loc="left", fontsize=10)
    ax = fig.add_subplot(gs[0, 3:6])
    _real_exhumed(ax)
    ax.set_title(T("\n→ 後に土層が剥ぎ取られ(exhumation)、柱が地表に現れる", "→ later the soil is stripped (exhumation)\nand the pillars appear"),
                 loc="left", fontsize=10)
    ax = fig.add_subplot(gs[2, 0:2])
    _encflow_initial(ax)
    ax.set_title(T("(b) ENCflow: 節理を横切る断面(1 列 = 1 セル %g m)\n初期(入力)" % DX,
                   "(b) ENCflow: section across the joints (one column = one %g m cell)\ninitial (inputs)" % DX),
                 loc="left", fontsize=9.5)
    ax = fig.add_subplot(gs[2, 2:4])
    _encflow_dissol(ax, 5000.0)
    ax.set_title(T("\n5 kyr 後(式から。崩落が始まる前)", "\nafter 5 kyr (from the formula; before collapse)"), loc="left", fontsize=9.5)
    ax = fig.add_subplot(gs[2, 4:6])
    _encflow_collapse(ax)
    ax.set_title(T("\n溝の 1 本を拡大: 崩落と崖錐の規則(模式。量は説明用)", "\none cleft enlarged: collapse and talus (rule; amounts illustrative)"),
                 loc="left", fontsize=9.5)
    ax = fig.add_subplot(gs[4, 0:4])
    _rules(ax)
    ax.set_title(T("(c) 規則と値(param.txt)", "(c) Rules and values (param.txt)"), loc="left", fontsize=10)
    ax = fig.add_subplot(gs[4, 4:6])
    _wall_angle(ax)
    ax.set_title(T("(d) 壁の傾きの上限", "(d) Upper limit of the wall angle"), loc="left", fontsize=10)
    fig.savefig(f"{FIGDIR}/mechanism.png", dpi=105, bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ setup.png
def setup():
    z = np.loadtxt(P["fn_z"])
    ny, nx = z.shape
    ext = [0, nx * DX, 0, ny * DX]
    jsec = ny // 2 + 1                     # plot_results.py の sections.png と同じ行(y = 103 m)
    ysec = (jsec + 0.5) * DX
    fig = plt.figure(figsize=(14.5, 6.9))
    gs = fig.add_gridspec(2, 3, width_ratios=[1.12, 1.3, 1.05], height_ratios=[1, 1], wspace=0.3, hspace=0.55)
    ax = fig.add_subplot(gs[:, 0])
    im = ax.imshow(JOINTS, origin="lower", extent=ext, cmap="Greys", vmin=0, vmax=FJ)
    ax.axhline(ysec, color="C1", lw=1.2, ls="--")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title(T("節理の地図(入力 joints.txt)\n節理のセル %.1f %%、破線 = 横断の位置" % (100.0 * (JOINTS > 1).mean()),
                   "Joint map (input joints.txt)\njoint cells %.1f %%; dashed = section" % (100.0 * (JOINTS > 1).mean())),
                 fontsize=9)
    fig.colorbar(im, ax=ax, shrink=0.62).set_label(T("可溶率(節理 %g、ほか 1)" % FJ, "soluble fraction (joints %g, else 1)" % FJ))
    ax = fig.add_subplot(gs[0, 1])
    zs = z[jsec]
    zlo = 26.0
    xst = np.repeat(np.arange(nx + 1) * DX, 2)[1:-1]
    zst = np.repeat(zs, 2)
    ax.fill_between(xst, zlo, zst - SD0, color=C_ROCK)
    ax.fill_between(xst, zst - SD0, zst, color=C_SOIL, alpha=0.9)
    for i in np.where(JOINTS[jsec] > 1)[0]:
        ax.add_patch(plt.Rectangle((i * DX, zlo), DX, zs[i] - SD0 - zlo, fc=C_JOINT, ec="none"))
    ax.plot(xst, zst, "k-", lw=0.9)
    ax.set_xlim(0, nx * DX)
    ax.set_ylim(zlo, 30.9)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("z (m)")
    ax.set_title(T("y = %.0f m の横断(初期。台地 z = 30 m ± 0.1 m)\n茶 = 土層 %g m、濃い灰 = 節理のセル(可溶率 %g)"
                   % (ysec, SD0, FJ),
                   "Section at y = %.0f m (initial; plateau z = 30 m ± 0.1 m)\nbrown = soil %g m, dark grey = joint cells (fraction %g)"
                   % (ysec, SD0, FJ)), fontsize=9)
    ax = fig.add_subplot(gs[1, 1])
    ax.fill_between([0, DAYS], 0.01, RAIN, color="#9ecae1", label=T("降雨 %g mm/h(定常。年 ≈ %.0f mm)" % (RAIN, PANN_MM),
                                                                     "rain %g mm/h (steady; ≈ %.0f mm a year)" % (RAIN, PANN_MM)))
    ax.axhline(KSV, color="C1", ls="--", lw=1.2)
    ax.text(1.5, KSV * 1.22, T("浸透能 %g mm/h(Green-Ampt): 雨は全量しみ込む" % KSV, "capacity %g mm/h (Green-Ampt): all rain soaks in" % KSV),
            fontsize=8, color="C1")
    ax.axhline(KLEAK, color="0.25", ls="-.", lw=1.2)
    ax.text(1.5, KLEAK * 0.62, T("土層 → 管路層の交換能 %g mm/h: 土層は飽和しない" % KLEAK,
                                 "soil → conduit layer %g mm/h: the soil never saturates" % KLEAK),
            fontsize=8, color="0.25")
    ax.set_yscale("log")
    ax.set_xlim(0, DAYS)
    ax.set_ylim(0.05, 200)
    ax.set_xlabel(T("時刻 (日)。%g 日 = 地形時間 %.1f kyr(morfac %s)" % (DAYS, TEND_YR / 1e3, sci(MORFAC)),
                    "time (days); %g days = %.1f kyr of landform time (morfac %s)" % (DAYS, TEND_YR / 1e3, sci(MORFAC))))
    ax.set_ylabel("mm/h")
    ax.legend(fontsize=7.5, loc="lower right")
    ax.set_title(T("降雨と浸透(準定常強制)", "Rain and infiltration (quasi-steady forcing)"), fontsize=9)
    ax = fig.add_subplot(gs[:, 2])
    ax.axis("off")
    rows = [
        (T("領域", "domain"), T("%g × %g m、Δx = %g m(%d × %d)\n四周は壁" % (nx * DX, ny * DX, DX, nx, ny),
                                "%g × %g m, Δx = %g m (%d × %d)\nclosed walls" % (nx * DX, ny * DX, DX, nx, ny))),
        (T("台地", "plateau"), T("z = 30 m(相関長 10 m・\n標準偏差 0.1 m の起伏)", "z = 30 m (relief of correlation\nlength 10 m, std 0.1 m)")),
        (T("節理", "joints"), T("x = 一定を 14 m、y = 一定を 18 m 間隔\n(±1 セルの乱れ)、1 セル幅、可溶率 %g" % FJ,
                                "constant x every 14 m, constant y every\n18 m (±1-cell jitter), one cell wide,\nsoluble fraction %g" % FJ)),
        (T("土層・浸透", "soil"), T("土層 %g m(sy %g)、浸透能 %g mm/h\n土層の水は管路層へ %g mm/h で抜ける\n(吸込穴・側方通水なし)" % (SD0, SY0, KSV, KLEAK),
                                    "soil %g m (sy %g), capacity %g mm/h\nsoil water drains to the conduit layer\nat %g mm/h (no sinks, no lateral flow)" % (SD0, SY0, KSV, KLEAK))),
        (T("溶食", "dissolution"), T("c_eq %g mg/L、ρ_r %g(k_d = %s)\n浸透量に比例(dissol_src = 1)\n残渣率 %g" % (CEQ, RHO, sci(KD), FRES),
                                     "c_eq %g mg/L, ρ_r %g (k_d = %s)\nproportional to infiltration\n(dissol_src = 1), residue %g" % (CEQ, RHO, sci(KD), FRES))),
        (T("崩落", "collapse"), T("H_c = %g m、窓 %g m(%d セル)、崖錐 %g°\nrelax %g、基岩も崩す(rf_bedrock = 1)\n1 エッジ・1 更新 %g m まで" % (HC, RC, NWIN, PHI, RELAX, DZMAX),
                                  "H_c = %g m, window %g m (%d cells),\ntalus %g°, relax %g, bedrock collapses\n(rf_bedrock = 1), at most %g m per edge\nand update" % (HC, RC, NWIN, PHI, RELAX, DZMAX))),
        (T("時間", "time"), T("dt %g s、地形更新 %g 分 × morfac %s\n1 日 = %.0f 年、%g 日 = %.1f kyr" % (DT, DTG / 60, sci(MORFAC), DAY_YR, DAYS, TEND_YR / 1e3),
                              "dt %g s, update every %g min\n× morfac %s; 1 day = %.0f years,\n%g days = %.1f kyr" % (DT, DTG / 60, sci(MORFAC), DAY_YR, DAYS, TEND_YR / 1e3))),
    ]
    yv = 0.97
    for k, v in rows:
        ax.text(0.0, yv, k, fontsize=9, va="top", color="0.2")
        ax.text(0.27, yv, v, fontsize=9, va="top")
        yv -= 0.07 + 0.048 * v.count("\n")
    ax.set_title(T("設定の要約", "Summary of settings"), fontsize=9, loc="left")
    fig.savefig(f"{FIGDIR}/setup.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    mechanism()
    setup()
    print(f"{FIGDIR}/mechanism.png, {FIGDIR}/setup.png written")
