#!/usr/bin/env python3
"""sfzone: 貯留関数法の区画・タンク・出口の検定(developer.md §106)

Python 標準ライブラリのみ。使い方:
  python3 Check_sfzone.py base    result                  # param.txt の結果
  python3 Check_sfzone.py avg     result_avg              # 雨の分布 + 区画内面積平均
  python3 Check_sfzone.py restart result result_restart   # 途中保存 → 再開 = 連続計算
  python3 Check_sfzone.py bflow   result result_bflow     # 区画の基底流(param_bflow.txt)
  python3 Check_sfzone.py dflt    result result_dflt      # 既定値の表示と、明示した値との一致
  python3 Check_sfzone.py sync    result result_sync      # 同期間隔 dt_sfm = 60 s
  python3 Check_sfzone.py partial result_sync result_psync_restart   # 同期区間の途中で保存 → 再開
  python3 Check_sfzone.py steady  result_steady           # 一定の雨での定常 q → r
  python3 Check_sfzone.py mosaic  result result_mosaic    # VZ との併用

タンク(単位面積): dS/dt = r − q、S [mm] = K·q[mm/h]^P。SI では q = c·S^m
(m = 1/P、c = (1000/K)^m / 3.6e6、S [m]、q [m/s])。

base の検定項目:
  (0) 区画の入力 vin = 面積 × 地上雨量の積算(makepre の更新規則で計算)
  (1) 線形貯留(区画 2、P = 1)の貯留 = ステップごとの厳密解
      S_{n+1} = S_eq + (S_n − S_eq)·exp(−Δt/τ)(τ = 3600·K s、S_eq = τ·r)
  (2) 区画 1・3(P = 0.6・0.4)の貯留 = 同じ雨の常微分方程式を細かい刻みの RK4 で
      解いた参照解(時間誤差の許容 sfm_tol = 1e-4 の規模)
  (3) 雨の後の逓減の解析解: r = 0 で S^(1−m) = S1^(1−m) + (m − 1)·c·(t − t1)
      (t1 = 雨が終わった後の最初の記録時刻の S から)
  (4) 出力の q 列 = (S/K)^(1/P)(mm/h)
  (5) 区画の収支残差 = 丸め規模(入力に対し 1e-12)
  (a) 孤立した受水セルの水深 = 雨 + 配分どおりの移送量
      O_a = R + (0.6·V1 + V2)/A、O_b = R + 0.4·V1/A、O_c = R(V は区画の移送量)
  (b) 地表水の総量(Log の S_surf)= 受水セルへの雨 + 全区画の移送量の和
  (c) Log の S_total の変化 = 雨 − 系外流出/全面積(タンクの貯留は S_grnd に入る)
"""
import csv
from fractions import Fraction
import math
import os
import sys

DT = 5.0
DT_PRUPDATE = 60.0
A = 10.0 * 10.0
NVAL = 43                       # 領域内セル数(区画 40 + 受水 3)
RAIN_TABLE = [(0, 1), (60, 1), (61, 50), (180, 50), (181, 0), (9999, 0)]   # (min, mm/h)
TANK = {1: (10.0, 0.6, 0.1), 2: (2.0, 1.0, 1.0), 3: (20.0, 0.4, 0.0)}      # K, P, q0 (mm/h)
KIND = {1: 1, 2: 1, 3: 2}       # 出口 1: 地表セル / 2: 系外
# param_bflow.txt の区画 1 の基底流(namelist)。区画 3 は data_sfzone/base3.txt から読む
BASE1 = [(30.5, 0.0), (90.0, 2.0), (90.0, 4.0), (300.25, 1.0)]             # (min, mm/h)

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
            rows.append([float(x) for x in line.replace(",", " ").split()])
    return rows                 # t(hour), t(min), z, h, ...


def rain_rate(tmin, table=RAIN_TABLE):
    for (t1, r1), (t2, r2) in zip(table[:-1], table[1:]):
        if t1 <= tmin <= t2:
            return r1 + (r2 - r1) * (tmin - t1) / (t2 - t1)
    return 0.0


