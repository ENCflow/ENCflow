#!/usr/bin/env python3
"""examples/joganji_flume の入力生成: data_nilim/ の格子点・メッシュの値を正方格子(既定 10 cm)に写す。

  python3 make_init.py [--dx 0.1] [--feed-solid 0.6]   # 入力一式をこのディレクトリに書く
  python3 make_init.py --spinup-h result_spinup         # 助走計算の最終水深を h_spinup.txt に写す
                                                        # (地盤高が助走計算と違うセルは乾いた状態から)

元の格子は境界適合格子(I 2363 × J 87、約 5 cm)。正方格子のセル中心が入る四辺形を探し、四辺形の中の位置
(双一次の逆写像)で格子点の値を双一次補間する(地盤高・固定床高・240 分の河床高)。メッシュの値(表層の粒度)は
四辺形の値をそのまま使う。固定床・移動床の区別は四辺形の 4 隅のうち最も近い格子点のもの。
上流端(I = 1)と下流端(I = 2363)の断面は斜めなので、東西の外縁まで固定床の延長を足す(地盤高は端の断面を
水平に写す)。区間流入は東の外縁の、上流端の低水路の幅のセル。下流は西の外縁を自由流出にする。
流入部(移動床が始まるまでの固定床)の低水路の幅は、移動床の最初の断面の河床高の中央値の水平な床にする。

書くファイル:
  z.txt mask.txt rn.txt sd.txt fa1.txt fa2.txt fa3.txt        地盤高・領域マスク・粗度・移動層厚・表層の割合
  geoinfo.txt                                                 &list_geoinfo(格子の大きさとファイル名)
  z_outlet.txt geoinfo_outlet.txt                             下流端の延長を固定床高にした感度の構成の地盤高(param_outlet.txt)
  boundary.txt boundary_single.txt boundary_spinup.txt       &list_bound_edge・&list_bound_inflow(混合粒径・単一粒径・助走)
  inflow_cells.txt inflow_q.txt inflow_qbmix.txt inflow_qb.txt inflow_q_spinup.txt
                                                              流入セル・流量・粒径階ごとの給砂・合計の給砂
  record.txt                                                  水位計 21 か所のプローブ(各 3 × 3 セル)
  grid_info.txt                                               格子の原点・間隔・代表粒径(図化と README 用)
給砂量: 元のファイルの L/s に --feed-solid(既定 0.6 = 1 − 空隙率 0.4。元の値を空隙込みの体積と見なす)を掛けて
固体体積 (m3/s) にする。元の値を固体体積と見なすなら --feed-solid 1。
依存: numpy
"""
import argparse
import csv
import glob
import gzip
import io
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data_nilim")
D_CLASS = (0.00057, 0.0030, 0.0066)   # 粒径集団 1〜3 の D50 (m)(元のファイルの 3_粒径集団)
SUB0 = (0.374, 0.414, 0.212)          # 下層の組成(敷き均した混合砂の配合。小橋ら 2026。README)


def read_csv(name):
    """data_nilim/ の CSV(# 行は出典の注)を {列名: np.array} で返す。文字列の列は str のまま"""
    path = os.path.join(DATA, name)
    op = gzip.open if name.endswith(".gz") else open
    with op(path, "rt", encoding="utf-8") as f:
        lines = [l for l in f if not l.startswith("#")]
    rows = list(csv.reader(io.StringIO("".join(lines))))
    head, body = rows[0], rows[1:]
    out = {}
    for k, h in enumerate(head):
        col = [r[k] for r in body]
        try:
            out[h] = np.array([float(v) for v in col])
        except ValueError:
            out[h] = np.array(col)
    return out


def load_nodes():
    g = read_csv("grid.csv.gz")
    ni, nj = int(g["I"].max()), int(g["J"].max())
    order = np.lexsort((g["J"], g["I"]))
    nodes = {k: g[k][order].reshape(ni, nj) for k in ("x", "y", "z0", "zfix", "fixed", "z240")}
    return nodes


