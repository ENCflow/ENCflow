#!/usr/bin/env python3
"""timberyard の図と数表(事前に make run で 4 ケース、make supp で補足の 2 ケースを計算しておく)。

  figs/mechanism.png 高潮で貯木場の材木が流れ出して市街地へ入る仕組みと、3 つの対策の模式図
  figs/setup.png     地形と貯木場・防潮壁・開口部、高潮の波形と材木が流れ出し始める水位
  figs/maps.png      4 ケースの材木の届いた範囲(Wd9999)と最後に残った材木(Wd9998)
  figs/series.png    市街地にある材木の量の時間変化と、最後の材木の行き先
  figs/supp.png      補足: 材木を止める規則による、最後に残る材木の違い
引数 en で英語ラベル版を en/figs/ に描く(データと描画処理は共通)。
"""
import os
import re
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

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
I_YARD, I_WALL, I_TOWN, J_OPEN = (16, 35), (36, 37), 38, (25, 36)   # make_terrain.py と同じ(1 始まり)
STOCK = 60000.0
CASES = [("ise", T("伊勢湾台風型", "Ise Bay typhoon type"), "#c0392b", "-"),
         ("hold", T("流出を遅らせる(+2.5 m まで留める)", "release delayed (held until +2.5 m)"), "#e08214", "--"),
         ("far", T("貯木場を沖側へ離す", "timber yard moved offshore"), "#1f5f8b", "-."),
         ("wall4", T("防潮壁 +4 m・陸閘が開いている", "seawall +4 m, gate left open"), "#2b8a3e", ":")]
SUPP = [("ise", T("本体(流れが遅いと止まる)", "main (stops where the flow is slow)"), "#c0392b"),
        ("vstop0", T("流れが遅くても止まらない", "does not stop in slow flow"), "#8a8983"),
        ("refloat", T("止まった材木が再び流れる", "stopped timber floats off again"), "#2b8a3e")]
C_SEA, C_GROUND, C_LOG, C_HOUSE = "#7fb2e5", "#d9c7a0", "#8c5a2b", "#8c564b"


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


def ledger(case):
    """driftwood.csv を読む(3 桁の指数で E が落ちた値 1.6-103 も読めるように補う)。"""
    rows = []
    for line in open(f"result_{case}/driftwood.csv"):
        if line.startswith("time"):
            continue
        rows.append([float(re.sub(r"(\d)([+-]\d{3})$", r"\1E\2", v.strip())) for v in line.split(",")])
    return np.array(rows)


def zones(a):
    """柱状の量 × 空隙率 × 面積の配列を、市街地・防潮壁・貯木場・港の量に分ける (m3)。"""
    return dict(town=a[:, I_TOWN - 1:].sum(), wall=a[:, I_WALL[0] - 1:I_WALL[1]].sum(),
                yard=a[:, I_YARD[0] - 1:I_YARD[1]].sum(), harbour=a[:, 1:I_YARD[0] - 1].sum())


def fate(case):
    """最後の材木の行き先 (m3): 止まった材木の場所(市街地・防潮壁・貯木場の水域・港)、
    浮いている材木(全体と市街地の分)、沖へ出た量。"""
    gv = rd("gv.txt")
    z = zones(rd(f"result_{case}/Wd9998.txt") * gv * A)
    d = ledger(case)[-1]
    z["floating"] = d[7]
    k = max(frames(case))
    z["floating_town"] = zones(rd(f"result_{case}/Hd{k:04d}.txt") * gv * A)["town"]
    z["out"] = max(STOCK - (d[6] + d[7] + d[8]), 0.0)
    return z


def in_town(case):
    """市街地にある材木(流れている+止まっている)の量の時間変化(分、m3)。"""
    gv = rd("gv.txt")
    fr = frames(case)
    out = []
    for k in sorted(fr):
        a = (rd(f"result_{case}/Hd{k:04d}.txt") + rd(f"result_{case}/Wd{k:04d}.txt")) * gv * A
        out.append((fr[k], a[:, I_TOWN - 1:].sum()))
    return np.array(out)


