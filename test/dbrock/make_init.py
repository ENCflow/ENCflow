#!/usr/bin/env python3
# test/dbrock の入力生成(Check_dbrock.py / param*.txt と定数を対で保守)
#   python3 make_init.py   すべての入力ファイルを書く
#
# 構成 db1・db3(DB1 自己被覆の解析解・DB3 の門): 乾いた高い地盤(+BANK)に挟まれた幅 1 セルの
#   直線水路(南北向き。北 j = 1 が高く勾配 S で南へ下る。流れが MPI の帯界面を横切る)。
#   北端の区間流入で清水 QW と濃度 CS = h_s/h の土砂を与え、南辺は自由流出。交換なし
#   (f_dbed = 0)・Manning 抵抗の混合体を前段(db1_spin)で定常にしてから、リスタートで
#   土石流の項を効かせる。初期の被覆 sd0 と侵食性倍率 f_r は行ごとに変える。
# 構成 db2(DB2 保存): 四周壁の箱。y < YB2 が勾配 S2、下流は平坦。北の帯(行 J1R〜J2R)の
#   土層を瞬時流動化し、薄い被覆の上を流下させる(E-D あり)。
# 構成 db8(DB8 2 セル周期の凹凸): db1 と同じ水路・流れで、裸岩・倍率 1、水路の行 J1〜J2 に
#   ±EPS8 の 2 セル周期の凹凸を与える(developer.md §89.23・§89.24)。
import math

# --- db1・db3 の水路 ---
NX, NY, DX = 3, 60, 1.0
IC = 2                                  # 水路の列(両側の 1 列は乾いた高い地盤)
S, Z0, BANK = 0.2, 10.0, 2.0            # 勾配・下流端の標高・河岸の高さ (m)
QW, CS = 0.5, 0.5                       # 区間流入の清水の流量 (m3/s)・濃度 h_s/h(C = 1/3)
J1, J2 = 11, 50                         # 検定する内部の行(流入と出口の影響を避ける)


def z1(i, j):
    zc = Z0 + S * (NY - j + 0.5) * DX
    return zc if i == IC else zc + BANK


def sd1(i, j):
    """初期の被覆(水路は 0・0.02・0.04・0.06 m の繰り返し。河岸は 0)"""
    return 0.02 * (j % 4) if i == IC else 0.0


def fr1(i, j):
    """侵食性倍率 0〜2(並びが 9 行周期でずれるので、帯の配布の行ずれを検出できる)"""
    return 0.25 * ((i + 4 * j) % 9)


# --- db8 の凹凸 ---
EPS8 = 0.005                            # 2 セル周期の凹凸の振幅 (m)。凸部は (−1)^j > 0 の行


def z8(i, j):
    return z1(i, j) + (EPS8 * (-1) ** j if (i == IC and J1 <= j <= J2) else 0.0)


# --- db2 の箱 ---
NX2, NY2, DX2 = 10, 40, 1.0
S2, YB2 = 0.4, 25.0                     # 斜面の勾配・遷緩点 (m)
SD2, SDR, DREL = 0.02, 0.6, 0.5         # 被覆の厚さ・崩壊域の土層厚・崩壊深 (m)
J1R, J2R = 3, 8                         # 崩壊域の行


def z2(i, j):
    y = (j - 0.5) * DX2
    return S2 * (YB2 - y) if y < YB2 else 0.0


def sd2(i, j):
    return SDR if J1R <= j <= J2R else SD2


def rel2(i, j):
    return DREL if J1R <= j <= J2R else 0.0


def write(fn, f, nx, ny, fmt="%.6f"):
    with open(fn, "w") as o:
        for j in range(1, ny + 1):
            o.write(" ".join(fmt % f(i, j) for i in range(1, nx + 1)) + "\n")


if __name__ == "__main__":
    write("z_db1.txt", z1, NX, NY)
    write("z_db8.txt", z8, NX, NY)
    write("sd_db8.txt", lambda i, j: 0.0, NX, NY, "%.2f")
    write("sd_db1.txt", sd1, NX, NY, "%.2f")
    write("fr_db1.txt", fr1, NX, NY, "%.2f")
    write("z_db2.txt", z2, NX2, NY2)
    write("sd_db2.txt", sd2, NX2, NY2, "%.2f")
    write("rel_db2.txt", rel2, NX2, NY2, "%.1f")
