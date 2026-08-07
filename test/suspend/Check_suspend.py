#!/usr/bin/env python3
# suspend(浮遊砂)疎通・保存則検定
#   save/state.dat(ゼロ抑制 RLE。developer.md §7)から z, sd, hs を読み、
#     (1) 固体総量保存: |Σhs + (1-λ)Σ(z-z0)| < TOL_SUM(morfac=1 の
#         E-D 反対称+移流の保存性の帰結)
#     (2) 共動更新恒等: max|(sd - sd0) - (z - z0)| < TOL_SD
#     (3) 活性確認: max(hs) > MIN_HS かつ max|z - z0| > MIN_DZ(空回り検出)
#   を検定する。z0, sd0, λ は param.txt の設定値と対で保守する。
#   使い方: Check_suspend.py <savedir>
import sys, struct

Z0, SD0, PORO = 0.0, 10.0, 0.4
NX, NY = 101, 101
TOL_SUM, TOL_SD = 1.0e-9, 1.0e-10
MIN_HS, MIN_DZ = 1.0e-7, 1.0e-6


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


savedir = sys.argv[1]
with open(savedir + "/state.dat", "rb") as f:
    ntot = NX * NY
    h = read_rle_array(f, ntot)
    z = read_rle_array(f, ntot)
    rsh = read_rle_array(f, ntot)
    hg = read_rle_array(f, ntot)
    sd = read_rle_array(f, ntot)
    hs = read_rle_array(f, ntot)

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
sys.exit(0 if ok else 1)
