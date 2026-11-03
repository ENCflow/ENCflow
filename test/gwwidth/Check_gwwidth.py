#!/usr/bin/env python3
# =====================================================================
# gwwidth: 地下⇔地表の水の受け渡しの体積換算(サブグリッド河道幅のセル。
# developer.md §26.1)の reference 非依存検定
#   conserve DIR      : 閉領域なので、雨が止んだ後(1.5 時間以降)の総水量 S_total が
#                       一定(相対 1e-10。Log.txt は f_disp_debug=1 の全有効桁)。
#                       修正前は湧出で水が減り(param.txt)、管路への流入で水が
#                       増えた(param_gwc.txt)
#   match DIR1 DIR2   : 最終の総水量が等しい(河道幅あり・なし。雨の総量は同じ)
#   conc DIR K        : 分布番号 K の濃度が、水深 1 mm を超える全セルで
#                       1 mg/L ± 1e-3(雨・噴出の濃度。湧出の水が縮むと 1/wfrac 倍の
#                       5 前後になる。±1e-3 は浸透同伴の割合の評価時点の差などの
#                       既存の小さなずれ 1e-4 程度を許す幅)
#   rain DIR AREA     : 最終の総水量が雨の総量に等しい(雨の濃度 1 mg/L なので、台帳の
#                       in_rain_g [g] = 雨の体積 [m3]。AREA = 有効セルの総面積 m2。相対
#                       1e-6 = es15.7 の出力精度相当)。修正前の管路層の構成は流入で
#                       水が 3.6 % 増えた
#   ledger DIR        : 水質の台帳が閉じる(閉領域: 入力 − 管路側への除去 = 現在の質量。
#                       相対 1e-6 = es15.7 の出力精度相当)
# =====================================================================
import csv
import os
import sys

import numpy as np

NX, NY = 12, 8
rc = 0


def ng(msg):
    global rc
    print("  NG:", msg)
    rc = 1


def log_rows(d):
    """Log.txt の (時刻 h, S_total) の並び。"""
    out = []
    for line in open(os.path.join(d, "Log.txt")):
        p = line.split()
        if len(p) < 5 or ":" not in p[0] or not p[0][0].isdigit():
            continue
        hh, mm, ss = p[0].split(":")
        out.append((float(hh) + float(mm) / 60 + float(ss) / 3600, float(p[4])))
    return out


def conserve(d):
    rows = [r for r in log_rows(d) if r[0] >= 1.5]
    if len(rows) < 3:
        ng(f"{d}: Log.txt に 1.5 時間以降の行が足りない")
        return
    s0 = rows[0][1]
    dev = max(abs(s - s0) for _, s in rows) / s0
    print(f"  {d}: S_total after the rain = {s0:.14f} m, max relative deviation {dev:.2e}")
    if dev > 1e-10:
        ng(f"{d}: 雨の後の総水量が一定でない(相対 {dev:.2e})")


def match(d1, d2):
    s1 = log_rows(d1)[-1][1]
    s2 = log_rows(d2)[-1][1]
    rel = abs(s1 - s2) / s2
    print(f"  final S_total: {d1} {s1:.14f}  {d2} {s2:.14f}  (relative {rel:.2e})")
    if rel > 1e-10:
        ng(f"最終の総水量が河道幅なしと一致しない(相対 {rel:.2e})")


def conc(d, k):
    c = np.fromfile(os.path.join(d, f"C{k:04d}.bil"), "<f4").reshape(NY, NX)
    h = np.fromfile(os.path.join(d, f"H{k:04d}.bil"), "<f4").reshape(NY, NX)
    wet = h > 1e-3
    if not wet.any():
        ng(f"{d}: 分布 {k} に水のあるセルがない")
        return
    lo, hi = float(c[wet].min()), float(c[wet].max())
    print(f"  {d}: concentration on {int(wet.sum())} wet cells (frame {k}): {lo:.6f} .. {hi:.6f} mg/L")
    if lo < 1.0 - 1e-3 or hi > 1.0 + 1e-3:
        ng(f"{d}: 濃度が 1 mg/L からずれている({lo:.6f} .. {hi:.6f})")


def rain(d, area):
    rows = list(csv.reader(open(os.path.join(d, "wq.csv"))))
    v = dict(zip(rows[0], (float(x) for x in rows[-1])))
    expect = v["in_rain_g"] / area          # 雨の濃度 1 g/m3 → 体積 m3 → 領域平均の水深 m
    s = log_rows(d)[-1][1]
    rel = abs(s - expect) / expect
    print(f"  {d}: final S_total {s:.12f} m, rain total {expect:.12f} m (relative {rel:.2e})")
    if rel > 1e-6:
        ng(f"{d}: 最終の総水量が雨の総量と一致しない(相対 {rel:.2e})")


def ledger(d):
    rows = list(csv.reader(open(os.path.join(d, "wq.csv"))))
    head = rows[0]
    worst = 0.0
    for r in rows[1:]:
        v = dict(zip(head, (float(x) for x in r)))
        inp = v["in_rain_g"] + v["in_gwc_g"]
        mass = sum(v[c] for c in ("mass_surface_g", "mass_gw_g", "mass_pool_g", "mass_dam_g", "mass_rs_g"))
        res = inp - v["to_gwc_g"] - mass
        if inp > 0:
            worst = max(worst, abs(res) / inp)
    print(f"  {d}: wq ledger closure, max relative residual {worst:.2e}")
    if worst > 1e-6:
        ng(f"{d}: 水質の台帳が閉じない(相対 {worst:.2e})")


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    mode = argv[1]
    if mode == "conserve":
        conserve(argv[2])
    elif mode == "match":
        match(argv[2], argv[3])
    elif mode == "conc":
        conc(argv[2], int(argv[3]))
    elif mode == "rain":
        rain(argv[2], float(argv[3]))
    elif mode == "ledger":
        ledger(argv[2])
    else:
        print("unknown mode", mode)
        return 2
    print(f"gwwidth {mode}: {'PASS' if rc == 0 else 'FAIL'}")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
