#!/usr/bin/env python3
# bldgdebris(家屋破壊・瓦礫ラスタ場)疎通・保存則検定
#   <savedir>/bldgdebris.dat(ゼロ抑制 RLE。developer.md §7)から
#   hbd, wbd, wbs, wbs0 を読み、
#     (1) 材積保存: |Σhbd + Σwbd + Σwbs − Σwbs0| < TOL
#         (閉領域・ダムなし・gv=wfrac=1 の平地格子が前提)
#     (2) 活性確認: 破壊の発生(Σwbs < Σwbs0 − MIN_DES)と
#         堆積(Σwbd > MIN_DEP)
#     (3) 到達確認: 平坦部(i >= IREACH)の瓦礫 max(hbd+wbd) > 0
#   を検定する。初期ストック総量は保存された wbs0 から取る。
#   使い方: Check_bldgdebris.py <savedir>
import sys, struct

NX, NY = 60, 20
TOL = 1.0e-9
MIN_DES, MIN_DEP = 1.0e-3, 1.0e-3
IREACH = 30                   # 遷緩点(slope_break の x=30m)


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


savedir = sys.argv[1]
ntot = NX * NY
with open(savedir + "/bldgdebris.dat", "rb") as f:
    hbd = read_rle_array(f, ntot)
    wbd = read_rle_array(f, ntot)
    wbs = read_rle_array(f, ntot)
    wbs0 = read_rle_array(f, ntot)

total0 = sum(wbs0)
total = sum(hbd) + sum(wbd) + sum(wbs)
des = total0 - sum(wbs)
dep = sum(wbd)
reach = max(hbd[i] + wbd[i] for i in range(ntot) if (i % NX + 1) >= IREACH)

ok1 = abs(total - total0) < TOL
ok2 = des > MIN_DES and dep > MIN_DEP
ok3 = reach > 0.0
print("(1) 材積保存  : sum(hbd+wbd+wbs) - sum(wbs0) = %.3e m*cell (tol %.0e) : %s"
      % (total - total0, TOL, "PASS" if ok1 else "FAIL"))
print("(2) 活性確認  : 破壊 %.3e m*cell (要 > %.0e), 堆積 %.3e m*cell (要 > %.0e) : %s"
      % (des, MIN_DES, dep, MIN_DEP, "PASS" if ok2 else "FAIL"))
print("(3) 到達確認  : 平坦部(i>=%d) max(hbd+wbd) = %.3e m : %s"
      % (IREACH, reach, "PASS" if ok3 else "FAIL"))

ok = ok1 and ok2 and ok3
print("== bldgdebris 検定(%s): %s ==" % (savedir, "PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
