#!/bin/bash
# dbonset: 降伏(f_dbres = 1 のクーロン摩擦)による静止と動き出しが格子の向きによらないことの
# 検定(逐次実行)
#   ./Run.sh
# make_init.py が 45 ケース(降伏 36 = 斜面の勾配 3 × 下り向き 0°・22.5°・45° × 8・4 近傍 × 重力補正
# なし・あり、斜面安定判定の安全率 9 = 勾配 3 × 下り向き 3)の入力と設定を生成し、全ケースを実行して
# Check_dbonset.py が剛体の滑りの解析解と Fs = tanφs/tanθ に比べる。reference は持たない。
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
python3 "$sdir/Check_dbonset.py" table || rc=1
for c in $cases; do
    rm -rf save_${c}_serial && cp -r save_$c save_${c}_serial
done
exit $rc
