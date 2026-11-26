#!/usr/bin/env python3
# examples/confluence_backwater の補足 1「粗い格子」の切り分け(data_*/ と param_*.txt を書く。make coarse_check が呼ぶ)
#   本川 2,800 m3/s(と支川 300 m3/s)の一定の流量を 4 h 流した定常で、合流点の位置の本川の水位を、細かい格子(Δx = 20 m)・
#   粗い格子(Δx = 100 m)・1 次元の漸変流の式で比べる。本川の形(湾曲・狭窄部の有無)と、粗い格子での狭窄部の表し方を変える。
#   粗い格子の湾曲部の段を太らせた版(make_coarse.py の THICK = 2。隣り合う列が中心線に近い 2 行を共有する)も計算する。
#   地形は本編の make_terrain.py・make_coarse.py の式で作る。計算するのは本川の河道(細かい格子は本川の堤防を含む)と支川の
#   河道だけで、堤内地は計算しない(水はあふれない)。下流端は流量の和の等流水深の水位、上流端は区間流入
#   python3 make_check.py          入力(data_*/)と設定ファイル(param_*.txt)を書く
#   python3 make_check.py table    計算の後に数表を書く(引数 en を足すと英語)
import math
import os
import sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import make_terrain as m
import make_coarse as mc

Q_MAIN, Q_TRIB = 2800.0, 300.0
# 本川の形: (名前, 湾曲の振幅 AM (m), 狭窄部の幅 BC (m), 支川の流量 (m3/s))
SHAPES = [("uniform", 0.0, m.BM, 0.0), ("constr", 0.0, m.BC, 0.0), ("bend", m.AM, m.BM, 0.0),
          ("base", m.AM, m.BC, 0.0), ("trib", m.AM, m.BC, Q_TRIB)]
SHAPE = {s[0]: s for s in SHAPES}
# 計算: (名前, 本川の形, 格子, 粗い格子の狭窄部の表し方, 湾曲部の段を太らせる行数 THICK)。粗い格子の既定は本編と同じ
# mix・THICK = 0
RUNS = ([(f"f_{s[0]}", s[0], "fine", None, 0) for s in SHAPES] + [(f"c_{s[0]}", s[0], "coarse", "mix", 0) for s in SHAPES]
        + [(f"c_constr_{r}", "constr", "coarse", r, 0) for r in ("round", "split", "full")]
        + [(f"c_{s}_k2", s, "coarse", "mix", 2) for s in ("bend", "base", "trib")])
EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


def setup(shape):
    _, am, bc, _ = SHAPE[shape]
    m.AM, m.BC = am, bc
    m.geometry()


PARAM = """!======================================================================
! confluence_backwater 補足 1 の切り分け: {title}
!   本川 {qm:,.0f} m3/s{trib_txt} の一定の流量を 4 h 流した定常。計算するのは河道だけ(あふれない)。
!   入力は make_check.py が data_{name}/ に作る。数表は python3 make_check.py table
!======================================================================
&list_sysparam
  f_gridsystem = 0
  dt = {dt}
  t0 = 0
  tt_c = '4h'
  dt_disp_c = '1h'
  dt_file_c = '1h'          ! 最後の 2 つの出力で定常を確かめる
  fn_geoinfo = '-'
  fn_enc = '-'
  fn_initial = '-'
  fn_boundary = '-'
{chan_fn}  dir_data = 'data_{name}'
  dir_result = 'result_{name}'
  f_out_h = 1
  f_out_e = 1
/

&list_initial
  f_htype = 1
  fn_hinit = 'h0.txt'       ! 流量に合う等流水深
/

&list_enc
  f_exflux_reduction = 1
/

&list_geoinfo
  nx = {nx}
  ny = {ny}
  dx = {dx}
  dy = {dx}
  f_ztype = 1
  fn_z = 'z.txt'
  f_rntype = 1
  fn_rn = 'rn.txt'
  f_masktype = 1
  fn_mask = 'mask.txt'
{rw}/
{channel}
&list_bound_stage
  fn_stage_cell(1) = 'cells_out.txt'
  fn_stage_val(1) = 'stage.txt'
/
&list_bound_inflow
  fn_inflow_cell(1) = 'cells_main.txt'
  fn_inflow_val(1) = 'q_main.txt'
  inflow_dist(1) = 2
{trib}/
"""
CHANNEL = """
&list_channel
  fn_bank = 'bank.txt'
  f_bank_datum = 2
  fn_width = 'width.txt'
/
"""
TITLE_SHAPE = {"uniform": "直線の本川", "constr": "直線の本川 + 狭窄部", "bend": "湾曲の本川",
               "base": "湾曲の本川 + 狭窄部(本編の本川)", "trib": "本編の本川 + 支川"}
