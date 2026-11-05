#!/bin/bash
# salt: 模式実験 B(海水浸入の静的平衡)の逐次実行
#   reference 機構は使わない(np 一致検証は mpirun 実行の result_sea/Log.txt
#   を逐次実行の同ファイルと直接 diff する)
time ./encflow param_sea.txt | tee Screen_sea.log

# 斜めの配分の不一致の検出(developer.md §95): 土層の側方流と塩水 zone は通過幅を共有する
#   ので、salt_diagratio が gw_diagratio と違えば停止する(2026-11-05 まで後の値は黙って
#   無視されていた)。同じ入力で salt_diagratio = 0 を与え、停止することを確かめる
sed -e "s/dir_result = 'result_sea'/dir_result = 'result_sea_dmis'/" \
    -e "s/^&list_salt\$/\&list_salt\n  salt_diagratio = 0.0/" param_sea.txt > wrk_sea_dmis.txt
if ./encflow wrk_sea_dmis.txt > Screen_sea_dmis.log 2>&1; then
    echo "FAIL: salt_diagratio different from gw_diagratio was not detected" >&2
    exit 1
fi
if grep -q "salt_diagratio" Screen_sea_dmis.log && grep -q "differs from gw_diagratio" Screen_sea_dmis.log; then
    echo "=== salt: a salt_diagratio different from gw_diagratio stops the run (shared geometry) PASS ==="
else
    echo "FAIL: the run stopped, but not with the diagratio mismatch message" >&2
    tail -5 Screen_sea_dmis.log >&2
    exit 1
fi
