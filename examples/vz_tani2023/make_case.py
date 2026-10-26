#!/usr/bin/env python3
"""谷(2023)の VZ 計算の格子入力を作る(数値は論文の本文から)

土層厚の「線形分布」(論文 Ⅳ.1〜Ⅳ.3): 0 cm から最大値まで 2.5 cm 刻みの区分が
同じ面積を占める。1 区分を 1 セル(1 m × 1 m)で表し、流域ごとに 1 行の区画にする。

  grid_ty  : 竜ノ口山。KT 0〜175 cm(71 区分)、MN 0〜250 cm(101)、SL 0〜100 cm(41)の
             3 区画が同じ柱(TY の土壌)を参照する(論文 Ⅳ.2)
  grid_ki  : 桐生。0〜130 cm(53 区分。平均 65 cm が中央値になる最大値。Ⅳ.3)
  grid_mr  : Mettman Ridge の CB1。0〜200 cm(81 区分。Ⅳ.1)
  grid_kiex: 桐生の小斜面 Plot 2。土層厚 50 cm の 1 区画(柱の下端を読む。Ⅳ.1)

  python3 make_case.py [出力ディレクトリ(既定 data)]

出力: <出力>/grid_<地点>/ に mask.txt(領域)、zone.txt(区画番号)、sd.txt(土層厚 m)
"""
import os
import sys

DZ = 0.025
SITES = {
    "grid_ty": [("KT", 1, 1.75), ("MN", 2, 2.50), ("SL", 3, 1.00)],   # (名前, 区画番号, 最大の土層厚 m)
    "grid_ki": [("KI", 1, 1.30)],
    "grid_mr": [("CB1", 1, 2.00)],
}


def write(out, rows3):
    os.makedirs(out, exist_ok=True)
    for fn, rows in zip(("mask.txt", "zone.txt", "sd.txt"), rows3):
        with open(os.path.join(out, fn), "w") as f:
            for r in rows:
                f.write(" ".join(r) + "\n")


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "data"
    for site, zones in SITES.items():
        ncls = [int(round(dmax / DZ)) + 1 for _, _, dmax in zones]
        nx = max(ncls)
        mask, zone, sd = [], [], []
        for (name, z, dmax), n in zip(zones, ncls):
            mask.append(["1" if i < n else "0" for i in range(nx)])
            zone.append([str(z) if i < n else "0" for i in range(nx)])
            sd.append(["%.4f" % (i * DZ) if i < n else "0.0000" for i in range(nx)])
            print("  %s zone %d %s: %d classes, soil depth 0 - %.3f m" % (site, z, name, n, (n - 1) * DZ))
        write(os.path.join(base, site), (mask, zone, sd))
        print("  %s: nx = %d, ny = %d" % (site, nx, len(zones)))
    # KIEX: 土層厚 50 cm の 3 セル(同じ値。柱の下端 = 土層の底の排水を読む)
    write(os.path.join(base, "grid_kiex"), ([["1"] * 3], [["1"] * 3], [["0.5000"] * 3]))
    print("  grid_kiex: nx = 3, ny = 1, soil depth 0.500 m")


if __name__ == "__main__":
    main()
