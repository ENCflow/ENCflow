#!/usr/bin/env python3
"""test/debris 構成 9・10 の検定: 高橋・中川の侵食・堆積則(f_dbed = 3)への追加(developer.md §28.18)。

  Check_debris_tk.py rate <save_a> <save_b>   構成 9: 不飽和床の侵食速度
  Check_debris_tk.py same <save_1> <save_0>   構成 9: 飽和した河床では f_dbunsat = 1 と 0 が同じ
  Check_debris_tk.py eq <save> <0|1>          構成 10: 等流の平衡濃度(第 3 引数は f_dbimm)

rate: 同じ設定を T 秒まで(a)と、地形の更新 1 回ぶん先の T + Δt_g 秒まで(b)計算した 2 つの保存状態
  (state.dat。h, z, hrs, hg, sd, hs の倍精度)から、最後の更新を再構成する。
    侵食量(固体の厚さ)  fx = C* (z_a − z_b)          (z は更新のときだけ変わる)
    更新の直前の状態     z = z_a、h = h_b、hs = hs_b − fx (侵食・堆積は h を変えず、hs に fx を足す)
    流動面の勾配         tanθ = (η(j) − η(j+1))/Δy、η = z + h + hs(流れは南向き。コードは流向の下流側の
                         片側差分。水路は幅 1 セルで横向きの流速は 0)
    石礫型の平衡濃度     c∞ = min(tanθ / (s (tanφ − tanθ)), 0.9 C*)
    平衡濃度             C∞ = 6.7 c∞²(c∞ < 1/6.7。掃流状集合流動。f_dbimm = 1)、ほかは c∞
  C < C∞ のセルの fx を、不飽和床の侵食式(新砂防 44(3) 式(10)、年報 34 B-2 式(8)〜(11) の単一粒径形)
    i = (K/s) √(g h_t) sin^{3/2}θ (1 − C/c∞)^{1/2} (C∞ − C)/c∞ · h_t/d_L、 fx = C* i Δt_g
  と比べる(h_t = h + hs、C = hs/h_t)。判定は |fx − fx_式| ≤ TOL_RATE fx_式 + TOL_ABS(TOL_ABS は、
  標高 200 m の z の差から fx を求めるときの丸め = z の最小単位の数個ぶん)。水路ごとに検定したセルが
  MIN_CELLS 以上あり、石礫型・上限・掃流状集合流動の 3 つの領域がそろうことも確かめる。
same: 2 つの state.dat がバイト一致(飽和した河床 hg = sy0 sd では飽和床の式のまま)。
eq: 流入点と出口から離れた区間 J1〜J2 で、濃度 C が、最終の流動面の勾配から求めた平衡濃度と
  |C/C∞ − 1| ≤ TOL_C で一致する。f_dbimm = 1 では水路 4〜6 が掃流状集合流動の 6.7 c∞² になる。
水路・係数は make_eq.py・make_tk.py と対で保守する。
"""
import math
import struct
import sys

import make_eq as me
import make_tk as mt

NX, NY = me.NX, me.NY
GRAV = 9.8
SGRAV, TANPHI, CSTAR = 1.65, math.tan(math.radians(35.0)), 1.0 - mt.POROSITY
CAP = 0.9 * CSTAR
IMMAT = 6.7
J1, J2 = 100, 220
TOL_RATE, TOL_ABS, TOL_C = 1.0e-9, 2.0e-13, 1.0e-9
MIN_CELLS = 100


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


def read_state(savedir):
    with open(savedir + "/state.dat", "rb") as f:
        h, z, hrs, hg, sd, hs = [read_rle(f, NX * NY) for _ in range(6)]
    return h, z, hg, sd, hs


def at(a, i, j):
    return a[(j - 1) * NX + i - 1]


def cstony(t):
    """石礫型の平衡濃度(上限 0.9 C* つき)と領域名。"""
    if t <= 0.0:
        return 0.0, "flat"
    if t >= TANPHI:
        return CAP, "cap"
    c = t / (SGRAV * (TANPHI - t))
    return (CAP, "cap") if c >= CAP else (c, "stony")


def ceq(t, imm):
    """平衡濃度 C∞、石礫型の c∞、領域名。"""
    cs, reg = cstony(t)
    if imm and IMMAT * cs < 1.0:
        return IMMAT * cs * cs, cs, "immature"
    return cs, cs, reg


