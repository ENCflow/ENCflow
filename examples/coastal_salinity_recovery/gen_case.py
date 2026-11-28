#!/usr/bin/env python3
"""coastal_salinity_recovery の入力(data_coast/)と設定ファイル(param_*.txt)を作る。
置いてある設定ファイルと同じものを作り直すだけで、計算は置いてあるファイルで行う
(値を変えた比較を作るときの元にする)。

計算は 3 段を再開(f_state_restore = 2)でつなぐ。
  1. spinup      津波の前の地下水(雨の涵養・井戸の揚水・海への流出の釣り合い)を作る。時間の圧縮
  2. flood_*     津波(潮位の時系列)→ 低地の浸水 → 浸透と排水。実時間(8 日)
  3. rec_*       その後の 8 年の地下の塩水の変化。時間の圧縮
時間の圧縮(docs/users_guide/time.md)の段は、雨・浸透能・側方の透水係数・井戸と排水機場の流量を
M 倍にし、期間を 1/M にする。結果の時刻は M 倍して読む。
"""
import os

# ---------------- 幾何 ----------------
NX, NY, DX = 40, 10, 25.0
ZB = -8.0                                   # 帯水層の底の標高 (m)
D = "data_coast"
YEAR = 365.25 * 86400.0


def ground(i):
    """列 i(1 始まり)の地盤高 (m)。列 1〜2 は海(海域マスク)"""
    if i <= 2:
        return 0.0
    if i == 3:
        return 1.0                          # 浜
    if i <= 5:
        return 3.0                          # 堤防(天端 3 m)
    if i == 6:
        return 1.0                          # 排水路(低地より 1 m 深い)
    if i <= 32:
        return 2.0                          # 低地
    return 2.0 + 0.25 * (i - 32)            # 台地へ上がる


def write_map(name, fn, fmt="%.3f"):
    with open(os.path.join(D, name), "w") as f:
        for j in range(1, NY + 1):
            f.write(" ".join(fmt % fn(i, j) for i in range(1, NX + 1)) + "\n")


def write_cells(name, cells):
    with open(os.path.join(D, name), "w") as f:
        for i, j in cells:
            f.write("%d %d\n" % (i, j))


def gen_data():
    os.makedirs(D, exist_ok=True)
    write_map("z.txt", lambda i, j: ground(i))
    write_map("sd.txt", lambda i, j: ground(i) - ZB)                 # 土層厚 = 地盤高 − 帯水層の底
    write_map("sw.txt", lambda i, j: 1 if i <= 2 else 0, "%d")       # 海域マスク
    write_cells("canal.txt", [(6, j) for j in range(1, NY + 1)])     # 排水機場の取水セル = 排水路
    write_cells("wells.txt", [(18, 5), (18, 6), (26, 5), (26, 6)])   # 井戸(低地の 2 か所)


# ---------------- 実時間の量 ----------------
RAIN = 1200.0 / (365.25 * 24.0)             # 雨(涵養)1200 mm/年 → mm/h
KSV = 7.2                                   # 浸透能 (mm/h) = 2e-6 m/s
KSH = 3600.0                                # 側方の透水係数 (mm/h) = 1e-3 m/s
QWELL = 0.004                               # 井戸の揚水(4 セルの合計。m3/s)= 涵養の約 4 割
QFAST, QSLOW = 4.0, 0.4                     # 排水機場の能力 (m3/s)
M = 100.0                                   # 回復の段の圧縮率
YSPIN, YREC, YSTOP = 20.0, 8.0, 2.0         # スピンアップ・回復の年数、井戸を止める年数

HEAD = "!======================================================================\n"


