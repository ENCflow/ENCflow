#!/usr/bin/env python3
# =====================================================================
# wqstruct: 構造物・取水が水と一緒に運ぶ水質の質量(developer.md §30.10)の
# reference 非依存検定
#   conc DIR K [TOL]  : 分布番号 K の地表の濃度が、水深 1 mm を超える全セルで
#                       1 mg/L ± TOL(既定 1e-3)。全区画の水が 1 mg/L なので、
#                       取水が汲んだ水と同じ割合の質量を運べば濃度は変わらない
#                       (修正前は送り先が薄まり、取水側が濃くなった)
#   gwconc DIR K      : 地下の濃度 Cg/Hg(Cg は地下の質量 g/m2、Hg は地下の水深 m)
#                       が、Hg が 1 mm を超える全セルで 1 ± 1e-3(井戸が水だけを
#                       汲むと井戸のセルの地下水が濃くなる)
#   tank DIR K I J    : ため池 (I, J) の濃度 mass_rs_g / (Hrs × A) が 1 ± 1e-3
#                       (ため池はこのセルだけ。A = セル面積 100 m2)
#   ledger DIR        : 水質の台帳が閉じる: 初期の質量 + 入力(in_*)− 系外への除去
#                       (out_*、to_gwc_g)= 現在の質量(相対 1e-6 = es15.7 の出力精度
#                       相当)。out_intake_g を除くと閉じない(取水が持ち出した分)
#   intake DIR AREA TOL : 域外へ出た水の体積(総水量 S_total の減少 × AREA)× 1 g/m3
#                       = out_intake_g(相対 TOL)。地表だけの構成は出力精度の 1e-6、
#                       井戸は地下の濃度の既存の小さなずれ(1e-4 程度)を許す 1e-3
#   gwc DIR K         : 管路から汲んだ水の体積(管路の貯留 Hgc の減少 × セル面積)
#                       × 1 g/m3 = in_gwc_g(相対 1e-6。管路の水は固定濃度 1 mg/L)
#   active DIR K      : 構造物が水を動かした(区画の平均水深が初期から 5 cm 以上
#                       動いた/構造物のない対照 N は動かない)。検定が「何も
#                       流れずに通る」ことを防ぐ
# =====================================================================
import csv
import os
import sys

import numpy as np

N = 17
ACELL = 100.0          # セル面積 (m2)
rc = 0

# 区画 (r, c) の名前と、param.txt で期待する水深の変化の向き(+1 増、-1 減、0 不変)
NAMES = [["A", "C", "D", "F"], ["H", "I", "E", "G"], ["J", "L", "N", "O"], ["B", "K", "M", "Q"]]
MOVE = {"A": -1, "C": -1, "D": -1, "F": +1, "H": -1, "I": -1, "E": +1, "G": -1,
        "J": -1, "L": -1, "N": 0, "O": +1, "B": +1, "K": +1, "M": +1, "Q": -1}


def ng(msg):
    global rc
    print("  NG:", msg)
    rc = 1


def field(d, name, k):
    return np.fromfile(os.path.join(d, f"{name}{k:04d}.bil"), "<f4").reshape(N, N)


def comp(a, r, c):
    """区画 (r, c) の内部 3 × 3 セル(配列は 0 始まり: j-1, i-1)。"""
    return a[4 * r + 1:4 * r + 4, 4 * c + 1:4 * c + 4]


def ledger_rows(d):
    rows = list(csv.reader(open(os.path.join(d, "wq.csv"))))
    head = rows[0]
    return [dict(zip(head, (float(x) for x in r))) for r in rows[1:]]


def log_s_total(d):
    """Log.txt の (時刻 s, 総水量 m)。保存量の列が 1 列(S)なら 3 列目、3 列(S_surf,
    S_grnd, S_total)なら 5 列目。"""
    out = []
    ncol = None
    for line in open(os.path.join(d, "Log.txt")):
        p = line.split()
        if p and p[0] == "time,":
            ncol = 5 if "S_total(m)," in p else 3
            continue
        if ncol is None or len(p) < ncol or ":" not in p[0] or not p[0][0].isdigit():
            continue
        hh, mm, ss = p[0].split(":")
        out.append((float(hh) * 3600 + float(mm) * 60 + float(ss), float(p[ncol - 1])))
    return out


def conc(d, k, tol):
    c = field(d, "C", k)
    h = field(d, "H", k)
    wet = h > 1e-3
    lo, hi = float(c[wet].min()), float(c[wet].max())
    print(f"  {d}: surface concentration on {int(wet.sum())} wet cells (frame {k}): {lo:.6f} .. {hi:.6f} mg/L")
    if lo < 1.0 - tol or hi > 1.0 + tol:
        ng(f"{d}: 地表の濃度が 1 mg/L からずれている({lo:.6f} .. {hi:.6f})")


def gwconc(d, k):
    cg = field(d, "Cg", k)
    hg = field(d, "Hg", k)
    w = hg > 1e-3
    if not w.any():
        ng(f"{d}: 地下に水のあるセルがない")
        return
    r = cg[w] / hg[w]
    lo, hi = float(r.min()), float(r.max())
    print(f"  {d}: groundwater concentration Cg/Hg on {int(w.sum())} cells (frame {k}): {lo:.6f} .. {hi:.6f} mg/L")
    if lo < 1.0 - 1e-3 or hi > 1.0 + 1e-3:
        ng(f"{d}: 地下の濃度が 1 mg/L からずれている({lo:.6f} .. {hi:.6f})")


