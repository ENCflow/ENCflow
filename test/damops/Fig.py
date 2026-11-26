#!/usr/bin/env python3
"""test/damops の図を figs/damops.png に描く(事前に ./Run.sh を実行しておく)。
7 基のダム・放流工の流入・放流・貯水位の時系列(運転則・時系列との対応)と、閉じた系の体積保存。
引数 en で英語版を en/figs/damops.png に描く。
"""
import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

EN = "en" in sys.argv[1:]
def T(ja, en): return en if EN else ja
FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)
RES = "result"


def read_csv(n):
    t, H, Qin, Qout = [], [], [], []
    for line in open(os.path.join(RES, "dams", f"dam{n:04d}.csv")):
        if line.startswith("#"):
            continue
        v = [float(x) for x in line.split(",")]
        t.append(v[1]); H.append(v[2]); Qin.append(v[4]); Qout.append(v[5])
    return t, H, Qin, Qout


def series(pts, t):
    """interp_series と同じ規約の線形補間(時刻は分)"""
    if t <= pts[0][0]:
        return pts[0][1]
    if t > pts[-1][0]:
        return pts[-1][1]
    for k in range(1, len(pts)):
        if t < pts[k][0]:
            (t0, q0), (t1, q1) = pts[k - 1], pts[k]
            return q0 + (t - t0) / (t1 - t0) * (q1 - q0)
    return pts[-1][1]


def panel(ax, n, title, extra=None, hline=None, qin_from=None):
    t, H, Qin, Qout = read_csv(n)
    if qin_from is not None:
        Qin = read_csv(qin_from)[2]
    ax.plot(t, Qin, color="0.55", lw=1.2, label=T("流入", "inflow"))
    ax.plot(t, Qout, color="tab:blue", lw=1.6, label=T("放流", "release"))
    if extra:
        extra(ax, t)
    ax.set_xlabel(T("時刻 (分)", "time (min)"))
    ax.set_ylabel(T("流量 (m³/s)", "discharge (m³/s)"))
    ax.set_title(title, fontsize=10)
    ax.set_xlim(0, 330)
    ax2 = ax.twinx()
    ax2.plot(t, H, color="tab:red", lw=1.2, label=T("貯水位", "level"))
    if hline is not None:
        ax2.axhline(hline, color="tab:red", lw=0.8, ls=":")
    ax2.set_ylabel(T("貯水位 (m)", "level (m)"), color="tab:red")
    ax2.tick_params(axis="y", colors="tab:red")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=7.5, loc="upper right")
    return ax2


fig, axs = plt.subplots(2, 3, figsize=(15, 8.2))

# (a) ダム 1: 一定量放流方式
panel(axs[0, 0], 1, T("(a) ダム 1: 一定量 0.8 + 制限水位 103 m", "(a) dam 1: constant 0.8 + restricted level 103 m"),
      hline=103.0)

# (b) ダム 2: 一定率一定量のピークまで
def rule2(ax, t):
    _, _, Qin, _ = read_csv(2)
    q = [0.6 if qi <= 0.6 else min(0.6 + 0.5 * (qi - 0.6), 1.0) for qi in Qin]
    ax.plot(t, q, color="k", lw=0.8, ls="--", label=T("式(床より上)", "formula (above floor)"))
panel(axs[0, 1], 2, T("(b) ダム 2: Qon 0.6・r 0.5・Qmax 1.0 + 制限水位 103 m",
                      "(b) dam 2: Qon 0.6, r 0.5, Qmax 1.0 + restricted level 103 m"),
      extra=rule2, hline=103.0)

