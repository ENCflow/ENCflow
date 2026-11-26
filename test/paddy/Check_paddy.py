#!/usr/bin/env python3
"""test/paddy の検定(田んぼダムのサブグリッドの水田タンク fn_paddy。developer.md §127)。

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
  python3 Check_paddy.py b_drain  result_b_drain   区画の解像(B): 1 区画の落水(堰の厳密解・穴の参照解)、台帳
  python3 Check_paddy.py b_tight  result_b_tight   区画の解像(B): 畦畔・市松の角の水密(全セルで 初期 + 雨)
  python3 Check_paddy.py b_over   result_b_over    区画の解像(B): 畦畔の越流と閉じた領域の水の保存
  python3 Check_paddy.py b_back   result_b_back    区画の解像(B): 落水口からの逆流、水位がそろうこと、保存
  python3 Check_paddy.py b_ext    result_b_ext     区画の解像(B): 畦畔を越える外からの流入、水位がそろうこと、保存
  python3 Check_paddy.py b_bank   result_b_bank    区画の解像(B): 畦畔と河川堤防が重なるエッジは天端の大きい方
  python3 Check_paddy.py b_chain  result_b_chain   区画の解像(B): 区画から区画への落水口(田越し)、水深がそろうこと、保存
  python3 Check_paddy.py restart_b <連続の結果> <再開の結果>    区画の解像(B)の保存 → 再開のビット一致
  python3 Check_paddy.py wq_a     result_wq_a      水質: タンクの濃度の一次減衰(厳密解)と質量の収支
  python3 Check_paddy.py wq_rain  result_wq_rain   水質: 雨の物質でタンクの濃度が雨の濃度へ近づくことと質量の収支
  python3 Check_paddy.py wq_tw    result_wq_tw     水質: 双方向の逆流で水田に入る水の濃度と閉じた箱の質量の保存
  python3 Check_paddy.py wq_b     result_wq_b      水質: 区画の解像(B)の減水深の持ち出しを含む質量の収支
  python3 Check_paddy.py wq_vs    result_wq_vs     水質: タンクの沈降(離散式の厳密解、湛水深で割る)と質量の収支
  python3 Check_paddy.py restart_wq <連続の結果> <再開の結果>   水質のプールの保存 → 再開のビット一致
  python3 Check_paddy.py sed_tw   result_sed_tw    土砂: 双方向のタンクへ入る水の浮遊砂を田面に積む(固相の保存)
  python3 Check_paddy.py b_sed    result_b_sed     土砂: 区画の解像で掃流砂が畦畔を越えない(区画ごとの河床の変化の合計 0)
  python3 Check_paddy.py restart_sed <連続の結果> <再開の結果>  土砂: 堆積の記録の保存 → 再開のビット一致
  python3 Check_paddy.py catch    result_catch     集水面積率(片方向): 閉じた箱の雨だけの厳密解(タンク・地表)と台帳
  python3 Check_paddy.py catch_tw result_catch_tw  集水面積率(双方向): 同じ厳密解(地表の水は水田でない面積だけ)
  python3 Check_paddy.py catch_zero <与えない結果> <c = 0 を与えた結果>   集水面積率 0 の分布でビット一致(catch 列を除く)
  python3 Check_paddy.py catch_sp    result_catch_sp     集水面積の雨を 3 × 3 の近傍の水田へ配る(片方向): セルごとの
                                                         タンクの水深・種類ごとの平均湛水深と濃度の厳密解、台帳
  python3 Check_paddy.py catch_sp_tw result_catch_sp_tw  同じ(双方向)
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


def check_restart(cont, rest, files=("H9998.txt", "Hpn9998.txt", "Hpd9998.txt")):
    for f in files:
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
    """雨滴侵食から水田の部分を外す(§127.5)。地盤の下がり = −(1 − a)·k·P·T(全セル)。
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


# ---------------------------------------------------------------- 双方向(二室化。§127.6)
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

# ---------------------------------------------------------------- 区画の解像(表現 B。developer.md §127.8)
B_DX = 5.0        # param_b_*.txt の格子間隔 (m)


def rk4(q, h0, area, times, step=2.0):
    """1 区画の水収支 dH/dt = −Q(H)/A の参照解(古典的ルンゲクッタ。times の時刻ごとの水深)"""
    out = {}
    h, t = h0, 0.0
    for te in sorted(times):
        n = max(1, int(round((te - t) / step)))
        dt = (te - t) / n
        for _ in range(n):
            k1 = -q(h) / area
            k2 = -q(h + 0.5 * dt * k1) / area
            k3 = -q(h + 0.5 * dt * k2) / area
            k4 = -q(h + dt * k3) / area
            h += dt * (k1 + 2 * k2 + 2 * k3 + k4) / 6.0
        t = te
        out[te] = h
    return out


def b_levels(res, name, nx, ny, zfile=None):
    """終わりの水位(H0001.bil の水深 + 地盤)"""
    h = read_bil(os.path.join(res, name), nx, ny)
    z = [0.0] * (nx * ny)
    if zfile:
        with open(os.path.join("data_paddy", zfile)) as f:
            z = [float(x) for line in f for x in line.split()]
    return [h[k] + z[k] for k in range(nx * ny)], h, z


def no_exchange(last, keys, label):
    for k in keys:
        if last[k] != 0.0:
            fail("%s: %s = %.3e m3 (expected none)" % (label, k, last[k]))


