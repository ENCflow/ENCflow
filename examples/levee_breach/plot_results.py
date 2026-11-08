#!/usr/bin/env python3
"""levee_breach の図と数表(事前に make run で 4 ケースを計算しておく)。

  figs/mechanism.png 越水から破堤・氾濫・家屋の流失までの模式図(データを使わない)
  figs/setup.png     地形と天端の低い区間・住宅地・二線堤(平面)、破堤口の横断、洪水と破堤の時刻
  figs/laws.png      与えた破堤の進み方、家屋の空隙率、家屋の破壊と瓦礫の則(入力と param.txt の値だけ。
                     計算結果を使わない)
  figs/maps.png      4 ケースの最大浸水深と家屋の流失
  figs/series.png    堤内地へ入る流量、破堤口より下流の川の流量、住宅地の浸水深の時間変化
引数 en で英語ラベル版を en/figs/ に描く(データと描画処理は共通)。
"""
import glob
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)

NX, NY, DX = 175, 200, 10.0
I_LEV2, J_LOW1, J_LOW2, J_DIKE = 15, 53, 67, 155         # make_terrain.py と同じ
BLOCKS = {"A": (17, 36, 50, 70), "B": (40, 80, 115, 140), "C": (40, 80, 170, 195)}
EXT = [0, NX * DX, NY * DX, 0]                           # 行 1 = 北を上に
CASES = [("overtop", T("越水だけ", "overtopping only"), "#8a8983", ":"),
         ("breach", T("越水で破堤", "breach by overtopping"), "#c0392b", "-"),
         ("delay", T("破堤が 1 時間遅れる", "breach 1 hour later"), "#e08214", "--"),
         ("dike", T("破堤+二線堤", "breach + secondary levee"), "#1f5f8b", "-.")]
T_BREACH = {"breach": (180, 240), "delay": (240, 300), "dike": (180, 240)}
C_GROUND, C_WATER, C_LEVEE, C_HOUSE = "#d9c7a0", "#2a78d6", "#555555", "#8c564b"
CM, DD_MIN = 2.0, 0.001          # 家屋の付加質量係数 cm・移動限界水深 dd(param.txt になく src/list_sysparam.f90 の既定)


def rd(path):
    return np.loadtxt(path)


def flux(case, n):
    """フラックス測線 n の時刻(分)と流量 (m3/s)。"""
    a = np.loadtxt(f"result_{case}/fluxes/flux{n:04d}.csv", delimiter=",", comments="#")
    return a[:, 1], a[:, 2]


def probe(case, n):
    """プローブ n の時刻(分)・地盤高・水深。"""
    a = np.loadtxt(f"result_{case}/probes/probe{n:04d}.csv", delimiter=",", comments="#")
    return a[:, 1], a[:, 2], a[:, 3]


def last_frame(case, var):
    ks = sorted(int(f[-8:-4]) for f in glob.glob(f"result_{case}/{var}0*.txt"))
    return rd(f"result_{case}/{var}{ks[-1]:04d}.txt")


def inflow_series():
    """param.txt の流入波形(分、m3/s)。"""
    ts, qs = [], []
    for line in open("param.txt", encoding="utf-8"):
        if line.strip().startswith("inflow_val"):
            v = line.split("=")[1].split("!")[0].split(",")
            ts.append(float(v[0]))
            qs.append(float(v[1]))
    return np.array(ts), np.array(qs)


# ---------------------------------------------------------------- 模式図
def _levee(ax, x0, stage, title, stage_n):
    """堤防の横断(左 = 川、右 = 堤内地)。stage_n = 0: 越水の始まり、1: 裏法の侵食、2: 破堤。"""
    G, CR = 2.0, 6.0                                           # 堤内地の地盤高、天端
    bed = [(0, -0.4), (0, 0.0), (3.0, 0.0), (3.0, G)]
    if stage_n < 2:
        levee = [(3.0, G), (4.3, CR), (5.3, CR)]
        if stage_n == 0:
            levee += [(7.3, G)]
        else:
            levee += [(5.8, 4.9), (6.2, 3.3), (6.7, 2.3), (7.2, 1.4), (7.9, 1.6), (8.3, G)]
    else:
        levee = [(3.0, G), (3.4, 2.9), (3.6, 1.6), (6.3, 1.4), (7.3, 1.8), (8.3, G)]
    land = [(10.0, G), (10.0, -0.4)]
    poly = bed + levee + land
    ax.add_patch(plt.Polygon([(x + x0, y) for x, y in poly], closed=True, color=C_GROUND))
    if stage_n < 2:
        wl = stage
        xr = 3.0 + (wl - G) / (CR - G) * 1.3                    # 川表の法面と水面の交点
        ax.add_patch(plt.Polygon([(x0, 0.0), (x0 + 3.0, 0.0), (x0 + 3.0, G), (x0 + xr, wl), (x0, wl)], color=C_WATER, alpha=0.55))
        # 天端と裏法を流れる薄い越流
        top = [(4.3, CR), (5.3, CR)] + levee[3:]
        xs = [x for x, y in [(xr, wl)] + top]
        ys = [y + 0.18 for x, y in [(xr, wl - 0.18)] + top]
        ax.plot([x + x0 for x in xs], ys, color=C_WATER, lw=2.2)
        ax.annotate("", xy=(x0 + 9.4, G + 0.15), xytext=(x0 + 8.0, G + 0.15), arrowprops=dict(arrowstyle="-|>", color=C_WATER, lw=1.6))
    else:
        ax.add_patch(plt.Polygon([(x0, 0.0), (x0 + 3.0, 0.0), (x0 + 3.0, G), (x0 + 3.4, 2.9), (x0 + 3.6, 1.6), (x0 + 6.3, 1.4),
                                  (x0 + 7.3, 1.8), (x0 + 8.3, G), (x0 + 10.0, G), (x0 + 10.0, G + 0.9), (x0 + 6.0, 3.3),
                                  (x0 + 3.6, 5.0), (x0, 5.2)], color=C_WATER, alpha=0.55))
        ax.annotate("", xy=(x0 + 9.6, G + 0.55), xytext=(x0 + 2.0, 4.6), arrowprops=dict(arrowstyle="-|>", color=C_WATER, lw=3))
    ax.text(x0 + 5.0, 7.3, title, ha="center", fontsize=9)


