#!/usr/bin/env python3
"""estuary_barrage の入力データを data/ に生成する(make が呼ぶ)。

理想化した河口域(格子 40 m、東西 90 列 × 南北 24 行 = 3.6 km × 0.96 km)。
  i = 1..75  : 陸(地盤高 +3.0 m)と河道(幅 120 m = 行 11〜13、河床 −3.0 → −4.0 m)
  i = 76..87 : 計算する海(水深 5 m = 地盤高 −5.0 m。初期は全層が塩水)
  i = 88..90 : 海域マスク(潮位を強制する全塩水の境界)
帯水層(層1)の底は全域 −10 m(土層厚 sd = z + 10)。海底下の帯水層は初期に
全層塩水(fn_salt_hgs0 = sd·sy)、陸の帯水層は空で始め、最初の出水と強雨で
淡水を満たす(初期の地下貯留を直接与える入力はないため。gwflow の章)。
河道マスク rw.txt(河道 3 行 × 75 列)は目詰まりした河床のケースの河床交換能に使う。
堰あり: 河口から 500 m(i = 63)の河道 3 セルを天端 +1.0 m にした地形
(ゲートを閉じて越流させている平常時の河口堰。満潮位 +0.6 m より高い)。
潮位 tide.txt は M2 分潮(周期 12.42 h)振幅 0.6 m の正弦を 30 分刻みで
999 点(20.8 日)の &list_tide にする。
"""
import os
import numpy as np

NX, NY, DX = 90, 24, 40.0
I_COAST, I_SEA, I_WEIR = 75, 88, 63      # 陸の最終列・海域マスクの最初の列・堰の列(1 始まり)
J_RIVER = range(11, 14)                  # 河道の行(1 始まり)
Z_LAND, Z_SEA, Z_CREST, Z_BOT = 3.0, -5.0, 1.0, -10.0
SY = 0.2                                 # 比湧水量(param の sy0 と同じ値)
E_POOL = 1.2                             # 堰ありの初期湛水位(堰上流の河道)
AMP, PERIOD = 0.6, 745.2                 # 潮位振幅 (m)・M2 周期 (min)


def main(out="data"):
    os.makedirs(out, exist_ok=True)
    z = np.full((NY, NX), Z_LAND)
    for i in range(1, I_COAST + 1):
        zb = -3.0 - (i - 1) / (I_COAST - 1)      # 河床 −3.0(上流端)→ −4.0 m(河口)
        for j in J_RIVER:
            z[j - 1, i - 1] = zb
    z[:, I_COAST:] = Z_SEA
    zw = z.copy()
    for j in J_RIVER:
        zw[j - 1, I_WEIR - 1] = Z_CREST

    sw = np.zeros((NY, NX), dtype=int)
    sw[:, I_SEA - 1:] = 1
    hss0 = np.zeros((NY, NX))
    hss0[:, I_COAST:] = 99.0                     # 計算する海は全層塩水(min(h, 値))
    hgs0 = np.zeros((NY, NX))
    hgs0[:, I_COAST:] = (Z_SEA - Z_BOT) * SY     # 海底下の帯水層は全層塩水
    e_bar = np.zeros((NY, NX))
    for j in J_RIVER:
        e_bar[j - 1, :I_WEIR - 1] = E_POOL       # 堰上流の河道は湛水位から

    for name, zz, ee in (("nobarrage", z, np.zeros((NY, NX))), ("barrage", zw, e_bar)):
        np.savetxt(os.path.join(out, f"z_{name}.txt"), zz, fmt="%.4f")
        np.savetxt(os.path.join(out, f"sd_{name}.txt"), zz - Z_BOT, fmt="%.4f")
        np.savetxt(os.path.join(out, f"e0_{name}.txt"), ee, fmt="%.2f")
    np.savetxt(os.path.join(out, "sw.txt"), sw, fmt="%d")
    rw = np.zeros((NY, NX), dtype=int)
    for j in J_RIVER:
        rw[j - 1, :I_COAST] = 1                  # 河道マスク(目詰まりした河床のケースが使う)
    np.savetxt(os.path.join(out, "rw.txt"), rw, fmt="%d")
    np.savetxt(os.path.join(out, "hss0.txt"), hss0, fmt="%.1f")
    np.savetxt(os.path.join(out, "hgs0.txt"), hgs0, fmt="%.2f")

    t = np.arange(999) * 30.0
    eta = AMP * np.sin(2.0 * np.pi * t / PERIOD)
    with open(os.path.join(out, "tide.txt"), "w") as f:
        f.write("! estuary_barrage の潮位(gen_data.py が生成。M2 振幅 0.6 m、30 分刻み)\n")
        f.write("&list_tide\n  titype = 2\n  hsea0 = 2.0\n  dt_tiupdate = 1\n")
        for k, (a, b) in enumerate(zip(t, eta)):
            f.write(f"  tival(1:2,{k + 1}) = {a:.1f}, {b:.4f}\n")
        f.write("/\n")


if __name__ == "__main__":
    main()
