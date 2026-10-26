#!/usr/bin/env python3
"""vzzone: VZ 区画・共有柱・出口の検定(developer.md §87)

Python 標準ライブラリのみ。使い方:
  python3 Check_vzzone.py base    result                 # param.txt の結果
  python3 Check_vzzone.py dup     result result_dup      # 柱を共有 vs 複製
  python3 Check_vzzone.py avg     result_avg             # 雨の分布 + 柱内面積平均
  python3 Check_vzzone.py restart result result_restart  # 途中保存 → 再開 = 連続計算

base の検定項目:
  (a) 孤立した受水セルの水深 = 雨 + 配分どおりの移送量
      O_a = R + (0.6·V1 + V2)/A、O_b = R + 0.4·V1/A、O_c = R(V は区画の移送量)
  (b) 地表水の総量(Log の S_surf)= 受水セルへの雨 + 全区画の移送量の和
      (同じ受水セルに複数区画から渡る量が一度だけ加わる)
  (c) Log の S_total の変化 = 雨 − 系外流出/全面積
  (d) 区画の収支残差が非線形残差の予算内
"""
import csv
import math
import os
import sys

DT = 5.0
DT_PRUPDATE = 60.0
MB_RATE = 1.0e-11
A = 10.0 * 10.0
NVAL = 43                       # 領域内セル数(VZ 40 + 受水 3)
RAIN_TABLE = [(0, 1), (60, 1), (61, 50), (180, 50), (181, 0), (9999, 0)]   # (min, mm/h)

failed = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        failed.append(msg)


def read_csv(path):
    with open(path, newline="") as f:
        rows = list(csv.reader(f))
    head = [h.strip() for h in rows[0]]
    data = [[float(v) for v in r] for r in rows[1:] if r]
    return head, data


def read_log(path):
    out = {}
    with open(path) as f:
        for line in f:
            s = line.split()
            if len(s) < 5 or ":" not in s[0] or s[0].startswith("time"):
                continue
            h, m, sec = s[0].split(":")
            t = int(h) * 3600 + int(m) * 60 + float(sec)
            out[round(t)] = (float(s[2]), float(s[3]), float(s[4]))    # S_surf, S_grnd, S_total
    return out


def read_probe(path):
    rows = []
    with open(path) as f:
        for line in f:
            if line.startswith("#"):
                continue
            v = [float(x) for x in line.replace(",", " ").split()]
            rows.append(v)
    return rows                 # t(hour), t(min), z, h, ...


def rain_rate(tmin, table=RAIN_TABLE):
    for (t1, r1), (t2, r2) in zip(table[:-1], table[1:]):
        if t1 <= tmin <= t2:
            return r1 + (r2 - r1) * (tmin - t1) / (t2 - t1)
    return 0.0


def rain_total(tend, table=RAIN_TABLE, scale=1.0 / 3.6e6):
    """makepre の更新規則(初期化時と DT_PRUPDATE ごと)での地上雨量の積算 (m)"""
    nstep = int(round(tend / DT))
    idt = int(round(DT_PRUPDATE / DT))
    rate = rain_rate(0.0, table) * scale
    total = 0.0
    for it in range(1, nstep + 1):
        if it % idt == 0:
            rate = rain_rate(it * DT / 60.0, table) * scale
        total += rate * DT
    return total


def zone_rows(res):
    head, data = read_csv(os.path.join(res, "vz_zone.csv"))
    return head, data


def last_by_zone(head, data):
    iz = head.index("zone")
    out = {}
    for r in data:
        out[int(r[iz])] = r
    return out


def check_base(res):
    print("== vzzone base: " + res)
    hz, zone = zone_rows(res)
    last = last_by_zone(hz, zone)
    it = hz.index("time(s)")
    ivint, ivext, ires, ivin, iarea = (hz.index("vsurface(m3)"), hz.index("vexternal(m3)"),
                                       hz.index("residual(m3)"), hz.index("vin(m3)"), hz.index("area(m2)"))
    tend = last[1][it]
    R = rain_total(tend)
    v1, v2, v3 = last[1][ivint], last[2][ivint], last[3][ivint]
    check(v3 == 0.0 and last[3][ivext] > 0.0 and last[1][ivext] == 0.0 and last[2][ivext] == 0.0,
          "(a) zones 1-2 deliver to surface cells, zone 3 to outside the system")

    # (a) 受水セルの水深(プローブは 5 桁表示なので 1e-5 m の許容)
    expect = {1: R + (0.6 * v1 + v2) / A, 2: R + 0.4 * v1 / A, 3: R}
    for k, name in [(1, "O_a"), (2, "O_b"), (3, "O_c")]:
        pr = read_probe(os.path.join(res, "probes", "probe%04d.csv" % k))
        h = pr[-1][3]
        check(abs(h - expect[k]) < 1.5e-5, "(a) %s depth %.5f m = expected %.5f m" % (name, h, expect[k]))

    # (b) 地表水の総量 = 受水セル 3 つへの雨 + 移送量の和
    log = read_log(os.path.join(res, "Log.txt"))
    ssurf = log[round(tend)][0]
    vol = ssurf * NVAL * A
    exp_ = 3 * R * A + v1 + v2
    check(abs(vol - exp_) / exp_ < 1e-12, "(b) surface water volume %.10e m3 = rain on receiving cells + "
          "transfers %.10e m3 (rel %.1e)" % (vol, exp_, abs(vol - exp_) / exp_))

    # (c) S_total の収支(全セルに雨、系外流出は区画 3 のみ)
    s0 = log[0][2]
    worst = 0.0
    rows = {}
    for r in zone:
        rows.setdefault(round(r[it]), {})[int(r[hz.index("zone")])] = r
    for t, v in log.items():
        if t == 0 or t not in rows:
            continue
        vext = sum(rows[t][z][ivext] for z in rows[t])
        exp_ = s0 + rain_total(t) - vext / (NVAL * A)
        worst = max(worst, abs(v[2] - exp_))
    check(worst < 1e-12 + MB_RATE * tend, "(c) Log S_total = S0 + rain - outflow/area (max abs err %.2e m)" % worst)

    # (d) 区画の収支残差
    worst = 0.0
    for r in zone:
        worst = max(worst, abs(r[ires]) / (MB_RATE * r[it] * r[iarea] + 1e-9 * r[ivin]))
    check(worst <= 1.0, "(d) zone water balance residual within the budget (worst ratio %.2e)" % worst)