def mechanism():
    fig = plt.figure(figsize=(13, 8.4))
    gs = fig.add_gridspec(2, 1, height_ratios=[1, 1.35])
    ax = fig.add_subplot(gs[0])
    _levee(ax, 0, 6.2, T("① 洪水の水位が天端の低い所を越える", "① the flood rises over the low crest"), 0)
    _levee(ax, 11, 6.2, T("② 越水が裏法(堤内地側の斜面)を削る", "② overtopping erodes the landside slope"), 1)
    _levee(ax, 22, 6.2, T("③ 堤体が崩れて破堤し、口が広がる", "③ the levee fails and the opening widens"), 2)
    for xs in (0, 11, 22):
        ax.text(xs + 1.4, 0.6, T("川", "river"), color="w", fontsize=9, ha="center")
        ax.text(xs + 9.0, 0.9, T("堤内地", "landside"), fontsize=9, ha="center")
    ax.set_xlim(-0.3, 32.3)
    ax.set_ylim(-0.5, 8.0)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(T("(a) 越水から破堤まで(堤防の横断)", "(a) From overtopping to breach (cross-section of the levee)"), fontsize=10, loc="left")
    ax = fig.add_subplot(gs[1])
    ax.add_patch(plt.Rectangle((0, 0), 1.6, 10, color=C_WATER, alpha=0.5))
    ax.add_patch(plt.Rectangle((1.6, 0), 0.25, 10, color=C_LEVEE))
    ax.add_patch(plt.Rectangle((1.6, 6.0), 0.25, 1.5, color="w"))
    ax.annotate("", xy=(0.8, 1.0), xytext=(0.8, 9.0), arrowprops=dict(arrowstyle="-|>", color="w", lw=2))
    ax.text(0.45, 5.0, T("川(下流へ)", "river (downstream)"), ha="center", fontsize=8, rotation=90, va="center", color="w")
    for k, (dx_, dy_) in enumerate(((2.2, 0.0), (1.6, -1.6), (2.0, -3.0), (0.8, -3.6))):
        ax.annotate("", xy=(1.9 + dx_, 6.75 + dy_), xytext=(1.9, 6.75), arrowprops=dict(arrowstyle="-|>", color=C_WATER, lw=2.5 - 0.4 * k))
    ax.add_patch(plt.Rectangle((2.0, 6.0), 1.0, 1.5, facecolor="none", edgecolor=C_HOUSE, hatch="xx", lw=1))
    ax.text(3.1, 7.6, T("破堤口の近く: 速い氾濫流が家屋を押し流す", "near the breach: fast flow sweeps houses away"), fontsize=8, color=C_HOUSE)
    ax.add_patch(plt.Rectangle((4.2, 2.8), 1.6, 1.4, facecolor="none", edgecolor=C_HOUSE, hatch="..", lw=1))
    ax.text(5.9, 3.5, T("離れた所: 流れは遅く、浸水する(床上・床下)", "farther away: slow flow, houses are flooded"), fontsize=8, color=C_HOUSE)
    ax.fill_between([1.85, 9.5], 1.55, 1.75, color=C_LEVEE)
    ax.text(6.5, 1.0, T("二線堤・盛土道路: 氾濫水を止め、手前を深くし、背後を守る", "secondary levee or road embankment: holds the water, deepens it in front, protects behind"), fontsize=8, ha="center")
    ax.text(1.0 + 0.9, 5.2, T("破堤口", "breach"), fontsize=8, rotation=90, color="k")
    ax.text(5.5, 9.3, T("氾濫水は地面の傾きに沿って下流へ広がる", "the flood spreads downslope"), fontsize=8, color=C_WATER)
    ax.annotate("", xy=(8.0, 4.8), xytext=(6.0, 8.6), arrowprops=dict(arrowstyle="-|>", color=C_WATER, lw=1.2, ls="--"))
    ax.set_xlim(0, 10)
    ax.set_ylim(0.5, 10)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(T("(b) 破堤口からの氾濫(平面)", "(b) Flooding from the breach (plan)"), fontsize=10, loc="left")
    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/mechanism.png", dpi=100)
    plt.close(fig)