def check_b_drain(res):
    """10 × 12 セル(3000 m2)の区画 2 つの落水。種類 1 は水位調整板の堰(厳密解)、種類 2 は円の穴(参照解)"""
    rows = read_csv(os.path.join(res, "paddy.csv"))
    a, h0, c = 3000.0, 0.25, 0.6
    if abs(rows[0]["area1(m2)"] - a) > 1e-9 or abs(rows[0]["area2(m2)"] - a) > 1e-9:
        fail("plot areas %.6f %.6f differ from 3000 m2" % (rows[0]["area1(m2)"], rows[0]["area2(m2)"]))
    ok("plot areas 3000 / 3000 m2 (10 x 12 cells of 5 m)")
    k = (2.0 / 3.0) * c * math.sqrt(2 * G) * 0.30
    exact = {}
    for r in rows:
        t = r["time(s)"]
        exact[t] = 0.03 + ((h0 - 0.03) ** -0.5 + k / (2 * a) * t) ** -2
    compare(rows, "h1(mm)", exact, 0.03, 2e-3, "resolved plot, board weir vs exact solution", base=0.03)
    ref2 = rk4(lambda h: circle(c, 0.05, 0.0, h) + weir(c, 0.30, 0.29, h), h0, a, [r["time(s)"] for r in rows])
    compare(rows, "h2(mm)", ref2, 0.01, 2e-3, "resolved plot, circular hole vs ODE reference (RK4)")
    check_ledger(rows)
    last = rows[-1]
    drained = 2 * h0 * a - (last["store1(m3)"] + last["store2(m3)"])
    if abs(last["outflow(m3)"] - drained) > 1e-9 * drained:
        fail("outlet outflow %.9f m3 differs from the drained volume %.9f m3" % (last["outflow(m3)"], drained))
    no_exchange(last, ("spill(m3)", "levee_in(m3)", "inflow(m3)"), "b_drain")
    ok("outlet outflow = drained volume (%.6f m3); no flow over the levees, no inflow" % drained)


def check_b_tight(res):
    """落水口のない区画: どのセルも 初期の水深 + 雨(畦畔・斜めの階段の境・市松の角を水が抜けない)"""
    nx, ny = 20, 16
    rows = read_csv(os.path.join(res, "paddy.csv"))
    last = rows[-1]
    r_in = last["rain(m3)"] / last["area1(m2)"]
    h0 = read_bil(os.path.join(res, "H0000.bil"), nx, ny)
    h1 = read_bil(os.path.join(res, "H0001.bil"), nx, ny)
    worst, wc = 0.0, None
    for j in range(ny):
        for i in range(nx):
            d = h1[j * nx + i] - h0[j * nx + i] - r_in
            if abs(d) > abs(worst):
                worst, wc = d, (i + 1, j + 1)
    if abs(worst) > 1e-6:
        fail("water moved across a levee: depth change - rain = %.3e m at %s" % (worst, wc))
    ok("every cell gained exactly the rain %.6f m (max |diff| %.1e m; single precision output)" % (r_in, abs(worst)))
    for (i, j), hexp, what in (((14, 4), 0.2, "pool D1"), ((15, 5), 0.0, "pool D2 (diagonal through the plot pinch)"),
                               ((14, 12), 0.2, "cell 1 of plot 4"), ((15, 13), 0.05, "cell 2 of plot 4 (diagonal)")):
        v = h0[(j - 1) * nx + (i - 1)]
        if abs(v - hexp) > 1e-6:
            fail("initial depth of %s is %.6f m, expected %.2f m" % (what, v, hexp))
    ok("initial depths of the pools and the diagonal plot cells differ (0.2 / 0 / 0.2 / 0.05 m) and stay apart")
    check_ledger(rows)
    no_exchange(last, ("outflow(m3)", "spill(m3)", "levee_in(m3)", "inflow(m3)"), "b_tight")
    ok("no flow through the plot boundaries")


def check_b_over(res):
    """畦畔の越流: 閉じた領域の水の保存(S の増分 + 減水深 = 雨)、越流、区画の水深"""
    rows = read_csv(os.path.join(res, "paddy.csv"))
    area_dom = 20 * 20 * B_DX * B_DX
    s = read_log(os.path.join(res, "Log.txt"))
    by_t = {r["time(s)"]: r for r in rows}
    worst, n = 0.0, 0
    for t, sv in s[1:]:
        r = by_t[t]
        lhs = (sv - s[0][1]) + r["perc(m3)"] / area_dom
        rain = r["rain(m3)"] / r["area1(m2)"]
        worst = max(worst, abs(lhs - rain))
        n += 1
    if n < 2 or worst > 1e-12:
        fail("closed domain: increase of S + percolation - rain = %.3e m" % worst)
    ok("closed domain: increase of S + percolation = rain (%d times, max |diff| %.1e m)" % (n, worst))
    hm = [r["h1(mm)"] / 1e3 for r in rows]
    if not max(hm) > 0.30:
        fail("the plot water did not rise above the levee crest (max %.4f m)" % max(hm))
    last = rows[-1]
    if not last["spill(m3)"] > 0.0:
        fail("no flow over the levees is recorded")
    if not (0.2995 < hm[-1] < 0.302):
        fail("after the rain the plot water should fall to just above the crest: %.5f m" % hm[-1])
    if last["levee_in(m3)"] != 0.0 or last["outflow(m3)"] != 0.0 or last["inflow(m3)"] != 0.0:
        fail("unexpected exchange (outlet or inflow over the levees)")
    ok("overflow over the levees %.1f m3; max plot depth %.4f m, %.4f m one hour after the rain"
       % (last["spill(m3)"], max(hm), hm[-1]))
    check_ledger(rows)


