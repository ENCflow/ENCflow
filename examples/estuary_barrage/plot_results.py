#!/usr/bin/env python3
"""estuary_barrage の図と数表(事前に make run で 4 ケースを計算しておく)。

  figs/mechanism.png 塩水くさびと地盤の塩水化の機構の模式図(データを使わない)
  figs/setup.png    地形(平面)と河道中心の縦断(堰・帯水層底・潮位の幅)
  figs/plan.png     20 日後の平面: 帯水層に占める塩水の割合と河道の底層塩水(4 ケース)
  figs/profile.png  20 日後の河道中心の縦断(河床の塩水交換あり、堰なし・あり)
  figs/series.png   帯水層の塩水量(混合比の感度ケースを含む 6 ケース)と塩水くさびの先端位置の時間変化
引数 en で英語ラベル版を en/figs/ に描く(データと描画処理は共通)。
"""
import glob
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)

DX, NX, NY = 40.0, 90, 24
I_COAST, I_WEIR, JC = 75, 63, 11          # 陸の最終列・堰の列(1 始まり)・河道中心行(0 始まり)
SY, ZBOT, DT_FILE_H = 0.2, -10.0, 6.0
CASES = [("nobarrage_off", T("堰なし", "No barrage"), T("河床の塩水の出入りなし", "no bed salt exchange")),
         ("nobarrage", T("堰なし", "No barrage"), T("河床の塩水の出入りあり", "with bed salt exchange")),
         ("barrage_off", T("堰あり", "Barrage"), T("河床の塩水の出入りなし", "no bed salt exchange")),
         ("barrage", T("堰あり", "Barrage"), T("河床の塩水の出入りあり", "with bed salt exchange"))]
# 下限側の感度ケース(f_salt_exch=2: 湧出を混合比で配分)
MIXCASES = [("nobarrage_mix", T("堰なし", "No barrage"), T("湧出を混合比で(下限側)", "seepage by mixing ratio (lower bound)")),
            ("barrage_mix", T("堰あり", "Barrage"), T("湧出を混合比で(下限側)", "seepage by mixing ratio (lower bound)"))]


def base(case):
    """ケース名から地形の名前(nobarrage / barrage)を返す。"""
    return case.replace("_off", "").replace("_mix", "")
X_MOUTH = I_COAST * DX / 1000.0
XK = (np.arange(NX) + 0.5) * DX / 1000.0
EXT = [0, NX * DX / 1000, NY * DX / 1000, 0]


def geo(name):
    return np.loadtxt(f"data/z_{name}.txt"), np.loadtxt(f"data/sd_{name}.txt")


def frames(case, var):
    fs = sorted(f for f in glob.glob(f"result_{case}/{var}[0-9][0-9][0-9][0-9].txt")
                if int(f[-8:-4]) < 9000)
    return fs


def load(case, var, k):
    return np.loadtxt(f"result_{case}/{var}{k:04d}.txt")


def tip_km(hss):
    """河道中心行で Hss > 0.05 m の最上流セルの河口からの距離 (km)。"""
    r = hss[JC, :I_COAST]
    idx = np.nonzero(r > 0.05)[0]
    return X_MOUTH - (idx.min() * DX / 1000.0) if len(idx) else 0.0


# 模式図の色(実験結果の図と同じ配色)
C_FRESH, C_SALT, C_AQ, C_AQSALT, C_LAND = "#9ecae1", "#1f4e9c", "#e8d9b5", "#c0392b", "#b9a37a"


def _arrow(ax, x0, y0, x1, y1, color, lw=2.0, style="-|>"):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw, shrinkA=0, shrinkB=0))


