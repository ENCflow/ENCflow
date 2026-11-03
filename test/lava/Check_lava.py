#!/usr/bin/env python3
# lava(溶岩流 = Bingham 粘性重力流)検定
#   使い方: Check_lava.py <savedir> <huppert|bingham|dome|wall>
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
#   dome モード(構成4: 塑性ドームの静止形。param_dome.txt と対):
#     (1) 台帳    : |Σhl − V_in/A_cell| < TOL_SUM(固化なし)
#     (2) 等方性  : 格子軸の方向(±22.5°)と斜めの方向(±22.5°)の扇形の
#                   面積等価半径の比が 1 に相対 TOL_ISO 以内
#     (3) 解析解  : h(r)² = a(R − r)(a = 2τ_y/ρg、V = (8π/15)√a R^{5/2})
#                   に対し、中心厚が H = √(aR) に相対 TOL_H4、面積等価
#                   半径が R に相対 TOL_R4 以内、r < R の RMS 誤差 < TOL_RMS4·H
#   wall モード(構成5: 壁の前の溶岩だまりの固化。param_wall.txt と対):
#     (1) 台帳    : |Σhl + Σ(z−z0) − V_in/A_cell| < TOL_SUM
#     (2) 全量固化: Σdz / 注入 > FRAC_SOL5
#     (3) 壁際    : 壁に接する列(i = IW5)の全行で hl = 0 かつ
#                   dz > FRAC_WALL5 × max dz
import sys, struct, math

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
# --- 構成4(param_dome.txt と対で保守)---
NX4, NY4, DX4 = 61, 61, 1.0
IC4, JC4 = 31, 31                # 噴火口のセル(1 始まり)
Q4, TSUP4, DT4, TT4 = 2.0, 900.0, 1.0, 6000.0
RHO4, TAUY4 = 2600.0, 1.0e4
HL_EPS4 = 0.01                   # 広がりの判定厚 (m)
TOL_ISO, TOL_H4, TOL_R4, TOL_RMS4 = 0.05, 0.05, 0.05, 0.05
# --- 構成5(param_wall.txt・make_init.py wall と対で保守)---
NX5, NY5, DX5 = 40, 8, 1.0
IWALL5, ZWALL5 = 31, 10.0        # 段(壁)の始まりの列と高さ
IW5 = IWALL5 - 1                 # 壁に接する列
Q5, TSUP5, DT5, TT5 = 0.2, 300.0, 0.5, 4800.0
FRAC_SOL5, FRAC_WALL5 = 0.999, 0.5


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
elif mode == "dome":
    hl = load_hl(savedir, NX4, NY4)
    area = DX4 * DX4
    # (1) 台帳(注入は t < TSUP4 の tick ごとに Q4*dt の厳密加算。固化なし)
    nt = round(TT4 / DT4)
    vin = sum(Q4 * DT4 for it in range(1, nt + 1) if it * DT4 < TSUP4)
    res = sum(hl) * area - vin
    ok1 = abs(res) < TOL_SUM * vin
    print("(1) 台帳  : sum(hl)*A - V_in = %.3e m3 (V_in = %.1f, tol %.0e 相対) : %s"
          % (res, vin, TOL_SUM, "PASS" if ok1 else "FAIL"))
    # セルの中心から噴火口までの距離と方位(0〜90°に畳む)
    cells = []
    for idx, h in enumerate(hl):
        i = idx % NX4 + 1
        j = idx // NX4 + 1
        dx_ = (i - IC4) * DX4
        dy_ = (j - JC4) * DX4
        r = math.hypot(dx_, dy_)
        th = math.degrees(math.atan2(abs(dy_), abs(dx_)))
        cells.append((h, r, th))
    # (2) 等方性: 扇形群(4 扇形 × 45° = π)の面積等価半径 √(2 N A/π)
    nax = sum(1 for h, r, th in cells if h > HL_EPS4 and r > 0.0 and (th < 22.5 or th > 67.5))
    ndg = sum(1 for h, r, th in cells if h > HL_EPS4 and 22.5 <= th <= 67.5)
    rax = (2.0 * nax * area / math.pi) ** 0.5
    rdg = (2.0 * ndg * area / math.pi) ** 0.5
    ratio = rdg / rax
    ok2 = abs(ratio - 1.0) < TOL_ISO
    print("(2) 等方性: 面積等価半径 斜め %.2f m / 格子軸 %.2f m = %.3f (tol 1±%.2f) : %s"
          % (rdg, rax, ratio, TOL_ISO, "PASS" if ok2 else "FAIL"))
    # (3) 塑性ドームの解析解
    a = 2.0 * TAUY4 / (RHO4 * GG)
    rr = (vin / ((8.0 * math.pi / 15.0) * a ** 0.5)) ** 0.4
    hh = (a * rr) ** 0.5
    hc = hl[(JC4 - 1) * NX4 + (IC4 - 1)]
    ra = r_area(hl, HL_EPS4, area)
    sq = [(h - (a * (rr - r)) ** 0.5) ** 2 for h, r, th in cells if r < rr]
    rms = (sum(sq) / len(sq)) ** 0.5
    eh = (hc - hh) / hh
    er = (ra - rr) / rr
    ok3 = abs(eh) < TOL_H4 and abs(er) < TOL_R4 and rms < TOL_RMS4 * hh
    print("(3) 解析解: 中心厚 %.3f m vs H = %.3f m (err %+.1f%%)、r_A = %.2f m vs R = %.2f m "
          "(err %+.1f%%)、RMS = %.3f m (%.1f%% of H)(tol %.0f%%) : %s"
          % (hc, hh, 100 * eh, ra, rr, 100 * er, rms, 100 * rms / hh, 100 * TOL_H4,
             "PASS" if ok3 else "FAIL"))
    ok = ok1 and ok2 and ok3