def check_b_even(res, efile, e0_out, levee_in_expected):
    """閉じた領域で区画の外(水位 e0_out)から区画へ水が入り、水位がそろう(水位 = 体積の保存から決まる値)"""
    nx, ny = 20, 20
    rows = read_csv(os.path.join(res, "paddy.csv"))
    s = [v for _, v in read_log(os.path.join(res, "Log.txt"))]
    if max(abs(x - s[0]) for x in s) > 1e-12 * s[0]:
        fail("S is not conserved in the closed domain")
    ok("S conserved in the closed domain (%.12f m)" % s[0])
    lv, h, z = b_levels(res, "H0001.bil", nx, ny, "b_back_z.txt")
    vol = sum(h)                       # 体積 / セル面積
    eeq = (vol + sum(z)) / (nx * ny)    # 全セルが浸かっているときの水位
    worst = max(abs(x - eeq) for x in lv)
    if worst > 2e-3:
        fail("levels have not evened out: max |level - %.5f| = %.3e m" % (eeq, worst))
    if abs(eeq - (0.75 * e0_out + 0.25 * 0.05)) > 1e-4:
        fail("equilibrium level %.6f m differs from the volume balance %.6f m" % (eeq, 0.75 * e0_out + 0.25 * 0.05))
    ok("plot and surroundings at the same level %.5f m (max |diff| %.1e m)" % (eeq, worst))
    last = rows[-1]
    gain = last["store1(m3)"] - rows[0]["store1(m3)"] + (rows[0]["inflow(m3)"] + rows[0]["levee_in(m3)"]
                                                          - rows[0]["outflow(m3)"] - rows[0]["spill(m3)"])
    net = last["inflow(m3)"] + last["levee_in(m3)"] - last["outflow(m3)"] - last["spill(m3)"]
    if abs(gain - net) > 1e-9 * max(gain, 1.0):
        fail("plot water gained %.9f m3 but the net inflow is %.9f m3" % (gain, net))
    if not last["inflow(m3)"] > 0.0:
        fail("no inflow through the outlet is recorded")
    if levee_in_expected and not last["levee_in(m3)"] > 0.0:
        fail("no inflow over the levees is recorded")
    if not levee_in_expected and last["levee_in(m3)"] != 0.0:
        fail("inflow over the levees while the outside level stays below the crest")
    ok("plot water gained = inflow through the outlet %.2f m3 + over the levees %.2f m3 - outflow %.2e m3"
       % (last["inflow(m3)"], last["levee_in(m3)"], last["outflow(m3)"] + last["spill(m3)"]))
    check_ledger(rows)



def check_b_bank(res):
    """区画の東隣が河道(堤防の天端 = 地盤 + 0.1 m)。外の水位 0.20 m は堤防より上・畦畔(0.30 m)より下なので、
    重なるエッジの天端が大きい方(畦畔)なら区画に水は入らない(堤防の天端だけなら越流して入る)"""
    nx, ny = 20, 20
    rows = read_csv(os.path.join(res, "paddy.csv"))
    h = read_bil(os.path.join(res, "H0001.bil"), nx, ny)
    pl = [h[(j - 1) * nx + (i - 1)] for j in range(6, 16) for i in range(8, 18)]
    worst = max(abs(v - 0.05) for v in pl)
    if worst > 1e-6:
        fail("water crossed the edge shared by the levee and the river bank: max |plot depth - 0.05| = %.3e m" % worst)
    ok("plot depth stays 0.05 m next to the channel (bank crest 0.1 m < levee crest 0.3 m; max |diff| %.1e m)" % worst)
    s = [v for _, v in read_log(os.path.join(res, "Log.txt"))]
    if max(abs(x - s[0]) for x in s) > 1e-12 * s[0]:
        fail("S is not conserved in the closed domain")
    no_exchange(rows[-1], ("outflow(m3)", "spill(m3)", "levee_in(m3)", "inflow(m3)"), "b_bank")
    ok("S conserved; no flow through the plot boundaries")
    check_ledger(rows)


def check_b_chain(res):
    """区画 A(種類 1、初期 0.25 m)の落水口が隣の区画 B(種類 2、初期 0)を向く(田越し)。同じ面積なので終わりに
    両方 0.125 m。A の落水口からの流出 = B の落水口からの流入(区画どうしの流れは両方に数える)"""
    rows = read_csv(os.path.join(res, "paddy.csv"))
    last = rows[-1]
    h1, h2 = last["h1(mm)"] / 1e3, last["h2(mm)"] / 1e3
    if abs(h1 - 0.125) > 1e-3 or abs(h2 - 0.125) > 1e-3:
        fail("the plots did not even out at 0.125 m: A %.5f m, B %.5f m" % (h1, h2))
    ok("plots A and B even out (A %.5f m, B %.5f m; 0.125 m from the volume balance)" % (h1, h2))
    if abs(last["outflow(m3)"] - last["inflow(m3)"]) > 1e-9 * last["outflow(m3)"]:
        fail("outflow from A %.9f m3 differs from the inflow into B %.9f m3" % (last["outflow(m3)"], last["inflow(m3)"]))
    # 落水口を通る流れは A の流出(B の流入)と、水位がそろう近くで向きが逆になった分(B の流出・A の流入)の和
    area = 7 * 8 * B_DX * B_DX
    loss_a = 0.25 * area - last["store1(m3)"]
    gain_b = last["store2(m3)"]                  # B は空から始まる
    back = last["outflow(m3)"] - loss_a
    if abs(loss_a - gain_b) > 1e-9 * loss_a:
        fail("plot A lost %.9f m3 but plot B gained %.9f m3" % (loss_a, gain_b))
    if not (-1e-9 * loss_a <= back <= 1e-3 * loss_a):
        fail("outlet outflow %.9f m3 does not match the water moved from A to B %.9f m3" % (last["outflow(m3)"], loss_a))
    no_exchange(last, ("spill(m3)", "levee_in(m3)"), "b_chain")
    ok("A lost = B gained = %.6f m3; outlet outflow = inflow (%.6f m3, of which %.1e m3 back and forth near the "
       "end); no flow over the levees" % (loss_a, last["outflow(m3)"], back))
    s = [v for _, v in read_log(os.path.join(res, "Log.txt"))]
    if max(abs(x - s[0]) for x in s) > 1e-12 * s[0]:
        fail("S is not conserved in the closed domain")
    ok("S conserved in the closed domain")
    check_ledger(rows)


