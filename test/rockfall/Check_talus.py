#!/usr/bin/env python3
# 崖錐の溶食の検定(developer.md §86.7)
#   result_talus0(崖錐を作った第 0 段の終端)→ result_talus1(一様な雨で W だけ溶かした第 1 段)で
#     (1) ht1 = max(ht0 − W, 0)            崖錐が先に溶ける
#     (2) z1 = z0 − (1 − f_res) W           地表は崖錐の有無によらず同じだけ下がる
#     (3) sd1 = sd0 − (1 − f_res) min(ht0, W) + f_res max(W − ht0, 0)   残渣の帳尻
#     (4) 崖錐が尽きたセル(ht0 < W)と残るセル(ht0 > W)が両方ある(検定が両分岐を踏む)
#   使い方: Check_talus.py <resdir0> <resdir1> W fres [tol]
import sys
import numpy as np
r0, r1 = sys.argv[1], sys.argv[2]
W, FRES = float(sys.argv[3]), float(sys.argv[4])
TOL = float(sys.argv[5]) if len(sys.argv) > 5 else 3.0e-4     # 出力は印字桁 1e-4 m
z0, sd0, ht0 = (np.loadtxt("%s/%s9998.txt" % (r0, v)) for v in ("Z", "Sd", "Ht"))
z1, sd1, ht1 = (np.loadtxt("%s/%s9998.txt" % (r1, v)) for v in ("Z", "Sd", "Ht"))
e1 = np.abs(ht1 - np.maximum(ht0 - W, 0.0)).max()
e2 = np.abs((z1 - z0) + (1.0 - FRES) * W).max()
e3 = np.abs(sd1 - (sd0 - (1.0 - FRES) * np.minimum(ht0, W) + FRES * np.maximum(W - ht0, 0.0))).max()
nex, nrm = int(((ht0 > 0) & (ht0 < W)).sum()), int((ht0 > W).sum())
ok1, ok2, ok3, ok4 = e1 < TOL, e2 < TOL, e3 < TOL, (nex > 0 and nrm > 0)
print("(1) 崖錐が先に溶ける: max|ht1 - max(ht0 - W, 0)| = %.2e m (tol %.0e) : %s" % (e1, TOL, "PASS" if ok1 else "FAIL"))
print("(2) 地表の低下      : max|(z1 - z0) + (1 - f_res) W| = %.2e m : %s" % (e2, "PASS" if ok2 else "FAIL"))
print("(3) 土層の帳尻      : max|sd1 - sd1(解析)| = %.2e m : %s" % (e3, "PASS" if ok3 else "FAIL"))
print("(4) 両分岐          : 崖錐が尽きたセル %d、残るセル %d : %s" % (nex, nrm, "PASS" if ok4 else "FAIL"))
ok = ok1 and ok2 and ok3 and ok4
print("== talus dissolution 検定: %s ==" % ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
