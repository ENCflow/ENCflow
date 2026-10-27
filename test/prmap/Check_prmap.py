#!/usr/bin/env python3
# prmap(降雨分布 prtype = 2・3 の時間の単位)の検定(developer.md §88)
#   使い方: Check_prmap.py [tag ...]   (省略時は全構成)
#   読むもの: result_<tag>/Log.txt と Screen_<tag>.log(Run.sh・Run_MPI.sh が作る)
#
#   4 × 8 セルの平坦な閉領域に一様な雨を与えるので、Log の S(領域平均の水深)は
#   降った雨の積算に等しい。ステップ it(時刻 (it−1)·dt → it·dt)の降水強度は
#     prtype = 2: 分布の値 × 倍率 / dt_mapunit(倍率は 1 で一定)
#     prtype = 3: フレーム k = it // n + 1 の値 / dt_mapunit(n = dt_maplist / dt
#                 ステップ。切替はステップの終わりの時刻で判定するので、最初の
#                 フレームだけ 1 ステップ短い。リストの後は 0)
#   で、これを積算した S と Log の S を比べる(相対 1e-9。Log の表示 14 桁の丸めは
#   最小の S でも 3e-11、単位の取り違えは 24 倍・60 倍の差になる)。同じ指定の
#   別表現(数値の分・単位付きの文字列・単位を省いた文字列・*_c の優先)の Log が
#   ビット一致すること、画面に採用値が表示されることも確かめる。構成は
#   param_*.txt と対で保守する。
import os
import sys

DT, TT = 10.0, 5400.0
MAP2 = 24.0                     # prmap.txt の値 (mm)
FRAMES = [6.0, 12.0, 0.0]       # f1〜f3.txt の値 (mm)
RTOL = 1e-9

# tag: (prtype, dt_mapunit (min), dt_maplist (min), 画面の採用値, ビット一致すべき構成)
CASES = {
    "p2_def": (2, 1440.0, None, ["precip: dt_mapunit = 1440.00000 min (default)"], None),
    "p2_min": (2, 60.0, None, ["precip: dt_mapunit = 60.00000 min"], None),
    "p2_c1h": (2, 60.0, None, ["precip: dt_mapunit = 60.00000 min"], "p2_min"),
    "p2_c60": (2, 60.0, None, ["precip: dt_mapunit = 60.00000 min"], "p2_min"),
    "p2_prio": (2, 1440.0, None, ["precip: dt_mapunit = 1440.00000 min"], "p2_def"),
    "p3_def": (3, 30.0, 30.0, ["precip: dt_maplist = 30.00000 min (180 steps)",
                               "precip: dt_mapunit = 30.00000 min (default)"], None),
    "p3_c30": (3, 30.0, 30.0, ["precip: dt_maplist = 30.00000 min (180 steps)",
                               "precip: dt_mapunit = 30.00000 min (default)"], "p3_def"),
    "p3_unit": (3, 60.0, 30.0, ["precip: dt_maplist = 30.00000 min (180 steps)",
                                "precip: dt_mapunit = 60.00000 min"], None),
}


def hms(s):
    h, m, sec = s.split(":")
    return int(h) * 3600 + int(m) * 60 + float(sec)


def read_log(path):
    rows = []
    with open(path) as f:
        for line in f:
            if line.startswith("time"):
                continue
            c = line.split()
            rows.append((hms(c[0]), float(c[2])))
    return rows


def rate(case, it):
    # ステップ it の降水強度 (m/s)
    prtype, unit_min, list_min = case[0], case[1], case[2]
    if prtype == 2:
        val = MAP2
    else:
        k = it // int(round(list_min * 60 / DT))
        val = FRAMES[k] if k < len(FRAMES) else 0.0
    return val / 1000.0 / (unit_min * 60.0)


def expected(case, t):
    return sum(rate(case, it) * DT for it in range(1, int(round(t / DT)) + 1))


def main(tags):
    nfail = 0

    def check(ok, msg):
        nonlocal nfail
        print(("  ok   " if ok else "  FAIL ") + msg)
        if not ok:
            nfail += 1

    for tag in tags:
        case = CASES[tag]
        print(f"== prmap {tag}")
        log = f"result_{tag}/Log.txt"
        if not os.path.exists(log):
            check(False, f"{log} not found")
            continue
        rows = read_log(log)
        check(abs(rows[-1][0] - TT) < 1e-6, f"Log reaches t = {TT:g} s ({len(rows)} rows)")
        err = max(abs(s - expected(case, t)) / max(expected(case, t), 1e-30)
                  for t, s in rows if t > 0)
        check(err < RTOL, f"S = accumulated map value / dt_mapunit (max rel err {err:.1e}; "
              f"S(end) = {rows[-1][1] * 1000:.4f} mm)")
        with open(f"Screen_{tag}.log") as f:
            screen = f.read()
        for line in case[3]:
            check(line in screen, f"screen shows '{line}'")
        if case[4]:
            with open(log, "rb") as f1, open(f"result_{case[4]}/Log.txt", "rb") as f2:
                check(f1.read() == f2.read(), f"Log.txt identical to {case[4]}")

    if nfail:
        print(f"=== prmap check FAIL ({nfail}) ===")
        return 1
    print("=== prmap check PASS ===")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:] or list(CASES)
    bad = [a for a in args if a not in CASES]
    if bad:
        sys.exit(f"usage: Check_prmap.py [tag ...]  (unknown: {' '.join(bad)}; known: {' '.join(CASES)})")
    sys.exit(main(args))
