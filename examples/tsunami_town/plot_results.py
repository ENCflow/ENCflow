#!/usr/bin/env python3
"""tsunami_town の図と数表(事前に make run で 4 ケース、make supp で補足の 3 ケースを計算しておく)。

  figs/mechanism.png 津波で家屋が壊れ、瓦礫が運ばれる仕組みと、浸水深による被害関数の模式図
  figs/setup.png     地形と防潮堤・開口部、家屋ストック(木造率込み)、津波の波形と防潮堤の天端
  figs/maps.png      4 ケースの最大浸水深・家屋の破壊率・瓦礫の堆積
  figs/series.png    家屋の破壊の進み方と、瓦礫の行き先(4 ケース)
  figs/supp_damage.png  補足: 判定の方法・流木・空隙率への帰還による破壊率の違い
  figs/supp_ledger.png  補足: 残る家屋と流れている瓦礫の時間変化
引数 en で英語ラベル版を en/figs/ に描く(データと描画処理は共通)。
"""
import glob
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)

NX, NY, DX = 120, 60, 10.0
A = DX * DX
EXT = [0, NX * DX, NY * DX, 0]                 # 行 1 = 北を上に
X = (np.arange(NX) + 0.5) * DX
Y = (np.arange(NY) + 0.5) * DX
I_WALL, J_OPEN, I_TOWN = (26, 27), (25, 36), 28   # make_terrain.py と同じ(1 始まり)
ZONES = [(T("海側", "seaward"), 270, 500), (T("中ほど", "middle"), 500, 800), (T("内陸", "inland"), 800, 1200)]
CASES = [("t4", T("津波 +4 m・防潮堤 +2 m", "tsunami +4 m, seawall +2 m"), 4.0, 2.0, True, "#c0392b", "-"),
         ("t3", T("津波 +3 m・防潮堤 +2 m", "tsunami +3 m, seawall +2 m"), 3.0, 2.0, True, "#e08214", "--"),
         ("wall3", T("防潮堤 +3 m・開口部あり", "seawall +3 m, opening open"), 4.0, 3.0, True, "#1f5f8b", "-."),
         ("wall3c", T("防潮堤 +3 m・開口部も閉じる", "seawall +3 m, opening closed"), 4.0, 3.0, False, "#2b8a3e", ":")]
SUPP = [("t4", T("本体(浸水深で判定)", "main (depth criterion)"), "#c0392b"),
        ("oneway", T("壊れても空隙率を上げない", "porosity not raised by destruction"), "#8a8983"),
        ("load", T("流体力 hV² で判定", "load hV² criterion"), "#2b8a3e"),
        ("load_dw", T("流体力で判定+流木", "load criterion + driftwood"), "#e08214")]
C_SEA, C_GROUND, C_HOUSE, C_DEBRIS = "#7fb2e5", "#d9c7a0", "#8c564b", "#a0522d"


def rd(path):
    return np.loadtxt(path)


def frames(case):
    out = {}
    for line in open(f"result_{case}/FILENUMBER.csv"):
        if line.startswith("#"):
            continue
        f = line.split(",")
        if int(f[0]) < 9000:
            out[int(f[0])] = float(f[2]) / 60.0
    return out


def field(case, var, k):
    return rd(f"result_{case}/{var}{k:04d}.txt")


def k_at(case, tmin):
    fr = frames(case)
    return min(fr, key=lambda k: abs(fr[k] - tmin))


def ledger(case):
    """bldgdebris.csv: 時刻(分)、破壊した量、残る家屋、流れている瓦礫、積もった瓦礫 (m3)。"""
    d = np.loadtxt(f"result_{case}/bldgdebris.csv", delimiter=",", skiprows=1)
    return d[:, 0] / 60.0, d[:, 1] + d[:, 2], d[:, 6], d[:, 7], d[:, 8]


def tide(peak):
    t = np.array([0, 5, 15, 25, 35, 60])
    return t, np.array([0, 0, peak, peak, 0, 0])


def draw_wall(ax, crest_open=True, lw=1.0):
    x0, x1 = (I_WALL[0] - 1) * DX, I_WALL[1] * DX
    y0, y1 = (J_OPEN[0] - 1) * DX, J_OPEN[1] * DX
    for ys in ((0, y0), (y1, NY * DX)):
        ax.fill_betweenx(ys, x0, x1, color="k")
    if crest_open:
        ax.plot([x0, x1, x1, x0, x0], [y0, y0, y1, y1, y0], "k--", lw=lw * 0.8)
    else:
        ax.fill_betweenx((y0, y1), x0, x1, color="k")


