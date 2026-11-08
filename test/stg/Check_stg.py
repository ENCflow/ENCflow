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
"""
import csv
import glob
import os
import re
import sys

import numpy as np

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
    h = np.fromfile(fs[-1], dtype="<f4").reshape(NY, NX).astype(np.float64)
    vol = h[1:-1, 1:-1].sum() * DX * DX
    exp = P / 1000.0 / 3600.0 * TT * DX * DX * (NX - 2) * (NY - 2)
    rel = abs(vol - exp) / exp
    ring = np.concatenate([h[0, :], h[-1, :], h[:, 0], h[:, -1]])
    east, west = h[1:-1, -2].mean(), h[1:-1, 1].mean()
    checks = [
        (t is not None and abs(t - TT) < 1e-6, f"last output {os.path.basename(fs[-1])} at t = {t} s (expected {TT})"),
        (rel <= TOL, f"water volume {vol:.6f} m3 vs rain on the computed cells {exp:.6f} m3 (rel. error {rel:.2e} <= {TOL:.0e})"),
        (np.all(ring == 0.0), f"outer ring dry (max H {ring.max():.3e} m)"),
        (np.isfinite(h).all() and (h >= 0.0).all(), f"H finite and non-negative (min {h.min():.3e} m)"),
        (east > west, f"water collects on the low east side (mean H east {east:.4f} m > west {west:.4f} m)"),
    ]
    nfail = 0
    for ok, msg in checks:
        print(f"  {'ok  ' if ok else 'FAIL'} {msg}")
        nfail += 0 if ok else 1
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
