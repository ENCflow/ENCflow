#!/usr/bin/env python3
"""ashfall_lahar の補足実験(谷の向きと格子)の図と数表(事前に make rotated で 4 ケースを計算しておく)。

  figs/rotated.png  谷を格子に沿わせた場合(0°)と 45° 傾けた場合の、40 分の流動深と終了時の
                    地形変化(8 近傍と 4 近傍)。45° の結果は谷沿いの座標へ戻して描く
  figs/rotated_profile.png  谷底付近の横断の流動深(30〜60 分の平均)と、扇状地の流れの横の広がり
引数 en で英語ラベル版を en/figs/ に描く。
"""
import glob
import math
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)

DX, NXR, NYR = 5.0, 120, 30                 # 谷沿いの格子(make_init.py の地形と同じ)
XP = (np.arange(NXR) + 0.5) * DX
YP = (np.arange(NYR) + 0.5) * DX
RUNS = [(0, 8), (45, 8), (0, 4), (45, 4)]


def label(th, nb):
    return T(f"{th}°・{nb} 近傍", f"{th}°, {nb} neighbours")


def frames(case, var="Z"):
    return sorted(int(f[-8:-4]) for f in glob.glob(f"result_{case}/{var}0*.txt"))


def back(arr, th):
    """出力の場(先頭行 = 北端)を谷沿いの格子 (x', y') の値へ戻す(45° は双一次補間)。"""
    g = arr[::-1]                                        # 先頭行 = 南端(make_rotated.py の j)
    nx, ny, ox, oy = open(f"data_rot{th}/size.txt").read().split()
    ox, oy = float(ox), float(oy)
    t = math.radians(th)
    c, s = math.cos(t), math.sin(t)
    xr, yr = np.meshgrid(XP, YP)
    fi = (ox + xr * c + yr * s) / DX - 0.5
    fj = (oy - xr * s + yr * c) / DX - 0.5
    i0 = np.floor(fi).astype(int)
    j0 = np.floor(fj).astype(int)
    a, b = fi - i0, fj - j0
    if th == 0:
        return g[j0, i0]
    return (g[j0, i0] * (1 - a) * (1 - b) + g[j0, i0 + 1] * a * (1 - b)
            + g[j0 + 1, i0] * (1 - a) * b + g[j0 + 1, i0 + 1] * a * b)


def fields(th, nb):
    c = f"rot{th}_{nb}"
    ks = frames(c)
    tm = {int(l.split(",")[0]): float(l.split(",")[2]) / 60 for l in open(f"result_{c}/FILENUMBER.csv")
          if not l.startswith("#") and int(l.split(",")[0]) < 9000}
    z0 = np.loadtxt(f"result_{c}/Z0000.txt")
    dz = back(np.loadtxt(f"result_{c}/Z{ks[-1]:04d}.txt") - z0, th)
    dep = lambda k: back(np.loadtxt(f"result_{c}/H{k:04d}.txt") + np.loadtxt(f"result_{c}/Hs{k:04d}.txt"), th)
    k40 = min(tm, key=lambda k: abs(tm[k] - 40))
    hmean = np.mean([dep(k) for k in ks if 30 <= tm[k] <= 60], axis=0)
    return dz, dep(k40), hmean


