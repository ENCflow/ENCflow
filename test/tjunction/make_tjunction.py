#!/usr/bin/env python3
# test/tjunction の入力生成と定数(Check_tjunction.py・param_*.txt と定数を対で保守。標準ライブラリだけ)
#   1 セル幅の T 字の合流を、2 つの形で作る。
#   ax : 格子の軸に沿う合流。本川は行 JM を東へ(勾配 S0)、支川は列 IT の行 1〜JM−1 を本川へ向かう(同じ勾配)。
#   rot: 格子に対して 45° 回した合流。本川は対角線 (k, k) を k の増える向きへ、支川は合流のセル (KJ, KJ) から
#        伸びる対角線 (KJ + m, KJ − m) を本川へ向かう(セルの間隔は √2 Δx。同じ勾配)。
#   河道の外は、河床より BANK 高い岸(水は登らない)。流量は本川・支川の上流端のセルの湧き出しで与える。
#   濡れた岸の構成(wet)は、合流のセルの周りの岸の 5 セル(支川の口の両脇 2 つと、本川の向かいの岸 3 つ)に
#   FILM_Q ずつの湧き出しを置いて、岸を薄い水膜で濡らす。
#   向き(ori): '' = 上の形、'mx' = 東西を反転、'my' = 南北を反転、'xy' = 両方(180° 回転)。
#   python3 make_tjunction.py z <ax|rot> [ori] > tj_z_....txt
#   python3 make_tjunction.py param <構成名> > param_<構成名>.txt(保守用。置いてある param_*.txt はこの出力)
import sys
import math

DX = 50.0
S0, RN, G = 0.002, 0.03, 9.81       # 河床勾配、マニングの粗度係数、重力加速度(理論の計算に使う)
BANK, Z0 = 30.0, 100.0              # 岸の高さ(河床から)、本川の上流端の河床高
QTOT = 1000.0                       # 合流の下流の流量 (m3/s)
CASES = {"m800": (800.0, 200.0), "m500": (500.0, 500.0), "m200": (200.0, 800.0)}   # 本川・支川の流量 (m3/s)
FILM_Q = 0.05                       # 濡れた岸の湧き出し(1 セルあたり m3/s)
T_END, T_SYM = 7200, 1800           # 計算時間 (s)。向きを変えた構成は T_SYM まで

# ax: 格子の軸に沿う合流
NX, NY = 80, 25
JM, IT = 13, 40                     # 本川の行、支川の列(合流のセルは (IT, JM))
# rot: 45° 回した合流
NR = 100
KJ, MT = 35, 25                     # 合流のセルの番号、支川のセルの数
LS = math.sqrt(2.0) * DX            # 対角線に沿うセルの間隔
WD = DX / math.sqrt(2.0)            # 対角 1 セル河道の通過幅(斜めの自然幅 Δx Δy / √(Δx² + Δy²))

# 構成の組: (構成名の接頭辞, 形, f_advection_lateral)
GROUPS = (("", "ax", 0), ("l1_", "ax", 1), ("r_", "rot", 0), ("rl1_", "rot", 1))
# 向きを変えた構成(f_advection_lateral = 1 の、本川・支川が同じ流量の濡れた岸。T_SYM まで)
SYM_BASE = ("l1_m500_wet", "rl1_m500_wet")
ORIS = ("mx", "my", "xy")


def size(geom):
    return (NX, NY) if geom == "ax" else (NR, NR)


def spacing(geom):
    """本川のセルの間隔と、1 セル幅の河道の通過幅"""
    return (DX, DX) if geom == "ax" else (LS, WD)


def orient(i, j, geom, ori):
    """基本の形のセル (i, j) を、向き ori の格子のセルへ写す(逆も同じ写像)"""
    nx, ny = size(geom)
    if ori in ("mx", "xy"):
        i = nx + 1 - i
    if ori in ("my", "xy"):
        j = ny + 1 - j
    return i, j


def zmain(geom, k):
    return Z0 - S0 * spacing(geom)[0] * (k - 1)


