"""浅水流計算の章の図: ENC 格子(8 近傍コロケート)と STG の対比、適応的ルンゲクッタの発動規則。"""
from _style import *

T = {"ja": {
    "a": "(a) ENC 格子(f_gridsystem = 0、既定)\n8 近傍連結のコロケート格子",
    "b": "(b) STG(f_gridsystem = 1)\nスタガード格子(旧互換・比較用)",
    "c": "(c) 適応的ルンゲクッタ(f_adaptive_runge = 1)\n ",
    "cell": "セル中心: 水深 h・地盤高 z\n(セル流速 u, v はエッジから再構成)",
    "axis": "軸エッジ 4 本",
    "diag": "斜めエッジ 4 本\n(通過幅の配分比 p_diagratio)",
    "edge": "エッジ(8 方向)に法線流速 uv と\n単位幅流量 mn を置き、フラックスを計算",
    "stg_note": "h はセル中心、u は東西面・v は南北面\n(4 近傍。新機能・再開は非対応)",
    "c_top": "各エッジで、陽解法で得た流量 mn(新) を\n前ステップの mn(前) と比べる",
    "c_lo": "急減・逆転", "c_hi": "急増",
    "c_in": "閾値内: 陽解法の値をそのまま採用",
    "c_out": "閾値外のエッジだけ 4 段 RK で再計算\n(他エッジは前ステップ値を参照)\n→ 画面の Runge 列 = 再計算したエッジの割合",
    "c_ratio": "横軸: 比 mn(新) / mn(前)",
    "c_thr": "p_adprunge_thresh(既定 1.5。\n小さいほど高精度・高コスト、1.1〜)",
}, "en": {
    "a": "(a) ENC grid (f_gridsystem = 0, default)\n8-neighbour connected collocated grid",
    "b": "(b) STG (f_gridsystem = 1)\nstaggered grid (legacy, comparison only)",
    "c": "(c) Adaptive Runge-Kutta (f_adaptive_runge = 1)\n ",
    "cell": "cell centre: depth h, ground z\n(cell velocity u, v rebuilt from edges)",
    "axis": "4 axis edges",
    "diag": "4 diagonal edges\n(width share p_diagratio)",
    "edge": "the 8 edges carry the normal velocity uv and\nunit-width flux mn; fluxes are computed there",
    "stg_note": "h at cell centre, u on E/W faces, v on N/S faces\n(4 neighbours; no new features, no restart)",
    "c_top": "each edge: compare the explicit flux mn(new)\nwith the previous step's mn(old)",
    "c_lo": "drop /\nreversal", "c_hi": "rise",
    "c_in": "inside the band: keep the explicit value",
    "c_out": "only edges outside the band are recomputed with\n4-stage RK (other edges keep their old value)\n-> Runge column on screen = share of recomputed edges",
    "c_ratio": "axis: ratio mn(new) / mn(old)",
    "c_thr": "p_adprunge_thresh (default 1.5;\nsmaller = more accurate, costlier; 1.1 and up)",
}}


def panel_enc(ax, t):
    ax.set_aspect("equal"); ax.axis("off")
    grid(ax, 0, 0, 3, 3, 1, C_P, 0.8)
    ax.add_patch(Rectangle((1, 1), 1, 1, fc="#eaf2fc", ec="none", zorder=0.5))
    c = (1.5, 1.5)
    for (dx, dy) in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
        ax.plot([c[0], c[0] + dx], [c[1], c[1] + dy], color=C_C, lw=1.8, zorder=3)
        ax.plot([c[0] + dx * 0.5], [c[1] + dy * 0.5], "s", color=C_C, ms=6, zorder=5)
    for (dx, dy) in [(1, 1), (-1, 1), (1, -1), (-1, -1)]:
        ax.plot([c[0], c[0] + dx], [c[1], c[1] + dy], color=C_C, lw=1.4, ls="--", zorder=3)
        ax.plot([c[0] + dx * 0.5], [c[1] + dy * 0.5], "s", color=C_C, ms=6, mfc="white", zorder=5)
    for i in range(3):
        for j in range(3):
            ax.plot([i + 0.5], [j + 0.5], "o", color=C_P, ms=5, zorder=4)
    ax.plot([1.5], [1.5], "o", color="k", ms=7, zorder=6)
    ax.annotate(t["cell"], (1.5, 1.5), (-0.2, 3.95), fontsize=8.5, color="k", ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color="k", lw=0.7))
    ax.annotate(t["axis"], (2.0, 1.5), (3.2, 2.3), fontsize=8.5, color=C_C, ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color=C_C, lw=0.7))
    ax.annotate(t["diag"], (2.0, 1.0), (3.2, 0.75), fontsize=8.5, color=C_C, ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color=C_C, lw=0.7))
    ax.text(-0.25, -0.35, t["edge"], ha="left", va="top", fontsize=8.5, color=C_C)
    ax.set_xlim(-0.3, 5.6); ax.set_ylim(-1.3, 4.5)
    ax.set_title(t["a"], loc="left", fontsize=10)


