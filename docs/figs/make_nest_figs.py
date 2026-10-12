#!/usr/bin/env python3
"""ネスティングの説明図(docs/users_guide/nest.md、docs/en/users_guide/nest.md 用)を figs/ に描く。

  使い方: python3 docs/figs/make_nest_figs.py [layout|time|bc ...]
  引数なしは従来どおり全3図。layout 指定は配置図だけを日英PNG・SVGで生成。
  nest_layout.png   親子格子の配置(i0, j0・比 r・帯 nb)と親→子・子→親の交換
  nest_time.png     時間進行(親先行・子の r_t サブステップ・帯の時間補間・置換の時機)
  nest_bc.png       親→子の 3 方式(帯 Dirichlet・Flather 放射・スポンジ)と非静水圧の帯の φ
  各図は日本語(<name>.png)と英語(<name>_en.png)の 2 枚を書く。文字は T[lang][key] の辞書で
  切り替え、draw(lang) が 3 図をまとめて描く(guide/fig_*.py と同じ様式)。
計算本体の外(方針 10)。numpy + matplotlib。
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
import numpy as np

plt.rcParams.update({"font.family": ["IPAGothic", "DejaVu Sans"], "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
C_P, C_C, C_B, C_X, C_G = "#6b6a66", "#2a78d6", "#f2b84b", "#eb6834", "#8fbf6a"   # 親・子・帯・強調・置換
HERE = os.path.dirname(os.path.abspath(__file__))

T = {"ja": {
    # ---- time
    "tn": "tⁿ", "tn1": "tⁿ⁺¹ = tⁿ + Δt", "tparent": "親(格子 1)",
    "step1": "① 親が先に 1 歩進む(帯の窓 wc を tⁿ・tⁿ⁺¹ の 2 時刻で保持)",
    "tchild": "子(r_t = 3)", "alpha": "α = {k}/{rt}",
    "step2": "② 子は Δt/r_t を r_t 回。各サブステップの開始時刻で帯 = (1−α)·wc(tⁿ) + α·wc(tⁿ⁺¹)(非静水圧の φ は終了時刻 α + 1/r_t)",
    "tgrand": "孫(r_t = 2)",
    "step3": "③ 子の各サブステップの中で孫が同じ手順を繰り返す(再帰。任意の深さ・一つの親に複数の子)",
    "fb": "④ 子 → 親の置換(nest_fb)\n(tⁿ⁺¹ で子の内部の平均を親へ)",
    "ttitle": "時間進行(親先行・子サブステップ・時間補間・置換。plan §3.4)",
    # ---- bc
    "pside": "親\n側",
    "t1": "(1) nest_bc = 1・2(既定)・4: 境界帯(nb セル)に親の値を置く(Dirichlet)。子の外縁は壁(f_bc_* = 0)のまま",
    "l1a": "帯: 親の η(→h)・u, v・エッジ流量(2・4)\n/ η のみ(1)", "l1b": "子が計算する内部(置換の対象)",
    "n1": "子の擾乱は帯で親の値に上書きされ反射する(双方向なら小さい)",
    "t2": "(2) nest_bc = 3: Flather 放射(帯なし)。親の値を受ける辺を f_bc_* = 2 にする。一方向(nest_fb = 0)向き",
    "l2": "子は境界セルまで自分で計算する(足元の全域が使える)",
    "n2": "境界面: u_n = u_n,e + √(g/h)(η − η_e)   η_e, u_n,e = 親の値(境界セル中心へ補間、時間補間)",
    "n2b": "親の波は入る\n子の擾乱は出る",
    "t3": "(3) nest_bc = 4: 2 + スポンジ(帯の内側 nest_ns セルを親の値へ緩和)。帯の反射が目立つときの選択肢",
    "l3a": "帯(親の値)", "l3b": "スポンジ nest_ns(緩和)", "l3c": "内部",
    "t4": "(4) 非静水圧の子(f_nonhydrostatic = 1、帯あり): 帯のセルは親の φ の既知セル(Dirichlet。nest_nh = 1 既定)、内部が射影の未知数",
    "l4a": "φ_e = 親の φ(サブステップ終了時刻で補間)", "l4b": "子の射影(CG)の未知数。活性集合は帯に接するセルを |φ_e| で種に",
    "n4": "帯〜内部のエッジも補正される(既知セルの φ_e と未知セルの φ の差)。nest_nh = 0 は帯 + 余白 nh_bc_margin を静水圧にする(位相がずれる)",
}, "en": {
    # ---- time
    "tn": "tⁿ", "tn1": "tⁿ⁺¹ = tⁿ + Δt", "tparent": "parent (grid 1)",
    "step1": "① parent steps first (band window wc kept at tⁿ and tⁿ⁺¹)",
    "tchild": "child (r_t = 3)", "alpha": "α = {k}/{rt}",
    "step2": "② the child takes Δt/r_t, r_t times. At each sub-step start: band = (1−α)·wc(tⁿ) + α·wc(tⁿ⁺¹) (non-hydrostatic φ: end time α + 1/r_t)",
    "tgrand": "grandchild (r_t = 2)",
    "step3": "③ inside each child sub-step the grandchild repeats the same procedure (recursive: any depth, several children per parent)",
    "fb": "④ child → parent replacement (nest_fb)\n(mean of the child's interior to the parent at tⁿ⁺¹)",
    "ttitle": "Time stepping (parent first, child sub-steps, time interpolation, replacement; plan §3.4)",
    # ---- bc
    "pside": "parent\nside",
    "t1": "(1) nest_bc = 1, 2 (default), 4: the parent's values are placed in the boundary band (nb cells; Dirichlet).\n     The child's outer edges stay walls (f_bc_* = 0)",
    "l1a": "band: parent η (→h), u, v, edge discharge (2, 4)\n/ η only (1)", "l1b": "interior computed by the child (replaced into the parent)",
    "n1": "the child's disturbances are overwritten by the parent's values in the band and reflect (small in two-way mode)",
    "t2": "(2) nest_bc = 3: Flather radiation (no band). Set the edges that receive the parent's values to f_bc_* = 2.\n     Meant for one-way nests (nest_fb = 0)",
    "l2": "the child computes up to its boundary cells (the whole footprint is usable)",
    "n2": "boundary face: u_n = u_n,e + √(g/h)(η − η_e)   η_e, u_n,e = parent values (interpolated to the boundary-cell centre and in time)",
    "n2b": "parent waves enter\nchild disturbances leave",
    "t3": "(3) nest_bc = 4: 2 + sponge (the nest_ns cells inside the band are relaxed towards the parent's values).\n     An option when reflections at the band are visible",
    "l3a": "band\n(parent values)", "l3b": "sponge nest_ns\n(relaxation)", "l3c": "interior",
    "t4": "(4) non-hydrostatic child (f_nonhydrostatic = 1, with a band): the band cells are known cells of the parent's φ\n     (Dirichlet; nest_nh = 1, default), the interior holds the unknowns of the projection",
    "l4a": "φ_e = parent φ\n(interpolated to the sub-step end time)", "l4b": "unknowns of the child's projection (CG); the active set is seeded\nnext to the band by |φ_e|",
    "n4": "edges between band and interior are corrected too (difference of known φ_e and unknown φ).\nnest_nh = 0 makes band + margin nh_bc_margin hydrostatic (phase shift)",
}}

def out_path(name, lang):
    return os.path.join(HERE, name + ("" if lang == "ja" else "_en") + ".png")

def grid(ax, x0, y0, nx, ny, d, color, lw, z=1):
    for i in range(nx + 1):
        ax.plot([x0 + i * d, x0 + i * d], [y0, y0 + ny * d], color=color, lw=lw, zorder=z)
    for j in range(ny + 1):
        ax.plot([x0, x0 + nx * d], [y0 + j * d, y0 + j * d], color=color, lw=lw, zorder=z)

def arrow(ax, p, q, color, text=None, lw=1.6, dxy=(0, 0), ha="center", fs=9):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=12, color=color, lw=lw, zorder=6))
    if text:
        ax.text((p[0] + q[0]) / 2 + dxy[0], (p[1] + q[1]) / 2 + dxy[1], text, color=color, ha=ha, va="center", fontsize=fs, zorder=7)

# ------------------------------------------------------------------ 配置
def fig_layout(lang):
    """Draw only the integer-aligned layout, as PNG and SVG."""
    from guide.fig_nest_layout import draw as draw_layout
    return draw_layout(lang)

# ------------------------------------------------------------------ 時間進行
def fig_time(lang):
    t = T[lang]; en = lang == "en"
    fig, ax = plt.subplots(figsize=(10.5, 4.2)); ax.axis("off")
    RT = 3
    yP, yC, yG = 3.0, 1.9, 0.9
    x0, x1 = 1.0, 7.0
    dt = x1 - x0
    fs2 = 8.5 if en else 9                    # 英語の長い説明行
    # 親
    ax.plot([x0, x1], [yP, yP], color=C_P, lw=2.5, solid_capstyle="round")
    ax.plot([x0, x1], [yP, yP], "o", color=C_P, ms=8)
    ax.text(x0, yP + 0.32, t["tn"], ha="center", fontsize=11, color=C_P); ax.text(x1, yP + 0.32, t["tn1"], ha="center", fontsize=11, color=C_P)
    ax.text(x0 - 0.15, yP, t["tparent"], ha="right", va="center", fontsize=10, color=C_P)
    ax.text((x0 + x1) / 2, yP + 0.32, t["step1"], ha="center", fontsize=fs2, color=C_P)
    # 子
    ax.text(x0 - 0.15, yC, t["tchild"], ha="right", va="center", fontsize=10, color=C_C)
    for k in range(RT):
        xa, xb = x0 + k * dt / RT, x0 + (k + 1) * dt / RT
        ax.plot([xa, xb], [yC, yC], color=C_C, lw=2.2)
        ax.plot([xa], [yC], "o", color=C_C, ms=6)
        ax.add_patch(FancyArrowPatch((xa, yP - 0.08), (xa, yC + 0.1), arrowstyle="-|>", mutation_scale=10, color=C_X, lw=1.2, ls="--"))
        ax.text(xa + 0.08, (yP + yC) / 2 + 0.05, t["alpha"].format(k=k, rt=RT), fontsize=8.5, color=C_X, va="center")
    ax.plot([x1], [yC], "o", color=C_C, ms=6)
    ax.text((x0 + x1) / 2, yC - 0.38, t["step2"], ha="center", fontsize=fs2, color=C_X)
    # 孫
    ax.text(x0 - 0.15, yG, t["tgrand"], ha="right", va="center", fontsize=10, color="#5a9bd5")
    for k in range(RT):
        for m in range(2):
            xa = x0 + (k + m / 2) * dt / RT
            ax.plot([xa, xa + dt / RT / 2], [yG, yG], color="#5a9bd5", lw=1.6)
            ax.plot([xa], [yG], "o", color="#5a9bd5", ms=4)
    ax.plot([x1], [yG], "o", color="#5a9bd5", ms=4)
    ax.text((x0 + x1) / 2, yG - 0.38, t["step3"], ha="center", fontsize=fs2, color="#5a9bd5")
    # 置換
    ax.add_patch(FancyArrowPatch((x1 + 0.05, yC + 0.1), (x1 + 0.05, yP - 0.1), arrowstyle="-|>", mutation_scale=12, color=C_G, lw=2))
    ax.text(x1 + 0.2, (yP + yC) / 2, t["fb"], fontsize=9, color="#3f7a2a", va="center")
    ax.set_xlim(-0.6, 10.3); ax.set_ylim(0.3, 3.7)
    ax.set_title(t["ttitle"], loc="left", fontsize=10)
    fig.tight_layout(); out = out_path("nest_time", lang); fig.savefig(out, dpi=150); plt.close(fig)
    return out

# ------------------------------------------------------------------ 親→子の方式
def strip(ax, n, band, title, _n, labels, colors, pside, extra=None, tfs=10, lfs=8.5, pxy=(-0.15, 0.5)):
    """横一列のセル(西端 = 子の境界)を描く。band = 帯の幅、labels = (位置, 文, 色) の列"""
    ax.set_aspect("equal"); ax.axis("off")
    for i in range(n):
        fc = colors(i)
        ax.add_patch(Rectangle((i, 0), 1, 1, fc=fc, ec=C_C, lw=0.8))
    ax.plot([0, 0], [-0.1, 1.1], color="k", lw=2.2)
    ax.text(pxy[0], pxy[1], pside, ha="right", va="center", fontsize=8.5, color=C_P)
    for (x, s, c) in labels:
        ax.text(x, 1.18, s, ha="center", va="bottom", fontsize=lfs, color=c)
    ax.set_xlim(-2.6, n + 0.2); ax.set_ylim(-0.9, 2.4)
    ax.set_title(title, loc="left", fontsize=tfs)
    if extra: extra(ax)

def fig_bc(lang):
    t = T[lang]; en = lang == "en"
    fig, axs = plt.subplots(4, 1, figsize=(10.5, 8.8 if en else 7.6))
    N = 13
    hyd = "#f6e6c3"      # 帯(親の値)
    sponge = "#dff0cf"
    inner = "white"
    tfs = 9.2 if en else 10
    nfs = 8.2 if en else 8.5
    ps = t["pside"]
    # (1) 帯 Dirichlet
    def c1(i): return hyd if i < 3 else inner
    strip(axs[0], N, 3, t["t1"], N, [(1.5, t["l1a"], "#8a6b17"), (8.5, t["l1b"], C_C)], c1, ps,
          lambda ax: ax.text(1.5 if not en else 0.0, -0.45, t["n1"], ha="center" if not en else "left", fontsize=nfs, color=C_P), tfs=tfs)
    # (2) Flather
    def c2(i): return inner
    def ex2(ax):
        ax.add_patch(FancyArrowPatch((-0.9, 0.5), (0.0, 0.5), arrowstyle="-|>", mutation_scale=12, color=C_X, lw=1.8))
        ax.add_patch(FancyArrowPatch((0.0, 0.25), (-0.9, 0.25), arrowstyle="-|>", mutation_scale=12, color=C_G, lw=1.8))
        ax.text(0.5, -0.45, t["n2"], fontsize=nfs, color=C_X, ha="left")
        if en:
            ax.text(-0.5, 1.2, t["n2b"], fontsize=8, color=C_X, ha="center", va="bottom")
        else:
            ax.text(-0.95, 0.95, t["n2b"], fontsize=8, color=C_X, ha="right", va="center")
    strip(axs[1], N, 0, t["t2"], N, [(6.5, t["l2"], C_C)], c2, ps, ex2, tfs=tfs, pxy=(-1.05, 0.5) if en else (-0.15, 0.5))
    # (3) sponge
    def c3(i): return hyd if i < 3 else (sponge if i < 7 else inner)
    strip(axs[2], N, 3, t["t3"], N, [(1.5, t["l3a"], "#8a6b17"), (5.0, t["l3b"], "#3f7a2a"), (10, t["l3c"], C_C)], c3, ps, tfs=tfs)
    # (4) NH φ
    def c4(i): return hyd if i < 3 else inner
    def ex4(ax):
        for i in range(3):
            ax.text(i + 0.5, 0.5, "φ_e", ha="center", va="center", fontsize=9, color="#8a6b17")
        for i in range(3, N):
            ax.text(i + 0.5, 0.5, "φ", ha="center", va="center", fontsize=9, color=C_C)
        ax.plot([3, 3], [-0.05, 1.05], color=C_X, lw=2)
        ax.text(3.1, -0.45, t["n4"], fontsize=nfs, color=C_P, ha="left")
    strip(axs[3], N, 3, t["t4"], N, [(1.5, t["l4a"], "#8a6b17"), (8.5, t["l4b"], C_C)], c4, ps, ex4, tfs=tfs)
    fig.tight_layout(h_pad=0.4); out = out_path("nest_bc", lang); fig.savefig(out, dpi=150); plt.close(fig)
    return out

def draw(lang):
    """lang = "ja" | "en"。3 図を描いて出力パスの列を返す。"""
    return [fig_layout(lang), fig_time(lang), fig_bc(lang)]

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("figures", nargs="*", metavar="FIGURE",
                        help="layout, time or bc (default: all three)")
    args = parser.parse_args()
    drawers = {"layout": fig_layout, "time": fig_time, "bc": fig_bc}
    names = args.figures or list(drawers)
    for name in names:
        if name not in drawers:
            parser.error("unknown figure: " + name + " (choose layout, time or bc)")
    outs = []
    for lang in ("ja", "en"):
        outs.extend(drawers[name](lang) for name in names)
    print("wrote " + " ".join(os.path.basename(o) for o in outs))
