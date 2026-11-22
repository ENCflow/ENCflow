#!/usr/bin/env python3
"""test/slide 構成 5〜8 の検定: 斜面安定判定 f_slide の選択子(developer.md §28.19)。

  Check_slide_fs.py fs <case>              安全率の出力 Fs0001.bil を式の値と比べる(判定だけのケース)
  Check_slide_fs.py pair <case1> <case0>   2 つのケースの Fs が同じ(same)か、違う(differ)かを確かめる
                    <same|differ>
  Check_slide_fs.py dmax1 <case>           slide_dmax: 更新 1 回でちょうど slide_dmax だけ流動化する
  Check_slide_fs.py wet <case1> <case0> <case2>   f_slide_wet
  Check_slide_fs.py noflow <case1> <case0>        f_slide_noflow
  Check_slide_fs.py ledger <case>          流動化ありの保存則(固体・水)

fs: 平面の地形 z = Z0 − A x − B y では、内部のセルの最急勾配は tanθ = √(A² + B²)(D∞ は平面で厳密)。
  土層厚 sd と飽和厚 hw = gw_sat0·sd も平面なので、全水頭 H = (z − sd) + hw の最急降下勾配 J も
  解析的に決まる(静水の湖の下は H = z + h = 一定で J = 0)。判定する厚さ d = min(sd, slide_dmax)
  (slide_dmax = 0 は sd)、その中の飽和厚 hw_d = max(0, hw − (sd − d)) として
    従来の式        Fs = [c' + (γt d − γw hw_d) cos²θ tanφs] / (γt d tanθ cos²θ)
    f_slide_seep = 1 Fs = [c' + (γt d − γw hw_d) cos²θ tanφs] / [cos²θ {(γt d − γw hw_d) tanθ + γw hw_d J}]
  の値と、出力(bil = 単精度)が相対 TOL_FS 以内で一致することを、内部のセル(縁の 1 列を除く。
  湖のケースは、自分と 8 近傍がすべて湖か、すべて陸のセル)で確かめる。
定数・ケースは make_fs.py と対で保守する。
"""
import math
import struct
import sys

import make_fs as mf

NX, NY = mf.NX, mf.NY
GRAV, RHOW = 9.8, 1000.0
TOL_FS = 2.0e-6          # 単精度の出力の丸め
TOL_X = 1.0e-12          # 標高・土層厚の厳密な値との差 (m)
TOL_SUM, TOL_W = 1.0e-9, 1.0e-9


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


def read_state(case):
    with open(f"save_{case}/state.dat", "rb") as f:
        h, z, hrs, hg, sd, hs = [read_rle(f, NX * NY) for _ in range(6)]
    return dict(h=h, z=z, hg=hg, sd=sd, hs=hs)


def read_fs(case):
    raw = open(f"result_{case}/Fs0001.bil", "rb").read()
    return struct.unpack("<%df" % (NX * NY), raw)


def at(a, i, j):
    return a[(j - 1) * NX + i - 1]


def interior(m=1):
    """縁から m 列を除いたセル。"""
    return [(i, j) for j in range(1 + m, NY - m + 1) for i in range(1 + m, NX - m + 1)]


def nbrs(i, j):
    return [(i + di, j + dj) for dj in (-1, 0, 1) for di in (-1, 0, 1)]


def fs_formula(c, i, j, jh):
    """セル (i, j) の安全率。jh は全水頭の勾配 J(None なら従来の式)。"""
    tanth = math.hypot(mf.A, mf.B)
    cos2 = 1.0 / (1.0 + tanth * tanth)
    sd = mf.sd_of(c, i, j)
    d = min(sd, c["dmax"]) if c["dmax"] > 0.0 else sd
    hw = c["sat"] * sd
    if c["dmax"] > 0.0:
        hw = max(0.0, hw - (sd - d))
    w = mf.GAMMA * d
    u = RHOW * GRAV * hw
    num = c["c"] + (w - u) * cos2 * math.tan(math.radians(c["phi"]))
    if jh is None:
        return num / (w * tanth * cos2)
    return num / (((w - u) * tanth + u * jh) * cos2)


def head_grad(c, kind):
    """全水頭の勾配 J。kind = 'land'(地表水なし)か 'lake'(静水の下)。"""
    if kind == "lake":
        return 0.0
    cx = mf.SDG[1] if c["sd"] == "g" else 0.0
    cy = mf.SDG[2] if c["sd"] == "g" else 0.0
    return math.hypot(mf.A + (1.0 - c["sat"]) * cx, mf.B + (1.0 - c["sat"]) * cy)


