#!/usr/bin/env python3
"""examples/shield_volcano の図と数値(make run・make run-dome の後に実行)。引数 en で英語版を en/figs/ に描く。

  figs/mechanism.png  機構の模式図(計算結果ではない)
  figs/setup.png      火口の位置と噴火の列
  figs/shield.png     S1・S2 の最終の地形(陰影と等高線)、方位平均の断面、S1 の成長
  figs/dome.png       溶岩ドームの形と塑性ドームの解析解(固化なし・固化あり)

画面に形の数値(高さ・直径・高さ/直径・勾配・台帳)を書く(README の表の値)。
"""
import math
import os
import re
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource

EN = "en" in sys.argv[1:]
def T(ja, en): return en if EN else ja
FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)

RHO, G = 2600.0, 9.8
DX = 100.0
CASES = [("S1", 2.0e3, T("S1: 降伏応力 2×10³ Pa", "S1: yield stress 2×10³ Pa")),
         ("S2", 2.0e4, T("S2: 降伏応力 2×10⁴ Pa", "S2: yield stress 2×10⁴ Pa"))]
# 比較の相手: アイスランドの楯状火山(かんらん石ソレアイト質 24 座)の中央値(Rossi 1996)
ROSSI = {"slope": 2.7, "H": 60.0, "D": 3600.0, "HD": 0.019, "V": 0.2e9}
THICK_MIN = 0.5      # 覆われた面積に数える堆積の厚さ (m)


def load(case, k):
    return np.loadtxt("result_%s/%s.txt" % (case, k))


def vents(case):
    """param ファイルから噴火口の (i, j, 開始 s, 終了 s, 体積 m3) を読む"""
    cell, val = {}, {}
    for line in open("param_%s.txt" % case, encoding="utf-8"):
        m = re.match(r"\s*lv_cell\(1:2,1,(\d+)\)\s*=\s*(\d+),\s*(\d+)", line)
        if m:
            cell[int(m.group(1))] = (int(m.group(2)), int(m.group(3)))
        m = re.match(r"\s*lv_val\(1:2,\d+,(\d+)\)\s*=\s*([-\d.eE+]+),\s*([-\d.eE+]+)", line)
        if m:
            val.setdefault(int(m.group(1)), []).append((float(m.group(2)) * 60.0, float(m.group(3))))
    out = []
    for k in sorted(cell):
        on = [t for t, q in val[k] if q > 0.0]
        q = max(q for t, q in val[k])
        out.append((cell[k][0], cell[k][1], min(on), max(on), q * (max(on) - min(on))))
    return out


def morph(dep, z1):
    """形の数値: 高さ・面積等価直径・高さ/直径・覆われたセルの勾配"""
    cov = dep > THICK_MIN
    area = cov.sum() * DX * DX
    d = 2.0 * math.sqrt(area / math.pi)
    h = dep.max()
    gy, gx = np.gradient(z1, DX)
    sl = np.degrees(np.arctan(np.hypot(gx, gy)))[cov]
    return {"H": h, "D": d, "HD": h / d, "slope_med": float(np.median(sl)), "slope_mean": float(sl.mean()),
            "V": dep.sum() * DX * DX}


def vexag(ax, xm=1.0):
    """描いた軸の縦の拡大率(横 1 m の長さに対する縦 1 m の長さの比)。xm は横軸の単位を m にする係数。
    レイアウトを決めた後(tight_layout の後)に呼ぶ。"""
    bb = ax.get_window_extent()
    (x0, x1), (y0, y1) = ax.get_xlim(), ax.get_ylim()
    return ((x1 - x0) * xm / bb.width) / ((y1 - y0) / bb.height)


def radial(dep, ic, jc):
    n = dep.shape[0]
    jj, ii = np.mgrid[0:n, 0:n]
    r = np.hypot((ii - ic) * DX, (jj - jc) * DX)
    rb = np.arange(0.0, 6000.0 + DX, DX)
    rc = 0.5 * (rb[1:] + rb[:-1])
    prof = np.array([dep[(r >= rb[k]) & (r < rb[k + 1])].mean() if ((r >= rb[k]) & (r < rb[k + 1])).any() else np.nan
                     for k in range(len(rb) - 1)])
    return rc, prof