TITLE_REP = {"mix": "狭窄部は解像 1 セル + サブグリッド 1 セル", "round": "狭窄部は解像 1 セル",
             "split": "狭窄部はサブグリッド 2 セル(幅を等分)", "full": "狭窄部は解像 2 セル"}


def write_inputs(name, shape, grid, rep, thick=0):
    setup(shape)
    qt = SHAPE[shape][3]
    keep = [1, 2] if grid == "fine" else [1]               # 本川の河道(細かい格子は本川の堤防も)
    if qt > 0:
        keep.append(3)                                     # 支川の河道
    d = os.path.join(HERE, f"data_{name}")
    os.makedirs(d, exist_ok=True)
    if grid == "fine":
        z, rn, _, h0, kind = m.build(Q_MAIN, max(qt, 1.0))
        nx, ny, dx = m.NX, m.NY, m.DX
        z_out = m.ZM0 - m.SM * float(np.interp((m.NX - 0.5) * m.DX, m.XS, m.SC))
        arrays = []
    else:
        z, rn, rw, width, bank, _, h0, kind = mc.build(Q_MAIN, max(qt, 1.0), rep=rep, thick=thick)
        nx, ny, dx = mc.NXC, mc.NYC, mc.DXC
        z_out = float(np.mean([z[j, nx - 1] for j in range(ny) if kind[j, nx - 1] == 1]))
        arrays = [("rw", rw, "%d"), ("width", width, "%.1f"), ("bank", bank, "%.3f")]
    mask = np.isin(kind, keep).astype(int)
    for fn, a, fmt in [("z", z, "%.3f"), ("rn", rn, "%.3f"), ("mask", mask, "%d"), ("h0", h0, "%.3f"),
                       ("kind", kind, "%d")] + arrays:
        np.savetxt(os.path.join(d, f"{fn}.txt"), a, fmt=fmt)
    with open(os.path.join(d, "cells_main.txt"), "w") as f:
        f.writelines(f"1 {j + 1}\n" for j in range(ny) if kind[j, 0] == 1)
    with open(os.path.join(d, "cells_out.txt"), "w") as f:
        f.writelines(f"{nx} {j + 1}\n" for j in range(ny) if kind[j, nx - 1] == 1)
    eta = z_out + m.hn((Q_MAIN + qt) / m.BM, m.RNM, m.SM)
    with open(os.path.join(d, "stage.txt"), "w") as f:
        f.write(f"0 {eta:.4f}\n1440 {eta:.4f}\n")
    with open(os.path.join(d, "q_main.txt"), "w") as f:
        f.write(f"0 {Q_MAIN:.1f}\n1440 {Q_MAIN:.1f}\n")
    trib = ""
    if qt > 0:
        with open(os.path.join(d, "cells_trib.txt"), "w") as f:
            f.writelines(f"{i + 1} 1\n" for i in range(nx) if kind[0, i] == 3)
        with open(os.path.join(d, "q_trib.txt"), "w") as f:
            f.write(f"0 {qt:.1f}\n1440 {qt:.1f}\n")
        trib = "  fn_inflow_cell(2) = 'cells_trib.txt'\n  fn_inflow_val(2) = 'q_trib.txt'\n  inflow_dist(2) = 2\n"
    title = TITLE_SHAPE[shape] + ("、細かい格子 Δx = 20 m" if grid == "fine" else f"、粗い格子 Δx = 100 m。{TITLE_REP[rep]}")
    if thick:
        title += f"。湾曲部の段を太らせる(THICK = {thick})"
    with open(os.path.join(HERE, f"param_{name}.txt"), "w", encoding="utf-8") as f:
        f.write(PARAM.format(title=title, qm=Q_MAIN, trib_txt=f"・支川 {qt:,.0f} m3/s" if qt > 0 else "", name=name,
                             dt="1.0" if grid == "fine" else "2.0", chan_fn="" if grid == "fine" else "  fn_channel = '-'\n",
                             nx=nx, ny=ny, dx=f"{dx:.1f}", rw="" if grid == "fine" else "  fn_rw = 'rw.txt'\n",
                             channel="" if grid == "fine" else CHANNEL, trib=trib))
    return int(mask.sum())


