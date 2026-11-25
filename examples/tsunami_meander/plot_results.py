#!/usr/bin/env python3
"""examples/tsunami_meander の計算と実験の比較の図と数表。

  python3 plot_results.py      # figs/*.png(日本語ラベル)と数表
  python3 plot_results.py en   # en/figs/*.png(英語ラベル)と数表

  figs/setup.png      3 つの水路の平面形(格子のマスク)、ゲート、測定断面、側壁の階段の拡大
  figs/surface.png    蛇行度 1.10 の水路の波状段波の波高の平面分布(静水圧と非静水圧。2 時刻)
  figs/breaking.png   蛇行度 1.10 の水路の砕波段波: 断面平均波高、横断分布、両岸の最大波高(実験と静水圧の計算)
  figs/undular.png    蛇行度 1.10 の水路の波状段波: 同上と Section 4 の外岸の時系列(実験と静水圧・非静水圧の計算)
  figs/firstwave.png  波状段波の第 1 波の波高の縦断分布(直線水路・蛇行度 1.25・蛇行度 1.10)
  figs/sens.png       感度の構成(格子間隔・水路を 30° 回した配置・砕波スイッチ・初期の段差をなだらかにした計算・砕波段波の非静水圧)。
                      make sens の結果があれば描く

数表(標準出力。README の数値はこれを写したもの):
  表 1  段波の理論値(湿潤床のダム破壊の解)
  表 2  蛇行度 1.10 の水路の断面平均波高(到達時刻、到達後の平均、最初の山)
  表 3  蛇行度 1.10 の水路の横断方向の時間平均の偏差(両岸の点)
  表 4  蛇行度 1.10 の水路の両岸の最大波高(岸沿いの点列のばらつき、外岸の最大の山の幅、計測が 2 つの計算の間に入る点の数)
  表 5  波状段波の第 1 波の波高(3 つの水路。直線水路の岸と中央の比、直線水路に対する外岸の比、2 つの計算の間に入る点の数)
  表 6  蛇行度 1.10 の水路の Section 4 の外岸の波形(山と谷の時刻と高さ)、断面 4 の 5 点の第 1 の山、直線水路の先頭の速さ
  表 7  感度の構成の、両岸の最大波高・到達時刻・第 1 波の波高と、直線水路の水面勾配の最大(砕波スイッチの判定との比較)
終わった計算の結果ディレクトリだけを扱う(E9998.txt がないものは表と図から外す)。
依存: numpy, matplotlib
"""
import csv
import math
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

HERE = os.path.dirname(os.path.abspath(__file__))
EN = len(sys.argv) > 1 and sys.argv[1] == "en"
FIGS = os.path.join(HERE, "en", "figs") if EN else os.path.join(HERE, "figs")
plt.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["font.size"] = 9

G = 9.8                       # 重力加速度 (m/s2)。ENCflow の既定の gg
H0 = 0.285                    # ゲート上流の水深 (m)
H1 = {"bk": 0.107, "ub": 0.147}
BORE = {"bk": "breaking", "ub": "undular"}       # data_kobayashi/ の CSV での名前
# 構成名: (入力の tag, 段波, モデル)
RUNS = {"bk_h": ("s110", "bk", "h"), "ub_h": ("s110", "ub", "h"), "ub_nh": ("s110", "ub", "nh"),
        "str_h": ("str", "ub", "h"), "str_nh": ("str", "ub", "nh"), "s125_h": ("s125", "ub", "h"), "s125_nh": ("s125", "ub", "nh"),
        # 感度の構成(make sens)
        "str_nhb": ("str", "ub", "nhb"), "str_nhb2": ("str", "ub", "nhb"), "str_nh_s": ("str_s", "ub", "nh"), "str_nhb_s": ("str_s", "ub", "nhb"),
        "bk_nh": ("s110", "bk", "nh"), "bk_h_c1": ("s110", "bk", "h"),
        "bk_h_r30": ("s110_r30", "bk", "h"), "ub_nh_r30": ("s110_r30", "ub", "nh"),
        "bk_h_d4": ("s110_d4", "bk", "h"), "ub_nh_d4": ("s110_d4", "ub", "nh"),
        "bk_h_d1": ("s110_d1", "bk", "h"), "ub_nh_d1": ("s110_d1", "ub", "nh")}
SENS = ("str_nhb", "str_nhb2", "str_nh_s", "str_nhb_s", "bk_nh", "bk_h_c1", "bk_h_r30", "ub_nh_r30", "bk_h_d4", "ub_nh_d4", "bk_h_d1", "ub_nh_d1")
SECS21 = (1, 3, 4, 5, 7, 8)   # 小林ら (2021) の測定断面
PERIOD = 3.5                  # 実験の波列の周期(無次元時間。Section 4 の外岸の山から山まで。表 6)
# 色: 系列の役割ごとに固定(実験 = 黒、静水圧 = 青、非静水圧 = 橙、論文の 3 次元計算 = 緑、論文の平面 2 次元計算 = 灰)。
# 感度の図(論文の計算を描かない)では、3 つ目の色を「非静水圧 + 砕波スイッチ」に使う
C_EXP, C_H, C_NH, C_3D, C_2D, C_TH = "#191919", "#257de0", "#f47230", "#00b894", "#666666", "#9c9c9c"
C_SW = C_3D
SEQ = LinearSegmentedColormap.from_list("seq_blue", ["#e3effd", "#cce3fd", "#84b9f3", "#338ced", "#1b64be", "#0e3d7e"])   # 1 色相の明→暗


def L(ja, en):
    return en if EN else ja


# ---------------------------------------------------------------- 理論(湿潤床のダム破壊。Stoker 1957)
def stoker(h0, h1):
    """段波の背後の水深 hm・流速 um と段波の波速 sb"""
    c0 = math.sqrt(G * h0); lo, hi = h1, h0
    for _ in range(200):
        hm = 0.5 * (lo + hi)
        if (hm - h1) * math.sqrt(G * (hm + h1) / (2 * hm * h1)) > 2 * (c0 - math.sqrt(G * hm)): hi = hm
        else: lo = hm
    um = 2 * (c0 - math.sqrt(G * hm))
    return hm, um, um * hm / (hm - h1)


def t_upstream(h0, h1, lup, s):
    """ゲートから上流へ進む負の波が、長さ lup の直線部の上流端で反射して、ゲートから s の位置に届く時刻(1 次元の特性曲線)。
    負の波の先端は -c0 で進み、反射した波は希薄波の中を dx/dt = u + c で、その下流では um + cm で進む"""
    hm, um, sb = stoker(h0, h1); c0 = math.sqrt(G * h0); cm = math.sqrt(G * hm)
    t1 = lup / c0; tex = t1 / ((2 * c0 - um + cm) / (3 * c0)) ** 1.5; xex = (um - cm) * tex
    return tex - xex / (um + cm) + s / (um + cm)


# ---------------------------------------------------------------- 実験値(data_kobayashi/)と計算結果の読み込み
def data(fn):
    with open(os.path.join(HERE, "data_kobayashi", fn), encoding="utf-8") as f:
        return list(csv.DictReader([ln for ln in f if not ln.startswith("#")]))


def series(rows, xk, yk, **cond):
    r = [(float(x[xk]), float(x[yk])) for x in rows if all(x[k] == str(v) for k, v in cond.items())]
    return np.array(r).T if r else np.zeros((2, 0))


def read_probes(tag):
    """probes_<tag>.csv → (諸元の辞書, プローブの行のリスト)。ファイルがなければ None"""
    fn = os.path.join(HERE, f"probes_{tag}.csv")
    if not os.path.exists(fn): return None
    with open(fn, encoding="utf-8") as f:
        lines = f.read().splitlines()
    par = {k: v for k, v in (w.split("=") for w in lines[0][1:].split())}
    return par, list(csv.DictReader([ln for ln in lines if not ln.startswith("#")]))


def read_probe(fn):
    """プローブの CSV → 配列 [時刻 (min), 地盤高 z (m), 水深 h (m)]"""
    with open(fn) as f:
        return np.array([[float(v) for v in ln.split(",")[1:4]] for ln in f if ln[0] != "#" and ln.strip()])


def gauge_xy(rows, kind, sec):
    """測定断面 sec の測定点の位置(格子座標。プローブの位置の重みつき平均)を、右岸側から順に"""
    g = {}
    for r in rows:
        if r["kind"] == kind and int(r["section"]) == sec:
            g.setdefault(int(r["gauge"]), []).append((float(r["w"]) * float(r["x"]), float(r["w"]) * float(r["y"])))
    return [tuple(np.sum(v, axis=0)) for k, v in sorted(g.items())]


