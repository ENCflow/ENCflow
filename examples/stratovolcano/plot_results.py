#!/usr/bin/env python3
"""examples/stratovolcano の図を figs/*.png に描き、形の数値を表示する(事前に make run)。

  python3 plot_results.py        # 引数 en で英語版を en/figs/ に

- figs/mechanism.png : 1 サイクルの 3 段の模式図(計算結果ではない)
- figs/setup.png     : 火口の位置、1 回の噴火の降灰の厚さ、噴火の列
- figs/volcano.png   : 3 ケースの最終の地形(陰影)と、方位平均の断面・勾配
- figs/section.png   : 山頂を通る東西断面の層序(溶岩・灰・再堆積、侵食面)
- figs/erosion.png   : 侵食と堆積の累計(P・L)と、サイクルごとの体積
"""
import csv
import math
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource
from matplotlib.patches import Patch

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)

# run_cycles.py と対で保守する定数
NX = NY = 100
DX = 50.0
IC = JC = 50
CASES = ["P", "L", "P0"]
CNAME = {"P": T("P: 火砕物の多い噴火 + 侵食", "P: pyroclast-rich eruptions + erosion"),
         "L": T("L: 溶岩の多い噴火 + 侵食", "L: lava-rich eruptions + erosion"),
         "P0": T("P0: P と同じ噴火、侵食なし", "P0: same eruptions as P, no erosion")}
CCOL = {"P": "C0", "L": "C3", "P0": "0.45"}

x = (np.arange(NX) + 0.5) * DX
X, Y = np.meshgrid(x, x)
R = np.hypot(X - (IC - 0.5) * DX, Y - (JC - 0.5) * DX)
KM = [x[0] / 1000 - DX / 2000, x[-1] / 1000 + DX / 2000]


def load(case):
    fn = f"result_{case}/surfaces.npz"
    if not os.path.exists(fn):
        return None
    s = dict(np.load(fn))
    n = len([k for k in s if k.startswith("zl")])
    led = list(csv.DictReader(open(f"result_{case}/ledger.csv")))
    return s, n, led


def radial(z, step=100.0, rmax=2500.0):
    rb = np.arange(0.0, rmax, step)
    return rb + step / 2, np.array([z[(R >= a) & (R < a + step)].mean() for a in rb])


def morph(z):
    """形の数値: 高さ(最高点)、方位平均の断面が高さの 10% まで下がる距離 R10、
    方位平均の断面の平均勾配(山頂から 0.1〜0.5 km・0.5〜1.0 km・1.0〜1.5 km)"""
    h = z.max()
    rr, pz = radial(z, step=50.0)
    r10 = float(rr[np.argmax(pz < 0.1 * h)])
    def mslope(a, b):
        za, zb = np.interp(a, rr, pz), np.interp(b, rr, pz)
        return math.degrees(math.atan((za - zb) / (b - a)))
    return h, r10, mslope(100.0, 500.0), mslope(500.0, 1000.0), mslope(1000.0, 1500.0)


def vexag(ax):
    """軸の縦の拡大率(横 1 m あたりの長さに対する縦 1 m あたりの長さの比)"""
    fig = ax.figure
    bb = ax.get_position()
    w, h = bb.width * fig.get_figwidth(), bb.height * fig.get_figheight()
    x0, x1 = ax.get_xlim(); y0, y1 = ax.get_ylim()
    return (h / (y1 - y0)) / (w / ((x1 - x0) * 1000.0))


data = {c: load(c) for c in CASES}

# ---------------------------------------------------------------- mechanism.png(模式図)
fig, axes = plt.subplots(1, 3, figsize=(15, 3.9))
xs = np.linspace(-1, 1, 400)
cone = 0.55 * np.exp(-np.abs(xs) / 0.35) - 0.05
for ax in axes:
    ax.fill_between(xs, -0.15, cone, color="0.80", lw=0)
    ax.plot(xs, cone, "0.4", lw=1)
    ax.set_xlim(-1, 1); ax.set_ylim(-0.15, 0.85); ax.axis("off")
