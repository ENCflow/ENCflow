#!/usr/bin/env python3
"""test/creep の図を figs/*.png に描く(事前に ./Run.sh を実行しておく)。

  python3 Fig.py

- figs/probes.png  : プローブ z(t)(r = 0, 10, 20 m)と線形拡散のガウス丘解析解。
                     morfac = 2(result_morfac2、水理時刻 25 s = 地形時間 50 s)も重ねる
- figs/profile.png : ガウス丘の断面(解析解)とプローブの計算値、プローブ誤差の推移(上の 2 枚は 1 つの PNG)
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
        t = np.round(a[:, 1] * 60.0, 3)        # 2 列目 t(min) → s(印字桁の丸めを戻す)
        r = np.hypot((ix - IC) * DX, (iy - JC) * DX)
        out.append((r, t, a[:, 2]))      # 3 列目 z(m)
    return out


fig, axes = plt.subplots(1, 3, figsize=(15, 4))
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
# 最終地形の場は出力していない(Z0000 のみ)ので、解析解の断面にプローブ値を重ね、誤差の推移を描く
r = np.linspace(-50, 50, 401)
for tau, c in [(0, "0.6"), (25, "C1"), (50, "k")]:
    ax.plot(r, z_ana(np.abs(r), tau), color=c, lw=1.2, label=f"解析解 τ = {tau} s")
for (rr, t, z) in probes("result"):
    for tau, c in [(25, "C1"), (50, "k")]:
        k = np.argmin(np.abs(t - tau))
        ax.plot([rr, -rr], [z[k], z[k]], "o", color=c, ms=5, mfc="none")
ax.set_xlabel("r (m)")
ax.set_ylabel("z (m)")
ax.set_title("ガウス丘の断面(線: 解析解、○: プローブの計算値)", fontsize=10)
ax.grid(alpha=0.3)
ax.legend(fontsize=8)
ax = axes[2]
for (rr, t, z), c in zip(probes("result"), ["C0", "C1", "C2", "C3"]):
    ax.plot(t, (z - z_ana(rr, t)) * 1e4, "-", color=c, lw=1, label=f"morfac = 1, r = {rr:.0f} m")
for (rr, t, z), c in zip(probes("result_morfac2"), ["C0", "C1", "C2", "C3"]):
    ax.plot(t * 2, (z - z_ana(rr, t * 2)) * 1e4, "--", color=c, lw=1, label=f"morfac = 2, r = {rr:.0f} m" if rr < 20 else None)
ax.set_xlabel("地形時間 τ (s)")
ax.set_ylabel("計算 − 解析解 (×1e-4 m)")
ax.set_title("プローブ誤差の推移(破線: morfac = 2)", fontsize=10)
ax.grid(alpha=0.3)
ax.legend(fontsize=7, ncol=2)
fig.suptitle("斜面クリープ(線形拡散 D = 1 m²/s)のガウス丘ベンチマーク(A = 1 m、σ = 10 m、Δx = 1 m)", fontsize=10)
fig.tight_layout()
fig.savefig("figs/profile.png", dpi=110)
plt.close(fig)
for d, mf in (("result", 1.0), ("result_morfac2", 2.0)):
    for (rr, t, z) in probes(d):
        print("%-15s r=%5.1f m  max|z - z_ana| = %.2e m" % (d, rr, np.abs(z - z_ana(rr, t * mf)).max()))