# ---------------------------------------------------------------- 機構の模式図
fig, axs = plt.subplots(1, 3, figsize=(16, 4.4))
ax = axs[0]
x = np.linspace(0, 10, 400)
bed = 3.0 - 0.3 * x
ax.plot(x, bed, "0.35", lw=2)
xl = np.linspace(1.5, 7.6, 300)
top = 3.0 - 0.3 * xl + 0.55 * np.sqrt(np.clip((7.6 - xl) / 0.8, 0.0, 1.0))
ax.fill_between(xl, 3.0 - 0.3 * xl, top, color="#c0392b", alpha=0.85)
ax.plot([1.5], [3.0 - 0.3 * 1.5], "k^", ms=8)
ax.text(1.2, 2.25, T("火口", "vent"), fontsize=9)
xm = 4.5
ax.annotate("", xy=(xm, 3.0 - 0.3 * xm), xytext=(xm, 3.0 - 0.3 * xm + 0.55), arrowprops=dict(arrowstyle="<->", lw=1))
ax.text(xm + 0.15, 3.0 - 0.3 * xm + 0.6, "h∞", fontsize=10)
ax.text(4.2, 3.2, T("止まる厚さ h∞ = τ_y /(ρ g tanθ)\n降伏応力 τ_y が大きいほど厚く短い",
                    "stop thickness h∞ = τ_y /(ρ g tanθ)\nlarger yield stress τ_y → thicker, shorter"), fontsize=9)
ax.text(0.2, 0.2, T("止まった溶岩は固まって地形 z になり、\n次の溶岩はその上を流れる",
                    "stopped lava solidifies into terrain z;\nlater lava flows over it"), fontsize=9)
ax.set_xlim(0, 10); ax.set_ylim(-0.2, 4.2); ax.set_aspect("equal")
ax.set_title(T("(a) 1 回の溶岩流: 降伏応力で止まり、固まる", "(a) one lava flow stops by its yield stress and solidifies"), fontsize=10)
ax.axis("off")
ax = axs[1]
xx = np.linspace(-5, 5, 300)
base = np.zeros_like(xx)
cols = plt.cm.YlOrRd(np.linspace(0.35, 0.9, 6))
for k, (c0, w, h) in enumerate([(-0.8, 2.6, 0.35), (0.9, 2.4, 0.35), (-0.2, 3.4, 0.3), (1.2, 2.8, 0.3), (-1.4, 3.0, 0.3), (0.3, 3.8, 0.25)]):
    lay = h * np.clip(1 - ((xx - c0) / w) ** 2, 0, None) ** 0.5
    ax.fill_between(xx, base, base + lay, color=cols[k], ec="k", lw=0.3)
    base = base + lay
    ax.plot([c0], [base[np.argmin(abs(xx - c0))] + 0.08], "kv", ms=5)
ax.text(-4.8, 1.75, T("火口の位置と噴出量を変えて\n溶岩流を重ねる → 楯状の高まり", "lava flows from shifting vents with\nvarying volumes pile up → a shield"), fontsize=9)
ax.set_xlim(-5, 5); ax.set_ylim(0, 2.3)
ax.set_title(T("(b) 断続的な噴火で積み重なる", "(b) intermittent eruptions stack flows"), fontsize=10)
ax.axis("off")
ax = axs[2]
r = np.linspace(0, 1, 200)
for a_, lab in [(0.08, T("降伏応力が小さい", "small yield stress")), (0.6, T("大きい(溶岩ドーム)", "large (lava dome)"))]:
    R = (a_ / 0.08) ** -0.2          # 同じ体積 V = (8π/15)√a R^2.5 にそろえる: R ∝ a^−0.2(a = 2τ_y/ρg)
    h = np.sqrt(a_ * R * (1 - r))
    ax.plot(R * np.r_[-r[::-1], r], np.r_[h[::-1], h], lw=2, label=lab)
ax.text(-0.95, 0.85, T("1 つの火口から同じ体積を噴出して止まった形\nh(r)² = (2τ_y/ρg)(R − r)(塑性ドーム)", "shape at rest of the same volume from one vent\nh(r)² = (2τ_y/ρg)(R − r) (plastic dome)"), fontsize=9)
ax.set_ylim(0, 1.1); ax.legend(fontsize=8, loc="center right")
ax.set_title(T("(c) 降伏応力が形を決める(粘度は速さだけ)", "(c) the yield stress sets the shape (viscosity only the speed)"), fontsize=10)
ax.set_yticks([]); ax.set_xticks([])
fig.suptitle(T("機構の模式図(計算結果ではない)", "Schematic of the mechanism (not computed results)"), fontsize=11)
fig.tight_layout(); fig.savefig(f"{FIGDIR}/mechanism.png", dpi=100); plt.close(fig)

