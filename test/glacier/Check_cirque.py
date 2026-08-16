#!/usr/bin/env python3
# カール形成スモークテストの検定
#   result_cirque/ の Z0000(初期地形)・Z9998(最終地形)・Hi9998(最終氷厚)
#   から次を確認する:
#     (1) 氷河が形成された(max Hi > 1 m)
#     (2) 氷河下で侵食が起きた(min(Z9998 - Z0000) < -0.01 m)
#     (3) 隆起はしていない(max(Z9998 - Z0000) <= 0)
#     (4) 場に NaN がない
#   使い方: Check_cirque.py [resultdir]
import sys
import math

NX = NY = 81
resultdir = sys.argv[1] if len(sys.argv) > 1 else "result_cirque"


def read_field(fn):
    rows = []
    for line in open(fn):
        vals = [float(w) for w in line.split()]
        if vals:
            rows.append(vals)
    assert len(rows) == NY and len(rows[0]) == NX, f"bad shape in {fn}"
    return rows


z0 = read_field(f"{resultdir}/Z0000.txt")
z1 = read_field(f"{resultdir}/Z9998.txt")
hi = read_field(f"{resultdir}/Hi9998.txt")

rc = 0
himax, dzmin, dzmax, nan = 0.0, 0.0, -1.0e30, 0
for j in range(NY):
    for i in range(NX):
        if any(math.isnan(v) for v in (z0[j][i], z1[j][i], hi[j][i])):
            nan += 1
            continue
        himax = max(himax, hi[j][i])
        dz = z1[j][i] - z0[j][i]
        dzmin = min(dzmin, dz)
        dzmax = max(dzmax, dz)

print(f"cirque: max Hi = {himax:.3f} m, dz range = [{dzmin:.4f}, {dzmax:.4f}] m, "
      f"NaN cells = {nan}")
if nan > 0:
    print("FAIL: NaN in output fields")
    rc = 1
if himax <= 1.0:
    print("FAIL: no glacier formed (max Hi <= 1 m)")
    rc = 1
if dzmin >= -0.01:
    print("FAIL: no glacial erosion detected")
    rc = 1
if dzmax > 1.0e-9:
    print("FAIL: terrain rose (erosion must only lower z)")
    rc = 1

sys.exit(rc)
