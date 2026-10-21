#!/usr/bin/env python3
"""examples/badland_round の図化と数表(事前に param_d*.txt を実行しておく)。

  python3 plot_results.py

図(figs/):
  maps.png      4 ケース × 3 時刻の陰影図(等高線付き)+ 初期地形
  sections.png  4 つの丘の頂を通る横断(y = 40 m)の時間発展(ケース別)
  radial.png    各丘の方位平均した半径方向断面(評価時刻 T_geo = 1.4e7 s と初期)
  rounding.png  側面の最大勾配・頂の曲率 vs 丘の高さ、頂の低下の時系列
数表(標準出力): 水収支・土砂収支の検算、丘ごとの頂高・キャップ半幅・凸形割合・頂の曲率

依存: numpy, matplotlib
"""
import csv
import os
import re
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource
matplotlib.rcParams["font.family"] = ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs("figs", exist_ok=True)

CASES = [("param_d0.txt", "クリープなし (D = 0)"),
         ("param_d3e-7.txt", "D = 3e-7 m²/s (L ≈ 2 m)"),
         ("param_d1e-6.txt", "D = 1e-6 m²/s (L ≈ 8 m)"),
         ("param_d3e-6.txt", "D = 3e-6 m²/s (L ≈ 24 m)")]
HILLS = [(35.0, 24.0), (90.0, 15.0), (128.0, 9.0), (154.0, 5.0)]   # make_terrain.py と同じ
TANB = 0.8
YC = 40.0
P = 10.0 / 3.6e6          # 降雨 (m/s)
KT, HEXP = 0.05, 1.5


# ---------------------------------------------------------------- 読み込み
def read_param(fn):
    p = {}
    for line in open(fn, encoding="utf-8"):
        line = line.split("!")[0]
        m = re.match(r"\s*(\w+)\s*=\s*([^,\s]+)", line)
        if m:
            p[m.group(1)] = m.group(2).strip("'")
    return p


def file_times(resdir):
    t = {}
    for row in csv.reader(open(os.path.join(resdir, "FILENUMBER.csv"))):
        if row[0].startswith("#"):
            continue
        t[int(row[0])] = float(row[2])
    return t


def load_case(param_fn):
    p = read_param(param_fn)
    res = p["dir_result"]
    if not os.path.exists(os.path.join(res, "Z9998.txt")):
        return None
    dx = float(p["lx"]) / int(p["nx"])
    morfac = float(p["morfac"])
    times = file_times(res)
    snaps = []
    for n in sorted(times):
        if n >= 9998:
            continue
        f = os.path.join(res, "Z%04d.txt" % n)
        if os.path.exists(f):
            snaps.append((times[n] * morfac, np.loadtxt(f)))
    zf = np.loadtxt(os.path.join(res, "Z9998.txt"))
    tend = float(p["tt"]) * morfac
    if not snaps or snaps[-1][0] < tend:
        snaps.append((tend, zf))
    logfn = "Screen_" + param_fn[6:-4] + ".log"      # ./encflow param_dX.txt > Screen_dX.log
    log = open(logfn, errors="ignore").read() if os.path.exists(logfn) else ""
    m = re.search(r"splash exported sediment volume =\s*([0-9.Ee+-]+)", log)
    export = float(m.group(1)) if m else np.nan
    rows = [l.split() for l in log.splitlines() if re.match(r"\s*\d+:\d\d:\d\d", l)]
    ssurf = max(float(r[2]) for r in rows) if rows else np.nan
    sgrnd = float(rows[-1][3]) if rows else np.nan
    D = float(p.get("creep_d", 0)) if p.get("f_creep", "0") == "1" else 0.0
    return dict(name=param_fn[6:-4], p=p, dx=dx, D=D, snaps=snaps, z0=snaps[0][1], zf=zf,
                export=export, ssurf=ssurf, sgrnd=sgrnd, tend=tend)