def panel_stg(ax, t):
    ax.set_aspect("equal"); ax.axis("off")
    grid(ax, 0, 0, 3, 3, 1, C_P, 0.8)
    ax.add_patch(Rectangle((1, 1), 1, 1, fc="#eaf2fc", ec="none", zorder=0.5))
    for i in range(3):
        for j in range(3):
            ax.plot([i + 0.5], [j + 0.5], "o", color=C_P, ms=5, zorder=4)
    ax.plot([1.5], [1.5], "o", color="k", ms=7, zorder=6)
    ax.text(1.5, 1.72, "h", ha="center", va="bottom", fontsize=9, color="k", zorder=7)
    for x in (1, 2):
        for j in range(3):
            ax.plot([x], [j + 0.5], ">", color=C_C, ms=7, zorder=5)
    for y in (1, 2):
        for i in range(3):
            ax.plot([i + 0.5], [y], "^", color=C_C, ms=7, zorder=5)
    ax.text(1.0, 1.62, "u", ha="right", va="bottom", fontsize=9, color=C_C, zorder=7)
    ax.text(1.62, 2.0, "v", ha="left", va="bottom", fontsize=9, color=C_C, zorder=7)
    for (dx, dy) in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
        ax.plot([1.5, 1.5 + dx * 0.5], [1.5, 1.5 + dy * 0.5], color=C_C, lw=1.6, zorder=3)
    ax.text(-0.25, -0.35, t["stg_note"], ha="left", va="top", fontsize=8.5, color=C_P)
    ax.set_xlim(-0.3, 4.6); ax.set_ylim(-1.3, 4.5)
    ax.set_title(t["b"], loc="left", fontsize=10)


def panel_rk(ax, t):
    ax.axis("off")
    # 比の帯: 対数目盛風に 1/thr, 1, thr を等間隔に置く
    x_lo, x1, x_hi = 2.2, 4.2, 6.2
    y0, hh = 2.0, 0.6
    ax.add_patch(Rectangle((0.2, y0), x_lo - 0.2, hh, fc=C_X, ec="none", alpha=0.8, zorder=1))
    ax.add_patch(Rectangle((x_lo, y0), x_hi - x_lo, hh, fc=C_G, ec="none", alpha=0.8, zorder=1))
    ax.add_patch(Rectangle((x_hi, y0), 8.0 - x_hi, hh, fc=C_X, ec="none", alpha=0.8, zorder=1))
    for x, s in [(x_lo, "1/thr"), (x1, "1"), (x_hi, "thr")]:
        ax.plot([x, x], [y0 - 0.1, y0 + hh + 0.1], color="k", lw=1.0, zorder=3)
        ax.text(x, y0 - 0.18, s, ha="center", va="top", fontsize=9, color="k")
    ax.text(x1, y0 + hh + 0.18, t["c_in"], ha="center", va="bottom", fontsize=8.5, color="#3f7a2a", zorder=4)
    ax.text((0.2 + x_lo) / 2, y0 + hh / 2, t["c_lo"], ha="center", va="center", fontsize=8, color="white", zorder=4)
    ax.text((x_hi + 8.0) / 2, y0 + hh / 2, t["c_hi"], ha="center", va="center", fontsize=8, color="white", zorder=4)
    ax.annotate("", (8.35, y0 + hh / 2), (8.05, y0 + hh / 2), arrowprops=dict(arrowstyle="-|>", color="k", lw=1))
    ax.text(x1, y0 - 0.55, t["c_ratio"], ha="center", va="top", fontsize=8.5, color="k")
    ax.text(0.2, y0 + hh + 1.0, t["c_top"], ha="left", va="center", fontsize=8.5, color="k")
    ax.text(0.2, y0 - 1.15, "thr = " + t["c_thr"], ha="left", va="center", fontsize=8.5, color=C_P)
    ax.text(0.2, y0 - 2.05, t["c_out"], ha="left", va="center", fontsize=8.5, color="#b0481f")
    ax.set_xlim(0, 8.6); ax.set_ylim(-0.6, 3.9)
    ax.set_title(t["c"], loc="left", fontsize=10)


def draw(lang):
    t = T[lang]
    fig, axs = plt.subplots(1, 3, figsize=(10.5, 4.3), gridspec_kw={"width_ratios": [1.25, 1.0, 1.4]})
    panel_enc(axs[0], t); panel_stg(axs[1], t); panel_rk(axs[2], t)
    for ax in axs[:2]:
        ax.set_anchor("N")
    fig.tight_layout(w_pad=0.6)
    return save(fig, "swflow_enc", lang)
