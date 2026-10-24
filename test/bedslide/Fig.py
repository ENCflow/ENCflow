#!/usr/bin/env python3
"""test/bedslide の図を figs/*.png に描く(事前に ./Run.sh を実行しておく)。

  python3 Fig.py [en]      # en: 英語表記で en/figs/ に出力

- figs/bench.png   : 構成 1(格子沿い)・構成 2(45° 回転)の底層速度 Vb の分布と、
                     解析値 V = √(ξ D (tanθ − μ)) との比較
- figs/tsunami.png : 構成 3(斜面 → 湖)の初期地形と底層、最終の地形変化、水面変位の中央行
- figs/plunge.png  : 構成 4(混合体 → 引き渡し → 底層)と対照(混合体のみ)の湖底堆積の比較
出力は分布テキスト(result_*/Z, Sd, Hb, Vb, E, H)を読む。
"""
import glob, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
EN = "en" in sys.argv[1:]          # 引数 en: 英語表記で en/figs/ に出力
def T(ja, en): return en if EN else ja
FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)


def last(rdir, name):
    fs = sorted(glob.glob(os.path.join(rdir, name + "[0-9][0-9][0-9][0-9].txt")))
    fs = [f for f in fs if not f.endswith("9999.txt")]
    return np.loadtxt(fs[-1])


# ---- 構成 1・2: Voellmy 底層の速度 ----
ST, D, MU, XI = 0.4, 1.0, 0.1, 200.0
V = np.sqrt(XI * D * (ST - MU))
fig, axes = plt.subplots(1, 2, figsize=(12, 4.2), gridspec_kw={"width_ratios": [1.6, 1]})
vb1 = last("result_bench", "Vb"); vb2 = last("result_rot", "Vb")
im = axes[0].imshow(np.where(vb1 > 0.01, vb1, np.nan), origin="lower", extent=[0, 100, 0, 20], cmap="viridis", vmin=V * 0.9, vmax=V * 1.02)
axes[0].set_title(T(f"構成 1(格子沿い、tanθ = {ST}): 底層速度 Vb (m/s)、t = 1 s。解析値 V = √(ξ D (tanθ − μ)) = {V:.3f}", f"Config. 1 (grid-aligned, tanθ = {ST}): Vb (m/s), t = 1 s; analytical V = √(ξ D (tanθ − μ)) = {V:.3f}"), fontsize=9)
axes[0].set_xlabel("x (m)"); axes[0].set_ylabel("y (m)"); fig.colorbar(im, ax=axes[0], shrink=0.8)
im = axes[1].imshow(np.where(vb2 > 0.01, vb2, np.nan), origin="lower", extent=[0, 60, 0, 60], cmap="viridis", vmin=V * 0.9, vmax=V * 1.02)
axes[1].set_title(T("構成 2(45° 回転): Vb (m/s)", "Configuration 2 (rotated 45°): Vb (m/s)"), fontsize=9)
axes[1].set_xlabel("x (m)"); axes[1].set_ylabel("y (m)"); fig.colorbar(im, ax=axes[1], shrink=0.8)
fig.tight_layout(); fig.savefig(f"{FIGDIR}/bench.png", dpi=110); plt.close(fig)
inner1 = vb1[2:-2, 40:60]
print("bench: inner Vb %.4f..%.4f (V %.4f); rot: median Vb of moving cells %.4f" % (inner1.min(), inner1.max(), V, np.median(vb2[vb2 > 0.5 * V])))

