#!/usr/bin/env python3
# bedfines 検定(developer.md §84.10)
#   save_*/state.dat(h, z, rsh, hg, sd, hs の順。RLE)と save_*/geomorph_fines.dat(sf)を読む。
#     (1) all(細粒 100 %、浮遊砂のみ)は off と state.dat がビット一致(Run.sh が cmp)。
#         ここでは sf = sd(全層が細粒分)を確認する
#     (2) mix(掃流砂+浮遊砂、細粒 50 %): 0 <= sf <= sd(TOL_INV)、
#         固体総量 Σhs + (1−λ)Σ(z − z0) と細粒分 Σhs + (1−λ)Σ(sf − sf0) が
#         ともに TOL_SUM 未満(閉じた系)、細粒分が浮遊砂に出ている(Σ(sf − sf0) < 0 で
#         |Σ| > MIN_REL、max(hs) > MIN_REL)、河床は動いている(max|z − z0| > MIN_DZ)
#     (3) coarse(粗粒のみ): hs が厳密に 0、sf が厳密に 0、河床は動いている
#     (4) feed(粗粒の水路に細粒分を給砂、浮遊砂のみ): z − z0 >= −TOL_INV(河床は
#         削られない)、|sf − (z − z0)| < TOL_ID(在庫 = 堆積)、堆積がある(max sf > MIN_DEP)
#     (5) off に Sf 出力がない(配列未確保)
#     (6) bfeed(細粒 50 % の河床、掃流砂のみが動く(巻き上げなし)、容量給砂): 入口列
#         (i = 1、水路の行)の |z − z0| と |sf − sf0| が TOL_FEED 未満(給砂は流入セルと
#         同じ組成 = 入口の高さと在庫が固定)、0 <= sf <= sd、河床と在庫が動いている
#         (細粒分が掃流砂に同伴)
#   リスタート往復(mix と同じ設定の rt1 → rt2)と MPI の一致は Run.sh / Run_MPI.sh が cmp で見る
import sys, struct, os, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_init import NX as CNX, NY as CNY, J1, J2, z_of, sdfeed_of

PORO, SD0_BOX = 0.4, 10.0
BNX, BNY = 101, 101
TOL_SUM, TOL_INV, TOL_ID, TOL_FEED = 1.0e-9, 1.0e-12, 1.0e-9, 1.0e-9
MIN_DZ, MIN_REL, MIN_DEP = 1.0e-6, 1.0e-6, 1.0e-6


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


def load(tag, nx, ny):
    ntot = nx * ny
    with open("save_%s/state.dat" % tag, "rb") as f:
        h = read_rle_array(f, ntot); z = read_rle_array(f, ntot); read_rle_array(f, ntot)
        read_rle_array(f, ntot); sd = read_rle_array(f, ntot); hs = read_rle_array(f, ntot)
    with open("save_%s/geomorph_fines.dat" % tag, "rb") as f:
        sf = read_rle_array(f, ntot)
    return z, sd, hs, sf


ok = True


def rep(label, cond, detail):
    global ok
    ok = ok and cond
    print("%s %s : %s" % (label, detail, "PASS" if cond else "FAIL"))


# (1) all: sf = sd
z, sd, hs, sf = load("all", BNX, BNY)
rep("(1) all 細粒 100 %", max(abs(a - b) for a, b in zip(sf, sd)) < TOL_INV,
    "max|sf - sd| = %.2e" % max(abs(a - b) for a, b in zip(sf, sd)))

# (2) mix
z, sd, hs, sf = load("mix", BNX, BNY)
sf0 = 0.5 * SD0_BOX
inv = min(min(sf), min(b - a for a, b in zip(sf, sd)))
solids = sum(hs) + (1.0 - PORO) * sum(z)
fines = sum(hs) + (1.0 - PORO) * sum(a - sf0 for a in sf)
dsf = sum(a - sf0 for a in sf)
rep("(2a) mix 不変条件 0 <= sf <= sd", inv > -TOL_INV, "min(sf, sd - sf) = %.2e" % inv)
rep("(2b) mix 固体総量保存", abs(solids) < TOL_SUM, "sum(hs)+(1-λ)sum(z-z0) = %.2e" % solids)
rep("(2c) mix 細粒分保存", abs(fines) < TOL_SUM, "sum(hs)+(1-λ)sum(sf-sf0) = %.2e" % fines)
rep("(2d) mix 細粒分が浮遊砂に出ている", dsf < -MIN_REL and max(hs) > MIN_REL,
    "sum(sf-sf0) = %.3e m*cell, max(hs) = %.3e" % (dsf, max(hs)))
