#!/usr/bin/env python3
# swi(土壌雨量指数)検定
#   使い方: Check_swi.py <resultdir>
#
#   気象庁3段直列タンク(石原・小葉竹1979 の全国一律定数)を RK4
#   (dt=0.5 s)で高分解能積分した参照解と比較する:
#     (1) 最終値   : Swi9998 の全セルが参照解 SWI(tt) に相対 TOL 以内
#     (2) 期間最大 : Swi9999 が参照解のピークに相対 TOL 以内
#     (3) 発生時刻 : Swit9999(min)が参照解のピーク時刻 ±TOL_T 以内
#     (4) 一様性   : 一様降雨なので全セル同値(max = min)
#   降雨・時間の設定は param.txt と対で保守する。
import sys

# --- param.txt と対 ---
RAIN, TRAIN, TT = 30.0, 10800.0, 21600.0     # mm/h, 一定区間の終端 (s), 計算時間 (s)
TRAMP = 60.0                                  # 休止までの線形ランプ (s)(テーブルは線形補間)
NX, NY = 10, 8
TOL, TOL_T = 0.01, 2.0                        # 相対 1%, 時刻 ±2 min
# --- タンク定数(m_swi.f90 と対。全国一律の原式固定)---
L1, L2, L3, L4 = 15.0, 60.0, 15.0, 15.0       # mm
A1, A2, A3, A4 = 0.1, 0.15, 0.05, 0.01        # 1/hr
B1, B2, B3 = 0.12, 0.05, 0.01                 # 1/hr


def deriv(s1, s2, s3, r):
    # r: mm/hr。返り値は mm/hr
    q1 = A1 * max(s1 - L1, 0.0) + A2 * max(s1 - L2, 0.0)
    b1 = B1 * s1
    q2 = A3 * max(s2 - L3, 0.0)
    b2 = B2 * s2
    q3 = A4 * max(s3 - L4, 0.0)
    b3 = B3 * s3
    return (r - q1 - b1, b1 - q2 - b2, b2 - q3 - b3)


def rain(t):
    # param.txt のテーブル(線形補間)と同一: 一定 → 1 分ランプ → 0
    if t <= TRAIN:
        return RAIN
    if t >= TRAIN + TRAMP:
        return 0.0
    return RAIN * (1.0 - (t - TRAIN) / TRAMP)


def reference():
    # RK4, dt=0.5 s。ピークと最終値を返す
    dt = 0.5
    dth = dt / 3600.0
    s = (0.0, 0.0, 0.0)
    t = 0.0
    peak, tpeak = 0.0, 0.0
    n = int(round(TT / dt))
    for i in range(n):
        r = rain(t)
        r2 = rain(t + dt / 2)
        r3 = rain(t + dt)
        k1 = deriv(*s, r)
        k2 = deriv(*(x + dth / 2 * k for x, k in zip(s, k1)), r2)
        k3 = deriv(*(x + dth / 2 * k for x, k in zip(s, k2)), r2)
        k4 = deriv(*(x + dth * k for x, k in zip(s, k3)), r3)
        s = tuple(x + dth / 6 * (a + 2 * b + 2 * c + d)
                  for x, a, b, c, d in zip(s, k1, k2, k3, k4))
        t += dt
        swi = sum(s)
        if swi > peak:
            peak, tpeak = swi, t
    return sum(s), peak, tpeak / 60.0


def load(fn):
    return [x for line in open(fn) if line.split()
            for x in map(float, line.split())]


resultdir = sys.argv[1]
fin = load(resultdir + "/Swi9998.txt")
fmx = load(resultdir + "/Swi9999.txt")
fmt_ = load(resultdir + "/Swit9999.txt")
ref_fin, ref_peak, ref_tpk = reference()

ok1 = all(abs(x - ref_fin) / ref_fin < TOL for x in fin)
ok2 = all(abs(x - ref_peak) / ref_peak < TOL for x in fmx)
ok3 = all(abs(x - ref_tpk) <= TOL_T for x in fmt_)
ok4 = max(fin) == min(fin) and max(fmx) == min(fmx)
print("(1) 最終値   : SWI(tt) = %.3f mm vs 参照 %.3f mm (tol %.0f%%) : %s"
      % (fin[0], ref_fin, 100 * TOL, "PASS" if ok1 else "FAIL"))
print("(2) 期間最大 : Swi9999 = %.3f mm vs 参照 %.3f mm : %s"
      % (fmx[0], ref_peak, "PASS" if ok2 else "FAIL"))
print("(3) 発生時刻 : Swit9999 = %.1f min vs 参照 %.1f min (tol ±%.0f min) : %s"
      % (fmt_[0], ref_tpk, TOL_T, "PASS" if ok3 else "FAIL"))
print("(4) 一様性   : max-min = %.3e : %s"
      % (max(fin) - min(fin), "PASS" if ok4 else "FAIL"))

ok = ok1 and ok2 and ok3 and ok4
print("== swi 検定: %s ==" % ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
