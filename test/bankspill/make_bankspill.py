#!/usr/bin/env python3
# test/bankspill の入力生成と定数(Check_bankspill.py・param_*.txt と定数を対で保守。標準ライブラリだけ)
#   1 セル幅の河道(勾配 S0、西が高い)が東へ流れ、列 IJ で南東へ 1 行ずれて(屈曲)、また東へ流れる。
#   河道の外は、河床より TER 高い台地(水は登らない)。台地のうち 2 つのセルだけを、河床より B 高い
#   「河岸のくぼみ」にする:
#     くぼみ S(side):  まっすぐな区間の河道のセル (IS, JC) の北隣 (IS, JC−1)。流れは河岸に平行
#     くぼみ H(head-on): 屈曲の外側のセル (IJ, JC)。上流から来る流れの正面にあり、屈曲のあとの
#                        河道のセル (IJ, JC+1)・(IJ+1, JC+1) にも接する(屈曲を近道する道になる)
#   流量は上流端のセルの湧き出しで与え、等流の水位が、くぼみの地盤の下 → 上 → 下 と動くように
#   ゆっくり上げ下げする。濡れた構成(wet)は、くぼみに FILM_Q の湧き出しを置いて薄い水膜で濡らす。
#   python3 make_bankspill.py z > bs_z.txt
import sys, math

NX, NY, DX = 60, 8, 200.0
JC = 4                               # 屈曲の上流の河道の行(屈曲の下流は JC + 1)
IJ = 31                              # 屈曲の列: (IJ−1, JC) → (IJ, JC+1)。くぼみ H は (IJ, JC)
IS = 15                              # くぼみ S の列: (IS, JC−1)
S0, RN, G, Z0 = 0.0015, 0.03, 9.8, 100.0
B, TER = 7.2, 25.0                   # くぼみの地盤・台地の高さ(河床から。m)
H_LO, H_HI = 5.2, 7.8                # 流量を上げ下げするときの等流水深の下端と上端 (m)
T_SPIN, T_RAMP, T_HOLD = 60.0, 100.0, 20.0    # 助走・上げ(下げ)・保持の長さ(分)
T_END = T_SPIN + 2 * T_RAMP + 2 * T_HOLD      # 計算の長さ(分)= 300
FILM_Q = 0.05                        # 濡れた構成のくぼみの湧き出し (m3/s)
CASES = {"wet_dt6": (6.0, True), "wet_dt15": (1.5, True), "dry_dt6": (6.0, False), "dry_dt15": (1.5, False)}
# プローブ: 1 = くぼみ S の上流側の斜め隣の河道のセル、2 = くぼみ S の真横の河道のセル、3 = くぼみ S、
#           4 = くぼみ H の手前(上流)の河道のセル、5 = くぼみ H、6 = 屈曲の下流の河道の 1 セル目
PROBES = [(IS - 1, JC), (IS, JC), (IS, JC - 1), (IJ - 1, JC), (IJ, JC), (IJ, JC + 1)]
I_FLUX = 50                          # 下流の測線の列


def qn(h):
    """等流の流量 (m3/s)。幅 1 セルの河道(側壁の摩擦は数えない = 単位幅のマニング式 × セル幅)"""
    return h ** (5.0 / 3.0) * math.sqrt(S0) / RN * DX


def bed(i):
    return Z0 - S0 * DX * (i - 1)


def is_channel(i, j):
    return (j == JC and i < IJ) or (j == JC + 1 and i >= IJ)


def ground(i, j):
    if is_channel(i, j):
        return bed(i)
    if (i, j) in ((IS, JC - 1), (IJ, JC)):
        return bed(i) + B
    return bed(i) + TER


