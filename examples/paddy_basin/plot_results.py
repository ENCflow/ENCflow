#!/usr/bin/env python3
"""paddy_basin の図と数表(事前に make run で計算しておく)。

合成の傾斜地の流域(100 km²)で、出口のピーク流量が田んぼダムでどれだけ下がるか(モデル)を、田んぼダムの手引き
(農林水産省 2026)の概算式と、その元になった吉川(2022)の簡便法と比べる。

  figs/basin.png     流域(地形・河道の幅)と、水田面積率 10・20・40・60 % で水田にするセル
  figs/hydro.png     総雨量 250 mm の雨と 1 区画の流出(通常の落水口・田んぼダム)、出口の流量(水田面積率 20・60 %)
  figs/peakcut.png   出口のピークカット率と水田面積率(総雨量ごと): モデルと概算式 3 つ
数表(README の表)は標準出力に Markdown で出す。引数 en で英語ラベル版を en/figs/ に描く(データと描画処理は共通)。

ピークカット率 PC = 1 − Q_D / Q_N(Q_N・Q_D は全て通常の落水口・全て田んぼダムの出口のピーク流量)。概算式:
  (a) 手引きの積の形     PC = A_r × r × 0.6           (r: 区画のピークカット率、0.6: 非水田に対する水田のピーク流出割合)
  (b) 吉川(2022)の比の形 PC = A_r Q_P (1 − Q_PP) / (A_r Q_P + 1 − A_r)、Q_P = 0.7、Q_PP = 0.2
  (c) 比の形にモデルの 1 区画の値を入れたもの  Q_P = 区画の通常の落水口の流出のピーク / 雨のピーク、Q_PP = 1 − r
区画の値は、流域の計算の paddy.csv(全ての水田の落水口と畦畔の越流の合計を水田の面積で割った流出の強さ)から求める
(一様な雨・同じ装置なので、どの区画もほぼ同じ流出。片方向なので水田に外の水は入らない)。
"""
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_basin import NX, NY, DX, IC, AR_LEVELS, STORMS, FRAC, mononobe   # noqa: E402

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
matplotlib.rcParams["axes.spines.top"] = False
matplotlib.rcParams["axes.spines.right"] = False
os.makedirs(FIGDIR, exist_ok=True)

RUNS = "runs"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
C1, C2, C3, C4 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"   # dataviz の既定の分類色の順
QP_GUIDE = 0.6                       # 手引きの「非水田に対する水田のピーク流出割合」
QP_Y22, QPP_Y22 = 0.7, 0.2           # 吉川(2022)の 100 年確率 24 時間雨量の値
KIND = {"0": T("水田のタンクなし", "no paddy tanks"), "N": T("全て通常の落水口", "all normal outlets"),
        "D": T("全て田んぼダム", "all paddy-field dams"), "H": T("半分が田んぼダム", "half paddy-field dams")}


def case(total, ar, tag):
    return "R%d_A%d_%s" % (total, ar, tag)


def have(c):
    return os.path.isfile(os.path.join(RUNS, "result_%s" % c, "H0008.bil"))


def flux(c):
    """出口の 1 行上の測線の流量(時刻 h、Q m³/s)"""
    a = np.loadtxt(os.path.join(RUNS, "result_%s" % c, "fluxes", "flux0001.csv"), delimiter=",", comments="#")
    return a[:, 0], a[:, 2]


def peak(c):
    t, q = flux(c)
    k = int(np.argmax(q))
    return q[k], t[k]


def paddy(c):
    with open(os.path.join(RUNS, "result_%s" % c, "paddy.csv")) as f:
        head = f.readline().strip().split(",")
    a = np.loadtxt(os.path.join(RUNS, "result_%s" % c, "paddy.csv"), delimiter=",", skiprows=1)
    return {k: a[:, i] for i, k in enumerate(head)}


def plot_rate(c):
    """1 区画の流出の強さ (mm/h): 落水口の流出と畦畔の越流の合計を水田の面積で割る(記録の間の平均)。時刻 h"""
    p = paddy(c)
    t = np.concatenate([[0.0], p["time(s)"]])
    v = np.concatenate([[0.0], p["outflow(m3)"] + p["spill(m3)"]])
    a = p["area1(m2)"][-1] + p["area2(m2)"][-1]
    q = np.diff(v) / np.diff(t) / a * 3.6e6
    return 0.5 * (t[1:] + t[:-1]) / 3600.0, q, p["spill(m3)"][-1]


