#!/usr/bin/env python3
"""test/wqstruct の図を figs/layout.png に描く(事前に ./Run.sh を実行しておく)。

  python3 Fig.py        # 日本語版 → figs/
  python3 Fig.py en     # 英語版   → en/figs/

(a) 16 の区画の名前・初期水深と、構造物・取水の向き(矢印。域外は格子の外向き)
(b) 2 時間後の地表の濃度 result/C0002.bil(水深 1 mm 以下のセルと壁は灰色)。
    濃度 1 mg/L からのずれを ±1e-4 の発散色で示す(検定の許容は ±1e-3)
"""
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)

N = 17
INK, MUTED, WALL = "#0b0b0b", "#52514e", "#b9b8b3"
PUMP, CULV, DIV = "#2a78d6", "#eb6834", "#1baf7a"     # ポンプ / カルバート / 分水・吸い込み
NAMES = [["A", "C", "D", "F"], ["H", "I", "E", "G"], ["J", "L", "N", "O"], ["B", "K", "M", "Q"]]
H0 = [[1.0, 1.0, 1.5, 0.5], [1.0, 1.0, 0.5, 1.5], [1.0, 1.5, 1.0, 0.0], [1.0, 1.0, 0.5, 1.0]]

# 構造物(ラベル, 種類の色, 経路の点列 (i, j), 域外か)。域外への取水は壁までの短い矢印 +
# 丸印、P1(長い圧送)は格子の外側を回す
ARROWS = [
    ("P1", PUMP, [(2.2, 3.0), (-0.4, 3.0), (-0.4, 15.5), (2.2, 15.5)], False),
    ("P2", PUMP, [(7.0, 3.0), (7.0, 1.0)], True),
    ("P3", PUMP, [(3.4, 11.4), (6.6, 14.6)], False),
    ("P4", PUMP, [(15.0, 14.6), (15.0, 11.4)], False),
    ("K1", CULV, [(11.0, 3.6), (11.0, 6.4)], False),
    ("K2", CULV, [(15.0, 6.4), (15.0, 3.6)], False),     # 逆流: 下流側 G → 上流側 F
    ("V1", DIV, [(3.0, 7.0), (1.0, 7.0)], True),
    ("V2", DIV, [(7.4, 11.4), (10.6, 14.6)], False),
    ("S1", DIV, [(7.0, 7.0), (7.0, 5.0)], True),
]
LABEL_AT = {"P1": (-0.4, 9.0), "P2": (6.35, 2.0), "P3": (5.0, 13.0), "P4": (15.35, 13.0),
            "K1": (11.35, 5.0), "K2": (15.35, 5.0), "V1": (2.75, 6.3), "V2": (9.0, 13.0),
            "S1": (6.35, 6.0)}


def draw_layout(ax):
    ax.set_xlim(-1.4, N + 0.9)
    ax.set_ylim(N + 0.9, -0.4)
    ax.set_aspect("equal")
    ax.axis("off")
    # 格子(壁)の外枠
    ax.add_patch(plt.Rectangle((0.5, 0.5), N, N, facecolor="#f7f6f3", edgecolor=WALL, lw=1.5))
    for r in range(4):
        for c in range(4):
            x0, y0 = 4 * c + 1.5, 4 * r + 1.5
            nm = NAMES[r][c]
            face = "#e6e5e0" if nm == "N" else ("#ffffff" if H0[r][c] == 0 else "#e3eefb")
            ax.add_patch(plt.Rectangle((x0, y0), 3, 3, facecolor=face, edgecolor=WALL, lw=1.0))
            ax.text(x0 + 2.85, y0 + 0.15, nm, ha="right", va="top", fontsize=10, color=INK)
            ax.text(x0 + 0.12, y0 + 2.9, f"{H0[r][c]:.1f} m", ha="left", va="bottom",
                    fontsize=7.5, color=MUTED)
    for lab, col, pts, out in ARROWS:
        xs, ys = zip(*pts)
        if len(pts) > 2:
            ax.plot(xs[:-1], ys[:-1], color=col, lw=2.0, solid_capstyle="round", zorder=4)
        ax.annotate("", xy=pts[-1], xytext=pts[-2], zorder=5,
                    arrowprops=dict(arrowstyle="-|>", color=col, lw=2.0, shrinkA=0, shrinkB=0,
                                    mutation_scale=12))
        if out:
            ax.plot([pts[-1][0]], [pts[-1][1]], "o", ms=8, mfc="white", mec=col, mew=1.8, zorder=6)
        lx, ly = LABEL_AT[lab]
        ax.text(lx, ly, lab, fontsize=8.5, color=INK, ha="center", va="center", zorder=7,
                bbox=dict(boxstyle="round,pad=0.15", facecolor="white", edgecolor=col, lw=0.8))
    # 凡例(種類。矢印にはすべてラベルを付けるので色だけに頼らない)
    hs = [plt.Line2D([], [], color=PUMP, lw=2.0), plt.Line2D([], [], color=CULV, lw=2.0),
          plt.Line2D([], [], color=DIV, lw=2.0),
          plt.Line2D([], [], color=MUTED, lw=0, marker="o", ms=7, mfc="white", mec=MUTED, mew=1.5)]
    ax.legend(hs, [T("ポンプ", "pump"), T("カルバート", "culvert"),
                   T("分水・吸い込み", "diversion / sink"), T("域外へ", "out of the domain")],
              loc="upper center", bbox_to_anchor=(0.5, 0.02), ncol=4, frameon=False, fontsize=8,
              handlelength=1.8, columnspacing=1.2)
    ax.set_title(T("(a) 区画(初期水深)と構造物・取水", "(a) Compartments (initial depth) and withdrawals"),
                 fontsize=10, loc="left")