# ---------------------------------------------------------------- 解析
def radial_profile(z, xc, yc, rmax, dx):
    """頂(窓内の最大)を中心に方位平均した半径方向断面 (r, zbar)"""
    ny, nx = z.shape
    x = (np.arange(nx) + 0.5) * dx
    y = (np.arange(ny) + 0.5) * dx
    X, Y = np.meshgrid(x, y)
    win = np.hypot(X - xc, Y - yc) <= rmax
    zz = np.where(win, z, -np.inf)
    j, i = np.unravel_index(np.argmax(zz), z.shape)
    xs, ys = x[i], y[j]
    r = np.hypot(X - xs, Y - ys)
    rb = np.arange(0, rmax + 0.5 * dx, dx)
    prof = []
    for k in range(len(rb) - 1):
        m = (r >= rb[k]) & (r < rb[k + 1])
        prof.append(z[m].mean() if m.any() else np.nan)
    rc = 0.5 * (rb[:-1] + rb[1:])
    rc[0] = 0.0
    return rc, np.array(prof), (xs, ys, z[j, i])


def crest_metrics(rc, prof, dx):
    """キャップ半幅(勾配が側面最大勾配の半分に達する r)、凸形区間の割合、頂の曲率"""
    valid = np.isfinite(prof) & (prof > 0.2)
    if valid.sum() < 4:
        return np.nan, np.nan, np.nan
    r, zz = rc[valid], prof[valid]
    s = -np.gradient(zz, r)
    smax = s.max()
    if smax <= 0:
        return np.nan, np.nan, np.nan
    half = np.where(s >= 0.5 * smax)[0]
    wcap = r[half[0]] if len(half) else r[-1]
    d2 = np.gradient(s, r)        # dS/dr > 0 = 凸(上に凸)
    convex = (d2 > 0).sum() / len(d2)
    c = np.polyfit(r[:4], zz[:4], 2)[0] * 2.0 if len(r) >= 4 else np.nan   # 頂の 2 次フィット曲率
    return wcap, convex, c


def convexity_index(rc, prof):
    """断面の凸形指数: 裾からの頂高 zs と z = 0.1 zs になる半径 R で正規化した断面 ẑ(r̂) について
    ∫(ẑ − (1 − r̂)) dr̂ / (1/6)。直線の円錐 = 0、放物線のドーム = 1、凹形(ガリーで刻まれた丘)< 0"""
    ok = np.isfinite(prof)
    r, zz = rc[ok], prof[ok]
    zz = zz - zz.min()            # 裾(窓内の最低)を基準にする(クリープの堆積で裾が上がるため)
    zs = zz[0]
    if zs <= 0.3:
        return np.nan
    below = np.where(zz <= 0.1 * zs)[0]
    if len(below) == 0:
        return np.nan
    k = below[0]
    R = np.interp(0.1 * zs, zz[k - 1:k + 1][::-1], r[k - 1:k + 1][::-1]) if k > 0 else r[0]
    if R <= 1.0:
        return np.nan
    rr = np.linspace(0, R, 200)
    zn = np.interp(rr, r, zz) / zs
    return np.trapezoid(zn - (1 - rr / R), rr / R) / (1.0 / 6.0)


def hillshade(z, dx):
    ls = LightSource(azdeg=315, altdeg=40)
    return ls.hillshade(z, vert_exag=1.0, dx=dx, dy=dx)


# ---------------------------------------------------------------- 本体
cases = [c for c in (load_case(f) for f, _ in CASES) if c]
labels = {f[6:-4]: lab for f, lab in CASES}
if not cases:
    raise SystemExit("結果がありません")
dx = cases[0]["dx"]
z0 = cases[0]["z0"]
ny, nx = z0.shape
ext = [0, nx * dx, 0, ny * dx]

print("=== 検算 ===")
print("ケース | S_surf 最大 (m) | S_grnd 最終 (m) | 降雨累計 (m) | Σ(z0−zf)Δx² (m³) | splash 排出 (m³) | 差 (%)")
for c in cases:
    rain = P * float(c["p"]["tt"])
    vol = (c["z0"] - c["zf"]).sum() * dx * dx
    print("%s | %.4f | %.4f | %.4f | %.1f | %.1f | %.3f" %
          (c["name"], c["ssurf"], c["sgrnd"], rain, vol, c["export"], 100 * (vol - c["export"]) / c["export"]))

# --- 丘ごとの指標(ISEL 番目のスナップ = 指標の評価時刻、および最終)
ISEL = 4