# ---- 構成 3: 斜面 → 湖 ----
DX3 = 5.0
z0 = np.loadtxt("result/Z0000.txt"); zf = last("result", "Z"); e0 = np.loadtxt("result/E0000.txt"); ef = last("result", "E")
h0 = np.loadtxt("result/H0000.txt"); hf = last("result", "H")
db = np.loadtxt("db.txt")
ny, nx = z0.shape
x = (np.arange(nx) + 0.5) * DX3
jc = ny // 2
fig, axes = plt.subplots(2, 2, figsize=(13, 7))
ax = axes[0, 0]
ax.fill_between(x, z0[jc] - 60, z0[jc], color="0.8", label=T("初期地形(岩盤 + 底層)", "initial terrain (bedrock + bed layer)"))
ax.plot(x, z0[jc] - db[jc], "k--", lw=1, label=T("すべり面 z₀ − D", "slip surface z₀ − D"))
ax.plot(x, np.where(h0[jc] > 0.01, e0[jc], np.nan), "C0", lw=1.2, label=T("初期水面", "initial water surface"))
ax.plot(x, zf[jc], "C3", lw=1.5, label=T("最終地形 (60 s)", "final terrain (60 s)"))
ax.set_ylim(z0[jc].min() - 20, z0[jc].max() + 10)
ax.set_xlabel("x (m)"); ax.set_ylabel("z (m)"); ax.set_title(T("構成 3: 中央行の縦断(斜面 → 湖、Δx = 5 m)", "Configuration 3: longitudinal profile of the centre row (slope → lake, Δx = 5 m)"), fontsize=10)
ax.legend(fontsize=8); ax.grid(alpha=0.3)
ax = axes[0, 1]
im = ax.imshow(zf - z0, origin="lower", extent=[0, 600, 0, 200], cmap="RdBu_r", vmin=-15, vmax=15)
ax.set_title(T("地形変化 z − z₀ (m)、t = 60 s(負: 発生域、正: 湖底の堆積)", "Terrain change z − z₀ (m), t = 60 s (negative: source area, positive: lake-bed deposit)"), fontsize=10); ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
fig.colorbar(im, ax=ax, shrink=0.8)
ax = axes[1, 0]
wet = (hf > 0.01) & (h0 > 0.01)
ax.plot(x, np.where(wet[jc], ef[jc] - e0[jc], np.nan), "C0", lw=1.5)
ax.axhline(0, color="0.5", lw=0.8)
ax.set_xlabel("x (m)"); ax.set_ylabel("η (m)"); ax.set_title(T("中央行の水面変位 e − e₀、t = 60 s(湖の部分)", "Water-surface displacement e − e₀ of the centre row, t = 60 s (lake part)"), fontsize=10); ax.grid(alpha=0.3)
ax = axes[1, 1]
im = ax.imshow(np.where(wet, ef - e0, np.nan), origin="lower", extent=[0, 600, 0, 200], cmap="RdBu_r", vmin=-1, vmax=1)
ax.set_title(T("水面変位 e − e₀ (m)、t = 60 s", "Water-surface displacement e − e₀ (m), t = 60 s"), fontsize=10); ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
fig.colorbar(im, ax=ax, shrink=0.8)
fig.suptitle(T("構成 3: 底層(Voellmy μ = 0.15、ξ = 500、かさ密度 2000 kg/m³)が湖へ突入し、湖底を走って堆積・造波", "Configuration 3: the bed layer (Voellmy μ = 0.15, ξ = 500, bulk density 2000 kg/m³) plunges into the lake, runs along the lake bed, deposits and generates waves"), fontsize=10)
fig.tight_layout(); fig.savefig(f"{FIGDIR}/tsunami.png", dpi=110); plt.close(fig)
flat = (x >= 300)
print("tsunami: max dz on flat lake floor (x>=300) %.2f m, max eta %.3f m, sum h0 %.2f sum hf %.2f" % ((zf - z0)[:, flat].max(), np.nanmax(np.where(wet, ef - e0, np.nan)), h0.sum(), hf.sum()))

# ---- 構成 4: 引き渡し ----
fig, axes = plt.subplots(1, 2, figsize=(13, 4))
for ax, rdir, lab in [(axes[0], "result_plunge", T("構成 4: 混合体 → 引き渡し → 底層(f_bedslide = 1、bs_hplunge = 2 m)", "Configuration 4: mixture → handover → bed layer (f_bedslide = 1, bs_hplunge = 2 m)")),
                      (axes[1], "result_mix", T("対照: 混合体のみ(f_bedslide = 0)", "Control: mixture only (f_bedslide = 0)"))]:
    z0p = np.loadtxt(os.path.join(rdir, "Z0000.txt")); zfp = last(rdir, "Z")
    im = ax.imshow(zfp - z0p, origin="lower", extent=[0, 600, 0, 200], cmap="RdBu_r", vmin=-15, vmax=15)
    ax.set_title(lab + T("\n地形変化 z − z₀ (m)", "\nTerrain change z − z₀ (m)"), fontsize=9); ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
    fig.colorbar(im, ax=ax, shrink=0.8)
    print("%s: flat lake floor max dz %.2f m" % (rdir, (zfp - z0p)[:, flat].max()))
fig.tight_layout(); fig.savefig(f"{FIGDIR}/plunge.png", dpi=110); plt.close(fig)
