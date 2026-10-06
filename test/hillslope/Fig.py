#!/usr/bin/env python3
"""test/hillslope の図を figs/*.png に描く。

事前に Make_hillslope.py で plane / stairplane / vcat の各ケースを生成し、
全 param_*.txt を実行しておく(README の「実行」節)。

  python3 Fig.py

- figs/plane.png : 一様平面斜面(勾配 0.05 / 0.20)の出口流量。スキーム 1・3 と
                   運動学的波の解析解(立ち上がり q = α (P t)^{5/3}、平衡 q_e = P L)
- figs/stair.png : 階段斜面(2 セルごとに 10 m 段差)の出口流量。移流項なし・スキーム 1・3
- figs/vcat.png  : V 字集水域の出口流量。dx = 100 m と 10 m、スキーム 1・3
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
matplotlib.rcParams["font.family"] = ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

os.makedirs("figs", exist_ok=True)
G = 9.8


def flux(d):
    p = os.path.join(d, "fluxes", "flux0001.csv")
    if not os.path.isfile(p):
        return None
    a = np.loadtxt(p, delimiter=",", comments="#")
    return a[:, 1], a[:, 2]          # t (min), Q (m3/s)


def peak(d):
    f = flux(d)
    return (np.nan, np.nan) if f is None else (f[1].max(), f[0][f[1].argmax()])


# ---- 図 1: 一様平面斜面と運動学的波 ----
P = 200.0 / 1000 / 3600          # 降雨強度 (m/s)
W = 2000.0                       # 斜面幅 (m)
L = 1900.0                       # 測線の面(ix = 19 と 20 の境界 x = 1900 m)までの斜面長 (m)
n = 0.15
fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
for ax, (name, S0) in zip(axes, [("p05", 0.05), ("p20", 0.20)]):
    alpha = np.sqrt(S0) / n
    te = (L / (alpha * P ** (2.0 / 3.0))) ** 0.6          # 平衡到達時刻 (s)
    t = np.linspace(0, 14400, 600)
    q = np.where(t < te, alpha * (P * t) ** (5.0 / 3.0), P * L) * W
    ax.plot(t / 60, q, "k", lw=2, label="運動学的波の解析解")
    for s, c, ls in [(1, "C0", "-"), (3, "C3", "--")]:
        f = flux(f"result_{name}_s{s}")
        if f is not None:
            ax.plot(f[0], f[1], color=c, ls=ls, lw=1.4, label=f"スキーム {s}")
    ax.axhline(P * L * W, color="0.6", lw=0.8)
    ax.set_title(f"勾配 {S0}(平衡 Q = P L W = {P*L*W:.1f} m³/s、t_e = {te/60:.0f} min)", fontsize=10)
    ax.set_xlabel("t (min)")
    ax.set_xlim(0, 240)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9, loc="lower right")
axes[0].set_ylabel("出口流量 Q (m³/s)")
fig.suptitle("一様平面斜面(2 km × 2 km、Δx = 100 m、n = 0.15、降雨 200 mm/h)", fontsize=11)
fig.tight_layout()
fig.savefig("figs/plane.png", dpi=110)
plt.close(fig)

# ---- 図 2: 階段斜面 ----
fig, (ax, ax2) = plt.subplots(1, 2, figsize=(11, 4), gridspec_kw={"width_ratios": [2, 1]})
for tag, lab, c, ls in [("noadv", "移流項なし(拡散波 f_govequation = 1)", "C2", "-"),
                        ("s1", "スキーム 1", "C0", "--"), ("s3", "スキーム 3", "C3", ":")]:
    f = flux(f"result_sp05_{tag}")
    if f is not None:
        ax.plot(f[0], f[1], color=c, ls=ls, lw=1.6, label=lab)
fp = flux("result_p05_s3")
if fp is not None:
    ax.plot(fp[0], fp[1], color="0.5", lw=1.0, label="(参考)滑らかな斜面 0.05、スキーム 3")
ax.set_xlim(0, 240)
ax.set_xlabel("t (min)")
ax.set_ylabel("出口流量 Q (m³/s)")
ax.set_title("階段斜面の出口流量", fontsize=10)
ax.grid(alpha=0.3)
ax.legend(fontsize=8)
if os.path.isfile("z_sp05.txt"):
    z = np.loadtxt("z_sp05.txt")[0]
    xs = (np.arange(len(z)) + 0.5) * 100
    ax2.step(np.arange(len(z) + 1) * 100, np.r_[z, z[-1]], where="post", color="k", lw=1.5, label="階段斜面 z")
    ax2.plot([0, 2000], [100, 100 - 0.05 * 2000], "C3--", lw=1, label="平均勾配 0.05")
    ax2.set_xlabel("x (m)")
    ax2.set_ylabel("z (m)")
    ax2.set_title("地形(2 セルごとに 10 m の段差)", fontsize=10)
    ax2.legend(fontsize=8)
    ax2.grid(alpha=0.3)
fig.tight_layout()
fig.savefig("figs/stair.png", dpi=110)
plt.close(fig)

# ---- 図 3: V 字集水域 ----
fig, ax = plt.subplots(figsize=(8, 4.2))
for name, lab, c in [("c100", "Δx = 100 m", "C0"), ("f10", "Δx = 10 m", "C3")]:
    for s, ls in [(1, "-"), (3, "--")]:
        f = flux(f"result_{name}_s{s}")
        if f is not None:
            ax.plot(f[0], f[1], color=c, ls=ls, lw=1.4, label=f"{lab}、スキーム {s}")
ax.axvspan(0, 90, color="0.9", label="降雨 10.8 mm/h")
ax.set_xlim(0, 180)
ax.set_xlabel("t (min)")
ax.set_ylabel("出口流量 Q (m³/s)")
ax.set_title("V 字集水域(1 km × 1.7 km。両側 800 m の斜面 → 中央 100 m の河道帯、縦断 0.02)", fontsize=10)
ax.grid(alpha=0.3)
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig("figs/vcat.png", dpi=110)
plt.close(fig)

# ---- 数表 ----
print("case            peak Q (m3/s)  t_peak (min)  t50 (min)  t90 (min)  volume 3h (m3)")
for d in ["result_p05_s1", "result_p05_s3", "result_p20_s1", "result_p20_s3",
          "result_sp05_noadv", "result_sp05_s1", "result_sp05_s3",
          "result_c100_s1", "result_c100_s3", "result_f10_s1", "result_f10_s3"]:
    f = flux(d)
    if f is None:
        continue
    t, q = f
    qm = q.max()
    t50 = t[np.argmax(q >= 0.5 * qm)]
    t90 = t[np.argmax(q >= 0.9 * qm)]
    vol = np.trapezoid(q, t * 60)
    print("%-16s %10.3f %10.0f %10.0f %10.0f %14.0f" % (d, qm, t[q.argmax()], t50, t90, vol))
for name, S0 in [("p05", 0.05), ("p20", 0.20)]:
    alpha = np.sqrt(S0) / n
    te = (L / (alpha * P ** (2.0 / 3.0))) ** 0.6
    t90a = (0.9 ** 0.6) * te
    print("kinematic %s: Q_e = %.1f m3/s, t_e = %.1f min, t90 = %.1f min" % (name, P * L * W, te / 60, t90a / 60))
