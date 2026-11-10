#!/usr/bin/env python3
"""V 字流域の計算結果を運動学的波の理論解(data/analytic.csv)と比べ、水収支を確かめる。

  python3 check.py              result_*/ にある全ケースの表を出す。8 近傍・既定のケース(主ケース)には合否を付ける
  python3 check.py dx10_r0 ...  指定したケースだけ

読むもの: result_<case>/fluxes/flux0001.csv(出口の計測面の流量)、flux0002.csv(左岸側の斜面の脚から
水路へ入る流量)、probes/probe0001.csv(出口の水路の水深)、probe0002.csv(斜面の脚の水深)、
H9998.txt(終了時の水深)。格子は make_inputs.py から作り直して面積を数える。

指標(1 分ごとの値。流量の理論値は水路の運動学的波、斜面は閉じた式):
  NRMSE   = √(平均((Q − Q_理論)²)) / 理論のピーク(出口 4.860 m³/s、斜面 2.400 m³/s)
  ピーク比 = 計算のピーク / 理論のピーク。格子比 = 計算のピーク / (降雨強度 × 格子上の集水面積)
           (45° では格子に乗せた流域の面積が 1.62 km² から最大 0.8 % ずれるので、格子比が 1 なら
           雨がすべて出口を通っている)
  t50     = 出口の流量が理論のピークの半分に初めて達する時刻(理論 39 分)
  水深比  = 80 分(定常)の水深 / 理論の等流水深(出口の水路 0.443 m、斜面の脚 0.0053 m)
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
H_FOOT_TH = (P * M.B / ALPHA_S) ** 0.6               # 斜面の脚の等流水深 (m)
H_OUT_TH = (Q_TH / (M.W * np.sqrt(M.S_C) / M.N_C)) ** 0.6   # 出口の等流水深(広幅)(m)
T_EVAL = 80.0                                        # 水深を比べる時刻 (min)
TOL = {"nrmse": 0.04, "ratio": 0.01, "t50": 3.0, "closure": 0.01}
LABEL = {"": "8 近傍", "_4nb": "4 近傍", "_dif": "拡散波", "_kin": "運動波", "_od2": "振り替え 2"}


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
    v_out = np.trapezoid(q, t * 60.0)
    c = {"name": name, "dx": dx, "theta": th, "suffix": suf, "t": t, "q": q, "qh": qh, "qth": qth, "qhth": qhth,
         "h_out": np.interp(T_EVAL, p1[:, 1], p1[:, 3]), "h_foot": np.interp(T_EVAL, p2[:, 1], p2[:, 3]),
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
    print("理論: 出口のピーク %.3f m3/s、t50 %.0f 分、出口の等流水深 %.3f m、斜面の脚の等流水深 %.4f m、"
          "斜面 1 側の平衡 %.3f m3/s" % (Q_TH, cases[0]["t50_th"], H_OUT_TH, H_FOOT_TH, QH_TH))
    print()
    print("| ケース | 向き | 格子 | 条件 | NRMSE 出口 | ピーク比 | 格子比 | t50 (分) | NRMSE 斜面 | 斜面ピーク比 | 水深比 出口 | 水深比 脚 | 収支 | 流出高比 | 判定 |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    nfail = 0
    for c in cases:
        main_case = c["suffix"] == ""
        judge = ("PASS" if c["pass"] else "FAIL") if main_case else "—"
        if main_case and not c["pass"]:
            nfail += 1
        print("| %s | %g° | %g m | %s | %.4f | %.3f | %.3f | %.0f | %.4f | %.3f | %.2f | %.2f | %.4f | %.3f | %s |"
              % (c["name"], c["theta"], c["dx"], LABEL.get(c["suffix"], c["suffix"]), c["nrmse"], c["peak_ratio"],
                 c["grid_ratio"], c["t50"], c["nrmse_h"], c["peak_h"] / QH_TH, c["h_out"] / H_OUT_TH,
                 c["h_foot"] / H_FOOT_TH, c["closure"], c["vol_ratio"], judge))
    print()
    print("合否の目安: NRMSE ≤ %.2f、|格子比 − 1| ≤ %.2f、|t50 − 理論| ≤ %.0f 分、|収支 − 1| ≤ %.2f(主ケース = 8 近傍・既定だけ)"
          % (TOL["nrmse"], TOL["ratio"], TOL["t50"], TOL["closure"]))
    nmain = sum(1 for c in cases if c["suffix"] == "")
    print("== v-shaped: %d main cases, %d FAIL ==" % (nmain, nfail))
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
