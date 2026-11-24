#!/usr/bin/env python3
"""test/paddy の検定(田んぼダムのサブグリッドの水田タンク fn_paddy。developer.md §119)。

Python 標準ライブラリのみ。落水口の装置則(docs/paddy_plan.md §5)を本スクリプトで独立に書き、
1 区画の水収支の常微分方程式の厳密解・参照解と、モデルの台帳 paddy.csv を比べる。円の穴の積分は
Gauss–Legendre の求積で直接求める(モデルは表と展開)。

  python3 Check_paddy.py weir    result          水位調整板の落水: 厳密解と同じ陽解法の参照解、台帳
  python3 Check_paddy.py open    result_open     三角の切欠き(厳密解)と円の穴(参照解)の落水
  python3 Check_paddy.py sep     result_sep      長方形の穴と機能分離型(min の切り替えと越流)の参照解
  python3 Check_paddy.py steady  result_steady   一定の雨の平衡(通常)と、満水の越流(田んぼダム)
  python3 Check_paddy.py spill   result_spill    畦畔の越流の速さ、満水の割合、台帳
  python3 Check_paddy.py mix     result_mix result_mix_nopd   閉じた領域の水の保存(水田なしの同じ計算と比べる)、面積、台帳
  python3 Check_paddy.py dflt    result_dflt Screen_dflt.log   既定値の採用と表示
  python3 Check_paddy.py restart <連続の結果> <再開の結果>      保存 → 再開のビット一致
"""
import math
import os
import sys

G = 9.8           # 重力加速度(モデルの既定 gg = 9.8。&list_sysparam)
DT = 2.0          # 時間刻み (s。param*.txt)


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(1)


def ok(msg):
    print("  ok   " + msg)


def read_csv(path):
    with open(path) as f:
        head = f.readline().strip().split(",")
        rows = []
        for line in f:
            vals = [float(v) for v in line.strip().split(",")]
            rows.append(dict(zip(head, vals)))
    return rows


def read_log(path):
    """Log.txt の (時刻 s, S) の並び(1 列目 h:mm:ss.ss、3 列目 S)"""
    out = []
    with open(path) as f:
        for line in f:
            t = line.split()
            if not t or not t[0][0].isdigit():
                continue
            h, m, s = t[0].split(":")
            out.append((int(h) * 3600 + int(m) * 60 + float(s), float(t[2])))
    return out


# ---------------------------------------------------------------- 装置則(paddy_plan.md §5)
def legendre_nodes(n):
    """Gauss–Legendre の節点と重み([0, 1] に写した値)"""
    xs, ws = [], []
    for i in range(1, n + 1):
        x = math.cos(math.pi * (i - 0.25) / (n + 0.5))
        for _ in range(100):
            p0, p1 = 1.0, x
            for k in range(2, n + 1):
                p0, p1 = p1, ((2 * k - 1) * x * p1 - (k - 1) * p0) / k
            dp = n * (x * p1 - p0) / (x * x - 1)
            dx = p1 / dp
            x -= dx
            if abs(dx) < 1e-15:
                break
        xs.append(0.5 * (1 - x))
        ws.append(1.0 / ((1 - x * x) * dp * dp))   # = 0.5 × 2/((1−x²)P′²)
    return xs, ws


GL_X, GL_W = legendre_nodes(48)


def gfun(eta):
    """G(η) = ∫_0^min(η,1) 2√(u(1−u)) √(η − u) du(u = (1 − cos θ)/2、θ = θm(1 − v²) で端点の特異性を除く)"""
    if eta <= 0:
        return 0.0
    um = min(eta, 1.0)
    tm = math.acos(1 - 2 * um)
    s = 0.0
    for v, w in zip(GL_X, GL_W):
        th = tm * (1 - v * v)
        u = 0.5 * (1 - math.cos(th))
        s += w * 0.5 * math.sin(th) ** 2 * math.sqrt(max(eta - u, 0.0)) * 2 * tm * v
    return s


def weir(c, b, z, h):
    h1 = h - z
    return (2.0 / 3.0) * c * math.sqrt(2 * G) * b * h1 ** 1.5 if h1 > 0 else 0.0


def circle(c, d, z, h):
    return c * math.sqrt(2 * G) * d ** 2.5 * gfun((h - z) / d) if h > z else 0.0


def rect(c, b, e, z, h):
    hh = h - z
    if hh <= 0:
        return 0.0
    return (2.0 / 3.0) * c * math.sqrt(2 * G) * b * (hh ** 1.5 - max(hh - e, 0.0) ** 1.5)


