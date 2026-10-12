#!/usr/bin/env python3
"""test/culvert の入力データを data_culvert/ に書く(コミット済み。再生成用)。

  python3 make_init.py

- z.txt     : 地盤高。i=1..10 は上流槽(z=0)、i=11 は盛土(z=10)、i=12 は下流列(z=0)
- hinit.txt : 初期水深。上流槽 3.0 m、その他 0
- stage.txt : 水位規定セル(下流列 i=12 の全行。完全排水口 η=-999 を param で指定)
"""
import os
NX, NY = 12, 11
os.makedirs("data_culvert", exist_ok=True)
with open("data_culvert/z.txt", "w") as f:
    for j in range(1, NY + 1):
        f.write(" ".join("10.0" if i == 11 else "0.0" for i in range(1, NX + 1)) + "\n")
with open("data_culvert/hinit.txt", "w") as f:
    for j in range(1, NY + 1):
        f.write(" ".join("3.0" if i <= 10 else "0.0" for i in range(1, NX + 1)) + "\n")
with open("data_culvert/stage.txt", "w") as f:
    for j in range(1, NY + 1):
        f.write("%d %d\n" % (NX, j))
