# -*- coding: utf-8 -*-
# sewer_hybrid の結果の図(ラン A〜F の計算結果から描く)。
#   python3 plot_sewer.py        → figs/sewer_hybrid_result.png, figs/sewer_hybrid_outfall.png
#   python3 plot_sewer.py en     → 英語ラベル版を en/figs/ に描く
# 吐口の放流量は画面出力の "outfall discharge total" から読むので、ラン F の画面出力を
# Screen_F.log に残しておく(README の実行の手順)。
# figs/sewer_hybrid_result.png(ラン A〜D)
#   (a) 地表の氾濫水量 S_surf の時系列  (b) 3 時間後の雨の行き先(地表・管の体積の分・疑似スロットの分)
#   (c) t = 1 h の管内充満率 hgc/cap の縦断(幹線 j = 11 と枝管 j = 5)
# figs/sewer_hybrid_outfall.png(川と開放吐口のラン E・F と D の比較)
#   (a) 管内貯留 S_grnd の時系列  (b) 陸地の地表水 S_surf の時系列
#   (c) 幹線 j = 11 の充満率の縦断(t = 1 h・3 h)  (d) 3 時間後の雨の行き先(川へ出た分を含む)
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


here = os.path.dirname(os.path.abspath(__file__))
os.chdir(here)
FIGDIR = "en/figs" if EN else "figs"
os.makedirs(FIGDIR, exist_ok=True)
plt.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAPGothic", "IPAGothic", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

C_BLUE, C_ORANGE, C_AQUA, C_RED, C_PURPLE = "#2a78d6", "#eb6834", "#1baf7a", "#c8102e", "#7b4fb3"
C_MUTED = "#8a8983"
C_SURF, C_PIPEV, C_SLOT, C_SLOTE = "#2a78d6", "#9cc3ec", "#f6c9ae", "#eb6834"
RAIN_TOTAL = 61.0                       # mm(60 mm/h を 61 分まで)
NLAND_R = 798                           # 川のある系(E・F)の陸地のセル数
CELL = 100.0                            # セル面積 (m2)
RUNS = [("A", C_BLUE, T("A: 幹線あり・一様 sy = 枝管に合わせた 0.031", "A: trunk; uniform sy = 0.031 (matched to branch pipes)")),
        ("B", C_ORANGE, T("B: 幹線あり・一様 sy = 幹線に合わせた 0.091", "B: trunk; uniform sy = 0.091 (matched to trunk)")),
        ("C", C_AQUA, T("C: 幹線なし(全セル枝管)", "C: no trunk (all cells branch pipes)")),
        ("D", C_RED, T("D: 幹線あり・セル別 sy / slot_sy(整合)", "D: trunk; per-cell sy / slot_sy (consistent)"))]
CAPMAP = {"A": "cap_T.txt", "B": "cap_T.txt", "C": "cap_C.txt", "D": "cap_T.txt", "E": "cap_R.txt", "F": "cap_R.txt"}


def read(fn):
    return np.loadtxt(fn)


def read_log(fn):
    """Log.txt → t(h), S_surf(mm), S_grnd(mm), S_total(mm)"""
    t, ss, sg, st = [], [], [], []
    pat = re.compile(r"^\s*(\d+):(\d\d):(\d\d)\.\d\d\s+\S+%\s+(\S+)\s+(\S+)\s+(\S+)\s")
    for line in open(fn):
        m = pat.match(line)
        if m:
            t.append(int(m.group(1)) + int(m.group(2)) / 60.0 + int(m.group(3)) / 3600.0)
            ss.append(float(m.group(4)) * 1000.0)
            sg.append(float(m.group(5)) * 1000.0)
            st.append(float(m.group(6)) * 1000.0)
    return np.array(t), np.array(ss), np.array(sg), np.array(st)


def outfall_total(run):
    """画面出力の吐口の累積放流体積 (m3)。画面出力がなければ None"""
    fn = f"Screen_{run}.log"
    if not os.path.isfile(fn):
        return None
    for line in open(fn, errors="replace"):
        m = re.search(r"outfall discharge total =\s*(\S+)", line)
        if m:
            return float(m.group(1))
    return None


