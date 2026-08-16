#!/usr/bin/env python3
# volcano(火山流動 = 等価流体モード)検定
#   使い方: Check_volcano.py <savedir> <voellmy|tauy>
#
#   voellmy モード(構成1: 定常等流ベンチマーク。param.txt と対):
#     (1) 水台帳  : |Σh − Q・tt| < TOL_SUM(閉領域・f_dbed=0)
#     (2) 固体台帳: |Σhs + (1-λ)Σ(z-z0) − cs・Q・tt| < TOL_SUM
#     (3) 解析解  : 検定窓(x∈[60,100])の流動深 h_t = h+hs の平均が
#                   h_ana = (q_m²/(ξ(tanθ−μ)))^(1/3) に相対 TOL_ANA 以内、
#                   窓内の変動係数 < TOL_CV(等流性)、濃度 C ≈ cs/(1+cs)
#   tauy モード(構成2: ランアウト・停止。param_ty.txt と対):
#     (1) 固体台帳: |Σhs + (1-λ)Σ(z-z0)| < TOL_SUM(放出・凝集とも内部移転)
#     (2) 活性    : 放出域の地盤低下 min(dz) < -1、平坦部(x>=30)の
#                   堆積 max(dz) > MIN_DEP(斜面からのランアウト)
#     (3) 停止    : 残存 Σhs / 放出固体量 < FRAC_STOP(凝集による河床固定)
import sys, struct

TOL_SUM = 1.0e-9
# --- 構成1(param.txt と対で保守)---
NX1, NY1, DX1 = 150, 8, 1.0
ST1, LX1 = 0.2, 150.0            # 斜面 tanθ, 全長(make_init.py z と対)
QIN, CSIN, TT1 = 4.0, 0.8, 120.0 # 流入 (m3/s), 濃度 (hs/h), 継続 (s)
XI, MU = 200.0, 0.1              # Voellmy ξ, μ
IW1, IW2 = 60, 100               # 検定窓(等流到達・末端プールの外)
TOL_ANA, TOL_CV = 0.03, 0.05
# --- 構成2(param_ty.txt と対で保守)---
NX2, NY2, DX2 = 60, 20, 1.0
ST2, XB2 = 0.4, 30.0             # slope_break(user_geoinfo と対)
REL_I, REL_J, REL_D = (5, 15), (8, 13), 2.0
MIN_DEP, FRAC_STOP = 1.0e-2, 0.3
PORO = 0.4


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


def load(savedir, nx, ny):
    ntot = nx * ny
    with open(savedir + "/state.dat", "rb") as f:
        h = read_rle_array(f, ntot)
        z = read_rle_array(f, ntot)
        read_rle_array(f, ntot)     # hrs
        read_rle_array(f, ntot)     # hg
        sd = read_rle_array(f, ntot)
        hs = read_rle_array(f, ntot)
    return h, z, sd, hs


savedir = sys.argv[1]
mode = sys.argv[2]
ok = True

if mode == "voellmy":
    h, z, sd, hs = load(savedir, NX1, NY1)
    ntot = NX1 * NY1

    def z0_of(idx):
        x = (idx % NX1 + 0.5) * DX1
        return ST1 * (LX1 - x)
    dz = [zi - z0_of(idx) for idx, zi in enumerate(z)]
    wres = sum(h) - QIN * TT1
    sres = sum(hs) + (1.0 - PORO) * sum(dz) - CSIN * QIN * TT1
    ok1 = abs(wres) < TOL_SUM
    ok2 = abs(sres) < TOL_SUM
    print("(1) 水台帳  : sum(h) - Q*tt = %.3e m*cell (tol %.0e) : %s"
          % (wres, TOL_SUM, "PASS" if ok1 else "FAIL"))
    print("(2) 固体台帳: sum(hs)+(1-λ)sum(dz) - cs*Q*tt = %.3e m*cell (tol %.0e) : %s"
          % (sres, TOL_SUM, "PASS" if ok2 else "FAIL"))
    # 解析解(単位幅の混合体流量 q_m = Q(1+cs)/ly)
    qm = QIN * (1.0 + CSIN) / NY1
    hana = (qm * qm / (XI * (ST1 - MU))) ** (1.0 / 3.0)
    win = [idx for idx in range(ntot) if IW1 <= (idx % NX1 + 0.5) * DX1 <= IW2]
    ht = [h[idx] + hs[idx] for idx in win]
    mean = sum(ht) / len(ht)
    cv = (sum((x - mean) ** 2 for x in ht) / len(ht)) ** 0.5 / mean
    cmix = sum(hs[idx] for idx in win) / sum(h[idx] + hs[idx] for idx in win)
    cana = CSIN / (1.0 + CSIN)
    err = abs(mean - hana) / hana
    ok3 = err < TOL_ANA and cv < TOL_CV and abs(cmix - cana) < 0.02
    print("(3) 解析解  : <h_t> = %.4f m vs %.4f m (err %.1f%%, tol %.0f%%), "
          "CV = %.3f, C = %.3f (理論 %.3f) : %s"
          % (mean, hana, 100 * err, 100 * TOL_ANA, cv, cmix, cana,
             "PASS" if ok3 else "FAIL"))
    ok = ok1 and ok2 and ok3
else:
    h, z, sd, hs = load(savedir, NX2, NY2)
    ntot = NX2 * NY2

    def z0_of(idx):
        x = (idx % NX2 + 0.5) * DX2
        return ST2 * (XB2 - x) if x < XB2 else 0.0
    dz = [zi - z0_of(idx) for idx, zi in enumerate(z)]
    sres = sum(hs) + (1.0 - PORO) * sum(dz)
    ok1 = abs(sres) < TOL_SUM
    print("(1) 固体台帳: sum(hs)+(1-λ)sum(dz) = %.3e m*cell (tol %.0e) : %s"
          % (sres, TOL_SUM, "PASS" if ok1 else "FAIL"))
    rel = [idx for idx in range(ntot)
           if REL_I[0] <= idx % NX2 + 1 <= REL_I[1]
           and REL_J[0] <= idx // NX2 + 1 <= REL_J[1]]
    flat = [idx for idx in range(ntot) if (idx % NX2 + 0.5) * DX2 >= XB2]
    ero = min(dz[idx] for idx in rel)
    dep = max(dz[idx] for idx in flat)
    ok2 = ero < -1.0 and dep > MIN_DEP
    print("(2) 活性    : 放出域 min dz = %.3f m, 平坦部 max dz = %.3e m : %s"
          % (ero, dep, "PASS" if ok2 else "FAIL"))
    solids = (1.0 - PORO) * REL_D * len(rel)
    frac = sum(hs) / solids
    ok3 = frac < FRAC_STOP
    print("(3) 停止    : 残存 sum(hs)/放出固体 = %.3f (tol %.2f) : %s"
          % (frac, FRAC_STOP, "PASS" if ok3 else "FAIL"))
    ok = ok1 and ok2 and ok3

print("== volcano 検定: %s ==" % ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
