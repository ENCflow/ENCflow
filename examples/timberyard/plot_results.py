#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# examples/timberyard の図化(result/ を読んで figs/ に保存)
#   figs/setup.png   : 地形・材木ストックの配置と高潮ハイドログラフ(流失開始・越流の水位)
#   figs/frames.png  : 流動材木 Hd の平面分布の時間発展(浸水範囲の輪郭つき)
#   figs/deposit.png : 最大到達量 Wd9999・最終堆積 Wd9998・最大流速 V9999・最大流体力 F9999
#   figs/ledger.png  : 材積台帳(driftwood.csv)の時系列と高潮水位
#   figs/profile.png : 開口部の行と防潮壁の行の断面(水面の時間発展と堆積柱状量)
#   末尾に README 用の数表(ゾーン別堆積量・到達距離・ピーク値)を出力する
import os, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

NX, NY, DX = 120, 60, 10.0
A = DX * DX
EXT = (0, NX * DX, 0, NY * DX)          # imshow の extent (m)
X = (np.arange(NX) + 0.5) * DX          # セル中心
I_YARD = (16, 35)                        # 貯木場のセル番号(1 始まり)
I_WALL = (36, 37)                        # 岸壁・防潮壁
J_OPEN = (25, 36)                        # 開口部の行
J_ROW_OPEN, J_ROW_WALL = 30, 10          # 断面図に使う行(1 始まり)
TIDE = [(0, 0.0), (60, 1.0), (150, 3.5), (180, 3.5), (240, 0.5)]   # param.txt の tival (min, m)
Z_OPEN, Z_WALL, Z_YARD = 0.5, 1.5, -2.0
DW_HREC = 3.0                            # param.txt の dw_hrec(流失の水深閾値)
os.makedirs("figs", exist_ok=True)

def rd(name, k):
    return np.loadtxt("result/%s%04d.txt" % (name, k))

def times():
    return {int(l.split(",")[0]): float(l.split(",")[2])
            for l in open("result/FILENUMBER.csv") if not l.startswith("#")}

def zones(x1):
    return {"harbor": (x1 >= 2) & (x1 <= 15), "yard": (x1 >= I_YARD[0]) & (x1 <= I_YARD[1]),
            "wall": (x1 >= I_WALL[0]) & (x1 <= I_WALL[1]), "town": x1 >= 38}

def draw_walls(ax, lw=0.8):
    """防潮壁の位置(x = 350〜370 m)と開口部を描く"""
    x0, x1 = (I_WALL[0] - 1) * DX, I_WALL[1] * DX
    y0, y1 = (J_OPEN[0] - 1) * DX, J_OPEN[1] * DX
    ax.plot([x0, x0], [0, y0], "k-", lw=lw); ax.plot([x0, x0], [y1, NY * DX], "k-", lw=lw)
    ax.plot([x1, x1], [0, y0], "k-", lw=lw); ax.plot([x1, x1], [y1, NY * DX], "k-", lw=lw)
    ax.plot([x0, x1, x1, x0, x0], [y0, y0, y1, y1, y0], "k--", lw=lw)

def tide_curve(tmin):
    tt = np.array([p[0] for p in TIDE]); ee = np.array([p[1] for p in TIDE])
    return np.interp(tmin, tt, ee)

tm = times()
z0 = rd("Z", 0); gv = np.loadtxt("gv.txt"); stock = np.loadtxt("stock.txt")
x1 = np.arange(1, NX + 1); zn = zones(x1)