def rain_steps(nstep, table=RAIN_TABLE):
    """makepre の更新規則(初期化時と DT_PRUPDATE ごと)での各ステップの地上雨量 (m/s)"""
    idt = int(round(DT_PRUPDATE / DT))
    rate = rain_rate(0.0, table) / 3.6e6
    out = []
    for it in range(1, nstep + 1):
        if it % idt == 0:
            rate = rain_rate(it * DT / 60.0, table) / 3.6e6
        out.append(rate)
    return out


def rain_total(tend, table=RAIN_TABLE):
    return sum(r * DT for r in rain_steps(int(round(tend / DT)), table))


def tank_coef(k, p):
    m = 1.0 / p
    return m, (1000.0 / k) ** m / 3.6e6


def qfun(s, m, c):
    return c * s ** m if s > 0.0 else 0.0


def reference_storage(k, p, q0, rates, nsub=10):
    """同じ雨を区分一定で与えた dS/dt = r − c·S^m を RK4(1 ステップを nsub に分割)で解く。
    各ステップ末の S (m) を返す(添字 n = ステップ n の末)"""
    m, c = tank_coef(k, p)
    s = k * q0 ** p / 1000.0
    h = DT / nsub
    out = [s]
    for r in rates:
        for _ in range(nsub):
            k1 = r - qfun(s, m, c)
            k2 = r - qfun(max(s + 0.5 * h * k1, 0.0), m, c)
            k3 = r - qfun(max(s + 0.5 * h * k2, 0.0), m, c)
            k4 = r - qfun(max(s + h * k3, 0.0), m, c)
            s = s + h * (k1 + 2 * k2 + 2 * k3 + k4) / 6.0
        out.append(s)
    return out


def linear_storage(k, q0, rates):
    """線形貯留(P = 1)の区分一定入力の厳密解(各ステップ末の S。m)"""
    tau = 3600.0 * k
    s = k * q0 / 1000.0
    out = [s]
    e = math.exp(-DT / tau)
    for r in rates:
        seq = tau * r
        s = seq + (s - seq) * e
        out.append(s)
    return out


def zone_rows(res):
    return read_csv(os.path.join(res, "sfm_zone.csv"))


def by_zone(head, data):
    iz = head.index("zone")
    out = {}
    for r in data:
        out.setdefault(int(r[iz]), []).append(r)
    return out


