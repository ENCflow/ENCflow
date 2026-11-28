#!/usr/bin/env python3
"""terminal_lake の図と数表(事前に make run で 6 ケースを計算しておく)。

  figs/setup.png     湖の断面と、縮小・析出・再上昇の模式図(計算結果を使わない)
  figs/fate.png      塩のゆくえ(湖水に溶けている・湖底の析出物・陸地化した湖底)の時間変化。5 ケースと湖の最大水深
  figs/maps.png      6 年目の濃度の分布(混合なし・混合あり)と、12 年目の析出物の分布(salt)
  figs/compress.png  湖の体積を、湖面を水平とみなした水収支の解と比べる(圧縮率 1000 と 10000。縮小の 12 年)
引数 en で英語ラベル版を en/figs/ に描く(データと描画処理は共通)。
時刻はすべて実時間に換算して表す(計算の時刻 × 圧縮率)。
"""
import csv
import math
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)

N, DX = 61, 200.0
A = DX * DX
YEAR = 365.25 * 86400.0
K = math.pi * 5000.0 ** 2 / 10.0
E = 1.0 / YEAR
ETA0 = 8.0
Q0 = E * K * ETA0
INK, INK2, GRID, SURF = "#191919", "#666666", "#e6e6e6", "#ffffff"
COL = ["#257de0", "#f47230", "#00b894"]          # 湖水 / 湖底の析出物 / 陸地
SEQ = LinearSegmentedColormap.from_list("seq", ["#f4f8fe", "#cce3fd", "#84b9f3", "#338ced", "#1757ac", "#0e3d7e"])
Z = np.loadtxt("data_lake/z.txt")


def rd(tag, name, n):
    return np.fromfile(f"result_{tag}/{name}{n:04d}.bil", dtype="<f4").astype(float).reshape(N, N)


def ledger(tag, m):
    rows = list(csv.reader(open(f"result_{tag}/wq.csv")))
    hd = [h.strip() for h in rows[0]]
    d = np.array([[float(x) for x in r[:len(hd)]] for r in rows[1:]])
    out = {h: d[:, i] for i, h in enumerate(hd)}
    out["year"] = d[:, 0] * m / YEAR
    return out


def fate(tag, m=1000.0, years=24):
    """年ごとに (年, 湖水 %, 湖底の析出物 %, 陸地 %, 最大水深, 湖水の平均濃度 g/L, 湖の体積)"""
    L = ledger(tag, m)
    out = []
    for n in range(0, years + 1):
        if not os.path.exists(f"result_{tag}/H{n:04d}.bil"):
            break
        H, C = rd(tag, "H", n), rd(tag, "C", n)
        it = np.argmin(abs(L["year"] - n))
        tot = L["mass_surface_g"][it] + L["mass_pool_g"][it]
        wet = H > 0.05                               # 湖(水深 5 cm 以上)
        mlake = (C[wet] * H[wet]).sum() * A
        pw = 0.0
        if os.path.exists(f"result_{tag}/B{n:04d}.bil"):
            pw = (rd(tag, "B", n)[wet] * 0.1).sum() * A          # kg/ha -> g/m2
        land = (L["mass_surface_g"][it] - mlake) + (L["mass_pool_g"][it] - pw)
        out.append((n, 100 * mlake / tot, 100 * pw / tot, 100 * land / tot, H.max(),
                    mlake / max(H[wet].sum() * A, 1.0) / 1000.0, H.sum() * A))
    return np.array(out)


def style(ax):
    ax.set_facecolor(SURF)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=8.5, length=0)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


