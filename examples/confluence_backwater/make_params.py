#!/usr/bin/env python3
# examples/confluence_backwater の設定ファイル param*.txt を書く(保守用。置いてある param*.txt はこの出力)
#   python3 make_params.py
import os

HERE = os.path.dirname(os.path.abspath(__file__))

HEAD = """!======================================================================
! confluence_backwater: 合流点の背水による支川の氾濫({title})
{desc}
!   共通: 西から東へ流れる本川(幅 200 m、勾配 1/1500)の湾曲部の外岸(北岸)に、北から支川(幅 80 m、
!   勾配 1/1000、堤防の天端 = 河床 + 4.5 m)が直角に合流する。本川は合流点の 1.6 km 下流に狭窄部
!   (幅 100 m、600 m)があり、洪水時に合流点の水位が上がる。支川の両岸は丘陵に囲まれた低地(堤内地)。
!   流量: 本川は平水 300 m3/s → 1〜6 h で 2,800 m3/s → 8 h まで続き 13 h で平水。支川は平水 20 m3/s、
!   出水は 2 h で 300 m3/s に上がり 3 h で戻る。詳細と結果は README.md。入力は make_terrain.py が data/ に作る
!======================================================================
"""

SYS = """&list_sysparam
  f_gridsystem = 0
  dt = 1.0                  ! 時間刻み (s)(本川の √(gh) ≈ 8 m/s、Δx = 20 m)
  t0 = 0
  tt_c = '14h'              ! 計算終了時刻
  dt_disp_c = '30m'
  dt_file_c = '30m'         ! 分布の出力(浸水の広がりと堤内地の水量の時間変化に使う)
  dt_recrd_c = '5m'
  fn_geoinfo = '-'
  fn_enc = '-'
  fn_initial = '-'          ! 初期条件(河道の平水の水深)
  fn_boundary = '-'
  fn_record = '-'
{extra_fn}  dir_data = 'data'
  dir_result = 'result_{case}'
  f_out_h = 1
  f_out_hmax = 1
/

&list_initial
  f_htype = 1
  fn_hinit = 'h0.txt'       ! 本川に平水 300 m3/s、支川に 20 m3/s の等流水深。堤内地は乾いている
/

&list_enc
  f_exflux_reduction = 1    ! 乾いた地面へ広がる浸水の先端の定石
/

!======================================================================
! 地理情報(dx = 20 m。make_terrain.py が生成。堤防は z の標高そのもの = 解像した堤防)
!======================================================================
&list_geoinfo
  nx = 300
  ny = 370
  dx = 20.0
  dy = 20.0
  f_ztype = 1
  fn_z = '{zfile}'{zcomment}
  f_rntype = 1
  fn_rn = 'rn.txt'          ! 本川 0.03、支川 0.035、堤防・堤内地 0.05
  f_masktype = 1
  fn_mask = 'mask.txt'      ! 丘陵は計算しない(壁)
/

!======================================================================
! 境界: 本川は西辺の 10 セルから流入、東辺の 10 セルは本川と支川の流入の和の等流水深の水位
!   (Manning、幅 200 m、n 0.03、勾配 1/1500。2 次元計算なので R = h)。支川は北辺の 4 セルから流入
!======================================================================
&list_bound_stage
  fn_stage_cell(1) = 'cells_out.txt'
  fn_stage_val(1) = 'stage_{stage}.txt'
/
&list_bound_inflow
  fn_inflow_cell(1) = 'cells_main.txt'
  fn_inflow_val(1) = 'q_main_{qm}.txt'   ! 本川の流量(時刻 min, m3/s)
  inflow_dist(1) = 2
  fn_inflow_cell(2) = 'cells_trib.txt'
  fn_inflow_val(2) = 'q_trib_{qt}.txt'   ! 支川の流量
  inflow_dist(2) = 2
/
"""