# ---------------------------------------------------------------- 設定(火口と噴火の列)
v1 = vents("S1")
fig, axs = plt.subplots(1, 2, figsize=(13, 5))
ax = axs[0]
n = 120
ic = jc = (n + 1) / 2.0
xs = [(i - ic) * DX / 1000 for i, j, *_ in v1]
ys = [(jc - j) * DX / 1000 for i, j, *_ in v1]
sc = ax.scatter(xs, ys, s=[v / 1e6 * 3 for *_, v in v1], c=range(1, len(v1) + 1), cmap="viridis", edgecolors="k")
for k, (x_, y_) in enumerate(zip(xs, ys), start=1):
    ax.annotate(str(k), (x_, y_), fontsize=7, xytext=(4, 4), textcoords="offset points")
ax.set_xlim(-2, 2); ax.set_ylim(-2, 2); ax.set_aspect("equal"); ax.grid(alpha=0.3)
ax.set_xlabel(T("中心からの距離 x (km)", "x from the center (km)")); ax.set_ylabel("y (km)")
fig.colorbar(sc, ax=ax, label=T("噴火の順番", "eruption order"), shrink=0.85)
ax.set_title(T("(a) 火口の位置(円の大きさ = 噴出量)。12 km 四方の領域の中央 4 km", "(a) vent positions (circle size = volume); central 4 km of the 12 km domain"), fontsize=9)
ax = axs[1]
for case, col in [("S1", "C0"), ("S2", "C1")]:
    vv = vents(case)
    for k, (i, j, t0, t1, v) in enumerate(vv):
        ax.barh(k + (0.2 if case == "S2" else -0.2), (t1 - t0) / 86400, left=t0 / 86400, height=0.35, color=col,
                label=(T("S1 の噴火", "S1 eruptions") if case == "S1" else T("S2 の噴火(休止が長い)", "S2 eruptions (longer repose)")) if k == 0 else None)
ax.invert_yaxis(); ax.set_yticks(range(len(v1))); ax.set_yticklabels([str(k + 1) for k in range(len(v1))], fontsize=7)
ax.set_xlabel(T("時刻 (日)", "time (days)")); ax.set_ylabel(T("噴火", "eruption"))
ax.legend(fontsize=8); ax.grid(alpha=0.3, axis="x")
vmin_, vmax_ = min(v for *_, v in v1) / 1e7, max(v for *_, v in v1) / 1e7
ax.set_title(T(f"(b) 噴火の列(噴出率 20〜60 m³/s、1 回 {vmin_:.1f}〜{vmax_:.1f}×10⁷ m³)",
               f"(b) eruption sequence (20–60 m³/s, {vmin_:.1f}–{vmax_:.1f}×10⁷ m³ each)"), fontsize=9)
fig.tight_layout(); fig.savefig(f"{FIGDIR}/setup.png", dpi=100); plt.close(fig)

# ---------------------------------------------------------------- 楯状火山の結果
res = {}
for case, tauy, lab in CASES:
    z0 = load(case, "Z0000"); z1 = load(case, "Z9998"); hl = load(case, "Hl9998")
    dep = z1 + hl - z0
    mo = morph(dep, z1 + hl)
    vin = sum(v for *_, v in vents(case))
    mo["Vin"] = vin
    mo["molten"] = hl.sum() * DX * DX
    w = dep.clip(min=0)
    jj, ii = np.mgrid[0:dep.shape[0], 0:dep.shape[1]]
    mo["ic"] = (ii * w).sum() / w.sum(); mo["jc"] = (jj * w).sum() / w.sum()
    mo["edge"] = max(dep[0, :].max(), dep[-1, :].max(), dep[:, 0].max(), dep[:, -1].max())
    res[case] = (dep, z1 + hl, mo)
    print("%s: H %.1f m, D %.2f km (area %.1f km2), H/D %.4f, slope median %.2f deg / mean %.2f deg, "
          "deposit %.3e m3 (erupted %.3e, molten %.2e), max thickness at the domain edge %.2f m"
          % (case, mo["H"], mo["D"] / 1000, math.pi * (mo["D"] / 2) ** 2 / 1e6, mo["HD"], mo["slope_med"],
             mo["slope_mean"], mo["V"], vin, mo["molten"], mo["edge"]))

print("reference: median of Icelandic shields (Rossi 1996): H %.0f m, D %.1f km, H/D %.3f, slope %.1f deg, volume %.1f km3"
      % (ROSSI["H"], ROSSI["D"] / 1000, ROSSI["HD"], ROSSI["slope"], ROSSI["V"] / 1e9))

