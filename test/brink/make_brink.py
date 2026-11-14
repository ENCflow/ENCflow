#!/usr/bin/env python3
# test/brink の入力生成と定数、理論の水面形(Check_brink.py・param_*.txt と定数を対で保守。標準ライブラリだけ)
#   1 セル幅の水路の「池の出口の段落ち」: 水平な池(河床 Z_POOL、N_POOL セル)→ 段差 DROP → 水平な棚
#   (N_APRON セル)→ 勾配 S_OUT の流出区間 → 東辺の自由流出。岸は河床 + BANK の乾いた地盤。池の上流端の
#   2 セルに湧き出しで流量を与える(運動量を持たない流入)。
#   構成 straight: 水路は 1 行の直線。
#   構成 diag    : 段落ちの直前のセルの手前で、水路が斜めに 1 行ずれる(池は 1 行南。最後の 1 本が北東向き)。
#   構成 stair   : 一様な勾配 S_ST の水路で、東と北東のリンクが交互に並ぶ(等流の確認用)。
#   「落差の先の池」: 上の池(N_UP セル)→ 段差 DROP → 水平な下の池(N_MID セル)→ 段差 DROP → 棚 → 流出区間。
#   下の池には、段差を落ちた射流と、2 つ目の段差から上流へ延びる常流があり、その間に跳水が立つ。
#   構成 pstraight: 水路は 1 行の直線。
#   構成 pfoot    : 1 つ目の段差の足元のセルの直後で、水路が斜めに 1 行ずれる(足元のセルまでが 1 行南)。
#   構成 pbrink   : 1 つ目の段差の直前のセルの手前で、水路が斜めに 1 行ずれる(diag と同じ位置)。
#   python3 make_brink.py z straight|diag|stair|pstraight|pfoot|pbrink > br_z_<構成>.txt
import sys, math

G = 9.81
DX = 50.0
N_MAN = 0.02                    # 粗度係数(水路・岸とも)
BANK = 200.0                    # 岸の高さ(河床から。m)
# ---- 段落ち(straight・diag)----
N_POOL, N_APRON, N_OUT = 20, 5, 12
Z_POOL, DROP, S_OUT = 20.0, 3.0, 0.02
NX, NY = 2 + N_POOL + N_APRON + N_OUT, 12
J_CH = 6                        # 水路の行(straight。diag の池は J_CH + 1)
I_BRINK = 2 + N_POOL            # 段落ちの直前のセルの列(1 始まり。西に余白 2 列)
Q_LEVELS = [2000.0, 4000.0, 6000.0]     # 流量の段 (m3/s)。各段: T_RAMP 分で上げて T_HOLD 分保つ
T_RAMP, T_HOLD = 10.0, 30.0             # (min)
# ---- 落差の先の池(pstraight・pfoot・pbrink)。棚・流出区間・段差・流量の段は段落ちの構成と同じ ----
N_UP, N_MID = 12, 20            # 上の池と下の池のセル数
NX_PL = 2 + N_UP + N_MID + N_APRON + N_OUT
I_DROP1 = 2 + N_UP              # 1 つ目の段差の直前のセルの列(上の池の最後のセル)
I_DROP2 = I_DROP1 + N_MID       # 2 つ目の段差の直前のセルの列(下の池の最後のセル)
# ---- 等流の階段状の水路(stair)----
NX_ST, N_ST = 80, 80            # 列数 = 水路のセル数(列ごとに 1 セル)
S_ST, N_ST_MAN, Q_ST = 0.005, 0.03, 200.0


def bed_brink(i):
    """段落ちの構成の、列 i(1 始まり)の水路の河床"""
    if i <= I_BRINK:
        return Z_POOL
    if i <= I_BRINK + N_APRON:
        return Z_POOL - DROP
    return Z_POOL - DROP - S_OUT * DX * (i - I_BRINK - N_APRON)


def row_brink(i, kind):
    """段落ちの構成の、列 i の水路の行。池の水路は列 3 から(西の 2 列は岸)"""
    if i < 3:
        return 0
    if kind == "diag" and i < I_BRINK:
        return J_CH + 1
    return J_CH


def bed_pool(i):
    """落差の先の池の構成の、列 i(1 始まり)の水路の河床"""
    if i <= I_DROP1:
        return Z_POOL
    if i <= I_DROP2:
        return Z_POOL - DROP
    if i <= I_DROP2 + N_APRON:
        return Z_POOL - 2 * DROP
    return Z_POOL - 2 * DROP - S_OUT * DX * (i - I_DROP2 - N_APRON)


def row_pool(i, kind):
    """落差の先の池の構成の、列 i の水路の行(西の 2 列は岸)"""
    if i < 3:
        return 0
    if kind == "pfoot" and i <= I_DROP1 + 1:
        return J_CH + 1
    if kind == "pbrink" and i < I_DROP1:
        return J_CH + 1
    return J_CH