ax = axes[0]
lava = np.where(np.abs(xs + 0.12) < 0.42, 0.07 * np.clip(1 - ((xs + 0.12) / 0.42) ** 2, 0, None) ** 0.3, 0)
ax.fill_between(xs, cone, cone + lava, color="firebrick", lw=0)
ax.fill_between(xs, cone - 0.03, cone, where=lava > 0, color="khaki", lw=0)
ax.annotate("", xy=(-0.42, 0.33), xytext=(-0.05, 0.56), arrowprops=dict(arrowstyle="->", color="firebrick"))
ax.text(0.0, 0.78, T("(1) 溶岩流: 火口から流れ出て止まり、固まる", "(1) lava flow: leaves the vent, stops and solidifies"), ha="center", fontsize=10)
ax.text(0.35, 0.40, T("下の灰は埋まって\n侵食されなくなる", "ash beneath is buried\nand no longer erodible"), fontsize=9)
ax = axes[1]
ash = 0.09 * np.exp(-np.abs(xs) / 0.3)
ax.fill_between(xs, cone, cone + ash, color="khaki", lw=0)
ax.plot(xs, cone + ash, color="goldenrod", lw=1)
for xx in (-0.15, 0.0, 0.15):
    ax.annotate("", xy=(xx, 0.62), xytext=(xx * 1.4, 0.74), arrowprops=dict(arrowstyle="->", color="0.5"))
ax.text(0.0, 0.78, T("(2) 降灰: 火口から離れるほど指数的に薄い", "(2) ashfall: thins exponentially away from the vent"), ha="center", fontsize=10)
ax.text(0.30, 0.38, T("灰 = 侵食できる層 sd\nT(r) = T0 exp(−r/b)", "ash = erodible layer sd\nT(r) = T0 exp(−r/b)"), fontsize=9)
ax = axes[2]
gul = -0.04 * np.exp(-((np.abs(xs) - 0.25) / 0.08) ** 2)
fan = 0.05 * np.exp(-((np.abs(xs) - 0.62) / 0.12) ** 2)
ax.fill_between(xs, cone + gul, cone + gul + fan, color="peru", lw=0)
ax.plot(xs, cone + gul + fan, color="saddlebrown", lw=1)
for xx in np.linspace(-0.7, 0.7, 8):
    ax.plot([xx, xx - 0.03], [0.70, 0.62], color="steelblue", lw=1)
ax.annotate("", xy=(0.66, 0.08), xytext=(0.30, 0.25), arrowprops=dict(arrowstyle="->", color="saddlebrown"))
ax.text(0.0, 0.78, T("(3) 豪雨: しみ込めない雨が灰を運ぶ", "(3) storms: rain that cannot infiltrate carries ash"), ha="center", fontsize=10)
ax.text(-0.95, 0.30, T("山腹を削り(谷)\n勾配の緩む麓に積もる", "erodes the flanks (gullies)\nand deposits where the slope eases"), fontsize=9)
fig.suptitle(T("1 サイクルの 3 段(模式図。計算結果ではない)。これを 10 回繰り返す",
               "The three stages of one cycle (schematic, not computed results), repeated 10 times"), fontsize=11)
fig.tight_layout()
fig.savefig(f"{FIGDIR}/mechanism.png", dpi=110)
plt.close(fig)

