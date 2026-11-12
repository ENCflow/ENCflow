#!/usr/bin/env python3
# examples/bridge_wood_jam の入力生成(引数なしで data/ に全ファイルを書く。make が呼ぶ)
#   橋に流木が掛かって溜まり、川が堰き上がって氾濫原(住宅地を想定した平地)へあふれ、橋を
#   迂回して流れる現象の模式実験。行 1 が北(図の上)、列 1 が西(上流)。西から東へ流れる。
#     行  1..48 : 氾濫原(幅 240 m。河床 + 3.5 m。粗度 0.05)
#     行 49..52 : 河道(幅 20 m = 4 セル。河床 z = 10 − 0.002 x。粗度 0.03)。掘り込み河道で堤防はない
#     行 53..60 : 南の台地(河床 + 7 m。浸水しない)
#     列 240    : 橋(x = 1195〜1200 m)。河道の 4 セルが流木の捕捉セル。桁・橋脚・取付道路は持たない
#     列 61..120: 上流から来る流木の供給の代用。この区間の河道に立木ストック 0.03 m3/m2(180 m3)を
#                 置き、水深が dw_hrec を超える出水のピーク前後に流木になる
#   出力: z.txt(標高)、h0.txt(平水 30 m3/s の等流水深)、rn.txt(粗度)、stock.txt(立木ストック)、
#         trap_0.3.txt・trap_0.1.txt(捕捉率 E の分布。橋の 4 セルだけ)
#   値は現象を見やすくするための模式的な設定で、特定の川・橋を再現したものではない
import os
import numpy as np

NX, NY, DX = 320, 60, 5.0
S, Z0 = 0.002, 10.0
D_BANK, D_TER = 3.5, 7.0            # 氾濫原・台地の高さ(河床から。m)
J_CH1, J_CH2 = 49, 52               # 河道の行
I_BR = 240                          # 橋の列(上流端から 1200 m。堰上げが上流端に届かない長さ)
I_ST1, I_ST2 = 61, 120              # 流木の供給の代用にする区間(列。x = 300〜600 m)
STOCK = 0.03                        # その区間の立木ストック (m3/m2)
N_CH, N_FP = 0.03, 0.05             # 粗度(河道、氾濫原と台地)
Q_BASE, Q_PEAK = 30.0, 137.3        # 平水とピークの流量 (m3/s)。param*.txt の inflow_val と対


def uniform_depth(q_total):
    """幅 20 m の河道の等流水深(2 次元計算なので側壁の摩擦なし。径深 = 水深)"""
    q = q_total / ((J_CH2 - J_CH1 + 1) * DX)
    return (q * N_CH / np.sqrt(S)) ** 0.6


def main():
    os.makedirs("data", exist_ok=True)
    z = np.zeros((NY, NX))
    h0 = np.zeros((NY, NX))
    rn = np.full((NY, NX), N_FP)
    stock = np.zeros((NY, NX))
    trap = np.zeros((NY, NX))
    xc = (np.arange(NX) + 0.5) * DX
    bed = Z0 - S * xc
    hb = uniform_depth(Q_BASE)
    for j in range(1, NY + 1):
        if j < J_CH1:
            z[j - 1] = bed + D_BANK
        elif j <= J_CH2:
            z[j - 1] = bed
            h0[j - 1] = hb
            rn[j - 1] = N_CH
            stock[j - 1, I_ST1 - 1:I_ST2] = STOCK
            trap[j - 1, I_BR - 1] = 1.0
        else:
            z[j - 1] = bed + D_TER
    np.savetxt("data/z.txt", z, fmt="%.4f")
    np.savetxt("data/h0.txt", h0, fmt="%.4f")
    np.savetxt("data/rn.txt", rn, fmt="%.3f")
    np.savetxt("data/stock.txt", stock, fmt="%.3f")
    for e in (0.3, 0.1):
        np.savetxt("data/trap_%.1f.txt" % e, trap * e, fmt="%.2f")
    vol = stock.sum() * DX * DX
    print("z.txt h0.txt rn.txt stock.txt trap_0.3.txt trap_0.1.txt -> data/")
    print("uniform depth: %.3f m at %.0f m3/s, %.3f m at %.1f m3/s; wood stock %.0f m3"
          % (hb, Q_BASE, uniform_depth(Q_PEAK), Q_PEAK, vol))


if __name__ == "__main__":
    main()
