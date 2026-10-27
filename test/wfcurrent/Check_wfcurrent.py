#!/usr/bin/env python3
"""wfcurrent: 沿岸の波浪場の流れへの作用(段 W2。fn_wavefield の wf_flow。developer.md §88)の検定

Python 標準ライブラリのみ。使い方:
  python3 Check_wfcurrent.py setup  result_setup          # セットアップ(規則波・直角入射、wf_flow = 1)
  python3 Check_wfcurrent.py flat   result_flat           # 一様水深の沿岸流と岸沖の釣り合い(wf_flow = 2)
  python3 Check_wfcurrent.py long   result_long           # 海浜の沿岸流(不規則波、ローラーなし)
  python3 Check_wfcurrent.py roller result result_long    # 同じ構成でローラーあり(基本 param.txt)
  python3 Check_wfcurrent.py rot    result result_rot     # 基本を 90° 回した格子(W・E が側方 Neumann)
  python3 Check_wfcurrent.py cur    result_cur result     # 基本に流れの波への作用(段 W3)を加えた双方向の連成

格子は 120 × 8 セル(Δx = Δy = 10 m)。西(i = 1)が沖で入射、南北は側方 Neumann(波・流れとも)。
分布は bil(単精度)の最終出力(9998)で読む。y の成分(v・Wfy・Wsy)は流れの出力と同じ
規約(行の増える向き = 南が正)で、北向きの沿岸流は負。

独立に組み立てる参照:
  - 分散関係 σ² = g k tanh(kh) を倍精度の Newton 法で解き、c = σ/k、n = c_g/c
  - セットアップ(静止 u = 0 の定常): 面 (i, i+1) ごとの離散の釣り合い
      g_e (η_{i+1} − η_i)/Δx = (F_i + F_{i+1}) / (2 ρ h_f)、h_f = (h_i + h_{i+1})/2、
      g_e = g Δx²/(Δx² + Δz²)(急勾配の重力補正。浅水流の既定)
    砕波帯より沖の set-down η = −H²k/(8 sinh 2kh)(Longuet-Higgins & Stewart 1962。
    沖の境界のセルとの差で比べる)、砕波帯の勾配 dη/dx = −K dz/dx、
    K = 1/(1 + 8/(3γ²))(Bowen ら 1968。飽和砕波 H = γh の浅水の極限)
  - 沿岸流(岸沿いに一様な定常): セルごとの沿岸方向の運動量の釣り合い
      F_y/(ρh) = g n² |V_E| v_E / h^{4/3}、v_E = v − v_S、
      |V_E| = √(u_E² + v_E² + (1.16 u_rms)²)、u_E = u − u_S
    を v_E について閉じた形で解く(a = v_E: a²(A + a²) = R²、A = u_E² + (1.16 u_rms)²、
    R = F_y h^{1/3}/(ρ g n²))。GLM の流速は u = u^L(Lagrangian 平均)で、摩擦は
    オイラー流速 u^E = u^L − u^S に作用する(Ruessink ら 2001 の波・流れの摩擦。XBeach と同じ)
  - 岸沖の面の釣り合い(GLM): g_e Δη/Δx = F_x/(ρh_f) − g n² |V_E| (u − u_S)/h_f^{4/3}
    (u^L ≈ 0 のとき戻り流れ u^E = −u^S の摩擦がセットアップを押し上げる)
  - ローラーのエネルギー(定常): Σ(D_b + 上限の除去) = Σ D_r + 汀線への流出、
    D_r = 2 β g E_r / c(Reniers & Battjes 1997。β = 0.1 は XBeach の既定)。流れの波への
    作用(cur)では c は平均波向の向きの流速成分 U_θ でのドップラーの分散関係
    (ω − k U_θ)² = g k tanh(kh) の固有の位相速度 σ/k(モデルはビンのエネルギー重みの平均)
"""
import csv
import math
import struct
import sys

NX, NY, DX, DY = 120, 8, 10.0, 10.0
JC = NY // 2 - 1      # 検定に使う中央の行(0 始まり)
G = 9.8               # 重力加速度(既定 p%gg)
RHO = 1025.0          # 海水の密度(m_wavefield)
GAMMA = 0.78          # 砕波指標(既定)
BETA = 0.1            # ローラーの散逸係数(既定)
HMIN = 0.1            # 波浪セルの最小水深(既定)

