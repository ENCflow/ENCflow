#!/usr/bin/env python3
# test/cascade の入力生成と定数(Check_cascade.py・param_*.txt と定数を対で保守。標準ライブラリだけ)
#   test/chichibu の 50 m 格子のデータから、本川が段々に下る区間(河床 354 → 268 m)を切り出す。
#   上流端の河道のセルに流量を与えて、ゆっくり上げて保つ。東辺は自由流出。
#     河道は 1 セル幅(50 m)で、落差と平らな区間が交互に続き、格子に斜めの区間と屈曲がある。
#     両岸には、河床より 10〜15 m 高いセルがあり、射流が乗り上げる。
#   エッジ水深の頭打ち f_dry_head_cap と、側方面の扱い f_advection_lateral の組み合わせで 3 構成。
#   python3 make_cascade.py z > cs_z.txt ; ... rw > cs_rw.txt ; ... mask > cs_mask.txt
import sys, os

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "chichibu", "data_chichibu_50m")
FILES = {"z": ("Chichibu_50m_filled.txt", "%.3f"), "rw": ("Chichibu_50m_river_flowline.txt", "%d"),
         "mask": ("Chichibu_50m_basin.txt", "%d")}
IX0, IY0 = 603, 364                  # 切り出しの左上のセル(元の格子の列・行。1 始まり、行は北から)
NX, NY, DX = 43, 55, 50.0
RN_LAND, RN_RIVER = 0.05, 0.02       # 粗度(tutorials/chichibu の 50 m 格子の計算と同じ)
DT = 0.75
Q_LO, Q_HI = 2000.0, 8000.0          # 与える流量の下端と上端 (m3/s)
T_RISE, T_SPIN, T_RAMP, T_HOLD = 5.0, 20.0, 120.0, 30.0     # 立ち上げ・助走の終わり・上げ・保持(分)
T_END = T_SPIN + T_RAMP + T_HOLD     # 計算の長さ(分)= 170
# 構成名 → (f_dry_head_cap, f_advection_lateral)
CASES = {"c2": (2, 0), "c3": (3, 0), "c3j": (3, 1)}


def loc(ix, iy):
    """元の格子のセル (ix, iy) の、切り出しの中の番号"""
    return ix - IX0 + 1, iy - IY0 + 1


SOURCE = loc(606, 415)               # 流量を与えるセル(切り出しの西の端に近い河道のセル。河床 353.8 m)
# プローブ: 1 = 流量を与えるセル、2〜4 = 河床 312.8・293.8・290.5 m の平らな区間のセル
PROBES = [loc(606, 415), loc(616, 392), loc(624, 374), loc(628, 372)]
FLUX = loc(626, 378) + loc(626, 368)    # 下流の測線(河床 290.5 m の区間を横切る)


def cut(kind):
    name, fmt = FILES[kind]
    rows = [l.split() for l in open(os.path.join(SRC, name)) if l.strip()]
    out = []
    for j in range(IY0 - 1, IY0 - 1 + NY):
        out.append(" ".join(fmt % float(v) for v in rows[j][IX0 - 1:IX0 - 1 + NX]))
    return "\n".join(out)


def param(name):
    cap, lat = CASES[name]
    L = []
    L.append("!======================================================================")
    L.append("! cascade %s: 急な段々の河道(f_dry_head_cap = %d、f_advection_lateral = %d)" % (name, cap, lat))
    L.append("!   test/chichibu の 50 m 格子のデータの列 %d〜%d・行 %d〜%d を切り出した %d × %d セル。" % (IX0, IX0 + NX - 1, IY0, IY0 + NY - 1, NX, NY))
    L.append("!   上流端の河道のセルに、%.0f m3/s を %.0f 分まで、そのあと %.0f 分かけて %.0f m3/s まで上げ、%.0f 分保つ。" % (Q_LO, T_SPIN, T_RAMP, Q_HI, T_HOLD))
    L.append("!   検定は Check_cascade.py。入力 cs_*.txt は make_cascade.py が作る")
    L.append("!======================================================================")
    L.append("&list_sysparam\n  f_gridsystem = 0\n  dt = %g\n  t0 = 0\n  tt = %d\n  dt_disp = 3600\n  dt_file = %d\n  dt_recrd = 10\n"
             "  fn_geoinfo = '-'\n  fn_boundary = '-'\n  fn_record = '-'\n  fn_enc = '-'\n  dir_result = 'result_%s'\n  f_out_h = 1\n"
             "  f_out_vvmax = 1           ! 期間最大流速 V9999(検定が読む)\n/\n" % (DT, T_END * 60, T_END * 60, name))
    L.append("&list_enc\n  f_dry_head_cap = %d        ! 高い地盤へ向かうエッジ水深の頭打ち(この検定の対象)\n"
             "  f_advection_lateral = %d   ! 側方面で横から入る水の扱い\n/\n" % (cap, lat))
    L.append("&list_geoinfo\n  nx = %d\n  ny = %d\n  dx = %.1f\n  dy = %.1f\n  f_ztype = 1\n  fn_z = 'cs_z.txt'\n  f_masktype = 1\n  fn_mask = 'cs_mask.txt'\n"
             "  fn_rw = 'cs_rw.txt'      ! 河道マスク\n  f_rntype = 0\n  rn0 = %.2f               ! 斜面の粗度\n  rn0_rw = %.2f            ! 河道マスクのセルの粗度\n/\n" % (NX, NY, DX, DX, RN_LAND, RN_RIVER))
    L.append("&list_bound_edge\n  f_bc_e = 1                ! 東辺は自由流出(本川の出口)\n/\n")
    s = "&list_bound_source\n  src_cell(:,1,1) = %d, %d      ! 上流端の河道のセル(時刻は分)\n" % SOURCE
    for k, (t, q) in enumerate(((0.0, 0.0), (T_RISE, Q_LO), (T_SPIN, Q_LO), (T_SPIN + T_RAMP, Q_HI), (T_END, Q_HI))):
        s += "  src_val(:,%d,1) = %g, %.1f\n" % (k + 1, t, q)
    L.append(s + "/\n")
    s = "&list_record\n  pbxytype = 0\n"
    for n, (i, j) in enumerate(PROBES):
        s += "  pbxy(:,%d) = %d, %d\n" % (n + 1, i, j)
    s += "  flxytype = 0\n  flxy(:,1) = %d, %d, %d, %d   ! 下流の測線\n/" % FLUX
    L.append(s)
    return "\n".join(L)


if __name__ == "__main__":
    if sys.argv[1] in FILES:
        print(cut(sys.argv[1]))
    elif sys.argv[1] == "param":        # 保守用: 置いてある param_*.txt はこの出力
        print(param(sys.argv[2]))
    elif sys.argv[1] == "names":
        print(" ".join(CASES))