def check_fs(case):
    c = mf.CASES[case]
    fs = read_fs(case)
    worst = {"land": 0.0, "lake": 0.0}
    ncell = {"land": 0, "lake": 0}
    rng = {"land": [9.9e9, 0.0], "lake": [9.9e9, 0.0]}
    for i, j in interior():
        wet = [mf.h_of(c, a, b) > 0.0 for a, b in nbrs(i, j)]
        if all(wet):
            kind = "lake"
        elif not any(wet):
            kind = "land"
        else:
            continue                       # 汀線のセル(湖と陸が混じる)は比べない
        jh = head_grad(c, kind) if c["seep"] == 1 else None
        fe = fs_formula(c, i, j, jh)
        worst[kind] = max(worst[kind], abs(at(fs, i, j) / fe - 1.0))
        ncell[kind] += 1
        rng[kind] = [min(rng[kind][0], fe), max(rng[kind][1], fe)]
    nfail = 0
    print(f"== slide fs: safety factor against the formula, case {case} "
          f"(f_slide_seep = {c['seep']}, slide_dmax = {c['dmax']:g})")
    for kind in ("land", "lake"):
        if kind == "lake" and not c["lake"]:
            continue
        ok = worst[kind] <= TOL_FS and ncell[kind] >= 50
        nfail += 0 if ok else 1
        print(("  ok   " if ok else "  FAIL ") +
              f"{kind}: max |Fs/formula - 1| = {worst[kind]:.1e} (limit {TOL_FS:.0e}) over {ncell[kind]} cells, "
              f"formula Fs = {rng[kind][0]:.4f}-{rng[kind][1]:.4f}")
    return nfail


def check_pair(case1, case0, want):
    f1, f0 = read_fs(case1), read_fs(case0)
    c = mf.CASES[case1]
    dmax, dmin, n = 0.0, 9.9e9, 0
    for i, j in interior():
        wet = [mf.h_of(c, a, b) > 0.0 for a, b in nbrs(i, j)]
        if want == "differ" and c["lake"] and not all(wet):
            continue                       # 湖のケースの検出力は湖の下のセルで見る
        r = abs(at(f1, i, j) / at(f0, i, j) - 1.0)
        dmax, dmin, n = max(dmax, r), min(dmin, r), n + 1
    if want == "same":
        ok = dmax <= TOL_FS
        msg = f"max |Fs1/Fs0 - 1| = {dmax:.1e} (limit {TOL_FS:.0e})"
    else:
        ok = dmin >= 0.02
        msg = f"min |Fs1/Fs0 - 1| = {dmin:.3f} (must be >= 0.02), max = {dmax:.3f}"
    print(f"== slide fs pair: {case1} vs {case0} must {want}")
    print(("  ok   " if ok else "  FAIL ") + msg + f" over {n} cells")
    return 0 if ok else 1


def ledgers(case):
    """固体の台帳 Σhs + (1 − λ) Σ(z − z0) と、水の台帳 Σh + Σhg − Σhg0(湖は初期の水も引く)。"""
    c = mf.CASES[case]
    st = read_state(case)
    dz = h0 = hg0 = 0.0
    for j in range(1, NY + 1):
        for i in range(1, NX + 1):
            dz += at(st["z"], i, j) - mf.z_of(i, j)
            h0 += mf.h_of(c, i, j)
            hg0 += c["sat"] * mf.SY0 * mf.sd_of(c, i, j)
    solids = sum(st["hs"]) + (1.0 - mf.POROSITY) * dz
    water = sum(st["h"]) + sum(st["hg"]) - hg0 - h0
    return st, solids, water


def check_dmax1(case):
    c = mf.CASES[case]
    st, solids, water = ledgers(case)
    d = c["dmax"]
    e = {k: 0.0 for k in ("z", "sd", "hs", "hg", "h")}
    for i, j in interior():
        sd0 = mf.sd_of(c, i, j)
        e["z"] = max(e["z"], abs(mf.z_of(i, j) - at(st["z"], i, j) - d))
        e["sd"] = max(e["sd"], abs(at(st["sd"], i, j) - (sd0 - d)))
        e["hs"] = max(e["hs"], abs(at(st["hs"], i, j) - (1.0 - mf.POROSITY) * d))
        e["hg"] = max(e["hg"], abs(at(st["hg"], i, j) - mf.SY0 * (sd0 - d)))
        e["h"] = max(e["h"], abs(at(st["h"], i, j) - (c["sat"] * mf.SY0 * sd0 - mf.SY0 * (sd0 - d))))
    ok1 = max(e.values()) <= TOL_X
    ok2 = abs(solids) < TOL_SUM and abs(water) < TOL_W
    print(f"== slide dmax1: one update fluidizes exactly slide_dmax = {d:g} m, case {case}")
    print(("  ok   " if ok1 else "  FAIL ") + "interior cells: max error of z drop, sd, hs, hg, h = " +
          ", ".join(f"{e[k]:.1e}" for k in ("z", "sd", "hs", "hg", "h")) + f" m (limit {TOL_X:.0e})")
    print(("  ok   " if ok2 else "  FAIL ") + f"ledgers: solids {solids:.2e}, water {water:.2e} "
          f"(limits {TOL_SUM:.0e}, {TOL_W:.0e})")
    return (0 if ok1 else 1) + (0 if ok2 else 1)