def check_base(res):
    print("== sfzone base: " + res)
    hz, zone = zone_rows(res)
    zr = by_zone(hz, zone)
    it, iS, iq, ivin, iarea = (hz.index("time(s)"), hz.index("S(mm)"), hz.index("q(mm/h)"),
                               hz.index("vin(m3)"), hz.index("area(m2)"))
    ires, ivint, ivext, ivst = (hz.index("residual(m3)"), hz.index("vsurface(m3)"),
                                hz.index("vexternal(m3)"), hz.index("vstore(m3)"))
    tend = zr[1][-1][it]
    nstep = int(round(tend / DT))
    rates = rain_steps(nstep)

    # (0) 入力
    worst = 0.0
    for z in (1, 2, 3):
        for r in zr[z]:
            n = int(round(r[it] / DT))
            exp_ = r[iarea] * sum(x * DT for x in rates[:n])
            worst = max(worst, abs(r[ivin] - exp_) / exp_)
    check(worst < 1e-12, "(0) zone input = area x ground rainfall (worst rel %.1e)" % worst)

    # (1) 線形貯留の厳密解
    k, p, q0 = TANK[2]
    sref = linear_storage(k, q0, rates)
    worst = 0.0
    for r in zr[2]:
        n = int(round(r[it] / DT))
        worst = max(worst, abs(r[iS] / 1000.0 - sref[n]) / sref[n])
    check(worst < 1e-6, "(1) zone 2 (P = 1) storage = exact linear-reservoir solution (worst rel %.2e)" % worst)

    # (2) 非線形タンクの RK4 参照解(時間誤差の許容の規模)
    for z in (1, 3):
        k, p, q0 = TANK[z]
        sref = reference_storage(k, p, q0, rates)
        m, c = tank_coef(k, p)
        ws = wq = 0.0
        for r in zr[z]:
            n = int(round(r[it] / DT))
            ws = max(ws, abs(r[iS] / 1000.0 - sref[n]) / sref[n])
            qr = qfun(sref[n], m, c) * 3.6e6
            wq = max(wq, abs(r[iq] - qr) / qr)
        check(ws < 1e-5 and wq < 2e-5, "(2) zone %d (P = %.1f) storage and outflow = RK4 reference "
              "(worst rel %.2e, %.2e)" % (z, p, ws, wq))

    # (3) 雨の後の逓減の解析解
    nend = max(i for i, x in enumerate(rates) if x > 0.0) + 1      # 最後に雨のあるステップ
    for z in (1, 2, 3):
        k, p, q0 = TANK[z]
        m, c = tank_coef(k, p)
        rows = [r for r in zr[z] if r[it] >= nend * DT]
        t1, s1 = rows[0][it], rows[0][iS] / 1000.0
        worst = 0.0
        for r in rows[1:]:
            if m == 1.0:
                sa = s1 * math.exp(-c * (r[it] - t1))
            else:
                sa = (s1 ** (1.0 - m) + (m - 1.0) * c * (r[it] - t1)) ** (1.0 / (1.0 - m))
            worst = max(worst, abs(r[iS] / 1000.0 - sa) / sa)
        check(worst < 1e-5, "(3) zone %d recession after %.0f s = analytic solution (%d rows, worst rel %.2e)"
              % (z, t1, len(rows) - 1, worst))

    # (4) q 列 = (S/K)^(1/P)
    worst = 0.0
    for z in (1, 2, 3):
        k, p, q0 = TANK[z]
        for r in zr[z]:
            qa = (r[iS] / k) ** (1.0 / p)
            worst = max(worst, abs(r[iq] - qa) / qa)
    check(worst < 1e-12, "(4) column q = (S/K)^(1/P) (worst rel %.1e)" % worst)

    # (5) 区画の収支残差
    worst = 0.0
    for r in zone:
        worst = max(worst, abs(r[ires]) / max(r[ivin], r[ivst]))
    check(worst < 1e-12, "(5) zone water balance residual at rounding level (worst rel %.1e)" % worst)

    # (a) 受水セルの水深(プローブは 5 桁表示なので 1e-5 m の許容)
    last = {z: zr[z][-1] for z in zr}
    R = rain_total(tend)
    v1, v2, v3 = last[1][ivint], last[2][ivint], last[3][ivint]
    check(v3 == 0.0 and last[3][ivext] > 0.0 and last[1][ivext] == 0.0 and last[2][ivext] == 0.0,
          "(a) zones 1-2 deliver to surface cells, zone 3 to outside the system")
    expect = {1: R + (0.6 * v1 + v2) / A, 2: R + 0.4 * v1 / A, 3: R}
    for kk, name in [(1, "O_a"), (2, "O_b"), (3, "O_c")]:
        pr = read_probe(os.path.join(res, "probes", "probe%04d.csv" % kk))
        h = pr[-1][3]
        check(abs(h - expect[kk]) < 1.5e-5, "(a) %s depth %.5f m = expected %.5f m" % (name, h, expect[kk]))

    # (b) 地表水の総量 = 受水セル 3 つへの雨 + 移送量の和
    log = read_log(os.path.join(res, "Log.txt"))
    ssurf = log[round(tend)][0]
    vol = ssurf * NVAL * A
    exp_ = 3 * R * A + v1 + v2
    check(abs(vol - exp_) / exp_ < 1e-12, "(b) surface water volume %.10e m3 = rain on receiving cells + "
          "transfers %.10e m3 (rel %.1e)" % (vol, exp_, abs(vol - exp_) / exp_))

    # (c) S_total の収支(全セルに雨、系外流出は区画 3 のみ)
    check_total(log, hz, zone, None, "(c)")


