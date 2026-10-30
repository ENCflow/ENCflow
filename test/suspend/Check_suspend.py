#!/usr/bin/env python3
# suspend(浮遊砂)の検定
#   使い方: Check_suspend.py <savedir>               構成 1・2: 疎通・保存則
#           Check_suspend.py eq [savedir resdir]      構成 3: 等流の水路の平衡と適応(平衡濃度式 1)
#           Check_suspend.py eq_ik [savedir resdir]   構成 4: 同(板倉・岸式・Rubey の沈降速度)
#
#   構成 1・2: save/state.dat(ゼロ抑制 RLE。developer.md §7)から z, sd, hs を読み、
#     (1) 固体総量保存: |Σhs + (1-λ)Σ(z-z0)| < TOL_SUM(morfac=1 の
#         E-D 反対称+移流の保存性の帰結)
#     (2) 共動更新恒等: max|(sd - sd0) - (z - z0)| < TOL_SD
#     (3) 活性確認: max(hs) > MIN_HS かつ max|z - z0| > MIN_DZ(空回り検出)
#   を検定する。z0, sd0, λ は param.txt の設定値と対で保守する。
#
#   構成 3・4(developer.md §19.11): savedir/state.dat の h・hs(倍精度)と、resdir の流速 V・
#   浮遊砂 Hs(float32 の bil)を水路の列 i = 2 で読み、
#     (0) 定常・等流: 20〜350 m で h/h_n と V/V_n が 1 ± 1e-5、2400 s と 3600 s の hs の差が
#         相対 1e-5 以下(下流端の低下背水は 400 m より下流)
#     (1) 平衡: 250〜350 m で C = hs/h と C_eq(τ*)/β の比が 1 ± 1e-5
#         (τ* = n² V² / (s d h^{1/3})。C_eq と Rubey の w_f は users guide の式を独立に組む)
#     (2) 適応: 10〜60 m で平衡からの不足 hs_eq − hs の流下方向の減衰率 −ln ρ が、MUSCL と
#         時間の分割を含む離散の予測 ρ = (1 − k)/(1 + k)、k = b / (2c (1 − b))
#         (b = w_f β Δt/h、c = q Δt/(h Δy))に比 1 ± 1e-3 で一致
#   を検定する。水路・流れ・係数は param_eq*.txt・make_eq.py と対で保守する。
import math
import os
import struct
import sys

Z0, SD0, PORO = 0.0, 10.0, 0.4
NX, NY = 101, 101
TOL_SUM, TOL_SD = 1.0e-9, 1.0e-10
MIN_HS, MIN_DZ = 1.0e-7, 1.0e-6

# 構成 3・4 の水路(make_eq.py・param_eq*.txt と対)
EQ_NX, EQ_NY = 3, 1000
EQ_Q, EQ_HN, EQ_N, EQ_DT, EQ_DY = 0.469545, 0.5, 0.03, 0.2, 1.0
SGRAV, GG, D50, NU = 1.65, 9.8, 0.0002, 1.0e-6
EQ_CASES = {
    "eq": dict(form=1, wf=0.02, beta=1.5, esa=1.0e-4, tausc=0.05, save="save_eq", res="result_eq"),
    "eq_ik": dict(form=2, wf=0.0, beta=1.0, save="save_eq_ik", res="result_eq_ik"),
}
EQ_UNI, EQ_PLATEAU, EQ_ADAPT = (20, 350), (250, 350), (10, 60)   # 区間(セル番号 j = 流下距離 m)
TOL_UNI, TOL_STEADY, TOL_EQ, TOL_RATE = 1.0e-5, 1.0e-5, 1.0e-5, 1.0e-3


def read_rec(f):
    n = struct.unpack("<i", f.read(4))[0]
    payload = f.read(n)
    n2 = struct.unpack("<i", f.read(4))[0]
    assert n == n2, "record marker mismatch"
    return payload


def read_rle_array(f, ntot):
    hdr = read_rec(f)
    n, nrun = struct.unpack("<2q", hdr)
    assert n == ntot, "unexpected array size %d != %d" % (n, ntot)
    runs = struct.unpack("<%dq" % (2 * nrun), read_rec(f))
    packed_raw = read_rec(f)
    nd = len(packed_raw) // 8
    packed = struct.unpack("<%dd" % nd, packed_raw)
    out = [0.0] * n
    i = 0
    k = 0
    for r in range(nrun):
        i += runs[2 * r]
        lit = runs[2 * r + 1]
        out[i:i + lit] = packed[k:k + lit]
        i += lit
        k += lit
    return out