def _longitudinal(ax, barrage):
    """河道に沿った縦断の模式図(縮尺は誇張)。x: 0 = 上流端、7.5 = 河口、10 = 沖。"""
    xm, xb, ybot = 7.5, 6.2, -10.0
    x = np.linspace(0, 10, 401)
    bed = np.where(x <= xm, -3.0 - x / xm, -5.0)
    ax.fill_between(x, ybot, bed, color=C_AQ)
    # 帯水層の塩水(海の下は全層、堰なしはくさびの下、堰ありは堰の下流と底の舌)
    if barrage:
        top = np.where(x > xb + 0.08, bed, ybot + np.clip((x - 4.6) / (xb - 4.6), 0, 1) ** 3 * 1.6)
    else:
        top = np.where(x >= 2.4, bed, ybot + np.clip((x - 1.2) / 1.2, 0, 1) ** 2 * (bed + 10))
    ax.fill_between(x, ybot, np.minimum(top, bed), color=C_AQSALT, alpha=0.75)
    # 水面と塩水くさび
    eta = np.where(x < xb, 1.2, 0.0) if barrage else np.zeros_like(x)
    ax.fill_between(x, bed, eta, where=eta > bed, color=C_FRESH, alpha=0.8)
    tip = xb + 0.1 if barrage else 2.0
    wedge = np.where(x > tip, bed + np.clip((x - tip) / (xm - tip), 0, 1) ** 0.6 * 2.6, bed)
    wedge = np.where(x > xm, eta, wedge)
    ax.fill_between(x, bed, wedge, where=wedge > bed, color=C_SALT, alpha=0.85)
    ax.plot(x, bed, "k-", lw=1)
    if barrage:
        ax.add_patch(plt.Rectangle((xb - 0.08, -3.0 - xb / xm), 0.16, 1.0 + 3.0 + xb / xm,
                                   color="0.45", zorder=3))
    ax.axvline(xm, color="k", lw=0.6, ls=":")
    ax.text(xm + 0.05, 2.6, T("河口", "mouth"), fontsize=8)
    # 矢印と説明
    _arrow(ax, 0.3, -0.8, 1.9, -0.8, C_FRESH, lw=3)
    ax.text(0.3, -0.35, T("河川の淡水(下流へ)", "river fresh water (seaward)"), fontsize=8)
    _arrow(ax, 9.6, -0.9, 9.6, 0.9, "k", lw=1.2, style="<|-|>")
    ax.text(8.15, 1.25, T("潮汐(満潮・干潮)", "tide (high / low)"), fontsize=8)
    _arrow(ax, 9.3, -6.0, 8.0, -6.0, C_AQSALT, lw=2)
    ax.text(7.9, -6.9, T("海岸からの浸入", "intrusion from the coast"), fontsize=8, ha="center")
    if not barrage:
        _arrow(ax, 6.6, -3.2, 4.2, -2.9, C_SALT, lw=2.5)
        ax.text(3.0, -1.35, T("密度差で底を這って遡上する塩水くさび", "salt wedge creeping upstream along the bed (density)"),
                fontsize=8, color=C_SALT)
        for xi in (3.6, 4.9, 6.2):
            _arrow(ax, xi, -3.3 - xi / xm, xi, -5.4 - xi / xm, C_AQSALT, lw=1.6)
        ax.text(3.0, -8.9, T("河床から塩水が浸透し、重いので帯水層の底へ沈んで広がる",
                             "salt water infiltrates through the bed and, being denser, sinks and spreads"),
                fontsize=8, color="0.15")
    else:
        ax.text(xb - 0.1, 1.55, T("堰(天端は満潮より高い)", "barrage (crest above high water)"), fontsize=8, ha="center")
        ax.text(6.35, 0.35, T("くさびは堰で止まる", "the wedge stops at the barrage"), fontsize=8, color=C_SALT)
        ax.text(0.3, 1.45, T("堰の上流は淡水の湛水(水位が高い)", "fresh pool upstream (higher level)"), fontsize=8)
        for xi in (1.5, 3.0, 4.5):
            _arrow(ax, xi, -3.2 - xi / xm, xi, -5.3 - xi / xm, "#2c7fb8", lw=1.4)
        ax.text(0.3, -7.2, T("河床から淡水が浸透し、地下水位を押し上げる", "fresh water infiltrates and raises the groundwater head"),
                fontsize=8, color="0.15")
        _arrow(ax, 6.8, -9.6, 4.9, -9.6, C_AQSALT, lw=1.6)
        ax.text(3.1, -9.45, T("地下は堰の下でつながっている(底を這う舌)", "the aquifer is continuous under the barrage (tongue)"),
                fontsize=7.5, color="0.15")
    ax.set_xlim(0, 10)
    ax.set_ylim(-10.3, 3.0)
    ax.set_xticks([])
    ax.set_ylabel(T("標高(模式)", "elevation (schematic)"))
    ax.set_title(T("(b) 堰あり" if barrage else "(a) 堰なし", "(b) with barrage" if barrage else "(a) no barrage"),
                 fontsize=10, loc="left")


