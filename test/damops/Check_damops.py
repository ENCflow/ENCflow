#!/usr/bin/env python3
# =====================================================================
# damops: reference 非依存の検定(ダムの運転則。developer.md §131)
#   rules <result_dir>   : 各ダム CSV の記録行で
#     - 流入 = 1 歩前のソースの流量(孤立した捕捉帯。セットアップの確認)
#     - ダム 1・2・7: 床(制限水位)より上なら放流 = 運転則の式、
#       床にいる行は min(使える流入, 式) ≤ 放流 ≤ 式(使える流入は流入、
#       追加の放流工 7 では主放流 6 の後の残り)。水位は床を下回らない。
#       最後の行は床に戻って流入をそのまま流している
#     - ダム 3・5: 放流 = 与えた放流量の時系列(5 はダム 3 の湖と同じ水位)
#     - ダム 4: 水位 = 与えた水位の時系列(t = 0 を含む)、
#       放流 = 流入 − (V(H(t)) − V(H(t − dt))) / dt
#     - ダム 6: 放流 = 0.6 × 流入(従来の一定率カット)
#     - スピル 0
#     - Log.txt の S × 有効セル面積 = 初期貯水量 + ソースの累計体積
#       (閉じた系の体積保存。ソースは各歩の終わりの時刻の流量 × dt)
#   restart <result> <result_rt2> <t_restart_min> : リスタートの継続
#     (result_rt2)のダム CSV の行と Log.txt の S が、再開時刻より後で
#     通し計算と一致する(再開の最初の行の Qin・Qout は保存しない診断量
#     なので比べない)
#   許容: CSV の H・Q は f13.4 の印字(±5e-5)に余裕を見て 1.5e-4、
#   S は 1e-9 m
#   パラメータは param.txt と同じ値をここに書いている(変えるときは両方)
# =====================================================================
import os
import sys

DT = 1.0                                  # 時間刻み (s)
HV = [(100.0, 0.0), (105.0, 2.0e4), (112.0, 6.0e4)]
TOLQ = 1.5e-4
TOLH = 1.5e-4
NVALID = 285                              # 有効セル数(mask.txt)
AREA = 10.0 * 10.0                        # セル面積 (m2)
V0 = 1.2e4 + 1.2e4 + 1.6e4 + 1.6e4 + 4.0e3   # 初期貯水量(ダム 1, 2, 3, 4, 6)

def mins(series):
    return [(60.0 * t, v) for (t, v) in series]

S_TRI = mins([(0, 0.2), (60, 1.7), (180, 0.2), (400, 0.2)])
S_CONST = mins([(0, 1.2), (400, 1.2)])
SOURCES = [S_TRI, S_TRI, S_TRI, S_CONST, S_TRI]       # ソース 1..5
SRC_OF_DAM = {1: S_TRI, 2: S_TRI, 3: S_TRI, 4: S_CONST, 6: S_TRI}
Q3 = mins([(0, 0.3), (30, 0.3), (30, 0.6), (120, 0.6), (240, 0.1), (400, 0.1)])
Q5 = mins([(0, 0.1), (200, 0.1), (200, 0.0), (400, 0.0)])
H4 = mins([(0, 104.0), (60, 104.0), (180, 105.5), (240, 105.5), (330, 104.5)])


def interp(series, t):
    """m_boundary の interp_series と同じ規約(線形。範囲外は端の値。
    同じ時刻の点が重なると、その時刻からは後ろの点で補間する)"""
    if t <= series[0][0]:
        return series[0][1]
    if t > series[-1][0]:
        return series[-1][1]
    for k in range(1, len(series)):
        t1 = series[k][0]
        if t < t1:
            t0, q0 = series[k - 1]
            q1 = series[k][1]
            return q0 + (t - t0) / (t1 - t0) * (q1 - q0)
    return series[-1][1]


def v_of_h(h):
    return interp(HV, h)


def rule_rate(qin, qon, r, qmax):
    """モード 2 の洪水調節開始流量・放流量の上限つきの式(dam_rate_target)"""
    if qin <= qon:
        return qon
    return min(qon + r * (qin - qon), qmax)


def read_csv(fn):
    rows = []
    for line in open(fn):
        if line.startswith("#"):
            continue
        v = [float(x) for x in line.split(",")]
        rows.append({"t": v[1] * 60.0, "H": v[2], "V": v[3], "Qin": v[4],
                     "Qout": v[5], "Qsp": v[6], "line": line})
    return rows


rc = 0


def check(ok, msg):
    global rc
    print(f"  {'ok' if ok else 'NG'}   {msg}")
    if not ok:
        rc = 1


