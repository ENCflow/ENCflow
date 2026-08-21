#!/usr/bin/env python3
# avalanche(流れ型雪崩 = 等価流体+速度比例連行)検定
#   使い方: Check_avalanche.py <savedir>
#   地形・発生区・定数は param.txt / make_init.py と対で保守する
import sys, struct

NX, NY, DX = 60, 20, 1.0
ST, XB = 0.4, 30.0                    # slope_break(user_geoinfo と対)
SD0, PORO, D0 = 0.5, 0.1, 0.5         # 雪厚, 空隙率, 破断深
REL_I, REL_J = (3, 10), (8, 13)       # 発生区(make_init.py と対)
TOL_SUM, TOL_SD = 1.0e-9, 1.0e-10
MIN_ENT, FRAC_GROW, FRAC_STOP = 0.05, 0.2, 0.3


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
with open(savedir + "/state.dat", "rb") as f:
    h = read_rle_array(f, ntot)
    z = read_rle_array(f, ntot)
    read_rle_array(f, ntot)     # hrs
    read_rle_array(f, ntot)     # hg
    sd = read_rle_array(f, ntot)
    hs = read_rle_array(f, ntot)


def z0_of(idx):
    x = (idx % NX + 0.5) * DX
    return ST * (XB - x) if x < XB else 0.0


def in_rel(idx):
    return (REL_I[0] <= idx % NX + 1 <= REL_I[1]
            and REL_J[0] <= idx // NX + 1 <= REL_J[1])


dz = [zi - z0_of(idx) for idx, zi in enumerate(z)]
solids = sum(hs) + (1.0 - PORO) * sum(dz)
max_ident = max(abs((sdi - SD0) - d) for sdi, d in zip(sd, dz))
ok1 = abs(solids) < TOL_SUM
ok2 = max_ident < TOL_SD
print("(1) 固体台帳  : sum(hs)+(1-λ)sum(dz) = %.3e m*cell (tol %.0e) : %s"
      % (solids, TOL_SUM, "PASS" if ok1 else "FAIL"))
print("(2) 共動更新  : max|(sd-sd0)-(z-z0)| = %.3e m (tol %.0e) : %s"
      % (max_ident, TOL_SD, "PASS" if ok2 else "FAIL"))

# 連行の活性: 発生区の外の走路(斜面部)で雪が削られている
path = [idx for idx in range(ntot)
        if not in_rel(idx) and (idx % NX + 0.5) * DX < XB]
ent_min = min(sd[idx] - SD0 for idx in path)
ok3 = ent_min < -MIN_ENT
print("(3) 連行の活性: 走路(発生区外)min(sd-sd0) = %.3f m (要 < -%.2f) : %s"
      % (ent_min, MIN_ENT, "PASS" if ok3 else "FAIL"))

# 成長: 連行された固体量が放出固体量に対して有意
released = (1.0 - PORO) * D0 * (REL_I[1] - REL_I[0] + 1) * (REL_J[1] - REL_J[0] + 1)
entrained = (1.0 - PORO) * sum(SD0 - sd[idx] for idx in range(ntot)
                               if not in_rel(idx) and sd[idx] < SD0)
ok4 = entrained > FRAC_GROW * released
print("(4) 成長      : 連行固体 %.1f m*cell / 放出固体 %.1f m*cell = %.2f (要 > %.2f) : %s"
      % (entrained, released, entrained / released, FRAC_GROW,
         "PASS" if ok4 else "FAIL"))

frac = sum(hs) / (released + entrained)
ok5 = frac < FRAC_STOP
print("(5) 停止      : 残存 sum(hs)/(放出+連行) = %.3f (tol %.2f) : %s"
      % (frac, FRAC_STOP, "PASS" if ok5 else "FAIL"))

ok = ok1 and ok2 and ok3 and ok4 and ok5
print("== avalanche 検定: %s ==" % ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
