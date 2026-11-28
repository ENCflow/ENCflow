#!/bin/bash
# saltledger: 淡塩2層の塩水の台帳 salt.csv と、構造物による地表の塩水層の転送 f_salt_struct の検定
#             (逐次実行。developer.md §140)
#   ./Run.sh
# 9 ケース(param_<名前>.txt)を実行し、Check_cases.sh(Check_saltledger.py)が台帳の閉合と、経路ごとの
# 解析的な値で判定する。reference は持たない。画面出力は Screen.log
sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

cases="sea evap pump0 pump1 pump2 xfer exin exout gwsea"
: > Screen.log
for c in $cases; do
    echo "--- $c"
    rm -rf result_$c
    if ! ./encflow param_$c.txt >> Screen.log 2>&1; then
        echo "FAIL: $c の実行が異常終了した(Screen.log)" >&2
        exit 1
    fi
done
echo ""

rc=0
"$sdir/Check_cases.sh" || rc=1
if [ $rc -eq 0 ]; then
    echo "=== saltledger verification PASS ==="
else
    echo "=== saltledger verification FAIL ===" >&2
fi
exit $rc
