#!/usr/bin/env python3
"""wfsed: 沿岸の波浪場による土砂の攪拌と輸送(段 W4。fn_geomorph の f_wfsed。developer.md §88)の検定

Python 標準ライブラリのみ。使い方:
  python3 Check_wfsed.py stir   result_stir save_stir   # 攪拌: 浮遊砂の平衡濃度と土砂の保存(流れなし)
  python3 Check_wfsed.py bed    result_bed              # 掃流砂: 一様な流れ + 斜めの波
  python3 Check_wfsed.py beach  result                  # 海浜の沿岸漂砂(基本 param.txt)
  python3 Check_wfsed.py closed save_closed             # 閉じた海盆の土砂の保存
  python3 Check_wfsed.py asym   result                  # 岸向きの輸送速度 u_a(段 W5)
  python3 Check_wfsed.py shore  result_storm result_calm # 高波浪の侵食と低波浪の回復(段 W5)
  python3 Check_wfsed.py turb   result_turb result      # 砕波の乱れによる攪拌(f_wfsed_turb)

分布は bil(単精度)の最終出力(9998)、保存則は save の state.dat(倍精度)で読む。y の成分
(v・Qby・Qsy)は流れの出力と同じ規約(行の増える向き = 南が正)で、北向きは負。

独立に組み立てる参照(モデルの出力した流速・水深・軌道流速 u_rms・平均波向から):
  - 軌道流速の振幅 u_w = √2 u_rms、軌道の振幅 A = u_w/ω(流れの波への作用なし = σ = ω)
  - 波の摩擦係数 f_w = min(1.39 (A/z0)^−0.52, 0.3)、z0 = d50/12(Soulsby 1997 式 62a)
  - τ*_w = ½ f_w u_w²/(s g d)、τ*_c = n² |u|²/(s d h^{1/3})(Manning の閉じ)
  - τ*_m = τ*_c [1 + 1.2 (τ*_w/(τ*_c + τ*_w))^3.2]、
    τ*_max = √((τ*_m + τ*_w |cos φ|)² + (τ*_w sin φ)²)(Soulsby 1997 式 69・70)
  - 浮遊砂の平衡濃度 C_eq = esa (τ*_max/τ*c − 1)、地形の更新 Δt ごとの E-D の緩和
    c_{n+1} = c_n + (w_f Δt/h)(C_eq − β c_n) の n 回後 c_n = (C_eq/β)(1 − (1 − β w_f Δt/h)^n)
    (w_f は Rubey 式。モデルが表示した値を読む)
  - 掃流砂 q_b = q*(τ*_max) √(τ*_c/τ*_max) √(s g d³)(MPM q* = 8 (τ* − τ*c)^1.5)を流れの向きに
    (param_bed は u_a = 0 なので、モデルの √(τ*_s/τ*_max) の τ*_s = τ*_c)
  - CERC(Komar & Inman 1970): I_l = K (E c_g)_b sin α_b cos α_b(K = 0.77、E は H_rms)、
    固体体積の沿岸漂砂量 Q = I_l/(s ρ g)。砕波点はモデルの波高の最大のセル
  - 砕波の乱れ(turb。XBeach の turb = wave_averaged): k_s = (D_r/ρ)^{2/3}(Battjes 1975)、
    D_r = 2βgE_r/c(β = 0.1、c = σ/k)、L_mix = √(2E_r T/(ρc))(Svendsen 1984)、
    k_b = k_s/(exp(h/L_mix) − 1)(Roelvink & Stive 1989)。出力の E_r(Wr)と水深から。
    u_rms = H_rms σ/(2√2 sinh kh)(H_rms = Wh/√2)
"""
import math
import re
import struct
import sys

NX, NY = 120, 8
JC = NY // 2 - 1      # 検定に使う中央の行(0 始まり)
G = 9.8               # 重力加速度(既定 p%gg)
RHO = 1025.0          # 海水の密度(m_wavefield)
SGRAV = 1.65          # 水中比重(fluv_sgrav)
PORO = 0.4            # 空隙率(fluv_porosity)
D50 = 0.0002          # 粒径(fluv_d50・susp_d50)
TAUSC = 0.05          # 限界無次元掃流力(fluv_tausc・susp_tausc)
ESA = 1.0e-4          # 平衡濃度係数(susp_esa)
BETA = 1.0            # 沈降の底面濃度係数(susp_beta)

failed = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        failed.append(msg)


