#!/usr/bin/env python3
"""nhbreak: 海浜斜面を遡上する孤立波の解析(docs/nonhydrostatic_plan.md §11 Phase 6)

  使い方: ./Runup.py [result_dir ...]   既定は result(NH), result_h(静水圧)
  水深分布 H00NN.txt の中央行から、各時刻の湿潤前縁(h > hthr)の x と、その地盤高
  − H = 遡上高 R(t)(静水面基準)を追い、最大遡上高 R_max/H を Synolakis (1987)
  の砕波性孤立波の遡上則 R/H = 0.918 (a/H)^0.606(a/H = 0.28 で 0.425)と比べる。
  波頂の高さの推移も出す。
  斜面式 z = max(0, (x − 150)/19.85) は user_geoinfo beach_slope と対で保守。
"""
import sys, os, glob
import numpy as np
H = 1.0; dx = 0.25; XT = 150.0; COT = 19.85; HTHR = 0.01
def z_of(x): return np.maximum(0.0, (x - XT) / COT)
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
if __name__ == "__main__":
    dirs = sys.argv[1:] or ["result", "result_h"]
    for d in dirs:
        if not os.path.isdir(d): continue
        prof = load(d)
        x = (np.arange(len(prof[0][1])) + 0.5) * dx
        z = z_of(x)
        rmax, tmax = -1.0, 0.0
        print(f"=== {d} ===")
        print("   t(s)   x_front(m)   R(t)/H   eta_max/H  x_crest(m)")
        for t, h in prof:
            wet = np.where(h > HTHR)[0]
            xf = x[wet[-1]] if len(wet) else 0.0
            R = z_of(xf) - H
            eta = np.where(h > HTHR, h + z - H, -np.inf)   # 湿潤セルだけの水面高
            ic = int(np.argmax(eta))
            if R > rmax: rmax, tmax = R, t
            if int(round(t)) % 4 == 0:
                print(f"  {t:5.1f}   {xf:8.2f}   {R/H:7.3f}   {eta.max()/H:8.3f}   {x[ic]:8.2f}")
        print(f"  R_max/H = {rmax/H:.3f} at t = {tmax:.1f} s   (Synolakis 1987 breaking run-up law 0.918 (a/H)^0.606 = {0.918*0.28**0.606:.3f})")