CASES = [("nomix", T("混合なし・溶解度の上限なし", "no mixing, no solubility limit")),
         ("mix", T("水平の混合あり", "with horizontal mixing")),
         ("salt", T("混合 + 溶解度 360 g/L\n(塩化ナトリウムに近い。浸かればすぐ溶ける)",
                    "mixing + solubility 360 g/L\n(like sodium chloride; dissolves at once)")),
         ("slow", T("混合 + 溶解度 360 g/L\n+ 溶けにくい析出物", "mixing + solubility 360 g/L\n+ slowly dissolving precipitate")),
         ("gypsum", T("混合 + 溶解度 2.4 g/L\n(石膏に近い物質)", "mixing + solubility 2.4 g/L\n(a substance like gypsum)"))]
LAB = [T("湖水に溶けている", "dissolved in the lake water"), T("湖底の析出物(水面下)", "precipitate on the lake bed (under water)"),
       T("陸地化した湖底に残る", "left on the exposed lake bed")]

# ---------------- setup.png(模式図。計算結果を使わない)----------------
SALT = "#f47230"
rr = np.linspace(-5.6, 5.6, 561)
zb = 10.0 * (rr / 5.0) ** 2
fig, axs = plt.subplots(1, 3, figsize=(12.6, 3.6), dpi=200)
fig.patch.set_facecolor(SURF)
PAN = [(8.0, 0.0, T("初め: 流入と蒸発が釣り合う", "start: inflow balances evaporation")),
       (0.6, 1.0, T("流入が減る: 湖が縮み、塩が析出して残る", "less inflow: the lake shrinks and salt precipitates")),
       (6.0, 0.4, T("流入が戻る: 浸かった所から塩が溶ける", "inflow restored: flooded salt dissolves"))]
for ax, (eta, band, title) in zip(axs, PAN):
    ax.set_xlim(-5.8, 5.8); ax.set_ylim(-2.2, 13.2); ax.axis("off")
    ax.fill_between(rr, -1.2, zb, color="#efe6d8", linewidth=0)
    ax.fill_between(rr, zb, np.maximum(zb, eta), color="#cce3fd", linewidth=0)
    ax.plot(rr, zb, color=INK2, linewidth=1.2)
    re = 5.0 * (eta / 10.0) ** 0.5
    ax.plot([-re, re], [eta, eta], color=COL[0], linewidth=1.6)
    if band > 0.0:                                        # 析出物(湖底に沿う帯。標高 5.2 m より下)
        ax.plot(rr[zb <= 5.2], zb[zb <= 5.2] + 0.12, color=SALT, linewidth=3.2, solid_capstyle="butt", alpha=band)
    ax.annotate("", xy=(0.0, eta + 0.25), xytext=(0.0, 11.6), arrowprops=dict(arrowstyle="-|>", color=COL[0], lw=1.6))
    for x in (-1.7, 1.7):
        if abs(x) < re:
            ax.annotate("", xy=(x, eta + 2.6), xytext=(x, eta + 0.25), arrowprops=dict(arrowstyle="-|>", color=SALT, lw=1.4))
    ax.set_title(title, fontsize=10.5, color=INK, loc="left")
axs[0].text(0.15, 12.1, T("流入(川の水。塩分 0.5 g/L)", "inflow (river, 0.5 g/L salt)"), fontsize=9, color=INK, ha="left")
axs[0].text(1.9, 9.0, T("蒸発 1 m/年\n(水だけが抜ける)", "evaporation\n1 m/yr\n(water only)"), fontsize=9, color=INK, ha="left", va="bottom")
axs[0].text(0.0, 3.6, T("湖水 10 g/L", "lake water 10 g/L"), fontsize=9.5, color=INK, ha="center")
axs[1].text(0.0, 12.1, T("流入を 5 % に", "inflow cut to 5 %"), fontsize=9, color=INK, ha="center")
axs[1].text(0.25, 7.4, T("陸地になった湖底に\n塩(析出物)が残る", "salt (precipitate)\nstays on the exposed\nlake bed"), fontsize=9, color=INK, ha="left")
axs[2].text(0.15, 12.1, T("流入を元に戻す", "inflow restored"), fontsize=9, color=INK, ha="left")
axs[2].text(0.0, 2.9, T("溶けやすい塩はすぐ溶け、\n溶けにくい塩は湖底に残る", "soluble salt dissolves\nat once; sparingly soluble\nsalt stays on the bed"), fontsize=9, color=INK, ha="center")
axs[0].annotate("", xy=(-5.0, -1.7), xytext=(5.0, -1.7), arrowprops=dict(arrowstyle="<->", color=INK2, lw=1.0))
axs[0].text(0.0, -2.1, T("すり鉢の直径 10 km、深さ 10 m(縦を強調)", "bowl 10 km across, 10 m deep (vertically exaggerated)"),
            fontsize=8.5, color=INK2, ha="center", va="top")
