#!/bin/bash
# dbslope: 混合体流動の抵抗則を斜面に沿って評価する f_gravity_correction = 2 の検定(developer.md §101)。
# 逐次実行
#   ./Run.sh
# make_init.py が 8 ケース(Voellmy・江頭・高橋・中川の石礫型・掃流状集合流動 × f_gravity_correction 1・2。
# 30° の斜面の等流)の入力と設定を生成し、全ケースを実行して
# Check_dbslope.py が判定する。reference は持たない。画面出力は Screen.log にまとめる。実行後の
# save_<case>/ は save_<case>_serial/ にも複製する(Run_MPI.sh のバイト比較用)
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

python3 "$sdir/make_init.py" || exit 1
cases=$(python3 "$sdir/make_init.py" list)

: > Screen.log
for c in $cases; do
    echo "--- $c"
    if ! ./encflow p_$c.txt >> Screen.log 2>&1; then
        echo "FAIL: $c の実行が異常終了した(Screen.log)" >&2
        exit 1
    fi
done
echo ""
rc=0
python3 "$sdir/Check_dbslope.py" table || rc=1
for c in $cases; do
    rm -rf save_${c}_serial && cp -r save_$c save_${c}_serial
done
exit $rc
