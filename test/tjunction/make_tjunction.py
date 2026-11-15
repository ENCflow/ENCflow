#!/usr/bin/env python3
# test/tjunction の入力生成と定数(Check_tjunction.py・param_*.txt と定数を対で保守。標準ライブラリだけ)
#   1 セル幅の T 字の合流。本川は行 JM を東へ(勾配 S0)、支川は列 IT の行 1〜JM−1 を本川へ向かう(同じ勾配)。
#   河道の外は、河床より BANK 高い平らな岸(水は登らない)。流量は本川・支川の上流端のセルの湧き出しで与える。
#   濡れた岸の構成(wet)は、合流のセルの周りの岸の 5 セル(支川の口の両脇 2 つと、本川の向かいの岸 3 つ)に
#   FILM_Q ずつの湧き出しを置いて、岸を薄い水膜で濡らす。
#   python3 make_tjunction.py z > tj_z.txt
import sys

NX, NY, DX = 80, 25, 50.0
JM, IT = 13, 40                     # 本川の行、支川の列(合流のセルは (IT, JM))
S0, RN, G = 0.002, 0.03, 9.81       # 河床勾配、マニングの粗度係数、重力加速度(理論の計算に使う)
BANK, Z0 = 30.0, 100.0              # 岸の高さ(河床から)、本川の上流端の河床高
QTOT = 1000.0                       # 合流の下流の流量 (m3/s) = 単位幅 20 m2/s
CASES = {"m800": (800.0, 200.0), "m500": (500.0, 500.0), "m200": (200.0, 800.0)}   # 本川・支川の流量 (m3/s)
FILM_Q = 0.05                       # 濡れた岸の湧き出し(1 セルあたり m3/s)
FILM = [(IT - 1, JM - 1), (IT + 1, JM - 1), (IT - 1, JM + 1), (IT, JM + 1), (IT + 1, JM + 1)]


def zmain(i):
    return Z0 - S0 * DX * (i - 1)


def ground(i, j):
    zj = zmain(IT)
    if j == JM:
        return zmain(i)
    if i == IT and j < JM:
        return zj + S0 * DX * (JM - j)
    if j > JM:
        return zmain(i) + BANK
    return zj + S0 * DX * (JM - j) + BANK


if __name__ == "__main__":
    if sys.argv[1] == "z":
        for j in range(1, NY + 1):
            print(" ".join("%.3f" % ground(i, j) for i in range(1, NX + 1)))
    elif sys.argv[1] == "param":        # 構成の param を書き出す(保守用。置いてある param_*.txt はこの出力)
        tag, wet = sys.argv[2], sys.argv[3] == "wet"
        q1, q2 = CASES[tag]
        name = "%s_%s" % (tag, "wet" if wet else "dry")
        L = []
        L.append("!======================================================================")
        L.append("! tjunction %s: 1 セル幅の T 字の合流(本川 %.0f m3/s、支川 %.0f m3/s、%s)" % (name, q1, q2, "濡れた岸" if wet else "乾いた岸"))
        L.append("!   本川は行 %d を東へ、支川は列 %d の行 1〜%d を本川へ向かう。勾配 %.3f、n = %.2f、格子幅 %.0f m。" % (JM, IT, JM - 1, S0, RN, DX))
        L.append("!   岸は河床より %.0f m 高い平らな地盤。流量は上流端のセルの湧き出しで与え、10 分で上げて一定にする。" % BANK)
        if wet:
            L.append("!   合流のセルの周りの岸の 5 セルに %.2f m3/s ずつの湧き出しを置いて、岸を薄い水膜で濡らす。" % FILM_Q)
        L.append("!   検定は Check_tjunction.py(合流の 1 セル上流の本川の水深を、1 次元の理論と比べる)。")
        L.append("!   入力 tj_z.txt は make_tjunction.py が作る")
        L.append("!======================================================================")
        L.append("&list_sysparam\n  f_gridsystem = 0\n  dt = 1.0\n  t0 = 0\n  tt = 7200\n  dt_disp = 1800\n  dt_file = 7200\n  dt_recrd = 60\n"
                 "  fn_geoinfo = '-'\n  fn_boundary = '-'\n  fn_record = '-'\n  dir_result = 'result_%s'\n  f_out_h = 1\n/\n" % name)
        L.append("&list_geoinfo\n  nx = %d\n  ny = %d\n  dx = %.1f\n  dy = %.1f\n  f_ztype = 1\n  fn_z = 'tj_z.txt'\n  f_rntype = 0\n  rn0 = %.3f\n/\n" % (NX, NY, DX, DX, RN))
        L.append("&list_bound_edge\n  f_bc_e = 1                ! 東辺は自由流出\n/\n")
        s = "&list_bound_source\n"
        k = 0
        for (i, j), q, lab in (((1, JM), q1, "本川の上流端"), ((IT, 1), q2, "支川の上流端")):
            k += 1
            s += "  src_cell(:,1,%d) = %d, %d      ! %s\n  src_val(:,1,%d) = 0, 0\n  src_val(:,2,%d) = 10, %.1f\n  src_val(:,3,%d) = 120, %.1f\n" % (k, i, j, lab, k, k, q, k, q)
        if wet:
            for (i, j) in FILM:
                k += 1
                s += "  src_cell(:,1,%d) = %d, %d     ! 岸の水膜\n  src_val(:,1,%d) = 0, %.2f\n  src_val(:,2,%d) = 120, %.2f\n" % (k, i, j, k, FILM_Q, k, FILM_Q)
        L.append(s + "/\n")
        pb = [(IT + d, JM) for d in range(-6, 7)] + [(IT, JM - d) for d in range(1, 5)]
        s = "&list_record\n  pbxytype = 0             ! プローブ 1〜13: 本川の合流のセルの −6〜+6、14〜17: 支川の合流の手前 1〜4 セル\n"
        for n, (i, j) in enumerate(pb):
            s += "  pbxy(:,%d) = %d, %d\n" % (n + 1, i, j)
        s += "  flxytype = 0\n  flxy(:,1) = 70, %d, 70, %d   ! 合流の 30 セル下流の本川の測線\n/" % (JM + 2, JM - 2)
        L.append(s)
        print("\n".join(L))