def budget(run):
    """3 時間後の雨の行き先 (mm。陸地の平均): 地表、管の体積の分、疑似スロットの分、崖から川へ、吐口から川へ"""
    t, ss, sg, st = read_log(f"result_{run}/Log.txt")
    cap = read("data_sewer/" + CAPMAP[run])
    hgc = read(f"result_{run}/Hgc0006.txt")
    land = cap > 0.0 if run in "EF" else np.ones_like(cap, bool)
    real = float(np.minimum(hgc, cap)[land].mean()) * 1000.0
    out = 0.0
    river = RAIN_TOTAL - st[-1]
    if run == "F":
        v = outfall_total(run)
        out = v / (NLAND_R * CELL) * 1000.0 if v is not None else float("nan")
    return dict(surface=ss[-1], real=real, phantom=sg[-1] - real, cliff=river - (0.0 if np.isnan(out) else out),
                outfall=out, river=river)


def style(ax):
    ax.grid(color="#eceae6", lw=0.6)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)


SEGS = [("surface", C_SURF, None, "white", T("地表(あふれた水)", "on the surface (overflow)")),
        ("real", C_PIPEV, None, "#1f1f1f", T("管の中: 管の体積の分", "in the pipes: pipe volume")),
        ("phantom", C_SLOT, "////", "#1f1f1f", T("管の中: 疑似スロットの分(幻の貯留)", "in the pipes: pseudo slot (phantom storage)")),
        ("cliff", C_AQUA, None, "white", T("地表から崖を越えて川へ", "to the river over the bank")),
        ("outfall", C_PURPLE, None, "white", T("吐口から川へ", "to the river through the outfall"))]


def bars(ax, runs, labels, xlabel):
    ys = np.arange(len(runs))[::-1]
    used = set()
    for y, run in zip(ys, runs):
        b = budget(run)
        x = 0.0
        for key, col, hatch, tc, name in SEGS:
            v = b[key]
            if not v or np.isnan(v) or v < 0.05:
                continue
            ax.barh(y, v, left=x, height=0.62, color=col, hatch=hatch, edgecolor=C_SLOTE if hatch else "white",
                    lw=0.8 if hatch else 0.6, label=None if key in used else name)
            used.add(key)
            if v >= 1.0:
                ax.text(x + v / 2, y, "%.1f" % v, ha="center", va="center", fontsize=8.5 if v >= 3.0 else 7.2, color=tc)
            x += v
    ax.axvline(RAIN_TOTAL, color=C_MUTED, lw=1.0, ls="--")
    ax.text(RAIN_TOTAL, ys[0] + 0.48, T("総雨量 61.0 mm", "total rain 61.0 mm"), fontsize=8.5, color=C_MUTED,
            ha="right", va="bottom")
    ax.set_yticks(ys)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlim(0, 66)
    ax.set_ylim(ys[-1] - 0.6, ys[0] + 0.9)
    ax.set_xlabel(xlabel, fontsize=9)
    ax.grid(color="#eceae6", lw=0.6, axis="x")
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)


capT = read("data_sewer/cap_T.txt")
xg = (np.arange(1, 41) - 0.5) * 10.0

# ================= 図 1: A/B/C/D =================
fig = plt.figure(figsize=(11.5, 10.6), facecolor="white")
gs = fig.add_gridspec(3, 1, height_ratios=[1.0, 0.62, 0.9], hspace=0.56, top=0.94)

ax = fig.add_subplot(gs[0])
for run, c, label in RUNS:
    t, ss, sg, st = read_log(f"result_{run}/Log.txt")
    ax.plot(t, ss, color=c, lw=2.0, label=label)
    ax.annotate("%.1f mm" % ss[-1], (t[-1], ss[-1]), xytext=(4, 0), textcoords="offset points", color=c, fontsize=10, va="center")
ax.axvspan(0, 61.0 / 60.0, color="#eceae6", zorder=0)
ax.annotate(T("降雨 60 mm/h", "rain 60 mm/h"), (0.5, 24), color=C_MUTED, fontsize=10, ha="center")
ax.set_xlim(0, 3.4)
ax.set_ylim(0, 58)
ax.set_xlabel(T("時間 (h)", "time (h)"))
ax.set_ylabel(T("地表の氾濫水量 S_surf (mm)", "surface flood water S_surf (mm)"))
ax.set_title(T("(a) 地表にあふれた水の量: 貯留係数の与え方(A, B, C ↔ D)で答えが 1.7〜3.6 倍違う",
               "(a) Water overflowing onto the surface: how the storage coefficient is given (A, B, C ↔ D) changes it 1.7–3.6×"),
             fontsize=11, loc="left")
