#!/usr/bin/env python3
# ENCflow/examples/source_area/make_catchment.py
# 秩父の 50 m 格子(test/chichibu/data_chichibu_50m)から、出口セルの上流の集水域を切り出して
# data/ に入力を書く(make から呼ぶ。numpy だけを使う)。
#
#   python3 make_catchment.py [--outlet I J] [--margin N]
#
# 手順:
#   1. 落水線を決める。各セルの流下先は 8 近傍の最急勾配のセル(D8)。窪地処理済みの標高には、
#      埋めた窪地が平坦面として残る(自分より低い隣がないセルが 1 % ほどある)。そこは、流域の最低点から
#      標高の低い順にセルを取り出して隣へ広げる Priority-Flood(Barnes ら 2014)で、先に取り出された
#      隣を流下先にする。これで全セルが流域の最低点まで 1 本の木でつながる
#   2. 出口セルのすぐ上流の谷筋のセル(測るセル)の上流のセルと、出口セルを領域マスクにし、その外接矩形
#      (+ 余白)で切り出す。出口セルは水位規定で常に空にする排水口で、流域を出る水はすべて測るセルの
#      列から出口セルへ入る(測線をこの列に置くと、流域からの流出の全量を測れる)
#   3. 河道マスクを落水線でつなぐ。国土数値情報の河川から作られた河道マスクの線は、標高の谷線から
#      1 セルずれて途切れる所がある。斜面と河道の粗度を分けるとき、途切れた所が斜面の粗度だと流れを
#      堰き止めるので、河道マスクの各セルから落水線を出口までたどり、通ったセルを河道に加える
#
# 出力(data/。テキスト行列、行は北から南):
#   z.txt     地盤高 (m)。元データの値のまま
#   mask.txt  領域マスク(1: 集水域)
#   rw.txt    河道マスク(1: 河道セル。落水線でつないだもの)
#   acc.txt   落水線の集水面積(セル数。自セルを含む。図化用で、計算には使わない)
#   catchment.txt  切り出しの記録(元の格子での位置、出口セル、面積など。図化と確認用)
#
# 既定の出口セルは元の格子の (i, j) = (344, 302)(1 始まり。i は西から、j は北から)。流域の西端の
# 源流域にある 2 本の支川の合流点のすぐ上流で、南側(右岸側)の支川の谷にあたる。出口を変えたら、
# 設定ファイルの nx・ny、水位規定セル、測線、プローブを、このスクリプトが表示する値に合わせる。
import argparse
import heapq
import os
import sys

import numpy as np

SRC = "../../test/chichibu/data_chichibu_50m"
DX = 50.0
DJ = (-1, -1, -1, 0, 0, 1, 1, 1)        # 8 近傍(北西から東へ、行ごと)
DI = (-1, 0, 1, -1, 1, -1, 0, 1)


