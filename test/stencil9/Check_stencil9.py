#!/usr/bin/env python3
# test/stencil9 の検定(developer.md §96)。save_<構成>/state.dat(倍精度)の z を読む。
#   gauss : 9 点のクリープ(d = 1/3)がよく解像したガウス丘で解析解に一致する(重みの正規化)
#   hill  : 解像しきれない丘(σ = 2Δ)の、中心から同じ距離の格子軸寄りと斜めのセルの差
#           (r² = 25: (5,0)・(4,3)、r² = 50: (7,1)・(5,5))が、9 点(d = 1/3)で小さく、
#           5 点(対照)で大きい(検出器として働く)
#   strip : 幅 1・3 セルの帯の cos モードが、壁で塞がれた斜めの配分を振り替えたときの
#           1 次元の厳密な離散解 (1 − λΔt)^N に全セルで一致する(振り替えがなければ 1 − d・
#           (2(1 − d/2) + 1)/3 倍の拡散係数で遅れる)
#   splash: 乾式斜面侵食の雨滴項の侵食深から読んだ曲率 κ の、同じ距離のセルの差が、9 点の
#           κ(と ℓ = 2 m の 9 点の核)で小さく、5 点(対照)で大きい
#   値(丘・帯・格子・係数)は make_terrain.py・param_*.txt と対で保守する。
#   使い方: Check_stencil9.py [gauss|hill|strip|splash ...](省略時は全部)。終了コード 0 = PASS
import sys, math, struct

A, SIG, N, C = 1.0, 2.0, 81, 41           # z_hill2.txt(make_terrain.py)
D = 1.0                                     # creep_d
TOL_GAUSS = 5.0e-3                          # test/creep の Check_analytic.py と同じ許容
TOL_ISO9, MIN_ISO5_CREEP = 0.003, 0.01      # 9 点の差の上限(0.3 %)・5 点の差の下限(1 %)
TOL_ISO9_SPL, MIN_ISO5_SPL = 0.005, 0.02    # 曲率: 9 点 0.5 %・5 点 2 %
TOL_STRIP = 1.0e-9                          # 帯: 厳密な離散解との相対差
CA = 100.0                                  # spl_ca
fails = 0


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


def load_z(tag, nx, ny):
    # 書き並びは h, z, ...(m_state の save_state。test/creep の Check_hstar.py と同じ読み方)
    with open("save_" + tag + "/state.dat", "rb") as f:
        read_rle_array(f, nx * ny)
        z = read_rle_array(f, nx * ny)
    return lambda i, j: z[(j - 1) * nx + (i - 1)]


def load_txt(fn):
    rows = [[float(v) for v in line.split()] for line in open(fn) if line.strip()]
    return lambda i, j: rows[j - 1][i - 1]


def check(cond, msg):
    global fails
    print(("PASS: " if cond else "FAIL: ") + msg)
    if not cond:
        fails += 1


def gauss():
    # test/creep と同じガウス丘(A = 1 m、σ = 10 m、101 × 101、中心 (51, 51))、τ = 50 s
    z = load_z("gauss_c9", 101, 101)
    s2 = 100.0 + 2.0 * D * 50.0
    err = 0.0
    for j in range(1, 102):
        for i in range(1, 102):
            r2 = (i - 51) ** 2 + (j - 51) ** 2
            err = max(err, abs(z(i, j) - 100.0 / s2 * math.exp(-r2 / (2.0 * s2))))
    check(err < TOL_GAUSS, "gauss: 9-point creep (d = 1/3) max |z - z_ana| = %.3e m < %.0e m (normalisation of the weights)"
          % (err, TOL_GAUSS))


PAIRS = [(25.0, (5, 0), (4, 3)), (50.0, (7, 1), (5, 5))]


