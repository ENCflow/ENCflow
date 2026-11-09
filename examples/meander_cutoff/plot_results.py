#!/usr/bin/env python3
"""examples/meander_cutoff の結果の図と数表。

  python3 plot_results.py      # figs/*.png(日本語ラベル)と数表
  python3 plot_results.py en   # en/figs/*.png(英語ラベル)と数表

  figs/sequence.png           出水あり(result)の経過: 流速と河床変化(30 分 = 地形 5 h ごと)
  figs/states.png             全構成の流れの状態(流れている・滞水・乾いた初期河道)の推移
  figs/final_slump_fines.png  出水なし・粘着性+崩落土塊+細粒分(result_slump_fines)の終了時と細粒分の厚さ

領域(plot_setup.py と同じ定義): ループ = 初期河道のうち y > 70 m(2,265 セル。x = 160 m より西が
ループ 1、東がループ 2)。
「流れている」は h > 0.05 m かつ |V| > 0.3 m/s。3 つの陸 = 出水で流れが横切る初期の陸(ループ 1 の脚の間
x = 100〜120 m・y = 55〜90 m、2 つのループの間 x = 150〜175 m・y = 90〜140 m、ループ 2 の脚の間
x = 205〜225 m・y = 100〜145 m)。下の湾曲 = 2 つのループをつなぐ南へ張り出す湾曲(初期河道のうち
y <= 70 m・x = 115〜210 m。469 セル)。
存在する結果ディレクトリだけを扱う。台帳は画面出力 Screen_<名>.log(param.txt は Screen.log)から読む。
依存: numpy, matplotlib
"""
import os
import re
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import make_init as mi
from plot_setup import loops, LANDS_XY

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)

MORFAC = 10.0
z0 = np.loadtxt("z.txt"); h0 = np.loadtxt("h.txt")
NY, NX = z0.shape
DX = mi.DX
x = (np.arange(NX) + 0.5) * DX
y = (np.arange(NY) + 0.5) * DX
ext = [0, NX * DX, 0, NY * DX]
loop = loops(h0)
# 上流側のループ(ループ 1)と下流側のループ(ループ 2)。x = 160 m は 2 つのループの間の陸
LOOPS = ((loop & (x[None, :] <= 160.0)), (loop & (x[None, :] > 160.0)))
# 出水で流れが横切る 3 つの陸(初期の陸のセル): ループ 1 の脚の間、2 つのループの間、ループ 2 の脚の間
LANDS = [(T("ループ 1 の脚の間", "between the limbs of loop 1"),) + LANDS_XY[0],
         (T("2 つのループの間", "between the two loops"),) + LANDS_XY[1],
         (T("ループ 2 の脚の間", "between the limbs of loop 2"),) + LANDS_XY[2]]
LANDM = [(h0 == 0) & (x[None, :] >= xa) & (x[None, :] <= xb) & (y[:, None] >= ya) & (y[:, None] <= yb)
         for _, (xa, xb), (ya, yb) in LANDS]
LANDALL = LANDM[0] | LANDM[1] | LANDM[2]
# 下の湾曲: ループ 1 の下流側の脚から南へ回ってループ 2 の上流側の脚へつなぐ湾曲(初期河道のうち y <= 70 m)
BEND = (h0 > 0) & (y[:, None] <= 70.0) & (x[None, :] > 115.0) & (x[None, :] < 210.0)
# (結果ディレクトリ, 設定ファイル, 画面出力, 日本語名, 英語名)
CASES = [("result", "param.txt", "Screen.log", "出水あり(安息角 40°)", "flood (repose 40°)"),
         ("result_slump", "param_slump.txt", "Screen_slump.log", "出水あり+崩落土塊", "flood + slump blocks"),
         ("result_noflood", "param_noflood.txt", "Screen_noflood.log", "出水なし: 対照(安息角 40°)", "no flood: control (repose 40°)"),
         ("result_slump_noflood", "param_slump_noflood.txt", "Screen_slump_noflood.log", "出水なし: 安息角 40° + 崩落土塊",
          "no flood: repose 40° + slump blocks"),
         ("result_slump_cohesive", "param_slump_cohesive.txt", "Screen_slump_cohesive.log", "出水なし: 粘着性 + 崩落土塊",
          "no flood: cohesive + slump blocks"),
         ("result_slump_fines", "param_slump_fines.txt", "Screen_slump_fines.log", "出水なし: 粘着性 + 崩落土塊 + 細粒分",
          "no flood: cohesive + slump blocks + fines")]
