#!/usr/bin/env python3
"""V 字流域の結果の図 figs/*.png(事前に make run で全ケースを計算しておく。ないケースは飛ばす)。

  python3 plot_results.py        日本語 → figs/
  python3 plot_results.py en     英語   → en/figs/

  hydrographs.png  出口と斜面の脚の流量: 8 近傍の 20・10・5 m と理論解(向き 0° と 45°)
  fournb.png       4 近傍(p_diagratio = 0)の 20・10・5 m と理論解(0° と 45°)
  goveq.png        基礎式の比較(10 m): 力学波・拡散波・運動波と理論解
  maps.png         60 分の水深: 45° の 20 m の出口付近のセル(8 近傍と 4 近傍)と、水路の軸に沿う縦断(20・10・5 m)
  depths.png       出口の水路と斜面の脚の水深の時系列(8 近傍)と理論の等流水深
数値の表は check.py が出す。
"""
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
COL = {20.0: "#c0392b", 10.0: "#2b8a3e", 5.0: "#1f5f8b"}
LS = {20.0: "-.", 10.0: "--", 5.0: "-"}
TH_T, TH_QH, TH_Q = C.theory()


def case(name):
    return C.load_case(name)


def theory_line(ax, which="out", every=3, label=True):
    q = TH_Q if which == "out" else TH_QH
    ax.plot(TH_T[::every], q[::every], "o", ms=3.5, mfc="none", mec="k", mew=0.8,
            label=T("理論解(運動学的波)", "theory (kinematic wave)") if label else None)


def fig_hydrographs():
    fig, axes = plt.subplots(2, 2, figsize=(12, 7.5), sharex=True)
    for col, th in enumerate((0.0, 45.0)):
        ax, axh = axes[0, col], axes[1, col]
        theory_line(ax, "out")
        theory_line(axh, "hill")
        for dx in (20.0, 10.0, 5.0):
            c = case(M.case_name(dx, th))
            if c is None:
                continue
            ax.plot(c["t"], c["q"], color=COL[dx], ls=LS[dx], lw=1.4, label=f"Δx = {dx:g} m")
            axh.plot(c["t"], c["qh"], color=COL[dx], ls=LS[dx], lw=1.4, label=f"Δx = {dx:g} m")
        ax.set_title(T(f"向き {th:g}°: 出口の流量(8 近傍)", f"Orientation {th:g}°: outlet discharge (8-neighbour)"), fontsize=10)
        axh.set_title(T(f"向き {th:g}°: 左岸側の斜面の脚から水路へ", f"Orientation {th:g}°: left hillslope foot into the channel"), fontsize=10)
        for a in (ax, axh):
            a.axvspan(0, M.T_RAIN, color="#9ecae1", alpha=0.25)
            a.grid(alpha=0.3)
            a.legend(fontsize=8)
        ax.set_ylim(0, 5.5)
        axh.set_ylim(0, 2.7)
        axh.set_xlabel(T("時間 (分)", "time (min)"))
    axes[0, 0].set_ylabel(T("流量 (m³/s)", "discharge (m³/s)"))
    axes[1, 0].set_ylabel(T("流量 (m³/s)", "discharge (m³/s)"))
    axes[0, 0].set_xlim(0, 180)
    fig.suptitle(T("V 字流域の降雨流出(10.8 mm/h × 90 分)。ENC の 8 近傍(既定)と運動学的波の理論解",
                   "Rainfall runoff of the V-shaped catchment (10.8 mm/h × 90 min): ENC 8-neighbour (default) vs kinematic-wave theory"), fontsize=11)
    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/hydrographs.png", dpi=110)
    plt.close(fig)


def fig_fournb():
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4), sharey=True)
    for ax, th in zip(axes, (0.0, 45.0)):
        theory_line(ax, "out")
        ref = case(M.case_name(10.0, th))
        if ref is not None:
            ax.plot(ref["t"], ref["q"], color="0.55", lw=1.0, label=T("8 近傍 10 m(参考)", "8-neighbour 10 m (reference)"))
        for dx in (20.0, 10.0, 5.0):
            c = case(M.case_name(dx, th, "_4nb"))
            if c is None:
                continue
            ax.plot(c["t"], c["q"], color=COL[dx], ls=LS[dx], lw=1.6, label=T(f"4 近傍 Δx = {dx:g} m", f"4-neighbour Δx = {dx:g} m"))
        ax.axvspan(0, M.T_RAIN, color="#9ecae1", alpha=0.25)
        ax.set_title(T(f"向き {th:g}°: 4 近傍(p_diagratio = 0)", f"Orientation {th:g}°: 4-neighbour (p_diagratio = 0)"), fontsize=10)
        ax.set_xlabel(T("時間 (分)", "time (min)"))
        ax.set_xlim(0, 180)
        ax.set_ylim(-0.1, 5.5)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    axes[0].set_ylabel(T("出口の流量 (m³/s)", "outlet discharge (m³/s)"))
    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/fournb.png", dpi=110)
    plt.close(fig)


