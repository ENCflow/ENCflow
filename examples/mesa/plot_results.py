#!/usr/bin/env python3
"""examples/mesa の図化と数表(事前に param_cap.txt / param_nocap.txt を実行しておく)。
  python3 plot_results.py          # キャップあり / 層理なし
  python3 plot_results.py bench    # 中間硬層の対照(cap / bench / bench2): figs/*_bench.png
  figs/maps.png      ケース × 4 時刻の陰影図
  figs/sections.png  2 つの台地の中心を通る横断(y = 50 m)の時間発展
  figs/series.png    台地面(z >= 17 m)の等価半径 sqrt(A/π) と頂高の時系列(崖の後退速度)
"""
import csv, os, re, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource
matplotlib.rcParams["font.family"] = ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs("figs", exist_ok=True)
MODE = sys.argv[1] if len(sys.argv) > 1 else "cap"
if MODE == "bench":
    CASES = [("param_cap.txt", "中間硬層 z = 8〜10 m・倍率 0.3(param_cap)"),
             ("param_bench.txt", "中間硬層 z = 6〜10 m・倍率 0.05"),
             ("param_bench2.txt", "中間硬層 z = 5〜10 m・倍率 0.02"),
             ("param_bench3.txt", "中間硬層 z = 5〜10 m・倍率 0.02、凹地形増幅なし (spl_cb = 0)")]
    SUF = "_bench"
else:
    CASES = [("param_cap.txt", "キャップロックあり(上 3 m 倍率 0.05、z = 8〜10 m 倍率 0.3)"),
             ("param_nocap.txt", "層理なし(対照)")]
    SUF = ""
HARD = {"cap": [(17, 20), (8, 10)], "bench": [(17, 20), (6, 10)], "bench2": [(17, 20), (5, 10)], "bench3": [(17, 20), (5, 10)]}
PLATEAUS = [(60.0, 50.0, 30.0), (150.0, 50.0, 12.0)]
ZCAP, DX, YC = 17.0, 1.0, 50.0


def read_param(fn):
    p = {}
    for line in open(fn, encoding="utf-8"):
        m = re.match(r"\s*(\w+)\s*=\s*([^,\s]+)", line.split("!")[0])
        if m:
            p[m.group(1)] = m.group(2).strip("'")
    return p


def load(fn):
    p = read_param(fn)
    res = p["dir_result"]
    t = {}
    for row in csv.reader(open(os.path.join(res, "FILENUMBER.csv"))):
        if not row[0].startswith("#"):
            t[int(row[0])] = float(row[2]) * float(p["morfac"])
    snaps = [(t[n], np.loadtxt(os.path.join(res, "Z%04d.txt" % n))) for n in sorted(t) if n < 9998]
    zf = np.loadtxt(os.path.join(res, "Z9998.txt"))
    tend = float(p["tt"]) * float(p["morfac"])
    if snaps[-1][0] < tend:
        snaps.append((tend, zf))
    logfn = "Screen_" + fn[6:-4] + ".log"
    log = open(logfn, errors="ignore").read() if os.path.exists(logfn) else ""
    m = re.search(r"exported sediment volume =\s*([0-9.Ee+-]+)", log)
    rows = [l.split() for l in log.splitlines() if re.match(r"\s*\d+:\d\d:\d\d", l)]
    return dict(name=fn[6:-4], snaps=snaps, export=float(m.group(1)) if m else np.nan,
                ssurf=max((float(r[2]) for r in rows), default=np.nan), sgrnd=float(rows[-1][3]) if rows else np.nan, tt=float(p["tt"]))


cases = [load(f) for f, _ in CASES]
labels = {f[6:-4]: l for f, l in CASES}
ny, nx = cases[0]["snaps"][0][1].shape
x = (np.arange(nx) + 0.5) * DX
y = (np.arange(ny) + 0.5) * DX
X, Y = np.meshgrid(x, y)
ext = [0, nx * DX, 0, ny * DX]

print("=== 検算 ===")
print("ケース | S_surf 最大 | S_grnd 最終 | 降雨累計 | Σ(z0−zf)Δx² (m³) | 排出(固体) | 比")
for c in cases:
    z0, zf = c["snaps"][0][1], c["snaps"][-1][1]
    vol = (z0 - zf).sum() * DX * DX
    print("%s | %.4f | %.4f | %.4f | %.0f | %.0f | %.4f" % (c["name"], c["ssurf"], c["sgrnd"], 10 / 3.6e6 * c["tt"], vol, c["export"], vol / c["export"]))


def plateau_stats(z, xc, yc, R):
    win = np.hypot(X - xc, Y - yc) <= R + 15
    top = win & (z >= ZCAP)
    A = top.sum() * DX * DX
    return np.sqrt(A / np.pi), z[win].max(), A


# --- 時系列
fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
print("\n=== 台地面(z >= 17 m)の等価半径 (m) / 頂高 (m) ===")
for c in cases:
    for k, (xc, yc, R) in enumerate(PLATEAUS):
        ts, rs, zs = [], [], []
        for t, z in c["snaps"]:
            r_eq, zmax, A = plateau_stats(z, xc, yc, R)
            ts.append(t); rs.append(r_eq); zs.append(zmax)
        ls = "-" if k == 0 else "--"
        col = {"cap": "C0", "nocap": "C3", "bench": "C2", "bench2": "C1", "bench3": "C4"}[c["name"]]
        axes[0].plot(ts, rs, ls, color=col, label="%s, R₀ = %g m" % (c["name"], R))
        axes[1].plot(ts, zs, ls, color=col, label="%s, R₀ = %g m" % (c["name"], R))
        sel = [i for i in range(len(ts)) if rs[i] > 2]
        rate = np.nan
        if len(sel) >= 3:
            rate = -np.polyfit(np.array(ts)[sel], np.array(rs)[sel], 1)[0]
        print("%s R0=%g: r_eq %s / zmax %s / 後退速度 %.2e m/s(地形時間)" % (
            c["name"], R, " ".join("%.1f" % v for v in rs[:7]), " ".join("%.1f" % v for v in zs[:7]), rate))
