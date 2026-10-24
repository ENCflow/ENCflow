#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# nhbottom 海底地滑り(result_ls_*)の図表: 静水圧 / NH(加速度項なし)/ NH + 加速度項の
#   プローブ波形と中央断面、dt 半減(ls_b025, ls_n025)による一段遅れの影響の定量
#   figs/landslide.png、標準出力に数表
#   引数 en: 英語表記で en/figs/ に出力(python3 Landslide.py en)
import sys, os, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
EN = "en" in sys.argv[1:]
def T(ja, en): return en if EN else ja
FIGDIR = "en/figs" if EN else "figs"
plt.rcParams.update({"font.family": ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"], "font.size": 10})

DX, J = 5.0, 19
CASES = [("result_ls_h", "#8a8983", T("静水圧", "Hydrostatic")),
         ("result_ls_n", "#2a78d6", T("NH(f_nh_slope=1、加速度項なし)", "NH (f_nh_slope=1, no acceleration term)")),
         ("result_ls_b", "#eb6834", T("NH + 加速度項(f_nh_bottom=1)", "NH + acceleration term (f_nh_bottom=1)"))]
PROBES = [(2, T("x = 212 m(汀線直後、水深 5 m)", "x = 212 m (just off the shoreline, depth 5 m)")),
          (3, T("x = 298 m(斜面下端、水深 39 m)", "x = 298 m (foot of the slope, depth 39 m)")),
          (4, T("x = 398 m(湖央)", "x = 398 m (lake centre)")), (5, T("x = 548 m(対岸側)", "x = 548 m (far-shore side)"))]
os.makedirs(FIGDIR, exist_ok=True)
x = (np.arange(120) + 0.5) * DX

def probe(rdir, n):
    d = np.loadtxt("%s/probes/probe%04d.csv" % (rdir, n), delimiter=",", comments="#")
    return d[:, 0] * 3600, d[:, 2] + d[:, 3]

def times(rdir):
    return {int(l.split(",")[0]): float(l.split(",")[2]) for l in open(rdir + "/FILENUMBER.csv") if not l.startswith("#")}

def surf(rdir, k):
    h = np.loadtxt("%s/H%04d.txt" % (rdir, k))[J]; z = np.loadtxt("%s/Z%04d.txt" % (rdir, k))[J]
    return np.where(h > 0.01, z + h, np.nan), z

fig, axes = plt.subplots(3, 2, figsize=(13, 9))
for ax, (n, lab) in zip(axes.flat[:4], PROBES):
    for rdir, col, cl in CASES:
        t, e = probe(rdir, n)
        ax.plot(t, e, color=col, lw=1.3, label=cl)
    ax.set_title(lab, fontsize=10); ax.grid(); ax.set_ylabel(T("水面 (m)", "Surface (m)")); ax.set_xlabel("t (s)"); ax.set_xlim(0, 120)
axes.flat[0].legend(fontsize=8)
for ax, tsel in zip(axes.flat[4:], (20.0, 40.0)):
    for rdir, col, cl in CASES:
        tm = times(rdir); k = min(tm, key=lambda q: abs(tm[q] - tsel))
        s, z = surf(rdir, k)
        ax.plot(x, s, color=col, lw=1.3, label=cl)
    ax.plot(x, z, "k--", lw=0.8, label=T("底面 z(t)/10", "bottom z(t)/10"))
    ax.set_xlim(180, 600); ax.set_ylim(-4, 4); ax.grid()
    ax.set_title(T("中央断面の水面 t = %.0f s", "Surface along the centre section, t = %.0f s") % tsel, fontsize=10); ax.set_xlabel("x (m)"); ax.set_ylabel(T("水面 (m)", "Surface (m)"))
plt.tight_layout(); plt.savefig(f"{FIGDIR}/landslide.png", dpi=100); plt.close()

print(T("| プローブ | 量 | ", "| Probe | Quantity | ") + " | ".join(c[2] for c in CASES) + " |")
print("|---|---|" + "---:|" * len(CASES))
for n, lab in PROBES:
    vals = [probe(rdir, n)[1] for rdir, _, _ in CASES]
    print(T("| %s | 最低 (m) | ", "| %s | Minimum (m) | ") % lab + " | ".join("%.3f" % v.min() for v in vals) + " |")
    print(T("| %s | 最高 (m) | ", "| %s | Maximum (m) | ") % lab + " | ".join("%.3f" % v.max() for v in vals) + " |")
# 一段遅れ: dt 半減との差(加速度項あり)を、加速度項なしの dt 感度と比べる
print()
print(T("| プローブ | max\\|Δη\\| 加速度項あり dt 0.05 vs 0.025 (m) | 同 加速度項なし (m) | 加速度項の効果 max\\|η_b − η_n\\| (m) |",
        "| Probe | max\\|Δη\\| with acceleration term, dt 0.05 vs 0.025 (m) | Same, without acceleration term (m) | Effect of the acceleration term max\\|η_b − η_n\\| (m) |"))
print("|---|---:|---:|---:|")
for n, lab in PROBES:
    tb, eb = probe("result_ls_b", n); tb2, eb2 = probe("result_ls_b025", n)
    tn, en = probe("result_ls_n", n); tn2, en2 = probe("result_ls_n025", n)
    m = min(len(eb), len(eb2), len(en), len(en2))
    print("| %s | %.4f | %.4f | %.4f |" % (lab, np.abs(eb[:m] - eb2[:m]).max(), np.abs(en[:m] - en2[:m]).max(), np.abs(eb[:m] - en[:m]).max()))