# ---------------------------------------------------------------- 設定
def setup():
    z = rd("data/z_dike.txt")
    fig = plt.figure(figsize=(14, 8.2))
    gs = fig.add_gridspec(2, 2, width_ratios=[1, 1.25], height_ratios=[1, 1])
    ax = fig.add_subplot(gs[:, 0])
    im = ax.imshow(z, extent=EXT, cmap="terrain", vmin=-4, vmax=6)
    ax.contour((np.arange(NX) + 0.5) * DX, (np.arange(NY) + 0.5) * DX, z, levels=np.arange(-2.0, 0.01, 0.5), colors="0.4", linewidths=0.4)
    ax.plot([I_LEV2 * DX - 10] * 2, [(J_LOW1 - 1) * DX, J_LOW2 * DX], color="#c0392b", lw=4)
    ax.annotate(T("天端の低い区間 = 破堤口(150 m)", "low crest = breach (150 m)"), xy=(I_LEV2 * DX, (J_LOW1 - 1) * DX),
                xytext=(450, 330), color="#c0392b", fontsize=8, arrowprops=dict(arrowstyle="-", color="#c0392b", lw=0.8))
    for nm, (i1, i2, j1, j2) in BLOCKS.items():
        ax.add_patch(plt.Rectangle(((i1 - 1) * DX, (j1 - 1) * DX), (i2 - i1 + 1) * DX, (j2 - j1 + 1) * DX, facecolor="none", edgecolor=C_HOUSE, hatch="xx", lw=1.2))
        ax.text((i2 + 1) * DX, (j1 + j2) / 2 * DX, T(f"住宅地 {nm}", f"houses {nm}"), color=C_HOUSE, fontsize=8, va="center")
    ax.plot([I_LEV2 * DX, NX * DX], [J_DIKE * DX] * 2, color="k", lw=2, ls="--")
    ax.text(1000, J_DIKE * DX - 45, T("二線堤(破堤+二線堤のケースだけ)", "secondary levee (only in the breach + levee case)"), fontsize=8, ha="center",
            bbox=dict(facecolor="w", alpha=0.7, edgecolor="none", pad=1))
    ax.annotate("", xy=(90, 1900), xytext=(90, 100), arrowprops=dict(arrowstyle="-|>", color="w", lw=1.5))
    ax.text(60, 1000, T("川", "river"), color="w", rotation=90, fontsize=9, va="center")
    ax.text(1000, 1980, T("南辺: 自由流出(氾濫原が下流へ続く)", "south edge: free outflow (the plain continues)"), fontsize=8, ha="center")
    ax.set_xlabel("x (m)")
    ax.set_ylabel(T("y (m)  北 → 南", "y (m)  north → south"))
    ax.set_title(T("地形(等高線 0.5 m)と住宅地・二線堤", "Terrain (0.5 m contours), houses and secondary levee"), fontsize=10)
    fig.colorbar(im, ax=ax, shrink=0.7, pad=0.02).set_label(T("地盤高 (m)", "ground elevation (m)"))
    ax = fig.add_subplot(gs[0, 1])
    z0 = rd("data/z.txt")
    j = (J_LOW1 + J_LOW2) // 2
    xs = (np.arange(NX) + 0.5) * DX
    zb = z0[j - 1].copy()
    zb[13:15] = z0[j - 1, 15]
    ax.fill_between(xs[:40], -4, z0[j - 1, :40], color=C_GROUND, step="mid")
    ax.step(xs[:40], z0[J_LOW1 - 4, :40], where="mid", color="k", lw=1, ls=":", label=T("ふつうの区間の堤防(高さ 4 m)", "ordinary levee (4 m high)"))
    ax.step(xs[:40], zb[:40], where="mid", color="#c0392b", lw=1.2, ls="--", label=T("破堤後(堤内地の地盤高まで下がる)", "after the breach (down to the landside ground)"))
    if os.path.exists("result_overtop/probes/probe0001.csv"):     # 洪水のピークの水位は越水だけのケースの結果から(計算前は描かない)
        t, zp, hp = probe("overtop", 1)
        ax.axhline(np.max(np.asarray(zp) + np.asarray(hp)), xmin=0.02, xmax=0.33, color=C_WATER, lw=2, label=T("洪水のピークの水位(越水だけのケース)", "flood peak level (overtopping-only case)"))
    ax.set_xlim(0, 400)
    ax.set_ylim(-3.5, 4.5)
    ax.set_xlabel("x (m)")
    ax.set_ylabel(T("標高 (m)", "elevation (m)"))
    ax.set_title(T(f"破堤口の中央の横断(行 {j})", f"Cross-section through the centre of the breach (row {j})"), fontsize=10)
    ax.text(85, -2.5, T("川(幅 100 m)", "river (100 m wide)"), ha="center", fontsize=8)
    ax.text(140, 2.9, T("天端の低い区間", "low crest"), ha="center", fontsize=8, color="#c0392b")
    ax.text(300, 0.0, T("堤内地", "landside"), ha="center", fontsize=8)
    ax.legend(fontsize=8, loc="upper right")
    ax = fig.add_subplot(gs[1, 1])
    tq, qq = inflow_series()
    ax.plot(tq, qq, color="k", lw=1.8, label=T("洪水の流量(上流端)", "flood discharge (upstream end)"))
    ax.set_ylabel(T("流量 (m³/s)", "discharge (m³/s)"))
    ax.set_xlabel(T("時刻 (分)", "time (min)"))
    ax.axvspan(147, 309, color=C_WATER, alpha=0.1)
    ax.text(150, 150, T("越水(147〜309 分)", "overtopping (147-309 min)"), fontsize=8, color=C_WATER)
    for case, lab, col, ls in CASES[1:3]:
        t0, t1 = T_BREACH[case]
        y = 1750 if case == "breach" else 1850
        ax.plot([t0, t1], [y, y], color=col, lw=5, solid_capstyle="butt")
        ax.text(t1 + 5, y, T(f"{lab}: {t0} 分から破堤、{t1} 分に 150 m", f"{lab}: from {t0} min, 150 m at {t1} min"), fontsize=8, va="center", color=col)
    ax.set_xlim(0, 480)
    ax.set_ylim(0, 2000)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, loc="center right")
    ax.set_title(T("洪水と破堤の時刻", "Flood and breach timing"), fontsize=10)
    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/setup.png", dpi=100)
    plt.close(fig)


# ---------------------------------------------------------------- 則(入力と設定値だけ。計算結果を使わない)
def param_value(name, fn="param.txt"):
    """設定ファイルの「name = 値」を読む(最初の 1 つ。! 以降のコメントは除く)。"""
    for line in open(fn, encoding="utf-8"):
        s = line.split("!")[0]
        if "=" in s and s.split("=")[0].strip() == name:
            return float(s.split("=")[1])
    raise KeyError(f"{name} is not in {fn}")


def draft(sg, d):
    """横向き円柱の喫水: 水没断面積比 (θ − sinθ)/2π = sg を二分法で解く(src/m_driftwood.f90 の m_driftwood_draft と同じ)。"""
    lo, hi = 0.0, 1.0
    for _ in range(60):
        xm = 0.5 * (lo + hi)
        th = 2.0 * np.arccos(1.0 - 2.0 * xm)
        if (th - np.sin(th)) / (2.0 * np.pi) < sg:
            lo = xm
        else:
            hi = xm
    return 0.5 * (lo + hi) * d


