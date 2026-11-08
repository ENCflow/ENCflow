#!/usr/bin/env python3
"""test/steepwave の入力と設定ファイルの生成(Run.sh・Run_MPI.sh が呼ぶ)。

水面の勾配の項の可変の重力 g′(f_gravity_correction = 3。Yuan ら 2016 の式 42 の水の場合。
developer.md §100)の検定。3 つの構成を、比べる f_gravity_correction の値ごとに作る。

  lake: 静止した湖(水位 0)。勾配 1(45°)の平面の地盤を格子の x 軸から 30° の向きに傾け、
        湖岸の乾いた斜面まで含める。水面が水平なら g′ の値によらず力が 0 で、静止が保たれる
        (2・3)。勾配と水深の勾配の接線成分(minmod のセルの勾配)の組み立てを確かめる。
  wave: 急な湖底(勾配 0.5)を渡る小さな長波。深さ 40 m の平らな湖底 → 勾配 0.5 の斜面 → 深さ
        4 m の平らな浅瀬。水面がほぼ水平な深い水では鉛直の静水圧が正しく、補正なし(0)の浅水
        方程式がそのまま当てはまる。3 は g′ ≈ g でこれに一致し、2 は斜面の上で g_e = g cos²θ に
        なって波が cos θ 倍に遅れる(案 D)。
  bump: 勾配 tan30° の摩擦のない斜面に一様な層(地盤に直角な厚さ 1 m)を置き、小さな山(厚さの
        1 %)を載せる。層全体が g sinθ で加速しても、山は上下 2 つに分かれ、その間隔は斜面に沿う
        座標で 2√(g cosθ h_n) t で広がる(薄層の式の線形の波速。層と一緒に動く座標では重力 g cosθ の
        浅水方程式)。間隔の広がる速さを比べると層の移動が打ち消される。斜面の向きの水深の勾配の
        係数は薄層の式で g cos⁴θ、2 は g cos²θ(1/cos θ 倍に速い)、3 は一様な層のまわりで g cos⁴θ
        (案 E)、0 は g(1/cos²θ 倍)。4 近傍(1 次元。南北の壁の行で斜めの辺が欠ける影響を除く)。

  python3 make_init.py        全ケースの地形・初期水位と p_<case>.txt を書く
  python3 make_init.py list   ケース名を 1 行ずつ出す
定数は Check_steepwave.py と対。
"""
import math
import os
import sys

G = 9.8

# --- lake ---
LAKE_N, LAKE_DX = 40, 1.0
LAKE_S, LAKE_PHI = 1.0, 30.0          # 勾配、下り向きの x 軸からの角度 (deg)
LAKE_DT, LAKE_TT = 0.02, 60.0
LAKE_GCS = (2, 3)

# --- wave ---
WAVE_NX, WAVE_NY, WAVE_DX = 400, 16, 2.0
WAVE_H0, WAVE_S, WAVE_X0, WAVE_HS = 40.0, 0.5, 400.0, 4.0   # 深さ、斜面の勾配、斜面の下端、浅瀬の深さ
WAVE_A, WAVE_XC, WAVE_SIG = 0.02, 250.0, 25.0               # 初期の水位の山(ガウス形)
WAVE_DT, WAVE_TT, WAVE_REC = 0.05, 40.0, 0.05
WAVE_PROBES = (381.0, 421.0, 441.0, 461.0, 491.0, 551.0)   # プローブの x (m。セルの中心)
WAVE_GCS = (0, 2, 3)

# --- bump ---
BUMP_NX, BUMP_NY, BUMP_DX = 1400, 4, 0.5
BUMP_THETA = 30.0                      # 斜面の傾斜角 (deg)
BUMP_HN, BUMP_A, BUMP_SIG, BUMP_X0 = 1.0, 0.01, 4.0, 300.0   # 層厚、山の高さ(地盤に直角)、幅(斜面に沿う)、中心の x
BUMP_DT, BUMP_TT, BUMP_OUT = 0.005, 6.0, 3.0
BUMP_GCS = (0, 2, 3)


def wave_bed(x):
    """wave の地盤高 (m)。湖面は 0。"""
    z = -WAVE_H0 + WAVE_S * (x - WAVE_X0)
    return min(max(z, -WAVE_H0), -WAVE_HS)


def bump_bed(x):
    return 500.0 - math.tan(math.radians(BUMP_THETA)) * x


def case_name(cfg, gc):
    return f"{cfg}_g{gc}"


CASES = ([("lake", gc) for gc in LAKE_GCS] + [("wave", gc) for gc in WAVE_GCS]
         + [("bump", gc) for gc in BUMP_GCS])


def write_grid(path, nx, ny, val):
    """先頭行が北端(行 0 が南端)のテキストラスタ。val(i, j) はセル中心の値。"""
    rows = []
    for j in reversed(range(ny)):
        rows.append(" ".join(f"{val(i, j):.8f}" for i in range(nx)))
    with open(path, "w") as f:
        f.write("\n".join(rows) + "\n")


