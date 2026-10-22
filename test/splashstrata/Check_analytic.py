#!/usr/bin/env python3
"""test/splashstrata の解析検証(事前に ./Run.sh を実行しておく)。
水平層理の倍率 f(z) を掛けた解析形 Δz = f(z) P (kr + kt S) T_geo に対し、
出力 Sd0000 − Sd9998(= 侵食深)の列平均を列クラス別に照合する。
"""
import sys
import numpy as np

P = 30.0 / 3.6e6
KR, KT, TGEO = 0.004, 0.02, 18000.0
sd0 = np.loadtxt("result/Sd0000.txt")
sd1 = np.loadtxt("result/Sd9998.txt")
dz = (sd0 - sd1).mean(axis=0)          # 列平均(y 方向に一様)
nx = dz.size
x = (np.arange(nx) + 0.5) * 1.0
z = np.where(x < 30.0, 0.4 * (30.0 - x), 0.0)
fac = np.where(z >= 10.0, 0.0, np.where(z >= 6.0, 0.5, 1.0))
S = np.where(x < 29.0, 0.4, np.where(x < 30.0, 0.2, 0.0))   # 最急降下: 遷緩点の列は面の勾配 0.2
dz_th = fac * P * (KR + KT * S) * TGEO
err = np.abs(dz - dz_th)
tol = 1.0e-6                              # 理論値は出力の印字桁 1e-4 m の整数倍なので丸めなしで一致する
print("列クラス | x (m) | 倍率 | 理論 Δz (mm) | 計算 Δz (mm) | 最大誤差 (mm)")
for name, sel in (("硬層(倍率 0)", x <= 4.5), ("倍率 0.5 の層", (x >= 5.5) & (x <= 14.5)),
                  ("倍率 1 の斜面", (x >= 15.5) & (x <= 28.5)), ("遷緩点の列", (x > 28.5) & (x < 30.0)),
                  ("平坦部", x >= 30.0)):
    print("%s | %g-%g | %g | %.4f | %.4f | %.2e" % (name, x[sel].min(), x[sel].max(), fac[sel][0],
          dz_th[sel][0] * 1e3, dz[sel].mean() * 1e3, err[sel].max() * 1e3))
ok = err.max() <= tol
print("max |error| = %.3e m (tol %.1e): %s" % (err.max(), tol, "PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
