#!/usr/bin/env python3
"""nhsolitary: 孤立波の伝播を解析する(docs/nonhydrostatic_plan.md §11 Phase 5 Test 3)

  使い方: ./Solitary.py [result_dir ...]   既定は result(NH), result_h(静水圧), result_a(活性集合)
  水深分布 H00NN.txt(dt_file ごと)の中央行から、波頂の位置 x_c(t)・高さ a(t) を追い、
  伝播速度(線形回帰)、理論値 c = √(g(H+a0))、波形の保存(最終時刻の波形を初期波形を
  x_c だけずらしたものと比較した RMS 誤差 / a0)を表にする。計算本体の外(方針 10)。
"""
import sys, os, math, glob
import numpy as np
G = 9.8
def load(resdir):
    files = sorted(glob.glob(os.path.join(resdir, "H[0-9][0-9][0-9][0-9].txt")))
    files = [f for f in files if not f.endswith(("H9998.txt", "H9999.txt"))]
    times = {}
    for l in open(os.path.join(resdir, "FILENUMBER.csv")):
        if l.startswith("#"): continue
        c = l.split(","); times[int(c[0])] = float(c[2])
    out = []
    for f in files:
        k = int(os.path.basename(f)[1:5])
        a = np.loadtxt(f)
        out.append((times.get(k, float("nan")), a[a.shape[0] // 2, :]))
    return out
def analyze(resdir, dx, H):
    prof = load(resdir)
    t0, h0 = prof[0]
    x = (np.arange(len(h0)) + 0.5) * dx
    a0 = h0.max() - H
    ic = int(np.argmax(h0)); x0 = x[ic]
    rows = []
    for t, h in prof:
        ic = int(np.argmax(h))
        # 放物線補間で波頂位置を細かく
        if 0 < ic < len(h) - 1:
            y0, y1, y2 = h[ic - 1], h[ic], h[ic + 1]
            d = 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2) if (y0 - 2 * y1 + y2) != 0 else 0.0
        else:
            d = 0.0
        rows.append((t, x[ic] + d * dx, h.max() - H))
    rows = np.array(rows)
    sel = rows[:, 0] > 0
    c_fit = np.polyfit(rows[sel, 0], rows[sel, 1], 1)[0]
    c_th = math.sqrt(G * (H + a0))
    # 波形の保存: 最終時刻の波形と、初期波形を波頂移動量だけずらしたもの
    tN, hN = prof[-1]
    shift = rows[-1, 1] - x0
    h0s = np.interp(x - shift, x, h0, left=H, right=H)
    win = np.abs(x - rows[-1, 1]) < 15.0
    rms = math.sqrt(np.mean((hN[win] - h0s[win]) ** 2)) / a0
    # 後続波(波頂より後ろ 15〜60 m)の最大振幅
    back = (x < rows[-1, 1] - 15.0) & (x > rows[-1, 1] - 60.0)
    trail = (np.abs(hN[back] - H).max() / a0) if back.any() else float("nan")
    return dict(a0=a0, c_fit=c_fit, c_th=c_th, aN=rows[-1, 2], rms=rms, trail=trail, rows=rows)
if __name__ == "__main__":
    dirs = sys.argv[1:] or ["result", "result_h", "result_a"]
    dx = 0.25; H = 1.0
    print(f"{'case':10s} {'a0/H':>6s} {'c_fit':>7s} {'c_th':>7s} {'c_fit/c_th':>10s} {'aN/a0':>7s} {'RMS/a0':>7s} {'trail/a0':>8s}")
    for d in dirs:
        if not os.path.isdir(d): continue
        r = analyze(d, dx, H)
        print(f"{d:10s} {r['a0']/H:6.3f} {r['c_fit']:7.4f} {r['c_th']:7.4f} {r['c_fit']/r['c_th']:10.4f} "
              f"{r['aN']/r['a0']:7.4f} {r['rms']:7.4f} {r['trail']:8.4f}")
        for t, xc, a in r['rows'][::3]:
            print(f"    t={t:5.1f}  x_c={xc:7.2f}  a={a:.4f}")
