#!/usr/bin/env python3
# fluvial 疎通・保存則検定
#   save/state.dat(ゼロ抑制 RLE。developer.md §7)から z, sd を読み、
#     (1) 土砂体積保存: |Σ(z - z0)| < TOL_SUM(反対称フラックスの帰結)
#     (2) 共動更新恒等: max|(sd - sd0) - (z - z0)| < TOL_SD
#     (3) 活性確認:     max|z - z0| > MIN_ACT(空回りの検出)
#   を検定する。z0, sd0 は param.txt の設定値と対で保守する。
#   使い方: Check_fluvial.py <savedir>
import sys, struct

Z0, SD0 = 0.0, 10.0
NX, NY = 101, 101
TOL_SUM, TOL_SD, MIN_ACT = 1.0e-9, 1.0e-10, 1.0e-4


def read_rec(f):
    # gfortran の unformatted sequential(4バイトレコードマーカー)
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


savedir = sys.argv[1]
with open(savedir + "/state.dat", "rb") as f:
    ntot = NX * NY
    h = read_rle_array(f, ntot)
    z = read_rle_array(f, ntot)
    rsh = read_rle_array(f, ntot)
    hg = read_rle_array(f, ntot)
    sd = read_rle_array(f, ntot)

sum_dz = sum(zi - Z0 for zi in z)
max_dz = max(abs(zi - Z0) for zi in z)
max_ident = max(abs((sdi - SD0) - (zi - Z0)) for sdi, zi in zip(sd, z))

ok1 = abs(sum_dz) < TOL_SUM
ok2 = max_ident < TOL_SD
ok3 = max_dz > MIN_ACT
print("(1) 体積保存   : sum(z - z0) = %.3e m*cell (tol %.0e) : %s"
      % (sum_dz, TOL_SUM, "PASS" if ok1 else "FAIL"))
print("(2) 共動更新   : max|(sd-sd0)-(z-z0)| = %.3e m (tol %.0e) : %s"
      % (max_ident, TOL_SD, "PASS" if ok2 else "FAIL"))
print("(3) 活性確認   : max|z - z0| = %.3e m (min %.0e) : %s"
      % (max_dz, MIN_ACT, "PASS" if ok3 else "FAIL"))
ok = ok1 and ok2 and ok3
print("== fluvial 検定: %s ==" % ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
