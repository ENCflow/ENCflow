#!/usr/bin/env python3
"""V 字谷の計算結果を、向き 0° の 8 近傍(基準)と比べ、疑似窪地の貯留と水収支を確かめる。

  python3 check.py                 result_*/ にある全ケースの表を出す。45° の 8 近傍には合否を付ける
  python3 check.py s03_dx10_r45    指定したケースだけ(基準のケースも読む)

読むもの: result_<case>/fluxes/flux0001.csv(下流端の計測面の流量)、H9998.txt(終了時の水深)。
格子は make_inputs.py から作り直して面積と谷底の軸のセルを数える。

指標(1 分ごとの値):
  NRMSE    = √(平均((Q − Q_基準)²)) / 基準のピーク。基準 = 同じ斜面の勾配・格子間隔の 0°・8 近傍
  ピーク比 = ピーク / 基準のピーク、ピーク時刻の差 (分)
  流出比   = 180 分までの流出量 / 基準の流出量
  残留     = 終了時に谷に残る水量 / 谷に降った雨
  収支     = (流出量 + 残留の水量) / 雨
  窪地     = 45° の 4 近傍で谷底の軸のセルが溜める量の見積もり Σ V_p = (L/2)(S_S − S_V) Δx²
             (1 セルの深さ H_p = (√2/2)(S_S − S_V) Δx、セル数 L/(√2 Δx))/ 雨。S_S ≤ S_V なら 0
合否(45° の 8 近傍だけ。目安): NRMSE ≤ 0.05、|ピーク比 − 1| ≤ 0.05、|収支 − 1| ≤ 0.01
"""
import glob
import os
import re
import sys
import numpy as np
import make_inputs as M

P = M.P_MMH / 1000.0 / 3600.0
T_R = M.T_RAIN * 60.0
TOL = {"nrmse": 0.05, "peak": 0.05, "closure": 0.01}


def parse(name):
    m = re.fullmatch(r"s(\d\d)_dx(\d+)_r(\d+)(.*)", name)
    if not m:
        return None
    return int(m.group(1)) / 100.0, float(m.group(2)), float(m.group(3)), m.group(4)


def load_case(name):
    d = f"result_{name}"
    if not os.path.isfile(f"{d}/summary.csv"):
        return None
    ss, dx, th, suf = parse(name)
    f1 = np.loadtxt(f"{d}/fluxes/flux0001.csv", delimiter=",", comments="#")
    t, q = f1[:, 1], f1[:, 2]
    _, kind, s, n = M.grid(ss, dx, th)
    kind_n = kind[::-1]
    valley = kind_n == 1
    a = valley.sum() * dx * dx
    H = np.loadtxt(f"{d}/H9998.txt")
    v_end = H[valley].sum() * dx * dx
    v_out = np.trapezoid(q, t * 60.0)
    rain = P * T_R * a
    vp = 0.5 * M.L * max(ss - M.S_V, 0.0) * dx * dx if th == 45.0 else 0.0
    return {"name": name, "ss": ss, "dx": dx, "theta": th, "suffix": suf, "t": t, "q": q, "H_end": H, "kind": kind_n,
            "area": a, "peak": q.max(), "t_peak": t[q.argmax()], "v_out": v_out, "v_end": v_end, "rain": rain,
            "resid": v_end / rain, "closure": (v_out + v_end) / rain, "vp": vp / rain}


def compare(c, ref):
    qr = np.interp(c["t"], ref["t"], ref["q"])
    c["nrmse"] = np.sqrt(np.mean((c["q"] - qr) ** 2)) / ref["peak"]
    c["peak_ratio"] = c["peak"] / ref["peak"]
    c["dt_peak"] = c["t_peak"] - ref["t_peak"]
    c["vol_ratio"] = c["v_out"] / ref["v_out"]
    c["pass"] = (c["nrmse"] <= TOL["nrmse"] and abs(c["peak_ratio"] - 1) <= TOL["peak"]
                 and abs(c["closure"] - 1) <= TOL["closure"])


def order_key(name):
    ss, dx, th, suf = parse(name)
    return (dx != 10.0, ss, th, suf)


def main():
    names = sys.argv[1:] or sorted((os.path.basename(d)[7:] for d in glob.glob("result_*")
                                    if parse(os.path.basename(d)[7:])), key=order_key)
    cases = {}
    for nm in names:
        c = load_case(nm)
        if c is not None:
            cases[nm] = c
    if not cases:
        sys.exit("結果がありません(make run の後に実行)")
    for c in list(cases.values()):
        refname = M.case_name(c["ss"], c["dx"], 0.0)
        ref = cases.get(refname) or load_case(refname)
        if ref is None:
            c["nrmse"] = c["peak_ratio"] = c["dt_peak"] = c["vol_ratio"] = np.nan
            c["pass"] = False
        else:
            compare(c, ref)
    print("雨: 10.8 mm/h × 60 分 = %.0f m³(1.62 km²)。基準 = 同じ斜面の勾配・格子の 0°・8 近傍" % (P * T_R * 1.62e6))
    print()
    print("| ケース | S_S | 格子 | 向き | 近傍 | ピーク (m³/s) | ピーク時刻 (分) | NRMSE | ピーク比 | ピーク時刻の差 | 流出比 | 残留 | 窪地の見積もり | 収支 | 判定 |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    nfail = 0
    for c in cases.values():
        judge_case = c["theta"] == 45.0 and c["suffix"] == ""
        judge = ("PASS" if c["pass"] else "FAIL") if judge_case else "—"
        if judge_case and not c["pass"]:
            nfail += 1
        print("| %s | %.2f | %g m | %g° | %s | %.3f | %.0f | %.4f | %.3f | %+.0f | %.3f | %.3f | %.3f | %.4f | %s |"
              % (c["name"], c["ss"], c["dx"], c["theta"], "4" if c["suffix"] == "_4nb" else "8", c["peak"], c["t_peak"],
                 c["nrmse"], c["peak_ratio"], c["dt_peak"], c["vol_ratio"], c["resid"], c["vp"], c["closure"], judge))
    print()
    print("合否の目安: NRMSE ≤ %.2f、|ピーク比 − 1| ≤ %.2f、|収支 − 1| ≤ %.2f(45° の 8 近傍だけ)" % (TOL["nrmse"], TOL["peak"], TOL["closure"]))
    njudge = sum(1 for c in cases.values() if c["theta"] == 45.0 and c["suffix"] == "")
    print("== v-valley: %d judged cases, %d FAIL ==" % (njudge, nfail))
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