REC = """
!======================================================================
! 計測: プローブ(1 本川の合流点の北岸 = 外岸、2 同じ列の南岸 = 内岸、3 本川の合流点の 1 km 上流、
!   4 支川の口から 200 m、5 支川の水位観測所 = 口から 2 km、6 支川の口から 4 km、7 堤内地 A(支川の西)、
!   8 堤内地 B(支川の東)、9 支川の口(水門の内側。ケース gate のポンプの運転の基準のセル))
!   測線(1 支川の口(行 314)、2 支川の口から 200 m、3 支川の水位観測所(口から 2 km)、4 本川の合流点の上流
!   (x = 2.0 km)、5 本川の合流点の下流(x = 3.3 km)、6 本川の下流端の手前(x = 5.7 km)。下流向きが正 = 支川の逆流は負。
!   支川の測線は堤防の列 128・133 までで、堤内地の流れを含まない)
!======================================================================
&list_record
  pbxytype = 0
  pbxy(:,1) = 130, 316
  pbxy(:,2) = 130, 325
  pbxy(:,3) = 81, 335
  pbxy(:,4) = 130, 305
  pbxy(:,5) = 130, 215
  pbxy(:,6) = 130, 115
  pbxy(:,7) = 115, 300
  pbxy(:,8) = 145, 300
  pbxy(:,9) = 129, 313
  flxytype = 0
  flxy(:,1) = 128, 314, 133, 314
  flxy(:,2) = 128, 305, 133, 305
  flxy(:,3) = 128, 215, 133, 215
  flxy(:,4) = 100, 339, 100, 328
  flxy(:,5) = 165, 340, 165, 329
  flxy(:,6) = 285, 341, 285, 330
/
"""

GATE_NL = """
!======================================================================
! 対策 B: 合流点の水門(締切の 4 セルを抜けるカルバート 4 門。フラップゲート = 本川の水が逆流しない)
!   と排水ポンプ(支川の水を本川へ 50 m3/s。支川の口の水位 21.2 m から運転を始め、21.7 m で全量)
!   締切は支川の口の 1 行(行 315)を本川の堤防の天端の高さにした地形(z_gate.txt)
!======================================================================
&list_struct_culvert
  culv_in_cell(:,1,1) = 129, 314     ! 支川の側
  culv_out_cell(:,1,1) = 129, 316    ! 本川の側
  culv_width(1) = 18.0
  culv_height(1) = 4.0
  culv_zin(1) = 19.25
  culv_zout(1) = 19.25
  culv_length(1) = 20.0
  culv_flap(1) = 1
  culv_in_cell(:,1,2) = 130, 314     ! 支川の側
  culv_out_cell(:,1,2) = 130, 316    ! 本川の側
  culv_width(2) = 18.0
  culv_height(2) = 4.0
  culv_zin(2) = 19.25
  culv_zout(2) = 19.25
  culv_length(2) = 20.0
  culv_flap(2) = 1
  culv_in_cell(:,1,3) = 131, 314     ! 支川の側
  culv_out_cell(:,1,3) = 131, 316    ! 本川の側
  culv_width(3) = 18.0
  culv_height(3) = 4.0
  culv_zin(3) = 19.25
  culv_zout(3) = 19.25
  culv_length(3) = 20.0
  culv_flap(3) = 1
  culv_in_cell(:,1,4) = 132, 314     ! 支川の側
  culv_out_cell(:,1,4) = 132, 316    ! 本川の側
  culv_width(4) = 18.0
  culv_height(4) = 4.0
  culv_zin(4) = 19.25
  culv_zout(4) = 19.25
  culv_length(4) = 20.0
  culv_flap(4) = 1
/
&list_struct_pump
  pump_in_cell(:,1,1) = 129, 313
  pump_in_cell(:,2,1) = 130, 313
  pump_in_cell(:,3,1) = 131, 313
  pump_in_cell(:,4,1) = 132, 313
  pump_out_cell(:,1,1) = 129, 318
  pump_out_cell(:,2,1) = 130, 318
  pump_out_cell(:,3,1) = 131, 318
  pump_out_cell(:,4,1) = 132, 318
  f_pump_ref(1) = 0                 ! 基準 = 取水の先頭のセルの水位
  pump_rule(:,1,1) = 21.2, 0.0      ! (水位 m, 流量 m3/s)
  pump_rule(:,2,1) = 21.7, 50.0
/
"""