def load_mesh():
    m = read_csv("gsd.csv.gz")
    ni, nj = int(m["I"].max()), int(m["J"].max())
    order = np.lexsort((m["J"], m["I"]))
    keys = [k for k in m if k not in ("I", "J")]
    return {k: m[k][order].reshape(ni, nj) for k in keys}


class Raster:
    """正方格子: 西端 x0、北端 y1、間隔 dx、nx 列 × ny 行(行 1 が北)"""

    def __init__(self, nodes, dx):
        X, Y = nodes["x"], nodes["y"]
        self.dx = dx
        self.x0 = np.floor(X.min() / dx) * dx - dx
        x1 = np.ceil(X.max() / dx) * dx + dx
        y0 = np.floor(Y.min() / dx) * dx - dx
        self.y1 = np.ceil(Y.max() / dx) * dx + dx
        self.nx = int(round((x1 - self.x0) / dx))
        self.ny = int(round((self.y1 - y0) / dx))

    def xc(self):
        return self.x0 + (np.arange(self.nx) + 0.5) * self.dx

    def yc(self):
        return self.y1 - (np.arange(self.ny) + 0.5) * self.dx

    def cell_of(self, x, y):
        """点 (x, y) を含むセルの (ix, iy)(1 始まり)"""
        return int(np.floor((x - self.x0) / self.dx)) + 1, int(np.floor((self.y1 - y) / self.dx)) + 1


def locate(nodes, ras):
    """各セル中心を含む四辺形 (a, b)(0 始まり)と、その中の位置 (s, t)。外は a = -1"""
    X, Y = nodes["x"], nodes["y"]
    ni, nj = X.shape
    p00 = np.stack([X[:-1, :-1], Y[:-1, :-1]], -1).reshape(-1, 2)
    p10 = np.stack([X[1:, :-1], Y[1:, :-1]], -1).reshape(-1, 2)
    p01 = np.stack([X[:-1, 1:], Y[:-1, 1:]], -1).reshape(-1, 2)
    p11 = np.stack([X[1:, 1:], Y[1:, 1:]], -1).reshape(-1, 2)
    allp = np.stack([p00, p10, p01, p11], 0)
    xmin, xmax = allp[..., 0].min(0), allp[..., 0].max(0)
    ymin, ymax = allp[..., 1].min(0), allp[..., 1].max(0)
    dx = ras.dx
    i0 = np.ceil((xmin - ras.x0) / dx - 0.5).astype(int)
    i1 = np.floor((xmax - ras.x0) / dx - 0.5).astype(int)
    j0 = np.ceil((ras.y1 - ymax) / dx - 0.5).astype(int)
    j1 = np.floor((ras.y1 - ymin) / dx - 0.5).astype(int)
    ni_c = np.maximum(i1 - i0 + 1, 0)
    nj_c = np.maximum(j1 - j0 + 1, 0)
    nc = ni_c * nj_c
    q = np.repeat(np.arange(nc.size), nc)
    k = np.arange(q.size) - np.repeat(np.cumsum(nc) - nc, nc)
    ci = i0[q] + k % ni_c[q]
    cj = j0[q] + k // ni_c[q]
    px = ras.x0 + (ci + 0.5) * dx
    py = ras.y1 - (cj + 0.5) * dx
    a00, a10, a01, a11 = p00[q], p10[q], p01[q], p11[q]
    s = np.full(q.size, 0.5)
    t = np.full(q.size, 0.5)
    for _ in range(12):
        fx = a00[:, 0] * (1 - s) * (1 - t) + a10[:, 0] * s * (1 - t) + a01[:, 0] * (1 - s) * t + a11[:, 0] * s * t - px
        fy = a00[:, 1] * (1 - s) * (1 - t) + a10[:, 1] * s * (1 - t) + a01[:, 1] * (1 - s) * t + a11[:, 1] * s * t - py
        dsx = (a10[:, 0] - a00[:, 0]) * (1 - t) + (a11[:, 0] - a01[:, 0]) * t
        dsy = (a10[:, 1] - a00[:, 1]) * (1 - t) + (a11[:, 1] - a01[:, 1]) * t
        dtx = (a01[:, 0] - a00[:, 0]) * (1 - s) + (a11[:, 0] - a10[:, 0]) * s
        dty = (a01[:, 1] - a00[:, 1]) * (1 - s) + (a11[:, 1] - a10[:, 1]) * s
        det = dsx * dty - dsy * dtx
        det = np.where(np.abs(det) < 1e-30, 1e-30, det)
        s = s - (fx * dty - fy * dtx) / det
        t = t - (-fx * dsy + fy * dsx) / det
    eps = 1.0e-9
    ok = (s >= -eps) & (s <= 1 + eps) & (t >= -eps) & (t <= 1 + eps) & \
         (ci >= 0) & (ci < ras.nx) & (cj >= 0) & (cj < ras.ny)
    A = np.full((ras.ny, ras.nx), -1, dtype=int)
    B = np.full((ras.ny, ras.nx), -1, dtype=int)
    S = np.zeros((ras.ny, ras.nx))
    T = np.zeros((ras.ny, ras.nx))
    qa, qb = np.divmod(q[ok], nj - 1)
    A[cj[ok], ci[ok]] = qa      # 境界上の重複は後勝ち(どちらの四辺形でも同じ値)
    B[cj[ok], ci[ok]] = qb
    S[cj[ok], ci[ok]] = np.clip(s[ok], 0.0, 1.0)
    T[cj[ok], ci[ok]] = np.clip(t[ok], 0.0, 1.0)
    return A, B, S, T


