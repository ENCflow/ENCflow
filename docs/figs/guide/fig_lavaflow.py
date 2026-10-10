"""溶岩流(docs/users_guide/lavaflow.md)の説明図: (a) 湧き出し → 流下 → 降伏で停止 → 固化、(b) 固化後の降雨・洪水。

  lavaflow_profile.png
データ不要の模式図(matplotlib のみ)。
"""
import numpy as np
from _style import *

T = {
    "ja": dict(
        ta="(a) 噴火中: 湧き出し → 流下 → 降伏応力で停止 → 固化",
        tb="(b) 固化後: 同じランの中で降雨・洪水が新しい地形の上を流れる",
        vent="噴火口セル lv_cell(i, j)\n噴出率 lv_q0 / lv_val(m³/s)\nセル集合に均等分配(運動量なし)",
        flow="流動: 溶岩面 z + hl の勾配 S に対し\nρg·hl·S > τ_y のエッジだけ流れる\n(lv_rho, 粘度 lv_visc, 降伏応力 lv_tauy)",
        hinf="停止厚 h∞ = τ_y/(ρg tanθ)",
        stop="停止セル(速度 < lv_vsol)\n→ レート lv_wsol で z へ転換\n(固化。不可逆)",
        hl="溶岩厚 hl(出力 Hl)",
        solid="固化した溶岩 = 新しい地盤 z(f_out_z で Z に出る)\n侵食されない岩盤扱い(土層 sd は増えない)",
        rain="降雨・洪水",
        water="地表水は z の上を流れる(流動中の溶岩には不可視。\n相互作用は地形経由のみ。熱・せき止めはなし)",
        tanth="tanθ",
    ),
    "en": dict(
        ta="(a) Eruption: effusion → flow → stop → solidification",
        tb="(b) Afterwards: rain and floods flow over the new terrain",
        vent="vent cells lv_cell(i, j)\nrate lv_q0 / lv_val (m³/s)\nshared equally by the set\n(no momentum)",
        flow="flow: only edges with ρg·hl·S > τ_y\n(S = slope of z + hl;\nlv_rho, lv_visc, lv_tauy)",
        hinf="stop thickness h∞ = τ_y/(ρg tanθ)",
        stop="stopped cells (speed < lv_vsol)\n→ to z at rate lv_wsol\n(solidified, irreversible)",
        hl="lava thickness hl (output Hl)",
        solid="solidified lava = new bed z (Z with f_out_z)\nnon-erodible bedrock (soil sd not increased)",
        rain="rain / flood",
        water="surface water flows on z (moving lava is\ninvisible to it; interaction only through\nthe terrain; no heat, no damming)",
        tanth="tanθ",
    ),
}


def _ground():
    xs = [0, 1.0, 2.5, 4.5, 6.5, 8.2, 10.4]
    zs = [2.6, 2.45, 1.9, 1.2, 0.75, 0.55, 0.5]
    x = np.linspace(0, 10.4, 521)
    return x, np.interp(x, xs, zs)


def _lava_top(x, zb, x0=1.0, x1=7.3):
    hl = np.where((x >= x0) & (x <= x1), 0.22 + 0.33 * np.clip((x - x0) / (x1 - x0), 0, 1), 0.0)
    hl = np.where(x > x1, 0.0, hl)
    return hl


