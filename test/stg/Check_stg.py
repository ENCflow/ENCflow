#!/usr/bin/env python3
"""test/stg の判定(Run.sh・Run_MPI.sh が呼ぶ)。定数は make_init.py と対。

STG(f_gridsystem = 1)の連続式の保存の検定。マスクなしの閉じた矩形の斜面に一様な雨(P mm/h、
全期間一定)を降らせ、計算の終わり(t = TT)の水量を数える。STG は外周の 1 列(i = 1, nx・
j = 1, ny)を計算せず、そこには雨も入らないので、期待値は
    V = P × TT × Δx² × (nx − 2)(ny − 2)
(外周は高い壁で、計算するセルから外周へ出る水はない)。H は float32 の bil(f_output_mode = 3)
から読む(テキストは小数点以下 4 桁で、水量の検定には粗い)。合格の条件:
  - 水量の相対誤差が 1e-5 以下(float32 の丸めの大きさ。1 セル分の漏れでも約 1e-3)
  - 外周の H が 0、H がすべて有限で負でない
  - 水が東の低い側に集まっている(東端の列の平均水深 > 西端の列。流れていることの粗い確認)

  python3 Check_stg.py [result_dir](既定 result_stg)
標準ライブラリだけを使う(CI の実行環境に numpy はない)。
"""
import array
import csv
import glob
import math
import os
import re
import sys

NX, NY, DX, P, TT = 40, 24, 10.0, 60.0, 1800
TOL = 1.0e-5


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else "result_stg"
    fs = sorted(f for f in glob.glob(os.path.join(d, "H[0-9][0-9][0-9][0-9].bil"))
                if int(re.findall(r"(\d{4})\.bil$", f)[0]) < 9000)
    if not fs:
        print(f"FAIL: no H????.bil in {d}")
        return 1
    k = int(re.findall(r"(\d{4})\.bil$", fs[-1])[0])
    t = None
    with open(os.path.join(d, "FILENUMBER.csv")) as f:
        for row in csv.reader(f):
            if row and row[0].strip().isdigit() and int(row[0]) == k:
                t = float(row[2])
    a = array.array("f")                   # float32(bil はリトルエンディアン)
    with open(fs[-1], "rb") as f:
        a.frombytes(f.read())
    if sys.byteorder == "big":
        a.byteswap()
    if len(a) != NX * NY:
        print(f"FAIL: {fs[-1]} has {len(a)} values (expected {NX * NY})")
        return 1
    h = [[float(a[j * NX + i]) for i in range(NX)] for j in range(NY)]
    vol = sum(h[j][i] for j in range(1, NY - 1) for i in range(1, NX - 1)) * DX * DX
    exp = P / 1000.0 / 3600.0 * TT * DX * DX * (NX - 2) * (NY - 2)
    rel = abs(vol - exp) / exp
    ring = h[0] + h[-1] + [h[j][0] for j in range(NY)] + [h[j][-1] for j in range(NY)]
    east = sum(h[j][-2] for j in range(1, NY - 1)) / (NY - 2)
    west = sum(h[j][1] for j in range(1, NY - 1)) / (NY - 2)
    flat = [v for row in h for v in row]
    checks = [
        (t is not None and abs(t - TT) < 1e-6, f"last output {os.path.basename(fs[-1])} at t = {t} s (expected {TT})"),
        (rel <= TOL, f"water volume {vol:.6f} m3 vs rain on the computed cells {exp:.6f} m3 (rel. error {rel:.2e} <= {TOL:.0e})"),
        (all(v == 0.0 for v in ring), f"outer ring dry (max H {max(ring):.3e} m)"),
        (all(math.isfinite(v) and v >= 0.0 for v in flat), f"H finite and non-negative (min {min(flat):.3e} m)"),
        (east > west, f"water collects on the low east side (mean H east {east:.4f} m > west {west:.4f} m)"),
    ]
    nfail = 0
    for ok, msg in checks:
        print(f"  {'ok  ' if ok else 'FAIL'} {msg}")
        nfail += 0 if ok else 1
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