def interp_nodes(V, A, B, S, T):
    """格子点の値 V (ni, nj) をセルへ双一次補間(外は nan)"""
    inside = A >= 0
    a, b, s, t = A[inside], B[inside], S[inside], T[inside]
    out = np.full(A.shape, np.nan)
    out[inside] = V[a, b] * (1 - s) * (1 - t) + V[a + 1, b] * s * (1 - t) + V[a, b + 1] * (1 - s) * t + V[a + 1, b + 1] * s * t
    return out


def nearest_node(V, A, B, S, T):
    inside = A >= 0
    out = np.full(A.shape, np.nan)
    out[inside] = V[A[inside] + np.rint(S[inside]).astype(int), B[inside] + np.rint(T[inside]).astype(int)]
    return out


def mesh_value(M, A, B):
    inside = A >= 0
    out = np.full(A.shape, np.nan)
    out[inside] = M[A[inside], B[inside]]
    return out


def end_extension(nodes, ras, end):
    """端の断面(end = 0: 上流 I = 1、-1: 下流 I = 2363)から外縁までの延長のセルと、写す断面上の位置 J(実数)"""
    X, Y = nodes["x"][end], nodes["y"][end]
    xc, yc = ras.xc(), ras.yc()
    cells = []
    for j in range(ras.ny):
        y = yc[j]
        # 断面の折れ線(J 1..87)で y を挟む区間
        for b in range(len(Y) - 1):
            ya, yb = Y[b], Y[b + 1]
            if (ya - y) * (yb - y) <= 0 and ya != yb:
                w = (y - ya) / (yb - ya)
                xl = X[b] + w * (X[b + 1] - X[b])
                jj = b + w
                for i in range(ras.nx):
                    if (end == 0 and xc[i] > xl) or (end == -1 and xc[i] < xl):
                        cells.append((j, i, jj))
                break
    return cells


def section_profile(V, end, jj):
    b = min(int(np.floor(jj)), V.shape[1] - 2)
    w = jj - b
    return V[end, b] * (1 - w) + V[end, b + 1] * w


