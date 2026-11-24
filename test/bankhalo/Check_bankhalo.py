#!/usr/bin/env python3
"""test/bankhalo の検定(Python 標準ライブラリのみ。developer.md §120)。

  python3 Check_bankhalo.py <結果のディレクトリ> ...

各結果について、閉じた箱の水の量が保たれること(Log の S の最初と最後が相対 1e-12 で一致)と、深く潜った
堤防を越えて両岸の水位差が縮まること(初め 0.05 m → 終わりに半分未満、東岸の水位が 5 mm 以上上がる)を
確かめる。ランク数によらないこと(1 ランクとのバイト一致)は Run_MPI.sh が確かめる。
"""
import os
import sys

IC = 9           # 河道の列(0 始まり)


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(1)


def ok(msg):
    print("  ok   " + msg)


def read_s(path):
    out = []
    with open(path) as f:
        for line in f:
            t = line.split()
            if t and t[0][0].isdigit():
                out.append(float(t[2]))
    return out


def read_matrix(path):
    with open(path) as f:
        return [[float(x) for x in line.split()] for line in f if line.strip()]


def side_means(e):
    west = [r[i] for r in e for i in range(IC)]
    east = [r[i] for r in e for i in range(IC + 1, len(r))]
    return sum(west) / len(west), sum(east) / len(east)


def check(res):
    s = read_s(os.path.join(res, "Log.txt"))
    if len(s) < 2:
        fail("%s: Log.txt has no records" % res)
    if abs(s[-1] - s[0]) > 1e-12 * abs(s[0]):
        fail("%s: water volume S changes from %.15f to %.15f in the closed box" % (res, s[0], s[-1]))
    ok("%s: S conserved in the closed box (%.15f m)" % (res, s[0]))
    w0, e0 = side_means(read_matrix(os.path.join(res, "E0000.txt")))
    w1, e1 = side_means(read_matrix(os.path.join(res, "E0001.txt")))
    d0, d1 = w0 - e0, w1 - e1
    if not (d1 < 0.5 * d0):
        fail("%s: the level difference across the levees does not shrink enough (%.4f -> %.4f m)" % (res, d0, d1))
    if not (e1 > e0 + 0.005):
        fail("%s: the east side does not rise through the submerged levees (%.4f -> %.4f m)" % (res, e0, e1))
    ok("%s: level difference across the submerged levees %.4f -> %.4f m, east side %.4f -> %.4f m"
       % (res, d0, d1, e0, e1))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    for res in sys.argv[1:]:
        check(res)
    print("PASS: bankhalo")


if __name__ == "__main__":
    main()