# --- 1. 設定図(地形+ストック / 高潮ハイドログラフ) ---
fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(13, 4.2), gridspec_kw={"width_ratios": [1.5, 1]})
im = ax0.imshow(z0, origin="lower", extent=EXT, cmap="terrain", vmin=-4, vmax=4)
plt.colorbar(im, ax=ax0, label="bed elevation z (m)", shrink=0.85)
ax0.contour(X, (np.arange(NY) + 0.5) * DX, stock, levels=[0.25], colors="saddlebrown", linewidths=1.5)
draw_walls(ax0, lw=1.2)
ax0.text(5, 300, "sea\ncolumn\n(tide)", fontsize=7, rotation=90, va="center", ha="left")
ax0.text(80, 560, "harbor\nz = -3 m", fontsize=7, ha="center", va="top")
ax0.text(250, 560, "log yard z = -2 m\nstock 0.5 m3/m2", fontsize=7, ha="center", va="top", color="saddlebrown")
ax0.text(392, 470, "seawall +1.5 m", fontsize=7, rotation=90, ha="center", va="center")
ax0.text(400, 305, "opening +0.5 m", fontsize=7, ha="left", va="center")
ax0.text(780, 540, "town (z = +0.5 to +2.0 m, gv = 0.6)", fontsize=8, ha="center")
ax0.set_xlabel("x (m)"); ax0.set_ylabel("y (m)"); ax0.set_title("terrain, timber stock (brown outline) and seawall", fontsize=10)
t = np.linspace(0, 240, 481)
ax1.plot(t, tide_curve(t), "b-", lw=1.8, label="sea level (tival)")
ax1.axhline(Z_WALL, color="k", lw=0.8, ls="-", label="seawall crest +1.5 m")
ax1.axhline(Z_OPEN, color="k", lw=0.8, ls="--", label="opening crest +0.5 m")
ax1.axhline(DW_HREC + Z_YARD, color="saddlebrown", lw=1.2, ls=":", label="release level dw_hrec + z_yard = +1.0 m")
for k in range(1, 9):
    ax1.axvline(tm[k] / 60, color="0.8", lw=0.5)
ax1.set_xlim(0, 240); ax1.set_ylim(-0.5, 4); ax1.set_xlabel("t (min)"); ax1.set_ylabel("water level (m)")
ax1.set_title("storm surge hydrograph (grey: output frames)", fontsize=10); ax1.grid(alpha=0.3); ax1.legend(fontsize=7, loc="upper left")
plt.tight_layout(); plt.savefig("figs/setup.png", dpi=100); plt.close()

# --- 2. 流動材木の時間発展 ---
frames = [2, 3, 4, 5, 6, 7]
cmap = plt.get_cmap("YlOrBr").copy(); cmap.set_under("white")
fig, axes = plt.subplots(2, 3, figsize=(13, 4.9), sharex=True, sharey=True)
for k, ax in zip(frames, axes.flat):
    hd = rd("Hd", k); h = rd("H", k)
    im = ax.imshow(hd, origin="lower", extent=EXT, cmap=cmap, vmin=0.005, vmax=0.5)
    ax.contour(X, (np.arange(NY) + 0.5) * DX, h, levels=[0.01], colors="royalblue", linewidths=0.8)
    draw_walls(ax)
    vol = (hd * gv * A).sum()
    ax.set_title("t = %.1f h, sea %+.2f m, afloat %5.0f m3" % (tm[k] / 3600, tide_curve(tm[k] / 60), vol), fontsize=8)
for ax in axes[-1]:
    ax.set_xlabel("x (m)")
for ax in axes[:, 0]:
    ax.set_ylabel("y (m)")
fig.colorbar(im, ax=axes, label="floating wood Hd (m3/m2)", shrink=0.7, extend="min")
fig.suptitle("floating timber (blue line: edge of inundation h > 0.01 m)", fontsize=10)
plt.savefig("figs/frames.png", dpi=100, bbox_inches="tight"); plt.close()

# --- 3. 到達・堆積・流速・流体力 ---
fig, axes = plt.subplots(2, 2, figsize=(13, 6.4), sharex=True, sharey=True)
panels = [("Wd", 9999, "max arrival Wd9999 = max(floating + deposited) (m3/m2)", cmap, 0.005, 1.5),
          ("Wd", 9998, "final deposit Wd9998 (m3/m2)", cmap, 0.005, 1.5),
          ("V", 9999, "max velocity V9999 (m/s)", plt.get_cmap("viridis"), 0.0, 2.0),
          ("F", 9999, "max fluid force F9999 = u2h (m3/s2)", plt.get_cmap("magma"), 0.0, 6.0)]
