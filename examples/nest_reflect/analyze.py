#!/usr/bin/env python3
"""nest_reflect の解析: 一様細格子(fine。比 3 の解像度で全域)を基準に、
   粗格子単独(coarse)と、比 3・比 5 の双方向ネストのルート(root_r3/r5)の
   水位誤差を親格子上で比較する。細格子は親セルごとに 3×3 の平均で粗格子化する。
   子の足元(親セル 160..226)の内側・外側に分けて RMS と最大を出す。
   「反射率」: 波が子を出た後(t >= 6 s)の子の足元内の最大|Δη| / 初期振幅 a。
   使い方: python3 analyze.py   (各ランの result_*/E00NN.txt を読む)
"""
import numpy as np, os, sys
A = 0.2
I0, NF = 160, 67          # 子の足元(親セル。1 始まり)
H0 = 1.0

def load(d, n):
    fn = os.path.join(d, "E%04d.txt" % n)
    return np.loadtxt(fn)        # 行 j、列 i

def fine_to_parent(e):
    n = e.shape[0] // 3
    return e.reshape(n, 3, n, 3).mean(axis=(1, 3))

def child_to_parent(e, r):
    n = e.shape[0] // r
    return e.reshape(n, r, n, r).mean(axis=(1, 3))

def stats(d, mask):
    v = d[mask]
    return np.sqrt(np.mean(v ** 2)), np.max(np.abs(v))

inside = np.zeros((385, 385), bool)
inside[I0 - 1:I0 - 1 + NF, I0 - 1:I0 - 1 + NF] = True
# 帯(nb=3 親セル分の余裕)を除いた子内部に対応する親セル
core = np.zeros((385, 385), bool)
core[I0 + 1:I0 - 1 + NF - 2, I0 + 1:I0 - 1 + NF - 2] = True
outside = ~inside

runs = {"coarse": "result_coarse", "root_r3": "result_root_r3", "root_r5": "result_root_r5"}
print("time  run        RMS_in    MAX_in    RMS_out   MAX_out   (η − η_fine→parent, m)")
for n in (2, 4, 6, 8, 10):
    ef = fine_to_parent(load("result_fine", n)) - H0
    for name, d in runs.items():
        if not os.path.exists(os.path.join(d, "E%04d.txt" % n)):
            continue
        e = load(d, n) - H0
        de = e - ef
        ri, mi = stats(de, inside)
        ro, mo = stats(de, outside)
        print("%4d  %-9s  %.2e  %.2e  %.2e  %.2e" % (n, name, ri, mi, ro, mo))
    # 子格子そのもの(細格子基準。子を親格子へ平均してから)
    for r in (3, 5):
        d = "result_child_r%d" % r
        if not os.path.exists(os.path.join(d, "E%04d.txt" % n)):
            continue
        ec = child_to_parent(load(d, n) - H0, r)
        de = ec - ef[I0 - 1:I0 - 1 + NF, I0 - 1:I0 - 1 + NF]
        print("%4d  child_r%d   %.2e  %.2e  (子の足元内。親格子へ平均して比較)" % (n, r, np.sqrt(np.mean(de ** 2)), np.max(np.abs(de))))
print()
# 界面(子の足元の外周 1 セル)での入射振幅: 基準ランの η の最大(時間方向にも最大)
ring = inside.copy(); ring[I0:I0 - 2 + NF, I0:I0 - 2 + NF] = False
amp = max(np.max(np.abs(fine_to_parent(load("result_fine", n)) - H0)[ring]) for n in range(1, 11))
print("界面での入射振幅(基準ランの η の最大、足元外周): %.3f m  (初期振幅 a = %.2f m。出力は 1e-4 m 刻み)" % (amp, A))
print("反射率の目安(t = 6, 8, 10 s の子内部〔帯を除く〕の最大|Δη| / a, a = %.2f m):" % A)
for n in (6, 8, 10):
    ef = fine_to_parent(load("result_fine", n)) - H0
    for name, d in runs.items():
        if not os.path.exists(os.path.join(d, "E%04d.txt" % n)):
            continue
        e = load(d, n) - H0
        print("  t=%2d  %-9s  max|Δη|/a = %.4f   max|Δη|/入射振幅 = %.4f" % (n, name, np.max(np.abs((e - ef)[core])) / A, np.max(np.abs((e - ef)[core])) / amp))