def surge(t):
    return np.interp(t, [0, 60, 150, 180, 240], [0.0, 1.0, 3.5, 3.5, 0.5])


def draw_wall(ax, high=False):
    x0, x1 = (I_WALL[0] - 1) * DX, I_WALL[1] * DX
    y0, y1 = (J_OPEN[0] - 1) * DX, J_OPEN[1] * DX
    for ys in ((0, y0), (y1, NY * DX)):
        ax.fill_betweenx(ys, x0, x1, color="k" if not high else "0.2")
    ax.plot([x0, x1, x1, x0, x0], [y0, y0, y1, y1, y0], "k--", lw=0.8)


# ---------------------------------------------------------------- 模式図
def _logs(ax, x0, x1, y, n=6, color=C_LOG):
    for k in range(n):
        xc = x0 + (x1 - x0) * (k + 0.5) / n
        ax.add_patch(plt.Rectangle((xc - 0.18, y - 0.06), 0.36, 0.12, color=color, angle=8 * (k % 3 - 1)))


def _house(ax, x, y, broken=False):
    if broken:
        ax.plot([x, x + 0.5], [y, y + 0.35], color=C_HOUSE, lw=2)
        ax.plot([x + 0.1, x + 0.55], [y + 0.3, y], color=C_HOUSE, lw=2)
    else:
        ax.add_patch(plt.Rectangle((x, y), 0.5, 0.45, facecolor="w", edgecolor=C_HOUSE, lw=1.2))
        ax.add_patch(plt.Polygon([(x - 0.05, y + 0.45), (x + 0.25, y + 0.75), (x + 0.55, y + 0.45)], color=C_HOUSE))


def _section(ax, wall_h, yard_x, surge_h, logs_town, title, gate_jet=False, held=False):
    x = np.linspace(0, 12, 601)
    ground = np.where(x < 4.6, -2.0, np.where(x < 5.0, wall_h, 0.5 + 1.0 * (x - 5.0) / 7.0))
    ground = np.where(x < 1.0, -3.0, ground)
    ax.fill_between(x, -3.4, ground, color=C_GROUND)
    surf = np.full_like(x, surge_h)
    ax.fill_between(x, ground, np.maximum(surf, ground), where=surf > ground, color=C_SEA, alpha=0.55)
    _logs(ax, yard_x[0], yard_x[1], surge_h if not held else -1.4, n=5)
    if held:
        for xs in np.linspace(yard_x[0] - 0.1, yard_x[1] + 0.1, 4):
            ax.plot([xs, xs], [-2.0, -1.2], color="0.3", lw=1.5)
        ax.text(np.mean(yard_x), -2.7, T("係留・柵で留める", "held by mooring and fences"), ha="center", fontsize=8)
    for xh in (6.2, 7.6, 9.0, 10.4):
        _house(ax, xh, np.interp(xh, x, ground), broken=(logs_town and xh < 8))
    if logs_town:
        _logs(ax, 5.6, 8.6, surge_h, n=4)
        ax.annotate("", xy=(8.8, surge_h + 0.35), xytext=(3.2, surge_h + 0.35), arrowprops=dict(arrowstyle="-|>", color=C_LOG, lw=2))
    if gate_jet:
        ax.text(4.8, wall_h + 0.2, T("陸閘(開いている所から入る)", "gate (water enters where it is open)"), fontsize=8, ha="center")
    ax.set_xlim(0, 12)
    ax.set_ylim(-3.4, 5.0)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(title, fontsize=9, loc="left")