fig = plt.figure(figsize=(14, 11))
ls = LightSource(azdeg=315, altdeg=35)
for k, (case, tauy, lab) in enumerate(CASES):
    dep, zs, mo = res[case]
    ax = fig.add_subplot(2, 2, k + 1)
    ext = [-6, 6, -6, 6]
    rgb = ls.shade(zs[::-1], cmap=plt.cm.YlOrBr, vert_exag=10, blend_mode="soft", vmin=0,
                   vmax=max(r[0].max() for r in res.values()), dx=DX, dy=DX)
    ax.imshow(rgb, extent=ext, origin="lower")
    xc = (np.arange(120) + 0.5) * DX / 1000 - 6
    step = 10 if case == "S1" else 20
    ax.contour(xc, xc, zs[::-1], levels=np.arange(step, zs.max(), step), colors="k", linewidths=0.5)
    ax.set_xlim(-5, 5); ax.set_ylim(-5, 5)
    ax.set_xlabel("x (km)"); ax.set_ylabel("y (km)")
    ax.set_title(T(f"({'ab'[k]}) {lab}: 高さ {mo['H']:.0f} m、直径 {mo['D']/1000:.1f} km、等高線 {step} m",
                   f"({'ab'[k]}) {lab}: height {mo['H']:.0f} m, diameter {mo['D']/1000:.1f} km, contours {step} m"), fontsize=9)
ax = fig.add_subplot(2, 2, 3)
for (case, tauy, lab), col in zip(CASES, ["C0", "C1"]):
    dep, zs, mo = res[case]
    rc, pr = radial(dep, mo["ic"], mo["jc"])
    ax.plot(rc / 1000, pr, col, lw=2, label=lab)
ax.set_xlim(0, 5); ax.set_ylim(0, None); ax.grid(alpha=0.3); ax.legend(fontsize=8)
ax.set_xlabel(T("中心からの距離 (km)", "distance from the center (km)"))
ax.set_ylabel(T("溶岩の厚さ(方位平均) (m)", "lava thickness, azimuthal mean (m)"))
ax_c = ax
ax = fig.add_subplot(2, 2, 4)
z0 = load("S1", "Z0000")
vv = vents("S1")
frames = sorted(int(f[1:5]) for f in os.listdir("result_S1") if re.match(r"Z\d{4}\.txt", f) and f not in ("Z0000.txt", "Z9998.txt"))
dtf = float(re.search(r"dt_file\s*=\s*(\d+)", open("param_S1.txt", encoding="utf-8").read()).group(1))
cmap = plt.cm.viridis
sel = [f for f in frames if f % 2 == 0]
for m, fr in enumerate(sel):
    tfr = fr * dtf
    ne = sum(1 for *_, t1, v in vv if t1 <= tfr)
    dep = load("S1", "Z%04d" % fr) - z0
    rc, pr = radial(dep, res["S1"][2]["ic"], res["S1"][2]["jc"])
    ax.plot(rc / 1000, pr, color=cmap(m / max(len(sel) - 1, 1)), lw=1.5,
            label=T(f"{tfr/86400:.0f} 日(噴火 {ne} 回の後)", f"day {tfr/86400:.0f} (after {ne} eruptions)"))
ax.set_xlim(0, 5); ax.set_ylim(0, None); ax.grid(alpha=0.3); ax.legend(fontsize=8)
ax.set_xlabel(T("中心からの距離 (km)", "distance from the center (km)"))
ax.set_ylabel(T("固化した溶岩の厚さ(方位平均) (m)", "solidified lava, azimuthal mean (m)"))
ax.set_title(T("(d) S1 の成長(固化した分)", "(d) growth of S1 (solidified part)"), fontsize=9)
ax_c.set_title(T("(c) 方位平均の断面(縦は約 25 倍に拡大)", "(c) azimuthal mean profiles (vertical exaggeration about 25×)"), fontsize=9)
fig.tight_layout()
ex = vexag(ax_c, 1000.0)
ax_c.set_title(T(f"(c) 方位平均の断面(縦は約 {ex:.0f} 倍に拡大)", f"(c) azimuthal mean profiles (vertical exaggeration about {ex:.0f}×)"),
               fontsize=9)
fig.savefig(f"{FIGDIR}/shield.png", dpi=90); plt.close(fig)

