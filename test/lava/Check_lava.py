#!/usr/bin/env python3
# lava(溶岩流 = Bingham 粘性重力流)検定
#   使い方: Check_lava.py <savedir> <huppert|bingham>
#
#   huppert モード(構成1: Newton 極限の相似解。param.txt と対):
#     (1) 台帳    : |Σhl − V_in/A_cell| < TOL_SUM(注入は厳密加算・
#                   拡散はエッジ反対称 = 機械精度で保存)
#     (2) 解析解  : 面積等価半径 r_A = √(N_wet dx dy/π) が
#                   r_N = 0.715 (g Q³/3ν)^{1/8} √t に相対 TOL_ANA 以内
#     (3) 成長則  : r_A(tt)/r_A(tt/2) が √2 に相対 TOL_GROW 以内
#   bingham モード(構成2: 停止・固化。param_ty.txt と対):
#     (1) 台帳    : |Σhl + Σ(z−z0) − V_in/A_cell| < TOL_SUM(固化は
#                   z への内部移転)
#     (2) 停止厚  : 検定窓の hl+dz の平均が h∞ = τ_y/(ρg tanθ) に
#                   相対 TOL_HINF 以内、変動係数 < TOL_CV
#     (3) 固化    : Σdz / 注入 > FRAC_SOL かつ max dz > MIN_DZ
import sys, struct

