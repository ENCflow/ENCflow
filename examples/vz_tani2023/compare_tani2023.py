#!/usr/bin/env python3
"""ENCflow の VZ 計算を谷(2023)の計算流出強度(HYDRUS-1D)・観測流出強度と比べる

  python3 compare_tani2023.py [事例 ...]   (既定: KIEX MREX MR1 TY1 TY2 KI1 KI2)

入力: result_<事例>/ の vz_zone.csv(ENCflow)、data/ の calc_*.csv・obs_*.csv・
rain_*.csv(extract_tani2023.py が論文の図から生成)。
出力: 画面に指標、result_<事例>/compare_<事例>.csv(時刻ごとの比較)、matplotlib が
あれば result_<事例>/fig_<事例>.png。図と CSV は論文の図から取り出した数値を含むので
リポジトリには置かない。

ENCflow の排水強度 q は、区画の累積排水 vdrain の記録間隔ごとの差分を区画面積で
割った値(区間の中央の時刻に置き、比べる時刻へ線形補間)。論文がモデルの外で行った
後処理を同じように適用して、図の量に揃える(EVENTS の post):
  TY1・TY2 : 流出強度 = q
  KI1・KI2 : 流出強度 = q / 2(排水の 1/2 は風化基岩への深部浸透。論文 Ⅳ.3)
  MREX     : 各堰の流出強度 = (q − 0.3 mm/h) / 2(深部浸透 0.3 mm/h、上流堰と
             下流堰に 1/2 ずつ。論文 Ⅳ.1。降雨の 80 % 化は precip_MREX.txt で済み)
  MR1      : 上流堰の流出量 = (q − 0.3 mm/h) / 2 × 860 m²(L/s。論文 Ⅳ.1)
  KIEX     : 流出強度 = 50 cm の柱の底面の排水 q(論文 Ⅳ.1)
論文の TY・KI の計算値には観測から分離した基底流が加えてある(論文 Ⅲ.1)が、
ENCflow の値には加えていない。

指標(区画ごと。論文の計算値が下端で切られた点は除く):
  log10 比   = log10(ENCflow / 論文の計算値) の中央値と、絶対値の 90 % 値・最大値を、
               論文の計算値が qmin の 2 つの下限以上の点で
  ピーク     = 論文の計算値の最大と、その前後 win 時間の ENCflow の最大
  ピーク時刻 = 論文の計算値が qpeak を超え前後 win 時間で最大になる点ごとに、前後
               win 時間にある ENCflow の極大(値が論文の半分以上)のうち最も近いものとの
               時刻差の中央値
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
# 単位、比較の下限 qmin、極大の下限 qpeak、窓 win (h)、図の縦軸(log / lin と範囲)
EVENTS = {
    "KIEX": dict(zones={1: "Plot2"}, post=ident, calc={"calc": "Plot2"}, obs={"obs": "Plot2"},
                 unit="mm/h", qmin=(1.0, 10.0), qpeak=10.0, win=0.5, axis=("lin", 0.0, 90.0)),
    "MREX": dict(zones={1: "CB1"}, post=mrex, calc={"QcC": "CB1"}, obs={"QU": "CB1", "QL": "CB1"},
                 unit="mm/h", qmin=(0.1, 0.3), qpeak=0.4, win=6.0, axis=("lin", 0.0, 0.7)),
    "MR1": dict(zones={1: "CB1"}, post=mr1_upper, calc={"QcC": "CB1"}, obs={"QU": "CB1"},
                unit="L/s", qmin=(0.1, 0.3), qpeak=0.5, win=3.0, axis=("lin", 0.0, 2.0)),
    "TY1": dict(zones={1: "KT", 2: "MN", 3: "SL"}, post=ident, calc={"KT": "KT", "MN": "MN", "SL": "SL"},
                obs={"KT": "KT", "MN": "MN", "SL": "SL"}, unit="mm/h", qmin=(0.1, 0.5), qpeak=1.0, win=3.0,
                axis=("log", 0.01, 20.0)),
    "TY2": dict(zones={1: "KT", 2: "MN", 3: "SL"}, post=ident, calc={"KT": "KT", "MN": "MN"},
                obs={"KT": "KT", "MN": "MN"}, unit="mm/h", qmin=(0.1, 0.5), qpeak=1.0, win=3.0,
                axis=("log", 0.01, 20.0)),
    "KI1": dict(zones={1: "KI"}, post=half, calc={"QcC": "KI"}, obs={"Qb": "KI"},
                unit="mm/h", qmin=(0.1, 0.5), qpeak=1.0, win=3.0, axis=("log", 0.05, 30.0)),
    "KI2": dict(zones={1: "KI"}, post=half, calc={"QcC": "KI"}, obs={"Qb": "KI"},
                unit="mm/h", qmin=(0.1, 0.5), qpeak=1.0, win=3.0, axis=("log", 0.05, 10.0),
                baseflow="Qb"),
}
# baseflow: 論文の計算値に加えられた分離基底流の近似として、観測の最初と最後の値を結ぶ
# 直線を ENCflow に足した比較も示す(KI2 だけ。図の終わりで流出が基底流に近く、差
# 論文 − ENCflow が時間にほぼ比例して増えるため。論文の分離線そのものではない)


def read_rates(res, ev):
    """vz_zone.csv → {区画名: [(t(h), 後処理後の値)]}(区間の中央の時刻)"""
    cfg = EVENTS[ev]
    with open(os.path.join(res, "vz_zone.csv"), newline="") as f:
        rows = list(csv.reader(f))
    head = [h.strip() for h in rows[0]]
    it, iz, ia, iv = (head.index("time(s)"), head.index("zone"), head.index("area(m2)"),
                      head.index("vdrain(m3)"))
    cum = {}
    for r in rows[1:]:
        if r and int(r[iz]) in cfg["zones"]:
            cum.setdefault(cfg["zones"][int(r[iz])], []).append((float(r[it]), float(r[iv]), float(r[ia])))
    rates = {}
    for name, s in cum.items():
        out, t0, v0 = [], 0.0, 0.0
        for t, v, a in s:
            q = (v - v0) / a / (t - t0) * 3.6e6           # 排水強度 (mm/h)
            out.append(((t + t0) / 2.0 / 3600.0, cfg["post"](q)))
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


def add_baseflow(rates, obs, oname):
    """観測の最初と最後の値を結ぶ直線を足した系列を返す"""
    (t0, b0, _), (t1, b1, _) = obs[oname][0], obs[oname][-1]
    out = {}
    for name, s in rates.items():
        out[name] = [(t, q + b0 + (b1 - b0) * min(max((t - t0) / (t1 - t0), 0.0), 1.0)) for t, q in s]
    return out, (t0, b0, t1, b1)


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
    if "baseflow" in cfg:
        rb, (t0, b0, t1, b1) = add_baseflow(rates, obs, cfg["baseflow"])
        for cname, zname in cfg["calc"].items():
            show(cname + "+base", *metrics(cfg, cname, rb[zname], calc))
        print("   (+base: ENCflow + straight baseflow from the first to the last observation, "
              "%.3g at %.1f h to %.3g at %.1f h)" % (b0, t0, b1, t1))
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
    plot(ev, res, rates, calc, obs)


def plot(ev, res, rates, calc, obs):
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


def main():
    evs = sys.argv[1:] or list(EVENTS)
    for ev in evs:
        compare(ev)


if __name__ == "__main__":
    main()