def path_stair():
    """階段状の水路の (列, 行, 路長) の並び。東・北東を交互に(両端の 6 セルは東向き)"""
    cells = [(1, 0, 0.0)]
    for k in range(1, N_ST):
        i, j, s = cells[-1]
        ne = 6 <= k < N_ST - 6 and k % 2 == 0
        cells.append((i + 1, j - (1 if ne else 0), s + DX * (math.sqrt(2.0) if ne else 1.0)))
    jmin = min(c[1] for c in cells)
    return [(i, j - jmin + 3, s) for i, j, s in cells]


def ny_stair():
    return max(c[1] for c in path_stair()) + 2


def main(kind):
    if kind in ("straight", "diag"):
        for j in range(1, NY + 1):
            print(" ".join("%.3f" % (bed_brink(i) + (0.0 if j == row_brink(i, kind) else BANK))
                           for i in range(1, NX + 1)))
    elif kind in ("pstraight", "pfoot", "pbrink"):
        for j in range(1, NY + 1):
            print(" ".join("%.3f" % (bed_pool(i) + (0.0 if j == row_pool(i, kind) else BANK))
                           for i in range(1, NX_PL + 1)))
    else:
        cells = path_stair()
        zb = {(i, j): 100.0 - S_ST * s for i, j, s in cells}
        col = {i: 100.0 - S_ST * s for i, j, s in cells}
        for j in range(1, ny_stair() + 1):
            print(" ".join("%.4f" % (zb[(i, j)] if (i, j) in zb else col[i] + BANK) for i in range(1, NX_ST + 1)))


# ---- 1 次元の定常の水面形(単位幅流量 q、広い矩形断面、Manning)----
def hcrit(q):
    return (q * q / G) ** (1.0 / 3.0)


def _rk4(f, h, dx, nstep):
    out = [h]
    for _ in range(nstep):
        k1 = f(h)
        k2 = f(h + 0.5 * dx * k1)
        k3 = f(h + 0.5 * dx * k2)
        k4 = f(h + dx * k3)
        h += dx * (k1 + 2 * k2 + 2 * k3 + k4) / 6.0
        out.append(h)
    return out


def pool_depth(q, x_up, n=N_MAN, dx=0.25):
    """水平な池の H2 の水面形: 段落ち(限界水深)から上流へ x_up (m) の水深"""
    hc = hcrit(q)
    f = lambda h: n * n * q * q / h ** (10.0 / 3.0) / (1.0 - q * q / (G * h ** 3))
    return _rk4(f, hc * 1.001, dx, int(round(x_up / dx)))[-1]


def super_depth(q, e):
    """河床からの比エネルギー e の射流の水深"""
    lo, hi = 1.0e-6, hcrit(q)
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if mid + q * q / (2 * G * mid * mid) > e:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def apron_depth(q, x_dn, n=N_MAN, drop=DROP, dx=0.25):
    """水平な棚の H3 の水面形: 段落ちの直下(比エネルギー 1.5 h_c + drop)から下流へ x_dn (m) の水深"""
    f = lambda h: n * n * q * q / h ** (10.0 / 3.0) / (q * q / (G * h ** 3) - 1.0)
    return _rk4(f, super_depth(q, 1.5 * hcrit(q) + drop), dx, int(round(x_dn / dx)))[-1]


def momentum_fn(q, h):
    """運動量関数(単位幅の比力)M = q²/(g h) + h²/2"""
    return q * q / (G * h) + 0.5 * h * h


def jump_position(q, length=N_MID * DX, n=N_MAN, drop=DROP, dx=0.25):
    """水平な区間(長さ length。上流端が段落ちの足元、下流端が次の段落ち)の跳水の位置(足元から。m)。
    足元からの射流(H3。比エネルギー 1.5 h_c + drop から)と、下流端からの常流(H2。限界水深から)の
    運動量関数が等しくなる所。区間の中で等しくならなければ None(跳水は区間の外へ押し出される)。
    足元ですでに常流の側が大きければ 0(跳水は足元に潜る)"""
    hc = hcrit(q)
    ns = int(round(length / dx))
    fb = lambda h: n * n * q * q / h ** (10.0 / 3.0) / (1.0 - q * q / (G * h ** 3))
    hb = _rk4(fb, hc * 1.001, dx, ns)           # hb[k]: 下流端から k dx 上流の常流の水深
    fs = lambda h: n * n * q * q / h ** (10.0 / 3.0) / (q * q / (G * h ** 3) - 1.0)
    h = super_depth(q, 1.5 * hc + drop)
    for k in range(ns + 1):
        if momentum_fn(q, h) <= momentum_fn(q, hb[ns - k]):
            return k * dx
        if h >= 0.99 * hc:                      # 跳水の前に限界水深へ近づく(この検定の範囲では起きない)
            return None
        k1 = fs(h)
        k2 = fs(h + 0.5 * dx * k1)
        k3 = fs(h + 0.5 * dx * k2)
        k4 = fs(h + dx * k3)
        h += dx * (k1 + 2 * k2 + 2 * k3 + k4) / 6.0
    return None


KINDS = ("straight", "diag", "stair", "pstraight", "pfoot", "pbrink")

if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "z" or sys.argv[2] not in KINDS:
        sys.exit("usage: make_brink.py z " + "|".join(KINDS))
    main(sys.argv[2])
