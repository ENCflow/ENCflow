#!/usr/bin/env python3
"""test/debris 構成 9・10 の設定ファイルの生成(Run.sh・Run_MPI.sh が呼ぶ)。

高橋・中川の侵食・堆積則(f_dbed = 3)への追加(developer.md §28.18)の検定。地形と初期水深は構成 7 と同じ
6 本の水路(make_eq.py の z_eq.txt・h_eq.txt。tanθ = 0.60・0.25・0.15・0.10・0.05・0.02、幅 1 セル、長さ 300 m)。
抵抗はマニングだけ(f_dbres = 0)。

構成 9: 不飽和床の侵食式(f_dbunsat = 1)と緩い勾配の平衡濃度(f_dbimm = 1)の侵食速度
  清水を流し込み、流下とともに濃度が 0 から平衡濃度へ上がる流れを作る。地形の更新は 1 秒ごと。
  同じ設定を T 秒までと T + 1 秒までの 2 回計算し、2 つの保存状態から最後の更新の侵食量と、更新の直前の
  水深・濃度・流動面の勾配を求めて、不飽和床の侵食式の値と突き合わせる(Check_debris_tk.py の rate)。
    p_tk_un_a / p_tk_un_b     : 地下水計算なし。db_satbed = 0.8(不飽和)
    p_tk_ug_a / p_tk_ug_b     : 地下水計算あり。gw_sat0 = 0.5(hg < sy0 sd = 不飽和)
    p_tk_sg_1 / p_tk_sg_0     : 地下水計算あり。gw_sat0 = 1(飽和)。f_dbunsat = 1 と 0 の結果が
                                バイト一致する(飽和したセルは飽和床の式のまま)
構成 10: 緩い勾配の掃流状集合流動の平衡濃度(f_dbimm = 1)
  構成 7 と同じ濃度の流入(水と土砂)で 120 秒流し、下流の濃度が平衡濃度に一致することを確かめる
  (Check_debris_tk.py の eq)。f_dbed = 3 の平衡濃度は流動面の勾配で決まるので、流れの揺れがそのまま
  濃度に写る。構成 7 の粗度 0.05(フルード数 0.5〜3)では転波列で濃度が 1e-2〜1e-4 揺れるため、粗度を
  RN_EQ = 0.3(フルード数 0.5 以下)にし、流入の流量を等流水深が同じになるよう 0.05/0.3 倍にする。
  侵食係数は緩和を速めるため δe = 0.2(緩和の長さ 0.25 m)。
    p_tk_eq0                  : f_dbimm = 0(石礫型の平衡濃度 c∞ を全勾配で。従来)
    p_tk_eq1                  : f_dbimm = 1(c∞ < 1/6.7 の勾配で 6.7 c∞²)

  python3 make_tk.py        p_tk_*.txt を書く
  python3 make_tk.py list   ケース名を 1 行ずつ出す
定数は Check_debris_tk.py・make_eq.py と対。
"""
import sys

import make_eq as me

T_RATE = 30.0                 # 構成 9 の 1 回目の終了時刻 (s)。2 回目は T_RATE + DT_GEO
DT, DT_GEO = 0.02, 1.0
RN, H0 = 0.05, me.H0
RN_EQ = 0.3                               # 構成 10 の粗度(流れを落ち着かせる。先頭の説明)
D50, KUNS, DELTE = 0.05, 0.01, 0.2       # 代表粒径 (m)、不飽和床の侵食式の K(既定値)、構成 10 の δe
SATBED, SY0, POROSITY = 0.8, 0.2, 0.4
# 構成 7(param_eq.txt)の流入: 水路 k の (流量 m³/s, 流入の hs/h 比)
INFLOW_EQ = [(0.105129, 0.950000), (0.067860, 0.481898), (0.052564, 0.188034),
             (0.042919, 0.069656), (0.030348, 0.014029), (0.019194, 0.010000)]

CASES = {
    #  name         tt                  gw     gw_sat0  unsat  imm  流入の土砂  dt_geomorph  δe
    "tk_un_a": dict(tt=T_RATE,          gw=False, sat0=0.0, unsat=1, imm=1, sed=False, dtg=DT_GEO, delte=0.0001, rn=RN),
    "tk_un_b": dict(tt=T_RATE + DT_GEO, gw=False, sat0=0.0, unsat=1, imm=1, sed=False, dtg=DT_GEO, delte=0.0001, rn=RN),
    "tk_ug_a": dict(tt=T_RATE,          gw=True,  sat0=0.5, unsat=1, imm=1, sed=False, dtg=DT_GEO, delte=0.0001, rn=RN),
    "tk_ug_b": dict(tt=T_RATE + DT_GEO, gw=True,  sat0=0.5, unsat=1, imm=1, sed=False, dtg=DT_GEO, delte=0.0001, rn=RN),
    "tk_sg_1": dict(tt=T_RATE,          gw=True,  sat0=1.0, unsat=1, imm=1, sed=False, dtg=DT_GEO, delte=0.0001, rn=RN),
    "tk_sg_0": dict(tt=T_RATE,          gw=True,  sat0=1.0, unsat=0, imm=1, sed=False, dtg=DT_GEO, delte=0.0001, rn=RN),
    "tk_eq0":  dict(tt=120.0,           gw=False, sat0=0.0, unsat=0, imm=0, sed=True,  dtg=0.0,    delte=DELTE,  rn=RN_EQ),
    "tk_eq1":  dict(tt=120.0,           gw=False, sat0=0.0, unsat=0, imm=1, sed=True,  dtg=0.0,    delte=DELTE,  rn=RN_EQ),
}


