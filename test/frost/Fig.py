#!/usr/bin/env python3
"""test/frost の図を figs/frost.png に描く(事前に ./Run.sh を実行しておく)。
凍土による浸透抑制: 一定気温 −8.64 ℃で凍結指数 FI が線形に増え、低減係数 Ff = 1 − FI/fifull が 1 → 0 に
落ちる。地下貯留 S_grnd(t) と解析解 K t (1 − t/2T)、Ff の分布(t = 1800, 3600 s)。
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

def read_log(path):
    names, rows = None, []
    for line in open(path):
        if line.startswith("time,"):
            names = [s.strip() for s in line.split(",")]; continue
        f = line.split()
        if names is None or len(f) < len(names) or ":" not in f[0]:
            continue
        hh, mm, ss = f[0].split(":")
        rows.append([int(hh) * 3600 + int(mm) * 60 + float(ss)] + [float(v.rstrip("%")) for v in f[1:len(names)]])
    return names, np.array(rows)


names, lg = read_log("result/Log.txt")
t = lg[:, 0]; K = 1e-5; T = 3600.0
fig, axes = plt.subplots(1, 3, figsize=(15, 4), gridspec_kw={"width_ratios": [1.6, 1, 1]})
ax = axes[0]
ax.plot(t, lg[:, names.index("S_grnd(m)")], "C1o", ms=4, label="計算 S_grnd")
tt = np.linspace(0, T, 200)
ax.plot(tt, K * tt * (1 - tt / (2 * T)), "k-", lw=1, label="解析 K t (1 − t/2T)、K = 1e-5 m/s、T = 3600 s")
ax.plot(t, lg[:, names.index("S_surf(m)")], "C0s", ms=3, label="計算 S_surf")
ax2 = ax.twinx(); ax2.plot(tt, 1 - tt / T, "C3--", lw=1, label="低減係数 Ff = 1 − t/T"); ax2.set_ylabel("Ff", color="C3")
ax.set_xlabel("t (s)"); ax.set_ylabel("柱状換算水深 (m)"); ax.grid(alpha=0.3)
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels(); ax.legend(h1 + h2, l1 + l2, fontsize=8, loc="center left")
ax.set_title("浸透が凍結とともに止まる(S_grnd(3600) = K T/2 = 0.018 m)", fontsize=9)
for ax, n, tlab in [(axes[1], "Ff0001.txt", "1800 s"), (axes[2], "Ff0002.txt", "3600 s")]:
    a = np.loadtxt("result/" + n)
    im = ax.imshow(a, origin="lower", extent=[0, 42, 0, 42], cmap="Blues_r", vmin=0, vmax=1)
    ax.set_title(f"Ff の分布 t = {tlab}(一様 {a.mean():.3f})", fontsize=9); ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
    fig.colorbar(im, ax=ax, shrink=0.8)
fig.suptitle("凍土による浸透抑制(f_gwfrost): 平坦閉領域 21 × 21、初期水 0.05 m、気温 −8.64 ℃、fro_fifull = 0.36 ℃·day", fontsize=10)
fig.tight_layout(); fig.savefig("figs/frost.png", dpi=110); plt.close(fig)
k = names.index("S_grnd(m)")
print("S_grnd(3600) = %.14f (analytic discrete 0.0179975), Ff(1800) = %.4f, Ff(3600) = %.4f" % (lg[-1, k], np.loadtxt("result/Ff0001.txt").mean(), np.loadtxt("result/Ff0002.txt").mean()))
