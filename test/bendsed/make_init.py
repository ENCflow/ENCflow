#!/usr/bin/env python3
# test/bendsed の入力生成(Check_bendsed.py / param_*.txt と定数を対で保守)
#   90° 湾曲水路: 西端から東へ直線 L1 → 半径 R(中心線)の円弧で 90° 曲がる →
#   直線 L2 で北辺(left)または南辺(right)へ抜ける。幅 W、両岸は河床 +BANK の
#   乾いた河岸(氾濫原)。河床勾配 S0 は路長 s に沿う。left と right は行の
#   上下反転で厳密に鏡像(z・h とも配列が一致する)。
#   python3 make_init.py dims            → "nx ny"
#   python3 make_init.py z left|right    → zinit
#   python3 make_init.py h left|right    → hinit(水路内 H0、河岸 0)
#   python3 make_init.py rows left|right → 西端の水路の行番号(区間流入セル)
import sys, math

W, R, L1, L2, DX = 10.0, 25.0, 60.0, 20.0, 1.0
BANK, S0, Z0, H0 = 2.0, 0.002, 10.0, 0.6
Y0 = W / 2 + 1.0                       # 直線部の中心線の y(河岸 1 セル分の余白)
NX = int(L1 + R + W / 2 + 1)           # 円弧の外縁 + 河岸 1 セル
NY = int(Y0 + R + L2)
S_ARC0, S_ARC1 = L1, L1 + R * math.pi / 2   # 円弧の路長範囲
turn = "left"


def centerline_dist(x, y):
    """物理座標 (x 東, y 北) → (路長 s, 中心線からの符号付き距離 n。左が正)。流路外は (None, None)"""
    y = y - Y0
    if x <= L1:
        return x, y
    cx, cy = L1, R
    r = math.hypot(x - cx, y - cy)
    ang = math.atan2(y - cy, x - cx)      # −90°(入口)→ 0°(出口)
    if -math.pi / 2 <= ang <= 0.0:
        return L1 + R * (ang + math.pi / 2), R - r
    if y >= cy and x >= cx:                # 出口直線(北へ)
        return S_ARC1 + (y - cy), (cx + R) - x
    return None, None


def cell(i, j):
    """格子 (i, j) → (s, n)。河岸は None。left: 北 = 小さい j(行順 北→南)"""
    x = (i - 0.5) * DX
    y = (NY - j + 0.5) * DX if turn == "left" else (j - 0.5) * DX
    s, n = centerline_dist(x, y)
    if s is None or abs(n) > W / 2:
        return None
    return s, n


def z_of(i, j):
    c = cell(i, j)
    if c is None:
        # 河岸: 最寄りの路長(円弧の外側は x+y で代用)に合わせた河床 + BANK
        x = (i - 0.5) * DX
        y = (NY - j + 0.5) * DX if turn == "left" else (j - 0.5) * DX
        s, n = centerline_dist(x, y)
        if s is None:
            s = x
        return Z0 - S0 * s + BANK
    return Z0 - S0 * c[0]


def h_of(i, j):
    return 0.0 if cell(i, j) is None else H0


if __name__ == "__main__":
    kind = sys.argv[1]
    if len(sys.argv) > 2:
        turn = sys.argv[2]
    if kind == "dims":
        print(NX, NY)
    elif kind == "rows":
        print(" ".join(str(j) for j in range(1, NY + 1) if cell(1, j) is not None))
    else:
        fn = z_of if kind == "z" else h_of
        for j in range(1, NY + 1):
            print(" ".join("%.6f" % fn(i, j) for i in range(1, NX + 1)))
