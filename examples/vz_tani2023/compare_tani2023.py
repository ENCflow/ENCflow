#!/usr/bin/env python3
"""ENCflow の VZ 計算を谷(2023)の計算流出強度(HYDRUS-1D)・観測流出強度と比べる

  python3 compare_tani2023.py [TY1|TY2 ...]      (既定: TY1 TY2)

入力: result_ty1/・result_ty2/ の vz_zone.csv(ENCflow)、data/ の calc_*.csv・
obs_*.csv・rain_*.csv(extract_tani2023.py が論文の図から生成)。
出力: 画面に指標、result_<ev>/compare_<ev>.csv(時刻ごとの比較)、matplotlib が
あれば result_<ev>/fig_<ev>.png。図と CSV は論文の図から取り出した数値を含むので
リポジトリには置かない。

流出強度は区画の累積排水 vdrain の 10 分ごとの差分を区画面積で割った値
(区間の中央の時刻に置き、比べる時刻へ線形補間)。論文の計算値には観測から分離した
基底流が加えてある(論文 Ⅲ.1)が、ENCflow の値には加えていない。そのため低流量では
ENCflow が基底流の分(0.01〜0.03 mm/h 程度)だけ低く出る。

指標(区画ごと。論文の計算値が下端で切られた点は除く):
  log10 比 = log10(ENCflow / 論文の計算値) の中央値と、絶対値の 90 % 値・最大値を、
             論文の計算値 0.1 mm/h 以上の点と 0.5 mm/h 以上の点(基底流の影響が
             小さい範囲)で
  ピーク   = 論文の計算値の最大と、その前後 3 h の ENCflow の最大
  ピーク時刻 = 論文の計算値が 1 mm/h を超え前後 3 h で最大になる点ごとに、前後 3 h の
             ENCflow の最大の時刻との差の中央値
"""
import csv
import math
import os
import statistics
import sys

NAMES = {1: "KT", 2: "MN", 3: "SL"}
QMIN = (0.1, 0.5)    # 比較に使う流出強度の下限 (mm/h)


def read_rates(res):
    """vz_zone.csv → {区画名: [(t(h), 流出強度 mm/h)]}(区間の中央の時刻)"""
    with open(os.path.join(res, "vz_zone.csv"), newline="") as f:
        rows = list(csv.reader(f))
    head = [h.strip() for h in rows[0]]
    it, iz, ia, iv = (head.index("time(s)"), head.index("zone"), head.index("area(m2)"),
                      head.index("vdrain(m3)"))
    cum = {}
    for r in rows[1:]:
        if r:
            cum.setdefault(NAMES[int(r[iz])], []).append((float(r[it]), float(r[iv]), float(r[ia])))
    rates = {}
    for name, s in cum.items():
        out, t0, v0 = [], 0.0, 0.0
        for t, v, a in s:
            out.append(((t + t0) / 2.0 / 3600.0, (v - v0) / a / (t - t0) * 3.6e6))
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
            pts.setdefault(r["catchment"], []).append((float(r["t(h)"]), float(r["runoff(mm/h)"]), flag))
    return pts


