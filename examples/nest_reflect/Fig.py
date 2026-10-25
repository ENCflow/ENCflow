#!/usr/bin/env python3
"""nest_reflect: README 用の図を figs/ に描く(各ランの result_*/E00NN.txt を読む)

  使い方: README の各ランと python3 make_inputs.py の後に ./Fig.py
  figs/snapshots.png    t = 4 s の水位(細格子基準・粗格子単独・比 3 ネストのルート)と誤差。子の足元を枠で示す
  figs/error_time.png   子の足元の内側/外側の RMS 誤差の時間変化(r_t = 1 と r_t = r の各ラン)
  figs/oneway_edge.png  一方向の子の誤差分布(t = 2 s): 帯 Dirichlet(ow2)と Flather 放射(ow3)
  figs/nh_profile.png   非静水圧(σ = 2 m)の中心線の水位と子の誤差分布(親の φ の帯 nh1 と静水圧の帯 nh0)
  python3 Fig.py en で英語ラベル版を en/figs/ に描く。
計算本体の外(方針 10)。numpy + matplotlib。存在しないランは飛ばす。
"""
import os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
EN = "en" in sys.argv[1:]
def T(ja, en): return en if EN else ja
FIGDIR = "en/figs" if EN else "figs"

plt.rcParams.update({"font.family": ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"], "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": "#e3e2dd", "grid.linewidth": 0.6,
                     "lines.linewidth": 1.6})
C = {"fine": "#6b6a66", "coarse": "#eb6834", "r3": "#2a78d6", "r5": "#8e6bd6", "ow2": "#eb6834", "ow3": "#2a78d6",
     "nh1": "#2a78d6", "nh0": "#eb6834", "coarse_nh": "#9a9890"}
I0, NF, H0, NP, DX = 160, 67, 1.0, 385, 100.0 / 385        # 子の足元(親セル)、親の格子数と刻み
os.makedirs(FIGDIR, exist_ok=True)

def have(d, n): return os.path.exists(os.path.join(d, "E%04d.txt" % n))
def load(d, n): return np.loadtxt(os.path.join(d, "E%04d.txt" % n)) - H0        # η(行 j = 北から、列 i)
def to_parent(e, r):
    n = e.shape[0] // r
    return e.reshape(n, r, n, r).mean(axis=(1, 3))
def fine(n, nh=False): return to_parent(load("result_fine_nh" if nh else "result_fine", n), 3)
def box(ax, color="k"):                                   # 子の足元(親セル I0..I0+NF-1)の枠(画像座標 = 親セル。原点は北西)
    ax.add_patch(Rectangle((I0 - 1.5, I0 - 1.5), NF, NF, fill=False, ec=color, lw=1.2, ls="--"))
inside = np.zeros((NP, NP), bool); inside[I0 - 1:I0 - 1 + NF, I0 - 1:I0 - 1 + NF] = True
ext = (0.5, NP + 0.5, NP + 0.5, 0.5)                      # imshow の extent(親セル番号。上が北)

def fig_snapshots(out, n=4):
    if not (have("result_fine", n) and have("result_coarse", n) and have("result_root_r3", n)): return
    ef = fine(n); ec = load("result_coarse", n); er = load("result_root_r3", n)
    fig, axs = plt.subplots(2, 3, figsize=(10.5, 6.8), layout="constrained")
    vm = 0.03
    for ax, e, t in zip(axs[0], (ef, ec, er), (T("細格子(基準。3×3 平均)", "fine grid (reference; 3×3 mean)"), T("粗格子単独(385²)", "coarse grid alone (385²)"), T("比 3 双方向ネストのルート", "root of ratio-3 two-way nest"))):
        im = ax.imshow(e, cmap="RdBu_r", vmin=-vm, vmax=vm, extent=ext, interpolation="nearest")
        ax.set_title(t, fontsize=9.5, loc="left"); box(ax); ax.grid(False)
    fig.colorbar(im, ax=axs[0], fraction=0.025, pad=0.02, label="η (m)")
    dm = 1.0e-3
    if have("result_child_r3", n):
        ax = axs[1][0]
        im0 = ax.imshow(load("result_child_r3", n), cmap="RdBu_r", vmin=-vm, vmax=vm, interpolation="nearest",
                        extent=(I0 - 0.5, I0 + NF - 0.5, I0 + NF - 0.5, I0 - 0.5))
        ax.set_title(T("子格子(201²。足元を拡大)", "child grid (201²; footprint enlarged)"), fontsize=9.5, loc="left"); ax.grid(False)
    else:
        axs[1][0].axis("off")
    for ax, e, t in zip(axs[1][1:], (ec, er), (T("粗格子単独 − 細格子", "coarse grid alone − fine grid"), T("ネストのルート − 細格子", "nested root − fine grid"))):
        im = ax.imshow(e - ef, cmap="PuOr_r", vmin=-dm, vmax=dm, extent=ext, interpolation="nearest")
        ax.set_title(t, fontsize=9.5, loc="left"); box(ax); ax.grid(False)
    fig.colorbar(im, ax=axs[1], fraction=0.025, pad=0.02, label="Δη (m)")
    for ax in axs.flat:
        if ax.axison: ax.set_xlabel(T("i(親セル)", "i (parent cell)")); ax.set_ylabel("j")
    fig.suptitle(T("nest_reflect: ガウス波(a = 0.2 m, σ = 5 m)の t = %d s の水位 η と誤差 η − η_fine(破線 = 子の足元、親セル %d..%d)",
                   "nest_reflect: Gaussian wave (a = 0.2 m, σ = 5 m), water level η at t = %d s and error η − η_fine (dashed = child footprint, parent cells %d..%d)") % (n, I0, I0 + NF - 1), x=0.01, ha="left", fontsize=10)
    fig.savefig(out, dpi=150); plt.close(fig)

