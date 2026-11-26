#!/usr/bin/env python3
"""wallpond: 河道の堤防の仮想壁面(fn_bank)の向こうの湛水が、河道の流れを変えないことの検定の入力と設定を生成する。

  python3 make_wallpond.py          → d_<case>/(z・rn・mask・h0・rw・width・bank・境界の表・kind・info)と p_<case>.txt
  python3 make_wallpond.py list     → ケース名を 1 行に 1 つ書く(Run.sh 用)
  python3 make_wallpond.py mpi      → Run_MPI.sh が N ランクと 1 ランクで比べるケース名

移流項は、隣のセルの状態を読む判定(流向面の風上の供給元・側方面の平行リンク・斜めエッジの開口率・屈曲の規則の
供給元・スキーム 1 のセル中心の勾配)で、河道の堤防の仮想壁面の向こうのセルを、濡れていても乾いたセルと同じに数えない
(developer.md §134)。この検定は、同じ河道で堤内地を「乾いている」と「水平な地盤に静かに湛水している」の 2 通りにして、
河道の水位が一致することを確かめる(Check_wallpond.py)。

形(どれも Δx = 100 m、勾配 1/1000、粗度 0.03、河道の両側に幅 300 m の堤内地、3 時間):
  ax2  格子の軸に沿う直線の河道を 2 セル(幅 200 m)の解像した河道で表す。流量 1,000 m³/s(等流水深 2.55 m)。
       堤内地を計算しない構成(mask)と、1 セルの解像した堤防の向こうに湛水する構成(levee_wet)も回す
  ax1  同じ河道を 1 セルのサブグリッド河道(幅 80 m)で表す。流量 1,000 m³/s(等流水深 4.41 m)
  dg1  45° の直線の河道を 4 連結の 1 セルの階段(解像。tutorials/chichibu の河道マスクと同じ型)で表す。
       流量 300 m³/s。移流項の規則の組み合わせを 3 つ(既定の 4・2・2・4、3・1・0・3、0・1・0・3。値は
       f_advection_donor・f_advection_bend・f_advection_lateral・f_dry_head_cap の順)と、スキーム 1(セル中心勾配)で回す
堤内地は水平(地盤 = 区間の中ほどの河床 + 1 m)。湛水は水深 1.5 m の静かな池。堤防の天端は河床 + 10 m(越流しない)。
"""
import math, os, sys

S, RN, DX = 1.0 / 1000.0, 0.03, 100.0
Z0 = 20.0                          # 上流端の河床 (m)
B = 300.0                          # 片側の堤内地の幅(河道の縁から。m)
HP = 1.5                           # 湛水の深さ (m)
CREST = 10.0                       # 堤防の天端の高さ(河床から。m)
TT, DT_FILE = 10800.0, 3600.0      # 計算時間・出力間隔 (s)
# 移流項の構成: 名前、f_advection_scheme、f_advection_donor、f_advection_bend、f_advection_lateral、f_dry_head_cap
OPTS = {"o4": (3, 4, 2, 2, 4), "o3l0": (3, 3, 1, 0, 3), "o0": (3, 0, 1, 0, 3), "s1": (1, 4, 2, 2, 4)}
# ケース: 名前、形、堤内地、構成
CASES = [("ax2_mask", "ax2", "mask", "o4"), ("ax2_dry", "ax2", "dry", "o4"), ("ax2_wet", "ax2", "wet", "o4"),
         ("ax2_levee", "ax2", "levee", "o4"),
         ("ax1_dry", "ax1", "dry", "o4"), ("ax1_wet", "ax1", "wet", "o4")]
for o in OPTS:
    CASES += [(f"dg1_{o}_dry", "dg1", "dry", o), (f"dg1_{o}_wet", "dg1", "wet", o)]
MPI_CASES = ["ax2_wet", "ax1_wet", "dg1_o4_wet", "dg1_s1_wet"]


def hn(q):
    """マニングの等流水深(広い矩形断面。q は単位幅流量)"""
    return (RN * q / math.sqrt(S)) ** 0.6


def geom_axis(nch, var):
    """格子の軸に沿う直線の河道。nch = 河道のセル数(2: 解像 200 m、1: サブグリッド 80 m)。
    戻り値: z・種類(1 河道・2 解像した堤防・5 堤内地)・沿う距離・領域の大きさ"""
    L = 4000.0
    nfp = int(round(B / DX))                      # 河道の縁から 300 m
    nlev = 1 if var == "levee" else 0
    ny = 1 + nfp + nlev + nch + nlev + nfp + 1
    nx = int(L / DX)
    kind = [[0] * nx for _ in range(ny)]
    sal = [[(i + 0.5) * DX for i in range(nx)] for _ in range(ny)]
    j0 = 1 + nfp + nlev
    for j in range(ny):
        for i in range(nx):
            if j0 <= j < j0 + nch:
                kind[j][i] = 1
            elif nlev and j in (j0 - 1, j0 + nch):
                kind[j][i] = 2
            elif 1 <= j < ny - 1:
                kind[j][i] = 5
    return kind, sal, nx, ny, L