# ---------------------------------------------------------------- 溶岩ドーム
ND, DXD, TAUY = 101, 10.0, 1.0e5
c = ND // 2
jj, ii = np.mgrid[0:ND, 0:ND]
dome = {}
for case in ("dome", "dome_sol"):
    z0 = np.loadtxt("result_%s/Z0000.txt" % case); z1 = np.loadtxt("result_%s/Z9998.txt" % case)
    hl = np.loadtxt("result_%s/Hl9998.txt" % case)
    dep = z1 + hl - z0
    V = dep.sum() * DXD * DXD
    a = 2 * TAUY / (RHO * G)
    R = (V / ((8 * math.pi / 15) * math.sqrt(a))) ** 0.4
    H = math.sqrt(a * R)
    cov = dep > 0.1
    rA = math.sqrt(cov.sum() * DXD * DXD / math.pi)
    dome[case] = (dep, V, a, R, H, cov, rA)
    print("%s: V %.3e m3 (molten %.2e), H %.1f m (analytic %.1f, %+.1f%%), equivalent radius %.0f m "
          "(analytic %.0f, %+.1f%%), H/D %.3f" % (case, V, hl.sum() * DXD * DXD, dep[c, c], H,
          100 * (dep[c, c] / H - 1), rA, R, 100 * (rA / R - 1), dep[c, c] / (2 * rA)))
dep, V, a, R, H, cov, rA = dome["dome"]
fig, axs = plt.subplots(1, 2, figsize=(14, 5))
ax = axs[0]
im = ax.imshow(np.where(cov, dep, np.nan)[::-1], extent=[-505, 505, -505, 505], origin="lower", cmap="copper_r")
th = np.linspace(0, 2 * math.pi, 200)
ax.plot(R * np.cos(th), R * np.sin(th), "b--", lw=1, label=T(f"解析解の半径 R = {R:.0f} m", f"analytic radius R = {R:.0f} m"))
ax.set_xlim(-300, 300); ax.set_ylim(-300, 300); ax.set_aspect("equal"); ax.legend(fontsize=8, loc="lower right")
fig.colorbar(im, ax=ax, label=T("溶岩の厚さ (m)", "lava thickness (m)"), shrink=0.85)
ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
ax.set_title(T(f"(a) 溶岩ドーム(固化なし。上から見た図): 高さ {dep[c, c]:.0f} m、高さ/直径 {dep[c, c] / (2 * rA):.2f}",
               f"(a) lava dome (no solidification), plan view: height {dep[c, c]:.0f} m, height/diameter {dep[c, c] / (2 * rA):.2f}"), fontsize=9)
ax = axs[1]
rr = np.linspace(0, R, 300)
ax.plot(rr, np.sqrt(a * (R - rr)), "k", lw=2, label=T("塑性ドームの解析解 h² = (2τ_y/ρg)(R − r)(Blake 1990)", "plastic dome h² = (2τ_y/ρg)(R − r) (Blake 1990)"))
ax.plot(-rr, np.sqrt(a * (R - rr)), "k", lw=2)
xs = (np.arange(ND) - c) * DXD
ax.plot(xs, dep[c, :], "o-", ms=3, lw=0.8, label=T("固化なし: 格子軸の方向", "no solidification: along a grid axis"))
kk = np.arange(-c, ND - c)
ax.plot(kk * DXD * math.sqrt(2), dep[c + kk, c + kk], "s-", ms=3, lw=0.8, label=T("固化なし: 斜めの方向", "no solidification: along the diagonal"))
ds = dome["dome_sol"][0]
ax.plot(xs, ds[c, :], "--", color="C3", lw=1.5, label=T("固化あり(lv_vsol = 10⁻⁶ m/s): 格子軸の方向", "with solidification (lv_vsol = 10⁻⁶ m/s): grid axis"))
ax.set_xlim(-300, 300); ax.set_ylim(0, 1.6 * H)
ax.grid(alpha=0.3); ax.legend(fontsize=7, loc="upper right")
ax.set_xlabel(T("中心からの距離 (m)(縦は約 3 倍に拡大)", "distance from the center (m) (vertical exaggeration about 3×)"))
ax_b = ax
ax.set_ylabel(T("溶岩の厚さ (m)", "lava thickness (m)"))
ax.set_title(T("(b) 断面と解析解(τ_y = 10⁵ Pa、体積 2×10⁶ m³)", "(b) profiles and the analytic solution (τ_y = 10⁵ Pa, volume 2×10⁶ m³)"), fontsize=9)
fig.tight_layout()
ex = vexag(ax_b)
ax_b.set_xlabel(T(f"中心からの距離 (m)(縦は約 {ex:.1f} 倍に拡大)", f"distance from the center (m) (vertical exaggeration about {ex:.1f}×)"))
fig.savefig(f"{FIGDIR}/dome.png", dpi=100); plt.close(fig)
