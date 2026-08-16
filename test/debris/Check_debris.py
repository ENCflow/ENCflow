#!/usr/bin/env python3
# debris(土石流 E-D)疎通・保存則検定
#   save/state.dat(ゼロ抑制 RLE。developer.md §7)から z, sd, hs を読み、
#     (1) 固体総量保存: |Σhs + (1-λ)Σ(z-z0)| < TOL_SUM(E-D 反対称の帰結)
#     (2) 共動更新恒等: max|(sd - sd0) - (z - z0)| < TOL_SD
#     (3) 活性確認: 斜面部の侵食 min(dz) < -MIN_ERO かつ
#         遷緩点(i>=30)下流の堆積 max(dz) > MIN_DEP
#   を検定する。z0 は slope_break(tanθ=0.4, 遷緩点 x=30m)、sd0, λ は
#   param.txt と対で保守する。
#   使い方: Check_debris.py <savedir> [eg]
#   eg モード(江頭則構成): (3) を「斜面侵食 + 平坦部への土砂到達
#   (max hs)」に替える。希薄なシート流では θe ≈ 0 のため平坦部の
#   河床堆積は遅く(物理的に正しい)、短時間の疎通検定では hs の到達を
#   活性の証拠とする。
import sys, struct

SD0, PORO = 5.0, 0.4
NX, NY = 60, 20
DX = 1.0
ST, XB = 0.4, 30.0          # slope_break のパラメータ(user_geoinfo と対)
TOL_SUM, TOL_SD = 1.0e-9, 1.0e-10
MIN_ERO, MIN_DEP = 1.0e-3, 1.0e-3


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


def z0_of(idx):
    i = idx % NX + 1
    x = (i - 0.5) * DX
    return ST * (XB - x) if x < XB else 0.0


savedir = sys.argv[1]
mode = sys.argv[2] if len(sys.argv) > 2 else "tk"
with open(savedir + "/state.dat", "rb") as f:
    ntot = NX * NY
    h = read_rle_array(f, ntot)
    z = read_rle_array(f, ntot)
    hrs = read_rle_array(f, ntot)
    hg = read_rle_array(f, ntot)
    sd = read_rle_array(f, ntot)
    hs = read_rle_array(f, ntot)

dz = [zi - z0_of(idx) for idx, zi in enumerate(z)]
solids = sum(hs) + (1.0 - PORO) * sum(dz)
max_ident = max(abs((sdi - SD0) - d) for sdi, d in zip(sd, dz))
ero = min(dz[idx] for idx in range(ntot) if (idx % NX + 1) < 30)
dep = max(dz[idx] for idx in range(ntot) if (idx % NX + 1) >= 30)
arr = max(hs[idx] for idx in range(ntot) if (idx % NX + 1) >= 30)

ok1 = abs(solids) < TOL_SUM
ok2 = max_ident < TOL_SD
if mode == "eg":
    ok3 = ero < -MIN_ERO and arr > 1.0e-4
else:
    ok3 = ero < -MIN_ERO and dep > MIN_DEP
print("(1) 固体総量保存: sum(hs)+(1-λ)sum(dz) = %.3e m*cell (tol %.0e) : %s"
      % (solids, TOL_SUM, "PASS" if ok1 else "FAIL"))
print("(2) 共動更新    : max|(sd-sd0)-(z-z0)| = %.3e m (tol %.0e) : %s"
      % (max_ident, TOL_SD, "PASS" if ok2 else "FAIL"))
if mode == "eg":
    print("(3) 活性確認    : 斜面侵食 min dz = %.3e m, 平坦部到達 max hs = %.3e m : %s"
          % (ero, arr, "PASS" if ok3 else "FAIL"))
else:
    print("(3) 活性確認    : 斜面侵食 min dz = %.3e m, 遷緩点下堆積 max dz = %.3e m : %s"
          % (ero, dep, "PASS" if ok3 else "FAIL"))

ok = ok1 and ok2 and ok3
print("== debris 検定: %s ==" % ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
