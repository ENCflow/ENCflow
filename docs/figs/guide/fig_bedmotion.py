"""規定底面運動(docs/users_guide/bedmotion.md)の説明図。

  bedmotion_patterns.png  (a) 累積変位の時刻歴と補間・z への増分、(b) 3 つの入力パターン、(c) z と h の契約と窓付きの変位ファイル
データ不要の模式図(matplotlib のみ)。
"""
import numpy as np
from _style import *

T = {
    "ja": dict(
        ta="(a) 時刻歴: 表の累積変位 d を補間し、増分 Δd を z に加える",
        tb="(b) 変位の与え方: 3 つのパターン",
        tc="(c) z と h の契約、広域の計算の窓付き変位ファイル",
        table="# time(s)  file\n  0.0      bm/disp_0000.txt\n 10.0      bm/disp_0010.txt\n 60.0      bm/disp_0060.txt",
        lin="線形補間 f_bminterp = 1(既定)", step="階段 f_bminterp = 0(直前の値を保持)",
        hold="最後の時刻より後は末尾の値を保持", hold0="最初の時刻より前:\n先頭の値",
        snap="スナップショット(累積変位。正 = 隆起)",
        inc="各ステップの頭: ステップ末尾の時刻の d を補間し、\n前回適用した変位との差分 Δd を z に加える",
        xl="t (s)(bm_tscale で分・時も可)", yl="累積変位 d (m)",
        contract="z は Δd だけ上がり h は不変\n→ 水面 e = z + h が一緒に上がる\n(陸セル・海域マスク外。運動量は触らない)",
        before="前", after="後",
        A="A: 断層パラメータ(&list_fault2disp)\n位置・走向・傾斜・すべり角・長さ・幅・すべり量・t_r・t_rise\n(複数セグメント可)\n→ utils/fault2disp(Okada 1985)が\n   bm/disp_0000.txt … と bm/bmlist.txt を書く",
        B="B: 自分で作った変位場(測地観測・断層反転解・別モデル)\n→ 前処理で z と同じ格子・形式(f_input_mode)にし、\n   各時刻の累積変位にして、表を自分で書く",
        C="C: 瞬時変位(従来の初期水位方式と同じ)\n→ 表を 1 行にする:  0.0  bm/disp_0010.txt",
        anyof="いずれか一つ",
        D="&list_bedmotion: fn_bmlist(表)\nf_bminterp、bm_tscale",
        E="地盤高 z(陸セル。海域マスク sw > 0 のセルは動かない)\n増分で与えるので、土砂・地形変化・溶岩流が同じランで\nz を動かしていても衝突しない",
        win_full="全域 nx × ny", win="窓 ni × nj\n(左上 = 列 i1, 行 j1)\n窓の外は変位 0",
        win_line="行末に 4 整数:\n0.0  bm/disp_0000.txt  i1 j1 ni nj\n(fault2disp の f_window = 1 が書く形)",
    ),
    "en": dict(
        ta="(a) Time history: cumulative d is interpolated, Δd is added to z",
        tb="(b) Three ways to supply the displacement",
        tc="(c) The z-h contract, and windowed files for large domains",
        table="# time(s)  file\n  0.0      bm/disp_0000.txt\n 10.0      bm/disp_0010.txt\n 60.0      bm/disp_0060.txt",
        lin="linear f_bminterp = 1 (default)", step="stepwise f_bminterp = 0 (previous value held)",
        hold="after the last time the last value holds", hold0="before t₀:\nfirst value",
        snap="snapshot (cumulative; positive = uplift)",
        inc="at the head of each step: interpolate d at the end of\nthe step, add the difference Δd from the last applied d to z",
        xl="t (s) (minutes/hours via bm_tscale)", yl="cumulative displacement d (m)",
        contract="z rises by Δd, h is kept\n→ e = z + h rises with it\n(land cells outside the sea mask;\nmomentum untouched)",
        before="before", after="after",
        A="A: fault parameters (&list_fault2disp): position, strike, dip,\nrake, length, width, slip, t_r, t_rise; several segments allowed\n→ utils/fault2disp (Okada 1985) writes\n   bm/disp_0000.txt … and bm/bmlist.txt",
        B="B: a displacement field of your own (geodetic data, slip\ninversions, other models) → preprocess to the grid and\nformat of z (f_input_mode), make each time cumulative,\nwrite the table yourself",
        C="C: instantaneous (the conventional initial-surface approach)\n→ reduce the table to one line:  0.0  bm/disp_0010.txt",
        anyof="one of",
        D="&list_bedmotion: fn_bmlist (the table)\nf_bminterp, bm_tscale",
        E="bed elevation z (land cells; sea-mask cells do not move)\nincrements → no conflict with geomorph or lava flow\nmoving z in the same run",
        win_full="full grid nx × ny", win="window ni × nj\n(top-left = column i1, row j1)\nzero outside",
        win_line="4 integers at the line end:\n0.0  bm/disp_0000.txt  i1 j1 ni nj\n(f_window = 1 of fault2disp writes it)",
    ),
}


