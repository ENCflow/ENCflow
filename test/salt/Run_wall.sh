#!/bin/bash
# salt: 模式実験 D1・D2(地表の底層重力流と堤防・海岸堤防の仮想壁)の逐次実行と検定
#   reference 機構は使わない(Check_wall.py が倍精度の保存状態から解析終状態と照合する)
set -e
time ./encflow param_wall_bank.txt | tee Screen_wall_bank.log
time ./encflow param_wall_sea.txt | tee Screen_wall_sea.log
python3 Check_wall.py
