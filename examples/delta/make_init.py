#!/usr/bin/env python3
# examples/delta の入力生成: 河川が静水の海盆に突入してデルタを作る理想化地形
#   使い方: python3 make_init.py <case> <kind>   (case = base|sand|mud|varq|fix|wave|baseqb|tide、kind = z|sd|rows|sw|tide)
#   z:    地盤高 (m。海面 0 m 基準)。西側 LCH m は幅 W の河道(河床 ZCH0 から勾配 S0 で下る)、
#         両岸は +ZLAND の乾いた非侵食の陸地。河口から LRAMP m の斜面で海盆底 ZSEA へ、残りは平坦な海盆
#   sd:   土層厚 (m)。河道内 SDCH = 可動、陸地と海盆底は 0 = 非侵食(海盆への堆積は sd を増やす)。
#         固定給砂の構成(FIXEDCH)は河道も 0 = 給砂を運ぶ固い水路(河口に出てから動く)
#   rows: 西端の河道セルの行番号(区間流入の inflow_cell に使う)
#   sw:   海域マスク(1 = 海)。東端 NSEA 列を潮位を与える海の帯にする(段 6 の tide)
#   tide: 潮位の &list_tide(M2 分潮。周期 TM2 分、振幅 ATIDE m の正弦を 1/48 周期ごと、NCYC 周期分)
import sys
import numpy as np

CASES = {
    #        NX   NY   DX   LCH   ZSEA
    "base": (200, 120, 5.0, 150.0, -2.0),   # 1000 x 600 m、海盆 2 m(段 1)
    "sand": (240, 320, 5.0, 200.0, -1.5),   # 1200 x 1600 m、海盆 1.5 m(段 2 砂の多いデルタ)
    "mud":  (320, 520, 5.0, 200.0, -1.5),   # 1600 x 2600 m(段 2 泥の多いデルタ。南北 ±1300 m)
    "varq": (240, 320, 5.0, 200.0, -1.5),   # 1200 x 1600 m(段 3 流量変動・定着なし)
    "fix":  (240, 320, 5.0, 200.0, -1.5),   # 1200 x 1600 m(段 3 流量変動+定着+冠水減衰+河岸係数)
    "wave": (200, 120, 5.0, 150.0, -2.0),   # base + 沖波(段 4・5。param_wave.txt・param_wfsed.txt)
    "baseqb": (200, 120, 5.0, 150.0, -2.0), # base の固定給砂版(段 4 の波なしの基準。param_baseqb.txt)
    "tide": (200, 120, 5.0, 150.0, -2.0),   # baseqb + 潮汐(段 6。param_tide.txt・param_notide.txt)
}
FIXEDCH = {"wave", "baseqb", "tide"}       # 固定給砂の構成: 陸地内の河道も非侵食(土層 0。給砂はそのまま通過)
NSEA, TM2, ATIDE, NCYC = 3, 745.2, 1.0, 6  # 海の帯の列数、M2 の周期 (min)、振幅 (m) = 潮差 2 m、周期数
W, LRAMP, S0, ZCH0, ZLAND, SDCH = 30.0, 50.0, 0.001, -1.0, 1.5, 3.0

def build(case):
    NX, NY, DX, LCH, ZSEA = CASES[case]
    YC = NY * DX / 2.0
    x = (np.arange(1, NX + 1) - 0.5) * DX
    n = (np.arange(1, NY + 1) - 0.5) * DX - YC
    X, N = np.meshgrid(x, n)
    zmouth = ZCH0 - S0 * LCH
    inch = (X <= LCH) & (np.abs(N) <= W / 2)
    z = np.where(X <= LCH, np.where(inch, ZCH0 - S0 * X, ZLAND),
                 np.where(X <= LCH + LRAMP, zmouth + (ZSEA - zmouth) * (X - LCH) / LRAMP, ZSEA))
    sd = np.where(inch, 0.0 if case in FIXEDCH else SDCH, 0.0)
    rows = [int(j) for j in np.arange(1, NY + 1)[inch[:, 0]]]
    return z, sd, rows

if __name__ == "__main__":
    case, kind = sys.argv[1], sys.argv[2]
    z, sd, rows = build(case)
    if kind == "rows":
        print(" ".join(str(j) for j in rows))
    elif kind == "sw":
        sw = np.zeros(z.shape, dtype=int)
        sw[:, -NSEA:] = 1
        np.savetxt(sys.stdout, sw, fmt="%d")
    elif kind == "tide":
        # 初期水位 0 m(平均潮位)から上げ潮で始める。hsea0 は海盆の水深(2 m)と同じにする
        t = np.arange(48 * NCYC + 1) * TM2 / 48
        eta = ATIDE * np.sin(2 * np.pi * t / TM2)
        print("&list_tide\n  titype = 2\n  hsea0 = 2.0\n  dt_tiupdate = 1")
        for k, (a, b) in enumerate(zip(t, eta), 1):
            print("  tival(1:2,%d) = %.4f, %.4f" % (k, a, b))
        print("/")
    else:
        np.savetxt(sys.stdout, {"z": z, "sd": sd}[kind], fmt="%.4f")
