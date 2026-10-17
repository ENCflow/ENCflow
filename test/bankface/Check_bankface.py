#!/usr/bin/env python3
# bankface 検定(developer.md §84.1・§84.2)
#   save/state.dat(ゼロ抑制 RLE)から z, sd を読み、make_init.py の地形と対で
#     (1) 土砂体積保存: |Σ(z − z0)| < TOL_SUM(閉領域・反対称フラックスの帰結。
#         param_thin では供給量制限が発動した上で成立することが要点)
#     (2) 河岸面の遮断: 乾いた河岸セル(水面より 2 m 高い)の |z − z0| が厳密に 0
#         (掃流砂は水面より上へ登らず、乾いたセルは供給しない)
#     (3) 共動更新恒等: max|(sd − sd0) − (z − z0)| < TOL_SD
#     (4) 活性確認: 水路内の max|z − z0| > MIN_ACT
#     (5) 可動層の下限: min sd >= 0(param_thin。供給量制限が床を割らない)
#   使い方: Check_bankface.py <savedir> <sd0>
import sys, struct
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from make_init import NX, NY, z_of, h_of

TOL_SUM, TOL_SD, MIN_ACT = 1.0e-9, 1.0e-10, 1.0e-4


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
    i = k = 0
    for r in range(nrun):
        i += runs[2 * r]
        lit = runs[2 * r + 1]
        out[i:i + lit] = packed[k:k + lit]
        i += lit
        k += lit
    return out


savedir, sd0 = sys.argv[1], float(sys.argv[2])
with open(savedir + "/state.dat", "rb") as f:
    ntot = NX * NY
    h = read_rle_array(f, ntot)
    z = read_rle_array(f, ntot)
    rsh = read_rle_array(f, ntot)
    hg = read_rle_array(f, ntot)
    sd = read_rle_array(f, ntot)

# 配列は行(j)優先で並ぶ(1 行 = nx 個)
dz = [z[(j - 1) * NX + (i - 1)] - z_of(i, j) for j in range(1, NY + 1) for i in range(1, NX + 1)]
dry = [h_of(i, j) <= 0.0 for j in range(1, NY + 1) for i in range(1, NX + 1)]
sum_dz = sum(dz)
max_dz_dry = max(abs(d) for d, q in zip(dz, dry) if q)
max_dz_wet = max(abs(d) for d, q in zip(dz, dry) if not q)
max_ident = max(abs((s - sd0) - d) for s, d in zip(sd, dz))
min_sd = min(sd)

ok1 = abs(sum_dz) < TOL_SUM
ok2 = max_dz_dry == 0.0
ok3 = max_ident < TOL_SD
ok4 = max_dz_wet > MIN_ACT
ok5 = min_sd >= 0.0
print("(1) 体積保存     : sum(z - z0) = %.3e m*cell (tol %.0e) : %s" % (sum_dz, TOL_SUM, "PASS" if ok1 else "FAIL"))
print("(2) 河岸面の遮断 : max|z - z0| on dry banks = %.3e m (must be 0) : %s" % (max_dz_dry, "PASS" if ok2 else "FAIL"))
print("(3) 共動更新     : max|(sd-sd0)-(z-z0)| = %.3e m (tol %.0e) : %s" % (max_ident, TOL_SD, "PASS" if ok3 else "FAIL"))
print("(4) 活性確認     : max|z - z0| in channel = %.3e m (min %.0e) : %s" % (max_dz_wet, MIN_ACT, "PASS" if ok4 else "FAIL"))
print("(5) 可動層下限   : min sd = %.3e m (>= 0) : %s" % (min_sd, "PASS" if ok5 else "FAIL"))
ok = ok1 and ok2 and ok3 and ok4 and ok5
print("== bankface 検定 (%s, sd0=%g): %s ==" % (savedir, sd0, "PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
