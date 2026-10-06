#!/usr/bin/env python3
"""test/swi の図を figs/swi.png に描く(事前に ./Run.sh を実行しておく)。
気象庁 3 段直列タンクの参照解(RK4、dt = 0.5 s)の SWI(t) と、ENCflow の最終値 Swi9998・期間最大 Swi9999・
発生時刻 Swit9999(全セル同値)。参照解の計算は Check_swi.py の定数・関数と同じ。
"""
import glob, os, struct
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
matplotlib.rcParams["font.family"] = ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs("figs", exist_ok=True)


def read_rec(f):
    n = struct.unpack("<i", f.read(4))[0]; p = f.read(n); f.read(4); return p


def read_rle(f, ntot):
    n, nrun = struct.unpack("<2q", read_rec(f))
    runs = struct.unpack("<%dq" % (2 * nrun), read_rec(f))
    raw = read_rec(f); packed = struct.unpack("<%dd" % (len(raw) // 8), raw)
    out = np.zeros(n); i = k = 0
    for r in range(nrun):
        i += runs[2 * r]; lit = runs[2 * r + 1]
        out[i:i + lit] = packed[k:k + lit]; i += lit; k += lit
    return out


def load_state(savedir, nx, ny):
    with open(os.path.join(savedir, "state.dat"), "rb") as f:
        return {k: read_rle(f, nx * ny).reshape(ny, nx) for k in ["h", "z", "hrs", "hg", "sd", "hs"]}


def read_wq(path):
    names = open(path).readline().strip().split(",")
    a = np.loadtxt(path, delimiter=",", skiprows=1)
    return {n: a[:, i] for i, n in enumerate(names)}

RAIN, TRAIN, TT, TRAMP = 30.0, 10800.0, 21600.0, 60.0
L1, L2, L3, L4 = 15.0, 60.0, 15.0, 15.0
A1, A2, A3, A4 = 0.1, 0.15, 0.05, 0.01
B1, B2, B3 = 0.12, 0.05, 0.01


def deriv(s1, s2, s3, r):
    q1 = A1 * max(s1 - L1, 0.0) + A2 * max(s1 - L2, 0.0); b1 = B1 * s1
    q2 = A3 * max(s2 - L3, 0.0); b2 = B2 * s2
    q3 = A4 * max(s3 - L4, 0.0); b3 = B3 * s3
    return (r - q1 - b1, b1 - q2 - b2, b2 - q3 - b3)


def rain(t):
    return RAIN if t <= TRAIN else (0.0 if t >= TRAIN + TRAMP else RAIN * (1 - (t - TRAIN) / TRAMP))


dt = 0.5; dth = dt / 3600; s = (0.0, 0.0, 0.0); t = 0.0
ts, swi, tanks = [0.0], [0.0], [(0, 0, 0)]
for i in range(int(TT / dt)):
    r, r2, r3 = rain(t), rain(t + dt / 2), rain(t + dt)
    k1 = deriv(*s, r); k2 = deriv(*(x + dth / 2 * k for x, k in zip(s, k1)), r2)
    k3 = deriv(*(x + dth / 2 * k for x, k in zip(s, k2)), r2); k4 = deriv(*(x + dth * k for x, k in zip(s, k3)), r3)
    s = tuple(x + dth / 6 * (a + 2 * b + 2 * c + d) for x, a, b, c, d in zip(s, k1, k2, k3, k4)); t += dt
    ts.append(t); swi.append(sum(s)); tanks.append(s)
ts = np.array(ts) / 60; swi = np.array(swi); tanks = np.array(tanks)
fin = np.loadtxt("result/Swi9998.txt"); mx = np.loadtxt("result/Swi9999.txt"); tmx = np.loadtxt("result/Swit9999.txt")
fig, ax = plt.subplots(figsize=(9, 4.2))
ax.plot(ts, swi, "k", lw=1.6, label="参照解 SWI(t)(RK4、dt = 0.5 s)")
for k, lab in enumerate(["第 1 タンク", "第 2 タンク", "第 3 タンク"]):
    ax.plot(ts, tanks[:, k], lw=0.9, ls="--", label=lab)
ax.plot([tmx.mean()], [mx.mean()], "C3o", ms=8, label=f"ENCflow 期間最大 Swi9999 = {mx.mean():.2f} mm @ {tmx.mean():.0f} min")
ax.plot([TT / 60], [fin.mean()], "C3s", ms=8, label=f"ENCflow 最終値 Swi9998 = {fin.mean():.2f} mm")
ax.axvspan(0, TRAIN / 60, color="0.92", label="降雨 30 mm/h")
ax.set_xlabel("t (min)"); ax.set_ylabel("貯留 (mm)"); ax.grid(alpha=0.3); ax.legend(fontsize=8)
ax.set_title("土壌雨量指数(気象庁 3 段タンク、全国一律定数): 30 mm/h × 3 h → 休止 3 h", fontsize=10)
fig.tight_layout(); fig.savefig("figs/swi.png", dpi=110); plt.close(fig)
ipk = swi.argmax()
print("ref final %.3f peak %.3f @ %.1f min; ENC final %.3f (min %.3f max %.3f) peak %.3f @ %.1f min" % (swi[-1], swi[ipk], ts[ipk], fin.mean(), fin.min(), fin.max(), mx.mean(), tmx.mean()))