def ground0(geom, i, j):
    """基本の形の地盤高"""
    if geom == "ax":
        zj = zmain(geom, IT)
        if j == JM:
            return zmain(geom, i)
        if i == IT and j < JM:
            return zj + S0 * DX * (JM - j)
        if j > JM:
            return zmain(geom, i) + BANK
        return zj + S0 * DX * (JM - j) + BANK
    if i == j:
        return zmain(geom, i)
    m = i - KJ
    if 1 <= m <= MT and j == KJ - m:
        return zmain(geom, KJ) + S0 * LS * m
    return Z0 - S0 * LS * ((i + j) / 2.0 - 1.0) + BANK


def ground(geom, ori, i, j):
    i0, j0 = orient(i, j, geom, ori)
    return ground0(geom, i0, j0)


def layout(geom):
    """基本の形の、(本川の上流端, 支川の上流端, 水膜のセル, プローブ, 測線の両端)"""
    if geom == "ax":
        film = [(IT - 1, JM - 1), (IT + 1, JM - 1), (IT - 1, JM + 1), (IT, JM + 1), (IT + 1, JM + 1)]
        pb = [(IT + d, JM) for d in range(-6, 7)] + [(IT, JM - d) for d in range(1, 5)]
        return (1, JM), (IT, 1), film, pb, ((70, JM + 2), (70, JM - 2))
    film = [(KJ + 1, KJ), (KJ, KJ - 1), (KJ - 1, KJ + 1), (KJ - 1, KJ), (KJ, KJ + 1)]
    pb = [(KJ + d, KJ + d) for d in range(-6, 7)] + [(KJ + m, KJ - m) for m in range(1, 5)]
    return (1, 1), (KJ + MT, KJ - MT), film, pb, ((KJ + 25, KJ + 30), (KJ + 35, KJ + 30))


def nfilm(geom):
    return len(layout(geom)[2])


def parse(name):
    """構成名 → (接頭辞, 形, f_advection_lateral, 流量の組, 岸, 向き)"""
    for pre, geom, lat in sorted(GROUPS, key=lambda g: -len(g[0])):
        if name.startswith(pre):
            rest = name[len(pre):].split("_")
            if rest[0] in CASES and len(rest) >= 2 and rest[1] in ("dry", "wet"):
                ori = rest[2] if len(rest) > 2 else ""
                return pre, geom, lat, rest[0], rest[1], ori
    raise SystemExit("unknown configuration: " + name)


def names():
    """Run.sh が回す構成名の並び"""
    out = []
    for pre, geom, lat in GROUPS:
        for tag in ("m800", "m500", "m200"):
            for bank in ("dry", "wet"):
                out.append("%s%s_%s" % (pre, tag, bank))
    for base in SYM_BASE:
        for ori in ORIS:
            out.append("%s_%s" % (base, ori))
    return out


def zfile(geom, ori):
    return "tj_z%s%s.txt" % ("r" if geom == "rot" else "", "_" + ori if ori else "")


