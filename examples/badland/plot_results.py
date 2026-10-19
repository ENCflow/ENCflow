#!/usr/bin/env python3
"""examples/badland の図化と数表(事前に param*.txt を実行しておく)。

  python3 plot_results.py            # 存在する result* をすべて図化し、数表を表示する

図(figs/):
  main_maps.png     主ケースの地形の時間発展(地図・崖面帯の横断・谷と稜線の縦断)
  main_series.png   主ケースの時系列(起伏・卓越波長・下刻・谷頭の後退・排出量)
  main_features.png 主ケースのバッドランド的特徴(勾配の分布・稜線の鋭さ・D8 流域網)
  spacing.png       谷間隔の選択則(spl_lc 系列と格子の κ)と格子収束(Δx = 0.5/1/2)

依存: numpy, matplotlib(scipy は使わない)
"""
import csv
import glob
import os
import re
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
matplotlib.rcParams["font.family"] = ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs("figs", exist_ok=True)


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
    if not os.path.isdir(res) or not os.path.exists(os.path.join(res, "Z9998.txt")):
        return None
    dx = float(p["lx"]) / int(p["nx"])
    times = file_times(res)
    snaps = []
    for n in sorted(times):
        if n >= 9998:
            continue
        f = os.path.join(res, "Z%04d.txt" % n)
        if os.path.exists(f):
            snaps.append((times[n] * float(p["morfac"]), np.loadtxt(f)))
    zf = np.loadtxt(os.path.join(res, "Z9998.txt"))
    tgeo_end = float(p["tt"]) * float(p["morfac"])
    if not snaps or snaps[-1][0] < tgeo_end:
        snaps.append((tgeo_end, zf))
    log = ""
    for cand in ("Screen.log", os.path.join(res, "Screen.log")):
        if os.path.exists(cand):
            log = open(cand, errors="ignore").read()
    hp = float(np.loadtxt(os.path.join(res, "Z0000.txt")).max())
    return dict(name=os.path.basename(param_fn)[:-4], p=p, dx=dx, hp=hp, lc=float(p.get("spl_lc", 0)),
                snaps=snaps, z0=snaps[0][1], zf=zf, log=log)


# ---------------------------------------------------------------- 解析
def cliff_cols(z, hp):
    return [c for c in range(z.shape[1]) if 0.5 < z[:, c].mean() < hp - 0.5]


def valley_spacing(z, cols, dx, pmin=0.5):
    """崖面帯の各列で、y 方向の局所最小(谷)を prominence >= pmin で拾い、間隔の平均・本数"""
    sp, nv = [], []
    for c in cols:
        s = -z[:, c]
        idx = [i for i in range(1, len(s) - 1) if s[i] >= s[i - 1] and s[i] > s[i + 1]]
        keep = []
        for i in idx:
            left = s[:i].min() if i > 0 else s[i]
            right = s[i + 1:].min() if i < len(s) - 1 else s[i]
            # prominence: 隣の高い峰(谷間の尾根)までの落差の小さい方
            lo = s[i]
            lmax = s[:i][::-1]; rmax = s[i + 1:]
            lcut = np.where(lmax > lo)[0]; rcut = np.where(rmax > lo)[0]
            lmin = lmax[:lcut[0]].min() if len(lcut) else lmax.min()
            rmin = rmax[:rcut[0]].min() if len(rcut) else rmax.min()
            prom = lo - max(lmin, rmin)
            if prom >= pmin:
                keep.append(i)
        nv.append(len(keep))
        if len(keep) > 1:
            sp.extend(np.diff(keep) * dx)
    return (np.mean(sp) if sp else np.nan, np.std(sp) if sp else np.nan, float(np.mean(nv)) if nv else 0.0)


