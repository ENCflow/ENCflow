#!/usr/bin/env python3
"""examples/stratovolcano: 溶岩流 → 降灰 → 侵食 を繰り返して成層火山を作る(段ごとの計算をつなぐドライバ)。

  python3 run_cycles.py P      # 主ケース: 火砕物(灰)の多い噴火 + 侵食
  python3 run_cycles.py L      # 比較: 溶岩の多い噴火 + 侵食
  python3 run_cycles.py P0     # 対照: P と同じ噴火で侵食なし
  オプション: --ncyc 10(サイクル数)、--seed 7(火口の列の乱数の種)、--morfac 100

1 サイクル = 3 段。各段の最終の地盤高 Z と土層厚 Sd を次の段の入力にする。
  1. 溶岩流(ENCflow。fn_lavaflow): 火口から溶岩を噴出させ、止まって固まるまで計算する。
     地下水の計算(fn_gwflow)を有効にして土層を確保し、固化した溶岩の下の灰を埋める
     (sd = 0。developer.md §51.6)。計算の終わりにまだ流れている溶岩(厚い舌の先端が
     ゆっくり進み続ける)は、その場で固まったとみなして地盤高に足し、下の灰を埋める
     (量は台帳 ledger.csv の molten_frozen に記録)。
  2. 降灰(このスクリプトの前処理。計算本体は降灰を扱わない): 火口からの距離 r に対して
     指数的に薄くなる厚さ T(r) = T0 exp(−r/b)(Pyle 1989 の指数的な薄化を円形に置いた
     模式)を、地盤高 z と侵食できる層 sd の両方に足す。
  3. 侵食(ENCflow。豪雨 1 回 × morfac): 雨 50 mm/h × 1 時間。灰の浸透能 5 mm/h
     (Green-Ampt)。しみ込めない雨が斜面を流れ、灰を掃流砂として運ぶ(f_fluvial。
     代表粒径 1 mm)。地形時間の加速 morfac(既定 100)で、この豪雨 morfac 回分の侵食・
     堆積とみなす(土石流 f_debris は morfac = 1 が必須なので使わない。README)。
火口: 主な噴火は山頂(中心)から標準偏差 75 m で散らした位置、2 回目以降の噴火の 25% は
山腹(山頂から 600〜1000 m、方位は一様)。山腹の噴火は溶岩 0.4 倍、灰は厚さ 0.3 倍・
薄化距離 0.5 倍(小さな火砕丘の模式)。
出力: result_<case>/ に各段の結果(cNN_lava/、cNN_ero/)、台帳 ledger.csv、各段の地表
surfaces.npz(plot_results.py が読む)。
"""
import argparse
import csv
import math
import os
import random
import re
import subprocess
import sys
import time

import numpy as np

# ---------------------------------------------------------------- 設定
NX = NY = 100                     # 格子数(5 km 四方)
DX = 50.0                         # 格子間隔 (m)
IC = JC = 50                      # 山頂(中心)のセル(1 始まり)
RHO_L = 2600.0                    # 溶岩の密度 (kg/m3)
QL = 20.0                         # 溶岩の噴出率 (m3/s)
TAIL = 1.0e7                      # 噴出の終了から溶岩の計算を続ける時間 (s)
RAIN, RDUR = 50.0, 60.0           # 豪雨の強度 (mm/h) と継続時間 (分)
KSV = 5.0                         # 灰の浸透能 (mm/h)
CASES = {
    # vl: 山頂の噴火の溶岩量 (m3)、tauy: 降伏応力 (Pa)、t0: 火口での灰の厚さ (m)、
    # b: 灰の薄化距離 (m)、erosion: 侵食の段を計算するか
    "P":  dict(vl=5.0e6, tauy=2.0e4, t0=15.0, b=400.0, erosion=True,
               title="火砕物の多い噴火 + 侵食(主ケース)"),
    "L":  dict(vl=1.0e7, tauy=5.0e4, t0=5.0, b=300.0, erosion=True,
               title="溶岩の多い噴火 + 侵食"),
    "P0": dict(vl=5.0e6, tauy=2.0e4, t0=15.0, b=400.0, erosion=False,
               title="P と同じ噴火、侵食なし(対照)"),
}
FLANK_P = 0.25                    # 2 回目以降の噴火が山腹になる確率
FLANK_R = (600.0, 1000.0)         # 山腹の火口の山頂からの距離 (m)
SUMMIT_SIG = 75.0                 # 山頂の火口の散らばり (m)


