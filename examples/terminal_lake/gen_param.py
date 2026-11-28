#!/usr/bin/env python3
"""terminal_lake の設定ファイル(param_<ケース>.txt)を作る。置いてある設定ファイルと同じものを作り直す
だけで、計算は置いてあるファイルで行う(値を変えた比較を作るときの元にする)。

実時間の量(流入・蒸発・塩の負荷・混合係数・溶解の係数・期間)を決め、圧縮率 M を掛けて書き出す
(時間の圧縮。docs/users_guide/time.md)。
"""
import math

YEAR = 365.25 * 86400.0
K = math.pi * 5000.0 ** 2 / 10.0        # 湖面積 A = K·η (m2)
E = 1.0 / YEAR                          # 蒸発 1 m/年 (m/s)
ETA0 = 8.0                              # 初期水位 (m)
Q0 = E * K * ETA0                       # 初期水位で蒸発と釣り合う流入 (m3/s)
DT = 5.0
YEARS, YBACK = 25.0, 12.0               # 計算する年数、流入を元に戻す年
DT_FILE_Y = 1.0                         # 分布出力の間隔(年)


def write(tag, title, lines, m=1000.0, c0=10000.0, cin=500.0, extra="", years=YEARS, yback=YBACK, dt=DT):
    q1 = 0.05 * Q0                      # 絞った後の流入
    step = lambda sec: round(sec / DT) * DT
    tfile = step(DT_FILE_Y * YEAR / m)
    tt = tfile * years + 10 * DT
    tb = tfile * yback                  # 流入を戻す時刻(yback 年目の分布出力の時刻。その直後に戻す)
    if yback > 0.0:
        src = (f"  src_val(:,1,1) = 0.0, {q1*m:.6e}          ! (min, m3/s) = 0.05 × Q0 × M\n"
               f"  src_val(:,2,1) = {tb/60:.4f}, {q1*m:.6e}\n"
               f"  src_val(:,3,1) = {(tb+DT)/60:.4f}, {Q0*m:.6e}   ! {yback:g} 年目の出力の直後に、流入を元(Q0 × M)に戻す\n"
               f"  src_val(:,4,1) = 9.9e9, {Q0*m:.6e}\n")
        load = (f"  wq_pt_series(:,1,1) = 0.0, {q1*cin*m:.6e}    ! (経過日, g/s) = 流入 × 流入水の濃度\n"
                f"  wq_pt_series(:,2,1) = {tb/86400:.8f}, {q1*cin*m:.6e}\n"
                f"  wq_pt_series(:,3,1) = {(tb+DT)/86400:.8f}, {Q0*cin*m:.6e}\n"
                f"  wq_pt_series(:,4,1) = 9.9e9, {Q0*cin*m:.6e}\n")
    else:
        src = (f"  src_val(:,1,1) = 0.0, {q1*m:.6e}          ! (min, m3/s) = 0.05 × Q0 × M\n"
               f"  src_val(:,2,1) = 9.9e9, {q1*m:.6e}\n")
        load = f"  wq_pt_load(1) = {q1*cin*m:.6e}          ! (g/s) = 流入 × 流入水の濃度\n"
    head = "\n".join("!   " + l if l else "!" for l in lines)
    txt = f"""!======================================================================
! terminal_lake / {tag}: {title}
{head}
!   時間の圧縮(docs/users_guide/time.md): 圧縮率 M = {m:g}。蒸発・流入・塩の負荷・混合係数・溶解の
!   係数を M 倍にし、{years:g} 年を {years:g} 年 / M で計算する。結果の時刻は M 倍して読む。
!======================================================================
&list_sysparam
  dt = {dt:g}                  ! 時間刻み (s)
  tt = {tt:.1f}            ! 計算終了時刻 (s) = {years:g} 年 / M
  dt_disp = {tfile/4:.1f}          ! Log.txt の間隔(実時間の 0.25 年ごと)
  dt_file = {tfile:.1f}         ! 分布出力の間隔(実時間の 1 年ごと)
  dt_recrd = {tfile/20:.1f}         ! wq.csv・evap.csv・プローブの間隔(実時間の 0.05 年ごと)
  fn_geoinfo = '-'
  fn_initial = '-'
  fn_boundary = '-'
  fn_evap = '-'
  fn_wq = '-'
  fn_record = '-'
  dir_data = 'data_lake'
  dir_result = 'result_{tag}'
  f_output_mode = 2         ! 分布は bil
/

&list_geoinfo
  nx = 61
  ny = 61
  dx = 200.0
  dy = 200.0
  f_ztype = 1
  fn_z = 'z.txt'            ! 放物面のすり鉢(gen_data.py)
  rn0 = 0.03
/

&list_initial
  f_htype = 2               ! 水位の固定値
  e0 = {ETA0:g}                  ! 初期水位 (m)。流入 Q0 と蒸発が釣り合う水位
/

&list_bound_source
  fn_src_cell(1) = 'inflow_cells.txt'   ! 流入(川の水)を湖の中心の 5 × 5 セル(1 km 四方)へ直接入れる
{src}/

&list_evap
  f_evmodel = 1             ! 一定(年平均値を直接与える)
  evap0 = {1000.0/365.25*m:.6e}    ! 蒸発 (mm/day) = 1 m/年 × M
/

&list_wq
  wq_c0 = {c0:g}             ! 湖の初期の濃度 (mg/L)
  fn_wq_pt_cell(1) = 'inflow_cells.txt'   ! 流入水の塩(流入と同じセルへの点源)
{load}{extra}/

&list_record
  pbxytype = 0
  pbxy(:,1) = 31, 31        ! 湖の中心(流入を入れる範囲の中)
  pbxy(:,2) = 31, 38        ! 中心から 1.4 km
/
"""
    open(f"param_{tag}.txt", "w").write(txt)
    print(f"param_{tag}.txt  M = {m:g}  tt = {tt:.0f} s  steps = {int(tt/DT)}")