def mechanism():
    fig = plt.figure(figsize=(13, 7.4))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.25, 1])
    ax = fig.add_subplot(gs[0, :])
    _section(ax, 1.5, (2.0, 4.2), 3.5, True,
             T("(a) 高潮で水位が上がると、貯木場の材木が浮き上がって流れ出し、防潮壁を越えて市街地の家屋を壊す",
               "(a) As the surge raises the water, timber in the yard floats free, crosses the seawall and damages houses"))
    ax.text(0.2, 3.8, T("高潮", "storm surge"), fontsize=9, color="#2a78d6")
    ax.text(3.1, -1.4, T("貯木場", "timber yard"), fontsize=9, ha="center")
    ax.text(4.8, 1.8, T("防潮壁", "seawall"), fontsize=8, ha="center")
    ax.text(9.0, 3.9, T("市街地", "town"), fontsize=9)
    ax = fig.add_subplot(gs[1, 0])
    _section(ax, 1.5, (2.0, 4.2), 3.5, False, T("(b) 材木の流出を遅らせる(係留・柵)", "(b) delay the release (mooring, fences)"), held=True)
    ax = fig.add_subplot(gs[1, 1])
    _section(ax, 1.5, (0.2, 1.4), 3.5, False, T("(c) 貯木場を市街地から離す(木材港)", "(c) move the yard away from the town (timber port)"))
    ax = fig.add_subplot(gs[1, 2])
    _section(ax, 4.0, (2.0, 4.2), 3.5, False, T("(d) 防潮壁を高くしても、陸閘が開いていると", "(d) a raised seawall with its gate left open"), gate_jet=True)
    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/mechanism.png", dpi=100)
    plt.close(fig)


# ---------------------------------------------------------------- 設定
def setup():
    z = rd("z.txt")
    st = rd("stock.txt")
    sf = rd("stock_far.txt")
    fig, axs = plt.subplots(1, 2, figsize=(15, 4.3), gridspec_kw=dict(width_ratios=[1.5, 1]), constrained_layout=True)
    ax = axs[0]
    im = ax.imshow(z, extent=EXT, cmap="terrain", vmin=-4, vmax=4)
    draw_wall(ax)
    ax.add_patch(plt.Rectangle(((I_YARD[0] - 1) * DX, 0), (I_YARD[1] - I_YARD[0] + 1) * DX, NY * DX, facecolor="none", edgecolor=C_LOG, lw=2))
    ax.text((I_YARD[0] + I_YARD[1]) / 2 * DX - 5, 300, T("貯木場\n6 万 m³", "timber yard\n60,000 m³"), ha="center", va="center", fontsize=9, color=C_LOG,
            bbox=dict(facecolor="w", alpha=0.7, edgecolor="none"))
    xs = np.where(sf.any(axis=0))[0]
    ax.add_patch(plt.Rectangle((xs.min() * DX, 0), (xs.max() - xs.min() + 1) * DX, NY * DX, facecolor="none", edgecolor=C_LOG, lw=1.5, ls="--"))
    ax.text((xs.min() + xs.max() + 1) / 2 * DX, 80, T("沖側の貯木場\n(離すケース)", "offshore yard\n(moved case)"), ha="center", fontsize=8, color=C_LOG,
            bbox=dict(facecolor="w", alpha=0.7, edgecolor="none"))
    ax.annotate(T("開口部(陸閘。幅 120 m、+0.5 m)", "opening (gate; 120 m wide, +0.5 m)"), xy=(370, 300), xytext=(520, 330), fontsize=8,
                arrowprops=dict(arrowstyle="-", lw=0.8))
    ax.text(800, 80, T("市街地 +0.5 → +2.0 m(建物の空隙率 0.6)", "town +0.5 → +2.0 m (building porosity 0.6)"), ha="center", fontsize=8)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title(T("地形と貯木場、防潮壁(天端 +1.5 m。黒)", "Terrain, timber yard and seawall (crest +1.5 m, black)"), fontsize=10)
    fig.colorbar(im, ax=ax, shrink=0.85).set_label(T("地盤高 (m)", "ground elevation (m)"))
    ax = axs[1]
    t = np.linspace(0, 240, 241)
    ax.plot(t, surge(t), color="#2a78d6", lw=2.2, label=T("高潮(沖の水位)", "storm surge (offshore level)"))
    for lev, lab, ls, c in ((4.0, T("かさ上げした防潮壁 +4.0 m", "raised seawall +4.0 m"), "-.", "k"),
                            (1.5, T("防潮壁 +1.5 m", "seawall +1.5 m"), "-", "k"),
                            (0.5, T("開口部 +0.5 m", "opening +0.5 m"), "--", "k"),
                            (2.5, T("材木が流れ出す水位(遅らせる)+2.5 m", "release level (delayed) +2.5 m"), ":", "#e08214"),
                            (1.0, T("材木が流れ出す水位 +1.0 m", "release level +1.0 m"), ":", C_LOG)):
        ax.axhline(lev, color=c, ls=ls, lw=1.2, label=lab)
    ax.set_xlim(0, 240)
    ax.set_ylim(-0.2, 4.5)
    ax.set_xlabel(T("時刻 (分)", "time (min)"))
    ax.set_ylabel(T("水位 (m)", "water level (m)"))
    ax.set_title(T("高潮の波形と、材木が流れ出す水位", "Surge and the levels at which timber is released"), fontsize=10)
    ax.legend(fontsize=7.5, loc="upper left")
    ax.grid(alpha=0.3)
    fig.savefig(f"{FIGDIR}/setup.png", dpi=100)
    plt.close(fig)