def fig_goveq():
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4), sharey=True)
    lab = {"": T("力学波(既定)", "dynamic wave (default)"), "_dif": T("拡散波(移流項なし)", "diffusive wave (no advection)"),
           "_kin": T("運動波(圧力項もなし)", "kinematic wave (no pressure term)")}
    col = {"": "#1f5f8b", "_dif": "#d08c00", "_kin": "#7b2d8e"}
    for ax, th in zip(axes, (0.0, 45.0)):
        theory_line(ax, "out")
        for suf in ("", "_dif", "_kin"):
            c = case(M.case_name(10.0, th, suf))
            if c is None:
                continue
            ax.plot(c["t"], c["q"], color=col[suf], lw=1.4, ls="-" if suf == "" else "--", label=lab[suf])
        ax.axvspan(0, M.T_RAIN, color="#9ecae1", alpha=0.25)
        ax.set_title(T(f"向き {th:g}°、Δx = 10 m: 基礎式の比較", f"Orientation {th:g}°, Δx = 10 m: governing equations"), fontsize=10)
        ax.set_xlabel(T("時間 (分)", "time (min)"))
        ax.set_xlim(0, 180)
        ax.set_ylim(0, 5.5)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
        # 立ち上がりの拡大
        ins = ax.inset_axes([0.55, 0.12, 0.42, 0.42])
        theory_line(ins, "out", every=1, label=False)
        for suf in ("", "_dif", "_kin"):
            c = case(M.case_name(10.0, th, suf))
            if c is not None:
                ins.plot(c["t"], c["q"], color=col[suf], lw=1.2, ls="-" if suf == "" else "--")
        ins.set_xlim(25, 65)
        ins.set_ylim(0.5, 5.0)
        ins.tick_params(labelsize=7)
        ins.grid(alpha=0.3)
    axes[0].set_ylabel(T("出口の流量 (m³/s)", "outlet discharge (m³/s)"))
    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/goveq.png", dpi=110)
    plt.close(fig)