def hill_metrics(c, isnap):
    out = []
    z = c["snaps"][isnap][1]
    for xc, H in HILLS:
        R = H / TANB
        rc, prof, (xs, ys, zs) = radial_profile(z, xc, YC, R + 12, dx)
        wcap, convex, curv = crest_metrics(rc, prof, dx)
        valid = np.isfinite(prof) & (prof > 0.2)
        smax = (-np.gradient(prof[valid], rc[valid])).max() if valid.sum() > 3 else np.nan
        out.append(dict(H=H, zs=zs, wcap=wcap, convex=convex, curv=curv, smax=smax, rc=rc, prof=prof,
                        cidx=convexity_index(rc, prof)))
    return out


metrics, metrics_f = {}, {}
for isnap, store, tag in ((ISEL, metrics, "評価時刻"), (len(cases[0]["snaps"]) - 1, metrics_f, "最終")):
    print("\n=== 丘ごとの指標(%s T_geo = %.2e s)===" % (tag, cases[0]["snaps"][isnap][0]))
    print("ケース | 丘 H0 (m) | 頂高 (m) | 側面最大勾配 | 凸形指数(0 = 円錐, 1 = ドーム) | 頂の曲率 (1/m) | キャップ半幅 (m)")
    for c in cases:
        store[c["name"]] = hill_metrics(c, isnap)
        for m in store[c["name"]]:
            print("%s | %g | %.2f | %.2f | %.2f | %.3f | %.1f" % (c["name"], m["H"], m["zs"], m["smax"],
                                                                 m["cidx"], m["curv"], m["wcap"]))
TSEL = cases[0]["snaps"][ISEL][0]

# 理論の長さ尺度 L = D / (P kt S^(h-1))
print("\n長さ尺度 L = D/(P kt S_f^(h−1)) (m), S_f = %.1f:" % TANB,
      ", ".join("%s: %.1f" % (c["name"], c["D"] / (P * KT * TANB ** (HEXP - 1))) for c in cases))

# ---------------------------------------------------------------- 図 1: 地図
isel = [2, ISEL, 7]
fig, axes = plt.subplots(len(cases) + 1, 3, figsize=(15, 3.1 * (len(cases) + 1)))
for ax in axes[0]:
    ax.axis("off")
ax = axes[0, 1]
ax.axis("on")
ax.imshow(hillshade(z0, dx), cmap="gray", extent=ext, origin="lower", vmin=0, vmax=1)
ax.contour(np.arange(nx) * dx + 0.5 * dx, np.arange(ny) * dx + 0.5 * dx, z0, levels=np.arange(2, 26, 2),
           colors="orange", linewidths=0.4)
ax.set_title("初期地形(円錐丘 H = 24 / 15 / 9 / 5 m, tanθ = 0.8)")
for r, c in enumerate(cases, start=1):
    for k, i in enumerate(isel):
        t, z = c["snaps"][i]
        ax = axes[r, k]
        ax.imshow(hillshade(z, dx), cmap="gray", extent=ext, origin="lower", vmin=0, vmax=1)
        ax.contour(np.arange(nx) * dx + 0.5 * dx, np.arange(ny) * dx + 0.5 * dx, z, levels=np.arange(1, 26, 1),
                   colors="orange", linewidths=0.3)
        ax.set_title("%s  T_geo = %.1e s" % (labels[c["name"]], t), fontsize=10)
        if k == 0:
            ax.set_ylabel("y (m)")
        if r == len(cases):
            ax.set_xlabel("x (m)")
fig.tight_layout()
fig.savefig("figs/maps.png", dpi=110)
plt.close(fig)

