#!/bin/bash
# prmap: 逐次実行 + 解析検定(降雨分布 prtype = 2・3 の時間の単位と流出率・出力 Pr。developer.md §88)
#   ./Run.sh
# 合否は Check_prmap.py(構成は README.md)。reference 比較なし。
# 各構成の Log.txt は result_serial/ に複製する(Run_MPI.sh の比較用)
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

tags="p2_def p2_min p2_c1h p2_c60 p2_prio p3_def p3_c30 p3_unit p3_prupdate p1_rr p2_rr p3_rr"
for tag in $tags; do
    rm -rf result_$tag
    ./encflow param_$tag.txt > Screen_$tag.log 2>&1 \
        || { echo "ERROR: param_$tag run failed (see Screen_$tag.log)" >&2; exit 1; }
done
# prtype = 3 をフレームの途中(45 min)で保存し、再開する
rm -rf save result_p3_save result_p3_restart
for tag in p3_save p3_restart; do
    ./encflow param_$tag.txt > Screen_$tag.log 2>&1 \
        || { echo "ERROR: param_$tag run failed (see Screen_$tag.log)" >&2; exit 1; }
done
python3 "$sdir/Check_prmap.py" $tags restart || exit 1

rm -rf result_serial && mkdir result_serial
for tag in $tags p3_restart; do cp result_$tag/Log.txt result_serial/Log_$tag.txt; done
echo "=== prmap verification PASS ==="