class Run:
    """1 つの計算の、測定点ごとの時系列(測定点を囲むセル中心のプローブの、双 1 次補間の重みつき平均)。
    eta = (水位 - 初期の下流の水位) / 理論の段波波高、ts = t sqrt(g / h0)"""

    def __init__(self, name):
        self.name = name; self.tag, self.bore, self.model = RUNS[name]
        self.dir = os.path.join(HERE, "result_" + name)
        self.par, rows = read_probes(self.tag)
        self.B = float(self.par["B"]); self.Lm = float(self.par["Lm"]); self.Lup = float(self.par["Lup"])
        self.h1 = H1[self.bore]; self.hm, self.um, self.sb = stoker(H0, self.h1); self.ht = self.hm - self.h1
        d = [read_probe(os.path.join(self.dir, "probes", f"probe{i:04d}.csv")) for i in range(1, len(rows) + 1)]
        self.t = d[0][:, 0] * 60.0; self.ts = self.t * math.sqrt(G / H0)
        eta_p = np.array([(x[:, 2] + x[0, 1] - self.h1) / self.ht for x in d])       # プローブごと(x[0, 1] は地盤高)
        gid = np.array([int(r["gauge"]) for r in rows]); wgt = np.array([float(r["w"]) for r in rows])
        first = [int(np.argmax(gid == g)) for g in range(1, gid.max() + 1)]
        self.eta = np.array([(eta_p[gid == g] * wgt[gid == g][:, None]).sum(axis=0) for g in range(1, gid.max() + 1)])
        self.kind = np.array([rows[i]["kind"] for i in first]); self.sec = np.array([int(rows[i]["section"]) for i in first])
        self.s = np.array([float(rows[i]["s"]) for i in first]); self.n = np.array([float(rows[i]["n"]) for i in first])

    def idx(self, kind, sec=None):
        return [i for i in range(len(self.s)) if self.kind[i] == kind and (sec is None or self.sec[i] == sec)]

    def tend(self, i):
        """上流端の影響が届く時刻 (s)。実験の図が示す時間の範囲の終わりに当たる"""
        return t_upstream(H0, self.h1, self.Lup, self.s[i])

    def bank(self, side, smax=1.26):
        """岸沿いの点の番号。side = 'left' / 'right' / 'outer' / 'inner'(外岸は s/Lm = 0〜0.25 と 0.75〜1.25 が右岸、
        0.25〜0.75 が左岸)。直線水路は中心線"""
        if self.tag.startswith("str"):
            return [i for i in self.idx("center") if self.s[i] <= smax * self.Lm]
        out = []
        for ir, il in zip(self.idx("right"), self.idx("left")):
            x = self.s[ir] / self.Lm
            if x > smax: continue
            right_outer = (x <= 0.25 + 1e-9) or (x > 0.75 + 1e-9)
            if side == "right": out.append(ir)
            elif side == "left": out.append(il)
            elif side == "outer": out.append(ir if right_outer else il)
            else: out.append(il if right_outer else ir)
        return out

    def first_peak(self, i, drop=0.05):
        return first_peak(self.t, self.eta[i], drop)

    def wave1(self, i):
        """第 1 波の波高。非静水圧の計算は最初の山。静水圧の計算(砕波スイッチつきの非静水圧を含む)には波列がないので、
        到達(波高 0.3)から波 1 周期分(無次元時間 PERIOD)の間の最大を、それに当たる量とする"""
        if self.model == "nh": return self.first_peak(i)[1]
        ta = self.cross(self.eta[i], 0.3); tb = ta + PERIOD / math.sqrt(G / H0)
        if not ta == ta or tb > self.t[-1]: return float("nan")
        return self.eta[i][(self.t >= ta) & (self.t <= tb)].max()

    def wmax(self, i):
        """上流端の影響が届くまでの最大波高。計算がそれより前に終わっていれば NaN"""
        if self.t[-1] < self.tend(i) - 1e-6: return float("nan")
        return self.eta[i][self.t <= self.tend(i)].max()

    def cross(self, e, level=0.5):
        return cross(self.t, e, level)


def first_peak(t, e, drop=0.05):
    """最初の山(時刻, 高さ): 時間順に最大を更新していき、最大から drop 以上下がったところで、その最大を返す。
    時系列の終わりまでに下がらなければ(山がまだ通り過ぎていない)高さは NaN"""
    best = -1.0; kb = 0
    for k in range(len(e)):
        if e[k] > best: best = e[k]; kb = k
        elif best > 0.3 and e[k] < best - drop: return t[kb], best
    return t[kb], float("nan")


def cross(t, e, level=0.5):
    """e が level を初めて上向きに横切る時刻(線形補間)"""
    k = int(np.argmax(e >= level))
    if k == 0: return float("nan")
    return t[k - 1] + (level - e[k - 1]) / (e[k] - e[k - 1]) * (t[k] - t[k - 1])


def extrema(t, e, n=4, drop=0.05):
    """山と谷を交互に n 個: [(時刻, 値), ...]。drop 以上の戻りで確定する"""
    out = []; up = True; best = e[0]; kb = 0
    for k in range(1, len(e)):
        if (e[k] > best) == up: best = e[k]; kb = k
        elif abs(e[k] - best) > drop and (out or best > 0.3):
            out.append((t[kb], best)); up = not up; best = e[k]; kb = k
            if len(out) == n: break
    return out


def fnum(v, fmt):
    """NaN(その時刻・断面まで計算していない、山が確定していない)は - と書く"""
    return fmt % v if v == v else " " * (len(fmt % 0.0) - 1) + "-"


def load_runs():
    runs = {}
    for name in RUNS:
        if os.path.exists(os.path.join(HERE, "result_" + name, "E9998.txt")) and \
           os.path.exists(os.path.join(HERE, f"probes_{RUNS[name][0]}.csv")):
            runs[name] = Run(name)
    return runs


def level_map(run, t_out):
    """時刻 t_out (s) の水位の分布 → 波高 / h_t の配列(マスクの外は NaN)と、水路座標の範囲"""
    num = None
    with open(os.path.join(run.dir, "FILENUMBER.csv")) as f:
        for ln in f:
            if ln.startswith("#"): continue
            c = ln.split(",")
            if num is None and abs(float(c[2]) - t_out) < 1e-6: num = int(c[0])      # 終了時刻は 9998・9999 にも出るので、最初の番号を採る
    e = np.loadtxt(os.path.join(run.dir, f"E{num:04d}.txt"))
    mask = np.loadtxt(os.path.join(HERE, f"mask_{run.tag}.txt"))
    dx = float(run.par["dx"]); x0 = float(run.par["x0"]); y0 = float(run.par["y0"])
    ext = [x0, x0 + e.shape[1] * dx, y0, y0 + e.shape[0] * dx]
    return np.where(mask > 0, (e - run.h1) / run.ht, np.nan), ext


# ---------------------------------------------------------------- 図の部品
def style(ax, xl=None, yl=None, title=None):
    ax.grid(True, color="#e6e6e6", lw=0.6); ax.set_axisbelow(True)
    for sp in ("top", "right"): ax.spines[sp].set_visible(False)
    if xl: ax.set_xlabel(xl)
    if yl: ax.set_ylabel(yl)
    if title: ax.set_title(title, fontsize=9.5, loc="left")


LB_T = lambda: L("無次元時間  ", "dimensionless time  ") + r"$t\sqrt{g/h_0}$"
LB_E = lambda: L("波高 / ", "wave height / ") + r"$h_t$"
LB_S = lambda: L("ゲートからの距離 / 蛇行長", "distance from the gate / meander length")
NM_H = lambda: L("ENCflow 静水圧", "ENCflow hydrostatic")
NM_NH = lambda: L("ENCflow 非静水圧", "ENCflow non-hydrostatic")
NM_EXP = lambda: L("実験", "experiment")
NM_E19 = lambda: L("実験(小林ら 2019)", "experiment (Kobayashi et al. 2019)")
NM_E21 = lambda: L("実験(小林ら 2021)", "experiment (Kobayashi et al. 2021)")
NM_TH = lambda: L("理論(1 次元の理想段波、一様湾曲の定常流の横断水面形)", "theory (ideal 1D bore; steady flow in a uniform bend)")
NM_2D = lambda: L("論文の平面 2 次元計算(静水圧)", "2D model of the paper (hydrostatic)")
NM_3D = lambda: L("論文の 3 次元計算", "3D model of the paper")


def top_legend(fig, y, ncol=4):
    """図の全パネルの系列を、重複を除いて図の上に 1 つの凡例にまとめる(理論・論文の計算・ENCflow・実験の順)"""
    order = [NM_TH(), NM_2D(), NM_3D(), NM_H(), NM_NH(), NM_E19(), NM_E21()]; seen = {}
    for ax in fig.axes:
        for h, lb in zip(*ax.get_legend_handles_labels()):
            seen.setdefault(lb, h)
    labels = [lb for lb in order if lb in seen] + [lb for lb in seen if lb not in order]
    fig.legend([seen[lb] for lb in labels], labels, loc="lower center", bbox_to_anchor=(0.5, y), ncol=ncol, fontsize=8, frameon=False)


def sec_marks(ax, y, smax=1.25):
    """横軸 s/Lm の図に、偏角が 0 の断面(湾曲の頂点)を薄い縦線で入れる"""
    for x in (0.5, 1.0):
        if x <= smax: ax.axvline(x, color="#cfcfcf", lw=0.8, ls=":")


# ---------------------------------------------------------------- 表
def table1():
    print(L("表 1  段波の理論値(湿潤床のダム破壊の解。h0 = %.3f m、g = %.1f m/s2)", "Table 1  Theoretical bore (wet-bed dam break; h0 = %.3f m, g = %.1f m/s2)") % (H0, G))
    print("  %-10s %7s %8s %8s %9s %8s %7s" % ("bore", "h1 (m)", "hm (m)", "um (m/s)", "c (m/s)", "h_t (m)", "F"))
    for b in ("bk", "ub"):
        hm, um, sb = stoker(H0, H1[b])
        print("  %-10s %7.3f %8.4f %8.4f %9.4f %8.4f %7.3f" % (BORE[b], H1[b], hm, um, sb, hm - H1[b], sb / math.sqrt(G * H1[b])))
    print()


