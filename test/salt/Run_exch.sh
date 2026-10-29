#!/bin/bash
# salt: 模式実験 C1〜C4(地表—地下の交換の淡塩配分 f_salt_exch)の逐次実行と検定
#   reference 機構は使わない(C1 は解析終状態、C2〜C4 は湧き出る水の塩水と塩水体積を
#   Check_exch.py が倍精度の保存状態から判定する。np 一致検証は mpirun 実行の
#   result_exch_*/Log.txt を逐次実行の同ファイルと直接 diff する)
set -e
time ./encflow param_exch_in.txt | tee Screen_exch_in.log
time ./encflow param_exch_out.txt | tee Screen_exch_out.log
time ./encflow param_exch_dtg.txt | tee Screen_exch_dtg.log
time ./encflow param_exch_mix1.txt | tee Screen_exch_mix1.log
time ./encflow param_exch_mix2.txt | tee Screen_exch_mix2.log
python3 Check_exch.py