for (nm, k, ttl, cm, v0, v1), ax in zip(panels, axes.flat):
    a = rd(nm, k)
    im = ax.imshow(a, origin="lower", extent=EXT, cmap=cm, vmin=v0, vmax=v1)
    draw_walls(ax, lw=1.0)
    plt.colorbar(im, ax=ax, shrink=0.9, extend="max" if nm == "F" else "neither")
    ax.set_title(ttl, fontsize=9)
for ax in axes[-1]:
    ax.set_xlabel("x (m)")
for ax in axes[:, 0]:
    ax.set_ylabel("y (m)")
plt.tight_layout(); plt.savefig("figs/deposit.png", dpi=100); plt.close()

# --- 4. 材積台帳の時系列 ---
d = np.loadtxt("result/driftwood.csv", delimiter=",", skiprows=1)
tmin = d[:, 0] / 60
fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(tmin, d[:, 6], color="saddlebrown", lw=1.6, label="standing stock in yard (vol_stock)")
ax.plot(tmin, d[:, 7], color="darkorange", lw=1.6, label="floating (vol_float)")
ax.plot(tmin, d[:, 8], color="0.3", lw=1.6, label="deposited (vol_deposit)")
ax.plot(tmin, d[:, 6] + d[:, 7] + d[:, 8], "k:", lw=0.8, label="sum (= 60,000 m3)")
ax.set_xlim(0, 240); ax.set_xlabel("t (min)"); ax.set_ylabel("timber volume (m3)"); ax.grid(alpha=0.3)
ax2 = ax.twinx()
ax2.plot(tmin, tide_curve(tmin), "b-", lw=1.0, alpha=0.6, label="sea level (right axis)")
ax2.axhline(DW_HREC + Z_YARD, color="b", lw=0.6, ls=":")
ax2.set_ylim(-0.5, 4); ax2.set_ylabel("sea level (m)", color="b")
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, fontsize=8, loc="center right")
ax.set_title("timber ledger (result/driftwood.csv)", fontsize=10)
plt.tight_layout(); plt.savefig("figs/ledger.png", dpi=100); plt.close()

# --- 5. 断面図(開口部の行 / 防潮壁の行) ---
fig, axes = plt.subplots(2, 2, figsize=(13, 6.4), sharex=True)
for col, (jrow, lab) in enumerate(((J_ROW_OPEN, "through the opening (y = %.0f m)" % ((J_ROW_OPEN - 0.5) * DX)),
                                    (J_ROW_WALL, "through the seawall (y = %.0f m)" % ((J_ROW_WALL - 0.5) * DX)))):
    j = jrow - 1
    ax = axes[0][col]
    ax.fill_between(X, -4, z0[j], color="0.85"); ax.plot(X, z0[j], "k-", lw=1)
    for k, c in zip((2, 3, 4, 5, 7, 8), ("#9ecae1", "#6baed6", "#3182bd", "#08519c", "#807dba", "#54278f")):
        h = rd("H", k)[j]
        ax.plot(X, np.where(h > 0.01, z0[j] + h, np.nan), color=c, lw=1.1, label="t = %.1f h" % (tm[k] / 3600))
    ax.set_ylim(-3.5, 4.2); ax.set_ylabel("elevation (m)"); ax.grid(alpha=0.3); ax.set_title("water surface " + lab, fontsize=10)
    ax = axes[1][col]
    ax.fill_between(X, 0, rd("Wd", 9999)[j], color="navajowhite", label="max arrival Wd9999")
    ax.fill_between(X, 0, rd("Wd", 9998)[j], color="saddlebrown", alpha=0.8, label="final deposit Wd9998")
    ax.plot(X, rd("Hd", 4)[j], color="darkorange", lw=1.2, label="floating Hd at t = 2.0 h")
    ax.set_ylim(0, 2.0); ax.set_ylabel("wood column (m3/m2)"); ax.set_xlabel("x (m)"); ax.grid(alpha=0.3)
    ax.set_title("timber " + lab, fontsize=10)
