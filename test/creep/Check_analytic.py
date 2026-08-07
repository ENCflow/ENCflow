#!/usr/bin/env python3
# creep ベンチマークの解析解比較
#   プローブ CSV の z(t) を、線形拡散のガウス丘解析解
#     z(r,t) = A sigma^2/(sigma^2 + 2 D tau) exp(-r^2/(2(sigma^2 + 2 D tau)))
#   (tau = 水理時刻 t × morfac = 地形時間)と比較する。
#   使い方: Check_analytic.py <probesdir> <morfac> [tol]
#   終了コード: 0 = PASS(最大絶対誤差 < tol)、1 = FAIL
import sys, glob, math

A, SIGMA2, D = 1.0, 100.0, 1.0   # param.txt / gaussian_hill と対で保守する
IC, JC, DX, DY = 51, 51, 1.0, 1.0

probesdir = sys.argv[1]
morfac = float(sys.argv[2])
tol = float(sys.argv[3]) if len(sys.argv) > 3 else 5.0e-3

fails = 0
maxerr_all = 0.0
files = sorted(glob.glob(probesdir + "/probe*.csv"))
if not files:
    print("FAIL: no probe csv in " + probesdir)
    sys.exit(1)
for fn in files:
    ix = iy = None
    rows = []
    for line in open(fn):
        if line.startswith("#"):
            if line.startswith("# ix"):
                ix = int(line.split(",")[1])
            elif line.startswith("# iy"):
                iy = int(line.split(",")[1])
            continue
        c = line.split(",")
        if len(c) < 3:
            continue
        t = float(c[1]) * 60.0          # t(min) -> s
        rows.append((t, float(c[2])))   # z(m)
    r2 = ((ix - IC) * DX) ** 2 + ((iy - JC) * DY) ** 2
    maxerr = 0.0
    for t, znum in rows:
        s2 = SIGMA2 + 2.0 * D * t * morfac
        zana = A * SIGMA2 / s2 * math.exp(-r2 / (2.0 * s2))
        maxerr = max(maxerr, abs(znum - zana))
    ok = maxerr < tol
    if not ok:
        fails += 1
    maxerr_all = max(maxerr_all, maxerr)
    print("%s  r=%6.2f m  max|z_num - z_ana| = %.3e m  %s"
          % (fn, math.sqrt(r2), maxerr, "PASS" if ok else "FAIL"))

print("== creep benchmark (morfac=%g): max error %.3e m (tol %.1e) : %s =="
      % (morfac, maxerr_all, tol, "PASS" if fails == 0 else "FAIL"))
sys.exit(0 if fails == 0 else 1)
