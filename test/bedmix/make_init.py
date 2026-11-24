#!/usr/bin/env python3
# test/bedmix の入力生成(Check_bedmix.py / param*.txt と定数を対で保守)
#   幅 W = 5 セルの直線水路(行 J1〜J2。西が高い勾配 S)を、乾いた高い地盤(+BANK)の河岸が挟む。
#   西端の区間流入は Manning の等流水深 H0 の単位幅流量 × W、東辺は自由流出。
#   水路の型:
#     std  : S = 0.002、H0 = 0.5 m、河床の土層厚 1 m、河岸は土層厚 0(侵食しない)、下流端の 4 列は土層厚 0
#     deep : S = 0.001、H0 = 1.0 m(深い流れ = 河床が変わっても水理がほぼ変わらない)、河床の土層厚 0.5 m、
#            河岸は土層厚 0、下流端の 4 列は土層厚 0
#     free : std と同じで、下流端まで動く床(開境界の流出の検定)
#     bank : std と同じで、河岸の高さを 1 m にして河岸も動く床(土層厚 1 m。側岸侵食・安息角崩落)
#   python3 make_init.py z <型> > zinit_<型>.txt   (h、sd も同様)
#   python3 make_init.py qbmix > qbmix.txt          (粒径階ごとの給砂の時系列。時刻 (min) と 3 粒径階)
#   python3 make_init.py rw > rw_suw.txt            (構成 suw の河道マスク: 水路の中央の行 J_SUB だけ 1)
#   python3 make_init.py width > width_suw.txt      (構成 suw の河道幅: 中央の行だけ W_SUB(セル幅より狭い))
import sys, math

NX, NY, DX = 60, 9, 1.0
J1, J2 = 3, 7
W = J2 - J1 + 1
N, Z0, N_FIX = 0.03, 10.0, 4
GEOM = {
    #        S      H0    BANK  SD_BED  SD_BANK  fixed downstream columns
    "std":  (0.002, 0.5, 2.0, 1.0, 0.0, N_FIX),
    "deep": (0.001, 1.0, 2.0, 0.5, 0.0, N_FIX),
    "free": (0.002, 0.5, 2.0, 1.0, 0.0, 0),
    "bank": (0.002, 0.5, 1.0, 1.0, 1.0, N_FIX),
}
J_SUB, W_SUB = 5, 0.6                    # サブグリッド河道幅の行と幅 (m)(構成 suw。河道平面積率 0.6)
# 粒径階ごとの給砂の時系列(時刻 min, Qb_1, Qb_2, Qb_3 (m3/s 固体))。区間で線形補間
QBMIX = [(0.0, 2.0e-4, 5.0e-4, 3.0e-4),
         (2.0, 4.0e-4, 1.0e-4, 0.0),
         (5.0, 4.0e-4, 1.0e-4, 0.0)]


def q_unit(geom):
    s, h0 = GEOM[geom][0], GEOM[geom][1]
    return h0 ** (5.0 / 3.0) * math.sqrt(s) / N


def in_channel(j):
    return J1 <= j <= J2


def z_of(geom, i, j):
    s, h0, bank = GEOM[geom][0:3]
    return Z0 - s * (i - 0.5) * DX + (0.0 if in_channel(j) else bank)


def h_of(geom, i, j):
    return GEOM[geom][1] if in_channel(j) else 0.0


def sd_of(geom, i, j):
    s, h0, bank, sdb, sdk, nfix = GEOM[geom]
    if i > NX - nfix:
        return 0.0
    return sdb if in_channel(j) else sdk


if __name__ == "__main__":
    kind = sys.argv[1]
    if kind == "qbmix":
        for row in QBMIX:
            print("%.3f %.6e %.6e %.6e" % row)
        sys.exit(0)
    if kind in ("rw", "width"):
        val = "1" if kind == "rw" else "%.3f" % W_SUB
        for j in range(1, NY + 1):
            print(" ".join(val if j == J_SUB else "0" for i in range(1, NX + 1)))
        sys.exit(0)
    if kind == "q":
        print("%.6f" % (q_unit(sys.argv[2]) * W))
        sys.exit(0)
    geom = sys.argv[2]
    fn = {"z": z_of, "h": h_of, "sd": sd_of}[kind]
    for j in range(1, NY + 1):
        print(" ".join("%.6f" % fn(geom, i, j) for i in range(1, NX + 1)))