def fig_maps():
    """60 分(H0002)の水深。上: 45° の 20 m の出口付近のセル(8 近傍と 4 近傍。流域の座標 s, n に戻して描く)、
    下: 水路の軸に沿う水深の縦断(45° の 20・10・5 m、8 近傍と 4 近傍)と理論の等流水深 h(s) = h_e (s/L)^0.6。"""
    fig, axes = plt.subplots(2, 2, figsize=(12, 9.5))
    from matplotlib.patches import Polygon
    for col, suf in enumerate(("", "_4nb")):
        ax = axes[0, col]
        dx = 20.0
        name = M.case_name(dx, 45.0, suf)
        path = f"result_{name}/H0002.txt"
        if not os.path.isfile(path):
            ax.set_axis_off()
            continue
        H = np.loadtxt(path)[::-1]
        nx, ny, ox, oy, c, sn, _ = M.frame(dx, 45.0)
        _, kind, s, n = M.grid(dx, 45.0)
        sel = (kind > 0) & (s > M.L - 320) & (s < M.L + 140) & (np.abs(n) < 220)
        jj, ii = np.nonzero(sel)
        cmap = plt.get_cmap("viridis")
        for i, j in zip(ii, jj):
            # セルの 4 隅を (s, n) へ
            xs = np.array([i, i + 1, i + 1, i]) * dx - ox
            ys = np.array([j, j, j + 1, j + 1]) * dx - oy
            ss = xs * c - ys * sn
            nn = xs * sn + ys * c
            if kind[j, i] == 4:
                fc = "#1f3f8b"
            elif H[j, i] < 1e-3:
                fc = "#f3efe6"
            else:
                fc = cmap(np.clip(H[j, i] / 1.0, 0, 1))
            ax.add_patch(Polygon(np.c_[ss, nn], closed=True, facecolor=fc, edgecolor="0.6", lw=0.3))
        ax.plot([M.L, M.L], [-220, 220], "k--", lw=0.8)
        ax.axhline(M.W / 2, color="#1f3f8b", lw=0.6)
        ax.axhline(-M.W / 2, color="#1f3f8b", lw=0.6)
        ax.set_xlim(M.L - 320, M.L + 140)
        ax.set_ylim(-220, 220)
        ax.set_aspect("equal")
        ax.set_xlabel("s (m)")
        ax.set_ylabel("n (m)")
        hmax = float(np.nanmax(np.where(kind == 2, H, np.nan)))
        ax.set_title(T(f"Δx = 20 m、45°、{'8 近傍' if suf == '' else '4 近傍'}: 出口付近の 60 分の水深(水路の最大 {hmax:.2f} m)",
                       f"Δx = 20 m, 45°, {'8-neighbour' if suf == '' else '4-neighbour'}: depth near the outlet at 60 min (max in channel {hmax:.2f} m)"), fontsize=9)
    sm = plt.cm.ScalarMappable(cmap="viridis", norm=plt.Normalize(0, 1.0))
    fig.colorbar(sm, ax=axes[0, :].tolist(), fraction=0.02, pad=0.01).set_label(T("水深 (m)。白 = 1 mm 未満、紺 = 海", "depth (m); white < 1 mm, navy = sea"))
    # 下段: 水路の軸に沿う水深
    he = C.H_OUT_TH
    for col, suf in enumerate(("", "_4nb")):
        ax = axes[1, col]
        ss_ = np.linspace(1, M.L, 200)
        ax.plot(ss_, he * (ss_ / M.L) ** 0.6, "k", lw=1.2, label=T("理論の等流水深 h_e (s/L)^0.6", "theory, uniform depth h_e (s/L)^0.6"))
        for dx in (20.0, 10.0, 5.0):
            name = M.case_name(dx, 45.0, suf)
            path = f"result_{name}/H0002.txt"
            if not os.path.isfile(path):
                continue
            H = np.loadtxt(path)[::-1]
            _, kind, s, n = M.grid(dx, 45.0)
            axis = (kind == 2) & (np.abs(n) < 1e-6)
            k = np.argsort(s[axis])
            ax.plot(s[axis][k], H[axis][k], color=COL[dx], ls=LS[dx], lw=1.4, label=f"Δx = {dx:g} m")
        ax.set_xlabel("s (m)")
        ax.set_ylabel(T("水路の軸のセルの水深 (m)", "depth in the channel-axis cells (m)"))
        ax.set_title(T(f"45°、{'8 近傍' if suf == '' else '4 近傍'}: 60 分の水路の縦断", f"45°, {'8-neighbour' if suf == '' else '4-neighbour'}: along the channel at 60 min"), fontsize=9)
        ax.set_xlim(0, M.L)
        ax.set_ylim(0, 1.0)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    fig.savefig(f"{FIGDIR}/maps.png", dpi=110)
    plt.close(fig)


def fig_depths():
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    for th in (0.0, 45.0):
        for dx in (20.0, 10.0, 5.0):
            c = case(M.case_name(dx, th))
            if c is None:
                continue
            lab = f"Δx = {dx:g} m, {th:g}°"
            axes[0].plot(c["p1"][:, 1], c["p1"][:, 3], color=COL[dx], ls="-" if th == 0 else ":", lw=1.3, label=lab)
            axes[1].plot(c["p2"][:, 1], c["p2"][:, 3] * 1000, color=COL[dx], ls="-" if th == 0 else ":", lw=1.3, label=lab)
    axes[0].axhline(C.H_OUT_TH, color="k", lw=1.0, label=T("理論の等流水深 0.443 m(広幅)", "theory 0.443 m (wide channel)"))
    axes[1].axhline(C.H_FOOT_TH * 1000, color="k", lw=1.0, label=T("理論の等流水深 5.3 mm", "theory 5.3 mm"))
    axes[0].set_title(T("出口の水路のセルの水深(P1)", "Depth in the outlet channel cell (P1)"), fontsize=10)
    axes[1].set_title(T("水路に接する斜面のセルの水深(P2、s = 500 m)", "Depth in the hillslope cell next to the channel (P2, s = 500 m)"), fontsize=10)
    axes[0].set_ylabel(T("水深 (m)", "depth (m)"))
    axes[1].set_ylabel(T("水深 (mm)", "depth (mm)"))
    for ax in axes:
        ax.axvspan(0, M.T_RAIN, color="#9ecae1", alpha=0.25)
        ax.set_xlabel(T("時間 (分)", "time (min)"))
        ax.set_xlim(0, 180)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/depths.png", dpi=110)
    plt.close(fig)


def main():
    fig_hydrographs()
    fig_fournb()
    fig_goveq()
    fig_maps()
    fig_depths()
    print(f"{FIGDIR}/hydrographs.png fournb.png goveq.png maps.png depths.png")


if __name__ == "__main__":
    main()
