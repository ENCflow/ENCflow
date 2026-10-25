# -*- coding: utf-8 -*-
# sewer_hybrid の比較図(ラン A〜E)。
#   python3 plot_sewer.py        → sewer_hybrid_result.png, sewer_hybrid_outfall.png
#   python3 plot_sewer.py en     → 英語ラベル版を en/figs/ に描く(en/figs/sewer_hybrid_result.png 等)
# sewer_hybrid_result.png
#   (a) 地表の氾濫水量 S_surf の時系列 A/B/C/D
#   (b) 降雨終了時 t=1h の地表水深マップ A/B/C/D
#   (c) t=1h の管内充満率 hgc/cap の縦断(幹線 j=11 と枝管 j=5)A/B/D
# sewer_hybrid_outfall.png(川と開放吐口のラン E・F と D の比較)
#   (a) 管内貯留 S_grnd の時系列 D/E/F  (b) 地表貯留 S_surf D/E/F
#   (c) 幹線 j=11 の充満率の縦断 t=1h / 3h D/E/F
import os, re, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "."
plt.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAPGothic", "IPAGothic", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
here = os.path.dirname(os.path.abspath(__file__))
os.chdir(here)
os.makedirs(FIGDIR, exist_ok=True)


def out(name):                       # 既定はケース直下(従来どおり)。EN では en/figs/
    return os.path.join(FIGDIR, name) if EN else name

C_BLUE, C_ORANGE, C_AQUA, C_RED, C_PURPLE = "#2a78d6", "#eb6834", "#1baf7a", "#c8102e", "#7b4fb3"
C_MUTED = "#8a8983"
RUNS = [("A", C_BLUE, T("A: 幹線あり・一様 sy = 枝管に合わせた 0.031", "A: trunk; uniform sy = 0.031 (matched to branch pipes)")),
        ("B", C_ORANGE, T("B: 幹線あり・一様 sy = 幹線に合わせた 0.091", "B: trunk; uniform sy = 0.091 (matched to trunk)")),
        ("C", C_AQUA, T("C: 幹線なし(全セル枝管)", "C: no trunk (all cells branch pipes)")),
        ("D", C_RED, T("D: 幹線あり・セル別 sy / slot_sy(整合)", "D: trunk; per-cell sy / slot_sy (consistent)"))]

def read(fn):
    return np.loadtxt(fn)

def read_log(fn):
    """Log.txt → t(h), S_surf(mm), S_grnd(mm)"""
    t, ss, sg = [], [], []
    pat = re.compile(r"^\s*(\d+):(\d\d):(\d\d)\.\d\d\s+\S+%\s+(\S+)\s+(\S+)\s")
    for line in open(fn):
        m = pat.match(line)
        if m:
            t.append(int(m.group(1)) + int(m.group(2)) / 60.0 + int(m.group(3)) / 3600.0)
            ss.append(float(m.group(4)) * 1000.0); sg.append(float(m.group(5)) * 1000.0)
    return np.array(t), np.array(ss), np.array(sg)

def probe(run, n, col):
    d = np.loadtxt(f"result_{run}/probes/probe{n:04d}.csv", delimiter=",", comments="#")
    return d[:, 0], d[:, col]

def style(ax):
    ax.grid(color="#eceae6", lw=0.6); ax.set_axisbelow(True)
    for sp in ("top", "right"): ax.spines[sp].set_visible(False)

# ================= 図 1: A/B/C/D =================
fig = plt.figure(figsize=(11.5, 10), facecolor="white")
gs = fig.add_gridspec(3, 4, height_ratios=[1.0, 0.85, 0.9], hspace=0.5, wspace=0.22)

ax = fig.add_subplot(gs[0, :])
final = {}
for run, c, label in RUNS:
    t, ss, sg = read_log(f"result_{run}/Log.txt")
    ax.plot(t, ss, color=c, lw=2.0, label=label); final[run] = (ss[-1], sg[-1])
    ax.annotate("%.1f mm" % ss[-1], (t[-1], ss[-1]), xytext=(4, 0), textcoords="offset points", color=c, fontsize=10, va="center")
