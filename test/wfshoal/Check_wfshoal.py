#!/usr/bin/env python3
"""wfshoal: 沿岸の波浪場(fn_wavefield。developer.md §90)の海浜断面の検定

Python 標準ライブラリのみ。使い方:
  python3 Check_wfshoal.py base   result                 # 基本(沖の波の時系列・斜め入射の不規則波)
  python3 Check_wfshoal.py shoal  result_shoal           # 浅水変形と飽和砕波(規則波)
  python3 Check_wfshoal.py refr   result_refr [result_refr80]
                                                         # 屈折(Snell の法則)と方向ビンの 1 次収束
  python3 Check_wfshoal.py brk    result_brk             # 砕波(Baldock ら 1998)
  python3 Check_wfshoal.py brkjb  result_brkjb           # 砕波(Janssen & Battjes 2007)+ 底面摩擦
  python3 Check_wfshoal.py unst   result_unst result_brk # 非定常: 前線の到達・定常解・台帳(累積)
  python3 Check_wfshoal.py rt     result_unst result_rt2 # 再開の継続で台帳の CSV が通し計算と一致

地形は make_z.py と同じ一様勾配 1/80 の海浜(西 = 沖、x = 1100 m が汀線、水位 0)。
波高の分布は bil(単精度)で読む。岸沿い(8 行)は厳密に一様でなければならない。

独立に組み立てる参照解:
  - 分散関係 σ² = g k tanh(kh) を倍精度の Newton 法で解き、c = σ/k、
    c_g = (c/2)(1 + 2kh/sinh 2kh)
  - 直角入射・岸沿い一様の定常では、2 リンク分解の風上法は軸方向のリンクだけで
    運ぶので、離散の定常解は漸化式 c_g,i E_i + Δx D(E_i) = c_g,i−1 E_i−1 と
    上限 E_i <= E_max(h_i) で決まる(境界のセル i = 1 の上流は沖の波 E_0 を
    セル 1 の群速度で運ぶ仮想の送り手)。D は文献の形(XBeach の
    マニュアルの式)から本スクリプトで独立に書いた砕波・摩擦の散逸
  - 屈折は Snell の法則 sin α/c = sin α_0/c_0、波高 H = H_0 K_s K_r
"""
import csv
import math
import struct
import sys

NX, NY, DX = 120, 8, 10.0
XS, SLOPE = 1100.0, 1.0 / 80.0
G = 9.8           # 重力加速度(既定 p%gg)
RHO = 1025.0      # 海水の密度(m_wavefield)
HMIN = 0.1        # 波浪セルの最小水深(既定)
GAMMA, ALPHA, GAMMAX = 0.78, 1.0, 0.6

failed = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        failed.append(msg)


def depth(i):
    """セル i(1 始まり)の静水深(水位 0)"""
    x = (i - 0.5) * DX
    return max(0.0, (XS - x) * SLOPE)


def read_bil(path):
    with open(path, "rb") as f:
        data = f.read()
    v = struct.unpack("<%df" % (NX * NY), data)
    return [list(v[j * NX:(j + 1) * NX]) for j in range(NY)]


def read_csv(path):
    with open(path, newline="") as f:
        rows = list(csv.reader(f))
    head = [h.strip() for h in rows[0]]
    return [dict(zip(head, [c.strip() for c in r])) for r in rows[1:] if r]


def wavenumber(sig, h):
    y = sig * sig * h / G
    kh = math.sqrt(y) if y < 1.0 else y
    for _ in range(100):
        t = math.tanh(kh)
        f = kh * t - y
        df = t + kh * (1.0 - t * t)
        dkh = f / df
        kh -= dkh
        if abs(dkh) < 1e-15 * kh:
            break
    return kh / h


def celerity(sig, h):
    k = wavenumber(sig, h)
    kh = k * h
    n = 0.5 * (1.0 + 2.0 * kh / math.sinh(2.0 * kh))
    return sig / k, n * sig / k, k


def wave_cells():
    """波浪セル(h > hmin)の列番号 1..iw(沖から連続)"""
    cells = [i for i in range(1, NX + 1) if depth(i) > HMIN]
    assert cells == list(range(1, len(cells) + 1))
    return cells


def uniform_rows(a, name):
    same = all(a[j] == a[0] for j in range(1, NY))
    check(same, "%s is exactly uniform alongshore (8 rows bit-identical)" % name)