def check_total(log, hz, zone, kind, tag, table=RAIN_TABLE, extra_ext=None):
    """Log の S_total = S0 + 雨 + 地表へ渡る基底流 − 系外流出(基底流を除く)/全面積"""
    it, iz, ivext = hz.index("time(s)"), hz.index("zone"), hz.index("vexternal(m3)")
    ib = hz.index("vbase(m3)") if "vbase(m3)" in hz else None
    kind = kind or KIND
    rows = {}
    for r in zone:
        rows.setdefault(round(r[it]), {})[int(r[iz])] = r
    s0 = log[0][2]
    worst = 0.0
    for t, v in log.items():
        if t == 0 or t not in rows:
            continue
        vext = sum(rows[t][z][ivext] for z in rows[t])
        vb_in = vb_ext = 0.0
        if ib is not None:
            vb_in = sum(rows[t][z][ib] for z in rows[t] if kind[z] == 1)
            vb_ext = sum(rows[t][z][ib] for z in rows[t] if kind[z] == 2)
        if extra_ext is not None:
            vext += extra_ext.get(t, 0.0)
        exp_ = s0 + rain_total(t, table) + (vb_in - (vext - vb_ext)) / (NVAL * A)
        worst = max(worst, abs(v[2] - exp_))
    check(worst < 2e-12, "%s Log S_total = S0 + rain - outflow/area (max abs err %.2e m)" % (tag, worst))


def check_avg(res):
    """雨の分布(prmap × 時系列倍率)を区画内面積平均で与える構成の収支"""
    print("== sfzone avg: " + res)
    prmap, zmap = [], []
    with open(os.path.join("data_sfzone", "prmap.txt")) as f:
        for line in f:
            prmap.append([float(x) / 24.0 for x in line.split()])     # mm/day → mm/h
    with open(os.path.join("data_sfzone", "zone.txt")) as f:
        for line in f:
            zmap.append([int(x) for x in line.split()])
    hz, zone = zone_rows(res)
    zr = by_zone(hz, zone)
    it, ivin, iarea = hz.index("time(s)"), hz.index("vin(m3)"), hz.index("area(m2)")
    tend = zr[1][-1][it]
    R = rain_total(tend)                      # 倍率 × 1 mm/h の積算 (m)
    msum, mcnt = {1: 0.0, 2: 0.0, 3: 0.0}, {1: 0, 2: 0, 3: 0}
    for j, row in enumerate(zmap):
        for i, z in enumerate(row):
            if z > 0:
                msum[z] += prmap[j][i]
                mcnt[z] += 1
    for z in (1, 2, 3):
        exp_ = zr[z][-1][iarea] * R * msum[z] / mcnt[z]
        rel = abs(zr[z][-1][ivin] - exp_) / exp_
        check(rel < 1e-12, "zone %d input = area x zone-mean rainfall (rel %.1e)" % (z, rel))
    total_map = sum(prmap[j][i] for j in range(len(zmap)) for i in range(len(zmap[0]))
                    if zmap[j][i] > 0) + 3 * 1.0
    log = read_log(os.path.join(res, "Log.txt"))
    st = log[round(tend)][2]
    vext = zr[3][-1][hz.index("vexternal(m3)")]
    exp_ = log[0][2] + R * total_map / NVAL - vext / (NVAL * A)
    check(abs(st - exp_) < 2e-12, "Log S_total = S0 + mean rain - outflow/area (abs err %.2e m)" % abs(st - exp_))


def base_integral(series, tsec):
    """区分線形(範囲外は端の値を保持)の 0〜tsec の厳密な積分 (mm/h·s)。series は (min, mm/h)"""
    pts = [(Fraction(t) * 60, Fraction(q)) for t, q in series]
    t, total = Fraction(tsec), Fraction(0)
    if t > 0 and pts[0][0] > 0:
        total += (min(t, pts[0][0])) * pts[0][1]
    for (t0, q0), (t1, q1) in zip(pts[:-1], pts[1:]):
        a, b = max(Fraction(0), t0), min(t, t1)
        if b <= a:
            continue
        fa = q0 + (q1 - q0) * (a - t0) / (t1 - t0)
        fb = q0 + (q1 - q0) * (b - t0) / (t1 - t0)
        total += (b - a) * (fa + fb) / 2
    if t > pts[-1][0]:
        total += (t - max(Fraction(0), pts[-1][0])) * pts[-1][1]
    return total


