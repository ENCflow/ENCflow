#!/usr/bin/env python3
"""test/splashlc の図を figs/splashlc.png に描く(事前に ./Run.sh を実行しておく)。
格子の κ(spl_lc = 0)と相関長 ℓ = 2 m の κ の対照: 最終地形、崖面帯の列の
y 方向起伏、崖面帯の y 方向スペクトル(初期と最終)。
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
matplotlib.rcParams["font.family"] = ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs("figs", exist_ok=True)

DX = 1.0
cases = [("g", "構成 g: 格子の κ(spl_lc = 0)"), ("l", "構成 l: 相関長 ℓ = 2 m(spl_lc = 2)")]


def cliff_cols(z, hp=15.0):
    return [c for c in range(z.shape[1]) if 0.5 < z[:, c].mean() < hp - 0.5]


def spectrum(z, cols):
    ny = z.shape[0]
    P = np.zeros(ny // 2 + 1)
    for c in cols:
        s = z[:, c] - z[:, c].mean()
        P += (2.0 * np.abs(np.fft.rfft(s)) / ny) ** 2
    k = np.fft.rfftfreq(ny, d=DX)
    return k[1:], np.sqrt(P[1:] / len(cols))


fig, axes = plt.subplots(2, 3, figsize=(15, 7.5))
for row, (tag, lab) in enumerate(cases):
    z0 = np.loadtxt("result_%s/Z0000.txt" % tag); z1 = np.loadtxt("result_%s/Z9998.txt" % tag)
    ny, nx = z0.shape; ext = [0, nx * DX, 0, ny * DX]
    im = axes[row, 0].imshow(z1, origin="lower", extent=ext, cmap="terrain", vmin=0, vmax=15)
    axes[row, 0].set_xlim(10, 40); axes[row, 0].set_title(lab + ": 最終地形 z (m)", fontsize=9)
    fig.colorbar(im, ax=axes[row, 0], shrink=0.8)
    c0 = cliff_cols(z0); c1 = cliff_cols(z1); c = c1[len(c1) // 2]
    y = (np.arange(ny) + 0.5) * DX
    axes[row, 1].plot(y, z0[:, c] - z0[:, c].mean(), "0.5", label="初期(列 ix = %d)" % (c + 1))
    axes[row, 1].plot(y, z1[:, c] - z1[:, c].mean(), "C3", label="最終")
    axes[row, 1].set_xlabel("y (m)"); axes[row, 1].set_ylabel("z − 列平均 (m)"); axes[row, 1].legend(fontsize=8)
    axes[row, 1].set_title("崖面帯の列の y 方向起伏", fontsize=9)
    k0, a0 = spectrum(z0, c0); k1, a1 = spectrum(z1, c1)
    axes[row, 2].semilogy(1.0 / k0, a0, "0.5", marker="o", ms=3, label="初期")
    axes[row, 2].semilogy(1.0 / k1, a1, "C3", marker="o", ms=3, label="最終")
    for lam in (4.0, 20.0):
        axes[row, 2].axvline(lam, color="k", ls=":", lw=0.8)
    axes[row, 2].set_xscale("log"); axes[row, 2].set_xlabel("波長 (m)"); axes[row, 2].set_ylabel("振幅 (m)")
    axes[row, 2].set_title("崖面帯の y 方向スペクトル(点線: 4 m・20 m)", fontsize=9); axes[row, 2].legend(fontsize=8)
plt.tight_layout()
plt.savefig("figs/splashlc.png", dpi=110)
print("figs/splashlc.png written")