def read_state(savedir, ntot):
    with open(savedir + "/state.dat", "rb") as f:
        return [read_rle_array(f, ntot) for _ in range(6)]   # h, z, hrs, hg, sd, hs


def check_conservation(savedir):
    h, z, rsh, hg, sd, hs = read_state(savedir, NX * NY)
    solids = sum(hs) + (1.0 - PORO) * sum(zi - Z0 for zi in z)
    max_dz = max(abs(zi - Z0) for zi in z)
    max_hs = max(hs)
    min_hs = min(hs)
    max_ident = max(abs((sdi - SD0) - (zi - Z0)) for sdi, zi in zip(sd, z))

    ok1 = abs(solids) < TOL_SUM
    ok2 = max_ident < TOL_SD
    ok3 = max_hs > MIN_HS and max_dz > MIN_DZ
    print("(1) 固体総量保存: sum(hs)+(1-λ)sum(z-z0) = %.3e m*cell (tol %.0e) : %s"
          % (solids, TOL_SUM, "PASS" if ok1 else "FAIL"))
    print("(2) 共動更新    : max|(sd-sd0)-(z-z0)| = %.3e m (tol %.0e) : %s"
          % (max_ident, TOL_SD, "PASS" if ok2 else "FAIL"))
    print("(3) 活性確認    : max(hs) = %.3e m, max|z-z0| = %.3e m : %s"
          % (max_hs, max_dz, "PASS" if ok3 else "FAIL"))
    print("    (参考) min(hs) = %.3e m(強い乾燥化での負値は h1 と同種の既知挙動)" % min_hs)
    ok = ok1 and ok2 and ok3
    print("== suspend 検定: %s ==" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


# --- 構成 3・4: 平衡濃度式と沈降速度(users guide sediment.md §4 の式を独立に組む) ---
def rubey_wf(d):
    bb = 36.0 * NU ** 2 / (SGRAV * GG * d ** 3)
    return (math.sqrt(2.0 / 3.0 + bb) - math.sqrt(bb)) * math.sqrt(SGRAV * GG * d)


def ceq_of(cs, taus, wf):
    if cs["form"] == 1:
        return cs["esa"] * (taus / cs["tausc"] - 1.0) if taus > cs["tausc"] else 0.0
    kk, alpha, bstar, eta0 = 0.008, 0.14, 0.143, 0.5        # 板倉・岸の原式の定数
    ap = bstar / taus - 1.0 / eta0
    omega = taus / bstar * math.exp(-ap * ap) / (math.sqrt(math.pi) * math.erfc(ap)) \
        + taus / (bstar * eta0) - 1.0
    ustar = math.sqrt(taus * SGRAV * GG * D50)
    qsu = kk * (alpha / (SGRAV + 1.0) * (SGRAV * GG * D50 / ustar) * omega - wf)
    return max(qsu, 0.0) / wf


def read_bil(resdir, name, k):
    with open(os.path.join(resdir, "%s%04d.bil" % (name, k)), "rb") as f:
        return struct.unpack("<%df" % (EQ_NX * EQ_NY), f.read())


def check_equilibrium(case, savedir=None, resdir=None):
    cs = EQ_CASES[case]
    savedir = savedir or cs["save"]
    resdir = resdir or cs["res"]
    nfail = 0

    def check(ok, msg):
        nonlocal nfail
        print(("  ok   " if ok else "  FAIL ") + msg)
        if not ok:
            nfail += 1

    wf = cs["wf"] if cs["wf"] > 0.0 else rubey_wf(D50)
    beta = cs["beta"]
    print("== suspend %s: erosion-deposition balance in a uniform channel (f_esform = %d, w_f = %.6e m/s%s, beta = %g)"
          % (case, cs["form"], wf, " Rubey" if cs["wf"] <= 0.0 else "", beta))
    h, z, rsh, hg, sd, hs = read_state(savedir, EQ_NX * EQ_NY)
    vv = read_bil(resdir, "V", 9998)
    hs2, hs3 = read_bil(resdir, "Hs", 2), read_bil(resdir, "Hs", 3)
    col = lambda a, j: a[(j - 1) * EQ_NX + 1]          # 水路の列 i = 2、j = 1..ny(北端が流入)
    rng = lambda r: range(r[0], r[1] + 1)

    # (0) 定常・等流
    vn = EQ_Q / EQ_HN
    eh = max(abs(col(h, j) / EQ_HN - 1.0) for j in rng(EQ_UNI))
    ev = max(abs(col(vv, j) / vn - 1.0) for j in rng(EQ_UNI))
    check(eh <= TOL_UNI and ev <= TOL_UNI,
          f"uniform flow over {EQ_UNI[0]}-{EQ_UNI[1]} m: max |h/h_n - 1| = {eh:.1e}, max |V/V_n - 1| = {ev:.1e} "
          f"(h_n = {EQ_HN} m, V_n = {vn:.6f} m/s; limit {TOL_UNI:.0e})")
    es = max(abs(col(hs2, j) / col(hs3, j) - 1.0) for j in range(1, EQ_UNI[1] + 1))
    check(es <= TOL_STEADY, f"steady: hs at 2400 s and 3600 s differ by at most {es:.1e} (relative) over 1-{EQ_UNI[1]} m")

    # (1) 平衡 C = C_eq(τ*)/β
    worst, ceq_mid, taus_mid = 0.0, 0.0, 0.0
    for j in rng(EQ_PLATEAU):
        hh = col(h, j)
        taus = EQ_N ** 2 * col(vv, j) ** 2 / (SGRAV * D50 * hh ** (1.0 / 3.0))
        ceq = ceq_of(cs, taus, wf)
        worst = max(worst, abs((col(hs, j) / hh) / (ceq / beta) - 1.0))
        if j == (EQ_PLATEAU[0] + EQ_PLATEAU[1]) // 2:
            ceq_mid, taus_mid = ceq, taus
    check(worst <= TOL_EQ,
          f"equilibrium over {EQ_PLATEAU[0]}-{EQ_PLATEAU[1]} m: C = hs/h matches C_eq(tau*)/beta within {worst:.1e} "
          f"(tau* = {taus_mid:.5f}, C_eq = {ceq_mid:.6e}; limit {TOL_EQ:.0e})")

    # (2) 適応: 平衡からの不足の流下方向の減衰率
    heq = sum(col(hs, j) for j in rng(EQ_PLATEAU)) / (EQ_PLATEAU[1] - EQ_PLATEAU[0] + 1)
    j1, j2 = EQ_ADAPT
    lam = math.log((heq - col(hs, j1)) / (heq - col(hs, j2))) / (j2 - j1)
    hm = sum(col(h, j) for j in rng(EQ_ADAPT)) / (j2 - j1 + 1)
    b = wf * beta * EQ_DT / hm
    c = EQ_Q * EQ_DT / (hm * EQ_DY)
    k = b / (2.0 * c * (1.0 - b))
    lam_d = -math.log((1.0 - k) / (1.0 + k))
    lam_c = wf * beta * EQ_DY / EQ_Q
    rates = [math.log((heq - col(hs, j)) / (heq - col(hs, j + 1))) for j in range(j1, j2)]
    check(abs(lam / lam_d - 1.0) <= TOL_RATE,
          f"adaptation over {j1}-{j2} m: decay rate of the deficit {lam:.7f} per cell, discrete prediction "
          f"(MUSCL, explicit E-D after advection) {lam_d:.7f} (ratio {lam / lam_d:.6f}, limit 1 +- {TOL_RATE:.0e}; "
          f"continuous w_f beta dy/q = {lam_c:.7f}, ratio {lam / lam_c:.5f})")
    spread = (max(rates) - min(rates)) / lam
    check(spread <= 1.0e-4, f"the deficit decays geometrically (rate in each cell within {spread:.1e} of the mean)")

    print(f"=== suspend {case} check {'PASS' if nfail == 0 else f'FAIL ({nfail})'} ===")
    return 1 if nfail else 0


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] in EQ_CASES:
        sys.exit(check_equilibrium(*sys.argv[1:4]))
    if len(sys.argv) != 2:
        print("usage: Check_suspend.py <savedir> | eq [savedir resdir] | eq_ik [savedir resdir]", file=sys.stderr)
        sys.exit(2)
    sys.exit(check_conservation(sys.argv[1]))