def iso(val, ref, label, tol9, min5, tags):
    for tag, nine in tags:
        v = val(tag)
        for r2, a, b in PAIRS:
            rel = (v(C + b[0], C + b[1]) - v(C + a[0], C + a[1])) / ref(r2)
            # 鏡像のセルが同じ値(対称性の確認)
            sym = abs(v(C + a[0], C + a[1]) - v(C - a[1], C + a[0])) / abs(ref(r2))
            if nine:
                check(abs(rel) < tol9 and sym < 1e-9,
                      "%s %s: r^2 = %g, (diagonal - axis)/ref = %+.3f %% (|.| < %.1f %%; symmetric %.1e)"
                      % (label, tag, r2, 100 * rel, 100 * tol9, sym))
            elif r2 == 25.0 or label == "creep":
                if label == "creep" and r2 != 50.0:
                    print("info: %s %s: r^2 = %g, (diagonal - axis)/ref = %+.3f %%" % (label, tag, r2, 100 * rel))
                    continue
                check(abs(rel) > min5,
                      "%s %s (5-point control): r^2 = %g, (diagonal - axis)/ref = %+.3f %% (|.| > %.0f %% = detector works)"
                      % (label, tag, r2, 100 * rel, 100 * min5))
            else:
                print("info: %s %s: r^2 = %g, (diagonal - axis)/ref = %+.3f %%" % (label, tag, r2, 100 * rel))


def hill():
    s2 = SIG ** 2 + 2.0 * D * 4.0
    ref = lambda r2: A * SIG ** 2 / s2 * math.exp(-r2 / (2.0 * s2))
    val = lambda tag: (lambda zz: (lambda i, j: zz(i, j) - 10.0))(load_z(tag, N, N))
    iso(val, ref, "creep", TOL_ISO9, MIN_ISO5_CREEP, [("hill_c5", False), ("hill_c9", True)])


def strip():
    k = math.pi / 40.0
    lam = D * 2.0 * (1.0 - math.cos(k))                  # 3 点の 1 次元ラプラシアンの固有値(Δ = 1 m)
    g = (1.0 - lam * 0.1) ** 1000                         # 陽解法 1000 ステップ(dt = 0.1 s、100 s)
    for nx in (1, 3):
        z0 = load_txt("z_strip%d.txt" % nx)
        z = load_z("strip%d_c9" % nx, nx, 40)
        err = max(abs(z(i, j) / z0(i, j) - g) / g for j in range(1, 41) for i in range(1, nx + 1)
                  if abs(z0(i, j)) > 1e-3)
        ratio = math.log(z(1, 1) / z0(1, 1)) / math.log(g)
        check(err < TOL_STRIP, "strip%d: amplitude after 100 s matches the exact discrete decay %.9f within %.1e "
              "(effective diffusivity %.6f x D; without the reassignment it would be %.3f)"
              % (nx, g, err, ratio, (1 - 1/3.) if nx == 1 else (2 * (1 - 1/6.) + 1) / 3))


def splash():
    z0 = load_txt("z_hill2.txt")
    def kap(tag):
        z = load_z(tag, N, N)
        dzf = z0(11, 11) - z(11, 11)                     # 平坦なセル(κ = 0)の侵食深 = P kr dts
        return lambda i, j: ((z0(i, j) - z(i, j)) / dzf - 1.0) / CA
    for lc, tags in ((0.0, [("hill_s5", False), ("hill_s9", True)]),
                     (2.0, [("hill_lc_s5", False), ("hill_lc_s9", True)])):
        se2 = SIG ** 2 + lc ** 2
        amp = SIG ** 2 / se2
        ref = lambda r2, se2=se2, amp=amp: amp * math.exp(-r2 / (2 * se2)) * (r2 / se2 ** 2 - 2 / se2)
        iso(kap, ref, "splash(lc = %g)" % lc, TOL_ISO9_SPL, MIN_ISO5_SPL, tags)


modes = sys.argv[1:] or ["gauss", "hill", "strip", "splash"]
for m in modes:
    {"gauss": gauss, "hill": hill, "strip": strip, "splash": splash}[m]()
print("== stencil9: %s ==" % ("PASS" if fails == 0 else "FAIL (%d)" % fails))
sys.exit(0 if fails == 0 else 1)