# ---------------------------------------------------------------- 水質(§127.10)
def wq_closure(res, m0=None, tol=1e-6):
    """wq.csv の質量の収支: 貯留(地表・タンク)+ 出 − 入 が一定(= 初めの質量 m0)。wq.csv は有効数字 8 桁
    (es15.7)なので、許容は初めの質量か入力の累積の大きい方に対して相対 1e-6"""
    rows = read_csv(os.path.join(res, "wq.csv"))
    ins = ("in_point_g", "in_area_g", "in_map_g", "in_rain_g", "in_gwc_g", "in_bldup_g", "in_edge_g", "in_stage_g")
    outs = ("decay_g", "settle_g", "out_sea_g", "out_edge_g", "out_stage_g", "out_intake_g", "out_paddy_perc_g")
    vals = []
    for r in rows:
        stores = r["mass_surface_g"] + r["mass_paddy_g"]
        vals.append(stores + sum(r[k] for k in outs) - sum(r[k] for k in ins))
    ref = m0 if m0 is not None else vals[0]
    scale = max(abs(ref), max(sum(r[k] for k in ins) for r in rows), 1e-30)
    worst = max(abs(v - ref) for v in vals) / scale
    if worst > tol:
        fail("wq mass balance: stores + outputs - inputs drifts by %.3e (relative to %.6g g)" % (worst, ref))
    ok("wq mass balance closes (stores + outputs - inputs = %.6f g, max relative drift %.1e)" % (ref, worst))
    return rows


def check_wq_a(res):
    """事前の湛水 10 mg/L・半減期 6 h: タンクの濃度 = 10 × 2^(−t/6 h)(落水・減水深は濃度を変えない)"""
    rows = read_csv(os.path.join(res, "paddy.csv"))
    worst = 0.0
    for r in rows:
        ex = 10.0 * 2.0 ** (-r["time(s)"] / 21600.0)
        worst = max(worst, abs(r["c1(mg/L)"] - ex) / ex)
    if worst > 1e-9:
        fail("tank concentration vs 10 x 2^(-t/6h): relative difference %.3e" % worst)
    ok("tank concentration = 10 x 2^(-t/6 h) (%d records, max relative difference %.1e)" % (len(rows), worst))
    m0 = 10.0 * 0.25 * 8000.0
    w = wq_closure(res, m0)
    last = w[-1]
    if not (last["out_edge_g"] > 0.0 and last["out_paddy_perc_g"] > 0.0 and last["decay_g"] > 0.0):
        fail("expected outflow over the open edges, percolation and decay of the substance")
    ok("substance left by the open edges %.1f g, with percolation %.1f g, decayed %.1f g"
       % (last["out_edge_g"], last["out_paddy_perc_g"], last["decay_g"]))


def check_wq_rain(res):
    """雨 2 mg/L、事前の湛水 0: タンクの濃度は 2 へ単調に近づく(通常の落水口は 48 h で相対 1e-3 以内)"""
    rows = read_csv(os.path.join(res, "paddy.csv"))
    for key in ("c1(mg/L)", "c2(mg/L)"):
        cs = [r[key] for r in rows]
        if any(cs[k + 1] < cs[k] - 1e-12 for k in range(len(cs) - 1)):
            fail("%s does not increase monotonically" % key)
        if max(cs) > 2.0 * (1.0 + 1e-3):
            fail("%s exceeds the rain concentration: %.9f" % (key, max(cs)))
    c1 = rows[-1]["c1(mg/L)"]
    if abs(c1 - 2.0) > 2.0e-3:
        fail("normal outlets: tank concentration %.9f is not within 1e-3 of the rain concentration 2" % c1)
    ok("tank concentrations rise monotonically toward 2 mg/L (after 48 h: normal %.6f, paddy dam %.6f mg/L)"
       % (c1, rows[-1]["c2(mg/L)"]))
    wq_closure(res, 0.0)           # 事前の湛水も地表も初めは 0 g(雨の物質だけが入る)


