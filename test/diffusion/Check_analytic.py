#!/usr/bin/env python3
# diffusion ベンチマークの解析解比較
#   プローブ CSV の u(t) を、定数 ν の拡散方程式 ∂u/∂t = ν ∂²u/∂y² の
#   ガウス形ジェットの解析解
#     u(r, t) = U0 σ/√(σ² + 2νt) exp(−r²/(2(σ² + 2νt)))    (r = |y − yc|)
#   と比較する。
#   使い方: Check_analytic.py <probesdir> <dy> [tol]
#     dy  : セル幅 (m)。プローブの行番号 iy から r = |(iy − 0.5) dy − yc| を作る
#     tol : 最大絶対誤差の許容値 (m/s)。既定 5e-4 = U0 の 1%
#   終了コード: 0 = PASS(全プローブで最大絶対誤差 < tol)、1 = FAIL
import sys, glob, math

U0, SIGMA2, NU, YC = 0.05, 100.0, 4.0, 50.5   # param*.txt / jet_gaussian と対で保守する

probesdir = sys.argv[1]
dy = float(sys.argv[2])
tol = float(sys.argv[3]) if len(sys.argv) > 3 else 5.0e-4

fails = 0
maxerr_all = 0.0
files = sorted(glob.glob(probesdir + "/probe*.csv"))
if not files:
    print("FAIL: no probe csv in " + probesdir)
    sys.exit(1)
for fn in files:
    iy = None
    rows = []
    for line in open(fn):
        if line.startswith("#"):
            if line.startswith("# iy"):
                iy = int(line.split(",")[1])
            continue
        c = line.split(",")
        if len(c) < 5:
            continue
        t = float(c[1]) * 60.0          # t(min) -> s
        rows.append((t, float(c[4])))   # u(m/s)
    r = abs((iy - 0.5) * dy - YC)
    maxerr = 0.0
    for t, unum in rows:
        s2 = SIGMA2 + 2.0 * NU * t
        uana = U0 * math.sqrt(SIGMA2 / s2) * math.exp(-r * r / (2.0 * s2))
        maxerr = max(maxerr, abs(unum - uana))
    ok = maxerr < tol
    if not ok:
        fails += 1
    maxerr_all = max(maxerr_all, maxerr)
    print("%s  r=%6.2f m  max|u_num - u_ana| = %.3e m/s  %s"
          % (fn, r, maxerr, "PASS" if ok else "FAIL"))

print("== diffusion benchmark (dy=%g m): max error %.3e m/s = %.2f%% of U0 (tol %.1e) : %s =="
      % (dy, maxerr_all, 100.0 * maxerr_all / U0, tol, "PASS" if fails == 0 else "FAIL"))
sys.exit(0 if fails == 0 else 1)