def build(dx):
    nodes = load_nodes()
    mesh = load_mesh()
    ras = Raster(nodes, dx)
    A, B, S, T = locate(nodes, ras)
    inside = A >= 0
    z = interp_nodes(nodes["z0"], A, B, S, T)
    zfix = interp_nodes(nodes["zfix"], A, B, S, T)
    fixed = nearest_node(nodes["fixed"], A, B, S, T)
    jpos = np.where(inside, B + T, np.nan)            # 格子の J(0 始まりの実数)
    ipos = np.where(inside, A + S, np.nan)            # 格子の I(0 始まりの実数)
    # 延長(固定床。端の断面を水平に写す)
    ext = {}
    for end in (0, -1):
        for (j, i, jj) in end_extension(nodes, ras, end):
            if inside[j, i]:
                continue
            ext[(j, i)] = (end, jj)
            z[j, i] = section_profile(nodes["z0"], end, jj)
            zfix[j, i] = z[j, i]
            fixed[j, i] = 1.0
            jpos[j, i] = jj
            ipos[j, i] = 0.0 if end == 0 else nodes["x"].shape[0] - 1.0
    mask = np.isfinite(z)
    # 流入部(上流端から移動床が始まる I までの固定床)の低水路の幅は、移動床の最初の断面の低水路の河床高の
    # 中央値の水平な床にする。元の流入部には溜まりと溝(最深 1.49 m)と、上流端の断面(I = 1)の高い構造
    # (最高 3.27 m)があり、延長に写すと流入を閉じ込め、深い水が時間刻みを律し、給砂が溝に溜まるため
    # (計測の区間の外。README の「入力の作り方」)
    jr, jl = bank_j(nodes)
    jr_c = np.interp(ipos, np.arange(len(jr)), jr)
    jl_c = np.interp(ipos, np.arange(len(jl)), jl)
    in_low = (jpos >= np.minimum(jr_c, jl_c)) & (jpos <= np.maximum(jr_c, jl_c))
    i_mov, zapron = inlet_apron(nodes)
    inlet = mask & (ipos < i_mov) & in_low
    z = np.where(inlet, zapron, z)
    zfix = np.where(inlet, zapron, zfix)
    fixed = np.where(inlet, 1.0, fixed)
    sd = np.where(mask & (fixed < 0.5), np.maximum(z - zfix, 0.0), 0.0)
    # 粗度: 低水路(左右の低水路河岸の間)は断面の値を I で線形補間、高水敷は断面の値(全断面 0.013)
    sec = read_csv("sections.csv")
    order = np.argsort(sec["I"])
    si = sec["I"][order] - 1.0
    n_low = np.interp(ipos, si, sec["n_low"][order])
    n_fp = np.interp(ipos, si, 0.5 * (sec["n_lfp"][order] + sec["n_rfp"][order]))
    rn = np.where(in_low, n_low, n_fp)
    # 表層の割合(メッシュの値。延長と固定床は一様 1/3 = 使われない)
    fa = []
    for k in (1, 2, 3):
        v = mesh_value(mesh["f%d_0" % k], A, B) / 100.0
        fa.append(v)
    tot = fa[0] + fa[1] + fa[2]
    for k in range(3):
        fa[k] = np.where(mask & (sd > 0) & (tot > 0), fa[k] / np.where(tot > 0, tot, 1), 1.0 / 3.0)
    return dict(ras=ras, A=A, B=B, S=S, T=T, z=z, zfix=zfix, fixed=fixed, sd=sd, mask=mask, rn=rn, fa=fa,
                ipos=ipos, jpos=jpos, in_low=in_low, ext=ext, nodes=nodes, mesh=mesh, jr=jr, jl=jl)


def inlet_apron(nodes):
    """移動床が始まる I(0 始まり。低水路に移動床の格子点がある最初の I)と、その断面の低水路の河床高の中央値"""
    jr, jl = bank_j(nodes)
    j0, j1 = int(min(jr[0], jl[0])), int(max(jr[0], jl[0]))
    low_fixed = nodes["fixed"][:, j0:j1 + 1]
    i_mov = int(np.argmax(low_fixed.min(axis=1) < 0.5))
    return float(i_mov), float(np.median(nodes["z0"][i_mov, j0:j1 + 1]))


def bank_j(nodes):
    """I ごとの右岸・左岸の低水路河岸の J(0 始まり)。河岸の法線の点に最も近い格子点"""
    bk = read_csv("banks.csv.gz")
    X, Y = nodes["x"], nodes["y"]
    order = np.argsort(bk["k"])
    jr = np.argmin((X - bk["x_rbank"][order][:, None]) ** 2 + (Y - bk["y_rbank"][order][:, None]) ** 2, axis=1)
    jl = np.argmin((X - bk["x_lbank"][order][:, None]) ** 2 + (Y - bk["y_lbank"][order][:, None]) ** 2, axis=1)
    return jr.astype(float), jl.astype(float)