def box(ax, x0, y0, w, h, text, ec, fc="white", fs=8.5, color="k", lw=1.5):
    ax.add_patch(FancyBboxPatch((x0, y0), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fc, ec=ec, lw=lw, zorder=4))
    ax.text(x0 + w / 2, y0 + h / 2, text, ha="center", va="center", fontsize=fs, color=color, zorder=5)


def draw(lang):
    t = T[lang]
    en = lang == "en"
    fig = plt.figure(figsize=(10.5, 6.6), layout="constrained")
    gs = fig.add_gridspec(2, 2, width_ratios=[1.12, 1], height_ratios=[1.0, 0.85])
    # ---------------------------------------------------------------- (a) 時刻歴
    ax = fig.add_subplot(gs[0, 0])
    tk, dk = [0.0, 10.0, 60.0], [0.0, 0.35, 1.0]
    tl = np.linspace(-8, 78, 300)
    dl = np.interp(tl, tk, dk)
    ds = np.piecewise(tl, [tl < 10, (tl >= 10) & (tl < 60), tl >= 60], [0.0, 0.35, 1.0])
    ax.plot(tl, dl, color=C_C, lw=2.0, label=t["lin"], zorder=3)
    ax.plot(tl, ds, color=C_P, lw=1.3, ls="--", label=t["step"], zorder=2)
    ax.plot(tk, dk, "o", color=C_X, ms=7, zorder=5, label=t["snap"])
    for tt in np.arange(-5, 76, 5):
        ax.plot([tt, tt], [-0.06, -0.02], color=C_P, lw=0.8)
    # 増分の説明(t = 30 → 36)
    for tt in (30, 36):
        ax.plot([tt, tt], [-0.02, np.interp(tt, tk, dk)], color=C_X, lw=0.8, ls=":")
    ax.annotate("", (37.5, np.interp(36, tk, dk)), (37.5, np.interp(30, tk, dk)),
                arrowprops=dict(arrowstyle="<->", color=C_X, lw=1.0, shrinkA=0, shrinkB=0))
    ax.text(38.5, (np.interp(30, tk, dk) + np.interp(36, tk, dk)) / 2, "Δd", color=C_X, fontsize=9, va="center")
    ax.text(21, 1.3, t["inc"], color=C_X, fontsize=7.5, ha="left", va="top")
    ax.text(61, 1.04, t["hold"], color=C_P, fontsize=7.5, ha="left", va="bottom")
    ax.text(-7.5, 0.4, t["hold0"], color=C_P, fontsize=7, ha="left", va="bottom")
    ax.text(-7, 0.98, t["table"], family="monospace", fontsize=7, ha="left", va="top",
            bbox=dict(fc="#f6f6f3", ec="none", pad=3))
    ax.set_xlim(-8, 78); ax.set_ylim(-0.12, 1.32)
    ax.set_xlabel(t["xl"], fontsize=8.5); ax.set_ylabel(t["yl"], fontsize=8.5)
    ax.tick_params(labelsize=8)
    ax.legend(loc="lower right", fontsize=7, frameon=True, framealpha=0.9, edgecolor="none", bbox_to_anchor=(1.0, 0.03))
    ax.set_title(t["ta"], loc="left", fontsize=8 if en else 9)
    # ---------------------------------------------------------------- (c) z と h の契約 + 窓
    ax = fig.add_subplot(gs[1, 0])
    ax.axis("off"); ax.set_xlim(0, 10.5); ax.set_ylim(-0.2, 3.9)
    for k, (x0, zb) in enumerate(((0.3, 0.3), (1.8, 0.9))):
        ax.add_patch(Rectangle((x0, 0.0), 1.0, zb, fc=C_GROUND_L, ec="k", lw=0.8, zorder=2))
        ax.add_patch(Rectangle((x0, zb), 1.0, 1.4, fc=C_WATER_L, ec=C_WATER, lw=0.8, zorder=2))
        label(ax, x0 + 0.5, zb + 0.7, "h", color="#1f4f8f", fs=9)
        label(ax, x0 + 0.5, zb / 2, "z", color="k", fs=9)
        label(ax, x0 + 0.5, zb + 1.4 + 0.12, "e = z + h", color=C_WATER, fs=8, va="bottom")
        label(ax, x0 + 0.5, -0.15, t["before"] if k == 0 else t["after"], color=C_P, fs=8, va="top")
    ax.annotate("", (1.8 - 0.05, 0.9), (1.3 + 0.05, 0.3), arrowprops=dict(arrowstyle="-|>", color=C_X, lw=1.4))
    ax.annotate("", (3.1, 0.9), (3.1, 0.3), arrowprops=dict(arrowstyle="<->", color=C_X, lw=1.0))
    label(ax, 3.2, 0.6, "Δd", color=C_X, fs=9, ha="left")
    label(ax, 0.3, 2.75, t["contract"], color="k", fs=7.5 if en else 8.5, ha="left", va="bottom")
    gx, gy, nx, ny, d = 5.8, 0.1, 16, 10, 0.19
    grid(ax, gx, gy, nx, ny, d, color="#c9c8c3", lw=0.5)
    ax.add_patch(Rectangle((gx, gy), nx * d, ny * d, fill=False, ec=C_P, lw=1.2, zorder=3))
    wi, wj, wn, wm = 5, 2, 7, 5
    wx, wy = gx + (wi - 1) * d, gy + (ny - (wj - 1) - wm) * d
    ax.add_patch(Rectangle((wx, wy), wn * d, wm * d, fc=C_B, ec=C_X, lw=1.4, alpha=0.75, zorder=3))
    ax.plot([wx], [wy + wm * d], "o", color=C_X, ms=5, zorder=6)
    label(ax, gx + nx * d / 2, gy + ny * d + 0.1, t["win_full"], color=C_P, fs=8, va="bottom")
    ax.annotate(t["win"], (wx + wn * d / 2, wy + wm * d / 2), (gx + nx * d + 0.15, wy + wm * d / 2 + 0.2), fontsize=7.5, ha="left", va="center",
                color="#8a6b17", arrowprops=dict(arrowstyle="-", color=C_P, lw=0.7), zorder=8)
    label(ax, 5.9, 2.75, t["win_line"], color="k", fs=7.5, ha="left", va="bottom")
    ax.text(0.0, 3.75, t["tc"], fontsize=8 if en else 9, ha="left", va="center")
    # ---------------------------------------------------------------- (b) パターン
    ax = fig.add_subplot(gs[:, 1])
    ax.axis("off"); ax.set_xlim(0, 10.3); ax.set_ylim(0, 10.6)
    ax.set_title(t["tb"], loc="left", fontsize=9)
    fsb = 7.0 if en else 7.8
    box(ax, 0.2, 8.45, 9.6, 1.75, t["A"], C_X, fc="#fdeee8", fs=fsb)
    box(ax, 0.2, 6.35, 9.6, 1.75, t["B"], C_X, fc="#fdeee8", fs=fsb)
    box(ax, 0.2, 4.85, 9.6, 1.15, t["C"], C_X, fc="#fdeee8", fs=fsb)
    # 3 つは択一: 右の背骨でまとめて &list_bedmotion へ
    for yc in (8.45 + 1.75 / 2, 6.35 + 1.75 / 2, 4.85 + 1.15 / 2):
        ax.plot([9.82, 10.1], [yc, yc], color=C_X, lw=1.3, zorder=3)
    ax.plot([10.1, 10.1, 5.0], [8.45 + 1.75 / 2, 4.3, 4.3], color=C_X, lw=1.3, zorder=3)
    ax.add_patch(FancyArrowPatch((5.0, 4.3), (5.0, 3.72), arrowstyle="-|>", mutation_scale=12, color=C_X, lw=1.3, zorder=6))
    label(ax, 5.15, 4.0, t["anyof"], color=C_X, fs=7.5, ha="left")
    box(ax, 1.8, 2.5, 6.4, 1.15, t["D"], C_C, fc="#eaf2fc", fs=fsb)
    arrow(ax, (5.0, 2.45), (5.0, 1.85), color=C_G, lw=1.8)
    box(ax, 0.2, 0.3, 9.6, 1.5, t["E"], C_G, fc="#eef6e8", fs=fsb)
    return save(fig, "bedmotion_patterns", lang)