# --- 散逸(文献の形を独立に記述。XBeach マニュアルの式) ---
def d_baldock(e, k, h, fr):
    """Baldock ら(1998): D = α/4 ρ g f Q_b (H_b² + H_rms²)、Q_b = exp(−H_b²/H_rms²)、
    H_b = 0.88/k tanh(γ k h/0.88)"""
    hrms = math.sqrt(8.0 * e / (RHO * G))
    if hrms <= 0.0:
        return 0.0
    hb = 0.88 / k * math.tanh(GAMMA * k * h / 0.88)
    qb = math.exp(-(hb / hrms) ** 2)
    return 0.25 * ALPHA * RHO * G * fr * qb * (hb * hb + hrms * hrms)


def d_janssen(e, k, h, fr):
    """Janssen & Battjes(2007): D = 3√π/16 α ρ g f H_rms³/h Q_b、
    Q_b = 1 + 4/(3√π)(R³ + 3R/2) exp(−R²) − erf(R)、R = H_b/H_rms"""
    hrms = math.sqrt(8.0 * e / (RHO * G))
    if hrms <= 0.0:
        return 0.0
    hb = 0.88 / k * math.tanh(GAMMA * k * h / 0.88)
    r = hb / hrms
    qb = 1.0 + 4.0 / (3.0 * math.sqrt(math.pi)) * (r ** 3 + 1.5 * r) * math.exp(-r * r) - math.erf(r)
    qb = max(qb, 0.0)
    return 3.0 * math.sqrt(math.pi) / 16.0 * ALPHA * RHO * G * fr * hrms ** 3 / h * qb


def d_friction(e, k, h, sig, fw, c):
    """底面摩擦 D_f = c ρ f_w u_orb³、u_orb = π H_rms/(T sinh kh)(c = 0.28 不規則・0.21 規則。
    Guza & Thornton 1985 の係数。XBeach のマニュアル)"""
    hrms = math.sqrt(8.0 * e / (RHO * G))
    uorb = math.pi * hrms / (2.0 * math.pi / sig * math.sinh(k * h))
    return c * RHO * fw * uorb ** 3


def solve_cell(flux_up, cg, dfun):
    """c_g E + Δx D(E) = flux_up を E について解く(左辺は E の単調増加。二分法)"""
    lo, hi = 0.0, flux_up / cg
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if cg * mid + DX * dfun(mid) > flux_up:
            hi = mid
        else:
            lo = mid
        if hi - lo <= 1e-15 * max(hi, 1e-300):
            break
    return 0.5 * (lo + hi)


def recursion(e0, sig, dfun_of_cell, emax_of_cell):
    """直角入射の離散定常解(漸化式)。戻り値 E_i(i = 1..iw)と群速度・波数"""
    cells = wave_cells()
    es, cgs, ks = [], [], []
    flux = None
    for i in cells:
        h = depth(i)
        _, cg, k = celerity(sig, h)
        if flux is None:
            flux = cg * e0                      # 仮想の送り手はセル 1 の群速度で運ぶ
        e = solve_cell(flux, cg, lambda ee: dfun_of_cell(ee, k, h))
        e = min(e, emax_of_cell(h))
        es.append(e)
        cgs.append(cg)
        ks.append(k)
        flux = cg * e
    return cells, es, cgs, ks


def ledger_closed(res, tol_rel):
    rows = read_csv(res + "/wavefield.csv")
    worst = 0.0
    for r in rows:
        inw = float(r["in_W"])
        if inw > 0.0:
            worst = max(worst, abs(float(r["imbalance_W"])) / inw)
    check(worst < tol_rel, "ledger closes: max |imbalance|/in = %.2e < %.0e" % (worst, tol_rel))
    return rows


# ======================================================================
def case_shoal(res):
    print("== shoal (%s): shoaling and saturated breaking of regular waves" % res)
    wh = read_bil(res + "/Wh0001.bil")
    uniform_rows(wh, "Wh")
    sig = 2.0 * math.pi / 8.0
    h0 = 1.0
    e0 = RHO * G * h0 * h0 / 8.0
    cells, es, cgs, _ = recursion(e0, sig, lambda e, k, h: 0.0,
                                  lambda h: RHO * G * (GAMMA * h) ** 2 / 8.0)
    worst = 0.0
    nsat = 0
    worst_th = 0.0
    for n, i in enumerate(cells):
        href = math.sqrt(8.0 * es[n] / (RHO * G))
        worst = max(worst, abs(wh[0][i - 1] - href) / href)
        # 線形理論: 飽和していなければ H = H0 (c_g1/c_g)^{1/2}、飽和なら γh
        hth = h0 * math.sqrt(cgs[0] / cgs[n])
        if hth >= GAMMA * depth(i):
            nsat += 1
            hth = GAMMA * depth(i)
        worst_th = max(worst_th, abs(wh[0][i - 1] - hth) / hth)
    check(worst < 2e-6, "H equals the discrete steady solution (c_g E conserved, capped at gamma h):"
          " max rel diff %.2e" % worst)
    check(worst_th < 2e-6, "H equals linear shoaling H0 (cg1/cg)^1/2 offshore and gamma h in the surf"
          " zone (%d saturated cells): max rel diff %.2e" % (nsat, worst_th))
    check(nsat >= 10, "the surf zone is resolved by >= 10 saturated cells (%d)" % nsat)
    for i in range(cells[-1] + 1, NX + 1):
        if wh[0][i - 1] != 0.0:
            check(False, "non-wave cell %d (h = %.4f m <= wf_hmin) has H = 0" % (i, depth(i)))
            break
    else:
        check(True, "cells with h <= wf_hmin (and the dry beach) carry no waves")
    ledger_closed(res, 1e-9)


