"""time_axis: 時刻の管理 — 経過秒の時間軸(t0, tt, dt)・表示/出力の間隔と時間窓・暦・再開の延長。"""
from _style import *

T = {"ja": {
    "title": "時間軸は「経過秒」の 1 本(&list_sysparam)",
    "t0": "t0(開始)", "tt": "tt(終了。経過時間ではなく絶対時刻)", "dt": "dt(時間刻み)",
    "steps": "総ステップ数 = (tt − t0)/dt、計算内時刻 t = t0 + dt × ステップ数(画面・ログの time 列)",
    "date": "date0_c = \"2019-10-11 09:00\"\n(t = 0 の暦。暦を使う機能だけが参照。\n この例では t0 = 0)",
    "disp": "画面・ログ\ndt_disp", "file": "分布ファイル\ndt_file", "recrd": "プローブ・測線\ndt_recrd",
    "num": "0000", "nums": ["0001", "0002", "0003", "0004"], "last": "9998",
    "numnote": "(番号と時刻の対応は FILENUMBER.csv。入出力の章)",
    "strec": "st_recrd", "etrec": "et_recrd", "win": "時間窓(st_* 〜 et_*。et = −1 は最後まで)",
    "ext": "再開(f_state_restore = 1): tt を増やして継続\n(時刻・ステップ番号は中断なしランと同一)",
    "c": "文字列指定: tt_c = \"24h\"、dt_file_c = \"10min\"(両方書けば _c が優先)",
}, "en": {
    "title": "A single time axis in elapsed seconds (&list_sysparam)",
    "t0": "t0 (start)", "tt": "tt (end: an absolute time, not a duration)", "dt": "dt (time step)",
    "steps": "number of steps = (tt − t0)/dt,  in-run time t = t0 + dt × steps (the time column of screen / log)",
    "date": "date0_c = \"2019-10-11 09:00\"\n(calendar of t = 0; read only by features\nthat need it. In this example t0 = 0)",
    "disp": "screen / log\ndt_disp", "file": "distributed files\ndt_file", "recrd": "probes / transects\ndt_recrd",
    "num": "0000", "nums": ["0001", "0002", "0003", "0004"], "last": "9998",
    "numnote": "(number ↔ time in FILENUMBER.csv; see the I/O chapter)",
    "strec": "st_recrd", "etrec": "et_recrd", "win": "time window (st_* to et_*; et = −1 means until the end)",
    "ext": "Restart (f_state_restore = 1): increase tt and continue\n(times and step numbers identical to an uninterrupted run)",
    "c": "String form: tt_c = \"24h\", dt_file_c = \"10min\" (the _c version wins if both are given)",
}}


def draw(lang):
    t = T[lang]
    fig, ax = plt.subplots(figsize=(10.5, 4.8)); ax.axis("off")
    x0, x1, xe = 2.1, 8.4, 9.9
    yA, yD, yF, yR = 3.55, 2.55, 1.85, 1.15
    # ---- main axis: t0 .. tt with dt ticks, dashed extension for a restart
    ax.add_patch(FancyArrowPatch((x0 - 0.5, yA), (xe + 0.25, yA), arrowstyle="-|>", mutation_scale=12, color="k", lw=1.5, zorder=3))
    ax.plot([x1, xe], [yA, yA], color=C_G, lw=4, ls=(0, (2, 1.5)), zorder=2, alpha=0.8)
    n = 18; d = (x1 - x0) / n
    for k in range(n + 1):
        ax.plot([x0 + k * d] * 2, [yA - 0.07, yA + 0.07], color=C_P, lw=0.9, zorder=4)
    ax.plot([x0, x1], [yA, yA], "o", color="k", ms=7, zorder=5)
    label(ax, x0, yA + 0.3, t["t0"], fs=10, va="bottom")
    label(ax, x1, yA + 0.3, t["tt"], fs=10, va="bottom")
    # dt bracket between ticks 4 and 5
    xa, xb = x0 + 4 * d, x0 + 5 * d
    ax.annotate("", (xb, yA + 0.2), (xa, yA + 0.2), arrowprops=dict(arrowstyle="<->", color=C_X, lw=1.1, shrinkA=0, shrinkB=0))
    label(ax, (xa + xb) / 2, yA + 0.3, t["dt"], color=C_X, fs=9.5, va="bottom")
    # calendar anchor and restart extension
    label(ax, x0 - 0.5, yA + 0.85, t["date"], color=C_X, fs=9, ha="left", va="bottom")
    label(ax, xe + 0.25, yA + 0.85, t["ext"], color="#3f7a2a", fs=9, ha="right", va="bottom")
    # ---- rows of display / output marks
    for y, key in ((yD, "disp"), (yF, "file"), (yR, "recrd")):
        ax.plot([x0, x1], [y, y], color=C_P, lw=0.8, zorder=1)
        label(ax, x0 - 0.35, y, t[key], color=C_P, fs=9, ha="right")
    # screen / log: dt_disp
    nd = 12
    for k in range(nd + 1):
        ax.plot([x0 + k * (x1 - x0) / nd] * 2, [yD - 0.09, yD + 0.09], color=C_P, lw=1.4, zorder=3)
    # distributed files: dt_file(window = whole run by default)
    nf = 5
    for k in range(nf + 1):
        xk = x0 + k * (x1 - x0) / nf
        ax.plot([xk], [yF], "s", color=C_C, ms=8, zorder=4)
        s = t["num"] if k == 0 else (t["last"] if k == nf else t["nums"][k - 1])
        label(ax, xk, yF - 0.2, s, color=C_C, fs=8.5, va="top")
    label(ax, x1 + 0.12, yF, t["numnote"], color=C_C, fs=8.5, ha="left")
    # probes / transects: dt_recrd inside the window st_recrd..et_recrd
    ws, we = x0 + 1.6, x0 + 4.9
    ax.add_patch(Rectangle((ws, yR - 0.22), we - ws, 0.44, fc=C_B, ec="none", alpha=0.55, zorder=0))
    nr = 11
    for k in range(nr + 1):
        xk = ws + k * (we - ws) / nr
        ax.plot([xk], [yR], "o", color=C_G, ms=5, zorder=4)
    label(ax, ws, yR - 0.3, t["strec"], color="#8a6b17", fs=9, va="top")
    label(ax, we, yR - 0.3, t["etrec"], color="#8a6b17", fs=9, va="top")
    label(ax, (ws + we) / 2, yR - 0.62, t["win"], color="#8a6b17", fs=8.5, va="top")
    # ---- footer
    label(ax, 0.2, 0.12, t["steps"], fs=9, ha="left")
    label(ax, 0.2, -0.22, t["c"], color=C_P, fs=9, ha="left")
    ax.set_xlim(0.0, 10.6); ax.set_ylim(-0.42, 5.0)
    ax.set_title(t["title"], loc="left", fontsize=10)
    fig.tight_layout()
    return save(fig, "time_axis", lang)