def read_bil(d, name, k="9998", nx=NX, ny=NY):
    with open("%s/%s%s.bil" % (d, name, k), "rb") as f:
        data = f.read()
    v = struct.unpack("<%df" % (nx * ny), data)
    return [list(v[j * nx:(j + 1) * nx]) for j in range(ny)]


def read_rec(f):
    n = struct.unpack("<i", f.read(4))[0]
    payload = f.read(n)
    n2 = struct.unpack("<i", f.read(4))[0]
    assert n == n2, "record marker mismatch"
    return payload


def read_rle(f, ntot):
    n, nrun = struct.unpack("<2q", read_rec(f))
    assert n == ntot, "unexpected array size %d != %d" % (n, ntot)
    runs = struct.unpack("<%dq" % (2 * nrun), read_rec(f))
    raw = read_rec(f)
    packed = struct.unpack("<%dd" % (len(raw) // 8), raw)
    out = [0.0] * n
    i = k = 0
    for r in range(nrun):
        i += runs[2 * r]
        lit = runs[2 * r + 1]
        out[i:i + lit] = packed[k:k + lit]
        i += lit
        k += lit
    return out


def read_state(savedir):
    """state.dat(h, z, hrs, hg, sd, hs の順。m_state の保存)"""
    with open(savedir + "/state.dat", "rb") as f:
        a = [read_rle(f, NX * NY) for _ in range(6)]
    return dict(zip(["h", "z", "hrs", "hg", "sd", "hs"], a))


def wavenumber(sig, h):
    y = sig * sig * h / G
    x = y if y > 1.0 else math.sqrt(y)
    for _ in range(100):
        f = x * math.tanh(x) - y
        df = math.tanh(x) + x / math.cosh(x) ** 2
        dx = f / df
        x -= dx
        if abs(dx) < 1e-14 * max(1.0, x):
            break
    return x / h


def taumax(tauc, urms, om, cphi):
    uw = math.sqrt(2.0) * urms
    if uw <= 0.0:
        return tauc, 0.0
    a = uw / om
    fw = min(1.39 * (a / (D50 / 12.0)) ** -0.52, 0.3)
    tw = 0.5 * fw * uw * uw / (SGRAV * G * D50)
    tm = tauc * (1.0 + 1.2 * (tw / (tauc + tw)) ** 3.2)
    return math.sqrt((tm + tw * cphi) ** 2 + tw * tw * (1.0 - cphi * cphi)), tw


def wave_vec(wa):
    """平均波向 Wa(deg。x 軸から反時計回り、y 北)を流れの規約(y 南)の単位ベクトルへ"""
    th = math.radians(wa)
    return math.cos(th), -math.sin(th)


def screen_value(log, pattern):
    with open(log) as f:
        for line in f:
            m = re.search(pattern, line)
            if m:
                return float(m.group(1))
    return None


# ----------------------------------------------------------------------
def check_stir(d, savedir, period=8.0, dtg=5.0, tt=1800.0, log="Screen_stir.log"):
    print("== stir (%s): waves only on a flat bed, suspended sediment stirred by the waves" % d)
    hs = read_bil(d, "Hs")
    h = read_bil(d, "H")
    wu = read_bil(d, "Wu")
    wf = screen_value(log, r"settling velocity \(Rubey\) =\s*([0-9.Ee+-]+)")
    check(wf is not None and wf > 0.0, "settling velocity read from %s (w_f = %s m/s)" % (log, wf))
    om = 2.0 * math.pi / period
    n = int(round(tt / dtg))
    worst = 0.0
    for j in range(NY):
        for i in range(NX):
            tmax, _ = taumax(0.0, wu[j][i], om, 0.0)
            ceq = ESA * (tmax / TAUSC - 1.0) if tmax > TAUSC else 0.0
            r = wf * dtg / h[j][i]
            cn = ceq / BETA * (1.0 - (1.0 - BETA * r) ** n)
            c = hs[j][i] / h[j][i]
            worst = max(worst, abs(c - cn) / cn)
    tm0, tw0 = taumax(0.0, wu[JC][NX // 2], om, 0.0)
    print("  stir: u_rms = %.4f m/s, tau*_w = %.4f, C_eq = %.4e, model C = %.4e (after %d updates)"
          % (wu[JC][NX // 2], tw0, ESA * (tm0 / TAUSC - 1.0), hs[JC][NX // 2] / h[JC][NX // 2], n))
    check(worst < 1e-5, "stir: concentration = Soulsby (1997) equilibrium with the E-D relaxation "
          "(max relative difference %.1e < 1e-5)" % worst)
    st = read_state(savedir)
    z0 = -5.0
    tot = sum(st["hs"]) + (1.0 - PORO) * sum(z - z0 for z in st["z"])
    rel = abs(tot) / sum(st["hs"])
    check(rel < 1e-10, "stir: sediment conserved (sum hs + (1-lambda) sum dz = %.2e, %.1e of sum hs)" % (tot, rel))


# ----------------------------------------------------------------------
def check_bed(d, period=6.0, rn=0.02):
    print("== bed (%s): bed load on a uniform current with oblique waves" % d)
    u = read_bil(d, "u")
    v = read_bil(d, "v")
    h = read_bil(d, "H")
    wu = read_bil(d, "Wu")
    wa = read_bil(d, "Wa")
    qx = read_bil(d, "Qbx")
    qy = read_bil(d, "Qby")
    om = 2.0 * math.pi / period
    qcoef = math.sqrt(SGRAV * G * D50 ** 3)
    worst = worst_dir = 0.0
    fmin = 1e30
    for j in range(NY):
        for i in range(20, 110):
            U = math.hypot(u[j][i], v[j][i])
            tc = rn * rn * U * U / (SGRAV * D50 * h[j][i] ** (1.0 / 3.0))
            wx, wy = wave_vec(wa[j][i])
            cphi = abs(u[j][i] * wx + v[j][i] * wy) / U
            tmax, _ = taumax(tc, wu[j][i], om, cphi)
            qb = 8.0 * (tmax - TAUSC) ** 1.5 * qcoef * math.sqrt(tc / tmax)
            qc = 8.0 * (tc - TAUSC) ** 1.5 * qcoef if tc > TAUSC else 0.0
            qm = math.hypot(qx[j][i], qy[j][i])
            worst = max(worst, abs(qm - qb) / qb)
            worst_dir = max(worst_dir, abs(math.atan2(qy[j][i], qx[j][i]) - math.atan2(v[j][i], u[j][i])))
            if qc > 0.0:
                fmin = min(fmin, qb / qc)
    i = NX // 2
    U = math.hypot(u[JC][i], v[JC][i])
    print("  bed: U = %.4f m/s, h = %.3f m, mean wave direction %.2f deg, model q_b = %.4e m2/s"
          % (U, h[JC][i], wa[JC][i], math.hypot(qx[JC][i], qy[JC][i])))
    check(worst < 1e-5, "bed: q_b = q*(tau*_max) sqrt(tau*_c/tau*_max) sqrt(sgd^3) (Soulsby 1997 stress; "
          "max relative difference %.1e < 1e-5)" % worst)
    check(worst_dir < 1e-5, "bed: the bed load moves in the current direction (max angle %.1e rad)" % worst_dir)
    check(fmin > 1.5, "bed: the waves stir the bed (q_b / q_b(current only) >= %.2f > 1.5)" % fmin)


# ----------------------------------------------------------------------
def check_beach(d, period=8.0):
    print("== beach (%s): longshore sediment transport on a 1:80 beach" % d)
    h = read_bil(d, "H")
    wh = read_bil(d, "Wh")
    wa = read_bil(d, "Wa")
    wb = read_bil(d, "Wb")
    v = read_bil(d, "v")
    qbx = read_bil(d, "Qbx")
    qby = read_bil(d, "Qby")
    qsx = read_bil(d, "Qsx")
    qsy = read_bil(d, "Qsy")
    z = read_bil(d, "Z")
    z0 = read_bil(d, "Z", "0000")
    j = JC
    qy = [qby[j][i] + qsy[j][i] for i in range(NX)]
    rows = [sum(qby[jj][i] + qsy[jj][i] for i in range(NX)) * 10.0 for jj in range(NY)]
    qtot = rows[j]
    qb_tot = sum(qby[j]) * 10.0
    qs_tot = sum(qsy[j]) * 10.0
    print("  beach: longshore transport (solid, y south positive) bed %.4e + suspended %.4e = %.4e m3/s"
          % (qb_tot, qs_tot, qtot))
    check(all(r < 0.0 for r in rows), "beach: the longshore transport is northward like the current in every row")
    dmax = max(wb[j])
    ib = max(range(NX), key=lambda i: wb[j][i])
    surf = [i for i in range(NX) if wb[j][i] > 0.05 * dmax]
    ipk = min(range(NX), key=lambda i: qy[i])
    print("  beach: surf zone (D_b > 5%% of max) i = %d..%d, D_b max at i = %d, transport peak at i = %d"
          % (surf[0], surf[-1], ib, ipk))
    check(surf[0] <= ipk <= surf[-1], "beach: the longshore transport peaks in the surf zone (i = %d)" % ipk)
    i0 = min(i for i in range(NX) if wb[j][i] > 1e-3 * dmax)
    off = max(abs(qy[i]) for i in range(i0))
    check(off <= 0.05 * abs(qy[ipk]), "beach: offshore of the surf zone (i < %d) |q| = %.2e <= 5%% of the peak %.2e"
          % (i0, off, abs(qy[ipk])))
    spread = (max(rows) - min(rows)) / abs(qtot)
    check(spread < 1e-4, "beach: alongshore uniformity of the transport (row totals differ by %.1e < 1e-4)" % spread)
    dzr = max(max(z[jj][i] - z0[jj][i] for jj in range(NY)) - min(z[jj][i] - z0[jj][i] for jj in range(NY))
              for i in range(NX))
    check(dzr < 1e-5, "beach: alongshore uniformity of the bed change (row difference %.1e m < 1e-5 m)" % dzr)
    # CERC(Komar & Inman 1970)を砕波点(波高の最大)の波で
    ibk = max(range(NX), key=lambda i: wh[j][i])
    hrms = wh[j][ibk] / math.sqrt(2.0)
    hb = h[j][ibk]
    om = 2.0 * math.pi / period
    k = wavenumber(om, hb)
    cg = 0.5 * (1.0 + 2.0 * k * hb / math.sinh(2.0 * k * hb)) * om / k
    al = math.radians(wa[j][ibk])
    il = 0.77 * RHO * G * hrms * hrms / 8.0 * cg * math.sin(al) * math.cos(al)
    qcerc = il / (SGRAV * RHO * G)
    ratio = abs(qtot) / qcerc
    print("  beach: breaker (max H) i = %d, H_rms = %.3f m, h = %.3f m, alpha = %.2f deg -> CERC %.4e m3/s, "
          "ratio %.2f" % (ibk, hrms, hb, wa[j][ibk], qcerc, ratio))
    check(0.2 <= ratio <= 5.0, "beach: the total longshore transport is of the same order as CERC "
          "(Komar & Inman 1970; ratio %.2f in [0.2, 5])" % ratio)
    qxs = sum(qsx[j][i] + qbx[j][i] for i in surf)
    check(qxs < 0.0, "beach: the cross-shore transport in the surf zone is offshore (undertow; sum %.2e m2/s)" % qxs)
    dz = [z[j][i] - z0[j][i] for i in range(NX)]
    idep = max(range(NX), key=lambda i: dz[i])
    iero = min(range(NX), key=lambda i: dz[i])
    print("  beach: max deposition %.4f m at i = %d, max erosion %.4f m at i = %d (v at the peak %.3f m/s)"
          % (dz[idep], idep, dz[iero], iero, v[j][ipk]))
    check(idep < iero, "beach: deposition offshore of the erosion (bar-forming response to the undertow)")


# ----------------------------------------------------------------------
def asym_velocity(hrms, k, h, urms, fsk=0.1, fas=0.1):
    """u_a = (f_Sk S_k − f_As A_s) u_rms(van Thiel de Vries 2009)、S_k・A_s は Ruessink ら(2012)。
    係数 p2〜p6 は XBeach の公開ソース(morphevolution.F90 の RvR)の値"""
    p2, p3, p4, p5, p6 = 0.7939, -0.6065, 0.3539, 0.6373, 0.5995
    kh = k * h
    if urms <= 0.0 or kh <= 0.0:
        return 0.0
    ur = max(0.375 * math.sqrt(2.0) * hrms * k / kh ** 3, 1e-12)
    b = p2 / (1.0 + math.exp((p3 - math.log10(ur)) / p4))
    psi = math.radians(-90.0 + 90.0 * math.tanh(p5 / ur ** p6))
    return (fsk * b * math.cos(psi) - fas * b * math.sin(psi)) * urms


def check_asym(d, period=8.0):
    print("== asym (%s): onshore transport velocity of wave skewness and asymmetry (stage W5)" % d)
    h = read_bil(d, "H")
    wh = read_bil(d, "Wh")
    wu = read_bil(d, "Wu")
    ua = read_bil(d, "Wua")
    om = 2.0 * math.pi / period
    worst = 0.0
    n = 0
    for j in range(NY):
        for i in range(NX):
            if wu[j][i] <= 1e-3 or h[j][i] < 0.2:
                continue
            k = wavenumber(om, h[j][i])
            ref = asym_velocity(wh[j][i] / math.sqrt(2.0), k, h[j][i], wu[j][i])
            worst = max(worst, abs(ua[j][i] - ref) / abs(ref))
            n += 1
    i = max(range(NX), key=lambda ii: ua[JC][ii])
    print("  asym: max u_a = %.4f m/s at i = %d (h = %.3f m, u_rms = %.4f m/s)" % (ua[JC][i], i, h[JC][i], wu[JC][i]))
    check(n > 0 and worst < 2e-4, "asym: u_a = (f_Sk S_k - f_As A_s) u_rms with the Ruessink et al. (2012) "
          "parameterization (%d cells, max relative difference %.1e < 2e-4)" % (n, worst))
    check(min(ua[j][i] for j in range(NY) for i in range(NX) if wu[j][i] > 1e-3) > 0.0,
          "asym: u_a is onshore (along the waves) wherever there are waves")


def check_shore(dstorm, dcalm):
    print("== shore (%s, %s): erosion by high waves and recovery by low waves (stage W5)" % (dstorm, dcalm))
    for d, sign, label in [(dstorm, -1.0, "storm"), (dcalm, 1.0, "calm")]:
        wb = read_bil(d, "Wb")[JC]
        wh = read_bil(d, "Wh")[JC]
        qx = [read_bil(d, "Qsx")[JC][i] + read_bil(d, "Qbx")[JC][i] for i in range(NX)]
        dmax = max(wb)
        i0 = min(i for i in range(NX) if wb[i] > 0.05 * dmax)      # 砕波帯の沖の端
        wave = [i for i in range(NX) if wh[i] > 0.0]
        if label == "storm":
            cells = [i for i in wave if i >= 20]
            ok = all(qx[i] < 0.0 for i in cells)
            check(ok, "shore: storm (H_m0 = 2 m) cross-shore transport offshore in cells %d..%d (max %.2e m2/s)"
                  % (cells[0], cells[-1], max(qx[i] for i in cells)))
        else:
            # 砕波帯より沖で輸送のある(その区間の最大の 1% を超える)セル。深いところは限界掃流力に
            # 届かず輸送がない
            zone = [i for i in wave if i < i0 - 4]
            qref = max(abs(qx[i]) for i in zone)
            cells = [i for i in zone if abs(qx[i]) > 0.01 * qref]
            ok = len(cells) >= 10 and all(qx[i] > 0.0 for i in cells)
            check(ok, "shore: calm (H_m0 = 0.6 m, T = 12 s) cross-shore transport onshore offshore of the surf zone "
                  "(cells %d..%d with transport, min %.2e m2/s; surf zone from i = %d)"
                  % (cells[0], cells[-1], min(qx[i] for i in cells), i0))


# ----------------------------------------------------------------------
def check_closed(savedir):
    print("== closed (%s): sediment conservation in a closed basin" % savedir)
    st = read_state(savedir)
    z0 = [((i + 0.5) * 10.0 - 1100.0) / 80.0 for _ in range(NY) for i in range(NX)]
    tot = sum(st["hs"]) + (1.0 - PORO) * sum(z - zz for z, zz in zip(st["z"], z0))
    rel = abs(tot) / sum(st["hs"])
    dzm = max(abs(z - zz) for z, zz in zip(st["z"], z0))
    print("  closed: sum hs = %.6e m3/m2-cell, max |dz| = %.4f m" % (sum(st["hs"]), dzm))
    check(dzm > 1e-3, "closed: the bed changes (max |dz| = %.4f m)" % dzm)
    check(rel < 1e-10, "closed: sediment conserved (sum hs + (1-lambda) sum dz = %.2e, %.1e of sum hs)" % (tot, rel))


def check_turb(d, dbase, period=8.0, beta=0.1):
    """基本に砕波の乱れによる攪拌(f_wfsed_turb = 1)を加える: 出力の底面の乱れ Wkb が
    k_b = k_s/(exp(h/L_mix) − 1)(k_s = (D_r/ρ)^{2/3}、L_mix = √(2E_r T/(ρc)))に一致し、
    出力 Wu は乱れを含まない u_rms のまま(攪拌の速さ √(u_rms² + 1.45 k_b) は内部だけ)。
    ローラーの厚さが水深に比べて大きい汀線側で乱れが底面に届き、攪拌が強まって沿岸漂砂が増える"""
    print("== turb (%s vs %s): stirring by the turbulence of wave breaking (f_wfsed_turb = 1)" % (d, dbase))
    h = read_bil(d, "H")
    wh = read_bil(d, "Wh")
    wr = read_bil(d, "Wr")
    wkb = read_bil(d, "Wkb")
    wu = read_bil(d, "Wu")
    wb = read_bil(d, "Wb")
    j = JC
    om = 2.0 * math.pi / period
    dk = du = kbmax = umax = 0.0
    ikb = 0
    for i in range(NX):
        hh = h[j][i]
        if wh[j][i] <= 0.0 or hh < 0.1:
            continue
        k = wavenumber(om, hh)
        c = om / k
        kb = 0.0
        if wr[j][i] > 0.0:
            ks = (2.0 * beta * G * wr[j][i] / c / RHO) ** (2.0 / 3.0)
            x = hh / math.sqrt(2.0 * wr[j][i] * period / (RHO * c))
            if x <= 50.0:
                kb = ks / (math.exp(x) - 1.0)
        if kb > kbmax:
            kbmax, ikb = kb, i
        dk = max(dk, abs(wkb[j][i] - kb))
        kh = k * hh
        ur = wh[j][i] / math.sqrt(2.0) * om / (2.0 * math.sqrt(2.0) * math.sinh(kh)) if kh <= 20.0 else 0.0
        umax = max(umax, ur)
        du = max(du, abs(wu[j][i] - ur))
    ib = max(range(NX), key=lambda i: wb[j][i])
    gain = math.sqrt(wu[j][ikb] ** 2 + 1.45 * wkb[j][ikb]) / wu[j][ikb]
    print("  turb: max k_b = %.4e m2/s2 at i = %d (h = %.2f m, stirring speed x%.3f), max D_b at i = %d"
          % (kbmax, ikb + 1, h[j][ikb], gain, ib + 1))
    check(dk <= 1e-4 * kbmax, "turb: Wkb = k_s/(exp(h/L_mix) - 1) (max difference %.1e of max k_b <= 1e-4)"
          % (dk / kbmax))
    check(du <= 1e-4 * umax, "turb: the output Wu stays the orbital velocity u_rms without turbulence "
          "(max difference %.1e of max u_rms <= 1e-4)" % (du / umax))
    check(ikb > ib, "turb: the near-bed turbulence peaks shoreward of the peak breaking (i = %d > %d)"
          % (ikb + 1, ib + 1))
    rows = []
    for jj in range(NY):
        qb = read_bil(d, "Qby")[jj]
        qs = read_bil(d, "Qsy")[jj]
        rows.append(sum(qb[i] + qs[i] for i in range(NX)) * 10.0)
    qb0 = read_bil(dbase, "Qby")[j]
    qs0 = read_bil(dbase, "Qsy")[j]
    q0 = sum(qb0[i] + qs0[i] for i in range(NX)) * 10.0
    ratio = rows[j] / q0
    print("  turb: longshore transport %.4e m3/s (base %.4e, ratio %.3f)" % (rows[j], q0, ratio))
    check(1.0 < ratio <= 1.5, "turb: the turbulence increases the longshore transport (ratio %.3f in (1, 1.5])"
          % ratio)
    spread = (max(rows) - min(rows)) / abs(rows[j])
    check(spread < 1e-4, "turb: alongshore uniformity of the transport (row totals differ by %.1e < 1e-4)" % spread)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    mode = sys.argv[1]
    if mode == "stir":
        check_stir(sys.argv[2], sys.argv[3])
    elif mode == "bed":
        check_bed(sys.argv[2])
    elif mode == "beach":
        check_beach(sys.argv[2])
    elif mode == "closed":
        check_closed(sys.argv[2])
    elif mode == "asym":
        check_asym(sys.argv[2])
    elif mode == "shore":
        check_shore(sys.argv[2], sys.argv[3])
    elif mode == "turb":
        check_turb(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)
        sys.exit(2)
    if failed:
        print("=== Check_wfsed.py %s: FAIL (%d) ===" % (mode, len(failed)))
        sys.exit(1)
    print("=== Check_wfsed.py %s: PASS ===" % mode)


if __name__ == "__main__":
    main()
