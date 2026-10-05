#!/usr/bin/env python3
"""nhshelf: README 用の図を figs/fission.png に描く(result = NH V2、result_v1 = V1、result_h = 静水圧)

  使い方: ./Run.sh、./encflow param_v1.txt、./encflow param_h.txt の後に ./Fig.py
  上段: 最終時刻(120 s)の中央行の水面 η(x) を 3 構成で重ねる。地形も示す
  下段: NH(param.txt)の η(x) を 20 s ごとに縦にずらして並べる(棚に乗って分裂する過程)
  計算本体の外(方針 10)。numpy + matplotlib。
"""
import os, glob
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from Fission import z_of, H1, H2, A0, dx

plt.rcParams.update({"font.family": ["IPAGothic", "DejaVu Sans"], "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": "#e3e2dd", "grid.linewidth": 0.6,
                     "lines.linewidth": 1.5})
C_NH, C_HY, C_V1, C_BED = "#2a78d6", "#eb6834", "#4a3aa7", "#9c9a94"

def profiles(resdir):
    times = {}
    for l in open(os.path.join(resdir, "FILENUMBER.csv")):
        if l.startswith("#"): continue
        c = l.split(","); times[int(c[0])] = float(c[2])
    out = []
    for f in sorted(glob.glob(os.path.join(resdir, "H[0-9][0-9][0-9][0-9].txt"))):
        if f.endswith(("H9998.txt", "H9999.txt")): continue
        a = np.loadtxt(f); k = int(os.path.basename(f)[1:5])
        out.append((times.get(k, float("nan")), a[a.shape[0] // 2, :]))
    return out

if __name__ == "__main__":
    os.makedirs("figs", exist_ok=True)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7.2, 6.0), gridspec_kw={"height_ratios": [1, 1.4]})
    cases = [("result", "非静水圧、底面勾配項あり(V2)", C_NH, "-"),
             ("result_v1", "非静水圧、勾配項なし(V1)", C_V1, "--"),
             ("result_h", "静水圧", C_HY, "-")]
    x = None
    for d, lab, col, ls in cases:
        if not os.path.isdir(d): continue
        t, h = profiles(d)[-1]
        x = (np.arange(len(h)) + 0.5) * dx
        ax1.plot(x, (h + z_of(x) - H1) / A0, color=col, ls=ls, label=lab)
    bed = -1.0 + 0.4 * z_of(x) / H2          # 模式的な地形(縦は非縮尺)
    ax1.fill_between(x, -1.0, bed, color=C_BED, alpha=0.3, lw=0)
    ax1.text(60, -0.9, "H₁ = 1 m", fontsize=8, ha="center", color="#52514e")
    ax1.text(125, -0.4, "斜面 1:20", fontsize=8, ha="center", color="#52514e")
    ax1.text(260, -0.5, "棚 H₂ = 0.5 m", fontsize=8, ha="center", color="#52514e")
    ax1.set_xlim(0, 400); ax1.set_ylim(-1, 1.1)
    ax1.set_ylabel("η / a₀"); ax1.set_xlabel("x (m)")
    ax1.set_title(f"t = {t:.0f} s の水面(地形は模式、縦方向は非縮尺)", fontsize=10, loc="left")
    ax1.legend(loc="upper left", frameon=False, fontsize=8)
    prof = profiles("result")
    x = (np.arange(len(prof[0][1])) + 0.5) * dx
    shown = [p for p in prof if abs(p[0] / 20.0 - round(p[0] / 20.0)) < 1e-6]
    for i, (t, h) in enumerate(shown):
        off = -1.2 * i
        ax2.axhline(off, color="#e3e2dd", lw=0.6)
        ax2.plot(x, (h + z_of(x) - H1) / A0 + off, color=C_NH)
        ax2.text(395, off + 0.15, f"t = {t:.0f} s", ha="right", fontsize=8, color="#52514e")
    ax2.axvspan(120, 130, color=C_BED, alpha=0.2, lw=0)
    ax2.set_xlim(0, 400); ax2.set_yticks([])
    ax2.set_xlabel("x (m)"); ax2.set_ylabel("η / a₀(20 s ごとに 1.2 ずらす)")
    ax2.set_title("非静水圧(V2)の時間発展。灰帯は斜面の区間", fontsize=10, loc="left")
    ax2.grid(False)
    fig.suptitle("棚に乗り上げる孤立波のソリトン分裂(a₀/H₁ = 0.1、Δx = 0.25 m)", fontsize=10, x=0.02, ha="left")
    fig.tight_layout(); fig.savefig("figs/fission.png", dpi=150)
    print("written: figs/fission.png")
