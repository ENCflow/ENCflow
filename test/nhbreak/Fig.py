#!/usr/bin/env python3
"""nhbreak: README 用の図を figs/runup.png に描く

  使い方: ./Run.sh(result = NH + 砕波スイッチ)、./encflow param_h.txt(result_h = 静水圧)の後に
          ./Fig.py。result_ns(NH、スイッチなし。param.txt の f_nh_breaking=0、dir_result='result_ns')が
          あればそれも描く。
  上段: 遡上高 R(t)/H(湿潤前縁の地盤高 − H)と Synolakis (1987) の砕波遡上則
  下段: 斜面付近の水面と地形(実寸)。t = 28, 36, 42 s
  計算本体の外(方針 10)。numpy + matplotlib。
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from Runup import load, z_of, H, dx, HTHR

plt.rcParams.update({"font.family": ["IPAGothic", "DejaVu Sans"], "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": "#e3e2dd", "grid.linewidth": 0.6,
                     "lines.linewidth": 1.5})
C_NH, C_HY, C_NS, C_BED, C_TH = "#2a78d6", "#eb6834", "#1baf7a", "#9c9a94", "#6b6a66"
LAW = 0.918 * 0.28 ** 0.606

def runup(prof, x):
    out = []
    for t, h in prof:
        wet = np.where(h > HTHR)[0]
        xf = x[wet[-1]] if len(wet) else 0.0
        out.append((t, z_of(xf) - H))
    return np.array(out)

if __name__ == "__main__":
    os.makedirs("figs", exist_ok=True)
    cases = [("result", "非静水圧 + 砕波スイッチ(param.txt)", C_NH, "-"),
             ("result_h", "静水圧", C_HY, "-"),
             ("result_ns", "非静水圧、スイッチなし", C_NS, "--")]
    cases = [c for c in cases if os.path.isdir(c[0])]
    data = {d: load(d) for d, *_ in cases}
    x = (np.arange(len(data[cases[0][0]][0][1])) + 0.5) * dx
    z = z_of(x)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7.2, 6.2), gridspec_kw={"height_ratios": [1, 1.3]})
    for d, lab, col, ls in cases:
        r = runup(data[d], x)
        ax1.plot(r[:, 0], r[:, 1] / H, color=col, ls=ls, label=f"{lab}: R_max/H = {r[:, 1].max()/H:.2f}")
    ax1.axhline(LAW, color=C_TH, lw=1.0, ls=":", label=f"実験則 0.918 (a/H)^0.606 = {LAW:.2f}")
    ax1.set_xlim(0, 60); ax1.set_ylim(-0.35, 1.0)
    ax1.set_xlabel("t (s)"); ax1.set_ylabel("R(t) / H")
    ax1.set_title("遡上高の推移(湿潤前縁 h > 1 cm の地盤高 − H)", fontsize=10, loc="left")
    ax1.legend(loc="upper left", frameon=False, fontsize=8)
    ax2.fill_between(x, -0.2, z, color=C_BED, alpha=0.35, lw=0)
    for i, ts in enumerate([28.0, 36.0, 42.0]):
        for d, lab, col, ls in cases[:2]:
            t, h = min(data[d], key=lambda p: abs(p[0] - ts))
            ws = np.where(h > HTHR, h + z, np.nan)
            ax2.plot(x, ws, color=col, ls=ls, alpha=0.45 + 0.55 * i / 2, label=lab if i == 2 else None)
            if d == "result":
                wet = np.where(h > HTHR)[0]
                ic = int(np.nanargmax(np.where(h > HTHR, h + z - H, -np.inf)))
                xa, ya = (x[wet[-1]], ws[wet[-1]]) if i == 2 else (x[ic], ws[ic])
                ax2.annotate(f"t = {ts:.0f} s", (xa, ya), xytext=(-6, 10), textcoords="offset points",
                             fontsize=8, color="#52514e", ha="right")
    ax2.set_xlim(100, 190); ax2.set_ylim(0.0, 2.0)
    ax2.set_xlabel("x (m)"); ax2.set_ylabel("水面・地盤高 (m)")
    ax2.set_title("斜面付近の水面(縦を強調。色が濃いほど後の時刻)", fontsize=10, loc="left")
    ax2.legend(loc="upper left", frameon=False, fontsize=8)
    fig.suptitle("砕波性孤立波の海浜遡上(H = 1 m、a/H = 0.28、斜面 1:19.85、Δx = 0.25 m)", fontsize=10, x=0.02, ha="left")
    fig.tight_layout(); fig.savefig("figs/runup.png", dpi=150)
    print("written: figs/runup.png")
