#!/usr/bin/env python3
"""test/pump の図を figs/*.png に描く(事前に ./Run.sh を実行しておく)。

  python3 Fig.py

- figs/storage.png : S_surf / S_grnd / S_total の時系列と、総揚水量 0.01002 m3/s からの解析値
                     S_total(t) = 0.05 − 0.01002 t / (42 × 42)
- figs/map.png     : 最終時刻の地下水位 Hg の分布(中央セルの井戸 2 の局所的な低下)
"""
import glob, os
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
        rows.append([int(hh) * 3600 + int(mm) * 60 + float(ss)] + [float(v.rstrip("%")) for v in f[1:len(names)]])
    return names, np.array(rows)


names, lg = read_log("result/Log.txt")
t = lg[:, 0]
Q = 0.01 + 2e-5
A = 42.0 * 42.0
fig, ax = plt.subplots(figsize=(8, 4))
for key, lab, c in [("S_surf(m)", "地表 S_surf", "C0"), ("S_grnd(m)", "地下 S_grnd", "C1"), ("S_total(m)", "合計 S_total", "k")]:
    if key in names:
        ax.plot(t, lg[:, names.index(key)], "o-", ms=3, color=c, label=lab)
ax.plot(t, 0.05 - Q * t / A, "r--", lw=1, label="解析値 0.05 − Q t / A(Q = 0.01002 m³/s)")
ax.set_xlabel("t (s)")
ax.set_ylabel("柱状換算水深 (m)")
ax.set_title("井戸揚水: 初期水 0.05 m が Green-Ampt で地下へ入り、一定流量で汲み上げられる", fontsize=10)
ax.grid(alpha=0.3)
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig("figs/storage.png", dpi=110)
plt.close(fig)
k = names.index("S_total(m)")
print("S_total end %.15f, analytic %.15f, rel diff %.1e" % (lg[-1, k], 0.05 - Q * 3600 / A, lg[-1, k] / (0.05 - Q * 3600 / A) - 1))

hg = sorted(glob.glob("result/Hg[0-9]*.txt"))
if hg:
    a = np.loadtxt(hg[-1])
    fig, ax = plt.subplots(figsize=(5, 4.2))
    im = ax.imshow(a, origin="lower", extent=[0, 42, 0, 42], cmap="viridis")
    ax.set_title(f"地下水位 Hg (m), {os.path.basename(hg[-1])}", fontsize=10)
    ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
    fig.colorbar(im, ax=ax, shrink=0.8)
    fig.tight_layout()
    fig.savefig("figs/map.png", dpi=110)
    plt.close(fig)
    print("Hg: center %.6f, edge %.6f, max-min %.2e" % (a[10, 10], a[0, 0], a.max() - a.min()))
