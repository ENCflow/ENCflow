#!/bin/bash
# chutepool: 落差のあとの池へ落ち込む流れ(逐次実行。古い値の組み合わせの f_dry_head_cap を 2・3 にした 2 構成と、
#   4 つの値の組み合わせの 1 構成。どれも 4 つのスイッチを明示)
#   ./Run.sh
# 合否は Check_chutepool.py(池の中の測線の流量が、与えた流量に合い、揺れないこと。3 構成とも判定)
# 入力は、test/chichibu のデータから make_chutepool.py が切り出す

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

for k in z rw mask; do python3 "$sdir/make_chutepool.py" $k > cp_$k.txt || exit 1; done

set -o pipefail
: > Screen.log
for c in $(python3 "$sdir/make_chutepool.py" names); do
    ./encflow param_$c.txt | tee -a Screen.log || exit 1
done
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_chutepool.py" || rc=1
if [ $rc -eq 0 ]; then
    echo "=== chutepool verification PASS ==="
else
    echo "=== chutepool verification FAIL ===" >&2
fi
exit $rc