def draw(lang):
    t = T[lang]
    en = lang == "en"
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.3), layout="constrained")
    x, zb = _ground()
    hl = _lava_top(x, zb)
    for ax in axs:
        ax.axis("off"); ax.set_xlim(-0.1, 10.5); ax.set_ylim(-0.2, 4.45)
        ax.fill_between(x, -0.2, zb, color=C_GROUND_L, lw=0, zorder=1)
        ax.plot(x, zb, color="k", lw=1.0, zorder=3)
    # (a)
    ax = axs[0]
    ax.fill_between(x, zb, zb + hl, where=hl > 0, color=C_LAVA, alpha=0.85, lw=0, zorder=2)
    st = (x > 5.9) & (x <= 7.3)
    ax.fill_between(x, zb, zb + hl, where=st, color="none", hatch="///", ec="#7a2a14", lw=0, zorder=2.5)
    ax.fill_between(x, zb - 0.9, zb, where=(x > 1.0) & (x < 1.6), color=C_LAVA, alpha=0.85, lw=0, zorder=2)
    arrow(ax, (1.3, zb[np.argmin(abs(x - 1.3))] - 0.8), (1.3, zb[np.argmin(abs(x - 1.3))] + 0.05), color="#7a2a14", lw=2.0)
    ax.annotate(t["vent"], (1.3, 2.75), (0.05, 3.25), fontsize=7.5 if en else 8.5, ha="left", va="bottom",
                arrowprops=dict(arrowstyle="-", color=C_P, lw=0.7), zorder=8)
    arrow(ax, (2.2, np.interp(2.2, x, zb + hl) + 0.2), (4.8, np.interp(4.8, x, zb + hl) + 0.2), color=C_X, lw=2.2)
    label(ax, 4.6 if en else 4.0, 3.35, t["flow"], color=C_X, fs=7.5 if en else 8.5, ha="left", va="bottom")
    ax.annotate(t["stop"], (6.5, np.interp(6.5, x, zb + hl) - 0.15), (6.0, 2.45) if en else (7.3, 2.45), fontsize=7.5 if en else 8.5, ha="left", va="bottom",
                arrowprops=dict(arrowstyle="-", color=C_P, lw=0.7), zorder=8)
    zf, hf = np.interp(7.3, x, zb), np.interp(7.28, x, hl)
    ax.annotate("", (7.5, zf + hf), (7.5, zf), arrowprops=dict(arrowstyle="<->", color="#7a2a14", lw=1.0))
    label(ax, 7.6, zf + hf / 2 + 0.02, t["hinf"], color="#7a2a14", fs=7.5 if en else 8, ha="left")
    ax.annotate(t["hl"], (3.6, np.interp(3.6, x, zb) + 0.2), (1.0, 0.6), fontsize=7.5 if en else 8, ha="left", va="center",
                color="#7a2a14", arrowprops=dict(arrowstyle="-", color=C_P, lw=0.7), zorder=8)
    ax.set_title(t["ta"], loc="left", fontsize=9 if en else 9.5)
    # (b)
    ax = axs[1]
    zn = zb + hl
    ax.fill_between(x, zb, zn, where=hl > 0, color="#a8655a", lw=0, zorder=2)
    ax.fill_between(x, zb, zn, where=hl > 0, color="none", hatch="///", ec="#5a2a1a", lw=0, zorder=2.5)
    ax.plot(x, zn, color="k", lw=1.2, zorder=3)
    for xr in np.arange(0.3, 10.3, 0.33):
        ax.plot([xr, xr - 0.05], [4.2, 4.0], color=C_C, lw=0.9, alpha=0.8, zorder=4)
    label(ax, 9.8, 3.75, t["rain"], color=C_C, fs=8.5)
    wsurf = zn + 0.1
    ax.fill_between(x, zn, wsurf, color=C_WATER_L, lw=0, zorder=2.8)
    ax.plot(x, wsurf, color=C_WATER, lw=1.0, zorder=3.5)
    for xw in (2.6, 5.2, 8.6):
        arrow(ax, (xw, np.interp(xw, x, wsurf) + 0.22), (xw + 1.0, np.interp(xw + 1.0, x, wsurf) + 0.22), color=C_C, lw=1.8)
    ax.annotate(t["solid"], (5.0, np.interp(5.0, x, zb) + 0.22), (0.05, 0.1), fontsize=7.5 if en else 8.5, ha="left", va="bottom",
                arrowprops=dict(arrowstyle="-", color=C_P, lw=0.7), zorder=8, bbox=dict(fc="white", ec="none", alpha=0.85))
    label(ax, 4.3 if en else 4.6, 2.8 if en else 2.95, t["water"], color=C_C, fs=7.5 if en else 8.5, ha="left", va="bottom")
    ax.set_title(t["tb"], loc="left", fontsize=9 if en else 9.5)
    return save(fig, "lavaflow_profile", lang)