# ---------------------------------------------------------------- setup.png
if data["P"] is not None:
    s, n, led = data["P"]
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.4), gridspec_kw={"width_ratios": [1, 1.1, 1.2]})
    ax = axes[0]
    for row in led:
        i, j, k = int(row["vi"]), int(row["vj"]), int(row["cycle"])
        xe, yn = (i - IC) * DX, (JC - j) * DX
        mk = "^" if row["vent"] == "S" else "o"
        ax.scatter(xe, yn, s=60, marker=mk, c=[[k / n]], cmap="viridis", vmin=0, vmax=1, edgecolor="k", zorder=3)
        ax.annotate(str(k), (xe, yn), xytext=(4, 4), textcoords="offset points", fontsize=8)
    for rr in (600, 1000):
        th = np.linspace(0, 2 * np.pi, 200)
        ax.plot(rr * np.cos(th), rr * np.sin(th), "0.6", lw=0.8, ls="--")
    ax.set_aspect("equal"); ax.set_xlim(-1300, 1300); ax.set_ylim(-1300, 1300)
    ax.set_xlabel(T("東西 (m、山頂から)", "east–west (m from the summit)")); ax.set_ylabel(T("南北 (m)", "north–south (m)"))
    ax.set_title(T("(a) 火口(▲ 山頂、● 山腹。数字は噴火の順番。\n破線は山腹の火口の範囲 600〜1000 m)",
                   "(a) vents (▲ summit, ● flank; numbers = order;\ndashed = flank-vent range 600–1000 m)"), fontsize=9)
    ax.grid(alpha=0.3)
    ax = axes[1]
    rr = np.linspace(0, 2500, 300)
    for cs, col, lab in (("P", "C0", "P"), ("L", "C3", "L")):
        t0, b = (15.0, 400.0) if cs == "P" else (5.0, 300.0)
        ax.plot(rr, t0 * np.exp(-rr / b), color=col, label=T(f"{lab}: 山頂の噴火(T0 = {t0:.0f} m、b = {b:.0f} m)",
                                                           f"{lab}: summit eruption (T0 = {t0:.0f} m, b = {b:.0f} m)"))
        ax.plot(rr, 0.3 * t0 * np.exp(-rr / (0.5 * b)), color=col, ls="--", label=T(f"{lab}: 山腹の噴火", f"{lab}: flank eruption"))
    ax.set_yscale("log"); ax.set_ylim(1e-3, 30); ax.set_xlim(0, 2500)
    ax.set_xlabel(T("火口からの距離 (m)", "distance from the vent (m)")); ax.set_ylabel(T("灰の厚さ (m)", "ash thickness (m)"))
    ax.set_title(T("(b) 1 回の噴火の降灰の厚さ T(r) = T0 exp(−r/b)", "(b) ash thickness of one eruption, T(r) = T0 exp(−r/b)"), fontsize=9)
    ax.legend(fontsize=7.5); ax.grid(alpha=0.3, which="both")
    ax = axes[2]
    kk = np.arange(1, n + 1)
    for off, cs, col in ((-0.2, "P", "C0"), (0.2, "L", "C3")):
        if data[cs] is None:
            continue
        lv = [float(r["lava_m3"]) for r in data[cs][2]]
        av = [float(r["ash_m3"]) for r in data[cs][2]]
        ax.bar(kk + off - 0.1, np.array(lv) / 1e6, width=0.2, color=col, label=T(f"{cs}: 溶岩", f"{cs}: lava"))
        ax.bar(kk + off + 0.1, np.array(av) / 1e6, width=0.2, color=col, alpha=0.4, label=T(f"{cs}: 灰", f"{cs}: ash"))
    ax.set_xticks(kk); ax.set_xlabel(T("噴火(サイクル)", "eruption (cycle)")); ax.set_ylabel(T("体積 (10⁶ m³)", "volume (10⁶ m³)"))
    ax.set_title(T("(c) サイクルごとの溶岩と灰の体積(4〜6 は山腹の噴火)", "(c) lava and ash volume per cycle (4–6 are flank eruptions)"), fontsize=9)
    ax.set_ylim(0, 19)                      # 凡例が棒に重ならないよう上に余白
    ax.legend(fontsize=7.5, ncol=4, loc="upper center"); ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/setup.png", dpi=110)
    plt.close(fig)