# 計算中の結果(FILENUMBER.csv が空)は外す
CASES = [c for c in CASES if os.path.exists(c[0] + "/FILENUMBER.csv") and
         any(l.strip() and not l.startswith("#") for l in open(c[0] + "/FILENUMBER.csv"))]
NAME = {c[0]: (c[4] if EN else c[3]) for c in CASES}


def rd(rdir, name, k):
    return np.loadtxt("%s/%s%04d.txt" % (rdir, name, k))


def times(rdir):
    """出力番号 → 水理の時間 (s)"""
    return {int(l.split(",")[0]): float(l.split(",")[2])
            for l in open(rdir + "/FILENUMBER.csv") if not l.startswith("#") and int(l.split(",")[0]) < 9000}


def hydrograph(pfile):
    """設定ファイルの inflow_val(分, m³/s)。ENCflow と同じく折れ線で補間する"""
    pts = sorted((float(m.group(1)), float(m.group(2))) for m in
                 (re.match(r"\s*inflow_val\(1:2,\d+,1\)\s*=\s*([0-9.]+),\s*([0-9.]+)", l) for l in open(pfile)) if m)
    tq = np.array(pts)
    return lambda ts: float(np.interp(ts / 60.0, tq[:, 0], tq[:, 1]))


# ループの頂点(中心線の向きが東になる点。路長 s = LIN + Λ/2 と LIN + 3Λ/2)の x
APEX_X = [min(mi.pts, key=lambda p: abs(p[0] - s))[1] - mi.XMIN for s in (mi.LIN + mi.LAM / 2, mi.LIN + 1.5 * mi.LAM)]


def qtop(h, vv, n):
    """ループ n(0, 1)の頂部を回る流量の目安: 頂点を南北に切る線(y >= 140 m)に沿う h|V| Δx の和(m³/s)。
    出力は流速の大きさだけなので、流れが線に直交しない所や渦があると大きめに出る"""
    j = int(APEX_X[n] / DX); m = y >= 140.0
    return float((h[m, j] * vv[m, j]).sum() * DX)


def state(rdir, k):
    h = rd(rdir, "H", k); vv = rd(rdir, "V", k); z = rd(rdir, "Z", k)
    flowing = (h > 0.05) & (vv > 0.3)
    return h, vv, z, flowing


def ledger(log):
    out = {}
    if not os.path.exists(log):
        return out
    pats = {"repose": r"angle-of-repose avalanching moved\s+([0-9.Ee+-]+)",
            "rockfall": r"rockfall moved\s+([0-9.Ee+-]+)",
            "fines": r"bed load carried\s+([0-9.Ee+-]+)",
            "dzclip": r"fluvial dzmax clip fired on\s+([0-9]+)"}
    for line in open(log, errors="replace"):
        for k, p in pats.items():
            m = re.search(p, line)
            if m:
                out[k] = float(m.group(1))
    return out


# ------------------------------------------------------------------ 数表
print("領域: ループ %d セル(ループ 1 %d、ループ 2 %d)、下の湾曲 %d セル。ループの頂点 x = %.0f m・%.0f m" % (
    loop.sum(), LOOPS[0].sum(), LOOPS[1].sum(), BEND.sum(), APEX_X[0], APEX_X[1]))