def _cross(ax, high):
    """河道を横切る断面の模式図。high: 満潮(川の水位 > 岸の地下水位)。"""
    ybot = -10.0
    x = np.linspace(-5, 5, 401)
    z = np.where(np.abs(x) < 1.2, -3.5, 3.0)
    ax.fill_between(x, ybot, z, color=C_AQ)
    gw = np.where(np.abs(x) < 1.2, 0.0, 0.3 - 0.15 * (np.abs(x) - 1.2))
    eta = 0.8 if high else -0.6
    ax.plot(x[np.abs(x) >= 1.2], (z * 0 + gw)[np.abs(x) >= 1.2], color="#2c7fb8", ls="--", lw=1.2)
    river = np.abs(x) < 1.2
    ax.fill_between(x, z, eta, where=river, color=C_FRESH, alpha=0.8)
    ax.fill_between(x, z, -1.6, where=river, color=C_SALT, alpha=0.85)
    salt_top = ybot + np.clip(1.0 - (np.abs(x) - 1.2) / 2.6, 0, 1) * 6.5
    salt_top = np.where(river, -3.5, salt_top)
    ax.fill_between(x, ybot, salt_top, color=C_AQSALT, alpha=0.75)
    ax.plot(x, z, "k-", lw=1)
    if high:
        for sgn in (-1, 1):
            _arrow(ax, sgn * 0.9, -3.7, sgn * 2.2, -5.3, C_AQSALT, lw=2)
        _arrow(ax, 0, -3.6, 0, -5.6, C_AQSALT, lw=2)
        ax.text(-4.8, 2.0, T("満潮: 川の水位 > 岸の地下水位", "high tide: river level > bank groundwater"), fontsize=8)
        ax.text(-4.8, -9.4, T("河床に接する底層の塩水が先にしみ込む", "the bottom salt layer touching the bed infiltrates first"),
                fontsize=7.5, color="0.15")
        title = T("(c) 河道の横断(満潮)", "(c) across the river (high tide)")
    else:
        for sgn in (-1, 1):
            _arrow(ax, sgn * 2.4, -1.0, sgn * 1.0, -2.6, "#2c7fb8", lw=2)
        ax.text(-4.8, 2.0, T("干潮: 岸の地下水位 > 川の水位", "low tide: bank groundwater > river level"), fontsize=8)
        ax.text(-4.8, -9.4, T("帯水層の上部の淡水が先に湧き出す", "the upper fresh water of the aquifer seeps out first"),
                fontsize=7.5, color="0.15")
        title = T("(d) 河道の横断(干潮)", "(d) across the river (low tide)")
    ax.text(3.2, 0.8, T("地下水位", "water table"), fontsize=7.5, color="#2c7fb8")
    ax.set_xlim(-5, 5)
    ax.set_ylim(-10.3, 3.0)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(title, fontsize=10, loc="left")


