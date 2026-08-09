#!/usr/bin/env python3
# slide(瞬時流動化 f_release / 斜面安定 f_slide)疎通・保存則検定
#   save/state.dat から h, z, sd, hs を読み、モードに応じて検定する。
#   release モード(param.txt。崩壊深 D=1m を i∈[5,15], j∈[5,16] に与える):
#     (1) 固体総量保存: |Σhs + (1-λ)Σ(z-z0)| < TOL_SUM
#     (2) 共動更新恒等: max|(sd - sd0) - (z - z0)| < TOL_SD
#     (3) 水収支: |Σh − λ・relsat・ΣD| < TOL_W(水は放出間隙水のみ)
#     (4) 活性確認: 崩壊域の掘削(min dz < -0.5)と域外への移動
#   fslide モード(param_fs.txt。sd0=0.5):
#     (1) 固体総量保存(許容 TOL_SUM_FS: 多数回転換の丸め累積)
#     (2) 共動更新恒等
#     (4) 活性確認: 斜面部に sd ≈ 0(崩壊発生)のセルが存在
#   z0 は slope_break(tanθ=0.4, 遷緩点 x=30m)と対で保守する。
#   使い方: Check_slide.py <savedir> <release|fslide>
import sys, struct

NX, NY = 60, 20
DX = 1.0
ST, XB = 0.4, 30.0
PORO = 0.4
TOL_SUM, TOL_SD, TOL_W = 1.0e-9, 1.0e-10, 1.0e-9
TOL_SUM_FS = 1.0e-8


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


savedir, mode = sys.argv[1], sys.argv[2]
SD0 = 5.0 if mode == "release" else 0.5
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

ok = True
if mode == "release":
    # 崩壊域(i∈[5,15], j∈[5,16]。Run.sh の dbinit 生成と対)D=1m
    ncell = 11 * 12
    wexp = PORO * 1.0 * 1.0 * ncell     # λ・relsat・ΣD
    wsum = sum(h) + sum(hg)
    src_min = min(dz[idx] for idx in range(ntot)
                  if 5 <= idx % NX + 1 <= 15 and 5 <= idx // NX + 1 <= 16)
    out_dep = max(dz[idx] for idx in range(ntot) if idx % NX + 1 >= 16)
    ok1 = abs(solids) < TOL_SUM
    ok2 = max_ident < TOL_SD
    ok3 = abs(wsum - wexp) < TOL_W
    ok4 = src_min < -0.5 and out_dep > 1.0e-3
    print("(1) 固体総量保存: %.3e (tol %.0e) : %s" % (solids, TOL_SUM, "PASS" if ok1 else "FAIL"))
    print("(2) 共動更新    : %.3e (tol %.0e) : %s" % (max_ident, TOL_SD, "PASS" if ok2 else "FAIL"))
    print("(3) 水収支      : Σh+Σhg = %.6f (期待 %.6f) : %s" % (wsum, wexp, "PASS" if ok3 else "FAIL"))
    print("(4) 活性確認    : 崩壊域 min dz = %.3f, 域外堆積 max dz = %.3e : %s"
          % (src_min, out_dep, "PASS" if ok4 else "FAIL"))
    ok = ok1 and ok2 and ok3 and ok4
else:
    slid = min(sd[idx] for idx in range(ntot) if idx % NX + 1 < 30)
    ok1 = abs(solids) < TOL_SUM_FS
    ok2 = max_ident < TOL_SD
    ok4 = slid < 1.0e-12
    print("(1) 固体総量保存: %.3e (tol %.0e) : %s" % (solids, TOL_SUM_FS, "PASS" if ok1 else "FAIL"))
    print("(2) 共動更新    : %.3e (tol %.0e) : %s" % (max_ident, TOL_SD, "PASS" if ok2 else "FAIL"))
    print("(4) 活性確認    : 斜面部 min sd = %.3e(0 = 崩壊発生): %s"
          % (slid, "PASS" if ok4 else "FAIL"))
    ok = ok1 and ok2 and ok4

print("== slide(%s)検定: %s ==" % (mode, "PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