def flow_tree(z, valid):
    """落水線の木を作る。戻り値: 流下先の行・列(流域の最低点は -1)、下流から上流への処理順。"""
    ny, nx = z.shape
    zz = np.where(valid, z, np.inf)
    # --- Priority-Flood: 流域の最低点から標高の低い順に広げる(平坦面と残った窪地の流下先を決める) ---
    j0, i0 = np.unravel_index(np.argmin(zz), z.shape)
    par_j = np.full((ny, nx), -1, dtype=np.int32)
    par_i = np.full((ny, nx), -1, dtype=np.int32)
    zfill = np.full((ny, nx), np.inf)           # 取り出したときの水位(窪地は溢れる高さ)
    seen = np.zeros((ny, nx), dtype=bool)
    order = []
    heap = [(zz[j0, i0], 0, j0, i0)]
    seen[j0, i0] = True
    cnt = 1
    while heap:
        zc, _, j, i = heapq.heappop(heap)
        zfill[j, i] = zc
        order.append((j, i))
        for k in range(8):
            jn, im = j + DJ[k], i + DI[k]
            if jn < 0 or jn >= ny or im < 0 or im >= nx:
                continue
            if seen[jn, im] or not valid[jn, im]:
                continue
            seen[jn, im] = True
            par_j[jn, im], par_i[jn, im] = j, i
            heapq.heappush(heap, (max(zz[jn, im], zc), cnt, jn, im))
            cnt += 1
    if seen.sum() != valid.sum():
        sys.exit("make_catchment.py: 流域マスクが 8 近傍でつながっていない")
    # --- D8: 自分より低い隣のうち勾配が最大のセルへ(あれば Priority-Flood の流下先を置き換える) ---
    zp = np.pad(zfill, 1, constant_values=np.inf)
    best = np.zeros((ny, nx))
    rcv_j, rcv_i = par_j.copy(), par_i.copy()
    jj, ii = np.mgrid[0:ny, 0:nx]
    for k in range(8):
        zn = zp[1 + DJ[k]:1 + DJ[k] + ny, 1 + DI[k]:1 + DI[k] + nx]
        with np.errstate(invalid="ignore"):
            s = (zfill - zn) / (DX * np.hypot(DJ[k], DI[k]))
        s = np.where(valid & np.isfinite(zn), s, 0.0)
        upd = s > best
        best[upd] = s[upd]
        rcv_j[upd] = (jj + DJ[k])[upd]
        rcv_i[upd] = (ii + DI[k])[upd]
    rcv_j[j0, i0] = rcv_i[j0, i0] = -1
    # 処理順: 溢れる高さの低い順、同じ高さは Priority-Flood が取り出した順(流下先が必ず先に来る)
    rank = np.empty((ny, nx), dtype=np.int64)
    for n, (j, i) in enumerate(order):
        rank[j, i] = n
    order.sort(key=lambda c: (zfill[c], rank[c]))
    return rcv_j, rcv_i, order, zfill


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outlet", type=int, nargs=2, default=(344, 302), metavar=("I", "J"),
                    help="出口セル(元の格子の列 i・行 j。1 始まり)")
    ap.add_argument("--margin", type=int, default=2, help="外接矩形の外に付ける領域外のセル数")
    ap.add_argument("--out", default="data", help="出力ディレクトリ")
    a = ap.parse_args()

    z = np.loadtxt(f"{SRC}/Chichibu_50m_filled.txt")
    basin = np.loadtxt(f"{SRC}/Chichibu_50m_basin.txt") > 0
    river = np.loadtxt(f"{SRC}/Chichibu_50m_river.txt") > 0
    ny, nx = z.shape
    io, jo = a.outlet[0] - 1, a.outlet[1] - 1
    if not basin[jo, io]:
        sys.exit("make_catchment.py: 出口セルが流域マスクの外にある")

    rcv_j, rcv_i, order, zfill = flow_tree(z, basin)
    nfill = int((basin & (zfill > z + 1e-6)).sum())

    # 集水面積(セル数): 上流から下流へ足し込む
    acc = basin.astype(np.int64)
    for j, i in reversed(order):
        if rcv_j[j, i] >= 0:
            acc[rcv_j[j, i], rcv_i[j, i]] += acc[j, i]

    # 測るセル: 出口セルへ流れ込むセルのうち集水面積が最大のもの(谷筋のすぐ上流のセル)
    jg, ig = -1, -1
    for k in range(8):
        jn, im = jo + DJ[k], io + DI[k]
        if 0 <= jn < ny and 0 <= im < nx and basin[jn, im] and (rcv_j[jn, im], rcv_i[jn, im]) == (jo, io):
            if jg < 0 or acc[jn, im] > acc[jg, ig]:
                jg, ig = jn, im
    if jg < 0:
        sys.exit("make_catchment.py: 出口セルへ流れ込むセルがない")

    # 集水域 = 測るセルの上流(下流から上流への順に、流下先が集水域なら自分も集水域)と出口セル。
    # 出口セルへ横から直接落ちるセルは入れない(流域を出る水がすべて測るセルの列を通るようにする)
    m = np.zeros((ny, nx), dtype=bool)
    m[jg, ig] = True
    for j, i in order:
        if rcv_j[j, i] >= 0 and m[rcv_j[j, i], rcv_i[j, i]]:
            m[j, i] = True
    m[jo, io] = True

    # 河道マスクを落水線でつなぐ
    rw = river & m
    nrw0 = int(rw.sum())
    for j, i in zip(*np.where(rw)):
        while (j, i) != (jo, io):
            j, i = rcv_j[j, i], rcv_i[j, i]
            if rw[j, i]:
                break
            rw[j, i] = True

    # 切り出し
    js, is_ = np.where(m)
    j1, j2 = js.min() - a.margin, js.max() + a.margin + 1
    i1, i2 = is_.min() - a.margin, is_.max() + a.margin + 1
    if j1 < 0 or i1 < 0 or j2 > ny or i2 > nx:
        sys.exit("make_catchment.py: 余白が元の格子からはみ出す(--margin を小さくする)")
    sl = (slice(j1, j2), slice(i1, i2))
    os.makedirs(a.out, exist_ok=True)
    np.savetxt(f"{a.out}/z.txt", z[sl], fmt="%.3f")
    np.savetxt(f"{a.out}/mask.txt", m[sl].astype(int), fmt="%d")
    np.savetxt(f"{a.out}/rw.txt", rw[sl].astype(int), fmt="%d")
    np.savetxt(f"{a.out}/acc.txt", np.where(m, acc, 0)[sl], fmt="%d")

    ncell = int(m.sum())
    il, jl = io - i1 + 1, jo - j1 + 1          # 切り出した格子での出口セル(1 始まり)
    lines = [
        f"source_grid = {SRC}  ({nx} x {ny}, dx = {DX:g} m)",
        f"outlet_source_ij = {io + 1} {jo + 1}",
        f"window_source_i = {i1 + 1} {i2}",
        f"window_source_j = {j1 + 1} {j2}",
        f"nx = {i2 - i1}",
        f"ny = {j2 - j1}",
        f"outlet_ij = {il} {jl}",
        f"gauge_ij = {ig - i1 + 1} {jg - j1 + 1}",
        f"outlet_z = {z[jo, io]:.3f}",
        f"cells = {ncell}",
        f"area_km2 = {ncell * DX * DX / 1e6:.4f}",
        f"z_min_max = {z[m].min():.1f} {z[m].max():.1f}",
        f"river_cells_source_mask = {nrw0}",
        f"river_cells_connected = {int(rw.sum())}",
        f"cells_raised_by_priority_flood = {nfill}",
    ]
    with open(f"{a.out}/catchment.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
