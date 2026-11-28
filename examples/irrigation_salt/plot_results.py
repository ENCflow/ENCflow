#!/usr/bin/env python3
"""irrigation_salt の図と数表(事前に make run で 4 ケースを計算しておく)。

  figs/setup.png    農地の断面と、水と塩の出入りの模式図(計算結果を使わない)
  figs/profile.png  排水路からの距離に対する土の塩(10・20・30 年)。3 ケース
  figs/series.png   土の塩の総量と、排水路から出た塩の累積の時間変化
引数 en で英語ラベル版を en/figs/ に描く(データと描画処理は共通)。
時刻はすべて実時間に換算して表す(計算の時刻 × 圧縮率)。
"""
import csv
import os
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

NX, NY, DX = 41, 5, 20.0
YEAR = 365.25 * 86400.0
AREA = NX * NY * DX * DX
INK, INK2, GRID, SURF = "#191919", "#666666", "#e6e6e6", "#ffffff"
C1, C2, C3 = "#257de0", "#f47230", "#00b894"          # ケースの色(排水路なし・あり・あり + 1.3 倍)
SEQ = ["#84b9f3", "#338ced", "#0f4a96"]               # 10・20・30 年(同じ色相の濃淡)
CASES = [("nodrain", 1000.0, T("排水路なし", "no drain"), C1),
         ("drain", 1000.0, T("排水路あり", "with a drain"), C2),
         ("leach", 1000.0, T("排水路あり + 灌漑水 1.3 倍", "with a drain, irrigation x 1.3"), C3)]


def rd(tag, name, n):
    return np.fromfile(f"result_{tag}/{name}{n:04d}.bil", dtype="<f4").astype(float).reshape(NY, NX)


def ledger(tag, m):
    rows = list(csv.reader(open(f"result_{tag}/wq.csv")))
    hd = [h.strip() for h in rows[0]]
    d = np.array([[float(x) for x in r[:len(hd)]] for r in rows[1:]])
    out = {h: d[:, i] for i, h in enumerate(hd)}
    out["year"] = d[:, 0] * m / YEAR
    return out


def style(ax):
    ax.set_facecolor(SURF)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=9, length=0)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


# ---------------- setup.png(模式図。計算結果を使わない)----------------
fig, ax = plt.subplots(figsize=(9.6, 3.8), dpi=200)
fig.patch.set_facecolor(SURF)
ax.set_xlim(-40, 880); ax.set_ylim(3.5, 12.6); ax.axis("off")
ax.fill_between([0, 800], 5.0, 10.0, color="#efe6d8", linewidth=0)             # 土層
ax.fill_between([0, 800], 5.0, [7.0, 6.6], color="#cce3fd", linewidth=0)       # 地下水
ax.fill_between([800, 820], 5.0, 6.5, color="#efe6d8", linewidth=0)
ax.fill_between([800, 820], 6.5, 6.6, color="#84b9f3", linewidth=0)            # 排水路の水
ax.plot([0, 800, 800, 820, 820], [10, 10, 6.5, 6.5, 10], color=INK2, linewidth=1.2)
ax.plot([0, 820], [5, 5], color=INK2, linewidth=1.2)
ax.plot([0, 800], [7.0, 6.6], color=C1, linewidth=1.6)
for x in (80, 240, 400, 560, 720):
    ax.annotate("", xy=(x, 10.1), xytext=(x, 11.5), arrowprops=dict(arrowstyle="-|>", color=C1, lw=1.4))
    ax.annotate("", xy=(x + 50, 11.5), xytext=(x + 50, 10.1), arrowprops=dict(arrowstyle="-|>", color=C2, lw=1.4))
ax.annotate("", xy=(795, 6.9), xytext=(560, 6.9), arrowprops=dict(arrowstyle="-|>", color=INK2, lw=1.4))
ax.text(80, 11.75, T("灌漑水 1000 mm/年(塩分 0.5 g/L)", "irrigation 1000 mm/yr (0.5 g/L salt)"), fontsize=9.5, color=INK, ha="left")
ax.text(480, 11.75, T("蒸発散(水だけが抜ける)", "evapotranspiration (water only)"), fontsize=9.5, color=INK, ha="left")
ax.text(400, 8.4, T("土層 5 m(有効間隙率 0.2)。塩は土の水に残る", "soil layer 5 m (porosity 0.2); the salt stays in the soil water"),
        fontsize=9.5, color=INK, ha="center")
ax.text(300, 6.0, T("地下水", "groundwater"), fontsize=9.5, color=INK, ha="center")
ax.text(670, 7.25, T("排水路へ流れて塩を運び出す", "flows to the drain and carries salt out"), fontsize=9, color=INK, ha="center")
ax.text(825, 8.3, T("排水路\n(水位固定)", "drain\n(fixed\nlevel)"), fontsize=9, color=INK, ha="left", va="center")
ax.annotate("", xy=(0, 4.3), xytext=(800, 4.3), arrowprops=dict(arrowstyle="<->", color=INK2, lw=1.0))
ax.text(400, 3.75, T("農地 800 m(排水路なしのケースは東端も農地)", "field 800 m (the east end is also field in the no-drain case)"),
        fontsize=9, color=INK2, ha="center")
fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.02)
fig.savefig(f"{FIGDIR}/setup.png", facecolor=SURF)
plt.close(fig)

