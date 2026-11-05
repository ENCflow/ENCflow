#!/bin/bash
# slopefric: 急斜面の薄層流の摩擦(f_gravity_correction = 1 の古典の等流と、2 の斜面に沿う摩擦の等流)
# の検定(逐次実行)
#   ./Run.sh
# make_init.py が 16 ケース(流れ 12 = 下り向き 0°・22.5°・45° × 8・4 近傍 × f_gravity_correction 1・2、
# 掃流砂 4 = 下り向き 0°・45° × f_gravity_correction 1・2)の入力と
# 設定を生成し、全ケースを実行して Check_slopefric.py が等流の解析解に比べる。reference は持たない。
# 画面出力は Screen.log にまとめる。実行後の save_<case>/ は save_<case>_serial/ にも複製する
# (Run_MPI.sh のバイト比較用)
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
python3 "$sdir/Check_slopefric.py" table || rc=1
for c in $cases; do
    rm -rf save_${c}_serial && cp -r save_$c save_${c}_serial
done
exit $rc
