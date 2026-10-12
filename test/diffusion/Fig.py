#!/usr/bin/env python3
"""diffusion: ガウス形ジェットの拡散ベンチマークの図(figs/profile.png)

  左: 中央列のプローブ u(t)(点)と解析解(線)。粗格子(Δx = 1 m。○)と
      細格子(Δx = 0.5 m。×)を重ねる。
  中: 解析解の断面 u(y)(t = 0, 25, 50 s)と、粗格子の u00NN.txt の中央列(○)。
  右: 計算 − 解析解の推移(プローブごと。両格子)。
  使い方: ./Run.sh のあとで python3 Fig.py(result/ と result_fine/ を読む)。
  計算本体の外(方針 10)。matplotlib・numpy のみ。
"""
import glob, math, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

U0, SIGMA2, NU, YC = 0.05, 100.0, 4.0, 50.5     # param*.txt / jet_gaussian / Check_analytic.py と対


def uana(r, t):
    s2 = SIGMA2 + 2.0 * NU * t
    return U0 * math.sqrt(SIGMA2 / s2) * math.exp(-r * r / (2.0 * s2))


def probes(resdir, dy):
    out = []
    for fn in sorted(glob.glob(os.path.join(resdir, "probes", "probe*.csv"))):
        iy = None; t = []; u = []
        for line in open(fn):
            if line.startswith("#"):
                if line.startswith("# iy"):
                    iy = int(line.split(",")[1])
                continue
            c = line.split(",")
            if len(c) < 5:
                continue
            t.append(float(c[1]) * 60.0); u.append(float(c[4]))
        out.append((abs((iy - 0.5) * dy - YC), np.array(t), np.array(u)))
    return out


def fields(resdir):
    times = {}
    for l in open(os.path.join(resdir, "FILENUMBER.csv")):
        if l.startswith("#"):
            continue
        c = l.split(","); times[int(c[0])] = float(c[2])
    out = []
    for f in sorted(glob.glob(os.path.join(resdir, "u[0-9][0-9][0-9][0-9].txt"))):
        k = int(os.path.basename(f)[1:5])
        if k >= 9998:
            continue
        a = np.loadtxt(f)
        out.append((times.get(k, float("nan")), a[:, a.shape[1] // 2]))
    return out


plt.rcParams.update({"font.family": ["IPAGothic", "DejaVu Sans"], "font.size": 9})
fig, axs = plt.subplots(1, 3, figsize=(13, 4.2))
cols = ["#2a78d6", "#eb6834", "#8fbf6a", "#6b6a66"]

# 左: プローブ u(t)
ax = axs[0]
tt = np.linspace(0, 12.5, 200)
for k, (r, t, u) in enumerate(probes("result", 1.0)):
    ax.plot(tt, [uana(r, x) for x in tt], color=cols[k], lw=1.2)
    ax.plot(t[::4], u[::4], "o", color=cols[k], ms=4, mfc="none", label="r = %.0f m" % r)
if os.path.isdir("result_fine"):
    for k, (r, t, u) in enumerate(probes("result_fine", 0.5)):
        ax.plot(t[2::4], u[2::4], "x", color=cols[k], ms=4)
ax.set_xlabel("t (s)"); ax.set_ylabel("u (m/s)")
ax.set_title("プローブ u(t): 線 = 解析解、○ Δx = 1 m、× Δx = 0.5 m", loc="left", fontsize=9)
ax.legend(fontsize=8, frameon=False)

# 中: 断面 u(y)
ax = axs[1]
fl = fields("result")
ny = len(fl[0][1]) if fl else 101
y = (np.arange(ny) + 0.5) * 1.0
for k, (t, u) in enumerate(fl[:3]):
    ax.plot(y - YC, [uana(abs(yy - YC), t) for yy in y], color=cols[k], lw=1.2, label="t = %.4g s" % t)
    ax.plot(y[::4] - YC, u[::4], "o", color=cols[k], ms=3.5, mfc="none")
ax.set_xlim(-40, 40)
ax.set_xlabel("y − yc (m)"); ax.set_ylabel("u (m/s)")
ax.set_title("中央列の断面: 線 = 解析解、○ 計算(Δx = 1 m)", loc="left", fontsize=9)
ax.legend(fontsize=8, frameon=False)

# 右: 誤差
ax = axs[2]
for lab, resdir, dy, ls in (("Δx = 1 m", "result", 1.0, "-"), ("Δx = 0.5 m", "result_fine", 0.5, "--")):
    if not os.path.isdir(resdir):
        continue
    for k, (r, t, u) in enumerate(probes(resdir, dy)):
        err = u - np.array([uana(r, x) for x in t])
        ax.plot(t, err * 1e3, ls, color=cols[k], lw=1.1, label="%s, r = %.0f m" % (lab, round(r)))
ax.axhline(0, color="#d8d6d1", lw=0.8)
ax.set_xlabel("t (s)"); ax.set_ylabel("u_num − u_ana (10⁻³ m/s)")
ax.set_title("誤差の推移(許容 ±0.5 = U0 の 1%)", loc="left", fontsize=9)
ax.legend(fontsize=7, frameon=False, ncol=2)

fig.tight_layout()
os.makedirs("figs", exist_ok=True)
fig.savefig("figs/profile.png", dpi=130)
print("wrote figs/profile.png")
