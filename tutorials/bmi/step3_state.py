# /// script
# dependencies = ["numpy"]
# ///
"""Step 3: 計算の途中で状態(水深)を取り出す。

使い方: uv run step3_state.py  (または python3 step3_state.py)
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "bmi" / "python"))
from encflow import ENCflow, VAR_DEPTH, VAR_ELEVATION

with ENCflow("param.txt") as model:
    ny, nx = model.grid_shape                 # 格子の形(行数 ny, 列数 nx)
    dy, dx = model.grid_spacing               # セルの大きさ (m)
    print("grid:", nx, "x", ny, "cells of", dx, "m")
    print("variables you can get:")
    for name in model.output_var_names:
        print("   ", name)

    z = model.get2d(VAR_ELEVATION)            # 標高 (ny, nx)。行 0 = 南端
    print(f"elevation: {np.nanmin(z[z > 0]):.0f} .. {z.max():.0f} m")

    # ENCflow 内部のセル番地 (i, j)(1 始まり、j = 1 が北)→ 配列の添字
    ip, jp = 147, 104                         # chichibu チュートリアル Step 3 のプローブ 3(本川中流)
    row, col = ny - jp, ip - 1
    print(f"probe cell (i={ip}, j={jp}) -> h[{row}, {col}],  z = {z[row, col]:.1f} m")

    print(" time(s)   h_probe(m)   h_max(m)   wet cells")
    while model.time < model.end_time:
        model.update_until(min(model.time + 1800.0, model.end_time))
        h = model.get2d(VAR_DEPTH)            # 水深のコピー (ny, nx)
        wet = int(np.count_nonzero(h > 0.01))
        print(f"{model.time:8.0f}   {h[row, col]:9.3f}   {h.max():8.3f}   {wet:9d}")
