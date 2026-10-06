#!/usr/bin/env python3
"""test/creep の図を figs/*.png に描く(事前に ./Run.sh を実行しておく)。

  python3 Fig.py

- figs/probes.png  : プローブ z(t)(r = 0, 10, 20 m)と線形拡散のガウス丘解析解。
                     morfac = 2(result_morfac2、水理時刻 25 s = 地形時間 50 s)も重ねる
- figs/profile.png : 最終時刻の中央行の地形 z(x) と解析解、および誤差
"""
import glob, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
matplotlib.rcParams["font.family"] = ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs("figs", exist_ok=True)

A, SIG2, D = 1.0, 100.0, 1.0           # param.txt / gaussian_hill / Check_analytic.py と対
IC, JC, DX = 51, 51, 1.0


def z_ana(r, tau):
    s = SIG2 + 2 * D * tau
    return A * SIG2 / s * np.exp(-r ** 2 / (2 * s))


def probes(d):
    out = []
    for fn in sorted(glob.glob(os.path.join(d, "probes", "probe*.csv"))):
        ix = iy = None
        for line in open(fn):
            if line.startswith("# ix"):
                ix = int(line.split(",")[1])
            elif line.startswith("# iy"):
                iy = int(line.split(",")[1])
        a = np.loadtxt(fn, delimiter=",", comments="#")
        t = a[:, 0] * 3600.0 if a[:, 0].max() < 1 else a[:, 0]   # 1 列目は時刻 (hour)
        r = np.hypot((ix - IC) * DX, (iy - JC) * DX)
        out.append((r, t, a[:, 2]))      # 3 列目 z(m)
    return out


fig, axes = plt.subplots(1, 2, figsize=(11, 4))
ax = axes[0]
for (r, t, z), c in zip(probes("result"), ["C0", "C1", "C2", "C3"]):
    ax.plot(t, z, "o", ms=3, color=c, label=f"計算 r = {r:.0f} m")
    tt = np.linspace(0, t.max(), 200)
    ax.plot(tt, z_ana(r, tt), "-", color=c, lw=1, label=f"解析解 r = {r:.0f} m" if r == 0 else None)
for (r, t, z) in probes("result_morfac2"):
    ax.plot(t * 2, z, "x", ms=4, color="k", label="morfac = 2(水理時刻 × 2 で描画)" if r == 0 else None)
ax.set_xlabel("地形時間 τ (s)")
ax.set_ylabel("z (m)")
ax.set_title("プローブの地盤高 z(t)", fontsize=10)
ax.grid(alpha=0.3)
ax.legend(fontsize=8)

ax = axes[1]
z = np.loadtxt(sorted(glob.glob("result/Z9998.txt") or glob.glob("result/Z0*.txt"))[-1])
x = (np.arange(z.shape[1]) - (IC - 1)) * DX
za = z_ana(np.abs(x), 50.0)
z0 = np.loadtxt("result/Z0000.txt")
ax.plot(x, z0[JC - 1], "0.6", lw=1, label="初期 (t = 0)")
ax.plot(x, z[JC - 1], "C0o", ms=2.5, label="計算 (τ = 50 s)")
ax.plot(x, za, "k-", lw=1, label="解析解 (τ = 50 s)")
ax.set_xlabel("x − x_c (m)")
ax.set_ylabel("z (m)")
ax.set_title("中央行の地形断面", fontsize=10)
ax.grid(alpha=0.3)
ax.legend(fontsize=8)
axr = ax.twinx()
axr.plot(x, (z[JC - 1] - za) * 1e4, "C3", lw=0.8)
axr.set_ylabel("計算 − 解析解 (×1e-4 m)", color="C3")
fig.suptitle("斜面クリープ(線形拡散 D = 1 m²/s)のガウス丘ベンチマーク(A = 1 m、σ = 10 m、Δx = 1 m)", fontsize=10)
fig.tight_layout()
fig.savefig("figs/profile.png", dpi=110)
plt.close(fig)
print("max |z - z_ana| on final field = %.2e m, volume change = %.2e m3" % (np.abs(z - z_ana(np.hypot(*np.meshgrid(x, x)), 50.0)).max(), (z.sum() - z0.sum()) * DX * DX))