def breach_schedule(out):
    """make_breach.py が data/<out>/ に書いた規定底面運動: 時刻 (分)、窓の左上 (i1, j1)、累積変位 (時刻, 行, 列)。"""
    ts, ds = [], []
    for line in open(f"data/{out}/bmlist.txt"):
        if line.startswith("#") or not line.strip():
            continue
        f = line.split()
        i1, j1, ni, nj = (int(v) for v in f[2:6])
        ts.append(float(f[0]) / 60.0)
        ds.append(np.loadtxt(os.path.join("data", f[1])).reshape(nj, ni))
    return np.array(ts), (i1, j1), np.array(ds)


def _box(ax, x, y, w, h, text, fc, ec, fs=8.5):
    ax.add_patch(plt.Rectangle((x, y), w, h, facecolor=fc, edgecolor=ec, lw=1.2))
    ax.text(x + 0.12, y + h - 0.12, text, fontsize=fs, va="top", ha="left", linespacing=1.35)


def _arrow(ax, xy, xytext, color, ls="-", lw=1.5):
    ax.annotate("", xy=xy, xytext=xytext, arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, ls=ls,
                                                          shrinkA=0, shrinkB=0))


def laws():
    z = rd("data/z.txt")
    gv0 = rd("data/gv.txt").min()                         # 住宅地の空隙率
    stock = rd("data/bdstock.txt").max()                  # 家屋ストック (m3/m2)
    fc1, fc2 = param_value("bd_fcrit"), param_value("bd_fcrit2")
    wdes, fsink = param_value("bd_wdes"), param_value("bd_fsink")
    wstop, vstop = param_value("bd_wstop"), param_value("bd_vstop")
    sgbd, dlog = param_value("bd_sg"), param_value("bd_dlog")
    hf = draft(sgbd, dlog)                                # 瓦礫の喫水
    tq, qq = inflow_series()
    tpk = tq[qq == qq.max()]                              # 上流端の流量のピークの期間
    fig = plt.figure(figsize=(15, 11))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.1, 1], height_ratios=[1, 1], left=0.06, right=0.985,
                          top=0.92, bottom=0.04, wspace=0.13, hspace=0.24)
    fig.suptitle(T("破堤・家屋の空隙率・家屋の破壊の則(make_breach.py が書いた入力と param.txt の値で描く。計算結果ではない)",
                   "The breach, building porosity and building destruction as ENCflow applies them "
                   "(inputs written by make_breach.py and the values of param.txt; not computed results)"),
                 fontsize=10.5, x=0.06, ha="left")

    # (a) 与えた破堤: 行ごとの天端の高さと、破堤口の幅
    sub = gs[0, 0].subgridspec(2, 1, height_ratios=[1.55, 1], hspace=0.08)
    ax = fig.add_subplot(sub[0])
    axw = fig.add_subplot(sub[1], sharex=ax)
    tt = np.linspace(150.0, 330.0, 3601)
    info = {}                                             # 中央の行・両端の行と、下がり始め・下がり終わりの時刻
    for out, cmap, col, ls, lab in (("bm_breach", "Reds", "#c0392b", "-", T("越水で破堤(param.txt)", "breach by overtopping (param.txt)")),
                                    ("bm_delay", "Oranges", "#e08214", "--", T("1 時間遅れる(param_delay.txt)", "breach 1 hour later (param_delay.txt)"))):
        ts, (i1, j1), d = breach_schedule(out)
        nj = d.shape[1]
        jc = j1 + (nj - 1) // 2                           # 最初に下がる中央の行(make_breach.py の --center の既定)
        cols = plt.get_cmap(cmap)(np.linspace(0.95, 0.45, nj - (jc - j1)))
        started, floor = np.zeros_like(tt), np.zeros_like(tt)
        for jj in range(nj):
            j = j1 + jj
            dd = np.interp(tt, ts, d[:, jj, 0])           # スナップショットの間は線形補間(f_bminterp = 1 の既定)
            crest = z[j - 1, i1 - 1] + dd - z[j - 1, I_LEV2]   # 天端 − 法尻(列 16 = make_breach.py の --floor-col)
            started += (dd < 0.0) * DX
            floor += (crest < 0.005) * DX
            if j in (jc, j1):
                info[(out, j == jc)] = (j, tt[np.argmax(dd < 0.0)], tt[np.argmax(crest < 0.005)], crest[0])
            if j >= jc:
                ax.plot(tt, crest, ls, color=cols[j - jc], lw=1.7 if j in (jc, j1 + nj - 1) else 0.9,
                        label=lab if j == jc else None)
        axw.plot(tt, started, ls, color=col, lw=1.0)
        axw.plot(tt, floor, ls, color=col, lw=2.2)
    zn = z[J_LOW1 - 3, I_LEV2 - 2] - z[J_LOW1 - 3, I_LEV2]
    ax.axhline(zn, color="0.45", lw=0.9, ls=":")
    ax.text(328, zn + 0.06, T(f"ふつうの区間の天端(法尻 + {zn:.1f} m)", f"ordinary levee crest (toe + {zn:.1f} m)"),
            fontsize=8, color="0.35", ha="right", va="bottom")
    jc, t0c, t1c, cr0 = info[("bm_breach", True)]
    je_, t0e, t1e, _ = info[("bm_breach", False)]
    jn = 2 * jc - je_                                     # 反対側の端の行(中央から対称)
    lag = info[("bm_delay", True)][1] - t0c
    ax.text(152, cr0 + 0.08, T(f"天端の低い区間(法尻 + {cr0:.1f} m)", f"low crest (toe + {cr0:.1f} m)"), fontsize=8, va="bottom")
    ax.annotate(T(f"中央の行 {jc}\n{t0c:.0f}→{t1c:.0f} 分", f"central row {jc}\n{t0c:.0f}→{t1c:.0f} min"),
                xy=((t0c + t1c) / 2 + 1, cr0 * 0.45), xytext=(156, 0.75),
                fontsize=8, color="#c0392b", arrowprops=dict(arrowstyle="-", color="#c0392b", lw=0.7))
    ax.annotate(T(f"両端の行 {je_}・{jn}: {t0e:.0f}→{t1e:.0f} 分", f"end rows {je_}, {jn}: {t0e:.0f}→{t1e:.0f} min"),
                xy=(t0e + 0.2 * (t1e - t0e), cr0 * 0.8), xytext=(t0e - 14, cr0 + 0.42),
                fontsize=8, color="#c0392b", arrowprops=dict(arrowstyle="-", color="#c0392b", lw=0.7))
    ax.text(t1e + lag + 7, 1.3, T(f"同じ進み方で\n{lag:.0f} 分遅い", f"same course,\n{lag:.0f} min later"), fontsize=8, color="#e08214", ha="center")
    for a in (ax, axw):
        a.axvspan(tpk[0], tpk[-1], color=C_WATER, alpha=0.08, lw=0)
        a.grid(alpha=0.3)
    ax.text(152, 4.52, T(f"上流端の流量のピーク {qq.max():,.0f} m³/s({tpk[0]:.0f}〜{tpk[-1]:.0f} 分)",
                         f"upstream peak {qq.max():,.0f} m³/s ({tpk[0]:.0f}-{tpk[-1]:.0f} min)"), fontsize=8, color=C_WATER, va="top")
    ax.set_ylim(-0.15, 4.6)
    ax.set_ylabel(T("天端の高さ (m)\n(堤内地の法尻から)", "crest height (m)\nabove the landside toe"), fontsize=9)
    ax.legend(fontsize=8, loc="upper right", bbox_to_anchor=(1.0, 0.84), frameon=False)
    ax.tick_params(labelbottom=False, labelsize=8)
    ax.set_title(T("(a) 与えた破堤(規定底面運動。make_breach.py の出力)", "(a) The prescribed breach (bed motion written by make_breach.py)"),
                 fontsize=9.5, loc="left")
    axw.plot([], [], color="0.3", lw=1.0, label=T("下がり始めた幅", "width going down"))
    axw.plot([], [], color="0.3", lw=2.2, label=T("法尻の高さまで下がった幅", "width down to the toe"))
    axw.legend(fontsize=8, loc="upper left", frameon=False)
    axw.set_ylim(0, 165)
    axw.set_xlim(150, 330)
    axw.set_ylabel(T("破堤口の幅 (m)", "breach width (m)"), fontsize=9)
    axw.set_xlabel(T("時刻 (分)", "time (min)"), fontsize=9)
    axw.tick_params(labelsize=8)

    # (b) 家屋の空隙率と、壊れた家屋の分
    ax = fig.add_subplot(gs[0, 1])
    ax.set_title(T(f"(b) 家屋の空隙率 gv(住宅地 {gv0:.1f})と、壊れた家屋の分", f"(b) Building porosity gv ({gv0:.1f} in the residential areas) and destroyed houses"),
                 fontsize=9.5, loc="left")
    houses = [(1.2, 7.4, 4.0, 2.5), (6.4, 6.9, 2.5, 4.0), (2.3, 12.0, 3.2, 3.125)]     # 3 棟 × 10 m² = 30 m²(1 − gv0 = 0.3)
    for k, dmg in enumerate((0.0, 0.5, 1.0)):
        x0 = 3.2 + 12.4 * k
        gv = gv0 + (1.0 - gv0) * dmg
        ax.add_patch(plt.Rectangle((x0, 6.0), 10, 10, facecolor="#cfe3f6", edgecolor="k", lw=1.2))
        for hx, hy, hw, hh in houses:
            sc = np.sqrt(1.0 - dmg)
            cx, cy = hx + hw / 2, hy + hh / 2
            if dmg < 1.0:
                ax.add_patch(plt.Rectangle((x0 + cx - hw * sc / 2, cy - hh * sc / 2), hw * sc, hh * sc, facecolor=C_HOUSE, edgecolor="none"))
            ax.add_patch(plt.Rectangle((x0 + hx, hy), hw, hh, facecolor="none", edgecolor=C_HOUSE, lw=0.8, ls=":"))
        ax.text(x0 + 5, 16.5, T(["壊れていない", "半分壊れた", "全部壊れた"][k], ["intact", "half destroyed", "all destroyed"][k])
                + f"  d = {dmg:g}", ha="center", fontsize=8.5)
        ax.text(x0 + 5, 5.4, f"gv = {gv:.2f}\nλm = {gv + (1 - gv) * CM:.2f}\n" + T(f"水深 × {1 / gv:.2f}", f"depth × {1 / gv:.2f}"),
                ha="center", va="top", fontsize=8.2, linespacing=1.4)
    for yy in (7.5, 11.0, 14.5):
        _arrow(ax, (3.2, yy), (0.4, yy), C_WATER, lw=1.3)
    ax.text(0.2, 15.6, "q = u·h", fontsize=8, color=C_WATER)
    ax.text(0.3, -0.6, T(f"連続式: 水がたまるのは建物の外の gv·Δx·Δy だけ(同じ水量なら水深は 1/gv 倍)\n"
                         f"辺の流量 q = u·h は辺の全幅で通す(通過幅を gv で縮めない。左の矢印)\n"
                         f"運動方程式: 慣性 λm = gv + (1 − gv)·cm(cm = {CM:.1f})、圧力と摩擦の項 × gv\n"
                         f"  → 加速は遅くなるが、等流の流量は変わらない\n"
                         f"家屋の抗力の項には家屋の寸法 fn_bb が要る(この例題は与えないので働かない)\n"
                         f"壊れると gv = {gv0:.1f} + {1 - gv0:.1f}·d(d = 破壊率。f_bdgv = 1)。水量を保ち、\n"
                         f"  水深は gv の比で浅くなる。セルは 10 m × 10 m",
                         f"Continuity: water is stored only outside the buildings, gv·Δx·Δy (depth × 1/gv for\n"
                         f"  the same volume). An edge passes q = u·h over its full width (the passage width is not\n"
                         f"  narrowed by gv; arrows). Momentum: inertia λm = gv + (1 − gv)·cm (cm = {CM:.1f});\n"
                         f"  the pressure and friction terms × gv, so the flow accelerates more slowly, but uniform\n"
                         f"  flow keeps its discharge. Building drag needs the building size fn_bb, which this\n"
                         f"  example does not give, so there is no drag. Destruction raises gv = {gv0:.1f} + {1 - gv0:.1f}·d\n"
                         f"  (d = destroyed fraction; f_bdgv = 1), keeping the water volume. Cells 10 m × 10 m."),
            fontsize=8, va="top", linespacing=1.5)
    ax.set_xlim(0, 38)
    ax.set_ylim(-11.5, 18)
    ax.set_aspect("equal")
    ax.axis("off")

    # (c) 家屋が壊れる条件: 流体力 hV² と破壊の倍率
    sub = gs[1, 0].subgridspec(1, 2, width_ratios=[1.45, 1], wspace=0.05)
    ax = fig.add_subplot(sub[0])
    vmax, hmax = 4.0, 3.0
    vg, hg = np.meshgrid(np.linspace(0.0, vmax, 801), np.linspace(0.0, hmax, 601))
    xx = hg * vg ** 2
    aa = np.where(xx > fc1, np.clip((xx - fc1) / (fc2 - fc1), 0.0, 1.0), np.nan)
    aa = np.where(xx >= fc2, 1.5, aa)                     # 倍率 1 の範囲(hV² ≥ bd_fcrit2)は別の色(色見本の三角)
    ramp_cols = ["#fee8c8", "#fdd49e", "#fdbb84", "#fc8d59", "#ef6548", "#c8402c"]
    cf = ax.contourf(vg, hg, aa, levels=[0, 0.2, 0.4, 0.6, 0.8, 1.0], colors=ramp_cols, extend="max", alpha=0.9)
    v = np.linspace(0.3, vmax, 400)
    ax.plot(v, fc1 / v ** 2, color="k", lw=1.8)
    ax.plot(v, fc2 / v ** 2, color="#7f0000", lw=1.8)
    for xv in (3.0, 4.0):
        ax.plot(v, xv / v ** 2, color="#7f0000", lw=0.8, ls="--")
    for xv in (fc1, 3.0, 4.0, fc2):                       # 線の上の数字 = hV²(等高線の数字と同じ置き方)
        ax.text(np.sqrt(xv / 1.2), 1.2, f"{xv:g}", fontsize=8, color="k" if xv == fc1 else "#7f0000", va="center", ha="center",
                bbox=dict(facecolor="w", edgecolor="none", pad=0.8))
    tfull = stock / wdes / 60.0                           # 倍率 1 で家屋ストックが全部壊れるまで (分)
    ax.text(0.12, 0.2, T(f"壊れない\n(hV² ≤ {fc1:g})", f"no breaking\n(hV² ≤ {fc1:g})"), fontsize=8.5, color="0.3")
    ax.text(3.0, 2.0, T(f"倍率 1\n{tfull:.1f} 分で全壊", f"factor 1:\nall in {tfull:.1f} min"), fontsize=8.5, color="w", ha="center", va="center")
    ax.set_xlim(0, vmax)
    ax.set_ylim(0, hmax)
    ax.set_xlabel(T("流速 V (m/s)", "velocity V (m/s)"), fontsize=9)
    ax.set_ylabel(T("浸水深 h (m)", "inundation depth h (m)"), fontsize=9)
    ax.tick_params(labelsize=8)
    ax.set_title(T("(c) 家屋が壊れる条件(f_bdcrit = 2: 流体力 hV²)", "(c) When houses break (f_bdcrit = 2: load hV²)"), fontsize=9.5, loc="left")
    axi = fig.add_subplot(sub[1])
    axi.axis("off")
    axi.set_xlim(0, 1)
    axi.set_ylim(0, 1)
    for y_, c_, ls_, lab in ((0.94, "k", "-", T(f"hV² = {fc1:g}(bd_fcrit): 壊れ始める", f"hV² = {fc1:g} (bd_fcrit): breaking starts")),
                             (0.87, "#7f0000", "-", T(f"hV² = {fc2:g}(bd_fcrit2): 最も速い", f"hV² = {fc2:g} (bd_fcrit2): fastest")),
                             (0.80, "#7f0000", "--", T("hV² = 3、4", "hV² = 3, 4"))):
        axi.plot([0.04, 0.16], [y_, y_], color=c_, ls=ls_, lw=1.8 if ls_ == "-" else 0.9)
        axi.text(0.2, y_, lab, fontsize=8, va="center")
    rows = "\n".join(T(f"  hV² = {xv:g} → {tfull / min(1.0, (xv - fc1) / (fc2 - fc1)):.0f} 分", f"  hV² = {xv:g} → {tfull / min(1.0, (xv - fc1) / (fc2 - fc1)):.0f} min")
                     for xv in (3.0, 4.0))
    axi.text(0.04, 0.72, T(f"判定量 X = (h + bd_sg·hbd)·V²\n(図は流れる瓦礫 hbd = 0)\n"
                           f"倍率 a = min(1, (X − {fc1:g})/({fc2:g} − {fc1:g}))\n"
                           f"壊れる速さ = bd_wdes·a\n  = {wdes * 1e4:g}×10⁻⁴·a m³/m²/s\n\n"
                           f"家屋ストック {stock:g} m³/m² が全部壊れるまで\n(その値が続いたとき):\n{rows}\n"
                           f"  hV² ≥ {fc2:g} → {tfull:.1f} 分",
                           f"load X = (h + bd_sg·hbd)·V²\n(floating debris hbd = 0 here)\n"
                           f"factor a = min(1, (X − {fc1:g})/({fc2:g} − {fc1:g}))\n"
                           f"breaking rate = bd_wdes·a\n  = {wdes * 1e4:g}×10⁻⁴·a m³/m²/s\n\n"
                           f"time to break the whole house stock\n{stock:g} m³/m² (if X stays):\n{rows}\n"
                           f"  hV² ≥ {fc2:g} → {tfull:.1f} min"),
             fontsize=8, va="top", linespacing=1.45)
    cax = axi.inset_axes([0.04, 0.06, 0.8, 0.045])
    cb = fig.colorbar(cf, cax=cax, orientation="horizontal", ticks=[0, 0.2, 0.4, 0.6, 0.8, 1.0], extendfrac=0.12)
    cb.ax.tick_params(labelsize=7.5)
    cb.set_label(T(f"破壊の倍率 a(三角 = 1。hV² ≥ {fc2:g})", f"breaking factor a (triangle = 1; hV² ≥ {fc2:g})"), fontsize=8)

    # (d) 壊れた家屋の行き先(瓦礫)
    ax = fig.add_subplot(gs[1, 1])
    ax.set_title(T("(d) 壊れた家屋の行き先(瓦礫。fn_bldgdebris)", "(d) Where the destroyed houses go (debris; fn_bldgdebris)"), fontsize=9.5, loc="left")
    _box(ax, 0.0, 3.9, 2.9, 1.6, T(f"家屋ストック wbs\n{stock:g} m³/m²(住宅地)\n壊れる速さ bd_wdes·a((c))", f"house stock wbs\n{stock:g} m³/m² (residential)\nbreaks at bd_wdes·a ((c))"), "#efe6dc", C_HOUSE)
    _box(ax, 6.2, 3.9, 3.9, 1.6, T(f"流れる瓦礫 hbd\n水と同じ流れで運ばれる\n判定量 X に {sgbd:g}·hbd を足す((c))", f"floating debris hbd\ncarried with the water\nadds {sgbd:g}·hbd to the load X ((c))"), "#e3eefa", C_WATER)
    _box(ax, 6.2, 0.2, 3.9, 1.5, T("止まった瓦礫 wbd\nその場に残る\n(再び流れない: bd_wfloat = 0)", "deposited debris wbd\nstays in place\n(no refloating: bd_wfloat = 0)"), "#efe6dc", C_HOUSE)
    _box(ax, 0.0, 0.2, 4.1, 1.5, T(f"空隙率への帰還(f_bdgv = 1)\n破壊率 d = 1 − wbs/wbs0\ngv = {gv0:.1f} + {1 - gv0:.1f}·d((b))", f"feedback to the porosity (f_bdgv = 1)\ndestroyed fraction d = 1 − wbs/wbs0\ngv = {gv0:.1f} + {1 - gv0:.1f}·d ((b))"), "#e8f3e8", "#2e7d32")
    _arrow(ax, (6.2, 4.85), (2.9, 4.85), "#c0392b", lw=1.8)
    ax.text(4.55, 4.95, T(f"浮く分\n1 − bd_fsink = {1 - fsink:.1f}", f"floating share\n1 − bd_fsink = {1 - fsink:.1f}"), fontsize=8, color="#c0392b", ha="center", va="bottom")
    _arrow(ax, (6.2, 1.2), (2.9, 4.3), "#c0392b", lw=1.8)
    ax.text(5.05, 3.0, T(f"沈む分\nbd_fsink = {fsink:g}\n(瓦・基礎など。\nその場に)", f"sinking share\nbd_fsink = {fsink:g}\n(tiles, foundations;\non the spot)"),
            fontsize=8, color="#c0392b", ha="left", va="center")
    _arrow(ax, (7.45, 1.7), (7.45, 3.9), C_HOUSE, lw=1.8)
    ax.text(7.6, 2.8, T(f"止まる:\nH < 喫水 {hf:.2f} m\nまたは V < bd_vstop = {vstop:g} m/s\nのとき bd_wstop = {wstop:g} m/s で\n乾いたセル(h ≤ {DD_MIN:g} m)は全部",
                        f"stops where\nH < draft {hf:.2f} m\nor V < bd_vstop = {vstop:g} m/s,\nat bd_wstop = {wstop:g} m/s;\ndry cells (h ≤ {DD_MIN:g} m): all"),
            fontsize=8, va="center", linespacing=1.4)
    _arrow(ax, (1.6, 1.7), (1.6, 3.9), "#2e7d32", ls="--", lw=1.4)
    ax.text(0.0, -0.15, T(f"喫水は寸法 bd_dlog = {dlog:g} m・比重 bd_sg = {sgbd:g} の横向き円柱の浮力の釣り合いから(半分沈む)。\nH = h(土砂なし)。",
                          f"The draft is the buoyancy balance of a horizontal cylinder (bd_dlog = {dlog:g} m, bd_sg = {sgbd:g};\nhalf submerged). H = h (no sediment)."),
            fontsize=7.8, va="top", color="0.3")
    ax.set_xlim(0, 10.2)
    ax.set_ylim(-0.9, 5.8)
    ax.axis("off")
    fig.savefig(f"{FIGDIR}/laws.png", dpi=100)
    plt.close(fig)