def plot_values(total, ar):
    """1 区画の値: 通常の落水口と田んぼダムの流出のピーク (mm/h)、r、Q_P(雨のピークに対する通常の落水口の流出)、
    田んぼダムの畦畔の越流 (m³)、出口のピークの時刻の区画のピークカット率 r_t = 1 − q_D(t_D) / q_N(t_N)
    (t_N・t_D は全て通常の落水口・全て田んぼダムの出口のピークの時刻)"""
    tn_, qn, _ = plot_rate(case(total, ar, "N"))
    td_, qd, spill = plot_rate(case(total, ar, "D"))
    rp = max(mononobe(total))
    t_n = peak(case(total, ar, "N"))[1]
    t_d = peak(case(total, ar, "D"))[1]
    r_t = 1.0 - np.interp(t_d, td_, qd) / np.interp(t_n, tn_, qn)
    return qn.max(), qd.max(), 1.0 - qd.max() / qn.max(), qn.max() / rp, spill, r_t


def pc_guide(ar, r):
    return ar * r * QP_GUIDE


def pc_ratio(ar, qp, qpp):
    return ar * qp * (1.0 - qpp) / (ar * qp + 1.0 - ar)


def results():
    """総雨量・水田面積率ごとの値(計算済みのケースだけ)"""
    out = []
    for total in STORMS:
        for ar in AR_LEVELS:
            cs = [case(total, ar, t) for t in "0ND"]
            if not all(have(c) for c in cs):
                continue
            q0, t0 = peak(cs[0])
            qn, tn = peak(cs[1])
            qd, td = peak(cs[2])
            pn, pd, r, qp, spill, r_t = plot_values(total, ar)
            a = ar / 100.0
            row = dict(total=total, ar=ar, q0=q0, t0=t0, qn=qn, tn=tn, qd=qd, td=td, pc=1.0 - qd / qn,
                       pn=pn, pd=pd, r=r, qp=qp, spill=spill, r_t=r_t,
                       pca=pc_guide(a, r), pcb=pc_ratio(a, QP_Y22, QPP_Y22), pcc=pc_ratio(a, qp, 1.0 - r),
                       qp_eff=(qn / q0 - (1.0 - a)) / a)
            ch = case(total, ar, "H")
            if have(ch):
                row["pch"] = 1.0 - peak(ch)[0] / qn
            out.append(row)
    return out


def style(ax):
    ax.grid(True, color=GRID, lw=0.6)
    ax.tick_params(colors=INK2, labelsize=8)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(INK2)


# ---------------------------------------------------------------- 流域の図
def fig_basin():
    z = np.loadtxt("data/z.txt")
    mask = np.loadtxt("data/mask.txt")
    rw = np.loadtxt("data/rw.txt")
    w = np.loadtxt("data/w.txt")
    order = np.loadtxt("data/order.txt")
    ext = [0, NX * DX / 1000, 0, NY * DX / 1000]          # km。行 1 = 北を上に
    fig, axs = plt.subplots(1, 2, figsize=(10.6, 5.0), constrained_layout=True)
    zz = np.where(mask > 0, z, np.nan)
    river = matplotlib.colors.ListedColormap(["#16306e"])
    land = matplotlib.colors.LinearSegmentedColormap.from_list("land", plt.cm.terrain(np.linspace(0.28, 1.0, 256)))
    im = axs[0].imshow(zz, cmap=land, extent=ext, interpolation="nearest", vmin=40, vmax=420)   # 水色を使わない
    axs[0].contour(np.flipud(zz), levels=range(60, 420, 20), colors=INK2, linewidths=0.3, extent=ext)
    axs[0].imshow(np.where(rw > 0, 1.0, np.nan), cmap=river, extent=ext, interpolation="nearest")
    cb = fig.colorbar(im, ax=axs[0], shrink=0.85)
    cb.set_label(T("地盤高 (m)", "ground (m)"), fontsize=8)
    cb.ax.tick_params(labelsize=8, colors=INK2)
    axs[0].set_title(T("(1) 地形(等高線 20 m)と河道(紺。幅 %.0f〜%.0f m)",
                       "(1) terrain (20 m contours), channels (navy, %.0f–%.0f m)")
                     % (w[rw > 0].min(), w[rw > 0].max()), fontsize=9, loc="left", color=INK)
    lev = np.full(z.shape, np.nan)
    ncell = int(mask.sum())
    for k, ar in reversed(list(enumerate(AR_LEVELS))):
        n = int(round(ar / 100.0 * ncell / FRAC))
        lev[(order > 0) & (order <= n)] = k
    cols = matplotlib.colors.ListedColormap(["#1d5e3a", "#3f8f5b", "#8cc084", "#d6ebc2"])
    axs[1].imshow(lev, cmap=cols, extent=ext, interpolation="nearest", vmin=-0.5, vmax=3.5)
    axs[1].imshow(np.where(rw > 0, 1.0, np.nan), cmap=river, extent=ext, interpolation="nearest")
    hs = [matplotlib.patches.Patch(color=cols(k), label=T("%d %% までの水田", "paddies up to %d %%") % ar)
          for k, ar in enumerate(AR_LEVELS)]
    axs[1].legend(handles=hs, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.09), ncol=4, frameon=False)
    axs[1].set_title(T("(2) 水田にするセル(最寄りの河道からの比高の低い順)",
                       "(2) paddy cells (lowest height above the nearest channel first)"), fontsize=9, loc="left",
                     color=INK)
    for ax in axs:
        ax.set_xlabel("x (km)", fontsize=8, color=INK2)
        ax.set_ylabel("y (km)", fontsize=8, color=INK2)
        ax.tick_params(colors=INK2, labelsize=8)
        ax.plot([(IC - 0.5) * DX / 1000], [0.1], marker="v", color=C2, ms=8)
    fig.savefig(os.path.join(FIGDIR, "basin.png"), dpi=130)
    plt.close(fig)


