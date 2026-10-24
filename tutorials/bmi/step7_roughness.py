# /// script
# dependencies = ["numpy"]
# ///
"""Step 7: パラメータ(粗度係数)を Python から書き換える。

同じ雨で、粗度係数 Manning の n を入力値の 1 倍・1.5 倍・2 倍にして
プローブセルの最大水深とそのピーク時刻を比べる。

使い方: uv run step7_roughness.py  (または python3 step7_roughness.py)
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "bmi" / "python"))
from encflow import ENCflow, VAR_DEPTH, VAR_MANNING_N

IP, JP = 147, 104                             # プローブセル(内部番地)


def run(factor):
    with ENCflow("param.txt") as model:
        ny, nx = model.grid_shape
        row, col = ny - JP, IP - 1
        rn = model.get2d(VAR_MANNING_N)       # 入力値(rn0, rn0_rw を適用済み)
        model.set(VAR_MANNING_N, rn * factor)  # 全セル一括で書き換え。次の update から効く
        peak, t_peak = 0.0, 0.0
        while model.time < model.end_time:
            model.update_until(min(model.time + 60.0, model.end_time))
            h = model.get2d(VAR_DEPTH)[row, col]
            if h > peak:
                peak, t_peak = h, model.time
        return peak, t_peak


print(f"probe cell (i={IP}, j={JP})")
print(" n factor   peak h (m)   time of peak")
for factor in (1.0, 1.5, 2.0):
    peak, t_peak = run(factor)
    print(f"   {factor:4.1f}     {peak:8.3f}      {t_peak / 60:5.0f} min")
