#!/usr/bin/env python3
"""横流入つき 1 セル水路(developer.md §68.17)の地形・河道マスク・パラメータを生成する。

  python3 Make_lateral.py
    → z_lat1.txt, rw_lat1.txt, mask_lat1.txt   片側横流入(ny = 13。行 1-2 無効、
                                                 行 3 河道、行 4-13 斜面帯)
      z_lat2.txt, rw_lat2.txt                  両側横流入(ny = 21。行 11 河道、
                                                 行 1-10 / 12-21 斜面帯)
      param_lat{1,2}_s{1,3}.txt                s = f_advection_scheme
  実行:  ./encflow param_lat2_s3.txt
  検証:  python3 Check_lateral.py lat2 _s1 _s3
水路: dx = dy = 10 m、400 セル、河床勾配 S0 = 0.02(超臨界。下流端境界に
依存しない)、n = 0.03、上流端に Q0 = 40 m³/s。斜面帯は河床 + 5 m(河道側の
行)から外側へ 2% で上がり、一様降雨 P = 1440 mm/h を受けて河道へ側方から
流れ込む(流下方向の運動量を持たない横流入)。河道セルへの直接降雨は
総流入の 1/11(片側)・1/21(両側)。河道の斜め開口は +5 m の段差で塞がれる
(f_opening_dynamic=1 で s = 1 → エッジ流速 = セル流速)。
"""
import numpy as np
DX, S0, Z0, NX = 10.0, 0.02, 100.0, 400
STEP, SLOPE = 5.0, 0.02
base = """&list_sysparam
  f_gridsystem = 0
  f_govequation = 0
  dt = 0.25
  t0 = 0
  tt = 3600
  dt_disp = 300
  dt_file = 1800
  fn_geoinfo = '-'
  fn_initial = '-'
  fn_enc = '-'
  fn_boundary = '-'
  fn_precip = '-'
  dir_result = 'result_{name}_s{s}'
  f_disp_debug = 1
  f_disp_qq = 1
  f_out_h = 1
  f_out_u = 1
  f_out_v = 1
  f_out_m = 1
  f_out_n = 1
  f_out_hmax = 0
/
&list_enc
  f_advection_scheme = {s}
  f_hcap_upwind = 1
  f_opening_dynamic = 1
  f_dry_head_cap = 1
/
&list_initial
  f_htype = 0
  f_uvtype = 0
  h0 = 0.0
  u0 = 0
  v0 = 0
/
&list_geoinfo
  lx = 4000.0
  ly = {ly}
  nx = 400
  ny = {ny}
  f_ztype = 1
  fn_z = 'z_{name}.txt'
  fn_rw = 'rw_{name}.txt'
  rn0_rw = 0.03
  f_rntype = 0
  rn0 = 0.03
{mask}/
&list_precip
  prtype = 1
  prval(:,1) = 0, 1440.0
  prval(:,2) = 600, 1440.0
/
&list_bound_edge
  f_bc_e = 1
/
&list_bound_inflow
  inflow_cell(:,1,1) = 1, {jc}
  inflow_val(:,1,1) = 0, 40.0
  inflow_val(:,2,1) = 600, 40.0
  inflow_dist(1) = 0
/
"""
for name, ny, jc, masked in (('lat1', 13, 3, [1, 2]), ('lat2', 21, 11, [])):
    z = np.zeros((ny, NX)); rw = np.zeros((ny, NX), dtype=int); mk = np.ones((ny, NX), dtype=int)
    for i in range(NX):
        bed = Z0 - S0 * DX * i
        for j in range(1, ny + 1):
            d = abs(j - jc)
            z[j-1, i] = bed if d == 0 else bed + STEP + SLOPE * DX * (d - 1)
    rw[jc-1, :] = 1
    for j in masked: mk[j-1, :] = 0
    np.savetxt(f'z_{name}.txt', z, fmt='%.4f'); np.savetxt(f'rw_{name}.txt', rw, fmt='%d')
    mask = ''
    if masked:
        np.savetxt(f'mask_{name}.txt', mk, fmt='%d'); mask = f"  f_masktype = 1\n  fn_mask = 'mask_{name}.txt'\n"
    for s in (1, 3):
        open(f'param_{name}_s{s}.txt', 'w').write(base.format(name=name, s=s, ly=ny*DX, ny=ny, jc=jc, mask=mask))
print('ok')