# ---------------------------------------------------------------- 結果
def maps():
    fig, axs = plt.subplots(2, 4, figsize=(17, 5.6), constrained_layout=True)
    cmap = plt.get_cmap("YlOrBr").copy()
    for col, (case, lab, c, ls) in enumerate(CASES):
        for row, (name, ttl) in enumerate((("Wd9999", T("届いた範囲(最大の量)", "reach (maximum amount)")),
                                           ("Wd9998", T("最後に残った材木", "timber remaining at the end")))):
            a = rd(f"result_{case}/{name}.txt")
            im = axs[row, col].imshow(np.where(a > 0.01, a, np.nan), extent=EXT, cmap=cmap, vmin=0, vmax=1.0)
            draw_wall(axs[row, col], case == "wall4")
            if col == 0:
                axs[row, col].set_ylabel(ttl + "\ny (m)")
            else:
                axs[row, col].set_yticks([])
            axs[row, col].set_xticks([0, 400, 800, 1200])
        axs[0, col].set_title(lab, fontsize=10)
        axs[1, col].set_xlabel("x (m)")
    fig.colorbar(im, ax=axs, shrink=0.85, extend="max").set_label(T("材木(柱状の量 m³/m²)", "timber (column amount, m³/m²)"))
    fig.savefig(f"{FIGDIR}/maps.png", dpi=95)
    plt.close(fig)


def series():
    fig, axs = plt.subplots(1, 2, figsize=(15, 4.6), constrained_layout=True, gridspec_kw=dict(width_ratios=[1.25, 1]))
    ax = axs[0]
    for case, lab, c, ls in CASES:
        d = in_town(case)
        ax.plot(d[:, 0], d[:, 1] / 1000, ls, color=c, lw=2, marker=".", label=lab)
    ax2 = ax.twinx()
    t = np.linspace(0, 240, 241)
    ax2.plot(t, surge(t), color="#2a78d6", lw=1, alpha=0.5)
    ax2.set_ylabel(T("高潮(沖の水位 m)", "surge (offshore level, m)"), color="#2a78d6")
    ax2.set_ylim(0, 8)
    ax.set_xlim(0, 240)
    ax.set_xlabel(T("時刻 (分)", "time (min)"))
    ax.set_ylabel(T("市街地にある材木 (千 m³)", "timber in the town (1000 m³)"))
    ax.set_title(T("市街地にある材木(流れている+止まっている。10 分ごと)", "Timber in the town (floating + stopped; every 10 min)"), fontsize=10)
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(alpha=0.3)
    ax = axs[1]
    parts = [("town", T("市街地", "town"), "#8c5a2b"), ("wall", T("防潮壁の上", "on the seawall"), "#b8860b"),
             ("yard", T("貯木場の水域", "yard area"), "#d9a066"), ("harbour", T("港", "harbour"), "#f2d0a4"),
             ("floating", T("流れている", "still floating"), "#cccccc"), ("out", T("沖へ出る", "carried offshore"), "#2a78d6")]
    for r, (case, lab, c, ls) in enumerate(CASES):
        f = fate(case)
        x0 = 0.0
        for key, name, col in parts:
            v = f[key] / 1000.0
            ax.barh(r, v, left=x0, color=col, edgecolor="w", label=name if r == 0 else None)
            if v > 4:
                ax.text(x0 + v / 2, r, f"{v:.0f}", ha="center", va="center", fontsize=8)
            x0 += v
    ax.set_yticks(range(len(CASES)))
    ax.set_yticklabels([lab for _, lab, _, _ in CASES], fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel(T("材木 (千 m³。計 60 千 m³)", "timber (1000 m³; 60,000 m³ in total)"))
    ax.set_title(T("最後(4 時間)の材木の行き先", "Where the timber is at the end (4 hours)"), fontsize=10)
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=3, frameon=False)
    fig.savefig(f"{FIGDIR}/series.png", dpi=100)
    plt.close(fig)