def check_floor_rule(name, rows, hfloor, rule_of_row):
    """床より上 → 放流 = 式、床 → min(使える流入, 式) ≤ 放流 ≤ 式。水位 ≥ 床。
    使える流入は既定で流入 Qin、追加の放流工では主放流が流した後の残り
    (行の "avail")。戻り値: 床より上の行数, 床の行数"""
    nab = nfl = 0
    worst = 0.0
    bad = None
    for r in rows[1:]:
        q = rule_of_row(r)
        if r["H"] < hfloor - TOLH:
            bad = bad or f"t={r['t']/60:.0f} min: H={r['H']:.4f} below the floor {hfloor}"
        if r["H"] > hfloor + TOLH:
            nab += 1
            d = abs(r["Qout"] - q)
            worst = max(worst, d)
            if d > TOLQ:
                bad = bad or f"t={r['t']/60:.0f} min: Qout={r['Qout']:.4f} vs rule {q:.4f}"
        else:
            nfl += 1
            lo = min(r.get("avail", r["Qin"]), q) - TOLQ
            if not (lo <= r["Qout"] <= q + TOLQ):
                bad = bad or (f"t={r['t']/60:.0f} min (at the floor): Qout={r['Qout']:.4f} "
                              f"not in [min(inflow, rule), rule] = [{lo + TOLQ:.4f}, {q:.4f}]")
    check(bad is None, f"{name}: rule above the floor (max |dQ| = {worst:.1e}, {nab} rows), "
                       f"bounds at the floor ({nfl} rows)" + ("" if bad is None else f" - {bad}"))
    return nab, nfl


def mode_rules(res):
    dams = {n: read_csv(os.path.join(res, "dams", f"dam{n:04d}.csv")) for n in range(1, 8)}

    # --- 流入 = 1 歩前のソースの流量(孤立した捕捉帯)
    for n, src in SRC_OF_DAM.items():
        worst = max(abs(r["Qin"] - interp(src, r["t"] - DT)) for r in dams[n][1:])
        check(worst <= TOLQ, f"dam {n}: Qin = source of the previous step (max |d| = {worst:.1e})")

    # --- スピル 0(このケースの水位はサーチャージに届かない)
    check(all(r["Qsp"] == 0.0 for n in dams for r in dams[n]), "no spill in any dam")

    # --- ダム 1: 一定量放流方式(q0 = 0.8、制限水位 103 m)
    nab, nfl = check_floor_rule("dam 1 (mode 1 + dam_hlim)", dams[1], 103.0, lambda r: 0.8)
    last = dams[1][-1]
    check(nab > 0 and abs(last["H"] - 103.0) <= TOLH and abs(last["Qout"] - last["Qin"]) <= TOLQ,
          f"dam 1: left the floor and came back, then passes the inflow "
          f"(last row H={last['H']:.4f}, Qout={last['Qout']:.4f}, Qin={last['Qin']:.4f})")

    # --- ダム 2: 一定率一定量放流方式(Qon 0.6、r 0.5、Qmax 1.0、制限水位 103 m)
    rule2 = lambda r: rule_rate(r["Qin"], 0.6, 0.5, 1.0)
    nab, nfl = check_floor_rule("dam 2 (mode 2 + dam_qon/dam_qmax/dam_hlim)", dams[2], 103.0, rule2)
    rows = dams[2][1:]
    phases = {
        "pass-through at the floor (Qout = Qin < Qon)":
            any(abs(r["H"] - 103.0) <= TOLH and r["Qin"] < 0.6 - TOLQ
                and abs(r["Qout"] - r["Qin"]) <= TOLQ for r in rows),
        "constant rate (Qon < Qout < Qmax)":
            any(0.6 + TOLQ < r["Qout"] < 1.0 - TOLQ for r in rows),
        "maximum release (Qout = Qmax)": any(abs(r["Qout"] - 1.0) <= TOLQ for r in rows),
        "drawdown above the floor (Qin < Qon, Qout = Qon)":
            any(r["H"] > 103.0 + TOLH and r["Qin"] < 0.6 - TOLQ
                and abs(r["Qout"] - 0.6) <= TOLQ for r in rows),
    }
    for k, v in phases.items():
        check(v, f"dam 2 visits: {k}")

    # --- ダム 3: 放流量の時系列
    worst = max(abs(r["Qout"] - interp(Q3, r["t"])) for r in dams[3][1:])
    check(worst <= TOLQ and min(r["H"] for r in dams[3]) > 100.0 + TOLH,
          f"dam 3 (mode 4): Qout = the release series (max |d| = {worst:.1e})")
    check(any(abs(r["t"] - 1800.0) < 1.0 and abs(r["Qout"] - 0.6) <= TOLQ for r in dams[3])
          and any(abs(r["t"] - 1740.0) < 1.0 and abs(r["Qout"] - 0.3) <= TOLQ for r in dams[3]),
          "dam 3: the step 0.3 -> 0.6 at 30 min (repeated time point)")

    # --- ダム 5: ダム 3 の湖から引く取水(放流量の時系列)
    worst = max(abs(r["Qout"] - interp(Q5, r["t"])) for r in dams[5][1:])
    same = all(a["H"] == b["H"] and a["V"] == b["V"] for a, b in zip(dams[3], dams[5]))
    check(worst <= TOLQ and same and all(r["Qin"] == 0.0 for r in dams[5]),
          f"dam 5 (dam_lake = 3, mode 4): Qout = the intake series (max |d| = {worst:.1e}), "
          f"same lake level as dam 3, Qin = 0")

    # --- ダム 4: 貯水位の時系列(初期水位は時系列の t0 の値)
    worst = max(abs(r["H"] - interp(H4, r["t"])) for r in dams[4])
    check(worst <= TOLH and abs(dams[4][0]["H"] - 104.0) <= TOLH,
          f"dam 4 (mode 5): H = the water-level series incl. t = 0 (max |d| = {worst:.1e})")
    worst = 0.0
    for r in dams[4][1:]:
        q = r["Qin"] - (v_of_h(interp(H4, r["t"])) - v_of_h(interp(H4, r["t"] - DT))) / DT
        worst = max(worst, abs(r["Qout"] - max(q, 0.0)))
    check(worst <= TOLQ, f"dam 4: Qout = Qin - dV/dt of the target (max |d| = {worst:.1e})")

    # --- ダム 6: 一定率カット(従来の経路)
    worst = max(abs(r["Qout"] - 0.6 * r["Qin"]) for r in dams[6][1:])
    check(worst <= TOLQ, f"dam 6 (mode 2, rate only): Qout = 0.6 Qin (max |d| = {worst:.1e})")

    # --- ダム 7: ダム 6 の湖から引く一定率一定量(Qon 0.5、r 0.25、Qmax 0.6、床 100.5 m)
    rows7 = []
    for a, b in zip(dams[6], dams[7]):
        r = dict(b)
        r["Qin"] = a["Qin"]          # 参照構造物の CSV の Qin は 0。湖の流入で評価する
        r["avail"] = a["Qin"] - a["Qout"]   # 床で引けるのは主放流(ダム 6)の後の残り
        rows7.append(r)
    same = all(a["H"] == b["H"] for a, b in zip(dams[6], dams[7]))
    check(same, "dam 7: same lake level as dam 6")
    nab, nfl = check_floor_rule("dam 7 (dam_lake = 6, mode 2 + dam_qon/dam_qmax/dam_hlim)",
                                rows7, 100.5, lambda r: rule_rate(r["Qin"], 0.5, 0.25, 0.6))
    check(nab > 0 and nfl > 0 and any(abs(r["Qout"] - 0.6) <= TOLQ for r in rows7),
          "dam 7: visits the maximum release and its own floor")

    # --- 閉じた系の体積保存: S × 有効面積 = 初期貯水量 + ソースの累計体積
    logrows = []
    for line in open(os.path.join(res, "Log.txt")):
        p = line.split()
        if not p or not p[0][0].isdigit():
            continue
        h, m, s = p[0].split(":")
        logrows.append((int(h) * 3600 + int(m) * 60 + float(s), float(p[2])))
    tend = max(t for t, _ in logrows)
    cum = {}
    vol = V0
    k = 0
    cum[0.0] = vol
    while k * DT < tend - 1e-9:
        k += 1
        t = k * DT
        vol += sum(interp(src, t) for src in SOURCES) * DT
        cum[round(t, 6)] = vol
    worst = 0.0
    for t, sv in logrows:
        expect = cum[round(t, 6)] / (NVALID * AREA)
        worst = max(worst, abs(sv - expect))
    check(worst <= 1.0e-9, f"Log S = (initial storage + cumulative source volume) / area "
                           f"({len(logrows)} rows, max |dS| = {worst:.1e} m)")


