#!/usr/bin/env python3
"""nhbore: README 用の図を figs/bore.png に描く(result = NH a/H 0.1、result_20 = a/H 0.2、result_h = 静水圧)

  使い方: ./Run.sh、./encflow param20.txt、./encflow param_h.txt の後に ./Fig.py(引数 en で英語版を en/figs/ に)
  左: 中央行の水面 η/a を 20 s ごとに縦にずらして並べる(NH 0.1 と静水圧)
  右: 先頭波の高さ η₁/a の推移(KdV の漸近値 2a)
  計算本体の外(方針 10)。numpy + matplotlib。
"""
import sys, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from Bore import load, analyze, H

EN = "en" in sys.argv[1:]
def T(ja, en): return en if EN else ja
FIGDIR = "en/figs" if EN else "figs"
plt.rcParams.update({"font.family": ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"], "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": "#e3e2dd", "grid.linewidth": 0.6, "lines.linewidth": 1.3})
C_NH, C_HY, C_20, C_TH = "#2a78d6", "#eb6834", "#4a3aa7", "#6b6a66"
dx = 0.25

if __name__ == "__main__":
    os.makedirs(FIGDIR, exist_ok=True)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.5, 4.0), gridspec_kw={"width_ratios": [1.6, 1]})
    for d, col, lab in [("result", C_NH, T("非静水圧(a/H = 0.1)", "Non-hydrostatic (a/H = 0.1)")), ("result_h", C_HY, T("静水圧", "Hydrostatic"))]:
        if not os.path.isdir(d): continue
        prof = load(d); a0 = prof[0][1].max() - H
        x = (np.arange(len(prof[0][1])) + 0.5) * dx
        shown = [p for p in prof if abs(p[0] / 20.0 - round(p[0] / 20.0)) < 1e-6 and p[0] <= 80]
        for i, (t, h) in enumerate(shown):
            off = -2.5 * i
            ax1.plot(x, (h - H) / a0 + off, color=col, label=lab if i == 0 else None, alpha=0.9)
            if d == "result": ax1.text(448, off + 0.3, f"t = {t:.0f} s", ha="right", fontsize=8, color="#52514e")
    ax1.set_xlim(0, 450); ax1.set_yticks([])
    ax1.set_xlabel("x (m)"); ax1.set_ylabel(T("η / a(20 s ごとに 2.5 ずらす)", "η / a (offset by 2.5 every 20 s)"))
    ax1.set_title(T("段差(x < 100 m、a/H = 0.1)から分裂する undular bore(中央行)", "Undular bore splitting from the step (x < 100 m, a/H = 0.1) (central row)"), fontsize=10, loc="left")
    ax1.legend(loc="lower left", frameon=False, fontsize=8); ax1.grid(False)
    for d, col, lab in [("result", C_NH, T("非静水圧 a/H = 0.1", "Non-hydrostatic a/H = 0.1")), ("result_20", C_20, T("非静水圧 a/H = 0.2", "Non-hydrostatic a/H = 0.2")), ("result_h", C_HY, T("静水圧 a/H = 0.1", "Hydrostatic a/H = 0.1"))]:
        if not os.path.isdir(d): continue
        a0, r = analyze(d)
        ok = np.isfinite(r[:, 3]) & (r[:, 1] < 440)
        ax2.plot(r[ok, 0], r[ok, 3], "o-", ms=4, color=col, mec="white", mew=0.8, label=lab)
    ax2.axhline(2.0, color=C_TH, ls=":", lw=1.0, label=T("KdV の漸近値 2a", "KdV asymptote 2a"))
    ax2.set_xlim(0, 100); ax2.set_ylim(1.0, 2.6)
    ax2.set_xlabel("t (s)"); ax2.set_ylabel(T("先頭波の高さ η₁ / a", "Leading-wave height η₁ / a"))
    ax2.set_title(T("先頭波の成長", "Growth of the leading wave"), fontsize=10, loc="left")
    ax2.legend(loc="lower right", frameon=False, fontsize=8)
    fig.tight_layout(); fig.savefig(f"{FIGDIR}/bore.png", dpi=150)
    print(f"written: {FIGDIR}/bore.png")
