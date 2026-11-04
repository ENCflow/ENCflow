#!/usr/bin/env python3
"""test/dbonset の入力と設定ファイルの生成(Run.sh・Run_MPI.sh が呼ぶ)。

一様な斜面(勾配 G、下り向きが格子の x 軸から角度 θ)を 60 m 四方の壁で囲み、全面に厚さ D の
崩壊深を与えて計算開始と同時に流動化する(fn_dbinit、db_relsat = 1 で混合体の濃度 C = C*)。
河床との交換なし(f_dbed = 0)・クーロン + Manning 合成(f_dbres = 1)。壁から離れた内部は
一様な層の剛体の滑りになり、降伏減速度 a_y = g_e tanφ sC/(1 + sC) と斜面の駆動 g_e G から
  G < μ なら静止、G > μ なら V(t) = g_e (G − μ) t(μ = tanφ sC/(1 + sC))
になる。急勾配の重力補正(f_gravity_correction)なしの構成(g_e = g。降伏の静止判定だけを
切り分ける。developer.md §28.16)と、ありの構成(名前の末尾 _gc。g_e = g cos²θ = g/(1 + G²)。
補正の cos²θ が辺の向きによらないこと。§91)を同じ斜面で回す。時間刻みは、降伏の摩擦を半陰的に
入れることによる立ち上がりの遅れ(時間刻みに比例)が解析解との比較に効かない小ささにする。
定数は Check_dbonset.py と対。

同じ斜面(8 近傍)で、斜面安定判定(f_slide = 2。判定のみで流動化しない)の安全率も求める(名前の
末尾 _fs)。c' = 0・地下水なし(h_w = 0)では Fs = tanφs/tanθ で、tanθ は最急勾配(D∞。
developer.md §92)。流れは起こさない(初期水深 0、崩壊深なし)。

  python3 make_init.py        全ケースの d_<斜面>/(z.txt, dbinit.txt, sd.txt)と p_<case>.txt を書く
  python3 make_init.py list   ケース名を 1 行ずつ出す
"""
import math
import os
import sys

L, DX = 60.0, 1.0            # 領域の一辺、格子間隔 (m)
D = 1.0                      # 層の厚さ(崩壊深。かさ)(m)
TANPHI = math.tan(math.radians(35.0))
SGRAV, POROSITY = 1.65, 0.4
CSTAR = 1.0 - POROSITY
MU = TANPHI * SGRAV * CSTAR / (1.0 + SGRAV * CSTAR)   # a_y/g_e(C = C*)
RATIOS = (0.9, 1.1, 1.3)     # G/(a_y/g_e)
THETAS = (0.0, 22.5, 45.0)   # 下り向きの格子の x 軸からの角度 (deg)
NBS = (8, 4)                 # 近傍の数(4 は p_diagratio = 0)
GCS = (0, 1)                 # 急勾配の重力補正 f_gravity_correction(1 の構成は名前の末尾に _gc)
DT, TT = 0.0005, 2.0         # 時間刻み・計算時間 (s)。dt = 0.01 s では半陰的な摩擦の立ち上がりの
                             #   遅れで速さが解析解の 0.8 倍、0.002 s で 0.96 倍、0.0005 s で 0.995 倍
RN = 0.01                    # マニングの粗度(内部の剛体の滑りに効かない小さな値)
FS_PHI = 30.0                # 斜面安定判定のせん断抵抗角 φs (deg)。c' = 0 で Fs = tanφs/tanθ
FS_DT, FS_TT = 0.1, 1.0      # 安全率の構成の時間刻み・計算時間 (s)(流れがないので短く)


def case_name(ratio, theta, nb, gc=0):
    return f"r{ratio:g}_t{theta:g}_n{nb}".replace(".", "p") + ("_gc" if gc else "")


CASES = [(r, t, n, gc) for gc in GCS for r in RATIOS for t in THETAS for n in NBS]
CASES_FS = [(r, t) for r in RATIOS for t in THETAS]


def fs_name(ratio, theta):
    return f"r{ratio:g}_t{theta:g}_fs".replace(".", "p")


def gacc(ratio, gc, gg=9.8):
    """有効重力 g_e(重力補正ありは g cos²θ = g/(1 + G²)。G は斜面の勾配)。"""
    g = ratio * MU
    return gg / (1.0 + g * g) if gc else gg