def table2(runs):
    sm = data("k2019_fig2_fig3_section_mean.csv")
    print(L("表 2  蛇行度 1.10 の水路の断面平均波高(断面の 5 点の平均)。到達 = 波高 0.5 を横切る無次元時刻、平均 = 理論の到達の 1.0 後から"
            "実験値の終わりまでの平均、山 = 最初の山の高さ",
            "Table 2  Section-mean wave height in the S = 1.10 flume (mean of 5 points). arrival = dimensionless time of crossing 0.5; "
            "mean = average from 1.0 after the theoretical arrival to the end of the measured series; peak = height of the first crest"))
    print("  %-9s %3s | %7s %7s %7s | %7s %8s | %7s %8s" % ("run", "sec", "arr_th", "arr_exp", "arr_cal", "mean_ex", "mean_cal", "peak_ex", "peak_cal"))
    for name in ("bk_h", "ub_h", "ub_nh"):
        if name not in runs: continue
        r = runs[name]
        for sec in (1, 4, 8):
            te, ee = series(sm, "tstar", "eta", bore=BORE[r.bore], section=sec)
            ii = r.idx("sec", sec); em = r.eta[ii].mean(axis=0)
            ath = r.s[ii[0]] / r.sb * math.sqrt(G / H0)
            w_e = te >= ath + 1.0; w_c = (r.ts >= ath + 1.0) & (r.ts <= te[-1])
            print("  %-9s %3d | %7.2f %7.2f %7.2f | %7.3f %8.3f | %s %s" % (
                name, sec, ath, cross(te, ee), cross(r.ts, em), ee[w_e].mean(), em[w_c].mean(),
                fnum(first_peak(te, ee)[1], "%7.3f"), fnum(first_peak(r.ts, em)[1], "%8.3f")))
    print()


def transverse(r, sec, te, ee):
    """断面 sec の 5 点の、断面平均からの偏差の時間平均。平均する時間は、断面平均波高が 0.5 を横切る時刻(到達)から、
    実験値の時系列の「到達から終わりまで」と同じ長さ(到達の時刻のずれが平均に入らないようにする)。左岸からの距離 / B と偏差"""
    ii = r.idx("sec", sec); em = r.eta[ii].mean(axis=0)
    ta = cross(r.ts, em); w = (r.ts >= ta) & (r.ts <= ta + te[-1] - cross(te, ee))
    e = r.eta[ii][:, w]
    return 0.5 - r.n[ii] / r.B, (e - e.mean(axis=0)).mean(axis=1)


def table3(runs):
    sm = data("k2019_fig2_fig3_section_mean.csv"); tr = data("k2019_fig4_fig5_transverse.csv")
    print(L("表 3  蛇行度 1.10 の水路の、断面平均からの偏差の時間平均(左岸から 0.02 m と 0.78 m の点。計算は、断面平均波高が 0.5 を横切る時刻から、実験値の時系列の同じ区間と同じ長さの平均)",
            "Table 3  Time-mean deviation from the section mean in the S = 1.10 flume (points 0.02 m and 0.78 m from the left bank; "
            "the computed values are averaged from the time the section mean crosses 0.5 over the same duration as that part of the measured series)"))
    print("  %-9s %3s | %8s %8s %8s | %8s %8s %8s" % ("run", "sec", "L_exp", "L_ana", "L_cal", "R_exp", "R_ana", "R_cal"))
    for name in ("bk_h", "ub_h", "ub_nh"):
        if name not in runs: continue
        r = runs[name]
        for sec in (1, 4, 8):
            te, ee = series(sm, "tstar", "eta", bore=BORE[r.bore], section=sec)
            xe, de = series(tr, "n_over_B", "dev", bore=BORE[r.bore], section=sec, series="exp")
            xa, da = series(tr, "n_over_B", "dev", bore=BORE[r.bore], section=sec, series="analytical")
            xc, dc = transverse(r, sec, te, ee); o = np.argsort(xc)
            print("  %-9s %3d | %+8.3f %+8.3f %+8.3f | %+8.3f %+8.3f %+8.3f" % (
                name, sec, de[0], np.interp(0.025, xa, da), dc[o][0], de[-1], np.interp(0.975, xa, da), dc[o][-1]))
    print()


def bank_at(r, side, sec, fn):
    i = [k for k in r.idx(side) if abs(r.s[k] - sec * r.Lm / 8) < 1e-6][0]
    return fn(i)


def bank_scatter(r, side):
    """岸沿いの点列(Lm / 80 ごと)の最大波高の、隣り合う 5 点の中央値からのずれの (中央値, 最大, 0.1 を超える点の数, 点の数)"""
    v = np.array([r.wmax(i) for i in r.idx(side) if r.s[i] <= 1.06 * r.Lm])
    d = np.abs([v[k] - np.median(v[max(k - 2, 0):k + 3]) for k in range(len(v))])
    return np.median(d), d.max(), int((d > 0.1).sum()), len(d)


def peak_width(r, i):
    """最大波高の山の幅 (s): 上流端の影響が届くまでの最大の前後で、最大と 1.0 の中間の高さを超えている時間"""
    w = r.t <= r.tend(i); e = r.eta[i][w]; k = int(np.argmax(e)); lev = 0.5 * (e[k] + 1.0)
    a = k
    while a > 0 and e[a - 1] > lev: a -= 1
    b = k
    while b < len(e) - 1 and e[b + 1] > lev: b += 1
    return r.t[b] - r.t[a] + (r.t[1] - r.t[0])


def table4(runs, names=("bk_h", "ub_h", "ub_nh"), title=True):
    mx = data("k2019_fig8_max_height.csv"); keep = {}
    if title:
        print(L("表 4  蛇行度 1.10 の水路の両岸(岸から 0.02 m)の最大波高(上流端の影響が届くまでの最大)。断面 1〜8。bias = 計算 − 実験の平均、"
                "外岸 = 断面 1・2・7・8 は右岸、3〜6 は左岸",
                "Table 4  Maximum wave height along both banks (0.02 m from the wall) of the S = 1.10 flume, before the upstream influence arrives; "
                "sections 1-8. bias = mean of computed - measured; outer bank = right at sections 1, 2, 7, 8 and left at 3-6"))
    for name in names:
        if name not in runs: continue
        r = runs[name]; he = {}; hc = {}
        for bank in ("left", "right"):
            he[bank] = series(mx, "s_over_L", "hmax", bore=BORE[r.bore], bank=bank)[1]
            hc[bank] = np.array([bank_at(r, bank, k, r.wmax) for k in range(1, 9)])
        ob = ["right" if k in (0, 1, 6, 7) else "left" for k in range(8)]; ib = ["left" if k in (0, 1, 6, 7) else "right" for k in range(8)]
        print("  %-10s %-11s" % (name, "sec") + " ".join("%5d" % k for k in range(1, 9)) + "   bias   RMSE")
        for lab, bk in (("outer", ob), ("inner", ib)):
            e = np.array([he[bk[k]][k] for k in range(8)]); c = np.array([hc[bk[k]][k] for k in range(8)]); ok = np.isfinite(c)
            print("  %-10s %-11s" % ("", lab + " exp") + " ".join("%5.2f" % v for v in e))
            print("  %-10s %-11s" % ("", lab + " calc") + " ".join(fnum(v, "%5.2f") for v in c) +
                  "  %+5.2f  %5.2f" % ((c - e)[ok].mean(), math.sqrt(((c - e)[ok] ** 2).mean())))
            keep[name, lab] = (e, c)
        if title and not np.isnan([r.wmax(i) for i in r.idx("left") if r.s[i] <= 1.06 * r.Lm]).any():
            sl = bank_scatter(r, "left"); sr = bank_scatter(r, "right")
            print("  %-10s " % "" + L("岸沿いの点列(蛇行長の 1/80 ごと)の、隣り合う 5 点の中央値からのずれ(中央値 / 最大 / 0.1 を超える点の数): "
                                      "左岸 %.2f / %.2f / %d (%d 点中)、右岸 %.2f / %.2f / %d (%d 点中)",
                                      "scatter along a bank (points every 1/80 of the meander length; deviation from the median of 5 neighbours, "
                                      "median / maximum / number of points above 0.1): left %.2f / %.2f / %d (of %d), right %.2f / %.2f / %d (of %d)") % (sl + sr))
            if r.model == "h":
                wd = [bank_at(r, ob[k - 1], k, lambda i: peak_width(r, i)) for k in range(1, 9)]
                print("  %-10s " % "" + L("外岸の最大の山の幅(最大と 1.0 の中間を超えている時間。断面 1〜8 の中央値): %.2f s",
                                          "width of the peak at the outer bank (time above the midpoint between the maximum and 1.0; median of sections 1-8): %.2f s") % np.median(wd))
    if title and ("ub_h", "outer") in keep and ("ub_nh", "outer") in keep:
        n = sum(int(np.sum((keep["ub_h", lab][1] <= keep["ub_h", lab][0]) & (keep["ub_h", lab][0] <= keep["ub_nh", lab][1]))) for lab in ("outer", "inner"))
        print(L("  波状段波: 静水圧の計算 ≤ 計測 ≤ 非静水圧の計算 が成り立つ点: 16 点のうち %d 点", "  Undular bore: points with hydrostatic <= measured <= non-hydrostatic: %d of 16") % n)
    print()
    return keep


