#!/usr/bin/env python3
"""dbonset(降伏による静止と動き出し)の検定。

  使い方: Check_dbonset.py [table]   (table を付けると判定の前にケースごとの値を表で出す)

一様な斜面の全面の層(make_init.py)の、壁から MARGIN 以上離れた内部の流速を、計算終了時刻 T の
出力(u・v)から読み、剛体の滑りの解析解と比べる。
  解析解: G < μ なら静止、G > μ なら V(T) = g (G − μ) T、向きは斜面の下り向き
          (μ = tanφ sC/(1 + sC)。make_init.py と同じ定数。重力補正なし)
  (1) 静止: G = 0.9 μ の全ケースで内部の速さの最大が 0
  (2) 速さ: G = 1.1 μ・1.3 μ の全ケースで内部の速さの平均が解析解に相対 TOL_V 以内
  (3) 一様: 内部の速さの (最大 − 最小)/ 平均 が TOL_U 以内(層全体が一体で滑る)
  (4) 向き: 内部の平均流速の向きが斜面の下り向きから TOL_DEG 以内
(2)〜(4) は谷の向き 0°・22.5°・45° と 8 近傍・4 近傍のすべてで判定する(格子の向きによらない
ことの検定)。出力は f12.4 の印字なので、速さの比較は印字の桁で足りる大きさの許容にしている。
流速の v は格子の行が増える向き(南)が正なので、向きは atan2(−v, u) で求める。
"""
import math
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_init as mi

G = 9.8                      # param の gg(既定)と対
MARGIN = 18.0                # 壁からの距離 (m)。壁で生じる乱れは T までに 13 m ほど入り込む
TOL_V, TOL_U, TOL_DEG = 0.015, 0.01, 0.5


def read_txt(path):
    return [[float(v) for v in line.split()] for line in open(path) if line.strip()]


def interior(case):
    """内部セルの (u, v) の一覧(出力の最後の通常フレーム)。"""
    rdir = f"result_{case}"
    k = max(int(l.split(",")[0]) for l in open(f"{rdir}/FILENUMBER.csv")
            if not l.startswith("#") and int(l.split(",")[0]) < 9000)
    u = read_txt(f"{rdir}/u{k:04d}.txt")[::-1]      # 行 0 が南端
    v = read_txt(f"{rdir}/v{k:04d}.txt")[::-1]
    n = len(u)
    out = []
    for j in range(n):
        y = (j + 0.5) * mi.DX
        for i in range(n):
            x = (i + 0.5) * mi.DX
            if min(x, y, mi.L - x, mi.L - y) >= MARGIN:
                out.append((u[j][i], v[j][i]))
    return out


def main():
    show = "table" in sys.argv[1:]
    ok = True
    rows = []
    for ratio, theta, nb in mi.CASES:
        case = mi.case_name(ratio, theta, nb)
        uv = interior(case)
        sp = [math.hypot(a, b) for a, b in uv]
        g = ratio * mi.MU
        vref = max(G * (g - mi.MU) * mi.TT, 0.0)
        um = sum(a for a, _ in uv) / len(uv)
        vm = sum(b for _, b in uv) / len(uv)
        smean = sum(sp) / len(sp)
        ang = math.degrees(math.atan2(-vm, um)) if smean > 0 else float("nan")
        rows.append((case, ratio, theta, nb, vref, smean, max(sp), min(sp), ang))
        if ratio < 1.0:
            if max(sp) != 0.0:
                print(f"FAIL (1) {case}: 静止しない(内部の速さの最大 {max(sp):.4f} m/s)")
                ok = False
        else:
            if abs(smean / vref - 1.0) > TOL_V:
                print(f"FAIL (2) {case}: 内部の速さ {smean:.4f} m/s が解析解 {vref:.4f} m/s から "
                      f"{100 * (smean / vref - 1):+.1f} %")
                ok = False
            if smean <= 0.0:
                print(f"FAIL (3)(4) {case}: 内部が動かない")
                ok = False
                continue
            if (max(sp) - min(sp)) / smean > TOL_U:
                print(f"FAIL (3) {case}: 内部の速さが一様でない({min(sp):.4f}〜{max(sp):.4f} m/s)")
                ok = False
            dang = (ang - theta + 180.0) % 360.0 - 180.0
            if abs(dang) > TOL_DEG:
                print(f"FAIL (4) {case}: 流れの向き {ang:.2f}° が斜面の下り向き {theta:g}° から {dang:+.2f}°")
                ok = False
    if show or not ok:
        print("case              G/mu  theta nb   V_ref   V_mean   V_max    V_min   angle")
        for case, ratio, theta, nb, vref, sm, smax, smin, ang in rows:
            print(f"{case:16s} {ratio:5.2f} {theta:6.1f} {nb:2d} {vref:7.4f} {sm:8.4f} {smax:8.4f} {smin:8.4f} {ang:7.2f}")
    print("=== dbonset " + ("PASS" if ok else "FAIL") + " ===")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