CASES = [
    # (ファイル名, ケース名, 題, 説明の行, z, 本川, 支川, 水位, 追加の fn, 追加の namelist)
    ("param_trib.txt", "trib", "ケース trib: 支川だけの出水",
     "!   本川は平水のまま、支川だけが出水する(7 h にピーク 300 m3/s)。支川は自分の流量ではあふれない",
     "z.txt", "base", "same", "base_same", "", ""),
    ("param_main.txt", "main", "ケース main: 本川だけの出水",
     "!   支川は平水 20 m3/s のまま、本川だけが出水する。本川の水位が支川を逆流して堤防を越える",
     "z.txt", "flood", "base", "flood_base", "", ""),
    ("param_early.txt", "early", "ケース early: 両方の出水(支川のピークが 3 h 早い)",
     "!   支川のピーク(4 h)が、本川の水位が高くなる前に来る",
     "z.txt", "flood", "early", "flood_early", "", ""),
    ("param.txt", "same", "ケース same: 両方の出水(ピークが重なる)",
     "!   支川のピーク(7 h)が本川のピーク(6〜8 h)に重なる。対策の 2 ケースの基準",
     "z.txt", "flood", "same", "flood_same", "", ""),
    ("param_raise.txt", "raise", "ケース raise: 対策 A 背水区間の支川の堤防のかさ上げ",
     "!   ケース same と同じ流量で、合流点から 3 km(支川の元の天端が本川の堤防の天端に届くまで = 背水区間)の\n"
     "!   支川の堤防を、合流点の本川の堤防の天端(26.72 m)までかさ上げした地形(z_raise.txt)",
     "z_raise.txt", "flood", "same", "flood_same", "", ""),
    ("param_gate.txt", "gate", "ケース gate: 対策 B 合流点の水門と排水ポンプ",
     "!   ケース same と同じ流量で、支川の口を締め切り、フラップゲートのカルバート(水門)とポンプで本川へ出す",
     "z_gate.txt", "flood", "same", "flood_same", "  fn_structure = '-'        ! 水門(カルバート)と排水ポンプ\n", GATE_NL),
]


COARSE = """!======================================================================
! confluence_backwater 補足 1: 同じ地区を Δx = 100 m の粗い格子で表す({title}。河道マスクの作り方: {mtitle})
{desc}
!   河道マスクは、本編の Δx = 20 m の河道マスクから 100 m のセルごとに本川が占める割合(占有率)を数えて作る
!   (make_coarse.py)。{mdesc}
!   堤防は地形で表せないので、河道の堤防(仮想壁面)の天端を絶対標高で与える(fn_bank、f_bank_datum = 2)。
!   地形の式と流量は本編と同じ。入力は make_coarse.py が data_coarse_{method}/ に作る
!======================================================================
&list_sysparam
  f_gridsystem = 0
  dt = 2.0                  ! 時間刻み (s)(Δx = 100 m)
  t0 = 0
  tt_c = '14h'
  dt_disp_c = '30m'
  dt_file_c = '30m'
  dt_recrd_c = '5m'
  fn_geoinfo = '-'
  fn_enc = '-'
  fn_initial = '-'
  fn_boundary = '-'
  fn_channel = '-'          ! 河道(サブグリッド河道幅・堤防の仮想壁面)
  fn_record = '-'
  dir_data = 'data_coarse_{method}'
  dir_result = 'result_coarse_{case}_{method}'
  f_out_h = 1
  f_out_hmax = 1
/

&list_initial
  f_htype = 1
  fn_hinit = 'h0.txt'       ! 本川に平水 300 m3/s、支川に 20 m3/s の等流水深(支川は幅の中の水深)
/

&list_enc
  f_exflux_reduction = 1
/

&list_geoinfo
  nx = 60
  ny = 74
  dx = 100.0
  dy = 100.0
  f_ztype = 1
  fn_z = 'z.txt'            ! 河道のセルは河床、ほかは堤内地の地盤高(本編と同じ式をセルの中心で評価)
  f_rntype = 1
  fn_rn = 'rn.txt'          ! 本川 0.03、支川 0.035、堤内地 0.05
  f_masktype = 1
  fn_mask = 'mask.txt'
  fn_rw = 'rw.txt'          ! 河道マスク(本川と支川)
/

&list_channel
  fn_bank = 'bank.txt'      ! 堤防の天端(河道のセルに絶対標高。本川 = 河床 + 8.5 m、支川 = 河床 + 4.5 m)
  f_bank_datum = 2
{width_line}
/

&list_bound_stage
  fn_stage_cell(1) = 'cells_out.txt'
  fn_stage_val(1) = 'stage_{stage}.txt'   ! 本編と同じ流量の等流水深(粗い格子の下流端の河床から)
/
&list_bound_inflow
  fn_inflow_cell(1) = 'cells_main.txt'
  fn_inflow_val(1) = 'q_main_{qm}.txt'
  inflow_dist(1) = 2
  fn_inflow_cell(2) = 'cells_trib.txt'
  fn_inflow_val(2) = 'q_trib_{qt}.txt'
  inflow_dist(2) = 2
/

!======================================================================
! 計測: 本編と同じ場所(セル番号は粗い格子)。支川の中心 x = 2,600 m は粗い格子の列 26(中心 2,550 m)に置く。
!   測線は 1 支川の口(行 63)、2 支川の水位観測所(口から 2 km)、3〜5 本川(本編の 4〜6 と同じ位置)。
!   支川の測線は東隣の堤内地のセルを含む(1 セルの測線は書けない。口の行の東隣は本川の堤防に接し、流れはない)
!======================================================================
&list_record
  pbxytype = 0
  pbxy(:,1) = 26, 64
  pbxy(:,2) = 26, 65
  pbxy(:,3) = 17, 67
  pbxy(:,4) = 26, 62
  pbxy(:,5) = 26, 44
  pbxy(:,6) = 26, 24
  pbxy(:,7) = 23, 60
  pbxy(:,8) = 29, 60
  pbxy(:,9) = 26, 63
  flxytype = 0
  flxy(:,1) = 26, 63, 27, 63
  flxy(:,2) = 26, 44, 27, 44
  flxy(:,3) = 20, 69, 20, 66
  flxy(:,4) = 33, 69, 33, 66
  flxy(:,5) = 57, 69, 57, 66
/
"""