def wall_rows(run, t_out, nrow=4):
    """直線水路の、時刻 t_out (s) の先頭の山の高さの、壁から 1〜nrow 行目と中央の行の比(まっすぐな水路では 1 になるはずの量)。
    山は、中央の行を下流から見て最初に波高 0.3 を超える所から上流へたどった最初の極大。各行は、その列の前後 0.3 m の最大"""
    img, ext = level_map(run, t_out); rows = np.where(np.isfinite(img).any(axis=1))[0]; c = img[rows[len(rows) // 2]]
    k = int(np.where(np.nan_to_num(c) > 0.3)[0].max())
    while c[k - 1] >= c[k]: k -= 1
    n = int(round(0.3 / float(run.par["dx"])))
    v = np.nanmax(img[rows][:, k - n:k + n + 1], axis=1)
    return v[:nrow] / v[len(rows) // 2]


def table5(runs):
    fw = data("k2021_fig4_first_wave.csv")
    print(L("表 5  波状段波の第 1 波の波高(最初の山の高さ)。小林ら (2021) の Section 1・3・4・5・7・8。直線水路は水路の中央、蛇行水路は岸から 0.02 m。"
            "「岸/中央」は、直線水路の岸から 0.02 m の点と中央の第 1 波の波高の比、「壁から 1〜4 行目/中央」は、水位の分布の先頭の山の高さの比",
            "Table 5  Height of the first wave of the undular bore at Sections 1, 3, 4, 5, 7, 8 of Kobayashi et al. (2021); "
            "channel centre for the straight flume, 0.02 m from the wall for the meandering flumes. "
            "bank/centre = ratio of the first-wave height 0.02 m from the wall to that at the centre of the straight flume; "
            "rows 1-4 from the wall/centre = ratio of the height of the leading crest in the level maps"))
    print("  %-22s " % "" + " ".join("%6d" % k for k in SECS21) + "   mean   bias   RMSE"); mean = {}; nin = 0; nall = 0
    for ch, key, sides in (("str", "straight_LmS125", ("center",)), ("s125", "S125", ("outer", "inner")), ("s110", "S110", ("outer", "inner"))):
        for side in sides:
            ser = key if ch == "str" else f"{key}_{side}"
            _, he = series(fw, "s_over_Lm", "h1st", series=ser)
            print("  %-22s " % (ser + " exp") + " ".join("%6.2f" % v for v in he) + " %6.2f" % he.mean()); mean[ch, side, "exp"] = he.mean(); hcs = {}
            for m in ("h", "nh"):
                name = ("ub" if ch == "s110" else ch) + "_" + m
                if name not in runs: continue
                r = runs[name]; ii = r.bank(side)
                hc = np.array([r.wave1([i for i in ii if abs(r.s[i] - k * r.Lm / 8) < 1e-6][0]) for k in SECS21])
                print("  %-22s " % ("  " + name) + " ".join("%6.2f" % v for v in hc) + " %6.2f  %+5.2f  %5.2f" % (hc.mean(), (hc - he).mean(), math.sqrt(((hc - he) ** 2).mean())))
                mean[ch, side, m] = hc.mean(); hcs[m] = hc
                if ch == "str":     # 直線水路の岸から 0.02 m の点と中央の比(まっすぐな水路では 1 になるはずの量)
                    rat = [r.wave1(r.idx("sec", k)[0]) / r.wave1(r.idx("sec", k)[2]) for k in SECS21]
                    print("  %-22s " % ("  " + name + L(" 岸/中央", " bank/centre")) + " ".join("%6.3f" % v for v in rat))
                    print("  %-22s " % ("  " + name + L(" 壁から 1〜4 行目/中央", " rows 1-4 from the wall/centre")) +
                          ";  ".join("t = %.0f s: " % t + " ".join("%.3f" % v for v in wall_rows(r, t)) for t in (2.0, 4.0, 6.0)))
            if len(hcs) == 2:
                ok = (hcs["h"] <= he) & (he <= hcs["nh"]); nin += int(ok.sum()); nall += len(he)
                print("  %-22s " % L("  間に入る点", "  between the runs") + " ".join("%6s" % ("o" if v else "x") for v in ok))
    if nall:
        print(L("  静水圧の計算 ≤ 計測 ≤ 非静水圧の計算 が成り立つ点: %d 点のうち %d 点" % (nall, nin),
                "  Points with hydrostatic <= measured <= non-hydrostatic: %d of %d" % (nin, nall)))
    if all((ch, sd, m) in mean for ch, sd in (("str", "center"), ("s125", "outer"), ("s110", "outer")) for m in ("exp", "h", "nh")):
        print(L("  外岸の第 1 波の波高の、直線水路(中央)に対する比(6 断面の平均どうし)", "  Ratio of the first-wave height at the outer bank to that in the straight flume (centre); means of the six sections"))
        for m, nm in (("exp", NM_EXP()), ("h", NM_H()), ("nh", NM_NH())):
            print("  %-22s " % ("  " + nm) + L("蛇行度 1.25: %.2f、蛇行度 1.10: %.2f", "S = 1.25: %.2f, S = 1.10: %.2f") % (
                mean["s125", "outer", m] / mean["str", "center", m], mean["s110", "outer", m] / mean["str", "center", m]))
    print()


def table6(runs):
    d6 = data("k2021_fig6_sec4_outer.csv")
    print(L("表 6  蛇行度 1.10 の水路の Section 4 の外岸(左岸から 0.02 m)の波状段波の波形: 山と谷の無次元時刻と波高",
            "Table 6  Undular bore at the outer bank of Section 4 (0.02 m from the left wall) of the S = 1.10 flume: dimensionless times and heights of crests and troughs"))
    te, ee = series(d6, "tstar", "eta", channel="S110", series="exp")
    rows = [(NM_EXP(), extrema(te, ee, 4))]
    for nm, ser in ((L("論文の 3 次元計算", "3D model of the paper"), "calc3d"),):
        t3, e3 = series(d6, "tstar", "eta", channel="S110", series=ser); rows.append((nm, extrema(t3, e3, 4)))
    for name in ("ub_nh", "ub_nh_r30", "ub_nh_d4", "ub_nh_d1"):
        if name in runs:
            r = runs[name]; i = r.idx("sec", 4)[-1]; rows.append((name, extrema(r.ts, r.eta[i], 4)))
    for nm, ex in rows:
        print("  %-22s " % nm + "  ".join("%6.2f:%5.2f" % (t, v) for t, v in ex) +
              ("   period %.2f" % (ex[2][0] - ex[0][0]) if len(ex) > 2 else ""))
    t2, e2 = series(d6, "tstar", "eta", channel="S110", series="calc2d")
    print("  " + L("静水圧の段波の到達(波高 0.5): 論文の平面 2 次元計算 %.2f", "arrival of the hydrostatic bore (height 0.5): 2D model of the paper %.2f") % cross(t2, e2), end="")
    print(L("(最初の山 %.2f)", " (first peak %.2f)") % first_peak(t2, e2)[1], end="")
    if "ub_h" in runs:
        r = runs["ub_h"]; i = r.idx("sec", 4)[-1]
        print(L("、ENCflow %.2f(最初の山 %.2f)", ", ENCflow %.2f (first peak %.2f)") % (cross(r.ts, r.eta[i]), r.first_peak(i)[1]), end="")
    print()
    # 断面 4 の 5 点の第 1 の山(小林ら 2019 の図-10)
    d10 = data("k2019_fig10_section4.csv"); dist = ("0.02", "0.20", "0.40", "0.60", "0.78"); rows = []; ex = []
    for d in dist:
        t_, e_ = series(d10, "t", "eta", dist_left=d); k = int(np.argmax(e_)); ex.append((t_[k] * math.sqrt(G / H0), e_[k]))
    rows.append((NM_EXP(), ex))
    if "ub_nh" in runs:
        r = runs["ub_nh"]; ii = sorted(r.idx("sec", 4), key=lambda i: -r.n[i])
        rows.append(("ub_nh", [(r.first_peak(i)[0] * math.sqrt(G / H0), r.first_peak(i)[1]) for i in ii]))
    print(L("  断面 4 の 5 点の第 1 の山(左岸 = 外岸からの距離 0.02・0.20・0.40・0.60・0.78 m。無次元時刻: 波高)と、外岸と内岸の時刻の差",
            "  First crest at the five points of section 4 (0.02, 0.20, 0.40, 0.60, 0.78 m from the left = outer bank; dimensionless time: height) "
            "and the time difference between the outer and the inner bank"))
    for nm, ex in rows:
        print("  %-22s " % nm + "  ".join("%6.2f:%5.2f" % v for v in ex) + "   %+.2f" % (ex[0][0] - ex[-1][0]))
    # 直線水路の Section 4(小林ら 2021 の図-2): 静水圧の段波の到達から第 1 の山までの時間と、周期
    f2 = data("k2021_fig2_straight_sec4.csv"); ts2, es2 = series(f2, "tstar", "eta", series="calc2d"); tx, ex_ = series(f2, "tstar", "eta", series="exp")
    x = extrema(tx, ex_, 3)
    print(L("  直線水路の Section 4: 静水圧の段波の到達(波高 0.5)から第 1 の山までの無次元時間 / 山から山までの周期。計測(到達は論文の平面 2 次元計算) %+.2f / %.2f",
            "  Section 4 of the straight flume: dimensionless time from the arrival of the hydrostatic bore (height 0.5) to the first crest / crest-to-crest period. "
            "measured (arrival from the 2D model of the paper) %+.2f / %.2f") % (x[0][0] - cross(ts2, es2), x[2][0] - x[0][0]), end="")
    if "str_h" in runs and "str_nh" in runs:
        rh = runs["str_h"]; rn = runs["str_nh"]; i4 = [i for i in rh.idx("center") if abs(rh.s[i] - 4.03) < 1e-6][0]
        x = extrema(rn.ts, rn.eta[i4], 3)
        print(L("、ENCflow %+.2f / %.2f", ", ENCflow %+.2f / %.2f") % (x[0][0] - cross(rh.ts, rh.eta[i4]), x[2][0] - x[0][0]))
        # 先頭の進む速さ: 静水圧は波高 0.5 の到達、非静水圧は第 1 の山。Section 1 → 4 と 4 → 8 の区間
        ii = rh.bank("center"); sel = [[i for i in ii if abs(rh.s[i] - k * rh.Lm / 8) < 1e-6][0] for k in (1, 4, 8)]
        th = [cross(rh.t, rh.eta[i]) for i in sel]; tn = [rn.first_peak(i)[0] for i in sel]; ss = [rh.s[i] for i in sel]
        vh = [(ss[k + 1] - ss[k]) / (th[k + 1] - th[k]) for k in (0, 1)]; vn = [(ss[k + 1] - ss[k]) / (tn[k + 1] - tn[k]) for k in (0, 1)]
        print(L("  直線水路の先頭の速さ (m/s。Section 1 → 4 / 4 → 8): 理論の段波 %.3f、静水圧(波高 0.5 の到達)%.3f / %.3f、非静水圧(第 1 の山)%.3f / %.3f",
                "  Straight flume, speed of the front (m/s; Sections 1 -> 4 / 4 -> 8): theoretical bore %.3f, hydrostatic (arrival at height 0.5) %.3f / %.3f, "
                "non-hydrostatic (first crest) %.3f / %.3f") % (rh.sb, vh[0], vh[1], vn[0], vn[1]), end="")
    print("\n")


def breaking_cells(name):
    """画面出力の末尾から、砕波スイッチが静水圧にしたセルの数の平均(非静水圧の計算でなければ -)"""
    fn = os.path.join(HERE, f"Screen_{name}.log")
    if os.path.exists(fn):
        with open(fn) as f:
            for ln in f:
                if "breaking cells avg" in ln: return ln.split("breaking cells avg")[1].split(",")[0].strip()
    return "-"


def max_slope(run, t_out):
    """直線水路の中央の行の、時刻 t_out (s) の水面勾配の最大(砕波スイッチの判定は、水面勾配が 0.3 を超えること)"""
    img, ext = level_map(run, t_out); ok = np.where(np.isfinite(img).any(axis=1))[0]
    e = img[ok[len(ok) // 2]]; e = e[np.isfinite(e)] * run.ht
    return np.abs(np.diff(e)).max() / float(run.par["dx"])


def table7(runs):
    names = ("bk_h", "bk_h_c1", "bk_h_r30", "bk_h_d4", "bk_h_d1", "bk_nh", "ub_nh", "ub_nh_r30", "ub_nh_d4", "ub_nh_d1")
    if not any(n in runs for n in SENS): return
    print(L("表 7  感度の構成。bk_h_c1 = エッジ水深が既定(f_hcap_upwind = 1)、_r30 = 格子に対して水路を 30° 回した配置、_d4 = 4 cm 格子、"
            "_d1 = 1 cm 格子(3.7 s まで。断面 1〜4)、bk_nh = 砕波段波の非静水圧。蛇行度 1.10 の水路の両岸の最大波高は表 4 と同じ集計"
            "(- は、その断面の時間の範囲まで計算していない)",
            "Table 7  Sensitivity runs. bk_h_c1 = default edge depth (f_hcap_upwind = 1), _r30 = flume rotated by 30 deg against the grid, "
            "_d4 = 4 cm grid, _d1 = 1 cm grid (to 3.7 s; sections 1-4), bk_nh = breaking bore, non-hydrostatic. "
            "Bank maxima in the S = 1.10 flume: same statistics as Table 4 (- = not computed up to the time window of that section)"))
    keep = table4(runs, names=names, title=False)
    print(L("  両岸の最大波高の、2 cm 格子の構成(bk_h・ub_nh)との差(計算した断面の、外岸と内岸の点。平均 / 絶対値の最大)",
            "  Difference of the bank maxima from the 2 cm runs (bk_h, ub_nh) at the outer and inner points of the computed sections (mean / maximum absolute)"))
    for name in names:
        base = name[:5] if name.startswith("ub_nh") else "bk_h"
        if name == base or (name, "outer") not in keep or (base, "outer") not in keep: continue
        d = np.concatenate([keep[name, lab][1] - keep[base, lab][1] for lab in ("outer", "inner")]); d = d[np.isfinite(d)]
        print("  %-10s %+.2f / %.2f  (%d %s)" % (name, d.mean(), np.abs(d).max(), len(d), L("点", "points")))
    print(L("  断面平均波高の到達(波高 0.5 を横切る無次元時刻。断面 1・4・8)と最初の山(断面 4)、Section 4 の外岸の第 1 波(時刻: 波高。"
            "波列のない計算は、到達から 1 周期の間の最大)と、その外岸の周期",
            "  Arrival of the section-mean height (dimensionless time of crossing 0.5; sections 1, 4, 8) and its first crest (section 4); "
            "first wave at the outer bank of Section 4 (time: height; for runs without a wave train, the maximum within one period after arrival) "
            "and the period there"))
    for name in names:
        if name not in runs: continue
        r = runs[name]; i4 = r.idx("sec", 4)[-1]; tp, hp = r.first_peak(i4); per = float("nan")
        if r.model != "nh": hp = r.wave1(i4); tp = r.t[int(np.argmax(r.eta[i4] >= hp - 1e-12))] if hp == hp else float("nan")
        else:
            ex = extrema(r.ts, r.eta[i4], 3); per = ex[2][0] - ex[0][0] if len(ex) > 2 else float("nan")
        em4 = r.eta[r.idx("sec", 4)].mean(axis=0)
        print("  %-10s " % name + " ".join(fnum(cross(r.ts, r.eta[r.idx("sec", k)].mean(axis=0)), "%6.2f") for k in (1, 4, 8)) +
              "   %s   %s: %s   %s" % (fnum(first_peak(r.ts, em4)[1], "%5.2f"), fnum(tp * math.sqrt(G / H0), "%6.2f"), fnum(hp, "%5.2f"), fnum(per, "%5.2f")))
    if any(n in runs for n in ("str_nhb", "str_nhb2", "str_nh_s", "str_nhb_s")):
        fw = data("k2021_fig4_first_wave.csv"); _, he = series(fw, "s_over_Lm", "h1st", series="straight_LmS125")
        print(L("  直線水路の第 1 波の波高(Section 1・3・4・5・7・8。砕波スイッチなしの非静水圧は最初の山、ほかは到達から 1 周期の間の最大)と、"
                "Section 4 の到達(波高 0.5)、砕波スイッチが静水圧にしたセルの数の平均(有効セル 15760)。str_nhb = 非静水圧 + 砕波スイッチ"
                "(既定の判定と縁)、str_nhb2 = 同(縁 2 セル)、_s = 初期水位の段差を tanh(s / 0.3 m) のなだらかな水面にした計算",
                "  Straight flume: height of the first wave (Sections 1, 3, 4, 5, 7, 8; first crest for the non-hydrostatic runs without the breaking "
                "switch, maximum within one period after arrival for the others), arrival at Section 4 (height 0.5) and the mean number of cells "
                "made hydrostatic by the breaking switch (15760 valid cells). str_nhb = non-hydrostatic + breaking switch (default criterion and "
                "margin), str_nhb2 = same with a margin of 2 cells, _s = initial step smoothed to tanh(s / 0.3 m)"))
        print("  %-10s " % L("実験", "experiment") + " ".join("%6.2f" % v for v in he))
        for name in ("str_h", "str_nh", "str_nhb", "str_nhb2", "str_nh_s", "str_nhb_s"):
            if name not in runs: continue
            r = runs[name]; ii = r.bank("center")
            sel = [[i for i in ii if abs(r.s[i] - k * r.Lm / 8) < 1e-6][0] for k in SECS21]
            print("  %-10s " % name + " ".join(fnum(r.wave1(i), "%6.2f") for i in sel) + "   %s   %s" % (
                fnum(cross(r.ts, r.eta[sel[2]]), "%6.2f"), breaking_cells(name)))
        tsl = (0.5, 1.0, 1.5, 2.0, 2.5, 4.0, 6.5)
        print(L("  直線水路の中央の行の水面勾配の最大(砕波スイッチの判定は 0.3)。t = ", "  Straight flume: maximum surface slope along the centre row "
                "(the breaking switch acts above 0.3). t = ") + ", ".join("%.1f" % t for t in tsl) + " s" +
              L("、最後の列は 2.5 s から 6.5 s までの 0.5 s ごとの最小", "; last column = minimum of the values every 0.5 s from 2.5 s to 6.5 s"))
        for name in ("str_h", "str_nh", "str_nhb", "str_nh_s", "str_nhb_s"):
            if name not in runs: continue
            print("  %-10s " % name + " ".join("%6.2f" % max_slope(runs[name], t) for t in tsl) +
                  "   %6.2f" % min(max_slope(runs[name], t) for t in np.arange(2.5, 6.51, 0.5)))
    print()


# ---------------------------------------------------------------- 図
def fig_setup():
    fig = plt.figure(figsize=(11, 6.6))
    gs = fig.add_gridspec(3, 4, height_ratios=[4.2, 2.9, 1.0], hspace=0.5, wspace=0.3)
    axs = [fig.add_subplot(gs[0, 0:3]), fig.add_subplot(gs[1, 0:3]), fig.add_subplot(gs[2, 0:3])]
    info = (("s110", L("(a) 蛇行度 1.10 の水路(幅 0.80 m、蛇行長 7.50 m、最大偏角 35°、勾配 1/600)。上流水槽つき",
                       "(a) S = 1.10 flume (width 0.80 m, meander length 7.50 m, maximum angle 35 deg, slope 1/600), with the upstream tank")),
            ("s125", L("(b) 蛇行度 1.25 の水路(幅 0.39 m、蛇行長 8.06 m、最大偏角 53°、勾配 0)",
                       "(b) S = 1.25 flume (width 0.39 m, meander length 8.06 m, maximum angle 53 deg, slope 0)")),
            ("str", L("(c) 直線水路(幅 0.40 m、勾配 0)", "(c) Straight flume (width 0.40 m, slope 0)")))
    for ax, (tag, ttl) in zip(axs, info):
        pp = read_probes(tag)
        if pp is None: continue
        par, rows = pp
        mask = np.loadtxt(os.path.join(HERE, f"mask_{tag}.txt")); dx = float(par["dx"]); x0 = float(par["x0"]); y0 = float(par["y0"])
        ny, nx = mask.shape; xc = x0 + (np.arange(nx) + 0.5) * dx
        img = np.where(mask > 0, np.where(xc[None, :] < 0, 2.0, 1.0), np.nan)     # 濃い色 = ゲートの上流(水深 h0)
        ax.imshow(img, extent=[x0, x0 + nx * dx, y0, y0 + ny * dx], cmap=SEQ, vmin=0.0, vmax=4.0, interpolation="nearest")
        B = float(par["B"]); ax.plot([0, 0], [-B / 2, B / 2], color=C_EXP, lw=2.5)
        ax.text(-0.08 if tag == "str" else 0.0, B / 2 + 0.12, L("ゲート", "gate"), ha="right" if tag == "str" else "center", va="bottom", fontsize=8)
        for k in range(1, 9):
            xs, ys = zip(*[(px + x0, py + y0) for px, py in gauge_xy(rows, "sec", k)])
            ax.plot(xs, ys, color=C_EXP, lw=0.7); ax.plot(xs, ys, "o", color=C_EXP, ms=2.2)
            dxn = xs[-1] - xs[0]; dyn = ys[-1] - ys[0]; nrm = math.hypot(dxn, dyn)
            ax.text(xs[-1] + 0.2 * dxn / nrm, ys[-1] + 0.2 * dyn / nrm, str(k), ha="center", va="center", fontsize=8)
        ax.set_aspect("equal"); ax.set_title(ttl, fontsize=9.5, loc="left", pad=17 if tag == "str" else 6)
        ax.set_xlim(-3.1, 17.5); ax.set_ylabel("y (m)")
        for sp in ("top", "right"): ax.spines[sp].set_visible(False)
        if tag == "s110":
            ax.text(-2.25, 0.72, L("上流水槽", "upstream\ntank"), ha="center", va="center", fontsize=8)
            ax.text(-0.75, -0.72, L("水深 0.285 m", "depth 0.285 m"), ha="center", va="center", fontsize=8)
            ax.text(2.6, -0.72, L("水深 0.107 m(砕波段波)または 0.147 m(波状段波)", "depth 0.107 m (breaking bore) or 0.147 m (undular bore)"),
                    ha="left", va="center", fontsize=8)
            ax.text(15.0, 0.0, L("下流端(壁)", "downstream\nend (wall)"), ha="left", va="center", fontsize=8)
        if tag == "str": ax.set_yticks([0.0])
    axs[2].set_xlabel(L("x (m)。ゲートが 0", "x (m); gate at 0"))
    # 側壁の階段の拡大(蛇行度 1.10 の水路の Section 2 の左岸 = 偏角が最大の所)。黒い線は設計上の側壁の位置
    ax = fig.add_subplot(gs[0:2, 3]); pp = read_probes("s110")
    if pp is not None:
        par, rows = pp
        mask = np.loadtxt(os.path.join(HERE, "mask_s110.txt")); dx = float(par["dx"]); x0 = float(par["x0"]); y0 = float(par["y0"]); ny, nx = mask.shape
        p = [(px + x0, py + y0) for px, py in gauge_xy(rows, "sec", 2)]
        cx, cy = p[-1]
        ax.imshow(np.where(mask > 0, 1.0, np.nan), extent=[x0, x0 + nx * dx, y0, y0 + ny * dx], cmap=SEQ, vmin=0.0, vmax=4.0, interpolation="nearest")
        for v in np.arange(x0, x0 + nx * dx + dx / 2, dx): ax.axvline(v, color="#ffffff", lw=0.6)
        for v in np.arange(y0, y0 + ny * dx + dx / 2, dx): ax.axhline(v, color="#ffffff", lw=0.6)
        sys.path.insert(0, HERE)
        import make_init as mi
        c = mi.CHANNELS["s110"]; s_, X_, Y_, th_ = mi.centerline(c)
        ax.plot(X_ - 0.5 * c["B"] * np.sin(th_), Y_ + 0.5 * c["B"] * np.cos(th_), color=C_EXP, lw=1.2)
        ax.plot(cx, cy, "o", color=C_EXP, ms=5.5)
        gl = [int(r["gauge"]) for r in rows if r["kind"] == "sec" and int(r["section"]) == 2][-1]
        pp2 = [(float(r["x"]) + x0, float(r["y"]) + y0) for r in rows if int(r["gauge"]) == gl]
        ax.plot([q[0] for q in pp2], [q[1] for q in pp2], "o", color=C_EXP, ms=3.5, mfc="white", mew=0.9)
        ax.text(cx + 0.02, cy - 0.02, L("岸から 0.02 m の測定点\n(白丸のセル中心の\nプローブから補間)", "gauge 0.02 m from\nthe wall (interpolated\nfrom the probes at the\ncell centres, open circles)"),
                ha="left", va="top", fontsize=8)
        ax.set_xlim(cx - 0.13, cx + 0.13); ax.set_ylim(cy - 0.17, cy + 0.12); ax.set_aspect("equal")
        ax.set_title(L("(d) 側壁の階段(2 cm 格子)", "(d) Staircase wall (2 cm grid)"), fontsize=9.5, loc="left")
        ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
        for sp in ("top", "right"): ax.spines[sp].set_visible(False)
    fig.savefig(os.path.join(FIGS, "setup.png"), dpi=130, bbox_inches="tight"); plt.close(fig)


def fig_surface(runs):
    if "ub_h" not in runs or "ub_nh" not in runs: return
    times = (2.5, 5.0)
    fig, axs = plt.subplots(2, 2, figsize=(11, 3.75), sharex=True, sharey=True, constrained_layout=True)
    for j, name in enumerate(("ub_h", "ub_nh")):
        for i, tt in enumerate(times):
            ax = axs[i, j]; img, ext = level_map(runs[name], tt)
            im = ax.imshow(img, extent=ext, cmap=SEQ, vmin=0.0, vmax=2.6, interpolation="nearest")
            ax.set_xlim(-1.5, 10.6); ax.set_ylim(-0.75, 2.05); ax.set_aspect("equal")      # 上流水槽(x < -1.5 m)は描かない
            ax.set_title("%s   t = %.1f s" % ((NM_H(), NM_NH())[j], tt), fontsize=9.5, loc="left")
            for sp in ("top", "right"): ax.spines[sp].set_visible(False)
            if j == 0: ax.set_ylabel("y (m)")
            if i == 1: ax.set_xlabel("x (m)")
    cb = fig.colorbar(im, ax=axs, shrink=0.9, pad=0.015); cb.set_label(LB_E()); cb.outline.set_visible(False)
    fig.savefig(os.path.join(FIGS, "surface.png"), dpi=130, bbox_inches="tight"); plt.close(fig)


def panel_secmean(ax, runs, names, bore, sec):
    sm = data("k2019_fig2_fig3_section_mean.csv")
    te, ee = series(sm, "tstar", "eta", bore=BORE[bore], section=sec)
    ath = None
    for name in names:
        if name not in runs: continue
        r = runs[name]; ii = r.idx("sec", sec); col = C_H if r.model == "h" else C_NH
        ax.plot(r.ts, r.eta[ii].mean(axis=0), color=col, lw=1.8, label=NM_H() if r.model == "h" else NM_NH())
        ath = r.s[ii[0]] / r.sb * math.sqrt(G / H0); tnd = r.tend(ii[0]) * math.sqrt(G / H0)
    if ath is not None:
        ax.plot([ath - 4, ath, ath, tnd], [0, 0, 1, 1], color=C_TH, lw=1.0, ls="--", label=NM_TH())
        ax.axvline(tnd, color="#cfcfcf", lw=0.8, ls=":")
        ax.set_xlim(ath - 2.2, tnd + 2.5)
    ax.plot(te, ee, "o", color=C_EXP, ms=2.6, label=NM_E19())
    ax.set_ylim(-0.1, 2.05)
    style(ax, LB_T(), LB_E() if sec == 1 else None, L("断面 %d の断面平均波高", "Section %d: section-mean wave height") % sec)


def panel_transverse(ax, runs, names, bore, sec):
    sm = data("k2019_fig2_fig3_section_mean.csv"); tr = data("k2019_fig4_fig5_transverse.csv")
    te, ee = series(sm, "tstar", "eta", bore=BORE[bore], section=sec)
    xa, da = series(tr, "n_over_B", "dev", bore=BORE[bore], section=sec, series="analytical")
    ax.plot(xa, da, color=C_TH, lw=1.0, ls="--", label=NM_TH())
    for name in names:
        if name not in runs: continue
        r = runs[name]; xc, dc = transverse(r, sec, te, ee); o = np.argsort(xc); col = C_H if r.model == "h" else C_NH
        ax.plot(xc[o], dc[o], "-", color=col, lw=1.8, marker="s", ms=4, label=NM_H() if r.model == "h" else NM_NH())
    xe, de = series(tr, "n_over_B", "dev", bore=BORE[bore], section=sec, series="exp")
    ax.plot(xe, de, "o", color=C_EXP, ms=5.5, label=NM_E19())
    ax.set_ylim(-0.42, 0.42); ax.set_xlim(-0.03, 1.03)
    style(ax, L("左岸からの距離 / 水路幅", "distance from the left bank / width"),
          L("偏差の時間平均 / ", "time-mean deviation / ") + r"$h_t$" if sec == 1 else None,
          L("断面 %d の横断分布", "Section %d: transverse profile") % sec)


def panel_bankmax(ax, runs, names, bore, bank):
    mx = data("k2019_fig8_max_height.csv")
    for name in names:
        if name not in runs: continue
        r = runs[name]; ii = [i for i in r.idx(bank) if r.s[i] <= 1.06 * r.Lm]; col = C_H if r.model == "h" else C_NH
        ax.plot(r.s[ii] / r.Lm, [r.wmax(i) for i in ii], color=col, lw=1.8, label=NM_H() if r.model == "h" else NM_NH())
    se, he = series(mx, "s_over_L", "hmax", bore=BORE[bore], bank=bank)
    ax.plot(se, he, "o", color=C_EXP, ms=5.5, label=NM_E19())
    sec_marks(ax, 0, 1.06); ax.set_xlim(0, 1.07); ax.set_ylim(0.6, 2.45 if bore == "bk" else 3.15)
    style(ax, LB_S(), L("最大波高 / ", "maximum wave height / ") + r"$h_t$" if bank == "left" else None,
          L("左岸沿い(岸から 0.02 m)の最大波高", "Maximum wave height along the left bank (0.02 m from the wall)") if bank == "left" else
          L("右岸沿い(岸から 0.02 m)の最大波高", "Maximum wave height along the right bank (0.02 m from the wall)"))


def fig_breaking(runs):
    if "bk_h" not in runs: return
    fig = plt.figure(figsize=(11, 9.4)); gs = fig.add_gridspec(3, 6, hspace=0.46, wspace=0.9, top=0.93)
    for a, sec in enumerate((1, 4, 8)):
        panel_secmean(fig.add_subplot(gs[0, 2 * a:2 * a + 2]), runs, ("bk_h",), "bk", sec)
        panel_transverse(fig.add_subplot(gs[1, 2 * a:2 * a + 2]), runs, ("bk_h",), "bk", sec)
    panel_bankmax(fig.add_subplot(gs[2, 0:3]), runs, ("bk_h",), "bk", "left")
    panel_bankmax(fig.add_subplot(gs[2, 3:6]), runs, ("bk_h",), "bk", "right")
    top_legend(fig, 0.955, ncol=3)
    fig.savefig(os.path.join(FIGS, "breaking.png"), dpi=130, bbox_inches="tight"); plt.close(fig)


def fig_undular(runs):
    if "ub_h" not in runs or "ub_nh" not in runs: return
    names = ("ub_h", "ub_nh")
    fig = plt.figure(figsize=(11, 12.4)); gs = fig.add_gridspec(4, 6, hspace=0.46, wspace=0.9, top=0.93)
    for a, sec in enumerate((1, 4, 8)):
        panel_secmean(fig.add_subplot(gs[0, 2 * a:2 * a + 2]), runs, names, "ub", sec)
        panel_transverse(fig.add_subplot(gs[2, 2 * a:2 * a + 2]), runs, names, "ub", sec)
    # Section 4 の外岸の時系列(小林ら 2021 の図-6)
    ax = fig.add_subplot(gs[1, 0:4]); d6 = data("k2021_fig6_sec4_outer.csv")
    t2, e2 = series(d6, "tstar", "eta", channel="S110", series="calc2d"); t3, e3 = series(d6, "tstar", "eta", channel="S110", series="calc3d")
    ax.plot(t3, e3, color=C_3D, lw=1.5, label=NM_3D())
    for name in names:
        r = runs[name]; i = r.idx("sec", 4)[-1]; col = C_H if r.model == "h" else C_NH
        ax.plot(r.ts, r.eta[i], color=col, lw=1.8, label=NM_H() if r.model == "h" else NM_NH())
    ax.plot(t2, e2, color=C_2D, lw=1.4, ls=":", label=NM_2D())
    te, ee = series(d6, "tstar", "eta", channel="S110", series="exp")
    ax.plot(te, ee, "o", color=C_EXP, ms=3.2, mfc="none", mew=0.9, label=NM_E21())
    ax.set_xlim(11.5, 26.5); ax.set_ylim(-0.1, 3.15)
    style(ax, LB_T(), LB_E(), L("Section 4 の外岸(左岸から 0.02 m)の波高", "Wave height at the outer bank of Section 4 (0.02 m from the left wall)"))
    # 断面 4 の 5 点の最初の山の高さ(小林ら 2019 の図-10)
    ax = fig.add_subplot(gs[1, 4:6]); d10 = data("k2019_fig10_section4.csv")
    for name in names:
        r = runs[name]; ii = r.idx("sec", 4); col = C_H if r.model == "h" else C_NH
        x = 0.5 * r.B - r.n[ii]; o = np.argsort(x)
        ax.plot(x[o], np.array([r.wave1(i) for i in ii])[o], "-", color=col, lw=1.8, marker="s", ms=4, label=NM_H() if r.model == "h" else NM_NH())
    xe = []; he = []
    for d in ("0.02", "0.20", "0.40", "0.60", "0.78"):
        t_, e_ = series(d10, "t", "eta", dist_left=d); xe.append(float(d)); he.append(e_.max())
    ax.plot(xe, he, "o", color=C_EXP, ms=5.5, label=NM_E19())
    ax.set_ylim(0.6, 3.15); ax.set_xlim(-0.03, 0.83)
    style(ax, L("左岸からの距離 (m)", "distance from the left bank (m)"), L("第 1 波の波高 / ", "first-wave height / ") + r"$h_t$",
          L("断面 4 の 5 点の第 1 波", "First wave at the 5 points of Section 4"))
    panel_bankmax(fig.add_subplot(gs[3, 0:3]), runs, names, "ub", "left")
    panel_bankmax(fig.add_subplot(gs[3, 3:6]), runs, names, "ub", "right")
    top_legend(fig, 0.945, ncol=4)
    fig.savefig(os.path.join(FIGS, "undular.png"), dpi=130, bbox_inches="tight"); plt.close(fig)


def fig_firstwave(runs):
    fw = data("k2021_fig4_first_wave.csv"); f5 = data("k2021_fig5_outer_bank.csv"); f2 = data("k2021_fig2_straight_sec4.csv")
    fig, axs = plt.subplots(2, 3, figsize=(11, 7.0), constrained_layout=True)
    cfg = (("str", "straight_LmS125", L("直線水路(中央)", "Straight flume (centre)")),
           ("s125", "S125", L("蛇行度 1.25 の水路", "S = 1.25 flume")), ("s110", "S110", L("蛇行度 1.10 の水路", "S = 1.10 flume")))
    for a, (ch, key, ttl) in enumerate(cfg):
        for b, side in enumerate(("outer", "inner")):
            if ch == "str" and b == 1: continue
            ax = axs[b, a]
            if ch != "str" and side == "outer":
                for ser, col, ls, nm in (("calc2d", C_2D, ":", NM_2D()), ("calc3d", C_3D, "-", NM_3D())):
                    x_, y_ = series(f5, "s_over_Lm", "h1st", channel=key, series=ser)
                    for lo, hi in ((0, 0.25), (0.25, 0.75), (0.75, 1.26)):      # 岸が替わる所で線を切る
                        w = (x_ > lo + 1e-6) & (x_ <= hi + 1e-6)
                        ax.plot(x_[w], y_[w], color=col, lw=1.4 if ser == "calc2d" else 1.5, ls=ls, label=nm if lo == 0 else None)
            for m in ("h", "nh"):
                name = ("ub" if ch == "s110" else ch) + "_" + m
                if name not in runs: continue
                r = runs[name]; ii = r.bank("center" if ch == "str" else side); col = C_H if m == "h" else C_NH
                ax.plot(r.s[ii] / r.Lm, [r.wave1(i) for i in ii], color=col, lw=1.8, label=NM_H() if m == "h" else NM_NH())
            ser = key if ch == "str" else f"{key}_{side}"
            xe, he = series(fw, "s_over_Lm", "h1st", series=ser)
            ax.plot(xe, he, "o", color=C_EXP, ms=5.5, label=NM_E21())
            sec_marks(ax, 0); ax.set_xlim(0, 1.27); ax.set_ylim(0.6, 3.15)
            sub = "" if ch == "str" else L("、外岸沿い" if side == "outer" else "、内岸沿い", ", outer bank" if side == "outer" else ", inner bank")
            style(ax, LB_S() if (b == 1 or ch == "str") else None,
                  L("第 1 波の波高 / ", "first-wave height / ") + r"$h_t$" if a == 0 or (b == 1 and a == 1) else None, ttl + sub)
    axs[0, 0].set_xlabel(L("ゲートからの距離 / 8.06 m", "distance from the gate / 8.06 m"))
    # 直線水路の Section 4 の時系列。時刻の原点が合わないので、静水圧の段波の到達(波高 0.5)を 0 にそろえる
    ax = axs[1, 0]
    t2, e2 = series(f2, "tstar", "eta", series="calc2d"); t0 = cross(t2, e2)
    t3, e3 = series(f2, "tstar", "eta", series="calc3d_coarse")
    ax.plot(t3 - t0, e3, color=C_3D, lw=1.5, label=NM_3D())
    if "str_h" in runs:
        rh = runs["str_h"]; i4 = [i for i in rh.idx("center") if abs(rh.s[i] - 4.03) < 1e-6][0]; tc0 = cross(rh.ts, rh.eta[i4])
        ax.plot(rh.ts - tc0, rh.eta[i4], color=C_H, lw=1.8, label=NM_H())
        if "str_nh" in runs:
            rn = runs["str_nh"]; ax.plot(rn.ts - tc0, rn.eta[i4], color=C_NH, lw=1.8, label=NM_NH())
    ax.plot(t2 - t0, e2, color=C_2D, lw=1.4, ls=":", label=NM_2D())
    te, ee = series(f2, "tstar", "eta", series="exp")
    ax.plot(te - t0, ee, "o", color=C_EXP, ms=3.2, mfc="none", mew=0.9)
    ax.set_xlim(-3, 13.5); ax.set_ylim(-0.1, 3.15)
    style(ax, L("静水圧の段波の到達からの無次元時間", "dimensionless time from the hydrostatic arrival"), LB_E(),
          L("直線水路の Section 4(ゲートから 4.03 m)の時間変化", "Straight flume: time series at Section 4\n(4.03 m from the gate)"))
    top_legend(fig, 1.0, ncol=5)
    fig.savefig(os.path.join(FIGS, "firstwave.png"), dpi=130, bbox_inches="tight"); plt.close(fig)


def fig_sens(runs):
    if not any(n in runs for n in SENS): return
    fig, axs = plt.subplots(2, 3, figsize=(11, 7.0), constrained_layout=True)
    mx = data("k2019_fig8_max_height.csv"); d6 = data("k2021_fig6_sec4_outer.csv"); sm = data("k2019_fig2_fig3_section_mean.csv")
    # 上段: 同じ計算の変種は、同じ色(静水圧 = 青、非静水圧 = 橙)で線種を変える。線種の凡例は図の上に 1 つ
    var = (("", "-", L("2 cm 格子", "2 cm grid")), ("_d4", "--", L("4 cm 格子", "4 cm grid")), ("_d1", "-.", L("1 cm 格子(3.7 s まで)", "1 cm grid (to 3.7 s)")),
           ("_r30", ":", L("2 cm 格子、水路を 30° 回した配置", "2 cm grid, flume rotated by 30 deg")))
    # (a)(b) 左岸沿いの最大波高: 砕波段波の静水圧、波状段波の非静水圧
    for ax, base, bore, col, ttl in ((axs[0, 0], "bk_h", "bk", C_H, L("(a) 砕波段波、静水圧: 左岸沿いの最大波高", "(a) Breaking bore, hydrostatic:\nmaximum along the left bank")),
                                     (axs[0, 1], "ub_nh", "ub", C_NH, L("(b) 波状段波、非静水圧: 左岸沿いの最大波高", "(b) Undular bore, non-hydrostatic:\nmaximum along the left bank"))):
        for suf, ls, nm in var:
            if base + suf not in runs: continue
            r = runs[base + suf]; ii = [i for i in r.idx("left") if r.s[i] <= 1.06 * r.Lm]
            ax.plot(r.s[ii] / r.Lm, [r.wmax(i) for i in ii], color=col, lw=1.8 if suf == "" else 1.3, ls=ls)
        se, he = series(mx, "s_over_L", "hmax", bore=BORE[bore], bank="left")
        ax.plot(se, he, "o", color=C_EXP, ms=5.5)
        sec_marks(ax, 0, 1.06); ax.set_xlim(0, 1.07); ax.set_ylim(0.6, 3.8)
        style(ax, LB_S(), L("最大波高 / ", "maximum wave height / ") + r"$h_t$" if ax is axs[0, 0] else None, ttl)
    # (c) Section 4 の外岸の時系列: 格子と配置
    te, ee = series(d6, "tstar", "eta", channel="S110", series="exp")
    ax = axs[0, 2]
    for suf, ls, nm in var:
        if "ub_nh" + suf not in runs: continue
        r = runs["ub_nh" + suf]; i = r.idx("sec", 4)[-1]
        ax.plot(r.ts, r.eta[i], color=C_NH, lw=1.8 if suf == "" else 1.3, ls=ls)
    ax.plot(te, ee, "o", color=C_EXP, ms=3.2, mfc="none", mew=0.9)
    ax.set_xlim(11.5, 26.5); ax.set_ylim(-0.1, 3.8)
    style(ax, LB_T(), LB_E(), L("(c) 波状段波、非静水圧: Section 4 の外岸", "(c) Undular bore, non-hydrostatic:\nouter bank at Section 4"))
    from matplotlib.lines import Line2D
    hd = [Line2D([], [], color="#666666", lw=1.8 if suf == "" else 1.3, ls=ls) for suf, ls, nm in var] + \
         [Line2D([], [], color=C_EXP, marker="o", ms=5.5, ls="")]
    fig.legend(hd, [nm for suf, ls, nm in var] + [NM_EXP()], loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=5, fontsize=8, frameon=False,
               title=L("上段の図(線の色: 青 = 静水圧、橙 = 非静水圧)", "upper panels (line colour: blue = hydrostatic, orange = non-hydrostatic)"), title_fontsize=8)
    # (d) 砕波スイッチ: 直線水路の Section 4(静水圧の段波の到達をそろえる)。(d) と (f) の線は同じ組で、凡例は図の下に 1 つ
    sw = (("str_nh", C_NH, "-", 1.8, L("非静水圧(砕波スイッチなし)", "non-hydrostatic (no breaking switch)")),
          ("str_nh_s", C_NH, "--", 1.3, L("非静水圧(砕波スイッチなし)、初期の段差がなだらか", "non-hydrostatic (no breaking switch), smoothed initial step")),
          ("str_h", C_H, "-", 1.8, NM_H()),
          ("str_nhb", C_SW, "--", 1.8, L("非静水圧 + 砕波スイッチ", "non-hydrostatic + breaking switch")),
          ("str_nhb2", C_SW, ":", 1.6, L("非静水圧 + 砕波スイッチ(縁 2 セル)", "non-hydrostatic + breaking switch (margin of 2 cells)")),
          ("str_nhb_s", C_SW, "-.", 1.6, L("非静水圧 + 砕波スイッチ、初期の段差がなだらか", "non-hydrostatic + breaking switch, smoothed initial step")))
    ax = axs[1, 0]; f2 = data("k2021_fig2_straight_sec4.csv")
    if "str_h" in runs:
        rh = runs["str_h"]; i4 = [i for i in rh.idx("center") if abs(rh.s[i] - 4.03) < 1e-6][0]; tc0 = cross(rh.ts, rh.eta[i4])
        for name, col, ls, lw, nm in sw:
            if name in runs: ax.plot(runs[name].ts - tc0, runs[name].eta[i4], color=col, lw=lw, ls=ls, label=nm)
    t2, e2 = series(f2, "tstar", "eta", series="calc2d"); tx, ex_ = series(f2, "tstar", "eta", series="exp")
    ax.plot(tx - cross(t2, e2), ex_, "o", color=C_EXP, ms=3.2, mfc="none", mew=0.9, label=NM_EXP())
    ax.set_xlim(-3, 13.5); ax.set_ylim(-0.1, 3.8)
    style(ax, L("静水圧の段波の到達からの無次元時間", "dimensionless time from the hydrostatic arrival"), LB_E(),
          L("(d) 波状段波: 砕波スイッチ(直線水路の Section 4)", "(d) Undular bore, breaking switch:\nSection 4 of the straight flume"))
    hd, lb = ax.get_legend_handles_labels()
    fig.legend(hd, lb, loc="upper center", bbox_to_anchor=(0.5, 0.0), ncol=2, fontsize=8, frameon=False,
               title=L("(d) と (f) の線", "lines of panels (d) and (f)"), title_fontsize=8)
    # (e) 砕波段波を非静水圧で計算したとき: 断面 4 の断面平均
    ax = axs[1, 1]
    for name, col, nm in (("bk_h", C_H, NM_H()), ("bk_nh", C_NH, L("非静水圧(砕波スイッチなし)", "non-hydrostatic (no breaking switch)"))):
        if name not in runs: continue
        r = runs[name]; ax.plot(r.ts, r.eta[r.idx("sec", 4)].mean(axis=0), color=col, lw=1.8, label=nm)
    t4, e4 = series(sm, "tstar", "eta", bore="breaking", section=4)
    ax.plot(t4, e4, "o", color=C_EXP, ms=2.6, label=NM_EXP())
    ax.set_xlim(11.5, 23.5); ax.set_ylim(-0.1, 3.8)
    style(ax, LB_T(), None, L("(e) 砕波段波: 断面 4 の断面平均", "(e) Breaking bore:\nsection mean at Section 4"))
    ax.legend(fontsize=7.5, frameon=False, loc="upper left")
    # (f) 直線水路の第 1 波の波高: 砕波スイッチ
    ax = axs[1, 2]; fw = data("k2021_fig4_first_wave.csv")
    for name, col, ls, lw, nm in sw:
        if name not in runs: continue
        r = runs[name]; ii = r.bank("center")
        ax.plot(r.s[ii] / r.Lm, [r.wave1(i) for i in ii], color=col, lw=lw, ls=ls)
    xe, he = series(fw, "s_over_Lm", "h1st", series="straight_LmS125")
    ax.plot(xe, he, "o", color=C_EXP, ms=5.5)
    ax.set_xlim(0, 1.27); ax.set_ylim(0.6, 3.8)
    style(ax, L("ゲートからの距離 / 8.06 m", "distance from the gate / 8.06 m"), L("第 1 波の波高 / ", "first-wave height / ") + r"$h_t$",
          L("(f) 波状段波: 砕波スイッチ(直線水路の第 1 波)", "(f) Undular bore, breaking switch:\nfirst wave in the straight flume"))
    fig.savefig(os.path.join(FIGS, "sens.png"), dpi=130, bbox_inches="tight"); plt.close(fig)


def main():
    os.makedirs(FIGS, exist_ok=True)
    runs = load_runs()
    print(L("読み込んだ構成: ", "runs found: ") + ", ".join(runs) + "\n")
    table1()
    if runs:
        table2(runs); table3(runs); table4(runs); table5(runs); table6(runs); table7(runs)
    fig_setup(); fig_surface(runs); fig_breaking(runs); fig_undular(runs); fig_firstwave(runs); fig_sens(runs)


if __name__ == "__main__":
    main()
