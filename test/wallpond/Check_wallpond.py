#!/usr/bin/env python3
"""wallpond の判定(Run.sh・Run_MPI.sh が呼ぶ。developer.md §134)

  python3 Check_wallpond.py        全ケースの結果(result_<case>/)を判定して数表を書く

判定(どれも 3 時間の終わり = E0003・H0003。2 時間の結果 E0002 と比べて定常も確かめる):
  1. 仮想壁面 + 湛水と、仮想壁面 + 乾いた堤内地の河道の水位の差が 1 mm 以下(形 ax2・ax1・dg1 の 4 構成・ob2 と、
     海岸堤防の ax2・dg1)
  2. ax2 の乾いた堤内地と、堤内地を計算しない構成・解像した堤防 + 湛水の構成・海岸堤防 + 乾いた陸の河道の水位の差が
     1 mm 以下(海岸堤防は、開口の動的な振り替えで壁の向こうを塞がっていると数えること = §134.9 の見張りを兼ねる)
  3. 湛水の水位が初めの値(地盤 + 1.5 m)から 1 mm 以内で、2 → 3 時間に 1 mm 以上変わらない(壁から水が漏れない)
  4. 河道の水位の 2 → 3 時間の変化が 2 mm 以下(定常)
  5. ax2・ax1 の乾いた堤内地の区間の中ほど(40〜60 %)の水深が、マニングの等流水深と 1 % 以内

Python の標準ライブラリだけで書く(毎 push の CI で回す。ランナーに numpy はない。developer.md §10)。格子は行のリスト
(行 = 列の値のリスト)で持ち、セルの選び出しは行の順(北から)・列の順に並べたリストにする。
"""
import math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_wallpond as mw

TOL_SAME, TOL_POND, TOL_STEADY, TOL_HN = 1.0e-3, 1.0e-3, 2.0e-3, 0.01


def info(name):
    d = {}
    for line in open(f"d_{name}/info.txt"):
        k, v = line.split()
        d[k] = v
    return d


def loadgrid(path, conv=float):
    """空白区切りの格子の表(1 行が格子の 1 行)を、行のリストで読む"""
    rows = [[conv(v) for v in line.split()] for line in open(path)]
    rows = [r for r in rows if r]
    if any(len(r) != len(rows[0]) for r in rows):
        sys.exit(f"FAIL: {path} の行の長さがそろっていない")
    return rows


def load(name):
    kind = loadgrid(f"d_{name}/kind.txt", int)
    z = loadgrid(f"d_{name}/z.txt")
    e3 = loadgrid(f"result_{name}/E0003.txt")
    e2 = loadgrid(f"result_{name}/E0002.txt")
    for g, f in ((z, "z"), (e3, "E0003"), (e2, "E0002")):
        if len(g) != len(kind) or len(g[0]) != len(kind[0]):
            sys.exit(f"FAIL: {name} の {f} の大きさが kind と違う")
    return kind, z, e2, e3


def pick(grid, sel):
    """sel(格子と同じ大きさの真偽の表)が真のセルの値を、行の順・列の順に並べたリスト"""
    return [v for grow, srow in zip(grid, sel) for v, s in zip(grow, srow) if s]


def where(kind, k):
    """種類が k のセルの真偽の表"""
    return [[v == k for v in row] for row in kind]


def maxdiff(a, b):
    """同じ並びのリストの差の絶対値の最大"""
    if len(a) != len(b):
        sys.exit(f"FAIL: 比べるセルの数が違う({len(a)} と {len(b)})")
    return max(abs(x - y) for x, y in zip(a, b))


def chan_levels(name):
    """河道セルの水位を、行の順(北から)・列の順に並べたリスト"""
    kind, z, e2, e3 = load(name)
    return pick(e3, where(kind, 1))