def check_wq_tw(res):
    """双方向の逆流: 地表の水だけが水田に入るので、タンクの濃度 = 地表の初めの濃度(初めの地表の質量 / 地表の水の
    量。畦畔より下の水は水田でない面積だけにあるので (1 − 0.6) × 0.15 × 8000 m3)。閉じた箱の質量は一定。
    初めの地表の質量は m_wq が wq_c0 × h(矩形の換算)で置くので、初めの濃度は wq_c0 × h / vh = 12.5 mg/L に
    なる(水質の初期濃度の既知の簡略化。ユーザーガイドの田んぼダムの章「水質との併用」)。検定はこの換算に
    よらないよう、初めの質量から濃度を求める"""
    w = read_csv(os.path.join(res, "wq.csv"))
    m0 = w[0]["mass_surface_g"]
    c0 = m0 / ((1.0 - 0.6) * 0.15 * 8000.0)
    rows = read_csv(os.path.join(res, "paddy.csv"))
    c1 = rows[-1]["c1(mg/L)"]
    if not rows[-1]["inflow(m3)"] > 0.0:
        fail("no backflow into the paddy tanks")
    if abs(c1 - c0) > 1.0e-6 * c0:
        fail("tank concentration %.12f differs from the initial surface concentration %.12f mg/L" % (c1, c0))
    ok("water entering the paddy tanks by backflow carries the surface concentration (tank %.9f, surface %.9f mg/L)"
       % (c1, c0))
    wq_closure(res, m0)


def check_wq_vs(res):
    """タンクのプールの沈降(wq_vs = 0.05 m/d だけ。閉じた箱で落水・雨・減水深・減衰なし): 種類ごとの濃度 =
    10 × (1 − vs·Δt/h)^n(n = t/Δt。m_wq の沈降の離散式 c·(1 − vs·Δt/h) の厳密解。h は種類 1 が 0.10 m、種類 2 が
    0.20 m)。連続の解 10 × exp(−vs·t/h) との差は時間の離散化の誤差 n·x²/2 = vs²·t·Δt/(2h²) に一致する。湛水深は
    変わらず、地表の物質は 0 のまま、沈降した量は wq.csv の settle_g に入る(質量の収支)"""
    vs = 0.05 / 86400.0
    dt = 2.0
    rows = read_csv(os.path.join(res, "paddy.csv"))
    for key, h in (("h1(mm)", 100.0), ("h2(mm)", 200.0)):
        worst = max(abs(r[key] - h) for r in rows) / h
        if worst > 1e-12:
            fail("%s changes (relative %.3e from %.1f mm): the tanks should neither drain nor fill" % (key, worst, h))
    last = rows[-1]
    for c, h in ((1, 0.10), (2, 0.20)):
        key = "c%d(mg/L)" % c
        x = vs * dt / h
        worst = 0.0
        for r in rows:
            ex = 10.0 * (1.0 - x) ** round(r["time(s)"] / dt)
            worst = max(worst, abs(r[key] - ex) / ex)
        if worst > 1e-10:
            fail("class %d: tank concentration vs 10 x (1 - vs dt/h)^n: relative difference %.3e" % (c, worst))
        t = last["time(s)"]
        dc = abs(last[key] - 10.0 * math.exp(-vs * t / h)) / (10.0 * math.exp(-vs * t / h))
        pred = vs * vs * t * dt / (2.0 * h * h)
        if abs(dc - pred) > 0.01 * pred:
            fail("class %d: difference from the continuous solution %.4e is not the time-discretisation error %.4e"
                 % (c, dc, pred))
        ok("class %d (h = %.2f m): tank concentration = 10 x (1 - vs dt/h)^n (max relative difference %.1e), "
           "%.6f mg/L after %.0f h; the continuous solution differs by %.3e = vs^2 t dt/(2h^2)"
           % (c, h, worst, last[key], t / 3600.0, dc))
    m0 = 10.0 * (0.5 * 0.10 + 0.5 * 0.20) * 8000.0
    w = wq_closure(res, m0)
    if max(abs(r["mass_surface_g"]) for r in w) > 0.0:
        fail("substance appeared on the surface (the tanks neither drain nor spill)")
    if not w[-1]["settle_g"] > 0.0:
        fail("no settling counted in settle_g")
    ok("settled %.4f g of %.1f g (counted in settle_g); the surface stays free of the substance"
       % (w[-1]["settle_g"], m0))


def check_wq_b(res):
    """B: 区画の事前の湛水 10 mg/L・雨 2 mg/L・減水深の持ち出し: 閉じた領域の質量の収支、区画の水の濃度は 2〜10"""
    rows = read_csv(os.path.join(res, "paddy.csv"))
    for r in rows:
        if not (2.0 - 1e-9 <= r["c1(mg/L)"] <= 10.0 + 1e-9):
            fail("plot water concentration %.9f outside 2..10 mg/L at t = %.0f s" % (r["c1(mg/L)"], r["time(s)"]))
    ok("plot water concentration stays within 2..10 mg/L (end %.4f mg/L)" % rows[-1]["c1(mg/L)"])
    w = wq_closure(res, 10.0 * 0.28 * 2500.0)
    if not w[-1]["out_paddy_perc_g"] > 0.0:
        fail("no substance left with the percolation")



# ---------------------------------------------------------------- 土砂(段 4b。§127.11)
def read_map(name):
    """data_paddy の整数・実数の分布(行 1 = j = 1)を (j − 1)·nx + (i − 1) の並びで返す"""
    with open(os.path.join("data_paddy", name)) as f:
        return [float(x) for line in f if line.strip() for x in line.split()]


