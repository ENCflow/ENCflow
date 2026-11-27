#!/usr/bin/env python3
"""sliver: 幅が 0 に近いサブグリッド河道のセル(占有率で作った河道マスクの角をかすめる細片)が、そのセルの無い構成と
同じ流れになることの検定の入力と設定を生成する(developer.md §136)。

  python3 make_sliver.py          → d_<case>/(z・rn・mask・h0・rw・width・境界の表・kind・info)と p_<case>.txt
  python3 make_sliver.py list     → ケース名を 1 行に 1 つ書く(Run.sh 用)
  python3 make_sliver.py mpi      → Run_MPI.sh が N ランクと 1 ランクで比べるケース名

開口の動的な振り替え(f_opening_dynamic)は、辺の角のセルが計算の外なら塞がった開口として、その分の通過幅を辺へ
返す。サブグリッド河道幅のセルの流速は、周りの辺の幅キャップの平均(通水率)で割り戻す。角や隣に幅の極端に狭い
河道のセルがあると、「開いている」と数えて通過幅が返らず、通水率も下がって、河道の通水が落ちていた。比べる側の
セルの幅(面長で頭打ち)の 5 % 未満の幅のセルは、振り替えと通水率で計算の外と同じに数える(§136)。この検定は、
同じ河道に幅 0.01 m のセルを添えた構成(tiny)と添えない構成(none)で、河道の水位が一致することを確かめる
(Check_sliver.py)。

形(どれも Δx = 100 m、勾配 1/1000、粗度 0.03、河道の外は領域の外、3 時間):
  dg  45° の直線の河道を、1 列に 1 セル(8 連結)の解像したセル(幅 9999 m)で表す。tiny は斜めの段の角のセル
      (両側)を幅 0.01 m の河道のセルにする(斜めの辺の振り替え)。流量 300 m³/s(斜めの自然幅 70.7 m で
      等流水深 2.31 m)
  ax  格子の軸に沿う直線の河道を 2 行の解像したセル(幅 9999 m)で表す。tiny は片側(北)の 1 行を幅 0.01 m の
      河道のセルにする(軸の辺の振り替えと、隣の通水率)。流量 1,000 m³/s(幅 200 m で等流水深 2.54 m)
"""
import math, os, sys

S, RN, DX = 1.0 / 1000.0, 0.03, 100.0
Z0 = 20.0                          # 上流端の河床 (m)
WRES, WTINY = 9999.0, 0.01         # 解像したセルの幅・細片の幅 (m)
TT, DT_FILE = 10800.0, 3600.0      # 計算時間・出力間隔 (s)
CASES = [("dg_none", "dg", False), ("dg_tiny", "dg", True), ("ax_none", "ax", False), ("ax_tiny", "ax", True)]
MPI_CASES = ["dg_tiny", "ax_tiny"]


def hn(q):
    """マニングの等流水深(広い矩形断面。q は単位幅流量)"""
    return (RN * q / math.sqrt(S)) ** 0.6


def geom_dg(tiny):
    """45° の直線の河道(1 列に 1 セル)。北西の端から南東へ。kind: 1 河道、3 細片"""
    n = 40
    nx, ny = n, n + 2
    kind = [[0] * nx for _ in range(ny)]
    sal = [[0.0] * nx for _ in range(ny)]
    for i in range(nx):
        j = i + 1                                 # j = 0 が北端の行
        kind[j][i] = 1
    for i in range(nx - 1):                       # 段 (i, i+1) → (i+1, i+2) の角: (i+1, i+1) と (i, i+2)
        if tiny:
            kind[i + 1][i + 1] = 3
            kind[i + 2][i] = 3
    for j in range(ny):
        for i in range(nx):
            # 中心線に沿う距離(セルの中心を中心線へ投影。中心線は (0.5, 1.5) セルから南東へ)
            x, y = i + 0.5, j - 0.5
            sal[j][i] = min(max((x + y) / math.sqrt(2) * DX - 0.5 * math.sqrt(2) * DX, 0.0), (n - 1) * math.sqrt(2) * DX)
    return kind, sal, nx, ny, (n - 1) * math.sqrt(2) * DX


def geom_ax(tiny):
    """格子の軸に沿う直線の河道(2 行)。tiny は北側に細片の行を添える"""
    nx, ny = 40, 4
    kind = [[0] * nx for _ in range(ny)]
    sal = [[(i + 0.5) * DX for i in range(nx)] for _ in range(ny)]
    for i in range(nx):
        kind[1][i] = kind[2][i] = 1
        if tiny:
            kind[0][i] = 3
    return kind, sal, nx, ny, nx * DX


