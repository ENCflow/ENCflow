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
#   MUSCL(f_scalar_scheme = 3。result_m*): 同じ量を求め、1 次風上に対する
#     比が縦断 0.5 以下・横断 0.2 以下であること、濃度場に負値も初期濃度を
#     超える値も出ないこと(正値性・単調性)を検定する。
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

def plume_stats(rdir, dx=10.0, dy=10.0, i0=50):
    tk = times(rdir)
    k = max(kk for kk in tk if kk < 9000)
    c = np.loadtxt(os.path.join(rdir, "C%04d.txt" % k))
    h = np.loadtxt(os.path.join(rdir, "H%04d.txt" % k))
    ny, nx = c.shape
    y = (np.arange(ny) + 0.5) * dy
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
    u = 610.0 / (ny * dy * h[:, i0 + 100].mean())   # 実測流速: 流量 / (幅 × 平均水深)
    return tk[k], u, slope, slope * u / 2.0, np.sqrt(np.interp(3000.0, xs, s2)), c

rdir, dx, dy = "result_b", 10.0, 10.0
d_y1 = None
if not os.path.isdir(rdir):
    print("missing", rdir); rc = 1
else:
    t, u, slope, d_y, sig3, c = plume_stats(rdir)
    d_th = (PDIAG / 2.0) * u * dy
    ratio = d_y / d_th
    ok = abs(ratio - 1.0) <= 0.20
    if not ok:
        rc = 1
    d_y1 = d_y
    print("| t (min) | u (m/s) | dσy²/dx (m) | Dy 実測 (m2/s) | Dy 理論 0.293·u·dy | 比 | σy at 3 km (m) |")
    print("|---:|---:|---:|---:|---:|---:|---:|")
    print("| %.0f | %.3f | %.2f | %.2f | %.2f | %.2f%s | %.0f |"
          % (t / 60, u, slope, d_y, d_th, ratio, "" if ok else " NG", sig3))
    print("(参考) 縦断の理論値 u·dx·(1−Cr)/2 = %.2f m2/s: 横断は縦断の %.2f 倍"
          % (u * dx * (1 - u * 1.0 / dx) / 2, d_th / (u * dx * (1 - u * 1.0 / dx) / 2)))

print()
print("--- MUSCL(f_scalar_scheme = 3): 1 次風上に対する数値拡散の比と正値性 ---")
print("| ケース | t (min) | 1 次 D (m2/s) | MUSCL D | 比 | MUSCL C 最小 | C 最大 |")
print("|---|---:|---:|---:|---:|---:|---:|")
for base, mdir, dx, dt in (("result", "result_m", 10.0, 1.0), ("result_a10dt2", "result_m_a10dt2", 10.0, 2.0),
                           ("result_a20", "result_m_a20", 20.0, 2.0)):
    if not os.path.isdir(mdir):
        print("missing", mdir); rc = 1; continue
    tk = times(mdir)
    cmin, cmax = np.inf, -np.inf
    for k in sorted(tk):
        t = tk[k]
        if k == 0 or k >= 9000:
            continue
        cm = np.loadtxt(os.path.join(mdir, "C%04d.txt" % k))
        cmin = min(cmin, cm.min()); cmax = max(cmax, cm.max())
        if t < 1790 or k % 3 != 0:
            continue
        c1 = np.loadtxt(os.path.join(base, "C%04d.txt" % k))
        x1, v1, _ = front_stats(c1, dx, 100.0)
        xm, vm, _ = front_stats(cm, dx, 100.0)
        ratio = vm / v1
        ok = ratio <= 0.5
        if not ok:
            rc = 1
        print("| %s | %.0f | %.2f | %.2f | %.2f%s | %.3e | %.4f |"
              % (mdir, t / 60, v1 / (2 * t), vm / (2 * t), ratio, "" if ok else " NG", cmin, cmax))
    if cmin < 0.0 or cmax > 100.0 * (1.0 + 1.0e-9):
        print("  NG: concentration outside [0, 100] in", mdir); rc = 1
if os.path.isdir("result_m_b") and d_y1 is not None:
    t, u, slope, d_y, sig3, c = plume_stats("result_m_b")
    ratio = d_y / d_y1
    ok = ratio <= 0.2 and c.min() >= 0.0
    if not ok:
        rc = 1
    print("| result_m_b(横断) | %.0f | %.2f | %.2f | %.2f%s | %.3e | σy at 3 km %.0f m |"
          % (t / 60, d_y1, d_y, ratio, "" if ok else " NG", c.min(), sig3))
else:
    print("missing result_m_b"); rc = 1

sys.exit(rc)
