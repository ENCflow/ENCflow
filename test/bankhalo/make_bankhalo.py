#!/usr/bin/env python3
"""test/bankhalo の入力を作る(Python 標準ライブラリのみ)。

20 × 16 セル(Δx = Δy = 10 m)。列 i = 10 が南北に通る河道(河床 −1 m、サブグリッド幅 4 m)で、
両岸の地盤は 0 m。河道セルの堤防は天端 0.5 m(堤内地の地盤 + 0.5 m)。初期の水位は西岸 1.50 m、
東岸 1.45 m、河道 1.475 m で、堤防は深く潜っている(潜り越流の追い越し上限が効く)。
行の並びは j によらない(全行が同じ値)。

  python3 make_bankhalo.py z|rw|w|e > ファイル
"""
import sys

NX, NY = 20, 16
IC = 9            # 河道の列(0 始まり。i = 10)


def value(kind, i):
    if kind == "z":
        return "%.4f" % (-1.0 if i == IC else 0.0)
    if kind == "rw":
        return "1" if i == IC else "0"
    if kind == "w":
        return "%.4f" % (4.0 if i == IC else 0.0)
    if kind == "e":
        return "%.4f" % (1.50 if i < IC else (1.45 if i > IC else 1.475))
    raise SystemExit("unknown kind: " + kind)


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    kind = sys.argv[1]
    for _ in range(NY):
        print(" ".join(value(kind, i) for i in range(NX)))


if __name__ == "__main__":
    main()