ax.axvspan(0, 61.0 / 60.0, color="#eceae6", zorder=0)
ax.annotate(T("降雨 60 mm/h", "rain 60 mm/h"), (0.5, 40), color=C_MUTED, fontsize=10, ha="center")
ax.set_xlim(0, 3.4); ax.set_ylim(0, 44)
ax.set_xlabel(T("時間 (h)", "time (h)")); ax.set_ylabel(T("地表の氾濫水量 S_surf (mm)", "surface flood water S_surf (mm)"))
ax.set_title(T("(a) 地表にあふれた水の量: 幹線の効果(C → A, B)と貯留係数の与え方(A, B ↔ D)",
               "(a) Water overflowing onto the surface: effect of the trunk (C → A, B) and of how the storage coefficient is given (A, B ↔ D)"), fontsize=11, loc="left")
ax.legend(loc="upper left", bbox_to_anchor=(0.30, 0.98), frameon=False, fontsize=9.5); style(ax)

cmap = LinearSegmentedColormap.from_list("blues1", ["#ffffff", "#bcd6f2", C_BLUE, "#123b6b"])
vmax = max(float(read(f"result_{r}/H0002.txt").max()) for r, _, _ in RUNS)
ims = []
for col, (run, c, label) in enumerate(RUNS):
    ax = fig.add_subplot(gs[1, col])
    h = np.ma.masked_less(read(f"result_{run}/H0002.txt"), 1.0e-3)
    im = ax.imshow(h, cmap=cmap, vmin=0, vmax=vmax, extent=[0, 400, 210, 0], interpolation="nearest"); ims.append(im)
    if run != "C":
        ax.plot([15, 375], [105, 105], color=C_ORANGE, lw=1.6, ls="--")
    ax.set_title(T("ラン ", "Run ") + run, fontsize=10, loc="left"); ax.set_xlabel("x (m)", fontsize=9)
    if col == 0: ax.set_ylabel("y (m)", fontsize=9)
    else: ax.set_yticklabels([])
    ax.tick_params(labelsize=8)
cb = fig.colorbar(ims[-1], ax=fig.axes[1:5], shrink=0.85, pad=0.02); cb.set_label(T("地表水深 (m) at t = 1 h", "surface depth (m) at t = 1 h"), fontsize=9)
fig.axes[1].text(-0.12, 1.28, T("(b) 降雨終了時(t = 1 h)の氾濫分布(破線 = 幹線の位置。水は東へ流れ東端に溜まる)",
                                 "(b) Flood distribution at the end of the rain (t = 1 h) (dashed = trunk; water flows east and ponds at the eastern end)"), transform=fig.axes[1].transAxes, fontsize=11)

axl = fig.add_subplot(gs[2, :])
capT = read("data_sewer/cap_T.txt"); xg = (np.arange(1, 41) - 0.5) * 10.0
for run, c, _ in [RUNS[0], RUNS[1], RUNS[3]]:
    hgc = read(f"result_{run}/Hgc0002.txt")
    axl.plot(xg[1:38], (hgc[10] / capT[10])[1:38], color=c, lw=2.0, label=T(f"ラン {run}: 幹線(j = 11)", f"Run {run}: trunk (j = 11)"))
    axl.plot(xg[1:38], (hgc[4] / capT[4])[1:38], color=c, lw=1.4, ls=":", label=T(f"ラン {run}: 枝管(j = 5)", f"Run {run}: branch (j = 5)"))
axl.axhline(1.0, color=C_MUTED, lw=1.0, ls="--")
axl.annotate(T("満管(= 1)。これより上は疑似スロットに入った「被圧の貯留」", "pipe-full (= 1); above this is pressurized storage in the pseudo slot"), (8, 0.35), color=C_MUTED, fontsize=9)
axl.set_xlim(0, 400); axl.set_ylim(0, 5.9); axl.set_xlabel("x (m)"); axl.set_ylabel(T("充満率 hgc / cap", "filling ratio hgc / cap"))
axl.set_title(T("(c) t = 1 h の管内充満率: 緩い slot_sy(A, B)は満管の 3〜5 倍の幻の貯留を作り、硬い slot_sy(D)は満管付近に収まる",
                "(c) Pipe filling ratio at t = 1 h: soft slot_sy (A, B) creates phantom storage of 3–5 times pipe-full; stiff slot_sy (D) stays near pipe-full"), fontsize=11, loc="left")
