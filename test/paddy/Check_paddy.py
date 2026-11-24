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
  python3 Check_paddy.py wash    result_wash     雨滴侵食(f_wash の雨滴の項)に 1 − 面積率が掛かること
  python3 Check_paddy.py splash  result_splash   乾いた斜面の侵食(f_splash)に 1 − 面積率が掛かること
  python3 Check_paddy.py tw_back  result_tw_back   双方向: 落水口からの逆流(同じ陽解法の参照解)と S の保存
  python3 Check_paddy.py tw_fill  result_tw_fill   双方向: 畦畔を越える浸水での瞬時の満水と、二重計上がないこと
  python3 Check_paddy.py tw_flood result_tw_flood  双方向: 外水の流入での水の保存、満水
  python3 Check_paddy.py tw_drain result_tw_drain  双方向: 浸水が引いた後の落水
"""
import array
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
            "paddy: initial ponding depth of class 1 = 0.300000E-1 m (default",
            "paddy: f_pd_exchange = 0 (default)"]
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


def read_bil(path, nx, ny):
    """単精度のバイナリ(m_fileio の write_bil_real: (1:nx, 1:ny) を列優先で並べた float32)"""
    v = array.array("f")
    with open(path, "rb") as f:
        v.frombytes(f.read())
    if sys.byteorder != "little":
        v.byteswap()
    if len(v) != nx * ny:
        fail("%s: %d values, expected %d" % (path, len(v), nx * ny))
    return v


def check_erosion(res, kind):
    """雨滴侵食から水田の部分を外す(§119.5)。地盤の下がり = −(1 − a)·k·P·T(全セル)。
    a = 1 のセルは侵食 0(wash は沈降を止めた浮遊砂の 1e-30 程度の堆積を除く)、
    a = 0 のセルは水田なしの式そのもの"""
    nx, ny = 10, 8
    with open(os.path.join("data_paddy", "frac_mix.txt")) as f:
        rows = [[float(x) for x in line.split()] for line in f if line.strip()]
    col = rows[0]
    if any(r != col for r in rows) or len(col) != nx:
        fail("frac_mix.txt is expected to vary by column only")
    if kind == "wash":
        k, p_mmh, t_geo = 0.01, 50.0, 3600.0         # wash_kr、雨、T(morfac = 1)
    else:
        k, p_mmh, t_geo = 0.003, 30.0, 3600.0 * 5.0  # spl_kr、雨、T_geo = tt·morfac
    full = k * p_mmh / 3.6e6 * t_geo                 # 水田なしの侵食深 (m。poroi = 1)
    z0 = read_bil(os.path.join(res, "Z0000.bil"), nx, ny)
    z1 = read_bil(os.path.join(res, "Z0001.bil"), nx, ny)
    emax = 0.0
    for j in range(ny):
        for i in range(nx):
            a = col[i]
            dz = z1[j * nx + i] - z0[j * nx + i]
            if a >= 1.0:
                if abs(dz) > 1e-12 * full:
                    fail("%s: the all-paddy cell (%d, %d) is eroded: dz = %.3e m" % (kind, i + 1, j + 1, dz))
                continue
            exp = -(1.0 - a) * full
            e = abs(dz - exp) / full
            emax = max(emax, e)
            if e > 1e-6:
                fail("%s: cell (%d, %d) a = %.1f: dz = %.9e m, expected %.9e m" % (kind, i + 1, j + 1, a, dz, exp))
    ok("%s: z − z0 = −(1 − a)·k·P·T on every cell (max error %.1e of %.3e m); no erosion where a = 1"
       % (kind, emax, full))


# ---------------------------------------------------------------- 双方向(二室化。§119.6)
def tw_wq(k, z, h, hd):
    """水位調整板の堰(モデルの weir_q と dev_q の型 0 と同じ。h ≤ z か hd ≥ h なら 0、h2/h1 > 2/3 で潜り)"""
    if h <= z or hd >= h:
        return 0.0
    h1 = h - z
    h2 = max(hd - z, 0.0)
    if h2 >= h1:
        return 0.0
    q = k * h1 * math.sqrt(h1)
    if h2 > h1 * (2.0 / 3.0):
        r = h2 / h1
        q *= 1.5 * math.sqrt(3.0) * r * math.sqrt(max(1.0 - r, 0.0))
    return q


def log_s(res):
    return [v for _, v in read_log(os.path.join(res, "Log.txt"))]


def check_tw_back(res):
    """落水口からの逆流: 階段形の断面(畦畔より下は水田でない面積の割合 f)・両向きの装置則・上限を、モデルと
    同じ順で 1 区画について解いた参照解と、台帳の湛水深を比べる"""
    rows = read_csv(os.path.join(res, "paddy.csv"))
    a, gv, hlev, area = 0.6, 1.0, 0.30, 300.0
    c, b, zb = 0.6, 0.30, 0.03
    f = 1.0 - a / gv
    k = (2.0 / 3.0) * c * math.sqrt(2 * G) * b

    def v_of(h):
        return h - hlev * (1.0 - f) if h >= hlev else (h if h <= 0.0 else f * h)

    def h_of(v):
        return v + hlev * (1.0 - f) if v >= hlev * f else (v if v <= 0.0 else v / f)

    h, tk = 0.15, 0.0
    ref = {}
    for n in range(1, int(round(rows[-1]["time(s)"] / DT)) + 1):
        vh = max(v_of(h), 0.0)
        hd = h_of(vh)
        r = a / (gv * (1.0 if hd >= hlev else f))
        q = 0.0
        if hd < hlev:
            if tk >= hd:
                q = min(tw_wq(k, zb, tk, hd) * DT / area, max(tk - zb, 0.0), 0.5 * (tk - hd) / (1.0 + r))
            else:
                q = -min(tw_wq(k, zb, hd, tk) * DT / area, 0.5 * (hd - tk) / (1.0 + r))
        tk -= q
        vh = max(vh + a * q / gv, 0.0)
        h = h_of(vh)
        if n % 300 == 0:
            ref[n * DT] = tk
    compare(rows, "h1(mm)", ref, 0.001, 1e-9, "two-way backflow through the outlet vs explicit reference")
    s = log_s(res)
    if max(abs(x - s[0]) for x in s) > 1e-12 * s[0]:
        fail("S (surface + paddy tanks) is not conserved in the closed box")
    ok("S conserved (%.12f m); final ponding depth %.6f m = equilibrium 0.06 m" % (s[0], rows[-1]["h1(mm)"] / 1e3))
    if abs(rows[-1]["h1(mm)"] / 1e3 - 0.06) > 1e-6:
        fail("the levels do not even out at 0.06 m")
    if not rows[-1]["inflow(m3)"] > 0.0:
        fail("no inflow through the outlets is recorded")
    check_ledger(rows)


def check_tw_fill(res):
    """瞬時の満水: 湛水深 = 畦畔高、地表の水深 = 0.5 − 0.6 × (0.30 − 0.03) = 0.338 m、S = 地表の水深(二重計上なし)"""
    rows = read_csv(os.path.join(res, "paddy.csv"))
    last = rows[-1]
    if abs(last["h1(mm)"] - 300.0) > 1e-9:
        fail("the paddy fields are not filled to the levee crest: %.12f mm" % last["h1(mm)"])
    exp_fill = 0.6 * 8000.0 * (0.30 - 0.03)
    if abs(last["levee_in(m3)"] - exp_fill) > 1e-9 * exp_fill:
        fail("levee inflow %.9f m3, expected %.9f m3" % (last["levee_in(m3)"], exp_fill))
    if last["inflow(m3)"] != 0.0:
        fail("the outlets exchange water while the surface is above the levee crest")
    hv = read_bil(os.path.join(res, "H0001.bil"), 10, 8)
    hexp = 0.50 - 0.6 * (0.30 - 0.03)
    e = max(abs(x - hexp) for x in hv)
    if e > 1e-6:
        fail("surface depth differs from %.6f m by %.3e m" % (hexp, e))
    s = log_s(res)[-1]
    if abs(s - hexp) > 1e-12:
        fail("S = %.15f m differs from the depth of the merged water %.15f m (double counting?)" % (s, hexp))
    ok("filled to the levee crest instantly (levee inflow %.3f m3); surface depth %.6f m; S = depth of the "
       "merged water (no double counting)" % (last["levee_in(m3)"], hexp))
    check_ledger(rows)


def check_tw_flood(res):
    """外水の流入: S の増分 + 減水深 = 流し込んだ外水(1.0 m3/s × 7200 s / 8000 m2)、満水、台帳"""
    rows = read_csv(os.path.join(res, "paddy.csv"))
    s = read_log(os.path.join(res, "Log.txt"))
    t_end = s[-1][0]
    area = 8000.0
    vin = 1.0 * t_end / area
    perc = rows[-1]["perc(m3)"] / area
    d = (s[-1][1] - s[0][1]) + perc - vin
    if abs(d) > 1e-9 * vin:
        fail("water balance: increase of S + percolation - inflow = %.3e m" % d)
    ok("water balance: increase of S (surface + paddy tanks) + percolation = inflow %.6f m (diff %.1e m)" % (vin, d))
    last = rows[-1]
    if not (last["levee_in(m3)"] > 0.0 and last["inflow(m3)"] > 0.0):
        fail("no inflow over the levees or through the outlets is recorded")
    if not (last["full1(-)"] > 0.999 and last["full2(-)"] > 0.999):
        fail("not all paddy fields are full at the end (%.4f, %.4f)" % (last["full1(-)"], last["full2(-)"]))
    if last["spill(m3)"] != 0.0:
        fail("spill recorded while the flood stays above the levee crest (%.3e m3)" % last["spill(m3)"])
    ok("flood water entered through the outlets (%.1f m3) and over the levees (%.1f m3); all paddy fields full"
       % (last["inflow(m3)"], last["levee_in(m3)"]))
    check_ledger(rows)


def check_tw_drain(res):
    """浸水が引いた後: 湛水深 ≤ 畦畔高、通常の落水口のほうが速く抜け、流入はなく、台帳が閉じる"""
    rows = read_csv(os.path.join(res, "paddy.csv"))
    for r in rows:
        if r["h1(mm)"] > 300.0 + 1e-9 or r["h2(mm)"] > 300.0 + 1e-9:
            fail("ponding depth above the levee crest at t = %.0f s" % r["time(s)"])
    h1 = [r["h1(mm)"] for r in rows]
    h2 = [r["h2(mm)"] for r in rows]
    if any(h1[i + 1] > h1[i] + 1e-9 for i in range(len(h1) - 1)) or any(h2[i + 1] > h2[i] + 1e-9 for i in range(len(h2) - 1)):
        fail("the ponding depth rises while the flood recedes")
    if not (h1[-1] < 150.0 and h2[-1] > h1[-1] and h2[-1] < 300.0):
        fail("unexpected drainage: normal %.1f mm, paddy dam %.1f mm after %.0f h" % (h1[-1], h2[-1], rows[-1]["time(s)"] / 3600))
    if rows[-1]["inflow(m3)"] != 0.0 or rows[-1]["levee_in(m3)"] != 0.0:
        fail("inflow into the paddy fields while the flood recedes")
    ok("ponding depth <= levee crest and falling; after %.0f h normal outlets %.1f mm, paddy dams %.1f mm"
       % (rows[-1]["time(s)"] / 3600, h1[-1], h2[-1]))
    check_ledger(rows)


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
    elif cmd in ("wash", "splash"):
        check_erosion(sys.argv[2], cmd)
    elif cmd == "tw_back":
        check_tw_back(sys.argv[2])
    elif cmd == "tw_fill":
        check_tw_fill(sys.argv[2])
    elif cmd == "tw_flood":
        check_tw_flood(sys.argv[2])
    elif cmd == "tw_drain":
        check_tw_drain(sys.argv[2])
    else:
        print(__doc__)
        sys.exit(2)
    print("PASS: " + cmd)


if __name__ == "__main__":
    main()