failed = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        failed.append(msg)


def read_bil(d, name, k="9998"):
    with open("%s/%s%s.bil" % (d, name, k), "rb") as f:
        data = f.read()
    v = struct.unpack("<%df" % (NX * NY), data)
    return [list(v[j * NX:(j + 1) * NX]) for j in range(NY)]


def read_fields(d, names):
    a = {n: read_bil(d, n) for n in names}
    a["Z"] = read_bil(d, "Z", "0000")
    return a


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


def depth(a, j, i):
    return a["E"][j][i] - a["Z"][j][i]


def param_value(path, key):
    """パラメータファイルから key = 値 を読む(最初に現れたもの)"""
    for line in open(path, encoding="utf-8"):
        s = line.split("!")[0].strip()
        if s.startswith(key) and "=" in s and s.split("=")[0].strip() == key:
            return float(s.split("=")[1].strip().strip("'"))
    return None


def uniformity(a, names, tol, label):
    """岸沿い(行)の一様性: 中央の行との差の最大"""
    for n in names:
        m = 0.0
        for j in range(NY):
            for i in range(NX):
                if depth(a, JC, i) < HMIN:
                    continue
                m = max(m, abs(a[n][j][i] - a[n][JC][i]))
        check(m <= tol[n], "%s: alongshore uniformity of %s (max row difference %.2e <= %.0e)"
              % (label, n, m, tol[n]))


def alongshore_closed(a, rn, label, tol_rel):
    """セルごとの沿岸方向の閉じた形 v = v_S + a と、積分の釣り合い Σ F_y/ρ = Σ τ_y/ρ"""
    j = JC
    vmax = max(abs(a["v"][j][i]) for i in range(NX))
    dmax, imax = 0.0, 0
    sf = st = 0.0
    for i in range(NX):
        h = depth(a, j, i)
        if h < HMIN or a["Wh"][j][i] <= 0.0:
            continue
        us, vs, ur, fy = a["Wsx"][j][i], a["Wsy"][j][i], a["Wu"][j][i], a["Wfy"][j][i]
        ue = a["u"][j][i] - us
        aq = ue * ue + (1.16 * ur) ** 2
        r = fy * h ** (1.0 / 3.0) / (RHO * G * rn * rn)
        a2 = (-aq + math.sqrt(aq * aq + 4.0 * r * r)) / 2.0
        vp = vs + math.copysign(math.sqrt(a2), r)
        dv = abs(a["v"][j][i] - vp)
        if dv > dmax:
            dmax, imax = dv, i + 1
        ve = a["v"][j][i] - vs
        st += G * rn * rn * math.sqrt(ue * ue + ve * ve + (1.16 * ur) ** 2) * ve / h ** (1.0 / 3.0)
        sf += fy / RHO
    print("  %s: max |v| = %.4f m/s, cell balance max difference %.5f m/s at i = %d"
          % (label, vmax, dmax, imax))
    check(dmax <= tol_rel * vmax,
          "%s: v = v_S + v_E from the per-cell alongshore balance (max difference %.2f%% <= %.0f%% of max |v|)"
          % (label, 100.0 * dmax / vmax, 100.0 * tol_rel))
    ratio = st / sf
    check(abs(ratio - 1.0) <= 0.02,
          "%s: integral alongshore momentum balance sum(tau_y)/sum(F_y) = %.4f (within 2%%)" % (label, ratio))
    return vmax


