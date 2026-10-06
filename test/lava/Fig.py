#!/usr/bin/env python3
"""test/lava の図を figs/lava.png に描く(事前に ./Run.sh を実行しておく)。
構成 1(Huppert): 平坦床・中央 1 セルの定率噴出(Newton 極限)。溶岩厚 hl の分布と、面積等価半径 r_A(t) と
相似解 r_N = 0.715 (g Q³/3ν)^{1/8} √t。構成 2(Bingham): 等勾配斜面の停止厚 h∞ = τ_y/(ρ g tanθ)。
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

def load_hl(savedir, nx, ny):
    with open(os.path.join(savedir, "lavaflow.dat"), "rb") as f:
        return read_rle(f, nx * ny).reshape(ny, nx)


G = 9.8
# 構成 1
NX1 = NY1 = 61; DX1 = 1.0; Q = 0.5; RHO = 2600.0; ETA = 2.0e4; NU = ETA / RHO; TT1 = 600.0
hl = load_hl("save", NX1, NY1)
frames = sorted(f for f in glob.glob("result/Hl[0-9]*.txt") if not f.endswith("9998.txt") and not f.endswith("9999.txt"))
fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))
im = axes[0].imshow(np.where(hl > 1e-4, hl, np.nan), origin="lower", extent=[0, 61, 0, 61], cmap="hot_r")
axes[0].set_title("構成 1: 溶岩厚 hl (m)、t = 600 s", fontsize=9); axes[0].set_xlabel("x (m)"); axes[0].set_ylabel("y (m)"); fig.colorbar(im, ax=axes[0], shrink=0.8)
ax = axes[1]
tt = np.linspace(1, TT1, 100)
rN = 0.715 * (G * Q ** 3 / (3 * NU)) ** (1.0 / 8.0) * np.sqrt(tt)
ax.plot(tt, rN, "k", lw=1.5, label="相似解 r_N = 0.715 (g Q³/3ν)^{1/8} √t")
ts, rs = [], []
for f in frames:
    a = np.loadtxt(f); n = int(os.path.basename(f)[2:6])
    ts.append(n * 150.0); rs.append(np.sqrt((a > 0.01).sum() * DX1 * DX1 / np.pi))
ts.append(TT1); rs.append(np.sqrt((hl > 0.01).sum() * DX1 * DX1 / np.pi))
ax.plot(ts, rs, "C3o", ms=6, label="計算: 面積等価半径 r_A = √(N_wet Δx²/π)")
ax.set_xlabel("t (s)"); ax.set_ylabel("半径 (m)"); ax.grid(alpha=0.3); ax.legend(fontsize=8)
ax.set_title("構成 1: 広がりの半径(Huppert 1982 の定率供給相似解)", fontsize=9)
print("huppert: sum hl*A = %.6f (V_in = %.1f), r_A(tt) = %.3f (r_N = %.3f, err %.1f%%)" % (hl.sum() * DX1 * DX1, Q * TT1, rs[-1], rN[-1], 100 * (rs[-1] / rN[-1] - 1)))
# 構成 2
NX2, NY2, DX2 = 100, 8, 1.0; ST = 0.2; TAUY = 2000.0
HINF = TAUY / (RHO * G * ST)
hl2 = load_hl("save_ty", NX2, NY2)
with open("save_ty/state.dat", "rb") as f:
    read_rle(f, NX2 * NY2); z2 = read_rle(f, NX2 * NY2).reshape(NY2, NX2)
z0 = np.loadtxt("zinit.txt")
dz = z2 - z0
x = (np.arange(NX2) + 0.5) * DX2
ax = axes[2]
ax.plot(x, (hl2 + dz).mean(axis=0), "C3o-", ms=3, lw=0.8, label="計算 hl + dz(固化分込み、行平均)")
ax.plot(x, dz.mean(axis=0), "C1--", lw=1, label="固化した厚さ dz")
ax.axhline(HINF, color="k", ls="--", lw=1, label=f"停止厚 h∞ = τ_y/(ρ g tanθ) = {HINF:.4f} m")
ax.set_xlabel("x (m)"); ax.set_ylabel("厚さ (m)"); ax.grid(alpha=0.3); ax.legend(fontsize=8)
ax.set_title("構成 2: Bingham 停止・固化(tanθ = 0.2、τ_y = 2000 Pa、噴出 300 s → 4800 s)", fontsize=9)
win = (x >= 14.5) & (x <= 35.5)      # Check_lava の検定窓 i = 15..35
print("bingham: <hl+dz> window %.4f (h_inf %.4f, err %.1f%%), solidified fraction %.3f" % ((hl2 + dz).mean(axis=0)[win].mean(), HINF, 100 * ((hl2 + dz).mean(axis=0)[win].mean() / HINF - 1), dz.sum() / (hl2.sum() + dz.sum())))
fig.suptitle("溶岩流(fn_lavaflow): Bingham 粘性重力流の Newton 極限(相似解)と停止厚(解析値)", fontsize=10)
fig.tight_layout(); fig.savefig("figs/lava.png", dpi=110); plt.close(fig)