COARSE_CASES = [
    ("main", "ケース main: 本川だけの出水", "!   本編の param_main.txt と同じ流量", "flood", "base", "flood_base"),
    ("same", "ケース same: 両方の出水(ピークが重なる)", "!   本編の param.txt と同じ流量", "flood", "same", "flood_same"),
]
# 粗い格子の河道マスクの作り方(make_coarse.py の METHODS)
COARSE_METHODS = [
    ("simple", "簡便", "簡便: 占有率 50 % 以上のセルを本川の河道にし、幅は与えない(解像)。支川(幅 80 m)は中心線の\n"
     "!   1 列の解像した河道"),
    ("occ", "占有率のまま", "占有率のまま: 占有率 5 % 以上のセルをすべて本川の河道にし、幅を占有率 × 100 m にする。\n"
     "!   支川(幅 80 m)は中心線の 1 列にし、幅 80 m を与える(fn_width)"),
    ("fixed", "直したもの", "直したもの: 占有率のままの河道マスクの、格子の軸に沿う区間(狭窄部とその前後)を、列ごとに\n"
     "!   解像したセル + 残りの幅のセル 1 つに詰め直す(狭窄部の 60 m × 2 → 100 m + 20 m)。支川は占有率のままと同じ"),
]
# 河道幅の行: 簡便は幅を与えない(河道マスクだけ)
WIDTH_LINE = {
    "simple": "  ! fn_width は与えない(河道マスクだけ。河道のセルはどれもセル幅いっぱいの河道)",
    "occ": "  fn_width = 'width.txt'    ! 河道幅(9999 = 解像。それ以外はサブグリッド河道の幅)",
    "fixed": "  fn_width = 'width.txt'    ! 河道幅(9999 = 解像。それ以外はサブグリッド河道の幅)",
}