def vents(seed, n):
    """噴火の列: (種類, 山頂からの x (m), y (m))。種類 S = 山頂、F = 山腹"""
    rng = random.Random(seed)
    out = []
    for k in range(1, n + 1):
        if k > 1 and rng.random() < FLANK_P:
            r = rng.uniform(*FLANK_R)
            th = math.radians(rng.uniform(0.0, 360.0))
            out.append(("F", r * math.cos(th), r * math.sin(th)))
        else:
            out.append(("S", rng.gauss(0.0, SUMMIT_SIG), rng.gauss(0.0, SUMMIT_SIG)))
    return out


def vent_cell(v):
    """火口のセル (i, j)(1 始まり)。x は東向き、y は北向き。行列ファイルの先頭行が北端
    (j = 1)なので、北へ行くほど j は小さい"""
    return int(round(IC + v[1] / DX)), int(round(JC - v[2] / DX))


def eruption(c, v):
    """噴火の量: (溶岩量 (m3), 火口での灰の厚さ (m), 薄化距離 (m))"""
    if v[0] == "S":
        return c["vl"], c["t0"], c["b"]
    return 0.4 * c["vl"], 0.3 * c["t0"], 0.5 * c["b"]


def wmat(fn, a):
    np.savetxt(fn, a, fmt="%.4f")


def run(exe, param, log):
    t = time.time()
    r = subprocess.run([exe, param], capture_output=True, text=True)
    with open(log, "w") as f:
        f.write(r.stdout + r.stderr)
    if r.returncode != 0:
        sys.stdout.write(r.stdout[-3000:] + r.stderr[-2000:])
        sys.exit("encflow failed: " + param)
    return time.time() - t, r.stdout


GEO = """&list_geoinfo
  lx = {lx:.1f}
  ly = {ly:.1f}
  nx = {nx}
  ny = {ny}
  f_ztype = 1
  fn_z = '{fz}'             ! 前の段の最終の地盤高
  f_rntype = 0
  rn0 = 0.05
  f_sdtype = 1
  fn_sd = '{fsd}'           ! 前の段の最終の土層厚(侵食できる灰)
  sy0 = 0.5                 ! 灰の間隙率
/
"""

GW = """&list_gwflow
  f_gwvertical = 2          ! Green-Ampt(gw_psif = 0 で一定の浸透能)
/
&list_gwflow_greenampt
  gw_ksv_mmh = {ksv}        ! 灰の浸透能 (mm/h)
  gw_psif = 0.0
/
"""


def lava_param(case, k, c, v, data, res):
    vl, _, _ = eruption(c, v)
    vi, vj = vent_cell(v)
    tend = vl / QL
    tt = tend + TAIL
    return f"""! examples/stratovolcano サイクル {k} の溶岩流の段(run_cycles.py が作る)
&list_sysparam
  f_gridsystem = 0
  f_govequation = 0
  dt = 1800                 ! 水がないので溶岩のサブサイクルが安定条件を担う
  t0 = 0
  tt = {tt:.0f}
  dt_disp = {tt / 4:.0f}
  dt_file = {tt:.0f}
  dt_recrd = {tt:.0f}
  fn_geoinfo = '-'
  fn_initial = '-'
  fn_lavaflow = '-'
  fn_gwflow = '-'           ! 土層(灰)を確保して、固化した溶岩の下の灰を埋めるため
  dir_data = '{data}'
  dir_result = '{res}'
  f_check_cfl = 0
  f_out_z = 1
/
&list_initial
  f_htype = 0
  h0 = 0.0
/
{GEO.format(lx=NX * DX, ly=NY * DX, nx=NX, ny=NY, fz=f"z_{k - 1:02d}.txt", fsd=f"sd_{k - 1:02d}.txt")}{GW.format(ksv=KSV)}&list_lavaflow
  lv_rho = {RHO_L}
  lv_visc = 1.0e8           ! 粘度 (Pa s)。形は変えず時間の尺度だけを決める
  lv_tauy = {c['tauy']:.1e}           ! 降伏応力 (Pa)。安山岩質の範囲(users guide の型別表)
  lv_wsol = 5.0e-3          ! 固化レート (m/s)
  lv_vsol = 5.0e-6          ! 停止判定の速度閾値 (m/s)
  lv_nsubmax = 1000000
  lv_cell(1:2,1,1) = {vi}, {vj}
  lv_val(1:2,1,1) = 0.0, {QL}
  lv_val(1:2,2,1) = {tend / 60.0:.3f}, {QL}
  lv_val(1:2,3,1) = {tend / 60.0:.3f}, 0.0
/
"""