def vnotch(c, ang, z, h):
    hh = h - z
    if hh <= 0:
        return 0.0
    return (8.0 / 15.0) * c * math.tan(math.radians(ang) / 2) * math.sqrt(2 * G) * hh ** 2.5


def euler(q, h0, area, t_end, rain=0.0, perc=0.0, hlev=1e9, zlow=0.0):
    """モデルと同じ陽解法の参照解(雨 → 落水 → 越流 → 減水深の順)。600 s ごとの水深を返す"""
    h = h0
    out = {}
    n_end = int(round(t_end / DT))
    for n in range(1, n_end + 1):
        h += rain * DT
        dv = min(q(h) * DT / area, max(h - zlow, 0.0))
        h -= dv
        h = min(h, hlev)
        h -= min(perc * DT, h)
        if n % 300 == 0:
            out[n * DT] = h
    return out


def compare(rows, key, ref, hmin, tol, label, base=0.0):
    """台帳の平均水深 key (mm) を参照解 ref と比べる(水深が hmin を超える時刻で、base からの深さの相対差)"""
    worst = 0.0
    n = 0
    for r in rows:
        t = r["time(s)"]
        if t not in ref or ref[t] <= hmin:
            continue
        hm = r[key] / 1000.0
        e = abs(hm - ref[t]) / (ref[t] - base)
        worst = max(worst, e)
        n += 1
    if n == 0:
        fail(label + ": no record to compare")
    if worst > tol:
        fail("%s: relative difference %.3e > %.1e" % (label, worst, tol))
    ok("%s: %d records, max relative difference %.2e (tol %.0e)" % (label, n, worst, tol))


def check_ledger(rows, tol=1e-9):
    worst = 0.0
    for r in rows:
        scale = max(r["store1(m3)"] + r["store2(m3)"], r["rain(m3)"], r["outflow(m3)"], 1.0)
        worst = max(worst, abs(r["residual(m3)"]) / scale)
    if worst > tol:
        fail("ledger residual %.3e > %.0e (relative)" % (worst, tol))
    ok("ledger closes (max |residual| / scale %.2e)" % worst)


# ---------------------------------------------------------------- 各検定
def check_weir(res):
    rows = read_csv(os.path.join(res, "paddy.csv"))
    c, b, z, a, h0 = 0.6, 0.30, 0.03, 3000.0, 0.25
    k = (2.0 / 3.0) * c * math.sqrt(2 * G) * b
    exact = {}
    for r in rows:
        t = r["time(s)"]
        exact[t] = z + ((h0 - z) ** -0.5 + k / (2 * a) * t) ** -2
    ref = euler(lambda h: weir(c, b, z, h), h0, a, rows[-1]["time(s)"], zlow=z)
    compare(rows, "h1(mm)", exact, z, 2e-3, "weir vs exact solution (H − z)^−1/2 linear in t", base=z)
    compare(rows, "h1(mm)", ref, z, 1e-9, "weir vs explicit Euler reference", base=z)
    check_ledger(rows)
    last = rows[-1]
    store0 = h0 * last["area1(m2)"]
    if abs(last["outflow(m3)"] - (store0 - last["store1(m3)"])) > 1e-9 * store0:
        fail("outflow does not equal the drained volume")
    ok("outflow = drained volume (%.6f m3)" % last["outflow(m3)"])


def check_open(res):
    rows = read_csv(os.path.join(res, "paddy.csv"))
    a, h0, c = 500.0, 0.25, 0.6
    kv = (8.0 / 15.0) * c * math.tan(math.radians(60.0) / 2) * math.sqrt(2 * G)
    exact = {}
    for r in rows:
        t = r["time(s)"]
        exact[t] = (h0 ** -1.5 + 1.5 * kv / a * t) ** (-2.0 / 3.0)
    compare(rows, "h1(mm)", exact, 0.01, 2e-3, "V-notch vs exact solution H^−3/2 linear in t")
    ref1 = euler(lambda h: vnotch(c, 60.0, 0.0, h), h0, a, rows[-1]["time(s)"])
    compare(rows, "h1(mm)", ref1, 0.01, 1e-7, "V-notch vs explicit Euler reference")
    ref2 = euler(lambda h: circle(c, 0.05, 0.0, h), h0, a, rows[-1]["time(s)"])
    compare(rows, "h2(mm)", ref2, 0.01, 1e-6, "circular hole (chord-width integral) vs explicit Euler reference")
    check_ledger(rows)


