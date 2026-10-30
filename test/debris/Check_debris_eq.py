#!/usr/bin/env python3
# debris 構成 7(param_eq.txt)の検定: 斜面等流の平衡濃度(高橋型 f_dbed = 1。developer.md §28.15)
#   使い方: Check_debris_eq.py [savedir]   (既定 save_eq)
#   savedir/state.dat(ゼロ抑制 RLE。h, z, hrs, hg, sd, hs の倍精度)を読み、水路 k(列 2k)の
#   流入点と出口から離れた区間 J1〜J2 で、混合体濃度 C = hs/(h + hs) を、最終の z から求めた
#   最急降下勾配(8 近傍への下り勾配の最大。領域内の近傍だけ)の高橋型の平衡濃度
#     tanθ ≥ tanφ        : C∞ = 0.9 C*(上限)
#     tanθ > 0.138       : C∞ = min(tanθ / (s (tanφ − tanθ)), 0.9 C*)(石礫型)
#     0.03 < tanθ ≤ 0.138 : C∞ = min(6.7 C∞d², 0.9 C*)(未成熟)
#     tanθ ≤ 0.03         : C∞ = 0(掃流域)
#   と比べる(C∞ > 0 は |C/C∞ − 1| ≤ 1e-9、C∞ = 0 は C ≤ 1e-12)。各水路の勾配が狙いの領域に
#   入っていることも確かめる。出口の行(開いた境界)の堆積は記録として表示する(§28.15)。
#   水路・係数は make_eq.py・param_eq.txt と対で保守する
import math
import struct
import sys

TAN = [0.60, 0.25, 0.15, 0.10, 0.05, 0.02]
REGIME = ["cap", "stony", "stony", "immature", "immature", "bedload"]
NX, NY, Z0 = 2 * len(TAN) + 1, 300, 200.0
SGRAV, TANPHI, CSTAR = 1.65, math.tan(math.radians(35.0)), 0.6
J1, J2 = 100, 220
TOL_C, TOL_ZERO = 1.0e-9, 1.0e-12


def cinf(t):
    if t <= 0.03:
        return 0.0, "bedload"
    if t >= TANPHI:
        return 0.9 * CSTAR, "cap"
    cd = t / (SGRAV * (TANPHI - t))
    if t > 0.138:
        return (min(cd, 0.9 * CSTAR), "stony" if cd < 0.9 * CSTAR else "cap")
    c = 6.7 * cd * cd
    return (min(c, 0.9 * CSTAR), "immature" if c < 0.9 * CSTAR else "cap")


def read_rec(f):
    n = struct.unpack("<i", f.read(4))[0]
    payload = f.read(n)
    assert struct.unpack("<i", f.read(4))[0] == n, "record marker mismatch"
    return payload


def read_rle(f, ntot):
    n, nrun = struct.unpack("<2q", read_rec(f))
    assert n == ntot, "unexpected array size %d != %d" % (n, ntot)
    runs = struct.unpack("<%dq" % (2 * nrun), read_rec(f))
    raw = read_rec(f)
    packed = struct.unpack("<%dd" % (len(raw) // 8), raw)
    out = [0.0] * n
    i = k = 0
    for r in range(nrun):
        i += runs[2 * r]
        lit = runs[2 * r + 1]
        out[i:i + lit] = packed[k:k + lit]
        i += lit
        k += lit
    return out


def main(savedir="save_eq"):
    with open(savedir + "/state.dat", "rb") as f:
        h, z, hrs, hg, sd, hs = [read_rle(f, NX * NY) for _ in range(6)]
    at = lambda a, i, j: a[(j - 1) * NX + i - 1]

    def slope8(i, j):
        best = 0.0
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                if (di or dj) and 1 <= i + di <= NX and 1 <= j + dj <= NY:
                    best = max(best, (at(z, i, j) - at(z, i + di, j + dj)) / math.hypot(di, dj))
        return best

    nfail = 0

    def check(ok, msg):
        nonlocal nfail
        print(("  ok   " if ok else "  FAIL ") + msg)
        if not ok:
            nfail += 1

    print("== debris eq: equilibrium concentration of uniform flow on six slopes (Takahashi type, %d-%d m)" % (J1, J2))
    for k, t in enumerate(TAN, 1):
        i = 2 * k
        worst, regimes, tans = 0.0, set(), []
        for j in range(J1, J2 + 1):
            c = at(hs, i, j) / (at(h, i, j) + at(hs, i, j))
            tl = slope8(i, j)
            ce, reg = cinf(tl)
            regimes.add(reg)
            tans.append(tl)
            worst = max(worst, abs(c / ce - 1.0) if ce > 0.0 else abs(c))
        ce0 = cinf(t)[0]
        ok_reg = regimes == {REGIME[k - 1]}
        tol = TOL_C if ce0 > 0.0 else TOL_ZERO
        what = "|C/Cinf - 1|" if ce0 > 0.0 else "C"
        check(ok_reg and worst <= tol,
              f"channel {k} tan(theta) = {t:.2f} ({REGIME[k - 1]}, Cinf = {ce0:.6f}): max {what} = {worst:.1e} "
              f"(limit {tol:.0e}; local slope {min(tans):.9f}-{max(tans):.9f}, regime {'/'.join(sorted(regimes))})")
    dzo = [at(z, 2 * k, NY) - (Z0 - t * (NY - 0.5)) for k, t in enumerate(TAN, 1)]
    print("  info outlet row (open boundary, no downslope neighbour inside the domain -> Cinf = 0): "
          "bed change " + ", ".join("%+.3f" % d for d in dzo) + " m (channels 1-6; developer.md §28.15)")

    print(f"=== debris eq check {'PASS' if nfail == 0 else f'FAIL ({nfail})'} ===")
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:2]))