def geom_diag(var):
    """45° の直線の河道(4 連結の 1 セルの階段)。中心線は西端から南東へ東端まで"""
    n = 40
    w = DX * (math.cos(math.pi / 4) + math.sin(math.pi / 4))      # 4 連結の 1 セルの帯の幅
    m = int(math.ceil((B + w / 2) * math.sqrt(2) / DX)) + 2
    nx, ny = n, n + 2 * m
    x0, y0 = 0.0, -(m + 0.5) * DX
    ux, uy = 1 / math.sqrt(2), -1 / math.sqrt(2)
    L = n * DX * math.sqrt(2)
    kind = [[0] * nx for _ in range(ny)]
    sal = [[0.0] * nx for _ in range(ny)]
    for j in range(ny):                           # j = 0 が北端の行
        for i in range(nx):
            x, y = (i + 0.5) * DX, -(j + 0.5) * DX
            t = (x - x0) * ux + (y - y0) * uy
            d = -(x - x0) * uy + (y - y0) * ux
            sal[j][i] = min(max(t, 0.0), L)
            if -w / 2 < d <= w / 2:
                kind[j][i] = 1
            elif abs(d) <= w / 2 + B:
                kind[j][i] = 5
    return kind, sal, nx, ny, L


PARAM = """! test/wallpond: {name}(make_wallpond.py が生成。developer.md §134)
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
{chan_fn}  dir_data = 'd_{name}'
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
  f_advection_scheme = {sch}
  f_advection_donor = {don}
  f_advection_bend = {bend}
  f_advection_lateral = {lat}
  f_dry_head_cap = {cap}
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
{rw}/
{channel}&list_bound_stage
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


def gen_case(name, geo, var, opt):
    if geo == "dg1":
        kind, sal, nx, ny, L = geom_diag(var)
        q, width = 300.0, None
    else:
        kind, sal, nx, ny, L = geom_axis(2 if geo == "ax2" else 1, var)
        q, width = 1000.0, (None if geo == "ax2" else 80.0)
    zfp = Z0 - S * L / 2 + 1.0                    # 堤内地の地盤(水平)
    z = [[-9999.0] * nx for _ in range(ny)]
    h0 = [[0.0] * nx for _ in range(ny)]
    mask = [[0] * nx for _ in range(ny)]
    chan_w = width if width else (200.0 if geo == "ax2" else DX)
    for j in range(ny):
        for i in range(nx):
            k = kind[j][i]
            zb = Z0 - S * sal[j][i]
            if k == 1:
                z[j][i] = zb
                h0[j][i] = hn(q / chan_w)
            elif k == 2:
                z[j][i] = zb + CREST                  # 解像した堤防(セルの地盤を天端の高さに)
            elif k == 5:
                z[j][i] = zfp
                if var in ("wet", "levee"):
                    h0[j][i] = HP
            if k > 0 and not (var == "mask" and k == 5):
                mask[j][i] = 1
    walls = var in ("dry", "wet")
    chan_model = walls or width is not None
    dd = f"d_{name}"
    os.makedirs(dd, exist_ok=True)
    write(os.path.join(dd, "z.txt"), z, "%.3f")
    write(os.path.join(dd, "rn.txt"), [[RN] * nx for _ in range(ny)], "%.3f")
    write(os.path.join(dd, "mask.txt"), mask, "%d")
    write(os.path.join(dd, "h0.txt"), h0, "%.3f")
    write(os.path.join(dd, "kind.txt"), kind, "%d")      # 1 河道・2 解像した堤防・5 堤内地(判定用)
    if chan_model:
        write(os.path.join(dd, "rw.txt"), [[1 if kind[j][i] == 1 else 0 for i in range(nx)] for j in range(ny)], "%d")
        write(os.path.join(dd, "width.txt"), [[(width if width else 9999.0) if kind[j][i] == 1 else 0.0
                                               for i in range(nx)] for j in range(ny)], "%.1f")
        write(os.path.join(dd, "bank.txt"), [[Z0 - S * sal[j][i] + CREST if (kind[j][i] == 1 and walls) else -9999.0
                                              for i in range(nx)] for j in range(ny)], "%.3f")
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
        f.write(f"geo {geo}\nvar {var}\nq {q}\nchan_w {chan_w}\nzfp {zfp}\nhp {HP}\nnx {nx}\nny {ny}\n")
    sch, don, bend, lat, cap = OPTS[opt]
    bank = "  fn_bank = 'bank.txt'\n  f_bank_datum = 2\n" if walls else ""
    channel = f"&list_channel\n{bank}  fn_width = 'width.txt'\n/\n" if chan_model else ""
    with open(f"p_{name}.txt", "w") as f:
        f.write(PARAM.format(name=name, tt=TT, dtf=DT_FILE, sch=sch, don=don, bend=bend, lat=lat, cap=cap,
                             chan_fn="  fn_channel = '-'\n" if chan_model else "", nx=nx, ny=ny, dx=DX,
                             rw="  fn_rw = 'rw.txt'\n" if chan_model else "", channel=channel))


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        print("\n".join(c[0] for c in CASES))
        return
    if len(sys.argv) > 1 and sys.argv[1] == "mpi":
        print("\n".join(MPI_CASES))
        return
    for name, geo, var, opt in CASES:
        gen_case(name, geo, var, opt)


if __name__ == "__main__":
    main()
