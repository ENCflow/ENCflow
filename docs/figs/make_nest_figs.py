#!/usr/bin/env python3
"""ネスティングの説明図(docs/users_guide/nest.md、docs/en/users_guide/nest.md 用)を figs/ に描く。

  使い方: python3 make_nest_figs.py        (docs/figs/ で実行。データ不要の模式図)
  nest_layout.png   親子格子の配置(i0, j0・比 r・帯 nb)と親→子・子→親の交換
  nest_time.png     時間進行(親先行・子の r_t サブステップ・帯の時間補間・置換の時機)
  nest_bc.png       親→子の 3 方式(帯 Dirichlet・Flather 放射・スポンジ)と非静水圧の帯の φ
計算本体の外(方針 10)。numpy + matplotlib。
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
import numpy as np

plt.rcParams.update({"font.family": ["IPAGothic", "DejaVu Sans"], "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
C_P, C_C, C_B, C_X, C_G = "#6b6a66", "#2a78d6", "#f2b84b", "#eb6834", "#8fbf6a"   # 親・子・帯・強調・置換

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
def fig_layout(out):
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 5.0), gridspec_kw={"width_ratios": [1.15, 1]})
    # (a) 親の中の子: 親 14x11 セル、子は親セル (5..10, 3..8) = 6x6 親セル、比 3 → 18x18
    ax = axs[0]; ax.set_aspect("equal"); ax.axis("off")
    NXP, NYP, R = 14, 11, 3
    I0, J0, NFP = 5, 3, 6                      # 子の足元の親セル(1 始まり)と足元の親セル数
    grid(ax, 0, 0, NXP, NYP, 1, C_P, 0.7)
    # 親の外縁 1 セル(子を置けない)
    ax.add_patch(Rectangle((0, 0), NXP, NYP, fill=False, hatch="////", ec="#d9d8d3", lw=0, zorder=0))
    ax.add_patch(Rectangle((1, 1), NXP - 2, NYP - 2, fc="white", ec="none", zorder=0.5))
    # 子(y は上が北 = j 小。描画の y は北を上に: y_top = NYP、j 行は y = NYP - j)
    xs, yt = I0 - 1, NYP - (J0 - 1)            # 子の北西角
    fp = Rectangle((xs, yt - NFP), NFP, NFP, fc="#eaf2fc", ec="none", zorder=1.5); ax.add_patch(fp)
    grid(ax, xs, yt - NFP, NFP * R, NFP * R, 1.0 / R, C_C, 0.35, z=2)
    ax.add_patch(Rectangle((xs, yt - NFP), NFP, NFP, fill=False, ec=C_C, lw=1.8, zorder=4))
    # 帯 nb = 3 子セル(= 1 親セル)
    nb = 3.0 / R
    for (x, y, w, h) in [(xs, yt - nb, NFP, nb), (xs, yt - NFP, NFP, nb), (xs, yt - NFP, nb, NFP), (xs + NFP - nb, yt - NFP, nb, NFP)]:
        ax.add_patch(Rectangle((x, y), w, h, fc=C_B, ec="none", alpha=0.75, zorder=3))
    ax.plot([xs], [yt], "o", color=C_X, ms=6, zorder=7)
    ax.annotate("子セル (1,1) の北西角 = 親セル (i0, j0) の北西角", (xs, yt), (0.3, NYP + 0.9), fontsize=9, color=C_X,
                arrowprops=dict(arrowstyle="-", color=C_X, lw=0.8))
    ax.text(xs + NFP / 2, yt - NFP - 0.45, f"子: nx = ny = {NFP * R}(親セル {NFP} 個 × r = {R})", ha="center", va="top", fontsize=9, color=C_C)
    ax.text(xs + NFP + 0.35, yt - nb / 2 - 0.2, "境界帯 nb セル\n(自動: スキーム 1 は 2、\n 2・3 は 3)", va="center", fontsize=8.5, color="#8a6b17")
    ax.text(NXP / 2 + 1, -0.9, "親(ルート): nx × ny。外縁 1 セル(斜線)には子を置けない", ha="center", va="top", fontsize=9, color=C_P)
    # 行番号の向き
    ax.annotate("", (-0.6, NYP - 3), (-0.6, NYP), arrowprops=dict(arrowstyle="-|>", color=C_P, lw=1))
    ax.text(-0.75, NYP - 1.5, "j(行。北→南)", fontsize=8.5, color=C_P, va="center", ha="right", rotation=90)
    ax.annotate("", (3, -0.35), (0, -0.35), arrowprops=dict(arrowstyle="-|>", color=C_P, lw=1))
    ax.text(1.5, -0.45, "i(列。西→東)", fontsize=8.5, color=C_P, ha="center", va="top")
    ax.set_xlim(-1.6, NXP + 3.6); ax.set_ylim(-1.8, NYP + 1.6)
    ax.set_title("(a) 配置: 一覧ファイルの 1 行 = 1 格子(parent, r, r_t, i0, j0)", loc="left", fontsize=10)
    # (b) 交換の拡大図: 親 4x4 セル、子は右下 2x2 親セル… 子の西辺付近を拡大
    ax = axs[1]; ax.set_aspect("equal"); ax.axis("off")
    grid(ax, 0, 0, 5, 4, 1, C_P, 0.8)
    xs = 1.0
    ax.add_patch(Rectangle((xs, 0), 4, 4, fc="#eaf2fc", ec="none", zorder=1))
    grid(ax, xs, 0, 12, 12, 1 / 3, C_C, 0.4, z=2)
    ax.add_patch(Rectangle((xs, 0), 1, 4, fc=C_B, ec="none", alpha=0.75, zorder=3))
    ax.add_patch(Rectangle((xs, 0), 4, 4, fill=False, ec=C_C, lw=1.8, zorder=4))
    ax.plot([xs + 0.5], [2.5], "s", color=C_P, ms=7, zorder=6)
    ax.plot([xs + 0.5 - 1.0], [2.5], "s", color=C_P, ms=7, zorder=6, mfc="none")
    arrow(ax, (xs - 0.35, 2.5), (xs + 0.3, 2.5), C_X, lw=2)
    ax.text(xs - 0.1, 4.75, "親 → 子(各サブステップ)\n帯の子セルへ親の値を補間して置く\n(nest_bc: 水位 / 水位+流速+エッジ流量)",
            fontsize=8.5, color=C_X, ha="left", va="center",
            bbox=dict(fc="white", ec="none", alpha=0.85))
    # 子→親: 内部の r×r → 親セル
    cx, cy = xs + 2, 1.5
    ax.add_patch(Rectangle((cx, cy), 1, 1, fill=False, ec=C_G, lw=2.2, zorder=6))
    arrow(ax, (cx + 1.15, cy + 0.5), (cx + 1.85, cy + 0.5), C_G, lw=2)
    ax.add_patch(Rectangle((cx + 2, cy), 1, 1, fill=False, ec=C_G, lw=2.2, ls="--", zorder=6))
    ax.text(xs - 0.1, -0.85, "子 → 親(親の 1 歩ごと)\n帯を除く内部の r×r 子セルの平均で\n親セルを置換(nest_fb: 0 = 一方向, 1 = 面積平均,\n2 = 湿潤判定付き〔既定〕, 3 = 2 + 保存修正)",
            fontsize=8.5, color="#3f7a2a", ha="left", va="center", bbox=dict(fc="white", ec="none", alpha=0.85))
    ax.text(xs - 0.5, 2.1, "親セル", fontsize=8, color=C_P, ha="center")
    ax.text(xs + 0.5, 2.1, "帯の\n子セル", fontsize=8, color=C_P, ha="center", va="top")
    ax.set_xlim(-0.3, 5.3); ax.set_ylim(-1.6, 5.4)
    ax.set_title("(b) 交換(r = 3、nb = 3 子セル = 1 親セル)", loc="left", fontsize=10)
    fig.tight_layout(); fig.savefig(out, dpi=150); plt.close(fig)

# ------------------------------------------------------------------ 時間進行
def fig_time(out):
    fig, ax = plt.subplots(figsize=(10.5, 4.2)); ax.axis("off")
    RT = 3
    yP, yC, yG = 3.0, 1.9, 0.9
    x0, x1 = 1.0, 7.0
    dt = x1 - x0
    # 親
    ax.plot([x0, x1], [yP, yP], color=C_P, lw=2.5, solid_capstyle="round")
    ax.plot([x0, x1], [yP, yP], "o", color=C_P, ms=8)
    ax.text(x0, yP + 0.32, "tⁿ", ha="center", fontsize=11, color=C_P); ax.text(x1, yP + 0.32, "tⁿ⁺¹ = tⁿ + Δt", ha="center", fontsize=11, color=C_P)
    ax.text(x0 - 0.15, yP, "親(格子 1)", ha="right", va="center", fontsize=10, color=C_P)
    ax.text((x0 + x1) / 2, yP + 0.32, "① 親が先に 1 歩進む(帯の窓 wc を tⁿ・tⁿ⁺¹ の 2 時刻で保持)", ha="center", fontsize=9, color=C_P)
    # 子
    ax.text(x0 - 0.15, yC, "子(r_t = 3)", ha="right", va="center", fontsize=10, color=C_C)
    for k in range(RT):
        xa, xb = x0 + k * dt / RT, x0 + (k + 1) * dt / RT
        ax.plot([xa, xb], [yC, yC], color=C_C, lw=2.2)
        ax.plot([xa], [yC], "o", color=C_C, ms=6)
        a = k / RT
        ax.add_patch(FancyArrowPatch((xa, yP - 0.08), (xa, yC + 0.1), arrowstyle="-|>", mutation_scale=10, color=C_X, lw=1.2, ls="--"))
        ax.text(xa + 0.08, (yP + yC) / 2 + 0.05, f"α = {k}/{RT}", fontsize=8.5, color=C_X, va="center")
    ax.plot([x1], [yC], "o", color=C_C, ms=6)
    ax.text((x0 + x1) / 2, yC - 0.38, "② 子は Δt/r_t を r_t 回。各サブステップの開始時刻で帯 = (1−α)·wc(tⁿ) + α·wc(tⁿ⁺¹)(非静水圧の φ は終了時刻 α + 1/r_t)",
            ha="center", fontsize=9, color=C_X)
    # 孫
    ax.text(x0 - 0.15, yG, "孫(r_t = 2)", ha="right", va="center", fontsize=10, color="#5a9bd5")
    for k in range(RT):
        for m in range(2):
            xa = x0 + (k + m / 2) * dt / RT
            ax.plot([xa, xa + dt / RT / 2], [yG, yG], color="#5a9bd5", lw=1.6)
            ax.plot([xa], [yG], "o", color="#5a9bd5", ms=4)
    ax.plot([x1], [yG], "o", color="#5a9bd5", ms=4)
    ax.text((x0 + x1) / 2, yG - 0.38, "③ 子の各サブステップの中で孫が同じ手順を繰り返す(再帰。任意の深さ・一つの親に複数の子)", ha="center", fontsize=9, color="#5a9bd5")
    # 置換
    ax.add_patch(FancyArrowPatch((x1 + 0.05, yC + 0.1), (x1 + 0.05, yP - 0.1), arrowstyle="-|>", mutation_scale=12, color=C_G, lw=2))
    ax.text(x1 + 0.2, (yP + yC) / 2, "④ 子 → 親の置換(nest_fb)\n(tⁿ⁺¹ で子の内部の平均を親へ)", fontsize=9, color="#3f7a2a", va="center")
    ax.set_xlim(-0.6, 10.3); ax.set_ylim(0.3, 3.7)
    ax.set_title("時間進行(親先行・子サブステップ・時間補間・置換。plan §3.4)", loc="left", fontsize=10)
    fig.tight_layout(); fig.savefig(out, dpi=150); plt.close(fig)

# ------------------------------------------------------------------ 親→子の方式
def strip(ax, n, band, title, _n, labels, colors, extra=None):
    """横一列のセル(西端 = 子の境界)を描く。band = 帯の幅、labels = (位置, 文, 色) の列"""
    ax.set_aspect("equal"); ax.axis("off")
    for i in range(n):
        fc = colors(i)
        ax.add_patch(Rectangle((i, 0), 1, 1, fc=fc, ec=C_C, lw=0.8))
    ax.plot([0, 0], [-0.1, 1.1], color="k", lw=2.2)
    ax.text(-0.15, 0.5, "親\n側", ha="right", va="center", fontsize=8.5, color=C_P)
    for (x, s, c) in labels:
        ax.text(x, 1.18, s, ha="center", va="bottom", fontsize=8.5, color=c)
    ax.set_xlim(-2.6, n + 0.2); ax.set_ylim(-0.9, 2.4)
    ax.set_title(title, loc="left", fontsize=10)
    if extra: extra(ax)

def fig_bc(out):
    fig, axs = plt.subplots(4, 1, figsize=(10.5, 7.6))
    N = 13
    hyd = "#f6e6c3"      # 帯(親の値)
    sponge = "#dff0cf"
    inner = "white"
    # (1) 帯 Dirichlet
    def c1(i): return hyd if i < 3 else inner
    strip(axs[0], N, 3, "(1) nest_bc = 1・2(既定)・4: 境界帯(nb セル)に親の値を置く(Dirichlet)。子の外縁は壁(f_bc_* = 0)のまま",
          N, [(1.5, "帯: 親の η(→h)・u, v・エッジ流量(2・4)\n/ η のみ(1)", "#8a6b17"), (8.5, "子が計算する内部(置換の対象)", C_C)], c1,
          lambda ax: ax.text(1.5, -0.45, "子の擾乱は帯で親の値に上書きされ反射する(双方向なら小さい)", ha="center", fontsize=8.5, color=C_P))
    # (2) Flather
    def c2(i): return inner
    def ex2(ax):
        ax.add_patch(FancyArrowPatch((-0.9, 0.5), (0.0, 0.5), arrowstyle="-|>", mutation_scale=12, color=C_X, lw=1.8))
        ax.add_patch(FancyArrowPatch((0.0, 0.25), (-0.9, 0.25), arrowstyle="-|>", mutation_scale=12, color=C_G, lw=1.8))
        ax.text(0.5, -0.45, "境界面: u_n = u_n,e + √(g/h)(η − η_e)   η_e, u_n,e = 親の値(境界セル中心へ補間、時間補間)", fontsize=8.5, color=C_X, ha="left")
        ax.text(-0.95, 0.95, "親の波は入る\n子の擾乱は出る", fontsize=8, color=C_X, ha="right", va="center")
    strip(axs[1], N, 0, "(2) nest_bc = 3: Flather 放射(帯なし)。親の値を受ける辺を f_bc_* = 2 にする。一方向(nest_fb = 0)向き",
          N, [(6.5, "子は境界セルまで自分で計算する(足元の全域が使える)", C_C)], c2, ex2)
    # (3) sponge
    def c3(i): return hyd if i < 3 else (sponge if i < 7 else inner)
    strip(axs[2], N, 3, "(3) nest_bc = 4: 2 + スポンジ(帯の内側 nest_ns セルを親の値へ緩和)。帯の反射が目立つときの選択肢",
          N, [(1.5, "帯(親の値)", "#8a6b17"), (5.0, "スポンジ nest_ns(緩和)", "#3f7a2a"), (10, "内部", C_C)], c3)
    # (4) NH φ
    def c4(i): return hyd if i < 3 else inner
    def ex4(ax):
        for i in range(3):
            ax.text(i + 0.5, 0.5, "φ_e", ha="center", va="center", fontsize=9, color="#8a6b17")
        for i in range(3, N):
            ax.text(i + 0.5, 0.5, "φ", ha="center", va="center", fontsize=9, color=C_C)
        ax.plot([3, 3], [-0.05, 1.05], color=C_X, lw=2)
        ax.text(3.1, -0.45, "帯〜内部のエッジも補正される(既知セルの φ_e と未知セルの φ の差)。nest_nh = 0 は帯 + 余白 nh_bc_margin を静水圧にする(位相がずれる)", fontsize=8.5, color=C_P, ha="left")
    strip(axs[3], N, 3, "(4) 非静水圧の子(f_nonhydrostatic = 1、帯あり): 帯のセルは親の φ の既知セル(Dirichlet。nest_nh = 1 既定)、内部が射影の未知数",
          N, [(1.5, "φ_e = 親の φ(サブステップ終了時刻で補間)", "#8a6b17"), (8.5, "子の射影(CG)の未知数。活性集合は帯に接するセルを |φ_e| で種に", C_C)], c4, ex4)
    fig.tight_layout(h_pad=0.4); fig.savefig(out, dpi=150); plt.close(fig)

if __name__ == "__main__":
    fig_layout("nest_layout.png"); fig_time("nest_time.png"); fig_bc("nest_bc.png")
    print("wrote nest_layout.png nest_time.png nest_bc.png")