rep("(2e) mix 河床が動いている", max(abs(a) for a in z) > MIN_DZ, "max|z-z0| = %.3e" % max(abs(a) for a in z))

# (3) coarse
z, sd, hs, sf = load("coarse", BNX, BNY)
rep("(3) coarse hs・sf が厳密に 0、河床は動く", max(abs(a) for a in hs) == 0.0 and max(abs(a) for a in sf) == 0.0
    and max(abs(a) for a in z) > MIN_DZ, "max|hs| = %.1e, max|sf| = %.1e, max|z-z0| = %.3e"
    % (max(abs(a) for a in hs), max(abs(a) for a in sf), max(abs(a) for a in z)))

# (4) feed(channel)
z, sd, hs, sf = load("feed", CNX, CNY)
z0 = [z_of(i, j) for j in range(1, CNY + 1) for i in range(1, CNX + 1)]
dz = [a - b for a, b in zip(z, z0)]
rep("(4a) feed 河床は削られない", min(dz) > -TOL_INV, "min(z-z0) = %.2e" % min(dz))
rep("(4b) feed 在庫 = 堆積", max(abs(a - b) for a, b in zip(sf, dz)) < TOL_ID,
    "max|sf-(z-z0)| = %.2e" % max(abs(a - b) for a, b in zip(sf, dz)))
rep("(4c) feed 堆積がある", max(sf) > MIN_DEP, "max(sf) = %.3e m" % max(sf))

# (6) bfeed(channel): 入口の z・sf が固定、不変条件、活性
z, sd, hs, sf = load("bfeed", CNX, CNY)
z0 = [z_of(i, j) for j in range(1, CNY + 1) for i in range(1, CNX + 1)]
sf0 = [0.5 * sdfeed_of(i, j) for j in range(1, CNY + 1) for i in range(1, CNX + 1)]
dz = [a - b for a, b in zip(z, z0)]; dsf = [a - b for a, b in zip(sf, sf0)]
inlet = [(j - 1) * CNX + 0 for j in range(J1, J2 + 1)]
rep("(6a) bfeed 入口の河床高が固定", max(abs(dz[n]) for n in inlet) < TOL_FEED, "max|z-z0| at i=1 = %.2e" % max(abs(dz[n]) for n in inlet))
rep("(6b) bfeed 入口の在庫が固定", max(abs(dsf[n]) for n in inlet) < TOL_FEED, "max|sf-sf0| at i=1 = %.2e" % max(abs(dsf[n]) for n in inlet))
inv = min(min(sf), min(b - a for a, b in zip(sf, sd)))
rep("(6c) bfeed 不変条件 0 <= sf <= sd", inv > -TOL_INV, "min(sf, sd - sf) = %.2e" % inv)
rep("(6d) bfeed 河床と在庫が動いている(細粒分が掃流砂に同伴)", max(abs(a) for a in dz) > MIN_DZ and max(abs(a) for a in dsf) > MIN_DZ,
    "max|z-z0| = %.3e, max|sf-sf0| = %.3e" % (max(abs(a) for a in dz), max(abs(a) for a in dsf)))

# (5) off に Sf 出力がない
rep("(5) off に Sf 出力なし", not glob.glob("result_off/Sf*.txt") and bool(glob.glob("result_all/Sf*.txt")),
    "result_off/Sf* = %d, result_all/Sf* = %d" % (len(glob.glob("result_off/Sf*.txt")), len(glob.glob("result_all/Sf*.txt"))))

print("== bedfines 検定: %s ==" % ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
