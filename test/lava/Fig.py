#!/usr/bin/env python3
"""test/lava の図を figs/lava.png に描く(事前に ./Run.sh を実行しておく)。引数 en で英語ラベルの図を en/figs/lava.png に描く。
構成 1(Huppert): 平坦床・中央 1 セルの定率噴出(Newton 極限)。溶岩厚 hl の分布と、面積等価半径 r_A(t) と
相似解 r_N = 0.715 (g Q³/3ν)^{1/8} √t。構成 2(Bingham): 等勾配斜面の停止厚 h∞ = τ_y/(ρ g tanθ)。
構成 4(ドーム): 平坦床・中央 1 セルからの噴出が止まった静止形の、格子軸の方向と斜めの方向の断面と、
塑性ドームの解析解 h² = (2τ_y/ρg)(R − r)、および上から見た溶岩厚。構成 5(壁): 高さ 10 m の段の前に
たまった溶岩が、壁に接する列まで全量固化した地形の断面。
"""
import glob, os, struct, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
EN = "en" in sys.argv[1:]
def T(ja, en): return en if EN else ja
FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)


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
fig, axs = plt.subplots(2, 3, figsize=(18, 8.4))
axes = axs.ravel()
im = axes[0].imshow(np.where(hl > 1e-4, hl, np.nan), origin="lower", extent=[0, 61, 0, 61], cmap="hot_r")
axes[0].set_title(T("構成 1: 溶岩厚 hl (m)、t = 600 s", "Configuration 1: lava thickness hl (m), t = 600 s"), fontsize=9)
axes[0].set_xlabel("x (m)"); axes[0].set_ylabel("y (m)"); fig.colorbar(im, ax=axes[0], shrink=0.8)
ax = axes[1]
tt = np.linspace(1, TT1, 100)
rN = 0.715 * (G * Q ** 3 / (3 * NU)) ** (1.0 / 8.0) * np.sqrt(tt)
ax.plot(tt, rN, "k", lw=1.5, label=T("相似解 r_N = 0.715 (g Q³/3ν)^{1/8} √t", "similarity solution r_N = 0.715 (g Q³/3ν)^{1/8} √t"))
ts, rs = [], []
for f in frames:
    a = np.loadtxt(f); n = int(os.path.basename(f)[2:6])
    ts.append(n * 150.0); rs.append(np.sqrt((a > 0.01).sum() * DX1 * DX1 / np.pi))
ts.append(TT1); rs.append(np.sqrt((hl > 0.01).sum() * DX1 * DX1 / np.pi))
ax.plot(ts, rs, "C3o", ms=6, label=T("計算: 面積等価半径 r_A = √(N_wet Δx²/π)", "computed: area-equivalent radius r_A = √(N_wet Δx²/π)"))
ax.set_xlabel("t (s)"); ax.set_ylabel(T("半径 (m)", "radius (m)")); ax.grid(alpha=0.3); ax.legend(fontsize=8)
ax.set_title(T("構成 1: 広がりの半径(Huppert 1982 の定率供給相似解)", "Configuration 1: spreading radius (Huppert 1982 similarity solution)"), fontsize=9)
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
ax.plot(x, (hl2 + dz).mean(axis=0), "C3o-", ms=3, lw=0.8, label=T("計算 hl + dz(固化分込み、行平均)", "computed hl + dz (incl. solidified part, row average)"))
ax.plot(x, dz.mean(axis=0), "C1--", lw=1, label=T("固化した厚さ dz", "solidified thickness dz"))
ax.axhline(HINF, color="k", ls="--", lw=1, label=T(f"停止厚 h∞ = τ_y/(ρ g tanθ) = {HINF:.4f} m", f"stopping thickness h∞ = τ_y/(ρ g tanθ) = {HINF:.4f} m"))
ax.set_xlabel("x (m)"); ax.set_ylabel(T("厚さ (m)", "thickness (m)")); ax.grid(alpha=0.3); ax.legend(fontsize=8)
ax.set_title(T("構成 2: Bingham 停止・固化(tanθ = 0.2、τ_y = 2000 Pa、噴出 300 s → 4800 s)",
               "Configuration 2: Bingham stopping (tanθ = 0.2, τ_y = 2000 Pa, 300 s → 4800 s)"), fontsize=9)
