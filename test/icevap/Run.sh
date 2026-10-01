#!/bin/bash
# icevap: 降雨遮断・蒸発散パラメータの既定値の同値検定(逐次実行。developer.md §66)
#   ./Run.sh
# 構成 e(固定遮断率)・f(初期損失)・g(一定蒸発散)の各々について、最小入力
# (param_X.txt。既定値を使う)と既定値を明示した対照(param_Xx.txt)を実行し、
# save の全ファイルと result の Log.txt がバイト一致することを検定する。
# reference 機構は使わない(対照が基準)。save_X は save_X_serial にも複製する

../Scripts/Check_mode.sh serial || exit 1
rc=0
rm -f Screen.log
for tag in e f g; do
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
ndef=$(grep -c "(default)" Screen.log)
echo "=== $ndef '(default)' lines were printed (expected 3) ==="
[ "$ndef" -eq 3 ] || { echo "FAIL: unexpected number of '(default)' lines" >&2; rc=1; }
if [ $rc -eq 0 ]; then
    echo "=== icevap verification PASS ==="
else
    echo "=== icevap verification FAIL ===" >&2
fi
exit $rc
