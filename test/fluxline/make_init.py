#!/usr/bin/env python3
# test/fluxline の入力生成(流量測線の角度掃引。developer.md §24.3)
#   zinit.txt・hinit.txt : 東西に長い直線水路(500 × 21 セル、Δx = 1 m、勾配 0.002 で西が高い、
#                          初期水深は Manning の等流水深 0.5 m)。南北の縁は領域の壁
#   record_stair.txt     : セル番号指定(flxytype = 0。ENC は階段面のエッジ流量)の測線
#   record_xy.txt        : 実座標指定(flxytype = 1。セル内線分成分の積算)の測線
#   どちらも、壁から壁まで横切る測線(角度 φ = 流れに直交する向きからの傾き 0〜85°)、
#   内部の行だけを横切る測線(同じ角度)、流れに平行な測線を並べる。測線の幾何は
#   Check_fluxline.py が出力 CSV の見出しから読む
# 水路と流れの定数は param_*.txt と対で保守する
import math

NX, NY = 500, 21
S, Z0, H0 = 0.002, 10.0, 0.5
I0 = 100                                           # 測線の南端の列(x = 99.5 m)
PHI = [0, 10, 20, 30, 40, 45, 50, 60, 70, 80, 85]  # 実座標指定の角度 (°)

with open("zinit.txt", "w") as f:
    for j in range(1, NY + 1):
        f.write(" ".join("%.6f" % (Z0 - S * (i - 0.5)) for i in range(1, NX + 1)) + "\n")
with open("hinit.txt", "w") as f:
    for j in range(1, NY + 1):
        f.write(" ".join("%.6f" % H0 for i in range(1, NX + 1)) + "\n")

# セル番号指定: 始点 R が南、終点 L が北(R → L の右側 = 東 = 下流が正)。
# 壁から壁: 行 21 → 1(列の差 dx ≈ 20 tan φ)。内部: 行 16 → 6(dx ≈ 10 tan φ)と、
# 長さ違いの直交測線 2 本(行 14 → 8、18 → 4)。平行: 行 11 を西 → 東(右側 = 南)
stair = [(I0, NY, I0 + round(20 * math.tan(math.radians(p))), 1) for p in PHI]
stair += [(I0, 16, I0 + round(10 * math.tan(math.radians(p))), 6) for p in PHI]
stair += [(I0, 14, I0, 8), (I0, 18, I0, 4), (I0, 11, I0 + 50, 11)]
# 実座標指定(南西端が原点の局所座標 m): 壁から壁は y = 1e-6(南の縁はちょうど 0 だと
# 領域外の行に帰属する)→ 21 m。内部は y = 5.3 → 15.8 m。平行は y = 10.3 m を西 → 東
x0 = I0 - 0.5
xy = [(x0, 1.0e-6, x0 + NY * math.tan(math.radians(p)), float(NY)) for p in PHI]
xy += [(x0, 5.3, x0 + 10.5 * math.tan(math.radians(p)), 15.8) for p in PHI]
xy += [(x0, 10.3, x0 + 50.0, 10.3)]

with open("record_stair.txt", "w") as f:
    f.write("&list_record\n  flxytype = 0\n")
    for n, l in enumerate(stair, 1):
        f.write("  flxy(:,%d) = %d, %d, %d, %d\n" % ((n,) + l))
    f.write("/\n")
with open("record_xy.txt", "w") as f:
    f.write("&list_record\n  flxytype = 1\n")
    for n, l in enumerate(xy, 1):
        f.write("  flxy(:,%d) = %.6f, %.6f, %.6f, %.6f\n" % ((n,) + l))
    f.write("/\n")
