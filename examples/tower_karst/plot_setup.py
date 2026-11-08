#!/usr/bin/env python3
"""examples/tower_karst の機構の模式図と設定の図(計算結果は使わない)。

  python3 plot_setup.py        # figs/mechanism.png, figs/setup.png(基準面つきの入力があれば figs/setup_base.png も)
  python3 plot_setup.py en     # 英語ラベル版を en/figs/ に描く

  figs/mechanism.png  (a) 裸岩の塔と土層に覆われた平野の断面(どこで水がしみ込み、どこが溶けるか)、
                      (b) 平野が下がって塔の比高が増し、裾が堀・ノッチ・崩落で切られていく様子
  figs/setup.png      初期地形(平面と塔 1 を通る横断)、土層厚と浸透能、1 日の降雨、設定の要約
  figs/setup_base.png 基準面と隆起の構成 param_base.txt: 塔 1・2 を通る横断と東端の河道の拡大(管路層、
                      水頭底、地下水面、吐口、隆起)、規則と値、入力の値(平野・裸岩・河道)、4 構成の比較

入力は make_terrain.py が書く z.txt / sd.txt / ksv.txt(make で作る)。setup_base.png は
make_terrain.py --steady --base が書く z_base・gwc_bot・gwc_outfall・uplift・sol_base・ksv_base・
ksv_steady.txt と 4 つの param*.txt を読む(なければ描かない)。
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
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)

C_ROCK, C_SOIL, C_WATER, C_DISS, C_TALUS = "#d6d2c4", "#a0522d", "#2c7fb8", "#c0392b", "#8f8f8f"
HILLS = [(300.0, 300.0, 40.0, 90.0), (700.0, 320.0, 40.0, 90.0), (320.0, 720.0, 40.0, 90.0),
         (690.0, 700.0, 40.0, 90.0), (500.0, 520.0, 20.0, 60.0), (150.0, 850.0, 20.0, 60.0)]


def _arrow(ax, x0, y0, x1, y1, color, lw=1.5, style="-|>", ms=9):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw, shrinkA=0, shrinkB=0, mutation_scale=ms))


def _tower(x, H=40.0, R=90.0, xc=0.0, plain=0.0):
    r = np.abs(x - xc)
    return plain + np.where(r < R, H * np.clip(1.0 - (r / R) ** 2, 0, None) ** 1.5, 0.0)


def _section(ax):
    """塔と平野の断面: 塔の雨は裾へ流れ下り、平野と裾で浸透して溶かす。"""
    x = np.linspace(-200, 200, 801)
    z = _tower(x)
    ax.fill_between(x, -14, z, color=C_ROCK)
    plain = np.abs(x) >= 85
    ax.fill_between(x, z - 1.6, z, where=plain, color=C_SOIL, alpha=0.85)
    ax.plot(x, z, "k-", lw=1.1)
    for xi in np.arange(-195, 200, 22):
        _arrow(ax, xi, 52, xi - 3, 46.5, C_WATER, lw=1.0, ms=7)
    ax.text(-195, 53.5, T("代表豪雨 40 mm/h × 1 時間(1 日周期)", "representative storm 40 mm/h × 1 h (daily)"), fontsize=8.5, color=C_WATER)
    # 塔: 裸岩、浸透能 1 mm/h → 雨は表面流として裾へ
    for sgn in (-1, 1):
        _arrow(ax, sgn * 30, 36, sgn * 70, 12, C_WATER, lw=1.8)
    ax.text(0, 26, T("裸岩の塔: 浸透能 1 mm/h\n雨はほぼ全量が表面流で裾へ\n岩面は流出水の 0.3 倍だけ溶ける",
                     "bare-rock tower: capacity 1 mm/h\nalmost all rain runs off to the foot\nthe rock face dissolves with 0.3 × runoff"),
            ha="center", fontsize=8)
    # 平野: 土層 1 m、40 mm/h で浸透し、攻撃性の高い水が溶かす
    for xi in (-170, -140, 140, 170):
        _arrow(ax, xi, 0.5, xi, -5.0, C_WATER, lw=1.3, ms=8)
    ax.text(-195, -8.5, T("平野: 土層 1 m・浸透能 40 mm/h\nしみ込んだ水(土壌 CO₂)が溶かす",
                          "plain: soil 1 m, capacity 40 mm/h\ninfiltrating water (soil CO₂) dissolves"),
            fontsize=8, color=C_DISS)
    # 裾: 集水して深く溶ける(堀)、湛水が壁を溶かす(ノッチ)、崩落
    for sgn in (-1, 1):
        xs = sgn * 92
        ax.fill_between([xs - 6, xs + 6], [-3.5, -3.5], [0.3, 0.3], color=C_WATER, alpha=0.75)
        _arrow(ax, xs, -1.0, xs, -9.0, C_DISS, lw=1.6)
        _arrow(ax, xs - sgn * 2, -1.0, xs - sgn * 9, -1.0, C_DISS, lw=1.4)
    ax.text(105, -11.5, T("裾: 塔の水が集まって深く溶ける(堀・穴)\n湛水が岩壁を溶かす(ノッチ)",
                          "foot: tower water gathers and\ndissolves deeply (moat, holes);\nponded water dissolves the wall (notch)"),
            fontsize=8, color=C_DISS)
    ax.add_patch(plt.Polygon([(-80, 9.0), (-96, 0.3), (-86, 0.3)], color=C_TALUS))
    ax.text(-128, 14, T("露出した壁が H_c = 10 m を\n超えると崩れて崖錐に", "walls exposed above H_c = 10 m\ncollapse into talus"), fontsize=8)
    ax.set_xlim(-200, 200)
    ax.set_ylim(-14, 57)
    ax.set_xticks([])
    ax.set_yticks([])


def _evolution(ax):
    """平野が下がり、塔の比高が増す(fenglin)。"""
    x = np.linspace(-200, 200, 801)
    z0 = _tower(x)
    z1 = _tower(x, plain=-8.0) + np.where(np.abs(x) < 90, 8.0 - 1.6 * (1 - (np.abs(x) / 90.0)) - 6.4 * (np.abs(x) / 90.0) ** 6, 0.0)
    z1 = np.where((np.abs(x) > 84) & (np.abs(x) < 100), z1 - 5.0 * np.exp(-((np.abs(x) - 92) / 4.0) ** 2), z1)
    ax.fill_between(x, -16, z1, color=C_ROCK)
    ax.plot(x, z0, color="0.4", lw=1.0, ls="--", label=T("初めの地形", "initial terrain"))
    ax.plot(x, z1, "k-", lw=1.2, label=T("後の地形(模式)", "later terrain (schematic)"))
    _arrow(ax, 160, 0.0, 160, -7.5, C_DISS, lw=1.6)
    ax.text(150, -2.5, T("平野は速く下がる", "the plain lowers fast"), fontsize=8, color=C_DISS, ha="right")
    _arrow(ax, 0, 41.5, 0, 40.2, C_DISS, lw=1.2, ms=6)
    ax.text(5, 43.5, T("塔の頂は遅く下がる(平野の 1/3〜1/4)", "the top lowers slowly (1/3 to 1/4 of the plain)"), fontsize=8, color=C_DISS)
    ax.annotate("", xy=(-150, 40), xytext=(-150, -8.0), arrowprops=dict(arrowstyle="<->", color="k", lw=1.0))
    ax.text(-145, 15, T("比高が増す\n(平野に残る塔 = fenglin)", "relative height grows\n(towers on a plain = fenglin)"), fontsize=8)
    ax.legend(fontsize=7.5, loc="upper right")
    ax.set_xlim(-200, 200)
    ax.set_ylim(-16, 48)
    ax.set_xticks([])
    ax.set_yticks([])


def mechanism():
    fig = plt.figure(figsize=(13.5, 9.6))
    gs = fig.add_gridspec(2, 1, height_ratios=[1.2, 0.9], hspace=0.2)
    ax = fig.add_subplot(gs[0])
    _section(ax)
    ax.set_title(T("(a) 塔と平野の断面(模式。縦は誇張): 雨がどこでしみ込み、どこが溶けるか",
                   "(a) Section of a tower and the plain (schematic, vertical exaggeration): where rain soaks in and what dissolves"),
                 loc="left", fontsize=10)
    ax = fig.add_subplot(gs[1])
    _evolution(ax)
    ax.set_title(T("(b) 平野が下がって塔の比高が増し、裾は堀・ノッチ・崩落で切られていく",
                   "(b) The plain lowers, the towers grow in relative height, and their feet are cut by moats, notches and collapse"),
                 loc="left", fontsize=10)
    fig.savefig(f"{FIGDIR}/mechanism.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


def setup():
    z = np.loadtxt("z.txt")
    sd = np.loadtxt("sd.txt")
    ksv = np.loadtxt("ksv.txt")
    ny, nx = z.shape
    dx = 10.0
    ext = [0, nx * dx, 0, ny * dx]
    fig = plt.figure(figsize=(14, 6.8))
    gs = fig.add_gridspec(2, 3, width_ratios=[1.15, 1.25, 1.05], height_ratios=[1, 1], wspace=0.32, hspace=0.5)
    ax = fig.add_subplot(gs[:, 0])
    im = ax.imshow(z, origin="lower", extent=ext, cmap="terrain", vmin=-8, vmax=42)
    ax.contour((np.arange(nx) + 0.5) * dx, (np.arange(ny) + 0.5) * dx, ksv, levels=[20.0], colors="k", linewidths=0.8)
    for k, (xc, yc, H, R) in enumerate(HILLS):
        ax.text(xc, yc, "%d" % (k + 1), ha="center", va="center", fontsize=9, fontweight="bold")
    ax.axhline(305, color="k", lw=0.6, ls="--")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title(T("初期地形と塔の番号\n(黒線の内側 = 裸岩)", "Initial terrain and tower numbers\n(inside the black line = bare rock)"),
                 fontsize=9)
    fig.colorbar(im, ax=ax, shrink=0.6).set_label(T("地盤高 (m)", "elevation (m)"))
    ax = fig.add_subplot(gs[0, 1])
    x = (np.arange(nx) + 0.5) * dx
    j = 30
    ax.fill_between(x, -3, z[j], color=C_ROCK)
    ax.fill_between(x, z[j] - sd[j], z[j], color=C_SOIL, alpha=0.9)
    ax.plot(x, z[j], "k-", lw=1.1)
    ax.set_xlim(0, 1000)
    ax.set_ylim(-3, 44)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("z (m)")
    ax.set_title(T("塔 1・2 を通る横断(y = 305 m)\n茶 = 土層(平野 1 m、裸岩 0.001 m)",
                   "Section through towers 1 and 2 (y = 305 m)\nbrown = soil (plain 1 m, bare rock 0.001 m)"), fontsize=9)
    ax = fig.add_subplot(gs[1, 1])
    t = np.array([0, 1, 1, 24])
    p = np.array([40, 40, 0, 0])
    ax.fill_between(t, 0, p, color="#9ecae1", label=T("降雨 40 mm/h × 1 時間", "rain 40 mm/h × 1 h"))
    ax.axhline(40, color="C1", ls="--", lw=1.2)
    ax.text(4, 41.5, T("平野の浸透能 40 mm/h(全量しみ込む)", "plain capacity 40 mm/h (all soaks in)"), fontsize=8, color="C1")
    ax.axhline(1, color="k", ls="--", lw=1.2)
    ax.text(4, 2.5, T("裸岩の浸透能 1 mm/h(ほぼ全量が表面流)", "bare-rock capacity 1 mm/h (almost all runs off)"), fontsize=8)
    ax.set_xlim(0, 24)
    ax.set_ylim(0, 52)
    ax.set_xlabel(T("時刻 (h)。1 日周期で 60 日繰り返す", "time (h); the day repeats for 60 days"))
    ax.set_ylabel("mm/h")
    ax.legend(fontsize=7.5, loc="upper right")
    ax.set_title(T("1 日の降雨と浸透能", "Rain of one day and infiltration capacities"), fontsize=9)
    ax = fig.add_subplot(gs[:, 2])
    ax.axis("off")
    rows = [
        (T("領域", "domain"), T("1000 × 1000 m、Δx = 10 m、四周は壁", "1000 × 1000 m, Δx = 10 m, closed walls")),
        (T("塔", "towers"), T("1〜4: 高さ 40 m・半径 90 m\n5・6: 高さ 20 m・半径 60 m(釣鐘形)", "1–4: 40 m high, radius 90 m\n5, 6: 20 m high, radius 60 m (bell-shaped)")),
        (T("土層・浸透", "soil"), T("平野 1 m・40 mm/h、裸岩 0.001 m・1 mm/h\n土層の水は管路層へ 20 mm/h で抜ける\n(吸込穴なし)", "plain 1 m, 40 mm/h; bare rock 0.001 m, 1 mm/h\nsoil water drains to the conduit layer\nat 20 mm/h (no sinks)")),
        (T("溶食", "dissolution"), T("c_eq 300 mg/L(k_d = 1.2×10⁻⁴)\n浸透量 + 裸岩の流出水 × 0.3\n残渣率 0.1、側方溶食(自動配分)", "c_eq 300 mg/L (k_d = 1.2×10⁻⁴)\ninfiltration + 0.3 × runoff on bare rock\nresidue 0.1, lateral dissolution (auto)")),
        (T("崩落", "collapse"), T("H_c = 10 m、窓 10 m、崖錐 35°\n基岩も崩す(rf_bedrock = 1)", "H_c = 10 m, window 10 m, talus 35°\nbedrock collapses (rf_bedrock = 1)")),
        (T("時間", "time"), T("dt 2 s、地形更新 10 分 × morfac 5×10³\n1 日 = 5000 豪雨 = 100 年(年 50 回)\n60 日 = 地形時間 6000 年", "dt 2 s, update every 10 min × morfac 5×10³\n1 day = 5000 storms = 100 years (50 a year)\n60 days = landform time 6000 years")),
    ]
    yv = 0.97
    for k, v in rows:
        ax.text(0.0, yv, k, fontsize=9, va="top", color="0.2")
        ax.text(0.29, yv, v, fontsize=9, va="top")
        yv -= 0.08 + 0.055 * v.count("\n")
    ax.set_title(T("設定の要約", "Summary of settings"), fontsize=9, loc="left")
    fig.savefig(f"{FIGDIR}/setup.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ setup_base.png(基準面と隆起の構成)
BASE_INPUTS = ["param.txt", "param_steady.txt", "param_base.txt", "param_base_hc50.txt", "z.txt", "z_base.txt", "sd.txt",
               "ksv.txt", "ksv_steady.txt", "ksv_base.txt", "sol_base.txt", "uplift.txt", "gwc_outfall.txt", "gwc_bot.txt"]
C_COND, C_UP = "#6a51a3", "#238b45"
ZROCK = 5.0                                # make_terrain.py: これより高いセルが裸岩
STORMS_PER_YR = 50.0                       # make_terrain.py・README の換算(代表豪雨は年 50 回)


def read_param(fn):
    """key = value(! 以降はコメント)と prval(1:2,n) = 時刻 (min), 強度 (mm/h) を読む。"""
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


def _days(s):
    """"60d"・"1d" などの時間文字列を日に。"""
    m = re.match(r"([0-9.]+)\s*([dhms]?)", s)
    return float(m.group(1)) * {"d": 1.0, "h": 1 / 24.0, "m": 1 / 1440.0, "s": 1 / 86400.0, "": 1 / 86400.0}[m.group(2)]


def _sci(v):
    """6e6 → 6×10⁶"""
    e = int(np.floor(np.log10(abs(v))))
    sup = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")
    return "%g×10%s" % (round(v / 10.0 ** e, 2), str(e).translate(sup))


def _num(v):
    """負号を − にした %g"""
    return ("%g" % v).replace("-", "−")


def _config(fn, rock, river):
    """4 構成の比較表の 1 列(値は param*.txt と生成入力から)。"""
    p = read_param(fn)
    days = _days(p["tt_c"])
    morfac = float(p["morfac"])
    if "t_cycle_c" in p:
        rain = T("豪雨 %g mm/h × %g 時間を\n%g 日周期で反復" % (p["prval"][0][1], (p["prval"][2][0] - p["prval"][0][0]) / 60, _days(p["t_cycle_c"])),
                 "storm %g mm/h × %g h\nrepeated %s" % (p["prval"][0][1], (p["prval"][2][0] - p["prval"][0][0]) / 60,
                                                          "daily" if _days(p["t_cycle_c"]) == 1 else "every %g days" % _days(p["t_cycle_c"])))
        tyr = days * morfac / STORMS_PER_YR
        tland = T("%.0f 年(1 日 = 豪雨 1 回、\n年 %g 回で換算)" % (tyr, STORMS_PER_YR), "%.0f years (1 day = 1 storm,\n%g storms a year)" % (tyr, STORMS_PER_YR))
    else:
        r = p["prval"][0][1]
        rain = T("%g mm/h の定常\n(年 ≈ %.0f mm)" % (r, round(r * 8766.0, -1)), "steady %g mm/h\n(≈ %.0f mm a year)" % (r, round(r * 8766.0, -1)))
        tyr = days * morfac / 365.25
        tland = T("%s 年(%.2f Myr)" % (format(int(round(tyr)), ",").replace(",", " "), tyr / 1e6),
                  "%s years (%.2f Myr)" % (format(int(round(tyr)), ","), tyr / 1e6))
    ksv = np.loadtxt(p["fn_gw_ksv"])
    krock = np.unique(ksv[rock])
    kriv = np.unique(ksv[river])
    kr = T("%g mm/h" % krock[0], "%g mm/h" % krock[0])
    if kriv.size == 1 and kriv[0] == 0.0:
        kr += T("(河道 0)", " (river 0)")
    if "fn_gwc_outfall" in p:
        zriv = np.unique(np.loadtxt(p["fn_z"])[river])[0]
        ca = np.unique(np.loadtxt(p["fn_gwc_outfall"])[river])[0]
        zbot = np.unique(np.loadtxt(p["fn_gwc_bot"]))[0]
        h0 = zbot + float(p["gwc_sat0"]) * float(p["gwc_cap"]) / float(p["gwc_sy"])
        base = T("東端の河道 z = %s m・吐口\nCd·A %g m²・水頭底 %s m\n(地下水面 %s m から)" % (_num(zriv), ca, _num(zbot), _num(h0)),
                 "river column z = %s m, outfall\nCd·A %g m², head floor %s m\n(water table from %s m)" % (_num(zriv), ca, _num(zbot), _num(h0)))
    else:
        base = T("なし(管路層は深さ %g m の\n受け皿、四周は壁)" % float(p["gwc_depth"]),
                 "none (conduit layer = a sink\n%g m deep; closed walls)" % float(p["gwc_depth"]))
    if int(p.get("f_uplift", "0")) > 0:
        up = T("%g mm/yr(河道の列 0)" % float(p["uplift0"]), "%g mm/yr (river column 0)" % float(p["uplift0"]))
    else:
        up = T("なし", "none")
    src = int(p["dissol_src"])
    fs = float(p["dissol_fsurf"])
    dsrc = {3: T("3: 浸透量 + %g × 裸岩の流出" % fs, "3: infiltration + %g × runoff" % fs),
            5: T("5: 涵養 + %g × 裸岩の流出" % fs, "5: recharge + %g × runoff" % fs)}.get(src, "%d" % src)
    return [rain, kr, _sci(morfac), tland, base, up, "%g m" % float(p["rf_hc"]), dsrc]


def _base_values(p, zb, plain, rock, river):
    """param_base.txt と生成入力から、図に書く値をまとめる。"""
    def one(fn, m):
        u = np.unique(np.loadtxt(fn)[m])
        return float(u[0]) if u.size == 1 else float("nan")
    b = dict(rain=p["prval"][0][1], kleak=float(p["gwc_leak_mmh"]), sy0=float(p["sy0"]), cnd=float(p["gwc_cnd_m2s"]), law=int(p["f_gwc_fluxlaw"]),
             cap=float(p["gwc_cap"]), sat0=float(p["gwc_sat0"]), sy=float(p["gwc_sy"]), up=float(p["uplift0"]),
             ceq=float(p["dissol_ceq"]), rho=float(p["dissol_rho"]), fres=float(p["dissol_fres"]), fsurf=float(p["dissol_fsurf"]),
             sdsurf=float(p["dissol_sdsurf"]), src=int(p["dissol_src"]), fbc=int(p["f_bc_e"]))
    b["kp"], b["kr"], b["kv"] = (one(p["fn_gw_ksv"], m) for m in (plain, rock, river))
    b["sdp"], b["sdr"] = one(p["fn_sd"], plain), one(p["fn_sd"], rock)
    b["zbot"] = float(np.unique(np.loadtxt(p["fn_gwc_bot"]))[0])
    b["h0"] = b["zbot"] + b["sat0"] * b["cap"] / b["sy"]
    b["zriv"] = float(np.unique(zb[river])[0])
    b["ca"] = one(p["fn_gwc_outfall"], river)
    b["upl"], b["upv"] = one(p["fn_uplift"], ~river), one(p["fn_uplift"], river)
    b["fsl"], b["fsv"] = one(p["fn_dissol"], ~river), one(p["fn_dissol"], river)
    b["kd"] = b["ceq"] * 1.0e-3 / b["rho"]                       # init_dissol と同じ式
    b["fi"] = min(b["kr"], b["rain"]) / b["rain"]               # 裸岩でしみ込む雨の割合
    b["fbr"] = max(0.0, 1.0 - b["sdr"] / b["sdsurf"])
    b["fbp"] = max(0.0, 1.0 - b["sdp"] / b["sdsurf"])
    pann = b["rain"] * 365.25 * 24.0 / 1000.0                   # m/yr
    b["lp"] = (1.0 - b["fres"]) * b["kd"] * pann * 1e3          # 平野の地表の低下 (m/kyr)。R ≈ 雨
    b["lr"] = (1.0 - b["fres"]) * b["kd"] * pann * (b["fi"] + b["fsurf"] * b["fbr"] * (1.0 - b["fi"])) * 1e3
    return b


def _base_section(ax, b, zb, sd, j, dx):
    """param_base.txt の横断(塔 1・2 を通る y = 305 m)。管路層は水頭 H = z_b + h_gc/s_y で描く。"""
    nx = zb.shape[1]
    xs = np.repeat(np.arange(nx + 1) * dx, 2)[1:-1]
    zs = np.repeat(zb[j], 2)
    ss = np.repeat(sd[j], 2)
    zlo = b["zbot"] - 8.0
    ax.fill_between(xs, zlo, zs - ss, color=C_ROCK)
    ax.fill_between(xs, zs - ss, zs, color=C_SOIL, alpha=0.9)
    ax.plot(xs, zs, "k-", lw=1.0)
    ax.fill_between([0, nx * dx], [b["zbot"]] * 2, [b["h0"]] * 2, color=C_COND, alpha=0.22, lw=0)
    ax.plot([0, nx * dx], [b["zbot"]] * 2, color=C_COND, lw=1.6)
    ax.plot([0, nx * dx], [b["h0"]] * 2, color=C_WATER, lw=1.3, ls="--")
    for xi in np.arange(15, 1000, 40.0):
        _arrow(ax, xi, 51.0, xi - 3, 46.5, C_WATER, lw=0.9, ms=6)
    ax.text(8, 52.5, T("雨 %g mm/h(定常)" % b["rain"], "rain %g mm/h (steady)" % b["rain"]), fontsize=8.5, color=C_WATER)
    ax.text(10, 33, T("平野: 土層 %g m、浸透能 %g mm/h\n→ 雨は全量しみ込む" % (b["sdp"], b["kp"]),
                      "plain: soil %g m, capacity %g mm/h\n→ all rain soaks in" % (b["sdp"], b["kp"])), fontsize=8.5)
    ax.text(500, 33, T("裸岩の塔: 浸透能 %g mm/h\n(雨の %.1f %%)。残りは裾へ流れ、\nその %g 倍が岩面を溶かす" % (b["kr"], 100 * b["fi"], b["fsurf"]),
                       "bare-rock towers: %g mm/h\n(%.1f %% of the rain); the rest runs\noff, %g × of it dissolves the face" % (b["kr"], 100 * b["fi"], b["fsurf"])),
            fontsize=8.5, ha="center")
    for xi in (110.0, 470.0, 880.0):
        _arrow(ax, xi, -1.6, xi, b["h0"] - 6.0, C_COND, lw=1.6, ms=9)
    ax.text(124, b["h0"] - 7.6, T("土層 → 管路層の交換 R(≤ %g mm/h。土層の水頭が H より高いときだけ)= 溶食の水量" % b["kleak"],
                                  "soil → conduit exchange R (≤ %g mm/h; only while the soil head is above H) = water of dissolution" % b["kleak"]),
            fontsize=8.5, color=C_COND, va="top")
    _arrow(ax, 560, -24.0, 930, -24.0, C_COND, lw=2.0, ms=11)
    ax.text(560, -22.6, T("管路層の側方通水(線形則)→ 吐口へ", "lateral flow in the conduit layer (linear law) → outfall"),
            fontsize=8.5, color=C_COND)
    for xi in (40.0, 470.0, 700.0):
        _arrow(ax, xi, b["zbot"] + 3.0, xi, b["zbot"] + 14.0, C_UP, lw=2.6, ms=12)
    ax.text(56, b["zbot"] + 4.5, T("隆起 %g mm/yr(陸の z と基岩をそのまま上げる)" % b["up"],
                                   "uplift %g mm/yr (raises the land z and its bedrock)" % b["up"]), fontsize=8.5, color=C_UP)
    ax.text(130, b["h0"] - 0.8, T("初期の地下水面 H = %s m" % _num(b["h0"]), "initial water table H = %s m" % _num(b["h0"])),
            fontsize=8.5, color=C_WATER, va="top")
    ax.text(990, b["zbot"] - 1.6, T("水頭底 z_b = %s m(gwc_bot.txt。絶対標高。隆起しても動かない)" % _num(b["zbot"]),
                                    "head floor z_b = %s m (gwc_bot.txt; absolute, does not move with uplift)" % _num(b["zbot"])),
            fontsize=8.5, color=C_COND, ha="right", va="top")
    ax.add_patch(plt.Rectangle((930, -15.5), 70, 20.0, fill=False, ec="k", lw=0.9, ls=":"))
    ax.text(928, 5.6, T("拡大 →", "enlarged →"), fontsize=8, ha="right")
    ax.set_xlim(0, nx * dx)
    ax.set_ylim(zlo, 56)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("z (m)")


def _base_zoom(ax, b, zb, sd, j, dx):
    """東端の河道の列の拡大: 吐口(フラップ)と東の辺の自由流出。"""
    nx = zb.shape[1]
    i0 = nx - 7
    xe = nx * dx
    xs = np.repeat(np.arange(i0, nx + 1) * dx, 2)[1:-1]
    zs = np.repeat(zb[j, i0:], 2)
    ss = np.repeat(sd[j, i0:], 2)
    zlo, zhi = -15.5, 4.5
    ax.fill_between(xs, zlo, zs - ss, color=C_ROCK)
    ax.fill_between(xs, zs - ss, zs, color=C_SOIL, alpha=0.9)
    ax.plot(xs, zs, "k-", lw=1.0)
    ax.fill_between([i0 * dx, xe], [zlo, zlo], [b["h0"]] * 2, color=C_COND, alpha=0.22, lw=0)
    ax.plot([i0 * dx, xe], [b["h0"]] * 2, color=C_WATER, lw=1.3, ls="--")
    ax.add_patch(plt.Rectangle((xe, zlo), 60, zhi - zlo, fc="0.93", ec="none"))
    xr = xe - 0.5 * dx
    ax.fill_between([xe - dx, xe], [b["zriv"]] * 2, [b["zriv"] + 0.35] * 2, color=C_WATER, alpha=0.8)
    _arrow(ax, xr, -12.8, xr, b["zriv"] - 0.2, C_COND, lw=2.2, ms=11)
    _arrow(ax, xr, b["zriv"] + 0.6, xe + 9, b["zriv"] + 0.6, C_WATER, lw=2.0, ms=10)
    ax.plot([xe, xe], [zlo, zhi], color="k", lw=1.2)
    ax.text(xe + 1.5, b["zriv"] + 1.4, T("東の辺:\n自由流出\n(f_bc_e\n= %d)\n→ 域外へ" % b["fbc"], "east edge:\nfree\noutflow\n(f_bc_e\n= %d)" % b["fbc"]),
            fontsize=7.8, va="bottom")
    ax.text(xe - dx - 0.5, b["zriv"] + 0.2, "h", fontsize=8, color=C_WATER, ha="right")
    ax.text(i0 * dx + 1.0, -14.9, T("吐口: Q = Cd·A √(2g (H − z − h))\nCd·A = %g m²(gwc_outfall.txt)\nH > z + h のときだけ\n放流する(フラップ)" % b["ca"],
                                    "outfall: Q = Cd·A √(2g (H − z − h))\nCd·A = %g m² (gwc_outfall.txt);\ndischarges only while\nH > z + h (flap)" % b["ca"]),
            fontsize=7.8, color=C_COND, va="bottom",
            bbox=dict(boxstyle="square,pad=0.15", fc="w", ec="none", alpha=0.85))
    ax.text(i0 * dx + 1.0, zhi - 0.4, T("河道の列(x = %g〜%g m)\nz = %s m、可溶率 %g、浸透能 %g、\n隆起の倍率 %g"
                                        % (xe - dx, xe, _num(b["zriv"]), b["fsv"], b["kv"], b["upv"]),
                                        "river column (x = %g–%g m):\nz = %s m; soluble fraction %g,\ncapacity %g, uplift multiplier %g"
                                        % (xe - dx, xe, _num(b["zriv"]), b["fsv"], b["kv"], b["upv"])),
            fontsize=7.8, va="top")
    ax.text(i0 * dx + 1.0, b["h0"] - 0.3, "H", fontsize=8.5, color=C_WATER, va="top")
    ax.set_xlim(i0 * dx, xe + 22)
    ax.set_ylim(zlo, zhi)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("z (m)")


def _base_rules(ax, b):
    ax.axis("off")
    lines = [
        (T("交換(gwc_leak_layer = 1): 土層の水頭 (z − sd) + h_g/sy0 が H より高いとき R = min(k_l Δt, h_g)、k_l = %g mm/h。"
           % b["kleak"],
           "Exchange (gwc_leak_layer = 1): R = min(k_l Δt, h_g) while the soil head (z − sd) + h_g/sy0 is above H; k_l = %g mm/h."
           % b["kleak"]), False),
        (T("     H の方が高いと向きが逆になり、管路層の水が土層へ移る(土層の容量 sd·sy0 まで。sy0 = %g)" % b["sy0"],
           "     When H is higher the exchange reverses and conduit water moves into the soil (up to its capacity sd·sy0; sy0 = %g)"
           % b["sy0"]), False),
        (T("管路層の水頭: H = z_b + h_gc/gwc_sy(gwc_sy = %g)。初期 h_gc = %g × %g m = %g m(gwc_sat0 × gwc_cap)→ H = %s m"
           % (b["sy"], b["sat0"], b["cap"], b["sat0"] * b["cap"], _num(b["h0"])),
           "Conduit head: H = z_b + h_gc/gwc_sy (gwc_sy = %g). Initial h_gc = %g × %g m = %g m (gwc_sat0 × gwc_cap) → H = %s m"
           % (b["sy"], b["sat0"], b["cap"], b["sat0"] * b["cap"], _num(b["h0"]))), False),
        (T("側方通水(f_gwc_fluxlaw = %d、線形則): q = C · f_e · ΔH/Δs、C = %g m²/s(gwc_cnd_m2s。満管時の値)、"
           % (b["law"], b["cnd"]),
           "Lateral flow (f_gwc_fluxlaw = %d, linear law): q = C · f_e · ΔH/Δs, C = %g m²/s (gwc_cnd_m2s; value for a full layer),"
           % (b["law"], b["cnd"])), False),
        (T("     f_e = 充満率 min(h_gc/cap, 1)(初期 %g → 実効 %s m²/s)" % (b["sat0"], _sci(b["cnd"] * b["sat0"])),
           "     f_e = fill ratio min(h_gc/cap, 1) (initially %g → effectively %s m²/s)" % (b["sat0"], _sci(b["cnd"] * b["sat0"]))), False),
        (T("吐口(陸側): Q = Cd·A √(2g (H − (z + h)))、Cd·A = %g m²。H > z + h のときだけ河道の地表へ出し、東の辺から域外へ" % b["ca"],
           "Outfall (land side): Q = Cd·A √(2g (H − (z + h))), Cd·A = %g m², only while H > z + h; to the river surface, out at the east edge"
           % b["ca"]), False),
        (T("隆起: z += U · m · Δt、U = %g mm/yr、m = uplift.txt(陸 %g、河道 %g)。sd は不変。z_b と河道は動かない"
           % (b["up"], b["upl"], b["upv"]),
           "Uplift: z += U · m · Δt, U = %g mm/yr, m = uplift.txt (land %g, river %g); sd unchanged; z_b and the river stay"
           % (b["up"], b["upl"], b["upv"])), False),
        (T("溶食(dissol_src = %d): w = k_d · f_sol · morfac · [R + f_surf · f_b · max(P − R, 0)]、k_d = c_eq/ρ_r = %s、"
           % (b["src"], _sci(b["kd"])),
           "Dissolution (dissol_src = %d): w = k_d · f_sol · morfac · [R + f_surf · f_b · max(P − R, 0)], k_d = c_eq/ρ_r = %s,"
           % (b["src"], _sci(b["kd"]))), False),
        (T("     f_surf = %g、f_b = max(0, 1 − sd/%g m)(裸岩 %g、平野 %g)、f_sol = sol_base.txt(陸 %g、河道 %g)"
           % (b["fsurf"], b["sdsurf"], b["fbr"], b["fbp"], b["fsl"], b["fsv"]),
           "     f_surf = %g, f_b = max(0, 1 − sd/%g m) (bare rock %g, plain %g), f_sol = sol_base.txt (land %g, river %g)"
           % (b["fsurf"], b["sdsurf"], b["fbr"], b["fbp"], b["fsl"], b["fsv"])), False),
        (T("     初めの地表の低下 (1 − f_res) w の見積もり(式から): 平野 R ≈ P → %.2f m/kyr、裸岩 R ≈ %.3f P → %.2f m/kyr。隆起は %.2f m/kyr"
           % (b["lp"], b["fi"], b["lr"], b["up"]),
           "     Initial surface lowering (1 − f_res) w from the formula: plain R ≈ P → %.2f m/kyr, bare rock R ≈ %.3f P → %.2f m/kyr;"
           " uplift %.2f m/kyr" % (b["lp"], b["fi"], b["lr"], b["up"])), False),
        (T("     R は土層の水頭が H より高い間だけ流れる。基岩面が地下水面より下でも、土層の水頭が高ければ溶食は続く",
           "     R flows only while the soil head is above H; below the water table dissolution goes on if the soil head is higher"), True),
    ]
    y = 1.0
    for s, warn in lines:
        ax.text(0.0, y, s, fontsize=8.5, va="top", color=C_DISS if warn else "k", transform=ax.transAxes)
        y -= 0.091


def _grid_table(ax, header, rows, colw, hl=None, fs=8.3, rowh=None):
    """罫線つきの表(ax の軸座標 0..1 に描く)。hl[i][k] が真のセルは色付き。"""
    ax.axis("off")
    ncol = len(header)
    xe = np.concatenate([[0.0], np.cumsum(colw)]) / np.sum(colw)
    nl = [max(s.count("\n") + 1 for s in r) for r in rows]
    hh = max(s.count("\n") + 1 for s in header)
    unit = 1.0 / (hh + sum(nl) + 0.6 * (len(rows) + 1)) if rowh is None else rowh
    y = 1.0
    hgt = (hh + 0.6) * unit
    ax.add_patch(plt.Rectangle((0, y - hgt), 1, hgt, fc="0.9", ec="none", transform=ax.transAxes))
    for k in range(ncol):
        ax.text(xe[k] + 0.008, y - hgt / 2, header[k], fontsize=fs, va="center", transform=ax.transAxes)
    y -= hgt
    for i, r in enumerate(rows):
        hgt = (nl[i] + 0.6) * unit
        for k in range(ncol):
            if hl is not None and hl[i][k]:
                ax.add_patch(plt.Rectangle((xe[k], y - hgt), xe[k + 1] - xe[k], hgt, fc="#fff2b3", ec="none",
                                           transform=ax.transAxes))
            ax.text(xe[k] + 0.008, y - hgt / 2, r[k], fontsize=fs, va="center", transform=ax.transAxes)
        ax.plot([0, 1], [y, y], color="0.75", lw=0.6, transform=ax.transAxes)
        y -= hgt
    ax.plot([0, 1], [y, y], color="0.75", lw=0.6, transform=ax.transAxes)


def setup_base():
    # この図は比例幅の IPAPGothic を優先して描く(mechanism・setup はモジュール冒頭のフォント設定のまま)
    with plt.rc_context({"font.family": ["DejaVu Sans"] if EN else ["IPAPGothic", "IPAGothic", "DejaVu Sans"]}):
        pb = read_param("param_base.txt")
        z = np.loadtxt("z.txt")
        zb = np.loadtxt(pb["fn_z"])
        sd = np.loadtxt(pb["fn_sd"])
        dx = float(pb["lx"]) / int(pb["nx"])
        rock = z > ZROCK
        river = np.zeros_like(rock)
        river[:, -1] = True
        plain = ~rock & ~river
        j = 30                                     # 塔 1・2 を通る y = 305 m(setup.png と同じ横断)
        b = _base_values(pb, zb, plain, rock, river)
        fig = plt.figure(figsize=(15, 12.2))
        gs = fig.add_gridspec(3, 2, width_ratios=[3.0, 1.0], height_ratios=[1.25, 0.95, 0.95], hspace=0.3, wspace=0.13)
        ax = fig.add_subplot(gs[0, 0])
        _base_section(ax, b, zb, sd, j, dx)
        ax.set_title(T("(a) param_base.txt の横断(塔 1・2 を通る y = 305 m。入力 z_base.txt・sd.txt から。縦は誇張)",
                       "(a) Section of param_base.txt (y = 305 m through towers 1 and 2; from z_base.txt and sd.txt; vertical exaggeration)"),
                     loc="left", fontsize=10)
        ax = fig.add_subplot(gs[0, 1])
        _base_zoom(ax, b, zb, sd, j, dx)
        ax.set_title(T("(b) 東端の河道の列(拡大)", "(b) River column at the east edge (enlarged)"), loc="left", fontsize=10)
        ax = fig.add_subplot(gs[1, 0])
        _base_rules(ax, b)
        ax.set_title(T("(c) 規則と値(param_base.txt と src の式)", "(c) Rules and values (param_base.txt and the formulas in src)"),
                     loc="left", fontsize=10)
        ax = fig.add_subplot(gs[1, 1])
        files = [("z_base.txt", T("地盤高 (m)", "elevation (m)")), ("sd.txt", T("土層厚 (m)", "soil (m)")),
                 ("ksv_base.txt", T("浸透能 (mm/h)", "capacity (mm/h)")), ("sol_base.txt", T("可溶率", "soluble fraction")),
                 ("uplift.txt", T("隆起の倍率", "uplift multiplier")), ("gwc_outfall.txt", T("吐口 Cd·A (m²)", "outfall Cd·A (m²)")),
                 ("gwc_bot.txt", T("水頭底 (m)", "head floor (m)"))]
        rows = []
        for fn, lab in files:
            a = np.loadtxt(fn)
            cells = []
            for m in (plain, rock, river):
                u = np.unique(a[m])
                cells.append(_num(u[0]) if u.size == 1 else "%s%s%s" % (_num(round(u.min(), 1)), T("〜", "–"), _num(round(u.max(), 1))))
            rows.append(["%s\n%s" % (fn, lab)] + cells)
        _grid_table(ax, [T("入力", "input"), T("平野", "plain"), T("裸岩", "bare rock"), T("河道の列", "river")], rows,
                    [1.75, 0.9, 0.9, 0.75], fs=8.0)
        ax.set_title(T("(d) 入力の値(make_terrain.py --steady --base)", "(d) Input values (make_terrain.py --steady --base)"),
                     loc="left", fontsize=10)
        ax = fig.add_subplot(gs[2, :])
        names = ["param.txt", "param_steady.txt", "param_base.txt", "param_base_hc50.txt"]
        labels = [T("主ケース", "main case"), T("準定常強制", "quasi-steady forcing"), T("基準面と隆起", "base level and uplift"),
                  T("感度: rf_hc = 50 m", "sensitivity: rf_hc = 50 m")]
        cols = [_config(fn, rock, river) for fn in names]
        items = [T("降雨", "rain"), T("裸岩の浸透能", "bare-rock capacity"), "morfac", T("地形時間(60 日)", "landform time (60 days)"),
                 T("基準面", "base level"), T("隆起", "uplift"), "rf_hc", "dissol_src"]
        rows = [[items[i]] + [c[i] for c in cols] for i in range(len(items))]
        hl = [[False] + [k > 0 and cols[k][i] != cols[k - 1][i] for k in range(4)] for i in range(len(items))]
        _grid_table(ax, [""] + ["%s\n%s" % (n, l) for n, l in zip(names, labels)], rows, [0.85, 1.25, 1.25, 1.45, 1.45], hl=hl,
                    fs=8.3)
        ax.set_title(T("(e) 4 つの構成の比較(値は param*.txt から。色付き = 左の構成から変えた値)",
                       "(e) The four configurations (values from param*.txt; shaded = changed from the configuration to the left)"),
                     loc="left", fontsize=10)
        fig.savefig(f"{FIGDIR}/setup_base.png", dpi=105, bbox_inches="tight")
        plt.close(fig)


if __name__ == "__main__":
    mechanism()
    setup()
    print(f"{FIGDIR}/mechanism.png, {FIGDIR}/setup.png written")
    if all(os.path.exists(f) for f in BASE_INPUTS):
        setup_base()
        print(f"{FIGDIR}/setup_base.png written")
    else:
        print("setup_base.png not drawn: run python3 make_terrain.py --steady --base first")
