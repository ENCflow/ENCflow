#!/usr/bin/env python3
# test/chutepool の入力生成と定数(Check_chutepool.py・param_*.txt と定数を対で保守。標準ライブラリだけ)
#   test/chichibu のデータ(100 m 格子)から、本川が落差を落ちて池へ入る所のまわりを切り出す。
#   上流端の河道のセルに流量を与えて、ゆっくり上げる。北辺は自由流出。
#     本川: 13 m の落差(元の格子のセル (292,208) → (293,208))を落ちた直後に北東へ折れ、深さ約 10 m の池
#           ((294,207)〜(309,204))へ落ち込む。池の出口は (309,203)〜(309,201) の落差
#     (293,208) の流れの正面のセル (294,208) は、(293,208) の水位より約 8 m 高い斜面
#   エッジ水深の頭打ち f_dry_head_cap は、2(c2)と 3(c3)の 2 通り。
#   python3 make_chutepool.py z > cp_z.txt ; ... rw > cp_rw.txt ; ... mask > cp_mask.txt
import sys, os

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "chichibu", "data_chichibu")
FILES = {"z": ("Chichibu_100m_filled2.txt", "%.3f"), "rw": ("Chichibu_100m_river_flowline.txt", "%d"),
         "mask": ("Chichibu_100m_basin.txt", "%d")}
IX0, IY0 = 285, 194                  # 切り出しの左上のセル(元の格子の列・行。1 始まり、行は北から)
NX, NY, DX = 32, 21, 100.0
RN_LAND, RN_RIVER = 0.15, 0.02       # 粗度(test/chichibu と同じ)
DT = 2.5
Q_LO, Q_HI = 2500.0, 5000.0          # 与える流量の下端と上端 (m3/s)
T_RISE, T_SPIN, T_RAMP, T_HOLD = 5.0, 40.0, 150.0, 20.0     # 立ち上げ・助走の終わり・上げ・保持(分)
T_END = T_SPIN + T_RAMP + T_HOLD     # 計算の長さ(分)= 210
CASES = {"c2": 2, "c3": 3}           # 構成名と f_dry_head_cap


def loc(ix, iy):
    """元の格子のセル (ix, iy) の、切り出しの中の番号"""
    return ix - IX0 + 1, iy - IY0 + 1


SOURCE = loc(285, 200)               # 流量を与えるセル(切り出しの西端の河道のセル)
# プローブ: 1 = 落差の下の河道のセル (293,208)、2 = その正面の斜面のセル (294,208)、
#           3 = 池の入口のセル (294,207)、4 = 池の中の測線のセル (296,206)
PROBES = [loc(293, 208), loc(294, 208), loc(294, 207), loc(296, 206)]
FLUX = loc(296, 207) + loc(296, 204)    # 池の中の測線(test/chichibu の測線 3 と同じ位置)


def cut(kind):
    name, fmt = FILES[kind]
    rows = [l.split() for l in open(os.path.join(SRC, name)) if l.strip()]
    out = []
    for j in range(IY0 - 1, IY0 - 1 + NY):
        out.append(" ".join(fmt % float(v) for v in rows[j][IX0 - 1:IX0 - 1 + NX]))
    return "\n".join(out)


def param(name):
    cap = CASES[name]
    L = []
    L.append("!======================================================================")
    L.append("! chutepool %s: 落差のあとの池へ落ち込む流れ(f_dry_head_cap = %d)" % (name, cap))
    L.append("!   test/chichibu のデータ(100 m 格子)の列 %d〜%d・行 %d〜%d を切り出した %d × %d セル。" % (IX0, IX0 + NX - 1, IY0, IY0 + NY - 1, NX, NY))
    L.append("!   上流端の河道のセルに、%.0f m3/s を %.0f 分まで、そのあと %.0f 分かけて %.0f m3/s まで上げ、%.0f 分保つ。" % (Q_LO, T_SPIN, T_RAMP, Q_HI, T_HOLD))
    L.append("!   検定は Check_chutepool.py。入力 cp_*.txt は make_chutepool.py が作る")
    L.append("!======================================================================")
    L.append("&list_sysparam\n  f_gridsystem = 0\n  dt = %g\n  t0 = 0\n  tt = %d\n  dt_disp = 3600\n  dt_file = %d\n  dt_recrd = 10\n"
             "  fn_geoinfo = '-'\n  fn_boundary = '-'\n  fn_record = '-'\n  fn_enc = '-'\n  dir_result = 'result_%s'\n  f_out_h = 1\n/\n" % (DT, T_END * 60, T_END * 60, name))
    L.append("&list_enc\n  f_dry_head_cap = %d        ! 高い地盤へ向かうエッジ水深の頭打ち(この検定の対象)\n/\n" % cap)
    L.append("&list_geoinfo\n  nx = %d\n  ny = %d\n  dx = %.1f\n  dy = %.1f\n  f_ztype = 1\n  fn_z = 'cp_z.txt'\n  f_masktype = 1\n  fn_mask = 'cp_mask.txt'\n"
             "  fn_rw = 'cp_rw.txt'      ! 河道マスク\n  f_rntype = 0\n  rn0 = %.2f               ! 斜面の粗度\n  rn0_rw = %.2f            ! 河道マスクのセルの粗度\n/\n" % (NX, NY, DX, DX, RN_LAND, RN_RIVER))
    L.append("&list_bound_edge\n  f_bc_n = 1                ! 北辺は自由流出(本川の出口)\n/\n")
    s = "&list_bound_source\n  src_cell(:,1,1) = %d, %d      ! 上流端の河道のセル(時刻は分)\n" % SOURCE
    for k, (t, q) in enumerate(((0.0, 0.0), (T_RISE, Q_LO), (T_SPIN, Q_LO), (T_SPIN + T_RAMP, Q_HI), (T_END, Q_HI))):
        s += "  src_val(:,%d,1) = %g, %.1f\n" % (k + 1, t, q)
    L.append(s + "/\n")
    s = "&list_record\n  pbxytype = 0\n"
    for n, (i, j) in enumerate(PROBES):
        s += "  pbxy(:,%d) = %d, %d\n" % (n + 1, i, j)
    s += "  flxytype = 0\n  flxy(:,1) = %d, %d, %d, %d   ! 池の中の測線\n/" % FLUX
    L.append(s)
    return "\n".join(L)


if __name__ == "__main__":
    if sys.argv[1] in FILES:
        print(cut(sys.argv[1]))
    elif sys.argv[1] == "param":        # 保守用: 置いてある param_*.txt はこの出力
        print(param(sys.argv[2]))
    elif sys.argv[1] == "names":
        print(" ".join(CASES))
