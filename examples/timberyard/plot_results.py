#!/usr/bin/env python3
"""timberyard の図と数表(事前に make run で 4 ケース、make supp で補足の 2 ケースを計算しておく)。

  figs/mechanism.png 高潮で貯木場の材木が流れ出して市街地へ入る仕組みと、3 つの対策の模式図
  figs/setup.png     地形と貯木場・防潮壁・開口部、高潮の波形と材木が流れ出し始める水位
  figs/laws.png      材木が流れ出す・止まる・運ばれる則(入力と設定ファイルの値だけ。計算結果を使わない)
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
DD_MIN = 0.001                   # 移動限界水深 dd(param.txt になく src/list_sysparam.f90 の既定。乾いたセルの判定)


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


def _house(ax, x, y):
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
        _house(ax, xh, np.interp(xh, x, ground))
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
             T("(a) 高潮で水位が上がると、貯木場の材木が浮き上がって流れ出し、防潮壁を越えて市街地へ入る",
               "(a) As the surge raises the water, timber in the yard floats free, crosses the seawall and enters the town"))
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


# ---------------------------------------------------------------- 則(入力と設定値だけ。計算結果を使わない)
def param_value(name, fn="param.txt"):
    """設定ファイルの「name = 値」を読む(最初の 1 つ。! 以降のコメントは除く)。"""
    for line in open(fn, encoding="utf-8"):
        s = line.split("!")[0]
        if "=" in s and s.split("=")[0].strip() == name:
            return float(s.split("=")[1])
    raise KeyError(f"{name} is not in {fn}")


def draft(sg, d):
    """横向き円柱の喫水: 水没断面積比 (θ − sinθ)/2π = sg を二分法で解く(src/m_driftwood.f90 の m_driftwood_draft と同じ)。"""
    lo, hi = 0.0, 1.0
    for _ in range(60):
        xm = 0.5 * (lo + hi)
        th = 2.0 * np.arccos(1.0 - 2.0 * xm)
        if (th - np.sin(th)) / (2.0 * np.pi) < sg:
            lo = xm
        else:
            hi = xm
    return 0.5 * (lo + hi) * d


def lv(v):
    """標高の表示(+1.5、−2.0)。"""
    return f"{v:+.1f}".replace("-", "−")


def laws():
    z, zw = rd("z.txt"), rd("z_wall4.txt")
    st, sf = rd("stock.txt"), rd("stock_far.txt")
    z_har, z_yard = z[0, 1], z[0, I_YARD[0] - 1]                 # 港・貯木場の底
    z_wall, z_open, z_high = z[0, I_WALL[0] - 1], z[J_OPEN[0] - 1, I_WALL[0] - 1], zw[0, I_WALL[0] - 1]
    gv_town = rd("gv.txt")[0, I_TOWN - 1]
    wrec, vrec = param_value("dw_wrec"), param_value("dw_vrec")
    wstop, vstop = param_value("dw_wstop"), param_value("dw_vstop")
    dlog, sg = param_value("dw_dlog"), param_value("dw_sglog")
    hf = draft(sg, dlog)                                          # 丸太の喫水
    wfl, rfl, vfl = (param_value(n, "param_refloat.txt") for n in ("dw_wfloat", "dw_rfloat", "dw_vfloat"))
    vstop0 = param_value("dw_vstop", "param_vstop0.txt")
    # 流れ出す水位 = 底 + dw_hrec と、流れ出しにかかる時間 = ストック ÷ dw_wrec(各ケースの設定ファイルから)
    rel = []
    for case, fn, zb, stock in (("ise", "param.txt", z_yard, st.max()), ("wall4", "param_wall4.txt", z_yard, st.max()),
                                ("hold", "param_hold.txt", z_yard, st.max()), ("far", "param_far.txt", z_har, sf.max())):
        lev = zb + param_value("dw_hrec", fn)
        tt = np.linspace(0, 150, 15001)
        t_on = tt[np.argmax(surge(tt) > lev)]                     # 沖の水位が流れ出す水位を越える時刻 (分)
        rel.append((case, fn, lev, t_on, stock, stock / param_value("dw_wrec", fn) / 60.0))
    fig = plt.figure(figsize=(15, 10.8))
    gs = fig.add_gridspec(2, 1, height_ratios=[1.05, 1], left=0.06, right=0.985, top=0.92, bottom=0.04, hspace=0.25)
    fig.suptitle(T("材木が流れ出す・止まる・運ばれる則(make_terrain.py が作った入力と設定ファイルの値で描く。計算結果ではない)",
                   "How timber floats away, stops and is carried in ENCflow "
                   "(inputs made by make_terrain.py and the values of the settings files; not computed results)"),
                 fontsize=10.5, x=0.06, ha="left")

    # (a) 流れ出す: 貯木場の水深の閾値と、高潮の水位
    top = gs[0].subgridspec(2, 2, width_ratios=[1, 3.4], height_ratios=[2.3, 1], wspace=0.03, hspace=0.16)
    axs = fig.add_subplot(top[0, 0])
    ax = fig.add_subplot(top[0, 1], sharey=axs)
    axg = fig.add_subplot(top[1, 1], sharex=ax)
    ground = [(0, -3.6), (0, z_har), (1.2, z_har), (1.2, z_yard), (2.9, z_yard), (2.9, z_wall), (3.1, z_wall), (3.1, 0.5), (4.0, 0.8), (4.0, -3.6)]
    axs.add_patch(plt.Polygon(ground, closed=True, color=C_GROUND))
    axs.add_patch(plt.Polygon([(0, z_har), (1.2, z_har), (1.2, z_yard), (2.9, z_yard), (2.9, 0.0), (0, 0.0)], color=C_SEA, alpha=0.55))
    axs.add_patch(plt.Rectangle((2.9, z_wall), 0.2, z_high - z_wall, facecolor="none", edgecolor="k", lw=0.9, ls="-."))
    axs.plot([2.85, 3.15], [z_open, z_open], color="k", lw=1.0, ls="--")
    _logs(axs, 1.3, 2.8, 0.0, n=4)
    for x_, zb, lev, col, yl in ((1.55, z_yard, rel[0][2], C_LOG, -1.25), (2.3, z_yard, rel[2][2], "#e08214", -1.25),
                                 (0.35, z_har, rel[3][2], "#1f5f8b", -1.9)):     # dw_hrec の矢印(param.txt・param_hold.txt・param_far.txt)
        axs.annotate("", xy=(x_, lev), xytext=(x_, zb), arrowprops=dict(arrowstyle="<|-|>", color=col, lw=1.3, shrinkA=0, shrinkB=0))
        axs.text(x_ + 0.06, yl, f"{lev - zb:.1f} m", color=col, fontsize=8, va="center")
    axs.text(0.6, -3.35, T("港", "harbour"), ha="center", fontsize=8)
    axs.text(2.05, -2.45, T("貯木場", "timber yard"), ha="center", fontsize=8)
    axs.text(3.55, 1.25, T("市街地", "town"), ha="center", fontsize=8)
    axs.text(3.0, z_high + 0.12, "wall4", ha="center", fontsize=7.5)
    axs.text(0.45, 0.1, T("初期の水位 0 m", "initial level 0 m"), fontsize=7.5, color="#1f5f8b", va="bottom")
    axs.set_xlim(0, 4.0)
    axs.set_xticks([])
    axs.set_ylim(-3.6, 4.6)
    axs.set_ylabel(T("標高・水位 (m)", "elevation, water level (m)"), fontsize=9)
    axs.tick_params(labelsize=8)
    axs.set_title(T("(a) 流れ出す: 水深 > dw_hrec のとき", "(a) Floating away: depth > dw_hrec"), fontsize=9.5, loc="left")
    t = np.linspace(0, 240, 2401)
    ax.plot(t, surge(t), color="#2a78d6", lw=2.2)
    for lev, lab, ls, c in ((z_high, T(f"かさ上げした防潮壁 {lv(z_high)} m(wall4)", f"raised seawall {lv(z_high)} m (wall4)"), "-.", "k"),
                            (rel[2][2], T(f"流れ出す水位 {lv(rel[2][2])} m(遅らせる)", f"release level {lv(rel[2][2])} m (delayed)"), ":", "#e08214"),
                            (z_wall, T(f"防潮壁 {lv(z_wall)} m", f"seawall {lv(z_wall)} m"), "-", "k"),
                            (rel[0][2], T(f"流れ出す水位 {lv(rel[0][2])} m", f"release level {lv(rel[0][2])} m"), ":", C_LOG),
                            (z_open, T(f"開口部(陸閘){lv(z_open)} m", f"opening (gate) {lv(z_open)} m"), "--", "k"),
                            (z_yard, T(f"貯木場の底 {lv(z_yard)} m", f"yard bed {lv(z_yard)} m"), "-", C_GROUND),
                            (z_har, T(f"港の底 {lv(z_har)} m", f"harbour bed {lv(z_har)} m"), "-", C_GROUND)):
        ax.axhline(lev, color=c, ls=ls, lw=1.2 if c != C_GROUND else 2.0)
        ax.text(2.5, lev + 0.06, lab, fontsize=8, va="bottom", color=c if c != C_GROUND else "#8c6d3f")
    for _, _, lev, t_on, _, _ in rel[0], rel[2]:
        ax.plot(t_on, lev, "o", color="#2a78d6", ms=5, zorder=5)
        ax.text(t_on + 2.5, lev - 0.12, T(f"{t_on:.0f} 分", f"{t_on:.0f} min"), fontsize=8, va="top", color="#1f5f8b")
    ax.text(150, 3.62, T("高潮(沖の水位。tival)", "storm surge (offshore level; tival)"), fontsize=8, color="#2a78d6", ha="center", va="bottom")
    ax.set_xlim(0, 240)
    ax.tick_params(labelleft=False, labelbottom=False, labelsize=8)
    ax.grid(alpha=0.3)
    ax.text(238, -1.0, T(f"水深 = 水位 − 底。流れ出す条件: 水深 > dw_hrec かつ V > dw_vrec(= {vrec:g})\n"
                         f"速さ dw_wrec = {wrec * 1e4:g}×10⁻⁴ m³/m²/s で、残りのストックがなくなるまで",
                         f"depth = level − bed. Floats away where depth > dw_hrec and V > dw_vrec (= {vrec:g}),\n"
                         f"at dw_wrec = {wrec * 1e4:g}×10⁻⁴ m³/m²/s until the remaining stock runs out"),
            fontsize=8, ha="right", va="center", bbox=dict(facecolor="w", edgecolor="0.75", alpha=0.95, pad=3))
    names = {"ise": T("伊勢湾台風型", "Ise Bay type"), "wall4": T("防潮壁 +4 m", "seawall +4 m"),
             "hold": T("流出を遅らせる", "release delayed"), "far": T("貯木場を離す", "yard moved away")}
    colors = {"ise": "#c0392b", "wall4": "#2b8a3e", "hold": "#e08214", "far": "#1f5f8b"}
    for r, (case, fn, lev, t_on, stock, dur) in enumerate(rel):
        axg.barh(r, dur, left=t_on, height=0.55, color=colors[case], alpha=0.85)
        axg.text(t_on + dur + 2.5, r, T(f"{stock:.2g} m³/m² ÷ dw_wrec = {dur:.0f} 分", f"{stock:.2g} m³/m² ÷ dw_wrec = {dur:.0f} min"),
                 fontsize=8, va="center")
    axg.set_yticks(range(len(rel)))
    axg.set_yticklabels([f"{names[c]}({fn})" if not EN else f"{names[c]} ({fn})" for c, fn, *_ in rel], fontsize=8)
    axg.set_ylim(len(rel) - 0.4, -0.6)
    axg.set_xlim(0, 240)
    axg.grid(axis="x", alpha=0.3)
    axg.tick_params(labelsize=8)
    axg.set_xlabel(T("時刻 (分)", "time (min)"), fontsize=9)
    axg.text(0.0, 1.03, T("流れ出す期間(沖の水位が流れ出す水位を越えた時刻から、dw_wrec の速さが続いたとき)",
                          "Release period (from the time the offshore level passes the release level, at the rate dw_wrec)"),
             transform=axg.transAxes, fontsize=8, va="bottom")

    # (b) 止まる・再び流れる: (V, H) 平面
    bot = gs[1].subgridspec(1, 3, width_ratios=[1.25, 0.95, 1.55], wspace=0.08)
    ax = fig.add_subplot(bot[0])
    vmx, hmx = 0.1, 1.0
    ax.add_patch(plt.Rectangle((0, 0), vmx, hf, facecolor=C_LOG, alpha=0.35, lw=0))
    ax.add_patch(plt.Rectangle((0, hf), vstop, hmx - hf, facecolor=C_LOG, alpha=0.25, lw=0, hatch="///", edgecolor=C_LOG))
    ax.add_patch(plt.Rectangle((vfl, rfl * hf), vmx - vfl, hmx - rfl * hf, facecolor="#2b8a3e", alpha=0.18, lw=0))
    ax.axhline(hf, color=C_LOG, lw=1.4)
    ax.plot([vstop, vstop], [hf, hmx], color=C_LOG, lw=1.2, ls="--")
    ax.plot([vfl, vfl, vmx], [hmx, rfl * hf, rfl * hf], color="#2b8a3e", lw=1.2, ls="--")
    ax.text(0.098, hf / 2, T(f"H < 喫水 {hf:.2f} m: 止まる(全ケース)", f"H < draft {hf:.2f} m: stops (all cases)"),
            fontsize=8, ha="right", va="center", color="#5a3a1a")
    ax.text(vstop / 2, 0.66, T(f"V < dw_vstop = {vstop:g} m/s: 止まる", f"V < dw_vstop = {vstop:g} m/s: stops"),
            fontsize=7.8, rotation=90, ha="center", va="center", color="#5a3a1a")
    ax.text(0.075, 0.74, T(f"止まった材木が再び流れる\n(param_refloat.txt だけ)\nH > {rfl:g}·喫水 = {rfl * hf:.2f} m\nかつ V > dw_vfloat = {vfl:g} m/s",
                           f"stopped timber floats\noff again (param_refloat.txt\nonly): H > {rfl:g}·draft = {rfl * hf:.2f} m\nand V > dw_vfloat = {vfl:g} m/s"),
            fontsize=7.8, ha="center", va="center", color="#1b5e20")
    ax.text(0.05, 0.37, T("流れる材木は流れ続け、\n止まった材木はそのまま", "floating timber keeps floating;\nstopped timber stays"),
            fontsize=7.8, ha="center", va="center", color="0.3")
    ax.set_xlim(0, vmx)
    ax.set_ylim(0, hmx)
    ax.set_xlabel(T("流速 V (m/s)", "velocity V (m/s)"), fontsize=9)
    ax.set_ylabel(T("水深 H (m)", "depth H (m)"), fontsize=9)
    ax.tick_params(labelsize=8)
    ax.set_title(T("(b) 止まる・再び流れる", "(b) Stopping and floating off again"), fontsize=9.5, loc="left")
    axi = fig.add_subplot(bot[1])
    axi.axis("off")
    axi.set_xlim(0, 1)
    axi.set_ylim(0, 1)
    axi.text(0.0, 1.0, T(f"止まる(流れる材木 → 止まった材木)\n"
                         f"  H < 喫水 または V < dw_vstop のとき\n"
                         f"  速さ dw_wstop = {wstop:g} m³/m²/s\n"
                         f"  ({st.max():g} m³/m² が {st.max() / wstop:.0f} 秒で止まる)\n"
                         f"  乾いたセル(h ≤ {DD_MIN:g} m)では全部\n"
                         f"  param_vstop0.txt は dw_vstop = {vstop0:g}:\n"
                         f"  流れが遅くても止まらない(斜線が消える)\n\n"
                         f"再び流れる(param_refloat.txt だけ)\n"
                         f"  H > dw_rfloat·喫水 かつ V > dw_vfloat\n"
                         f"  速さ dw_wfloat = {wfl:g} m³/m²/s\n"
                         f"  (止まる側との間をあけて行き来を防ぐ)\n\n"
                         f"毎ステップ、流れ出す → 止まる →\n再び流れる の順にセルごとに処理する\n"
                         f"H = h + max(hs, 0) = h(土砂なし)",
                         f"Stopping (floating → stopped timber)\n"
                         f"  where H < draft or V < dw_vstop,\n"
                         f"  at dw_wstop = {wstop:g} m³/m²/s\n"
                         f"  ({st.max():g} m³/m² stops in {st.max() / wstop:.0f} s);\n"
                         f"  all at once on dry cells (h ≤ {DD_MIN:g} m).\n"
                         f"  param_vstop0.txt has dw_vstop = {vstop0:g}:\n"
                         f"  no stopping in slow flow (no hatch)\n\n"
                         f"Floating off again (param_refloat.txt)\n"
                         f"  where H > dw_rfloat·draft and V > dw_vfloat,\n"
                         f"  at dw_wfloat = {wfl:g} m³/m²/s\n"
                         f"  (a gap to the stopping side prevents\n  switching back and forth)\n\n"
                         f"Each step, cell by cell: float away →\nstop → float off again.\n"
                         f"H = h + max(hs, 0) = h (no sediment)"),
             fontsize=8, va="top", linespacing=1.4)
    axl = axi.inset_axes([0.05, 0.02, 0.55, 0.22])
    axl.add_patch(plt.Rectangle((-0.6, -0.5), 1.55, 0.5, color=C_SEA, alpha=0.55, lw=0))
    axl.add_patch(plt.Circle((0, 0), dlog / 2, color=C_LOG))
    axl.plot([-0.6, 0.95], [0, 0], color="#2a78d6", lw=1)
    axl.annotate("", xy=(0.42, -hf), xytext=(0.42, 0.0), arrowprops=dict(arrowstyle="<|-|>", lw=0.8, shrinkA=0, shrinkB=0))
    axl.text(0.46, -hf / 2, T(f"喫水\n{hf:.2f} m", f"draft\n{hf:.2f} m"), fontsize=7.2, va="center")
    axl.text(0.0, 0.33, T(f"直径 {dlog:g} m・比重 {sg:g}", f"diameter {dlog:g} m, s.g. {sg:g}"), fontsize=7.2, ha="center")
    axl.set_xlim(-0.6, 0.95)
    axl.set_ylim(-0.42, 0.42)
    axl.set_aspect("equal")
    axl.axis("off")

    # (c) 運ばれる: 水と同じ流量で運ぶ
    ax = fig.add_subplot(bot[2])
    ax.set_title(T("(c) 運ばれる: 水と同じ流れで(advect_scalar)", "(c) Carried: with the same flow as the water (advect_scalar)"), fontsize=9.5, loc="left")
    gx = np.array([0.3, 4.6, 8.9])
    ax.fill_between([gx[0], gx[2]], 0.0, 0.5, color=C_GROUND)
    ax.add_patch(plt.Polygon([(gx[0], 0.5), (gx[2], 0.5), (gx[2], 2.75), (gx[0], 3.15)], color=C_SEA, alpha=0.55))
    ax.plot([gx[1], gx[1]], [0.5, 3.6], color="k", lw=1.0, ls="--")
    _logs(ax, 0.5, 4.4, 3.08, n=5)
    _logs(ax, 4.9, 8.7, 2.8, n=2)
    ax.annotate("", xy=(5.6, 1.6), xytext=(3.6, 1.6), arrowprops=dict(arrowstyle="-|>", color="#2a78d6", lw=2.2))
    ax.text(3.45, 1.6, T("水の流量 q = u·h", "water flux q = u·h"), ha="right", va="center", fontsize=8, color="#1f5f8b")
    ax.annotate("", xy=(5.6, 3.62), xytext=(3.6, 3.62), arrowprops=dict(arrowstyle="-|>", color=C_LOG, lw=2.2))
    ax.text(3.45, 3.62, T("材木の流量 q·(hd/h)", "timber flux q·(hd/h)"), ha="right", va="center", fontsize=8, color=C_LOG)
    ax.text(2.45, 0.85, T("風上のセル", "upwind cell"), ha="center", fontsize=8)
    ax.text(6.75, 0.85, T("風下のセル", "downwind cell"), ha="center", fontsize=8)
    ax.text(gx[0], -0.25, T(f"材木の柱状の量 hd を、水の連続式と同じ辺の流量 q で運ぶ:\n"
                            f"  hd ← hd − Δt/(gv·Δx·Δy)·Σ L·q·(hd/h)面   (水: h ← h − Δt/(gv·Δx·Δy)·Σ L·q)\n"
                            f"  (hd/h)面 は辺での材木の濃度(風上側。リンクごとの MUSCL + van Leer。\n"
                            f"  f_scalar_scheme = 3 の既定)\n"
                            f"• 材木は水と同じ速さで動き、濃度 hd/h が一様なら一様のまま\n"
                            f"• 材木の量に上限はなく、材木は流れに力を返さない(運動量・抵抗に入れない)\n"
                            f"• 西端の海域マスクの列へ出た材木は領域の外へ出る(沖へ出る)\n"
                            f"• 材木の体積 = hd × gv × セルの面積(市街地は gv = {gv_town:g})",
                            f"The column amount of timber hd moves with the same edge flux q as the water:\n"
                            f"  hd ← hd − Δt/(gv·Δx·Δy)·Σ L·q·(hd/h)face   (water: h ← h − Δt/(gv·Δx·Δy)·Σ L·q)\n"
                            f"  (hd/h)face is the timber concentration at the edge (upwind side; link-wise\n"
                            f"  MUSCL + van Leer, the default f_scalar_scheme = 3)\n"
                            f"• Timber moves at the speed of the water; a uniform hd/h stays uniform\n"
                            f"• No upper limit on the amount; timber exerts no force on the flow (not in momentum or drag)\n"
                            f"• Timber that flows into the westmost sea-mask column leaves the domain (offshore)\n"
                            f"• Timber volume = hd × gv × cell area (gv = {gv_town:g} in the town)"),
            fontsize=8, va="top", linespacing=1.45)
    ax.set_xlim(0, 10)
    ax.set_ylim(-5.2, 4.3)
    ax.axis("off")
    fig.savefig(f"{FIGDIR}/laws.png", dpi=100)
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
        sea = max(f["floating"] - f["floating_town"], 0.0) / 1000      # 台帳の丸めで −0 と出さない
        # 地図は止まった材木(Wd9998)。浮いている材木は描かないので、題では台帳の量として分けて書く
        ax.set_title(T(f"{lab}: 地図 = 止まった材木。市街地に残る {town:.1f} 千 m³(浮遊を含む)、海側の浮遊 {sea:.0f} 千 m³",
                       f"{lab}: map = stopped timber; {town:.1f}k m³ left in the town (incl. floating), {sea:.0f}k m³ afloat seaward"),
                     fontsize=9)
        ax.set_xlabel("x (m)")
    axs[0].set_ylabel("y (m)")
    fig.colorbar(im, ax=axs, shrink=0.9).set_label(T("最後に止まっている材木 (m³/m²)", "timber stopped at the end (m³/m²)"))
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
    laws()
    if all(os.path.exists(f"result_{c}/FILENUMBER.csv") for c, *_ in CASES):
        maps()
        series()
        table()
    if all(os.path.exists(f"result_{c}/FILENUMBER.csv") for c, _, _ in SUPP):
        supp()
