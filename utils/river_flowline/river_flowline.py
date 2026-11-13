#!/usr/bin/env python3
# ENCflow/utils/river_flowline/river_flowline.py
# 河道マスクを、標高の落水線に載せ直す前処理(numpy だけを使う)。
#
#   python3 river_flowline.py Z MASK RIVER OUT [--acc ACC]
#
#   Z      標高(窪地処理済み)。テキスト行列、行は北から南(ENCflow の fn_z と同じ)
#   MASK   領域マスク(0 より大きい値: 計算するセル。fn_mask と同じ)。全域を使うなら '-'
#   RIVER  元の河道マスク(0 より大きい値: 河道セル。fn_rw と同じ)
#   OUT    載せ直した河道マスク(0 / 1)の出力先
#   --acc  落水線の集水面積(セル数。自セルを含む)も書く(確認と図化用)
#
# 河川の中心線をラスタにした河道マスクは、標高の谷線から 1 セルずれる所がある。ずれたセルは谷壁の
# セルで、河道の粗度(rn0_rw)や掘り込み(depth_rw)が谷壁に付き、谷線の上のセルには付かない。
# このスクリプトは、河道マスクの各セルから標高の落水線をたどり、通ったセルを新しい河道マスクにする。
#
# 手順:
#   1. 落水線を決める。各セルの流下先は 8 近傍の最急勾配のセル(D8。O'Callaghan & Mark 1984)。
#      自分より低い隣がないセル(窪地処理で埋めた平坦面、残った窪地)は、領域の縁のセルから標高の
#      低い順にセルを取り出して隣へ広げる Priority-Flood(Barnes ら 2014)で、先に取り出された隣を
#      流下先にする。領域の縁のセルで自分より低い隣がないものが、落水線の終点(流出先)になる
#   2. 元の河道マスクの各セルから落水線を終点までたどり、通ったセルを河道にする。出発したセル自身は、
#      ほかの河道セルからの落水線が通るときだけ河道になる(谷線から外れたセルは河道から外れる。
#      各河道の最上流の 1 セルも外れる)
#
# できないこと: 落水線は標高だけで決まる(幅 1 セル。8 近傍でつながる)。川幅が格子幅より広い河道や
# 湖は、落水線が通るセルだけが河道になる(元のマスクが面で塗ってあるところは、各セルからの落水線が
# 通る範囲が残る)。平坦面の中の落水線は Priority-Flood の取り出し順で決まり、地形の情報を持たない。
# 落水線の手続きは examples/source_area/make_catchment.py と同じ(流出先を領域の縁のセルにした点だけが違う)。
# 文献:
#   Barnes, R., Lehman, C. and Mulla, D. (2014): Priority-flood: An optimal depression-filling and
#     watershed-labeling algorithm for digital elevation models. Computers & Geosciences, 62, 117-127.
#   O'Callaghan, J. F. and Mark, D. M. (1984): The extraction of drainage networks from digital
#     elevation data. Computer Vision, Graphics, and Image Processing, 28(3), 323-344.
import argparse
import heapq
import sys

import numpy as np

DJ = (-1, -1, -1, 0, 0, 1, 1, 1)        # 8 近傍(北西から東へ、行ごと)
DI = (-1, 0, 1, -1, 1, -1, 0, 1)


