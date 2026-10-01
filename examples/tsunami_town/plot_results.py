#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# examples/tsunami_town の図化(result/ と result_* を読んで figs/ に保存)
#   figs/setup.png   : 地形・家屋ストック(木造率込み)・津波波形
#   figs/frames.png  : 浸水深 H と流動瓦礫 Bf の平面分布の時間発展(本体ケース)
#   figs/damage.png  : 家屋の破壊率 Bs(最終)の 4 ケース比較
#   figs/deposit.png : 瓦礫の最大到達量 Bd9999・最終堆積・荷重込み最大流体力 Fd9999・水のみ F9999
#   figs/ledger.png  : 材積台帳(bldgdebris.csv)の時系列(4 ケース)
#   figs/profile.png : 開口部の行の断面(水面の時間発展: 帰還あり/なし、破壊率、瓦礫)
#   末尾に README 用の数表を出力する
import os, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

NX, NY, DX = 120, 60, 10.0
A = DX * DX
EXT = (0, NX * DX, 0, NY * DX)
X = (np.arange(NX) + 0.5) * DX
Y = (np.arange(NY) + 0.5) * DX
I_WALL = (26, 27); J_OPEN = (25, 36); J_ROW = 30
I_TOWN = 28
TIDE = [(0, 0.0), (5, 0.0), (15, 4.0), (25, 4.0), (35, 0.0), (60, 0.0)]
CASES = [("result",         "base: depth criterion, feedback on",        "#2a78d6"),
         ("result_oneway",  "one-way: depth criterion, no feedback",     "#8a8983"),
         ("result_load",    "load criterion, feedback on",               "#2e9e5b"),
         ("result_load_dw", "load criterion + driftwood, feedback on",   "#eb6834")]
os.makedirs("figs", exist_ok=True)

def rd(rdir, name, k):
    return np.loadtxt("%s/%s%04d.txt" % (rdir, name, k))

def times(rdir):
    return {int(l.split(",")[0]): float(l.split(",")[2])
            for l in open(rdir + "/FILENUMBER.csv") if not l.startswith("#")}

def tide_curve(tmin):
    tt = np.array([p[0] for p in TIDE]); ee = np.array([p[1] for p in TIDE])
    return np.interp(tmin, tt, ee)

def draw_walls(ax, lw=0.8):
    x0, x1 = (I_WALL[0] - 1) * DX, I_WALL[1] * DX
    y0, y1 = (J_OPEN[0] - 1) * DX, J_OPEN[1] * DX
    ax.plot([x0, x0], [0, y0], "k-", lw=lw); ax.plot([x0, x0], [y1, NY * DX], "k-", lw=lw)
    ax.plot([x1, x1], [0, y0], "k-", lw=lw); ax.plot([x1, x1], [y1, NY * DX], "k-", lw=lw)
    ax.plot([x0, x1, x1, x0, x0], [y0, y0, y1, y1, y0], "k--", lw=lw)

z0 = np.loadtxt("z.txt"); gv = np.loadtxt("gv.txt"); stock = np.loadtxt("bdstock.txt"); frac = np.loadtxt("bdfrac.txt")
town = np.arange(1, NX + 1) >= I_TOWN
have = {r: os.path.exists(r + "/FILENUMBER.csv") for r, _, _ in CASES}
tm = times("result")
klast = max(k for k in tm if k < 9000)

# --- 1. 設定図 ---
fig, axes = plt.subplots(1, 3, figsize=(15, 3.8), gridspec_kw={"width_ratios": [1.4, 1.4, 1]})
im = axes[0].imshow(z0, origin="lower", extent=EXT, cmap="terrain", vmin=-6, vmax=6)
plt.colorbar(im, ax=axes[0], label="bed elevation z (m)", shrink=0.85)
draw_walls(axes[0], lw=1.2)
axes[0].text(75, 560, "sea\nz = -5 m", fontsize=7, ha="center", va="top"); axes[0].text(205, 40, "beach\n(timber)", fontsize=7, ha="center", va="bottom")
axes[0].text(730, 560, "town z = +0.5 to +3.0 m, gv = 0.6", fontsize=7, ha="center", va="top")
axes[0].set_title("terrain and seawall (+2.0 m, opening +0.5 m)", fontsize=9)
im = axes[1].imshow(np.where(stock > 0, stock, np.nan), origin="lower", extent=EXT, cmap="YlOrBr", vmin=0, vmax=0.3)
plt.colorbar(im, ax=axes[1], label="building stock (m3/m2)", shrink=0.85)
draw_walls(axes[1], lw=1.0)
axes[1].set_title("destructible building stock (wooden fraction 100% -> 40%)", fontsize=9)
t = np.linspace(0, 60, 601)
axes[2].plot(t, tide_curve(t), "b-", lw=1.8, label="sea level (tival)")
axes[2].axhline(2.0, color="k", lw=0.8, label="seawall crest +2.0 m"); axes[2].axhline(0.5, color="k", lw=0.8, ls="--", label="opening +0.5 m")
for k in sorted(tm):
    if k < 9000: axes[2].axvline(tm[k] / 60, color="0.85", lw=0.5)
