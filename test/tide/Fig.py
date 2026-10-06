#!/usr/bin/env python3
"""test/tide の図を figs/*.png に描く(事前に ./Run.sh を実行しておく)。

  python3 Fig.py

- figs/storage.png : 画面出力(Log.txt)の平均水深 S(t) と潮位の時系列。
                     陸水の海への排水(S 減少)→ 潮位が陸の水面を超えた後の浸水(S 増加)
- figs/map.png     : 水位 e の分布(t = 60, 120, 180, 240 s)
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
matplotlib.rcParams["font.family"] = ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs("figs", exist_ok=True)


def read_log(path):
    names, rows = None, []
    for line in open(path):
        if line.startswith("time,"):
            names = [s.strip() for s in line.split(",")]
            continue
        f = line.split()
        if names is None or len(f) < len(names) or ":" not in f[0]:
            continue
        hh, mm, ss = f[0].split(":")
        vals = [int(hh) * 3600 + int(mm) * 60 + float(ss)]
        vals += [float(v.rstrip("%")) for v in f[1:len(names)]]
        rows.append(vals)
    return names, np.array(rows)


names, lg = read_log("result/Log.txt")
t = lg[:, 0]
S = lg[:, names.index("S(m)")]
tide = np.interp(t, [0, 120, 240], [0.0, 2.0, 2.0])      # tival: 0 → 2 m (0〜2 min)、以後 2 m

fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(t, S, "o-", ms=3, label="平均水深 S(陸+海セル)")
ax.set_xlabel("t (s)")
ax.set_ylabel("S (m)")
ax.grid(alpha=0.3)
ax2 = ax.twinx()
ax2.plot(t, tide, "C3--", label="潮位(m, T.P.)")
ax2.axhline(1.5, color="0.6", lw=0.8)
ax2.text(2, 1.52, "陸の初期水面 z + h0 = 1.5 m", fontsize=8, color="0.4")
ax2.set_ylabel("潮位 (m)")
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, loc="lower right", fontsize=9)
ax.set_title("潮位境界: 陸水の排水(S 減少)→ 潮位が陸の水面を超えて浸水(S 増加)", fontsize=10)
fig.tight_layout()
fig.savefig("figs/storage.png", dpi=110)
plt.close(fig)

fig, axes = plt.subplots(1, 4, figsize=(14, 3.8))
for ax, n in zip(axes, [1, 2, 3, 4]):
    e = np.loadtxt(f"result/E{n:04d}.txt")
    h = np.loadtxt(f"result/H{n:04d}.txt") if os.path.isfile(f"result/H{n:04d}.txt") else None
    e = np.where(h <= 1e-6, np.nan, e) if h is not None else e
    im = ax.imshow(e, origin="lower", extent=[0, 210, 0, 210], vmin=0.5, vmax=2.0, cmap="viridis")
    ax.set_title(f"水位 e (m), t = {60*n} s(潮位 {np.interp(60*n,[0,120,240],[0,2,2]):.1f} m)", fontsize=9)
    ax.set_xlabel("x (m)")
axes[0].set_ylabel("y (m)")
fig.colorbar(im, ax=axes, shrink=0.8, label="e (m)")
fig.savefig("figs/map.png", dpi=110, bbox_inches="tight")
plt.close(fig)
print("S: t=0 %.4f, min %.4f at %.0f s, end %.4f" % (S[0], S.min(), t[S.argmin()], S[-1]))