def write_inputs():
    os.makedirs("d_lake", exist_ok=True)
    ph = math.radians(LAKE_PHI)
    c = LAKE_N * LAKE_DX / 2

    def zl(i, j):
        x, y = (i + 0.5) * LAKE_DX - c, (j + 0.5) * LAKE_DX - c
        return -LAKE_S * (x * math.cos(ph) + y * math.sin(ph))     # 下り向き φ(東北東)へ下がる
    write_grid("d_lake/z.txt", LAKE_N, LAKE_N, zl)

    os.makedirs("d_wave", exist_ok=True)
    write_grid("d_wave/z.txt", WAVE_NX, WAVE_NY, lambda i, j: wave_bed((i + 0.5) * WAVE_DX))

    def ew(i, j):
        x = (i + 0.5) * WAVE_DX
        return WAVE_A * math.exp(-((x - WAVE_XC) / WAVE_SIG) ** 2)
    write_grid("d_wave/e0.txt", WAVE_NX, WAVE_NY, ew)

    os.makedirs("d_bump", exist_ok=True)
    write_grid("d_bump/z.txt", BUMP_NX, BUMP_NY, lambda i, j: bump_bed((i + 0.5) * BUMP_DX))
    cth = math.cos(math.radians(BUMP_THETA))

    def hb(i, j):                                                 # 鉛直の水深 = 地盤に直角な厚さ / cos θ
        s = ((i + 0.5) * BUMP_DX - BUMP_X0) / cth                 # 斜面に沿う距離
        return (BUMP_HN + BUMP_A * math.exp(-(s / BUMP_SIG) ** 2)) / cth
    write_grid("d_bump/h0.txt", BUMP_NX, BUMP_NY, hb)


def param(cfg, gc):
    name = case_name(cfg, gc)
    if cfg == "lake":
        nx = ny = LAKE_N
        dx, dt, tt, dfile, drec, rn = LAKE_DX, LAKE_DT, LAKE_TT, LAKE_TT, LAKE_TT, 0.03
        init = "  f_htype = 2\n  e0 = 0.0\n"
        probes = ""
    elif cfg == "wave":
        nx, ny = WAVE_NX, WAVE_NY
        dx, dt, tt, dfile, drec, rn = WAVE_DX, WAVE_DT, WAVE_TT, WAVE_TT, WAVE_REC, 0.0
        init = "  f_htype = 3\n  fn_hinit = 'e0.txt'\n"
        pts = "".join(f"  pbxy(:,{k + 1}) = {x:.1f}, {(WAVE_NY / 2 - 0.5) * WAVE_DX:.1f}\n"
                      for k, x in enumerate(WAVE_PROBES))
        probes = f"""&list_record
  pbxytype = 1
{pts}/
"""
    else:
        nx, ny = BUMP_NX, BUMP_NY
        dx, dt, tt, dfile, drec, rn = BUMP_DX, BUMP_DT, BUMP_TT, BUMP_OUT, BUMP_TT, 0.0
        init = "  f_htype = 1\n  fn_hinit = 'h0.txt'\n"
        probes = ""
    fn_probe = "  fn_record = '-'\n" if probes else ""
    if cfg == "bump":
        fn_probe += "  fn_boundary = '-'\n"
        enc_extra = "  p_diagratio = 0.0          ! 4 近傍(南北の壁の行で斜めの辺が欠ける影響を除き、1 次元にする)\n"
        bnd = "&list_bound_edge\n  f_bc_e = 1                 ! 東辺(下り)は自由流出\n/\n"
    else:
        enc_extra = ""
        bnd = ""
    with open(f"p_{name}.txt", "w") as f:
        f.write(f"""!======================================================================
! steepwave: ケース {name}(make_init.py が生成。構成の説明は make_init.py の先頭)
!======================================================================
&list_sysparam
  dt = {dt:g}
  t0 = 0
  tt = {tt:g}
  dt_disp = {tt:g}
  dt_file = {dfile:g}
  dt_recrd = {drec:g}
  fn_geoinfo = '-'
  fn_initial = '-'
  fn_enc = '-'
{fn_probe}  dir_data = 'd_{cfg}'
  dir_result = 'result_{name}'
  dir_save = 'save_{name}'
  f_state_save = 1
  f_out_h = 1
  f_out_u = 1
  f_out_v = 1
  f_check_cfl = 0
/
&list_enc
  f_gravity_correction = {gc}   ! 0: なし / 2: 有効重力 + 斜面に沿う摩擦(既定)/ 3: 2 + 水面の勾配の項の g′(§100)
{enc_extra}/
&list_initial
{init}/
&list_geoinfo
  nx = {nx}
  ny = {ny}
  dx = {dx:g}
  dy = {dx:g}
  f_ztype = 1
  fn_z = 'z.txt'
  f_rntype = 0
  rn0 = {rn:g}                ! マニングの粗度(wave・bump は摩擦なし)
/
{probes}{bnd}""")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        for cfg, gc in CASES:
            print(case_name(cfg, gc))
        return
    write_inputs()
    for cfg, gc in CASES:
        param(cfg, gc)


if __name__ == "__main__":
    main()