def check_rate(dir_a, dir_b):
    ha, za, hga, sda, hsa = read_state(dir_a)
    hb, zb, hgb, sdb, hsb = read_state(dir_b)
    dtg = mt.DT_GEO
    kuns = mt.KUNS / SGRAV
    nfail = 0
    regs_all = set()
    print("== debris tk rate: unsaturated-bed erosion in the last bed update (%s -> %s)" % (dir_a, dir_b))
    for k, t in enumerate(me.TAN, 1):
        i = 2 * k
        fx = [0.0] * (NY + 2)
        hsp = [0.0] * (NY + 2)
        eta = [0.0] * (NY + 2)
        for j in range(1, NY + 1):
            fx[j] = CSTAR * (at(za, i, j) - at(zb, i, j))
            hsp[j] = at(hsb, i, j) - fx[j]
            eta[j] = at(za, i, j) + at(hb, i, j) + max(hsp[j], 0.0)
        worst, wex, ncell, regs, cmin, cmax = 0.0, 0.0, 0, set(), 1.0, 0.0
        for j in range(2, NY - 1):
            h = at(hb, i, j)
            ht = h + max(hsp[j], 0.0)
            cc = max(hsp[j], 0.0) / ht
            tl = (eta[j] - eta[j + 1]) / 1.0
            ce, cs, reg = ceq(tl, True)
            if not cc < ce:
                continue                      # 堆積の側(流速に依る式。ここでは検定しない)
            sinth = tl / math.sqrt(1.0 + tl * tl)
            fxe = (CSTAR * kuns * math.sqrt(GRAV * ht) * sinth ** 1.5
                   * math.sqrt(1.0 - cc / cs) * (ce - cc) / cs * ht / mt.D50 * dtg)
            worst = max(worst, abs(fx[j] / fxe - 1.0))
            wex = max(wex, abs(fx[j] - fxe) / (TOL_RATE * fxe + TOL_ABS))
            ncell += 1
            regs.add(reg)
            cmin, cmax = min(cmin, cc / ce), max(cmax, cc / ce)
        regs_all |= regs
        ok = wex <= 1.0 and ncell >= MIN_CELLS
        nfail += 0 if ok else 1
        print(("  ok   " if ok else "  FAIL ") +
              f"channel {k} tan(theta) = {t:.2f} ({'/'.join(sorted(regs))}): max |fx/formula - 1| = {worst:.1e}, "
              f"max |fx - formula| / ({TOL_RATE:.0e} formula + {TOL_ABS:.0e} m) = {wex:.2f} (limit 1) "
              f"over {ncell} cells, C/Cinf = {cmin:.3f}-{cmax:.3f}")
    ok = regs_all >= {"cap", "stony", "immature"}
    nfail += 0 if ok else 1
    print(("  ok   " if ok else "  FAIL ") + "regimes covered: " + "/".join(sorted(regs_all)))
    return nfail


def check_same(dir_1, dir_0):
    a = open(dir_1 + "/state.dat", "rb").read()
    b = open(dir_0 + "/state.dat", "rb").read()
    h, z, hg, sd, hs = read_state(dir_1)
    # 飽和の確認(hg = sy0 sd)と、侵食が起きていること
    sat = max(abs(at(hg, 2 * k, j) - mt.SY0 * at(sd, 2 * k, j))
              for k in range(1, len(me.TAN) + 1) for j in range(1, NY + 1))
    ero = min(at(z, 2 * k, j) - (me.Z0 - t * (j - 0.5))
              for k, t in enumerate(me.TAN, 1) for j in range(1, NY + 1))
    ok = a == b and sat < 1.0e-9 and ero < -1.0e-6
    print("== debris tk same: saturated bed, f_dbunsat = 1 vs 0 (%s, %s)" % (dir_1, dir_0))
    print(("  ok   " if ok else "  FAIL ") +
          f"state.dat {'identical' if a == b else 'DIFFERENT'}; max |hg - sy0 sd| = {sat:.1e} m; "
          f"largest bed lowering {ero:.2e} m")
    return 0 if ok else 1


def check_eq(savedir, imm):
    h, z, hg, sd, hs = read_state(savedir)
    nfail = 0
    print("== debris tk eq: equilibrium concentration of uniform flow, f_dbed = 3, f_dbimm = %d (%d-%d m)"
          % (imm, J1, J2))
    regs_all = set()
    for k, t in enumerate(me.TAN, 1):
        i = 2 * k
        eta = [0.0] + [at(z, i, j) + at(h, i, j) + at(hs, i, j) for j in range(1, NY + 1)]
        worst, regs = 0.0, set()
        for j in range(J1, J2 + 1):
            c = at(hs, i, j) / (at(h, i, j) + at(hs, i, j))
            ce, cs, reg = ceq(eta[j] - eta[j + 1], bool(imm))
            regs.add(reg)
            worst = max(worst, abs(c / ce - 1.0))
        regs_all |= regs
        ce0, cs0, reg0 = ceq(t, bool(imm))
        ok = worst <= TOL_C and regs == {reg0}
        nfail += 0 if ok else 1
        print(("  ok   " if ok else "  FAIL ") +
              f"channel {k} tan(theta) = {t:.2f} ({reg0}, Cinf = {ce0:.6f}): max |C/Cinf - 1| = {worst:.1e} "
              f"(limit {TOL_C:.0e}; regime {'/'.join(sorted(regs))})")
    want = {"cap", "stony", "immature"} if imm else {"cap", "stony"}
    ok = regs_all == want
    nfail += 0 if ok else 1
    print(("  ok   " if ok else "  FAIL ") + "regimes: " + "/".join(sorted(regs_all)))
    return nfail


def main():
    mode = sys.argv[1]
    if mode == "rate":
        nfail = check_rate(sys.argv[2], sys.argv[3])
    elif mode == "same":
        nfail = check_same(sys.argv[2], sys.argv[3])
    elif mode == "eq":
        nfail = check_eq(sys.argv[2], int(sys.argv[3]))
    else:
        sys.exit("usage: Check_debris_tk.py rate|same|eq ...")
    print(f"=== debris tk {mode} check {'PASS' if nfail == 0 else f'FAIL ({nfail})'} ===")
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