# ---------------------------------------------------------------- 図 2: 横断
fig, axes = plt.subplots(len(cases), 1, figsize=(13, 2.8 * len(cases)), sharex=True)
jc = int(YC / dx)
x = (np.arange(nx) + 0.5) * dx
for ax, c in zip(np.atleast_1d(axes), cases):
    ax.plot(x, c["z0"][jc], "k--", lw=0.8, label="初期")
    n = len(c["snaps"])
    cmap = plt.get_cmap("viridis")
    for i in range(1, n):
        t, z = c["snaps"][i]
        ax.plot(x, z[jc], color=cmap(i / (n - 1)), lw=0.9,
                label=("T_geo = %.1e s" % t) if i in (1, n // 2, n - 1) else None)
    ax.set_ylabel("z (m)")
    ax.set_title(labels[c["name"]], fontsize=10, loc="left")
    ax.set_ylim(-0.5, 26)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, loc="upper right")
np.atleast_1d(axes)[-1].set_xlabel("x (m)(y = 40 m、4 つの丘の頂を通る横断)")
fig.tight_layout()
fig.savefig("figs/sections.png", dpi=110)
plt.close(fig)

# ---------------------------------------------------------------- 図 3: 半径方向断面
fig, axes = plt.subplots(len(cases), len(HILLS), figsize=(3.4 * len(HILLS), 2.6 * len(cases)), sharex="col")
for r, c in enumerate(cases):
    for k, (xc, H) in enumerate(HILLS):
        ax = axes[r, k]
        rc0, prof0, _ = radial_profile(c["z0"], xc, YC, H / TANB + 12, dx)
        m = metrics[c["name"]][k]
        ax.plot(rc0, prof0, "k--", lw=0.8, label="初期")
        ax.plot(m["rc"], m["prof"], "r-", lw=1.4, label="T_geo = %.1e s" % TSEL)
        if np.isfinite(m["wcap"]):
            ax.axvline(m["wcap"], color="b", lw=0.6, ls=":", label="キャップ半幅")
        ax.set_ylim(-0.5, H + 1)
        ax.grid(alpha=0.3)
        if r == 0:
            ax.set_title("丘 H₀ = %g m" % H)
        if k == 0:
            ax.set_ylabel("%s\nz (m)" % labels[c["name"]], fontsize=8)
        if r == len(cases) - 1:
            ax.set_xlabel("頂からの距離 r (m)")
        if r == 0 and k == 0:
            ax.legend(fontsize=7)
fig.tight_layout()
fig.savefig("figs/radial.png", dpi=110)
plt.close(fig)

# ---------------------------------------------------------------- 図 4: 丸さ vs 丘の大きさ、頂の時系列
fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))
Hs = [H for _, H in HILLS]
for c in cases:
    mm = metrics[c["name"]]
    axes[0].plot(Hs, [m["smax"] for m in mm], "o-", label=labels[c["name"]])
    axes[1].plot(Hs, [max(-m["curv"], 1e-3) for m in mm], "o-", label=labels[c["name"]])
axes[0].axhline(TANB, color="k", lw=0.5, ls="--")
axes[0].text(5, TANB + 0.05, "初期の側面勾配 0.8", fontsize=8)
axes[0].set_xlabel("丘の初期高さ H₀ (m)")
axes[0].set_ylabel("側面の最大勾配(方位平均断面)")
axes[0].set_title("側面の急峻化(尖る型)/ 緩傾斜化(丸い型)(T_geo = %.1e s)" % TSEL)
axes[0].grid(alpha=0.3)
axes[0].legend(fontsize=8)
axes[1].set_xlabel("丘の初期高さ H₀ (m)")
axes[1].set_ylabel("頂の曲率 −∂²z/∂r² (1/m)(大 = 尖る)")
axes[1].set_yscale("log")
axes[1].set_title("頂の鋭さ(T_geo = %.1e s)" % TSEL)
axes[1].grid(alpha=0.3, which="both")
for c in cases:
    for k, (xc, H) in enumerate(HILLS):
        ts, zs = [], []
        for t, z in c["snaps"]:
            _, _, (_, _, zsum) = radial_profile(z, xc, YC, H / TANB + 12, dx)
            ts.append(t)
            zs.append(zsum)
        axes[2].plot(ts, zs, color=plt.get_cmap("tab10")(cases.index(c)), lw=1.0,
                     ls=["-", "--", "-.", ":"][k], label=(labels[c["name"]] if k == 0 else None))
axes[2].set_xlabel("地形時間 T_geo (s)")
axes[2].set_ylabel("頂の高さ (m)")
axes[2].set_title("頂の低下(線種: 実線 H₀=24, 破線 15, 一点鎖線 9, 点線 5 m)")
axes[2].grid(alpha=0.3)
axes[2].legend(fontsize=8)
fig.tight_layout()
fig.savefig("figs/rounding.png", dpi=110)
plt.close(fig)
print("\nfigs/maps.png, sections.png, radial.png, rounding.png written")
