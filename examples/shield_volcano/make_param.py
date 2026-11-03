#!/usr/bin/env python3
"""examples/shield_volcano の設定ファイルを作る(make params が呼ぶ。生成物はリポジトリに入れてある)。

  python3 make_param.py [--seed 1] [--neru 20] [--sigma 400] [--cone 0]

  param_S1.txt   楯状火山・主ケース(降伏応力 2×10³ Pa = 玄武岩質の溶岩の実測の範囲)
  param_S2.txt   楯状火山・比較(降伏応力 2×10⁴ Pa = 冷えて固まる効果を含めた実効値)
  param_dome.txt     溶岩ドーム(1 つの火口、降伏応力 10⁵ Pa。固化なし = 静止形を解析解と比べる)
  param_dome_sol.txt 同じドームで固化あり(止まりかけた縁から固まると形がどう変わるか)

S1 と S2 は同じ噴火の列(火口の位置・噴出量・噴出率)で、降伏応力・粘度・停止判定の閾値・
時間の刻みだけが違う。噴火の列は乱数(--seed)で作る。火口は中心から標準偏差 --sigma (m) の
正規分布で散らし、噴出量は中央値 3×10⁷ m³・対数標準偏差 0.7 の対数正規分布、噴出率は
20〜60 m³/s の一様分布。噴火と噴火の間は、溶岩が止まって固まるまでの時間だけ空ける
(休止期間を縮めている。水も侵食もないので、休止期間には何も起きない)。
--cone > 0 なら、平坦面の代わりに勾配 --cone (m/m) の緩い円錐から始める(z_cone.txt を書く)。
"""
import argparse
import math
import random

ap = argparse.ArgumentParser()
ap.add_argument("--seed", type=int, default=1)
ap.add_argument("--neru", type=int, default=20)       # 噴火の回数(1 回の計算の噴火口の上限 20)
ap.add_argument("--sigma", type=float, default=400.0)  # 火口の散らばり (m)
ap.add_argument("--cone", type=float, default=0.0)     # 初期の円錐の勾配 (m/m)。0 = 平坦面
a = ap.parse_args()
assert 1 <= a.neru <= 20, "1 回の計算で使える噴火口は 20 まで(lvmax)"

NX = NY = 120          # 格子数(12 km 四方)
DX = 100.0             # 格子間隔 (m)
IC = JC = (NX + 1) / 2.0
VMED, VSIG = 3.0e7, 0.7
QLO, QHI = 20.0, 60.0

rng = random.Random(a.seed)
eru = []
for k in range(a.neru):
    x, y = rng.gauss(0.0, a.sigma), rng.gauss(0.0, a.sigma)
    i = int(round(IC + x / DX))
    j = int(round(JC - y / DX))
    v = VMED * math.exp(rng.gauss(0.0, VSIG))
    q = rng.uniform(QLO, QHI)
    eru.append((i, j, v, q))

if a.cone > 0.0:
    with open("z_cone.txt", "w") as f:
        for j in range(1, NY + 1):
            f.write(" ".join("%.3f" % (a.cone * max(NX * DX / 2 - math.hypot((i - IC) * DX, (j - JC) * DX), 0.0))
                             for i in range(1, NX + 1)) + "\n")

GEO_FLAT = """&list_geoinfo
  lx = %g
  ly = %g
  nx = %d
  ny = %d
  f_ztype = 0
  z0 = 0.0                  ! 平坦面から始める
  f_rntype = 0
  rn0 = 0.03
/
"""
GEO_CONE = """&list_geoinfo
  lx = %g
  ly = %g
  nx = %d
  ny = %d
  f_ztype = 1
  fn_z = 'z_cone.txt'       ! 緩い円錐から始める(make_param.py --cone)
  f_rntype = 0
  rn0 = 0.03
/
"""


