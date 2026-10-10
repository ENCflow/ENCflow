"""家屋破壊・瓦礫(docs/users_guide/bldgdebris.md)の説明図: 3 つの台帳の連鎖と空隙率への帰還。

  bldgdebris_chain.png  家屋ストック wbs → 破壊判定 → 流動瓦礫 hbd → 堆積瓦礫 wbd、沈下分・再流動、gv への帰還
データ不要の模式図(matplotlib のみ)。
"""
from _style import *

T = {
    "ja": dict(
        title="家屋破壊・瓦礫の連鎖(柱状材積 m³/m² の 3 つの台帳と、流れへの帰還)",
        flow="流れ h, V(土砂 hs を含む)\n+ 流動流木 hd(fn_driftwood)\n+ 流動瓦礫 hbd(荷重判定のとき)",
        crit_t="判定量",
        wbs="家屋ストック wbs(不動)\n建物セル(gv < 1)に\nbd_stock0 / fn_bdstock(木造率込み)\nfn_bdfrac = 破壊可能な割合\n出力 Bs = 破壊率",
        crit="破壊判定(2 閾値の線形ランプ = 被害関数の幅)\nf_bdcrit = 1: 浸水深 h + hs(bd_hcrit → bd_hcrit2)\nf_bdcrit = 2: 荷重 (h+(1+s)hs+sg木·hd+sg瓦礫·hbd)·V²\n                  (bd_fcrit → bd_fcrit2。Fd9999 と同じ基底)",
        ramp_y="破壊可能率", ramp_x1="bd_hcrit\nbd_fcrit", ramp_x2="bd_hcrit2\nbd_fcrit2",
        wdes="破壊レート bd_wdes",
        hbd="流動瓦礫 hbd\n水(混合体)と\n同速で移流\n出力 Bf",
        wbd="堆積瓦礫 wbd\n出力 Bd\nBd9999 =\nmax(hbd + wbd)",
        stop="停止: h < 喫水(bd_dlog, bd_sg の浮力平衡)\nまたは V < bd_vstop → レート bd_wstop\n乾燥セルでは全量",
        refloat="再流動 bd_wfloat(既定 0)\nh > bd_rfloat × 喫水 かつ V > bd_vfloat",
        fsink="沈下分 bd_fsink: 破壊量の一部をその場で wbd へ(瓦・基礎の抽象化。0 = 全量浮遊 = 到達の上限側)",
        gv="空隙率への帰還 f_bdgv = 1(既定)\n破壊率に応じて建物の空隙率 gv が上がる(上限 gv0 + (1−gv0)·fw)\nh × gv を保存して水深が縮む = 同じ水が広がり水位が下がる\n(f_bdgv = 0: 片方向結合。瓦礫・破壊率の分布だけ出し流れは変えない)",
    ),
    "en": dict(
        title="The destruction-debris chain (three ledgers of volume per area m³/m², and the feedback to the flow)",
        flow="flow h, V (incl. sediment hs)\n+ floating driftwood hd\n   (fn_driftwood)\n+ floating debris hbd\n   (load criterion)",
        crit_t="criterion",
        wbs="building stock wbs (immobile)\nbuilding cells (gv < 1):\nbd_stock0 / fn_bdstock\n(incl. wooden fraction)\nfn_bdfrac = destructible fraction\noutput Bs = destroyed fraction",
        crit="destruction criterion\n(linear ramp between 2 thresholds = fragility width)\nf_bdcrit = 1: depth h + hs (bd_hcrit → bd_hcrit2)\nf_bdcrit = 2: load (h+(1+s)hs+sg_log·hd+sg_deb·hbd)·V²\n(bd_fcrit → bd_fcrit2; same basis as Fd9999)",
        ramp_y="destructible\nfraction", ramp_x1="bd_hcrit\nbd_fcrit", ramp_x2="bd_hcrit2\nbd_fcrit2",
        wdes="destruction rate bd_wdes",
        hbd="floating\ndebris hbd\nadvected with\nwater (mixture)\noutput Bf",
        wbd="deposited\ndebris wbd\noutput Bd\nBd9999 =\nmax(hbd + wbd)",
        stop="stopping: h < draft (bd_dlog, bd_sg buoyancy)\nor V < bd_vstop → rate bd_wstop\ndry cells: everything deposits",
        refloat="refloating bd_wfloat (default 0)\nh > bd_rfloat × draft and V > bd_vfloat",
        fsink="sinking part bd_fsink: a fraction of the destroyed volume deposits on the spot\n(tiles, foundations; 0 = all floats = upper bound of reach)",
        gv="feedback to the void ratio, f_bdgv = 1 (default)\nthe building void ratio gv rises with the destroyed fraction (up to gv0 + (1−gv0)·fw)\nh × gv is conserved, so the depth shrinks = the same water spreads and the level drops\n(f_bdgv = 0: one-way coupling; debris and damage maps only, the flow is unchanged)",
    ),
}


def box(ax, x0, y0, w, h, text, ec, fc="white", fs=8.5, color="k", lw=1.6):
    ax.add_patch(FancyBboxPatch((x0, y0), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fc, ec=ec, lw=lw, zorder=4))
    ax.text(x0 + w / 2, y0 + h / 2, text, ha="center", va="center", fontsize=fs, color=color, zorder=5)


