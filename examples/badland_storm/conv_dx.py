#!/usr/bin/env python3
"""強い湿潤侵食(param_storm_wet*)のガリー間隔の格子収束(Δx = 2 / 1 / 0.5 m)。
  python3 conv_dx.py   → 数表と figs/conv_dx.png
result_storm_wet(Δx = 1 m、25 周期)の 5・10 周期目と、result_storm_wet_dx2 /
_dx05(10 周期。y 方向は半分の 120 m)を比べる。本数は 100 m あたりに換算する。指標は examples/badland/plot_results.py の関数で、
波長・間隔は地形変化 Δz から取る(prominence ≥ 1 m)。
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
exec(open(os.path.join(HERE, "..", "badland", "plot_results.py"), encoding="utf-8").read().split("# ---------------------------------------------------------------- 主ケース")[0])
os.chdir(HERE)
os.makedirs("figs", exist_ok=True)
MORFAC, HP = 50.0, 30.0
cases = [("result_storm_wet_dx2", 2.0), ("result_storm_wet", 1.0), ("result_storm_wet_dx05", 0.5)]
rows = []
fig, ax = plt.subplots(2, 3, figsize=(14, 8))
for k, (res, dx) in enumerate(cases):
    if not os.path.exists(os.path.join(res, "Z0000.txt")):
        print(res, "missing"); continue
    t = file_times(res); z0 = np.loadtxt(os.path.join(res, "Z0000.txt"))
    avail = [nn for nn in t if nn < 9998 and os.path.exists(os.path.join(res, "Z%04d.txt" % nn))]
    if not avail or max(t[nn] for nn in avail) * MORFAC < 1.8e6 - 1:
        print(res, "incomplete"); continue
    for tt, r in ((9.0e5, 0), (1.8e6, 1)):
        n = min(avail, key=lambda nn: abs(t[nn] * MORFAC - tt))
        z = np.loadtxt(os.path.join(res, "Z%04d.txt" % n))
        m = metrics(z, z0, dx, HP)
        S, K = slope_curv(z, dx); land = (z0 > 0) & (z > 0)
        rows.append(dict(res=res, dx=dx, ly=z.shape[0] * dx, tgeo=t[n] * MORFAC, lam=m["lam"], spacing=m["spacing"], nvalleys=m["nvalleys"],
                         relief=m["relief"], mean_inc=m["mean_inc"], max_inc=m["max_inc"], xhead=m["xhead"],
                         s50=float(np.median(S[land])), s99=float(np.percentile(S[land], 99))))
        ny, nx = z.shape
        im = ax[r, k].imshow(z, origin="lower", extent=[0, nx * dx, 0, ny * dx], cmap="terrain", vmin=0, vmax=HP)
        ax[r, k].set_xlim(0, 100); ax[r, k].set_ylim(0, 120)
        ax[r, k].set_title("Δx = %g m, T_geo = %.1e s" % (dx, t[n] * MORFAC), fontsize=9)
fig.colorbar(im, ax=ax.ravel().tolist(), shrink=0.6, label="z (m)")
fig.savefig("figs/conv_dx.png", dpi=110, bbox_inches="tight")
print("| Δx (m) | T_geo (s) | Δz の重心波長 (m) | 谷間隔 (m) / 本数(100 m あたり) | 間隔 / Δx | 崖面帯の起伏 (m) | 平均低下 / 最大下刻 (m) | 谷頭 x (m) | 勾配の中央値 / 99 % 点 |")
print("|---|---|---|---|---|---|---|---|---|")
for r in rows:
    print("| %g | %.1e | %.1f | %s / %.1f | %.1f | %.2f | %.1f / %.1f | %.1f | %.2f / %.1f |" % (
        r["dx"], r["tgeo"], r["lam"], fmt(r["spacing"]), r["nvalleys"] * 100.0 / r["ly"], r["spacing"] / r["dx"], r["relief"], r["mean_inc"], r["max_inc"], r["xhead"], r["s50"], r["s99"]))
print("figs/conv_dx.png written")
