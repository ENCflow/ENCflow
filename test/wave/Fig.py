#!/usr/bin/env python3
"""test/wave の図を figs/*.png に描く。

事前に ./Run.sh(result/)を実行しておく。result_cap/(param_cap.txt)が
あれば中央断面の図に重ねる(reference と一致するので線は重なる)。

  python3 Fig.py

- figs/profile.png : 中央行(y = 50 m)の水位 e = z + h の断面。t = 0, 1, 2, 4, 8 s
- figs/map.png     : 水位分布 t = 2, 8 s と期間最大水深 H9999
- figs/log.png     : 波面半径 r_f(t) と、画面出力(Log.txt)の h_max・V_max・Cn_max・Runge の時系列
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
# 日本語ラベル用のフォント(入っているものが使われる。無ければ豆腐になるだけ)
matplotlib.rcParams["font.family"] = ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

LX = 100.0
os.makedirs("figs", exist_ok=True)


def load(name, d="result"):
    return np.loadtxt(os.path.join(d, name))


def read_log(path):
    """Log.txt → 秒, S, Runge%, Cn_max, h_max, V_max, Q_max"""
    rows = []
    for line in open(path):
        f = line.split()
        if len(f) < 9 or ":" not in f[0]:
            continue
        hh, mm, ss = f[0].split(":")
        t = int(hh) * 3600 + int(mm) * 60 + float(ss)
        rows.append([t, float(f[2]), float(f[3].rstrip("%")), float(f[5]),
                     float(f[6]), float(f[7]), float(f[8])])
    return np.array(rows)


e0 = load("E0000.txt")
ny, nx = e0.shape
dx = LX / nx
x = (np.arange(nx) + 0.5) * dx
jc = ny // 2            # 中央行(y = 50 m)

# ---- 図 1: 中央断面 ----
fig, ax = plt.subplots(figsize=(8, 4.2))
for n, c in zip([0, 1, 2, 4, 8], ["0.3", "C0", "C1", "C2", "C3"]):
    e = load(f"E{n:04d}.txt")
    ax.plot(x, e[jc, :], color=c, lw=1.4, label=f"t = {n} s")
if os.path.isdir("result_cap"):
    e = load("E0008.txt", "result_cap")
    ax.plot(x, e[jc, :], "k:", lw=1.0, label="t = 8 s, f_dry_head_cap = 1")
ax.axhline(1.0, color="0.8", lw=0.8)
ax.set_xlim(0, LX)
ax.set_xlabel("x (m)")
ax.set_ylabel("水位 e = z + h (m)")
ax.set_title("中央行 (y = 50 m) の水位断面。初期の山は高さ 1 m・半径 15 m のコサイン型")
ax.legend(ncol=2, fontsize=9)
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig("figs/profile.png", dpi=110)
plt.close(fig)

# ---- 図 2: 分布図 ----
fig, axes = plt.subplots(1, 3, figsize=(12, 4.2))
ext = [0, LX, 0, LX]
for ax, (name, title, vmin, vmax, cmap) in zip(axes, [
        ("E0002.txt", "水位 e (m), t = 2 s", 0.8, 1.3, "RdBu_r"),
        ("E0008.txt", "水位 e (m), t = 8 s", 0.8, 1.3, "RdBu_r"),
        ("H9999.txt", "期間最大水深 H9999 (m)", 1.0, 2.0, "viridis")]):
    a = load(name)
    im = ax.imshow(a, origin="lower", extent=ext, vmin=vmin, vmax=vmax, cmap=cmap)
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    fig.colorbar(im, ax=ax, shrink=0.8)
fig.tight_layout()
fig.savefig("figs/map.png", dpi=110)
plt.close(fig)

# ---- 図 3: 波面の位置と画面出力の時系列 ----
# 波面半径 r_f(t): 中央行で水位が静水 + 1 cm を超える最外点(両側の平均)
g = 9.8
tf, rf = [], []
for n in range(0, 9):
    e = load(f"E{n:04d}.txt")[jc, :]
    idx = np.where(e > 1.01)[0]
    if len(idx) == 0:
        continue
    tf.append(float(n))
    rf.append(0.5 * (x[idx[-1]] - x[idx[0]]))
tf, rf = np.array(tf), np.array(rf)
lg = read_log("result/Log.txt")
fig, axes = plt.subplots(1, 3, figsize=(12, 3.6))
axes[0].plot(tf, rf, "o-", ms=4, label="計算(水位 > 静水 + 1 cm の最外点)")
axes[0].plot(tf, rf[0] + np.sqrt(g * 1.0) * tf, "k--", lw=1, label="r0 + √(g h0) t  (h0 = 1 m)")
axes[0].set_title("波面の半径 r_f(t)", fontsize=10)
axes[0].set_ylabel("r_f (m)")
axes[0].legend(fontsize=8, loc="upper left")
axes[1].plot(lg[:, 0], lg[:, 4], "o-", ms=3, label="h_max (m)")
axes[1].plot(lg[:, 0], lg[:, 5], "s-", ms=3, label="V_max (m/s)")
axes[1].plot(lg[:, 0], lg[:, 3], "^-", ms=3, label="Cn_max")
axes[1].legend(fontsize=9)
axes[1].set_title("最大水深・最大流速・最大クーラン数", fontsize=10)
axes[2].plot(lg[:, 0], lg[:, 2], "o-", ms=3)
axes[2].set_title("適応的ルンゲ・クッタの適用率 Runge (%)", fontsize=10)
for ax in axes:
    ax.set_xlabel("t (s)")
    ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig("figs/log.png", dpi=110)
plt.close(fig)

print("front radius r_f (m) at t = 0..8 s:", " ".join("%.1f" % r for r in rf))
print("mean front speed %.2f m/s (sqrt(g h0) = %.2f, sqrt(g h_max0) = %.2f)" % ((rf[-1] - rf[1]) / (tf[-1] - tf[1]), np.sqrt(g), np.sqrt(2 * g)))
print("S0 = %.14f, max |S/S0-1| = %.1e" % (lg[0, 1], np.abs(lg[:, 1] / lg[0, 1] - 1).max()))
print("h_max(t=0) = %.4f, min h_max = %.4f at t = %.1f s" % (lg[0, 4], lg[:, 4].min(), lg[lg[:, 4].argmin(), 0]))
print("V_max peak = %.4f at t = %.1f s; Cn_max peak = %.4f" % (lg[:, 5].max(), lg[lg[:, 5].argmax(), 0], lg[:, 3].max()))
h9999 = load("H9999.txt")
print("H9999 max = %.4f; e(8 s) center = %.4f; e(8 s) min/max on center row = %.4f / %.4f"
      % (h9999.max(), load("E0008.txt")[jc, nx // 2], load("E0008.txt")[jc].min(), load("E0008.txt")[jc].max()))
