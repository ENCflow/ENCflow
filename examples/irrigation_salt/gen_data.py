#!/usr/bin/env python3
"""irrigation_salt の入力(data_irrigation/)を作る。
  z_flat.txt   平らな農地(41 × 5 セル、dx = 20 m。地盤高 10 m)
  z_drain.txt  同じ農地の東端の 1 列を、深さ 3.5 m の排水路(地盤高 6.5 m)にしたもの
行は北から南、列は西から東。"""
import os

NX, NY = 41, 5
D = "data_irrigation"
os.makedirs(D, exist_ok=True)
for name, zd in (("z_flat.txt", 10.0), ("z_drain.txt", 6.5)):
    with open(os.path.join(D, name), "w") as f:
        for _ in range(NY):
            f.write(" ".join(["10.0"] * (NX - 1) + ["%.1f" % zd]) + "\n")
print("wrote", sorted(os.listdir(D)))
