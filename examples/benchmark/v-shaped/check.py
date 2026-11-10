#!/usr/bin/env python3
"""V 字流域の計算結果を運動学的波の理論解(data/analytic.csv)と比べ、水収支を確かめる。

  python3 check.py              result_*/ にある全ケースの表を出す。20・10・5 m の 8 近傍・既定のケース(主ケース)には
                                合否を付ける(追補の 40 m は付けない)
  python3 check.py dx10_r0 ...  指定したケースだけ

読むもの: result_<case>/fluxes/flux0001.csv(出口の計測面の流量)、flux0002.csv(左岸側の斜面の脚から
水路へ入る流量)、probes/probe0001.csv(出口の水路の水深)、probe0002.csv(斜面の水路から 2 列目の水深)、
H0003.txt(90 分の水深)、H9998.txt(終了時の水深)。格子は make_inputs.py から作り直して面積を数える。

指標(1 分ごとの値。流量の理論値は水路の運動学的波、斜面は閉じた式):
  NRMSE   = √(平均((Q − Q_理論)²)) / 理論のピーク(出口 4.860 m³/s、斜面 2.400 m³/s)
  ピーク比 = 計算のピーク / 理論のピーク。格子比 = 計算のピーク / (降雨強度 × 格子上の集水面積)
           (45° では格子に乗せた流域の面積が 1.62 km² から最大 0.8 % ずれるので、格子比が 1 なら
           雨がすべて出口を通っている)
  t50     = 出口の流量が理論のピークの半分に初めて達する時刻(理論 39 分)
  水深比  = 80 分(定常)の水深 / 理論の等流水深。出口は P1 / 0.443 m。斜面の 2 列目は P2 / その位置(尾根から x2。
           20 m で 770 m)の等流水深 (i x2/α)^0.6(5.2 mm)。斜面の 1 列目(脚)は 90 分の分布 H0003 の左岸側の
           脚の列の s = 200〜800 m の平均 / その位置(x1)の等流水深(水路との辺の粗度で水が溜まるので理論より深い)。
           水路は H0003 の水路の軸(軸に最も近い左岸側の行・列)のセルの水深 / h_e (s/L)^0.6 の s = 200〜800 m の平均
  収支    = (出口を通った水量 + 終了時に流域に残る水量) / 流域に降った雨(1 に近いほど閉じている)
  流出高  = 出口を通った水量 / 理論の 180 分の流出量
合否(主ケースだけ。目安): NRMSE ≤ 0.04、|格子比 − 1| ≤ 0.01、|t50 − 理論| ≤ 3 分、|収支 − 1| ≤ 0.01
"""
import glob
import os
import re
import sys
import numpy as np
import make_inputs as M

P = M.P_MMH / 1000.0 / 3600.0
T_R = M.T_RAIN * 60.0
Q_TH = 2.0 * P * M.B * M.L + P * M.W * M.L          # 出口のピークの理論値 4.86 m3/s
QH_TH = P * M.B * M.L                                # 斜面 1 側 × 1000 m の平衡 2.4 m3/s
ALPHA_S = np.sqrt(M.S_S) / M.N_S
H_FOOT_TH = (P * M.B / ALPHA_S) ** 0.6               # 斜面の脚(尾根から B)の等流水深 (m)
H_OUT_TH = (Q_TH / (M.W * np.sqrt(M.S_C) / M.N_C)) ** 0.6   # 出口の等流水深(広幅)(m)
T_EVAL = 80.0                                        # 水深を比べる時刻 (min)
H_MAP = "H0003.txt"                                  # 90 分の水深の分布(dt_file = 1800 s の 3 枚目)。水路の縦断に使う
S_CHAN = (200.0, 800.0)                              # 水路の水深比を平均する区間 (m)
TOL = {"nrmse": 0.04, "ratio": 0.01, "t50": 3.0, "closure": 0.01}
LABEL = {"": "8 近傍", "_4nb": "4 近傍", "_dif": "拡散波", "_kin": "運動波", "_od2": "振り替え 2",
         "_sgc": "fn_rw + 幅 20 m"}


