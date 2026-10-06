#!/usr/bin/env python3
"""test/conduit の図を figs/*.png に描く(事前に ./Run.sh と ./Run_lat.sh を実行しておく)。

  python3 Fig.py

- figs/equilibrium.png : 模式実験 A(param.txt)。S_surf / S_grnd / S_total の時系列と
                         解析平衡値 h_eq = 0.049/1.001、hgc_eq = 51.1/1001
- figs/lateral.png     : 模式実験 B(param_lat.txt)。最終時刻の管路層水頭 Hgc と地表水深 H の分布
                         (中心 3×3 の枡から sqrt 乱流則で放射状に広がる。点対称・転置対称の確認)
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


HEQ, HGEQ = 0.049 / 1.001, 51.1 / 1001.0
names, lg = read_log("result/Log.txt")
t = lg[:, 0]
fig, ax = plt.subplots(figsize=(8, 4))
for key, lab, c in [("S_surf(m)", "地表 S_surf", "C0"), ("S_grnd(m)", "管路層 S_grnd", "C1"), ("S_total(m)", "合計 S_total", "k")]:
    ax.plot(t, lg[:, names.index(key)], "o-", ms=3, color=c, label=lab)
ax.axhline(HEQ, color="C0", ls="--", lw=1, label=f"解析平衡 h_eq = {HEQ:.10f}")
ax.axhline(HGEQ, color="C1", ls="--", lw=1, label=f"解析平衡 hgc_eq = {HGEQ:.10f}")
ax.set_xlabel("t (s)")
ax.set_ylabel("柱状換算水深 (m)")
ax.set_title("模式実験 A: 一様湛水 0.1 m が枡から管路層へ落ち、被圧水頭と平衡する", fontsize=10)
ax.grid(alpha=0.3)
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig("figs/equilibrium.png", dpi=110)
plt.close(fig)
i = names.index("S_surf(m)"); j = names.index("S_grnd(m)"); k = names.index("S_total(m)")
print("end: S_surf %.14f (h_eq %.14f), S_grnd %.14f (hgc_eq %.14f), S_total %.14f (init %.14f)"
      % (lg[-1, i], HEQ, lg[-1, j], HGEQ, lg[-1, k], lg[0, k]))

if os.path.isdir("result_lat"):
    hg = sorted(glob.glob("result_lat/Hgc*.txt"))
    hh = sorted(glob.glob("result_lat/H0*.txt"))
    if hg and hh:
        A = np.loadtxt(hg[-1]); H = np.loadtxt(hh[-1])
        fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
        for ax, a, title in [(axes[0], A, f"管路層水頭 Hgc (m) {os.path.basename(hg[-1])}"),
                             (axes[1], H, f"地表水深 H (m) {os.path.basename(hh[-1])}")]:
            im = ax.imshow(a, origin="lower", extent=[0, 42, 0, 42], cmap="viridis")
            ax.set_title(title, fontsize=9); ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
            fig.colorbar(im, ax=ax, shrink=0.8)
        fig.suptitle("模式実験 B: 中心 3×3 の枡、sqrt 乱流則の側方拡散、Green-Ampt・漏水の全結合", fontsize=10)
        fig.tight_layout()
        fig.savefig("figs/lateral.png", dpi=110)
        plt.close(fig)
        print("Hgc point symmetry max |A - rot180(A)| = %.3e, transpose %.3e" % (np.abs(A - A[::-1, ::-1]).max(), np.abs(A - A.T).max()))
        nl, lgl = read_log("result_lat/Log.txt")
        kk = nl.index("S_total(m)")
        print("lat: S_total init %.14f end %.14f" % (lgl[0, kk], lgl[-1, kk]))