axes[0][0].legend(fontsize=7, ncol=2); axes[1][0].legend(fontsize=7)
plt.tight_layout(); plt.savefig("figs/profile.png", dpi=100); plt.close()

# --- 数表(README 用) ---
wd = rd("Wd", 9998); wm = rd("Wd", 9999); v = rd("V", 9999); f = rd("F", 9999); hmax = rd("H", 9999)
vol = wd * gv * A
total = stock.sum() * A
print("timber stock %.0f m3" % total)
for name, m in zn.items():
    print("  %-7s deposit %6.0f m3 (%4.1f%%)  max column %.2f m3/m2" % (name, vol[:, m].sum(), 100 * vol[:, m].sum() / total, wd[:, m].max()))
print("  sum     %.0f m3 (ledger vol_deposit %.0f m3)" % (vol.sum(), d[-1, 8]))
rows = slice(J_OPEN[0] - 1, J_OPEN[1])
print("town deposit behind the opening (rows %d-%d) %.0f m3 / other rows %.0f m3"
      % (J_OPEN[0], J_OPEN[1], vol[rows, zn["town"]].sum(), vol[:, zn["town"]].sum() - vol[rows, zn["town"]].sum()))
for a, b in ((370, 500), (500, 700), (700, 900), (900, 1200)):
    m = (X > a) & (X < b)
    print("  town x %4d-%4d m: %6.0f m3" % (a, b, vol[:, m].sum()))
reach = X[(wm > 0.01).any(axis=0)].max()
print("max reach of timber (Wd9999 > 0.01): x = %.0f m; town cells reached %d / %d" % (reach, (wm[:, zn["town"]] > 0.01).sum(), zn["town"].sum() * NY))
i = d[:, 7].argmax()
t_rel = d[np.where(d[:, 6] < 1)[0][0], 0] / 60
t_dep = d[np.where((d[:, 7] < 1) & (d[:, 0] > d[i, 0]))[0][0], 0] / 60
print("peak floating volume %.0f m3 at t = %.0f min; release complete at t = %.0f min; all deposited by t = %.0f min"
      % (d[i, 7], d[i, 0] / 60, t_rel, t_dep))
print("town: max depth %.2f m, max velocity %.2f m/s, max fluid force %.2f m3/s2; opening: max velocity %.2f m/s"
      % (hmax[:, zn["town"]].max(), v[:, zn["town"]].max(), f[:, zn["town"]].max(), v[rows, I_WALL[0] - 1:I_WALL[1]].max()))

# --- 感度ケース(param_vstop0.txt / param_refloat.txt を実行済みなら比較表を出す) ---
print("\nsensitivity (final state at t = 4 h; arrival = sum of Wd9999 over the town):")
print("  %-15s %8s %8s %8s %8s %8s %8s" % ("case", "arrival", "town dep", "yard dep", "afloat", "outflow", "reach"))
for r in ("result", "result_vstop0", "result_refloat", "result_wall4"):
    if not os.path.exists(r + "/driftwood.csv"):
        continue
    dd = np.loadtxt(r + "/driftwood.csv", delimiter=",", skiprows=1)[-1]
    wdr = np.loadtxt(r + "/Wd9998.txt"); wmr = np.loadtxt(r + "/Wd9999.txt")
    print("  %-15s %8.0f %8.0f %8.0f %8.0f %8.0f %6.0f m" % (r, (wmr * gv * A)[:, zn["town"]].sum(), (wdr * gv * A)[:, zn["town"]].sum(),
          (wdr * gv * A)[:, zn["yard"]].sum(), dd[7], total - dd[6] - dd[7] - dd[8], X[(wmr > 0.01).any(axis=0)].max()))
print("figs/setup.png figs/frames.png figs/deposit.png figs/ledger.png figs/profile.png")
