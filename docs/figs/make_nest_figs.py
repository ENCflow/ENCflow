#!/usr/bin/env python3
"""ネスティングの説明図(docs/users_guide/nest.md、docs/en/users_guide/nest.md 用)を figs/ に描く。

  使い方: python3 docs/figs/make_nest_figs.py [layout|time|bc ...]
  引数なしは従来どおり全3図。layout / bc はそれぞれ対象だけを日英PNG・SVGで生成。
  nest_layout.png   親子格子の配置(i0, j0・比 r・帯 nb)と親→子・子→親の交換
  nest_time.png     時間進行(親先行・子の r_t サブステップ・帯の時間補間・置換の時機)
  nest_bc.png       親→子の境界方式(帯・Flather・スポンジ)と非静水圧の追加設定
  各図は日本語(<name>.png)と英語(<name>_en.png)を書く。layout / bc は SVG も出力。
  draw(lang) が 3 図をまとめて描く。時間進行図は従来の描画処理を保持。
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
def fig_bc(lang):
    """Draw boundary methods and the NH supplement, as PNG and SVG."""
    from guide.fig_nest_bc import draw as draw_bc
    return draw_bc(lang)


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