def check_setup(d):
    print("== setup (%s): regular waves H = 1 m, T = 8 s, normal incidence, wave force only" % d)
    a = read_fields(d, ["E", "u", "v", "Wh", "Wfx"])
    uniformity(a, ["E"], {"E": 1.0e-4}, "setup")
    j = JC
    sig = 2.0 * math.pi / 8.0
    # (1) 面ごとの離散の釣り合い
    worst = 0.0
    nf = 0
    for i in range(NX - 1):
        h1, h2 = depth(a, j, i), depth(a, j, i + 1)
        if h1 < HMIN or h2 < HMIN:
            continue
        dz = a["Z"][j][i + 1] - a["Z"][j][i]
        ge = G * DX * DX / (DX * DX + dz * dz)
        lhs = ge * (a["E"][j][i + 1] - a["E"][j][i]) / DX
        rhs = (a["Wfx"][j][i] + a["Wfx"][j][i + 1]) / (2.0 * RHO * 0.5 * (h1 + h2))
        worst = max(worst, abs(lhs - rhs) / (0.02 * abs(rhs) + 5.0e-6))
        nf += 1
    check(worst <= 1.0, "setup: per-face balance g_e d(eta)/dx = F_x/(rho h) on %d faces "
          "(|residual| <= 2%% of the force term + 5e-6 m/s2; worst %.2f of the tolerance)" % (nf, worst))
    # (2) 砕波帯より沖の set-down(Longuet-Higgins & Stewart 1962)
    def lhs_setdown(i):
        h = depth(a, j, i)
        k = wavenumber(sig, h)
        return -a["Wh"][j][i] ** 2 * k / (8.0 * math.sinh(2.0 * k * h))

    ib = None
    for i in range(NX):
        h = depth(a, j, i)
        if h < HMIN:
            break
        k = wavenumber(sig, h)
        hb = 0.88 / k * math.tanh(GAMMA * k * h / 0.88)
        if a["Wh"][j][i] >= 0.98 * hb:
            ib = i
            break
    check(ib is not None and ib > 10, "setup: breaking (saturation) starts at i = %s" % (None if ib is None else ib + 1))
    if ib is None:
        return
    s0, e0 = lhs_setdown(0), a["E"][j][0]
    sb = lhs_setdown(ib - 2) - s0
    err = max(abs((a["E"][j][i] - e0) - (lhs_setdown(i) - s0)) for i in range(ib - 1))
    print("  set-down at i = %d: model %.2f mm, Longuet-Higgins & Stewart %.2f mm (relative to i = 1)"
          % (ib - 1, (a["E"][j][ib - 2] - e0) * 1e3, sb * 1e3))
    check(err <= 0.02 * abs(sb), "setup: set-down offshore of breaking agrees with -H^2 k/(8 sinh 2kh) "
          "(max difference %.3f mm <= 2%% of the set-down at the breaker line)" % (err * 1e3))
    # (3) 砕波帯の勾配(Bowen ら 1968)
    kb = 1.0 / (1.0 + 8.0 / (3.0 * GAMMA ** 2))
    ks = []
    for i in range(ib + 1, NX - 1):
        h = depth(a, j, i)
        if h < 0.3:
            break
        if h > 1.5:
            continue
        slope = (a["Z"][j][i + 1] - a["Z"][j][i - 1]) / (2.0 * DX)
        ks.append((a["E"][j][i + 1] - a["E"][j][i - 1]) / (2.0 * DX) / slope)
    kmin, kmax = min(ks), max(ks)
    print("  surf zone setup slope K = %.4f .. %.4f over %d cells (Bowen et al. 1968: %.4f)"
          % (kmin, kmax, len(ks), kb))
    check(len(ks) >= 5 and kmin >= 0.92 * kb and kmax <= 1.04 * kb,
          "setup: surf zone slope d(eta)/dx = -K dz/dx within -8%..+4% of Bowen's K")


