#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# nhbottom の図表: 区間隆起の 3 ケース(result_h: 静水圧、result_n: NH 加速度項なし、
#   result: NH 加速度項あり)を線形理論(Theory.py)と比べる。
#   figs/uplift.png: 断面(t = 1, 5, 20 s)とプローブ x = xc+200 m の時系列
#   標準出力: 数表(README に貼る)
#   引数 en: 英語表記で en/figs/ に出力(python3 Fig.py en)
import sys, os, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
EN = "en" in sys.argv[1:]
def T(ja, en): return en if EN else ja
FIGDIR = "en/figs" if EN else "figs"
plt.rcParams.update({"font.family": ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"], "font.size": 10})
from Theory import Theory, XC, TC, H, LABEL

DX, J = 1.25, 15
CASES = [("result_h", "hydro", "#8a8983", T("静水圧", "Hydrostatic")),
         ("result_n", "nh0", "#2a78d6", T("NH(加速度項なし)", "NH (no acceleration term)")),
         ("result", "nh1", "#eb6834", T("NH(加速度項あり f_nh_bottom=1)", "NH (with acceleration term, f_nh_bottom=1)"))]
PROBE, XP = 3, XC + 200.0
os.makedirs(FIGDIR, exist_ok=True)
x = (np.arange(800) + 0.5) * DX

def times(rdir):
    return {int(l.split(",")[0]): float(l.split(",")[2]) for l in open(rdir + "/FILENUMBER.csv") if not l.startswith("#")}

def surf(rdir, k):
    return np.loadtxt("%s/E%04d.txt" % (rdir, k))[J] - H

def probe(rdir):
    d = np.loadtxt("%s/probes/probe%04d.csv" % (rdir, PROBE), delimiter=",", comments="#")
    return d[:, 0] * 3600, d[:, 2] + d[:, 3] - H

th = {m: Theory(m) for m in ("hydro", "nh0", "nh1", "exact")}
fig, axes = plt.subplots(2, 2, figsize=(13, 8))
for ax, t in zip(axes.flat[:3], (1.0, 5.0, 20.0)):
    for rdir, m, col, lab in CASES:
        tm = times(rdir)
        k = min(tm, key=lambda q: abs(tm[q] - t))
        ax.plot(x - XC, surf(rdir, k), color=col, lw=1.4, label="ENCflow " + lab)
        ax.plot(th[m].x - XC, th[m].surface(t), color=col, lw=1.0, ls="--", label=T("理論 ", "theory ") + LABEL[m])
    ax.plot(th["exact"].x - XC, th["exact"].surface(t), "k:", lw=1.0, label=T("理論 厳密", "theory, exact"))
    ax.set_xlim(-60, 60) if t <= 1.0 else ax.set_xlim(-250 if t > 5 else -120, 250 if t > 5 else 120)
    ax.set_title("t = %.0f s" % t, fontsize=10); ax.grid(); ax.set_ylabel("η (m)"); ax.set_xlabel("x − xc (m)")
axes.flat[0].legend(fontsize=7)
ax = axes.flat[3]
tt = np.arange(0, 40.0001, 0.05)
rows = []
for rdir, m, col, lab in CASES:
    t, e = probe(rdir)
    ax.plot(t, e, color=col, lw=1.4, label="ENCflow " + lab)
    et = th[m].probe(XP, tt)
    ax.plot(tt, et, color=col, lw=1.0, ls="--")
    i, j = int(np.argmax(e)), int(np.argmax(et))
    rows.append((lab, e[i], t[i], et[j], tt[j]))
ee = th["exact"].probe(XP, tt)
ax.plot(tt, ee, "k:", lw=1.0, label=T("理論 厳密", "theory, exact"))
ax.set_xlim(15, 40); ax.grid(); ax.set_title(T("x = xc + 200 m の水面(破線: 各モデルの線形理論)", "Surface at x = xc + 200 m (dashed: linear theory of each model)"), fontsize=10)
ax.set_xlabel("t (s)"); ax.set_ylabel("η (m)"); ax.legend(fontsize=7)
plt.tight_layout(); plt.savefig(f"{FIGDIR}/uplift.png", dpi=100); plt.close()

je = int(np.argmax(ee))
print(T("| ケース | η_max ENCflow (m) | t (s) | η_max 理論 (m) | t (s) | ENC/理論 | 理論/厳密 |",
        "| Case | η_max ENCflow (m) | t (s) | η_max theory (m) | t (s) | ENC/theory | theory/exact |"))
print("|---|---:|---:|---:|---:|---:|---:|")
for lab, e1, t1, e2, t2 in rows:
    print("| %s | %.4f | %.2f | %.4f | %.2f | %.3f | %.3f |" % (lab, e1, t1, e2, t2, e1 / e2, e2 / ee[je]))
print(T("| 厳密(線形ポテンシャル流) | — | — | %.4f | %.2f | — | 1 |", "| Exact (linear potential flow) | — | — | %.4f | %.2f | — | 1 |") % (ee[je], tt[je]))
