#!/bin/bash
# chutepool: 落差のあとの池へ落ち込む流れ(逐次実行。f_dry_head_cap = 2 と 3 の 2 構成)
#   ./Run.sh
# 合否は Check_chutepool.py(池の中の測線の流量が、与えた流量に合い、揺れないこと)。
# 揺れの項目は、2 では判定し、3 では記録する(3 の限界。README)
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