def mode_restart(res, res2, trs):
    tr = float(trs) * 60.0
    for n in range(1, 8):
        a = {r["t"]: r["line"] for r in read_csv(os.path.join(res, "dams", f"dam{n:04d}.csv"))}
        b = [r for r in read_csv(os.path.join(res2, "dams", f"dam{n:04d}.csv")) if r["t"] > tr + 1e-6]
        ok = len(b) > 0 and all(r["line"] == a.get(r["t"]) for r in b)
        check(ok, f"dam {n}: {len(b)} rows after the restart match the straight run")

    def logs(fn):
        d = {}
        for line in open(fn):
            p = line.split()
            if p and p[0][0].isdigit():
                d[p[0]] = p[2]
        return d
    a = logs(os.path.join(res, "Log.txt"))
    b = logs(os.path.join(res2, "Log.txt"))
    keys = [k for k in b if sum(x * y for x, y in zip((3600, 60, 1), map(float, k.split(":")))) > tr]
    check(len(keys) > 0 and all(a.get(k) == b[k] for k in keys),
          f"Log S: {len(keys)} rows after the restart match the straight run")


if len(sys.argv) >= 3 and sys.argv[1] == "rules":
    mode_rules(sys.argv[2])
elif len(sys.argv) >= 5 and sys.argv[1] == "restart":
    mode_restart(sys.argv[2], sys.argv[3], sys.argv[4])
else:
    print("usage: Check_damops.py rules <result_dir> | restart <result> <result_rt2> <t_restart_min>")
    rc = 2
sys.exit(rc)