# ---------------------------------------------------------------- 模式図
def _house(ax, x, y, w=0.55, h=0.5, broken=False):
    if broken:
        for k in range(4):
            ax.add_patch(plt.Rectangle((x + 0.12 * k, y + 0.05 * (k % 2)), 0.12, 0.06, color=C_DEBRIS, angle=20 * k))
    else:
        ax.add_patch(plt.Rectangle((x, y), w, h, facecolor="w", edgecolor=C_HOUSE, lw=1.2))
        ax.add_patch(plt.Polygon([(x - 0.05, y + h), (x + w / 2, y + h + 0.3), (x + w + 0.05, y + h)], color=C_HOUSE))


def mechanism():
    fig = plt.figure(figsize=(13, 5.6))
    gs = fig.add_gridspec(1, 2, width_ratios=[2.3, 1])
    ax = fig.add_subplot(gs[0])
    x = np.linspace(0, 12, 601)
    ground = np.where(x < 2.6, -2.0 + 2.0 * x / 2.6, 0.5 + 2.3 * (x - 2.6) / 9.4)
    ground = np.where((x > 2.6) & (x < 2.9), 2.0, ground)                    # 防潮堤
    ax.fill_between(x, -2.6, ground, color=C_GROUND)
    surf = np.where(x < 2.6, 4.0, 4.0 - 0.9 * (x - 2.6) / 9.4)
    ax.fill_between(x, ground, np.maximum(surf, ground), color=C_SEA, alpha=0.55)
    ax.plot(x, np.maximum(surf, ground), color="#2a78d6", lw=1.5)
    ax.annotate("", xy=(2.4, 4.4), xytext=(0.3, 4.4), arrowprops=dict(arrowstyle="-|>", color="#2a78d6", lw=2.5))
    ax.text(0.3, 4.65, T("津波の押し波", "tsunami inflow"), fontsize=9, color="#2a78d6")
    ax.text(2.75, 2.25, T("防潮堤", "seawall"), fontsize=8, ha="center", rotation=90, va="bottom")
    for xh in (3.4, 4.3, 5.2, 6.1):
        _house(ax, xh, np.interp(xh, x, ground), broken=True)
    for xh in (8.0, 9.1, 10.2, 11.2):
        _house(ax, xh, np.interp(xh, x, ground))
    ax.annotate("", xy=(7.9, 3.0), xytext=(5.0, 3.0), arrowprops=dict(arrowstyle="-|>", color=C_DEBRIS, lw=2))
    ax.text(5.0, 3.2, T("瓦礫が流れに乗って内陸へ", "debris carried inland"), fontsize=9, color=C_DEBRIS)
    ax.annotate("", xy=(0.4, 1.4), xytext=(3.6, 1.4), arrowprops=dict(arrowstyle="-|>", color=C_DEBRIS, lw=2, ls="--"))
    ax.text(0.4, 0.75, T("引き波で海へ", "backwash carries it to sea"), fontsize=9, color=C_DEBRIS)
    ax.annotate("", xy=(3.4, 4.25), xytext=(3.4, np.interp(3.4, x, ground) + 0.7),
                arrowprops=dict(arrowstyle="<->", color="k", lw=1))
    ax.text(3.5, 3.0, T("浸水深が\n2 m を超えると\n壊れて流される", "over 2 m deep:\nhouses break\nand wash away"), fontsize=8)
    ax.text(8.0, 3.8, T("浅い所・RC 造の多い所は残る", "shallow areas and RC buildings remain"), fontsize=9)
    ax.set_xlim(0, 12)
    ax.set_ylim(-2.6, 5.2)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(T("(a) 津波の遡上と家屋の破壊・瓦礫(横断の模式)", "(a) Tsunami run-up, house destruction and debris (schematic section)"), fontsize=10, loc="left")
    ax = fig.add_subplot(gs[1])
    h = np.linspace(0, 5, 201)
    ramp = np.clip((h - 1.0) / 2.0, 0, 1)
    ax.plot(h, ramp, color="#c0392b", lw=2.2, label=T("このモデル: 壊れる速さの倍率", "this model: rate multiplier"))
    from math import erf, log, sqrt
    curve = [0.0 if v <= 0 else 0.5 * (1 + erf((log(v) - log(2.0)) / (0.4 * sqrt(2)))) for v in h]
    ax.plot(h, curve, color="0.4", lw=1.5, ls="--", label=T("被害関数の形(模式。中央値 2 m)", "shape of a fragility curve (schematic, median 2 m)"))
    ax.axvline(2.0, color="0.6", lw=0.8)
    ax.set_xlabel(T("浸水深 (m)", "inundation depth (m)"))
    ax.set_ylabel(T("倍率 / 被害の割合", "multiplier / damage fraction"))
    ax.set_title(T("(b) 浸水深による家屋の破壊", "(b) House destruction by inundation depth"), fontsize=10, loc="left")
    ax.legend(fontsize=8, loc="lower right")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/mechanism.png", dpi=100)
    plt.close(fig)


