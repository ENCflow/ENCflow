#!/usr/bin/env python3
# driftwood(流木ラスタ場)疎通・保存則検定
#   <savedir>/driftwood.dat(ゼロ抑制 RLE。developer.md §7)から
#   hd, wd, wst を読み(zref は読み飛ばし)、
#     (1) 材積保存: |Σhd + Σwd + Σwst − 初期ストック総量| < TOL
#         (閉領域・ダムなし・gv=wfrac=1 の平地格子が前提)
#     (2) 活性確認: 流木化の発生(Σwst < 初期総量 − MIN_REC)と
#         堆積(Σwd > MIN_DEP)
#     (3) 到達確認: 平坦部(i >= IREACH)への流木到達 max(hd+wd) > 0
#   を検定する。初期ストック総量 = dw_stock0 × nx × ny は param と対で
#   保守する。
#   使い方: Check_driftwood.py <savedir>
import sys, struct

NX, NY = 60, 20
STOCK0 = 0.01                 # dw_stock0(param.txt / param_flood.txt と対)
TOL = 1.0e-9
MIN_REC, MIN_DEP = 1.0e-3, 1.0e-3
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
with open(savedir + "/driftwood.dat", "rb") as f:
    hd = read_rle_array(f, ntot)
    wd = read_rle_array(f, ntot)
    wst = read_rle_array(f, ntot)

total0 = STOCK0 * NX * NY
total = sum(hd) + sum(wd) + sum(wst)
rec = total0 - sum(wst)
dep = sum(wd)
reach = max(hd[i] + wd[i] for i in range(ntot) if (i % NX + 1) >= IREACH)

ok1 = abs(total - total0) < TOL
ok2 = rec > MIN_REC and dep > MIN_DEP
ok3 = reach > 0.0
print("(1) 材積保存  : sum(hd+wd+wst) - total0 = %.3e m*cell (tol %.0e) : %s"
      % (total - total0, TOL, "PASS" if ok1 else "FAIL"))
print("(2) 活性確認  : 流木化 %.3e m*cell (要 > %.0e), 堆積 %.3e m*cell (要 > %.0e) : %s"
      % (rec, MIN_REC, dep, MIN_DEP, "PASS" if ok2 else "FAIL"))
print("(3) 到達確認  : 平坦部(i>=%d) max(hd+wd) = %.3e m : %s"
      % (IREACH, reach, "PASS" if ok3 else "FAIL"))

ok = ok1 and ok2 and ok3
print("== driftwood 検定(%s): %s ==" % (savedir, "PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