fig.subplots_adjust(left=0.01, right=0.99, top=0.92, bottom=0.06, wspace=0.03)
fig.savefig(f"{FIGDIR}/setup.png", facecolor=SURF)
plt.close(fig)

# ---------------- fate.png ----------------
data = {tag: fate(tag) for tag, _ in CASES if os.path.exists(f"result_{tag}/wq.csv")}
fig, axs = plt.subplots(2, 3, figsize=(12.5, 7.4), dpi=200)
fig.patch.set_facecolor(SURF)
for ax, (tag, title) in zip(axs.flat, CASES):
    if tag not in data:
        ax.axis("off")
        continue
    f = data[tag]
    bot = np.zeros(len(f))
    for k in range(3):
        ax.bar(f[:, 0], f[:, 1 + k], bottom=bot, width=0.72, color=COL[k], edgecolor=SURF, linewidth=0.6)
        bot += f[:, 1 + k]
    ax.set_title(title, fontsize=10.5, color=INK, loc="left")
    ax.set_ylim(0, 100); ax.set_xlim(-0.8, 24.8)
    ax.set_yticks([0, 25, 50, 75, 100]); ax.set_xticks([0, 5, 10, 15, 20])
    ax.axvline(12.5, color=INK2, linewidth=0.8)
    style(ax)
ax = axs.flat[5]
f = max(data.values(), key=len)
ax.plot(f[:, 0], f[:, 4], color=COL[0], linewidth=2, solid_capstyle="round")
ax.set_title(T("湖の最大水深 (m)。5 つのケースで共通", "maximum lake depth (m), all cases"),
             fontsize=10.5, color=INK, loc="left")
ax.set_ylim(0, 9); ax.set_xlim(-0.8, 24.8); ax.set_xticks([0, 5, 10, 15, 20])
ax.axvline(12.5, color=INK2, linewidth=0.8)
style(ax)
for ax in axs[1, :]:
    ax.set_xlabel(T("年(実時間に換算)", "year (converted to real time)"), fontsize=9, color=INK2)
for ax in axs[:, 0]:
    ax.set_ylabel(T("物質の全量に占める割合 (%)", "share of the total mass (%)"), fontsize=9, color=INK2)
handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in COL]
fig.legend(handles, LAB, loc="upper left", bbox_to_anchor=(0.045, 0.985), ncol=3, frameon=False,
           fontsize=9.5, labelcolor=INK, handlelength=1.2, columnspacing=2.0)
fig.text(0.985, 0.965, T("縦線: 12 年目の後に流入を元に戻す", "vertical line: the inflow is restored after year 12"),
         fontsize=9.5, color=INK2, ha="right", va="center")
fig.subplots_adjust(left=0.06, right=0.985, top=0.88, bottom=0.075, hspace=0.42, wspace=0.16)
fig.savefig(f"{FIGDIR}/fate.png", facecolor=SURF)
plt.close(fig)