def parse(name):
    m = re.fullmatch(r"dx(\d+)_r(\d+)(.*)", name)
    if not m:
        return None
    return float(m.group(1)), float(m.group(2)), m.group(3)


def theory():
    a = np.loadtxt("data/analytic.csv", delimiter=",", comments="#")
    return a[:, 0], a[:, 2], a[:, 3]           # t (min), Q_hill (m3/s), Q_out (m3/s)


def read_csv(path):
    return np.loadtxt(path, delimiter=",", comments="#")


def t50(t, q, q50):
    k = np.argmax(q >= q50)
    return t[k] if q[k] >= q50 else np.nan


def h_hill_th(x):
    """斜面の尾根から x (m) の位置の等流水深 (m)。"""
    return (P * x / ALPHA_S) ** 0.6


def axis_cells(kind, n):
    """水路の軸のセル(軸に最も近い、左岸側 n ≥ 0 の水路の行・列)。0° の 10・5 m のように軸が格子線に
    乗る格子では軸のすぐ左岸側の行、それ以外では軸上のセル。"""
    chan = kind == 2
    nmin = np.abs(n[chan]).min()
    return chan & (np.abs(np.abs(n) - nmin) < 1e-6) & (n >= -1e-6)


def load_case(name):
    """1 ケースの時系列と指標。結果がなければ None。"""
    d = f"result_{name}"
    if not os.path.isfile(f"{d}/summary.csv"):
        return None
    dx, th, suf = parse(name)
    tth, qh_th, q_th = theory()
    f1 = read_csv(f"{d}/fluxes/flux0001.csv")
    f2 = read_csv(f"{d}/fluxes/flux0002.csv")
    p1 = read_csv(f"{d}/probes/probe0001.csv")
    p2 = read_csv(f"{d}/probes/probe0002.csv")
    t, q = f1[:, 1], f1[:, 2]
    qh = f2[:, 2]
    qth = np.interp(t, tth, q_th)
    qhth = np.interp(t, tth, qh_th)
    _, kind, s, n = M.grid(dx, th)
    kind_n = kind[::-1]
    catch = (kind_n == 1) | (kind_n == 2)
    a_catch = catch.sum() * dx * dx
    H = np.loadtxt(f"{d}/H9998.txt")
    v_end = H[catch].sum() * dx * dx
    Hm = np.loadtxt(f"{d}/{H_MAP}")[::-1]                     # 90 分。行 0 が南端(kind, s, n と同じ向き)
    sel = axis_cells(kind, n) & (s > S_CHAN[0]) & (s < S_CHAN[1])
    h_chan = float(np.mean(Hm[sel] / (H_OUT_TH * (s[sel] / M.L) ** 0.6)))
    rec = M.records(dx, th, kind, s, n)                        # プローブの位置(尾根からの距離 x1, x2)
    foot = (kind == 1) & (np.abs(n - (M.WH - rec["x1"])) < 1e-6) & (s > S_CHAN[0]) & (s < S_CHAN[1])
    h_foot1 = float(np.mean(Hm[foot])) / h_hill_th(rec["x1"])
    v_out = np.trapezoid(q, t * 60.0)
    c = {"name": name, "dx": dx, "theta": th, "suffix": suf, "t": t, "q": q, "qh": qh, "qth": qth, "qhth": qhth,
         "h_out": np.interp(T_EVAL, p1[:, 1], p1[:, 3]), "h_foot": np.interp(T_EVAL, p2[:, 1], p2[:, 3]),
         "h_chan": h_chan, "h_foot1": h_foot1, "x1": rec["x1"], "x2": rec["x2"],
         "p1": p1, "p2": p2, "a_catch": a_catch, "kind": kind_n, "H_end": H,
         "nrmse": np.sqrt(np.mean((q - qth) ** 2)) / Q_TH,
         "nrmse_h": np.sqrt(np.mean((qh - qhth) ** 2)) / QH_TH,
         "peak": q.max(), "peak_ratio": q.max() / Q_TH, "grid_ratio": q.max() / (P * a_catch),
         "peak_h": qh.max(), "t50": t50(t, q, 0.5 * Q_TH), "t50_th": t50(t, qth, 0.5 * Q_TH),
         "closure": (v_out + v_end) / (P * T_R * a_catch),
         "vol_ratio": v_out / np.trapezoid(qth, t * 60.0)}
    c["pass"] = (c["nrmse"] <= TOL["nrmse"] and abs(c["grid_ratio"] - 1) <= TOL["ratio"]
                 and abs(c["t50"] - c["t50_th"]) <= TOL["t50"] and abs(c["closure"] - 1) <= TOL["closure"])
    return c


