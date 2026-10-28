#!/usr/bin/env python3
"""ENCflow の VZ 計算を谷(2023)の計算流出強度(HYDRUS-1D)・観測流出強度と比べる

  python3 compare_tani2023.py [事例 ...]   (既定: KIEX MREX MR1 TY1 TY2 KI1 KI2)

入力: result_<事例>/ の vz_zone.csv・vzprof_1_*.csv・FILENUMBER.csv(ENCflow)、data/ の
calc_*.csv・obs_*.csv・rain_*.csv・psi_*.csv(extract_tani2023.py が論文の図から生成)。
出力: 画面に指標、result_<事例>/compare_<事例>.csv・compare_psi_<事例>.csv(時刻ごとの
比較)、matplotlib があれば result_<事例>/fig_<事例>.png・fig_<事例>_psi.png。図と CSV は
論文の図から取り出した数値を含むのでリポジトリには置かない。

ENCflow の排水強度 q は、区画の累積排水 vdrain の記録間隔ごとの差分を区画面積で
割った値(区間の中央の時刻に置き、比べる時刻へ線形補間)。論文がモデルの外で行った
後処理を同じように適用して、図の量に揃える(EVENTS の post):
  TY1・TY2 : 流出強度 = q
  KI1・KI2 : 流出強度 = q / 2(排水の 1/2 は風化基岩への深部浸透。論文 Ⅳ.3)
  MREX     : 各堰の流出強度 = (q − 0.3 mm/h) / 2(深部浸透 0.3 mm/h、上流堰と
             下流堰に 1/2 ずつ。論文 Ⅳ.1。降雨の 80 % 化は precip_MREX.txt で済み)
  MR1      : 上流堰の流出量 = (q − 0.3 mm/h) / 2 × 860 m²(L/s。論文 Ⅳ.1)
  KIEX     : 流出強度 = 50 cm の柱の底面の排水 q(論文 Ⅳ.1)
論文の TY・KI の計算値には観測から分離した基底流が加えてある(論文 Ⅲ.1)。ENCflow の
値には加えず、モデルに基底流を与えた事例(KI2。param_ki2.txt の fn_vz_base)は、
vz_zone.csv の vbase の差分(区画面積あたりの強度)を後処理後の排水に足した比較
(+base)も示す。

指標(区画ごと。論文の計算値が下端で切られた点は除く):
  log10 比   = log10(ENCflow / 論文の計算値) の中央値と、絶対値の 90 % 値・最大値を、
               論文の計算値が qmin の 2 つの下限以上の点で
  ピーク     = 論文の計算値の最大と、その前後 win 時間の ENCflow の最大
  ピーク時刻 = 論文の計算値が qpeak を超え前後 win 時間で最大になる点ごとに、前後
               win 時間にある ENCflow の極大(値が論文の半分以上)のうち最も近いものとの
               時刻差の中央値

圧力水頭(水理水頭)の比較(論文の図の深さごと):
  ENCflow の ψ は柱の鉛直分布の出力(層中心の値。dt_file ごと)を深さで線形補間し、
  時刻 0 には初期条件(EVENTS の psi0)を置く。水理水頭は地表面を基準に ψ − 深さ
  到達時刻 = 湿潤前線の到達として、値が arrive の水準を下から超えた最初の時刻
             (level = 圧力水頭 (cm) の水準。half = 最初の値と最大値の中間。MREX は観測の
             水理水頭が標高で基準が分からないので、計算値も含めてこの定義にそろえる)
  差         = ENCflow − 論文の計算値 (cm) の中央値と、絶対値の 90 % 値。ENCflow の出力
             時刻ごとに、論文の曲線の図の枠で切られていない区間で比べる(KIEX の図−12(b) は
             論文の注記により太田ら(1983)の計算値で、論文の VZ モデルの計算値ではない)
  観測(TY1 のテンシオメータ、MREX の nest 5-4)は到達時刻を比べ、TY1 は差(ENCflow −
  観測)の中央値、MREX は立ち上がりの大きさ(最大値 − 最初の値)を示す
"""
import csv
import math
import os
import statistics
import sys