COMMON = ["放物面のすり鉢の湖(半径 5 km で深さ 10 m。gen_data.py)。初期水位 8 m、塩分 10 g/L。蒸発 1 m/年。",
          f"流入を、蒸発と釣り合う Q0 = {Q0:.3f} m3/s の 5 % に絞って 12 年(湖はほぼ干上がる)、その後 Q0 に戻して",
          "13 年(水位が戻る)。流入水の塩分は 0.5 g/L。"]
MIX = "  wq_diff = 1000.0          ! 水平の混合係数 (m2/s) = 1 m2/s × M\n"
write("nomix", "湖の縮小と再上昇(混合なし・溶解度の上限なし)",
      COMMON + ["水平の混合も溶解度も与えない(移流と蒸発による濃縮だけ)。流入口のまわりが淡水、縁が極端に濃くなり、",
                "塩は干上がった湖底の水柱の柱状量として残る。水が戻ると全量が瞬時に溶ける。"])
write("mix", "湖の縮小と再上昇(水平の混合あり)",
      COMMON + ["水平の混合係数 1 m2/s(風などによる湖の中の混合の代わり)を与える。湖の塩分はほぼ一様に上がるが、",
                "溶解度の上限がないので、干上がる直前の濃度は現実の飽和を超える。"], extra=MIX)
write("salt", "湖の縮小と再上昇(混合 + 溶解度。塩化ナトリウムに近い物質)",
      COMMON + ["水平の混合に加えて、溶解度 360 g/L を与える。飽和を超えた分と干上がったセルの塩は析出物(分布 B)に",
                "なり、水が戻ると、浸かった所から飽和まで瞬時に溶ける。"],
      extra=MIX + "  wq_csat = 3.6e5           ! 溶解度 (mg/L) = 360 g/L(濃度なので圧縮率を掛けない)\n")
write("slow", "湖の縮小と再上昇(混合 + 溶解度 + 溶けにくい析出物)",
      COMMON + ["salt と同じ設定に、析出物の溶解の物質移動係数 8.64e-4 m/day(1e-8 m/s)を与える。水深 1 m の水が",
                "飽和に近づく時定数が約 3 年なので、水が戻っても析出物は数年かけて溶ける。"],
      extra=MIX + "  wq_csat = 3.6e5           ! 溶解度 (mg/L) = 360 g/L\n"
                  "  wq_kdis = 0.864           ! 溶解の物質移動係数 (m/day) = 8.64e-4 m/day × M\n")
write("gypsum", "湖の縮小と再上昇(混合 + 溶解度。石膏に近い物質)",
      ["放物面のすり鉢の湖(半径 5 km で深さ 10 m。gen_data.py)。初期水位 8 m。蒸発 1 m/年。",
       f"流入を、蒸発と釣り合う Q0 = {Q0:.3f} m3/s の 5 % に絞って 12 年、その後 Q0 に戻して 13 年。",
       "溶けにくい物質の例として、初期の濃度 1.5 g/L、流入水 0.1 g/L、溶解度 2.4 g/L を与える。縮み始めて",
       "数年で飽和して湖底に析出し、水が戻っても、水の濃度は飽和の 2.4 g/L で頭打ちになる。"],
      c0=1500.0, cin=100.0,
      extra=MIX + "  wq_csat = 2.4e3           ! 溶解度 (mg/L) = 2.4 g/L\n")
write("mix_m10000", "圧縮率の確かめ(mix と同じ湖を M = 10000 で、縮小の 12 年だけ)",
      ["mix と同じ設定の最初の 12 年(流入を 5 % に絞った期間)を、圧縮率 10000 で計算する。湖の体積を、",
       "湖面を水平とみなした水収支の解と比べて、圧縮率による誤差を見る(plot_results.py)。混合係数が",
       "10 倍になるので、その安定条件(約 0.35 dx²/dt)に合わせて時間刻みを 1 s にする。"],
      m=10000.0, extra="  wq_diff = 10000.0         ! 水平の混合係数 (m2/s) = 1 m2/s × M\n", years=12.0, yback=0.0, dt=1.0)
