#!/usr/bin/env python3
"""test/stg の入力と設定ファイルの生成(Run.sh・Run_MPI.sh が呼ぶ)。

STG 格子(f_gridsystem = 1。旧互換の比較用で凍結中。developer.md §7)が動き続けていることの検定。

  stg:     マスクなしの閉じた矩形の斜面(東へ下る勾配 0.02)に一様な雨を降らせ、力学波で流す。
           STG は外周の 1 列(i = 1, nx・j = 1, ny)を計算せず、そこには雨も入らない。計算する
           セル(i = 2..nx-1, j = 2..ny-1)の水量は、連続式が保存形なので、そこに降った雨の量に
           一致する。外周は高い壁(標高 WALL)にして、計算するセルから外周へ水が出ないようにする。
  stgmask: 同じ設定に領域マスク(f_masktype = 1。北東の隅を外す)を与える。STG は領域マスクに
           対応しないので、初期化で明示的に止まることを確かめる(Run.sh が終了コードと文言を見る)。

  python3 make_init.py        d_stg/ の地形・マスクと p_stg.txt・p_stgmask.txt を書く
定数は Check_stg.py と対。
"""
import os

NX, NY, DX = 40, 24, 10.0       # 格子(m)
S0 = 0.02                       # 斜面の勾配(東へ下る)
WALL = 20.0                     # 外周の壁の標高(m)
P = 60.0                        # 雨の強さ(mm/h。全期間一定)
TT = 1800                       # 計算時間(s)

PARAM = """&list_sysparam
  f_gridsystem = 1           ! 格子システム(1: STG)
  f_govequation = 0          ! 力学波
  dt = 0.5                   ! 時間刻み(s)
  t0 = 0
  tt = {tt}
  dt_disp = 600
  dt_file = {tt}
  fn_geoinfo = '-'
  fn_initial = '-'
  fn_boundary = '-'
  fn_precip = '-'
  dir_data = 'd_stg'
  dir_result = 'result_{case}'
  f_output_mode = 3          ! テキスト + bil(Check_stg.py は float32 の bil で水量を数える)
  f_out_h = 1                ! 水深 H
/
&list_initial
  f_htype = 0
  f_uvtype = 0
  h0 = 0.0
  u0 = 0
  v0 = 0
/
&list_geoinfo
  lx = {lx}
  ly = {ly}
  nx = {nx}
  ny = {ny}
  f_ztype = 1
  fn_z = 'z.txt'
  f_rntype = 0
  rn0 = 0.03
{mask}/
&list_precip
  prtype = 1
  prval(:,1) = 0, {p}
  prval(:,2) = {tt}, {p}
/
"""


def write_matrix(fn, rows, fmt):
    with open(fn, "w") as f:
        for r in rows:
            f.write(" ".join(fmt % v for v in r) + "\n")


def main():
    os.makedirs("d_stg", exist_ok=True)
    z = []
    mask = []
    for j in range(1, NY + 1):
        zr, mr = [], []
        for i in range(1, NX + 1):
            if i in (1, NX) or j in (1, NY):
                zr.append(WALL)
            else:
                zr.append(S0 * DX * (NX - i))
            mr.append(0 if (i > NX - 5 and j > NY - 5) else 1)
        z.append(zr)
        mask.append(mr)
    write_matrix("d_stg/z.txt", z, "%.4f")
    write_matrix("d_stg/mask.txt", mask, "%d")
    common = dict(tt=TT, lx=NX * DX, ly=NY * DX, nx=NX, ny=NY, p=P)
    with open("p_stg.txt", "w") as f:
        f.write(PARAM.format(case="stg", mask="  f_masktype = 0\n", **common))
    with open("p_stgmask.txt", "w") as f:
        f.write(PARAM.format(case="stgmask", mask="  f_masktype = 1\n  fn_mask = 'mask.txt'\n", **common))


if __name__ == "__main__":
    main()