A_CB1 = 860.0        # MR の CB1 の面積 (m2。上流堰の流出量の換算)


def ident(q):
    return q


def half(q):
    return 0.5 * q


def mrex(q):
    return 0.5 * (q - 0.3)


def mr1_upper(q):
    return 0.5 * (q - 0.3) * A_CB1 / 3600.0      # mm/h × m2 → L/s


# 事例ごとの設定: 区画番号 → 名前、後処理、比べる論文の計算値の名前 → 区画、観測の名前 → 区画、
# 単位、比較の下限 qmin、極大の下限 qpeak、窓 win (h)、図の縦軸(log / lin と範囲)、
# 柱の初期条件 psi0(const = 一様な ψ (m)、hydro = 初期地下水面の深さ (m) の静水圧)、
# 圧力水頭の到達時刻の定義 arrive(level = 圧力水頭 (cm) の水準、half = 最初の値と最大値の中間。
# 水準は論文の図の枠の中にあり、論文の曲線が下から超える値: MR1 の −60 cm は 1.025 m の
# 曲線が図の枠の下端(ψ = −67.5 cm)から現れるため、MREX は観測に合わせて half)
EVENTS = {
    "KIEX": dict(zones={1: "Plot2"}, post=ident, calc={"calc": "Plot2"}, obs={"obs": "Plot2"},
                 unit="mm/h", qmin=(1.0, 10.0), qpeak=10.0, win=0.5, axis=("lin", 0.0, 90.0),
                 psi0=("hydro", 0.5), arrive=("level", -15.0)),
    "MREX": dict(zones={1: "CB1"}, post=mrex, calc={"QcC": "CB1"}, obs={"QU": "CB1", "QL": "CB1"},
                 unit="mm/h", qmin=(0.1, 0.3), qpeak=0.4, win=6.0, axis=("lin", 0.0, 0.7),
                 psi0=("const", -1.0), arrive=("half", None)),
    "MR1": dict(zones={1: "CB1"}, post=mr1_upper, calc={"QcC": "CB1"}, obs={"QU": "CB1"},
                unit="L/s", qmin=(0.1, 0.3), qpeak=0.5, win=3.0, axis=("lin", 0.0, 2.0),
                psi0=("const", -1.0), arrive=("level", -60.0)),
    "TY1": dict(zones={1: "KT", 2: "MN", 3: "SL"}, post=ident, calc={"KT": "KT", "MN": "MN", "SL": "SL"},
                obs={"KT": "KT", "MN": "MN", "SL": "SL"}, unit="mm/h", qmin=(0.1, 0.5), qpeak=1.0, win=3.0,
                axis=("log", 0.01, 20.0), psi0=("const", -4.0), arrive=("level", -50.0)),
    "TY2": dict(zones={1: "KT", 2: "MN", 3: "SL"}, post=ident, calc={"KT": "KT", "MN": "MN"},
                obs={"KT": "KT", "MN": "MN"}, unit="mm/h", qmin=(0.1, 0.5), qpeak=1.0, win=3.0,
                axis=("log", 0.01, 20.0), psi0=("const", -4.0), arrive=("level", -50.0)),
    "KI1": dict(zones={1: "KI"}, post=half, calc={"QcC": "KI"}, obs={"Qb": "KI"},
                unit="mm/h", qmin=(0.1, 0.5), qpeak=1.0, win=3.0, axis=("log", 0.05, 30.0),
                psi0=("const", -1.0), arrive=("level", -50.0)),
    "KI2": dict(zones={1: "KI"}, post=half, calc={"QcC": "KI"}, obs={"Qb": "KI"},
                unit="mm/h", qmin=(0.1, 0.5), qpeak=1.0, win=3.0, axis=("log", 0.05, 10.0),
                psi0=("const", -1.0), arrive=("level", -50.0)),
}


