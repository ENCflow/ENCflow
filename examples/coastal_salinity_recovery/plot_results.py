#!/usr/bin/env python3
"""coastal_salinity_recovery の図と数表(事前に make run で 8 つの計算をしておく)。

  figs/setup.png     断面の模式図(海・堤防・排水路と排水機場・低地・井戸・帯水層。計算結果を使わない)
  figs/flood.png     津波の後の 8 日間: 堤内の海水、排水機場が出した量、地下へ浸透した量(排水の速さ 2 通り)
  figs/recovery.png  その後の 8 年: 帯水層の塩水の体積と、井戸の下の塩水の界面の高さ(4 ケース)
  figs/section.png   海岸から内陸への断面の塩水の界面(津波の前・8 日後・1 年後・2 年後・4 年後・8 年後)
引数 en で英語ラベル版を en/figs/ に描く(データと描画処理は共通)。
回復の段の時刻は実時間に換算して表す(計算の時刻 × 圧縮率)。
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

NX, NY, DX = 40, 10, 25.0
A = DX * DX
ZB, SY = -8.0, 0.2
M = 100.0
YR = round(365.25 * 86400.0 / M / 200.0) * 200.0        # 圧縮した段の 1 年 (s)。gen_case.py と同じ丸め
INK, INK2, GRID, SURF = "#191919", "#666666", "#e6e6e6", "#ffffff"
C1, C2, C3, C0 = "#257de0", "#f47230", "#00b894", "#9c9c9c"
SEQ = ["#cce3fd", "#84b9f3", "#338ced", "#1757ac", "#0b2f66"]
WELLS = [(18, 5), (18, 6), (26, 5), (26, 6)]
Z = np.loadtxt("data_coast/z.txt")
SD = np.loadtxt("data_coast/sd.txt")
XKM = (np.arange(NX) + 0.5 - 2.0) * DX                   # 海岸線(列 2 と 3 の境)からの距離 (m)


def rd(tag, name, n):
    return np.fromfile(f"result_{tag}/{name}{n:04d}.bil", dtype="<f4").astype(float).reshape(NY, NX)


def ledger(tag):
    rows = list(csv.reader(open(f"result_{tag}/salt.csv")))
    hd = [h.strip() for h in rows[0]]
    d = np.array([[float(x) for x in r[:len(hd)]] for r in rows[1:]])
    return {h: d[:, i] for i, h in enumerate(hd)}


def style(ax):
    ax.set_facecolor(SURF)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=9, length=0)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def interface(tag, n):
    """断面(全行の平均)の塩水の界面と地下水面の標高 (m)"""
    hg, hgs = rd(tag, "Hg", n), rd(tag, "Hgs", n)
    return (Z - SD + hgs / SY).mean(axis=0), (Z - SD + hg / SY).mean(axis=0)


NPY = 4                                                   # 回復の段の分布出力は 1 年に 4 回


def at_wells(tag, n):
    hgs = rd(tag, "Hgs", n)
    return float(np.mean([ZB + hgs[j - 1, i - 1] / SY for i, j in WELLS]))


# ---------------- setup.png(模式図。計算結果を使わない)----------------
fig, ax = plt.subplots(figsize=(10.4, 4.2), dpi=200)
fig.patch.set_facecolor(SURF)
ax.set_xlim(-90, 1010); ax.set_ylim(-9.6, 7.4); ax.axis("off")
xs = np.concatenate(([-50.0], XKM[2:] - DX / 2, [XKM[-1] + DX / 2]))
zs = np.concatenate(([0.0], Z[0, 2:], [Z[0, -1]]))
gx = np.repeat(xs, 2)[1:-1]; gz = np.repeat(zs[:-1], 2)                     # 階段状の地表
ax.fill_between(gx, ZB, gz, color="#efe6d8", linewidth=0)                    # 帯水層
wt = 0.1 + 1.1 * np.clip(gx / 950.0, 0.0, 1.0) ** 0.6                        # 地下水面(模式)
ax.fill_between(gx, ZB, np.minimum(wt, gz), where=gx >= 0, color="#cce3fd", linewidth=0)
ax.plot(gx[gx >= 0], np.minimum(wt, gz)[gx >= 0], color=C1, linewidth=1.4)
ax.fill_between([-90, 0], ZB, 0.0, color="#a9cdf6", linewidth=0)             # 海
ax.fill_between([0, 60], [ZB + 4.0, ZB], ZB, color="#f6c7ae", linewidth=0)   # 海岸の塩水くさび(模式)
ax.plot(gx, gz, color=INK2, linewidth=1.2)
ax.plot([-90, 1010], [ZB, ZB], color=INK2, linewidth=1.2)
ax.plot([-90, 0], [0, 0], color=C1, linewidth=1.4)
ax.fill_between([100, 750], ZB, ZB + 1.6, color="#f6c7ae", linewidth=0)      # 浸透した塩水(帯水層の底)
ax.fill_between([87.5, 760], 2.0, 3.0, color="#a9cdf6", alpha=0.55, linewidth=0)   # 堤内に残った海水
for xw in (387.5, 587.5):                                                    # 井戸
    ax.plot([xw, xw], [-3.0, 2.6], color=INK, linewidth=1.6)
    ax.annotate("", xy=(xw, 3.9), xytext=(xw, 2.7), arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.2))
ax.annotate("", xy=(-30, 2.6), xytext=(90, 1.3), arrowprops=dict(arrowstyle="-|>", color=C2, lw=1.6,
                                                                 connectionstyle="arc3,rad=0.55"))
ax.annotate("", xy=(40, 4.6), xytext=(-70, 4.6), arrowprops=dict(arrowstyle="-|>", color=C1, lw=1.8))
for xr in (250.0, 500.0, 700.0):
    ax.annotate("", xy=(xr, 1.2), xytext=(xr, 2.0), arrowprops=dict(arrowstyle="-|>", color=C2, lw=1.2))
ax.annotate("", xy=(20, -2.0), xytext=(230, -2.0), arrowprops=dict(arrowstyle="-|>", color=INK2, lw=1.3))
ax.text(-85, 5.1, T("津波(潮位 4.5 m)が\n堤防を越える", "tsunami (4.5 m) overtops\nthe dike"), fontsize=9, color=INK, ha="left", va="bottom")
ax.text(52, 3.35, T("堤防\n3 m", "dike\n3 m"), fontsize=8.5, color=INK, ha="center", va="bottom")
ax.text(-45, 0.9, T("排水機場が\n海へ出す", "pumped out\nto the sea"), fontsize=9, color=INK, ha="center", va="bottom")
ax.text(240, 3.3, T("堤内に残った海水\n(水深 約 1 m)", "seawater trapped behind\nthe dike (about 1 m deep)"), fontsize=9, color=INK, ha="center", va="bottom")
ax.text(500, 4.3, T("井戸(揚水)", "wells (pumping)"), fontsize=9, color=INK, ha="center")
ax.text(820, 0.1, T("淡水の地下水\n(雨の涵養 1200 mm/年)", "fresh groundwater\n(recharge 1200 mm/yr)"), fontsize=9, color=INK, ha="center", va="center")
ax.text(425, -7.2, T("浸透した海水(帯水層の底にたまる)", "infiltrated seawater (collects at the base of the aquifer)"), fontsize=9, color=INK, ha="center", va="center")
ax.text(125, -1.6, T("海へ流れ出る", "flows out to the sea"), fontsize=9, color=INK, ha="center", va="bottom")
ax.text(-45, -4.5, T("海", "sea"), fontsize=9.5, color=INK, ha="center")
ax.text(28, -6.6, T("塩水\nくさび", "salt\nwedge"), fontsize=8, color=INK, ha="center", va="center")
ax.annotate("", xy=(0, -9.1), xytext=(950, -9.1), arrowprops=dict(arrowstyle="<->", color=INK2, lw=1.0))
ax.text(475, -9.25, T("陸 950 m(排水路と低地 675 m)。帯水層の底 −8 m(縦を強調)", "land 950 m (canal and lowland 675 m); aquifer base −8 m (vertically exaggerated)"),
        fontsize=8.5, color=INK2, ha="center", va="top")
fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.03)
fig.savefig(f"{FIGDIR}/setup.png", facecolor=SURF)
plt.close(fig)

# ---------------- flood.png(実時間 8 日)----------------
FL = {t: ledger(f"flood_{t}") for t in ("fast", "slow")}
fig, axs = plt.subplots(1, 2, figsize=(11.0, 4.2), dpi=200, sharey=True)
fig.patch.set_facecolor(SURF)
names = [T("堤内に残っている海水", "seawater still behind the dike"), T("排水機場が海へ出した量", "pumped out to the sea"),
         T("地下へ浸透した量", "infiltrated into the ground")]
for ax, (tag, title) in zip(axs, (("fast", T("速い排水(4 m³/s)", "fast drainage (4 m³/s)")), ("slow", T("遅い排水(0.4 m³/s)", "slow drainage (0.4 m³/s)")))):
    L = FL[tag]
    day = (L["time_s"] - 3600.0) / 86400.0                                   # 津波の到達(1 時間後)からの日数
    for y, c, nm in ((L["vol_surf_m3"], C1, names[0]), (L["out_struct_m3"], C2, names[1]), (L["infil_m3"], C3, names[2])):
        ax.plot(day, y / 1000.0, color=c, linewidth=2, label=nm)
    ax.set_title(title, fontsize=11, color=INK, loc="left")
    ax.set_xlim(0, 5.0); ax.set_ylim(0, 260.0)
    ax.set_xlabel(T("津波の後の日数", "days after the tsunami"), fontsize=9.5, color=INK2)
    style(ax)
axs[0].set_ylabel(T("海水の体積 (千 m³)", "seawater volume (thousand m³)"), fontsize=9.5, color=INK2)
hd, lb = axs[0].get_legend_handles_labels()
fig.legend(hd, lb, loc="upper center", ncol=3, frameon=False, fontsize=9.5, labelcolor=INK, bbox_to_anchor=(0.5, 1.0))
fig.subplots_adjust(left=0.06, right=0.985, top=0.83, bottom=0.14, wspace=0.06)
fig.savefig(f"{FIGDIR}/flood.png", facecolor=SURF)
plt.close(fig)

# ---------------- recovery.png(時間の圧縮 8 年)----------------
CASES = [("control", T("津波なし", "no tsunami"), C0), ("fast_pump", T("速い排水・井戸は継続", "fast drainage, wells on"), C1),
         ("fast_stop", T("速い排水・井戸を 2 年停止", "fast drainage, wells off for 2 years"), C3),
         ("slow_pump", T("遅い排水・井戸は継続", "slow drainage, wells on"), C2)]
RL = {t: ledger(f"rec_{t}") for t, _, _ in CASES}
fig, axs = plt.subplots(1, 2, figsize=(11.0, 3.9), dpi=200)
fig.patch.set_facecolor(SURF)
for tag, name, col in CASES:
    L = RL[tag]
    axs[0].plot(L["time_s"] / YR, L["vol_gw_m3"] / 1000.0, color=col, linewidth=2, label=name)
    axs[1].plot(np.arange(8 * NPY + 1) / NPY, [at_wells(f"rec_{tag}", n) for n in range(8 * NPY + 1)], color=col, linewidth=2, label=name)
axs[0].set_title(T("帯水層の塩水の体積 (千 m³)", "salt water in the aquifer (thousand m³)"), fontsize=11, color=INK, loc="left")
axs[1].set_title(T("井戸の下の塩水の界面の標高 (m)", "elevation of the salt interface under the wells (m)"), fontsize=11, color=INK, loc="left")
axs[1].set_ylim(-8.3, -2.5)
for ax in axs:
    ax.set_xlim(0, 8); ax.set_xlabel(T("津波の後の年数(実時間に換算)", "years after the tsunami (converted to real time)"), fontsize=9.5, color=INK2)
    style(ax)
axs[0].legend(loc="upper right", frameon=False, fontsize=9.5, labelcolor=INK)
fig.subplots_adjust(left=0.055, right=0.985, top=0.9, bottom=0.14, wspace=0.14)
fig.savefig(f"{FIGDIR}/recovery.png", facecolor=SURF)
plt.close(fig)

# ---------------- section.png ----------------
fig, axs = plt.subplots(1, 3, figsize=(12.6, 3.9), dpi=200, sharey=True)
fig.patch.set_facecolor(SURF)
for ax, (tag, name, col) in zip(axs, CASES[1:]):
    for xw in (387.5, 587.5):                             # 井戸の列の位置
        ax.plot([xw, xw], [-8.3, -3.2], color=GRID, linewidth=1.2)
    zi0, _ = interface("rec_control", 0)
    ax.plot(XKM[2:], zi0[2:], color=C0, linewidth=1.6, linestyle=(0, (4, 2)))
    for k, yy in enumerate((0, 1, 2, 4, 8)):
        zi, _ = interface(f"rec_{tag}", yy * NPY)
        ax.plot(XKM[2:], zi[2:], color=SEQ[4 - k], linewidth=2)
    ax.set_title(name, fontsize=11, color=INK, loc="left")
    ax.set_xlim(0, 950); ax.set_ylim(-8.3, -3.2)
    ax.set_xlabel(T("海岸からの距離 (m)", "distance from the coast (m)"), fontsize=9.5, color=INK2)
    style(ax)
axs[0].set_ylabel(T("標高 (m)", "elevation (m)"), fontsize=9.5, color=INK2)
handles = [plt.Line2D([0], [0], color=SEQ[4 - k], linewidth=2) for k in range(5)] + [plt.Line2D([0], [0], color=C0, linewidth=1.6, linestyle=(0, (4, 2)))]
labels = [T("津波の 8 日後", "8 days after the tsunami"), T("1 年後", "after 1 year"), T("2 年後", "after 2 years"), T("4 年後", "after 4 years"),
          T("8 年後", "after 8 years"), T("津波の前", "before the tsunami")]
fig.legend(handles, labels, loc="upper center", ncol=6, frameon=False, fontsize=9.5, labelcolor=INK, bbox_to_anchor=(0.5, 1.0))
fig.text(0.985, 0.02, T("線 = 塩水の界面(これより下が塩水。行方向の平均。帯水層の底は −8 m、津波の前の地下水面は +0.1〜1.2 m)。縦の線 = 井戸の位置",
                           "lines = salt interface (salt water below; mean over the rows; aquifer base −8 m, water table before the tsunami +0.1 to 1.2 m); vertical lines = well positions"),
         fontsize=8.5, color=INK2, ha="right")
fig.subplots_adjust(left=0.05, right=0.985, top=0.82, bottom=0.17, wspace=0.06)
fig.savefig(f"{FIGDIR}/section.png", facecolor=SURF)
plt.close(fig)

# ---------------- 数表 ----------------
if not EN:
    print("--- 津波の後の 8 日間(千 m³)")
    for tag in ("fast", "slow"):
        L = FL[tag]
        trapped = L["in_sea_m3"][-1] - L["out_sea_m3"][-1]
        clear = L["time_s"][np.argmax((L["time_s"] > 7200.0) & (L["vol_surf_m3"] < 0.01 * trapped))]
        print(f"{tag}: 海から入った {L['in_sea_m3'][-1]/1e3:.0f}、海へ戻った {L['out_sea_m3'][-1]/1e3:.0f}、堤内に残った {trapped/1e3:.0f}、"
              f"排水機場 {L['out_struct_m3'][-1]/1e3:.1f}({100*L['out_struct_m3'][-1]/trapped:.0f} %)、浸透 {L['infil_m3'][-1]/1e3:.1f}"
              f"({100*L['infil_m3'][-1]/trapped:.0f} %)、浸水の解消 {(clear-3600)/3600:.0f} 時間後、"
              f"lost_surf {L['lost_surf_m3'][-1]:.1f}、8 日後の帯水層の塩水 {L['vol_gw_m3'][-1]/1e3:.1f}")
    print("--- その後の 8 年: 帯水層の塩水の体積(千 m³)/ 井戸の下の界面の標高 (m)")
    base = RL["control"]["vol_gw_m3"][-1]
    thr = 0.1 * (RL["fast_pump"]["vol_gw_m3"][0] - base)             # 余分の塩水の目安 = 速い排水の直後の 1 割
    print(f"津波なしの帯水層の塩水 {base/1e3:.2f}(海岸の塩水くさび)。余分の塩水の目安 = 速い排水の直後の 1 割 = {thr/1e3:.1f}")
    for tag, name, _ in CASES:
        L = RL[tag]
        y = L["time_s"] / YR
        vals = "  ".join(f"{yy} 年 {L['vol_gw_m3'][np.argmin(abs(y - yy))]/1e3:.1f} / {at_wells('rec_' + tag, yy * NPY):.2f}" for yy in (0, 1, 2, 4, 8))
        zw = [at_wells('rec_' + tag, n) for n in range(8 * NPY + 1)]
        vals += f"   井戸の下の界面の最高 {max(zw):.2f} m({np.argmax(zw) / NPY:.2f} 年)"
        ex = L["vol_gw_m3"] - base
        rec = "-"
        if ex[0] > thr:
            k = np.argmax(ex < thr)
            rec = f"{y[k]:.1f} 年" if ex[k] < thr else "> 8 年"
        print(f"{tag:10s} {vals}   余分の塩水が目安を下回るまで {rec}   8 年後の余分 {ex[-1]/1e3:.2f}   "
              f"海へ出た塩水 {L['out_sea_gw_m3'][-1]/1e3:.1f}   井戸が汲んだ塩水 {L['out_pump_m3'][-1]:.1f} m³")
    if os.path.exists("result_rec_fast_pump_m50/salt.csv"):
        L1, L2 = RL["fast_pump"], ledger("rec_fast_pump_m50")
        y1, y2 = L1["time_s"] / YR, L2["time_s"] / (2 * YR)
        d = [abs(np.interp(yy, y2, L2["vol_gw_m3"]) - np.interp(yy, y1, L1["vol_gw_m3"])) / np.interp(yy, y1, L1["vol_gw_m3"]) for yy in np.arange(0.5, 8.01, 0.5)]
        print(f"圧縮率 100 と 50 の帯水層の塩水の体積の差(0.5 年ごと): 最大 {100*max(d):.2f} %")
print("saved", FIGDIR)