# ---------------- profile.png ----------------
dist = (NX - 1 - np.arange(NX - 1)) * DX              # 排水路(東端の列)からの距離 (m)
fig, axs = plt.subplots(1, 3, figsize=(12.0, 3.9), dpi=200, sharey=True)
fig.patch.set_facecolor(SURF)
for ax, (tag, m, name, col) in zip(axs, CASES):
    for k, (n, yr) in enumerate(((2, 10), (4, 20), (6, 30))):
        cg = rd(tag, "Cg", n)[NY // 2, :NX - 1] / 1000.0
        ax.plot(dist, cg, color=SEQ[k], linewidth=2, solid_capstyle="round")
        ax.text(dist[0] + 8, cg[0], T(f"{yr} 年", f"{yr} yr"), fontsize=9, color=INK, va="center", ha="left")
    ax.set_title(name, fontsize=11, color=INK, loc="left")
    ax.set_xlim(0, 900); ax.set_xticks([0, 200, 400, 600, 800]); ax.set_ylim(0, 20)
    ax.set_xlabel(T("排水路(東端)からの距離 (m)", "distance from the drain (east end) (m)"), fontsize=9.5, color=INK2)
    style(ax)
axs[0].set_ylabel(T("土の塩 (kg/m²)", "salt in the soil (kg/m²)"), fontsize=9.5, color=INK2)
fig.subplots_adjust(left=0.055, right=0.985, top=0.9, bottom=0.14, wspace=0.08)
fig.savefig(f"{FIGDIR}/profile.png", facecolor=SURF)
plt.close(fig)

# ---------------- series.png ----------------
fig, axs = plt.subplots(1, 2, figsize=(11.0, 3.9), dpi=200)
fig.patch.set_facecolor(SURF)
led = {tag: ledger(tag, m) for tag, m, _, _ in CASES}
for tag, m, name, col in CASES:
    L = led[tag]
    axs[0].plot(L["year"], L["mass_gw_g"] / AREA / 1000.0, color=col, linewidth=2, label=name)
    axs[1].plot(L["year"], (L["out_stage_g"] - L["in_stage_g"]) / 1.0e6, color=col, linewidth=2, label=name)
axs[0].set_title(T("土の塩(農地の平均)(kg/m²)", "salt in the soil, field average (kg/m²)"), fontsize=11, color=INK, loc="left")
axs[1].set_title(T("排水路から出た塩の累積 (t)", "cumulative salt carried out by the drain (t)"), fontsize=11, color=INK, loc="left")
for ax in axs:
    ax.set_xlim(0, 30); ax.set_xlabel(T("年(実時間に換算)", "year (converted to real time)"), fontsize=9.5, color=INK2)
    style(ax)
axs[0].legend(loc="upper left", frameon=False, fontsize=9.5, labelcolor=INK)
fig.subplots_adjust(left=0.055, right=0.985, top=0.9, bottom=0.14, wspace=0.14)
fig.savefig(f"{FIGDIR}/series.png", facecolor=SURF)
plt.close(fig)

# ---------------- 数表 ----------------
if not EN:
    ev = {}
    print("ケース            灌漑で入った塩(t) 土の塩(t) 排水路から出た塩(t) 収支の残差(相対)  蒸発散(mm/年)  排水(mm/年)")
    for tag, m, name, _ in CASES + [("drain_m100", 100.0, "排水路あり(M = 100)", C2)]:
        if not os.path.exists(f"result_{tag}/wq.csv"):
            continue
        L = ledger(tag, m)
        e = np.array([[float(x) for x in r] for r in list(csv.reader(open(f"result_{tag}/evap.csv")))[1:]])
        yrs = e[-1, 0] * m / YEAR
        etmm = e[-1, -1] / AREA / yrs * 1000.0
        rain = L["in_rain_g"][-1]
        out = L["out_stage_g"][-1] - L["in_stage_g"][-1]
        res = (L["mass_gw_g"][-1] + L["mass_surface_g"][-1] + out - rain) / rain
        irr = rain / 500.0 / AREA / yrs * 1000.0          # 灌漑水量 (mm/年) = 塩 / 濃度
        print(f"{name:22s} {rain/1e6:9.2f} {L['mass_gw_g'][-1]/1e6:9.2f} {out/1e6:9.2f}      {res:9.1e}   {etmm:8.1f}   {irr - etmm:8.1f}")
    print()
    print("排水路からの距離 (m)                 " + "".join(f"{d:8.0f}" for d in (20, 100, 200, 300, 400, 600, 800)))
    for tag, m, name, _ in CASES + [("drain_m100", 100.0, "排水路あり(M = 100)", C2)]:
        if not os.path.exists(f"result_{tag}/Cg0006.bil"):
            continue
        cg = rd(tag, "Cg", 6)[NY // 2, :] / 1000.0
        hg = rd(tag, "Hg", 6)[NY // 2, :]
        idx = [NX - 1 - int(d / DX) for d in (20, 100, 200, 300, 400, 600, 800)]
        print(f"{name:20s} 30 年の土の塩 kg/m2 " + "".join(f"{cg[i]:8.2f}" for i in idx))
        print(f"{'':20s} 土の水の塩分 g/L    " + "".join(f"{cg[i]/hg[i]:8.1f}" for i in idx))
    if os.path.exists("result_drain_m100/Cg0006.bil"):
        a, b = rd("drain", "Cg", 6)[:, :NX - 1], rd("drain_m100", "Cg", 6)[:, :NX - 1]
        print(f"\n圧縮率 1000 と 100 の 30 年の土の塩の差の最大(相対): {np.abs(a - b).max() / b.max():.1e}")
print("saved", FIGDIR)