def main():
    fails = []

    def check(ok, msg):
        print(("  ok   " if ok else "FAIL: ") + msg)
        if not ok:
            fails.append(msg)

    names = [c[0] for c in mw.CASES]
    missing = [n for n in names if not os.path.exists(f"result_{n}/E0003.txt")]
    if missing:
        print("FAIL: 結果がない: " + " ".join(missing))
        sys.exit(1)
    print("== 1. 仮想壁面の向こうの湛水と河道の水位(湛水 − 乾いた堤内地。河道セルの最大の差)")
    pairs = [("ax2_dry", "ax2_wet"), ("ax1_dry", "ax1_wet")] + \
            [(f"dg1_{o}_dry", f"dg1_{o}_wet") for o in mw.OPTS] + \
            [("ax2_sdry", "ax2_swet"), ("dg1_o4_sdry", "dg1_o4_swet"), ("ob2_dry", "ob2_wet")]
    for dry, wet in pairs:
        d = maxdiff(chan_levels(wet), chan_levels(dry))
        check(d <= TOL_SAME, f"{wet:14s} − {dry:14s}: {d:.4f} m(許容 {TOL_SAME * 1000:.0f} mm)")
    print("== 2. 堤内地の表し方(ax2。乾いた堤内地との河道の水位の差)")
    for other in ("ax2_mask", "ax2_levee", "ax2_sdry"):
        d = maxdiff(chan_levels(other), chan_levels("ax2_dry"))
        check(d <= TOL_SAME, f"{other:14s} − ax2_dry       : {d:.4f} m(許容 {TOL_SAME * 1000:.0f} mm)")
    print("== 3. 湛水の水位(初めの水位との差の最大、2 → 3 時間の変化の最大)")
    for name in names:
        if not (name.endswith("wet") or name.endswith("_levee")):
            continue
        kind, z, e2, e3 = load(name)
        pond = where(kind, 5)
        h0 = loadgrid(f"d_{name}/h0.txt")
        if len(h0) != len(z) or len(h0[0]) != len(z[0]):
            sys.exit(f"FAIL: {name} の h0 の大きさが z と違う")
        lev0 = [[zv + hv for zv, hv in zip(zr, hr)] for zr, hr in zip(z, h0)]   # 初めの水位(入力の地盤 + 湛水の深さ)
        d0 = maxdiff(pick(e3, pond), pick(lev0, pond))
        d1 = maxdiff(pick(e3, pond), pick(e2, pond))
        check(d0 <= TOL_POND and d1 <= TOL_POND, f"{name:14s}: 初めとの差 {d0:.4f} m、2 → 3 時間 {d1:.4f} m")
    print("== 4. 定常(河道の水位の 2 → 3 時間の変化の最大)")
    for name in names:
        kind, z, e2, e3 = load(name)
        ch = where(kind, 1)
        d = maxdiff(pick(e3, ch), pick(e2, ch))
        check(d <= TOL_STEADY, f"{name:14s}: {d:.4f} m(許容 {TOL_STEADY * 1000:.0f} mm)")
    print("== 5. 等流水深(区間の中ほど 40〜60 % の水深の平均とマニングの等流水深)")
    for name in ("ax2_dry", "ax1_dry"):
        kind, z, e2, e3 = load(name)
        nx = len(kind[0])
        c0, c1 = int(0.4 * nx), int(0.6 * nx)
        ch = [[v == 1 and c0 <= i < c1 for i, v in enumerate(row)] for row in kind]
        dep = pick([[ev - zv for ev, zv in zip(er, zr)] for er, zr in zip(e3, z)], ch)
        h = math.fsum(dep) / len(dep)
        inf = info(name)
        hn = mw.hn(float(inf["q"]) / float(inf["chan_w"]))
        check(abs(h - hn) / hn <= TOL_HN, f"{name:14s}: 水深 {h:.3f} m、等流水深 {hn:.3f} m(差 {100 * (h - hn) / hn:+.2f} %)")
    print("")
    if fails:
        print(f"FAIL: wallpond ({len(fails)} 件)")
        sys.exit(1)
    print("PASS: wallpond")


if __name__ == "__main__":
    main()