def check_sep(res):
    rows = read_csv(os.path.join(res, "paddy.csv"))
    a, h0, c = 500.0, 0.25, 0.6
    ref1 = euler(lambda h: rect(c, 0.12, 0.05, 0.03, h), h0, a, rows[-1]["time(s)"], zlow=0.03)
    compare(rows, "h1(mm)", ref1, 0.04, 1e-7, "rectangular hole vs explicit Euler reference", base=0.03)

    def sep(h):
        return min(weir(c, 0.30, 0.03, h), circle(c, 0.05, 0.0, h) + weir(c, 0.30, 0.20, h))
    ref2 = euler(sep, h0, a, rows[-1]["time(s)"], zlow=0.03)
    compare(rows, "h2(mm)", ref2, 0.035, 1e-6, "separated type min(board, hole + plate overflow) vs reference",
            base=0.03)
    # 流出量調整板の越流が効いた区間(0.20 m 超)と穴だけの区間の両方を通ったこと
    hs = [r["h2(mm)"] for r in rows]
    if not (max(hs) > 200.0 and min(hs) < 200.0):
        fail("separated type did not pass the plate crest (0.20 m)")
    ok("separated type passed the plate crest 0.20 m (overflow then hole only)")
    check_ledger(rows)


def check_steady(res):
    rows = read_csv(os.path.join(res, "paddy.csv"))
    r_in = 20.0 / 3.6e6
    perc = 5.0 / 1000.0 / 86400.0
    a, z, c, b, hlev = 3000.0, 0.03, 0.6, 0.30, 0.30
    k = (2.0 / 3.0) * c * math.sqrt(2 * G) * b
    # 種類 1: 陽解法の不動点は「雨を足した後の水深」が厳密解 H* = z + ((r − perc)A/k)^(2/3)
    hstar = z + ((r_in - perc) * a / k) ** (2.0 / 3.0)
    h1 = rows[-1]["h1(mm)"] / 1000.0 + r_in * DT
    e = abs(h1 - hstar) / (hstar - z)
    if e > 5e-6:
        fail("steady state of class 1: %.9f vs H* %.9f (relative %.2e)" % (h1, hstar, e))
    ok("class 1 converges to H* = z + ((r − perc)A/k)^(2/3) = %.6f m (relative %.1e)" % (hstar, e))
    # 種類 2: 穴の最大の流出は雨より小さい → 畦畔まで満ちて越流する。保存値は hlev − perc·dt
    h2 = rows[-1]["h2(mm)"] / 1000.0
    if abs(h2 - (hlev - perc * DT)) > 1e-12:
        fail("class 2 is not full at the levee crest: %.12f" % h2)
    if rows[-1]["full2(-)"] != 1.0:
        fail("full2 is not 1 at the end")
    ok("class 2 is full at the levee crest (h2 = hlev − perc·dt, full2 = 1)")
    # 満水の間の越流の速さ = 面積 × ((r − perc) − Q(hlev + (r − perc)dt)/A)
    q2 = circle(0.6, 0.05, 0.0, hlev + (r_in - perc) * DT)
    rate = rows[-1]["area2(m2)"] * ((r_in - perc) - q2 / a)
    d = (rows[-1]["spill(m3)"] - rows[-2]["spill(m3)"]) / (rows[-1]["time(s)"] - rows[-2]["time(s)"])
    if abs(d - rate) > 1e-6 * rate:
        fail("spill rate %.9e vs expected %.9e" % (d, rate))
    ok("spill rate at the full state = area × ((r − perc) − Q(hlev)/A) = %.6e m3/s" % rate)
    check_ledger(rows)


def check_spill(res):
    rows = read_csv(os.path.join(res, "paddy.csv"))
    r_in = 80.0 / 3.6e6
    a, hlev = 3000.0, 0.30
    hmax = max(r["h2(mm)"] for r in rows) / 1000.0
    if hmax > hlev + 1e-12:
        fail("ponding depth exceeds the levee height: %.12f" % hmax)
    full = [r for r in rows if r["full2(-)"] == 1.0 and r["time(s)"] <= 21600.0]
    if len(full) < 3:
        fail("the paddy fields did not stay full during the rain")
    q2 = circle(0.6, 0.05, 0.0, hlev + r_in * DT)
    rate = rows[0]["area2(m2)"] * (r_in - q2 / a)
    d = (full[-1]["spill(m3)"] - full[-2]["spill(m3)"]) / (full[-1]["time(s)"] - full[-2]["time(s)"])
    if abs(d - rate) > 1e-6 * rate:
        fail("spill rate %.9e vs expected %.9e" % (d, rate))
    ok("full during the rain (%d records), spill rate = area × (r − Q(hlev)/A) = %.6e m3/s" % (len(full), rate))
    if rows[-1]["full2(-)"] != 0.0 or rows[-1]["h2(mm)"] / 1000.0 >= hlev:
        fail("the paddy fields are still full after the rain")
    ok("drains below the levee crest after the rain (h2 = %.2f mm)" % rows[-1]["h2(mm)"])
    check_ledger(rows)