def fig_error_time(out):
    runs = [("coarse", T("粗格子単独(dt = 1/60 s)", "coarse grid alone (dt = 1/60 s)"), C["coarse"], "-"),
            ("root_r3", T("比 3 ネストのルート(r_t = 1)", "ratio-3 nested root (r_t = 1)"), C["r3"], "-"),
            ("root_r5", T("比 5 ネストのルート(r_t = 1)", "ratio-5 nested root (r_t = 1)"), C["r5"], "-"),
            ("coarse_dt05", T("粗格子単独(dt = 0.05 s)", "coarse grid alone (dt = 0.05 s)"), C["coarse"], "--"),
            ("root_r3t3", T("比 3・r_t = 3 のルート", "ratio-3 nested root, r_t = 3"), C["r3"], "--"),
            ("root_r3t3_fb3", T("比 3・r_t = 3 + 保存修正", "ratio 3, r_t = 3 + conservation correction"), "#3f7a2a", "--")]
    ts = list(range(1, 11))
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 3.6), sharey=True)
    for name, lab, col, ls in runs:
        d = "result_" + name
        if not all(have(d, n) for n in ts): continue
        ri, ro = [], []
        for n in ts:
            de = load(d, n) - fine(n)
            ri.append(np.sqrt(np.mean(de[inside] ** 2))); ro.append(np.sqrt(np.mean(de[~inside] ** 2)))
        axs[0].plot(ts, ri, ls, color=col, marker="o", ms=4, label=lab); axs[1].plot(ts, ro, ls, color=col, marker="o", ms=4, label=lab)
    axs[0].set_title(T("子の足元の内側(親セル %d..%d)", "inside the child footprint (parent cells %d..%d)") % (I0, I0 + NF - 1), loc="left", fontsize=10)
    axs[1].set_title(T("足元の外側(透過波)", "outside the footprint (transmitted wave)"), loc="left", fontsize=10)
    for ax in axs:
        ax.set_yscale("log"); ax.set_xlabel("t (s)"); ax.set_xlim(0.5, 10.5)
    axs[0].set_ylabel("RMS(η − η_fine) (m)")
    axs[1].axhline(1e-4, color="#bbb", lw=0.8); axs[1].text(0.7, 1.08e-4, T("出力の刻み 1e-4 m", "output step 1e-4 m"), fontsize=8, color="#888", ha="left")
    axs[0].legend(fontsize=8, frameon=False, loc="lower right")
    fig.tight_layout(); fig.savefig(out, dpi=150); plt.close(fig)

def fig_oneway(out, n=2):
    if not (have("result_child_r3t3_ow2", n) and have("result_child_r3t3_ow3", n) and have("result_fine", n)): return
    ef = fine(n)[I0 - 1:I0 - 1 + NF, I0 - 1:I0 - 1 + NF]
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.6))
    dm = 2e-3
    for ax, name, t in zip(axs, ("ow2", "ow3"), (T("帯 Dirichlet(nest_bc = 2)", "Dirichlet band (nest_bc = 2)"), T("Flather 放射(nest_bc = 3、帯なし)", "Flather radiation (nest_bc = 3, no band)"))):
        de = to_parent(load("result_child_r3t3_" + name, n), 3) - ef
        im = ax.imshow(de, cmap="PuOr_r", vmin=-dm, vmax=dm, extent=(I0 - 0.5, I0 + NF - 0.5, I0 + NF - 0.5, I0 - 0.5), interpolation="nearest")
        ax.add_patch(Rectangle((I0 + 1.5, I0 + 1.5), NF - 4, NF - 4, fill=False, ec="k", lw=1.0, ls="--"))
        ax.set_title("%s: max |Δη| = %.1e m(core %.1e)" % (t, np.abs(de).max(), np.abs(de[2:-2, 2:-2]).max()), fontsize=9.5, loc="left")
        ax.set_xlabel(T("i(親セル)", "i (parent cell)")); ax.grid(False)
    axs[0].set_ylabel("j")
    fig.colorbar(im, ax=axs, fraction=0.025, pad=0.02, label="η_child − η_fine (m)")
    fig.suptitle(T("一方向(nest_fb = 0)の子の誤差(t = %d s。子を親格子へ 3×3 平均。破線 = core = 外周 2 親セルを除く)",
                   "one-way (nest_fb = 0) child error (t = %d s; child averaged 3×3 onto the parent grid; dashed = core = excluding the outer 2 parent cells)") % n, x=0.01, ha="left", fontsize=10)
    fig.savefig(out, dpi=150, bbox_inches="tight"); plt.close(fig)