STEADY = """!======================================================================
! confluence_backwater 補足: 支川の背水曲線を 1 次元の理論と比べる定常計算({title})
!   本川 1,500 m3/s・支川 100 m3/s の一定の流量を 6 h 流して定常にする(支川はあふれない)。
!   支川の水面形を、広い矩形断面・Manning の漸変流の式(1 次元)の解と比べる(plot_results.py)。
!   地形・境界の置き方は{base}と同じ
!======================================================================
&list_sysparam
  f_gridsystem = 0
  dt = {dt}
  t0 = 0
  tt_c = '6h'
  dt_disp_c = '1h'
  dt_file_c = '1h'          ! 最後の 2 つの出力で定常を確かめる
  dt_recrd_c = '10m'
  fn_geoinfo = '-'
  fn_enc = '-'
  fn_initial = '-'
  fn_boundary = '-'
{chan_fn}  fn_record = '-'
  dir_data = '{ddir}'
  dir_result = 'result_{rname}'
  f_out_h = 1
  f_out_e = 1
/

&list_initial
  f_htype = 1
  fn_hinit = 'h0_steady.txt' ! 本川 1,500 m3/s・支川 100 m3/s の等流水深
/

&list_enc
  f_exflux_reduction = 1
/
{geo}
&list_bound_stage
  fn_stage_cell(1) = 'cells_out.txt'
  fn_stage_val(1) = 'stage_steady.txt'
/
&list_bound_inflow
  fn_inflow_cell(1) = 'cells_main.txt'
  fn_inflow_val(1) = 'q_main_steady.txt'
  inflow_dist(1) = 2
  fn_inflow_cell(2) = 'cells_trib.txt'
  fn_inflow_val(2) = 'q_trib_steady.txt'
  inflow_dist(2) = 2
/

&list_record
  flxytype = 0
  flxy(:,1) = {fl1}            ! 支川の口の近く(流量が 100 m3/s で一定になったことの確認)
/
"""

GEO_FINE = """
&list_geoinfo
  nx = 300
  ny = 370
  dx = 20.0
  dy = 20.0
  f_ztype = 1
  fn_z = 'z.txt'
  f_rntype = 1
  fn_rn = 'rn.txt'
  f_masktype = 1
  fn_mask = 'mask.txt'
/
"""

GEO_COARSE = """
&list_geoinfo
  nx = 60
  ny = 74
  dx = 100.0
  dy = 100.0
  f_ztype = 1
  fn_z = 'z.txt'
  f_rntype = 1
  fn_rn = 'rn.txt'
  f_masktype = 1
  fn_mask = 'mask.txt'
  fn_rw = 'rw.txt'
/

&list_channel
  fn_bank = 'bank.txt'
  f_bank_datum = 2
  fn_width = 'width.txt'
/
"""


def main():
    for fn, case, title, desc, zfile, qm, qt, stage, extra_fn, extra in CASES:
        zc = ""
        txt = HEAD.format(title=title, desc=desc) + SYS.format(
            extra_fn=extra_fn, case=case, zfile=zfile, zcomment=zc, stage=stage, qm=qm, qt=qt) + extra + REC
        with open(os.path.join(HERE, fn), "w") as f:
            f.write(txt)
        print("wrote", fn)
    for fn, rname, title, base, dt, chan_fn, ddir, geo, fl1 in (
            ("param_steady.txt", "steady", "本編の格子 Δx = 20 m", "本編", "1.0", "", "data", GEO_FINE, "128, 305, 133, 305"),
            ("param_coarse_steady.txt", "coarse_steady", "粗い格子 Δx = 100 m。河道マスクは補足 1 の「直したもの」",
             "粗い格子の補足 1", "2.0", "  fn_channel = '-'\n", "data_coarse_fixed", GEO_COARSE, "26, 63, 27, 63")):
        with open(os.path.join(HERE, fn), "w") as f:
            f.write(STEADY.format(title=title, base=base, dt=dt, chan_fn=chan_fn, ddir=ddir, rname=rname, geo=geo, fl1=fl1))
        print("wrote", fn)
    for case, title, desc, qm, qt, stage in COARSE_CASES:
        for method, mtitle, mdesc in COARSE_METHODS:
            fn = f"param_coarse_{case}_{method}.txt"
            with open(os.path.join(HERE, fn), "w") as f:
                f.write(COARSE.format(title=title, desc=desc, case=case, qm=qm, qt=qt, stage=stage,
                                      method=method, mtitle=mtitle, mdesc=mdesc, width_line=WIDTH_LINE[method]))
            print("wrote", fn)


if __name__ == "__main__":
    main()
