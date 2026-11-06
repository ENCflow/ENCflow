#!/bin/bash
# steepwave: 水面の勾配の項の可変の重力 g′(f_gravity_correction = 3。Yuan ら 2016 の式 42 の水の場合。
# developer.md §100)の検定(逐次実行)
#   ./Run.sh
# make_init.py が 3 構成(lake: 急な湖岸の静止した湖 / wave: 急な湖底を渡る長波 / bump: 摩擦のない斜面の
# 一様な層の上の小さな山)の入力と設定を f_gravity_correction の値ごとに生成し、全ケースを実行して
# Check_steepwave.py が判定する。reference は持たない。画面出力は Screen.log にまとめる。実行後の
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
python3 "$sdir/Check_steepwave.py" table || rc=1
for c in $cases; do
    rm -rf save_${c}_serial && cp -r save_$c save_${c}_serial
done
exit $rc