def check_flat(d):
    print("== flat (%s): uniform depth 5 m, random waves at 30 deg, bottom friction only" % d)
    a = read_fields(d, ["E", "u", "v", "Wh", "Wu", "Wfx", "Wfy", "Wsx", "Wsy"])
    rn = param_value("param_flat.txt", "rn0")
    uniformity(a, ["E", "v"], {"E": 1.0e-5, "v": 1.0e-4}, "flat")
    vmax = alongshore_closed(a, rn, "flat", 0.02)
    j = JC
    check(all(a["v"][j][i] < 0.0 for i in range(NX)), "flat: the current flows north (v < 0) everywhere")
    # 岸沖の面ごとの釣り合い(戻り流れの摩擦を含む)
    def spd(i):
        return math.sqrt((a["u"][j][i] - a["Wsx"][j][i]) ** 2 + (a["v"][j][i] - a["Wsy"][j][i]) ** 2
                         + (1.16 * a["Wu"][j][i]) ** 2)

    worst = 0.0
    frac = []
    for i in range(NX - 1):
        h1, h2 = depth(a, j, i), depth(a, j, i + 1)
        hf = 0.5 * (h1 + h2)
        lhs = G * (a["E"][j][i + 1] - a["E"][j][i]) / DX
        force = (a["Wfx"][j][i] + a["Wfx"][j][i + 1]) / (2.0 * RHO * hf)
        vve = 0.5 * (spd(i) + spd(i + 1))
        uf = 0.5 * (a["u"][j][i] + a["u"][j][i + 1])
        usf = 0.5 * (a["Wsx"][j][i] + a["Wsx"][j][i + 1])
        fric = -G * rn * rn * vve * (uf - usf) / hf ** (4.0 / 3.0)
        worst = max(worst, abs(lhs - force - fric) / abs(force + fric))
        frac.append(fric / (force + fric))
    print("  undertow friction is %.0f..%.0f%% of the setup gradient" % (100 * min(frac), 100 * max(frac)))
    check(worst <= 0.01, "flat: per-face cross-shore balance g d(eta)/dx = F_x/(rho h) + undertow friction "
          "(max relative residual %.2e <= 1%%)" % worst)
    usmax = max(abs(a["Wsx"][j][i]) for i in range(NX))
    umax = max(abs(a["u"][j][i]) for i in range(NX))
    check(umax <= 0.01 * usmax, "flat: Lagrangian cross-shore velocity u^L ~ 0 (max |u| = %.1e <= 1%% of max u_S = %.4f)"
          % (umax, usmax))
    return vmax


def beach_current(d, label):
    a = read_fields(d, ["E", "u", "v", "Wh", "Wu", "Wb", "Wfy", "Wsx", "Wsy"])
    rn = param_value("param_long.txt", "rn0")
    vmax = alongshore_closed(a, rn, label, 0.05)
    j = JC
    # 岸沿いの一様性(流れは最大の 1%)
    dv = max(abs(a["v"][jj][i] - a["v"][j][i]) for jj in range(NY) for i in range(NX))
    check(dv <= 0.01 * vmax, "%s: alongshore uniformity of v (max row difference %.1e <= 1%% of max |v|)" % (label, dv))
    # 最大は砕波帯の中、沖の流れは小さい
    dbmax = max(a["Wb"][j])
    ipk = min(range(NX), key=lambda i: a["v"][j][i])
    check(a["v"][j][ipk] < 0.0 and a["Wb"][j][ipk] >= 0.5 * dbmax,
          "%s: the northward current peaks in the surf zone (i = %d, D_b = %.0f%% of its maximum)"
          % (label, ipk + 1, 100.0 * a["Wb"][j][ipk] / dbmax))
    # 砕波帯より沖(砕波の散逸が最大の 0.1% 未満のセル)。砕波の始まりの外縁では、ENC の
    # 斜めの面の移流が沿岸流を横へならすので数 % の流れがある(横混合に相当)
    i0 = next(i for i in range(NX) if a["Wb"][j][i] > 0.001 * dbmax)
    voff = max(abs(a["v"][j][i]) for i in range(i0))
    check(voff <= 0.01 * vmax, "%s: offshore of the surf zone (i < %d) |v| = %.5f <= 1%% of max |v|"
          % (label, i0 + 1, voff))
    usmax = max(abs(a["Wsx"][j][i]) for i in range(NX))
    umax = max(abs(a["u"][j][i]) for i in range(NX) if depth(a, j, i) >= HMIN)
    check(umax <= 0.05 * usmax, "%s: Lagrangian cross-shore velocity u^L ~ 0 (max |u| = %.1e <= 5%% of max u_S = %.3f)"
          % (label, umax, usmax))
    return a


def centroid(vals):
    w = [abs(x) for x in vals]
    return sum((i + 1) * w[i] for i in range(len(w))) / sum(w)


