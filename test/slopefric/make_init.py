#!/usr/bin/env python3
"""test/slopefric の入力と設定ファイルの生成(Run.sh・Run_MPI.sh が呼ぶ)。

一様な急斜面(傾斜角 30°、勾配 G = tan30°、下り向きが格子の x 軸から角度 φ)の全面に一定の雨を
降らせ、下りの辺(東と北)から自由流出させる。定常の薄層流では、各セルで水深の勾配と移流が
勾配に比べて小さく、等流の関係(局所の釣り合い)が成り立つ。

  f_gravity_correction = 1(2026-11-05 までの既定): 摩擦にも g_e が掛かって相殺し、古典の水平投影のマニング式
      h = (n² q² / tanθ)^{3/10}(h は鉛直の水深、q = h|V| は水平の単位幅流量)
  f_gravity_correction = 2: 摩擦を斜面に沿う速さと地盤に直角な水深で評価(developer.md §93)。
      斜面に沿う式の等流 h_n = (n² q² / sinθ)^{3/10}、h = h_n / cosθ(Chow 1959、Van Emelen ら 2014)

の 2 つを、下り向き φ = 0°・22.5°・45° と 8 近傍・4 近傍の全部で回す(12 ケース)。

流砂のせん断(名前の末尾 _sed。下り向き 0°・45°、8 近傍、f_gravity_correction 1・2 の 4 ケース):
同じ流れに掃流砂(f_fluvial = 1)を加え、侵食の始まる位置を無次元掃流力が限界 τ*c に達する位置
(等流の解析解)と比べる。斜面の上の端からの流下方向の水平距離 ℓ で、q = r ℓ(r は雨)、
  f_gravity_correction = 1: τ* = h tanθ / (s d)、h = (n² q² / tanθ)^{3/10}(古典)
  f_gravity_correction = 2: τ* = h_n sinθ / (s d)、h_n = (n² q² / sinθ)^{3/10}(斜面に沿う底面せん断
      τ_b = ρ g h_n sinθ。§93)
粒径は f_gravity_correction = 2 の始まりが ℓ = SED_LC になる値にする(1 では上流へ約 5 m ずれる)。
定数は Check_slopefric.py と対。

  python3 make_init.py        全ケースの d_<斜面>/z.txt と p_<case>.txt を書く
  python3 make_init.py list   ケース名を 1 行ずつ出す
"""
import math
import os
import sys

L, DX = 60.0, 1.0            # 領域の一辺、格子間隔 (m)
THETA = 30.0                 # 斜面の傾斜角 (deg)
G = math.tan(math.radians(THETA))
RAIN = 300.0                 # 雨 (mm/h)。評価する内部の水深が限界水深 dd・仮想水深 dv(1 mm)より十分深くなる値
RN = 0.1                     # マニングの粗度
DT, TT = 0.1, 1200.0         # 時間刻み・計算時間 (s)。到達時間(約 2 分)の 10 倍で定常
PHIS = (0.0, 22.5, 45.0)     # 下り向きの格子の x 軸からの角度 (deg)
NBS = (8, 4)                 # 近傍の数(4 は p_diagratio = 0)
GCS = (1, 2)                 # f_gravity_correction
SED_PHIS = (0.0, 45.0)       # 流砂の構成の下り向き (deg)(8 近傍)
SED_LC = 30.0                # f_gravity_correction = 2 の侵食の始まり(流下方向の水平距離 m)
TAUSC, SGRAV, POROSITY = 0.05, 1.65, 0.4
SED_MORFAC = 0.02            # 河床変化を小さく保つ(始まりの位置だけを見る。morfac = 1 では 20 分で下流の河床が
                             #   水深の数十倍変わり、流れとの相互作用で始まりより下流に堆積・上流へ頭部侵食が出る)


def sed_d50():
    """f_gravity_correction = 2 で ℓ = SED_LC の τ* が τ*c になる粒径 (m)。"""
    th = math.radians(THETA)
    q = RAIN / 3.6e6 * SED_LC
    hn = (RN ** 2 * q * q / math.sin(th)) ** 0.3
    return hn * math.sin(th) / (SGRAV * TAUSC)


def sed_lc(gc):
    """侵食の始まる流下方向の水平距離 ℓ_c (m)(等流の解析解)。"""
    th = math.radians(THETA)
    d = sed_d50()
    if gc == 1:
        hc = TAUSC * SGRAV * d / math.tan(th)
        qc = (hc ** (10.0 / 3.0) * math.tan(th) / RN ** 2) ** 0.5
    else:
        hc = TAUSC * SGRAV * d / math.sin(th)
        qc = (hc ** (10.0 / 3.0) * math.sin(th) / RN ** 2) ** 0.5
    return qc / (RAIN / 3.6e6)