axes[0].set_xlabel("地形時間 T_geo (s)"); axes[0].set_ylabel("台地面(z ≥ 17 m)の等価半径 (m)")
axes[0].set_title("キャップの縁の後退(直線 = 平行後退)"); axes[0].grid(alpha=0.3); axes[0].legend(fontsize=8)
axes[1].set_xlabel("地形時間 T_geo (s)"); axes[1].set_ylabel("頂高 (m)")
axes[1].set_title("頂の高さ"); axes[1].grid(alpha=0.3); axes[1].legend(fontsize=8)
fig.tight_layout(); fig.savefig("figs/series%s.png" % SUF, dpi=110); plt.close(fig)

# --- 地図
isel = [0, 1, 2, 3]
fig, axes = plt.subplots(len(cases), len(isel), figsize=(4.2 * len(isel), 2.4 * len(cases)))
ls = LightSource(azdeg=315, altdeg=40)
for r, c in enumerate(cases):
    for k, i in enumerate(isel):
        t, z = c["snaps"][min(i, len(c["snaps"]) - 1)]
        ax = axes[r, k]
        ax.imshow(ls.hillshade(z, vert_exag=1, dx=DX, dy=DX), cmap="gray", extent=ext, origin="lower", vmin=0, vmax=1)
        ax.contour(x, y, z, levels=np.arange(2, 21, 2), colors="orange", linewidths=0.4)
        ax.contour(x, y, z, levels=[ZCAP], colors="red", linewidths=0.8)
        ax.set_title("%s  T_geo = %.1e s" % (c["name"], t), fontsize=9)
fig.suptitle("赤線 = キャップ上面(z = 17 m)の輪郭", fontsize=10)
fig.tight_layout(); fig.savefig("figs/maps%s.png" % SUF, dpi=110); plt.close(fig)

# --- 横断
fig, axes = plt.subplots(len(cases), 1, figsize=(13, 3 * len(cases)), sharex=True)
jc = int(YC / DX)
for ax, c in zip(axes, cases):
    for z1, z2 in HARD.get(c["name"], []):
        ax.axhspan(z1, z2, color="0.85", lw=0, zorder=0)
    ax.plot(x, c["snaps"][0][1][jc], "k--", lw=0.8, label="初期")
    n = len(c["snaps"]); cmap = plt.get_cmap("viridis")
    for i in range(1, n):
        t, z = c["snaps"][i]
        ax.plot(x, z[jc], color=cmap(i / (n - 1)), lw=0.9, label=("T_geo = %.1e s" % t) if i in (1, n // 2, n - 1) else None)
    ax.set_ylabel("z (m)"); ax.set_ylim(-0.5, 22); ax.grid(alpha=0.3); ax.legend(fontsize=8, loc="upper right")
    ax.set_title(labels[c["name"]], fontsize=10, loc="left")
axes[-1].set_xlabel("x (m)(y = 50 m。灰色 = キャップ(上)と中間硬層(下))")
fig.tight_layout(); fig.savefig("figs/sections%s.png" % SUF, dpi=110); plt.close(fig)

# ベンチの指標: 大きい台地の方位平均断面で、z = 10〜17 m の軟層区間と中間硬層の上面(z ≈ 10 m)の
# 幅 — 硬層上面 ±0.5 m にあるセルの数(台地中心から半径 45 m 以内)を時刻ごとに数える
if MODE == "bench":
    print("\n=== ベンチの指標: 大きい台地(中心 x = 60 m)で中間硬層の上面 ±0.5 m にあるセル数(= 段の面積 m²)===")
    for c in cases:
        ztop = 10.0
        win = np.hypot(X - 60.0, Y - 50.0) <= 45.0
        ns = [int((win & (np.abs(z - ztop) <= 0.5)).sum()) for t, z in c["snaps"]]
        print("%s: %s" % (c["name"], " ".join(str(n) for n in ns)))
    print("\n=== 方位平均断面(大きい台地)で各標高帯が占める半径方向の幅 (m): 17-20 / 10.5-17 / 9.5-10.5(段) / 5-9.5 / 1-5 ===")
    rr = np.hypot(X - 60.0, Y - 50.0)
    for c in cases:
        for i in (2, 6, 9):
            t, z = c["snaps"][i]
            prof = np.array([z[(rr >= a) & (rr < a + 1)].mean() for a in np.arange(0, 46, 1.0)])
            w = lambda z1, z2: int(((prof >= z1) & (prof < z2)).sum())
            print("%s T_geo=%.1e: %d / %d / %d / %d / %d" % (c["name"], t, w(17, 20.5), w(10.5, 17), w(9.5, 10.5), w(5, 9.5), w(1, 5)))
print("\nfigs/maps%s.png, sections%s.png, series%s.png written" % (SUF, SUF, SUF))
