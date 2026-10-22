#!/usr/bin/env python3
"""test/splashsat の解析検証(事前に ./Run.sh を実行しておく)。
放物線の谷(κ = 0.1 一定)で、飽和した増幅 Φ_A = 1 + ca κ/(1 + κ/κ_s) = 1.5 を掛けた
解析形 Δz = P kr Φ_A T_geo = 0.9 mm に、Sd0000 − Sd9998 の内部行が一致するかを照合する。
飽和なし(Φ_A = 2.0、1.2 mm)とは区別できる。"""
import sys
import numpy as np
P, KR, CA, KAPPA, KSAT, TGEO = 30.0 / 3.6e6, 0.004, 10.0, 0.1, 0.1, 18000.0
phi = 1.0 + CA * KAPPA / (1.0 + KAPPA / KSAT)
dz_th = P * KR * phi * TGEO
sd0 = np.loadtxt("result/Sd0000.txt"); sd1 = np.loadtxt("result/Sd9998.txt")
dz = sd0 - sd1
inner = dz[1:-1, :]                      # 境界行(鏡像で κ が半分)を除く
err = np.abs(inner - dz_th).max()
print("Φ_A = %.3f, 理論 Δz = %.4f mm, 計算 Δz(内部行): min %.4f / max %.4f mm, 境界行: %.4f mm"
      % (phi, dz_th * 1e3, inner.min() * 1e3, inner.max() * 1e3, dz[0].mean() * 1e3))
print("飽和なしなら Δz = %.4f mm" % (P * KR * (1 + CA * KAPPA) * TGEO * 1e3))
ok = err <= 1.0e-6
print("max |error| = %.3e m (tol 1e-6): %s" % (err, "PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
