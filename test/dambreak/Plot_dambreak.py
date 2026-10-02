#!/usr/bin/env python3
"""ダム破壊: 数値解と Stoker 解析解の比較図(PNG)。

使い方:  python3 Plot_dambreak.py [出力 PNG] [結果ディレクトリ ...]
  引数なしなら result(と存在すれば result_scheme2, result_scheme3)を描き、
  dambreak.png に書く。各ディレクトリには Check_stoker.py が書く
  stoker.csv が必要(RESDIR=<dir> python3 Check_stoker.py)。
"""
import csv, os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

out = sys.argv[1] if len(sys.argv) > 1 else "dambreak.png"
dirs = sys.argv[2:] or [d for d in ("result", "result_scheme2", "result_scheme3") if os.path.isdir(d)]
labels = {"result": "scheme 1 (cell gradient, default)",
          "result_scheme2": "scheme 2 (momentum-cons., upwind)",
          "result_scheme3": "scheme 3 (momentum-cons., MUSCL)"}
colors = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]

def load(d):
    rows = list(csv.DictReader(open(os.path.join(d, "stoker.csv"))))
    return {k: [float(r[k]) for r in rows] for k in rows[0]}

data = {d: load(d) for d in dirs}
ana = data[dirs[0]]

fig, axes = plt.subplots(3, 1, figsize=(9, 10.5), facecolor="#fcfcfb")
panels = [("h_num", "h_ana", "h (m)", (150, 850), None),
          ("u_num", "u_ana", "u (m/s)", (150, 850), None),
          ("h_num", "h_ana", "h (m), bore region", (640, 840), (0.5, 7.5))]
for ax, (num, an, ylab, xr, yr) in zip(axes, panels):
    ax.set_facecolor("#fcfcfb")
    ax.plot(ana["x"], ana[an], color="#0b0b0b", lw=2.4, label="Stoker (analytic)", zorder=5)
    for c, d in zip(colors, dirs):
        ax.plot(data[d]["x"], data[d][num], color=c, lw=1.6, label=labels.get(d, d))
    ax.set_xlim(*xr)
    if yr: ax.set_ylim(*yr)
    ax.set_ylabel(ylab, color="#52514e")
    ax.grid(True, color="#e6e5e2", lw=0.6)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    ax.tick_params(colors="#52514e")
axes[0].set_title("Wet-bed dam break, t = 30 s, centre row (hl = 10 m, hr = 1 m, dx = 2 m)",
                  color="#0b0b0b", loc="left")
axes[0].legend(frameon=False, loc="upper right", fontsize=9)
axes[2].set_xlabel("x (m)", color="#52514e")
fig.tight_layout()
fig.savefig(out, dpi=130)
print("wrote", out)