axl.legend(loc="center right", frameon=False, fontsize=9, ncol=2); style(axl)
fig.suptitle(T("幹線 1 本(線)+ 枝管網(面)を 1 つの管路連続体層で表す模式実験",
               "Idealized experiment: one trunk main (line) + a branch network (area) in a single conduit continuum layer"), fontsize=13, y=0.995)
fig.savefig(out("sewer_hybrid_result.png"), dpi=140, bbox_inches="tight")
print("saved " + out("sewer_hybrid_result.png"))

# ================= 図 2: D vs E(開放吐口) =================
fig, axs = plt.subplots(1, 3, figsize=(14, 4.3), facecolor="white")
for run, c, label in [("D", C_RED, T("D: 閉領域(川なし・吐口なし)", "D: closed domain (no river, no outfall)")),
                      ("E", C_AQUA, T("E: 東端に川(受け皿)。吐口なし", "E: river at the eastern end (receiver); no outfall")),
                      ("F", C_PURPLE, T("F: 川 + 幹線末端の開放吐口", "F: river + open outfall at the trunk end"))]:
    t, ss, sg = read_log(f"result_{run}/Log.txt"); final[run] = (ss[-1] - ss[0], sg[-1])
    # Log の S_surf は陸地セルだけの平均(2026-10-22 以降。海域マスクの川セルを含まない)。
    # 以前は川セルの水柱を含んでいたため t = 0 の値を引いていた。現在 ss[0] = 0 で差し引きは恒等
    axs[0].plot(t, sg, color=c, lw=2, label=label)
    axs[1].plot(t, ss - ss[0], color=c, lw=2, label=label)
    for k, ls, tl in [(2, "-", "t = 1 h"), (6, ":", "t = 3 h")]:
        hgc = read(f"result_{run}/Hgc{k:04d}.txt")
        axs[2].plot(xg[1:38], (hgc[10] / capT[10])[1:38], color=c, lw=2, ls=ls, label=f"{run}, {tl}")
axs[2].axhline(1.0, color=C_MUTED, lw=1, ls="--"); axs[2].annotate(T("満管(= 1)", "pipe-full (= 1)"), (20, 1.05), color=C_MUTED, fontsize=9)
axs[2].set_xlim(0, 400); axs[2].legend(frameon=False, fontsize=8, ncol=3)
for ax in axs[:2]:
    ax.axvspan(0, 61.0 / 60.0, color="#eceae6", zorder=0); ax.set_xlim(0, 3); ax.set_xlabel(T("時間 (h)", "time (h)"))
for ax in axs: style(ax)
axs[0].set_ylabel(T("管内の貯留 S_grnd (mm)", "in-pipe storage S_grnd (mm)")); axs[0].set_title(T("(a) 管の中にある水", "(a) Water inside the pipes"), fontsize=11, loc="left")
axs[1].set_ylabel(T("陸地の地表水 S_surf − S_surf(0) (mm)", "land surface water S_surf − S_surf(0) (mm)")); axs[1].set_title(T("(b) 陸地の地表にある水(川の水柱を除く)", "(b) Water on the land surface (excluding the river water column)"), fontsize=11, loc="left")
axs[2].set_ylabel(T("幹線の充満率 hgc / cap", "trunk filling ratio hgc / cap")); axs[2].set_xlabel("x (m)"); axs[2].set_title(T("(c) 幹線(j = 11)の充満率の縦断(吐口は x = 375 m)", "(c) Longitudinal profile of the trunk (j = 11) filling ratio (outfall at x = 375 m)"), fontsize=11, loc="left")
axs[0].legend(frameon=False, fontsize=9)
fig.suptitle(T("受け皿の川と開放吐口の効果(ラン D・E・F。いずれもセル別 sy / slot_sy)", "Effect of the receiving river and the open outfall (runs D, E, F; all with per-cell sy / slot_sy)"), fontsize=13)
fig.tight_layout()
fig.savefig(out("sewer_hybrid_outfall.png"), dpi=140, bbox_inches="tight")
print("saved " + out("sewer_hybrid_outfall.png"))
for r in "ABCDEF":
    if r in final: print("run %s: final land S_surf %.2f mm, S_grnd %.2f mm" % (r, *final[r]))