def tank(d, k, i, j):
    hrs = float(field(d, "Hrs", k)[j - 1, i - 1])
    rows = ledger_rows(d)
    t = (k * 3600.0)
    v = [r for r in rows if abs(r["time_s"] - t) < 1e-6]
    if not v or hrs <= 0.0:
        ng(f"{d}: 分布 {k} の時刻の台帳の行か、ため池の貯留がない")
        return
    cr = v[0]["mass_rs_g"] / (hrs * ACELL)
    print(f"  {d}: tank ({i},{j}) frame {k}: Hrs = {hrs:.6f} m, mass_rs_g = {v[0]['mass_rs_g']:.6f} g, concentration {cr:.6f} mg/L")
    if abs(cr - 1.0) > 1e-3:
        ng(f"{d}: ため池の濃度が 1 mg/L からずれている({cr:.6f})")


def ledger(d):
    rows = ledger_rows(d)
    m0 = None
    worst = 0.0
    for v in rows:
        mass = sum(v[c] for c in ("mass_surface_g", "mass_gw_g", "mass_pool_g", "mass_dam_g", "mass_rs_g"))
        if m0 is None:
            m0 = mass
        inp = sum(v[c] for c in ("in_point_g", "in_area_g", "in_map_g", "in_rain_g", "in_gwc_g",
                                 "in_bldup_g", "in_edge_g", "in_stage_g"))
        out = sum(v[c] for c in ("decay_g", "to_gwc_g", "out_sea_g", "out_edge_g", "out_stage_g",
                                 "out_intake_g"))
        res = m0 + inp - out - mass
        worst = max(worst, abs(res) / m0)
    last = rows[-1]
    print(f"  {d}: wq ledger closure, max relative residual {worst:.2e}"
          f" (initial {m0:.4f} g, out_intake_g {last['out_intake_g']:.4f} g)")
    if worst > 1e-6:
        ng(f"{d}: 水質の台帳が閉じない(相対 {worst:.2e})")


def intake(d, area, tol):
    s = log_s_total(d)
    vol = (s[0][1] - s[-1][1]) * area
    got = ledger_rows(d)[-1]["out_intake_g"]
    if vol <= 0.0 or got <= 0.0:
        ng(f"{d}: 域外へ出た水か out_intake_g がない(体積 {vol:.6f} m3、{got:.6f} g)")
        return
    rel = abs(got - vol) / vol
    print(f"  {d}: exported water {vol:.6f} m3 x 1 g/m3 vs out_intake_g {got:.6f} g (relative {rel:.2e})")
    if rel > tol:
        ng(f"{d}: out_intake_g が域外へ出た水の体積 × 濃度に一致しない(相対 {rel:.2e})")


def gwc(d, k):
    dv = float((field(d, "Hgc", 0) - field(d, "Hgc", k)).sum()) * ACELL
    t = k * 3600.0
    v = [r for r in ledger_rows(d) if abs(r["time_s"] - t) < 1e-6]
    if not v or dv <= 0.0:
        ng(f"{d}: 分布 {k} の時刻の台帳の行か、管路の貯留の減少がない")
        return
    got = v[0]["in_gwc_g"]
    rel = abs(got - dv) / dv
    print(f"  {d}: water pumped from the conduit {dv:.6f} m3 x 1 g/m3 vs in_gwc_g {got:.6f} g (relative {rel:.2e})")
    if rel > 1e-6:
        ng(f"{d}: in_gwc_g が管路から汲んだ水の体積 × 濃度に一致しない(相対 {rel:.2e})")


def active(d, k):
    h0 = field(d, "H", 0)
    h1 = field(d, "H", k)
    parts = []
    for r in range(4):
        for c in range(4):
            nm = NAMES[r][c]
            dh = float(comp(h1, r, c).mean() - comp(h0, r, c).mean())
            parts.append(f"{nm} {dh:+.3f}")
            want = MOVE[nm]
            if want == 0 and abs(dh) > 1e-6:
                ng(f"{d}: 構造物のない区画 {nm} の水深が変わった({dh:+.6f} m)")
            if want != 0 and want * dh < 0.05:
                ng(f"{d}: 区画 {nm} の水深が期待どおりに動いていない({dh:+.6f} m)")
    print(f"  {d}: change of the mean depth by frame {k} (m): " + ", ".join(parts))


def main(argv):
    if len(argv) < 3:
        print(__doc__ or "usage: Check_wqstruct.py MODE DIR ...")
        return 2
    mode, d = argv[1], argv[2]
    if mode == "conc":
        conc(d, int(argv[3]), float(argv[4]) if len(argv) > 4 else 1e-3)
    elif mode == "gwconc":
        gwconc(d, int(argv[3]))
    elif mode == "tank":
        tank(d, int(argv[3]), int(argv[4]), int(argv[5]))
    elif mode == "ledger":
        ledger(d)
    elif mode == "intake":
        intake(d, float(argv[3]), float(argv[4]))
    elif mode == "gwc":
        gwc(d, int(argv[3]))
    elif mode == "active":
        active(d, int(argv[3]))
    else:
        print("unknown mode", mode)
        return 2
    print(f"wqstruct {mode}: {'PASS' if rc == 0 else 'FAIL'}")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