# ---------------------------------------------------------------- 1 次元の漸変流(標準逐次計算)
def gvf_1d(shape, ds=1.0):
    """矩形・幅 b(s)・Manning・R = h の 1 次元の漸変流を、下流端の等流水深から上流へ解く。縮流・拡流と合流の損失は
    数えない(エネルギー水頭 z + h + V²/2g の差 = 摩擦勾配の平均 × Δs)。支川があれば合流点より下流の流量に足す。
    戻り値は (s, 水位) で s は上流向きに減る"""
    setup(shape)
    qt = SHAPE[shape][3]
    g, n = 9.81, m.RNM
    s_end = float(np.interp((m.NX - 0.5) * m.DX, m.XS, m.SC))
    s = np.arange(s_end, -0.5, -ds)
    b = np.array([m.width(x) for x in np.interp(s, m.SC, m.XS)])
    z = m.ZM0 - m.SM * s
    q = np.where(s >= m.S_J, Q_MAIN + qt, Q_MAIN)

    def sf(h, k):
        return n * n * (q[k] / (b[k] * h)) ** 2 / h ** (4.0 / 3.0)

    def head(h, k):
        return z[k] + h + (q[k] / (b[k] * h)) ** 2 / (2.0 * g)

    h = np.empty(len(s))
    h[0] = (n * q[0] / b[0] / math.sqrt(m.SM)) ** 0.6
    for k in range(1, len(s)):
        target = head(h[k - 1], k - 1)
        hc = ((q[k] / b[k]) ** 2 / g) ** (1.0 / 3.0)
        hh = h[k - 1]
        for _ in range(50):          # 常流の根を Newton 法で(差分の微分)
            f = head(hh, k) - target - 0.5 * (sf(h[k - 1], k - 1) + sf(hh, k)) * ds
            fp = head(hh + 1e-5, k) - target - 0.5 * (sf(h[k - 1], k - 1) + sf(hh + 1e-5, k)) * ds
            dh = f / ((fp - f) / 1e-5)
            hh = max(hh - dh, 1.001 * hc)
            if abs(dh) < 1e-7:
                break
        h[k] = hh
    return s, z + h


# ---------------------------------------------------------------- 数表
def stage_at_junction(name, shape, grid):
    """合流点の位置(本川の中心線の距離が合流点 ±60 m)の本川のセルの水位の平均と、最後の 1 h の変化の最大"""
    setup(shape)
    d = os.path.join(HERE, f"result_{name}")
    e4 = np.loadtxt(os.path.join(d, "E0004.txt"))
    e3 = np.loadtxt(os.path.join(d, "E0003.txt"))
    kind = np.loadtxt(os.path.join(HERE, f"data_{name}", "kind.txt"), dtype=int)
    dx, ly = (m.DX, m.LY) if grid == "fine" else (mc.DXC, mc.LYC)
    ee, ss = [], []
    for j, i in zip(*np.nonzero(kind == 1)):
        _, s, _ = m.nearest((i + 0.5) * dx, ly - (j + 0.5) * dx)
        ee.append(e4[j, i])
        ss.append(s)
    ee, ss = np.array(ee), np.array(ss)
    return float(ee[np.abs(ss - m.S_J) <= 60.0].mean()), float(np.abs(e4 - e3)[kind == 1].max())


def sgn(x):
    """符号付きの差(0.005 m 未満は 0.00、負は U+2212)"""
    return "0.00" if abs(x) < 0.005 else f"{x:+.2f}".replace("-", "\u2212")


