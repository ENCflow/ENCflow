#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# examples/levee_breach の図化(result / result_vwall → figs/)
#   figs/setup.png       : 地形と破堤口、破堤口を通る東西断面の地形の変化(Z0000 → Z0010)
#   figs/timeseries.png  : 流入波形と破堤口・河道下流の流量、破堤口前の河川水位と破堤セルの地盤高、堤内地の浸水深
#   figs/inundation.png  : 最大浸水深(解像堤防 / 仮想壁面)と水深分布のスナップショット
#   標準出力に数表(破堤口の最大流量・氾濫量・浸水面積・最大浸水深)
import os, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams.update({"font.family": ["IPAGothic", "DejaVu Sans"], "font.size": 10})

DX, NX, NY = 10.0, 120, 80
CASES = [("result", "解像堤防 + 規定底面運動", "#eb6834"),
         ("result_vwall", "仮想壁面 + &list_channel_breach", "#2a78d6")]
JB = 50                                   # 破堤口の中心行(1 スタート)
x = (np.arange(NX) + 0.5) * DX; y = (NY - np.arange(NY) - 0.5) * DX
os.makedirs("figs", exist_ok=True)
z0 = np.loadtxt("z.txt")

def times(rdir):
    return {int(l.split(",")[0]): float(l.split(",")[2]) for l in open(rdir + "/FILENUMBER.csv") if not l.startswith("#")}
def field(rdir, name, k):
    return np.loadtxt("%s/%s%04d.txt" % (rdir, name, k))
def probe(rdir, n):
    a = np.loadtxt("%s/probes/probe%04d.csv" % (rdir, n), delimiter=",", comments="#")
    return a[:, 1], a[:, 2], a[:, 3]            # t(min), z, h
def flux(rdir, n):
    a = np.loadtxt("%s/fluxes/flux%04d.csv" % (rdir, n), delimiter=",", comments="#")
    return a[:, 1], a[:, 2]
cases = [c for c in CASES if os.path.isdir(c[0])]

# --- 1. 設定 ---
fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(12, 4.2), gridspec_kw={"width_ratios": [1.4, 1]})
im = ax0.imshow(z0, extent=[0, NX * DX, 0, NY * DX], origin="upper", cmap="terrain", vmin=-4, vmax=4)
ax0.add_patch(plt.Rectangle((200, (NY - 52) * DX), 20, 50, fill=False, ec="#eb6834", lw=2))
ax0.annotate("破堤口 (列 21〜22, 行 48〜52)", (225, (NY - 50) * DX), color="#eb6834", fontsize=9, va="center")
ax0.text(80, 400, "山付き", ha="center"); ax0.text(180, 400, "河道", ha="center", rotation=90)
ax0.text(600, 400, "堤内地(氾濫原)", ha="center")
ax0.set_xlabel("x (m)"); ax0.set_ylabel("y (m)"); ax0.set_title("地形 z(堤防は標高そのもの = 解像堤防)")
plt.colorbar(im, ax=ax0, label="z (m)", shrink=0.85)
if cases:
    rdir = cases[0][0]; tk = times(rdir)
    for k, c in ((0, "#8a8983"), (max(k for k in tk if k < 9000), "#eb6834")):
        zz = field(rdir, "Z", k)[JB - 1, :]
        ax1.plot(x, zz, color=c, lw=2, label="z  t = %d 分" % round(tk[k] / 60))
    ax1.set_xlim(100, 400); ax1.set_ylim(-4.5, 3.5)
    ax1.set_xlabel("x (m)"); ax1.set_ylabel("z (m)"); ax1.set_title("破堤口の中心行(j = %d)の東西断面" % JB)
    ax1.legend(frameon=False)
fig.tight_layout(); fig.savefig("figs/setup.png", dpi=120); plt.close(fig)

# --- 2. 時系列 ---
fig, axs = plt.subplots(1, 3, figsize=(14, 4.2))
tq = np.array([0, 30, 60, 120, 150, 180]); qin = np.array([100, 100, 700, 700, 100, 100])
axs[0].plot(tq, qin, color="#8a8983", lw=2, label="流入(北辺)")
for rdir, lab, c in cases:
    t, q = flux(rdir, 1); axs[0].plot(t, q, color=c, lw=2, label="破堤口 " + lab.split(" + ")[0])
    t, q = flux(rdir, 2); axs[0].plot(t, q, color=c, lw=1.2, ls="--", label="河道 下流 (j = 70)")
