#!/usr/bin/env python3
# test/bldgdrag の入力生成と理論値(Check_bldgdrag.py / param_*.txt と定数を対で保守)
#   乾いた高い地盤(+BANK)に挟まれた幅 W セルの直線水路(勾配 S、西が高い)の全体に家屋を置く
#   (空隙率 gv・家屋の平均寸法 B を一様に)。西端の区間流入 Q = q·W·DX、東辺は自由流出。
#   長さ 2000 m のうち、流入の近くと下流端の低下背水を避けた x = X1〜X2 で等流を測る。
#   等流の水深 h は、ENC の運動方程式(developer.md §107)の定常の釣り合い
#       gv g S = [ gv g n² / h^{4/3} + (kk·cd/2)(1 − gv)/B ] V²,   q = V h
#   の解(uniform_depth)。
#   python3 make_init.py z > zinit.txt / h > hinit.txt / gv 構成 > gv_構成.txt / bb 構成 > bb_構成.txt
import sys, math

NX, NY, DX = 400, 12, 5.0
S, N, Z0, BANK, H_INIT, G = 0.01, 0.03, 30.0, 12.0, 1.0, 9.8
W = 4
X1, X2 = 300, 900                                   # 計測区間 (m)
# 構成: 空隙率 gv、家屋の平均寸法 bb (m)、抗力係数 cd、補正係数 kk、単位幅流量 q (m2/s)
CONFIGS = {
    "shallow": dict(gv=0.7, bb=10.0, cd=1.0, kk=0.5, q=0.4),    # 浅い流れ(マニングの摩擦が主)
    "deep":    dict(gv=0.7, bb=10.0, cd=1.0, kk=0.5, q=8.0),    # 深い流れ(家屋の抗力が主)
    "dense":   dict(gv=0.5, bb=20.0, cd=2.0, kk=0.5, q=8.0),    # 空隙率・寸法・抗力係数を変える
}


def rows():
    j1 = (NY - W) // 2 + 1
    return j1, j1 + W - 1


def drag_coef(c):
    """家屋の抗力の係数 (kk·cd/2)(1 − gv)/B (1/m)。"""
    return 0.5 * c["kk"] * c["cd"] * (1.0 - c["gv"]) / c["bb"]


def uniform_depth(c):
    """等流の水深 (m)。二分法。"""
    q = c["q"]

    def f(h):
        return (c["gv"] * G * N * N * h ** (-4.0 / 3.0) + drag_coef(c)) * q * q / (h * h) - c["gv"] * G * S
    lo, hi = 1.0e-3, 100.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if f(mid) > 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def manning_depth(q):
    """家屋のない水路の等流の水深(マニング)。"""
    return (q * N / math.sqrt(S)) ** 0.6


if __name__ == "__main__":
    kind = sys.argv[1]
    cfg = CONFIGS[sys.argv[2]] if len(sys.argv) > 2 else None
    j1, j2 = rows()
    for j in range(1, NY + 1):
        ch = j1 <= j <= j2
        if kind == "z":
            print(" ".join("%.6f" % (Z0 - S * (i - 0.5) * DX + (0.0 if ch else BANK)) for i in range(1, NX + 1)))
        elif kind == "h":
            print(" ".join("%.6f" % (H_INIT if ch else 0.0) for i in range(1, NX + 1)))
        elif kind == "gv":
            print(" ".join("%.2f" % (cfg["gv"] if ch else 1.0) for i in range(1, NX + 1)))
        elif kind == "bb":
            print(" ".join("%.1f" % cfg["bb"] for i in range(1, NX + 1)))