def supp():
    fig, axs = plt.subplots(1, 3, figsize=(16, 3.4), constrained_layout=True)
    for ax, (case, lab, c) in zip(axs, SUPP):
        a = rd(f"result_{case}/Wd9998.txt")
        im = ax.imshow(np.where(a > 0.01, a, np.nan), extent=EXT, cmap="YlOrBr", vmin=0, vmax=1.0)
        draw_wall(ax)
        f = fate(case)
        town = (f["town"] + f["floating_town"]) / 1000
        ax.set_title(T(f"{lab}: 市街地に残る {town:.1f} 千 m³、海側に浮く {(f['floating'] - f['floating_town']) / 1000:.0f} 千 m³",
                       f"{lab}: {town:.1f}k m³ left in the town, {(f['floating'] - f['floating_town']) / 1000:.0f}k m³ afloat seaward"), fontsize=9)
        ax.set_xlabel("x (m)")
    axs[0].set_ylabel("y (m)")
    fig.colorbar(im, ax=axs, shrink=0.9).set_label(T("最後に残った材木 (m³/m²)", "timber remaining (m³/m²)"))
    fig.savefig(f"{FIGDIR}/supp.png", dpi=100)
    plt.close(fig)


def table():
    print(T("ケース | 流れ出した時刻 | 市街地に入り始めた時刻 | 市街地にあった材木の最大 | 届いた範囲(市街地の割合 / 最も遠い x) | 最後: 市街地 | 防潮壁 | 貯木場の水域 | 港 | 流れている | 沖へ出る",
            "case | release period | timber enters the town | max timber in the town | reach (share of town / farthest x) | end: town | seawall | yard area | harbour | floating | offshore"))
    for case, lab, *_ in CASES + [(c, l, None, None) for c, l, _ in SUPP[1:]]:
        d = ledger(case)
        t = d[:, 0] / 60
        rel = d[:, 1]
        t0, t1 = t[np.argmax(rel > 100)], t[np.argmax(rel > 0.99 * rel[-1])]
        it = in_town(case)
        ton = it[np.argmax(it[:, 1] > 100), 0]
        wm = rd(f"result_{case}/Wd9999.txt")[:, I_TOWN - 1:]
        cols = np.where((wm > 0.01).any(axis=0))[0]
        f = fate(case)
        print(f"{lab} | {t0:.0f}-{t1:.0f} min | {ton:.0f} min | {it[:, 1].max():.0f} m3 ({it[it[:, 1].argmax(), 0]:.0f} min) | "
              f"{(wm > 0.01).mean() * 100:.0f} % / {(cols.max() + I_TOWN - 0.5) * DX:.0f} m | {f['town']:.0f} | {f['wall']:.0f} | {f['yard']:.0f} | "
              f"{f['harbour']:.0f} | {f['floating']:.0f} (town {f['floating_town']:.0f}) | {f['out']:.0f}")


if __name__ == "__main__":
    mechanism()
    setup()
    if all(os.path.exists(f"result_{c}/FILENUMBER.csv") for c, *_ in CASES):
        maps()
        series()
        table()
    if all(os.path.exists(f"result_{c}/FILENUMBER.csv") for c, _, _ in SUPP):
        supp()
