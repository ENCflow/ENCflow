#!/usr/bin/env python3
"""examples/badland_storm の図化と数表(param_storm.txt・param_dry.txt を実行後)。
  python3 plot_storm.py
図(figs/): maps.png(両ケースの地形の時間発展と差)、series.png(時系列)、
          flow.png(豪雨時の最大水深 Hmax と最終地形の D8 網)
依存: numpy, matplotlib。解析関数は examples/badland/plot_results.py を流用する。
"""
import os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
matplotlib.rcParams["font.family"] = ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
sys.argv = ["x"]
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "..", "badland", "plot_results.py"), encoding="utf-8").read()
exec(src.split("# ---------------------------------------------------------------- 主ケース")[0])
os.chdir(HERE)
os.makedirs("figs", exist_ok=True)

MORFAC = 50.0
HP = 30.0
cases = {}
SUF = os.environ.get("SUF", "")
CTRL = {"_wet": "result_dry_tilt"}   # 強い湿潤侵食の対照は傾き版の全量浸透
for name, res in [("storm", "result_storm" + SUF), ("dry", CTRL.get(SUF, "result_dry" + SUF))]:
    if not os.path.exists(os.path.join(res, "Z0000.txt")):
        continue
    t = file_times(res)
    z0 = np.loadtxt(os.path.join(res, "Z0000.txt"))
    snaps = []
    for n in sorted(t):
        if n >= 9998:
            continue
        f = os.path.join(res, "Z%04d.txt" % n)
        if os.path.exists(f):
            snaps.append((t[n] * MORFAC, n, np.loadtxt(f)))
    hmax = np.loadtxt(os.path.join(res, "H9998.txt")) if os.path.exists(os.path.join(res, "H9998.txt")) else None   # 最終 = 豪雨の終了時刻の水深
    cases[name] = dict(res=res, z0=z0, snaps=snaps, hmax=hmax)

if not cases:
    sys.exit("no results")
ny, nx = cases[next(iter(cases))]["z0"].shape
dx = 1.0
ext = [0, nx * dx, 0, ny * dx]
sw = (cases[next(iter(cases))]["z0"] <= 0).astype(int)

# ---- 時系列 ----
rows = {}
for name, c in cases.items():
    rr = []
    for tg, n, z in c["snaps"]:
        m = metrics(z, c["z0"], dx, HP)
        if m:
            m["t"] = tg; rr.append(m)
    rows[name] = rr
fig, ax = plt.subplots(1, 4, figsize=(16, 3.6))
for name, rr in rows.items():
    T = [r["t"] for r in rr]
    ax[0].plot(T, [r["relief"] for r in rr], "o-", ms=3, label=name)
    ax[1].plot(T, [r["spacing"] for r in rr], "o-", ms=3, label=name + " 谷間隔")
    ax[1].plot(T, [r["lam"] for r in rr], "s--", ms=3, label=name + " Δz 重心波長")
    ax[2].plot(T, [r["mean_inc"] for r in rr], "o-", ms=3, label=name + " 崖面帯の平均低下")
    ax[2].plot(T, [r["max_inc"] for r in rr], "s--", ms=3, label=name + " 最大下刻")
    ax[3].plot(T, [r["xhead"] for r in rr], "o-", ms=3, label=name)
ax[0].set_ylabel("崖面帯の y 方向起伏 (m)"); ax[1].set_ylabel("(m)"); ax[2].set_ylabel("(m)"); ax[3].set_ylabel("谷頭の位置 x (m)(台地縁 60 m)")
for a in ax:
    a.set_xlabel("T_geo (s)"); a.legend(fontsize=7)
fig.tight_layout(); fig.savefig("figs/series%s.png" % SUF, dpi=110); plt.close(fig)

# ---- 地図 ----
names = [n for n in ("dry", "storm") if n in cases]
picks_t = [1.8e6, 4.5e6, 9.0e6]
fig, axes = plt.subplots(len(names) + 1, len(picks_t), figsize=(4.6 * len(picks_t), 4.2 * (len(names) + 1)))
axes = np.atleast_2d(axes)
for r, name in enumerate(names):
    c = cases[name]
    for k, tt in enumerate(picks_t):
        tg, n, z = c["snaps"][int(np.argmin([abs(t - tt) for t, _, _ in c["snaps"]]))]
        im = axes[r, k].imshow(z, origin="lower", extent=ext, cmap="terrain", vmin=0, vmax=HP)
        axes[r, k].set_xlim(20, 100); axes[r, k].set_title("%s: T_geo = %.1e s(%d 周期)" % ("全量浸透(対照)" if name == "dry" else "豪雨時に表面流", tg, n), fontsize=9)
    fig.colorbar(im, ax=axes[r, :].tolist(), shrink=0.7, label="z (m)")
if len(names) == 2:
    for k, tt in enumerate(picks_t):
        zs = cases["storm"]["snaps"][int(np.argmin([abs(t - tt) for t, _, _ in cases["storm"]["snaps"]]))][2]
        zd = cases["dry"]["snaps"][int(np.argmin([abs(t - tt) for t, _, _ in cases["dry"]["snaps"]]))][2]
        im = axes[2, k].imshow(zs - zd, origin="lower", extent=ext, cmap="RdBu", vmin=-15, vmax=15)
        axes[2, k].set_xlim(20, 100); axes[2, k].set_title("差 z(表面流) − z(対照)(青: 表面流で余計に削れた)", fontsize=9)
    fig.colorbar(im, ax=axes[2, :].tolist(), shrink=0.7, label="Δz (m)")