PARAM = """! test/sliver: {name}(make_sliver.py が生成。developer.md §136)
&list_sysparam
  f_gridsystem = 0
  dt = 2.0
  t0 = 0
  tt = {tt:.0f}
  dt_disp = {dtf:.0f}
  dt_file = {dtf:.0f}
  fn_geoinfo = '-'
  fn_enc = '-'
  fn_initial = '-'
  fn_boundary = '-'
  fn_channel = '-'
  dir_data = 'd_{name}'
  dir_result = 'result_{name}'
  f_out_h = 1
  f_out_e = 1
/
&list_initial
  f_htype = 1
  fn_hinit = 'h0.txt'
/
&list_enc
  f_exflux_reduction = 1
/
&list_geoinfo
  nx = {nx}
  ny = {ny}
  dx = {dx:.1f}
  dy = {dx:.1f}
  f_ztype = 1
  fn_z = 'z.txt'
  f_rntype = 1
  fn_rn = 'rn.txt'
  f_masktype = 1
  fn_mask = 'mask.txt'
  fn_rw = 'rw.txt'
/
&list_channel
  fn_width = 'width.txt'
/
&list_bound_stage
  fn_stage_cell(1) = 'cells_out.txt'
  fn_stage_val(1) = 'stage.txt'
/
&list_bound_inflow
  fn_inflow_cell(1) = 'cells_in.txt'
  fn_inflow_val(1) = 'q.txt'
  inflow_dist(1) = 2
/
"""


def write(path, rows, fmt):
    with open(path, "w") as f:
        for r in rows:
            f.write(" ".join(fmt % v for v in r) + "\n")


def gen_case(name, geo, tiny):
    if geo == "dg":
        kind, sal, nx, ny, L = geom_dg(tiny)
        q, chan_w = 300.0, DX / math.sqrt(2)
    else:
        kind, sal, nx, ny, L = geom_ax(tiny)
        q, chan_w = 1000.0, 2 * DX
    z = [[-9999.0] * nx for _ in range(ny)]
    h0 = [[0.0] * nx for _ in range(ny)]
    mask = [[1 if kind[j][i] > 0 else 0 for i in range(nx)] for j in range(ny)]
    for j in range(ny):
        for i in range(nx):
            if kind[j][i] > 0:
                z[j][i] = Z0 - S * sal[j][i]
                h0[j][i] = hn(q / chan_w)
    dd = f"d_{name}"
    os.makedirs(dd, exist_ok=True)
    write(os.path.join(dd, "z.txt"), z, "%.3f")
    write(os.path.join(dd, "rn.txt"), [[RN] * nx for _ in range(ny)], "%.3f")
    write(os.path.join(dd, "mask.txt"), mask, "%d")
    write(os.path.join(dd, "h0.txt"), h0, "%.3f")
    write(os.path.join(dd, "kind.txt"), kind, "%d")       # 1 河道・3 細片(判定用)
    write(os.path.join(dd, "rw.txt"), [[1 if kind[j][i] > 0 else 0 for i in range(nx)] for j in range(ny)], "%d")
    write(os.path.join(dd, "width.txt"), [[WRES if kind[j][i] == 1 else (WTINY if kind[j][i] == 3 else 0.0)
                                           for i in range(nx)] for j in range(ny)], "%.2f")
    jin = [j for j in range(ny) if kind[j][0] == 1]
    jout = [j for j in range(ny) if kind[j][nx - 1] == 1]
    with open(os.path.join(dd, "cells_in.txt"), "w") as f:
        f.writelines(f"1 {j + 1}\n" for j in jin)
    with open(os.path.join(dd, "cells_out.txt"), "w") as f:
        f.writelines(f"{nx} {j + 1}\n" for j in jout)
    eta = sum(z[j][nx - 1] for j in jout) / len(jout) + hn(q / chan_w)
    with open(os.path.join(dd, "stage.txt"), "w") as f:
        f.write(f"0 {eta:.4f}\n1440 {eta:.4f}\n")
    with open(os.path.join(dd, "q.txt"), "w") as f:
        f.write(f"0 {q:.1f}\n1440 {q:.1f}\n")
    with open(os.path.join(dd, "info.txt"), "w") as f:
        f.write(f"geo {geo}\ntiny {int(tiny)}\nq {q}\nchan_w {chan_w}\nL {L}\nnx {nx}\nny {ny}\n")
    with open(f"p_{name}.txt", "w") as f:
        f.write(PARAM.format(name=name, tt=TT, dtf=DT_FILE, nx=nx, ny=ny, dx=DX))


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        print("\n".join(c[0] for c in CASES))
        return
    if len(sys.argv) > 1 and sys.argv[1] == "mpi":
        print("\n".join(MPI_CASES))
        return
    for name, geo, tiny in CASES:
        gen_case(name, geo, tiny)


if __name__ == "__main__":
    main()
