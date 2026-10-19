#!/usr/bin/env python3
# bendsed 検定(developer.md §84.3)
#   4 構成(left/right × on/off)の save_*/state.dat から z を読み、make_init.py の
#   地形(zinit)との差 Δz を円弧区間の横断方向 n(左が正。left では n > 0 が内岸、
#   right は鏡像なので make_init の n 定義もそのまま内岸)で集計する。
#     (1) 補正あり: 外岸側(n < 0)の平均 Δz − 内岸側(n > 0)の平均 Δz < −CONTRAST
#         (外岸洗掘・内岸堆積の向き。left と right の両方)
#     (2) 補正なし(対照): 同じ量が > 0(補正なしでは内岸側が多く削れる = 補正の
#         効果が符号を反転させていることの記録)
#     (3) 鏡像対称: max|Δz_left − flipud(Δz_right)| < TOL_MIRROR(on・off とも。
#         曲率の符号と左法線の扱いが座標系の向きに依らない)
#     (4) 乾いた河岸: max|Δz| が厳密に 0(4 構成すべて。§84.2)
#   使い方: Check_bendsed.py(カレントの save_left_on 等を読む)
import sys, math, struct, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_init as mi

CONTRAST, TOL_MIRROR = 0.05, 1.0e-4
S_LO, S_HI = mi.S_ARC0 + 2.0, mi.S_ARC1 - 2.0    # 集計する円弧区間(端を除く)


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


def load_dz(tag, turn):
    # 初期地形は本体が読んだ zinit_*.txt(6 桁)と同じ値を使う(z_of の丸め前の
    # 値と比べると乾いた河岸に 5e-7 の見かけの差が出る)
    z0 = [[float(v) for v in line.split()] for line in open("zinit_%s.txt" % turn)]
    with open("save_%s/state.dat" % tag, "rb") as f:
        ntot = mi.NX * mi.NY
        read_rle_array(f, ntot)              # h
        z = read_rle_array(f, ntot)
    dz = [[z[(j - 1) * mi.NX + (i - 1)] - z0[j - 1][i - 1] for i in range(1, mi.NX + 1)] for j in range(1, mi.NY + 1)]
    return dz


def stats(dz, turn):
    mi.turn = turn
    inner, outer, dry = [], [], 0.0
    for j in range(1, mi.NY + 1):
        for i in range(1, mi.NX + 1):
            c = mi.cell(i, j)
            if c is None:
                dry = max(dry, abs(dz[j - 1][i - 1]))
                continue
            s, n = c
            if S_LO <= s <= S_HI:
                (inner if n > 0 else outer).append(dz[j - 1][i - 1])
    return sum(outer) / len(outer) - sum(inner) / len(inner), dry


ok = True
res = {}
for mode in ("on", "off"):
    for turn in ("left", "right"):
        tag = "%s_%s" % (turn, mode)
        dz = load_dz(tag, turn)
        res[tag] = dz
        contrast, dry = stats(dz, turn)
        if mode == "on":
            good = contrast < -CONTRAST
            print("(1) %-9s 外岸−内岸の平均 Δz = %+.4f m (< %.2f) : %s" % (tag, contrast, -CONTRAST, "PASS" if good else "FAIL"))
        else:
            good = contrast > 0.0
            print("(2) %-9s 外岸−内岸の平均 Δz = %+.4f m (> 0, 対照) : %s" % (tag, contrast, "PASS" if good else "FAIL"))
        ok = ok and good
        good = dry == 0.0
        print("(4) %-9s 乾いた河岸の max|Δz| = %.1e m (must be 0) : %s" % (tag, dry, "PASS" if good else "FAIL"))
        ok = ok and good
    a, b = res["left_%s" % mode], res["right_%s" % mode]
    mirror = max(abs(a[j][i] - b[mi.NY - 1 - j][i]) for j in range(mi.NY) for i in range(mi.NX))
    good = mirror < TOL_MIRROR
    print("(3) %-9s 鏡像対称 max|Δz_left − flipud(Δz_right)| = %.3e m (tol %.0e) : %s" % (mode, mirror, TOL_MIRROR, "PASS" if good else "FAIL"))
    ok = ok and good
print("== bendsed 検定: %s ==" % ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
