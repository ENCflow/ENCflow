#!/usr/bin/env python3
"""estuary_barrage の図と数表(事前に make run で 4 ケースを計算しておく)。

  figs/setup.png    地形(平面)と河道中心の縦断(堰・帯水層底・潮位の幅)
  figs/plan.png     20 日後の平面: 帯水層に占める塩水の割合と河道の底層塩水(4 ケース)
  figs/profile.png  20 日後の河道中心の縦断(河床の塩水交換あり、堰なし・あり)
  figs/series.png   帯水層の塩水量と塩水くさびの先端位置の時間変化
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
CASES = [("nobarrage_off", T("堰なし", "No barrage"), T("河床の塩水交換なし", "no bed salt exchange")),
         ("nobarrage", T("堰なし", "No barrage"), T("河床の塩水交換あり", "with bed salt exchange")),
         ("barrage_off", T("堰あり", "Barrage"), T("河床の塩水交換なし", "no bed salt exchange")),
         ("barrage", T("堰あり", "Barrage"), T("河床の塩水交換あり", "with bed salt exchange"))]
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
        name = case.replace("_off", "")
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
        ax.set_title(title + T(f": 河道中心の縦断({day:.0f} 日後・河床の塩水交換あり)",
                               f": section along the river centre (day {day:.0f}, with bed salt exchange)"), fontsize=10)
        ax.legend(loc="lower left", fontsize=8, ncol=4)
    axs[-1].set_xlabel(T("x (km)  ← 上流   河口(x = 3.0 km)→", "x (km)  ← upstream   mouth (x = 3.0 km) →"))
    fig.savefig(f"{FIGDIR}/profile.png", dpi=110)
    plt.close(fig)


def series():
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.2), constrained_layout=True)
    sty = {"_off": "--", "": "-"}
    col = {"nobarrage": "#c0392b", "barrage": "#2c7fb8"}
    for case, lb, lx in CASES:
        name = case.replace("_off", "")
        fs = frames(case, "Hgs")
        t = np.arange(len(fs)) * DT_FILE_H / 24
        v = [(np.loadtxt(f)[:, :I_COAST] * DX * DX).sum() / 1e3 for f in fs]
        axs[0].plot(t, v, sty["_off" if case.endswith("_off") else ""], color=col[name], label=f"{lb} / {lx}")
        if not case.endswith("_off"):
            tips = [tip_km(np.loadtxt(f)) for f in frames(case, "Hss")]
            axs[1].plot(t, tips, "-", color=col[name], marker=".", ms=3, label=lb)
    for ax in axs:
        ax.axvspan(0, 2, color="0.9")
        ax.grid(alpha=0.3)
        ax.set_xlabel(T("経過日数", "days"))
    axs[0].set_ylabel(T("陸側帯水層の塩水量 (千 m³)", "salt in landward aquifer (10³ m³)"))
    axs[0].legend(fontsize=8, loc="upper left", bbox_to_anchor=(0.12, 0.99))
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
    print(T("ケース, 陸側帯水層の塩水量(千 m³), 堰位置より上流の河床下帯水層の塩水割合, 岸から 80 m 以内の塩水割合(同区間), くさび先端(最終 2 日の範囲 km)",
            "case, salt in landward aquifer (10^3 m3), salt fraction below bed upstream of barrage site, salt fraction within 80 m of banks (same reach), wedge tip range in last 2 days (km)"))
    for case, lb, lx in CASES:
        name = case.replace("_off", "")
        _, sd = geo(name)
        hgs = load(case, "Hgs", k)
        fr = hgs / (sd * SY)
        up = slice(0, I_WEIR - 1)
        bed = fr[JC - 1:JC + 2, up].mean()
        bank = np.r_[fr[JC - 3:JC - 1, up].ravel(), fr[JC + 2:JC + 4, up].ravel()].mean()
        fs = frames(case, "Hss")[-8:]
        tips = [tip_km(np.loadtxt(f)) for f in fs]
        print(f"{case}, {(hgs[:, :I_COAST] * DX * DX).sum() / 1e3:.0f}, {bed:.3f}, {bank:.3f}, "
              f"{min(tips):.2f}-{max(tips):.2f}")


if __name__ == "__main__":
    kl = min(int(frames(c, "Hgs")[-1][-8:-4]) for c, _, _ in CASES)
    setup()
    plan(kl)
    profile(kl)
    series()
    table(kl)