def interior_sd(case, m=1):
    c = mf.CASES[case]
    st = read_state(case)
    vals = [at(st["sd"], i, j) for i, j in interior(m)]
    dzs = [abs(at(st["z"], i, j) - mf.z_of(i, j)) for i, j in interior(m)]
    return min(vals), max(vals), max(dzs), c


def check_wet(case1, case0, case2):
    nfail = 0
    print("== slide wet: f_slide_wet = 1 leaves cells that are unstable without pore pressure")
    mn, mx, dz, c = interior_sd(case1)
    ok = dz <= TOL_X and mn == c["sd"] and mx == c["sd"]
    nfail += 0 if ok else 1
    print(("  ok   " if ok else "  FAIL ") + f"{case1} (phi_s = {c['phi']:g}, dry Fs < 1, f_slide_wet = 1): "
          f"interior unchanged (max |dz| = {dz:.1e} m, sd = {mn:g}-{mx:g} m)")
    mn, mx, dz, c = interior_sd(case0)
    ok = mx == 0.0
    nfail += 0 if ok else 1
    print(("  ok   " if ok else "  FAIL ") + f"{case0} (same, f_slide_wet = 0): interior fluidized over the whole "
          f"layer (max sd = {mx:g} m)")
    mn, mx, dz, c = interior_sd(case2)
    ok = mx == 0.0
    nfail += 0 if ok else 1
    print(("  ok   " if ok else "  FAIL ") + f"{case2} (phi_s = {c['phi']:g}, dry Fs > 1, saturated, f_slide_wet = 1): "
          f"interior fluidized by pore pressure (max sd = {mx:g} m)")
    return nfail


def check_noflow(case1, case0):
    nfail = 0
    print("== slide noflow: f_slide_noflow = 1 does not judge cells under a dense mixture")
    # 縁から 2 列を除く: 1 回目に流動化しなかった縁のセルの隣は、2 回目に勾配が変わる
    mn, mx, dz, c = interior_sd(case1, 2)
    lim1 = c["sd"] - 1.2 * c["dmax"]
    ok = mn > lim1
    nfail += 0 if ok else 1
    print(("  ok   " if ok else "  FAIL ") + f"{case1} (f_slide_noflow = 1): interior sd = {mn:.3f}-{mx:.3f} m after two "
          f"updates (> {lim1:g}: fluidized once)")
    mn, mx, dz, c = interior_sd(case0, 2)
    lim0 = c["sd"] - 1.6 * c["dmax"]
    ok = mx < lim0
    nfail += 0 if ok else 1
    print(("  ok   " if ok else "  FAIL ") + f"{case0} (f_slide_noflow = 0): interior sd = {mn:.3f}-{mx:.3f} m "
          f"(< {lim0:g}: fluidized twice)")
    return nfail


def check_ledger(case):
    c = mf.CASES[case]
    st, solids, water = ledgers(case)
    dzmin = min(at(st["z"], i, j) - mf.z_of(i, j) for i, j in interior())
    ok1 = abs(solids) < TOL_SUM
    ok2 = abs(water) < TOL_W
    ok3 = dzmin < -0.5
    print(f"== slide ledger: conservation with fluidization, case {case}")
    print(("  ok   " if ok1 else "  FAIL ") + f"solids {solids:.2e} (limit {TOL_SUM:.0e})")
    print(("  ok   " if ok2 else "  FAIL ") + f"water {water:.2e} (limit {TOL_W:.0e})")
    print(("  ok   " if ok3 else "  FAIL ") + f"activity: min dz = {dzmin:.3f} m (< -0.5)")
    return sum(0 if ok else 1 for ok in (ok1, ok2, ok3))


def main():
    mode = sys.argv[1]
    if mode == "fs":
        nfail = check_fs(sys.argv[2])
    elif mode == "pair":
        nfail = check_pair(sys.argv[2], sys.argv[3], sys.argv[4])
    elif mode == "dmax1":
        nfail = check_dmax1(sys.argv[2])
    elif mode == "wet":
        nfail = check_wet(sys.argv[2], sys.argv[3], sys.argv[4])
    elif mode == "noflow":
        nfail = check_noflow(sys.argv[2], sys.argv[3])
    elif mode == "ledger":
        nfail = check_ledger(sys.argv[2])
    else:
        sys.exit("usage: Check_slide_fs.py fs|pair|dmax1|wet|noflow|ledger ...")
    print(f"=== slide {mode} check {'PASS' if nfail == 0 else f'FAIL ({nfail})'} ===")
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