def param(name):
    dt, wet = CASES[name]
    qa, qb = qn(H_LO), qn(H_HI)
    t1, t2, t3, t4 = T_SPIN, T_SPIN + T_RAMP, T_SPIN + T_RAMP + T_HOLD, T_SPIN + 2 * T_RAMP + T_HOLD
    L = []
    L.append("!======================================================================")
    L.append("! bankspill %s: 河岸のくぼみへのあふれ始め(dt = %g s、くぼみは%s)" % (name, dt, "薄い水膜で濡れている" if wet else "乾いている"))
    L.append("!   1 セル幅の河道(格子幅 %.0f m、勾配 %.4f、n = %.2f)。台地(河床 + %.0f m)のうち 2 セルだけが" % (DX, S0, RN, TER))
    L.append("!   河床より %.1f m 高いくぼみ: まっすぐな区間の脇 (%d, %d) と、屈曲の正面 (%d, %d)。" % (B, IS, JC - 1, IJ, JC))
    L.append("!   流量を %.0f → %.0f → %.0f m3/s(等流水深 %.1f → %.1f → %.1f m)と %.0f 分ずつで上げ下げする。" % (qa, qb, qa, H_LO, H_HI, H_LO, T_RAMP))
    L.append("!   検定は Check_bankspill.py。入力 bs_z.txt は make_bankspill.py が作る")
    L.append("!======================================================================")
    L.append("&list_sysparam\n  f_gridsystem = 0\n  dt = %g\n  t0 = 0\n  tt = %d\n  dt_disp = 3600\n  dt_file = %d\n  dt_recrd = 60\n"
             "  fn_geoinfo = '-'\n  fn_boundary = '-'\n  fn_record = '-'\n  dir_result = 'result_%s'\n  f_out_h = 1\n/\n" % (dt, T_END * 60, T_END * 60, name))
    L.append("&list_geoinfo\n  nx = %d\n  ny = %d\n  dx = %.1f\n  dy = %.1f\n  f_ztype = 1\n  fn_z = 'bs_z.txt'\n  f_rntype = 0\n  rn0 = %.3f\n/\n" % (NX, NY, DX, DX, RN))
    L.append("&list_bound_edge\n  f_bc_e = 1                ! 東辺は自由流出\n/\n")
    s = "&list_bound_source\n  src_cell(:,1,1) = 1, %d      ! 河道の上流端(時刻は分)\n" % JC
    for k, (t, q) in enumerate(((0.0, qa), (t1, qa), (t2, qb), (t3, qb), (t4, qa), (T_END, qa))):
        s += "  src_val(:,%d,1) = %g, %.2f\n" % (k + 1, t, q)
    if wet:
        for n, (i, j) in enumerate(((IS, JC - 1), (IJ, JC))):
            s += "  src_cell(:,1,%d) = %d, %d     ! くぼみの水膜\n  src_val(:,1,%d) = 0, %.2f\n  src_val(:,2,%d) = %g, %.2f\n" % (n + 2, i, j, n + 2, FILM_Q, n + 2, T_END, FILM_Q)
    L.append(s + "/\n")
    s = "&list_record\n  pbxytype = 0\n"
    for n, (i, j) in enumerate(PROBES):
        s += "  pbxy(:,%d) = %d, %d\n" % (n + 1, i, j)
    s += "  flxytype = 0\n  flxy(:,1) = %d, %d, %d, %d   ! 屈曲の下流の河道の測線\n/" % (I_FLUX, JC + 2, I_FLUX, JC)
    L.append(s)
    return "\n".join(L)


if __name__ == "__main__":
    if sys.argv[1] == "z":
        for j in range(1, NY + 1):
            print(" ".join("%.3f" % ground(i, j) for i in range(1, NX + 1)))
    elif sys.argv[1] == "param":        # 保守用: 置いてある param_*.txt はこの出力
        print(param(sys.argv[2]))
    elif sys.argv[1] == "consts":
        print("Q = %.1f → %.1f m3/s, B = %.1f m, 等流水深が B になる流量 %.1f m3/s" % (qn(H_LO), qn(H_HI), B, qn(B)))