def case_refr(res, res80=None):
    print("== refr (%s): refraction on parallel depth contours (Snell's law)" % res)
    errs = {}
    for r, nth in ((res, 40), (res80, 80)):
        if r is None:
            continue
        wh = read_bil(r + "/Wh0001.bil")
        wa = read_bil(r + "/Wa0001.bil")
        uniform_rows(wh, "Wh (N_theta = %d)" % nth)
        uniform_rows(wa, "Wa (N_theta = %d)" % nth)
        sig = 2.0 * math.pi / 8.0
        h0, a0 = 0.2, math.radians(30.0)
        c1, cg1, _ = celerity(sig, depth(1))
        da = dh = 0.0
        da_end = 0.0
        for i in wave_cells():
            h = depth(i)
            if h < 1.0:
                continue
            c, cg, _ = celerity(sig, h)
            a = math.asin(math.sin(a0) * c / c1)
            hth = h0 * math.sqrt(cg1 / cg) * math.sqrt(math.cos(a0) / math.cos(a))
            dd = wa[0][i - 1] - math.degrees(a)
            da = max(da, abs(dd))
            dh = max(dh, abs(wh[0][i - 1] - hth) / hth)
            da_end = dd                     # 最も浅い比較点(h ≈ 1 m)の差
        errs[nth] = (da, dh, da_end)
        print("     N_theta = %d: max |dir - Snell| = %.3f deg (at h ~ 1 m: %+.3f), max rel H err = %.4f"
              % (nth, da, da_end, dh))
    da, dh, _ = errs[40]
    check(da < 2.0, "N_theta = 40: mean direction follows Snell's law within 2 deg for h >= 1 m (%.3f)" % da)
    check(dh < 0.01, "N_theta = 40: H follows H0 Ks Kr within 1%% for h >= 1 m (%.4f)" % dh)
    if 80 in errs:
        r_dir = errs[80][0] / errs[40][0]
        r_h = errs[80][1] / errs[40][1]
        check(r_dir < 0.65, "N_theta = 80 halves the direction error (first-order convergence): ratio %.3f" % r_dir)
        check(r_h < 0.65, "N_theta = 80 halves the height error: ratio %.3f" % r_h)
    ledger_closed(res, 1e-6)


