#!/usr/bin/env python3
# examples/confluence_backwater の補足「合流の形と水位」の入力生成(data/ と param_*.txt を書く。make が呼ぶ)
#   背水の弱い定常の流れで、合流角と湾曲部の外岸・内岸による水位の違いを見る。岸は河床 + 10 m の高台で、
#   水はあふれない。本川の下流端は等流水深の水位、上流端は区間流入。
#   合流角(Δx = 10 m、2 h): 本川は幅 100 m・東へ勾配 1/1000、支川は幅 50 m・勾配 1/1000(軸に沿って)、n = 0.03。
#     角度 = 本川の流向(東)と支川の流向のなす角。90: 支川は南へ、45: 南東へ(北西から。鋭角)、
#     135: 南西へ(北東から。本川に逆らう向き)。流量比 a = 本川 600・支川 400、b = 本川 300・支川 700 m3/s
#   格子の確認(Δx = 5 m、1.5 h): 合流角 90・135 の流量比 a
#   湾曲(Δx = 10 m、2 h): 本川は幅 100 m、東へ 1 km → 半径 300 m の 90° の右曲がり → 南へ 1.5 km。
#     支川(幅 40 m)が湾曲の頂点に放射方向から合流する。outer = 北東から(外岸)、inner = 南西から(内岸)、
#     none = 支川なし。本川 900・支川 100 m3/s(none は本川 1,000)
#   python3 make_junction.py
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
S0, RN = 1.0e-3, 0.03
BANK, Z0 = 10.0, 10.0


def hn(q):
    """広い矩形(R = h)の Manning の等流水深"""
    return (RN * q / math.sqrt(S0)) ** 0.6


def wmat(path, a, fmt):
    with open(path, "w") as f:
        for row in a:
            f.write(" ".join(fmt % v for v in row) + "\n")


# ---------------------------------------------------------------- 合流角
BM, BT = 100.0, 50.0


def angle_geom(dx):
    nx, ny = int(3600 / dx), int(1350 / dx)
    j0, ij = int(1200 / dx), int(1500 / dx)     # 本川の北岸の行、合流点の x のセル番号
    return nx, ny, j0, ij


def angle_build(dx, theta, qm, qt):
    nx, ny, j0, ij = angle_geom(dx)
    nb = int(BM / dx)
    xj, ym0 = (ij - 0.5) * dx, j0 * dx
    d = {90: (0.0, -1.0), 45: (-1 / math.sqrt(2), -1 / math.sqrt(2)), 135: (1 / math.sqrt(2), -1 / math.sqrt(2))}[theta]
    z = [[0.0] * nx for _ in range(ny)]
    h = [[0.0] * nx for _ in range(ny)]
    kind = [[0] * nx for _ in range(ny)]
    for j in range(1, ny + 1):
        yy = (j - 0.5) * dx                      # 北端から南向きに測る
        for i in range(1, nx + 1):
            x = (i - 0.5) * dx
            zm = Z0 - S0 * x
            if j0 < j <= j0 + nb:
                z[j-1][i-1] = zm
                kind[j-1][i-1] = 1
                h[j-1][i-1] = hn((qm if x < xj else qm + qt) / BM)
                continue
            z[j-1][i-1] = zm + BANK + S0 * max(0.0, ym0 - yy)
            if j > j0:
                continue
            px, py = x - xj, yy - ym0
            s = px * d[0] + py * d[1]
            dist = abs(px * d[1] - py * d[0])
            if s >= -BT and dist <= BT / 2 + 1e-6:
                z[j-1][i-1] = Z0 - S0 * xj + S0 * max(s, 0.0)
                kind[j-1][i-1] = 2
                h[j-1][i-1] = hn(qt / BT)
    return z, h, kind


# ---------------------------------------------------------------- 湾曲
BB, BTB, RB = 100.0, 40.0, 300.0
XC, YC = 1000.0, 1500.0


def bend_geom():
    return 175, 215, 10.0