def param(name):
    pre, geom, lat, tag, bank, ori = parse(name)
    wet = bank == "wet"
    q1, q2 = CASES[tag]
    nx, ny = size(geom)
    src1, src2, film, pb, fl = layout(geom)
    tt = T_SYM if ori else T_END
    east = ori in ("", "my")          # 本川の下流端が東辺か(東西を反転した向きは西辺)
    L = []
    L.append("!======================================================================")
    if geom == "ax":
        L.append("! tjunction %s: 1 セル幅の T 字の合流(本川 %.0f m3/s、支川 %.0f m3/s、%s)" % (name, q1, q2, "濡れた岸" if wet else "乾いた岸"))
        L.append("!   本川は行 %d を東へ、支川は列 %d の行 1〜%d を本川へ向かう。勾配 %.3f、n = %.2f、格子幅 %.0f m。" % (JM, IT, JM - 1, S0, RN, DX))
    else:
        L.append("! tjunction %s: 格子に対して 45° 回した 1 セル幅の T 字の合流(本川 %.0f m3/s、支川 %.0f m3/s、%s)" % (name, q1, q2, "濡れた岸" if wet else "乾いた岸"))
        L.append("!   本川は対角線 (k, k) を k の増える向きへ、支川は対角線 (%d + m, %d − m) の m = 1〜%d を本川へ向かう。" % (KJ, KJ, MT))
        L.append("!   勾配 %.3f、n = %.2f、格子幅 %.0f m(対角線に沿うセルの間隔は %.1f m)。" % (S0, RN, DX, LS))
    L.append("!   岸は河床より %.0f m 高い地盤。流量は上流端のセルの湧き出しで与え、10 分で上げて一定にする。" % BANK)
    if wet:
        L.append("!   合流のセルの周りの岸の 5 セルに %.2f m3/s ずつの湧き出しを置いて、岸を薄い水膜で濡らす。" % FILM_Q)
    L.append("!   側方面で横から入る水の扱いは f_advection_lateral = %d(%s)。"
             % (lat, "合流の損失を、岸の濡れによらずに数える" if lat == 1 else "平行リンクの流速を使う。合流の損失を、岸が濡れているときだけ数える"))
    if ori:
        L.append("!   向きを変えた構成(%s。%s)。同じ構成の基本の向きと、%d 分の水深を比べる。"
                 % (ori, {"mx": "東西を反転", "my": "南北を反転", "xy": "東西と南北を反転"}[ori], T_SYM // 60))
    L.append("!   検定は Check_tjunction.py(合流の 1 セル上流の本川の水深を、1 次元の理論と比べる)。")
    L.append("!   入力 %s は make_tjunction.py が作る" % zfile(geom, ori))
    L.append("!======================================================================")
    L.append("&list_sysparam\n  f_gridsystem = 0\n  dt = 1.0\n  t0 = 0\n  tt = %d\n  dt_disp = 1800\n  dt_file = %d\n  dt_recrd = 60\n"
             "  fn_geoinfo = '-'\n  fn_boundary = '-'\n  fn_record = '-'\n  fn_enc = '-'\n  dir_result = 'result_%s'\n  f_out_h = 1\n/\n" % (tt, tt, name))
    L.append("&list_geoinfo\n  nx = %d\n  ny = %d\n  dx = %.1f\n  dy = %.1f\n  f_ztype = 1\n  fn_z = '%s'\n  f_rntype = 0\n  rn0 = %.3f\n/\n"
             % (nx, ny, DX, DX, zfile(geom, ori), RN))
    L.append("&list_enc\n  f_advection_lateral = %d\n/\n" % lat)
    if east:
        L.append("&list_bound_edge\n  f_bc_e = 1                ! 東辺は自由流出\n/\n")
    else:
        L.append("&list_bound_edge\n  f_bc_w = 1                ! 西辺は自由流出\n/\n")
    s = "&list_bound_source\n"
    k = 0
    for c0, q, lab in ((src1, q1, "本川の上流端"), (src2, q2, "支川の上流端")):
        k += 1
        i, j = orient(c0[0], c0[1], geom, ori)
        s += "  src_cell(:,1,%d) = %d, %d      ! %s\n  src_val(:,1,%d) = 0, 0\n  src_val(:,2,%d) = 10, %.1f\n  src_val(:,3,%d) = 120, %.1f\n" % (k, i, j, lab, k, k, q, k, q)
    if wet:
        for c0 in film:
            k += 1
            i, j = orient(c0[0], c0[1], geom, ori)
            s += "  src_cell(:,1,%d) = %d, %d     ! 岸の水膜\n  src_val(:,1,%d) = 0, %.2f\n  src_val(:,2,%d) = 120, %.2f\n" % (k, i, j, k, FILM_Q, k, FILM_Q)
    L.append(s + "/\n")
    s = "&list_record\n  pbxytype = 0             ! プローブ 1〜13: 本川の合流のセルの −6〜+6、14〜17: 支川の合流の手前 1〜4 セル\n"
    for n, c0 in enumerate(pb):
        i, j = orient(c0[0], c0[1], geom, ori)
        s += "  pbxy(:,%d) = %d, %d\n" % (n + 1, i, j)
    (i1, j1), (i2, j2) = [orient(c[0], c[1], geom, ori) for c in fl]
    s += "  flxytype = 0\n  flxy(:,1) = %d, %d, %d, %d   ! 合流の 30 セル下流の本川の測線\n/" % (i1, j1, i2, j2)
    L.append(s)
    return "\n".join(L)


if __name__ == "__main__":
    if sys.argv[1] == "z":
        geom = sys.argv[2]
        ori = sys.argv[3] if len(sys.argv) > 3 else ""
        nx, ny = size(geom)
        for j in range(1, ny + 1):
            print(" ".join("%.3f" % ground(geom, ori, i, j) for i in range(1, nx + 1)))
    elif sys.argv[1] == "param":
        print(param(sys.argv[2]))
    elif sys.argv[1] == "names":
        print(" ".join(names()))