# ---------------------------------------------------------------- 設定
def setup():
    z = rd("z.txt")
    st = rd("bdstock.txt")
    fig, axs = plt.subplots(1, 3, figsize=(16, 4.2), gridspec_kw=dict(width_ratios=[1.35, 1.35, 1]), constrained_layout=True)
    ax = axs[0]
    im = ax.imshow(z, extent=EXT, cmap="terrain", vmin=-6, vmax=6)
    draw_wall(ax)
    ax.text(75, 300, T("海\n−5 m", "sea\n−5 m"), ha="center", va="center", fontsize=8)
    ax.text(205, 300, T("浜", "beach"), ha="center", va="center", fontsize=8)
    ax.annotate(T("開口部(幅 120 m、+0.5 m)", "opening (120 m wide, +0.5 m)"), xy=(265, 300), xytext=(420, 330), fontsize=8,
                arrowprops=dict(arrowstyle="-", lw=0.8))
    ax.text(740, 80, T("市街地 +0.5 → +3.0 m", "town +0.5 → +3.0 m"), ha="center", fontsize=8)
    ax.set_title(T("地形と防潮堤(天端 +2 m。黒)", "Terrain and seawall (crest +2 m, black)"), fontsize=10)
    fig.colorbar(im, ax=ax, shrink=0.85).set_label(T("地盤高 (m)", "ground elevation (m)"))
    ax = axs[1]
    im = ax.imshow(np.where(st > 0, st, np.nan), extent=EXT, cmap="YlOrBr", vmin=0, vmax=0.3)
    draw_wall(ax)
    for name, x0, x1 in ZONES:
        ax.axvline(x1, color="0.5", lw=0.6, ls=":")
        ax.text((x0 + x1) / 2, 30, name, ha="center", fontsize=8)
    ax.set_title(T("壊れうる家屋ストック(木造率: 海側 100 % → 内陸 40 %)", "Destructible house stock (wooden share 100 % → 40 %)"), fontsize=10)
    fig.colorbar(im, ax=ax, shrink=0.85).set_label("m³/m²")
    for ax in axs[:2]:
        ax.set_xlabel("x (m)")
        ax.set_ylabel("y (m)")
    ax = axs[2]
    for peak, col, ls in ((4.0, "#c0392b", "-"), (3.0, "#e08214", "--")):
        t, e = tide(peak)
        ax.plot(t, e, ls, color=col, lw=2, label=T(f"津波 +{peak:.0f} m(沖の水位)", f"tsunami +{peak:.0f} m (offshore level)"))
    ax.axhline(2.0, color="k", lw=1.2, label=T("防潮堤の天端 +2 m", "seawall crest +2 m"))
    ax.axhline(3.0, color="k", lw=1.2, ls="-.", label=T("かさ上げした天端 +3 m", "raised crest +3 m"))
    ax.axhline(0.5, color="k", lw=0.8, ls="--", label=T("開口部 +0.5 m", "opening +0.5 m"))
    ax.set_xlim(0, 60)
    ax.set_ylim(-0.3, 5)
    ax.set_xlabel(T("時刻 (分)", "time (min)"))
    ax.set_ylabel(T("水位 (m)", "water level (m)"))
    ax.set_title(T("津波の波形と防潮堤の天端", "Tsunami waveform and seawall crests"), fontsize=10)
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(alpha=0.3)
    fig.savefig(f"{FIGDIR}/setup.png", dpi=100)
    plt.close(fig)