elif mode == "wall":
    hl = load_hl(savedir, NX5, NY5)
    z = load_z(savedir, NX5, NY5)
    area = DX5 * DX5
    dz = [zi - (ZWALL5 if idx % NX5 + 1 >= IWALL5 else 0.0) for idx, zi in enumerate(z)]
    nt = round(TT5 / DT5)
    vin = sum(Q5 * DT5 for it in range(1, nt + 1) if it * DT5 < TSUP5)
    # (1) 台帳(固化は hl → z の内部移転)
    res = (sum(hl) + sum(dz)) * area - vin
    ok1 = abs(res) < TOL_SUM * vin
    print("(1) 台帳  : (sum(hl)+sum(dz))*A - V_in = %.3e m3 (V_in = %.2f, tol %.0e 相対) : %s"
          % (res, vin, TOL_SUM, "PASS" if ok1 else "FAIL"))
    # (2) 全量の固化
    frac = sum(dz) * area / vin
    ok2 = frac > FRAC_SOL5
    print("(2) 固化  : sum(dz)*A/V_in = %.4f (tol > %.3f)、残る溶岩 max hl = %.3e m : %s"
          % (frac, FRAC_SOL5, max(hl), "PASS" if ok2 else "FAIL"))
    # (3) 壁に接する列の全行が固化して地形になった
    dzmax = max(dz)
    hw = [hl[(j - 1) * NX5 + (IW5 - 1)] for j in range(1, NY5 + 1)]
    dw = [dz[(j - 1) * NX5 + (IW5 - 1)] for j in range(1, NY5 + 1)]
    ok3 = max(hw) <= 0.0 and min(dw) > FRAC_WALL5 * dzmax
    print("(3) 壁際  : 列 i = %d の max hl = %.3e m、min dz = %.3f m(max dz %.3f m の %.0f%% 超) : %s"
          % (IW5, max(hw), min(dw), dzmax, 100 * FRAC_WALL5, "PASS" if ok3 else "FAIL"))
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
