# /// script
# dependencies = ["numpy"]
# ///
"""Step 1: Python から ENCflow を起動して、何もせずに終了する。

使い方(このディレクトリで):
    uv run step1_hello.py          # uv を使う場合
    python3 step1_hello.py         # numpy 入りの Python を使う場合
"""
import sys
from pathlib import Path

# Python ラッパー(bmi/python/encflow.py)の場所を Python に教える
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "bmi" / "python"))
from encflow import ENCflow

model = ENCflow("param.txt")        # initialize: 入力を読んで計算の準備をする
print("component :", model.name)
print("grid      :", model.grid_shape, "(ny, nx)")
print("time      :", model.time, "->", model.end_time, "s   dt =", model.time_step, "s")
model.finalize()                    # finalize: 後始末をして計算を閉じる
print("finished without advancing time")