def common(tag, dt, tt, dt_disp, dt_file, dt_recrd, restore, save_dir):
    rs = f"  f_state_restore = {restore}       ! 保存状態を新しい時間軸の初期条件にする\n" if restore else ""
    return f"""&list_sysparam
  dt = {dt:g}                 ! 時間刻み (s)
  tt = {tt:.1f}
  dt_disp = {dt_disp:.1f}
  dt_file = {dt_file:.1f}
  dt_recrd = {dt_recrd:.1f}
  fn_geoinfo = '-'
  fn_initial = '-'
  fn_tide = '-'
  fn_precip = '-'
  fn_gwflow = '-'
  fn_salt = '-'
  fn_structure = '-'
  dir_data = 'data_coast'
  dir_result = 'result_{tag}'
  dir_save = '{save_dir}'
  f_state_save = 1          ! 終了時の状態を保存(次の段の初期条件)
{rs}  f_output_mode = 2         ! 分布は bil
  f_out_hg = 1              ! 地下の貯留 Hg と地下の塩水 Hgs の分布を出力
/

&list_geoinfo
  nx = {NX}
  ny = {NY}
  dx = {DX:g}
  dy = {DX:g}
  f_ztype = 1
  fn_z = 'z.txt'            ! 海・浜・堤防(天端 3 m)・排水路・低地(2 m)・台地
  rn0 = 0.03
  f_masktype = 2            ! 領域マスクを海域マスクから作る
  fn_sw = 'sw.txt'          ! 海域マスク(西端の 2 列)
  f_sdtype = 1
  fn_sd = 'sd.txt'          ! 土層厚 = 地盤高 + 8 m(帯水層の底 −8 m)
  sy0 = 0.2                 ! 有効間隙率
/

&list_initial
  f_htype = 0
  h0 = 0.0
/
"""


def tide(series):
    lines = "".join(f"  tival(1:2,{k}) = {t:g}, {e:g}\n" for k, (t, e) in enumerate(series, 1))
    return f"""
&list_tide
  titype = 2                ! 一様な潮位の時系列
  hsea0 = 2.0               ! 海セルの見かけの水柱の厚さ (m)
  dt_tiupdate = 0.1         ! 潮位の更新間隔 (min)
{lines}/
"""


def physics(m, wells, qpump, sat0=None):
    s0 = f"  gw_sat0 = {sat0:g}             ! 初期の飽和度(スピンアップの出発点)\n" if sat0 is not None else ""
    wl = "".join(f"  gwp_val(1:2,{k},1) = {t:.4f}, {q * m:.6e}\n" for k, (t, q) in enumerate(wells, 1))
    return f"""
&list_precip
  prtype = 1                ! 一様な時系列
  dt_prupdate = 60
  prval(:,1) = 0, {RAIN * m:.6f}      ! (min, mm/h) = 1200 mm/年{' × M' if m > 1 else ''}
  prval(:,2) = 9.9e9, {RAIN * m:.6f}
/

&list_gwflow
  f_gwvertical = 2          ! Green-Ampt の浸透
  f_gwlateral = 1           ! 地下水の側方流
  f_gwpump = 1              ! 井戸揚水
{s0}/

&list_gwflow_greenampt
  gw_ksv_mmh = {KSV * m:g}       ! 浸透能 (mm/h) = 2e-6 m/s{' × M' if m > 1 else ''}
  gw_psif = 0.0
/

&list_gwflow_lateral
  gw_ksh_mmh = {KSH * m:g}    ! 側方の透水係数 (mm/h) = 1e-3 m/s{' × M' if m > 1 else ''}
/

&list_gwflow_pump
  fn_gwp_cell(1) = 'wells.txt'   ! 井戸(低地の 4 セル)
{wl}/

&list_salt
  f_salt_surf = 1           ! 地表の塩水層
  f_salt_gw = 1             ! 地下の塩水 zone(浸透・湧出の淡塩配分 f_salt_exch は既定の 1)
  f_salt_struct = 1         ! 排水機場は底層の塩水から先に汲む
/

&list_struct_pump
  fn_pump_in_cell(1) = 'canal.txt'   ! 排水機場: 排水路の 10 セルから汲み、海へ出す(吐口なし = 域外)
  f_pump_ref(1) = 1                  ! 基準 = 排水路の水深
  pump_rule(:,1,1) = 0.10, 0.0       ! (水深 m, 流量 m3/s)。排水路の水深が 0.1 m になるまで汲む
  pump_rule(:,2,1) = 0.30, {qpump * m:g}
/
"""


def write(tag, title, lines, body):
    head = "".join("!   " + l + "\n" for l in lines)
    open(f"param_{tag}.txt", "w").write(HEAD + f"! coastal_salinity_recovery / {tag}: {title}\n" + head + HEAD + body)
    print("param_%s.txt" % tag)


