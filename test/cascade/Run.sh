#!/bin/bash
# cascade: 急な段々の河道(逐次実行。f_dry_head_cap と f_advection_lateral の組み合わせで 3 構成)
#   ./Run.sh
# 合否は Check_cascade.py(下流の測線の流量が与えた流量に合うこと。f_dry_head_cap = 3 で、流れの水頭が
#   上流端の水位を 10 m 以上超えないこと。2 の値は限界として記録)
# 入力は、test/chichibu の 50 m 格子のデータから make_cascade.py が切り出す

sdir=$(dirname "$(readlink -f "$0")")
../Scripts/Check_mode.sh serial || exit 1

for k in z rw mask; do python3 "$sdir/make_cascade.py" $k > cs_$k.txt || exit 1; done

set -o pipefail
: > Screen.log
for c in $(python3 "$sdir/make_cascade.py" names); do
    ./encflow param_$c.txt | tee -a Screen.log || exit 1
done
set +o pipefail
echo ""

rc=0
python3 "$sdir/Check_cascade.py" || rc=1
if [ $rc -eq 0 ]; then
    echo "=== cascade verification PASS ==="
else
    echo "=== cascade verification FAIL ===" >&2
fi
exit $rc
