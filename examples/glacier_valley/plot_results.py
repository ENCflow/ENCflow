#!/usr/bin/env python3
"""examples/glacier_valley の図を描く(事前に make run、湖の段は make run-lakes)。

  python3 plot_results.py        # figs/*.png(引数 en で英語版を en/figs/ に)

- figs/setup.png   : 初期地形(陰影・等高線・平衡線・断面の位置)と初期の横断形
- figs/glacier.png : 氷期の段の終わりの氷厚、侵食量の分布、氷の体積と最大の侵食の時間変化
- figs/valley.png  : 谷の横断形(3 か所)と、主谷・支谷の谷底の縦断形(初期と氷期の後)
- figs/lakes.png   : 湖の段の水深(result_lakes がある場合)
定数は make_terrain.py・param_*.txt と対で保守する。
"""
import glob
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LightSource

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)

NX, NY, DX = 120, 40, 200.0          # make_terrain.py と同じ
XT = 11000.0                          # 支谷の軸 (m)
ELA = 2680.0                          # param_glacial.txt の平衡線 (m)
YRS_PER_OUT = 1000.0                  # param_glacial.txt の出力間隔(地形時間の年)
XSEC = [6000.0, 12000.0, 18000.0]     # 横断形を描く x (m)
RES = "result_glacial"
x = (np.arange(NX) + 0.5) * DX
y = (np.arange(NY) + 0.5) * DX
ext = [0, NX * DX / 1000, NY * DX / 1000, 0]
ls = LightSource(azdeg=315, altdeg=45)
JC = [NY // 2 - 1, NY // 2]           # 主谷の谷底の 2 行(0 始まり)
IT = [int(XT / DX) - 1, int(XT / DX)]  # 支谷の谷底の 2 列


def ld(name, res=RES):
    return np.loadtxt(os.path.join(res, name))


def outputs(res=RES):
    nums = sorted(int(os.path.basename(f)[1:5]) for f in glob.glob(os.path.join(res, "Z0*.txt")))
    return [n for n in nums if n < 9998]


def col(xm):
    return int(xm / DX)


nums = outputs()
last = nums[-1]
z0 = ld("Z0000.txt")
z1 = ld(f"Z{last:04d}.txt")
hi = ld(f"Hi{last:04d}.txt")
yr_last = last * YRS_PER_OUT

# ---------------------------------------------------------------- setup.png
fig, axes = plt.subplots(1, 2, figsize=(15, 4.6), gridspec_kw={"width_ratios": [2.4, 1]})
ax = axes[0]
ax.imshow(ls.hillshade(z0, vert_exag=2, dx=DX, dy=DX), cmap="gray", extent=ext)
cs = ax.contour(x / 1000, y / 1000, z0, levels=np.arange(1600, 4400, 200), colors="k", linewidths=0.35)
ax.clabel(cs, levels=cs.levels[::2], fontsize=6, fmt="%d")
ax.contour(x / 1000, y / 1000, z0, levels=[ELA], colors="C0", linewidths=1.6)
for xm in XSEC:
    ax.axvline(xm / 1000, color="C3", lw=0.9, ls="--")
    ax.text(xm / 1000 + 0.1, 7.7, f"x = {xm/1000:.0f} km", color="C3", fontsize=8)
ax.text(1.0, 4.2, T("主谷", "main valley"), fontsize=9, color="k")
ax.text(XT / 1000 + 0.3, 1.0, T("支谷", "tributary"), fontsize=9, color="k")
ax.set_xlabel("x (km)"); ax.set_ylabel(T("y (km)  北 ↑", "y (km)  north ↑"))
ax.set_title(T(f"初期地形(川の V 字谷と支谷)。青線 = 平衡線 {ELA:.0f} m(これより上で雪が積もる)",
               f"Initial terrain (fluvial V-shaped valley and tributary). Blue = equilibrium line {ELA:.0f} m (snow accumulates above it)"),
             fontsize=10)
ax = axes[1]
for xm, c in zip(XSEC, ["C0", "C1", "C2"]):
    k = col(xm)
    ax.plot(y / 1000, z0[:, k], "-", color=c, lw=1.3, drawstyle="steps-mid", label=f"x = {xm/1000:.0f} km")
ax.axhline(ELA, color="C0", lw=0.8, ls=":")
ax.set_xlabel(T("y (km)  北 ← → 南", "y (km)  north ← → south")); ax.set_ylabel(T("標高 (m)", "elevation (m)"))
ax.set_title(T("初期の横断形", "Initial cross-sections"), fontsize=10)
ax.legend(fontsize=8); ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(f"{FIGDIR}/setup.png", dpi=100)
plt.close(fig)

# ---------------------------------------------------------------- glacier.png
fig = plt.figure(figsize=(15, 8))
ax = fig.add_subplot(2, 2, 1)
ax.imshow(ls.hillshade(z1, vert_exag=2, dx=DX, dy=DX), cmap="gray", extent=ext)
im = ax.imshow(np.ma.masked_less(hi, 1.0), cmap="Blues", alpha=0.85, extent=ext, vmin=0)
fig.colorbar(im, ax=ax, shrink=0.8, label=T("氷厚 (m)", "ice thickness (m)"))
ax.set_title(T(f"(a) 氷期の段の終わり({yr_last:.0f} 年)の氷河", f"(a) Glacier at the end of the glacial stage ({yr_last:.0f} years)"), fontsize=10)
ax.set_xlabel("x (km)"); ax.set_ylabel("y (km)")
ax = fig.add_subplot(2, 2, 2)
dz = z1 - z0
im = ax.imshow(dz, cmap="Reds_r", extent=ext, vmax=0, interpolation="nearest")
fig.colorbar(im, ax=ax, shrink=0.8, label=T("地盤の変化 (m)", "bed change (m)"))
ax.contour(x / 1000, y / 1000, hi, levels=[1.0], colors="C0", linewidths=0.8)
ax.set_title(T(f"(b) 侵食量(最大 {-dz.min():.0f} m)。青線 = 氷河の範囲", f"(b) Erosion (max {-dz.min():.0f} m). Blue = glacier extent"), fontsize=10)
ax.set_xlabel("x (km)"); ax.set_ylabel("y (km)")
ax = fig.add_subplot(2, 2, 3)
tyr, vol, emax, term = [], [], [], []
for n in nums:
    h = ld(f"Hi{n:04d}.txt"); z = ld(f"Z{n:04d}.txt")
    tyr.append(n * YRS_PER_OUT); vol.append(h.sum() * DX * DX / 1e9); emax.append(-(z - z0).min())
    a = h[JC].mean(axis=0); ice = np.where(a > 5.0)[0]
    term.append((ice.max() + 0.5) * DX / 1000 if ice.size else 0.0)
ax.plot(tyr, vol, "C0-o", ms=4, label=T("氷の体積 (km³)", "ice volume (km³)"))
ax.set_xlabel(T("地形時間 (年)", "landform time (years)")); ax.set_ylabel(T("氷の体積 (km³)", "ice volume (km³)"), color="C0")
ax2 = ax.twinx()
ax2.plot(tyr, emax, "C3-s", ms=4)
ax2.set_ylabel(T("最大の侵食 (m)", "maximum erosion (m)"), color="C3")
ax.set_title(T("(c) 氷の体積と最大の侵食の時間変化", "(c) Ice volume and maximum erosion through time"), fontsize=10)
ax.grid(alpha=0.3)
ax = fig.add_subplot(2, 2, 4)
ax.plot(tyr, term, "k-o", ms=4)
ax.set_xlabel(T("地形時間 (年)", "landform time (years)")); ax.set_ylabel(T("主谷の氷河の末端 x (km)", "terminus of the main glacier, x (km)"))
ax.set_ylim(0, NX * DX / 1000)
ax.set_title(T("(d) 主谷の氷河の末端の位置", "(d) Position of the main glacier terminus"), fontsize=10)
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(f"{FIGDIR}/glacier.png", dpi=100)
plt.close(fig)

# ---------------------------------------------------------------- valley.png
fig = plt.figure(figsize=(15, 8.5))
for k, xm in enumerate(XSEC):
    ax = fig.add_subplot(2, 3, k + 1)
    c = col(xm)
    base = z0[:, c].min()
    ax.plot(y / 1000, z0[:, c] - base, "k--", lw=0.9, drawstyle="steps-mid", label=T("初期(川の谷)", "initial (fluvial valley)"))
    ax.plot(y / 1000, z1[:, c] - base, "C3-", lw=1.5, drawstyle="steps-mid", label=T(f"{yr_last:.0f} 年後の地盤", f"bed after {yr_last:.0f} years"))
    m = hi[:, c] > 1.0
    if m.any():
        ax.plot(y[m] / 1000, (z1 + hi)[m, c] - base, "C0:", lw=1.2, label=T("氷面", "ice surface"))
    ax.set_xlim(1.5, 6.5); ax.set_ylim(-200, 800)
    ax.set_xlabel("y (km)"); ax.set_ylabel(T("初期の谷底からの高さ (m)", "height above the initial floor (m)"))
    ax.set_title(T(f"({'abc'[k]}) 横断形 x = {xm/1000:.0f} km", f"({'abc'[k]}) Cross-section x = {xm/1000:.0f} km"), fontsize=10)
    ax.grid(alpha=0.3)
    if k == 0:
        ax.legend(fontsize=8, loc="upper center")
ax = fig.add_subplot(2, 1, 2)
main0 = z0[JC].mean(axis=0); main1 = z1[JC].mean(axis=0); mice = (z1 + hi)[JC].mean(axis=0)
ax.plot(x / 1000, main0, "k--", lw=0.9, label=T("主谷の谷底(初期)", "main valley floor (initial)"))
ax.plot(x / 1000, main1, "C3-", lw=1.6, label=T(f"主谷の谷底({yr_last:.0f} 年後)", f"main valley floor (after {yr_last:.0f} years)"))
mm = hi[JC].mean(axis=0) > 1.0
ax.plot(x[mm] / 1000, mice[mm], "C0:", lw=1.2, label=T("主谷の氷面", "ice surface, main valley"))
# 支谷の谷底を、北の端からの距離ではなく x 方向の合流点の位置にそろえて描く(合流点 = 縦の点線)
jt = np.arange(0, JC[0] + 1)
t0 = z0[:, IT].mean(axis=1)[jt]; t1 = z1[:, IT].mean(axis=1)[jt]
xs = XT / 1000 - (JC[0] - jt) * DX / 1000      # 合流点から北へ離れるほど左へ(見やすさのため)
ax.plot(xs, t0, "--", color="0.5", lw=0.9, label=T("支谷の谷底(初期。合流点から北への距離を左向きに)", "tributary floor (initial; distance north of the confluence plotted leftwards)"))
ax.plot(xs, t1, "C2-", lw=1.6, label=T(f"支谷の谷底({yr_last:.0f} 年後)", f"tributary floor (after {yr_last:.0f} years)"))
ax.axvline(XT / 1000, color="k", lw=0.5, ls=":")
step = t1[-1] - main1[col(XT)]
ax.annotate(T(f"合流点の段 {step:.0f} m", f"step at the confluence {step:.0f} m"),
            xy=(XT / 1000, main1[col(XT)]), xytext=(XT / 1000 + 1.5, main1[col(XT)] + 250),
            arrowprops=dict(arrowstyle="->"), fontsize=9)
ax.set_xlabel("x (km)"); ax.set_ylabel(T("標高 (m)", "elevation (m)"))
ax.set_title(T("(d) 谷底の縦断形(主谷と支谷)", "(d) Long profiles of the valley floors (main valley and tributary)"), fontsize=10)
ax.legend(fontsize=7.5, loc="upper right"); ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(f"{FIGDIR}/valley.png", dpi=100)
plt.close(fig)

# ---------------------------------------------------------------- lakes.png
if os.path.isdir("result_lakes"):
    zl = ld("Z0000.txt", "result_lakes")
    hfiles = sorted(glob.glob("result_lakes/H0*.txt"))
    hl = np.loadtxt(hfiles[-1])
    fig, axes = plt.subplots(1, 2, figsize=(15, 4.6), gridspec_kw={"width_ratios": [2.4, 1]})
    ax = axes[0]
    ax.imshow(ls.hillshade(zl, vert_exag=2, dx=DX, dy=DX), cmap="gray", extent=ext)
    im = ax.imshow(np.ma.masked_less(hl, 0.5), cmap="Blues", extent=ext, vmin=0, interpolation="nearest")
    fig.colorbar(im, ax=ax, shrink=0.8, label=T("水深 (m)", "water depth (m)"))
    ax.set_title(T("氷が消えた後の雨で、深く削られた所に残る水(湖)", "Water left in the deeply eroded places after the ice is gone (lakes)"), fontsize=10)
    ax.set_xlabel("x (km)"); ax.set_ylabel("y (km)")
    ax = axes[1]
    ax.plot(x / 1000, zl[JC].mean(axis=0), "C3-", lw=1.4, label=T("谷底", "valley floor"))
    w = hl[JC].mean(axis=0)
    ax.fill_between(x / 1000, zl[JC].mean(axis=0), zl[JC].mean(axis=0) + w, where=w > 0.5, color="C0", alpha=0.6, label=T("湖", "lake"))
    ax.set_xlabel("x (km)"); ax.set_ylabel(T("標高 (m)", "elevation (m)"))
    ax.set_title(T("主谷の縦断形と湖", "Main valley long profile and lakes"), fontsize=10)
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/lakes.png", dpi=100)
    plt.close(fig)

print(f"figures written to {FIGDIR}/ (glacial stage output {last}, {yr_last:.0f} years)")
