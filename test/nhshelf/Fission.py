#!/usr/bin/env python3
"""nhshelf: 棚に乗り上げた孤立波の分裂を解析する(docs/nonhydrostatic_plan.md §11 Phase 5/7)

  使い方: ./Fission.py [result_dir ...]   既定は result(V2), result_v1(V1), result_h(静水圧)
  最終時刻の水深分布の中央行で、棚(x > 130 m)上の水面 η = h + z − H2 の極大
  (η > 0.1 a0、隣より高い)を数えて位置と高さを出す。先頭ソリトンの高さを、
  棚の静水深 H2 と比べる。斜面式は user_geoinfo shelf_slope と対で保守。
"""
import sys, os, glob
import numpy as np
H1 = 1.0; H2 = 0.5; A0 = 0.1; dx = 0.25
def z_of(x): return 0.5 * np.clip((x - 120.0) / 10.0, 0.0, 1.0)
def last(resdir):
    files = [f for f in sorted(glob.glob(os.path.join(resdir, "H[0-9][0-9][0-9][0-9].txt"))) if not f.endswith(("H9998.txt", "H9999.txt"))]
    a = np.loadtxt(files[-1]); return a[a.shape[0] // 2, :]
if __name__ == "__main__":
    for d in (sys.argv[1:] or ["result", "result_v1", "result_h"]):
        if not os.path.isdir(d): continue
        h = last(d); x = (np.arange(len(h)) + 0.5) * dx; z = z_of(x)
        eta = h + z - H1
        shelf = x > 135.0
        pk = [i for i in range(1, len(h) - 1) if shelf[i] and eta[i] > 0.1 * A0 and eta[i] >= eta[i-1] and eta[i] > eta[i+1]]
        # 近接ピークの統合(2 m 以内)
        merged = []
        for i in pk:
            if merged and x[i] - x[merged[-1]] < 2.0:
                if eta[i] > eta[merged[-1]]: merged[-1] = i
            else:
                merged.append(i)
        print(f"=== {d}: peaks on the shelf = {len(merged)}")
        for i in merged[::-1][:6]:
            print(f"   x = {x[i]:7.2f} m   eta = {eta[i]:.4f} m  (eta/H2 = {eta[i]/H2:.3f})")
        back = (x > 135.0) & (x < 150.0)
        print(f"   reflected/trailing max |eta| at 135-150 m: {np.abs(eta[back]).max():.4f} m")
