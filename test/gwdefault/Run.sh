#!/bin/bash
# gwdefault: 地下水パラメータの既定値の同値検定(逐次実行。developer.md §64)
#   ./Run.sh
# 構成 a(バケツ)・b(Green-Ampt+側方+層2)・c(Green-Ampt+凍土)・
# d(管路連続体層+浸入水)の各々について、最小入力(param_X.txt。既定値を
# 使う)と既定値をすべて明示した対照(param_Xx.txt)を実行し、save の
# 全ファイル(state.dat と各モデルの私有ファイル)と result の Log.txt が
# バイト一致することを検定する。reference 機構は使わない(対照が基準)。
# 実行後の save_X は save_X_serial にも複製する(Run_MPI.sh のバイト比較用)

../Scripts/Check_mode.sh serial || exit 1
rc=0
rm -f Screen.log
for tag in a b c d; do
    set -o pipefail
    ./encflow param_${tag}.txt  | tee -a Screen.log || exit 1
    ./encflow param_${tag}x.txt | tee -a Screen.log || exit 1
    set +o pipefail
    echo ""
    if diff -r save_${tag} save_${tag}x > /dev/null && cmp -s result_${tag}/Log.txt result_${tag}x/Log.txt; then
        echo "=== config $tag: save/ and Log.txt are bit-identical between the minimal input and the explicit defaults ==="
    else
        echo "FAIL: config $tag differs between the minimal input (defaults) and the explicit defaults" >&2
        rc=1
    fi
    rm -rf save_${tag}_serial && cp -r save_${tag} save_${tag}_serial
done

# 最小入力の run は採用した既定値を "(default)" 付きで表示していること
ndef=$(grep -c "(default)" Screen.log)
echo "=== $ndef '(default)' lines were printed (expected 18) ==="
[ "$ndef" -eq 18 ] || { echo "FAIL: unexpected number of '(default)' lines" >&2; rc=1; }

if [ $rc -eq 0 ]; then
    echo "=== gwdefault verification PASS ==="
else
    echo "=== gwdefault verification FAIL ===" >&2
fi
exit $rc
