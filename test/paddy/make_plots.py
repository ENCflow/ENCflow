#!/usr/bin/env python3
"""test/paddy の区画の解像(表現 B。fn_pd_plot。developer.md §127.8)の入力を作る(Python 標準ライブラリのみ)。

  python3 make_plots.py <出力ディレクトリ>

格子は Δx = Δy = 5 m。ラスタの 1 行目が j = 1(落水口の向きはラスタの並びで 1 左上・2 上・3 右上・4 左・5 右・
6 左下・7 下・8 右下)。添字は 1 始まりで書く。

  b_drain (16 × 32): 区画 1(種類 1)i = 3..12, j = 3..14、区画 2(種類 2)i = 3..12, j = 17..28(各 10 × 12 セル =
          3000 m2)。i = 13..16 は地盤 −0.5 m の排水路(東の辺は自由流出)、ほかは地盤 0 m の道路。落水口は
          (12, 8) と (12, 22) から東(向き 5)の排水路へ。区画 1 は行 8・9、区画 2 は行 24・25 の帯の境(np = 4)を
          またぐ
  b_tight (20 × 16): 落水口のない区画(地盤はすべて 0 m)。区画 1・2 は i, j = 3..10 の 8 × 8 を斜めの階段で
          分けたもの(i − j ≤ 0 が区画 1)。区画 3(i = 12..17, j = 2..7)の中の 2 つの水たまり(区画でない
          セル)D1 = (14, 4)・D2 = (15, 5) が対角で接する(市松の角。区画 3 のくびれを横切る対角)。区画 5
          (i = 12..17, j = 10..15)の中に区画 4 の 2 セル (14, 12)・(15, 13) が対角に並ぶ(両方の対角が壁)。
          初期の水深 b_tight_h0: 区画 1・D1・(14, 12) は 0.2 m、ほかは 0(区画のセルは事前の湛水深 0.05 m に
          なる)。市松の角は行 4・5 と行 12・13 の帯の境(np = 4)にかかる
  b_back  (20 × 20): 区画 1(種類 1)i = 6..15, j = 6..15(10 × 10 = 2500 m2)。落水口 (15, 10) から東(向き 5)の
          排水路(i = 16..19、地盤 −0.5 m)へ。ほかは地盤 0 m の道路。初期の水位 b_back_e: 区画の外は 0.20 m
          (区画は 0 = 事前の湛水深になる)、b_ext_e: 区画の外は 0.40 m(畦畔の天端 0.30 m より上)
  b_over  b_back と同じ地形で落水口なし(b_over_out はすべて 0)
  b_bank  (20 × 20): 区画 1(i = 8..17, j = 6..15)の東隣の列 i = 18 が河道(河床 −0.5 m、堤防の天端は地盤 + 0.1 m)。
          区画の外と河道の初期の水位は 0.20 m(堤防の天端より上、畦畔の天端 0.30 m より下)。区画と河道の間の
          エッジは堤防と畦畔の天端の大きい方(0.30 m)で、区画に水は入らない
  b_chain (20 × 12): 区画 A(種類 1。i = 3..9, j = 3..10)と区画 B(種類 2。i = 10..16, j = 3..10)が隣り合い、A の落水口
          (9, 6) が東の B を向く(田越し)。地盤はすべて 0 m、閉じた領域。初期の水深 b_chain_h0: A は 0.25 m、ほかは 0
  b_bad_* 停止の確認(b_back の格子): 外周の区画のセル(ring)、同じ区画を向く落水口(self)、区画でないセルの
          落水口(noplot)、区画の中で違う種類(class)、整数でない区画番号(id)、天端より高い先を向く落水口
          (up_z: 向きの先の地盤を 0.5 m に)、向かい合う 2 つの落水口(face)
"""
import os
import sys


def write(path, nx, ny, f, fmt):
    with open(path, "w") as out:
        for j in range(1, ny + 1):
            out.write(" ".join(fmt % f(i, j) for i in range(1, nx + 1)) + "\n")


def drain(d):
    nx, ny = 16, 32

    def plot(i, j):
        if 3 <= i <= 12 and 3 <= j <= 14:
            return 1
        if 3 <= i <= 12 and 17 <= j <= 28:
            return 2
        return 0
    write(os.path.join(d, "b_drain_z.txt"), nx, ny, lambda i, j: -0.5 if i >= 13 else 0.0, "%.4f")
    write(os.path.join(d, "b_drain_plot.txt"), nx, ny, plot, "%d")
    write(os.path.join(d, "b_drain_out.txt"), nx, ny,
          lambda i, j: 5 if (i, j) in ((12, 8), (12, 22)) else 0, "%d")
    write(os.path.join(d, "b_drain_class.txt"), nx, ny, plot, "%d")   # 区画 1 = 種類 1、区画 2 = 種類 2