def mechanism():
    """塩水くさびと地盤の塩水化の機構の模式図(データを使わない)。"""
    fig = plt.figure(figsize=(13, 10.5))
    gs = fig.add_gridspec(3, 2, height_ratios=[1, 1, 0.95], hspace=0.3, wspace=0.08, top=0.95)
    _longitudinal(fig.add_subplot(gs[0, :]), barrage=False)
    _longitudinal(fig.add_subplot(gs[1, :]), barrage=True)
    _cross(fig.add_subplot(gs[2, 0]), high=True)
    _cross(fig.add_subplot(gs[2, 1]), high=False)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c, alpha=a) for c, a in
               ((C_FRESH, 0.8), (C_SALT, 0.85), (C_AQ, 1.0), (C_AQSALT, 0.75))]
    fig.legend(handles, [T("淡水(河川)", "fresh water (river)"), T("塩水(海・底層)", "salt water (sea, bottom layer)"),
                         T("帯水層(淡水)", "aquifer (fresh)"), T("帯水層の塩水", "salt water in the aquifer")],
               loc="upper center", ncol=4, fontsize=9, frameon=False, bbox_to_anchor=(0.5, 0.99))
    fig.savefig(f"{FIGDIR}/mechanism.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


def setup():
    z, _ = geo("nobarrage")
    zw, _ = geo("barrage")
    fig, axs = plt.subplots(1, 2, figsize=(14, 3.8), gridspec_kw={"width_ratios": [1.2, 1]})
    zz = zw.copy()
    zz[:, 87:] = np.nan
    im = axs[0].imshow(zz, extent=EXT, cmap="terrain", vmin=-6, vmax=4, aspect="equal")
    axs[0].axvline(X_MOUTH, color="k", lw=0.8)
    axs[0].plot([(I_WEIR - 0.5) * DX / 1000] * 2, [(JC - 1.5) * DX / 1000, (JC + 1.5) * DX / 1000],
                color="red", lw=3)
    axs[0].text(3.54, 0.48, T("海域マスク(潮位)", "sea mask (tide)"), rotation=90, ha="center", va="center", fontsize=7)
    axs[0].text(3.24, 0.48, T("計算する海", "computed sea"), rotation=90, ha="center", va="center", fontsize=8, color="w")
    axs[0].text((I_WEIR - 0.5) * DX / 1000, 0.33, T("堰", "barrage"), color="red", ha="center", fontsize=9)
    axs[0].set_xlabel(T("x (km)  ← 上流   海 →", "x (km)  ← upstream   sea →"))
    axs[0].set_ylabel("y (km)")
    fig.colorbar(im, ax=axs[0], shrink=0.8).set_label(T("地盤高 (m)", "ground elevation (m)"))
    ax = axs[1]
    s = slice(0, 87)
    ax.fill_between(XK[s], ZBOT, z[JC, s], color="#e8d9b5",
                    label=T("帯水層(層1)", "aquifer (layer 1)"))
    ax.plot(XK[s], z[JC, s], "k-", lw=1.2, label=T("河床・海底", "river bed / sea floor"))
    ax.plot(XK[s], np.full(87, 3.0), color="0.4", lw=1, ls=":", label=T("陸の地盤高 +3 m", "land +3 m"))
    ax.plot([(I_WEIR - 0.5) * DX / 1000] * 2, [z[JC, I_WEIR - 1], 1.0], color="red", lw=3,
            label=T("堰の天端 +1.0 m", "barrage crest +1.0 m"))
    ax.axhspan(-0.6, 0.6, color="#9ecae1", alpha=0.4, label=T("潮位の幅 ±0.6 m", "tidal range ±0.6 m"))
    ax.axvline(X_MOUTH, color="k", lw=0.8)
    ax.set_ylim(-10.5, 4)
    ax.set_xlabel(T("x (km)  河口 = 3.0 km", "x (km)  mouth = 3.0 km"))
    ax.set_ylabel(T("標高 (m)", "elevation (m)"))
    ax.set_title(T("河道中心の縦断(行 12)", "Longitudinal section along the river centre (row 12)"), fontsize=10)
    ax.legend(fontsize=7, loc="lower left", ncol=2)
    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/setup.png", dpi=110)
    plt.close(fig)


def plan(k):
    fig, axs = plt.subplots(2, 2, figsize=(13, 5.6), constrained_layout=True)
    order = [CASES[0], CASES[1], CASES[2], CASES[3]]
    for ax, (case, lb, lx) in zip(axs.flat, order):
        name = base(case)
        _, sd = geo(name)
        hgs = load(case, "Hgs", k)
        hss = load(case, "Hss", k)
        frac = np.ma.masked_array(hgs / (sd * SY))
        frac[:, I_COAST:] = np.ma.masked
        im = ax.imshow(frac, extent=EXT, vmin=0, vmax=1, cmap="YlOrRd", aspect="equal")
        surf = np.ma.masked_less(hss, 0.05)
        surf[:, I_COAST:] = np.ma.masked
        ax.imshow(np.ma.masked_where(surf.mask, np.ones_like(hss)), extent=EXT,
                  cmap=ListedColormap(["#1f4e9c"]), alpha=0.75, aspect="equal")
        ax.axvline(X_MOUTH, color="k", lw=0.8)
        if name == "barrage":
            ax.plot([(I_WEIR - 0.5) * DX / 1000] * 2, [(JC - 1.5) * DX / 1000, (JC + 1.5) * DX / 1000],
                    color="lime", lw=3)
        vol = (hgs[:, :I_COAST] * DX * DX).sum() / 1e3
        ax.set_title(f"{lb} / {lx}  " + T(f"(陸側帯水層の塩水 {vol:.0f} 千 m³)",
                                          f"(salt in landward aquifer {vol:.0f}×10³ m³)"), fontsize=10)
        ax.set_xlabel(T("x (km)  ← 上流   海 →", "x (km)  ← upstream   sea →"))
        ax.set_ylabel("y (km)")
    cb = fig.colorbar(im, ax=axs, shrink=0.8)
    cb.set_label(T("帯水層厚に占める塩水の割合 Hgs/(sd·sy)", "salt fraction of aquifer thickness Hgs/(sd·sy)"))
    day = k * DT_FILE_H / 24
    fig.suptitle(T(f"{day:.0f} 日後: 帯水層の塩水(暖色)と河道の底層塩水 Hss > 0.05 m(青)。緑線 = 堰",
                   f"Day {day:.0f}: salt in the aquifer (warm colours) and bottom salt layer in the river Hss > 0.05 m (blue). Green line = barrage"),
                 fontsize=11)
    fig.savefig(f"{FIGDIR}/plan.png", dpi=110)
    plt.close(fig)


def profile(k):
    fig, axs = plt.subplots(2, 1, figsize=(11, 7), sharex=True, constrained_layout=True)
    for ax, case in zip(axs, ("nobarrage", "barrage")):
        z, sd = geo(case)
        z, sd = z[JC], sd[JC]
        e = load(case, "E", k)[JC]
        hss = load(case, "Hss", k)[JC]
        hgs = load(case, "Hgs", k)[JC]
        base = z - sd
        s = slice(0, I_COAST)
        ax.fill_between(XK[s], base[s], z[s], color="#e8d9b5", label=T("帯水層(河床下)", "aquifer (below bed)"))
        ax.fill_between(XK[s], base[s], base[s] + hgs[s] / SY, color="#c0392b", alpha=0.6,
                        label=T("帯水層の塩水 zone", "salt zone of the aquifer"))
        ax.fill_between(XK[s], z[s], z[s] + hss[s], color="#1f4e9c", alpha=0.7,
                        label=T("河道の底層塩水", "bottom salt layer in the river"))
        ax.fill_between(XK[s], z[s] + hss[s], e[s], color="#9ecae1", alpha=0.6,
                        label=T("河道の淡水", "fresh water in the river"))
        ax.plot(XK[s], z[s], "k-", lw=1)
        ax.set_ylim(-10.5, 2.5)
        ax.set_ylabel(T("標高 (m)", "elevation (m)"))
        title = T("堰なし", "No barrage") if case == "nobarrage" else T("堰あり", "Barrage")
        day = k * DT_FILE_H / 24
        ax.set_title(title + T(f": 河道中心の縦断({day:.0f} 日後・河床の塩水の出入りあり)",
                               f": section along the river centre (day {day:.0f}, with bed salt exchange)"), fontsize=10)
        ax.legend(loc="lower left", fontsize=8, ncol=4)
    axs[-1].set_xlabel(T("x (km)  ← 上流   河口(x = 3.0 km)→", "x (km)  ← upstream   mouth (x = 3.0 km) →"))
    fig.savefig(f"{FIGDIR}/profile.png", dpi=110)
    plt.close(fig)


def series():
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.2), constrained_layout=True)
    col = {"nobarrage": "#c0392b", "barrage": "#2c7fb8"}
    for case, lb, lx in CASES + MIXCASES:
        if not frames(case, "Hgs"):
            continue
        name = base(case)
        sty = "--" if case.endswith("_off") else (":" if case.endswith("_mix") else "-")
        fs = frames(case, "Hgs")
        t = np.arange(len(fs)) * DT_FILE_H / 24
        v = [(np.loadtxt(f)[:, :I_COAST] * DX * DX).sum() / 1e3 for f in fs]
        axs[0].plot(t, v, sty, color=col[name], label=f"{lb} / {lx}")
        if case in ("nobarrage", "barrage"):
            tips = [tip_km(np.loadtxt(f)) for f in frames(case, "Hss")]
            axs[1].plot(t, tips, "-", color=col[name], marker=".", ms=3, label=lb)
    for ax in axs:
        ax.axvspan(0, 2, color="0.9")
        ax.grid(alpha=0.3)
        ax.set_xlabel(T("経過日数", "days"))
    axs[0].set_ylabel(T("陸側帯水層の塩水量 (千 m³)", "salt in landward aquifer (10³ m³)"))
    axs[0].legend(fontsize=8, loc="center right", bbox_to_anchor=(0.99, 0.48))
    axs[0].text(1.0, axs[0].get_ylim()[1] * 0.5, T("出水+強雨", "flood + rain"), fontsize=8, ha="center",
                rotation=90)
    axs[1].axhline(X_MOUTH - (I_WEIR - 1) * DX / 1000, color="k", ls=":", lw=1)
    axs[1].text(19.8, X_MOUTH - (I_WEIR - 1) * DX / 1000 + 0.05, T("堰の位置", "barrage"), ha="right", fontsize=8)
    axs[1].set_ylabel(T("塩水くさびの先端の河口からの距離 (km)", "salt-wedge tip distance from mouth (km)"))
    axs[1].set_ylim(0, 3.1)
    axs[1].legend(fontsize=8)
    fig.savefig(f"{FIGDIR}/series.png", dpi=110)
    plt.close(fig)


