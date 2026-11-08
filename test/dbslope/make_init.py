#!/usr/bin/env python3
"""test/dbslope の入力と設定ファイルの生成(Run.sh・Run_MPI.sh が呼ぶ)。

混合体流動(土石流モデル f_debris)の抵抗則を斜面に沿って評価する f_gravity_correction = 2 の検定
(developer.md §101)。勾配 tan30° の一様な斜面の帯(150 m × 8 m、Δx = 1 m、4 近傍)の上端から混合体を
一定の流量で流し込み、帯の中ほどの等流の深さを解析解と比べる。土砂の交換はない(f_dbed = 0。濃度は流入の
値のまま)。

抵抗則(4 つ)× f_gravity_correction(1・2)の 8 ケース:
  voellmy   : Voellmy(f_dbres = 4。降伏 μ + 乱流項 g V²/(ξ h))
  egashira  : 江頭の構成則(f_dbres = 2。降伏 + 層流則 f_b ∝ (d/h)²)
  stony     : 高橋・中川の石礫型(f_dbres = 3。C > 0.4 C*。降伏 tanα' + A'{(1−C)/C}^{2/3}(d/h)²)
  collective: 高橋・中川の掃流状集合流動(f_dbres = 3。C ≤ 0.4 C*。降伏 tanα' + (d/h)/0.49)
2 は降伏を 1/(r cos θ) 倍(最急勾配の向きの流れでは 1)、速度の 2 乗の抵抗を r/cos³θ 倍(掃流状は
r/cos²θ 倍。最急勾配の向きでは 1/cos⁴θ・1/cos³θ)にする。1 は水平の形のまま。

  python3 make_init.py        地形 d_slope/z.txt と p_<case>.txt を書く
  python3 make_init.py list   ケース名を 1 行ずつ出す
定数は Check_dbslope.py と対。
"""
import math
import os
import sys

NX, NY, DX = 150, 8, 1.0
THETA = 30.0                         # 斜面の傾斜角 (deg)
G = math.tan(math.radians(THETA))
DT, TT = 0.02, 90.0
QIN = 4.0                            # 流入の水の流量 (m³/s。西辺の 8 セルに一様)
LAWS = {                             # 抵抗則: (f_dbres, 流入の hs/h 比 cs、追加の設定)
    "voellmy":    (4, 0.8,  "  db_mu = 0.1               ! Voellmy の μ\n  db_xi = 200.0             ! Voellmy の ξ (m/s²)\n"),
    "egashira":   (2, 0.8,  "  db_phi = 35.0             ! 内部摩擦角 (deg)\n  db_d50 = 0.05             ! 代表粒径 (m)\n"
                            "  db_erest = 0.85           ! 粒子の反発係数\n"),
    "stony":      (3, 0.8,  "  db_d50 = 0.05             ! 代表粒径 d_L (m)\n"),
    "collective": (3, 0.25, "  db_d50 = 0.05             ! 代表粒径 d_L (m)\n"),
}
MU, XI = 0.1, 200.0
PHI, D50, EREST = 35.0, 0.05, 0.85
SGRAV, POROSITY = 1.65, 0.4          # 水中比重 s(既定)、空隙率 λ(C* = 1 − λ)
GCS = (1, 2)


def case_name(law, gc):
    return f"{law}_g{gc}"


CASES = [(law, gc) for law in LAWS for gc in GCS]


def write_terrain():
    os.makedirs("d_slope", exist_ok=True)
    with open("d_slope/z.txt", "w") as f:
        for _ in range(NY):
            f.write(" ".join(f"{G * (NX * DX - (i + 0.5) * DX):.6f}" for i in range(NX)) + "\n")


def write_case(law, gc):
    name = case_name(law, gc)
    fres, cs, extra = LAWS[law]
    inflow = "".join(f"  inflow_cell(1:2,{j},1) = 1, {j}\n" for j in range(1, NY + 1))
    with open(f"p_{name}.txt", "w") as f:
        f.write(f"""!======================================================================
! dbslope: ケース {name}(make_init.py が生成。構成の説明は make_init.py の先頭)
!======================================================================
&list_sysparam
  dt = {DT:g}
  t0 = 0
  tt = {TT:g}
  dt_disp = {TT:g}
  dt_file = {TT:g}
  dt_recrd = {TT:g}
  fn_geoinfo = '-'
  fn_initial = '-'
  fn_enc = '-'
  fn_geomorph = '-'
  fn_boundary = '-'
  dir_data = 'd_slope'
  dir_result = 'result_{name}'
  dir_save = 'save_{name}'
  f_state_save = 1
  f_out_h = 1
  f_out_hs = 1
  f_check_cfl = 0
/
&list_enc
  f_gravity_correction = {gc}   ! 1: 抵抗は水平の形 / 2: 抵抗を斜面に沿って評価(既定。§101)
  p_diagratio = 0.0          ! 4 近傍(斜めの辺の降伏の非線形を除く。test/volcano と同じ。§28.8)
/
&list_initial
  f_htype = 0
  h0 = 0.0
/
&list_geoinfo
  lx = {NX * DX:g}
  ly = {NY * DX:g}
  nx = {NX}
  ny = {NY}
  f_ztype = 1
  fn_z = 'z.txt'
  f_rntype = 0
  rn0 = 0.03
  sd0 = 1.0
  sy0 = 0.2
/
&list_geomorph
  dt_geomorph = 0.0
  morfac = 1.0
  f_debris = 1
  f_dbed = 0                 ! 交換なし(濃度は流入の値のまま)
  f_dbres = {fres}
{extra}  db_vstop = 0.05
  fluv_porosity = {POROSITY:g}       ! C* = 1 − λ
/
&list_bound_inflow
{inflow}  inflow_val(1:2,1,1) = 0, {QIN:g}
  inflow_val(1:2,2,1) = 9999, {QIN:g}
  inflow_cs(1:2,1,1) = 0, {cs:g}
  inflow_cs(1:2,2,1) = 9999, {cs:g}
  inflow_dist(1) = 0
/
""")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        for law, gc in CASES:
            print(case_name(law, gc))
        return
    write_terrain()
    for law, gc in CASES:
        write_case(law, gc)


if __name__ == "__main__":
    main()
