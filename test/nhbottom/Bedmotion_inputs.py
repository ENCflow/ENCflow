#!/usr/bin/env python3
# nhbottom 構成 3: 構成 1 と同じ区間隆起を fn_bedmotion のスナップショット表で与える入力を作る
#   bm/bmlist.txt(時刻 ファイル名。ファイル名は dir_data 相対 = bm/disp_NNNN.txt)と bm/disp_NNNN.txt(累積変位 d(x) の全域行列。z と同じ行順)。
#   隆起中(0 < t ≤ tc)は毎ステップ(dt = 0.0125 s)のスナップショット = uplift ドライバと同じ時刻歴。
#   最後のスナップショット以後は末尾の値が保持される。
#   python3 Bedmotion_inputs.py ls : 海底地滑りの格子(120 × 40、Δx = 5 m)で湖底 |x−450|<30, |y−100|<30 を
#   t = 5〜7 s に 0.3 m 持ち上げる bm_ls/(param_ls_bb.txt = bedslide との同居の検定)
import os, math, sys
if len(sys.argv) > 1 and sys.argv[1] == "ls":
    os.makedirs("bm_ls", exist_ok=True)
    NX, NY, DX = 120, 40, 5.0
    with open("bm_ls/bmlist.txt", "w") as lst:
        for k in range(0, 41):
            tt = 5.0 + 0.05 * k
            rr = 0.5 * (1 - math.cos(math.pi * min(0.05 * k, 2.0) / 2.0))
            fn = "bm_ls/disp_%04d.txt" % k
            with open(fn, "w") as f:
                for j in range(1, NY + 1):
                    y = (j - 0.5) * DX
                    f.write(" ".join("%.6f" % (0.3 * rr if abs((i - 0.5) * DX - 450) < 30 and abs(y - 100) < 30 else 0.0)
                                     for i in range(1, NX + 1)) + "\n")
            lst.write("%.3f %s\n" % (tt, fn))
    print("wrote bm_ls/bmlist.txt and 41 snapshots")
    sys.exit(0)
NX, NY, DX = 800, 32, 1.25
XC, BH, ZETA0, TC, DT = 500.0, 20.0, 0.2, 1.0, 0.0125
os.makedirs("bm", exist_ok=True)
nstep = int(round(TC / DT))
with open("bm/bmlist.txt", "w") as lst:
    lst.write("# time(s)  file   (uplift of test/nhbottom config 1: half-sine ramp, every step)\n")
    for k in range(nstep + 1):
        t = k * DT
        r = 0.5 * (1.0 - math.cos(math.pi * min(t, TC) / TC)) if t < TC else 1.0
        row = " ".join("%.10f" % (ZETA0 * r if abs((i - 0.5) * DX - XC) < BH else 0.0) for i in range(1, NX + 1))
        fn = "disp_%04d.txt" % k
        with open("bm/" + fn, "w") as f:
            for j in range(NY):
                f.write(row + "\n")
        lst.write("%.6f  bm/%s\n" % (t, fn))
print("wrote bm/bmlist.txt and %d snapshots" % (nstep + 1))
