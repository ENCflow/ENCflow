#!/usr/bin/env python3
"""test/wqstruct の入力データを data_wqstruct/ に書く(コミット済み。再生成用)。

  python3 make_data.py

17 × 17 セル(10 m 格子)を高さ 10 m の壁で 4 × 4 = 16 の閉じた区画に分ける。
区画 (r, c)(r = 北から 0..3、c = 西から 0..3)の内部は 3 × 3 セル
(i = 4c+2..4c+4, j = 4r+2..4r+4)、壁は i または j が 1, 5, 9, 13, 17 の列・行。

- z.txt      : 地盤高。区画の内部 0 m、壁 10 m
- hinit.txt  : 初期水深(区画ごと。下の HINIT。壁は 0)
- gv.txt     : 家屋の空隙率。区画 (3,0) の全セル 0.5、(3,3) のセル 0.7、他は 1
- rw.txt     : 河道マスク(サブグリッド河道幅を置く 2 セル)
- width.txt  : サブグリッド河道幅 2 m(wfrac = 0.2)
- rscap.txt  : ため池の限界貯留高 0.5 m(区画 (2,0) の中央セル)
- gwc_cap.txt: param_gw.txt の管路の貯留容量 0.5 m(区画 (0,1) の 1 セル)

param.txt・param_gw.txt のセル番号はこの配置を前提にする(README の表)。
"""
import os

NX = NY = 17
DIR = "data_wqstruct"

# 区画ごとの初期水深 (m)
HINIT = {
    (0, 0): 1.0,   # A: ポンプ P1 の取水側(域内へ)
    (0, 1): 1.0,   # C: ポンプ P2(域外へ)
    (0, 2): 1.5,   # D: カルバート K1 の上流側(順流)
    (0, 3): 0.5,   # F: カルバート K2 の上流側(逆流で受ける)
    (1, 0): 1.0,   # H: 分水 V1(域外へ)
    (1, 1): 1.0,   # I: 内部ソースの吸い込み S1
    (1, 2): 0.5,   # E: カルバート K1 の下流側
    (1, 3): 1.5,   # G: カルバート K2 の下流側(逆流の送り元)
    (2, 0): 1.0,   # J: ため池(中央セル)+ ポンプ P3 の取水側
    (2, 1): 1.5,   # L: 分水 V2 の取水側(域内へ)
    (2, 2): 1.0,   # N: 対照(構造物なし)
    (2, 3): 0.0,   # O: ポンプ P4 の送り先(乾いた区画)
    (3, 0): 1.0,   # B: ポンプ P1 の送り先(空隙率 0.5、1 セルは河道幅あり)
    (3, 1): 1.0,   # K: ポンプ P3 の送り先
    (3, 2): 0.5,   # M: 分水 V2 の送り先
    (3, 3): 1.0,   # Q: ポンプ P4 の取水側(1 セルは空隙率 0.7)
}
GV = {(3, 0): 0.5}             # 区画全体の空隙率
GV_CELL = {(15, 15): 0.7}      # セル単位の空隙率(P4 の取水セル)
WIDTH_CELL = {(4, 16): 2.0,    # P1 の送り先の 1 セル(空隙率 0.5 と重なる)
              (7, 3): 2.0}     # P2 の取水セル
RSCAP_CELL = {(3, 11): 0.5}    # ため池(P3 の取水セル)
GWC_CAP_CELL = {(7, 3): 0.5}   # param_gw.txt の管路(P1 の取水セル)


def comp_of(i, j):
    """セル (i, j)(1 始まり)が属する区画 (r, c)。壁なら None。"""
    if (i - 1) % 4 == 0 or (j - 1) % 4 == 0:
        return None
    return ((j - 2) // 4, (i - 2) // 4)


def write(name, fn, fmt="%.3f"):
    with open(os.path.join(DIR, name), "w") as f:
        for j in range(1, NY + 1):
            f.write(" ".join(fmt % fn(i, j) for i in range(1, NX + 1)) + "\n")


def main():
    os.makedirs(DIR, exist_ok=True)
    write("z.txt", lambda i, j: 10.0 if comp_of(i, j) is None else 0.0)
    write("hinit.txt", lambda i, j: 0.0 if comp_of(i, j) is None else HINIT[comp_of(i, j)])

    def gv(i, j):
        if (i, j) in GV_CELL:
            return GV_CELL[(i, j)]
        return GV.get(comp_of(i, j), 1.0)
    write("gv.txt", gv)
    write("rw.txt", lambda i, j: 1 if (i, j) in WIDTH_CELL else 0, "%d")
    write("width.txt", lambda i, j: WIDTH_CELL.get((i, j), 0.0), "%.1f")
    write("rscap.txt", lambda i, j: RSCAP_CELL.get((i, j), 0.0), "%.2f")
    write("gwc_cap.txt", lambda i, j: GWC_CAP_CELL.get((i, j), 0.0), "%.2f")


if __name__ == "__main__":
    main()