def check_sed_tw(res):
    """双方向と浮遊砂: タンクへ入る水の浮遊砂を田面に積む。固相の保存(浮遊 + 河床の上昇 × (1 − λ) = 流し込んだ土砂)、
    水田のセルの河床の上昇 × (1 − λ) = paddy.csv の sed(+ 沈降の分)、水田のないセルは沈降の分しか上がらない"""
    nx, ny, area, lam = 10, 8, 100.0, 0.4
    vin = 0.002 * 1.0 * 7200.0                        # 流入の土砂(体積濃度 × 流量 × 時間)
    frac = read_map("frac_tw.txt")
    z0 = read_bil(os.path.join(res, "Z0000.bil"), nx, ny)
    z1 = read_bil(os.path.join(res, "Z0001.bil"), nx, ny)
    hs = read_bil(os.path.join(res, "Hs0001.bil"), nx, ny)
    dz = [z1[k] - z0[k] for k in range(nx * ny)]
    tot = sum(hs) * area + sum(dz) * area * (1.0 - lam)
    if abs(tot - vin) > 1e-6 * vin:
        fail("solid volume %.9f m3 (suspended + deposited) differs from the inflow %.6f m3" % (tot, vin))
    ok("solid volume conserved: suspended + deposited = %.9f m3 (inflow %.6f m3)" % (tot, vin))
    settle = max(abs(dz[k]) for k in range(nx * ny) if frac[k] <= 0.0)
    if settle > 1e-5:
        fail("the bed of a cell without paddy fields rose by %.3e m (only settling is expected)" % settle)
    dmin = min(dz[k] for k in range(nx * ny) if frac[k] > 0.0)
    if not dmin > 1e-4:
        fail("a paddy cell received no deposit (dz = %.3e m)" % dmin)
    ok("deposit only on paddy cells (paddy cells >= %.3e m; cells without paddy fields <= %.1e m = settling)"
       % (dmin, settle))
    npd = sum(1 for k in range(nx * ny) if frac[k] > 0.0)
    pad = sum(dz[k] for k in range(nx * ny) if frac[k] > 0.0) * area * (1.0 - lam)
    sed = read_csv(os.path.join(res, "paddy.csv"))[-1]["sed(m3)"]
    bound = 2.0 * settle * npd * area * (1.0 - lam) + 1e-6 * sed
    if not (sed - 1e-6 * sed <= pad <= sed + bound):
        fail("deposit on the paddy cells %.9f m3 differs from sed(m3) of paddy.csv %.9f m3 (settling bound %.1e)"
             % (pad, sed, bound))
    ok("deposit on the paddy cells %.6f m3 = sed(m3) %.6f m3 + settling (<= %.1e m3)" % (pad, sed, bound))


def check_b_sed(res):
    """区画の解像と掃流砂: 掃流砂は区画の畦畔・落水口のエッジを越えないので、区画ごとの河床の変化の合計は 0
    (区画の中の移動だけ)。掃流砂が区画の中で働いていることも確かめる"""
    nx, ny = 20, 20
    pid = [int(round(v)) for v in read_map("b_back_plot.txt")]
    z0 = read_bil(os.path.join(res, "Z0000.bil"), nx, ny)
    z1 = read_bil(os.path.join(res, "Z0001.bil"), nx, ny)
    for p in sorted(set(v for v in pid if v > 0)):
        cells = [k for k in range(nx * ny) if pid[k] == p]
        net = sum(z1[k] - z0[k] for k in cells)
        moved = sum(abs(z1[k] - z0[k]) for k in cells)
        if not moved > 1e-3:
            fail("plot %d: the bed load did not act inside the plot (sum |dz| = %.3e m)" % (p, moved))
        if abs(net) > 1e-6 * moved + 1e-9:
            fail("plot %d: the bed of the plot changed by %.3e m in total (sum |dz| %.3e m): bed load crossed "
                 "the levees" % (p, net, moved))
        ok("plot %d: bed load moved inside the plot (sum |dz| = %.3e m) with no net change (%.1e m)"
           % (p, moved, net))


# ---------------------------------------------------------------- 集水面積率(段 4c。§127.13)
def check_catch(res, tw):
    """param_catch.txt: a = 0.5・c = 0.3・雨 20 mm/h の閉じた平らな箱。落水・減水深なし。
    種類ごとの平均湛水深 = (a + c)/a × 雨(集水面積の雨は 3 × 3 の近傍の水田へ配るので、箱の縁のセルの湛水深は
    平均と違う。セルごとの厳密解は catch_sp。§127.15)、地表の水(セル面積あたり)= (1 − a − c) × 雨、地表の水深 H は片方向でセル全面
    (0.2 × 雨)、双方向で水田でない面積だけ(0.2 × 雨 / (1 − a))"""
    a, c, area = 0.5, 0.3, 8000.0
    rate = 20.0 / 3.6e6                          # m/s
    rows = read_csv(os.path.join(res, "paddy.csv"))
    worst = 0.0
    for r in rows:
        p = rate * r["time(s)"]                  # それまでの雨 (m)
        for k in ("h1(mm)", "h2(mm)"):
            worst = max(worst, abs(r[k] - (a + c) / a * p * 1e3) / ((a + c) / a * p * 1e3))
        worst = max(worst, abs(r["rain(m3)"] - a * p * area) / (a * p * area))
        worst = max(worst, abs(r["catch(m3)"] - c * p * area) / (c * p * area))
        if r["outflow(m3)"] != 0.0 or r["spill(m3)"] != 0.0 or r["inflow(m3)"] != 0.0 or r["levee_in(m3)"] != 0.0:
            fail("water moved between the tanks and the surface at t = %.0f s (only rain is expected)" % r["time(s)"])
    if worst > 1e-9:
        fail("class mean ponding depth or ledger differs from the exact solution by %.3e (relative)" % worst)
    ok("class mean ponding depth = (a + c)/a x rain, rain = a x rain x area, catch = c x rain x area (%d records, max relative "
       "difference %.1e)" % (len(rows), worst))
    # 地表の水: Log の S(地表 + タンク。領域平均 m)からタンクの貯留を引く
    last = rows[-1]
    p = rate * last["time(s)"]
    s = log_s(res)[-1]
    surf = s - (last["store1(m3)"] + last["store2(m3)"]) / area
    if abs(surf - (1.0 - a - c) * p) > 1e-12:
        fail("surface water %.15f m differs from (1 - a - c) x rain = %.15f m" % (surf, (1.0 - a - c) * p))
    if abs(s - p) > 1e-12:
        fail("S = %.15f m differs from the rain %.15f m (closed box)" % (s, p))
    hexp = (1.0 - a - c) * p / ((1.0 - a) if tw else 1.0)
    hv = read_bil(os.path.join(res, "H0001.bil"), 10, 8)
    e = max(abs(x - hexp) for x in hv)
    if e > 1e-7:
        fail("surface depth differs from %.6f m by %.3e m" % (hexp, e))
    ok("surface water = (1 - a - c) x rain (%.6f m per cell area), S = rain (closed box), surface depth %.6f m (%s)"
       % (surf, hexp, "non-paddy area only" if tw else "whole cell"))
    check_ledger(rows)


