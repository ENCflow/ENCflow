#!/usr/bin/env python3
"""test/steepwave の検定(水面の勾配の項の可変の重力 g′、f_gravity_correction = 3。developer.md §100)。

  (1) lake: 静止した湖が保たれる(2・3)。流速の最大と水位の変化が 0(TOL_LAKE 以下)。
  (2) wave: 急な湖底を渡る長波の山の到達時刻。プローブ 1(深さ 40 m の平らな所)からの時間を、
      3 は補正なし(0。水面がほぼ水平な深い水では厳密)と TOL_WAVE_REF 以内、線形の長波の
      走時 ∫dx/√(gh) と TOL_WAVE_ANA 以内で合う(案 D)。2 は斜面の上で g_e = g cos²θ になって
      遅れる(表に出すだけ。斜面を越えた所で数 % 以上)。
  (3) bump: 摩擦のない斜面の一様な層の上の山が上下に分かれる間隔の広がる速さを、薄層の式の
      2√(g cosθ h_n)(斜面に沿う座標)と比べる。3 は TOL_BUMP 以内(案 E)。2 は 1/cos θ 倍、
      0 は 1/cos²θ 倍に近い(表に出すだけ)。山の高さは層厚の 1 %(分かれた山は 0.5 %)で、
      有限振幅による波速の上乗せ(約 1.5 a/h)は 1 % 未満。

  python3 Check_steepwave.py        判定(失敗があれば終了コード 1)
  python3 Check_steepwave.py table  判定と表
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_init as mi   # noqa: E402

G = mi.G
TOL_LAKE = 1e-12
TOL_WAVE_REF, TOL_WAVE_ANA = 0.003, 0.02
TOL_BUMP = 0.02


def read_txt(path):
    return np.loadtxt(path)


# ---------------- (1) lake ----------------
def check_lake(rows):
    ok = True
    for gc in mi.LAKE_GCS:
        r = f"result_{mi.case_name('lake', gc)}"
        h0, h1 = read_txt(f"{r}/H0000.txt"), read_txt(f"{r}/H9998.txt")
        u, v = read_txt(f"{r}/u9998.txt"), read_txt(f"{r}/v9998.txt")
        z = read_txt(f"{r}/Z0000.txt")
        wet = h1 > 0.0
        de = float(np.abs((h1 + z)[wet]).max())
        dh = float(np.abs(h1 - h0).max())
        vm = float(max(np.abs(u).max(), np.abs(v).max()))
        rows.append(f"lake g{gc}: wet cells {int(wet.sum())}, max|η| {de:.1e} m, max|Δh| {dh:.1e} m, max|u|,|v| {vm:.1e} m/s")
        if max(de, dh, vm) > TOL_LAKE:
            print(f"FAIL (1) lake g{gc}: 静止が保たれない(max|η| {de:.2e}, max|Δh| {dh:.2e}, max|u|,|v| {vm:.2e})")
            ok = False
    return ok


# ---------------- (2) wave ----------------
def wave_travel(xa, xb, n=20001):
    xs = np.linspace(xa, xb, n)
    f = 1.0 / np.sqrt(G * -np.array([mi.wave_bed(x) for x in xs]))
    return float(np.sum((f[1:] + f[:-1]) * np.diff(xs)) / 2)


def wave_peak(rdir, k, t_guess):
    """プローブ k の水位の山の時刻 (s)。t_guess ± 3 s の窓の最大を放物線で補間。"""
    d = np.loadtxt(f"{rdir}/probes/probe{k:04d}.csv", delimiter=",", comments="#")
    t = d[:, 1] * 60.0
    e = d[:, 2] + d[:, 3]
    idx = np.where((t >= t_guess - 3.0) & (t <= t_guess + 3.0))[0]
    i = idx[np.argmax(e[idx])]
    y0, y1, y2 = e[i - 1], e[i], e[i + 1]
    den = y0 - 2.0 * y1 + y2
    return t[i] + (0.5 * (y0 - y2) / den * (t[i + 1] - t[i]) if den != 0.0 else 0.0)


def check_wave(rows):
    ok = True
    xs = mi.WAVE_PROBES
    t0 = wave_travel(mi.WAVE_XC, xs[0])
    ana = [wave_travel(xs[0], x) for x in xs]
    dt = {}
    for gc in mi.WAVE_GCS:
        r = f"result_{mi.case_name('wave', gc)}"
        tp = [wave_peak(r, k + 1, t0 + a) for k, a in enumerate(ana)]
        dt[gc] = [t - tp[0] for t in tp]
    rows.append("wave: probe x (m)      " + "  ".join(f"{x:7.0f}" for x in xs[1:]))
    rows.append("      depth (m)        " + "  ".join(f"{-mi.wave_bed(x):7.1f}" for x in xs[1:]))
    rows.append("      ∫dx/√(gh) (s)    " + "  ".join(f"{a:7.3f}" for a in ana[1:]))
    for gc in mi.WAVE_GCS:
        rows.append(f"      g{gc} time from P1 " + "  ".join(f"{d:7.3f}" for d in dt[gc][1:])
                    + "  | / analytic " + " ".join(f"{d / a:.4f}" for d, a in zip(dt[gc][1:], ana[1:])))
    for k in range(1, len(xs)):
        e_ref = abs(dt[3][k] / dt[0][k] - 1.0)
        e_ana = abs(dt[3][k] / ana[k] - 1.0)
        if e_ref > TOL_WAVE_REF:
            print(f"FAIL (2) wave x = {xs[k]:g}: g3 の走時 {dt[3][k]:.3f} s が補正なし {dt[0][k]:.3f} s と {e_ref:.4f} ずれる")
            ok = False
        if e_ana > TOL_WAVE_ANA:
            print(f"FAIL (2) wave x = {xs[k]:g}: g3 の走時 {dt[3][k]:.3f} s が解析 {ana[k]:.3f} s と {e_ana:.4f} ずれる")
            ok = False
    return ok


# ---------------- (3) bump ----------------
def bump_peaks(hn, s):
    """層厚からの増分の 2 つの山の位置(斜面に沿う距離。放物線で補間)。"""
    d = hn - mi.BUMP_HN
    idx = [i for i in range(1, len(d) - 1) if d[i] > d[i - 1] and d[i] >= d[i + 1] and d[i] > 0.1 * mi.BUMP_A]
    idx = sorted(sorted(idx, key=lambda i: -d[i])[:2])
    out = []
    for i in idx:
        y0, y1, y2 = d[i - 1], d[i], d[i + 1]
        den = y0 - 2.0 * y1 + y2
        out.append(s[i] + (0.5 * (y0 - y2) / den * (s[1] - s[0]) if den != 0.0 else 0.0))
    return out


def check_bump(rows):
    ok = True
    th = math.radians(mi.BUMP_THETA)
    c = math.cos(th)
    c0 = math.sqrt(G * c * mi.BUMP_HN)
    rows.append(f"bump: thin-layer separation speed 2√(g cosθ h_n) = {2 * c0:.4f} m/s "
                f"(θ = {mi.BUMP_THETA:g}°; 1/cosθ = {1 / c:.4f}, 1/cos²θ = {1 / c ** 2:.4f})")
    for gc in mi.BUMP_GCS:
        r = f"result_{mi.case_name('bump', gc)}"
        sep = []
        for k in (1, 2):                                      # t = BUMP_OUT, 2 BUMP_OUT
            h = read_txt(f"{r}/H{k:04d}.txt")[mi.BUMP_NY // 2]
            x = (np.arange(h.size) + 0.5) * mi.BUMP_DX
            pk = bump_peaks(h * c, (x - mi.BUMP_X0) / c)
            if len(pk) != 2:
                print(f"FAIL (3) bump g{gc}: t = {k * mi.BUMP_OUT:g} s で山が 2 つに分かれていない")
                return False
            sep.append(pk[1] - pk[0])
        speed = (sep[1] - sep[0]) / mi.BUMP_OUT
        ratio = speed / (2 * c0)
        rows.append(f"      g{gc}: separation {sep[0]:.3f} m → {sep[1]:.3f} m, speed {speed:.4f} m/s, ratio {ratio:.4f}")
        if gc == 3 and abs(ratio - 1.0) > TOL_BUMP:
            print(f"FAIL (3) bump g3: 山の間隔の広がる速さが薄層の式の {ratio:.4f} 倍(許容 ±{TOL_BUMP})")
            ok = False
    return ok


def main():
    show = len(sys.argv) > 1 and sys.argv[1] == "table"
    rows = []
    ok = check_lake(rows)
    ok = check_wave(rows) and ok
    ok = check_bump(rows) and ok
    if show or not ok:
        print("\n".join(rows))
    print("=== steepwave verification " + ("PASS" if ok else "FAIL") + " ===")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