def check_bflow(res0, res):
    """区画の基底流(param_bflow.txt)を param.txt の結果と比べる"""
    print("== sfzone bflow: %s vs %s" % (res0, res))
    base3 = []
    with open(os.path.join("data_sfzone", "base3.txt")) as f:
        for line in f:
            if line.split():
                t, q = line.split()[:2]
                base3.append((Fraction(t), Fraction(q)))
    series = {1: BASE1, 3: base3}
    h0, _ = zone_rows(res0)
    hz, zone = zone_rows(res)
    check("vbase(m3)" not in h0 and hz[:len(h0)] == h0 and hz[len(h0):] == ["vbase(m3)"],
          "(e) sfm_zone.csv has the vbase column only when a baseflow is given (appended last)")
    it, iz, iarea, ib = hz.index("time(s)"), hz.index("zone"), hz.index("area(m2)"), hz.index("vbase(m3)")
    ivd, ivint, ivext = hz.index("vdrain(m3)"), hz.index("vsurface(m3)"), hz.index("vexternal(m3)")
    worst, nrow = 0.0, 0
    for r in zone:
        z = int(r[iz])
        exp_ = 0.0
        if z in series:
            exp_ = float(base_integral(series[z], Fraction(r[it])) / Fraction(3600000)) * r[iarea]
        err = abs(r[ib] - exp_) / max(abs(exp_), 1e-30) if exp_ != 0.0 else abs(r[ib])
        worst = max(worst, err)
        nrow += 1
    check(worst < 1e-12, "(e) cumulative baseflow = exact integral x zone area (%d rows, worst rel %.1e)"
          % (nrow, worst))
    with open(os.path.join(res0, "sfm_zone.csv")) as f0, open(os.path.join(res, "sfm_zone.csv")) as f1:
        l0, l1 = f0.read().splitlines()[1:], f1.read().splitlines()[1:]
    keep = [h0.index(k) for k in ("time(s)", "zone", "area(m2)", "rain(mm/h)", "q(mm/h)", "S(mm)", "vin(m3)",
                                  "vstore(m3)", "vdrain(m3)", "residual(m3)")]
    same = len(l0) == len(l1) and all([a.split(",")[k] for k in keep] == [b.split(",")[k] for k in keep]
                                      for a, b in zip(l0, l1))
    check(same, "(f) the tank side (rain, q, S, vin, vstore, vdrain, residual) identical to the run without baseflow")
    worst = 0.0
    for r in zone:
        z = int(r[iz])
        out = r[ivint] if KIND[z] == 1 else r[ivext]
        other = r[ivext] if KIND[z] == 1 else r[ivint]
        exp_ = r[ivd] + r[ib]
        worst = max(worst, abs(out - exp_) / max(exp_, 1e-30), abs(other))
    check(worst < 1e-13, "(g) outlet volume = outflow + baseflow (worst rel %.1e)" % worst)
    log = read_log(os.path.join(res, "Log.txt"))
    check_total(log, hz, zone, None, "(h)")


def check_restart(res1, res2):
    """途中保存 → 再開の結果が連続計算と一致する(再開後の記録)"""
    print("== sfzone restart: %s vs %s" % (res1, res2))
    with open(os.path.join(res1, "sfm_zone.csv")) as f1, open(os.path.join(res2, "sfm_zone.csv")) as f2:
        a = f1.read().splitlines()[1:]
        b = f2.read().splitlines()[1:]
    tail = a[len(a) - len(b):]
    check(len(b) > 0 and tail == b, "sfm_zone.csv after the restart identical to the continuous run (%d rows)"
          % len(b))
    la, lb = read_log(os.path.join(res1, "Log.txt")), read_log(os.path.join(res2, "Log.txt"))
    common = [t for t in lb if t in la and t > min(lb)]
    check(len(common) > 0 and all(la[t] == lb[t] for t in common),
          "Log.txt rows after the restart identical (%d rows)" % len(common))