# ---------------------------------------------------------------- 雨・1 区画の流出・出口の流量
def rain_steps(total):
    inc = mononobe(total)
    t = np.repeat(np.arange(25), 2)[1:-1]
    v = np.repeat(inc, 2)
    return np.concatenate([t, [24, 48]]), np.concatenate([v, [0, 0]])


def fig_hydro():
    total = 250
    if not all(have(case(total, ar, t)) for ar in (20, 60) for t in "0ND"):
        return
    fig, axs = plt.subplots(2, 2, figsize=(9.8, 6.8), sharex=True)
    for col, tot in enumerate((250, 350)):
        ax = axs[0, col]
        tr, vr = rain_steps(tot)
        ax.fill_between(tr, vr, color=GRID, step=None, label=T("雨", "rain"))
        for tag, color, ls in (("N", C1, "-"), ("D", C2, "-")):
            c = case(tot, 40, tag)
            if have(c):
                t, q, _ = plot_rate(c)
                ax.plot(t, q, color=color, ls=ls, lw=2, label=T("1 区画の流出 — %s", "outflow of a plot — %s") % KIND[tag])
        ax.set_title(T("(%d) 雨と 1 区画の流出 — 総雨量 %d mm", "(%d) rain and outflow of a plot — %d mm")
                     % (col + 1, tot), fontsize=9, loc="left", color=INK)
        ax.set_ylabel(T("mm/h", "mm/h"), fontsize=8, color=INK2)
    axs[0, 0].legend(fontsize=7, frameon=False, loc="upper right")
    for col, ar in enumerate((20, 60)):
        ax = axs[1, col]
        for tag, color in (("0", INK2), ("N", C1), ("D", C2)):
            t, q = flux(case(total, ar, tag))
            ax.plot(t, q, color=color, lw=2 if tag != "0" else 1.2, ls="-" if tag != "0" else "--", label=KIND[tag])
        ax.set_title(T("(%d) 出口の流量 — 250 mm、水田面積率 %d %%", "(%d) outlet discharge — 250 mm, paddy fraction %d %%")
                     % (col + 3, ar), fontsize=9, loc="left", color=INK)
        ax.set_xlabel(T("時刻 (h)", "time (h)"), fontsize=8, color=INK2)
        ax.set_ylabel(T("流量 (m³/s)", "discharge (m³/s)"), fontsize=8, color=INK2)
        ax.set_xlim(0, 48)
        ax.set_xticks(range(0, 49, 6))
    axs[1, 0].legend(fontsize=7, frameon=False, loc="upper right")
    for ax in axs.flat:
        style(ax)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, "hydro.png"), dpi=130)
    plt.close(fig)