def check_catch_sp(res, tw):
    """param_catch_sp.txt: 面積率・取組率・集水面積率が場所で違う閉じた平らな箱(雨 20 mm/h を 2 h、事前の湛水 0.01 m、
    落水・減水深なし)。雨の降るセル m の集水面積の雨 c_m × 雨を、m を中心とする 3 × 3 のセル(領域の外は除く)の水田へ
    面積の比で配る(§127.15): 水田のセル n のタンクの水深 = 0.01 + 雨 × (1 + Σ_m c_m / A_m)、A_m = Σ_{3 × 3(m)} a。
    雨の物質(2 mg/L)も水と同じ行き先なので、種類ごとの平均濃度 = 2 × (受けた水) / (事前の湛水 + 受けた水)"""
    nx, ny, acell, h0, crain = 10, 8, 100.0, 0.01, 2.0
    rate = 20.0 / 3.6e6                          # m/s
    fa, ad, fc = read_map("frac_sp.txt"), read_map("adopt_sp.txt"), read_map("catch_sp.txt")
    f1 = [x * (1.0 - r) for x, r in zip(fa, ad)]
    f2 = [x * r for x, r in zip(fa, ad)]

    def nb(i, j):
        return [(ii, jj) for jj in range(max(j - 1, 0), min(j + 1, ny - 1) + 1)
                for ii in range(max(i - 1, 0), min(i + 1, nx - 1) + 1)]
    anb = [sum(fa[jj * nx + ii] for ii, jj in nb(i, j)) for j in range(ny) for i in range(nx)]
    gain = [0.0] * (nx * ny)                     # 雨 1 m あたりのタンクの水深の増え(1 + Σ c_m / A_m)
    for j in range(ny):
        for i in range(nx):
            n = j * nx + i
            if fa[n] > 0.0:
                gain[n] = 1.0 + sum(fc[jj * nx + ii] / anb[jj * nx + ii] for ii, jj in nb(i, j) if fc[jj * nx + ii] > 0.0)
    a1, a2, csum = sum(f1), sum(f2), sum(fc)
    g1 = sum(f * g for f, g in zip(f1, gain)) / a1
    g2 = sum(f * g for f, g in zip(f2, gain)) / a2
    if abs(a1 * g1 + a2 * g2 - (a1 + a2 + csum)) > 1e-12 * (a1 + a2 + csum):
        fail("test setup: the spread water is not conserved in the reference solution")
    rows = read_csv(os.path.join(res, "paddy.csv"))
    worst = 0.0
    for r in rows:
        p = rate * r["time(s)"]
        for key, gk in (("h1(mm)", g1), ("h2(mm)", g2)):
            ex = (h0 + gk * p) * 1e3
            worst = max(worst, abs(r[key] - ex) / ex)
        if p > 0.0:
            worst = max(worst, abs(r["rain(m3)"] - (a1 + a2) * p * acell) / ((a1 + a2) * p * acell))
            worst = max(worst, abs(r["catch(m3)"] - csum * p * acell) / (csum * p * acell))
            for key, gk in (("c1(mg/L)", g1), ("c2(mg/L)", g2)):
                ex = crain * gk * p / (h0 + gk * p)
                worst = max(worst, abs(r[key] - ex) / ex)
        if r["outflow(m3)"] != 0.0 or r["spill(m3)"] != 0.0 or r["inflow(m3)"] != 0.0 or r["levee_in(m3)"] != 0.0:
            fail("water moved between the tanks and the surface at t = %.0f s (only rain is expected)" % r["time(s)"])
    if worst > 1e-9:
        fail("class mean ponding depth, concentration or ledger differs from the exact solution by %.3e (relative)"
             % worst)
    ok("class mean ponding depth (%.6f, %.6f x rain + 0.01 m), concentration, rain and catch match the exact solution "
       "(%d records, max relative difference %.1e)" % (g1, g2, len(rows), worst))
    # セルごとのタンクの水深(単精度の出力。両方の種類が同じ水深)
    p = rate * rows[-1]["time(s)"]
    e = 0.0
    for name, fk in (("Hpn0001.bil", f1), ("Hpd0001.bil", f2)):
        hv = read_bil(os.path.join(res, name), nx, ny)
        for n in range(nx * ny):
            if fk[n] > 0.0:
                ex = h0 + gain[n] * p
                e = max(e, abs(hv[n] - ex) / ex)
    if e > 2e-7:
        fail("tank depth of a cell differs from 0.01 + rain x (1 + sum c/A) by %.3e (relative)" % e)
    ok("tank depth of every paddy cell = 0.01 m + rain x (1 + sum of c/A over the 3 x 3 neighbourhood), "
       "%.4f to %.4f m (max relative difference %.1e, single-precision output)"
       % (min(h0 + g * p for g, x in zip(gain, fa) if x > 0.0), max(h0 + g * p for g in gain), e))
    # 地表の水: Log の S(地表 + タンク。領域平均 m)から水田の貯留を引く
    last = rows[-1]
    s = log_s(res)[-1]
    area = acell * nx * ny
    surf = s - (last["store1(m3)"] + last["store2(m3)"]) / area
    sexp = sum(1.0 - x - c for x, c in zip(fa, fc)) * p / (nx * ny)
    sdep = h0 * (a1 + a2) / (nx * ny)
    if abs(surf - sexp) > 1e-12:
        fail("surface water %.15f m differs from the mean of (1 - a - c) x rain = %.15f m" % (surf, sexp))
    if abs(s - (p + sdep)) > 1e-12:
        fail("S = %.15f m differs from rain + initial ponding %.15f m (closed box)" % (s, p + sdep))
    ok("surface water = mean of (1 - a - c) x rain (%.6f m per cell area), S = rain + initial ponding (closed box, %s)"
       % (surf, "two-way" if tw else "one-way"))
    check_ledger(rows)
    wq_closure(res, 0.0)