# ---------------- maps.png ----------------
if all(os.path.exists(f"result_{t}/C0006.bil") for t in ("nomix", "mix")) and os.path.exists("result_salt/B0012.bil"):
    fig, axs = plt.subplots(1, 3, figsize=(12.0, 4.3), dpi=200)
    fig.patch.set_facecolor(SURF)
    ext = [0, N * DX / 1000.0, 0, N * DX / 1000.0]
    panels = [("nomix", "C", 6, 0.001, T("6 年目の濃度 (g/L)。混合なし", "concentration in year 6 (g/L)\nno mixing"), 100.0),
              ("mix", "C", 6, 0.001, T("6 年目の濃度 (g/L)。混合あり", "concentration in year 6 (g/L)\nwith mixing"), 100.0),
              ("salt", "B", 12, 1.0e-4, T("12 年目の析出物 (kg/m²)。混合 + 溶解度", "precipitate in year 12 (kg/m²)\nmixing + solubility"), None)]
    for ax, (tag, name, n, fac, title, vmax) in zip(axs, panels):
        v = rd(tag, name, n) * fac
        if name == "C":
            v = np.where(rd(tag, "H", n) > 0.05, v, np.nan)
        else:
            v = np.where(v > 0.0, v, np.nan)
        im = ax.imshow(v, cmap=SEQ, vmin=0.0, vmax=vmax, extent=ext, interpolation="nearest")
        ax.contour(np.linspace(DX / 2000, ext[1] - DX / 2000, N), np.linspace(ext[1] - DX / 2000, DX / 2000, N), Z,
                   levels=[2, 4, 6, 8], colors=INK2, linewidths=0.5)
        ax.set_title(title, fontsize=10.5, color=INK, loc="left")
        ax.set_xlabel("x (km)", fontsize=9, color=INK2)
        ax.tick_params(colors=INK2, labelsize=8.5, length=0)
        for sp in ax.spines.values():
            sp.set_color(GRID)
        cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
        cb.ax.tick_params(colors=INK2, labelsize=8.5, length=0)
        cb.outline.set_edgecolor(GRID)
    axs[0].set_ylabel("y (km)", fontsize=9, color=INK2)
    fig.text(0.01, 0.015, T("等高線は湖底の標高 2・4・6・8 m。色のない所は水のないセル(濃度)・析出物のないセル",
                            "contours: lake-bed elevation 2, 4, 6, 8 m; uncoloured cells have no water (concentration) or no precipitate"),
             fontsize=8.5, color=INK2, ha="left")
    fig.subplots_adjust(left=0.05, right=0.97, top=0.9, bottom=0.13, wspace=0.22)
    fig.savefig(f"{FIGDIR}/maps.png", facecolor=SURF)
    plt.close(fig)

# ---------------- compress.png(水収支の解との比較)----------------
etas = np.linspace(0.0, 10.0, 20001)
vols = np.array([np.maximum(e - Z, 0.0).sum() * A for e in etas])
area_of = lambda V: (Z < np.interp(V, vols, etas)).sum() * A
q1 = 0.05 * Q0
V = np.maximum(ETA0 - Z, 0.0).sum() * A
h = YEAR / 2000.0
rt, rv = [0.0], [V]
while rt[-1] < 12.0 * YEAR - 1e-6:                    # ラスタ地形の面積・体積で dV/dt = Q − E·A を解く(RK4)
    k1 = q1 - E * area_of(V); k2 = q1 - E * area_of(V + 0.5 * h * k1)
    k3 = q1 - E * area_of(V + 0.5 * h * k2); k4 = q1 - E * area_of(V + h * k3)
    V += h * (k1 + 2 * k2 + 2 * k3 + k4) / 6.0
    rt.append(rt[-1] + h); rv.append(V)
rt, rv = np.array(rt) / YEAR, np.array(rv)


def volume(tag, m):
    t, v = [], []
    for line in open(f"result_{tag}/Log.txt"):
        p = line.split()
        if len(p) >= 8 and p[0].count(":") == 2 and p[1].endswith("%"):
            hh, mm, ss = p[0].split(":")
            t.append((int(hh) * 3600 + int(mm) * 60 + float(ss)) * m / YEAR)
            v.append(float(p[2]) * Z.size * A)
    t, v = np.array(t), np.array(v)
    keep = t <= 12.0
    return t[keep], v[keep]