# ---------------------------------------------------------------- 結果
def maps():
    st = rd("bdstock.txt")
    fig, axs = plt.subplots(3, 4, figsize=(17, 8.6), constrained_layout=True)
    lv = [0.01, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0]
    cmap = plt.get_cmap("Blues", len(lv) + 1)
    norm = BoundaryNorm(lv, cmap.N, extend="max")
    for col, (case, lab, peak, crest, op, c, ls) in enumerate(CASES):
        kl = max(frames(case))
        h = rd(f"result_{case}/H9999.txt")
        im0 = axs[0, col].imshow(np.where(h > 0.01, h, np.nan), extent=EXT, cmap=cmap, norm=norm)
        bs = field(case, "Bs", kl)
        im1 = axs[1, col].imshow(np.where(st > 0, bs, np.nan), extent=EXT, cmap="Reds", vmin=0, vmax=1)
        bd = field(case, "Bd", kl)
        im2 = axs[2, col].imshow(np.where(bd > 0.002, bd, np.nan), extent=EXT, cmap="YlOrBr", vmin=0, vmax=0.3)
        axs[0, col].set_title(lab, fontsize=10)
        for r in range(3):
            draw_wall(axs[r, col], op)
            axs[r, col].set_xticks([0, 400, 800, 1200])
            if col:
                axs[r, col].set_yticks([])
        axs[2, col].set_xlabel("x (m)")
    axs[0, 0].set_ylabel(T("最大浸水深\ny (m)", "max depth\ny (m)"))
    axs[1, 0].set_ylabel(T("家屋の破壊率(60 分)\ny (m)", "houses destroyed (60 min)\ny (m)"))
    axs[2, 0].set_ylabel(T("積もった瓦礫(60 分)\ny (m)", "deposited debris (60 min)\ny (m)"))
    fig.colorbar(im0, ax=axs[0, :], shrink=0.9, pad=0.01).set_label("m")
    fig.colorbar(im1, ax=axs[1, :], shrink=0.9, pad=0.01).set_label(T("破壊率", "fraction"))
    fig.colorbar(im2, ax=axs[2, :], shrink=0.9, pad=0.01, extend="max").set_label("m³/m²")
    fig.savefig(f"{FIGDIR}/maps.png", dpi=95)
    plt.close(fig)


def fate(case):
    """60 分の瓦礫の行き先 (m3): 市街地・防潮堤に積もった、浜・海に積もった、流れている、沖へ出た。"""
    st = rd("bdstock.txt")
    fr = rd("bdfrac.txt")
    gv0 = rd("gv.txt")
    kl = max(frames(case))
    bs = field(case, "Bs", kl)
    gv = gv0 + (1.0 - gv0) * fr * bs                            # 破壊で上がった空隙率(帰還あり)
    if case == "oneway":
        gv = gv0
    dep = field(case, "Bd", kl) * gv * A
    t, destroyed, left, flo, depo = ledger(case)
    total = st.sum() * A
    return dict(destroyed=destroyed[-1], town=dep[:, I_WALL[0] - 1:].sum(), sea=dep[:, :I_WALL[0] - 1].sum(),
                floating=flo[-1], out=max(total - (left[-1] + flo[-1] + depo[-1]), 0.0), total=total)


def series():
    fig, axs = plt.subplots(1, 2, figsize=(15, 4.6), constrained_layout=True, gridspec_kw=dict(width_ratios=[1.3, 1]))
    ax = axs[0]
    total = rd("bdstock.txt").sum() * A
    for case, lab, peak, crest, op, c, ls in CASES:
        t, destroyed, left, flo, depo = ledger(case)
        ax.plot(t, destroyed / total * 100, ls, color=c, lw=2, label=lab)
    ax.axvspan(25, 35, color="0.9")
    ax.text(30, 3, T("引き波", "backwash"), ha="center", fontsize=8)
    ax.axvspan(15, 25, color="#e8f0fa")
    ax.text(20, 3, T("押し波の最大", "peak inflow"), ha="center", fontsize=8)
    ax.set_xlim(0, 60)
    ax.set_ylim(0, 105)
    ax.set_xlabel(T("時刻 (分)", "time (min)"))
    ax.set_ylabel(T("壊れた家屋 (%)", "houses destroyed (%)"))
    ax.set_title(T("家屋の破壊の進み方", "Progress of house destruction"), fontsize=10)
    ax.legend(fontsize=8, loc="center right")
    ax.grid(alpha=0.3)
    ax = axs[1]
    parts = [("town", T("市街地に積もる", "deposited in the town"), C_DEBRIS),
             ("sea", T("浜・海に積もる", "deposited on the beach and sea"), "#d9a066"),
             ("floating", T("流れている", "still floating"), "#f2d0a4"),
             ("out", T("沖へ出る", "carried offshore"), "#2a78d6")]
    for r, (case, lab, peak, crest, op, c, ls) in enumerate(CASES):
        f = fate(case)
        x0 = 0.0
        for key, name, col in parts:
            v = f[key] / 1000.0
            ax.barh(r, v, left=x0, color=col, edgecolor="w", label=name if r == 0 else None)
            if v > 6:
                ax.text(x0 + v / 2, r, f"{v:.0f}", ha="center", va="center", fontsize=8)
            x0 += v
    ax.set_yticks(range(len(CASES)))
    ax.set_yticklabels([lab for _, lab, *_ in CASES], fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel(T("瓦礫 (千 m³。家屋ストックは計 117 千 m³)", "debris (1000 m³; house stock 117,000 m³ in total)"))
    ax.set_title(T("60 分の瓦礫の行き先", "Where the debris is at 60 min"), fontsize=10)
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, frameon=False)
    fig.savefig(f"{FIGDIR}/series.png", dpi=100)
    plt.close(fig)


