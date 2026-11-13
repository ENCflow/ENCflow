#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# examples/landslide_tsunami の図化(result_A/B/B0/C を読んで figs/ に保存)
#   python3 plot_results.py      figs/*.png(日本語)と数表(標準出力)
#   python3 plot_results.py en   en/figs/*.png(英語)
#   profiles.png : 各ケースの中央断面(y=97.5 m)。左 = 地形と陸上の流れの表面、右 = 湖面 z+h+hs の時間発展
#   probes.png   : 湖内プローブ(x=298, 398, 548 m)の水面時系列の比較
#   deposit.png  : t=120 s の地形変化 z−z0(中央断面)の比較
#   nonhydro.png : A・C の静水圧と非静水圧(result_A_nh / result_C_nh)の比較(中央断面とプローブ)
import os, sys, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

EN = len(sys.argv) > 1 and sys.argv[1] == "en"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
OUT = "en/figs/" if EN else "figs/"
os.makedirs(OUT, exist_ok=True)


def T(ja, en):
    return en if EN else ja


DX, J = 5.0, 19                         # 格子幅、中央行(0 始まり)
# (結果, ラベル, 色, 線種, 線幅)。A と B は湖底の堆積がほぼ重なるので、A を太い実線、B を破線で描く
CASES = [("result_A",  T("A: 岩屑なだれ(底層だけ)", "A: rockslide (bed layer only)"),            "#2a78d6", "-", 2.6),
         ("result_B",  T("B: 土石流 → 底層へ引き渡し", "B: debris flow -> handover to bed layer"), "#eb6834", "--", 1.5),
         ("result_B0", T("B0: 土石流(混合体のみ)", "B0: debris flow, mixture only"),               "#8a8983", ":", 1.8),
         ("result_C",  T("C: 海底地滑り", "C: submarine slide"),                                   "#2e9e5b", "-.", 1.5)]
x = (np.arange(120) + 0.5) * DX


def rd(rdir, name, k):
    return np.loadtxt("%s/%s%04d.txt" % (rdir, name, k))


def times(rdir):
    return {int(l.split(",")[0]): float(l.split(",")[2])
            for l in open(rdir + "/FILENUMBER.csv") if not l.startswith("#")}


def surface(rdir, k):
    h = rd(rdir, "H", k)[J]; z = rd(rdir, "Z", k)[J]
    try:
        hs = rd(rdir, "Hs", k)[J]
    except OSError:
        hs = np.zeros_like(h)
    return np.where(h + hs > 0.01, z + h + hs, np.nan)


# --- 1. 縦断図(4 ケース × [地形と陸上の流れ / 湖面]) ---
# 湖面の変化は ±数 m で、全体(−45〜90 m)の縦軸では見えないので右の図に分ける。右の縦軸は全ケースの湖面の
# 極値が入るように決める(B0 の汀線の土砂柱は約 3 m)
lake_ext = []
for rdir, _, _, _, _ in CASES:
    tm = times(rdir); z0 = rd(rdir, "Z", 0)[J]
    for k in (2, 3, 4, 5, 6, 8, 12, 24):
        if k in tm:
            s = np.where(z0 < 0, surface(rdir, k), np.nan)
            lake_ext += [np.nanmin(s), np.nanmax(s)]
ylo, yhi = min(-3.0, np.nanmin(lake_ext) - 0.3), max(3.0, np.nanmax(lake_ext) + 0.3)
fig, axes = plt.subplots(len(CASES), 2, figsize=(13, 3.2 * len(CASES)))
for (rdir, lab, col, _, _), (ax0, ax1) in zip(CASES, axes):
    tm = times(rdir)
    z0 = rd(rdir, "Z", 0)[J]
    ax0.plot(x, z0, "k-", lw=1, label=T("初期の地形 z0", "z0"))
    for k in (2, 3, 4, 5, 6, 8, 12, 24):
        if k not in tm:
            continue
        s = surface(rdir, k)
        ax0.plot(x, np.where(z0 >= 0, s, np.nan), lw=1, label="t = %.0f s" % tm[k])
        ax1.plot(x, np.where(z0 < 0, s, np.nan), lw=1, label="t = %.0f s" % tm[k])
    ax0.plot(x, rd(rdir, "Z", 24)[J], "k--", lw=1, label=T("t = 120 s の地形 z", "z (t = 120 s)"))
    ax0.axhline(0.0, color="#2a78d6", lw=0.6, ls=":")
    ax0.set_ylim(-45, 90); ax0.set_ylabel(T("標高 (m)", "elevation (m)")); ax0.grid()
    ax0.set_title(lab + T("(左: 地形と陸上の流れの表面、点線 = 湖の水位)", " (left: terrain and surface of the flow on land; dotted = lake level)"), fontsize=9)
    ax1.set_ylim(ylo, yhi); ax1.set_xlim(180, 600); ax1.set_ylabel(T("湖面 z + h + hs (m)", "lake surface z + h + hs (m)")); ax1.grid()
