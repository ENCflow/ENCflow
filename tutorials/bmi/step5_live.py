# /// script
# dependencies = ["numpy", "matplotlib"]
# ///
"""Step 5: 計算しながら描く(リアルタイム表示)。

使い方: uv run step5_live.py                 # 画面に順次表示
        uv run step5_live.py --save frames   # 画面なし: PNG 連番を frames/ に保存
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "bmi" / "python"))
from encflow import ENCflow, VAR_DEPTH, VAR_ELEVATION

INTERVAL = 300.0                              # 表示間隔 (s)。dt(6 s)の整数倍にする
IP, JP = 147, 104                             # 時系列を描くセル(内部番地 i, j)

save_dir = None
if len(sys.argv) >= 3 and sys.argv[1] == "--save":
    save_dir = Path(sys.argv[2])
    save_dir.mkdir(parents=True, exist_ok=True)
    import matplotlib
    matplotlib.use("Agg")                     # 画面を使わない描画バックエンド
import matplotlib.pyplot as plt

model = ENCflow("param.txt")
ny, nx = model.grid_shape
dy, dx = model.grid_spacing
row, col = ny - JP, IP - 1
z = model.get2d(VAR_ELEVATION)
extent = (0.0, nx * dx / 1000.0, 0.0, ny * dy / 1000.0)

# --- 図の枠を先に作る(左: 水深分布、右: プローブの水深時系列) ---
fig, (ax_map, ax_ts) = plt.subplots(1, 2, figsize=(12, 4.5),
                                    gridspec_kw={"width_ratios": [1.4, 1.0]})
ax_map.imshow(np.where(z > 0, z, np.nan), cmap="Greys", origin="lower", extent=extent)
im = ax_map.imshow(np.full((ny, nx), np.nan), cmap="Blues", origin="lower",
                   extent=extent, vmin=0.0, vmax=3.0)
fig.colorbar(im, ax=ax_map, shrink=0.8, label="h (m)")
ax_map.plot((IP - 0.5) * dx / 1000.0, (ny - JP + 0.5) * dy / 1000.0, "r+", ms=10)
ax_map.set_xlabel("x (km)")
ax_map.set_ylabel("y (km)")
(line,) = ax_ts.plot([], [], lw=2)
ax_ts.set_xlim(0.0, model.end_time / 3600.0)
ax_ts.set_ylim(0.0, 6.0)
ax_ts.set_xlabel("t (h)")
ax_ts.set_ylabel("h (m)")
ax_ts.set_title(f"h at cell (i={IP}, j={JP})")
ax_ts.grid(alpha=0.3)
if save_dir is None:
    plt.ion()                                 # 対話モード: 描画してもスクリプトが止まらない
    plt.show()

times, series = [], []
frame = 0


def draw():
    """いまの水深を取り出して、2 つの図を更新する。"""
    global frame
    h = model.get2d(VAR_DEPTH)
    im.set_data(np.where(h >= 0.01, h, np.nan))
    ax_map.set_title(f"t = {model.time / 3600:4.2f} h   max h = {h.max():.2f} m")
    times.append(model.time / 3600.0)
    series.append(h[row, col])
    line.set_data(times, series)
    if save_dir is None:
        fig.canvas.draw_idle()
        plt.pause(0.01)                       # 画面を更新する(ここで絵が動く)
    else:
        fig.savefig(save_dir / f"frame_{frame:04d}.png", dpi=90)
    frame += 1


draw()                                        # 初期状態
while model.time < model.end_time:            # 計算 → 描画 → 計算 → 描画 …
    model.update_until(min(model.time + INTERVAL, model.end_time))
    draw()
model.finalize()
print(f"finished: {frame} frames")

if save_dir is None:
    plt.ioff()
    plt.show()                                # 最後の絵を表示したまま待つ