def case_brk(res, jb):
    title = "Janssen & Battjes 2007 + bottom friction" if jb else "Baldock et al. 1998"
    print("== %s (%s): random-wave breaking, %s" % ("brkjb" if jb else "brk", res, title))
    wh = read_bil(res + "/Wh0001.bil")
    wb = read_bil(res + "/Wb0001.bil")
    wu = read_bil(res + "/Wu0001.bil")
    uniform_rows(wh, "Wh")
    sig = 2.0 * math.pi / 8.0
    fr = 1.0 / 8.0
    hm0 = 1.5
    e0 = RHO * G * hm0 * hm0 / 16.0
    fw = 0.02 if jb else 0.0
    dbr = d_janssen if jb else d_baldock

    def dtot(e, k, h):
        d = dbr(e, k, h, fr)
        if fw > 0.0:
            d += d_friction(e, k, h, sig, fw, 0.28)
        return d

    emax = lambda h: RHO * G * (GAMMAX * h) ** 2 / 8.0
    cells, es, cgs, ks = recursion(e0, sig, dtot, emax)
    worst = worst_b = worst_u = 0.0
    ncap = 0
    for n, i in enumerate(cells):
        h = depth(i)
        hm = math.sqrt(2.0) * math.sqrt(8.0 * es[n] / (RHO * G))
        worst = max(worst, abs(wh[0][i - 1] - hm) / hm)
        if es[n] >= emax(h) * (1.0 - 1e-12):
            ncap += 1
        db = dbr(es[n], ks[n], h, fr)
        if db > 1.0:
            worst_b = max(worst_b, abs(wb[0][i - 1] - db) / db)
        hrms = math.sqrt(8.0 * es[n] / (RHO * G))
        ub = hrms * sig / (2.0 * math.sqrt(2.0) * math.sinh(ks[n] * h))
        worst_u = max(worst_u, abs(wu[0][i - 1] - ub) / ub)
    check(worst < 1e-5, "H equals the discrete steady solution (independent dissipation formula,"
          " cap H_rms <= %.1f h at %d cells): max rel diff %.2e" % (GAMMAX, ncap, worst))
    check(worst_b < 1e-5, "breaking dissipation Wb equals D_w(E) where D_w > 1 W/m2: max rel diff %.2e"
          % worst_b)
    check(worst_u < 1e-5, "orbital velocity Wu equals H_rms sigma/(2 sqrt2 sinh kh): max rel diff %.2e"
          % worst_u)

    # 細かい刻み(Δx/100)の RK4 で求積したエネルギー式 d(E c_g)/dx = −D(E) との差
    # (離散化は 1 次の後退 Euler なので差は Δx の 1 次。情報として表示し、粗い判定)
    def rhs(x, f):
        h = (XS - x) * SLOPE
        _, cg, k = celerity(sig, h)
        e = max(f / cg, 0.0)
        return -dtot(e, k, h)

    x = 0.5 * DX
    f = cgs[0] * e0
    worst_ode = 0.0
    sub = 100
    step = DX / sub
    for n, i in enumerate(cells):
        xi = (i - 0.5) * DX
        while x < xi - 1e-9:
            k1 = rhs(x, f)
            k2 = rhs(x + step / 2, f + step / 2 * k1)
            k3 = rhs(x + step / 2, f + step / 2 * k2)
            k4 = rhs(x + step, f + step * k3)
            f = f + step / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
            x += step
        h = depth(i)
        _, cg, _ = celerity(sig, h)
        e = min(f / cg, emax(h))
        f = cg * e
        hm_ode = math.sqrt(2.0) * math.sqrt(8.0 * e / (RHO * G))
        worst_ode = max(worst_ode, abs(wh[0][i - 1] - hm_ode) / hm0)
    check(worst_ode < 0.02, "H is within 2%% of the energy balance integrated with dx/100 (first-order"
          " upwind in x; %.4f relative to H_m0,0)" % worst_ode)
    rows = ledger_closed(res, 1e-8)
    r = rows[-1]
    check(float(r["out_W"]) == 0.0 and float(r["limit_W"]) > 0.0,
          "no wave energy leaves through the lateral sides; the cap removes energy (limit_W > 0)")


def case_unst(res, res_brk):
    print("== unst (%s): unsteady mode (front, steady state, cumulative ledger)" % res)
    sig = 2.0 * math.pi / 8.0
    # 前線の到達: t = 60 s(出力 0001)で E/E_steady = 0.5 の位置 ~ ∫dx/c_g = 60 s の位置
    wh1 = read_bil(res + "/Wh0001.bil")
    whs = read_bil(res_brk + "/Wh0001.bil")
    cells = wave_cells()
    xf = None
    for i in cells:
        rat = (wh1[0][i - 1] / whs[0][i - 1]) ** 2
        if rat < 0.5:
            # 直前のセルとの線形補間
            rp = (wh1[0][i - 2] / whs[0][i - 2]) ** 2
            xf = (i - 1.5) * DX + DX * (rp - 0.5) / (rp - rat)
            break
    t = 0.0
    x = 0.0
    while t < 60.0:
        _, cg, _ = celerity(sig, (XS - x) * SLOPE)
        x += cg * 0.01
        t += 0.01
    check(xf is not None and abs(xf - x) < 2.0 * DX,
          "the energy front (E/E_steady = 0.5) at t = 60 s is at x = %.1f m; the group-velocity travel"
          " distance is %.1f m (within 2 cells)" % (xf if xf is not None else -1.0, x))
    whe = read_bil(res + "/Wh9998.bil")
    worst = max(abs(whe[0][i - 1] - whs[0][i - 1]) / whs[0][i - 1] for i in cells)
    check(worst < 1e-5, "the unsteady run reaches the quasi-steady solution (same discrete steady state):"
          " max rel diff %.2e" % worst)
    rows = read_csv(res + "/wavefield.csv")
    worst = 0.0
    for r in rows:
        inj = float(r["in_J"])
        if inj > 0.0:
            worst = max(worst, abs(float(r["imbalance_J"])) / inj)
    check(worst < 1e-9, "cumulative ledger closes: max |storage change - net input|/in = %.2e" % worst)