axes[0][0].legend(fontsize=7, ncol=3); axes[-1][0].set_xlabel("x (m)"); axes[-1][1].set_xlabel("x (m)")
plt.tight_layout(); plt.savefig(OUT + "profiles.png", dpi=100); plt.close()

# --- 2. 湖内プローブの水面時系列 ---
fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
for ax, n in zip(axes, (3, 4, 5)):
    for rdir, lab, col, ls, lw in CASES:
        f = "%s/probes/probe%04d.csv" % (rdir, n)
        xx = float(open(f).readlines()[1].split(",")[1])
        d = np.loadtxt(f, delimiter=",", comments="#")
        ax.plot(d[:, 0] * 3600, d[:, 2] + d[:, 3] + d[:, 9], color=col, lw=1.2, label=lab)
    ax.set_ylabel(T("水面 (m)\nx = %.0f m", "surface (m)\nx = %.0f m") % xx); ax.grid()
axes[0].legend(fontsize=8); axes[-1].set_xlabel(T("時刻 t (s)", "t (s)"))
axes[0].set_title(T("湖内プローブの水面(y = 97.5 m)", "lake free surface at probes (y = 97.5 m)"))
plt.tight_layout(); plt.savefig(OUT + "probes.png", dpi=100); plt.close()

# --- 3. 地形変化の比較(重なる線が見えるように線種を変え、A を下に太く描く) ---
fig, ax = plt.subplots(figsize=(10, 4))
for rdir, lab, col, ls, lw in CASES:
    dz = rd(rdir, "Z", 24)[J] - rd(rdir, "Z", 0)[J]
    ax.plot(x, dz, color=col, lw=lw, ls=ls, label=lab)
ax.axvline(200, color="k", lw=0.5); ax.axvline(300, color="k", lw=0.5)
ax.text(200, ax.get_ylim()[1] * 0.9, T(" 汀線", " shoreline"), fontsize=8)
ax.text(300, ax.get_ylim()[1] * 0.9, T(" 湖底の平坦部", " basin floor"), fontsize=8)
ax.set_xlabel("x (m)"); ax.set_ylabel(T("t = 120 s の地形変化 z − z0 (m)", "bed change z − z0 at t = 120 s (m)")); ax.grid()
ax.legend(fontsize=8)
plt.tight_layout(); plt.savefig(OUT + "deposit.png", dpi=100); plt.close()

# --- 数表(README 用。日本語版のときだけ) ---
if not EN:
    A = DX * DX
    for rdir, lab, col, ls, lw in CASES:
        z0 = rd(rdir, "Z", 0); dz = rd(rdir, "Z", 24) - z0
        bands = [np.clip(dz[:, (x >= a) & (x < b)], 0, None).sum() * A for a, b in ((200, 275), (275, 350))]
        reach = x[np.where(dz > 0.01)[1]].max()
        ex = []
        for n in (2, 3, 4, 5):
            f = "%s/probes/probe%04d.csv" % (rdir, n)
            d = np.loadtxt(f, delimiter=",", comments="#"); s = d[:, 2] + d[:, 3] + d[:, 9]; t = d[:, 0] * 3600
            ex.append("%+.2f@%.0fs/%+.2f" % (s.max(), t[s.argmax()], s.min()))
        print("%-10s shore(200-275) %6.0f  floor(275-350) %6.0f m3  reach %.0f m | x=212 %s | 298 %s | 398 %s | 548 %s"
              % (rdir, bands[0], bands[1], reach, *ex))

# --- 4. 非静水圧との比較(A と C) ---
NH = [("result_A", "result_A_nh", T("A: 岩屑なだれ", "A: rockslide"), "#2a78d6"),
      ("result_C", "result_C_nh", T("C: 海底地滑り", "C: submarine slide"), "#2e9e5b")]
