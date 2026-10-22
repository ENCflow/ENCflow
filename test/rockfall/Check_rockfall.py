#!/usr/bin/env python3
# rockfall 検定(developer.md §48.7)
#   save/state.dat から z, sd を、result/Ht9998.txt から崖錐の厚さを読み、
#     (1) 土砂体積保存: |Σ(z − z0)| < TOL_SUM
#     (2) 終端の最大高さ差(軸 4 方向・対角 4 方向)<= H_c + TOL_H(崩落で自由面が限界以下)
#     (3) 崖錐の収支: 全セルで ht >= (z − z0)^+ − TOL_HT(正味の堆積は崖錐)、Σht > 0
#     (4) 共動更新恒等: max|(sd − sd0) − (z − z0)| < TOL_SD
#   使い方: Check_rockfall.py <savedir>
import sys, struct, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_init import NX, NY, ZTOP

HC, SD0 = 4.0, 20.0
TOL_SUM, TOL_H, TOL_HT, TOL_SD = 1.0e-9, 1.0e-3, 2.0e-4, 1.0e-10   # 高さ差は relax の幾何収束の残差(1e-4 程度)を許す。ht は印字桁 1e-4 m の出力から


def read_rec(f):
    n = struct.unpack("<i", f.read(4))[0]
    payload = f.read(n)
    n2 = struct.unpack("<i", f.read(4))[0]
    assert n == n2, "record marker mismatch"
    return payload


def read_rle_array(f, ntot):
    n, nrun = struct.unpack("<2q", read_rec(f))
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


z0 = [[float(v) for v in line.split()] for line in open("zinit.txt")]
with open(sys.argv[1] + "/state.dat", "rb") as f:
    ntot = NX * NY
    read_rle_array(f, ntot)
    zf = read_rle_array(f, ntot)
    read_rle_array(f, ntot)
    read_rle_array(f, ntot)
    sd = read_rle_array(f, ntot)
z = [[zf[(j - 1) * NX + (i - 1)] for i in range(1, NX + 1)] for j in range(1, NY + 1)]
ht = [[float(v) for v in line.split()] for line in open("result/Ht9998.txt")]
dz = [[z[j][i] - z0[j][i] for i in range(NX)] for j in range(NY)]
sum_dz = sum(sum(r) for r in dz)
hmax = 0.0
for j in range(NY):
    for i in range(NX):
        for di, dj in ((1, 0), (0, 1), (1, 1), (-1, 1)):
            ii, jj = i + di, j + dj
            if 0 <= ii < NX and 0 <= jj < NY:
                hmax = max(hmax, abs(z[jj][ii] - z[j][i]))
zmax = max(max(r) for r in z)
ident = max(abs((sd[j * NX + i] - SD0) - dz[j][i]) for j in range(NY) for i in range(NX))
htdef = min(ht[j][i] - max(dz[j][i], 0.0) for j in range(NY) for i in range(NX))
sum_ht = sum(sum(r) for r in ht)
sum_dep = sum(max(v, 0.0) for r in dz for v in r)
ok1 = abs(sum_dz) < TOL_SUM
ok2 = hmax <= HC + TOL_H
ok3 = htdef >= -TOL_HT and sum_ht > 0.0
ok4 = ident < TOL_SD
print("(1) 体積保存   : sum(z - z0) = %.3e m*cell (tol %.0e) : %s" % (sum_dz, TOL_SUM, "PASS" if ok1 else "FAIL"))
print("(2) 最大高さ差 : %.6f <= H_c = %g m : %s  (頂 %.2f -> %.3f m)" % (hmax, HC, "PASS" if ok2 else "FAIL", ZTOP, zmax))
print("(3) 崖錐の収支 : min(ht - (z-z0)^+) = %.2e m, Σht = %.2f, Σ(z-z0)^+ = %.2f m*cell : %s"
      % (htdef, sum_ht, sum_dep, "PASS" if ok3 else "FAIL"))
print("(4) 共動更新   : max|(sd-sd0)-(z-z0)| = %.3e m : %s" % (ident, "PASS" if ok4 else "FAIL"))
ok = ok1 and ok2 and ok3 and ok4
print("== rockfall 検定: %s ==" % ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
