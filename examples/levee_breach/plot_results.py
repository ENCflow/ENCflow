#!/usr/bin/env python3
"""levee_breach の図と数表(事前に make run で 4 ケースを計算しておく)。

  figs/mechanism.png 越水から破堤・氾濫・家屋の流失までの模式図(データを使わない)
  figs/setup.png     地形と天端の低い区間・住宅地・二線堤(平面)、破堤口の横断、洪水と破堤の時刻
  figs/maps.png      4 ケースの最大浸水深と家屋の流失
  figs/series.png    堤内地へ入る流量、破堤口より下流の川の流量、住宅地の浸水深の時間変化
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

NX, NY, DX = 175, 200, 10.0
I_LEV2, J_LOW1, J_LOW2, J_DIKE = 15, 53, 67, 155         # make_terrain.py と同じ
BLOCKS = {"A": (17, 36, 50, 70), "B": (40, 80, 115, 140), "C": (40, 80, 170, 195)}
EXT = [0, NX * DX, NY * DX, 0]                           # 行 1 = 北を上に
CASES = [("overtop", T("越水だけ", "overtopping only"), "#8a8983", ":"),
         ("breach", T("越水で破堤", "breach by overtopping"), "#c0392b", "-"),
         ("delay", T("破堤が 1 時間遅れる", "breach 1 hour later"), "#e08214", "--"),
         ("dike", T("破堤+二線堤", "breach + secondary levee"), "#1f5f8b", "-.")]
T_BREACH = {"breach": (180, 240), "delay": (240, 300), "dike": (180, 240)}
C_GROUND, C_WATER, C_LEVEE, C_HOUSE = "#d9c7a0", "#2a78d6", "#555555", "#8c564b"


def rd(path):
    return np.loadtxt(path)


def flux(case, n):
    """フラックス測線 n の時刻(分)と流量 (m3/s)。"""
    a = np.loadtxt(f"result_{case}/fluxes/flux{n:04d}.csv", delimiter=",", comments="#")
    return a[:, 1], a[:, 2]


def probe(case, n):
    """プローブ n の時刻(分)・地盤高・水深。"""
    a = np.loadtxt(f"result_{case}/probes/probe{n:04d}.csv", delimiter=",", comments="#")
    return a[:, 1], a[:, 2], a[:, 3]


def last_frame(case, var):
    ks = sorted(int(f[-8:-4]) for f in glob.glob(f"result_{case}/{var}0*.txt"))
    return rd(f"result_{case}/{var}{ks[-1]:04d}.txt")


def inflow_series():
    """param.txt の流入波形(分、m3/s)。"""
    ts, qs = [], []
    for line in open("param.txt", encoding="utf-8"):
        if line.strip().startswith("inflow_val"):
            v = line.split("=")[1].split("!")[0].split(",")
            ts.append(float(v[0]))
            qs.append(float(v[1]))
    return np.array(ts), np.array(qs)


# ---------------------------------------------------------------- 模式図
def _levee(ax, x0, stage, title, stage_n):
    """堤防の横断(左 = 川、右 = 堤内地)。stage_n = 0: 越水の始まり、1: 裏法の侵食、2: 破堤。"""
    G, CR = 2.0, 6.0                                           # 堤内地の地盤高、天端
    bed = [(0, -0.4), (0, 0.0), (3.0, 0.0), (3.0, G)]
    if stage_n < 2:
        levee = [(3.0, G), (4.3, CR), (5.3, CR)]
        if stage_n == 0:
            levee += [(7.3, G)]
        else:
            levee += [(5.8, 4.9), (6.2, 3.3), (6.7, 2.3), (7.2, 1.4), (7.9, 1.6), (8.3, G)]
    else:
        levee = [(3.0, G), (3.4, 2.9), (3.6, 1.6), (6.3, 1.4), (7.3, 1.8), (8.3, G)]
    land = [(10.0, G), (10.0, -0.4)]
    poly = bed + levee + land
    ax.add_patch(plt.Polygon([(x + x0, y) for x, y in poly], closed=True, color=C_GROUND))
    if stage_n < 2:
        wl = stage
        xr = 3.0 + (wl - G) / (CR - G) * 1.3                    # 川表の法面と水面の交点
        ax.add_patch(plt.Polygon([(x0, 0.0), (x0 + 3.0, 0.0), (x0 + 3.0, G), (x0 + xr, wl), (x0, wl)], color=C_WATER, alpha=0.55))
        # 天端と裏法を流れる薄い越流
        top = [(4.3, CR), (5.3, CR)] + levee[3:]
        xs = [x for x, y in [(xr, wl)] + top]
        ys = [y + 0.18 for x, y in [(xr, wl - 0.18)] + top]
        ax.plot([x + x0 for x in xs], ys, color=C_WATER, lw=2.2)
        ax.annotate("", xy=(x0 + 9.4, G + 0.15), xytext=(x0 + 8.0, G + 0.15), arrowprops=dict(arrowstyle="-|>", color=C_WATER, lw=1.6))
    else:
        ax.add_patch(plt.Polygon([(x0, 0.0), (x0 + 3.0, 0.0), (x0 + 3.0, G), (x0 + 3.4, 2.9), (x0 + 3.6, 1.6), (x0 + 6.3, 1.4),
                                  (x0 + 7.3, 1.8), (x0 + 8.3, G), (x0 + 10.0, G), (x0 + 10.0, G + 0.9), (x0 + 6.0, 3.3),
                                  (x0 + 3.6, 5.0), (x0, 5.2)], color=C_WATER, alpha=0.55))
        ax.annotate("", xy=(x0 + 9.6, G + 0.55), xytext=(x0 + 2.0, 4.6), arrowprops=dict(arrowstyle="-|>", color=C_WATER, lw=3))
    ax.text(x0 + 5.0, 7.3, title, ha="center", fontsize=9)


def mechanism():
    fig = plt.figure(figsize=(13, 8.4))
    gs = fig.add_gridspec(2, 1, height_ratios=[1, 1.35])
    ax = fig.add_subplot(gs[0])
    _levee(ax, 0, 6.2, T("① 洪水の水位が天端の低い所を越える", "① the flood rises over the low crest"), 0)
    _levee(ax, 11, 6.2, T("② 越水が裏法(堤内地側の斜面)を削る", "② overtopping erodes the landside slope"), 1)
    _levee(ax, 22, 6.2, T("③ 堤体が崩れて破堤し、口が広がる", "③ the levee fails and the opening widens"), 2)
    for xs in (0, 11, 22):
        ax.text(xs + 1.4, 0.6, T("川", "river"), color="w", fontsize=9, ha="center")
        ax.text(xs + 9.0, 0.9, T("堤内地", "landside"), fontsize=9, ha="center")
    ax.set_xlim(-0.3, 32.3)
    ax.set_ylim(-0.5, 8.0)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(T("(a) 越水から破堤まで(堤防の横断)", "(a) From overtopping to breach (cross-section of the levee)"), fontsize=10, loc="left")
    ax = fig.add_subplot(gs[1])
    ax.add_patch(plt.Rectangle((0, 0), 1.6, 10, color=C_WATER, alpha=0.5))
    ax.add_patch(plt.Rectangle((1.6, 0), 0.25, 10, color=C_LEVEE))
    ax.add_patch(plt.Rectangle((1.6, 6.0), 0.25, 1.5, color="w"))
    ax.annotate("", xy=(0.8, 1.0), xytext=(0.8, 9.0), arrowprops=dict(arrowstyle="-|>", color="w", lw=2))
    ax.text(0.45, 5.0, T("川(下流へ)", "river (downstream)"), ha="center", fontsize=8, rotation=90, va="center", color="w")
    for k, (dx_, dy_) in enumerate(((2.2, 0.0), (1.6, -1.6), (2.0, -3.0), (0.8, -3.6))):
        ax.annotate("", xy=(1.9 + dx_, 6.75 + dy_), xytext=(1.9, 6.75), arrowprops=dict(arrowstyle="-|>", color=C_WATER, lw=2.5 - 0.4 * k))
    ax.add_patch(plt.Rectangle((2.0, 6.0), 1.0, 1.5, facecolor="none", edgecolor=C_HOUSE, hatch="xx", lw=1))
    ax.text(3.1, 7.6, T("破堤口の近く: 速い氾濫流が家屋を押し流す", "near the breach: fast flow sweeps houses away"), fontsize=8, color=C_HOUSE)
    ax.add_patch(plt.Rectangle((4.2, 2.8), 1.6, 1.4, facecolor="none", edgecolor=C_HOUSE, hatch="..", lw=1))
    ax.text(5.9, 3.5, T("離れた所: 流れは遅く、浸水する(床上・床下)", "farther away: slow flow, houses are flooded"), fontsize=8, color=C_HOUSE)
    ax.fill_between([1.85, 9.5], 1.55, 1.75, color=C_LEVEE)
    ax.text(6.5, 1.0, T("二線堤・盛土道路: 氾濫水を止め、手前を深くし、背後を守る", "secondary levee or road embankment: holds the water, deepens it in front, protects behind"), fontsize=8, ha="center")
    ax.text(1.0 + 0.9, 5.2, T("破堤口", "breach"), fontsize=8, rotation=90, color="k")
    ax.text(5.5, 9.3, T("氾濫水は地面の傾きに沿って下流へ広がる", "the flood spreads downslope"), fontsize=8, color=C_WATER)
    ax.annotate("", xy=(8.0, 4.8), xytext=(6.0, 8.6), arrowprops=dict(arrowstyle="-|>", color=C_WATER, lw=1.2, ls="--"))
    ax.set_xlim(0, 10)
    ax.set_ylim(0.5, 10)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(T("(b) 破堤口からの氾濫(平面)", "(b) Flooding from the breach (plan)"), fontsize=10, loc="left")
    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/mechanism.png", dpi=100)
    plt.close(fig)


# ---------------------------------------------------------------- 設定
def setup():
    z = rd("data/z_dike.txt")
    fig = plt.figure(figsize=(14, 8.2))
    gs = fig.add_gridspec(2, 2, width_ratios=[1, 1.25], height_ratios=[1, 1])
    ax = fig.add_subplot(gs[:, 0])
    im = ax.imshow(z, extent=EXT, cmap="terrain", vmin=-4, vmax=6)
    ax.contour((np.arange(NX) + 0.5) * DX, (np.arange(NY) + 0.5) * DX, z, levels=np.arange(-2.0, 0.01, 0.5), colors="0.4", linewidths=0.4)
    ax.plot([I_LEV2 * DX - 10] * 2, [(J_LOW1 - 1) * DX, J_LOW2 * DX], color="#c0392b", lw=4)
    ax.annotate(T("天端の低い区間 = 破堤口(150 m)", "low crest = breach (150 m)"), xy=(I_LEV2 * DX, (J_LOW1 - 1) * DX),
                xytext=(450, 330), color="#c0392b", fontsize=8, arrowprops=dict(arrowstyle="-", color="#c0392b", lw=0.8))
    for nm, (i1, i2, j1, j2) in BLOCKS.items():
        ax.add_patch(plt.Rectangle(((i1 - 1) * DX, (j1 - 1) * DX), (i2 - i1 + 1) * DX, (j2 - j1 + 1) * DX, facecolor="none", edgecolor=C_HOUSE, hatch="xx", lw=1.2))
        ax.text((i2 + 1) * DX, (j1 + j2) / 2 * DX, T(f"住宅地 {nm}", f"houses {nm}"), color=C_HOUSE, fontsize=8, va="center")
    ax.plot([I_LEV2 * DX, NX * DX], [J_DIKE * DX] * 2, color="k", lw=2, ls="--")
    ax.text(1000, J_DIKE * DX - 45, T("二線堤(破堤+二線堤のケースだけ)", "secondary levee (only in the breach + levee case)"), fontsize=8, ha="center",
            bbox=dict(facecolor="w", alpha=0.7, edgecolor="none", pad=1))
    ax.annotate("", xy=(90, 1900), xytext=(90, 100), arrowprops=dict(arrowstyle="-|>", color="w", lw=1.5))
    ax.text(60, 1000, T("川", "river"), color="w", rotation=90, fontsize=9, va="center")
    ax.text(1000, 1980, T("南辺: 自由流出(氾濫原が下流へ続く)", "south edge: free outflow (the plain continues)"), fontsize=8, ha="center")
    ax.set_xlabel("x (m)")
    ax.set_ylabel(T("y (m)  北 → 南", "y (m)  north → south"))
    ax.set_title(T("地形(等高線 0.5 m)と住宅地・二線堤", "Terrain (0.5 m contours), houses and secondary levee"), fontsize=10)
    fig.colorbar(im, ax=ax, shrink=0.7, pad=0.02).set_label(T("地盤高 (m)", "ground elevation (m)"))
    ax = fig.add_subplot(gs[0, 1])
    z0 = rd("data/z.txt")
    j = (J_LOW1 + J_LOW2) // 2
    xs = (np.arange(NX) + 0.5) * DX
    zb = z0[j - 1].copy()
    zb[13:15] = z0[j - 1, 15]
    ax.fill_between(xs[:40], -4, z0[j - 1, :40], color=C_GROUND, step="mid")
    ax.step(xs[:40], z0[J_LOW1 - 4, :40], where="mid", color="k", lw=1, ls=":", label=T("ふつうの区間の堤防(高さ 4 m)", "ordinary levee (4 m high)"))
    ax.step(xs[:40], zb[:40], where="mid", color="#c0392b", lw=1.2, ls="--", label=T("破堤後(堤内地の地盤高まで下がる)", "after the breach (down to the landside ground)"))
    t, zp, hp = probe("overtop", 1) if os.path.exists("result_overtop/probes/probe0001.csv") else (None, [0.0], [0.0])
    ax.axhline(np.max(np.asarray(zp) + np.asarray(hp)), xmin=0.02, xmax=0.33, color=C_WATER, lw=2, label=T("洪水のピークの水位(越水だけのケース)", "flood peak level (overtopping-only case)"))
    ax.set_xlim(0, 400)
    ax.set_ylim(-3.5, 4.5)
    ax.set_xlabel("x (m)")
    ax.set_ylabel(T("標高 (m)", "elevation (m)"))
    ax.set_title(T(f"破堤口の中央の横断(行 {j})", f"Cross-section through the centre of the breach (row {j})"), fontsize=10)
    ax.text(85, -2.5, T("川(幅 100 m)", "river (100 m wide)"), ha="center", fontsize=8)
    ax.text(140, 2.9, T("天端の低い区間", "low crest"), ha="center", fontsize=8, color="#c0392b")
    ax.text(300, 0.0, T("堤内地", "landside"), ha="center", fontsize=8)
    ax.legend(fontsize=8, loc="upper right")
    ax = fig.add_subplot(gs[1, 1])
    tq, qq = inflow_series()
    ax.plot(tq, qq, color="k", lw=1.8, label=T("洪水の流量(上流端)", "flood discharge (upstream end)"))
    ax.set_ylabel(T("流量 (m³/s)", "discharge (m³/s)"))
    ax.set_xlabel(T("時刻 (分)", "time (min)"))
    ax.axvspan(147, 309, color=C_WATER, alpha=0.1)
    ax.text(150, 150, T("越水(147〜309 分)", "overtopping (147-309 min)"), fontsize=8, color=C_WATER)
    for case, lab, col, ls in CASES[1:3]:
        t0, t1 = T_BREACH[case]
        y = 1750 if case == "breach" else 1850
        ax.plot([t0, t1], [y, y], color=col, lw=5, solid_capstyle="butt")
        ax.text(t1 + 5, y, T(f"{lab}: {t0} 分から破堤、{t1} 分に 150 m", f"{lab}: from {t0} min, 150 m at {t1} min"), fontsize=8, va="center", color=col)
    ax.set_xlim(0, 480)
    ax.set_ylim(0, 2000)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, loc="center right")
    ax.set_title(T("洪水と破堤の時刻", "Flood and breach timing"), fontsize=10)
    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/setup.png", dpi=100)
    plt.close(fig)


# ---------------------------------------------------------------- 結果
def maps():
    fig, axs = plt.subplots(1, 4, figsize=(16, 5.6), constrained_layout=True)
    levels = [0.01, 0.1, 0.3, 0.5, 1.0, 2.0, 3.0]
    cmap = plt.get_cmap("Blues", len(levels) + 1)
    norm = BoundaryNorm(levels, cmap.N, extend="max")
    for ax, (case, lab, col, ls) in zip(axs, CASES):
        h = rd(f"result_{case}/H9999.txt")
        h = np.where(h > 0.01, h, np.nan)
        h[:, :15] = np.nan
        im = ax.imshow(h, extent=EXT, cmap=cmap, norm=norm)
        bs = last_frame(case, "Bs")
        ax.contourf((np.arange(NX) + 0.5) * DX, (np.arange(NY) + 0.5) * DX, bs, levels=[0.1, 0.5, 1.01], colors=["#f4a582", "#b2182b"], alpha=0.9)
        for nm, (i1, i2, j1, j2) in BLOCKS.items():
            ax.add_patch(plt.Rectangle(((i1 - 1) * DX, (j1 - 1) * DX), (i2 - i1 + 1) * DX, (j2 - j1 + 1) * DX, facecolor="none", edgecolor=C_HOUSE, lw=1))
            ax.text((i2 + 1) * DX, (j1 - 1) * DX, nm, color=C_HOUSE, fontsize=9, va="top")
        ax.plot([I_LEV2 * DX - 10] * 2, [(J_LOW1 - 1) * DX, J_LOW2 * DX], color="#c0392b", lw=3)
        if case == "dike":
            ax.plot([I_LEV2 * DX, NX * DX], [J_DIKE * DX] * 2, color="k", lw=2)
        ax.set_title(lab, fontsize=10)
        ax.set_xlabel("x (m)")
    axs[0].set_ylabel("y (m)")
    cb = fig.colorbar(im, ax=axs, shrink=0.85)
    cb.set_label(T("最大浸水深 (m)", "maximum inundation depth (m)"))
    handles = [plt.Rectangle((0, 0), 1, 1, color="#f4a582"), plt.Rectangle((0, 0), 1, 1, color="#b2182b")]
    fig.legend(handles, [T("家屋の流失 10〜50 %", "houses swept away 10-50 %"), T("家屋の流失 50 % 以上", "houses swept away ≥ 50 %")],
               loc="lower center", ncol=2, fontsize=9, frameon=False, bbox_to_anchor=(0.45, -0.06))
    fig.savefig(f"{FIGDIR}/maps.png", dpi=100, bbox_inches="tight")
    plt.close(fig)


def series():
    fig, axs = plt.subplots(1, 3, figsize=(16, 4.6), constrained_layout=True)
    tq, qq = inflow_series()
    axs[1].plot(tq, qq, color="k", lw=1, label=T("上流端の流量", "upstream discharge"))
    for case, lab, col, ls in CASES:
        t, q = flux(case, 1)
        axs[0].plot(t, q, ls, color=col, lw=1.8, label=lab)
        t, q = flux(case, 2)
        axs[1].plot(t, q, ls, color=col, lw=1.6, label=lab)
        t, z, h = probe(case, 4)
        axs[2].plot(t, h, ls, color=col, lw=1.6, label=lab)
    axs[0].set_title(T("堤内地へ入る流量(堤防の法尻の測線)", "Flow into the landside (line along the levee toe)"), fontsize=10)
    axs[1].set_title(T("破堤口より下流の川の流量", "River discharge downstream of the breach"), fontsize=10)
    axs[2].set_title(T("住宅地 B(破堤口から南へ約 700 m)の浸水深", "Depth at houses B (about 700 m south of the breach)"), fontsize=10)
    axs[0].set_ylabel(T("流量 (m³/s)", "discharge (m³/s)"))
    axs[1].set_ylabel(T("流量 (m³/s)", "discharge (m³/s)"))
    axs[2].set_ylabel(T("浸水深 (m)", "depth (m)"))
    for ax in axs:
        ax.set_xlabel(T("時刻 (分)", "time (min)"))
        ax.set_xlim(0, 480)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8, loc="upper left" if ax is not axs[1] else "lower center")
    fig.savefig(f"{FIGDIR}/series.png", dpi=100)
    plt.close(fig)


def table():
    st = rd("data/bdstock.txt")
    print(T("ケース | 堤内地へ入った水 (万 m³) | 最大流量 (m³/s) | 下流の川の最小流量 (m³/s) | 浸水 0.1 m 以上 (ha) | 0.5 m 以上 (ha) | 最大浸水深 (m) | 流失 A / B / C (%) | 最大浸水深 A / B / C (m) | B が 0.5 m に達した時刻 (分)",
            "case | water into the landside (10^4 m3) | peak flow (m3/s) | min river discharge downstream (m3/s) | inundated >= 0.1 m (ha) | >= 0.5 m (ha) | max depth (m) | swept away A / B / C (%) | max depth A / B / C (m) | B reaches 0.5 m (min)"))
    for case, lab, col, ls in CASES:
        t, q = flux(case, 1)
        vol = np.sum(0.5 * (q[1:] + q[:-1]) * np.diff(t) * 60.0)
        t2, q2 = flux(case, 2)
        h = rd(f"result_{case}/H9999.txt")[:, 15:]
        hh = rd(f"result_{case}/H9999.txt")
        bs = last_frame(case, "Bs")
        lost, dep = [], []
        for nm, (i1, i2, j1, j2) in BLOCKS.items():
            sl = (slice(j1 - 1, j2), slice(i1 - 1, i2))
            lost.append((bs[sl] * st[sl]).sum() / st[sl].sum() * 100)
            dep.append(hh[sl].max())
        tb, zb, hb = probe(case, 4)
        on = tb[np.argmax(hb > 0.5)] if (hb > 0.5).any() else float("nan")
        print(f"{lab} | {vol / 1e4:.1f} | {q.max():.0f} | {q2[(t2 > 150) & (t2 < 330)].min():.0f} | {(h > 0.1).sum() * DX * DX / 1e4:.0f} | "
              f"{(h > 0.5).sum() * DX * DX / 1e4:.0f} | {h.max():.2f} | {lost[0]:.0f} / {lost[1]:.0f} / {lost[2]:.0f} | "
              f"{dep[0]:.2f} / {dep[1]:.2f} / {dep[2]:.2f} | {on:.0f}")


if __name__ == "__main__":
    mechanism()
    setup()
    if all(os.path.exists(f"result_{c}/FILENUMBER.csv") for c, _, _, _ in CASES):
        maps()
        series()
        table()