def check_dflt(res1, res2, screen):
    """既定値(P・q0・数値制御)が表示され、同じ値を明示した計算とビット一致する"""
    print("== sfzone defaults: %s vs %s" % (res1, res2))
    with open(screen) as f:
        lines = [x for x in f.read().splitlines() if "(default)" in x and x.startswith("sfm:")]
    names = ["dt_sfm", "sfm_tol", "sfm_dt_min", "sfm_p(1)", "sfm_q0_mmh(1)"]
    check(all(any(("sfm: " + n + " = ") in x for x in lines) for n in names),
          "adopted defaults are displayed with (default) (%d lines)" % len(lines))
    nsame = 0
    for fn in ("sfm_zone.csv", "Log.txt", os.path.join("probes", "probe0001.csv"),
               os.path.join("probes", "probe0002.csv")):
        with open(os.path.join(res1, fn)) as f1, open(os.path.join(res2, fn)) as f2:
            nsame += (f1.read() == f2.read())
    check(nsame == 4, "results identical to the explicit values (%d of 4 files)" % nsame)


def reference_by_zone(nstep, rates):
    """区画ごとの参照解(各ステップ末の S。区画 2 は線形貯留の厳密解、ほかは RK4)"""
    ref = {}
    for z in (1, 2, 3):
        k, p, q0 = TANK[z]
        ref[z] = linear_storage(k, q0, rates) if p == 1.0 else reference_storage(k, p, q0, rates)
    return ref


def check_sync(res1, res2):
    """dt_sfm = 60 s(区間 12 ステップの雨を区分一定で受ける)の結果を参照解・毎ステップ同期と比べる"""
    print("== sfzone sync: %s vs %s" % (res1, res2))
    h1, z1 = zone_rows(res1)
    h2, z2 = zone_rows(res2)
    it, iz = h2.index("time(s)"), h2.index("zone")
    iS, ires, ivin, ivst = h2.index("S(mm)"), h2.index("residual(m3)"), h2.index("vin(m3)"), h2.index("vstore(m3)")
    check(len(z1) == len(z2), "same number of records (%d)" % len(z1))
    tend = z2[-1][it]
    nstep = int(round(tend / DT))
    ref = reference_by_zone(nstep, rain_steps(nstep))
    worst = 0.0
    for r in z2:
        n = int(round(r[it] / DT))
        sr = ref[int(r[iz])][n]
        if sr > 0.0:
            worst = max(worst, abs(r[iS] / 1000.0 - sr) / sr)
    check(worst < 1e-4, "storage at the synchronisation times = reference solution within sfm_tol "
          "(worst rel %.2e)" % worst)
    win = max(abs(a[ivin] - b[ivin]) / a[ivin] for a, b in zip(z1, z2))
    check(win < 1e-12, "the same input reaches the tanks as with every-step synchronisation (worst rel %.1e)" % win)
    worst = max(abs(r[ires]) / max(r[ivin], r[ivst]) for r in z2)
    check(worst < 1e-12, "zone water balance residual at rounding level (worst rel %.1e)" % worst)
    log = read_log(os.path.join(res2, "Log.txt"))
    check_total(log, h2, z2, None, "(sync)")


def check_partial(res1, res2):
    """同期区間の途中で保存 → 再開した計算(dispose が残りのステップを同期して保存)を、
    連続計算(param_sync.txt)と比べる。区間の切れ目が 1 か所変わるだけなので、貯留の差は
    時間誤差の許容の規模に収まり、収支は丸め規模で閉じる"""
    print("== sfzone partial-interval save: %s vs %s" % (res1, res2))
    h1, z1 = zone_rows(res1)
    h2, z2 = zone_rows(res2)
    iS, ires, ivin, ivst = h2.index("S(mm)"), h2.index("residual(m3)"), h2.index("vin(m3)"), h2.index("vstore(m3)")
    tail = z1[len(z1) - len(z2):]
    worst = max(abs(a[iS] - b[iS]) / a[iS] for a, b in zip(tail, z2) if a[iS] > 0.0)
    check(len(z2) > 0 and worst < 1e-4, "storage after the restart agrees with the continuous run "
          "(%d rows, worst rel %.2e)" % (len(z2), worst))
    win = max(abs(a[ivin] - b[ivin]) / a[ivin] for a, b in zip(tail, z2))
    check(win < 1e-12, "the input is carried over the save (worst rel %.1e)" % win)
    worst = max(abs(r[ires]) / max(r[ivin], r[ivst]) for r in z2)
    check(worst < 1e-12, "zone water balance residual at rounding level after the restart (worst rel %.1e)" % worst)