def bend_s(x, y):
    """本川の中心線に沿う距離と、中心線からの符号付き距離(外岸側が正)。本川の範囲外は None"""
    if x <= XC and y >= YC:
        return x, y - (YC + RB)
    if x >= XC and y <= YC:
        return XC + RB * math.pi / 2 + (YC - y), x - (XC + RB)
    r = math.hypot(x - XC, y - YC)
    phi = math.atan2(y - YC, x - XC)
    if 0 <= phi <= math.pi / 2:
        return XC + RB * (math.pi / 2 - phi), r - RB
    return None


def bend_build(kind_t, qm, qt):
    nx, ny, dx = bend_geom()
    z = [[0.0] * nx for _ in range(ny)]
    h = [[0.0] * nx for _ in range(ny)]
    kind = [[0] * nx for _ in range(ny)]
    ur = (math.cos(math.pi / 4), math.sin(math.pi / 4))
    ax, ay = XC + RB * ur[0], YC + RB * ur[1]            # 湾曲の頂点
    s_apex = XC + RB * math.pi / 4
    for j in range(1, ny + 1):
        y = (ny - j + 0.5) * dx
        for i in range(1, nx + 1):
            x = (i - 0.5) * dx
            c = bend_s(x, y)
            if c is not None and abs(c[1]) <= BB / 2:
                z[j-1][i-1] = Z0 - S0 * c[0]
                h[j-1][i-1] = hn((qm if c[0] < s_apex else qm + qt) / BB)
                kind[j-1][i-1] = 1
                continue
            phi = math.atan2(y - YC, x - XC)
            if x <= XC and y >= YC:
                s = x
            elif y <= YC and x >= XC:
                s = XC + RB * math.pi / 2 + (YC - y)
            elif 0 <= phi <= math.pi / 2:
                s = XC + RB * (math.pi / 2 - phi)
            else:
                s = s_apex
            z[j-1][i-1] = Z0 - S0 * s + BANK
            if kind_t == "none":
                continue
            d = ur if kind_t == "outer" else (-ur[0], -ur[1])
            px, py = x - ax, y - ay
            st = px * d[0] + py * d[1] - BB / 2
            dist = abs(px * d[1] - py * d[0])
            if -BB / 2 <= st <= 2000.0 and dist <= BTB / 2 + 1e-6:
                z[j-1][i-1] = Z0 - S0 * s_apex + S0 * max(st, 0.0)
                h[j-1][i-1] = hn(qt / BTB)
                kind[j-1][i-1] = 2
    return z, h, kind


# ---------------------------------------------------------------- 設定ファイル
PARAM = """!======================================================================
! confluence_backwater 補足「合流の形と水位」: {title}
!   背水の弱い定常の流れ(岸は河床 + 10 m の高台で、水はあふれない)。入力は make_junction.py が data/ に作る
!======================================================================
&list_sysparam
  f_gridsystem = 0
  dt = {dt}
  t0 = 0
  tt_c = '{tt}'
  dt_disp_c = '30m'
  dt_file_c = '30m'         ! 最後の 2 つの出力で定常を確かめる
  dt_recrd_c = '10m'
  fn_geoinfo = '-'
  fn_initial = '-'
  fn_boundary = '-'
  dir_data = 'data'
  dir_result = 'result_{name}'
  f_out_h = 1
  f_out_e = 1
  f_out_u = 1
  f_out_v = 1
/
&list_initial
  f_htype = 1
  fn_hinit = 'h_{name}.txt' ! 流量に合う等流水深
/
&list_geoinfo
  nx = {nx}
  ny = {ny}
  dx = {dx}
  dy = {dx}
  f_ztype = 1
  fn_z = 'z_{name}.txt'
  f_rntype = 0
  rn0 = {rn}
/
&list_bound_stage
{stage}/
&list_bound_inflow
{inflow}/
"""


def cells_list(prefix, n, cells):
    return "".join(f"  {prefix}(:,{k},{n}) = {i}, {j}\n" for k, (i, j) in enumerate(cells, 1))