def write_raster(path, a, fmt="%.5f", fill=0.0):
    a = np.where(np.isfinite(a), a, fill)
    with open(path, "w") as f:
        for row in a:
            f.write(" ".join(fmt % v for v in row) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dx", type=float, default=0.1)
    ap.add_argument("--feed-solid", type=float, default=0.6)
    ap.add_argument("--spinup-h", default=None)
    args = ap.parse_args()
    if args.spinup_h:
        frames = sorted(glob.glob(os.path.join(args.spinup_h, "H9998.txt")))
        if not frames:
            sys.exit("no H9998.txt in " + args.spinup_h)
        h = np.loadtxt(frames[-1])
        z_old = np.loadtxt(os.path.join(args.spinup_h, "Z0000.txt"))
        z_new = np.loadtxt("z.txt")
        h = np.where(np.abs(z_new - z_old) > 1.0e-3, 0.0, h)  # 助走計算と地盤高が違うセルは乾いた状態から
        write_raster("h_spinup.txt", h, "%.6f")
        print("h_spinup.txt from %s (max %.4f m)" % (frames[-1], h.max()))
        if os.path.exists("z_outlet.txt"):           # 下流端の延長を固定床高にした感度の構成(param_outlet.txt)
            z_o = np.loadtxt("z_outlet.txt")
            write_raster("h_outlet.txt", np.where(np.abs(z_o - z_new) > 1.0e-3, 0.0, h), "%.6f")
            print("h_outlet.txt (the lowered outlet extension starts dry)")
        return

    m = build(args.dx)
    ras = m["ras"]
    mask = m["mask"]
    write_raster("z.txt", np.where(mask, m["z"], 9.0))     # 領域外は高い地盤(マスクで対象外)
    write_raster("mask.txt", mask.astype(float), "%d")
    write_raster("rn.txt", np.where(mask, m["rn"], 0.013), "%.4f")
    write_raster("sd.txt", m["sd"], "%.5f")
    for k in range(3):
        write_raster("fa%d.txt" % (k + 1), m["fa"][k], "%.5f")
    lx, ly = ras.nx * ras.dx, ras.ny * ras.dx
    # 感度の構成(param_outlet.txt): 下流端の延長の床を、端の断面の河床高ではなく固定床高(移動層の底)にする
    z_out = np.where(mask, m["z"], 9.0)
    for (j, i), (end, jj) in m["ext"].items():
        if end == -1:
            z_out[j, i] = section_profile(m["nodes"]["zfix"], -1, jj)
    write_raster("z_outlet.txt", z_out)
    for name, fz in (("geoinfo.txt", "z.txt"), ("geoinfo_outlet.txt", "z_outlet.txt")):
        with open(name, "w") as f:
            f.write("! make_init.py が書いた格子(dx = %g m。西端 x = %.3f m、北端 y = %.3f m)\n" % (ras.dx, ras.x0, ras.y1))
            f.write("&list_geoinfo\n  lx = %.4f\n  ly = %.4f\n  nx = %d\n  ny = %d\n" % (lx, ly, ras.nx, ras.ny))
            f.write("  f_ztype = 1\n  fn_z = '%s'\n  f_masktype = 1\n  fn_mask = 'mask.txt'\n" % fz)
            f.write("  f_rntype = 1\n  fn_rn = 'rn.txt'\n  f_sdtype = 1\n  fn_sd = 'sd.txt'\n/\n")

    # 区間流入: 東の外縁の列のうち、上流端(I = 1)の低水路の幅
    jr0, jl0 = m["jr"][0], m["jl"][0]
    lo, hi = min(jr0, jl0), max(jr0, jl0)
    cells = [(ras.nx, j + 1) for j in range(ras.ny)
             if mask[j, ras.nx - 1] and lo <= m["jpos"][j, ras.nx - 1] <= hi]
    with open("inflow_cells.txt", "w") as f:
        for i, j in cells:
            f.write("%d %d\n" % (i, j))
    bc = read_csv("bc_2-1.csv.gz")
    with open("inflow_q.txt", "w") as f:
        for t, q in zip(bc["t_min"], bc["q_lps"]):
            f.write("%.6f %.6e\n" % (t, q * 1.0e-3))
    with open("inflow_qbmix.txt", "w") as f:
        for t, a, b, c in zip(bc["t_min"], bc["f1_lps"], bc["f2_lps"], bc["f3_lps"]):
            f.write("%.6f %.6e %.6e %.6e\n" % (t, a * 1.0e-3 * args.feed_solid, b * 1.0e-3 * args.feed_solid,
                                                c * 1.0e-3 * args.feed_solid))
    with open("inflow_qb.txt", "w") as f:        # 単一粒径の構成の給砂(3 つの粒径集団の合計)
        for t, a, b, c in zip(bc["t_min"], bc["f1_lps"], bc["f2_lps"], bc["f3_lps"]):
            f.write("%.6f %.6e\n" % (t, (a + b + c) * 1.0e-3 * args.feed_solid))
    q0 = bc["q_lps"][0] * 1.0e-3
    with open("inflow_q_spinup.txt", "w") as f:   # 5 分の 3 L/s で満たし、5 分で基底流量へ下げ、30 分保つ
        for t, q in ((0.0, 3.0e-3), (5.0, 3.0e-3), (10.0, q0), (40.0, q0)):
            f.write("%.6f %.6e\n" % (t, q))
    for name, qf, feed in (("boundary.txt", "inflow_q.txt", "qbmix"), ("boundary_single.txt", "inflow_q.txt", "qb"),
                           ("boundary_spinup.txt", "inflow_q_spinup.txt", None)):
        with open(name, "w") as f:
            f.write("&list_bound_edge\n  f_bc_w = 1                ! 西辺(下流端の延長): 自由流出\n/\n")
            f.write("&list_bound_inflow\n  fn_inflow_cell(1) = 'inflow_cells.txt'\n  fn_inflow_val(1) = '%s'\n" % qf)
            f.write("  inflow_dist(1) = 2\n")
            if feed == "qbmix":
                f.write("  fn_inflow_qbmix(1) = 'inflow_qbmix.txt'\n")
            elif feed == "qb":
                f.write("  fn_inflow_qb(1) = 'inflow_qb.txt'\n")
            f.write("/\n")
    # 水位計のプローブ
    wl = read_csv("wl_2-1.csv.gz")
    gauges = []
    for g in dict.fromkeys(wl["gauge"]):
        k = np.nonzero(wl["gauge"] == g)[0][0]
        gauges.append((g, wl["x"][k], wl["y"][k]))
    with open("record.txt", "w") as f:   # 水位計ごとに、そのセルを中心とする 3 × 3 のセル(9 点。中心は 5 番目)
        f.write("&list_record\n")
        n = 0
        for g, x, y in gauges:
            ix, iy = ras.cell_of(x, y)
            for dj in (-1, 0, 1):
                for di in (-1, 0, 1):
                    n += 1
                    f.write("  pbxy(:,%d) = %d, %d%s\n" % (n, ix + di, iy + dj,
                            "      ! %s (x = %.3f, y = %.3f)" % (g, x, y) if di == 0 and dj == 0 else ""))
        f.write("/\n")
    # 代表粒径(単一粒径の構成の fluv_d50): 移動層のあるセルの初期の表層の平均粒径 d_m の面積平均
    dm = sum(m["fa"][k] * D_CLASS[k] for k in range(3))
    mov = mask & (m["sd"] > 0)
    with open("grid_info.txt", "w") as f:
        f.write("dx %g\nx0 %.6f\ny1 %.6f\nnx %d\nny %d\n" % (ras.dx, ras.x0, ras.y1, ras.nx, ras.ny))
        f.write("cells %d\nmovable_cells %d\ninflow_cells %d\n" % (mask.sum(), mov.sum(), len(cells)))
        f.write("dm_mean %.6f\n" % dm[mov].mean())
        f.write("feed_solid %g\n" % args.feed_solid)
    print(open("grid_info.txt").read(), end="")


if __name__ == "__main__":
    main()