def read_rates(res, ev, column="vdrain(m3)", post=True):
    """vz_zone.csv → {区画名: [(t(h), 後処理後の値)]}(区間の中央の時刻)。column の
    列がなければ {}(vbase は基底流を与えたときだけ出る)。post = False は後処理なし"""
    cfg = EVENTS[ev]
    with open(os.path.join(res, "vz_zone.csv"), newline="") as f:
        rows = list(csv.reader(f))
    head = [h.strip() for h in rows[0]]
    if column not in head:
        return {}
    it, iz, ia, iv = (head.index("time(s)"), head.index("zone"), head.index("area(m2)"),
                      head.index(column))
    cum = {}
    for r in rows[1:]:
        if r and int(r[iz]) in cfg["zones"]:
            cum.setdefault(cfg["zones"][int(r[iz])], []).append((float(r[it]), float(r[iv]), float(r[ia])))
    rates = {}
    for name, s in cum.items():
        out, t0, v0 = [], 0.0, 0.0
        for t, v, a in s:
            q = (v - v0) / a / (t - t0) * 3.6e6           # 区画面積あたりの強度 (mm/h)
            out.append(((t + t0) / 2.0 / 3600.0, cfg["post"](q) if post else q))
            t0, v0 = t, v
        rates[name] = out
    return rates


def interp(series, t):
    for (t0, v0), (t1, v1) in zip(series[:-1], series[1:]):
        if t0 <= t <= t1:
            return v0 + (v1 - v0) * (t - t0) / (t1 - t0)
    return None


def read_points(path):
    pts = {}
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            flag = int(r.get("clipped", r.get("censored", "0")))
            key = [k for k in r if k.startswith("runoff")][0]
            pts.setdefault(r["catchment"], []).append((float(r["t(h)"]), float(r[key]), flag))
    return pts


def add_baseflow(rates, base):
    """後処理後の排水に、モデルに与えた基底流(同じ記録区間の平均強度)を足した系列"""
    return {name: [(t, q + b) for (t, q), (_, b) in zip(s, base[name])] for name, s in rates.items()}


def metrics(cfg, cname, series, calc, table=None):
    """論文の計算値 cname と ENCflow の系列 series を比べた指標の行を表示する"""
    pk = max(calc[cname], key=lambda p: p[1])
    mpk = max(p[1] for p in series if abs(p[0] - pk[0]) <= cfg["win"])
    pts = [p for p in calc[cname] if not p[2]]
    # ENCflow の極大(前後の値より大きい点)
    emax = [series[i] for i in range(1, len(series) - 1)
            if series[i][1] >= series[i - 1][1] and series[i][1] > series[i + 1][1]]
    dts = []
    for t0, q0, _ in pts:
        # 前後 win 時間で論文の計算値が最大になる点(破線の細かな凹凸を極大と数えない)ごとに、
        # 前後 win 時間にある ENCflow の極大(値が論文の半分以上)のうち最も近いもの
        if q0 > cfg["qpeak"] and q0 >= max(q for t, q, _ in pts if abs(t - t0) <= cfg["win"]):
            cand = [p for p in emax if abs(p[0] - t0) <= cfg["win"] and p[1] >= 0.5 * q0]
            if cand:
                dts.append(min(cand, key=lambda p: abs(p[0] - t0))[0] - t0)
    rows = []
    for qmin in cfg["qmin"]:
        lr = []
        for t, q, clipped in calc[cname]:
            m = interp(series, t)
            if clipped or q < qmin or m is None or m <= 0.0:
                continue
            lr.append(math.log10(m / q))
            if table is not None and qmin == cfg["qmin"][0]:
                table.append((cname, t, q, m))
        absr = sorted(abs(v) for v in lr)
        rows.append((qmin, len(lr), statistics.median(lr), absr[int(0.9 * (len(absr) - 1))], absr[-1]))
    return rows, pk[1], mpk, (statistics.median(dts) if dts else float("nan")), len(dts)


