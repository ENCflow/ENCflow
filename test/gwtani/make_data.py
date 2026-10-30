#!/usr/bin/env python3
# test/gwtani の入力生成(谷(Tani)型のシナリオ: 急勾配・薄い土層の斜面。developer.md §16.7)
#   斜面は南北に長い 1 × 40 セルの帯(Δx = Δy = 5 m、長さ L = 200 m。北端 = 分水界)で、その南に
#   渓流のセルを 1 行置く(計 41 行)。MPI の帯分割(j 方向)が斜面方向に入るよう、帯を j 方向に置く。
#   基盤(土層の底)は一様勾配 S_b = 0.5 の平面 z_b = ZB0 − S_b·s(s = (j − 0.5) Δy は分水界から
#   の距離)で、地表は z = z_b + d(土層厚 d を基盤に載せる。土層厚を変えても基盤の勾配は同じ)。
#   渓流のセル(j = 41)は地下水の出口: 地表を基盤面の延長(z = ZB0 − S_b·s)に置き、土層厚
#   D_DRAIN = 2 m を最初のステップで満たす(h_init.txt の初期水深 H_DRAIN。浸透能が十分大きい)。
#   飽和したセルの水頭は地表 + 湛水なので、斜面の最下段の地下水は基盤面の高さへ抜ける
#   (浸出面。領域の縁は側方流の無流束なので、渓流がないと下端に水がたまって上流へ戻る)。
#   data_gwtani/z_<名前>.txt・sd_<名前>.txt:
#     uni_thin  : d = 0.38 m 一様(薄い。斜面の下側 2/3 が飽和する)
#     uni_thick : d = 2.0 m 一様(厚い。飽和しない)
#     thin_toe  : d = 3.0 → 0.3 m(分水界から下端へ直線的に薄くなる。谷(Tani)型)
# 値は param*.txt・Check_gwtani.py と対で保守する
import os

NY, DY, SB, ZB0 = 40, 5.0, 0.5, 120.0     # 斜面の行数・格子間隔・基盤の勾配・基盤の標高の基準
D_DRAIN, H_DRAIN = 2.0, 0.5                 # 渓流のセルの土層厚と初期水深(sy0 = 0.2 で 0.4 m が地下へ)
PROFILES = {
    "uni_thin": lambda s: 0.38,
    "uni_thick": lambda s: 2.0,
    "thin_toe": lambda s: 3.0 - 2.7 * s / (NY * DY),
}

os.makedirs("data_gwtani", exist_ok=True)
for name, dfun in PROFILES.items():
    with open(f"data_gwtani/z_{name}.txt", "w") as fz, open(f"data_gwtani/sd_{name}.txt", "w") as fd:
        for j in range(1, NY + 1):
            s = (j - 0.5) * DY
            d = dfun(s)
            fz.write("%.12f\n" % (ZB0 - SB * s + d))
            fd.write("%.12f\n" % d)
        s = (NY + 0.5) * DY                  # 渓流のセル
        fz.write("%.12f\n" % (ZB0 - SB * s))
        fd.write("%.12f\n" % D_DRAIN)
with open("data_gwtani/h_init.txt", "w") as f:
    f.write("0.0\n" * NY + "%.12f\n" % H_DRAIN)