comp = [(tag, m, lab, c) for tag, m, lab, c in (("mix", 1000.0, "M = 1000", COL[0]), ("mix_m10000", 10000.0, "M = 10000", COL[1]))
        if os.path.exists(f"result_{tag}/Log.txt")]
if comp:
    fig, axs = plt.subplots(1, 2, figsize=(11.0, 3.9), dpi=200)
    fig.patch.set_facecolor(SURF)
    axs[0].plot(rt, rv / 1e6, color="#9c9c9c", linewidth=3.5, label=T("水収支の解(湖面は水平)", "water-balance solution (level lake)"))
    for tag, m, lab, c in comp:
        t, v = volume(tag, m)
        axs[0].plot(t, v / 1e6, color=c, linewidth=1.6, label=lab)
        axs[1].plot(t[1:], 100 * (v[1:] - np.interp(t[1:], rt, rv)) / np.interp(t[1:], rt, rv), color=c, linewidth=2, label=lab)
    axs[0].set_yscale("log"); axs[0].set_ylim(0.3, 400.0)
    axs[0].set_yticks([1, 10, 100]); axs[0].set_yticklabels(["1", "10", "100"]); axs[0].minorticks_off()
    axs[0].set_title(T("湖の体積 (百万 m³。対数目盛)", "lake volume (million m³; log scale)"), fontsize=11, color=INK, loc="left")
    axs[1].set_title(T("水収支の解との差 (%)", "difference from the water-balance solution (%)"), fontsize=11, color=INK, loc="left")
    for ax in axs:
        ax.set_xlim(0, 12); ax.set_xlabel(T("年(実時間に換算)", "year (converted to real time)"), fontsize=9.5, color=INK2)
        style(ax)
        ax.legend(loc="upper right" if ax is axs[0] else "upper left", frameon=False, fontsize=9.5, labelcolor=INK)
    fig.subplots_adjust(left=0.055, right=0.985, top=0.9, bottom=0.14, wspace=0.14)
    fig.savefig(f"{FIGDIR}/compress.png", facecolor=SURF)
    plt.close(fig)

# ---------------- 数表 ----------------
if not EN:
    yrs = (4, 8, 12, 13, 14, 16, 20, 24)
    print("ケース    年: 湖水 % / 湖底の析出物 % / 陸地 %(下の行は湖水の平均濃度 g/L)")
    for tag, _ in CASES:
        if tag not in data:
            continue
        f = data[tag]
        L = ledger(tag, 1000.0)
        c0 = 1500.0 if tag == "gypsum" else 10000.0
        m0 = c0 * np.maximum(ETA0 - Z, 0.0).sum() * A
        res = (L["mass_surface_g"][-1] + L["mass_pool_g"][-1] - m0 - L["in_point_g"][-1]) / (m0 + L["in_point_g"][-1])
        print(f"{tag:8s}" + "  ".join(f"{int(r[0])}: {r[1]:.0f}/{r[2]:.0f}/{r[3]:.0f}" for r in f if int(r[0]) in yrs)
              + f"   収支の残差 {res:.1e}")
        print(f"{'':8s}" + "  ".join(f"{int(r[0])}: {r[5]:.1f}" for r in f if int(r[0]) in yrs))
    for tag, m, lab, c in comp:
        t, v = volume(tag, m)
        d = 100 * (v - np.interp(t, rt, rv)) / np.interp(t, rt, rv)
        print(f"{lab}: 水収支の解との体積の差 " + "  ".join(f"{y} 年 {d[np.argmin(abs(t - y))]:+.2f} %" for y in (2, 4, 6, 8, 10, 12)))
print("saved", FIGDIR)