def tight(d):
    nx, ny = 20, 16

    def plot(i, j):
        if 3 <= i <= 10 and 3 <= j <= 10:
            return 1 if i - j <= 0 else 2
        if 12 <= i <= 17 and 2 <= j <= 7:
            return 0 if (i, j) in ((14, 4), (15, 5)) else 3
        if 12 <= i <= 17 and 10 <= j <= 15:
            return 4 if (i, j) in ((14, 12), (15, 13)) else 5
        return 0

    def h0(i, j):
        if plot(i, j) == 1 or (i, j) in ((14, 4), (14, 12)):
            return 0.2
        return 0.0
    write(os.path.join(d, "b_tight_plot.txt"), nx, ny, plot, "%d")
    write(os.path.join(d, "b_tight_h0.txt"), nx, ny, h0, "%.4f")


def back(d):
    nx, ny = 20, 20

    def plot(i, j):
        return 1 if 6 <= i <= 15 and 6 <= j <= 15 else 0
    write(os.path.join(d, "b_back_z.txt"), nx, ny, lambda i, j: -0.5 if 16 <= i <= 19 else 0.0, "%.4f")
    write(os.path.join(d, "b_back_plot.txt"), nx, ny, plot, "%d")
    write(os.path.join(d, "b_back_out.txt"), nx, ny, lambda i, j: 5 if (i, j) == (15, 10) else 0, "%d")
    write(os.path.join(d, "b_over_out.txt"), nx, ny, lambda i, j: 0, "%d")
    for tag, e in (("b_back_e", 0.20), ("b_ext_e", 0.40)):
        write(os.path.join(d, tag + ".txt"), nx, ny, lambda i, j, e=e: 0.0 if plot(i, j) else e, "%.4f")


def bank(d):
    nx, ny = 20, 20

    def plot(i, j):
        return 1 if 8 <= i <= 17 and 6 <= j <= 15 else 0
    write(os.path.join(d, "b_bank_z.txt"), nx, ny, lambda i, j: -0.5 if i == 18 else 0.0, "%.4f")
    write(os.path.join(d, "b_bank_rw.txt"), nx, ny, lambda i, j: 1 if i == 18 else 0, "%d")
    write(os.path.join(d, "b_bank_plot.txt"), nx, ny, plot, "%d")
    write(os.path.join(d, "b_bank_e.txt"), nx, ny, lambda i, j: 0.0 if plot(i, j) else 0.2, "%.4f")


def chain(d):
    nx, ny = 20, 12

    def plot(i, j):
        if 3 <= i <= 9 and 3 <= j <= 10:
            return 1
        if 10 <= i <= 16 and 3 <= j <= 10:
            return 2
        return 0
    write(os.path.join(d, "b_chain_plot.txt"), nx, ny, plot, "%d")
    write(os.path.join(d, "b_chain_out.txt"), nx, ny, lambda i, j: 5 if (i, j) == (9, 6) else 0, "%d")
    write(os.path.join(d, "b_chain_class.txt"), nx, ny, plot, "%d")
    write(os.path.join(d, "b_chain_h0.txt"), nx, ny, lambda i, j: 0.25 if plot(i, j) == 1 else 0.0, "%.4f")


def bad(d):
    nx, ny = 20, 20

    def plot(i, j):
        return 1 if 6 <= i <= 15 and 6 <= j <= 15 else 0
    write(os.path.join(d, "b_bad_ring_plot.txt"), nx, ny, lambda i, j: 2 if (i, j) == (1, 10) else plot(i, j), "%d")
    write(os.path.join(d, "b_bad_self_out.txt"), nx, ny, lambda i, j: 4 if (i, j) == (15, 10) else 0, "%d")
    write(os.path.join(d, "b_bad_noplot_out.txt"), nx, ny, lambda i, j: 5 if (i, j) == (17, 10) else 0, "%d")
    write(os.path.join(d, "b_bad_class.txt"), nx, ny, lambda i, j: (1 if i <= 10 else 2) if plot(i, j) else 0, "%d")
    write(os.path.join(d, "b_bad_id_plot.txt"), nx, ny, lambda i, j: 1.5 if plot(i, j) else 0.0, "%.1f")
    write(os.path.join(d, "b_bad_up_z.txt"), nx, ny,
          lambda i, j: 0.5 if (i, j) == (16, 10) else (-0.5 if 16 <= i <= 19 else 0.0), "%.4f")
    write(os.path.join(d, "b_bad_face_plot.txt"), nx, ny, lambda i, j: (1 if i <= 10 else 2) if plot(i, j) else 0, "%d")
    write(os.path.join(d, "b_bad_face_out.txt"), nx, ny,
          lambda i, j: {(10, 8): 5, (11, 8): 4}.get((i, j), 0), "%d")


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    d = sys.argv[1]
    drain(d)
    tight(d)
    back(d)
    bank(d)
    chain(d)
    bad(d)


if __name__ == "__main__":
    main()