def main():
    F = {r: fields(*r) for r in RUNS}
    inner = (slice(1, -1), slice(1, -1))                  # 外周 1 セル(補間の縁)を除く
    print(T("回転への依存(0° と 45° の差 / 0° の大きさ。L1)", "rotation dependence (|45° − 0°| / |0°|, L1)"))
    for nb in (8, 4):
        a, b = F[(0, nb)], F[(45, nb)]
        r = [np.abs(b[k][inner] - a[k][inner]).sum() / np.abs(a[k][inner]).sum() for k in range(3)]
        print(f"  {nb}: dz {r[0]:.3f}  h(40 min) {r[1]:.3f}  h(30-60 min mean) {r[2]:.3f}")
    # 谷の中の横断(x' 150〜250 m)と扇状地の横の広がり(x' 400〜550 m)
    valley = (XP >= 150) & (XP < 250)
    fan = (XP >= 400) & (XP < 550)
    print(T("谷の中の横断(30〜60 分平均の流動深、mm。y' 47.5〜102.5 m)", "cross-section in the valley (mean flow depth 30-60 min, mm; y' 47.5-102.5 m)"))
    prof = {}
    for r in RUNS:
        prof[r] = F[r][2][:, valley].mean(axis=1)
        print(f"  {label(*r)}: " + " ".join(f"{v * 1000:.1f}" for v in prof[r][9:21]))
    print(T("扇状地の中央の流れ(30〜60 分平均の流動深の横断分布。ピーク mm、半値幅 m = 扇状地全面のシート流の"
            "深さを底とした半分の高さの幅)", "central flow on the fan (lateral distribution of the 30-60 min mean depth; "
            "peak mm, half width m = width at half height above the sheet flow on the whole fan)"))
    spread = {}
    for r in RUNS:
        h = F[r][2][:, fan].mean(axis=1)
        base = 0.5 * (h[:4].mean() + h[-4:].mean())
        half = base + 0.5 * (h.max() - base)
        yy = np.linspace(YP[0], YP[-1], 2001)
        hh = np.interp(yy, YP, h)
        spread[r] = (h.max() * 1000, (hh >= half).sum() * (yy[1] - yy[0]))
        print(f"  {label(*r)}: peak {spread[r][0]:.1f} mm, half width {spread[r][1]:.1f} m")
    # 図 1: 40 分の流動深と地形変化
    fig, axs = plt.subplots(4, 2, figsize=(15, 9.2), constrained_layout=True)
    for row, r in enumerate(RUNS):
        dz, h40, _ = F[r]
        im = axs[row, 0].imshow(np.where(h40 > 0.002, h40, np.nan), origin="lower", extent=[0, 600, 0, 150],
                                cmap="Blues", vmin=0, vmax=0.05)
        axs[row, 0].set_title(T(f"{label(*r)}: 流動深 h + hs(40 分)", f"{label(*r)}: flow depth h + hs (40 min)"), fontsize=9.5)
        fig.colorbar(im, ax=axs[row, 0], shrink=0.9, extend="max").set_label("m")
        im = axs[row, 1].imshow(dz, origin="lower", extent=[0, 600, 0, 150], cmap="RdBu_r",
                                norm=TwoSlopeNorm(vmin=-0.3, vcenter=0.0, vmax=2.5))
        axs[row, 1].set_title(T(f"{label(*r)}: 地形変化 z − z0(90 分)", f"{label(*r)}: bed change z − z0 (90 min)"), fontsize=9.5)
        cb = fig.colorbar(im, ax=axs[row, 1], shrink=0.9)
        cb.set_ticks([-0.3, -0.1, 0.0, 0.5, 1.0, 1.5, 2.0, 2.5])
        cb.set_label("m")
        for ax in axs[row]:
            ax.axvline(300, color="k", lw=0.6, ls="--")
            ax.set_ylabel("y' (m)")
    for ax in axs[-1]:
        ax.set_xlabel(T("x' (m)  谷に沿う向き", "x' (m)  along the valley"))
    fig.savefig(f"{FIGDIR}/rotated.png", dpi=95)
    plt.close(fig)
    # 図 2: 谷の中の横断と扇状地の横断
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.2), constrained_layout=True)
    sty = {(0, 8): ("#1f5f8b", "-"), (45, 8): ("#1f5f8b", "--"), (0, 4): ("#c0392b", "-"), (45, 4): ("#c0392b", "--")}
    for r in RUNS:
        col, ls = sty[r]
        axs[0].plot(YP, prof[r] * 1000, ls, color=col, lw=1.6, marker=".", label=label(*r))
        axs[1].plot(YP, F[r][2][:, fan].mean(axis=1) * 1000, ls, color=col, lw=1.6,
                    label=T(f"{label(*r)}(半値幅 {spread[r][1]:.0f} m)", f"{label(*r)} (half width {spread[r][1]:.0f} m)"))
    axs[0].set_xlim(40, 110)
    axs[0].axvspan(67.5, 82.5, color="0.92")
    axs[0].text(75, axs[0].get_ylim()[1] * 0.95, T("谷底", "valley floor"), ha="center", fontsize=8)
    axs[0].set_title(T("谷の中の横断(x' 150〜250 m、30〜60 分の平均)", "Across the valley (x' 150-250 m, mean of 30-60 min)"), fontsize=10)
    axs[1].set_title(T("扇状地の横断(x' 400〜550 m、30〜60 分の平均)", "Across the fan (x' 400-550 m, mean of 30-60 min)"), fontsize=10)
    for ax in axs:
        ax.set_xlabel(T("y' (m)  谷を横切る向き", "y' (m)  across the valley"))
        ax.set_ylabel(T("流動深 h + hs (mm)", "flow depth h + hs (mm)"))
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    fig.savefig(f"{FIGDIR}/rotated_profile.png", dpi=100)
    plt.close(fig)


if __name__ == "__main__":
    main()