def flow_tree(z, valid):
    """落水線の木を作る。戻り値: 流下先の行・列(終点は -1)、下流から上流への処理順、低い隣のないセルの数。"""
    ny, nx = z.shape
    zz = np.where(valid, z, np.inf)
    # 領域の縁のセル(8 近傍に領域外か格子の外がある)
    vp = np.pad(valid, 1, constant_values=False)
    edge = np.zeros((ny, nx), dtype=bool)
    for k in range(8):
        edge |= ~vp[1 + DJ[k]:1 + DJ[k] + ny, 1 + DI[k]:1 + DI[k] + nx]
    edge &= valid
    # --- Priority-Flood: 縁のセルから標高の低い順に広げる(平坦面と残った窪地の流下先を決める) ---
    par_j = np.full((ny, nx), -1, dtype=np.int32)
    par_i = np.full((ny, nx), -1, dtype=np.int32)
    zfill = np.full((ny, nx), np.inf)           # 取り出したときの水位(窪地は溢れる高さ)
    seen = edge.copy()
    heap = [(zz[j, i], n, j, i) for n, (j, i) in enumerate(zip(*np.where(edge)))]
    heapq.heapify(heap)
    cnt = len(heap)
    order = []
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
    # --- D8: 自分より低い隣のうち勾配が最大のセルへ(あれば Priority-Flood の流下先を置き換える) ---
    zp = np.pad(zfill, 1, constant_values=np.inf)
    best = np.zeros((ny, nx))
    rcv_j, rcv_i = par_j.copy(), par_i.copy()
    jj, ii = np.mgrid[0:ny, 0:nx]
    for k in range(8):
        zn = zp[1 + DJ[k]:1 + DJ[k] + ny, 1 + DI[k]:1 + DI[k] + nx]
        with np.errstate(invalid="ignore"):
            s = (zfill - zn) / np.hypot(DJ[k], DI[k])
        s = np.where(valid & np.isfinite(zn), s, 0.0)
        upd = s > best
        best[upd] = s[upd]
        rcv_j[upd] = (jj + DJ[k])[upd]
        rcv_i[upd] = (ii + DI[k])[upd]
    nflat = int((valid & (best <= 0.0)).sum())
    # 処理順: 溢れる高さの低い順、同じ高さは Priority-Flood が取り出した順(流下先が必ず先に来る)
    rank = np.empty((ny, nx), dtype=np.int64)
    for n, (j, i) in enumerate(order):
        rank[j, i] = n
    order.sort(key=lambda c: (zfill[c], rank[c]))
    return rcv_j, rcv_i, order, nflat


def remap(river, rcv_j, rcv_i):
    """元の河道マスクの各セルから落水線をたどり、通ったセル(出発セルは含めない)を返す。"""
    new = np.zeros_like(river)
    for j, i in zip(*np.where(river)):
        while rcv_j[j, i] >= 0:
            j, i = rcv_j[j, i], rcv_i[j, i]
            if new[j, i]:
                break
            new[j, i] = True
    return new


def main():
    ap = argparse.ArgumentParser(description="河道マスクを標高の落水線に載せ直す")
    ap.add_argument("z", help="標高(窪地処理済み。テキスト行列)")
    ap.add_argument("mask", help="領域マスク(全域なら '-')")
    ap.add_argument("river", help="元の河道マスク")
    ap.add_argument("out", help="載せ直した河道マスクの出力先")
    ap.add_argument("--acc", help="落水線の集水面積(セル数)の出力先")
    a = ap.parse_args()

    z = np.loadtxt(a.z)
    valid = np.ones(z.shape, dtype=bool) if a.mask == "-" else np.loadtxt(a.mask) > 0
    river0 = np.loadtxt(a.river) > 0
    if valid.shape != z.shape or river0.shape != z.shape:
        sys.exit("river_flowline.py: 標高・領域マスク・河道マスクの格子の大きさが合わない")
    river = river0 & valid

    rcv_j, rcv_i, order, nflat = flow_tree(z, valid)
    new = remap(river, rcv_j, rcv_i)
    np.savetxt(a.out, new.astype(int), fmt="%d")

    if a.acc:
        acc = valid.astype(np.int64)
        for j, i in reversed(order):
            if rcv_j[j, i] >= 0:
                acc[rcv_j[j, i], rcv_i[j, i]] += acc[j, i]
        np.savetxt(a.acc, acc, fmt="%d")

    nend = int((valid & (rcv_j < 0)).sum())
    off = river & ~new
    dz = z[off] - z[rcv_j[off], rcv_i[off]] if off.any() else np.zeros(1)
    print("領域 %d セル、低い隣のないセル %d(%.2f %%)、落水線の終点 %d セル"
          % (valid.sum(), nflat, 100.0 * nflat / valid.sum(), nend))
    print("元の河道マスク %d セル → 載せ直した河道マスク %d セル" % (river.sum(), new.sum()))
    print("  落水線に載っていたセル %d(元の %.0f %%)、外したセル %d(流下先より中央値で %.1f m 高い)、"
          "足したセル %d" % ((river & new).sum(), 100.0 * (river & new).sum() / max(river.sum(), 1),
                             off.sum(), float(np.median(dz)), (new & ~river).sum()))
    if (river0 & ~valid).any():
        print("  領域マスクの外の河道セル %d は使っていない" % (river0 & ~valid).sum())


if __name__ == "__main__":
    main()