def compare(ev):
    res = "result_" + ev.lower()
    rates = read_rates(res)
    calc = read_points(os.path.join("data", "calc_%s.csv" % ev))
    obs = read_points(os.path.join("data", "obs_%s.csv" % ev))
    print("== %s: ENCflow vs the calculated runoff of Tani (2023)" % ev)
    print("   %-3s %-10s %4s %8s %8s %8s   %-28s %s" % ("", "runoff", "n", "median", "p90|.|", "max|.|",
                                                      "peak paper / ENCflow (mm/h)", "peak time (h)"))
    table = []
    for name in sorted(calc):
        pk = max(calc[name], key=lambda p: p[1])
        mpk = max(p[1] for p in rates[name] if abs(p[0] - pk[0]) <= 3.0)
        # 極大ごとのピーク時刻の差
        pts = [p for p in calc[name] if not p[2]]
        dts = []
        for t0, q0, _ in pts:
            # 前後 3 h で論文の計算値が最大になる点(破線の細かな凹凸を極大と数えない)
            if q0 > 1.0 and q0 >= max(q for t, q, _ in pts if abs(t - t0) <= 3.0):
                win = [p for p in rates[name] if abs(p[0] - t0) <= 3.0]
                dts.append(max(win, key=lambda p: p[1])[0] - t0)
        for qmin in QMIN:
            lr = []
            for t, q, clipped in calc[name]:
                m = interp(rates[name], t)
                if clipped or q < qmin or not m or m <= 0.0:
                    continue
                lr.append(math.log10(m / q))
                if qmin == QMIN[0]:
                    table.append((name, t, q, m))
            absr = sorted(abs(v) for v in lr)
            tail = ("%6.2f / %6.2f (%+5.1f %%)   %+.2f (%d peaks)"
                    % (pk[1], mpk, 100.0 * (mpk / pk[1] - 1.0), statistics.median(dts) if dts else float("nan"),
                       len(dts))) if qmin == QMIN[0] else ""
            print("   %-3s >= %-4.1f %5d %+8.3f %8.3f %8.3f   %s"
                  % (name if qmin == QMIN[0] else "", qmin, len(lr), statistics.median(lr),
                     absr[int(0.9 * (len(absr) - 1))], absr[-1], tail))
    print("   observed (Fig.): peak of the markers vs ENCflow at the same time")
    for name in sorted(obs):
        pk = max(obs[name], key=lambda p: p[1])
        print("   %-3s observed %.2f mm/h at %.1f h, ENCflow %.2f" % (name, pk[1], pk[0], interp(rates[name], pk[0])))
    with open(os.path.join(res, "compare_%s.csv" % ev.lower()), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["catchment", "t(h)", "paper(mm/h)", "encflow(mm/h)"])
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
    rain = []
    with open(os.path.join("data", "rain_%s.csv" % ev), newline="") as f:
        for r in csv.DictReader(f):
            rain.append((float(r["t_start(h)"]), float(r["t_end(h)"]), float(r["rain(mm/h)"])))
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 6), sharex=True, gridspec_kw=dict(height_ratios=[1, 3]))
    for a, b, r in rain:
        ax1.bar(a, r, width=b - a, align="edge", color="0.7")
    ax1.set_ylabel("rain (mm/h)\n(as drawn)")
    style = {"KT": ("k", "o"), "MN": ("tab:blue", "x"), "SL": ("tab:orange", "^")}
    for name in sorted(calc):
        col, mk = style[name]
        t = [p[0] for p in calc[name] if not p[2]]
        q = [p[1] for p in calc[name] if not p[2]]
        ax2.plot(t, q, color=col, lw=2.5, alpha=0.35, label="%s Tani (2023) calculated" % name)
        ax2.plot([p[0] for p in rates[name]], [max(p[1], 1e-4) for p in rates[name]], color=col, lw=1.0,
                 label="%s ENCflow" % name)
        if name in obs:
            ax2.plot([p[0] for p in obs[name]], [p[1] for p in obs[name]], mk, color=col, ms=4, mfc="none",
                     label="%s observed" % name)
    ax2.set_yscale("log")
    ax2.set_ylim(0.01, 20)
    ax2.set_ylabel("runoff rate (mm/h)")
    ax2.set_xlabel("hours from the left end of the time axis of the figure")
    ax2.legend(fontsize=7, ncol=3)
    fig.tight_layout()
    fn = os.path.join(res, "fig_%s.png" % ev.lower())
    fig.savefig(fn, dpi=120)
    print("   figure: " + fn)


def main():
    evs = sys.argv[1:] or ["TY1", "TY2"]
    for ev in evs:
        compare(ev)


if __name__ == "__main__":
    main()
