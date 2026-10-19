#!/usr/bin/env python3
# repose 検定(developer.md §84.4)
#   save/state.dat から z, sd を読み、
#     (1) 土砂体積保存: |Σ(z − z0)| < TOL_SUM
#     (2) 終端の最大勾配(軸 4 方向・対角 4 方向)<= tanφ_r + TOL_SLOPE
#     (3) 活性: 頂上が ZTOP より MIN_DROP 以上下がる
#     (4) 共動更新恒等: max|(sd − sd0) − (z − z0)| < TOL_SD
#   使い方: Check_repose.py <savedir>
import sys, struct, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_init import NX, NY, DX, ZTOP

PHI, SD0 = 30.0, 10.0
TOL_SUM, TOL_SLOPE, MIN_DROP, TOL_SD = 1.0e-9, 1.0e-4, 0.5, 1.0e-10   # 勾配は relax の幾何収束の残差(1e-7 程度)を許す


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
dz = [[z[j][i] - z0[j][i] for i in range(NX)] for j in range(NY)]
sum_dz = sum(sum(r) for r in dz)
tanphi = math.tan(math.radians(PHI))
smax = 0.0
dd = math.sqrt(2.0) * DX
for j in range(NY):
    for i in range(NX):
        if i + 1 < NX:
            smax = max(smax, abs(z[j][i + 1] - z[j][i]) / DX)
        if j + 1 < NY:
            smax = max(smax, abs(z[j + 1][i] - z[j][i]) / DX)
        if i + 1 < NX and j + 1 < NY:
            smax = max(smax, abs(z[j + 1][i + 1] - z[j][i]) / dd)
        if i > 0 and j + 1 < NY:
            smax = max(smax, abs(z[j + 1][i - 1] - z[j][i]) / dd)
zmax = max(max(r) for r in z)
ident = max(abs((sd[(j) * NX + i] - SD0) - dz[j][i]) for j in range(NY) for i in range(NX))
ok1 = abs(sum_dz) < TOL_SUM
ok2 = smax <= tanphi + TOL_SLOPE
ok3 = ZTOP - zmax > MIN_DROP
ok4 = ident < TOL_SD
print("(1) 体積保存   : sum(z - z0) = %.3e m*cell (tol %.0e) : %s" % (sum_dz, TOL_SUM, "PASS" if ok1 else "FAIL"))
print("(2) 最大勾配   : %.6f <= tan(%g deg) = %.6f : %s" % (smax, PHI, tanphi, "PASS" if ok2 else "FAIL"))
print("(3) 活性確認   : peak %.2f -> %.3f m (drop > %.1f) : %s" % (ZTOP, zmax, MIN_DROP, "PASS" if ok3 else "FAIL"))
print("(4) 共動更新   : max|(sd-sd0)-(z-z0)| = %.3e m : %s" % (ident, "PASS" if ok4 else "FAIL"))
ok = ok1 and ok2 and ok3 and ok4
print("== repose 検定: %s ==" % ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
