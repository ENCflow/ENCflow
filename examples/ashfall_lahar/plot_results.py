#!/usr/bin/env python3
"""ashfall_lahar の図と数表(事前に make run で 4 ケースを計算しておく)。

  figs/mechanism.png 噴火前の雨・降灰後の泥流・砂防堰堤の機構の模式図(データを使わない)
  figs/setup.png     地形と降灰厚(平面)、谷筋の縦断、雨と浸透能
  figs/maps.png      地形変化(侵食・堆積)と最大流動深(降灰、降灰+砂防堰堤)
  figs/profile.png   谷筋の縦断: 終了時の侵食・堆積と、流れの濃度の最大
  figs/series.png    谷出口・扇状地の流動深と、扇状地に届いた土砂・堰堤にたまった土砂の時間変化
引数 en で英語ラベル版を en/figs/ に描く(データと描画処理は共通)。
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)

DX, NX, NY = 5.0, 120, 30
J = 15                                    # 谷筋の行(0 始まり。y = 77.5 m)
I_DAM = 57                                # 堤体の列(0 始まり。x = 287.5 m)
X_SEC1, X_SEC2 = 250.0, 355.0              # フラックス測線の位置(谷の中、扇状地。param の flxy と対)
XAPEX, LAM = 300.0, 0.5                   # 谷出口の x、降灰層の空隙率
X = (np.arange(NX) + 0.5) * DX
Y = (np.arange(NY) + 0.5) * DX
A = DX * DX
EXT = [0, NX * DX, 0, NY * DX]
CASES = [("preeruption", T("噴火前(降灰なし)", "before the eruption (no ash)"), "#2b8a3e", ":"),
         ("water", T("降灰・土砂を運ばない(清水の対照)", "ash, no sediment transport (clear-water control)"), "#6baed6", "--"),
         ("ash", T("降灰(泥流)", "ash (lahar)"), "#8c5a2b", "-"),
         ("dam", T("降灰+砂防堰堤", "ash + check dam"), "#c0392b", "-.")]
LAB = {c: l for c, l, _, _ in CASES}
C_SOIL, C_ASH, C_CRUST = "#cdb98f", "#b5b5b5", "#4d4d4d"
C_WATER, C_LAHAR, C_DEP = "#6baed6", "#8c5a2b", "#c99a63"


def rd(case, name, k):
    return np.loadtxt(f"result_{case}/{name}{k:04d}.txt")


def times(case):
    """出力番号 → 時刻 (s)。"""
    out = {}
    for line in open(f"result_{case}/FILENUMBER.csv"):
        if line.startswith("#"):
            continue
        f = line.split(",")
        if int(f[0]) < 9000:
            out[int(f[0])] = float(f[2])
    return out


# ---------------------------------------------------------------- 模式図
def _arrow(ax, x0, y0, x1, y1, color, lw=2.0, style="-|>"):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw, shrinkA=0, shrinkB=0))


def _ground(x):
    """模式の地形: 急な山腹(x < 5.5)→ 緩い扇状地。"""
    return np.where(x < 5.5, 6.0 - x, 0.5 - 0.1 * (x - 5.5))


def _panel(ax, kind):
    """kind: 'pre'(噴火前)、'ash'(降灰後)、'dam'(降灰後+砂防堰堤)。"""
    x = np.linspace(0, 10, 501)
    g = _ground(x)
    ax.fill_between(x, -1.2, g - 0.35, color="0.85")
    ax.fill_between(x, g - 0.35, g, color=C_SOIL)
    top = g
    if kind != "pre":
        ash = np.where(x < 5.5, 0.32 - 0.04 * x, 0.06)
        top = g + ash
        ax.fill_between(x, g, top, color=C_ASH)
        ax.plot(x, top, color=C_CRUST, lw=1.6)
    for xr in np.arange(0.4, 10, 0.7):                                   # 雨
        ax.plot([xr, xr - 0.15], [7.2, 6.75], color=C_WATER, lw=1)
    if kind == "pre":
        for xi in (1.0, 2.5, 4.0, 7.0, 8.5):
            gi = float(_ground(np.array([xi]))[0])
            _arrow(ax, xi, gi + 0.55, xi, gi - 0.25, C_WATER, lw=2.2)
        ax.text(0.25, 1.0, T("雨はすべて地面にしみ込む\n(森林の土壌の浸透能は雨より大きい)",
                             "all the rain soaks into the ground\n(forest soil infiltrates faster than it rains)"),
                fontsize=9)
        ax.text(6.0, 3.2, T("表面流も泥流も起きない", "no surface flow, no lahar"), fontsize=10, color="#2b8a3e")
        title = T("(a) 噴火前", "(a) before the eruption")
    else:
        for xi in (1.2, 3.0):
            ti = 6.0 - xi + 0.32 - 0.04 * xi
            _arrow(ax, xi, ti + 0.45, xi, ti - 0.05, C_WATER, lw=0.9)
        # 表面流 → 泥流
        xs = np.linspace(0.6, 5.3, 60)
        ts = 6.0 - xs + 0.32 - 0.04 * xs
        xe = 5.3 if kind == "ash" else 3.95                              # 堰堤ありは堆砂域の手前まで
        ax.plot(xs[:20], ts[:20] + 0.12, color=C_WATER, lw=3)
        m = (xs >= xs[19]) & (xs <= xe)
        ax.plot(xs[m], ts[m] + 0.16, color=C_LAHAR, lw=5)
        if kind == "ash":
            _arrow(ax, 4.6, 1.9, 5.25, 1.25, C_LAHAR, lw=3)
        else:
            _arrow(ax, 3.2, 3.25, 3.9, 2.55, C_LAHAR, lw=3)
        ax.text(0.15, 7.45, T("① 細かい灰が表面に皮膜を作り、浸透能が下がる(噴火前の数十分の一)",
                              "① fine ash forms a crust on the surface and infiltration drops (to a few % of before)"),
                fontsize=8.5)
        ax.text(2.1, 4.6, T("② 雨の大半が表面を流れ、灰を削る", "② most of the rain runs off and erodes the ash"),
                fontsize=8.5, color="#1f5f8b")
        ax.text(3.6, 3.2, T("③ 削った灰を取り込んで泥流になる\n   (同じ雨の清水より流量が大きく速い)",
                            "③ the eroded ash turns the flow into a lahar\n   (more discharge and faster than clear water)"),
                fontsize=8.5, color=C_LAHAR)
        if kind == "ash":
            xd = np.linspace(5.3, 7.8, 100)
            dep = 0.55 * np.clip(1 - ((xd - 6.0) / 1.8) ** 2, 0, 1) * np.where(xd < 5.6, (xd - 5.3) / 0.3, 1)
            gd = _ground(xd) + 0.06
            ax.fill_between(xd, gd, gd + dep, color=C_DEP)
            ax.text(6.1, 1.25, T("④ 勾配が緩む谷出口で運べる土砂の量が減り、\n   扇状地に堆積する",
                                 "④ where the slope eases at the valley outlet the flow\n   can carry less and deposits on the fan"),
                    fontsize=8.5, color="0.15")
            title = T("(b) 降灰後の雨", "(b) rain after the ashfall")
        else:
            xb = 4.9
            zb = float(_ground(np.array([xb]))[0])
            ax.add_patch(plt.Rectangle((xb - 0.07, zb - 0.1), 0.14, 1.25, color="0.35", zorder=4))
            crest = zb + 1.15
            xp = np.linspace((6.32 - (crest - 0.1)) / 1.04, xb - 0.07, 40)
            ax.fill_between(xp, 6.32 - 1.04 * xp, np.full_like(xp, crest - 0.1), color=C_DEP, zorder=3)
            xo = np.linspace(xb + 0.07, 8.0, 60)
            ax.plot(xo, _ground(xo) + 0.13, color="#9c7b5a", lw=2.5)
            _arrow(ax, 6.6, _ground(np.array([6.6]))[0] + 0.35, 7.6, _ground(np.array([7.6]))[0] + 0.3, "#9c7b5a", lw=2)
            _arrow(ax, 6.05, 3.35, 4.65, 2.3, "0.3", lw=1.2)
            ax.text(6.1, 3.25, T("⑤ 堰堤の上流の空き容量に土砂がたまる\n   (満砂すると土砂も越えて流れる)",
                                              "⑤ sediment fills the empty space behind the dam\n   (once full, sediment passes over it too)"),
                    fontsize=8.5, color="0.15")
            ax.text(5.9, 1.25, T("越流する流れは土砂が少なく、扇状地の堆積が減る",
                                 "the overflow carries little sediment and the fan receives less"),
                    fontsize=8.5, color="0.15")
            title = T("(c) 降灰後の雨+砂防堰堤", "(c) rain after the ashfall + check dam")
    ax.axvline(5.5, color="k", lw=0.6, ls=":")
    ax.text(5.55, 6.7, T("谷出口", "valley outlet"), fontsize=8)
    ax.set_xlim(0, 10)
    ax.set_ylim(-1.2, 7.8)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(title, fontsize=10, loc="left")


def mechanism():
    fig, axs = plt.subplots(3, 1, figsize=(12, 12.5))
    for ax, kind in zip(axs, ("pre", "ash", "dam")):
        _panel(ax, kind)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in (C_SOIL, C_ASH, C_WATER, C_LAHAR, C_DEP)]
    fig.legend(handles, [T("森林の土壌", "forest soil"), T("降灰層(上面の黒線 = 皮膜)", "ash layer (black top line = crust)"),
                         T("雨・表面流", "rain, surface flow"), T("泥流", "lahar"), T("堆積", "deposit")],
               loc="upper center", ncol=5, fontsize=9, frameon=False, bbox_to_anchor=(0.5, 1.0))
    fig.tight_layout(rect=(0, 0, 1, 0.975))
    fig.savefig(f"{FIGDIR}/mechanism.png", dpi=100)
    plt.close(fig)


# ---------------------------------------------------------------- 設定
def setup():
    z0 = np.loadtxt("z.txt")
    zn = np.loadtxt("z_noash.txt")
    zd = np.loadtxt("z_dam.txt")
    ash = np.loadtxt("ash.txt")
    fig = plt.figure(figsize=(14, 8))
    gs = fig.add_gridspec(2, 2, height_ratios=[0.85, 1], width_ratios=[1.3, 1])
    axs = [fig.add_subplot(gs[0, :]), fig.add_subplot(gs[1, 0]), fig.add_subplot(gs[1, 1])]
    ax = axs[0]
    im = ax.imshow(ash, origin="lower", extent=EXT, cmap="Oranges", vmin=0, vmax=0.32)
    cs = ax.contour(X, Y, z0, levels=np.arange(0, 160, 10), colors="k", linewidths=0.4)
    ax.clabel(cs, fontsize=6, fmt="%d")
    dam = np.where(zd[:, I_DAM] != z0[:, I_DAM])[0]
    ax.plot([X[I_DAM]] * 2, [Y[dam[0]] - 2.5, Y[dam[-1]] + 2.5], color="red", lw=3)
    ax.text(X[I_DAM] - 6, Y[dam[-1]] + 4, T("砂防堰堤", "check dam"), color="red", ha="right", fontsize=9)
    for n, (px, py) in enumerate(((202.5, 77.5), (302.5, 77.5), (452.5, 77.5)), 1):
        ax.plot(px, py, "o", color="#1f5f8b", ms=5)
        ax.text(px + 4, py + 4, f"P{n}", color="#1f5f8b", fontsize=9)
    ax.axvline(XAPEX, color="k", lw=0.8, ls=":")
    for n, xs in ((1, X_SEC1), (2, X_SEC2)):
        ax.axvline(xs, color="#1f5f8b", lw=1.2, ls="--")
        ax.text(xs + 3, 140, T(f"測線 {n}", f"transect {n}"), color="#1f5f8b", fontsize=8, va="top")
    ax.set_xlabel(T("x (m)  ← 山腹(火口側)   扇状地 →", "x (m)  ← mountain slope (vent side)   fan →"))
    ax.set_ylabel("y (m)")
    ax.set_title(T("降灰厚と地形(等高線 10 m)", "Ash thickness and terrain (10 m contours)"), fontsize=10)
    fig.colorbar(im, ax=ax, shrink=0.9, pad=0.01).set_label(T("降灰厚 (m)", "ash thickness (m)"))
    ax = axs[1]
    ax.plot(X, zn[J], color="0.3", lw=1.2, label=T("元の地表(谷底)", "original ground (valley floor)"))
    ax.plot([X[I_DAM]] * 2, [zn[J, I_DAM], zd[J, I_DAM]], color="red", lw=4, label=T("砂防堰堤(高さ 5 m)", "check dam (5 m high)"))
    ax.axvline(XAPEX, color="k", lw=0.8, ls="--")
    ax.text(XAPEX + 6, 100, T("谷出口", "valley outlet"), fontsize=8)
    ax.text(110, 95, T("山腹 勾配 0.35", "slope 0.35"), fontsize=9)
    ax.text(380, 30, T("扇状地 勾配 0.08", "fan 0.08"), fontsize=9)
    ax.set_xlabel("x (m)")
    ax.set_ylabel(T("標高 (m)", "elevation (m)"))
    tw = ax.twinx()
    tw.plot(X, ash[J], color="#e6550d", lw=1.5, label=T("降灰厚(右軸)", "ash thickness (right axis)"))
    tw.set_ylim(0, 1.0)
    tw.set_ylabel(T("降灰厚 (m)", "ash thickness (m)"), color="#e6550d")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = tw.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=8, loc="upper right")
    ax.set_title(T("谷筋の縦断", "Longitudinal section along the valley axis"), fontsize=10)
    ax = axs[2]
    ax.fill_between([10, 70], 0, 5, color=C_WATER, alpha=0.6, label=T("降灰後: 灰にしみ込む分", "after the ashfall: soaks into the ash"))
    ax.fill_between([10, 70], 5, 30, color=C_LAHAR, alpha=0.45, label=T("降灰後: 表面を流れる分", "after the ashfall: runs off"))
    ax.plot([0, 10, 10, 70, 70, 90], [0, 0, 30, 30, 0, 0], color="#1f5f8b", lw=1.5, label=T("雨 30 mm/h × 60 分", "rain 30 mm/h for 60 min"))
    ax.axhline(100, color="#2b8a3e", lw=2, label=T("浸透能: 噴火前の森林の土壌 100 mm/h", "infiltration: forest soil before the eruption 100 mm/h"))
    ax.axhline(5, color="#4d4d4d", lw=2, label=T("浸透能: 皮膜のできた灰 5 mm/h", "infiltration: crusted ash 5 mm/h"))
    ax.set_ylim(0, 115)
    ax.set_xlim(0, 90)
    ax.set_xlabel(T("時刻 (分)", "time (min)"))
    ax.set_ylabel("mm/h")
    ax.legend(fontsize=7.5, loc="center left", bbox_to_anchor=(0.0, 0.62))
    ax.set_title(T("雨と浸透能", "Rain and infiltration capacity"), fontsize=10)
    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/setup.png", dpi=105)
    plt.close(fig)


# ---------------------------------------------------------------- 結果
def maxfields(case):
    """2 分ごとの出力から、流動深 h+hs と濃度 C = hs/(h+hs) の最大を求める(濃度は流動深 2 mm 以上の時刻だけ)。"""
    hmax = np.zeros((NY, NX))
    cmax = np.full((NY, NX), -1.0)
    for k in times(case):
        h = rd(case, "H", k)
        hs = rd(case, "Hs", k) if os.path.exists(f"result_{case}/Hs{k:04d}.txt") else 0.0 * h
        d = h + hs
        hmax = np.maximum(hmax, d)
        cmax = np.maximum(cmax, np.where(d > 0.002, hs / np.maximum(d, 1e-12), -1.0))
    return hmax, np.where(cmax >= 0, cmax, np.nan)


def dam_span():
    """堤体の y の範囲(m)。"""
    z0, zd = np.loadtxt("z.txt"), np.loadtxt("z_dam.txt")
    rows = np.where(zd[:, I_DAM] != z0[:, I_DAM])[0]
    return Y[rows[0]] - DX / 2, Y[rows[-1]] + DX / 2


def maps():
    fig, axs = plt.subplots(3, 2, figsize=(15, 7.6), constrained_layout=True)
    z0 = np.loadtxt("z.txt")
    y0, y1 = dam_span()
    titles = (T("地形変化 z − z0(青 = 侵食、赤 = 堆積)", "bed change z − z0 (blue = erosion, red = deposit)"),
              T("流動深 h + hs の最大", "max flow depth h + hs"),
              T("流れの濃度 hs/(h + hs) の最大", "max concentration hs/(h + hs)"))
    for col, case in enumerate(("ash", "dam")):
        K = max(times(case))
        dz = rd(case, "Z", K) - rd(case, "Z", 0)
        hmax, cmax = maxfields(case)
        fields = ((dz, dict(cmap="RdBu_r", norm=TwoSlopeNorm(vmin=-0.3, vcenter=0.0, vmax=2.5)), "m", "neither"),
                  (np.where(hmax > 0.002, hmax, np.nan), dict(cmap="Blues", vmin=0, vmax=0.08), "m", "max"),
                  (cmax, dict(cmap="YlOrBr", vmin=0, vmax=0.5), "", "neither"))
        for row, (f, kw, unit, ext) in enumerate(fields):
            ax = axs[row, col]
            im = ax.imshow(f, origin="lower", extent=EXT, **kw)
            ax.contour(X, Y, z0, levels=np.arange(0, 160, 10), colors="k", linewidths=0.3)
            ax.axvline(XAPEX, color="k", lw=0.6, ls="--")
            if case == "dam":
                ax.plot([X[I_DAM]] * 2, [y0, y1], color="lime", lw=2.5)
            ax.set_title(f"{LAB[case]}: {titles[row]}", fontsize=9.5)
            ax.set_ylabel("y (m)")
            if row == 2:
                ax.set_xlabel("x (m)")
            cb = fig.colorbar(im, ax=ax, shrink=0.9, extend=ext)
            if row == 0:
                cb.set_ticks([-0.3, -0.1, 0.0, 0.5, 1.0, 1.5, 2.0, 2.5])
            if unit:
                cb.set_label(unit)
    fig.savefig(f"{FIGDIR}/maps.png", dpi=100)
    plt.close(fig)


def profile():
    fig, axs = plt.subplots(2, 1, figsize=(11, 7), sharex=True, constrained_layout=True)
    for case in ("ash", "dam"):
        _, _, col, ls = next(c for c in CASES if c[0] == case)
        K = max(times(case))
        dz = rd(case, "Z", K)[J] - rd(case, "Z", 0)[J]
        if case == "dam":
            dz[I_DAM] = np.nan
        axs[0].plot(X, dz, ls, color=col, lw=1.5, label=LAB[case])
        _, cmax = maxfields(case)
        axs[1].plot(X, cmax[J], ls, color=col, lw=1.5, label=LAB[case])
    axs[0].axhline(0, color="k", lw=0.6)
    axs[0].set_ylabel(T("地形変化 z − z0 (m)\n(負 = 侵食、正 = 堆積)", "bed change z − z0 (m)\n(< 0 erosion, > 0 deposit)"))
    axs[1].set_ylabel(T("流れの濃度の最大", "max concentration of the flow"))
    axs[1].set_xlabel(T("x (m)  谷筋(y = 77.5 m)", "x (m)  along the valley axis (y = 77.5 m)"))
    for ax in axs:
        ax.axvline(XAPEX, color="k", lw=0.6, ls="--")
        ax.axvline(X[I_DAM], color="lime", lw=2, alpha=0.7)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    axs[0].text(XAPEX + 4, axs[0].get_ylim()[1] * 0.85, T("谷出口", "valley outlet"), fontsize=8)
    axs[0].text(X[I_DAM] - 4, axs[0].get_ylim()[1] * 0.85, T("堰堤", "dam"), fontsize=8, ha="right")
    fig.savefig(f"{FIGDIR}/profile.png", dpi=100)
    plt.close(fig)


def budget(case):
    """時刻 (min)、谷出口(x = 300 m)を越えて扇状地へ出た土砂、堰堤の上流にたまった土砂、
    扇頂(x = 300〜350 m)に積もった土砂(いずれも灰のかさ体積 m³)の時間変化。
    出た土砂 = 谷出口より上流の、侵食で減った量 − 堆積と流下中の量(流下中は hs/(1−λ))。"""
    tm = times(case)
    z0 = rd(case, "Z", 0)
    up = X < XAPEX
    pocket = (X >= X[I_DAM] - 25) & (X < X[I_DAM])
    apex = (X >= XAPEX) & (X < XAPEX + 50)
    out = []
    for k in sorted(tm):
        dz = rd(case, "Z", k) - z0
        hs = rd(case, "Hs", k)
        out.append((tm[k] / 60, -(dz[:, up].sum() + hs[:, up].sum() / (1 - LAM)) * A,
                    np.clip(dz[:, pocket], 0, None).sum() * A, np.clip(dz[:, apex], 0, None).sum() * A))
    return np.array(out)


def flux(case, n):
    """フラックス測線 n の時刻 (min) と水の流量 Q (m³/s)(エッジの流量の和。東向きが正)。"""
    d = np.loadtxt(f"result_{case}/fluxes/flux{n:04d}.csv", delimiter=",", comments="#")
    return d[:, 1], d[:, 2]


def sed_flux(case, xs):
    """x = xs の断面を通る土砂の流量 (m³/s。固体の体積)を、上流の土砂の収支の時間変化から求める。"""
    tm = times(case)
    z0 = rd(case, "Z", 0)
    up = X < xs
    ks = sorted(tm)
    st = [((1 - LAM) * (rd(case, "Z", k) - z0)[:, up].sum() + rd(case, "Hs", k)[:, up].sum()) * A for k in ks]
    t = np.array([tm[k] / 60 for k in ks])
    return 0.5 * (t[1:] + t[:-1]), -np.diff(st) / np.diff(t * 60)


def series():
    fig, axs = plt.subplots(1, 3, figsize=(16, 4.8), constrained_layout=True)
    for case, lab, col, ls in CASES:
        t, q = flux(case, 1)
        if case != "dam":
            axs[0].plot(t, q, ls, color=col, lw=1.4, label=T(f"{lab}: 水", f"{lab}: water"))
        if case == "ash":
            ts, qs = sed_flux(case, X_SEC1)
            axs[0].plot(t, q + np.interp(t, ts, qs, left=0, right=0), color=col, lw=2.4, alpha=0.5,
                        label=T(f"{lab}: 水 + 土砂", f"{lab}: water + sediment"))
        t, q = flux(case, 2)
        axs[1].plot(t, q, ls, color=col, lw=1.4, label=lab)
    for case in ("ash", "dam"):
        _, _, col, ls = next(c for c in CASES if c[0] == case)
        d = budget(case)
        axs[2].plot(d[:, 0], d[:, 1], ls, color=col, lw=1.8,
                    label=T(f"{LAB[case]}: 谷出口を越えて扇状地へ出た土砂", f"{LAB[case]}: passed the valley outlet to the fan"))
        if case == "dam":
            axs[2].plot(d[:, 0], d[:, 2], ":", color=col, lw=2.2, label=T("堰堤の上流にたまった土砂", "trapped behind the dam"))
    axs[0].set_title(T(f"谷の中の断面(x = {X_SEC1:.0f} m)を通る流量", f"Discharge through the valley section (x = {X_SEC1:.0f} m)"), fontsize=10)
    axs[1].set_title(T(f"扇状地の断面(x = {X_SEC2:.0f} m)を通る水の流量", f"Water discharge through the fan section (x = {X_SEC2:.0f} m)"), fontsize=10)
    axs[2].set_title(T("土砂の行き先(灰のかさ体積)", "Where the sediment goes (bulk volume of ash)"), fontsize=10)
    axs[0].set_ylabel(T("流量 (m³/s)", "discharge (m³/s)"))
    axs[1].set_ylabel(T("流量 (m³/s)", "discharge (m³/s)"))
    axs[2].set_ylabel("m³")
    for ax in axs:
        ax.axvspan(10, 70, color="0.93")
        ax.set_xlabel(T("時刻 (分)", "time (min)"))
        ax.set_xlim(0, 90)
        ax.grid(alpha=0.3)
    axs[0].legend(fontsize=7.5, loc="upper right")
    axs[1].legend(fontsize=7.5, loc="upper right")
    axs[2].legend(fontsize=7.5, loc="upper left")
    fig.savefig(f"{FIGDIR}/series.png", dpi=100)
    plt.close(fig)


def table():
    """README の数表(標準出力)。"""
    ash = np.loadtxt("ash.txt")
    up = X < XAPEX
    rain = 0.030 * NX * NY * A
    print(T("ケース | 地下へ入った水(降雨に対する割合)| 谷出口より上流で削られた灰 m³(割合)| 谷出口を越えて扇状地へ出た土砂 m³ | 堰堤の上流にたまった土砂 m³ | 扇頂(x 300〜350 m)の堆積 m³ / 最大厚 m | 谷の断面: 水の流量 0.05 m³/s を超えた時刻 分 / 40〜60 分の水の流量 m³/s / 水 + 土砂 | 扇状地の断面: 0.05 m³/s を超えた時刻 分 / 40〜60 分の水の流量 m³/s / 総流出量 m³",
            "case | water into the ground (fraction of rain) | ash eroded upstream of the valley outlet m³ (fraction) | sediment passing the valley outlet to the fan m³ | trapped behind the dam m³ | deposit at the fan apex (x 300-350 m) m³ / max thickness m | valley section: time water discharge exceeds 0.05 m³/s min / water discharge 40-60 min m³/s / water + sediment | fan section: time it exceeds 0.05 m³/s min / water discharge 40-60 min m³/s / total volume m³"))
    for case, lab, _, _ in CASES:
        log = [l.split() for l in open(f"result_{case}/Log.txt") if l[:1] == " " and "%" in l]
        sg = float(log[-1][3]) * NX * NY * A
        row = [lab, f"{sg:.0f} m³ ({sg / rain:.0%})"]
        sed = os.path.exists(f"result_{case}/Hs0000.txt")
        if sed:
            K = max(times(case))
            dz = rd(case, "Z", K) - rd(case, "Z", 0)
            ero = -np.clip(dz[:, up], None, 0).sum() * A
            d = budget(case)
            apex = (X >= XAPEX) & (X < XAPEX + 50)
            row += [f"{ero:.0f} ({ero / (ash[:, up].sum() * A):.0%})", f"{d[-1, 1]:.0f}",
                    f"{d[-1, 2]:.0f}" if case == "dam" else "—",
                    f"{d[-1, 3]:.0f} / {dz[:, apex].max():.2f}"]
        else:
            row += ["—"] * 4
        for n, xs in ((1, X_SEC1), (2, X_SEC2)):
            t, q = flux(case, n)
            on = np.where(q > 0.05)[0]
            m = (t >= 40) & (t <= 60)
            cell = f"{t[on[0]]:.1f}" if len(on) else "—"
            cell += f" / {q[m].mean():.2f}"
            if n == 1:
                if sed:
                    ts, qs = sed_flux(case, xs)
                    cell += f" / {(q + np.interp(t, ts, qs, left=0, right=0))[m].mean():.2f}"
                else:
                    cell += " / —"
            else:
                cell += f" / {np.trapezoid(q, t * 60):.0f}"
            row.append(cell)
        print(" | ".join(row))


if __name__ == "__main__":
    mechanism()
    setup()
    if all(os.path.exists(f"result_{c}/FILENUMBER.csv") for c, _, _, _ in CASES):
        maps()
        profile()
        series()
        table()