def fig_nh(out, n=4):
    if not all(have(d, n) for d in ("result_fine_nh", "result_coarse_nh", "result_root_r3_nh1", "result_root_r3_nh0", "result_child_r3_nh1", "result_child_r3_nh0")): return
    ef = fine(n, nh=True)
    jc = NP // 2                                              # 中心線(行 193)
    x = (np.arange(NP) + 0.5) * DX
    fig = plt.figure(figsize=(10.5, 7.2), layout="constrained")
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.15])
    ax = fig.add_subplot(gs[0, :])
    ax.plot(x, ef[jc], color=C["fine"], lw=2.2, label=T("細格子 NH(基準)", "fine grid NH (reference)"))
    ax.plot(x, load("result_coarse_nh", n)[jc], color=C["coarse_nh"], ls=":", label=T("粗格子単独 NH", "coarse grid alone NH"))
    ax.plot(x, load("result_root_r3_nh1", n)[jc], color=C["nh1"], label=T("ネストのルート、帯 = 親の φ(nest_nh = 1)", "nested root, band = parent's φ (nest_nh = 1)"))
    ax.plot(x, load("result_root_r3_nh0", n)[jc], color=C["nh0"], ls="--", label=T("ネストのルート、帯 + 余白は静水圧(nest_nh = 0)", "nested root, band + margin hydrostatic (nest_nh = 0)"))
    for xx in ((I0 - 1) * DX, (I0 - 1 + NF) * DX): ax.axvline(xx, color="#bbb", lw=0.8)
    ax.set_xlim(20, 80); ax.set_xlabel(T("x (m)(中心線 j = %d)", "x (m) (centreline j = %d)") % (jc + 1)); ax.set_ylabel("η (m)")
    ax.set_title(T("t = %d s の水位(σ = 2 m、kH ≈ 0.5 の分散波。縦線 = 子の界面)", "water level at t = %d s (σ = 2 m, dispersive wave with kH ≈ 0.5; vertical lines = child interface)") % n, loc="left", fontsize=10)
    ax.legend(fontsize=8.5, frameon=False, ncol=2)
    dm = 2e-3
    for k, (name, t) in enumerate((("nh1", T("子、帯 = 親の φ(nest_nh = 1)", "child, band = parent's φ (nest_nh = 1)")), ("nh0", T("子、帯 + 余白は静水圧(nest_nh = 0)", "child, band + margin hydrostatic (nest_nh = 0)")))):
        axm = fig.add_subplot(gs[1, k])
        de = to_parent(load("result_child_r3_" + name, n), 3) - ef[I0 - 1:I0 - 1 + NF, I0 - 1:I0 - 1 + NF]
        im = axm.imshow(de, cmap="PuOr_r", vmin=-dm, vmax=dm, extent=(I0 - 0.5, I0 + NF - 0.5, I0 + NF - 0.5, I0 - 0.5), interpolation="nearest")
        axm.set_title("%s: RMS %.1e / max %.1e m" % (t, np.sqrt(np.mean(de ** 2)), np.abs(de).max()), fontsize=9.5, loc="left")
        axm.set_xlabel(T("i(親セル)", "i (parent cell)")); axm.grid(False)
        if k == 0: axm.set_ylabel("j")
    fig.colorbar(im, ax=fig.axes[1:], fraction=0.025, pad=0.02, label="η_child − η_fine (m)")
    fig.savefig(out, dpi=150); plt.close(fig)

if __name__ == "__main__":
    fig_snapshots(os.path.join(FIGDIR, "snapshots.png")); fig_error_time(os.path.join(FIGDIR, "error_time.png"))
    fig_oneway(os.path.join(FIGDIR, "oneway_edge.png")); fig_nh(os.path.join(FIGDIR, "nh_profile.png"))
    print("wrote", sorted(os.listdir(FIGDIR)))