def ero_param(case, k, morfac, data, res):
    tt = (10 + RDUR + 50) * 60
    return f"""! examples/stratovolcano サイクル {k} の侵食の段(run_cycles.py が作る)
&list_sysparam
  f_gridsystem = 0
  f_govequation = 0
  dt = 1.0                  ! 時間刻み (s)
  t0 = 0
  tt = {tt}                 ! 無降雨 10 分 + 降雨 {RDUR:.0f} 分 + 減水 50 分
  dt_disp = 1200
  dt_file = {tt}
  dt_recrd = {tt}
  fn_geoinfo = '-'
  fn_initial = '-'
  fn_enc = '-'
  fn_precip = '-'
  fn_gwflow = '-'
  fn_geomorph = '-'
  fn_boundary = '-'
  dir_data = '{data}'
  dir_result = '{res}'
  f_out_z = 1
  f_check_cfl = 0
  dd = 0.0002               ! 移動限界水深 (m)。斜面の薄いシート流を解くため(ashfall_lahar と同じ)
/
&list_enc
  f_gravity_correction = 1  ! 急勾配の重力補正
/
&list_initial
  f_htype = 0
  h0 = 0.0
/
{GEO.format(lx=NX * DX, ly=NY * DX, nx=NX, ny=NY, fz=f"za_{k:02d}.txt", fsd=f"sda_{k:02d}.txt")}&list_precip
  prtype = 1
  prval(1:2,1) = 0, 0
  prval(1:2,2) = 10, 0
  prval(1:2,3) = 10, {RAIN:.0f}
  prval(1:2,4) = {10 + RDUR:.0f}, {RAIN:.0f}
  prval(1:2,5) = {10 + RDUR:.0f}, 0
/
{GW.format(ksv=KSV)}&list_geomorph
  dt_geomorph = 0.0
  morfac = {morfac:.1f}            ! この豪雨 {morfac:.0f} 回分の侵食・堆積とみなす
  f_fluvial = 1             ! 表面流による灰の掃流砂
  fluv_d50 = 0.001          ! 灰の代表粒径 (m)
  fluv_porosity = 0.5       ! 灰の層の空隙率
  fluv_dzmax = 0.05
  fluv_slope = 1            ! 斜面の勾配による流砂方向の補正
  f_repose = 1              ! 安息角を超えた斜面の崩落(谷壁が急になりすぎないように)
  repose_phi = 33.0
/
&list_bound_edge
  f_bc_e = 1                ! 四辺とも自由流出
  f_bc_w = 1
  f_bc_n = 1
  f_bc_s = 1
/
"""