def draw(lang):
    t = T[lang]
    en = lang == "en"
    fb = 7.2 if en else 8.0            # 箱内の文字
    fl = 7.6 if en else 8.5            # 箱外の注記
    fig, ax = plt.subplots(figsize=(10.5, 5.6), layout="constrained")
    ax.axis("off"); ax.set_xlim(-0.45, 10.55); ax.set_ylim(-0.1, 5.55)
    yB, hB = 2.45, 1.25
    xC0, xC1 = 2.95, 7.3               # 判定の箱
    xH0, xH1 = 7.55, 8.95              # 流動瓦礫
    xW0, xW1 = 9.15, 10.5              # 堆積瓦礫
    # 流れ(判定量の供給)
    box(ax, 0.0, 4.15, 2.6, 1.05, t["flow"], C_C, fc="#eaf2fc", fs=fb)
    # 台帳と判定
    box(ax, 0.0, yB, 2.6, hB, t["wbs"], C_P, fs=fb)
    box(ax, xC0, yB - 0.12, xC1 - xC0, hB + 0.24, t["crit"], "#c9962a", fc="#fdf3dc", fs=fb)
    box(ax, xH0, yB, xH1 - xH0, hB, t["hbd"], C_C, fc="#eaf2fc", fs=fb)
    box(ax, xW0, yB, xW1 - xW0, hB, t["wbd"], C_G, fc="#eef6e8", fs=fb)
    # 矢印: 判定量 → 判定、ストック → 判定 → 流動 → 堆積
    arrow(ax, (2.1, 4.15), (xC0 + 0.25, yB + hB + 0.14), color=C_C, lw=1.6, text=t["crit_t"], dxy=(0.35, 0.1), fs=fl, ha="left")
    arrow(ax, (2.62, yB + hB / 2), (xC0 - 0.02, yB + hB / 2), color=C_X, lw=2.0)
    label(ax, (2.6 + xC0) / 2, yB - 0.32, t["wdes"], color=C_X, fs=fl)
    arrow(ax, (xC1 + 0.02, yB + hB / 2), (xH0 - 0.02, yB + hB / 2), color=C_X, lw=2.0)
    arrow(ax, (xH1 + 0.02, yB + hB / 2), (xW0 - 0.02, yB + hB / 2), color=C_X, lw=2.0)
    label(ax, 8.55, yB + hB + 0.95, t["stop"], color=C_X, fs=fl, va="bottom")
    # 再流動(破線の戻り)
    ax.add_patch(FancyArrowPatch((9.6, yB + hB + 0.02), (8.3, yB + hB + 0.02), connectionstyle="arc3,rad=0.5",
                                 arrowstyle="-|>", mutation_scale=12, color=C_G, lw=1.4, ls="--", zorder=6))
    label(ax, 8.55, yB + hB + 0.52, t["refloat"], color="#3f7a2a", fs=fl)
    # 沈下分: 判定 → 堆積(下を回る)
    yS = yB - 0.65
    xS = (xC0 + xC1) / 2
    ax.plot([xS, xS, 9.8], [yB - 0.12, yS, yS], color=C_X, lw=1.3, ls="--", zorder=3)
    ax.add_patch(FancyArrowPatch((9.8, yS), (9.8, yB - 0.02), arrowstyle="-|>", mutation_scale=12, color=C_X, lw=1.3, ls="--", zorder=6))
    label(ax, 4.0, yS - 0.2, t["fsink"], color=C_X, fs=fl, ha="left", va="top")
    # 破壊可能率のランプ(判定の箱の上)
    rx, ry, rw, rh = 3.35, 4.3, 1.6, 0.75
    ax.plot([rx, rx + rw], [ry, ry], color=C_P, lw=0.8); ax.plot([rx, rx], [ry, ry + rh], color=C_P, lw=0.8)
    ax.plot([rx, rx + 0.45, rx + 1.15, rx + rw], [ry, ry, ry + rh * 0.9, ry + rh * 0.9], color="#c9962a", lw=2.0)
    ax.plot([rx + 0.45, rx + 0.45], [ry, ry + rh * 0.9], color=C_P, lw=0.6, ls=":")
    ax.plot([rx + 1.15, rx + 1.15], [ry, ry + rh * 0.9], color=C_P, lw=0.6, ls=":")
    label(ax, rx + 0.45, ry - 0.07, t["ramp_x1"], fs=7, va="top", color=C_P)
    label(ax, rx + 1.15, ry - 0.07, t["ramp_x2"], fs=7, va="top", color=C_P)
    label(ax, rx - 0.08, ry + rh * 0.9, "1", fs=7.5, ha="right", color=C_P)
    label(ax, rx - 0.08, ry, "0", fs=7.5, ha="right", color=C_P)
    label(ax, rx + rw + 0.1, ry + rh * 0.5, t["ramp_y"], fs=7.5, ha="left", color="#8a6b17")
    # 空隙率への帰還(緑の環)
    box(ax, 0.0, 0.12, 6.9 if en else 6.4, 1.05, t["gv"], C_G, fc="#eef6e8", fs=fb)
    arrow(ax, (1.3, yB - 0.02), (1.3, 1.2), color=C_G, lw=1.8)
    ax.plot([-0.02, -0.3, -0.3], [0.65, 0.65, 4.65], color=C_G, lw=1.8, zorder=3)
    ax.add_patch(FancyArrowPatch((-0.3, 4.65), (-0.02, 4.65), arrowstyle="-|>", mutation_scale=12, color=C_G, lw=1.8, zorder=6))
    ax.set_title(t["title"], loc="left", fontsize=10)
    return save(fig, "bldgdebris_chain", lang)
