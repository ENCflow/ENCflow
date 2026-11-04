#!/usr/bin/env python3
# =====================================================================
# evapdry: 土の乾き具合で抑える地下水の段の蒸発散(evap_hglim。developer.md
# §27.2)の reference 非依存検定
#   decay DIR PET HLIM [T1] : 時刻 T1 時間(既定 1.5 = 雨の後)以降の地下の貯留
#                        (Log.txt の S_grnd。f_disp_debug=1 の全有効桁)が、
#                        dhg/dt = −E·min(1, hg/HLIM) の解析解に一致する
#                        (E = PET [mm/day]、HLIM [m]。HLIM に 0 を与えると抑制
#                        なし = hg は速さ E で線形に減って 0 で止まる)。
#                        ステップ内で厳密に解くので、許容は丸めの範囲
#                        (T1 の値 H1 に対して相対 1e-9)
#   evbal DIR AREA       : 最終の総水量 + 蒸発散の総量 = 雨の総量(雨の濃度
#                        1 mg/L なので台帳の in_rain_g [g] = 雨の体積 [m3]。
#                        AREA = 有効セルの総面積 m2。相対 1e-6 = es15.7 の精度)
#   ledger DIR           : 水質の台帳が閉じる(閉領域: 入力 = 現在の質量。蒸発では
#                        物質が残る。相対 1e-6)
# =====================================================================
import csv
import math
import os
import sys

rc = 0


def ng(msg):
    global rc
    print("  NG:", msg)
    rc = 1


def log_rows(d):
    """Log.txt の (時刻 h, S_surf, S_grnd, S_total) の並び。"""
    out = []
    for line in open(os.path.join(d, "Log.txt")):
        p = line.split()
        if len(p) < 5 or ":" not in p[0] or not p[0][0].isdigit():
            continue
        hh, mm, ss = p[0].split(":")
        out.append((float(hh) + float(mm) / 60 + float(ss) / 3600,
                    float(p[2]), float(p[3]), float(p[4])))
    return out


def expected(h1, tau, e, hl):
    """解析解: 時刻 T1 に h1、そこから経過時間 tau [s] の貯留 [m]。"""
    if hl <= 0.0:                          # 抑制なし(あるだけ引く)
        return max(h1 - e * tau, 0.0)
    if h1 > hl:
        t_lin = (h1 - hl) / e              # hl に下がるまでの時間
        if tau <= t_lin:
            return h1 - e * tau
        return hl * math.exp(-e * (tau - t_lin) / hl)
    return h1 * math.exp(-e * tau / hl)


def decay(d, pet, hl, t1):
    e = pet * 1e-3 / 86400.0               # m/s
    rows = [r for r in log_rows(d) if r[0] >= t1 - 1e-9]
    if len(rows) < 3:
        ng(f"{d}: Log.txt に {t1} 時間以降の行が足りない")
        return
    ta, h1 = rows[0][0], rows[0][2]
    if rows[0][1] != 0.0:
        ng(f"{d}: 時刻 {t1} 時間に地表の水が残っている(S_surf = {rows[0][1]})")
    worst = 0.0
    for t, _, hg, _ in rows[1:]:
        ex = expected(h1, (t - ta) * 3600.0, e, hl)
        worst = max(worst, abs(hg - ex) / h1)
    t, _, hg, _ = rows[-1]
    print(f"  {d}: H1 = {h1:.12f} m at {ta:.2f} h; at {t:.2f} h S_grnd {hg:.12f} m, "
          f"expected {expected(h1, (t - ta) * 3600.0, e, hl):.12f} m; "
          f"max deviation / H1 = {worst:.2e} over {len(rows) - 1} rows")
    if worst > 1e-9:
        ng(f"{d}: 地下の貯留が解析解と一致しない(H1 に対して {worst:.2e})")


def evbal(d, area):
    rows = list(csv.reader(open(os.path.join(d, "wq.csv"))))
    v = dict(zip(rows[0], (float(x) for x in rows[-1])))
    rain = v["in_rain_g"] / area            # 雨の濃度 1 g/m3 → 体積 m3 → 領域平均の水深 m
    e = list(csv.DictReader(open(os.path.join(d, "evap.csv"))))
    et = float(e[-1]["ev_total_m3"]) / area
    s = log_rows(d)[-1][3]
    rel = abs(s + et - rain) / rain
    print(f"  {d}: final S_total {s:.10f} m + ET {et:.10f} m = {s + et:.10f} m, "
          f"rain total {rain:.10f} m (relative {rel:.2e})")
    if rel > 1e-6:
        ng(f"{d}: 総水量 + 蒸発散 が雨の総量と一致しない(相対 {rel:.2e})")


def ledger(d):
    rows = list(csv.reader(open(os.path.join(d, "wq.csv"))))
    head = rows[0]
    worst = 0.0
    for r in rows[1:]:
        v = dict(zip(head, (float(x) for x in r)))
        inp = v["in_rain_g"]
        mass = sum(v[c] for c in ("mass_surface_g", "mass_gw_g", "mass_pool_g", "mass_dam_g", "mass_rs_g"))
        if inp > 0:
            worst = max(worst, abs(inp - mass) / inp)
    print(f"  {d}: wq ledger closure, max relative residual {worst:.2e}")
    if worst > 1e-6:
        ng(f"{d}: 水質の台帳が閉じない(相対 {worst:.2e})")


def main(argv):
    if len(argv) < 3:
        print("usage: Check_evapdry.py decay|evbal|ledger DIR [ARG...]")
        return 2
    mode, d = argv[1], argv[2]
    if mode == "decay":
        decay(d, float(argv[3]), float(argv[4]), float(argv[5]) if len(argv) > 5 else 1.5)
    elif mode == "evbal":
        evbal(d, float(argv[3]))
    elif mode == "ledger":
        ledger(d)
    else:
        print("unknown mode", mode)
        return 2
    print(f"evapdry {mode}: {'PASS' if rc == 0 else 'FAIL'}")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
