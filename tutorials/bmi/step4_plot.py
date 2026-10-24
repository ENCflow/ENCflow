# /// script
# dependencies = ["numpy", "matplotlib"]
# ///
"""Step 4: 取り出した水深を Matplotlib で描く(計算終了後に 1 枚)。

使い方: uv run step4_plot.py  (または python3 step4_plot.py)
        → figs/step4_depth.png を保存し、画面があれば表示する
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "bmi" / "python"))
from encflow import ENCflow, VAR_DEPTH, VAR_ELEVATION

T_PLOT = 2.0 * 3600.0                         # 描く時刻 (s): 雨が止んで 1 時間後

with ENCflow("param.txt") as model:
    ny, nx = model.grid_shape
    dy, dx = model.grid_spacing
    z = model.get2d(VAR_ELEVATION)
    model.update_until(T_PLOT)
    h = model.get2d(VAR_DEPTH)

# ここからは普通の Matplotlib。配列の行 0 が南なので origin="lower" で北が上になる
extent = (0.0, nx * dx / 1000.0, 0.0, ny * dy / 1000.0)      # km
land = np.where(z > 0, z, np.nan)                            # 流域外(標高 0)は描かない
wet = np.where(h >= 0.01, h, np.nan)                         # 1 cm 未満は「水なし」

fig, ax = plt.subplots(figsize=(9, 5))
ax.imshow(land, cmap="Greys", origin="lower", extent=extent)
im = ax.imshow(wet, cmap="Blues", origin="lower", extent=extent, vmin=0.0, vmax=3.0)
fig.colorbar(im, ax=ax, shrink=0.8, label="water depth h (m)")
ax.set_title(f"ENCflow via BMI: t = {T_PLOT / 3600:.0f} h,  max h = {np.nanmax(h):.2f} m")
ax.set_xlabel("x (km)")
ax.set_ylabel("y (km)")
fig.tight_layout()

Path("figs").mkdir(exist_ok=True)
fig.savefig("figs/step4_depth.png", dpi=110)
print("saved figs/step4_depth.png")
plt.show()                                   # 画面がない環境では何も起きずに終わる