fig.savefig("figs/maps%s.png" % SUF, dpi=110, bbox_inches="tight"); plt.close(fig)

# ---- 流れ ----
if "storm" in cases:
    c = cases["storm"]
    zf = c["snaps"][-1][2]
    acc = d8_accumulation(zf, sw)
    fig, ax = plt.subplots(1, 3, figsize=(14, 4.6))
    if c["hmax"] is not None:
        im = ax[0].imshow(np.log10(np.maximum(c["hmax"], 1e-4)), origin="lower", extent=ext, cmap="Blues", vmin=-3, vmax=0)
        ax[0].set_xlim(20, 100); ax[0].set_title("豪雨終了時(最終)の水深 log10 h (m)", fontsize=9); fig.colorbar(im, ax=ax[0], shrink=0.8)
    im = ax[1].imshow(np.log10(np.maximum(acc, 1)), origin="lower", extent=ext, cmap="Blues")
    ax[1].set_xlim(20, 100); ax[1].set_title("最終地形の D8 集水面積 log10(セル数)", fontsize=9); fig.colorbar(im, ax=ax[1], shrink=0.8)
    if "dry" in cases:
        accd = d8_accumulation(cases["dry"]["snaps"][-1][2], sw)
        bins = np.logspace(0, 4, 30)
        ax[2].hist(acc[(sw == 0) & (zf > 0)], bins=bins, histtype="step", label="表面流あり")
        ax[2].hist(accd[(sw == 0) & (cases["dry"]["snaps"][-1][2] > 0)], bins=bins, histtype="step", label="対照")
        ax[2].set_xscale("log"); ax[2].set_yscale("log"); ax[2].set_xlabel("D8 集水面積(セル数)"); ax[2].legend(fontsize=8); ax[2].set_title("集水面積の分布(最終)", fontsize=9)
    fig.tight_layout(); fig.savefig("figs/flow%s.png" % SUF, dpi=110); plt.close(fig)

# ---- 数表 ----
print("| 量 | " + " | ".join(("対照(全量浸透)" if n == "dry" else "豪雨時に表面流") for n in names) + " |")
print("|---|" + "---|" * len(names))
def last(name, key):
    return rows[name][-1][key]
def at(name, key, tt):
    rr = rows[name]; r = rr[int(np.argmin([abs(x["t"] - tt) for x in rr]))]; return r[key]
print("| 最終の T_geo (s) | " + " | ".join("%.1e" % last(n, "t") for n in names) + " |")
print("| 崖面帯の起伏 (m): 最大 / 最終 | " + " | ".join("%.2f / %.2f" % (max(r["relief"] for r in rows[n]), last(n, "relief")) for n in names) + " |")
print("| 谷間隔 (m): T_geo 1.8e6 / 4.5e6 / 最終 | " + " | ".join("%s / %s / %s" % (fmt(at(n, "spacing", 1.8e6)), fmt(at(n, "spacing", 4.5e6)), fmt(last(n, "spacing"))) for n in names) + " |")
print("| 谷の本数(最終) | " + " | ".join("%.0f" % last(n, "nvalleys") for n in names) + " |")
print("| 崖面帯の平均低下 (m): 1.8e6 / 4.5e6 / 最終 | " + " | ".join("%.1f / %.1f / %.1f" % (at(n, "mean_inc", 1.8e6), at(n, "mean_inc", 4.5e6), last(n, "mean_inc")) for n in names) + " |")
print("| 最大下刻 (m)(最終) | " + " | ".join("%.1f" % last(n, "max_inc") for n in names) + " |")
print("| 谷頭の位置 x (m): 1.8e6 / 4.5e6 / 最終 | " + " | ".join("%.1f / %.1f / %.1f" % (at(n, "xhead", 1.8e6), at(n, "xhead", 4.5e6), last(n, "xhead")) for n in names) + " |")
for n in names:
    c = cases[n]; zf = c["snaps"][-1][2]; z0 = c["z0"]
    plateau = z0 >= HP - 0.1
    print("| 台地内部(初期 30 m)の平均低下 (m) %s | %.2f |" % (n, (z0 - zf)[plateau].mean()))
    S, K = slope_curv(zf, dx)
    land = (sw == 0) & (zf > 0)
    print("| 勾配の 99 %% 点・> 1 の割合 %s | %.1f・%.2f |" % (n, np.percentile(S[land], 99), (S[land] > 1).mean()))
if "storm" in cases and cases["storm"]["hmax"] is not None:
    hm = cases["storm"]["hmax"]; land = (sw == 0) & (cases["storm"]["z0"] > 0)
    print("| 豪雨終了時の水深 h (m): 中央値 / 99 %% 点 / 最大(陸) | %.3f / %.3f / %.3f |" % (np.median(hm[land]), np.percentile(hm[land], 99), hm[land].max()))
print("figs/ written")