win = (x >= 14.5) & (x <= 35.5)      # Check_lava の検定窓 i = 15..35
print("bingham: <hl+dz> window %.4f (h_inf %.4f, err %.1f%%), solidified fraction %.3f" % ((hl2 + dz).mean(axis=0)[win].mean(), HINF, 100 * ((hl2 + dz).mean(axis=0)[win].mean() / HINF - 1), dz.sum() / (hl2.sum() + dz.sum())))
# 構成 4
NX4 = NY4 = 61; DX4 = 1.0; IC4 = JC4 = 31; TAUY4 = 1.0e4
hl4 = load_hl("save_dome", NX4, NY4)
V4 = hl4.sum() * DX4 * DX4
A4 = 2 * TAUY4 / (RHO * G)
R4 = (V4 / ((8 * np.pi / 15) * np.sqrt(A4))) ** 0.4
ax = axes[3]
rr = np.linspace(0, R4, 300)
ax.plot(rr, np.sqrt(A4 * (R4 - rr)), "k", lw=1.5, label=T("塑性ドームの解析解 h² = (2τ_y/ρg)(R − r)", "plastic dome h² = (2τ_y/ρg)(R − r)"))
ax.plot(-rr, np.sqrt(A4 * (R4 - rr)), "k", lw=1.5)
xs = (np.arange(NX4) - (IC4 - 1)) * DX4
ax.plot(xs, hl4[JC4 - 1, :], "C0o-", ms=3, lw=0.8, label=T("計算: 格子軸の方向", "computed: along a grid axis"))
kk = np.arange(-(IC4 - 1), NX4 - (IC4 - 1))
ax.plot(kk * DX4 * np.sqrt(2), hl4[JC4 - 1 + kk, IC4 - 1 + kk], "C3s-", ms=3, lw=0.8, label=T("計算: 斜めの方向(45°)", "computed: along the diagonal (45°)"))
ax.set_xlim(-25, 25); ax.set_ylim(0, 4.5)
ax.set_xlabel(T("噴火口からの距離 (m)", "distance from the vent (m)")); ax.set_ylabel(T("溶岩厚 hl (m)", "lava thickness hl (m)"))
ax.grid(alpha=0.3); ax.legend(fontsize=8, loc="lower center")
ax.set_title(T("構成 4: 塑性ドームの静止形(平坦床・1 火口、τ_y = 10⁴ Pa、噴出 900 s → 6000 s)",
               "Configuration 4: plastic dome at rest (flat bed, one vent, τ_y = 10⁴ Pa, 900 s → 6000 s)"), fontsize=9)
print("dome: h(center) = %.3f m (H = %.3f m), R = %.2f m" % (hl4[JC4 - 1, IC4 - 1], np.sqrt(A4 * R4), R4))
ax = axes[4]
im = ax.imshow(np.where(hl4 > 0.01, hl4, np.nan), origin="lower", extent=[-30.5, 30.5, -30.5, 30.5], cmap="hot_r")
th = np.linspace(0, 2 * np.pi, 200)
ax.plot(R4 * np.cos(th), R4 * np.sin(th), "b--", lw=1, label=T(f"解析解の半径 R = {R4:.1f} m", f"analytic radius R = {R4:.1f} m"))
ax.set_xlim(-24, 24); ax.set_ylim(-24, 24); ax.set_aspect("equal")
ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)"); ax.legend(fontsize=8, loc="lower right")
fig.colorbar(im, ax=ax, shrink=0.8)
ax.set_title(T("構成 4: 静止形の溶岩厚 hl (m)(上から見た図)", "Configuration 4: lava thickness hl (m) at rest, plan view"), fontsize=9)
# 構成 5
NX5, NY5, DX5, IWALL5, ZWALL5 = 40, 8, 1.0, 31, 10.0
hl5 = load_hl("save_wall", NX5, NY5)
with open("save_wall/state.dat", "rb") as f:
    read_rle(f, NX5 * NY5); z5 = read_rle(f, NX5 * NY5).reshape(NY5, NX5)
z05 = np.where(np.arange(1, NX5 + 1) >= IWALL5, ZWALL5, 0.0)
x5 = (np.arange(NX5) + 0.5) * DX5
ax = axes[5]
xe = np.arange(NX5 + 1) * DX5
ax.fill_between(xe, np.r_[z05, z05[-1]], -0.2, step="post", color="0.75", label=T("地盤(高さ 10 m の段 = 壁)", "ground (10 m step = wall)"))
ax.fill_between(xe, np.r_[z05, z05[-1]], np.r_[z5.mean(axis=0), z5.mean(axis=0)[-1]], step="post", color="C1", alpha=0.8, label=T("固化した溶岩 dz(行平均)", "solidified lava dz (row average)"))
ax.step(xe, np.r_[(z5 + hl5).mean(axis=0), (z5 + hl5).mean(axis=0)[-1]], where="post", color="C3", lw=1, label=T("溶岩面(残る溶岩 hl 込み)", "lava surface (incl. molten hl)"))
ax.axvline((IWALL5 - 1) * DX5, color="k", lw=0.8, ls=":")
ax.set_xlim(15, 35); ax.set_ylim(-0.2, 2.0)
ax.set_xlabel("x (m)"); ax.set_ylabel(T("標高 (m)", "elevation (m)")); ax.grid(alpha=0.3); ax.legend(fontsize=8, loc="upper left")
ax.set_title(T("構成 5: 壁の前の溶岩だまり(壁に接する列まで全量固化)", "Configuration 5: lava pond against a wall (all solidified, up to the wall)"), fontsize=9)
print("wall: solidified fraction %.4f, wall column min dz %.3f m, molten max %.2e m" % ((z5 - z05).sum() / ((z5 - z05).sum() + hl5.sum()), (z5 - z05)[:, IWALL5 - 2].min(), hl5.max()))
fig.suptitle(T("溶岩流(fn_lavaflow): Newton 極限(相似解)、停止厚(解析値)、塑性ドームの静止形(解析解)、壁の前の溶岩だまりの固化",
               "Lava flow (fn_lavaflow): Newtonian limit (similarity solution), stopping thickness (analytical value), plastic dome at rest (analytical solution) and solidification of a pond against a wall"), fontsize=10)
fig.tight_layout(); fig.savefig(f"{FIGDIR}/lava.png", dpi=110); plt.close(fig)
