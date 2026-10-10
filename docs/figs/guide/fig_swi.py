"""土壌雨量指数(直列 3 段タンク)の模式図(swi.md)。定数は src/m_swi.f90 の固定値(気象庁標準)。"""
from _style import *

T = {"ja": {
    "title": "土壌雨量指数(fn_swi): 石原・小葉竹の直列 3 段タンク。SWI = S1 + S2 + S3 (mm)。定数は固定(気象庁標準)",
    "rain": "地上雨量(fn_precip)\n併用できるのは定率遮断 f_icmodel=1 のみ",
    "tank1": "第1タンク S1", "tank2": "第2タンク S2", "tank3": "第3タンク S3",
    "q1": "流出 0.1×(S1−15)", "q2": "流出 0.15×(S1−60)", "q3": "流出 0.05×(S2−15)", "q4": "流出 0.01×(S3−15)",
    "b1": "浸透 0.12×S1", "b2": "浸透 0.05×S2", "b3": "浸透 0.01×S3",
    "out": "側方流出\n(系外)", "outb": "系外",
    "unit": "係数の単位 1/h、孔高 mm", "swi": "SWI = S1+S2+S3",
    "init": "初期貯留 swi0 = (S1, S2, S3)(先行降雨)",
    "outfiles": "出力: Swi0001…(分布)、Swi9999(期間最大)、Swit9999(最大の時刻)。dt ≤ 600 s",
}, "en": {
    "title": "Soil Water Index (fn_swi): Ishihara-Kobatake serial 3-tank model. SWI = S1 + S2 + S3 (mm). Constants fixed (JMA standard)",
    "rain": "ground rainfall (fn_precip)\nonly fixed-rate interception f_icmodel=1 may be combined",
    "tank1": "tank 1  S1", "tank2": "tank 2  S2", "tank3": "tank 3  S3",
    "q1": "outflow 0.1 x (S1−15)", "q2": "outflow 0.15 x (S1−60)", "q3": "outflow 0.05 x (S2−15)", "q4": "outflow 0.01 x (S3−15)",
    "b1": "percolation 0.12 x S1", "b2": "percolation 0.05 x S2", "b3": "percolation 0.01 x S3",
    "out": "lateral outflow\n(leaves the system)", "outb": "leaves system",
    "unit": "coefficients in 1/h, outlet heights in mm", "swi": "SWI = S1+S2+S3",
    "init": "initial storages swi0 = (S1, S2, S3) (antecedent rain)",
    "outfiles": "output: Swi0001... (maps), Swi9999 (period maximum), Swit9999 (time of maximum). dt <= 600 s",
}}


def tank(ax, x, y, w, h, fill, name, holes, t, color=C_WATER_L):
    """タンク(上開き)。holes = [(高さ(0..h), 文)]"""
    ax.plot([x, x, x + w, x + w], [y + h, y, y, y + h], color="k", lw=1.6, zorder=4)
    ax.add_patch(Rectangle((x, y), w, fill, fc=color, ec="none", zorder=2))
    ax.text(x + 0.12, y + h - 0.12, name, fontsize=9, color="k", ha="left", va="top", zorder=5)
    for (hh, s) in holes:
        ax.plot([x + w, x + w + 0.25], [y + hh, y + hh], color="white", lw=4, zorder=4.5)
        arrow(ax, (x + w + 0.05, y + hh), (x + w + 0.9, y + hh), color=C_C, lw=1.8)
        ax.text(x + w + 1.0, y + hh, s, fontsize=8.5, color=C_C, ha="left", va="center", zorder=5)


def draw(lang):
    t = T[lang]
    fig, ax = plt.subplots(figsize=(7.2, 7.4), layout="constrained")
    ax.axis("off"); ax.set_xlim(-0.2, 7.4); ax.set_ylim(-1.95, 8.4)
    X, W = 1.2, 2.2
    # 雨
    for k in range(5):
        arrow(ax, (X + 0.3 + 0.4 * k, 7.75), (X + 0.3 + 0.4 * k, 7.25), color=C_X, lw=1.2)
    label(ax, X + W / 2, 8.05, t["rain"], color=C_X, fs=8.5, va="center")
    # タンク 1: 高さ 2.4、孔 15 mm (0.5)・60 mm (1.6)
    y1 = 4.7
    tank(ax, X, y1, W, 2.4, 1.3, t["tank1"], [(0.5, t["q1"]), (1.6, t["q2"])], t)
    arrow(ax, (X + W / 2, y1 - 0.05), (X + W / 2, y1 - 0.85), color=C_X, lw=2.0, text=t["b1"], dxy=(0.15, 0), ha="left", fs=8.5)
    # タンク 2
    y2 = 2.3
    tank(ax, X, y2, W, 1.6, 0.9, t["tank2"], [(0.5, t["q3"])], t)
    arrow(ax, (X + W / 2, y2 - 0.05), (X + W / 2, y2 - 0.85), color=C_X, lw=2.0, text=t["b2"], dxy=(0.15, 0), ha="left", fs=8.5)
    # タンク 3
    y3 = -0.1
    tank(ax, X, y3, W, 1.6, 0.6, t["tank3"], [(0.5, t["q4"])], t)
    arrow(ax, (X + W / 2, y3 - 0.05), (X + W / 2, y3 - 0.85), color=C_X, lw=2.0, text=t["b3"], dxy=(0.15, 0), ha="left", fs=8.5)
    label(ax, X + W / 2 + 0.15, y3 - 1.15, t["outb"], color=C_P, fs=8, ha="left", va="center")
    # 側方流出のまとめ(右)
    label(ax, 6.9, 3.9, t["out"], color=C_C, fs=8.5, ha="right", va="center")
    label(ax, 6.9, 0.1, t["unit"], color=C_P, fs=7.5, ha="right", va="center")
    # SWI の括弧(左)
    ax.plot([X - 0.35, X - 0.5, X - 0.5, X - 0.35], [y1 + 2.4, y1 + 2.4, y3, y3], color="k", lw=1.2, zorder=4)
    ax.text(X - 0.6, (y1 + 2.4 + y3) / 2, t["swi"], fontsize=9.5, color="k", ha="center", va="center", rotation=90, zorder=5)
    # 注
    label(ax, -0.1, -1.7, t["init"] + "\n" + t["outfiles"], color=C_P, fs=7.8, ha="left", va="center")
    ax.set_title(t["title"], loc="left", fontsize=8.6, wrap=True)
    return save(fig, "swi_tanks", lang)