def spectrum_centroid(z, cols, dx):
    ny = z.shape[0]
    P = np.zeros(ny // 2 + 1)
    for c in cols:
        s = z[:, c] - z[:, c].mean()
        P += np.abs(np.fft.rfft(s)) ** 2
    k = np.fft.rfftfreq(ny, d=dx)
    P[0] = 0
    kc = (P[1:] * k[1:]).sum() / P[1:].sum()
    return 1.0 / kc, k[1:], P[1:] / len(cols)


def metrics(z, z0, dx, hp):
    cols = cliff_cols(z, hp)
    if not cols:
        return None
    rel = float(np.mean([z[:, c].std() for c in cols]))
    sp, sps, nv = valley_spacing(z, cols, dx)
    lam, _, _ = spectrum_centroid(z, cols, dx)
    stds = z.std(axis=0)
    cr = np.where(stds > 0.2)[0]
    xhead = (cr.min() + 0.5) * dx if len(cr) else np.nan
    return dict(relief=rel, spacing=sp, spacing_sd=sps, nvalleys=nv, lam=lam, max_inc=float((z0 - z).max()),
                mean_inc=float((z0 - z)[:, cols].mean()), xhead=xhead)


def d8_accumulation(z, sw):
    """最急降下 D8 の集水面積(セル数)。海セルは流出先として受けるだけ"""
    ny, nx = z.shape
    zz = np.where(sw > 0, -1e9, z)
    order = np.argsort(-zz, axis=None)
    acc = np.ones((ny, nx))
    dirs = [(-1, -1, np.sqrt(2)), (-1, 0, 1), (-1, 1, np.sqrt(2)), (0, -1, 1), (0, 1, 1), (1, -1, np.sqrt(2)), (1, 0, 1), (1, 1, np.sqrt(2))]
    for flat in order:
        j, i = divmod(int(flat), nx)
        if sw[j, i] > 0:
            continue
        best, bj, bi = 0.0, -1, -1
        for dj, di, dd in dirs:
            jj, ii = j + dj, i + di
            if 0 <= jj < ny and 0 <= ii < nx:
                s = (zz[j, i] - zz[jj, ii]) / dd
                if s > best:
                    best, bj, bi = s, jj, ii
        if bj >= 0:
            acc[bj, bi] += acc[j, i]
    acc[sw > 0] = 0
    return acc


def slope_curv(z, dx):
    zp = np.pad(z, 1, mode="edge")
    sx = (zp[1:-1, 2:] - zp[1:-1, :-2]) / (2 * dx)
    sy = (zp[2:, 1:-1] - zp[:-2, 1:-1]) / (2 * dx)
    kap = (zp[1:-1, 2:] + zp[1:-1, :-2] + zp[2:, 1:-1] + zp[:-2, 1:-1] - 4 * z) / dx ** 2
    return np.hypot(sx, sy), kap


def fmt(v, f="%.1f"):
    return "–" if v is None or (isinstance(v, float) and np.isnan(v)) else (f % v)


# ---------------------------------------------------------------- 主ケース
main = load_case("param.txt")
if main is not None:
    z0, zf, dx, hp = main["z0"], main["zf"], main["dx"], main["hp"]
    ny, nx = z0.shape
    ext = [0, nx * dx, 0, ny * dx]
    sw = (z0 <= 0.0).astype(int)
    snaps = main["snaps"]
    picks = [int(np.argmin([abs(t - tt) for t, _ in snaps])) for tt in (0.0, 1.8e6, 3.6e6, snaps[-1][0])]

    # --- 地図と断面 ---
    fig = plt.figure(figsize=(16, 9))
    gs = fig.add_gridspec(2, 4, height_ratios=[1.6, 1])
    for k, ip in enumerate(picks):
        t, z = snaps[ip]
        ax = fig.add_subplot(gs[0, k])
        im = ax.imshow(z, origin="lower", extent=ext, cmap="terrain", vmin=0, vmax=hp)
        ax.set_xlim(30, 100); ax.set_title("T_geo = %.1e s\n(10 mm/h の降雨 %.0f 日分)" % (t, t / 86400.0), fontsize=9)
        ax.set_xlabel("x (m)")
        if k == 0:
            ax.set_ylabel("y (m)")
    fig.colorbar(im, ax=fig.axes[:4], shrink=0.6, label="z (m)")
    # 崖面帯の横断(時間発展)
    ax = fig.add_subplot(gs[1, 0:2])
    y = (np.arange(ny) + 0.5) * dx
    cols0 = cliff_cols(z0, hp); c = cols0[len(cols0) // 2]
    for ip in picks:
        t, z = snaps[ip]
        ax.plot(y, z[:, c], label="T_geo = %.1e s" % t, lw=1)
    ax.set_xlabel("y (m)"); ax.set_ylabel("z (m)"); ax.set_title("初期の崖面の中央の列(x = %.1f m)の横断" % ((c + 0.5) * dx), fontsize=9)
    ax.legend(fontsize=7)
    # 谷と稜線の縦断(最終)
    ax = fig.add_subplot(gs[1, 2:4])
    x = (np.arange(nx) + 0.5) * dx
    cols = cliff_cols(zf, hp); cf = cols[len(cols) // 2]
    jv = int(np.argmin(zf[:, cf])); jr = int(np.argmax(zf[:, cf]))
    ax.plot(x, z0[jv, :], "0.6", label="初期")
    ax.plot(x, zf[jv, :], "C0", label="最終: 谷底(y = %.1f m)" % ((jv + 0.5) * dx))
    ax.plot(x, zf[jr, :], "C3", label="最終: 稜線(y = %.1f m)" % ((jr + 0.5) * dx))
    ax.set_xlabel("x (m)"); ax.set_ylabel("z (m)"); ax.legend(fontsize=7); ax.set_title("縦断(x 方向)", fontsize=9)
    fig.savefig("figs/main_maps.png", dpi=110, bbox_inches="tight"); plt.close(fig)

    # --- 時系列 ---
    rows = []
    for t, z in snaps:
        m = metrics(z, z0, dx, hp)
        if m:
            m["t"] = t; rows.append(m)
    T = np.array([r["t"] for r in rows])
    fig, ax = plt.subplots(1, 4, figsize=(16, 3.6))
    ax[0].plot(T, [r["relief"] for r in rows], "o-"); ax[0].set_ylabel("崖面帯の y 方向起伏 (m)")
    ax[1].plot(T, [r["lam"] for r in rows], "o-", label="スペクトル重心の波長"); ax[1].plot(T, [r["spacing"] for r in rows], "s--", label="谷間隔(prominence ≥ 0.5 m)")
    ax[1].axhline(2 * np.pi * main["lc"] / 1.31, color="k", ls=":", lw=0.8, label="線形理論 λ* = 4.8 ℓ")
    ax[1].set_ylabel("(m)"); ax[1].legend(fontsize=7)
    ax[2].plot(T, [r["max_inc"] for r in rows], "o-", label="最大下刻"); ax[2].plot(T, [r["mean_inc"] for r in rows], "s--", label="崖面帯の平均低下")
    ax[2].set_ylabel("(m)"); ax[2].legend(fontsize=7)
    ax[3].plot(T, [r["xhead"] for r in rows], "o-")
    ax[3].set_ylabel("谷頭の位置 x (m)(台地縁 60 m)")
    for a in ax:
        a.set_xlabel("T_geo (s)")
    fig.tight_layout(); fig.savefig("figs/main_series.png", dpi=110); plt.close(fig)

    # --- バッドランド的特徴 ---
    S0, K0 = slope_curv(z0, dx); Sf, Kf = slope_curv(zf, dx)
    land = sw == 0
    acc = d8_accumulation(zf, sw)
    fig, ax = plt.subplots(1, 4, figsize=(17, 4.2))
    bins = np.linspace(0, 3, 61)
    ax[0].hist(S0[land], bins=bins, histtype="step", color="0.5", label="初期", density=True)
    ax[0].hist(Sf[land], bins=bins, histtype="step", color="C3", label="最終", density=True)
    ax[0].set_xlabel("勾配 |∇z|"); ax[0].set_ylabel("頻度密度"); ax[0].legend(fontsize=8); ax[0].set_title("勾配の分布(陸)", fontsize=9)
    im = ax[1].imshow(np.clip(Kf, -3, 3), origin="lower", extent=ext, cmap="RdBu", vmin=-3, vmax=3)
    ax[1].set_xlim(30, 100); ax[1].set_title("最終の曲率 ∇²z (1/m)(青: 稜線 = 凸、赤: 谷 = 凹)", fontsize=9); fig.colorbar(im, ax=ax[1], shrink=0.8)
    im = ax[2].imshow(np.log10(np.maximum(acc, 1)), origin="lower", extent=ext, cmap="Blues")
    ax[2].set_xlim(30, 100); ax[2].set_title("最終地形の D8 集水面積 log10(セル数)", fontsize=9); fig.colorbar(im, ax=ax[2], shrink=0.8)
    # 稜線の鋭さ: 崖面帯の列ごとの稜線(局所最大)の曲率
    ridge_k = []
    for cc in cols:
        col = zf[:, cc]
        for j in range(1, ny - 1):
            if col[j] > col[j - 1] and col[j] >= col[j + 1]:
                ridge_k.append((col[j - 1] + col[j + 1] - 2 * col[j]) / dx ** 2)
    ax[3].hist(ridge_k, bins=40, color="C3"); ax[3].set_xlabel("稜線の y 方向曲率 (1/m)"); ax[3].set_title("稜線の鋭さ(崖面帯の列の局所最大)", fontsize=9)
    fig.tight_layout(); fig.savefig("figs/main_features.png", dpi=110); plt.close(fig)

    m0 = metrics(snaps[0][1], z0, dx, hp); mf = rows[-1]
    vout = re.findall(r"exported sediment volume =\s*([\d.Ee+-]+)", main["log"])
    nclip = re.findall(r"clip fired on\s+(\d+)", main["log"])
    ridge_k = np.array(ridge_k)
    print("## 主ケース(param.txt)")
    print("| 量 | 初期 | 最終(T_geo = %.1e s) |" % mf["t"]); print("|---|---|---|")
    print("| 崖面帯の y 方向起伏 (m) | %.2f | %.2f |" % (m0["relief"], mf["relief"]))
    print("| 谷間隔 (m)(prominence ≥ 0.5 m) | %s | %s ± %s(%s 本) |" % (fmt(m0["spacing"]), fmt(mf["spacing"]), fmt(mf["spacing_sd"]), fmt(mf["nvalleys"])))
    print("| スペクトル重心の波長 (m) | %.1f | %.1f |" % (m0["lam"], mf["lam"]))
    print("| 最大下刻 / 崖面帯の平均低下 (m) | – | %.1f / %.1f |" % (mf["max_inc"], mf["mean_inc"]))
    print("| 谷頭の位置 x (m)(台地縁 60 m) | %.1f | %.1f |" % (m0["xhead"], mf["xhead"]))
    print("| 稜線の y 方向曲率 (1/m): 中央値 / 最小 | – | %.1f / %.1f |" % (np.median(ridge_k), ridge_k.min()))
    print("| 勾配 > 1.0 の陸セルの割合 | %.2f | %.2f |" % ((S0[land] > 1).mean(), (Sf[land] > 1).mean()))
    if vout:
        print("| 系外排出した固体体積 (m³) | – | %s |" % vout[-1])
    if nclip:
        print("| spl_dzmax クリップの発生セル数 | – | %s |" % nclip[-1])
    print()


# ---------------------------------------------------------------- 間隔の選択則・格子収束
cases = [load_case(f) for f in ["param_grid.txt", "param_lc1.txt", "param_lc2.txt", "param_lc4.txt", "param_lc2_dx05.txt", "param_lc2_dx2.txt"]]
cases = [c for c in cases if c is not None]
if cases:
    tab = []
    for c in cases:
        z0, dx, hp = c["z0"], c["dx"], c["hp"]
        early = [s for s in c["snaps"] if s[0] >= 1.8e6 - 1][0] if any(s[0] >= 1.8e6 - 1 for s in c["snaps"]) else c["snaps"][-1]
        me = metrics(early[1], z0, dx, hp); mf = metrics(c["zf"], z0, dx, hp)
        tab.append((c, early[0], me, mf))
    print("## 谷間隔の選択則と格子収束")
    print("| ケース | spl_lc (m) | Δx (m) | 初期の起伏 (m) | T_geo = %.1e s: 重心波長 / 谷間隔 (m) | 最終: 重心波長 / 谷間隔 (m) / 本数 | 最終の起伏 (m) | 最大下刻 / 平均低下 (m) | 谷頭 x (m) |" % tab[0][1])
    print("|---|---|---|---|---|---|---|---|---|")
    for c, te, me, mf in tab:
        m0 = metrics(c["z0"], c["z0"], c["dx"], c["hp"])
        print("| %s | %g | %g | %.2f | %.1f / %s | %.1f / %s / %s | %.2f | %.1f / %.1f | %.1f |" % (
            c["name"], c["lc"], c["dx"], m0["relief"], me["lam"], fmt(me["spacing"]), mf["lam"], fmt(mf["spacing"]), fmt(mf["nvalleys"], "%.0f"), mf["relief"], mf["max_inc"], mf["mean_inc"], mf["xhead"]))

    fig, ax = plt.subplots(2, 4, figsize=(17, 8))
    # 上段: 地図(grid, lc1, lc2, lc4)
    for k, nm in enumerate(["param_grid", "param_lc1", "param_lc2", "param_lc4"]):
        cc = [c for c in cases if c["name"] == nm]
        if not cc:
            ax[0, k].axis("off"); continue
        c = cc[0]; ny, nx = c["zf"].shape; ext = [0, nx * c["dx"], 0, ny * c["dx"]]
        ts, zs = c["snaps"][int(np.argmin([abs(t - 3.6e6) for t, _ in c["snaps"]]))]
        im = ax[0, k].imshow(zs, origin="lower", extent=ext, cmap="terrain", vmin=0, vmax=c["hp"])
        ax[0, k].set_xlim(20, 60); ax[0, k].set_ylim(0, 120)
        ax[0, k].set_title(("格子の κ(spl_lc = 0)" if c["lc"] == 0 else "spl_lc = %g m" % c["lc"]) + ", T_geo = %.1e s" % ts, fontsize=9)
    # 下段左: 間隔 vs ℓ
    a = ax[1, 0]
    lcs = [c["lc"] for c, te, me, mf in tab if c["dx"] == 1.0 and c["lc"] > 0]
    a.plot(lcs, [me["lam"] for c, te, me, mf in tab if c["dx"] == 1.0 and c["lc"] > 0], "o-", label="T_geo = 1.8e6 s(重心波長)")
    a.plot(lcs, [mf["lam"] for c, te, me, mf in tab if c["dx"] == 1.0 and c["lc"] > 0], "s--", label="最終(重心波長)")
    a.plot(lcs, [mf["spacing"] for c, te, me, mf in tab if c["dx"] == 1.0 and c["lc"] > 0], "^:", label="最終(谷間隔)")
    ll = np.linspace(0.5, 4.5, 20)
    a.fill_between(ll, 4.4 * ll, 6.0 * ll, color="0.85", label="線形理論 4.4〜6 ℓ")
    g = [mf for c, te, me, mf in tab if c["lc"] == 0]
    if g:
        a.axhline(g[0]["lam"], color="k", ls=":", lw=0.8, label="格子の κ(最終)")
    a.set_xlabel("spl_lc ℓ (m)"); a.set_ylabel("波長・間隔 (m)"); a.legend(fontsize=7); a.set_title("谷間隔の選択則", fontsize=9)
    # 下段中: 格子収束
    a = ax[1, 1]
    dxs = sorted(set(c["dx"] for c, te, me, mf in tab if c["lc"] == 2.0))
    a.plot(dxs, [[me["lam"] for c, te, me, mf in tab if c["lc"] == 2.0 and c["dx"] == d][0] for d in dxs], "o-", label="重心波長 (m), T_geo = 1.8e6 s")
    for key, lab, st in [("lam", "重心波長 (m), 最終", "o--"), ("spacing", "谷間隔 (m), 最終", "s--"), ("mean_inc", "崖面帯の平均低下 (m), 最終", "^:"), ("relief", "起伏 (m), 最終", "d-.")]:
        a.plot(dxs, [[mf[key] for c, te, me, mf in tab if c["lc"] == 2.0 and c["dx"] == d][0] for d in dxs], st, label=lab)
    a.set_xscale("log"); a.set_xticks(dxs); a.set_xticklabels(["%g" % d for d in dxs]); a.set_xlabel("Δx (m)(spl_lc = 2 m)"); a.legend(fontsize=7); a.set_title("格子収束", fontsize=9)
    # 下段右 2 枚: Δx = 0.5 と 2 の地図
    for k, nm in enumerate(["param_lc2_dx05", "param_lc2_dx2"]):
        cc = [c for c in cases if c["name"] == nm]
        if not cc:
            ax[1, 2 + k].axis("off"); continue
        c = cc[0]; ny, nx = c["zf"].shape; ext = [0, nx * c["dx"], 0, ny * c["dx"]]
        ts, zs = c["snaps"][int(np.argmin([abs(t - 3.6e6) for t, _ in c["snaps"]]))]
        ax[1, 2 + k].imshow(zs, origin="lower", extent=ext, cmap="terrain", vmin=0, vmax=c["hp"])
        ax[1, 2 + k].set_xlim(20, 60); ax[1, 2 + k].set_ylim(0, 120); ax[1, 2 + k].set_title("spl_lc = 2 m, Δx = %g m, T_geo = %.1e s" % (c["dx"], ts), fontsize=9)
    fig.tight_layout(); fig.savefig("figs/spacing.png", dpi=110); plt.close(fig)
print("figs/ written")
