# /// script
# dependencies = ["numpy"]
# ///
"""Step 2: 時間を進める(update と update_until)。

使い方: uv run step2_time.py  (または python3 step2_time.py)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "bmi" / "python"))
from encflow import ENCflow

with ENCflow("param.txt") as model:         # with を抜けるとき finalize が自動で呼ばれる
    dt = model.time_step

    model.update()                          # 1 ステップ(dt 秒)だけ進める
    print(f"after update():       t = {model.time:g} s")

    model.update_until(600.0)               # 指定した時刻まで進める(dt の整数倍の時刻)
    print(f"after update_until(): t = {model.time:g} s")

    interval = 1800.0                       # ここから 30 分ごとに進めて進捗を表示する
    while model.time < model.end_time:
        target = min(model.time + interval, model.end_time)
        model.update_until(target)
        print(f"t = {model.time:7.0f} s  ({model.time / model.end_time:5.1%})")

print("finished")