def check_long(d):
    print("== long (%s): random waves H_m0 = 1 m at 20 deg on the 1/80 beach, no roller" % d)
    beach_current(d, "long")


def check_roller(d, dlong):
    print("== roller (%s): same as long with the roller (default)" % d)
    a = beach_current(d, "roller")
    b = read_fields(dlong, ["E", "v", "Wfy"])
    j = JC
    fr = min(range(NX), key=lambda i: a["Wfy"][j][i])
    fl = min(range(NX), key=lambda i: b["Wfy"][j][i])
    cr, cl = centroid(a["v"][j]), centroid(b["v"][j])
    print("  force peak i = %d (no roller %d); current centroid i = %.2f (no roller %.2f)" % (fr + 1, fl + 1, cr, cl))
    check(fr > fl and (cr - cl) * DX >= 3.0,
          "roller: the force peak and the current move shoreward (force +%d cells, centroid +%.1f m >= 3 m)"
          % (fr - fl, (cr - cl) * DX))
    roller_budget(d, a, "roller", False)


def doppler_c(sig, h, um):
    """(ω − k U)² = g k tanh(kh) の U → 0 で連続な枝の固有の位相速度 σ/k と固有角周波数 σ
    (順流・弱い逆流)"""
    k = wavenumber(sig, h)
    for _ in range(100):
        kh = k * h
        s0 = math.sqrt(G * k * math.tanh(kh))
        dk = (s0 + k * um - sig) / (0.5 * s0 / k * (1.0 + 2.0 * kh / math.sinh(2.0 * kh)) + um)
        k -= dk
        if abs(dk) <= 1e-14 * k:
            break
    return (sig - k * um) / k, sig - k * um


def roller_budget(d, a, label, cur):
    """ローラーのエネルギーの収支(台帳の砕波 + 上限の除去 = Σ D_r + 汀線への流出)と分布。
    流れの波への作用(cur)では台帳が作用量 × ω なので、砕波の分布で重みを付けた σ/ω を
    掛けてエネルギーにする"""
    j = JC
    a2 = read_fields(d, ["Wr", "Wa"])
    sig = 2.0 * math.pi / 8.0
    sdr = 0.0
    wsum = wsr = 0.0
    last = None
    for i in range(NX):
        h = depth(a, j, i)
        if a["Wh"][j][i] <= 0.0 or h < HMIN:
            continue
        if cur:
            th = math.radians(a2["Wa"][j][i])
            um = a["u"][j][i] * math.cos(th) - a["v"][j][i] * math.sin(th)    # v は南が正
            c, sg = doppler_c(sig, h, um)
            wsum += a["Wb"][j][i]
            wsr += a["Wb"][j][i] * sg / sig
        else:
            c = sig / wavenumber(sig, h)
        sdr += 2.0 * BETA * G * a2["Wr"][j][i] / c * DX
        last = (c, a2["Wr"][j][i], a2["Wa"][j][i])
    c, er, th = last
    flux = c * er * math.cos(math.radians(th))
    row = read_csv("%s/wavefield.csv" % d)[-1]
    src = (float(row["breaking_W"]) + float(row["limit_W"])) / (NY * DY)
    if cur:
        src *= wsr / wsum
    print("  roller source (breaking + limit, ledger) %.1f W/m = dissipation %.1f + flux to the shoreline %.1f W/m"
          % (src, sdr, flux))
    check(abs(sdr + flux - src) <= 0.01 * src,
          "%s: steady roller energy budget closes within 1%% (%.2f%%)" % (label, 100.0 * (sdr + flux - src) / src))
    i0 = next(i for i in range(NX) if a["Wb"][j][i] > 0.001 * max(a["Wb"][j]))
    ermax = max(a2["Wr"][j])
    eroff = max(a2["Wr"][j][i] for i in range(i0))
    check(eroff <= 0.01 * ermax, "%s: the roller energy is confined to the surf zone (offshore max %.2e J/m2)"
          % (label, eroff))