TOL_SUM = 1.0e-8
GG = 9.8
# --- 構成1(param.txt と対で保守)---
NX1, NY1, DX1 = 61, 61, 1.0
Q1, T1, DT1 = 0.5, 600.0, 0.5    # 噴出率 (m3/s), 継続 (s), dt (s)
RHO1, VISC1 = 2600.0, 2.0e4
HL_EPS = 1.0e-6                  # wet 判定の溶岩厚閾値 (m)
TOL_ANA, TOL_GROW = 0.10, 0.05
# --- 構成2(param_ty.txt と対で保守)---
NX2, NY2, DX2 = 100, 8, 1.0
ST2, LX2 = 0.2, 100.0            # 斜面 tanθ, 全長(make_init.py と対)
Q2, TSUP, DT2, TT2 = 0.5, 300.0, 0.5, 1200.0
RHO2, TAUY2 = 2600.0, 2000.0
IW1, IW2 = 15, 35                # 検定窓(セル番号 i。噴火口の下流・前縁の後方)
TOL_HINF, TOL_CV = 0.20, 0.15
FRAC_SOL, MIN_DZ = 0.7, 0.2


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
    packed = struct.unpack("<%dd" % (len(packed_raw) // 8), packed_raw)
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


def load_hl(savedir, nx, ny):
    with open(savedir + "/lavaflow.dat", "rb") as f:
        return read_rle_array(f, nx * ny)


def load_z(savedir, nx, ny):
    ntot = nx * ny
    with open(savedir + "/state.dat", "rb") as f:
        read_rle_array(f, ntot)     # h
        z = read_rle_array(f, ntot)
    return z


def load_txt(fname, nx, ny):
    out = []
    with open(fname) as f:
        for line in f:
            out.extend(float(v) for v in line.split())
    assert len(out) == nx * ny, "unexpected matrix size in " + fname
    return out


def r_area(hl, eps, dxdy):
    nwet = sum(1 for v in hl if v > eps)
    return (nwet * dxdy / 3.141592653589793) ** 0.5


savedir = sys.argv[1]
mode = sys.argv[2]
ok = True

if mode == "huppert":
    hl = load_hl(savedir, NX1, NY1)
    # (1) 台帳(注入は毎ステップ q0*dt の厳密加算)
    vin = Q1 * DT1 * round(T1 / DT1)          # m3(一定噴出率)
    res = sum(hl) * DX1 * DX1 - vin
    ok1 = abs(res) < TOL_SUM * vin
    print("(1) 台帳  : sum(hl)*A - V_in = %.3e m3 (tol %.0e 相対) : %s"
          % (res, TOL_SUM, "PASS" if ok1 else "FAIL"))
    # (2) 先端半径(面積等価)vs Huppert 相似解
    nu = VISC1 / RHO1
    rana = 0.715 * (GG * Q1 ** 3 / (3.0 * nu)) ** 0.125 * T1 ** 0.5
    ra = r_area(hl, HL_EPS, DX1 * DX1)
    err = abs(ra - rana) / rana
    ok2 = err < TOL_ANA
    print("(2) 解析解: r_A = %.2f m vs r_N = %.2f m (err %.1f%%, tol %.0f%%) : %s"
          % (ra, rana, 100 * err, 100 * TOL_ANA, "PASS" if ok2 else "FAIL"))
    # (3) 成長則 r ∝ t^{1/2}(中間時刻の分布出力 Hl0002 = tt/2)
    hl2 = load_txt("result/Hl0002.txt", NX1, NY1)
    ratio = ra / r_area(hl2, HL_EPS, DX1 * DX1)
    err = abs(ratio - 2.0 ** 0.5) / 2.0 ** 0.5
    ok3 = err < TOL_GROW
    print("(3) 成長則: r(tt)/r(tt/2) = %.3f vs √2 (err %.1f%%, tol %.0f%%) : %s"
          % (ratio, 100 * err, 100 * TOL_GROW, "PASS" if ok3 else "FAIL"))
    ok = ok1 and ok2 and ok3
else:
    hl = load_hl(savedir, NX2, NY2)
    z = load_z(savedir, NX2, NY2)
    ntot = NX2 * NY2

    def z0_of(idx):
        x = (idx % NX2 + 0.5) * DX2
        return ST2 * (LX2 - x)
    dz = [zi - z0_of(idx) for idx, zi in enumerate(z)]
    # 注入量: interp_series は重複時刻 (5,0.5),(5,0.0) で t=300s から 0
    #   → q = Q2 (t < TSUP), 0 (t >= TSUP)。tick 時刻 t = it*dt で厳密再現
    nt = round(TT2 / DT2)
    vin = sum(Q2 * DT2 for it in range(1, nt + 1) if it * DT2 < TSUP)
    # (1) 台帳(固化は hl → z の内部移転)
    res = (sum(hl) + sum(dz)) * DX2 * DX2 - vin
    ok1 = abs(res) < TOL_SUM * vin
    print("(1) 台帳  : (sum(hl)+sum(dz))*A - V_in = %.3e m3 (V_in = %.2f, "
          "tol %.0e 相対) : %s" % (res, vin, TOL_SUM, "PASS" if ok1 else "FAIL"))
    # (2) 停止厚 h∞ = τ_y/(ρg tanθ)(検定窓の hl+dz)
    hinf = TAUY2 / (RHO2 * GG * ST2)
    win = [idx for idx in range(ntot) if IW1 <= idx % NX2 + 1 <= IW2]
    ht = [hl[idx] + dz[idx] for idx in win]
    mean = sum(ht) / len(ht)
    cv = (sum((x - mean) ** 2 for x in ht) / len(ht)) ** 0.5 / mean
    err = abs(mean - hinf) / hinf
    ok2 = err < TOL_HINF and cv < TOL_CV
    print("(2) 停止厚: <hl+dz> = %.4f m vs h∞ = %.4f m (err %.1f%%, tol %.0f%%), "
          "CV = %.3f : %s"
          % (mean, hinf, 100 * err, 100 * TOL_HINF, cv, "PASS" if ok2 else "FAIL"))
    # (3) 固化の活性
    frac = sum(dz) * DX2 * DX2 / vin
    dzmax = max(dz)
    ok3 = frac > FRAC_SOL and dzmax > MIN_DZ
    print("(3) 固化  : sum(dz)*A/V_in = %.3f (tol > %.2f), max dz = %.3f m "
          "(tol > %.1f) : %s"
          % (frac, FRAC_SOL, dzmax, MIN_DZ, "PASS" if ok3 else "FAIL"))
    ok = ok1 and ok2 and ok3

print("== lava 検定: %s ==" % ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
