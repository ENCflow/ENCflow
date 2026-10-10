#!/usr/bin/env python3
"""nest_reflect の非静水圧版(σ = 2 m。plan §16.5)の解析: 一様細格子(fine_nh)を基準に、
   粗格子単独(coarse_nh)と比 3 双方向ネストのルート・子(root/child_r3_nh1 = 帯の φ を
   親の φ の Dirichlet、r3_nh0 = 帯の φ = 0)の水位誤差を親格子上で比較する(analyze.py と同じ
   手順・同じ領域定義)。使い方: python3 analyze_nh.py
"""
import numpy as np, os
I0, NF, H0, A = 160, 67, 1.0, 0.2

def load(d, n):
    return np.loadtxt(os.path.join(d, "E%04d.txt" % n))

def to_parent(e, r):
    n = e.shape[0] // r
    return e.reshape(n, r, n, r).mean(axis=(1, 3))

inside = np.zeros((385, 385), bool); inside[I0 - 1:I0 - 1 + NF, I0 - 1:I0 - 1 + NF] = True
outside = ~inside
print("time  run           RMS_in    MAX_in    RMS_out   MAX_out   (η − η_fine_nh→parent, m)")
for n in (2, 4, 6, 8, 10):
    fn = os.path.join("result_fine_nh", "E%04d.txt" % n)
    if not os.path.exists(fn):
        continue
    ef = to_parent(load("result_fine_nh", n), 3) - H0
    for name in ("coarse_nh", "root_r3_nh1", "root_r3_nh0"):
        d = "result_" + name
        if not os.path.exists(os.path.join(d, "E%04d.txt" % n)):
            continue
        de = load(d, n) - H0 - ef
        print("%4d  %-12s  %.2e  %.2e  %.2e  %.2e" % (n, name, np.sqrt(np.mean(de[inside] ** 2)), np.max(np.abs(de[inside])),
                                                  np.sqrt(np.mean(de[outside] ** 2)), np.max(np.abs(de[outside]))))
    for name in ("child_r3_nh1", "child_r3_nh0"):
        d = "result_" + name
        if not os.path.exists(os.path.join(d, "E%04d.txt" % n)):
            continue
        de = to_parent(load(d, n) - H0, 3) - ef[I0 - 1:I0 - 1 + NF, I0 - 1:I0 - 1 + NF]
        dc = de[2:-2, 2:-2]
        print("%4d  %-12s  %.2e  %.2e  core: %.2e  %.2e  (子。親格子へ平均。core = 外周 2 親セルを除く)"
              % (n, name, np.sqrt(np.mean(de ** 2)), np.max(np.abs(de)), np.sqrt(np.mean(dc ** 2)), np.max(np.abs(dc))))