def check_dup(res1, res2):
    """区画 3 が柱 1 を共有する構成と、柱 1 の複製(柱 3)を参照する構成で、
    区画の応答(列 column を除く全数値)と Log がビット一致する"""
    print("== vzzone dup: %s vs %s" % (res1, res2))
    with open(os.path.join(res1, "vz_zone.csv")) as f1, open(os.path.join(res2, "vz_zone.csv")) as f2:
        l1, l2 = f1.read().splitlines(), f2.read().splitlines()
    same = len(l1) == len(l2)
    for a, b in zip(l1[1:], l2[1:]):
        fa, fb = a.split(","), b.split(",")
        if fa[:2] != fb[:2] or fa[3:] != fb[3:]:
            same = False
    check(same, "zone responses identical whether column 1 is shared or duplicated")
    with open(os.path.join(res1, "Log.txt")) as f1, open(os.path.join(res2, "Log.txt")) as f2:
        check(f1.read() == f2.read(), "Log.txt identical")


def check_avg(res):
    """雨の分布(prmap × 時系列倍率)を柱内面積平均で与える構成の収支"""
    print("== vzzone avg: " + res)
    prmap = []
    with open(os.path.join("data_vzzone", "prmap.txt")) as f:
        for line in f:
            prmap.append([float(x) / 24.0 for x in line.split()])     # mm/day → mm/h
    zmap = []
    with open(os.path.join("data_vzzone", "zone.txt")) as f:
        for line in f:
            zmap.append([int(x) for x in line.split()])
    table = [(0, 1), (60, 1), (61, 50), (180, 50), (181, 0), (9999, 0)]   # 倍率(prmap を mm/h に換算済み)
    hz, zone = zone_rows(res)
    last = last_by_zone(hz, zone)
    it, ivin, iarea, ivext = hz.index("time(s)"), hz.index("vin(m3)"), hz.index("area(m2)"), hz.index("vexternal(m3)")
    tend = last[1][it]
    R = rain_total(tend, table)               # 倍率 × 1 mm/h の積算 (m)
    col = {1: 1, 2: 2, 3: 1}
    msum = {1: 0.0, 2: 0.0}
    mcnt = {1: 0, 2: 0}
    for j, row in enumerate(zmap):
        for i, z in enumerate(row):
            if z > 0:
                msum[col[z]] += prmap[j][i]
                mcnt[col[z]] += 1
    for z in (1, 2, 3):
        exp_ = last[z][iarea] * R * msum[col[z]] / mcnt[col[z]]
        rel = abs(last[z][ivin] - exp_) / exp_
        check(rel < 1e-12, "zone %d input = area x column-mean rainfall (rel %.1e)" % (z, rel))
    # 全体の収支: 雨の総量は prmap の総和(領域内セル)× R
    total_map = sum(prmap[j][i] for j in range(len(zmap)) for i in range(len(zmap[0]))
                    if zmap[j][i] > 0) + 3 * 1.0
    log = read_log(os.path.join(res, "Log.txt"))
    s0 = log[0][2]
    st = log[round(tend)][2]
    vext = last[3][ivext]
    exp_ = s0 + R * total_map / NVAL - vext / (NVAL * A)
    check(abs(st - exp_) < 1e-12 + MB_RATE * tend,
          "Log S_total = S0 + mean rain - outflow/area (abs err %.2e m)" % abs(st - exp_))


def check_restart(res1, res2):
    """途中保存 → 再開の結果が連続計算と一致する(再開後の記録)"""
    print("== vzzone restart: %s vs %s" % (res1, res2))
    for fn in ("vz_zone.csv", "vz_column.csv"):
        with open(os.path.join(res1, fn)) as f1, open(os.path.join(res2, fn)) as f2:
            a = f1.read().splitlines()[1:]
            b = f2.read().splitlines()[1:]
        tail = a[len(a) - len(b):]
        check(len(b) > 0 and tail == b, "%s after the restart identical to the continuous run (%d rows)" % (fn, len(b)))
    la, lb = read_log(os.path.join(res1, "Log.txt")), read_log(os.path.join(res2, "Log.txt"))
    common = [t for t in lb if t in la and t > min(lb)]
    check(len(common) > 0 and all(la[t] == lb[t] for t in common),
          "Log.txt rows after the restart identical (%d rows)" % len(common))


def main():
    mode = sys.argv[1]
    if mode == "base":
        check_base(sys.argv[2])
    elif mode == "dup":
        check_dup(sys.argv[2], sys.argv[3])
    elif mode == "avg":
        check_avg(sys.argv[2])
    elif mode == "restart":
        check_restart(sys.argv[2], sys.argv[3])
    else:
        sys.exit("unknown mode " + mode)
    if failed:
        print("=== vzzone check FAIL (%d) ===" % len(failed))
        sys.exit(1)
    print("=== vzzone check PASS ===")


if __name__ == "__main__":
    main()