for rdir, pfile, log, _, _ in CASES:
    tm = times(rdir); ks = sorted(tm)
    Q = hydrograph(pfile)
    flood = max(Q(t) for t in tm.values()) > 20.0
    print()
    print("## %s(%s)" % (NAME[rdir], rdir))
    print("| t (分) | 地形時間 (h) | Q (m³/s) | ループで流れているセル | 頂部を回る流量の目安 ループ 1 / 2 (m³/s) "
          "| 3 つの陸で流れているセル(%d セル中) / 陸の河床変化の平均 (m) | 下の湾曲で流れているセル(%d セル中) "
          "| 初期河道の外で湿潤 | 最深の洗掘 (m) |" % (LANDALL.sum(), BEND.sum()))
    print("|---|---|---|---|---|---|---|---|---|")
    # 出水ありは全出力(30 分 = 地形 5 h ごと)、出水なし(地形 180 h)は 20 h ごと
    for k in (ks[1:] if flood else [k for k in ks if k > 0 and k % 4 == 0]):
        h, vv, z, fl = state(rdir, k)
        print("| %.0f | %.0f | %.0f | %d | %.1f / %.1f | %d / %+.2f | %d | %d | %.2f |" % (
            tm[k] / 60, tm[k] * MORFAC / 3600, Q(tm[k]), (fl & loop).sum(), qtop(h, vv, 0), qtop(h, vv, 1),
            (fl & LANDALL).sum(), (z - z0)[LANDALL].mean(), (fl & BEND).sum(), ((h > 0.05) & (h0 == 0)).sum(), (z - z0).min()))
    # 短絡の時期: ループで流れているセルが初めてループのセル数の半分を下回った出力(初期の出力 0 は流速 0 なので除く)
    nloop = {k: (state(rdir, k)[3] & loop).sum() for k in ks[1:]}
    cut = next((k for k in ks[1:] if nloop[k] < 0.5 * loop.sum()), None)
    K = ks[-1]
    h, vv, z, fl = state(rdir, K); dz = z - z0

    def interval(k):
        return "地形時間 %.0f〜%.0f h の間" % (tm[ks[ks.index(k) - 1]] * MORFAC / 3600, tm[k] * MORFAC / 3600)
    print("短絡(ループで流れているセル < %d)の時期: %s" % (0.5 * loop.sum(), "なし" if cut is None else interval(cut)))
    if cut is not None:
        # 短絡の後に流れがループへ戻った時期: ループで流れているセルが 1 出力で 100 以上増えた出力
        # (出水なしでは、2 つのループの間の陸が切れてループ 1 からループ 2 の上流側の脚へ流れが入る時)
        back = next((k for k in ks[ks.index(cut) + 1:] if nloop[k] - nloop[ks[ks.index(k) - 1]] >= 100), None)
        print("短絡の後に流れがループへ戻った(ループで流れているセルが 1 出力で 100 以上増えた)時期: %s" % (
            "なし" if back is None else interval(back)))
    print("終了時の陸: " + "、".join("%s 流れている %d / %d セル・河床変化の平均 %+.2f m" % (
        LANDS[n][0], (fl & m).sum(), m.sum(), dz[m].mean()) for n, m in enumerate(LANDM)))
    print("終了時: 湿潤セル %d(初期河道の外 %d)、ループで流れているセル %d" % (
        (h > 0.05).sum(), ((h > 0.05) & (h0 == 0)).sum(), (fl & loop).sum()))
    sf = rd(rdir, "Sf", K) if os.path.exists("%s/Sf%04d.txt" % (rdir, K)) else None
    for n, lp in enumerate(LOOPS):
        print("終了時のループ %d の初期河道(%d セル): 流れている %d、滞水 %d、乾いた %d、河床変化の平均 %+.2f m%s" % (
            n + 1, lp.sum(), (fl & lp).sum(), ((h > 0.05) & ~fl & lp).sum(), ((h <= 0.05) & lp).sum(), dz[lp].mean(),
            "" if sf is None else "、細粒分の厚さ Sf の平均 %.2f m・最大 %.2f m" % (sf[lp].mean(), sf[lp].max())))
    print("終了時の下の湾曲の初期河道(%d セル): 流れている %d、滞水 %d、乾いた %d、河床変化の平均 %+.2f m" % (
        BEND.sum(), (fl & BEND).sum(), ((h > 0.05) & ~fl & BEND).sum(), ((h <= 0.05) & BEND).sum(), dz[BEND].mean()))
    if sf is not None:
        jm, im_ = np.unravel_index(sf.argmax(), sf.shape)
        print("細粒分の厚さ Sf: 湿潤セルの平均 %.2f m、初期河道の外の湿潤セルの平均 %.2f m、最大 %.2f m(x = %.0f m・y = %.0f m)" % (
            sf[h > 0.05].mean(), sf[(h > 0.05) & (h0 == 0)].mean(), sf.max(), x[im_], y[jm]))
    lg = ledger(log)
    if lg:
        print("台帳: 安息角崩落 %s m³、崩落土塊 %s m³、掃流砂に同伴した細粒分 %s m³、fluv_dzmax の発動 %s エッジ" % tuple(
            "–" if lg.get(k) is None else "{:,.0f}".format(lg[k]) for k in ("repose", "rockfall", "fines", "dzclip")))