def case_rt(res_all, res_rt2):
    print("== rt (%s vs %s): ledger rows after the restart continue the straight run" % (res_rt2, res_all))
    a = {r["t_s"]: r for r in read_csv(res_all + "/wavefield.csv")}
    b = read_csv(res_rt2 + "/wavefield.csv")
    check(len(b) > 0, "the continuation writes ledger rows (%d)" % len(b))
    worst = 0.0
    for r in b:
        ra = a.get(r["t_s"])
        if ra is None:
            check(False, "time %s of the continuation is in the straight run" % r["t_s"])
            return
        for key in ("in_J", "out_J", "absorbed_J", "breaking_J", "limit_J", "storage_J", "storage0_J"):
            va, vb = float(ra[key]), float(r[key])
            if va != 0.0:
                worst = max(worst, abs(va - vb) / abs(va))
    check(worst < 1e-12, "cumulative ledger and storage of the continuation equal the straight run"
          " (max rel diff %.1e; the restart re-associates the row sums)" % worst)


def case_base(res):
    print("== base (%s): offshore wave series, oblique random waves" % res)
    rows = read_csv(res + "/wavefield.csv")
    # 沖の波の時系列(分 → 秒)の線形補間。進行方向は短い向き(340° → 20° は 0° をまたぐ)
    table = [(0.0, 1.0, 8.0, 340.0, 20.0), (1200.0, 1.5, 9.0, 20.0, 15.0), (2400.0, 1.5, 9.0, 20.0, 15.0)]

    def interp(t):
        for k in range(len(table) - 1):
            t1, t2 = table[k][0], table[k + 1][0]
            if t <= t2:
                w = (t - t1) / (t2 - t1)
                a, b = table[k], table[k + 1]
                dd = (b[3] - a[3] + 540.0) % 360.0 - 180.0
                return (a[1] + w * (b[1] - a[1]), a[2] + w * (b[2] - a[2]), (a[3] + w * dd) % 360.0)
        return table[-1][1:4]

    ts = [float(r["t_s"]) for r in rows]
    check(ts == [0.0, 600.0, 1200.0, 1800.0], "the quasi-steady field is solved at t = 0 and every"
          " dt_wave = 600 s (%s)" % ts)
    worst = 0.0
    for r in rows:
        h, t, d = interp(float(r["t_s"]))
        dd = abs((float(r["dir_bc"]) - d + 180.0) % 360.0 - 180.0)
        worst = max(worst, abs(float(r["H_bc"]) - h), abs(float(r["T_bc"]) - t), dd)
    check(worst < 1e-4, "offshore H, T and direction follow the series (direction interpolated the short"
          " way across 0 deg): max diff %.1e" % worst)
    check(all(int(r["iter"]) >= 1 and float(r["residual"]) < 1e-4 for r in rows),
          "every update converged below wf_tol")
    wh = read_bil(res + "/Wh0001.bil")
    wu = read_bil(res + "/Wu0001.bil")
    uniform_rows(wh, "Wh")
    uniform_rows(wu, "Wu")
    sig = 2.0 * math.pi / 9.0
    worst = 0.0
    for i in wave_cells():
        h = depth(i)
        _, _, k = celerity(sig, h)
        hrms = wh[0][i - 1] / math.sqrt(2.0)
        ub = hrms * sig / (2.0 * math.sqrt(2.0) * math.sinh(k * h))
        if ub > 0.0:
            worst = max(worst, abs(wu[0][i - 1] - ub) / ub)
    check(worst < 1e-5, "Wu = H_rms sigma/(2 sqrt2 sinh kh) with the current period: max rel diff %.1e" % worst)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    kind = sys.argv[1]
    if kind == "base":
        case_base(sys.argv[2])
    elif kind == "shoal":
        case_shoal(sys.argv[2])
    elif kind == "refr":
        case_refr(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    elif kind == "brk":
        case_brk(sys.argv[2], False)
    elif kind == "brkjb":
        case_brk(sys.argv[2], True)
    elif kind == "unst":
        case_unst(sys.argv[2], sys.argv[3])
    elif kind == "rt":
        case_rt(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)
        sys.exit(2)
    if failed:
        print("FAIL: %d check(s) failed" % len(failed))
        sys.exit(1)
    print("PASS")


if __name__ == "__main__":
    main()