def show(label, rows, pk, mpk, dt, npk):
    for i, (qmin, n, med, p90, mx) in enumerate(rows):
        tail = ("%7.3g / %7.3g (%+5.1f %%)   %+.2f (%d peaks)" % (pk, mpk, 100.0 * (mpk / pk - 1.0), dt, npk)
                if i == 0 else "")
        print("   %-12s >= %-6.3g %4d %+8.3f %8.3f %8.3f   %s"
              % (label if i == 0 else "", qmin, n, med, p90, mx, tail))


def read_profiles(res, col=1):
    """柱の鉛直分布の出力 → (層中心の深さ, [(t(h), 層ごとの ψ (m))])"""
    times = {}
    with open(os.path.join(res, "FILENUMBER.csv")) as f:
        for line in f:
            if not line.startswith("#"):
                r = line.split(",")
                times[int(r[0])] = float(r[2]) / 3600.0
    z, snaps = None, []
    for ifn in sorted(times):
        fn = os.path.join(res, "vzprof_%d_%04d.csv" % (col, ifn))
        if not os.path.exists(fn):
            continue
        with open(fn, newline="") as f:
            rows = [r for r in csv.reader(f)][1:]
        z = [float(r[0]) for r in rows]
        snaps.append((times[ifn], [float(r[1]) for r in rows]))
    return z, snaps


def enc_series(cfg, prof, d, quantity):
    """深さ d (m) の ENCflow の系列 [(t(h), 値)]。値は psi = cm、head・elev = ψ − d (m)"""
    z, snaps = prof
    k = max(i for i in range(len(z) - 1) if z[i] <= d) if d >= z[0] else 0
    w = (d - z[k]) / (z[k + 1] - z[k])
    kind, v = cfg["psi0"]
    ser = [(0.0, v if kind == "const" else d - v)]
    ser += [(t, p[k] + w * (p[k + 1] - p[k])) for t, p in snaps]
    if quantity == "psi":
        return [(t, 100.0 * p) for t, p in ser]
    return [(t, p - d) for t, p in ser]


def paper_at(pts, t, gap=6.0):
    """論文の曲線(描画順の点)の時刻 t の値。図の枠で切られた点を含む区間・gap 時間を超える
    途切れ(実線は折れ線の頂点の間が数時間あることがある)・曲線の範囲外では None"""
    for (t0, v0, c0), (t1, v1, c1) in zip(pts[:-1], pts[1:]):
        if t0 <= t <= t1:
            if c0 or c1 or t1 - t0 > gap:
                return None
            return v0 if t1 == t0 else v0 + (v1 - v0) * (t - t0) / (t1 - t0)
    return None


def arrival(cfg, ser, d, quantity):
    """湿潤前線の到達時刻(arrive の水準を下から超えた最初の時刻。最初から超えていれば None)"""
    mode, lev = cfg["arrive"]
    vals = [p[1] for p in ser]
    if mode == "half":
        level = 0.5 * (vals[0] + max(vals))
    else:
        level = lev if quantity == "psi" else lev / 100.0 - d
    if vals[0] >= level:
        return None
    for (t0, v0), (t1, v1) in zip(ser[:-1], ser[1:]):
        if v0 < level <= v1:
            return t0 + (level - v0) / (v1 - v0) * (t1 - t0)
    return None


def read_psi(path):
    """psi_<EV>.csv → [(source, site, 深さ, quantity, [(t, 値, clipped)])](図ごと、図の中は深さの順)"""
    cur = {}
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            key = (r["source"], r["site"], float(r["depth(m)"]), r["quantity"].split("(")[0])
            cur.setdefault(key, []).append((float(r["t(h)"]), float(r["value"]), int(r["clipped"])))
    return [k + (v,) for k, v in cur.items()]


def fmt_h(t):
    return "   —  " if t is None else "%6.1f" % t


def fmt_dt(a, b):
    return "   —  " if a is None or b is None else "%+6.2f" % (b - a)