if all(os.path.isdir(d) for _, d, _, _ in NH):
    fig, axes = plt.subplots(3, 2, figsize=(13, 10))
    for col_i, (rh, rn, lab, col) in enumerate(NH):
        ax = axes[0][col_i]
        tm = times(rh); z0 = rd(rh, "Z", 0)[J]
        for k, cc in ((2, "#2a78d6"), (4, "#eb6834")):
            if k not in tm:
                continue
            for rdir, lw, ls in ((rh, 1.0, "--"), (rn, 1.5, "-")):
                h = rd(rdir, "H", k)[J]; z = rd(rdir, "Z", k)[J]
                s = np.where(h > 0.01, z + h, np.nan)
                ax.plot(x, np.where(z0 < 0, s, np.nan), lw=lw, ls=ls, color=cc,
                        label=(T("静水圧 ", "hydrostatic ") if rdir == rh else T("非静水圧 + 底面の加速度 ", "NH + bottom acc. "))
                        + "t = %.0f s" % tm[k])
        ax.set_xlim(180, 600); ax.set_ylim(-2.5, 2.5); ax.grid()
        ax.set_title(lab + T(": 湖面(破線 = 静水圧、実線 = 非静水圧)", ": lake surface (dashed = hydrostatic, solid = NH)"), fontsize=10)
        ax.set_ylabel(T("水面 (m)", "surface (m)")); ax.legend(fontsize=7, ncol=2)
        for row, n in ((1, 3), (2, 4)):
            ax = axes[row][col_i]
            for rdir, cl, lw, cc in ((rh, T("静水圧", "hydrostatic"), 1.0, "#8a8983"),
                                     (rn + "0", T("非静水圧、分散だけ(f_nh_bottom=0)", "non-hydrostatic, dispersion only (f_nh_bottom=0)"), 1.0, "#eb6834"),
                                     (rn, T("非静水圧 + 底面の加速度(f_nh_bottom=1)", "non-hydrostatic + bottom acceleration (f_nh_bottom=1)"), 1.3, col)):
                if not os.path.isdir(rdir):
                    continue
                f = "%s/probes/probe%04d.csv" % (rdir, n)
                xx = float(open(f).readlines()[1].split(",")[1])
                d = np.loadtxt(f, delimiter=",", comments="#")
                ax.plot(d[:, 0] * 3600, d[:, 2] + d[:, 3] + d[:, 9], color=cc, lw=lw, label=cl)
            ax.set_ylabel(T("水面 (m)\nx = %.0f m", "surface (m)\nx = %.0f m") % xx); ax.grid()
            if row == 2:
                ax.set_xlabel(T("時刻 t (s)", "t (s)"))
        axes[1][col_i].legend(fontsize=7)
    plt.tight_layout(); plt.savefig(OUT + "nonhydro.png", dpi=100); plt.close()
    if not EN:
        print("| ケース | x=212 m | x=298 m | x=398 m | x=548 m | 水中の底層: 停止 / 移動中 (m³) |")
        print("|---|---|---|---|---|---|")
        for rh, rn, lab, col in NH:
            for rdir, cl in ((rh, "静水圧"), (rn + "0", "非静水圧(加速度項なし)"), (rn, "非静水圧 + 加速度項")):
                if not os.path.isdir(rdir):
                    continue
                ex = []
                for n in (2, 3, 4, 5):
                    d = np.loadtxt("%s/probes/probe%04d.csv" % (rdir, n), delimiter=",", comments="#")
                    s = d[:, 2] + d[:, 3] + d[:, 9]; t = d[:, 0] * 3600
                    ex.append("%+.2f@%.0fs / %+.2f" % (s.max(), t[s.argmax()], s.min()))
                mv = ""
                # 画面出力の保存名: README の手順の Screen_<設定名>.log か、旧い Screen_<結果名>.log
                stem = {"result_A": "rockslide", "result_C": "submarine"}[rh] + rdir[len(rh):]
                for cand in ("Screen_%s.log" % stem, rdir.replace("result_", "Screen_") + ".log"):
                    if os.path.exists(cand):
                        for l in open(cand):
                            if "still moving" in l:
                                parts = l.split(); mv = "%s / %s" % (parts[parts.index("stopped") + 1], parts[-2])
                        break
                print("| %s %s | %s | %s |" % (lab, cl, " | ".join(ex), mv))
print(" ".join(OUT + f for f in ("profiles.png", "probes.png", "deposit.png", "nonhydro.png")))
