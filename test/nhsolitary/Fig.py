#!/usr/bin/env python3
"""nhsolitary: README 用の図を figs/profiles.png に描く(result = NH、result_h = 静水圧)

  使い方: ./Run.sh と ./encflow param_h.txt の後に ./Fig.py
  上 2 段: 中央行の水面 η(x) = h − H を 20 s ごとに重ねる(NH / 静水圧)
  下段:   波頂高さ a(t)/a0 の推移
  計算本体の外(方針 10)。numpy + matplotlib。
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from Solitary import load, analyze

plt.rcParams.update({"font.family": ["IPAGothic", "DejaVu Sans"], "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": "#e3e2dd", "grid.linewidth": 0.6,
                     "lines.linewidth": 1.5})
C_NH, C_HY = "#2a78d6", "#eb6834"
dx = 0.25; H = 1.0

if __name__ == "__main__":
    os.makedirs("figs", exist_ok=True)
    cases = [("result", "非静水圧 1 層", C_NH), ("result_h", "静水圧", C_HY)]
    cases = [c for c in cases if os.path.isdir(c[0])]
    fig, axes = plt.subplots(len(cases) + 1, 1, figsize=(7.2, 2.1 * len(cases) + 2.2))
    for ax, (d, lab, col) in zip(axes, cases):
        prof = load(d)
        x = (np.arange(len(prof[0][1])) + 0.5) * dx
        shown = [p for p in prof if abs(p[0] / 20.0 - round(p[0] / 20.0)) < 1e-6]
        for i, (t, h) in enumerate(shown):
            alpha = 0.35 + 0.65 * i / max(1, len(shown) - 1)
            ax.plot(x, (h - H) / 0.1, color=col, alpha=alpha)
            ic = int(np.argmax(h))
            ax.annotate(f"{t:.0f} s", (x[ic], (h[ic] - H) / 0.1), xytext=(0, 4),
                        textcoords="offset points", ha="center", fontsize=8, color="#52514e")
        ax.set_xlim(0, 300); ax.set_ylim(-0.3, 1.7)
        ax.set_ylabel("η / a₀")
        ax.set_title(lab, fontsize=10, loc="left")
    axes[-2].set_xlabel("x (m)")
    ax = axes[-1]
    for d, lab, col in cases:
        r = analyze(d, dx, H)
        ax.plot(r["rows"][:, 0], r["rows"][:, 2] / r["a0"], "o-", ms=4, color=col, mec="white", mew=0.8,
                label=f"{lab}(c/√(g(H+a)) = {r['c_fit']/r['c_th']:.3f})")
    ax.set_xlim(0, 60); ax.set_ylim(0.9, 1.6)
    ax.set_xlabel("t (s)"); ax.set_ylabel("a(t) / a₀")
    ax.set_title("波頂高さの推移", fontsize=10, loc="left")
    ax.legend(loc="upper left", frameon=False, fontsize=9)
    fig.suptitle("孤立波の伝播(H = 1 m、a₀/H = 0.1、Δx = H/4、x₀ = 50 m)", fontsize=10, x=0.02, ha="left")
    fig.tight_layout(); fig.savefig("figs/profiles.png", dpi=150)
    print("written: figs/profiles.png")