def check_mix(res, res0):
    """閉じた領域(四辺が壁): 水田ありの S の増分 + 減水深の累積 = 水田なしの同じ計算の S の増分(= 降った雨)"""
    rows = read_csv(os.path.join(res, "paddy.csv"))
    if abs(rows[0]["area1(m2)"] - 1960.0) > 1e-9 or abs(rows[0]["area2(m2)"] - 2120.0) > 1e-9:
        fail("class areas %.6f %.6f differ from 1960 / 2120 m2" % (rows[0]["area1(m2)"], rows[0]["area2(m2)"]))
    ok("class areas from the fraction and adoption maps: 1960 / 2120 m2")
    domain = 10 * 8 * 100.0              # 領域の面積 (m2)
    perc = {r["time(s)"]: r["perc(m3)"] for r in rows}
    log1 = read_log(os.path.join(res, "Log.txt"))
    log0 = dict(read_log(os.path.join(res0, "Log.txt")))
    s1_0 = log1[0][1]
    s0_0 = log0[0.0]
    worst = 0.0
    n = 0
    for t, s in log1:
        if t not in log0 or (t > 0 and t not in perc):
            continue
        lhs = (s - s1_0) + (perc[t] / domain if t > 0 else 0.0)
        worst = max(worst, abs(lhs - (log0[t] - s0_0)))
        n += 1
    if n < 10 or worst > 1e-12:
        fail("water is not conserved in the closed domain: max |diff| %.3e m (%d times)" % (worst, n))
    ok("closed domain: increase of S (surface + paddy tanks) + percolation = rain (no-paddy run), "
       "%d times, max |diff| %.1e m" % (n, worst))
    check_ledger(rows)


def check_dflt(res, screen):
    text = open(screen).read()
    need = ["paddy: pd_aplot = 3000.0000 m2 (default)", "paddy: pd_hlev = 0.3000 m (default)",
            "paddy: pd_perc_mmd = 5.0000 mm/d (default)", "paddy: pd_adopt = 0.0000 (default)",
            "paddy: pd_dev_type(1) = 0 (default)", "paddy: pd_board_h(1) = 0.0300 m (default)",
            "paddy: pd_board_w(1) = 0.3000 m (default)", "paddy: pd_cw(1) = 0.6000 (default)",
            "paddy: initial ponding depth of class 1 = 0.300000E-1 m (default"]
    for s in need:
        if s not in text:
            fail("default not shown: " + s)
    ok("%d defaults adopted and shown" % len(need))
    if "pd_dev_type(2)" in text:
        fail("defaults of the absent class 2 are shown")
    ok("no default is shown for the absent class 2")


def check_restart(cont, rest):
    for f in ["H9998.txt", "Hpn9998.txt", "Hpd9998.txt"]:
        a = open(os.path.join(cont, f), "rb").read()
        b = open(os.path.join(rest, f), "rb").read()
        if a != b:
            fail("%s differs between the continuous and restarted runs" % f)
        ok("%s identical (continuous vs save → restore)" % f)
    la = open(os.path.join(cont, "Log.txt")).read().split("\n")
    lb = open(os.path.join(rest, "Log.txt")).read().split("\n")
    la = [x for x in la if x.strip()][-1]
    lb = [x for x in lb if x.strip()][-1]
    if la != lb:
        fail("the last Log line differs:\n  %s\n  %s" % (la, lb))
    ok("last Log line identical")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    cmd = sys.argv[1]
    if cmd == "weir":
        check_weir(sys.argv[2])
    elif cmd == "open":
        check_open(sys.argv[2])
    elif cmd == "sep":
        check_sep(sys.argv[2])
    elif cmd == "steady":
        check_steady(sys.argv[2])
    elif cmd == "spill":
        check_spill(sys.argv[2])
    elif cmd == "mix":
        check_mix(sys.argv[2], sys.argv[3])
    elif cmd == "dflt":
        check_dflt(sys.argv[2], sys.argv[3])
    elif cmd == "restart":
        check_restart(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)
        sys.exit(2)
    print("PASS: " + cmd)


if __name__ == "__main__":
    main()