def draw_conc(ax, fig):
    c = np.fromfile("result/C0002.bil", "<f4").reshape(N, N).astype(float)
    h = np.fromfile("result/H0002.bil", "<f4").reshape(N, N).astype(float)
    wet = h > 1e-3
    dev = np.where(wet, c - 1.0, np.nan)
    cmap = LinearSegmentedColormap.from_list("div", ["#2a78d6", "#f0efec", "#e34948"])
    cmap.set_bad(WALL)
    lim = 1e-4
    im = ax.imshow(dev, cmap=cmap, vmin=-lim, vmax=lim, extent=(0.5, N + 0.5, N + 0.5, 0.5),
                   interpolation="nearest")
    ax.set_aspect("equal")
    ax.set_xticks([1, 5, 9, 13, 17])
    ax.set_yticks([1, 5, 9, 13, 17])
    ax.tick_params(labelsize=7.5, colors=MUTED)
    for s in ax.spines.values():
        s.set_color(WALL)
    ax.set_xlabel("i", fontsize=8, color=MUTED)
    ax.set_ylabel("j", fontsize=8, color=MUTED)
    for r in range(4):
        for cc in range(4):
            ax.text(4 * cc + 1.75, 4 * r + 1.85, NAMES[r][cc], fontsize=8, color=INK,
                    ha="left", va="top")
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03, ticks=[-1e-4, -5e-5, 0.0, 5e-5, 1e-4])
    cb.ax.set_yticklabels(["−1e-4", "−5e-5", "0", "+5e-5", "+1e-4"])
    cb.ax.tick_params(labelsize=7.5)
    cb.set_label(T("濃度 − 1 (mg/L)", "concentration − 1 (mg/L)"), fontsize=8)
    lo, hi = float(np.nanmin(dev)), float(np.nanmax(dev))
    ax.set_title(T("(b) 2 時間後の地表の濃度(1 からのずれ)", "(b) Surface concentration after 2 h (offset from 1)"),
                 fontsize=10, loc="left")
    ax.text(0.5, N + 0.5 + 1.6,
            T(f"水のあるセル {int(wet.sum())}: {lo:+.1e} 〜 {hi:+.1e}(検定の許容 ±1e-3)。灰色 = 壁・乾いたセル",
              f"{int(wet.sum())} wet cells: {lo:+.1e} to {hi:+.1e} (check tolerance ±1e-3). Gray = walls and dry cells"),
            fontsize=7.5, color=MUTED, ha="left", va="top")


def main():
    fig, axs = plt.subplots(1, 2, figsize=(11.0, 5.6), gridspec_kw=dict(width_ratios=[1.05, 1.0]))
    draw_layout(axs[0])
    draw_conc(axs[1], fig)
    fig.subplots_adjust(left=0.02, right=0.92, top=0.92, bottom=0.12, wspace=0.14)
    out = os.path.join(FIGDIR, "layout.png")
    fig.savefig(out, dpi=150)
    print("wrote", out)


if __name__ == "__main__":
    main()
