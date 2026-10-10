#!/usr/bin/env python3
"""nest_identity: README 用の模式図 figs/identity.png を描く(データ不要)

  使い方: ./Fig.py
  比 1:1 の自己ネスト(子 = 親の部分領域)で nestcheck が毎ステップ比較する領域を示す。
計算本体の外(方針 10)。matplotlib。
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
plt.rcParams.update({"font.family": ["IPAGothic", "DejaVu Sans"], "font.size": 10})
C_P, C_C, C_B, C_X = "#6b6a66", "#2a78d6", "#f2b84b", "#eb6834"

def panel(ax, nxp, nyp, i0, j0, nxc, nyc, nb, title, note, wave=None, label_inside=True):
    ax.set_aspect("equal"); ax.axis("off")
    ax.add_patch(Rectangle((0, 0), nxp, nyp, fc="#f4f4f1", ec=C_P, lw=1.2))
    x0, y0 = i0 - 1, nyp - (j0 - 1) - nyc                      # 子の南西角(y は北を上に)
    ax.add_patch(Rectangle((x0, y0), nxc, nyc, fc=C_B, ec="none", alpha=0.8))
    ax.add_patch(Rectangle((x0 + nb, y0 + nb), nxc - 2 * nb, nyc - 2 * nb, fc="#eaf2fc", ec="none"))
    ax.add_patch(Rectangle((x0, y0), nxc, nyc, fill=False, ec=C_C, lw=1.6))
    if wave:
        cx, cy, rr = wave
        for k, r in enumerate(rr):
            ax.add_patch(Circle((cx, cy), r, fill=False, ec=C_X, lw=1.2, ls="-" if k == 0 else "--"))
    ax.text(nxp / 2, nyp + 0.03 * nyp, title, ha="center", va="bottom", fontsize=10, color="k")
    lab = "子の内部(帯を除く)\n== 親の同じセル\n(毎ステップ・全セル)"
    if label_inside:
        ax.text(x0 + nxc / 2, y0 + nyc / 2, lab, ha="center", va="center", fontsize=8.5, color=C_C)
    else:
        ax.annotate(lab, (x0 + nxc - nb, y0 + nyc - nb), (nxp * 0.72, nyp * 0.9), fontsize=8.5, color=C_C, ha="left", va="center",
                    arrowprops=dict(arrowstyle="-", color=C_C, lw=0.8))
    ax.text(x0 + nxc / 2, y0 - 0.02 * nyp, f"子 {nxc}×{nyc}(親セル {i0}..{i0 + nxc - 1} × {j0}..{j0 + nyc - 1})、帯 nb = {nb}", ha="center", va="top", fontsize=8.5, color=C_C)
    ax.text(nxp / 2, -0.12 * nyp, note, ha="center", va="top", fontsize=8.5, color=C_P)
    ax.set_xlim(-0.02 * nxp, 1.02 * nxp); ax.set_ylim(-0.3 * nyp, 1.12 * nyp)

fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.6), gridspec_kw={"width_ratios": [1, 1.4]})
panel(axs[0], 385, 385, 133, 133, 121, 121, 3, "wave: 親 385×385、比 1:1、dt 同一",
      "中央の盛り上がり(実線)が t ≈ 5 s に帯へ達し(破線)、3 s 間横切る。\n一方向では子の内部 == 親(ULP 0)。双方向では加えてルートの最終状態 == 単独ラン",
      wave=(192.5, 192.5, (20, 60)), label_inside=False)
panel(axs[1], 112, 60, 20, 10, 60, 40, 3, "chichibu: 実地形 500 m、1 時間(乾湿・流出あり)",
      "地形・物性・初期条件は cut_chichibu.py で親から切り出す。\n場の表(地下水 hg・浮遊砂等)の交換と保存修正(fb3)の恒等もこの構成")
fig.suptitle("nest_identity: 比 1:1 の自己ネスト(子 = 親の部分領域)— 子の内部が親と一致することを nestcheck が毎ステップ検査する", x=0.01, ha="left", fontsize=10)
fig.tight_layout(); fig.savefig("figs/identity.png", dpi=150); plt.close(fig)
print("wrote figs/identity.png")