# ---------------------------------------------------------------- 結果
def maps():
    fig, axs = plt.subplots(1, 4, figsize=(16, 5.6), constrained_layout=True)
    levels = [0.01, 0.1, 0.3, 0.5, 1.0, 2.0, 3.0]
    cmap = plt.get_cmap("Blues", len(levels) + 1)
    norm = BoundaryNorm(levels, cmap.N, extend="max")
    for ax, (case, lab, col, ls) in zip(axs, CASES):
        h = rd(f"result_{case}/H9999.txt")
        h = np.where(h > 0.01, h, np.nan)
        h[:, :15] = np.nan
        im = ax.imshow(h, extent=EXT, cmap=cmap, norm=norm)
        bs = last_frame(case, "Bs")
        ax.contourf((np.arange(NX) + 0.5) * DX, (np.arange(NY) + 0.5) * DX, bs, levels=[0.1, 0.5, 1.01], colors=["#f4a582", "#b2182b"], alpha=0.9)
        for nm, (i1, i2, j1, j2) in BLOCKS.items():
            ax.add_patch(plt.Rectangle(((i1 - 1) * DX, (j1 - 1) * DX), (i2 - i1 + 1) * DX, (j2 - j1 + 1) * DX, facecolor="none", edgecolor=C_HOUSE, lw=1))
            ax.text((i2 + 1) * DX, (j1 - 1) * DX, nm, color=C_HOUSE, fontsize=9, va="top")
        ax.plot([I_LEV2 * DX - 10] * 2, [(J_LOW1 - 1) * DX, J_LOW2 * DX], color="#c0392b", lw=3)
        if case == "dike":
            ax.plot([I_LEV2 * DX, NX * DX], [J_DIKE * DX] * 2, color="k", lw=2)
        ax.set_title(lab, fontsize=10)
        ax.set_xlabel("x (m)")
    axs[0].set_ylabel("y (m)")
    cb = fig.colorbar(im, ax=axs, shrink=0.85)
    cb.set_label(T("最大浸水深 (m)", "maximum inundation depth (m)"))
    handles = [plt.Rectangle((0, 0), 1, 1, color="#f4a582"), plt.Rectangle((0, 0), 1, 1, color="#b2182b")]
    fig.legend(handles, [T("家屋の流失 10〜50 %", "houses swept away 10-50 %"), T("家屋の流失 50 % 以上", "houses swept away ≥ 50 %")],
               loc="lower center", ncol=2, fontsize=9, frameon=False, bbox_to_anchor=(0.45, -0.06))
    fig.savefig(f"{FIGDIR}/maps.png", dpi=100, bbox_inches="tight")
    plt.close(fig)


