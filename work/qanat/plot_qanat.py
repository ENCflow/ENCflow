# -*- coding: utf-8 -*-
# qanat ケースの図化: (a) 縦断面(坑道と地下水位) (b) 平面の地表水深
# (c) 出口流量の時系列。result/ を読んで qanat_result.png を保存する。
import csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

plt.rcParams["font.family"] = "IPAPGothic"
plt.rcParams["axes.unicode_minus"] = False

# 配色(dataviz 参照パレット: 青=系列1, 橙=系列2。文脈線は無彩色)
C_BLUE, C_ORANGE = "#2a78d6", "#eb6834"
C_INK, C_MUTED = "#0b0b0b", "#8a8983"

nx, ny, dx = 40, 21, 10.0
jline0 = 10                     # 坑道の行(0 始まり)
i1, i2 = 2, 35                  # 坑道セル範囲(1 始まり)
sd, d2, sy2 = 1.0, 8.0, 0.2     # 土層厚・層2厚・比湧水量
cap, syc, syslot = 0.1, 10.0, 1.0 / 0.02   # 坑道: 容量・1/sy_c・1/sy_slot

def read(fn):
    with open(fn) as f:
        return np.array([[float(v) for v in line.split()]
                         for line in f if line.strip()])

x = (np.arange(1, nx + 1) - 0.5) * dx
z = read("data_qanat/z.txt")[jline0]
zbot = read("data_qanat/gwc_bot.txt")[jline0]
hg2_0 = read("result/Hg20000.txt")[jline0]
hg2_1 = read("result/Hg29998.txt")[jline0]
hgc_1 = read("result/Hgc9998.txt")[jline0]
h_fin = read("result/H9998.txt")

wt0 = z - sd - d2 + hg2_0 / sy2            # 初期地下水位
wt1 = z - sd - d2 + hg2_1 / sy2            # 最終地下水位
hcnd = np.where(hgc_1 <= cap, zbot + hgc_1 * syc,
                zbot + cap * syc + (hgc_1 - cap) * syslot)  # 坑道水頭
line = slice(i1 - 1, i2)                   # 坑道セルの 0 始まりスライス

fig = plt.figure(figsize=(11, 8.5), facecolor="white")
gs = fig.add_gridspec(3, 1, height_ratios=[1.3, 1.0, 0.8], hspace=0.42)

# ---- (a) 縦断面 ----
ax = fig.add_subplot(gs[0])
ax.plot(x, z, color=C_INK, lw=1.6)
ax.plot(x[line], zbot[line], color=C_MUTED, lw=1.4, ls="--")
ax.plot(x, wt0, color=C_BLUE, lw=1.2, ls=":", alpha=0.7)
ax.plot(x, wt1, color=C_BLUE, lw=2.0)
ax.plot(x[line], hcnd[line], color=C_ORANGE, lw=2.0)
ax.plot(x[i2 - 1], z[i2 - 1], "v", color=C_ORANGE, ms=9, zorder=5)
ax.annotate("地表", (x[4], z[4]), xytext=(0, 6), textcoords="offset points",
            color=C_INK, fontsize=10)
ax.annotate("坑道床(勾配 0.004)", (x[14], zbot[14]), xytext=(0, -16),
            textcoords="offset points", color=C_MUTED, fontsize=10)
ax.annotate("初期地下水位(z−1.8 m)", (x[2], wt0[2]), xytext=(4, 8),
            textcoords="offset points", color=C_BLUE, alpha=0.8, fontsize=10)
ax.annotate("最終地下水位(8 h)", (x[8], wt1[8]), xytext=(0, -20),
            textcoords="offset points", color=C_BLUE, fontsize=10)
ax.annotate("坑道水頭", (x[28], hcnd[28]), xytext=(-4, 8),
            textcoords="offset points", color=C_ORANGE, fontsize=10)
ax.annotate("出口(崖中腹)", (x[i2 - 1], z[i2 - 1]), xytext=(10, 10),
            textcoords="offset points", color=C_ORANGE, fontsize=10)
ax.set_xlim(0, 400)
ax.set_xlabel("x (m)")
ax.set_ylabel("標高 (m)")
ax.set_title("(a) 縦断面(j=11 の坑道線に沿う): 集水部 i=2..31・導水部 i=32..34・出口 i=35",
             fontsize=11, loc="left")
ax.grid(color="#eceae6", lw=0.6)
ax.set_axisbelow(True)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)

# ---- (b) 平面の地表水深 ----
ax = fig.add_subplot(gs[1])
cmap = LinearSegmentedColormap.from_list("blues1", ["#ffffff", "#bcd6f2", C_BLUE, "#123b6b"])
hm = np.ma.masked_less(h_fin, 1.0e-4)
ext = [0, nx * dx, ny * dx, 0]             # 行1 = 北を上に
im = ax.imshow(hm, cmap=cmap, vmin=0, vmax=float(h_fin.max()),
               extent=ext, interpolation="nearest")
ax.plot([x[i1 - 1], x[i2 - 1]], [105, 105], color=C_ORANGE, lw=2.0, ls="--")
ax.plot(x[i2 - 1], 105, "v", color=C_ORANGE, ms=9)
ax.annotate("坑道(地下)", (x[10], 105), xytext=(0, -14),
            textcoords="offset points", color=C_ORANGE, fontsize=10)
ax.annotate("湧出 → 地表流 → 湛水", (185, 45), color=C_INK, fontsize=10)
cb = fig.colorbar(im, ax=ax, shrink=0.9, pad=0.01)
cb.set_label("地表水深 (m)")
ax.set_xlabel("x (m)")
ax.set_ylabel("y (m)")
ax.set_title("(b) 8 時間後の地表水深(出口からの湧出流と低地の湛水)",
             fontsize=11, loc="left")

# ---- (c) 出口流量の時系列 ----
ax = fig.add_subplot(gs[2])
t, q = [], []
with open("result/fluxes/flux0001.csv") as f:
    for row in csv.reader(f):
        if not row or row[0].startswith("#"):
            continue
        t.append(float(row[0]))
        q.append(float(row[2]) * 1000.0)   # m3/s -> L/s
ax.plot(t, q, color=C_BLUE, lw=2.0)
ax.annotate("Q(8h) = %.1f L/s" % q[-1], (t[-1], q[-1]), xytext=(-8, 6),
            textcoords="offset points", ha="right", color=C_BLUE, fontsize=10)
ax.set_xlim(0, 8)
ax.set_ylim(bottom=0)
ax.set_xlabel("時間 (h)")
ax.set_ylabel("出口流量 (L/s)")
ax.set_title("(c) 出口直下流の測線流量(坑道の満管化後に湧出が立ち上がる)",
             fontsize=11, loc="left")
ax.grid(color="#eceae6", lw=0.6)
ax.set_axisbelow(True)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)

fig.suptitle("カナート理想化ケース(管路連続体層 f_gwconduit + 層2帯水層)",
             fontsize=13, y=0.995)
fig.savefig("qanat_result.png", dpi=140, bbox_inches="tight")
print("saved qanat_result.png")
