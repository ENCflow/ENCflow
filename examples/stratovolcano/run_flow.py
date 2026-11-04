#!/usr/bin/env python3
"""examples/stratovolcano の最後の段: 育った成層火山の地形に、温度を考慮した 1 回の溶岩流を流す。

  python3 run_flow.py            # 主ケース P の最終地形で 3 本を計算する(先に run_cycles.py P)
  オプション: --case L / P0(そのケースの最終地形を使う)

run_cycles.py の溶岩の段は等温のモデルで、粘度は時間を縮めた値、止まった形は降伏応力で決まる。
この段は、そうしてできた凹凸のある地形の上に、温度を計算する溶岩流(f_lvtemp = 1。表面からの
放射と対流で冷え、冷えると粘度と降伏応力が上がって止まり、固化温度で固まる。developer.md §51.7)
を 1 回だけ流し、流路が地形の凹凸で決まる様子と、冷えて止まる様子を見る。3 本:
  S : 山頂(最終地形の最高点のセル)の火口から 50 m3/s を 6 時間(108 万 m3)
  E : 山頂から東へ 300 m の火口から同じ
  S4: 山頂の火口から同じ体積を 4 倍の噴出率で(200 m3/s を 1.5 時間)
溶岩の値は例示用(玄武岩質安山岩くらいを想定した組で、特定の溶岩や文献の値ではない)。温度の
計算は実時間で進むので、粘度は実際の溶岩の大きさにする(等温の段のように時間を縮められない)。
1 日分を計算し、全量が固まったことを確かめる。土層(灰)は読まない(この段で見るのは流路と
冷却。固化した溶岩の下の灰の埋没は等温の段と同じ処理になる)。
検査(1 本ごと): (1) 地盤高の増えた量が噴出量と一致し(許容差は出力の地盤高の桁 = 小数 4 桁の
丸め。変化したセルあたり 0.00005 m)、溶けた溶岩が残っていない、(2) 熱の台帳の残差が噴出した
熱量の相対 1e-12 以内。
出力: result_<case>/flow_<run>/(ENCflow の結果。1 時間ごとの Hl・Tl・Z)、設定ファイル
result_<case>/param_flow_<run>.txt、台帳 result_<case>/flow.csv(plot_flow.py が読む)。
"""
import argparse
import csv
import glob
import math
import os
import re
import subprocess
import sys
import time

import numpy as np

NX = NY = 100                     # 格子数(run_cycles.py と同じ 5 km 四方)
DX = 50.0                         # 格子間隔 (m)
TT = 86400                        # 計算時間 (s)。1 日
DT = 10.0                         # 時間刻み (s)。溶岩は毎ステップ更新(冷却の後退 Euler の刻み)
DZ_FOOT = 0.05                    # 溶岩の広がりの判定厚 (m)
RUNS = [
    # (名前, 説明, 山頂からの東向きのずれ (セル), 噴出率 (m3/s), 噴出の時間 (時間))
    ("S", "山頂の火口", 0, 50.0, 6.0),
    ("E", "山頂から東へ 300 m の火口", 6, 50.0, 6.0),
    ("S4", "山頂の火口・同じ体積を 4 倍の噴出率で", 0, 200.0, 1.5),
]
# 溶岩の値(例示用。玄武岩質安山岩くらいを想定した組。users guide の溶岩流の章「温度モード」)
LAVA = dict(rho=2600.0, visc=1.0e4, tauy=1.0e3, temp0=1100.0, bvisc=0.03, btau=0.03,
            tsol=950.0, emis=0.95, hconv=70.0, cp=1150.0, tair=15.0)


def flow_param(case, name, vi, vj, q, hours, zfile, res):
    tmin = hours * 60.0
    L = LAVA
    return f"""! examples/stratovolcano 最後の段: 温度を考慮した 1 回の溶岩流 {name}(run_flow.py が作る)
&list_sysparam
  f_gridsystem = 0
  f_govequation = 0
  dt = {DT}                 ! 時間刻み (s)。溶岩は毎ステップ更新
  t0 = 0
  tt = {TT}                 ! 1 日
  dt_disp = 21600
  dt_file = 3600            ! 1 時間ごとに Hl・Tl・Z を出す
  dt_recrd = {TT}
  fn_geoinfo = '-'
  fn_initial = '-'
  fn_lavaflow = '-'
  dir_result = '{res}'
  f_check_cfl = 0
  f_out_z = 1
/
&list_initial
  f_htype = 0
  h0 = 0.0                  ! 水なし(溶岩だけの段)
/
&list_geoinfo
  lx = {NX * DX}
  ly = {NY * DX}
  nx = {NX}
  ny = {NY}
  f_ztype = 1
  fn_z = '{zfile}'          ! run_cycles.py {case} の最終地形
  f_rntype = 0
  rn0 = 0.03
/
&list_lavaflow
  lv_rho = {L['rho']}
  lv_visc = {L['visc']:.1e}           ! 基準温度(噴出温度)での粘度 (Pa s)。例示用
  lv_tauy = {L['tauy']:.1e}           ! 基準温度での降伏応力 (Pa)。例示用
  lv_cell(1:2,1,1) = {vi}, {vj}
  lv_val(1:2,1,1) = 0.0, {q}
  lv_val(1:2,2,1) = {tmin:.1f}, {q}
  lv_val(1:2,3,1) = {tmin:.1f}, 0.0     ! 重複時刻 = 階段状に停止
  f_lvtemp = 1              ! 温度を計算する(developer.md §51.7)
  lv_temp0(1) = {L['temp0']}      ! 噴出温度 (°C)
  lv_tref = {L['temp0']}          ! 基準温度 (°C)。lv_visc・lv_tauy はこの温度の値
  lv_bvisc = {L['bvisc']}          ! 粘度の温度感度 (1/K)。約 77 K 冷えると 10 倍
  lv_btau = {L['btau']}           ! 降伏応力の温度感度 (1/K)
  lv_tsol = {L['tsol']}          ! 固化温度 (°C)
  lv_emis = {L['emis']}           ! 有効放射率(表面の殻の断熱を含めた有効値)
  lv_hconv = {L['hconv']}          ! 対流の熱伝達係数 (W/m2/K)
  lv_cp = {L['cp']}            ! 比熱 (J/kg/K)
  lv_tair = {L['tair']}           ! 気温 (°C)
/
"""


