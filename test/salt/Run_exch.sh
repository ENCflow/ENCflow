#!/bin/bash
# salt: 模式実験 C1・C2(地表—地下の交換の淡塩配分 f_salt_exch)の逐次実行と検定
#   reference 機構は使わない(C1 は解析終状態、C2 は塩水の湧出の有無を
#   Check_exch.py が倍精度の保存状態から判定する。np 一致検証は mpirun 実行の
#   result_exch_*/Log.txt を逐次実行の同ファイルと直接 diff する)
set -e
time ./encflow param_exch_in.txt | tee Screen_exch_in.log
time ./encflow param_exch_out.txt | tee Screen_exch_out.log
python3 Check_exch.py