# ---------------------------------------------------------------- volcano.png
avail = [c for c in CASES if data[c] is not None]
if avail:
    fig = plt.figure(figsize=(15, 9))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.15, 1])
    ls = LightSource(azdeg=315, altdeg=45)
    print(T("形の数値(高さ、断面が高さの 10% まで下がる距離 R10、山頂から 0.1〜0.5・0.5〜1.0・1.0〜1.5 km の平均勾配)",
            "Shape numbers (height, distance R10 where the profile falls to 10% of the height, mean slopes 0.1–0.5, 0.5–1.0, 1.0–1.5 km from the summit)"))
    for m, c in enumerate(CASES):
        ax = fig.add_subplot(gs[0, m])
        if data[c] is None:
            ax.axis("off")
            continue
        s, n, led = data[c]
        z = s[f"z{n:02d}"]
        rgb = ls.shade(z, cmap=plt.cm.terrain, vert_exag=2, dx=DX, dy=DX, blend_mode="soft",
                       vmin=-0.3 * max(z.max(), 50), vmax=1.05 * max(z.max(), 50))
        ax.imshow(rgb, origin="upper", extent=[KM[0], KM[1], KM[0], KM[1]])
        lev = np.arange(10, z.max(), 20)
        # 配列の先頭行が北端なので、行の座標は北から南へ減らす(X・Y を渡すと origin・extent は
        # 効かず、そのままでは陰影の図と南北が逆になる。2026-11-04 修正)
        ax.contour(x / 1000, x[::-1] / 1000, z, levels=lev, colors="k", linewidths=0.4)
        h, r10, s1, s2, s3 = morph(z)
        print(f"  {c}: H = {h:.0f} m, R10 = {r10 / 1000:.2f} km, slopes {s1:.1f} / {s2:.1f} / {s3:.1f} deg")
        ax.set_title("(" + "abc"[m] + ") " + CNAME[c] + T(f"\n高さ {h:.0f} m、等高線 20 m", f"\nheight {h:.0f} m, contours 20 m"), fontsize=9.5)
        ax.set_xlabel("km"); ax.set_ylabel("km")
    ax = fig.add_subplot(gs[1, 0:2])
    ax2 = fig.add_subplot(gs[1, 2])
    for c in avail:
        s, n, led = data[c]
        rr, pz = radial(s[f"z{n:02d}"])
        ax.plot(rr / 1000, pz, color=CCOL[c], lw=1.8, label=CNAME[c])
        sl = -np.gradient(pz, rr)
        ax2.plot(rr / 1000, np.degrees(np.arctan(sl)), color=CCOL[c], lw=1.5, label=c)
    ax.set_xlabel(T("山頂からの距離 (km)", "distance from the summit (km)")); ax.set_ylabel(T("地盤高(方位平均)(m)", "elevation, azimuthal mean (m)"))
    ax.set_xlim(0, 2.5); ax.grid(alpha=0.3); ax.legend(fontsize=9)
    fig.tight_layout()
    ve = vexag(ax)
    ax.set_title(T(f"(d) 方位平均の断面(縦は約 {ve:.0f} 倍に拡大)", f"(d) azimuthal-mean profiles (vertical exaggeration about {ve:.0f}×)"), fontsize=10)
    ax2.set_xlabel(T("山頂からの距離 (km)", "distance from the summit (km)")); ax2.set_ylabel(T("勾配 (°)", "slope (°)"))
    ax2.set_title(T("(e) 方位平均の断面の勾配", "(e) slope of the azimuthal-mean profile"), fontsize=10)
    ax2.set_xlim(0, 2.5); ax2.grid(alpha=0.3); ax2.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/volcano.png", dpi=110)
    plt.close(fig)

# ---------------------------------------------------------------- section.png(層序)
sec = [c for c in ("P", "L") if data[c] is not None]
if sec:
    fig, axes = plt.subplots(len(sec), 1, figsize=(13, 3.6 * len(sec)), squeeze=False)
    j = JC - 1
    for ax, c in zip(axes[:, 0], sec):
        s, n, led = data[c]
        zprev = s["z0"][j]
        for k in range(1, n + 1):
            zl, za, zk = s[f"zl{k:02d}"][j], s[f"za{k:02d}"][j], s[f"z{k:02d}"][j]
            lava_c = (0.72, 0.13, 0.10) if k % 2 else (0.45, 0.08, 0.06)
            ash_c = (0.98, 0.91, 0.52) if k % 2 else (0.90, 0.80, 0.38)
            xk = x / 1000
            # where による塗り分けは孤立した 1 セルを塗れない(2 点以上の連続が要る)ので、
            # 上下の面を挟み込んで全セルを塗る(何もないセルは厚さ 0)
            zl_ = np.maximum(zl, zprev)
            za_ = np.maximum(za, zl_)
            ax.fill_between(xk, zprev, zl_, color=lava_c, lw=0, step="mid")
            ax.fill_between(xk, zl_, za_, color=ash_c, lw=0, step="mid")
            ax.fill_between(xk, np.minimum(zk, za_), za_, color="white", lw=0, step="mid")
            ax.fill_between(xk, za_, np.maximum(zk, za_), color="peru", lw=0, step="mid")
            ax.step(xk, zk, "k-", lw=0.35, where="mid")
            zprev = zk
        ax.set_xlim(0.8, 4.2)
        ax.set_ylim(-5, s[f"z{n:02d}"][j].max() * 1.08)
        ax.set_ylabel(T("地盤高 (m)", "elevation (m)"))
        ax.grid(alpha=0.25)
    fig.tight_layout()
    for ax, c in zip(axes[:, 0], sec):
        ve = vexag(ax)
        ax.set_title(CNAME[c] + T(f"。山頂を通る東西断面(縦は約 {ve:.0f} 倍に拡大。線は各サイクルの終わりの地表)",
                                  f". East–west section through the summit (vertical exaggeration about {ve:.0f}×; lines = surface at the end of each cycle)"), fontsize=9.5)
    axes[-1, 0].set_xlabel(T("西 ← 東西の位置 (km) → 東", "west ← east–west position (km) → east"))
    axes[0, 0].legend(handles=[Patch(color=(0.72, 0.13, 0.10), label=T("溶岩(濃淡はサイクルの交互)", "lava (shades alternate by cycle)")),
                               Patch(color=(0.98, 0.91, 0.52), label=T("灰(降灰。濃淡はサイクルの交互)", "ash (fall deposit; shades alternate by cycle)")),
                               Patch(color="peru", label=T("豪雨で運ばれて積もった灰", "ash redeposited by storms"))],
                      fontsize=8.5, loc="upper right")
    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/section.png", dpi=110)
    plt.close(fig)