# (c) ダム 3 と 5: 放流量の時系列(5 はダム 3 の湖から引く取水)
Q3 = [(0, 0.3), (30, 0.3), (30, 0.6), (120, 0.6), (240, 0.1), (400, 0.1)]
Q5 = [(0, 0.1), (200, 0.1), (200, 0.0), (400, 0.0)]
def given35(ax, t):
    ax.plot(t, [series(Q3, x) for x in t], color="k", lw=0.8, ls="--", label=T("与えた放流量 3", "given release 3"))
    t5, _, _, q5 = read_csv(5)
    ax.plot(t5, q5, color="tab:green", lw=1.4, label=T("取水 5(ダム 3 の湖)", "intake 5 (lake of dam 3)"))
    ax.plot(t, [series(Q5, x) for x in t], color="k", lw=0.8, ls=":", label=T("与えた取水量 5", "given intake 5"))
panel(axs[0, 2], 3, T("(c) ダム 3・5: 放流量の時系列(モード 4)", "(c) dams 3 and 5: release time series (mode 4)"),
      extra=given35)

# (d) ダム 4: 貯水位の時系列
H4 = [(0, 104.0), (60, 104.0), (180, 105.5), (240, 105.5), (330, 104.5)]
ax2 = panel(axs[1, 0], 4, T("(d) ダム 4: 貯水位の時系列(モード 5)", "(d) dam 4: water-level time series (mode 5)"))
t4 = read_csv(4)[0]
ax2.plot(t4, [series(H4, x) for x in t4], color="k", lw=0.8, ls="--", label=T("与えた水位", "given level"))
ax2.legend(fontsize=7.5, loc="lower right")

# (e) ダム 6 と 7: 一定率カットと、その湖から引く一定率一定量(自分の制限水位 100.5 m)
def rule7(ax, t):
    t7, _, _, q7 = read_csv(7)
    ax.plot(t7, q7, color="tab:green", lw=1.4, label=T("放流工 7", "release work 7"))
panel(axs[1, 1], 6, T("(e) ダム 6: 一定率 0.6 + 放流工 7(床 100.5 m)", "(e) dam 6: rate 0.6 + release work 7 (floor 100.5 m)"),
      extra=rule7, hline=100.5)

# (f) 閉じた系の体積保存: S × 有効面積 と 初期貯水量 + ソースの累計体積
tri = [(0, 0.2), (60, 1.7), (180, 0.2), (400, 0.2)]
const = [(0, 1.2), (400, 1.2)]
ts, sv = [], []
for line in open(os.path.join(RES, "Log.txt")):
    p = line.split()
    if p and p[0][0].isdigit():
        h, m, s = p[0].split(":")
        ts.append(int(h) * 60 + int(m) + float(s) / 60)
        sv.append(float(p[2]) * 285 * 100.0)
vol, cum, k = 6.0e4, [6.0e4], 0
tt = [0.0]
while k < 19800:
    k += 1
    vol += sum(series(src, k / 60.0) for src in [tri, tri, tri, const, tri])
    if k % 600 == 0:
        tt.append(k / 60.0); cum.append(vol)
ax = axs[1, 2]
ax.plot(tt, [c / 1e4 for c in cum], color="k", lw=1.0, label=T("初期貯水量 + ソースの累計", "initial storage + cumulative sources"))
ax.plot(ts, [v / 1e4 for v in sv], "o", ms=3.5, color="tab:orange", label=T("S × 有効面積(Log)", "S × valid area (Log)"))
err = max(abs(a - b) for a, b in zip(sv, cum)) / (285 * 100.0)
ax.set_title(T(f"(f) 閉じた系の体積(最大差 {err:.1e} m)", f"(f) volume of the closed system (max diff {err:.1e} m)"), fontsize=10)
ax.set_xlabel(T("時刻 (分)", "time (min)"))
ax.set_ylabel(T("体積 (10⁴ m³)", "volume (10⁴ m³)"))
ax.set_xlim(0, 330)
ax.legend(fontsize=7.5, loc="upper left")

fig.tight_layout()
out = os.path.join(FIGDIR, "damops.png")
fig.savefig(out, dpi=110)
print("wrote", out)