ax.legend(loc="upper left", bbox_to_anchor=(0.30, 1.0), frameon=False, fontsize=9.5, ncol=2, columnspacing=1.6)
style(ax)

axb = fig.add_subplot(gs[1])
bars(axb, ["A", "B", "C", "D"], [T("A: 一様 sy 0.031", "A: uniform sy 0.031"), T("B: 一様 sy 0.091", "B: uniform sy 0.091"),
                                 T("C: 幹線なし", "C: no trunk"), T("D: セル別 sy・slot", "D: per-cell sy, slot")],
     T("領域の平均の水量 (mm)", "water over the domain (mm)"))
axb.legend(loc="upper left", bbox_to_anchor=(0.0, -0.32), ncol=3, frameon=False, fontsize=8.5)
axb.set_title(T("(b) 3 時間後の雨の行き先: A・B・C は 27〜35 mm を実在しないスロットに隠し、その分だけ地表の水が少ない",
                "(b) Where the rain is after 3 h: A, B and C hide 27–35 mm in the non-existent slot, and that much less is on the surface"),
              fontsize=11, loc="left")

axl = fig.add_subplot(gs[2])
for run, c, _ in [RUNS[0], RUNS[1], RUNS[3]]:
    hgc = read(f"result_{run}/Hgc0002.txt")
    axl.plot(xg[1:38], (hgc[10] / capT[10])[1:38], color=c, lw=2.0, label=T(f"ラン {run}: 幹線(j = 11)", f"Run {run}: trunk (j = 11)"))
    axl.plot(xg[1:38], (hgc[4] / capT[4])[1:38], color=c, lw=1.4, ls=":", label=T(f"ラン {run}: 枝管(j = 5)", f"Run {run}: branch (j = 5)"))
axl.axhline(1.0, color=C_MUTED, lw=1.0, ls="--")
axl.annotate(T("満管(= 1)。これより上は疑似スロットに入った「被圧の貯留」", "pipe-full (= 1); above this is pressurized storage in the pseudo slot"),
             (8, 0.35), color=C_MUTED, fontsize=9)
axl.set_xlim(0, 400)
axl.set_ylim(0, 5.9)
axl.set_xlabel("x (m)")
axl.set_ylabel(T("充満率 hgc / cap", "filling ratio hgc / cap"))
axl.set_title(T("(c) t = 1 h の管内充満率: 緩い slot_sy(A, B)では枝管の東端で 5〜5.5 になり(1 を超える分は幻の貯留)、\n硬い slot_sy(D)は 2 未満に収まる",
                "(c) Filling ratio at t = 1 h: with soft slot_sy (A, B) it reaches 5–5.5 at the east end of the branch (the part above 1 is\nphantom storage); with stiff slot_sy (D) it stays below 2"),
              fontsize=11, loc="left")
axl.legend(loc="upper left", frameon=False, fontsize=9, ncol=2)
style(axl)
fig.suptitle(T("幹線 1 本(線)+ 枝管網(面)を 1 つの管路連続体層で表す模式実験(ラン A〜D)",
               "Idealized experiment: one trunk main (line) + a branch network (area) in a single conduit continuum layer (runs A–D)"),
             fontsize=13, y=0.995)
out = os.path.join(FIGDIR, "sewer_hybrid_result.png")
fig.savefig(out, dpi=140, bbox_inches="tight")
plt.close(fig)
print("saved " + out)