# ------------------------------------------------------------------ 図
def sequence(rdir, pfile, fname):
    """初期(流速 0)を除く全出力の流速と河床変化"""
    tm = times(rdir); ks = sorted(tm)[1:]
    Q = hydrograph(pfile)
    fig, axes = plt.subplots(len(ks), 2, figsize=(12, 2.95 * len(ks)))
    for n, k in enumerate(ks):
        h, vv, z, fl = state(rdir, k)
        ax = axes[n, 0]
        im = ax.imshow(np.where(h > 0.05, vv, np.nan), origin="lower", extent=ext, cmap="magma", vmin=0, vmax=2)
        ax.contour(x, y, h0 > 0, levels=[0.5], colors="c", linewidths=0.4)
        ax.set_title(T("|V| (m/s) %.0f 分、Q = %.0f m³/s(地形 %.0f h)", "|V| (m/s) at %.0f min, Q = %.0f m³/s (landform %.0f h)")
                     % (tm[k] / 60, Q(tm[k]), tm[k] * MORFAC / 3600), fontsize=9, loc="left")
        fig.colorbar(im, ax=ax, shrink=0.85, pad=0.01)
        ax = axes[n, 1]
        im = ax.imshow(z - z0, origin="lower", extent=ext, cmap="RdBu_r", vmin=-2, vmax=2)
        ax.contour(x, y, h0 > 0, levels=[0.5], colors="k", linewidths=0.3)
        ax.set_title(T("河床変化 z − z0 (m)", "bed change z − z0 (m)"), fontsize=9, loc="left")
        fig.colorbar(im, ax=ax, shrink=0.85, pad=0.01)
    for ax in axes.ravel():
        ax.tick_params(labelsize=7)
    fig.tight_layout(); fig.savefig(os.path.join(FIGDIR, fname), dpi=80); plt.close(fig)


# 流れの状態の色: 乾いた陸、乾いた初期河道、滞水(h > 0.05 m、|V| <= 0.3 m/s)、
# 初期河道の中で流れている、初期河道の外で流れている
SCOL = np.array([[0.99, 0.98, 0.95], [0.78, 0.78, 0.78], [0.62, 0.80, 0.95], [0.45, 0.05, 0.08], [0.92, 0.33, 0.20]])
SLAB = [T("乾いた陸", "dry land"), T("乾いた初期河道", "dry initial channel"), T("滞水(|V| ≤ 0.3 m/s)", "standing water (|V| ≤ 0.3 m/s)"),
        T("流れている(初期河道の中)", "flowing (inside initial channel)"), T("流れている(初期河道の外)", "flowing (outside initial channel)")]