def table():
    missing = [r[0] for r in RUNS if not os.path.exists(os.path.join(HERE, f"result_{r[0]}", "E0004.txt"))]
    if missing:
        print(T("計算していない: ", "not computed: ") + " ".join(missing))
        return
    val, drift = {}, {}
    for name, shape, grid, rep, thick in RUNS:
        val[name], drift[name] = stage_at_junction(name, shape, grid)
    one_d = {}
    for shape, *_ in SHAPES:
        s, e = gvf_1d(shape)
        one_d[shape] = float(np.interp(m.S_J, s[::-1], e[::-1]))
    print(T("== 合流点の位置の本川の水位 (m)(本川 2,800 m3/s の定常。1 次元は縮流・拡流と合流の損失を数えない)",
            "== Main-river stage at the confluence location (m) (steady, main 2,800 m3/s; the 1-D model has no "
            "contraction, expansion or junction loss)"))
    lab = {"uniform": T("直線", "straight"), "constr": T("直線 + 狭窄部", "straight + narrows"),
           "bend": T("湾曲", "bend"), "base": T("湾曲 + 狭窄部(本編の本川)", "bend + narrows (main river of this example)"),
           "trib": T("湾曲 + 狭窄部 + 支川 300 m³/s", "bend + narrows + tributary 300 m³/s")}
    print(T("| 本川の形 | Δx = 20 m | Δx = 100 m | 差 | Δx = 100 m(段を太らせる) | 差 | 1 次元 |",
            "| Main river | Δx = 20 m | Δx = 100 m | Difference | Δx = 100 m (steps thickened) | Difference | 1-D |"))
    print("|---|---:|---:|---:|---:|---:|---:|")
    for shape, *_ in SHAPES:
        f, c = val[f"f_{shape}"], val[f"c_{shape}"]
        k = val.get(f"c_{shape}_k2")
        kk = f"{k:.2f} | {sgn(k - f)}" if k is not None else "— | —"
        print(f"| {lab[shape]} | {f:.2f} | {c:.2f} | {sgn(c - f)} | {kk} | {one_d[shape]:.2f} |")
    print()
    print(T("== 粗い格子の狭窄部(幅 120 m)の表し方(直線 + 狭窄部)", "== Representing the 120 m narrows on the coarse grid (straight + narrows)"))
    rep_lab = {"round": T("解像 1 セル(幅 100 m)", "1 resolved cell (100 m wide)"),
               "split": T("サブグリッド 60 m × 2 セル", "2 subgrid cells of 60 m"),
               "mix": T("解像 1 セル + サブグリッド 20 m(本編)", "1 resolved cell + 20 m subgrid (this example)"),
               "full": T("解像 2 セル(幅 200 m。狭窄部が消える)", "2 resolved cells (200 m; the narrows disappears)")}
    print(T("| 表し方 | 合流点の位置の水位 (m) | Δx = 20 m との差 (m) |", "| Representation | Stage at the confluence location (m) | Difference from Δx = 20 m (m) |"))
    print("|---|---:|---:|")
    for rep in ("round", "split", "mix", "full"):
        v = val["c_constr" if rep == "mix" else f"c_constr_{rep}"]
        print(f"| {rep_lab[rep]} | {v:.2f} | {sgn(v - val['f_constr'])} |")
    print(T(f"参考: Δx = 20 m(6 セル = 120 m){val['f_constr']:.2f} m、1 次元(120 m){one_d['constr']:.2f} m",
            f"Reference: Δx = 20 m (6 cells = 120 m) {val['f_constr']:.2f} m, 1-D (120 m) {one_d['constr']:.2f} m"))
    print(T("最後の 1 h の水位の変化の最大 (m): ", "Largest stage change in the last hour (m): ")
          + ", ".join(f"{k} {v:.4f}" for k, v in drift.items()))


def main():
    if "table" in sys.argv[1:]:
        table()
        return
    for name, shape, grid, rep, thick in RUNS:
        n = write_inputs(name, shape, grid, rep, thick)
        print(f"{name:16s} {T('有効セル', 'active cells')} {n}")


if __name__ == "__main__":
    main()
