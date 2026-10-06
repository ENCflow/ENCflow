#!/usr/bin/env python3
"""test/glacier の図を figs/*.png に描く(事前に ./Run.sh を実行しておく)。

  python3 Fig.py

- figs/halfar.png : Halfar ドーム。初期(t = t0)と最終(地形時間 t0 + 80 日 ≈ 2 t0)の
                    中央行の氷厚と相似解、および氷厚分布の計算 − 解析解
- figs/cirque.png : カール形成スモークテスト。初期地形(円錐)、最終氷厚 Hi、地形変化 Z9998 − Z0000
"""
import glob, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
matplotlib.rcParams["font.family"] = ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs("figs", exist_ok=True)

# Check_halfar.py / Make_input.py と対で保守する定数
NX = NY = 61; DX = 25.0; IC = JC = 31
H0, R0 = 200.0, 600.0
A_YR = 1.0e-16; RHOI, GG = 900.0, 9.8; YR_S = 365.25 * 86400.0
TT, MORFAC = 86400.0, 80.0
n_gl = 3
A_S = A_YR / YR_S
GAMMA = 2.0 * A_S * (RHOI * GG) ** n_gl / (n_gl + 2)
T0 = (1.0 / (18.0 * GAMMA)) * (7.0 / 4.0) ** 3 * R0 ** 4 / H0 ** 7


def halfar(r, t):
    f = (T0 / t) ** (1.0 / 18.0) * r / R0
    return np.where(f < 1, H0 * (T0 / t) ** (1.0 / 9.0) * np.clip(1 - f ** (4.0 / 3.0), 0, None) ** (3.0 / 7.0), 0.0)


hi0 = np.loadtxt("result/Hi0000.txt")
hi1 = np.loadtxt("result/Hi9998.txt")
x = (np.arange(NX) + 0.5) * DX - (IC - 0.5) * DX
X, Y = np.meshgrid(x, x)
R = np.hypot(X, Y)
t1 = T0 + TT * MORFAC
ana1 = halfar(R, t1)

fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [1.4, 1]})
ax = axes[0]
ax.plot(x, hi0[JC - 1], "0.5", lw=1.2, label="初期 t = t0(相似解を与える)")
ax.plot(x, hi1[JC - 1], "C0o", ms=3, label=f"ENCflow t = t0 + {TT*MORFAC/86400:.0f} 日")
ax.plot(x, ana1[JC - 1], "k-", lw=1.2, label="相似解(Halfar 1983)")
ax.set_xlabel("x − x_c (m)"); ax.set_ylabel("氷厚 H (m)")
ax.set_title(f"中央行の氷厚(t0 = {T0/86400:.1f} 日、地形時間 ≈ {t1/T0:.2f} t0)", fontsize=10)
ax.legend(fontsize=8); ax.grid(alpha=0.3)
ax = axes[1]
im = ax.imshow(hi1 - ana1, origin="lower", extent=[x[0], x[-1], x[0], x[-1]], cmap="RdBu_r", vmin=-40, vmax=40)
ax.set_title("氷厚の計算 − 相似解 (m)", fontsize=10); ax.set_xlabel("x − x_c (m)"); ax.set_ylabel("y − y_c (m)")
fig.colorbar(im, ax=ax, shrink=0.85)
fig.suptitle("Halfar ドーム(平坦床・質量収支ゼロの SIA 流動、Δx = 25 m、Glen A = 1e-16 Pa⁻³ yr⁻¹)", fontsize=10)
fig.tight_layout()
fig.savefig("figs/halfar.png", dpi=110)
plt.close(fig)
err = hi1 - ana1
print("Halfar: mean|err| %.2f m, max|err| %.1f m, center err %.1f m, volume ratio %.6f" % (np.abs(err).mean(), np.abs(err).max(), err[JC - 1, IC - 1], hi1.sum() / hi0.sum()))

if os.path.isdir("result_cirque"):
    z0 = np.loadtxt("result_cirque/Z0000.txt"); z1 = np.loadtxt("result_cirque/Z9998.txt"); hi = np.loadtxt("result_cirque/Hi9998.txt")
    nx = z0.shape[1]
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    for ax, a, title, cmap, kw in [(axes[0], z0, "初期地形 z (m)(円錐山体)", "terrain", {}),
                                   (axes[1], np.where(hi > 0.01, hi, np.nan), "最終氷厚 Hi (m)", "Blues", {}),
                                   (axes[2], z1 - z0, "地形変化 Z9998 − Z0000 (m)", "Reds_r", {"vmax": 0})]:
        im = ax.imshow(a, origin="lower", cmap=cmap, **kw)
        ax.set_title(title, fontsize=10); ax.set_xlabel("ix"); ax.set_ylabel("iy")
        fig.colorbar(im, ax=ax, shrink=0.8)
    fig.suptitle("カール形成スモークテスト(雪 → 雪崩再配分 → 氷化 → SIA 流動 + 滑動 → 氷河侵食。1 日 × 地形時間 500 倍)", fontsize=10)
    fig.tight_layout()
    fig.savefig("figs/cirque.png", dpi=110)
    plt.close(fig)
    print("cirque: max Hi %.1f m, min dz %.3f m, max dz %.3f m, eroded cells %d" % (hi.max(), (z1 - z0).min(), (z1 - z0).max(), ((z1 - z0) < -0.01).sum()))