axes[2].set_xlim(0, 60); axes[2].set_ylim(-0.5, 5); axes[2].set_xlabel("t (min)"); axes[2].set_ylabel("water level (m)")
axes[2].set_title("tsunami waveform (grey: frames)", fontsize=9); axes[2].grid(alpha=0.3); axes[2].legend(fontsize=7)
for ax in axes[:2]:
    ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
plt.tight_layout(); plt.savefig("figs/setup.png", dpi=100); plt.close()

# --- 2. 浸水深と流動瓦礫の時間発展(本体) ---
frames = [k for k in sorted(tm) if k < 9000 and tm[k] > 0][:6]
cmap = plt.get_cmap("YlOrBr").copy(); cmap.set_under("white")
fig, axes = plt.subplots(2, len(frames), figsize=(2.6 * len(frames), 5.2), sharex=True, sharey=True)
for col, k in enumerate(frames):
    h = rd("result", "H", k); bf = rd("result", "Bf", k)
    im0 = axes[0][col].imshow(np.where(h > 0.01, h, np.nan), origin="lower", extent=EXT, cmap="Blues", vmin=0, vmax=4)
    im1 = axes[1][col].imshow(bf, origin="lower", extent=EXT, cmap=cmap, vmin=0.002, vmax=0.2)
    axes[1][col].contour(X, Y, h, levels=[0.01], colors="royalblue", linewidths=0.6)
    for ax in (axes[0][col], axes[1][col]): draw_walls(ax)
    axes[0][col].set_title("t = %.0f min, sea %+.1f m" % (tm[k] / 60, tide_curve(tm[k] / 60)), fontsize=8)
    axes[1][col].set_xlabel("x (m)")
axes[0][0].set_ylabel("depth H (m)\ny (m)"); axes[1][0].set_ylabel("floating debris Bf (m3/m2)\ny (m)")
fig.colorbar(im0, ax=axes[0], shrink=0.8, pad=0.01); fig.colorbar(im1, ax=axes[1], shrink=0.8, pad=0.01, extend="min")
plt.savefig("figs/frames.png", dpi=100, bbox_inches="tight"); plt.close()

# --- 3. 破壊率の 4 ケース比較 ---
fig, axes = plt.subplots(2, 2, figsize=(13, 6.4), sharex=True, sharey=True)
for (rdir, lab, col), ax in zip(CASES, axes.flat):
    if not have[rdir]:
        ax.set_title(lab + " (not run)", fontsize=9); continue
    bs = rd(rdir, "Bs", klast)
    im = ax.imshow(np.where(stock > 0, bs, np.nan), origin="lower", extent=EXT, cmap="Reds", vmin=0, vmax=1)
    draw_walls(ax, lw=1.0)
    vol = (bs * stock * A).sum()
    ax.set_title("%s\ndestroyed %6.0f m3 (%.0f%% of stock)" % (lab, vol, 100 * vol / (stock * A).sum()), fontsize=9)
for ax in axes[-1]: ax.set_xlabel("x (m)")
for ax in axes[:, 0]: ax.set_ylabel("y (m)")
fig.colorbar(im, ax=axes, label="destroyed fraction Bs (final)", shrink=0.7)
plt.savefig("figs/damage.png", dpi=100, bbox_inches="tight"); plt.close()

# --- 4. 到達・堆積・流体力(本体) ---
fig, axes = plt.subplots(2, 2, figsize=(13, 6.4), sharex=True, sharey=True)
panels = [("Bd", 9999, "max arrival Bd9999 = max(floating + deposited) (m3/m2)", cmap, 0.002, 0.3),
          ("Bd", klast, "final deposit Bd (m3/m2)", cmap, 0.002, 0.3),
          ("Fd", 9999, "max fluid force incl. debris Fd9999 (m3/s2)", plt.get_cmap("magma"), 0.0, 8.0),
          ("F", 9999, "max fluid force, water only F9999 (m3/s2)", plt.get_cmap("magma"), 0.0, 8.0)]
for (nm, k, ttl, cm, v0, v1), ax in zip(panels, axes.flat):
    a = rd("result", nm, k)
    im = ax.imshow(a, origin="lower", extent=EXT, cmap=cm, vmin=v0, vmax=v1)
    draw_walls(ax, lw=1.0); plt.colorbar(im, ax=ax, shrink=0.9, extend="max"); ax.set_title(ttl, fontsize=9)
for ax in axes[-1]: ax.set_xlabel("x (m)")
for ax in axes[:, 0]: ax.set_ylabel("y (m)")
plt.tight_layout(); plt.savefig("figs/deposit.png", dpi=100); plt.close()