def gen_param():
    dtc = 10.0                                              # 圧縮した段の時間刻み (s)
    yr = round(YEAR / M / (20 * dtc)) * 20 * dtc            # 圧縮した段の 1 年 (s)。出力間隔(1/4 年・1/20 年)が時間刻みの倍数になるように丸める
    calm = [(0, 0.0), (9.9e9, 0.0)]
    on = [(0.0, QWELL), (9.9e9, QWELL)]
    # 1. スピンアップ
    write("spinup", "津波の前の地下水を作る(スピンアップ。時間の圧縮 M = %g、%g 年)" % (M, YSPIN),
          ["雨の涵養 1200 mm/年、井戸の揚水、海への地下水の流出が釣り合うまで計算し、状態を save_spinup に保存する。",
           "海に接する帯水層には、海から塩水のくさびが入る。"],
          common("spinup", dtc, YSPIN * yr, yr, YSPIN * yr / 4, yr / 4, 0, "save_spinup")
          + tide(calm) + physics(M, on, QFAST, sat0=0.8))
    # 2. 津波 → 浸水 → 排水(実時間 8 日)
    surge = [(0, 0.0), (60, 0.0), (70, 4.5), (90, 4.5), (130, 0.0), (9.9e9, 0.0)]
    for tag, q, txt in (("fast", QFAST, "排水機場の能力 4 m3/s(半日で排水)"), ("slow", QSLOW, "排水機場の能力 0.4 m3/s(5 日かけて排水)")):
        write(f"flood_{tag}", f"津波による浸水と排水(実時間 8 日。{txt})",
              ["スピンアップの状態(save_flood_%s = save_spinup のコピー)から始める。1 時間後に潮位を 4.5 m まで上げて" % tag,
               "堤防(天端 3 m)を越えさせ、低地を海水で浸す。水が引いた後、堤防の内側に残った海水(水深 約 1 m)を",
               "排水機場が海へ出す。その間、海水は地面にしみ込んで帯水層へ入る。"],
              common(f"flood_{tag}", 1.0, 8 * 86400.0, 21600.0, 86400.0, 1800.0, 2, f"save_flood_{tag}")
              + tide(surge) + physics(1.0, on, q))
    # 3. 回復(時間の圧縮 8 年)
    stop = [(0.0, 0.0), (YSTOP * yr / 60.0, 0.0), ((YSTOP * yr + dtc) / 60.0, QWELL), (9.9e9, QWELL)]
    cases = (("control", "save_spinup", on, "津波なし(比較の基準)", ["スピンアップの状態(save_rec_control = save_spinup のコピー)から、津波なしで続ける。"]),
             ("fast_pump", "save_flood_fast", on, "速い排水の後。井戸は汲み続ける", ["flood_fast の終わりの状態から始める。"]),
             ("fast_stop", "save_flood_fast", stop, "速い排水の後。井戸を 2 年止めてから再開", ["flood_fast の終わりの状態から始める。井戸は最初の 2 年止める。"]),
             ("slow_pump", "save_flood_slow", on, "遅い排水の後。井戸は汲み続ける", ["flood_slow の終わりの状態から始める。"]))
    for tag, src, wells, title, lines in cases:
        write(f"rec_{tag}", f"その後の {YREC:g} 年({title}。時間の圧縮 M = {M:g})",
              lines + [f"保存状態は save_rec_{tag}({src} のコピー)。雨・浸透能・透水係数・井戸と排水機場の流量を M 倍にして、",
                       f"{YREC:g} 年を {YREC:g} 年 / M で計算する。"],
              common(f"rec_{tag}", dtc, YREC * yr, yr, yr / 4, yr / 20, 2, f"save_rec_{tag}")
              + tide(calm) + physics(M, wells, QFAST))
    # 圧縮率の確かめ: rec_fast_pump を M = 50 で(期間が 2 倍。それ以外は同じ)
    m2 = M / 2.0
    write("rec_fast_pump_m50", f"圧縮率の確かめ(rec_fast_pump と同じ {YREC:g} 年を M = {m2:g} で)",
          ["flood_fast の終わりの状態(save_rec_fast_pump_m50 = save_flood_fast のコピー)から始める。雨・浸透能・透水係数・",
           f"井戸と排水機場の流量を {m2:g} 倍にして、{YREC:g} 年を {YREC:g} 年 / {m2:g} で計算する(rec_fast_pump の 2 倍の計算時間)。"],
          common("rec_fast_pump_m50", dtc, YREC * yr * 2, yr * 2, yr / 2, yr / 10, 2, "save_rec_fast_pump_m50")
          + tide(calm) + physics(m2, on, QFAST))


if __name__ == "__main__":
    gen_data()
    gen_param()
