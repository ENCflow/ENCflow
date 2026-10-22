#!/usr/bin/env python3
# wetlw: 剥離深の横方向拡散 wet_lw の効きの検定
#   save_0(wet_lw なし)と save_l(wet_lw = ℓ_w)の state.dat を読み、
#     (1) 平滑: 侵食深 Δz = z0 − z の格子規模の凹凸(5 点ラプラシアンの 2 乗和)
#         が構成 l で半分以下(剥離の集中が ℓ_w に広がる)
#     (2) 平滑: 最大侵食深が構成 l で小さい(集中が緩む)
#     (3) 総量: 両構成の総侵食量 Σ(z0 − z) の比が 0.5〜2(拡散は量を変えず
#         配り直すだけ。流れの差で少し変わる)
#   を検定する。state.dat の読み方は ../suspend/Check_suspend.py と同じ。
#   使い方: Check_spread.py <save_0> <save_l>
import sys, struct

Z0 = 0.0
NX, NY = 101, 101


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


def read_z(savedir):
    with open(savedir + "/state.dat", "rb") as f:
        ntot = NX * NY
        read_rle_array(f, ntot)          # h
        return read_rle_array(f, ntot)   # z


z0 = read_z(sys.argv[1])
zl = read_z(sys.argv[2])
dz0 = [Z0 - v for v in z0]
dzl = [Z0 - v for v in zl]
def rough(dz):
    r = 0.0
    for j in range(1, NY - 1):
        for i in range(1, NX - 1):
            k = j * NX + i
            r += (4.0 * dz[k] - dz[k - 1] - dz[k + 1] - dz[k - NX] - dz[k + NX]) ** 2
    return r


r0, rl = rough(dz0), rough(dzl)
m0, ml = max(dz0), max(dzl)
s0, sl = sum(dz0), sum(dzl)
ok1 = rl < 0.5 * r0
ok2 = ml < m0
ok3 = 0.5 < sl / s0 < 2.0
print("(1) 平滑: 侵食深の格子規模の凹凸 (ラプラシアンの 2 乗和) = %.3e (なし) / %.3e (wet_lw) m2 : %s" % (r0, rl, "PASS" if ok1 else "FAIL"))
print("(2) 平滑: 最大侵食深 = %.3e (なし) / %.3e (wet_lw) m : %s" % (m0, ml, "PASS" if ok2 else "FAIL"))
print("(3) 総量: 総侵食量の比 (wet_lw / なし) = %.3f : %s" % (sl / s0, "PASS" if ok3 else "FAIL"))
ok = ok1 and ok2 and ok3
print("== wetlw 検定: %s ==" % ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
