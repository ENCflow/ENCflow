#!/usr/bin/env python3
"""1 セル幅 / 2 セル幅の水路でのダム破壊(developer.md §68.15)の地形・
マスク・パラメータを生成する。

  python3 Make_incised.py
    → z_ch1.txt, z_ch2.txt      掘込水路(堤内地 z = 20 m、水路 z = 0)
      z_ch1z12.txt, z_ch2z12.txt 同(堤内地 z = 12 m)
      mask_m1.txt, mask_m2.txt   マスク壁(堤内地を無効セルに)
      param_{ch1,ch2,ch1z12,ch2z12,m1,m2}_s{1,3}_d{0,2}[_c1].txt
        s = f_advection_scheme、d = f_opening_dynamic(0 / 2)、_c1 = f_dry_head_cap=1
  実行:  ./encflow param_m1_s3_d2.txt
  検証:  RESDIR=result_m1_s3_d2 PARAM=param_m1_s3_d2.txt python3 Check_stoker.py
格子は param.txt と同じ dx = 2 m、nx = 500。ny は 1 セル水路で 5(水路は
第 3 行)、2 セル水路で 6(第 3・4 行)。初期条件は dambreak_step(水位
基準なので堤内地は乾燥で始まる)。
"""
import numpy as np
nx = 500
cases = (('ch1', 5, [2], 'z', 20.0), ('ch2', 6, [2, 3], 'z', 20.0),
         ('ch1z12', 5, [2], 'z', 12.0), ('ch2z12', 6, [2, 3], 'z', 12.0),
         ('m1', 5, [2], 'mask', None), ('m2', 6, [2, 3], 'mask', None))
base = open('param.txt').read()
for name, ny, ch, kind, zl in cases:
    if kind == 'mask':
        m = np.zeros((ny, nx))
        for j in ch:
            m[j, :] = 1
        np.savetxt(f'mask_{name}.txt', m, fmt='%d')
    else:
        z = np.full((ny, nx), zl)
        for j in ch:
            z[j, :] = 0.0
        np.savetxt(f'z_{name}.txt', z, fmt='%.1f')
    for s in (1, 3):
        for d in (0, 2):
            t = base.replace("dir_result = 'result'", f"dir_result = 'result_{name}_s{s}_d{d}'")
            t = t.replace("  f_hcap_upwind = 1 ", f"  f_advection_scheme = {s}\n  f_opening_dynamic = {d}\n  f_hcap_upwind = 1 ")
            t = t.replace("  ly = 400.0\n", f"  ly = {ny * 2:.1f}\n").replace("  ny = 200\n", f"  ny = {ny}\n")
            if kind == 'mask':
                t = t.replace("  f_rntype = 0    ! 粗度係数タイプ (0:固定値)\n",
                              f"  f_rntype = 0    ! 粗度係数タイプ (0:固定値)\n  f_masktype = 1\n  fn_mask = 'mask_{name}.txt'   ! 水路行のみ有効(堤内地は無効セル=壁)\n")
            else:
                t = t.replace("  f_ztype = 0     ! 地盤高タイプ (0:固定値)\n",
                              f"  f_ztype = 1\n  fn_z = 'z_{name}.txt'   ! 掘込水路: 堤内地 z={zl:g} m\n")
            assert f'f_opening_dynamic = {d}' in t and f'ny = {ny}' in t
            open(f'param_{name}_s{s}_d{d}.txt', 'w').write(t)
            # 同じケースで f_dry_head_cap = 1(§68.16)
            tc = t.replace(f"dir_result = 'result_{name}_s{s}_d{d}'", f"dir_result = 'result_{name}_s{s}_d{d}_c1'")
            tc = tc.replace("  f_opening_dynamic = ", "  f_dry_head_cap = 1\n  f_opening_dynamic = ", 1)
            open(f'param_{name}_s{s}_d{d}_c1.txt', 'w').write(tc)
print('generated', len(cases) * 8, 'parameter files')