def compare_psi(ev, res):
    """圧力水頭(水理水頭)を論文の計算値・観測値と比べる"""
    cfg = EVENTS[ev]
    path = os.path.join("data", "psi_%s.csv" % ev)
    if not os.path.exists(path):
        return
    curves = read_psi(path)
    prof = read_profiles(res)
    mode, lev = cfg["arrive"]
    print("   pressure head: arrival = first upward crossing of %s; diff = ENCflow - paper (cm)"
          % ("half-way from the first value to the maximum" if mode == "half" else "%g cm" % lev))
    print("   %-14s %7s   %6s %6s %6s   %4s %8s %8s" % ("calculated", "depth", "paper", "ENCflw", "diff",
                                                         "n", "median", "p90|.|"))
    table, enc, calc_arr = [], {}, {}
    for src, site, d, qty, pts in curves:
        if src != "calc":
            continue
        ser = enc_series(cfg, prof, d, qty)
        enc[(d, qty)] = ser
        scale = 1.0 if qty == "psi" else 100.0
        diffs = []
        for t, v in ser[1:]:
            pv = paper_at(pts, t)
            if pv is not None:
                diffs.append(scale * (v - pv))
                table.append(("calc", site, d, t, pv, v))
        ta, te = arrival(cfg, [(p[0], p[1]) for p in pts], d, qty), arrival(cfg, ser, d, qty)
        calc_arr[d] = ta
        absd = sorted(abs(x) for x in diffs)
        print("   %-14s %5.3f m   %s %s %s   %4d %+8.1f %8.1f"
              % ("%s %s" % (qty, site or ("(m)" if qty == "head" else "(cm)")), d, fmt_h(ta), fmt_h(te),
                 fmt_dt(ta, te),
                 len(diffs), statistics.median(diffs) if diffs else float("nan"),
                 absd[int(0.9 * (len(absd) - 1))] if absd else float("nan")))
    obs = [c for c in curves if c[0] == "obs"]
    if obs:
        print("   %-14s %7s   %6s %6s %6s   %6s  %s" % ("observed", "depth", "obs", "ENCflw", "diff", "paper",
                                                       "median ENCflow - obs (cm) / rise obs, ENCflow (m)"))
    for src, site, d, qty, pts in obs:
        ser = enc_series(cfg, prof, d, qty)
        enc[(d, qty)] = ser
        ta, te = arrival(cfg, [(p[0], p[1]) for p in pts], d, qty), arrival(cfg, ser, d, qty)
        near = [ta_ for dc, ta_ in calc_arr.items() if abs(dc - d) < 0.03]
        tc = near[0] if near else None                       # 同じ深さの論文の計算値
        if qty == "psi":
            diffs = []
            for t, v in ser[1:]:
                pv = paper_at(pts, t)
                if pv is not None:
                    diffs.append(v - pv)
                    table.append(("obs", site, d, t, pv, v))
            tail = "%+.1f (n = %d)" % (statistics.median(diffs), len(diffs)) if diffs else "—"
        else:
            vs = [p[1] for p in ser if p[0] >= pts[0][0]]
            tail = "rise %.2f / %.2f" % (max(p[1] for p in pts) - pts[0][1], max(vs) - vs[0])
            for t, v in ser[1:]:
                pv = paper_at(pts, t)
                if pv is not None:
                    table.append(("obs", site, d, t, pv, v))
        print("   %-14s %5.3f m   %s %s %s   %s  %s" % (site, d, fmt_h(ta), fmt_h(te), fmt_dt(ta, te),
                                                         fmt_h(tc), tail))
    with open(os.path.join(res, "compare_psi_%s.csv" % ev.lower()), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["source", "site", "depth(m)", "t(h)", "paper", "encflow"])
        for src, site, d, t, pv, v in table:
            w.writerow([src, site, "%.3f" % d, "%.3f" % t, "%.5g" % pv, "%.5g" % v])
    plot_psi(ev, res, curves, enc)


