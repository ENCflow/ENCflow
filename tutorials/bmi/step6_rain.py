# /// script
# dependencies = ["numpy"]
# ///
"""Step 6: 雨を Python から与える(set)。

ラン A: param.txt(雨はパラメータファイル)。
ラン B: param_norain.txt(雨なし)に、同じ雨を Python から set で与える。
終了時の水深が A と B で一致する(同じ雨なら与え方によらない)ことを確かめ、
最後にラン C で「西半分だけに降る雨」という分布つきの雨を与える。

使い方: uv run step6_rain.py  (または python3 step6_rain.py)
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "bmi" / "python"))
from encflow import ENCflow, VAR_DEPTH, VAR_PRECIP, BmiError

MMH = 1.0e-3 / 3600.0                       # mm/h → m/s


PRVAL = [(0.0, 0.0), (1800.0, 200.0), (3600.0, 0.0)]   # param.txt の prval(時刻は秒に換算)


def rain_rate(t):
    """時刻 t (s) の雨量強度 (mm/h)。ENCflow と同じく prval の点を直線でつなぐ。"""
    if t <= PRVAL[0][0]:
        return PRVAL[0][1]
    if t > PRVAL[-1][0]:
        return PRVAL[-1][1]
    for (t0, r0), (t1, r1) in zip(PRVAL[:-1], PRVAL[1:]):
        if t < t1:
            return r0 + (t - t0) / (t1 - t0) * (r1 - r0)
    return PRVAL[-1][1]


def run(param, pattern=None):
    """pattern が None なら雨はパラメータファイル任せ。
    配列なら、各ステップの前に rain_rate(t) × pattern を set する。"""
    with ENCflow(param) as model:
        if pattern is None:
            try:
                model.set(VAR_PRECIP, np.zeros(model.grid_shape))
            except BmiError as e:
                print("   set(VAR_PRECIP) refused as expected:", e)
        dt = model.time_step
        while model.time < model.end_time:
            t_next = model.time + dt                        # これから進む 1 歩の終端時刻
            if pattern is not None and round(t_next) % 60 == 0:
                # ENCflow の &list_precip は 1 分ごと(dt_prupdate)に、ステップ終端の
                # 時刻で雨量強度を評価する。同じ時刻・同じ値を set すれば結果は一致する
                rate = rain_rate(t_next) * MMH              # (m/s)
                field = np.full(model.grid_shape, rate) * pattern   # (ny, nx) の分布にする
                model.set(VAR_PRECIP, field)                # 次の update の冒頭で適用され、次の set まで持続
            model.update()
        return model.get2d(VAR_DEPTH)


print("run A: rain from param.txt")
h_a = run("param.txt")

print("run B: rain supplied from Python (uniform)")
h_b = run("param_norain.txt", pattern=1.0)
print(f"   max |h_B - h_A| = {np.abs(h_b - h_a).max():.3e} m")

print("run C: rain only on the western half")
ny, nx = h_a.shape
west = np.zeros((ny, nx))
west[:, : nx // 2] = 1.0
h_c = run("param_norain.txt", pattern=west)
print(f"   max h: A = {h_a.max():.2f} m,  C = {h_c.max():.2f} m")
