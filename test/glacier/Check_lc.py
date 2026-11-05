#!/usr/bin/env python3
# 侵食の結合長 gl_lc の検定(構成 5・5b・5c・5d。developer.md §45.3)
#   V 字谷を満たした氷が 10 年(地形時間)削った後の、谷を横切る侵食の形
#   (x = 2〜4 km の列で平均した dz(y) = Z9998 − Z0000)を比べて次を確かめる:
#     (1) gl_lc = 400 m では Δx = 200 m(構成 5)と 100 m(構成 5b。2 行ずつ平均して
#         200 m に揃える)の差が相対 L1 で 5% 未満(格子によらない)
#     (2) gl_lc = 400 m の侵食は gl_lc = 0(構成 5c)より氷の幅に広がる
#         (侵食が最大値の半分を超える幅が 2 倍以上、氷のある範囲の平均/最大が
#         0.15 以上大きい)
#     (3) gl_lc = 400 m では侵食の大きさが谷の軸から氷の縁へ単調に減る
#         (縁のセルの「氷の崖」が駆動応力に入らない)
#     (4) gl_lc = 0 では (1) と同じ比較が 5% を超える(局所の τb の形が格子で
#         変わり、この検定が格子依存を検出できることの確認)
#     (5) 侵食は氷のあるセルだけ、(6) 隆起なし・NaN なし
#   (5) の「氷のない」は、終了時の氷厚(save_<case>/glacier.dat の全桁)と初期の氷厚がともに 0 のセル。
#   分布出力 Hi は小数 4 桁で、8 近傍の 9 点(gl_diagratio > 0)では谷壁の縁のセルに 1e-7 m 級の氷が
#   入って侵食される(氷はあるので正しい)のを 0.0000 と読んで誤って数えたため(§99)
#   使い方: Check_lc.py(result_lc, result_lc2, result_lc0, result_lc02 と save_* を読む)
import math
import struct
import sys

CASES = {"lc": 200.0, "lc2": 100.0, "lc0": 200.0, "lc02": 100.0}
LX = 6000.0
XSEL = (2000.0, 4000.0)


def read_rec(f):
    n = struct.unpack("<i", f.read(4))[0]
    payload = f.read(n)
    n2 = struct.unpack("<i", f.read(4))[0]
    assert n == n2, "record marker mismatch"
    return payload


def read_rle_array(f, ntot):
    # m_restart の restart_write_cell の形式(test/lava/Check_lava.py と同じ読み方)
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


def read_field(fn):
    rows = []
    for line in open(fn):
        vals = [float(w) for w in line.split()]
        if vals:
            rows.append(vals)
    return rows


def profile(case, dx):
    z0 = read_field(f"result_{case}/Z0000.txt")
    z1 = read_field(f"result_{case}/Z9998.txt")
    hi = read_field(f"result_{case}/Hi9998.txt")
    hi0 = read_field(f"result_{case}/Hi0000.txt")
    ny, nx = len(z0), len(z0[0])
    with open(f"save_{case}/glacier.dat", "rb") as f:
        hix = read_rle_array(f, nx * ny)          # 終了時の氷厚(全桁。行は j = 1 から)
    cols = [i for i in range(nx) if XSEL[0] <= (i + 0.5) * dx <= XSEL[1]]
    prof, hprof = [], []
    nan, up, out = 0, -1.0e30, 0
    for j in range(ny):
        s = sh = 0.0
        for i in range(nx):
            dz = z1[j][i] - z0[j][i]
            if math.isnan(dz) or math.isnan(hi[j][i]):
                nan += 1
                continue
            up = max(up, dz)
            if dz < -1.0e-9 and hix[j * nx + i] <= 0.0 and hi0[j][i] <= 0.0:
                out += 1
        for i in cols:
            s += z1[j][i] - z0[j][i]
            sh += hi[j][i]
        prof.append(s / len(cols))
        hprof.append(sh / len(cols))
    return prof, hprof, nan, up, out


def coarsen(p):
    return [0.5 * (p[2 * k] + p[2 * k + 1]) for k in range(len(p) // 2)]


def rel_l1(a, b):
    return sum(abs(x - y) for x, y in zip(a, b)) / sum(abs(x) for x in a)


def half_width(p, dx):
    m = min(p)
    return sum(1 for v in p if v < 0.5 * m) * dx


def flatness(p, h):
    ice = [v for v, hh in zip(p, h) if hh > 1.0]
    return (sum(ice) / len(ice)) / min(p)


def monotone_from_axis(p):
    # 谷の軸は中央の 2 行の境界。軸から縁へ |dz| が増えないこと(氷のない行の 0 を含む)
    n = len(p)
    half = [abs(v) for v in p[n // 2:]]
    other = [abs(v) for v in reversed(p[:n // 2])]
    ok = all(half[k + 1] <= half[k] + 1.0e-6 for k in range(len(half) - 1))
    ok = ok and all(other[k + 1] <= other[k] + 1.0e-6 for k in range(len(other) - 1))
    return ok


rc = 0
res = {}
for case, dx in CASES.items():
    p, h, nan, up, out = profile(case, dx)
    res[case] = (p, h, dx)
    print(f"lc[{case:4s}] dx = {dx:5.0f} m: max erosion {-min(p):.3f} m, half-max width {half_width(p, dx):6.0f} m, "
          f"mean/max within ice {flatness(p, h):.3f}, NaN {nan}, max dz {up:.2e}, eroded ice-free cells {out}")
    if nan > 0:
        print(f"FAIL: NaN in result_{case}")
        rc = 1
    if up > 1.0e-9:
        print(f"FAIL: terrain rose in result_{case}")
        rc = 1
    if out > 0:
        print(f"FAIL: erosion outside the ice in result_{case}")
        rc = 1

d_lc = rel_l1(res["lc"][0], coarsen(res["lc2"][0]))
d_loc = rel_l1(res["lc0"][0], coarsen(res["lc02"][0]))
print(f"lc: cross-valley erosion, dx = 200 m vs 100 m (averaged to 200 m): relative L1 = {d_lc:.4f} "
      f"with gl_lc = 400 m (tol 0.05), {d_loc:.4f} with gl_lc = 0 (must exceed 0.05)")
if d_lc >= 0.05:
    print("FAIL: erosion profile with gl_lc depends on the grid")
    rc = 1
if d_loc <= 0.05:
    print("FAIL: the comparison no longer detects the grid dependence of the local law")
    rc = 1

w_lc = half_width(res["lc"][0], 200.0)
w_loc = half_width(res["lc0"][0], 200.0)
f_lc = flatness(res["lc"][0], res["lc"][1])
f_loc = flatness(res["lc0"][0], res["lc0"][1])
print(f"lc: half-max width {w_lc:.0f} m (gl_lc = 400) vs {w_loc:.0f} m (gl_lc = 0), "
      f"mean/max within ice {f_lc:.3f} vs {f_loc:.3f}")
if w_lc < 2.0 * w_loc or f_lc < f_loc + 0.15:
    print("FAIL: erosion with gl_lc is not spread over the ice width")
    rc = 1

for case in ("lc", "lc2"):
    if not monotone_from_axis(res[case][0]):
        print(f"FAIL: erosion with gl_lc does not decrease monotonically from the axis to the ice margin ({case})")
        rc = 1
print("lc: erosion decreases monotonically from the axis to the margin with gl_lc:",
      all(monotone_from_axis(res[c][0]) for c in ("lc", "lc2")),
      "(gl_lc = 0, dx = 200 m:", str(monotone_from_axis(res["lc0"][0])) + ")")

sys.exit(rc)
