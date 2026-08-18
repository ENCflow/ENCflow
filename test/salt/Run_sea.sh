#!/bin/bash
# salt: 模式実験 B(海水浸入の静的平衡)の逐次実行
#   reference 機構は使わない(np 一致検証は mpirun 実行の result_sea/Log.txt
#   を逐次実行の同ファイルと直接 diff する)
time ./encflow param_sea.txt | tee Screen_sea.log
