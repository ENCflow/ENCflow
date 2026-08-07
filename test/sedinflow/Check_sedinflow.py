#!/usr/bin/env python3
# sedinflow の台帳検定
#   固体総量 Σhs + (1-λ)Σ(z-z0) が流入土砂総量 C・Q・tt と機械精度で
#   一致することを検定する(濃度指定の流入が「水量×濃度」で厳密に
#   注入されることの直接検証)。定数は param.txt と対で保守する。
#   使い方: Check_sedinflow.py <savedir>
import sys, struct

Z0, PORO = 0.0, 0.4
NX, NY = 101, 101
C0, Q0, TT = 0.001, 5.0, 8.0
TOL = 1.0e-9


def read_rec(f):
    n = struct.unpack("<i", f.read(4))[0]
    payload = f.read(n)
    f.read(4)
    return payload


def read_rle_array(f, ntot):
    n, nrun = struct.unpack("<2q", read_rec(f))
    assert n == ntot
    runs = struct.unpack("<%dq" % (2 * nrun), read_rec(f))
    pk = read_rec(f)
    packed = struct.unpack("<%dd" % (len(pk) // 8), pk)
    out = [0.0] * n
    i = k = 0
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
expected = C0 * Q0 * TT
err = solids - expected
ok = abs(err) < TOL
print("固体総量 = %.15e m3, 期待値 C・Q・tt = %.15e m3" % (solids, expected))
print("差 = %.3e m3 (tol %.0e) : %s" % (err, TOL, "PASS" if ok else "FAIL"))
print("(参考) max(hs) = %.3e m, sum(h) = %.4f m*cell (流入水量 Q・tt = %.1f)"
      % (max(hs), sum(h), Q0 * TT))
print("== sedinflow 検定: %s ==" % ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