# ---------------------------------------------------------------- ピークカット率と水田面積率
def fig_peakcut(rows):
    if not rows:
        return
    fig, axs = plt.subplots(1, len(STORMS), figsize=(11.6, 4.2), sharey=True)
    xs = np.linspace(0.0, 0.7, 71)
    for k, total in enumerate(STORMS):
        ax = axs[k]
        rr = [r for r in rows if r["total"] == total]
        if not rr:
            continue
        r40 = [r for r in rr if r["ar"] == 40] or rr       # (a)・(c) の線は水田面積率 40 % の計算の 1 区画の値(表 1)
        r_40 = r40[0]["r"]
        qp_40 = r40[0]["qp"]
        ax.plot(xs * 100, pc_guide(xs, r_40) * 100, color=C2, ls="--", lw=1.8,
                label=T("(a) 手引きの積の形(0.6)", "(a) guide, product (0.6)"))
        ax.plot(xs * 100, pc_ratio(xs, QP_Y22, QPP_Y22) * 100, color=C1, ls=":", lw=2.2,
                label=T("(b) 吉川(2022)の比の形(0.7・0.2)", "(b) Yoshikawa (2022), ratio (0.7, 0.2)"))
        ax.plot(xs * 100, pc_ratio(xs, qp_40, 1.0 - r_40) * 100, color=C3, ls="-", lw=1.6,
                label=T("(c) 比の形 + モデルの 1 区画の値", "(c) ratio + the model's plot values"))
        ax.plot([r["ar"] for r in rr], [r["pc"] * 100 for r in rr], "o", color=INK, ms=6,
                label=T("モデル(出口のピーク)", "model (outlet peak)"))
        hh = [r for r in rr if "pch" in r]
        if hh:
            ax.plot([r["ar"] for r in hh], [r["pch"] * 100 for r in hh], "D", color=INK, mfc="white", ms=5,
                    label=T("モデル・取組率 50 %", "model, adoption 50 %"))
        ax.set_title(T("(%d) 総雨量 %d mm(区画のピークカット率 %.0f %%)", "(%d) %d mm (plot peak cut %.0f %%)")
                     % (k + 1, total, r_40 * 100), fontsize=9, loc="left", color=INK)
        ax.set_xlabel(T("流域の水田面積率 (%)", "paddy fraction of the basin (%)"), fontsize=8, color=INK2)
        ax.set_xlim(0, 70)
        style(ax)
    axs[0].set_ylabel(T("出口のピークカット率 (%)", "peak cut at the outlet (%)"), fontsize=8, color=INK2)
    axs[0].legend(fontsize=7, frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, "peakcut.png"), dpi=130)
    plt.close(fig)


# ---------------------------------------------------------------- 数表
def tables(rows):
    print(T("表 1(1 区画の流出。水田面積率 40 % の計算から)", "Table 1 (outflow of a plot; from the runs with 40 % paddies)"))
    print(T("| 総雨量 mm | 雨のピーク mm/h | 通常の落水口の流出のピーク mm/h | 田んぼダムの流出のピーク mm/h | 区画のピークカット率 r | "
            "Q_P(通常の落水口のピーク / 雨のピーク) | 田んぼダムの畦畔の越流 mm | 出口のピークの時刻の r_t |",
            "| Rain mm | rain peak mm/h | outflow peak, normal outlets mm/h | outflow peak, paddy-field dams mm/h | "
            "plot peak cut r | Q_P (normal outlet peak / rain peak) | overflow over the levees, paddy-field dams mm | "
            "r_t at the time of the outlet peak |"))
    print("|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in rows:
        if r["ar"] != 40:
            continue
        area = paddy(case(r["total"], 40, "D"))
        a = area["area1(m2)"][-1] + area["area2(m2)"][-1]
        print("| %d | %.1f | %.1f | %.1f | %.0f %% | %.2f | %.0f | %.0f %% |"
              % (r["total"], max(mononobe(r["total"])), r["pn"], r["pd"], r["r"] * 100, r["qp"], r["spill"] / a * 1000,
                 r["r_t"] * 100))
    print()
    print(T("表 2(出口のピーク流量とピークカット率)", "Table 2 (outlet peak discharge and peak cut)"))
    print(T("| 総雨量 mm | 水田面積率 | タンクなし m³/s | 通常の落水口 m³/s(時刻) | 田んぼダム m³/s(時刻) | ピークカット率(モデル) | "
            "(a) 積の形 | (b) 比の形 | (c) 比の形 + モデルの値 | 流域の Q_P |",
            "| Rain mm | paddy fraction | no tanks m³/s | normal outlets m³/s (time) | paddy-field dams m³/s (time) | "
            "peak cut (model) | (a) product | (b) ratio | (c) ratio + model values | basin Q_P |"))
    print("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in rows:
        print("| %d | %d %% | %.0f | %.0f(%.1f h) | %.0f(%.1f h) | %.1f %% | %.1f %% | %.1f %% | %.1f %% | %.2f |"
              % (r["total"], r["ar"], r["q0"], r["qn"], r["tn"], r["qd"], r["td"], r["pc"] * 100, r["pca"] * 100,
                 r["pcb"] * 100, r["pcc"] * 100, r["qp_eff"]))
    hh = [r for r in rows if "pch" in r]
    if hh:
        print()
        print(T("表 3(取組率 50 %。水田面積率 40 %)", "Table 3 (adoption 50 %; 40 % paddies)"))
        print(T("| 総雨量 mm | ピークカット率(取組率 50 %) | 取組率 100 % の半分 |",
                "| Rain mm | peak cut (adoption 50 %) | half of adoption 100 % |"))
        print("|---:|---:|---:|")
        for r in hh:
            print("| %d | %.1f %% | %.1f %% |" % (r["total"], r["pch"] * 100, r["pc"] * 50))


if __name__ == "__main__":
    fig_basin()
    rows = results()
    fig_hydro()
    fig_peakcut(rows)
    tables(rows)