def table(k):
    print(T("ケース, 陸側帯水層の塩水量(千 m³), 河床下の塩水の前線(割合 0.5)の河口からの距離 km, 堰位置より上流の河床下帯水層の塩水割合, 岸から 80 m 以内の塩水割合(同区間), くさび先端(最終 2 日の範囲 km), 河道の底層塩水量(最終 2 日の平均、千 m³)",
            "case, salt in landward aquifer (10^3 m3), distance of salt front below bed (fraction 0.5) from mouth km, salt fraction below bed upstream of barrage site, salt fraction within 80 m of banks (same reach), wedge tip range in last 2 days (km), bottom salt in river (mean over last 2 days, 10^3 m3)"))
    for case, lb, lx in CASES + MIXCASES:
        if not frames(case, "Hgs"):
            continue
        name = base(case)
        _, sd = geo(name)
        hgs = load(case, "Hgs", k)
        fr = hgs / (sd * SY)
        up = slice(0, I_WEIR - 1)
        bed = fr[JC - 1:JC + 2, up].mean()
        bank = np.r_[fr[JC - 3:JC - 1, up].ravel(), fr[JC + 2:JC + 4, up].ravel()].mean()
        idx = np.nonzero(fr[JC, :I_COAST] > 0.5)[0]
        front = X_MOUTH - idx.min() * DX / 1000.0 if len(idx) else 0.0
        fs = frames(case, "Hss")[-8:]
        tips = [tip_km(np.loadtxt(f)) for f in fs]
        surf = np.mean([(np.loadtxt(f)[:, :I_COAST] * DX * DX).sum() / 1e3 for f in fs])
        print(f"{case}, {(hgs[:, :I_COAST] * DX * DX).sum() / 1e3:.0f}, {front:.2f}, {bed:.3f}, {bank:.3f}, "
              f"{min(tips):.2f}-{max(tips):.2f}, {surf:.0f}")


if __name__ == "__main__":
    kl = min(int(frames(c, "Hgs")[-1][-8:-4]) for c, _, _ in CASES)
    mechanism()
    setup()
    plan(kl)
    profile(kl)
    series()
    table(kl)
