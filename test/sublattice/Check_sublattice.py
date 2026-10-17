#!/usr/bin/env python3
# sublattice: 斜め副格子モードの減衰率(初期パターンへの射影振幅の時間変化)
#   使い方: Check_sublattice.py <resdir> [alternating|smooth] [--require-decay T]
#   resdir の u????.txt / v????.txt(FILENUMBER.csv で時刻)を読み、初期の渦
#   パターン(user_initial gyre_*: ψ = A sin(πx/L) sin(πy/L)、V0 = 0.2 m/s)への
#   射影振幅
#     a_alt(t) = Σ s·(u·up + v·vp) / Σ(up² + vp²)   s = (−1)^(i+j)(副格子モード)
#     a_sm(t)  = Σ   (u·up + v·vp) / Σ(up² + vp²)                (滑らかな渦)
#   と運動エネルギー比 KE(t)/KE(0) を表にし、e-folding 時間を最小二乗で推定する。
#   判定: smooth は a_sm(tt) > 0.5(物理的な渦が保たれる)で PASS。
#         alternating は --require-decay T を与えたとき a_alt の e-folding 時間
#         < T 秒で PASS(与えなければ計測値の表示のみ = 現状の記録)。
import sys, os, math
import numpy as np

V0 = 0.2   # user_initial gyre_* と対で保守する

def pattern(nx, ny, dx, dy):
    lx, ly = nx * dx, ny * dy
    aa = V0 * lx / math.pi
    x = (np.arange(nx) + 0.5) * dx
    y = (np.arange(ny) + 0.5) * dy
    X, Y = np.meshgrid(x, y)
    up = aa * (math.pi / ly) * np.sin(math.pi * X / lx) * np.cos(math.pi * Y / ly)
    vp = -aa * (math.pi / lx) * np.cos(math.pi * X / lx) * np.sin(math.pi * Y / ly)
    I, J = np.meshgrid(np.arange(1, nx + 1), np.arange(1, ny + 1))
    s = np.where((I + J) % 2 == 0, 1.0, -1.0)
    return up, vp, s

def main():
    resdir = sys.argv[1]
    kind = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else "alternating"
    req = None
    if "--require-decay" in sys.argv:
        req = float(sys.argv[sys.argv.index("--require-decay") + 1])
    times = {}
    for line in open(os.path.join(resdir, "FILENUMBER.csv")):
        t = line.split(",")
        if len(t) < 3 or not t[0].strip().isdigit():
            continue
        if int(t[0]) >= 9998:   # 9998/9999 = 最終・期間最大(時刻が重複する)
            continue
        times[int(t[0])] = float(t[2])
    dx = dy = 10.0   # param.txt と対
    rows = []
    for k in sorted(times):
        fu = os.path.join(resdir, "u%04d.txt" % k)
        fv = os.path.join(resdir, "v%04d.txt" % k)
        if not (os.path.exists(fu) and os.path.exists(fv)):
            continue
        u = np.loadtxt(fu); v = np.loadtxt(fv)
        if not rows:
            up, vp, s = pattern(u.shape[1], u.shape[0], dx, dy)
            norm = (up**2 + vp**2).sum()
        a_alt = (s * (u * up + v * vp)).sum() / norm
        a_sm = (u * up + v * vp).sum() / norm
        ke = (u**2 + v**2).sum()
        rows.append((times[k], a_alt, a_sm, ke))
    ke0 = rows[0][3]
    print("Check_sublattice %s: %s" % (kind, resdir))
    print("  %8s %10s %10s %10s" % ("t(s)", "a_alt", "a_smooth", "KE/KE0"))
    for t, a1, a2, ke in rows:
        print("  %8.0f %10.4f %10.4f %10.4f" % (t, a1, a2, ke / ke0))
    col = 2 if kind == "smooth" else 1
    amp = np.array([r[col] for r in rows]); tt = np.array([r[0] for r in rows])
    # e-folding 時間: 振幅が初期の 5 % を超えるフレームの log 線形回帰。
    # 1 フレーム目で 5 % を割る速い減衰は最初の区間から τ = −Δt/ln(a1/a0)
    ok = amp > 0.05 * amp[0]
    tau = None
    if ok.sum() >= 3:
        slope = np.polyfit(tt[ok], np.log(amp[ok]), 1)[0]
        if slope < 0:
            tau = -1.0 / slope
    elif len(amp) >= 2 and amp[0] > 0 and amp[1] > 0 and amp[1] < amp[0]:
        tau = -(tt[1] - tt[0]) / math.log(amp[1] / amp[0])
    rc = 0
    if kind == "smooth":
        print("  smooth gyre retained at t = %.0f s: a_sm = %.3f of initial (require > 0.5) -> %s"
              % (tt[-1], amp[-1] / amp[0], "OK" if amp[-1] / amp[0] > 0.5 else "NG"))
        if amp[-1] / amp[0] <= 0.5:
            rc = 1
    else:
        print("  alternating mode: amplitude at t = %.0f s is %.3f of initial; e-folding time %s"
              % (tt[-1], amp[-1] / amp[0], ("%.0f s" % tau) if tau else "> run length (no decay)"))
        if kind == "mixed":
            sm = np.array([r[2] for r in rows])
            print("  background smooth gyre retained: a_sm = %.3f of initial (require > 0.5) -> %s"
                  % (sm[-1] / sm[0], "OK" if sm[-1] / sm[0] > 0.5 else "NG"))
            if sm[-1] / sm[0] <= 0.5:
                rc = 1
        if req is not None:
            good = tau is not None and tau < req
            print("  require e-folding < %.0f s -> %s" % (req, "OK" if good else "NG"))
            if not good:
                rc = 1
    return rc

sys.exit(main())