def write_case(name, title, dt, tt, nx, ny, dx, z, h, kind, main_in, out_cells, eta, q_main, trib_in, q_trib):
    ddir = os.path.join(HERE, "data")
    os.makedirs(ddir, exist_ok=True)
    wmat(os.path.join(ddir, f"z_{name}.txt"), z, "%.4f")
    wmat(os.path.join(ddir, f"h_{name}.txt"), h, "%.4f")
    wmat(os.path.join(ddir, f"k_{name}.txt"), kind, "%d")
    stage = cells_list("stage_cell", 1, out_cells) + f"  stage_eta(1) = {eta:.4f}  ! 下流端の等流水深の水位\n"
    inflow = cells_list("inflow_cell", 1, main_in) + f"  inflow_val(:,1,1) = 0, {q_main:.1f}   ! 本川\n" \
        f"  inflow_val(:,2,1) = 999, {q_main:.1f}\n  inflow_dist(1) = 0\n"
    if q_trib > 0:
        inflow += cells_list("inflow_cell", 2, trib_in) + f"  inflow_val(:,1,2) = 0, {q_trib:.1f}   ! 支川\n" \
            f"  inflow_val(:,2,2) = 999, {q_trib:.1f}\n  inflow_dist(2) = 0\n"
    with open(os.path.join(HERE, f"param_{name}.txt"), "w") as f:
        f.write(PARAM.format(title=title, dt=dt, tt=tt, name=name, nx=nx, ny=ny, dx=dx, rn=RN, stage=stage, inflow=inflow))


def main():
    for dx, tag, cases, tt, dt in ((10.0, "", (("a", 600.0, 400.0), ("b", 300.0, 700.0)), "2h", "0.5"),
                                   (5.0, "f", (("a", 600.0, 400.0),), "90m", "0.25")):
        nx, ny, j0, ij = angle_geom(dx)
        nb = int(BM / dx)
        for rtag, qm, qt in cases:
            for th in ((45, 90, 135) if dx == 10.0 else (90, 135)):
                name = f"{tag}{rtag}{th}"
                z, h, kind = angle_build(dx, th, qm, qt)
                rows = range(j0 + 1, j0 + nb + 1)
                eta = Z0 - S0 * (nx - 0.5) * dx + hn((qm + qt) / BM)
                tcells = [(i, 1) for i in range(1, nx + 1) if kind[0][i-1] == 2]
                title = f"合流角 {th}°(Δx = {dx:g} m。本川 {qm:.0f}・支川 {qt:.0f} m3/s)"
                write_case(name, title, dt, tt, nx, ny, dx, z, h, kind, [(1, j) for j in rows],
                           [(nx, j) for j in rows], eta, qm, tcells, qt)
                print("wrote", name)
    nx, ny, dx = bend_geom()
    for name, qm, qt in (("bend_none", 1000.0, 0.0), ("bend_outer", 900.0, 100.0), ("bend_inner", 900.0, 100.0)):
        z, h, kind = bend_build(name.split("_")[1], qm, qt)
        out_cells = [(i, ny) for i in range(1, nx + 1) if kind[ny-1][i-1] == 1]
        s_end = XC + RB * math.pi / 2 + (YC - 0.5 * dx)
        eta = Z0 - S0 * s_end + hn((qm + qt) / BB)
        main_in = [(1, j) for j in range(1, ny + 1) if kind[j-1][0] == 1]
        edge = []
        for i in range(1, nx + 1):
            if kind[0][i-1] == 2:
                edge.append((i, 1))
            if kind[ny-1][i-1] == 2:
                edge.append((i, ny))
        for j in range(1, ny + 1):
            if kind[j-1][0] == 2:
                edge.append((1, j))
            if kind[j-1][nx-1] == 2:
                edge.append((nx, j))
        title = {"bend_none": "湾曲(支川なし。本川 1,000 m3/s)", "bend_outer": "湾曲の外岸に支川が合流(本川 900・支川 100 m3/s)",
                 "bend_inner": "湾曲の内岸に支川が合流(本川 900・支川 100 m3/s)"}[name]
        write_case(name, title, "0.5", "2h", nx, ny, dx, z, h, kind, main_in, out_cells, eta, qm, edge, qt)
        print("wrote", name)


if __name__ == "__main__":
    main()