def write_case(name, c):
    inflow = ""
    for k, (q, cs) in enumerate(INFLOW_EQ, 1):
        q = q * RN / c["rn"]              # 等流水深を保つ(流量は粗度に反比例)
        inflow += f"  inflow_cell(1:2,1,{k}) = {2 * k}, 1\n"
        inflow += f"  inflow_val(1:2,1,{k}) = 0, {q:.6f}\n  inflow_val(1:2,2,{k}) = 9999, {q:.6f}\n"
        if c["sed"]:
            inflow += f"  inflow_cs(1:2,1,{k}) = 0, {cs:.6f}\n  inflow_cs(1:2,2,{k}) = 9999, {cs:.6f}\n"
    gwfn = "  fn_gwflow = '-'\n" if c["gw"] else ""
    gw = ""
    if c["gw"]:
        gw = f"""&list_gwflow
  f_gwvertical = 2          ! Green-Ampt
  gw_sat0 = {c['sat0']:g}             ! 層1の初期飽和度
/
&list_gwflow_greenampt
  gw_ksv_mmh = 1.0e-6       ! 浸透能 (mm/h)。正の値が要るので極小値(地下貯留は初期値のまま)
  gw_psif = 0.0
/
"""
    with open(f"p_{name}.txt", "w") as f:
        f.write(f"""!======================================================================
! debris: ケース {name}(make_tk.py が生成。構成 9・10 の説明は make_tk.py の先頭)
!======================================================================
&list_sysparam
  f_gridsystem = 0
  f_govequation = 0
  dt = {DT:g}
  t0 = 0
  tt = {c['tt']:g}
  dt_disp = {c['tt']:g}
  dt_file = {c['tt']:g}
  dt_recrd = {c['tt']:g}
  fn_geoinfo = '-'
  fn_initial = '-'
  fn_enc = '-'
  fn_boundary = '-'
  fn_geomorph = '-'
{gwfn}  dir_result = 'result_{name}'
  dir_save = 'save_{name}'
  f_state_save = 1          ! 検定は save_{name}/state.dat の h・hs・z(倍精度)を読む
  f_check_cfl = 1
/
&list_enc
  f_gravity_correction = 2
/
&list_initial
  f_htype = 1
  fn_hinit = 'h_eq.txt'     ! 水路だけ {H0:g} m(土砂なし)
/
&list_geoinfo
  lx = {me.NX:g}
  ly = {me.NY:g}
  nx = {me.NX}
  ny = {me.NY}
  f_ztype = 1
  fn_z = 'z_eq.txt'
  f_rntype = 0
  rn0 = {c['rn']:g}
  sd0 = 5.0                 ! 可動層厚(侵食で使い切らない厚さ)
  sy0 = {SY0:g}
/
&list_bound_edge
  f_bc_s = 1                ! 南辺は自由流出
/
&list_bound_inflow          ! 水路 k = 1〜6(列 2k)の北端。Q はマニングの等流水深 {H0:g} m 相当
{inflow}/
&list_geomorph
  dt_geomorph = {c['dtg']:g}
  morfac = 1.0              ! f_debris は 1 必須
  f_debris = 1
  f_dbed = 3                ! 高橋・中川 (1991)
  f_dbres = 0               ! マニングのみ
  f_dbstop = 0
  db_phi = 35.0             ! tanφ = 0.7002
  db_d50 = {D50:g}
  db_delte = {c['delte']:g}
  db_deltd = 0.5
  f_dbunsat = {c['unsat']}             ! 1: 河床が不飽和のセルは不飽和床の侵食式(K は既定の {KUNS:g})
  db_satbed = {SATBED:g}           ! 地下水計算なしのとき、1 未満なら不飽和
  f_dbimm = {c['imm']}               ! 1: 緩い勾配の掃流状集合流動(平衡濃度 6.7 c∞²、δ'd は既定の 0.1)
  fluv_porosity = {POROSITY:g}       ! C* = 0.6、上限 0.9 C* = 0.54
/
{gw}""")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        print("\n".join(CASES))
        return
    for name, c in CASES.items():
        write_case(name, c)


if __name__ == "__main__":
    main()