axs[0].set_xlabel("時刻 (分)"); axs[0].set_ylabel("Q (m³/s)"); axs[0].set_title("流量"); axs[0].legend(frameon=False, fontsize=8)
for rdir, lab, c in cases:
    t, z, h = probe(rdir, 2); axs[1].plot(t, z + h, color=c, lw=2, label="河川水位 " + lab.split(" + ")[0])
    t, z, h = probe(rdir, 3); axs[1].plot(t, z, color=c, lw=1.2, ls=":", label="破堤セルの地盤高(解像堤防)" if rdir == "result" else "破堤口の堤内地側の地盤高(仮想壁面)")
axs[1].axhline(z0[JB - 1, 20], color="#8a8983", lw=1, ls="--"); axs[1].text(2, z0[JB - 1, 20] + 0.1, "天端", color="#8a8983", fontsize=8)
axs[1].set_xlabel("時刻 (分)"); axs[1].set_ylabel("標高 (m)"); axs[1].set_title("破堤口前の河川水位と破堤口の地盤高"); axs[1].legend(frameon=False, fontsize=8)
for rdir, lab, c in cases:
    for n, ls, nm in ((4, "-", "法尻 x = 245 m"), (5, "--", "x = 595 m"), (6, ":", "x = 995 m")):
        t, z, h = probe(rdir, n); axs[2].plot(t, h, color=c, lw=1.6, ls=ls, label=lab.split(" + ")[0] + " " + nm)
axs[2].set_xlabel("時刻 (分)"); axs[2].set_ylabel("h (m)"); axs[2].set_title("堤内地の浸水深(j = %d)" % JB); axs[2].legend(frameon=False, fontsize=8)
for a in axs: a.axvspan(70, 90, color="#eb6834", alpha=0.08)
fig.tight_layout(); fig.savefig("figs/timeseries.png", dpi=120); plt.close(fig)

# --- 3. 浸水 ---
if cases:
    snaps = [90, 120, 180]
    fig, axs = plt.subplots(len(cases), 1 + len(snaps), figsize=(4.0 * (1 + len(snaps)), 2.9 * len(cases)), squeeze=False)
    for r, (rdir, lab, c) in enumerate(cases):
        tk = times(rdir); hm = np.loadtxt(rdir + "/H9999.txt"); hm = np.where(hm > 0.01, hm, np.nan)
        ax = axs[r, 0]; im = ax.imshow(hm, extent=[0, NX * DX, 0, NY * DX], origin="upper", cmap="Blues", vmin=0, vmax=2)
        ax.set_title("%s\n最大浸水深 H9999" % lab, fontsize=9); ax.set_ylabel("y (m)")
        for s, tmin in enumerate(snaps):
            k = min((kk for kk in tk if kk < 9000), key=lambda kk: abs(tk[kk] - tmin * 60)); h = field(rdir, "H", k); h = np.where(h > 0.01, h, np.nan)
            ax = axs[r, s + 1]; ax.imshow(h, extent=[0, NX * DX, 0, NY * DX], origin="upper", cmap="Blues", vmin=0, vmax=2)
            ax.set_title("h  t = %d 分" % tmin, fontsize=9)
        for ax in axs[r]:
            ax.contour(x, y, z0, levels=[1.0], colors="#8a8983", linewidths=0.6); ax.set_xlabel("x (m)")
    fig.colorbar(im, ax=axs.ravel().tolist(), label="h (m)", shrink=0.8)
    fig.savefig("figs/inundation.png", dpi=120, bbox_inches="tight"); plt.close(fig)

# --- 数表 ---
print("| ケース | 破堤口の最大流量 (m³/s) / 時刻 (分) | 氾濫量 (万 m³) | 浸水面積 (ha; h > 0.01 m) | 最大浸水深 (m) | 法尻の浸水開始 (分) |")
print("|---|---:|---:|---:|---:|---:|")
for rdir, lab, c in cases:
    t, q = flux(rdir, 1); dt = np.diff(t) * 60.0; vol = np.sum(0.5 * (q[1:] + q[:-1]) * dt)
    hm = np.loadtxt(rdir + "/H9999.txt")[:, 22:]
    tt, zz, hh = probe(rdir, 4); t_on = tt[np.argmax(hh > 0.01)] if (hh > 0.01).any() else float("nan")
    print("| %s | %.0f / %.0f | %.1f | %.1f | %.2f | %.0f |" % (lab, q.max(), t[q.argmax()], vol / 1e4,
          (hm > 0.01).sum() * DX * DX / 1e4, hm.max(), t_on))
print("written: figs/setup.png figs/timeseries.png figs/inundation.png")