def compare(ev):
    cfg = EVENTS[ev]
    res = "result_" + ev.lower()
    rates = read_rates(res, ev)
    calc = read_points(os.path.join("data", "calc_%s.csv" % ev))
    obs = read_points(os.path.join("data", "obs_%s.csv" % ev))
    u = cfg["unit"]
    print("== %s: ENCflow vs the calculated runoff of Tani (2023) (%s)" % (ev, u))
    print("   %-12s %-10s %4s %8s %8s %8s   %-30s %s" % ("", "runoff", "n", "median", "p90|.|", "max|.|",
                                                        "peak paper / ENCflow", "peak time (h)"))
    table = []
    for cname, zname in cfg["calc"].items():
        show(cname, *metrics(cfg, cname, rates[zname], calc, table))
    base = read_rates(res, ev, "vbase(m3)", post=False)
    if base:
        rb = add_baseflow(rates, base)
        for cname, zname in cfg["calc"].items():
            show(cname + "+base", *metrics(cfg, cname, rb[zname], calc))
        for zname, s in base.items():
            print("   (+base: ENCflow + the baseflow given to the model (fn_vz_base), %s %.3g to %.3g mm/h)"
                  % (zname, s[0][1], s[-1][1]))
    print("   observed (Fig.): maximum of the observations vs ENCflow at the same time")
    for oname, zname in cfg["obs"].items():
        if oname in obs:
            pk = max(obs[oname], key=lambda p: p[1])
            print("   %-6s observed %.3g %s at %.2f h, ENCflow %.3g" % (oname, pk[1], u, pk[0],
                                                                   interp(rates[zname], pk[0])))
    with open(os.path.join(res, "compare_%s.csv" % ev.lower()), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["catchment", "t(h)", "paper(%s)" % u, "encflow(%s)" % u])
        for name, t, q, m in table:
            w.writerow([name, "%.3f" % t, "%.5g" % q, "%.5g" % m])
    plot(ev, res, rates, calc, obs, rb if base else None)
    compare_psi(ev, res)


def plot(ev, res, rates, calc, obs, rb=None):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("   (matplotlib not found: no figure)")
        return
    cfg = EVENTS[ev]
    rain = []
    with open(os.path.join("data", "rain_%s.csv" % ev), newline="") as f:
        for r in csv.DictReader(f):
            rain.append((float(r["t_start(h)"]), float(r["t_end(h)"]), float(r["rain(mm/h)"])))
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 6), sharex=True, gridspec_kw=dict(height_ratios=[1, 3]))
    for a, b, r in rain:
        ax1.bar(a, r, width=b - a, align="edge", color="0.7")
    ax1.set_ylabel("rain (mm/h)\n(as drawn)")
    colors = ["k", "tab:blue", "tab:orange"]
    marks = {"KT": "o", "MN": "x", "SL": "^", "QU": "o", "QL": "x", "Qb": "o", "obs": "."}
    for i, (cname, zname) in enumerate(cfg["calc"].items()):
        col = colors[i % 3]
        t = [p[0] for p in calc[cname] if not p[2]]
        q = [p[1] for p in calc[cname] if not p[2]]
        ax2.plot(t, q, color=col, lw=2.5, alpha=0.35, label="%s Tani (2023) calculated" % cname)
        ax2.plot([p[0] for p in rates[zname]], [p[1] for p in rates[zname]], color=col, lw=1.0,
                 label="%s ENCflow" % zname)
        if rb:
            ax2.plot([p[0] for p in rb[zname]], [p[1] for p in rb[zname]], color=col, lw=1.0, ls="--",
                     label="%s ENCflow + baseflow" % zname)
    for j, (oname, zname) in enumerate(cfg["obs"].items()):
        if oname in obs:
            col = colors[j % 3] if ev.startswith("TY") else "0.3"
            ax2.plot([p[0] for p in obs[oname]], [p[1] for p in obs[oname]], marks.get(oname, "o"), color=col,
                     ms=4, mfc="none", label="%s observed" % oname)
    scale, lo, hi = cfg["axis"]
    if scale == "log":
        ax2.set_yscale("log")
    ax2.set_ylim(lo, hi)
    ax2.set_ylabel("runoff (%s)" % cfg["unit"])
    ax2.set_xlabel("hours from time 0 of the example (left end of the time axis of the figure)")
    ax2.legend(fontsize=7, ncol=3)
    fig.tight_layout()
    fn = os.path.join(res, "fig_%s.png" % ev.lower())
    fig.savefig(fn, dpi=120)
    plt.close(fig)
    print("   figure: " + fn)