def case_name(phi, nb, gc, sed=False):
    return f"p{phi:g}_n{nb}_g{gc}".replace(".", "p") + ("_sed" if sed else "")


CASES = [(p, n, gc) for gc in GCS for p in PHIS for n in NBS]
CASES_SED = [(p, 8, gc) for gc in GCS for p in SED_PHIS]


def write_case(phi, nb, gc, sed=False):
    name = case_name(phi, nb, gc, sed)
    n = int(round(L / DX))
    ph = math.radians(phi)
    ddir = f"d_p{phi:g}".replace(".", "p")              # 地形は近傍・補正の有無で共通
    os.makedirs(ddir, exist_ok=True)
    rows = []
    for j in reversed(range(n)):                  # 先頭行が北端(行 0 が南端)
        y = (j + 0.5) * DX
        rows.append(" ".join(f"{100.0 - G * (((i + 0.5) * DX) * math.cos(ph) + y * math.sin(ph)):.8f}"
                             for i in range(n)))
    with open(os.path.join(ddir, "z.txt"), "w") as f:
        f.write("\n".join(rows) + "\n")
    pd = "0.5857864376" if nb == 8 else "0.0"
    bcn = 1 if phi > 0.0 else 0                   # 北辺は下りの向きに北の成分があるときだけ開く
    gm_fn = "  fn_geomorph = '-'\n" if sed else ""
    out_z = "  f_out_z = 1\n" if sed else ""
    sd_ln = "  sd0 = 1.0                 ! 可動層厚(供給量制限が効かない厚さ)\n" if sed else ""
    gm_grp = (f"""&list_geomorph
  dt_geomorph = 0.0
  morfac = {SED_MORFAC:g}             ! 河床変化を小さく保つ(侵食の始まりの位置だけを見る)
  f_fluvial = 1              ! 掃流砂(芦田・道上)
  f_qbform = 1
  fluv_d50 = {sed_d50():.6f}        ! f_gravity_correction = 2 の侵食の始まりが ℓ = {SED_LC:g} m になる粒径
  fluv_tausc = {TAUSC:g}
  fluv_porosity = {POROSITY:g}
  fluv_sgrav = {SGRAV:g}
/
""" if sed else "")
    with open(f"p_{name}.txt", "w") as f:
        f.write(f"""!======================================================================
! slopefric: ケース {name}(make_init.py が生成)
!   傾斜角 {THETA:g}°(勾配 {G:.6f})、下り向き {phi:g}° の一様な斜面に {RAIN:g} mm/h の雨を降らせ、
!   {TT:g} 秒後(定常)の水深と流速を等流の関係と比べる(Check_slopefric.py)
!======================================================================
&list_sysparam
  dt = {DT:g}
  t0 = 0
  tt = {TT:g}
  dt_disp = {TT:g}
  dt_file = {TT:g}
  dt_recrd = {TT:g}
  fn_geoinfo = '-'
  fn_initial = '-'
  fn_enc = '-'
  fn_precip = '-'
  fn_boundary = '-'
{gm_fn}  dir_data = '{ddir}'
  dir_result = 'result_{name}'
  dir_save = 'save_{name}'
  f_state_save = 1
  f_out_h = 1
  f_out_u = 1
  f_out_v = 1
{out_z}/
&list_enc
  f_gravity_correction = {gc}   ! 1: 有効重力 / 2: + 斜面に沿う摩擦(既定。§93)
  p_diagratio = {pd}       ! 8 近傍(既定)/ 4 近傍(0)
/
&list_initial
  f_htype = 0
  h0 = 0.0
/
&list_precip
  prtype = 1
  dt_prupdate = 1
  prval(1:2,1) = 0, {RAIN:g}
  prval(1:2,2) = 9999999, {RAIN:g}
/
&list_bound_edge
  f_bc_e = 1                 ! 東辺は自由流出(下り)
  f_bc_n = {bcn}                 ! 北辺(下り向きに北の成分があるとき自由流出)
/
&list_geoinfo
  lx = {n * DX:g}
  ly = {n * DX:g}
  nx = {n}
  ny = {n}
  f_ztype = 1
  fn_z = 'z.txt'
  f_rntype = 0
  rn0 = {RN:g}
{sd_ln}/
{gm_grp}""")
    return name


def main():
    if sys.argv[1:] == ["list"]:
        for c in CASES:
            print(case_name(*c))
        for c in CASES_SED:
            print(case_name(*c, sed=True))
        return
    for c in CASES:
        write_case(*c)
    for c in CASES_SED:
        write_case(*c, sed=True)


if __name__ == "__main__":
    main()
