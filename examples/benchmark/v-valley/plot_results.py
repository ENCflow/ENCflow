#!/usr/bin/env python3
"""V 字谷の結果の図 figs/*.png(事前に make run で全ケースを計算しておく。ないケースは飛ばす)。

  python3 plot_results.py        日本語 → figs/
  python3 plot_results.py en     英語   → en/figs/

  slopes.png   斜面の勾配 S_S = 0.01〜0.04(格子 10 m)の下流端の流量: 0° の 8 近傍(基準)、45° の 8 近傍、45° の 4 近傍
  grids.png    格子 20・10・5 m(S_S = 0.03)の下流端の流量: 45° の 8 近傍と 4 近傍(0° の基準を重ねる)
  maps.png     60 分の水深: 45°・20 m の谷底付近のセル(8 近傍と 4 近傍)と、谷底の軸に沿う水深(20・10・5 m)
数値の表は check.py が出す。
"""
import math
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import make_inputs as M
import check as C

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)
COL_S = {0.01: "#1f5f8b", 0.02: "#2b8a3e", 0.03: "#d08c00", 0.04: "#c0392b"}
COL_D = {20.0: "#c0392b", 10.0: "#2b8a3e", 5.0: "#1f5f8b"}
LS_D = {20.0: "-.", 10.0: "--", 5.0: "-"}


def case(name):
    return C.load_case(name)


def fig_slopes():
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.4), sharey=True)
    titles = (T("0°、8 近傍(基準)", "0°, 8-neighbour (reference)"), T("45°、8 近傍", "45°, 8-neighbour"),
              T("45°、4 近傍(p_diagratio = 0)", "45°, 4-neighbour (p_diagratio = 0)"))
    for ax, (th, suf), ttl in zip(axes, ((0.0, ""), (45.0, ""), (45.0, "_4nb")), titles):
        for ss in M.S_S_LIST:
            c = case(M.case_name(ss, 10.0, th, suf))
            if c is None:
                continue
            ax.plot(c["t"], c["q"], color=COL_S[ss], lw=1.5, label=f"S_S = {ss}")
            if th == 45.0:
                r = case(M.case_name(ss, 10.0, 0.0))
                if r is not None:
                    ax.plot(r["t"], r["q"], color=COL_S[ss], lw=0.8, ls=":")
        ax.axvspan(0, M.T_RAIN, color="#9ecae1", alpha=0.25)
        ax.set_title(T(f"Δx = 10 m、{ttl}", f"Δx = 10 m, {ttl}"), fontsize=10)
        ax.set_xlabel(T("時間 (分)", "time (min)"))
        ax.set_xlim(0, 180)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    axes[0].set_ylabel(T("下流端の流量 (m³/s)", "outlet discharge (m³/s)"))
    axes[0].set_ylim(0, 4.5)
    fig.suptitle(T("斜面の勾配 S_S を変えた下流端の流量(谷の勾配 S_V = 0.02)。点線 = 同じ S_S の 0° の 8 近傍",
                   "Outlet discharge for hillslope slopes S_S (valley slope S_V = 0.02). Dotted = 0° 8-neighbour with the same S_S"), fontsize=11)
    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/slopes.png", dpi=110)
    plt.close(fig)


def fig_grids():
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4), sharey=True)
    for ax, suf, ttl in zip(axes, ("", "_4nb"), (T("45°、8 近傍", "45°, 8-neighbour"), T("45°、4 近傍", "45°, 4-neighbour"))):
        for dx in (20.0, 10.0, 5.0):
            c = case(M.case_name(M.S_S_BASE, dx, 45.0, suf))
            if c is None:
                continue
            ax.plot(c["t"], c["q"], color=COL_D[dx], ls=LS_D[dx], lw=1.6, label=f"Δx = {dx:g} m")
            r = case(M.case_name(M.S_S_BASE, dx, 0.0))
            if r is not None:
                ax.plot(r["t"], r["q"], color=COL_D[dx], lw=0.8, ls=":")
        ax.axvspan(0, M.T_RAIN, color="#9ecae1", alpha=0.25)
        ax.set_title(T(f"S_S = {M.S_S_BASE}、{ttl}(点線 = 同じ格子の 0°)", f"S_S = {M.S_S_BASE}, {ttl} (dotted = 0° on the same grid)"), fontsize=10)
        ax.set_xlabel(T("時間 (分)", "time (min)"))
        ax.set_xlim(0, 180)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    axes[0].set_ylabel(T("下流端の流量 (m³/s)", "outlet discharge (m³/s)"))
    axes[0].set_ylim(0, 4.0)
    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/grids.png", dpi=110)
    plt.close(fig)


