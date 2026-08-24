# -*- coding: utf-8 -*-
# sewer_hybrid の比較図: (a) 地表貯留の時系列 A/B/C
# (b) 降雨終了時 t=1h の地表水深マップ A/B/C (c) 管内充満率の縦断 A vs B
import re
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

plt.rcParams["font.family"] = "IPAPGothic"
plt.rcParams["axes.unicode_minus"] = False

C_BLUE, C_ORANGE, C_AQUA = "#2a78d6", "#eb6834", "#1baf7a"
C_INK, C_MUTED = "#0b0b0b", "#8a8983"
RUNS = [("A", C_BLUE, "A: 幹線あり・sy=枝管適合 0.031"),
        ("B", C_ORANGE, "B: 幹線あり・sy=幹線適合 0.091"),
        ("C", C_AQUA, "C: 幹線なし(全セル枝管)")]

def read(fn):
    with open(fn) as f:
        return np.array([[float(v) for v in line.split()]
                         for line in f if line.strip()])

def read_log_ssurf(fn):
    t, s = [], []
    pat = re.compile(r"^\s*(\d+):(\d\d):(\d\d)\.\d\d\s+\S+%\s+(\S+)\s")
    for line in open(fn):
        m = pat.match(line)
        if m:
            t.append(int(m.group(1)) + int(m.group(2)) / 60.0)
            s.append(float(m.group(4)) * 1000.0)   # m -> mm
    return t, s

fig = plt.figure(figsize=(11, 9), facecolor="white")
gs = fig.add_gridspec(3, 3, height_ratios=[1.0, 0.9, 0.9], hspace=0.48, wspace=0.25)

# ---- (a) 地表貯留の時系列 ----
ax = fig.add_subplot(gs[0, :])
for run, c, label in RUNS:
    t, s = read_log_ssurf(f"result_{run}/Log.txt")
    ax.plot(t, s, color=c, lw=2.0, label=label)
    ax.annotate("%.1f mm" % s[-1], (t[-1], s[-1]), xytext=(4, 0),
                textcoords="offset points", color=c, fontsize=10, va="center")
ax.axvspan(0, 61.0 / 60.0, color="#eceae6", zorder=0)
ax.annotate("降雨 60 mm/h", (0.5, 20.5), color=C_MUTED, fontsize=10, ha="center")
ax.set_xlim(0, 3.35)
ax.set_ylim(0, 23)
ax.set_xlabel("時間 (h)")
ax.set_ylabel("地表貯留 S_surf (mm)")
ax.set_title("(a) 地表の氾濫水量: 幹線の効果(C→A,B)と sy スカラーの歪み(A↔B)",
             fontsize=11, loc="left")
ax.legend(loc="upper left", bbox_to_anchor=(0.33, 0.98), frameon=False, fontsize=10)
ax.grid(color="#eceae6", lw=0.6)
ax.set_axisbelow(True)
for sp in ("top", "right"):
    ax.spines[sp].set_visible(False)

# ---- (b) t=1h の地表水深マップ ----
cmap = LinearSegmentedColormap.from_list("blues1", ["#ffffff", "#bcd6f2", C_BLUE, "#123b6b"])
vmax = max(float(read(f"result_{r}/H0002.txt").max()) for r, _, _ in RUNS)
ims = []
for col, (run, c, label) in enumerate(RUNS):
    ax = fig.add_subplot(gs[1, col])
    h = np.ma.masked_less(read(f"result_{run}/H0002.txt"), 1.0e-3)
    im = ax.imshow(h, cmap=cmap, vmin=0, vmax=vmax,
                   extent=[0, 400, 210, 0], interpolation="nearest")
    ims.append(im)
    if run != "C":
        ax.plot([15, 375], [105, 105], color=C_ORANGE, lw=1.6, ls="--")
    ax.set_title("ラン " + run, fontsize=10, loc="left")
    ax.set_xlabel("x (m)", fontsize=9)
    if col == 0:
        ax.set_ylabel("y (m)", fontsize=9)
    else:
        ax.set_yticklabels([])
    ax.tick_params(labelsize=8)
cb = fig.colorbar(ims[-1], ax=[fig.axes[-3], fig.axes[-2], fig.axes[-1]],
                  shrink=0.85, pad=0.02)
cb.set_label("地表水深 (m) at t=1h", fontsize=9)
fig.axes[1].text(-0.12, 1.28, "(b) 降雨終了時の氾濫分布(破線=幹線の位置)",
                 transform=fig.axes[1].transAxes, fontsize=11)

# ---- (c) 管内充満率の縦断(t=1h, A vs B) ----
axl = fig.add_subplot(gs[2, :])
capT = read("data_sewer/cap_T.txt")
capC = read("data_sewer/cap_C.txt")
xg = (np.arange(1, 41) - 0.5) * 10.0
for run, c, _ in RUNS[:2]:
    hgc = read(f"result_{run}/Hgc0002.txt")
    axl.plot(xg[1:38], (hgc[10] / capT[10])[1:38], color=c, lw=2.0,
             label=f"ラン {run}: 幹線(j=11)")
    axl.plot(xg[1:38], (hgc[4] / capC[4])[1:38], color=c, lw=1.4, ls=":",
             label=f"ラン {run}: 枝管(j=5)")
axl.axhline(1.0, color=C_MUTED, lw=1.0, ls="--")
axl.annotate("満管(=1)。これより上は疑似スロットの被圧貯留", (8, 0.42),
             color=C_MUTED, fontsize=9)
axl.set_xlim(0, 400)
axl.set_ylim(0, 5.9)
axl.set_xlabel("x (m)")
axl.set_ylabel("充満率 hgc / cap")
axl.set_title("(c) t=1h の管内充満率: slot_sy(dt 上限との折り合いで緩め)による"
              "被圧側の幻の貯留が充満率 3〜5 に現れる", fontsize=11, loc="left")
axl.legend(loc="center right", frameon=False, fontsize=9)
axl.grid(color="#eceae6", lw=0.6)
axl.set_axisbelow(True)
for sp in ("top", "right"):
    axl.spines[sp].set_visible(False)

fig.suptitle("幹線1本(線)+枝管網(面)の同一インスタンス模式実験(管路連続体層)",
             fontsize=13, y=0.995)
fig.savefig("sewer_hybrid_result.png", dpi=140, bbox_inches="tight")
print("saved sewer_hybrid_result.png")