def states(fname):
    """各構成の流れの状態。出水ありは地形 5・15・20・30 h、出水なしは 80・100・140・180 h"""
    rows = [c for c in CASES]
    hrs_f, hrs_n = [5, 15, 20, 30], [80, 100, 140, 180]
    fig, axes = plt.subplots(len(rows), 4, figsize=(15, 2.75 * len(rows) + 0.6), squeeze=False)
    for i, (rdir, pfile, _, _, _) in enumerate(rows):
        tm = times(rdir); ks = sorted(tm)
        Q = hydrograph(pfile)
        flood = max(Q(t) for t in tm.values()) > 20.0
        for n, hr in enumerate(hrs_f if flood else hrs_n):
            ax = axes[i, n]
            k = min(ks, key=lambda kk: abs(tm[kk] * MORFAC / 3600 - hr))
            h, vv, z, fl = state(rdir, k)
            cat = np.where(h0 > 0, 1, 0)
            cat = np.where((h > 0.05) & ~fl, 2, cat)
            cat = np.where(fl & (h0 > 0), 3, cat)
            cat = np.where(fl & (h0 == 0), 4, cat)
            ax.imshow(SCOL[cat], origin="lower", extent=ext, interpolation="nearest")
            ax.contour(x, y, loop, levels=[0.5], colors="k", linewidths=0.4)
            ax.set_title(T("地形 %.0f h、Q = %.0f m³/s。ループで流れている %d", "landform %.0f h, Q = %.0f m³/s; loop flowing %d")
                         % (tm[k] * MORFAC / 3600, Q(tm[k]), (fl & loop).sum()), fontsize=8, loc="left")
            ax.tick_params(labelsize=6)
            if n == 0:
                ax.set_ylabel(NAME[rdir], fontsize=8)
    from matplotlib.patches import Patch
    hd = [Patch(facecolor=SCOL[j], edgecolor="0.5", label=SLAB[j]) for j in range(5)]
    from matplotlib.lines import Line2D
    hd += [Line2D([], [], color="k", lw=0.8, label=T("ループ(初期河道のうち y > 70 m)", "loop (initial channel, y > 70 m)"))]
    fig.legend(handles=hd, loc="lower center", ncol=3, fontsize=8, frameon=False)
    fig.tight_layout(rect=(0, 0.045, 1, 1)); fig.savefig(os.path.join(FIGDIR, fname), dpi=80); plt.close(fig)


def final(rdir, fname, fines=False):
    tm = times(rdir); K = sorted(tm)[-1]
    h, vv, z, fl = state(rdir, K)
    n = 4 if fines else 3
    fig, axes = plt.subplots(1, n, figsize=(5.4 * n, 4.0))
    im = axes[0].imshow(np.where(h > 0.05, h, np.nan), origin="lower", extent=ext, cmap="Blues", vmin=0, vmax=3)
    axes[0].set_title(T("水深 (m)", "depth (m)"), fontsize=9.5, loc="left"); fig.colorbar(im, ax=axes[0], shrink=0.85, pad=0.01)
    im = axes[1].imshow(np.where(h > 0.05, vv, np.nan), origin="lower", extent=ext, cmap="magma", vmin=0, vmax=2)
    axes[1].set_title("|V| (m/s)", fontsize=9.5, loc="left"); fig.colorbar(im, ax=axes[1], shrink=0.85, pad=0.01)
    im = axes[2].imshow(z - z0, origin="lower", extent=ext, cmap="RdBu_r", vmin=-2, vmax=2)
    axes[2].set_title("z − z0 (m)", fontsize=9.5, loc="left"); fig.colorbar(im, ax=axes[2], shrink=0.85, pad=0.01)
    if fines:
        sf = rd(rdir, "Sf", K)
        im = axes[3].imshow(np.where(sf > 0.005, sf, np.nan), origin="lower", extent=ext, cmap="YlOrBr", vmin=0, vmax=1.0)
        axes[3].set_title(T("細粒分の厚さ Sf (m)", "bed fines thickness Sf (m)"), fontsize=9.5, loc="left")
        fig.colorbar(im, ax=axes[3], shrink=0.85, pad=0.01)
    for ax in axes:
        ax.contour(x, y, h0 > 0, levels=[0.5], colors="k", linewidths=0.4)
        ax.set_xlabel("x (m)", fontsize=8); ax.set_ylabel("y (m)", fontsize=8); ax.tick_params(labelsize=7)
    fig.suptitle(T("%s: 地形 %.0f h(黒 = 初期の河岸)", "%s: landform %.0f h (black = initial banks)")
                 % (NAME[rdir], tm[K] * MORFAC / 3600), fontsize=10, x=0.01, ha="left")
    fig.tight_layout(); fig.savefig(os.path.join(FIGDIR, fname), dpi=90); plt.close(fig)


made = []
if "result" in NAME:
    sequence("result", "param.txt", "sequence.png")
    made += ["sequence.png"]
if CASES:
    states("states.png")
    made += ["states.png"]
if "result_slump_fines" in NAME:
    final("result_slump_fines", "final_slump_fines.png", fines=True)
    made += ["final_slump_fines.png"]
print()
print("figures: " + " ".join("%s/%s" % (FIGDIR, f) for f in made))
