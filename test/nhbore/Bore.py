#!/usr/bin/env python3
"""nhbore: 段差から分裂する undular bore を解析する(docs/nonhydrostatic_plan.md §11 Phase 5)

  使い方: ./Bore.py [result_dir ...]   既定は result(NH、a/H = 0.1)、result_20(a/H = 0.2)、result_h(静水圧)
  水深分布 H00NN.txt の中央行から、各時刻の先頭波(最前の極大)の位置と高さ η_1/a、
  波列の山の数(η > 1.1a の極大)、前面(η = a/2 を横切る位置)の速度を表にする。
  比較: KdV の undular bore(Gurevich & Pitaevskii 1974)では先頭波の高さが 2a に漸近し、
  先頭の速度は √(gH)(1 + a/H)(高さ 2a の孤立波の速度)、後端は √(gH)(1 − a/(2H)) ... の
  扇状に広がる。静水圧は段波のまま(先頭波なし)。計算本体の外(方針 10)。numpy のみ。
"""
import sys, os, glob
import numpy as np
G = 9.8; H = 1.0; dx = 0.25
def load(resdir):
    times = {}
    for l in open(os.path.join(resdir, "FILENUMBER.csv")):
        if l.startswith("#"): continue
        c = l.split(","); times[int(c[0])] = float(c[2])
    out = []
    for f in sorted(glob.glob(os.path.join(resdir, "H[0-9][0-9][0-9][0-9].txt"))):
        if f.endswith(("H9998.txt", "H9999.txt")): continue
        k = int(os.path.basename(f)[1:5]); a = np.loadtxt(f)
        out.append((times.get(k, float("nan")), a[a.shape[0] // 2, :]))
    return out
def analyze(resdir):
    prof = load(resdir)
    x = (np.arange(len(prof[0][1])) + 0.5) * dx
    a0 = prof[0][1].max() - H
    rows = []
    for t, h in prof:
        eta = h - H
        # 前面: 右から見て最初に η > a0/2 になる位置
        above = np.where(eta > 0.5 * a0)[0]
        xf = x[above[-1]] if len(above) else float("nan")
        # 極大(両隣より高く、η > 1.1 a0)
        pk = [i for i in range(1, len(h) - 1) if eta[i] > 1.1 * a0 and eta[i] >= eta[i-1] and eta[i] > eta[i+1]]
        if pk:
            i1 = pk[-1]
            y0, y1, y2 = eta[i1-1], eta[i1], eta[i1+1]
            d = 0.5 * (y0 - y2) / (y0 - 2*y1 + y2) if (y0 - 2*y1 + y2) != 0 else 0.0
            x1, e1 = x[i1] + d * dx, y1 - 0.25 * (y0 - y2) * d
        else:
            x1, e1 = float("nan"), float("nan")
        rows.append((t, xf, x1, e1 / a0, len(pk)))
    return a0, np.array(rows)
if __name__ == "__main__":
    for d in (sys.argv[1:] or ["result", "result_20", "result_h"]):
        if not os.path.isdir(d): continue
        a0, r = analyze(d)
        print(f"=== {d}: a0/H = {a0/H:.3f}   (KdV undular bore: leading wave -> 2a, speed -> sqrt(gH)(1 + a/H) = {np.sqrt(G*H)*(1+a0/H):.3f} m/s)")
        print("    t(s)  x_front  x_lead  eta_1/a  n_peaks")
        for t, xf, x1, e1, n in r:
            print(f"  {t:6.1f}  {xf:7.2f}  {x1:7.2f}  {e1:7.3f}  {int(n):4d}")
        sel = r[:, 0] >= r[-1, 0] * 0.5
        if np.isfinite(r[sel, 2]).sum() >= 3:
            c1 = np.polyfit(r[sel, 0][np.isfinite(r[sel, 2])], r[sel, 2][np.isfinite(r[sel, 2])], 1)[0]
            print(f"  leading-wave speed (later half) = {c1:.3f} m/s = {c1/np.sqrt(G*H):.4f} sqrt(gH)")