def write_shield(name, title, tauy, visc, vsol, dt, gap, tail, note):
    t = 0.0
    sched = []
    for (i, j, v, q) in eru:
        dur = v / q
        sched.append((i, j, v, q, t, t + dur))
        t = t + dur + gap
    tt = sched[-1][5] + tail
    with open("param_%s.txt" % name, "w") as f:
        f.write("!" + "=" * 70 + "\n")
        f.write("! examples/shield_volcano %s: %s\n" % (name, title))
        f.write("!   make_param.py が書いた(--seed %d, %d 回の噴火、火口の散らばり %.0f m)。\n"
                % (a.seed, a.neru, a.sigma))
        for line in note:
            f.write("!   " + line + "\n")
        f.write("!" + "=" * 70 + "\n")
        f.write("&list_sysparam\n  f_gridsystem = 0\n  f_govequation = 0\n")
        f.write("  dt = %g                 ! 時間刻み (s)。水がないので溶岩のサブサイクルが安定条件を担う\n" % dt)
        f.write("  t0 = 0\n  tt = %d             ! 最後の噴火の %d 日後まで\n" % (int(tt), int(tail / 86400)))
        f.write("  dt_disp = %d\n  dt_file = %d          ! 分布の出力は 10 回\n  dt_recrd = %d\n"
                % (int(tt / 10), int(tt / 10), int(tt)))
        f.write("  fn_geoinfo = '-'\n  fn_initial = '-'\n  fn_lavaflow = '-'\n")
        f.write("  dir_result = 'result_%s'\n  dir_save = 'save_%s'\n" % (name, name))
        f.write("  f_state_save = 1\n  f_check_cfl = 0\n  f_out_z = 1               ! 地盤高 Z(固化した溶岩)を出力\n/\n\n")
        f.write("&list_initial\n  f_htype = 0\n  h0 = 0.0                  ! 水なし\n/\n\n")
        f.write((GEO_CONE if a.cone > 0.0 else GEO_FLAT) % (NX * DX, NY * DX, NX, NY))
        f.write("\n&list_lavaflow\n  lv_rho = 2600.0\n")
        f.write("  lv_visc = %.1e           ! 粘度 (Pa s)。形は変えず時間の尺度だけを決める(README「注意」)\n" % visc)
        f.write("  lv_tauy = %.1e           ! 降伏応力 (Pa)。溶岩が止まる厚さ = 形を決める\n" % tauy)
        f.write("  lv_wsol = 5.0e-3          ! 固化レート (m/s)\n")
        f.write("  lv_vsol = %.1e           ! 停止判定の速度閾値 (m/s)。流れの速さより十分小さく\n" % vsol)
        f.write("  lv_nsubmax = 1000000\n")
        for k, (i, j, v, q, ts, te) in enumerate(sched, start=1):
            f.write("  ! 噴火 %d: 体積 %.2e m3、噴出率 %.1f m3/s、%.1f 日間\n" % (k, v, q, (te - ts) / 86400))
            f.write("  lv_cell(1:2,1,%d) = %d, %d\n" % (k, i, j))
            pts = ([(0.0, 0.0)] if ts > 0 else []) + [(ts / 60, 0.0), (ts / 60, q), (te / 60, q), (te / 60, 0.0)]
            for m, (tm, qq) in enumerate(pts, start=1):
                f.write("  lv_val(1:2,%d,%d) = %.3f, %.4f\n" % (m, k, tm, qq))
        f.write("/\n")
    return sched, tt


s1, tt1 = write_shield(
    "S1", "楯状火山・主ケース(降伏応力 2×10³ Pa)", 2.0e3, 1.0e6, 5.0e-5, 300.0, 1.0e6, 2.0e6,
    ["降伏応力は玄武岩質のアア溶岩の実測の範囲(1e3〜5e3 Pa。users_guide/lavaflow.md の型別表)。",
     "粘度は玄武岩質の実測(1e2〜1e4 Pa s)より大きい 1e6 Pa s にして時間を縮めている",
     "(形は粘度によらない。停止判定の閾値も同じ比で合わせる)。噴火の間は 10^6 s(約 12 日)。"])
s2, tt2 = write_shield(
    "S2", "楯状火山・比較(降伏応力 2×10⁴ Pa)", 2.0e4, 1.0e8, 5.0e-6, 1800.0, 2.0e6, 5.0e6,
    ["S1 と同じ噴火の列で、降伏応力を 10 倍にした。実際の玄武岩の溶岩流は冷えて表面が固まり",
     "止まる(このモデルは温度を計算しない)。その効果を含めた「実効の」降伏応力として大きい値を",
     "与えると、実在の楯状火山に近い勾配になる(README「結果」)。厚い流れは拡散が速いので、",
     "粘度を 1e8 Pa s にして時間刻みを広げている。噴火の間は 2×10^6 s。"])