def series():
    fig, axs = plt.subplots(1, 3, figsize=(16, 4.6), constrained_layout=True)
    tq, qq = inflow_series()
    axs[1].plot(tq, qq, color="k", lw=1, label=T("上流端の流量", "upstream discharge"))
    for case, lab, col, ls in CASES:
        t, q = flux(case, 1)
        axs[0].plot(t, q, ls, color=col, lw=1.8, label=lab)
        t, q = flux(case, 2)
        axs[1].plot(t, q, ls, color=col, lw=1.6, label=lab)
        t, z, h = probe(case, 4)
        axs[2].plot(t, h, ls, color=col, lw=1.6, label=lab)
    axs[0].set_title(T("堤内地へ入る流量(堤防の法尻の測線)", "Flow into the landside (line along the levee toe)"), fontsize=10)
    axs[1].set_title(T("破堤口より下流の川の流量", "River discharge downstream of the breach"), fontsize=10)
    axs[2].set_title(T("住宅地 B(破堤口から南へ約 700 m)の浸水深", "Depth at houses B (about 700 m south of the breach)"), fontsize=10)
    axs[0].set_ylabel(T("流量 (m³/s)", "discharge (m³/s)"))
    axs[1].set_ylabel(T("流量 (m³/s)", "discharge (m³/s)"))
    axs[2].set_ylabel(T("浸水深 (m)", "depth (m)"))
    for ax in axs:
        ax.set_xlabel(T("時刻 (分)", "time (min)"))
        ax.set_xlim(0, 480)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8, loc="upper left" if ax is not axs[1] else "lower center")
    fig.savefig(f"{FIGDIR}/series.png", dpi=100)
    plt.close(fig)