def num(text, pat):
    m = re.findall(pat + r"\s+([-+0-9.Ee]+)", text)
    return float(m[-1]) if m else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", default="P", choices=["P", "L", "P0"])
    a = ap.parse_args()
    exe = os.path.abspath("encflow")
    if not os.path.exists(exe):
        sys.exit("encflow not found (run make first)")
    top = f"result_{a.case}"
    zfile = os.path.join(top, "data", "z_10.txt")
    if not os.path.exists(zfile):
        sys.exit(f"{zfile} not found (run run_cycles.py {a.case} first)")
    z0 = np.loadtxt(zfile)
    jj, ii = np.unravel_index(np.argmax(z0), z0.shape)
    si, sj = ii + 1, jj + 1                      # 山頂のセル (i, j)(1 始まり。先頭行が北端 j = 1)
    area = DX * DX
    rows = []
    t_all = time.time()
    for name, desc, di, q, hours in RUNS:
        vi, vj = si + di, sj
        res = os.path.join(top, f"flow_{name}")
        pf = os.path.join(top, f"param_flow_{name}.txt")
        with open(pf, "w") as f:
            f.write(flow_param(a.case, name, vi, vj, q, hours, zfile, res))
        t = time.time()
        r = subprocess.run([exe, pf], capture_output=True, text=True)
        tw = time.time() - t
        out = r.stdout + r.stderr
        with open(os.path.join(top, f"Screen_flow_{name}.log"), "w") as f:
            f.write(out)
        if r.returncode != 0:
            sys.exit(f"run {name} failed (see {top}/Screen_flow_{name}.log)")
        zf = np.loadtxt(os.path.join(res, "Z9998.txt"))
        hl = np.loadtxt(os.path.join(res, "Hl9998.txt"))
        dz = zf - z0
        erupted = num(out, "lavaflow: erupted")
        added = dz.sum() * area
        # 出力の地盤高は小数 4 桁なので、変化したセルごとに ±0.00005 m の丸めが入る
        tol_vol = 0.5e-4 * area * max(1, int((dz != 0.0).sum()))
        ok_vol = abs(added - erupted) <= tol_vol and hl.max() == 0.0
        m = re.findall(r"heat balance residual\s+[-+0-9.Ee]+ J \(\s*([-+0-9.Ee]+)", out)
        resid = float(m[-1]) if m else float("nan")
        ok_heat = abs(resid) < 1e-12
        # 広がり・到達距離(噴火口のセル中心から)・固まり終えた時刻(1 時間ごとの出力から)
        foot = dz > DZ_FOOT
        fj, fi = np.nonzero(foot)
        reach = float(np.hypot((fi + 1 - vi) * DX, (fj + 1 - vj) * DX).max())
        solid_h = float("nan")
        for fn in sorted(glob.glob(os.path.join(res, "Hl[0-9][0-9][0-9][0-9].txt"))):
            k = int(fn[-8:-4])
            if 0 < k < 9998 and k * 3600 > hours * 3600 and np.loadtxt(fn).max() == 0.0:
                solid_h = float(k)
                break
        rows.append(dict(run=name, vent_i=vi, vent_j=vj, q_m3s=q, hours=hours, erupted_m3=erupted,
                         reach_m=round(reach), area_km2=round(foot.sum() * area / 1e6, 3),
                         max_thick_m=round(float(dz.max()), 2), solid_by_h=solid_h,
                         heat_erupted_J=num(out, "heat erupted"), heat_radiated_J=num(out, "J, radiated"),
                         heat_convected_J=num(out, "J, convected"), heat_residual=resid,
                         subcycles=int(num(out, "subcycles total =")), t_wall_s=round(tw, 1),
                         checks=ok_vol and ok_heat))
        print(f"[flow {name}] {desc} (i,j)=({vi},{vj}), {q:.0f} m3/s x {hours:g} h: erupted {erupted:.3e} m3, "
              f"reach {reach:.0f} m, area {foot.sum() * area / 1e6:.2f} km2, max {dz.max():.1f} m, "
              f"all solid by {solid_h:.0f} h, heat residual {resid:.1e}, "
              f"checks {'ok' if ok_vol and ok_heat else 'FAIL'}  [{tw:.0f} s]", flush=True)
    with open(os.path.join(top, "flow.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    bad = [r["run"] for r in rows if not r["checks"]]
    print(f"[flow] {len(rows)} runs on the final terrain of {a.case} in {time.time() - t_all:.0f} s; "
          + ("all checks ok" if not bad else f"checks FAILED in {bad}"))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