# ================= 図 2: D・E・F(川と開放吐口) =================
fig = plt.figure(figsize=(14, 8.4), facecolor="white")
gs = fig.add_gridspec(2, 3, height_ratios=[1.0, 0.46], hspace=0.62, wspace=0.28, top=0.9)
axs = [fig.add_subplot(gs[0, k]) for k in range(3)]
for run, c, label in [("D", C_RED, T("D: 閉領域(川なし・吐口なし)", "D: closed (no river, no outfall)")),
                      ("E", C_AQUA, T("E: 東端に川(受け皿)。吐口なし", "E: river at the east end; no outfall")),
                      ("F", C_PURPLE, T("F: 川 + 幹線末端の開放吐口", "F: river + open outfall"))]:
    t, ss, sg, st = read_log(f"result_{run}/Log.txt")
    axs[0].plot(t, sg, color=c, lw=2, label=label)
    axs[1].plot(t, ss, color=c, lw=2, label=label)
    for k, ls, tl in [(2, "-", "t = 1 h"), (6, ":", "t = 3 h")]:
        hgc = read(f"result_{run}/Hgc{k:04d}.txt")
        axs[2].plot(xg[1:38], (hgc[10] / capT[10])[1:38], color=c, lw=2, ls=ls, label=f"{run}, {tl}")
axs[2].axhline(1.0, color=C_MUTED, lw=1, ls="--")
axs[2].annotate(T("満管(= 1)", "pipe-full (= 1)"), (20, 1.05), color=C_MUTED, fontsize=9)
axs[2].set_xlim(0, 400)
axs[2].legend(frameon=False, fontsize=8, ncol=3, loc="center", bbox_to_anchor=(215, 1.26), bbox_transform=axs[2].transData)
for ax in axs[:2]:
    ax.axvspan(0, 61.0 / 60.0, color="#eceae6", zorder=0)
    ax.set_xlim(0, 3)
    ax.set_xlabel(T("時間 (h)", "time (h)"))
for ax in axs:
    style(ax)
axs[0].set_ylabel(T("管内の貯留 S_grnd (mm)", "in-pipe storage S_grnd (mm)"))
axs[0].set_title(T("(a) 管の中にある水", "(a) Water inside the pipes"), fontsize=11, loc="left")
axs[1].set_ylabel(T("陸地の地表水 S_surf (mm)", "land surface water S_surf (mm)"))
axs[1].set_title(T("(b) 陸地の地表にある水(川の水柱を除く)", "(b) Water on the land surface"), fontsize=11, loc="left")
axs[2].set_ylabel(T("幹線の充満率 hgc / cap", "trunk filling ratio hgc / cap"))
axs[2].set_xlabel("x (m)")
axs[2].set_title(T("(c) 幹線(j = 11)の充満率の縦断(吐口は x = 375 m)", "(c) Trunk filling ratio (j = 11; outfall at x = 375 m)"),
                 fontsize=11, loc="left")
axs[0].legend(frameon=False, fontsize=9, loc="center right", bbox_to_anchor=(1.0, 0.42))
axd = fig.add_subplot(gs[1, :])
bars(axd, ["D", "E", "F"], [T("D: 閉領域", "D: closed"), T("E: 川あり", "E: river"), T("F: 川 + 吐口", "F: river + outfall")],
     T("陸地の平均の水量 (mm)", "water over the land (mm)"))
axd.legend(loc="upper left", bbox_to_anchor=(0.0, -0.42), ncol=5, frameon=False, fontsize=8.5)
axd.set_title(T("(d) 3 時間後の雨の行き先(陸地の平均): 吐口があると雨の 9 割以上が幹線から川へ出る",
                "(d) Where the rain is after 3 h (mean over the land): with the outfall, more than 90 % of the rain leaves through the trunk"),
              fontsize=11, loc="left")
fig.suptitle(T("受け皿の川と開放吐口の効果(ラン D・E・F。いずれもセル別 sy / slot_sy)",
               "Effect of the receiving river and the open outfall (runs D, E, F; all with per-cell sy / slot_sy)"), fontsize=13, y=0.995)
out = os.path.join(FIGDIR, "sewer_hybrid_outfall.png")
fig.savefig(out, dpi=140, bbox_inches="tight")
plt.close(fig)
print("saved " + out)
for r in "ABCDEF":
    b = budget(r)
    print("run %s (mm over the land at 3 h): surface %.2f, pipe volume %.2f, slot %.2f, to river %.2f (outfall %.2f, bank %.2f)"
          % (r, b["surface"], b["real"], b["phantom"], b["river"], b["outfall"], b["cliff"]))
