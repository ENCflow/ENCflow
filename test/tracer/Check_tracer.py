#!/usr/bin/env python3
# =====================================================================
# tracer: 1 次風上スカラー輸送の数値拡散の検定(reference 非依存)
#   構成 A(result, result_a10dt2, result_a20): 清水前線の幅から
#     等価拡散係数 D = σ²/(2t)(σ² は −dC/dx の分散)を求め、1 次風上
#     (前進オイラー)の修正方程式の値 D_th = u·dx·(1 − Cr)/2、Cr = u·dt/dx
#     と比べる(u は前線の移動速度から実測)。t ≥ 30 分で相対差 20 % 以内。
#   構成 B(result_b): 定常プルームの横断分散 σy²(x) の勾配から
#     Dy = (dσy²/dx)·u/2 を求め、ENC の斜めリンクの通過幅シェア
#     p_diag/2 = 0.293 による理論値 Dy_th = 0.293·u·dy と比べる(20 % 以内)。
# =====================================================================
import glob, os, sys
import numpy as np

G = 9.8
PDIAG = 2.0 / (2.0 + np.sqrt(2.0))      # ENC の斜め成分比(既定)
rc = 0

def times(rdir):
    return {int(l.split(",")[0]): float(l.split(",")[2])
            for l in open(os.path.join(rdir, "FILENUMBER.csv")) if not l.startswith("#")}

def front_stats(c, dx, c0):
    """横断平均した前線 f(s) = C/c0(s は流下距離。構成 A は南北水路なので行方向)から、
    前線密度 w = df/ds の平均位置と分散"""
    f = c.mean(axis=1) / c0
    w = np.diff(f)                       # f は上流 0 → 下流 1 へ増える
    w = np.clip(w, 0.0, None)
    x = (np.arange(len(w)) + 1.0) * dx   # エッジ位置
    if w.sum() <= 0:
        return np.nan, np.nan, 0.0
    xm = (w * x).sum() / w.sum()
    var = (w * (x - xm) ** 2).sum() / w.sum()
    return xm, var, w.sum()

print("--- 構成 A: 縦断の数値拡散(清水前線の広がり) ---")
print("| ケース | dx (m) | dt (s) | t (min) | 前線位置 x_f (m) | u = x_f/t (m/s) | Cr | D 実測 (m2/s) | D 理論 u·dx·(1−Cr)/2 | 比 |")
print("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
for rdir, dx, dt in (("result", 10.0, 1.0), ("result_a10dt2", 10.0, 2.0), ("result_a20", 20.0, 2.0)):
    if not os.path.isdir(rdir):
        print("missing", rdir); rc = 1; continue
    tk = times(rdir)
    for k in sorted(tk):
        t = tk[k]
        if k == 0 or k >= 9000 or t < 1790:
            continue
        c = np.loadtxt(os.path.join(rdir, "C%04d.txt" % k))
        xm, var, wsum = front_stats(c, dx, 100.0)
        if wsum < 0.9:                   # 前線が領域内に収まっていない
            continue
        u = xm / t
        cr = u * dt / dx
        d_num = var / (2.0 * t)
        d_th = u * dx * (1.0 - cr) / 2.0
        ratio = d_num / d_th
        ok = abs(ratio - 1.0) <= 0.20
        if not ok:
            rc = 1
        print("| %s | %g | %g | %.0f | %.0f | %.3f | %.2f | %.2f | %.2f | %.2f%s |"
              % (rdir, dx, dt, t / 60, xm, u, cr, d_num, d_th, ratio, "" if ok else " NG"))

print()
print("--- 構成 B: 横断の数値拡散(定常プルームの横断分散) ---")
rdir, dx, dy, u_nom = "result_b", 10.0, 10.0, 1.0
if not os.path.isdir(rdir):
    print("missing", rdir); rc = 1
else:
    tk = times(rdir)
    k = max(kk for kk in tk if kk < 9000)
    c = np.loadtxt(os.path.join(rdir, "C%04d.txt" % k))
    h = np.loadtxt(os.path.join(rdir, "H%04d.txt" % k))
    ny, nx = c.shape
    y = (np.arange(ny) + 0.5) * dy
    i0 = 50                              # 点源の列(1 スタート)
    xs, s2 = [], []
    for i in range(i0 + 20, i0 + 320):   # 源の 200〜3200 m 下流(壁の影響外)
        col = c[:, i - 1]
        if col.sum() <= 0:
            continue
        ym = (col * y).sum() / col.sum()
        var = (col * (y - ym) ** 2).sum() / col.sum()
        xs.append((i - i0) * dx); s2.append(var)
    xs, s2 = np.array(xs), np.array(s2)
    slope, icpt = np.polyfit(xs, s2, 1)
    # 実測流速: 流量 / (幅 × 平均水深)
    u = 610.0 / (ny * dy * h[:, i0 + 100].mean())
    d_y = slope * u / 2.0
    d_th = (PDIAG / 2.0) * u * dy
    ratio = d_y / d_th
    ok = abs(ratio - 1.0) <= 0.20
    if not ok:
        rc = 1
    print("| t (min) | u (m/s) | dσy²/dx (m) | Dy 実測 (m2/s) | Dy 理論 0.293·u·dy | 比 | σy at 3 km (m) |")
    print("|---:|---:|---:|---:|---:|---:|---:|")
    print("| %.0f | %.3f | %.2f | %.2f | %.2f | %.2f%s | %.0f |"
          % (tk[k] / 60, u, slope, d_y, d_th, ratio, "" if ok else " NG", np.sqrt(np.interp(3000.0, xs, s2))))
    print("(参考) 縦断の理論値 u·dx·(1−Cr)/2 = %.2f m2/s: 横断は縦断の %.2f 倍"
          % (u * dx * (1 - u * 1.0 / dx) / 2, d_th / (u * dx * (1 - u * 1.0 / dx) / 2)))

sys.exit(rc)