def supp():
    st = rd("bdstock.txt")
    fig, axs = plt.subplots(2, 2, figsize=(12, 6.2), constrained_layout=True)
    for ax, (case, lab, c) in zip(axs.flat, SUPP):
        kl = max(frames(case))
        bs = field(case, "Bs", kl)
        im = ax.imshow(np.where(st > 0, bs, np.nan), extent=EXT, cmap="Reds", vmin=0, vmax=1)
        draw_wall(ax)
        vol = (bs * st * A).sum()
        ax.set_title(T(f"{lab}: 破壊 {vol / 1000:.0f} 千 m³({vol / (st.sum() * A) * 100:.0f} %)",
                       f"{lab}: {vol / 1000:.0f}k m³ destroyed ({vol / (st.sum() * A) * 100:.0f} %)"), fontsize=9)
    for ax in axs[1]:
        ax.set_xlabel("x (m)")
    for ax in axs[:, 0]:
        ax.set_ylabel("y (m)")
    fig.colorbar(im, ax=axs, shrink=0.8).set_label(T("家屋の破壊率(60 分)", "houses destroyed (60 min)"))
    fig.savefig(f"{FIGDIR}/supp_damage.png", dpi=100)
    plt.close(fig)
    fig, axs = plt.subplots(1, 2, figsize=(13, 4), constrained_layout=True)
    for case, lab, c in SUPP:
        t, destroyed, left, flo, depo = ledger(case)
        axs[0].plot(t, left / 1000, color=c, lw=1.8, label=lab)
        axs[1].plot(t, flo / 1000, color=c, lw=1.8, label=lab)
    axs[0].set_ylabel(T("残っている家屋ストック (千 m³)", "remaining house stock (1000 m³)"))
    axs[1].set_ylabel(T("流れている瓦礫 (千 m³)", "floating debris (1000 m³)"))
    for ax in axs:
        ax.set_xlim(0, 60)
        ax.set_xlabel(T("時刻 (分)", "time (min)"))
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    fig.savefig(f"{FIGDIR}/supp_ledger.png", dpi=100)
    plt.close(fig)


def table():
    st = rd("bdstock.txt")
    total = st.sum() * A
    print(T("ケース | 最大浸水深(市街地の最大 / 平均) | 2 m 以上の面積 | 破壊率(全体 / 海側 / 中ほど / 内陸) | 35 分の破壊率 | 市街地に積もる | 浜・海に積もる | 流れている | 沖へ出る",
            "case | max depth (town max / mean) | area >= 2 m | destroyed (all / seaward / middle / inland) | destroyed at 35 min | in town | beach and sea | floating | offshore"))
    for case, lab, *_ in CASES + [(c, l, None, None, None, None, None) for c, l, _ in SUPP[1:]]:
        kl = max(frames(case))
        h = rd(f"result_{case}/H9999.txt")[:, I_TOWN - 1:]
        bs = field(case, "Bs", kl)
        zs = [(bs * st)[:, (X > a) & (X < b)].sum() / st[:, (X > a) & (X < b)].sum() * 100 for _, a, b in ZONES]
        b35 = field(case, "Bs", k_at(case, 35))
        f = fate(case)
        print(f"{lab} | {h.max():.2f} / {h.mean():.2f} m | {(h > 2).mean() * 100:.0f} % | {f['destroyed'] / total * 100:.0f} / "
              f"{zs[0]:.0f} / {zs[1]:.0f} / {zs[2]:.0f} % | {(b35 * st).sum() / st.sum() * 100:.0f} % | {f['town']:.0f} | {f['sea']:.0f} | "
              f"{f['floating']:.0f} | {f['out']:.0f}")


if __name__ == "__main__":
    mechanism()
    setup()
    if all(os.path.exists(f"result_{c}/FILENUMBER.csv") for c, *_ in CASES):
        maps()
        series()
        table()
    if all(os.path.exists(f"result_{c}/FILENUMBER.csv") for c, _, _ in SUPP):
        supp()