# 溶岩ドーム(1 つの火口からの定率噴出)
ND, DXD = 101, 10.0


def write_dome(name, wsol, vsol, note):
    with open("param_%s.txt" % name, "w") as f:
        f.write("!" + "=" * 70 + "\n")
        f.write("! examples/shield_volcano %s: 溶岩ドーム(1 つの火口、降伏応力 10⁵ Pa)\n" % name)
        f.write("!   平坦面の中央の 1 セルから 2 m3/s を 10^6 s(約 12 日。計 2×10^6 m3)噴出する。\n")
        for line in note:
            f.write("!   " + line + "\n")
        f.write("!   粘度 1e10 Pa s はデイサイト質のドームの目安(静止形は粘度によらない)。\n")
        f.write("!" + "=" * 70 + "\n")
        f.write("&list_sysparam\n  f_gridsystem = 0\n  f_govequation = 0\n  dt = 300\n  t0 = 0\n")
        f.write("  tt = 6000000             ! 噴出の終わりから 5×10^6 s 後まで\n")
        f.write("  dt_disp = 600000\n  dt_file = 1000000\n  dt_recrd = 6000000\n")
        f.write("  fn_geoinfo = '-'\n  fn_initial = '-'\n  fn_lavaflow = '-'\n")
        f.write("  dir_result = 'result_%s'\n  dir_save = 'save_%s'\n" % (name, name))
        f.write("  f_state_save = 1\n  f_check_cfl = 0\n  f_out_z = 1\n/\n\n")
        f.write("&list_initial\n  f_htype = 0\n  h0 = 0.0\n/\n\n")
        f.write("&list_geoinfo\n  lx = %g\n  ly = %g\n  nx = %d\n  ny = %d\n  f_ztype = 0\n  z0 = 0.0\n"
                "  f_rntype = 0\n  rn0 = 0.03\n/\n\n" % (ND * DXD, ND * DXD, ND, ND))
        f.write("&list_lavaflow\n  lv_rho = 2600.0\n")
        f.write("  lv_visc = 1.0e10          ! 粘度 (Pa s)。デイサイト質のドームの目安\n")
        f.write("  lv_tauy = 1.0e5           ! 降伏応力 (Pa)。a = 2τ_y/(ρg) = 7.85 m\n")
        if wsol > 0.0:
            f.write("  lv_wsol = %.1e           ! 固化レート (m/s)\n" % wsol)
            f.write("  lv_vsol = %.1e           ! 停止判定の速度閾値 (m/s)。ドームの流れ(〜1e-4 m/s)より小さく\n" % vsol)
        else:
            f.write("  lv_wsol = 0.0             ! 固化なし(止まった形を解析解と比べる)\n")
        f.write("  lv_nsubmax = 1000000\n")
        f.write("  lv_cell(1:2,1,1) = %d, %d ! 中央の 1 セル\n" % ((ND + 1) // 2, (ND + 1) // 2))
        f.write("  lv_val(1:2,1,1) = 0, 2.0  ! (時刻(min), 噴出率(m3/s))\n")
        f.write("  lv_val(1:2,2,1) = 16666.667, 2.0\n")
        f.write("  lv_val(1:2,3,1) = 16666.667, 0.0 ! 重複時刻 = 約 10^6 s で階段状に停止\n/\n")


write_dome("dome", 0.0, 0.0,
           ["固化なし。止まった形(降伏応力で支えられた静止形)を塑性ドームの解析解",
            "h(r)^2 = (2τ_y/ρg)(R − r) と比べる。"])
write_dome("dome_sol", 5.0e-3, 1.0e-6,
           ["固化あり。止まりかけた縁から固まるので、固化なし(param_dome.txt)より中央が高くなる",
            "(停止判定の閾値 lv_vsol による数値的な閉じ方の影響。README「補足」)。"])

print("S1: %d eruptions, total %.3e m3, tt = %.3e s (%.0f days)" % (len(s1), sum(e[2] for e in s1), tt1, tt1 / 86400))
print("S2: same eruptions, tt = %.3e s (%.0f days)" % (tt2, tt2 / 86400))