def check_steady(res):
    """一定の雨 r = 10 mm/h を 48 h: q → r、S = K·r^P"""
    print("== sfzone steady: " + res)
    hz, zone = zone_rows(res)
    zr = by_zone(hz, zone)
    iq, iS = hz.index("q(mm/h)"), hz.index("S(mm)")
    for z in (1, 2, 3):
        k, p, q0 = TANK[z]
        r = zr[z][-1]
        eq = abs(r[iq] - 10.0) / 10.0
        es = abs(r[iS] - k * 10.0 ** p) / (k * 10.0 ** p)
        check(eq < 1e-6 and es < 1e-6, "zone %d at 48 h: q = %.10f mm/h -> 10 (rel %.1e), S = K r^P (rel %.1e)"
              % (z, r[iq], eq, es))


def check_mosaic(res0, res):
    """VZ との併用: 貯留関数の区画 1・2 と受水セルは param.txt と一致、全体の収支"""
    print("== sfzone mosaic: %s vs %s" % (res0, res))
    with open(os.path.join(res0, "sfm_zone.csv")) as f0, open(os.path.join(res, "sfm_zone.csv")) as f1:
        l0 = [x for x in f0.read().splitlines()[1:] if x.split(",")[1] in ("1", "2")]
        l1 = f1.read().splitlines()[1:]
    check(len(l1) > 0 and l0 == l1, "SFM zones 1-2 identical to the run without VZ (%d rows)" % len(l1))
    nsame = 0
    for k in (1, 2, 3):
        fn = os.path.join("probes", "probe%04d.csv" % k)
        with open(os.path.join(res0, fn)) as f0, open(os.path.join(res, fn)) as f1:
            nsame += (f0.read() == f1.read())
    check(nsame == 3, "receiving cells O_a, O_b, O_c identical (%d of 3)" % nsame)
    hv, vz = read_csv(os.path.join(res, "vz_zone.csv"))
    itv, ivx = hv.index("time(s)"), hv.index("vexternal(m3)")
    ext = {round(r[itv]): r[ivx] for r in vz}
    hz, zone = zone_rows(res)
    log = read_log(os.path.join(res, "Log.txt"))
    # VZ の柱の非線形残差の予算(mb_rate = 1e-11 m/s)の分だけ許容を広げる
    tend = max(log)
    s0 = log[0][2]
    worst = 0.0
    for t, v in log.items():
        if t == 0 or t not in ext:
            continue
        exp_ = s0 + rain_total(t) - ext[t] / (NVAL * A)
        worst = max(worst, abs(v[2] - exp_))
    check(worst < 2e-12 + 1e-11 * tend, "Log S_total = S0 + rain - VZ outflow/area (max abs err %.2e m)" % worst)


def main():
    mode = sys.argv[1]
    if mode == "base":
        check_base(sys.argv[2])
    elif mode == "avg":
        check_avg(sys.argv[2])
    elif mode == "restart":
        check_restart(sys.argv[2], sys.argv[3])
    elif mode == "bflow":
        check_bflow(sys.argv[2], sys.argv[3])
    elif mode == "dflt":
        check_dflt(sys.argv[2], sys.argv[3], sys.argv[4])
    elif mode == "sync":
        check_sync(sys.argv[2], sys.argv[3])
    elif mode == "partial":
        check_partial(sys.argv[2], sys.argv[3])
    elif mode == "steady":
        check_steady(sys.argv[2])
    elif mode == "mosaic":
        check_mosaic(sys.argv[2], sys.argv[3])
    else:
        sys.exit("unknown mode " + mode)
    if failed:
        print("=== sfzone check FAIL (%d) ===" % len(failed))
        sys.exit(1)
    print("=== sfzone check PASS ===")


if __name__ == "__main__":
    main()
