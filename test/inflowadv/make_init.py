#!/usr/bin/env python3
# test/inflowadv の入力生成(Check_inflowadv.py / param_*.txt と定数を対で保守)
#   区間流入の外縁セルに接するエッジの移流項の規則(developer.md §68.40)の検定。
#   osc5・osc3: 壁(領域外縁)に挟まれた河道だけの領域(Δx = 10 m、80 行)。河床 −3.0 → −3.8 m
#     (勾配 1/1000、n = 0.03)、北辺の区間流入(inflow_dist = 2。幅 5 列は 700 m3/s、幅 3 列は同じ
#     単位幅流量の 420 m3/s)、南辺の水位 0.9 m(700 m3/s の等流水深 4.72 m)、初期水深 4.7 m。
#     流入区間の両端の角セルが閉じて(§69.9)流入が中央に集まり、流入行の移流項と結合して
#     限界周期振動を自励する構成(§68.40 の現象)
#   jet3: osc3 と同じ領域に 700 m3/s(流入は中央 1 列に集まる)。内側エッジの流速の上限の基準を
#     流入セルの今のフルード数で切り替えると、流入直下に射流のジェットが残る構成(§68.40 の改定 2)
#   side: 固定床の横溢(Δx = 2 m、16 列 × 20 行)。西端の区間流入(列 1、行 4〜8、5 m3/s)の主水路は
#     東辺へ自由流出。流入区間の南端の隣から、境界の列 i = 1 に沿って主水路より 0.5 m 低い側溝
#     (南へ勾配 0.05)が南辺の自由流出まで続く。両岸(氾濫原)は主水路の河床 + 1 m
#   steep: 射流の区間流入(Δx = 2 m、60 列 × 8 行、p_diagratio = 0 の 4 近傍)。壁に挟まれた
#     勾配 1/20 の河道(n = 0.03)の西端の全 8 行に区間流入 16 m3/s(単位幅 1 m2/s、等流の
#     フルード数 1.95)、東辺は自由流出、初期水深は Manning の等流水深。区間は MPI の帯境界
#     (np = 2・4)をまたぐ
#   python3 make_init.py <z|h> <osc5|osc3|jet3|side|steep> > file
import sys

# 河道だけの領域
NY_O, DX_O = 80, 10.0
ZB0_O, S_O, H0_O, STAGE_O = -3.0, 1.0e-3, 4.7, 0.9
Q_PER_COL = 140.0                 # 列あたりの流入量(幅 5 列で 700 m3/s)
J_FLUX = 30                       # 流量を測る行
# 横溢
NX_S, NY_S, DX_S = 16, 20, 2.0
J1, J2 = 4, 8                     # 主水路の行(流入区間)
Z0_S, S0_S, BANK, DROP, SS = 10.0, 1.0e-3, 1.0, 0.5, 0.05
Q_S, H0_S = 5.0, 0.5
# 射流の区間流入
NX_T, NY_T, DX_T = 60, 8, 2.0
Z0_T, S_T, Q_T, N_T = 20.0, 0.05, 16.0, 0.03


def width(case):
    return {"osc5": 5, "osc3": 3, "jet3": 3}[case]


def z_osc(i, j):
    return ZB0_O - S_O * (j - 0.5) * DX_O


def z_side(i, j):
    zb = Z0_S - S0_S * (i - 0.5) * DX_S
    if J1 <= j <= J2:
        return zb
    if i == 1 and j > J2:          # 側溝(流入区間の南端の隣から南辺まで)
        return Z0_S - S0_S * 0.5 * DX_S - DROP - SS * (j - J2 - 1) * DX_S
    return zb + BANK


def h_side(i, j):
    return H0_S if J1 <= j <= J2 else 0.0


def hn_steep():
    # Manning の等流水深 h_n = (q n / √S)^{3/5}(q = 単位幅流量)
    return (Q_T / (NY_T * DX_T) * N_T / S_T ** 0.5) ** 0.6


def z_steep(i, j):
    return Z0_T - S_T * (i - 0.5) * DX_T


if __name__ == "__main__":
    kind, case = sys.argv[1], sys.argv[2]
    if case == "side":
        nx, ny = NX_S, NY_S
        fn = z_side if kind == "z" else h_side
    elif case == "steep":
        nx, ny = NX_T, NY_T
        fn = z_steep if kind == "z" else (lambda i, j: hn_steep())
    else:
        nx, ny = width(case), NY_O
        fn = z_osc if kind == "z" else (lambda i, j: H0_O)
    for j in range(1, ny + 1):
        print(" ".join("%.4f" % fn(i, j) for i in range(1, nx + 1)))