def plot_psi(ev, res, curves, enc):
    """圧力水頭: 上段 = 論文の計算値と ENCflow、下段(観測があれば)= 観測と ENCflow"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    calc = [c for c in curves if c[0] == "calc"]
    obs = [c for c in curves if c[0] == "obs"]
    fig, axs = plt.subplots(2 if obs else 1, 1, figsize=(9, 7 if obs else 4), sharex=True, squeeze=False)
    cmap = plt.get_cmap("tab10")
    ax = axs[0][0]
    lo = []
    for i, (src, site, d, qty, pts) in enumerate(calc):
        col = cmap(i % 10)
        seg = [p for p in pts if not p[2]]
        ax.plot([p[0] for p in seg], [p[1] for p in seg], ".", color=col, ms=2.5, alpha=0.5)
        ser = enc[(d, qty)]
        ax.plot([p[0] for p in ser], [p[1] for p in ser], color=col, lw=1.0, label="%g m" % d)
        lo.append(min(p[1] for p in pts))
    unit = "pressure head (cm)" if calc[0][3] == "psi" else "hydraulic head (m)\nfrom the ground surface"
    ax.set_ylabel(unit)
    ax.set_ylim(min(lo) - 0.05 * abs(min(lo)), None)
    who = "Ohta et al. (1983) calculated, as read in Tani (2023)" if calc[0][1] == "Ohta1983" else \
        "Tani (2023) calculated"
    ax.set_title("%s: %s (dots) and ENCflow (lines)" % (ev, who), fontsize=9)
    ax.legend(fontsize=7, ncol=7)
    if obs:
        ax = axs[1][0]
        styles = ["--", ":", "-.", (0, (6, 2))]
        sites = list(dict.fromkeys(c[1] for c in obs))
        depths = sorted(set(c[2] for c in obs))
        for src, site, d, qty, pts in obs:
            col = cmap(depths.index(d) % 10)
            ser = enc[(d, qty)]
            if qty == "elev":            # 標高の観測は最初の値からの変化で、ENCflow も同じ時刻から
                v0 = pts[0][1]
                e0 = paper_at([(t, v, 0) for t, v in ser], pts[0][0])
                ax.plot([p[0] for p in pts], [p[1] - v0 for p in pts], ls=styles[0], color=col,
                        label="%s %g m observed" % (site, d))
                ax.plot([p[0] for p in ser], [p[1] - e0 for p in ser], color=col, lw=1.0,
                        label="ENCflow %g m" % d)
            else:
                ax.plot([p[0] for p in pts], [p[1] for p in pts], ls=styles[sites.index(site) % 4], color=col,
                        lw=1.0, label="%s %g m" % (site, d))
        if obs[0][3] == "psi":
            for d in depths:
                ser = enc[(d, "psi")]
                ax.plot([p[0] for p in ser], [p[1] for p in ser], color=cmap(depths.index(d) % 10), lw=2.0,
                        alpha=0.4, label="ENCflow %g m" % d)
            ax.set_ylim(min(min(p[1] for p in c[4]) for c in obs) - 5.0, None)
            ax.set_ylabel("pressure head (cm)")
        else:
            ax.set_ylabel("change of hydraulic head\nfrom the first value (m)")
        ax.set_title("observed (thin, by site) and ENCflow (thick)" if obs[0][3] == "psi" else
                     "observed at nest 5-4 (dashed) and ENCflow (solid)", fontsize=9)
        ax.legend(fontsize=6, ncol=4)
    axs[-1][0].set_xlabel("hours from time 0 of the example (left end of the time axis of the figure)")
    fig.tight_layout()
    fn = os.path.join(res, "fig_%s_psi.png" % ev.lower())
    fig.savefig(fn, dpi=120)
    plt.close(fig)
    print("   figure: " + fn)


def main():
    evs = sys.argv[1:] or list(EVENTS)
    for ev in evs:
        compare(ev)


if __name__ == "__main__":
    main()