def order_key(name):
    dx, th, suf = parse(name)
    return (list(LABEL).index(suf) if suf in LABEL else 9, th, -dx)


def main():
    names = sys.argv[1:] or sorted((os.path.basename(d)[7:] for d in glob.glob("result_*") if parse(os.path.basename(d)[7:])),
                                   key=order_key)
    cases = [c for c in (load_case(nm) for nm in names) if c is not None]
    if not cases:
        sys.exit("結果がありません(make run の後に実行)")
    print("理論: 出口のピーク %.3f m3/s、t50 %.0f 分、出口の等流水深 %.3f m、斜面の脚(尾根から %g m)の等流水深 %.4f m、"
          "斜面 1 側の平衡 %.3f m3/s" % (Q_TH, cases[0]["t50_th"], H_OUT_TH, M.B, H_FOOT_TH, QH_TH))
    print("水深比の理論値はプローブの位置で評価(斜面 2 列目 P2: 20 m で尾根から 770 m、%.4f m)" % h_hill_th(M.B - 30.0))
    print()
    print("| ケース | 向き | 格子 | 条件 | NRMSE 出口 | ピーク比 | 格子比 | t50 (分) | NRMSE 斜面 | 斜面ピーク比 | 水深比 水路 | 水深比 出口 (P1) | 水深比 斜面 2 列目 (P2) | 水深比 脚 (1 列目) | 収支 | 流出高比 | 判定 |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    nfail = 0
    for c in cases:
        main_case = c["suffix"] == "" and c["dx"] in M.DXS
        judge = ("PASS" if c["pass"] else "FAIL") if main_case else "—"
        if main_case and not c["pass"]:
            nfail += 1
        print("| %s | %g° | %g m | %s | %.4f | %.3f | %.3f | %.0f | %.4f | %.3f | %.2f | %.2f | %.2f | %.2f | %.4f | %.3f | %s |"
              % (c["name"], c["theta"], c["dx"], LABEL.get(c["suffix"], c["suffix"]), c["nrmse"], c["peak_ratio"],
                 c["grid_ratio"], c["t50"], c["nrmse_h"], c["peak_h"] / QH_TH, c["h_chan"], c["h_out"] / H_OUT_TH,
                 c["h_foot"] / h_hill_th(c["x2"]), c["h_foot1"], c["closure"], c["vol_ratio"], judge))
    print()
    print("合否の目安: NRMSE ≤ %.2f、|格子比 − 1| ≤ %.2f、|t50 − 理論| ≤ %.0f 分、|収支 − 1| ≤ %.2f(主ケース = 20・10・5 m の 8 近傍・既定だけ)"
          % (TOL["nrmse"], TOL["ratio"], TOL["t50"], TOL["closure"]))
    nmain = sum(1 for c in cases if c["suffix"] == "" and c["dx"] in M.DXS)
    print("== v-shaped: %d main cases, %d FAIL ==" % (nmain, nfail))
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
