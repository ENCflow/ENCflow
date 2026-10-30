#!/usr/bin/env python3
"""test/gwbed の図を figs/gwbed.png に描く(事前に ./Run.sh を実行しておく。引数 en で英語版を en/figs/ に)。
河床交換能 f_gwbed: 構成 1(得水が上限 k_bed·l_k·h_e で律速)のプローブ水深と解析勾配、構成 1・2 の S_grnd、
構成 3(鉛直浸透能の置き換え)の S_grnd と解析解 7e-6 t。
"""
import math, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
EN = "en" in sys.argv[1:]
def T(ja, en): return en if EN else ja
FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)


def read_log(path):
    names, rows = None, []
    for line in open(path):
        if line.startswith("time,"):
            names = [s.strip() for s in line.split(",")]; continue
        f = line.split()
        if names is None or len(f) < len(names) or ":" not in f[0]:
            continue
        hh, mm, ss = f[0].split(":")
        rows.append([int(hh) * 3600 + int(mm) * 60 + float(ss)] + [float(v.rstrip("%")) for v in f[1:len(names)]])
    return names, np.array(rows)


def read_probe(path):
    a = np.loadtxt(path, delimiter=",", comments="#")
    return a[:, 1] * 60.0, a[:, 3], a[:, 8]          # t (s), h, hg


# 解析値(param.txt と同じ係数。l_k は側方流の 8 方向幾何。l_ax は塞がれた斜めの配分の
# 振り替え f_gw_opening = 1(既定。§16.6)込みで、領域外へ向かう斜め 1 本ぶん r/2 が足される)
dx = dy = 2.0; A = dx * dy; sd = 1.0; sy = 0.2
r = 2 / (2 + math.sqrt(2)); l_ax = (1 - r / 2) * dy; l_diag = math.sqrt(2 * ((r / 2) * dx) ** 2)
k = 1e-3
rate_bank = -k * sd * (l_ax + l_diag) / A
rate_chan = 2 * k * sd * (l_ax + l_diag) / A
hg_bank = sd * sy - k * sd * (l_ax + l_diag) * 0.25 / A
sg_gain = (12 * hg_bank + 6 * sd * sy) / 18
sg_lined = 12 * sd * sy / 18

fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.3), gridspec_kw={"width_ratios": [1.4, 1, 1]})

ax = axes[0]
tc, hc, gc = read_probe("result/probes/probe0001.csv")
tb, hb, gb = read_probe("result/probes/probe0002.csv")
i0 = np.searchsorted(tc, 300.0)
ax.plot(tc, hc, "C0o", ms=4, label=T("河道セル h(計算)", "channel cell h (computed)"))
ax.plot(tb, hb, "C1s", ms=4, label=T("堤内地セル h(計算)", "floodplain cell h (computed)"))
tt = np.linspace(300, tc[-1], 50)
ax.plot(tt, hc[i0] + rate_chan * (tt - tc[i0]), "k-", lw=1, label=T(f"解析 dh/dt = +2 k_bed sd (l_ax + l_diag)/A = {rate_chan:.3e} m/s", f"analytical dh/dt = +2 k_bed sd (l_ax + l_diag)/A = {rate_chan:.3e} m/s"))
ax.plot(tt, hb[i0] + rate_bank * (tt - tb[i0]), "k--", lw=1, label=T(f"解析 dh/dt = −k_bed sd (l_ax + l_diag)/A = {rate_bank:.3e} m/s", f"analytical dh/dt = −k_bed sd (l_ax + l_diag)/A = {rate_bank:.3e} m/s"))
tl, hl, gl = read_probe("result_lined/probes/probe0001.csv")
ax.plot(tl, hl, "C2-", lw=1.2, label=T("河道セル h、k_bed = 0(遮断。1.2 m 不変)", "channel cell h, k_bed = 0 (cut off; stays 1.2 m)"))
ax.set_xlabel("t (s)"); ax.set_ylabel(T("水深 h (m)", "depth h (m)")); ax.grid(alpha=0.3); ax.legend(fontsize=7, loc="center left")
ax.set_title(T("構成 1: 堤内地(飽和)→ 河道の地下水流入が k_bed で律速", "Config 1: groundwater inflow floodplain (saturated) → channel throttled by k_bed"), fontsize=9)

ax = axes[1]
names, lg = read_log("result/Log.txt"); t = lg[:, 0]
names2, lg2 = read_log("result_lined/Log.txt")
ax.plot(t, lg[:, names.index("S_grnd(m)")], "C0o", ms=4, label=T("S_grnd(k_bed = 1e-3 m/s)", "S_grnd (k_bed = 1e-3 m/s)"))
ax.plot(lg2[:, 0], lg2[:, names2.index("S_grnd(m)")], "C2s", ms=4, label=T("S_grnd(k_bed = 0)", "S_grnd (k_bed = 0)"))
ax.axhline(sg_gain, color="k", lw=1, label=T(f"解析 (12·(0.2 − 1 ステップ損失) + 6·0.2)/18 = {sg_gain:.11f}", f"analytical (12·(0.2 − per-step loss) + 6·0.2)/18 = {sg_gain:.11f}"))
ax.axhline(sg_lined, color="k", ls="--", lw=1, label=T(f"解析 12·0.2/18 = {sg_lined:.6f}", f"analytical 12·0.2/18 = {sg_lined:.6f}"))
ax.set_ylim(0.13, 0.205); ax.set_xlabel("t (s)"); ax.set_ylabel(T("領域平均の地下貯留 S_grnd (m)", "domain-mean groundwater storage S_grnd (m)")); ax.grid(alpha=0.3); ax.legend(fontsize=7, loc="center right")
ax.set_title(T("構成 1・2: 飽和後の S_grnd は一定(堤内地は毎ステップ補充)", "Configs 1 and 2: S_grnd is constant after saturation\n(floodplain refilled every step)"), fontsize=9)

ax = axes[2]
names3, lg3 = read_log("result_vert/Log.txt"); t3 = lg3[:, 0]
ax.plot(t3, lg3[:, names3.index("S_grnd(m)")], "C3o", ms=4, label=T("計算 S_grnd", "computed S_grnd"))
ax.plot(t3, 7e-6 * t3, "k-", lw=1, label=T("解析 (12 K_sv + 6 k_bed) t / 18 = 7e-6 t", "analytical (12 K_sv + 6 k_bed) t / 18 = 7e-6 t"))
ax.set_xlabel("t (s)"); ax.set_ylabel("S_grnd (m)"); ax.grid(alpha=0.3); ax.legend(fontsize=7, loc="upper left")
ax.set_title(T("構成 3: 河道セルの浸透能 K_sv → k_bed の置き換え(平坦・側方なし)", "Config 3: channel-cell infiltration capacity K_sv → k_bed\n(flat, no lateral flow)"), fontsize=9)

fig.suptitle(T("河床交換能(f_gwbed): 2 × 11 セル、3 セル縦列 [堤内地・河道・堤内地] × 3 組、堤防で地表水を隔離、k_bed = 1e-3 m/s",
               "Streambed exchange limit (f_gwbed): 2 × 11 cells, three [floodplain, channel, floodplain] stacks, levee separating the surface water, k_bed = 1e-3 m/s"), fontsize=10)
fig.tight_layout(rect=[0, 0, 1, 0.94])
out = os.path.join(FIGDIR, "gwbed.png"); fig.savefig(out, dpi=110); print("wrote", out)