def write_case(ratio, theta, nb, gc):
    name = case_name(ratio, theta, nb, gc)
    n = int(round(L / DX))
    g = ratio * MU
    th = math.radians(theta)
    ddir = f"d_{case_name(ratio, theta, nb)}"          # 地形は重力補正の有無で共通
    os.makedirs(ddir, exist_ok=True)
    rows_z, rows_d, rows_s = [], [], []
    for j in reversed(range(n)):                  # 先頭行が北端
        y = (j + 0.5) * DX
        rz, rd, rs = [], [], []
        for i in range(n):
            x = (i + 0.5) * DX
            z = 100.0 - g * (x * math.cos(th) + y * math.sin(th))
            rz.append(f"{z:.8f}")
            rd.append(f"{D:.4f}")
            rs.append(f"{D:.4f}")
        rows_z.append(" ".join(rz))
        rows_d.append(" ".join(rd))
        rows_s.append(" ".join(rs))
    for fn, rows in (("z.txt", rows_z), ("dbinit.txt", rows_d), ("sd.txt", rows_s)):
        with open(os.path.join(ddir, fn), "w") as f:
            f.write("\n".join(rows) + "\n")
    pd = "0.5857864376" if nb == 8 else "0.0"
    gcnote = "あり(cos²θ が辺の向きによらないこと。§91)" if gc else "なし(降伏の静止判定だけを切り分ける。§28.16)"
    with open(f"p_{name}.txt", "w") as f:
        f.write(f"""!======================================================================
! dbonset: ケース {name}(make_init.py が生成)
!   一様な斜面(勾配 {g:.6f} = {ratio:g} × tanφ sC/(1+sC)、下り向き {theta:g}°)の全面に厚さ {D:g} m の
!   崩壊深を与えて流動化し、{TT:g} 秒後の内部の速さを剛体の滑りの解析解と比べる(Check_dbonset.py)
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
  dir_data = '{ddir}'
  dir_result = 'result_{name}'
  dir_save = 'save_{name}'
  f_state_save = 1
  f_out_hs = 1
  f_out_u = 1
  f_out_v = 1
/
&list_enc
  f_gravity_correction = {gc}   ! 急勾配の重力補正 {gcnote}
  p_diagratio = {pd}       ! 8 近傍(既定)/ 4 近傍(0)
/
&list_initial
  f_htype = 0
  h0 = 0.0
/
&list_geoinfo
  lx = {n * DX:g}
  ly = {n * DX:g}
  nx = {n}
  ny = {n}
  f_ztype = 1
  fn_z = 'z.txt'
  f_rntype = 0
  rn0 = {RN:g}
  f_sdtype = 1
  fn_sd = 'sd.txt'
  sy0 = {POROSITY:g}
/
&list_geomorph
  dt_geomorph = 0.0
  morfac = 1.0
  f_debris = 1
  f_dbed = 0                 ! 河床との交換なし(濃度 C = C* が保たれる)
  f_dbres = 1                ! クーロン + マニング合成(a_y = g_e tanφ sC/(1+sC))
  db_phi = 35.0
  f_dbstop = 0
  db_vstop = 0.05
  fluv_porosity = {POROSITY:g}
  fn_dbinit = 'dbinit.txt'
  db_reltime = 0.0
  db_relsat = 1.0            ! 間隙水 λD(混合体の濃度 C = C* = {CSTAR:g})
/
""")
    return name


def write_fs(ratio, theta):
    """斜面安定判定(f_slide = 2)の安全率の構成。地形は降伏の構成(8 近傍)と共通。"""
    name = fs_name(ratio, theta)
    n = int(round(L / DX))
    g = ratio * MU
    ddir = f"d_{case_name(ratio, theta, 8)}"
    if not os.path.isdir(ddir):
        write_case(ratio, theta, 8, 0)
    with open(f"p_{name}.txt", "w") as f:
        f.write(f"""!======================================================================
! dbonset: ケース {name}(make_init.py が生成)
!   一様な斜面(勾配 {g:.6f}、下り向き {theta:g}°)で、斜面安定判定(f_slide = 2。判定のみ)の安全率を
!   求め、Fs = tanφs/tanθ(c' = 0、地下水なし)と比べる(Check_dbonset.py の (5))。流れは起こさない
!======================================================================
&list_sysparam
  dt = {FS_DT:g}
  t0 = 0
  tt = {FS_TT:g}
  dt_disp = {FS_TT:g}
  dt_file = {FS_TT:g}
  dt_recrd = {FS_TT:g}
  fn_geoinfo = '-'
  fn_initial = '-'
  fn_enc = '-'
  fn_geomorph = '-'
  dir_data = '{ddir}'
  dir_result = 'result_{name}'
  dir_save = 'save_{name}'
  f_state_save = 1
  f_out_fs = 1
/
&list_enc
/
&list_initial
  f_htype = 0
  h0 = 0.0
/
&list_geoinfo
  lx = {n * DX:g}
  ly = {n * DX:g}
  nx = {n}
  ny = {n}
  f_ztype = 1
  fn_z = 'z.txt'
  f_rntype = 0
  rn0 = {RN:g}
  f_sdtype = 1
  fn_sd = 'sd.txt'
  sy0 = {POROSITY:g}
/
&list_geomorph
  dt_geomorph = 0.0
  morfac = 1.0
  f_debris = 1
  f_dbed = 0
  f_dbres = 1
  db_phi = 35.0
  f_dbstop = 0
  fluv_porosity = {POROSITY:g}
  f_slide = 2                ! 判定のみ(流動化しない)
  slide_c = 0.0              ! 有効粘着力 c' = 0 → Fs = tanφs/tanθ(地下水なし)
  slide_phi = {FS_PHI:g}
/
""")
    return name


def main():
    if sys.argv[1:] == ["list"]:
        for c in CASES:
            print(case_name(*c))
        for c in CASES_FS:
            print(fs_name(*c))
        return
    for c in CASES:
        write_case(*c)
    for c in CASES_FS:
        write_fs(*c)


if __name__ == "__main__":
    main()