def ledger_value(text, key):
    m = re.search(key + r"\s+([-+0-9.E]+)", text)
    return float(m.group(1)) if m else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("case", choices=sorted(CASES))
    ap.add_argument("--ncyc", type=int, default=10)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--morfac", type=float, default=100.0)
    a = ap.parse_args()
    c = CASES[a.case]
    exe = os.path.abspath("encflow")
    if not os.path.exists(exe):
        sys.exit("encflow not found (run make first)")
    top = f"result_{a.case}"
    data = os.path.join(top, "data")
    os.makedirs(data, exist_ok=True)

    # 初期地形: 平坦面 + ±0.5 m の乱れ(流れと谷の対称性を破る種)。土層なし
    rng = random.Random(1)
    z = np.array([[rng.uniform(-0.5, 0.5) for _ in range(NX)] for _ in range(NY)])
    sd = np.zeros((NY, NX))
    wmat(os.path.join(data, "z_00.txt"), z)
    wmat(os.path.join(data, "sd_00.txt"), sd)
    xs = (np.arange(NX) + 0.5) * DX
    X, Y = np.meshgrid(xs, xs)                 # 配列の行 = j(先頭行が北端)。Y は行の位置
    area = DX * DX

    seq = vents(a.seed, a.ncyc)
    surf = {"z0": z.copy(), "vents": np.array([[0 if v[0] == "S" else 1, *vent_cell(v)] for v in seq])}
    rows = []
    t_all = time.time()
    for k in range(1, a.ncyc + 1):
        v = seq[k - 1]
        vl, t0, b = eruption(c, v)
        vi, vj = vent_cell(v)
        # ---- 1. 溶岩流 ----
        res = os.path.join(top, f"c{k:02d}_lava")
        pf = os.path.join(top, f"param_c{k:02d}_lava.txt")
        with open(pf, "w") as f:
            f.write(lava_param(a.case, k, c, v, data, res))
        tl, out = run(exe, pf, os.path.join(top, f"Screen_c{k:02d}_lava.log"))
        zl = np.loadtxt(os.path.join(res, "Z9998.txt"))
        sdl = np.loadtxt(os.path.join(res, "Sd9998.txt"))
        hl = np.loadtxt(os.path.join(res, "Hl9998.txt"))
        erupted = ledger_value(out, "erupted")
        buried = ledger_value(out, "soil buried under solidified lava")
        # 残った溶岩はその場で固まったとみなす(下の灰を埋める)
        frozen = hl.sum() * area
        buried += (sdl * (hl > 0)).sum() * area
        zl = zl + hl
        sdl = np.where(hl > 0, 0.0, sdl)
        lava_added = (zl - z).sum() * area
        # 検査: 溶岩の体積の収支と、溶岩の下の灰が埋まっていること
        ok_lava = abs(lava_added - erupted) <= 1e-3 * erupted
        ok_burial = float(np.max(np.where(zl - z > 0.01, sdl, 0.0))) == 0.0
        # ---- 2. 降灰 ----
        rv = np.hypot(X - (vi - 0.5) * DX, Y - (vj - 0.5) * DX)
        ash = t0 * np.exp(-rv / b)
        za, sda = zl + ash, sdl + ash
        ash_vol = ash.sum() * area
        wmat(os.path.join(data, f"za_{k:02d}.txt"), za)
        wmat(os.path.join(data, f"sda_{k:02d}.txt"), sda)
        # ---- 3. 侵食 ----
        if c["erosion"]:
            res = os.path.join(top, f"c{k:02d}_ero")
            pf = os.path.join(top, f"param_c{k:02d}_ero.txt")
            with open(pf, "w") as f:
                f.write(ero_param(a.case, k, a.morfac, data, res))
            te, out = run(exe, pf, os.path.join(top, f"Screen_c{k:02d}_ero.log"))
            z = np.loadtxt(os.path.join(res, "Z9998.txt"))
            sd = np.loadtxt(os.path.join(res, "Sd9998.txt"))
        else:
            te = 0.0
            z, sd = za.copy(), sda.copy()
        dz = z - za
        eroded = max(0.0, -dz[dz < 0].sum() * area)
        deposited = dz[dz > 0].sum() * area
        net = dz.sum() * area            # 負 = 領域外へ出た量
        wmat(os.path.join(data, f"z_{k:02d}.txt"), z)
        wmat(os.path.join(data, f"sd_{k:02d}.txt"), sd)
        surf[f"zl{k:02d}"], surf[f"za{k:02d}"], surf[f"z{k:02d}"] = zl, za, z.copy()
        rows.append(dict(cycle=k, vent=v[0], vi=vi, vj=vj, lava_m3=vl, erupted_m3=erupted,
                         lava_added_m3=lava_added, molten_frozen_m3=frozen, ash_buried_m3=buried,
                         ash_m3=ash_vol, eroded_m3=eroded, deposited_m3=deposited, net_m3=net,
                         lava_check=ok_lava, burial_check=ok_burial, t_lava_s=round(tl, 1),
                         t_ero_s=round(te, 1)))
        print(f"[{a.case}] cycle {k:2d} ({'summit' if v[0] == 'S' else 'flank '} {vi:3d},{vj:3d}): "
              f"lava {vl:.2e} m3 (still molten {frozen / erupted:5.1%}, buried ash {buried:.2e}), "
              f"ash {ash_vol:.2e} m3, eroded {eroded:.2e}, deposited {deposited:.2e}, net {net:+.1e} m3, "
              f"checks {'ok' if ok_lava and ok_burial else 'FAIL'}  [{tl:.0f} s + {te:.0f} s]", flush=True)
    np.savez_compressed(os.path.join(top, "surfaces.npz"), **surf)
    with open(os.path.join(top, "ledger.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    bad = [r["cycle"] for r in rows if not (r["lava_check"] and r["burial_check"])]
    print(f"[{a.case}] {a.ncyc} cycles in {time.time() - t_all:.0f} s; "
          + ("all checks ok" if not bad else f"checks FAILED in cycles {bad}"))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