# ---------------------------------------------------------------- erosion.png
ero = [c for c in ("P", "L") if data[c] is not None]
if ero:
    fig, axes = plt.subplots(1, len(ero) + 1, figsize=(5.2 * (len(ero) + 1), 4.4))
    for ax, c in zip(axes, ero):
        s, n, led = data[c]
        dzc = sum(s[f"z{k:02d}"] - s[f"za{k:02d}"] for k in range(1, n + 1))
        im = ax.imshow(dzc, origin="upper", extent=[KM[0], KM[1], KM[0], KM[1]], cmap="RdBu", vmin=-10, vmax=10)
        ax.set_xlim(0.5, 4.5); ax.set_ylim(0.5, 4.5)
        ax.set_title(CNAME[c] + T("\n豪雨の段の地盤高の変化の累計 (m)(赤 侵食・青 堆積)",
                                  "\ncumulative change of the storm stages (m) (red erosion, blue deposition)"), fontsize=9)
        ax.set_xlabel("km"); ax.set_ylabel("km")
        fig.colorbar(im, ax=ax, shrink=0.85)
    ax = axes[-1]
    for c in ero:
        s, n, led = data[c]
        kk = np.array([int(r["cycle"]) for r in led])
        ash = np.array([float(r["ash_m3"]) for r in led])
        er = np.array([float(r["eroded_m3"]) for r in led])
        ax.plot(kk, 100 * er / ash, "o-", color=CCOL[c], label=T(f"{c}: 侵食量 / その回の降灰量", f"{c}: eroded / ash of that cycle"))
    ax.set_xlabel(T("サイクル", "cycle")); ax.set_ylabel("%")
    ax.set_title(T("各サイクルの豪雨の段で動いた灰(4〜6 は山腹の噴火で\n降灰が少ないので割合が大きい)",
                   "ash moved in each storm stage (4–6 are flank eruptions\nwith little ash, so the ratio is large)"), fontsize=9)
    ax.grid(alpha=0.3); ax.legend(fontsize=8.5)
    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/erosion.png", dpi=110)
    plt.close(fig)

# ---------------------------------------------------------------- 台帳の要約
for c in avail:
    s, n, led = data[c]
    lv = sum(float(r["erupted_m3"]) for r in led)
    fr = sum(float(r["molten_frozen_m3"]) for r in led)
    ash = sum(float(r["ash_m3"]) for r in led)
    bur = sum(float(r["ash_buried_m3"]) for r in led)
    er = sum(float(r["eroded_m3"]) for r in led)
    dep = sum(float(r["deposited_m3"]) for r in led)
    net = sum(float(r["net_m3"]) for r in led)
    ok = all(r["lava_check"] == "True" and r["burial_check"] == "True" for r in led)
    print(f"{c}: lava {lv:.3e} m3 (frozen at the end of lava stages {fr / lv:.1%}), ash {ash:.3e} m3 "
          f"(buried under lava {bur:.3e}), storms eroded {er:.3e} ({er / ash:.1%} of the ash), "
          f"deposited {dep:.3e}, left the domain {-net:.2e} m3; checks {'ok' if ok else 'FAIL'}")