def check_catch_zero(res0, res1):
    """集水面積率 0 の分布を与えた計算は、与えない計算とビット一致(paddy.csv は末尾の catch 列を除く)"""
    for f in ("Log.txt", "H9998.txt", "Hpn9998.txt", "Hpd9998.txt"):
        p0, p1 = os.path.join(res0, f), os.path.join(res1, f)
        if not os.path.exists(p0):
            continue
        with open(p0, "rb") as a, open(p1, "rb") as b:
            if a.read() != b.read():
                fail("%s differs between no catchment and a catchment fraction of 0" % f)
        ok("%s identical with a catchment fraction of 0" % f)
    with open(os.path.join(res0, "paddy.csv")) as a, open(os.path.join(res1, "paddy.csv")) as b:
        l0, l1 = a.read().splitlines(), b.read().splitlines()
    if len(l0) != len(l1):
        fail("paddy.csv: %d and %d lines" % (len(l0), len(l1)))
    for x, y in zip(l0, l1):
        head, _, last = y.rpartition(",")
        if x != head:
            fail("paddy.csv differs apart from the catch column:\n  %s\n  %s" % (x, y))
        if last.strip() not in ("catch(m3)",) and float(last) != 0.0:
            fail("catch column is not 0: %s" % last)
    ok("paddy.csv identical apart from the added catch column (all 0)")


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
    elif cmd == "restart_b":
        check_restart(sys.argv[2], sys.argv[3], files=("H9998.txt",))
    elif cmd == "restart_sed":
        check_restart(sys.argv[2], sys.argv[3], files=("H9998.txt", "Hpn9998.txt", "Hpd9998.txt", "Z9998.bil",
                                                       "Hs9998.bil"))
    elif cmd == "restart_wq":
        check_restart(sys.argv[2], sys.argv[3], files=("H9998.txt", "Hpn9998.txt", "C9998.txt"))
        a = read_csv(os.path.join(sys.argv[2], "paddy.csv"))[-1]["c1(mg/L)"]
        b = read_csv(os.path.join(sys.argv[3], "paddy.csv"))[-1]["c1(mg/L)"]
        if a != b:
            fail("tank concentration at the end differs: %.17g vs %.17g" % (a, b))
        ok("tank concentration at the end identical (%.12f mg/L)" % a)
    elif cmd == "b_drain":
        check_b_drain(sys.argv[2])
    elif cmd == "b_tight":
        check_b_tight(sys.argv[2])
    elif cmd == "b_over":
        check_b_over(sys.argv[2])
    elif cmd == "b_back":
        check_b_even(sys.argv[2], "b_back_e.txt", 0.20, False)
    elif cmd == "b_ext":
        check_b_even(sys.argv[2], "b_ext_e.txt", 0.40, True)
    elif cmd == "b_bank":
        check_b_bank(sys.argv[2])
    elif cmd == "b_chain":
        check_b_chain(sys.argv[2])
    elif cmd == "wq_a":
        check_wq_a(sys.argv[2])
    elif cmd == "wq_rain":
        check_wq_rain(sys.argv[2])
    elif cmd == "wq_tw":
        check_wq_tw(sys.argv[2])
    elif cmd == "wq_b":
        check_wq_b(sys.argv[2])
    elif cmd == "wq_vs":
        check_wq_vs(sys.argv[2])
    elif cmd == "sed_tw":
        check_sed_tw(sys.argv[2])
    elif cmd == "b_sed":
        check_b_sed(sys.argv[2])
    elif cmd == "catch":
        check_catch(sys.argv[2], False)
    elif cmd == "catch_tw":
        check_catch(sys.argv[2], True)
    elif cmd == "catch_sp":
        check_catch_sp(sys.argv[2], False)
    elif cmd == "catch_sp_tw":
        check_catch_sp(sys.argv[2], True)
    elif cmd == "catch_zero":
        check_catch_zero(sys.argv[2], sys.argv[3])
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
