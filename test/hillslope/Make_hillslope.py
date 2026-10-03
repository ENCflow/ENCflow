#!/usr/bin/env python3
"""斜面流の移流スキーム比較ケース(developer.md §68.18)。

  python3 Make_hillslope.py plane   → z_p05.txt, z_p20.txt, param_p{05,20}_s{1,3}.txt
      一様平面斜面(dx = dy = 100 m、2 km × 2 km、勾配 0.05 / 0.20、n = 0.15、
      降雨 200 mm/h)。運動学的波の解析解(q = α(Pt)^{5/3}、平衡 q_e = P·x)と比べる。
  python3 Make_hillslope.py stairplane → z_sp05.txt, param_sp05_{noadv,s1,s3}.txt(plane の後に実行)
      横断方向一様な階段斜面(2 セルごとに 10 m の段差、平均勾配 0.05、n = 0.15、
      降雨 200 mm/h)。段差での散逸が斜面流(薄い・粗い・低フルード数)では
      効かないことの確認(developer.md §68.20)。
  python3 Make_hillslope.py vcat    → z_{c100,f10}.txt, rn_{c100,f10}.txt, param_{c100,f10}_s{1,3}.txt
      V 字集水域(両側 800 m の斜面が勾配 0.05 で中央 100 m の河道帯に集まり、
      縦断勾配 0.02。斜面 n = 0.015、河道 n = 0.15、降雨 10.8 mm/h × 90 分)。
      dx = 100 m と 10 m の格子収束比較。
  実行:  ./encflow param_p05_s1.txt など。出口手前の測線 1 本を記録する。
2026-10-03 の結果: いずれもスキーム 1・3 が 3 桁まで一致(差は現れない)。
"""
import sys
import numpy as np
kind = sys.argv[1] if len(sys.argv) > 1 else "plane"
BASE = """&list_sysparam
  f_gridsystem = 0
  f_govequation = 0
  dt = {dt}
  t0 = 0
  tt = {tt}
  dt_recrd = 60
  fn_record = '-'
  dt_disp = 1800
  dt_file = {tt}
  fn_geoinfo = '-'
  fn_initial = '-'
  fn_enc = '-'
  fn_boundary = '-'
  fn_precip = '-'
  dir_result = 'result_{name}_s{s}'
  f_disp_debug = 1
  f_disp_qq = 1
  f_out_h = 1
  f_out_hmax = 0
/
&list_enc
  f_advection_scheme = {s}
  f_hcap_upwind = 1
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
  fn_z = 'z_{name}.txt'
{rn}/
&list_precip
  prtype = 1
{rain}/
&list_bound_edge
  f_bc_e = 1
/
&list_record
  flxytype = 0
  flxy(:,1) = {ix}, {ny}, {ix}, 1
/
"""
if kind == "plane":
    nx, ny, dx = 20, 20, 100.0
    for name, S0 in (("p05", 0.05), ("p20", 0.20)):
        z = np.tile(100.0 - S0 * dx * np.arange(nx), (ny, 1))
        np.savetxt(f"z_{name}.txt", z, fmt="%.3f")
        for s in (1, 3):
            open(f"param_{name}_s{s}.txt", "w").write(BASE.format(
                dt=5.0, tt=14400, name=name, s=s, lx=2000.0, ly=2000.0, nx=nx, ny=ny,
                rn="  f_rntype = 0\n  rn0 = 0.15\n",
                rain="  prval(:,1) = 0, 200.0\n  prval(:,2) = 600, 200.0\n", ix=nx - 1))
    print("plane: 4 parameter files")
elif kind == "vcat":
    for name, dx in (("c100", 100.0), ("f10", 10.0)):
        nx, ny = int(1000 / dx), int(1700 / dx)
        xs = (np.arange(nx) + 0.5) * dx; ys = (np.arange(ny) + 0.5) * dx
        X, Y = np.meshgrid(xs, ys)
        dist = np.maximum(np.abs(Y - 850.0) - 50.0, 0.0)
        z = 100.0 - 0.02 * X + 0.05 * dist
        rn = np.where(dist > 0, 0.015, 0.15)
        np.savetxt(f"z_{name}.txt", z, fmt="%.4f"); np.savetxt(f"rn_{name}.txt", rn, fmt="%.3f")
        for s in (1, 3):
            open(f"param_{name}_s{s}.txt", "w").write(BASE.format(
                dt=2.0 if dx == 100 else 0.25, tt=10800, name=name, s=s, lx=1000.0, ly=1700.0, nx=nx, ny=ny,
                rn=f"  f_rntype = 1\n  fn_rn = 'rn_{name}.txt'\n",
                rain="  prval(:,1) = 0, 10.8\n  prval(:,2) = 90, 10.8\n  prval(:,3) = 90.0001, 0.0\n  prval(:,4) = 600, 0.0\n", ix=nx - 1))
    print("vcat: 4 parameter files")

if kind == "stairplane":
    nx = ny = 20
    z = np.zeros((ny, nx))
    for i in range(nx):
        z[:, i] = 100.0 - 10.0 * (i // 2)     # 2 セルごとに 10 m の段差(平均勾配 0.05)
    np.savetxt("z_sp05.txt", z, fmt="%.3f")
    base = open("param_p05_s1.txt").read()
    for tag, rep in (("noadv", [("f_govequation = 0", "f_govequation = 1")]), ("s1", []),
                     ("s3", [("f_advection_scheme = 1", "f_advection_scheme = 3")])):
        t = base.replace("result_p05_s1", f"result_sp05_{tag}").replace("z_p05.txt", "z_sp05.txt")
        for a, b in rep:
            t = t.replace(a, b)
        open(f"param_sp05_{tag}.txt", "w").write(t)
    print("stairplane: z_sp05.txt, param_sp05_{noadv,s1,s3}.txt")
