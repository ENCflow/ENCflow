#!/usr/bin/env python3
"""debris_fan_flume の図と数表(事前に make run で全ケースを計算しておく)。

  figs/setup.png     水路と氾濫台の縦断・平面、材料の粒度(入力だけ。計算結果を使わない)
  figs/outlet.png    水路の出口の流量と土砂濃度の時間変化(形成の段)と、論文の図 1・2 の読み取り
  figs/fan.png       形成の段の終わりの堆積厚(混合粒径・単一粒径・格子 2.5 cm)と、論文の図 8 の読み取り
  figs/erosion.png   侵食の段(清水 300 cc/s)の 0・2・10 分の堆積厚(掃流砂だけの混合粒径・単一粒径、
                     土石流の式を有効にしたままの混合粒径)
  figs/armour.png    侵食の段の時間変化(氾濫台の侵食量・基盤の露出・表層の平均粒径)と 10 分後の表層の平均粒径
  figs/select.png    土石流の式の侵食を動ける粒径階に限る f_dbsel の侵食の段(10 分後の堆積厚と表層の平均粒径)と、
                     論文の図 10 の読み取り(厚さの等値線の中の面積、厚さ 2 cm より上の体積)との比較
数表(標準出力): 形成と侵食の指標。
引数 en で英語ラベル版を en/figs/ に描く(データと描画処理は共通)。計算結果がなければ setup.png だけを描く。

論文(高橋・中川・山敷 1991)の実験と計算の値は、公開版の図(スキャン)からの読み取りで、概略。数表はない。
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import make_init as M

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)

CSTAR = 1.0 - M.LAMBDA
TH_EDGE = 0.005                  # 堆積の縁とみなす厚さ (m)(論文の図の「0」の線に当てる)
TH_BARE = 0.002                  # 基盤の露出とみなす厚さ (m)
TH_FAN = 0.01                    # 扇状地の本体とみなす厚さ (m)
COL = {"form": "#1f5f8b", "form_single": "#c0392b", "form_dx25": "#2b8a3e", "form_sel1": "#2b8a3e", "form_sel2": "#e8590c",
       "ero": "#1f5f8b", "ero_single": "#c0392b", "ero_debris": "#7b2d8e", "ero_debris_single": "#d08c00",
       "ero_sel1": "#2b8a3e", "ero_sel2": "#e8590c"}

# ---- 論文の図からの読み取り(概略)
# 図 1: 水路の下流端の流量。先端の到達を t = 0 とする。実験 6 回の点の範囲と、計算の線(混合砂・均一砂)
PAPER_Q_EXP = [(0.0, 12.0, 1.2, 3.4)]                         # (t1, t2, 下限, 上限) (s, ℓ/s)
PAPER_Q_MIX = [(0.0, 2.4), (4.0, 1.9), (8.0, 1.7), (12.0, 1.6), (16.0, 0.9), (24.0, 0.9), (30.0, 0.3)]
PAPER_Q_UNI = [(0.0, 1.6), (4.0, 1.8), (8.0, 1.8), (12.0, 1.6), (16.0, 0.9), (24.0, 0.6), (30.0, 0.3)]
PAPER_C_EXP = (0.40, 0.50)                                    # 図 2: 土砂濃度(実験の点の範囲)
# 図 8(最終形状。実験 Run B と計算): 厚さ 0 の線の下流端までの距離・最大の半幅・最大の厚さ
PAPER_FAN = {"exp": dict(length=0.85, halfwidth=0.38, thick=0.055),
             "cal": dict(length=1.00, halfwidth=0.40, thick=0.055)}
# 図 10(侵食の実験): 10 分後の厚さ 0 の線の下流端
PAPER_ERO_LEN = 1.15
# 図 10(侵食の実験。0 分と 10 分の厚さの等値線): 厚さ 0・1・2・3・4・5 cm の線の中の面積 (cm²)。等値線の幅と長さから
# 概算した値で、±15 % 程度の不確かさがある。厚さ 2 cm より上の体積は、この面積を厚さについて台形で積分した値 (ℓ)
PAPER_ERO_LEVELS = (0, 1, 2, 3, 4, 5)
PAPER_ERO_AREA = {0: (6100, 4200, 2900, 2200, 1400, 440), 10: (10500, 5700, 3100, 1500, 700, 0)}
PAPER_ERO_V2 = {0: 5.5, 10: 3.6}


def lab(name):
    return {"form": T("混合粒径(5 階)", "mixed sizes (5 classes)"),
            "form_single": T("単一粒径 3.04 mm", "single size 3.04 mm"),
            "form_dx25": T("混合粒径、格子 2.5 cm", "mixed sizes, 2.5 cm grid"),
            "form_sel1": T("混合粒径、f_dbsel = 1", "mixed sizes, f_dbsel = 1"),
            "form_sel2": T("混合粒径、f_dbsel = 2", "mixed sizes, f_dbsel = 2"),
            "ero": T("混合粒径、掃流砂だけ", "mixed sizes, bed load only"),
            "ero_single": T("単一粒径、掃流砂だけ", "single size, bed load only"),
            "ero_debris": T("混合粒径、土石流の式も有効", "mixed sizes, debris-flow laws on"),
            "ero_debris_single": T("単一粒径、土石流の式も有効", "single size, debris-flow laws on"),
            "ero_sel1": T("混合粒径、土石流の式も有効、f_dbsel = 1", "mixed sizes, debris-flow laws on, f_dbsel = 1"),
            "ero_sel2": T("混合粒径、土石流の式も有効、f_dbsel = 2", "mixed sizes, debris-flow laws on, f_dbsel = 2")}[name]


class Case:
    def __init__(self, name):
        self.name = name
        self.gname, self.rep = M.CASES[name]
        self.dx = M.GRIDS[self.gname]
        self.nx, self.ny, xc, yc = M.grid(self.dx)
        self.xc, self.yc = np.array(xc), np.array(yc)
        self.rdir = f"result_{name}"
        self.ok = os.path.exists(f"{self.rdir}/Z9998.bil")
        self.io = int(round(M.XO / self.dx))                  # 氾濫台の最初の列(0 始まり)
        self.frames = []
        if self.ok:
            for ln in open(f"{self.rdir}/FILENUMBER.csv"):
                if ln.startswith("#"):
                    continue
                a = ln.split(",")
                if int(a[0]) < 9000:
                    self.frames.append((int(a[0]), float(a[2])))
        zb = np.array(M.fields(self.dx)[0])
        self.zb = zb[:, self.io:]                             # 氾濫台の面(固定床)
        self.xb = self.xc[self.io:] - M.XO                    # 出口からの距離
        self.mixed = "f_bedmix" not in self.rep or self.rep["f_bedmix"] is not None

    def bil(self, name):
        return np.fromfile(f"{self.rdir}/{name}.bil", dtype="<f4").reshape(self.ny, self.nx).astype(float)

    def thick(self, k):
        """氾濫台の上の堆積厚 (m)(フレーム k)。"""
        return self.bil(f"Z{k:04d}")[:, self.io:] - self.zb

    def board(self, key, k):
        return self.bil(f"{key}{k:04d}")[:, self.io:]

    def nearest(self, t):
        return min(self.frames, key=lambda f: abs(f[1] - t))[0]

    def probes(self):
        """水路の出口の時系列: (t, 流量 Q_T m3/s, 土砂濃度 C)。計測点は水路の幅のセル。"""
        rows = []
        n = 1
        while os.path.exists(f"{self.rdir}/probes/probe{n:04d}.csv"):
            r = []
            for ln in open(f"{self.rdir}/probes/probe{n:04d}.csv"):
                if ln.startswith("#") or not ln.strip():
                    continue
                r.append([float(v) for v in ln.split(",")])
            rows.append(np.array(r))
            n += 1
        t = rows[0][:, 1] * 60.0
        q = sum((r[:, 3] + r[:, 9]) * r[:, 4] for r in rows) * self.dx        # (h + hs) u Δy
        qs = sum(r[:, 9] * r[:, 4] for r in rows) * self.dx
        c = np.where(q > 1.0e-9, qs / np.maximum(q, 1.0e-30), np.nan)
        return t, q, c


def fan_metrics(c, th):
    """堆積の指標: 体積 (m3。かさ)、最大の厚さ、厚さ TH_EDGE の線の下流端までの距離と最大の半幅。"""
    a = c.dx * c.dx
    on = th > TH_EDGE
    length = float(c.xb[on.any(axis=0)].max() + c.dx / 2) if on.any() else 0.0
    half = float(np.abs(c.yc[on.any(axis=1)]).max() + c.dx / 2) if on.any() else 0.0
    return dict(vol=float(np.clip(th, 0.0, None).sum() * a), thick=float(th.max()), length=length, halfwidth=half)


def movavg(t, v, w):
    n = max(int(round(w / (t[1] - t[0]))), 1)
    k = np.ones(n) / n
    return np.convolve(v, k, mode="same")


# ---------------------------------------------------------------- 図
def fig_setup():
    fig, axs = plt.subplots(1, 3, figsize=(15.5, 4.3), gridspec_kw=dict(width_ratios=[1.5, 1.0, 1.0]))
    ax = axs[0]
    dx = M.GRIDS["dx5"]
    nx, ny, xc, yc = M.grid(dx)
    z, sd, mask = M.fields(dx)
    jf = M.flume_rows(dx)[0] - 1
    xc = np.array(xc)
    zs = np.array(z[jf])
    zb = zs - np.array(sd[jf])
    ax.plot(xc, zb, color="#555555", lw=1.2, label=T("固定床(水路の床・氾濫台)", "rigid floor (flume bed, board)"))
    ax.fill_between(xc, zb, zs, where=np.array(sd[jf]) > 0, color="#c8a165", label=T("材料(厚さ 10 cm、飽和)", "sediment (10 cm thick, saturated)"))
    ax.annotate(T("給水 600 cc/s × 20 s\n(侵食の段は清水 300 cc/s × 10 分)", "water 600 cc/s for 20 s\n(erosion stage: clear water 300 cc/s, 10 min)"),
                xy=(0.05, zs[0]), xytext=(0.3, 0.9), fontsize=9, arrowprops=dict(arrowstyle="->", color="#1f5f8b"), color="#1f5f8b")
    ax.text(4.3, 1.75, T("水路: 幅 10 cm、勾配 18°", "flume: 10 cm wide, 18°"), fontsize=9)
    ax.text(M.XO + 0.1, M.ZO + 0.25, T("氾濫台 5°", "board 5°"), fontsize=9)
    ax.axvline(M.XO, color="#999999", lw=0.8, ls=":")
    ax.set_xlabel(T("x (m)(水平距離)", "x (m) (horizontal)"))
    ax.set_ylabel(T("高さ (m)", "elevation (m)"))
    ax.set_title(T("(a) 縦断(水路の軸)", "(a) Long profile (flume axis)"), fontsize=10)
    ax.legend(fontsize=8, loc="upper right")
    ax = axs[1]
    m = np.array(mask)
    ax.pcolormesh(xc, np.array(yc), np.where(m > 0, 1.0, np.nan), cmap="Blues", vmin=0, vmax=3, shading="nearest")
    ax.set_xlim(M.XO - 1.0, M.LX)
    ax.set_ylim(M.LY / 2, -M.LY / 2)
    ax.set_aspect("equal")
    ax.axvline(M.XO, color="#999999", lw=0.8, ls=":")
    ax.text(M.XO - 0.95, -0.12, T("水路(幅 2 セル)", "flume (2 cells wide)"), fontsize=8)
    ax.text(M.XO + 0.3, -0.55, T("氾濫台(三方が自由流出)", "board (free outflow on three sides)"), fontsize=8)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title(T("(b) 平面(格子 5 cm。水路の出口のまわり)", "(b) Plan (5 cm grid, around the flume outlet)"), fontsize=10)
    ax = axs[2]
    d = np.array(M.D_CLASS) * 1e3
    f = np.array(M.F_CLASS)
    cum = np.cumsum(f)
    # 粒径階の境界(隣り合う粒径の幾何平均)で階段状に描く
    edges = np.concatenate([[d[0] / 2.2], np.sqrt(d[:-1] * d[1:]), [d[-1] * 1.45]])
    xs, ys = [edges[0]], [0.0]
    for k in range(len(d)):
        xs += [edges[k], edges[k + 1]]
        ys += [ys[-1], cum[k]]
    ax.plot(xs, np.array(ys) * 100, color="#1f5f8b", lw=1.5, label=T("計算の 5 粒径階", "the five classes of the runs"))
    ax.plot(d, (cum - f / 2) * 100, "o", color="#1f5f8b", ms=5)
    ax.axvline(M.D_MEAN * 1e3, color="#c0392b", lw=1.0, ls="--", label=T("平均粒径 3.04 mm(単一粒径の計算)", "mean 3.04 mm (single-size runs)"))
    ax.set_xscale("log")
    ax.set_xlim(0.05, 20)
    ax.set_ylim(0, 100)
    ax.set_xlabel(T("粒径 (mm)", "grain size (mm)"))
    ax.set_ylabel(T("通過質量百分率 (%)", "percent finer (%)"))
    ax.set_title(T("(c) 材料の粒度(粒度曲線の段からの読み取り)", "(c) Grain sizes (read from the published curve)"), fontsize=10)
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(alpha=0.3, which="both")
    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/setup.png", dpi=130, bbox_inches="tight")
    plt.close(fig)


def fig_outlet(cases):
    fig, axs = plt.subplots(1, 2, figsize=(12.5, 4.2))
    ax = axs[0]
    for t1, t2, lo, hi in PAPER_Q_EXP:
        ax.fill_between([t1, t2], lo, hi, color="#bbbbbb", alpha=0.5, label=T("実験 6 回の範囲(図 1 の読み取り)", "range of six experiments (read from Fig. 1)"))
    ax.plot(*zip(*PAPER_Q_MIX), color="k", lw=1.0, ls="-", label=T("論文の計算(混合砂。粒径選別あり)", "paper's computation (mixture, with sorting)"))
    ax.plot(*zip(*PAPER_Q_UNI), color="k", lw=1.0, ls="--", label=T("論文の計算(均一砂)", "paper's computation (uniform)"))
    for c in cases:
        t, q, cc = c.probes()
        t0 = t[np.argmax(q > 1.0e-5)]
        ax.plot(t - t0, movavg(t, q, 2.0) * 1e3, color=COL[c.name], lw=1.6, label=lab(c.name) + T("(2 秒平均)", " (2 s mean)"))
        if c.name == "form":
            ax.plot(t - t0, q * 1e3, color=COL[c.name], lw=0.4, alpha=0.5)
    ax.axhline(M.Q_FORM * 1e3, color="#1f5f8b", lw=0.8, ls=":")
    ax.text(27, M.Q_FORM * 1e3 + 0.08, T("給水 0.6 ℓ/s", "water supply 0.6 L/s"), fontsize=8, color="#1f5f8b")
    ax.set_xlim(-2, 32)
    ax.set_ylim(0, 6)
    ax.set_xlabel(T("先端が出口に着いてからの時間 (s)", "time after the front reaches the outlet (s)"))
    ax.set_ylabel(T("流量(水 + 土砂)(ℓ/s)", "discharge, water + sediment (L/s)"))
    ax.set_title(T("(a) 水路の出口の流量", "(a) Discharge at the flume outlet"), fontsize=10)
    ax.legend(fontsize=7.5, loc="upper right")
    ax.grid(alpha=0.3)
    ax = axs[1]
    ax.axhspan(*PAPER_C_EXP, color="#bbbbbb", alpha=0.5, label=T("実験の範囲(図 2 の読み取り)", "range of the experiments (read from Fig. 2)"))
    for c in cases:
        t, q, cc = c.probes()
        t0 = t[np.argmax(q > 1.0e-5)]
        qs = np.where(np.isnan(cc), 0.0, cc) * q
        cm = movavg(t, qs, 2.0) / np.maximum(movavg(t, q, 2.0), 1.0e-12)
        ok = movavg(t, q, 2.0) > 2.0e-5
        ax.plot((t - t0)[ok], cm[ok], color=COL[c.name], lw=1.6, label=lab(c.name))
    ax.set_xlim(-2, 32)
    ax.set_ylim(0, 0.7)
    ax.set_xlabel(T("先端が出口に着いてからの時間 (s)", "time after the front reaches the outlet (s)"))
    ax.set_ylabel(T("土砂の体積濃度", "volume concentration of solids"))
    ax.set_title(T("(b) 水路の出口の土砂濃度(流量で重みづけた 2 秒平均)", "(b) Solids concentration at the outlet (discharge-weighted 2 s mean)"), fontsize=10)
    ax.legend(fontsize=8, loc="lower right")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/outlet.png", dpi=130, bbox_inches="tight")
    plt.close(fig)


LEVELS = (0.005, 0.02, 0.04, 0.06, 0.08, 0.10)


def draw_thick(ax, c, th, title, ref=None, vmax=0.10):
    X, Y = np.meshgrid(c.xb * 100, c.yc * 100)
    im = ax.pcolormesh(X, Y, np.where(th > 0.001, th * 100, np.nan), cmap="YlOrBr", vmin=0, vmax=vmax * 100, shading="nearest")
    ax.contour(X, Y, th, levels=LEVELS, colors="k", linewidths=0.5)
    if ref:
        ax.plot([ref["length"] * 100] * 2, [-8, 8], color="#1f5f8b", lw=1.5)
        ax.plot([20, 60], [ref["halfwidth"] * 100] * 2, color="#1f5f8b", lw=1.5)
        ax.plot([20, 60], [-ref["halfwidth"] * 100] * 2, color="#1f5f8b", lw=1.5)
    ax.set_xlim(0, 170)
    ax.set_ylim(70, -70)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=9)
    return im


def fig_fan(cases):
    fig, axs = plt.subplots(1, len(cases) + 1, figsize=(4.3 * (len(cases) + 1), 4.0))
    for ax, c in zip(axs, cases):
        th = c.thick(9998)
        m = fan_metrics(c, th)
        im = draw_thick(ax, c, th, lab(c.name), ref=PAPER_FAN["exp"])
        ax.text(0.97, 0.04, T("最大 %.1f cm\n長さ %.0f cm\n半幅 %.0f cm", "max %.1f cm\nlength %.0f cm\nhalf-width %.0f cm")
                % (m["thick"] * 100, m["length"] * 100, m["halfwidth"] * 100), transform=ax.transAxes, fontsize=8, ha="right", va="bottom")
        ax.set_xlabel(T("出口からの距離 (cm)", "distance from the outlet (cm)"))
    axs[0].set_ylabel("y (cm)")
    fig.colorbar(im, ax=axs[:-1], shrink=0.8, label=T("堆積厚 (cm)。等値線 0.5・2・4・6・8 cm", "deposit thickness (cm); contours 0.5, 2, 4, 6, 8 cm"))
    ax = axs[-1]
    for c in cases:
        th = c.thick(9998)
        j = np.argsort(np.abs(c.yc))[:2]
        ax.plot(c.xb * 100, th[j].mean(axis=0) * 100, color=COL[c.name], lw=1.5, label=lab(c.name))
    ax.axvline(PAPER_FAN["exp"]["length"] * 100, color="#1f5f8b", lw=1.5)
    ax.axhline(PAPER_FAN["exp"]["thick"] * 100, color="#1f5f8b", lw=1.0, ls="--")
    ax.text(88, 5.8, T("実験(図 8 の読み取り):\n縁 85 cm、最大 5〜6 cm", "experiment (read from Fig. 8):\nedge 85 cm, max 5-6 cm"), fontsize=8, color="#1f5f8b")
    ax.set_xlim(0, 170)
    ax.set_ylim(0, 10)
    ax.set_xlabel(T("出口からの距離 (cm)", "distance from the outlet (cm)"))
    ax.set_ylabel(T("軸の上の堆積厚 (cm)", "thickness on the axis (cm)"))
    ax.set_title(T("軸に沿う厚さ", "Thickness along the axis"), fontsize=9)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.suptitle(T("形成の段の終わり(40 s)の堆積厚。青い線は実験の縁と半幅(論文の図 8 の読み取り)",
                   "Deposit thickness at the end of the formation stage (40 s). Blue: edge and half-width of the experiment (read from Fig. 8)"), fontsize=10)
    fig.savefig(f"{FIGDIR}/fan.png", dpi=130, bbox_inches="tight")
    plt.close(fig)


def fig_erosion(cases, times=(0.0, 120.0, 600.0)):
    fig, axs = plt.subplots(len(cases), len(times), figsize=(4.2 * len(times), 3.3 * len(cases)), squeeze=False)
    for r, c in enumerate(cases):
        for k, tt in enumerate(times):
            ax = axs[r][k]
            fr = c.nearest(tt)
            th = c.thick(fr)
            im = draw_thick(ax, c, th, lab(c.name) + T("、%g 分", ", %g min") % (tt / 60.0), vmax=0.12)
            if r == len(cases) - 1:
                ax.set_xlabel(T("出口からの距離 (cm)", "distance from the outlet (cm)"))
            if k == 0:
                ax.set_ylabel("y (cm)")
    fig.colorbar(im, ax=axs, shrink=0.6, label=T("堆積厚 (cm)。等値線 0.5・2・4・6・8・10 cm", "deposit thickness (cm); contours 0.5, 2, 4, 6, 8, 10 cm"))
    fig.suptitle(T("侵食の段(清水 300 cc/s)の堆積厚", "Deposit thickness in the erosion stage (clear water, 300 cc/s)"), fontsize=10)
    fig.savefig(f"{FIGDIR}/erosion.png", dpi=130, bbox_inches="tight")
    plt.close(fig)


def ero_series(c):
    """侵食の段の時系列: 時刻 (分)、氾濫台で初めより下がった体積 (ℓ)、上がった体積 (ℓ)、
    初めに TH_FAN 以上あったセルのうち TH_BARE を切った数、水路に残る土砂 (ℓ)、表層の平均粒径 (mm) を
    侵食された所(初めより 2 mm 以上下がり、土砂が残るセル)と、扇状地の外に新しく積もった所(初めの厚さが
    TH_EDGE 未満のセル)で。"""
    a = c.dx * c.dx
    th0 = c.thick(0)
    body = th0 > TH_FAN
    out = []
    for k, t in c.frames:
        th = c.thick(k)
        d = th - th0
        sdf = c.bil(f"Sd{k:04d}")[np.abs(c.yc) < M.W_FLUME / 2, :c.io]      # 水路の幅のセルだけ
        dm_e = dm_n = np.nan
        if c.mixed:
            dmb = c.board("Dm", k)
            w = (d < -0.002) & (th > TH_BARE)
            dm_e = float(dmb[w].mean() * 1e3) if w.any() else np.nan
            w = (th0 < TH_EDGE) & (th > TH_BARE)
            dm_n = float(dmb[w].mean() * 1e3) if w.any() else np.nan
        out.append((t / 60.0, -d[d < 0].sum() * a * 1e3, d[d > 0].sum() * a * 1e3,
                    int((body & (th < TH_BARE)).sum()), np.clip(sdf, 0, None).sum() * a * 1e3, dm_e, dm_n))
    return np.array(out), int(body.sum())


def fig_armour(cases):
    fig, axs = plt.subplots(1, 4, figsize=(17.5, 4.0))
    for c in cases:
        s, nbody = ero_series(c)
        axs[0].plot(s[:, 0], s[:, 1], color=COL[c.name], lw=1.6, label=lab(c.name))
        axs[1].plot(s[:, 0], s[:, 3] * c.dx * c.dx * 1e4, color=COL[c.name], lw=1.6, label=lab(c.name))
        if c.mixed:
            axs[2].plot(s[:, 0], s[:, 5], color=COL[c.name], lw=1.6, label=lab(c.name) + T("、侵食された所", ", eroded cells"))
            axs[2].plot(s[:, 0], s[:, 6], color=COL[c.name], lw=1.2, ls="--", label=lab(c.name) + T("、外に新しく積もった所", ", new deposit outside the fan"))
    axs[0].set_ylabel(T("氾濫台で侵食された体積 (ℓ。かさ)", "volume eroded on the board (L, bulk)"))
    axs[0].set_title(T("(a) 扇状地の侵食量", "(a) Erosion of the fan"), fontsize=10)
    axs[1].set_ylabel(T("基盤が露出した面積 (cm²)", "area stripped to the board (cm²)"))
    axs[1].set_title(T("(b) 基盤の露出(初めの厚さ 1 cm 以上が 2 mm 未満に)", "(b) Stripped area (from ≥ 1 cm to < 2 mm)"), fontsize=10)
    axs[2].axhline(M.D_MEAN * 1e3, color="#999999", lw=0.8, ls="--")
    axs[2].set_ylabel(T("表層(交換層)の平均粒径 (mm)", "mean grain size of the surface layer (mm)"))
    axs[2].set_title(T("(c) 表層の平均粒径(灰色 = 材料の 3.04 mm)", "(c) Surface mean grain size (grey: material)"), fontsize=10)
    for ax in axs[:3]:
        ax.set_xlabel(T("清水を流し始めてからの時間 (分)", "time after the clear water starts (min)"))
        ax.grid(alpha=0.3)
    axs[0].set_ylim(-0.2, 6.6)
    axs[0].legend(fontsize=7.5, loc="upper left")                # 色は (b)・(c) も同じ
    axs[2].plot([], [], color="k", lw=1.6, label=T("侵食された所", "eroded cells"))
    axs[2].plot([], [], color="k", lw=1.2, ls="--", label=T("扇状地の外に新しく積もった所", "new deposit outside the fan"))
    h, lb = axs[2].get_legend_handles_labels()
    axs[2].legend(h[-2:], lb[-2:], fontsize=7.5, loc="lower left")
    axs[2].set_ylim(0.8, 5.4)
    ax = axs[3]
    c = next((x for x in cases if x.name == "ero"), None)
    if c is not None:
        th = c.thick(9998)
        dm = c.board("Dm", 9998) * 1e3
        X, Y = np.meshgrid(c.xb * 100, c.yc * 100)
        im = ax.pcolormesh(X, Y, np.where(th > TH_BARE, dm, np.nan), cmap="viridis", vmin=2, vmax=7, shading="nearest")
        ax.contour(X, Y, th, levels=LEVELS, colors="w", linewidths=0.4)
        fig.colorbar(im, ax=ax, shrink=0.8, label="Dm (mm)")
        ax.set_xlim(0, 170)
        ax.set_ylim(70, -70)
        ax.set_aspect("equal")
        ax.set_xlabel(T("出口からの距離 (cm)", "distance from the outlet (cm)"))
        ax.set_title(T("(d) 10 分後の表層の平均粒径\n(混合粒径、掃流砂だけ)", "(d) Surface mean grain size after 10 min\n(mixed sizes, bed load only)"), fontsize=10)
    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/armour.png", dpi=130, bbox_inches="tight")
    plt.close(fig)


def contour_areas(c, th):
    """厚さ PAPER_ERO_LEVELS (cm) 以上の面積 (cm²。0 cm は堆積の縁 TH_EDGE)と、厚さ 2 cm より上の体積 (ℓ。かさ)。"""
    a = c.dx * c.dx
    areas = [float(((th >= k / 100.0) if k > 0 else (th > TH_EDGE)).sum() * a * 1e4) for k in PAPER_ERO_LEVELS]
    return areas, float(np.clip(th - 0.02, 0.0, None).sum() * a * 1e3)


def fig_select(cases):
    """f_dbsel の侵食の段: 上段 = 10 分後の堆積厚(粒径を選ばない・f_dbsel = 1・2)、下段 = 実験の図 10 の読み取りとの
    比較(厚さの等値線の中の面積の 10 分後と初めの比、厚さ 2 cm より上の体積の変化)と、10 分後の表層の平均粒径。"""
    by = {c.name: c for c in cases}
    top = [by[n] for n in ("ero_debris", "ero_sel1", "ero_sel2") if n in by]
    fig, axs = plt.subplots(2, 3, figsize=(15.0, 8.6))
    short = {"ero_debris": T("(a) 粒径を選ばない(f_dbsel = 0)", "(a) no selection (f_dbsel = 0)"),
             "ero_sel1": "(b) f_dbsel = 1", "ero_sel2": "(c) f_dbsel = 2"}
    for ax, c in zip(axs[0], top):
        im = draw_thick(ax, c, c.thick(9998), short[c.name] + T("、10 分後", ", after 10 min"), vmax=0.12)
        ax.set_xlabel(T("出口からの距離 (cm)", "distance from the outlet (cm)"))
    axs[0][0].set_ylabel("y (cm)")
    fig.colorbar(im, ax=list(axs[0]), shrink=0.8, label=T("堆積厚 (cm)。等値線 0.5〜10 cm", "thickness (cm); contours 0.5 to 10 cm"))
    # (d) 厚さの等値線の中の面積: 10 分後 / 初め
    ax = axs[1][0]
    lv = np.array(PAPER_ERO_LEVELS, dtype=float)
    e0, e1 = np.array(PAPER_ERO_AREA[0], dtype=float), np.array(PAPER_ERO_AREA[10], dtype=float)
    ax.plot(lv, e1 / e0, color="k", lw=2.0, marker="o", label=T("実験(図 10 の読み取り)", "experiment (read from Fig. 10)"))
    dv = [(T("実験", "experiment"), PAPER_ERO_V2[10] - PAPER_ERO_V2[0], "k")]
    for n in ("ero", "ero_debris", "ero_sel1", "ero_sel2"):
        if n not in by:
            continue
        c = by[n]
        a0, v0 = contour_areas(c, c.thick(0))
        a1, v1 = contour_areas(c, c.thick(9998))
        ax.plot(lv, np.array(a1) / np.maximum(np.array(a0), 1.0e-9), color=COL[n], lw=1.6, marker="s", ms=4, label=lab(n))
        dv.append((lab(n), v1 - v0, COL[n]))
    ax.axhline(1.0, color="#999999", lw=0.8, ls="--")
    ax.set_xlabel(T("厚さ (cm)", "thickness (cm)"))
    ax.set_ylabel(T("その厚さ以上の面積(10 分後 / 初め)", "area at least that thick (10 min / start)"))
    ax.set_ylim(0, 2.0)
    ax.set_title(T("(d) 厚さごとの面積の変化", "(d) Change of the area by thickness"), fontsize=10)
    ax.legend(fontsize=7.5, loc="upper right")
    ax.grid(alpha=0.3)
    # (e) 厚さ 2 cm より上の体積の変化
    ax = axs[1][1]
    xx = np.arange(len(dv))
    ax.bar(xx, [v for _, v, _ in dv], color=[col for _, _, col in dv])
    for x, (_, v, _) in zip(xx, dv):
        ax.text(x, v + (0.12 if v >= 0 else -0.12), "%+.1f" % v, ha="center", va="bottom" if v >= 0 else "top", fontsize=9)
    ax.axhline(0.0, color="k", lw=0.6)
    ax.set_xticks(xx)
    ax.set_xticklabels([T("実験", "experiment"), T("掃流砂\nだけ", "bed load\nonly"), T("選ばない\n(f_dbsel = 0)", "no selection\n(f_dbsel = 0)"),
                        "f_dbsel\n= 1", "f_dbsel\n= 2"][:len(dv)], fontsize=8.5)
    ax.set_ylabel(T("厚さ 2 cm より上の体積の変化 (ℓ。かさ)", "change of the volume above 2 cm (L, bulk)"))
    ax.set_ylim(-3.2, 4.8)
    ax.set_title(T("(e) 扇状地の厚い部分の体積の変化(10 分)", "(e) Change of the volume of the thick part (10 min)"), fontsize=10)
    ax.grid(alpha=0.3, axis="y")
    # (f) 10 分後の表層の平均粒径(f_dbsel = 1)
    ax = axs[1][2]
    c = by.get("ero_sel1")
    if c is not None:
        th = c.thick(9998)
        dm = c.board("Dm", 9998) * 1e3
        X, Y = np.meshgrid(c.xb * 100, c.yc * 100)
        im = ax.pcolormesh(X, Y, np.where(th > TH_BARE, dm, np.nan), cmap="viridis", vmin=2, vmax=7, shading="nearest")
        ax.contour(X, Y, th, levels=LEVELS, colors="w", linewidths=0.4)
        fig.colorbar(im, ax=ax, shrink=0.8, label="Dm (mm)")
        ax.set_xlim(0, 170)
        ax.set_ylim(70, -70)
        ax.set_aspect("equal")
        ax.set_xlabel(T("出口からの距離 (cm)", "distance from the outlet (cm)"))
        ax.set_title(T("(f) 10 分後の表層の平均粒径\n(f_dbsel = 1)", "(f) Surface mean grain size after 10 min\n(f_dbsel = 1)"), fontsize=10)
    fig.suptitle(T("侵食の段(土石流の式を有効にしたまま): 侵食を動ける粒径階に限る f_dbsel。上段は堆積厚",
                   "Erosion stage with the debris-flow laws on: erosion limited to the movable classes (f_dbsel). Top: deposit thickness"),
                 fontsize=10, y=0.90)
    fig.savefig(f"{FIGDIR}/select.png", dpi=130, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------- 数表
def table_form(cases):
    print("\n形成の段(40 s)。流量は先端が出口に着いてからの時間の平均、濃度は流量で重みづけた平均")
    print("ケース, 先端の到達 (s), Q 0-4 s, 4-8 s, 8-12 s (ℓ/s), 2 秒平均の最大 (ℓ/s), 濃度 0-12 s, 出口を通った土砂 (ℓ。固体), "
          "氾濫台の堆積 (ℓ。かさ), 最大の厚さ (cm), 長さ (cm), 半幅 (cm)")
    for c in cases:
        t, q, cc = c.probes()
        dt = t[1] - t[0]
        t0 = t[np.argmax(q > 1.0e-5)]
        qs = np.where(np.isnan(cc), 0.0, cc) * q

        def av(a, b):
            w = (t >= t0 + a) & (t < t0 + b)
            return q[w].mean() * 1e3

        w = (t >= t0) & (t < t0 + 12.0)
        m = fan_metrics(c, c.thick(9998))
        print(f"{c.name}, {t0:.1f}, {av(0, 4):.2f}, {av(4, 8):.2f}, {av(8, 12):.2f}, {movavg(t, q, 2.0).max() * 1e3:.2f}, "
              f"{qs[w].sum() / q[w].sum():.2f}, {qs.sum() * dt * 1e3:.1f}, {m['vol'] * 1e3:.1f}, {m['thick'] * 100:.1f}, "
              f"{m['length'] * 100:.0f}, {m['halfwidth'] * 100:.0f}")
    print("論文の図の読み取り(概略): 流量 実験 1.2〜3.4 ℓ/s(0〜12 s)、計算の最大 混合砂 2.4・均一砂 1.6〜1.8 ℓ/s、濃度 0.40〜0.50、"
          "扇状地 実験 長さ 85 cm・半幅 38 cm・最大 5〜6 cm、計算 長さ 100 cm")


def table_ero(cases):
    print("\n侵食の段(清水 300 cc/s)。体積はかさ (ℓ)")
    print("ケース, 時刻 (分), 氾濫台の侵食, 氾濫台の堆積, 基盤の露出 (セル/本体のセル), 水路に残る土砂, "
          "表層の平均粒径 (mm) 侵食された所・外に積もった所, 長さ (cm)")
    for c in cases:
        s, nbody = ero_series(c)
        for tt in (0.0, 2.0, 5.0, 10.0):
            r = s[np.argmin(np.abs(s[:, 0] - tt))]
            m = fan_metrics(c, c.thick(c.nearest(tt * 60.0)))
            print(f"{c.name}, {r[0]:.0f}, {r[1]:.2f}, {r[2]:.2f}, {int(r[3])}/{nbody}, {r[4]:.2f}, "
                  f"{'%.2f' % r[5] if not np.isnan(r[5]) else '-'}, {'%.2f' % r[6] if not np.isnan(r[6]) else '-'}, "
                  f"{m['length'] * 100:.0f}")


def table_select(cases):
    print("\n侵食の段と実験(論文の図 10 の読み取り。概略): 厚さ 0・1・2・3・4・5 cm 以上の面積 (cm²) と、厚さ 2 cm より上の体積 (ℓ。かさ)")
    for t in (0, 10):
        print(f"実験, {t}, " + ", ".join("%d" % v for v in PAPER_ERO_AREA[t]) + f", {PAPER_ERO_V2[t]:.1f}")
    for c in cases:
        for tt in (0.0, 10.0):
            a, v = contour_areas(c, c.thick(c.nearest(tt * 60.0)))
            print(f"{c.name}, {tt:.0f}, " + ", ".join("%d" % round(x) for x in a) + f", {v:.2f}")
        if c.mixed:
            th, th0 = c.thick(9998), c.thick(0)
            dm = c.board("Dm", 9998) * 1e3
            w = (th - th0 < -0.002) & (th > TH_BARE)
            if w.any():
                print(f"  {c.name}: 侵食された所の表層の平均粒径 {dm[w].mean():.2f} mm(最大 {dm[w].max():.2f} mm。{int(w.sum())} セル)")


def main():
    fig_setup()
    cases = {n: Case(n) for n in M.CASES}
    done = {n: c for n, c in cases.items() if c.ok}
    print("計算済み:", " ".join(done) if done else "なし(setup.png だけを描きました)")
    form = [done[n] for n in ("form", "form_single", "form_dx25") if n in done]
    if form:
        fig_outlet(form)
        fig_fan(form)
        table_form(form + [done[n] for n in ("form_sel1", "form_sel2") if n in done])
    ero = [done[n] for n in ("ero", "ero_single", "ero_debris", "ero_debris_single") if n in done]
    sel = [done[n] for n in ("ero_sel1", "ero_sel2") if n in done]
    if ero:
        fig_erosion([c for c in ero if c.name != "ero_debris_single"])
        fig_armour(ero + sel)
        table_ero(ero + sel)
    if sel and "ero_debris" in done:
        fig_select(ero + sel)
        table_select(ero + sel)


if __name__ == "__main__":
    main()