def fig_maps():
    """60 分(H0002)の水深。上: 45°・20 m の谷底付近のセル(8 近傍と 4 近傍。谷の座標 s, n に戻して描く)、
    下: 谷底の軸のセルの列に沿う水深(45° の 20・10・5 m、8 近傍と 4 近傍)。"""
    from matplotlib.patches import Polygon
    fig, axes = plt.subplots(2, 2, figsize=(12, 9.0))
    ss = M.S_S_BASE
    hp20 = math.sqrt(2) / 2 * (ss - M.S_V) * 20.0
    for col, suf in enumerate(("", "_4nb")):
        ax = axes[0, col]
        dx = 20.0
        name = M.case_name(ss, dx, 45.0, suf)
        path = f"result_{name}/H0002.txt"
        if not os.path.isfile(path):
            ax.set_axis_off()
            continue
        H = np.loadtxt(path)[::-1]
        nx, ny, ox, oy, c, sn, _ = M.frame(dx, 45.0)
        _, kind, s, n = M.grid(ss, dx, 45.0)
        sel = (kind == 1) & (s > 380) & (s < 620) & (np.abs(n) < 130)
        jj, ii = np.nonzero(sel)
        cmap = plt.get_cmap("viridis")
        vmax = 0.3
        for i, j in zip(ii, jj):
            xs = np.array([i, i + 1, i + 1, i]) * dx - ox
            ys = np.array([j, j, j + 1, j + 1]) * dx - oy
            s4 = xs * c - ys * sn
            n4 = xs * sn + ys * c
            fc = "#f3efe6" if H[j, i] < 1e-3 else cmap(np.clip(H[j, i] / vmax, 0, 1))
            ax.add_patch(Polygon(np.c_[s4, n4], closed=True, facecolor=fc, edgecolor="0.6", lw=0.3))
            if abs(n[j, i]) < 1e-6:
                ax.text(s[j, i], n[j, i], f"{H[j, i]:.2f}", ha="center", va="center", fontsize=6.5, color="w")
        ax.axhline(0, color="k", lw=0.6, ls="--")
        ax.set_xlim(380, 620)
        ax.set_ylim(-130, 130)
        ax.set_aspect("equal")
        ax.set_xlabel("s (m)")
        ax.set_ylabel("n (m)")
        ax.set_title(T(f"Δx = 20 m、45°、{'8 近傍' if suf == '' else '4 近傍'}: 谷底付近の 60 分の水深(数字 = 軸のセル)",
                       f"Δx = 20 m, 45°, {'8-neighbour' if suf == '' else '4-neighbour'}: depth near the floor at 60 min (numbers = axis cells)"), fontsize=9)
    sm = plt.cm.ScalarMappable(cmap="viridis", norm=plt.Normalize(0, 0.3))
    fig.colorbar(sm, ax=axes[0, :].tolist(), fraction=0.02, pad=0.01).set_label(T("水深 (m)。白 = 1 mm 未満", "depth (m); white < 1 mm"))
    for col, suf in enumerate(("", "_4nb")):
        ax = axes[1, col]
        for dx in (20.0, 10.0, 5.0):
            name = M.case_name(ss, dx, 45.0, suf)
            path = f"result_{name}/H0002.txt"
            if not os.path.isfile(path):
                continue
            H = np.loadtxt(path)[::-1]
            _, kind, s, n = M.grid(ss, dx, 45.0)
            axis = (kind == 1) & (np.abs(n) < 1e-6)
            k = np.argsort(s[axis])
            ax.plot(s[axis][k], H[axis][k], color=COL_D[dx], ls=LS_D[dx], lw=1.4, label=f"Δx = {dx:g} m")
            if suf == "_4nb" and ss > M.S_V:
                ax.axhline(math.sqrt(2) / 2 * (ss - M.S_V) * dx, color=COL_D[dx], lw=0.7, ls=":")
        ax.set_xlabel("s (m)")
        ax.set_ylabel(T("谷底の軸のセルの水深 (m)", "depth in the floor-axis cells (m)"))
        ax.set_title(T(f"45°、{'8 近傍' if suf == '' else '4 近傍(点線 = 窪地の深さ H_p)'}: 60 分の谷底の軸に沿う水深",
                       f"45°, {'8-neighbour' if suf == '' else '4-neighbour (dotted = depression depth H_p)'}: depth along the floor axis at 60 min"), fontsize=9)
        ax.set_xlim(0, M.L)
        ax.set_ylim(0, 0.35)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    fig.savefig(f"{FIGDIR}/maps.png", dpi=110)
    plt.close(fig)


def main():
    fig_slopes()
    fig_grids()
    fig_maps()
    print(f"{FIGDIR}/slopes.png grids.png maps.png")


if __name__ == "__main__":
    main()