def check_cur(d, dbase):
    """基本に流れの波への作用(段 W3)を加えた双方向の連成: 段 W2 と同じ釣り合いと収支が成り立ち、
    流れの作用が波と沿岸流を変える"""
    print("== cur (%s vs %s): the base case with the current acting on the waves (f_wf_current = 1)" % (d, dbase))
    a = beach_current(d, "cur")
    roller_budget(d, a, "cur", True)
    b = read_fields(dbase, ["E", "v", "Wh", "Wa"])
    j = JC
    cells = [i for i in range(NX) if a["Wh"][j][i] > 0.0 and depth(a, j, i) >= HMIN]
    dh = max(abs(a["Wh"][j][i] - b["Wh"][j][i]) / b["Wh"][j][i] for i in cells)
    dvmax = max(abs(x) for x in a["v"][j]) / max(abs(x) for x in b["v"][j]) - 1.0
    print("  cur: max relative change of the wave height %.2e, of the peak longshore current %+.2e" % (dh, dvmax))
    check(1e-4 <= dh <= 0.05, "cur: the current changes the waves (max relative change of the wave height %.1e, "
          "between 1e-4 and 5%%)" % dh)
    row = read_csv("%s/wavefield.csv" % d)[-1]
    vin = float(row["in_W"])
    imb = float(row["imbalance_W"])
    check(abs(imb) <= 1e-6 * vin, "cur: the wave ledger (action x omega) closes (imbalance %.1e of the inflow)"
          % (abs(imb) / vin))


def check_rot(d, drot):
    """基本(120 × 8)を時計回りに 90° 回した格子(8 × 120)の結果と比べる。
    セル (i, j) → (9 − j, i)、東向き u → 南向き v(行の増える向き)、y 成分(南が正)→ x 成分の
    符号反転(元の北向きが東向きになる)。演算の順序が違うので丸めの規模で一致"""
    print("== rot (%s vs %s): the base case rotated by 90 deg clockwise" % (drot, d))

    def rb(path, nx, ny):
        with open(path, "rb") as f:
            v = struct.unpack("<%df" % (nx * ny), f.read())
        return [list(v[j * nx:(j + 1) * nx]) for j in range(ny)]

    # (元の名前, 回した格子の名前, 符号)
    pairs = [("E", "E", 1.0), ("Wh", "Wh", 1.0), ("Wr", "Wr", 1.0), ("u", "v", 1.0), ("v", "u", -1.0),
             ("Wfx", "Wfy", 1.0), ("Wfy", "Wfx", -1.0), ("Wsx", "Wsy", 1.0), ("Wsy", "Wsx", -1.0)]
    vmax = max(abs(x) for x in read_bil(d, "v")[JC])
    for n0, n1, sg in pairs:
        a = rb("%s/%s9998.bil" % (d, n0), NX, NY)
        b = rb("%s/%s9998.bil" % (drot, n1), NY, NX)
        dmax = max(abs(sg * a[j][i] - b[i][NY - 1 - j]) for j in range(NY) for i in range(NX))
        amax = max(abs(a[j][i]) for j in range(NY) for i in range(NX))
        if n0 in ("u", "v"):
            ok = dmax <= 1.0e-3 * vmax
            tol = "1e-3 of max |v|"
        elif n0 == "E":
            ok = dmax <= 1.0e-4
            tol = "1e-4 m"
        else:
            ok = dmax <= 1.0e-3 * amax
            tol = "1e-3 of max"
        check(ok, "rot: %s of the rotated grid matches the base case (max difference %.2e <= %s)" % (n1, dmax, tol))


def main():
    mode = sys.argv[1]
    if mode == "setup":
        check_setup(sys.argv[2])
    elif mode == "flat":
        check_flat(sys.argv[2])
    elif mode == "long":
        check_long(sys.argv[2])
    elif mode == "roller":
        check_roller(sys.argv[2], sys.argv[3])
    elif mode == "rot":
        check_rot(sys.argv[2], sys.argv[3])
    elif mode == "cur":
        check_cur(sys.argv[2], sys.argv[3])
    else:
        raise SystemExit("unknown mode: " + mode)
    if failed:
        print("=== Check_wfcurrent.py %s: %d check(s) FAILED ===" % (mode, len(failed)))
        sys.exit(1)
    print("=== Check_wfcurrent.py %s: PASS ===" % mode)


if __name__ == "__main__":
    main()
