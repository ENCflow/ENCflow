#!/usr/bin/env python3
# examples/delta の入力生成: 河川が静水の海盆に突入してデルタを作る理想化地形
#   使い方: python3 make_init.py <case> <kind>   (case = base|sand|mud|varq|fix、kind = z|sd|rows)
#   z:    地盤高 (m。海面 0 m 基準)。西側 LCH m は幅 W の河道(河床 ZCH0 から勾配 S0 で下る)、
#         両岸は +ZLAND の乾いた非侵食の陸地。河口から LRAMP m の斜面で海盆底 ZSEA へ、残りは平坦な海盆
#   sd:   土層厚 (m)。河道内 SDCH = 可動、陸地と海盆底は 0 = 非侵食(海盆への堆積は sd を増やす)
#   rows: 西端の河道セルの行番号(区間流入の inflow_cell に使う)
import sys
import numpy as np

CASES = {
    #        NX   NY   DX   LCH   ZSEA
    "base": (200, 120, 5.0, 150.0, -2.0),   # 1000 x 600 m、海盆 2 m(docs/delta_plan.md §2.1)
    "sand": (240, 320, 5.0, 200.0, -1.5),   # 1200 x 1600 m、海盆 1.5 m(§2.4 砂主体)
    "mud":  (320, 520, 5.0, 200.0, -1.5),   # 1600 x 2600 m(§2.4 泥主体。南北 ±1300 m)
    "varq": (240, 320, 5.0, 200.0, -1.5),   # 1200 x 1600 m(§2.6 流量変動・定着なし)
    "fix":  (240, 320, 5.0, 200.0, -1.5),   # 1200 x 1600 m(§2.6 流量変動+定着+冠水減衰+河岸係数)
    "wave": (200, 120, 5.0, 150.0, -2.0),   # base + 沖波(docs/wave_plan.md。param_wave.txt)
}
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
    sd = np.where(inch, SDCH, 0.0)
    rows = [int(j) for j in np.arange(1, NY + 1)[inch[:, 0]]]
    return z, sd, rows

if __name__ == "__main__":
    case, kind = sys.argv[1], sys.argv[2]
    z, sd, rows = build(case)
    if kind == "rows":
        print(" ".join(str(j) for j in rows))
    else:
        np.savetxt(sys.stdout, {"z": z, "sd": sd}[kind], fmt="%.4f")
