#!/usr/bin/env python3
"""test/volcano の図を figs/*.png に描く(事前に ./Run.sh を実行しておく)。

  python3 Fig.py

- figs/voellmy.png : 構成 1(Voellmy 定常等流)。流動深 h_t = h + hs の全行平均の縦断と
                     解析解 h_ana = (q_m²/(ξ(tanθ − μ)))^{1/3}、濃度 C
- figs/tauy.png    : 構成 2(τ_y ランアウト)。初期の崩壊深、最終の地形変化 dz と残存 hs
"""
import os, struct
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
    """state.dat → dict(h, z, hrs, hg, sd, hs) を (ny, nx) で返す"""
    with open(os.path.join(savedir, "state.dat"), "rb") as f:
        names = ["h", "z", "hrs", "hg", "sd", "hs"]
        return {k: read_rle(f, nx * ny).reshape(ny, nx) for k in names}


# ---- 構成 1 ----
NX1, NY1, DX1 = 150, 8, 1.0
ST, MU, XI = 0.2, 0.1, 200.0
QIN, CS = 4.0, 0.8
QM = QIN * (1 + CS) / (NY1 * DX1)
HANA = (QM ** 2 / (XI * (ST - MU))) ** (1.0 / 3.0)
st = load_state("save", NX1, NY1)
x = (np.arange(NX1) + 0.5) * DX1
ht = (st["h"] + st["hs"]).mean(axis=0)
C = np.where(st["h"] + st["hs"] > 1e-6, st["hs"] / np.maximum(st["h"] + st["hs"], 1e-12), np.nan).mean(axis=0)
fig, axes = plt.subplots(2, 1, figsize=(9, 6), sharex=True)
ax = axes[0]
ax.plot(x, ht, "C0o-", ms=2.5, lw=0.8, label="ENCflow h_t = h + hs(全行平均)")
ax.axhline(HANA, color="k", ls="--", lw=1.2, label=f"解析解 (q_m²/(ξ(tanθ−μ)))^(1/3) = {HANA:.4f} m")
ax.axvspan(60, 100, color="0.9", label="検定窓 x ∈ [60, 100]")
ax.set_ylabel("流動深 h_t (m)")
ax.set_ylim(0, HANA * 1.6)
ax.set_title(f"Voellmy 定常等流(tanθ = {ST}、μ = {MU}、ξ = {XI:.0f}、q_m = {QM:.2f} m²/s、p_diagratio = 0)", fontsize=10)
ax.legend(fontsize=8); ax.grid(alpha=0.3)
ax = axes[1]
ax.plot(x, C, "C1o-", ms=2.5, lw=0.8, label="混合体積濃度 C = hs/(h + hs)")
ax.axhline(CS / (1 + CS), color="k", ls="--", lw=1, label=f"理論 cs/(1 + cs) = {CS/(1+CS):.3f}")
ax.set_xlabel("x (m)"); ax.set_ylabel("C"); ax.set_ylim(0, 0.7)
ax.legend(fontsize=8); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig("figs/voellmy.png", dpi=110); plt.close(fig)
w = (x >= 60) & (x <= 100)
print("voellmy: <h_t> = %.4f m (ana %.4f, err %+.2f%%), CV = %.4f, C = %.3f" % (ht[w].mean(), HANA, 100 * (ht[w].mean() / HANA - 1), ht[w].std() / ht[w].mean(), np.nanmean(C[w])))

# ---- 構成 2 ----
NX2, NY2, DX2, XB = 60, 20, 1.0, 30.0
st = load_state("save_ty", NX2, NY2)
x2 = (np.arange(NX2) + 0.5) * DX2
z0 = np.tile(np.where(x2 < XB, 0.4 * (XB - x2), 0.0), (NY2, 1))
dz = st["z"] - z0
db = np.loadtxt("dbinit.txt")
fig, axes = plt.subplots(1, 3, figsize=(14, 3.6))
for ax, a, title, cmap, kw in [(axes[0], np.where(db > 0, db, np.nan), "崩壊深 D (m)(t = 0 で瞬時流動化)", "Oranges", {}),
                               (axes[1], dz, "地形変化 z − z₀ (m)(t = 90 s)", "RdBu_r", {"vmin": -2, "vmax": 2}),
                               (axes[2], np.where(st["hs"] > 1e-4, st["hs"], np.nan), "残存する流動中の土砂 hs (m)", "Reds", {})]:
    ax.imshow(np.tile(z0[0], (NY2, 1)), origin="lower", extent=[0, 60, 0, 20], cmap="Greys", alpha=0.25)
    im = ax.imshow(a, origin="lower", extent=[0, 60, 0, 20], cmap=cmap, **kw)
    ax.axvline(XB, color="k", lw=0.6, ls=":")
    ax.set_title(title, fontsize=9); ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
    fig.colorbar(im, ax=ax, shrink=0.8)
fig.suptitle("τ_y ランアウト(slope_break: tanθ = 0.4 の斜面 → x = 30 m から平坦。f_dbres = 5、τ_y = 4000 Pa)", fontsize=10)
fig.tight_layout(); fig.savefig("figs/tauy.png", dpi=110); plt.close(fig)
flat = dz[:, x2 >= XB]
print("tauy: release min dz = %.3f m, flat max dz = %.3f m, remaining hs/released = %.4f" % (dz.min(), flat.max(), st["hs"].sum() / ((1 - 0.4) * db.sum())))