# --- 5. 材積台帳 ---
fig, axes = plt.subplots(1, 2, figsize=(13, 4))
for rdir, lab, col in CASES:
    if not have[rdir]: continue
    d = np.loadtxt(rdir + "/bldgdebris.csv", delimiter=",", skiprows=1)
    axes[0].plot(d[:, 0] / 60, d[:, 6], color=col, lw=1.6, label=lab)
    axes[1].plot(d[:, 0] / 60, d[:, 7], color=col, lw=1.6, ls="-", label=lab + " (floating)")
    axes[1].plot(d[:, 0] / 60, d[:, 8], color=col, lw=1.0, ls="--")
ax2 = axes[0].twinx(); ax2.plot(t, tide_curve(t), "b-", lw=0.8, alpha=0.5); ax2.set_ylim(-0.5, 5); ax2.set_ylabel("sea level (m)", color="b")
axes[0].set_ylabel("remaining building stock (m3)"); axes[1].set_ylabel("debris volume (m3): floating (solid), deposited (dashed)")
for ax in axes:
    ax.set_xlim(0, 60); ax.set_xlabel("t (min)"); ax.grid(alpha=0.3); ax.legend(fontsize=7)
plt.tight_layout(); plt.savefig("figs/ledger.png", dpi=100); plt.close()

# --- 6. 開口部の行の断面 ---
j = J_ROW - 1
fig, axes = plt.subplots(2, 1, figsize=(11, 6.4), sharex=True)
ax = axes[0]
ax.fill_between(X, -6, z0[j], color="0.85"); ax.plot(X, z0[j], "k-", lw=1)
for k, c in zip(frames, ("#c6dbef", "#9ecae1", "#6baed6", "#3182bd", "#08519c", "#54278f")):
    h = rd("result", "H", k)[j]
    ax.plot(X, np.where(h > 0.01, z0[j] + h, np.nan), color=c, lw=1.2, label="feedback on, t = %.0f min" % (tm[k] / 60))
    if have["result_oneway"]:
        h2 = rd("result_oneway", "H", k)[j]
        ax.plot(X, np.where(h2 > 0.01, z0[j] + h2, np.nan), color=c, lw=0.8, ls=":")
ax.set_ylim(-5.5, 6); ax.set_ylabel("elevation (m)"); ax.grid(alpha=0.3); ax.legend(fontsize=7, ncol=3)
ax.set_title("water surface along the opening row (y = %.0f m). dotted: no feedback" % ((J_ROW - 0.5) * DX), fontsize=10)
ax = axes[1]
for rdir, lab, col in CASES:
    if not have[rdir]: continue
    ax.plot(X, rd(rdir, "Bs", klast)[j], color=col, lw=1.4, label="Bs " + lab)
ax.plot(X, rd("result", "Bd", 9999)[j] / 0.3, "k--", lw=1.0, label="Bd9999 / 0.3 (base)")
ax.set_ylim(0, 1.05); ax.set_ylabel("destroyed fraction / scaled debris"); ax.set_xlabel("x (m)"); ax.grid(alpha=0.3); ax.legend(fontsize=7)
plt.tight_layout(); plt.savefig("figs/profile.png", dpi=100); plt.close()

# --- 数表 ---
total = (stock * A).sum()
print("building stock %.0f m3 (town cells %d)" % (total, town.sum() * NY))
print("%-42s %9s %7s %9s %9s %9s %8s %8s" % ("case", "destroyed", "ratio", "deposit", "afloat", "outflow", "reach", "Hmax"))
for rdir, lab, col in CASES:
    if not have[rdir]: continue
    d = np.loadtxt(rdir + "/bldgdebris.csv", delimiter=",", skiprows=1)[-1]
    bm = rd(rdir, "Bd", 9999); hm = rd(rdir, "H", 9999)
    reach = X[town][(bm[:, town] > 0.01).any(axis=0)].max() if (bm[:, town] > 0.01).any() else 0.0
    out = total - d[6] - d[7] - d[8]
    print("%-42s %9.0f %6.1f%% %9.0f %9.0f %9.0f %6.0f m %6.2f m"
          % (lab, total - d[6], 100 * (total - d[6]) / total, d[8], d[7], out, reach, hm[:, town].max()))
    if rdir == "result":
        bs = rd(rdir, "Bs", klast)
        for a, b in ((270, 500), (500, 800), (800, 1200)):
            m = (X > a) & (X < b)
            print("   town x %4d-%4d m: destroyed %6.0f m3 of %6.0f" % (a, b, (bs * stock * A)[:, m].sum(), (stock * A)[:, m].sum()))
print("figs/setup.png figs/frames.png figs/damage.png figs/deposit.png figs/ledger.png figs/profile.png")