def table():
    st = rd("data/bdstock.txt")
    print(T("ケース | 堤内地へ入った水 (万 m³) | 最大流量 (m³/s) | 下流の川の最小流量 (m³/s) | 浸水 0.1 m 以上 (ha) | 0.5 m 以上 (ha) | 最大浸水深 (m) | 流失 A / B / C (%) | 最大浸水深 A / B / C (m) | B が 0.5 m に達した時刻 (分)",
            "case | water into the landside (10^4 m3) | peak flow (m3/s) | min river discharge downstream (m3/s) | inundated >= 0.1 m (ha) | >= 0.5 m (ha) | max depth (m) | swept away A / B / C (%) | max depth A / B / C (m) | B reaches 0.5 m (min)"))
    for case, lab, col, ls in CASES:
        t, q = flux(case, 1)
        vol = np.sum(0.5 * (q[1:] + q[:-1]) * np.diff(t) * 60.0)
        t2, q2 = flux(case, 2)
        h = rd(f"result_{case}/H9999.txt")[:, 15:]
        hh = rd(f"result_{case}/H9999.txt")
        bs = last_frame(case, "Bs")
        lost, dep = [], []
        for nm, (i1, i2, j1, j2) in BLOCKS.items():
            sl = (slice(j1 - 1, j2), slice(i1 - 1, i2))
            lost.append((bs[sl] * st[sl]).sum() / st[sl].sum() * 100)
            dep.append(hh[sl].max())
        tb, zb, hb = probe(case, 4)
        on = tb[np.argmax(hb > 0.5)] if (hb > 0.5).any() else float("nan")
        print(f"{lab} | {vol / 1e4:.1f} | {q.max():.0f} | {q2[(t2 > 150) & (t2 < 330)].min():.0f} | {(h > 0.1).sum() * DX * DX / 1e4:.0f} | "
              f"{(h > 0.5).sum() * DX * DX / 1e4:.0f} | {h.max():.2f} | {lost[0]:.0f} / {lost[1]:.0f} / {lost[2]:.0f} | "
              f"{dep[0]:.2f} / {dep[1]:.2f} / {dep[2]:.2f} | {on:.0f}")


if __name__ == "__main__":
    mechanism()
    setup()
    laws()
    if all(os.path.exists(f"result_{c}/FILENUMBER.csv") for c, _, _, _ in CASES):
        maps()
        series()
        table()
