#!/usr/bin/env python3
# test/curvature の入力生成(Check_curvature.py / param_*.txt と定数を対で保守)
#   zinit.txt: 直線斜面 A(tanθ1, x<=XA)→ 半径 R の凹円弧(両斜面に接する)
#              → 直線斜面 B(tanθ2)の 1 次元地形(nx=NX, ny=NY, dx=1)。
#              東端(x=LX)で z=0。円弧中心 C = (XA + R sinθ1, zA(XA) + R cosθ1)、
#              B との接点 XB = XA + R(sinθ1 − sinθ2)
import sys, math

NX, NY, DX = 220, 8, 1.0
ST1, ST2, XA, R = 1.0, 0.3, 60.0, 80.0
LX = NX * DX
TH1, TH2 = math.atan(ST1), math.atan(ST2)
XB = XA + R * (math.sin(TH1) - math.sin(TH2))
# 東端 z=0 から逆算した各区間の基準高
ZB = ST2 * (LX - XB)                         # 接点 B の標高
CZ = ZB + R * math.cos(TH2)                  # 円弧中心の標高
CX = XB + R * math.sin(TH2)                  # 円弧中心の x(= XA + R sinθ1)
ZA = CZ - R * math.cos(TH1)                  # 接点 A の標高


def z_of(x):
    if x <= XA:
        return ZA + ST1 * (XA - x)
    if x < XB:
        return CZ - math.sqrt(R * R - (x - CX) ** 2)
    return ZB - ST2 * (x - XB)


if __name__ == "__main__":
    for j in range(1, NY + 1):
        print(" ".join("%.8f" % z_of((i - 0.5) * DX) for i in range(1, NX + 1)))
