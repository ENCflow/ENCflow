#!/usr/bin/env python3
"""谷(2023)の竜ノ口山(TY)の VZ 計算の格子入力を作る(数値は論文の本文から)

土層厚の「線形分布」(論文 Ⅳ.1・Ⅳ.2): 0 cm から最大値まで 2.5 cm 刻みの区分が
同じ面積を占める。最大値は SL 100 cm(41 区分)、KT 175 cm(71 区分)、
MN 250 cm(101 区分)。1 区分を 1 セル(1 m × 1 m)で表し、流域ごとに 1 行の
区画にする。3 区画とも同じ柱(TY の土壌)を参照する(柱の共有)。

  python3 make_case.py [出力ディレクトリ(既定 data)]

出力: mask.txt(領域)、zone.txt(区画番号 1 = KT、2 = MN、3 = SL)、sd.txt(土層厚 m)
"""
import os
import sys

DZ = 0.025
ZONES = [("KT", 1, 1.75), ("MN", 2, 2.50), ("SL", 3, 1.00)]   # (名前, 区画番号, 最大の土層厚 m)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "data"
    os.makedirs(out, exist_ok=True)
    ncls = [int(round(dmax / DZ)) + 1 for _, _, dmax in ZONES]
    nx = max(ncls)
    mask, zone, sd = [], [], []
    for (name, z, dmax), n in zip(ZONES, ncls):
        mask.append(["1" if i < n else "0" for i in range(nx)])
        zone.append([str(z) if i < n else "0" for i in range(nx)])
        sd.append(["%.4f" % (i * DZ) if i < n else "0.0000" for i in range(nx)])
        print("  zone %d %s: %d classes, soil depth 0 - %.3f m" % (z, name, n, (n - 1) * DZ))
    for fn, rows in (("mask.txt", mask), ("zone.txt", zone), ("sd.txt", sd)):
        with open(os.path.join(out, fn), "w") as f:
            for r in rows:
                f.write(" ".join(r) + "\n")
    print("  grid nx = %d, ny = %d -> %s/" % (nx, len(ZONES), out))


if __name__ == "__main__":
    main()
