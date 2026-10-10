"""restart_modes: 中断と再開 — 保存(f_state_save)と、再開(f_state_restore = 1、時刻継続)/ 初期条件として利用(= 2、新しい時間軸)。"""
from _style import *

T = {"ja": {
    "title": "状態保存 save/ と、2 つの復元モード",
    "run1": "保存側のラン\nf_state_save = 1", "t0": "t0", "tt": "tt", "save": "save/\n(計算終了時に保存)",
    "saved": "保存内容: 場(水深・地形 …)+ 力学の内部状態(エッジの流速・流量)+ 内部状態を持つモジュールの私有状態",
    "run2": "再開\nf_state_restore = 1", "tt2": "tt(延長)", "cont": "時間軸は継続",
    "m1": "時刻・ステップ番号・出力ファイルの番号まで\n中断なしランと同一。結果はビット単位で一致。\nt0・dt は保存時と同じ。最大値統計(H9999 系)と\n積算流量はゼロから再集計",
    "chain": "終了時に再び\nsave/ へ\n(リスタート連鎖)",
    "run3": "初期条件として利用\nf_state_restore = 2", "newt0": "新しい t0・date0_c から最初のステップを開始\n(dt の変更も可)",
    "sc": ["シナリオ A", "シナリオ B"],
    "m2": "場だけを引き継ぐ(典型は助走後のシナリオ分岐)。時系列強制(潮位・流入・降雨)は新しい時間軸の\n先頭から読まれる — 保存状態との整合は利用者の責務",
    "f0000": "0000 = 復元状態",
}, "en": {
    "title": "State save to save/ and the two restore modes",
    "run1": "saving run\nf_state_save = 1", "t0": "t0", "tt": "tt", "save": "save/\n(written at the end of the run)",
    "saved": "Saved: fields (depth, topography, …) + internal state of the dynamics (edge velocities, discharges)\n+ private state of modules that hold internal state",
    "run2": "restart\nf_state_restore = 1", "tt2": "tt (extended)", "cont": "time axis continues",
    "m1": "Times, step numbers and output file numbers identical\nto an uninterrupted run; results match bit for bit.\nt0 and dt as at save time. Maximum statistics (H9999\nfamily) and cumulative discharge restart from zero",
    "chain": "saved again to\nsave/ at the end\n(restart chain)",
    "run3": "use as initial condition\nf_state_restore = 2", "newt0": "a new time axis from its first step: new t0, date0_c\n(dt may change)",
    "sc": ["scenario A", "scenario B"],
    "m2": "Only the fields are carried over (typically scenario branching after spin-up). Time-series forcings (tide, inflow,\nrain) are read from the start of the new axis — consistency with the saved state is up to the user",
    "f0000": "0000 = restored state",
}}


def draw(lang):
    t = T[lang]
    fig, ax = plt.subplots(figsize=(10.5, 5.8)); ax.axis("off")
    xl = 2.3                       # left edge of the time lines
    xs = 6.2                       # x of the save point (tt of the saving run)
    xr = 9.5                       # right end of the continued / new axes
    xb = xs + 1.8                  # centre of the save/ box
    y1, y2, yA, yB = 4.9, 3.1, 1.45, 0.65
    def tline(y, xa, xb_, color, lw=2.5, ls="-"):
        ax.plot([xa, xb_], [y, y], color=color, lw=lw, ls=ls, solid_capstyle="round", zorder=2)
    # ---------------- saving run
    label(ax, xl - 0.2, y1 + 0.62, t["saved"], color=C_P, fs=8.5, ha="left", va="bottom")
    tline(y1, xl, xs, C_P)
    ax.plot([xl, xs], [y1, y1], "o", color=C_P, ms=7, zorder=3)
    label(ax, xl - 0.2, y1, t["run1"], color=C_P, fs=9.5, ha="right")
    label(ax, xl, y1 + 0.22, t["t0"], color=C_P, fs=10, va="bottom")
    label(ax, xs, y1 + 0.22, t["tt"], color=C_P, fs=10, va="bottom")
    ax.add_patch(FancyBboxPatch((xb - 1.35, y1 - 0.34), 2.7, 0.68, boxstyle="round,pad=0.05", fc=C_B, ec="none", alpha=0.9, zorder=3))
    label(ax, xb, y1, t["save"], color="#5a4610", fs=8.8, z=8)
    arrow(ax, (xs + 0.1, y1), (xb - 1.4, y1), C_X, lw=1.8)
    # ---------------- mode 1: continue from tt
    arrow(ax, (xb - 0.3, y1 - 0.42), (xs + 0.12, y2 + 0.18), C_X, lw=1.6, ls="--")
    tline(y2, xl, xs, C_P, lw=1.2, ls=(0, (2, 2)))
    tline(y2, xs, xr, C_C)
    ax.plot([xs, xr], [y2, y2], "o", color=C_C, ms=7, zorder=3)
    label(ax, xl - 0.2, y2, t["run2"], color=C_C, fs=9.5, ha="right")
    label(ax, xs - 0.12, y2 + 0.2, t["f0000"], color=C_C, fs=8.5, ha="right", va="bottom")
    label(ax, xr, y2 + 0.22, t["tt2"], color=C_C, fs=10, va="bottom")
    label(ax, (xs + xr) / 2 + 0.5, y2 - 0.22, t["cont"], color=C_C, fs=9, va="top")
    label(ax, xl - 0.2, y2 - 0.5, t["m1"], color=C_C, fs=8.5, ha="left", va="top")
    arrow(ax, (xr + 0.1, y2 + 0.12), (xr - 0.25, y1 - 0.46), "#8a6b17", lw=1.3, ls="--")
    label(ax, xr + 0.2, (y1 + y2) / 2 + 0.05, t["chain"], color="#8a6b17", fs=8, ha="left")
    # ---------------- mode 2: new time axis, branched from the saved state
    arrow(ax, (xb + 0.3, y1 - 0.42), (xs + 0.12, yA + 0.2), C_X, lw=1.6, ls="--")
    label(ax, xl - 0.2, (yA + yB) / 2, t["run3"], color="#3f7a2a", fs=9.5, ha="right")
    for y, name in zip((yA, yB), t["sc"]):
        tline(y, xs, xr, C_G)
        ax.plot([xs], [y], "o", color=C_G, ms=7, zorder=3)
        label(ax, xr + 0.15, y, name, color="#3f7a2a", fs=9, ha="left")
    label(ax, xs - 0.12, yA + 0.2, t["newt0"], color="#3f7a2a", fs=8.5, ha="right", va="bottom")
    label(ax, xl - 0.2, yB - 0.4, t["m2"], color="#3f7a2a", fs=8.5, ha="left", va="top")
    ax.set_xlim(-0.2, 10.9); ax.set_ylim(-0.6, 6.0)
    ax.set_title(t["title"], loc="left", fontsize=10)
    fig.tight_layout()
    return save(fig, "restart_modes", lang)
